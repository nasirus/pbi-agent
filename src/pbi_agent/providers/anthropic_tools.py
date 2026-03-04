"""Execution logic for Anthropic native tools: bash and text editor.

These functions execute tool calls received from the Anthropic Messages API
and return string results suitable for ``tool_result`` content blocks.
"""

from __future__ import annotations

import logging
import os
import queue
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

BASH_TIMEOUT_SECONDS = 120
_BASH_SENTINEL_PREFIX = "__PBI_AGENT_BASH_DONE__"


@dataclass(slots=True)
class BashExecutionResult:
    output: str
    exit_code: int | None
    timed_out: bool
    is_error: bool


class _PersistentBashSession:
    """Simple persistent bash session used by Anthropic native ``bash`` calls."""

    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._output_queue: queue.Queue[str] | None = None
        self._reader_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._start_session_locked()

    def execute(self, command: str, *, timeout_seconds: int) -> BashExecutionResult:
        with self._lock:
            self._ensure_running_locked()
            assert self._process is not None
            assert self._process.stdin is not None
            assert self._output_queue is not None

            sentinel = f"{_BASH_SENTINEL_PREFIX}_{uuid.uuid4().hex}"
            shell_family = _detect_shell_family(self._process.args)
            wrapped_command = _wrap_command_with_sentinel(
                command=command,
                sentinel=sentinel,
                shell_family=shell_family,
            )

            try:
                self._process.stdin.write(wrapped_command)
                self._process.stdin.flush()
            except Exception as exc:
                _log.debug("Failed to write command to persistent bash", exc_info=True)
                self._restart_locked()
                return BashExecutionResult(
                    output=f"Error: Failed to execute command: {exc}",
                    exit_code=1,
                    timed_out=False,
                    is_error=True,
                )

            output_parts: list[str] = []
            deadline = time.monotonic() + timeout_seconds

            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    partial_output = "".join(output_parts).strip()
                    self._restart_locked()
                    timeout_message = (
                        f"Error: Command timed out after {timeout_seconds} seconds."
                    )
                    if partial_output:
                        timeout_message = f"{partial_output}\n{timeout_message}"
                    return BashExecutionResult(
                        output=timeout_message,
                        exit_code=None,
                        timed_out=True,
                        is_error=True,
                    )

                try:
                    chunk = self._output_queue.get(timeout=remaining)
                except queue.Empty:
                    continue

                marker = f"{sentinel}:"
                if marker in chunk:
                    before, _, after = chunk.partition(marker)
                    if before:
                        output_parts.append(before)

                    exit_code = _parse_exit_code(after)
                    if exit_code is None:
                        output_text = "".join(output_parts).strip()
                        if not output_text:
                            output_text = "Error: Could not parse command exit code."
                        return BashExecutionResult(
                            output=output_text,
                            exit_code=1,
                            timed_out=False,
                            is_error=True,
                        )

                    output_text = "".join(output_parts).strip()
                    if not output_text:
                        output_text = "(no output)"

                    is_error = exit_code != 0
                    if is_error:
                        output_text = f"{output_text}\n(exit code: {exit_code})"

                    return BashExecutionResult(
                        output=output_text,
                        exit_code=exit_code,
                        timed_out=False,
                        is_error=is_error,
                    )

                output_parts.append(chunk)

    def restart(self) -> None:
        with self._lock:
            self._restart_locked()

    def close(self) -> None:
        with self._lock:
            self._stop_session_locked()

    def _ensure_running_locked(self) -> None:
        if self._process is None or self._process.poll() is not None:
            self._restart_locked()

    def _restart_locked(self) -> None:
        self._stop_session_locked()
        self._start_session_locked()

    def _start_session_locked(self) -> None:
        executable, args, shell_family = _resolve_shell_command()
        _log.debug(
            "Starting persistent shell session: executable=%s family=%s",
            executable,
            shell_family,
        )

        self._output_queue = queue.Queue()
        self._process = subprocess.Popen(
            [executable, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(Path.cwd()),
            env=dict(os.environ),
            bufsize=1,
        )
        assert self._process.stdout is not None
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            args=(self._process.stdout, self._output_queue),
            daemon=True,
        )
        self._reader_thread.start()

    def _stop_session_locked(self) -> None:
        process = self._process
        self._process = None
        self._output_queue = None
        self._reader_thread = None

        if process is None:
            return

        try:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=2)
        except Exception:
            if process.poll() is None:
                process.kill()
        finally:
            try:
                if process.stdin is not None:
                    process.stdin.close()
            except Exception:
                pass
            try:
                if process.stdout is not None:
                    process.stdout.close()
            except Exception:
                pass

    @staticmethod
    def _reader_loop(stdout_stream: Any, output_queue: queue.Queue[str]) -> None:
        try:
            for line in iter(stdout_stream.readline, ""):
                output_queue.put(line)
        except Exception:
            _log.debug("Persistent bash reader terminated", exc_info=True)


