from typing import Any

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.api.serializers import job_json
from app.application.services.operations import create_operation
from app.domain.errors import LocalPDFError
from app.infrastructure.db.session import get_db

router = APIRouter(tags=["operations"])


@router.post("/operations", status_code=status.HTTP_202_ACCEPTED)
def operation_create(
    body: dict[str, Any],
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    if not idempotency_key or len(idempotency_key) > 200:
        raise LocalPDFError("IDEMPOTENCY_REQUIRED", "Geçerli bir Idempotency-Key gereklidir.")
    operation, job, replayed = create_operation(
        session, body, idempotency_key, request.state.correlation_id
    )
    session.commit()
    return {
        "operation": {"id": str(operation.id), "type": operation.type},
        "job": job_json(job),
        "replayed": replayed,
    }
