from __future__ import annotations

import uuid
from html import escape

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from pbi_agent.web.api.deps import SessionManagerDep, model_from_payload
from pbi_agent.web.api.errors import config_http_error
from pbi_agent.web.api.schemas.config import (
    ProviderAuthFlowResponse,
    ProviderAuthFlowStartRequest,
    ProviderAuthImportRequest,
    ProviderAuthLogoutResponse,
    ProviderAuthResponse,
)

router = APIRouter(prefix="/api/provider-auth", tags=["provider-auth"])


@router.get("/{provider_id}", response_model=ProviderAuthResponse)
def get_provider_auth_status(
    provider_id: str,
    manager: SessionManagerDep,
) -> ProviderAuthResponse:
    try:
        payload = manager.get_provider_auth_status(provider_id)
    except Exception as exc:
        raise config_http_error(exc) from exc
    return model_from_payload(ProviderAuthResponse, payload)


@router.post("/{provider_id}/import", response_model=ProviderAuthResponse)
def import_provider_auth(
    provider_id: str,
    request: ProviderAuthImportRequest,
    manager: SessionManagerDep,
) -> ProviderAuthResponse:
    try:
        payload = manager.import_provider_auth(
            provider_id,
            access_token=request.access_token,
            refresh_token=request.refresh_token,
            account_id=request.account_id,
            email=request.email,
            plan_type=request.plan_type,
            expires_at=request.expires_at,
            id_token=request.id_token,
        )
    except Exception as exc:
        raise config_http_error(exc) from exc
    return model_from_payload(ProviderAuthResponse, payload)


@router.post("/{provider_id}/refresh", response_model=ProviderAuthResponse)
def refresh_provider_auth(
    provider_id: str,
    manager: SessionManagerDep,
) -> ProviderAuthResponse:
    try:
        payload = manager.refresh_provider_auth(provider_id)
    except Exception as exc:
        raise config_http_error(exc) from exc
    return model_from_payload(ProviderAuthResponse, payload)


@router.delete("/{provider_id}", response_model=ProviderAuthLogoutResponse)
def logout_provider_auth(
    provider_id: str,
    manager: SessionManagerDep,
) -> ProviderAuthLogoutResponse:
    try:
        payload = manager.logout_provider_auth(provider_id)
    except Exception as exc:
        raise config_http_error(exc) from exc
    return model_from_payload(ProviderAuthLogoutResponse, payload)


@router.post("/{provider_id}/flows", response_model=ProviderAuthFlowResponse)
def start_provider_auth_flow(
    provider_id: str,
    request: ProviderAuthFlowStartRequest,
    http_request: Request,
    manager: SessionManagerDep,
) -> ProviderAuthFlowResponse:
    flow_id = uuid.uuid4().hex
    redirect_uri = None
    if request.method == "browser":
        redirect_uri = str(
            http_request.url_for(
                "provider_auth_flow_callback",
                provider_id=provider_id,
                flow_id=flow_id,
            )
        )
    try:
        payload = manager.start_provider_auth_flow(
            provider_id,
            flow_id=flow_id,
            method=request.method,
            redirect_uri=redirect_uri,
        )
    except Exception as exc:
        raise config_http_error(exc) from exc
    return model_from_payload(ProviderAuthFlowResponse, payload)


@router.get("/{provider_id}/flows/{flow_id}", response_model=ProviderAuthFlowResponse)
def get_provider_auth_flow(
    provider_id: str,
    flow_id: str,
    manager: SessionManagerDep,
) -> ProviderAuthFlowResponse:
    try:
        payload = manager.get_provider_auth_flow(provider_id, flow_id)
    except Exception as exc:
        raise config_http_error(exc) from exc
    return model_from_payload(ProviderAuthFlowResponse, payload)


@router.post(
    "/{provider_id}/flows/{flow_id}/poll",
    response_model=ProviderAuthFlowResponse,
)
def poll_provider_auth_flow(
    provider_id: str,
    flow_id: str,
    manager: SessionManagerDep,
) -> ProviderAuthFlowResponse:
    try:
        payload = manager.poll_provider_auth_flow(provider_id, flow_id)
    except Exception as exc:
        raise config_http_error(exc) from exc
    return model_from_payload(ProviderAuthFlowResponse, payload)


@router.get(
    "/{provider_id}/flows/{flow_id}/callback",
    response_class=HTMLResponse,
    include_in_schema=False,
    name="provider_auth_flow_callback",
)
def provider_auth_flow_callback(
    provider_id: str,
    flow_id: str,
    manager: SessionManagerDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> HTMLResponse:
    try:
        payload = manager.complete_provider_browser_auth_flow(
            provider_id,
            flow_id,
            code=code,
            state=state,
            error=error,
            error_description=error_description,
        )
    except Exception as exc:
        raise config_http_error(exc) from exc
    flow = payload["flow"]
    if flow["status"] == "completed":
        return HTMLResponse(
            (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<title>PBI Agent Authorization Complete</title></head><body>"
                "<h1>Authorization complete</h1>"
                "<p>You can close this window and return to pbi-agent.</p>"
                "<script>setTimeout(() => window.close(), 1500)</script>"
                "</body></html>"
            )
        )
    message = escape(flow.get("error_message") or "Authorization failed.")
    return HTMLResponse(
        (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>PBI Agent Authorization Failed</title></head><body>"
            "<h1>Authorization failed</h1>"
            f"<p>{message}</p>"
            "</body></html>"
        ),
        status_code=400,
    )
