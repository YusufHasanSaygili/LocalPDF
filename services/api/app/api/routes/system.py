import shutil
import subprocess
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.serializers import job_json
from app.domain.errors import LocalPDFError
from app.infrastructure.db.models import Job
from app.infrastructure.db.session import get_db
from app.infrastructure.storage import LocalStorage
from app.infrastructure.tools.system import tool_version
from app.settings import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "localpdf-api"}


@router.get("/ready")
def ready(session: Session = Depends(get_db)) -> dict[str, Any]:
    session.execute(text("SELECT 1"))
    storage = LocalStorage()
    probe = storage.resolve("tmp/.ready", must_exist=False)
    probe.touch()
    probe.unlink()
    capabilities = capabilities_payload()
    required = capabilities["tools"]["pikepdf"]["available"]
    return {"status": "ready" if required else "degraded", "store": "ready", **capabilities}


@router.get("/system/capabilities")
def capabilities() -> dict[str, Any]:
    return capabilities_payload()


def capabilities_payload() -> dict[str, Any]:
    settings = get_settings()
    return {
        "app_version": settings.app_version,
        "local_only": True,
        "telemetry": False,
        "limits": {
            "max_upload_bytes": settings.max_upload_bytes,
            "max_pdf_pages": settings.max_pdf_pages,
        },
        "tools": {
            "pikepdf": {"available": True, "version": _pikepdf_version()},
            "libreoffice": {
                "available": bool(shutil.which("libreoffice") or shutil.which("soffice")),
                "version": tool_version("libreoffice", ["--version"]),
            },
            "poppler": {
                "available": bool(shutil.which("pdftoppm")),
                "version": tool_version("pdftoppm", ["-v"]),
            },
            "tesseract": {
                "available": bool(shutil.which("tesseract")),
                "version": tool_version("tesseract", ["--version"]),
                "languages": _tesseract_languages(),
            },
        },
        "signature_delivery": "smtp" if settings.smtp_enabled else "manual",
    }


@router.post("/maintenance/backups", status_code=status.HTTP_202_ACCEPTED)
def create_backup(
    request: Request,
    confirmation: str | None = Header(default=None, alias="X-Confirm-Backup"),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    if confirmation != "backup-local-data":
        raise LocalPDFError("BACKUP_CONFIRMATION_REQUIRED", "Yerel backup işlemini onaylayın.")
    job = Job(
        kind="backup",
        payload={"correlation_id": request.state.correlation_id},
        max_attempts=1,
    )
    session.add(job)
    session.commit()
    return job_json(job)


@router.get("/maintenance/backups/{job_id}")
def get_backup(job_id: str, session: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        parsed_id = uuid.UUID(job_id)
    except ValueError as exc:
        raise LocalPDFError("JOB_NOT_FOUND", "Backup işi bulunamadı.", status_code=404) from exc
    job = session.get(Job, parsed_id)
    if not job or job.kind != "backup":
        raise LocalPDFError("JOB_NOT_FOUND", "Backup işi bulunamadı.", status_code=404)
    return job_json(job)


def _pikepdf_version() -> str:
    import pikepdf

    return pikepdf.__version__


def _tesseract_languages() -> list[str]:
    binary = shutil.which("tesseract")
    if not binary:
        return []
    try:
        result = subprocess.run(
            [binary, "--list-langs"], check=False, capture_output=True, text=True, timeout=5
        )
        return [line.strip() for line in result.stdout.splitlines()[1:] if line.strip()]
    except (OSError, subprocess.SubprocessError):
        return []
