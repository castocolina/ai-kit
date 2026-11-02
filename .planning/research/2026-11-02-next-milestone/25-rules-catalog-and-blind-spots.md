# Project rules: full catalog, where each piece goes, and blind spots (research, 2026-11-02)

Read-only, checkout at 27337d5. Builds on `23-project-rules-state.md` (skill-by-skill state, defects, history)
and the Round 6 and Round 7 notes in `.planning/milestones/NEXT-MILESTONE-INPUTS.md`; those are not repeated.
Scripts beside this file:

- `25_owner_msgs.py`: short snippets of owner messages matching the rules, hook, worktree and quota keywords
  (skips injected `<...>` messages and subagent turns, masks key-like text); output `25_owner_msgs.out`
  (171 hits: 4 July, 33 August, 67 September, 56 October, 11 November).
- `25_owner_full.py`: prints chosen owner messages in full by timestamp; output `25_owner_full.out`.

## Target vocabulary

Every rule and wish below gets one target:

- **Top rule**: a short mandatory line in the target project's `AGENTS.md`, pointing to a runbook when it needs
  detail.
- **Playbook**: an event-keyed asset inside the new skill. The agent reads it when the event happens. It is not
  copied into the target project.
- **Runbook**: `docs/run-book/<topic>.md` in the target project. The skill generates it from a template, and the
  developer adapts it. Humans read it as well as agents.
- **README**: a section in the target project's README.
- **Config**: a Makefile, pre-commit, CI or compose file that the skill generates or edits.
- **Hook**: a host event hook, installed as a setup knob per host.
- **Check script**: a deterministic, stdlib-only checker, kept from today's family and run by a playbook.
- **Drop**: stale, Claude-only, GSD-only or rtk, or moved to another skill.

Proposed playbooks, keyed to the owner's events (2026-10-31 and Round 7):

1. New project.
2. Session start.
3. Worktree created.
4. Task, plan or phase finished.
5. Worktree closed or branch merged.
6. Subagent or cross-AI run delegated.
7. Quota or rate limit hit, or getting close to one.
8. Waiting for CI and the PR review loop.
9. Before an image build or a deploy.
10. Building a feature (the vertical-slice cycle).
11. A decision point (jev).

## 1. Catalog of every rule and check, with its target

Format: what it enforces. Evidence: where the rule comes from. Target.

### House rules (`skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py`, 20 entries)

The September todo (`.planning/todos/completed/2026-09-09-agents-md-rules-checker-skill-wrapping-agent-md-refactor.md`,
17 rules) is the evidence for every rule below that names no other source.

- English-only artifacts, whatever language the conversation uses. Evidence: the September todo, rule 1, and
  ai-kit `AGENTS.md`. Target: top rule, merged with the owner's Round 7 "one clear rule on language and
  interaction" (talk in the owner's language, write files in English).
- Never skip pre-commit checks, except a deliberate red-to-green TDD commit. Evidence: September rule 2. Target:
  top rule. Its Makefile half goes to config.
- Commit compaction: few logical commits per unit of work. Evidence: September rule 3 (the unit is the plan,
  explicitly not the phase). Target: playbook "task, plan or phase finished", plus a one-line top rule.
  **Conflict:** memory `feedback_compact_history_per_phase_by_subagent.md` (October) says per phase, through a
  reporting subagent. Round 7 says "per phase, plan or task depending on the framework". The latest wording wins,
  so the unit depends on the framework, and the playbook must state the unit for each framework.
- Every plan gets cross-AI plan review and cheap cross-AI execution, with path-agnostic commands. Evidence:
  September rule 4 (it also had a reviewer order, never coded). Target: split it.
  - "Path-agnostic commands" joins the no-absolute-paths top rule.
  - The cross-AI part goes to the GSD section of the playbook "subagent or cross-AI run delegated", active only
    when GSD is detected. It is not a general top rule.
- rtk hook rewriting. Evidence: September rule 5. Target: **drop**. The owner removed rtk (the rtk uninstall
  section and the 2026-10-18 hooks todo: "the hooks must not mention rtk at all"). Also drop rtk from:
  - `_shared/ai_kit_rules_common/tool_presence.py`;
  - the agents SKILL.md trust-gate text and worked example;
  - `.claude/cli-environment.md` (3 mentions);
  - this repo's `AGENTS.md` (1 mention).
