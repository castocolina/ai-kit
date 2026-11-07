---
phase: 31-removals-and-small-defects
plan: 05
subsystem: skills
tags: [removal, ai-kit-opencode-providers, mermaid-audit, pi, readme]
requires: ["31-01", "31-02", "31-03", "31-04"]
provides:
  - "ai-kit-opencode-providers and mermaid-audit removed end to end"
  - "docstrings name no removed skill; curated-config describes pi's session variables as pi sets them"
affects: [README.md, ai-kit-gsd-curated-config, markdown-to-pdf]
requirements-completed: [RMV-02, RMV-03, DEF-01]
completed: 2026-11-06
status: complete
---

# Phase 31 Plan 05: Removals, README and pi wording Summary

**Removed `ai-kit-opencode-providers` and `mermaid-audit` end to end, reworded every origin and docstring reference to them and to the removed GSD adapter, and made curated-config describe pi's session variables as pi 1.3.0 really sets them.**

## Plan

- Plan id: 31-05 (wave 2, depends on 31-01 to 31-04)
- Base: `c0717d773c53273c7e7c057a15d262b21e1f7bd6` (recorded in `tmp/p31/05/base_sha`)
- Requirements: RMV-02, RMV-03, DEF-01, JDG-04

## Commits

| Short sha | Subject |
|---|---|
| 1f4b4eb | refactor(31-05): remove ai-kit-opencode-providers; spec-config reports stale providers |
| 884f68e | test(31-05): drop runtime superset checks that the drift test replaced |
| 5afea30 | refactor(31-05): remove mermaid-audit; markdown-to-pdf keeps its renderer |
| 87a2739 | docs(31-05): docstrings name no removed GSD adapter |
| e6bc2fc | docs(31-05): README says a bare --headless run only prunes dead ai-kit links |
| 43b16fc | docs(31-05): curated-config says pi variables exist only in the agent's bash tool; new-shape evals |

Every commit ran the pre-commit hooks (no `--no-verify`). The staged-tests hook passed on each commit.

## What changed

- **Task 1 (providers removal):** `git rm -r` of `skills/ai-kit-opencode-providers/` and `tests/test_ai_kit_opencode_providers.py`. Removed the `pyproject.toml` extraPaths entry, the `test_gate_scope.py` alternative, the README row and the `REWRITTEN` entry in `test_ai_kit_spec_runtimes_table.py` (the step-0 guard `grep -c 'REWRITTEN\[:4\]'` printed 0). Origin comments in `tools/config_doctor_readers.py` (4), `tools/config_doctor_appliers.py` (2), `tools/setup.py`, the usage-metrics `paths.py` and `raw_store.py` now name no deleted file; the readers comments name `skills/ai-kit-spec-review/ai_kit_spec/jsonc_read.py` as the drift-tested read-only copy. Code is unchanged.
- **Task 1 step 5 (R13):** removed `test_runner_template_keys_use_table_ids` and the two `RUNNER_IDS` lines in `test_curated_config_registries_use_table_ids`. `tests/test_runtime_list_drift.py` covers those registries.
- **Task 2 (mermaid-audit):** `git rm -r` of `skills/mermaid-audit/` and `tests/test_mermaid_style.py`. `pyproject.toml` extraPaths (2 entries), README row and the plugin.json clause removed (`.claude-plugin/plugin.json` description now reads "... a LibCST refactor helper, and a responsive status line."). `render_mermaid.py` docstring only; `git diff --stat c0717d7..HEAD -- skills/markdown-to-pdf` lists only that file (3 insertions, 6 deletions, docstring). `tests/test_run_unittest_parallel.py` samples `tests.test_ai_kit_spec_execute_router` instead of `tests.test_mermaid_style`.
- **Task 2 step 5 (R1 completion):** seven docstring or comment rewordings (`cross_ai_build.py`, `model_detect.py`, `tests/test_ai_kit_gsd_curated_config.py`, `ai-kit-session-wake.py`, superpowers `cli.py`, `dispatch_injection.py`, `dispatch_guidance.py`). Code unchanged. `gsd_tools.py:11` untouched (kept module name).
- **Task 2 step 6 (A10):** the two README sentences about bare `--headless` now say a bare run only removes dead ai-kit links. `grep -c "only removes dead ai-kit links" README.md` = 2; `pure no-op` = 0.
- **Task 3 (R9 and R15 inputs):** SKILL.md steer bullet, `recommend.py` unset message and `plan_io.py` message now say pi sets `PI_PROVIDER` and `PI_MODEL` only for commands the pi agent runs through its own bash tool, not for `!` commands or RPC bash. Dated correction notes added to the Phase 22 guide (S2 section) and `v1.3-OWNER-FOLLOWUP.md`; the `tests/fixtures/archived` copy is untouched. New class `TestPiSessionVariableWording` in `tests/test_curated_config_recommend.py`. New `skills/ai-kit-gsd-curated-config/evals/evals.json` (6 evals, ids as specified).

