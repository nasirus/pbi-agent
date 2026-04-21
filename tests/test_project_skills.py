from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from pathlib import Path

import pytest
from rich.console import Console

from pbi_agent.skills.project_catalog import (
    discover_installed_project_skills,
    render_installed_project_skills,
)
from pbi_agent.skills.project_installer import (
    ProjectSkillInstallError,
    install_project_skill,
    list_remote_project_skills,
    parse_github_skill_source,
    render_remote_skill_listing,
)


def _write_skill(
    root: Path,
    name: str,
    description: str,
    *,
    directory_name: str | None = None,
) -> Path:
    skill_dir = root / (directory_name or name)
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    return skill_dir


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def _make_zip_archive(members: dict[str, str | bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in members.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def _install_fake_github(
    monkeypatch: pytest.MonkeyPatch,
    *,
    owner: str = "owner",
    repo: str = "repo",
    ref: str = "main",
    archive_bytes: bytes,
    include_default_branch_lookup: bool = True,
    extra_responses: dict[str, bytes] | None = None,
    http_errors: dict[str, int] | None = None,
) -> list[str]:
    seen_urls: list[str] = []
    responses: dict[str, bytes] = {
        f"https://api.github.com/repos/{owner}/{repo}/zipball/{urllib.parse.quote(ref, safe='')}": archive_bytes,
    }
    if include_default_branch_lookup:
        responses[f"https://api.github.com/repos/{owner}/{repo}"] = json.dumps(
            {"default_branch": ref}
        ).encode("utf-8")
    if extra_responses:
        responses.update(extra_responses)

    def fake_urlopen(
        request: urllib.request.Request, timeout: float = 0.0
    ) -> _FakeResponse:
        seen_urls.append(request.full_url)
        if http_errors and request.full_url in http_errors:
            raise urllib.error.HTTPError(
                request.full_url,
                http_errors[request.full_url],
                "mocked error",
                hdrs=None,
                fp=None,
            )
        try:
            return _FakeResponse(responses[request.full_url])
        except KeyError as exc:  # pragma: no cover - test failure path
            raise urllib.error.HTTPError(
                request.full_url,
                404,
                "mocked error",
                hdrs=None,
                fp=None,
            ) from exc

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return seen_urls


def test_render_installed_project_skills_lists_table(tmp_path: Path) -> None:
    _write_skill(
        tmp_path / ".agents" / "skills",
        "repo-skill",
        "Repository workflow.",
    )
    output = io.StringIO()

    rc = render_installed_project_skills(
        workspace=tmp_path,
        console=Console(file=output, force_terminal=False, color_system=None),
    )

    assert rc == 0
    rendered = output.getvalue()
    assert "Project Skills" in rendered
    assert "repo-skill" in rendered
    assert "Repository workflow." in rendered


def test_render_installed_project_skills_shows_empty_state(tmp_path: Path) -> None:
    output = io.StringIO()

    rc = render_installed_project_skills(
        workspace=tmp_path,
        console=Console(file=output, force_terminal=False, color_system=None),
    )

    assert rc == 0
    assert "No project skills discovered under" in output.getvalue()


def test_discover_installed_project_skills_is_workspace_scoped(tmp_path: Path) -> None:
    workspace_one = tmp_path / "one"
    workspace_two = tmp_path / "two"
    _write_skill(
        workspace_one / ".agents" / "skills",
        "one-skill",
        "First workspace skill.",
    )
    _write_skill(
        workspace_two / ".agents" / "skills",
        "two-skill",
        "Second workspace skill.",
    )

    discovered = discover_installed_project_skills(workspace=workspace_one)

    assert [skill.name for skill in discovered] == ["one-skill"]


def test_parse_github_skill_source_accepts_shorthand_repo_and_tree_urls() -> None:
    shorthand = parse_github_skill_source("owner/repo")
    repo_url = parse_github_skill_source("https://github.com/owner/repo")

    assert shorthand.owner_repo == "owner/repo"
    assert shorthand.ref is None
    assert repo_url.owner_repo == "owner/repo"
    assert repo_url.ref is None


def test_parse_github_skill_source_parses_tree_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = _make_zip_archive({})
    _install_fake_github(
        monkeypatch,
        archive_bytes=archive_bytes,
        include_default_branch_lookup=False,
        extra_responses={
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/main": json.dumps(
                [{"ref": "refs/heads/main"}]
            ).encode("utf-8"),
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/main": json.dumps(
                []
            ).encode("utf-8"),
        },
        http_errors={
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/main/skills/remote-skill": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/main/skills/remote-skill": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/main/skills": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/main/skills": 404,
        },
    )
    tree_url = parse_github_skill_source(
        "https://github.com/owner/repo/tree/main/skills/remote-skill"
    )

    assert tree_url.owner_repo == "owner/repo"
    assert tree_url.ref == "main"
    assert tree_url.subpath == "skills/remote-skill"


