from __future__ import annotations

import base64
import json
import urllib.request

from pbi_agent.auth.providers.openai_chatgpt import (
    OPENAI_CHATGPT_BACKEND_ID,
    OpenAIChatGPTAuthBackend,
)
from pbi_agent.auth.store import build_auth_session


def _jwt(payload: dict[str, object]) -> str:
    def encode(part: dict[str, object]) -> str:
        raw = json.dumps(part, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"{encode({'alg': 'none', 'typ': 'JWT'})}.{encode(payload)}."


class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def test_import_session_uses_organization_id_as_account_fallback() -> None:
    backend = OpenAIChatGPTAuthBackend()

    session = backend.import_session(
        provider_id="openai-chatgpt",
        payload={
            "access_token": _jwt(
                {
                    "organizations": [
                        {"id": "org_123"},
                        {"id": "org_456"},
                    ],
                    "email": "user@example.com",
                }
            ),
            "refresh_token": "refresh-token",
        },
    )

    assert session.backend == OPENAI_CHATGPT_BACKEND_ID
    assert session.account_id == "org_123"
    assert session.email == "user@example.com"


def test_refresh_session_uses_expires_in_when_token_has_no_exp(monkeypatch) -> None:
    backend = OpenAIChatGPTAuthBackend()
    session = build_auth_session(
        provider_id="openai-chatgpt",
        backend=OPENAI_CHATGPT_BACKEND_ID,
        access_token="old-access-token",
        refresh_token="refresh-token",
        expires_at=100,
        account_id="acct_123",
    )

    def fake_urlopen(
        request: urllib.request.Request,
        timeout: float,
    ) -> _FakeHTTPResponse:
        del request, timeout
        return _FakeHTTPResponse(
            {
                "access_token": _jwt({"email": "user@example.com"}),
                "refresh_token": "next-refresh-token",
                "expires_in": 3600,
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    refreshed = backend.refresh_session(session)

    assert refreshed.access_token != session.access_token
    assert refreshed.refresh_token == "next-refresh-token"
    assert refreshed.account_id == "acct_123"
    assert refreshed.expires_at is not None
    assert refreshed.expires_at > 100
    assert refreshed.email == "user@example.com"
