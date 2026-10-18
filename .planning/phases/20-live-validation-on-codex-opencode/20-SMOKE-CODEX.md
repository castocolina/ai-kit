# Phase 20 — codex smoke (headless iterations; EVAL-04 evidence is the user's interactive run, 20-INTERACTIVE-CODEX.md)

## Session
- date: 2026-10-18T09:03:27Z
- codex --version: codex-cli 0.162.1
- gsd-core: 1.17.0 at `<worktree>/.claude/gsd-core`; cached installer copy: 1.17.0 at `<installer>`
- product_commit: 4e53b3e
- runner: `.planning/scripts/cross-ai.mjs`; `// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=4 sha256=1b9fca44a07b641fef9114ec559c091dd73c7abeb2432fc9c6d7bb6b155b9dfa`
- --print-argv: `codex ["exec","--sandbox","workspace-write","--skip-git-repo-check","-C","<worktree>","-m","gpt-5.6-luna","--json","-o","<tmp>/last-message.md","-"]`
- model: `gpt-5.6-luna` (this repo's runner CONFIG)
- sandbox: `--codex-sandbox workspace-write`

## Headless runs
Every headless dispatch uses this repo's runner from the repository root, with `--no-preamble` and exactly `--prefer codex`; `no_change` with `cli_rc=0` is healthy for evidence-only work because the runner's own clean-tree semantics classify it as no_change, while the host-written `smoke exit=0` and complete smoke evidence independently prove success.

| # | Purpose | Command (labels only) | Verbatim AIKIT-XAI line | runner exit | smoke exit | Outcome |
|---|---|---|---|---:|---:|---|
| 1 | Codex host smoke; workspace-write sandbox | `node .planning/scripts/cross-ai.mjs --prefer codex --model-codex <model> --mode exec --codex-sandbox workspace-write --timeout 900 --outer-timeout 930 --no-preamble --child-pgid-file <pgid-file>` | `AIKIT-XAI status=no_change cli=codex model=gpt-5.6-luna exit=1 cli_rc=0 elapsed=92s out=6776 tree=clean action=fallback` | 1 (expected no_change) | `smoke exit=0` | pass; all steps pass and host detected |
| 2 | Codex JSON event types (direct scrubbed exec; one non-runner call specifically to capture raw `--json` events) | `env <all HOST_SIGNAL_ENV_VARS unset> codex exec --ephemeral --ignore-user-config --skip-git-repo-check --sandbox read-only -C <scratch> -m <model> --json` | not a runner dispatch | 0 | n/a | pass; event sequence recorded below |
| 3 | Unseeded runtime enumeration under controlled PATH | `PATH=<controlled-bin> XDG_CACHE_HOME=<scratch> ... inventory --project-dir . --host codex --refresh` | not a runner dispatch | 0 | n/a | pass; installed runtime list is codex only |
| 4 | Failure-vs-empty listing attempt using a fresh CODEX_HOME | same controlled-PATH inventory with `CODEX_HOME=<scratch>` | not a runner dispatch | 0 | n/a | listing remained `ok`; failure not provoked |
| 5 | CR-03/04: single SIGTERM following readiness | runner with `--child-pgid-file <codex-signal1.pgid>`, `sleep 170` prompt, runner under `run-with-timeout` | `AIKIT-XAI status=signal cli=codex model=gpt-5.6-luna exit=143 cli_rc=- elapsed=4s out=409 tree=clean action=stop` | 143 from supervisor | n/a | readiness confirmed; signal status and cleanup recorded |
| 6 | CR-03/04: double SIGTERM, 0.3 s apart | runner with `--child-pgid-file <codex-signal2.pgid>`, same prompt | `AIKIT-XAI status=signal cli=codex model=gpt-5.6-luna exit=143 cli_rc=- elapsed=4s out=439 tree=clean action=stop` | 143 from supervisor | n/a | readiness confirmed; second signal reached wrapper after first had ended (see finding) |

## Environment findings
- Smoke run: none; smoke reported `protected set unchanged: pass`.
- Run 2: `turn.completed` appeared; no `error` event. Recovery path not provoked (cannot be forced deterministically); shortcut comment stays.
- C-W12 failure attempt: fresh `CODEX_HOME` did not provoke listing failure; `runtime_enumeration.codex` remained `ok`. Thus failed-vs-empty is not distinguished by this attempted failure; it is recorded as not provoked, not as proof of either behavior.
- Signal run 2 deviation: the runner completed its signal handling before the second `kill -TERM` reached the wrapper (`kill: ... No such process`); the recorded status remains a single signal line, but this does not verify second-signal immediate group-kill timing.
- No external-directory denial, permission block, quota or capacity blocker observed.

## Env names (names only)
CODEX_APPLY_PATCH_PRESERVE_LINE_ENDINGS
CODEX_CI
CODEX_SANDBOX_NETWORK_DISABLED
CODEX_SESSION_ID
CODEX_THREAD_ID
CODEX_VERSION
PI_MODEL
PI_OFFLINE
PI_PROVIDER
PI_REASONING_LEVEL
PI_SESSION_FILE
PI_SESSION_ID
PI_SKIP_VERSION_CHECK
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

`CODEX_THREAD_ID` and `CODEX_VERSION` both appeared in this `codex exec` tool environment. The four-set check returned `signals clean`: among `HOST_SIGNAL_ENV_VARS`, no foreign detection/scrub signal leaked; Codex's own host signals and generic marker allowance were applied. `inherited, not a detection signal: CLAUDE_CODE_BRIDGE_SESSION_ID, CLAUDE_CODE_CHILD_SESSION, CLAUDE_CODE_EXECPATH, CLAUDE_CODE_MESSAGING_SOCKET, CLAUDE_CODE_MESSAGING_TOKEN, CLAUDE_CODE_SESSION_ATTENDED, CLAUDE_CODE_SESSION_ID, CLAUDE_EFFORT, CLAUDE_JOB_DIR, CLAUDE_PID; PI_MODEL, PI_OFFLINE, PI_PROVIDER, PI_REASONING_LEVEL, PI_SESSION_FILE, PI_SESSION_ID, PI_SKIP_VERSION_CHECK` (the PI names are not members of the detection set).

## Smoke evidence (written by the harness inside codex)

Regenerated 2026-10-18 after the code-review fixes (20-REVIEW-FIX.md), verbatim from `tmp/p20/headless/codex-smoke.md`: one runner dispatch (`--prefer codex`, `--codex-sandbox workspace-write`, `--no-preamble`) ended `AIKIT-XAI status=no_change cli=codex model=gpt-5.6-luna exit=1 cli_rc=0 elapsed=88s tree=clean action=fallback` with `smoke exit=0`. Two earlier dispatches with the default TMPDIR ended `no_change` in 73 s and 43 s without a finished smoke (an empty smoke log, then none); a direct `codex exec` with the same argv and the third runner dispatch (TMPDIR under the repo's `tmp/`) completed. Cause not determined; recorded as a finding, not retried further. The section below replaces the earlier hand-copied list (WR-09).

# Smoke evidence

## Steps
- step 1 ai-kit inventory, recommend, dry run: pass — dry run wrote nothing; host codex (detected)
- step 2 project (a) local gsd-core install: pass — installed 1.17.0 into .codex/gsd-core
- step 3 project (a) inventory, recommend, choices: pass — forced placeholders: none
- step 4 project (a) dry run, apply, validation: pass — apply and validation passed
- step 5 project (a) second apply: pass — second apply: writes 0, bytes identical, backups +1
- step 6 project (a) forced failure restores: pass — forced failure: exit 1, intel.enabled written then undone, restored
- step 7 project (a) post-apply install and planned == baked: pass — 35 agents; planned == baked == resolve-model; repeat install unchanged
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
- project-a: scope local, root <scratch-a>/.codex/gsd-core, version 1.17.0 (from inventory)
- project-b: scope local, root <scratch-b>/.codex/gsd-core, version 1.17.0 (from inventory)
- seed: absent
- installer: <installer> --<host> --local --no-legacy-cleanup
- installer env: an allowlist (PATH, locale, TERM, USER, SHELL, TZ, TMPDIR) plus HOME and XDG_CONFIG_HOME/XDG_DATA_HOME/XDG_CACHE_HOME/XDG_STATE_HOME under <install-home>

## Planned vs baked
- project-a: 35 agents; planned == baked == resolve-model
- project-a: a repeat install left the agents dir unchanged
- project-b: 35 agents; planned == baked == resolve-model

## Generated paths
- in every project (project-a, project-b):
- .codex/agents/gsd-advisor-researcher.compact.md
- .codex/agents/gsd-advisor-researcher.md
- .codex/agents/gsd-advisor-researcher.toml
- .codex/agents/gsd-ai-researcher.compact.md
- .codex/agents/gsd-ai-researcher.md
- .codex/agents/gsd-ai-researcher.toml
- .codex/agents/gsd-assumptions-analyzer.compact.md
- .codex/agents/gsd-assumptions-analyzer.md
- .codex/agents/gsd-assumptions-analyzer.toml
- .codex/agents/gsd-code-fixer.compact.md
- .codex/agents/gsd-code-fixer.md
- .codex/agents/gsd-code-fixer.toml
- .codex/agents/gsd-code-reviewer.compact.md
- .codex/agents/gsd-code-reviewer.md
- .codex/agents/gsd-code-reviewer.toml
- .codex/agents/gsd-codebase-mapper.compact.md
- .codex/agents/gsd-codebase-mapper.md
- .codex/agents/gsd-codebase-mapper.toml
- .codex/agents/gsd-debug-session-manager.compact.md
- .codex/agents/gsd-debug-session-manager.md
- .codex/agents/gsd-debug-session-manager.toml
- .codex/agents/gsd-debugger.md
- .codex/agents/gsd-debugger.toml
- .codex/agents/gsd-doc-classifier.compact.md
- .codex/agents/gsd-doc-classifier.md
- .codex/agents/gsd-doc-classifier.toml
- .codex/agents/gsd-doc-synthesizer.compact.md
- .codex/agents/gsd-doc-synthesizer.md
- .codex/agents/gsd-doc-synthesizer.toml
- .codex/agents/gsd-doc-verifier.compact.md
- .codex/agents/gsd-doc-verifier.md
- .codex/agents/gsd-doc-verifier.toml
- .codex/agents/gsd-doc-writer.compact.md
- .codex/agents/gsd-doc-writer.md
- .codex/agents/gsd-doc-writer.toml
- .codex/agents/gsd-dom-verifier.compact.md
- .codex/agents/gsd-dom-verifier.md
- .codex/agents/gsd-dom-verifier.toml
- .codex/agents/gsd-domain-researcher.compact.md
- .codex/agents/gsd-domain-researcher.md
- .codex/agents/gsd-domain-researcher.toml
- .codex/agents/gsd-eval-auditor.compact.md
- .codex/agents/gsd-eval-auditor.md
- .codex/agents/gsd-eval-auditor.toml
- .codex/agents/gsd-eval-planner.compact.md
- .codex/agents/gsd-eval-planner.md
- .codex/agents/gsd-eval-planner.toml
- .codex/agents/gsd-executor.md
- .codex/agents/gsd-executor.toml
- .codex/agents/gsd-framework-selector.compact.md
- .codex/agents/gsd-framework-selector.md
- .codex/agents/gsd-framework-selector.toml
- .codex/agents/gsd-integration-checker.compact.md
- .codex/agents/gsd-integration-checker.md
- .codex/agents/gsd-integration-checker.toml
- .codex/agents/gsd-intel-updater.compact.md
- .codex/agents/gsd-intel-updater.md
- .codex/agents/gsd-intel-updater.toml
- .codex/agents/gsd-mempalace-curator.compact.md
- .codex/agents/gsd-mempalace-curator.md
- .codex/agents/gsd-mempalace-curator.toml
- .codex/agents/gsd-nyquist-auditor.compact.md
- .codex/agents/gsd-nyquist-auditor.md
- .codex/agents/gsd-nyquist-auditor.toml
- .codex/agents/gsd-pattern-mapper.compact.md
- .codex/agents/gsd-pattern-mapper.md
- .codex/agents/gsd-pattern-mapper.toml
- .codex/agents/gsd-phase-researcher.md
- .codex/agents/gsd-phase-researcher.toml
- .codex/agents/gsd-plan-checker.md
- .codex/agents/gsd-plan-checker.toml
- .codex/agents/gsd-planner.md
- .codex/agents/gsd-planner.toml
- .codex/agents/gsd-project-researcher.compact.md
- .codex/agents/gsd-project-researcher.md
- .codex/agents/gsd-project-researcher.toml
- .codex/agents/gsd-research-synthesizer.compact.md
- .codex/agents/gsd-research-synthesizer.md
- .codex/agents/gsd-research-synthesizer.toml
- .codex/agents/gsd-roadmapper.compact.md
- .codex/agents/gsd-roadmapper.md
- .codex/agents/gsd-roadmapper.toml
- .codex/agents/gsd-security-auditor.compact.md
- .codex/agents/gsd-security-auditor.md
- .codex/agents/gsd-security-auditor.toml
- .codex/agents/gsd-ui-auditor.compact.md
- .codex/agents/gsd-ui-auditor.md
- .codex/agents/gsd-ui-auditor.toml
- .codex/agents/gsd-ui-checker.compact.md
- .codex/agents/gsd-ui-checker.md
- .codex/agents/gsd-ui-checker.toml
- .codex/agents/gsd-ui-researcher.compact.md
- .codex/agents/gsd-ui-researcher.md
- .codex/agents/gsd-ui-researcher.toml
- .codex/agents/gsd-user-profiler.compact.md
- .codex/agents/gsd-user-profiler.md
- .codex/agents/gsd-user-profiler.toml
- .codex/agents/gsd-verifier.md
- .codex/agents/gsd-verifier.toml
- .codex/gsd-core/
- .codex/gsd-file-manifest.json
- .codex/gsd-install-state.json
- .codex/skills/gsd-add-tests
- .codex/skills/gsd-ai-integration-phase
- .codex/skills/gsd-audit-fix
- .codex/skills/gsd-audit-milestone
- .codex/skills/gsd-audit-uat
- .codex/skills/gsd-autonomous
- .codex/skills/gsd-capture
- .codex/skills/gsd-cleanup
- .codex/skills/gsd-code-review
- .codex/skills/gsd-complete-milestone
- .codex/skills/gsd-config
- .codex/skills/gsd-debug
- .codex/skills/gsd-discuss-phase
- .codex/skills/gsd-docs-update
- .codex/skills/gsd-eval-review
- .codex/skills/gsd-execute-phase
- .codex/skills/gsd-explore
- .codex/skills/gsd-extract-learnings
- .codex/skills/gsd-fast
- .codex/skills/gsd-forensics
- .codex/skills/gsd-graphify
- .codex/skills/gsd-health
- .codex/skills/gsd-help
- .codex/skills/gsd-import
- .codex/skills/gsd-inbox
- .codex/skills/gsd-ingest-docs
- .codex/skills/gsd-manager
- .codex/skills/gsd-map-codebase
- .codex/skills/gsd-mempalace-capture
- .codex/skills/gsd-mempalace-recall
- .codex/skills/gsd-milestone-summary
- .codex/skills/gsd-mvp-phase
- .codex/skills/gsd-new-milestone
- .codex/skills/gsd-new-project
- .codex/skills/gsd-next
- .codex/skills/gsd-ns-context
- .codex/skills/gsd-ns-ideate
- .codex/skills/gsd-ns-manage
- .codex/skills/gsd-ns-project
- .codex/skills/gsd-ns-review
- .codex/skills/gsd-ns-workflow
- .codex/skills/gsd-onboard
- .codex/skills/gsd-pause-work
- .codex/skills/gsd-phase
- .codex/skills/gsd-plan-phase
- .codex/skills/gsd-plan-review-convergence
- .codex/skills/gsd-pr-branch
- .codex/skills/gsd-profile-user
- .codex/skills/gsd-progress
- .codex/skills/gsd-quick
- .codex/skills/gsd-quick-batch
- .codex/skills/gsd-resume-work
- .codex/skills/gsd-review
- .codex/skills/gsd-review-backlog
- .codex/skills/gsd-secure-phase
- .codex/skills/gsd-settings
- .codex/skills/gsd-ship
- .codex/skills/gsd-sketch
- .codex/skills/gsd-spec-phase
- .codex/skills/gsd-spike
- .codex/skills/gsd-stats
- .codex/skills/gsd-surface
- .codex/skills/gsd-thread
- .codex/skills/gsd-ui-phase
- .codex/skills/gsd-ui-review
- .codex/skills/gsd-ultraplan-phase
- .codex/skills/gsd-undo
- .codex/skills/gsd-update
- .codex/skills/gsd-validate-phase
- .codex/skills/gsd-verify-work
- .codex/skills/gsd-workspace
- .codex/skills/gsd-workstreams
- only in project-a: none
- only in project-b: none
- gitignore decision: ignore these prefixes in the target project; curated-config reports, never edits .gitignore (D-12)

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
- unchanged
- host-managed changed: none

## Project (b) key paths
- plan_review.source_grounding_authority

## Caches
- seeded scratch cache; no runtime enumeration; byte-identical after every inventory

## Artifacts kept
- Eight files retained under `tmp/p20/headless/codex-artifacts/`: project-a/{plan.json,config.json,resolve-model.json,baked.json} and project-b/{plan.json,config.json,resolve-model.json,baked.json}; project-a resolve-model has 35 agent records.

## Deferred-in items
- Codex JSON event types: `['thread.started', 'turn.started', 'item.completed', 'turn.completed']`; `turn.completed` present; no `error` event. recovered stream error: not provoked (cannot be forced deterministically); the shortcut comment in the template stays. This one direct scrubbed `codex exec --json` run was intentionally outside the runner to capture the CLI's event stream itself.
- C-W12: the unseeded inventory used a temporary PATH containing only codex, node, python3, git, env, sh and bash. Its `installed_runtimes` was exactly `['codex']` (enumeration scoped: codex only), and `runtime_enumeration` was `{'codex': 'ok'}`. A second inventory used a fresh scratch `CODEX_HOME`; its status also remained `ok`, so failure-versus-empty was not provoked. Recommend was run on that inventory; codex why text included `best execution score within ceiling (<= 4/1M, 75th pct of 8 families)` and tier notes included `rigor standard preset (spec §5)`. Other installed CLIs were unavailable on the controlled PATH.
- CR-03/CR-04 run 1:
- readiness: live child 105521 (codex exec), sleep 170 observed
  - status: `AIKIT-XAI status=signal cli=codex model=gpt-5.6-luna exit=143 cli_rc=- elapsed=4s out=409 tree=clean action=stop`
  - first SIGTERM-to-status elapsed: about 4 s (runner-reported); supervisor exit 143
  - `codex-signal1.pgid` spawn pids: 105470, 105471, 105472, 105473, 105474, 105475, 105521, 106031, 106032, 106034, 106035, 106036; every process group was empty afterward
  - run-owned TMPDIR `cross-ai-*`/`xai-*` check: empty; TMPDIR removed
- CR-03/CR-04 run 2:
- readiness: live child 106788 (codex exec), sleep 170 observed
  - status: `AIKIT-XAI status=signal cli=codex model=gpt-5.6-luna exit=143 cli_rc=- elapsed=4s out=439 tree=clean action=stop`
  - SIGTERMs were 0.302 s apart; the status was recorded about 0.30 s after the second signal, but the wrapper had already exited before that second kill could be delivered; immediate second-signal group-kill behavior remains unverified
  - `codex-signal2.pgid` spawn pids: 106729, 106730, 106738, 106739, 106740, 106742, 106788, 107218, 107219, 107221, 107222, 107223; every process group was empty afterward
  - run-owned TMPDIR `cross-ai-*`/`xai-*` check: empty; TMPDIR removed
- Interactive run: pending; see `20-INTERACTIVE-CODEX.md`. The user's TUI env names, smoke and artifacts are the EVAL-04 evidence.

## Interactive run

- Script: `20-INTERACTIVE-CODEX.md`
- Pending EVAL item: EVAL-04; headless runs are not EVAL evidence (SPEC constraint).
- Required steps: 1–5.
- Return: names-only environment list, smoke evidence and log, fresh-baseline snapshot check, and the full artifacts directory (`plan.json`, resulting `config.json`, `resolve-model.json`, `baked.json` for each label). Also return any Codex trust prompt note.

## Phase gates

- `make test`: `exit=0`; 56 module results, 4,343 tests total. The matrix module reports `Ran 36 tests`; loader totals are `TestResolveModelMatrix=9`, `TestResolveModelMatrixCodex=9`, `TestResolveModelMatrixOpencode=9`, module total 36 (one matrix run, no second run).
- `make validate`: `exit=0`; all hooks passed after the in-phase pyright correction (initial run exposed 23 typing errors in the matrix test mixin and one nullable mismatch assertion).
- Verbose pre-push unittest hook: `exit=0`; 43 modules, 4,125 tests total.
- `make e2e-docker`: `exit=0` (`ai-kit clean-room E2E: PASS`).
- `snapshot --check tmp/p20/plan07.before.json`: `snapshot ok`. Older plan04 baseline: `snapshot ok` (information only).
- `secret-scan`: clean. `$HOME` literal scan: clean.
- Leak check: no process started by this plan remains.

