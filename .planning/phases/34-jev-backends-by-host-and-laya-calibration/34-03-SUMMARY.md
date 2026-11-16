---
phase: 34-jev-backends-by-host-and-laya-calibration
plan: 03
subsystem: jev-fast-decision
tags: [laya, pypi, fingerprint, records, stdlib, injected-fetcher]

# Dependency graph
requires:
  - phase: 34-01
    provides: the [jev] config reader (jev_config.py) the probe reads the configured Laya version from
provides:
  - jev_learn.py: Laya version source order, route and checkpoint fingerprint, version-keyed capability records, fetch-once of published notes through an injected fetcher
  - tests/test_jev_learn.py: 19 pure tests over fake fetchers
  - tests/fixtures/jev/laya-upstream.json: trimmed live shapes of /health, /openapi.json, PyPI and the README
affects: [34-06 (probe wiring with the real keyless fetcher), 34-07 (SKILL.md and reference text: stored notes are data), 34-08 (JEV-10 amendment)]

# Actuals (#2632): chars/4 over the realized diff of the plan's commits, measured with git diff
actuals:
  tokens: 17596
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Injected fetcher: learn_laya takes fetch(url) -> bytes, so every test runs with no network"
    - "Records written by mkstemp + os.replace into a 0700 folder; the file is 0600"
    - "Decision order before any fetch: no key, idle without a matching fingerprint, matching stored entry, fetch deadline"

key-files:
  created:
    - skills/jev-fast-decision/scripts/jev_learn.py
    - tests/test_jev_learn.py
    - tests/fixtures/jev/laya-upstream.json
  modified:
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "A server that exposes no version is keyed by fp:<fingerprint>; the fingerprint is sha256 of the canonical OpenAPI part plus the loaded models and their revisions (idle_seconds and other /health fields excluded)"
  - "An idle server (no loaded models) reuses the newest recorded fingerprint whose OpenAPI part matches; with none it waits as pending_idle and fetches nothing (Resolved Open Question 3)"
  - "A version-keyed entry is known only while its stored fingerprint matches the loaded one; a changed route list or revision fetches once and reports changed with previous_fingerprint (review C1-6)"
  - "No notes found while a source failed records nothing, so a forced refresh never replaces a good entry with a partial result (review C1-7)"
  - "A PyPI document that is not a JSON object, or whose info is not an object, counts as a failed source named unexpected JSON shape (review C3-3)"
  - "The OpenAPI route list keeps only HTTP method keys (get, put, post, delete, options, head, patch, trace); path-item keys such as parameters or summary stay out of the hash"
  - "JEV-10 stays Pending: this plan delivers the learning module, and Plan 06 wires the probe; requirements-completed is empty for that reason, and no mark-complete step ran"

patterns-established:
  - "Notes are data: decoded with replacement, stored as text, cut to 4000 characters, never rendered or executed"
  - "A feature named in the notes is reported as documented upstream, not verified here; verified features are excluded and no capability cell is written"

requirements-completed: []

# Metrics
duration: ~13min (worktree checked out 18:42, last task commit 18:55; the plan start time was not recorded)
completed: 2026-11-15
status: complete
---

# Phase 34 Plan 03: Laya version, fingerprint and published-notes records

**Laya version order, route and checkpoint fingerprint with idle reuse, and a fetch-once record of published notes through an injected fetcher, with 19 pure tests**

## Performance

- **Duration:** ~13 min (see frontmatter)
- **Tasks:** 3 of 3 completed
- **Files:** 3 created, 2 modified (plus the scratch fixture builder under the worktree `tmp/`, not committed)

## Accomplishments

- An unknown configured Laya version fetches its published notes once (PyPI per-version JSON, then the README) and records them under `<state>/jev/laya-capabilities.json`; a known key never fetches.
- A server that exposes no version is keyed by a fingerprint of its OpenAPI routes and loaded models. The fingerprint survives an idle unload (the last matching record is reused) and changes when a route or a checkpoint revision changes.
- Failed, partial, empty and odd-encoded fetches are handled as the review rules require: a failed fetch keeps the file byte for byte, and notes found in one source are recorded with a notice that names the failed source.
- New features named in the notes are reported as "documented upstream, not verified here"; verified features are excluded, and nothing in the module writes a capability cell.

## Task Commits

1. **Task 1: tracer, an unknown configured version fetches its notes once** - `3af2804` (feat)
2. **Task 2: fingerprint key and idle reuse** - `0df2d7c` (feat, tests and implementation together)
3. **Task 3: failure, empty, encoding, refresh and privacy rows** - `d55d881` (test)

The plan metadata commit follows this SUMMARY.

**TDD record:** Task 2 ran RED first. With the idle branch stubbed, `python3 tools/run_unittest_parallel.py tests.test_jev_learn` reported `FAILED (failures=2)` of 9 tests (`test_idle_reuses_the_last_matching_fingerprint`, `test_idle_with_a_configured_version_waits_or_reuses`). After the implementation it reported `ok`, 9 tests. Task 3's ten rows passed on their first run, so no RED state was observed for them and the module needed no change. To check that the rows guard the rules, I applied two temporary mutations: the C1-7 no-notes check disabled (1 failure, `test_pypi_failing_alone_records_nothing`) and the C3-3 shape check disabled (1 error, `test_failed_fetch_keeps_records_and_says_so`). Both were reverted, and the module matches the Task 2 commit.

