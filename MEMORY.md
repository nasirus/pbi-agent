# Memory

## Metadata

- Purpose: durable repo memory plus compact append-only task notes for the current day.
- Format: keep exactly three top-level sections: Metadata, Long-Term Memory, and Detailed Task Events.
- Last compacted: 2026-04-20.
- Current note: TODO.md is the session checklist and should be reset for each substantive task.

## Long-Term Memory

- Repo workflow: MEMORY.md holds durable repo memory and compact task history; TODO.md is the current-task checklist and uses [ ], [>], [X], [!], and [-] markers.
- Architecture: CLI entry is src/pbi_agent/__main__.py -> src/pbi_agent/cli.py; web backend lives under src/pbi_agent/web/ with routes in web/api/routes, orchestration in web/session_manager.py, event/display publishing in web/display.py, and Uvicorn startup helpers in web/server_runtime.py.
- Frontend: the Vite + React + TypeScript app lives in webapp/; bun run web:build writes the served bundle to src/pbi_agent/web/static/app.
- Web contracts: when changing web API shapes, keep backend routes, schemas, and session manager aligned with webapp/src/api.ts and webapp/src/types.ts.
- Display/testing: src/pbi_agent/display/protocol.py defines DisplayProtocol; console output lives in src/pbi_agent/display/console_display.py; tests commonly use tests/conftest.py::DisplaySpy.
- Providers: outbound provider and tool HTTP must use urllib.request.
- Provider/auth product model: openai is API-key-only, chatgpt is account-auth-only, and github_copilot is account-auth-only.
- ChatGPT transport: ChatGPT/Codex-specific Responses logic lives in src/pbi_agent/providers/chatgpt_codex_backend.py; it replays local transcripts instead of relying on backend previous_response_id chaining.
- Model discovery: runtime provider model discovery lives in src/pbi_agent/providers/model_discovery.py; the web API exposes /api/config/providers/{provider_id}/models; the settings UI falls back to manual entry when discovery is unsupported or fails.
- ChatGPT discovery: use the Codex backend models endpoint with a minimum client_version of 0.99.0; visible live models included gpt-5.4, gpt-5.4-mini, gpt-5.3-codex, and gpt-5.2 during the last probe.
- GitHub Copilot: backend model listing is available at GET https://api.githubcopilot.com/models; current visible models observed included gpt-5.4, gpt-5-mini, gpt-5.3-codex, gpt-5.2-codex, claude-sonnet-4, and gemini-2.5-pro, so the default Copilot model was updated to gpt-5.4.
- Auth flows: provider auth storage/services live under src/pbi_agent/auth/; CLI and web provider-auth flows support browser/device login, and web browser auth now uses a dedicated localhost callback listener pattern shared with the CLI.
- Web UX: creating a subscription-backed provider in settings should open auth immediately; onboarding dismissal on /settings should stay suppressed for the current setup session; auth completion should leave the modal dismissible even while background refresh is still pending.
- Docs/build validation: Python changes usually validate with Ruff plus focused pytest; frontend changes validate with bun run test:web, bun run typecheck, and bun run web:build; bun run lint has intermittently hung in this environment.
- Known repo state: a previous full uv run pytest had unrelated failures in tests/test_internal_config.py and tests/test_xai_provider.py around runtime/default resolution.

## Detailed Task Events

## 2026-04-20

- Updated MEMORY.md to the AGENTS.md three-section structure, compacting the prior flat chronological log into durable repo facts plus a new dated task-events section.
- Validation: manual structure check against AGENTS.md requirements; the file now contains only Metadata, Long-Term Memory, and Detailed Task Events as top-level sections.
- Next context: append future task notes under the current date until the next day-level compaction.
