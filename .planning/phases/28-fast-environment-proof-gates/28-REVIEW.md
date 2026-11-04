---
phase: 28-fast-environment-proof-gates
reviewed: 2026-11-04T00:00:00Z
depth: standard
files_reviewed: 46
files_reviewed_list:
  - .pre-commit-config.yaml
  - AGENTS.md
  - Makefile
  - README.md
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - tests/fixtures/curated_config_v2/repo-config.json
  - tests/gsd_curated_eval.py
  - tests/host_fakes.py
  - tests/test_ai_kit_gsd_curated_config_matrix.py
  - tests/test_ai_kit_project_rules_all.py
  - tests/test_ai_kit_project_rules_all_e2e.py
  - tests/test_ai_kit_session_wake.py
  - tests/test_ai_kit_spec_goal_prompt_e2e.py
  - tests/test_ai_kit_spec_goal_prompt_evals.py
  - tests/test_arch.py
  - tests/test_check_dogfood.py
  - tests/test_config_doctor_pty.py
  - tests/test_cross_ai_runner_e2e.py
  - tests/test_cross_ai_skill_text.py
  - tests/test_curated_config_apply_e2e.py
  - tests/test_curated_config_e2e.py
  - tests/test_curated_config_script.py
  - tests/test_env_matrix.py
  - tests/test_gate_scope.py
  - tests/test_gsd_curated_eval.py
  - tests/test_hook_registry.py
  - tests/test_markdown_to_pdf.py
  - tests/test_markdown_to_pdf_e2e.py
  - tests/test_phase26_owner_captures.py
  - tests/test_pi_live_tools.py
  - tests/test_precompact_core.py
  - tests/test_run_unittest_parallel.py
  - tests/test_setup.py
  - tests/test_staged_commit_e2e.py
  - tests/test_staged_mapper.py
  - tests/test_time_prepush.py
  - tests/test_tool_advisor_core.py
  - tests/test_tool_substitution_hook.py
  - tests/test_wizard_pty.py
  - tests/test_worktree_e2e.py
  - tools/check_dogfood.py
  - tools/env_matrix.py
  - tools/run_unittest_parallel.py
  - tools/setup.py
  - tools/staged_mapper.py
  - tools/time_prepush.py
findings:
  critical: 0
  warning: 0
  info: 7
  total: 7
  necessity: 1
status: issues_found
---

# Phase 28: Code Review Report

**Reviewed:** 2026-11-04
**Depth:** standard
**Files Reviewed:** 46
**Status:** issues_found (info only: no critical or warning finding remains)

## Summary

This is re-review iteration 2. It covers the fix commits `bf32abf`, `b823c56` and `bc6f8ea`
(`git diff 5243f70..HEAD`) against the three warnings of the first pass, plus the code they
connect to: `_staged_selection`, `_run_staged_modules` and `group_modules` in
`tools/run_unittest_parallel.py`, `check_no_write` and `main` in `tools/check_dogfood.py`,
and `_tool_forms` and `covering_modules` in `tools/staged_mapper.py`. I did not re-review the
unchanged phase code. As instructed, I ran no tests. I checked behavior with two read-only probes
under `tmp/phase28-review/`, which are deleted now.

All three warnings are resolved, and the fixes add no defect or regression:

- **WR-01 (resolved).** A full run now builds `sorted({*unit, *arch, *covering})`
  (`tools/run_unittest_parallel.py:687`), so it always contains the targeted run. Probe:
  `tools/wizard_app.py` alone selects integration `tests.test_wizard_app` and e2e
  `tests.test_system_memory_e2e`. `tools/wizard_app.py Makefile` now gives a full run that keeps
  both, adds `tests.test_config_doctor`, and runs 80 unit modules. The mapper-error and no-index
  paths are unchanged in effect: their covering set is `sorted(E2E_MODULES)`, which the old
  filter passed through whole. `_run_staged_modules` still splits e2e by budget and still checks
  for uv before any heavy module runs. The full path now reaches `_uv_missing` with uv or
  integration modules, the same as a targeted run. The docstrings match the code.
- **WR-02 (resolved).** `_guard_report` now adds a problem for every skipped guard except
  `APPLY_GUARD` (`tools/check_dogfood.py:170-171`), so three skips give two problems and
  `main` exits 1. A class-level `setUpClass` skip goes through `_result_for` and is caught the
  same way. The apply guard's exemption covers any skip reason, including no node. That is safe:
  without node the two `TestRealIntegration` guards also skip and fail the run. No existing test
  expected a non-apply skip to pass. `tests/test_check_dogfood.py:235-242` pins the new rule.
  Expected side effect: a checkout with no node or no checkout-local gsd-core now fails
  `make validate` and pre-push at `check-dogfood`. That is the fail-closed behavior the warning
  asked for.