- Prefer rg, bat, sd, fd and eza when installed. Evidence: September rule 6. Target: hook. The session briefing,
  tool advisor and tool reminder already exist in `tools/hooks/`. In AGENTS.md this is at most a pointer, since
  an always-on line does not change behaviour over a long session (2026-10-18 todo).
- Prefer `codegraph_explore` when `.codegraph/` exists. Evidence: September rule 7, which had detail since cut:
  `codegraph init` in an unindexed workspace, `sync` only without the watcher, code only. Target:
  - hook (session start or worktree created, 2026-10-24 todo item 1);
  - one top-rule line when the index exists;
  - runbook "code navigation" for the detail, including the memory rule "sync before mapping".
- Use graphify for doc-aware indexing and re-index on purpose. Evidence: September rule 8. Its cut detail: under
  GSD the output goes to `.planning/graphs/` through `graphify.enabled` and `auto_update`, standalone runs use a
  post-commit hook and `./graphify-out/`, and graphify works together with codegraph. Target: same as codegraph.
  The GSD half goes to the GSD section. A refresh at phase close would be our own addition (Round 1, checked).
- Kill the ephemeral processes and windows spawned for e2e checks. Evidence: September rule 9. Its cut detail:
  the opencode/Bun temp-copy leak and disk checks. Target: top rule (one line), plus the playbook "task, plan or
  phase finished" (a cleanup step), plus a runbook that restores the leak and disk detail.
- Scratch files go under `./tmp/`, which is gitignored. Evidence: September rule 10. Target: top rule. The "new
  project" playbook adds `tmp/` to `.gitignore` (config).
- Keep the README and nested docs current. Evidence: September rule 11. Target: top rule, plus a docs-freshness
  step in the playbook "task, plan or phase finished".
- No absolute paths in source, tests or assets. Evidence: September rule 12. Target: top rule. A check script
  could grep for a home-path prefix (blind spot).
- No excuse-driven deflection on a failing test or bug. Evidence: September rule 13. Target: top rule.
- Verify gray-area or new topics against current sources. Evidence: September rule 14. Target: top rule.
- Theory, hypothesis, spike before planning new territory. Evidence: September rule 15. Target: playbook "new
  project" or "building a feature" (a planning step). This is framework-neutral, so `/gsd-spike` is only one
  option.
- No unexplained uncommitted files when a plan closes. Evidence: September rule 16. Target: playbook "task, plan
  or phase finished", plus a top rule.
- Concise docs, no narration of abandoned paths. Evidence: September rule 17. Target: top rule.
- The main agent arms the session wake before a multi-plan run. Evidence: Phase 26, and the owner's 2026-10-14
  message. Target: playbook "quota or rate limit". The executors already arm it, so this is no longer a general
  top rule. A one-line top rule ("long unattended runs follow the quota playbook") replaces it.
- Cross-AI runs go through `.planning/scripts/cross-ai.mjs` and never switch CLI or model. Evidence: Phase 26,
  and the owner's 2026-10-24 decision that the detail lives in the runner and AGENTS.md gets "3-4 lines that
  point to the runner". Target: GSD or cross-AI section of the playbook "subagent or cross-AI run delegated".
  **Stale part:** "never switch" turns into opt-in runtime and model escalation flags under the Round 1/2
  decision, so the wording must follow the runner's new flags.
- Parallel unit tests use floor(40% of the available CPUs) workers, never a hardcoded count. Evidence: Phase 26,
  and the owner's 2026-10-14 message ("unit tests should run in parallel and not sync"). Target:
  - config (a generated test runner target, in the right form for each stack);
  - runbook "testing";
  - a one-line top rule.

### Agents checker behaviour, beyond the rule list

- Broken relative links in AGENTS.md and the files it links to directly. Evidence: Phase 9. Target: check script,
  run by the playbooks "new project" and "task, plan or phase finished".
- Matching by signal phrases (literal substring). Evidence: Phase 6 and 9. Target: **replace**. Generated top
  rules and runbook pointers sit inside marked begin/end blocks (the banner-block pattern the status-line modules
  already use). The check then becomes "block present and current", which is exact, instead of guessing from
  phrases. Phrase matching stays only for hand-written files.
