# Phase 44: curated-config writes the agreed settings — Specification

**Created:** 2026-11-23
**Ambiguity score:** 0.23 (gate: ≤ 0.20) — gate missed by 0.03; requirement 7 is flagged and goes to the researcher; no dimension below its minimum
**Requirements:** 8 locked (requirement 7 is an assumption until the researcher answers)

## Goal

On a fixture project, curated-config writes the agreed profile, routing, models, effort, skills, graph flags and workflow
defaults through the project's `gsd-tools`, removes nothing it did not plan, runs the effort sync for the checkout and a worktree
session's launch directory, and sets (or records that GSD already has) the keys that make the plan checker read a plan again
after review amends it.

## Background

Requirements CUR-03, CUR-04, CUR-05, CUR-07, CUR-08, CUR-09 and LENS-03 (REQUIREMENTS.md) and the ROADMAP's Phase 44 criteria 1
to 8. Phase 43 (tagged docs, cascade, v1 records) comes first; Phase 39's role-keyed skill table is a dependency; Phase 39.2's
check on GSD branching names couples to the "branch per phase" default below.

**The owner's decisions (highest priority):**

- 2026-11-23, Phase 43 answers that this phase inherits: profile and routing stop being questions and become defaults written
  here; the one cross-AI execution confirmation stays here; `rigorous` and the cross-AI plan review choice stay reachable as plan
  edits (no existing feature removed).
- Owner rules: never remove an existing setting or feature; writes go through the project's `gsd-tools`; no write to `~/.claude`
  or any user-level config; every follow-up that changes a checkout is listed and approval-gated; jev is advisory and never
  gates, with a tested no-jev behavior on every path.
- The effort sync must also cover the launch directory of a worktree session (the owner's recorded rule: config-set plus
  `effort sync --apply`, also the launch dir's `.claude/agents`).

**Decided by own reasoning on 2026-11-23, the owner may overrule:** "branch per phase" writes `git.branching_strategy = "phase"`
and leaves `git.phase_branch_template` at GSD's default (a custom template that differs from the default is reported, never
rewritten), because the default template renders the names the fold flow creates. **Confirmed by the owner at the gate
(2026-11-23):** the effort sync is an approval-gated follow-up as `followups` already works, one approval covering both
directories.

**Live facts checked for this spec (2026-11-23, this machine, installed gsd-core 1.22.0):**

- Installed docs (`references/planning-config.md`): `git.branching_strategy` defaults to `"none"` and `git.phase_branch_template`
  to `"gsd/phase-{phase}-{slug}"`; `workflow.use_worktrees` defaults to `true`; GSD itself degrades to sequential execution when
  the current branch is ahead of `origin/HEAD` (a one-line "Worktree base mismatch" warning, restored by `worktree.baseRef:"head"`
  in `.claude/settings.local.json`), and a runtime whose `dispatch.isolation` is `none` with an explicit `true` fails closed
  (warning `W025`); `workflow.plan_check` defaults to `true`.
- `model-profiles.md` documents `dynamic_routing.enabled`, `escalate_on_failure`, `max_escalations` and `tier_models`; curated-config's
  `presets.py` already writes `dynamic_routing.*` for the adaptive profile and `recommend.py` writes
  `model_profile_overrides.<host>.<tier>`; jev is already used in `recommend.py`, `skills.py` and `skill_scan.py`.
- `graphify.enabled` and `graphify.auto_update` exist in `workflows/settings.md` and `bin/lib/graphify.cjs`
  (`references/planner-graphify-auto-update.md` describes the auto-update).
- `followups.py` holds `effort_sync_argv` and `EFFORT_SYNC_HOSTS = ("claude", "codex", "opencode")`, lists follow-ups in one block
  and runs nothing without approval; its notes say effort sync is not offered on a host with no `effort:` frontmatter or without a
  project-local gsd-core.
