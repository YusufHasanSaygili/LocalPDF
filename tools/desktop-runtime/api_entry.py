"""Entrypoint for the self-contained LocalPDF Windows API runtime."""

import os
import threading

import uvicorn

from app.main import app
from app.infrastructure.db.models import Base
from app.infrastructure.db.session import engine
from app.worker.main import main as worker_main


def main() -> None:
    Base.metadata.create_all(bind=engine)
    worker = threading.Thread(target=worker_main, name="localpdf-worker", daemon=True)
    worker.start()
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(os.environ.get("LOCALPDF_API_PORT", "8000")),
        access_log=False,
        log_level=os.environ.get("LOG_LEVEL", "warning").lower(),
    )


if __name__ == "__main__":
    main()
