import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.services.events import append_event
from app.domain.errors import LocalPDFError
from app.domain.validation import parse_page_ranges, validate_permutation
from app.infrastructure.db.models import (
    Document,
    DocumentVersion,
    Job,
    Operation,
    OperationInput,
    Original,
)
from app.settings import get_settings

SUPPORTED_OPERATIONS = {
    "merge",
    "split",
    "reorder",
    "rotate",
    "compress",
    "watermark",
    "redact",
    "ocr",
    "office_to_pdf",
}


def create_operation(
    session: Session,
    body: dict[str, Any],
    idempotency_key: str,
    correlation_id: str,
) -> tuple[Operation, Job, bool]:
    existing = session.scalar(select(Operation).where(Operation.idempotency_key == idempotency_key))
    if existing:
        job = session.scalar(select(Job).where(Job.operation_id == existing.id))
        if not job:
            raise LocalPDFError("INTERNAL_STATE", "İş kaydı bulunamadı.", status_code=500)
        return existing, job, True
    operation_type = str(body.get("type", ""))
    if operation_type not in SUPPORTED_OPERATIONS:
        raise LocalPDFError("INPUT_INVALID", "İşlem türü desteklenmiyor.")
    inputs = body.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise LocalPDFError("INPUT_INVALID", "En az bir kaynak dosya seçin.")
    resolved = [_resolve_input(session, item) for item in inputs]
    if operation_type == "merge" and len(resolved) < 2:
        raise LocalPDFError("INPUT_INVALID", "Birleştirme için en az iki PDF seçin.")
    if operation_type != "merge" and len(resolved) != 1:
        raise LocalPDFError("INPUT_INVALID", "Bu işlem tam olarak bir kaynak bekliyor.")
    parameters = body.get("parameters") or {}
    _validate_parameters(operation_type, parameters, resolved[0]["page_count"])
    document_id = resolved[0]["document_id"]
    document = session.get(Document, document_id)
    if not document or document.state != "active":
        raise LocalPDFError("DOCUMENT_EXPIRED", "Bu belge artık işlenemez.")
    operation = Operation(
        document_id=document_id,
        type=operation_type,
        parameters=parameters,
        idempotency_key=idempotency_key,
    )
    session.add(operation)
    session.flush()
    for position, item in enumerate(resolved):
        session.add(
            OperationInput(
                operation_id=operation.id,
                input_kind=item["kind"],
                input_id=item["id"],
                position=position,
                sha256=item["sha256"],
            )
        )
    job = Job(
        operation_id=operation.id,
        kind="operation",
        payload={"correlation_id": correlation_id},
        max_attempts=get_settings().job_max_attempts,
    )
    session.add(job)
    append_event(
        session,
        "operation.queued",
        "operation",
        operation.id,
        correlation_id,
        document_sha256=resolved[0]["sha256"],
        payload={"type": operation_type, "input_count": len(resolved)},
    )
    try:
        session.flush()
    except IntegrityError as exc:
        raise LocalPDFError(
            "IDEMPOTENCY_CONFLICT", "İşlem anahtarı başka bir istekte kullanıldı."
        ) from exc
    return operation, job, False


def _resolve_input(session: Session, item: object) -> dict[str, Any]:
    if not isinstance(item, dict) or item.get("kind") not in {"original", "version"}:
        raise LocalPDFError("INPUT_INVALID", "Kaynak türü geçersiz.")
    try:
        input_id = uuid.UUID(str(item.get("id")))
    except ValueError as exc:
        raise LocalPDFError("INPUT_INVALID", "Kaynak kimliği geçersiz.") from exc
    if item["kind"] == "original":
        source = session.get(Original, input_id)
        if not source:
            raise LocalPDFError("INPUT_NOT_FOUND", "Kaynak dosya bulunamadı.", status_code=404)
        return {
            "id": source.id,
            "kind": "original",
            "document_id": source.document_id,
            "sha256": source.sha256,
            "page_count": source.page_count,
            "media_type": source.document.media_type,
        }
    version = session.get(DocumentVersion, input_id)
    if not version or version.deleted_at:
        raise LocalPDFError("INPUT_NOT_FOUND", "Kaynak sürüm bulunamadı.", status_code=404)
    return {
        "id": version.id,
        "kind": "version",
        "document_id": version.document_id,
        "sha256": version.sha256,
        "page_count": version.page_count,
        "media_type": "application/pdf",
    }


def _validate_parameters(
    operation_type: str, parameters: dict[str, Any], page_count: int | None
) -> None:
    if operation_type == "office_to_pdf":
        return
    if page_count is None:
        raise LocalPDFError("INPUT_INVALID", "Bu işlem yalnız PDF kaynaklarında kullanılabilir.")
    if operation_type == "split" and parameters.get("mode", "range") == "range":
        parse_page_ranges(str(parameters.get("ranges", "")), page_count)
    elif operation_type == "reorder":
        validate_permutation([int(page) for page in parameters.get("pages", [])], page_count)
    elif operation_type == "rotate":
        if int(parameters.get("degrees", 0)) not in (90, 180, 270):
            raise LocalPDFError("INPUT_INVALID", "Döndürme açısı geçersiz.")
    elif operation_type == "watermark":
        if not str(parameters.get("text", "")).strip():
            raise LocalPDFError("INPUT_INVALID", "Filigran metni boş olamaz.")
