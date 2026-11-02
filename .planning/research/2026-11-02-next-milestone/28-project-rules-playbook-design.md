# Project rules as one skill of playbooks: design synthesis (2026-11-02)

Read-only synthesis. No code run beyond line counts. Sources in parentheses:

- "report NN" means `tmp/next-milestone-research/NN-*.md`.
- "Round N" means that round in `.planning/milestones/NEXT-MILESTONE-INPUTS.md`.
- "AGENTS.md" means this repo's house rules.
- **PROPOSAL** marks my own design choices. Everything else traces to a source.

Facts used throughout, all from reports 23 and 25:

- Seven skills today: about 1,600 SKILL.md lines and about 8,100 lines of checker code. The shared library adds
  2,564 lines, and the family has nine flat test files.
- Every checker prints deterministic JSON.
- Only the agents checker edits files.
- Copy installs break all seven.
- ai-kit fails its own rules 11 times.

## 1. Strategy

The options:

- **(a) Keep the seven checkers plus the orchestrator.**
  - Owner's wish: fails it. Round 7 asks for one skill whose rules are playbooks and runbooks, with scripts that
    decide what to generate and where. Checkers that only report never generate anything.
  - Judge: seven descriptions, seven evals sets and seven judge runs. None has evals today, so each one starts
    with a high finding (report 23).
  - Copy installs: the shared library has to be vendored six times, and the family still installs as a group
    because of the sibling lookup and the GSD probe (report 14).
  - Cost and testability: cheap per call and well tested. But a whole-repo audit runs six subprocesses with a
    30 s timeout each (report 23).
- **(b) One skill made only of playbooks, judged by the model.**
  - Owner's wish: fits it.
  - Judge: every check turns into a model judgement. Evals lose verifiable assertions, and D8 has to trace many
    model-side branches (report 15).
  - Cost: every call reads the whole repo on a strong model.
  - Certainty: weaker. AGENTS.md requires that a result is never shown with more certainty than its sourcing,
    and an unlabelled model guess breaks that.
  - Waste: about 10k lines of tested, deterministic detection would be thrown away.