_BASH_SESSION: _PersistentBashSession | None = None
_BASH_SESSION_LOCK = threading.Lock()


def _get_bash_session() -> _PersistentBashSession:
    global _BASH_SESSION
    with _BASH_SESSION_LOCK:
        if _BASH_SESSION is None:
            _BASH_SESSION = _PersistentBashSession()
        return _BASH_SESSION


def close_bash_session() -> None:
    global _BASH_SESSION
    with _BASH_SESSION_LOCK:
        if _BASH_SESSION is not None:
            _BASH_SESSION.close()
            _BASH_SESSION = None


def _parse_exit_code(raw_marker_tail: str) -> int | None:
    marker_tail = raw_marker_tail.strip()
    if not marker_tail:
        return None
    first_line = marker_tail.splitlines()[0].strip()
    try:
        return int(first_line)
    except ValueError:
        return None


def _resolve_shell_command() -> tuple[str, list[str], str]:
    """Return (executable, args, family) for an available interactive shell."""
    if os.name == "nt":
        for candidate in ("bash.exe", "bash", "sh.exe", "sh"):
            resolved = shutil.which(candidate)
            if resolved:
                return resolved, [], "bash"

        comspec = os.environ.get("COMSPEC")
        if comspec and Path(comspec).exists():
            return comspec, ["/Q", "/K"], "cmd"

        cmd_path = shutil.which("cmd.exe") or shutil.which("cmd")
        if cmd_path:
            return cmd_path, ["/Q", "/K"], "cmd"

        raise FileNotFoundError(
            "No supported shell found. Install bash or ensure cmd.exe is available."
        )

    for candidate in ("/bin/bash", "bash", "/bin/sh", "sh"):
        resolved = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if resolved and Path(resolved).exists():
            family = "bash" if "bash" in Path(resolved).name else "sh"
            return str(resolved), [], family

    raise FileNotFoundError("No supported shell found (bash/sh).")


def _detect_shell_family(process_args: Any) -> str:
    try:
        if isinstance(process_args, list) and process_args:
            executable = str(process_args[0]).lower()
        else:
            executable = str(process_args).lower()
    except Exception:
        return "bash"

    if "cmd" in executable:
        return "cmd"
    return "bash"


def _wrap_command_with_sentinel(
    *, command: str, sentinel: str, shell_family: str
) -> str:
    if shell_family == "cmd":
        return f"{command}\r\necho {sentinel}:%errorlevel%\r\n"
    return f"{command}\nprintf '\\n{sentinel}:%s\\n' \"$?\"\n"


# ---------------------------------------------------------------------------
# Bash tool executor  (bash_20250124)
# ---------------------------------------------------------------------------


def execute_bash(input_data: dict[str, Any]) -> BashExecutionResult:
    """Execute an Anthropic ``bash`` tool call.

    *input_data* has the shape ``{"command": "...", "restart": bool}``.
    Returns command output plus execution metadata.
    """
    if input_data.get("restart"):
        _get_bash_session().restart()
        return BashExecutionResult(
            output="Bash session restarted.",
            exit_code=0,
            timed_out=False,
            is_error=False,
        )

    command = input_data.get("command")
    if not command or not isinstance(command, str):
        return BashExecutionResult(
            output="Error: 'command' parameter is required and must be a non-empty string.",
            exit_code=1,
            timed_out=False,
            is_error=True,
        )

    return _get_bash_session().execute(command, timeout_seconds=BASH_TIMEOUT_SECONDS)


# ---------------------------------------------------------------------------
# Text editor tool executor  (text_editor_20250728)
# ---------------------------------------------------------------------------


def execute_text_editor(input_data: dict[str, Any]) -> str:
    """Execute an Anthropic ``str_replace_based_edit_tool`` tool call.

    Supports commands: ``view``, ``str_replace``, ``create``, ``insert``.
    """
    command = input_data.get("command", "")
    file_path = input_data.get("path", "")

    if command == "view":
        return _editor_view(file_path, input_data.get("view_range"))
    elif command == "str_replace":
        return _editor_str_replace(
            file_path, input_data.get("old_str", ""), input_data.get("new_str", "")
        )
    elif command == "create":
        return _editor_create(file_path, input_data.get("file_text", ""))
    elif command == "insert":
        return _editor_insert(
            file_path,
            input_data.get("insert_line", 0),
            input_data.get("insert_text", ""),
        )
    else:
        return f"Error: Unknown command '{command}'. Supported: view, str_replace, create, insert."


