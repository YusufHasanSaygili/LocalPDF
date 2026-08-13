from typing import Any

from app.infrastructure.db.models import Document, DocumentVersion, Event, Job, Original, Preview


def original_json(original: Original) -> dict[str, Any]:
    return {
        "id": str(original.id),
        "sha256": original.sha256,
        "byte_size": original.byte_size,
        "page_count": original.page_count,
        "detected_features": original.detected_features,
        "created_at": original.created_at.isoformat(),
        "download_url": f"/api/v1/originals/{original.id}/download",
    }


def version_json(version: DocumentVersion) -> dict[str, Any]:
    return {
        "id": str(version.id),
        "operation_id": str(version.operation_id),
        "version_number": version.version_number,
        "sha256": version.sha256,
        "byte_size": version.byte_size,
        "page_count": version.page_count,
        "created_at": version.created_at.isoformat(),
        "expires_at": version.expires_at.isoformat() if version.expires_at else None,
        "download_url": f"/api/v1/versions/{version.id}/download",
    }


def document_json(document: Document, *, detail: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(document.id),
        "display_name": document.display_name,
        "media_type": document.media_type,
        "state": document.state,
        "created_at": document.created_at.isoformat(),
        "expires_at": document.expires_at.isoformat() if document.expires_at else None,
        "original": original_json(document.original),
        "latest_version": version_json(document.versions[-1]) if document.versions else None,
    }
    if detail:
        payload["versions"] = [version_json(version) for version in document.versions]
    return payload


def job_json(job: Job) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "state": job.state,
        "progress_percent": job.progress_percent,
        "operation_id": str(job.operation_id) if job.operation_id else None,
        "result_ids": job.payload.get("result_ids", []),
        "result": job.payload.get("result"),
        "error": (
            {
                "code": job.error_code,
                "message": job.safe_error_message,
                "recoverable": job.attempt_count < job.max_attempts,
            }
            if job.error_code
            else None
        ),
        "created_at": job.created_at.isoformat(),
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


def preview_json(preview: Preview) -> dict[str, Any]:
    return {
        "id": str(preview.id),
        "page_number": preview.page_number,
        "width": preview.width,
        "height": preview.height,
        "sha256": preview.sha256,
        "state": preview.state,
        "content_url": f"/api/v1/previews/{preview.id}/content",
    }


def event_json(event: Event) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "occurred_at": event.occurred_at.isoformat(),
        "event_type": event.event_type,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": str(event.aggregate_id),
        "actor_type": event.actor_type,
        "correlation_id": event.correlation_id,
        "document_sha256": event.document_sha256,
        "output_sha256": event.output_sha256,
        "schema_version": event.schema_version,
        "payload": event.payload,
    }
