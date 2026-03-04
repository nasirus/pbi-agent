"""OpenAI Responses WebSocket provider.

Wraps the existing ``ws_client``, ``protocol``, and tool-runtime modules
behind the :class:`Provider` interface.  Conversation history is managed
server-side via ``previous_response_id``.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from pbi_agent.agent.apply_patch_runtime import execute_apply_patch_calls
from pbi_agent.agent.protocol import (
    RateLimitError,
    build_response_create_payload,
    parse_completed_response,
    parse_error_event,
)
from pbi_agent.agent.shell_runtime import execute_shell_calls
from pbi_agent.agent.system_prompt import get_system_prompt
from pbi_agent.agent.tool_runtime import (
    execute_tool_calls,
    to_function_call_output_items,
)
from pbi_agent.agent.ws_client import (
    ResponsesWebSocketClient,
    WebSocketClientError,
    WebSocketClientTransientError,
)
from pbi_agent.config import Settings
from pbi_agent.display import Display
from pbi_agent.models.messages import CompletedResponse, TokenUsage
from pbi_agent.providers.base import Provider
from pbi_agent.tools.registry import get_openai_tool_definitions

_log = logging.getLogger(__name__)


class OpenAIProvider(Provider):
    """Provider backed by OpenAI's Responses WebSocket API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._ws: ResponsesWebSocketClient | None = None
        self._previous_response_id: str | None = None
        self._tools = get_openai_tool_definitions()
        self._instructions = get_system_prompt()

    # -- lifecycle -----------------------------------------------------------

    def connect(self) -> None:
        if self._ws is not None:
            return
        self._ws = ResponsesWebSocketClient(
            self._settings.ws_url, self._settings.api_key
        )
        self._ws.connect()

    def close(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None

    # -- request_turn --------------------------------------------------------

    def request_turn(
        self,
        *,
        user_message: str | None = None,
        tool_result_items: list[dict[str, Any]] | None = None,
        instructions: str | None = None,
        display: Display,
        session_usage: TokenUsage,
    ) -> CompletedResponse:
        assert self._ws is not None, "Provider is not connected"

        if user_message is not None:
            input_items: list[dict[str, Any]] = [_build_user_input_item(user_message)]
        elif tool_result_items is not None:
            input_items = tool_result_items
        else:
            raise ValueError("Either user_message or tool_result_items is required")

        effective_instructions = instructions or self._instructions
        response = self._request_with_retries(
            input_items=input_items,
            instructions=effective_instructions,
            display=display,
            session_usage=session_usage,
        )
        self._previous_response_id = response.response_id
        return response

    # -- execute_tool_calls --------------------------------------------------

    def execute_tool_calls(
        self,
        response: CompletedResponse,
        *,
        max_workers: int,
        display: Display,
    ) -> tuple[list[dict[str, Any]], bool]:
        had_errors = False
        output_items: list[dict[str, Any]] = []

        # --- function calls ------------------------------------------------
        if response.function_calls:
            display.function_start(len(response.function_calls))
            function_batch = execute_tool_calls(
                response.function_calls,
                max_workers=max_workers,
            )
            had_errors = had_errors or function_batch.had_errors
            for result in function_batch.results:
                call = _find_function_call(response.function_calls, result.call_id)
                display.function_result(
                    name=call.name if call else "unknown",
                    success=not result.is_error,
                    call_id=result.call_id,
                    arguments=call.arguments if call else None,
                )
            output_items.extend(to_function_call_output_items(function_batch.results))
            display.tool_group_end()

        # --- apply_patch calls ---------------------------------------------
        if response.apply_patch_calls:
            display.patch_start(len(response.apply_patch_calls))
            apply_patch_items, ap_errors = execute_apply_patch_calls(
                response.apply_patch_calls,
                workspace_root=Path.cwd(),
            )
            had_errors = had_errors or ap_errors
            for call, item in zip(response.apply_patch_calls, apply_patch_items):
                status = item.get("status", "unknown")
                output = str(item.get("output", ""))
                display.patch_result(
                    path=call.operation.get("path", "<missing>"),
                    operation=call.operation.get("type", "update"),
                    success=(status != "failed" and status != "error"),
                    call_id=item.get("call_id", ""),
                    detail=output,
                )
            output_items.extend(apply_patch_items)
            display.tool_group_end()

        # --- shell calls ---------------------------------------------------
        if response.shell_calls:
            all_commands = _collect_shell_commands(response.shell_calls)
            display.shell_start(all_commands)
            shell_items, shell_errors = execute_shell_calls(
                response.shell_calls,
                workspace_root=Path.cwd(),
            )
            had_errors = had_errors or shell_errors
            for call, item in zip(response.shell_calls, shell_items):
                commands = call.action.get("commands", [])
                timeout_ms = call.action.get("timeout_ms", "default")
                working_directory = call.action.get("working_directory", ".")
                outcomes = _extract_shell_outcomes(item.get("output"))
                for idx, command in enumerate(commands):
                    exit_code, timed_out = (
                        outcomes[idx] if idx < len(outcomes) else (None, False)
                    )
                    display.shell_command(
                        command=command,
                        exit_code=exit_code,
                        timed_out=timed_out,
                        call_id=call.call_id,
                        working_directory=working_directory,
                        timeout_ms=timeout_ms,
                    )
            output_items.extend(shell_items)
            display.tool_group_end()

        return output_items, had_errors

    # -- internal transport --------------------------------------------------

    def _request_with_retries(
        self,
        *,
        input_items: list[dict[str, Any]],
        instructions: str | None,
        display: Display,
        session_usage: TokenUsage,
    ) -> CompletedResponse:
        assert self._ws is not None

        payload = build_response_create_payload(
            model=self._settings.model,
            input_items=input_items,
            tools=self._tools,
            previous_response_id=self._previous_response_id,
            store=True,
            instructions=instructions,
            reasoning_effort=self._settings.reasoning_effort,
            compact_threshold=self._settings.compact_threshold,
        )

        max_retries = self._settings.ws_max_retries
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            if attempt > 0:
                display.retry_notice(attempt, max_retries)
                self._ws.reconnect()
            try:
                self._ws.send_json(payload)
                response = self._read_one_response(
                    stream_output=True,
                    display=display,
                    waiting_message=_waiting_message_for_input_items(input_items),
                )
                session_usage.add(response.usage)
                return response
            except RateLimitError as exc:
                if attempt >= max_retries:
                    raise
                wait_seconds = _rate_limit_wait(exc, attempt)
                display.rate_limit_notice(
                    wait_seconds=wait_seconds,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                time.sleep(wait_seconds)
                continue
            except WebSocketClientTransientError as exc:
                last_error = exc
                continue
            except WebSocketClientError:
                raise

        if last_error is not None:
            raise WebSocketClientError(str(last_error)) from last_error
        raise WebSocketClientError("WebSocket request failed after retries.")

    def _read_one_response(
        self,
        *,
        stream_output: bool,
        display: Display,
        waiting_message: str,
    ) -> CompletedResponse:
        assert self._ws is not None

        streamed_text_parts: list[str] = []
        if stream_output:
            display.wait_start(waiting_message)

        try:
            while True:
                event = self._ws.recv_json()
                event_type = event.get("type")

                if event_type == "response.output_text.delta":
                    delta = event.get("delta", "")
                    if delta:
                        streamed_text_parts.append(delta)
                        if stream_output:
                            display.stream_delta(delta)
                elif event_type == "response.completed":
                    if stream_output:
                        display.stream_end()
                    return parse_completed_response(
                        event.get("response", {}), streamed_text_parts
                    )
                elif event_type == "error":
                    raise parse_error_event(event)
        except Exception:
            if stream_output:
                display.stream_abort()
            raise


# ---------------------------------------------------------------------------
# Utilities (moved from session.py)
# ---------------------------------------------------------------------------


def _build_user_input_item(prompt: str) -> dict[str, Any]:
    return {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": prompt}],
    }


def _find_function_call(calls: list, call_id: str):  # type: ignore[type-arg]
    for c in calls:
        if c.call_id == call_id:
            return c
    return None


def _collect_shell_commands(shell_calls: list) -> list[str]:  # type: ignore[type-arg]
    commands: list[str] = []
    for call in shell_calls:
        cmds = call.action.get("commands", [])
        if isinstance(cmds, list):
            commands.extend(cmds)
    return commands


def _extract_shell_outcomes(output: Any) -> list[tuple[int | None, bool]]:
    if not isinstance(output, list):
        return []
    results: list[tuple[int | None, bool]] = []
    for chunk in output:
        if not isinstance(chunk, dict):
            results.append((None, False))
            continue
        outcome = chunk.get("outcome")
        if not isinstance(outcome, dict):
            results.append((None, False))
            continue
        outcome_type = outcome.get("type")
        if outcome_type == "timeout":
            results.append((None, True))
        elif outcome_type == "exit":
            results.append((outcome.get("exit_code"), False))
        else:
            results.append((None, False))
    return results


def _waiting_message_for_input_items(input_items: list[dict[str, Any]]) -> str:
    item_types = {
        item.get("type")
        for item in input_items
        if isinstance(item, dict) and isinstance(item.get("type"), str)
    }
    if "message" in item_types:
        return "analyzing your request..."
    if item_types & {
        "function_call_output",
        "apply_patch_call_output",
        "shell_call_output",
    }:
        return "integrating tool results..."
    return "processing..."


def _rate_limit_wait(error: RateLimitError, attempt: int) -> float:
    if error.retry_after_seconds is not None:
        return max(0.1, min(error.retry_after_seconds, 30.0))
    return min(2.0 * (2**attempt), 30.0)
