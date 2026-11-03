# Phase 30: Phase-boundary index refresh, code-exploration rules and lens wiring — Specification

**Created:** 2026-11-03
**Ambiguity score:** 0.175 (gate: ≤ 0.20)
**Requirements:** 12 locked

## Goal

On every unit of planned work and in every new worktree, the codegraph index and the graphify graph are created or
refreshed automatically on the branch being worked on, and the next unit's researcher, planner and executor are
handed the previous unit's new, changed and removed symbols with the documents that mention them. Agents are told
one rule for which index to use and how to keep it fresh. ai-kit's GSD agents get their lens skills, and AGENTS.md
states the owner's design rule. ai-kit's setup rewrites codegraph's installer sentence in the global instruction files to that rule.

## Scope

The boundary step and the worktree step are **general**: they live in ai-kit's unit-flow engine (Phase 29.1) and
serve any project and any unit (a GSD phase, a superpowers plan, a later system through the unit contract). Four
requirements are **ai-kit dogfood**, each with its general counterpart: R6 (ai-kit's worktree hook; general
counterpart RULE-06, the worktree-created playbook, Phase 47), R7 (ai-kit's AGENTS.md, house rules and tool advisor;
general counterpart RULE-03, the generated top rules, Phase 45.1), R9 (ai-kit's lens wiring; general counterpart
LENS-03, Phase 44) and R10 (ai-kit's design rule; general counterpart DESIGN-02, Phase 45.1). The fixture tests use
temporary projects and scratch HOMEs, never ai-kit's own repo.

**Terms used below.**
- **Unit**, **checkpoint**, **stack**: as defined in the Phase 29.1 SPEC.
- **Previous unit**: the unit directly below this one in the stack record, or, when it has already merged, the most
  recently merged unit the record still knows.
- **Boundary step**: the refresh-and-brief step of R1.
- **Index refresh**: R2 (codegraph) plus R3 (graphify) for one checkout.

## Background

Live-verified on 2026-11-03 in the ai-kit checkout (scratch copies of HEAD, scratch HOMEs,
`AI_KIT_REFUSE_REAL_HOME=1`; probes and notes under the gitignored `tmp/p30/`):

- **codegraph 1.6.2.** `codegraph sync .` took 0.23 s on an up-to-date index; `codegraph init -y` built a fresh copy
  of ai-kit in 12.5 s. `status --json` reports `reindexRecommended` (true today: index built with 1.6.0, extraction
  version 25 against 27) and `worktreeMismatch`. It indexes 391 files and no Markdown. A worktree under
  `.claude/worktrees/<name>` (where GSD and Claude put worktrees) silently resolves the main checkout's index until
  it has its own `.codegraph/`, so symbols that exist only in the worktree are invisible to its agents. codegraph's
  git sync hooks (`post-commit`, `post-merge`, `post-checkout`) are opt-in and offered only when its live file
  watcher is disabled (for example WSL `/mnt` drives); here the watcher runs and no codegraph git hook is installed.
  codegraph writes its own `.codegraph/.gitignore`.
- **graphify 0.9.54.** There is no `/graphify build`: bare `/graphify` runs the full pipeline (LLM extraction through
  subagents), `/graphify <path> --update` the incremental one, and the CLI's `graphify update .` is AST-only with no
  LLM. Searching is `graphify query "<question>"`, `path`, `explain` and `affected`; there is no `search` command. A
  root `.graphifyignore` holding `.planning/milestones/` is honored by `graphify update .`: nodes 34,798 → 21,167,
  Markdown nodes 17,696 → 4,207, archived-milestone nodes 13,623 → 0, 21 s → 15 s; an existing full graph shrinks on
  a plain update (no `--force`). graphify writes no `.gitignore` for `graphify-out/`.
- **GSD's graph (gsd-core 1.18.0).** `/gsd-graphify build` runs `graphify update .` and copies `graph.json`,
  `graph.html` and `GRAPH_REPORT.md` into `.planning/graphs/`. Its auto-update hook (`.claude/hooks/gsd-graphify-update.sh`,
  a Claude PostToolUse hook) does the same, but only on the default branch and only for `git commit|merge|pull|rebase
  --continue|cherry-pick` or a literal `gsd-tools query commit`: it skips `node …/gsd-tools.cjs query commit`,
  `gsd_run query commit` and `git update-ref` (the Phase 29 fold). `gsd-tools graphify status` shows the graph 3
  commits behind main with auto-update on. The phase researcher and the planner query the graph whenever it exists
  (intel is not needed; `intel.enabled` is unset in ai-kit) and treat it as stale only by age (24 h) or a running or
  failed auto-build, never by commits behind.
- **GSD hook points.** `transition.md` dispatches no hook. Rendered points: `discuss:pre/post`, `plan:pre/post`,
  `execute:wave:pre/post`, `execute:post`, `verify:pre/post`, `ship:pre/post`. `git worktree add` runs the
  `post-checkout` hook under GSD's default 10 s git timeout (`bin/lib/worktree-safety.cjs`).
- **Lens names (`query agent-skills`, scratch config).** `global:impeccable` resolves when it is a real folder under
  `~/.claude/skills`; on this machine it is a symlink into `~/.agents/skills`, and GSD skips it ("failed path check
  (symlink escape?)") unless `agent_skills_security.trusted_global_roots` holds `~/.agents/skills`, which then
  resolves it with a NOTE line. A missing bare skill leaves the block empty with `reason: configured_unresolved` and
  a stderr warning only the orchestrator sees. `global:ponytail:ponytail` and `global:ponytail:ponytail-review` are
  emitted as Skill-tool directives on the claude runtime with no existence check. `config-set` accepts
  `agent_skills.<agent>`, `agent_skills_security.trusted_global_roots` and `workflow.ui_review` (absent today; GSD's
  default is true when absent).
- **Rules today.** AGENTS.md Code Exploration sends every code question to codegraph; the tool advisor
  (`tools/hooks/advisor_core.py`) advises only rg, bat, fd and sd and large reads, and names neither tool; house rules
  R07 (codegraph) and R08 (graphify "doc-aware indexing") live in
  `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py`. `.claude/` is wholly gitignored, so the
  `.claude/cli-environment.md` that AGENTS.md links is a local-only file. `.codegraph/`, `graphify-out/` and
  `.planning/graphs/` are ignored in ai-kit (`.gitignore` lines 9-11); no requirement gives target projects those
  entries. No `docs/run-book/` exists yet.
- **The owner's global Claude file** carries a block written by codegraph's installer: "If there is no `.codegraph/`
  directory, skip CodeGraph entirely — indexing is the user's decision." The owner did not write it and wants the
  opposite (index automatically when the CLI is present).
- **Where codegraph's installer writes that block** (codegraph 1.6.2 source, `installer/instructions-template.js` and
  `installer/targets/`): a marker-fenced section `<!-- CODEGRAPH_START -->` … `<!-- CODEGRAPH_END -->`, upserted on
  every `codegraph install` (replace-or-append of the whole section), into four global files: Claude
  `~/.claude/CLAUDE.md` (`CLAUDE_CONFIG_DIR` overrides the folder), Codex `$CODEX_HOME/AGENTS.md` (default
  `~/.codex/`), Gemini `~/.gemini/GEMINI.md` (shared with the Antigravity IDE) and opencode
  `${XDG_CONFIG_HOME:-~/.config}/opencode/AGENTS.md`. Cursor's rule file and Kiro's steering file carry other text
  without that sentence. On this machine all four files hold the block and the sentence once each (counted, not
  printed). The codegraph CLI itself prints the same policy when no index exists ("If you are an AI agent: continue
  with your usual tools; indexing is the user's decision, do not run it yourself"); that message is in the binary and
  cannot be rewritten.
- **The exact commands** (scratch repo): `codegraph init -y` creates an index non-interactively and is a silent no-op
  on an existing one; `codegraph status --json` reports `pendingChanges` (`added`, `modified`, `removed`), non-zero
  after an edit and zero after `codegraph sync`; `codegraph index` rebuilds in full.
- **ai-kit's setup** (`tools/setup.py`) has a wizard path, a headless path, `--dry-run`, and the config doctor
  (`tools/config_doctor_checks.py`, `config_doctor_appliers.py`, labeled rows); its JSON writers
  (`_read_json_checked`, `_atomic_write_json`) are atomic. JEV-04 (Phase 54) plans a jev marker block in "the four
  global instruction files" through the same writers.

## Requirements

1. **The boundary step runs at three points of every unit, on the unit's own branch**: unit start, before the unit's
   planning, and before its first execution wave.
   - Current: no step exists; GSD's auto-update rebuilds only on the default branch, and nothing refreshes codegraph.
   - Target: the unit-flow engine runs the index refresh (R2, R3) and writes the brief (R4) at each of the three
     points, in the checkout and on the branch the unit works on, with no commit to main needed. For GSD the points
     are the flow's start, `plan:pre` and `execute:wave:pre` of wave 1; for superpowers, the adapter's start, before
     its plan is written, and before the first task. Each run reports what it refreshed, skipped and why.
   - Acceptance: in a GSD fixture and a superpowers fixture, a unit stacked on a previous unit that added a function
     gets, at each point, a fresh codegraph index and graph built at the unit branch's HEAD (`codegraph status` and
     `gsd-tools graphify status` agree with HEAD) and a brief naming that function; no commit lands on main.
   - Scope: general.

2. **codegraph is created or refreshed automatically whenever its CLI is installed**: no question, no stored setting.
   - Current: indexing is manual; a checkout without `.codegraph/` is skipped.
   - Target: with `codegraph` on PATH, a checkout with no `.codegraph/` of its own gets `codegraph init -y`; one whose
     `status --json` reports `reindexRecommended` gets `codegraph index`; any other gets `codegraph sync`. Without the
     CLI, one line names the command that would have run, and the step continues.
   - Acceptance: fixtures for each case (no index, reindex recommended, current, CLI missing) run the expected command
     through a fake that records argv, and the CLI-missing case prints the one line and exits 0.
   - Scope: general.

3. **graphify is refreshed with archived milestones excluded, and GSD's copy kept current**.
   - Current: no `.graphifyignore`; the graph carries 13,623 archived-milestone nodes; `.planning/graphs/` lags.
   - Target: a committed root `.graphifyignore` excludes `.planning/milestones/`; with `graphify` on PATH the step runs
     `graphify update .`, and in a GSD project with `graphify.enabled` it copies the outputs into `.planning/graphs/`
     and writes `.last-build-status.json` with the built HEAD, as `/gsd-graphify build` does. Without the CLI, one line
     names what would have run, and the step continues. The graphify flags stay on.
   - Acceptance: in a fixture copy of ai-kit, the built graph has zero nodes under `.planning/milestones/`;
     `gsd-tools graphify status` reports `built_at_commit` equal to HEAD and `stale: false`; a fixture with no
     `graphify` prints the one line and exits 0.
   - Scope: general.
   - *Amended 2026-11-03 (30 D-16):* owner rule — the step first detects whether the project is a GSD project, reusing ai-kit's
     existing detection (the `.planning/PROJECT.md` marker of `skills/ai-kit-spec-execute/detect_framework.py`, plus
     `.planning/config.json` or a resolvable project gsd-tools). A non-GSD project keeps the graph in `graphify-out/`
     only: no copy, and no `.planning/` folder is ever created; any agent (superpowers, a plain host session, another
     framework) queries `graphify-out/graph.json`. A GSD project keeps the single build in `graphify-out/` plus the
     copy and status file in `.planning/graphs/` (only when `graphify.enabled` is true), and agents may read either.
     The `.graphifyignore` entry for `.planning/milestones/` is written only in a GSD project. Acceptance adds: a
     non-GSD fixture (a superpowers project) ends with `graphify-out/graph.json` and no `.planning/` folder; a GSD
     fixture ends with both files from the same build. The same rule holds for the worktree hook (R6).

4. **The brief lists what the previous unit changed and the documents that mention it**.
   - Current: no brief; researchers find hook points through keyword-noisy graph queries.
   - Target: the brief names the previous unit, its commit range and its changed files (added, modified, removed),
     and tells each agent to run `codegraph_explore` on those files (the MCP tool, or `codegraph explore` in a shell
     for agents without MCP) to get their symbols, callers and blast radius. For the documents to update, the step
     runs `codegraph explore` on the changed files, takes the symbol names it returns plus the changed file names, and
     lists the tracked documents outside `.planning/` that mention them (whole-word plain-text search; a name found in
     more documents than a stated cap shows the count instead of the list). It says "mentions", never "describes".
     With no previous unit it says so; without the codegraph CLI the document search uses the file names only,
     labeled as such.
   - Acceptance: a fixture whose previous unit adds, changes and removes a file gets a brief with the range, the three
     files, the explore instruction, and the README and `SKILL.md` documents that mention a symbol or file name from
     them, with no `.planning/` file; a first unit on the trunk gets the "no previous unit" brief.
   - *Amended 2026-11-03 (30 D-08):* owner decision — no reading of codegraph's internal database and no symbol
     differ of ai-kit's own: the agents get symbols from `codegraph_explore` itself; the earlier wording (symbol name,
     kind and line from the index intersected with the diff) is superseded.
   - Scope: general.

