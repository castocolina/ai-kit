---
phase: 05-usage-metrics-dashboard
plan: 05
subsystem: usage-metrics
tags: [usage-metrics, dashboard, skill-md, phase-close]

requires:
  - "05-01 refined_commands schema, atomic-write/escape mechanism, open_refined_db_readonly"
  - "05-04 turn_id/step_count/operator/execution_certain/source_confidence/rtk_* columns"
  - "05-06 inferred_family/inferred_confidence columns and classify-loop documentation"
provides:
  - "dashboard.py::generate: full 5-axis filter+sort UI, session grouping, pure JS functions"
  - "skills/ai-kit-usage-metrics/SKILL.md: final, skill-judge-passed pipeline documentation"
affects: [05-usage-metrics-dashboard]

actuals:
  tokens: 130000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Inline <script> factored into pure top-level functions (filterRows/sortRows/groupBySession/displayFamily) with zero DOM dependency, called by a separate DOM-wiring block"
    - "groupBySession dedups on (session_id, turn_id) before summing tokens/price; invocation counts are a separate, undeduped reduction over the same filtered set"
    - "createElement + textContent/.value exclusively for all data-driven DOM writes -- never innerHTML"
    - "node-executed shipped-JS test: extract filterRows/sortRows/groupBySession source from the generated HTML and run it for real via subprocess.run([\"node\", ...]), conditional on shutil.which(\"node\")"

key-files:
  created:
    - .planning/phases/05-usage-metrics-dashboard/05-05-SUMMARY.md
  modified:
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/dashboard.py
    - skills/ai-kit-usage-metrics/SKILL.md
    - tests/test_ai_kit_usage_metrics.py
    - .planning/PROJECT.md
    - .planning/intel/requirements.md

key-decisions:
  - "This plan is the sole, final SKILL.md editor and sole skill-judge runner for Phase 5, running strictly after 05-06 (Wave 6) so the reviewed file genuinely reflects the whole phase's feature set."
  - "05-06's ready-to-publish 'Classification refinement loop' section was folded into SKILL.md verbatim from 05-06-SUMMARY.md, not re-derived."
  - "PROJECT.md and .planning/intel/requirements.md's stale pre-D-10 'dashboard Artifact'/'local export' wording corrected to match REQUIREMENTS.md's already-amended D-10 phrasing."
  - "make validate's remaining 25 ruff findings + 5 pylint C0301 are the documented pre-existing baseline confined to tools/status-line.py, tools/wizard_app.py, tests/test_ai_kit_spec.py, and tests/test_ai_kit_spec_superpowers.py -- none of this plan's files, unaffected by this plan's changes, and not treated as a new-work blocker for this plan's own close-out."
  - "<human-check> real-browser/DOM verification remains a documented, deliberate deferral (Round 1 review decision) -- no headless-browser dependency added this milestone."

patterns-established:
  - "A static-HTML dashboard's filter/sort/group logic ships as pure, DOM-free functions specifically so a test can execute the ACTUAL shipped JS via node, not merely a Python re-implementation of its logic."
  - "Confidence-visible rendering: an inferred or low-certainty value never shares an unlabeled cell with a mechanically-determined one -- it always carries an explicit textual marker (\"(inferred, ...)\", \"(conditional)\")."

requirements-completed:
  - REQ-usage-metrics-dashboard-ui

coverage:
  - id: REQ-usage-metrics-dashboard-ui
    description: "Full filter/sort UI across all 5 MVP axes, session grouping, canonical query answerable from embedded data alone, no live re-parse, no hosted-database capability"
    requirement: REQ-usage-metrics-dashboard-ui
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestDashboardFull"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestDashboardFull.test_shipped_js_canonical_query_via_node"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestSkillDocumentation"
        status: pass
    human_judgment: true
  - id: SKILL-QUALITY-GATE
    description: "SKILL.md passes skill-judge with 0 remaining Critical/Important findings"
    requirement: REQ-usage-metrics-dashboard-ui
    verification:
      - kind: review
        ref: "skill-judge run against skills/ai-kit-usage-metrics/SKILL.md"
        status: pass
    human_judgment: false
  - id: PHASE-CLOSE-GATE
    description: "make test and make lint exit 0 for the whole repository; make validate's remaining findings are the documented pre-existing baseline, unrelated to Phase 5"
    requirement: REQ-usage-metrics-dashboard-ui
    verification:
      - kind: integration
        ref: "make test && make lint"
        status: pass
      - kind: integration
        ref: "make validate (25 ruff + 5 pylint C0301, all pre-existing baseline in tools/status-line.py, tools/wizard_app.py, tests/test_ai_kit_spec.py, tests/test_ai_kit_spec_superpowers.py)"
        status: baseline-only
    human_judgment: true

