# Phase 41: Superpowers adapter refactor with spec-config handoff — Specification

**Created:** 2026-11-23
**Ambiguity score:** 0.31 (gate: ≤ 0.20) — gate not passed: requirement 5 is flagged below minimum and its open questions go to the researcher
**Requirements:** 10 locked (requirement 5's six items are assumptions until the researcher answers them)

## Goal

The superpowers execute adapter keeps one pinned-resume path and one owner-stop path, hands off to spec-config when no config
exists, escalates a stuck task in fix rounds 4 and 5 only along the flags the owner set, can run on the session's own model when
the owner opted in, passes the gates and the commit guard in its dispatch guidance, runs every executor lane of an ai-kit
checkout with the real-home guard and reports host-config changes, and moves a flagged executor lane that hits quota to its
fallback.

## Background

Requirements EXE-01, EXE-04, EXE-05, EXE-08 and EXE-09 (REQUIREMENTS.md) and the ROADMAP's Phase 41 criteria 1 to 6, including the
amendments of 2026-11-16 (Phase 36 D-03: the no-config check already sits in the adapter; the free-lane pool study, PROVISIONAL).
Phase 36 stores `usage_limited`, `escalate_runtime` and `escalate_model` per lane and left their reading to later phases.

**The owner's decisions (highest priority):**

- 2026-11-02 and 2026-11-16: the runner never switches harness, provider or model on its own; a lane flagged `usage_limited`
  switches at once to the first unflagged lane of a different pool; an unflagged lane stops and reports; a direct lane stops at
  once on quota (Phase 38.1 D-12).
- 2026-11-23, answers to this phase's question batch: (1) the escalation flags gate rounds 4 and 5: a stuck task escalates only
  along an enabled flag; (2) the session-model fallback is a persistent flag that spec-config writes, off by default, and with it
  off the error names spec-config as the fix; (3) executor-brief changes go into ai-kit's own briefs and nothing is written into
  another framework's prose.
- jev is advisory and never gates; every jev path has a tested no-jev behavior (2026-11-16).

**Correction after a live check (2026-11-23):** the owner's answer 3 chose "the two briefs ai-kit ships" on a premise that the
runner builds an executor prompt. It does not: `cross-ai.mjs` has no executor-prompt builder (no match for an execute prompt or
brief), so the runner sends the prompt a caller gives it. The only executor brief text ai-kit owns is the shared
`ai_kit_spec/dispatch_guidance.py`, reused by every `ai-kit-spec-execute-*` adapter, whose header states that it never edits a
framework's own prose and takes framework-specific text from the caller. The GSD guard block (`<sequential_execution>`, the
`agent-*` branch allow-list regex) lives in GSD's own `gsd-executor.md` and workflows. Requirement 5 is written against that fact;
the owner confirmed this scope at the gate (2026-11-23) and chose to write the SPEC flagged and research first.

**Decided by own reasoning on 2026-11-23, the owner may overrule:** with the fallback flag on and no jev (or a low jev answer) the
task runs on the session model unchanged, with no haiku or sonnet pick; the real-home audit is a report labeled as an
observation, never a gate, because a host may rewrite its own config during a lane.

**Live facts checked for this spec (2026-11-23, this machine):**

- `skills/ai-kit-spec-execute-superpowers/` holds `SKILL.md` (300 lines), `ai_kit_spec_superpowers/{cli.py (509),
  dispatch_injection.py (469), task_classification.py (55)}`, ten references and 14 evals. The adapter already runs the no-config
  check with its three-answer ask (`references/config-check.md`, scalar `CONFIG_CHECK`, a session-model mode that dispatches
  natively with the model omitted) and keeps a per-task resume file (`superpowers-resume-<project>-task-<N>.json`,
  `RESUME_FOUND`, a Restore script, SKILL.md Step 2).
- Resume and stop text sits in several places: SKILL.md Step 2 and Step 3, `references/state-management.md` (267 lines),
  `quota-wake.md`, `session-wake.md`, `escalation.md`, `resolution-stops.md`, and the dispatch-result handling at SKILL.md lines
  266 to 271 (read, not yet compared line by line).
