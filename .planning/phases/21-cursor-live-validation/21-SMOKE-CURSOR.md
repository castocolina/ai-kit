# Phase 21 — cursor smoke (headless iteration; SPEC R1 acceptance is the user's interactive run, 21-INTERACTIVE-CURSOR.md)

## Session
- date: 2026-10-18T22:42:57Z
- cursor-agent version: 2026.10.14-941492e (read from the installed version directory name)
- gsd-core: 1.17.0 at `<worktree>/.claude/gsd-core`; cached installer copy: 1.17.0 at `<installer>`
- product_commit: 9129390
- runner: `.planning/scripts/cross-ai.mjs`; `// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=5 sha256=6666258f553dc872d4f6967ae6529853c3aab988894da4b7427671ac8d9420c8`
- --print-argv: `cursor <home>/.local/bin/cursor-agent ["-p","--output-format","json","--model","composer-2.5","--trust","--force","--sandbox","disabled","--approve-mcps","--workspace","<worktree>"]`
- model: `composer-2.5` (explicit non-fast model, not `auto` or the runner CONFIG default)
- scratch home: `<scratch-home>/.cursor` for CURSOR_CONFIG_DIR, `<scratch-home>/.config` for XDG_CONFIG_HOME, `<scratch-home>/.cache` for XDG_CACHE_HOME, and `<scratch-home>/.local/state` for XDG_STATE_HOME; login symlink at `<scratch-home>/.config/cursor/auth.json` points to `<home>/.config/cursor/auth.json` (link target not read)
- Isolation scope: scratch isolation redirects HOME, CURSOR_CONFIG_DIR, XDG_CONFIG_HOME, XDG_CACHE_HOME and XDG_STATE_HOME; XDG_DATA_HOME remains unchanged because cursor-agent locates its own install there. `snapshot --check` proves the protected allowlist unchanged: the strict `~/.cursor/cli-config.json` and `hooks.json` entries, `~/.cursor/agents` and `skills` name listings (names only), plus `~/.codex`, `~/.config/opencode`, `~/.claude` and `~/.gsd` entries. This is exactly the snapshot allowlist, no more; another write the CLI might make elsewhere in the real home is not checked.
- cursor-agent invoked only by the runner.

## Headless runs
Every evidence-only dispatch uses this repo's template-5 runner from the repository root with `--prefer cursor` alone, explicit `--model-cursor composer-2.5`, `--mode exec`, `--no-preamble` and `--child-pgid-file`; `no_change` with `cli_rc=0` is healthy because the smoke writes only under gitignored `tmp/` and `/tmp`, while the host-written smoke log and evidence independently prove execution.

| # | Purpose | Command (labels only) | Verbatim AIKIT-XAI line | runner exit | smoke exit | Outcome |
|---|---|---|---|---:|---|---|
| 1 | Cursor headless smoke under scratch HOME | `node .planning/scripts/cross-ai.mjs --prefer cursor --model-cursor composer-2.5 --mode exec --timeout 900 --outer-timeout 930 --no-preamble --child-pgid-file <pgid-file>` | `AIKIT-XAI status=no_change cli=cursor model=composer-2.5 exit=1 cli_rc=0 elapsed=106s out=1669 tree=clean action=fallback` | 1 (expected no_change) | `smoke exit=0` | pass; all ten steps pass, host detected |

headless verdict: green (attempt 1: status=no_change cli_rc=0, spawn recorded, smoke exit=0, steps 10/10 pass)

## Environment findings
- Runner classified the successful evidence-only run as `no_change` and exited 1: `AIKIT-XAI status=no_change cli=cursor model=composer-2.5 exit=1 cli_rc=0 elapsed=106s out=1669 tree=clean action=fallback`; the host smoke independently ended `smoke exit=0` with ten passing steps. This is healthy runner semantics, not a smoke failure.
- No quota, billing, capacity, permission, bad-model, timeout or signal blocker observed.

## Env names (names only)
AGENT_TRANSCRIPTS
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
CURSOR_AGENT
CURSOR_CONFIG_DIR
CURSOR_CONVERSATION_ID
CURSOR_INVOKED_AS
CURSOR_REQUEST_ID
CURSOR_RIPGREP_PATH
PI_MODEL
PI_OFFLINE
PI_PROVIDER
PI_REASONING_LEVEL
PI_SESSION_FILE
PI_SESSION_ID
PI_SKIP_VERSION_CHECK

