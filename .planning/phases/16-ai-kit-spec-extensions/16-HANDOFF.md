# Handoff: v1.3 curated-config v2: Phase 16 code-reviewed and fixed, phases 17–20 pending

## Session Metadata
- Created: 2026-09-24 11:57:32
- Project: /var/home/bazzite/git/personal/ai-kit
- Branch: gsd/v1.3-curated-config-v2
- Session duration: about 2 days of autonomous GSD work across several context compactions

## Recent Commits (for context)
  - e233dc9 docs(16): add code review fix report
  - 99ccb98 fix(16): resolve code review lint findings WR-01..WR-04 and IN-01
  - 1ea2085 docs(16): add code review report
  - fa4fd4e docs(16-06): record orchestrator gate re-run (GATE PASSED)
  - b407f8f style(16): restore original test name renamed by the lint fix

## Handoff Chain

- **Continues from**: [2026-09-23-114518-ai-kit-usage-metrics-dashboard-ux-fixes.md](./2026-09-23-114518-ai-kit-usage-metrics-dashboard-ux-fixes.md)
  - Previous title: ai-kit usage-metrics dashboard — Phase 15.1 completion + post-UAT UX fixes
- **Supersedes**: None

> A committed copy of this handoff lives at
> `.planning/phases/16-ai-kit-spec-extensions/16-HANDOFF.md`, because `.claude/` is gitignored.
> The cross-AI helper scripts are saved next to it in `.planning/phases/16-ai-kit-spec-extensions/cross-ai-scripts/`.

## Current State Summary

The user ran `/gsd-autonomous --to 20 --converge` for milestone v1.3 (GSD Curated Config v2, phases 16 → 20). The user required every plan to be `cross_ai: true`, so plans are reviewed and executed by an external AI.

Phase 16 (ai-kit-spec extensions) status:
- Planned via plan-review-convergence. 3 cycles; at cycle 3 the user chose "fix and execute".
- All 6 plans executed and have SUMMARY files:
  - 16-01..16-04 by the cross-AI executor (opencode `router-env/my-coding`);
  - 16-05 and 16-06 by native Haiku, because the router failed repeatedly.
- The 16-06 gate re-run passed.
- skill-judge passed at 104/120.
- Code review (`16-REVIEW.md`) found 0 critical, 4 warning, 1 info. All 5 are fixed in 99ccb98 and recorded in `16-REVIEW-FIX.md`.

The user asked to STOP after the Phase 16 review/fix, save state, commit everything, and push. The execute-phase 16 closing steps are therefore NOT done yet: goal verification, verify:post hooks and phase.complete.

## Codebase Understanding

## Architecture Overview

- **`skills/ai-kit-spec-review/ai_kit_spec/`** is the stdlib-only Python package behind the spec review and config skills:
  - `detection.py`: CLI/runtime detection and model enumeration (codex `debug models`, opencode `models --verbose`, claude alias plus catalog ids);
  - `cli.py`: fetch-model-catalog, `_apply_runtime_meta`, `schema_version` via the `_meta` key;
  - `model_catalog.py` and `config_io.py`: field types and the `_VALID_NATIVE_RUNTIME` set, which must change together;
  - `model_ranker.py`: 5 purposes plus aliases and per-purpose floors;
  - `references/ranking-weights.toml`.
- **GSD planning state** is in `.planning/`: ROADMAP.md, STATE.md, REQUIREMENTS.md, and `phases/NN-*/` with CONTEXT, RESEARCH, PLAN, SUMMARY, REVIEW and VERIFICATION files.

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| .planning/ROADMAP.md | Phase list and progress for v1.3 | Phases 17–20 still to plan and execute |
| .planning/STATE.md | GSD current-position state | Updated by gsd-tools queries |
| .planning/phases/16-ai-kit-spec-extensions/16-REVIEW.md | Code review report | status issues_found; all fixed |
| .planning/phases/16-ai-kit-spec-extensions/16-REVIEW-FIX.md | Fix report | Documents the 5 fixes and out-of-scope items |
| .planning/phases/16-ai-kit-spec-extensions/16-SKILL-JUDGE.md | skill-judge evidence | 104/120 pass |
| skills/ai-kit-spec-review/ai_kit_spec/detection.py | Runtime and model detection | Core Phase 16 code |
| skills/ai-kit-spec-review/ai_kit_spec/cli.py | Catalog fetch and runtime meta | Core Phase 16 code |
| skills/ai-kit-spec-config/SKILL.md | Config skill (skill-judge gated) | Edited in 16-01, 16-02 and the judge gate |
| tests/test_ai_kit_spec.py | 594 tests for ai_kit_spec | Must stay green |

