from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, cast
from urllib.parse import parse_qs, urlparse

from pbi_agent.auth.models import (
    BrowserAuthChallenge,
    DeviceAuthChallenge,
    StoredAuthSession,
)
from pbi_agent.auth.service import (
    complete_provider_browser_auth,
    poll_provider_device_auth,
    start_provider_browser_auth,
    start_provider_device_auth,
)

_BROWSER_CALLBACK_PATH = "/auth/callback"
_BROWSER_AUTH_TIMEOUT_SECS = 5 * 60
_DEVICE_AUTH_TIMEOUT_SECS = 15 * 60
_DEFAULT_CALLBACK_PORT = 1455
_CALLBACK_SERVER_HOST = "127.0.0.1"
_SUCCESS_HTML = """<!doctype html>
<html>
  <head><meta charset="utf-8"><title>PBI Agent Authorization Complete</title></head>
  <body>
    <h1>Authorization complete</h1>
    <p>You can close this window and return to pbi-agent.</p>
    <script>setTimeout(() => window.close(), 1500)</script>
  </body>
</html>
"""
_ERROR_HTML = """<!doctype html>
<html>
  <head><meta charset="utf-8"><title>PBI Agent Authorization Failed</title></head>
  <body>
    <h1>Authorization failed</h1>
    <p>{message}</p>
  </body>
</html>
"""


@dataclass(slots=True)
class BrowserAuthFlowResult:
    session: StoredAuthSession
    browser_auth: BrowserAuthChallenge
    opened_browser: bool


@dataclass(slots=True)
class DeviceAuthFlowResult:
    session: StoredAuthSession
    device_auth: DeviceAuthChallenge


class _BrowserCallbackServer(ThreadingHTTPServer):
    def __init__(
        self,
        *,
        provider_kind: str,
        provider_id: str,
        auth_mode: str,
        port: int,
    ) -> None:
        super().__init__((_CALLBACK_SERVER_HOST, port), _BrowserCallbackHandler)
        self.provider_kind = provider_kind
        self.provider_id = provider_id
        self.auth_mode = auth_mode
        self.browser_auth: BrowserAuthChallenge | None = None
        self.result_queue: queue.Queue[StoredAuthSession | Exception] = queue.Queue()
        self.callback_path = _BROWSER_CALLBACK_PATH


class _BrowserCallbackHandler(BaseHTTPRequestHandler):
    server: _BrowserCallbackServer

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != self.server.callback_path:
            self._send_html(404, _ERROR_HTML.format(message="Unknown callback path."))
            return

        if self.server.browser_auth is None:
            self._send_result(
                RuntimeError("Browser authorization was not initialized correctly."),
            )
            return

        params = parse_qs(parsed.query)
        error = _first_query_value(params, "error")
        error_description = _first_query_value(params, "error_description")
        if error:
            self._send_result(RuntimeError(error_description or error))
            return

        state = _first_query_value(params, "state")
        if state != self.server.browser_auth.state:
            self._send_result(RuntimeError("Invalid authorization state in callback."))
            return

        code = _first_query_value(params, "code")
        if not code:
            self._send_result(RuntimeError("Missing authorization code in callback."))
            return

        try:
            session = complete_provider_browser_auth(
                provider_kind=self.server.provider_kind,
                provider_id=self.server.provider_id,
                auth_mode=self.server.auth_mode,
                browser_auth=self.server.browser_auth,
                code=code,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests
            self._send_result(exc)
            return

        self.server.result_queue.put(session)
        self._send_html(200, _SUCCESS_HTML)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        del format, args

    def _send_result(self, error: Exception) -> None:
        self.server.result_queue.put(error)
        self._send_html(400, _ERROR_HTML.format(message=str(error)))

    def _send_html(self, status_code: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run_provider_browser_auth_flow(
    *,
    provider_kind: str,
    provider_id: str,
    auth_mode: str,
    open_browser: Callable[[str], bool],
    on_ready: Callable[[BrowserAuthChallenge], None] | None = None,
) -> BrowserAuthFlowResult:
    server = _create_browser_callback_server(
        provider_kind=provider_kind,
        provider_id=provider_id,
        auth_mode=auth_mode,
    )
    callback_url = _browser_callback_url(server)
    thread: threading.Thread | None = None
    try:
        server.browser_auth = start_provider_browser_auth(
            provider_kind=provider_kind,
            provider_id=provider_id,
            auth_mode=auth_mode,
            redirect_uri=callback_url,
        )
        if on_ready is not None:
            on_ready(server.browser_auth)
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.1},
            name="pbi-agent-auth-browser-callback",
            daemon=True,
        )
        thread.start()
        opened_browser = bool(open_browser(server.browser_auth.authorization_url))
        try:
            result = server.result_queue.get(timeout=_BROWSER_AUTH_TIMEOUT_SECS)
        except queue.Empty as exc:
            raise RuntimeError(
                "Timed out waiting for the browser authorization callback."
            ) from exc
        if isinstance(result, Exception):
            raise result
        return BrowserAuthFlowResult(
            session=result,
            browser_auth=server.browser_auth,
            opened_browser=opened_browser,
        )
    finally:
        if thread is not None:
            server.shutdown()
        server.server_close()
        if thread is not None:
            thread.join(timeout=1.0)


def run_provider_device_auth_flow(
    *,
    provider_kind: str,
    provider_id: str,
    auth_mode: str,
    timeout_seconds: int = _DEVICE_AUTH_TIMEOUT_SECS,
    on_start: Callable[[DeviceAuthChallenge], None] | None = None,
) -> DeviceAuthFlowResult:
    device_auth = start_provider_device_auth(
        provider_kind=provider_kind,
        provider_id=provider_id,
        auth_mode=auth_mode,
    )
    if on_start is not None:
        on_start(device_auth)
    deadline = time.monotonic() + timeout_seconds
    while True:
        result = poll_provider_device_auth(
            provider_kind=provider_kind,
            provider_id=provider_id,
            auth_mode=auth_mode,
            device_auth=device_auth,
        )
        if result.session is not None:
            return DeviceAuthFlowResult(session=result.session, device_auth=device_auth)
        if time.monotonic() >= deadline:
            raise RuntimeError("Timed out waiting for device authorization.")
        sleep_for = result.retry_after_seconds or device_auth.interval_seconds
        time.sleep(max(sleep_for, 1))


def _create_browser_callback_server(
    *,
    provider_kind: str,
    provider_id: str,
    auth_mode: str,
) -> _BrowserCallbackServer:
    try:
        return _BrowserCallbackServer(
            provider_kind=provider_kind,
            provider_id=provider_id,
            auth_mode=auth_mode,
            port=_DEFAULT_CALLBACK_PORT,
        )
    except OSError:
        return _BrowserCallbackServer(
            provider_kind=provider_kind,
            provider_id=provider_id,
            auth_mode=auth_mode,
            port=0,
        )


def _browser_callback_url(server: _BrowserCallbackServer) -> str:
    host, port = cast(tuple[str, int], server.server_address)
    del host
    return f"http://localhost:{port}{server.callback_path}"


def _first_query_value(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    value = values[0].strip()
    return value or None
