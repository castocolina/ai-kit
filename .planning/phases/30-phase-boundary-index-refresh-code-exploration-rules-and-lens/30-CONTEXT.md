# Phase 30: Phase-boundary index refresh, code-exploration rules and lens wiring - Context

**Gathered:** 2026-11-03 (interactive, standard discuss mode `--analyze --all --batch`, after 30-SPEC.md; best over easy, DESIGN-01)
**Status:** Ready for planning

<domain>
## Phase Boundary

Every unit of planned work and every new worktree gets its codegraph index and graphify graph created or refreshed
automatically on the branch being worked on; the next unit's researcher, planner and executor get a brief naming the
previous unit's range, changed files and the documents that mention them; one tool-use rule tells agents which index
to use and how to keep it fresh; ai-kit's GSD agents get their lens skills; AGENTS.md carries the design rule;
ai-kit's setup rewrites codegraph's installer sentence in the global instruction files; `make setup-dev` installs the
flow's tools. The general playbook and generated rules stay in Phases 45.1, 46 and 47 (amended).
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**12 requirements are locked.** See `30-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `30-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- The boundary step at the unit's start, `plan:pre` and wave 1's `execute:wave:pre`, for GSD and superpowers units.
- Automatic codegraph init, sync or reindex, and the graphify build with the committed `.graphifyignore`, copied into
  `.planning/graphs/` only in a GSD project.
- The brief (range, changed files, the explore instruction, the documents that mention them) and its delivery.
- ai-kit's worktree-created indexing hook, with the boundary step and the rule as further triggers.
- The tool-use rule in AGENTS.md, house rules R07 and R08 and the tool advisor; the graphify runbook.
- ai-kit's lens wiring through gsd-tools; the design rule in AGENTS.md and the lens briefing.
- The setup action rewriting codegraph's sentence in the four global instruction files, with its doctor drift row.
- ai-kit's `make setup-dev` with guarded installs of the flow's tools.

**Out of scope (from SPEC.md):**
- The generated top rules (45.1, RULE-03), the Makefile rules (46, RULE-05) and the worktree-created playbook (47,
  RULE-06) for target projects — amended now.
- curated-config's lens proposal (44, LENS-03); session-hook indexing advice (49, HOOK-03).
- Editing GSD's installed hook scripts; the jev marker block itself (54, JEV-04, reuses R11's editor).
- The message the codegraph binary prints when no index exists; `.claude/cli-environment.md`; LLM-backed graphify.
</spec_lock>

<decisions>
## Implementation Decisions

### Where the step lives and how it is triggered

- **D-01: The boundary step is a `boundary` command in the unit-flow engine (Phase 29.1 D-02).** `start` calls it;
  GSD's hooks call the same command; it moves into `ai-kit-project-rules` with the engine in Phase 45. Owner choice
  (recommended).
- **D-02: GSD triggers it through two more step hooks, `plan:pre` and wave 1's `execute:wave:pre`, in the ai-kit
  GSD extension the Phase 29 D-02 spike proves.** If a hook form cannot run it, planning returns to the owner (the
  Phase 29 D-02 rule). Live: `transition.md` dispatches no hook; both points are rendered by gsd-core 1.18.0. Owner
  choice (recommended).
- **D-03: Indexing is resilient: three triggers, none the only one** (SPEC R6 amended).
  - A `post-checkout` stage in ai-kit's `.pre-commit-config.yaml`, installed by `make setup-dev`, fires on a new
    worktree or clone, hands off to a detached job and returns at once (GSD runs `git worktree add` under a 10 s git
    timeout).
  - The unit's `start` and every boundary point also initialize or sync a checkout whose `.codegraph/` is missing or
    stale (`codegraph status --json` pending changes or a recommended reindex).
  - The tool-use rule tells any agent, including an executor in a worktree whose hook never fired, to run
    `codegraph init -y` or `codegraph sync` before exploring.
  - Owner: "Anything we create must be resilient, and the required tools should be installed by setup-dev."