## Key Patterns Discovered

- **Cross-AI execution** (execute-phase `cross_ai_delegation`):
  - the prompt is the plan's `<objective>` plus `<tasks>`, sent over stdin to `opencode run --model router-env/my-coding` through `gsd-tools run-with-timeout`;
  - stdout becomes the SUMMARY;
  - the helper scripts `xai_exec.sh` and `xai_finalize.sh` automate this (copies are in `cross-ai-scripts/`). They hardcode the Phase 16 paths and the `# Phase 16 Plan` heading, so adapt them per phase.
- **Isolation guard:** before any gsd-executor dispatch without a worktree, run `gsd-tools query dispatch-isolation --raw --phase N --force-isolation none` IMMEDIATELY before each dispatch.
- **Env for repo gates:** `PATH="$HOME/.local/bin:$PATH" UV_NO_SYNC=1`. Do NOT set `UV_OFFLINE=1`; it breaks `make test-integration`.

## Work Completed

## Tasks Finished

- [x] Phase 16 plan-review convergence (3 cycles, then a targeted replan)
- [x] Phase 16 plans 16-01..16-06 executed and summarized
- [x] Phase 16 gate re-run (make test and make validate constituents): passed apart from the pre-existing failures
- [x] Phase-caused ruff regression fixed (80bcac6, b407f8f)
- [x] skill-judge gate for ai-kit-spec-config (82a0c62)
- [x] Code review, with 5 findings, all fixed (1ea2085, 99ccb98, e233dc9)

## Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| skills/ai-kit-spec-review/ai_kit_spec/cli.py | Collapsed nested image_input `if` | WR-03 (SIM102) |
| skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py | Moved long comments to their own lines | WR-02 (E501) |
| skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py | Collapsed nested `if`; ternary for axis_weights | WR-04 (SIM102/SIM108) |
| tests/test_ai_kit_usage_metrics.py | Sorted imports; tidied json.dump | WR-01 (I001), IN-01 |

## Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Fix and execute at cycle-3 escalation | Another replan cycle, or accept as-is | User choice; the 8 residual findings were fixed in a targeted replan |
| Native Haiku for 16-05 and 16-06 | Keep retrying the router, or wait | User: "try again now and use native haiku if fail again" |
| Use the cross-AI executor again from Phase 17 on | Stay on Haiku | User: "consider using cross-ai next time"; fall back to Haiku only if the router fails |
| Cap the opencode review-lane wait at 1 probe + 1 retry | Long quota polling | Cycle 2 wasted about 45 minutes waiting on a quota lock |
| Fix review findings directly instead of spawning gsd-code-fixer | Spawn gsd-code-fixer | All 5 were mechanical lint fixes |

## Pending Work

## Immediate Next Steps

1. Finish execute-phase 16's closing steps, from `~/.claude/gsd-core/workflows/execute-phase.md`:
   - **verify_phase_goal:** spawn gsd-verifier (sonnet) to write `16-VERIFICATION.md`.
   - **verify:post hooks:** nyquist `validate-phase`, `secure-phase`, and `ui-review` if applicable (probably N/A: no UI).
   - **update_roadmap:** `gsd-tools query phase.complete 16`.
   - **close_phase_todos.**
2. Continue `/gsd-autonomous --from 17 --to 20 --converge` for phases 17, 18, 19 and 20:
   - discuss is already done (CONTEXT files exist);
   - plan with plan-review-convergence, with every plan `cross_ai: true`;
   - execute via the cross-AI executor.
3. Stop after Phase 20 with the "--to 20 REACHED" banner. Do NOT run milestone audit/complete unless asked.

## Blockers/Open Questions

- [ ] **router-env/my-coding is unreliable.** Errors seen:
  - "Chat admission capacity is temporarily unavailable";
  - 402 "requires an opencode API key";
  - "all targets were skipped by pre-dispatch filters";
  - "Credential gate blocked opencode-zen/...".

  Retry once, then fall back to native Haiku.
