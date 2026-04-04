from __future__ import annotations

import argparse
import hashlib
import shutil
import stat
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable

RTK_RELEASE_TAG = "v0.34.3"

RTK_BUNDLES = {
    "linux_x86_64": {
        "archive_name": "rtk-x86_64-unknown-linux-musl.tar.gz",
        "binary_name": "rtk",
        "sha256": "a607c17bfdccc1d48dc94ca81cd3a545523329df6a378368fd175d8023425ea5",
        "url": f"https://github.com/rtk-ai/rtk/releases/download/{RTK_RELEASE_TAG}/"
        "rtk-x86_64-unknown-linux-musl.tar.gz",
    },
    "linux_aarch64": {
        "archive_name": "rtk-aarch64-unknown-linux-gnu.tar.gz",
        "binary_name": "rtk",
        "sha256": "0a3afae8435a352c32eaacb8ecd76953146928191fefc8b2de703f3adf10c9f8",
        "url": f"https://github.com/rtk-ai/rtk/releases/download/{RTK_RELEASE_TAG}/"
        "rtk-aarch64-unknown-linux-gnu.tar.gz",
    },
    "macos_x86_64": {
        "archive_name": "rtk-x86_64-apple-darwin.tar.gz",
        "binary_name": "rtk",
        "sha256": "35928229a7fe064016b7cd567e9333278c661221e2a19180d4f1943516a8c1f1",
        "url": f"https://github.com/rtk-ai/rtk/releases/download/{RTK_RELEASE_TAG}/"
        "rtk-x86_64-apple-darwin.tar.gz",
    },
    "macos_arm64": {
        "archive_name": "rtk-aarch64-apple-darwin.tar.gz",
        "binary_name": "rtk",
        "sha256": "945f644a77e5da3367142a999c41a4fa448d0a4ae3e61c8a45094b8522dba047",
        "url": f"https://github.com/rtk-ai/rtk/releases/download/{RTK_RELEASE_TAG}/"
        "rtk-aarch64-apple-darwin.tar.gz",
    },
    "win_amd64": {
        "archive_name": "rtk-x86_64-pc-windows-msvc.zip",
        "binary_name": "rtk.exe",
        "sha256": "27fc7be1f90af050bc533dd77ff53bfe39a972206621ff217d27bcd671a6aac6",
        "url": f"https://github.com/rtk-ai/rtk/releases/download/{RTK_RELEASE_TAG}/"
        "rtk-x86_64-pc-windows-msvc.zip",
    },
}

DEFAULT_VENDOR_ROOT = Path("src") / "pbi_agent" / "_vendor" / "rtk"


def stage_rtk_binaries(
    vendor_root: Path = DEFAULT_VENDOR_ROOT,
    bundles: Iterable[str] | None = None,
) -> list[Path]:
    selected_bundles = list(bundles or RTK_BUNDLES)
    return [stage_rtk_binary(bundle, vendor_root) for bundle in selected_bundles]


def stage_rtk_binary(bundle: str, vendor_root: Path = DEFAULT_VENDOR_ROOT) -> Path:
    try:
        spec = RTK_BUNDLES[bundle]
    except KeyError as exc:
        supported = ", ".join(sorted(RTK_BUNDLES))
        raise ValueError(
            f"Unknown RTK bundle {bundle!r}. Expected one of: {supported}."
        ) from exc

    vendor_root = Path(vendor_root)
    vendor_path = vendor_root / bundle / spec["binary_name"]
    vendor_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = temp_path / spec["archive_name"]
        _download_file(spec["url"], archive_path)
        _verify_sha256(archive_path, spec["sha256"])
        extracted_binary = _extract_binary(
            archive_path,
            destination_dir=temp_path / "extracted",
            binary_name=spec["binary_name"],
        )
        shutil.copy2(extracted_binary, vendor_path)

    _ensure_executable(vendor_path)
    return vendor_path


def _download_file(url: str, destination: Path) -> None:
    try:
        with (
            urllib.request.urlopen(url, timeout=60) as response,
            destination.open("wb") as output,
        ):
            shutil.copyfileobj(response, output)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to download bundled RTK asset from {url}.") from exc


def _verify_sha256(path: Path, expected_sha256: str) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError(
            f"Checksum mismatch for {path.name}: expected {expected_sha256}, got {digest}."
        )


def _extract_binary(
    archive_path: Path, destination_dir: Path, binary_name: str
) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    if archive_path.suffix == ".zip":
        _extract_zip(archive_path, destination_dir)
    elif archive_path.name.endswith(".tar.gz"):
        _extract_tar(archive_path, destination_dir)
    else:
        raise ValueError(f"Unsupported RTK archive format: {archive_path.name}")

    candidates = sorted(
        path for path in destination_dir.rglob(binary_name) if path.is_file()
    )
    if not candidates:
        raise FileNotFoundError(f"Could not find {binary_name} in {archive_path.name}.")
    return candidates[0]


def _extract_tar(archive_path: Path, destination_dir: Path) -> None:
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            extracted_path = destination_dir / member.name
            _ensure_within_directory(destination_dir, extracted_path)

            if member.isdir():
                extracted_path.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue

            extracted_path.parent.mkdir(parents=True, exist_ok=True)
            file_object = archive.extractfile(member)
            if file_object is None:
                continue
            with extracted_path.open("wb") as output:
                shutil.copyfileobj(file_object, output)
            extracted_path.chmod(member.mode)


def _extract_zip(archive_path: Path, destination_dir: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            extracted_path = destination_dir / member.filename
            _ensure_within_directory(destination_dir, extracted_path)

            if member.is_dir():
                extracted_path.mkdir(parents=True, exist_ok=True)
                continue

            extracted_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, extracted_path.open("wb") as output:
                shutil.copyfileobj(source, output)


def _ensure_within_directory(root: Path, candidate: Path) -> None:
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve(strict=False)
    if (
        candidate_resolved != root_resolved
        and root_resolved not in candidate_resolved.parents
    ):
        raise ValueError(
            f"Refusing to extract archive member outside {root}: {candidate}"
        )


def _ensure_executable(path: Path) -> None:
    if path.suffix.lower() == ".exe":
        return

    current_mode = path.stat().st_mode
    path.chmod(current_mode | stat.S_IXUSR)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download, verify, and stage bundled RTK binaries."
    )
    parser.add_argument(
        "--vendor-root",
        default=DEFAULT_VENDOR_ROOT,
        type=Path,
        help="Directory where RTK bundle subdirectories should be written.",
    )
    parser.add_argument(
        "--bundle",
        action="append",
        choices=sorted(RTK_BUNDLES),
        dest="bundles",
        help="Specific bundle to stage. Repeat to stage more than one bundle.",
    )
    args = parser.parse_args(argv)

    for path in stage_rtk_binaries(args.vendor_root, args.bundles):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
