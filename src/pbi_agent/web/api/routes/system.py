from __future__ import annotations

from fastapi import APIRouter, Response

from pbi_agent.web.api.deps import (
    LimitQuery,
    MentionLimitQuery,
    MentionQuery,
    SessionIdPath,
    SessionManagerDep,
    model_from_payload,
)
from pbi_agent.web.api.errors import bad_request, not_found
from pbi_agent.web.api.schemas.system import (
    BootstrapResponse,
    FileMentionItemModel,
    FileMentionSearchResponse,
    HistoryItemModel,
    LiveSessionDetailResponse,
    LiveSessionModel,
    LiveSessionSnapshotModel,
    LiveSessionsResponse,
    SessionDetailResponse,
    SessionRecordModel,
    SessionsResponse,
    SlashCommandItemModel,
    SlashCommandSearchResponse,
)

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/bootstrap", response_model=BootstrapResponse)
def bootstrap(manager: SessionManagerDep) -> BootstrapResponse:
    return model_from_payload(BootstrapResponse, manager.bootstrap())


@router.get("/sessions", response_model=SessionsResponse)
def list_sessions(
    manager: SessionManagerDep,
    limit: LimitQuery = 30,
) -> SessionsResponse:
    return SessionsResponse(
        sessions=[
            model_from_payload(SessionRecordModel, item)
            for item in manager.list_sessions(limit=limit)
        ]
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(
    session_id: SessionIdPath,
    manager: SessionManagerDep,
) -> SessionDetailResponse:
    try:
        payload = manager.get_session_detail(session_id)
    except KeyError as exc:
        raise not_found("Session not found.") from exc
    return SessionDetailResponse(
        session=model_from_payload(SessionRecordModel, payload["session"]),
        history_items=[
            model_from_payload(HistoryItemModel, item)
            for item in payload["history_items"]
        ],
        live_session=(
            model_from_payload(LiveSessionModel, payload["live_session"])
            if payload["live_session"] is not None
            else None
        ),
        active_live_session=(
            model_from_payload(LiveSessionModel, payload["active_live_session"])
            if payload["active_live_session"] is not None
            else None
        ),
    )


@router.get("/live-sessions", response_model=LiveSessionsResponse)
def list_live_sessions(manager: SessionManagerDep) -> LiveSessionsResponse:
    return LiveSessionsResponse(
        live_sessions=[
            model_from_payload(LiveSessionModel, item)
            for item in manager.list_live_sessions()
        ]
    )


@router.get(
    "/live-sessions/{live_session_id}",
    response_model=LiveSessionDetailResponse,
)
def get_live_session_detail(
    live_session_id: str,
    manager: SessionManagerDep,
) -> LiveSessionDetailResponse:
    try:
        payload = manager.get_live_session_detail(live_session_id)
    except KeyError as exc:
        raise not_found("Live session not found.") from exc
    return LiveSessionDetailResponse(
        live_session=model_from_payload(LiveSessionModel, payload["live_session"]),
        snapshot=model_from_payload(LiveSessionSnapshotModel, payload["snapshot"]),
    )


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: SessionIdPath,
    manager: SessionManagerDep,
) -> Response:
    try:
        manager.delete_session(session_id)
    except KeyError as exc:
        raise not_found("Session not found.") from exc
    except Exception as exc:
        raise bad_request(str(exc)) from exc
    return Response(status_code=204)


@router.get("/files/search", response_model=FileMentionSearchResponse)
def search_workspace_files(
    manager: SessionManagerDep,
    q: MentionQuery = "",
    limit: MentionLimitQuery = 8,
) -> FileMentionSearchResponse:
    return FileMentionSearchResponse(
        items=[
            FileMentionItemModel(path=item.path, kind=item.kind)
            for item in manager.search_file_mentions(
                q,
                limit=limit,
            )
        ]
    )


@router.get("/slash-commands/search", response_model=SlashCommandSearchResponse)
def search_available_slash_commands(
    manager: SessionManagerDep,
    q: MentionQuery = "",
    limit: MentionLimitQuery = 8,
) -> SlashCommandSearchResponse:
    return SlashCommandSearchResponse(
        items=[
            model_from_payload(SlashCommandItemModel, item)
            for item in manager.search_slash_commands(q, limit=limit)
        ]
    )
