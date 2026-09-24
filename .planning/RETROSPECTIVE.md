# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.2 — ai-kit Rules Skill Family

**Shipped:** 2026-09-23
**Phases:** 9 (9–15, plus inserted 15.1 and 15.2) | **Plans:** 28 | **Sessions:** not tracked

### What Was Built
- Six single-domain project-rules checkers on a shared `ai_kit_rules_common`: agents (pruned), makefile, precommit, arch, docker and cicd.
- The `ai-kit-project-rules-all` orchestrator, with a criticality-merged report, dogfooded live against this repo.
- A usage-metrics dashboard overhaul (15.1): virtualized Material UI, and five live-found data-correctness bugs fixed against the real ~85k-row store.
- A pre-close debt cleanup (15.2): pyright back to 0 errors, symmetric sort-key fallback plus regression tests, and todo bookkeeping.

### What Worked
- The strict dependency chain (9 → 15) with the shared package extracted first. The integration check found no divergent copies across 6 checkers.
- Each checker ends in a SKILL.md plan gated by `/skill-judge` and `/naming-analyzer`. Scores ranged 97–103/120 with 0 Critical/Important findings.
- Testing against real data in 15.1 surfaced bugs that fixtures never showed: NULL dates, codex's new tool-call shape, and session dedup.
- An audit, then a cleanup phase, then the close. The audit converted "deferred" notes into a short, verifiable fix list.

### What Was Inefficient
- **Verification staleness:** most phase VERIFICATIONs went `stale` just because later phases touched covered files, which forced an override closeout.
- **Unclosed milestones:** v1.0 and v1.1 were never formally closed. The ROADMAP had grown into free-form "addenda", which `milestone.complete` could not scope, so the archive was done by hand.
- **Repeated deferrals:** the same pre-existing lint debt (`status-line.py`, `wizard_app.py`) was re-deferred by at least 5 plans across 3 milestones.
- **Incomplete fingerprint:** the 15.2 verifier could not compute `covered_digest` itself. It wrote an "unavailable" placeholder, and the phase read stale until the digest was filled in by hand.

### Patterns Established
- Close each milestone with `/gsd-complete-milestone` before starting the next one. Don't append "vX.Y addendum" prose to a live ROADMAP.
- An inserted pre-close cleanup phase (N.2) for in-milestone debt found by the audit.
- Node-executed regression tests for dashboard JS behavior (`*_via_node`).

### Key Lessons
1. **Close milestones on time.** Retroactive archiving costs more than a timely close, because tooling assumes versioned headings.
2. **Fix lint debt in its own quick task.** Re-deferring it in every plan's `deferred-items.md` is pure overhead.
3. **Compute the fingerprint deterministically.** After a verifier runs, check `verification.status` and fill `covered_digest` with `gsd-tools query verification.fingerprint` if the agent could not.

### Cost Observations
- Model mix: not tracked for this milestone
- Sessions: not tracked
- Notable: cross-AI plan-review lanes were intermittently unavailable (opencode sandbox, xai billing), so reviews fell back to `--codex`.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | n/a | 6 | Autonomous-run infra first (convergence + clean-room E2E) |
| v1.1 | n/a | 4 | Skill-authoring pipeline (writing-skills → skill-judge → naming-analyzer) |
| v1.2 | n/a | 9 | Strict phase chain on a shared package; audit → cleanup → close |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.1 | 1682 | n/a | stdlib-only skills |
| v1.2 | 2535 | n/a | stdlib-only checkers (YAML/TOML readers hand-rolled) |

### Top Lessons (Verified Across Milestones)

1. Live verification against real data and real CLIs catches what fixtures miss (v1.0 tool-substitution, v1.2 dashboard).
2. Pre-existing lint debt left out of scope keeps resurfacing. Schedule it once instead of deferring it forever.
