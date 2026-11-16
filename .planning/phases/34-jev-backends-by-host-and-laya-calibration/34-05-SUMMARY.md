---
phase: 34-jev-backends-by-host-and-laya-calibration
plan: 05
subsystem: jev-fast-decision
tags: [typesafe, model-records, docs-flow, stdlib, injected-fetcher, secret-shapes]

# Dependency graph
requires:
  - phase: 34-03
    provides: jev_learn.py Laya records, write_records/read_records helpers, FakeFetch test double
provides:
  - jev_learn.py: note_model (local pending note, no fetch), note_unknown (unknown primitive or option names, secret-shape screened), learn_models (one doc-flow read per pending id), latest_model, doc_links, fetch_model_docs, model_notes, model_primitives, model_entry
  - tests/test_jev_typesafe_models.py: 10 pure tests over an injected fetcher
  - tests/fixtures/jev/typesafe-docs.json: trimmed llms.txt, changelog.md and models.md
affects: [34-06 (wires note_model, note_unknown and learn_models into the answer path and the probe; completes the answer-path half of JEV-12)]

# Actuals (#2632): chars/4 over the realized diff from the spawn base 01d8509 to HEAD (measured)
actuals:
  tokens: 14047
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pending first, read once: a new versioned model id is noted from the answer path with no network call; the doc flow is read only by learn_models"
    - "Doc links are followed only under https://docs.typesafe.ai/; anything else falls back to the fixed default URLs"
    - "Unknown names are screened by the skill's own secret_shapes.detect before any count or write, loaded by path as jev_ladder.py does"

key-files:
  created:
    - tests/test_jev_typesafe_models.py
    - tests/fixtures/jev/typesafe-docs.json
  modified:
    - skills/jev-fast-decision/scripts/jev_learn.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "note_model writes only status and first_seen, under a key that must fullmatch the versioned-id pattern; aliases such as jev-latest, None and empty ids write nothing (SPEC R4 adjacency and empty)"
  - "learn_models records only when changelog.md and models.md both arrived (review C1-11); otherwise every target stays pending, nothing is written, and the notice names the failed page"
  - "llms.txt failing alone does not block: the default doc URLs serve the same pages, and the success notice says llms.txt was not read"
  - "The id's row in the models table is matched by an exact cell (`jev-1.14.0` as a whole cell), and the question-types cell is read at the same column index"
  - "model_notes takes the block from the nearest heading at or before the id's line to the next heading; an id absent from the changelog gets empty notes, not the whole page"
  - "An unknown name is dropped silently when it does not fullmatch the primitive/option pattern or holds a key shape (review C2-4); at most 16 names per id, and a name already seen never triggers a second doc read"
  - "unknown_documented reports a name only when its part after the colon appears as a whole word in the changelog or models page"

patterns-established:
  - "Notes and primitives are data: decoded with replacement, stored as text, cut to NOTES_MAX_CHARS, and reported as documented upstream, not verified here"

requirements-completed: []

# Metrics
duration: ~15 min (scratch folder created 19:09:34 -0300, last commit 19:18:36 -0300; the plan start time was not recorded)
completed: 2026-11-15
status: complete
---

# Phase 34 Plan 05: TypeSafe model records, one doc-flow read per new id

**A new TypeSafe model id is noted locally with no fetch, then the official doc flow is read once to record its notes, documented question types and the features it could serve; unknown primitive or option names trigger one doc read, screened for key shapes**

## Performance

- **Duration:** ~15 min (see frontmatter)
- **Tasks:** 2 of 2 completed
- **Files:** 2 created, 3 modified (plus scratch under the worktree `tmp/`, not committed)

## Accomplishments

- A versioned model id that an answer reports is noted as `{status: pending, first_seen}` with no network call; an alias, a missing id, or an id already recorded writes nothing.
- `learn_models` reads `llms.txt`, then `changelog.md` and `models.md` (links taken from the index only when they point under `https://docs.typesafe.ai/`), and records each pending id with its changelog block, documented question types, new primitives and the features it could serve (box, image, long_context, batch).
- A failed `changelog.md` or `models.md` keeps every id pending and writes nothing; the notice names the failed URL. A failed `llms.txt` alone falls back to the default URLs and says so.
- A primitive or option name the skill does not know (`primitive:<type>`, `option:<key>`) is noted with no network call, turns its id pending once, and is reported as `unknown_seen` / `unknown_documented` on the next doc read. A name holding a key shape is dropped before any count or write, and never logged.

## Task Commits

1. **Task 1: tracer, a new model id is noted locally, then the doc flow is read once and recorded** - `072f54c` (feat)
2. **Task 2: known ids, aliases, failures, unknown primitives and options, off-site links and refresh; static gates** - `e34a936` (feat, tests and implementation together; see TDD record)

The plan metadata commit follows this SUMMARY.

**TDD record (Task 2):** RED was observed locally before the implementation. `python3 tools/run_unittest_parallel.py tests.test_jev_typesafe_models` reported `FAILED (errors=2)` of 10 tests; both errors were `AttributeError: ... has no attribute 'note_unknown'` (`test_unknown_primitive_or_option_triggers_one_doc_read`, `test_secret_shaped_unknown_name_is_dropped`). The other eight already passed on the Task 1 code. After the implementation the same command reported `ok`, 10 tests. The red state was not committed on its own, per the run rails (the staged-tests hook blocks a failing-test-only commit).

## Files Created/Modified

