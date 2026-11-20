---
phase: 35-model-discovery-and-catalog
plan: 20
subsystem: catalog
tags: [report, stale, usability, listing-state]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-03 catalog_labels.show, 35-11 optional candidates, 35-12 usability record, 35-14 match fact, 35-15 snapshot listing keys"
provides:
  - "catalog_report.py: ReportRow, REPORT_FACTS, facts_text, listing_state, listed_from_text, stale_state, stale_providers, marked_state, usability_state, context_line, report_rows, render_lines"
  - "tests/test_catalog_stale.py: 15 tests (TestStaleOnProof 3, TestReportStates 12)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_report.py
  modified:
    - tests/test_catalog_stale.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (617 s, status=ok exit=0, attempts=1, cycles=0)"
---

# Phase 35 Plan 20: catalog report rows

One commit, `a1b9e7d feat(35-20): report catalog listing and stale states` (pre-fold); the commit hook ran 98/98 modules green. The executor's first
`make ruff` found one over-long test line, which it fixed before committing.

## Accomplishments

- `report_rows(catalog, snapshot, optional=None, fresh=False)` gives one row per (runtime, model), sorted by runtime then id, plus rows for
  optional candidates absent from the catalog (`not listed`, `unmatched`), listed ids the build left unmatched (`unmatched`) and one host row
  (`-`) for an installed runtime with no row at all.
- Stale only on proof: `listing == "ok"` with a `models` list. With `fresh=True` an absent id is `stale (not in the listing of <at>; last seen
  <last_seen or never>)`; from a saved snapshot it is `not checked (cached <at>)`; a failed, skipped or absent listing is `not checked`, even
  when an old `models` list is retained. `stale-provider (no listed model from <prefix>)` needs a fresh successful listing; `router-env` is
  never a provider prefix.
- Usability reads `verified <at> via <via>`, `rejected <at>: <error>`, `unverified`, and `listed disabled by host` first when the host's own
  record says `enabled` False. `marked_state` shows `marked by source: <status> (models.dev)` apart from stale; the context line and the
  facts text go through `catalog_labels.show`.

## Deviations and notes for the code review

- No deviation from the plan's behavior; no file outside `files_modified` was touched.
- Small defects left for the review: `listing_state` ends with two branches that both return `not checked` (the `listing is None and "listing"
  not in cli_row` branch is redundant); `_listed_rows` calls `cli_row.get("listing")` without the dict check its `models` line has (a snapshot
  whose `clis.<id>` is not a dict would raise); `_extra_row` builds a throwaway `{"listed_from": {}}` dict for the optional case, which reads
  better as two functions.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_stale tests.test_ai_kit_spec_check_providers tests.test_arch_hardcoded_models tests.test_skill_text_history tests.test_arch tests.test_gate_scope`:
  exit 0, 6/6 modules (15, 29, 14, 45, 109 and 62 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: all rc 0.
- I read `catalog_report.py` whole against the plan text.
- Real-config audit (`audit_c2.py` against the wave 7 marker): two pi session logs; the Claude host's own `history.jsonl` and `jobs/*` (this
  agent's session); nothing from the lane.

## Self-Check: PASSED