- Edits through `/agent-md-refactor`, Steps A-D. Evidence: Phase 6 and 9. Target: playbook "new project" (create
  or refresh AGENTS.md). Keep the backup and diff steps. `/agent-md-refactor` stays optional.
- Reads AGENTS.md, else CLAUDE.md. Evidence: Phase 9. Target: **change** to the Round 7 wish:
  - AGENTS.md is mandatory, and CLAUDE.md is an optional symlink to it;
  - AGENTS.local.md is respected, or created instead of CLAUDE.local.md;
  - curated-config sets `claude_md_path` explicitly.

  Live fact: ai-kit has no CLAUDE.md at all, `.planning/config.json` has `claude_md_path: "./AGENTS.md"`, and
  this Claude Code session loaded `AGENTS.md` as project instructions. That was observed, not checked against
  the docs.
- GSD identity probe: runs the target repo's own gsd-tools. Evidence: Phase 26. Target: the GSD section of the
  playbooks. It needs the two sibling skills, so it stays install-group bound.

### Makefile checker

Evidence for all: the September todo, rule 2 (the target shape), the design spec
`docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`, and the v1.2 Phase 10 success criteria
cited in `makefile_checker.py`.

- Required targets: `setup-env`, `validate`, `test`, `test-unit`, `test-integration`, `e2e-test`, `arch-test`.
  Target: config (generated by "new project"), plus a check script, plus runbook "make targets". The owner's
  newer names `setup-dev` and `setup-docker` (Round 7) are not in the list. Decide the canonical name
  (`setup-env` versus `setup-dev`) once.
- The `validate-<category>` aliases (format, lint, security, duplicate, dead). Target: config plus a check script.
  ai-kit itself fails five of them, so the owner should confirm the rule before it is enforced.
- Help and fail reachability (an unknown target gives help). Target: config template plus a check script.
- At most three lines per recipe, longer logic goes to a script. Target: check script, plus the existing memory
  rule "scripts in files, not inline". ai-kit fails it once (`e2e-docker`).
- A docker `*-up` target builds its image first. Target: config plus a check script (shared with docker).
- A `shellcheck` target once there are five or more bash scripts. Target: config plus a check script.
- Fast-before-slow order (advisory). Target: runbook "make targets" (a heuristic, never verified).
- Missing tool categories go to `blocked` and need per-stack research, cached for 30 days. Target: playbook "new
  project" (a research step at invocation time, as Round 7 asks), plus the cache as a skill script. **Open:** 30
  days in code against 180 in the design spec.
- September wishes never coded: one Makefile target per pre-commit hook, every tool in its own target,
  per-language formatter conventions. Only parity and the aliases cover them. Target: config template
  (generated 1:1 from the hooks).

### Pre-commit checker

Evidence: the September todo, rule 2, the design spec, and v1.2 Phase 11.

- Parity between hooks and single-tool Makefile targets, both ways. Target: check script, plus config generated
  in pairs.
- Slow hooks split into a `pre-push` stage. Target: config template plus runbook "pre-commit and CI split" (the
  Round 7 research topic).
- Hooks classified into six categories (formatting, type checking, linting, security, duplicate code, dead code),
  with a confidence of baseline, cache or inferred. Target: check script. Round 7 asks the classifier to use jev,
  as a black box, with this table as the fallback.
- Out-of-taxonomy groups (test runners, the pre-commit-hooks hygiene fixers). Target: check script.
- A duplicate-code or dead-code tool is missing. Target: check script plus config.
- Enable-everything configs (ruff `ALL`, golangci `enable-all`). Target: check script.
- Ruff-specific: type-safety rules, preview without a version pin, a child config dropping its parent's ignore
  list. Target: check script, Python section.
- Redundant or complementary tool pairs (10 rows: ruff S/bandit, ruff/vulture, eslint-plugin-security/semgrep,
  knip/ts-prune, checkstyle/PMD, PMD/SpotBugs, cargo-audit/cargo-deny, cargo-machete/cargo-udeps,
  staticcheck/golangci-lint, gosec/govulncheck). Target: runbook "tooling per stack" (a cached research output),
  plus a check script.
- `check-limitation` advisories (unreadable ESLint flat config, for example). Target: check script.

### Arch checker

Evidence: the September todo, rule 2 ("rails/tests that block agent-introduced architecture violations"), and
v1.2 Phase 12.