- The installed `plan-phase.md` mentions `--reviews` replanning but a grep found no line stating that the plan checker runs again
  after a review amends the plan (not read line by line).
- The `workflow_defaults.py` (60 lines) and `frontend_detect.py` (87 lines) exist; the plan `plan-set` and `apply` machinery
  (`plan_edit.py`, `apply.py`) is the write path.

**Open questions for the researcher (`gsd-phase-researcher`), not answered here:**
1. Does gsd-core 1.22.0 run the plan checker again after `--reviews` amends a plan and before execution, and which key (if any)
   controls it? Cite the installed docs by file and line (requirement 7).
2. Does every curated-config write already go through the project's `gsd-tools config-set` (requirement 1), or does any path
   write the file directly?
3. How is the launch directory of a worktree session found for the second effort sync (requirement 6)?

## Requirements

1. **The agreed profile, routing, models and effort are written through `gsd-tools` and nothing unplanned is removed (CUR-03)**:
   curated-config sets the balanced profile, `dynamic_routing.*`, the tier models and per-agent models and effort (classified with
   jev when present), every write through the project's `gsd-tools config-set`, with effort values validated against the host's
   allowed set; a setting it did not plan survives an apply.
   - Current: presets and `recommend` already derive these values; whether every write path uses `config-set` is open question 2.
   - Target: one write path, all through `gsd-tools`, with validation before the write.
   - Acceptance: a fixture config holding an unplanned key (for example `workflow.skip_discuss`) keeps it after apply; an invalid
     effort value is refused with its key named and nothing is written for it; a seam spy records only `config-set` calls (no
     direct file write); with jev absent the catalog or default effort is used and the run says so.

2. **The workflow defaults are written as agreed (CUR-04)**: UI phases and UI review are on only for a UI project; cross-AI
   execution asks one confirmation; `response_language` is English; `claude_md_path` names a real `AGENTS.md`; branch per phase
   writes `git.branching_strategy = "phase"` and leaves the template at GSD's default; `intel` is on; `workflow.use_worktrees`
   stays on unless the owner turns it off, and the plan states the cases where GSD itself turns it off, quoted from the installed
   docs (a branch ahead of `origin/HEAD` degrades to sequential; a runtime with `dispatch.isolation: none` and an explicit `true`
   fails closed).
   - Current: `workflow_defaults.py` writes the two UI flags; the other defaults are not all written.
   - Target: each default is a plan entry with its reason and its source label.
   - Acceptance: fixtures: a UI project gets both flags true and a non-UI project false; `claude_md_path` pointing at a missing
     file is refused; a project with a custom `phase_branch_template` gets the strategy written, the template untouched and a
     note that it differs from GSD's default; `use_worktrees` is never written `false` without an owner answer; the plan text for
     `use_worktrees` names both docs cases.

3. **Skills are assigned to GSD agents by responsibility through the role-keyed table (CUR-05)**: assignments come from the
   skills actually available on the host, using the shared role-keyed table of Phase 39; an unsorted skill is offered to
   `classify-skills` and never assigned by guess.
   - Current: `skills.py` resolves and proposes; the shared table exists from Phase 39.
   - Target: assignment reads the table and the host's skills only.
   - Acceptance: fixtures: a skill present on the host and in the table is assigned to the agent of its role; a skill absent from
     the host is never assigned; an unsorted skill appears in the classify offer and not in the assignments.

4. **Graphify flags are turned on when graphify is installed (CUR-07)**: with graphify installed curated-config writes
   `graphify.enabled` and `graphify.auto_update` true and says what each does (from the installed docs); without graphify it
   says so and writes neither; it never leaves the graph switched off without saying.
   - Current: no write for these keys.
   - Target: two plan entries with their effects and a visible note when graphify is absent.
   - Acceptance: fixtures: graphify present yields both keys true with the effect text; graphify absent yields no write and a
     note; a project that already sets `graphify.enabled = false` keeps it and the plan shows it as an owner choice, never
     overwritten.

