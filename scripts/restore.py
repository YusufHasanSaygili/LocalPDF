#!/usr/bin/env python3
"""Verify and stage a LocalPDF backup into an empty destination."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in name


def run(args: list[str], environment: dict[str, str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True, shell=False, env=environment)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--stage-only", action="store_true")
    args = parser.parse_args()
    archive_path = args.archive.resolve(strict=True)
    destination = args.destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        parser.error("Restore destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(archive_path) as archive:
            for info in archive.infolist():
                if (
                    not safe_member(info.filename)
                    or (info.external_attr >> 16) & 0o170000 == 0o120000
                ):
                    raise ValueError(f"Unsafe archive entry: {info.filename}")
            archive.extractall(destination)
        manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1:
            raise ValueError("Unsupported backup schema")
        if sha256(destination / "database.dump") != manifest["database_sha256"]:
            raise ValueError("Database dump hash mismatch")
        records = [
            json.loads(line)
            for line in (destination / "files.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        ]
        for record in records:
            path = (destination / "store" / record["relative_path"]).resolve()
            path.relative_to((destination / "store").resolve())
            if path.stat().st_size != record["byte_size"] or sha256(path) != record["sha256"]:
                raise ValueError(f"Store hash mismatch: {record['relative_path']}")
        if args.verify_only:
            shutil.rmtree(destination)
        elif not args.stage_only:
            project_suffix = hashlib.sha256(str(destination).encode()).hexdigest()[:10]
            project_name = f"localpdf-restored-{project_suffix}"
            environment = dict(os.environ)
            environment["COMPOSE_PROJECT_NAME"] = project_name
            environment["LOCAL_DATA_DIR"] = str(destination / "store")
            run(["docker", "compose", "up", "-d", "db"], environment)
            try:
                run(
                    [
                        "docker",
                        "compose",
                        "cp",
                        str(destination / "database.dump"),
                        "db:/tmp/localpdf-restore.dump",
                    ],
                    environment,
                )
                run(
                    [
                        "docker",
                        "compose",
                        "exec",
                        "-T",
                        "db",
                        "pg_restore",
                        "-U",
                        environment.get("POSTGRES_USER", "localpdf"),
                        "-d",
                        environment.get("POSTGRES_DB", "localpdf"),
                        "--exit-on-error",
                        "/tmp/localpdf-restore.dump",
                    ],
                    environment,
                )
                run(
                    [
                        "docker",
                        "compose",
                        "exec",
                        "-T",
                        "db",
                        "rm",
                        "-f",
                        "/tmp/localpdf-restore.dump",
                    ],
                    environment,
                )
            finally:
                run(["docker", "compose", "stop", "db"], environment)
            (destination / "restore-info.json").write_text(
                json.dumps(
                    {
                        "compose_project_name": project_name,
                        "local_data_dir": str(destination / "store"),
                        "database_volume": f"{project_name}_postgres-data",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        print(
            json.dumps(
                {
                    "verified": True,
                    "file_count": len(records),
                    "destination": str(destination),
                    "database_restored": not args.verify_only and not args.stage_only,
                }
            )
        )
        return 0
    except Exception:
        if destination.exists():
            shutil.rmtree(destination)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
