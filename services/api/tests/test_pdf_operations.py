from pathlib import Path

import pikepdf
import pytest
from reportlab.pdfgen import canvas

from app.infrastructure.tools.pdf import compress, merge, redact, reorder, rotate, split, watermark
from app.infrastructure.tools.system import executable


def make_pdf(path: Path, labels: list[str]) -> None:
    draw = canvas.Canvas(str(path), pagesize=(300, 400))
    for label in labels:
        draw.drawString(50, 200, label)
        draw.showPage()
    draw.save()


def test_merge_split_reorder_rotate_and_watermark(tmp_path: Path) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    make_pdf(first, ["A1", "A2"])
    make_pdf(second, ["B1"])

    merged = tmp_path / "merged.pdf"
    assert merge([second, first], merged) == 3
    parts = split(merged, tmp_path, {"mode": "range", "ranges": "1,2-3"})
    assert [len(pikepdf.open(path).pages) for path in parts] == [1, 2]

    reordered = tmp_path / "reordered.pdf"
    assert reorder(merged, reordered, [3, 1, 2]) == 3
    rotated = tmp_path / "rotated.pdf"
    assert rotate(reordered, rotated, [2], 90) == 3
    with pikepdf.open(rotated) as pdf:
        assert int(pdf.pages[0].get("/Rotate", 0)) == 0
        assert int(pdf.pages[1].get("/Rotate", 0)) == 90

    marked = tmp_path / "marked.pdf"
    assert watermark(rotated, marked, {"text": "LOCAL", "opacity": 0.3}) == 3


def test_compression_report_matches_disk_sizes(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "compressed.pdf"
    make_pdf(source, ["compress me"])

    page_count, report = compress(source, output, "lossless")
    assert page_count == 1
    assert report["before_bytes"] == source.stat().st_size
    assert report["after_bytes"] == output.stat().st_size
    assert report["difference_bytes"] == output.stat().st_size - source.stat().st_size


def test_redaction_rasterizes_content_instead_of_overlay_only(tmp_path: Path) -> None:
    poppler = executable("pdftoppm")
    if not poppler or Path(poppler).suffix.lower() == ".cmd":
        pytest.skip("A native Poppler executable is required for this integration test")
    source = tmp_path / "sensitive.pdf"
    output = tmp_path / "redacted.pdf"
    make_pdf(source, ["SECRET VALUE"])

    assert (
        redact(
            source,
            output,
            {
                "rectangles": [
                    {
                        "page_number": 1,
                        "x_pt": 0,
                        "y_pt": 0,
                        "width_pt": 300,
                        "height_pt": 400,
                    }
                ]
            },
            tmp_path,
        )
        == 1
    )
    with pikepdf.open(output) as pdf:
        streams = b"".join(page.Contents.read_bytes() for page in pdf.pages)
    assert b"SECRET VALUE" not in streams
