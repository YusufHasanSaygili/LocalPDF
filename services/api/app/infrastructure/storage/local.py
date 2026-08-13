import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from app.domain.errors import LocalPDFError
from app.settings import get_settings


@dataclass(frozen=True)
class StoredFile:
    relative_path: str
    sha256: str
    byte_size: int


class LocalStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or get_settings().store_root).resolve()
        for directory in ("originals", "outputs", "previews", "exports", "backups", "tmp"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str, *, must_exist: bool = True) -> Path:
        if Path(relative_path).is_absolute() or PureWindowsPath(relative_path).is_absolute():
            raise LocalPDFError("PATH_INVALID", "Mutlak dosya yolu reddedildi.")
        raw_candidate = self.root / relative_path
        current = raw_candidate
        while current != self.root:
            if current.exists() and current.is_symlink():
                raise LocalPDFError("PATH_INVALID", "Sembolik bağlantı içeren yol reddedildi.")
            if current.parent == current:
                break
            current = current.parent
        candidate = raw_candidate.resolve(strict=False)
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise LocalPDFError("PATH_INVALID", "Güvenli olmayan dosya yolu reddedildi.") from exc
        if must_exist and (not candidate.exists() or candidate.is_symlink()):
            raise LocalPDFError("FILE_NOT_FOUND", "Dosya bulunamadı.", status_code=404)
        return candidate

    def job_directory(self, job_id: uuid.UUID) -> Path:
        path = self.resolve(f"tmp/{job_id}", must_exist=False)
        path.mkdir(parents=True, exist_ok=False)
        return path

    @staticmethod
    def hash_file(path: Path) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
        return digest.hexdigest(), size

    def publish_original(
        self, temp_path: Path, document_id: uuid.UUID, digest: str, extension: str
    ) -> StoredFile:
        relative = f"originals/{document_id}/{digest}.{extension}"
        target = self.resolve(relative, must_exist=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            temp_path.unlink(missing_ok=True)
        else:
            os.replace(temp_path, target)
            try:
                target.chmod(0o440)
            except OSError:
                pass
        actual_hash, size = self.hash_file(target)
        if actual_hash != digest:
            raise LocalPDFError(
                "OUTPUT_VALIDATION_FAILED", "Orijinal dosyanın hash doğrulaması başarısız oldu."
            )
        return StoredFile(relative, actual_hash, size)

    def publish_output(
        self,
        temp_path: Path,
        document_id: uuid.UUID,
        version_number: int,
        output_id: uuid.UUID,
        extension: str = "pdf",
    ) -> StoredFile:
        relative = f"outputs/{document_id}/v{version_number:06d}/{output_id}.{extension}"
        target = self.resolve(relative, must_exist=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise LocalPDFError("OUTPUT_VALIDATION_FAILED", "Çıktı yolu zaten mevcut.")
        os.replace(temp_path, target)
        digest, size = self.hash_file(target)
        return StoredFile(relative, digest, size)
