# LocalPDF 2.0

LocalPDF is a private, Docker-free Windows desktop toolbox for organizing, converting, editing, securing, and understanding PDF files. All document processing runs on the local computer; document bytes are never uploaded to a vendor service.

Original files are immutable. Every PDF-producing operation creates a separate version with its own SHA-256 hash and append-only audit event.

## Download for Windows

1. Open the repository's [Releases](https://github.com/YusufHasanSaygili/LocalPDF/releases) page.
2. Download `LocalPDF.exe` from the latest release.
3. Run it. No Docker, Python, Node.js, PostgreSQL, LibreOffice, Tesseract, or browser installation is required.

The self-contained executable includes the desktop window, local API, SQLite database, web interface, OCR engine, document converters, and offline English–Turkish translation models.

Application files are extracted to:

```text
%LOCALAPPDATA%\LocalPDF\app\2.0.0
```

Documents and generated results remain under:

```text
%LOCALAPPDATA%\LocalPDF\data
```

Closing the LocalPDF window stops its private background processes. Its internal endpoints bind only to `127.0.0.1`.

## Tools in 2.0

### Organize PDF

- Merge PDF
- Split PDF
- Remove pages
- Extract pages
- Organize/reorder PDF
- Scan images to PDF

### Optimize PDF

- Compress PDF
- Repair PDF
- OCR PDF with an embedded offline OCR engine

### Convert to PDF

- JPG and other common images to PDF
- Word (DOCX) to PDF
- PowerPoint (PPTX) to PDF
- Excel (XLSX) to PDF
- HTML to PDF

### Convert from PDF

- PDF to JPG archive
- PDF to Word
- PDF to PowerPoint
- PDF to Excel
- PDF to PDF/A-2b profile

### Edit PDF

- Rotate PDF
- Add page numbers
- Add watermark
- Crop PDF
- Add text to PDF
- Add fillable PDF form fields

### PDF security

- Unlock password-protected PDF
- Protect PDF with AES-256 encryption
- Signature-lite consent and hash sealing
- Permanent rasterized redaction
- Textual PDF comparison report

### PDF intelligence

- Offline extractive summarizer
- Offline English ↔ Turkish translation
- PDF to Markdown

> Signature-lite is intended for low-risk consent workflows. It is not a qualified electronic signature, certificate-based signature, or identity-verification service.

## Supported input files

`PDF`, `DOCX`, `XLSX`, `PPTX`, `JPG`, `JPEG`, `PNG`, `TIFF`, `BMP`, `WEBP`, `HTML`, and `HTM`.

## Privacy and security

- No telemetry, analytics, remote fonts, hosted control plane, or vendor document API.
- Filenames are display metadata and never become storage paths.
- Passwords are used only in memory for the requested operation and are not written to logs.
- Redaction removes the original page content from the generated result by rasterizing the page.
- Deleting data cannot erase copies already captured by backups, filesystem snapshots, or SSD wear leveling.
- If Windows itself is compromised, LocalPDF cannot provide a confidentiality guarantee.

## Run from source

Requirements: Python 3.12, `uv`, Node.js 22, and npm.

API:

```powershell
cd services/api
uv sync --python 3.12 --all-extras
$env:LOCALPDF_DATABASE_URL = "sqlite:///./localpdf-dev.sqlite3"
$env:LOCALPDF_LOCAL_DATA_DIR = "./localpdf-dev-data"
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Worker, in a second terminal:

```powershell
cd services/api
$env:LOCALPDF_DATABASE_URL = "sqlite:///./localpdf-dev.sqlite3"
$env:LOCALPDF_LOCAL_DATA_DIR = "./localpdf-dev-data"
uv run python -m app.worker.main
```

Web interface, in a third terminal:

```powershell
cd apps/web
npm ci
npm run dev
```

Open `http://127.0.0.1:3000`.

## Build the Windows executable

Requirements: Python 3.12 with `uv`, Node.js 22, npm, .NET 8 SDK, and a clean Git working tree.

```powershell
.\tools\windows-launcher\build.ps1
```

The build downloads the two open Argos translation model packages, embeds all runtimes, and writes:

```text
dist\LocalPDF.exe
dist\LocalPDF.exe.sha256
```

## Validation

```powershell
cd services/api
uv run pytest -q
uv run ruff check app tests
uv run mypy app tests

cd ../../apps/web
npm run lint
npm run typecheck
npm test
npm run build
```

The toolbox tests execute every V2 operation family, including Office conversion, OCR, encryption, form fields, comparison, summarization, and offline translation.

## Architecture

```text
Windows desktop shell
        |
        v
Next.js UI -> FastAPI -> SQLite job queue -> local worker
                                        |-> pikepdf / PyMuPDF
                                        |-> RapidOCR / ONNX Runtime
                                        |-> embedded document converters
                                        `-> CTranslate2 / Argos models
```

Long-running work never runs inside an HTTP request. The local worker validates generated PDFs, computes SHA-256 hashes, and atomically publishes results while retaining the original.
