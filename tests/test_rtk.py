from __future__ import annotations

import os
import stat
import subprocess
from contextlib import contextmanager
from pathlib import Path

from pbi_agent.tools import rtk


def test_get_embedded_rtk_path_returns_binary_and_sets_executable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    binary = tmp_path / "rtk"
    binary.write_text("binary", encoding="utf-8")
    binary.chmod(0o644)

    monkeypatch.setattr(rtk, "_resolve_embedded_rtk_resource", lambda: binary)

    resolved = rtk.get_embedded_rtk_path()

    assert resolved == binary
    if os.name != "nt":
        assert resolved.stat().st_mode & stat.S_IXUSR


def test_rewrite_command_with_rtk_returns_rewritten_command(monkeypatch) -> None:
    @contextmanager
    def fake_rtk_path():
        yield Path("/tmp/rtk")

    calls: list[object] = []

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=b"printf optimized",
            stderr=b"",
        )

    monkeypatch.setattr(rtk, "_embedded_rtk_path", fake_rtk_path)
    monkeypatch.setattr(rtk.subprocess, "run", fake_run)

    assert rtk.rewrite_command_with_rtk("printf original") == "printf optimized"
    assert calls == [
        (
            (["/tmp/rtk", "rewrite", "printf original"],),
            {
                "capture_output": True,
                "text": False,
                "check": False,
                "timeout": rtk.RTK_REWRITE_TIMEOUT_SECONDS,
            },
        )
    ]


def test_rewrite_command_with_rtk_falls_back_to_original_command(monkeypatch) -> None:
    @contextmanager
    def fake_rtk_path():
        yield Path("/tmp/rtk")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        del args, kwargs
        raise subprocess.TimeoutExpired(cmd="rtk rewrite", timeout=1.0)

    monkeypatch.setattr(rtk, "_embedded_rtk_path", fake_rtk_path)
    monkeypatch.setattr(rtk.subprocess, "run", fake_run)

    assert rtk.rewrite_command_with_rtk("printf original") == "printf original"