completed: 2026-09-10
status: complete
---

# Phase 5 Plan 05: Full Dashboard UI, Session Grouping, and SKILL.md Finalization Summary

**The static dashboard now exposes filterable AND sortable controls across all 5 MVP axes, groups rows by session with correct `(session_id, turn_id)` dedup on token/price sums, and answers the PRD's own canonical "grep this month, grouped by session" query from embedded data alone via the ACTUAL shipped JS (executed for real via `node`). `SKILL.md` is finalized as the single, final assembler of the whole pipeline's documentation, folding in 05-06's classification-loop section, and passes `skill-judge` at 108/120 with 0 remaining Critical/Important findings. This closes Phase 5.**

## Execution Note (cross-AI dispatch)

This plan was dispatched to `opencode run --model router-env/my-coding`
(PID 1804635, wrapper `node gsd-tools.cjs run-with-timeout` PID 1804627),
per `.planning/ONESHOT-RULES.md` Rule 2's execution-delegation route.
Persistent audit logs: `.planning/phases/05-usage-metrics-dashboard/
.execution-diagnostics/05-05-candidate.log` and `05-05-err.log`.

The dispatched process implemented and committed Task 1 in full
(commit `3f333c5`) and implemented all of Task 2 (SKILL.md finalization,
D-10 doc corrections, `TestSkillDocumentation`, a first `skill-judge` pass
scoring 108/120 with 0 remaining Critical/Important findings, `make test`
+ `make lint` green), but the process exited (hit the dispatch wrapper's
3600s timeout) mid-way through triaging `make validate`'s remaining
findings against the documented pre-existing baseline, before printing
`EXECUTION COMPLETE` or committing Task 2's already-correct working-tree
changes. Per ONESHOT-RULES' failure-handling guidance ("late death
mid-final-verification with real commits landed -> do NOT re-dispatch,
complete directly yourself"), the orchestrating session verified Task 2's
uncommitted work was complete and correct, re-ran every verification
command for real, confirmed `make validate`'s remaining 25 ruff findings
+ 5 pylint C0301 are entirely confined to the four files named in this
plan's own known pre-existing baseline (none of this plan's own files),
and committed Task 2 directly (commit `625eba7`).

## Performance

- **Tasks:** 2
- **Files created:** 1 (this SUMMARY)
- **Files modified:** 5
- **Commits:** 2

## Accomplishments

- `dashboard.py::generate` now `SELECT`s the full `refined_commands`
  column set (including `inferred_family`/`inferred_confidence`/
  `source_confidence`/`execution_certain`/`turn_id`), unchanged
  escape/atomic-write mechanism from Wave 1.
- The inline `<script>` is factored into pure, DOM-free top-level
  functions -- `filterRows`, `sortRows`, `groupBySession`, `displayFamily`
  -- called by a separate DOM-wiring block. All 5 MVP axes (date, model,
  family, tokens, price) get both a filter control and a sortable column
  header; family also gets a literal `command_text` substring filter.
- `groupBySession` dedups on `(session_id, turn_id)` before summing
  `tokens_input`/`tokens_output`/`price`, so a compound `&&` command's
  step rows sharing one `turn_id` contribute their figures exactly once
  to a session total; invocation counts still count every matching row.
- `execution_certain=False` rows render a visible "(conditional)" marker;
  a row with empty `family` but set `inferred_family` renders
  `"{inferred_family} (inferred, {inferred_confidence})"`; Cursor's
  `source_confidence` renders in its own distinct badge -- all via
  `createElement`/`textContent` only (`grep -cE '\.innerHTML[[:space:]]*='`
  is 0).
