---
phase: 31-removals-and-small-defects
verified: 2026-11-07T12:00:00Z
status: passed
score: 15/15 must-haves verified
covered_files:
  - ".planning/phases/31-removals-and-small-defects/31-01-PLAN.md"
  - ".planning/phases/31-removals-and-small-defects/31-01-SUMMARY.md"
  - ".planning/phases/31-removals-and-small-defects/31-02-PLAN.md"
  - ".planning/phases/31-removals-and-small-defects/31-02-SUMMARY.md"
  - ".planning/phases/31-removals-and-small-defects/31-03-PLAN.md"
  - ".planning/phases/31-removals-and-small-defects/31-03-SUMMARY.md"
  - ".planning/phases/31-removals-and-small-defects/31-04-PLAN.md"
  - ".planning/phases/31-removals-and-small-defects/31-04-SUMMARY.md"
  - ".planning/phases/31-removals-and-small-defects/31-05-PLAN.md"
  - ".planning/phases/31-removals-and-small-defects/31-05-SUMMARY.md"
  - ".planning/phases/31-removals-and-small-defects/31-06-PLAN.md"
  - ".planning/phases/31-removals-and-small-defects/31-06-SUMMARY.md"
  - "skills/ai-kit-spec-execute/SKILL.md"
  - "skills/ai-kit-spec-review/ai_kit_spec/provider_check.py"
  - "tests/test_banned_tool_mentions.py"
  - "tests/test_setup.py"
  - "tools/install.sh"
  - "tools/setup.py"
covered_digest: "v4:sha256:32f90ed6fa8ed5a49adf2361630f915f2be33e932cd75333585060cfdc44cded"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 15/15
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 31: Removals and small defects - Verification Report

**Phase Goal:** `ai-kit-spec-execute-gsd`, `ai-kit-opencode-providers` and `mermaid-audit` are gone from the tree with every reference, nothing recommends, installs or wires rtk, and the seven known small defects are fixed, each with a regression test.
**Verified:** 2026-11-07 (against main tip 7077c12)
**Status:** passed
**Re-verification:** Yes, after the post-31 commits (guard rule gsd-core >= 1.16, commit-fold re-discuss, wizard/setup changes, project-rules-docker skill, SUMMARY frontmatter). Prior live evidence from 2026-11-06 is kept; code and test claims were re-checked against the current tree.

## Observable Truths