5. **The next unit's researcher, planner and executor read the brief**.
   - Current: nothing hands them changed symbols.
   - Target: in GSD, the phase researcher's, planner's and executor's prompts carry the brief; in superpowers, the plan
     writer and every implementer brief the adapter builds carry it.
   - Acceptance: in the GSD fixture, the rendered researcher, planner and executor prompts contain the brief's path
     or content; in the superpowers fixture, every implementer brief does; with the brief removed, the prompts render
     and say no brief was found.
   - Scope: general.

6. **A new worktree is indexed automatically in ai-kit**: codegraph and graphify, without blocking git.
   - Current: a new worktree under `.claude/worktrees/` borrows the main checkout's codegraph index and has no graph.
   - Target: in ai-kit, creating a worktree (`git worktree add`, GSD's executor worktrees, a host's isolated agent)
     starts the index refresh (R2, R3) for that worktree in the background; the git command returns at once; at most
     one indexing job runs per repository at a time, codegraph before graphify; a missing CLI prints one line.
   - Acceptance: a fixture repo with ai-kit's hook installed creates two worktrees at once; each `git worktree add`
     returns in under 1 s; afterwards each worktree's `codegraph status` shows its own index with no
     `worktreeMismatch` and its own graph exists; the recorded job log never shows two indexing jobs overlapping.
   - Scope: ai-kit dogfood (general counterpart: RULE-06, Phase 47, amended).
   - *Amended 2026-11-03 (30 D-03):* resilience — the `post-checkout` hook is one trigger, not the only
     one: the unit's `start` and every boundary point also initialize or sync a checkout whose `.codegraph/` is
     missing or stale (R2), and the tool-use rule (R7) tells any agent, including an executor in a worktree whose hook
     never fired (an old clone, hooks not installed), to run `codegraph init -y` or `codegraph sync` before exploring.
     Acceptance adds: a worktree created with hooks uninstalled is indexed at the next boundary point.

