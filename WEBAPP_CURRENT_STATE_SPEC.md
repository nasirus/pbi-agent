# Web App Current-State UX/UI Spec

## Purpose

This document describes the **actual current state** of the `pbi-agent` web app as implemented in the React frontend under `webapp/` and the FastAPI-backed web API under `src/pbi_agent/web/`.

It is intended as a redesign handoff document for a dedicated web design tool.

This spec is:

- Descriptive, not prescriptive.
- Focused on the current shipped information architecture, UI structure, behaviors, and visible product framing.
- Written with the ongoing rebrand in mind: the product is moving from a Power BI-specific coding agent to an **agnostic local coding agent for multi-domain work**.

## Product Summary

The web app is currently a **workspace-first operator console** for running and reviewing agent work.

Core jobs of the app:

- Start and continue live coding sessions.
- Review prior session history.
- Configure providers and model profiles.
- Organize work in a kanban board.
- Inspect observability and usage analytics.

The app is not a marketing site and not a consumer-style chat app. It behaves like a compact, dark, tool-oriented control surface for technical users working inside a local repository.

## Current Product Framing

Current product framing is already mostly agnostic in the UI:

- Main topbar brand reads **`Agent Control Room`**.
- Primary navigation uses generic labels: `Sessions`, `Kanban`, `Dashboard`, `Settings`.
- Settings language is provider/model/runtime oriented rather than domain specific.

Current branding is still mixed in platform chrome and metadata:

- Browser `<title>` is still `pbi-agent`.
- Meta description still says `pbi-agent - local coding agent for skills, commands, agents, and multi-domain workflows`.
- FastAPI app title fallback is still `pbi-agent`.
- Favicon asset naming is still `favicon.png` under `src/pbi_agent/web/static/`.
- Repo/docs branding still prominently use `pbi-agent`.

There are no visible Power BI workflow screens in the current web UI.

## Entry Logic And Access Model

There is a single authenticated-less local app shell. There is no login screen.

Route behavior:

- `/` redirects to `/settings` if there are no model profiles.
- `/` redirects to `/sessions` if at least one model profile exists.
- `/sessions`, `/board`, and `/dashboard` are blocked until setup is complete.
- `/settings` is always accessible.

Onboarding gate:

- The app considers onboarding incomplete when `config-bootstrap.model_profiles.length === 0`.
- A blocking modal titled `Setup Required` appears until at least one provider and one model profile exist.
- On non-settings routes, the modal sends the user to `Settings`.
- On `Settings`, the modal becomes an inline “configure below” prompt.

## Information Architecture

Top-level routes:

| Route | Page | Purpose |
| --- | --- | --- |
| `/sessions` | Sessions | Primary live interaction surface with the agent |
| `/sessions/:sessionId` | Session detail | Saved session history plus resumed live runtime |
| `/sessions/live/:liveSessionId` | Live session route | Transitional live route that resolves back to saved sessions when available |
| `/board` | Kanban | Task orchestration and staged task execution |
| `/dashboard` | Dashboard | Metrics, provider/model breakdown, and run observability access |
| `/settings` | Settings | Providers, model profiles, and discovered project commands |

There is no separate home dashboard or landing page before the shell.

## Global Shell

The entire app sits inside a persistent app shell:

- Fixed top bar.
- Main content below it.
- No left rail at the app-shell level.
- The only persistent navigation is the top nav.

### Top Bar

Contents, left to right:

- Brand: `Agent Control Room`
- Workspace label: trailing compact path badge showing the last two path segments of the current workspace root
- Navigation: `Sessions`, `Kanban`, `Dashboard`, `Settings`
- Runtime pills on the right: provider, model, and reasoning effort

Runtime display rules:

- If onboarding is incomplete: provider pill shows `Not configured`.
- On session routes with an active live session: pills reflect the active session runtime.
- Otherwise: pills reflect the active default profile from settings.

### Navigation Behavior

