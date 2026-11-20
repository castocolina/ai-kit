# Phase 35: Model discovery and catalog - Discussion Log (standard discuss mode (`--analyze --all --batch`) for the interactive path)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-16
**Phase:** 35-model-discovery-and-catalog
**Mode:** interactive path: the owner answered the four unclear questions (relayed by the orchestrator); every other gray
area was screened with jev and decided by the decision table; no gsd-assumptions-analyzer run (the owner did not ask for
it; the scouting was done live in the phase subagent), best design over smallest diff
**Areas analyzed:** layout, sources and cache, Arena path, name identity, tiers, class, cost, context per runtime,
usability, optional sources, stale, `[models]` and schema, recorded help, router aliases, hardcoding guard, todo folding

## Assumptions Presented

No analyzer ran. The scouting covered the six hosts' listing commands and versions, opencode's `/api/model` shape, the
models.dev and Arena shapes, and the existing catalog code, all live on 2026-11-16 (SPEC Background).

| Assumption | Confidence | Evidence |
|---|---|---|
| The catalog can reuse the existing merge, matcher and cache code behind new small modules | Confident | `catalog_build.py` 731 lines, `model_matcher.py` has effort stripping, `model_catalog.py` has `merge_catalog_entry` |
| Arena is reachable with the standard library | Confident | JSON rows API answered, 100-row cap, 112 pages for `text` |
| Copilot's list can come from its interactive view through herdr | Unclear | `/model` output not read; spike first |
| Class thresholds can be written now | Unclear | needs the live catalog; researcher question |

## jev screening

Two requests for the spec items and one for the discuss items, plus one second opinion. Summaries only.

| Item | jev | Outcome |
|---|---|---|
| layout | new_modules, choice 0.99 | D-01 |
| guard detector | positions, choice 0.84; laya low name_list 0.51 | D-16 |
| tier input | laya average 0.86 contradicted the evidence; second opinion primary_then_fill, choice 0.85 | **jev overridden**: D-05 |
| usability record | command_records, choice 0.90 | D-10 |
| web query | fixed_template, choice 0.98 | D-11 |
| probe scope | chosen, choice 0.94 | D-10, SPEC R2 |
| tier bands | relative, choice 0.93 | D-05 |
| stale rule | laya low age 0.49, typesafe low success_only 0.54 | **Own reasoning:** D-12 (ledger) |
| context label | per_runtime, choice 1.00 | D-09 |
| Arena path | json_api, choice 0.96 | D-03 |
| help fixture | recorded, choice 0.88 | D-14 |
| schema bump | bump, choice 0.85 | D-13 |
| cost bands | banded, choice 0.88 | D-07 |
| context override | models_table, choice 0.97 | D-09, D-13 |
| names for bare-id hosts | laya low marker 0.55, typesafe low placeholders 0.57 | **Own reasoning:** D-17, needs confirmation (ledger) |
| cache age defaults | none | **Own reasoning:** D-02 (ledger) |
| class thresholds | none | **Own reasoning:** D-06, researcher question (ledger) |
| herdr order | none | **Own reasoning:** D-11, spike first (ledger) |

## Live facts that changed the plan

- copilot 1.0.112 has no non-interactive listing, so R3 (seed, web, herdr) exists.
- opencode 2.3.0 accepts `--standalone` on `models`; the runner comment saying otherwise is stale (R9).
- opencode's own `/api/model` carries `variants`, `limit` and `cost` for every model, so effort levels and window sizes
  come from the host (R6, R9).
- Arena's rows API caps at 100 rows per request and its `/filter` route failed once: the read is paged and cached (D-03).
- The 2026-11-16 wizard todo adds router aliases assumed, a confirm subcommand, and the `check-providers` "untrusted"
  defect (R5, R8, R10 text added to the SPEC).

## Corrections Made

- The 2026-11-14 wording "Arena is the alternative when Artificial Analysis is unavailable" is replaced by "merged
  whenever enabled" (owner-confirmed 2026-11-16; amended in HUB-03 and the Phase 35 goal note).
- The first 2026-11-16 amendment said any runtime may serve review or execute "with no closed list"; the owner corrected it:
  ai-kit has two tables, they are seed data and examples only (RUN-01, Phase 37 criterion 4, commit 451a0a9).
- HUB-03 and Phase 35 criterion 5 now keep the context window per (runtime, model); Phase 39 criterion 4 and REV-04 read the runtime's value.
- New requirement HUB-09 (the hardcoding guard) is added to REQUIREMENTS.md and Phase 35.

## External Research

- Arena dataset license cc-by-4.0 (Hugging Face API, 2026-11-16); Artificial Analysis free API requires attribution
  (its terms of use not read); models.dev repository license MIT, no attribution request found.