5. **The lens wiring is proposed from the skills present (LENS-03)**: curated-config proposes the lens wiring for a target
   project from the skills actually present (`impeccable` only for a UI project, plugin skills only on runtimes that can load
   them); run on ai-kit itself it proposes no change to the wiring Phase 39 set.
   - Current: no lens proposal in curated-config.
   - Target: a proposal built from the role-keyed table and the host's skills, with `impeccable` gated by the UI detection.
   - Acceptance: fixtures: a UI project proposes `impeccable`, a non-UI one does not; a plugin skill on a runtime that cannot
     load it is not proposed; a run against a copy of ai-kit's own wiring proposes an empty change.

6. **The effort sync runs for the checkout and the worktree launch directory and reports stale agents (CUR-08)**: after effort
   settings are written, `effort sync --apply` runs for the checkout and for the launch directory of a worktree session, and the
   report names any agent file still carrying the old effort; a fixture with two agents directories proves it.
   - Current: `followups.effort_sync_argv` builds the call for one directory and runs nothing without approval.
   - Target: the follow-up block lists both directories (open question 3 finds the second) and a report of stale agent files.
   - Acceptance: a fixture with two agents directories: both syncs are listed, both run after approval, and an agent file left
     with the old effort is reported with its path; a host with no effort frontmatter or no project-local gsd-core is not offered.

7. **The plan checker reads an amended plan again, or the doc citation is recorded (CUR-09)** *(⚠ below minimum: open question 1
   decides; the planner treats it as an assumption)*: curated-config sets the GSD keys that make the plan checker read a plan
   again after review amends it and before execution, citing the installed docs; when GSD already does this by default it
   records the citation and writes nothing.
   - Current: not verified; the installed docs show only `workflow.plan_check` (default true).
   - Target: either a key set with a docs citation or a recorded citation with no write.
   - Acceptance: the plan's first task records the researcher's answer with a file-and-line citation as a dated amendment of
     this SPEC; a fixture config shows the result (keys set, or unchanged).

8. **Every changed SKILL.md meets the judge bar (JDG-04)**: `ai-kit-gsd-curated-config` SKILL.md carries new-shape evals and tests
   and passes the skill-judge loop.
   - Current: the skill carries 6 evals, none for the writes of this phase.
   - Target: the judged result has no critical or high finding, or grade B or better, and no regression beyond the judge's
     run-to-run variation.
   - Acceptance: the judge record meets the bar of AGENTS.md and `make check-dogfood` validates it; `evals.json` gains one eval
     each for the unplanned-key survival, the graphify flags and the two-directory effort sync.

## Boundaries

**In scope:**
- The writes of the agreed settings (profile, routing, models, effort, workflow defaults, skills, graphify flags, lens wiring),
  the effort sync follow-up for two directories, the plan-checker keys or their citation, docs, evals and the judge loop.

**Out of scope:**
- The cascade, the tagged-docs reader and the v1 records (Phase 43).
- Installing or updating GSD, `gsd update`, writes into `~/.claude` or any user-level config.
- Changing a custom `git.phase_branch_template` or turning `use_worktrees` off without the owner.
- Changing the shared jev client; the runner and lane code.

## Constraints

- Runtime code stays stdlib-only; every config write goes through the project's `gsd-tools` and none is a direct file write.
- Effort and model values are validated before any write; a rejected value writes nothing for it.
- jev is advisory with a tested no-jev behavior; only summaries go to jev.
- Tests use a fixture project, fake `gsd-tools` seams and a scratch HOME; no test touches a real host config.
- Every default carries its source label (installed docs, ai-kit seed or unverified).
- No machine-specific absolute path in skill text, tests or fixtures.

## Acceptance Criteria

- [ ] An unplanned config key survives an apply; an invalid effort value is refused with its key named; every write is a
  `config-set` call