| # | Truth (SPEC) | Status | Evidence |
|---|---|---|---|
| R1 | execute-gsd gone; router sends GSD to `/gsd-execute-phase` | VERIFIED | `git grep` of the three removed names, `ai_kit_spec_gsd\b` and `ai-kit-spec-gsd.py` outside `.planning` finds only historical PRDs and superpowers plans under `docs/prds/` and `docs/superpowers/plans/` (history folders); `git ls-files` of the three skill dirs is empty. `tests.test_ai_kit_spec_execute_router` (4) and `tests.test_ai_kit_spec_routing` (30) pass. |
| R2 | Adapter-only code removed | VERIFIED | `git grep PROJECT_GUIDANCE_PATH, guidance=True, --guidance-file, cross-ai-guidance.md, prior_value` in skills/tools/tests: no hits. |
| R3 | opencode-providers gone | VERIFIED | No hits outside the history PRDs listed in R1. |
| R4 | mermaid-audit gone, markdown-to-pdf kept | VERIFIED | No hits outside the history PRD/plan in R1; `git ls-files skills/mermaid-audit` empty. |
| R5 | spec-config reports stale opencode providers | VERIFIED | `provider_check.py` plus `check-providers` wired in spec-config SKILL.md; `tests.test_ai_kit_spec_check_providers` 20 tests pass. |
| R6 | Installs prune dead ai-kit links | VERIFIED | The production install path is `stale_link_candidates` (tools/setup.py:1492), `apply_stale_prune` (1513) and `_headless_prune_roots` (1562, called at 4879; also `apply_stale_prune` at 4218/4220 and `stale_link_candidates` at 4306/4313). `prune_stale` (1539) has test callers only. Regression cases in `tests/test_setup.py` (including `TestHeadlessPrune.test_bytecode_only_skill_folder_counts_as_removed`); `tests.test_setup` 481 tests pass. |
| R7 | rtk not recommended/installed/wired; test enforces | VERIFIED | Whole-word `rtk` search over skills/tools/tests/README/AGENTS hits only `ai-kit-usage-metrics` (its own log-capture source, a named exemption); no `rtk-hint` in tests; no "20-rule"/"20 rules" text. `tests.test_banned_tool_mentions` passes (11). |
| R8 | Installer uses resolved paths (Cursor `/var/home` alias, DEF-01) | VERIFIED (unit-tested; no live Cursor re-check recorded) | `_is_inside` (tools/setup.py:1211) resolves with realpath and compares by commonpath. Alias cases are covered in `tests/test_setup.py` and `tests/test_install.sh` (48/0 on 2026-11-06). Scratch-HOME install linked the 3 pi skills. No live Cursor session re-check was recorded, so this rests on unit and installer tests. |
| R9 | pi variables described correctly | VERIFIED | SKILL.md, `plan_io.py`, `recommend.py` and evals carry the wording; dated correction in `v1.3-OWNER-FOLLOWUP.md`; herdr live check (2026-11-06) printed `PI_PROVIDER` and `PI_MODEL` names only. |
| R10 | 25.1 edge floor fixed; guard on current SPECs | VERIFIED | `tests.test_check_dogfood` 32 tests pass; `tools/check_dogfood.py` is the guard (SPEC note: tests may not read `.planning/`). |
| R11 | goal-prompt reads `@file:` | VERIFIED | `tests.test_ai_kit_spec_goal_prompt_cli` 49 pass. |
| R12 | routing docstring names no phase | VERIFIED | Routing tests pass (30). |
| R13 | Runtime lists tied to `RUNTIMES` | VERIFIED | `tests.test_runtime_list_drift` 10 pass. |
| R14 | AGENTS.md links no ignored file | VERIFIED | No `cli-environment` in AGENTS.md; `tests.test_agents_md_links` 5 pass. |
| R15 | Changed skills meet the judge bar | VERIFIED | See Skill-judge results below. |

**Score:** 15/15 truths verified (0 behavior-unverified).

## Skill-judge results (JDG-04 share for phase 31; rubric v4 /125)

| Skill | Rounds | Result | Bar |
|---|---|---|---|
| ai-kit-spec-execute | r1 74.4% C, 1 high -> fixed; r2 74.4% C, critical D4-1 (unquoted YAML description) -> double-quoted; r3 80.8% B (101/125), 0 critical, 1 high (D8-1, pre-existing detector behaviour) | Grade B | MET via grade B. Remaining findings go to phase 32.2. |
| ai-kit-spec-config | r1 79.2% C, 1 high (512 lines > 500) -> check-only branch moved to `references/check-only.md`; r2 77.6% C (97/125), 0 critical, 0 high | No high or critical | MET |
| ai-kit-gsd-curated-config | 84.0% B (105/125), 0 critical, 1 high (eval expected apply without dry-run) | Grade B; eval fixed in 763dc68 | MET via B |
| ai-kit-project-rules-agents / -makefile / ai-kit-usage-metrics | Not judged in phase 31 (D-01, one count word, unchanged) | n/a | Listed as not judged, with reason |

Judge results recorded after phase 31 (orchestrator-supplied evidence, not re-run here): `ai-kit-commit-fold` 105/125 grade B, 0 critical/high (`tmp/judge-close/`); project-rules agents 95, cicd 90, docker 93 of 125, all 0 critical/high (`tmp/judge-rules/` and `tmp/judge-rules/round2/`). These belong to later phases and are noted for context only. I did not re-run the judge.

## Requirements Coverage

