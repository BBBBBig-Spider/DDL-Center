"""AI assistant business logic with safe fallbacks."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import AI_DAILY_TOKEN_LIMIT
from app.network.key_store import KeyStore
from app.network.llm_client import LLMClient
from app.network.network_errors import NetworkError


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
        key_store: KeyStore | None = None,
        llm_client_factory=LLMClient,
    ) -> None:
        self.task_manager = task_manager
        self.alert_manager = alert_manager
        self.statistics_manager = statistics_manager
        self.setting_repository = setting_repository
        self.key_store = key_store or KeyStore(setting_repository)
        self.llm_client_factory = llm_client_factory
        self._conversation_seq = 0
        self._conversations: dict[int, list[dict[str, str]]] = {}
        self._summary_cache: dict[str, tuple[datetime, str]] = {}
        self._memory_token_usage: dict[str, int] = {}

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
        context = self._task_context(context_task_id)
        messages = [
            {
                "role": "system",
                "content": self._load_prompt(
                    "chat_assistant.txt",
                    "You help students plan deadlines and study work. Keep replies concise and actionable.",
                ),
            },
        ]
        if context:
            messages.append({"role": "system", "content": context})
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_msg.strip()})

        fallback = "AI is temporarily unavailable. Please continue with manual planning."
        reply = self._safe_chat(messages, fallback=fallback)
        history.append({"role": "user", "content": user_msg.strip()})
        history.append({"role": "assistant", "content": reply})
        return conversation_id, reply

    def generate_briefing(self) -> str:
        if self.task_manager is None:
            return ""
        tasks = self.task_manager.list_tasks()
        open_tasks = [task for task in tasks if task.status != "done"]
        if not open_tasks:
            return "No open tasks. Keep the schedule light today."

        stats = self.statistics_manager.get_statistics() if self.statistics_manager else None
        task_lines = "\n".join(
            f"- {task.title}, due {task.due_time.isoformat()}, priority {task.priority}"
            for task in sorted(open_tasks, key=lambda task: task.due_time)[:8]
        )
        completion = getattr(stats, "completion_rate", 0.0)
        prompt = self._format_prompt(
            "daily_briefing.txt",
            (
                "Write a short daily study briefing in Chinese. "
                "Mention urgent deadlines and workload. Keep it under 120 Chinese characters.\n"
                "Completion rate: {completion}\nTasks:\n{task_lines}"
            ),
            completion=f"{completion:.0%}",
            task_lines=task_lines,
        )
        return self._safe_chat(
            [
                {"role": "system", "content": "You write compact student briefings."},
                {"role": "user", "content": prompt},
            ],
            fallback=self._fallback_briefing(open_tasks),
        )

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
            client = self.llm_client_factory(key)
            client.chat([{"role": "user", "content": "ping"}], max_tokens=8)
            return True
        except Exception:
            return False

    def is_available(self) -> bool:
        return self.key_store.has_key() and self.today_token_usage() < AI_DAILY_TOKEN_LIMIT

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
            client = self.llm_client_factory(key)
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

    def _task_context(self, task_id: int | None) -> str:
        if task_id is None or self.task_manager is None:
            return ""
        task = self.task_manager.get_task(task_id)
        if task is None:
            return ""
        return (
            f"Current task: {task.title}; due {task.due_time.isoformat()}; "
            f"estimated hours {task.estimated_hours}; status {task.status}."
        )

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
