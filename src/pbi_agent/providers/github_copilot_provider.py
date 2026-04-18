"""GitHub Copilot Responses HTTP provider."""

from __future__ import annotations

import json
from typing import Any

from pbi_agent import __version__
from pbi_agent.config import Settings
from pbi_agent.providers.chatgpt_codex_backend import ResponsesRequestOptions
from pbi_agent.providers.openai_provider import OpenAIProvider
from pbi_agent.tools.catalog import ToolCatalog


class GitHubCopilotProvider(OpenAIProvider):
    """Provider backed by GitHub Copilot's Responses API."""

    def __init__(
        self,
        settings: Settings,
        *,
        system_prompt: str | None = None,
        excluded_tools: set[str] | None = None,
        tool_catalog: ToolCatalog | None = None,
    ) -> None:
        super().__init__(
            settings,
            system_prompt=system_prompt,
            excluded_tools=excluded_tools,
            tool_catalog=tool_catalog,
        )

    def _responses_request_options(self) -> ResponsesRequestOptions:
        return ResponsesRequestOptions(stream=True)

    def _build_request_body(
        self,
        *,
        input_items: list[dict[str, Any]],
        instructions: str | None,
        session_id: str | None = None,
        include_previous_response_id: bool = True,
    ) -> dict[str, Any]:
        body = super()._build_request_body(
            input_items=input_items,
            instructions=instructions,
            session_id=session_id,
            include_previous_response_id=include_previous_response_id,
        )
        body["stream"] = True
        if self._settings.model.startswith("gpt"):
            body.pop("max_output_tokens", None)
        return body

    def _request_headers(
        self,
        *,
        request_auth: Any,
        session_id: str | None,
        input_items: list[dict[str, Any]],
    ) -> dict[str, str]:
        headers = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "User-Agent": f"pbi-agent/{__version__}",
            "Openai-Intent": "conversation-edits",
            "x-initiator": (
                "user" if _is_user_initiated_request(input_items) else "agent"
            ),
            **request_auth.headers,
        }
        if _has_image_inputs(input_items):
            headers["Copilot-Vision-Request"] = "true"
        if session_id:
            headers["session_id"] = session_id
        return headers

    def _decode_response_body(
        self,
        raw_body: str,
        *,
        streamed: bool,
    ) -> dict[str, Any]:
        return _decode_copilot_responses_body(raw_body, streamed=streamed)


def _is_user_initiated_request(input_items: list[dict[str, Any]]) -> bool:
    if not input_items:
        return False
    last_item = input_items[-1]
    return last_item.get("role") == "user"


def _has_image_inputs(input_items: list[dict[str, Any]]) -> bool:
    for item in input_items:
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "input_image":
                return True
    return False


def _decode_copilot_responses_body(raw_body: str, *, streamed: bool) -> dict[str, Any]:
    normalized = raw_body.strip()
    if not streamed or normalized.startswith("{"):
        return json.loads(normalized)
    return _parse_copilot_sse_response(normalized)


def _parse_copilot_sse_response(raw_body: str) -> dict[str, Any]:
    event_name: str | None = None
    data_lines: list[str] = []
    last_response: dict[str, Any] | None = None
    last_error: dict[str, Any] | None = None
    response_meta: dict[str, Any] = {}
    output_items: dict[int, dict[str, Any]] = {}
    current_text_output_index: int | None = None
    current_reasoning_output_index: int | None = None

    def flush_event() -> None:
        nonlocal event_name, data_lines, last_response, last_error
        nonlocal current_text_output_index, current_reasoning_output_index
        if not data_lines:
            event_name = None
            return
        payload_text = "\n".join(data_lines).strip()
        data_lines = []
        if not payload_text:
            event_name = None
            return
        payload = json.loads(payload_text)
        event_type = event_name or payload.get("type")
        if event_type == "response.created":
            response = payload.get("response")
            if isinstance(response, dict):
                response_meta.update(response)
        elif event_type == "response.output_item.added":
            output_index = payload.get("output_index")
            item = payload.get("item")
            if isinstance(output_index, int) and isinstance(item, dict):
                normalized_item = _normalize_copilot_output_item(item)
                output_items[output_index] = normalized_item
                if normalized_item.get("type") == "message":
                    current_text_output_index = output_index
                elif normalized_item.get("type") == "reasoning":
                    current_reasoning_output_index = output_index
        elif event_type == "response.output_item.done":
            output_index = payload.get("output_index")
            item = payload.get("item")
            if isinstance(output_index, int) and isinstance(item, dict):
                normalized_item = _normalize_copilot_output_item(item)
                existing_item = output_items.get(output_index)
                if existing_item is not None:
                    output_items[output_index] = _merge_copilot_output_item(
                        existing_item, normalized_item
                    )
                else:
                    output_items[output_index] = normalized_item
                item_type = output_items[output_index].get("type")
                if item_type == "message":
                    current_text_output_index = None
                elif item_type == "reasoning":
                    current_reasoning_output_index = None
        elif event_type == "response.output_text.delta":
            delta = payload.get("delta")
            item_id = payload.get("item_id")
            if isinstance(delta, str):
                current_text_output_index = _append_copilot_message_delta(
                    output_items=output_items,
                    output_index=current_text_output_index,
                    item_id=item_id if isinstance(item_id, str) else None,
                    delta=delta,
                )
        elif event_type == "response.function_call_arguments.delta":
            output_index = payload.get("output_index")
            delta = payload.get("delta")
            item_id = payload.get("item_id")
            if isinstance(output_index, int) and isinstance(delta, str):
                _append_copilot_function_arguments_delta(
                    output_items=output_items,
                    output_index=output_index,
                    item_id=item_id if isinstance(item_id, str) else None,
                    delta=delta,
                )
        elif event_type == "response.reasoning_summary_part.added":
            summary_index = payload.get("summary_index", 0)
            if current_reasoning_output_index is not None and isinstance(
                summary_index, int
            ):
                _ensure_copilot_reasoning_summary_index(
                    output_items=output_items,
                    output_index=current_reasoning_output_index,
                    summary_index=summary_index,
                )
        elif event_type == "response.reasoning_summary_text.delta":
            delta = payload.get("delta")
            summary_index = payload.get("summary_index", 0)
            if (
                current_reasoning_output_index is not None
                and isinstance(delta, str)
                and isinstance(summary_index, int)
            ):
                _append_copilot_reasoning_summary_delta(
                    output_items=output_items,
                    output_index=current_reasoning_output_index,
                    summary_index=summary_index,
                    delta=delta,
                )
        if event_type in {"response.completed", "response.incomplete"}:
            response = payload.get("response")
            if isinstance(response, dict):
                last_response = response
        elif event_type == "response.failed":
            last_error = payload
        event_name = None

    for raw_line in raw_body.splitlines():
        line = raw_line.rstrip("\r")
        if not line:
            flush_event()
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    flush_event()

    if last_response is not None:
        merged_response = dict(response_meta)
        merged_response.update(last_response)
        ordered_output = [
            output_items[index]
            for index in sorted(output_items)
            if isinstance(output_items[index], dict)
        ]
        if ordered_output and not merged_response.get("output"):
            merged_response["output"] = ordered_output
        return merged_response
    if last_error is not None:
        return last_error
    raise ValueError("Stream ended without a response.completed event")


