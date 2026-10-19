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

The user's numbered script is [21-INTERACTIVE-CURSOR.md](21-INTERACTIVE-CURSOR.md). Steps 1-4
are the SPEC R1 acceptance: start cursor as `command cursor-agent --model <id>` at the checkout
root, take the fresh baseline with the names-only env list and the user-keys digest, run the
smoke with `TMPDIR=/tmp` and `--host-rewrite '<home>/.cursor/cli-config.json'` (cursor rewrites
its own config during a session, so that one strict entry is reported rather than failed, while
the three user-owned keys are compared by digest), and check the baseline with `--scratch-root`
plus the same exemption. Step 5 is ROADMAP SC5's optional per-call model probe: it reads the
Task call's `model` from the stream-json and lists any leftover `worker-server` process labelled
by an `/proc/<pid>/environ` ownership match, killing nothing. This plan writes the script and
never runs it; under SPEC R1/R3 as amended by 21-05 the run is a mandatory human-verification
item, so the phase ends `human_needed` until it is recorded.

## Label lift
- branch: LIFT (R1 headless green and R2 green, read from one identified attempt).
- R1 headless evidence, quoted verbatim from `## Headless runs` above:
  `headless verdict: green (attempt 1: status=no_change cli_rc=0, spawn recorded, smoke exit=0, steps 10/10 pass)`
- R2 evidence, quoted verbatim: `matrix ran: 420 checks` (step 9 of the smoke body) and `matrix ok (420 checks)` (21-03's `tmp/p21/matrix-cursor.txt`, last line).
- What changed, landing in this commit: `skills/ai-kit-gsd-curated-config/SKILL.md` (the combined `cursor / pi hosts` row split into a `pi hosts` row keeping `**not live-validated**` and a `cursor host` row with the qualified `validated headless ... **pending**` wording), `README.md` (skill row), and `tests/test_curated_config_apply.py` (`test_cursor_label_lifted_with_evidence_pointer`).
- The rule the lift is made under, quoted from the `21-SPEC.md` R3 amendment of this commit:
  > **Amended 2026-10-18 (review cycle 2, 21-05; Phase 20 codex precedent):** R1's acceptance remains the user's interactive cursor session (`21-INTERACTIVE-CURSOR.md`), a mandatory human-verification item. R3's "removed" is a two-step lift: passing headless evidence (R1 run headless through this repo's runner — the single `headless verdict: green` line of `21-SMOKE-CURSOR.md` — plus R2) replaces the bare `not live-validated` label with the qualified wording `validated headless ... interactive confirmation pending`, never a bare lift; the `pending` note is removed only in the commit that records the user's interactive run. Until that run is recorded the phase ends `human_needed`.

## Phase gates (plan 21-06)

- `make test`: `exit=0`, re-run on the final tree (`tmp/p21/gates/test.final.txt`; `tmp/p21/gates/test.txt`
  is the same run taken before the pyright fix landed, and both are kept because the gate has to be
  green *after* the fix, not before it). Identical numbers: 57 module `ok` lines, 4,396 tests in total,
  no `FAILED` line: unit `43/43 modules passed`, unit-uv `1/1`, integration `4/4`, e2e `8/8` plus
  `bash tests/test_install.sh` → `45 passed, 0 failed`, arch `1/1`. The matrix module reports
  `=== tests.test_ai_kit_gsd_curated_config_matrix: ok in 223.0s  Ran 36 tests` — and it is the
  only such line in the log — equal to the loader's module total
  (`tmp/p21/gates/matrix-loader.txt`: `module 36`; per class
  `TestResolveModelMatrix=9`, `TestResolveModelMatrixCodex=9`, `TestResolveModelMatrixOpencode=9`,
  `TestResolveModelMatrixCursor=9`) — checked again against `test.final.txt`, where the matrix module
  is again the single `Ran 36 tests` line. The phase's 9 per-class matrix runs therefore run once, not
  twice. This line is a fresh re-run, not a reference to the earlier plans: plan04's own `make test`
  is recorded in `21-04-SUMMARY.md` as `rc=0` (`unit 43/43, integration 4/4 and 8/8, e2e 45
  passed/0 failed, arch 1/1`), and its log `tmp/p21/plan04-make-test.log` — at the path 21-04's
  summary names, having rotated out of `tmp/p21/headless/` in 21-05's scratch reorganisation — shows
  those tiers plus 4,390 tests and exactly one
  `=== tests.test_ai_kit_gsd_curated_config_matrix: ok ... Ran 36 tests` line. So the loader-count
  equality holds for that run too, and the 6-test difference against this run is this plan's six new
  `--host-rewrite` cases.
