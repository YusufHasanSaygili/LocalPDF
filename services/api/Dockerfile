FROM python:3.12.5-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH=/app/.venv/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
      libreoffice-core libreoffice-writer libreoffice-calc libreoffice-impress \
      poppler-utils postgresql-client tesseract-ocr tesseract-ocr-eng tesseract-ocr-tur fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system localpdf && useradd --system --gid localpdf --home /app localpdf

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY app ./app
RUN pip install --upgrade pip==25.2 \
    && pip install uv==0.11.32 \
    && uv sync --frozen --all-extras --no-editable
COPY alembic.ini ./
COPY migrations ./migrations
COPY tests ./tests
RUN mkdir -p /data && chown -R localpdf:localpdf /app /data
USER localpdf

EXPOSE 8000