- **D-04: ai-kit's `make setup-dev` installs the flow's missing tools through guarded steps** (SPEC R12 added,
  FLOW-13 added; RULE-05 amended, coupling to Phase 46).
  - Tools: the codegraph and graphify CLIs, pre-commit, gh, the gh-stack extension; an installed tool is left alone;
    a failed install is reported with its manual command and the target still exits 0; the flow degrades.
  - `dev` and `setup-env` keep working until Phase 46 settles the aliases (RULE-05: `setup-dev`, `setup-docker`,
    `setup-env` as an alias for one milestone).
  - Live: ai-kit's Makefile has `setup-env` (`uv sync`) and `dev` (`setup-env` + `pre-commit install`), no
    `setup-dev`; RULE-05 and RULE-09 (ai-kit follows the rules skill) are Phase 46's.
  - Owner decision (Q3 answer).
- **D-05: The Phase 49 session-hooks todo is not folded; a dated note says Phase 30 now indexes automatically and
  its first item shrinks to reporting what was indexed.** Owner choice (recommended).

### The brief

- **D-06: The brief lives in a gitignored `.aikit/brief/` folder per checkout**, written atomically by the engine,
  copied into each new worktree by the worktree job. No commit churn; each worktree sees its own unit's brief. Owner
  choice (recommended).
- **D-07: The brief reaches the agents through GSD's agent-skills mechanism**: a project-relative entry pointing at
  the brief folder for `gsd-phase-researcher`, `gsd-planner` and `gsd-executor`, set through gsd-tools; the folder
  always holds a file, which says "no brief" when there is none; the superpowers adapter adds the path to the plan
  writer's and every implementer's brief. Live: project-relative entries resolve today (the two jev entries); the
  executor, researcher and planner workflows all render `query agent-skills`. Owner choice (recommended).
- **D-08: The brief names the range and the changed files and tells each agent to run `codegraph_explore` on them**
  (SPEC R4 amended, edge rows superseded).
  - No reading of codegraph's internal database and no symbol differ of ai-kit's own: symbols, callers and blast
    radius come from `codegraph_explore` (or `codegraph explore` in a shell) at the agent's call.
  - For the documents to update, the step runs `codegraph explore` on the changed files, takes the symbol names it
    returns plus the file names, and searches tracked documents outside `.planning/` (whole-word, capped at 10 per
    name).
  - Owner, in their words: "Why should it matter, if codegraph has its MCP tool? We should care about using the
    tool."

### Rules, advisor and lenses

- **D-09: The tool advisor shows the codegraph rule on code searches**: shell rg, grep or find over non-Markdown
  paths and Claude's built-in Grep and Glob, in a checkout with `.codegraph/`, rate-limited like today's advice. The
  Claude hook's matcher widens from `Bash|Read` to include `Grep|Glob` through setup's existing writers
  (`tools/setup.py` hook table). Owner choice (recommended).
- **D-10: A tracked lens-brief entry follows each lens in GSD's agent-skills.** It carries the design rule (or points
  to AGENTS.md's), lists each agent's expected lenses and says to continue without, and name, any lens that did not
  load; a drift check compares its list with `.planning/config.json` through `make check-dogfood` (Phase 28 D-11),
  since no test reads the repo's `.planning/`. Live: GSD silently drops a missing bare `global:` skill
  (`configured_unresolved`) and never checks plugin lenses, so the agent cannot know what was expected otherwise.
  Owner choice (recommended).
- **D-11: The global-sentence rewrite (SPEC R11) runs headless with a new `--with-global-rules` flag and in the
  wizard as a pre-checked Review item showing each file's diff.** A bare `--headless` still touches nothing; Phase
  54's jev block can ride the same flag and item. Owner choice (recommended).
- **D-12: One `graphify update .` build feeds both locations** (SPEC R7, R8 amended). Live: `graphify update` rejects
  `--graph` ("unknown update option", exit 2), so it cannot write to `.planning/graphs/` directly; `graphify query
  … --graph .planning/graphs/graph.json` works. The rule and the runbook say GSD's agents read `.planning/graphs/`
  and raw queries can pass `--graph .planning/graphs/graph.json`.
