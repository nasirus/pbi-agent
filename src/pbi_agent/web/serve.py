from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from rich.console import Console
import uvicorn
import uvicorn.server

from pbi_agent.branding import startup_panel
from pbi_agent.config import Settings
from pbi_agent.web.session_manager import APP_EVENT_STREAM_ID, WebSessionManager

_WEB_DIR = Path(__file__).resolve().parent
_APP_STATIC_DIR = _WEB_DIR / "static" / "app"
_FAVICON_PATH = _WEB_DIR / "static" / "favicon.png"


class CreateChatSessionRequest(BaseModel):
    resume_session_id: str | None = None
    live_session_id: str | None = None


class ChatInputRequest(BaseModel):
    text: str = ""
    image_paths: list[str] = Field(default_factory=list)


class CreateTaskRequest(BaseModel):
    title: str
    prompt: str
    stage: str = "backlog"
    project_dir: str = "."
    session_id: str | None = None


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    prompt: str | None = None
    stage: str | None = None
    position: int | None = None
    project_dir: str | None = None
    session_id: str | None = None
    clear_session_id: bool = False


def create_app(
    settings: Settings,
    *,
    debug: bool = False,
    title: str | None = None,
    public_url: str | None = None,
) -> FastAPI:
    manager = WebSessionManager(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        except asyncio.CancelledError:
            pass
        finally:
            manager.shutdown()

    app = FastAPI(
        title=title or "PBI Agent",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.manager = manager
    app.state.public_url = public_url
    app.state.debug = debug

    if debug:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://127.0.0.1:5173",
                "http://localhost:5173",
                "http://127.0.0.1:4173",
                "http://localhost:4173",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    assets_dir = _APP_STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/favicon.ico")
    async def favicon() -> FileResponse:
        return FileResponse(_FAVICON_PATH, media_type="image/png")

    @app.get("/logo.png")
    async def logo() -> FileResponse:
        return FileResponse(_FAVICON_PATH, media_type="image/png")

    @app.get("/api/bootstrap")
    async def bootstrap() -> dict[str, Any]:
        return manager.bootstrap()

    @app.get("/api/sessions")
    async def list_sessions(limit: int = 30) -> dict[str, Any]:
        return {"sessions": manager.list_sessions(limit=limit)}

    @app.post("/api/chat/session")
    async def create_chat_session(
        request: CreateChatSessionRequest,
    ) -> dict[str, Any]:
        try:
            session = manager.create_live_chat(
                resume_session_id=request.resume_session_id,
                live_session_id=request.live_session_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"session": session}

    @app.post("/api/chat/session/{live_session_id}/input")
    async def submit_chat_input(
        live_session_id: str,
        request: ChatInputRequest,
    ) -> dict[str, Any]:
        try:
            session = manager.submit_chat_input(
                live_session_id,
                text=request.text,
                image_paths=request.image_paths,
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=404, detail="Live session not found."
            ) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"session": session}

    @app.post("/api/chat/session/{live_session_id}/new-chat")
    async def request_new_chat(live_session_id: str) -> dict[str, Any]:
        try:
            session = manager.request_new_chat(live_session_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=404, detail="Live session not found."
            ) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"session": session}

    @app.get("/api/tasks")
    async def list_tasks() -> dict[str, Any]:
        return {"tasks": manager.list_tasks()}

    @app.post("/api/tasks")
    async def create_task(request: CreateTaskRequest) -> dict[str, Any]:
        try:
            task = manager.create_task(
                title=request.title,
                prompt=request.prompt,
                stage=request.stage,
                project_dir=request.project_dir,
                session_id=request.session_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"task": task}

    @app.patch("/api/tasks/{task_id}")
    async def update_task(task_id: str, request: UpdateTaskRequest) -> dict[str, Any]:
        try:
            task = manager.update_task(
                task_id,
                title=request.title,
                prompt=request.prompt,
                stage=request.stage,
                position=request.position,
                project_dir=request.project_dir,
                session_id=request.session_id,
                clear_session_id=request.clear_session_id,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Task not found.") from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"task": task}

    @app.delete("/api/tasks/{task_id}", status_code=204)
    async def delete_task(task_id: str) -> Response:
        try:
            manager.delete_task(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Task not found.") from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return Response(status_code=204)

    @app.post("/api/tasks/{task_id}/run")
    async def run_task(task_id: str) -> dict[str, Any]:
        try:
            task = manager.run_task(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Task not found.") from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"task": task}

    @app.websocket("/api/events/{stream_id}")
    async def stream_events(websocket: WebSocket, stream_id: str) -> None:
        try:
            stream = manager.get_event_stream(stream_id)
        except KeyError:
            await websocket.close(code=4404)
            return

        await websocket.accept()
        for event in stream.snapshot():
            await websocket.send_json(event)
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

    @app.get("/", response_class=HTMLResponse)
    async def index() -> Response:
        return _spa_index_response(title or "PBI Agent")

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def spa_fallback(full_path: str) -> Response:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found.")
        if full_path == APP_EVENT_STREAM_ID:
            raise HTTPException(status_code=404, detail="Not found.")
        return _spa_index_response(title or "PBI Agent")

    return app


def _spa_index_response(title: str) -> Response:
    index_path = _APP_STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse(
        (
            "<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{title}</title>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>body{font-family:system-ui,sans-serif;background:#0b1020;"
            "color:#eef2ff;padding:40px}code{background:#111827;padding:2px 6px;"
            "border-radius:6px}</style></head><body>"
            "<h1>PBI Agent Web UI assets are missing.</h1>"
            "<p>Run <code>npm install</code> then <code>npm run web:build</code> "
            "to build the bundled frontend.</p></body></html>"
        )
    )


class PBIWebServer:
    def __init__(
        self,
        *,
        settings: Settings,
        host: str = "127.0.0.1",
        port: int = 8000,
        title: str | None = None,
        public_url: str | None = None,
    ) -> None:
        self._settings = settings
        self.host = host
        self.port = port
        self.title = title
        self.public_url = public_url
        self.console = Console(highlight=False)

    def serve(self, debug: bool = False) -> None:
        app = create_app(
            self._settings,
            debug=debug,
            title=self.title,
            public_url=self.public_url,
        )
        target = self.public_url or f"http://{self.host}:{self.port}"
        self.console.print(startup_panel(), highlight=False)
        self.console.print(f"  Serving on [bold]{target}[/bold]")
        self.console.print("[cyan]  Press Ctrl+C to quit[/cyan]")
        server = _GracefulUvicornServer(
            uvicorn.Config(
                app=app,
                host=self.host,
                port=self.port,
                log_level="info" if debug else "warning",
            )
        )
        try:
            server.run()
        except KeyboardInterrupt:
            return


class _GracefulUvicornServer(uvicorn.Server):
    @contextlib.contextmanager
    def capture_signals(self):
        if threading.current_thread() is not threading.main_thread():
            yield
            return

        handled_signals = getattr(
            uvicorn.server,
            "HANDLED_SIGNALS",
            (signal.SIGINT, signal.SIGTERM),
        )
        original_handlers = {
            sig: signal.signal(sig, self.handle_exit) for sig in handled_signals
        }
        try:
            yield
        finally:
            for sig, handler in original_handlers.items():
                signal.signal(sig, handler)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="pbi-agent web server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--title", default=None)
    parser.add_argument("--url", default=None, dest="public_url")
    parser.add_argument("--dev", action="store_true", default=False)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--sub-agent-model", default="gpt-5.4-mini")
    parser.add_argument(
        "--responses-url", default="https://api.openai.com/v1/responses"
    )
    parser.add_argument(
        "--generic-api-url", default="https://openrouter.ai/api/v1/chat/completions"
    )
    parser.add_argument("--reasoning-effort", default="xhigh")
    parser.add_argument("--max-tool-workers", type=int, default=4)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--compact-threshold", type=int, default=150000)
    parser.add_argument("--max-tokens", type=int, default=16384)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--service-tier", default=None)
    parser.add_argument("--no-web-search", action="store_true", default=False)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    settings = Settings(
        api_key=args.api_key,
        provider=args.provider,
        model=args.model,
        sub_agent_model=args.sub_agent_model,
        responses_url=args.responses_url,
        generic_api_url=args.generic_api_url,
        reasoning_effort=args.reasoning_effort,
        max_tool_workers=args.max_tool_workers,
        max_retries=args.max_retries,
        compact_threshold=args.compact_threshold,
        max_tokens=args.max_tokens,
        verbose=args.verbose,
        service_tier=args.service_tier,
        web_search=not args.no_web_search,
    )
    PBIWebServer(
        settings=settings,
        host=args.host,
        port=args.port,
        title=args.title,
        public_url=args.public_url,
    ).serve(debug=args.dev)


if __name__ == "__main__":
    main()