def test_parse_github_skill_source_keeps_slashful_tree_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = _make_zip_archive({})
    _install_fake_github(
        monkeypatch,
        archive_bytes=archive_bytes,
        include_default_branch_lookup=False,
        extra_responses={
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/feature%2Ffoo": json.dumps(
                [{"ref": "refs/heads/feature/foo"}]
            ).encode("utf-8"),
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/feature%2Ffoo": json.dumps(
                []
            ).encode("utf-8"),
        },
        http_errors={
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/feature%2Ffoo%2Fskills%2Fbar": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/feature%2Ffoo%2Fskills%2Fbar": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/feature%2Ffoo%2Fskills": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/feature%2Ffoo%2Fskills": 404,
        },
    )

    parsed = parse_github_skill_source(
        "https://github.com/owner/repo/tree/feature/foo/skills/bar"
    )

    assert parsed.ref == "feature/foo"
    assert parsed.subpath == "skills/bar"


def test_parse_github_skill_source_rejects_unsafe_tree_subpaths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = _make_zip_archive({})
    _install_fake_github(
        monkeypatch,
        archive_bytes=archive_bytes,
        include_default_branch_lookup=False,
        extra_responses={
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/main": json.dumps(
                [{"ref": "refs/heads/main"}]
            ).encode("utf-8"),
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/main": json.dumps(
                []
            ).encode("utf-8"),
        },
        http_errors={
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/main%2Fskills%2F..%2F..%2Fetc": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/main%2Fskills%2F..%2F..%2Fetc": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/main%2Fskills%2F..%2F..": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/main%2Fskills%2F..%2F..": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/main%2Fskills%2F..": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/main%2Fskills%2F..": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/main%2Fskills": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/main%2Fskills": 404,
        },
    )

    with pytest.raises(ProjectSkillInstallError, match="Unsafe subpath"):
        parse_github_skill_source(
            "https://github.com/owner/repo/tree/main/skills/../../etc"
        )


def test_install_project_skill_installs_single_skill_repo_and_preserves_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = _make_zip_archive(
        {
            "repo-main/SKILL.md": (
                "---\nname: repo-skill\ndescription: Remote workflow skill.\n---\n\n# Repo\n"
            ),
            "repo-main/scripts/setup.sh": "echo setup\n",
            "repo-main/references/guide.md": "# Guide\n",
            "repo-main/assets/icon.txt": "asset\n",
        }
    )
    seen_urls = _install_fake_github(monkeypatch, archive_bytes=archive_bytes)

    result = install_project_skill("owner/repo", workspace=tmp_path)

    install_dir = tmp_path / ".agents" / "skills" / "repo-skill"
    assert result.name == "repo-skill"
    assert result.install_path == install_dir
    assert (install_dir / "SKILL.md").is_file()
    assert (install_dir / "scripts" / "setup.sh").read_text(
        encoding="utf-8"
    ) == "echo setup\n"
    assert (install_dir / "references" / "guide.md").is_file()
    assert (install_dir / "assets" / "icon.txt").is_file()

    assert not (install_dir / ".pbi-agent-skill-source.json").exists()
    assert seen_urls == [
        "https://api.github.com/repos/owner/repo",
        "https://api.github.com/repos/owner/repo/zipball/main",
    ]


def test_install_project_skill_supports_tree_url_with_slashful_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = _make_zip_archive(
        {
            "repo-main/skills/bar/SKILL.md": (
                "---\nname: bar\ndescription: Branch skill.\n---\n\n# Bar\n"
            ),
        }
    )
    seen_urls = _install_fake_github(
        monkeypatch,
        ref="feature/foo",
        archive_bytes=archive_bytes,
        include_default_branch_lookup=False,
        extra_responses={
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/feature%2Ffoo": json.dumps(
                [{"ref": "refs/heads/feature/foo"}]
            ).encode("utf-8"),
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/feature%2Ffoo": json.dumps(
                []
            ).encode("utf-8"),
        },
        http_errors={
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/feature%2Ffoo%2Fskills%2Fbar": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/feature%2Ffoo%2Fskills%2Fbar": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/heads/feature%2Ffoo%2Fskills": 404,
            "https://api.github.com/repos/owner/repo/git/matching-refs/tags/feature%2Ffoo%2Fskills": 404,
        },
    )

    result = install_project_skill(
        "https://github.com/owner/repo/tree/feature/foo/skills/bar",
        workspace=tmp_path,
    )

    assert result.name == "bar"
    assert result.ref == "feature/foo"
    assert result.subpath == "skills/bar"
    assert (tmp_path / ".agents" / "skills" / "bar" / "SKILL.md").is_file()
    assert "https://api.github.com/repos/owner/repo/zipball/feature%2Ffoo" in seen_urls


def test_list_remote_project_skills_returns_candidates_without_installing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = _make_zip_archive(
        {
            "repo-main/skills/alpha/SKILL.md": (
                "---\nname: alpha\ndescription: Alpha skill.\n---\n\n# Alpha\n"
            ),
            "repo-main/skills/beta/SKILL.md": (
                "---\nname: beta\ndescription: Beta skill.\n---\n\n# Beta\n"
            ),
        }
    )
    _install_fake_github(monkeypatch, archive_bytes=archive_bytes)

    listing = list_remote_project_skills("https://github.com/owner/repo")
    output = io.StringIO()
    render_remote_skill_listing(
        listing,
        console=Console(file=output, force_terminal=False, color_system=None),
    )

    assert listing.owner_repo == "owner/repo"
    assert listing.ref == "main"
    assert [candidate.name for candidate in listing.candidates] == ["alpha", "beta"]
    assert "Available Skills" in output.getvalue()
    assert "alpha" in output.getvalue()
    assert not (tmp_path / ".agents" / "skills").exists()


