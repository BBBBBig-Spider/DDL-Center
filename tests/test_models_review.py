from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_schedule_slot_imports_as_package() -> None:
    import app.models.schedule_slot  # noqa: F401


def test_alert_created_at_uses_fresh_default() -> None:
    from app.models.alert import Alert

    first = Alert(task_id=1, level="info", kind="deadline", message="first")
    time.sleep(0.001)
    second = Alert(task_id=2, level="info", kind="deadline", message="second")

    assert first.created_at != second.created_at


@pytest.mark.parametrize(
    ("model_name", "method_name", "instance_args"),
    [
        ("task", "is_done", {"title": "t", "due_time": __import__("datetime").datetime.now()}),
        ("course", "display_name", {"name": "c"}),
    ],
)
def test_model_methods_are_implemented(model_name: str, method_name: str, instance_args: dict) -> None:
    module = __import__(f"app.models.{model_name}", fromlist=["*"])
    cls = getattr(module, "".join(part.capitalize() for part in model_name.split("_")))
    instance = cls(**instance_args)

    getattr(instance, method_name)()


def test_schema_allows_model_alert_without_task_id_for_global_alerts() -> None:
    from app.models.alert import Alert

    Alert(task_id=None, level="warning", kind="overload", message="busy day")


def test_sync_record_local_type_matches_schema_text_column() -> None:
    from app.models.sync_record import SyncRecord
    from datetime import datetime

    record = SyncRecord(
        source_type="ddl",
        external_id="external-1",
        local_type="task",
        local_id=1,
        raw_hash="hash",
        last_seen_at=datetime.now(),
        status="new",
    )

    assert isinstance(record.local_type, str)


def test_schema_can_be_created_in_sqlite_memory() -> None:
    schema = (ROOT / "app" / "database" / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(schema)
    finally:
        conn.close()
