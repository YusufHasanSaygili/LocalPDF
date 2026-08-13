import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.responses import Response

from app.api.routes import router as api_router
from app.domain.errors import LocalPDFError
from app.infrastructure.db.session import SessionLocal
from app.settings import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level)
app = FastAPI(
    title="LocalPDF API",
    version=settings.app_version,
    description="Local-only document processing API. Document bytes never leave this stack.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID", "Content-Disposition"],
)


@app.middleware("http")
async def correlation_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    incoming = request.headers.get("X-Correlation-ID", "")
    correlation_id = incoming[:100] if incoming else str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(LocalPDFError)
async def localpdf_error_handler(request: Request, exc: LocalPDFError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "recoverable": exc.recoverable,
                "correlation_id": request.state.correlation_id,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INPUT_INVALID",
                "message": "Gönderilen alanlardan biri geçersiz.",
                "recoverable": True,
                "correlation_id": request.state.correlation_id,
                "details": {"fields": [".".join(map(str, item["loc"])) for item in exc.errors()]},
            }
        },
    )


@app.get("/health", tags=["system"])
def root_health() -> dict[str, str]:
    return {"status": "ok", "service": "localpdf-api"}


@app.get("/ready", tags=["system"])
def root_ready() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    settings.store_root.mkdir(parents=True, exist_ok=True)
    return {"status": "ready"}


app.include_router(api_router, prefix="/api/v1")
