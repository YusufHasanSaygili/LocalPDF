import json
import logging
import os
import shutil
import socket
import sqlite3
import stat
import threading
import time
import uuid
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pymupdf  # type: ignore[import-untyped]
from sqlalchemy import func, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.application.services.events import append_event
from app.domain.errors import LocalPDFError
from app.infrastructure.db.models import (
    Document,
    DocumentVersion,
    Event,
    Job,
    Operation,
    OperationInput,
    Original,
    Preview,
    SignatureField,
    SignatureRequest,
    Signer,
)
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.storage import LocalStorage
from app.infrastructure.tools import pdf as pdf_tools
from app.infrastructure.tools.system import executable, run_tool
from app.settings import get_settings

logger = logging.getLogger("localpdf.worker")
settings = get_settings()
worker_id = f"{socket.gethostname()}-{os.getpid()}"


def main() -> None:
    logging.basicConfig(level=settings.log_level)
    LocalStorage()
    logger.info("worker_started", extra={"worker_id": worker_id})
    next_cleanup = 0.0
    while True:
        if time.monotonic() >= next_cleanup:
            expire_documents()
            next_cleanup = time.monotonic() + 60
        recover_stale_jobs()
        job_id = claim_job()
        if not job_id:
            time.sleep(0.5)
            continue
        process_job(job_id)


