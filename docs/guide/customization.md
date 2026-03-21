---
title: 'Customization'
description: 'Override the agent system prompt and add project-specific rules using INSTRUCTIONS.md and AGENTS.md.'
layout: doc
outline: [2, 3]
---

# Customization

`pbi-agent` supports two workspace-level Markdown files that let you tailor agent behavior without touching any configuration flags or environment variables. Both files are loaded at startup from the current working directory.

## INSTRUCTIONS.md — custom system prompt

By default the agent operates in Power BI mode with a built-in system prompt that encodes PBIP conventions and best practices. Placing an `INSTRUCTIONS.md` file in your workspace root replaces that built-in prompt entirely with your own content.

```text
my-project/
├── INSTRUCTIONS.md   ← replaces the built-in system prompt
├── AGENTS.md         ← optional project rules (appended on top)
└── ...
```

**When `INSTRUCTIONS.md` is present:**

- Its content becomes the agent's system prompt verbatim.
- The Power BI-specific tools `skill_knowledge` and `init_report` are automatically excluded from the tool list, since they are only meaningful in a Power BI context.
- All other tools (`shell`, `python_exec`, `apply_patch`, `read_file`, `search_files`, `list_files`, `read_web_url`, `sub_agent`, `read_image`) remain available.
- `AGENTS.md` project rules are still appended if present (see below).

**Example — Python coding agent:**

```markdown
# INSTRUCTIONS.md
You are a Python expert coding agent. You help users write, review, debug, and refactor Python code.

<coding_rules>
- Follow PEP 8 and PEP 257 conventions.
- Use type hints for all function signatures.
- Prefer `pathlib.Path` over `os.path` for file system operations.
</coding_rules>
```

::: tip
`INSTRUCTIONS.md` is the right place for persona and capability definitions that apply to the whole workspace. Keep it focused — one clear role description with a small set of non-negotiable rules.
:::

::: warning
Removing `INSTRUCTIONS.md` (or leaving it empty) restores the default Power BI mode automatically. No restart is required; the file is re-read at each agent startup.
:::

## AGENTS.md — project rules

`AGENTS.md` adds project-specific rules on top of whatever system prompt is active (the default Power BI prompt, or your custom `INSTRUCTIONS.md`). Use it for conventions, constraints, or context that is specific to the current repository or workspace.

```text
my-project/
├── AGENTS.md   ← injected as <project_rules> in every session
└── ...
```

The file contents are wrapped in `<project_rules>` tags and appended to the system prompt:

```xml
<project_rules>
... your AGENTS.md content ...
</project_rules>
```

**Example — repository conventions:**

```markdown
# AGENTS.md
- All Python files must pass `ruff check` before committing.
- Use `uv run pytest` to execute tests; never use bare `pytest`.
- Keep internal data in `~/.pbi-agent/`, never in the workspace root.
```

::: tip
`AGENTS.md` is checked into version control alongside your project. It is the right place for team conventions that every contributor and every agent session should follow.
:::

## Using both files together

The two files compose cleanly:

| Files present | System prompt |
| --- | --- |
| Neither | Built-in Power BI prompt |
| `AGENTS.md` only | Built-in Power BI prompt + `<project_rules>` |
| `INSTRUCTIONS.md` only | Your custom prompt |
| Both | Your custom prompt + `<project_rules>` |

## File constraints

| Property | Value |
| --- | --- |
| Maximum size | 1 MB (content beyond that is truncated with a warning on stderr) |
| Encoding | UTF-8 (invalid bytes are replaced, not rejected) |
| Empty file | Treated as absent — the default behavior applies |
| Permissions | Unreadable file emits a warning on stderr and is skipped |