`signals clean`: no foreign host-signal name was inherited. `CURSOR_AGENT` was present inside cursor's shell tool. `inherited, not a detection signal: AGENT_TRANSCRIPTS, CLAUDE_CODE_BRIDGE_SESSION_ID, CLAUDE_CODE_CHILD_SESSION, CLAUDE_CODE_EXECPATH, CLAUDE_CODE_MESSAGING_SOCKET, CLAUDE_CODE_MESSAGING_TOKEN, CLAUDE_CODE_SESSION_ATTENDED, CLAUDE_CODE_SESSION_ID, CLAUDE_EFFORT, CLAUDE_JOB_DIR, CLAUDE_PID, PI_MODEL, PI_OFFLINE, PI_PROVIDER, PI_REASONING_LEVEL, PI_SESSION_FILE, PI_SESSION_ID, PI_SKIP_VERSION_CHECK`.

## Smoke evidence (written by the harness inside cursor)

# Smoke evidence

## Steps
- step 1 ai-kit inventory, recommend, dry run: pass — dry run wrote nothing; host cursor (detected)
- step 2 project (a) local gsd-core install: pass — installed 1.17.0 into .cursor/gsd-core
- step 3 project (a) inventory, recommend, choices: pass — forced placeholders: none
- step 4 project (a) dry run, apply, validation: pass — apply and validation passed
- step 5 project (a) second apply: pass — second apply: writes 0, bytes identical, backups +1
- step 6 project (a) forced failure restores: pass — forced failure: exit 1, intel.enabled written then undone, restored
- step 7 project (a) post-apply install and resolve-model check: pass — 35 agents; plan == resolve-model (resolve-model only); repeat install unchanged
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
- project-a: scope local, root <scratch-a>/.cursor/gsd-core, version 1.17.0 (from inventory)
- project-b: scope local, root <scratch-b>/.cursor/gsd-core, version 1.17.0 (from inventory)
- seed: absent
- installer: <installer> --<host> --local --no-legacy-cleanup
- installer env: an allowlist (PATH, locale, TERM, USER, SHELL, TZ, TMPDIR) plus HOME and XDG_CONFIG_HOME/XDG_DATA_HOME/XDG_CACHE_HOME/XDG_STATE_HOME under <install-home>

## Planned vs baked
- project-a: 35 agents; plan == resolve-model (resolve-model only: the cursor installer bakes no model line, baked files verified model-free)
- project-a: 29 compact agent files carry no model: line; not compared
- project-a: a repeat install left the agents dir unchanged
- project-b: 35 agents; plan == resolve-model (resolve-model only: the cursor installer bakes no model line, baked files verified model-free)
- project-b: 29 compact agent files carry no model: line; not compared

