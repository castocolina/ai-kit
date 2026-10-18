# Phase 20: Live Validation on Codex + Opencode — Specification

**Created:** 2026-10-14
**Ambiguity score:** 0.14 (gate: ≤ 0.20)
**Requirements:** 9 locked

## Goal

The v2 `ai-kit-gsd-curated-config` is shown working from the user's own interactive codex and
opencode sessions on scratch projects. gsd-tools resolves every agent as planned on both hosts,
and the two open verifications are settled and reflected in code and SKILL.md: the live codex
env signal, and the opencode lane from an opencode host.

## Background

- **20-CONTEXT D-01..D-06 (2026-09-23) stay locked.** They cover headless iteration and then
  the user's interactive run as the only evidence, the host order (already in Phase 16), the
  local install for opencode models, the fix threshold, the codex signal and the opencode lane.
- **GSD is now per repository (2026-10-14).** No global gsd-core exists for codex, opencode,
  pi or cursor on this machine (`~/.codex/gsd-core` and `~/.config/opencode/gsd-core` are
  absent), and `~/.config/opencode/agents` holds no GSD agents. D-03's description of the user's
  global opencode setup is out of date; its conclusion (models take effect only through a
  project-local install) still holds.
- **Host CLIs:** codex-cli 0.153.4 and opencode 1.18.35 are installed (amended 2026-10-18: this phase ran codex-cli 0.162.1 and opencode v2.0.31).
- **Inherited contracts:**
  - Phase 18 R14: the follow-up installer is `npx -y @opengsd/gsd-core@<version> --<host> --local`.
  - Phase 18 R2: a lane is never the host, which matches D-06's default until it is settled.
  - Phase 19 R5/R6: the smoke script and the model-and-tier matrix.
  - 16.1 `child_env`: the host-signal scrub for headless runs.
- A copied `resolve_model_ids: "omit"` is the installer's intended value on non-Claude hosts
  (17 D-21). With it, `GSD_RUNTIME=codex resolve-model gsd-planner` returned `gpt-5.6-sol` in a
  scratch project (2026-10-14).

## Requirements

1. **Host gsd-core per scratch project**: the same gsd-core on every host.
   - Current: no host-level installs.
   - Target: before `inventory`, the smoke script installs gsd-core locally into each scratch project for that host. It uses the same pinned command as Phase 18 R14, pinned to the version used on the claude host. The run records version and scope (17 D-11).
   - Acceptance: each smoke log shows `scope: local` and the pinned version in the inventory.

2. **Codex smoke** (EVAL-04).
   - Current: none.
   - Target: from the user's interactive codex session, the Phase 19 smoke script runs `inventory`, `recommend`, `apply --dry-run` and a real `apply` on the two scratch projects. The script is parameterized by host, and nothing runs on ai-kit beyond `inventory` and the dry run.
   - Acceptance: `20-SMOKE-CODEX.md` records the plan, the resulting config, the diff and a forced-failure restore. ai-kit's config is byte-identical.

3. **Codex env signal** (EVAL-04, D-05).
   - Current: `CODEX_THREAD_ID`/`CODEX_VERSION` labelled "observed in session snapshots".
   - Target:
     - The interactive session reports which of the two variables are set.
     - The detection docstring label becomes "live-verified" for those.
     - A variable that does not appear is dropped from detection. It stays in the 16.1 scrub only if it is still read anywhere.
   - Acceptance: the evidence shows the variable names (never their values beyond presence), and a unit test pins the detection table.

4. **Codex matrix** (APP-05 on codex).
   - Current: none.
   - Target: the Phase 19 matrix (5 combinations × 35 agents) runs with `GSD_RUNTIME=codex`. `model` and `tier` match the plan, with native sol/terra/luna kept where valid (17 D-02).
   - Acceptance: a recorded run with every row passing, saved in `20-SMOKE-CODEX.md`.

