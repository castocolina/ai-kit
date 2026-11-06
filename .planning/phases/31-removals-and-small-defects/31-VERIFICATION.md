---
phase: 31-removals-and-small-defects
verified: 2026-11-06T18:19:32Z
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
  - "tools/install.sh"
  - "tools/setup.py"
  - "tests/test_setup.py"
covered_digest: "v4:sha256:b1b840b6027557475417ac763b19307376c1a3221432918ca394ab259c9a6531"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 31: Removals and small defects - Verification Report

**Phase Goal:** `ai-kit-spec-execute-gsd`, `ai-kit-opencode-providers` and `mermaid-audit` are gone from the tree with every reference, nothing recommends, installs or wires rtk, and the seven known small defects are fixed, each with a regression test.
**Verified:** 2026-11-06
**Status:** passed (both orchestrator steps verified 2026-11-06; one installer defect found by step (a) and fixed in `0fcb4e2`)
**Re-verification:** Yes, close-out update after the live steps

## Observable Truths

| # | Truth (SPEC) | Status | Evidence |
|---|---|---|---|
| R1 | execute-gsd gone; router sends GSD to `/gsd-execute-phase` | VERIFIED | `git grep` of the three removed names/`ai_kit_spec_gsd\b`/`ai-kit-spec-gsd.py` outside history folders: exit 1, no hits. `git ls-files` of the three skill dirs is empty (only ignored `__pycache__` remains on disk, untracked). Router SKILL.md line 58 names `/gsd-execute-phase`; `tests.test_ai_kit_spec_execute_router` (4 tests) and `tests.test_ai_kit_spec_routing` (30) pass. |
| R2 | Adapter-only code removed | VERIFIED | `git grep PROJECT_GUIDANCE_PATH, guidance=True, --guidance-file, cross-ai-guidance.md, prior_value` in skills/tools/tests: exit 1. |
| R3 | opencode-providers gone | VERIFIED | Name search (hyphen and underscore): no hits. |
| R4 | mermaid-audit gone, markdown-to-pdf kept | VERIFIED | Name search incl. `test_mermaid_style`: no hits. Orchestrator ran the markdown-to-pdf-adjacent suites (evidence below). |
| R5 | spec-config reports stale opencode providers | VERIFIED | `provider_check.py` plus `check-providers` wired in spec-config SKILL.md line 112; "listed by opencode" label in code and tests; `tests.test_ai_kit_spec_check_providers` 20 tests pass. |
| R6 | Installs prune dead ai-kit links | VERIFIED (defect found live and fixed, see below) | `warn: removing dead ai-kit link ... (entry removed upstream)` in `tests/test_setup.py` (headless cases, neighbours, odd names); `prune_stale` is called from the install path (orchestrator's `test_install.sh` 48/0). |
| R7 | rtk not recommended/installed/wired; test enforces | VERIFIED | Whole-word case-insensitive `rtk` search outside the named exemptions: no hits; no "rtk init/install/run" text anywhere in skills/tools/README/AGENTS; no R05 in rules, no `probe_rtk`/`rtk-cursor` in tools/tests; `tests.test_banned_tool_mentions` passes (11 tests, orchestrator). "20-rule"/"20 rules" text: none left. |
| R8 | Installer uses resolved paths | VERIFIED | `_is_inside` (setup.py:1186) resolves both sides with `realpath`, compares by `commonpath` (prefix-safe), keeps the leaf unfollowed. Alias/checkout cases covered per 31-03 and `test_install.sh` 48/0; scratch-HOME install linked the 3 pi skills (4 pi links, 0 warnings). |
| R9 | pi variables described correctly | VERIFIED (code/doc and live herdr check) | SKILL.md:134, `plan_io.py:541`, `recommend.py:326`, evals line 60 carry the wording; dated correction note in `v1.3-OWNER-FOLLOWUP.md:74`. Herdr live check: see Orchestrator live steps (b). |
| R10 | 25.1 edge floor fixed; guard on current SPECs | VERIFIED | `edge_floor.py check` on the archived 25.1 SPEC: `ok:true`, 48/48, nothing missing. Guard is `tools/check_dogfood.py` (amended per SPEC note, since tests may not read `.planning/`); `tests.test_check_dogfood` 32 tests pass; `check_dogfood.py` runs exit 0. |
| R11 | goal-prompt reads `@file:` | VERIFIED | `goal_prompt.py:249-255` helper; tests cover happy path, missing file, empty path, bad JSON, prefix-not-at-start; `tests.test_ai_kit_spec_goal_prompt_cli` 49 pass. |
| R12 | routing docstring names no phase | VERIFIED | `routing.py:45-50` docstring has no "Phase"; routing tests pass. |
| R13 | Runtime lists tied to `RUNTIMES` | VERIFIED | `tests.test_runtime_list_drift` 10 tests pass. |
| R14 | AGENTS.md links no ignored file | VERIFIED | No `cli-environment` in AGENTS.md; `tests.test_agents_md_links` 5 tests pass. |
| R15 | Changed skills meet the judge bar | VERIFIED | See Skill-judge results below. |

**Score:** 15/15 truths verified (0 behavior-unverified). Truth R9's live check passed (see Orchestrator live steps).

## Skill-judge results (JDG-04; native opus xhigh, read-only, rubric v4 /125; source `tmp/phase31-exec/ledger.txt`, copied from the orchestrator's evidence)

| Skill | Rounds | Result | Bar |
|---|---|---|---|
| ai-kit-spec-execute | r1 74.4% C, 1 high (D8-1) -> fixed; r2 74.4% C, new critical D4-1 (unquoted YAML description) -> description double-quoted (verified: SKILL.md line 3 is quoted); r3 80.8% B (101/125), 0 critical, 1 high (D8-1: pre-existing detector behaviour, not phase-31 text) | Grade B | MET via grade B. Remaining findings listed for phase 32.2. |
| ai-kit-spec-config | r1 79.2% C, 1 high (D5-1, 512 lines > 500) -> check-only branch moved to `references/check-only.md` (464 lines, test pins <= 500); r2 77.6% C (97/125), 0 critical, 0 high | No high or critical; -1.6 within judge variation | MET |
| ai-kit-gsd-curated-config | 84.0% B (105/125), 0 critical, 1 high new this phase (D7-1: eval expected apply without dry-run review) | Grade B; eval fixed in 763dc68 | MET via B |
| ai-kit-project-rules-agents | Not judged (D-01; SJ-3 carried to Phase 45) | n/a | Listed as not judged, with reason |
| ai-kit-project-rules-makefile | Not judged (one count word) | n/a | Listed as not judged, with reason |
| ai-kit-usage-metrics | Not judged (unchanged) | n/a | Listed as not judged, with reason |

Evals and tests carried: ai-kit-spec-execute has `evals/evals.json` with new-shape GSD-routes-to-`/gsd-execute-phase` and superpowers cases (checked) plus `tests/test_ai_kit_spec_execute_router.py`; ai-kit-gsd-curated-config has the pi-variable eval (evals.json line 60) and the doc-contract test; ai-kit-spec-config has the line-count pin and `test_ai_kit_spec_check_providers`. I did not re-run the judge; the verdicts are the orchestrator's recorded evidence.

## Requirements Coverage

| Requirement | Plan(s) | Status | Evidence |
|---|---|---|---|
| RMV-01 | 31-01 | SATISFIED | R1, R2 |
| RMV-02 | 31-02, 31-05 | SATISFIED | R3, R5 |
| RMV-03 | 31-05 | SATISFIED | R4 |
| RMV-04 | 31-06 | SATISFIED | R7 |
| DEF-01 | 31-03, 31-04, 31-05, 31-06 | SATISFIED | R6, R8-R14 |
| JDG-04 | 31-01, 31-02, 31-05 | SATISFIED for this phase's changed skills | R15 |

All six IDs are declared in plan frontmatter and exist in REQUIREMENTS.md; no orphaned IDs. Bookkeeping, done at close-out: REQUIREMENTS.md traceability now maps JDG-04 to Phase 31 and Phase 32 (plans 31-01, 31-02 and 31-05 list it and R15 delivers it for this phase; the recurring requirement stays Pending until Phase 32), and the five IDs ROADMAP cites for Phase 31 are completed by `phase.complete`.

## Behavioral Spot-Checks (run by this verifier, `AI_KIT_REFUSE_REAL_HOME=1`)

| Check | Result |
|---|---|
| `tests.test_agents_md_links`, `test_runtime_list_drift`, `test_ai_kit_spec_check_providers`, `test_ai_kit_spec_goal_prompt_cli`, `test_check_dogfood`, `test_ai_kit_spec_execute_router`, `test_ai_kit_spec_routing` | all pass |
| `edge_floor.py check` on 25.1 SPEC | `ok:true` |
| `tools/check_dogfood.py` | exit 0 (W024 validate-health and the unguarded apply no-write guard under gsd-core 1.20.0 are warnings, unrelated to this phase) |

## Orchestrator checks (evidence copied from `tmp/phase31-close/evidence.md`)

- Scratch HOME `install --headless --skills all --dry-run`: exit 0; real install into the scratch HOME: exit 0; pi root links ai-kit-cross-ai, ai-kit-session-wake, jev-fast-decision (4 pi links), 0 "outside ai-kit" warnings.
- `git grep -n "rtk-hint" -- tests`: exit 1. Removed-name searches (opencode-providers, mermaid-audit, spec-execute-gsd names): exit 1 each.
- `uv run ... tests.test_wizard_app_1 tests.test_wizard_app_3`: exit 0 (31 + 34). `tests.test_banned_tool_mentions`: exit 0 (11). `tests.test_config_doctor`: exit 0 (78). `bash tests/test_install.sh`: exit 0 (48 passed, 0 failed).
- Final `make test` / `make pyright`: run later by the orchestrator; not part of this verdict.

## Orchestrator live steps (2026-11-06, verified)

**(a) Real-machine install** from the branch tip, `python3 tools/setup.py install --headless --skills all` (logs in `tmp/live-31/`: `dry-run.txt`, `install.txt`, `install2.txt`).

- Dry run exit 0; real run exit 0, "6 linked". pi's `~/.pi/agent/skills` now holds `ai-kit-cross-ai`, `ai-kit-session-wake` and `jev-fast-decision`, each with a SKILL.md. VERIFIED.
- **Defect found:** dead links to the three removed skills (`ai-kit-spec-execute-gsd`, `ai-kit-opencode-providers`, `mermaid-audit`) stayed in `~/.claude/skills`. Their checkout folders still existed, holding only gitignored `__pycache__`/`.pyc` bytecode left by the removal, so the links still resolved and `stale_link_candidates` did not treat them as removed upstream.
- Workaround at the time: the orchestrator removed the bytecode-only folders and re-ran the install; it printed `warn: removing dead ai-kit link skills/<name> (entry removed upstream)` for all three and the links are gone.
- **Root-cause fix `0fcb4e2`** (`fix(setup): prune skill links whose folder has no SKILL.md`): for the `skills` category a target folder without SKILL.md now counts as removed upstream (`tools/setup.py` `stale_link_candidates`; agents and commands are single files, so the plain existence check already fits them). Regression test `TestHeadlessPrune.test_bytecode_only_skill_folder_counts_as_removed` (scratch HOME and scratch kit, folder holding only `__pycache__/x.pyc`, headless install prunes the link). `tests.test_setup` 470 tests OK; `make pyright` passed; pre-commit hooks passed.

**(b) herdr pi env check (R9, D-11):** pi, in its own bash tool, ran `env | grep '^PI_' | cut -d= -f1 | sort` and printed `PI_CODING_AGENT`, `PI_MODEL`, `PI_PROVIDER`, `PI_REASONING_LEVEL`, `PI_SESSION_FILE`, `PI_SESSION_ID`. Names only were recorded, no values. `PI_PROVIDER` and `PI_MODEL` appear. The pane was closed. VERIFIED.

## Real-HOME write investigation

Real `~/.cursor/cli-config.json` was rewritten 14:02:37 -03:00. Verdict (orchestrator, metadata only): not test-caused. Every test tier runs through `tools/run_unittest_parallel.py` `baseline_env` (temp HOME, `AI_KIT_REFUSE_REAL_HOME=1`, host-config env vars stripped, host-CLI tripwire stubs first on PATH); `tools/env_matrix.py` pins a scratch HOME; `tests/test_install.sh` runs under `env -i HOME=$WORK`. No test or tool resolves the passwd home except `setup.py`'s read-only `_refuses_real_home` guard. The real Cursor CLI session (started 13:19, same version) exited at 14:02:37 and its run marker was removed at 14:02:38, consistent with a config write on exit. No cursor-agent runs now. jev home1 agreed "unsupported" at 0.40, needs_fallback, so the orchestrator decided on the evidence. No fix or guard test needed. I did not touch real configs.

## Code review

`31-REVIEW.md` (5830638): 0 critical, 1 high, 2 medium, 6 low, 5 info. Fixed: CR-01, WR-01, WR-03, WR-06 (partial), IN-01 in 1b48f0a; WR-02, WR-08 and security audit T-31-04 (RecursionError in `jsonc_read`) in 0be1acb; report in d2d8f17. Not fixed (low/info follow-ups): WR-04, WR-05, WR-06 remainder, WR-07, IN-02..IN-05.

## Prohibitions

| Prohibition | Status |
|---|---|
| R5: no `auth.json` read, no key or `apiKey` printed | Test-tier; covered by `test_ai_kit_spec_check_providers` (passes). I did not separately audit the apiKey fixture case line by line. |
| R6/R8: only dead ai-kit links inside the resolved kit dir removed | Test-tier; neighbours (foreign link, real dir, live link) cases present in `tests/test_setup.py`. |
| R7/R9: no deletion of stored usage data or real configs | Test-tier plus real-home guard; investigation above found no violation. |

## Anti-Patterns

No debt markers or stubs were found in the scanned changed files at this depth. The untracked, ignored `__pycache__` folders left inside the removed skill directories were NOT harmless: they kept the dead links alive (installer defect, fixed in `0fcb4e2`).

## Process gap and pending bookkeeping (non-blocking)

- Process gap: the fold checkpoint hooks refused `not_started` at every wave (w1, w2, w3) because unit `phase-31` was never started (`fold.py start --phase 31` was not run before planning). Not started now, by instruction.
- 31-05's orchestrator step to mark the folded todo items closed: done at close-out. The seven folded DEF-01 items in `.planning/todos/pending/2026-11-02-tooling-defects-and-skill-writing-principle-found-at-the-v1.md` are ticked; the SJ-1 item in `2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md` already carried its "closed 2026-11-03" strikethrough (SJ-2 and SJ-3 stay open).

## Human Verification

None pending. Both orchestrator steps (real-machine install, herdr pi env check) are recorded above as verified.

## Gaps Summary

No open gaps. Every SPEC requirement R1-R15 has code, test or search evidence in the tree, and both live steps passed. The one defect they surfaced (bytecode-only skill folders keeping dead links alive) is fixed in `0fcb4e2` with a regression test.

---

_Verified: 2026-11-06_
_Verifier: Claude (gsd-verifier)_
