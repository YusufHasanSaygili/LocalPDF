import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.infrastructure.db.models import Event


def append_event(
    session: Session,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    correlation_id: str,
    *,
    document_sha256: str | None = None,
    output_sha256: str | None = None,
    payload: dict[str, Any] | None = None,
) -> Event:
    event = Event(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        correlation_id=correlation_id,
        document_sha256=document_sha256,
        output_sha256=output_sha256,
        payload=payload or {},
    )
    session.add(event)
    return event
