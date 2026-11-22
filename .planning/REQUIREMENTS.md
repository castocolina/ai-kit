# Requirements: ai-kit

**Defined:** 2026-11-02
**Core Value:** ai-kit must never corrupt uz's AI-CLI configuration and must never claim more certainty than it
has: every config write is atomic and explicitly confirmed, every diagnostic is honestly labeled by its
confidence and sourcing, and every "this capability is active" claim is verified live.

Milestone v2.0 Skill Refactor. Source: `.planning/milestones/NEXT-MILESTONE-INPUTS.md` ("Decisions by skill",
rounds 1-9) and `.planning/research/2026-11-02-next-milestone/`. "The owner" is uz; "jev" is the
`jev-fast-decision` client, always advisory, and every skill that uses it still works without it.

## v2.0 Requirements

### Fast gates

- [x] **GATE-01**: A commit runs, in parallel, only the test modules that cover the staged files (mapped through
  imports and the runner's test lists) and is refused when one of them fails. *(amended 2026-11-03, 28 D-01: 81 of 95 test modules reach code through path strings, `sys.path` inserts or subprocesses, not imports; the mapper is a name index over tests and their helpers, which includes imports)* *(amended 2026-11-03, 28 plan check iteration 2; decided 2026-11-03 by the autonomous run's orchestrator under the run prompt's gray-area rule (jev ladder low-confidence, own reasoning); the owner reviews it in the run report and may revert: a covering e2e module whose recorded duration is over the 60 s commit budget, or unrecorded, is named in a notice and run by a pre-push hook for the pushed commits instead; `tests.test_cross_ai_runner_e2e` took 360.5 s on 2026-11-02)*
- [x] **GATE-02**: A push runs the full unit, arch and wizard suites in clearly less wall time than the 2.5 minutes
  measured on 2026-11-02, because no test calls a real host binary (fakes only). *(amended 2026-11-03, 28 SPEC R3: re-measured at 184 s (core 162.9 s, wizard 21.0 s, 24 CPUs); the target is 60 s or less for both test hooks)*
- [x] **GATE-03**: No test depends on the caller's environment: host signals, binaries on PATH, checkout path length,
  TMPDIR and whether the caller's directory is a git repository are pinned per test (this covers the goal-prompt
  test that depends on path length and the no-git e2e test that ran inside a repository), and a structural test fails when a test calls a real host CLI.
- [x] **GATE-04**: The runner's self-test budgets scale with host load, so a loaded or swapping machine does not fail
  them; real run limits are unchanged.
- [x] **GATE-05**: No test reads a path under `.planning/`: test data lives under `tests/`, and a structural test
  fails when a test module opens or globs a `.planning/` path.

### Commit, push and phase flow

- [x] **FLOW-01**: At the end of each plan the work is folded into logical-feature commits (a plan with two features
  gives two commits, never one squash per phase); jev proposes the grouping, the agent decides when jev is absent,
  and nothing already pushed is rewritten *(amended 2026-11-03, 29 spec: owner rule — commits already pushed to a phase or plan
  branch whose PR has not merged may be folded again and pushed with `--force-with-lease`; main and any branch
  whose PR has merged are never rewritten; the folding rules are written once as a policy the folding step
  implements and the RULE-17 playbook carries)*. The folding runs in a subagent that reports in five lines or fewer,
  checks that the folded tip's tree equals the tested tree before the swap, tags the old tip before replacing it,
  and never uses `reset --hard`.
- [x] **FLOW-02**: Each phase runs on its own branch stacked on the previous phase's branch, with one PR per phase
  opened against the previous one (chained PRs), and each finished plan is pushed to its phase branch.
  *(amended 2026-11-03, 29.1 spec: the stack is one per repository and made of framework-neutral units (FLOW-10): a GSD phase or a
  superpowers plan is a unit, each finished plan a checkpoint that is pushed; a unit's PR opens as a draft at its
  first push and turns ready when the unit finishes and verification passes; gh-stack when installed, plain `gh`
  otherwise; an owner-started merge chain merges ready PRs bottom-up with merge commits; hotfixes stay outside
  the stack, FLOW-11)*
- [x] **FLOW-03**: In MVP mode on a main-only project, the same point merges into main without review.
  *(amended 2026-11-03, 29.1 spec: still a unit branch, fast-forwarded into its target and pushed after each checkpoint with no PR, only
  when nothing unmerged sits below the unit; otherwise the flow refuses with a named reason and stays on the PR
  path)*
- [x] **FLOW-04**: At every phase boundary, on the current branch, the codegraph (replaced by codebase-memory-mcp in Phase 32.5) index is synced, the graphify
  graph is rebuilt, and the next phase's brief lists the new or changed symbols to hook into and the documents
  that mention them, so its researcher, planner and executor know what to attach to and which docs to update;
  none of this depends on commits to main.
  *(amended 2026-11-03, 30 spec: the step runs for every unit inside the unit-flow engine, at the unit's start, before its planning and before its first execution wave, on the unit's own branch; codegraph (replaced by codebase-memory-mcp in Phase 32.5) and graphify are created or refreshed automatically whenever their CLI is installed; the brief also lists removed symbols and searches tracked documents outside `.planning/`)*
- [x] **FLOW-05**: ai-kit's own GSD config is set for this flow (branch per phase, the boundary step above) through
  the project's `gsd-tools`.
