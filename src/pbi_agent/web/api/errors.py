from __future__ import annotations

from fastapi import HTTPException

from pbi_agent.config import ConfigConflictError


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=409, detail=detail)


def not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=404, detail=detail)


def config_http_error(exc: Exception) -> HTTPException:
    detail = str(exc)
    if isinstance(exc, ConfigConflictError):
        return conflict(detail)
    if (
        detail.startswith("Unknown provider ID")
        or detail.startswith("Unknown profile ID")
        or detail.startswith("Unknown mode ID")
    ):
        return not_found(detail)
    if (
        "already exists" in detail
        or "still references it" in detail
        or detail.startswith("Command alias '")
    ):
        return conflict(detail)
    return bad_request(detail)
