# Phase 29: Logical-commit folding and the shared jev ladder — Specification

**Created:** 2026-11-03
**Ambiguity score:** 0.15 (gate: ≤ 0.20)
**Requirements:** 10 locked

## Goal

Every finished GSD or superpowers plan is folded, by one reusable step that follows one written folding policy, into
one commit per logical feature with the tested tree proven unchanged, and every caller reaches jev only by chaining
the installed `jev-fast-decision` skill, still finishing when that skill or every backend is missing.

## Scope

The folding step, the folding policy and the shared jev ladder serve any project, GSD or superpowers, through
ai-kit's skills. ai-kit is their first user: it is mostly a GSD project but also runs superpowers plans, under the
same rules. Every requirement below is **general**. The ai-kit-only items are dogfood of general ones and sit in
Phase 29.1: ai-kit's own GSD config (FLOW-05; general counterpart: curated-config writing branch per phase,
CUR-04, Phase 44) and AGENTS.md's ship rule (FLOW-07; general counterpart: the end-of-phase playbook, RULE-17,
Phase 47). The fixture tests use one GSD fixture project and one superpowers fixture project, never ai-kit's own
repo. *(amended 2026-11-03, 29.1 spec: ai-kit's flow is framework-neutral: the fold engine takes a unit's checkpoint (commit range, tested tip, feature candidates) through the unit contract of Phase 29.1 (FLOW-10); GSD and superpowers are its first two thin adapters, and another spec-driven system plugs in through the same contract; superpowers itself governs none of the fold, branch or PR rules, which are ai-kit's own)*

## Background

Live-verified on 2026-11-03 in the ai-kit checkout (scratch copies and scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1`;
scripts and notes under the gitignored `tmp/p29/`):

- **How a GSD plan ends today.** gsd-core 1.18.0's executor commits once per task (`{type}({phase}-{plan}): …`,
  `.claude/agents/gsd-executor.md` `<task_commit_protocol>`), then `execute-plan.md` adds one
  `docs({phase}-{plan}): complete … plan` commit (SUMMARY, STATE, ROADMAP, REQUIREMENTS). gsd-core has lifecycle
  points `execute:wave:pre/post`, `execute:pre/post`, `verify:*` and `ship:*`, but none after a single plan (a wave
  may hold several plans). Nothing folds commits; the only squash in gsd-core is `complete-milestone`'s optional
  squash merge of whole branches.
- **How a superpowers plan ends today.** superpowers plans live under `docs/superpowers/plans/`; a plan runs on its
  own branch or worktree and ends in superpowers' finishing step. ai-kit's `ai-kit-spec-execute-superpowers` only
  injects a (runtime, model) pair at the implementer dispatch point; it has no end-of-plan step.
- **The owner's folding rule today** lives only in AGENTS.md Workflow ("fold related work into as few
  logically-grouped, buildable commits as possible") and in session memory (compact per phase by a subagent). No
  code implements it, and nothing checks that a fold kept the tested tree.
- **The jev ladder.** The client that talks to the backends is `skills/jev-fast-decision/scripts/jev_review.py`
  (`CLIENT_PROTOCOL = 2`, subcommands `--probe`, `--skip-local`, `consent`). The ladder caller is
  `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` (649 lines: item validation, the scrubbed child environment,
  the per-backend column mapping, `detect`, `--second-opinion`, consent delegation) with its own installed-skill
  lookup (`client_candidates`: its own skills root, then the Claude, `.agents`, opencode, Cursor and pi skill dirs).
- **Who reaches into another skill today.** `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py` runs
  spec-discuss's `decide.py detect` through `DECIDE_CLI = "ai-kit-gsd-spec-discuss/scripts/decide.py"`, and
  `gp_sections.py` tells agents to "use the decide.py ladder of the ai-kit-gsd-spec-discuss skill".
  `tools/hooks/precompact_core.py` (`find_client`) and `tools/hooks/claude_decision_probe.py` run `jev_review.py`
  from the checkout path. spec-discuss's SKILL.md and `references/decision-table.md` carry backend names (Laya,
  TypeSafe, OpenCode Zen), consent steps and probe statuses.
- **Install shape.** `~/.claude/skills/<skill>` and `~/.pi/agent/skills/jev-fast-decision` are symlinks into the
  main checkout. `skills/_shared/` works only for symlink installs (`ai-kit-project-rules-all` SKILL.md), so it
  cannot be the jev home (DIST-03: a copy install never breaks).
- **Phase split.** The owner's answers (superpowers plans now, gh-stack and plain `gh`, a merge chain) made the
  phase too large; on 2026-11-03 the remote half (stacked branches, pushes, PRs, merge chain, config, ship rule)
  moved to the new Phase 29.1. FLOW-01 was amended the same day: commits already pushed to an unmerged phase or plan
  branch may be folded again (pushed with `--force-with-lease` by 29.1); main and merged branches never are.
  gh-stack 0.3.0, probed for 29.1, pushes every stack branch with `--force-with-lease --atomic` and cascade-rebases
  upper branches, which the amended rule allows.

## Requirements

1. **One written folding policy**: The folding rules exist once, as one policy text that the folding step implements and that later playbooks can carry in full.
   - Current: the rule is one AGENTS.md sentence plus session memory; no policy text, no implementation.
   - Target: one policy text states: one commit per logical feature (a plan with two features gives two commits), never one squash per plan or phase; each folded commit carries its code with its tests and docs; the folded tip's tree equals the tested tree before the branch moves; the old tip gets a local backup tag before the branch moves, deleted when that unit's PR merges; no `reset --hard`; commits reachable from main or from a branch whose PR has merged are never rewritten; a rewritten pushed branch is pushed only with `--force-with-lease`; pushes go to the primary remote only.
   - Acceptance: a doc-contract test finds each of those rules in the policy text and fails when one is removed; the folding step's instructions point to the policy instead of restating it.
   - Scope: general.

2. **Fold a finished GSD plan**: At the end of a finished GSD plan the plan's commits are replaced by one commit per logical feature.
   - Current: a plan ends as one commit per task plus one docs commit.
   - Target: the folding step takes the plan's commit range (from the commit before the plan's first commit to the plan's tip) and writes one commit per logical feature, each with a message that names the feature and the plan.
   - Acceptance: a fixture GSD plan whose task commits build two features ends as exactly two commits; every changed path of the original range appears in exactly one folded commit, except a path that two features both change.
   - *Amended 2026-11-03 (29.1 spec):* the GSD plan reaches the fold as a checkpoint supplied by the GSD adapter of the unit contract (29.1 R1, FLOW-10); the fold engine itself names no framework.
   - Scope: general.

3. **Fold a finished superpowers plan**: At the end of a finished superpowers plan its commits are folded by the same step and the same policy.
   - Current: no end-of-plan step exists on the superpowers side.
   - Target: a finished superpowers plan's branch is folded the same way before superpowers' finishing step offers to merge or push it.
   - Acceptance: a fixture superpowers plan branch with commits for two features ends as exactly two commits under the same policy checks as a GSD plan.
   - *Amended 2026-11-03 (29.1 spec):* the superpowers plan reaches the fold as the single checkpoint of its unit, supplied by the superpowers adapter (29.1 R1); after the fold the unit flow pushes and opens the stacked draft PR, and superpowers' own merge and PR options are not used for a unit (29.1 R1, R4).
   - Scope: general.

4. **Tree proof and backup before the swap**: The branch moves to the folded tip only after the folded tip's tree is proven identical to the tested tree and the old tip is tagged.
   - Current: nothing checks a fold.
   - Target: the step compares the folded tip's tree id with the tested tip's tree id, creates a local backup tag on the old tip, and only then moves the branch ref to the folded tip, without `reset --hard`.
   - Acceptance: a fixture whose fold changes one byte is refused, with the branch and working tree unchanged and no tag left behind; a good fold leaves the backup tag on the old tip and the branch on a tip with the same tree; a structural test fails when the step's code or instructions contain `reset --hard`.
   - Scope: general.

5. **Never rewrite main or merged work**: The step refuses to rewrite any commit reachable from main or from a branch whose PR has merged, and folds only the current unit's own commits.
   - Current: no guard exists.
   - Target: before folding, the step checks that no commit in the range is reachable from main (or the project's base branch) or from a known merged unit branch; on a hit it stops with a named reason and changes nothing. Commits already pushed to the current unmerged branch may be folded again (FLOW-01 amended).
   - Acceptance: a fixture where the range includes a commit already on main is refused with the branch unchanged; a fixture where the range was pushed to an unmerged branch folds normally.
   - *Amended 2026-11-03 (29 D-05):* live fact — GSD's default worktree mode merges each plan back with `git merge --no-ff`, so a worktree-mode plan's range holds that merge commit; it is folded as part of the plan, and only a foreign merge commit refuses.
   - Scope: general.

6. **A five-line subagent report**: The folding runs in a subagent and reports in five lines or fewer.
   - Current: no folding subagent exists.
   - Target: the step dispatches the fold to a subagent where the host has one; the report states the unit, the commit count before and after, the tree check result, the backup tag and the outcome, in five lines or fewer. On a host without subagents it runs inline and says so in the report.
   - Acceptance: a test of the report renderer shows five lines or fewer for success and for every refusal reason; the step's instructions dispatch a subagent and name the inline fallback.
   - Scope: general.

7. **Grouping proposed by jev, decided by the agent**: The feature grouping is proposed through jev when available and decided by the agent's rule-based grouping otherwise.
   - Current: nothing proposes a grouping.
   - Target: the step asks `jev-fast-decision` (through its documented entry point) to classify the plan's commits into features; a `needs_fallback`, an error, no backend or no installed skill means the rule-based grouping decides (from the plan's declared tasks and features, commit scopes and touched paths). jev's answer is advisory; the agent's decision is logged with its source.
   - Acceptance: the two-feature fixtures fold into the same two commits with jev absent (no skill installed), with no backend reachable, and with a faked jev answer; a faked jev answer that would mix a code change with another feature's tests is overridden by the rule-based check.
   - Scope: general.

8. **The ladder lives in jev-fast-decision**: The jev ladder caller is owned by the `jev-fast-decision` skill and reached through one documented command-line entry point.
   - Current: the ladder caller is spec-discuss's `decide.py`.
   - Target: `jev-fast-decision` ships the ladder (validation, scrubbed environment, column mapping, detect, second opinion, consent delegation) behind one entry point its SKILL.md documents; spec-discuss ships no ladder code; the ladder's tests move with it.
   - Acceptance: spec-discuss's scripts folder holds no ladder or client-lookup code; jev's tests cover every behaviour today's `decide.py` tests cover; the documented entry point answers a `ladder` run and a `detect` run in a scratch HOME.
   - Scope: general.

9. **Every caller chains jev as a black box**: spec-discuss, the folding step, goal-prompt, the precompact hook and the decision-probe hook reach jev only by chaining the installed skill, and each still finishes when the skill or every backend is missing.
   - Current: goal-prompt runs spec-discuss's `decide.py`; the hooks run `jev_review.py` from the checkout path.
   - Target: agent callers ask `jev-fast-decision` and follow its SKILL.md; code callers run the documented entry point found through the installed-skill lookup; no caller imports another skill's code or opens another skill's files; a missing skill, an older skill without the entry point, or bad output means no backend and the rule-based default decides.
   - Acceptance: with `jev-fast-decision` absent from every skills dir, each of the five callers completes with its rule-based default; a structural test fails when a skill or hook imports from another skill's folder or names a path inside another skill's folder other than through the lookup, with a non-vacuity case for each form.
   - Scope: general.

10. **Caller text treats jev as a black box**: The SKILL.md and references of every caller say only to ask `jev-fast-decision` and follow its SKILL.md, and that `needs_fallback` or no answer means the rule-based default decides.
    - Current: spec-discuss's SKILL.md and `references/decision-table.md` name backends, consent steps and probe statuses; goal-prompt's generated text names spec-discuss's `decide.py`.
    - Target: backend names, consent steps and probe statuses appear only in `jev-fast-decision`'s own files; callers' texts carry the one black-box instruction; the consent ask moves into jev's own flow.
    - Acceptance: a text test over every caller's SKILL.md, references and generated prompt text fails on a backend name, a consent step or a probe status, with a non-vacuity case; every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04).
    - Scope: general.

## Boundaries

**In scope:**
- The one folding policy text and its doc-contract test.
- The reusable folding step for a finished GSD plan and a finished superpowers plan: range, grouping, fold, tree
  proof, backup tag, the main-and-merged guard, the five-line subagent report.
- Moving the ladder caller into `jev-fast-decision` with one documented entry point and its tests.
- Rewiring spec-discuss, goal-prompt, the precompact hook and the decision-probe hook to chain jev as a black box,
  with the structural and text tests.
- The judge bar (JDG-04) for every SKILL.md this phase adds or materially changes (at least `jev-fast-decision`,
  `ai-kit-gsd-spec-discuss`, and the folding step's skill if it is one; `ai-kit-spec-goal-prompt` and
  `ai-kit-spec-execute-superpowers` if their SKILL.md changes materially).
- Amending FLOW-01 and RULE-17, splitting Phase 29.1 out in the roadmap, and recording the Phase 49 coupling.

**Out of scope:**
- Stacked phase or plan branches, pushing, PRs, gh-stack or plain-`gh` chaining, the merge chain, deleting backup
  tags on merge, MVP main-only merging, one-time push consent, `git.*` config, the health-check archive and the
  AGENTS.md ship rule — Phase 29.1.
- The end-of-task, plan and phase playbook that carries the policy in generated rules — Phase 47 (RULE-17,
  amended to carry the policy in full).
- Whether the advisory hook reminds of the policy at commit or push time — Phase 49's discuss (coupling recorded).
- jev's backend choice per host, calibration and the on/off knob — Phase 34 (JEV-01, JEV-03, JEV-07).
- Removing OpenCode Zen from `jev-fast-decision` — Phase 32.1 (JEV-02); the moved ladder keeps today's table.
- Executor or reviewer choice through jev — EXE-03 and the review-sizing work.
- The GitLab mirror — the primary remote only.

## Constraints

- Runtime scripts stay stdlib-only under system python3; `git` is the only outside tool the folding step needs.
- No `reset --hard`, `git clean -f`, `checkout .` or `restore .`; the branch moves only after the tree proof.
- No test calls a real host CLI or reads the repo's `.planning/` (Phase 28 R4, R9); fixture repos live in
  temporary directories with synthetic commits.
- jev answers are advisory; no jev answer gates a fold.
- Never send code, diffs, file contents or secrets to jev: the grouping item carries commit subjects, path names
  and task summaries only.
- Plain-copy installs must keep working (DIST-03): no shared code reached through `skills/_shared/`.
- No absolute machine path in source, tests or fixtures.

## Acceptance Criteria

- [ ] The doc-contract test finds every folding rule in the policy text and fails when one is removed.
- [ ] A two-feature GSD plan fixture folds into exactly two commits (a GSD fixture project, not ai-kit's repo).
- [ ] A two-feature superpowers plan fixture folds into exactly two commits under the same checks (a superpowers fixture project).
- [ ] A fold whose tree differs by one byte is refused with the branch, working tree and tags unchanged.
- [ ] A good fold leaves a local backup tag on the old tip and a branch tip with the same tree.
- [ ] A structural test fails on `reset --hard` in the folding step's code or instructions.
- [ ] A range that contains a commit already on main is refused with the branch unchanged.
- [ ] A range already pushed to an unmerged branch folds normally.
- [ ] The fold report is five lines or fewer for success and every refusal; the inline fallback says so.
- [ ] The two-feature fixtures fold the same way with jev absent, with no backend, and with a faked jev answer.
- [ ] A faked jev grouping that splits a change from its tests is overridden by the rule-based check.
- [ ] spec-discuss's scripts hold no ladder or client-lookup code; jev's tests cover every former `decide.py` behaviour.
- [ ] jev's documented entry point answers `ladder` and `detect` in a scratch HOME.
- [ ] With `jev-fast-decision` absent, spec-discuss, the folding step, goal-prompt and both hooks finish on their rule-based defaults.
- [ ] The cross-skill structural test passes on the tree and fails on each synthetic violation form.
- [ ] The black-box text test passes on every caller's text and fails on a synthetic backend name.
- [ ] Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04).

## Edge Coverage

**Coverage:** 33/35 applicable edges resolved · 2 unresolved (both `unclassified`, with added rows below)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | AGENTS.md Workflow's folding sentence points to the policy text instead of restating it, so the two cannot drift |
| empty | R1 | ✅ covered | When the policy text is missing the folding step refuses with a named reason instead of folding without rules |
| encoding | R1 | 🧪 backstop | The doc-contract test matches each rule by a stable phrase, not by Markdown layout (held-out edge test) |
| ordering | R1 | 🧪 backstop | Reordering the rules in the policy text keeps the doc-contract test green |
| adjacency | R2 | 🧪 backstop | A path changed by both features stays whole in one folded commit unless its hunks separate cleanly; the tree proof holds either way (split rule decided in discuss) |
| empty | R2 | ✅ covered | A plan with no code commits (only its docs commit, or nothing) is not rewritten: no tag, report "nothing to fold" |
| encoding | R2 | 🧪 backstop | Multi-line and non-ASCII commit messages and paths survive the fold byte for byte (UTF-8) |
| ordering | R2 | ✅ covered | Folded commits keep the order of each feature's first original commit, so a feature that builds on another comes after it |
| adjacency | R3 | ✅ covered | Commits on the superpowers branch from before the plan started are outside the range and stay untouched |
| empty | R3 | ✅ covered | A superpowers plan with a single commit stays one commit, with no rewrite and no tag |
| ordering | R3 | 🧪 backstop | The superpowers fold uses the same feature order rule as the GSD fold (shared fixture assertion) |
| unclassified | R4 | ⚠ UNRESOLVED | unclassified — review manually; concrete edges added in the next two rows |
| adjacency | R4 | ✅ covered | (added 2026-11-03) A dirty working tree or index refuses the fold before any commit is written |
| concurrency | R4 | 🧪 backstop | (added 2026-11-03) If the branch moves between the tree proof and the swap, the ref update names the expected old tip and fails, leaving the branch where it was |
| adjacency | R5 | ✅ covered | The range starts after the merge-base with main or the base branch; the merge-base commit itself is never in it |
| empty | R5 | ✅ covered | A repo where no main or base branch resolves refuses with a named reason and changes nothing |
| ordering | R5 | ✅ covered | ~~A merge commit inside the range refuses the fold with a named reason~~ *(superseded, D-05)* GSD's own worktree merge-back of the plan being folded (`git merge --no-ff`, "chore: merge executor worktree") is part of that plan's range and is folded away; any other merge commit inside the range refuses the fold with a named reason |
| boundary | R6 | ✅ covered | A five-line report passes and a six-line report fails the renderer test |
| adjacency | R6 | 🧪 backstop | A refusal line names the unit and the reason code side by side |
| empty | R6 | ✅ covered | A no-op fold ("nothing to fold") still emits a report |
| encoding | R6 | 🧪 backstop | The report is plain text with no terminal colour codes |
| ordering | R6 | 🧪 backstop | Report lines come in a fixed order: unit, counts, tree check, tag, outcome |
| precision | R6 | 🧪 backstop | Counts are exact integers and commit and tree ids are shown at a fixed short length |
| unclassified | R7 | ⚠ UNRESOLVED | unclassified — review manually; concrete edges added in the next two rows |
| empty | R7 | ✅ covered | (added 2026-11-03) A jev grouping that leaves out a commit of the range is rejected and the rule-based grouping decides |
| adjacency | R7 | 🧪 backstop | (added 2026-11-03) A jev grouping that puts one commit into two features is rejected and the rule-based grouping decides |
| adjacency | R8 | ✅ covered | A caller that finds an older `jev-fast-decision` without the entry point treats it as no backend and names the update command |
| empty | R8 | 🧪 backstop | An empty item list returns an empty result and exit 0 through the entry point |
| ordering | R8 | 🧪 backstop | Results stay keyed by item id in input order, as `decide.py` does today |
| adjacency | R9 | 🧪 backstop | With two installed copies in different skills dirs, the lookup picks the first in its documented order |
| empty | R9 | ✅ covered | With no skills dir at all, every caller gets "no backend" and finishes on its default |
| encoding | R9 | 🧪 backstop | Skills dirs whose path contains a space are found and run (held-out edge test) |
| ordering | R9 | 🧪 backstop | Every code caller uses the same lookup order; a drift test compares them |
| concurrency | R9 | 🧪 backstop | A hook and spec-discuss running the entry point at once share only the client's existing consent file and answer log, as today |
| adjacency | R10 | ✅ covered | Only `jev-fast-decision`'s own files may name backends, consent or probes; the text test exempts that folder alone |
| empty | R10 | ✅ covered | A caller text with no jev mention passes the text test |
| encoding | R10 | 🧪 backstop | Backend names are matched case-insensitively, including "OpenCode Zen" and "opencode zen" |
| ordering | R10 | 🧪 backstop | The text test's result does not depend on file order |
| concurrency | R10 | 🧪 backstop | The text test only reads files, so parallel test modules cannot interfere |

## Prohibitions (must-NOT)

**Coverage:** 3/3 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| The folding step MUST NOT move a branch to a tip whose tree differs from the tested tree | R4 | resolved | verification: test (one-byte-different fixture refused, branch unchanged) |
| The folding step MUST NOT rewrite a commit reachable from main or from a merged unit's branch | R5 | resolved | verification: test (range with a commit on main refused) |
| A jev grouping item MUST NOT carry code, diffs, file contents or secrets | R7 | resolved | verification: test (the item builder emits subjects, paths and task summaries only; the ladder's existing guard rejects fences and key shapes) |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                       |
|--------------------|-------|------|--------|-------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | two-feature fixtures, tree proof, black-box jev               |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | remote half split to 29.1; playbook 47; hook 49               |
| Constraint Clarity | 0.80  | 0.65 | ✓      | no reset --hard, main and merged never rewritten, copy installs |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | fixtures, structural and text tests, judge bar                |
| **Ambiguity**      | 0.15  | ≤0.20| ✓      | 1 − (0.315 + 0.2125 + 0.16 + 0.16)                            |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

Interactive, 3 rounds (each batch answered by the owner through the orchestrator). The decision ladder was not
used: in the interactive path it screens only items the owner asks to screen, and none were. Rule: `mvp-mode`
inactive, the best design wins over the smallest diff (DESIGN-01: simple is not easy, no half-done feature).

| Round | Perspective | Question summary | Decision locked |
|-------|-------------|------------------|-----------------|
| 1 | Researcher | Who the flow serves | GSD and superpowers plans both, now; any project (R2, R3) |
| 1 | Researcher | How PRs are chained | gh-stack when installed, plain `gh --base` with own retargeting otherwise (Phase 29.1) |
| 1 | Simplifier | Who merges the chain | An owner-started merge chain, bottom-up, never squash, fast-forward local main (Phase 29.1) |
| 1 | Simplifier | Where the jev ladder lives | Every caller chains the existing `jev-fast-decision` skill as a black box and works without it; the ladder is owned by that skill (R8, R9) |
| 2 | Boundary Keeper | Work after the last plan | Commits can be folded again and pushed with `--force-with-lease`; FLOW-01 amended (R1, R5) |
| 2 | Boundary Keeper | The degraded health check | Archive `INGEST-CONFLICTS.md` and keep the check clean (Phase 29.1) |
| 2 | Boundary Keeper | How long push consent lasts | Per project, in the personal gitignored ai-kit settings, until revoked (Phase 29.1) |
| 2 | Boundary Keeper | MVP on a main-only project | Still a phase branch, fast-forwarded into main and pushed after each plan, no PR (Phase 29.1) |
| 2 | Failure Analyst | Backup tags | Local only, deleted when the unit's PR merges (R1, R4; deletion in 29.1) |
| 3 | Seed Closer | Phase size | Split: 29 local (folding step, jev ladder), 29.1 remote (branches, pushes, PRs, merge chain) |
| 3 | Seed Closer | Superpowers stack unit | Each superpowers plan is a unit with its own stacked branch and PR (R3; branch and PR in 29.1) |
| 3 | Seed Closer | jev for script callers | The documented entry point through the installed-skill lookup; missing or bad output means no backend (R9) |
| 3 | Failure Analyst | Force-push bound | Only unmerged phase or plan branches, always `--force-with-lease`; never main or merged branches (R1, R5) |
| 3 | Boundary Keeper | Remote | Primary remote only (GitHub `origin`); the GitLab mirror is out of scope (R1) |
| 3 | Owner addition | Folding rules beyond ai-kit | Written once as a policy (R1); RULE-17 amended so Phase 47's playbook carries it in full; the advisory-hook reminder is a coupling for Phase 49 |
| after 3 | Owner clarification | Whose repo the requirements serve | Any GSD or superpowers project through ai-kit's skills; ai-kit is the first user; ai-kit-only items (FLOW-05, FLOW-07, both in 29.1) are dogfood with named general counterparts (CUR-04, RULE-17); one scope line per requirement (Scope section) |
| after 3 | Edge and prohibition probes | The engine's floor and the must-NOT pass | Resolved by the orchestrating agent; not shown to the owner row by row, open to change in discuss |
