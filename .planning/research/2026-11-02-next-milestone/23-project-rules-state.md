# Baseline of the ai-kit-project-rules-* family (research, 2026-11-02)

Read-only, checkout at 27337d5. Builds on `13-orphaned-scripts.md` (thin shims), `14-dist-layout-and-install.md`
(copy-install break, YAML defect) and `15-skills-vs-new-judge.md` (judge history, new rubric); those findings are
referenced, not repeated. Scripts beside this file:

- `23_rules_list.py`: prints the 20 house rules from `rules.py`; output `23_rules_list.out`.
- `23_frontmatter_check.py`: flags unquoted `: ` in the family's `description:`; output `23_frontmatter_check.out`.
- `23_planning_refs.sh`: finds every planning note about the family.
- `23_deferred.py`: pulls the deferred sections of the v1.2 phase contexts; output `23_deferred.out`.
- `23_self_check.sh`: runs the agents checker and the orchestrator against ai-kit itself, with the GSD probe
  skipped; output `23_self_check.out`.

## 1. The skills

Shared facts, so they are not repeated per skill:

- Invocation is the same everywhere: `python3 <skill>/ai-kit-project-rules-<x>.py check|remediate [repo_root]`
  (default `.`), with a hand-rolled `argv` parser (no argparse) and a `-h/--help` usage line. Each SKILL.md first
  runs a bash loop that resolves the entry point from five candidates: the skill's own folder,
  `$CLAUDE_PLUGIN_ROOT/skills`, `~/.claude/skills`, `$XDG_CONFIG_HOME/opencode/skills`, `~/.agents/skills`. The
  loop also requires `../_shared/ai_kit_rules_common` next to the real folder.
- Output is JSON on stdout. `check` returns the domain's raw findings. `remediate` is the shared
  `build_remediation()` shape: `{"remediate": [...], "blocked": [...], "notices": [...]}`. Each `remediate` entry
  carries `kind`, `id`, `criticality` (1 critical, 2 high, 3 medium, plus advisory), `summary`, and either
  `recommendation` or `auto_apply`. Structural entries also carry location fields (`service`, `ci_file`, `job`,
  `hook_id`, ...). `blocked` holds findings that need a per-stack research result first (makefile and precommit
  only). `notices` holds agents rules whose condition could not be proven.
- Stacks are detected by marker files only (`_shared/.../stack_detect.py`): Go (`go.mod`), Python
  (`requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile`), Node (`package.json`), Java (`pom.xml`,
  `build.gradle`, `build.gradle.kts`, so Maven and Gradle together) and Rust (`Cargo.toml`). The baseline tool
  catalog (`tool_catalog.py`, 900 lines) has rows for the same five stacks. Nothing else (no C#, Ruby, PHP,
  Kotlin-only or Swift markers).
- Every skill except agents detects and reports only, and never edits the target repo.
- Tests: one flat `tests/test_ai_kit_project_rules_<x>.py` per skill, plus `test_ai_kit_project_rules_all_e2e.py`
  and `test_ai_kit_rules_common.py` for the shared library. No skill has `evals/`, `references/` or a README.
- All judge results are on the old 120-point rubric (from report 15). None has a result on the current rubric
  (version 4, 125 points, percent bands).

### ai-kit-project-rules-agents (SKILL.md 156 lines)

- Checks: an `AGENTS.md` (else `CLAUDE.md`) plus the files it links to directly (one hop, first 20 same-repo
  links) against the 20 house rules, by literal lowercase substring match on each rule's signal phrases. Also
  reports broken relative links.
- Fixes: yes, the only family member that edits. Steps A-D: confirm near-misses with the user, back up every
  file, insert the missing rules in one `/agent-md-refactor` pass (an external skill ai-kit does not ship), or by
  direct edit when that skill is absent or nobody can be asked, then re-check and show the diffs.
- Statuses: `missing`, `near_miss`, `not_applicable`, `present` (omitted from output). `remediate` drops the
  `links` list, so the skill runs both commands.
- Runs code from the target repo: when `.planning/` exists, a GSD identity probe runs the repo's own gsd-tools
  through `node` (rules 18 and 19). `AI_KIT_SKIP_GSD_PROBE=1` turns it off. The probe imports two sibling skills,
  `ai-kit-gsd-curated-config` and `ai-kit-spec-review`. Without them, rules 18 and 19 always come back unverified.
