---
phase: 05-usage-metrics-dashboard
plan: 04
subsystem: usage-metrics
tags: [usage-metrics, refinement, decomposer, cwd, cross-runtime]

requires:
  - "05-01 CaptureResult contract, refined_commands schema, Wave-1 Claude simple-command refiner"
  - "05-02 opencode session/message/part envelopes with top-level session_id/message_id/time_created"
  - "05-03 Codex session_id sibling + Cursor source_confidence=low envelopes"
provides:
  - "decomposer.py: quote-aware &&/;/| split with control-flow suppression and unclassified fallback"
  - "cwd_state.py: chronological resolve-then-observe CwdState with no filesystem access"
  - "refiner.refine_all: 5-source refinement replacing Wave 1's simple-commands-only entry point"
affects: [05-usage-metrics-dashboard]

actuals:
  tokens: 155000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Quote-aware single-pass char scan (JSONC _classify technique, POSIX quoting: single quotes never honor \\)"
    - "Control-flow nesting-depth counter with whitespace-token-boundary keyword matching"
    - "RESOLVE_CWD dict-of-callables keyed by runtime (per-record CwdState for Claude; session-long for opencode/Codex/Cursor)"
    - "Turn-level token/price attribution duplicated onto every step-row; consumers DISTINCT before SUM"

key-files:
  created:
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/decomposer.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cwd_state.py
    - .planning/phases/05-usage-metrics-dashboard/05-04-SUMMARY.md
  modified:
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refiner.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refined_store.py
    - tests/test_ai_kit_usage_metrics.py

key-decisions:
  - "command_shape is exactly 3 values (simple | control_flow_script | unclassified); compound is the derived fact step_count > 1."
  - "Claude uses a fresh per-record CwdState seeded from native cwd, discarded after that record's steps — never threaded across tool-calls."
  - "Opencode workdir, when present, REBASES CwdState.current before observe, not merely overrides the returned value."
  - "Opencode chronological walk sorts by time_created, falling back to record_id only on an exact tie — never by source_line as the primary key."
  - "Codex token attribution is the incremental delta between consecutive token_count events, never the raw cumulative total."
  - "rtk history rows populate dedicated rtk_* columns; tokens_input/tokens_output stay None. tee/parse_failure produce no refined row."

patterns-established:
  - "decomposer.py and cwd_state.py are independent units; refiner.py composes them and neither imports the other."
  - "Realistic TestRefinerFull envelopes are built via capture_*.py's own _envelope/_base_envelope helpers so envelope-shape drift breaks this test too."
  - "source_confidence = envelope.get('source_confidence') or 'high' on every refined row (Cursor's low flows through; everyone else defaults high)."

requirements-completed:
  - REQ-usage-metrics-refinement-pipeline

coverage:
  - id: REQ-usage-metrics-refinement-pipeline
    description: "Compound decomposition, cross-tool-call cwd resolution, control_flow_script vs unclassified, family tagging across all 5 sources"
    requirement: REQ-usage-metrics-refinement-pipeline
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestDecomposer"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCwdState"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestRefinerFull"
        status: pass
    human_judgment: false
  - id: PRD-EXAMPLE-1
    description: "cd src && grep -r TODO . two-step split with grep resolved_cwd from preceding cd"
    requirement: REQ-usage-metrics-refinement-pipeline
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestRefinerFull.test_claude_cd_and_grep_two_steps_with_cwd"
        status: pass
    human_judgment: false
  - id: PRD-EXAMPLE-2
    description: "Later separate grep -r FIXME . reuses carried cwd"
    requirement: REQ-usage-metrics-refinement-pipeline
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCwdState.test_prd_later_separate_call_reuses_carried_cwd"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestRefinerFull.test_opencode_later_separate_call_reuses_cwd"
        status: pass
    human_judgment: false
  - id: PRD-EXAMPLE-3
    description: "for-loop control-flow block as one opaque control_flow_script row"
    requirement: REQ-usage-metrics-refinement-pipeline
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestRefinerFull.test_for_loop_is_one_control_flow_script_row"
        status: pass
    human_judgment: false
  - id: T-05-12
    description: "Malformed Codex arguments JSON degrades that one record without aborting refine_all"
    requirement: REQ-usage-metrics-refinement-pipeline
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestRefinerFull.test_codex_malformed_arguments_does_not_abort"
        status: pass
    human_judgment: false

completed: 2026-09-10
status: complete
---

# Phase 5 Plan 04: Cross-AI Execution Dispatch Summary

**Every raw shell-command record across all 5 captured sources now produces correctly-shaped `refined_commands` rows: compound `&&`/`;`/`|` split, control-flow kept intact, cwd resolved per D-05, tokens attributed once per turn.**

## Performance

- **Tasks:** 3
- **Files created:** 2 (plus this SUMMARY)
- **Files modified:** 4
- **Commits:** 3

## Accomplishments

