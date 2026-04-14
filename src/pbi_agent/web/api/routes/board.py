from __future__ import annotations

from fastapi import APIRouter

from pbi_agent.config import ConfigError
from pbi_agent.web.api.deps import SessionManagerDep, model_from_payload
from pbi_agent.web.api.errors import bad_request, config_http_error
from pbi_agent.web.api.schemas.tasks import (
    BoardStageModel,
    BoardStagesResponse,
    UpdateBoardStagesRequest,
)

router = APIRouter(prefix="/api/board", tags=["board"])


@router.get("/stages", response_model=BoardStagesResponse)
def list_board_stages(manager: SessionManagerDep) -> BoardStagesResponse:
    return BoardStagesResponse(
        board_stages=[
            model_from_payload(BoardStageModel, item)
            for item in manager.list_board_stages()
        ]
    )


@router.put("/stages", response_model=BoardStagesResponse)
def update_board_stages(
    request: UpdateBoardStagesRequest,
    manager: SessionManagerDep,
) -> BoardStagesResponse:
    try:
        stages = manager.replace_board_stages(
            stages=[item.model_dump() for item in request.board_stages],
        )
    except ConfigError as exc:
        raise config_http_error(exc) from exc
    except Exception as exc:
        raise bad_request(str(exc)) from exc
    return BoardStagesResponse(
        board_stages=[model_from_payload(BoardStageModel, item) for item in stages]
    )