- [ ] UI flags follow the UI detection; `claude_md_path` must be a real file; the branching strategy is written as `phase` with the
  template untouched and a differing custom template reported
- [ ] `use_worktrees` is never written `false` without an owner answer and its plan text names both GSD cases
- [ ] Skills are assigned by role from the host's skills only; an unsorted skill goes to the classify offer
- [ ] Graphify present: both keys true with their effects; absent: a note and no write; an owner `false` is kept
- [ ] The lens wiring is proposed from the skills present; ai-kit's own wiring yields an empty change
- [ ] Two agents directories both get the effort sync after approval and stale agent files are reported
- [ ] The plan-checker answer is recorded with a doc citation and the fixture config shows the result (⚠ assumption until then)
- [ ] The changed SKILL.md meets the judge bar of AGENTS.md

## Edge Coverage

**Coverage:** 26/33 applicable edges resolved (16 covered or backstop, 10 dismissed with the owner's approval of 2026-11-23) · 7 unresolved (R3 unclassified and all of R7, flagged assumptions)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | R1 acceptance: an unplanned neighboring key survives an apply. |
| empty | R1 | 🧪 backstop | Held-out fixture: an empty plan writes nothing and exits 0. |
| ordering | R1 | 🧪 backstop | Held-out fixture: writes follow plan order, so the profile is written before the overrides that depend on it. |
| idempotency | R1 | 🧪 backstop | Held-out fixture: applying the same plan twice leaves the config bytes unchanged after the first apply. |
| concurrency | R1 | ⛔ dismissed | `gsd-tools` owns the file write and its locking; apply issues its calls one after another. |
| adjacency | R2 | 🧪 backstop | Held-out fixture: a project whose only frontend signal is a stylesheet in a docs folder follows the existing `frontend_detect` verdict, and the plan shows it. |
| empty | R2 | ✅ covered | R2 acceptance: a `claude_md_path` pointing at a missing file is refused. |
| encoding | R2 | 🧪 backstop | Held-out fixture: `response_language` is written as the literal value GSD documents for English, fixed at plan time. |
| ordering | R2 | ⛔ dismissed | The defaults are independent keys. |
| concurrency | R2 | ⛔ dismissed | One apply writes the defaults one after another. |
| unclassified | R3 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (no shape cue matched the skill-assignment requirement). |
| adjacency | R4 | ✅ covered | R4 acceptance: an owner-set `graphify.enabled = false` is kept and shown as an owner choice. |
| empty | R4 | ✅ covered | R4 acceptance: graphify absent writes nothing and prints a note. |
| encoding | R4 | ⛔ dismissed | Two boolean keys; no encoding semantics. |
| ordering | R4 | 🧪 backstop | Held-out fixture: `graphify.enabled` is written before `graphify.auto_update`. |
| adjacency | R5 | ✅ covered | R5 acceptance: a plugin skill on a runtime that cannot load it is not proposed. |
| empty | R5 | ✅ covered | R5 acceptance: ai-kit's own wiring yields an empty change. |
| ordering | R5 | ⛔ dismissed | The proposal is a set; order carries no meaning. |
| adjacency | R6 | 🧪 backstop | Held-out fixture: when the checkout is its own launch directory the sync runs once. |
| empty | R6 | ✅ covered | R6 acceptance: a host with no effort frontmatter or no project-local gsd-core is not offered. |
| encoding | R6 | 🧪 backstop | Held-out fixture: an agents directory path with spaces is passed as one argv item. |
| ordering | R6 | ⛔ dismissed | The checkout runs first and the launch directory second, a fixed order with no dependency. |
| idempotency | R6 | 🧪 backstop | Held-out fixture: a second sync after the first reports no stale agent file. |
| concurrency | R6 | ⛔ dismissed | The two syncs run one after another after one approval. |
| boundary | R7 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open question 1). |
| adjacency | R7 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open question 1). |
| empty | R7 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open question 1). |
| ordering | R7 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open question 1). |
| precision | R7 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open question 1). |
| concurrency | R7 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open question 1). |
| adjacency | R8 | ⛔ dismissed | The judge loop is a process over files; no values touch. |
| empty | R8 | ⛔ dismissed | A skill with no change is not judged; the requirement names the changed one. |
| ordering | R8 | ⛔ dismissed | Judge rounds have no order semantics beyond the three-round cap of AGENTS.md. |

