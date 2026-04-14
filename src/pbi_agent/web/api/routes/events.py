from __future__ import annotations

import asyncio
from typing import cast

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pbi_agent.web.api.deps import StreamIdPath
from pbi_agent.web.session_manager import WebSessionManager

router = APIRouter(prefix="/api/events", tags=["events"])


@router.websocket("/{stream_id}")
async def stream_events(websocket: WebSocket, stream_id: StreamIdPath) -> None:
    manager = cast(WebSessionManager, websocket.app.state.manager)
    try:
        stream = manager.get_event_stream(stream_id)
    except KeyError:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    try:
        for event in stream.snapshot():
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    except asyncio.CancelledError:
        return
    subscriber_id, queue = stream.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    except asyncio.CancelledError:
        return
    finally:
        stream.unsubscribe(subscriber_id)
