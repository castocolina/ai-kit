---
phase: 33-one-config-design
plan: 06
subsystem: docs
tags: [toml, cross-ai-runner, retry-config, curated-config, doc-pins, skill-text]

# Dependency graph
requires:
  - phase: 33-02
    provides: "Runner reads [runner.retry] per key from .aikit/config.toml and the user config.toml"
  - phase: 33-04
    provides: "The one-time migration of workflow.cross_ai_retry and the user cross-ai.json into config.toml"
provides:
  - "Policy reference Configuration section: [runner.retry] TOML block pinned to the template CONFIG retry object, scopes, TOML subset rule, source order and migration paragraph"
  - "cross-ai SKILL.md pointer names [runner.retry] in ai-kit's config.toml"
  - "curated-config SKILL.md and runner.md retry guidance names [runner.retry] and the migration, with no hand-edit instruction for a GSD key"
affects: [33-07 (CFG-06), skill-judge loop 33 (Plan 12: ai-kit-gsd-curated-config is materially changed)]

# Actuals (#2632): chars/4 over the realized diff (spawn base dff326e .. HEAD)
actuals:
  tokens: 3394
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Doc pin to the source of truth: the TOML block under ## Configuration is compared with the rendered template CONFIG retry object, sorted keys, one key = value line each"

key-files:
  created: []
  modified:
    - skills/ai-kit-cross-ai/references/subprocess-quota-policy.md
    - skills/ai-kit-cross-ai/SKILL.md
    - skills/ai-kit-gsd-curated-config/SKILL.md
    - skills/ai-kit-gsd-curated-config/references/runner.md
    - tests/test_cross_ai_skill_text.py

key-decisions:
  - "The policy reference documents the retry table as TOML only; the JSON project block is removed, since the runner no longer reads workflow.cross_ai_retry except through the one-time migration."
  - "curated-config states that retry tuning is not a GSD key and that the runner migrates the old block; the owner-edited exception sentence is removed, so no doc tells the owner to hand-edit a GSD key."
  - "The subset paragraph names the outside-runner causes of a skipped file (unreadable table header, multi-line string, array of tables outside [lanes], invalid UTF-8) so the doc matches Plan 02's refusals (review concern C1-11)."

patterns-established:
  - "Doc-pin tests assert phrases on single physical lines where the acceptance grep is line-based (the cross_ai_retry lines must carry migrat)"

requirements-completed: [CFG-03, CFG-06]

coverage:
  - id: D1
    description: "The policy reference's ## Configuration documents [runner.retry] as a TOML block equal to the template CONFIG retry object, with scopes, the subset rule, the source order and the migration"
    requirement: "CFG-03"
    verification:
      - kind: unit
        ref: "tests/test_cross_ai_skill_text.py#PolicyContent.test_configuration_toml_matches_the_template"
        status: pass
      - kind: unit
        ref: "tests/test_cross_ai_skill_text.py#PolicyContent.test_defaults_bounds_and_the_config_files"
        status: pass
    human_judgment: false
  - id: D2
    description: "curated-config SKILL.md and runner.md name [runner.retry] and the one-time migration; neither tells the owner to hand-edit a GSD key"
    requirement: "CFG-06"
    verification:
      - kind: unit
        ref: "tests/test_cross_ai_skill_text.py#CuratedConfigPins.test_curated_docs_point_to_cross_ai_and_pin_template_eight"
        status: pass
    human_judgment: false
  - id: D3
    description: "cross-ai SKILL.md points to [runner.retry] in ai-kit's config.toml instead of workflow.cross_ai_retry (fact-only update)"
    requirement: "CFG-03"
    verification:
      - kind: unit
        ref: "tests/test_cross_ai_skill_text.py#SkillShape"
        status: pass
    human_judgment: false

# Metrics
duration: unknown (plan start time was not recorded)
completed: 2026-11-15
status: complete
plan_head_before: dff326eac0e140e654e4f47089f90c4930fe5175
plan_head_after: 0e99bd4897a0ba502a6370d11ec39fd1af97db02
commits: 2
---

# Phase 33: One config design, Plan 06 Summary

