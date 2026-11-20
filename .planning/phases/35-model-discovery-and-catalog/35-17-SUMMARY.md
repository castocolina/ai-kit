---
phase: 35-model-discovery-and-catalog
plan: 17
subsystem: catalog
tags: [herdr, copilot, interactive-view, unverified]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-11 optional_sources (sanitize_name, record_names)"
provides:
  - "herdr_source.py: COPILOT_ARGV, READY_REGEX, LIST_REGEX, WAIT_MS, READ_LINES, LABEL, herdr_available, parse_pane_names, read_interactive_names"
  - "tests/herdr_fakes.py: write_herdr_fake, herdr_calls (helper, not a test module)"
  - "tests/test_catalog_herdr.py: 11 tests (TestHerdrSource)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/herdr_source.py
    - tests/herdr_fakes.py
  modified:
    - tests/test_catalog_herdr.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (1001 s, status=ok exit=0, attempts=1, cycles=0)"
---

# Phase 35 Plan 17: the herdr reader for copilot's interactive model view

One commit, `d96f456 feat(35-17): read copilot interactive models via herdr` (pre-fold). The executor's first runs of `make ruff` and pylint, and its
first commit attempt, failed on lint findings in the new files; it fixed them, and the final hook ran 98/98 modules green.

## Accomplishments

- `read_interactive_names("copilot", env, ...)` opens one pane beside the caller, starts `copilot --allow-all --no-auto-update`, sends `/model`,
  reads the pane, sends `esc` and closes the pane in a `finally`; a failed step returns its name (`pane failed: <step>`), an unusable split
  id starts nothing, and a failed close adds `; pane close failed: <id>` to the status.
- Absent herdr is a visible reason with no call: `HERDR_ENV` not 1, or no herdr CLI on PATH. Any runtime other than copilot answers
  `no interactive view known for <runtime>`.
- `parse_pane_names` reads names only after a line equal to `/model` (the echo of the typed command; none gives `no list boundary`), takes the
  first token of each later line, drops colon-ended tokens, passes the rest through `sanitize_name` and the digit-or-dash-or-slash filter.
  Every record is labeled `interactive view, unverified`, with source `interactive view` and the day's date; none is marked verified.
- The real herdr and copilot were never run; the tests use `tests/herdr_fakes.py` (an executable fake that answers an exact argv table and logs
  every call). The live `/model` check stays the manual-only item of Amend-11.

## Deviations and notes for the code review

- Order of `esc`: the plan sends `esc` right after `read` and parses afterwards; the code parses first and sends `esc` only when names were
  found. With `no list boundary` or `no names read` the pane is closed without an `esc` (the success-path call order the test pins is the
  plan's).
- A failed `pane close` also empties the returned records (status `<status>; pane close failed: <id>`, records `[]`): the plan only asks for
  the status suffix, and `test_failed_close_reported` pins the empty list. Names read from the pane are valid even when the close failed, so the
  review may prefer to keep them.
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_herdr tests.test_arch_hardcoded_models tests.test_gate_scope tests.test_arch tests.test_skill_text_history tests.test_catalog_optional_sources`:
  exit 0, 6/6 modules (11, 14, 62, 109, 45 and 13 tests).
- `make ruff`, `make pyright`, `make vulture`, and pylint over `herdr_source.py`: all Passed.
- I read `herdr_source.py` and `tests/herdr_fakes.py` whole and the test module whole.
- Real-config audit (`audit_c2.py` against the wave marker): two pi session logs; the Claude host's own `.credentials.json`, `daemon.log` and
  `history.jsonl`; and four user-level instruction files (`~/.claude/CLAUDE.md`, `~/.config/opencode/AGENTS.md`, `~/.cursor/AGENTS.md`,
  `~/.pi/agent/AGENTS.md`) rewritten within 7 ms of each other at 13:26:02 with a new "Temporary files and test cleanup" block. That looks like
  one program updating every host at once (an installer or sync outside this plan: the plan's code writes nothing to a home folder and its tests
  run under a scratch HOME), but I cannot prove which process did it; it is listed for the owner.

## Self-Check: PASSED