7. **One tool-use rule in AGENTS.md, the house rules and the tool advisor**.
   - Current: AGENTS.md sends every code question to codegraph; R07 and R08 are one-liners; the advisor names neither
     tool.
   - Target: one rule text says: explore code with codegraph first (`codegraph_explore`, or `codegraph explore` in a
     shell); search Markdown with rg; use graphify and `/gsd-graphify` for documents and planning next to code; index
     and sync automatically whenever the CLI is present (this overrides any "skip, the user decides" wording an
     installer wrote elsewhere); how to build and refresh each (`codegraph init`/`sync`/`index`, `graphify update .`,
     `/gsd-graphify build`); that on stacked branches with no local merges GSD's auto-update never fires, so the
     indexes go stale unless refreshed; and that the index is refreshed before GSD research. AGENTS.md Code
     Exploration carries it, R07 and R08 carry its short form, and the advisor gives a short form when a text search
     runs over code in a codegraph-indexed checkout.
   - *Amended 2026-11-03 (30 D-16):* the rule says to query `graphify-out/graph.json` in a non-GSD project and that a GSD
     project has the same graph in both places.
   - *Amended 2026-11-03 (30 D-12):* the rule also says that GSD's agents read the graph from
     `.planning/graphs/`, that raw graphify queries reach it with `--graph .planning/graphs/graph.json`, and that one
     `graphify update .` build feeds both (`update` takes no `--graph`, verified: "unknown update option"); the advisor
     covers Claude's built-in Grep and Glob as well as shell searches (D-09).
   - Acceptance: a doc-contract test pins each clause in AGENTS.md and fails when one is removed; the house-rules
     tests show the new R07 and R08 summaries; advisor fixtures give the advice for an rg or grep over code in an
     indexed checkout and none for a Markdown-only search or an unindexed checkout.
   - Scope: ai-kit dogfood (general counterpart: RULE-03, Phase 45.1, amended).

