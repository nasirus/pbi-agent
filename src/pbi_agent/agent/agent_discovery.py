"""Discover project agent definitions from ``.agents/agents/``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
import re

_DISCOVERY_ROOT = Path(".agents/agents")


@dataclass(slots=True, frozen=True)
class AgentDefinition:
    """A project-level agent definition loaded from a Markdown file."""

    name: str
    description: str
    system_prompt: str
    location: Path
    # Optional overrides
    model: str | None = None
    tools: list[str] | None = None
    disallowed_tools: list[str] | None = None
    max_turns: int | None = None


def format_project_agents_markdown(workspace: Path | None = None) -> str:
    agents = discover_project_agents(workspace)
    if not agents:
        return (
            "### Project Agents\n\n"
            "No project agents discovered under `.agents/agents/`."
        )

    lines = ["### Project Agents", ""]
    for agent in agents:
        lines.append(f"- `{agent.name}`: {agent.description}")
    return "\n".join(lines)


def _warn(message: str) -> None:
    print(message, file=sys.stderr)


def discover_project_agents(workspace: Path | None = None) -> list[AgentDefinition]:
    root = (workspace or Path.cwd()).resolve()
    agents_root = root / _DISCOVERY_ROOT
    if not agents_root.is_dir():
        return []

    discovered: list[AgentDefinition] = []
    for agent_file in sorted(
        agents_root.iterdir(), key=lambda item: item.name.casefold()
    ):
        if not agent_file.is_file() or agent_file.suffix != ".md":
            continue

        agent = _load_agent_definition(agent_file)
        if agent is not None:
            discovered.append(agent)

    return discovered


def get_agent_by_name(
    name: str, workspace: Path | None = None
) -> AgentDefinition | None:
    """Return the agent definition matching *name*, or ``None``."""
    for agent in discover_project_agents(workspace):
        if agent.name == name:
            return agent
    return None


def _load_agent_definition(agent_file: Path) -> AgentDefinition | None:
    try:
        content = agent_file.read_text(encoding="utf-8")
    except OSError:
        _warn(f"Skipping agent at {agent_file}: file is unreadable.")
        return None

    frontmatter = _extract_frontmatter(content, agent_file)
    if frontmatter is None:
        return None

    metadata = _parse_frontmatter(frontmatter, agent_file)
    if metadata is None:
        return None

    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not name.strip():
        _warn(f"Skipping agent at {agent_file}: missing non-empty 'name'.")
        return None
    if not isinstance(description, str) or not description.strip():
        _warn(f"Skipping agent at {agent_file}: missing non-empty 'description'.")
        return None

    # Extract system prompt (everything after the frontmatter closing ---)
    system_prompt = _extract_body(content).strip()

    # Parse optional fields
    model = metadata.get("model")
    if model is not None:
        model = model.strip() or None

    tools = _parse_comma_list(metadata.get("tools"))
    disallowed_tools = _parse_comma_list(metadata.get("disallowedTools"))

    max_turns: int | None = None
    raw_max_turns = metadata.get("maxTurns")
    if raw_max_turns is not None:
        try:
            max_turns = int(raw_max_turns)
            if max_turns < 1:
                _warn(f"Agent '{name.strip()}': maxTurns must be >= 1; ignoring.")
                max_turns = None
        except ValueError:
            _warn(f"Agent '{name.strip()}': maxTurns is not a valid integer; ignoring.")

    return AgentDefinition(
        name=name.strip(),
        description=description.strip(),
        system_prompt=system_prompt,
        location=agent_file.resolve(),
        model=model,
        tools=tools,
        disallowed_tools=disallowed_tools,
        max_turns=max_turns,
    )


def _parse_comma_list(value: str | None) -> list[str] | None:
    """Parse a comma-separated string into a list of stripped, non-empty items."""
    if value is None:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items if items else None


def _extract_body(content: str) -> str:
    """Return the Markdown body after the YAML frontmatter."""
    match = re.match(
        r"\A---\s*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)",
        content,
        re.DOTALL,
    )
    if match is None:
        return content
    return content[match.end() :]


def _extract_frontmatter(content: str, agent_file: Path) -> str | None:
    match = re.match(
        r"\A---\s*\r?\n(.*?)\r?\n---(?:\s*\r?\n|\s*\Z)",
        content,
        re.DOTALL,
    )
    if match is None:
        _warn(f"Skipping agent at {agent_file}: missing YAML frontmatter.")
        return None
    return match.group(1)


def _parse_frontmatter(frontmatter: str, agent_file: Path) -> dict[str, str] | None:
    """Parse simple ``key: value`` frontmatter without external dependencies."""
    result: dict[str, str] = {}
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        colon_idx = stripped.find(":")
        if colon_idx < 0:
            _warn(
                f"Skipping agent at {agent_file}: "
                f"frontmatter line is not a key-value pair: {stripped!r}."
            )
            return None
        key = stripped[:colon_idx].strip()
        value = stripped[colon_idx + 1 :].strip()
        if not key:
            _warn(f"Skipping agent at {agent_file}: frontmatter contains an empty key.")
            return None
        result[key] = value
    if not result:
        _warn(f"Skipping agent at {agent_file}: frontmatter is empty.")
        return None
    return result
