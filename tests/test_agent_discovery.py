"""Tests for agent discovery from ``.agents/agents/``."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pbi_agent.agent.agent_discovery import (
    discover_project_agents,
    format_project_agents_markdown,
    get_agent_by_name,
)


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    agents_dir = tmp_path / ".agents" / "agents"
    agents_dir.mkdir(parents=True)
    return tmp_path


def _write_agent(workspace: Path, filename: str, content: str) -> Path:
    path = workspace / ".agents" / "agents" / filename
    path.write_text(dedent(content), encoding="utf-8")
    return path


class TestDiscoverProjectAgents:
    def test_empty_directory(self, workspace: Path) -> None:
        assert discover_project_agents(workspace) == []

    def test_no_agents_directory(self, tmp_path: Path) -> None:
        assert discover_project_agents(tmp_path) == []

    def test_discovers_valid_agent(self, workspace: Path) -> None:
        _write_agent(
            workspace,
            "reviewer.md",
            """\
            ---
            name: reviewer
            description: Reviews code quality
            ---

            You are a code reviewer. Analyze code for quality.
            """,
        )

        agents = discover_project_agents(workspace)
        assert len(agents) == 1
        assert agents[0].name == "reviewer"
        assert agents[0].description == "Reviews code quality"
        assert "code reviewer" in agents[0].system_prompt

    def test_discovers_agent_with_all_fields(self, workspace: Path) -> None:
        _write_agent(
            workspace,
            "debugger.md",
            """\
            ---
            name: debugger
            description: Debugging specialist
            model: gpt-5-mini
            tools: shell, read_file, search_files
            disallowedTools: apply_patch
            maxTurns: 15
            ---

            You are an expert debugger.
            """,
        )

        agents = discover_project_agents(workspace)
        assert len(agents) == 1
        agent = agents[0]
        assert agent.name == "debugger"
        assert agent.model == "gpt-5-mini"
        assert agent.tools == ["shell", "read_file", "search_files"]
        assert agent.disallowed_tools == ["apply_patch"]
        assert agent.max_turns == 15

    def test_skips_non_md_files(self, workspace: Path) -> None:
        (workspace / ".agents" / "agents" / "notes.txt").write_text("not an agent")
        assert discover_project_agents(workspace) == []

    def test_skips_missing_frontmatter(self, workspace: Path) -> None:
        _write_agent(workspace, "bad.md", "No frontmatter here.\n")
        assert discover_project_agents(workspace) == []

    def test_skips_missing_name(self, workspace: Path) -> None:
        _write_agent(
            workspace,
            "no-name.md",
            """\
            ---
            description: Missing name field
            ---

            Body text.
            """,
        )
        assert discover_project_agents(workspace) == []

    def test_skips_missing_description(self, workspace: Path) -> None:
        _write_agent(
            workspace,
            "no-desc.md",
            """\
            ---
            name: incomplete
            ---

            Body text.
            """,
        )
        assert discover_project_agents(workspace) == []

    def test_invalid_max_turns_ignored(self, workspace: Path) -> None:
        _write_agent(
            workspace,
            "agent.md",
            """\
            ---
            name: test-agent
            description: A test agent
            maxTurns: not-a-number
            ---

            Body.
            """,
        )
        agents = discover_project_agents(workspace)
        assert len(agents) == 1
        assert agents[0].max_turns is None

    def test_sorted_by_name(self, workspace: Path) -> None:
        for name in ("zebra", "alpha", "mid"):
            _write_agent(
                workspace,
                f"{name}.md",
                f"""\
                ---
                name: {name}
                description: Agent {name}
                ---

                Body for {name}.
                """,
            )

        agents = discover_project_agents(workspace)
        names = [a.name for a in agents]
        assert names == ["alpha", "mid", "zebra"]


class TestGetAgentByName:
    def test_found(self, workspace: Path) -> None:
        _write_agent(
            workspace,
            "reviewer.md",
            """\
            ---
            name: reviewer
            description: Reviews code
            ---

            Review prompt.
            """,
        )
        agent = get_agent_by_name("reviewer", workspace)
        assert agent is not None
        assert agent.name == "reviewer"

    def test_not_found(self, workspace: Path) -> None:
        assert get_agent_by_name("nonexistent", workspace) is None


class TestFormatProjectAgentsMarkdown:
    def test_no_agents(self, tmp_path: Path) -> None:
        result = format_project_agents_markdown(tmp_path)
        assert "No project agents" in result

    def test_with_agents(self, workspace: Path) -> None:
        _write_agent(
            workspace,
            "reviewer.md",
            """\
            ---
            name: reviewer
            description: Reviews code quality
            ---

            Prompt.
            """,
        )
        result = format_project_agents_markdown(workspace)
        assert "`reviewer`" in result
        assert "Reviews code quality" in result
