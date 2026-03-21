"""Shared branding helpers for PBI Agent surfaces."""

from __future__ import annotations

PBI_AGENT_ACCENT = "#F2C811"
PBI_AGENT_NAME = "PBI AGENT"
PBI_AGENT_TAGLINE = "Transform data into decisions."
PBI_AGENT_LOGO_ROWS = (
    "              ████",
    "              ████",
    "        ████  ████",
    "        ████  ████",
    "  ████  ████  ████",
    "  ████  ████  ████",
)


def rich_brand_block(*, accent: str = PBI_AGENT_ACCENT) -> str:
    """Return the Rich markup block used for branded startup banners."""

    lines = [f"[bold {accent}]{row}[/bold {accent}]" for row in PBI_AGENT_LOGO_ROWS]
    lines.extend(
        [
            "",
            f"[bold {accent}]{PBI_AGENT_NAME}[/bold {accent}]",
            f"[bold]{PBI_AGENT_TAGLINE}[/bold]",
        ]
    )
    return "\n".join(lines)