- `decomposer.scan_command` is a single left-to-right scan tracking single/double quotes (inside single quotes `\` is a literal backslash) plus a control-flow nesting-depth counter (`if→fi`, `case→esac`, `for|while|until|select→done`). Unquoted `||`, heredoc (`<<`/`<<-`/`<<~`), `$(`, backtick, and leading `(` force `has_unsupported_shape`; `decompose` then returns one `unclassified` dict for the whole original text. Exactly 3 `command_shape` values exist.
- `CwdState` is constructed once per session (or once per Claude raw record) and walked resolve-then-observe. Bare `cd` is a documented no-op. No `os.path.exists`/`isdir`/`stat` anywhere in the module — a nonexistent path still records the resolved string.
- `refiner.refine_all` groups by `(runtime, session_id)` and walks chronologically with a per-runtime sort key: opencode by `time_created` (tie-break `record_id`); Claude/Codex/Cursor by `timestamp` falling back to `source_line`. `RESOLVE_CWD` dispatches cwd strategy. Opencode `workdir` rebases `CwdState.current` before `observe`. Codex tokens are incremental deltas. Cursor tokens/price stay `None`. rtk `history` populates dedicated `rtk_*` columns; `tee`/`parse_failure` produce no row. `cli.cmd_refine` now reads every source's raw JSONL and calls `refine_all`.
- `refined_store.py` documents the DISTINCT-before-SUM rule for turn-level token/price figures.

## Task Commits

1. **Task 1: Mechanical decomposer** — `e579f06` (feat)
2. **Task 2: Chronological cwd-resolution state machine** — `a3afc22` (feat)
3. **Task 3: Wire refine_all across all 5 sources** — `9b5c4ac` (feat)

## Files Created/Modified

- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/decomposer.py` — new
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cwd_state.py` — new
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refiner.py` — `refine_all` public entry; Wave-1 `refine_simple_commands` kept as helper
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py` — `cmd_refine` reads all 5 raw JSONL files, calls `refine_all`
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refined_store.py` — dedup-before-sum docstring
- `tests/test_ai_kit_usage_metrics.py` — TestDecomposer + TestCwdState + TestRefinerFull

## Decisions Made

None beyond the plan. Followed Round 1's 3-value `command_shape`, Round 1 workdir REBASE, Round 3 per-record Claude `CwdState`, Round 3 opencode `time_created` sort, Round 3 `source_confidence` threading, and T-05-12's malformed-arguments degrade.

## Deviations from Plan

- Wave 1's `refine_simple_commands` is kept as a helper (and `TestRefiner.test_compound_commands_produce_no_row` still exercises it) rather than removed. Public `cli.py` entry is `refine_all`. The plan explicitly allowed either.
- `family.py` and `pricing.py` needed no signature changes: `family_of` already operates on a plain string; `estimate_price` already takes `(provider, model, tokens_in, tokens_out, env)` and degrades when the catalog is absent.

**Total deviations:** 2
**Impact on plan:** None. Public behavior matches the spec.

## Issues Encountered

Pyright `reportOptionalMemberAccess` on the `payload if isinstance(...) else {}` ternary (the empty-dict fallback did not narrow). Fixed by assigning after an explicit `isinstance` check. Codex delta subtraction needed `prev_out is None` in the same guard as `prev_in` so the `-` operator was not applied to `None`.

## User Setup Required

None. Real `run` against live session data is user-initiated later — every automated read used scratch env overrides / in-memory envelopes built from `capture_*.py` helpers.

## Next Phase Readiness

Ready for 05-05 (dashboard aggregation over the now-complete `refined_commands` set). REQ-usage-metrics-refinement-pipeline is fully satisfied. Classification mining of `control_flow_script`/`unclassified` remains 05-06.

## Verification (captured)

```
$ python3 -m unittest tests.test_ai_kit_usage_metrics -v
Ran 78 tests in 0.012s
OK

$ python3 -c "import pathlib; print(pathlib.Path('skills/ai-kit-usage-metrics/ai_kit_usage_metrics/decomposer.py').read_text().count('compound_decomposed'))"
0
$ python3 -c "import pathlib; print(pathlib.Path('skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refiner.py').read_text().count('compound_decomposed'))"
0
$ python3 -c "import pathlib,re; t=pathlib.Path('skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cwd_state.py').read_text(); print(len(re.findall(r'os\\.path\\.(exists|isdir)|os\\.stat', t)))"
0

$ make lint
shellcheck tools/install.sh tests/test_install.sh
python3 -m py_compile tools/setup.py tools/status-line.py tools/statusline-doctor.py tools/hooks/*.py tools/config_doctor_*.py skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py skills/ai-kit-usage-metrics/ai_kit_usage_metrics/*.py
```

## Self-Check: PASSED

- [x] `cd src && grep -r TODO .` refines into two ordered rows sharing one `raw_ref`; grep `resolved_cwd` is the path from the preceding `cd`
- [x] A later separate `grep -r FIXME .` in the same session reuses the carried cwd (opencode/Codex/Cursor state machine)
- [x] `for f in *.py; do rg pattern "$f"; done` is exactly one `control_flow_script` row
- [x] `||` / heredoc / subshell / unterminated quote are `unclassified`, distinct from `control_flow_script`
- [x] No `compound_decomposed` literal in decomposer.py or refiner.py
- [x] Opencode `workdir` rebases `CwdState.current` so a subsequent record without `workdir` resolves against the rebased value
- [x] Two steps of one compound Claude command share the same `turn_id` and the same token/price figures
- [x] Codex token attribution uses the incremental delta, never the raw cumulative total
- [x] Cursor rows have `tokens_input=None`, `tokens_output=None`, `price=None`, `source_confidence="low"`
- [x] rtk `history` populates `rtk_*` columns with `tokens_input`/`tokens_output` both None; `tee`/`parse_failure` produce no row
- [x] Opencode walk orders by `time_created`, proven by a fixture whose `record_id` TEXT order disagrees with time
- [x] Malformed Codex `arguments` does not abort `refine_all`; other records in the same batch still refine
- [x] `CwdState` performs no filesystem access
- [x] 78 tests, 0 failures; make lint py_compile clean
- [x] Production commits exist (`e579f06`, `a3afc22`, `9b5c4ac`)

---
*Phase: 05-usage-metrics-dashboard*
*Completed: 2026-09-10*