- **D-16: GSD versus non-GSD projects** (SPEC R3, R7 amended; RULE-03 and RULE-06 amended; edge row added).
  - Detection reuses `detect_framework.py`'s `.planning/PROJECT.md` marker, plus `.planning/config.json` or a
    resolvable project gsd-tools.
  - A non-GSD project keeps `graphify-out/` only, gets no `.graphifyignore` milestone entry, and never gets a
    `.planning/` folder; agents query `graphify-out/graph.json`.
  - A GSD project gets the copy and status file in `.planning/graphs/` (only with `graphify.enabled`); agents may
    read either file.
  - Gitignore: `graphify-out/` always, `.planning/graphs/` only in a GSD project. A fixture test per kind.
  - Owner rule, given after Round B's batch.

### Provisional, own reasoning (not objected by the owner)

- **D-13: House rules R07 and R08 keep their ids and criticality; both summaries are cut from the one rule text and
  a test pins that they match it.** Their tool-presence conditions differ, so they stay two rules.
- **D-14: SKILL.md files under the judge bar (JDG-04):** `ai-kit-commit-fold` (the `boundary` command, D-01) and
  `ai-kit-spec-execute-superpowers` (the brief in implementer briefs, D-07). `ai-kit-project-rules-agents` joins only
  if its SKILL.md text changes (the R07/R08 change is in `rules.py`).
- **D-15: Tests fake `codegraph` and `graphify` through Phase 28's shared fake helper** (D-04 there), recording argv
  and returning canned `status --json`; the worktree tests use temporary repos with ai-kit's hook installed; R11's
  tests use synthetic global files in a scratch HOME.

### Claude's Discretion

