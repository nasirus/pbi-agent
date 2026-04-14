from __future__ import annotations

from pbi_agent.web.app_factory import create_app
from pbi_agent.web.server_runtime import (
    PBIWebServer,
    create_default_fastapi_app as _create_default_fastapi_app,
    default_settings_namespace as _default_settings_namespace,
    main,
    parse_args as _parse_args,
)

__all__ = [
    "PBIWebServer",
    "app",
    "create_app",
    "main",
    "_create_default_fastapi_app",
    "_default_settings_namespace",
    "_parse_args",
]

app = _create_default_fastapi_app()
