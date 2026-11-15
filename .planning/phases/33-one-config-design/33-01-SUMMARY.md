---
phase: 33-one-config-design
plan: 01
subsystem: config
tags: [toml, splicer, atomic-write, fsync, tomllib, comment-preserving]

# Dependency graph
requires: []
provides:
  - "toml_splice.set_table: change keys of one table, the rest of the file keeps its bytes"
  - "toml_splice.set_array: replace an array of tables entry by entry (in-place edit, ordered insert, removal)"
  - "toml_splice.remove_table: drop one table with every block under it"
  - "toml_splice.publish: atomic write of checked TOML (temp file in folder, fsync, rename, folder fsync)"
  - "cache.cache_write_bytes now fsyncs the file and its folder (D-09)"
affects: [33-02, 33-03, 33-04, 33-05, 33-06, 33-07, 33-08, 33-09]

# Actuals (#2632) - chars/4 over the realized diff (75.2 KB of diff text)
actuals:
  tokens: 18800
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Region splicing: classify lines into key spans and table headers, rewrite only the owned lines"
    - "Every write is re-parsed with tomllib and refused unless it equals the intended document"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py
    - tests/test_toml_splice.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cache.py
    - tests/test_curated_config_recommend.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "Every operation re-parses its result with tomllib and raises SpliceError unless it equals the intended document (T-33-01)"
  - "Comment lines directly above a table header belong to that header's block; a blank line breaks the attachment, so a removed entry takes its comment with it"
  - "Array entries pair by their unique string key; without unique keys they pair by position"
  - "A changed entry is edited block by block, so its sub-table blocks and their comments survive (C1-1)"
  - "A new entry is inserted directly before the group of the next kept entry, so the parsed order matches the intended order (C1-2)"
  - "A key under an implicit parent table gets the missing header block; an implicit table set through dotted keys is refused (C2-1)"
  - "A header's name is cut at the first ] outside double quotes, so a bracketed scope name stays one table (C2-2); a header whose name does not parse fails closed with the line named (C3-1)"
  - "A changed entry holding a nested array of tables is refused rather than re-rendered"
  - "publish keeps an existing file's mode, creates new files at 0600, and writes a symlink's target so the link stays a link"
  - "The folder fsync opens the output folder read-only; the curated-config recommend I/O audit now allows that one folder"

patterns-established:
  - "Splicer tests: difflib line counts for minimal-diff claims, tomllib parse equality for correctness"
  - "Refusal tests patch toml_value to a wrong writer and assert SpliceError, proving the re-parse check is not vacuous"

requirements-completed: []

# Metrics
duration: unknown
completed: 2026-11-15
status: complete
---

# Phase 33 Plan 01: Comment-keeping TOML splicer with atomic publish Summary

**Stdlib TOML splicer (set_table, set_array, remove_table) that rewrites only the lines it owns, re-parses every result with tomllib, and publishes through an fsynced temp file and rename**

## Performance

- **Duration:** unknown (the start time was not captured at plan start)
- **Started:** not recorded
- **Completed:** 2026-11-15
- **Tasks:** 3 plan tasks, plus one test-only rename commit
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- A key changed in a commented, unusually spaced file with an unknown table produces a one-line diff (difflib shows one `-` and one `+` line), and the parse equals the intended document.
- An array of tables is replaced entry by entry: unchanged entries keep their bytes, a changed entry is edited in place (its sub-table blocks and their comments survive), new entries land in the intended order (middle, start, interleaved review/execute), and gone entries take their comments.
- Implicit parent tables gain their missing header; implicit tables set through dotted keys and changed entries with nested arrays of tables are refused with SpliceError.
- `publish` writes through a temp file in the target folder, fsyncs the file, renames, and fsyncs the folder; an interrupted rename leaves the old file and no temp file; a symlink stays a link; an existing mode is kept and a new file is 0600.
- `cache.cache_write_bytes` (shared by every caller) now fsyncs the file and its folder.
- Static gates (ruff, pyright, pylint, vulture) pass on the new code; the plan's unit and arch groups pass (117/117 modules).

## Task Commits

1. **Task 1: set one key of one table, verified and published atomically** - `9914d63` (feat)
2. **Task 2: arrays of tables and table removal** - `cb5ba04` (feat)
3. **Task 3: static gates and edge rows** - `11d38d7` (test)
4. **Test rename to the plan's acceptance name** - `034398d` (test)

## Files Created/Modified

- `skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py` - the splicer: `SpliceError`, `Span`, `Block`, `toml_key`, `toml_value`, `split_blocks`, `set_table`, `set_array`, `remove_table`, `publish`, and their private helpers.
- `skills/ai-kit-spec-review/ai_kit_spec/cache.py` - `cache_write_bytes` fsyncs the file and its folder; `_fsync_folder` helper.
- `tests/test_toml_splice.py` - 44 tests in classes TestSetTable, TestPublish, TestCacheFsync, TestSetArray, TestRemoveTable, TestSpliceRefusals, TestEdgeRows.
- `tests/test_curated_config_recommend.py` - the I/O audit's allow-list also names the output folder (see Deviations).
- `Makefile`, `.pre-commit-config.yaml` - regenerated test-group listings (only `tests.test_toml_splice` added).

## Decisions Made

