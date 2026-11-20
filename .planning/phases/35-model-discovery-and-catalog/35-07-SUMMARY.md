---
phase: 35-model-discovery-and-catalog
plan: 07
subsystem: catalog
tags: [arena, datasets-server, retry, fallback, synthetic-fixture]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 stub test modules; 35-02 hardcoding guard"
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/arena_source.py: ARENA_CATEGORIES, PAGE_CEILING, FETCH_DEADLINE_S, RETRIES, filter_url, rows_url, fetch_arena"
  - "tests/test_catalog_arena.py: 14 tests; tests/fixtures/arena_rows.json: synthetic Arena-shaped rows"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/arena_source.py
    - tests/fixtures/arena_rows.json
  modified:
    - tests/test_catalog_arena.py

requirements-completed: [HUB-02]

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (872 s, status=ok exit=0)"
---

# Phase 35 Plan 07: the Arena leaderboard source

One commit, `ba2a7f8 feat(35-07): add Arena leaderboard source`. Per the executor's report the first commit attempt failed ruff on the long
docstring and the retry passed the hook (97/97 staged modules).

## Accomplishments

- `fetch_arena(fetch_fn, progress, sleep_fn, page_length, clock_fn)` reads the official dataset through the datasets-server JSON API, one
  `/filter` query per category for the seven categories, 100 rows per page, three tries per page with a 1 s pause, sequential, bounded by
  `PAGE_CEILING` (115 pages) and `FETCH_DEADLINE_S` (240 s); progress lines start `arena: `; it returns `(data, ok)` and never raises.
- A failed category falls back to one complete `/rows` snapshot that replaces the filter data (never mixes); a failed fallback, a ceiling, a
  deadline, a malformed page or a premature empty page return the rows read so far with `ok` false.
- Data records `config` and `split` and keeps `rating`, `rating_lower`, `rating_upper` and `vote_count` per (category, model name); rows without a
  model name or with a non-numeric rating are skipped. The fixture says it is synthetic.

## Deviations and notes for the code review

- The module docstring is the plan's one-line text. To pass ruff E501 the executor added `# noqa: E501` on it and a file-level
  `# pylint: disable=line-too-long` on line 1: the only `line-too-long` suppression in the repository. Wrapping the docstring over several lines
  removes both; left for the code review (the plan's text does not require a single line).
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_arena tests.test_arch_hardcoded_models tests.test_gate_scope`: exit 0, 3/3 modules
  (14, 12 and 62 tests).
- `rg` finds `RETRIES = 3`, `PAGE_CEILING = 115`, `FETCH_DEADLINE_S = 240` and the seven-category tuple; the fixture holds the word `synthetic`.
- `make ruff`, `make pyright`, `make vulture` and `uv run pre-commit run pylint --files .../arena_source.py`: all Passed.
- Real-config audit after the lane (`tmp/run-2026-11-19/audit_c2.py`): nothing unexpected; only pi session logs and files of the Claude host and of
  another project's codex daemon changed.

## Self-Check: PASSED