- Rounds 4 and 5 escalate automatically today (`references/escalation.md`, `escalation_target` in `lane_settings.py`); nothing
  reads `lane_escalation` (the flags) in the adapter.
- `dispatch_guidance.py` has four builders (model-selection override, incremental progress, output format, failure reporting) and
  no builder for gates, a commit guard, verify tolerance or a branch allow-list.
- The runner has finding codes for an execute result (`no_commit`, `task_uncovered`, `forbidden_path`, `no_tree_change`,
  `outside_plan_files`, `uncommitted_edits`, `baseline_replaced`, `coverage_unchecked`) and a `coverage=` status key
  (`cross-ai.mjs:1629-1655`); whether `uncommitted_edits` ignores the owner's config file was not found.
- `AI_KIT_REFUSE_REAL_HOME=1` is honored by `tools/setup.py:5187-5312` and set by the test runner, `time_prepush.py`,
  `env_matrix.py` and `record_cli_help.py`; no executor lane sets it today and nothing compares host-config modification times.
- The origin of the EXE-05 wording is the v1.3 close handoff, lesson 4 (`.planning/research/2026-11-02-next-milestone/4-providers-
  crossai-onboard.md:165`): executor briefs must name the exact gates and the commit-guard block, and the symptoms were an arch
  test left red and an uneven commit guard.

**Open questions for the researcher (`gsd-phase-researcher`), not answered here:**
1. Which resume and stop blocks exist today, and which are duplicates of each other (requirement 1)?
2. Does the runner's `uncommitted_edits` check ignore the owner's own config file today, and which file is "the owner's config
   file" (`.planning/config.json`, `.aikit/config.toml`)? Does `coverage=` already match "the tasks actually done"?
3. What exactly is the agent-branch allow-list "applied the same way on every path": the GSD guard's regex, a runner check, or a
   superpowers-side check, and which paths exist (native, external CLI, resumed)?
4. How does an adapter learn a project's unit and arch gate commands (AGENTS.md, the Makefile, the plan's verify lines)?
5. What does a "version banner" break in a verify line, with a real example from an executor run?

## Requirements

1. **The adapter keeps one pinned-resume path and one owner-stop path (EXE-01)**: the pinned resume (restoring a task's saved
   injection and round) and the owner stop (every outcome that ends a run for the owner) are each defined once; every other
   place points to that definition; the first step keeps the shared no-config check that hands off to spec-config.
   - Current: resume and stop text is spread over SKILL.md and at least five references (see Background).
   - Target: one reference holds each path; SKILL.md and the other references link to it and hold no second copy.
   - Acceptance: a doc-contract test finds exactly one definition of each path and fails when a second copy appears; the
     existing 14 evals and `tests/test_ai_kit_spec_superpowers.py` pass unchanged except where this SPEC names a behavior
     change; with no config the adapter still asks once and chains to spec-config.