## Acceptance checks (run on the final HEAD before this summary)

| Check | Result |
|---|---|
| `git grep` opencode-providers names, outside `.planning`, `docs/prds`, `docs/superpowers`, `tests/fixtures/archived` | no hits |
| `git grep -E 'mermaid-audit\|mermaid_audit\|test_mermaid_style'` (same exclusions) | no hits |
| `git grep -P 'ai-kit-spec-execute-gsd\|ai_kit_spec_gsd\b\|ai-kit-spec-gsd\.py'` (same exclusions) | no hits (R1 complete) |
| `grep -c 'def test_runner_template_keys_use_table_ids'` | 0 (baseline 1) |
| `grep -c 'jsonc_read.py' tools/config_doctor_readers.py` | 4 (at least 1) |
| `grep -c 'pure no-op' README.md` | 0 |
| `grep -c 'only removes dead ai-kit links' README.md` | 2 |
| plugin.json description mentions an auditor | False |
| `git diff --stat c0717d7..HEAD -- skills/markdown-to-pdf` | only `render_mermaid.py` |
| `inside the pi session` / `inside a pi session` in `skills/ai-kit-gsd-curated-config` | no hits (baseline 3 files) |
| `Correction (2026-11-06, Phase 31)` in `v1.3-OWNER-FOLLOWUP.md` | 1 |
| curated-config `evals.json` eval count | 6 |

## Test runs

- Targeted runner runs after each task, all `ok`: `tests.test_ai_kit_spec_runtimes_table`, `tests.test_gate_scope`, `tests.test_ai_kit_spec_check_providers`, `tests.test_ai_kit_spec_jsonc_read`, `tests.test_runtime_list_drift`, `tests.test_ai_kit_usage_metrics`, `tests.test_setup` (466 tests), `tests.test_config_doctor` (uv, 83 tests), `tests.test_markdown_to_pdf`, `tests.test_run_unittest_parallel`, `tests.test_arch`, `tests.test_curated_config_recommend` (139 tests), `tests.test_curated_config_plan_edit`, `tests.test_skill_evals_shape`, `tests.test_ai_kit_gsd_curated_config`.
- Sample module for the runner (review A19): `tests.test_ai_kit_spec_execute_router` ran in `ok in 0.0s` (4 tests).
- `AI_KIT_REFUSE_REAL_HOME=1 make pyright`: passed.
- `scope.py test` (the one `make test` of this plan): see the "Make test" section below.

## Make test

`AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/p31/05/scope.py test` exited 0 (the `make test` exit code is 0; `tests/test_install.sh` reported 48 passed, 0 failed).

Module counts per runner line, in the order the runner printed them: 98/98 (unit), 1/1 (unit-uv), 8/8 (integration), 25/25 (e2e), 1/1 (arch). The tier mapping follows the Makefile order.

## Self-Check

