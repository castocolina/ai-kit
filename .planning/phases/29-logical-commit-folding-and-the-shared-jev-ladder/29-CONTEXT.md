# Phase 29: Logical-commit folding and the shared jev ladder - Context

**Gathered:** 2026-11-03 (interactive, standard discuss mode `--analyze --all --batch`, after 29-SPEC.md; best over easy, DESIGN-01)
**Status:** Ready for planning

<domain>
## Phase Boundary

One reusable folding step turns every finished GSD plan and every finished superpowers plan, in any project, into
one commit per logical feature, following one written folding policy, with the tested tree proven unchanged and a
local backup tag on the old tip. The jev ladder moves into `jev-fast-decision`, and every caller chains that skill
as a black box and still finishes without it. Pushes, branches, PRs and the merge chain are Phase 29.1.
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**10 requirements are locked.** See `29-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `29-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- The one folding policy text and its doc-contract test.
- The reusable folding step for a finished GSD plan and a finished superpowers plan: range, grouping, fold, tree
  proof, backup tag, the main-and-merged guard, the five-line subagent report.
- Moving the ladder caller into `jev-fast-decision` with one documented entry point and its tests.
- Rewiring spec-discuss, goal-prompt, the precompact hook and the decision-probe hook to chain jev as a black box,
  with the structural and text tests.
- The judge bar (JDG-04) for every SKILL.md this phase adds or materially changes.
- Amending FLOW-01 and RULE-17, splitting Phase 29.1 out in the roadmap, and recording the Phase 49 coupling.

**Out of scope (from SPEC.md):**
- Branches, pushes, PRs, gh-stack or plain `gh`, the merge chain, deleting backup tags on merge, MVP main-only
  merging, push consent, `git.*` config, the health-check archive and the AGENTS.md ship rule — Phase 29.1.
- The playbook that carries the policy in generated rules — Phase 47 (RULE-17, amended).
- An advisory-hook reminder at commit or push time — Phase 49's discuss (coupling recorded).
- jev backends per host, calibration, the on/off knob — Phase 34. OpenCode Zen removal — Phase 32.1.
- Executor or reviewer choice through jev; the GitLab mirror.
</spec_lock>

<decisions>
## Implementation Decisions

### Where the folding step lives and when it runs

- **D-01: The engine ships now as a small, temporary `ai-kit-commit-fold` skill, built to move.** A stdlib script
  plus the folding policy under the skill's `references/`; no skill-specific absolute or relative paths baked into
  callers; callers find it through the installed-skill lookup (D-13 pattern). In Phase 45 the engine moves into
  `ai-kit-project-rules`, `skills/ai-kit-commit-fold/` is deleted, and the callers are updated with their tests
  intact (RULE-27 added, Phase 45 criterion 7 added).
  - The precision lives in the code and tests (temporary index, tree check, expected-old-tip ref update, backup
    tag, guards), not in the skill-versus-rules choice; the callers call the script directly.
  - Owner choice after a clarification round (the owner does not want a skill for everything).
- **D-02: GSD side: an ai-kit GSD extension at `execute:wave:post`, spiked first.** After each wave it folds each
  plan of that wave, in plan order, before the next wave forks. It fires in any GSD project with the extension
  installed, whether execution started through ai-kit or plain `/gsd-execute-phase`.
  - Live: gsd-core 1.18.0 has no per-plan lifecycle point; `execute:wave:post` exists
    (`workflows/execute-phase.md`, `references/loop-hook-dispatch.md`); third-party capabilities install through
    `gsd-tools capability install <spec>` with a trust step. A `step` hook dispatches `ref.agent` (a subagent,
    which fits the five-line subagent report), `ref.skill` (as `gsd-<skill>`) or `ref.command` (a gsd-tools
    subcommand only); which form can run the fold is the spike's question.
  - **If the spike fails, planning returns to the owner; there is no silent fallback.** No fallback through
    `ai-kit-spec-execute-gsd`: Phase 31 removes that skill.
  - Owner choice (recommended option), with the spike rule added by the owner.
- **D-03: superpowers side: one step in `ai-kit-spec-execute-superpowers`, after the last task's review passes
  and before superpowers' finishing step.** superpowers plans carry an explicit fold step at their end; the adapter
  makes sure the plan it runs ends with that step before execution starts. `ai-kit-spec-review` reporting a
  superpowers plan without the fold step as a finding is REV-08 in Phase 40 (coupling, not built here).
  - The adapter's SKILL.md changes materially, so it meets the judge bar here (D-16).
  - Owner choice (recommended option) plus the owner's two additions; the "adapter makes sure the step is there"
    mechanism is own reasoning, open to the planner's shape.
  - **Refined 2026-11-03 (29.1 spec):** the adapter step hands the finished plan to ai-kit's unit flow (fold, push, stacked draft PR); superpowers' finishing step is not used to merge, push or open a PR for a unit (29.1 R1, R4). superpowers governs none of these rules.
