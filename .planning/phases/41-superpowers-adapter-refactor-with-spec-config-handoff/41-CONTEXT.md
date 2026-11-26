# Phase 41: Superpowers adapter refactor with spec-config handoff - Context

**Gathered:** 2026-11-23 (interactive, after 41-SPEC.md)
**Status:** Ready for planning (requirement 5 needs the researcher first)

<domain>
## Phase Boundary

The superpowers execute adapter keeps one pinned-resume path and one owner-stop path (hands off to spec-config when no config
exists), gates fix rounds 4 and 5 by the owner's escalation flags, offers an opt-in session-model fallback, passes gates and a
commit guard in the shared dispatch guidance, runs every spawned executor lane with the real-home guard and reports host-config
changes, and moves a flagged executor lane that hits quota to its fallback.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**10 requirements are locked** (requirement 5 flagged: its meaning waits for the researcher). See `41-SPEC.md` for full
requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `41-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** resume and stop consolidation, flag-gated escalation, the session-model fallback and its spec-config
flag, the gate and guard builders, the lane guard and audit, the flagged executor switch, docs, evals and the judge loop.
**Out of scope (from SPEC.md):** editing GSD's or superpowers' own files; code review after execution, jev-picked executors and
lane transport (Phase 42); review-side switching (Phase 40); the runner's retry and classification (38, 38.1); failing a lane on
the audit.

</spec_lock>

<decisions>
## Implementation Decisions

### Consolidation
- **D-01: The single definitions live where the topic already lives.** The pinned resume is defined once in
  `references/state-management.md` (it already holds the resume-state mechanics) and the owner stop once in
  `references/resolution-stops.md`; SKILL.md, `quota-wake.md`, `session-wake.md`, `escalation.md` and
  `dispatch-external-cli.md` link to them and keep no second copy. A doc-contract test counts one marker heading per path.
  **Own reasoning** (jev not asked): the files' current scope matches the two topics. Ledger. Which blocks are duplicates is the
  researcher's open question 1.
  - **Reversibility:** reversible — documentation moves; behavior is pinned by the unchanged evals and tests.

### Flags and fallback
- **D-02: The escalation flags gate rounds 4 and 5 inside the escalation resolve block** through `lane_escalation` and
  `escalation_target(role_lanes, key, kind)` (`lane_settings.py`), kind `runtime` for `escalate_runtime` and `model` for
  `escalate_model`; both off keeps the lane and reports the stuck task. *(owner answer 2026-11-23, recommended option)*
  - **Reversibility:** costly — a behavior change from today's automatic escalation for every existing lane roster.
  - *(amended 2026-11-25 after research, own reasoning, the owner may overrule: `escalation_target` walks lanes after a key
    while the round 4-5 floor bumps only above the stuck lane, so the kind rule of `escalation_target` is applied over the stuck
    lane followed by the lanes ranked above it, nearest first; both flags on keep today's candidates; SPEC amendment 3.)*
- **D-03: The session-model fallback flag is a lane-table boolean** read by one reader next to `lane_usage_limit` (written only
  when true, a non-boolean refused with the key named, the existing `_bool_setting` rule); spec-config's execute-role step asks
  the question (off by default). jev's haiku-or-sonnet pick uses the `jev_names` pattern: summaries only, classes `haiku` and
  `sonnet`, any other, a low or a missing answer leaves the session model. The flag name is fixed at plan time. **Own reasoning.**
  Ledger.

### Guidance and guard
- **D-04: `dispatch_guidance.py` gains two caller-fed builders** (names at plan time) for the gates and the commit guard,
  composed after failure reporting and before the output format (the format stays last); the module keeps its rule of holding no
  framework wording and never editing another framework's prose. How a caller learns a project's gate commands is the researcher's
  open question 4. **Own reasoning.** Ledger.
- **D-05: The real-home guard variable is set in the environment of every executor lane the adapter or the runner spawns as a
  subprocess**; a native subagent runs inside the session's own process and cannot be given the variable, so the report says
  "not applicable" for it. The "inside an ai-kit checkout" marker (a file or folder pair that only the ai-kit repo holds, and a
  linked worktree of it) is fixed at plan time with held-out fixtures. **Own reasoning; verify at plan time.** Ledger.
- **D-06: The host-config audit is a small stdlib function** over a fixed list of host-config files kept as seed data in one module
  (never a decider), resolved against the process's HOME so tests use a scratch HOME; it snapshots `st_mtime_ns` before and
  after a lane and prints changed paths labeled as an observation. **Own reasoning.** Ledger.

### Executor switch and ordering
- **D-07: The executor switch reuses the flagged-lane switch module of Phase 40** (D-04 there) and the runner's
  `--blocked-status <pool>` reader; the dispatch of a flagged lane passes `--pool <provider>:free`. Phase 41 therefore depends on
  Phase 40, and the ROADMAP's "Depends on" line is amended (this commit). **Own reasoning.** Ledger. Confirmed by the owner 2026-11-25 (was PROVISIONAL), as the SPEC.
- **D-08: Build order is a vertical slice.** (1) the behavior-preserving consolidation with its doc-contract tests; (2) flag-gated
  escalation; (3) the fallback flag, the jev pick and the spec-config question; (4) the guidance builders; (5) the guard and the
  audit; (6) the executor switch; (7) evals, docs and the skill-judge loops of `ai-kit-spec-execute-superpowers` and
  `ai-kit-spec-config`.

### Research handoff (requirement 5)
- **D-09: Before planning, the researcher answers the five open questions of the SPEC** and records each answer as a dated
  amendment of `41-SPEC.md` (requirement 5's items and its six unresolved edge rows): resume and stop duplicates; whether
  `uncommitted_edits` and `coverage=` already satisfy the clean-tree and progress items and which file is "the owner's config
  file"; the agent-branch allow-list's real home and paths; how gate commands are found; what a version banner breaks, with a real
  example. Never answered by invented text.

### Claude's Discretion
Names (the flag, the builders, the audit module), the marker for an ai-kit checkout, the audit file list and the exact report
wording.

### Folded Todos
None folded. The unresolved Phase 36 review notes and the 38.1 notes stay with their own phases.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements
- `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md` — Locked requirements — MUST read before planning
- `.planning/ROADMAP.md` §Phase 41 and `.planning/REQUIREMENTS.md` EXE-01, EXE-04, EXE-05, EXE-08, EXE-09

### Earlier decisions this phase builds on
- `.planning/phases/36-spec-config-as-the-hub/36-CONTEXT.md` D-03 (the adapter's config check), D-06 (escalation flags), D-16
  (usage-limited flag and fallback)
- `.planning/phases/38.1-runner-error-classification-and-retry-policy-inserted/38.1-CONTEXT.md` D-12, D-23 to D-27
- `.planning/phases/40-resilient-review-sized-by-jev/40-CONTEXT.md` D-04, D-05 (the switch module and the blocked-until reader)
- `.planning/research/2026-11-02-next-milestone/4-providers-crossai-onboard.md` item 5 and
  `.planning/milestones/NEXT-MILESTONE-INPUTS.md` (the EXE-05 origin)

### Code and docs the phase touches
- `skills/ai-kit-spec-execute-superpowers/SKILL.md` (Steps 1 to 3), `references/` (state-management, resolution-stops, escalation,
  config-check, quota-wake, session-wake, dispatch-external-cli), `ai_kit_spec_superpowers/dispatch_injection.py`, `cli.py`
- `skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py`, `lane_settings.py`, `runner_dispatch.py`, `execute_selection.py`,
  `execute_dispatch.py`, `jev_names.py`; `references/cross-ai.mjs` (finding codes at line 1629, blocked-until reader at 4042 on)
- `skills/ai-kit-spec-config/SKILL.md` (the execute-role step), `tools/setup.py:5187-5312` (the guard)
- `.claude/agents/gsd-executor.md` (read only: the GSD guard block and allow-list regex; never edited)

### Tests that pin or must keep passing
- `tests/test_ai_kit_spec_superpowers.py`, the adapter's evals, `tests/test_role_orders.py`, `tests/test_cross_ai_docs_text.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lane_escalation`, `escalation_target`, `lane_usage_limit`, `lane_fallback`, `_bool_setting` (`lane_settings.py`).
- The adapter's resume file and Restore script, `config-check.md` blocks (session-model mode), `dispatch_guidance.py` builders.
- The runner's `--blocked-status` and `--pool` flags; Phase 40's switch module once built.

### Established Patterns
- `dispatch_guidance.py` holds no framework wording and takes caller text (header of the module).
- Flags are booleans written only when true and refused when non-boolean, with the key named.
- Fake lanes and a scratch HOME in tests; a table of paths is seed data, never a decider.

### Integration Points
- SKILL.md Step 2 (resolve) and Step 3 (dispatch and result table), `references/escalation.md`, `config-check.md`, spec-config's
  execute-role step, the lane environment built for subprocess dispatch.

</code_context>

<specifics>
## Specific Ideas

The executor-brief premise correction (the runner builds no executor prompt) is why requirement 4 targets the shared dispatch
guidance and why the GSD guard text is read, never written, by this phase.

</specifics>

<deferred>
## Deferred Ideas

- A note for open-gsd that its plan template lacks the gates and a uniform guard block (outside this repo's reach).
- Failing a lane on a changed host config (the owner may want it once the audit shows its false-positive rate).

### Reviewed Todos (not folded)
- `2026-11-21-review-notes-left-open-by-phase-37.md`, `2026-11-22-review-notes-left-open-by-phase-38.md` and `...38.1.md`: runner
  notes that belong to their own follow-ups; none changes the adapter.
- 26 other todos matched by keyword only.

</deferred>

---

*Phase: 41-Superpowers adapter refactor with spec-config handoff*
*Context gathered: 2026-11-23*