def claim_job() -> uuid.UUID | None:
    now = datetime.now(UTC)
    with SessionLocal.begin() as session:
        job = session.scalar(
            select(Job)
            .where(Job.state == "queued", Job.available_at <= now)
            .order_by(Job.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not job:
            return None
        job.state = "running"
        job.started_at = job.started_at or now
        job.attempt_count += 1
        job.lease_owner = worker_id
        job.lease_expires_at = now + timedelta(seconds=settings.job_lease_seconds)
        job.heartbeat_at = now
        job.progress_percent = 1
        return job.id


def recover_stale_jobs() -> None:
    now = datetime.now(UTC)
    with SessionLocal.begin() as session:
        stale = session.scalars(
            select(Job).where(Job.state.in_(["running", "validating"]), Job.lease_expires_at < now)
        ).all()
        for job in stale:
            if job.attempt_count < job.max_attempts:
                job.state = "queued"
                job.available_at = now + timedelta(seconds=min(30, job.attempt_count * 2))
                job.lease_owner = None
                job.lease_expires_at = None
            else:
                job.state = "failed"
                job.error_code = "WORKER_LEASE_EXPIRED"
                job.safe_error_message = "İşçi işlemi tamamlayamadı; önceki dosyalar korundu."
                job.finished_at = now


def expire_documents() -> None:
    now = datetime.now(UTC)
    with SessionLocal.begin() as session:
        expired = session.scalars(
            select(Document)
            .where(
                Document.state == "active",
                Document.expires_at.is_not(None),
                Document.expires_at <= now,
            )
            .with_for_update(skip_locked=True)
        ).all()
        for document in expired:
            document.state = "expired"
            append_event(
                session,
                "document.expired",
                "document",
                document.id,
                f"cleanup-{document.id}",
                document_sha256=document.original.sha256 if document.original else None,
                payload={"expired_at": now.isoformat()},
            )
        purge_before = now - timedelta(days=settings.expired_purge_grace_days)
        purgeable = session.scalars(
            select(Document)
            .where(
                Document.state == "expired",
                Document.deleted_at.is_(None),
                Document.expires_at <= purge_before,
            )
            .with_for_update(skip_locked=True)
        ).all()
        storage = LocalStorage()
        for document in purgeable:
            if document.original:
                _unlink_stored_file(
                    storage.resolve(document.original.relative_path, must_exist=False)
                )
            for version in document.versions:
                _unlink_stored_file(storage.resolve(version.relative_path, must_exist=False))
                version.deleted_at = now
            document.deleted_at = now
            append_event(
                session,
                "document.expired_bytes_purged",
                "document",
                document.id,
                f"cleanup-{document.id}",
                payload={"purged_at": now.isoformat(), "backups_unaffected": True},
            )


def process_job(job_id: uuid.UUID) -> None:
    storage = LocalStorage()
    workdir: Path | None = None
    heartbeat_stop = threading.Event()
    heartbeat = threading.Thread(target=heartbeat_loop, args=(job_id, heartbeat_stop), daemon=True)
    heartbeat.start()
    try:
        workdir = storage.job_directory(job_id)
        with SessionLocal() as session:
            job = session.get(Job, job_id)
            if not job:
                return
            job.heartbeat_at = datetime.now(UTC)
            job.lease_expires_at = datetime.now(UTC) + timedelta(
                seconds=settings.tool_timeout_seconds + 60
            )
            session.commit()
            if job.kind == "preview":
                process_preview(session, job, workdir)
            elif job.kind == "operation":
                process_operation(session, job, workdir)
            elif job.kind == "delete":
                process_delete(session, job)
            elif job.kind == "export":
                process_export(session, job, workdir)
            elif job.kind == "signature_seal":
                process_signature_seal(session, job, workdir)
            elif job.kind == "backup":
                process_backup(session, job, workdir)
            else:
                raise LocalPDFError("JOB_KIND_UNKNOWN", "İş türü desteklenmiyor.")
            job.state = "succeeded"
            job.progress_percent = 100
            job.finished_at = datetime.now(UTC)
            job.lease_owner = None
            job.lease_expires_at = None
            session.commit()
    except Exception as exc:
        fail_job(job_id, exc)
    finally:
        heartbeat_stop.set()
        heartbeat.join(timeout=2)
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)


def heartbeat_loop(job_id: uuid.UUID, stop: threading.Event) -> None:
    interval = max(5, min(30, settings.job_lease_seconds // 3))
    while not stop.wait(interval):
        now = datetime.now(UTC)
        try:
            with SessionLocal.begin() as session:
                session.execute(
                    update(Job)
                    .where(Job.id == job_id, Job.state.in_(["running", "validating"]))
                    .values(
                        heartbeat_at=now,
                        lease_expires_at=now + timedelta(seconds=settings.job_lease_seconds),
                    )
                )
        except Exception:
            logger.warning("job_heartbeat_failed", extra={"job_id": str(job_id)})


def process_preview(session: Session, job: Job, workdir: Path) -> None:
    storage = LocalStorage()
    source_kind = job.payload["source_kind"]
    source_id = uuid.UUID(job.payload["source_id"])
    source: Original | DocumentVersion | None
    if source_kind == "original":
        source = session.get(Original, source_id)
    else:
        source = session.get(DocumentVersion, source_id)
    if not source:
        raise LocalPDFError("INPUT_NOT_FOUND", "Önizleme kaynağı bulunamadı.")
    input_path = storage.resolve(source.relative_path)
    with pymupdf.open(input_path) as document:
        page_count = len(document)
        if page_count < 1:
            raise LocalPDFError("OUTPUT_VALIDATION_FAILED", "Önizleme üretilemedi.")
        scale = settings.preview_dpi / 72
        matrix = pymupdf.Matrix(scale, scale)
        for index, page in enumerate(document, start=1):
            relative = f"previews/{source_id}/page-{index:06d}.webp"
            target = storage.resolve(relative, must_exist=False)
            target.parent.mkdir(parents=True, exist_ok=True)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            pixmap.pil_save(target, format="WEBP")
            digest, _ = storage.hash_file(target)
            session.add(
                Preview(
                    source_id=source_id,
                    source_kind=source_kind,
                    page_number=index,
                    relative_path=relative,
                    width=pixmap.width,
                    height=pixmap.height,
                    sha256=digest,
                )
            )
            job.progress_percent = min(95, round(index / page_count * 95))
            if index == 1:
                session.commit()
    payload = dict(job.payload)
    payload["result"] = {"preview_count": page_count}
    job.payload = payload


def process_operation(session: Session, job: Job, workdir: Path) -> None:
    if not job.operation_id:
        raise LocalPDFError("INTERNAL_STATE", "Operation kaydı eksik.")
    operation = session.get(Operation, job.operation_id)
    if not operation:
        raise LocalPDFError("INTERNAL_STATE", "Operation bulunamadı.")
    inputs = session.scalars(
        select(OperationInput)
        .where(OperationInput.operation_id == operation.id)
        .order_by(OperationInput.position)
    ).all()
    source_paths = [resolve_operation_input(session, item) for item in inputs]
    output = workdir / "output.pdf"
    result_metadata: dict[str, Any] = {}
    outputs: list[Path]
    if operation.type == "merge":
        pdf_tools.merge(source_paths, output)
        outputs = [output]
    elif operation.type == "split":
        outputs = pdf_tools.split(source_paths[0], workdir, operation.parameters)
    elif operation.type == "reorder":
        pdf_tools.reorder(source_paths[0], output, operation.parameters["pages"])
        outputs = [output]
    elif operation.type == "rotate":
        pdf_tools.rotate(
            source_paths[0], output, operation.parameters["pages"], operation.parameters["degrees"]
        )
        outputs = [output]
    elif operation.type == "compress":
        _, result_metadata = pdf_tools.compress(
            source_paths[0], output, operation.parameters.get("profile", "lossless")
        )
        outputs = [output]
    elif operation.type == "watermark":
        pdf_tools.watermark(source_paths[0], output, operation.parameters)
        outputs = [output]
    elif operation.type == "redact":
        pdf_tools.redact(source_paths[0], output, operation.parameters, workdir)
        outputs = [output]
    elif operation.type == "ocr":
        pdf_tools.ocr(source_paths[0], output, operation.parameters, workdir)
        outputs = [output]
    elif operation.type == "office_to_pdf":
        pdf_tools.office_to_pdf(source_paths[0], output, workdir)
        outputs = [output]
    else:
        raise LocalPDFError("JOB_KIND_UNKNOWN", "PDF işlemi desteklenmiyor.")
    job.state = "validating"
    job.progress_percent = 85
    session.commit()
    result_ids = publish_versions(session, operation, outputs, job, result_metadata)
    if len(result_ids) > 1:
        result_metadata["zip_url"] = create_split_zip(session, job, result_ids, workdir)
    payload = dict(job.payload)
    payload["result_ids"] = [str(result_id) for result_id in result_ids]
    payload["result"] = result_metadata
    job.payload = payload


def publish_versions(
    session: Session,
    operation: Operation,
    outputs: list[Path],
    job: Job,
    result_metadata: dict[str, Any],
) -> list[uuid.UUID]:
    storage = LocalStorage()
    document = session.scalar(
        select(Document).where(Document.id == operation.document_id).with_for_update()
    )
    if not document:
        raise LocalPDFError("DOCUMENT_NOT_FOUND", "Çıktı belgesi bulunamadı.")
    next_version = (
        session.scalar(
            select(func.coalesce(func.max(DocumentVersion.version_number), 0)).where(
                DocumentVersion.document_id == document.id
            )
        )
        or 0
    ) + 1
    result_ids: list[uuid.UUID] = []
    input_sha256 = session.scalar(
        select(OperationInput.sha256)
        .where(OperationInput.operation_id == operation.id)
        .order_by(OperationInput.position)
        .limit(1)
    )
    for offset, path in enumerate(outputs):
        output_id = uuid.uuid4()
        page_count = pdf_tools.validate_output(path)
        stored = storage.publish_output(path, document.id, next_version + offset, output_id)
        version = DocumentVersion(
            id=output_id,
            document_id=document.id,
            operation_id=operation.id,
            version_number=next_version + offset,
            relative_path=stored.relative_path,
            sha256=stored.sha256,
            byte_size=stored.byte_size,
            page_count=page_count,
        )
        session.add(version)
        session.add(
            Job(
                kind="preview",
                payload={"source_kind": "version", "source_id": str(output_id)},
                max_attempts=settings.job_max_attempts,
            )
        )
        append_event(
            session,
            "operation.succeeded",
            "operation",
            operation.id,
            job.payload.get("correlation_id", str(job.id)),
            document_sha256=input_sha256,
            output_sha256=stored.sha256,
            payload={
                "type": operation.type,
                "version_number": version.version_number,
                "page_count": page_count,
                "byte_size": stored.byte_size,
                **({"report": result_metadata} if result_metadata else {}),
            },
        )
        result_ids.append(output_id)
    session.flush()
    return result_ids


def create_split_zip(session: Session, job: Job, result_ids: list[uuid.UUID], workdir: Path) -> str:
    storage = LocalStorage()
    zip_path = workdir / "split-results.zip"
    manifest: list[dict[str, Any]] = []
    versions = [session.get(DocumentVersion, result_id) for result_id in result_ids]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, version in enumerate(versions, start=1):
            if not version:
                continue
            name = f"part-{index:03d}.pdf"
            archive.write(storage.resolve(version.relative_path), arcname=name)
            manifest.append(
                {"filename": name, "sha256": version.sha256, "byte_size": version.byte_size}
            )
        archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True, indent=2))
    relative = f"exports/{job.id}/split-results.zip"
    target = storage.resolve(relative, must_exist=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(zip_path, target)
    payload = dict(job.payload)
    payload["export_relative_path"] = relative
    job.payload = payload
    return f"/api/v1/exports/{job.id}/download"


def resolve_operation_input(session: Session, item: OperationInput) -> Path:
    source: Original | DocumentVersion | None
    if item.input_kind == "original":
        source = session.get(Original, item.input_id)
    else:
        source = session.get(DocumentVersion, item.input_id)
    if not source or source.sha256 != item.sha256:
        raise LocalPDFError("INPUT_NOT_FOUND", "İşlem kaynağı değişmiş veya bulunamadı.")
    return LocalStorage().resolve(source.relative_path)


def process_delete(session: Session, job: Job) -> None:
    document = session.get(Document, uuid.UUID(job.payload["document_id"]))
    if not document:
        raise LocalPDFError("DOCUMENT_NOT_FOUND", "Silinecek belge bulunamadı.")
    storage = LocalStorage()
    if document.original:
        _unlink_stored_file(storage.resolve(document.original.relative_path, must_exist=False))
    for version in document.versions:
        _unlink_stored_file(storage.resolve(version.relative_path, must_exist=False))
        version.deleted_at = datetime.now(UTC)
    document.state = "deleted"
    document.deleted_at = datetime.now(UTC)
    append_event(
        session,
        "document.deleted",
        "document",
        document.id,
        job.payload.get("correlation_id", str(job.id)),
        payload={"bytes_removed": True, "backups_unaffected": True},
    )
    payload = dict(job.payload)
    payload["result"] = {"document_id": str(document.id), "state": "deleted"}
    job.payload = payload


def process_export(session: Session, job: Job, workdir: Path) -> None:
    document = session.get(Document, uuid.UUID(job.payload["document_id"]))
    if not document or not document.original:
        raise LocalPDFError("DOCUMENT_NOT_FOUND", "Dışa aktarılacak belge bulunamadı.")
    storage = LocalStorage()
    archive_path = workdir / "document-export.zip"
    events = session.scalars(
        select(Event)
        .where(Event.aggregate_id.in_([document.id, *[v.operation_id for v in document.versions]]))
        .order_by(Event.occurred_at, Event.id)
    ).all()
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "document_id": str(document.id),
        "display_name": document.display_name,
        "files": [],
    }
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        original_name = f"original/{document.safe_name}"
        archive.write(storage.resolve(document.original.relative_path), original_name)
        manifest["files"].append(
            {
                "path": original_name,
                "sha256": document.original.sha256,
                "byte_size": document.original.byte_size,
            }
        )
        for version in document.versions:
            name = f"versions/v{version.version_number:06d}.pdf"
            archive.write(storage.resolve(version.relative_path), name)
            manifest["files"].append(
                {"path": name, "sha256": version.sha256, "byte_size": version.byte_size}
            )
        archive.writestr(
            "manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2)
        )
        archive.writestr(
            "audit.jsonl",
            "".join(json.dumps(_event_export(event), sort_keys=True) + "\n" for event in events),
        )
    relative = f"exports/{job.id}/document-export.zip"
    target = storage.resolve(relative, must_exist=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(archive_path, target)
    payload = dict(job.payload)
    payload["export_relative_path"] = relative
    payload["result"] = {"download_url": f"/api/v1/exports/{job.id}/download"}
    job.payload = payload
    append_event(
        session,
        "document.exported",
        "document",
        document.id,
        job.payload.get("correlation_id", str(job.id)),
        payload={"file_count": len(manifest["files"])},
    )


def process_signature_seal(session: Session, job: Job, workdir: Path) -> None:
    request_id = uuid.UUID(job.payload["request_id"])
    signature_request = session.scalar(
        select(SignatureRequest).where(SignatureRequest.id == request_id).with_for_update()
    )
    if not signature_request or signature_request.state != "consented":
        raise LocalPDFError("CONSENT_REQUIRED", "Signature-lite isteği mühürlenmeye hazır değil.")
    source = session.get(DocumentVersion, signature_request.version_id)
    signer = session.scalar(select(Signer).where(Signer.request_id == request_id))
    fields = session.scalars(
        select(SignatureField).where(SignatureField.request_id == request_id)
    ).all()
    if not source or not signer or not signer.consented_at:
        raise LocalPDFError("CONSENT_REQUIRED", "Rıza veya kaynak kaydı eksik.")
    output = workdir / "sealed.pdf"
    pdf_tools.apply_signature(
        LocalStorage().resolve(source.relative_path),
        output,
        [
            {
                "type": field.type,
                "page_number": field.page_number,
                "x_pt": field.x_pt,
                "y_pt": field.y_pt,
                "width_pt": field.width_pt,
                "height_pt": field.height_pt,
            }
            for field in fields
        ],
        signer.display_name,
        signer.consented_at.isoformat(),
    )
    operation = Operation(
        document_id=source.document_id,
        type="signature_seal",
        parameters={
            "request_id": str(request_id),
            "consent_text_version": signature_request.consent_text_version,
        },
        idempotency_key=f"signature-seal:{request_id}",
    )
    session.add(operation)
    session.flush()
    session.add(
        OperationInput(
            operation_id=operation.id,
            input_kind="version",
            input_id=source.id,
            position=0,
            sha256=source.sha256,
        )
    )
    versions = publish_versions(session, operation, [output], job, {})
    signature_request.sealed_version_id = versions[0]
    signature_request.state = "sealed"
    sealed = session.get(DocumentVersion, versions[0])
    append_event(
        session,
        "signature.sealed",
        "signature_request",
        signature_request.id,
        job.payload.get("correlation_id", str(job.id)),
        document_sha256=source.sha256,
        output_sha256=sealed.sha256 if sealed else None,
        payload={
            "consent_text_version": signature_request.consent_text_version,
            "sealed_version_id": str(versions[0]),
        },
    )
    payload = dict(job.payload)
    payload["result_ids"] = [str(versions[0])]
    payload["result"] = {
        "sealed_version_id": str(versions[0]),
        "final_sha256": sealed.sha256 if sealed else None,
    }
    job.payload = payload


def process_backup(session: Session, job: Job, workdir: Path) -> None:
    database = make_url(settings.database_url)
    if database.drivername.startswith("sqlite"):
        database_dump = workdir / "database.sqlite3"
        source_database = Path(database.database or "")
        with sqlite3.connect(source_database) as source, sqlite3.connect(database_dump) as backup_db:
            source.backup(backup_db)
    else:
        pg_dump = executable("pg_dump")
        if not pg_dump:
            raise LocalPDFError("TOOL_UNAVAILABLE", "PostgreSQL backup aracı hazır değil.")
        database_dump = workdir / "database.dump"
        run_tool(
            [
                pg_dump,
                "--host",
                database.host or "db",
                "--port",
                str(database.port or 5432),
                "--username",
                database.username or "localpdf",
                "--dbname",
                database.database or "localpdf",
                "--format=custom",
                f"--file={database_dump}",
            ],
            cwd=workdir,
            env={"PGPASSWORD": database.password or ""},
        )
    storage = LocalStorage()
    records: list[dict[str, Any]] = []
    archive_path = workdir / "localpdf-backup.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(database_dump, database_dump.name)
        for directory in ("originals", "outputs", "previews", "exports"):
            directory_path = storage.resolve(directory, must_exist=False)
            if not directory_path.exists():
                continue
            for path in sorted(
                candidate for candidate in directory_path.rglob("*") if candidate.is_file()
            ):
                if path.is_symlink():
                    raise LocalPDFError(
                        "PATH_INVALID", "Backup sırasında sembolik bağlantı bulundu."
                    )
                relative = path.relative_to(storage.root).as_posix()
                digest, size = storage.hash_file(path)
                archive.write(path, f"store/{relative}")
                records.append({"relative_path": relative, "byte_size": size, "sha256": digest})
        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "app_version": settings.app_version,
            "database_sha256": storage.hash_file(database_dump)[0],
            "file_count": len(records),
        }
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        archive.writestr(
            "files.jsonl",
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        )
        archive.writestr(
            "README_RESTORE.txt",
            "Restore only into a new, empty target with scripts/restore.py.\n",
        )
    archive_digest, _ = storage.hash_file(archive_path)
    relative = f"backups/{job.id}/localpdf-backup.zip"
    target = storage.resolve(relative, must_exist=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(archive_path, target)
    payload = dict(job.payload)
    payload["export_relative_path"] = relative
    payload["result"] = {
        "download_url": f"/api/v1/exports/{job.id}/download",
        "manifest_sha256": archive_digest,
        "file_count": len(records),
    }
    job.payload = payload
    append_event(
        session,
        "backup.completed",
        "job",
        job.id,
        job.payload.get("correlation_id", str(job.id)),
        output_sha256=archive_digest,
        payload={"file_count": len(records)},
    )


def fail_job(job_id: uuid.UUID, exc: Exception) -> None:
    logger.exception("job_failed", extra={"job_id": str(job_id), "worker_id": worker_id})
    with SessionLocal.begin() as session:
        job = session.get(Job, job_id)
        if not job:
            return
        if isinstance(exc, LocalPDFError):
            job.error_code = exc.code
            job.safe_error_message = exc.message
        else:
            job.error_code = "UNEXPECTED_ERROR"
            job.safe_error_message = "İşlem tamamlanamadı; önceki dosyalarınız korundu."
        job.state = "failed"
        job.finished_at = datetime.now(UTC)
        job.lease_owner = None
        job.lease_expires_at = None
        append_event(
            session,
            "job.failed",
            "job",
            job.id,
            job.payload.get("correlation_id", str(job.id)),
            payload={"kind": job.kind, "error_code": job.error_code},
        )


def _unlink_stored_file(path: Path) -> None:
    """Remove an explicitly deleted stored file, including read-only originals on Windows."""
    if not path.exists():
        return
    try:
        path.chmod(stat.S_IREAD | stat.S_IWRITE)
    except OSError:
        pass
    path.unlink(missing_ok=True)


def _page_number_from_path(path: Path) -> int:
    try:
        return int(path.stem.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def _event_export(event: Event) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "occurred_at": event.occurred_at.isoformat(),
        "event_type": event.event_type,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": str(event.aggregate_id),
        "document_sha256": event.document_sha256,
        "output_sha256": event.output_sha256,
        "payload": event.payload,
    }


if __name__ == "__main__":
    main()
