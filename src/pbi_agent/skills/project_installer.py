from __future__ import annotations

import io
import json
import re
import shutil
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from rich.console import Console
from rich.table import Table

from pbi_agent.skills.project_catalog import (
    SkillManifestError,
    load_project_skill_manifest,
)

_GITHUB_API_ROOT = "https://api.github.com"
_INSTALL_ROOT = Path(".agents/skills")


class ProjectSkillInstallError(ValueError):
    """Raised when remote project skill installation fails."""


@dataclass(slots=True, frozen=True)
class GitHubSkillSource:
    source: str
    owner: str
    repo: str
    owner_repo: str
    ref: str | None = None
    subpath: str | None = None


@dataclass(slots=True, frozen=True)
class RemoteSkillCandidateSummary:
    name: str
    description: str
    subpath: str | None


@dataclass(slots=True, frozen=True)
class RemoteSkillListing:
    source: str
    owner_repo: str
    ref: str
    candidates: list[RemoteSkillCandidateSummary]


@dataclass(slots=True, frozen=True)
class ProjectSkillInstallResult:
    name: str
    install_path: Path
    owner_repo: str
    ref: str
    subpath: str | None


@dataclass(slots=True, frozen=True)
class _RemoteSkillCandidate:
    name: str
    description: str
    skill_dir: Path
    repo_subpath: str | None


def render_remote_skill_listing(
    listing: RemoteSkillListing,
    *,
    console: Console | None = None,
) -> int:
    active_console = console or Console()
    table = Table(title="Available Skills", title_style="bold cyan")
    table.add_column("Name", style="green")
    table.add_column("Description")
    table.add_column("Source Path", style="dim")
    for candidate in listing.candidates:
        table.add_row(candidate.name, candidate.description, candidate.subpath or ".")
    active_console.print(table)
    return 0


def list_remote_project_skills(source: str) -> RemoteSkillListing:
    parsed_source = parse_github_skill_source(source)
    resolved_ref = resolve_github_source_ref(parsed_source)

    with TemporaryDirectory(prefix="pbi-agent-skill-") as temp_dir:
        repo_root = _download_and_extract_github_archive(
            parsed_source,
            ref=resolved_ref,
            destination=Path(temp_dir),
        )
        resolved_root = _resolve_repo_selection_root(repo_root, parsed_source.subpath)
        candidates = _discover_remote_skill_candidates(
            repo_root=repo_root,
            resolved_root=resolved_root,
        )

    if not candidates:
        raise ProjectSkillInstallError(
            "No valid skills found. Skills require a SKILL.md with name and description."
        )

    return RemoteSkillListing(
        source=parsed_source.source,
        owner_repo=parsed_source.owner_repo,
        ref=resolved_ref,
        candidates=[
            RemoteSkillCandidateSummary(
                name=candidate.name,
                description=candidate.description,
                subpath=candidate.repo_subpath,
            )
            for candidate in candidates
        ],
    )


def install_project_skill(
    source: str,
    *,
    skill_name: str | None = None,
    force: bool = False,
    workspace: Path | None = None,
) -> ProjectSkillInstallResult:
    parsed_source = parse_github_skill_source(source)
    resolved_ref = resolve_github_source_ref(parsed_source)
    install_workspace = (workspace or Path.cwd()).resolve()
    install_root = (install_workspace / _INSTALL_ROOT).resolve()

    with TemporaryDirectory(prefix="pbi-agent-skill-") as temp_dir:
        repo_root = _download_and_extract_github_archive(
            parsed_source,
            ref=resolved_ref,
            destination=Path(temp_dir),
        )
        resolved_root = _resolve_repo_selection_root(repo_root, parsed_source.subpath)
        candidates = _discover_remote_skill_candidates(
            repo_root=repo_root,
            resolved_root=resolved_root,
        )
        selected = _select_remote_skill_candidate(candidates, skill_name=skill_name)
        target_dir = _resolve_install_target(
            install_root=install_root, skill_name=selected.name
        )

        _prepare_install_target(target_dir, force=force)
        shutil.copytree(selected.skill_dir, target_dir)

    return ProjectSkillInstallResult(
        name=selected.name,
        install_path=target_dir,
        owner_repo=parsed_source.owner_repo,
        ref=resolved_ref,
        subpath=selected.repo_subpath,
    )