- `make validate`: `exit=0` (`tmp/p21/gates/validate.txt`) — every hook `Passed`, no `Failed`
  line: ruff, pylint, pyright, vulture, shellcheck, py-compile, `unittest (core)`,
  `unittest (wizard — uv)`. Re-run after this section's and the SUMMARY's text was written (the
  final tree, docs uncommitted at that moment):
  `tmp/p21/gates/validate.final.txt`, `exit=0` again with all eight hooks `Passed` on a single
  attempt. The first green run took seven attempts, for two different reasons, recorded here
  because neither is dodged:
  1. attempts 1-5 stopped at `pylint ... Failed — files were modified by this hook` while pylint
     itself reported `10.00/10` with zero messages. The only file that changed during those runs
     was another session's: a `md5sum` manifest taken around one hook run shows
     `.planning/phases/21.1-*/21.1-07-PLAN.md` as the sole difference (the two manifests and the
     hook's own output are kept: `tmp/p21/gates/manifest-before-pylint.txt`,
     `tmp/p21/gates/manifest-after-pylint.txt`, `tmp/p21/gates/pylint-hook-output.txt`) — the orchestrator's Phase
     21.1 replan was rewriting its own plan files in this same worktree while pre-commit hashed
     the tree. Nothing in this phase changed during those runs, and the attempt that finally
     passed ran after those writes settled.
  2. attempt 6 cleared pylint and then failed pyright on a real defect:
     `tests/gsd_curated_eval.py` `_baked_chain` — the cursor branch
     (`promised_map = {agent: None for agent in agents}`) inferred `dict[str, None]`, which pyright
     rejects as `dict[str, str | None]` because `dict` is invariant in its value type. Verified
     pre-existing: the same error reproduces at `HEAD~1` before this plan touched the file (21-03
     introduced the branch; no `make validate` run is recorded between 21-03 and this plan). Fixed in-phase as
     commit `a3fab6d` by annotating `promised_map: dict[str, str | None]` once above the branch —
     one dev-harness module, no product module, so no decimal phase (R8); the check that catches it
     is pyright itself, in the gate log above and in every future `make validate`.
- `python3 -m unittest tests.test_gate_scope`: `Ran 34 tests ... OK` — this plan added no test
  module (the new cases live in `tests/test_gsd_curated_eval.py`, already registered), so no group
  registration changed and the rule that enforces it still passes.