## Generated paths
- in every project (project-a, project-b):
- .cursor/.gsd-profile
- .cursor/.gsd-staging/
- .cursor/agents/gsd-advisor-researcher.compact.md
- .cursor/agents/gsd-advisor-researcher.md
- .cursor/agents/gsd-ai-researcher.compact.md
- .cursor/agents/gsd-ai-researcher.md
- .cursor/agents/gsd-assumptions-analyzer.compact.md
- .cursor/agents/gsd-assumptions-analyzer.md
- .cursor/agents/gsd-code-fixer.compact.md
- .cursor/agents/gsd-code-fixer.md
- .cursor/agents/gsd-code-reviewer.compact.md
- .cursor/agents/gsd-code-reviewer.md
- .cursor/agents/gsd-codebase-mapper.compact.md
- .cursor/agents/gsd-codebase-mapper.md
- .cursor/agents/gsd-debug-session-manager.compact.md
- .cursor/agents/gsd-debug-session-manager.md
- .cursor/agents/gsd-debugger.md
- .cursor/agents/gsd-doc-classifier.compact.md
- .cursor/agents/gsd-doc-classifier.md
- .cursor/agents/gsd-doc-synthesizer.compact.md
- .cursor/agents/gsd-doc-synthesizer.md
- .cursor/agents/gsd-doc-verifier.compact.md
- .cursor/agents/gsd-doc-verifier.md
- .cursor/agents/gsd-doc-writer.compact.md
- .cursor/agents/gsd-doc-writer.md
- .cursor/agents/gsd-dom-verifier.compact.md
- .cursor/agents/gsd-dom-verifier.md
- .cursor/agents/gsd-domain-researcher.compact.md
- .cursor/agents/gsd-domain-researcher.md
- .cursor/agents/gsd-eval-auditor.compact.md
- .cursor/agents/gsd-eval-auditor.md
- .cursor/agents/gsd-eval-planner.compact.md
- .cursor/agents/gsd-eval-planner.md
- .cursor/agents/gsd-executor.md
- .cursor/agents/gsd-framework-selector.compact.md
- .cursor/agents/gsd-framework-selector.md
- .cursor/agents/gsd-integration-checker.compact.md
- .cursor/agents/gsd-integration-checker.md
- .cursor/agents/gsd-intel-updater.compact.md
- .cursor/agents/gsd-intel-updater.md
- .cursor/agents/gsd-mempalace-curator.compact.md
- .cursor/agents/gsd-mempalace-curator.md
- .cursor/agents/gsd-nyquist-auditor.compact.md
- .cursor/agents/gsd-nyquist-auditor.md
- .cursor/agents/gsd-pattern-mapper.compact.md
- .cursor/agents/gsd-pattern-mapper.md
- .cursor/agents/gsd-phase-researcher.md
- .cursor/agents/gsd-plan-checker.md
- .cursor/agents/gsd-planner.md
- .cursor/agents/gsd-project-researcher.compact.md
- .cursor/agents/gsd-project-researcher.md
- .cursor/agents/gsd-research-synthesizer.compact.md
- .cursor/agents/gsd-research-synthesizer.md
- .cursor/agents/gsd-roadmapper.compact.md
- .cursor/agents/gsd-roadmapper.md
- .cursor/agents/gsd-security-auditor.compact.md
- .cursor/agents/gsd-security-auditor.md
- .cursor/agents/gsd-ui-auditor.compact.md
- .cursor/agents/gsd-ui-auditor.md
- .cursor/agents/gsd-ui-checker.compact.md
- .cursor/agents/gsd-ui-checker.md
- .cursor/agents/gsd-ui-researcher.compact.md
- .cursor/agents/gsd-ui-researcher.md
- .cursor/agents/gsd-user-profiler.compact.md
- .cursor/agents/gsd-user-profiler.md
- .cursor/agents/gsd-verifier.md
- .cursor/gsd-core/
- .cursor/gsd-file-manifest.json
- .cursor/gsd-install-state.json
- .cursor/hooks.json
- .cursor/hooks/
- .cursor/scripts/
- .cursor/skills/gsd-add-tests
- .cursor/skills/gsd-ai-integration-phase
- .cursor/skills/gsd-audit-fix
- .cursor/skills/gsd-audit-milestone
- .cursor/skills/gsd-audit-uat
- .cursor/skills/gsd-autonomous
- .cursor/skills/gsd-capture
- .cursor/skills/gsd-cleanup
- .cursor/skills/gsd-code-review
- .cursor/skills/gsd-complete-milestone
- .cursor/skills/gsd-config
- .cursor/skills/gsd-debug
- .cursor/skills/gsd-docs-update
- .cursor/skills/gsd-eval-review
- .cursor/skills/gsd-execute-phase
- .cursor/skills/gsd-explore
- .cursor/skills/gsd-extract-learnings
- .cursor/skills/gsd-fast
- .cursor/skills/gsd-forensics
- .cursor/skills/gsd-graphify
- .cursor/skills/gsd-health
- .cursor/skills/gsd-help
- .cursor/skills/gsd-import
- .cursor/skills/gsd-inbox
- .cursor/skills/gsd-manager
- .cursor/skills/gsd-map-codebase
- .cursor/skills/gsd-mempalace-capture
- .cursor/skills/gsd-mempalace-recall
- .cursor/skills/gsd-milestone-summary
- .cursor/skills/gsd-mvp-phase
- .cursor/skills/gsd-new-milestone
- .cursor/skills/gsd-new-project
- .cursor/skills/gsd-next
- .cursor/skills/gsd-ns-context
- .cursor/skills/gsd-ns-ideate
- .cursor/skills/gsd-ns-manage
- .cursor/skills/gsd-ns-project
- .cursor/skills/gsd-ns-review
- .cursor/skills/gsd-ns-workflow
- .cursor/skills/gsd-onboard
- .cursor/skills/gsd-pause-work
- .cursor/skills/gsd-phase
- .cursor/skills/gsd-plan-phase
- .cursor/skills/gsd-plan-review-convergence
- .cursor/skills/gsd-pr-branch
- .cursor/skills/gsd-profile-user
- .cursor/skills/gsd-quick
- .cursor/skills/gsd-quick-batch
- .cursor/skills/gsd-resume-work
- .cursor/skills/gsd-review
- .cursor/skills/gsd-review-backlog
- .cursor/skills/gsd-secure-phase
- .cursor/skills/gsd-settings
- .cursor/skills/gsd-ship
- .cursor/skills/gsd-sketch
- .cursor/skills/gsd-spec-phase
- .cursor/skills/gsd-spike
- .cursor/skills/gsd-stats
- .cursor/skills/gsd-surface
- .cursor/skills/gsd-thread
- .cursor/skills/gsd-ui-phase
- .cursor/skills/gsd-ui-review
- .cursor/skills/gsd-ultraplan-phase
- .cursor/skills/gsd-undo
- .cursor/skills/gsd-update
- .cursor/skills/gsd-validate-phase
- .cursor/skills/gsd-verify-work
- .cursor/skills/gsd-workspace
- .cursor/skills/gsd-workstreams
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

