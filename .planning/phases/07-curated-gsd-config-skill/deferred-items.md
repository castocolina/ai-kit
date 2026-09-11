# Phase 07 — Deferred Items

## `make validate`'s overall gate blocked by pre-existing, out-of-phase-scope lint issues (2026-09-11)

**Found during:** Plan 07-04, Task 2 (`make test && make lint && make validate` verification).

**Issue:** `make validate` (the full `pre-commit run --all-files` gate) fails on two
files this plan's `files_modified` does not touch, neither introduced nor modified
by any Phase 07 plan:

- `tools/status-line.py` — 5 `ruff` E501 (line-too-long) findings + 1 `pylint`
  R0914 (too-many-locals) + the same 5 lines re-flagged by `pylint` C0301. Confirmed
  via `git log --oneline -3 -- tools/status-line.py` these lines were last touched by
  Phase 8 commit `b80a26a` (`feat(08-01): add burn-rate ratio helpers for rate-limit
  ramp coloring`) — unrelated to Phase 07's scope.
- `tools/wizard_app.py` — 1 `ruff` RUF012 (mutable default class attribute) + 1
  `ruff` E501. Also untouched by any Phase 07 commit (`git diff --stat
  tools/wizard_app.py` against this plan's changes is empty).

**Scope Boundary rule applied:** Per the executor's own scope-boundary rule ("Only
auto-fix issues DIRECTLY caused by the current task's changes... Pre-existing
warnings, linting errors, or failures in unrelated files are out of scope"), these
are NOT fixed by this plan. This mirrors Phase 6's own identical precedent (see
`06-agents-md-rules-checker-skill/deferred-items.md`, Plan 02: "`make validate`'s
overall gate is blocked by three pre-existing, out-of-Phase-6-scope lint issues").

**This plan's own scope is confirmed clean independently:**
- `uv run ruff check skills/ai-kit-gsd-curated-config/` → `[]` (zero findings)
- `uv run pyright` (full project, no args — same invocation the pre-commit hook
  uses) → `0 errors, 0 warnings, 0 informations`
- `uv run vulture skills/ai-kit-gsd-curated-config/` → zero findings
- `make test` → `Ran 1682 tests in ...` `OK (skipped=25)` (includes the 87 new
  `tests.test_ai_kit_gsd_curated_config` tests)
- `make lint` → exits 0, zero output
- `pre-commit`'s `pyright`/`vulture`/`shellcheck`/`py-compile`/`unittest (core)`/
  `unittest (wizard — uv)` hooks all report `Passed` in the full `make validate` run;
  only `ruff` and `pylint` fail, and only on the two pre-existing unrelated files
  above.

**Status:** Deferred — not this phase's responsibility to fix. Should be addressed
in a future phase/plan that legitimately touches `tools/status-line.py`/
`tools/wizard_app.py`.