- An arch-test-shaped target exists and `test` reaches it. Target: config plus a check script.
- The backing test file parses with `ast` only (Python). Target: check script. It must also see through a test
  runner, since ai-kit's own target fails here.
- One canonical tool per stack: import-linter, dependency-cruiser, ArchUnit. Rust and Go are a known gap.
  Target: runbook "architecture tests" (the Round 7 "arch tests by layers" topic, researched at invocation).
- Real layering enforcement was cut in v1.2. Target: runbook template with rules by layer, plus the vertical-slice
  playbook. Generic AST tooling is not coming back.

### Docker checker

Evidence: the design spec (the target names and the bounds are its own) and v1.2 Phase 13.

- The eight `docker-*` targets: up, health, stop, clean, prune, events-up, events-monitor, events-test. Target:
  config template. The list is a default the developer can change, so a fixed name list is not a check.
- `docker/local/README.md` holds the local-dev runbook. Target: runbook (`docs/run-book/docker.md`, per Round 7:
  "run everything in docker, see ..."). Keep the old path, or move it.
- Healthcheck bounds: timeout up to 2 s, start period up to 10 s, interval up to 5 s. Target: check script plus
  the compose template.
- `depends_on` uses `condition: service_healthy`. Target: check script plus the compose template.
- Local-dev services use a bind mount plus a hot-reload command. Target: check script, plus the compose override
  template, plus the hot-reload table per stack.
- Docker build before up. Target: shared with makefile.

### CI checker

Evidence: the design spec and v1.2 Phase 14.

- CI steps reuse a Makefile target, pre-commit hook, `package.json` script or Gradle task instead of calling the
  tool directly. Target: check script, plus a CI template that calls `make` targets.
- Package manager from the lockfile (pnpm, yarn, bun, npm), and the Gradle plugin table. Target: check script
  helper.
