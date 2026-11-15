---
phase: 33-one-config-design
plan: 05
subsystem: config
tags: [migration, trust, toml, lanes, review-spec, purpose, canonical-digest]

# Dependency graph
requires:
  - "33-01: toml_splice (split_blocks, toml_key, publish) for the header rewrite and the atomic publish"
  - "33-03: one user-dir rule; the migration takes explicit paths and reads no environment"
provides:
  - "config_migrate.migrate_layer: old review-spec.toml into [lanes] of config.toml, comments and values kept, re-read and compared as a whole document, then the old file is renamed to .migrated"
  - "config_migrate: split_by_purpose, lanes_from_legacy, migrate_text, read_legacy, pending, legacy_path, legacy_trust_dir, revoke_legacy_trust (C2-3)"
  - "trust.command_lanes_bytes: canonical digest of the command-running lane entries (D-11, C1-12)"
affects: [33-07 (wires migrate_layer into every roster reader and trust-local --revoke)]

# Actuals (#2632): chars/4 over the realized diff (base dff326e .. HEAD)
actuals:
  tokens: 17808
  tasks: 3
  commits: 3
plan_head_before: dff326eac0e140e654e4f47089f90c4930fe5175
plan_head_after: 8578704e28b8cca67c79a2e45a528db251e7a528

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Copy, never merge: the old roster's text is copied under [lanes], re-read, compared, and only then retired"
    - "Publish with a pre-publish re-read (two attempts) and a post-publish whole-document check (C1-9)"
    - "Trust carried only by the run that publishes; a completed run never reads the legacy trust record (C1-10)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py
    - tests/test_config_migrate.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/trust.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "lanes_from_legacy returns the body of the [lanes] table (the document wraps it under lanes), so config.toml's parsed lanes equals it directly"
  - "migrate_text takes an optional old_path (default review-spec.toml) so the inline-array refusal can name the old file; migrate_layer always passes the real path"
  - "A reviewer entry is copied under each role its purpose names; purpose is kept as written (D-24)"
  - "command_lanes_bytes takes the file's own command-bearing keys into the digest for every role (C1-12); user_command_keys is passed by the caller"
  - "The new config's existing bytes are kept as a byte-for-byte prefix; the migrated lanes follow one blank line"

patterns-established:
  - "Interruption tests patch toml_splice.publish and config_migrate.os.rename; concurrency tests wrap config_migrate._read_bytes with a per-path read counter"

requirements: [CFG-02, CFG-05]
requirements-completed: []  # Migration module only. CFG-02 needs Plan 07 (every reader calls migrate_layer); CFG-05 is met for the migrated roster only. The orchestrator decides the status.

# Metrics
duration: unknown (plan start time was not recorded)
completed: 2026-11-15
status: complete
---

# Phase 33 Plan 05: Roster migration into config.toml with trust carried Summary

**Old review-spec.toml copies into [lanes] of config.toml with comments and every value kept, is re-read and compared as a whole document, and only then is renamed to .migrated; a trusted roster is re-keyed to the canonical command-lane digest**

## Performance

- **Duration:** unknown (the plan start time was not recorded)
- **Tasks:** 3 (Task 1 tracer, Task 2 every R4 and R5 case, Task 3 static gates)
- **Commits:** 3 task commits; SUMMARY committed after them

## Accomplishments

- `config_migrate.migrate_layer(new_path, *, warn_fn, trust_dir=None, trust_bytes_fn=None)` returns `none`, `migrated`, `completed`, `kept-new` or `deferred`.
- Purpose picks the role: `review` or none to `[[lanes.review]]`, `execute` to `[[lanes.execute]]`, `both` to each. Every key and value, `purpose` included, is kept.
- Interruptions leave the old file intact: a failed publish writes nothing; a failed rename leaves every value in both files and the next run completes.
- Concurrent writes are handled without a lock (D-25): a write before the publish rebuilds from fresh bytes; a write after it defers with the old file kept; a change to the old file before the rename defers.
- Trust is carried only by the publishing run, to the digest of the new file's command-bearing lanes; `revoke_legacy_trust` makes a revoke before the first migration stick.
- `trust.command_lanes_bytes` is canonical JSON (sorted keys, fixed separators, ASCII) over roles in sorted order and entries in file order; it includes every entry whose key matches a command entry, so C1-12's second-row case changes the digest.

## Task Commits

1. **Task 1: one local roster migrates into config.toml** - `012041e` (feat, with its tests)
2. **Task 2: every R4 and R5 migration case** - `5ede837` (test)
3. **Task 3: static gates** - `8578704` (test; pyright typing in the test helpers)

## Files Created/Modified

- `skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py` - the migration module; the only Python code that names `review-spec.toml` and `review-spec-trust` (D-10). It imports only `trust` and `toml_splice`.
- `skills/ai-kit-spec-review/ai_kit_spec/trust.py` - `command_lanes_bytes` added; the module docstring states what a record pins. `is_trusted` and `record_trust` keep their signatures.
- `tests/test_config_migrate.py` - 39 tests in classes TestTracer, TestLayers, TestShapes, TestRepeat, TestTrustCarry, TestInterruptions, TestConcurrency, TestErrors, TestNoSecretCopied, TestCanonicalBytes.
- `Makefile`, `.pre-commit-config.yaml` - regenerated test-group blocks (only `tests.test_config_migrate` added to unit).

