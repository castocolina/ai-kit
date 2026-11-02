# Roadmap: ai-kit

## Milestones

- ✅ **v1.0 Multi-CLI Foundation & Config Safety** — Phases 1.1–5 (shipped 2026-09-10)
- ✅ **v1.1 Agent Workflow Hygiene & Tooling Polish** — Phases 6–8.1 (shipped 2026-09-13)
- ✅ **v1.2 ai-kit Rules Skill Family** — Phases 9–15.2 (shipped 2026-09-23)
- ✅ **v1.3 GSD Curated Config v2** — Phases 16–27 (shipped 2026-10-31; owner items carried, see below)

Phase numbering continues across milestone boundaries and is never reset. Integer `0`
and `999` are reserved by `gsd-core`'s phase-id parser as non-milestone sentinels
(`999.x` = Backlog).

## Phases

<details>
<summary>✅ v1.0 Multi-CLI Foundation & Config Safety (Phases 1.1–5) — SHIPPED 2026-09-10</summary>

- [x] Phase 1.1: Autonomous-Run Infrastructure (INSERTED) (1/1 plans) — completed 2026-09-09
- [x] Phase 1.2: Multi-CLI Runtime Foundation (4/4 plans) — completed 2026-09-09
- [x] Phase 2: Opencode Provider Management (2/2 plans) — completed 2026-09-09
- [x] Phase 3: Tool-Substitution Awareness Hook (2/2 plans) — completed 2026-09-09
- [x] Phase 4: Config Doctor (3/3 plans) — completed 2026-09-10
- [x] Phase 5: Usage Metrics Dashboard (6/6 plans) — completed 2026-09-10

Full details: `milestones/v1.0-ROADMAP.md` · phase dirs: `milestones/v1.0-phases/`

</details>

<details>
<summary>✅ v1.1 Agent Workflow Hygiene & Tooling Polish (Phases 6–8.1) — SHIPPED 2026-09-13</summary>

- [x] Phase 6: AGENTS.md Rules Checker Skill (3/3 plans) — completed 2026-09-11
- [x] Phase 7: Curated GSD Config Skill (4/4 plans) — completed 2026-09-11
- [x] Phase 8: Status-line Quota Color Refactor (1/1 plan) — completed 2026-09-10
- [x] Phase 8.1: Status-line Rate-Burn Pace Fix (INSERTED) (1/1 plan) — completed 2026-09-13

Full details: `milestones/v1.1-ROADMAP.md` · phase dirs: `milestones/v1.1-phases/`

</details>

<details>
<summary>✅ v1.2 ai-kit Rules Skill Family (Phases 9–15.2) — SHIPPED 2026-09-23</summary>

- [x] Phase 9: AGENTS.md Checker Prune (ai-kit-project-rules-agents) (2/2 plans) — completed 2026-09-14
- [x] Phase 10: Makefile Rules Checker (ai-kit-project-rules-makefile) (3/3 plans) — completed 2026-09-14
- [x] Phase 11: Pre-commit Rules Checker (ai-kit-project-rules-precommit) (4/4 plans) — completed 2026-09-14
- [x] Phase 12: Architecture Rules Checker (ai-kit-project-rules-arch) (3/3 plans) — completed 2026-09-14
- [x] Phase 13: Docker Rules Checker (ai-kit-project-rules-docker) (4/4 plans) — completed 2026-09-14
- [x] Phase 14: CI/CD Rules Checker (ai-kit-project-rules-cicd) (4/4 plans) — completed 2026-09-14
- [x] Phase 15: Rules Orchestrator (ai-kit-project-rules-all) (2/2 plans) — completed 2026-09-14
- [x] Phase 15.1: Usage Metrics Dashboard UX/Perf Overhaul (INSERTED) (5/5 plans) — completed 2026-09-21
- [x] Phase 15.2: v1.2 Tech Debt Cleanup (pre-close) (INSERTED) (1/1 plan) — completed 2026-09-23

Full details: `milestones/v1.2-ROADMAP.md` · phase dirs: `milestones/v1.2-phases/`