- **D-04: A plan's range is identified per plan, inside the wave.** For GSD: the plan's own commits (scope
  `({phase}-{plan})`, its `docs({phase}-{plan})` commit) plus GSD's merge-back of that plan's worktree; plans of
  one wave fold in plan order so a later plan's fold sits on the earlier plan's folded tip. For superpowers: the
  plan branch's commits after its merge-base with the base branch.
  - **Refined 2026-11-03 (29.1 spec):** both ranges are what each adapter supplies as a checkpoint of the framework-neutral unit contract (29.1 R1, FLOW-10); the fold engine reads only the contract.
- **D-05: GSD's own worktree merge-back is part of the plan's range** (SPEC R5 amended, edge row superseded).
  - Live: worktree mode (`workflow.use_worktrees`, default true) merges each executor branch with
    `git merge --no-ff --no-edit -m "chore: merge executor worktree (<branch>)"` (`bin/lib/worktree-safety.cjs`).
    Refusing every merge commit would refuse every worktree-mode plan. A merge commit that is not that plan's
    merge-back still refuses the fold.

### How features are grouped

- **D-06: The rule-based grouping comes from the plan's tasks.** Each GSD task (its files) or superpowers task
  (its heading and files) is a candidate feature; tasks that touch the same files merge, so a change and its tests
  stay together; a commit that matches no task joins the feature whose files it touches. Owner choice (recommended).
  - **Refined 2026-11-03 (29.1 spec):** "the plan's tasks" are the feature candidates an adapter supplies through the unit contract; a later system (grill-me, spec-kit) supplies its own.
- **D-07: jev gets one `choice` item per commit, with the rule-based candidate features as options**, through the
  documented entry point (D-12), one item per call. The answers form a partition only if every commit is placed
  exactly once and no code change is split from its tests; otherwise the rule-based grouping decides. The log
  records which source decided. Items carry commit subjects, path names and task summaries only. Owner choice
  (recommended).
- **D-08: GSD's plan-docs changes (SUMMARY, STATE, ROADMAP, REQUIREMENTS) go into the last folded feature commit**,
  so two features give two commits (SPEC R2 literal). Owner choice (recommended).
- **D-09: Features that cannot be separated cleanly become one commit, and the report says why** (the fold always
  finishes and never writes an unbuildable commit). Owner choice (recommended).
  *(amended 2026-11-04, 29 plan review cycle 2: the fold proves only the tip's tree, before and after
  replay; an intermediate folded commit is not built or tested, and an import across features is not
  detected. The policy text and 29-06 state this limit. "Never unbuildable" holds for the tip only;
  needs owner confirmation.)*

### Fold mechanics and the policy text

- **D-10: The mechanics** (accepted as proposed):
  - The fold builds its commits with git plumbing in a temporary index (`GIT_INDEX_FILE`); the working tree is
    never touched.
  - The caller passes the tested tip; the fold refuses when the branch no longer points at it.
  - The branch moves only through `git update-ref <ref> <new> <expected-old>`, after the tree proof.
  - The backup tag is `ai-kit-fold/<unit>/<old-short-sha>`, local only (its deletion on merge is Phase 29.1).
- **D-11: The policy text lives once in the fold skill's `references/`** (moving with the engine in Phase 45). The
  doc-contract test pins each rule; AGENTS.md Workflow's folding sentence points to it; Phase 47's playbook carries
  it in full as a copy with a drift test (RULE-17 amended), since a copy install cannot reach another skill's file.
  Own reasoning (follows SPEC R1 and DIST-03).

### The jev ladder

- **D-12: `jev_review.py` gains `ladder` and `detect` commands; the ladder code lives in a new module beside it in
  `skills/jev-fast-decision/scripts/`.** One documented command line for every caller; the moved code keeps
  today's validation, scrubbed child environment, column mapping, `--second-opinion` and consent delegation, and
  today's backend table (Zen removal stays Phase 32.1). Owner choice (recommended).
- **D-13: Each code caller carries a small copy of the installed-skill lookup**, in the order jev's SKILL.md
  documents (today's `client_candidates` order: own skills root, then the Claude, `.agents`, opencode, Cursor and pi
  skills dirs); one drift test compares every copy with that documented order. Code callers: the fold script,
  goal-prompt's `gp_host.py`, `tools/hooks/precompact_core.py`, `tools/hooks/claude_decision_probe.py`. Owner
  choice (recommended).
- **D-14: `decide.py` is deleted in this phase and every caller is updated in the same change.** spec-discuss's
  SKILL.md and `references/decision-table.md` say only to ask `jev-fast-decision` and follow its SKILL.md;
  goal-prompt's `DECIDE_CLI`, `jev_status`, `gp_sections.py` text and SKILL.md backend-check table point at jev;
  `tests/test_ai_kit_gsd_spec_discuss.py`'s ladder tests move to `tests/test_jev_fast_decision.py`. Owner choice
  (recommended).
- **D-15: The remote-consent ask moves into jev's own SKILL.md flow.** spec-discuss's setup no longer runs detect
  or asks consent itself; an agent that follows jev's SKILL.md meets the consent ask there. Own reasoning (follows
  SPEC R10).