- Gaps: no GitLab `include:` (it sees almost nothing of ai-kit's own CI), and CircleCI, Jenkins and Azure are
  ignored. Target: a fix in the check script. The Round 7 question "what CI must run before an image build or a
  deploy" goes to the playbook "before an image build or a deploy" and runbook "ci".

### Shared library (`skills/_shared/ai_kit_rules_common/`)

- Stack detection from marker files: Python, Node, Go, Java (Maven or Gradle), Rust. Target: a skill script.
  Round 7 adds per-ecosystem research at invocation time for anything else.
- Tool catalog (900 lines): six categories, the baseline tools per stack, the out-of-taxonomy groups, tool pairs,
  the parallel test forms. Target: skill reference data, plus runbook "tooling per stack" generated per project.
- Stack cache: `~/.cache/ai-kit/<namespace>/stack-refs`, 30 days, a `(source: ...)` citation required. Target:
  skill script. Keep the citation rule (AGENTS.md: certainty matches sourcing).
- Tool presence (rtk, graphify, codegraph, modern CLIs, `.planning/`). Target: skill script, without rtk. It
  overlaps `tools/hooks/detect.py`, so share one detector.
- Criticality and remediation shape (critical, high, medium, advisory; `remediate`, `blocked`, `notices`).
  Target: check script output, unchanged.
- Makefile, pre-commit and YAML text parsers (stdlib only). Target: skill scripts. Vendor them (report 14).

## 2. The October context capture: what the owner asked

From the owner messages (`25_owner_full.out`), the memories and the todos:

- **2026-10-14, quota.** Two separate things. First, a shell-level wake every hour, so a session that hits its
  limit after 15 minutes can continue about 45 minutes later. Second, when a cross-AI subprocess shows "limit
  reached", retry every 10 minutes for up to 4 hours. Todo `2026-10-14-agents-md-quota-schedule-rules-...`
  (still pending, superseded) also asked to build the directive into spec-review and spec-execute, not only into
  AGENTS.md. Delivered differently:
  - the wake fires reset + 60 s, else hourly, with a 24-fire cap;
  - the cross-AI hard tier waits whole minutes from `retry_after_s` (600 s in the worked example).
- **2026-10-14, rules.** "Unit tests should run in parallel, not sync" (this became the CPU-share rule). "All the
  skills in question must be language-agnostic and write the right thing into AGENTS.md's rules section."
- **2026-10-14, quota routes.** Router combos recover after minutes or hours. Direct Zen or Cursor API billing
  errors do not. Memory `project_quota_recovery_by_route.md`.
- **2026-10-17.** "No reason to wait if the quota was already restored." This is early resume: poll, do not only
  wait for the stated reset.
- **2026-10-18, hooks as knobs.** Every hook (session briefing, PreToolUse advisor, PostToolUse reminder,
  decision system, PreCompact) is its own setup knob, visible to the user. Mostly delivered in Phases 21.1-21.3
  (`tools/hooks/README.md`).
- **2026-10-23.** "Next time use schedule to auto-wake when the window quota resets" (memory
  `feedback_schedule_wake_on_quota_limit.md`). "From now on ship each feature or phase and apply it to the current
  machine" (memory `feedback_ship_each_phase_to_machine.md`). A hook that is "unmeasured" or off by default is
  of no use to the owner.
- **2026-10-24, failure ladder.**
  - The detail lives in `cross-ai.mjs`, with tests. AGENTS.md or CLAUDE[.local].md gets a short pointer of 3 or 4
    lines.
  - On quota or rate-limit errors the orchestrator retries the same lane up to 3 times, then changes session up
    to 3 times, then reports with evidence and waits.
  - A soft backoff with a configurable ratio (for example 1.5x, 5 tries) comes before a session reset. The hard
    tier waits 10, 15 or 30 minutes and notifies the user.
  - The preferred runtime is a parameter. Quota errors differ by provider and must be catalogued from logs.

  Memory: `feedback_external_run_retry_ladder.md`.
- **2026-10-24, hooks todo.** Worktree or new-checkout indexing advice at session start (detect a linked worktree
  from `git rev-parse`, since a Claude Code `WorktreeCreate` hook would take over worktree creation),
  install-relative doc paths, and compaction metrics.
- **2026-10-28 and 2026-10-29.** "Set up an automatic schedule every 5 h from 21:31 to wake if the quota limit
  is hit." Next message: "I told you to activate it every 5 h from 21:31 and you did what you wanted." The owner
  wants the wake to follow the 5-hour window grid. Nothing in `ai-kit-session-wake` does that today (no 5-hour
  or window logic in the skill or its code).
- **2026-10-30.** GSD is Claude Code-only scope. At milestone end, compact the history, audit, close, merge to
  main, push, and clean merged or disposable worktrees, using jev for the gray cases. Use the referees, not
  native Opus.
- **2026-10-31.** "Clean branches and worktrees already merged, considering they may show in the tree if you
  compare hashes and not content." Then the founding message of this idea: the rules "should become one skill
  with several play rules, playbooks or runbooks". The events are: a new project (Makefiles, pre-commit, tests,
  checks), a new worktree, a plan or phase finished in open-GSD, a worktree closed, a subagent delegated, quota
  errors, "and things like that". The goal: AGENTS.md is not overloaded, and the agent knows what to do in each
  case. Memory `project_rules_skills_playbook_idea.md`, backlog 999.16.
- **2026-11-02.** Desktop alerts about quota must check their paths first, and must work on macOS as well as
  Bazzite. Then Round 7: hooks as knobs per host (direct, or through herdr), the stage events (the
  worktree-created setup, phase-end teardown, compaction, local or AWS e2e, CI wait, the PR review loop),
  AGENTS.md as the mandatory file, vertical slices, the 5-hour window, and anticipating the limit.
- **Standing October memories that are really playbook content:**
  - time-box subagents to about 20-30 minutes;
  - scripts in files, not inline;
  - run status pings carry the local time;
  - no stops in permissive runs;
  - jev at every decision point;
  - the executor real-home guard (`AI_KIT_REFUSE_REAL_HOME=1` plus a config mtime audit);
  - GSD is project-local only;
  - run `codegraph sync` before mapping;
  - explain before asking;
  - plain words, no codes.

## 3. Owner wishes mapped to targets

- One language and interaction rule. Target: top rule.
- jev for decisions (advisory, a black box, the skill works without it). Target: top rule (one line) plus the
  playbook "decision point".
- AGENTS.md mandatory, CLAUDE.md a symlink, AGENTS.local.md respected. Target: playbook "new project" (detect and
  create) plus a check script (the symlink exists and points to the right file). Curated-config `claude_md_path`
  goes to the curated-config skill.