</details>

<details>
<summary>✅ v1.3 GSD Curated Config v2 (Phases 16–27) — SHIPPED 2026-10-31</summary>

- [x] Phase 16: ai_kit_spec Extensions (6/6 plans)
- [x] Phase 16.1: Hardening (INSERTED) (31/31 plans)
- [x] Phase 17: Curated-Config Inventory & Recommendation Engine (9/9 plans)
- [x] Phase 18: Cross-AI, Skills & Apply Pipeline (22/22 plans)
- [x] Phase 18.1: One runtime model (INSERTED) (22/22 plans)
- [x] Phase 19: Evaluation on Claude (10/10 plans)
- [x] Phase 20: Live Validation on Codex + Opencode (7/7 plans) — human_needed
- [x] Phase 21: Cursor Live Validation (7/7 plans) — human_needed
- [x] Phase 21.1: Atomic reusable decision-system skills (INSERTED) (7/7 plans) — human_needed
- [x] Phase 21.2: PreCompact pre-summary hook (INSERTED) (5/5 plans) — human_needed
- [x] Phase 21.3: Visible tool-advisory hooks (INSERTED) (8/8 plans) — human_needed
- [x] Phase 22: Pi Live Validation (7/7 plans) — human_needed
- [x] Phase 23: Host-split status line for Claude Code and Cursor CLI (18/18 plans) — human_needed
- [x] Phase 24: Spec-and-discuss chain skill (1/1 plan) — human_needed
- [x] Phase 25: Quota-aware cross-AI subprocess supervision (11/11 plans) — human_needed
- [x] Phase 25.1: Configurable cross-AI retry ladder and upstream error propagation (INSERTED) (15/15 plans) — human_needed
- [x] Phase 26: Session self-resume and OpenGSD quota rules (12/12 plans) — human_needed
- [x] Phase 27: One-shot goal and loop prompt skill (14/14 plans) — human_needed

**Carried to the owner (not done):** every `*-OWNER-CAPTURES.md` (phases 25, 25.1, 26, 27), the
interactive and live runs (20, 21, 21.2, 21.3, 22, 23), every `human_needed` verification, the
deferred skill-judge verdicts (`ai-kit-spec-goal-prompt` and `ai-kit-spec-config` UNRESOLVED; SJ-1,
SJ-2, SJ-3 deferred), the Phase 24 chain dry run, and `.planning/WINDOWS.md` entry 7. The full list
with paths is in the v1.3 entry of `MILESTONES.md`.

Full details: `milestones/v1.3-ROADMAP.md` · phase dirs: `milestones/v1.3-phases/`

</details>

## Backlog

### Phase 999.1: Config Doctor reachable from the setup wizard (BACKLOG)

**Goal:** [Captured for future planning] Config Doctor (v1.0 Phase 4) is a
standalone `textual` TUI reached only through `setup.py --config-doctor`; the
setup wizard (`tools/wizard_app.py`: housekeeping, Choose, Arrange, Review,
Done) never offers it, and `make doctor` runs the different status-line
doctor. Make Config Doctor reachable from the wizard (for example an entry on
the Done step, or a dedicated step) reusing the existing stdlib-only engine
(`config_doctor_checks.py` / `config_doctor_readers.py` /
`config_doctor_appliers.py`) and `config_doctor_app.py` screen, with no second
implementation. Coordinate with v1.3 Phase 23 C2 (per-host
status-line step); `worktree-context-tools-manager-plan1` no longer lands (2026-10-14). Candidate rows to add later: the Playwright MCP Chrome path
on Bazzite. Rewritten 2026-10-13 from the former "shared core for a CLI
variant" note, whose goal (engine not coupled to the TUI) is already met.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

**Moved 2026-10-13:** the host-split status line (former 999.4) was promoted to
v1.3 Phase 23 on branch `gsd/v1.3-curated-config-v2`; former 999.3 was removed
(resolved by v1.2 Phase 12; see git history).

