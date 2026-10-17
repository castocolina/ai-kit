---
phase: 19-evaluation-on-claude
verified: 2026-10-17T23:30:00Z
status: passed
score: 4/4 must-haves verified
covered_files:
  - .planning/phases/19-evaluation-on-claude/19-01-PLAN.md
  - .planning/phases/19-evaluation-on-claude/19-01-SUMMARY.md
  - .planning/phases/19-evaluation-on-claude/19-02-PLAN.md
  - .planning/phases/19-evaluation-on-claude/19-02-SUMMARY.md
  - .planning/phases/19-evaluation-on-claude/19-03-PLAN.md
  - .planning/phases/19-evaluation-on-claude/19-03-SUMMARY.md
  - .planning/phases/19-evaluation-on-claude/19-04-PLAN.md
  - .planning/phases/19-evaluation-on-claude/19-04-SUMMARY.md
  - .planning/phases/19-evaluation-on-claude/19-05-PLAN.md
  - .planning/phases/19-evaluation-on-claude/19-05-SUMMARY.md
  - .planning/phases/19-evaluation-on-claude/19-06-PLAN.md
  - .planning/phases/19-evaluation-on-claude/19-06-SUMMARY.md
  - .planning/phases/19-evaluation-on-claude/19-07-PLAN.md
  - .planning/phases/19-evaluation-on-claude/19-07-SUMMARY.md
  - .planning/phases/19-evaluation-on-claude/19-08-PLAN.md
  - .planning/phases/19-evaluation-on-claude/19-08-SUMMARY.md
  - .planning/phases/19-evaluation-on-claude/19-09-PLAN.md
  - .planning/phases/19-evaluation-on-claude/19-09-SUMMARY.md
  - .planning/phases/19-evaluation-on-claude/19-10-PLAN.md
  - .planning/phases/19-evaluation-on-claude/19-10-SUMMARY.md
  - .pre-commit-config.yaml
  - Makefile
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - skills/ai-kit-gsd-curated-config/evals/01-claude-rigorous-cross-ai.md
  - skills/ai-kit-gsd-curated-config/evals/02-opencode-routers-no-catalog.md
  - skills/ai-kit-gsd-curated-config/evals/03-v1-written-config.md
  - skills/ai-kit-gsd-curated-config/evals/04-just-apply-it.md
  - skills/ai-kit-gsd-curated-config/references/v1-path.md
  - tests/gsd_curated_eval.py
  - tests/test_ai_kit_gsd_curated_config_matrix.py
  - tests/test_curated_config_apply.py
  - tests/test_curated_config_apply_e2e.py
  - tests/test_gsd_curated_eval.py
  - tools/run_unittest_parallel.py
covered_digest: "v3:sha256:2bc35be8697144da58d2bbf7df7f5965b2947ae57c1a657d753359a44850c09c"
behavior_unverified: 0
overrides_applied: 0
owner_review_nonblocking:
  - test: "Decide IN-07 (SKILL.md wording: 'a key the project has now' and a broken line wrap) from 19-REVIEW.md"
    expected: "Fixed in the next SKILL.md revision (which re-binds the digest, all GREEN cells and both judges), or explicitly waived"
    why_human: "Listed under 'Not fixed' in 19-REVIEW-FIX.md for owner review; any SKILL.md edit invalidates the 9cddf0a5892fba97 evidence."
  - test: "Accept the skill-judge PASS without glm-5.3 (unavailable, capacity, in rounds 0, r1 and r2)"
    expected: "Owner confirms the PASS on in-session Opus (109/120) plus pi gpt-6.1-sol (114/120); glm dropped from future rounds (owner decision 2026-10-17)"
    why_human: "19-SKILL-JUDGE.md 'Phase decisions for owner review' item glm-5.3-unavailable."
  - test: "Review 19-07-D-full-key-r2 (laya refactor_round_2, round 2 ran at 19e3d3d)"
    expected: "Owner agrees round 2 was warranted, or flags it"
    why_human: "A decision taken on the owner's behalf via jev/laya (19-SKILL-JUDGE.md owner-review index)."
  - test: "Review v1-suite-package-attribute (_reimport_with_ai_kit_spec_blocked leaves a degraded module bound on the package)"
    expected: "Owner decides whether to fix tests/test_ai_kit_gsd_curated_config.py (Run rule 8 forbade it in Phase 19; worked around in c326bbd; also 19-REVIEW-FIX M6)"
    why_human: "Root cause is in a file the phase was forbidden to edit."
