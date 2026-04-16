from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from pbi_agent.auth.models import (
    AUTH_MODE_CHATGPT_ACCOUNT,
    AUTH_SESSION_STATUS_CONNECTED,
    AUTH_SESSION_STATUS_EXPIRED,
    AUTH_SESSION_STATUS_MISSING,
    ProviderAuthStatus,
    RequestAuthConfig,
    StoredAuthSession,
)
from pbi_agent.auth.providers.base import AuthProviderBackend
from pbi_agent.auth.store import build_auth_session

OPENAI_CHATGPT_BACKEND_ID = "openai_chatgpt"
OPENAI_CHATGPT_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"
OPENAI_CHATGPT_REFRESH_URL = "https://auth.openai.com/oauth/token"
OPENAI_CHATGPT_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
_TOKEN_REFRESH_TIMEOUT_SECS = 30.0


class OpenAIChatGPTAuthBackend(AuthProviderBackend):
    @property
    def backend_id(self) -> str:
        return OPENAI_CHATGPT_BACKEND_ID

    def build_status(self, session: StoredAuthSession | None) -> ProviderAuthStatus:
        if session is None:
            return ProviderAuthStatus(
                auth_mode=AUTH_MODE_CHATGPT_ACCOUNT,
                backend=self.backend_id,
                session_status=AUTH_SESSION_STATUS_MISSING,
                has_session=False,
                can_refresh=False,
            )
        return ProviderAuthStatus(
            auth_mode=AUTH_MODE_CHATGPT_ACCOUNT,
            backend=self.backend_id,
            session_status=(
                AUTH_SESSION_STATUS_EXPIRED
                if session.is_expired()
                else AUTH_SESSION_STATUS_CONNECTED
            ),
            has_session=True,
            can_refresh=bool(session.refresh_token),
            account_id=session.account_id,
            email=session.email,
            plan_type=session.plan_type,
            expires_at=session.expires_at,
        )

    def import_session(
        self,
        *,
        provider_id: str,
        payload: dict[str, Any],
        previous: StoredAuthSession | None = None,
    ) -> StoredAuthSession:
        access_token = _require_non_empty_string(payload, "access_token")
        refresh_token = _optional_non_empty_string(payload, "refresh_token")
        account_id = _optional_non_empty_string(payload, "account_id")
        email = _optional_non_empty_string(payload, "email")
        plan_type = _optional_non_empty_string(payload, "plan_type")
        id_token = _optional_non_empty_string(payload, "id_token")
        expires_at = _optional_int(payload, "expires_at")
        expires_in = _optional_int(payload, "expires_in")

        access_claims = _decode_jwt_claims(access_token)
        id_claims = _decode_jwt_claims(id_token) if id_token else {}
        merged_claims = dict(access_claims)
        merged_claims.update(id_claims)

        resolved_account_id = (
            account_id
            or _string_value(merged_claims.get("chatgpt_account_id"))
            or _claim_string(
                merged_claims,
                "https://api.openai.com/auth",
                "chatgpt_account_id",
            )
            or _organization_account_id(merged_claims)
        )
        if not resolved_account_id:
            raise ValueError(
                "ChatGPT account auth requires an account_id or a token with "
                "chatgpt_account_id claims."
            )
        resolved_email = (
            email
            or _claim_string(merged_claims, "https://api.openai.com/profile", "email")
            or _string_value(merged_claims.get("email"))
        )
        resolved_plan_type = (
            plan_type
            or _claim_string(
                merged_claims,
                "https://api.openai.com/auth",
                "chatgpt_plan_type",
            )
            or _string_value(merged_claims.get("chatgpt_plan_type"))
        )
        resolved_expires_at = (
            expires_at
            if expires_at is not None
            else _expires_at_from_duration(expires_in)
            if expires_in is not None
            else _int_value(merged_claims.get("exp"))
        )
        metadata = {
            "id_token": id_token,
            "token_source": _optional_non_empty_string(payload, "token_source")
            or "manual_import",
        }
        if previous is not None:
            metadata = {**previous.metadata, **metadata}
        return build_auth_session(
            provider_id=provider_id,
            backend=self.backend_id,
            access_token=access_token,
            refresh_token=refresh_token
            or (previous.refresh_token if previous else None),
            expires_at=resolved_expires_at,
            account_id=resolved_account_id,
            email=resolved_email,
            plan_type=resolved_plan_type,
            metadata=metadata,
            previous=previous,
        )

    def refresh_session(self, session: StoredAuthSession) -> StoredAuthSession:
        if not session.refresh_token:
            raise ValueError(
                "This ChatGPT auth session does not include a refresh token."
            )
        request_body = urllib.parse.urlencode(
            {
                "client_id": OPENAI_CHATGPT_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": session.refresh_token,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            OPENAI_CHATGPT_REFRESH_URL,
            data=request_body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=_TOKEN_REFRESH_TIMEOUT_SECS
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"ChatGPT token refresh failed with status {exc.code}: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"ChatGPT token refresh failed: {exc.reason}") from exc

        imported = self.import_session(
            provider_id=session.provider_id,
            payload={
                "access_token": payload.get("access_token") or session.access_token,
                "refresh_token": payload.get("refresh_token") or session.refresh_token,
                "account_id": session.account_id,
                "email": session.email,
                "plan_type": session.plan_type,
                "expires_in": payload.get("expires_in"),
                "id_token": payload.get("id_token"),
                "token_source": "refresh",
            },
            previous=session,
        )
        return imported

    def build_request_auth(
        self,
        *,
        request_url: str,
        session: StoredAuthSession,
    ) -> RequestAuthConfig:
        headers = {"Authorization": f"Bearer {session.access_token}"}
        if session.account_id:
            headers["ChatGPT-Account-Id"] = session.account_id
        return RequestAuthConfig(request_url=request_url, headers=headers)


def _require_non_empty_string(payload: dict[str, Any], key: str) -> str:
    value = _optional_non_empty_string(payload, key)
    if value is None:
        raise ValueError(f"Missing required auth field '{key}'.")
    return value


def _optional_non_empty_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) else None


def _decode_jwt_claims(token: str | None) -> dict[str, Any]:
    if not token:
        return {}
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload + padding)
        claims = json.loads(decoded.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return {}
    return claims if isinstance(claims, dict) else {}


def _claim_string(
    claims: dict[str, Any], nested_key: str, field_name: str
) -> str | None:
    nested = claims.get(nested_key)
    if not isinstance(nested, dict):
        return None
    return _string_value(nested.get(field_name))


def _string_value(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _int_value(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _organization_account_id(claims: dict[str, Any]) -> str | None:
    organizations = claims.get("organizations")
    if not isinstance(organizations, list):
        return None
    for organization in organizations:
        if not isinstance(organization, dict):
            continue
        account_id = _string_value(organization.get("id"))
        if account_id:
            return account_id
    return None


def _expires_at_from_duration(expires_in: int) -> int:
    current_timestamp = int(datetime.now(timezone.utc).timestamp())
    return current_timestamp + max(expires_in, 0)


def utc_now_timestamp() -> int:
    return int(datetime.now(timezone.utc).timestamp())
