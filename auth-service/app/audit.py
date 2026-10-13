"""
Append-only audit log writer.  Never logs credentials or secrets.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app import clock
from app.models import AuditLog


async def write(
    db: AsyncSession,
    event_type: str,
    subject_id: int,
    subject_type: str,
    source_ip: Optional[str] = None,
    vendor_id: Optional[int] = None,
    device_uuid_hash: Optional[str] = None,
    action_detail: Optional[dict] = None,
) -> None:
    entry = AuditLog(
        event_type=event_type,
        subject_id=subject_id,
        subject_type=subject_type,
        vendor_id=vendor_id,
        device_uuid_hash=device_uuid_hash,
        action_detail=action_detail or {},
        timestamp=clock.now_naive(),
        source_ip=source_ip,
    )
    db.add(entry)
    # caller is responsible for committing
