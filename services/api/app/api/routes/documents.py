import json
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.serializers import document_json, event_json, preview_json
from app.application.services.events import append_event
from app.application.services.intake import ingest_upload
from app.domain.errors import LocalPDFError
from app.infrastructure.db.models import (
    Document,
    DocumentVersion,
    Event,
    Job,
    Operation,
    Original,
    Preview,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.storage import LocalStorage
from app.settings import get_settings

router = APIRouter(tags=["documents"])


def document_query() -> Any:
    return select(Document).options(
        selectinload(Document.original), selectinload(Document.versions)
    )


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    expires_at: datetime | None = Form(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    if not idempotency_key:
        raise LocalPDFError("IDEMPOTENCY_REQUIRED", "Geçerli bir Idempotency-Key gereklidir.")
    document, original, preview_job, duplicate = await ingest_upload(
        session, file, request.state.correlation_id, expires_at
    )
    session.commit()
    return {
        "document": document_json(document, detail=True),
        "preview_job_id": str(preview_job.id) if preview_job else None,
        "duplicate_of_original_id": str(duplicate) if duplicate else None,
    }


@router.get("/documents")
def list_documents(session: Session = Depends(get_db)) -> dict[str, Any]:
    documents = session.scalars(
        document_query().order_by(Document.created_at.desc()).limit(100)
    ).all()
    return {"items": [document_json(document) for document in documents], "next_cursor": None}


@router.get("/documents/{document_id}")
def get_document(document_id: uuid.UUID, session: Session = Depends(get_db)) -> dict[str, Any]:
    document = session.scalar(document_query().where(Document.id == document_id))
    if not document:
        raise LocalPDFError("DOCUMENT_NOT_FOUND", "Belge bulunamadı.", status_code=404)
    return document_json(document, detail=True)


@router.patch("/documents/{document_id}/expiry")
def update_expiry(
    document_id: uuid.UUID,
    body: dict[str, Any],
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    if not idempotency_key:
        raise LocalPDFError("IDEMPOTENCY_REQUIRED", "Geçerli bir Idempotency-Key gereklidir.")
    document = session.get(Document, document_id)
    if not document:
        raise LocalPDFError("DOCUMENT_NOT_FOUND", "Belge bulunamadı.", status_code=404)
    value = body.get("expires_at")
    document.expires_at = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
    append_event(
        session,
        "document.expiry_changed",
        "document",
        document.id,
        request.state.correlation_id,
        payload={"expires_at": document.expires_at.isoformat() if document.expires_at else None},
    )
    session.commit()
    return {"id": str(document.id), "expires_at": document.expires_at}


@router.delete("/documents/{document_id}", status_code=status.HTTP_202_ACCEPTED)
def delete_document(
    document_id: uuid.UUID,
    request: Request,
    confirmation: str | None = Header(default=None, alias="X-Confirm-Delete"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    if confirmation != "delete" or not idempotency_key:
        raise LocalPDFError("DELETE_CONFIRMATION_REQUIRED", "Silme işlemini açıkça onaylayın.")
    document = session.get(Document, document_id)
    if not document:
        raise LocalPDFError("DOCUMENT_NOT_FOUND", "Belge bulunamadı.", status_code=404)
    if document.state == "deleted":
        return {"state": "deleted", "job_id": None, "replayed": True}
    job = Job(
        kind="delete",
        payload={"document_id": str(document.id), "correlation_id": request.state.correlation_id},
        max_attempts=get_settings().job_max_attempts,
    )
    session.add(job)
    session.commit()
    return {"state": "queued", "job_id": str(job.id), "replayed": False}


@router.get("/documents/{document_id}/export", status_code=status.HTTP_202_ACCEPTED)
def export_document(
    document_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    document = session.get(Document, document_id)
    if not document:
        raise LocalPDFError("DOCUMENT_NOT_FOUND", "Belge bulunamadı.", status_code=404)
    job = Job(
        kind="export",
        payload={"document_id": str(document.id), "correlation_id": request.state.correlation_id},
        max_attempts=get_settings().job_max_attempts,
    )
    session.add(job)
    session.commit()
    return {"job_id": str(job.id)}


@router.get("/documents/{document_id}/events")
def document_events(document_id: uuid.UUID, session: Session = Depends(get_db)) -> dict[str, Any]:
    operation_ids = session.scalars(
        select(Operation.id).where(Operation.document_id == document_id)
    ).all()
    event_filter = Event.aggregate_id == document_id
    if operation_ids:
        event_filter = or_(event_filter, Event.aggregate_id.in_(operation_ids))
    events = session.scalars(
        select(Event).where(event_filter).order_by(Event.occurred_at, Event.id)
    ).all()
    return {"items": [event_json(event) for event in events]}


@router.get("/documents/{document_id}/audit-export")
def audit_export(document_id: uuid.UUID, session: Session = Depends(get_db)) -> StreamingResponse:
    payload = document_events(document_id, session)
    lines = "".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in payload["items"]
    )
    return StreamingResponse(
        iter([lines.encode("utf-8")]),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="audit-{document_id}.jsonl"'},
    )


@router.get("/sources/{kind}/{source_id}/previews")
def list_previews(
    kind: str, source_id: uuid.UUID, session: Session = Depends(get_db)
) -> dict[str, Any]:
    if kind not in {"original", "version"}:
        raise LocalPDFError("INPUT_INVALID", "Önizleme kaynak türü geçersiz.")
    previews = session.scalars(
        select(Preview)
        .where(Preview.source_kind == kind, Preview.source_id == source_id)
        .order_by(Preview.page_number)
    ).all()
    return {"items": [preview_json(preview) for preview in previews]}


@router.get("/previews/{preview_id}/content")
def preview_content(preview_id: uuid.UUID, session: Session = Depends(get_db)) -> FileResponse:
    preview = session.get(Preview, preview_id)
    if not preview:
        raise LocalPDFError("PREVIEW_NOT_FOUND", "Önizleme bulunamadı.", status_code=404)
    path = LocalStorage().resolve(preview.relative_path)
    return FileResponse(
        path, media_type="image/webp", headers={"Cache-Control": "private, max-age=3600"}
    )


@router.get("/originals/{original_id}/download")
def download_original(original_id: uuid.UUID, session: Session = Depends(get_db)) -> FileResponse:
    original = session.get(Original, original_id)
    if not original or original.document.state != "active":
        raise LocalPDFError("DOCUMENT_NOT_FOUND", "Dosya indirilemiyor.", status_code=404)
    return _download(
        LocalStorage().resolve(original.relative_path),
        original.document.safe_name,
        original.document.media_type,
    )


@router.get("/versions/{version_id}/download")
def download_version(version_id: uuid.UUID, session: Session = Depends(get_db)) -> FileResponse:
    version = session.get(DocumentVersion, version_id)
    if not version or version.deleted_at or version.document.state != "active":
        raise LocalPDFError("DOCUMENT_NOT_FOUND", "Dosya indirilemiyor.", status_code=404)
    name = f"{version.document.safe_name.rsplit('.', 1)[0]}-v{version.version_number}.pdf"
    return _download(LocalStorage().resolve(version.relative_path), name)


@router.get("/exports/{job_id}/download")
def download_export(job_id: uuid.UUID, session: Session = Depends(get_db)) -> FileResponse:
    job = session.get(Job, job_id)
    relative_path = job.payload.get("export_relative_path") if job else None
    if not job or job.state != "succeeded" or not relative_path:
        raise LocalPDFError("EXPORT_NOT_READY", "Dışa aktarma henüz hazır değil.", status_code=404)
    return _download(
        LocalStorage().resolve(relative_path),
        str(job.payload.get("export_filename") or f"localpdf-export-{job_id}.zip"),
        str(job.payload.get("export_media_type") or "application/zip"),
    )


def _download(path: Any, filename: str, media_type: str = "application/pdf") -> FileResponse:
    ascii_name = "".join(character if ord(character) < 128 else "_" for character in filename)
    disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Content-Disposition": disposition,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
