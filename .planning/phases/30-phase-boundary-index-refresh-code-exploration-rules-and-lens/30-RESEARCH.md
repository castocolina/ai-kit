# Phase 30: Phase-boundary index refresh, code-exploration rules and lens wiring - Research

**Researched:** 2026-11-05
**Domain:** unit-flow engine extension (Python stdlib), GSD capability hooks, agent-skills wiring, git hooks, setup/doctor
**Confidence:** HIGH on repo facts (read this session), MEDIUM on GSD dispatch behavior (read from workflow prose, not executed), LOW on third-party install commands

<user_constraints>
## User Constraints (from CONTEXT.md)

Full text: `30-CONTEXT.md` (locked; never re-discuss). Lead lines, verbatim:

### Locked Decisions
- **D-01:** The boundary step is a `boundary` command in the unit-flow engine (Phase 29.1 D-02). `start` calls it; GSD's hooks call the same command; it moves into `ai-kit-project-rules` with the engine in Phase 45.
- **D-02:** GSD triggers it through two more step hooks, `plan:pre` and wave 1's `execute:wave:pre`, in the ai-kit GSD extension the Phase 29 D-02 spike proves. If a hook form cannot run it, planning returns to the owner (the Phase 29 D-02 rule).
- **D-03:** Indexing is resilient: three triggers, none the only one (post-checkout stage hook via detached job; `start` and every boundary point init/sync a missing or stale `.codegraph/`; the tool-use rule tells any agent to run `codegraph init -y` or `codegraph sync`).
- **D-04:** `make setup-dev` installs the flow's missing tools through guarded steps (codegraph, graphify, pre-commit, gh, gh-stack); installed tool left alone; failed install reported with manual command, target exits 0; `dev` and `setup-env` keep working.
- **D-05:** The Phase 49 session-hooks todo is not folded; a dated note says Phase 30 now indexes automatically.
- **D-06:** The brief lives in a gitignored `.aikit/brief/` folder per checkout, written atomically by the engine, copied into each new worktree by the worktree job.
- **D-07:** The brief reaches the agents through GSD's agent-skills mechanism (project-relative entry for `gsd-phase-researcher`, `gsd-planner`, `gsd-executor`, set through gsd-tools; the folder always holds a file; the superpowers adapter adds the path to the plan writer's and every implementer's brief).
- **D-08:** The brief names the range and the changed files and tells each agent to run `codegraph_explore`; no reading of codegraph's database, no symbol differ; documents come from `codegraph explore` names plus file names, searched in tracked documents outside `.planning/` (whole-word, capped at 10 per name).
- **D-09:** The tool advisor shows the codegraph rule on code searches (shell rg/grep/find over non-Markdown paths and Claude's built-in Grep and Glob) in a checkout with `.codegraph/`; the Claude hook matcher widens from `Bash|Read` to include `Grep|Glob` through setup's existing writers.
- **D-10:** A tracked lens-brief entry follows each lens in agent-skills; carries the design rule (or points to AGENTS.md's), lists each agent's expected lenses, says to continue without, and name, any lens that did not load; a drift check compares its list with `.planning/config.json` through `make check-dogfood`.
- **D-11:** The global-sentence rewrite (R11) runs headless with a new `--with-global-rules` flag and in the wizard as a pre-checked Review item showing each file's diff. Bare `--headless` still touches nothing.
- **D-12:** One `graphify update .` build feeds both locations (`update` rejects `--graph`).
- **D-13:** R07 and R08 keep ids and criticality; both summaries cut from the one rule text; a test pins that they match.
- **D-14:** SKILL.md files under the judge bar: `ai-kit-commit-fold`, `ai-kit-spec-execute-superpowers`; `ai-kit-project-rules-agents` only if its SKILL.md text changes.
- **D-15:** Tests fake `codegraph` and `graphify` through the shared fake helper, recording argv and returning canned `status --json`; worktree tests use temporary repos with ai-kit's hook installed; R11 tests use synthetic global files in a scratch HOME.
- **D-16:** GSD vs non-GSD: detection reuses `detect_framework.py`'s `.planning/PROJECT.md` marker plus `.planning/config.json` or a resolvable project gsd-tools; non-GSD keeps `graphify-out/` only and never gets `.planning/`; GSD gets the copy and status file in `.planning/graphs/` only with `graphify.enabled`; gitignore `graphify-out/` always, `.planning/graphs/` only in a GSD project; fixture test per kind.

### Claude's Discretion
Command, module and file names (brief file inside `.aikit/brief/`, lens-brief tracked path, job lock name); brief layout; advisor wording within the rule text; guarded install command per tool and platform (nothing needs sudo silently; each failure names its manual step).

### Deferred Ideas (OUT OF SCOPE)
Generated top rules (45.1), Makefile rules/alias decision (46), worktree-created playbook (47), curated-config lens proposal (44), session-hook indexing advice (49), jev marker block itself (54), editing GSD's installed hook scripts, the binary's "no index" message, `.claude/cli-environment.md`, LLM-backed graphify.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FLOW-04 | boundary step at start / plan:pre / wave-1 pre, codegraph + graphify refresh, brief (SPEC R1-R5) | Sections U1, U2, U9; Plans 01-03 |
| FLOW-06 | new worktree indexed in ai-kit without blocking git (R6) | U8 (post-checkout verified live); Plan 06 |
| FLOW-12 | setup rewrites codegraph sentence in four global files (R11) | U6; Plan 05 |
| FLOW-13 | `make setup-dev` guarded tool installs (R12) | U8; Plan 06 |
| DESIGN-01 | AGENTS.md design rule + lens briefing (R10) | U3, U7; Plans 03, 04 |
| LENS-01 | lens skills wired through gsd-tools (R9) | U3; Plan 03 |
(R7 rule/advisor/R07-R08 and R8 runbook ride FLOW-04/LENS-01 anchors; Plan 04.)
</phase_requirements>

## Summary

Seven findings change plans. (1) **GSD's `plan:pre` has no command arm**: `plan-phase.md` dispatches only `ref.skill` and `ref.agent` at that point; `ref.command` is honored at `discuss:pre` and `execute:wave:pre` (and verify/ship/execute:post) through `loop-hook-dispatch.md`. The capability validator accepts a `ref.command` at any point, so a `plan:pre` command step would be declared but never run. A capability cannot ship its own skill or agent (`skills`/`agents` arrays only name ones already installed), so D-02's "if a hook form cannot run it, planning returns to the owner" applies to `plan:pre`. (2) `execute:wave:pre` runs `gsd_run ${ref.command} --phase N --raw` and exposes **no wave number**; wave-1-only must be decided inside the command. (3) `tools/check_dogfood.py` currently **asserts `plan:pre` and `execute:wave:pre` hold no ai-kit entry** (`FLOW_EMPTY_POINTS`), so Plan 03 must change it and its tests. (4) A project-relative agent-skills entry needs a `SKILL.md` inside the folder; `.aikit/brief/SKILL.md` can be the brief file itself. (5) `built_at_commit` in `gsd-tools graphify status` comes from `graph.json`'s own field (graphify writes it), not from the status file. (6) `Makefile` and `.pre-commit-config.yaml` carry generated test-group blocks, so every new `tests/test_*.py` edits both shared files (plans cannot run in parallel on them). (7) gsd-core installed here is **1.20.0** (SPEC said 1.18.0); the runbook must name the version it read.

**Primary recommendation:** Build the engine bottom-up (index step, then `boundary`+brief, then adapters), keep rules/docs and setup/R11 as independent plans, and put the `plan:pre` question to the owner at plan time with a recommended fallback (below, O1).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary | Rationale |
|------------|-------------|-----------|-----------|
| Index refresh + brief | unit-flow engine (`skills/ai-kit-commit-fold/scripts`) | GSD cjs router, superpowers adapter prose | D-01: one command, adapters only call it |
| Worktree indexing | git `post-checkout` via pre-commit | engine detached job | fires on `git worktree add` (verified U8) |
| Brief delivery | GSD `agent_skills` config | superpowers SKILL prose | D-07 |
| Rule text | AGENTS.md + `rules.py` + advisor | doc-contract tests | one text, three short forms |
| Global-file rewrite | `tools/` setup + doctor | shared marked-block helper | only writer of real-HOME files (prohibition) |

## Standard Stack

Stdlib-only Python 3 (system python3 is 3.14.7 here; ruff target py312) for everything runtime. Node built-ins only in `ai-kit-fold.cjs`. Test framework: `unittest` via `tools/run_unittest_parallel.py`. No new third-party dependency in code.

External tools the flow needs (setup-dev, installed only when missing):

| Tool | Local version | Install form known | Tag |
|------|---------------|--------------------|-----|
| pre-commit | 4.6.2 (`uv tool`) | `uv tool install pre-commit` | [VERIFIED: `uv tool list`] |
| graphify | 0.9.54 (`uv tool`, package `graphifyy`) | `uv tool install graphifyy` | [VERIFIED: `uv tool list`] |
| gh | at `~/.local/opt/gh` | release tarball; no confirmed portable one-liner (Fedora atomic has no dnf) | [ASSUMED] |
| gh-stack | v0.3.0 | `gh extension install github/gh-stack` | [VERIFIED: `gh extension list`] install verb [ASSUMED] |
| codegraph | 1.6.2 under `~/.codegraph/versions` | upstream installer; WebSearch gave only third-party forks (`npx @colbymchenry/codegraph`, curl script); `npm` is banned on this machine | [ASSUMED] |

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| graphifyy | PyPI | latest release 2026-11-03 | unknown | graphify.com | SUS (too-new, unknown-downloads) | Flagged; already installed on the owner machine; setup-dev installs only when missing, so planner adds a `checkpoint:human-verify` before the install step is first wired |
| pre-commit | PyPI | latest release 2026-10-12 | unknown | github.com/pre-commit/pre-commit | SUS (same seam reasons: release recency, no download data) | Flagged, same handling; long-established project, installed locally |

`gsd-tools query package-legitimacy check` run this session. Seam SUS reflects recency of the latest release, not a new project. codegraph, gh, gh-stack are not registry packages here: tagged [ASSUMED] installers.

## Unknown-by-unknown answers

### U1. Unit-flow engine (Phase 29.1)
- Location: `skills/ai-kit-commit-fold/scripts/`: `fold.py` (CLI), `flow_unit.py` (start/guard/checkpoint/ready/show), `flow_record.py` (record, settings, atomic JSON), `flow_git.py`, `flow_stack.py`, `flow_merge.py`, `flow_pr.py`, `fold_adapters.py` (GSD/superpowers unit resolution).
- Dispatch table, verbatim from `fold.py`: `_FLOW_HANDLERS = {"start": ("flow_unit", "cmd_start"), ... "merge-chain": ("flow_merge", "cmd_merge_chain")}` and `_UNIT_COMMANDS = ("start", "guard", "checkpoint", "ready", "show")`. A missing module/function fails closed with exit 2. **A new `boundary` slots in as `"boundary": ("flow_boundary", "cmd_boundary")` plus an entry in `_UNIT_COMMANDS`** (so `_attach` resolves `args.unit`, `args.phase`/`--plan` selectors and `args.plan_paths`), with a `--point start|plan|wave` option added in `_add_flow_parsers`. A worktree-hook command that has no unit (`fold.py index ...`) goes in `_FLOW_HANDLERS` only, not `_UNIT_COMMANDS`.
- CLI of start: `fold.py start (--unit FILE|- | --phase N | --plan FILE | --unit-id ID) [--repo DIR]`. `_start` in `flow_unit.py` appends a unit dict then `write_record`; the call to the boundary step goes at its return paths (new unit, `reuses unit`, `joins hotfix`).
- Stack record: `ai-kit-stack.json` in the git common directory (`RECORD_NAME`, `record_path(repo)`); `read_record` returns `{"schema": 1, "units": [...]}`. Entry keys, verbatim from `_start`: `"id", "kind", "target", "branch", "parent", "parent_tip", "pr", "state", "mvp", "pushed", "pending", "tags", "title", "goal", "checkpoints", "carried"`. States: `open`, `finished`, `ready`, `merged` (unit-contract.md).
- **Previous unit:** the entry immediately before this one in `record["units"]` (stack order); this unit's `parent` equals that unit's `branch` while unmerged. When it has merged, the latest entry with `state == "merged"` below it. Commit range of the previous unit: `<prev.parent_tip>..refs/heads/<prev.branch>` (if the branch is gone after merge, use `prev.pushed`/merged sha; verify in plan; this is the one range edge I did not exercise). `fold_adapters._fold_base`/`flow_git.rev`/`flow_git.run_git` are the reusable helpers. First unit on trunk: no entry below, so "no previous unit" brief.
- `.aikit/` layout: `<main worktree>/.aikit/flow.json` (settings, `SETTINGS_REL = Path(".aikit") / "flow.json"`, refused with `settings_not_ignored` unless git ignores it). `.aikit/` is in ai-kit's `.gitignore`. For other projects `_ensure_ignored` adds `.aikit/` to `.git/info/exclude` only under `consent grant --add-exclude`. **The brief is per checkout** (`<toplevel>/.aikit/brief/`), not main worktree. The plan must `git check-ignore` the brief path and use the same exclude fallback; also use `.git/info/exclude` (common dir `info/exclude`, shared by worktrees, never tracked) for `graphify-out/` and `.planning/graphs/` so the "no index output committed" prohibition holds in target projects [ASSUMED design, discretion].
- Atomic write: copy `flow_record._atomic_write_json` shape (mkstemp in same dir + `os.replace`); it is JSON-only, so the brief (text) needs a small text twin in the new module (skills stay self-contained: the file comment says it was copied from `tools/setup.py`).
- Lock under `.git/`: reuse `flow_record.common_dir(repo)`; add `ai-kit-boundary.lock` (flock) there (SPEC concurrency row).
- Superpowers adapter: `skills/ai-kit-spec-execute-superpowers/`. It is **prose plus a thin CLI** (`ai_kit_spec_superpowers/cli.py`, `dispatch_injection.py`), not code that builds briefs. `references/start-step.md` holds the Bash block running `python3 "$FOLD_PY" start --plan "$PLAN_FILE" --repo "$CWD"`. Implementer briefs: the `task-N-brief.md` is written by superpowers' own `scripts/task-brief`; the adapter then composes `$PROMPT_FILE` per `references/dispatch-external-cli.md` "Compose" (one `<objective>` block + `<files>` block). **D-07 edit points (prose only):** `start-step.md` also runs `fold.py boundary --plan ... --point start`; SKILL.md Step 1 runs `--point plan` before the plan is written (plan writing happens in superpowers' own skills before Step 1, so "before its plan is written" cannot be hooked by ai-kit: use the start run and tell the plan writer to read `.aikit/brief/`) and `--point wave` before the first task; `dispatch-external-cli.md` "Compose" adds one line to the `<objective>` naming `.aikit/brief/SKILL.md` and "none found" text; the native-dispatch path in SKILL.md Step 3 gets the same line.

### U2. The GSD extension (Phase 29 D-02 spike result, read this session)
- Manifest: `skills/ai-kit-commit-fold/gsd/ai-kit-commit-fold/capability.json` (tracked) with `ai-kit-fold.cjs`. Installed per checkout by `node .claude/gsd-core/bin/gsd-tools.cjs capability install ./<path> --scope project [--yes]`; the installed mirror is `.gsd/capabilities/` and `.gsd-capabilities.json`, **both gitignored** (`.gitignore` lines `.gsd/` and `.gsd-capabilities.json`), so each checkout and worktree must install it itself (the worktree `wt-30` has no `.gsd/` now). Current steps, verbatim: `{"point": "discuss:pre", "ref": {"command": "ai-kit-fold start"}, ...}` and `{"point": "execute:wave:post", "ref": {"command": "ai-kit-fold checkpoint"}, ...}`, `"onError": "skip"`; gate `ship:pre` `ai-kit-fold ship`.
- Step command contract: `ref.command` must match `^[a-z][a-z0-9-]*( [a-z][a-z0-9-]*)*$` and is run as `gsd_run ${ref.command} --phase "${PHASE_NUMBER}" --raw` [CITED: `.claude/gsd-core/references/loop-hook-dispatch.md`]. `ai-kit-fold.cjs` `parse(args)` accepts `<family> <verb> --phase N [--raw]`, `VERBS = { run: 'gsd', start: 'start', guard: 'guard', checkpoint: 'checkpoint', ready: 'ready' }`. New verbs `boundary-plan`/`boundary-wave` map to `fold.py boundary --phase N --point plan|wave --repo <cwd>`. Dash words fit the regex, a flag cannot be part of the command string.
- **`execute:wave:pre`**: `execute-phase.md` step 2.75: `WAVE_PRE_HOOKS_JSON=$(gsd_run loop render-hooks execute:wave:pre --raw)` then "Step dispatch: `kind == "step"` per loop-hook-dispatch.md; never blocks". `ref.command` is honored. The command receives only `--phase N --raw`: **no wave number**. Wave-1-only rule must live in the engine: run when the phase has no finished-plan evidence of a completed wave 1. Recommended: parse each PLAN.md frontmatter `wave:` and skip when every wave-1 plan has a SUMMARY.md (so an interrupted wave 1 reruns, SPEC boundary row), via `fold_adapters.gsd_plans(repo, phase)` (state `finished` = SUMMARY present) plus a small frontmatter read, or `gsd-tools phase-plan-index`. Verify the frontmatter key name against a real PLAN.md during planning (not checked here).
- **`plan:pre`**: `plan-phase.md` lines 504-515, "Generic step hook dispatch contract: For each active entry where kind == step: If `ref.skill` is set, dispatch with `Skill(skill="gsd-${ref.skill}", ...)`. If `ref.agent` is set, dispatch with `Agent(... subagent_type=ref.agent ...)`." No command arm. The adapter guide already records "GSD's `plan:pre` point has no command arm, only skill and agent arms, so a step cannot run there" (`references/adapter-guide.md`). The validator (`capability-validator.cjs` `validateStep`) requires `ref.skill`/`ref.agent` names to be in the capability's own `skills`/`agents` arrays, and capability install does not ship those files (`capability-loader.cjs` only reads the arrays). **Conclusion: no deterministic shell-capable hook form exists at `plan:pre`.** A skill/agent step is prose-dispatched and best-effort, and needs a pre-existing `gsd-<stem>` skill or agent on disk.
  - Recommended fallback for the owner (O1): (a) keep the real command steps at `discuss:pre` (already runs `start`; add boundary there), `execute:wave:pre` (boundary-wave) and `execute:wave:post`; (b) cover the planning boundary by a numbered orchestrator instruction in `ai-kit-commit-fold/SKILL.md` (the existing pattern: "GSD dispatches no flow command at three points, so run these yourself", e.g. `gsd-tools ai-kit-fold boundary-plan --phase N` before plan-phase), plus (c) the tool-use rule and the brief's own HEAD/unit stamp telling the researcher the brief is stale. A cheap Wave-0 spike in a scratch GSD project (install capability with a `plan:pre` command step, render hooks, run plan-phase dry) can confirm (1) before the owner decides.
- Existing `check_dogfood.py` constants to change: `FLOW_EXPECT` (add `"execute:wave:pre": ("step", "ai-kit-fold boundary-wave")`, and the plan-pre outcome of O1) and `FLOW_EMPTY_POINTS = ("plan:pre", "execute:wave:pre", "verify:post")` (remove the points now used). Tests: `tests/test_check_dogfood.py` (line ~279 hook map, line ~339 "entry at plan:pre" negative case) and `tests/test_ai_kit_commit_fold_e2e.py` (lines ~276-296 assert both points empty) must change in the same plan. [VERIFIED: tools/check_dogfood.py:240-248, tests grep]

### U3. agent-skills (`.claude/gsd-core/bin/lib/init.cjs`, `buildAgentSkillsBlock`, lines 3826-3953)
- Project-relative entry `skills/jev-fast-decision` renders as `- @skills/jev-fast-decision/SKILL.md`. It **requires `<entry>/SKILL.md` to exist** (`existsSync`), else warns "Skill not found at ... — skipping" and the block can end empty (`configured_unresolved`). Only existence is checked (no front-matter parse). The path must be confined to the project root (`tryWithinRoot`). **A gitignored `.aikit/brief` works**: verified in a scratch project, `agent_skills.gsd-planner = ["global:ponytail:ponytail","skills/x",".aikit/brief"]` rendered `- @.aikit/brief/SKILL.md`. So the brief file is `.aikit/brief/SKILL.md` (always written by `start`/boundary/worktree job; content "no brief" when none; a fresh clone before any run warns and skips silently, hence the tracked lens-brief reminder and the rule's "run codegraph first" text).
- Order = array order. SPEC wants lens first, brief text after. Because `config-set` replaces a whole array, **every set must include the existing `skills/jev-fast-decision` entry** (all 32 agents have exactly that today; `workflow` has no `ui_review`; `agent_skills_security` absent).
- `global:` forms: bare `global:impeccable` resolves to `<runtime skills base>/impeccable/SKILL.md`; a symlink out of the base needs `agent_skills_security.trusted_global_roots`. Namespaced `global:ponytail:ponytail` (regex `^[A-Za-z0-9_-]+(:[A-Za-z0-9_-]+)*$`) is emitted as `- Load the `ponytail:ponytail` skill via the Skill tool before proceeding (plugin-provided).` on runtime `claude` only (other runtimes: warning, skipped), **no existence check**. `trusted_global_roots` expands a literal `~` and `~/` (`security.cjs loadTrustedGlobalRoots`), rejects non-absolute results.
- Exact commands (all verified in a scratch project cwd, node `gsd-tools.cjs`): `config-set agent_skills.gsd-planner '["global:ponytail:ponytail","<lens-brief path>","skills/jev-fast-decision",".aikit/brief"]'`; `config-set agent_skills_security.trusted_global_roots '["~/.agents/skills"]'`; `config-set workflow.ui_review true`; `config-get workflow.ui_review --raw` printed `true`. Agents (config keys): `gsd-ui-researcher`, `gsd-ui-checker`, `gsd-ui-auditor` get `global:impeccable`; `gsd-planner`, `gsd-plan-checker` get `global:ponytail:ponytail`; `gsd-code-reviewer` gets `global:ponytail:ponytail-review`; `gsd-phase-researcher`, `gsd-planner`, `gsd-executor` also get the brief. Check `query agent-skills <agent>` output for no WARNING (SPEC R9 acceptance).
- Lens-brief entry: GSD demands a folder holding `SKILL.md`. Recommend a tracked `.planning/lens-brief/SKILL.md` (path is project-relative, tracked, read only by check-dogfood, never by tests). It is not under `skills/`, but it is a `SKILL.md`: treat it as judge-subject to be safe (AGENTS.md rule is literal). The drift check lives in `tools/check_dogfood.py` as a read-only `gsd-tools query agent-skills`/`config-get` comparison (new `check_lens_wiring(root, run)` beside `check_flow_config`, same `FlowRun` seam).

### U4. Test fakes
- `tests/host_fakes.py`: `HOST_NAMES` = sorted RUNTIMES binaries plus `gp_host.HOST_BINARY` values; **`codegraph` and `graphify` are not host names and are not tripwired or faked today**. A module that does not set its own PATH would run the real binaries on this machine. API: `write_host_fakes(bin_dir, answers, log_path)`, `host_path(bin_dir, base)`, `fake_calls(log_path)` (JSON lines `{"name","argv"}`); the fake answers only exact argv tuples and exits 1 otherwise. `tests/forge_fakes.py` is the precedent for a non-host stateful fake (`gh`, same log format).
- Plan: new `tests/index_fakes.py` (helper, not a test module) writing `codegraph` and `graphify` fakes that log through the same `fake_calls` format, answer `status --json` from a canned dict per case (`initialized`, `pendingChanges {added,modified,removed}`, `worktreeMismatch`, `index.reindexRecommended`; confirm the exact nesting from `codegraph status --json`, which prints top-level keys `initialized, version, projectPath, indexPath, lastIndexed, fileCount, nodeCount, edgeCount, dbSizeBytes, walSizeBytes, backend, journalMode, nodesByKind, languages, pendingChanges, worktreeMismatch, index`), create `.codegraph/` on `init -y`, write `graphify-out/graph.json` with a `built_at_commit` on `update .`, and log start/end markers (for the no-overlap assertion). Build the fake PATH the way `write_host_fakes`/`host_path` do. Because the fake list `HOST_NAMES` is pinned by drift tests, do not add these two names to it.
- E2E grouping: `tools/run_unittest_parallel.py` `E2E_MODULES` (frozenset of dotted module names) and `E2E_RECORDED_SECS` (whole seconds; **a module missing there is deferred to push**; `COMMIT_E2E_BUDGET_SECS = 60`). Real-git-worktree modules named `*_e2e.py` are added to `E2E_MODULES` by hand; `tests/test_gate_scope.py` fails on a stale listing or an ungrouped module. After adding any test module run `python3 tools/gen_test_groups.py`, which rewrites the `# BEGIN GENERATED test groups` blocks in **`Makefile` and `.pre-commit-config.yaml`**; both are in `SHARED_MACHINERY`, so staging them runs the full unit and arch groups at commit (about 70 s `make test`). Record e2e time from `=== <module>: ok in <s>`.

### U5. Tool advisor
- `tools/hooks/advisor_core.py`: advice ids are the keys of `_advice_for` results: `grep`, `cat`, `find`, `sed-range`, `sed-edit`, plus `read-large`. Frequency: `count_due` shows the first and every tenth repeat (`REPEAT_EVERY = 10`); per-call dedupe by `call_key(event)` (sha of `tool_use_id`) recorded in `state["calls"]` (cap `MAX_CALL_RECORDS = 256`); state under a per-session flock (`with_state`, `LOCK_NAME`). Candidates come from `_candidate_advice(event, installed)`: only `tool == "bash"` and `"read"`.
- Grep/Glob reach: `event_from_claude` copies only `command`, `file_path`, `offset`, `limit` from `tool_input`; **it must also map Claude's Grep/Glob inputs (`pattern`, `path`, `glob`, `type`) and the payload `cwd`** (needed to test for `.codegraph/`). The Pi path `event_from_pi` already has `cwd`. Add new ids `codegraph-search` (rg/grep/find over non-Markdown paths, and Grep/Glob) and make the indexed check `os.path.isdir(os.path.join(cwd, ".codegraph"))` (nearest ancestor if cwd is nested). The advice line is one fixed-template string (`ai-kit advice: ...`) like `_grep_line`. Note `installed_tools(env)` is about `rg/bat/sd/fd`, unrelated to codegraph. The advisor must not shell out to `codegraph` (stdlib, 3 s hook timeout).
- Hook table: `tools/setup.py` line ~1781, `HookRow(id="tool-advisor", host="claude", event="PreToolUse", matcher="Bash|Read", script="tools/hooks/claude_tool_advisor.py", ..., timeout=3)`. Change to `"Bash|Read|Grep|Glob"`. `_refresh_or_append_claude_hook` already moves an existing ai-kit hook object to a fresh entry when the matcher differs, so no migration code. Tests pinning the old value to update: `tests/test_hook_registry.py:99` (`("PreToolUse", "Bash|Read", 3)`) and `tests/test_hook_registry_e2e.py:66`. Plus `tests/test_tool_advisor_core.py`, `tests/test_tool_advisor_state.py`.

### U6. setup, wizard and doctor
- `tools/setup.py` `main()` (line ~4729): flags `--dry-run`, `--headless`, `--skills`, `--with-statusline`, `--with-hooks`, `--examples`, `--config-doctor`, `--replace-existing`; the guard `(--skills/--with-statusline/--with-hooks) and not --headless -> parser.error`. `cmd_install_headless(env, dry, skills_flag, with_statusline, with_hooks, examples_flag, replace_existing)` is already at the lint ceiling (pylint max-args 5, disabled locally, 14 of 15 locals): add `--with-global-rules` as a **bool param handled in a new helper `_headless_apply_global_rules(env, dry)`** and extend `requested`; bare headless must still be a no-op. Real-home guard: `_refuses_real_home(env)` already blocks writes when `AI_KIT_REFUSE_REAL_HOME` is set and HOME is real; `--dry-run` bypasses it.
- Wizard: `_make_wizard_commit(paths, entries, dry, counts, examples_flag)` builds the in-UI commit callable (runs in a Textual worker thread; must not print); Review lives in `tools/wizard_app.py` (`_compose_review` ~line 494, `_review_component_rows` ~809). The pre-checked Review item with per-file diff is a wizard_app change plus a commit-step addition; AGENTS.md requires actually running `tools/wizard_app.py` under `uv run`. Integration tests: `tests/test_wizard_app_*.py`, `tests/test_wizard_pty.py` (under uv; slow to touch).
- Doctor: rows are `CheckRow(id, runtime, scope, check, read, recommended, confidence, why, source, apply, reads_section_file, apply_target, security_relevant)` in `CONFIG_DOCTOR_ROWS`; a cross-host row uses `runtime="cross"`, `reads_section_file=False` (precedent `rtk-cursor-integration`, line ~1028); `read(ctx)` gets `ReadContext(data, env, runner)`; `apply(ctx, target, dry)` returns `{"ok": bool, ...}` (`config_doctor_appliers.py`, which "imports nothing from setup.py and nothing from any skills/*"). `resolve_runtime_config_paths(env)` resolves the four runtime config files (not the global instruction files), so add a `resolve_global_instruction_paths(env)` next to it.
- Four target files (codegraph 1.6.2 installer, from the SPEC's read of `installer/targets/`; not re-read): Claude `${CLAUDE_CONFIG_DIR:-~/.claude}/CLAUDE.md`, Codex `${CODEX_HOME:-~/.codex}/AGENTS.md`, Gemini `~/.gemini/GEMINI.md`, opencode `${XDG_CONFIG_HOME:-~/.config}/opencode/AGENTS.md`, block `<!-- CODEGRAPH_START -->` ... `<!-- CODEGRAPH_END -->`. Re-read the installer's `instructions-template.js` in plan task 1 to copy the exact installer sentence and count it (read in place is allowed).
- **Shared marked-block editor path:** new stdlib module `tools/marked_block.py` (pure functions over `bytes`: `find_block(data, start, end)`, `replace_in_block(data, start, end, old, new)`, byte-preserving, returns the new bytes or a skip reason), importable by `setup.py` and by `config_doctor_checks`/`config_doctor_appliers` (a new tools module, not a skills import), reusable by Phase 54. A thin `tools/global_rules.py` holds the four-host path table, the sentence constants and the backup/re-read-before-replace write using the `tempfile.mkstemp` + `os.replace` pattern of `config_doctor_appliers.atomic_write_json` but for bytes and with a `.bak` copy first. Add a `tests/test_arch.py` non-vacuity pair if a new structural rule is added.

### U7. House rules and doc-contract tests
- `rules.py`: R07 `condition_tool_presence("codegraph")`, signals `("codegraph", "codegraph_explore", ".codegraph")`; R08 `condition_tool_presence("graphify")`, signals `("graphify", "graph.json", "graphify-out")`; both `CRITICALITY_MEDIUM`, category `workflow`. Keep ids and criticality (D-13). Signals drive the heuristic that a target AGENTS.md "covers" a rule, so keep the existing signal phrases in the new summaries. Single rule text: put the canonical constants in `skills/_shared/ai_kit_rules_common/` (new module, e.g. `code_exploration.py`: `RULE_TEXT`, `R07_SUMMARY`, `R08_SUMMARY`), imported by `rules.py` (same import style as `tool_catalog`). The advisor (under `tools/`) may not import a skills package (layering), so it holds its own one-line string and a test asserts it is a prefix/subset of the shared text. R07/R08 tests live in `tests/test_ai_kit_project_rules_agents.py` (lines ~137-177, 552) and `tests/test_ai_kit_rules_common.py`.
- Doc-contract pattern to copy: `tests/test_flow_docs.py` `TestShipRule` (`_ship_rule(agents)` extracts one bullet, `_missing_steps`, `_in_order`, a "remove each clause fails" loop, a missing-bullet non-vacuity case). Use the same shape for the tool-use rule (AGENTS.md `## Code Exploration`), the design rule (a Workflow/Non-Negotiable bullet in the owner-written part, above any generated block), the `setup-dev` Commands line and the runbook link. New test module suggestion: `tests/test_rules_docs.py`; the runbook sections test pins `docs/run-book/graphify.md` headings in order build, refresh, freshness check, query (`docs/` currently has `prds refactor research superpowers wizard-redesign`, no `run-book/`).
- `ai-kit-project-rules-agents/SKILL.md` has no R07/R08 text (only a tool-presence sentence at line 37), so it does not join the judge set unless edited.

### U8. Makefile, pre-commit, detached job
- `Makefile`: `.PHONY` list includes `dev setup-env`; recipes `setup-env: uv sync`, `dev: setup-env` then `uv run pre-commit install`. `setup-dev` target: `setup-dev: setup-env` plus a single-line call to a script (Makefile rules in this repo cap recipes at three lines): `python3 tools/setup_dev.py` (tool table: name, probe `shutil.which`, install argv, manual hint; failures printed, exit 0; lock `fcntl.flock` on `<git common dir>/ai-kit-setup-dev.lock`; injectable runner for tests) followed by `uv run pre-commit install` (installs all `default_install_hook_types`). Keep `dev` and `setup-env`.
- `.pre-commit-config.yaml`: `default_install_hook_types: [pre-commit, pre-push]` -> add `post-checkout`. **Verified live in a scratch repo (pre-commit 4.6.2):** with the hook installed, `git worktree add -q ../wtA -b a` ran the whole add in 0.10 s real and the `post-checkout` hook ran in the new worktree (cwd = the new worktree) with env `PRE_COMMIT_FROM_REF=0000000000000000000000000000000000000000`, `PRE_COMMIT_TO_REF=<sha>`, `PRE_COMMIT_CHECKOUT_TYPE=1`; `PRE_COMMIT_IS_BRANCH_CHECKOUT` was unset. Declaration: `stages: [post-checkout]`, `always_run: true`, `pass_filenames: false`, `language: system`, `entry: python3 skills/ai-kit-commit-fold/scripts/fold.py index --detach` (the script reads `PRE_COMMIT_FROM_REF`; all zeros = new worktree or clone; any other value is an ordinary checkout and is ignored, and always exits 0 so it can never fail a git command). `.pre-commit-config.yaml` is in `SHARED_MACHINERY`.
- Detached job + one lock per repo, stdlib: the hook only appends the worktree path to a queue file under the git common dir (`ai-kit-index-queue`, one line per path, written with `O_APPEND`) and `subprocess.Popen([...], start_new_session=True, stdin/stdout/stderr=DEVNULL, close_fds=True)` a runner, then returns. The runner takes `fcntl.flock(LOCK_EX | LOCK_NB)` on `ai-kit-index.lock` (common dir); if held, exits (the holder drains the queue before releasing, so creation order is kept and no two jobs overlap); if acquired, loops pop-first-line: codegraph then graphify for that worktree (skip with a note when the path is gone), until the queue is empty. Test seams (no sleeps): `run_tool(argv, cwd)` callable, `popen` callable, and a `wait_idle(common_dir)` helper that blocks on `flock(LOCK_EX)` (returns when the job released) used by tests; per-run deadline via an injected monotonic clock. The same `flow_index` functions serve the boundary step and `start`.
- Worktree timing risk: the hook entry spawns python then Popen; keep imports light (the 1 s acceptance covers two concurrent adds).

### U9. graphify and GSD graph facts
- `gsd-tools graphify status` (`graphify.cjs` `graphifyStatus`, lines ~440-505) fields: `exists, graph_path, last_build, node_count, edge_count, hyperedge_count, stale, age_hours, built_at_commit (7 chars), current_commit, commits_behind, commit_stale, last_build_auto_update`. **`built_at_commit` is read from `graph.json`'s own `built_at_commit` field** (graphify 0.7+ writes it; the main checkout's graph.json holds a full sha). `stale = age > 24 h (graph.json mtime) || last-build status in {failed, running}`. `commits_behind` is informational. SPEC acceptance "`built_at_commit` equals HEAD" therefore comes free from the real `graphify update .`; the fake must write the field.
- `.planning/graphs/.last-build-status.json`, written by GSD's rebuild script (`.claude/hooks/lib/gsd-graphify-rebuild.sh`, read in place), keys: `ts` (UTC ISO), `status` (`running` | `ok` | `failed`), `exit_code`, `duration_ms`, `head_at_build` (sha), `graphify_version`. Success path copies `graphify-out/graph.json`, `graph.html`, `GRAPH_REPORT.md` into `.planning/graphs/` and `graph.json` to `.planning/graphs/.last-build-snapshot.json` (the diff baseline). Failure keeps the previous graph. Mimic exactly.
- `.planning/graphs/.rebuild.lock` holds the rebuilder's PID, removed on exit (`trap 'rm -f' EXIT`). The step's "wait while a live process holds it" = read PID, `os.kill(pid, 0)`; treat a dead PID as stale and ignore (never delete GSD's lock; if the wait deadline passes, report and continue). Inject the deadline/clock.
- `graphify.enabled` config key (and `graphify.auto_update`) are read from `.planning/config.json`; this repo has `{'enabled': True, 'auto_update': True}`. Read with `config-get graphify.enabled --raw` or parse JSON; never write them (prohibition). `graphify update .` is AST-only; `update` takes no `--graph` (SPEC-verified); `built_at_commit` aside, a root `.graphifyignore` is honored. Whether the step may create `.graphifyignore` in a target project is O3.
- codegraph: `codegraph init -y` (no-op on existing), `codegraph sync`, `codegraph index`, `codegraph status --json` (SPEC-verified); install of the CLI not re-verified.

### U10. File-ownership map (6 plans; wave order is by dependency; shared generated blocks make same-wave test-adding plans conflict, so execute sequentially in this order unless the orchestrator regenerates the blocks at wave end)

| Plan | Wave | files_modified (owner) | Depends |
|------|------|------------------------|---------|
| 30-01 Index engine + fakes | 1 | `skills/ai-kit-commit-fold/scripts/flow_index.py` (new), `scripts/fold.py` (register `index`), `tests/index_fakes.py` (new), `tests/test_flow_index.py` (new), `tests/test_flow_index_e2e.py` (new, real git, add to `E2E_MODULES`/`E2E_RECORDED_SECS`), generated blocks (`Makefile`, `.pre-commit-config.yaml`), `.graphifyignore` (root, ai-kit) | none |
| 30-04 Rules, runbook, advisor | 1 | `AGENTS.md` (sole owner: tool-use rule, design rule, Commands `setup-dev`, runbook link), `docs/run-book/graphify.md` (new), `skills/_shared/ai_kit_rules_common/code_exploration.py` (new), `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py`, `tools/hooks/advisor_core.py`, tests `tests/test_rules_docs.py` (new), `test_ai_kit_project_rules_agents.py`, `test_tool_advisor_core.py`, `test_ai_kit_rules_common.py`, generated blocks | none |
| 30-05 setup global rules | 1 | `tools/marked_block.py`, `tools/global_rules.py` (new), `tools/setup.py` (sole owner, including the `Bash|Read|Grep|Glob` matcher row), `tools/wizard_app.py`, `tools/config_doctor_checks.py`, `tools/config_doctor_appliers.py`, tests `test_marked_block.py`, `test_global_rules.py`, `test_setup.py`, `test_hook_registry.py`, `test_hook_registry_e2e.py`, `test_config_doctor.py`, wizard tests, generated blocks | none |
| 30-02 `boundary` + brief | 2 | `scripts/flow_boundary.py`, `scripts/flow_brief.py` (new), `scripts/fold.py` (register `boundary`, `--point`), `scripts/flow_unit.py` (`_start` calls boundary), `references/unit-contract.md` (new reason codes, `.aikit/brief/`), tests `test_flow_boundary.py`, `test_flow_brief.py`, `test_flow_contract.py`, generated blocks | 01 |
| 30-06 setup-dev + post-checkout | 2 | `Makefile` (recipe), `.pre-commit-config.yaml` (stage + `default_install_hook_types`), `tools/setup_dev.py` (new), tests `test_setup_dev.py`, `test_staged_commit_e2e.py` (if hook list is pinned), arch rule if any | 01, 04 (AGENTS.md Commands line already present) |
| 30-03 Delivery: GSD hooks, superpowers, lens wiring | 3 | `skills/ai-kit-commit-fold/gsd/ai-kit-commit-fold/capability.json`, `ai-kit-fold.cjs`, `skills/ai-kit-commit-fold/SKILL.md`, `references/adapter-guide.md`, `skills/ai-kit-spec-execute-superpowers/SKILL.md`, `references/start-step.md`, `references/dispatch-external-cli.md`, `.planning/lens-brief/SKILL.md` (new), `.planning/config.json` (via `config-set` only), `tools/check_dogfood.py`, tests `test_check_dogfood.py`, `test_ai_kit_commit_fold_e2e.py`, `test_ai_kit_spec_superpowers.py`, `test_flow_docs.py` | 02 |

SKILL.md files that change materially (orchestrator runs skill-judge; plans only prepare): `skills/ai-kit-commit-fold/SKILL.md` (boundary commands, GSD hooks list, numbered orchestrator instruction), `skills/ai-kit-spec-execute-superpowers/SKILL.md` (brief line, `--point` runs), and the new tracked `.planning/lens-brief/SKILL.md` (judge to be safe). Not changed: `ai-kit-project-rules-agents`. Judge variance: SKILL.md files here are already long; keep additions short (references/ files carry detail).
`AGENTS.md` edits all in 30-04; `setup.py` edits all in 30-05; `check_dogfood.py` all in 30-03; `fold.py` is edited by 01 then 02 (sequential).

## Architecture Patterns

### Boundary step data flow
```
GSD: discuss:pre step ----+                      superpowers: start-step.md block
     plan:pre (O1) -------+--> gsd-tools ai-kit-fold boundary-{plan,wave} --phase N
     execute:wave:pre ----+            |                    |
                                       v                    v
              ai-kit-fold.cjs -> python3 fold.py boundary --phase|--plan --point P --repo <cwd>
                                       |
                    flow_boundary: take lock (common dir) -> read stack record
                       1. codegraph: no own index/worktreeMismatch -> init -y
                                     reindexRecommended -> index ; else sync   (CLI missing -> one line)
                       2. graphify update . (GSD project + enabled: copy to .planning/graphs + status file;
                                     honor .rebuild.lock; non-GSD: graphify-out only)
                       3. brief: previous unit range, git diff --name-status, explore instruction,
                                     docs outside .planning/ mentioning names -> .aikit/brief/SKILL.md (atomic)
                                       |
                              report lines (refreshed / skipped / why), exit 0 on tool absence
post-checkout (pre-commit) -> fold.py index --detach -> queue + detached runner (one flock) -> steps 1-2 per worktree
```

### Patterns
- Command module = `cmd_x(args)` returning an exit code, printing `render(...)` reports (`flow_record.render`), refusals via `FlowError`. Follow `flow_unit._run`.
- External tool calls through one `run_tool(argv, cwd)` seam (`subprocess.run` argv list, never a shell; paths as separate args for the encoding row).
- Choice order is fixed (SPEC): no own index (`not initialized` or `worktreeMismatch`) -> `init -y`; elif `index.reindexRecommended` -> `index`; else `sync`; unreadable status -> `index`, and a failure there is reported and skipped.
- Document search: tracked files via `git ls-files` outside `.planning/`, `-w`-style whole-word, case-sensitive, literal (regex-escape), cap 10 per name (11+ shows count and first 10 paths); the word "mentions" must appear in the brief template (test pins it).

### Anti-patterns
- Do not read `.codegraph/` internals (D-08). Do not write `.planning/` in a non-GSD project. Do not edit `graphify.enabled`/`auto_update` or GSD hook scripts. Do not hand-edit `.planning/config.json` (config-set only, at execution time). Do not `os.remove` any lock you do not own.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file write | new temp logic | `flow_record._atomic_write_json` shape / `config_doctor_appliers.atomic_write_json` shape (bytes variant) | fsync, mode copy, cleanup already proven |
| Previous-unit lookup | custom record parser | `flow_record.read_record` / `find_entry` | schema-checked |
| Rename detection | custom diff | `git diff --name-status -M <range>` (R lines) | edge row: renamed listed once |
| GSD project detection | new marker logic | `skills/ai-kit-spec-execute/detect_framework.py` marker `.planning/PROJECT.md` plus config check | D-16; note skills are self-contained, so copy the 3-line check rather than import across skills |
| Fake host/forge | ad hoc stubs | pattern of `tests/forge_fakes.py` + `host_fakes.fake_calls` | same log format, tripwire-safe |
| Per-file doc-contract | free-form string asserts | `TestShipRule` shape | includes non-vacuity |
| JSON config set | edit `config.json` | `gsd-tools config-set` | prohibition |

## Common Pitfalls

1. **A `plan:pre` command step looks installed and never runs** (`loop render-hooks plan:pre` lists it; plan-phase only dispatches skill/agent). check-dogfood would pass while nothing happens. Mitigation: O1 and an e2e that asserts what plan-phase prose can dispatch.
2. **Wave-1-only without a wave number.** Re-running at every wave re-indexes mid-phase (violates SPEC boundary row); deciding from SUMMARY files alone misses the interrupted-wave-1 case. Use per-plan frontmatter wave plus SUMMARY presence.
3. **check-dogfood self-contradiction.** Leaving `FLOW_EMPTY_POINTS` unchanged fails `make validate` and the pre-push hook the moment the capability is reinstalled.
4. **Capability mirror is gitignored.** `.gsd/capabilities/` is per checkout; the e2e must install into the fixture; ai-kit's live checks need a re-install in each worktree/main after the manifest changes (ship order in AGENTS.md: install and re-check live before verification passes).
5. **`config-set` replaces whole arrays.** Dropping `skills/jev-fast-decision` silently removes jev from that agent; the plan's set commands list it explicitly and a test of the plan's command list (not the live config) checks it.
6. **Gitignored brief absent on a fresh clone/worktree** gives `Skill not found ... skipping` for every agent. Boundary/start/worktree job must create `.aikit/brief/SKILL.md` ("no brief") even when indexing is skipped.
7. **Tests may run the real `codegraph`/`graphify`** (not tripwired). Every test module sets a PATH from `index_fakes`, or one without the tools; a `tests/test_arch.py`-style guard is cheap insurance.
8. **Hook must never fail git.** `post-checkout` exit code propagates to `git checkout`; wrap everything and `return 0`.
9. **Generated test-group blocks** in two shared files (U4). Run `python3 tools/gen_test_groups.py` before committing any plan that adds a module.
10. **pylint ceilings** (`max-args=5`, `max-locals=15`, `max-branches=12`, `max-statements=50`) hit `cmd_install_headless` and engine functions fast; split helpers up front. `make pyright` is not run by the commit hook (push only): plans run it themselves.
11. **Stale-index detection of `worktreeMismatch`** is on the status JSON top level; a nested worktree under `.claude/worktrees/` borrows the parent's index until it has its own (SPEC); do not treat parent `sync` as success.

## Code Examples

Verified agent-skills render (scratch project, node gsd-tools, this session): input `["global:ponytail:ponytail","skills/x",".aikit/brief"]` produced
```
<agent_skills>
Read these user-configured skills:
- Load the `ponytail:ponytail` skill via the Skill tool before proceeding (plugin-provided).
- @skills/x/SKILL.md
- @.aikit/brief/SKILL.md
</agent_skills>
```
post-checkout probe (verified): hook env on `git worktree add`: `from=0000000000000000000000000000000000000000 to=<sha> type=1 branch=None`.
Capability step to add (shape from existing manifest, verbatim keys): `{"point": "execute:wave:pre", "ref": {"command": "ai-kit-fold boundary-wave"}, "produces": [], "consumes": [], "onError": "skip"}`.

## State of the Art / Environment

gsd-core installed: **1.20.0** (`.claude/gsd-core/VERSION`), codegraph 1.6.2, graphify 0.9.54, pre-commit 4.6.2, gh with `gh stack` v0.3.0, uv present. Node present (gsd-tools run). Registry `npm` banned on this machine (use pnpm/volta) which matters for any codegraph install fallback.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| codegraph | R2, hook | yes | 1.6.2 | one-line note, step continues |
| graphify | R3 | yes | 0.9.54 | one-line note |
| pre-commit | R6 hook | yes | 4.6.2 | hook not installed; boundary-point trigger covers (D-03) |
| gh + gh-stack | 29.1 flow | yes | gh-stack 0.3.0 | no-PR path |
| node, uv, git | gsd-tools, uv env | yes | not probed individually beyond use | none |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | gh, gh-stack and codegraph install commands (no verified portable form) | Standard Stack, U8 | setup-dev installs nothing; reports manual step (designed to degrade) |
| A2 | Previous unit's range after merge uses `prev.pushed`/merge sha when its branch is gone | U1 | wrong range in the brief for merged predecessors; needs a fixture |
| A3 | PLAN.md frontmatter key for wave is `wave:` | U2 | wave-1 detection wrong; verify against a real plan first |
| A4 | `.git/info/exclude` is the right place to ignore `graphify-out/` and `.planning/graphs/` in target projects | U1 | dirty trees in target projects |
| A5 | `.planning/lens-brief/SKILL.md` as the tracked lens-brief path and that it counts for the judge | U3 | judge scope mismatch (discretion) |
| A6 | The four global file paths and installer sentence are as the SPEC read them (codegraph 1.6.2) | U6 | R11 rewrites nothing; re-read installer source in plan task 1 |
| A7 | A `plan:pre` skill/agent step cannot run a shell command deterministically | U2 | if wrong, O1 is simpler |
| A8 | Hook cost for the two concurrent `worktree add` stays under 1 s on cold python start | U8 | acceptance flake; measure in the e2e |

## Open Questions

1. **O1 (owner, blocks Plan 03 only): `plan:pre`.** No command-capable hook form exists at `plan:pre` in gsd-core 1.20.0. Options: (a) accept the fallback in U2 (discuss:pre + execute:wave:pre real steps, numbered orchestrator instruction for planning, brief staleness stamp) [recommended: nothing is lost that D-03's other triggers do not cover]; (b) a prose-dispatched `ref.agent` step with an inline fragment telling a subagent to run the command (best-effort, needs an installed agent); (c) ask GSD upstream for a command arm. Plans 01, 02, 04, 05, 06 do not depend on the answer.
2. **O2: wave number.** Resolved in plan by engine-side detection; confirm the PLAN.md frontmatter key (A3).
3. **O3: `.graphifyignore` in target projects.** SPEC says "committed root `.graphifyignore`" and D-16 "written only in a GSD project". Recommend ai-kit commits its own, and the step only reports (does not write a tracked file) when absent in other projects; owner may prefer the step to create it.
4. **O4: codegraph/gh install commands** for setup-dev (A1): confirm with the owner/tools-installer before wiring; table entry stays a manual hint until then.
5. Which `fold.py` subcommand name carries the detached hook (`index --detach` assumed).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest`, run by `tools/run_unittest_parallel.py` (one subprocess per module, tripwire on PATH, baseline env, temp HOME with `AI_KIT_REFUSE_REAL_HOME=1`) |
| Config file | none; groups discovered from `tests/test_*.py`, generated blocks via `tools/gen_test_groups.py` |
| Quick run command | `python3 tools/run_unittest_parallel.py --group unit -- tests.test_flow_index tests.test_flow_boundary` (any dotted modules after `--`) |
| Full suite command | `make test` (about 70 s); `make pyright` and `make check-dogfood` separately |

### Phase Requirements -> Test Map
| Req | Behavior | Type | Command | Exists |
|-----|----------|------|---------|--------|
| R2 | init/index/sync/CLI-missing/unreadable via recording fake | unit | `python3 tools/run_unittest_parallel.py --group unit -- tests.test_flow_index` | Wave 0 (30-01) |
| R3 | graphify update, copy, status file, rebuild lock, non-GSD no `.planning/` | unit + e2e | `... -- tests.test_flow_index tests.test_flow_index_e2e` | Wave 0 |
| R1/R4 | three points, previous unit range, brief (added/changed/removed, rename, docs-only, first unit, cap 10, case-sensitive whole word, "mentions") | unit | `-- tests.test_flow_boundary tests.test_flow_brief` | Wave 0 (30-02) |
| R5 | prompts carry brief; stale unit id; absent brief text | unit + e2e | `-- tests.test_ai_kit_commit_fold_e2e tests.test_ai_kit_spec_superpowers` | extend |
| R6 | two concurrent worktree adds < 1 s, no overlapping jobs, hooks-uninstalled worktree indexed at boundary | e2e (real git, real pre-commit hook in temp repo, fake indexers) | `-- tests.test_flow_index_e2e` | Wave 0 |
| R7 | clause pins, R07/R08 summaries equal the rule text, advisor lines (indexed vs not, Markdown-only, Grep/Glob, dedupe, frequency) | unit | `-- tests.test_rules_docs tests.test_ai_kit_project_rules_agents tests.test_tool_advisor_core` | Wave 0 (30-04) |
| R8 | runbook headings in order; AGENTS.md link | unit | `-- tests.test_rules_docs` | Wave 0 |
| R9/R10 | config-set command list (not the live config), lens text, design rule pins, check-dogfood lens drift | unit | `-- tests.test_check_dogfood tests.test_rules_docs` | extend |
| R11 | byte-diff is the sentence alone, backup, idempotent, dry run, adjacency (outside block), concurrency re-read, drift row + re-apply | unit (+ integration for wizard item) | `-- tests.test_marked_block tests.test_global_rules tests.test_setup`; wizard: `uv run python tools/run_unittest_parallel.py --group integration -- tests.test_wizard_app_1` | Wave 0 (30-05) |
| R12 | fake installers: four install, one fails, exit 0, second run installs nothing, order, lock | unit | `-- tests.test_setup_dev` | Wave 0 (30-06) |

### Sampling Rate
- Per task commit: the covering modules via the commit hook (`--staged`); e2e modules recorded over 60 s are deferred to push.
- Per wave merge: `make test`. Per plan close: `make pyright` and `make check-dogfood`.
- Phase gate: `make test` plus `make validate` green, then install + live re-check from the branch tip (AGENTS.md ship order).

### Fast-test rules
No `time.sleep` in any new test. Waiting is done by blocking on a lock (`flock`) or on an injected clock/deadline (`now()` callable, `wait_idle`). Detached jobs are started through an injectable `popen` in unit tests; the e2e starts the real runner and joins via the lock. Fake tools log start/end markers to a file read after the join. Every tool call goes through the injectable `run_tool`. Use temp repos from `tests/fold_fixtures.py` (`make_repo`, `commit`, `gsd_project`, `superpowers_project`) and the `_FlowCase` template of `tests/test_flow_contract.py`; synthetic HOME for R11. Record each new e2e module time in `E2E_RECORDED_SECS`.

### Wave 0 Gaps
- [ ] `tests/index_fakes.py`, `tests/test_flow_index.py`, `tests/test_flow_index_e2e.py` (30-01)
- [ ] `tests/test_flow_boundary.py`, `tests/test_flow_brief.py` (30-02)
- [ ] `tests/test_rules_docs.py` (30-04)
- [ ] `tests/test_marked_block.py`, `tests/test_global_rules.py` (30-05)
- [ ] `tests/test_setup_dev.py` (30-06)
- [ ] Spike for O1 (scratch GSD project) before Plan 03, optional

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input validation | yes | argv lists only (no shell); validate `--phase` with the existing `_PHASE` regex; regex-escape literal names; `ref.command` regex |
| V12 Files / V4 Access | yes | atomic writes, backup before global-file write, re-read before replace, real-HOME guard, never delete locks you do not own |
| V6 Cryptography | no | none |
| V2/V3 | no | no auth/session |

| Threat | STRIDE | Mitigation |
|--------|--------|------------|
| Path with spaces / hostile branch or file names reaching a shell | Tampering | `subprocess.run(list)`; names as separate args |
| Symlink swap on brief or global file | Tampering | `mkstemp` in the same dir + `os.replace`; refuse non-regular targets |
| Lost update to a global file written by `codegraph install` | Tampering | re-read just before replace; abandon with note |
| Third-party manifest `ref.command` injection | Elevation | fixed verbs in `parse()` of `ai-kit-fold.cjs`, regex-checked by GSD |
| Install steps run unvetted downloads | Elevation | tool table prints the manual command instead of piping curl to bash unless owner confirms (A1/O4) |

## Sources

### Primary (HIGH, read this session)
- `skills/ai-kit-commit-fold/scripts/{fold.py,flow_unit.py,flow_record.py}`, `gsd/ai-kit-commit-fold/{capability.json,ai-kit-fold.cjs}`, `references/{unit-contract,adapter-guide}.md`, `SKILL.md`
- `skills/ai-kit-spec-execute-superpowers/{SKILL.md,references/start-step.md,references/dispatch-external-cli.md}`
- `.claude/gsd-core/{workflows/plan-phase.md,execute-phase.md,discuss-phase.md,references/loop-hook-dispatch.md,bin/lib/init.cjs,graphify.cjs,capability-validator.cjs,security.cjs}`; `.claude/hooks/lib/gsd-graphify-rebuild.sh` (main checkout, read only)
- `tests/host_fakes.py`, `tests/forge_fakes.py`, `tools/run_unittest_parallel.py`, `tools/check_dogfood.py`, `tools/hooks/advisor_core.py`, `tools/setup.py`, `tools/config_doctor_checks.py`, `Makefile`, `.pre-commit-config.yaml`, `rules.py`
- Live probes: scratch-project `config-set`/`query agent-skills`; scratch-repo pre-commit `post-checkout` on `git worktree add`; `codegraph status --json` keys; `uv tool list`; `gsd-tools query package-legitimacy check`

### Tertiary (LOW)
- WebSearch on the codegraph install command (third-party forks only): not relied on.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH for repo facts, LOW for third-party installs.
- Architecture: MEDIUM-HIGH; the plan:pre dispatch conclusion is from workflow prose and the validator, not an executed spike.
- Pitfalls: HIGH.

**Research date:** 2026-11-05. **Valid until:** about 2026-11-19 (gsd-core and codegraph move quickly; re-check `VERSION` and the dispatch prose before planning if later).
