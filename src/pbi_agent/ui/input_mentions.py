"""Workspace-safe `@file` mention parsing and expansion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pbi_agent.tools.workspace_access import (
    read_text_file,
    relative_workspace_path,
    resolve_safe_path,
)

PATH_CHAR_CLASS = r"A-Za-z0-9._~/\\:-"
FILE_MENTION_PATTERN = re.compile(r"@(?P<path>(?:\\.|[" + PATH_CHAR_CLASS + r"])+)")
EMAIL_PREFIX_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]$")
IMAGE_FILE_SUFFIXES = frozenset({".jpeg", ".jpg", ".png", ".webp"})

_MAX_INLINE_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class _MentionMatch:
    path: Path
    start: int
    end: int


def expand_file_mentions(
    text: str,
    *,
    root: Path,
    max_inline_bytes: int = _MAX_INLINE_BYTES,
) -> tuple[str, list[str]]:
    """Return input text with referenced workspace files appended inline."""

    expanded, _image_paths, warnings = expand_input_mentions(
        text,
        root=root,
        max_inline_bytes=max_inline_bytes,
    )
    return expanded, warnings


def expand_input_mentions(
    text: str,
    *,
    root: Path,
    max_inline_bytes: int = _MAX_INLINE_BYTES,
) -> tuple[str, list[str], list[str]]:
    """Return expanded text plus image mention paths and warnings."""

    warnings: list[str] = []
    mentioned_files = _collect_mentioned_files(text, root=root, warnings=warnings)
    if not mentioned_files:
        return text, [], warnings

    parts = [_strip_mention_text(text, mentioned_files)]
    inline_parts: list[str] = []
    image_paths: list[str] = []
    for match in mentioned_files:
        relative_path = relative_workspace_path(root, match.path)
        if match.path.suffix.lower() in IMAGE_FILE_SUFFIXES:
            image_paths.append(relative_path)
            continue

        try:
            size = match.path.stat().st_size
        except OSError as exc:
            inline_parts.append(f"### {relative_path}\n[Could not inspect file: {exc}]")
            continue

        if size > max_inline_bytes:
            inline_parts.append(
                "### "
                + relative_path
                + "\n"
                + f"[File too large to inline ({size} bytes). Use read_file if needed.]"
            )
            continue

        try:
            content, encoding = read_text_file(match.path)
        except ValueError as exc:
            inline_parts.append(f"### {relative_path}\n[Could not read file: {exc}]")
            continue

        inline_parts.append(
            f"### {relative_path}\n[encoding: {encoding}]\n<file>\n{content}\n</file>"
        )

    if inline_parts:
        parts.extend(["", "## Referenced Files", *inline_parts])
    return "\n".join(parts), image_paths, warnings


def _collect_mentioned_files(
    text: str, *, root: Path, warnings: list[str]
) -> list[_MentionMatch]:
    root = root.resolve()
    seen: set[Path] = set()
    files: list[_MentionMatch] = []
    index = 0
    while index < len(text):
        at_index = text.find("@", index)
        if at_index < 0:
            break
        if at_index > 0 and EMAIL_PREFIX_PATTERN.search(text[at_index - 1]):
            index = at_index + 1
            continue

        line_end = text.find("\n", at_index + 1)
        if line_end < 0:
            line_end = len(text)
        raw_segment = text[at_index + 1 : line_end]

        resolved, clean_path, consumed = _resolve_mentioned_file(raw_segment, root=root)
        if resolved is None:
            missing_path = _missing_mention_path(raw_segment)
            if missing_path:
                try:
                    resolve_safe_path(root, missing_path)
                except ValueError as exc:
                    warnings.append(str(exc))
                else:
                    warnings.append(f"Referenced file not found: {missing_path}")
            index = at_index + 1
            continue

        if resolved not in seen:
            seen.add(resolved)
            files.append(_MentionMatch(resolved, at_index, at_index + 1 + consumed))
        index = at_index + 1 + consumed

    return files


def _strip_mention_text(text: str, mentions: list[_MentionMatch]) -> str:
    parts: list[str] = []
    cursor = 0
    for match in mentions:
        parts.append(text[cursor : match.start])
        cursor = match.end
    parts.append(text[cursor:])
    cleaned = "".join(parts)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"[ \t]+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]*\n[ \t]*", "\n", cleaned)
    return cleaned.strip()


def _resolve_mentioned_file(
    raw_segment: str, *, root: Path
) -> tuple[Path | None, str, int]:
    if not raw_segment or raw_segment[0].isspace():
        return None, "", 0

    for end in range(len(raw_segment), 0, -1):
        candidate = raw_segment[:end].rstrip()
        if not candidate or candidate[0].isspace():
            continue
        clean_path = candidate.replace("\\ ", " ")
        try:
            resolved = resolve_safe_path(root, clean_path)
        except ValueError:
            continue
        if resolved.exists() and resolved.is_file():
            return resolved, clean_path, len(candidate)

    return None, "", 0


def _missing_mention_path(raw_segment: str) -> str:
    if not raw_segment or raw_segment[0].isspace():
        return ""

    chars: list[str] = []
    index = 0
    while index < len(raw_segment):
        char = raw_segment[index]
        if char == "\\" and index + 1 < len(raw_segment):
            chars.extend([char, raw_segment[index + 1]])
            index += 2
            continue
        if char in " \t\r\n":
            break
        if not re.match(r"[" + PATH_CHAR_CLASS + r"]", char):
            break
        chars.append(char)
        index += 1

    return "".join(chars).replace("\\ ", " ")


__all__ = [
    "EMAIL_PREFIX_PATTERN",
    "FILE_MENTION_PATTERN",
    "IMAGE_FILE_SUFFIXES",
    "expand_input_mentions",
    "expand_file_mentions",
]
