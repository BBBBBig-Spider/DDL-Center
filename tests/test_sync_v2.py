"""SyncManager 新流程 (v2) 单元测试。"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.managers.sync_manager import SyncManager
from app.models.sync_result import SyncResult
from app.parsers.ddl_parser import DDLParser


# ─── Fakes ──────────────────────────────────────────────────────────────


class _FakeRepo:
    def __init__(self):
        self.added: list = []
        self._next_id = 1
        self._by_ext: dict[str, object] = {}

    def add(self, item):
        item.id = self._next_id
        self._next_id += 1
        self.added.append(item)
        if getattr(item, "external_id", None):
            self._by_ext[item.external_id] = item
        return item.id

    def find_by_external_id(self, external_id: str):
        return self._by_ext.get(external_id)


class _FakeTaskRepo(_FakeRepo):
    def purge_hidden_overdue(self, _now):
        return 0


class _FakeCourseRepo(_FakeRepo):
    pass


class _FakeSyncRepo:
    def upsert_record(self, _record):
        return 1

    def get_record(self, _source_type, _external_id):
        return None


class _FakeAI:
    def __init__(
        self,
        *,
        available: bool = True,
        compress_reply: str | None = None,
        parse_reply: dict | None = None,
    ):
        self._available = available
        self._compress_reply = compress_reply
        self._parse_reply = parse_reply
        self.compress_calls: list[tuple[str, int]] = []
        self.parse_calls: list[str] = []

    def is_available(self) -> bool:
        return self._available

    def compress_description(self, text: str, max_chars: int = 120) -> str:
        self.compress_calls.append((text, max_chars))
        return self._compress_reply if self._compress_reply is not None else text[:max_chars]

    def parse_item_from_text(self, text: str) -> dict:
        self.parse_calls.append(text)
        if self._parse_reply is None:
            raise RuntimeError("no scripted parse reply")
        return self._parse_reply


class _FakeAuth:
    def login(self, _u, _p):
        return object()


class _FakeClient:
    def __init__(self, raw: str, warnings: list[str] | None = None):
        self._raw = raw
        self._last_warnings = list(warnings or [])

    def fetch_current_semester_ddl(self, _session) -> str:
        return self._raw


def _make_sm(*, raw_html, ai=None, ai_fallback_enabled=True, parser=None):
    sm = SyncManager(
        auth_client=_FakeAuth(),
        teaching_site_client=_FakeClient(raw_html),
        ddl_parser=parser or DDLParser(),
        schedule_parser=None,
        exam_parser=None,
        task_repository=_FakeTaskRepo(),
        course_repository=_FakeCourseRepo(),
        schedule_repository=None,
        exam_repository=_FakeRepo(),
        sync_repository=_FakeSyncRepo(),
        ai_assistant_manager=ai,
        ai_fallback_enabled=ai_fallback_enabled,
    )
    return sm


def _wrap(course_external_id: str, course_name: str, body: str) -> str:
    return (
        f'<div class="ddl-course-page" data-course-name="{course_name}" '
        f'data-course-external-id="{course_external_id}">{body}</div>'
    )


def _li(li_id: str, title: str, body: str) -> str:
    return (
        f'<li id="contentListItem:{li_id}" class="liItem">'
        f"<h3>{title}</h3><div>{body}</div></li>"
    )


# ─── Tests ──────────────────────────────────────────────────────────────


def test_filters_to_current_semester_only():
    """fetch_current_semester_ddl 只返回当前学期 wrapper；老学期 wrapper 不应被解析。"""
    future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    current = _wrap(
        "CUR-2026",
        "当前学期课",
        _li("now-1", "本学期作业", f"结束时间: {future}"),
    )
    history = _wrap(
        "OLD-2024",
        "历史课",
        _li("old-1", "老学期作业", f"结束时间: {future}"),
    )
    # client 只返回 current（模拟 fetch_current_semester_ddl 的过滤效果）
    sm = _make_sm(raw_html=current)
    result = sm.sync_from_teaching_site("u", "p")

    assert result.tasks_new == 1
    assert sm.task_repository.added[0].external_id.startswith("CUR-2026:")

    # 反向检查：parser 解析全量 HTML（含 history）确实能看到两条
    items = DDLParser().parse_assignment_items(current + history)
    assert len(items) == 2


def test_drops_overdue_strictly():
    past = "2024-01-01 09:00:00"
    future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    html = _wrap(
        "C1",
        "课1",
        _li("a", "已过期", f"结束时间: {past}")
        + _li("b", "未来", f"结束时间: {future}"),
    )
    sm = _make_sm(raw_html=html)
    result = sm.sync_from_teaching_site("u", "p")

    assert result.tasks_new == 1
    assert result.tasks_dropped_overdue == 1
    assert sm.task_repository.added[0].title == "未来"


def test_short_description_passes_through():
    future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    short = "短描述说明文档"  # 7 字符 ≤ 120
    html = _wrap(
        "C1",
        "课1",
        _li("a", "作业 A", f"{short} 结束时间: {future}"),
    )
    ai = _FakeAI(available=True, compress_reply="不应被调用")
    sm = _make_sm(raw_html=html, ai=ai)
    result = sm.sync_from_teaching_site("u", "p")

    assert result.tasks_new == 1
    written = sm.task_repository.added[0]
    assert short in written.description
    assert ai.compress_calls == []  # 短描述不调 AI


def test_long_description_calls_ai_compressor():
    future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    long_desc = "x" * 300
    html = _wrap(
        "C1",
        "课1",
        _li("a", "作业 A", f"{long_desc} 结束时间: {future}"),
    )
    ai = _FakeAI(available=True, compress_reply="AI摘要")
    sm = _make_sm(raw_html=html, ai=ai)
    result = sm.sync_from_teaching_site("u", "p")

    assert result.tasks_new == 1
    written = sm.task_repository.added[0]
    assert written.description == "AI摘要"
    assert len(ai.compress_calls) == 1


def test_no_end_time_falls_back_to_ai_then_writes():
    body = _li("a", "无结束时间作业", "记得提交报告")
    html = _wrap("C1", "课1", body)
    ai = _FakeAI(
        available=True,
        parse_reply={
            "type": "task",
            "payload": {
                "title": "提交报告",
                "due_time": datetime(2099, 6, 30, 23, 59),
                "description": "",
                "estimated_hours": 2.0,
                "priority": 2,
                "status": "todo",
            },
        },
    )
    sm = _make_sm(raw_html=html, ai=ai)
    result = sm.sync_from_teaching_site("u", "p")

    assert result.ai_recovered == 1
    assert len(sm.task_repository.added) == 1
    assert sm.task_repository.added[0].external_id.startswith("ai-rec-")


def test_ai_compressor_unavailable_truncates():
    future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    long_desc = "y" * 200
    html = _wrap(
        "C1",
        "课1",
        _li("a", "作业 A", f"{long_desc} 结束时间: {future}"),
    )
    ai = _FakeAI(available=False)  # AI 不可用
    sm = _make_sm(raw_html=html, ai=ai)
    result = sm.sync_from_teaching_site("u", "p")

    assert result.tasks_new == 1
    written = sm.task_repository.added[0]
    assert len(written.description) <= 120
    assert written.description.endswith("…")
    assert ai.compress_calls == []  # is_available=False，不调
