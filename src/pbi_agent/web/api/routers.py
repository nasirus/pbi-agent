from __future__ import annotations

from .routes.board import router as board_router
from .routes.chat import router as chat_router
from .routes.config import router as config_router
from .routes.events import router as events_router
from .routes.system import router as system_router
from .routes.tasks import router as tasks_router

__all__ = [
    "board_router",
    "chat_router",
    "config_router",
    "events_router",
    "system_router",
    "tasks_router",
]
