import io
import math
from pathlib import Path
from typing import Any, cast

import pikepdf
import pymupdf  # type: ignore[import-untyped]
from PIL import Image, ImageDraw
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.domain.errors import LocalPDFError
from app.domain.validation import parse_page_ranges, validate_permutation
from app.infrastructure.tools.system import executable, run_tool


def inspect_pdf(path: Path, max_pages: int) -> tuple[int, dict[str, Any]]:
    try:
        with pikepdf.open(path) as pdf:
            page_count = len(pdf.pages)
            if page_count < 1:
                raise LocalPDFError("PDF_CORRUPT", "PDF en az bir sayfa içermelidir.")
            if page_count > max_pages:
                raise LocalPDFError("PAGE_LIMIT_EXCEEDED", "PDF sayfa limiti aşıldı.")
            root = cast(Any, pdf.Root)
            acroform = "/AcroForm" in root
            signatures = False
            if acroform:
                fields = root.AcroForm.get("/Fields", [])
                signatures = any(str(field.get("/FT", "")) == "/Sig" for field in fields)
            features = {
                "encrypted": bool(pdf.is_encrypted),
                "acroform": acroform,
                "signatures": signatures,
                "embedded_fonts": _has_embedded_fonts(pdf),
                "warnings": _warnings(acroform, signatures),
            }
            return page_count, features
    except pikepdf.PasswordError as exc:
        raise LocalPDFError(
            "PDF_ENCRYPTED",
            "Bu PDF parola ile korunuyor. Kilidi kaldırılmış bir kopya yükleyin.",
            details={"allowed_action": "upload_unlocked_copy"},
        ) from exc
    except pikepdf.PdfError as exc:
        raise LocalPDFError("PDF_CORRUPT", "PDF açılamadı veya bozuk.") from exc


def _has_embedded_fonts(pdf: pikepdf.Pdf) -> bool:
    for page in pdf.pages:
        resources = cast(Any, page.get("/Resources"))
        if not resources:
            continue
        for _, font in resources.get("/Font", {}).items():
            descriptor = font.get("/FontDescriptor")
            if descriptor and any(
                key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3")
            ):
                return True
    return False


def _warnings(acroform: bool, signatures: bool) -> list[str]:
    warnings: list[str] = []
    if acroform:
        warnings.append("may_flatten_forms")
    if signatures:
        warnings.append("invalidates_signature")
    warnings.append("may_change_fonts")
    return warnings


def validate_output(path: Path, expected_pages: int | None = None) -> int:
    page_count, _ = inspect_pdf(path, max_pages=100_000)
    if expected_pages is not None and page_count != expected_pages:
        raise LocalPDFError(
            "OUTPUT_VALIDATION_FAILED", "Üretilen PDF beklenen sayfa sayısını taşımıyor."
        )
    return page_count


def merge(inputs: list[Path], output: Path) -> int:
    if len(inputs) < 2:
        raise LocalPDFError("INPUT_INVALID", "Birleştirme için en az iki PDF seçin.")
    result = pikepdf.Pdf.new()
    count = 0
    for source in inputs:
        with pikepdf.open(source) as pdf:
            result.pages.extend(pdf.pages)
            count += len(pdf.pages)
    result.save(output)
    return validate_output(output, count)


def split(source: Path, output_dir: Path, parameters: dict[str, Any]) -> list[Path]:
    outputs: list[Path] = []
    with pikepdf.open(source) as pdf:
        count = len(pdf.pages)
        mode = parameters.get("mode", "range")
        if mode == "range":
            groups = parse_page_ranges(str(parameters.get("ranges", "")), count)
        elif mode == "every_n":
            every_n = int(parameters.get("every_n", 0))
            if every_n < 1:
                raise LocalPDFError("PAGE_RANGE_INVALID", "Bölme aralığı en az 1 olmalıdır.")
            groups = [
                list(range(start, min(start + every_n, count + 1)))
                for start in range(1, count + 1, every_n)
            ]
        elif mode == "single_pages":
            groups = [[page] for page in range(1, count + 1)]
        else:
            raise LocalPDFError("PAGE_RANGE_INVALID", "Bölme modu desteklenmiyor.")
        for index, group in enumerate(groups, start=1):
            target = output_dir / f"part-{index:03d}.pdf"
            part = pikepdf.Pdf.new()
            part.pages.extend(pdf.pages[page - 1] for page in group)
            part.save(target)
            validate_output(target, len(group))
            outputs.append(target)
    return outputs


