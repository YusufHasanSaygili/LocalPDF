#!/usr/bin/env python3
"""Create a verified LocalPDF archive without including secrets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def run(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True, shell=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    destination = args.destination.resolve()
    data_dir = args.data_dir.resolve()
    if destination in {ROOT.resolve(), data_dir}:
        parser.error("Destination cannot be the repository or data root")
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    final_path = destination / f"localpdf-{stamp}.zip"
    with tempfile.TemporaryDirectory(prefix="localpdf-backup-", dir=destination) as temp_name:
        temp = Path(temp_name)
        database_dump = temp / "database.dump"
        run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "db",
                "pg_dump",
                "-U",
                os.getenv("POSTGRES_USER", "localpdf"),
                "-d",
                os.getenv("POSTGRES_DB", "localpdf"),
                "--format=custom",
                "--file=/tmp/localpdf-backup.dump",
            ]
        )
        run(["docker", "compose", "cp", "db:/tmp/localpdf-backup.dump", str(database_dump)])
        run(["docker", "compose", "exec", "-T", "db", "rm", "-f", "/tmp/localpdf-backup.dump"])
        files: list[dict[str, object]] = []
        staged_store = temp / "store"
        for directory in ("originals", "outputs", "previews", "exports"):
            source_root = data_dir / directory
            if not source_root.exists():
                continue
            for source in sorted(
                path for path in source_root.rglob("*") if path.is_file() and not path.is_symlink()
            ):
                relative = source.relative_to(data_dir)
                target = staged_store / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                files.append(
                    {
                        "relative_path": relative.as_posix(),
                        "byte_size": target.stat().st_size,
                        "sha256": sha256(target),
                    }
                )
        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "app_version": "0.1.0",
            "database_sha256": sha256(database_dump),
            "file_count": len(files),
        }
        (temp / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        (temp / "files.jsonl").write_text(
            "".join(json.dumps(item, sort_keys=True) + "\n" for item in files), encoding="utf-8"
        )
        (temp / "README_RESTORE.txt").write_text(
            "Stop LocalPDF and run scripts/restore.py into a new, empty target. The active data directory is never overwritten.\n",
            encoding="utf-8",
        )
        temporary_archive = destination / f".{final_path.name}.part"
        with ZipFile(temporary_archive, "w", ZIP_DEFLATED) as archive:
            for source in sorted(path for path in temp.rglob("*") if path.is_file()):
                archive.write(source, source.relative_to(temp).as_posix())
        os.replace(temporary_archive, final_path)
    print(json.dumps({"archive": str(final_path), "sha256": sha256(final_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