See `key-decisions` in the frontmatter. The plan fixed every design choice; the implementation follows the plan's Design section and the review dispositions C1-1, C1-2, C2-1, C2-2, C3-1 as written.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] I/O audit in an existing test rejected the new folder fsync**
- **Found during:** Task 1 commit (staged-tests hook)
- **Issue:** `tests/test_curated_config_recommend.py::test_cli_recommend_touches_only_inventory_and_out` records every `open` the recommend CLI makes and requires each one to be a file in its temp folder. The folder fsync (D-09) opens the output folder itself, so the test failed.
- **Fix:** the test's allow-list names the output folder (`real_tmp`), with a comment that says why. Nothing else is allowed.
- **Files modified:** `tests/test_curated_config_recommend.py`
- **Verification:** `tests.test_curated_config_recommend` passes (139 tests); the full unit and arch groups pass (117/117).
- **Committed in:** `9914d63`

**2. [Plan naming] `_ensure_eol` is named `_with_eol`**
- **Found during:** Task 1 implementation
- **Issue:** the plan's artifact list names a private `_ensure_eol`; the implementation's helper is `_with_eol(text)` and returns the normalised text. Behaviour matches the plan's description (a last line without a newline gets one before anything is appended).
- **Fix:** none needed for behaviour; the name differs.
- **Committed in:** `9914d63`

**3. [Plan wording] The dotted-group `else SpliceError` branch is not reachable**
- **Found during:** Task 1 implementation
- **Issue:** the plan says a dotted key group is replaced by one line only when every span of its first key is replaced, otherwise SpliceError. The implementation replaces a changed group whole (the first span is rewritten and the others of that key are dropped), so the partial case never arises and the SpliceError branch is not written.
- **Fix:** none; the dotted-key conflict test accepts either a correct parse or SpliceError, and passes.
- **Committed in:** `9914d63`

### Deviations to note

- **TDD gate sequence is not met (see TDD Gate Compliance).** The RED commit was attempted and blocked by the staged-tests hook (the failing module is what the hook runs); `--no-verify` is prohibited, so no RED commit was made. The first GREEN commit includes tests and implementation together.
- **Requirements not marked complete.** The plan lists CFG-04 and CFG-05 as its requirements. This plan delivers only the writer part of CFG-04 (SPEC R9, the splicer and its publish) and the writer part of CFG-05 (SPEC R3, unknown tables kept through a write). Full closure needs the migration and the roster and runner plans (33-02..33-09). `requirements-completed` is therefore empty, and REQUIREMENTS.md was not changed.

**Total deviations:** 3 auto-fixed or noted (1 blocking fix, 2 naming or wording notes), plus the TDD sequence and requirement-closure notes above.
**Impact on plan:** The plan's behaviours and acceptance tests are met. No scope creep. The audit allow-list is the only change to another test.

## TDD Gate Compliance

- **RED, Task 1:** test module plus a RED stub (`toml_splice` names returning their input). The RED run gave `FAILED (failures=14, errors=2)` over 17 tests, on assertions such as `AssertionError: 'a = 1\n' != 'a = 2\n'` and `OSError not raised`. The commit was blocked by the staged-tests hook (it runs the failing module), and `--no-verify` is prohibited, so the RED commit was not made.
- **RED, Task 2:** 40 tests; the RED run gave `errors=21`, all `AttributeError: module ... has no attribute 'set_array'` (or `remove_table`). That is a load-level failure, not an assertion failure, so it would not count as a valid RED under the tdd.md classifier.
- **Violation flagged:** no `test(33-01)` commit precedes the first `feat(33-01)` commit. The `test(33-01)` commits (`11d38d7`, `034398d`) follow the features. The `gsd_run check tdd-red-evidence` classifier was not run.

## Issues Encountered

- The RED commit attempt failed the ruff and staged-tests hooks as intended. The ruff findings were real (unused import, long lines, a SIM117) and were fixed.
- The GREEN commit for Task 1 failed the staged-tests hook on `tests.test_curated_config_recommend` (Deviation 1); fixed and re-committed.
- Pylint's design limits (locals and returns) forced `set_table`, `_edit_block`, `toml_value` and the array placement code into small helpers; no `# pylint: disable` was added.

## Known Stubs

None. The RED stub was replaced by the implementation in Task 1.

## Threat Flags

None beyond the plan's threat model. The folder fsync opens the output folder read-only; no new network, auth, or schema surface.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The writer (`set_table`, `set_array`, `remove_table`, `publish`) is ready for the render-toml, roster migration and runner plans (33-02..33-09).
- The splicer is not wired into any caller yet; `render-toml` still uses its full-rewrite path until plan 09.
- Not reviewed: the 661-line unit brief was read only in part (its first 107 lines: the changed-files list). Its header names this unit (`phase-33`, `point: wave`), and no instruction from the rest was applied.

## Self-Check: PASSED

- Created files exist: `skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py`, `tests/test_toml_splice.py`.
- Commits are ancestors of HEAD: `9914d63`, `cb5ba04`, `11d38d7`.
- Plan verify: `python3 tmp/p33/01/scope.py all` ran with `tests rc: 0` and `lint make ruff/pyright/pylint/vulture rc: 0`.

---
*Phase: 33-one-config-design*
*Completed: 2026-11-15*