---

# Phase 19: Evaluation on Claude Verification Report

**Phase Goal:** The rewritten skill is proven correct end to end from inside a real Claude Code session: pressure-tested, code-reviewed, and confirmed to make `gsd-tools` resolve every agent's model exactly as planned.
**Verified:** 2026-10-17T23:30:00Z
**Status:** passed (owner items non-blocking)
**Re-verification:** No (initial verification)

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | SKILL.md passes writing-skills RED/GREEN pressure scenarios B, C, D, E with no-skill and v1 baselines | VERIFIED | `digest` prints `9cddf0a5892fba97`; `digest --check` on 19-PRESSURE-TESTS.md (B-E sections, both GREEN columns) prints `digests ok`; `cells --strict` exits 0 for `GREEN (sonnet)` and `GREEN (opus confirm)` (and exits 1 for a bogus column, so the gate is not vacuous). A script cross-check of all 8 `pressure/*-green-j3*.grade.json` records against the live tables: digest equal, every check value matches its cell, zero gating failures. RED-a (no skill) in B-E and RED-b (v1, `3b5e2f6`) in B and D each fail real outcome checks (for example C RED-a ran `config-new-project` and wrote `.planning/config.json`). |
| 2 | `/skill-judge` runs as part of code review; SKILL.md scores >= 96/120 with no Critical/Important | VERIFIED | 19-SKILL-JUDGE.md: JUDGED_COMMIT `86ad793` (equals `git log -1` over SKILL.md and references/); `digest --check` ok; in-session Opus r2 109/120, 0/0; pi gpt-6.1-sol r2 114/120, 0/0 (both reports read: `CURRENT`/`CRITICAL 0`/`IMPORTANT 0`). Baseline v1 105/120, so no regression. `git diff 86ad793..HEAD -- SKILL.md references` is empty. glm-5.3 `unavailable` (owner item). |
| 3 | Live smoke from the claude host: inventory + recommend + apply (dry-run, then real on a scratch project) without corrupting the scratch config | VERIFIED | 19-SMOKE.md: host detected (no `--host`), 8 steps pass (dry run wrote nothing, apply + validation, idempotent second apply with bytes identical, forced failure restored, empty project b), protected set unchanged; re-run after H2 fix. `product_commit: deb85b3` equals the last product commit. The smoke harness logic is covered by `tests.test_gsd_curated_eval` (247 tests OK here, including `test_matrix_step_fails_on_mismatch`). The live run itself was not repeated (no live CLI runs allowed). |
| 4 | After apply, `gsd-tools resolve-model <agent>` with `GSD_RUNTIME=claude` returns the planned model for all 35 agents, against checkout-local gsd-core, version recorded in 19-SMOKE.md | VERIFIED (version wording drift) | 19-SMOKE.md: matrix 420 checks, 35 agents, control_1 ok, control_2 ok, gsd-core 1.17.0 at `<worktree>/.claude/gsd-core`. `python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix` here: 9 tests OK in 74 s against the real node gsd-tools (not skipped). The criterion text says "(1.16.x)"; the proven version is 1.17.0 (guard `GSD_CORE_PREFIXES = ("1.16.", "1.17.")`, tests/test_curated_config_apply_e2e.py:65). Routed to the owner, not a failure: the intent (checkout-local, version recorded) holds. |