- Languages: stack-blind, except rule 20, whose clause is built per detected stack.
- Last judge: 93/120 (77.5%), FAIL, accepted by the owner and deferred, 2026-10-30 (Phase 26, round 15,
  referee-two).
- Open defects:
  - Judge finding (critical): the unattended-restore wording. It is refuted by definition, but the text was
    not reworded.
  - Judge finding (important): the "phrase thresholds" rule is stated as universal, but the code applies the
    half-of-three rule only to flat lists (rules 19 and 20 differ).
  - Judge finding (important): check-only versus link repair contradict each other (line 71 against line 93).
  - The YAML frontmatter defect (section 2).
  - The worked example JSON and the trust-gate text use the rtk rule.

### ai-kit-project-rules-all (SKILL.md 242 lines)

- Checks: nothing itself. It runs the six siblings' `remediate` as subprocesses (in sequence, 30 s timeout each)
  and merges the results into one list ordered by criticality. Ties break in a fixed domain order: agents,
  makefile, precommit, arch, docker, cicd. It adds `hand_off` to agents-kind entries and keeps going when one
  domain fails (`failed`).
- Fixes: no. The only edit path is the agents sibling's Steps A-D, used only when the user asked for fixes.
  `remediate` is an alias of `check`.
- Output: `remediate`, `blocked`, `notices`, `failed`. Broken links are not merged in; a separate agents `check`
  covers them.
- Last judge: 102/120, PASS, 2026-10-30 (Phase 26).
- Open defects: nothing from the judge. It inherits every sibling's copy-install break. Runs are not cached, and
  it never calls `cache-update`.

### ai-kit-project-rules-arch (SKILL.md 181 lines)

- Checks: an arch-test-shaped Makefile target exists (`arch-test`, `arch`, `arch-check`, ...), `test` reaches it
  (as a prerequisite, transitively, or through its recipe), and the backing Python test file only parses code
  with `ast` and never imports what it checks.
- Detect-only.
- Languages: the AST-only check works on Python only. Other files get a `not_python` advisory. The baseline
  names one canonical tool per stack: import-linter (Python), dependency-cruiser (Node/TS), ArchUnit (Java).
  For Rust and Go it states a known gap.
- Last judge: 100/120, 2026-09-14 (Phase 12).
- Open defects: it follows only one file named in the recipe. On ai-kit itself, `make arch-test` goes through
  `tools/run_unittest_parallel.py --group arch`, so the check reports `no_parse_call` on the runner and never
  reaches `tests/test_arch.py`. The house repo's own arch test therefore cannot be verified (`23_self_check.out`).
  Real layering enforcement was dropped from scope on purpose in v1.2.

### ai-kit-project-rules-cicd (SKILL.md 299 lines)

- Checks: GitHub Actions and GitLab CI `run:`/`script:` lines that call a tool directly when a reuse source
  already exists. The four sources are a single-tool Makefile target, a pre-commit hook, a root `package.json`
  script, and a Gradle task. One finding category, medium.
- Detect-only.
- Languages: Node (lockfile picks pnpm, yarn, bun or npm), Java/Gradle (root build script plus a pinned plugin
  table), plus whatever tools Makefile and pre-commit name. CircleCI, Jenkins and Azure are ignored silently.
- Last judge: 103/120, 2026-09-14 (Phase 14).
- Open defects:
  - The YAML frontmatter defect (section 2).
  - The "Limits" list has 11 items. It is long, but it states what the skill does not see.
  - It never follows GitLab `include:`, and ai-kit's own `.gitlab-ci.yml` is built from includes. So on its
    home repo it sees almost nothing.

### ai-kit-project-rules-docker (SKILL.md 251 lines)

- Checks:
  - The eight `docker-*` Makefile targets exist.
  - `docker/local/README.md` exists.
  - Healthcheck `timeout`/`start_period`/`interval` stay within 2 s/10 s/5 s.
  - Each `depends_on` entry uses `condition: service_healthy`.
  - Local-dev services (in the override or local compose files) use a bind mount plus a command override, for
    hot reload.
- Detect-only. It never runs `docker`.
- Languages: the hot-reload tool table covers Python, Node, Go, Rust and Java.
- Last judge: 103/120, 2026-09-14 (Phase 13).
- Open defects:
  - The YAML frontmatter defect (section 2).
  - The `description:` is 1,092 characters. The Agent Skills spec and the new rubric cap it at 1,024, and the
    rubric scores a longer one in the bottom band of the frontmatter dimension. New in this report.
  - The eight target names are a fixed, opinionated list.

