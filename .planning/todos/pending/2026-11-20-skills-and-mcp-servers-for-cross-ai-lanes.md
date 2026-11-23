---
created: 2026-11-20T04:56:00.000Z
title: Hand skills and MCP servers to cross-AI review and execute lanes by name, path or prose
area: tooling
severity: major
files:
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py
  - skills/ai-kit-spec-review/ai_kit_spec/reviewer_dispatch.py
  - skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py
---

## Problem

Two owner requests during the 2026-11-19 autonomous run (translated), one gap in the Phase 37 and Phase 39 specs.

1. Skills for lanes. Tell the runner (cross-ai.mjs) which skills a lane may use, for execution (agentic editing) and
   for review, chosen by task kind (frontend, backend, review, exec). Discover first which known skills exist on each
   runtime (pi, opencode, copilot, cursor, codex; claude as the caller). Pass the NAME where the lane's runtime can load
   the skill, else the PATH, else the full PROSE as a system-prompt-style block, so the lane can do its work.
2. MCP servers for lanes. Consider enabling useful MCP servers for review and execution when needed.

Where it stands (read in ROADMAP, REQUIREMENTS and the 39 SPEC on 2026-11-19):
- REV-03 (Phase 39) covers lens skills for REVIEWERS only: by path in the prompt guidance, inlined when the host cannot
  load by path (Claude built-ins; pi `--skill` is the one verified path form). REV-05 (Phase 39) is the role-keyed table of
  skills present on each host, shared by review, execute and curated-config. REV-04 (Phase 39) is the capability block
  computed by the runner from the final argv. Nothing gives EXECUTE lanes a skill block, nothing chooses name, path or
  prose per runtime and task kind, and nothing ENABLES an MCP server for a lane (REV-05 lists them by name only).
- Live facts from each host's own `--help` on 2026-11-19 (claude 2.1.328, codex 0.170.0, opencode 2.3.2, pi 1.5.2,
  copilot 1.0.112, cursor-agent 2026.11.13): claude `--mcp-config` and `--strict-mcp-config`; copilot
  `--additional-mcp-config <json>` and the GitHub MCP tool flags; pi `--no-mcp` and `--skill <path>`, servers from its own
  config; cursor-agent `--approve-mcps` only; codex and opencode only an `mcp` management subcommand (a per-call
  override form is unverified).

## Solution

TBD. Amend Phase 39 (REV-03 and REV-05 text, its SPEC and CONTEXT) to cover execute lanes and three delivery modes
(name, path, prose; prose is subject to the context-window refusal), chosen from the role-keyed table and the task
kind, and to enable MCP servers per lane only for the task kind that needs them (a browser or docs server for a frontend
task, codebase-memory-mcp for code exploration), read-only by default, never editing the user's real host config (use the
per-call form or a run-scoped scratch config; where a host has only a config file, report the server as ignored with the
reason), never printing server arguments or secrets, and naming only what was actually enabled in the capability block.
Amend Phase 37 (the runner side): a recorded per-host form for loading a skill or an MCP server, with source labels and
host version, printed as applied, ignored or unknown like the other settings. Apply as dated amendments when units 37
and 39 are reached.

Severity is the orchestrator's suggestion from an unattended run; confirm it at triage.