- [ ] **Claude-only or checkpoint work** in phase 19 (skill-judge, subagent RED/GREEN) and phase 20 (interactive user runs) cannot go to the cross-AI executor. Flag it or run it natively.

## Deferred Items

- **Pre-existing lint debt**, out of v1.3 scope:
  - `ai_kit_spec/dispatch.py:158` SIM105;
  - ruff and pylint findings in `tools/status-line.py` and `tools/wizard_app.py`;
  - ruff findings in `tests/test_ai_kit_spec_superpowers.py`.
- **`.pre-commit-config.yaml` ruff hook scope** does not cover `skills/ai-kit-spec-review/ai_kit_spec/*.py`. This is a candidate todo.
- **mmdc real-render test failure:** the pnpm-global mermaid-cli install is incomplete. This is an environment issue.

## Context for Resuming Agent

## Important Context

- **Hard constraints from the user:**
  - English-only artifacts, even when the user writes in Spanish.
  - No markdown pipe tables in trade-off analyses.
  - Run `/skill-judge` in code review for any phase that ships a skill.
  - Explain internals before asking the user to decide.
  - In autonomous runs, fix verifiable things without asking.
  - Never do a real `apply` of curated config on ai-kit itself during v1.3.
  - Never modify `~/.config/opencode`, `~/.gsd` or `~/.claude`.
  - Never use `git add -A` or `--no-verify`.
  - Push only with consent. The user did consent to push at this stop point.
- **The git pre-commit hook is broken:** `.git/hooks/pre-commit` points to a missing `/home/user-zero/...` venv, so commits currently run WITHOUT hooks. Run ruff and the tests manually before committing.
- **Pre-existing failures** (not phase-caused):
  - `tests.test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image`;
  - 6 pylint findings in `tools/status-line.py`.
- **`.planning/milestone.lock`** is a runtime session lock; it is intentionally left uncommitted.

## Assumptions Made

- `ui-review` does not apply to Phase 16, because it has no frontend changes.
- The workflow's code-review scope (16 files from the phase-start commit) matches `333cf04..HEAD`.

## Potential Gotchas

- **Router retry coverage:** `xai_exec.sh` retries only on "temporarily unavailable", "cooling down", "is locked" or "rate limit". The 402 billing error and the "pre-dispatch filters" error are not retried; handle them by hand.
- **Haiku executors can drift:**
  - once it deferred the required tests;
  - once it renamed a test to satisfy E501.

  Check its summaries against the actual diff.
- **The opencode reviewer** fails on very large prompts (about 263 KB). Use a compact prompt of about 18 KB.
- **The phase-dir first commit** (1550ff1) predates the pre-phase base 333cf04. The diff base for phase code is 333cf04.

## Environment State

## Tools/Services Used

- GSD gsd-core 1.14.0: `~/.claude/gsd-core/bin/gsd-tools.cjs`.
- `opencode run --model router-env/my-coding`, which is `workflow.cross_ai_command`.
- `uv` with `.venv` (textual 8.2.7 installed), plus `make test` and `make validate`.

## Active Processes

- None.

## Environment Variables

- PATH (prepend `$HOME/.local/bin`)
- UV_NO_SYNC
- CLAUDECODE (unset it when invoking opencode)

## Related Resources

- `.planning/phases/16-ai-kit-spec-extensions/16-REVIEW.md`
- `.planning/phases/16-ai-kit-spec-extensions/16-REVIEW-FIX.md`
- `.planning/phases/16-ai-kit-spec-extensions/cross-ai-scripts/`
- `~/.claude/gsd-core/workflows/execute-phase.md`, from the `verify_phase_goal` step onward
- `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md`

---

**Security Reminder**: Before finalizing, run `validate_handoff.py` to check for accidental secret exposure.

## Session Addendum — 2026-10-09 (quota-window gap coloring, opencode session)

Session run in opencode (glm-5.3-flash orchestrator) on top of this handoff's stop point.
Everything below is committed on this branch; the work is DONE and merged — next agent picks
up at the unchanged next steps at the bottom of the original handoff (phase 16 closing steps:
goal verification, verify:post hooks, phase.complete; then phases 17–20).

What this session did, in order:

1. **Quota-window coloring redesign (spec → plan → execute, superpowers flow).** Replaces the
   Phase 8.1 pace ratio (`used_percentage / elapsed_fraction`) with an ABSOLUTE gap:
   `delta = abs(used% − elapsed%)` graded against fixed inclusive bands — ≤5 GREEN,
   <11 YELLOW, ≤15 ORANGE, >15 RED. Unreliable window (missing/past `resets_at`, clock skew)
   paints the percentage WHITE with no sign; the old `1e-9` guard is gone (elapsed == 0 is a
   normal computable case). Spec: `docs/superpowers/specs/2026-10-09-statusline-quota-window-gap-design.md`;
   plan: `docs/superpowers/plans/2026-10-09-statusline-quota-window-gap.md`.
2. **Review loop (cross-AI reviewer forced to `opencode/glm-5.2` by the user).** Spec approved
   iteration 1 (3 non-blocking notes: fate of the deleted helpers, `[ramp.rate]` going inert,
   arch role-prefix). Plan took 3 iterations — real defects found: replacement code missing
   the `show_reset` marker gate, the plan's delete step would have dropped the four
   `test_window_seconds_*` parsing tests the spec mandates keeping, non-float-exact gap
   arithmetic (fixed with the remaining-percentage-first formulation), and an
   self-unsatisfiable `rg` verification gate.
3. **Execution (subagent-driven development):** commits `d23749b` (pure helpers
   `util_rate_gap`/`util_gap_color`/`util_gap_sign` + 10-test `TestRateGap`), `3ac0ae4`
   (wired into `util_rate_group_str`, render tests, README), `0a46a0c` (deleted the
   pace-ratio helpers + their ten tests, kept parsing tests under `TestWindowSeconds`),
   final whole-branch review fix `5b2011b` (README + `statusline.toml.sample` now say
   `[ramp.rate]` is parse-compat only and no longer colors quota windows; spec/plan docs
   committed — repo precedent). All tier tests green at close (unit 2673, integration 131,
   e2e 13, arch 22).
4. **Post-merge format amendment (`52def0f`), user-driven.** The `(+N)`/`(-N)` magnitude
   marker read confusingly next to the percentage (`5h: 0% (-1)`). Now the pace sign is
   glued to the displayed percentage and INVERTED from the gap direction: `+` = usage at or
   behind the window clock (under pace), `-` = usage burning faster than the clock.
   `5h: +0% (↺ 23:30)` early in a window; `5h: -60%` when 60% is used with 45% of the clock
   gone. Magnitude is carried by the color band only; terse tier stays byte-identical.
   Spec, README, and test pins updated in the same commit.
5. **Merge + workspace discipline fix.** `exercise/window-pct` was FF-merged into this branch
   (`1ccdc1e..52def0f`); `.planning/` untouched by the merge. The exercise worktree
   `.claude/worktrees/window-pct` and its branch were then deleted. The worktree had been
   created from HEAD by accident: the base workspace was parked on `gsd/v1.3-curated-config-v2`
   — this session's user correction of record is: **the base workspace stays on `main`
   (milestone-closure state); feature/GSD work lives in worktrees branched from the phase tip.**
   The base workspace is back on `main` @ `de2139c` (v1.2 closure).

Housekeeping state for the next agent (all verified, nothing lost):

- `backup/gap-coloring-52def0f`: local insurance branch pointing at this handoff's tip.
- Remotes are stale: `main` is 279 commits ahead of `origin/main`; nothing from v1.3 is
  pushed. Push (`git push origin main gsd/v1.3-curated-config-v2 backup/gap-coloring-52def0f`)
  is advised before any further surgery.
- Worktree `context-tools-manager-plan1` holds 21 UNMERGED commits (~2 months old,
  context-tools Step-0 toggle redesign; its design spec IS committed on this branch) —
  do NOT delete that worktree or branch.
- Worktree `agent-af8d0e0c2da92634f` holds exactly 1 unique commit (`ec47392`, docs-only
  Phase 15.1 halt note) — salvage by cherry-pick before deleting it.
- Branch `gsd/phase-15.1-…` is fully contained in this branch (0 unique commits; deletable).
- `.planning/milestone.lock` is untracked and stale (2026-09-24 session id) — harmless.
- Scope note: the 5 quota-gap commits are OUT of phase 16's literal plan scope. The phase 16
  verification sweep will see them on this branch; they are clearly labeled and
  cherry-pickable if they should live on their own line.