def _editor_view(raw_path: str, view_range: list[int] | None) -> str:
    """Read file contents with line numbers, or list directory contents."""
    if not raw_path:
        return "Error: 'path' parameter is required."

    try:
        target = _resolve_path(raw_path)
    except (PermissionError, ValueError) as exc:
        return f"Error: {exc}"

    # Directory listing
    if target.is_dir():
        try:
            entries = sorted(target.iterdir())
            lines: list[str] = []
            for entry in entries:
                name = entry.name + ("/" if entry.is_dir() else "")
                lines.append(name)
            return "\n".join(lines) if lines else "(empty directory)"
        except PermissionError:
            return f"Error: Permission denied reading directory: {raw_path}"

    # File reading
    if not target.exists():
        return f"Error: File not found: {raw_path}"

    try:
        content = target.read_text(encoding="utf-8")
    except PermissionError:
        return f"Error: Permission denied reading file: {raw_path}"
    except UnicodeDecodeError:
        return f"Error: File is not valid UTF-8: {raw_path}"

    all_lines = content.splitlines(keepends=True)

    if view_range and isinstance(view_range, list) and len(view_range) == 2:
        start = max(1, view_range[0])
        end = view_range[1] if view_range[1] != -1 else len(all_lines)
        end = min(end, len(all_lines))
        selected = all_lines[start - 1 : end]
        numbered = [f"{start + i}: {line}" for i, line in enumerate(selected)]
    else:
        numbered = [f"{i + 1}: {line}" for i, line in enumerate(all_lines)]

    result = "".join(numbered)
    # Ensure we don't return an absurdly large output
    max_chars = 100_000
    if len(result) > max_chars:
        result = (
            result[:max_chars]
            + f"\n\n... Output truncated ({len(all_lines)} total lines) ..."
        )
    return result


def _editor_str_replace(raw_path: str, old_str: str, new_str: str) -> str:
    """Replace *old_str* with *new_str* in the file.  Must match exactly once."""
    if not raw_path:
        return "Error: 'path' parameter is required."
    if not old_str:
        return "Error: 'old_str' parameter is required and must be non-empty."

    try:
        target = _resolve_path(raw_path)
    except (PermissionError, ValueError) as exc:
        return f"Error: {exc}"
    if not target.exists():
        return f"Error: File not found: {raw_path}"

    try:
        content = target.read_text(encoding="utf-8")
    except (PermissionError, UnicodeDecodeError) as exc:
        return f"Error: Cannot read file: {exc}"

    count = content.count(old_str)
    if count == 0:
        return "Error: No match found for replacement text. Please check your text and try again."
    if count > 1:
        return (
            f"Error: Found {count} matches for replacement text. "
            "Please provide more context to make a unique match."
        )

    new_content = content.replace(old_str, new_str, 1)
    try:
        target.write_text(new_content, encoding="utf-8")
    except PermissionError:
        return f"Error: Permission denied writing to file: {raw_path}"

    return "Successfully replaced text at exactly one location."


def _editor_create(raw_path: str, file_text: str) -> str:
    """Create a new file with the given content."""
    if not raw_path:
        return "Error: 'path' parameter is required."

    try:
        target = _resolve_path(raw_path)
    except (PermissionError, ValueError) as exc:
        return f"Error: {exc}"
    if target.exists():
        return f"Error: File already exists: {raw_path}. Use str_replace to edit existing files."

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file_text, encoding="utf-8")
    except PermissionError:
        return f"Error: Permission denied creating file: {raw_path}"

    return f"Successfully created file: {raw_path}"


def _editor_insert(raw_path: str, insert_line: int, insert_text: str) -> str:
    """Insert *insert_text* after line *insert_line* (0 = beginning of file)."""
    if not raw_path:
        return "Error: 'path' parameter is required."

    try:
        target = _resolve_path(raw_path)
    except (PermissionError, ValueError) as exc:
        return f"Error: {exc}"
    if not target.exists():
        return f"Error: File not found: {raw_path}"

    if not isinstance(insert_text, str):
        return "Error: 'insert_text' must be a string."

    try:
        content = target.read_text(encoding="utf-8")
    except (PermissionError, UnicodeDecodeError) as exc:
        return f"Error: Cannot read file: {exc}"

    lines = content.splitlines(keepends=True)

    # Validate insert_line
    if not isinstance(insert_line, int) or insert_line < 0:
        return "Error: 'insert_line' must be a non-negative integer."
    if insert_line > len(lines):
        return (
            f"Error: 'insert_line' ({insert_line}) is past the end of file "
            f"({len(lines)} lines)."
        )

    # Ensure the inserted text ends with a newline so it doesn't merge with
    # the next line.
    insert_text = insert_text if insert_text.endswith("\n") else insert_text + "\n"

    new_lines = lines[:insert_line] + [insert_text] + lines[insert_line:]
    new_content = "".join(new_lines)

    try:
        target.write_text(new_content, encoding="utf-8")
    except PermissionError:
        return f"Error: Permission denied writing to file: {raw_path}"

    return f"Successfully inserted text after line {insert_line}."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_path(raw_path: str) -> Path:
    """Resolve a path relative to cwd, blocking traversal outside workspace."""
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("'path' parameter must be a non-empty string.")

    candidate = Path(raw_path)
    root = Path.cwd().resolve()

    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (root / candidate).resolve()

    # Safety: block paths outside the workspace root
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PermissionError(
            f"Path outside workspace is not allowed: {raw_path}"
        ) from exc

    return resolved