## Files Created/Modified

- `skills/jev-fast-decision/scripts/jev_learn.py` - the Laya records module (stdlib only; no import of `jev_review`)
- `tests/test_jev_learn.py` - 19 tests: `TestLayaRecords` with `FakeFetch`, temp state folders, no network
- `tests/fixtures/jev/laya-upstream.json` - `health_idle`, `health_loaded`, `openapi`, `pypi_latest`, `pypi_0_4_27`, `readme`, `whats_new_latest`, built from the researcher's saved samples. The 0.4.27 bullet text is synthetic, as the plan states; the per-version PyPI shape comes from the saved sample.
- `Makefile`, `.pre-commit-config.yaml` - regenerated by `tools/gen_test_groups.py` to list `tests/test_jev_learn.py`

## Decisions Made

See the `key-decisions` frontmatter. The one interpretation beyond the plan text is the HTTP-method filter in `openapi_part`: the plan says "for each method key", and the filter keeps path-item metadata out of the hash.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree had no research samples or fixture folder**
- **Found during:** Task 1
- **Issue:** The worktree had no `tmp/auto/r325/research34/` and no `tests/fixtures/jev/`; the plan's fixture builder reads from `ROOT/tmp/auto/r325/research34`.
- **Fix:** Copied `laya-health.json`, `laya-openapi.json` and `pypi-laya-whatsnew.txt` read-only from the main checkout's scratch folder into the worktree's own `tmp/` (gitignored). Nothing was written to the main checkout.
- **Files modified:** none tracked (scratch only)
- **Verification:** `make_fixtures.py` produced the fixture; the module tests pass against it.
- **Committed in:** not applicable (scratch)

**2. [Rule 3 - Blocking] Pylint failed at the commit hook (Task 1)**
- **Found during:** Task 1 commit
- **Issue:** `useless-return` on the idle stub, and `too-many-locals` in `fetch_laya_notes` (17/15) and `learn_laya` (18/15).
- **Fix:** The stub drops its `return None`; `fetch_laya_notes` splits out `_read_source` and `_first_section`; `learn_laya` moves the fetch-and-store half into `_learn_fetch` and `_store`. Behaviour is unchanged, and the module tests passed before and after.
- **Files modified:** `skills/jev-fast-decision/scripts/jev_learn.py`
- **Verification:** `make pylint` passed; the Task 1 commit then landed.
- **Committed in:** `3af2804`

**3. [Rule 3 - Blocking] Ruff E501 in the test module (Task 2 and Task 3)**
- **Found during:** Task 2 and Task 3 gates
- **Issue:** Long lines in `tests/test_jev_learn.py`.
- **Fix:** `uv run --project <worktree> ruff format` on that file, plus one manual wrap of a long string literal.
- **Files modified:** `tests/test_jev_learn.py`
- **Verification:** `make ruff` passed.
- **Committed in:** `0df2d7c` and `d55d881`

**Total deviations:** 3 auto-fixed (all Rule 3, blocking gates or setup). None changed the plan's behaviour.
**Impact on plan:** No scope change. The one behaviour decision (HTTP-method filter) is recorded above.

## Issues Encountered

- The commit hook ran the full unit and arch suite once, because the regenerated `.pre-commit-config.yaml` counts as shared test machinery. It passed (133/133 modules).
- The plan's `estimate` was 70000 tokens and the measured realized diff is 17596 (chars/4). The estimate's scale covers the work, not only the diff; the measured figure is recorded as is.

## Verification

| Command | Exit | Result |
|---|---|---|
| `tools/run_unittest_parallel.py tests.test_jev_learn` (Task 1) | 0 | `=== tests.test_jev_learn: ok`, 2 tests |
| `tools/run_unittest_parallel.py tests.test_jev_learn` (Task 2 RED) | 1 | `FAILED (failures=2)`, 9 tests |
| `tools/run_unittest_parallel.py tests.test_jev_learn` (Task 2 GREEN) | 0 | `ok`, 9 tests |
| `tools/run_unittest_parallel.py tests.test_jev_learn` (final) | 0 | `ok`, 19 tests |
| `tools/run_unittest_parallel.py tests.test_jev_learn tests.test_gate_scope tests.test_arch` | 0 | `ok` for test_jev_learn (19), test_gate_scope (62) and test_arch (109); `3/3 modules passed` |
| `make ruff`, `make pylint`, `make pyright`, `make vulture` | 0 | all `Passed` |

## Next Phase Readiness

- Plan 06 wires `learn_laya` into `--probe` with the real keyless fetcher, validates the configured version (`valid_version`), and completes JEV-10.
- Plan 07 documents the stored notes as data, never instructions (T-34-09).
- Open: the per-version PyPI page shape is verified only from the saved sample, and the 0.4.27 bullets in the fixture are synthetic. A live fetch is needed to confirm the notes text, and the rails forbid network use in tests.

## Self-Check: PASSED

- Files found: `skills/jev-fast-decision/scripts/jev_learn.py`, `tests/test_jev_learn.py`, `tests/fixtures/jev/laya-upstream.json`
- Commits found in history: `3af2804`, `0df2d7c`, `d55d881`

---
*Phase: 34-jev-backends-by-host-and-laya-calibration*
*Completed: 2026-11-15*
