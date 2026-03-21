from __future__ import annotations

import sys
from pathlib import Path

SYSTEM_PROMPT = """
You are pbi-agent, a local CLI agent for creating, auditing, and editing Power BI PBIP projects.

<power_bi_rules>
- Use explicit measures in visuals; never rely on implicit aggregations.
- Dedicated measures table must be named `_Measures`, never `Measures`.
- Never modify auto-generated date tables (`DateTableTemplate_*`, `LocalDateTable_*`); skip their descriptions — their TMDL schema is restricted.
- Distribute visuals intentionally across the canvas unless the user specifies a layout.
- Style priority: explicit user instruction > existing project/brand conventions > skill default preset.
</power_bi_rules>
""".strip()

_SUB_AGENT_PROMPT = """
<persona>
- You are a delegated sub-agent operating on behalf of the main agent.
- You are in background mode and will not interact with the user directly. Do not ask the user questions.
</persona>
""".strip()

SUB_AGENT_SYSTEM_PROMPT = f"{SYSTEM_PROMPT}\n\n{_SUB_AGENT_PROMPT}"

_MAX_PROJECT_RULES_BYTES = 1_000_000  # 1 MB


def _warn_project_rules(message: str) -> None:
    print(message, file=sys.stderr)


def load_project_rules(cwd: Path | None = None) -> str | None:
    """Read an optional ``AGENTS.md`` file from *cwd* (default: CWD).

    Returns the file content, or ``None`` when the file is absent, empty,
    or unreadable.
    """
    target = (cwd or Path.cwd()) / "AGENTS.md"

    try:
        size = target.stat().st_size
    except FileNotFoundError:
        return None
    except OSError:
        _warn_project_rules("AGENTS.md found but unreadable due to permissions.")
        return None

    if size > _MAX_PROJECT_RULES_BYTES:
        _warn_project_rules("AGENTS.md exceeds 1 MB; content will be truncated.")

    try:
        with target.open("rb") as fh:
            raw_content = fh.read(_MAX_PROJECT_RULES_BYTES)
    except OSError:
        _warn_project_rules("AGENTS.md found but unreadable due to permissions.")
        return None

    content = raw_content.decode("utf-8", errors="replace").strip()
    if not content:
        return None

    return content


def _append_project_rules(base_prompt: str) -> str:
    """Append ``<project_rules>`` section if ``AGENTS.md`` is present."""
    rules = load_project_rules()
    if rules is None:
        return base_prompt
    return f"{base_prompt}\n\n<project_rules>\n{rules}\n</project_rules>"


def get_system_prompt() -> str:
    return _append_project_rules(SYSTEM_PROMPT)


def get_sub_agent_system_prompt() -> str:
    return _append_project_rules(SUB_AGENT_SYSTEM_PROMPT)
