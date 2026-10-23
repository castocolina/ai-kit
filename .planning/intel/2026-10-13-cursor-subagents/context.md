# Context: Cursor subagents pinned to non-fast models

All entries below come from one DOC unless marked "session-decision".
Doc: /var/home/bazzite/git/personal/ai-kit/.planning/todos/pending/2026-10-13-add-cursor-subagents-pinned-to-non-fast-composer-2-5-and-grok.md
(type DOC, confidence high, manifest_override true, locked false, precedence null)

## Topic: Problem statement
- source: .planning/todos/pending/2026-10-13-add-cursor-subagents-pinned-to-non-fast-composer-2-5-and-grok.md
- When cursor-agent spawns subagents, only a few agent definitions are available and they allow only a few models.
- One of them runs on `composer-2.5-fast`, which the user measured at roughly 5x the token spend of the non-fast model.
- Wanted: subagents on the non-fast models `composer-2.5` and a non-fast grok.
- Frontmatter: area agents, severity minor, created 2026-10-13T17:14:21.797Z.

## Topic: Environment facts (checked 2026-10-13, cursor-agent 2026.10.01-e373342)
- source: same DOC, "Problem" section
- No custom agents exist yet: `~/.cursor/agents/` and ai-kit's `.cursor/agents/` are both empty.
- Cursor also reads `~/.claude/agents`, where the 35 GSD agents live. Per research 07, Cursor's GSD conversion keeps only name and description, so tool lists and models are ignored.
- The fast default lives inside the cursor-agent bundle (`1623.index.js`), not in user files: `composer-2` maps to `composer-2.5` and `composer-2-fast` maps to `composer-2.5-fast`.
- Non-fast models on this account (`cursor-agent --list-models`): `composer-2.5`; `grok-4.7-low`/`-medium`/`-high`/`-xhigh`; `cursor-grok-4.6-low`/`-medium`/`-high`/`-xhigh`; `cursor-grok-4.5-high`. Every one has a `-fast` twin. `auto` is the account default.
- The user's interactive shell function `cursor-agent` injects `--model gpt-5.6-sol-high` when no `--model` is given. Scripts do not see shell functions, so subprocess calls must always pass `--model`.

## Topic: Live-verified behavior (2026-10-13, parent --model auto)
- source: same DOC, "Verified 2026-10-13" section (live-tested fact)
- Frontmatter the bundle parses: `name`, `description`, `model` (default `inherit`), `force-default-model`, `readonly: true`, `background`, `tools` (comma list). Cursor's own create-subagent skill documents only the first two.
- Per-agent pin works: `.cursor/agents/composer-worker.md` with `model: composer-2.5`; the Task call ran `custom:composer-worker` with `"model":"composer-2.5"` and created the file (20 s).
- Per-call model works too: an agent with no `model:`, invoked with "set its model parameter to grok-4.7", carried `"model":"grok-4.7-high"` and created the file (67 s). The Task tool has a `model` argument.
- Variant resolution uses `~/.cursor/cli-config.json` `modelParameters`. The user stores `composer-2.5: fast=false` and `grok-4.7: reasoning_effort=high, fast=false`; `grok-4.7` resolved to `grok-4.7-high`, with no `-fast`.
- Unconfirmed: the non-fast billing itself. The stream shows no fast flag; check one run in the Cursor usage dashboard.
- The built-in explore subagent has its own knob: `cli-config.json` `subagentModels.explore` / `exploreSubagentModel` (`default` or `inherit`, or a model via `/config`).
- Scratch test workspace: `scratchpad/cursor-subagent-test/` (session e987e526).

## Topic: Approach hints in the doc (Solution section)
- source: same DOC, "Solution" section
- 1. Confirm the schema (frontmatter fields; whether `model` accepts exact ids or only aliases; how Cursor resolves the same name across `~/.cursor/agents`, project `.cursor/agents` and `~/.claude/agents`). Partly answered by the Verified section; name-resolution across the three directories is not answered there.
- 2. Create a minimal user-level set in `~/.cursor/agents/*.md`: `composer-worker` (`model: composer-2.5`), `grok-worker` (`model: grok-4.7-medium`), optionally a read-only `composer-explorer`. Keep bodies short. Verify live that the parent delegates and that each run uses the pinned non-fast model.
- 3. Decide ownership: ai-kit could ship them like its skills, with `tools/setup.py` linking them into `~/.cursor/agents`; check against the scope split (tools-installer owns third-party sets only).
- 4. Coordinate with v1.3 Phase 18: the curated `cross-ai.mjs` cursor block already pins `--model`; the new agents cover Cursor's in-session subagents, which `cross-ai.mjs` does not.
- 5. Look for a fast-default override: check whether Cursor's built-in subagents (explore and similar) can be overridden to a non-fast model by config, which would be cheaper than custom agents.

## Topic: Related file references in the doc
- source: same DOC, frontmatter `files:`
- `~/.cursor/agents/`
- `~/.local/share/cursor-agent/versions/2026.10.01-e373342/1623.index.js`
- `skills/ai-kit-spec-review/ai_kit_spec/commands.py:116`

## Topic: Session decisions (NOT from a classified doc)
- source: orchestrator prompt for this ingest run (user decisions made this session); recorded for the roadmapper, not extracted from the DOC
- ai-kit owns its own agents and skills; tools-installer owns third-party sets only. Resolves doc step 3.
- Ship the agents from ai-kit, with `tools/setup.py` linking them into `~/.cursor/agents`.
- Pin the model in each agent file (`composer-2.5`, `grok-4.7`).
- Ship no unpinned generic agent. This declines the doc's verified per-call-model option (one generic agent taking `model` as a parameter).
- Fold this work into existing ROADMAP Phase 21 "Cursor Live Validation" (v1.3, phases 16-22).
