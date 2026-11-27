# Phase 42: Code review after execution and jev-picked executors - Context

**Gathered:** 2026-11-23 (interactive, after 42-SPEC.md)
**Status:** Ready for planning (the spike needs the owner's consent line first)

<domain>
## Phase Boundary

After the superpowers adapter executes a plan, a capped code-review loop runs on the same review lanes as spec review with the
lens skills, jev classifies lane results and gray areas, jev picks the executor from the owner's roster (a lite executor also gets
a lite file beside the plan-writer brief), and each lane's transport (subprocess, resumed session, herdr pane) is chosen from what
a recorded spike verified, reused within a plan and renewed after a set number of rounds.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**8 requirements are locked.** See `42-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `42-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** the code-review step and loop, lens loading, the jev executor pick, the lite block, the spike record,
the transport chooser and reuse, jev lane-result classification, docs, evals and the judge loop.
**Out of scope (from SPEC.md):** Phase 40's ping, switch, partial report and jev modules and Phase 41's flags, fallback, guidance
and audit (reused); redefining the herdr protocol, label or sweep; editing superpowers' or GSD's files; a new jev backend;
switching an unflagged lane.

</spec_lock>

<decisions>
## Implementation Decisions

### Code review
- **D-01: The review step is a new reference (`references/code-review.md`) and a SKILL.md step** after the last task's own review
  and before the fold step. It calls superpowers' `requesting-code-review` through the host's skill mechanism, then runs the
  capped loop (cap 3, pass on no CRITICAL or HIGH open) on Phase 40's lane machinery. How a review lane receives the diff (prompt
  shape, size limit) is a plan-time check that reuses the `reviewer_dispatch` seams. **Own reasoning** (jev not asked); the cap
  and the pass rule are the owner's. Ledger.
- **D-02: UI detection reuses the frontend extension tuple of `task_classification`** (made public, one source) over the diff's
  changed paths; lens delivery goes through `lens_delivery` with the role-keyed table; a missing lens uses `LENS_NOTES`.
  **Own reasoning.** Ledger.
  - *(amended 2026-11-26, after research: `lens_delivery.UI_EXTENSIONS` is already public and `lens_set` detects UI from the
    review lane's `--files`; the frozen cross-skill import allowlist forbids an import between the packages, so the changed
    paths go to the lanes as `--files`, the adapter tuple stays private and the existing pin test keeps the two tuples one rule;
    SPEC amendment 2)*
- **D-03: Gray areas at `receiving-code-review`'s stop-and-discuss point go through Phase 40's jev classification module** (same
  classes, same CRITICAL and HIGH exception, same no-jev path). **Own reasoning.** Ledger.

### Executor pick and lite file
- **D-04: `pick_executor` runs after `resolve_execute_candidates` and before `candidates_to_ladder`**, on Phase 40's jev module
  pattern: one item set summarizing each remaining candidate (runtime, model, effort, catalog class, task affinity), a sentinel
  for no answer, a log line "executor pick: <key> (jev, <confidence>)" or "default". The plan-level pick for the lite file runs
  the same function over the roster at plan time with no task. **Own reasoning.** Ledger.
- **D-05: The lite block is its own file beside the plan-writer brief**, written by a small adapter script at plan time and handed
  over by the same rail that hands over `.aikit/brief/SKILL.md`; the brief and the fold tool stay untouched (SPEC amended,
  dated). "Lite" is the catalog class of the pick (selector fixed at plan time); the block text is written at plan time, judged,
  and labeled unverified. The pick happens twice by design: once for the plan at brief time (advisory) and once per task at
  dispatch. **Own reasoning.** Ledger.

### Spike and transport
- **D-06: The spike follows the owner's consent rule and AGENTS.md's theory, hypothesis, spike order.** It runs only after a
  consent line, from a script under the phase's `spike/` folder with a scratch HOME and a scratch directory, and records one row
  per installed host (version, date, session id source, headless resume result, label) in the phase's spike record; the chooser
  plans start after it. **Own reasoning and AGENTS.md.** Ledger. *(note 2026-11-27, owner decision: the owner skipped the resume
  spike on 2026-11-27; no host is probed and no spike record is written in this phase, every resume label stays unverified and no
  runner label flips; the spike is backlog Phase 999.36; SPEC amendment 13)*