- Command, module and file names (the brief file inside `.aikit/brief/`, the lens-brief folder's tracked path, the
  job lock's name); the brief's layout; the exact advisor wording within the rule text.
- The guarded install command per tool and platform, as long as nothing needs sudo silently and each failure names
  its manual step.

### User-owned items

- **The installer's sentence in the global files.** ai-kit's setup now rewrites it (SPEC R11, D-11) when run with
  `--with-global-rules` or confirmed in the wizard; the owner decides when to run it. ai-kit never hand-edits those
  files, and `codegraph install` writes the installer's wording back (the doctor reports it). Blocks: nothing in
  planning.
- **Tool installs and tools-installer.** The owner placed the flow's tool installs in ai-kit's `setup-dev` (D-04);
  an earlier scope note gave third-party installs to tools-installer. Install only when missing keeps both from
  fighting; the owner may want tools-installer to stay the primary installer. Blocks: nothing.
- **Unpushed planning commits** (carried from Phase 29.1): local main is ahead of `origin/main`; pushing needs the
  owner's consent. Blocks: the first real stacked unit, which is this phase.

### Folded Todos

None. Reviewed, not folded: "Make the ai-kit session hooks dynamic" (Phase 49; dated note added, D-05). The other 12
keyword matches from `todo.match-phase 30` (jev, Cursor, decision-skill, rules-refactor and live-check todos) are
unrelated to indexes, rules or lenses.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-SPEC.md` — Locked requirements — MUST read before planning
- `.planning/phases/29.1-stacked-phase-branches-chained-prs-and-the-merge-chain-inserted/29.1-CONTEXT.md` — the unit-flow engine, `start`, the stack record, `.aikit/`, the superpowers adapter (D-01, D-02, D-04, D-05, D-12)
- `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-CONTEXT.md` — the GSD extension spike (D-02)
- `.planning/phases/28-fast-environment-proof-gates/28-CONTEXT.md` — fakes and the tripwire PATH (D-04), no `.planning/` reads in tests, `make check-dogfood` (D-11)
- `.planning/REQUIREMENTS.md` — FLOW-04, FLOW-06, FLOW-12, FLOW-13, DESIGN-01, LENS-01 (amended), RULE-03, RULE-05, RULE-06 (amended), JEV-04 (amended), JDG-04
- `.planning/ROADMAP.md` — Phase 30 criteria 1-9
- `.planning/milestones/NEXT-MILESTONE-INPUTS.md` — Round 9 "When to use codegraph and when graphify", Round 10 lens and design-rule wishes
- `AGENTS.md` — Code Exploration, Commands, Non-Negotiable Rules (atomic writes)
- `.claude/gsd-core/workflows/plan-phase.md`, `execute-phase.md` — `plan:pre`, `execute:wave:pre`, the `query agent-skills` calls
- `.claude/gsd-core/bin/lib/init.cjs` — agent-skills resolution (`global:`, plugin directives, `trusted_global_roots`)
- `.claude/gsd-core/bin/lib/graphify.cjs`, `.claude/commands/gsd-graphify.md`, `.claude/hooks/gsd-graphify-update.sh`, `.claude/hooks/lib/gsd-graphify-rebuild.sh` — GSD's graph location, status file and auto-update gaps
- `.claude/gsd-core/bin/lib/worktree-safety.cjs` — `worktree add` runs `post-checkout` under the default git timeout
- `.claude/agents/gsd-phase-researcher.md` — Step 1.3 graph context and its staleness rule
- `skills/ai-kit-spec-execute/detect_framework.py` — the GSD marker reused by D-16
- `tools/hooks/advisor_core.py`, `tools/hooks/claude_tool_advisor.py`, `tools/setup.py` (hook table, `--dry-run`, `--headless`), `tools/config_doctor_checks.py`, `tools/config_doctor_appliers.py`
- `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py` — R07, R08
- `Makefile` — `setup-env`, `dev`; `.pre-commit-config.yaml` — `default_install_hook_types`
- codegraph 1.6.2 installer source (installed tool, read in place): `installer/instructions-template.js`, `installer/targets/{claude,codex,gemini,opencode}.js`, `sync/git-hooks.d.ts`, `sync/worktree.d.ts`
- graphify 0.9.54 (`graphify --help`; `detect.py` `.graphifyignore` handling)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The unit-flow engine and its stack record (Phase 29.1) for `boundary`, the previous unit and the lock under `.git/`.
- `_read_json_checked()`/`_atomic_write_json()` style atomic writes for the brief and the global-file rewrite.
- The advisor's frequency limit, call-key dedupe and per-session lock (`advisor_core.advise`, `with_state`).
- The config doctor's check and applier rows with confidence labels, for R11's drift row.
- `detect_framework.py` for the GSD-project check (D-16).

### Established Patterns
- Stdlib-only scripts under system python3; host CLIs reached only through fakes in tests; scratch HOME.
- Doc-contract tests pin AGENTS.md rules; every structural rule has a non-vacuity case.

### Integration Points
- GSD: `plan:pre` and wave 1's `execute:wave:pre` (D-02); agent-skills entries for the brief (D-07) and the lenses
  plus lens brief (D-10), set through gsd-tools.
- superpowers: `ai-kit-spec-execute-superpowers` passes the brief path (D-07).
- git: ai-kit's `post-checkout` stage (D-03).
- setup: `--with-global-rules`, the wizard's Review item and the doctor row (D-11); `make setup-dev` (D-04).
</code_context>

<specifics>
## Specific Ideas

- Probes and notes under the gitignored `tmp/p30/` (`facts.md`, `probe_*.sh`) show the method; they are not
  deliverables.
- The proposed global sentence: "If there is no `.codegraph/` directory and the `codegraph` CLI is installed, run
  `codegraph init -y` to create the index; if the index exists and `codegraph status --json` shows pending changes,
  run `codegraph sync` first (`codegraph index` when it reports a reindex is recommended)."
- Measured here (2026-11-03): `codegraph sync` 0.23 s, `codegraph init -y` 12.5 s on ai-kit, `graphify update .`
  15 s with the milestone exclusion (21 s without).
</specifics>

<deferred>
## Deferred Ideas and Couplings

- Generated top rules carrying the tool-use rule and the ignore entries — Phase 45.1 (RULE-03, amended).
- `setup-dev` installing the flow's tools in target projects; the alias decision — Phase 46 (RULE-05, amended).
- The worktree-created playbook for target projects — Phase 47 (RULE-06, amended).
- curated-config proposing the lens wiring elsewhere — Phase 44 (LENS-03).
- Session-start indexing advice — Phase 49 (HOOK-03; todo note added).
- The jev marker block through R11's editor and flag — Phase 54 (JEV-04, amended).
- Reporting GSD's auto-update hook gaps (missed `gsd-tools.cjs query commit`, `update-ref`, non-default branches)
  upstream — not ai-kit's code; documented in the runbook.
</deferred>