def reorder(source: Path, output: Path, pages: list[int]) -> int:
    with pikepdf.open(source) as pdf:
        validate_permutation(pages, len(pdf.pages))
        result = pikepdf.Pdf.new()
        result.pages.extend(pdf.pages[index - 1] for index in pages)
        result.save(output)
    return validate_output(output, len(pages))


def rotate(source: Path, output: Path, pages: list[int], degrees: int) -> int:
    if degrees not in (90, 180, 270):
        raise LocalPDFError("INPUT_INVALID", "Döndürme 90, 180 veya 270 derece olmalıdır.")
    with pikepdf.open(source) as pdf:
        selected = set(pages)
        if not selected or min(selected) < 1 or max(selected) > len(pdf.pages):
            raise LocalPDFError("PAGE_OUT_OF_BOUNDS", "Seçili sayfa belge sınırını aşıyor.")
        for page_number, page in enumerate(pdf.pages, start=1):
            if page_number in selected:
                current = int(cast(Any, page.get("/Rotate")) or 0)
                page.Rotate = (current + degrees) % 360
        pdf.save(output)
        count = len(pdf.pages)
    return validate_output(output, count)


def compress(source: Path, output: Path, profile: str) -> tuple[int, dict[str, Any]]:
    if profile not in {"lossless", "balanced", "smallest"}:
        raise LocalPDFError("INPUT_INVALID", "Sıkıştırma profili desteklenmiyor.")
    before = source.stat().st_size
    with pikepdf.open(source) as pdf:
        pdf.save(
            output,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
            recompress_flate=profile != "lossless",
            linearize=profile == "balanced",
        )
        count = len(pdf.pages)
    validate_output(output, count)
    after = output.stat().st_size
    report = {
        "profile": profile,
        "before_bytes": before,
        "after_bytes": after,
        "difference_bytes": after - before,
        "percent_change": round(((after - before) / before * 100), 2) if before else 0,
        "larger_than_source": after > before,
    }
    return count, report


def watermark(source: Path, output: Path, parameters: dict[str, Any]) -> int:
    text = str(parameters.get("text", "")).strip()
    opacity = float(parameters.get("opacity", 0.2))
    if not text or not 0.01 <= opacity <= 1:
        raise LocalPDFError("INPUT_INVALID", "Görünür bir filigran metni ve opaklığı girin.")
    pages = set(int(value) for value in parameters.get("pages", []))
    with pikepdf.open(source) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            if pages and page_number not in pages:
                continue
            width, height = _page_size(page)
            layer_bytes = io.BytesIO()
            draw = canvas.Canvas(layer_bytes, pagesize=(width, height))
            draw.saveState()
            draw.setFillColor(Color(0.08, 0.22, 0.32, alpha=opacity))
            draw.setFont("Helvetica-Bold", float(parameters.get("font_size", 38)))
            draw.translate(width / 2, height / 2)
            draw.rotate(float(parameters.get("rotation", -35)))
            draw.drawCentredString(0, 0, text)
            draw.restoreState()
            draw.save()
            layer_bytes.seek(0)
            with pikepdf.open(layer_bytes) as overlay:
                page.add_overlay(overlay.pages[0], None)
        pdf.save(output)
        count = len(pdf.pages)
    return validate_output(output, count)


def redact(source: Path, output: Path, parameters: dict[str, Any], workdir: Path) -> int:
    rectangles = parameters.get("rectangles", [])
    if not rectangles:
        raise LocalPDFError("INPUT_INVALID", "En az bir redaksiyon alanı seçin.")
    with pikepdf.open(source) as pdf:
        page_count = len(pdf.pages)
        page_sizes = [_page_size(page) for page in pdf.pages]
    with pymupdf.open(source) as rendered_source:
        if len(rendered_source) != page_count:
            raise LocalPDFError("OUTPUT_VALIDATION_FAILED", "Redaksiyon sayfaları doğrulanamadı.")
        rendered = canvas.Canvas(str(output))
        for page_number, page in enumerate(rendered_source, start=1):
            width_pt, height_pt = page_sizes[page_number - 1]
            pixmap = page.get_pixmap(dpi=180, alpha=False)
            with Image.open(io.BytesIO(pixmap.tobytes("png"))) as opened_image:
                image = opened_image.convert("RGB")
                draw = ImageDraw.Draw(image)
                for rect in rectangles:
                    if int(rect.get("page_number", 0)) != page_number:
                        continue
                    x = float(rect.get("x_pt", -1))
                    y = float(rect.get("y_pt", -1))
                    width = float(rect.get("width_pt", 0))
                    height = float(rect.get("height_pt", 0))
                    if (
                        x < 0
                        or y < 0
                        or width <= 0
                        or height <= 0
                        or x + width > width_pt
                        or y + height > height_pt
                    ):
                        raise LocalPDFError(
                            "INPUT_INVALID", "Redaksiyon alanı sayfa sınırları dışında."
                        )
                    scale_x = image.width / width_pt
                    scale_y = image.height / height_pt
                    box = (
                        math.floor(x * scale_x),
                        math.floor((height_pt - y - height) * scale_y),
                        math.ceil((x + width) * scale_x),
                        math.ceil((height_pt - y) * scale_y),
                    )
                    draw.rectangle(box, fill="black")
                rendered.setPageSize((width_pt, height_pt))
                rendered.drawImage(ImageReader(image), 0, 0, width=width_pt, height=height_pt)
                rendered.showPage()
        rendered.save()
    return validate_output(output, page_count)


