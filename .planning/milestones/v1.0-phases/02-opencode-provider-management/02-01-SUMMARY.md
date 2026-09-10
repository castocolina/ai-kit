---
phase: 02-opencode-provider-management
plan: 01
subsystem: opencode-providers
tags: [jsonc, scanner, atomic-write, list, remove]

# Dependency graph
requires: []
provides:
  - "stdlib-only ai-kit-opencode-providers CLI with list and remove <id>"
  - "four-state JSONC surgical scanner (jsonc_edit.py)"
  - "mode-preserving, symlink-respecting atomic writer"
  - "tests.test_ai_kit_opencode_providers wired into make test and pre-commit"
affects: [02-opencode-provider-management]

# Actuals
actuals:
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Four-state JSONC walker (string / escape / line-comment / block-comment), mutually suppressing"
    - "Two disjoint deletions for provider removal (entry span + one comma); comments between them survive"
    - "significant_indices (content) vs code_indices (structural) — trailing-comma strip uses CODE state only"
    - "write_preserving_mode: realpath + chmod original mode + mkstemp + os.replace"

key-files:
  created:
    - skills/ai-kit-opencode-providers/ai-kit-opencode-providers.py
    - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/__init__.py
    - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cli.py
    - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/jsonc_edit.py
    - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py
    - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/config_paths.py
    - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cross_reference.py
    - tests/test_ai_kit_opencode_providers.py
    - tests/e2e/docker/fixtures/opencode/opencode.jsonc
    - tests/e2e/docker/fixtures/opencode/opencode-expected-remove-beta.jsonc
    - tests/e2e/docker/fixtures/opencode/opencode-single-provider.jsonc
    - .planning/phases/02-opencode-provider-management/02-01-SUMMARY.md
  modified:
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "--config takes a full FILE path, not a directory (RESEARCH Open Question 1)."
  - "Removal is two disjoint deletions: the entry's key..value span and exactly one comma. Comments between them are never consumed."
  - "A depth-1 provider child whose value is not an object is reported, never removed, never crashed on."
  - "strip_trailing_commas uses code_indices (walker CODE state), never significant_indices membership."

patterns-established:
  - "Hand-authored expected JSONC fixture as independent ground truth — never generate expected output from the scanner under test."
  - "One run_cli helper is the module's sole subprocess.run call site; cwd required, env=scratch_env(root) on every call."
  - "Atomic config write resolves realpath first so a symlinked opencode.jsonc stays a symlink."

requirements-completed:
  - REQ-opencode-provider-list-remove

coverage:
  - id: D1
    description: "remove beta-router against the three-provider fixture is byte-identical to the hand-authored expected file"
    requirement: REQ-opencode-provider-list-remove
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_opencode_providers.TestTracerRemoveEndToEnd.test_remove_beta_router_matches_hand_authored_fixture"
        status: pass
    human_judgment: false
  - id: D2
    description: "First, middle, last, and sole entry removals leave JSON that parses after comment stripping"
    requirement: REQ-opencode-provider-list-remove
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_opencode_providers.TestRemoveCommaCases"
        status: pass
    human_judgment: false
  - id: D3
    description: "list prints id / npm / baseURL from an explicit allowlist and never leaks the apiKey sentinel"
    requirement: REQ-opencode-provider-list-remove
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_opencode_providers.TestListOutput"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_opencode_providers.TestListRedaction"
        status: pass
    human_judgment: false

completed: 2026-09-09
status: complete
---

# Phase 2 Plan 01: Opencode Provider CLI Summary

**`ai-kit-opencode-providers` lists and removes custom opencode providers by surgically editing JSONC, preserving every other byte, comment, and permission bit.**

## Performance

- **Tasks:** 3
- **Files created:** 12 (plus this SUMMARY)
- **Files modified:** 2

## Accomplishments

- Four-state JSONC walker locates depth-1 `"provider"` children, skips nested decoys, and skips non-object values without breaking the scan.
- `remove <id>` deletes the first matching entry plus one comma; comments between those two deletions survive. Missing ids and missing files are clean no-ops or named errors.
- `list` renders a three-column table (ID, NPM, BASE URL) from an explicit field allowlist. Trailing commas in CODE state are tolerated; in-string `,}` is not stripped. apiKey never reaches output.
- Atomic writer resolves `realpath`, copies the original mode onto the temp file, and unlinks the temp on `OSError`. A symlink config stays a symlink.
- Test module is in both the `Makefile` `test` target and the pre-commit `unittest` hook; the skill is in the `ruff` and `py-compile` `files:` regexes.

## Task Commits

1. **Task 1: End-to-end `remove <id>`** — `dcc36dd` (feat)
2. **Task 2: Comma-position case split and clean no-ops** — `5cbee49` (feat)
3. **Task 3: `list` with an explicit field allowlist** — `bd01318` (feat)

## Files Created/Modified

- `skills/ai-kit-opencode-providers/` — CLI shim, scanner, atomic write, path discovery, local review-spec scan
- `tests/test_ai_kit_opencode_providers.py` — tracer, comma cases, walker invariants, list/redaction
- `tests/e2e/docker/fixtures/opencode/` — three-provider fixture, hand-authored expected output, single-provider fixture
- `Makefile`, `.pre-commit-config.yaml` — module and lint wiring

## Decisions Made

- `--config` is a full file path (Open Question 1, locked in-plan).
- `list --json` stays deferred (Open Question 2).
- pyright/vulture stay `tools/`-scoped; ruff and py-compile now cover this skill.

## Deviations from Plan

None. Two Task 2 assertions were tightened after GREEN (comma count after comment stripping; `"solo-router"` quoted rather than as a substring of `"solo-router/default"`). Scanner behavior matched the plan; the original assertions did not.

**Total deviations:** 0
**Impact on plan:** None.

## Issues Encountered

None.

## User Setup Required

None. SKILL.md and the remaining cross-reference scan (global review-spec + cached catalog) belong to plan 02-02.

## Next Phase Readiness

Ready for 02-02 (cross-reference audit trail + SKILL.md). ROADMAP Phase 2 success criteria 1, 2, and 3 are true for this plan's scope: `list` prints id/npm/baseURL without leaking apiKey; `remove` is a byte-preserving surgical edit; a missing id is a clean no-op.

## Verification (captured)

```
$ python3 -m unittest tests.test_ai_kit_opencode_providers -v
Ran 36 tests in 0.183s
OK

$ make test
Ran 1219 tests in 11.724s
OK (skipped=19)
```

AST gates: `MISSING: []`, `SEEDED_CALLS: 1`, `CODE_STATE_ONLY: True`, `ENV_EVERYWHERE` scoped, one `subprocess.run(` call site.

## Self-Check: PASSED

- [x] `remove beta-router` matches `opencode-expected-remove-beta.jsonc` byte-for-byte
- [x] First/middle/last/sole comma cases parse after `strip_jsonc_comments`
- [x] `list` redacts `DO-NOT-PRINT`; trailing commas and in-string `,}` are correct
- [x] `tests.test_ai_kit_opencode_providers` is in Makefile and pre-commit
- [x] `skills/ai-kit-opencode-providers` is in ruff and py-compile regexes
- [x] Production commits exist (`dcc36dd`, `5cbee49`, `bd01318`)

---
*Phase: 02-opencode-provider-management*
*Completed: 2026-09-09*
