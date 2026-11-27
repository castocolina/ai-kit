# Phase 41: Superpowers adapter refactor with spec-config handoff - Discussion Log (standard discuss mode (`--analyze --all --batch`))

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-23
**Phase:** 41-superpowers-adapter-refactor-with-spec-config-handoff
**Mode:** interactive path: standard discuss mode (`--analyze --all --batch`) with the owner, jev not asked (screens only items the
owner asks it to screen), best design over smallest diff (mvp-mode inactive), code index in the scout
**Areas analyzed:** single-definition homes, flag-gated escalation, the fallback flag and jev pick, guidance builders, the lane
guard and audit, the executor switch and its dependency, the research handoff

## Assumptions Presented

The analyzer (`gsd-assumptions-analyzer`) was not spawned: on the interactive path it runs only when the owner asks. The
orchestrator scouted inline in the SPEC step (adapter layout, resume and stop text, `dispatch_guidance.py`, the runner's finding
codes, `gsd-executor.md`, the real-home guard sites) and added no new read here.

| Assumption | Confidence | Evidence |
|---|---|---|
| `state-management.md` and `resolution-stops.md` match the two topics | Likely | file sizes and headings seen in the SPEC step; not read in full |
| A native subagent cannot receive the guard variable | Likely | it runs in the session's own process; not tested |
| Phase 40's switch module can be imported by the adapter | Likely | both live under `ai_kit_spec`; Phase 40 is planned, not built |
| The runner already covers some of EXE-05 part 2 | Unclear | finding codes exist (`cross-ai.mjs:1629`); behavior not read |

## jev screening

Not asked (interactive path: the owner answers). Every decision below is owner-answered in the SPEC step or own reasoning,
ledgered.

| Item | jev | Outcome |
|---|---|---|
| Single-definition homes | none | **Own reasoning:** existing topic files (D-01, ledger) |
| Escalation flags gate rounds 4 and 5 | none | Owner: yes, along an enabled flag (D-02) |
| Fallback flag and jev pick | none | **Own reasoning:** lane-table boolean, jev classes haiku and sonnet (D-03, ledger) |
| Guidance builders | none | **Own reasoning:** caller-fed, no framework wording (D-04, ledger) |
| Guard on native lanes | none | **Own reasoning:** subprocess lanes only, native reported not applicable (D-05, ledger) |
| Audit design | none | **Own reasoning:** fixed seed list, observation label (D-06, ledger) |
| Executor switch dependency | none | **Own reasoning:** reuse Phase 40's module, ROADMAP amended (D-07, ledger) |

## Live facts that changed the plan
- Cross-phase: Phase 41 reuses Phase 40's switch module, so the ROADMAP "Depends on" of Phase 41 gained Phase 40 (dated
  amendment in the same commit).

## Corrections Made
- The SPEC step corrected the owner's "two briefs" premise (recorded in 41-SPEC.md Background).

## External Research
- None; the five open questions of the SPEC go to the researcher before planning (D-09).