### Phase 999.2: Cursor hooks path ignores CURSOR_CONFIG_DIR (BACKLOG)

**Goal:** [Captured for future planning] `tools/setup.py`'s single `Paths.cursor_dir`
(`CURSOR_CONFIG_DIR` or `~/.cursor`) is used for Cursor hook wiring, but the Cursor CLI
(2026.10.01 bundle) always reads user hooks from `~/.cursor/hooks.json` and ignores both
`CURSOR_CONFIG_DIR` and `XDG_CONFIG_HOME`. When `CURSOR_CONFIG_DIR` is set, ai-kit writes hooks
where the CLI never looks. Resolve the hooks path separately from the config dir (Phase 23 D-21
adds the config-dir resolver for the status line), re-verify against current Cursor docs, and
check Phase 21's `cursor-agents` destination against the same split. Found by the Phase 23
assumptions analysis, 2026-10-14.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.5: Idle watchdog for the cross-AI runner (BACKLOG)

**Goal:** [Captured for future planning] The Phase 18 cross-AI runner
(`.planning/scripts/cross-ai.mjs`, rendered from the ai-kit-spec-review template) kills the
child's process group only at the overall deadline (outer `workflow.cross_ai_timeout` minus the
D-29 margin). A child that hangs without output burns the whole window. Add an opt-in idle
watchdog: kill the process group after N seconds with no stdout/stderr growth, then exit with the
existing status vocabulary (a `retry-later` or `fallback` action, never a new exit class). It needs
a self-test case and a default that is safe for slow, quiet models. Deferred by 18 D-43
(RUN-46, 2026-10-15): not required by SPEC R5/D-27, and the runner is the largest new code in
Phase 18.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.6: Codex interactive TUI confirmation (secondary runtime) (BACKLOG)

**Goal:** [Captured for future planning] Run `20-INTERACTIVE-CODEX.md` from a real codex TUI
session to confirm EVAL-04 (codex session env signal, smoke, snapshot) beyond the headless
`codex exec` evidence in `20-SMOKE-CODEX.md`, then promote or rename the "live-verified (Phase 20)
… TUI confirmation pending" labels in `detection.py`. Deferred 2026-10-18 by owner decision: the
primary runtimes are claude, opencode and pi; codex and cursor are secondary (their models remain
usable as reviewers and executors). The headless evidence and the pending label stay as they are.
**Requirements:** EVAL-04
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.7: Cursor project-level subagent linking (BACKLOG)

**Goal:** [Captured for future planning] ai-kit's pinned Cursor subagents (`cursor-agents/`,
shipped by Phase 21) reach the cursor CLI: they are linked per file into a project's
`.cursor/agents`, the only subagent root the CLI reads (Phase 21 D-01 spike, 2026-10-18), and a
live delegation shows each pinned model. Success criteria when promoted: (1) a tested ai-kit path
links `cursor-agents/*.md` per file (never a directory) into a chosen project's `.cursor/agents`,
mirrors `--skills` selection (`all|name1,name2`, unknown name exits 1 naming it), never overwrites
a non-ai-kit file and removes only its own links; (2) a headless delegation from a cursor parent
shows each pinned model in the Task call, and the user confirms one run as non-fast in the Cursor
usage dashboard; (3) docs say where the agents are linked and why `~/.cursor/agents` is not used.
Inputs: `21-SPIKE-D01.md`, 21-CONTEXT D-02..D-05. Moved out of the inserted Phase 21.1 on
2026-10-18 by owner decision (cursor is a secondary runtime; Phase 21 documents manual linking).
**Requirements:** AGT-02
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.8: Jev image and box questions (BACKLOG)