8. **A runbook says how to build and refresh the graph**: `docs/run-book/graphify.md`.
   - Current: only `.claude/cli-environment.md`'s local, untracked two-line note.
   - Target: the runbook says how to build the graph (`graphify update .` with the `.graphifyignore`, `/gsd-graphify
     build` and where it writes), when it refreshes (the three boundary points, every new worktree, and GSD's
     auto-update after commits on the default branch, with the commit forms it misses), how to check freshness
     (`gsd-tools graphify status`, `built_at_commit` against HEAD), and how to query (`graphify query`, `path`,
     `explain`, `affected`). AGENTS.md links it.
   - Acceptance: a doc-contract test pins those sections and the link from AGENTS.md.
   - *Amended 2026-11-03 (30 D-12):* the runbook says that `graphify-out/` (raw graphify) and
     `.planning/graphs/` (GSD) are two locations fed by the same build and copy, and that `graphify update` cannot write
     to `.planning/graphs/` directly.
   - Scope: ai-kit dogfood.

9. **Lens skills are wired to ai-kit's GSD agents through gsd-tools**.
   - Current: `agent_skills` holds only the two jev entries; no trusted root; `workflow.ui_review` is absent.
   - Target: at execution time, through `gsd-tools config-set`: `global:impeccable` for the UI researcher, UI checker
     and UI auditor; `global:ponytail:ponytail` for the planner and plan checker; `global:ponytail:ponytail-review` for
     the code reviewer; `agent_skills_security.trusted_global_roots` holding `~/.agents/skills`; `workflow.ui_review`
     true. An agent whose lens is missing still runs and names the lens it could not load.
   - Acceptance: `gsd-tools query agent-skills` shows each lens for its agents with no warning on this machine; no
     entry is an absolute path; with a lens removed from a scratch HOME, the agent's prompt still renders and the text
     delivered with the lenses tells it to name the missing lens; `config-get workflow.ui_review` prints true.
   - Scope: ai-kit dogfood (general counterpart: LENS-03, Phase 44).

10. **AGENTS.md states the owner's design rule, and the lenses are briefed with it**.
    - Current: the rule lives only in REQUIREMENTS.md (DESIGN-01) and the milestone inputs.
    - Target: AGENTS.md carries DESIGN-01's wording: simple is not the same as easy; prefer the simple design over the
      complex one, but never recommend the easier option when it gives the user less value only to skip a few steps
      that are not hard, and never ship a half-done feature or mediocre value to keep a change small; ponytail decides
      how the code is built (reuse existing components, helpers and well-known design patterns before writing from
      scratch, with no speculative abstraction), not how much of the feature ships; MVP mode only shifts the weight
      toward simplicity and never allows a half-done feature; when jev is present it classifies the options against
      these criteria. The planner, plan checker and code reviewer receive it next to their ponytail lens.
    - Acceptance: a doc-contract test pins each clause and fails when one is removed; the text delivered with the
      ponytail lenses carries the rule or points to it.
    - Scope: ai-kit dogfood (general counterpart: DESIGN-02, Phase 45.1).