- **(c) Hybrid: one skill with event and area playbooks, plus the kept deterministic scripts.**
  - Owner's wish: fits it. The playbooks and runbooks are assets, and scripts decide what to generate and edit
    (Round 7).
  - Judge:
    - One SKILL.md routes to gated playbooks, which suits D5.
    - One evals set uses the existing JSON output for assertions (report 23: "every checker emits deterministic
      JSON, which suits verifiable assertions").
    - The `scripts/` folder plus a script test earns the 5/5/5 split in D7 (report 15).
  - Copy installs: the shared library moves inside the one skill, so nothing needs vendoring and no sibling
    lookup is left. Only the `_shared` package uses that folder (Round 2 note).
  - Portability: the scripts are stdlib Python, the playbooks are host-neutral text, and hooks are optional
    pointers.
  - Cost: an event playbook is small and runs on any model. Only bootstrap, and audit with fixes, need the strong
    model.

**Recommendation: (c).** It is the only option that meets the owner's wish and the judge rubric, and it keeps
the tested code.

The key move (**PROPOSAL**): the branching lives in the `plan` script's output, not in the prose. The script
returns only the steps that apply, so each playbook reads as a straight checklist. D8 then traces few model-side
branches, and the branches that remain are unit-testable.

## 2. The skill

### Name (PROPOSAL)

`ai-kit-project-rules`.

- It keeps the trigger words users already say: "project rules", "house rules", "AGENTS.md rules".
- It maps cleanly from the seven old names.
- Alternative: `ai-kit-project-playbooks`. That one is more accurate, but nobody types it.

### Folder layout (PROPOSAL)

```
skills/ai-kit-project-rules/
  SKILL.md                 # under ~250 lines: modes, router (event/area -> file), delegation map, NEVER list, gotchas
  playbooks/<event>.md     # one per event; load only the one named by the event ("do NOT load the others")
  runbooks/<topic>.md      # templates for the target's docs/run-book/<topic>.md, with baked facts and placeholders
  assets/                  # agents-top.md.tmpl, Makefile/pre-commit/CI/compose fragments, hooks.toml.tmpl,
                           # gitignore fragment, post-checkout.sh.tmpl
  references/              # tooling-baseline.json (from tool_catalog.py: categories, stage per category, tool pairs),
                           # research-protocol.md, instruction-files.md (who reads what), events.toml (catalogue, §6)
  scripts/project_rules.py # one CLI: detect | plan <event|area|bootstrap> | apply <plan.json> | check [areas] |
                           # audit | cache get|put | --help; JSON on stdout
  scripts/project_rules_lib/  # the moved _shared library + the six checker packages + new modules
  evals/evals.json, evals/trigger-queries.json, evals/files/<fixture repos>
```

Tests stay flat: `tests/test_ai_kit_project_rules_*.py` in the unit group (AGENTS.md). Whether they move to
`tests/skills/<name>/` follows whatever the re-judge phase decides for every skill (report 15).

### Where generated content lives in the target project

- **AGENTS.md:** only a marked block, `<!-- ai-kit:project-rules:begin template=N -->` ...
  `<!-- ... :end -->`. It holds the top rules and the runbook pointers, and the rest of the file belongs to the
  developer. Checking that the block is present and current is exact. This replaces matching on signal phrases,
  as report 25 suggests. Phrase matching stays only as an advisory check on hand-written files.
- **`docs/run-book/<topic>.md`:** the path the owner gave as an example (Round 7). Each file is generated with a
  header line `<!-- ai-kit:generated topic=X template=N body-sha256=H -->`. **PROPOSAL** for refreshing:
  - If the body hash still matches, the developer has not touched it, so regenerate it.
  - Otherwise the model proposes a diff and asks.
  - No state file is needed.
- **README:** one "Development" quick-start section, written through `crafting-effective-readmes` when that skill
  is present (report 25), otherwise from a template.
- **Config:**
  - Missing targets, hooks and jobs are added inside a marked comment block, or as new files.
  - Existing entries are never rewritten without the owner's confirmation.
  - Writes are atomic (AGENTS.md).
- **`.aikit/hooks.toml`:** the project's event knobs (§6). It sits in the same `.aikit/` home as
  `review-spec.toml` (report 24).
- **`.gitignore`:** `tmp/`, `.env`, `AGENTS.local.md`.
- **Host wiring for the two AGENTS files** (§5): for example an `instructions` entry for `AGENTS.local.md` in the
  project's opencode config. JSONC edits are surgical and atomic (AGENTS.md).
- **`docs/run-book/events.md`** (**PROPOSAL**): a compact version of the event playbooks, so that a contributor
  or host without ai-kit still knows what to do. The playbooks themselves stay inside the skill (report 25).

### Event playbooks

Format for each: trigger; what it writes and where; script part versus model part; research.

1. **bootstrap**: new project, or adopting the rules in an existing one.
   - Trigger: a manual call ("set up project rules"). This is the new-project event (report 25).
   - Writes: every target above.
   - Script: `detect`, then `plan bootstrap`, then `apply` (marked blocks and new files only).
   - Model: adapting each runbook to the project, choosing tools after research, and merging with hand-written
     rules. Runs on the strong model with the delegation map (§3).
   - Research: yes, per area (§3).
2. **session-start**
   - Trigger: the host's SessionStart, through the dispatcher's one-line pointer (report 24), or a manual call.
   - Writes: nothing. Prints at most one line.
   - Script: `detect --quick`. It checks:
     - whether the AGENTS block is current;
     - the instruction-file rule (§5);
     - whether this is a linked worktree with no setup marker (then it routes to worktree-created);
     - whether the codegraph or graphify index is stale (the 2026-10-24 hooks todo).
   - Model: only when the script finds something. No research.
   - It must not repeat what the session-briefing hook already says.
3. **worktree-created**
   - Trigger: git `post-checkout` with an all-zero previous ref. It is host-neutral and tested (report 24).
     Claude's `WorktreeCreate` is optional, and only for worktrees Claude creates.
   - Writes: nothing in the repo.
   - Runs, as an opt-in `run:` list:
     - `make setup-dev`, and `setup-docker` when a compose file exists (the target names are an open question);
     - the project-local GSD install when the project uses GSD;
     - `AGENTS.local.md` from the main checkout, which exists only per worktree (report 27). It is a link,
       unless GSD writes to that file; then it is a copy (§5, step 6);
     - codegraph or graphify indexing advice.
   - Script: a generated `scripts/hooks/post-checkout.sh` wired through the pre-commit `post-checkout` stage
     (report 24). It works without ai-kit installed.
   - Model: only on a failure. No research.
4. **unit-done**: the end of a task, plan or phase, including closing the worktree.
   - Trigger: the workflow skill calls it at its own step. A PostToolUse marker match (`phase complete`,
     `git push`) is only a safety net, because no host has phase events (report 24).
   - Steps, in order:
     1. Gates pass.
     2. Docs are fresh.
     3. No unexplained untracked files.
     4. Spawned processes are killed.
     5. Commits are compacted.
     6. The work ships to the dev environment, or for ai-kit to this machine (report 25).
     7. After the local merge: merged branches and worktrees are removed by comparing content, not hashes
        (`git cherry`, report 25).
   - Script: `check unit-done` reports untracked files, worktrees already merged by content, and gate exit codes.
   - Model: grouping the commits (a standard-model subagent, per the memory "compact history per phase, by
     subagent") and judging whether docs are fresh. No research.
5. **ci-wait**: waiting for CI and reading the automated review.
   - Trigger: after a push or a PR is opened (a marker match).
   - Writes: nothing until the review-loop playbook acts.
   - Claude can use an `asyncRewake` PostToolUse hook that wakes the idle session when CI ends. That mechanism is
     documented but untested (report 24). Other hosts use a time-boxed poll script, `scripts/ci_wait.py`
     (**PROPOSAL**, cap about 30 min), over the platform CLI.
   - Model: summarising the CI result and the bot comments. No research.
6. **pr-review-loop**: receiving the PR review.
   - Trigger: review comments are present after ci-wait, or a manual call.
   - Writes: code fixes, replies and pushes.
     - Pushing and posting need the owner's consent (memory: push only with consent).
     - **PROPOSAL:** ask once per loop run, not per comment.
   - Script: fetch the comments as JSON.
   - Model:
     - jev classifies each comment as fix, reply, disagree or question (advisory, Round 4).
     - The fixes go to the executor.
     - Rounds are capped, with 3 as the default, the same as spec-review's cap (Round 4).
     - Disagreements go to the owner.
     - `receiving-code-review` is reused when present (report 17).
   - Comment text is untrusted data (§7). No research.
7. **delegation**: handing work to a subagent or a cross-AI run.
   - Trigger: SubagentStart on Claude, Codex, Cursor and Copilot (report 24), or a manual call.
   - Writes: nothing. It passes these rails:
     - a time box of about 20-30 minutes;
     - scripts in files;
     - `AI_KIT_REFUSE_REAL_HOME=1`;
     - "no stops in permissive runs".
     These are October memories that report 25 lists as playbook content.
   - The GSD cross-AI part (runner pointer, plan review) loads only when GSD is detected (report 25).
   - No research.
8. **quota**: wake and 5-hour pacing.
   - Trigger: Claude's StopFailure `rate_limit`, the approximations on other hosts (report 24), the runner's hard
     tier, or a manual call. Whether the status-line pace gauge is a trigger is an open question.
   - Writes: nothing in the repo. It arms `ai-kit-session-wake`, which is the mechanism. This playbook is the
     policy (Round 7: "the logic lives in the skill").
   - Steps:
     1. Classify by route. A router route waits. A direct-provider billing error stops and reports (memory,
        report 27).
     2. Finish the piece in hand and checkpoint it.
     3. Arm the wake at the reset plus 60 s.
     4. If the owner wants it: a wake on a 5-hour grid from a fixed start time (asked 2026-10-28, not built), and
        early-reset polling.
   - Conflicts to settle: early polling clashes with session-wake's "never create a repeated or fixed-interval
     job". No cheap quota probe exists. How Claude's 5-hour window starts is unverified (report 27).
   - Script: the session-wake CLI, plus a pace reader. The pace reader needs a status-line cache file, which does
     not exist today (report 27).
   - No research.
9. **audit**: check everything.
   - Trigger: a manual call ("check everything"), a milestone end, or after bootstrap.
   - Writes: a report only. Fixes go through bootstrap's `apply`, after the owner agrees.
   - Script: runs every check in-process and replaces rules-all's subprocess fan-out (report 25). It merges the
     results ordered by criticality, plus the block currency, the instruction-file rule, broken links and whether
     hooks.toml is valid.
   - Model: the summary and the fix proposals.
   - Research: only for `blocked` findings, through the cache.

### Area runbooks

Each one produces `docs/run-book/<topic>.md` in the target project, plus the config named. Expiry days come from
report 26's split.

- **make-targets**
  - Config: Makefile. It covers:
    - the setup target (name is an open question);
    - `validate` and the per-category aliases;
    - the test tiers;
    - help for an unknown target;
    - the three-line recipe cap;
    - the `docker-*` targets.
  - Check: the makefile checker.
  - Research: linter choice 30 days, version pins 90 days.
- **pre-commit**
  - Config: `.pre-commit-config.yaml`. Each hook is paired with a make target ("pattern B" in report 26), and
    whole-project tools move to the pre-push stage.
  - prek is accepted in place of pre-commit (report 26).
  - Check: the precommit checker.
  - Research: security and secrets tools 14 days, linters 30, formatters 90.
- **ci-cd**
  - Config: a GitHub or GitLab template that calls `make`. Shape:
    - jobs run checks, then the image build, then the deploy;
    - actions are pinned by SHA;
    - each job gets minimal `permissions`;
    - workflows are linted with actionlint and zizmor.
  - It includes the "before an image build" and "before a deploy" stage lists (report 26).
  - Check: the cicd checker, which must also follow GitLab `include:`.
  - Research: action SHAs and scanners 14 days.
- **docker-local**
  - Config: the compose override. It sets the healthcheck bounds and `service_healthy`, and uses either a bind
    mount or Compose Watch (`develop.watch`), a gap in today's checker (report 26).
  - Check: the docker checker.
  - Research: the image builder choice, 30 days.
- **architecture-tests** (layers)
  - Config: the stack's tool. The defaults: import-linter, dependency-cruiser, depguard, ArchUnit, Konsist, or a
    crate split plus cargo-deny. The zero-dependency fallback is an AST test (report 26).
  - Model: chooses the layers from the code. This is judgement.
  - Check: the arch checker, which must see through a test runner.
  - Research: young tools 30 days.
- **testing** (tiers)
  - Config: test targets for the unit, integration, e2e and arch tiers.
  - Rules:
    - 40% CPU share, never a hardcoded count (rule 20);
    - one process per module;
    - local versus cloud e2e, covering credentials, cost and teardown, a blind spot (report 25).
  - Research: runner pins 90 days.
- **secrets**
  - Config: a gitleaks or Betterleaks hook, `.env` gitignored.
  - Rules: never print keys; runbooks contain no secrets.
  - Research: the scanner, 14 days. Betterleaks forked from Gitleaks (report 26).
- **dependencies**
  - Rules: lockfiles committed, a legitimacy check before adding a package, Renovate or Dependabot, versions at
    least two weeks old, and the audit tool per stack.
  - The owner's preference for pnpm is a personal default. It is written only where the owner confirms it.
  - Research: 14 days.
- **branches-and-merge**
  - Rules: detect the base branch, protected branches, merge locally first, no push without consent, the order of
    remotes, cleanup by content.
  - No research.
- **release**
  - Changelog, version and tags. Generated only when the project publishes or deploys.
  - No research.
- **language-and-interaction**
  - Rules:
    - talk in the user's language, write in English;
    - explain before asking;
    - plain words, no codes;
    - status pings carry the local time;
    - keep it concise.
  - No research.
- **decisions** (jev)
  - Rules: route decisions through the jev ladder, which is advisory and a black box; work without it; label
    answers as inferred (report 25, Round 1-5 summary).
  - No research.
- **vertical-slices**
  - Content:
    - the cycle: mocks, front, backend, database, real data, security, infra, observability, accessibility;
    - the walking skeleton;
    - the phase 1 deliverable (§4);
    - lens skills per stage, found by discovery and not hardcoded (Round 5);
    - how it maps onto GSD's tracer and MVP mode, and that GSD has no mocks, infra or observability stage
      (report 27);
    - the shift-left note on security and accessibility, as a recommendation.
  - Research: a skill scan at invocation, with no cache (6-20 ms, report 17).
- **agent-sessions** (**PROPOSAL**, it collects report 25's process rules)
  - Rules:
    - bypass mode puts scripts in files;
    - time-boxed subagents;
    - the real-home guard;
    - kill ephemeral processes;
    - scratch files in `tmp/`;
    - process and disk hygiene, including the Bun temp-copy leak (report 25).
- **code-navigation** (**PROPOSAL**)
  - Rules: codegraph and graphify use, `sync` before mapping, and the GSD graph path. This restores the detail
    report 23 says was cut.
- **instruction-files**: the procedure in §5.

## 3. How it runs

### Models

- Event playbooks run on the session's own model. They are cheap, about SKILL.md plus one playbook plus the
  script JSON.
- Bootstrap, and audit with fixes, run on a strong model at the highest effort, or delegate by area (Round 7).
  The skill text names tiers: "strong (for example Opus at xhigh)" and "standard (for example Sonnet)". It never
  names a model alone, because the skill must stay host-portable and must not hardcode names (Round 4).

### Delegation map (PROPOSAL)

- **Wave 1** (parallel, read-only):
  - one research subagent per detected stack, plus one for cross-stack tools (standard, high effort);
  - architecture layers from the code (strong, high);
  - the vertical-slice plan from the README, the planning files and the UI or API shape (strong, high).
- **Wave 2** (parallel; each subagent returns a proposal file under `tmp/project-rules/<area>.json` and writes
  nothing in the repo):
  - Makefile, pre-commit and testing together in one subagent, because all three touch the Makefile
    (standard, high);
  - CI/CD (strong, high: it touches deploys and supply chain);
  - docker-local (standard, medium);
  - secrets and dependencies (strong, high);
  - branches, release, language and decisions (standard, medium; mostly template filling from detected facts).
- **Wave 3** (the orchestrator, alone):
  1. Merge the proposals and settle conflicts.
  2. Write the AGENTS block, the README section, `events.md` and hooks.toml.
  3. Run a single `apply`, then `audit`.
  4. Show the diff.
- **One writer only.** Area agents never edit the repo, so two areas never race on the same file.
- **Time box:** 20-30 minutes per subagent (memory). Before fanning out, check the quota pace and the time left.
  A long strong-model run can hit the 5-hour window (§7).

### Research at invocation

- **Time box:** about 10 minutes per stack, at most 3 sources per category, official release pages and docs
  first (**PROPOSAL**).
- **Cache:** the existing `~/.cache/ai-kit/<namespace>/stack-refs/<stack>.json`, with a citation required on
  every value (report 26).
- **Expiry per category** (report 26):
  - 14 days: scanners, secrets tools, SHAs;
  - 30 days: linter choice and young tools;
  - 90 days: formatter and runner pins.

  This settles the 30-versus-180-day conflict. The smallest change is an optional `stale_after_days` per key
  (report 26).
- **Context facts are never researched.** The package manager, framework, monorepo shape and cloud are read from
  the repo with `(source: <file>)`.
- **No web, or the time box ran out:** use the baked baseline, labelled "baseline, not re-checked on <date>", and
  mark the runbook section "research pending". This follows the AGENTS.md certainty rule.

### Hosts without subagents or a strong model

- **No subagents** (pi has none natively; opencode child sessions are unverified, report 24): run the same waves
  one after another. Write each area's proposal to `tmp/project-rules/` before starting the next, to free
  context.
- **Weak model only:** take the deterministic path. That is detect, then plan, then apply with templates and the
  baked baseline. Mark every judgement section "pending a strong-model pass" and say so. Never pass a guess off as
  a decision.

## 4. Draft of the generated AGENTS.md top section (DRAFT, 24 lines)

```markdown
<!-- ai-kit:project-rules:begin template=1 -->
## Top rules
1. **AGENTS.md is the only instructions file.** No `CLAUDE.md` of any kind; personal notes go in gitignored
   `AGENTS.local.md`, wired into each host. See `docs/run-book/instruction-files.md`.
2. **Vertical slices, outside-in.** Each feature: mocks, UI, backend, database, real data, security, infra,
   observability, accessibility. Phase 1 ends with something the user can see: a UI deploys its mockup on
   minimal infra; an API ships its contract (OpenAPI plus a JSON sample valid against its schema).
   See `docs/run-book/vertical-slices.md`.
3. **Bypass mode: no multi-line inline commands.** Anything beyond a one-liner goes in a `.sh` or `.py`
   file under `tmp/`, then run it. See `docs/run-book/agent-sessions.md`.
4. **Done means the gates pass.** `make validate` and `make test` green and behaviour checked for real;
   never `--no-verify` except a deliberate TDD red commit; fix failures, no excuses. See `docs/run-book/testing.md`.
5. **Talk in the user's language, write in English.** Explain before asking; settle gray areas with jev when
   present (advisory), else decide and log why. See `docs/run-book/language-and-interaction.md`.
## Never / avoid
- Never build a whole layer before one slice works end to end, and never let a mock outlive its slice.
  See `docs/run-book/vertical-slices.md`.
- Never print, log or commit a secret; `.env` stays gitignored. See `docs/run-book/secrets.md`.
- Never reset, clean, force-push, push or touch the user's real config without explicit consent.
  See `docs/run-book/branches-and-merge.md`.
On session start, a new worktree, the end of a task, plan or phase, a push, or a quota limit:
follow `docs/run-book/events.md`.
@AGENTS.local.md
<!-- ai-kit:project-rules:end -->
```

The `@AGENTS.local.md` line is how Claude reads the personal file. Whether it works is unverified (§5, step 4).
The draft is 24 lines with it.

Why I picked these two (rules 4 and 5):

- **Rule 4:** it merges three always-on, criticality-1 house rules into one line: never skip checks, no excuses,
  and verify for real (report 23).
- **Rule 5:** it delivers the owner's two explicit asks, "one clear rule on language and interaction" and "one on
  using jev" (Round 7), in one line.

The never list mixes one vertical-slice item with two general items: secrets and destructive operations, the
first and sixth blind spots in report 25. The full vertical-slice never and avoid list lives in its runbook. This
is an owner question.

## 5. AGENTS.md and AGENTS.local.md: procedure

Owner decision (2026-11-02, relayed by the coordinator):

- The skill works only with `AGENTS.md` (committed) and `AGENTS.local.md` (gitignored, personal).
- No `CLAUDE.md` of any kind.
- Windows is out of scope.
- Where a host does not read one of the two files natively, the skill configures the host to read it.
- open-gsd's `claude_md_path` always names one of the two real files, never a symlink.

The verified facts below come from report 27. Each one is treated as a gap to spike, not as a blocker.

1. **Detect** (script). The script looks for:
   - `AGENTS.md` and `AGENTS.local.md`;
   - any Claude file: `CLAUDE.md` (a regular file, a link or an import), `.claude/CLAUDE.md`, `CLAUDE.local.md`;
   - `AGENTS.override.md`;
   - GSD's `claude_md_path`;
   - each host's current wiring for `AGENTS.local.md` (step 4).
2. **Migrate the Claude files.** This step exists because Claude Code reads AGENTS.md only when no `CLAUDE.md`,
   `.claude/CLAUDE.md` or `CLAUDE.local.md` sits in the folder or above it.
   - Merge the text of `CLAUDE.md` and `.claude/CLAUDE.md` into `AGENTS.md`, and `CLAUDE.local.md` into
     `AGENTS.local.md`.
   - Show the diff and ask first. These are hand-written files.
   - Then remove the Claude files. Use `git rm` for tracked ones, so their history stays.
   - `~/.claude/CLAUDE.md` does not count and is left alone.
   - Spike: after migrating, confirm on the installed Claude Code that AGENTS.md loads. This was observed in this
     repo, which has no Claude file (report 25), but not tested as a migration.
3. **Keep it that way** (the audit, every run): a Claude file appearing in the project is a critical finding,
   because it silences AGENTS.md for Claude. GSD's default `.claude/CLAUDE.md` is the likely source (report 27).
4. **Make every host read `AGENTS.local.md`.** No host reads this file natively (report 27). **PROPOSAL**, every
   route **unverified**:
   - **Claude:** the AGENTS block ends with a plain `@AGENTS.local.md` line, as in the §4 draft. Report 27 says
     `@` imports work inside a natively read AGENTS.md, and imports skip code spans and fences. Spike two things:
     - that the import loads;
     - what happens for a contributor who has no `AGENTS.local.md` (a silent skip or an error).
   - **opencode:** an `instructions` entry for `AGENTS.local.md` in the project's opencode config. opencode
     does not parse `@` lines. Spike what happens when the listed file is missing. Spike too whether a relative
     entry in the global config resolves against the project.
   - **Codex, pi, Cursor, Copilot:** report 27 shows no additive file route.
     - Codex and pi take `AGENTS.override.md` as a replacement for AGENTS.md, not an addition.
     - Codex's fallback list is only read when there is no AGENTS.md.

     Route: the session-start dispatcher (§6) injects the file's text through each host's context field.
     - Claude caps that field at 10,000 characters (report 24); the caps on the other hosts are unknown.
     - Spike per host.
     - Copilot may also follow the `@AGENTS.local.md` line, since its `@` references must stay inside the repo
       (unverified).
   - **Hosts that ignore the line:** Codex reads the `@AGENTS.local.md` line as plain text. It is harmless.
5. **Never use `AGENTS.override.md` for personal notes.** It replaces AGENTS.md in Codex and pi.
6. **Worktrees:** `AGENTS.local.md` exists in one worktree only (report 27). worktree-created links it from the
   main checkout. The exception is a project where GSD's `claude_md_path` is `AGENTS.local.md`. GSD renames a
   temp file over the path, which turns a link into a plain file (report 27). So that project gets a copy, and
   the audit reports when the copies drift apart.
7. **GSD `claude_md_path`:**
   - It is always `./AGENTS.md` or `./AGENTS.local.md`, as real files.
   - Setting it is curated-config's job. This skill checks it and flags the default `.claude/CLAUDE.md`.
   - GSD honours the path only on the claude runtime. Other runtimes write to `AGENTS.md` on their own
     (report 27).
8. **Size:** keep AGENTS.md small and never `@`-import the runbooks, which would load them every session. Codex
   caps the combined instruction chain at 32 KiB by default (report 27). `AGENTS.local.md` counts toward each
   host's budget once it is injected.

Needs the owner's decision:

- Should GSD write to `AGENTS.md` (shared) or to `AGENTS.local.md` (personal, per worktree, a copy in each
  worktree)?
- Where does the opencode wiring live: the committed project config (it names a gitignored file) or the user
  config?
- Should injecting the file through the dispatcher on hosts with no file route be on by default, or opt-in per
  host?

## 6. Hooks: what the skill writes and what setup installs

Shared idea, from report 24's proposal:

- one event catalogue;
- one thin dispatcher per host and native event, which reads layered knobs when it fires (built-in defaults,
  then `~/.config/ai-kit/hooks.toml`, then `<repo>/.aikit/hooks.toml`);
- hooks advise and never block (21.3 rule).

**Catalogue location (PROPOSAL):** `skills/ai-kit-project-rules/references/events.toml`, read by the skill (it
ships to hosts that may not have setup) and by setup from the checkout. A test pins that every event in setup's
hook registry appears in the catalogue. Report 24 suggested keeping it beside the hook registry or the runtimes
table, so the owner may prefer `tools/`.

**What setup installs** (user level, per host):

- the dispatcher entries: Claude settings, Codex `hooks.json`, Cursor `hooks.json`, a pi extension, an opencode
  plugin, Copilot;
- the user knobs file;
- `setup.py hooks status [--project] [--json]`;
- wizard rows.

The six existing hooks keep their entry scripts. **PROPOSAL:** the dispatcher arrives as one new row,
"project-events".

**Why host wiring stays at user level:**

- Copilot also runs a repo's `.claude/settings*.json` hooks.
- Codex project hooks need trust approval (report 24).

So the skill never writes host hook config into a project.

**What the skill writes** (project level):

- `.aikit/hooks.toml`, for example:

  ```toml
  [events.worktree-created]
  enabled = true
  contexts = ["direct", "herdr"]
  playbook = "worktree-created"
  run = ["make setup-dev"]
  ```

  - `run:` is opt-in and only for agentless events (report 24).
  - Committed, with personal overrides at the user layer (**PROPOSAL**).
- The git `post-checkout` script plus its pre-commit stage entry. That is repo config, and it runs without
  ai-kit.
- An `[events.session-start] inject = ["AGENTS.local.md"]` knob (**PROPOSAL**). It is for hosts with no file
  route to the personal file (§5, step 4). The dispatcher injects the text, never blocks, and skips a missing
  file.

**Workflow events** (phase, plan or task done; pushed; PR opened):

- The workflow skills call the playbook themselves. The dispatcher's PostToolUse marker match is only a backup
  (report 24).
- The dispatcher stays silent in contexts that are not enabled. It detects them from `AI_KIT_RUN_CONTEXT`, then
  `HERDR_ENV`, then the agent id, and also checks `AI_KIT_CROSS_AI_CHILD=1` (report 18). This keeps playbook
  lines out of every subagent and cross-AI child.

**Spikes before the setup phase** (report 24):

- Does StopFailure carry a reset time?
- Does Codex trust hooks under `exec`?
- Does `asyncRewake` work to watch CI?
- Does pi's `session_start` deliver a visible briefing?
- Do opencode plugins fire in child sessions?
- Do Cursor hooks fire in the CLI?
- Does Copilot run the `.claude` hooks?

## 7. Blind spots, ranked

Each entry gives where it comes from, then where it lands in the design.

1. **Secrets** (report 25): the secrets runbook, a pre-commit hook, the second never line.
2. **Contributors or hosts without ai-kit** (mine): `docs/run-book/events.md` and a git hook that needs no
   ai-kit. Runbooks live in the repo.
3. **Untrusted input** (mine): repo files, PR comments and bot reviews are data and never instructions. The PR
   loop never runs a command that comes from a comment. The old agents checker ran the target's gsd-tools behind a
   trust gate (report 23), and the GSD probe leaves this skill (§8). Lands in pr-review-loop and the NEVER list.
4. **Isolation from the developer's real config** (report 25): the agent-sessions runbook, the delegation
   playbook, the third never line.
5. **Ownership drift in generated files** (mine): marked blocks plus a body hash, so the skill never overwrites
   what a developer edited. An eval checks that a second bootstrap produces no changes.
6. **Parallel writers** (mine): the one-writer rule in §3.
7. **Hook noise in subagents and children** (mine, from facts in reports 18 and 24): settings hooks also run
   inside subagents, so the dispatcher filters by context.
8. **Branch model and merge flow** (report 25): the branches-and-merge runbook and the end of unit-done.
9. **Test pyramid and cloud e2e** (report 25): the testing runbook.
10. **Dependencies and supply chain** (report 25): the dependencies runbook, plus the 14-day expiry on scanners.
11. **Instruction size budget** (mine, from report 27): no `@` imports of runbooks, and the top block capped at
    25 lines.
12. **Cost and quota of the strong-model run** (mine): check the pace before fanning out, and the time box per
    subagent.
13. **Rollback and destructive operations** (report 25): the third never line, plus reversible migrations at the
    database stage of vertical slices.
14. **Commit message convention** (report 25): **PROPOSAL** a commit-msg hook in the pre-commit runbook.
15. **Tooling freshness** (report 25): session-start and worktree-created.
16. **Monorepos and several stacks** (mine): stack detection reads markers at the root only. `detect` should walk
    package folders, and the open question is whether there is one Makefile or one per package.
17. **Process and disk hygiene** (report 25): the agent-sessions runbook.
18. **Release, multi-repo, observability tooling, licensing, incident runbooks** (report 25): low priority, as
    runbook stubs generated only when the project needs them.

## 8. Migration

### The seven skills and the shared library

- Move `skills/_shared/ai_kit_rules_common` and the six checker packages into
  `scripts/project_rules_lib/`, then delete `_shared` (it is used only by this family).
- The seven entry scripts become `check <area>` subcommands.
- rules-all becomes `audit`, run in-process. Delete the thin re-export shims (report 13).
- The installer's stale-link cleanup removes the seven old links. Update the README, the hooks README and the
  docs (AGENTS.md: stale docs are a defect).

### The house rules (the 20 in the old `rules.py`)

- Drop the rtk rule and every rtk mention (Round 5).
- Move the three GSD-only rules out (**PROPOSAL**):
  - the runner pointer and the cross-AI plan rules go to curated-config and cross-ai, which own the runner
    (report 25);
  - the rule about arming the wake goes into the quota playbook.

  This also removes the import of the two sibling skills, so the new skill installs alone. It answers the
  waiting decision on whether ai-kit's AGENTS.md adopts three workflow rules.
- The CPU-share rule goes to the testing runbook.
- Every other rule becomes a top-block line, a runbook line or a playbook step, per report 25's catalog.

### Defects to fix while porting (reports 23 and 26)

- one quoted description under 1,024 characters, plus a strict frontmatter test;
- follow GitLab `include:`;
- see through a test runner in the arch check;
- accept Compose Watch;
- a Kotlin stack id;
- expiry per category.

### Tests and evals

- Re-point the nine test files to the new import paths. They stay in the unit tier.
- New `evals/evals.json` with fixture repos (**PROPOSAL**, about 10 cases):
  - a CLAUDE.md-only repo migrated into AGENTS.md, but only after the owner confirms;
  - a `CLAUDE.local.md` migrated into `AGENTS.local.md`, with no Claude file left;
  - GSD's `claude_md_path` left at `.claude/CLAUDE.md`, which is flagged;
  - opencode wired to read `AGENTS.local.md`;
  - worktree-created with compose;
  - audit parity with today's findings;
  - a second bootstrap produces no diff;
  - an API repo whose phase 1 needs a contract;
  - a UI repo whose phase 1 needs a deployed mockup;
  - one stack with a stale security key but fresh formatter keys;
  - the bypass rule present in the block.
- `trigger-queries.json`, about 20 queries. Near-miss negatives: curated-config, agent-md-refactor,
  crafting-effective-readmes, session-wake, spec-review, skill-judge.
- Real config is never a fixture (AGENTS.md).

### ai-kit's 11 self-violations (report 23)

- **Fix in the repo (2):**
  - a help path for an unknown target;
  - the five-line `e2e-docker` recipe moves to a script file, which matches the scripts-in-files rule.
- **Fix in the checker (2):**
  - the arch test seen through the runner;
  - an "informational" marker, so that `security-scanner` and `duplicate-code` stop counting as missing hooks.
    AGENTS.md already calls them informational and keeps them out of `validate`.
- **Rule change (1):** the mutating `format` target is exempt from hook parity (**PROPOSAL**).
- **Owner decision (5):** the five `validate-<category>` aliases. **PROPOSAL:** require them only when a
  category has more than one tool.

### Ordering with the other work

- **Re-judge:** take the seven out of the baseline round and its batches (Round 4 put the five checkers in one
  batch and two more after this decision). Judge the new skill when phase 1 ends, and again when a later phase
  changes SKILL.md (AGENTS.md skill-judge rule).
- **dist and copy installs:** do phase 1 before, or together with, the dist phase. Otherwise dist builds
  vendoring of `_shared` into seven skills that are about to disappear. If dist comes first, it skips the seven.
- **Lens skills:** the vertical-slices runbook reuses the role-keyed skill table from the lens work (Round 5:
  "build it"). Until that exists, it falls back to its own short stage-to-role list.
- **Setup hooks:** after phase 3, so that the dispatcher has playbooks to point at.
- **The session-wake additions** (5-hour grid, early reset, anticipating the limit) belong to session-wake's own
  phase. The quota playbook only points to them.
- **curated-config's `claude_md_path`** is set in curated-config's phase, matching §5.
- **Close as superseded** the 2026-10-14 todo on quota rules and the goal-prompt skill (report 25).

### Phases as vertical slices (PROPOSAL)

1. **One skill, same checks, plus the AGENTS.md fix.**
   - Contents:
     - the port with the old seven deleted;
     - `detect`, `plan` and `apply` for the instruction files and the top block;
     - three runbooks: agent-sessions, vertical-slices, language-and-interaction;
     - the evals;
     - the judge loop.
   - What it shows:
     - `audit` on ai-kit returns today's 11 remediate findings and 4 blocked findings (parity);
     - bootstrap on a CLAUDE.md-only fixture leaves the migrated AGENTS.md, no Claude file, the
       `AGENTS.local.md` wiring for Claude and opencode, the block and the runbooks;
     - the Claude import spike and the opencode `instructions` spike run first in this phase;
     - ai-kit itself in plan-only mode.
2. **Area runbooks that write config.**
   - Contents:
     - Makefile, pre-commit, testing, CI/CD, docker, arch layers, secrets and dependencies;
     - the research cache with expiry per category;
     - the delegation map;
     - the checker fixes;
     - ai-kit's self-violations settled.
   - What it shows: fresh Python and Node fixtures are bootstrapped, and `make validate && make test` pass in the
     generated repos.
3. **Event playbooks.**
   - Contents:
     - session-start, worktree-created (the git hook), unit-done, ci-wait, pr-review-loop and delegation;
     - the hooks.toml writer;
     - spec-execute-superpowers calls unit-done.
   - What it shows: `git worktree add` on a fixture runs `setup-dev`, and the end of a plan flags a stray
     untracked file.
4. **Hooks per host in setup.**
   - Contents: the spikes first, then the catalogue, the dispatcher, `hooks status`, the wizard knobs and the
     contexts.
   - What it shows: `setup.py hooks status` on this machine.
5. **Quota policy.**
   - Contents: the quota playbook plus the session-wake additions, after the owner's answers and the spike on how
     the window starts.
   - What it shows: a wake armed on the 5-hour grid, visible in the status.

## 9. Open questions for the owner

1. **Commit compaction.** At what point, and in what unit? **PROPOSAL:** this reconciles September ("per plan")
   with the October memory ("at the end of each phase, logical commits per plan, by a subagent"):
   - GSD: at the end of the phase, grouped per plan;
   - superpowers: at the end of the plan;
   - quick tasks: per task.
2. **Setup target names.** `setup-env` (today, `uv sync`), `setup-dev` (Round 7), or both? **PROPOSAL:**
   - `setup-dev` is everything a fresh worktree needs (today's `dev`, including the hook install);
   - `setup-docker` builds and starts the local stack;
   - `setup-env` stays as an alias for one milestone.
3. **Pace gauge.** Does the quota playbook react to the status-line pace gauge (red and ahead of pace means
   checkpoint and arm a wake), or only to real limit errors? It needs a cache file the status line does not write
   today.
4. **5-hour grid.** Arm a wake on a 5-hour grid from a fixed start time, on top of the wake at the reset plus
   60 s?
5. **Early polling.** May early-reset polling relax session-wake's rule against repeated jobs, and if so, at
   what cadence and cap?
6. **Skill name.** `ai-kit-project-rules` or `ai-kit-project-playbooks`?
7. **The personal file.**
   - Should GSD write to `AGENTS.md` or to `AGENTS.local.md`?
   - Where does the opencode wiring live: the project config or the user config?
   - Is injecting `AGENTS.local.md` through the dispatcher on by default (§5)?
8. **Never list.** Should it be general (as drafted), or all three about vertical slices?
9. **Strict Makefile rules.** Keep the `validate-<category>` aliases and the three-line recipe cap as required?
10. **Runbook location.** Do runbooks live at `docs/run-book/<topic>.md` everywhere, with the docker one moving
    from `docker/local/README.md`?
11. **ai-kit's own AGENTS.md.** Should it take the generated block (dogfooding), or stay hand-written with only
    the audit run against it?
12. **PR review loop consent.** Ask once per loop run (proposed), or before every push and reply?
13. **Scope.** Which stacks beyond the five: Kotlin, .NET, PHP? Which CI platforms beyond GitHub and GitLab?
14. **hooks.toml.** Commit `.aikit/hooks.toml` as project policy (proposed), or keep it personal?

Skipped: no new web research, and no checker or judge run. The line counts are the only commands I ran. Risks:

- Each phase's size is my estimate.
- The delegation-map efforts are judgement, not measured.
- The hook spikes may change §6.