- `skills/jev-fast-decision/scripts/jev_learn.py` - the TypeSafe model records added beside the Laya records (stdlib only; no network; the secret-shape detector is loaded by path)
- `tests/test_jev_typesafe_models.py` - 10 tests in `TestModelRecords` with `FakeFetch` (imported from `tests.test_jev_learn`), temp state folders, no network
- `tests/fixtures/jev/typesafe-docs.json` - trimmed `llms` index (first 10 lines plus the changelog and models links the real index lists), the whole `changelog`, and the first 25 lines of `models`, built by a scratch script under the worktree `tmp/`
- `Makefile`, `.pre-commit-config.yaml` - regenerated by `tools/gen_test_groups.py` to list `tests/test_jev_typesafe_models.py`

## Decisions Made

See the `key-decisions` frontmatter. Interpretation beyond the plan text: the plan's `model_notes` wording "the id's line" is matched on the backticked id (`` `jev-1.14.0` ``), the form the docs print it in; an id line without backticks would not match. The plan's `learn_models` returns `model_ids` sorted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1 commit blocked by ruff and pylint**
- **Found during:** Task 1 commit
- **Issue:** ruff reported E501 on four docstrings (jev_learn.py and the new test module) and RUF059 on an unused unpacked `texts` in `_model_result`; pylint reported the same long line and an unused variable (W0612).
- **Fix:** Shortened the four docstrings to 100 characters and read `errors = docs[2]` in `_model_result`. No behaviour change.
- **Files modified:** `skills/jev-fast-decision/scripts/jev_learn.py`, `tests/test_jev_typesafe_models.py`
- **Verification:** `make ruff` and `make pylint` exit 0; the commit then landed with all hooks passing.
- **Committed in:** `072f54c`

**Total deviations:** 1 auto-fixed (Rule 3, lint gate on the first commit). **Impact:** none on behaviour or scope.

## Issues Encountered

- **Commit-plan ledger not written.** Protocol 0c's `gsd-plan-head-before-34-05` ledger was not created before the first commit. The `commits:` count above is measured with `git rev-list --count 01d8509165a7d5d920f71638bc60a2bac6fc4e10..HEAD`, using the spawn-time HEAD that the branch-check guard verified, which is the same base the ledger would have recorded.
- **Unit brief read partially.** `.aikit/brief/SKILL.md` (main checkout copy): the first 40 lines were read (header, unit `phase-34`, previous unit, changed-file list). A 200-line read exceeded the read tool's size limit. Nothing read contradicted the plan.
- **Full `make test` not run.** The plan's verification set (three test modules, `make ruff`, `make pyright`, `make pylint`, `make vulture`) was run and passes. The commit hooks ran the unit and arch groups in the first commit (134/134 modules) and the staged set in the second (27/27 modules). The e2e tier and `make test-env-matrix` were not run.
- **Leftovers in the worktree (ignored, not committed):** the `.venv` created by `uv run` for the lint hooks, and `tmp/auto/r325/research34/` (three trimmed TypeSafe samples copied read-only from the main checkout) plus `tmp/p34/05/` (the fixture builder, the two verify scripts and the measurement script).

## Verification

| Command | Exit | Result |
|---|---|---|
| `python3 tools/gen_test_groups.py` | 0 | regenerated Makefile and `.pre-commit-config.yaml` (before this step, `test_gate_scope` failed on the unlisted module, 2 failures) |
| `tools/run_unittest_parallel.py tests.test_jev_typesafe_models tests.test_jev_learn tests.test_gate_scope` (Task 1) | 0 | `ok` (1 test), `ok` (19), `ok` (62); `3/3 modules passed` |
| `tools/run_unittest_parallel.py tests.test_jev_typesafe_models` (Task 2 RED) | 1 | `FAILED (errors=2)`, `Ran 10 tests`, both `AttributeError` on `note_unknown` |
| `tools/run_unittest_parallel.py tests.test_jev_typesafe_models tests.test_jev_learn tests.test_arch` (Task 2 GREEN) | 0 | `ok` (10), `ok` (19), `ok` (109); `3/3 modules passed` |
| `make pylint` | 0 | `Passed` |
| `make ruff` | 0 | `Passed` |
| `make pyright` | 0 | `Passed` |
| `make vulture` | 0 | `Passed` |
| commit hooks, first commit `072f54c` | 0 | ruff, pylint, py-compile, staged-tests: `134/134 modules passed` |
| commit hooks, second commit `e34a936` | 0 | staged-tests: `27/27 modules passed` |

## Self-Check

- Files found: `skills/jev-fast-decision/scripts/jev_learn.py`, `tests/test_jev_typesafe_models.py`, `tests/fixtures/jev/typesafe-docs.json`
- Commits found in history (`git merge-base --is-ancestor`, exit 0): `072f54c`, `e34a936`

## Self-Check: PASSED

## Next Phase Readiness

- Plan 06 wires `note_model` (answer path, after the answer log), `note_unknown` (an answer's unknown fields, a caller item's unknown type or key, at a refusal that made no call) and `learn_models` (the probe) into `jev_review.py`, and copies `secret_shapes.py` beside the spaced test client (review C2-4 requires the loader's file to exist there).
- JEV-12 stays Pending until Plan 06 lands the answer-path and probe wiring; this plan delivers the module-level behaviour only.

---
*Phase: 34-jev-backends-by-host-and-laya-calibration*
*Completed: 2026-11-15*