### ai-kit-project-rules-makefile (SKILL.md 231 lines)

- Checks:
  - The required static targets: `setup-env`, `validate`, `test`, `test-unit`, `test-integration`, `e2e-test`,
    `arch-test`.
  - The `validate-<category>` alias chain.
  - Help and fail reachability.
  - A three-line recipe cap.
  - Docker build-before-up.
  - A shellcheck target once the repo has five or more bash scripts.
  - An advisory heuristic for fast-versus-slow ordering.
- Detect-only, plus a research step. When a per-stack cache entry is cold or stale (`STALE_AFTER_DAYS = 30` in
  `_shared/.../stack_cache.py`), the finding goes to `blocked`. The agent then researches current tools per
  stack and writes them back with `cache-update <stack> <json> [--cache-root]`. The cache lives under
  `~/.cache/ai-kit/<namespace>/stack-refs`, and each value must cite a `(source: ...)`.
- Languages: the five marker stacks.
- Last judge: 103/120, 2026-09-14 (Phase 10).
- Open defects: the design spec says the research cache goes stale after 180 days, but the code says 30. The
  SKILL.md avoids naming a number on purpose.

### ai-kit-project-rules-precommit (SKILL.md 245 lines)

- Checks:
  - Parity between pre-commit hooks and single-tool Makefile targets, in both directions.
  - Classifies each hook into six categories: formatting, type checking, linting, security, duplicate code,
    dead code. Each classification carries a confidence of `baseline`, `cache` or `inferred`.
  - Flags enable-everything configs.
  - Flags a missing duplicate-code or dead-code tool.
  - Has ruff- and golangci-lint-specific checks.
  - Evaluates 9 of the 10 redundant-versus-complementary tool pairs.
- Detect-only, plus the same research step and cache as makefile. An extra `classify` subcommand exists.
- Languages: the five stacks. ESLint flat config in JS is unreadable, which gives an advisory.
- Last judge: 103/120, 2026-09-14 (Phase 11).
- Open defects: by design, a hook with no matching target is reported twice, once by makefile and once by
  precommit. The doc explains this.

### skills/_shared/ai_kit_rules_common/ (13 modules, 2,564 lines)

- Holds the classification engine (literal substring match), criticality, the remediation builder, the
  Makefile, pre-commit and YAML text parsers (stdlib only, no YAML library), command-text keys, stack detection,
  the stack cache, the 900-line tool catalog, tool presence (looks up `rtk`, `graphify` and the modern CLIs on
  PATH, plus the `.codegraph/` and `.planning/` folders) and the GSD identity probe.
- Not a skill: no SKILL.md, so it is never installed by itself.
- Thin re-export shims in the consumers are covered in report 13 (7 files, optional cleanup).

### The family run against ai-kit itself (`23_self_check.out`, probe skipped, 0.24 s)

- Agents: every rule is present except rules 18 and 19 (unverified, probe skipped) and rule 5 (not applicable,
  `rtk` is no longer on PATH). No broken links.
- Orchestrator: 11 `remediate` entries and 4 `blocked`.
  - 7 makefile: five `validate-*` aliases missing, no reachable help path, a five-line `e2e-docker` recipe.
  - 3 precommit: `format` and `security-scanner` targets without hooks, no duplicate-code hook.
  - 1 arch: the runner hides the test file.
  - The house repo does not pass its own Makefile, pre-commit and arch rules.

## 2. The house ruleset

The rules live in `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py` (`RULES`, 305 lines).
Each rule is a dict: id, category, criticality, condition, signals, summary. The per-stack clauses of rule 20
come from `_shared/.../tool_catalog.py` (`PARALLEL_TEST_FORMS`). They are a paraphrase of the 17 rules in the
owner's v1.1 todo (`.planning/todos/completed/2026-09-09-agents-md-rules-checker-skill-wrapping-agent-md-refactor.md`),
plus rules 18-20 added in Phase 26. Below, `crit` is the criticality and `when` is the condition under which the
rule applies.

1. English-only artifacts (crit 1, always).
2. Never skip pre-commit checks, except TDD red-to-green (crit 1, always). Its Makefile half moved to the
   makefile skill.
3. Commit compaction: one plan, few logical commits (crit 2, always).
4. Every plan uses cross-AI plan review, cheap-model cross-AI execution, and path-agnostic commands (crit 2,
   when `gsd` is present).