2. **The escalation flags gate fix rounds 4 and 5 (EXE-01)**: at fix round 4 or 5 a stuck task escalates its runtime only when
   the lane's `escalate_runtime` flag is true and its model only when `escalate_model` is true, through `lane_escalation` and
   `escalation_target`; with both flags off the task stays on its lane and the round reports the stuck task to the owner.
   - Current: rounds 4 and 5 escalate to a more capable candidate automatically; `lane_escalation` has no reader in the adapter.
   - Target: the escalation block of `references/escalation.md` reads the flags first.
   - Acceptance: fake-lane tests: flag `escalate_model` only moves to a more capable model of the same runtime; flag
     `escalate_runtime` only moves to another runtime; both on keep today's order; both off keep the lane and report; a
     non-boolean flag is refused with the key named (the reader's existing rule).

3. **An opt-in session-model fallback runs when no configured executor is available (EXE-04)**: with the flag on and no
   configured executor lane available (all unavailable, blocked or out of quota), a task runs on the session's own model, with
   jev choosing haiku or sonnet when jev answers confidently and the session model unchanged otherwise; with the flag off the
   error names spec-config as the fix; spec-config writes the flag.
   - Current: a session-model mode exists only from the no-config ask; no flag, no jev pick, no spec-config question.
   - Target: a boolean lane-table flag read by one reader, a spec-config question that writes it (off by default), and the
     adapter step that applies it.
   - Acceptance: fake-lane tests: flag on and every lane unavailable runs natively on the session model; jev answering haiku or
     sonnet sets that model, a low or missing answer leaves the session model; flag off stops with a message that names
     `ai-kit-spec-config`; the flag round-trips through spec-config's write and read; a lane that is available is never replaced
     by the fallback.

4. **The dispatch guidance lists the gates and the commit guard (EXE-05, part 1)**: `dispatch_guidance.py` gains builders for the
   unit and arch gates and for the commit guard; both take their text from the caller (a project's gate commands, a framework's
   guard block) and hold no framework-specific wording; every superpowers implementer dispatch includes them when the caller
   supplies them.
   - Current: four builders, none for gates or a guard.
   - Target: two caller-fed builders composed into `build_dispatch_reinforcement_guidance`.
   - Acceptance: unit tests: the builders return the supplied text framed once and nothing when the caller supplies none; the
     composed guidance keeps its fixed order; no framework name appears in the module; a superpowers dispatch fixture carries
     both blocks when supplied.

5. **The checks around an executor run behave as the owner listed (EXE-05, part 2)** *(⚠ below minimum: the researcher's open
   questions 2 to 5 decide the exact behavior; the planner treats these six items as assumptions until they are answered)*:
   (a) verify lines pass when a tool prints a version banner; (b) the clean-tree check ignores the owner's own config file;
   (c) the progress counter equals the tasks actually done; (d) the agent-branch allow-list applies the same way on every
   path; (e) the commit guard is uniform across paths; (f) the gates are named in the guidance of requirement 4.
   - Current: not verified (see the open questions); the runner has finding codes and a `coverage=` key from Phase 38.
   - Target: each item holds on every dispatch path, with the owner-decided meaning recorded after research.
   - Acceptance: a fake-lane test per item once its meaning is fixed; until then the plan's first task records the researcher's
     answer for each item in a dated amendment of this SPEC.

6. **Every executor lane of an ai-kit checkout runs with the real-home guard (EXE-08, part 1)**: in an ai-kit checkout the
   superpowers adapter's dispatches and the runner's execute role run with `AI_KIT_REFUSE_REAL_HOME=1` in the lane's
   environment; outside an ai-kit checkout nothing is added.
   - Current: no executor lane sets it.
   - Target: the lane environment carries the variable when the working directory is an ai-kit checkout (the marker is fixed at
     plan time).
   - Acceptance: fake-lane tests assert the variable in the child environment inside a fixture ai-kit checkout and its absence
     in a plain fixture repo.

7. **The execute flow reports real host-config changes made during a lane (EXE-08, part 2)**: before and after each executor
   lane the flow records the modification times of the real host-config files and reports any that changed as an observation,
   naming the file and noting that a host may rewrite its own config; it never fails the lane on this alone.
   - Current: nothing compares modification times (an unexplained rewrite of two real config files was noticed by hand on
     2026-11-23).
   - Target: a before-and-after audit over a fixed list of host-config files, printed in the lane report.
   - Acceptance: a fake lane that touches a synthetic config file inside a scratch HOME is reported with its path; a lane that
     touches nothing reports no change; the audit lists only files, never recurses into session or log folders; the report
     states the observation label.

8. **A flagged executor lane that hits quota moves to a fallback of a different pool (EXE-09)** *(PROVISIONAL, needs owner
   confirmation)*: when an execute lane stops on a quota error, the adapter reads `lane_usage_limit` and `lane_fallback` and the
   pool's blocked-until record (through the runner's `--blocked-status <pool>`): a flagged lane moves at once to the fallback, a
   lane whose blocked-until time has not passed is skipped at selection, the first selection after that time tries it once, and
   an unflagged lane keeps stopping and reporting.
   - Current: a quota stop on any lane is an owner stop; the readers have no caller in the adapter.
   - Target: the same rule as Phase 40's review switch, applied at executor selection and on a quota stop; the dispatch of a
     flagged lane passes `--pool <provider>:free`.
   - Acceptance: fake-lane fixtures cover each of the four cases and a flagged lane with no eligible fallback (reported, not
     replaced).

