import os
import shutil
import subprocess
from pathlib import Path

from app.domain.errors import ToolError
from app.settings import get_settings


def executable(name: str) -> str | None:
    return shutil.which(name)


def run_tool(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout or get_settings().tool_timeout_seconds,
            shell=False,
            env={**os.environ, **env} if env else None,
        )
    except FileNotFoundError as exc:
        raise ToolError(
            "TOOL_UNAVAILABLE", "Gerekli yerel araç kurulu değil.", status_code=503
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError("TOOL_TIMEOUT", "Yerel belge işlemi zaman aşımına uğradı.") from exc
    except subprocess.CalledProcessError as exc:
        raise ToolError("TOOL_FAILED", "Yerel belge aracı işlemi tamamlayamadı.") from exc


def tool_version(name: str, args: list[str]) -> str | None:
    binary = executable(name)
    if not binary:
        return None
    try:
        output = subprocess.run(
            [binary, *args], check=False, capture_output=True, text=True, timeout=5, shell=False
        )
        return (output.stdout or output.stderr).splitlines()[0].strip()
    except (OSError, subprocess.SubprocessError, IndexError):
        return "available"
