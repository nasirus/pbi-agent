"""Custom ``shell`` tool – executes shell commands in a subprocess.

This replaces the provider-specific native shell tools (OpenAI ``shell``,
Anthropic ``bash``) with a single, provider-agnostic function tool that goes
through the normal tool registry and execution pipeline.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from pbi_agent.tools.types import ToolContext, ToolSpec

MAX_TIMEOUT_MS = 120_000

SPEC = ToolSpec(
    name="shell",
    description=(
        "Execute a shell command and return its stdout, stderr, and exit code. "
        "Commands run inside the workspace directory by default. "
        "Use this for running builds, tests, git, file listing, or any CLI tool."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "working_directory": {
                "type": "string",
                "description": (
                    "Working directory for the command, relative to the "
                    "workspace root. Defaults to the workspace root."
                ),
            },
            "timeout_ms": {
                "type": "integer",
                "description": (
                    "Timeout in milliseconds (max 120 000). "
                    "Defaults to 120 000 (2 minutes)."
                ),
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    },
    is_destructive=True,
)


def handle(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    """Execute a single shell command and return structured output."""
    command = arguments.get("command", "")
    if not isinstance(command, str) or not command.strip():
        return {"error": "'command' must be a non-empty string."}

    root = Path.cwd().resolve()
    working_directory = _resolve_working_directory(
        root, arguments.get("working_directory")
    )
    timeout_ms = _normalize_timeout_ms(arguments.get("timeout_ms"))

    try:
        completed = subprocess.run(
            command,
            cwd=str(working_directory),
            env=dict(os.environ),
            capture_output=True,
            text=False,
            shell=True,
            timeout=(timeout_ms / 1000.0),
        )
        stdout = _decode_output(completed.stdout)
        stderr = _decode_output(completed.stderr)
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": completed.returncode,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "stdout": _decode_output(exc.stdout),
            "stderr": _decode_output(exc.stderr),
            "exit_code": None,
            "timed_out": True,
            "error": f"Command timed out after {timeout_ms}ms.",
        }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": str(exc),
            "exit_code": 1,
            "error": f"Shell execution failed: {exc}",
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_working_directory(root: Path, raw: Any) -> Path:
    if raw is None:
        return root
    if not isinstance(raw, str) or not raw.strip():
        return root

    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (root / candidate).resolve()

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"working_directory outside workspace is not allowed: {raw}"
        ) from exc

    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(f"working_directory does not exist: {resolved}")
    return resolved


def _normalize_timeout_ms(raw_timeout: Any) -> int:
    if raw_timeout is None:
        return MAX_TIMEOUT_MS
    if not isinstance(raw_timeout, int):
        return MAX_TIMEOUT_MS
    if raw_timeout < 1:
        return MAX_TIMEOUT_MS
    return min(raw_timeout, MAX_TIMEOUT_MS)


def _decode_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")
