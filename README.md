# LocalPDF

LocalPDF is a private, local-first Windows desktop application. It processes PDF and Office files on your own computer without sending document bytes to a third-party document service.

Original files are stored once and never modified in place. Every successful operation creates a new version, a SHA-256 digest, and an append-only audit event.

> LocalPDF is intended for low-risk personal use. Its signature-lite workflow is not a qualified or regulated electronic signature, certificate-based signature, or identity-verification service.

## Windows executable

The Windows release is a self-contained desktop application:

1. Download `LocalPDF.exe` from the repository's [Releases](https://github.com/YusufHasanSaygili/LocalPDF/releases) page.
2. Run `LocalPDF.exe`.
3. The application opens in its own Windows desktop window. No Docker, PostgreSQL, Python, Node.js, or browser installation is required.

The executable contains its local API, SQLite database engine, web runtime, and desktop shell. On first launch it extracts versioned runtime files under:

```text
%LOCALAPPDATA%\LocalPDF\app\0.2.0
```

Persistent documents and generated files are stored separately under:

```text
%LOCALAPPDATA%\LocalPDF\data
```

Closing the LocalPDF window stops its private background processes. Documents, generated files, and the embedded SQLite database remain in the data directory. The application binds its internal HTTP endpoints only to `127.0.0.1` and does not require Docker.

## Run from source

The Docker Compose stack remains available for source development and integration testing. Requirements:

- Docker Desktop with Docker Compose v2
- Git, only when cloning the repository

From the repository root:

```powershell
docker compose up --build
```

After startup:

- Web interface: `http://localhost:3000`
- API health: `http://localhost:8000/health`
- API readiness: `http://localhost:8000/ready`
- OpenAPI documentation: `http://localhost:8000/docs`

A private `.env` file is optional. Copy the example only when you need to customize local settings:

```powershell
Copy-Item .env.example .env
```

Services are published only on `127.0.0.1` by default. Public internet deployment and multi-user isolation are not supported.

## Features

- PDF, DOCX, XLSX, and PPTX intake with extension and content validation
- Immutable original storage, safe relative paths, streaming SHA-256, and atomic output publication
- PostgreSQL job queue with `SKIP LOCKED`, leases, heartbeats, retry, and stale-job recovery
- Progressive WebP previews and warnings for forms, fonts, encryption, and existing digital signatures
- PDF merge and range/every-N/single-page split with hashed ZIP manifests
- Page reorder and 90/180/270-degree rotation
- Lossless, balanced, and smallest compression profiles with before/after reports
- Deterministic text watermarks
- Permanent area redaction through a rasterized output pipeline; overlay-only redaction is not published
- Local OCR through Tesseract
- Isolated Office-to-PDF conversion through LibreOffice
- Signature-lite fields, hashed single-use invitation tokens, explicit consent versioning, manual/SMTP delivery outcomes, flattening, and final hash sealing
- Expiry state, two-step deletion, portable document export, and deterministic audit JSONL
- PostgreSQL dump plus file/hash-manifest backup and verified restore into a new target

## Architecture

```text
Browser -> Next.js 15 -> FastAPI -> PostgreSQL
                          |             ^
                          v             |
                     local store <- worker
                     pikepdf / Poppler / Tesseract / LibreOffice
```

The API never performs long-running PDF transformations inside an HTTP request. It validates the request and creates an operation and job. The worker claims that job, processes it in an isolated temporary directory, reopens generated PDFs with pikepdf, computes hashes, and publishes validated outputs with an atomic rename.

PostgreSQL triggers reject updates and deletes against original and audit-event rows in the containerized development stack. The Windows desktop release uses an embedded SQLite database and a single local worker.

The default data layout is:

```text
data/
  originals/<document-id>/<sha256>.<ext>
  outputs/<document-id>/v000001/<output-id>.pdf
  previews/<source-id>/page-000001.webp
  exports/<job-id>/*.zip
  backups/<job-id>/localpdf-backup.zip
  tmp/<job-id>/
```

`data/`, `.env`, backups, real user documents, and generated previews are excluded from Git. The application contains no telemetry, analytics, remote font/CDN integration, hosted control plane, or vendor document API. SMTP is used only when the user explicitly enables it; otherwise signature-lite uses a manual invitation link.

## Build the Windows executable

Requirements:

- .NET 8 SDK
- A clean Git working tree

Run:

```powershell
.\tools\windows-launcher\build.ps1
```

The build script creates a self-contained `win-x64` executable and SHA-256 file:

```text
dist\LocalPDF.exe
dist\LocalPDF.exe.sha256
```

The executable embeds only the tracked runtime application files from Git `HEAD`; it does not embed `.env`, document data, backups, local caches, or development virtual environments.

## Validation

Container validation:

```powershell
docker compose build
docker compose run --rm api pytest -q
docker compose run --rm api ruff check .
docker compose run --rm api mypy app
docker compose run --rm web npm run lint
docker compose run --rm web npm run typecheck
docker compose run --rm web npm test
docker compose up -d
docker compose run --rm e2e npm test
docker compose down
```

Focused development checks without Docker:

```powershell
cd services/api
uv sync --python 3.12 --all-extras
uv run pytest -q
uv run ruff check .
uv run mypy app

cd ../../apps/web
npm ci
npm run lint
npm run typecheck
npm test
npm run build
```

## Backup and restore

Create a PostgreSQL dump and verified store archive while LocalPDF is running:

```powershell
.\scripts\backup.ps1 -Destination "D:\LocalPDF-Backups"
```

Restore never overwrites the active data directory or database volume. Stop the stack and use a new, empty destination:

```powershell
docker compose down
.\scripts\restore.ps1 `
  -Archive "D:\LocalPDF-Backups\localpdf-....zip" `
  -Destination ".\data-restored"
```

The restore script rejects path traversal and symlink entries, checks the manifest version, verifies the database dump hash, verifies every stored file, creates a separate Compose project and PostgreSQL volume, restores into that empty database, and writes the resulting transition settings to `restore-info.json`.

## Security boundaries

- Uploaded documents are treated as hostile input.
- User-supplied filenames are display metadata and are never used as storage paths.
- Encrypted PDFs are blocked; LocalPDF asks for an unlocked copy and does not collect passwords.
- Tool processes use argument lists, allowlisted options, timeouts, and no shell interpolation.
- Raster image content in a redacted PDF still requires visual verification by the user.
- Deleting data from the application store cannot guarantee destruction of SSD wear-leveling copies, filesystem snapshots, sync-provider history, or earlier backups.
- If the host operating system or Docker daemon is compromised, LocalPDF cannot provide a confidentiality guarantee.

See [PROJECT_SPEC.md](PROJECT_SPEC.md), [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md), [SECURITY_PRIVACY.md](SECURITY_PRIVACY.md), and [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md) for the full product and security contracts.

## Current verification limitation

The Docker Compose deployment and the Docker-free Windows desktop runtime are separate packaging targets. The Windows build is currently an alpha release and should be tested with copies of documents until the complete desktop acceptance suite is finished.