def parse_github_skill_source(source: str) -> GitHubSkillSource:
    normalized = source.strip()
    if not normalized:
        raise ProjectSkillInstallError("Skill source must not be empty.")

    shorthand_match = re_fullmatch_owner_repo(normalized.rstrip("/"))
    if shorthand_match is not None:
        owner, repo = shorthand_match
        return GitHubSkillSource(
            source=normalized,
            owner=owner,
            repo=repo,
            owner_repo=f"{owner}/{repo}",
        )

    try:
        parsed_url = urllib.parse.urlparse(normalized)
    except ValueError as exc:
        raise ProjectSkillInstallError(f"Unsupported skill source: {source}") from exc

    if parsed_url.scheme not in {"http", "https"} or parsed_url.netloc != "github.com":
        raise ProjectSkillInstallError(
            "Unsupported skill source. Use owner/repo, a GitHub repository URL, "
            "or a GitHub tree URL."
        )

    parts = [urllib.parse.unquote(part) for part in parsed_url.path.split("/") if part]
    if len(parts) < 2:
        raise ProjectSkillInstallError(
            "Unsupported GitHub URL. Expected https://github.com/<owner>/<repo>."
        )

    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    if not owner or not repo:
        raise ProjectSkillInstallError(
            "Unsupported GitHub URL. Expected https://github.com/<owner>/<repo>."
        )

    if len(parts) == 2:
        return GitHubSkillSource(
            source=normalized,
            owner=owner,
            repo=repo,
            owner_repo=f"{owner}/{repo}",
        )

    if len(parts) >= 4 and parts[2] == "tree":
        ref, subpath = _split_github_tree_ref_and_subpath(
            owner=owner,
            repo=repo,
            tree_parts=parts[3:],
        )
        return GitHubSkillSource(
            source=normalized,
            owner=owner,
            repo=repo,
            owner_repo=f"{owner}/{repo}",
            ref=ref,
            subpath=subpath,
        )

    raise ProjectSkillInstallError(
        "Unsupported GitHub URL. Use a repository URL or a tree URL."
    )


def sanitize_skill_subpath(subpath: str) -> str:
    normalized = subpath.replace("\\", "/")
    for segment in normalized.split("/"):
        if segment == "..":
            raise ProjectSkillInstallError(
                f'Unsafe subpath: "{subpath}" contains path traversal segments.'
            )
    return normalized.strip("/")


def _split_github_tree_ref_and_subpath(
    *,
    owner: str,
    repo: str,
    tree_parts: list[str],
) -> tuple[str, str | None]:
    if not tree_parts:
        raise ProjectSkillInstallError(
            "Unsupported GitHub tree URL. Expected a ref after /tree/."
        )

    for split_index in range(len(tree_parts), 0, -1):
        ref_candidate = "/".join(tree_parts[:split_index])
        if not _github_ref_exists(owner=owner, repo=repo, ref=ref_candidate):
            continue

        subpath = "/".join(tree_parts[split_index:]) or None
        if subpath is not None:
            subpath = sanitize_skill_subpath(subpath)
        return ref_candidate, subpath

    fallback_ref = tree_parts[0]
    subpath = "/".join(tree_parts[1:]) or None
    if subpath is not None:
        subpath = sanitize_skill_subpath(subpath)
    return fallback_ref, subpath


