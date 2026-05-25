"""app/repositories/sync_repository.py"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app.database.database_manager import DatabaseManager
from app.models.sync_record import SyncRecord


class SyncRepository:
    """sync_records 表的增删改查。增量同步的外部 ID -> 本地 ID 映射。"""

    VALID_STATUSES = {"new", "updated", "unchanged", "deleted"}

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @staticmethod
    def _is_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _validate_record(self, record: SyncRecord, *, require_id: bool = False) -> None:
        if not isinstance(record, SyncRecord):
            raise TypeError("record must be a SyncRecord")

        if require_id and record.id is None:
            raise ValueError("record.id is required")

        if record.id is not None and not self._is_int(record.id):
            raise TypeError("record.id must be int or None")

        if not isinstance(record.source_type, str) or not record.source_type:
            raise ValueError("record.source_type cannot be empty")

        if not isinstance(record.external_id, str) or not record.external_id:
            raise ValueError("record.external_id cannot be empty")

        if not isinstance(record.local_type, str) or not record.local_type:
            raise ValueError("record.local_type cannot be empty")

        if not self._is_int(record.local_id):
            raise TypeError("record.local_id must be int")

        if record.raw_hash is not None and not isinstance(record.raw_hash, str):
            raise TypeError("record.raw_hash must be str or None")

        if not isinstance(record.last_seen_at, datetime):
            raise TypeError("record.last_seen_at must be datetime")

        if not isinstance(record.status, str) or record.status not in self.VALID_STATUSES:
            raise ValueError(
                f"record.status must be one of: {', '.join(sorted(self.VALID_STATUSES))}"
            )

    def _row_to_record(self, row) -> SyncRecord:
        return SyncRecord(
            id=row["id"],
            source_type=row["source_type"],
            external_id=row["external_id"],
            local_type=row["local_type"],
            local_id=row["local_id"],
            raw_hash=row["raw_hash"],
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
            status=row["status"],
        )

    def upsert(self, record: SyncRecord) -> int:
        """按 (source_type, external_id) 唯一约束执行 upsert，返回行 id。"""
        self._validate_record(record)
        conn = self.db_manager.get_connection()

        with conn:
            cursor = conn.execute(
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
                    local_type = excluded.local_type,
                    local_id = excluded.local_id,
                    raw_hash = excluded.raw_hash,
                    last_seen_at = excluded.last_seen_at,
                    status = excluded.status
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

        cursor2 = conn.execute(
            """
            SELECT id FROM sync_records
            WHERE source_type = ? AND external_id = ?
            """,
            (record.source_type, record.external_id),
        )
        row = cursor2.fetchone()
        record.id = row["id"]
        return record.id

    def find(self, source_type: str, external_id: str) -> Optional[SyncRecord]:
        if not isinstance(source_type, str) or not source_type:
            raise ValueError("source_type cannot be empty")
        if not isinstance(external_id, str) or not external_id:
            raise ValueError("external_id cannot be empty")

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
        return self._row_to_record(row) if row else None

    def list_by_source(self, source_type: str) -> List[SyncRecord]:
        if not isinstance(source_type, str) or not source_type:
            raise ValueError("source_type cannot be empty")

        conn = self.db_manager.get_connection()
        cursor = conn.execute(
            """
            SELECT *
            FROM sync_records
            WHERE source_type = ?
            ORDER BY last_seen_at DESC
            """,
            (source_type,),
        )
        return [self._row_to_record(r) for r in cursor.fetchall()]

    def delete(self, source_type: str, external_id: str) -> bool:
        if not isinstance(source_type, str) or not source_type:
            raise ValueError("source_type cannot be empty")
        if not isinstance(external_id, str) or not external_id:
            raise ValueError("external_id cannot be empty")

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
