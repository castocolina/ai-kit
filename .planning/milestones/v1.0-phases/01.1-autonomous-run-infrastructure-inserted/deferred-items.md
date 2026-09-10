# Deferred Items — Phase 1.1 (Autonomous-Run Infrastructure, INSERTED)

Out-of-scope discoveries found during 01.1-01-PLAN.md execution, per the executor's
Scope Boundary rule (only auto-fix issues directly caused by the current task's
changes; pre-existing failures in unrelated files are logged here, not fixed).

## `make validate` pre-existing failures (unrelated to this plan's changes)

Discovered while confirming Task 1's `tools/setup.py` fix introduced no new lint
issues (`make validate` runs the full pre-commit hook suite across all files, a
broader gate than `make e2e-docker`'s own `make test` + `make lint`, which both pass
cleanly). All items below are confirmed pre-existing at HEAD (before this plan's
changes) via a direct `git checkout HEAD -- tools/setup.py` + re-run comparison, and
`make validate`'s pylint score is unchanged by this plan's `tools/setup.py` edits
(+0.00 delta) — no new violation was introduced.

1. ~~pylint R0913/R0917 — `tools/setup.py`'s `_make_apply_housekeeping`~~ **FIXED**
   this plan (Rule 3 — blocking issue): confirmed pre-existing at HEAD via
   `git checkout HEAD -- tools/setup.py && uv run pylint tools/setup.py` (same error,
   HEAD's own line 1998), but pre-commit's `pylint` hook is scoped to
   `tools/(status-line|statusline-doctor|setup)\.py$` and analyzes the WHOLE staged
   file, not just the diff — since Task 1's own `tools/setup.py` deviation fix is
   staged in the same commit, this pre-existing violation would otherwise block that
   commit. Fixed with the same `# pylint: disable=too-many-arguments,too-many-
   positional-arguments` convention already used elsewhere in this file (e.g.
   `launch_wizard`) — a comment-only change, no behavior change. `make test` +
   `make lint` re-verified green after this fix.
2. **ruff E501 (line too long) — `tools/status-line.py`** (lines ~798, 859, 2222,
   2225, 2227) and **`tools/wizard_app.py`** (line ~471). Pre-existing; this plan
   does not modify either file, and pre-commit's `ruff` hook only runs against
   STAGED files matching its `files:` pattern, so these never block this plan's
   commits.
3. **ruff RUF012 (mutable default value for class attribute) — `tools/wizard_app.py`**
   (`housekeeping: dict = {}`, line ~116). Pre-existing; this plan does not modify
   this file (same non-blocking reasoning as item 2).

None of these block Task 1's actual required gate (`make e2e-docker`, which runs
`make test` + `make lint` only, both green) — recorded here for a future phase or
dedicated cleanup pass to address, per the executor's Scope Boundary rule.
