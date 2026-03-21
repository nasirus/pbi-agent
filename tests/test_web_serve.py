from __future__ import annotations

import asyncio

from unittest.mock import Mock

from pbi_agent.branding import PBI_AGENT_NAME, PBI_AGENT_TAGLINE
from pbi_agent.web.serve import _FaviconServer


def test_favicon_server_startup_uses_pbi_agent_banner() -> None:
    server = _FaviconServer(command="uv run pbi-agent web")
    server.console = Mock()

    asyncio.run(server.on_startup(Mock()))

    print_calls = server.console.print.call_args_list
    assert len(print_calls) == 3
    assert PBI_AGENT_NAME in print_calls[0].args[0]
    assert PBI_AGENT_TAGLINE in print_calls[0].args[0]
    assert "textual-serve" not in print_calls[0].args[0]
    assert print_calls[1].args[0] == f"Serving {server.command!r} on {server.public_url}"
    assert print_calls[2].args[0] == "\n[cyan]Press Ctrl+C to quit"