- Top nav uses tab-like text links with amber active underline.
- There is no iconography in primary navigation.
- There is no mobile nav drawer or secondary navigation system.

## Visual Design System

The current UI uses a dark “mission control” design language.

### Overall Tone

- Dense, tool-like, technical.
- Minimal illustration.
- Heavy use of panels, cards, pills, and compact controls.
- More operator-console than collaborative whiteboard.

### Color System

Primary palette:

- Background: near-black / deep charcoal.
- Surfaces: layered dark gray panels.
- Accent: warm amber/orange.
- Success: green.
- Warning: yellow.
- Error: red.
- Info: blue.

Visual emphasis relies on:

- Border contrast.
- Tinted pills.
- Subtle hover fills.
- Amber highlight for active state and key CTAs.

### Typography

- UI font: `Outfit`
- Monospace font: `JetBrains Mono`

Typography pattern:

- Sans-serif for interface labels and body copy.
- Monospace for technical identifiers, models, token counts, paths, and pills.

### Shape And Spacing

- Compact 4px spacing scale.
- Small-to-medium radii.
- Rounded cards and pills.
- Subtle shadow usage, mostly for overlays and dropdowns.

## Shared UX Patterns

Common patterns across the app:

- Empty state cards with title, optional description, optional action.
- Reusable status pills.
- Modal overlays for create/edit/delete flows.
- Compact ghost and primary buttons.
- In-panel error banners for recoverable failures.
- Inline monospace metadata tags for IDs, models, commands, and paths.

## Real-Time Behavior

The app uses WebSockets for live updates.

Two live streams are important:

- App-level event stream:
  - invalidates tasks, board stages, sessions, and live session queries.
- Live-session-specific event stream:
  - updates message timeline, thinking blocks, tool-call groups, wait state, usage, runtime changes, session end state, and sub-agent state.

Connection states shown in UI:

- `Disconnected`
- `Connecting...`
- `Connected`

The session page is the only page with an explicit live connection badge.

## Page Specs

## Sessions

This is the primary operational page.

### Layout

Desktop layout:

- Narrow left session-history rail, collapsible.
- Main conversation panel to the right.

Collapsed state:

- Sidebar shrinks to a slim vertical strip.
- Strip contains:
  - expand arrow
  - new session button

Expanded state:

- Header: `Session History`
- `+ New` button
- collapse arrow
- workspace path badge
- scrollable list of saved sessions

### Session Sidebar

Session list item content:

- Session title or `Untitled session`
- Relative updated time like `Just now`, `12m ago`, `3h ago`, `Apr 21`
- Model pill

Session item actions:

- Click main card to open/resume session
- Hover/focus reveals overflow menu
- Overflow menu currently exposes only `Delete session`

Sidebar empty state:

- Title: `No sessions`
- Description: `Start a new session to begin`

### Session Main Panel

Top sub-bar content:

- Connection badge
- Model profile selector dropdown
- Usage bar
- Run history dropdown button when a saved session exists
- Delete button when viewing a saved session

### Profile Selector

Behavior:

- Dropdown trigger shows currently selected profile name.
- Options show:
  - profile name
  - provider name
  - model
  - reasoning effort
- Changing profile updates:
  - active default profile in global settings
  - live session profile if a live session exists

This means the selector is partly local and partly global in effect.

### Timeline

The timeline is centered and constrained to a readable max width.

Current timeline item types:

- User messages
- Assistant messages
- Notice/debug/error messages
- Thinking blocks
- Tool-call groups
- Sub-agent status banners attached to items

User message rendering:

- Right-aligned bubble
- Amber-tinted background
- Attached file paths rendered inline as pill tags
- Uploaded images shown as preview tiles above text

Assistant message rendering:

- Left-aligned dark panel
- Markdown rendering enabled
- Supports headings, lists, blockquotes, code, tables, and links

Thinking blocks:

- Collapsible
- Default collapsed
- Header row with chevron and title