def _normalize_copilot_output_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    item_type = normalized.get("type")
    if item_type == "message":
        normalized.setdefault("role", "assistant")
        if not isinstance(normalized.get("content"), list):
            normalized["content"] = []
    elif item_type == "reasoning":
        if not isinstance(normalized.get("summary"), list):
            normalized["summary"] = []
    elif item_type == "function_call":
        normalized.setdefault("arguments", "")
    return normalized


def _merge_copilot_output_item(
    existing: dict[str, Any],
    new_item: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in new_item.items():
        if key in {"content", "summary"} and isinstance(value, list) and not value:
            continue
        merged[key] = value
    return merged


def _append_copilot_message_delta(
    *,
    output_items: dict[int, dict[str, Any]],
    output_index: int | None,
    item_id: str | None,
    delta: str,
) -> int:
    resolved_index = output_index
    if resolved_index is None:
        resolved_index = max(output_items.keys(), default=-1) + 1
    item = output_items.get(resolved_index)
    if item is None:
        item = {
            "id": item_id or f"message_{resolved_index}",
            "type": "message",
            "role": "assistant",
            "content": [],
        }
        output_items[resolved_index] = item
    content = item.setdefault("content", [])
    if not content:
        content.append({"type": "output_text", "text": delta})
        return resolved_index
    first_part = content[0]
    if isinstance(first_part, dict) and first_part.get("type") == "output_text":
        first_part["text"] = f"{first_part.get('text', '')}{delta}"
    return resolved_index


def _append_copilot_function_arguments_delta(
    *,
    output_items: dict[int, dict[str, Any]],
    output_index: int,
    item_id: str | None,
    delta: str,
) -> None:
    item = output_items.get(output_index)
    if item is None:
        item = {
            "id": item_id or f"function_call_{output_index}",
            "type": "function_call",
            "call_id": item_id or f"call_{output_index}",
            "name": "",
            "arguments": "",
        }
        output_items[output_index] = item
    item["arguments"] = f"{item.get('arguments', '')}{delta}"


def _ensure_copilot_reasoning_summary_index(
    *,
    output_items: dict[int, dict[str, Any]],
    output_index: int,
    summary_index: int,
) -> None:
    item = output_items.get(output_index)
    if item is None:
        item = {
            "id": f"reasoning_{output_index}",
            "type": "reasoning",
            "summary": [],
        }
        output_items[output_index] = item
    summary = item.setdefault("summary", [])
    while len(summary) <= summary_index:
        summary.append({"type": "summary_text", "text": ""})


def _append_copilot_reasoning_summary_delta(
    *,
    output_items: dict[int, dict[str, Any]],
    output_index: int,
    summary_index: int,
    delta: str,
) -> None:
    _ensure_copilot_reasoning_summary_index(
        output_items=output_items,
        output_index=output_index,
        summary_index=summary_index,
    )
    summary = output_items[output_index]["summary"]
    summary_item = summary[summary_index]
    if isinstance(summary_item, dict):
        summary_item["type"] = "summary_text"
        summary_item["text"] = f"{summary_item.get('text', '')}{delta}"
