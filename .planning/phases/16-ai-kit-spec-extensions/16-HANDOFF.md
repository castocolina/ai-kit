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
