# Phase 31: Removals and small defects - Discussion Log (standard discuss mode (`--analyze --all --batch`))

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-03
**Phase:** 31-removals-and-small-defects
**Mode:** interactive path — standard discuss mode (`--analyze --all --batch`) with the owner answering through the
coordinator; decision ladder available but not asked for; best design over the smallest diff (`mvp-mode` inactive)
**Areas analyzed:** judge bar, stale-provider code placement, rtk exemption shape, todo folding; own reasoning on
pruning entry points, path resolution, test placement, helpers and commit grouping

## Assumptions Presented

No analyzer ran: on the interactive path it runs only when the owner asks, and no `USER-PROFILE.md` exists, so no
advisor was spawned. The orchestrator scouted the code itself and listed its technical choices for the owner to
object to; the owner let them stand.

| Assumption | Confidence | Evidence |
|---|---|---|
| No shared function besides `prior_value` and the guidance prepend is left without a kept caller | Confident | `dispatch_guidance`'s four builders feed `build_dispatch_reinforcement_guidance`, used by `execute_dispatch`; `gsd_tools.config_path`, `config_set`, `gsd_core_version`, `resolve_gsd_tools` have kept callers in curated-config and `_shared` |
| Headless installs never prune today | Confident | `tmp/p31/stale_prune.sh`: dead links in four roots survive `install --headless`; `prune_stale` has no caller |
| The edge-floor guard needs the e2e tier | Likely | `edge_floor.py` exits 2 without node or the gsd-core engine |
| rules-agents' change does not touch its flow | Confident | only the R05 entry in `rules.py`, the "20-rule" count and one signals example in SKILL.md |

## jev screening

No ladder call: the interactive path screens only items the owner asks it to screen, and none were asked.

| Item | laya | typesafe | Outcome |
|---|---|---|---|
| Judge bar for skills already failing | – | – | Owner choice (recommended): D-01 |
| `check-providers` subcommand | – | – | Owner choice (recommended): D-02 |
| rtk exemption shape | – | – | Owner choice (recommended): D-06 |
| Todo folding | – | – | Owner choice (recommended): Folded Todos |
| JSONC reader placement and drift test | – | – | **Own reasoning:** copy plus drift test, the 29 D-13 pattern (D-03, not ledgered) |
| Headless prune entry points | – | – | **Own reasoning:** install and reconfigure (D-04, not ledgered) |
| Resolved-path helper and kit dir | – | – | **Own reasoning:** follows the owner's round 2 answer (D-05, not ledgered) |
| rtk test mechanics | – | – | **Own reasoning:** `git ls-files`, named skip outside a work tree (D-07, not ledgered) |
| Edge-floor guard tier | – | – | **Own reasoning:** e2e, named skip (D-08, not ledgered) |
| `@file:` helper, link test, commits, retargeted tests | – | – | **Own reasoning:** D-09, D-10, D-12, D-13 (not ledgered) |

## Batch 1 (owner answers, relayed by the coordinator)

1. Judge bar — recommended: judge the execute router, spec-config and curated-config here; rules-agents' edit is
   non-material and it carries its failing verdict to Phase 45.
2. Stale-provider code — recommended: a new `check-providers` subcommand called from spec-config's detection step.
3. rtk exemption — recommended: the whole usage-metrics folder and its test, plus a SKILL.md wording check.
4. Todos — recommended: fold the seven DEF-01 items; close SJ-1; leave the rest open.

## Live facts that changed the plan

- Two of the four changed skills already fail the judge bar (rules-agents SJ-3, spec-config unresolved), which made
  the judge scope a real question (D-01).
- SJ-1 disappears with `ai-kit-spec-execute-gsd` (folded todo).
- Phase 35's criteria 3 and 4 overlap the stale-provider check and the opencode listing flags (coupling, D-02).

## Corrections Made

None in this round; the SPEC round's corrections (RMV-04, DEF-01 and the ROADMAP anchors) are in the spec commit.

## External Research

None new in this round; the pi and opencode sources are cited in the SPEC Background.

## Ledger

Empty: no item was decided provisionally with low confidence.