- Vertical slices, with the stage cycle mocks, basic front, backend, database, real data, security, infra,
  observability, accessibility. Target:
  - a top rule with the top-3 "never / avoid" lines (for example: never build layer by layer with nothing to
    show; never wire real data before the mock slice works; avoid adding security, infra or observability at the
    end);
  - the playbook "building a feature", which names the matching skills for each stage (ponytail, impeccable, the
    security and infra skills), found by discovery and not hardcoded, per the Round 5 lens design.
- Worktree created: `make setup-dev`, `setup-docker`, the local GSD install, indexing advice. Target: hook (the
  session-start worktree detection from the 2026-10-24 todo), the playbook "worktree created", and the Makefile
  targets (config).
- Phase, plan or task finished: destroy the worktree, compact the commits, run a local or AWS e2e, wait for CI,
  run the review loop. Target: playbooks "task, plan or phase finished", "worktree closed" and "waiting for
  CI". A hook works only where the framework emits an event: open-GSD has hook points, and Claude Code
  `TaskCompleted`/`Stop` are candidates to verify. Elsewhere the playbook is called from the framework's own
  step.
- Ship each phase to the machine. Target: playbook "task, plan or phase finished". It is ai-kit-specific (install
  to the machine), so in other projects it reads "deploy to the dev environment".
- Merged-branch cleanup by content, not by hash. Target: playbook "worktree closed", plus a check script
  (`git cherry` or a tree comparison).
- Quota: wake at the reset, poll for an early reset, keep the 5-hour windows on a fixed grid, anticipate the limit
  before the window ends. Target: playbook "quota", plus a hook (the existing `StopFailure` row is experimental
  and its payload unverified), plus session-wake changes (window grid, early-reset polling: neither exists). The
  "anticipate" part can reuse the status line's pace numbers (section 5).
- Failure ladder (retry, session change, hard tier, notify). Target: it stays in `cross-ai.mjs` (owner decision
  2026-10-24). The playbook only points to it.
- Desktop quota alerts work on macOS and Linux, with their paths checked first. Target: the notification work
  (Theme 4), not this skill.
- Per-ecosystem tooling: pre-commit for Java, Go and Node; CI before an image build or deploy; the pre-commit and
  CI split; arch tests by layers. Target: playbook "new project", with a research step at invocation time,
  cached with sources, writing runbooks "tooling per stack", "ci" and "architecture tests".
- Hooks as knobs per host, with a view of what is enabled where. Target: `tools/setup.py` and the wizard (the
  existing hook rows), not the skill. The skill's playbooks name the hook to enable.
- Content split: README for the human quick start, AGENTS.md for the top rules plus pointers, runbooks for the
  how. Target: the playbook "new project" writes all three, using `crafting-effective-readmes` for the README.

### To drop or move

- The rtk rule and every rtk mention (listed in section 1).
- Claude-only wording: "Claude Code's `Agent` tool with `subagent_type`" in Step C. Use host-neutral words
  (memory: native wording must be host-agnostic).
- GSD-only rules (cross-AI plan rules, arming the wake, the runner pointer): move them to a GSD section that loads
  only when open-GSD is detected. The runner pointer belongs to the cross-AI skill's install.
- The old reviewer order (`*my-plan-review`, GLM, chatgpt, Opus): already gone. Keep it out, since referee names
  are not hardcoded.
- The 2026-10-14 quota todo: close it as superseded. Its "also inside spec-review and spec-execute" part is
  covered by the executors arming the wake and by the runner's hard tier.
- Phrase-signal matching as the main check: replace it with marked blocks (section 1).
- The orchestrator subprocess fan-out (`-all`) becomes the skill's "audit everything" playbook running the
  check scripts in-process. That also removes the sibling-lookup failure in copy installs.

## 4. Blind spots, ranked by value

1. **Secrets.** A gitleaks or detect-secrets pre-commit hook, `.env` in `.gitignore`, never printing keys, and
   secrets kept out of runbooks. Today the catalog files `detect-private-key` under hygiene and has no secrets
   category (its "security" means static analysis). ai-kit elsewhere: GitLab's Secret-Detection template in
   `.gitlab-ci.yml`, and memory rules (never print keys, credentials live in one file). Target: config plus a
   top rule.