Tool-call groups:

- Collapsible
- Default collapsed
- Show group label and count
- Expanded state renders each tool item in a `<pre>` block

Other timeline behaviors:

- Auto-scroll follows new content unless the user has manually scrolled up
- A sticky `New messages below` chip appears when new content arrives off-screen
- A processing indicator appears at the bottom when the backend publishes a wait message

### Composer

The composer is a persistent bottom input surface.

Core controls:

- `+` action trigger
- auto-resizing textarea
- send button

Current input capabilities:

- Plain text prompt input
- Slash command completion
- `@` file mention completion
- Clipboard image paste
- File picker image upload

Slash command behavior:

- Only works at the beginning of the prompt
- Suggestions come from discovered project commands and built-in slash commands
- `Enter` on a slash command can auto-complete and submit

`@` mention behavior:

- Searches workspace files and image files
- Inserts escaped paths
- Mentioned files are expanded server-side before submission

Image behavior:

- Allowed types: PNG, JPEG, WEBP
- Preview cards shown before send
- Slash commands cannot be submitted with images
- Image input availability depends on current provider support

Keyboard behavior:

- `Enter` submits
- `Shift+Enter` creates newline
- Arrow keys navigate completions
- `Tab` accepts completion
- `Escape` closes completion panel

Composer disabled states:

- No live session
- Input not enabled by backend
- Session ended
- Submission in progress

### Session States

Current major states:

- Initial live session creation
- Empty conversation
- Active live conversation
- Saved session replay with live session attached
- Session not found
- Fatal session error
- Runtime/profile change error

Current banners used above the timeline:

- Notice banner for input expansion warnings
- Error banner for fatal session/runtime/session-load errors

Empty conversation state:

- Title: `No messages yet`
- Description: `Send a message to start the conversation`

Missing session state:

- Title: `Session not found`
- Description explaining the session is unavailable in the current workspace
- CTA: `Start new session`

### Run History And Run Detail

Saved sessions expose a `Runs` dropdown in the session top bar.

Run history list shows:

- Run status pill
- Agent label
- Sub-run badge when applicable
- Model
- Provider
- Duration
- Token, API call, tool call, error, and cost summaries
- Timestamp

Selecting a run opens a wide modal:

- Run summary section
- Event timeline section

Event timeline capabilities:

- Collapsible event rows
- Event type coloring by category
- Request/response/tool/config/metadata payload inspection
- Status code, duration, token counts, and timestamps

This is an observability/debugging surface, not an end-user narrative surface.

## Kanban

The board is a task orchestration view for staged single-turn task execution.

### Layout

Structure:

- Header row with title and subtitle
- `Edit Stages` action
- `+ Add Task` action
- Horizontal board grid below

Page title:

- `Kanban`

Subtitle:

- `Tasks move by configured stage order and can auto-start per stage`

### Stage Model

Current canonical fixed stages:

- `Backlog`
- `Done`

These are non-runnable and fixed:

- `Backlog` always first
- `Done` always last
- Neither can have profile, command, or auto-start behavior

Runnable stages must be user-created between them.

Stage metadata that can exist on runnable stages:

- Default profile
- Default command
- Auto-start flag

### Board Columns

Column header shows:

- Drag handle
- Stage name
- Optional labels:
  - `auto-start`
  - `command:<id>`
  - `profile:<id>`
- Task count pill

Empty column state:

- `No tasks`

### Task Cards

Visible card content:

- Task title
- Run-status pill
- Prompt preview, clamped to two lines

Hover-revealed content:

- Project/session metadata
- Last result summary in a scrollable code-like block
- Action row

Task actions:

- `Edit`
- `Start` unless the task is in `Done`
- `Session` link when the task is associated with a session
- `Delete`

Running tasks:

- Cannot be dragged
- Action buttons are disabled

### Task Behavior

Current task fields in the modal:

- Title
- Prompt
- Stage
- Profile Override