5. Explain rtk's hook-based command rewriting (crit 3, when `rtk` is on PATH).
6. Prefer rg, bat, sd, fd and eza, with a hint for each installed one (crit 3, when those tools are present).
7. Prefer the `codegraph_explore` MCP tool when `.codegraph/` exists (crit 3).
8. Use graphify for doc-aware indexing and re-index on purpose (crit 3, when graphify is present).
9. Kill the ephemeral processes and windows spawned for e2e checks (crit 2, always).
10. Scratch files go under `./tmp/` (crit 3, always).
11. Keep the README and nested docs current (crit 2, always).
12. No absolute paths in source, tests or assets (crit 1, always).
13. No excuse-driven deflection on failing tests or bugs (crit 1, always).
14. Verify gray-area or new topics against current sources (crit 2, always).
15. Theory, hypothesis, spike before planning new territory (crit 2, always).
16. No unexplained uncommitted files when a plan closes (crit 2, always).
17. Concise docs, no narration of abandoned paths (crit 3, always).
18. The main agent arms the `ai-kit-session-wake` self-resume before a multi-plan run (crit 2, open-GSD only,
    inserted verbatim).
19. Cross-AI runs go through `.planning/scripts/cross-ai.mjs`. Read the last `AIKIT-XAI` line and the
    `ai-kit-cross-ai` skill first, and never switch CLI or model (crit 2, open-GSD only, verbatim).
20. Parallel unit tests use floor(40% of the available CPUs) workers, never a hardcoded count (crit 3, when a
    stack is detected, verbatim).

### Stale or narrow

- Rule 5 (rtk) is stale. The owner dropped rtk (NEXT-MILESTONE-INPUTS, rtk section: "the agents-file rules
  checker has an rtk house rule"). The rtk name also sits in `tool_presence.py`, in the SKILL.md trust-gate text,
  and in the worked example JSON (`"signals": ["rtk", ...]`).
- Rules 4, 18 and 19 apply to GSD only. Rule 4 needs `gsd` on PATH, rules 18 and 19 need the open-GSD identity
  probe. Rules 18 and 19 also name ai-kit's own skills and runner (`ai-kit-session-wake`,
  `.planning/scripts/cross-ai.mjs`, `AIKIT-XAI`, `ai-kit-cross-ai`). They are ai-kit-internal and break when the
  runner or the wake changes, or when GSD support is reduced. The owner has not decided whether ai-kit's own
  `AGENTS.md` should adopt them (open decision in the live-checks todo).
- No referee or reviewer names appear in `rules.py`. The original todo's reviewer order (`*my-plan-review`, GLM,
  chatgpt, Opus) was never coded, and `my-plan-review` no longer exists.
- Wording tied to one host: rule 7 assumes an MCP tool. The SKILL.md Step C names "Claude Code's `Agent` tool
  with `subagent_type: general-purpose`" as its example mechanism. The candidate walk has no pi path of its own
  (pi reads `~/.agents/skills`, which is on the list).
- Weak signals, already warned about in the SKILL.md: rules 6 (`rg`, `bat`, `sd`, `fd`), 9 (`kill`), 10 (`tmp/`),
  15 (`theory`) and 17 (`concise`) match unrelated text. A rule can read `present` by accident.
- Detail dropped on the way: the original todo had long, verified guidance for rules 7, 8 and 9. Rule 8 said "on
  GSD write to `.planning/graphs/`, not `./graphify-out/`". Rule 9 had the opencode/Bun temp-copy leak and disk
  checks. The summaries keep one sentence each, by the Phase 9 decision that summaries paraphrase and never
  quote.

### YAML frontmatter defect (from report 14, re-checked)

`23_frontmatter_check.py` confirms that the `description:` of agents (`... or to fix it: insert ...`), cicd
(`... parity: this skill reads ...`) and docker (`... condition: service_healthy ...`) is an unquoted plain
scalar containing `: `. A strict YAML parser rejects them, and the `skills` CLI skips all three. Claude Code
accepts them. The other four are unquoted but have no `: `. The fix is to quote the value or use `>-`, and to
add a strict frontmatter test. Docker also needs its description cut below 1,024 characters.

## 3. Already recorded