def ocr(source: Path, output: Path, parameters: dict[str, Any], workdir: Path) -> int:
    pdftoppm = executable("pdftoppm")
    tesseract = executable("tesseract")
    if not pdftoppm or not tesseract:
        raise LocalPDFError("TOOL_UNAVAILABLE", "OCR için yerel araçlar hazır değil.")
    languages = "+".join(parameters.get("languages", ["eng"]))
    prefix = workdir / "ocr-page"
    run_tool([pdftoppm, "-png", "-r", "200", str(source), str(prefix)], cwd=workdir)
    image_paths = sorted(workdir.glob("ocr-page-*.png"))
    result = pikepdf.Pdf.new()
    for index, image_path in enumerate(image_paths, start=1):
        base = workdir / f"ocr-result-{index:04d}"
        args = [tesseract, str(image_path), str(base), "-l", languages, "pdf"]
        if parameters.get("deskew"):
            args.extend(["-c", "textord_straight_baselines=1"])
        run_tool(args, cwd=workdir)
        with pikepdf.open(base.with_suffix(".pdf")) as page_pdf:
            result.pages.extend(page_pdf.pages)
    result.save(output)
    return validate_output(output, len(image_paths))


def office_to_pdf(source: Path, output: Path, workdir: Path) -> int:
    libreoffice = executable("libreoffice") or executable("soffice")
    if not libreoffice:
        raise LocalPDFError("TOOL_UNAVAILABLE", "LibreOffice hazır değil.", status_code=503)
    profile = workdir / "lo-profile"
    converted = workdir / "converted"
    profile.mkdir()
    converted.mkdir()
    run_tool(
        [
            libreoffice,
            "--headless",
            "--nologo",
            "--nodefault",
            "--nolockcheck",
            "--norestore",
            f"-env:UserInstallation={profile.as_uri()}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(converted),
            str(source),
        ],
        cwd=workdir,
    )
    outputs = list(converted.glob("*.pdf"))
    if len(outputs) != 1:
        raise LocalPDFError("OUTPUT_VALIDATION_FAILED", "Office dönüşüm çıktısı bulunamadı.")
    outputs[0].replace(output)
    return validate_output(output)


def apply_signature(
    source: Path,
    output: Path,
    fields: list[dict[str, Any]],
    signer_name: str,
    consented_at: str,
) -> int:
    with pikepdf.open(source) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_fields = [field for field in fields if field["page_number"] == page_number]
            if not page_fields:
                continue
            width, height = _page_size(page)
            layer = io.BytesIO()
            draw = canvas.Canvas(layer, pagesize=(width, height))
            for field in page_fields:
                x, y = field["x_pt"], field["y_pt"]
                box_width, box_height = field["width_pt"], field["height_pt"]
                draw.setStrokeColorRGB(0.08, 0.22, 0.32)
                draw.setFillColorRGB(0.95, 0.98, 0.98)
                draw.roundRect(x, y, box_width, box_height, 4, stroke=1, fill=1)
                draw.setFillColorRGB(0.06, 0.12, 0.16)
                value = signer_name if field["type"] != "date" else consented_at[:10]
                draw.setFont("Helvetica", min(14, max(8, box_height * 0.35)))
                draw.drawString(x + 6, y + box_height / 2 - 4, value)
            draw.save()
            layer.seek(0)
            with pikepdf.open(layer) as overlay:
                page.add_overlay(overlay.pages[0], None)
        pdf.save(output)
        count = len(pdf.pages)
    return validate_output(output, count)


def _page_size(page: pikepdf.Page) -> tuple[float, float]:
    box = cast(Any, page.get("/CropBox") or page.MediaBox)
    return float(box[2] - box[0]), float(box[3] - box[1])
