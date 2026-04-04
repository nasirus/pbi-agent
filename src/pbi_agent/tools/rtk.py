"""Helpers for using a bundled RTK binary when available."""

from __future__ import annotations

import os
import platform
import stat
import subprocess
from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path
from typing import Iterator

from pbi_agent.tools.output import decode_output

RTK_REWRITE_TIMEOUT_SECONDS = 5.0

_RTK_BINARIES = {
    ("linux", "x86_64"): ("linux_x86_64", "rtk"),
    ("linux", "amd64"): ("linux_x86_64", "rtk"),
    ("linux", "aarch64"): ("linux_aarch64", "rtk"),
    ("linux", "arm64"): ("linux_aarch64", "rtk"),
    ("darwin", "x86_64"): ("macos_x86_64", "rtk"),
    ("darwin", "amd64"): ("macos_x86_64", "rtk"),
    ("darwin", "aarch64"): ("macos_arm64", "rtk"),
    ("darwin", "arm64"): ("macos_arm64", "rtk"),
    ("windows", "x86_64"): ("win_amd64", "rtk.exe"),
    ("windows", "amd64"): ("win_amd64", "rtk.exe"),
    ("windows", "arm64"): ("win_arm64", "rtk.exe"),
}


def get_embedded_rtk_path() -> Path:
    """Return the packaged RTK binary path for the current platform."""
    with _embedded_rtk_path() as path:
        return path


def rewrite_command_with_rtk(command: str) -> str:
    """Return an RTK-rewritten command, or the original on any failure."""
    if not command.strip():
        return command

    try:
        with _embedded_rtk_path() as rtk_path:
            completed = subprocess.run(
                [str(rtk_path), "rewrite", command],
                capture_output=True,
                text=False,
                check=False,
                timeout=RTK_REWRITE_TIMEOUT_SECONDS,
            )
    except (
        FileNotFoundError,
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
    ):
        return command

    rewritten_command = decode_output(completed.stdout).strip()
    if completed.returncode != 0 or not rewritten_command:
        return command
    return rewritten_command


@contextmanager
def _embedded_rtk_path() -> Iterator[Path]:
    resource = _resolve_embedded_rtk_resource()
    if not resource.is_file():
        raise FileNotFoundError("Bundled RTK binary is not available.")

    with as_file(resource) as resource_path:
        path = Path(resource_path)
        _ensure_executable(path)
        yield path


def _resolve_embedded_rtk_resource():
    bundle_directory, binary_name = _resolve_platform_binary()
    return files("pbi_agent").joinpath("_vendor", "rtk", bundle_directory, binary_name)


def _resolve_platform_binary() -> tuple[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()

    try:
        return _RTK_BINARIES[(system, machine)]
    except KeyError as exc:
        raise RuntimeError(
            "Bundled RTK is not available for "
            f"{platform.system()} {platform.machine()}."
        ) from exc


def _ensure_executable(path: Path) -> None:
    if os.name == "nt":
        return

    current_mode = path.stat().st_mode
    executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    if current_mode & executable_bits == executable_bits:
        return
    path.chmod(current_mode | executable_bits)
