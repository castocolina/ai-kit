# Phase 40: Resilient review sized by jev - Discussion Log (standard discuss mode (`--analyze --all --batch`))

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-23
**Phase:** 40-resilient-review-sized-by-jev
**Mode:** interactive path: standard discuss mode (`--analyze --all --batch`) with the owner, jev not asked (screens only items the
owner asks it to screen), best design over smallest diff (mvp-mode inactive), code index in the scout
**Areas analyzed:** reason list, ping and cadence, partial report, flagged switch, blocked-until read, jev adapters, deterministic
signals, fold-step check, docs and order

## Assumptions Presented

The analyzer (`gsd-assumptions-analyzer`) was not spawned: on the interactive path it runs only when the owner asks. The
orchestrator scouted inline: the spec-review SKILL.md hard rules and probe walk, `quota.py`, `lane_settings.py`,
`error_classifier.py`, `jev_names.py`, the runner's blocked-until record and flags, the fixer's severity rule.

| Assumption | Confidence | Evidence |
|---|---|---|
| A closed reason list already exists in Python | Confident | `error_classifier.py:16` `REASONS`, read by the probe and tests |
| The blocked-until record has one validated reader | Confident | `--blocked-status` in `skills/ai-kit-cross-ai/SKILL.md:69`; parser in `cross-ai.mjs:4081` |
| A flagged lane must be dispatched with `--pool` | Confident | `subprocess-quota-policy.md:185` |
| `probe_reviewer_quota` can serve as the ping | Likely | `quota.py:271`; its seams and timeout were not run |
| jev adapters for sizing and classification are new | Confident | `jev_names.py`, `skill_classify.py`, `lane_order.py` hold other jev uses only |

## jev screening

Not asked (interactive path: the owner answers). Every decision below is owner-answered in the SPEC step or own reasoning,
ledgered.

| Item | jev | Outcome |
|---|---|---|
| Reason list home | none | **Own reasoning:** extend `REASONS` (D-01, ledger) |
| Ping implementation and staleness | none | **Own reasoning:** concurrent `probe_reviewer_quota`, cache TTL (D-02, ledger) |
| Partial status | none | **Own reasoning:** Step 5 report wording (D-03, ledger) |
| Flagged-lane switch module and `--pool` | none | **Own reasoning:** small module beside `routing.py` (D-04, ledger) |
| Blocked-until reader | none | **Own reasoning:** the runner's `--blocked-status`, PROVISIONAL (D-05, ledger) |
| jev adapters | none | **Own reasoning:** one module on `ask_items`, no-jev sentinel (D-06, ledger) |
| Fold-step check home | none | **Own reasoning:** deterministic script, not a checklist item (D-08, ledger) |

## Live facts that changed the plan
- **Amended the SPEC:** requirement 3 said no closed reason list existed in spec-review; `error_classifier.py:16` has one, so
  the requirement now extends it (dated amendment in the SPEC; the R3 encoding edge row, a dismissal, dropped out of the floor
  and was removed from the table).
- The blocked-until record is written by the runner and has a single reader (`--blocked-status`); a Python reader would be a
  second parser.

## Corrections Made
- The SPEC's R3 "Current" statement (above).

## External Research
- None.