- `test_shipped_js_canonical_query_via_node` extracts the actual shipped
  `filterRows`/`sortRows`/`groupBySession` source from the generated HTML
  and executes it for real via `node`, proving the ACTUAL shipped JS (not
  a Python reimplementation) answers the PRD's canonical query and
  correctly dedups the shared-`turn_id` fixture.
- An AST-based scan of `dashboard.py`'s own imports confirms zero
  occurrences of `urllib`, `http`, `requests`, or `socket`.
- `SKILL.md` is rewritten as the finished, single documentation of the
  whole pipeline: full refined-schema field list, the
  `control_flow_script`-vs-`unclassified` `command_shape` distinction,
  Cursor's low-confidence caveat, the manual-only/no-cron D-07 non-goal,
  and 05-06's "Classification refinement loop" section folded in verbatim.
  Passed `skill-judge` at 108/120, 0 remaining Critical/Important
  findings.
- `PROJECT.md`'s Rejected Alternatives bullet and `.planning/intel/
  requirements.md`'s `REQ-usage-metrics-dashboard-ui` entry are reworded
  to match `REQUIREMENTS.md`'s already-amended D-10 phrasing (no
  export/import step, no browser-sandboxed Artifact mechanism).

## Task Commits

1. **Task 1: Full filter/sort dashboard UI + session grouping** — `3f333c5` (feat)
2. **Task 2: Finalize SKILL.md, D-10 corrections, skill-judge, close-out gate** — `625eba7` (docs)
3. **This SUMMARY** — (docs, committed separately below)

## Files Created/Modified

- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/dashboard.py` — full
  5-axis filter/sort/group UI, pure JS functions, confidence-visible
  rendering, `createElement`/`textContent`-only DOM writes
- `skills/ai-kit-usage-metrics/SKILL.md` — finalized, `skill-judge`-passed
  documentation of the whole pipeline
- `tests/test_ai_kit_usage_metrics.py` — `TestDashboardFull` (8 tests
  including the `node`-executed shipped-JS test) and
  `TestSkillDocumentation`
- `.planning/PROJECT.md` — D-10 wording correction (Rejected Alternatives)
- `.planning/intel/requirements.md` — D-10 wording correction
  (`REQ-usage-metrics-dashboard-ui`)

## Decisions Made

- Followed the plan's Round 1/2/3 review dispositions exactly: wave
  reorder (this plan runs after 05-06, sole `SKILL.md`/`skill-judge`
  owner), `(session_id, turn_id)` dedup before summing, visible
  `execution_certain=False` marker, `createElement`/`textContent`-only
  DOM writes, AST-based import scan, D-10 doc corrections.
- Treated `make validate`'s remaining findings as the documented
  pre-existing baseline (they are confined to the exact four files named
  in the dispatch instructions' known-baseline list and are unmodified by
  this plan) rather than a new blocker, consistent with the orchestrating
  instructions for this dispatch.

## Deviations from Plan

- The cross-AI dispatch process died mid-final-verification (3600s
  wrapper timeout) after completing all substantive work for both tasks
  but before committing Task 2 or printing `EXECUTION COMPLETE`. The
  orchestrating session completed the close-out directly rather than
  re-dispatching, per ONESHOT-RULES' own failure-handling guidance for a
  "late death... with real commits landed" case. No plan requirements
  were skipped or weakened; every `<verify>`/`<acceptance_criteria>` item
  was independently re-checked with real command output before this
  SUMMARY was written.

**Total deviations:** 1 (dispatch-process timeout, handled per
ONESHOT-RULES; no scope or quality impact)
**Impact on plan:** None on delivered scope or verification rigor.

## Issues Encountered

`make validate` (pre-commit `ruff` + `pylint`) reports 25 ruff findings
and 5 pylint `C0301` (line-too-long) findings, all in
`tools/status-line.py`, `tools/wizard_app.py`, `tests/test_ai_kit_spec.py`,
and `tests/test_ai_kit_spec_superpowers.py` — exactly the pre-existing
baseline this dispatch's own instructions named in advance. None of these
files were touched by this plan. `make test` and `make lint` both exit 0
cleanly for the whole repository.

