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

## Milestone: v1.3 — GSD Curated Config v2

**Shipped:** 2026-10-31
**Phases:** 18 (16-27, with inserted 16.1, 18.1, 21.1-21.3, 25.1) | **Plans:** 212 | **Sessions:** not tracked

### What Was Built
- The curated-config v2 pipeline (inventory, recommend, plan, apply) on one (runtime, model) vocabulary, evaluated on claude and smoke-validated headless on codex, opencode, cursor and pi.
- Decision-system skills, a PreCompact pre-summary hook and visible tool-advisory hooks as setup knobs.
- A host-split status line (Claude Code and Cursor CLI) with AST architecture guards.
- A quota-aware cross-AI runner with a configurable retry ladder, plus `ai-kit-cross-ai`, `ai-kit-session-wake`, `ai-kit-gsd-spec-discuss` and `ai-kit-spec-goal-prompt`.

### What Worked
- An audit before the close found three real integration defects (a wait-policy contradiction, a broken relative link, missing README rows) and all three were fixed in-milestone.
- Recording owner-only steps as `*-OWNER-CAPTURES.md` kits kept `human_needed` phases honest instead of forcing a green status.
- Spikes before plans (21, 21.2, 22, 23, 26) stopped several plans from resting on untested assumptions.

### What Was Inefficient
- Bookkeeping drifted: REQUIREMENTS traceability, ROADMAP checkboxes and STATE.md frontmatter were stale for most of the milestone and needed a dedicated refresh before the audit.
- Skill-judge rounds repeated on the same skills across phases 25, 25.1 and 26; two verdicts ended UNRESOLVED and three were deferred to a refactor todo.
- Most phase verifications read `stale` after later phases touched covered files, so the close was an `override_closeout` again (as in v1.2).
- The milestone grew from phases 16-22 to 16-27 plus six inserted phases while the header still read "Phases 16-22".

### Patterns Established
- Owner-pending work is a named capture file per phase, listed in the milestone entry, never silently closed.
- Cross-AI failures are classified and reported; the runner never switches harness, provider or model on its own.
- Status-line role modules follow banner-delimited blocks, enforced by `tests/test_arch.py` with non-vacuity tests.

### Key Lessons
1. **Update the milestone header and traceability as phases are inserted.** A late refresh costs a whole audit pass.
2. **Decide skill-judge deferrals in the phase that finds them.** An UNRESOLVED verdict carried across three phases is rework.
3. **Plan the live-host steps as owner kits from the start.** The phases that did this (25, 25.1, 26, 27) closed cleaner than the ones that discovered the need at verification.

### Cost Observations
- Model mix: not tracked for this milestone
- Sessions: not tracked
- Notable: cross-AI review lanes used the owner's router-backed referees; direct Zen and Cursor API billing errors did not recover and were classified by route.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | n/a | 6 | Autonomous-run infra first (convergence + clean-room E2E) |
| v1.1 | n/a | 4 | Skill-authoring pipeline (writing-skills → skill-judge → naming-analyzer) |
| v1.2 | n/a | 9 | Strict phase chain on a shared package; audit → cleanup → close |
| v1.3 | n/a | 18 | Spikes before plans; owner-capture kits for live steps; audit gaps closed before the close |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.1 | 1682 | n/a | stdlib-only skills |
| v1.2 | 2535 | n/a | stdlib-only checkers (YAML/TOML readers hand-rolled) |
| v1.3 | 5644 (unit + arch groups) | n/a | stdlib-only runtime modules; Textual stays wizard-only |

### Top Lessons (Verified Across Milestones)

1. Live verification against real data and real CLIs catches what fixtures miss (v1.0 tool-substitution, v1.2 dashboard).
2. Pre-existing lint debt left out of scope keeps resurfacing. Schedule it once instead of deferring it forever.