- **Backlog 999.16** (`.planning/ROADMAP.md`, priority major): the owner asked on 2026-10-30 to check whether the
  seven skills should become one skill with playbooks keyed by event. The events are: new project (create the
  Makefile, pre-commit, tests and checks), new worktree, a plan or phase finished in open-GSD, worktree closed,
  subagent delegated, quota errors. The goal is that `AGENTS.md` stops carrying every rule. A feasibility check
  comes first, and it may conclude "keep the siblings". It must answer: routing, judge size, host portability,
  per-host triggers (description, hook or manual call), and the overlap with session-wake and the execute skills.
- **Refactor todo** (`2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md`): refactor rules-agents
  (and execute-gsd) until a re-judge passes without an exception, and decide it together with 999.16. It also
  proposes a percent-based pass rule, which AGENTS.md now has.
- **Tooling todo** (`2026-11-02-tooling-defects-and-skill-writing-principle-found-at-the-v1.md`): audit seven
  skills, the rules family among them, for versions, dates and history in the main flow. Move provenance to a
  trailing section ("a SKILL.md carries behaviour, not history"). There is also an unapplied proposal for an
  AGENTS.md line about it.
- **Live-checks todo** (`2026-11-02-pending-live-checks-and-owner-decisions-from-v1.3.md`): the open owner
  decision is whether ai-kit's own `AGENTS.md` adopts rules 18, 19 and 20. The options are all three, only the
  runner pointer, or none. Default: not edited.
- **Old todo** `2026-10-14-agents-md-quota-schedule-rules-and-goal-prompt-skill.md` is still in `pending/`. Part 1
  asked for a quota-resume rule in the agents checker: re-check every 10 minutes, capped at 4 hours, plus an
  hourly re-activation. Part 2 asked for the goal-prompt skill. Phase 26 delivered rule 18 with a different
  cadence (reset + 60 s, else hourly), and Phase 27 delivered the goal-prompt skill. The todo looks superseded
  but was never closed. It also asks for the quota rule inside spec-review and spec-execute.
- **NEXT-MILESTONE-INPUTS**:
  - Theme 1 holds the refactor, the history audit and the playbook check.
  - Theme 6 holds the AGENTS.md adoption decision.
  - The skills discussion lists "the project-rules skills (next round)" as still to discuss.
  - The judge batching puts the five checkers in one batch, and rules-agents, rules-all and usage-metrics after
    999.16.
  - The dist section covers the YAML defect, the `_shared` copy-install break and the vendoring proposal.
  - The rtk section asks to remove the rtk rule.
- **Memory note** (`project_rules_skills_playbook_idea.md`): the same idea as 999.16. Treat it as a feasibility
  check and do not build it. SJ-1 and SJ-3 are deferred into it.

## 4. History

- **Origin**: the owner's v1.1 todo of 2026-09-09 asked for one skill that "wraps `/agent-md-refactor` to
  check/enforce a set of house rules". It listed 17 rules, and rule 2 was the whole Makefile and pre-commit target
  shape. Phase 6 built it as one checker.
- **Split**: the design spec `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md` cut it into
  six single-domain checkers plus an orchestrator: "would make one skill responsible for five unrelated domains".
  It also fixed the rule that "each checker skill detects and reports findings only". The agents hand-off to
  `/agent-md-refactor` was the one exception kept. Milestone v1.2, Phases 9-15, shipped 2026-09-23.