5. **Opencode smoke and local models** (EVAL-05, D-03).
   - Current: none.
   - Target:
     - From the user's interactive opencode session, the smoke runs on both scratch projects.
     - After the approved local install, the project's opencode agent files carry `model:` lines that match the plan.
     - The run shows that opencode loads the project agents over any global ones.
     - It records whether the project's `.opencode/` output should be committed or gitignored.
   - Acceptance: `20-SMOKE-OPENCODE.md` lists each GSD agent's planned versus baked model, all equal, plus the precedence evidence and the recorded gitignore decision.

6. **Opencode lane from an opencode host** (EVAL-05, D-06).
   - Current: not recommended (default).
   - Target: the run determines whether `/gsd-review` skips the opencode lane on an opencode host, or can use it intentionally with another provider/model. `recommend`'s lane eligibility and SKILL.md follow the finding.
   - Acceptance: the finding is in the evidence. If usable, a golden plan shows the lane with a vendor different from the planner's; if not, a test asserts it is never proposed.

7. **Opencode matrix** (APP-05 on opencode).
   - Current: none.
   - Target: the same matrix with `GSD_RUNTIME=opencode`; `model` and `tier` match the plan, and `anthropic/*` defaults are overridden (17 D-02).
   - Acceptance: a recorded run with every row passing.

8. **Headless iteration** (D-01).
   - Current: n/a.
   - Target:
     - Before the interactive runs, headless `codex exec` and `opencode run` iterations go through the cross-AI runner with the 16.1 host-signal scrub.
     - A killed or hung dispatch is probed with a short foreground run that polls output growth before any retry.
     - Known transient blockers are recorded as environment findings, not skill bugs: the opencode xai billing block, and the sandbox denying `external_directory` access.
   - Acceptance: the evidence lists each headless run with its status line and any environment findings.

9. **Fixes and gates** (D-04).
   - Current: n/a.
   - Target: small, local fixes land in this phase with a regression test. A fix that changes a CONTEXT decision or spans modules becomes a decimal phase. The user gets a short interactive-run script per host. `make test` and `make validate` are green.
   - Acceptance: each fix links its evidence; any decimal phase is in ROADMAP; both gates are green.

## Boundaries

**In scope:**
- The codex and opencode smoke runs and matrices, with local gsd-core per scratch project
- Settling the codex signal and the opencode lane, and updating code and SKILL.md to match
- Small fixes, and decimal phases for larger ones

**Out of scope:**
- cursor (Phase 21) and pi (Phase 22)
- Any change to the user's global opencode or codex configuration
- Machine-level GSD installs (tools-installer)

## Constraints

- Only the user's own interactive sessions count as EVAL-04/EVAL-05 evidence.
- Scratch projects live where each host's sandbox can write. Never use real tool configs as fixtures.
- No secret value appears in any evidence file.

## Acceptance Criteria

- [ ] Each scratch project's inventory shows a local, pinned gsd-core
- [ ] Codex smoke passes on both scratch projects, and ai-kit is unchanged
- [ ] The codex signal is live-verified and the detection table updated
- [ ] The codex matrix passes for 5 × 35
- [ ] Opencode's baked agent models equal the plan, and project agents win over global ones
- [ ] The opencode-lane finding is reflected in `recommend` and SKILL.md with a test
- [ ] The opencode matrix passes for 5 × 35
- [ ] Headless runs and environment findings are recorded
- [ ] `make test` and `make validate` are green
- [ ] MUST NOT: the user's global opencode/codex configuration is never modified
- [ ] MUST NOT: no secret value or env-variable value appears in the evidence

## Edge Coverage

