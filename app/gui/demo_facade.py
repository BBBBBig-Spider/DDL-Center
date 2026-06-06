from __future__ import annotations

from datetime import datetime, time, timedelta


class AttrDict:
    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, key):
        return self._data.get(key)

    def __getitem__(self, key):
        return self._data.get(key)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def update(self, data: dict) -> None:
        self._data.update(data)

    def to_dict(self) -> dict:
        return dict(self._data)


class DemoFacade:
    """In-memory AppFacade-compatible implementation for demo mode."""

    def __init__(self):
        now = datetime.now().replace(second=0, microsecond=0)
        self._api_key = ""
        self._task_arrangements = {}
        self._courses = [
            {"id": 101, "name": "人工智能引论", "teacher": "", "semester": "2026 Spring", "color": "#8C1515"},
            {"id": 102, "name": "汉英翻译理论与实践", "teacher": "", "semester": "2026 Spring", "color": "#B8860B"},
            {"id": 103, "name": "习近平新时代中国特色社会主义思想概论", "teacher": "", "semester": "2026 Spring", "color": "#6B7D3A"},
            {"id": 104, "name": "高等数学A", "teacher": "", "semester": "2026 Spring", "color": "#5F0F0F"},
            {"id": 105, "name": "理想国讨论班", "teacher": "", "semester": "2026 Spring", "color": "#9B6A1C"},
            {"id": 106, "name": "太极拳", "teacher": "", "semester": "2026 Spring", "color": "#6B7D3A"},
            {"id": 107, "name": "程序设计实习", "teacher": "", "semester": "2026 Spring", "color": "#8C1515"},
            {"id": 108, "name": "概率统计A", "teacher": "", "semester": "2026 Spring", "color": "#B8860B"},
            {"id": 109, "name": "高等数学A习题课", "teacher": "", "semester": "2026 Spring", "color": "#5F0F0F"},
        ]
        self._tasks = [
            {
                "id": 1,
                "title": "高数习题整理",
                "course_id": 104,
                "course_name": "高等数学A",
                "description": "整理本周习题并检查证明过程。",
                "due_time": now + timedelta(hours=8),
                "estimated_hours": 2.0,
                "status": "todo",
                "priority": 1,
            },
            {
                "id": 2,
                "title": "程序设计实习项目推进",
                "course_id": 107,
                "course_name": "程序设计实习",
                "description": "完成 GUI 演示版联调。",
                "due_time": now + timedelta(days=2),
                "estimated_hours": 4.0,
                "status": "doing",
                "priority": 2,
            },
            {
                "id": 3,
                "title": "概率统计复习",
                "course_id": 108,
                "course_name": "概率统计A",
                "description": "复习随机变量和分布函数。",
                "due_time": now + timedelta(days=5),
                "estimated_hours": 3.0,
                "status": "todo",
                "priority": 3,
            },
            {
                "id": 4,
                "title": "汉英翻译展示准备",
                "course_id": 102,
                "course_name": "汉英翻译理论与实践",
                "description": "准备课堂展示材料。",
                "due_time": now + timedelta(days=1, hours=6),
                "estimated_hours": 1.5,
                "status": "done",
                "priority": 2,
            },
        ]
        self._schedule_slots = self._build_demo_schedule()
        self._next_task_id = max(task["id"] for task in self._tasks) + 1
        self._next_slot_id = max(slot["id"] for slot in self._schedule_slots) + 1

    def list_tasks(self, filters=None):
        filters = filters or {}
        tasks = list(self._tasks)
        status = filters.get("status")
        course_id = filters.get("course_id")
        order_by = filters.get("order_by", "due_time")
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        if course_id is not None:
            tasks = [task for task in tasks if task.get("course_id") == course_id]
        if filters.get("due_before") is not None:
            tasks = [task for task in tasks if task.get("due_time") <= filters["due_before"]]
        if order_by == "priority":
            tasks.sort(key=lambda task: (task.get("priority", 2), task.get("due_time")))
        else:
            tasks.sort(key=lambda task: task.get("due_time"))
        return [AttrDict(task) for task in tasks]

    def create_task(self, data):
        payload = dict(data)
        payload["id"] = self._next_task_id
        self._next_task_id += 1
        payload.setdefault("description", "")
        payload.setdefault("estimated_hours", 1.0)
        payload.setdefault("status", "todo")
        payload.setdefault("priority", 2)
        payload["course_name"] = self._course_name(payload.get("course_id")) or "通用任务"
        self._tasks.append(payload)
        return payload["id"]

    def update_task(self, task_id, data):
        task = self._find_by_id(self._tasks, task_id, "task")
        task.update(data)
        task["course_name"] = self._course_name(task.get("course_id")) or "通用任务"

    def delete_task(self, task_id):
        before = len(self._tasks)
        self._tasks = [task for task in self._tasks if task["id"] != task_id]
        if len(self._tasks) == before:
            raise ValueError(f"task {task_id} not found")

    def mark_task_done(self, task_id):
        self.update_task(task_id, {"status": "done"})

    def list_courses(self):
        return [AttrDict(course) for course in self._courses]

    def list_schedule(self, weekday: int, week: int):
        slots = [
            slot
            for slot in self._schedule_slots
            if slot["weekday"] == weekday and self._occurs_in_week(slot, week)
        ]
        return [AttrDict(slot) for slot in sorted(slots, key=lambda slot: slot["start_time"])]

    def create_schedule_slot(self, data: dict) -> int:
        payload = dict(data)
        payload["id"] = self._next_slot_id
        self._next_slot_id += 1
        payload.setdefault("course_id", None)
        payload.setdefault("location", "")
        payload.setdefault("slot_type", "custom")
        payload.setdefault("start_week", 1)
        payload.setdefault("end_week", 16)
        payload.setdefault("week_type", "all")
        payload.setdefault("source", "manual")
        self._schedule_slots.append(payload)
        return payload["id"]

    def update_schedule_slot(self, slot_id: int, data: dict) -> None:
        self._find_by_id(self._schedule_slots, slot_id, "schedule slot").update(data)

    def delete_schedule_slot(self, slot_id: int) -> None:
        before = len(self._schedule_slots)
        self._schedule_slots = [slot for slot in self._schedule_slots if slot["id"] != slot_id]
        if len(self._schedule_slots) == before:
            raise ValueError(f"schedule slot {slot_id} not found")

    def get_free_slots(self, weekday: int, week: int):
        busy_slots = [slot.to_dict() for slot in self.list_schedule(weekday, week)]
        return [AttrDict(slot) for slot in self._build_free_slots(weekday, busy_slots)]

    def recommend_for_task(self, task_id: int):
        task = self._find_by_id(self._tasks, task_id, "task")
        estimated_hours = float(task.get("estimated_hours") or 1.0)
        candidates = []
        for weekday in range(1, 8):
            for free_slot in self.get_free_slots(weekday, 1):
                slot_hours = self._hours_between(free_slot.get("start_time"), free_slot.get("end_time"))
                if slot_hours < min(estimated_hours, 1.0):
                    continue
                candidates.append(((task.get("priority", 2), weekday, -slot_hours), free_slot))
        recommendations = []
        for rank, (_score, slot) in enumerate(sorted(candidates, key=lambda item: item[0])[:4], start=1):
            data = slot.to_dict()
            data["title"] = f"方案 {rank}：课表空闲，适合推进“{task['title']}”"
            recommendations.append(AttrDict(data))
        return recommendations

    def arrange_task_at_slot(self, task_id: int, slot_data) -> None:
        task = self._find_by_id(self._tasks, task_id, "task")
        if hasattr(slot_data, "to_dict"):
            payload = slot_data.to_dict()
        elif isinstance(slot_data, dict):
            payload = dict(slot_data)
        else:
            payload = {
                "weekday": getattr(slot_data, "weekday", 1),
                "start_time": getattr(slot_data, "start_time", "19:00"),
                "end_time": getattr(slot_data, "end_time", "21:00"),
                "location": getattr(slot_data, "location", "自习区"),
            }
        payload["task_id"] = task_id
        payload["task_title"] = task.get("title", "未命名任务")
        payload["estimated_hours"] = task.get("estimated_hours", 1.0)
        payload.setdefault("week", 1)
        self._task_arrangements[task_id] = payload

    def cancel_task_arrangement(self, task_id: int) -> None:
        self._task_arrangements.pop(task_id, None)

    def get_task_arrangement(self, task_id: int):
        arrangement = self._task_arrangements.get(task_id)
        return AttrDict(arrangement) if arrangement else None

    def list_task_arrangements(self, week: int | None = None):
        arrangements = list(self._task_arrangements.values())
        if week is not None:
            arrangements = [item for item in arrangements if item.get("week", 1) == week]
        return [AttrDict(item) for item in arrangements]

    def generate_alerts(self):
        now = datetime.now()
        alerts = []
        for task in self._tasks:
            if task.get("status") == "done":
                continue
            due_time = task.get("due_time")
            if not isinstance(due_time, datetime):
                continue
            hours_left = (due_time - now).total_seconds() / 3600
            if hours_left < 0:
                alerts.append(self._alert(task, "overdue", f"{task['title']} 已逾期"))
            elif hours_left <= 24:
                alerts.append(self._alert(task, "urgent", f"{task['title']} 将在 24 小时内截止"))
            elif hours_left <= 72:
                alerts.append(self._alert(task, "warning", f"{task['title']} 将在 3 天内截止"))
        return alerts

    def list_all_alerts(self):
        return self.generate_alerts()

    def get_statistics(self):
        total = len(self._tasks)
        done = len([task for task in self._tasks if task.get("status") == "done"])
        return AttrDict({"total_tasks": total, "done_tasks": done, "completion_rate": done / total if total else 0.0, "active_tasks": total - done})

    def sync_from_teaching_site(self, username: str, password: str):
        return AttrDict({"success": True, "message": "演示模式：已加载本地 mock 课程、课表和 DDL。", "created": 3, "updated": 0, "skipped": 0})

    def ai_decompose_task(self, description: str, due_time: datetime) -> list[dict]:
        return [
            {"title": "明确提交要求", "estimated_hours": 0.5, "suggested_date": datetime.now()},
            {"title": "完成主体内容", "estimated_hours": 2.0, "suggested_date": datetime.now() + timedelta(days=1)},
            {"title": "检查格式并提交", "estimated_hours": 0.5, "suggested_date": due_time - timedelta(hours=3)},
        ]

    def ai_chat(self, conversation_id: int | None, user_msg: str, context_task_id: int | None = None):
        reply = f"演示模式回复：我会结合你的课表和任务给出建议。你刚才问的是：{user_msg}"
        return conversation_id or 1, reply

    def ai_generate_briefing(self) -> str:
        return "今日重点：优先处理高数和程序设计相关任务，并利用课表空闲段安排整块学习时间。"

    def ai_summarize_ddl(self, raw_text: str) -> str:
        text = (raw_text or "").strip()
        return text[:80] if text else "演示模式：暂无可摘要内容。"

    def set_deepseek_api_key(self, key: str) -> None:
        self._api_key = key

    def get_deepseek_api_key(self) -> str | None:
        return self._api_key or None

    def test_deepseek_api_key(self, key: str) -> bool:
        return bool(key.strip())

    def ai_is_available(self) -> bool:
        return True

    def ai_today_token_usage(self) -> int:
        return 0

    def _build_demo_schedule(self) -> list[dict]:
        slots = []
        add = slots.append
        add(self._slot(1, 101, "人工智能引论", "13:00", "14:50"))
        add(self._slot(1, 102, "汉英翻译理论与实践", "15:10", "17:00"))
        add(self._slot(1, 103, "习近平新时代中国特色社会主义思想概论", "18:40", "21:30"))
        add(self._slot(2, 104, "高等数学A", "08:00", "09:50"))
        add(self._slot(2, 105, "理想国讨论班", "20:40", "21:30", slot_type="custom"))
        add(self._slot(3, 106, "太极拳", "08:00", "09:50"))
        add(self._slot(3, 107, "程序设计实习", "10:10", "12:00"))
        add(self._slot(3, 108, "概率统计A", "15:10", "17:00", week_type="odd"))
        add(self._slot(3, 109, "高等数学A习题课", "18:40", "20:30"))
        add(self._slot(4, 104, "高等数学A", "10:10", "12:00"))
        add(self._slot(4, 108, "概率统计A", "15:10", "17:00", week_type="odd"))
        add(self._slot(5, 108, "概率统计A", "10:10", "12:00"))
        add(self._slot(5, 107, "程序设计实习", "15:10", "17:00", week_type="odd"))
        return slots

    def _slot(self, weekday: int, course_id: int | None, title: str, start_time: str, end_time: str, location: str = "", slot_type: str = "lecture", week_type: str = "all") -> dict:
        slot_id = getattr(self, "_bootstrap_slot_id", 1)
        self._bootstrap_slot_id = slot_id + 1
        return {"id": slot_id, "course_id": course_id, "title": title, "weekday": weekday, "start_time": start_time, "end_time": end_time, "location": location, "slot_type": slot_type, "start_week": 1, "end_week": 16, "week_type": week_type, "source": "demo"}

    def _course_name(self, course_id):
        for course in self._courses:
            if course["id"] == course_id:
                return course["name"]
        return None

    def _find_by_id(self, rows: list[dict], row_id: int, label: str) -> dict:
        for row in rows:
            if row.get("id") == row_id:
                return row
        raise ValueError(f"{label} {row_id} not found")

    def _occurs_in_week(self, slot: dict, week: int) -> bool:
        if not (slot.get("start_week", 1) <= week <= slot.get("end_week", 16)):
            return False
        week_type = slot.get("week_type", "all")
        if week_type == "odd":
            return week % 2 == 1
        if week_type == "even":
            return week % 2 == 0
        return True

    def _build_free_slots(self, weekday: int, busy_slots: list[dict]) -> list[dict]:
        day_start = time(8, 0)
        day_end = time(22, 0)
        busy_ranges = sorted((self._parse_time(slot["start_time"]), self._parse_time(slot["end_time"])) for slot in busy_slots)
        free_slots = []
        cursor = day_start
        for busy_start, busy_end in busy_ranges:
            if self._minutes_between(cursor, busy_start) >= 45:
                free_slots.append(self._free_slot(weekday, cursor, busy_start))
            if busy_end > cursor:
                cursor = busy_end
        if self._minutes_between(cursor, day_end) >= 45:
            free_slots.append(self._free_slot(weekday, cursor, day_end))
        return free_slots

    def _free_slot(self, weekday: int, start: time, end: time) -> dict:
        return {"id": None, "course_id": None, "title": "课表空闲时间", "weekday": weekday, "start_time": start.strftime("%H:%M"), "end_time": end.strftime("%H:%M"), "location": "建议：图书馆 / 自习室", "slot_type": "free", "start_week": 1, "end_week": 16, "week_type": "all"}

    def _alert(self, task: dict, level: str, message: str) -> AttrDict:
        return AttrDict({"id": f"task-{task['id']}-{level}", "task_id": task["id"], "target_type": "task", "level": level, "kind": "deadline", "message": message, "created_at": datetime.now(), "is_read": False})

    def _parse_time(self, value) -> time:
        if isinstance(value, time):
            return value
        if isinstance(value, datetime):
            return value.time()
        return datetime.strptime(str(value)[:5], "%H:%M").time()

    def _minutes_between(self, start: time, end: time) -> int:
        return int((datetime.combine(datetime.today(), end) - datetime.combine(datetime.today(), start)).total_seconds() / 60)

    def _hours_between(self, start, end) -> float:
        return self._minutes_between(self._parse_time(start), self._parse_time(end)) / 60