- **D-07: The chooser is a seam next to the runner dispatch** (module name at plan time) with a per-plan record in the run
  directory: resumed session over subprocess for a headless lane, a herdr pane only for a lane the owner marked interactive (a
  lane setting spec-config writes only when true, name at plan time); a transport is offered only when its label is verified for
  the recorded host version; the renewal count is a named constant. The herdr result file is the only verdict; the pane closes at
  plan close and `--sweep` closes leftovers. *(owner decision 2026-11-23 for the precedence; the rest own reasoning)* Ledger.
  - **Reversibility:** costly — a per-plan transport record and a lane setting join the runner's run directory and the config.

### jev lane results
- **D-08: Phase 40's jev module gains two classifiers** (execute result: done, partial, another round; review finding: fit by
  kind, test tier, reproducibility, end-user reach, MVP versus production). Defaults without jev: the runner's outcome for
  execute and the reviewer's own severity for review; the run log says which decided. Summaries only. **Own reasoning.** Ledger.

### Order
- **D-09: Build order is a vertical slice.** (1) the spike request and record (owner consent); (2) executor pick and the lite file;
  (3) the code-review step, lenses and gray-area routing; (4) the transport chooser; (5) lane-result classification; (6) evals,
  docs and the skill-judge loop of `ai-kit-spec-execute-superpowers`.

### Claude's Discretion
Names (the pick function, the chooser module, the interactive lane setting), the renewal count, the lite selector, the spike's
host list (the installed hosts) and the exact log wording.

### Folded Todos
None folded.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements
- `.planning/phases/42-code-review-after-execution-and-jev-picked-executors/42-SPEC.md` — Locked requirements — MUST read before planning
- `.planning/ROADMAP.md` §Phase 42 and `.planning/REQUIREMENTS.md` EXE-02, EXE-03, EXE-06, EXE-07, LENS-02

### Earlier decisions this phase builds on
- `.planning/phases/40-resilient-review-sized-by-jev/40-CONTEXT.md` D-04, D-06 (switch and jev modules); `41-CONTEXT.md` D-03, D-07
- `.planning/phases/37-shared-runner-options-and-session-ids/37-CONTEXT.md` (herdr protocol, label, run directory, resume forms)
- `.planning/phases/38-runner-hardening-and-run-safety/38-CONTEXT.md` D-25, D-27 (the runner's `--sweep` and run record)
- `.planning/phases/39-lane-capability-blocks-and-lens-skills/39-CONTEXT.md` (the role-keyed table, lens delivery)

### Code and docs the phase touches
- `skills/ai-kit-spec-execute-superpowers/SKILL.md`, `references/` (a new code-review reference), `ai_kit_spec_superpowers/
  task_classification.py`, `dispatch_injection.py`
- `skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py`, `execute_dispatch.py`, `reviewer_dispatch.py`, `lens_delivery.py`,
  `runner_dispatch.py`, `references/skill-roles.json`, `references/cross-ai.mjs` (resume forms near line 1769, herdr, `--sweep`)
- `skills/ai-kit-commit-fold/` (read only: `boundary` writes the brief and stays neutral)

### Tests that pin or must keep passing
- `tests/test_ai_kit_spec_superpowers.py`, `tests/test_lens_delivery.py`, the adapter's evals, `tests/test_role_orders.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `classify_task`, the frontend extension tuple, `resolve_execute_candidates`, `candidates_to_ladder`, `lens_delivery`, the
  runner's resume forms and `--sweep`, Phase 40's switch, ping, partial-report and jev modules, Phase 41's flags.

### Established Patterns
- Every jev and herdr path has a tested no-jev and no-herdr behavior; only summaries go to jev.
- A transport or pick stays inside the owner's roster and never changes harness, provider or model on its own.
- Live probes need the owner's consent line; spikes use a scratch HOME.

### Integration Points
- The adapter's final-review step, the fold step, `execute_selection` flow, the runner dispatch seam, the plan-writer rail.

</code_context>

<specifics>
## Specific Ideas

The lite block is a separate file because the brief is the fold tool's neutral output; this keeps `ai-kit-commit-fold` unchanged
and the lite text owned by the adapter.

</specifics>

<deferred>
## Deferred Ideas

- Measuring the lite block's effect on a lite model (labeled unverified until a run compares plans).
- Pane reuse beyond a plan and an automatic interactive marker (the owner marks interactive lanes for now).

### Reviewed Todos (not folded)
- 26 other todos matched by keyword only; none concerns code review, executor picks or transports.

</deferred>

---

*Phase: 42-Code review after execution and jev-picked executors*
*Context gathered: 2026-11-23*
