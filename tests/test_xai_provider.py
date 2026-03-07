from __future__ import annotations

import json
import urllib.request

from pbi_agent.agent.system_prompt import get_system_prompt
from pbi_agent.cli import build_parser
from pbi_agent.config import (
    DEFAULT_XAI_MODEL,
    DEFAULT_XAI_RESPONSES_URL,
    DEFAULT_XAI_WS_URL,
    Settings,
    resolve_settings,
)
from pbi_agent.models.messages import TokenUsage
from pbi_agent.providers.xai_provider import XAIProvider


class _DisplayStub:
    def wait_start(self, message: str = "") -> None:
        self.last_wait_message = message

    def wait_stop(self) -> None:
        pass

    def retry_notice(self, attempt: int, max_retries: int) -> None:
        self.retry = (attempt, max_retries)

    def rate_limit_notice(
        self,
        *,
        wait_seconds: float,
        attempt: int,
        max_retries: int,
    ) -> None:
        self.rate_limit = (wait_seconds, attempt, max_retries)

    def session_usage(self, usage: TokenUsage) -> None:
        self.session_usage_snapshot = usage.snapshot()

    def render_thinking(
        self,
        text: str | None = None,
        *,
        title: str | None = None,
        replace_existing: bool = False,
        widget_id: str | None = None,
    ) -> str | None:
        self.thinking = {
            "text": text,
            "title": title,
            "replace_existing": replace_existing,
            "widget_id": widget_id,
        }
        return widget_id

    def render_markdown(self, text: str) -> None:
        self.markdown = text

    def function_start(self, count: int) -> None:
        self.function_count = count

    def function_result(
        self,
        *,
        name: str,
        success: bool,
        call_id: str,
        arguments: object,
    ) -> None:
        self.last_function_result = {
            "name": name,
            "success": success,
            "call_id": call_id,
            "arguments": arguments,
        }

    def tool_group_end(self) -> None:
        self.tool_group_closed = True


