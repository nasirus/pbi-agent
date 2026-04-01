---
title: 'Providers'
description: 'Provider selection, key resolution, endpoint overrides, history mode, and examples for every supported backend.'
---

# Provider Configuration

Saved configuration is split into two entities:

- Provider: connection-only settings such as provider kind, API key, and endpoint overrides.
- Model Profile: runnable model/runtime settings tied to one saved Provider.

Runtime resolution now happens in two phases:

1. Select a base model profile from `--model-profile`, then `PBI_AGENT_MODEL_PROFILE`, then the saved `active_model_profile`.
2. Compile that profile and its provider into runtime `Settings`, then overlay explicit CLI and environment overrides.

If no saved profile is selected, runtime settings fall back directly to CLI flags, environment variables, and provider defaults. The old provider-scoped saved runtime snapshot is no longer used, and runtime commands do not rewrite saved config.

API key precedence remains: `--api-key`, then `PBI_AGENT_API_KEY`, then the provider-specific fallback env var, then the saved Provider API key.

`sub_agent` uses the same provider as the parent session. Its sub-model defaults to a provider-specific sub-agent model from `config.py`, and you can override it independently with `--sub-agent-model` or `PBI_AGENT_SUB_AGENT_MODEL`.

## Saved Config Workflow

```bash
uv run pbi-agent config providers create \
  --name "OpenAI Main" \
  --kind openai \
  --api-key sk-...

uv run pbi-agent config profiles create \
  --name analysis \
  --provider-id openai-main \
  --model gpt-5.4 \
  --sub-agent-model gpt-5.4-mini \
  --reasoning-effort xhigh

uv run pbi-agent config profiles select analysis
uv run pbi-agent web
```

## Internal Config Shape

```json
{
  "providers": [
    {
      "id": "openai-main",
      "name": "OpenAI Main",
      "kind": "openai",
      "api_key": "sk-...",
      "responses_url": "https://api.openai.com/v1/responses",
      "generic_api_url": null
    }
  ],
  "model_profiles": [
    {
      "id": "analysis",
      "name": "Analysis",
      "provider_id": "openai-main",
      "model": "gpt-5.4",
      "sub_agent_model": "gpt-5.4-mini",
      "reasoning_effort": "xhigh",
      "max_tokens": 16384,
      "service_tier": null,
      "web_search": true,
      "max_tool_workers": 4,
      "max_retries": 3,
      "compact_threshold": 150000
    }
  ],
  "active_model_profile": "analysis"
}
```

## Provider Matrix

| Provider | API Shape | Default Endpoint | Default Model | Default Sub-Model | Env Var for Key | Image Input |
| --- | --- | --- | --- | --- | --- | --- |
| OpenAI | Responses API | `https://api.openai.com/v1/responses` | `gpt-5.4` | `gpt-5.4-mini` | `OPENAI_API_KEY` | yes |
| xAI | Responses API | `https://api.x.ai/v1/responses` | `grok-4.20` | `grok-4-1-fast` | `XAI_API_KEY` | no in this build |
| Google | Interactions API | `https://generativelanguage.googleapis.com/v1beta/interactions` | `gemini-3.1-pro-preview` | `gemini-3-flash-preview` | `GEMINI_API_KEY` | yes |
| Anthropic | Messages API | `https://api.anthropic.com/v1/messages` | `claude-opus-4-6` | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` | yes |
| Generic | Chat Completions API | `https://openrouter.ai/api/v1/chat/completions` | none | none | `GENERIC_API_KEY` | no in this build |

Image input covers both explicit user attachments (`run --image`, `/image add`) and model-initiated local image inspection through the `read_image` tool.

::: warning
`--responses-url` is only used by the OpenAI, xAI, and Google backends. Anthropic is hard-wired to `https://api.anthropic.com/v1/messages` in the current implementation, and Generic uses `--generic-api-url` instead.
:::

