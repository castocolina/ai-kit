---
created: 2026-10-14T20:54:03.000Z
title: Wire jev-fast-decision cross-host discovery scaffolding
area: skills
severity: major
files:
  - ~/.claude/skills/jev-fast-decision/SKILL.md
  - .planning/docs/system-one-decision-skill/PLAN.md
  - .planning/todos/pending/2026-10-11-execute-system-one-decision-skill-plan.md
  - .planning/ROADMAP.md
  - ~/.claude/CLAUDE.md
  - ~/.codex/AGENTS.md
  - ~/.config/opencode/AGENTS.md
  - ~/.pi/AGENTS.md
---

## Problem

`jev-fast-decision` lives only in `~/.claude/skills/jev-fast-decision/`, so only Claude Code
can discover it. Live-verified on 2026-10-14:

- Pi scans `~/.agents/skills/` and `.agents/skills/` (Pi docs, skills.md); the skill is in
  neither, so pi, opencode, codex, and Cursor sessions never load it.
- The skill is disabled by default and gated by per-session env vars (`GSD_PATH_JEV=1`,
  `JEV_BACKEND`, `JEV_ALLOW_REMOTE=1` for remote backends), but no always-on instruction file
  tells an agent that the skill exists, how to probe availability (`--probe`), or how to read
  `consent_required_for_remote` / `missing_api_key`.
- The four global always-on files exist and already carry ai-kit marker blocks
  (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.config/opencode/AGENTS.md`,
  `~/.pi/AGENTS.md`; CODEGRAPH_START/END precedent), but none mention jev.
- `TYPESAFE_API_KEY` is exported in `~/.mycreds` (0600, sourced via `~/.myshellrc` from both
  `.zshrc` and `.bashrc`) — interactive shells only. Agent tool shells are non-interactive and
  do not inherit it, so any script the skill runs must source `~/.mycreds` itself or fail
  closed with a clear reason.
- The direct API works from this machine (curl `POST /v1/systemone`, model `jev-latest`, key
  accepted; typed answers with probabilities returned).

Owner intent (2026-10-14): hard or complex code decisions stay with deep-reasoning LLMs;
Jev exists to absorb trivial-but-time-consuming structured judgments (picking among named
options, yes/no gating, severity triage, rubric scores) that otherwise burn long deliberation
passes. Advisory only, never a gate.

## Scope boundaries (checked 2026-10-14)

- Skill internals (3 backends, consent rules, calibration) are planned in
  `.planning/docs/system-one-decision-skill/PLAN.md` and queued by the pending todo
  `2026-10-11-execute-system-one-decision-skill-plan.md`. This todo does not touch them.
- GSD-chain usage of the decision ladder (detection semantics, logging, overrides) is already
  spec'd as v1.3 Phase 24 "Spec-and-discuss chain skill" on branch
  `gsd/v1.3-curated-config-v2` ("optional and detected, never assumed": Laya by TCP
  reachability, TypeSafe by key name, jev-fast-decision by its install). Reuse those
  semantics; do not reinvent detection here.
- This todo covers only the discovery/wiring layer: make the skill visible beyond Claude Code
  and teach every host's always-on context that it exists and how to reach it.

## Solution

Future scope; sequence after the plan-execution todo and aligned with v1.3 Phase 24:

1. Make the skill cross-host discoverable: install/symlink into `~/.agents/skills/` (Pi reads
   it natively; Claude Code already symlinks from there) via the ai-kit installer rather than
   a manual copy, keeping one source of truth.
2. Add a short marker block (CODEGRAPH-style, idempotent, atomic writes per repo rules) to the
   four global instruction files: trigger conditions (routing among named options, triage,
   gating, rubric scores), the activation env line, `--probe` usage, and the
   never-when-no-backend rule.
3. Credential guidance for non-interactive shells: document the `~/.mycreds` source pattern in
   the skill's reference so `jev_review.py` fails closed with a clear reason instead of an
   empty-key error.
4. Deliver as an ai-kit-installed piece (installer option or skill) so the wiring is portable
   and reproducible across machines; any new SKILL.md content passes the skill-judge loop.