9. **The SKILL.md and references describe the new behavior once (EXE-01, EXE-04, EXE-08)**: `ai-kit-spec-execute-superpowers`
   SKILL.md and its references describe the flags, the fallback, the guard and the audit in one place each.
   - Current: the skill has no text for these.
   - Target: short pointers in SKILL.md and the detail in the references already holding the matching topic.
   - Acceptance: doc-contract tests pin each topic's single location and the narrowed escalation wording.

10. **Every changed SKILL.md meets the judge bar (JDG-04)**: `ai-kit-spec-execute-superpowers` and `ai-kit-spec-config` (and any
    other SKILL.md this phase changes) carry new-shape evals and tests and pass the skill-judge loop.
    - Current: the adapter carries 14 evals, none for the fallback, the flag gating or the audit.
    - Target: each judged result has no critical or high finding, or grade B or better, and no regression beyond the judge's
      run-to-run variation.
    - Acceptance: the judge records meet the bar of AGENTS.md and `make check-dogfood` validates them; `evals.json` gains one
      eval each for the fallback, the flag-gated escalation, a flagged-lane switch and the host-config audit.

## Boundaries

**In scope:**
- The adapter's resume and stop consolidation, the flag-gated escalation, the session-model fallback and its spec-config flag,
  the gate and guard builders in `dispatch_guidance.py`, the lane real-home guard and the audit, the flagged executor switch, the
  docs and evals, and the judge loop.

**Out of scope:**
- Editing GSD's `gsd-executor.md`, its workflows or its plan template, and superpowers' own task-brief scripts (other systems;
  a note for open-gsd is recorded instead).
- Code review after execution, jev-picked executors and lane transport (Phase 42).
- Review-side lane switching (Phase 40) and the runner's own retry and classification (Phases 38 and 38.1).
- A hard failure on a changed host-config file (the audit only reports).

## Constraints

- Runtime code stays stdlib-only; jev is reached only through the existing client and never gates; only summaries go to jev.
- The new guidance builders hold no framework-specific wording and never edit another framework's prose.
- A lane switch or fallback stays inside the owner's roster, and the session-model fallback runs only when the owner's flag is on.
- Tests use fake lanes, a scratch HOME and synthetic config files; no test touches a real host config.
- No machine-specific absolute path in skill text, tests or fixtures; model names in fixtures are placeholders.
- The free-lane pool items stay PROVISIONAL in every artifact until the owner confirms them.

## Acceptance Criteria

- [ ] Exactly one definition each of the pinned-resume path and the owner-stop path; the 14 existing evals still pass
- [ ] Escalation flags decide rounds 4 and 5 (each flag alone, both, neither)
- [ ] The fallback flag round-trips through spec-config; on, every lane unavailable: the task runs on the session model with a jev
  haiku or sonnet pick when confident; off: the error names spec-config
- [ ] Gate and guard builders return caller text only, hold no framework wording and sit in the composed guidance
- [ ] Each of the six EXE-05 part 2 items has a fake-lane test after the researcher fixes its meaning (⚠ assumption until then)
- [ ] The real-home guard variable is in the lane environment inside an ai-kit checkout and absent outside
- [ ] The host-config audit reports a changed synthetic file as an observation and never fails the lane on it
- [ ] A flagged executor lane on quota moves to a different-pool fallback; a blocked pool is skipped; an unflagged lane stops
- [ ] Every changed SKILL.md meets the judge bar of AGENTS.md

## Edge Coverage