- `make e2e-docker`: `exit=0` (`tmp/p21/gates/docker.txt`) — run because `SKILL.md` changed in this
  phase (the container builds from the current tree, so it validated 21-05's wording too); engine
  `podman`; the container's own matrix smoke reported `matrix ran: 420 checks`; `protected set
  unchanged`; `e2e ok`; final line `==> ai-kit clean-room E2E: PASS`.
- skill-judge: **gate not passed — `UNRESOLVED (owner review)`**. The verifier accepts only
  `PASS`/`GREEN`/`APPROVED`/`MERGED`, so its recorded result is `exit=1`, and Phase 21 cannot be
  marked complete: the in-session row `CURRENT 110/120` meets its floor (109, Phase 20's in-session
  final), with 0 Critical and 0 Important. The independent row — `pi` / `openai/gpt-6.1-sol:xhigh`,
  12 turns, 22 files — reports `CURRENT 114/120` with 0 Critical and 0 Important, which is **below
  the 116 floor this lane inherits from Phase 20's final** (`20-SKILL-JUDGE.md`: in-session 109/120,
  pi 116/120, "the floors for this phase" per 21-05-PLAN.md). Staleness is not the issue: both
  reports' `DIGEST` line is `85da5a6682d937c5`, equal to the current
  `python3 tests/gsd_curated_eval.py digest` (`tmp/p21/gates/digest-now.txt`), so both judges
  scored exactly the skill 21-05 amended.
  This plan's own rule is unforgiving about that state — "`UNRESOLVED` fails the gate outright (a
  defect to fix in SKILL.md by the 21-05 fix loop, then the judge re-run), as does a pending marker"
  — so the remedy it prescribes is: edit `skills/ai-kit-gsd-curated-config/SKILL.md` against
  `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md` §Findings (its four Minor items:
  the lines 303-305 repetitions of 179-182 / 136-144 / 159-164, the runner-readiness duplication
  across layers, the repeated initial questions, and the unquoted target path in the runner
  verification step) and its §Top 3 improvements, then re-key
  `python3 tests/gsd_curated_eval.py digest` and re-run **both** judges on the new digest —
  in-session per the `skill-judge` skill, and independently
  `node .planning/scripts/cross-ai.mjs --prefer pi --model-pi openai/gpt-6.1-sol:xhigh --mode review --effort xhigh --timeout-s 1800 --files skills/ai-kit-gsd-curated-config/SKILL.md`
  — replacing `UNRESOLVED (owner review)` in `21-SKILL-JUDGE.md` with the new round before Phase 21
  can be marked complete.
  That fix loop was **not** run here, for reasons that are evidence rather than excuse: this plan's
  own task-2 action forbids running an AI CLI (`cursor-agent`, `pi`, `codex`, `opencode`, `claude`)
  because the interactive Cursor run belongs to uz, so the pi re-judge could not be dispatched; and
  editing `SKILL.md` first would change the judged bytes, making both current reports `STALE`
  (`skill-judge: STALE (digest 85da5a6682d937c5 != <new>) — gate not passed`), which is strictly
  weaker evidence than the state now recorded — the reports are today byte-exact with the tree they
  judge. Under the same D-04/R8 rule the plan cites, work needing both judges re-run is a decimal
  phase "recorded in the SUMMARY and inserted through the orchestrator", not an executor improvisation.
  The open question for uz is whether pi's 114 is a strict-score regression (the rubric's `CURRENT`
  is the strict reading, and the floor is the project's rule rather than the judge's own
  recommendation — pi graded this report "A — production-ready", "Remaining issues are minor") or a
  variance to accept: pi has scored 114/120 on this same skill before, in Phase 19
  (`19-SKILL-JUDGE.md`: `SCORE: 109/120 (pi gpt-6.1-sol: 114/120; pi glm-5.3: unavailable)`), and
  115/120 as Phase 20's executor dispatch (with 1 Important, fixed to 116 in the final), so 114 sits
  inside this judge's historical spread — which is exactly why `21-SKILL-JUDGE.md` routes it as
  `owner decides whether that is judge variance (accept as PASS) or a regression to fix`. Either way
  the recorded gate state stays **not passed** and Phase 21 stays `human_needed`.
- `21-SKILL-JUDGE.md` precondition (`no pending (orchestrator) marker`): satisfied in substance —
  the orchestrator replaced 21-05's hand-off marker with a real in-session report
  (`skill-judge/in-session.md`: `CURRENT 110/120`, `CRITICAL 0`, `IMPORTANT 0`,
  `DIGEST 85da5a6682d937c5`), so Task 2's gate work could start on a complete hand-off. The literal
  grep still matches one line, `21-SKILL-JUDGE.md:39`, which is narrative prose *quoting the rule*
  ("21-06 Task 2's precondition refuses any `pending (orchestrator)` marker in this file") rather
  than a marker: no score row is pending, and the in-session row is the orchestrator's to own.
  `21-SKILL-JUDGE.md` is the judges' artifact, so it was not edited to make a grep go quiet — the
  distinction is recorded here instead.
- Consequence for this plan's `<verify><automated>` block, stated plainly. The block was extracted
  verbatim into `tmp/p21/gates/verify-task2.sh` and traced (`tmp/p21/gates/verify-trace.txt`): it
  aborts at `! grep -rq 'pending (orchestrator)' …` — see the precondition line above — and behind
  that, its skill-judge clause accepts only `PASS` + a `STALE` line with a digest mismatch, or
  `BLOCKED: pi judge unavailable` + the `gate not passed` line; the verdict here is neither, so the
  command cannot exit 0 in this state. The three ways to force it were all rejected on purpose: write
  `## Verdict: BLOCKED: pi judge unavailable` (false — the pi judge ran, three rounds), write
  `skill-judge: PASS` (false — 114 < 116), or edit `SKILL.md` to re-key the digest without being able
  to re-judge (would void the two byte-exact reports). Removing exactly those two judge clauses
  (`tmp/p21/gates/verify-task2-rest.sh`, trace `verify-trace-rest.txt`) lets the chain run all the way
  to its final clause and stop only there: `test -z "$(git status --porcelain)"`. Re-run after this
  plan's `docs(21-06)` commit, that clause is the only remaining failure, and what it lists is other
  sessions' work — the two untracked `.planning/phases/21.2-*/21.2-RESEARCH.md` and
  `21.3-*/21.3-RESEARCH.md` (the `21.1-*` files that raced the validate attempts were committed by
  that session as `41193a4` and `6b65a9d` while this plan ran). Nothing this plan owns is uncommitted:
  `c4dba7f`, `a3fab6d` and the docs commit are the full set. With that clause removed too
  (`tmp/p21/gates/verify-task2-rest-notree.sh`) the chain exits `0`, so every other clause — test
  counts, loader equality, `validate`, `gate_scope`, docker, `snapshot ok`, secret scan, the `$HOME`
  grep, the pgid/leak/scratch-home proofs, `## Phase gates`, and the SUMMARY's
  `phase status: human_needed` + `21-INTERACTIVE-CURSOR.md` mentions — is verified green here rather
  than hidden behind a short-circuit.
- `python3 tests/gsd_curated_eval.py snapshot --check tmp/p21/plan06.before.json` → `snapshot ok`
  (`tmp/p21/gates/snapshot-plan06.txt`); the line is printed only when no strict entry failed, so it
  is the exit-0 proof itself. No `--host-rewrite` exemption was needed or used for it: the flag only
  applies when a host rewrite lands on `~/.cursor/cli-config.json` mid-run, and this plan's
  protected set never changed. Older baselines, information only: `--check tmp/p21/plan04.before.json`
  → `snapshot ok` and `--check tmp/p21/plan05.before.json` → `snapshot ok` — so nothing wrote to
  `~/.cursor/cli-config.json` (or any other protected path) during 21-04, 21-05 or 21-06.
- Secret scan / leak: `python3 tests/gsd_curated_eval.py secret-scan
  .planning/phases/21-cursor-live-validation` → `exit=0` (no finding; the command's own output
  names only paths), and `grep -rF -l -- "$HOME" .planning/phases/21-cursor-live-validation` →
  `exit=1`, no path printed: this plan's artifacts carry no machine-specific home path, no digest
  value and no credential content.
- Leak check: `bash tmp/p21/gates/leak-check.sh tmp/p21/gates/ps-final.txt` — the pattern list
  (`cursor-agent`, `worker-server`, `cross-ai`, `gsd_curated_eval`, each in the `[c]`-bracket form so
  the checking shell's own argv cannot match it) lives in a file rather than in the command line,
  because a first attempt run inline reported a second "new" line that was the checker itself
  (`etimes=0`). Run clean, it returns one line, and that line is also present in 21-04's
  pre-dispatch capture `tmp/p21/headless/ps-before.txt` — a two-day-old shell whose own command
  string merely mentions those binaries. Nothing this phase dispatched remains: the run wrapper, its
  `cross-ai.mjs` child, every `node -e while` idle probe and every `worker-server` 21-04's dispatch
  left are gone. All twelve `spawn <pid>` entries in `tmp/p21/headless/cursor-run1.pgid` report an
  empty process group, and no `cursor-probe*.pgid` file exists because no probe was dispatched.
  `gc-late`/`node -e while` strays: none, so the standing cleanup rule had nothing to remove.
- Scratch home: `scratch home removed: yes` — the path recorded in
  `tmp/p21/headless/scratch-home.txt` (`<scratch-home>`) no longer exists, and no
  `/tmp/p21-cursor-home.*` directory exists at all. 21-04's own teardown ran before this plan, so
  this plan never ran the D-19 late-teardown clause (recorded below). The `auth.json` symlink
  pointing at the user's real login was removed with the scratch home; it was never read, listed or
  hashed — only `test -L`/`test ! -e`.