**Coverage:** 30/31 applicable edges resolved · 1 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | The pinned version equals the claude host's resolved version, never a nearby one |
| empty | R1 | ✅ covered | A failed local install stops the smoke before `inventory` |
| ordering | R1 | ✅ covered | Install runs before `inventory`, every time |
| idempotency | R1 | ✅ covered | A second local install of the same version changes no agent file (added by the author) |
| idempotency | R2 | ✅ covered | A second apply on the same scratch project changes nothing but adds a backup |
| concurrency | R2 | 🧪 backstop | Smoke steps are sequential |
| adjacency | R3 | ✅ covered | A codex launched from Claude still detects as codex (host order) |
| empty | R3 | ✅ covered | Neither variable set means codex is not detected from env, and the evidence says so |
| encoding | R3 | ✅ covered | Only variable names and presence are recorded, never values |
| ordering | R3 | 🧪 backstop | The detection table order is pinned by a unit test |
| adjacency | R4 | ✅ covered | A specialist override and its tier are checked separately |
| empty | R4 | ✅ covered | `model: ""` is a failure unless inheritance was planned |
| ordering | R4 | ✅ covered | Agents are reported in sorted order |
| adjacency | R5 | ✅ covered | A same-named global agent never shadows the project agent (evidence) |
| empty | R5 | ✅ covered | An agent without a planned model keeps no `model:` line |
| ordering | R5 | ✅ covered | Project agents load before global ones |
| concurrency | R5 | 🧪 backstop | One opencode session per scratch project |
| unclassified | R6 | ⚠ UNRESOLVED | No shape cue; the finding and its test are specified in Acceptance |
| adjacency | R7 | ✅ covered | An `anthropic/*` default is replaced, and a valid native slot is kept |
| empty | R7 | ✅ covered | `model: ""` is a failure unless inheritance was planned |
| ordering | R7 | ✅ covered | Agents are reported in sorted order |
| adjacency | R8 | 🧪 backstop | A hung run is probed before a retry, never retried blindly |
| empty | R8 | ✅ covered | A run with no status line counts as a failure |
| ordering | R8 | 🧪 backstop | Headless iterations precede the interactive runs |
| idempotency | R8 | 🧪 backstop | A rerun of a passing headless iteration passes again |
| concurrency | R8 | 🧪 backstop | Headless runs are sequential |
| boundary | R9 | ✅ covered | A fix touching exactly one module stays in-phase; two modules make a decimal phase |
| adjacency | R9 | 🧪 backstop | A fix that changes a CONTEXT decision always becomes a decimal phase |
| empty | R9 | ✅ covered | No fixes needed: the evidence says so explicitly |
| ordering | R9 | 🧪 backstop | A fix's regression test lands in the same commit |
| precision | R9 | 🧪 backstop | The one-module threshold counts Python modules, not files touched by docs |

## Prohibitions (must-NOT)

**Coverage:** 2/2 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT modify the user's global opencode or codex configuration | R5 | resolved | test (semantic allowlist guard before/after in the smoke script; amended 2026-10-14, 20 D-10) |
| MUST NOT write a secret or an env-variable value into the evidence | R3 | resolved | judgment |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Two hosts, two verifications |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | 21, 22, global configs excluded |
| Constraint Clarity | 0.82  | 0.65 | ✓      | Interactive evidence only |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 11 pass/fail criteria |
| **Ambiguity**      | 0.14  | ≤0.20| ✓      | Initial 0.22 (per-repo GSD changed the setup); one round |

## Interview Log

`--auto`, one round. 20-CONTEXT D-01..D-06 are kept as locked. jev-fast-decision screened the open item (Laya first; `needs_fallback` to TypeSafe direct). Summaries only, advisory. Rule: best design over the smallest diff.

| Round | Perspective | Question summary | Laya (advisory) | TypeSafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Researcher | What changed since 2026-09-23? | – | – | No global GSD on codex/opencode; opencode 1.18.35, codex 0.153.4; 18 R14 installer; 16.1 scrub (Background) |
| 1 | Boundary Keeper | Where does each scratch project's host gsd-core come from? | pinned_local_per_scratch 0.54 (fb) | pinned_local_per_scratch 1.00 | R1: local install per scratch project, pinned to the claude host's version |

---

*Phase: 20-live-validation-on-codex-opencode*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 20 — implementation decisions (how to build what's specified above)*
