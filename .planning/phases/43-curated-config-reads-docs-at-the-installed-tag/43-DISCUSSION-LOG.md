# Phase 43: curated-config reads docs at the installed tag - Discussion Log (standard discuss mode (`--analyze --all --batch`))

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-23
**Phase:** 43-curated-config-reads-docs-at-the-installed-tag
**Mode:** interactive path: standard discuss mode (`--analyze --all --batch`) with the owner, jev not asked (screens only items the
owner asks it to screen), best design over smallest diff (mvp-mode inactive), code index in the scout
**Areas analyzed:** fetch mechanism, docs set, cache, update offer, impact labeling, cascade mapping, base branch, v1 records

## Assumptions Presented

The analyzer (`gsd-assumptions-analyzer`) was not spawned: on the interactive path it runs only when the owner asks. The
orchestrator scouted inline: the installed gsd-core folder, the package metadata and the upstream tag (read-only network
queries), curated-config's SKILL.md flow and v1 path, `git-base-branch.cjs`.

| Assumption | Confidence | Evidence |
|---|---|---|
| Upstream is `open-gsd/gsd-core` with tag `v<version>` | Confident | `pnpm view` and `gh api` on 2026-11-23: tag `v1.22.0` exists with `docs/` and `CHANGELOG.md` |
| The installed copy has no tagged docs | Confident | folder listing: no `docs/`, no changelog |
| `urllib` suffices for the fetch | Likely | stdlib; not run against GitHub raw in this scout |
| GSD's resolver gives the merge-flow base branch | Unclear | it gives the default branch; merge flow equality is the owner's confirmation |

## jev screening

Not asked (interactive path: the owner answers). Every decision below is owner-answered in the SPEC step or own reasoning,
ledgered.

| Item | jev | Outcome |
|---|---|---|
| Cascade replaces the four questions | none | Owner: replace (SPEC step) |
| Update offer rule | none | Owner: jev labels, rules decide (SPEC step) |
| `rigorous` and cross-AI plan review after the cascade | none | Owner: reachable as plan edits (D-07) |
| Fetch mechanism and repository slug | none | **Own reasoning:** stdlib `urllib`, seed data labeled (D-01, ledger) |
| Docs page set and fallback | none | **Own reasoning:** changelog plus config docs, installed copy as labeled fallback (D-02, ledger) |
| Cache layout | none | **Own reasoning:** `.aikit/gsd-docs/<version>/` (D-03, ledger) |
| Labeler rules | none | **Own reasoning:** keyword default under jev (D-05, ledger) |
| Base branch source | none | **Own reasoning:** GSD's resolver, owner confirms (D-08, ledger) |
| v1 run record method | none | **Own reasoning:** script in a scratch project (D-09, ledger) |

## Live facts that changed the plan
- The owner's "replace the four" answer would have removed the `rigorous` level and the cross-AI plan review choice; the owner
  chose to keep both reachable as plan edits (recorded in the SPEC Background and D-07).

## Corrections Made
- None to earlier artifacts.

## External Research
- Read-only upstream checks on 2026-11-23: package metadata (`pnpm view`), tag listing and root contents (`gh api`).
