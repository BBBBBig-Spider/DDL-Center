from __future__ import annotations

from datetime import datetime, timedelta


class AttrDict:
    """Small object/dict bridge used by the GUI fallback facade."""

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


class DemoFacade:
    """In-memory facade with the subset of AppFacade used by the GUI."""

    def __init__(self):
        now = datetime.now()
        self._courses = [
            {"id": 101, "name": "Advanced Mathematics"},
            {"id": 202, "name": "Programming Practice"},
            {"id": 303, "name": "College Physics"},
        ]
        self._tasks = [
            {
                "id": 1,
                "title": "Math problem set 1-5",
                "course_id": 101,
                "course_name": "Advanced Mathematics",
                "description": "Submit before Friday.",
                "due_time": now + timedelta(hours=8),
                "estimated_hours": 2,
                "status": "todo",
                "priority": 1,
            },
            {
                "id": 2,
                "title": "Programming assignment",
                "course_id": 202,
                "course_name": "Programming Practice",
                "description": "Finish the first project milestone.",
                "due_time": now + timedelta(days=2),
                "estimated_hours": 8,
                "status": "doing",
                "priority": 2,
            },
            {
                "id": 3,
                "title": "Physics lab report",
                "course_id": 303,
                "course_name": "College Physics",
                "description": "Write the measurement analysis.",
                "due_time": now + timedelta(days=5),
                "estimated_hours": 3,
                "status": "done",
                "priority": 3,
            },
        ]

    def list_courses(self):
        return [AttrDict(course) for course in self._courses]

    def list_tasks(self, filters=None):
        filters = filters or {}
        tasks = list(self._tasks)
        status = filters.get("status")
        course_id = filters.get("course_id")
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        if course_id is not None:
            tasks = [task for task in tasks if task.get("course_id") == course_id]
        return [AttrDict(task) for task in sorted(tasks, key=lambda t: t["due_time"])]

    def create_task(self, data):
        next_id = max((task["id"] for task in self._tasks), default=0) + 1
        payload = dict(data)
        payload["id"] = next_id
        payload.setdefault("status", "todo")
        payload["course_name"] = self._course_name(payload.get("course_id"))
        self._tasks.append(payload)
        return next_id

    def update_task(self, task_id, data):
        for task in self._tasks:
            if task["id"] == task_id:
                task.update(data)
                task["course_name"] = self._course_name(task.get("course_id"))
                return
        raise ValueError(f"task {task_id} not found")

    def delete_task(self, task_id):
        before = len(self._tasks)
        self._tasks = [task for task in self._tasks if task["id"] != task_id]
        if len(self._tasks) == before:
            raise ValueError(f"task {task_id} not found")

    def mark_task_done(self, task_id):
        self.update_task(task_id, {"status": "done"})

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
                alerts.append(
                    {"level": "overdue", "kind": "deadline", "message": f"{task['title']} is overdue."}
                )
            elif hours_left <= 24:
                alerts.append(
                    {"level": "urgent", "kind": "deadline", "message": f"{task['title']} is due within 24 hours."}
                )
            elif hours_left <= 72:
                alerts.append(
                    {"level": "warning", "kind": "deadline", "message": f"{task['title']} is due within 3 days."}
                )
        return alerts

    def _course_name(self, course_id):
        for course in self._courses:
            if course["id"] == course_id:
                return course["name"]
        return None
