# opencode Sidebar/Status-Bar Plugin Viability

**Researched:** 2026-09-09
**Requirement:** `REQ-multi-cli-opencode-ui-research`
**Scope:** D-06 — this report focuses exclusively on opencode's sidebar/status-bar plugin-API
viability. It cross-references `anomalyco/opencode#5971` (mandatory per D-06) and
`anomalyco/opencode#23539` (added because the phase's own goal names both "sidebar" and
"status-bar," and omitting the status-bar issue would understate the actual state of upstream
interest — see `01.2-RESEARCH.md`'s own recommendation). No code changes accompany this report.

## Current hook surface

opencode's plugin system today supports **backend-only** extension points: event hooks, custom
tools, agents, MCP configs, and env injection, as documented at
`opencode.ai/v2/docs/build/plugins` and `opencode.ai/v2/docs/build/plugins/cli`. None of these
hooks give a plugin any way to render custom UI inside opencode's own interface — there is
currently **no documented mechanism for a plugin to draw into the sidebar or the status bar**.
A plugin can react to events, expose new tools, and shape agent behavior, but it cannot today
add a persistent visual element to opencode's TUI shell itself.

## anomalyco/opencode#5971 (sidebar panels)

**Status:** open, unimplemented as of 2026-09-09. Assigned to `@thdxr`, with no linked PR and no
substantive maintainer comment or roadmap commitment visible as of this research date. The issue
itself is dated 2025-12-22.

**Proposed API:** a `SidebarPanel` interface allowing a plugin to register a collapsible section
in opencode's sidebar, with either static content or dynamic content refreshed on a 5-second
poll interval.

**Named example use cases (from the issue itself):**
- Background agent task status (running/completed/failed)
- Custom metrics or state tracked by hooks
- Plugin-specific configuration status
- Agent availability/health indicators

This is the mandatory cross-reference per D-06.

## anomalyco/opencode#23539 (status bar widgets)

**Status:** open, unimplemented as of 2026-09-09 — same lack of maintainer engagement as #5971
(assigned, no linked PR, no substantive maintainer response).

**Proposed API:** a `tui.statusbar.widget` hook, taking a widget id, a positioning parameter, a
render function, and a refresh interval. The issue references two earlier related issues
(`#8619` and `#18969`) and notes that opencode's TUI is built on the Bubble Tea framework, whose
composable-model architecture the issue's author argues is well suited to this kind of
extension point.

This issue directly covers the status-bar half of this report's scope. D-06 names only #5971 as
the mandatory cross-reference, but the phase's own goal explicitly says "sidebar/status-bar" —
omitting #23539 would understate the actual state of upstream interest in UI-extensible plugin
hooks, so it is included here alongside #5971.

## Codex

Not applicable here.

## Recommendation

**Wait for upstream.** No stable, shipped opencode plugin hook exists today that could back a
custom sidebar or status-bar element, even as a workaround — the entire currently-documented
hook surface (event hooks, tools, agents, MCP config, env injection) has zero UI-rendering
capability, and both #5971 and #23539 confirm this from their own framing ("Currently, OpenCode's
plugin system is powerful for backend logic... but there is no way for plugins to render custom
UI elements in the TUI," per #23539). With two independent, open, unimplemented, and
maintainer-unengaged feature requests covering this exact gap, there is no hook to prototype
against — building toward either proposed API now would mean coding against a shape that can
still change or never ship.

**Re-investigation trigger:** re-investigate opencode sidebar/status-bar viability when either
`anomalyco/opencode#5971` or `anomalyco/opencode#23539` gains a linked PR, or when a maintainer
posts a substantive implementation comment on either issue — whichever happens first. Until one
of those two concrete events occurs, this recommendation stands.

## Sources

- `opencode.ai/v2/docs/build/plugins`, `opencode.ai/v2/docs/build/plugins/cli` — current plugin
  hook surface (event hooks, tools, agents, MCP config, env injection).
- `github.com/anomalyco/opencode/issues/5971` — "Plugin API for custom sidebar panels," fetched
  and read directly during Phase 1.2 research (2026-09-09).
- `github.com/anomalyco/opencode/issues/23539` — "[FEATURE]: Plugin API for custom status bar
  widgets," fetched and read directly during Phase 1.2 research (2026-09-09).

**Valid until:** ~14 days from research date (2026-09-09) — upstream issue status can change;
re-check both issues' status before treating this recommendation as current if more than two
weeks have passed.