## Prohibitions (must-NOT)

**Coverage:** 5/5 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT write any config except through the project's `gsd-tools config-set`, and MUST NOT remove a setting it did not plan | R1 | resolved | test (a seam spy records only `config-set` calls; an unplanned key survives); wired-check descriptor left empty until plan time |
| MUST NOT write under `~/.claude` or any user-level config, and MUST NOT run `gsd update` or an installer | R2, R6 | resolved | test (a scratch-HOME run compares file modification times) and doc-contract; wired-check descriptor left empty until plan time |
| MUST NOT turn `workflow.use_worktrees` off, rewrite a custom `git.phase_branch_template`, or overwrite an owner-set graphify value without the owner | R2, R4 | resolved | test (R2 and R4 acceptance); wired-check descriptor left empty until plan time |
| MUST NOT run the effort sync without the owner's approval | R6 | resolved | test (no run before an approval token in the follow-up block); wired-check descriptor left empty until plan time |
| MUST NOT send code, config values or secrets to jev, and MUST NOT change today's behavior when jev is absent or low | R1 | resolved | test (a payload-recording seam and a no-jev fixture); wired-check descriptor left empty until plan time |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                           |
|--------------------|-------|------|--------|---------------------------------------------------------------------------------|
| Goal Clarity       | 0.85  | 0.75 | ✓      | the agreed writes, the effort sync, the plan-checker keys                         |
| Boundary Clarity   | 0.75  | 0.70 | ✓      | Phase 43 owns reading and asking; no user-level writes                           |
| Constraint Clarity | 0.70  | 0.65 | ✓      | write-path verification and the launch directory left to the researcher          |
| Acceptance Criteria| 0.72  | 0.70 | ✓      | 9 pass/fail criteria; requirement 7 acceptance waits for research                 |
| **Ambiguity**      | 0.23  | ≤0.20| ⚠      | gate missed by 0.03; no dimension below its minimum                              |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

Run mode `interactive`, 1 question at the gate. jev was not asked: in the interactive path it screens only items the owner asks
it to screen. Rule: mvp-mode inactive, the best design wins over the smallest diff.

| Round | Perspective     | Question summary                                              | jev (advisory) | Decision locked |
|-------|-----------------|---------------------------------------------------------------|----------------|-----------------|
| 1     | Researcher      | What do the GSD docs and curated-config write today?          | none           | Defaults and keys read from the installed 1.22.0 docs; presets, followups and workflow defaults exist (Background) |
| 1     | Boundary Keeper | Branch per phase and the template                             | none           | Strategy `phase`, template left at GSD's default, a differing one reported (R2). Ledger. |
| 1     | Failure Analyst | CUR-09: does GSD re-run the plan checker after review?        | none           | Not visible in the installed docs: researcher open question 1 (R7) |
| gate  | Boundary Keeper | Effort sync: approval-gated follow-up or automatic?           | none           | Approval-gated follow-up, one approval for both directories (owner, 2026-11-23; R6) |
| gate  | Seed Closer     | Approve the flagged SPEC (0.23), edges and prohibitions?      | none           | Approved and committed flagged (owner, 2026-11-23): 10 dismissals, 16 covered or backstop rows, 7 unresolved, five prohibitions |

---

*Phase: 44-curated-config-writes-the-agreed-settings*
*Spec created: 2026-11-23*
*Next step: /gsd-discuss-phase 44 — implementation decisions (write path, second launch directory, lens proposal shape, graphify effects text)*
