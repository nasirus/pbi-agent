"""Generic OpenAI-compatible Chat Completions HTTP provider.

Designed for OpenAI-compatible gateways (for example OpenRouter) that expose
an OpenAI Chat Completions compatible API.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from pbi_agent.agent.system_prompt import get_system_prompt
from pbi_agent.agent.tool_runtime import execute_tool_calls as _execute_tool_calls
from pbi_agent.config import Settings
from pbi_agent.models.messages import CompletedResponse, TokenUsage, ToolCall
from pbi_agent.providers.base import Provider
from pbi_agent.tools.registry import get_openai_chat_tool_definitions
from pbi_agent.ui import Display

_log = logging.getLogger(__name__)


class GenericProvider(Provider):
    """Provider backed by OpenAI Chat Completions compatible HTTP APIs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._tools = get_openai_chat_tool_definitions()
        self._system_prompt = get_system_prompt()
        self._messages: list[dict[str, Any]] = []

    def connect(self) -> None:
        if not self._settings.api_key:
            raise ValueError(
                "Missing generic provider API key. Set GENERIC_API_KEY in environment "
                "or pass --generic-api-key."
            )

    def close(self) -> None:
        pass

    def request_turn(
        self,
        *,
        user_message: str | None = None,
        tool_result_items: list[dict[str, Any]] | None = None,
        instructions: str | None = None,
        display: Display,
        session_usage: TokenUsage,
        turn_usage: TokenUsage,
    ) -> CompletedResponse:
        if user_message is not None:
            self._messages.append({"role": "user", "content": user_message})
        elif tool_result_items is not None:
            self._messages.extend(tool_result_items)
        else:
            raise ValueError("Either user_message or tool_result_items is required")

        result = self._http_request(
            instructions=instructions or self._system_prompt,
            display=display,
        )
        session_usage.add(result.usage)
        turn_usage.add(result.usage)
        display.session_usage(session_usage)

        assistant_message = result.provider_data.get("assistant_message")
        if isinstance(assistant_message, dict):
            self._messages.append(assistant_message)

        return result

    def execute_tool_calls(
        self,
        response: CompletedResponse,
        *,
        max_workers: int,
        display: Display,
    ) -> tuple[list[dict[str, Any]], bool]:
        if not response.function_calls:
            return [], False

        display.function_start(len(response.function_calls))
        batch = _execute_tool_calls(response.function_calls, max_workers=max_workers)

        tool_result_items: list[dict[str, Any]] = []
        for result in batch.results:
            call = _find_by_id(response.function_calls, result.call_id)
            display.function_result(
                name=call.name if call else "unknown",
                success=not result.is_error,
                call_id=result.call_id,
                arguments=call.arguments if call else None,
            )
            tool_result_items.append(
                {
                    "role": "tool",
                    "tool_call_id": result.call_id,
                    "content": result.output_json,
                }
            )
        display.tool_group_end()
        return tool_result_items, batch.had_errors

    def _http_request(
        self,
        *,
        instructions: str,
        display: Display,
    ) -> CompletedResponse:
        display.wait_start("waiting for generic provider response...")

        messages: list[dict[str, Any]] = [{"role": "system", "content": instructions}]
        messages.extend(self._messages)

        body: dict[str, Any] = {
            "model": self._settings.model,
            "messages": messages,
            "tools": self._tools,
            "tool_choice": "auto",
        }

        request_data = json.dumps(body).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._settings.api_key}",
        }

        max_retries = self._settings.ws_max_retries
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            if attempt > 0:
                display.retry_notice(attempt, max_retries)

            try:
                req = urllib.request.Request(
                    self._settings.generic_api_url,
                    data=request_data,
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=300) as resp:
                    response_json = json.loads(resp.read().decode("utf-8"))

                result = self._parse_response(response_json)
                display.wait_stop()

                if result.text:
                    display.render_markdown(result.text)

                return result
            except urllib.error.HTTPError as exc:
                error_body = ""
                try:
                    error_body = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    pass

                if exc.code == 429:
                    if attempt >= max_retries:
                        display.wait_stop()
                        raise RuntimeError(
                            f"Generic provider rate limit exceeded after {max_retries + 1} "
                            f"attempts: {error_body}"
                        ) from exc
                    wait = _extract_retry_after(exc, attempt)
                    display.rate_limit_notice(
                        wait_seconds=wait,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                    )
                    time.sleep(wait)
                    continue

                if exc.code >= 500:
                    last_error = exc
                    continue

                display.wait_stop()
                raise RuntimeError(
                    f"Generic provider API error {exc.code}: {error_body}"
                ) from exc
            except urllib.error.URLError as exc:
                last_error = exc
                continue

        display.wait_stop()
        if last_error is not None:
            raise RuntimeError(
                f"Generic provider request failed after {max_retries + 1} attempts: "
                f"{last_error}"
            ) from last_error
        raise RuntimeError("Generic provider request failed after retries.")

    def _parse_response(self, response_json: dict[str, Any]) -> CompletedResponse:
        choices = response_json.get("choices", [])
        message = choices[0].get("message", {}) if choices else {}

        content = message.get("content")
        text = content if isinstance(content, str) else ""

        raw_tool_calls = message.get("tool_calls", []) or []
        function_calls: list[ToolCall] = []
        for call in raw_tool_calls:
            function = call.get("function", {})
            raw_args = function.get("arguments", "{}")
            try:
                arguments: dict[str, Any] | str | None = json.loads(raw_args)
            except json.JSONDecodeError:
                arguments = raw_args
            function_calls.append(
                ToolCall(
                    call_id=str(call.get("id", "")),
                    name=str(function.get("name", "")),
                    arguments=arguments,
                )
            )

        usage_obj = response_json.get("usage", {})
        prompt_tokens = int(usage_obj.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage_obj.get("completion_tokens", 0) or 0)
        completion_details = usage_obj.get("completion_tokens_details", {})
        reasoning_tokens = (
            int(completion_details.get("reasoning_tokens", 0) or 0)
            if isinstance(completion_details, dict)
            else 0
        )

        return CompletedResponse(
            response_id=response_json.get("id"),
            text=text,
            usage=TokenUsage(
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
            ),
            function_calls=function_calls,
            provider_data={"assistant_message": message},
        )


def _find_by_id(calls: list[ToolCall], call_id: str) -> ToolCall | None:
    for call in calls:
        if call.call_id == call_id:
            return call
    return None


def _extract_retry_after(exc: urllib.error.HTTPError, attempt: int) -> float:
    try:
        retry_header = exc.headers.get("Retry-After") if exc.headers else None
        if retry_header:
            return max(0.1, min(float(retry_header), 60.0))
    except (TypeError, ValueError):
        pass
    return min(2.0 * (2**attempt), 30.0)