## Chain note
gsd-core 1.17.0's cursor installer bakes no `model:` line. The verified chain is plan -> project-local resolve-model only. Whether cursor-side GSD workflows pass that result into a Task call is unverified; this evidence does not imply planned models take effect inside cursor agents.

## Runner note
The runner's `resolveBin` scans every PATH entry for a guarded `agent` since 21-07, template 5, matching 21-01's Python resolver. This dispatch found the `cursor-agent` PATH hit directly, so it did not exercise the guarded scan; hermetic self-test case `agent-grok-first-then-cursor` covers it.

## Process proof
- `cursor-run1.pgid` recorded 12 spawn pids; every recorded process group is empty after finalization. There were no probe pgid files. The selected attempt's `spawn` record was present.
- Runner `finalize` attempts SIGTERM then SIGKILL on each child process group on every exit path, including normal exit. Any worker-server survivor would therefore be outside that group; none with HOME equal to `<scratch-home>` remained.
- `ps-before.txt` and `ps-after.txt` include the executor's pre-existing session processes; no cursor-agent or worker-server process with scratch HOME remained after dispatch. `ps-final.txt` is the final read-only listing.
- `escaped workers: none` (final environ scan over matching cursor-agent/worker-server processes).
- Login symlink intact: yes.
- `scratch home removed: yes` (normal teardown after dispatch, before scans; the anchored `/tmp` path guard passed and `test ! -e` passed).

## Artifacts kept
Eight files remain under `tmp/p21/headless/cursor-artifacts/`: project-a/{plan.json,config.json,resolve-model.json,baked.json} and project-b/{plan.json,config.json,resolve-model.json,baked.json}. `project-a/resolve-model.json` contains 35 agent records. Artifacts are uncommitted under gitignored tmp.

## run-smoke.sh (paths redacted)
```bash
#!/usr/bin/env bash
set -u
env | cut -d= -f1 | grep -E "^(CODEX|OPENCODE|AI_AGENT|AGENT|CLAUDE|PI_|CURSOR_|GROK_)" | sort > tmp/p21/headless/cursor-env-names.txt
export HOME=<home> XDG_CONFIG_HOME=<home>/.config CURSOR_CONFIG_DIR=<home>/.cursor TMPDIR=/tmp
unset XDG_CACHE_HOME
unset XDG_STATE_HOME
python3 tests/gsd_curated_eval.py smoke --evidence-out tmp/p21/headless/cursor-smoke.md --artifacts-out tmp/p21/headless/cursor-artifacts > tmp/p21/headless/cursor-smoke.log 2>&1
rc=$?
echo "smoke exit=$rc" >> tmp/p21/headless/cursor-smoke.log
exit "$rc"
```

## Label
branch (A) — `_LABEL_CURSOR` upgraded to live-verified (Phase 21) (headless; TUI confirmation pending
`21-INTERACTIVE-CURSOR.md` step 2), because `CURSOR_AGENT` was in the names-only list and
`signals.txt` reads `signals clean`. The docstring bullet carries the same wording and
`test_cursor_label_is_live_verified_headless` pins it. Commit: `feat(21-04): cursor env signal
live-verified from the headless cursor session` (this commit; sha: `git log --format=%h -1 --grep 'feat(21-04)'`).

## Interactive run
pending: `21-INTERACTIVE-CURSOR.md`; the user's TUI env names, smoke and artifacts are the SPEC R1 acceptance evidence.