- Commit presence: all six commits listed above are ancestors of HEAD.
- Files: `tmp/p31/05/scope.py`, `tmp/p31/05/base_sha`, `skills/ai-kit-gsd-curated-config/evals/evals.json`, `skills/ai-kit-gsd-curated-config/evals/trigger-queries.json`, `skills/ai-kit-gsd-curated-config/evals/files/v1-project/.planning/config.json` exist. The two removed skill folders are absent.
- Acceptance checks above all match the plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `tests/test_setup.py` dead-name fixtures**
- **Found during:** Task 1 acceptance search
- **Issue:** `_KIT_IGNORE`, `_DEAD_NAMES` and three `mermaid-audit` assertions in `tests/test_setup.py` name the removed skills. The plan's R1, R3 and R4 searches cover `tests/`, so they could not print nothing.
- **Fix:** `_KIT_IGNORE` keeps only `__pycache__` (entries removed in place). The dead-link prune fixture uses three synthetic names, `ai-kit-retired-alpha`, `ai-kit-retired-beta`, `ai-kit-retired-gamma`, which no kit skill uses. The three literal `mermaid-audit` checks now use `ai-kit-retired-gamma`. The prune behaviour and its assertions are unchanged.
- **Files:** `tests/test_setup.py` (not in the plan's `files_modified`)
- **Commit:** 1f4b4eb

**2. [Rule 3 - Blocking] `skills/ai-kit-spec-review/ai_kit_spec/provider_check.py` docstring**
- **Found during:** Task 1 acceptance search
- **Issue:** a docstring named the deleted providers skill. The file is not in `files_modified`.
- **Fix:** docstring reworded to "the retired opencode-providers scan". Code unchanged.
- **Commit:** 1f4b4eb

**3. [Drift] `tools/setup.py` origin comment**
- **Issue:** the plan said `:~1881`; after 30.x drift the comment sits at `_atomic_write_json` (~2017). Located by content.
- **Fix:** comment reworded to name no deleted file.
- **Commit:** 1f4b4eb

**4. [Rule 3 - Blocking] curated-config eval fixtures for `test_skill_evals_shape`**
- **Issue:** the plan says `files: []` for every new eval. The existing shape test requires `evals/trigger-queries.json` (16 to 24 queries, 8 to 12 true and 8 to 12 false) and at least one listed input file. Without them the test fails once `evals.json` exists.
- **Fix:** added `evals/trigger-queries.json` (16 queries, 8 true and 8 false) and one input fixture `evals/files/v1-project/.planning/config.json`, listed by `edge-v1-written-config`. The other five evals keep `files: []`.
- **Commit:** 43b16fc

**5. [Test-driven wording] `recommend.py` message line split**
- **Issue:** the wording test reads the source text, so "own bash tool" had to stay on one source line.
- **Fix:** the string split was placed so the phrase is contiguous in the source. Message text is the one the plan specified.
- **Commit:** 43b16fc

### Other notes

- The `mermaid-audit` `test_setup` references were changed in commit 1f4b4eb (Task 1) rather than in Task 2's commit, because they sit in the same dead-name list.
- `uv run` (for `tests.test_config_doctor`) created the gitignored `.venv` inside this worktree. It is untracked and ignored; it is not staged.
- No herdr, pi, claude, opencode, codex or cursor process was started. No real host config was read or written.

## jev call log

No jev calls were made in this run. The decisions above (the synthetic dead-name fixtures, the test-only files added to the eval shape, the `recommend.py` split) were made by the executor's own reasoning and are recorded here as deviations for owner review. Advisory jev review was not used because the scope and time budget were tight.

## Orchestrator steps

- orchestrator step: skill-judge loop (native opus xhigh) on `skills/ai-kit-gsd-curated-config/` after this plan, its last change in the phase. Record the result, the evals and the tests in `31-VERIFICATION.md`. Include the not-judged list with reasons (R15 empty edge): `ai-kit-project-rules-agents` per D-01 (SJ-3 carried to Phase 45), `ai-kit-project-rules-makefile` (one count word), `ai-kit-usage-metrics` (unchanged). The judged set for this plan is `ai-kit-spec-execute`, `ai-kit-spec-config` and `ai-kit-gsd-curated-config`.
- orchestrator step: herdr pi live check (D-11, R9 acceptance). Start pi in a herdr pane with a scratch HOME (no copied credentials), ask its agent to run `env | grep '^PI_'` through its own bash tool, and record the variable names only (`PI_PROVIDER` and `PI_MODEL` expected) in `31-VERIFICATION.md`. Stop the pane afterwards. Not run by the executor.
- orchestrator step: mark the folded DEF-01 items in `.planning/todos/pending/2026-11-02-tooling-defects-and-skill-writing-principle-found-at-the-v1.md` and SJ-1 closed in `.planning/todos/pending/2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md`, per CONTEXT "Folded Todos".
- orchestrator step: write `31-VERIFICATION.md` with the results above.

## Self-Check: PASSED
