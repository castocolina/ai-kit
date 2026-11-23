---
phase: 35-model-discovery-and-catalog
plan: 06
subsystem: catalog
tags: [jev, name-judge, class-judge, lookup-copy, arch-drift]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 stub test modules; 35-02 hardcoding guard"
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/jev_names.py: JEV_ENTRY_REL, SKILLS_ROOTS, skills_roots, find_jev, name_item, class_item, ask_items, name_judge, class_judge"
  - "tests/test_catalog_jev_names.py: TestJevNames (13 tests)"
  - "tests/test_arch.py: jev_names.py listed in LOOKUP_COPIES (root-order drift check covers the copy)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/jev_names.py
  modified:
    - tests/test_catalog_jev_names.py
    - tests/test_arch.py

requirements-completed: [HUB-03]

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (1040 s, status=ok exit=0)"
---

# Phase 35 Plan 06: the jev seam for catalog names and classes

One commit, `e43daf9 feat(35-06): add optional jev catalog judges`. Per the executor's report its first commit attempt failed ruff and the retry
passed the hook (100/100 staged modules).

## Accomplishments

- A lookup copy of fold-step's jev client (`JEV_ENTRY_REL`, `SKILLS_ROOTS`, `skills_roots`, `find_jev`) with the own-root three dirnames up.
- `name_item` and `class_item` build one choice item per name or model: only names go in (cleaned of control characters, cut to 80 characters, at
  most five candidates); `ask_items` sends ladder calls of at most 7000 JSON characters with a per-call timeout and turns old clients, timeouts,
  malformed output and `needs_fallback`/`forced`/`fallback` columns into "no choice", never raising.
- `name_judge` and `class_judge` return `None` when no jev client is installed and otherwise a batch judge in the plan-05 contract:
  `(choice, confidence, reason)` per pair, a confident `none` stays unmatched, an `e<i>` answer maps back to the caller's original name.
- `LOOKUP_COPIES` in `tests/test_arch.py` lists the new file.

## Deviations and notes for the code review

- The plan's acceptance line says "thirteen tests"; the module has 13 (3 of Task 1 plus 10 of Task 2).
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_jev_names tests.test_arch tests.test_arch_hardcoded_models`: exit 0, 3/3 modules
  (13, 109 and 12 tests); the lookup-copy drift check in `tests.test_arch` covers `jev_names.py`.
- `rg` finds `JEV_ENTRY_REL = os.path.join("jev-fast-decision", "scripts", "jev_review.py")`, `def ask_items(`, `def class_judge(` in the module and
  the `LOOKUP_COPIES` row at `tests/test_arch.py:1697`.
- `make ruff`, `make pyright`, `make vulture` and `uv run pre-commit run pylint --files .../jev_names.py`: all Passed.
- Real-config audit after the lane (`tmp/run-2026-11-19/audit_c2.py`): nothing unexpected; only pi session logs and files of the Claude host and of
  another project's codex daemon changed.

## Self-Check: PASSED