- **WR-03 (resolved).** `tests/test_time_prepush.py:44-48` names `env_matrix.py` in a code form
  the mapper matches. The probe `staged_mapper.py tools/env_matrix.py` now returns
  `tests.test_env_matrix tests.test_gate_scope tests.test_time_prepush`. The test makes a real
  assertion: `time_prepush.env_matrix` exists at `tools/time_prepush.py:58`. The general limit
  is now written down in the mapper docstring and in `AGENTS.md`. I grepped every
  `spec_from_file_location` load in `tools/`. All the others load
  `run_unittest_parallel.py` or `staged_mapper.py`, and both are in `SHARED_MACHINERY`, so no
  similar gap is left today.

IN-01 to IN-06 carry over unchanged from the first pass, where they were triaged out of fix
scope. IN-07 is new: a test-name accuracy note on the WR-01 regression test.

## Info

### IN-01: `--pushed` trusts a covering set the mapper marked untrusted

**File:** `tools/run_unittest_parallel.py:732-742`
**Issue:** `_range_deferred` checks only `decision.index_built` and ignores `decision.full_reason`
(shared machinery, a shared helper, or an "empty answer for covered file"). `decide()` documents
that reason as "they cannot be trusted". For a pushed range that changes, say, `uv.lock` or a
file that only an e2e module reads through a glob, the over-budget
`tests.test_cross_ai_runner_e2e` does not run at push. The commit stage behaves the same way, so
the e2e gate never falls back to a full run except on a mapper error. This matches the docs
(`AGENTS.md` calls only unit and arch "full"), so it is Info, not a defect.
**Fix:** If wanted, `if decision.full_reason: raise RuntimeError(decision.full_reason)` makes the
caller take `_fallback`. The cost is about 350 s on such pushes, so the owner should decide.

### IN-02: The guard result regex fails closed on interleaved stderr

**File:** `tools/check_dogfood.py:136-140`, `:204-207`
**Issue:** The child merges stderr into stdout. A guard test that emits a warning (for example a
`DeprecationWarning`) between `... ` and `ok` breaks the one-line ` ... ok$` match. The result
then reads as `no-write guard missing result`, a false push failure. It fails closed, so it is
low risk.
**Fix:** Keep stderr separate (`stderr=subprocess.PIPE`) and parse only the unittest stream, or
accept the status token on a later line.

### IN-03: The matrix's final cleanup can override its verdict

**File:** `tools/env_matrix.py:467-475`
**Issue:** `shutil.rmtree(scratch)` in `finally` has no error handling. The custom-tmpdir
environment puts the runner's per-module temp dirs under `scratch`, and the runner cleans those
with `ignore_cleanup_errors=True`. A test that leaves a mode-000 folder therefore makes the final
rmtree raise. The traceback replaces the printed verdict's exit code and leaves scratch behind.
**Fix:** `shutil.rmtree(scratch, ignore_errors=True)`, or chmod and retry, then report anything
left over.

### IN-04: A missing module is reported twice per environment

**File:** `tools/env_matrix.py:387-389` (with `:123-130`, `:148-152`)
**Issue:** `_env_differences` concatenates `inventory_problems` (`no report for X`) and
`compare_reports` (`X: missing in this environment`) for the same module, which inflates the
"N differences" count. Also, `_run_plain` prints "expect about 6x" even under `--only`.
**Fix:** Drop the missing/extra branch from one of the two, and scale the estimate by
`len(names)`.

### IN-05: The shortcut comment's gsd-core version is stale

**File:** `tools/check_dogfood.py:44-46`
**Issue:** The comment says the checkout-local gsd-core was 1.18.0 on 2026-11-03. Today's live
run of `tools/check_dogfood.py` reports `checkout-local gsd-core is 1.20.0`. The warning itself
is correct; only the comment's figure is out of date.
**Fix:** Drop the version figure from the comment, so it states only the condition (outside
`GSD_CORE_PREFIXES`) and the backlog id.

### IN-06: Generality without instantiation: an empty `ALL_SKIP_OK` allowlist and its stale checker

**File:** `tools/time_prepush.py:39-41`, `:117`, `:174-176`
**Category:** necessity
**Issue:** `ALL_SKIP_OK` is empty ("Empty unless the all-skip scan finds a case"), and the
`stale_all_skip_ok` helper with its tests (`tests/test_time_prepush.py:161`, `:179-190`) guards a
list that has never held an entry. This is a judgment call: the allowlist may be planned future
work, so this is Info.
**Fix:** Optional: keep the single membership check and drop `stale_all_skip_ok` until the first
entry lands.

### IN-07: The WR-01 regression test claims a unit-uv module but uses two integration modules

**File:** `tests/test_staged_mapper.py:552-564`
**Issue:** `test_a_full_run_keeps_a_covering_uv_and_integration_module` uses
`uv_mod = "tests.test_wizard_app"` and `integ = sorted(INTEGRATION_MODULES)[0]`
(`tests.test_config_doctor`). Both are in `INTEGRATION_MODULES`. The only unit-uv module is
`tests.test_framework_profiles`. So the test never shows that a full run keeps a unit-uv module,
even though its name says so. The composition is a group-agnostic set union, so the code is
correct today. The risk is only that a future group-specific filter would get past this test.
**Fix:** Take a real unit-uv module:
`uv_mod = sorted(self.runner.EXPLICIT_GROUPS["unit-uv"])[0]`.

---

_Reviewed: 2026-11-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
