---
phase: 28
fixed_at: 2026-11-04T00:00:00Z
review_path: .planning/phases/28-fast-environment-proof-gates/28-REVIEW.md
iteration: 2
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 28: Code Review Fix Report

**Iterations:** 2 (iteration 2 re-reviewed the fix diffs only: 0 critical, 0 warning, IN-07 new). Edits and commits were made in the main checkout (no worktree); verification ran there too.

## Fixed Issues

### WR-01: A full run at commit drops the covering unit-uv and integration modules

**Files modified:** `tools/run_unittest_parallel.py`, `tests/test_staged_mapper.py`
**Commit:** bf32abf
**Applied fix:** the full run is now `sorted({*unit, *arch, *covering})`; docstrings updated. New test stubs `_run_staged_modules` and asserts a covering unit-uv and integration module are in the list. One existing test was adjusted for the fixture tree's `tests.test_beta` covering module. Requires human verification (logic change).

### WR-02: `check-dogfood` reports `ok` when zero no-write guards executed

**Files modified:** `tools/check_dogfood.py`, `tests/test_check_dogfood.py`
**Commit:** b823c56
**Applied fix:** a skipped guard other than `APPLY_GUARD` is now a problem ("...; the live project is unguarded"). Zero-executed is covered by this rule, because only the apply guard can be skipped without a problem. The apply-only skip keeps its warning note (existing test). Requires human verification (logic change).

### WR-03: The mapper misses tool-to-tool loads

**Files modified:** `tests/test_time_prepush.py`, `tools/staged_mapper.py`, `AGENTS.md`
**Commit:** bc6f8ea
**Applied fix:** test asserts the loaded `env_matrix` module file is `tools/env_matrix.py`; `staged_mapper.py tools/env_matrix.py` now lists `tests.test_time_prepush`. Documented limit added to the mapper docstring and AGENTS.md. SHARED_MACHINERY untouched.

### IN-07: The WR-01 regression test claims a unit-uv module but uses two integration modules

**Files modified:** `tests/test_staged_mapper.py`
**Commit:** 227fe85
**Applied fix (iteration 2, orchestrator):** the test takes its unit-uv module from `UNIT_UV_MODULES`, so it pins the unit-uv case it names. Fixed although Info: it is a gap in this run's own regression test.

## Triage (jev advisory, all `needs_fallback`; the orchestrator verified each in the code)

- WR-01: supported 0.53 -> verified real, fixed.
- WR-02: supported 0.60 -> verified real (no later backstop), fixed.
- WR-03: supported 0.37 -> verified real; fixed through the test-naming path, because SHARED_MACHINERY is a spec-pinned set.
- IN-03 (Info): partial 0.60 -> kept out of scope, no observed occurrence.

## Skipped Issues

Out of scope: fix_scope critical_warning (Info findings).

### IN-01: `--pushed` trusts a covering set the mapper marked untrusted

**Reason:** owner decision, matches documented behavior (~350 s cost).

### IN-02: The guard result regex fails closed on interleaved stderr

**Reason:** fails closed, no observed occurrence.

### IN-03: The matrix's final cleanup can override its verdict

**Reason:** no observed occurrence, info only.

### IN-04: A missing module is reported twice per environment

**Reason:** cosmetic count/estimate text.

### IN-05: The shortcut comment's gsd-core version is stale

**Reason:** comment-only staleness.

### IN-06: Generality without instantiation: an empty `ALL_SKIP_OK` allowlist and its stale checker

**Reason:** necessity judgment; the allowlist is the documented hook for a future all-skip case.


## Verification

- `python3 tools/run_unittest_parallel.py tests.test_staged_mapper tests.test_run_unittest_parallel`: pass (main checkout)
- `python3 tools/run_unittest_parallel.py tests.test_check_dogfood`: rc 0
- `python3 tools/run_unittest_parallel.py tests.test_time_prepush tests.test_gate_scope`: rc 0
- `make test` at bc6f8ea: exit 0, 416 s (unit 80/80 + unit-uv 1/1, integration 4/4, e2e 15/15 + install 45/45, arch 1/1); after 227fe85 (test-only) `tests.test_staged_mapper` re-ran: pass.
- Live `tools/check_dogfood.py`: ok (2 of 3 guards executed; the apply guard skip is the documented exception).
- Pre-commit hooks ran on every commit (first WR-01 attempts failed ruff/pylint line length, fixed, no `--no-verify`).

---

_Fixer: Claude (gsd-code-fixer)_
