from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


__all__ = ["SyncRecord"]


@dataclass
class SyncRecord:
    source_type: str        # ddl / schedule / course
    external_id: str        # 外部来源 ID
    local_type: str         # task / schedule_slot / course
    local_id: int           # 本地对象 ID
    raw_hash: str           # 原始内容哈希
    last_seen_at: datetime  # 上次同步时间
    status: str             # new / updated / unchanged / deleted
    id: int | None = None   # 本地数据库 ID