11. **ai-kit's setup rewrites codegraph's "user decides" sentence in every global instruction file that carries it**.
    - Current: four global files carry codegraph's "skip CodeGraph entirely — indexing is the user's decision", which
      contradicts R2 and R7; nothing changes it except a hand edit.
    - Target: during install, headless and in the wizard, `tools/setup.py` finds the `CODEGRAPH_START` … `CODEGRAPH_END`
      block in each of the four global files (Claude, Codex, Gemini, opencode, at the paths codegraph's installer
      resolves) and replaces only that sentence with ai-kit's: "If there is no `.codegraph/` directory and the
      `codegraph` CLI is installed, run `codegraph init -y` to create the index; if the index exists and `codegraph
      status --json` shows pending changes, run `codegraph sync` first (`codegraph index` when it reports a reindex is
      recommended)." It writes a backup first and then atomically; every other byte stays as it was; a second run
      changes nothing; `--dry-run` shows the change and writes nothing; a missing file, block or sentence is skipped
      with a one-line note. The config doctor reports a file whose block holds the installer's wording again (after a
      `codegraph install`), and the next install re-applies ai-kit's wording. The marked-block editor is one shared
      stdlib helper that Phase 54's jev block (JEV-04) reuses.
    - Acceptance: in a scratch HOME with synthetic copies of the four files (the block plus unrelated text around it),
      install rewrites only the sentence (the byte diff is that sentence alone), leaves a backup, and a second install
      gives no diff; `--dry-run` prints the change and leaves the files byte-identical; files without the block or the
      sentence are untouched with a note each; after the installer's block is written back, the doctor row reports the
      drift and install fixes it; no test touches the real files.
    - Scope: general (every host whose global file codegraph's installer writes).

12. **ai-kit's `make setup-dev` installs the tools the flow needs when they are missing**.
    - Current: ai-kit's Makefile has `setup-env` (`uv sync`) and `dev` (`setup-env` plus `pre-commit install`); no
      `setup-dev`; nothing installs codegraph, graphify, gh or gh-stack.
    - Target: `make setup-dev` runs `setup-env`, installs the pre-commit hooks including the `post-checkout` stage (R6),
      and installs each missing flow tool (the codegraph and graphify CLIs, pre-commit, gh, the gh-stack extension)
      through a guarded step: an already-installed tool is left alone, a tool that cannot install (no permission, no
      network, no package manager) is reported by name with the manual command, and the target still succeeds; the
      flow degrades without that tool (R2, R3 one-line notes; Phase 29.1's no-PR path), never fails. `dev` and
      `setup-env` keep working as aliases until Phase 46 settles the aliases (RULE-05).
    - Acceptance: in a scratch HOME with a PATH missing all five tools and fake installers, `make setup-dev` installs
      the four that can install, reports the one whose installer fails, and exits 0; a second run installs nothing;
      AGENTS.md Commands lists `setup-dev`.
    - Scope: ai-kit dogfood (general counterpart: RULE-05, Phase 46, amended).
    - *Amended 2026-11-03 (30 D-04):* added from the owner's answer: "Anything we create must be resilient, and the
      required tools should be installed by setup-dev."

## Boundaries

**In scope:**
- The boundary step in the unit-flow engine at its three points, for GSD and superpowers units (R1).
- Automatic codegraph creation and refresh, and graphify refresh with the committed `.graphifyignore` and GSD's copy
  (R2, R3).
- The changed-symbols brief and its delivery to the next unit's agents (R4, R5).
- ai-kit's worktree-created indexing hook (R6).
- The tool-use rule in AGENTS.md, house rules R07 and R08 and the tool advisor (R7); the graphify runbook (R8).
- ai-kit's lens wiring through gsd-tools (R9); the design rule in AGENTS.md and the lens briefing (R10).
- ai-kit's `make setup-dev` with guarded installs of the flow's tools (R12).
- The setup action that rewrites codegraph's sentence in the four global instruction files, its doctor drift row and the shared marked-block editor (R11).
- Amendments made now: FLOW-04, FLOW-06, LENS-01, RULE-03 and RULE-06 in REQUIREMENTS.md; FLOW-12 added and JEV-04 amended (R11, 2026-11-03); FLOW-13 added and RULE-05 amended (R12, 2026-11-03, 30 D-04); ROADMAP Phase 30 (criteria,
  anchors, judge bar); a coupling note in the Phase 29.1 CONTEXT.

**Out of scope:**
- The generated top rules and the worktree-created playbook for target projects — Phases 45.1 (RULE-03) and 47
  (RULE-06), amended now to carry this phase's rules and the ignore entries.
- curated-config proposing the lens wiring for other projects — Phase 44 (LENS-03).
- Session-hook indexing advice — Phase 49 (HOOK-03).
- Editing GSD's installed hook scripts or reporting their missed commit forms upstream — gsd-core is a project-local
  install that tools-installer updates; the runbook documents the gaps.
- Editing the owner's global Claude file by hand, or anything in it beyond the one sentence of R11 — the setup action is the only writer.
- The jev marker block itself — Phase 54 (JEV-04) reuses R11's editor.
- The message the codegraph binary prints when no index exists — it cannot be rewritten; R7's rule text tells agents that ai-kit's rule overrides it.
- `.claude/cli-environment.md` — gitignored and local-only; its AGENTS.md link is Phase 31's.
- LLM-backed graphify extraction (`/graphify` without `--update`, `graphify extract`) — the steps use the AST-only
  `graphify update .`.

## Constraints

- Runtime scripts stay stdlib-only under system python3; outside tools are `git`, plus `codegraph` and `graphify`
  only when present. Reading the codegraph index other than through its CLI is a reverse-engineered format and is
  labeled as such wherever it is used.
- The worktree hook returns within GSD's git timeout (well under 10 s); indexing runs detached and respects the
  CPU-share rule (never more than one indexing job per repository at once).
- Tests use fakes for `codegraph` and `graphify` (Phase 28 tripwire), temporary repos and scratch HOMEs; no test reads
  the repo's `.planning/` or runs a real host CLI.
- R11 writes through ai-kit's atomic writers with a backup first, changes one sentence and nothing else, and is tested only on synthetic files in a scratch HOME.
- Every config write goes through `gsd-tools config-set` at execution time; the real `.planning/config.json` is not
  edited by hand; no absolute machine path in source, tests, fixtures or config.
- The GSD hook points rely on the Phase 29 D-02 spike (`plan:pre`, `execute:wave:pre`); if a hook form cannot run the
  step, planning returns to the owner.

## Acceptance Criteria

- [ ] GSD and superpowers fixtures: at unit start, before planning and before the first wave, the index and graph are
      built at the unit branch's HEAD and the brief names the previous unit's new function; nothing lands on main.
- [ ] Each codegraph case (no index → `init -y`, reindex recommended → `index`, current → `sync`, CLI missing → one
      line, exit 0) runs as specified through a recording fake.
- [ ] The fixture graph has zero `.planning/milestones/` nodes; `gsd-tools graphify status` shows `built_at_commit`
      equal to HEAD and `stale: false`; a missing `graphify` prints one line and the step continues.
- [ ] A non-GSD fixture ends with `graphify-out/graph.json` and no `.planning/` folder after the boundary step and
      the worktree hook; a GSD fixture ends with both files from one build. *(added 2026-11-03, 30 D-16)*
- [ ] The brief lists the range and an added, a changed and a removed file with the explore instruction and the tracked
      docs outside `.planning/` that mention their symbol or file names; a first unit gets the "no previous unit" brief;
      without the codegraph CLI the document search uses file names only, labeled. *(amended 2026-11-03, 30 D-08)*
- [ ] Rendered GSD researcher, planner and executor prompts and every superpowers implementer brief carry the brief;
      without it they render and say so.
- [ ] Two simultaneous `git worktree add` calls each return in under 1 s, and each worktree ends with its own
      codegraph index (no `worktreeMismatch`) and graph, with no overlapping indexing jobs.
- [ ] The AGENTS.md tool-use rule and runbook doc-contract tests pass and fail when a clause or section is removed;
      R07 and R08 show the new summaries; advisor fixtures advise on a code search in an indexed checkout only.
- [ ] `query agent-skills` shows the six lens entries as `global:` names with no warning; with a lens removed from a
      scratch HOME the prompt renders and the lens text tells the agent to name it; `workflow.ui_review` is true.
- [ ] The design-rule doc-contract test passes and fails when a clause is removed; the ponytail lens text carries the
      rule or points to it.
- [ ] In a scratch HOME, install rewrites only codegraph's sentence in the four synthetic global files, leaves a backup, and a second run gives no diff; `--dry-run` writes nothing; a missing block or sentence is skipped with a note; the doctor reports the installer's wording when it is back and install re-applies ai-kit's.
- [ ] With all five flow tools missing and fake installers, `make setup-dev` installs four, reports the failing one and exits 0; a second run installs nothing; a worktree made with hooks uninstalled is indexed at the next boundary point.
- [ ] Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04).

## Edge Coverage

**Coverage:** 67/67 applicable edges resolved · 0 unresolved (64 engine rows, 3 added)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| boundary | R1 | ✅ covered | "First execution wave" is wave 1 only; later waves do not rerun the step; a unit resumed after an interrupted wave 1 reruns it before wave 1 restarts |
| adjacency | R1 | ✅ covered | A checkpoint of the previous unit that lands after this unit started (the stack cascade moves this branch) is reflected at the next point, not lost |
| empty | R1 | ✅ covered | A unit with no previous unit still gets the index refresh and a "no previous unit" brief |
| ordering | R1 | ✅ covered | One run is codegraph refresh, then graphify refresh, then the brief, so the brief reads the fresh index |
| precision | R1 | ✅ covered | "Built at HEAD" means the exact commit: `gsd-tools graphify status` `built_at_commit` equals `git rev-parse --short HEAD`, never a time comparison |
| idempotency | R1 | 🧪 backstop | Two runs at the same HEAD give the same brief (apart from its timestamp line) and no commit (held-out edge test) |
| concurrency | R1 | ✅ covered | Two runs in one checkout at once: a lock under `.git/` makes the second wait, and the brief is replaced atomically, never half-written |
| adjacency | R2 | ✅ covered | A worktree nested in the main checkout counts as having no index of its own when `worktreeMismatch` is set, so it gets `init -y`, not the parent's `sync` |
| empty | R2 | ✅ covered | A `.codegraph/` that `status` cannot read gets a full `codegraph index`; if that fails too, the step reports it and continues |
| encoding | R2 | 🧪 backstop | Checkout paths with spaces or non-ASCII characters reach codegraph as one argument, never through a shell string |
| ordering | R2 | ✅ covered | The choice order is fixed: no index of its own → `init -y`; else reindex recommended → `index`; else `sync` |
| concurrency | R2 | ✅ covered | (added 2026-11-03) A sync refused because codegraph's own lock is held (its MCP daemon writing) is reported and retried at the next point; the step never deletes codegraph's lock |
| empty | R3 | ✅ covered | When `graphify update .` fails or writes no graph, `.planning/graphs/` keeps the previous graph and the status file records `failed`; an empty or missing graph is never copied |
| encoding | R3 | 🧪 backstop | `.graphifyignore` uses gitignore syntax relative to the repo root; the exclusion holds in a checkout whose path has spaces (held-out edge test) |
| idempotency | R3 | 🧪 backstop | A rerun at the same HEAD gives the same node count and leaves `.planning/graphs/` unchanged apart from the status file |
| concurrency | R3 | ✅ covered | The step honors GSD's `.planning/graphs/.rebuild.lock`: while a live process holds it, the step waits instead of writing over GSD's own rebuild |
| adjacency | R3 | ✅ covered | (added 2026-11-03, 30 D-16) A project with GSD resolvable but no `.planning/config.json`, or with `graphify.enabled` false, gets `graphify-out/` only; the step never creates `.planning/` or `.planning/graphs/` |
| boundary | R4 | ✅ covered | The mention cap is 10 documents: a name in exactly 10 lists all ten; in 11 or more, the brief shows the count and the first 10 paths |
| adjacency | R4 | ✅ covered | ~~A symbol removed in one file and added under the same name and kind in another is listed once as moved, not as an add and a remove~~ *(superseded, D-08)* A file renamed in the range (git rename detection) is listed once as renamed, with both names searched in the documents |
| empty | R4 | ✅ covered | ~~A previous unit that changed no symbols (docs or config only) gets a brief saying so, with its changed files~~ *(superseded, D-08)* A previous unit whose range changed no code file (docs or config only) gets a brief saying so, with its changed files and no explore instruction |
| encoding | R4 | 🧪 backstop | Names (symbol names from `codegraph explore` and file names) are matched whole-word and case-sensitively on the literal name with regex characters escaped, so `_atomic_write_json` never matches `atomic_write` |
| ordering | R4 | ✅ covered | ~~Symbols are listed by file path, then line~~ *(superseded, D-08)* Changed files are listed by path; documents by path; the order is stable across reruns |
| precision | R4 | ✅ covered | ~~A symbol counts as changed when a diff hunk of the range overlaps its line span on the new side~~ *(superseded, D-08)* The changed-file list is exactly `git diff --name-status` of the range; symbol detail comes from `codegraph_explore` at the agent's call, never estimated by the step |
| concurrency | R4 | ✅ covered | The brief is written atomically (temporary file, then replace), so an agent reading it sees the old or the new brief, never a partial one |
| idempotency | R4 | ✅ covered | A rerun at the same HEAD gives the same brief apart from its timestamp line; the document search is deterministic for a given tree |
| adjacency | R5 | ✅ covered | A brief whose unit id is not this unit's (a stale file) is not handed over; the prompt says the brief belongs to another unit |
| empty | R5 | ✅ covered | With no brief, the prompts render and say no brief was found (R5 acceptance) |
| ordering | R5 | ✅ covered | The agents read the brief after the SPEC and CONTEXT, so locked decisions win over the brief's hints |
| adjacency | R6 | ✅ covered | A worktree re-added at a path that still has its own index gets `sync`, not `init` |
| empty | R6 | ✅ covered | A worktree added with `--no-checkout` fires no `post-checkout`; the unit's next boundary point indexes it (R1) |
| ordering | R6 | ✅ covered | Queued jobs run in worktree-creation order, codegraph before graphify for each worktree |
| boundary | R6 | ✅ covered | (added 2026-11-03; an engine row since the D-03 amendment) The hook returns in under 1 s even with jobs queued, well inside GSD's 10 s git timeout for `worktree add`; a worktree removed before its job starts is skipped with a note |
| precision | R6 | ✅ covered | "Stale" means `codegraph status --json` shows non-zero pending changes or a recommended reindex; a current index is left alone |
| concurrency | R6 | ✅ covered | (added 2026-11-03) Two worktrees created at once never run two indexing jobs at the same time in one repository (R6 acceptance) |
| adjacency | R7 | ✅ covered | One search over both code and Markdown (an rg over the whole repo) gets the codegraph advice once, including the rg-for-Markdown clause |
| empty | R7 | ✅ covered | With no codegraph CLI and no index, the advisor gives no codegraph advice |
| encoding | R7 | 🧪 backstop | The advice is one line that survives the host's display cut with the tool names intact (held-out edge test) |
| ordering | R7 | ✅ covered | The new advice follows the advisor's per-command order and frequency limit (first time, then every tenth), like the existing advice ids |
| idempotency | R7 | ✅ covered | The same tool call seen twice gives the advice once (the advisor's existing call-key dedupe) |
| concurrency | R7 | 🧪 backstop | Parallel advisor calls in one session share the existing per-session lock, so the advice counts stay consistent |
| boundary | R8 | ✅ covered | The runbook gives GSD's staleness thresholds as GSD's own (24 h age, a running or failed build), says commits behind is not one, and names the gsd-core version read |
| adjacency | R8 | ✅ covered | The runbook holds the build and refresh steps; AGENTS.md states the rule and links the runbook instead of repeating the steps |
| empty | R8 | ✅ covered | The runbook says a project without GSD skips the copy into `.planning/graphs/` |
| ordering | R8 | ✅ covered | The runbook's sections run build, refresh, freshness check, query |
| precision | R8 | ✅ covered | Timings in the runbook are labeled as measured on 2026-11-03 on this machine, not as guarantees |
| idempotency | R8 | ✅ covered | The runbook says a rebuild can be rerun safely and gives the same graph at the same HEAD |
| concurrency | R8 | ✅ covered | The runbook says not to start a manual build while GSD's rebuild lock or the step's lock is held |
| adjacency | R9 | ✅ covered | The existing project-relative jev entries for the analyzer and the advisor researcher stay unchanged next to the new `global:` entries |
| empty | R9 | ✅ covered | On a runtime other than claude, GSD skips the plugin lenses; the agent runs and names them as not loaded (R9 missing-lens rule) |
| encoding | R9 | ✅ covered | `~/.agents/skills` is written with a literal `~` (GSD expands it), never as the expanded home path |
| ordering | R9 | ✅ covered | In each agent's list the lens comes first and any brief text after it, so the design rule is read after the lens it qualifies |
| adjacency | R10 | ✅ covered | Where ponytail's smallest-change wording meets the design rule, the text says ponytail yields; the doc-contract test pins that sentence |
| empty | R10 | ✅ covered | Without jev the rule still applies, decided by the agent's own reasoning; the text says so |
| encoding | R10 | 🧪 backstop | The doc-contract test compares the rule's clauses after whitespace normalization only |
| ordering | R10 | ✅ covered | The rule sits in AGENTS.md's owner-written part, above any generated block that Phase 45.1 adds |
| adjacency | R11 | ✅ covered | Only text strictly between the two markers is searched; the same sentence outside the block (a user's own note) is left alone |
| concurrency | R11 | ✅ covered | The file is re-read just before the atomic replace; when it changed since the backup (a host or `codegraph install` writing it), the write is abandoned with a note and retried on the next install |
| empty | R11 | ✅ covered | A missing file, a file without the block, a block without the sentence, or a block with only one marker is skipped with a one-line note and never written |
| encoding | R11 | 🧪 backstop | Line endings, a missing final newline and non-ASCII text around the block survive byte for byte; the file is read and written as bytes around the sentence (held-out edge test) |
| idempotency | R11 | ✅ covered | A file that already holds ai-kit's sentence is not rewritten and gets no new backup; a second install gives no diff |
| ordering | R11 | ✅ covered | Files are handled in a fixed host order (Claude, Codex, Gemini, opencode), each backup is written before its file, and the report lists them in that order |
| adjacency | R12 | ✅ covered | A tool already on PATH at any version is left alone; an upgrade is never part of `setup-dev` |
| concurrency | R12 | ✅ covered | Two `make setup-dev` runs at once (two worktrees) take one lock under the git common dir; the second waits and then finds the tools installed |
| empty | R12 | ✅ covered | With no network, no package manager or no permission, each missing tool is reported by name with its manual install command and the target exits 0 |
| encoding | R12 | 🧪 backstop | Install commands receive paths (HOME, the checkout) as separate arguments, so a path with spaces installs correctly (held-out edge test) |
| idempotency | R12 | ✅ covered | A second run installs nothing and prints each tool as already present |
| ordering | R12 | ✅ covered | Tools install in dependency order: pre-commit, then gh before the gh-stack extension, then codegraph and graphify; a failed gh skips gh-stack with a note |

## Prohibitions (must-NOT)

**Coverage:** 7/7 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| The boundary, worktree and rule steps MUST NOT edit the owner's global instruction files or any other file under the real HOME; the only writer of a global file is R11's setup action | R1-R7, R9 | resolved | verification: test (scratch-HOME fixtures with `AI_KIT_REFUSE_REAL_HOME=1`; a real-home write fails the run) |
| R11 MUST NOT change any byte of a global file outside codegraph's sentence, or write one without a backup first | R11 | resolved | verification: test (byte diff of synthetic files equals the sentence alone; a backup exists before each write) |
| Tests MUST NOT touch a real global instruction file; R11 is tested on synthetic files only | R11 | resolved | verification: test (the real-home guard fails any test that resolves a real HOME path) |
| The steps MUST NOT turn off `graphify.enabled` or `graphify.auto_update`, or edit GSD's installed hook scripts | R3 | resolved | verification: test (fixture config and hook files are byte-identical after every step) |
| The worktree hook MUST NOT block or fail a git command | R6 | resolved | verification: test (a failing or slow fake indexer still lets `git worktree add` exit 0 in under 1 s) |
| Index outputs (`.codegraph/`, `graphify-out/`, `.planning/graphs/`) MUST NOT be committed | R2, R3, R6 | resolved | verification: test (after each step `git status --porcelain` in the fixture lists none of them) |
| The brief MUST NOT claim that a document describes a symbol, only that it mentions it | R4 | resolved | verification: judgment (review of the brief template; a test pins the word "mentions") |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                  |
|--------------------|-------|------|--------|------------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | three points, auto-index, brief contents, rule text, lenses, design rule |
| Boundary Clarity   | 0.80  | 0.70 | ✓      | general playbook and generated rules stay in 45.1 and 47 (amended)     |
| Constraint Clarity | 0.80  | 0.65 | ✓      | stdlib, fakes, git timeout, CPU share, gsd-tools writes only          |
| Acceptance Criteria| 0.75  | 0.70 | ✓      | fixtures per point and per case, doc-contract tests, agent-skills output |
| **Ambiguity**      | 0.175 | ≤0.20| ✓      | 1 − (0.315 + 0.20 + 0.16 + 0.15)                                       |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

Interactive, 3 rounds (each batch answered by the owner through the orchestrator), after the owner's decisions given
with the task. The decision ladder was not used: in the interactive path it screens only items the owner asks to
screen, and none were. Rule: `mvp-mode` inactive, the best design wins over the smallest diff (DESIGN-01: simple is
not easy, no half-done feature).

| Round | Perspective | Question summary | Decision locked |
|-------|-------------|------------------|-----------------|
| 0 | Given with the task | Code versus documents, the boundary refresh, the runbook, lens names, UI review, the design rule | Owner decisions (R3, R7, R8, R9, R10) |
| 1 | Researcher | When the boundary step runs | Unit start, before planning and before the first execution wave, on the unit's own branch (R1) |
| 1 | Boundary Keeper | Which units get it | Every unit, inside the unit-flow engine; superpowers implementer briefs carry the brief (R1, R5) |
| 1 | Simplifier | Which documents the brief searches | Tracked documents outside `.planning/` (R4) |
| 1 | Failure Analyst | `impeccable` skipped as a symlink escape | Trust `~/.agents/skills`, written with `~` through gsd-tools at execution time (R9) |
| 1 | Owner addition | Indexes in new worktrees; one tool-use rule; ignore entries | Worktree-created step in ai-kit now (R6), the rule in AGENTS.md and the advisor (R7), RULE-03 and RULE-06 amended |
| 2 | Seed Closer | A never-indexed project | Always index when the CLI is present, no question and no stored setting; a missing CLI prints one line (R2, R3, R6, R7) |
| 2 | Owner correction | The "indexing is the user's decision" sentence | Written by codegraph's installer, not the owner; the rule text overrides it; changing the global file is the owner's (CONTEXT) |
| 3 | Owner addition | Rewriting that sentence in the global files | ai-kit's setup rewrites only that sentence in every global file codegraph's installer writes, atomically with a backup, idempotent, with a dry run, a doctor drift row and re-apply on install; placed here, reused by Phase 54 (R11) |
| after 2 | Edge and prohibition probes | The engine's floor and the must-NOT pass | Resolved by the orchestrating agent; open to change in discuss |
