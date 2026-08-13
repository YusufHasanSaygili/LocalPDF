from pathlib import Path

import pytest

from app.domain.errors import LocalPDFError
from app.domain.validation import parse_page_ranges, sanitize_filename, validate_permutation
from app.infrastructure.storage import LocalStorage


@pytest.mark.parametrize("name", ["../secret.pdf", "C:\\secret.pdf", "CON.pdf", "bad\x00.pdf"])
def test_sanitize_filename_rejects_path_and_reserved_names(name: str) -> None:
    with pytest.raises(LocalPDFError) as error:
        sanitize_filename(name)
    assert error.value.code == "FILENAME_INVALID"


def test_sanitize_filename_preserves_unicode_display_name() -> None:
    display, safe = sanitize_filename("Sözleşme 2026.pdf")
    assert display == "Sözleşme 2026.pdf"
    assert safe.endswith(".pdf")
    assert "/" not in safe and "\\" not in safe


def test_page_range_parser_and_overlap_policy() -> None:
    assert parse_page_ranges("1-3,5,8-10", 10) == [[1, 2, 3], [5], [8, 9, 10]]
    with pytest.raises(LocalPDFError, match="örtüşemez"):
        parse_page_ranges("1-3,3-4", 5)
    with pytest.raises(LocalPDFError) as error:
        parse_page_ranges("6", 5)
    assert error.value.code == "PAGE_OUT_OF_BOUNDS"


def test_permutation_requires_every_page_once() -> None:
    validate_permutation([3, 1, 2], 3)
    with pytest.raises(LocalPDFError):
        validate_permutation([1, 1, 3], 3)


def test_storage_resolver_never_escapes_root(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    assert storage.resolve("tmp/file.pdf", must_exist=False).is_relative_to(tmp_path)
    with pytest.raises(LocalPDFError):
        storage.resolve("../outside.pdf", must_exist=False)