def test_list_remote_project_skills_skips_malformed_siblings(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    archive_bytes = _make_zip_archive(
        {
            "repo-main/skills/alpha/SKILL.md": (
                "---\nname: alpha\ndescription: Alpha skill.\n---\n\n# Alpha\n"
            ),
            "repo-main/skills/broken/SKILL.md": "---\nname: broken\n---\n\n# Broken\n",
        }
    )
    _install_fake_github(monkeypatch, archive_bytes=archive_bytes)

    listing = list_remote_project_skills("https://github.com/owner/repo")

    assert [candidate.name for candidate in listing.candidates] == ["alpha"]
    assert "Skipping remote skill" in capsys.readouterr().err


def test_install_project_skill_requires_skill_for_multi_skill_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = _make_zip_archive(
        {
            "repo-main/skills/alpha/SKILL.md": (
                "---\nname: alpha\ndescription: Alpha skill.\n---\n\n# Alpha\n"
            ),
            "repo-main/skills/beta/SKILL.md": (
                "---\nname: beta\ndescription: Beta skill.\n---\n\n# Beta\n"
            ),
        }
    )
    _install_fake_github(monkeypatch, archive_bytes=archive_bytes)

    with pytest.raises(ProjectSkillInstallError, match="Multiple skills were found"):
        install_project_skill("owner/repo", workspace=tmp_path)


def test_install_project_skill_rejects_unknown_skill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = _make_zip_archive(
        {
            "repo-main/skills/alpha/SKILL.md": (
                "---\nname: alpha\ndescription: Alpha skill.\n---\n\n# Alpha\n"
            ),
            "repo-main/skills/beta/SKILL.md": (
                "---\nname: beta\ndescription: Beta skill.\n---\n\n# Beta\n"
            ),
        }
    )
    _install_fake_github(monkeypatch, archive_bytes=archive_bytes)

    with pytest.raises(ProjectSkillInstallError, match="Unknown skill 'gamma'"):
        install_project_skill("owner/repo", skill_name="gamma", workspace=tmp_path)


def test_install_project_skill_blocks_overwrite_without_force_and_allows_force(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_dir = tmp_path / ".agents" / "skills" / "repo-skill"
    install_dir.mkdir(parents=True)
    (install_dir / "old.txt").write_text("old\n", encoding="utf-8")

    archive_bytes = _make_zip_archive(
        {
            "repo-main/SKILL.md": (
                "---\nname: repo-skill\ndescription: Updated skill.\n---\n\n# Repo\n"
            ),
            "repo-main/new.txt": "new\n",
        }
    )
    _install_fake_github(monkeypatch, archive_bytes=archive_bytes)

    with pytest.raises(ProjectSkillInstallError, match="already installed"):
        install_project_skill("owner/repo", workspace=tmp_path)

    result = install_project_skill("owner/repo", workspace=tmp_path, force=True)

    assert result.install_path == install_dir
    assert not (install_dir / "old.txt").exists()
    assert (install_dir / "new.txt").read_text(encoding="utf-8") == "new\n"


def test_install_project_skill_rejects_malicious_zip_members(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_bytes = _make_zip_archive(
        {
            "repo-main/SKILL.md": (
                "---\nname: repo-skill\ndescription: Safe.\n---\n\n# Repo\n"
            ),
            "repo-main/../../escape.txt": "boom\n",
        }
    )
    _install_fake_github(monkeypatch, archive_bytes=archive_bytes)

    with pytest.raises(ProjectSkillInstallError, match="unsafe member path"):
        install_project_skill("owner/repo", workspace=tmp_path)


def test_install_project_skill_rejects_missing_name_or_description(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    archive_bytes = _make_zip_archive(
        {
            "repo-main/SKILL.md": "---\nname: \n---\n\n# Broken\n",
        }
    )
    _install_fake_github(monkeypatch, archive_bytes=archive_bytes)

    with pytest.raises(
        ProjectSkillInstallError,
        match="No valid skills found. Skills require a SKILL.md with name and description.",
    ):
        install_project_skill("owner/repo", workspace=tmp_path)
    assert "missing non-empty 'name'" in capsys.readouterr().err


def test_install_project_skill_rejects_unsupported_manifest_structure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    archive_bytes = _make_zip_archive(
        {
            "repo-main/SKILL.md": "---\nname\n---\n\n# Broken\n",
        }
    )
    _install_fake_github(monkeypatch, archive_bytes=archive_bytes)

    with pytest.raises(
        ProjectSkillInstallError,
        match="No valid skills found. Skills require a SKILL.md with name and description.",
    ):
        install_project_skill("owner/repo", workspace=tmp_path)
    assert "not a key-value pair" in capsys.readouterr().err
