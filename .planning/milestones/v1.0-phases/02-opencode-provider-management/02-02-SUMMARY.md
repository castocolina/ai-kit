---
phase: 02-opencode-provider-management
plan: 02
subsystem: opencode-providers
tags: [cross-reference, skill-md, skill-judge, clean-room]

# Dependency graph
requires:
  - "stdlib-only ai-kit-opencode-providers CLI with list and remove <id>"
  - "scan_review_spec / format_reference / local_review_spec_path"
  - "run_cli helper with env=scratch_env(root) passthrough"
provides:
  - "collect_references scans local review-spec, global review-spec, and cached catalog"
  - "scanned-inactive audit status under strategy = local-only"
  - "skills/ai-kit-opencode-providers/SKILL.md skill-judge bar"
affects: [02-opencode-provider-management]

# Actuals
actuals:
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "isinstance(v, str) filter on catalog fields — never str() coerce"
    - "scratch_env copy-then-override for HOME/XDG_CONFIG_HOME/XDG_CACHE_HOME"
    - "audit trail of (path, scanned|absent|scanned-inactive) printed before write"

key-files:
  created:
    - skills/ai-kit-opencode-providers/SKILL.md
    - .planning/phases/02-opencode-provider-management/02-02-SUMMARY.md
  modified:
    - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cross_reference.py
    - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/config_paths.py
    - skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cli.py
    - tests/test_ai_kit_opencode_providers.py
    - README.md

key-decisions:
  - "Scan both review-spec tiers plus the cached catalog; a local-only strategy still reports a global hit, labelled scanned-inactive / not active."
  - "Non-string catalog field values are skipped by isinstance(v, str), never stringified."
  - "SKILL.md is a thin CLI wrapper — host-neutral five-candidate resolution, no algorithm restatement."

patterns-established:
  - "Cross-reference tests build synthetic TOML/JSON in a tempfile scratch tree; the subprocess test proves scoping by asserting every printed audit path is inside that tree."

requirements-completed:
  - REQ-opencode-provider-cross-reference-check

coverage:
  - id: D1
    description: "collect_references returns references from both review-spec and catalog when both match"
    requirement: REQ-opencode-provider-cross-reference-check
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_opencode_providers.TestCrossReferenceCombined.test_both_sources_return_both_references"
        status: pass
    human_judgment: false
  - id: D2
    description: "cmd_remove prints warnings then removes; exit 0; no prompt"
    requirement: REQ-opencode-provider-cross-reference-check
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_opencode_providers.TestCrossReferenceNonBlocking.test_remove_warns_and_proceeds_inside_scratch_tree"
        status: pass
    human_judgment: false
  - id: D3
    description: "local-only strategy reports global hits as scanned-inactive with a not-active qualifier"
    requirement: REQ-opencode-provider-cross-reference-check
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_opencode_providers.TestCrossReferenceLocalOnlyStrategy"
        status: pass
    human_judgment: false
  - id: D4
    description: "SKILL.md documents list/remove, three sources, substring false-positive, exit codes 0/1/2, edge cases, NEVER"
    requirement: REQ-opencode-provider-cross-reference-check
    verification:
      - kind: other
        ref: "skills/ai-kit-opencode-providers/SKILL.md"
        status: pass
    human_judgment: true
  - id: D5
    description: "skill-judge bar: no remaining Critical/Important, score >= 96/120, no regression"
    requirement: REQ-opencode-provider-cross-reference-check
    verification:
      - kind: other
        ref: "skill-judge first 103/120 Grade B (1 Important); final 108/120 Grade A, Critical 0, Important 0"
        status: pass
    human_judgment: true

completed: 2026-09-09
status: complete
---

# Phase 2 Plan 02: Cross-Reference Scan and SKILL.md Summary

**`remove` now names every place the target id is referenced before it writes, and `SKILL.md` makes the CLI an invokable skill.**

## Performance

- **Tasks:** 3
- **Files created:** 2 (plus this SUMMARY)
- **Files modified:** 5

## Accomplishments

- `collect_references` scans local `.aikit/review-spec.toml`, global `~/.config/ai-kit/review-spec.toml`, and the cached model catalog, in that order, and returns an audit trail (`scanned` / `absent` / `scanned-inactive`).
- A `strategy = "local-only"` local review-spec still reports a global-tier hit, labelled `scanned-inactive` with a "not active" qualifier on the warning line.
- Catalog scan filters with `isinstance(v, str)` — a dict-valued `provider` neither matches nor prints.
- `cmd_remove` prints the audit and every warning **before** `write_preserving_mode`; removal is unconditional (D-04).
- Every cross-reference test is scratch-rooted. `TestCrossReferenceNonBlocking` passes `env=scratch_env(root)` through `run_cli` and asserts every printed audit path is inside that tree.
- `SKILL.md` is a thin, host-neutral wrapper (five candidate directories including `opencode/skills` and `agents/skills`). README Contents gained one row.

## Task Commits

1. **Task 1: Complete the cross-reference scan** — `e495d62` (feat)
2. **Task 2: SKILL.md and README Contents row** — `f150ee3` (docs)
3. **Task 3: skill-judge Important findings** — `6fe965b` (docs)
4. **This SUMMARY** — committed with this file

## Files Created/Modified