**The cross-AI policy reference, the cross-ai pointer and curated-config now document the runner's retry settings as `[runner.retry]` in ai-kit's `config.toml`, with the migration of the old GSD block, and a pin keeps the documented TOML equal to the template values.**

## Performance

- **Duration:** unknown (the plan start time was not recorded)
- **Tasks:** 2 completed, each committed
- **Files modified:** 5

## Accomplishments

- The policy reference's `## Configuration` shows the `[runner.retry]` TOML block (`base_s = 1`, `factor = 1.5`, `hard_waits_s = [600, 900, 1800]`, `max_retries = 5`, `session_resets = 1`), the scope table form, the TOML subset rule, the three sources and the migration paragraph.
- `test_configuration_toml_matches_the_template` renders the template CONFIG `retry` object and compares it with the documented block, so the docs cannot drift from the template.
- `test_defaults_bounds_and_the_config_files` pins the `.aikit/config.toml` and user `config.toml` paths, the `cross-ai.json.migrated` rename, `is skipped unread`, `not valid UTF-8` and `whose name the runner cannot read`.
- curated-config's SKILL.md and `references/runner.md` point to `[runner.retry]` and say the runner migrates an old `workflow.cross_ai_retry` block once. The "one owner-edited exception" sentence is gone.
- `rg cross_ai_retry skills/ai-kit-gsd-curated-config` now lists only two lines, and both carry `migrat`.

## Task Commits

1. **Task 1: the policy reference's configuration block is TOML and pinned to the template** - `b506f80` (docs)
2. **Task 2: curated-config's retry guidance moves to [runner.retry]** - `0e99bd4` (docs)

## Files Created/Modified

- `skills/ai-kit-cross-ai/references/subprocess-quota-policy.md` - `## Configuration` rewritten as the TOML table, scopes, subset rule, sources and migration; symlink sentence names `.aikit`.
- `skills/ai-kit-cross-ai/SKILL.md` - line 20 names the runner's retry table (`[runner.retry]` in ai-kit's `config.toml`).
- `skills/ai-kit-gsd-curated-config/SKILL.md` - retry tuning pointer (line 272) and the "owner-edited exception" paragraph (lines 363-366) replaced.
- `skills/ai-kit-gsd-curated-config/references/runner.md` - line 4 pointer and the first two sentences of `## Failure ladder` replaced.
- `tests/test_cross_ai_skill_text.py` - `_first_toml_block` and `_toml_line_value` helpers; `test_configuration_json_matches_the_template` replaced by `test_configuration_toml_matches_the_template`; `test_defaults_bounds_and_the_user_file` renamed `test_defaults_bounds_and_the_config_files` with the new pins; the `## Failure ladder` pin now asserts `[runner.retry]` and `migrates`. `_first_json_block` is deleted (no other user).

## Decisions Made

- The retry table is documented only as TOML; the JSON project block is removed.
- Retry tuning is described as not a GSD key, and the runner's migration is named, so the owner is not sent to a GSD key that `config-set` refuses.
- The subset paragraph names each outside-runner cause of a skipped file, matching Plan 02's refusals (review concern C1-11).

## Deviations from Plan

**1. [Rule 1 - Bug, self-introduced] A wrapped phrase broke the pin before the first commit**
- **Found during:** Task 1 verification (`test_defaults_bounds_and_the_config_files`).
- **Issue:** The subset paragraph wrapped `whose name the runner cannot read` across a line break, so the exact-phrase pin failed.
- **Fix:** Rewrapped that sentence so the phrase is on one physical line. Wording unchanged.
- **Files modified:** `skills/ai-kit-cross-ai/references/subprocess-quota-policy.md`
- **Verification:** `scope.py test` `tests rc: 0`, 6/6 modules.
- **Committed in:** `b506f80` (Task 1; fixed before the commit).