Important current behavior:

- Plain prompts are normalized into a structured markdown task body:
  - `# Task`
  - task title
  - `## Goal`
  - prompt content
- Structured prompts are preserved
- Backlog tasks cannot start unless there is at least one runnable stage
- Starting a backlog task first moves it to the first runnable stage
- Stage-linked commands can prefix the task prompt when a run starts
- Stages can auto-start when a task enters them

### Stage Editor

The stage editor opens in a modal.

Capabilities:

- Reorder runnable stages with up/down buttons
- Add stage
- Remove runnable stage
- Set stage name
- Set default profile
- Set default command
- Toggle auto-start

Fixed stage rules are explained inline:

- Backlog copy: `Backlog stays first and never runs directly.`
- Done copy: `Done stays last and is archive-only.`

### Board Empty And Prompt States

No tasks page state:

- Title: `No tasks yet`
- Description: `Create your first task to get started`
- CTA: `+ Add Task`

No runnable stage prompt:

- Modal title: `Create Runnable Stage`
- Explains that a board with only `Backlog` and `Done` cannot start backlog tasks
- CTA opens stage editor with a new stage inserted before `Done`

## Dashboard

The dashboard is the reporting and observability overview area.

### Layout

Centered vertical stack with three levels:

- Filter controls
- KPI metric cards
- Breakdown table
- All runs table

### Filters

Current global filter controls:

- Start date
- End date
- Scope toggle:
  - `Workspace`
  - `Global`

Default date window:

- Last 14 days

### Metric Cards

Current cards:

- Sessions
- Runs
- Total Tokens
- Cost
- API Calls
- Tool Calls
- Errors
- Avg Duration

Each card includes:

- Label
- Large numeric value
- Sparkline

### Breakdown Table

Title:

- `Provider / Model Breakdown`

Current sortable columns:

- Provider
- Model
- Runs
- Tokens
- Cost
- Avg Duration
- Errors

This section is read-only and summary-oriented.

### All Runs Table

Title:

- `All Runs`

Header also shows total count.

Current filters inside the panel:

- Status dropdown
- Provider text filter
- Model text filter

Current sortable columns:

- Duration
- In Tokens
- Out Tokens
- Cost
- Errors
- Time

Non-sort columns:

- Status
- Session
- Agent
- Model
- Provider

Pagination:

- Page size is 25
- `Previous` and `Next` controls

Row click:

- Opens the same run-detail modal used from the Sessions page

Current empty/error states:

- `No runs match the current filters.`
- `Failed to load runs.`

## Settings

Settings is both the onboarding surface and the system configuration surface.

### Layout

Centered stack of three panels:

- Providers
- Model Profiles
- Commands

When no profiles exist, an onboarding note appears above the panels.

Onboarding note copy:

- Step 1: add a provider and complete sign-in if needed
- Step 2: create a model profile using that provider

### Providers Panel

Purpose:

- Configure provider records and authentication method

Panel actions:

- `+ Add Provider`

Provider card content:

- Name
- Provider ID
- Provider kind tag
- Auth mode tag
- Auth status tag
- Optional key/source tag
- Optional plan tag
- Optional custom URL tags
- Optional email/backend/expiry summary

Provider card actions:

- `Connect` or `Reconnect` for account-based auth
- `Refresh`
- `Disconnect`
- `Edit`
- `Delete`

Supported configuration concepts visible in UI:

- Provider kind
- Authentication mode
- API key via env var / plaintext / none
- Custom Responses URL
- Custom OpenAI-compatible API URL

### Provider Modal

Fields:

- Name
- Optional ID on create
- Kind
- Authentication mode tabs when multiple auth modes exist
- Credential source tabs for API-key auth
- Environment variable name or plaintext API key
- Optional Responses URL override
- Optional generic API URL override

Non-API-key providers:

- Show a note that saving the provider continues into sign-in

### Provider Auth Flow Modal

Purpose:

- Complete provider account sign-in inside the app

Flow variants:

- Browser flow
- Device-code flow

Visible states:

- Method picker
- Start action
- Pending authorization
- Completed authorization
- Failed authorization

Displayed details can include:

- Authorization URL
- Verification URL
- User code
- Copy code action
- Account email
- Plan type
- Expiry timestamp

### Model Profiles Panel

Purpose:

- Create reusable runtime configurations

Panel actions:

- `+ Add Profile`

Panel-level control:

- Active default profile dropdown

Profile card content:

- Name
- `default` tag when active
- Profile ID
- Provider name and provider kind tags
- Runtime summary line composed from model, reasoning effort, service tier

Profile card actions:

- `Edit`
- `Delete`

### Model Profile Modal

Fields:

- Name
- Optional ID on create
- Provider
- Model
- Sub-agent model
- Reasoning effort
- Max tokens
- Service tier when supported
- Web search
- Max tool workers
- Max retries
- Compact threshold

Model selection behavior:

- Tries to fetch provider-supported models dynamically
- Can switch between:
  - provider-discovered model select
  - custom free-text entry

The profile modal is powerful but dense. It exposes both common runtime settings and advanced controls in one form.

### Commands Panel

Purpose:

- Show project command files discovered under `.agents/commands/`

This panel is read-only in the web UI.

Current content:

- Inline note explaining that Markdown files under `.agents/commands/` become slash commands
- One card per command

Command card content:

- Command name
- Command ID
- Slash alias tag
- File path tag
- Optional description
- Full instructions preview in a scrollable preformatted block

Empty state:

- Title: `No commands found`
- Description: `Add project command files under .agents/commands/.`

## Responsive Behavior

Current responsive behavior is partial and route-specific.

Sessions page on small screens:

- Sidebar disappears entirely
- Session layout becomes single-column
- Session top bar stacks vertically
- Profile selector expands to full width

Kanban page on smaller screens:

- Header stacks
- Board remains horizontally scrollable
- Columns become wider relative to viewport
- Stage editor rows collapse to one column

Dashboard and Settings:

- Use centered, vertically stacked layouts
- No dedicated mobile navigation treatment is implemented at the shell level

Top shell on mobile:

- No alternate nav pattern exists in code
- Primary nav remains topbar-based

## Current UX Characteristics

What the current app feels like:

- Professional, technical, and tool-heavy
- Designed for existing operator intent rather than discovery
- Dense but understandable for engineering users
- Strongly oriented around visibility of runtime state

What currently dominates the experience:

- Sessions as the primary working surface
- Settings as the prerequisite setup surface
- Kanban and Dashboard as operational support surfaces

## Current-State Friction Points

These are factual current-state observations useful for redesign planning.

- Branding is mixed between `Agent Control Room` in the shell and `pbi-agent` in page metadata and infrastructure naming.
- The top-level IA is clear, but there is no higher-level “overview” or home state between onboarding and raw operation.
- Sessions, settings, observability, and orchestration all use the same dense control-room language, so there is limited visual hierarchy between “work”, “configuration”, and “analytics”.
- The profile selector on the Sessions page has both global and local effects, which may be non-obvious to users.
- The Settings surface exposes advanced runtime options in first-class create/edit flows, which is powerful but cognitively heavy.
- Commands are inspectable in Settings but not manageable there; management still relies on file-system conventions.
- Mobile behavior exists for the session and board layouts, but global navigation does not have a dedicated mobile pattern.

## Summary

The current web app is a **dark, compact, operator-focused control room** for a local coding agent. It already behaves as an **agnostic multi-domain tool**, not a Power BI-specific product, but its branding and metadata still partially reflect the older `pbi-agent` identity.

The redesign should treat the current app as:

- a workspace-native technical product
- with four core surfaces: live sessions, task orchestration, observability, and runtime configuration
- presented today through a mission-control style UI with compact dark panels, amber accents, and dense technical metadata