- [x] **FLOW-06**: ai-kit's own AGENTS.md, the current house rules and the tool-advisor hook's advice (the generated
  rules block carries the same rule once RULE-03 builds it)
  tell agents to explore code with codegraph (replaced by codebase-memory-mcp in Phase 32.5) when it is indexed, and keep graphify for GSD's discovery of documents and planning next to code (verified 2026-11-02: codegraph indexes no Markdown; graphify does, but
  with no document-to-code links and keyword-noisy hits). A runbook says how to build the graphify index
  (archived milestones excluded), when to refresh it (every phase boundary, plus GSD's auto-update after commits)
  and how.
  *(amended 2026-11-03, 30 spec: the rule also says to index and sync automatically whenever the CLI is present, to search Markdown with rg, that on stacked branches GSD's auto-update never fires so the indexes go stale unless refreshed, and to refresh before GSD research; ai-kit also indexes every new worktree)*
  *(amended 2026-11-03, owner: the tool-use rule also says the shell's working directory persists between
  calls, so never prefix a command with `cd` into the project folder; use absolute paths, and put anything
  longer than a couple of steps into a script under `tmp/` and run it. The generated counterpart in Phase
  45.1 carries the same text.)*
- [x] **FLOW-07**: Shipping a finished phase: its gates pass on the phase branch, an installer dry run and the new
  hooks run against a scratch HOME, then the work is installed on this machine and re-checked live from the tip of
  the phase branch; local main moves only when the stacked PRs merge. AGENTS.md's Workflow section states this rule
  (it replaces the owner's earlier "merge every phase into local main" rule), ai-kit's GSD config (FLOW-05) matches
  it, and a doc-contract test pins the steps.
- [x] **FLOW-08**: In auto mode, spec-discuss ends by preparing the autonomous-run prompt for the discussed range
  through `ai-kit-spec-goal-prompt`, which stops only on a blocker; when goal-prompt is not installed it says so and
  stops. A doc-contract test pins both paths.
- [x] **FLOW-09**: goal-prompt's rails tell an autonomous run to ask the owner only for a locked-decision ambiguity,
  a package or security gate, or a call only human eyes can make (otherwise it verifies, decides and reports); never
  to end a turn with a waiting message while independent work remains; and to give the local time, the running step
  and when it started in every progress or resume ping. A doc-contract test pins each rail, and the generated prompt
  stays within its length caps.
- [x] **FLOW-10**: The branch, push, PR and merge-chain flow is ai-kit's own and framework-neutral: it knows only
  units, checkpoints and target branches through one documented unit contract, and each spec-driven system reaches
  it through a thin adapter (GSD and superpowers now; grill-me, spec-kit or others later); a synthetic third
  adapter drives the whole flow in a fixture with no change to the flow's code. *(added 2026-11-03, 29.1 spec)*
- [x] **FLOW-11**: A hotfix unit branches off a configurable target branch (the base branch by default; a sandbox
  or staging branch when configured), gets its own PR or MVP fast path to that target and is never stacked; once
  it merges into the trunk of an open stack, the unmerged stack is rebased onto the updated trunk and pushed with
  `--force-with-lease`, and a conflict restores every branch and stops. *(added 2026-11-03, 29.1 spec)*
  *(amended 2026-11-03, 29.1 D-07: a conflict is first resolved by an agent keeping both sides' intent, GSD's planning files merged by content, and the gates run on the result; every branch is restored and the flow stops only when the resolution or the gates fail; the report names every resolved file and how)*
- [x] **FLOW-12**: ai-kit's setup (`tools/setup.py`, headless and in the wizard) finds codegraph's (replaced by codebase-memory-mcp in Phase 32.5) installer block (`<!-- CODEGRAPH_START -->` … `<!-- CODEGRAPH_END -->`) in every global instruction file codegraph's installer writes (Claude, Codex, Gemini, opencode) and replaces only its "skip CodeGraph entirely — indexing is the user's decision" sentence with ai-kit's rule (create the index with `codegraph init -y` when the CLI is installed and there is none; `codegraph sync` first when `codegraph status --json` shows pending changes): a backup first, an
  atomic write, every other byte untouched, no diff on a second run, a dry run that shows the change, a one-line
  note when the file, block or sentence is missing; the config doctor reports the installer's wording when it is
  back and install re-applies ai-kit's; tests use synthetic files in a scratch HOME only. The marked-block editor is
  shared with JEV-04. *(added 2026-11-03, 30 spec)*
- [x] **FLOW-13**: ai-kit's `make setup-dev` runs `setup-env`, installs the pre-commit hooks including the
  `post-checkout` stage, and installs each missing flow tool (the codegraph (replaced by codebase-memory-mcp in Phase 32.5) and graphify CLIs, pre-commit, gh, the
  gh-stack extension) through a guarded step: an installed tool is left alone, a tool that cannot install is
  reported by name with its manual command, the target still succeeds and the flow degrades without that tool;
  `dev` and `setup-env` keep working until RULE-05 settles the aliases. *(added 2026-11-03, 30 D-04)*
- [ ] **FLOW-14**: `ai-kit-spec-goal-prompt` learns from the current and the previous session and from the rails applied
  in them, and proposes good rails for the next prompt, keeping only what the project's AGENTS.md rules and its generated
  block do not already say. Its sources are the installed `lesson-learned` skill, chained as an optional black box over
  the session's commit range and the previous one (it grounds a lesson in git commits, a branch diff or staged changes,
  never in a session transcript), the rails files the runs used, and optionally the redacted transcript and log search step
  of Phase 47.1 for owner corrections, stops and quota cuts that never reach a commit (whether that source is on by default
  needs owner confirmation). Each candidate appears inside the generated prompt's rails section labeled "learned" with
  its source, within the prompt's existing length caps, and is never written into AGENTS.md by this skill; without
  `lesson-learned`, or without Phase 47.1's step, the skill behaves as it does today for that source, and a test covers each
  absent path. *(added 2026-11-16, owner decision; Phase 47.2)*

### Removals

- [x] **RMV-01**: `ai-kit-spec-execute-gsd` is gone with its tests, test-list entries, README and doc mentions; the
  execute router hands GSD plans back to `/gsd-execute-phase`, and the installer removes the stale installed link.
  The code only it used goes too: the runner guidance prepend (`project_runner_command(guidance=True)`,
  `PROJECT_GUIDANCE_PATH`), the `cross-ai-guidance.md` file curated-config still writes, and
  `gsd_tools.prior_value`.
- [x] **RMV-02**: `ai-kit-opencode-providers` is gone; its stale-provider scan lives on in spec-config.
- [x] **RMV-03**: `mermaid-audit` is gone with every reference.
- [x] **RMV-04**: rtk appears in no tool list, guidance text, house rule (today one house rule recommends it),
  AGENTS.md section (today Tools and Stack mentions it), config-doctor advice or usage-metrics source; a test fails
  on an rtk mention outside history files. *(amended 2026-11-03, 31 spec: the ban covers recommending, installing or
  wiring rtk; usage-metrics keeps reading rtk data that already exists, as optional input, and nothing deletes
  stored data; the test's named exemptions are `.planning/`, `docs/prds/`, `docs/superpowers/`, the test itself and
  usage-metrics' rtk reader with its test; house rule R05 is retired with its id left unused)*

### Skill quality and judging

- [x] **JDG-01**: A re-judge report scores every kept skill with the current judge (two judges chosen from what the
  environment offers, native opus at xhigh as fallback); old /120 scores appear only as history. The judge prompt
  embeds the rubric and the spec sources it cites, and states one reading of ai-kit's flat `tests/test_*.py` layout
  and of skills without a `scripts/` folder that holds for every skill. *(amended 2026-11-07, owner decision: the
  kept skills are the 16 non-rules skills; 15 are judged, and `ai-kit-commit-fold` is listed as excluded beside the
  seven project-rules skills because it is temporary and RULE-27 absorbs it into `ai-kit-project-rules`. Where tests
  live (flat `tests/test_*.py` or `tests/skills/<name>/`, as the skill-judge rubric expects) is decided in the phase
  32 spec after a spike that measures the cost of moving them (parallel runner, gate-scope test, staged mapper,
  recorded e2e times); the judge prompt states the chosen layout. Evals stay in each skill's `evals/` folder, as the
  Agent Skills standard says, and DIST-01 trims them from the shipped copy)* *(amended 2026-11-07, 32 spec: the
  spike chose the flat layout; the judge prompt lists each skill's test modules by one rule, and a skill that ships
  runnable code is judged with the 5/5/5 split on them, one with no runnable code with the 8/7 split)*
- [x] **JDG-02**: The verdict checker is a tracked tool that takes the skill and judge lists as arguments and names
  no referee, resolves the repository root itself (the same digest when run from a sub-folder, proven by a test) and
  reports how many judge rounds ran.
- [x] **JDG-03**: Every kept skill has `evals/evals.json`, trigger queries (about 20, half near-misses) and tests,
  written in the batch phase that improves it; the closing re-judge report shows them for every kept skill.
  *(amended 2026-11-07, owner decision: the report covers the 15 judged skills; `ai-kit-commit-fold` is excluded as
  in JDG-01)* *(amended 2026-11-07, 32.1 D-01, owner batch scope "Narrow": evals, trigger queries and tests are
  written in the phase that brings a skill to the bar or, for a skill already at the bar, in the phase that next
  materially changes its SKILL.md (JDG-04): batches 32.1-32.4 for the five below-bar skills no later phase touches,
  Phases 37-38 for `ai-kit-cross-ai`, Phases 39-40 for `ai-kit-spec-review`, and that next phase for
  `ai-kit-session-wake`; the 32.4 closing report shows every judged skill's evals, trigger-query and test state and
  names the phase for each one still missing; the requirement completes when every kept skill has them)*
- [ ] **JDG-04**: Every phase of this milestone that adds or materially changes a SKILL.md (the batch phases and
  every other phase that touches a skill, including the new `ai-kit-project-rules` skill) leaves each such skill
  with new-shape evals and tests, no critical or high finding or grade B or better, and no regression beyond judge
  variation, recorded in that phase's verification before it closes; each such phase carries a success criterion
  that cites this requirement.
  *(2026-11-07, Phase 32 close-out: Phase 32's part is done (the bar is recorded per judged skill in `.planning/judge/REJUDGE.md`, 8 met and 7 not met, and check-dogfood guards the citations); the requirement stays open until every skill-changing phase meets it)*
  *(amended 2026-11-07, 32.1 D-01, owner batch scope "Narrow": the batch phases 32.1-32.4 bring to the bar only the
  below-bar skills no later phase touches (`cst-refactor`, `markdown-to-pdf`, `ai-kit-spec-review-fixer`,
  `ai-kit-usage-metrics`, `ai-kit-spec-review-checklist`); a below-bar skill a later phase modifies reaches the bar in
  that phase (`ai-kit-cross-ai` in Phases 37-38, `ai-kit-spec-review` in Phases 39-40); a skill already at the bar that
  a phase changes only for the fixes its requirements name keeps the bar with no regression beyond judge variation;
  each phase re-judges only the skills whose SKILL.md it adds or materially changes, and never judges a skill a later
  phase removes or replaces)*
- [x] **JDG-05**: Skill text carries behaviour, not history: no tool versions, dates or observation logs in the main
  flow, provenance in a trailing evidence section, no hardcoded referee names, and no shipped text pointing into a
  planning folder; ai-kit's AGENTS.md states the rule in one line (SKILL.md describes behaviour; provenance and
  version history live in a trailing section or a reference; version-specific text appears only as a conditional).
- [x] **JDG-06**: The number of judges per round (one or two) comes from deterministic signals plus jev's score, with
  a floor of one (two when the last verdict sits within judge noise of a grade boundary or had a high finding).
  *(amended 2026-11-07, 32 spec, confirmed by the owner 2026-11-07: "a grade boundary" is read as the bar's pass boundary at
  80 percent and judge noise as the recorded 7 points, so two judges run from 73.0 to 87.0 inclusive, and a skill
  with no rubric-v4 verdict also gets two; with 10-point grade bands every percent from 53 to 97 lies within 7
  points of some band edge, so the literal reading would never leave room for one judge or for jev's score)*
- [x] **JDG-07**: Every SKILL.md passes a strict frontmatter check (strict YAML, 1,024-character description cap) that
  matches what `npx skills` accepts.
- [x] **JDG-08**: AGENTS.md's skill-judge rule caps a judge loop at a stated number of rounds and requires a
  disputed finding to be refuted by running the code, not by judging again; the verdict checker flags a loop that
  runs past the cap.
  *(amended 2026-11-16, owner: a round that leaves 3 or fewer critical, important or high findings across the
  skill's judges is fixed in the skill's own files without another judge round; the fix commit is recorded beside
  the round's record and the digest stays stale until the next loop; more than 3 keeps the round cap)*

### One config design

- [x] **CFG-01**: A recorded decision, backed by an inventory of every setting ai-kit keeps (reviewers and executors
  with the trust file, hooks, project rules, status line, jev consent, secrets, runner retry), chooses between one
  file with a section per area and one file per concern, under neutral names, project layer over user layer.
  *(amended 2026-11-14, owner decision, 33 D-01/D-02: chosen — one neutral `config.toml` per layer, project
  `.aikit/config.toml` over user `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml`, one table per concern;
  machine-written state stays in its own files with the reason recorded)*
- [x] **CFG-02**: `review-spec.toml` is replaced by the chosen config with automatic migration from the old name, and
  every caller reads the new one. *(amended 2026-11-14, 33 D-03/D-12: the roster becomes `[[lanes.review]]` in
  `config.toml`)*
- [x] **CFG-03**: The runner's retry settings live in ai-kit's config, not GSD's `config.json`; the runner migrates a
  `workflow.cross_ai_retry` block once. *(amended 2026-11-14, owner decision, 33 D-13: the settings live in
  `config.toml` `[runner.retry]`; the GSD block and the user `cross-ai.json` are migrated out once and removed)*
- [x] **CFG-04**: Every config write stays atomic and lossless (comments, formatting and unrelated entries kept).
- [x] **CFG-05**: `config.toml` entries are structured by concern and role: `[models]`, `[lanes]` with
  `[[lanes.review]]` and `[[lanes.execute]]` (the coding role), `[runner]`/`[runner.retry]`, `[jev]`, `[hooks]`; no
  table or file is named after one skill or host; the reader keeps unknown tables. *(added 2026-11-14, owner
  decision: the old config labelled everything "reviews")*
- [x] **CFG-06**: ai-kit never writes a key outside another tool's own schema into that tool's config (GSD,
  Claude Code, opencode, Codex, Cursor, pi, Copilot), and every ai-kit skill CLI and the runner work in a
  repository without `.planning/`. *(added 2026-11-14, owner decision: `workflow.cross_ai_retry` was never requested
  and third-party schemas can drop unknown keys)*

### spec-config as the hub

- [x] **HUB-01**: An `ai-kit-spec-*` skill that starts with no config chains spec-config; a missing spec-config
  fails with a message naming the fix; `--no-cross-ai` still runs on the session model with no config.
- [x] **HUB-02**: spec-config discovers providers and models on claude, opencode, pi, cursor, codex and copilot, and
  records per model where it was listed from and a separate usability state (verified with date, rejected with the
  error, or unverified, shown visibly). *(amended 2026-11-14, owner decision: running spec-config builds the
  catalog of every model the machine can reach before any role is proposed)*
- [x] **HUB-03**: The model catalog merges models.dev, Artificial Analysis and the Arena leaderboard into tier (four
  or more, effort-aware), class, relative cost, modalities and strengths, each value labeled measured or judged,
  with cache times; it shows each source's required attribution, never commits or ships Artificial Analysis data
  (its free tier forbids redistribution), and takes Arena data from the official dataset under its CC-BY-4.0 terms.
  Each model also carries its context window size when a source states it, labeled measured or judged; an unknown
  size stays visibly unknown. *(amended 2026-11-16, GSD lane-handling study: Phase 39's prompt-size check reads it)*
  *(amended 2026-11-14, owner decision: models.dev and Artificial Analysis are the primary sources and the LM Arena
  leaderboard the alternative when Artificial Analysis is unavailable; the merged classification feeds HUB-07)*
  *(amended 2026-11-16, 35 D-03 and D-09, owner decisions: Arena is merged whenever enabled in `[models]`, because
  Artificial Analysis needs a key and some of its properties can be incomplete, so the sources complement each other;
  the context window is kept per (runtime, model) with its source label, since one model has different windows on
  different runtimes, and Phase 39's prompt-size check reads the runtime's value)*
- [x] **HUB-04**: The cheap-execution ranking still yields candidates although Artificial Analysis returns its coding
  and agentic indexes as null.
- [x] **HUB-05**: The config separates reviewers from executors, each with priorities, effort per model and opt-in
  runtime and model escalation flags (off by default); an effort is passed only when the model supports it (detected
  per model), in the runtime's own form, and is never dropped silently (today only codex receives it).
  *(amended 2026-11-14, 33 D-03: reviewers are `[[lanes.review]]` and executors `[[lanes.execute]]` in
  `config.toml`; a lane is never reused across roles)* *(amended 2026-11-16, 36 D-04 to D-06: each role's priority is
  `[lanes.policy.review]` or `[lanes.policy.execute]` `ladder`; the effort forms for codex, pi, cursor and opencode land in
  Phase 36, and claude's and copilot's land with the runner in Phase 37; escalation flags are two flat booleans on a lane,
  informational until Phases 37, 40 and 41 read them)* *(amended 2026-11-16, 36 D-15, D-16: a lane may also carry
  `usage_limited` (the owner's yes for a free model with a daily or other cap, written only when true) with a display-only
  note; the fallback is the first unflagged lane in the role's order, read through one function; informational until Phase 40
  reads it)* *(amended 2026-11-16, free-lane pool study, 36 D-20 to D-22, PROVISIONAL, needs owner confirmation: a flagged lane
  also records its pool (provider plus tier, for example the one pool that the free models of a provider appear to share), the
  fallback is the first lane of the role that is neither flagged nor in the same pool, and the wizard warns that other free
  models of the same provider share the pool; source `.planning/research/2026-11-16-opencode-free-models.md`)*
- [x] **HUB-06**: spec-config flags stale entries (removed models, providers no longer configured).
- [x] **HUB-07**: jev ranks candidates and the user picks; by default the ranking proposes flagship-class models for
  review and coding-class models for execution; no skill, rail or default hardcodes a referee name.
  *(amended 2026-11-14, owner decision: from the classified catalog, spec-config proposes a coding set and a
  review set separately and the user confirms each before anything is written; nothing is labelled review by
  default)* *(amended 2026-11-16, 36 D-18: the proposal also shows a separate group of zero-price models, ordered by the same
  scores and labelled with the price source, so the owner can select a free model; a zero price never marks a lane
  usage-limited, only the owner does)*
- [x] **HUB-08**: The opencode CLI profile and the runner's comments match the installed opencode as its own
  `--help` reports it (current providers, the effort levels the model API lists, the `opencode models` flags), and a
  test fails when the profile names a flag the recorded help text lacks.
- [x] **HUB-09**: Only `router-env/<x>` model names may be hardcoded in code, defaults, rails, skills, docs and tests as
  expected values, and in tests only for pi and opencode; every other provider or model name comes from live
  discovery, the catalog or the user's config. A test fails on a new violation, with a committed baseline of today's
  violating files that can only shrink (a baseline file that no longer violates also fails); a runtime table is seed
  data and examples only, each marked, and never decides. *(added 2026-11-16, owner rule; 35 D-16 to D-18: the guard
  is position-based, tests for the bare-id hosts use invented structure-only placeholders (needs owner confirmation),
  and Phase 36's hardcoded-referee test is the same guard family)*
- [x] **HUB-10**: When the owner selects a free (zero-price) model that is not known to be local, spec-config shows the model's
  data-use note before anything else about the lane: `zero_retention`, `may_be_kept_or_trained` or `unknown`, with a display
  line, its source, the date it was read and a label (`verified` only for the vendor's own documentation page read in that run,
  else `reported`); an unreadable or silent source shows `unknown` and never defaults to a safe value, and no shipped list decides.
  It states that a review or execute lane sends project content to that vendor and asks the owner to confirm; a yes records the
  note and the confirmation beside the lane, a no or a skip writes no lane. *(added 2026-11-16, owner directive, free-lane pool
  study, 36 D-23, PROVISIONAL, needs owner confirmation: the decline path and the closed value list; only four of the free models
  on the vendor's page are listed as zero-retention, so project code may reach a third party; source
  `.planning/research/2026-11-16-opencode-free-models.md`)*

### Review

- [ ] **REV-01**: When a review lane fails mid-review, spec-review switches to the next lane in the user's preference
  order instead of ending the review. *(amended 2026-11-16, 36 D-16: a lane the owner flagged `usage_limited` switches at
  once to the first unflagged lane of its role, read through one function; an unflagged lane never switches on its own)* *(amended 2026-11-16, free-lane pool study, 38.1 D-23 to D-27 and 36 D-20 to D-22,
  PROVISIONAL, needs owner confirmation: selection skips a lane whose pool's blocked-until time has not passed, the fallback is
  a lane of a different pool, and the first selection after the time tries the lane once)*
- [ ] **REV-02**: jev classifies reviewer-fixer disagreements and gray areas before the user is asked.
- [ ] **REV-03**: Lens skills present in the environment (the ponytail family, reducing-entropy, naming-analyzer,
  simplify, impeccable for UI) reach reviewers by path in the prompt guidance; file-editing lenses run as a pass
  after approval; a lens is inlined in the prompt when the lane's host cannot load it by path (Claude built-ins, pi
  through an allow-listed `--skill`). *(amended 2026-11-16, 39 D-10, D-11, D-14: pi is the one host whose own docs verify a
  by-path skill (`--skill` still loads under `--no-skills`); an unverified path form inlines; a built-in with no file is run only
  by a native lane of its host, other lanes get a named note; the file-editing pass after approval is opt-in
  (`[review] edit_lens_pass`, off by default), runs on a write-capable lane and the owner accepts its diff, needs owner
  confirmation)*
- [ ] **REV-04**: Each lane gets a capability block built from its final argv (read-only or write, shell or not, the
  tools found on the child's PATH, codebase-memory-mcp only when its binary is on that PATH (it replaced codegraph in Phase 32.5)), so no lane is told about a tool it cannot use.
  A prompt larger than a lane's known context window (the lane's own runtime's value in the catalog, or a user override
  per (runtime, model); *amended 2026-11-16, 35 D-09*) is refused for that lane with a named reason and never
  trimmed (an unknown window is not capped and shows as unknown), and a value embedded in a prompt (file list, lens
  path) that holds a control character or points outside the repository or skill roots is rejected. *(amended
  2026-11-16, GSD lane-handling study: GSD refuses over-cap prompts and validates embedded paths)* *(amended 2026-11-16, 39 D-02,
  D-05, D-12: the capability facts are computed by the runner from the final argv and printed on its `--print-argv` capabilities
  line, with `unknown` where the argv does not show a fact; "the tools found on the child's PATH" means each tool is resolved
  against the PATH of the exact child environment at dispatch time, not the parent's; a lane whose argv applies a context form
  with an unverified effect has an `unknown` window unless the user stated one; the pre-spawn refusal is Python-side only, a GSD
  hook route is Phase 44's)*
- [ ] **REV-05**: One role-keyed table of the skills (and MCP servers where a host allows it) present on each host,
  rescanned every run, is shared by review, execute and curated-config; an optional config-time jev step sorts an
  unknown skill into a role, and the user confirms every such sort. *(amended 2026-11-16, 39 D-07 to D-09: the roles are a
  closed list with a locking test, seed rows are examples with source labels and never decide presence, a confirmed sort is a
  `[skills.roles]` config entry labeled user-stated, and MCP servers are listed by name only from each host's own config)*
- [ ] **REV-06**: jev picks the reviewer for a plan and how many lanes it gets (one or two) from files touched,
  complexity, task count and category, on top of deterministic signals (security, data, irreversible operations).
- [ ] **REV-07**: Before a review or judge round, spec-review pings each chosen lane with a short probe, replaces
  only the blocked ones from the user's preference order, continues with at least one, and records which lanes
  judged; a fake-lane test covers one blocked lane. Pings run at once, each with its own timeout; every ping or lane
  failure records a reason from one closed list that a test locks; a review in which a lane was replaced, failed or
  never resolved is reported partial with the lanes that judged, never as a clean run, and one lane's failure never
  cancels another lane's result. *(amended 2026-11-16, GSD lane-handling study: GSD's lane dispatch is fail-closed in
  this way)*
- [ ] **REV-08**: spec-review reports a superpowers plan that has no explicit fold step at its end as a finding.
  *(added 2026-11-03, 29 D-03: owner decision; the fold step itself is Phase 29)*

### Execute

- [ ] **EXE-01**: The superpowers execute adapter keeps one pinned-resume path and one owner-stop path, and hands off
  to spec-config when no config exists (one phase changes this code once). *(amended 2026-11-16, 36 D-03: the
  adapter's no-config entry check and ask are added with HUB-01 in Phase 36; this phase keeps them and owns the resume
  and stop paths)*
- [ ] **EXE-02**: After implementation, superpowers' `requesting-code-review` runs and ai-kit's capped loop iterates
  with the same review lanes until the review passes; at `receiving-code-review`'s stop-and-discuss point jev
  classifies the gray areas before the user is asked, and lens skills from the role-keyed table help where the model
  must decide.
- [ ] **EXE-03**: jev picks the executor for a plan or task from what is available: router lite or strong coding
  models, haiku or sonnet at low, medium or high effort on native Claude, composer on Cursor, or a cheap Copilot
  model; when a lighter executor is picked, the plan-writing instructions adapt to it (plans written for a lite
  executor follow lite instructions).
- [ ] **EXE-04**: When no configured executor is available, an opt-in fallback runs on the session's own model with
  jev choosing haiku or sonnet; with the flag off, the error names spec-config as the fix.
- [ ] **EXE-05**: Every executor brief lists the unit and arch gates and the commit guard block, and verify lines
  tolerate tool version banners; clean-tree checks ignore the owner's own config file, the progress counter matches
  the tasks actually done, and the agent-branch allow-list is applied the same way on every path.
- [ ] **EXE-06**: Lane transport is chosen per lane (subprocess, resumed session, herdr pane) for execute,
  spec-review and code-review lanes, reused within a plan and renewed after a set number of rounds, after a spike on
  session ids and headless resume; a herdr lane returns its result through a report file, its pane closes at plan
  close, and a start-of-run sweep closes leftover panes ai-kit created. *(amended 2026-11-16, re-run 2, 38 D-25 and D-27: the
  sweep is the runner's (RUN-13, `--sweep` and the start of every real run), and a pane this requirement opens carries the
  same run record and label so that sweep closes it)*
- [ ] **EXE-07**: Review and execute flows classify each lane result through jev before the loop continues or stops:
  an execute result as done, partial or needing another round; a review finding by whether its severity fits the
  kind of problem, the test tier, reproducibility, end-user reach and MVP versus production. Without jev a
  deterministic default decides, and the run log shows which one did.
- [ ] **EXE-08**: In an ai-kit checkout every executor lane (the runner's execute role and the superpowers adapter)
  runs with the real-home guard on (`AI_KIT_REFUSE_REAL_HOME=1`), and the execute flow compares the real host-config
  modification times before and after the lane and reports any change; a fake-lane test proves both.
- [ ] **EXE-09**: When an execute lane stops on a quota error, the superpowers adapter reads the lane's `lane_usage_limit`,
  `lane_fallback` and the pool's blocked-until record (RUN-14): a flagged lane moves at once to a fallback lane of a different
  pool, a lane whose blocked-until time has not passed is skipped at selection, the first selection after that time tries it
  once, and an unflagged lane keeps stopping and reporting; a fake-lane fixture covers each case. *(added 2026-11-16,
  free-lane pool study, PROVISIONAL, needs owner confirmation; 36 D-16 handed the executor reading to Phase 41 without a
  criterion)*

### Shared runner

- [x] **RUN-01**: One runner serves open-gsd cross-AI and ai-kit review and execute, taking runtime, provider and
  model, effort, escalation flags and the role (review or execute) per call, from the config or from the calling
  skill's decision. Every setting a call names is reported as applied or ignored with the reason (a runtime that
  takes no model flag or no effort is never fed one and says so). A runtime table (the `RUNTIMES` tables in
  `detection.py` and `cross-ai.mjs`) is seed data and examples only, each row labeled with its source (verified with
  date, or unverified); it never decides. What a runtime accepts is learned live (its own `--help` or listing, a
  probe, the catalog) and live evidence beats a row; a runtime missing from the table, and a custom command lane, can
  still serve review or execute with each setting shown as unknown until learned, and a table row never blocks a
  lane. *(amended 2026-11-16, GSD lane-handling study: GSD's fixed lane table decides which hosts may review and
  which accept model, effort or context settings; ai-kit keeps its own tables as seed and examples only, owner
  correction 2026-11-16)* *(amended 2026-11-16, 37 D-01 to D-12: the call vocabulary is `--role`, `--effort`, `--context`,
  `--escalate-runtime`, `--escalate-model`, `--session-id`; the runner composes each runtime's effort form and checks a
  level's shape only; every named setting prints applied, ignored or unknown with a reason from a closed list; a runtime
  with no formula runs from a declared argv file and otherwise gets a named refusal; a model id passes a universal safety
  floor with an advisory for unusual shapes; the Python mirrors give way to the runner's `--describe`)* *(amended 2026-11-21,
  plan time, 37 D-31 to D-34, owner requests of 2026-11-19 and directive of 2026-11-20: the settings also cover the skills and MCP
  servers a call names: the runner records per host how a lane takes a skill (by name, by path or as inlined prose) and an MCP
  server (the host's per-invocation form only), each form with a source label from the host's own help (2026-11-21: only pi's
  `--skill` and claude's and copilot's MCP flags are fed), delivers a skill in the first verified form in the order name, path,
  prose, and reports each skill and server applied or ignored with a reason; it never picks them (Phase 39, REV-03, REV-05),
  never edits a host's config and never prints a server's values; grok is not a target)*
- [x] **RUN-02**: The runner accepts a session id and prints the one it used, so a lane can resume across rounds.
  *(amended 2026-11-16, 37 D-03: one `--session-id` flag, `session=` in the status line, chosen or minted per runtime row,
  a rejected id fails visibly)*
- [ ] **RUN-03**: An opt-in idle watchdog ends a lane's process group after a set time without output, using the
  existing exit vocabulary; its default is one a slow, quiet model does not trip, and the runner self-test has a
  case for it. For an execute lane the idle clock also resets when the checkout's tree state or commits change, so
  a quiet lane that is committing is never ended and one that prints but changes nothing is reported. *(amended
  2026-11-16, GSD lane-handling study: GSD's stall check for native executors keys on commits since dispatch, not
  on output; `pi -p` prints no stdout while working)* *(amended 2026-11-16, 38 D-01 to D-05: the opt-in is
  `--idle-timeout <seconds|default>` or the baked `CONFIG.idleTimeoutS`, `default` is 900 s labeled judged, an idle kill is
  a timed-out attempt in the existing retry ladder, and review lanes reset on output only)* *(amended 2026-11-16, re-run 2, 38
  D-28, RUN-13: for a lane the runner hosts in a herdr tab, "output" is growth of the lane's `out` or `err` file)*
- [ ] **RUN-04**: The Phase 25 review cleanup lands: one confirmed-router rule, a quota-cycle class, the long
  self-test moved out of rendered copies, the user's lower timeout restored on cleanup, curated-config's
  `plan_io.py` calling gsd-core's `buildAgentSkillsBlock` instead of re-implementing it, and the dead `runCli`
  state, the live-detection plumbing and the clamp helpers removed. *(amended 2026-11-16, 38 D-17 to D-22, live-verified:
  the lower-timeout restore has no code left (its skill was removed in Phase 31), so it becomes a visible, tested
  before and after in the plan entry; only the unused `watchChunk` parameters, a redundant term and one redundant
  assignment are dead, and `clampCapS` and `clampAttemptTimeout` are live and stay; the router rule counts an owner
  statement or an alias assumed by the naming rule; the quota class is `quota_cycle`)*
- [ ] **RUN-05**: The error catalogue classifies the real-run bodies it misses today (provider not configured,
  policy budget 429, data inspection 400, context length 400, a plan-not-open code, 502/503 capacity, copilot's
  "model not available") and promotes the rows that now have evidence; the model-cooldown row's class is set from
  its observed durations (2 minutes to over 2 hours) rather than assumed transient. *(amended 2026-11-16, 38.1 D-01 to D-06: the
  failure classes become one closed list with a locking test (`quota`, `billing`, `auth`, `permission_blocked`, `bad_model`,
  new `bad_request` for a request the provider itself refused, `transient`, `crash`), apart from Phase 37's setting reasons and
  Phase 38's outcomes `partial` and `locked`; four hosts' own "model does not exist" wording was captured live on 2026-11-16 and is
  added per host, labeled verified; the listed real-run bodies are added labeled unverified where no body was captured; the five
  rows with recorded real evidence are promoted)*
- [x] **RUN-06**: A test keeps the runner template and the rendered project copy in sync. *(amended 2026-11-16, 37 D-18:
  the test renders into a scratch project and reads no `.planning/` path; `tools/check_dogfood.py` stays the live check)*
- [x] **RUN-07**: An execute run through the runner records a start-of-run tree baseline and takes a run lock,
  because the lock exists to stop two runs from sharing one checkout: two runs started at once on the same checkout
  leave one running and the other refused, a stale lock left by a dead process is reported and cleared, and later
  checks compare against the baseline. A test starts two runs at once. *(amended 2026-11-16, 38 D-06 to D-10: the
  refused run ends with the new status `locked` and a bare exit 75, and the baseline is reused by a later round for the
  same task until it ends ok)* *(amended 2026-11-16, re-run 2, 38 D-26, RUN-13: for a hosted lane the recorded child group is
  the launcher's group; a surviving tab is not a live lane and holds no lock)*
- [ ] **RUN-08**: Before an execute result counts as done, the runner checks the planned tasks against the commits
  actually made: a planned task with no matching commit, an early exit, a summary that admits skipped work, or a
  diff touching forbidden files turns the result into partial or failed; fake-lane tests cover each case. *(amended
  2026-11-16, 38 D-11 to D-15: `partial` (new, exit 1) for an uncovered task, no commit or an admission phrase,
  `contract_violation` for a forbidden path, each with a finding from a closed list; the check reads the prompt's task
  blocks and says `coverage=n/a` when there are none)*
- [ ] **RUN-09**: The runner's Claude matcher reads a usage-limit message from stdout as well as stderr, so a limit
  printed on stdout gets its quota class instead of an unclassified crash; a test covers both channels. *(amended 2026-11-16,
  38.1 D-07, D-08, live-verified: a limit in claude's JSON result on stdout (the runner's own `--output-format json`) is already
  classed quota; only the same sentence as plain text on stdout is a crash. The fix is a catalogue row that opts in with
  `input: stdout`, read only after a failed attempt and never as a live kill, plus claude's `api_error_status` and
  `api_error_type` fields read beside the text)*
- [ ] **RUN-10** *(amended 2026-11-16: the logged wording is server-side only; the client sees JSON codes `model_cooldown`, `ALL_TARGETS_SKIPPED` and `all_targets_cooling_down` with `Retry-After`, so the catalogue matches those too: see 38.1 SPEC R4 and CONTEXT D-22)*: The error catalogue matches the router's logged cooldown wording ('all N active accounts cooling
  down for model X (reset after ...)') as a quota-cycle class with its reset time, tested on a captured log line,
  unless an owner decision recorded in Phase 38.1 says why it does not. *(amended 2026-11-16, 38.1 D-09: the wording was captured
  from the router's own log (level warning), not from a client body, so the rows are scoped to confirmed router lanes with class
  `quota`, keep the reset as a display field `reset_after_s`, and are labeled unverified until a client body is captured; the
  wildcard rows stay transient)*
- [ ] **RUN-11**: The owner decides the runner's retry policy: soft retries for transient faults, periodic retries
  for 5xx and quota errors with checks for an early reset, and the 10-minute and 4-hour ladder against the shipped
  single wait. The evidence is the retry outcomes in the runner logs since Phase 25.1, the error catalogue's classes
  and the observed recovery times by route (router combos versus direct providers). The decision is recorded in
  Phase 38.1, and the runner's defaults in ai-kit's config (CFG-03) follow it, with a test per policy branch. *(amended
  2026-11-16, 38.1 D-10 to D-12, owner decision: "the shipped single wait" was stale, the shipped ladder is five soft retries in
  about 13 s, one session reset, then hard waits of 600, 900 and 1800 s and a stop after 55 minutes. The decision: a short first
  check (60 s), then 300 s, then every 600 s until the 4-hour cap (`hard_every_s`, default 600; `hard_waits_s` default
  `[60, 300]`), plus one extra check just after a reset time the body states, only inside the cap. "Periodic retries for 5xx and
  quota errors" means 5xx on every lane and quota on confirmed router lanes only; a direct lane keeps the 2026-11-02 rule (a quota
  error stops at once). Evidence: 34 router cooldowns, 24 under 2 minutes and 8 over 4 hours; recorded in
  `38.1-RETRY-POLICY.md`)*
- [x] **RUN-12**: Where herdr is available at runtime (`HERDR_ENV=1` and the `herdr` CLI), the runner may run a lane in a tab it
  opens and closes what it opened when the lane ends; the lane's command line, settings, session id, classification and exit codes
  are identical to the headless run, and the headless path stays the unchanged default, tested without herdr, with `--host none`
  and with `AIKIT_HOST=none`. A pane has no exit code, so a hosted lane reports through its own files (output, error, exit code),
  never through herdr's screen text or agent status; the runner touches only the tab it opened. *(added 2026-11-16, 37 D-22 to D-29,
  owner directive "herdr hosting"; interactive agent TUIs, TUI apps, e2e runs and pane reuse are Phase 42's and the calling skills')*
- [ ] **RUN-13**: A lane the runner hosts in a herdr tab (RUN-12) is as safe as a headless one: the run lock names the lane's
  launcher group as its child group, the opt-in idle watchdog reads the lane's own output files, the execute checks use the same
  inputs, a hosted lane's output files stay bounded, and the secret files of a hosted lane are deleted by the launcher as its first
  steps. A run killed hard leaves a secret-free record in its run directory, and a sweep (at the start of every real run, and on
  demand with `--sweep`) removes what such a run left and closes a tab only when a dead run's record and a listed tab agree on id
  and complete label; it never closes another pane, never reads herdr's screen text, status or the existence of a tab as a
  liveness or verdict signal, and an automatic sweep never calls herdr when hosting is switched off. What cannot be guaranteed (a
  kill before the launcher ran, a detached `setsid` grandchild, unlinked disk blocks) is stated in the skill. *(added 2026-11-16,
  re-run 2, 38 D-25 to D-33, owner directive "herdr hosting")*
- [ ] **RUN-14**: A quota stop of a usage-limited lane writes a secret-free "blocked until" record in the runner's state
  directory (never in config), keyed by the lane's pool (provider plus tier, so lanes that share a pool block together), so a
  later run does not spend a call on a lane that is still limited. The time is now plus the stated reset (the typed
  `retryAfterMs` of an opencode free-pool error, taken from the HTTP `Retry-After` header) plus the 120 s margin of the stated
  reset check when stated, else now plus 24 hours; the first selection after that time tries the lane once, and after a second
  consecutive failure the floor becomes 24 hours. A client-rule error (`FreeTierError`, a missing session header, a version gate)
  is not a usage limit and is never retried, and a removed model is a terminal `bad_model` that writes no record. A read-only query
  prints a record; the caller (Phases 40 and 41) decides, the runner never switches lane. *(added 2026-11-16, free-lane pool
  study, 38.1 D-23 to D-27, PROVISIONAL, needs owner confirmation: whether the 24-hour floor or the stated reset wins, the
  second-failure rule and the margin; source `.planning/research/2026-11-16-opencode-free-models.md`)*
- [ ] **RUN-15**: The grok CLI runtime is removed from detection, command building, the runner's runtime table, the CLI
  profiles, the docs and the tests, and a test fails when a runtime list, command builder or profile names it again. Grok
  models stay reachable as models of opencode, pi and cursor-agent. A config that still names the grok runtime gets one clear
  message naming the replacement runtimes and the re-save command. *(added 2026-11-19, owner decision, Phase 39.1: a rare
  runtime that adds no value is not worth maintaining; no SPEC yet)*

### Project rules skill

- [ ] **RULE-01**: One `ai-kit-project-rules` skill replaces the seven `ai-kit-project-rules-*` skills, with the shared
  library inside it, and its audit on ai-kit reproduces today's findings.
- [ ] **RULE-02**: On a project with only a Claude instructions file, bootstrap migrates it into AGENTS.md after
  asking, removes the Claude file, adds the line that loads AGENTS.local.md, and the audit flags a Claude file that
  reappears; in a new worktree AGENTS.local.md is a link to the main checkout's file (a copy only where GSD writes
  it), and whether Claude follows the load line stays labeled unverified until a live check records it.
- [ ] **RULE-03**: The generated AGENTS.md block carries the top rules (AGENTS.md is the only instructions file;
  vertical slices with something visible at the end of phase 1; bypass mode means scripts in files; done means the
  gates pass; talk in the user's language and write in English; simplicity over complexity but the best
  implementation over the easy one, deciding with jev on certainty and criteria; codegraph (replaced by codebase-memory-mcp in Phase 32.5) for code exploration *(amended 2026-11-03, 30 spec: the general form of Phase 30's tool-use rule: codegraph first for code, rg for Markdown, graphify for documents and planning, index and sync automatically whenever the CLI is present, refresh before research on stacked branches; and `.codegraph/`, `graphify-out/` and `.planning/graphs/` gitignored when those tools are present)* *(amended 2026-11-03, 30 D-16: `graphify-out/` is always ignored and is the graph agents query in a non-GSD project, which never gets a `.planning/` folder; `.planning/graphs/` is ignored and fed by a copy of the same build only in a GSD project)*) and
  the general never list, placed below the owner's hand-written sections without collision, repetition or
  contradiction. The vertical-slices rule points to a runbook that names, per stage (mocks, front, backend,
  database, real data, security, infra, observability, accessibility), the lens skills from the role-keyed table,
  and defines 'visible at the end of phase 1' (a UI mockup deployed on minimal infra; for an API, a service contract
  with a JSON sample tied to a schema or an OpenAPI document).
  *(amended 2026-11-16, owner decision, RULE-33: "talk in the user's language" is superseded; the conversation language
  defaults to English and changes only when the user asks for another one, then stays until the user says otherwise; written
  artifacts stay in one language, English by default)*
- [ ] **RULE-04**: Runbooks live at `docs/run-book/<topic>.md` with a hash header, so a developer's edits are never
  overwritten.
- [ ] **RULE-05**: Makefile rules: `setup-dev` and `setup-docker` (with `setup-env` as an alias for one milestone),
  `validate-<category>` aliases only for a category with more than one tool and a cap on categories, and recipes of
  three lines or fewer. *(amended 2026-11-03, 30 D-04: `setup-dev` also installs the tools the project's flow needs when they are missing (codegraph (replaced by codebase-memory-mcp in Phase 32.5) and graphify when the project uses them, pre-commit, gh and gh-stack for the unit flow), each through a guarded step that reports a failed install and degrades instead of failing; ai-kit's own target ships in Phase 30, FLOW-13)*
- [ ] **RULE-06**: Event playbooks cover session start, worktree created, end of task, plan or phase, CI wait, the
  PR review loop (reusing an existing feedback skill first), delegation and quota, each reachable from one pointer
  line in the generated AGENTS.md block. The worktree-created playbook runs `setup-dev` through a git
  `post-checkout` hook and checks that the new worktree can run its project `gsd-tools`, naming the install step
  when it cannot (ai-kit never installs GSD itself). RULE-17 to RULE-19 set what the end-of-unit, delegation and
  quota playbooks contain; RULE-20 to RULE-23 add the requirement-intake, audit, milestone-close and worktree-closed
  playbooks.
  *(amended 2026-11-03, 30 spec: the worktree-created playbook also runs `codegraph init` (replaced by codebase-memory-mcp in Phase 32.5) (or `sync` when the worktree has its own index) and `graphify update .` in the new worktree whenever the CLI is installed, without blocking git; a missing CLI prints one line; ai-kit's own hook ships in Phase 30)* *(amended 2026-11-03, 30 D-16: the copy into `.planning/graphs/` happens only in a GSD project; a non-GSD project keeps `graphify-out/` only)*
- [ ] **RULE-07**: The skill chains `crafting-effective-readmes` for the README, a diagram skill for README diagrams,
  and `agent-md-refactor` through a wrapper.
- [ ] **RULE-08**: Per-stack research at invocation is time-boxed and cached per category for the five known stacks;
  the CI check reads GitHub Actions and GitLab CI including GitLab `include:` files.
- [ ] **RULE-09**: ai-kit's own AGENTS.md carries the generated block, including the session-wake rule (arm the wake
  before a multi-plan run), the cross-AI runner pointer (GSD-only rules appear only in GSD projects) and the general
  test-run and CPU-share rules (RULE-24); ai-kit's docker runbook moves from `docker/local/README.md` to
  `docs/run-book/`; and ai-kit's own rule violations are settled.
- [ ] **RULE-10**: `ai-kit-project-rules` applies its rules itself on a strong model, or delegates each area to
  strong or standard subagents with only the orchestrator writing files; it runs the areas in sequence when
  subagents are unavailable, and on a weak model writes templates only, with every pending item labeled. A fixture
  test covers each mode.
- [ ] **RULE-11**: Bootstrap wires every detected host that does not load AGENTS.md and AGENTS.local.md natively to
  load both (for example opencode's `instructions` list) through ai-kit's atomic writers, and a fixture test per
  host shows both files loaded. The owner decides how AGENTS.local.md takes precedence on Claude (a lone
  CLAUDE.local.md hides AGENTS.md from Claude), with the hosts' documented load order as evidence; the decision is
  recorded in Phase 45.
- [ ] **RULE-12**: The generated rules carry the asking rules: an autonomous run asks the owner only for a
  locked-decision ambiguity, a package or security gate, or a call only human eyes can make, and otherwise verifies,
  decides and reports (a CLI reviewer handles objective checks); every owner-facing decision question starts with
  one line per item saying what it is and who uses it; a package-approval question states the dependency's purpose
  and the alternatives it beat before the approve or reject options. A fixture test pins each rule.
- [ ] **RULE-13**: The generated rules carry the writing rules: name items in plain words by what they check or
  decide, never by letter-number codes outside history files; define a term once; capture the owner's open questions
  in the todo list or backlog in plain words; write trade-offs as one header per option with pros and cons bullets,
  never a markdown pipe table. The rules skill's own report leads each finding with its plain title, and a test
  fails on a report line that leads with a bare rule id.
- [ ] **RULE-14**: The generated rules carry the run rules: a permissive run never ends a turn with a waiting
  message and keeps doing independent work while a background agent runs; when jev is installed, the orchestrator
  sends every decision point (gray areas, proceed-anyway gates, revision conflicts, checkpoints, review triage,
  ambiguous quota routing) through the shared jev client as an advisory item, logs each call in the run ledger, and
  decides itself when jev is absent or unsure. A fixture test pins both.
  *(amended 2026-11-04, owner rules audit: jev comes first. Before spending reasoning on a classification or a
  choice (is a failure real or environment noise, is a finding a real bug, which of two to four fixes, does a
  deviation need the owner, re-run or move on), the agent asks jev, checks the answer with one cheap check, and
  acts; a general rule, not ai-kit-only)*
- [ ] **RULE-15**: The generated never list forbids reading or copying real credential files in any run (synthetic
  fixtures prove behaviour), executing a command string read from project config (probe only known shapes), and
  scripts that assume the working directory (they resolve the repository root themselves and search hidden planning
  folders with `--hidden`); it says a text rule is pinned to its policy source by a test. A fixture test pins each
  entry.
- [ ] **RULE-16**: The Node runbook bootstraps with pnpm unless the project already has another lockfile or its
  rules config names another package manager; a fixture shows a fresh Node project gets `pnpm-lock.yaml` and an npm
  project keeps `package-lock.json`.
- [ ] **RULE-17**: The end-of-task, plan and phase playbook runs the gates and the commit folding (FLOW-01), flags
  stray untracked files, and re-reads the latest verdict and summary files before writing any close-out text; a
  check flags a count or verdict that differs from the current files, shown by a fixture with a stale count.
  *(amended 2026-11-03, 29 spec: the generated playbook carries Phase 29's folding policy in full — logical-feature grouping, never
  one squash per plan or phase, the tree check before the swap, a local backup tag deleted when the PR merges,
  `--force-with-lease` only on unmerged branches, the primary remote only — so a project without ai-kit's folding
  step still follows it; the owner wants these rules part of project-rules, not ai-kit-only)*
  *(amended 2026-11-04, owner: the fold runs unattended before every push of a unit's branch and never asks
  for confirmation; the generated rules and the hook advisory say so in every project that uses them)*
- [ ] **RULE-18**: The delegation playbook splits work into pieces of about 20 to 30 minutes with one verifiable
  result each, forbids extra spawned reviewers unless the brief asks, and says how to tell the owner what each
  running agent and shell is. It ships a brief header with five rails (never kill a process the subagent did not
  start; no live CLI probes or real credentials, fake binaries in a temp dir instead; scratch files only in the job
  temp dir or `./tmp/`; anything beyond a short single command in a script file; pass these rails on to further
  subagents), and the briefs that spec-review, the superpowers adapter and goal-prompt generate include it; a test
  checks the header in each generated brief.
  *(amended 2026-11-04, owner rules audit: the header also carries (a) a jev-first block with time rules: ask jev
  before reasoning about a classification or a choice, re-run only the failing target after a fix, run the
  whole suite once at the end, and stop a step that passes twice its estimate and report; (b) the codegraph (replaced by codebase-memory-mcp in Phase 32.5)
  instruction: sync the index, then explore with it before grep or Read, using the shell form when the subagent
  has no MCP tools; (c) where the project has a real-home refusal guard, delegated executor runs export it, and
  the close compares the modification times of the real host-config files, because prompt rails are advisory
  and only mechanical guards hold. A general rule, not ai-kit-only)*
- [ ] **RULE-19**: The quota playbook follows the WAKE-03 decision: on a usage limit it arms a wake at the reset
  time before stopping and removes the wake when the run ends, and every progress or resume ping gives the local
  time, the running step and when it started, in one line; a doc-contract test pins the format.
- [ ] **RULE-20**: The requirement-intake and new-milestone playbook turns every owner idea into a requirement and
  every working rule into text in a flow agents read (AGENTS.md, the generated rules or playbooks, a skill brief, a
  host hook, or what curated-config writes), never only a private memory, because an idea that is not a requirement
  never gets built. Before an incoming wish is recorded as new, it searches past transcripts, archived planning
  files and todos and labels the wish implemented, partly done, decided otherwise, deferred, lost or claimed but
  missing; a fixture run labels a seeded earlier request.
- [ ] **RULE-21**: The audit playbook closes a pending check from redacted transcripts and logs when they hold the
  evidence, and asks for a live run only when they do not; the playbook text and a fixture pin the order.
- [ ] **RULE-22**: The milestone-close playbook classifies every open item into the todo list or backlog in plain
  words and writes one inputs file grouping them by theme with size, dependencies and who must act; the close fails
  when an open item appears only in a review note. It re-reads the current verdict and summary files before writing
  close-out text, and moves planning folders read-only dry run first, listing every reference, then moves and
  repoints them in one commit. A fixture seeds an item that lives only in a review note.
- [ ] **RULE-23**: The worktree-closed and milestone-close playbooks decide whether each branch is merged,
  superseded, useful or discardable by content (`git merge-tree`, `git cherry`), tag any branch that is not
  hash-merged before deleting it, and run the shared secret scanner (DEF-02) and a home-path check before any push;
  a fixture repository with a rewritten branch is classified correctly.
- [ ] **RULE-24**: The generated rules carry the test-run rules with their reasons. Parallel runs exist to save
  time, which matters once a project has hundreds or thousands of tests or tests that are slow to set up or run:
  unit tests run in parallel, and integration and e2e tests too where possible, with any test that cannot run in
  parallel kept in an explicit, commented exception set. Worker counts are a share of the available CPUs, never a
  hardcoded number, and a setting may only lower that share; this CPU-share rule is general, not ai-kit-only.
  Concurrency tests in integration and e2e depend on the project's kind: required (strongly recommended) for APIs,
  services and other multi-user systems, to prove users do not compete for or overwrite shared resources; only nice
  to have, never required, for desktop apps, CLIs and similar single-user tools. The rules skill records the
  project's kind (detected, or asked once) and that kind decides which text applies; a fixture test pins both texts
  on one project of each kind. *(amended 2026-11-16, owner decision, RULE-34: for a project with a slow suite the rules also
  point to smart test selection, so the hooks run the tests that cover the diff instead of the whole suite; RULE-34 owns that
  mechanism and its audit finding)*
- [ ] **RULE-25**: The testing runbook writes these rules into the project: a parallel test runner configured by
  default for unit tests, and for integration and e2e where the stack allows, with an explicit, commented exception
  set for tests that cannot run in parallel and a worker count computed as a share of the available CPUs that a
  setting may only lower; for an API, service or multi-user project, an integration or e2e concurrency test template
  on shared state, marked required; for a desktop or CLI project, the same template marked optional. Fresh Python
  and Node fixtures of each kind show the result. How the rules are enforced (for example a planning-time check, a
  gate test or a plan-checker criterion) is an open question that Phase 46's researcher evaluates during planning.
- [ ] **RULE-26**: The generated top rules say that a choice question lists the option the rule or the verified
  evidence recommends first, labelled `(Recommended)`, and that a host capability limit (for example whether a
  subagent can spawn subagents or ask the user) is verified before it is stated.
- [ ] **RULE-27**: The commit-fold engine moves from the temporary `ai-kit-commit-fold` skill (Phase 29) into
  `ai-kit-project-rules`; the standalone skill is deleted, and its callers (the GSD wave-end extension and the
  superpowers adapter) find the engine in its new home through the installed-skill lookup, with their tests
  intact. *(added 2026-11-03, 29 D-01: owner decision)* *(amended 2026-11-07, owner decision: because of this move,
  `ai-kit-commit-fold` is excluded from the Phase 32 re-judge; the folding policy in
  `references/folding-policy.md` moves with the engine and feeds RULE-17's playbook, and the new skill's judge run
  (JDG-04) covers the absorbed fold text)*
- [ ] **RULE-28**: The rules tell an agent not to run `make validate` before each commit or push when the
  pre-commit and pre-push hooks run the same checks. After a hook fails, the agent fixes the cause, re-runs
  only the failed check through its own target (for example `make test-unit` when a unit test failed, `make
  pyright` when the type check failed), confirms it passes, and commits again so the hooks re-run every check.
  The failing hook's output names the target that re-runs it. *(added 2026-11-04: owner request)*
  *(amended 2026-11-04, owner: a general rule, generated into every project that uses ai-kit's project rules and stressed by ai-kit's hook advisory there, not ai-kit-only)*
- [ ] **RULE-29**: Closing a plan or a phase (GSD or superpowers) leaves no leftover resources: no background
  process or process group the run started, no container, no browser or Playwright instance, no held file lock,
  no temporary files or directories in `/tmp` or the system temp dir (counted by size and by inode), no large
  scratch file outside `tmp/`, and no swap pressure the run caused. The end-of-plan playbook takes a resource
  snapshot at the start of the unit, compares it at the close, lists each leftover with its owner and a removal
  command, and removes only what the run itself started; anything else is reported to the owner. A spike gets
  the same check when it ends. The same snapshot covers the working tree: an ephemeral file the run created that
  git neither tracks nor ignores (a log, a report, a scratch script, a generated output) is moved under `tmp/`,
  removed, ignored or committed before the close, and untracked files that predate the unit are left untouched
  and only reported. *(added 2026-11-04: owner request)*
  *(amended 2026-11-04, owner: a general rule, generated into every project that uses ai-kit's project rules and stressed by ai-kit's hook advisory there, not ai-kit-only)*
  *(amended 2026-11-07, Phase 32 close-out: where a host rule forbids deleting outside `tmp/`, the playbook moves the run's own `/tmp` leftovers into the repository's `tmp/` instead of deleting them; the per-plan scope script that plan rails carry today deletes its run folder and zero-byte `uv-*.lock` files in `/tmp`, breaking that rule, and this playbook replaces it)*

- [ ] **RULE-30**: The end-of-task and phase playbook says a verification item that needs a real push or a run
  inside a host session is not owner-only: the agent does it. For a push check it folds the history first
  (RULE-17), then pushes the unit's branch to the primary remote itself. For a host-session check it starts that
  host (for example opencode or pi) in a herdr pane when herdr is installed, prompts it to run the check, reads
  the result and closes the pane (RULE-29). It then marks the verification and acceptance checklists passed and
  runs the transition. Any other push, and a push to a secondary remote, still needs the owner's consent; when
  herdr is absent the item is reported with the exact command for the owner. A doc-contract test pins the order.
  *(added 2026-11-04, owner rules audit: general rule, from the owner's memory)*
- [ ] **RULE-31**: The delegation playbook says what to do when an external run fails. The runner's retry ladder
  (same session first, then a new session, then stop and report with evidence) belongs to the runner; the agent
  never switches harness, provider or model on its own because of a failure, and never falls back to another CLI
  because the first hit a quota, so a silent fallback cannot spend another vendor's quota. A background run that
  comes back killed with little output gets a short foreground probe first: the same command under a time limit
  with its output file polled for growth. Steady growth means slow (raise the timeout); no growth or a quota or
  authentication message means a real failure to investigate. Only then is a retry decided. A doc-contract test
  pins the text. *(added 2026-11-04, owner rules audit: general rule, from the owner's memory)*
- [ ] **RULE-32**: In a GSD project only, the generated rules say GSD settings change through the project-local
  `gsd-tools` (`config-set`, and `effort sync --apply` for agent model and effort), never by hand-editing the
  config file; the tool is run from the project root, never a global install; the agents folders the session
  loads (including the launch folder's when working in a worktree) are synced and checked afterwards; and the
  `claude_md_path` setting names the real AGENTS.md or AGENTS.local.md file, never a symlink. A non-GSD fixture
  project gets none of these lines. *(added 2026-11-04, owner rules audit: general rule for GSD projects, from
  the owner's memory)*
- [ ] **RULE-33**: The generated AGENTS.md block carries a language section. Written artifacts (documentation, planning
  files, commit messages, code comments and memory files) are in one language, English by default; a project may choose one
  other language and then never mixes two in a file; quoted owner words are translated faithfully. Memory files are written in
  the same language as the artifacts. The project's AGENTS.md outranks the agent's memory files: a memory entry never overrides,
  relaxes or reinterprets a rule there, and the memory is corrected instead. The conversation language defaults to English and
  changes only when the user asks for another one, then stays until the user says otherwise; a memory entry or a mirrored habit
  never changes it. The audit flags a project AGENTS.md that has no such section and a memory entry that contradicts it (labeled
  inferred, because the match is a phrase check on the entry's description and body, never a reading of the owner's intent),
  and a fixture test pins each finding on synthetic files; the real memory folder is never a fixture. *(added 2026-11-16,
  owner decision; the model text is the `English only, always` and `This file outranks memory files` bullets of ai-kit's own
  AGENTS.md; Phase 45.1)*
- [ ] **RULE-34**: The pre-commit and pre-push test hooks the rules skill requires are a smart test selection, not a full suite.
  From the diff (the staged files for a commit, the pushed range for a push) the mechanism finds which source components
  changed (documents are not components), reads a dependency map to decide which tests must run (the tests of a changed
  component and of its dependents) and runs only those. It is conservative: it runs the full suite when the diff touches
  shared machinery or a file with no mapping, when the mapper fails or when its data is stale; a docs-only diff runs no tests
  beyond the doc checks; it reports its selectivity and the time saved. The project-rules audit flags a full-suite hook in a
  project whose suite is slow, and when no such mechanism exists the skill requires one and asks a subagent to build it from a
  delegation brief that carries this contract and a fixture acceptance (a diff touching component A runs only A's tests and
  its dependents, a shared-machinery change runs everything, an unmapped file runs everything, a docs-only diff runs none); the
  brief includes the stack's graph building (a Python import graph, a JS or TS module graph, others as detected). The in-repo
  reference to generalize is `tools/staged_mapper.py` with `tools/run_unittest_parallel.py --staged` (GATE-01), which today is a
  name index over tests and their helpers and prints selectivity with `--stats`; a time-saved report is new. *(added
  2026-11-16, owner decision; Phase 46)*

### Host hooks

- [ ] **HOOK-01**: `setup.py hooks status` shows which ai-kit hooks are on for each host.
- [ ] **HOOK-02**: One dispatcher hook per host reads layered settings when it fires, so switching a hook on or off
  never rewrites a host config, and it knows the launch mode (direct, herdr, subagent, subprocess). A hook advises
  and never blocks, except the opt-in guard rules of HOOK-07 (amended 2026-11-03): it prints one line naming
  the playbook to load, and agentless events such as the git hook run
  only commands from an opt-in list.
- [ ] **HOOK-03**: Session hooks give indexing advice for new worktrees and checkouts naming only installed tools;
  doc paths are install-relative and reach the model context as well as the user line (where a long path is cut),
  tested from a scratch `XDG_DATA_HOME/ai-kit` install; and compaction metrics are recorded as window size and
  compaction duration, with inferred numbers flagged.
- [ ] **HOOK-04**: Cursor hooks respect `CURSOR_CONFIG_DIR`, re-verified against current Cursor docs; the
  `cursor-agents` destination is checked against the same config-dir split.
- [ ] **HOOK-05**: The host-hook spikes (reset time in Claude's stop-failure event, pi's briefing, opencode child
  sessions, codex trust under `codex exec`, copilot running `.claude` hooks, background rewake) are recorded before
  the event catalogue is built.
- [ ] **HOOK-06**: A spike records, per host, which shell commands still stop the flow for the owner's
  confirmation and why, using the session history and the docs: `cd` (the owner sees it most, even a `cd` into
  the project's own folder), chains of `&&`, `||` and `;`, several pipes, `<<` and `>>`, subshells, the
  `rm` checks, untraceable commands, and auto mode's evaluator. It also records whether a PreToolUse hook's
  `ask` prompts under `bypassPermissions` on Claude and whether a `permissions.ask` rule can match these
  shapes, plus the equivalent mechanism or its absence on opencode, pi and Cursor, and compares the guard
  actions (deny with guidance to the agent, ask the owner, advise) by how often the flow stops. Each answer is
  marked verified or documented-only. *(amended 2026-11-03: widened from heredocs to complex inline commands and
  `cd`; the owner asked to explore which action is best.)*
- [ ] **HOOK-07**: Opt-in guard rules run through the dispatcher: each rule matches a tool call, carries an
  action (`deny` with guidance shown to the agent, `ask` the owner, or `advise`) and a message, and is switched
  on through layered ai-kit settings, never by rewriting a host config. The first rule set covers complex
  inline commands: always a heredoc, a subshell or command substitution, or a `cd` (including into the current
  folder, since the shell's working directory already persists); otherwise three or more segments joined by
  `&&`, `||`, `;` or `|`, or a `>>` inside a chain. A single `cmd | head` or `a && b` passes; the thresholds live
  in ai-kit settings. A denial never leaves the agent without options: its message says why and names them
  (drop a `cd` into the current folder, use absolute paths, write the steps to a script under `tmp/` and run
  it, or split the call). The default action is chosen from HOOK-06's comparison, so that the flow stops as
  little as possible. Detection reuses the shared command-text module (`has_heredoc`, the segment splitter).
  Where a host has no mechanism that works under bypass, the rule falls back to the strongest it has and
  `setup.py hooks status` says so. Tests cover each shape, the passing shapes, and each action.
  *(amended 2026-11-03: widened from the heredoc guard; a denial must carry guidance.)*

### Quota and wake

- [ ] **WAKE-01**: A wake fires on a 5-hour grid from the first detected window (for example 01:01, then every 5
  hours, capped at 7 days), reading the window deterministically from what Claude passes to the status line; two
  sessions arming the same grid slot at once leave exactly one wake, shown by a test with concurrent arm calls.
- [ ] **WAKE-02**: A wake is armed just before a session is known to run out.
- [ ] **WAKE-03**: A recorded decision says where the shared quota logic lives (library, playbook or skill) for
  session-wake, the rules playbook and the runner.
- [ ] **WAKE-04**: Desktop notices check paths before firing, say what was checked, are readable (host, short
  session id, reason, journal command, long enough to read), and are tested with fake notifiers; a missing session
  store gets its own text ('session store not found at <redacted path>'), and a failed notice never fails the wake.
- [ ] **WAKE-05**: On macOS the wake and notice work through launchd, or arming refuses with a clear "unsupported"
  message; macOS behaviour stays labeled unverified until it runs on a Mac.
- [ ] **WAKE-06**: An opt-in capture hook records the field names and a redacted payload of the next real Claude usage
  limit.

### curated-config

- [ ] **CUR-01**: curated-config reads open-gsd docs at the installed version's tag, cached per version under
  `.aikit/`, and offers a local update only when the changelog makes it worth it, labeled by impact.
- [ ] **CUR-02**: Questions come grouped in a cascade: MVP, UI, granularity beside MVP, runtime (Claude preferred,
  asking when another host is detected), base branch detected from the merge flow.
- [ ] **CUR-03**: It sets the balanced profile, dynamic routing, tier models and per-agent models and effort
  classified with jev, writes everything through the project's `gsd-tools` with effort values validated, and never
  removes a setting it did not plan.
- [ ] **CUR-04**: UI phases and review only for UI projects; cross-AI execution asks for confirmation; English
  `response_language`; `claude_md_path` names AGENTS.md (a real file); branch per phase; intel on;
  `workflow.use_worktrees` stays on (GSD's default `true`) unless the owner turns it off, and the cases where GSD
  itself turns it off are stated from the installed GSD docs.
- [ ] **CUR-05**: Skills are assigned to GSD agents by responsibility from the skills actually available, through the
  shared role-keyed table.
- [x] **CUR-06**: curated-config no longer writes `review.effort.opencode = "high"`. *(amended 2026-11-13, 32.4 spec S5: live check: the checkout-local gsd-core 1.16.0 no longer passes the effort as `--variant` (which opencode 2.x rejects) but appends it to the model as `#<variant>`, warning when no model is set; so the fix removes the v1 `apply-review` command's fixed write, which sets no model, and keeps the v2 planner's catalog-derived effort row, which is set with `review.models.opencode` and labelled with its unverified effect)*
- [ ] **CUR-07**: When graphify is installed, curated-config turns on GSD's `graphify.enabled` and
  `graphify.auto_update` and says what they do; it never leaves the graph switched off silently.
- [ ] **CUR-08**: After writing effort settings, curated-config runs `effort sync --apply` for the checkout and for
  the launch directory of a worktree session, and reports any agent file still carrying the old effort; a fixture
  with two agents directories proves it.
- [ ] **CUR-09**: curated-config sets the GSD keys that make the plan checker read a plan again after review amends
  it and before execution, citing the installed GSD docs; when GSD already does this by default, the phase records
  the doc citation and writes nothing. A fixture config shows the result.
- [ ] **CUR-10**: The owner decides, per v1 curated-config subcommand, whether it is kept, merged into v2 or
  removed. The evidence is a recorded run of each v1 subcommand on a fixture project; the decision is recorded in
  Phase 43, and no v1 code is removed before its run is recorded.

### dist and install

- [ ] **DIST-01**: A committed `dist/skills/<name>/` is generated from `skills/` without evals and tests, and a
  rebuild-and-diff check fails on drift. *(amended 2026-11-07, owner decision from the distribution fact sheet: a
  public `npx skills add castocolina/ai-kit` installs from the trimmed `dist/skills` copy, never from `skills/` with
  its evals, through a README route or a manifest the skills CLI reads; a test or recorded dry run shows no
  `evals/` folder reaches the target)*
- [ ] **DIST-02**: Setup syncs each selected host headless with one pinned `npx skills add ... -a <host> -g --copy
  -y` call after a dry run, passes the CLI's output through, and removes only ai-kit's own links; it migrates
  existing ai-kit symlinks to copies and removes ai-kit's copies of removed or renamed skills (the seven rules
  skills, the three removed skills) without touching other skills. *(amended 2026-11-07, owner decision from the
  distribution fact sheet: the one-line `curl ... | bash` installer still fetches the repo into its install folder,
  then copies each selected host's skills from `<clone>/dist/skills`, never from `skills/`; the README and the
  installer's own help say so)*
- [ ] **DIST-03**: Skills that share code install as a group or vendor it, so a copy install never breaks.
  *(amended 2026-11-07, owner decision from the distribution fact sheet: for `ai_kit_spec`, copy-per-skill
  vendoring or a group install is chosen after a spike that copy-installs its callers both ways into a scratch home)*
- [ ] **DIST-04**: The README documents install as a plugin and through `npx skills`. *(amended 2026-11-07, owner
  decision from the distribution fact sheet: the same README work fixes two stale docs, the README install line that
  omits pi and `.claude-plugin/plugin.json`'s description that still says the installer symlinks)*
- [ ] **DIST-05**: Every script belongs to the skill or tool that uses it: orphaned scripts are adopted, merged or
  deleted, the stale jev scratchpad is deleted (its plan and review history kept as research), and dead functions
  are removed.
- [ ] **DIST-06**: After setup's sync, each host lists every skill once (no duplicate from `~/.agents/skills` plus a
  host folder, as seen for ponytail on opencode and codex), and pi keeps its own skill list although pi and codex
  share `~/.agents/skills`; shown in a scratch home and reported by the config doctor on this machine.
- [ ] **DIST-07**: AGENTS.md's Architecture section states that ai-kit installs only its own skills and never a
  third-party skill, plugin or GSD (it may recommend or map installed ones), and an installer test fails when setup
  writes a skill ai-kit does not own.
- [ ] **DIST-08**: Copy installs get updates although `git pull` no longer reaches the hosts: re-running the
  installer or setup re-syncs every host it installed, and a drift report names each host copy that differs from
  `dist/skills`; shown in a scratch home with an edited copy. *(added 2026-11-07, owner decision from the
  distribution fact sheet)*
- [ ] **DIST-09**: Every hook script setup still links from the clone (`tools/hooks/*` into pi and opencode) that
  reaches into `ai-kit-session-wake` has an owner: it ships with its skill or vendors the shared code, so a hook
  keeps working once skills are copies; a test fails on a hook that imports from another skill's folder.
  *(added 2026-11-07, owner decision from the distribution fact sheet)*

### Architecture and shared code

- [ ] **ARCH-01**: A whole-tree layering test over `tools/` and `skills/` fails when a module imports across a
  forbidden layer (the layers are set by Phase 52's research), and a non-vacuity check proves each layering rule
  catches the violation it claims to; AGENTS.md's two mentions of "backlog 999.3" (Architecture and the Testing
  deferred note) and PROJECT.md's Out of Scope line point to this test instead.
- [ ] **ARCH-02**: The JSONC scanner and the atomic JSON writer each have one shared implementation (today about
  three and eight copies), reached in a way that survives copy installs (DIST-03), and a test fails when a new copy
  appears.

### jev

- [x] **JEV-01**: jev picks its backend per host (Laya first with a configurable URL and a first-run question,
  TypeSafe from the environment), and the home-file key fallback is strictly last. The probe names a missing key
  source and the terminal-multiplexer hint (a long-lived multiplexer server keeps the environment it started with)
  without printing any value; the skill gives credential guidance for non-interactive shells; and the home-file
  fallback is removed once a test shows agent shells inherit the key from the environment, or kept with a recorded
  reason. *(amended 2026-11-15, Phase 34 plans: the Laya URL comes from `[jev] laya_url` at any address, project over user, with `JEV_LAYA_URL`/`AI_KIT_LAYA_URL` as session overrides; a Laya host off loopback needs the same host-bound consent as a remote backend; the probe asks `needs_answer: laya_url` once; the home-file key fallback is kept with a recorded reason)*
- [x] **JEV-02**: OpenCode Zen is gone from the jev-fast-decision skill.
- [x] **JEV-03**: Laya is calibrated against its accuracy floor, the opencode judge lane is re-judged, and the
  calibration script is documented. *(amended 2026-11-07, owner decision from the jev and typesafe-ai research:
  before calibrating, Laya is upgraded from 0.4.2 to 0.4.27 or the reason to stay is recorded; the calibration
  records how accurate confident Laya answers are, tied to the Laya version and checkpoint revision; and the skill
  text states that a confident Laya answer is not proven accurate, since the 32-case live run measured about half
  right when confident)* *(amended 2026-11-14, owner decision: no upgrade step — the owner upgraded Laya in
  `llm-env`; the calibration runs on the version at the configured address and records its version or
  fingerprint)* *(amended 2026-11-15, Phase 34 plans: the limit sentence cites the latest calibration's date, case count and confident-answer accuracy, and the 32-case run of 2026-10-23 only until a new run exists)*
- [ ] **JEV-04**: A short jev marker block reaches the four global instruction files through ai-kit's atomic writers,
  with the owner's consent. *(amended 2026-11-03, 30 spec: it reuses the marked-block editor FLOW-12 builds in Phase 30; the four files are the global ones codegraph's (replaced by codebase-memory-mcp in Phase 32.5) installer also writes: `~/.claude/CLAUDE.md`, `$CODEX_HOME/AGENTS.md`, `~/.gemini/GEMINI.md`, `${XDG_CONFIG_HOME:-~/.config}/opencode/AGENTS.md`)*
- [ ] **JEV-05**: jev answers image and bounding-box questions after a TypeSafe spike, with a key and consent; a
  named caller uses it to judge a delivered screen against a supplied mockup, the request limits are recorded as
  live facts, and the Laya capability cell is re-checked. *(amended 2026-11-07, owner decision from the jev and
  typesafe-ai research: the Laya re-check covers laya 0.4.27's image support and records whether its server exposes
  it over HTTP)*
- [x] **JEV-06**: The jev ladder client has a shared home that every classifying skill uses, outside spec-discuss;
  skill text treats jev as a black box: it says only to ask that skill and follow its SKILL.md, carries no backend,
  consent or probe detail, and treats `needs_fallback` or no answer as the rule-based default deciding.
- [x] **JEV-07**: A knob in ai-kit's config turns jev classification on or off for every skill; it is asked once
  when absent, and with it off every skill behaves exactly as if jev were not installed, shown by tests in a scratch
  home. *(amended 2026-11-15, Phase 34 plans: the knob is `[jev] enabled`, project over user; `GSD_PATH_JEV` is a session override both ways (`1` on, any other value off) and callers no longer force it; absent, jev stays on and the probe asks `needs_answer: enabled` once; hooks see only the project layer)*
- [x] **JEV-08**: jev-fast-decision's SKILL.md replaces "Required reading" with "read X when Y" pointers: when
  designing a new item shape, meeting a new TypeSafe feature or a capability fact that looks stale, read the
  official `typesafe:typesafe-ai` skill's doc flow when it is installed (otherwise start at the docs index, then the
  changelog and the models page). The stale Jev 1.14 facts are refreshed (`jev-latest` is `jev-1.14.0`), receipts
  record the versioned model id that answered rather than the alias, and ai-kit never installs the official skill
  (ai-kit installs only its own skills, DIST-07); a doc-contract test pins the pointers. *(added 2026-11-07, owner
  decision from the jev and typesafe-ai research)*
- [x] **JEV-09**: jev-fast-decision's reference.md has a "Writing an item" section that adopts TypeSafe's question
  rules for an agent's own decisions: ask an observable judgment and let the agent decide; never ask about
  arithmetic, counting, dates or durations, or with double negatives; re-ask a close choice with the options
  reordered; give a choice a no-match option; run a cheap yes/no screen before an expensive step. A doc-contract test
  pins each rule. *(added 2026-11-07, owner decision from the jev and typesafe-ai research)*
- [x] **JEV-10**: jev's probe reads Laya's `/health` body and `/openapi.json`, caches them for 24 hours or until a
  checkpoint revision changes, compares them with a recorded known-features list and warns on each difference,
  without ever upgrading a capability cell to verified; the package version is labelled not exposed. An on-demand
  `--check-updates`, cached for 7 days and never run on a normal call, follows the official skill's doc flow and
  PyPI with public requests only (no key, no question) and lists each fact to re-verify. Tests use fake servers.
  *(added 2026-11-07, owner decision from the jev and typesafe-ai research)* *(amended 2026-11-14, owner decision:
  the probe determines the version at the configured address — server field, then `[jev] laya_version`, then
  "not exposed" with a server fingerprint — and when that version's capabilities are unknown it fetches Laya's
  published notes (PyPI, README) once and records them; a record stays valid until the version or fingerprint
  changes, replacing the fixed 24-hour and 7-day caches; `--check-updates` stays as the on-demand refresh)* *(amended 2026-11-15, Phase 34 plans: when Laya has unloaded its checkpoints the probe reuses the last recorded fingerprint with the same OpenAPI part; a probe under a deadline (hooks, detect) never fetches)*
- [x] **JEV-11**: Two decision-path records: Laya's official MCP server stays outside jev's decision path, because it
  would bypass the one-item-per-call rule, the size guard, the thresholds, the receipts and the answer log; and a
  spike records whether several questions over one shared state answer better on TypeSafe than the merged contexts
  jev sends today. *(added 2026-11-07, owner decision from the jev and typesafe-ai research)*
- [x] **JEV-12**: When the remote TypeSafe backend answers with a model id the skill has not recorded, or a
  primitive or option it does not know, the skill follows the official skill's doc flow once (`llms.txt`,
  `changelog.md`, `models.md`) and records what changed and which of its features it could serve; public
  requests only, never on the answer path. *(added 2026-11-14, owner decision: learn from `typesafe-ai`'s remote
  usage)*
- [x] **JEV-13**: A guard test keeps Zen and any other removed backend out of jev-fast-decision and fails on a
  step that hands Laya's or the official skill's install or upgrade to tools-installer or another repository.
  *(added 2026-11-14, owner decision)*

### Features and live checks

- [x] **FEAT-01**: The config doctor is reachable from the setup wizard, reusing the existing engine and screen. *(amended 2026-11-03, 30.1 spec: `d` on Done opens the doctor screen, one class shared with `--config-doctor`; every doctor apply refuses a file it cannot parse and backs the file up first, keeping the last 10 backups per file)*
- [ ] **FEAT-02**: The pinned Cursor subagents link per file (never a directory) into a project's `.cursor/agents`
  with a `--skills`-style selection (`all` or names; an unknown name exits 1 naming it); a link never overwrites a
  non-ai-kit file and removal touches only ai-kit's own links; docs say where the agents are linked and why not
  `~/.cursor/agents`; Cursor's built-in explore subagent model knob is checked and recorded; and the owner confirms
  one run as non-fast in the Cursor usage dashboard.
- [ ] **FEAT-03**: The agent-run live checks (real wake resume, wake during a GSD prompt, pointer form in a real
  session, native-execution wording, done-when wording, quota-checked task, chain without a decision backend, pi
  model-name grammar, background permission mode, launch-and-wait for opencode and pi, large-roadmap detection) run
  with herdr and a scratch home and are recorded.
- [ ] **FEAT-04**: The owner-attended live checks run and are recorded, each flipping or keeping its unverified
  label: at the next real Claude usage limit, the captured payload, the limit's output channel under `claude -p`,
  and whether the wake's headless resume exits or hangs while the limit is active; reboot survival of the persistent
  wake and of notices with linger on; the Cursor status line after a Cursor login; the Phase 21.2 PreCompact live
  delivery and measurement; the Phase 21.3 advisory-hook matrix on opencode; optionally the Phase 22 pi steering
  arms. *(amended 2026-11-03, 30.1 D-20: plus whether `env.PLAYWRIGHT_MCP_EXECUTABLE_PATH` in `~/.claude/settings.json` reaches the Playwright plugin's MCP process, and whether a headed launch through the flatpak Chrome wrapper works)*
- [ ] **FEAT-05**: The owner decides whether each of the two June ideas is ported or dropped: external status-line
  segments, and the loop-polish branch's icon and install flag. The evidence is each archived branch's diff against
  the split status line; the decision is recorded in Phase 54, and a port lands on the split status line with tests.
- [x] **FEAT-06**: The owner decides whether the config doctor gets a row for the Playwright MCP Chrome path. The
  evidence is the backlog 999.1 note and where the Playwright MCP looks for Chrome in a scratch home; the decision
  is recorded in Phase 30.1, and an added row uses the existing engine and its confidence labels. *(amended 2026-11-03, 30.1 spec: decided — a Claude row reports the plugin's missing default Chrome (`/opt/google/chrome/chrome`) and whether `env.PLAYWRIGHT_MCP_EXECUTABLE_PATH` is set and exists; its apply writes `/var/lib/flatpak/exports/bin/com.google.Chrome` there in `~/.claude/settings.json` through the doctor's atomic writer with a backup; the variable reaching the MCP process and a headed launch stay inferred until Phase 54)*

### Design rule

- [x] **DESIGN-01**: ai-kit's own AGENTS.md states the owner's design rule: Simple is not the same as easy. Prefer the simple design over the complex one, but never recommend the
  easier option when it gives the user less value only to skip a few steps that are not hard, and never ship
  a half-done feature or mediocre value to keep a change small. Ponytail decides how the code is built (reuse the
  components and helpers that already exist and well-known design patterns before writing anything from scratch,
  with no speculative abstraction), not how much of the feature ships; MVP mode only shifts
  the weight toward simplicity and never allows a half-done feature; when jev is present it classifies the
  options against these criteria. The ponytail lenses
  wired by LENS-01 and the review lenses of REV-03 are briefed with it, and a doc-contract test pins its text.
- [ ] **DESIGN-02**: The top rules that `ai-kit-project-rules` generates for a target project carry the same rule,
  so GSD and superpowers agents in that project read it before planning or review; the line points to a decisions
  runbook that holds the details.

### Lens skills

- [x] **LENS-01**: ai-kit's own GSD config wires lens skills to GSD agents through the project's `gsd-tools`:
  `impeccable` to the UI researcher, UI checker and UI auditor (for hierarchy, color, copy and accessibility of
  the TUI; its web code guidance does not apply), `ponytail` to the planner and plan checker, and `ponytail-review`
  to the code reviewer. Skills are named as `global:` entries (plugin skills as `global:<plugin>:<skill>`), never
  an absolute path, and UI review is on because ai-kit ships a TUI. An agent whose lens is missing runs without it
  and says so, and ponytail's smallest-change bias yields to the design rule (DESIGN-01).
  *(amended 2026-11-03, 30 spec: `global:impeccable` resolves on this machine only with `agent_skills_security.trusted_global_roots` holding `~/.agents/skills`, set through gsd-tools; GSD emits plugin lenses without an existence check, so the agent itself names a lens it could not load)*
- [ ] **LENS-02**: In the superpowers flow, the code review after execution loads `ponytail-review`, and
  `impeccable` when the diff touches UI, from the shared role-keyed table, on the same lanes as spec review; a
  missing lens is skipped with a note.
- [ ] **LENS-03**: curated-config proposes the same lens wiring for a target project from the skills actually
  present (`impeccable` only for UI projects, plugin skills only on runtimes that can load them), and run on
  ai-kit itself it proposes no change to the wiring LENS-01 set.

### Setup wizard

- [x] **WIZ-01**: The wizard's first screen splits components into one card per kind (skills, agents, commands,
  hooks), each card shown only when that kind has something to install, so adding more kinds does not crowd
  one list. *(amended 2026-11-03, 30.1 D-01: the cards are tabs, one card on screen, ←→ switches kind)* *(amended 2026-11-07, owner request, 2acf64f: no tabs; each kind is its own screen, Enter goes to the next card and Esc to the previous one, and the header counts "Step x of N" over the kind cards, Arrange when a host is detected, and Review)*
- [x] **WIZ-02**: The Claude status-line pane keeps today's layout with an orange accent background and the words
  "Claude Code" in bold.
- [x] **WIZ-03**: The Cursor status-line pane uses a gray accent and an on/off toggle: off keeps Cursor's own
  default status line (removing ai-kit's entry if setup had wired it), on wires ai-kit's. *(amended 2026-11-03, 30.1 spec: the toggle is on both host panes and replaces the yes/no gate; it starts at what is wired now; off removes whatever entry is wired, ai-kit's or another tool's, so the host default shows — a foreign one only after it is shown, backed up and confirmed; on wires ai-kit's, keeping today's replace confirmation for a foreign entry)* *(amended 2026-11-06, owner decision, 30.1 D-06: another tool's entry gets three states on its pane: keep current (the default; nothing written), remove so the host shows its own built-in default ("the default that Claude shows when it has no status line", the owner's clarification), or customize with ai-kit, starting from ai-kit's default arrangement; the last two only after it is shown, backed up and confirmed)*
- [x] **WIZ-04**: The Cursor status line matches Claude's on the aspects the hosts share, starting from the Cursor
  status-line proof of concept as the visual reference: every Cursor segment shows its icon in the real render
  and the wizard preview (the five shared segments `path`, `git_dirty`, `model`, `alt_time_ago`,
  `alt_term_dimensions` with the same icon on both hosts); a Cursor process-memory segment uses Claude's
  calculation, finding the Cursor CLI process by its program path and labelled unverified until a live Cursor
  session confirms it; the quota segments use Claude's ramp and window format wherever Cursor's data allows, each
  real data difference flagged visibly, never faked; `alt_term_dimensions` never shows a 0 row count. *(amended 2026-11-03, 30.2 SPEC and discuss: the process is found by its command line or program path; an extra-spend alert is set from the wizard with a toggle and a threshold; with the Cursor CLI installed an owner-attended live run from the branch tip closes Phase 23's S7, otherwise a labelled sample-data render stands in, and nothing installs Cursor)* *(amended 2026-11-06, owner answers: the alert threshold defaults to the spend limit already set on Cursor's platform, read from ai-kit's Cursor quota cache and labelled inferred; the wizard shows it read-only with an optional override, and with no limit and no override there is no alert; the live Cursor run is an orchestrator step at verification)* *(amended 2026-11-07, owner request, 8e23e75: the override is removed; the alert always fires at the spend limit read from Cursor, the wizard keeps only the alert on/off toggle beside that limit, and an older stored override is ignored and dropped on the next write)* *(rewritten 2026-11-03, 30.1 spec: the owner's complaint was the Cursor preview not matching Claude's, not disabled chips — the old wording, absent unshowable segments and switched-off ones in the tray, already holds in code; moved to Phase 30.2)*
- [x] **WIZ-05**: The wizard's status-line board preview is a real render through each host's own renderer and
  sample payload, at the preview panel's width, titled with the host on screen; the tray title does not call
  switched-off segments disabled. *(added 2026-11-03, 30.1 spec)*

### Defects and housekeeping

- [x] **DEF-01**: The small known defects are fixed: wake and cross-ai skills missing from pi's install, the
  nonexistent pi environment variables in the interactive guide, the Phase 25.1 edge floor, goal-prompt detect with
  file indirection, a stale routing docstring, a drift test between hand-copied runtime lists and the runtime
  table, and the AGENTS.md link to a gitignored file (seven items; the path-length test and the no-git e2e test
  belong to GATE-03). *(amended 2026-11-03, 31 spec: the pi-install item has two causes, both fixed portably —
  link targets and the kit dir are compared after resolving both, so an alias spelling of the same folder is never
  foreign, and `setup.py` run from a checkout uses that checkout unless `AI_KIT_DIR` is set; the pi variables item
  is reworded — pi 1.3.0 sets `PI_PROVIDER` and `PI_MODEL` only for the agent's own bash-tool commands, so the fix
  is the wording plus a herdr live check; the edge-floor item fixes 25.1 and adds a current-milestone guard)*
- [x] **DEF-02**: One shared secret-shape scanner with more key shapes replaces the four copies. *(amended
  2026-11-13, 32.3 spec: live search finds five shipped key-shape scanners, not four — the runner template's
  `redactSecrets`, session-wake's `reset_parse.redact`, goal-prompt's `scan_text`, jev-fast-decision's ladder item
  guard (the fourth) and commit-fold's GitHub-token redactor — plus the curated-config eval test helper; all six take
  their key shapes from the one shared scanner, which holds distinctive token shapes only, while each caller keeps its
  own broad rules; a guard test fails on a drifted copy or a new key-shape list (32.3 SPEC R1-R5))*
- [x] **DEF-03**: goal-prompt wraps long lists and commands instead of refusing them.
- [x] **DEF-04**: The eight spec-discuss polish items are fixed, each with a pinned doc-contract test: a forced
  local answer that matches no decision-table row; "one commit per phase" against the spec workflow's own commit;
  the analyzer starting while the same phase's CONTEXT is being written; `state.record-session` on an early stop;
  trigger keywords late in the description; the agent's action on `no_client` and `incompatible_client`; analyze
  mode's trade-off output written as one header per option with pros and cons bullets instead of a table; and each
  interactive decision question starting with one line per item saying what it is and who uses it.
- [ ] **DEF-05**: Housekeeping: the six todos v1.3 delivered are closed, the two unneeded tags dropped
  (`archive/worktree-agent-af8d0e0c2da92634f` and `archive/fix/8.1-status-line-rate-burn-pace`, with consent), the
  stale archived wording decided, Windows ledger entry 7 waived, and the v1.3 tag pushed with the owner's consent;
  the remaining archive tags (the Cursor proof-of-concept and host-split spec tags, and five older tags never
  discussed) are kept or dropped by recorded decision.
- [x] **DEF-06**: spec-discuss derives the run-mode recommendation (interactive unless the mode is yolo or MVP
  is active) before it builds the question, lists that option first and labels it `(Recommended)`; a remembered
  past choice may be mentioned in an option's text but never reorders the options. A doc-contract test pins it.
- [x] **DEF-07**: spec-discuss documents running each phase in its own subagent on the interactive path: the
  subagent verifies facts, drafts, and spawns the analyzer as a real subagent (hosts that nest subagents, such
  as Claude Code, verified 2026-11-03); because a subagent cannot ask the user, it stops with the owner's
  questions in batches of 2-5 (recommended option first, trade-offs as headers and bullets), the orchestrator
  asks them and resumes the same subagent with the answers. Hosts without nested subagents run the analyzer
  inline and say so.
- [x] **DEF-08**: Before an auto-mode run starts, spec-discuss shows the owner a short summary of every requested
  item in the range and how it plans to resolve each one, and waits for the owner's go-ahead before it runs; a
  doc-contract test pins it. *(added 2026-11-07, owner decision)*
- [x] **DEF-09**: No runtime label or docstring in spec-review's `detection.py` names a planning file (today
  `20-SMOKE-OPENCODE.md`, `21-SMOKE-CURSOR.md`, `20-SMOKE-CODEX.md`, one pinned by
  `tests/test_ai_kit_spec_runtimes_table.py`), and a test fails when a string literal in shipped skill Python code
  names a file under a planning folder; Phase 32's history-text check reads Markdown only. *(added 2026-11-07,
  Phase 32 close-out)* *(amended 2026-11-08, 32.2 D-05: the test also reads comments and covers every tracked
  skill Python file, the project-rules skills included; all 24 literal and 5 comment hits found by the live scan are
  fixed in Phase 32.2)*
- [x] **DEF-10**: curated-config's real-gsd-tools tracer test passes with `TMPDIR` inside a GSD project checkout:
  the behaviour for a new project nested inside another project is decided and tested, and the six-environment
  custom-tmpdir row keeps `.planning/` in its clone so it catches the case. *(added 2026-11-07, Phase 32
  close-out)* *(amended 2026-11-13, 32.4 D-15, D-16: live check: the custom-tmpdir row has no clone; its TMPDIR
  sits in a fresh `git init` repository, which gains a synthetic `.planning/`; the nested-project fix covers the v1
  `ensure-project` and the v2 inventory and apply, since gsd-tools resolves an empty nested folder to the outer
  project's config)*

### Code index

*(added 2026-11-14, owner decision: codebase-memory-mcp replaces codegraph; Phase 32.5)*

- [x] **IDX-01**: The unit flow's boundary step and `fold.py index` refresh the codebase-memory-mcp index of the checkout or worktree instead of running codegraph, and the unit brief names changed functions from it; a missing binary is reported once with its install command and the step still exits 0.
- [x] **IDX-02**: The tooling guidance for review and execute lanes names codebase-memory-mcp on every runtime: the MCP tools where the host registers it (Claude Code, opencode, pi, Codex, Copilot CLI, Cursor), the `codebase-memory-mcp cli <tool> '<json args>'` form otherwise. *(amended 2026-11-14, 32.5 research: codebase-memory-mcp 0.12.1 deprecates raw JSON arguments, so the CLI form is `codebase-memory-mcp cli <tool> --flag value`)*
- [x] **IDX-03**: spec-review's detection and spec-config's CLI preference read codebase-memory-mcp's registration and index state, with no auto-install and no global write; the codegraph probe is removed.
- [x] **IDX-04**: `make setup-dev`, the doctor, the global-rules writer, the tool advisor hook and the setup wizard check, recommend or write codebase-memory-mcp instead of codegraph, through the existing atomic writers.
- [x] **IDX-05**: The shared rules package and `ai-kit-project-rules-agents` generate their code-exploration rule with codebase-memory-mcp.
- [x] **IDX-06**: `AGENTS.md`, `README.md`, the run-book, every live SKILL.md and reference, the runner template comment, `.gitignore`, the live planning rows, pending todos and agent memory name codebase-memory-mcp; a `.cbmignore` keeps `.planning/` out of the index (owner, 2026-11-14).
- [x] **IDX-07**: History records keep their codegraph wording, graphify stays unchanged, and a backlog entry evaluates whether codebase-memory-mcp's document graph makes graphify redundant.

## Future Requirements

- Pace-gauge reaction (above 80 % used while the pace says the limit comes first, check for a reset every 10 %) and
  early-reset polling, after the shared quota-logic decision (WAKE-03).
- Codex interactive confirmation (backlog 999.6, secondary runtime).
- Extra stacks (Kotlin, .NET, PHP) and CI platforms for the rules skill.
- Optional status-line segment for cursor-agent memory.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Registering `workflow.cross_ai_retry` with gsd-core | Not a GSD key (gsd-core 1.18.0 rejects it); the setting moves into ai-kit's own config (CFG-03) |
| A separate cross-AI chain skill | The shared runner gains the options instead (RUN-01) |
| ai-kit execute or review of GSD plans | GSD's own execute and review lanes cover them; the GSD adapter is removed |
| CLAUDE.md and its variants as instruction files | AGENTS.md and AGENTS.local.md only (owner, 2026-11-02) |
| graphify as the agents' code-exploration tool | codegraph (replaced by codebase-memory-mcp in Phase 32.5) is better for code (verbatim source, call paths); graphify stays for GSD's document discovery (FLOW-06) |
| Windows support | Owner decision 2026-11-02 |
| rtk | Dropped by the owner; removed everywhere (RMV-04) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GATE-01 | Phase 28 | Complete |
| GATE-02 | Phase 28 | Complete |
| GATE-03 | Phase 28 | Complete |
| GATE-04 | Phase 28 | Complete |
| GATE-05 | Phase 28 | Complete |
| FLOW-01 | Phase 29 | Complete |
| FLOW-02 | Phase 29.1 | Complete |
| FLOW-03 | Phase 29.1 | Complete |
| FLOW-04 | Phase 30 | Complete |
| FLOW-05 | Phase 29.1 | Complete |
| FLOW-06 | Phase 30 | Complete |
| FLOW-07 | Phase 29.1 | Complete |
| FLOW-08 | Phase 32.4 | Complete |
| FLOW-09 | Phase 32.4 | Complete |
| FLOW-10 | Phase 29.1 | Complete |
| FLOW-11 | Phase 29.1 | Complete |
| FLOW-12 | Phase 30 | Complete |
| FLOW-13 | Phase 30 | Complete |
| FLOW-14 | Phase 47.2 | Pending |
| RMV-01 | Phase 31 | Complete |
| RMV-02 | Phase 31 | Complete |
| RMV-03 | Phase 31 | Complete |
| RMV-04 | Phase 31 | Complete |
| JDG-01 | Phase 32 | Complete |
| JDG-02 | Phase 32 | Complete |
| JDG-03 | Phase 32.4 | Complete |
| JDG-04 | Phase 31, Phase 32 | Pending |
| JDG-05 | Phase 32 | Complete |
| JDG-06 | Phase 32 | Complete |
| JDG-07 | Phase 32 | Complete |
| JDG-08 | Phase 32 | Complete |
| CFG-01 | Phase 33 | Complete |
| CFG-02 | Phase 33 | Complete |
| CFG-03 | Phase 33 | Complete |
| CFG-04 | Phase 33 | Complete |
| CFG-05 | Phase 33 | Complete |
| CFG-06 | Phase 33 | Complete |
| HUB-01 | Phase 36 | Complete |
| HUB-02 | Phase 35 | Complete |
| HUB-03 | Phase 35 | Complete |
| HUB-04 | Phase 32.2 | Complete |
| HUB-05 | Phase 36 | Complete |
| HUB-06 | Phase 35 | Complete |
| HUB-07 | Phase 36 | Complete |
| HUB-08 | Phase 35 | Complete |
| HUB-09 | Phase 35 | Complete |
| HUB-10 | Phase 36 | Complete |
| REV-01 | Phase 40 | Pending |
| REV-02 | Phase 40 | Pending |
| REV-03 | Phase 39 | Pending |
| REV-04 | Phase 39 | Pending |
| REV-05 | Phase 39 | Pending |
| REV-06 | Phase 40 | Pending |
| REV-07 | Phase 40 | Pending |
| REV-08 | Phase 40 | Pending |
| EXE-01 | Phase 41 | Pending |
| EXE-02 | Phase 42 | Pending |
| EXE-03 | Phase 42 | Pending |
| EXE-04 | Phase 41 | Pending |
| EXE-05 | Phase 41 | Pending |
| EXE-06 | Phase 42 | Pending |
| EXE-07 | Phase 42 | Pending |
| EXE-08 | Phase 41 | Pending |
| EXE-09 | Phase 41 | Pending |
| RUN-01 | Phase 37 | Complete |
| RUN-02 | Phase 37 | Complete |
| RUN-03 | Phase 38 | Pending |
| RUN-04 | Phase 38 | Pending |
| RUN-05 | Phase 38.1 | Pending |
| RUN-06 | Phase 37 | Complete |
| RUN-07 | Phase 38 | Complete |
| RUN-08 | Phase 38 | Pending |
| RUN-09 | Phase 38.1 | Pending |
| RUN-10 | Phase 38.1 | Pending |
| RUN-11 | Phase 38.1 | Pending |
| RUN-12 | Phase 37 | Complete |
| RUN-13 | Phase 38 | Pending |
| RUN-14 | Phase 38.1 | Pending |
| RUN-15 | Phase 39.1 | Pending |
| RULE-01 | Phase 45 | Pending |
| RULE-02 | Phase 45 | Pending |
| RULE-03 | Phase 45.1 | Pending |
| RULE-04 | Phase 45 | Pending |
| RULE-05 | Phase 46 | Pending |
| RULE-06 | Phase 47 | Pending |
| RULE-07 | Phase 46 | Pending |
| RULE-08 | Phase 46 | Pending |
| RULE-09 | Phase 46 | Pending |
| RULE-10 | Phase 45 | Pending |
| RULE-11 | Phase 45 | Pending |
| RULE-12 | Phase 45.1 | Pending |
| RULE-13 | Phase 45.1 | Pending |
| RULE-14 | Phase 45.1 | Pending |
| RULE-15 | Phase 45.1 | Pending |
| RULE-16 | Phase 46 | Pending |
| RULE-17 | Phase 47 | Pending |
| RULE-18 | Phase 47 | Pending |
| RULE-19 | Phase 47 | Pending |
| RULE-20 | Phase 47.1 | Pending |
| RULE-21 | Phase 47.1 | Pending |
| RULE-22 | Phase 47.1 | Pending |
| RULE-23 | Phase 47.1 | Pending |
| RULE-24 | Phase 45.1 | Pending |
| RULE-26 | Phase 45.1 | Pending |
| RULE-27 | Phase 45 | Pending |
| RULE-25 | Phase 46 | Pending |
| RULE-28 | Phase 47 | Pending |
| RULE-29 | Phase 47 | Pending |
| RULE-30 | Phase 47 | Pending |
| RULE-31 | Phase 47 | Pending |
| RULE-32 | Phase 45.1 | Pending |
| RULE-33 | Phase 45.1 | Pending |
| RULE-34 | Phase 46 | Pending |
| HOOK-01 | Phase 48 | Pending |
| HOOK-02 | Phase 49 | Pending |
| HOOK-03 | Phase 49 | Pending |
| HOOK-04 | Phase 48 | Pending |
| HOOK-05 | Phase 48 | Pending |
| HOOK-06 | Phase 48 | Pending |
| HOOK-07 | Phase 49 | Pending |
| WAKE-01 | Phase 50 | Pending |
| WAKE-02 | Phase 50 | Pending |
| WAKE-03 | Phase 47 | Pending |
| WAKE-04 | Phase 51 | Pending |
| WAKE-05 | Phase 51 | Pending |
| WAKE-06 | Phase 50 | Pending |
| CUR-01 | Phase 43 | Pending |
| CUR-02 | Phase 43 | Pending |
| CUR-03 | Phase 44 | Pending |
| CUR-04 | Phase 44 | Pending |
| CUR-05 | Phase 44 | Pending |
| CUR-06 | Phase 32.4 | Complete |
| CUR-07 | Phase 44 | Pending |
| CUR-08 | Phase 44 | Pending |
| CUR-09 | Phase 44 | Pending |
| CUR-10 | Phase 43 | Pending |
| DIST-01 | Phase 52 | Pending |
| DIST-02 | Phase 53 | Pending |
| DIST-03 | Phase 52 | Pending |
| DIST-04 | Phase 53 | Pending |
| DIST-05 | Phase 52 | Pending |
| DIST-06 | Phase 53 | Pending |
| DIST-07 | Phase 53 | Pending |
| DIST-08 | Phase 53 | Pending |
| DIST-09 | Phase 52 | Pending |
| ARCH-01 | Phase 52 | Pending |
| ARCH-02 | Phase 52 | Pending |
| JEV-01 | Phase 34 | Complete |
| JEV-02 | Phase 32.1 | Complete |
| JEV-03 | Phase 34 | Complete |
| JEV-04 | Phase 54 | Pending |
| JEV-05 | Phase 54 | Pending |
| JEV-06 | Phase 29 | Complete |
| JEV-07 | Phase 34 | Complete |
| JEV-08 | Phase 32.1 | Complete |
| JEV-09 | Phase 32.1 | Complete |
| JEV-10 | Phase 34 | Complete |
| JEV-11 | Phase 34 | Complete |
| JEV-12 | Phase 34 | Complete |
| JEV-13 | Phase 34 | Complete |
| FEAT-01 | Phase 30.1 | Complete |
| FEAT-02 | Phase 54 | Pending |
| FEAT-03 | Phase 54 | Pending |
| FEAT-04 | Phase 54 | Pending |
| FEAT-05 | Phase 54 | Pending |
| FEAT-06 | Phase 30.1 | Complete |
| DESIGN-01 | Phase 30 | Complete |
| DESIGN-02 | Phase 45.1 | Pending |
| LENS-01 | Phase 30 | Complete |
| LENS-02 | Phase 42 | Pending |
| LENS-03 | Phase 44 | Pending |
| WIZ-01 | Phase 30.1 | Complete |
| WIZ-02 | Phase 30.1 | Complete |
| WIZ-03 | Phase 30.1 | Complete |
| WIZ-04 | Phase 30.2 | Complete |
| WIZ-05 | Phase 30.1 | Complete |
| DEF-01 | Phase 31 | Complete |
| DEF-02 | Phase 32.3 | Complete |
| DEF-03 | Phase 32.4 | Complete |
| DEF-04 | Phase 32.4 | Complete |
| DEF-05 | Phase 54 | Pending |
| DEF-06 | Phase 32.4 | Complete |
| DEF-07 | Phase 32.4 | Complete |
| DEF-08 | Phase 32.4 | Complete |
| DEF-09 | Phase 32.2 | Complete |
| DEF-10 | Phase 32.4 | Complete |
| IDX-01 | Phase 32.5 | Complete |
| IDX-02 | Phase 32.5 | Complete |
| IDX-03 | Phase 32.5 | Complete |
| IDX-04 | Phase 32.5 | Complete |
| IDX-05 | Phase 32.5 | Complete |
| IDX-06 | Phase 32.5 | Complete |
| IDX-07 | Phase 32.5 | Complete |

**Coverage:**
- v2.0 requirements: 193 total *(193 after RUN-15, added 2026-11-19, owner decision, Phase 39.1: remove the grok runtime; 185 after RUN-12, added 2026-11-16, 37 D-22; 186 after RUN-13, added 2026-11-16, 38 D-25; 191 after FLOW-14, EXE-09, RUN-14, RULE-33 and RULE-34, added 2026-11-16, owner decisions: language rules, smart test selection, goal-prompt learned rails, free-lane pools; 192 after HUB-10, added 2026-11-16, 36 D-23: free-model data use)*
- Mapped to phases: 193
- Unmapped: 0

---
*Requirements defined: 2026-11-02*
*Last updated: 2026-11-03 after the ideas and rules audit: 41 new requirements (GATE-05, FLOW-07..09, JDG-08, HUB-08, REV-07, EXE-07..08, RUN-07..11, RULE-10..25, JEV-07, CUR-08..10, DIST-06..07, ARCH-01..02, FEAT-04..06), 38 amended, decimal phases 38.1, 45.1 and 47.1 split out; JDG-04 to Phase 32, RUN-05 to 38.1, RULE-03 and DESIGN-02 to 45.1*
*Amended 2026-11-03 by Phase 29's spec and discuss: FLOW-02, FLOW-03, FLOW-05 and FLOW-07 to the new Phase 29.1; FLOW-01 and RULE-17 amended; RULE-27 (Phase 45) and REV-08 (Phase 40) added.*
*Amended 2026-11-03 by Phase 29.1's spec: FLOW-02 and FLOW-03 amended; FLOW-10 (neutral unit contract) and FLOW-11 (hotfix path) added to Phase 29.1; FLOW-11 amended by its discuss (conflicts resolved before any restore).*
*Amended 2026-11-03 by Phase 30's spec: FLOW-04, FLOW-06, LENS-01, RULE-03, RULE-06 and JEV-04 amended; FLOW-12 (global codegraph (replaced by codebase-memory-mcp in Phase 32.5) sentence rewrite) added to Phase 30.*
*Amended 2026-11-03 by Phase 30's discuss: FLOW-13 (ai-kit's `setup-dev` installs the flow's tools) added to Phase 30; RULE-05 amended (coupling, Phase 46).*
*Amended 2026-11-03 by Phase 30.1's spec and discuss: WIZ-01, WIZ-03, FEAT-01, FEAT-04 and FEAT-06 amended; WIZ-04 rewritten as Cursor status-line parity and moved to the new Phase 30.2; WIZ-05 (real-render preview) added to Phase 30.1.*
*Amended 2026-11-04 by the owner rules audit (the owner's local memory compared with the requirements): RULE-14 (jev first) and RULE-18 (jev-first block with time rules, codegraph (replaced by codebase-memory-mcp in Phase 32.5) instruction and real-home guard in every brief) amended; RULE-30 (agent closes push and host-session verification items, through herdr for host sessions), RULE-31 (failed external runs: no silent harness switch, foreground probe) and RULE-32 (GSD-only settings rules) added.*
*Amended 2026-11-06 by the owner's decision on Phase 30.1's cycle-2 review: WIZ-03 amended (a foreign status line is kept, removed so the host shows its own default, or replaced by a customized ai-kit line).*
*Amended 2026-11-07 by the owner's decisions on the jev and typesafe-ai research and the skill-distribution fact sheet (`.planning/research/2026-11-07-*.md`): DEF-08 (Phase 32.4), JEV-08 and JEV-09 (Phase 32.1), JEV-10 and JEV-11 (Phase 34), DIST-08 (Phase 53) and DIST-09 (Phase 52) added; JDG-01, JDG-03, RULE-27, JEV-03, JEV-05, DIST-01, DIST-02, DIST-03 and DIST-04 amended.*
*Amended 2026-11-07 by Phase 32's spec and discuss: JDG-01 (the flat test layout and the scripts reading) and JDG-06 (the bar-boundary reading, confirmed by the owner 2026-11-07) amended; ROADMAP 32 criterion 8, 32.1-32.3 criterion 2 and 34 criterion 3 cite JDG-04; the stale `decide.py` anchors of 32.4 and 34 corrected.*
*Amended 2026-11-07 at Phase 32's close-out: DEF-09 (Phase 32.2) and DEF-10 (Phase 32.4) added; RULE-29 amended (move `/tmp` leftovers into `tmp/` under a no-delete host rule; replaces the plan-rail scope script).*
*Amended 2026-11-07 by Phase 32.1's spec and discuss (owner batch scope "Narrow"): JDG-03 and JDG-04 amended; ROADMAP goals and criteria 1-2 of 32.1-32.3, 32.1 criterion 5, 32.4's goal and criterion 4, and the JDG-04 criterion of Phases 37-40 amended; backlog 999.22 (headless installer agents) added.*
*Amended 2026-11-08 by Phase 32.2's spec and discuss: DEF-09 amended (the guard also reads comments and covers every skill's Python); ROADMAP 32.2's goal note and criterion 4 amended.*
*Amended 2026-11-13 by Phase 32.3's spec and discuss: DEF-02 amended (five shipped scanner copies plus the eval test helper, one shared token-shape scanner, a drift and new-copy guard); ROADMAP 32.3's code anchors and criterion 3 and Phase 47.1's code anchors amended.*
*Amended 2026-11-13 by Phase 32.4's spec and discuss: CUR-06 amended (only the v1 `apply-review` fixed effort write goes) and DEF-10 amended (no clone in the custom-tmpdir row; both curated-config write flows fixed); ROADMAP 32.4 criteria 3 and 9 amended.*
*Amended 2026-11-14 by Phase 32.5's plan: IDX-02 amended (the CLI form takes flags); every live row naming codegraph names codebase-memory-mcp on the same line (record rows keep their record with a replacement note; REV-04 names the new tool).*
*Amended 2026-11-16 by the owner's planning-docs pass: FLOW-14 (Phase 47.2, new inserted phase), EXE-09 (Phase 41), RUN-14 (Phase 38.1), RULE-33 (Phase 45.1), RULE-34 (Phase 46) and HUB-10 (Phase 36) added; HUB-05, REV-01, RULE-03 and RULE-24 amended (free-lane pools, language default, smart test selection). The free-lane pool decisions are PROVISIONAL and need owner confirmation.*