**Coverage:** 36/42 applicable edges resolved (23 covered or backstop, 13 dismissed with the owner's approval of 2026-11-23) · 6 unresolved (all of requirement 5, flagged assumptions until the researcher answers open questions 2 to 5)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| boundary | R1 | ✅ covered | R1 acceptance: the existing evals and tests pass unchanged except where this SPEC names a behavior change. |
| adjacency | R1 | ⛔ dismissed | Documentation structure; no two values touch. |
| empty | R1 | ✅ covered | R1 acceptance: with no config the adapter still asks once and chains to spec-config. |
| encoding | R1 | ⛔ dismissed | A doc-contract count of definitions; no text-encoding semantics. |
| ordering | R1 | ✅ covered | R1 acceptance: the first step keeps the shared no-config check before the start step and any resume. |
| precision | R1 | ✅ covered | R1 acceptance: a doc-contract test finds exactly one definition of each path. |
| boundary | R2 | 🧪 backstop | Held-out fixture: a flag on with no eligible target keeps the lane and reports. |
| precision | R2 | ✅ covered | R2 acceptance: a non-boolean flag is refused with the key named. |
| boundary | R3 | 🧪 backstop | Held-out fixture: exactly one configured lane that is blocked counts as no executor available and triggers the fallback when the flag is on. |
| adjacency | R3 | ✅ covered | R3 acceptance: a lane that is available is never replaced by the fallback. |
| empty | R3 | 🧪 backstop | Held-out fixture: no `[lanes]` table and the flag absent leaves today's no-config ask. |
| encoding | R3 | 🧪 backstop | Held-out fixture: a jev answer outside haiku and sonnet is discarded and the session model stays. |
| ordering | R3 | ⛔ dismissed | One fallback target; there is no order to keep. |
| precision | R3 | 🧪 backstop | Held-out fixture: a jev answer with `needs_fallback` true counts as low and leaves the session model. |
| adjacency | R4 | ⛔ dismissed | The two builders are independent text frames. |
| empty | R4 | ✅ covered | R4 acceptance: a builder returns nothing when the caller supplies none. |
| encoding | R4 | 🧪 backstop | Held-out fixture: caller text containing braces or markup is framed verbatim, with no format interpolation. |
| ordering | R4 | ✅ covered | R4 acceptance: the composed guidance keeps its fixed order. |
| boundary | R5 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open questions 2 to 5). |
| adjacency | R5 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open questions 2 to 5). |
| empty | R5 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open questions 2 to 5). |
| ordering | R5 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open questions 2 to 5). |
| precision | R5 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open questions 2 to 5). |
| concurrency | R5 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (researcher open questions 2 to 5). |
| adjacency | R6 | 🧪 backstop | Held-out fixture: a subdirectory or a linked worktree of an ai-kit checkout is detected as one. |
| empty | R6 | 🧪 backstop | Held-out fixture: an inherited `AI_KIT_REFUSE_REAL_HOME` with another value is set to 1 in the lane environment. |
| ordering | R6 | ⛔ dismissed | An environment variable; no order semantics. |
| adjacency | R7 | 🧪 backstop | Held-out fixture: two touched files are both reported, in the audit list's order. |
| empty | R7 | ✅ covered | R7 acceptance: a lane that touches nothing reports no change. |
| encoding | R7 | 🧪 backstop | Held-out fixture: a changed file whose path holds spaces or non-ASCII characters is reported verbatim. |
| ordering | R7 | ⛔ dismissed | The audit list order is fixed and the report follows it. |
| concurrency | R7 | ✅ covered | R7 acceptance: the report states the observation label, so a change made by another process or lane is not read as this lane's fault. |
| adjacency | R8 | 🧪 backstop | Held-out fixture: when the next lane shares the failed lane's pool, the fallback skips it. |
| empty | R8 | ✅ covered | R8 acceptance: a flagged lane with no eligible fallback is reported, not replaced. |
| ordering | R8 | 🧪 backstop | Held-out fixture: with two eligible fallbacks the earlier one in the role's order is taken. |
| adjacency | R9 | ⛔ dismissed | A documentation placement rule. |
| empty | R9 | ⛔ dismissed | A documentation placement rule; no input. |
| encoding | R9 | ⛔ dismissed | A documentation placement rule. |
| ordering | R9 | ⛔ dismissed | A documentation placement rule. |
| adjacency | R10 | ⛔ dismissed | The judge loop is a process over files; no values touch. |
| empty | R10 | ⛔ dismissed | A skill with no change is not judged; the requirement names the changed ones. |
| ordering | R10 | ⛔ dismissed | Judge rounds have no order semantics beyond the three-round cap of AGENTS.md. |

