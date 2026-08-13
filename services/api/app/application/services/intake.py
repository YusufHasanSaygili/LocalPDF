import hashlib
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.services.events import append_event
from app.domain.errors import LocalPDFError
from app.domain.validation import sanitize_filename
from app.infrastructure.db.models import Document, Job, Original
from app.infrastructure.storage import LocalStorage
from app.infrastructure.tools.pdf import inspect_pdf
from app.settings import get_settings

MEDIA_BY_EXTENSION = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


async def ingest_upload(
    session: Session,
    upload: UploadFile,
    correlation_id: str,
    expires_at: datetime | None = None,
) -> tuple[Document, Original, Job | None, uuid.UUID | None]:
    settings = get_settings()
    display_name, safe_name = sanitize_filename(upload.filename or "")
    extension = display_name.rsplit(".", 1)[-1].lower() if "." in display_name else ""
    if extension not in MEDIA_BY_EXTENSION:
        raise LocalPDFError(
            "UNSUPPORTED_MEDIA_TYPE", "Yalnız PDF, DOCX, XLSX ve PPTX kabul edilir."
        )
    storage = LocalStorage()
    temp_path = storage.resolve(f"tmp/upload-{uuid.uuid4()}.part", must_exist=False)
    digest = hashlib.sha256()
    size = 0
    try:
        with temp_path.open("xb") as target:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise LocalPDFError("FILE_TOO_LARGE", "Dosya yükleme limitini aşıyor.")
                digest.update(chunk)
                target.write(chunk)
        _validate_magic(temp_path, extension)
        page_count: int | None = None
        features: dict[str, object] = {"warnings": ["office_layout_may_change"]}
        if extension == "pdf":
            page_count, features = inspect_pdf(temp_path, settings.max_pdf_pages)
        duplicate = session.scalar(select(Original.id).where(Original.sha256 == digest.hexdigest()))
        document = Document(
            display_name=display_name,
            safe_name=safe_name,
            media_type=MEDIA_BY_EXTENSION[extension],
            expires_at=expires_at,
        )
        session.add(document)
        session.flush()
        stored = storage.publish_original(temp_path, document.id, digest.hexdigest(), extension)
        original = Original(
            document_id=document.id,
            relative_path=stored.relative_path,
            sha256=stored.sha256,
            byte_size=stored.byte_size,
            page_count=page_count,
            detected_features=features,
        )
        session.add(original)
        session.flush()
        append_event(
            session,
            "document.uploaded",
            "document",
            document.id,
            correlation_id,
            document_sha256=original.sha256,
            payload={
                "media_type": document.media_type,
                "byte_size": original.byte_size,
                "page_count": page_count,
                "duplicate_detected": duplicate is not None,
            },
        )
        job = None
        if extension == "pdf":
            job = Job(
                kind="preview",
                payload={"source_kind": "original", "source_id": str(original.id)},
                max_attempts=settings.job_max_attempts,
            )
            session.add(job)
        return document, original, job, duplicate
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _validate_magic(path: Path, extension: str) -> None:
    with path.open("rb") as source:
        head = source.read(8)
    if extension == "pdf":
        if not head.startswith(b"%PDF-"):
            raise LocalPDFError("UNSUPPORTED_MEDIA_TYPE", "Dosya içeriği geçerli bir PDF değil.")
        return
    if not head.startswith(b"PK"):
        raise LocalPDFError(
            "UNSUPPORTED_MEDIA_TYPE", "Office dosyasının içeriği uzantıyla eşleşmiyor."
        )
    expected_prefix = {"docx": "word/", "xlsx": "xl/", "pptx": "ppt/"}[extension]
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if "[Content_Types].xml" not in names or not any(
                name.startswith(expected_prefix) for name in names
            ):
                raise LocalPDFError(
                    "UNSUPPORTED_MEDIA_TYPE", "Office dosyasının içeriği uzantıyla eşleşmiyor."
                )
    except zipfile.BadZipFile as exc:
        raise LocalPDFError("UNSUPPORTED_MEDIA_TYPE", "Office dosyası açılamadı.") from exc