- **Owner wishes in the spec**: the skills run "a couple of times per project, or once per milestone", so each
  stack is researched once and cached. Concrete tool names go stale, so a research step was added ("this
  research pass alone surfaced `flake8+plugins -> ruff`, `ts-prune -> knip`").
- **Deferred or dropped**:
  - All seven phase contexts (09-15) say "None — discussion stayed within Phase N's scope" for deferred ideas.
  - The one explicit drop is real layering enforcement in the arch checker (v1.2 REQUIREMENTS, Out of Scope):
    "Scoped down deliberately for v1.2 to form/convention-only checks ... explicitly flagged as a known gap rather
    than silently dropped". It closed old backlog 999.3 at that scope only. AGENTS.md still lists the
    whole-tree layering suite as backlog 999.3.
  - Dropped quietly: the original todo's detail for codegraph, graphify and process leaks (section 2).
  - Dropped quietly: the original rule 4's reviewer and executor preference order.
  - Dropped quietly: the wish that "every other validation/lint tool gets its own dedicated target" exists only
    as the `validate-<category>` alias check.
- **Later changes**: Phase 26 (v1.3) added rules 18-20 and the GSD identity probe. Its judge loop ended with the
  accepted rules-agents FAIL.

## 5. Under the planned changes

### Copy installs and dist (report 14)

- All seven break in a copy install. `_shared` has no SKILL.md, so it is never installed. Each package
  `__init__.py` raises `ImportError`. Each SKILL.md's entry-point loop skips a candidate without `../_shared`,
  so the agent reports "no importable install".
- The proposed fix is to vendor `ai_kit_rules_common` into each of the six checkers at build time (about 132 KB
  each). Then change in three places from "must find `_shared`" to "vendored beside me first, else checkout
  `_shared`": the seven `__init__.py` guards, the seven SKILL.md loops, and `-all`'s `dispatch.py`.
- Two dependencies survive vendoring:
  - The orchestrator finds its siblings only in the same skills folder or the four host folders. A user who
    installs `-all` alone gets six `failed` entries.
  - The GSD probe in agents imports `ai-kit-gsd-curated-config` and `ai-kit-spec-review` from the same folder,
    so rules 18 and 19 stay unverified unless those are installed too.
  So the family is really an install group, like the spec skills.
- `agent-md-refactor` is external and optional. Its absence already falls back to direct edits.
- The research cache under `~/.cache/ai-kit/` does not depend on the install layout.

### The new judge (rubric version 4)

- No evals exist in any of the seven. The tests-and-evals dimension (15 points) then sits in its bottom band,
  which is by itself a high finding. The pass rule ("no critical or high, or grade B or better") then hangs on
  the percent alone.
- Agents, cicd and docker also lose the frontmatter dimension to its bottom band: invalid YAML, and docker
  over 1,024 characters. Each of these is another high finding.
- They have no `scripts/` folder (only a top-level entry and a package). A literal judge gives evals 8 points and
  trigger queries 7, and never credits the flat `tests/test_ai_kit_project_rules_*.py`. The judge prompt must
  name those tests, or the tests must move to `tests/skills/<name>/` (report 15).
- Likely weak spots in decision-branch tracing:
  - agents' Steps A-D, attended and unattended (already 5/15 on the old rubric).
  - The research-now-or-defer branch in makefile and precommit.
  - The 11-item limits list in cicd.
- Evals would be cheap to write. Each description already names its near-miss siblings, so negative trigger
  queries come for free, and every checker emits deterministic JSON, which suits verifiable assertions.
- Every old score is on the 120-point rubric, so the first run is a new baseline and not a regression check.

## Open questions for the owner

1. Keep the seven checkers plus the orchestrator, merge them into one skill with event playbooks (backlog
   999.16), or something in between? Example: keep the deterministic checkers as scripts behind one skill, with
   per-event runbooks on top.
2. Should the house rules stay ai-kit's own convention, or become something other repos can configure? Today
   they are a fixed list, not offered as a general engine.
3. Remove the rtk rule now, together with the rtk lookup and the rtk example text?
4. Should the GSD-only rules (cross-AI plan rules, session wake, runner pointer) stay in a general checker? Or
   should they move into the GSD or cross-AI skills, given that they name ai-kit's own runner and skills?
5. Should ai-kit's own `AGENTS.md` adopt rules 18-20 (still open from v1.3)? Should ai-kit's own Makefile and
   pre-commit pass the family's checks? Today 11 findings fail on the house repo. Is that the rules being too
   strict, or the repo being behind?
6. Should the agents checker keep editing files (Steps A-D through `/agent-md-refactor`)? Or should it report
   only, like its siblings? The edit path is where most judge findings come from.
7. Which ecosystems matter beyond Python, Node, Go, Java (Maven or Gradle) and Rust? Should CI platforms beyond
   GitHub and GitLab, or GitLab `include:`, be read?
8. Should the arch checker see through a test runner (as ai-kit's own `make arch-test` uses), and should real
   layering enforcement (backlog 999.3) come back?
9. For copy installs: vendor the shared library into each checker, and always install the family as one group,
   including the two siblings the GSD probe needs?
10. Re-judge the family in the planned batches (five checkers first, then agents and the orchestrator after the
    playbook decision), with evals written first?
11. Close or rewrite the 2026-10-14 quota-rule todo? Its cadence (10 minutes, 4 hours) was replaced by the Phase
    26 wake rule.
12. Research cache staleness: 30 days (code) or 180 days (design spec)?

Skipped: I did not read the SKILL.md bodies line by line for judge-style quality, did not run any judge, and ran
the checkers only against ai-kit itself with the GSD probe off.