**Goal:** [Captured for future planning] The `jev-fast-decision` client builds image questions
(one image, and several compared) and `box` questions on every backend whose 21.1 capability
matrix cell is `verified-live` or `documented`, so a flow can ask Jev to judge a UI state against
a reference screenshot. Success criteria when promoted: (1) a spike against TypeSafe direct (key
and consent present) records the request shape, size limits (PNG/JPEG, 280-1568 px, 16 MiB per
file, 32 MiB per request) and the danger-zone header as live facts; (2) stub-tested request
builders for images and `box`, gated by the matrix; (3) the Laya and Zen cells are re-checked.
Deferred 2026-10-18 from Phase 21.1 (D-21): no in-scope caller sends images, and no TypeSafe key
or consent was available to verify the shapes live.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.9: jev-fast-decision backend detection and selection by host (BACKLOG)

**Goal:** [Captured for future planning; rewritten 2026-10-24 from "drop the OpenCode Zen backend"
after the owner's follow-up] The client picks a backend through explicit, host-aware detection
instead of a fixed Laya -> TypeSafe -> Zen ladder:
1. **Laya first:** the default Laya URL lives in ai-kit's config `.toml` as a knob (default
   `http://127.0.0.1:8010`). The client probes `/health` there. The first time no Laya answers, it
   asks the user once whether a Laya instance exists (and where) and stores the answer in the knob.
2. **TypeSafe second:** the key is resolved from the environment (`TYPESAFE_API_KEY`). If it is
   missing, the client tells the user it must be in the env, or that the user can pass it or save
   it in ai-kit's `.toml` (owner option). The transitional file fallback is backlog 999.10.
3. **OpenCode Zen third, only where it is legitimate:**
   - The free `jev-*-free` model is used only when the host harness IS opencode and an OpenCode
     Zen provider is configured. It never runs under OpenCode Go or any other host.
   - Under pi, Zen (non-free) may be used through the owner's linked subscription.
   - Under Claude Code or Cursor, Zen is used only with an explicit token and URL.
   - Otherwise the Zen rung is skipped with a reason.

Owner note (2026-10-24): undecided whether to keep Zen at all, which is why it is gated, not
deleted. **Current state (verified 2026-10-24, before this work):** the Laya URL is hard-coded
with env overrides (no `.toml` knob, no first-run question). The Zen rung exists with free-tier
first and has no host/provider gating. `consent grant opencode` exists. Success criteria when
promoted: (1) detection table per host (claude, cursor, pi, opencode) with tests on synthetic
configs; (2) the free model is never selected outside opencode-with-Zen; (3) the `.toml` knob and
first-run question are covered by tests in a scratch HOME; (4) the skill-judge gate passes with
the owner's judge set.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.10: TypeSafe key sources, the transitional ~/.mycreds fallback and env inheritance (BACKLOG)