class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def _make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "api_key": "test-key",
        "provider": "xai",
        "ws_url": DEFAULT_XAI_WS_URL,
        "responses_url": DEFAULT_XAI_RESPONSES_URL,
        "model": DEFAULT_XAI_MODEL,
        "reasoning_effort": "high",
        "ws_max_retries": 0,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_resolve_settings_uses_xai_defaults(monkeypatch) -> None:
    for name in (
        "PBI_AGENT_PROVIDER",
        "PBI_AGENT_API_KEY",
        "PBI_AGENT_WS_URL",
        "PBI_AGENT_RESPONSES_URL",
        "PBI_AGENT_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("XAI_API_KEY", "xai-test-key")

    parser = build_parser()
    args = parser.parse_args(["--provider", "xai", "chat"])
    settings = resolve_settings(args)

    assert settings.provider == "xai"
    assert settings.api_key == "xai-test-key"
    assert settings.ws_url == DEFAULT_XAI_WS_URL
    assert settings.responses_url == DEFAULT_XAI_RESPONSES_URL
    assert settings.model == DEFAULT_XAI_MODEL
    assert settings.reasoning_effort == "high"
    settings.validate()


def test_xai_build_request_body_omits_unsupported_reasoning_effort() -> None:
    provider = XAIProvider(_make_settings(model="grok-4-1-fast-reasoning"))

    body = provider._build_request_body(
        input_items=[{"role": "user", "content": "hello"}],
        instructions="be concise",
    )

    assert body["stream"] is False
    assert body["parallel_tool_calls"] is True
    assert body["include"] == ["reasoning.encrypted_content"]
    assert body["input"] == [
        {"role": "system", "content": "be concise"},
        {"role": "user", "content": "hello"},
    ]
    assert "instructions" not in body
    assert "reasoning" not in body


def test_xai_build_request_body_maps_grok_3_mini_reasoning_effort() -> None:
    provider = XAIProvider(
        _make_settings(model="grok-3-mini", reasoning_effort="medium")
    )

    body = provider._build_request_body(
        input_items=[{"role": "user", "content": "hello"}],
        instructions="be concise",
    )

    assert body["reasoning"] == {"effort": "high"}
    assert body["input"][0] == {"role": "system", "content": "be concise"}
    assert "include" not in body


def test_xai_parse_response_extracts_function_calls_and_encrypted_reasoning() -> None:
    provider = XAIProvider(_make_settings())

    result = provider._parse_response(
        {
            "id": "resp_123",
            "model": "grok-4-1-fast-reasoning",
            "usage": {
                "input_tokens": 376,
                "input_tokens_details": {"cached_tokens": 282},
                "output_tokens": 233,
                "output_tokens_details": {"reasoning_tokens": 207},
            },
            "reasoning": {"effort": "medium", "summary": "detailed"},
            "output": [
                {
                    "id": "rs_123",
                    "type": "reasoning",
                    "status": "completed",
                    "summary": [
                        {"type": "summary_text", "text": "Planned a tool call"}
                    ],
                    "content": [
                        {
                            "type": "reasoning_text",
                            "text": "Examined the request before deciding to call a tool.",
                        }
                    ],
                    "encrypted_content": "encrypted-value",
                },
                {
                    "arguments": "{\"location\":\"San Francisco\"}",
                    "call_id": "call_88263992",
                    "name": "get_temperature",
                    "type": "function_call",
                    "status": "completed",
                },
            ],
        }
    )

    assert result.response_id == "resp_123"
    assert result.text == ""
    assert result.reasoning_summary == "Planned a tool call"
    assert (
        result.reasoning_content
        == "Examined the request before deciding to call a tool."
    )
    assert result.provider_data["encrypted_reasoning_content"] == ["encrypted-value"]
    assert result.provider_data["reasoning"] == {
        "effort": "medium",
        "summary": "detailed",
    }
    assert result.function_calls[0].call_id == "call_88263992"
    assert result.function_calls[0].name == "get_temperature"
    assert result.function_calls[0].arguments == {"location": "San Francisco"}
    assert result.usage.input_tokens == 376
    assert result.usage.cached_input_tokens == 282
    assert result.usage.output_tokens == 233
    assert result.usage.reasoning_tokens == 207
    assert result.usage.model == "grok-4-1-fast-reasoning"


def test_xai_request_turn_reuses_previous_response_id(monkeypatch) -> None:
    requests: list[dict[str, object]] = []
    responses = iter(
        [
            {
                "id": "resp_1",
                "model": "grok-4-1-fast-reasoning",
                "usage": {
                    "input_tokens": 10,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens": 3,
                    "output_tokens_details": {"reasoning_tokens": 2},
                },
                "output": [
                    {
                        "arguments": "{\"location\":\"San Francisco\"}",
                        "call_id": "call_1",
                        "name": "get_temperature",
                        "type": "function_call",
                    }
                ],
            },
            {
                "id": "resp_2",
                "model": "grok-4-1-fast-reasoning",
                "previous_response_id": "resp_1",
                "usage": {
                    "input_tokens": 12,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens": 4,
                    "output_tokens_details": {"reasoning_tokens": 1},
                },
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {"type": "output_text", "text": "The current temperature is 59F."}
                        ],
                    }
                ],
            },
        ]
    )

    def fake_urlopen(
        request: urllib.request.Request,
        timeout: float,
    ) -> _FakeHTTPResponse:
        del timeout
        payload = request.data.decode("utf-8") if request.data else "{}"
        requests.append(json.loads(payload))
        return _FakeHTTPResponse(next(responses))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    provider = XAIProvider(_make_settings())
    display = _DisplayStub()
    session_usage = TokenUsage(model="grok-4-1-fast-reasoning")

    first_turn_usage = TokenUsage(model="grok-4-1-fast-reasoning")
    first = provider.request_turn(
        user_message="What is the temperature in San Francisco?",
        display=display,
        session_usage=session_usage,
        turn_usage=first_turn_usage,
    )

    second_turn_usage = TokenUsage(model="grok-4-1-fast-reasoning")
    second = provider.request_turn(
        tool_result_items=[
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": '{"temperature":59}',
            }
        ],
        display=display,
        session_usage=session_usage,
        turn_usage=second_turn_usage,
    )

    assert first.response_id == "resp_1"
    assert second.response_id == "resp_2"
    assert requests[0]["input"] == [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": "What is the temperature in San Francisco?"},
    ]
    assert "instructions" not in requests[0]
    assert "previous_response_id" not in requests[0]
    assert requests[1]["previous_response_id"] == "resp_1"
    assert "instructions" not in requests[1]
    assert requests[1]["input"] == [
        {
            "type": "function_call_output",
            "call_id": "call_1",
            "output": '{"temperature":59}',
        }
    ]
