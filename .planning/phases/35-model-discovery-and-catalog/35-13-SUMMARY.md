---
phase: 35-model-discovery-and-catalog
plan: 13
subsystem: profiles
tags: [opencode, cli-profile, runner-comments, flag-guard, baseline]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-02 hardcoding guard and baseline; 35-09 recorded opencode help and the flag guard"
provides:
  - "cli-profiles/opencode.md rewritten to the recorded opencode 2.3.2 help (last_verified and source from meta.json, --standalone formulas, variants[].id from the model API)"
  - "cli-profiles/codex.md example sentence rewritten with invented placeholders (the live-test claim stays attached to the real run)"
  - "cross-ai.mjs template: opencode comment lines rewritten (argv formulas unchanged); .planning/scripts/cross-ai.mjs re-rendered from it"
  - "tests/fixtures/no_hardcoded_models_baseline.json: the two profile entries removed"
  - "tests/test_opencode_help_flags.py: help_flags, command_flags, negative_claims and four semantic tests (11 tests in all)"

key-files:
  modified:
    - skills/ai-kit-spec-review/references/cli-profiles/opencode.md
    - skills/ai-kit-spec-review/references/cli-profiles/codex.md
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - .planning/scripts/cross-ai.mjs
    - tests/fixtures/no_hardcoded_models_baseline.json
    - tests/test_opencode_help_flags.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite; the work was done and committed in attempt 1, then the lane ended with exit 75 (status=transient, 12 attempts, ECONNRESET, retry_after_s=600) before the executor's report"
---

# Phase 35 Plan 13: opencode profile and runner comments match the recorded help

One commit, `a1f5677 docs(35-13): align opencode profile and runner help`, made at 06:05:33 inside the lane's first attempt (the commit hook
passed). The attempt then failed with `Connection error.: read ECONNRESET`, as did eleven retries of the runner's soft ladder, so the lane ended
with `AIKIT-XAI status=transient exit=75 retry_after_s=600` and no executor report. The tree was clean and the commit complete, so no lane re-run
was needed for this plan; this SUMMARY comes from my own checks of the commit.

## Accomplishments

- The opencode profile names the recorded version and date, lists the two runner formulas with `--standalone`, says `opencode models` accepts the
  global `--standalone` and `--server` flags, and says effort levels come from the model API's `variants[].id`. No real provider or model name is
  left in it; the codex profile holds `placeholder-model-1` examples under a `model-example:` marker.
- The runner template's opencode comment lines no longer cite 2.0.29 or claim `opencode models` lacks `--standalone`; the argv formulas are
  unchanged. The project copy was re-rendered from the template (header sha256 changed, no `.new` file).
- The flag guard now checks command semantics: run flags against run help or the global help, models flags against models help or the global help,
  and negative claims ("has no such flag") against the recorded help, with planted-case non-vacuity tests.

## Deviations and notes for the code review

- No executor report exists (transport failure at the end of the run); the deviations list is therefore only what I found: none against the plan's
  acceptance criteria. The commit message type is `docs` although the commit also changes a test file and the runner copy.
- `make check-dogfood` passes (it only prints the known stale judge-record digests, which this plan did not change).
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not an executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_opencode_help_flags tests.test_arch_hardcoded_models tests.test_cross_ai_skill_text`: exit 0,
  3/3 modules (11, 12 and 30 tests).
- `make ruff`, `make pyright`, `make vulture`: Passed; `make check-dogfood`: ok (pristine runner copy).
- Acceptance checks, run by `tmp/run-2026-11-19/accept-35-13.sh`: opencode.md has `--standalone` (3), `variants[].id` (1), no `2.0.29`;
  `last_verified` 2026-11-20 equals meta.json `recorded`; no baseline entry for either profile; `Confirmed live` once in codex.md; the template has no
  `2.0.29` or `has no such flag` and keeps the exec formula; the copy holds the new comment once; `.planning/scripts/` holds only `cross-ai.mjs`;
  eleven tests in the flag module.
- Real-config audit (`audit_c2.py` against the wave marker): nothing unexpected; only pi session logs are newer.

## Self-Check: PASSED