## Prohibitions (must-NOT)

**Coverage:** 5/5 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT edit another framework's own prose or files (GSD agents, workflows or plan template, superpowers scripts) to deliver a brief change | R4, R5 | resolved | test (a diff-scope check over the changed files) and judgment review; wired-check descriptor left empty until plan time |
| MUST NOT switch an unflagged lane, and MUST NOT run the session-model fallback when its flag is off | R3, R8 | resolved | test (R3 and R8 acceptance); wired-check descriptor left empty until plan time |
| MUST NOT touch a real host config in any test, and MUST NOT fail a lane on the host-config audit alone | R6, R7 | resolved | test (scratch HOME; the audit never changes a lane's exit status); wired-check descriptor left empty until plan time |
| MUST NOT send code, diffs, file contents, config values or secrets to jev | R3 | resolved | test (a seam that records the payload) and judgment review; wired-check descriptor left empty until plan time |
| MUST NOT change today's behavior when jev is absent, errors or answers with low confidence | R3 | resolved | test (no-jev fixtures); wired-check descriptor left empty until plan time |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                                   |
|--------------------|-------|------|--------|-----------------------------------------------------------------------------------------|
| Goal Clarity       | 0.82  | 0.75 | ✓      | adapter paths, flags, fallback, guard, audit, executor switch                           |
| Boundary Clarity   | 0.65  | 0.70 | ⚠ Below minimum — planner must treat as assumption | which brief and which paths EXE-05 covers (open questions 2, 3) |
| Constraint Clarity | 0.55  | 0.65 | ⚠ Below minimum — planner must treat as assumption | how gate commands are found; what a banner breaks (open questions 4, 5) |
| Acceptance Criteria| 0.66  | 0.70 | ⚠ Below minimum — planner must treat as assumption | EXE-05 part 2 has no testable meaning until research |
| **Ambiguity**      | 0.31  | ≤0.20| ⚠      | gate not passed; written anyway, flagged                                                |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

Run mode `interactive`, 1 question round plus the gate question. jev was not asked: in the interactive path it screens only
items the owner asks it to screen. Rule: mvp-mode inactive, the best design wins over the smallest diff.

| Round | Perspective     | Question summary                                                    | jev (advisory) | Decision locked |
|-------|-----------------|---------------------------------------------------------------------|----------------|-----------------|
| 1     | Researcher      | What exists in the adapter and the runner for EXE-01, 04, 05, 08, 09? | none         | Resume file and no-config check exist; escalation flags unread; no gate or guard builder; no real-home guard on lanes (Background) |
| 1     | Boundary Keeper | Which executor briefs does EXE-05 change?                           | none           | Owner chose "the two briefs ai-kit ships"; a live check then showed only `dispatch_guidance.py` exists, so R4 and R5 are written against it (correction in Background) |
| 1     | Boundary Keeper | Where does the session-model fallback flag live?                    | none           | A spec-config-written config flag, off by default (R3) |
| 1     | Failure Analyst | Do the escalation flags gate rounds 4 and 5?                        | none           | Yes, escalate only along an enabled flag (R2) |
| —     | Own reasoning   | Fallback pick without jev; audit as report only                     | none           | Session model unchanged; observation label, never a gate (R3, R7). Ledger. |

| gate  | Seed Closer     | Scope of EXE-05 after the live check; edges and prohibitions        | none           | Write flagged, research first; 13 dismissals, 23 covered or backstop rows and five prohibitions approved; six requirement 5 rows left unresolved (owner, 2026-11-23) |

---

*Phase: 41-superpowers-adapter-refactor-with-spec-config-handoff*
*Spec created: 2026-11-23*
*Next step: /gsd-discuss-phase 41 — implementation decisions (the two single-definition homes, the flag reader, the audit file list, the ai-kit checkout marker)*
