"""app/repositories/sync_repository.py"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.database.database_manager import DatabaseManager
from app.models.sync_record import SyncRecord


class SyncRepository:
    """sync_records 表的访问层。
    提供 get_record / upsert_record / list_recent_records / delete。

    sync_records 用 (source_type, external_id) UNIQUE 约束去重，
    一个外部对象只对应一条记录。Day 20 的"按 external_id + raw_hash 去重"
    依赖此表。
    """

    VALID_SOURCE_TYPES = {"ddl", "schedule", "course", "exam"}
    VALID_LOCAL_TYPES = {"task", "schedule_slot", "course", "exam"}
    VALID_STATUSES = {"new", "updated", "unchanged", "deleted"}

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @staticmethod
    def _is_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _validate_record(self, record: SyncRecord) -> None:
        if not isinstance(record, SyncRecord):
            raise TypeError("record must be a SyncRecord")

        if record.id is not None and not self._is_int(record.id):
            raise TypeError("record.id must be int or None")

        if not isinstance(record.source_type, str):
            raise TypeError("record.source_type must be str")
        if record.source_type not in self.VALID_SOURCE_TYPES:
            raise ValueError(
                f"record.source_type must be one of: "
                f"{', '.join(sorted(self.VALID_SOURCE_TYPES))}"
            )

        if not isinstance(record.external_id, str) or not record.external_id:
            raise ValueError("record.external_id must be a non-empty str")

        if not isinstance(record.local_type, str):
            raise TypeError("record.local_type must be str")
        if record.local_type not in self.VALID_LOCAL_TYPES:
            raise ValueError(
                f"record.local_type must be one of: "
                f"{', '.join(sorted(self.VALID_LOCAL_TYPES))}"
            )

        if not self._is_int(record.local_id):
            raise TypeError("record.local_id must be int")

        if not isinstance(record.raw_hash, str):
            raise TypeError("record.raw_hash must be str")

        if not isinstance(record.last_seen_at, datetime):
            raise TypeError("record.last_seen_at must be datetime")

        if not isinstance(record.status, str):
            raise TypeError("record.status must be str")
        if record.status not in self.VALID_STATUSES:
            raise ValueError(
                f"record.status must be one of: "
                f"{', '.join(sorted(self.VALID_STATUSES))}"
            )

    def _validate_source_type(self, source_type: str) -> None:
        if not isinstance(source_type, str):
            raise TypeError("source_type must be str")
        if source_type not in self.VALID_SOURCE_TYPES:
            raise ValueError(
                f"source_type must be one of: "
                f"{', '.join(sorted(self.VALID_SOURCE_TYPES))}"
            )

    def _row_to_record(self, row) -> SyncRecord:
        return SyncRecord(
            id=row["id"],
            source_type=row["source_type"],
            external_id=row["external_id"],
            local_type=row["local_type"],
            local_id=row["local_id"],
            raw_hash=row["raw_hash"] or "",
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
            status=row["status"],
        )

    # ─── 查 ────────────────────────────────────────────────────

    def get_record(self, source_type: str, external_id: str) -> Optional[SyncRecord]:
        """按 (source_type, external_id) 复合键查询，找不到返回 None。"""
        self._validate_source_type(source_type)
        if not isinstance(external_id, str) or not external_id:
            raise ValueError("external_id must be a non-empty str")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM sync_records
            WHERE source_type = ? AND external_id = ?
            """,
            (source_type, external_id),
        )

        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_recent_records(self, limit: int = 100) -> List[SyncRecord]:
        """按 last_seen_at 倒序返回最近若干条同步记录。"""
        if not self._is_int(limit):
            raise TypeError("limit must be int")
        if limit < 1:
            raise ValueError("limit must be >= 1")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM sync_records
            ORDER BY last_seen_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    # ─── 写 ────────────────────────────────────────────────────

    def upsert_record(self, record: SyncRecord) -> int:
        """按 (source_type, external_id) UNIQUE 键 upsert，返回该行的 id。

        - 不存在 → INSERT 新行，返回 lastrowid
        - 已存在 → UPDATE 除 source_type/external_id 之外的字段，返回已存在的 id
        """
        self._validate_record(record)

        conn = self.db_manager.get_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO sync_records (
                    source_type,
                    external_id,
                    local_type,
                    local_id,
                    raw_hash,
                    last_seen_at,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_type, external_id) DO UPDATE SET
                    local_type   = excluded.local_type,
                    local_id     = excluded.local_id,
                    raw_hash     = excluded.raw_hash,
                    last_seen_at = excluded.last_seen_at,
                    status       = excluded.status
                """,
                (
                    record.source_type,
                    record.external_id,
                    record.local_type,
                    record.local_id,
                    record.raw_hash,
                    record.last_seen_at.isoformat(),
                    record.status,
                ),
            )

            # 拿到该行的 id（不论新增还是更新都通过复合键再 SELECT 一次）
            cursor = conn.execute(
                """
                SELECT id FROM sync_records
                WHERE source_type = ? AND external_id = ?
                """,
                (record.source_type, record.external_id),
            )
            row = cursor.fetchone()

        return row["id"]

    # ─── 删 ────────────────────────────────────────────────────

    def delete(self, source_type: str, external_id: str) -> bool:
        """按 (source_type, external_id) 删除一条记录。返回 True 表示删除成功。"""
        self._validate_source_type(source_type)
        if not isinstance(external_id, str) or not external_id:
            raise ValueError("external_id must be a non-empty str")

        conn = self.db_manager.get_connection()
        with conn:
            cursor = conn.execute(
                """
                DELETE FROM sync_records
                WHERE source_type = ? AND external_id = ?
                """,
                (source_type, external_id),
            )

        return cursor.rowcount > 0