::: details Hidden compatibility aliases
The CLI also accepts provider-specific hidden aliases that map to `--api-key`: `--openai-api-key`, `--xai-api-key`, `--google-api-key`, `--anthropic-api-key`, and `--generic-api-key`.
:::

## OpenAI

| Setting | Value |
| --- | --- |
| Select it | `--provider openai` or `PBI_AGENT_PROVIDER=openai` |
| API key | `--api-key`, `PBI_AGENT_API_KEY`, or `OPENAI_API_KEY` |
| Endpoint override | `--responses-url` or `PBI_AGENT_RESPONSES_URL` |
| Default model | `gpt-5.4` |
| Default sub-model | `gpt-5.4-mini` |
| Model override | `--model` or `PBI_AGENT_MODEL` |
| History mode | Server-side via `previous_response_id` |
| Image input | Supported |

```bash
export OPENAI_API_KEY="sk-..."
uv run pbi-agent --provider openai web
```

## xAI

| Setting | Value |
| --- | --- |
| Select it | `--provider xai` or `PBI_AGENT_PROVIDER=xai` |
| API key | `--api-key`, `PBI_AGENT_API_KEY`, or `XAI_API_KEY` |
| Endpoint override | `--responses-url` or `PBI_AGENT_RESPONSES_URL` |
| Default model | `grok-4.20` |
| Default sub-model | `grok-4-1-fast` |
| Model override | `--model` or `PBI_AGENT_MODEL` |
| History mode | Server-side via `previous_response_id` |
| Image input | Not enabled in this build |

```bash
export XAI_API_KEY="xai-..."
uv run pbi-agent --provider xai run --prompt "List the report pages in this PBIP project."
```

## Google

| Setting | Value |
| --- | --- |
| Select it | `--provider google` or `PBI_AGENT_PROVIDER=google` |
| API key | `--api-key`, `PBI_AGENT_API_KEY`, or `GEMINI_API_KEY` |
| Endpoint override | `--responses-url` or `PBI_AGENT_RESPONSES_URL` |
| Default model | `gemini-3.1-pro-preview` |
| Default sub-model | `gemini-3-flash-preview` |
| Model override | `--model` or `PBI_AGENT_MODEL` |
| History mode | Server-side via `previous_interaction_id` |
| Image input | Supported |

```bash
export GEMINI_API_KEY="AIza..."
uv run pbi-agent --provider google web
```

## Anthropic

| Setting | Value |
| --- | --- |
| Select it | `--provider anthropic` or `PBI_AGENT_PROVIDER=anthropic` |
| API key | `--api-key`, `PBI_AGENT_API_KEY`, or `ANTHROPIC_API_KEY` |
| Endpoint override | not currently supported; the provider posts to `https://api.anthropic.com/v1/messages` |
| Default model | `claude-opus-4-6` |
| Default sub-model | `claude-sonnet-4-6` |
| Model override | `--model` or `PBI_AGENT_MODEL` |
| History mode | Client-side full message replay |
| Image input | Supported in live sessions; resumed sessions replay only persisted text history |

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
uv run pbi-agent --provider anthropic web
```

## Generic

| Setting | Value |
| --- | --- |
| Select it | `--provider generic` or `PBI_AGENT_PROVIDER=generic` |
| API key | `--api-key`, `PBI_AGENT_API_KEY`, or `GENERIC_API_KEY` |
| Endpoint override | `--generic-api-url` or `PBI_AGENT_GENERIC_API_URL` |
| Default model | none; the request omits `model` when unset |
| Default sub-model | none; `sub_agent` also omits `model` when unset |
| Model override | `--model` or `PBI_AGENT_MODEL` |
| History mode | Client-side full message replay |
| Image input | Not enabled in this build |

```bash
export GENERIC_API_KEY="or-..."
uv run pbi-agent \
  --provider generic \
  --generic-api-url https://openrouter.ai/api/v1/chat/completions \
  --model openai/gpt-5.4 \
  run --prompt "Summarize the measures in this model."
```

::: tip
For the Generic backend, leaving `--model` unset is intentional when you want the upstream router to pick the model.
:::
