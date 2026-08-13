import hashlib
import hmac
import secrets
import smtplib
import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any, cast

import pikepdf
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.services.events import append_event
from app.domain.errors import LocalPDFError
from app.infrastructure.db.models import (
    DeliveryAttempt,
    DocumentVersion,
    Job,
    SignatureField,
    SignatureRequest,
    Signer,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.storage import LocalStorage
from app.settings import get_settings

router = APIRouter(tags=["signature-lite"])
DISCLAIMER = (
    "Bu signature-lite akışı düşük riskli kişisel kullanım içindir; nitelikli veya "
    "düzenlemeye tabi elektronik imza ve kimlik doğrulama sağlamaz."
)
CONSENT_TEXT = (
    "Belge hash'ini gördüm ve gösterilen alanların belgeye uygulanmasına açıkça rıza veriyorum."
)


@router.post("/signature-requests", status_code=status.HTTP_201_CREATED)
def create_signature_request(
    body: dict[str, Any],
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    if not idempotency_key:
        raise LocalPDFError("IDEMPOTENCY_REQUIRED", "Geçerli bir Idempotency-Key gereklidir.")
    try:
        version_id = uuid.UUID(str(body.get("version_id")))
    except ValueError as exc:
        raise LocalPDFError("INPUT_INVALID", "Sürüm kimliği geçersiz.") from exc
    version = session.get(DocumentVersion, version_id)
    if not version:
        raise LocalPDFError("INPUT_NOT_FOUND", "İmzalanacak sürüm bulunamadı.", status_code=404)
    fields = body.get("fields", [])
    _validate_fields(version, fields)
    signer_body = body.get("signer", {})
    signer_name = str(signer_body.get("display_name", "")).strip()
    if not signer_name:
        raise LocalPDFError("INPUT_INVALID", "İmzalayan adı gereklidir.")
    signature_request = SignatureRequest(version_id=version.id, consent_text_version="v1")
    session.add(signature_request)
    session.flush()
    for field in fields:
        session.add(
            SignatureField(
                request_id=signature_request.id,
                type=field["type"],
                page_number=int(field["page_number"]),
                x_pt=float(field["x_pt"]),
                y_pt=float(field["y_pt"]),
                width_pt=float(field["width_pt"]),
                height_pt=float(field["height_pt"]),
                required=bool(field.get("required", True)),
            )
        )
    session.add(
        Signer(
            request_id=signature_request.id,
            display_name=signer_name,
            delivery_address=signer_body.get("delivery_address"),
        )
    )
    append_event(
        session,
        "signature.created",
        "signature_request",
        signature_request.id,
        request.state.correlation_id,
        document_sha256=version.sha256,
        payload={"field_count": len(fields), "consent_text_version": "v1"},
    )
    session.commit()
    return _request_json(session, signature_request)


@router.post("/signature-requests/{request_id}/invite")
def invite_signature_request(
    request_id: uuid.UUID,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    if not idempotency_key:
        raise LocalPDFError("IDEMPOTENCY_REQUIRED", "Geçerli bir Idempotency-Key gereklidir.")
    signature_request = session.get(SignatureRequest, request_id)
    if not signature_request or signature_request.state not in {"draft", "invited"}:
        raise LocalPDFError("INPUT_INVALID", "Bu istek davet edilemez.")
    token = secrets.token_urlsafe(32)
    signature_request.token_hash = _token_hash(token)
    signature_request.token_expires_at = datetime.now(UTC) + timedelta(days=7)
    signature_request.state = "invited"
    signer = session.scalar(select(Signer).where(Signer.request_id == request_id))
    outcome, channel, safe_error = "manual", "manual", None
    settings = get_settings()
    if settings.smtp_enabled and signer and signer.delivery_address:
        try:
            _send_invite(signer.delivery_address, token)
            outcome, channel = "sent", "smtp"
        except (OSError, smtplib.SMTPException):
            outcome, channel, safe_error = (
                "failed",
                "smtp",
                "E-posta gönderilemedi; manuel bağlantı kullanılabilir.",
            )
    session.add(
        DeliveryAttempt(
            request_id=request_id,
            channel=channel,
            outcome=outcome,
            safe_error=safe_error,
        )
    )
    append_event(
        session,
        "signature.invited",
        "signature_request",
        request_id,
        request.state.correlation_id,
        payload={
            "delivery_outcome": outcome,
            "token_expires_at": signature_request.token_expires_at.isoformat(),
        },
    )
    session.commit()
    return {
        "request_id": str(request_id),
        "delivery": outcome,
        "manual_url": f"/sign/{token}",
        "token_expires_at": signature_request.token_expires_at.isoformat(),
        "disclaimer": DISCLAIMER,
    }


@router.get("/sign/{token}")
def get_consent(token: str, session: Session = Depends(get_db)) -> dict[str, Any]:
    signature_request = _request_for_token(session, token)
    version = session.get(DocumentVersion, signature_request.version_id)
    signer = session.scalar(select(Signer).where(Signer.request_id == signature_request.id))
    if signature_request.state == "invited":
        signature_request.state = "viewed"
        session.commit()
    return {
        "request_id": str(signature_request.id),
        "document_hash": version.sha256 if version else None,
        "signer_label": signer.display_name if signer else None,
        "consent_text": CONSENT_TEXT,
        "consent_text_version": signature_request.consent_text_version,
        "disclaimer": DISCLAIMER,
    }


@router.post("/sign/{token}/consent", status_code=status.HTTP_202_ACCEPTED)
def consent(
    token: str,
    body: dict[str, Any],
    request: Request,
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    signature_request = _request_for_token(session, token)
    if body.get("accepted") is not True:
        raise LocalPDFError("CONSENT_REQUIRED", "Devam etmek için açık rıza gereklidir.")
    if signature_request.state in {"consented", "sealed"}:
        raise LocalPDFError("TOKEN_INVALID_OR_EXPIRED", "Bu bağlantı daha önce kullanılmış.")
    now = datetime.now(UTC)
    signer = session.scalar(select(Signer).where(Signer.request_id == signature_request.id))
    if not signer:
        raise LocalPDFError("INTERNAL_STATE", "İmzalayan kaydı bulunamadı.", status_code=500)
    signer.consented_at = now
    signer.status = "consented"
    signature_request.state = "consented"
    signature_request.token_hash = None
    job = Job(
        kind="signature_seal",
        payload={
            "request_id": str(signature_request.id),
            "correlation_id": request.state.correlation_id,
            "consented_at": now.isoformat(),
        },
        max_attempts=get_settings().job_max_attempts,
    )
    session.add(job)
    version = session.get(DocumentVersion, signature_request.version_id)
    append_event(
        session,
        "signature.consented",
        "signature_request",
        signature_request.id,
        request.state.correlation_id,
        document_sha256=version.sha256 if version else None,
        payload={
            "consent_text_version": signature_request.consent_text_version,
            "accepted_at": now.isoformat(),
        },
    )
    session.commit()
    return {"request_id": str(signature_request.id), "job_id": str(job.id), "state": "consented"}


@router.get("/signature-requests/{request_id}")
def get_signature_request(
    request_id: uuid.UUID, session: Session = Depends(get_db)
) -> dict[str, Any]:
    signature_request = session.get(SignatureRequest, request_id)
    if not signature_request:
        raise LocalPDFError("INPUT_NOT_FOUND", "Signature-lite isteği bulunamadı.", status_code=404)
    return _request_json(session, signature_request)


@router.post("/signature-requests/{request_id}/cancel")
def cancel_signature_request(
    request_id: uuid.UUID, request: Request, session: Session = Depends(get_db)
) -> dict[str, Any]:
    signature_request = session.get(SignatureRequest, request_id)
    if not signature_request or signature_request.state in {"sealed", "cancelled"}:
        raise LocalPDFError("INPUT_INVALID", "Bu istek iptal edilemez.")
    signature_request.state = "cancelled"
    signature_request.token_hash = None
    append_event(
        session,
        "signature.cancelled",
        "signature_request",
        signature_request.id,
        request.state.correlation_id,
    )
    session.commit()
    return _request_json(session, signature_request)


def _validate_fields(version: DocumentVersion, fields: list[dict[str, Any]]) -> None:
    if not fields:
        raise LocalPDFError("INPUT_INVALID", "En az bir signature-lite alanı ekleyin.")
    path = LocalStorage().resolve(version.relative_path)
    with pikepdf.open(path) as pdf:
        for field in fields:
            page_number = int(field.get("page_number", 0))
            if page_number < 1 or page_number > len(pdf.pages):
                raise LocalPDFError("PAGE_OUT_OF_BOUNDS", "Alan sayfası belge sınırını aşıyor.")
            page = pdf.pages[page_number - 1]
            box = cast(Any, page.get("/CropBox") or page.MediaBox)
            page_width, page_height = float(box[2] - box[0]), float(box[3] - box[1])
            x, y = float(field.get("x_pt", -1)), float(field.get("y_pt", -1))
            width, height = float(field.get("width_pt", 0)), float(field.get("height_pt", 0))
            if (
                x < 0
                or y < 0
                or width <= 0
                or height <= 0
                or x + width > page_width
                or y + height > page_height
            ):
                raise LocalPDFError(
                    "INPUT_INVALID", "Signature-lite alanı sayfa sınırları dışında."
                )
            if field.get("type") not in {"signature", "initial", "text", "date"}:
                raise LocalPDFError("INPUT_INVALID", "Signature-lite alan türü desteklenmiyor.")


def _request_for_token(session: Session, token: str) -> SignatureRequest:
    if len(token) > 200:
        raise LocalPDFError("TOKEN_INVALID_OR_EXPIRED", "Bağlantı geçersiz veya süresi dolmuş.")
    signature_request = session.scalar(
        select(SignatureRequest).where(SignatureRequest.token_hash == _token_hash(token))
    )
    if (
        not signature_request
        or not signature_request.token_expires_at
        or signature_request.token_expires_at < datetime.now(UTC)
        or signature_request.state in {"sealed", "cancelled", "expired"}
    ):
        raise LocalPDFError("TOKEN_INVALID_OR_EXPIRED", "Bağlantı geçersiz veya süresi dolmuş.")
    return signature_request


def _token_hash(token: str) -> str:
    settings = get_settings()
    return hmac.new(
        settings.invite_token_pepper.encode(), token.encode(), hashlib.sha256
    ).hexdigest()


def _send_invite(address: str, token: str) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from:
        raise OSError("SMTP configuration incomplete")
    message = EmailMessage()
    message["Subject"] = "LocalPDF signature-lite daveti"
    message["From"] = settings.smtp_from
    message["To"] = address
    message.set_content(f"{DISCLAIMER}\n\nhttp://localhost:3000/sign/{token}")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


def _request_json(session: Session, signature_request: SignatureRequest) -> dict[str, Any]:
    fields = session.scalars(
        select(SignatureField).where(SignatureField.request_id == signature_request.id)
    ).all()
    signer = session.scalar(select(Signer).where(Signer.request_id == signature_request.id))
    return {
        "id": str(signature_request.id),
        "version_id": str(signature_request.version_id),
        "state": signature_request.state,
        "consent_text_version": signature_request.consent_text_version,
        "token_expires_at": signature_request.token_expires_at.isoformat()
        if signature_request.token_expires_at
        else None,
        "sealed_version_id": str(signature_request.sealed_version_id)
        if signature_request.sealed_version_id
        else None,
        "signer": {
            "display_name": signer.display_name,
            "status": signer.status,
            "consented_at": signer.consented_at.isoformat() if signer.consented_at else None,
        }
        if signer
        else None,
        "fields": [
            {
                "id": str(field.id),
                "type": field.type,
                "page_number": field.page_number,
                "x_pt": field.x_pt,
                "y_pt": field.y_pt,
                "width_pt": field.width_pt,
                "height_pt": field.height_pt,
                "required": field.required,
            }
            for field in fields
        ],
        "disclaimer": DISCLAIMER,
    }
