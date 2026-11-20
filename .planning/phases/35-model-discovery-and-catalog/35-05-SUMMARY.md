---
phase: 35-model-discovery-and-catalog
plan: 05
subsystem: catalog
tags: [model-names, effort-parsing, candidates, batch-resolution]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 stub test modules; 35-02 hardcoding guard"
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/model_names.py: EFFORT_WORDS, BlankNameError, NameParts, split_effort, known_ids_from_models_dev, candidates, Resolution, resolve_many, JUDGE_FLOOR, JUDGE_MIN_CONFIDENCE"
  - "tests/test_catalog_names.py: TestEffortParsing (8) and TestResolution (9)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/model_names.py
  modified:
    - tests/test_catalog_names.py

requirements-completed: [HUB-02]

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (695 s, status=ok exit=0)"
---

# Phase 35 Plan 05: one parser for host model names

One commit, `42c2eff feat(35-05): add model name resolution`.

## Accomplishments

- `split_effort(runtime, host_id, known_ids)` takes the effort out of a name by the runtime's own style (pi `:level`, opencode `#variant`,
  cursor bracket and trailing dash word, Arena parenthetical); codex, claude and copilot names stay whole; a name whose full id is in the
  known models.dev ids stays whole; a blank name raises `BlankNameError("blank model name")`; the stored host id is never changed.
- `known_ids_from_models_dev(payload)` yields bare and provider-qualified ids and skips malformed provider entries.
- `candidates` lists normalized exact matches first, else fuzzy matches at or above the floor, ordered by ratio then name, at most five by default.
- `resolve_many` matches deterministically first (one exact match, or a clear fuzzy winner); a tie stays `unmatched` with every candidate
  named; only unmatched names with candidates go, at most five each, to one injected `judge_batch` call; an answer counts only as a
  3-tuple whose choice is one of that name's candidates and whose confidence is a number from 0.5 to 1.
- The module never calls jev and imports no `subprocess`.

## Deviations and notes for the code review

- The plan's acceptance line says 16 tests; its two tasks list 8 plus 9 test names and the module has 17 tests.
- `resolve_many` narrows `judge_batch` with `assert judge_batch is not None` (pyright); it is reached only when a name was queued, which
  needs a judge.
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_names tests.test_arch_hardcoded_models`: exit 0, 2/2 modules (17 and 12 tests).
- `rg` finds `def candidates(`, `class Resolution(NamedTuple)`, `def resolve_many(`, `JUDGE_MIN_CONFIDENCE = 0.5`, `JUDGE_FLOOR = 0.5` and
  no `subprocess` in `model_names.py`.
- `make ruff`, `make pyright`, `make vulture` and `uv run pre-commit run pylint --files .../model_names.py`: all Passed.
- Real-config audit after the lane (`tmp/run-2026-11-19/audit_c2.py`): nothing unexpected; only pi session logs and files of the Claude host
  and of another project's codex daemon changed.

## Self-Check: PASSED