| Requirement | Plan(s) | Status | Evidence |
|---|---|---|---|
| RMV-01 | 31-01 | SATISFIED | R1, R2 |
| RMV-02 | 31-02, 31-05 | SATISFIED | R3, R5 |
| RMV-03 | 31-05 | SATISFIED | R4 |
| RMV-04 | 31-06 | SATISFIED | R7 |
| DEF-01 | 31-03, 31-04, 31-05, 31-06 | SATISFIED | R6, R8-R14 |
| JDG-04 | 31-01, 31-02, 31-05 | SATISFIED for this phase's changed skills | R15 |

All six IDs are declared in plan frontmatter and exist in REQUIREMENTS.md; no orphaned IDs. The recurring JDG-04 stays Pending until Phase 32.

## Behavioral Spot-Checks (run by this verifier, `AI_KIT_REFUSE_REAL_HOME=1`)

`python3 tools/run_unittest_parallel.py tests.test_agents_md_links tests.test_runtime_list_drift tests.test_ai_kit_spec_check_providers tests.test_ai_kit_spec_goal_prompt_cli tests.test_check_dogfood tests.test_ai_kit_spec_execute_router tests.test_ai_kit_spec_routing tests.test_banned_tool_mentions tests.test_setup`: 9/9 modules passed (4, 5, 10, 30, 20, 11, 32, 49 and 481 tests). Not re-run this round: `tests/test_install.sh`, the Textual wizard suites and `tests.test_config_doctor` (2026-11-06: 48/0, 31+34, 78).

## Live evidence kept from 2026-11-06

- **Real-machine install** (`python3 tools/setup.py install --headless --skills all`, logs in `tmp/live-31/`): exit 0, 6 linked; pi skills dir holds `ai-kit-cross-ai`, `ai-kit-session-wake`, `jev-fast-decision`. Found one defect: dead links to the three removed skills survived because their bytecode-only folders still resolved. Fixed by the root-cause change (`fix(setup): prune skill links whose folder has no SKILL.md`), now commit `e590afd` on main (it was `0fcb4e2` before the fold), with regression test `test_bytecode_only_skill_folder_counts_as_removed`.
- **herdr pi env check (R9):** names only recorded; `PI_PROVIDER` and `PI_MODEL` present.
- **Real-HOME write investigation:** the real `~/.cursor/cli-config.json` rewrite was judged not test-caused (all tiers run in a temp HOME with `AI_KIT_REFUSE_REAL_HOME=1`); no fix needed.

## Code review

`31-REVIEW.md`: 0 critical, 1 high, 2 medium, 6 low, 5 info. Fixed: CR-01, WR-01, WR-02, WR-03, WR-06 (partial), WR-08, IN-01 and security item T-31-04. Open low/info follow-ups: WR-04, WR-05, WR-06 remainder, WR-07, IN-02..IN-05.

## Prohibitions

| Prohibition | Status |
|---|---|
| R5: no `auth.json` read, no key or `apiKey` printed | Test-tier; `test_ai_kit_spec_check_providers` passes. Not audited fixture by fixture. |
| R6/R8: only dead ai-kit links inside the resolved kit dir removed | Test-tier; neighbour cases (foreign link, real dir, live link) present in `tests/test_setup.py`; pass. |
| R7/R9: no deletion of stored usage data or real configs | Test-tier plus real-home guard; no violation found. |

## Anti-Patterns

No debt markers or stubs found in the covered changed files. Post-31 commits touching `tools/setup.py` and `tests/test_setup.py` (wizard/setup changes) did not regress any phase 31 behavior: `tests.test_setup` is green at 481 tests.

## Process gap (non-blocking)

The fold checkpoint hooks refused `not_started` at every wave because unit `phase-31` was never started (`fold.py start --phase 31` was not run before planning). Unchanged.

## Human Verification

None pending. Note only: the Cursor `/var/home` alias fix (R8/DEF-01) has unit and installer-test coverage but no recorded live Cursor re-check.

## Gaps Summary

No open gaps. Every SPEC requirement R1-R15 has code, test or search evidence against the current tree.

---

_Verified: 2026-11-07_
_Verifier: Claude (gsd-verifier)_