def _github_ref_exists(*, owner: str, repo: str, ref: str) -> bool:
    quoted_ref = urllib.parse.quote(ref, safe="")
    for namespace in ("heads", "tags"):
        url = (
            f"{_GITHUB_API_ROOT}/repos/{owner}/{repo}/git/matching-refs/"
            f"{namespace}/{quoted_ref}"
        )
        try:
            payload = _read_json_value(url)
        except ProjectSkillInstallError:
            continue
        if not isinstance(payload, list):
            continue
        expected_ref = f"refs/{namespace}/{ref}"
        if any(
            isinstance(entry, dict) and entry.get("ref") == expected_ref
            for entry in payload
        ):
            return True
    return False


def resolve_github_source_ref(source: GitHubSkillSource) -> str:
    if source.ref:
        return source.ref

    repo_url = f"{_GITHUB_API_ROOT}/repos/{source.owner}/{source.repo}"
    payload = _read_json(repo_url)
    default_branch = payload.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch.strip():
        raise ProjectSkillInstallError(
            f"Could not resolve the default branch for {source.owner_repo}."
        )
    return default_branch


def _download_and_extract_github_archive(
    source: GitHubSkillSource,
    *,
    ref: str,
    destination: Path,
) -> Path:
    archive_url = (
        f"{_GITHUB_API_ROOT}/repos/{source.owner}/{source.repo}/zipball/"
        f"{urllib.parse.quote(ref, safe='')}"
    )
    archive_bytes = _read_bytes(archive_url)
    extract_root = destination / "archive"
    extract_root.mkdir(parents=True, exist_ok=True)
    return _extract_archive_bytes(archive_bytes, destination=extract_root)


def _extract_archive_bytes(archive_bytes: bytes, *, destination: Path) -> Path:
    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except zipfile.BadZipFile as exc:
        raise ProjectSkillInstallError(
            "GitHub archive response was not a valid zip file."
        ) from exc

    with archive:
        top_level_dirs: set[str] = set()
        destination_root = destination.resolve()
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ProjectSkillInstallError(
                    f"Archive contains unsafe member path: {member.filename!r}."
                )
            if not member.filename:
                continue

            unix_mode = member.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                raise ProjectSkillInstallError(
                    f"Archive contains unsupported symbolic link member: {member.filename!r}."
                )

            top_level_dirs.add(member_path.parts[0])
            target_path = (destination_root / member_path).resolve()
            _ensure_path_within_root(destination_root, target_path)

            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with (
                archive.open(member, "r") as source_file,
                target_path.open("wb") as target_file,
            ):
                shutil.copyfileobj(source_file, target_file)

    if len(top_level_dirs) != 1:
        raise ProjectSkillInstallError(
            "GitHub archive did not contain a single repository root."
        )

    return (destination_root / next(iter(top_level_dirs))).resolve()


def _resolve_repo_selection_root(repo_root: Path, subpath: str | None) -> Path:
    if subpath is None:
        return repo_root.resolve()

    candidate = (repo_root / subpath).resolve()
    _ensure_path_within_root(repo_root.resolve(), candidate)
    if not candidate.exists():
        raise ProjectSkillInstallError(
            f"Remote path {subpath!r} was not found in the downloaded repository archive."
        )
    if not candidate.is_dir():
        raise ProjectSkillInstallError(f"Remote path {subpath!r} is not a directory.")
    return candidate


def _discover_remote_skill_candidates(
    *,
    repo_root: Path,
    resolved_root: Path,
) -> list[_RemoteSkillCandidate]:
    candidate_dirs: list[Path] = []
    seen_dirs: set[Path] = set()

    def enqueue(skill_dir: Path) -> None:
        resolved_dir = skill_dir.resolve()
        if resolved_dir in seen_dirs:
            return
        seen_dirs.add(resolved_dir)
        candidate_dirs.append(resolved_dir)

    if (resolved_root / "SKILL.md").is_file():
        enqueue(resolved_root)

    for container in (resolved_root / "skills", resolved_root / ".agents" / "skills"):
        if not container.is_dir():
            continue
        for child in sorted(container.iterdir(), key=lambda item: item.name.casefold()):
            if child.is_dir() and (child / "SKILL.md").is_file():
                enqueue(child)

    candidates: list[_RemoteSkillCandidate] = []
    for skill_dir in candidate_dirs:
        try:
            manifest = load_project_skill_manifest(skill_dir / "SKILL.md")
        except SkillManifestError as exc:
            _warn(
                f"Skipping remote skill at {skill_dir / 'SKILL.md'}: "
                f"unsupported manifest: {exc}"
            )
            continue

        repo_subpath = skill_dir.relative_to(repo_root).as_posix()
        candidates.append(
            _RemoteSkillCandidate(
                name=manifest.name,
                description=manifest.description,
                skill_dir=skill_dir,
                repo_subpath=None if repo_subpath == "." else repo_subpath,
            )
        )

    return candidates


