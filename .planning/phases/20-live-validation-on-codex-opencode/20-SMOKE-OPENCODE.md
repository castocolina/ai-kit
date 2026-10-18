# Phase 20 — opencode smoke (headless iterations; EVAL-05 evidence is the user's interactive run, 20-INTERACTIVE-OPENCODE.md)

## Session
- date: 2026-10-18
- opencode --version: v2.0.31
- gsd-core: 1.17.0 at `<worktree>/.claude/gsd-core`; cached installer copy: 1.17.0 at `<installer>`
- runner: `.planning/scripts/cross-ai.mjs`; `// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=4 sha256=1b9fca44a07b641fef9114ec559c091dd73c7abeb2432fc9c6d7bb6b155b9dfa`
- --print-argv: `opencode <opencode-bin> ["run","--model","router-env/my-coding","--auto","--format","json","--standalone"]`
- model: `router-env/my-coding` (read from this repo runner's CONFIG; no model listing used to select it)

## Headless runs
Every headless dispatch uses this repo's runner from the repository root, with `--no-preamble` and exactly `--prefer opencode`; `no_change` with `cli_rc=0` is healthy for evidence-only work because the runner's clean-tree semantics classify it as no_change, while the host-written `smoke exit=0` and complete smoke evidence independently prove success.

| # | Purpose | Command (labels only) | Verbatim AIKIT-XAI line | runner exit | smoke exit | Outcome |
|---|---|---|---|---:|---:|---|
| 1 (first dispatch, interrupted) | Smoke through standalone runner; smoke itself completed, but the runner remained live without a final status line until this executor was terminated | `node .planning/scripts/cross-ai.mjs --prefer opencode --model-opencode <model> --mode exec --timeout 900 --outer-timeout 930 --no-preamble --child-pgid-file <opencode-run1.pgid>` | no final status line (failure/incomplete dispatch) | terminated by outer session SIGTERM, exit 143 | `smoke exit=0` | smoke steps passed; runner teardown not established |
| 2 (continuation) | Repeated Task 1 smoke through the runner | `node .planning/scripts/cross-ai.mjs --prefer opencode --model-opencode <model> --mode exec --timeout 900 --outer-timeout 930 --no-preamble --child-pgid-file <opencode-run2.pgid>` | `AIKIT-XAI status=no_change cli=opencode model=router-env/my-coding exit=1 cli_rc=0 elapsed=89s out=5703 tree=clean action=fallback` | 1 (expected no_change) | `smoke exit=0` | pass; all harness steps pass and host detected |
| 3 | Minimal `#high` suffix probe | `node .planning/scripts/cross-ai.mjs --prefer opencode --model-opencode <model>#high --mode exec --timeout 120 --outer-timeout 150 --no-preamble --child-pgid-file <opencode-run3.pgid>` | `AIKIT-XAI status=no_change cli=opencode model=router-env/my-coding#high exit=1 cli_rc=0 elapsed=4s out=605 tree=clean action=fallback` | 1 (expected no_change) | n/a | suffix accepted as model id; effort application unverified |
| 4 | Unseeded runtime enumeration under controlled PATH | `PATH=<controlled-bin> XDG_CACHE_HOME=<scratch> ... inventory --project-dir . --host opencode --refresh` | not a runner dispatch | 0 | n/a | pass; only opencode installed runtime exposed |
| 5 | CR-03/04: single SIGTERM after readiness | runner under `run-with-timeout 200`, `--child-pgid-file <opencode-signal1.pgid>`, `sleep 170` prompt and owned TMPDIR | `AIKIT-XAI status=signal cli=opencode model=router-env/my-coding exit=143 cli_rc=130 elapsed=41s out=566 tree=clean action=stop` | supervisor exit 143 | n/a | readiness observed; all recorded process groups empty |
| 6 | CR-03/04: attempted double SIGTERM, 0.3 s apart | runner under `run-with-timeout 200`, `--child-pgid-file <opencode-signal2.pgid>`, same prompt | `AIKIT-XAI status=signal cli=opencode model=router-env/my-coding exit=143 cli_rc=130 elapsed=41s out=11511 tree=clean action=stop` | supervisor exit 143 | n/a | one signal status and groups cleaned; wrapper had exited before second kill, so immediate second-signal behavior unverified |

## Environment findings
- First dispatch smoke finished successfully but the host runner did not terminate within the observation window and emitted no final status line; the outer session later terminated the executor. The continuation run completed in 89 seconds and emitted the healthy `no_change` status line. The first attempt's detached groups were checked and none remained.
- No `Managed service port ... already in use` appeared. Both smoke runs used the `--standalone` argv.
- Env names included inherited `PI_CODING_AGENT`, which is a detection/scrub signal but is not opencode's own signal, scrub list, or generic marker. The four-set validation therefore failed (`bad=['PI_CODING_AGENT']`); this is recorded, not represented as clean.
- No xai/grok billing/quota blocker or external_directory denial observed.
- C-W12 failure was not provoked; no safe deterministic trigger was available without touching the shared service.
- Signal run 2: the second `kill -TERM` found the wrapper already exited; its single signal line does not verify second-signal immediate group-kill behavior.

## Env names (names only)
AI_AGENT
CLAUDE_CODE_BRIDGE_SESSION_ID
CLAUDE_CODE_CHILD_SESSION
CLAUDE_CODE_EXECPATH
CLAUDE_CODE_MESSAGING_SOCKET
CLAUDE_CODE_MESSAGING_TOKEN
CLAUDE_CODE_SESSION_ATTENDED
CLAUDE_CODE_SESSION_ID
CLAUDE_EFFORT
CLAUDE_JOB_DIR
CLAUDE_PID
PI_CODING_AGENT
PI_MODEL
PI_OFFLINE
PI_PROVIDER
PI_REASONING_LEVEL
PI_SESSION_FILE
PI_SESSION_ID
PI_SKIP_VERSION_CHECK

`OPENCODE` was absent from this invoking shell's name dump; `AI_AGENT` was present. The host's smoke inventory independently reported `host opencode (detected)`. The four-set check failed because `PI_CODING_AGENT` is an inherited detection/scrub signal, not one of opencode's own host signals, scrub signals or generic markers; therefore `signals clean` was not established. `inherited, not a detection signal: CLAUDE_CODE_BRIDGE_SESSION_ID, CLAUDE_CODE_CHILD_SESSION, CLAUDE_CODE_EXECPATH, CLAUDE_CODE_MESSAGING_SOCKET, CLAUDE_CODE_MESSAGING_TOKEN, CLAUDE_CODE_SESSION_ATTENDED, CLAUDE_CODE_SESSION_ID, CLAUDE_EFFORT, CLAUDE_JOB_DIR, CLAUDE_PID; PI_MODEL, PI_OFFLINE, PI_PROVIDER, PI_REASONING_LEVEL, PI_SESSION_FILE, PI_SESSION_ID, PI_SKIP_VERSION_CHECK`.

## Smoke evidence (written by the harness inside opencode)

# Smoke evidence

## Steps
- step 1 ai-kit inventory, recommend, dry run: pass — dry run wrote nothing; host opencode (detected)
- step 2 project (a) local gsd-core install: pass — installed 1.17.0 into .opencode/gsd-core
- step 3 project (a) inventory, recommend, choices: pass — forced placeholders: none
- step 4 project (a) dry run, apply, validation: pass — apply and validation passed
- step 5 project (a) second apply: pass — second apply: writes 0, bytes identical, backups +1
- step 6 project (a) forced failure restores: pass — forced failure: exit 1, intel.enabled written then undone, restored
- step 7 project (a) post-apply install and planned == baked: pass — 35 agents; all equal; agents dir unchanged by a repeat install
- step 8 project (b) empty project, apply, validation: pass — reconciled 1 key paths
- step 9 matrix on the selected host: pass — matrix ran: 420 checks
- step 10 protected set unchanged: pass — unchanged

## gsd-core
- version: 1.17.0
- path: <worktree>/.claude/gsd-core

## Matrix
- checks: 420; agents: 35
- control_1: ok
- control_2: ok
- informational runtime row: not run (claude only)

## Local install
- host: opencode
- scope: local
- root: <scratch-a>/.opencode/gsd-core
- root: <scratch-b>/.opencode/gsd-core
- version: 1.17.0
- seed: absent
- installer: <installer>
- installer env: HOME and XDG_CONFIG_HOME/XDG_DATA_HOME/XDG_CACHE_HOME/XDG_STATE_HOME under <install-home>

## Planned vs baked
- agents: 35
- all equal
- idempotent re-install: yes

## Generated paths
- .opencode/agents/gsd-advisor-researcher.compact.md
- .opencode/agents/gsd-advisor-researcher.md
- .opencode/agents/gsd-ai-researcher.compact.md
- .opencode/agents/gsd-ai-researcher.md
- .opencode/agents/gsd-assumptions-analyzer.compact.md
- .opencode/agents/gsd-assumptions-analyzer.md
- .opencode/agents/gsd-code-fixer.compact.md
- .opencode/agents/gsd-code-fixer.md
- .opencode/agents/gsd-code-reviewer.compact.md
- .opencode/agents/gsd-code-reviewer.md
- .opencode/agents/gsd-codebase-mapper.compact.md
- .opencode/agents/gsd-codebase-mapper.md
- .opencode/agents/gsd-debug-session-manager.compact.md
- .opencode/agents/gsd-debug-session-manager.md
- .opencode/agents/gsd-debugger.md
- .opencode/agents/gsd-doc-classifier.compact.md
- .opencode/agents/gsd-doc-classifier.md
- .opencode/agents/gsd-doc-synthesizer.compact.md
- .opencode/agents/gsd-doc-synthesizer.md
- .opencode/agents/gsd-doc-verifier.compact.md
- .opencode/agents/gsd-doc-verifier.md
- .opencode/agents/gsd-doc-writer.compact.md
- .opencode/agents/gsd-doc-writer.md
- .opencode/agents/gsd-dom-verifier.compact.md
- .opencode/agents/gsd-dom-verifier.md
- .opencode/agents/gsd-domain-researcher.compact.md
- .opencode/agents/gsd-domain-researcher.md
- .opencode/agents/gsd-eval-auditor.compact.md
- .opencode/agents/gsd-eval-auditor.md
- .opencode/agents/gsd-eval-planner.compact.md
- .opencode/agents/gsd-eval-planner.md
- .opencode/agents/gsd-executor.md
- .opencode/agents/gsd-framework-selector.compact.md
- .opencode/agents/gsd-framework-selector.md
- .opencode/agents/gsd-integration-checker.compact.md
- .opencode/agents/gsd-integration-checker.md
- .opencode/agents/gsd-intel-updater.compact.md
- .opencode/agents/gsd-intel-updater.md
- .opencode/agents/gsd-mempalace-curator.compact.md
- .opencode/agents/gsd-mempalace-curator.md
- .opencode/agents/gsd-nyquist-auditor.compact.md
- .opencode/agents/gsd-nyquist-auditor.md
- .opencode/agents/gsd-pattern-mapper.compact.md
- .opencode/agents/gsd-pattern-mapper.md
- .opencode/agents/gsd-phase-researcher.md
- .opencode/agents/gsd-plan-checker.md
- .opencode/agents/gsd-planner.md
- .opencode/agents/gsd-project-researcher.compact.md
- .opencode/agents/gsd-project-researcher.md
- .opencode/agents/gsd-research-synthesizer.compact.md
- .opencode/agents/gsd-research-synthesizer.md
- .opencode/agents/gsd-roadmapper.compact.md
- .opencode/agents/gsd-roadmapper.md
- .opencode/agents/gsd-security-auditor.compact.md
- .opencode/agents/gsd-security-auditor.md
- .opencode/agents/gsd-ui-auditor.compact.md
- .opencode/agents/gsd-ui-auditor.md
- .opencode/agents/gsd-ui-checker.compact.md
- .opencode/agents/gsd-ui-checker.md
- .opencode/agents/gsd-ui-researcher.compact.md
- .opencode/agents/gsd-ui-researcher.md
- .opencode/agents/gsd-user-profiler.compact.md
- .opencode/agents/gsd-user-profiler.md
- .opencode/agents/gsd-verifier.md
- .opencode/commands/gsd-add-tests.md
- .opencode/commands/gsd-ai-integration-phase.md
- .opencode/commands/gsd-audit-fix.md
- .opencode/commands/gsd-audit-milestone.md
- .opencode/commands/gsd-audit-uat.md
- .opencode/commands/gsd-autonomous.md
- .opencode/commands/gsd-capture.md
- .opencode/commands/gsd-cleanup.md
- .opencode/commands/gsd-code-review.md
- .opencode/commands/gsd-complete-milestone.md
- .opencode/commands/gsd-config.md
- .opencode/commands/gsd-debug.md
- .opencode/commands/gsd-discuss-phase.md
- .opencode/commands/gsd-docs-update.md
- .opencode/commands/gsd-eval-review.md
- .opencode/commands/gsd-execute-phase.md
- .opencode/commands/gsd-explore.md
- .opencode/commands/gsd-extract-learnings.md
- .opencode/commands/gsd-fast.md
- .opencode/commands/gsd-forensics.md
- .opencode/commands/gsd-graphify.md
- .opencode/commands/gsd-health.md
- .opencode/commands/gsd-help.md
- .opencode/commands/gsd-import.md
- .opencode/commands/gsd-inbox.md
- .opencode/commands/gsd-ingest-docs.md
- .opencode/commands/gsd-manager.md
- .opencode/commands/gsd-map-codebase.md
- .opencode/commands/gsd-mempalace-capture.md
- .opencode/commands/gsd-mempalace-recall.md
- .opencode/commands/gsd-milestone-summary.md
- .opencode/commands/gsd-mvp-phase.md
- .opencode/commands/gsd-new-milestone.md
- .opencode/commands/gsd-new-project.md
- .opencode/commands/gsd-next.md
- .opencode/commands/gsd-ns-context.md
- .opencode/commands/gsd-ns-ideate.md
- .opencode/commands/gsd-ns-manage.md
- .opencode/commands/gsd-ns-project.md
- .opencode/commands/gsd-ns-review.md
- .opencode/commands/gsd-ns-workflow.md
- .opencode/commands/gsd-onboard.md
- .opencode/commands/gsd-pause-work.md
- .opencode/commands/gsd-phase.md
- .opencode/commands/gsd-plan-phase.md
- .opencode/commands/gsd-plan-review-convergence.md
- .opencode/commands/gsd-pr-branch.md
- .opencode/commands/gsd-profile-user.md
- .opencode/commands/gsd-progress.md
- .opencode/commands/gsd-quick-batch.md
- .opencode/commands/gsd-quick.md
- .opencode/commands/gsd-resume-work.md
- .opencode/commands/gsd-review-backlog.md
- .opencode/commands/gsd-secure-phase.md
- .opencode/commands/gsd-settings.md
- .opencode/commands/gsd-ship.md
- .opencode/commands/gsd-sketch.md
- .opencode/commands/gsd-spec-phase.md
- .opencode/commands/gsd-spike.md
- .opencode/commands/gsd-stats.md
- .opencode/commands/gsd-surface.md
- .opencode/commands/gsd-thread.md
- .opencode/commands/gsd-ui-phase.md
- .opencode/commands/gsd-ui-review.md
- .opencode/commands/gsd-ultraplan-phase.md
- .opencode/commands/gsd-undo.md
- .opencode/commands/gsd-update.md
- .opencode/commands/gsd-validate-phase.md
- .opencode/commands/gsd-verify-work.md
- .opencode/commands/gsd-workspace.md
- .opencode/commands/gsd-workstreams.md
- .opencode/gsd-core/
- .opencode/gsd-file-manifest.json
- .opencode/gsd-install-state.json
- .opencode/plugins/gsd-core.js
- .opencode/skills/gsd-add-tests
- .opencode/skills/gsd-ai-integration-phase
- .opencode/skills/gsd-audit-fix
- .opencode/skills/gsd-audit-milestone
- .opencode/skills/gsd-audit-uat
- .opencode/skills/gsd-autonomous
- .opencode/skills/gsd-capture
- .opencode/skills/gsd-cleanup
- .opencode/skills/gsd-code-review
- .opencode/skills/gsd-complete-milestone
- .opencode/skills/gsd-config
- .opencode/skills/gsd-debug
- .opencode/skills/gsd-discuss-phase
- .opencode/skills/gsd-docs-update
- .opencode/skills/gsd-eval-review
- .opencode/skills/gsd-execute-phase
- .opencode/skills/gsd-explore
- .opencode/skills/gsd-extract-learnings
- .opencode/skills/gsd-fast
- .opencode/skills/gsd-forensics
- .opencode/skills/gsd-graphify
- .opencode/skills/gsd-health
- .opencode/skills/gsd-help
- .opencode/skills/gsd-import
- .opencode/skills/gsd-inbox
- .opencode/skills/gsd-ingest-docs
- .opencode/skills/gsd-manager
- .opencode/skills/gsd-map-codebase
- .opencode/skills/gsd-mempalace-capture
- .opencode/skills/gsd-mempalace-recall
- .opencode/skills/gsd-milestone-summary
- .opencode/skills/gsd-mvp-phase
- .opencode/skills/gsd-new-milestone
- .opencode/skills/gsd-new-project
- .opencode/skills/gsd-next
- .opencode/skills/gsd-ns-context
- .opencode/skills/gsd-ns-ideate
- .opencode/skills/gsd-ns-manage
- .opencode/skills/gsd-ns-review
- .opencode/skills/gsd-ns-workflow
- .opencode/skills/gsd-onboard
- .opencode/skills/gsd-pause-work
- .opencode/skills/gsd-phase
- .opencode/skills/gsd-plan-phase
- .opencode/skills/gsd-plan-review-convergence
- .opencode/skills/gsd-pr-branch
- .opencode/skills/gsd-profile-user
- .opencode/skills/gsd-progress
- .opencode/skills/gsd-quick
- .opencode/skills/gsd-quick-batch
- .opencode/skills/gsd-resume-work
- .opencode/skills/gsd-review
- .opencode/skills/gsd-review-backlog
- .opencode/skills/gsd-secure-phase
- .opencode/skills/gsd-settings
- .opencode/skills/gsd-ship
- .opencode/skills/gsd-sketch
- .opencode/skills/gsd-spec-phase
- .opencode/skills/gsd-spike
- .opencode/skills/gsd-stats
- .opencode/skills/gsd-surface
- .opencode/skills/gsd-thread
- .opencode/skills/gsd-ui-phase
- .opencode/skills/gsd-ui-review
- .opencode/skills/gsd-ultraplan-phase
- .opencode/skills/gsd-undo
- .opencode/skills/gsd-update
- .opencode/skills/gsd-validate-phase
- .opencode/skills/gsd-workspace
- .opencode/skills/gsd-workstreams

## Artifacts
- project-a/plan.json
- project-a/config.json
- project-a/resolve-model.json
- project-a/baked.json
- project-b/plan.json
- project-b/config.json
- project-b/resolve-model.json
- project-b/baked.json

## Protected set
- protected set unchanged: pass

## Project (b) key paths
- plan_review.source_grounding_authority

## Caches
- seeded scratch cache; no runtime enumeration; byte-identical after every inventory

## Artifacts kept
- Eight files retained under `tmp/p20/headless/opencode-artifacts/`: project-a/{plan.json,config.json,resolve-model.json,baked.json} and project-b/{plan.json,config.json,resolve-model.json,baked.json}; project-a resolve-model has 35 agent records.

## Shared service
The headless `opencode run` executes with `--standalone`, so the model call runs on a private server. The runner's `opencode models` preflight has no `--standalone` flag and reads the user's managed service read-only; this is a known runner limitation. The pre-existing service was not stopped, restarted, or otherwise touched.

## Opencode lane from an opencode host (D-06, D-11)
The host lane is excluded by policy in code and tests. gsd-core has no code-level self-skip: `SELF_CLI=auto` for opencode (`workflows/review.md:126-149`). The LLM-judged mechanics trials (`--opencode` and `default_reviewers`, two trials each) were not re-run headless because they need a GSD project with plans; they are a REQUIRED human-verification item in step 6 of `20-INTERACTIVE-OPENCODE.md`, never optional.

## Local install and precedence (D-03, D-12)
The smoke's `## Local install`, `## Planned vs baked` and `## Generated paths` sections show local scope, exact scratch roots, pinned version, planned==baked for all 35 agents, idempotent re-install, and generated `.opencode/gsd-core/` paths. Baked files and the project-local resolve-model were verified by the harness. Loader precedence was not observed headless: there is no standalone listing path, so the required interactive step 7 of `20-INTERACTIVE-OPENCODE.md` must run `smoke --keep-scratch`. The global alternative (`~/.gsd/defaults.json` plus a global reinstall) was explained but not run; it would affect every opencode project. The gitignore decision is prefix-based: ignore GSD-generated prefixes, do not blanket-ignore `.opencode/`; curated-config reports but does not edit `.gitignore`.

## Effort suffix probe
Run 3: `AIKIT-XAI status=no_change cli=opencode model=router-env/my-coding#high exit=1 cli_rc=0 elapsed=4s out=605 tree=clean action=fallback`. Verdict: accepted (not rejected; whether the effort is applied is unverified). The successful response proves only that opencode 2.x accepted the `#high` suffix as part of the model id; it does not prove effort application.

## Deferred-in items
- C-W12: controlled PATH exposed only opencode plus node/python3/git/env/sh/bash; inventory `installed_runtimes` was `['opencode']` (enumeration scoped: opencode only). `runtime_enumeration` was `{'opencode': 'ok'}`. The inventory's listing process `opencode models` reads the user's managed service read-only; its image-capability probe starts a private `opencode serve --hostname 127.0.0.1 --port 0` in its own session and stops it in `finally`. The before/after `opencode serve` listings were identical, showing only the pre-existing `--service` process; the private probe was gone. failure not provoked: no safe deterministic trigger was available without touching the shared service.
- CR-03/CR-04 run 1:
- readiness: live child 159620 (opencode run), sleep 170 observed
  - Status: `AIKIT-XAI status=signal cli=opencode model=router-env/my-coding exit=143 cli_rc=130 elapsed=41s out=566 tree=clean action=stop`; elapsed was 41s from signal (runner elapsed; process readiness plus time-to-signal included). Spawn pids from `opencode-signal1.pgid`: 159537, 159538, 159539, 159540, 159541, 159542, 159620, 161597, 161598, 161599, 161600, 161601; all process groups were empty afterward. Run-owned TMPDIR `cross-ai-*`/`xai-*` check had no runner temp dirs; unrelated entries left by opencode were listed, then TMPDIR removed.
- CR-03/CR-04 run 2:
- readiness: live child 162453 (opencode run), sleep 170 observed
  - Status: `AIKIT-XAI status=signal cli=opencode model=router-env/my-coding exit=143 cli_rc=130 elapsed=41s out=11511 tree=clean action=stop`. The attempted SIGTERMs were intended 0.3s apart, but by the second `kill -TERM` the wrapper had already exited (`No such process`); immediate second-signal group-kill behavior is unverified. Spawn pids from `opencode-signal2.pgid` were checked; all groups were empty after completion. Run-owned TMPDIR `cross-ai-*`/`xai-*` check was performed and the directory removed.
- Interactive run: pending; see `20-INTERACTIVE-OPENCODE.md`. The user's TUI env names, smoke, loader precedence and artifacts are the EVAL-05 evidence.

## Interactive run
pending: `20-INTERACTIVE-OPENCODE.md`; the TUI env names, smoke, loader observation and artifacts from the user's session are the EVAL-05 evidence.