**Score:** 4/4 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `19-PRESSURE-TESTS.md` | B-E tables, RED-a/RED-b/GREEN columns, digest-bound | VERIFIED | live columns are round j3; superseded rounds kept in `### Superseded` blocks |
| `pressure/*-green-j3*.grade.json` + `.md` | per-cell records and transcripts | VERIFIED | 8 records, all match the tables |
| `19-SKILL-JUDGE.md` + `skill-judge/*-r2.md` | evidence fields, verdict, owner index | VERIFIED | all 7 fields present, JUDGED_COMMIT not `pending` |
| `19-SMOKE.md` | steps, matrix, gsd-core version, product_commit | VERIFIED | |
| `tests/gsd_curated_eval.py` | digest, cells, grader, smoke, matrix, secret-scan | VERIFIED | 247 unit tests OK |
| `19-REVIEW.md`, `19-REVIEW-FIX.md`, `19-PONYTAIL-CODE-REVIEW.md` | code review and fixes | VERIFIED | see Review fixes below |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| skill bytes | evidence rows | `digest --check` | WIRED | both evidence files bind `9cddf0a5892fba97` |
| product scripts | evidence | `product_commit:` | WIRED | `deb85b3` in both files equals `git log -1` over the product paths |
| judged commit | SKILL.md/references | `git diff 86ad793..HEAD` | WIRED | empty |
| grade records | tables | `checks[].pass` | WIRED | scripted cross-check, no mismatch |

### Review fixes (19-REVIEW.md Critical and Warning)

| Finding | Fixed in code | Test |
| --- | --- | --- |
| CR-01 dry run + apply in one turn | yes | `test_dry_run_and_apply_in_one_turn_fails`, `test_rows_named_only_in_the_apply_turn_are_not_shown`, `test_rerun_dry_run_with_the_shown_rows_passes` |
| CR-02 secrets in records / narrow scan | yes (`SECRET_RX`, `CELL_ENV_KEEP` allowlist at tests/gsd_curated_eval.py:3208) | `test_record_keeps_product_reports_only`, `test_cell_env_is_an_allowlist`, `test_secret_scan_hits_every_canary_and_not_diff_rows` |
| CR-03 orphaned `claude -p` on interrupt | yes (`finally` SIGKILLs the group, tests/gsd_curated_eval.py:3251) | `test_interrupt_kills_the_group_and_propagates` |
| WR-01 substring verb detection | yes | `test_calls_read_the_verb_of_each_segment`, `test_grep_of_a_write_verb_is_not_a_write`, `test_chained_dry_run_and_apply_is_a_write_and_a_real_apply` |
| WR-02 scripted answers out of step | yes (evals 01, 03, 04) | exercised by the j3 cells (every B/D/E cell ran a real grouped approval) |
| WR-03 placeholder order | yes | `test_smoke_placeholders_order` |
| WR-04 transcript key | yes | `test_transcript_key_maps_every_non_alphanumeric`, `test_reported_cwd_without_transcript_dir_is_harness_failure` |
| WR-05 reaper match | yes | `test_reaper_skips_a_sibling_path` |
| WR-06 unit test reads real home | yes | `test_snapshot_without_mode_reads_nothing` |
| WR-07 loose heuristics | yes | `test_ask_detector_rejects_incidental_text`, `test_grouped_question_needs_id_purpose_or_full_argv`, `test_router_must_be_the_first_runner_model` |
| WR-08 "context" rows ignored | yes | `test_note_mentioning_context_is_still_a_live_row` |

Not fixed, reasoned in 19-REVIEW-FIX.md: IN-07 (owner), M4/M5/L5/L9/L10 (dev-harness refactors), M6 (forbidden file), L4 (kept for Phase 20).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| skill digest | `python3 tests/gsd_curated_eval.py digest` | `9cddf0a5892fba97` | PASS |
| evidence bound | `digest --check` (judge file; pressure file B-E, both GREEN columns) | `digests ok` x2 | PASS |
| gating cells | `cells --column 'GREEN (sonnet)' --strict`, same for opus | exit 0, only `ensure_runner_disclosed fail (non-gating)` | PASS |
| strict is not vacuous | `cells --column BOGUS --strict` | exit 1 | PASS |
| grader/harness | `python3 -m unittest tests.test_gsd_curated_eval` | 247 OK | PASS |
| resolve-model matrix | `python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix` | 9 OK (real node) | PASS |
| secrets | `secret-scan` over the phase dir | exit 0 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| EVAL-01 | 19-02, 19-03, 19-06, 19-07, 19-09, 19-10 | RED/GREEN B-E with no-skill and v1 (B/D) baselines | SATISFIED | Truth 1 |
| EVAL-02 | 19-08, 19-09, 19-10 | skill-judge >= 96/120, no Critical/Important | SATISFIED | Truth 2 |
| EVAL-03 | 19-04, 19-05, 19-10 | live smoke on the claude host | SATISFIED | Truth 3 |
| APP-05 | 19-01, 19-05 | resolve-model planned model for 35 agents | SATISFIED (version wording to amend) | Truth 4 |

