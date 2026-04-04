from __future__ import annotations

import hashlib
import importlib.util
import io
import stat
import sys
import tarfile
import types
import zipfile
from pathlib import Path

import pytest

from pbi_agent import rtk_vendor

_HATCHLING_MODULE_NAMES = [
    "hatchling",
    "hatchling.builders",
    "hatchling.builders.hooks",
    "hatchling.builders.hooks.plugin",
    "hatchling.builders.hooks.plugin.interface",
]
for name in _HATCHLING_MODULE_NAMES:
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules["hatchling.builders.hooks.plugin.interface"].BuildHookInterface = type(
    "BuildHookInterface",
    (),
    {},
)
_ROOT = Path(__file__).resolve().parents[1]

_HATCH_BUILD_SPEC = importlib.util.spec_from_file_location(
    "hatch_build", _ROOT / "hatch_build.py"
)
assert _HATCH_BUILD_SPEC is not None
assert _HATCH_BUILD_SPEC.loader is not None
_HATCH_BUILD_MODULE = importlib.util.module_from_spec(_HATCH_BUILD_SPEC)
_HATCH_BUILD_SPEC.loader.exec_module(_HATCH_BUILD_MODULE)
CustomBuildHook = _HATCH_BUILD_MODULE.CustomBuildHook


def test_stage_rtk_binary_extracts_tarball(tmp_path: Path, monkeypatch) -> None:
    archive_path = tmp_path / "rtk-linux.tar.gz"
    _write_tarball(
        archive_path, "release/rtk", b"#!/bin/sh\necho bundled\n", mode=0o755
    )
    monkeypatch.setattr(
        rtk_vendor,
        "RTK_BUNDLES",
        {
            "linux_x86_64": {
                "archive_name": archive_path.name,
                "binary_name": "rtk",
                "sha256": _sha256(archive_path),
                "url": archive_path.resolve().as_uri(),
            }
        },
    )

    staged = rtk_vendor.stage_rtk_binary("linux_x86_64", tmp_path / "vendor")

    assert staged == tmp_path / "vendor" / "linux_x86_64" / "rtk"
    assert staged.read_bytes() == b"#!/bin/sh\necho bundled\n"
    assert staged.stat().st_mode & stat.S_IXUSR


def test_stage_rtk_binary_extracts_windows_zip(tmp_path: Path, monkeypatch) -> None:
    archive_path = tmp_path / "rtk-win.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("bin/rtk.exe", b"MZ")
    monkeypatch.setattr(
        rtk_vendor,
        "RTK_BUNDLES",
        {
            "win_amd64": {
                "archive_name": archive_path.name,
                "binary_name": "rtk.exe",
                "sha256": _sha256(archive_path),
                "url": archive_path.resolve().as_uri(),
            }
        },
    )

    staged = rtk_vendor.stage_rtk_binary("win_amd64", tmp_path / "vendor")

    assert staged == tmp_path / "vendor" / "win_amd64" / "rtk.exe"
    assert staged.read_bytes() == b"MZ"


def test_stage_rtk_binary_rejects_path_traversal_archive(
    tmp_path: Path, monkeypatch
) -> None:
    archive_path = tmp_path / "rtk-linux.tar.gz"
    _write_tarball(archive_path, "../rtk", b"bad", mode=0o755)
    monkeypatch.setattr(
        rtk_vendor,
        "RTK_BUNDLES",
        {
            "linux_x86_64": {
                "archive_name": archive_path.name,
                "binary_name": "rtk",
                "sha256": _sha256(archive_path),
                "url": archive_path.resolve().as_uri(),
            }
        },
    )

    with pytest.raises(ValueError, match="outside"):
        rtk_vendor.stage_rtk_binary("linux_x86_64", tmp_path / "vendor")


def test_build_hook_marks_wheel_as_platform_specific_when_rtk_is_staged(
    tmp_path: Path,
) -> None:
    binary = tmp_path / "src" / "pbi_agent" / "_vendor" / "rtk" / "linux_x86_64" / "rtk"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_bytes(b"rtk")

    hook = object.__new__(CustomBuildHook)
    hook.root = str(tmp_path)
    hook.target_name = "wheel"
    build_data: dict[str, object] = {}

    hook.initialize("0.0.0", build_data)

    assert build_data == {"pure_python": False, "infer_tag": True}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_tarball(path: Path, member_name: str, content: bytes, mode: int) -> None:
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo(member_name)
        info.mode = mode
        info.size = len(content)
        archive.addfile(info, io.BytesIO(content))