2. **Isolating agents from the developer's real config.** Tests never use real home config, and unattended
   executors run with the real-home guard. Agentic runs here have full permissions (memory) and broke this once.
   ai-kit elsewhere: its own AGENTS.md test rule, and `AI_KIT_REFUSE_REAL_HOME` in tests and goal-prompt. Target:
   top rule plus the playbook "subagent delegated".
3. **Branch model and merge flow.** Base branch detection (main only, or dev, staging and main), protected
   branches, no push without consent, the order of remotes, merge locally before any push. ai-kit elsewhere: the
   curated-config redesign (Round 1 base-branch detection), memories (remotes, ship-per-phase, milestone-end
   flow). Target: runbook "branches and release", plus the playbook "worktree closed".
4. **The test pyramid as one runbook.** Unit, integration, e2e and arch tiers, the CPU share, the
   one-process-per-module runner, the e2e-based definition of done, and local versus cloud e2e (the owner names
   AWS e2e, but nothing covers cloud credentials, cost or teardown). ai-kit elsewhere: its AGENTS.md Testing
   section, `tools/run_unittest_parallel.py`, the goal-prompt e2e reference. Target: runbook "testing" plus
   config.
5. **Dependency updates and supply chain.** Lockfiles committed, a legitimacy check before adding a package,
   pnpm preferred, Renovate or Dependabot, pinned versions old enough. ai-kit elsewhere: the memory
   package-gate rule. The artifact rules (exact version, at least two weeks old) exist only for one host tool.
   Target: runbook plus config.
6. **Rollback and destructive operations.** Ask for confirmation before reset, clean or a forced push. Make
   database migrations reversible. Keep a deploy rollback step. ai-kit elsewhere: the AGENTS.md "preserve
   unrelated dirty work" rule. Target: top rule plus runbook. Data migrations fit the "database" stage of the
   vertical-slice playbook.
7. **Commit message conventions.** ai-kit uses a `type(scope): subject` style, but nothing states or checks it,
   and there is no commit-msg hook. Target: config plus a top rule.
8. **Agent tooling freshness.** A stale codegraph or graphify index, the GSD project-local install in new
   worktrees, a stale research cache. ai-kit elsewhere: memories and the 2026-10-24 hooks todo. Target: hook
   plus the playbook "worktree created".
9. **Process and disk hygiene beyond "kill it".** The cut opencode/Bun temp-copy leak, disk checks, leftover
   containers and volumes (`docker-prune` exists only as a target name). Target: runbook.
10. **Release and versioning.** A changelog, version bumps, tags. Nothing covers this today. It is a low need for
    personal skills and a high one for apps. Target: runbook "branches and release".
11. **Multi-repo work.** The owner relays rules between llm-env and ai-kit ("llm-env-main -> ai-kit"), and the
    agent-toolkit hosts the judge. Nothing says where a shared rule lives or how the copies stay in sync. Target:
    runbook. Low urgency.
12. **Observability and accessibility.** These are named only as slice stages, with no checks or tooling per
    stack. Target: the playbook stage notes, researched at invocation.
13. **Licensing.** No license check for the project or its dependencies. This matters only when publishing
    (skills.sh distribution). Target: README plus runbook. Low.
14. **Incident runbooks.** Low value for a solo developer. Target: a template only when the project deploys.

## 5. Existing ai-kit facts the new skill must respect

### This repo's `AGENTS.md`

- Skill code stays stdlib-only. Any non-stdlib tool goes through the guard and re-exec pattern.
- Config writes are atomic (`mkstemp` plus `os.replace`), and JSONC edits are surgical. This matters when the
  skill edits a target's config.
- No result is shown with more certainty than its source. Inferred classifications are flagged. This includes
  jev answers and cached research.
- A new SKILL.md passes the skill-judge loop: no critical or high finding, or a grade of B or better, and no
  regression.
- Skills follow the Agent Skills standard and stay host-portable. Hooks are host-specific, so each playbook needs
  a manual-call path where a host has no event (Cursor, opencode, pi worktree events are unverified).
- One logical commit with its tests and docs. Never `--no-verify`, except a deliberate red commit.
- Preserve dirty work, with no absolute paths, and use `./tmp/` for scratch.
- Test tiers through `tools/run_unittest_parallel.py` (new tests join the unit group automatically). The CPU
  share is capped at 40% and can only be lowered.
- Real config never serves as a fixture.
- `tests/test_arch.py` rules need a non-vacuity counterpart. The deferred whole-tree layering suite is backlog
  999.3.