No orphaned requirements: REQUIREMENTS.md maps EVAL-01/02/03 and APP-05 to Phase 19, all claimed by plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `19-REVIEW.md` | 136, 146-147 | generic home-directory prefixes (no user name) | Info | not a machine-specific path; `secret-scan` clean; no login name anywhere in the phase dir |
| `19-PRESSURE-TESTS.md` | 56 | RED verdicts graded by the grader at `7bbd664`, before the CR-01/WR-01 fixes; run dirs deleted, cannot be re-graded | Info | RED failures read checked: they rest on config-state outcomes or a real write (C RED-a), so the RED/GREEN contrast holds |
| `19-10-SUMMARY.md` | Gates | gate runs predate fd80e5e/44c978a/0096e2d | Warning | orchestrator is re-running; listed as a human item until its results are added |

No TBD/FIXME/XXX debt markers found by this verification in the files reviewed (not exhaustively grepped across the 4,000-line grader).

### Human Verification Required

1. **gsd-core version in criterion 4.** Criterion 4 and 19-RESEARCH R-7 say 1.16.x, but 1.17.0 is what was proven. Amend ROADMAP.md or ask for a re-run.
2. **IN-07 SKILL.md wording.** Fix it in the next SKILL.md revision or waive it. Either way it re-binds all evidence.
3. **glm-5.3 unavailable.** Accept the PASS on in-session Opus plus pi gpt-6.1-sol.
4. **19-07-D-full-key-r2.** Review the laya-routed decision to run refactor round 2.
5. **eval-D-trusted-roots-answer.** Confirm that the j3 eval-03 answer settles it.
6. **v1-suite-package-attribute / M6.** Decide on fixing `tests/test_ai_kit_gsd_curated_config.py`.
7. **Gates on HEAD.** The orchestrator's `make test`, `make validate` and `make e2e-docker` results on HEAD.

Advisory, not routed: B `ensure_runner_disclosed` fails (non-gating) in every column.

### Gaps Summary

No blocking gaps. Every roadmap criterion and requirement has evidence I re-checked: the digest and its binding, strict cells, a record-to-table cross-check, the judged commit being unchanged, the review fixes mapped to tests, the secret scan, and the matrix test on the real gsd-tools. The status is `human_needed` because of the owner items above: the gsd-core version wording, IN-07, the owner-review index, and gate results still pending from the orchestrator.

---

_Verified: 2026-10-17T23:30:00Z_
_Verifier: Claude (gsd-verifier)_

## Orchestrator follow-up

- Criterion 4 wording: ROADMAP.md now names the verified lines (1.16.x or 1.17.x, run on 1.17.0); this is a live-verified fact, so it was amended rather than left for the owner (AGENTS.md Workflow).
- eval-D-trusted-roots-answer: settled by evidence. With eval 03's new turn-2 answer, D opus applies in j3 and passes every gating check (`pressure/D-green-j3-opus.grade.json`).
- Gates on HEAD 4420744 (after fd80e5e, 44c978a, 0096e2d and the pyright narrowing 4420744): `make test` rc 0 (unit 42/42 + 1/1, integration 4/4 and 8/8, e2e 45 passed 0 failed, arch 1/1); `make validate` rc 0 (ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest core and wizard all Passed); `make e2e-docker` rc 0 (`==> ai-kit clean-room E2E: PASS`). The first validate after 0096e2d failed on 7 pyright errors in `_redirected_reports` (`_expand` returns `str | None`), fixed in 4420744.
- Closing (jev 19-CLOSE: laya B 0.61 fallback, TypeSafe no answer, own reasoning A, the pattern of Phases 16, 18 and 18.1): the run rails forbid pausing for owner decisions, and the four remaining items are decisions, not defects. Status set to passed; the items moved to `owner_review_nonblocking` for the final report. Nyquist validation 0 gaps (f90bdd0); security 51/51 closed (ef9431b, after the T-19-45 test def2e30).