### Judge bar

- **D-16: The SKILL.md files that meet JDG-04 in this phase:** `ai-kit-commit-fold` (new), `jev-fast-decision`,
  `ai-kit-gsd-spec-discuss`, `ai-kit-spec-execute-superpowers` (D-03) and `ai-kit-spec-goal-prompt` (its
  backend-check table changes). Each gets new-shape evals and tests, no critical or high finding or grade B or
  better, and no regression beyond judge variation.

### Claude's Discretion

- Module and function names inside the fold skill and the new jev module; the exact report wording within five
  lines; the commit message format beyond naming the feature and the plan.
- How the D-02 spike is written, as long as it runs against a scratch GSD project and records the result.

### Folded Todos

None. Reviewed, not folded: "Atomic, reusable decision-system skills on Jev"
(`.planning/todos/pending/2026-10-18-atomic-reusable-decision-system-skills.md`) stays with Phase 54.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-SPEC.md` — Locked requirements — MUST read before planning
- `.planning/REQUIREMENTS.md` — FLOW-01 (amended), JEV-06, RULE-17 (amended), RULE-27, REV-08, DIST-03, JDG-04, DESIGN-01
- `.planning/ROADMAP.md` — Phase 29 and 29.1 entries, Phase 45 criterion 7, Phase 40 criterion 6, Phase 49 coupling
- `.planning/phases/28-fast-environment-proof-gates/28-SPEC.md`, `28-CONTEXT.md` — no host CLI in tests, no `.planning/` reads in tests
- `.planning/milestones/NEXT-MILESTONE-INPUTS.md` — Round 9 (commits, push and tests; chained PRs), Round 10
- `AGENTS.md` — Workflow (the folding sentence), Non-Negotiable Rules, Testing
- `.claude/gsd-core/workflows/execute-phase.md` — `handle_branching`, the wave merge-back block, `execute:wave:post` dispatch
- `.claude/gsd-core/references/loop-hook-dispatch.md` — hook kinds (`contribution`, `step`, `gate`)
- `.claude/gsd-core/bin/lib/worktree-safety.cjs` — `merge --no-ff` merge-back message
- `.claude/agents/gsd-executor.md` — `<task_commit_protocol>`
- `.claude/gsd-core/workflows/execute-plan.md` — the `docs({phase}-{plan})` commit
- `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` — the ladder caller that moves (`client_candidates`, `find_client`, `ladder`, `detect`)
- `skills/jev-fast-decision/SKILL.md`, `reference.md`, `scripts/jev_review.py` — the new owner of the ladder
- `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py` (`DECIDE_CLI`, `jev_status`), `gp_sections.py`, `SKILL.md`
- `tools/hooks/precompact_core.py` (`find_client`), `tools/hooks/claude_decision_probe.py`
- `skills/ai-kit-spec-execute-superpowers/SKILL.md` — the end-of-plan step (D-03)
- `skills/ai-kit-gsd-spec-discuss/SKILL.md`, `references/decision-table.md` — text that becomes black-box
- `tests/test_ai_kit_gsd_spec_discuss.py`, `tests/test_jev_fast_decision.py`, goal-prompt tests, `tests/test_arch.py`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `decide.py`'s validation (`item_error`, `partition`), output allowlists and `client_candidates` move as they are.
- `jev_review.py`'s argparse CLI (`build_parser`, `main`) takes the two new commands.
- `tests/test_arch.py`'s AST rules and `TestArchNonVacuity` pattern for the cross-skill and black-box checks.

### Established Patterns
- Stdlib-only scripts under system python3; fixture repos in temporary directories; no host CLI in tests.
- Every structural rule gets a non-vacuity counterpart.
- jev answers are advisory and never gate.

### Integration Points
- GSD: the `execute:wave:post` extension (spiked, D-02).
- superpowers: the adapter step before finishing (D-03).
- Every jev caller through the documented entry point and the lookup copies (D-12, D-13).
</code_context>

<specifics>
## Specific Ideas

- Scratch probes from the spec step live in the gitignored `tmp/p29/` (`config_probe.sh`, `ghstack_probe.sh`,
  `facts.md`); they show the method and feed Phase 29.1, and are not deliverables.
- gh-stack 0.3.0 pushes every stack branch with `--force-with-lease --atomic` and cascade-rebases upper branches;
  recorded for Phase 29.1.
</specifics>

<deferred>
## Deferred Ideas and Couplings

- The engine's move into `ai-kit-project-rules` and the standalone skill's deletion — Phase 45 (RULE-27, criterion 7).
- spec-review flags a superpowers plan without a fold step — Phase 40 (REV-08, criterion 6).
- The generated end-of-task, plan and phase playbook carries the folding policy in full — Phase 47 (RULE-17 amended).
- Whether the advisory hook reminds of the policy at commit or push time — Phase 49's discuss (coupling note in the roadmap).
- Branches, pushes, PRs, the merge chain and backup-tag deletion on merge — Phase 29.1, which gets its own spec and discuss.
</deferred>
