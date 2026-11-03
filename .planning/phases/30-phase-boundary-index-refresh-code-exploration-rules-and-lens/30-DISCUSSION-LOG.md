# Phase 30: Phase-boundary index refresh, code-exploration rules and lens wiring - Discussion Log (standard discuss mode (`--analyze --all --batch`))

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-03
**Phase:** 30-phase-boundary-index-refresh-code-exploration-rules-and-lens
**Mode:** interactive, standard discuss mode (`--analyze --all --batch`) with the owner answering through the
orchestrator; decision ladder not used; best design wins over the smallest diff (mvp-mode inactive, DESIGN-01).
**Areas analyzed:** where the step lives and its triggers; the brief; the advisor and the lens brief; the global
sentence rewrite; GSD versus non-GSD graph location (added by the owner).

## Assumptions Presented

No analyzer: in the interactive path `gsd-assumptions-analyzer` runs only when the owner asks, and the owner did not.
No advisor researcher: `.claude/gsd-core/USER-PROFILE.md` does not exist. No active `discuss:pre` hook.

## jev screening

The owner asked for no ladder screening; every item was answered by the owner or decided by own reasoning.

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| Engine home | – | – | Owner, recommended: D-01 |
| GSD triggers | – | – | Owner, recommended: D-02 |
| Worktree trigger | – | – | Owner, recommended plus resilience: D-03; setup-dev tools: D-04 |
| Phase 49 todo | – | – | Owner, recommended: D-05 |
| Brief location | – | – | Owner, recommended: D-06 |
| Brief delivery | – | – | Owner, recommended: D-07 |
| Symbol source | – | – | Owner, against the recommended option: D-08 (use `codegraph_explore`, no database read) |
| Advisor trigger | – | – | Owner, recommended: D-09 |
| Lens brief | – | – | Owner, recommended: D-10 |
| Headless trigger for R11 | – | – | Owner, recommended: D-11 |
| One graph build, two places | – | – | Owner note plus live check: D-12 |
| R07/R08, judge bar, fakes | – | – | **Own reasoning:** D-13, D-14, D-15 (not objected; no ledger, blocks nothing) |
| GSD versus non-GSD | – | – | Owner rule: D-16 |

## Batches presented

1. **Where the step lives and how it hooks in:** engine command or separate script; GSD hooks or instruction text;
   pre-commit `post-checkout`, a hand-written git hook or a session hook; fold the Phase 49 todo or not.
2. **The brief:** gitignored per checkout, committed in the phase folder, or inside `.git/`; agent-skills entry or
   edits to CONTEXT and PLAN; symbols from codegraph's database, from `--symbols-only` text, or from Python's parser.
3. **The advisor and the lens brief:** code searches including Grep and Glob, Bash only, or session start; a tracked
   lens-brief entry or AGENTS.md only.
4. **The global sentence rewrite:** a `--with-global-rules` flag plus a wizard item, every install, or under
   `--with-hooks`.

## Live facts that changed the plan

- `graphify update . --graph <path>` exits 2 ("unknown update option: --graph"); `graphify query … --graph
  .planning/graphs/graph.json` works (D-12).
- codegraph's CLI has no per-file JSON symbol listing with spans (`query --json` is search-based; `node
  --symbols-only` is text without end lines) — moot after D-08.
- The advisor's Claude hook matcher is `Bash|Read` (`tools/setup.py`), so Grep and Glob need the widened matcher (D-09).
- pre-commit 4.6.0 is installed; ai-kit's `default_install_hook_types` is `[pre-commit, pre-push]` (D-03).
- ai-kit's Makefile has `setup-env` and `dev`, no `setup-dev`; RULE-05 and RULE-09 are Phase 46's (D-04).
- `codegraph init -y` is a silent no-op on an existing index; `status --json` `pendingChanges` turns non-zero after an
  edit and zero after `sync` (SPEC R11 sentence).
- codegraph's installer writes the `CODEGRAPH_START` block into four global files (Claude, Codex, Gemini, opencode);
  all four hold the sentence once on this machine (counted, not printed).

## Corrections Made

- **Symbol source (D-08):** the recommended option (read codegraph's index database read-only, cache the base) was
  replaced by the owner's: the agents call `codegraph_explore` themselves; SPEC R4 amended and five edge rows
  superseded.
- **"Indexing is the user's decision":** written by codegraph's installer, not the owner; the owner wants automatic
  indexing (SPEC R2, R7, R11).
- **Worktree hook as the only trigger (D-03):** the owner required resilience; the boundary step and the rule are
  further triggers, and `setup-dev` installs the tools (D-04, SPEC R12, FLOW-13).
- **Graph location (D-16):** the owner separated GSD from non-GSD projects; no `.planning/` is created for a non-GSD
  project.

## Cross-phase amendments in this commit

- SPEC R3, R4, R6, R7, R8 amended; R11 and R12 added; edge table 67/67 (`edge_floor.py check` ok).
- REQUIREMENTS: FLOW-12 and FLOW-13 added (155 requirements); RULE-03, RULE-05, RULE-06 and JEV-04 amended.
- ROADMAP: Phase 30 requirements, anchors and criteria 7-9; Phase 46 criterion 1 coupling; Phase 54 criterion 3.
- Todo `2026-10-24-make-the-ai-kit-session-hooks-dynamic-…`: dated note (D-05).

## External Research

None beyond the installed tools' own source and help (codegraph 1.6.2, graphify 0.9.54, gsd-core 1.18.0, pre-commit
4.6.0).
