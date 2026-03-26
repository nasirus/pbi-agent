from __future__ import annotations

from pathlib import Path

from pbi_agent.ui.input_mentions import expand_file_mentions, expand_input_mentions


def test_expand_file_mentions_appends_workspace_file_content(tmp_path: Path) -> None:
    target = tmp_path / "report.md"
    target.write_text("hello report\n", encoding="utf-8")

    expanded, warnings = expand_file_mentions(
        "Summarize @report.md",
        root=tmp_path,
    )

    assert warnings == []
    assert "Summarize @report.md" not in expanded
    assert expanded.startswith("Summarize")
    assert "## Referenced Files" in expanded
    assert "hello report" in expanded


def test_expand_file_mentions_warns_for_missing_file(tmp_path: Path) -> None:
    expanded, warnings = expand_file_mentions(
        "Summarize @missing.md",
        root=tmp_path,
    )

    assert expanded == "Summarize @missing.md"
    assert warnings == ["Referenced file not found: missing.md"]


def test_expand_file_mentions_rejects_outside_workspace(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    try:
        expanded, warnings = expand_file_mentions(
            f"Check @{outside}",
            root=tmp_path,
        )
    finally:
        outside.unlink(missing_ok=True)

    assert expanded == f"Check @{outside}"
    assert warnings
    assert "path outside workspace is not allowed" in warnings[0]


def test_expand_file_mentions_skips_email_addresses(tmp_path: Path) -> None:
    expanded, warnings = expand_file_mentions(
        "contact me at user@example.com",
        root=tmp_path,
    )

    assert expanded == "contact me at user@example.com"
    assert warnings == []


def test_expand_input_mentions_extracts_image_paths(tmp_path: Path) -> None:
    target = tmp_path / "mockup.png"
    target.write_bytes(b"not-used-by-parser")

    expanded, image_paths, warnings = expand_input_mentions(
        "Review @mockup.png carefully",
        root=tmp_path,
    )

    assert expanded == "Review carefully"
    assert image_paths == ["mockup.png"]
    assert warnings == []


def test_expand_file_mentions_supports_escaped_spaces(tmp_path: Path) -> None:
    target = tmp_path / "my notes.txt"
    target.write_text("hello notes\n", encoding="utf-8")

    expanded, warnings = expand_file_mentions(
        r"Summarize @my\ notes.txt",
        root=tmp_path,
    )

    assert warnings == []
    assert "Summarize @my\\ notes.txt" not in expanded
    assert expanded.startswith("Summarize")
    assert "hello notes" in expanded


def test_expand_file_mentions_supports_literal_spaces(tmp_path: Path) -> None:
    target = tmp_path / "my notes.txt"
    target.write_text("hello notes\n", encoding="utf-8")

    expanded, warnings = expand_file_mentions(
        "Summarize @my notes.txt please",
        root=tmp_path,
    )

    assert warnings == []
    assert "Summarize @my notes.txt please" not in expanded
    assert expanded.startswith("Summarize please")
    assert "hello notes" in expanded
