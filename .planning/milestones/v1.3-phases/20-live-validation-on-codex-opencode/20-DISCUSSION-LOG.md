# Phase 20: Live Validation on Codex + Opencode - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-23
**Phase:** 20-live-validation-on-codex-opencode
**Mode:** --analyze. The discussion was held in Spanish; this log is in English per the project
constraint.
**Areas discussed:** Driving the hosts, Nesting and codex, opencode local vs global, Fix policy

**Findings presented before the questions:**
1. gsd-core bakes opencode agent models at install time, and only a project-local install reads
   the project's `.planning/config.json`.
2. Under 16 D-01's order, a codex launched from Claude would read as claude, because
   `CLAUDECODE` is inherited.

---

## Driving the hosts
- headless iteration, then a final interactive run as the evidence ✓
- interactive only
- headless only

## Nesting and codex
- claude last: pi > opencode > cursor > codex > claude (amends 16 D-01); headless runs also
  clean the env ✓
- keep the order and clean the env
- process-tree detection

## opencode local vs global
- local install as the follow-up; the global alternative is explained, not run ✓
- local only
- global defaults plus a global reinstall

## Fix policy
- a threshold: small local fixes happen in 20; decision or multi-module changes become 20.x ✓
- everything in 20
- everything in 20.x

## Propagated amendments
- 16-CONTEXT D-01, 17-CONTEXT, REQUIREMENTS SPEC-01, the ROADMAP Phase 16 success criteria and
  PROJECT.md now use the new order.
- 18-CONTEXT D-05 gets the opencode local-install note.
- A spec §11 Errata section was added, collecting every discussion-time deviation from the
  approved spec.

## Deferred Ideas
- Process-tree host detection.

# Update 2026-10-14 (assumptions mode)

**Input:** `20-SPEC.md` (committed in `b7fc32c`) and the 2026-09-23 CONTEXT (D-01..D-06 kept).
**Mode:** assumptions (`--analyze --all --batch`), jev screening, best over easy, CodeGraph.

## Assumptions Presented

The analyzer was `gsd-assumptions-analyzer` (sonnet), with 102 tool calls. It ran scratch
experiments against the real gsd-core 1.16.0 modules under a temp HOME and ran no installer
or model.

| Assumption | Confidence | Evidence |
|---|---|---|
| Planned == baked is its own check | Confident | `install-model-override-resolver.cjs:172-197`; scratch bake experiment |
| `runtime` must be a project managed key | Likely | `17-SPEC.md` R5; `bin/install.js:4139-4181` |
| Scratch installs need an isolated HOME | Likely | `bin/install.js:6972-7014,12234,14360-14375` |
| Global-config guard is semantic, not a checksum | Confident | codex TUI trust writes; opencode lockfile refresh |
| `CODEX_VERSION` absent, `CODEX_THREAD_ID` present | Likely | binary strings; 20 session snapshots |
| No code-level opencode self-skip | Likely | `workflows/review.md:126-149`; `review-reviewer-selection.cjs:214-300` |
| Prefix-specific gitignore | Likely | absolute paths in baked TOMLs; opencode's own `.gitignore` |

## jev screening

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| A1 runtime key | amend_both 0.90 | – | D-08, 17 D-23 |
| A2 HOME isolation | isolated_home 0.44 (fb) | isolated_home 0.96 | D-09 |
| A3 host lane | instance_after_proof 0.41 (fb) | never_host_lane 0.98 | D-11 |
| A4 gitignore | prefix_ignore 0.50 (fb) | prefix_ignore 0.86 | D-12 |

## Live facts that changed the plan

- The installer ignores `GSD_RUNTIME` and bakes from the project or global `runtime`. This
  amends 17-SPEC R5 and adds 17 D-23.
- A `--local` non-Claude install writes `~/.gsd/defaults.json`. This amends 18 D-37.
- `CODEX_VERSION` is not in the codex binary. This annotates 16 D-02 and REQUIREMENTS SPEC-01.