def _warn(message: str) -> None:
    print(message, file=sys.stderr)


def _select_remote_skill_candidate(
    candidates: list[_RemoteSkillCandidate],
    *,
    skill_name: str | None,
) -> _RemoteSkillCandidate:
    if not candidates:
        raise ProjectSkillInstallError(
            "No valid skills found. Skills require a SKILL.md with name and description."
        )

    if skill_name is None:
        if len(candidates) != 1:
            raise ProjectSkillInstallError(
                "Multiple skills were found in the remote source. Re-run with --skill <name>."
            )
        return candidates[0]

    matched = [
        candidate
        for candidate in candidates
        if candidate.name.casefold() == skill_name.casefold()
    ]
    if not matched:
        available = ", ".join(candidate.name for candidate in candidates)
        raise ProjectSkillInstallError(
            f"Unknown skill {skill_name!r}. Available skills: {available}."
        )
    if len(matched) > 1:
        raise ProjectSkillInstallError(
            f"Skill name {skill_name!r} matched multiple remote skill bundles."
        )
    return matched[0]


def _resolve_install_target(*, install_root: Path, skill_name: str) -> Path:
    normalized_name = skill_name.strip()
    if not normalized_name:
        raise ProjectSkillInstallError("Skill manifest name must not be empty.")
    if (
        "/" in normalized_name
        or "\\" in normalized_name
        or normalized_name in {".", ".."}
    ):
        raise ProjectSkillInstallError(
            f"Unsupported skill name {skill_name!r}. Skill install names must be a single path segment."
        )

    install_root.mkdir(parents=True, exist_ok=True)
    target_dir = (install_root / normalized_name).resolve()
    _ensure_path_within_root(install_root.resolve(), target_dir)
    return target_dir


def _prepare_install_target(target_dir: Path, *, force: bool) -> None:
    if not target_dir.exists():
        return

    if not force:
        raise ProjectSkillInstallError(
            f"Skill already installed at {target_dir}. Re-run with --force to replace it."
        )

    if target_dir.is_symlink() or target_dir.is_file():
        target_dir.unlink()
        return
    shutil.rmtree(target_dir)


def _read_json_value(url: str) -> object:
    payload = _read_bytes(url)
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectSkillInstallError(
            f"Failed to parse JSON response from {url}."
        ) from exc


def _read_json(url: str) -> dict[str, object]:
    data = _read_json_value(url)
    if not isinstance(data, dict):
        raise ProjectSkillInstallError(f"Unexpected JSON response from {url}.")
    return data


def _read_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "pbi-agent-skills",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise ProjectSkillInstallError(
            f"GitHub request failed for {url}: HTTP {exc.code}."
        ) from exc
    except urllib.error.URLError as exc:
        raise ProjectSkillInstallError(
            f"GitHub request failed for {url}: {exc.reason}."
        ) from exc


def _ensure_path_within_root(root: Path, candidate: Path) -> None:
    if candidate != root and root not in candidate.parents:
        raise ProjectSkillInstallError(
            f"Path {candidate} escapes the allowed root {root}."
        )


def re_fullmatch_owner_repo(value: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"([^/]+)/([^/]+?)(?:\.git)?", value)
    if match is None:
        return None
    owner = match.group(1)
    repo = match.group(2)
    if not owner or not repo:
        return None
    return owner, repo