## User Setup Required

None beyond the plan's own deliberately-deferred `<human-check>`: for uz,
at uz's own discretion and later, run
`python3 skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py run` against
real `~/.claude`/`~/.local/share/opencode`/`~/.local/share/rtk`/`~/.codex`/
`~/.cursor` data, open the generated `dashboard.html`, and confirm it
answers a real query, including trying the family/model/command-text/
date/tokens/price filters and the group-by-session toggle by hand. This
is never run automatically by this phase's own execution (ONESHOT-RULES
Rule 5).

## Next Phase Readiness

Phase 5 (Usage Metrics Dashboard) is complete: all 4 requirements
(`REQ-usage-metrics-raw-capture`, `REQ-usage-metrics-refinement-pipeline`,
`REQ-usage-metrics-dashboard-ui`, `REQ-usage-metrics-classification-
refinement-loop`) are delivered and verified. The whole-repository
`make test`/`make lint` gate is green; `make validate`'s remaining
findings are the documented pre-existing baseline, unrelated to this
phase.

## Verification (captured)

```
$ python3 -m unittest tests.test_ai_kit_usage_metrics -v
Ran 102 tests in 0.072s

OK

$ make test
[... full suite, including tests/test_install.sh ...]
16 passed, 0 failed

$ make lint
shellcheck tools/install.sh tests/test_install.sh
python3 -m py_compile tools/setup.py tools/status-line.py tools/statusline-doctor.py tools/hooks/*.py tools/config_doctor_*.py skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py skills/ai-kit-usage-metrics/ai_kit_usage_metrics/*.py
(clean, no output)

$ make validate
... 25 ruff findings + 5 pylint C0301, all in tools/status-line.py,
tools/wizard_app.py, tests/test_ai_kit_spec.py,
tests/test_ai_kit_spec_superpowers.py -- the documented pre-existing
baseline, none of this plan's files.
pylint rated 9.98/10 (previous run: 9.98/10, +0.00)
pyright..................................................................Passed
vulture..................................................................Passed
shellcheck...............................................................Passed
py-compile...............................................................Passed
unittest (core)..........................................................Passed
unittest (wizard — uv)...................................................Passed

skill-judge (skills/ai-kit-usage-metrics/SKILL.md): 108/120, 0 remaining
Critical/Important findings.

$ grep -cE '\.innerHTML[[:space:]]*=' skills/ai-kit-usage-metrics/ai_kit_usage_metrics/dashboard.py
0
```

## Self-Check: PASSED

- [x] All 5 MVP axes have BOTH a filter control AND a sortable header
- [x] `filterRows`/`sortRows`/`groupBySession` executed for real via
      `node` and match the PRD canonical query
- [x] `groupBySession` dedups `(session_id, turn_id)` before summing
      tokens/price; invocation counts still count every matching row
- [x] `execution_certain=False` rows render a visible "(conditional)"
      marker
- [x] Inferred-family and Cursor `source_confidence` render visibly
      distinct from mechanical values
- [x] Zero `innerHTML` assignments; `createElement`/`textContent` only
- [x] AST-based import scan: zero `urllib`/`http`/`requests`/`socket`
- [x] `dashboard.generate` works against `open_refined_db_readonly` and
      ignores missing `raw/*.jsonl`
- [x] `SKILL.md` documents the real schema (test-verified), the
      `command_shape` limitation, and 05-06's classify-loop section
- [x] `skill-judge`: 0 remaining Critical/Important findings
- [x] `PROJECT.md` / `.planning/intel/requirements.md` D-10 wording
      corrected
- [x] 102 tests, 0 failures
- [x] `make test` and `make lint` exit 0; `make validate` findings are
      the documented pre-existing baseline only
- [x] Production commits exist (`3f333c5`, `625eba7`)
- [x] `<human-check>` real-browser/DOM item explicitly deferred, not
      silently dropped

---
*Phase: 05-usage-metrics-dashboard*
*Completed: 2026-09-10*
