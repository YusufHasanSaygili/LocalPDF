import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.serializers import job_json
from app.application.services.events import append_event
from app.domain.errors import LocalPDFError
from app.infrastructure.db.models import Job
from app.infrastructure.db.session import get_db

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID, session: Session = Depends(get_db)) -> dict[str, object]:
    job = session.get(Job, job_id)
    if not job:
        raise LocalPDFError("JOB_NOT_FOUND", "İş bulunamadı.", status_code=404)
    return job_json(job)


@router.post("/jobs/{job_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_job(job_id: uuid.UUID, session: Session = Depends(get_db)) -> dict[str, object]:
    job = session.get(Job, job_id)
    if not job or job.state != "failed" or job.attempt_count >= job.max_attempts:
        raise LocalPDFError("JOB_NOT_RETRYABLE", "Bu iş tekrar denenemez.")
    job.state = "queued"
    job.error_code = None
    job.safe_error_message = None
    job.progress_percent = 0
    session.commit()
    return job_json(job)


@router.post("/jobs/{job_id}/cancel")
def cancel_job(
    job_id: uuid.UUID, request: Request, session: Session = Depends(get_db)
) -> dict[str, object]:
    job = session.get(Job, job_id)
    if not job or job.state not in {"queued", "failed"}:
        raise LocalPDFError("JOB_NOT_CANCELLABLE", "Bu aşamada iş iptal edilemez.")
    job.state = "cancelled"
    append_event(
        session,
        "job.cancelled",
        "job",
        job.id,
        request.state.correlation_id,
        payload={"kind": job.kind},
    )
    session.commit()
    return job_json(job)