**Goal:** [Captured for future planning; updated 2026-10-24] The TypeSafe key normally comes from
the environment (`TYPESAFE_API_KEY`, sourced by the owner's shell from `~/.mycreds`, 0600).
**Done on the v1.3 branch (9d9c181, not yet merged to main at capture time):**
- the client reads `~/.mycreds` as a transitional fallback (line parse, no `source`, no export to
  children, 0600 enforced);
- `--probe` reports `key_source` and an ordered `key_expected` list without values.

**Still open:**
- (a) make `~/.mycreds` strictly the last source (it currently sits before `state`);
- (b) document env inheritance: a long-lived terminal multiplexer server (herdr, observed
  2026-10-24) keeps the environment it started with, so panes it spawns lack a newly sourced
  variable until that server restarts, while a new Konsole/Kitty tab has it — no machine reboot
  needed;
- (c) remove the fallback once agents inherit the env;
- (d) the `.toml` storage option from 999.9 step 2, if the owner keeps it.

Success criteria when promoted: (a)-(c) done with tests on synthetic files; the probe names the
missing source and the inheritance hint without printing any value.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.11: ai-kit-gsd-spec-discuss polish after the Phase 24 close-out (BACKLOG)

**Goal:** [Captured for future planning] Resolve the Important findings left at the Phase 24
skill-judge r3 PASS (`24-SKILL-JUDGE.md`, digest 7fc3f03ffb2fb714): a forced local answer that
matches no decision-table row; "one commit per phase" vs the spec workflow's own commit; analyzer
start while the same phase's CONTEXT is written; `state.record-session` on an early stop; trigger
keywords late in the description; the agent's action on `no_client`/`incompatible_client`.
Success criteria when promoted: each fixed with a pinned doc-contract test, and the owner's judge
set (native Opus + my-referee-one + my-referee-two) scores no Important.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.12: Runner and adapter cleanup after the Phase 25 reviews (BACKLOG)

**Goal:** [Captured for future planning] Cut what the Phase 25 code and ponytail reviews
(`25-REVIEW.md`) found unneeded or duplicated, with no behavior change:
- one "confirmed router" rule shared by Python's catalog `fallback_quota` and curated-config's
  `is_router`/`router_confirmed`/execute;
- a `quota_cycle` class from superpowers' `classify_dispatch_failure`, instead of three shell
  JSON parses in its SKILL;
- `plan_io.py` calls gsd-core's `buildAgentSkillsBlock` instead of re-implementing its
  skill-resolution rules;
- dead `runCli` state, the live-detection plumbing and the clamp helpers (IN-01, IN-03);
- the runner's embedded self-test harness (about 3,300 lines) moves to a sibling file that
  rendered copies do not carry;
- the lower user `cross_ai_timeout` is restored on cleanup (WR-05).

Success criteria when promoted: each change keeps the runner self-test, `make test` and
`make validate` green, and the template still renders a pristine copy.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.13: Register workflow.cross_ai_retry with gsd-core so config-set accepts it (BACKLOG)

**Goal:** [Captured for future planning] Ship a gsd-core capability manifest that registers
`workflow.cross_ai_retry.*`, so `config-set workflow.cross_ai_retry.<key>` validates and writes the
key instead of the owner hand-editing `.planning/config.json` (Phase 25.1 D-02). Starting evidence
(25.1-RESEARCH.md Q2): gsd-core 1.17.0 composes federated capability config keys from
`capability.json` manifests under `$GSD_HOME/.gsd/capabilities/<id>/` (global) or
`<project>/.gsd/capabilities/<id>/` (project); a project-scope capability needs a consent record
keyed to the project's realpath and its bundle hash, or it stays discovered-but-inactive. Open:
the exact manifest fields, whether a list-typed key such as `hard_waits_s` is accepted, the
global versus project scope choice and the consent gate.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.14: Install ai-kit skills as real copies through the skills CLI, synced across hosts (BACKLOG)

**Priority:** major. This is the next feature to implement after v1.3.
**Goal:** [Captured for future planning] The setup installs each ai-kit skill into a host as a
symlink. Replace that with real (non-symlink) installs done through the existing `skills` CLI
(`npx --yes skills add <owner/repo or local path> --yes`; the exact subcommands, flags, target-host
selectors and non-interactive behavior are unverified and must be checked live before planning).
The same layer must install, remove and sync the skills in each supported host: pi, cursor,
copilot, codex, opencode and claude. Open: how a local path is copied instead of linked; how
sync detects drift (a removed skill, a changed `SKILL.md`, a renamed directory); how it migrates
existing symlinks without touching unrelated user skills; and how it relates to `tools/setup.py`
atomic writes and backups, the dry-run-first rule, and the scratch-HOME rule for tests and e2e.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.15: A cross-AI chain skill for execute and review runs (BACKLOG)

**Priority:** major. It builds on the todo "Unify the review/execute lane TOML".
**Goal:** [Captured for future planning] Turn the xai execute/review scripts used in v1.3 into a
portable Agent Skill (suggested name `ai-kit-cross-ai-chain`, beside the single-call
`ai-kit-cross-ai`) that bundles the script as an asset and carries the calling convention:
an explicit `--role execute|review` with per-role rails, confinement, timeouts and done
criteria; run in the background and wait for the notification; read the AIKIT-XAI status line;
the retry ladder (same-session resume x3, then a new session x3; never switch harness, provider
or model); coverage gates behind verify (tasks versus tagged commits, early exit, SUMMARY
admissions, forbidden-file diff); a start-of-chain tree baseline and a run lock; an append-only
run ledger; an informational-versus-blocking Issues taxonomy; a classifier for execute results
(done, partial, another round) and for review results (severity fit by problem kind, test tier,
reproducibility, end-user reach, MVP versus production; converge, continue or escalate). Runtime,
model, effort, timeout and polling rate are decided, not hard-coded, optionally through the
decision system behind the TOML knob (never a hard dependency). Evidence, incident catalogue and
the ten ranked recommendations: `.planning/phases/999.15-cross-ai-chain-skill-for-execute-and-review-runs/999.15-LESSONS.md`.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.16: Evaluate one event-keyed playbook skill for the ai-kit-project-rules-* family (BACKLOG)

**Priority:** major. Decide it together with the todo "Refactor execute-gsd and rules-agents (SJ-1, SJ-3)".
**Goal:** [Captured for future planning] Owner request (2026-10-30): evaluate whether the rules should
become a single skill with several event-keyed playbooks or runbooks, so AGENTS.md is not
overloaded and the agent knows what to do in each case. The events: a new project (create
Makefiles, pre-commit hooks, tests, verifications); a new worktree is created; a plan or phase
finishes in open-gsd; a worktree is closed; a subagent is delegated; quota errors appear.
**Problem:** AGENTS.md carries too many workflow rules. The family today is seven sibling checkers
(agents, makefile, precommit, arch, docker, cicd, plus `ai-kit-project-rules-all` as the wrapper),
and skill-judge kept finding new detail in the big skills (Phase 26: execute-gsd and
rules-agents were accepted as-is and deferred).
**First step (mandatory):** a feasibility check against the already confirmed architecture, before
anything is built. Questions: is one skill with event-keyed runbooks better than the siblings (what
does it gain and lose for routing, skill-judge size, host portability); what would the trigger be
for each event on each host (a skill description, a hook, a manual call; claude, opencode and pi
are primary, codex and cursor secondary); how does it relate to `ai-kit-session-wake` (quota
events) and the execute skills (`ai-kit-spec-execute-gsd`, `ai-kit-spec-execute-superpowers`: phase
finish, subagent delegation). Nothing is built before this check; its result may be to keep the
siblings.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.17: Lite or strong executor choice through jev-fast-decision (BACKLOG)

**Priority:** major. Depends on the todo "Refactor execute-gsd and rules-agents (SJ-1, SJ-3)" (same skills, resume paths).
**Goal:** [Captured for future planning] Let the executor of a plan be chosen between a lighter
local combo (`my-coding-lite`), `my-coding`, or a model the user names explicitly, in
`ai-kit-spec-execute` and its `-gsd` and `-superpowers` adapters, deciding by asking the
`jev-fast-decision` skill; and let `ai-kit-spec-review` adapt the writing-plans instructions to a
lighter executor (`EXECUTOR_PROFILE=lite`). Requested by the llm-env project.
**Hard rule (owner):** `jev-fast-decision` is a black box. ai-kit text says only: ask that skill,
follow its own `SKILL.md`, the answer is advisory, and `needs_fallback` or no answer means the
rule-based default decides. No text about how it picks local versus remote, consent, TypeSafe,
environment variables or probes; the call line is re-read from the jev skill's own `SKILL.md`
when built, never copied.
**Reference input (not to be applied blindly):** six patches against the old main (f669709), an
implementation plan and a JEV-NOTES file listing the jev wording to strip, kept in the llm-env
project (its `tmp/ai-kit-lite-executor-patches` folder and
`docs/superpowers/plans/2026-10-30-ai-kit-lite-executor-routing.md`).
**Timing:** after the v1.3 milestone is merged to main (the patches must be re-made against the
new main); build it on the refactored execute-gsd and execute-superpowers resume paths (see the
SJ-1/SJ-2/SJ-3 refactor todo).
**Gates:** skill-judge with the current percent-based judge (needs `README.md` and `evals/` in
each changed skill), arch and unit tests, and a GSD-first waiver note recorded by the owner.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)
