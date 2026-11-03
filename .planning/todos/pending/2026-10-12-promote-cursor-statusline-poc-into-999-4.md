---
created: 2026-10-12T12:50:00.000Z
title: Promote Cursor statusline POC spike into Phase 999.4 discuss/plan
area: statusline
severity: major
resolves_phase: 30.2
files:
  - .planning/ROADMAP.md
  - .claude/worktrees/poc-cursor-statusline/
  - .claude/worktrees/host-split-statusline-spec/.planning/specs/
---

> *Re-pointed 2026-11-03 (Phase 30.1 discuss): the `resolves_phase: 54` tag ("delivered by v1.3") was wrong — the owner
> saw the proof of concept in Cursor and the shipped host split diverged from it. Phase 30.2 starts from this
> proof of concept (branch `archive/poc/cursor-statusline`) and closes the gap.*
>
> *Amended 2026-11-03 (30.2 D-11): folded into Phase 30.2; this todo, the branch and its archive tag close after
> 30.2's verification, with owner confirmation for the deletion.*

## Problem

Cursor CLI can host a Claude-like `statusLine`, but `main` still only ships
`tools/status-line.py` for Claude Code. A throwaway POC proved the Cursor
payload, Dashboard quota RPC, layout, and RSS host-matching, then unwired
live config again. That evidence must feed Phase 999.4 — not stay as a
silent worktree.

## Solution

- Keep Phase 999.4 on `.planning/ROADMAP.md` §Backlog (already noted) with
  pointers to:
  - Spike: branch `poc/cursor-statusline` /
    `.claude/worktrees/poc-cursor-statusline`
  - Design/review: `.claude/worktrees/host-split-statusline-spec/.planning/specs/`
- When promoting: `/gsd-review-backlog` → discuss/plan-phase; fold POC
  findings (cmdline RSS, quota row-2 layout, stale-cache/`≈` behavior,
  ~1.9s cold fetch) into CONTEXT; resolve design REVIEW R3-1..R3-6.
- Do **not** merge the POC into `main` as production; extract via the
  host-split design instead.
- Keep `~/.cursor/cli-config.json` `statusLine` unset until 999.4 ships a
  real cursor entry + setup/wizard wiring.

## Acceptance

- [ ] 999.4 promoted off backlog with plans that cite the POC + design specs
- [ ] Specs/REVIEW either copied onto `main` `.planning/specs/` or linked
      as the single source of truth
- [ ] No lingering live wire of `cursor-status-line-poc.py` in uz's
      `cli-config.json` unless deliberately re-enabled for a demo