**2. [Rule 3 - Blocking acceptance line] Task 2 sentence split so the acceptance grep passes**
- **Found during:** Task 2 acceptance (`rg -n "cross_ai_retry" skills/ai-kit-gsd-curated-config` must list only lines that also contain `migrat`).
- **Issue:** The plan's sentence put "migrates" and `workflow.cross_ai_retry` on different physical lines, and a later wrap left the `workflow.cross_ai_retry` line without `migrat`.
- **Fix:** Reworded the curated SKILL.md paragraph into two sentences and wrapped so the line holding `workflow.cross_ai_retry` also holds `migrates`. The meaning matches the plan's sentence; the wording is split ("Retry tuning is not a GSD key: ... The runner migrates an old `workflow.cross_ai_retry` block out of the GSD config once; this skill writes neither.").
- **Files modified:** `skills/ai-kit-gsd-curated-config/SKILL.md`
- **Verification:** rg lists two lines, both with `migrat`; `scope.py test` `tests rc: 0`.
- **Committed in:** `0e99bd4` (Task 2).

**Total deviations:** 2 (1 self-introduced wrap bug fixed before commit, 1 wording split for the line-based acceptance grep). **Impact:** None on behaviour or the pinned phrases.

## Issues Encountered

- **Worktree base check trips after Task 1.** The spawn-time `worktree_branch_check` asserts HEAD equals `dff326e`; after `b506f80` it reports a base mismatch by design. I did not reset or re-home anything. For the second commit I ran the per-commit checks instead (branch in the `worktree-agent-` namespace, not detached, not a protected branch) and confirmed `dff326e` is an ancestor of HEAD.
- **Plan-start ledger not written.** `gsd-plan-head-before-33-06` was not written and the start time was not recorded. `commits` is measured with `git rev-list --count dff326e..HEAD` (2), from the base the branch check asserted at spawn.
- **Tracer gate.** Task 1 is `type="tracer"` with no `gate` attribute. Interactive mode, end-of-phase: the automated `<verify>` re-run (`scope.py test`) passed before Task 2, so execution continued.
- **Full `make test` not run in this worktree.** The plan's verification is the doc-pin modules (`scope.py test`) plus the curated-config run; the commit hooks ran the staged modules (9/9 for Task 1, 26/26 for Task 2 including 4 under uv). The full tiers were not run.
- **Judge records and digests (not edited).** `ai-kit-gsd-curated-config` changed materially, so its skill-judge record is stale until loop 33 (Plan 12). `ai-kit-cross-ai` changed fact-only, so its digest may also be stale. Judge records were not edited, per the run rules.

## Verification (run in this worktree)

| Command | Result |
| --- | --- |
| `python3 tmp/p33/06/scope.py test` (baseline, before edits) | `tests rc: 0`, 6/6 modules passed (exit 0) |
| `python3 tmp/p33/06/scope.py test` (after Task 1 edits, first run) | `tests rc: 1`: `whose name the runner cannot read` split by a wrap (deviation 1) |
| `python3 tmp/p33/06/scope.py test` (after Task 1 rewrap) | `tests rc: 0`, 6/6 modules passed (exit 0) |
| `python3 tmp/p33/06/scope.py test` (after Task 2) | `tests rc: 0`, 6/6 modules passed (exit 0) |
| `bash tmp/p33/06/extra.sh` (`AI_KIT_REFUSE_REAL_HOME=1`, `tests.test_gsd_curated_eval tests.test_curated_config_skills`) | `2/2 modules passed`, `extra rc: 0` (exit 0) |
| `rg -n "cross_ai_retry" skills/ai-kit-gsd-curated-config` | 2 lines, both contain `migrat` |
| Commit hook, `b506f80` | ruff, py-compile, staged tests 9/9 modules passed |
| Commit hook, `0e99bd4` | ruff, py-compile, staged tests 26/26 modules passed (4 under uv) |

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-33-18 (docs directing edits to GSD config) is mitigated: no text tells the owner to hand-edit a GSD key, and the template pin keeps the documented block equal to the template values.

## Next Phase Readiness

- The docs now match the runner from Plans 02 and 04 for the retry table and the migration.
- `ai-kit-gsd-curated-config` is materially changed and is judged in loop 33 (Plan 12). The `ai-kit-cross-ai` change is fact-only (D-21, not judged in loop 33).
- CFG-06 is also declared by 33-07; requirement checkboxes in `REQUIREMENTS.md` are left to the orchestrator.

---
*Phase: 33-one-config-design*
*Completed: 2026-11-15*