- `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cross_reference.py` — `scan_catalog`, `review_spec_strategy`, `collect_references`
- `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/config_paths.py` — `global_review_spec_path`, `catalog_path`
- `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cli.py` — `cmd_remove` prints audit then warnings then writes
- `tests/test_ai_kit_opencode_providers.py` — five new test classes
- `skills/ai-kit-opencode-providers/SKILL.md` — new
- `README.md` — one Contents row

## Decisions Made

- Scanning the global review-spec tier is a deliberate superset of REQ wording, because `cfg_resolve` merges it by default.
- Under `local-only`, over-warn and label rather than drop the global tier.
- Non-string catalog values are skipped, never coerced.

## Deviations from Plan

1. **`make validate` exits 2 on pre-existing ruff/pylint debt outside this plan's files.** Same findings Phase 01.1 already logged in `deferred-items.md` (`tools/status-line.py` E501, `tools/wizard_app.py` E501/RUF012, plus older `tests/test_ai_kit_spec.py` E501/RUF059). This plan did not modify those files. `uv run ruff check skills/ai-kit-opencode-providers tests/test_ai_kit_opencode_providers.py` reports `All checks passed!`. ONESHOT-RULES Rule 4: log, do not silently fix an unrelated file. `make test`, `make lint`, and `make e2e-docker` are green.

**Total deviations:** 1
**Impact on plan:** Gate evidence for this skill's own modules is green; the all-files `make validate` hook remains red on pre-existing debt.

## Issues Encountered

- Nested-decoy fixture still contains the substring `"beta-router"` after a successful remove. Assertions check remaining provider ids via `iter_provider_entries`, not a raw substring of the stripped JSONC.

## User Setup Required

None.

## Next Phase Readiness

Ready for phase close / verify-work. ROADMAP Phase 2 success criterion 4 is true: before removing, the user is warned by name of every place the target id is referenced, and removal is never blocked on that warning.

## Verification (captured)

```
$ python3 -m unittest tests.test_ai_kit_opencode_providers -v
Ran 60 tests in 0.218s
OK

$ python3 -c "...scan_catalog AST..."
STR_FILTERED: True ['', 'Reference', 'isinstance', 'open']

$ grep -v '^[[:space:]]*#' tests/test_ai_kit_opencode_providers.py | grep -c '.aikit'
1

$ python3 -c "...SCRATCH_REVIEW_SPEC_RELPATH window..."
SCRATCH_ROOTED: True

$ python3 -c "...TestCrossReferenceNonBlocking env=..."
ENV_SCOPED: True

$ make test
...
16 passed, 0 failed
EXIT=0

$ make lint
shellcheck tools/install.sh tests/test_install.sh
python3 -m py_compile tools/setup.py tools/status-line.py tools/statusline-doctor.py
EXIT=0

$ make validate
ruff.....................................................................Failed
pylint...................................................................Failed
pyright..................................................................Passed
vulture..................................................................Passed
shellcheck...............................................................Passed
py-compile...............................................................Passed
unittest (core)..........................................................Passed
unittest (wizard — uv)...................................................Passed
EXIT=2
# ruff on this plan's files: All checks passed!
# Failures are pre-existing in tools/status-line.py, tools/wizard_app.py, tests/test_ai_kit_spec.py (Phase 01.1 deferred-items.md).

$ make e2e-docker
==> make lint
shellcheck tools/install.sh tests/test_install.sh
python3 -m py_compile tools/setup.py tools/status-line.py tools/statusline-doctor.py
==> ai-kit clean-room E2E: PASS
EXIT=0
```

Clean-room preflight asserts `~/.config/opencode` is absent inside the container, so a green `make e2e-docker` is positive evidence that the suite does not depend on uz's real config directories.

## skill-judge

- **First run:** 103/120 (86%, Grade B). Knowledge ratio E:A:R approx 75:20:5. Pattern: Tool.
  - Critical: none.
  - **Important:** `$SKILL_DIR` was named as the fifth resolution candidate but never assigned, so a checkout install could report "not installed".
  - Suggestions (not blocking): empty-list message undocumented; missing-config "never create" not restated; no explicit "if the user asked to add/edit, stop" gate.
- **Addressed:** fifth candidate is now `$(dirname "absolute path to THIS SKILL.md")` with an instruction to substitute this SKILL.md's directory; Scope now splits config-based vs credential-based providers before invoke; empty-list and missing-config stop conditions documented.
- **Final run:** 108/120 (90%, Grade A). Critical 0, Important 0. No regression vs 103.

## Self-Check: PASSED

- [x] Both review-spec tiers and the cached catalog are scanned
- [x] Global-tier hit under `local-only` is labelled not-active
- [x] Dict-valued catalog `provider` produces zero references (`STR_FILTERED: True`)
- [x] `TestCrossReferenceNonBlocking` is env-scoped; audit paths stay inside the scratch tree
- [x] SKILL.md documents list/remove, `--config`, exit codes 0/1/2, substring false-positive, NEVER
- [x] README Contents gained exactly one row (`git diff --stat README.md` showed 1 insertion)
- [x] `make test` EXIT=0, `make lint` EXIT=0, `make e2e-docker` PASS
- [x] skill-judge final 108/120, no Critical/Important
- [x] No step read or wrote `~/.config/opencode/opencode.jsonc`, `~/.claude`, `~/.cursor`, or `~/.codex` — all CLI examples and tests used `/tmp` scratch trees; clean-room E2E preflight asserts those dirs are absent

---
*Phase: 02-opencode-provider-management*
*Completed: 2026-09-09*
