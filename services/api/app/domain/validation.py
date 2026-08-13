import re
import unicodedata
from pathlib import PurePath

from app.domain.errors import LocalPDFError

WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
CONTROL_AND_BIDI = re.compile(r"[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]")


def sanitize_filename(value: str) -> tuple[str, str]:
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized or CONTROL_AND_BIDI.search(normalized):
        raise LocalPDFError("FILENAME_INVALID", "Dosya adı güvenli değil.")
    if len(normalized) > 240:
        normalized = normalized[:240]
    basename = PurePath(normalized.replace("\\", "/")).name
    if basename != normalized or normalized.startswith(("/", "\\")) or ":" in normalized:
        raise LocalPDFError("FILENAME_INVALID", "Dosya yolu içeren adlar kabul edilmez.")
    stem = basename.rsplit(".", 1)[0].rstrip(". ")
    if stem.upper() in WINDOWS_RESERVED:
        raise LocalPDFError("FILENAME_INVALID", "Bu dosya adı işletim sistemi için ayrılmıştır.")
    display = basename.rstrip(". ")
    if not display:
        raise LocalPDFError("FILENAME_INVALID", "Dosya adı güvenli değil.")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", display).strip(".-") or "document"
    extension = display.rsplit(".", 1)[1].lower() if "." in display else ""
    if extension:
        safe = f"{safe.rsplit('.', 1)[0][:120]}.{extension}"
    return display, safe


def parse_page_ranges(expression: str, page_count: int) -> list[list[int]]:
    if not expression.strip():
        raise LocalPDFError("PAGE_RANGE_INVALID", "En az bir sayfa aralığı girin.")
    result: list[list[int]] = []
    seen: set[int] = set()
    for raw in expression.split(","):
        token = raw.strip()
        if not token:
            raise LocalPDFError("PAGE_RANGE_INVALID", "Sayfa aralığı geçersiz.")
        match = re.fullmatch(r"(\d+)(?:-(\d+))?", token)
        if not match:
            raise LocalPDFError("PAGE_RANGE_INVALID", f"'{token}' geçerli bir aralık değil.")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end < start:
            raise LocalPDFError("PAGE_RANGE_INVALID", "Ters veya sıfır aralık kullanılamaz.")
        if end > page_count:
            raise LocalPDFError("PAGE_OUT_OF_BOUNDS", "Sayfa aralığı belge sınırını aşıyor.")
        pages = list(range(start, end + 1))
        if seen.intersection(pages):
            raise LocalPDFError("PAGE_RANGE_INVALID", "Sayfa aralıkları örtüşemez.")
        seen.update(pages)
        result.append(pages)
    return result


def validate_permutation(pages: list[int], page_count: int) -> None:
    if len(pages) != page_count or sorted(pages) != list(range(1, page_count + 1)):
        raise LocalPDFError(
            "PAGE_RANGE_INVALID", "Sıralama her sayfayı tam olarak bir kez içermelidir."
        )