## Deviations from Plan

**1. [Rule 1 - Lint] Commit hook refused Task 1 on lint** (ruff E501 x3, RUF005 x3, F401 x3; pylint line length x2)
- **Found during:** Task 1 commit
- **Fix:** shortened docstrings, used iterable unpacking, removed the imports the Task 1 tests did not use (the Task 2 classes re-add them)
- **Committed in:** `012041e`

**2. [Rule 2 - Signature] `migrate_text` takes an optional `old_path`**
- **Issue:** the plan's `migrate_text(old_text)` has no path, but it must raise `LegacyRosterError(old, ...)` for an inline-array roster.
- **Fix:** `migrate_text(old_text, old_path=LEGACY_NAME)`. No new public name; callers that pass one argument behave as the plan says.
- **Committed in:** `012041e`

**3. [Rule 1 - Bug, test] Revoke-after-failed-rename test called a helper defined on another class** (`AttributeError`)
- **Fix:** `record_legacy_trust` moved to the shared base class in the test module.
- **Committed in:** `5ede837`

**4. [Rule 1 - Typing] Pyright errors in the test module** (8 errors: `bytes | None` from `command_lanes_bytes`, an optional from `read_legacy`)
- **Fix:** test helper `canonical_bytes` asserts a digest is present; the optional read narrows before unpacking. No production code changed.
- **Committed in:** `8578704`

**Total deviations:** 4 (1 lint, 1 signature, 2 test-side fixes). **Impact:** none on the migration behaviour the plan pins. No other test was changed, and no test outside the plan's file list broke.

## TDD Gate Compliance

- **RED, Task 1:** the test module was written first and run before `config_migrate.py` existed. The result was `ImportError: cannot import name 'config_migrate'` (`tmp/p33/05/red-task1.txt`). That is a load-level failure, not the assertion-level RED that tdd.md requires, so it does not count as a valid RED. No test-only commit was made.
- **GREEN, Task 1:** 4/4 tracer tests passed after the implementation (`tmp/p33/05/green-task1.txt`).
- **Task 2 tests came after the implementation.** The implementation was written in one pass from the plan's full transform and migration rules, so Task 2's cases did not drive it. They passed on their first run, apart from one test-side helper error that was fixed. They are not an assertion-level RED.
- **Violation flagged:** no `test(33-05)` RED commit precedes `feat(33-05)` (`012041e`); `test(33-05)` commits follow. The `tdd-red-evidence` classifier was not run.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. Migration writes trust records only for a file trusted under the old rule (T-33-14); it reads no environment or `secrets.env` (T-33-16).

## Verification (run in this worktree)

| Command | Exit | Count line |
| --- | --- | --- |
| `python3 tmp/p33/05/scope.py test` (after Task 1, module set as the plan) | 0 | `tests rc: 0`, 6/6 modules (`tests.test_config_migrate` 4 tests) |
| `python3 tmp/p33/05/scope.py all` (final, HEAD 8578704) | 0 | `tests rc: 0` (6/6: test_config_migrate 39, test_toml_splice 44, test_ai_kit_spec_trust 29, test_ai_kit_spec 693, test_gate_scope 62, test_arch 109); `lint ruff rc: 0`; `lint pyright rc: 0`; `lint pylint rc: 0`; `lint vulture rc: 0` |
| `bash tmp/p33/05/make-test.sh` (`make test`, real-home guard exported) | 0 | unit 118/118, unit-uv 3/3, integration 9/9, e2e 25/25 (plus `tests/test_install.sh` 48 passed, 0 failed), arch 1/1 modules |
| `rg -n "config_io" skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py` | 1 (no match) | none |

Commit hooks ran the staged tests on each commit: commit 1 ran the full unit group (137/137) and arch (109); commits 2 and 3 ran `tests.test_config_migrate` and `tests.test_arch`.

**Isolation:** every test builds its own temporary project, user folder and trust store and passes them explicitly. `config_migrate` reads no environment variable and no `HOME`. `scope.py` and `make-test.sh` export `AI_KIT_REFUSE_REAL_HOME=1`. No test or manual run touched the main checkout's `.aikit/`, `~/.config/ai-kit`, or any real `~/.claude`, `~/.cursor`, `~/.config/opencode`, `~/.codex`, `~/.pi`, `~/.gsd`.

## Self-Check

- Created files exist: `skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py`, `tests/test_config_migrate.py`.
- Commits are ancestors of HEAD: `012041e`, `5ede837`, `8578704`.
- The ledger base `dff326e` is the parent of `012041e`.
- `make test` result: see the table above.

## Self-Check: PASSED

---
*Phase: 33-one-config-design*
*Completed: 2026-11-15*
