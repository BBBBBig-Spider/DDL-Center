"""AI assistant business logic with safe fallbacks."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from app.config import AI_DAILY_TOKEN_LIMIT, DEEPSEEK_MODEL, SEMESTER_START
from app.network.key_store import KeyStore
from app.network.llm_client import LLMClient
from app.network.network_errors import NetworkError
from app.utils.semester import compute_current_week


class AIQuotaExceededError(RuntimeError):
    pass


PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
SUMMARY_CACHE_TTL = timedelta(hours=1)


class AIAssistantManager:
    TOKEN_PREFIX = "ai_tokens:"

    def __init__(
        self,
        *,
        task_manager=None,
        alert_manager=None,
        statistics_manager=None,
        setting_repository=None,
        schedule_manager=None,
        course_manager=None,
        key_store: KeyStore | None = None,
        llm_client_factory=LLMClient,
        model: str | None = None,
    ) -> None:
        self.task_manager = task_manager
        self.alert_manager = alert_manager
        self.statistics_manager = statistics_manager
        self.setting_repository = setting_repository
        self.schedule_manager = schedule_manager
        self.course_manager = course_manager
        self.key_store = key_store or KeyStore(setting_repository)
        self.llm_client_factory = llm_client_factory
        # Resolve initial model: explicit arg > stored setting > env default.
        resolved_model = model
        if resolved_model is None and setting_repository is not None:
            try:
                stored = setting_repository.get("deepseek_model", None)
                if isinstance(stored, str) and stored.strip():
                    resolved_model = stored.strip()
            except Exception:
                resolved_model = None
        if resolved_model is None:
            resolved_model = DEEPSEEK_MODEL
        self.model = resolved_model
        self._conversation_seq = 0
        self._conversations: dict[int, list[dict[str, str]]] = {}
        self._summary_cache: dict[str, tuple[datetime, str]] = {}
        self._memory_token_usage: dict[str, int] = {}

    def set_model(self, model: str) -> None:
        """Change the model used for subsequent LLM calls and persist it."""
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model name cannot be empty")
        self.model = model.strip()
        if self.setting_repository is not None:
            try:
                self.setting_repository.set("deepseek_model", self.model)
            except Exception:
                pass

    def get_model(self) -> str:
        return self.model

    def decompose_task(self, description: str, due_time: datetime) -> list[dict]:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description cannot be empty")
        if not isinstance(due_time, datetime):
            raise TypeError("due_time must be datetime")

        fallback = self._fallback_decomposition(description, due_time)
        prompt = self._format_prompt(
            "task_decompose.txt",
            (
                "Break this study task into 3-6 actionable subtasks. "
                "Return strict JSON array. Each item must have title, estimated_hours, note.\n"
                "Task: {description}\nDue time: {due_time}\nToday: {today}"
            ),
            description=description,
            due_time=due_time.isoformat(),
            today=date.today().isoformat(),
        )
        reply = self._safe_chat(
            [
                {
                    "role": "system",
                    "content": "You are a concise study planning assistant. Return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            fallback=json.dumps(fallback, ensure_ascii=False),
        )
        try:
            data = json.loads(reply)
        except ValueError:
            return fallback
        if not isinstance(data, list):
            return fallback
        cleaned = []
        for item in data:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            try:
                estimated_hours = float(item.get("estimated_hours", 1) or 1)
            except (TypeError, ValueError):
                estimated_hours = 1.0
            if estimated_hours <= 0:
                estimated_hours = 1.0
            cleaned.append(
                {
                    "title": title,
                    "estimated_hours": estimated_hours,
                    "note": str(item.get("note", "")).strip(),
                }
            )
        return cleaned or fallback

    def parse_task_from_text(self, raw_text: str) -> dict:
        """Backward-compatible task parser; delegates to parse_item_from_text."""
        item = self.parse_item_from_text(raw_text)
        if item["type"] == "none":
            raise ValueError("AI 未能识别出有效的任务/课程/考试信息")
        if item["type"] != "task":
            raise ValueError(
                f"AI 识别为 {item['type']} 类型，请使用智能创建对话框"
            )
        payload = dict(item["payload"])
        payload.setdefault("priority", 2)
        payload.setdefault("status", "todo")
        return payload

    def parse_item_from_text(self, raw_text: str) -> dict:
        """Parse a free-form Chinese description into a typed item.

        Returns ``{"type": "task"|"class"|"exam", "payload": {...}}`` where
        ``payload`` is shaped to match the corresponding facade.create_* method.
        Uses the LLM when available; falls back to regex parsing otherwise.
        """
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ValueError("raw_text cannot be empty")

        fallback_template = (
            "你是中文学习助理，识别用户描述的是 task / class / exam 之一并返回 JSON。"
            "今天是 {today}。\n输入：{raw_text}\n输出："
        )
        prompt = self._format_prompt(
            "item_from_text.txt",
            fallback_template,
            today=date.today().isoformat(),
            raw_text=raw_text.strip(),
        )
        reply = self._safe_chat(
            [
                {
                    "role": "system",
                    "content": "You parse Chinese descriptions to JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            fallback="{}",
        )

        if not reply or reply.strip() in {"{}", ""}:
            return self._fallback_parse_item(raw_text)

        match = re.search(r"\{.*\}", reply, re.DOTALL)
        if not match:
            return self._fallback_parse_item(raw_text)
        try:
            data = json.loads(match.group(0))
        except ValueError:
            return self._fallback_parse_item(raw_text)
        if not isinstance(data, dict):
            return self._fallback_parse_item(raw_text)

        item_type, payload = self._normalize_item_envelope(data)
        if item_type is None or not isinstance(payload, dict):
            return self._fallback_parse_item(raw_text)

        if item_type == "none":
            return {"type": "none", "payload": {}}

        try:
            if item_type == "task":
                cleaned = self._clean_task_payload(payload)
            elif item_type == "class":
                cleaned = self._clean_class_payload(payload)
            elif item_type == "exam":
                cleaned = self._clean_exam_payload(payload)
            else:
                return self._fallback_parse_item(raw_text)
        except ValueError:
            raise
        return {"type": item_type, "payload": cleaned}

    @staticmethod
    def _normalize_item_envelope(data: dict) -> tuple[str | None, dict]:
        """Accept both ``{type, payload}`` envelopes and flat shapes."""
        raw_type = data.get("type")
        payload = data.get("payload")
        if isinstance(raw_type, str):
            t = raw_type.strip().lower()
            if t == "none":
                return "none", payload if isinstance(payload, dict) else {}
            if t in ("task", "class", "exam") and isinstance(payload, dict):
                return t, payload
        # Flat shape heuristics — preserves backward compat with task-only LLM replies.
        has_weekday = "weekday" in data
        has_start_end = "start_time" in data and "end_time" in data
        if "title" in data and "due_time" in data and not has_weekday:
            return "task", data
        if "weekday" in data and has_start_end:
            return "class", data
        if ("name" in data) and has_start_end and not has_weekday:
            return "exam", data
        return None, data

    @staticmethod
    def _clean_task_payload(data: dict) -> dict:
        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("AI 未能识别出任务标题")
        title = title.strip()

        # ⚠️ Bug fix: when the input contains no deadline at all, the LLM is
        # explicitly instructed to return ``due_time: null``. Treat that as the
        # canonical "no deadline known" answer and propagate ``None`` upward —
        # do NOT fabricate a default (e.g. today 23:59), because callers like
        # ``SyncManager._ai_resolve_missing_due`` rely on ``None`` to drop the
        # item instead of writing a placeholder task.
        due_raw = data.get("due_time")
        due_time: datetime | None
        if due_raw is None or (isinstance(due_raw, str) and not due_raw.strip()):
            due_time = None
        elif isinstance(due_raw, datetime):
            due_time = due_raw.replace(tzinfo=None) if due_raw.tzinfo is not None else due_raw
        elif isinstance(due_raw, str):
            try:
                due_time = datetime.fromisoformat(due_raw.strip().replace("Z", ""))
            except ValueError:
                raise ValueError("AI 未能识别出截止时间")
            if due_time.tzinfo is not None:
                due_time = due_time.replace(tzinfo=None)
        else:
            raise ValueError("AI 未能识别出截止时间")

        description = data.get("description")
        if not isinstance(description, str):
            description = ""

        try:
            estimated_hours = float(data.get("estimated_hours", 2))
        except (TypeError, ValueError):
            estimated_hours = 2.0
        if estimated_hours <= 0:
            estimated_hours = 2.0

        return {
            "title": title,
            "due_time": due_time,
            "description": description,
            "estimated_hours": estimated_hours,
            "priority": 2,
            "status": "todo",
        }

    @staticmethod
    def _clean_class_payload(data: dict) -> dict:
        title = data.get("title") or data.get("name")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("AI 未能识别出课程标题")
        title = title.strip()[:30]

        try:
            weekday = int(data.get("weekday"))
        except (TypeError, ValueError):
            raise ValueError("AI 未能识别出星期")
        if not 1 <= weekday <= 7:
            raise ValueError("AI 识别出的星期不合法")

        try:
            start_time = time.fromisoformat(str(data.get("start_time", "")).strip())
            end_time = time.fromisoformat(str(data.get("end_time", "")).strip())
        except ValueError:
            raise ValueError("AI 未能识别出上下课时间")

        location = data.get("location")
        if not isinstance(location, str):
            location = ""

        try:
            start_week = int(data.get("start_week", 1))
        except (TypeError, ValueError):
            start_week = 1
        try:
            end_week = int(data.get("end_week", 16))
        except (TypeError, ValueError):
            end_week = 16
        if start_week < 1:
            start_week = 1
        if end_week < start_week:
            end_week = start_week

        week_type = str(data.get("week_type", "all")).strip().lower()
        if week_type not in ("all", "odd", "even"):
            week_type = "all"

        return {
            "title": title,
            "weekday": weekday,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "slot_type": "lecture",
            "start_week": start_week,
            "end_week": end_week,
            "week_type": week_type,
        }

    @staticmethod
    def _clean_exam_payload(data: dict) -> dict:
        name = data.get("name") or data.get("title")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("AI 未能识别出考试名称")
        name = name.strip()[:30]

        start_raw = data.get("start_time")
        end_raw = data.get("end_time")
        if not isinstance(start_raw, str) or not isinstance(end_raw, str):
            raise ValueError("AI 未能识别出考试时间")
        try:
            start_time = datetime.fromisoformat(start_raw.strip().replace("Z", ""))
            end_time = datetime.fromisoformat(end_raw.strip().replace("Z", ""))
        except ValueError:
            raise ValueError("AI 未能识别出考试时间")
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)

        location = data.get("location")
        if not isinstance(location, str):
            location = ""

        exam_type = str(data.get("exam_type", "final")).strip().lower()
        if exam_type not in ("final", "midterm", "quiz", "other"):
            exam_type = "final"

        return {
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "exam_type": exam_type,
            "seat": "",
        }

    @classmethod
    def _fallback_parse_item(cls, raw_text: str) -> dict:
        """Regex fallback when the LLM is unavailable; classifies first then parses.

        Returns ``{"type":"none","payload":{}}`` when the text doesn't yield a
        usable task/class/exam shape, except for empty input which still raises
        ValueError so callers can distinguish "nothing to parse" from "no signal".
        """
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ValueError("AI 不可用，无法识别输入")
        text = raw_text.strip()

        is_exam = bool(re.search(r"考试|期末|期中|小测|测验|quiz", text, re.IGNORECASE))
        is_class = (
            bool(re.search(r"每周|每星期|周[一二三四五六日天]|讲授|上课|课程|节课", text))
            and not is_exam
        )

        try:
            if is_exam:
                return {"type": "exam", "payload": cls._fallback_parse_exam(text)}
            if is_class:
                return {"type": "class", "payload": cls._fallback_parse_class(text)}
            return {"type": "task", "payload": cls._fallback_parse_task(text)}
        except ValueError:
            return {"type": "none", "payload": {}}

    @classmethod
    def _extract_time_range(cls, text: str) -> tuple[time | None, time | None]:
        """Find a "HH:MM-HH:MM" or "H点-H点" / "H-H 点" range; respects 晚."""
        m = re.search(
            r"(\d{1,2})[:：](\d{2})\s*[\-–~到至]\s*(\d{1,2})[:：](\d{2})",
            text,
        )
        if m:
            sh, sm, eh, em = (int(g) for g in m.groups())
            if "晚" in text and sh < 12:
                sh += 12
                if eh < 12:
                    eh += 12
            if 0 <= sh <= 23 and 0 <= eh <= 23 and 0 <= sm < 60 and 0 <= em < 60:
                return time(sh, sm), time(eh, em)
        m = re.search(
            r"(\d{1,2})\s*[\-–~到至]\s*(\d{1,2})\s*点",
            text,
        )
        if m:
            sh, eh = int(m.group(1)), int(m.group(2))
            if "晚" in text and sh < 12:
                sh += 12
                if eh < 12:
                    eh += 12
            if 0 <= sh <= 23 and 0 <= eh <= 23:
                return time(sh, 0), time(eh, 0)
        return None, None

    @classmethod
    def _fallback_parse_class(cls, text: str) -> dict:
        weekday_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}
        m = re.search(r"周([一二三四五六日天])", text)
        if not m:
            raise ValueError("AI 不可用，无法识别输入")
        weekday = weekday_map[m.group(1)]

        start_time, end_time = cls._extract_time_range(text)
        if start_time is None or end_time is None:
            raise ValueError("AI 不可用，无法识别输入")

        start_week, end_week = 1, 16
        wm = re.search(r"(\d{1,2})\s*[\-–~到至]\s*(\d{1,2})\s*周", text)
        if wm:
            start_week = int(wm.group(1))
            end_week = int(wm.group(2))

        location = ""
        lm = re.search(
            r"(理教|文史楼|二教|三教|四教|教学楼|实验楼|[A-Za-z]+楼)\s*\w*",
            text,
        )
        if lm:
            location = lm.group(0).strip()

        title = cls._strip_class_tokens(text)
        if not title:
            title = text[:20]

        return {
            "title": title,
            "weekday": weekday,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "slot_type": "lecture",
            "start_week": start_week,
            "end_week": end_week,
            "week_type": "all",
        }

    @staticmethod
    def _strip_class_tokens(text: str) -> str:
        title = text
        title = re.sub(r"每周[一二三四五六日天]|每星期[一二三四五六日天]", "", title)
        title = re.sub(r"每周|每星期", "", title)
        title = re.sub(r"周[一二三四五六日天]", "", title)
        title = re.sub(
            r"\d{1,2}[:：]\d{2}\s*[\-–~到至]\s*\d{1,2}[:：]\d{2}",
            "",
            title,
        )
        title = re.sub(
            r"\d{1,2}\s*[\-–~到至]\s*\d{1,2}\s*周",
            "",
            title,
        )
        title = re.sub(
            r"\d{1,2}\s*[\-–~到至]\s*\d{1,2}\s*点",
            "",
            title,
        )
        title = re.sub(r"晚上|早上|上午|中午|下午|深夜|凌晨|晚", "", title)
        title = re.sub(
            r"理教\s*\w*|二教\s*\w*|三教\s*\w*|四教\s*\w*|文史楼\s*\w*|教学楼\s*\w*|实验楼\s*\w*",
            "",
            title,
        )
        title = re.sub(r"[，,。;；]+", " ", title)
        title = re.sub(r"\s+", " ", title)
        return title.strip(" ，。、:：-~")[:30]

    @classmethod
    def _fallback_parse_exam(cls, text: str) -> dict:
        today = date.today()
        target_date: date | None = None

        m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
        if m:
            try:
                target_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                target_date = None

        if target_date is None:
            m = re.search(r"(\d{1,2})月(\d{1,2})[日号]", text)
            if m:
                month, day = int(m.group(1)), int(m.group(2))
                year = today.year
                try:
                    cand = date(year, month, day)
                    if cand < today:
                        cand = date(year + 1, month, day)
                    target_date = cand
                except ValueError:
                    target_date = None

        start_time, end_time = cls._extract_time_range(text)
        if target_date is None or start_time is None or end_time is None:
            raise ValueError("AI 不可用，无法识别输入")

        name = cls._strip_exam_tokens(text)
        if not name:
            name = text[:30]

        if "期中" in text:
            exam_type = "midterm"
        elif "小测" in text or "测验" in text or re.search(r"quiz", text, re.IGNORECASE):
            exam_type = "quiz"
        elif "期末" in text or "考试" in text:
            exam_type = "final"
        else:
            exam_type = "other"

        location = ""
        lm = re.search(
            r"(理教|文史楼|二教|三教|四教|教学楼|实验楼|[A-Za-z]+楼)\s*\w*",
            text,
        )
        if lm:
            location = lm.group(0).strip()

        return {
            "name": name,
            "start_time": datetime.combine(target_date, start_time),
            "end_time": datetime.combine(target_date, end_time),
            "location": location,
            "exam_type": exam_type,
            "seat": "",
        }

    @staticmethod
    def _strip_exam_tokens(text: str) -> str:
        name = text
        for sep in ["，", ",", "。", "；", ";"]:
            if sep in name:
                name = name.split(sep, 1)[0]
                break
        name = re.sub(r"\d{4}-\d{1,2}-\d{1,2}.*", "", name)
        name = re.sub(r"\d{1,2}月\d{1,2}[日号].*", "", name)
        name = re.sub(
            r"\d{1,2}[:：]\d{2}\s*[\-–~到至]\s*\d{1,2}[:：]\d{2}.*",
            "",
            name,
        )
        name = re.sub(
            r"(早上|上午|中午|下午|晚上|晚|深夜|凌晨)?\d{1,2}[点:：]\d{0,2}.*",
            "",
            name,
        )
        return name.strip(" ，。、:：-~")[:30]

    @staticmethod
    def _fallback_parse_task(raw_text: str) -> dict:
        """Pure-regex fallback for parsing task descriptions when LLM is unavailable."""
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ValueError("AI 未能识别出任务标题")
        text = raw_text.strip()
        today = date.today()

        # ── Date parsing ───────────────────────────────────────
        target_date: date | None = None

        m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
        if m:
            try:
                target_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                target_date = None

        if target_date is None:
            m = re.search(r"(\d{1,2})月(\d{1,2})[日号]", text)
            if m:
                month, day = int(m.group(1)), int(m.group(2))
                year = today.year
                try:
                    candidate = date(year, month, day)
                    if candidate < today:
                        candidate = date(year + 1, month, day)
                    target_date = candidate
                except ValueError:
                    target_date = None

        if target_date is None:
            if "后天" in text:
                target_date = today + timedelta(days=2)
            elif "明天" in text:
                target_date = today + timedelta(days=1)
            elif "今天" in text or "今晚" in text:
                target_date = today

        if target_date is None:
            weekday_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}
            m = re.search(r"(这|本|下)?周([一二三四五六日天])", text)
            if m:
                prefix = m.group(1) or "这"
                target_wd = weekday_map[m.group(2)]
                today_wd = today.isoweekday()
                delta = target_wd - today_wd
                if prefix == "下":
                    if delta <= 0:
                        delta += 7
                    else:
                        delta += 7
                else:
                    if delta < 0:
                        delta += 7
                target_date = today + timedelta(days=delta)

        # ── Time parsing ───────────────────────────────────────
        target_time: time | None = None
        next_day = False

        # 24点 / 0点 → next day 00:00
        if re.search(r"24[点:：]", text) or re.search(r"24点", text):
            target_time = time(0, 0)
            next_day = True

        if target_time is None:
            m = re.search(r"(\d{1,2})[:：](\d{2})", text)
            if m:
                hour, minute = int(m.group(1)), int(m.group(2))
                # Apply evening base if "晚" appears
                if ("晚上" in text or "今晚" in text or "晚" in text) and hour < 12:
                    hour += 12
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    target_time = time(hour, minute)

        if target_time is None:
            m = re.search(r"(\d{1,2})点", text)
            if m:
                hour = int(m.group(1))
                if hour == 24:
                    target_time = time(0, 0)
                    next_day = True
                else:
                    if "凌晨" in text or "深夜" in text:
                        if hour >= 12:
                            hour -= 12
                    elif "晚上" in text or "今晚" in text or "晚" in text:
                        if hour < 12:
                            hour += 12
                    elif "下午" in text and hour < 12:
                        hour += 12
                    elif "中午" in text:
                        hour = 12
                    if 0 <= hour <= 23:
                        target_time = time(hour, 0)

        if target_time is None and ("晚上" in text or "今晚" in text):
            target_time = time(18, 0)
        if target_time is None and "中午" in text:
            target_time = time(12, 0)
        if target_time is None and "凌晨" in text:
            target_time = time(0, 0)

        if target_date is None and target_time is None:
            raise ValueError("AI 未能识别出截止时间，请补充日期或时间。")

        if target_date is None:
            target_date = today
        if target_time is None:
            target_time = time(23, 59)

        due_dt = datetime.combine(target_date, target_time)
        if next_day:
            due_dt = due_dt + timedelta(days=1)

        # ── Title extraction ───────────────────────────────────
        # Strip date/time tokens from a leading clause to derive title.
        title = text
        # Common splitters
        for sep in ["，", ",", "。", "；", ";"]:
            if sep in title:
                title = title.split(sep, 1)[0]
                break
        # Drop trailing time/date noise from title
        title = re.sub(r"\d{4}-\d{1,2}-\d{1,2}.*", "", title)
        title = re.sub(r"\d{1,2}月\d{1,2}[日号].*", "", title)
        title = re.sub(r"(今天|明天|后天|今晚|这周[一二三四五六日天]|下周[一二三四五六日天]).*", "", title)
        title = re.sub(r"(凌晨|早上|上午|中午|下午|晚上|深夜)?\d{1,2}[点:：]\d{0,2}.*", "", title)
        title = re.sub(r"(截止|deadline|DDL).*", "", title, flags=re.IGNORECASE)
        title = title.strip(" ，。、:：")
        if not title:
            title = text[:20]
        if len(title) > 30:
            title = title[:30]

        return {
            "title": title,
            "due_time": due_dt,
            "description": "",
            "estimated_hours": 2.0,
            "priority": 2,
            "status": "todo",
        }

    def chat(
        self,
        conversation_id: int | None,
        user_msg: str,
        context_task_id: int | None = None,
    ) -> tuple[int, str]:
        if not isinstance(user_msg, str) or not user_msg.strip():
            raise ValueError("user_msg cannot be empty")
        if conversation_id is None:
            self._conversation_seq += 1
            conversation_id = self._conversation_seq
            self._conversations[conversation_id] = []

        history = self._conversations.setdefault(conversation_id, [])
        messages = [
            {
                "role": "system",
                "content": self._load_prompt(
                    "chat_assistant.txt",
                    "You help students plan deadlines and study work. Keep replies concise and actionable.",
                ),
            },
        ]
        # Inject live data context on every turn so AI always has current state
        data_context = self._build_data_context(context_task_id)
        if data_context:
            messages.append({"role": "system", "content": data_context})

        messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_msg.strip()})

        fallback = "AI 暂时不可用，请继续使用手动计划功能。"
        reply = self._safe_chat(messages, fallback=fallback)
        history.append({"role": "user", "content": user_msg.strip()})
        history.append({"role": "assistant", "content": reply})
        return conversation_id, reply

    def reset_conversation(self, conversation_id: int | None = None) -> int | None:
        if conversation_id is not None:
            self._conversations.pop(conversation_id, None)
            return None
        self._conversations.clear()
        return None

    def generate_briefing(self) -> str:
        if self.task_manager is None:
            return ""
        tasks = self.task_manager.list_tasks()
        open_tasks = [task for task in tasks if task.status != "done"]
        if not open_tasks:
            return "今日暂无未完成任务，保持节奏。"

        stats = self.statistics_manager.get_statistics() if self.statistics_manager else None
        task_lines = "\n".join(
            f"- {task.title}，截止 {task.due_time.strftime('%m-%d %H:%M')}，优先级 {task.priority}"
            for task in sorted(open_tasks, key=lambda t: t.due_time)[:8]
        )
        completion = getattr(stats, "completion_rate", 0.0)

        # Add today's schedule to briefing context
        schedule_lines = ""
        if self.schedule_manager is not None:
            try:
                today = date.today()
                today_weekday = today.isoweekday()
                current_week = compute_current_week(self.setting_repository)
                slots = self.schedule_manager.list_slots(current_week, today_weekday)
                if slots:
                    schedule_lines = "\n".join(
                        f"- {s.title} {s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}"
                        for s in sorted(slots, key=lambda x: x.start_time)
                    )
            except Exception:
                pass

        prompt = self._format_prompt(
            "daily_briefing.txt",
            (
                "请用中文写一段简短的每日学习简报（不超过120字）。"
                "结合课表空闲情况和紧急 DDL，给出今日重点建议。\n"
                "完成率：{completion}\n任务：\n{task_lines}\n今日课表：\n{schedule_lines}"
            ),
            completion=f"{completion:.0%}",
            task_lines=task_lines,
            schedule_lines=schedule_lines or "今日无课",
        )
        return self._safe_chat(
            [
                {"role": "system", "content": "你为学生写简洁的每日学习简报。"},
                {"role": "user", "content": prompt},
            ],
            fallback=self._fallback_briefing(open_tasks),
        )

    def compress_description(self, text: str, max_chars: int = 120) -> str:
        if not isinstance(text, str):
            return ""
        if len(text) <= max_chars:
            return text
        if not self.is_available():
            return self._truncate_description(text, max_chars)

        prompt = self._format_prompt(
            "compress_description.txt",
            (
                "你是中文助理。把下面的作业描述压缩为 <= {max_chars} 个汉字的一句话摘要。\n"
                "描述：\n{text}"
            ),
            max_chars=max_chars,
            text=text,
        )
        reply = self._safe_chat(
            [
                {"role": "system", "content": "你为学生压缩作业描述。直接输出结果。"},
                {"role": "user", "content": prompt},
            ],
            fallback="",
        )
        cleaned = (reply or "").strip()
        if not cleaned:
            return self._truncate_description(text, max_chars)
        if len(cleaned) > max_chars:
            return self._truncate_description(cleaned, max_chars)
        return cleaned

    @staticmethod
    def _truncate_description(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        head = text[: max_chars - 1]
        for sep in ("。", "；", "\n", "！", "？"):
            idx = head.rfind(sep)
            if idx >= max_chars // 2:
                return head[: idx + 1] + "…"
        return head + "…"

    def summarize_ddl(self, raw_text: str) -> str:
        if not isinstance(raw_text, str):
            raise TypeError("raw_text must be str")
        if not raw_text.strip():
            return ""
        cache_key = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        cached = self._summary_cache.get(cache_key)
        now = datetime.now()
        if cached is not None and now - cached[0] < SUMMARY_CACHE_TTL:
            return cached[1]
        if cached is not None:
            self._summary_cache.pop(cache_key, None)

        prompt = self._format_prompt(
            "ddl_summarize.txt",
            (
                "Summarize this teaching-site DDL content in Chinese. "
                "Focus on deadlines, course names, and risks. Keep it concise.\n"
                "{raw_text}"
            ),
            raw_text=raw_text[:6000],
        )
        summary = self._safe_chat(
            [
                {"role": "system", "content": "You summarize raw DDL pages for students."},
                {"role": "user", "content": prompt},
            ],
            fallback=raw_text[:300],
        )
        self._summary_cache[cache_key] = (now, summary)
        return summary

    def set_api_key(self, key: str) -> None:
        self.key_store.set_key(key)

    def get_api_key(self) -> str | None:
        return self.key_store.get_key()

    def test_api_key(self, key: str) -> bool:
        try:
            client = self.llm_client_factory(key, model=self.model)
            client.chat([{"role": "user", "content": "ping"}], max_tokens=8)
            return True
        except Exception:
            return False

    def is_available(self) -> bool:
        if not self.key_store.has_key():
            return False
        if AI_DAILY_TOKEN_LIMIT == float("inf"):
            return True
        return self.today_token_usage() < AI_DAILY_TOKEN_LIMIT

    def today_token_usage(self) -> int:
        key = self.TOKEN_PREFIX + date.today().isoformat()
        if self.setting_repository is None:
            return self._memory_token_usage.get(key, 0)
        raw = self.setting_repository.get(key, "0")
        try:
            return int(raw or "0")
        except ValueError:
            return 0

    def _safe_chat(self, messages: list[dict], *, fallback: str) -> str:
        key = self.key_store.get_key()
        if not key:
            return fallback
        try:
            self._check_quota_or_raise(messages)
            client = self.llm_client_factory(key, model=self.model)
            reply, tokens = client.chat(messages)
            self._add_tokens(tokens)
            return reply.strip() or fallback
        except (AIQuotaExceededError, NetworkError, RuntimeError, ValueError, TypeError):
            return fallback

    def _add_tokens(self, count: int) -> None:
        count = max(0, int(count or 0))
        key = self.TOKEN_PREFIX + date.today().isoformat()
        if self.setting_repository is None:
            self._memory_token_usage[key] = self.today_token_usage() + count
            return
        self.setting_repository.set(key, str(self.today_token_usage() + count))

    def _check_quota_or_raise(self, messages: list[dict]) -> None:
        if AI_DAILY_TOKEN_LIMIT == float("inf"):
            return
        estimated_tokens = self._estimate_input_tokens(messages)
        if self.today_token_usage() + estimated_tokens > AI_DAILY_TOKEN_LIMIT:
            raise AIQuotaExceededError("daily AI token limit exceeded")

    @staticmethod
    def _estimate_input_tokens(messages: list[dict]) -> int:
        text = "\n".join(str(message.get("content", "")) for message in messages if isinstance(message, dict))
        return max(1, len(text) // 4)

    @staticmethod
    def _load_prompt(filename: str, fallback: str) -> str:
        path = PROMPT_DIR / filename
        try:
            prompt = path.read_text(encoding="utf-8").strip()
        except OSError:
            return fallback
        return prompt or fallback

    @classmethod
    def _format_prompt(cls, filename: str, fallback: str, **kwargs) -> str:
        template = cls._load_prompt(filename, fallback)
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return fallback.format(**kwargs)

    def _build_data_context(self, focused_task_id: int | None = None) -> str:
        """Build a concise system-level data dump for the AI."""
        lines: list[str] = [f"今天是 {date.today().isoformat()}。"]

        # Tasks
        if self.task_manager is not None:
            try:
                tasks = self.task_manager.list_tasks()
                open_tasks = [t for t in tasks if t.status != "done"]
                if open_tasks:
                    lines.append(f"\n【未完成任务（共 {len(open_tasks)} 条）】")
                    for t in sorted(open_tasks, key=lambda x: x.due_time)[:12]:
                        overdue_flag = "（已逾期）" if t.due_time < datetime.now() else ""
                        lines.append(
                            f"- [{t.id}] {t.title} | 截止 {t.due_time.strftime('%m-%d %H:%M')}"
                            f"{overdue_flag} | 预计 {t.estimated_hours}h | 优先级 {t.priority}"
                        )
                else:
                    lines.append("\n【任务】暂无未完成任务。")
            except Exception:
                pass

        # Courses
        if self.course_manager is not None:
            try:
                courses = self.course_manager.list_courses()
                if courses:
                    lines.append(f"\n【课程（共 {len(courses)} 门）】")
                    for c in courses[:10]:
                        teacher = f"（{c.teacher}）" if c.teacher else ""
                        lines.append(f"- [{c.id}] {c.name}{teacher}")
            except Exception:
                pass

        # Today's schedule
        if self.schedule_manager is not None:
            try:
                today_weekday = date.today().isoweekday()
                current_week = compute_current_week(self.setting_repository)
                slots = self.schedule_manager.list_slots(current_week, today_weekday)
                if slots:
                    lines.append(f"\n【今日课表（第 {current_week} 周，周{today_weekday}）】")
                    for s in sorted(slots, key=lambda x: x.start_time):
                        lines.append(
                            f"- {s.title} {s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}"
                            f" @{s.location or '未知地点'}"
                        )
                else:
                    lines.append(f"\n【今日课表】今天（周{today_weekday}）无课。")
            except Exception:
                pass

        # Full schedule context
        if self.schedule_manager is not None:
            try:
                lines.extend(self._build_schedule_context())
            except Exception:
                pass

        # Focused task detail
        if focused_task_id is not None and self.task_manager is not None:
            try:
                task = self.task_manager.get_task(focused_task_id)
                if task is not None:
                    lines.append(
                        f"\n【当前聚焦任务】{task.title} | 截止 {task.due_time.isoformat()} | "
                        f"预计 {task.estimated_hours}h | 状态 {task.status} | 描述：{task.description or '无'}"
                    )
            except Exception:
                pass

        return "\n".join(lines)

    def _build_schedule_context(self) -> list[str]:
        today = date.today()
        current_week = self._current_semester_week(today)
        # The full-schedule iteration below historically capped at week 16;
        # honour the user-configured ``semester_total_weeks`` (clamped to
        # [1, 40]) so late-semester slots aren't silently dropped from the
        # AI context. See REVIEW.md severe #2.
        upper = 30
        if self.setting_repository is not None:
            try:
                stored_total = self.setting_repository.get("semester_total_weeks", None)
                if stored_total is not None:
                    upper = max(1, min(40, int(stored_total)))
            except Exception:
                pass
        weekday_names = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
        lines: list[str] = [f"\n【当前周完整课表（第 {current_week} 周）】"]

        week_has_slots = False
        for weekday in range(1, 8):
            slots = self.schedule_manager.list_slots(current_week, weekday)
            if not slots:
                continue
            week_has_slots = True
            lines.append(f"{weekday_names[weekday]}：")
            for slot in sorted(slots, key=lambda x: x.start_time):
                lines.append(f"- {self._format_schedule_slot(slot)}")
        if not week_has_slots:
            lines.append("本周暂无课程。")

        all_slots_by_key = {}
        for week in range(1, upper + 1):
            for slot in self.schedule_manager.list_slots(week):
                key = (
                    getattr(slot, "id", None),
                    getattr(slot, "title", ""),
                    getattr(slot, "weekday", 0),
                    getattr(slot, "start_time", None),
                    getattr(slot, "end_time", None),
                    getattr(slot, "start_week", week),
                    getattr(slot, "end_week", week),
                    getattr(slot, "week_type", "all"),
                )
                all_slots_by_key[key] = slot

        lines.append(f"\n【全学期课表摘要（共 {len(all_slots_by_key)} 个课程/时段）】")
        if not all_slots_by_key:
            lines.append("暂无全学期课表数据。")
            return lines

        all_slots = sorted(
            all_slots_by_key.values(),
            key=lambda slot: (
                getattr(slot, "weekday", 0),
                getattr(slot, "start_time", None),
                getattr(slot, "title", ""),
            ),
        )
        for slot in all_slots[:80]:
            weekday = weekday_names.get(getattr(slot, "weekday", 0), str(getattr(slot, "weekday", "")))
            lines.append(f"- {weekday} {self._format_schedule_slot(slot)} | {self._format_week_range(slot)}")
        if len(all_slots) > 80:
            lines.append(f"- 其余 {len(all_slots) - 80} 个时段已省略。")
        return lines

    def _current_semester_week(self, today: date | None = None) -> int:
        """Compute the current semester week, honouring user-configured
        ``semester_total_weeks`` (default 30, clamped to [1, 40]).

        Historically this clamped to ``[1, 16]``, which meant any user whose
        schedule extended past week 16 would see the AI context permanently
        pinned to week 16 in late semester — every recommendation thereafter
        was off by N weeks. See REVIEW.md severe #2.
        """
        # ``today`` is accepted for backwards compatibility with old callers
        # that pre-computed it; the helper itself uses ``date.today()`` and
        # the resulting week is identical when ``today`` matches the system
        # clock. We delegate to ``compute_current_week`` so the upper bound
        # tracks ``semester_total_weeks`` consistently with the rest of the
        # codebase.
        return compute_current_week(self.setting_repository)

    @staticmethod
    def _format_schedule_slot(slot) -> str:
        start = slot.start_time.strftime("%H:%M") if hasattr(slot.start_time, "strftime") else str(slot.start_time)[:5]
        end = slot.end_time.strftime("%H:%M") if hasattr(slot.end_time, "strftime") else str(slot.end_time)[:5]
        location = getattr(slot, "location", "") or "未知地点"
        return f"{slot.title} {start}-{end} @{location}"

    @staticmethod
    def _format_week_range(slot) -> str:
        start_week = getattr(slot, "start_week", "")
        end_week = getattr(slot, "end_week", "")
        week_type = getattr(slot, "week_type", "all")
        suffix = {"odd": "单周", "even": "双周", "all": "每周"}.get(week_type, week_type)
        if start_week == end_week:
            return f"第 {start_week} 周，{suffix}"
        return f"第 {start_week}-{end_week} 周，{suffix}"

    def _task_context(self, task_id: int | None) -> str:
        """Kept for backward compatibility; delegates to _build_data_context."""
        return self._build_data_context(task_id)

    @staticmethod
    def _fallback_decomposition(description: str, due_time: datetime) -> list[dict]:
        return [
            {
                "title": "Clarify requirements",
                "estimated_hours": 0.5,
                "note": f"Read the task and confirm what must be delivered before {due_time:%Y-%m-%d}.",
            },
            {"title": "Draft first version", "estimated_hours": 1.5, "note": description[:80]},
            {"title": "Review and submit", "estimated_hours": 0.5, "note": "Check quality and submit."},
        ]

    @staticmethod
    def _fallback_briefing(tasks: list[Any]) -> str:
        first = sorted(tasks, key=lambda task: task.due_time)[0]
        return f"Today focus: {first.title}, due {first.due_time:%Y-%m-%d %H:%M}."