- Workflow rules: amend REQUIREMENTS and ROADMAP on contradictions; spike before planning new territory; record
  out-of-scope ideas in the backlog with a goal.

### Session wake (`skills/ai-kit-session-wake/SKILL.md`)

- One systemd user-timer wake per session, Linux only. Cursor, or no user manager, exits 3: no surviving wake.
- An hourly fire, a hard stop after 24 counted fires. A fire while the host is still alive only logs and still
  counts.
- A reset-timed wake comes from `--reset-text` or `--reset-at`, at the reset plus 60 s (`ARM_WINDOW_S = 60`), and
  is always labelled inferred. A live stall resumes only through the in-session one-shot companion, and only
  when it is reset-timed.
- Never arm, `done` or `disarm` from a cross-AI child or a subagent. Never resume "most recent". Never guess a
  session id or pid. Never switch harness, provider or model on resume.
- The `StopFailure` rate-limit hook is opt-in and experimental, and its payload is unverified.
- **Not present:** alignment to the 5-hour window grid (the 2026-10-28 request), polling for an early reset (the
  2026-10-17 "no reason to wait"), and warnings that usage is getting close to the limit. These are new
  work in session-wake or the quota playbook, not existing behaviour.

### Status line gauge

- Each quota window shows spend % against elapsed % of the window. Bands on the gap `|used - elapsed|` in points:
  up to 5 green, under 11 yellow, up to 15 orange, above 15 red (`util_gap_color` in `tools/common_types.py`).
  The sign is `+` when under pace and `-` when ahead.
- Window keys come from the host (`five_hour` gives `5h`, also `seven_day`). Cursor quota has three segments: API,
  included, extra.
- This is the data the "anticipate the limit" wish needs. A playbook step could read the same pace numbers, for
  example: when the gap is red and ahead of pace, arm the wake and slow down. That means sharing the computation
  and not re-deriving it, and it holds only on hosts that report windows (Claude Code; Cursor through its API).

### jev black-box rule (NEXT-MILESTONE-INPUTS skills discussion, `skills/jev-fast-decision/SKILL.md`)

- Every skill that classifies uses jev for quick typed decisions with a certainty, and keeps working when jev is
  absent.
- The fallback order (Laya, then a remote with consent, then the native model) lives inside jev, and callers do
  not re-implement it.
- Answers are advisory. `needs_fallback` means the agent decides itself. No jev answer is a gate.
- Consequences for the new skill:
  - jev can classify hooks into categories, pick the playbook for an ambiguous event, and score near-miss rules;
  - the deterministic tables stay the fallback;
  - jev answers are labelled as inferred.

### Other constraints from earlier rounds

- The family installs as a group. Vendoring the shared library fixes the copy-install break, and one skill
  removes the sibling lookup.
- The GSD probe needs `ai-kit-gsd-curated-config` and `ai-kit-spec-review` installed beside it.
- The skill text carries behaviour, not history (the tooling todo), with no referee names and no rtk.
- GSD stays project-local and Claude Code-scoped (owner, 2026-10-30).

## Open questions for the owner, in plain words

1. Which unit does commit compaction use: the plan (September), the phase (October memory) or "depends on the
   framework" (Round 7)? Proposed answer: per framework, with the unit stated in the playbook.
2. Is the bootstrap target called `setup-env` (current checks), `setup-dev` (Round 7), or both, with
   `setup-docker` beside them?
3. Should the five `validate-<category>` aliases and the three-line recipe cap stay required? ai-kit fails them
   today.
4. Should the quota playbook also arm a fixed 5-hour-grid wake from a given start time (as asked 2026-10-28), on
   top of the wake at the reset plus 60 s?
5. Should the playbook react to the status line's pace gauge (red and ahead of pace means arm the wake or slow
   down), or only to actual limit errors?
6. Do runbooks live at `docs/run-book/<topic>.md` in every project, including the docker one (now at
   `docker/local/README.md`)?

Skipped: I did not read the seven SKILL.md bodies again (report 23 covers them), did not verify per-host hook
event lists or whether Claude Code reads AGENTS.md by design (only observed in this session), and ran no
checker. Risk: the October owner messages were matched by keyword, so a wish phrased without those words may be
missing. The September-to-August hits (100) were counted but not read.
