---
created: 2026-10-13T17:14:21.797Z
title: Add Cursor subagents pinned to non-fast composer-2.5 and grok
area: agents
severity: minor
files:
  - ~/.cursor/agents/
  - ~/.local/share/cursor-agent/versions/2026.10.01-e373342/1623.index.js
  - skills/ai-kit-spec-review/ai_kit_spec/commands.py:116
---

## Problem

When Cursor (cursor-agent) spawns subagents, only a few agent definitions are available, and they allow only a few models. One of them runs on `composer-2.5-fast`, which the user measured at roughly 5× the token spend of the non-fast model. The user wants subagents that run on the **non-fast** models: `composer-2.5`, and a non-fast grok.

Facts checked on 2026-10-13 (cursor-agent 2026.10.01-e373342):

- **No custom agents exist yet.** `~/.cursor/agents/` and ai-kit's `.cursor/agents/` are both empty.
- **Cursor also reads `~/.claude/agents`,** where the 35 GSD agents live. Per research 07, Cursor's GSD conversion keeps only name and description, so tool lists and models are ignored.
- **The fast default lives inside the cursor-agent bundle,** not in user files. `1623.index.js` maps `composer-2` → `composer-2.5` and `composer-2-fast` → `composer-2.5-fast`.
- **Non-fast models on this account** (`cursor-agent --list-models`):
  - `composer-2.5`
  - `grok-4.7-low` / `-medium` / `-high` / `-xhigh`
  - `cursor-grok-4.6-low` / `-medium` / `-high` / `-xhigh`
  - `cursor-grok-4.5-high`

  Every one of these has a `-fast` twin. `auto` is the account default.
- **The user's interactive shell function `cursor-agent` injects `--model gpt-5.6-sol-high`** when no `--model` is given. Scripts don't see shell functions, so subprocess calls must always pass `--model`.

## Solution

TBD. Approach hints:

1. **Confirm the schema.** Check Cursor's custom-subagent frontmatter in the official docs (name, description, `model`, readonly or tools fields, and whether `model` accepts exact ids like `composer-2.5` / `grok-4.7-medium` or only aliases). Also check how Cursor resolves the same name across `~/.cursor/agents`, project `.cursor/agents` and `~/.claude/agents`.
2. **Create a minimal set of user-level agents** in `~/.cursor/agents/*.md`, for example:
   - `composer-worker` (`model: composer-2.5`), general implementation;
   - `grok-worker` (`model: grok-4.7-medium`), an alternative implementer or reviewer;
   - optionally a read-only `composer-explorer` for search and exploration.

   Keep each body short, with no heavy instructions. Verify live that a parent session delegates to them and that each run uses the pinned model and not `-fast` (check usage or the model id in the transcript).
3. **Decide ownership.** These are our own agents, so ai-kit could ship them like its skills, with `tools/setup.py` linking them into `~/.cursor/agents`. Check against the scope split in memory: tools-installer owns third-party sets only.
4. **Coordinate with v1.3 Phase 18.** The curated `cross-ai.mjs` cursor block already pins `--model`. The new agents cover Cursor's *in-session* subagents, which `cross-ai.mjs` does not.
5. **Look for a fast-default override.** Check whether Cursor's built-in subagents (explore and similar) can be overridden to a non-fast model by config, which would be cheaper than custom agents.
