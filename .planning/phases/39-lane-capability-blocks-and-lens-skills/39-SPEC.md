# Phase 39: Lane capability blocks and lens skills — Specification

**Created:** 2026-11-16
**Ambiguity score:** 0.16 (gate: ≤ 0.20)
**Requirements:** 12 locked *(amended 2026-11-23, cross-phase amendment for what Phases 37, 38 and 38.1 shipped: still 12; R1, R3 to
R9, R11 and R12 carry dated notes, and the plan fix pass added notes to R2, R3, R4, R5, R7, R8, R10 and R11; see "Live facts added
2026-11-23")*

## Goal

Every review or execute lane (an external CLI the review or execute skill starts) is told, in its prompt, only what its own
final argument list lets it do, and a prompt that cannot fit a lane's known window is refused for that lane before it is spawned.
One role-keyed table of the skills and MCP servers present on each host, rescanned on every run, feeds that block, the lens
skills that reach reviewers, and the GSD config skill; an optional configuration-time sorter proposes a role for an unknown
skill and the owner confirms every sort.

## Background

Requirements REV-03, REV-04 and REV-05 (REQUIREMENTS.md "Review"), roadmap Phase 39 criteria 1 to 5, and the locked inputs of
Phases 35 to 38.1: the catalog keeps a context window per (runtime, model) with a source label (35 D-09), the runner prints every
named setting as `applied`, `ignored` or `unknown` with a reason and `--print-argv` shows the final argv (37 D-11, D-12, D-14),
38.1 added `bad_request` for the host's own `context_length_exceeded` answer, and the HOST SETTINGS FORMS directive says how a
host takes a setting is fixed knowledge in the runner rows with a source label, never a decision table.

**The owner's directives that bind this phase (2026-11-16):**

- A table is seed data and examples only; it never decides. Presence of a skill or server is learned by scanning; what a host
  accepts is learned from its own help or a probe; live evidence beats a row; a row never blocks a lane. A runtime missing from
  a table, and a custom command lane, still get a block with every unknown fact shown as unknown.
- Only `router-env/<x>` model names may be hardcoded; no model or provider name appears in the block, the table seed, the
  tests or the docs of this phase except as a placeholder.
- jev and herdr only where present at the runtime of the skill that uses them, each with a tested behavior without them.
- ADOPTED from GSD: refuse (never trim) a prompt over a lane's known window, an unknown window is not capped and shows as
  unknown, reject control characters and out-of-root paths in values embedded in a prompt.
- Best design over the smallest diff; no half-done feature.

**Live facts checked for this spec (2026-11-16, this machine; claude 2.1.325, codex 0.169.0, copilot 1.0.112, cursor-agent
2026.11.13, opencode 2.3.0, pi 1.5.2, node 24.21.0, herdr present with `HERDR_ENV=1`; the runner is the pre-Phase-37 template):**
*(amended 2026-11-23: the runner is now template 11 with Phase 37's skill and MCP forms; the argv and builder facts below are
re-read in "Live facts added 2026-11-23", which outranks this list where they differ)*

- The final review argv (`cross-ai.mjs --print-argv`) differs sharply per host. pi review: `--tools read,grep,find,ls --no-skills
  --no-mcp --no-extensions --no-context-files` (no shell, no skills, no MCP, read-only). pi exec: `--no-skills --no-extensions
  --no-approve --offline` (default tools including `bash`, `edit`, `write`). copilot review: `--available-tools=view,grep,glob
  --excluded-tools=bash,create,edit,apply_patch --deny-tool=shell --deny-tool=write --disable-builtin-mcps` (no shell, no
  write, no MCP; neither `--add-dir` nor `--allow-all-paths` is passed, so the path verification its help describes applies);
  copilot exec:
  `--allow-all-tools` only. claude review: `--permission-mode plan` with no tool list. codex review: `--sandbox read-only`;
  codex exec: `--dangerously-bypass-approvals-and-sandbox`. cursor review: `--mode ask` (read-only by its own help text);
  cursor exec: `--force --sandbox disabled`. opencode review: `--agent plan`; opencode exec: `--auto`. Whether a read-only claude
  plan lane, an opencode plan agent or a cursor ask lane can run a shell command is not shown by their help and is unverified.
- The current guidance builder (`tooling_guidance.build_tooling_guidance`, called by `reviewer_dispatch._reviewer_full_prompt`
  and `execute_dispatch.build_execute_guidance`) takes the runtime name, a tool map computed once from the parent's PATH, and a
  per-CLI MCP registration read. It takes no argv and no role, so a pi or copilot review lane (no shell tool at all) is told
  to prefer `rg` and to run `codebase-memory-mcp cli ...`, which it cannot do. Soft-confinement guidance is decided by
  membership in `OS_SANDBOXED_EXEC` (`{"codex"}`), a seed set, not by the lane's argv (codex exec runs unsandboxed unless
  `--codex-sandbox workspace-write` is passed).
- The child's PATH is the parent's PATH: `runner_dispatch.child_env` copies the parent's environment, removes host-signal
  variables and applies per-runtime extras; the runner's `childEnv` does the same plus `CONFIG.scrubEnv`. The tool map today is
  `detect_tool_availability` over the parent's PATH, passed in as `--tool-availability-json` (spec-review SKILL.md line 315,
  cross-ai-dispatch.md line 66 to 74).
- Skills on this machine: `~/.claude/skills` 43 entries, `~/.agents/skills` 20, `~/.pi/agent/skills` 6, `~/.codex/skills` 2,
  `~/.cursor/skills` 1, `~/.copilot/skills` 1, `~/.config/opencode/skills` 1. The lens skills named by REV-03 exist as real
  directories: `ponytail`, `ponytail-audit`, `ponytail-debt`, `ponytail-review`, `reducing-entropy`, `naming-analyzer` and
  `impeccable` under `~/.agents/skills` (and `impeccable`, `reducing-entropy`, `naming-analyzer` again under `~/.claude/skills`);
  the plugin cache also holds `ponytail` (with `ponytail-gain` and `ponytail-help`). `simplify` is a Claude Code built-in: no file
  named `simplify*` exists under `~/.claude` or `~/.agents`, so it has no text to inline for another lane.
- MCP servers by host config (names only, read from each host's own config file): claude `~/.claude.json` `mcpServers`, cursor
  `~/.cursor/mcp.json`, copilot `~/.copilot/mcp-config.json` and codex `~/.codex/config.toml` `mcp_servers` each hold exactly
  `codebase-memory-mcp`; opencode keeps its servers in `opencode.jsonc` (`mcp`); pi has no MCP config key and loads the
  `cbmem.ts` extension file. This is the registration reader `detection.cbm_registration` already implements for one server
  name; it reads no other name.
- pi 1.5.2's own docs state: `--no-skills` "disables discovered and configured skills. Explicit `--skill` paths still load"
  (docs/cli.md line 204 to 205); `--no-mcp` disables MCP; `--tools` is an allowlist that keeps MCP tools unless an entry starts
  with `mcp__`. claude has `--add-dir` ("additional directories to allow tool access to"); copilot has `--add-dir` ("allow
  file access to a directory and load its .github/skills") and path verification by default; cursor-agent has `--add-dir`
  ("additional workspace root"); opencode `run --file` attaches a file. Whether any of these lets a read-only lane read a file
  outside its working tree is unverified except pi's `--skill`.
- There is no prompt-size check today: `ARGV_PROMPT_MAX` (102400 bytes) in the runner is the argv length limit for runtimes that
  take the prompt on argv, not a window check. The only window figure in the runtimes snapshot is pi's `context_window` per id
  (detection schema version 6); Phase 35's catalog adds the per-(runtime, model) value with its label.
- Skill scanning exists in the GSD config skill (`skill_scan.py`: `scan_root`, `plugin_skills`, `scan_skills`,
  `ponytail_visibility` over a hardcoded `PONYTAIL_SKILLS` tuple and `host.HOSTS`, which has no copilot). Five other places hold
  their own copy of the host skill-root list (`fold_group.py`, `jev_ladder.py`, `gp_host.py`, `tools/judge_loop.py`,
  `tools/hooks/precompact_core.py`). The GSD config skill already loads modules of the review skill's package through
  `gsd_catalog.load_ai_kit_spec_module` (precedent: `local_secrets`, `gsd_tools`).
- jev is available (`jev_review.py --probe`: laya selected, typesafe usable with recorded consent) and herdr is present; both are
  optional everywhere else.

**Findings (existing code paths that gate on a table; listed, not changed beyond the requirements):**

- `runner_dispatch.OS_SANDBOXED_EXEC` decides soft-confinement guidance by runtime name (R4 replaces the decision with the lane's
  write capability from its argv; the set stays a seed until then).
- `skill_scan.PONYTAIL_SKILLS` and `host.HOSTS` decide which lens skills and hosts are reported (R10 derives the report from the
  shared table; copilot is missing from `HOSTS`).
- `detection.CBM_REGISTRATION_KEYS` decides which hosts have a registration reader; a host outside it gets "no reader" (unknown),
  never a refusal, which is the right behavior and stays.
- The five host skill-root copies and `PONYTAIL_SKILLS` are duplicated seed data; R1 gives the review and execute paths and the
  GSD config skill one source and leaves the five existing copies (outside this requirement's readers) listed here for the owner.

**Live facts added 2026-11-23 (cross-phase amendment: what Phases 37, 38 and 38.1 shipped; read at HEAD 04fd6ca, unit 39 stacked
on unit 38.1's review fold; every line below was read in the code or run under a scratch HOME with the real node,
`cross-ai.mjs` = `skills/ai-kit-spec-review/references/cross-ai.mjs`, the harness = its sibling `cross-ai-selftest.mjs`; the live
`--print-argv` run is `tmp/run-2026-11-19/p39-plan/argv_probe.py`, not committed):**

- *Size and shape.* The runner is 7,475 lines at template version 11 (`cross-ai.mjs:2`, `cross_ai.py:60` `TEMPLATE_VERSION = 11`);
  the harness is 12,026 lines. `--self-test-list` prints 908 cases (804 `logic`, 104 `runtime`) and
  `tests/fixtures/cross_ai_selftest_secs.json` holds 908 entries; the shards stay 5 `logic` and 7 `runtime` modules
  (`SHARD_COUNTS`, `tests/cross_ai_selftest.py:116`). A runner symbol a case uses must be in the trailing `export { ... }` list
  (`cross-ai.mjs:7319`, the 38-09 arch rule). The copy rule of 38-25 and 38.1-12 holds: the template version goes 11 to 12 with every
  pin, the live `.planning/scripts/cross-ai.mjs` is re-rendered once through `ensure-runner` in the phase's last code wave, then one
  `--record-times`, the `E2E_RECORDED_SECS` refresh and the shard check against the 60 s budget; `make check-dogfood` closes it.
- *Skills and MCP servers already reach a lane through the runner (Phase 37 R13 and R14, shipped).* The runner takes
  `--skill-path <dir>` and `--skill-name <name>` (repeatable) and `--mcp-config <file>` (usage `cross-ai.mjs:41-43`, parsed `:6694`
  to `:6699`). Each row has a `skills` field with three forms, `name`, `path` and `prose`, each with a source label and state
  (`:1758-1759`, pi `:1834`, claude `:1899`, copilot `:1929`, cursor, opencode and codex `skillsNone`), and an `mcp` field (claude
  `:1898`, copilot `:1928`, codex `:1867` unverified, pi, cursor and opencode none). `planSkills` (`:6521-6541`) applies, per skill,
  the first `verified` form in the order name, path, prose; prose is the runner's own form: a delimited block
  `<skill name=".." path=".." sha256="..">` with the `SKILL.md` body byte-equal (`skillBlock`, `:6520`), placed before the prompt.
  The report lines are `cross-ai: setting skill=<name> applied form=<name|path|prose>` or `ignored reason=<code>` (`reportLines`,
  `:2162`) and, per prose block, `cross-ai: skill-block <name> bytes=<n> sha256=<hex>` (`:6542`); `--print-argv` prints them
  (`:7050-7051`). Live (2026-11-23, both roles): `--skill-path` is `applied form=path` on pi (argv gains `--skill <dir>`) and
  `applied form=prose` on claude, copilot, codex, cursor and opencode with the argv unchanged; `--mcp-config` is `applied` on claude
  (`--mcp-config <file> --strict-mcp-config`) and copilot (`--additional-mcp-config @<file>`), `ignored reason=mode_forbids` on pi
  review, `no_form` on pi exec, cursor and opencode, and `unverified_form` on codex. An unknown runtime is a usage error (exit 2)
  before any line is printed. The runner refuses as usage errors (exit 2, the whole lane) a skill directory without `SKILL.md`, an
  empty `SKILL.md` (`:6499`), a body that is not strict UTF-8 or starts with a byte-order mark, a body over `FILE_READ_MAX` (65,536
  bytes, `:6420`), a skill name outside `^[a-z0-9][a-z0-9-]{0,63}$` (`SKILL_NAME_RE`, `:6615`; the curated-config scan accepts
  `[A-Za-z0-9_-]+`, `skill_scan.py:21`), a path holding a C0 or C1 control character (`CONTROL_CHAR_RE`, `:6617`, narrower than R8's
  set), and a copilot prompt pushed over `ARGV_PROMPT_MAX` (102,400 bytes, `:3896`). The MCP file must be a regular file not readable
  by group or others holding a non-empty `mcpServers` object (`loadMcpConfig`, `:6452-6466`). 37-REVIEW.md:100 (LOW-6, deferred):
  the prose block escapes neither its `path` attribute nor a body holding `</skill>`. The runner checks no repository or skill root
  (37 R13: "the repository-or-skill-root check is the caller's validator, Phase 39 R8"; the runner never scans a host).
- *The Python side passes none of it.* `RunnerSpec` (`runner_dispatch.py:68-84`) and `runner_flags` (`:215-233`) carry no skill or
  MCP field; `project_runner_command` (`:191-201`) builds the GSD hook string from the same `runner_flags`. `print_argv_lines`
  (`:296-318`, run in its own process group, both streams) and `preview_setting` (`:327`) already read `--print-argv`; their
  `SETTING_LINE_RE` (`:53-56`) drops `form=`. No lane config field carries skills or servers (`lane_settings.py:11`).
- *The guidance builder is unchanged.* `build_tooling_guidance(cli, tool_availability, agents_tooling_path, code_index_registered,
  shared_reference_path=None)` (`tooling_guidance.py:68-69`) is still called by `reviewer_dispatch._reviewer_full_prompt`
  (`:46`, `:51-57`) and `execute_dispatch.build_execute_guidance` (`:72`, `:86-92`) with no argv or role; `OS_SANDBOXED_EXEC`
  (`runner_dispatch.py:40`) also decides whether `--codex-sandbox` is passed (`:229-230`), which this phase leaves alone. The parent
  tool map is `--tool-availability-json` (`cli.py:423`, `:451`; spec-review SKILL.md:316; `cross-ai-dispatch.md:67-79`).
- *Argv per host now (2026-11-23).* As the Background list says, plus: copilot review now starts its profile with
  `--allow-all-tools` before `--available-tools=view,grep,glob --excluded-tools=bash,create,edit,apply_patch --deny-tool=shell
  --deny-tool=write --disable-builtin-mcps` (`:1922-1924`); pi review also passes `--no-approve --offline`; cursor exec adds
  `--trust --approve-mcps`; opencode adds `--standalone` and the env `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` (`:1802`). The
  `--print-argv` stdout is one `runtime<TAB>binary<TAB>argv-JSON` line (`:7047`), which `gp_host.py:381-385` parses by its
  three tab fields; every settings line goes to stderr.
- *Closed lists and exits from 38 and 38.1.* `--describe` prints 11 keys: `schema`, `template_version`, `settings`, `reasons`,
  `states`, `runtimes`, `host`, `statuses`, `findings`, `supervision_flags` and 38.1's `classes` (`describeJson`, `:6854-6885`); a
  row field is copied into `runtimes` keyed by setting (`:6869`), so a new row field shows up there with no change to
  `describeJson`. Runner exits in use: 0, 1, 2, 69 (38.1's `bad_request` among them), 75, 124, 127, 128 (`STATUS_TABLE`,
  `:1506-1529`); 65 is free. `SETTING_REASONS` (`:1955`) holds ten codes, `ROW_CLASSES` (`:1460`) seven classes with `bad_request`,
  `FINDING_CODES` (`:1629`) nine codes. The run lock is the runner's, in execute mode (`:4096` to `releaseLock` `:4289`; `locked`
  exit 75); Python's `STATUS_TO_REASON` maps `locked`, `partial` and `bad_request` to `real_error`. The confirmed-router rule
  (`model_heuristics.router_statement`, `:37`), `dispatch_classification`, the baseline, idle watchdog, finding group, `--sweep`,
  the stdout classification channel, router cooldown rows, the hard tier (60, 300, then every 600 s up to the cap, `hard_every_s`),
  `check=` and the blocked-until record (`--pool`, `--blocked-status`, `--blocked-clear`) are shipped and untouched by this phase.
- *The window.* No accessor function exists: Phase 35 stores the resolved window on each catalog runtime row as `context`
  (`{value, label, source, fetched_at}`, `catalog_labels.py:22`) and `ctx_window` (`catalog_facts.py:162-189`), resolved in the
  order `[[models.context]]` (`catalog_context.override_for`, `:68`, label `user-stated`), host figures, models.dev (label
  `measured`). `resolve_route` (`runner_dispatch.py:247-262`) is the existing reader pattern over the cached catalog.
- *Phase 36 read-only outputs.* `check-reviewer` prints one JSON object (`cli.py:1324`, `:1351`); `config-status` prints the state
  and one `checked <layer> <path> <status>` line per layer, not per lane (`config_status.py:63`, `:80`, `:85`).
- *Other homes.* The UI extension list is `_FRONTEND_EXTENSIONS` in the superpowers adapter
  (`task_classification.py:15`, `.tsx .jsx .css .vue .scss`), a module the frozen cross-skill allowlist does not list
  (`tests/test_arch.py:1568`, `:1632-1665`: only the adapter's `cli.py`, `dispatch_injection.py` and launcher may import the review
  package, and nothing may import the adapter). jev is reached by subprocess through its own ladder (`jev_names.find_jev` `:63`,
  `ask_items` `:140-146`). The layered config writer is `config_io.cfg_write_toml` (`:1057`) over `toml_splice.publish` (`:780`,
  atomic) and `set_table` (`:429`); `[skills.roles]` and `edit_lens_pass` exist nowhere yet. curated-config: `HOSTS` still has five
  hosts and no copilot (`host.py:19`), `PONYTAIL_SKILLS` is `skill_scan.py:22`, `load_ai_kit_spec_module` is `gsd_catalog.py:28`,
  `inventory.py` has no `skill_roles`.
- *codebase-memory-mcp.* `codebase-memory-mcp --help` (0.12.1, 2026-11-23): the bare command "Run MCP server on stdio", and
  `--tool-profile=analysis|scout` "Expose a restricted inspection surface" (its effect is unverified here).
- *gsd-core 1.22.0.* The project-local gsd-core was upgraded to 1.22.0 on 2026-11-22 12:53 (`.claude/gsd-core/VERSION`).
  `getGlobalSkillsBase` is still exported (`bin/lib/runtime-homes.cjs:47`, `:509`). gsd-core has no `--prepend-file` route: that flag
  is the runner's own (`cross-ai.mjs:57`); `workflows/execute-phase.md:442` pipes the prompt to `workflow.cross_ai_command` under
  `gsd_run run-with-timeout` (default 300 s, this project 1800, `.planning/config.json:47`), so a hook passes `--prepend-file` only
  if its configured command string does. The "ADOPTED from GSD" refusal is GSD's review-lane rule (`review-lane-invocation.cjs:66-71`
  `PROMPT_EXCEEDS_CONTEXT`, `refuseIfOverCap` `:385`, a 0.65 headroom `:294`, a 0 or null cap never refuses `:350-351`); this phase
  keeps its own locked compare (estimate against the full window, the under-counting divisor as its margin). GSD has no
  reject-only validator for prompt values (`security.cjs:478` `sanitizeForPrompt` rewrites; `assertWithinRoot` `:260` is a path
  helper); R8 stays this phase's own rule.
- *Test hygiene from 38.* A product spawn of node runs in its own session with a group kill on timeout (`run_in_own_group`,
  `detection.py:951`; the PATH `node` may be a Volta shim); tests take node from `tests.cross_ai_selftest._real_node_executable`.
- *Grok.* Grok is not a cross-AI target (owner directive 2026-11-20; Phase 39.1 removes its code). These files named no grok before
  this amendment; this phase adds no grok row, form, fixture, case, list entry or doc line, and the runner's runtime rows hold none.
- *Owner decision.* `.planning/docs/OWNER-DECISIONS-2026-11-16.md:52-54` confirms the after-approval pass off by default
  (`edit_lens_pass`) with a diff the owner accepts (R9, the Interview Log's provisional item).
- *Not re-checked.* The per-root skill counts of the Background list (the real home is not read in this run).

## Requirements

1. **One role-keyed table of skills and MCP servers per host, rescanned every run (REV-05)**: a shared module of the review
   skill's package holds a closed list of roles, seed rows that map a skill or server name to a role, and the scan.
   - Current: no shared table exists; `skill_scan.py` (GSD config skill) scans skills and lists ponytail names from a hardcoded
     tuple; `detection.cbm_registration` reads one MCP server name per host; five scripts copy the host skill-root list; the
     review and execute paths know no skill at all.
   - Target: roles are a closed list: `review_lens` (read-only advice lenses), `edit_lens` (lenses that change files),
     `ui_lens`, `code_index`, `decision_helper`, `host_control`, `skill_judge`, and `unsorted` for anything without a row. Seed rows
     live in one data file of the review skill's `references/`, each with a role, a `source` label (verified with date or
     unverified) and no decision power. The scan runs on every call and reads: each host's skill roots (claude, codex, opencode,
     cursor, copilot, pi and the shared agents root, honoring the host's own config-dir variables), the enabled Claude plugin
     skills (as the GSD config skill already does), and the MCP server names in each host's own config (names only, never
     values; a malformed or unreadable file is `unknown`, not "none"). The result is per host: `{skills: [{name, role, role_source,
     path, root_kind}], mcp: [{name, role}]}`. A seed row whose skill is not on disk is absent; a skill on disk with no row, no
     user-stated role and no confirmed sort is `unsorted`. Presence is never cached across runs. The GSD config skill reads the
     module through `load_ai_kit_spec_module`; the architecture test's cross-skill allowlist stays frozen.
   - Acceptance: a fixture home with a seed-listed skill missing from disk reports it absent and a fixture skill with no row
     reports `unsorted`; the scan result changes when a skill directory is added or removed between two calls with no cache
     invalidation step; a malformed MCP config reports `unknown` for that host; a test fails when a seed row lacks a source
     label, names a role outside the closed list, or names a model or provider; the role list in code, the seed file and the
     SKILL.md table are compared by one locking test.
   - *Amended 2026-11-23 (Phase 37 R14 shipped; Live facts added 2026-11-23):* REV-05 also picks the MCP servers a lane gets and
     writes the run-scoped file the runner reads (37 R14 left "which servers a task kind needs" to this phase). The pick: a server
     whose table role is `code_index` and whose seed row records a launch form (binary name and arguments, with a source label;
     the seed row for `codebase-memory-mcp` records the bare binary with `--tool-profile=analysis`, documented by its 0.12.1 help,
     effect unverified), for both task kinds (review and execute), only when that binary resolves on the child's PATH. The file is
     built from the resolved binary path and the seed arguments only (`{"mcpServers": {<name>: {"command": <abs path>, "args":
     [...]}}}`), never from a host config value (the scan still reads names only), written mode 0600 into a run directory the
     dispatch removes on every exit path, and passed as `--mcp-config`; whether it applies is the runner's report line. A server
     without a recorded launch form (its definition lives only in a host config) is never enabled and is listed in the block as
     present, not enabled. No other task kind or server role enables a server in this phase.

2. **An optional configuration-time sorter proposes a role for an unknown skill and the owner confirms every sort (REV-05)**.
   - Current: no sorting step exists; an unknown skill has no role anywhere.
   - Target: a read-only `classify-skills` command lists the `unsorted` skills and, when jev is present (probed at runtime through
     its own ladder), asks it one item per skill from the skill's name and its first 300 characters of description only (never the
     skill body, a path or a config value), choosing among the closed roles plus `none of these`. Each proposal prints the role,
     the confidence and the word "advisory". A low, forced or missing answer, or no jev, leaves the skill `unsorted` with no
     proposal. A separate `confirm-skill-role` command writes one sort the owner confirmed into the layered config as a
     `[skills.roles]` entry labeled `user-stated`, atomically, through the existing splicing writer; no command writes a sort the
     owner did not confirm. A confirmed sort beats a seed row. The sorter never runs during a review or an execute run; MCP
     server names are not sent to jev (no description) and are sorted only by seed row or by the owner.
   - Acceptance: a fake jev returns a confident role for one skill and a low answer for another, and only the first shows a
     proposal; with jev absent the command lists every unknown skill and proposes nothing; the confirm command writes one atomic
     `[skills.roles]` entry and a read of the file returns a role labeled `user-stated`; the item sent to the fake jev contains the
     name and description text and no path, key or config value (checked on the recorded request).
   - *Amended 2026-11-23, plan fix pass (read in the code):* "read-only" means `classify-skills` writes no ai-kit config and no
     skill file; the real jev client appends its own answer log under the state home (`jev_review.py:1937-1939`), which is jev's
     record, not this command's write; tests use a fake jev and pin that no ai-kit config changes. *(orchestrator decision
     2026-11-23: CONTEXT D-09's curated-config caller is owned by 39-09: curated-config gains `classify-skills` and
     `confirm-skill-role` subcommands that call the review package's same functions through `load_ai_kit_spec_module`; the D-18 live
     probe is not run (no consent line) and is listed as an owner item in 39-19)*

3. **The runner prints each lane's capabilities from its final argv (REV-04)**: the facts a block needs are computed in the
   runner, in the same place and from the same planner that builds the argv.
   - Current: `--print-argv` prints `runtime`, binary and argv JSON only; no field says whether the lane can write, run a shell,
     load skills or use MCP; Python would have to parse each CLI's flags itself.
   - Target: Phase 37's pure planner (D-11) also returns `capabilities`, computed by one pure function over the row, the role and
     the final argv (including flags added by `extraArgs`): `write` (`none`, `workspace`, `full` or `unknown`), `shell`, `skills`
     (`none`, `path`, `discovery` or `unknown`) and `mcp` (`none`, `host_config` or `unknown`), each with a label (`from argv`,
     verified or unverified with the source flag and the host version and date). `--print-argv` prints one extra
     `capabilities` line (JSON) and `--describe` lists each row's capability form with its source label. A tool list in the argv
     (pi `--tools`, copilot `--available-tools` and `--excluded-tools`, claude `--tools`) decides `shell`; a mode flag that the
     host's own help calls read-only (cursor `--mode ask`, codex `--sandbox read-only`) decides `write` and leaves `shell`
     `unknown` where the help does not say; a fact the argv does not show is `unknown`, never a guess. An unknown runtime and an
     `--argv-file` lane report every field `unknown`. No row blocks a lane; the line is information.
   - Acceptance: a table-driven test runs `--print-argv` for every runtime and both roles and compares the capabilities line with
     the expected values in a recorded fixture; a planted `--tools` entry that adds `bash` to a pi review lane flips `shell`; an
     unknown runtime prints all `unknown`; the sync test of Phase 37 compares the line between the template and the render; a
     doc-contract test lists each field and value.
   - *Amended 2026-11-23 (Phases 37 and 38.1 shipped; Live facts added 2026-11-23):* `planSettings` (`cross-ai.mjs:2122`) is the
     pure planner; its comment already reserves `capabilities` (`:2121`). The line is printed to stderr as `cross-ai: capabilities
     <JSON>` beside the settings lines, because the stdout line is parsed by its three tab fields (`gp_host.py:381-385`). A row field
     `capabilities` appears in `--describe` through the existing per-setting copy (`:6869`). The enums predate Phase 37's report
     lines, so the mapping is: `skills` describes what the host itself loads: `none` when the argv carries `--no-skills` and no
     path form applied, `path` when a `--skill` path form was applied, `discovery` when a name form was applied, else `unknown`;
     the runner's prose blocks are not a host capability and are read from the `form=prose` report lines. `mcp` gains one value,
     `call_file`, when a Phase 37 `--mcp-config` form was applied (from the argv); `none` when the argv turns MCP off (pi
     `--no-mcp`); `host_config` only where a row label says the host reads its own config; else `unknown`. The object also carries
     `prompt` (`{channel: argv|stdin, max_bytes: <int> or null}`, `max_bytes` being the largest prompt the runner admits on argv,
     `ARGV_PROMPT_MAX` minus the resume reserve that `argvPromptProblem` adds, `:3905-3909`) read from the row's `argvPrompt`, so the caller can keep
     lens prose under copilot's argv cap. An unknown runtime cannot reach the line (the runner exits 2 before planning); the Python
     reader (R4) gives every field `unknown` for a non-zero exit, a missing line or an unparseable one, which covers the unknown
     runtime and an old rendered copy.
   - *Amended 2026-11-23, plan fix pass (read in the code and the recorded help):* each field's `label` on the line is an object
     `{state, source}`, the shape of the row forms' labels. pi's `--tools` takes names or patterns (`tests/fixtures/cli_help/pi/help.txt:37`;
     its example `'mcp__radius__*'`, `:126`, names MCP tools only), so of the R3 boundary edge's "a wildcard is `yes`" only a bare `*`
     gives `yes`; any other pattern gives `unknown`, never a guess. copilot review's `--disable-builtin-mcps` disables the built-in
     servers only (`tests/fixtures/cli_help/copilot/help.txt:121-123`), so its `mcp` is `unknown`, not `none` (CONTEXT D-02's
     "no MCP" for copilot review reads as unknown). `planSettings` runs before the formula builds the final argv
     (`cross-ai.mjs:2122-2127`, then the formula at `:7045-7046`), so the "one pure function over the row, the role and the final
     argv" is `laneCapabilities(row, role, argv, report)`, called where the argv is final (the `--print-argv` block); the planner's
     result keeps its shape.
   - *Amended 2026-11-23, orchestrator decision:* R3's field list is `write` (`none`, `workspace`, `full`, `unknown`), `shell`
     (`yes`, `no`, `unknown`), `skills` (`none`, `path`, `discovery`, `unknown`), `mcp` (`none`, `host_config`, `call_file`,
     `unknown`), each `{value, label: {state, source}}`, plus `prompt` (`{channel: argv|stdin, max_bytes}`); `call_file` and `prompt`
     are accepted additions; `--tool-profile=analysis` in the MCP seed launch form keeps its `unverified` label.

4. **Each lane's prompt carries a capability block built from those facts (REV-04)**.
   - Current: `build_tooling_guidance` emits `SHARED_TOOLING_PATH`, `AGENTS_TOOLING_PATH`, a `TOOL_AVAILABILITY` JSON line from
     the parent's PATH and one codebase-memory-mcp line chosen from a host config read, whatever the lane can do.
   - Target: one composer (a new module in the review skill's package) builds the block per lane from the runner's capabilities
     line (read by running `--print-argv` for that lane), the child's PATH and the table of R1, and replaces the guidance call in
     `reviewer_dispatch._reviewer_full_prompt` and `execute_dispatch.build_execute_guidance`. The block states: access (read-only,
     write in the workspace, full write, or unknown), whether a shell tool exists, the tools found on the child's PATH (each tool
     resolved against the PATH of the exact child environment, at dispatch time; listed only when `shell` is `yes` or `unknown`
     and then labeled `if you have a shell`), codebase-memory-mcp only when its binary resolves on that PATH and either a host
     config registers it and `mcp` is not `none` (MCP tool list) or `shell` allows the CLI form (CLI line), never both, skills
     delivered by path or inlined (R5), and the settings actually applied from `--print-argv` (model, effort, context form). A lane
     without a shell is told about no shell tool and no CLI form; a lane without MCP is told about no MCP tool; an `unknown` fact is
     printed as unknown with the words "make no assumption". The names `SHARED_TOOLING_PATH`, `AGENTS_TOOLING_PATH` and
     `TOOL_AVAILABILITY` stay in the block, filtered the same way, because the checklist skill keys off them. The soft-confinement
     sentence for an execute lane is chosen from `write` (not from membership in `OS_SANDBOXED_EXEC`). A native lane (the host runs
     it, no argv) gets no tool claims, only the lens lines of R5. A read-only `capability-block` command prints the block for a
     runtime, model and role without spawning the lane, so any caller (including a GSD hook that passes `--prepend-file`) can use it.
   - Acceptance: fixture blocks for each runtime and role contain exactly the lines its capabilities allow (a pi review block has
     no `rg`, no `bash`, no `codebase-memory-mcp cli` line; a claude review block mentions MCP tools only when the config reader
     says registered); the tool list changes when a fake child PATH adds or removes a tool and does not change when only the
     parent's PATH does; the checklist's named variables are still present; the unknown-runtime block holds only "unknown" facts;
     `capability-block` output equals the block `dispatch-reviewer` prepends (same fixture, byte-equal).
   - *Amended 2026-11-23 (Phase 37 shipped; Live facts added 2026-11-23):* the composer reads the capabilities line, the
     `form=` of each `setting skill=` line, each `setting mcp=` line and each `skill-block ... bytes=` line from one
     `print_argv_lines` call for the lane with its real `--skill-path`, `--skill-name` and `--mcp-config` flags (`RunnerSpec` and
     `runner_flags` gain those fields, emitted after the existing setting flags, so a spec without them gives a byte-equal argv and
     hook string; `SETTING_LINE_RE` gains the optional `form=`). The code index line has three routes, first match wins: the R1
     run-scoped file applied for this call (MCP tool list, "enabled for this call"), a host config registration with `mcp` not
     `none` (MCP tool list, the existing evidence phrase), the CLI form when `shell` is not `no`; never two lines.
   - *Amended 2026-11-23, plan fix pass (read in the code):* route 2 needs `mcp` `host_config` or `unknown`: with a call file applied,
     claude also gets `--strict-mcp-config` (`cross-ai.mjs:1898`), so a host registration proves nothing for that lane. For an
     execute lane whose `write` is `unknown`, the existing soft-confinement sentence states "NO operating-system-level write
     confinement" (`execute_dispatch.py:44-47`), more than an unknown fact supports; by this requirement's rule for unknown facts the
     block gives that lane the same instruction (write only inside the working directory) with "make no assumption" and without
     the confinement claim (39-10 `UNKNOWN_CONFINEMENT_LINE`); `write` `full` keeps the sentence word for word (CONTEXT D-04 note).
     *(superseded 2026-11-23 by the orchestrator decision: D-04's locked sentence is given word for word to every execute lane
     whose `write` is `full` or `unknown`; there is no softer line; `workspace` and `none` get no sentence, as D-04 says. On a claude
     lane the run-scoped MCP file comes with `--strict-mcp-config`, 37 R14's verified form, so it replaces the host's other MCP
     servers for that lane; the docs say so.)*

5. **Lens skills reach each lane by path where it can load them and inlined where it cannot (REV-03)**.
   - Current: no lens reaches a spec-review lane; `ai-kit-spec-review` mentions no lens; the GSD agent wiring (LENS-01) is separate.
   - Target: the lens set is the present skills whose role is `review_lens` (and `ui_lens` only when the files named in the
     prompt include a UI file, by the extension list the superpowers adapter already keeps, not a third copy). A lens is delivered
     by path only when the lane's applied settings carry a skill-path form with a verified or probed label (R6: pi `--skill`);
     otherwise its text is inlined from its file (SKILL.md body), inside a delimited section with its path and sha256. A
     built-in lens with no file (`simplify`) is delivered only to a native lane of its own host by name, labeled unverified; every
     other lane gets a lens note `built_in_no_file`. Lenses are added one by one in table order while the total prompt stays within
     the lane's known window (R7); a lens that would not fit is skipped whole with the note `over_window`, and the base prompt is
     never cut. A lens whose path fails R8 gets the note `path_rejected`. Lens notes are a closed list with a locking test: `built_in_no_file`,
     `over_window`, `path_rejected`, `not_present`, `host_cannot_load`. The block names each delivered lens, how it was delivered
     and each skipped lens with its note.
   - Acceptance: with a fixture skills root, a pi review lane gets lens paths and an `--skill` argument, a copilot review lane gets
     the same lens inlined, a lane with a window of 4,000 tokens skips a 20,000-token lens by name, `simplify` goes only to a
     native Claude lane, and a lens with a control character in its path gets `path_rejected`; the closed list is compared with the
     SKILL.md table; no inlined text is shortened (byte-equal to the file body).
   - *Amended 2026-11-23 (Phase 37 R13 shipped; Live facts added 2026-11-23):* Python no longer inlines lens text. It selects the
     lens set and passes each delivered lens to the runner as `--skill-name <name> --skill-path <dir>`; the runner applies the first
     verified form (name, path, prose) and its `skill=` report line says how the lens was delivered, which the block's SKILLS
     section prints. "Delivered by path only where verified or probed" is the runner's `verified` state (pi `--skill` today); every
     other host gets the runner's prose block, which carries the path and sha256 and is byte-equal to the file (`:6520`). Before a
     lens is passed, the composer checks what the runner would refuse for the whole lane and skips that lens with a note from the
     closed list instead: an empty `SKILL.md` gets `not_present`; a body that is not strict UTF-8, starts with a byte-order mark or
     is over the runner's 65,536-byte read cap, a skill whose directory name and frontmatter name both miss the runner's name shape,
     and a path that fails R8 get `path_rejected`; a lens the runner reports `ignored` gets `host_cannot_load`. The budget loop
     (R7's estimate, table order, skip whole with `over_window`) runs before the flags are chosen and counts each delivered lens's
     bytes whatever its form (a path form loads the file into the host's context too); prose bytes are the runner's block size,
     which a sync test pins equal to the runner's `skill-block bytes=`. Where the capabilities line says the prompt rides argv
     (`prompt.channel` `argv`), the loop also keeps the whole prompt under `prompt.max_bytes`, with the same `over_window` note.
   - *Amended 2026-11-23, plan fix pass (read in the code):* the scan lists only skills on disk, and D-07 seeds `simplify` (a
     built-in with no file) as `edit_lens`, so no scan row can carry it. Its seed row records `built_in: claude`, and lens selection
     takes the role and the lane's native host: a built-in seed row of that role is delivered by name only to a native lane of the
     recorded host (label unverified), else noted `built_in_no_file`; with `simplify` seeded `edit_lens`, that rule applies in the
     R9 pass, and the acceptance case runs with the `edit_lens` role. The concurrency backstop "lens files are read once per
     dispatch" holds for the Python side; the runner reads each `--skill-path` file again at the preview and at the launch
     (`loadSkills`, `cross-ai.mjs:6495-6503`), a stated check-then-use limit like R8's. The acceptance case "a lane with a window of
     4,000 tokens skips a 20,000-token lens" is tested on the budget function with the size given: a real 20,000-token body
     (about 80,000 bytes) is over the runner's 65,536-byte read cap, so in a dispatch it gets `path_rejected` before the budget runs.

6. **A runner setting passes skill paths where a host has a form (REV-03, REV-04)**.
   - Current: the runner has no way to give a lane a skill path; pi review argv carries `--no-skills`.
   - Target: a repeatable runner setting `--skill-path <dir>` joins Phase 37's settings report: it is `applied` only where the
     row has a form with a source label, `ignored` with `no_form` or `unverified_form` otherwise, and the path must lie inside
     the working tree or a skill root (the same check as R8). Forms: pi `--skill <path>` (verified from its own docs, pi 1.5.2,
     2026-11-16); claude, copilot and cursor-agent `--add-dir <path>` (flag verified from each host's help; the effect on a
     read-only lane is unverified until the execute-start spike below, so the form is `unverified_form`, reported and not fed);
     codex, opencode and the others none. The capability line of R3 reports `skills=path` only when a form was applied. An
     execute-start spike (one cheap call per primary host: claude, opencode, pi) records whether a review lane reads a lens file
     outside the repository with and without the form, and updates the rows' labels; a host the spike does not cover stays
     unverified and inlines.
   - Acceptance: `--print-argv` with `--skill-path` for pi adds `--skill <path>` and reports it `applied`; for claude it reports
     `ignored unverified_form` and the argv is unchanged; an unknown runtime reports `ignored no_form`; a path outside the allowed
     roots is a usage error naming the path; the recorded-help flag test of Phase 37 covers the new flags.
   - *Amended 2026-11-23 (Phase 37 R13 shipped; Live facts added 2026-11-23):* the setting exists: `--skill-path` and `--skill-name`
     with the per-host forms, labels and report lines of 37 R13, and pi `--skill <path>` applied. What 37 shipped differs from this
     text in two places, and the shipped behaviour stands: a host whose path form is `unverified` (claude, copilot) or unknown
     reports `applied form=prose` with the argv unchanged, not `ignored unverified_form`; and an unknown runtime is a usage error
     (exit 2), not `ignored no_form`. The repository-or-skill-root check stays the Python validator's (R8), as 37 R13 assigned it:
     the runner never scans a host, so it cannot know a skill root. This phase's runner work for R6 is the control-character half
     of the edge row below: `--skill-path` and `--skill-name` values are checked against R8's full character set (Cc, Zl, Zp and the
     listed format code points) instead of C0 and C1 only, pinned equal to the Python validator by one shared fixture. The D-18
     spike is not run in this run (live host calls need an owner consent line that is absent), so every path form keeps its label
     and those hosts get prose.

7. **A prompt larger than a lane's known window is refused for that lane before it is spawned, never trimmed (REV-04)**.
   - Current: nothing compares a prompt with a window; the host's own `context_length_exceeded` answer (38.1) comes after the
     call.
   - Target: before spawning, `dispatch-reviewer` and `dispatch-execute` compute the prompt's token estimate (UTF-8 bytes divided
     by a fixed bytes-per-token constant chosen to under-count, labeled `estimated` and `judged`; the guidance block, the lens text
     and the prompt count; the runner's preamble and the host's own system prompt do not, a stated limit) and compare it with the
     lane's window: the integer from the Phase 35 catalog for (runtime, model) with its label, or the user's `[[models.context]]`
     override (user-stated, which beats the catalog). The prompt is refused when the estimate exceeds the window (equal passes).
     A window that is absent shows `unknown` and is never capped. When the lane's final argv applies a context form whose effect on
     the window is unverified (cursor bracket, codex key, copilot tier, per 37 D-15 and D-22), the window is `unknown` for that
     lane with the note `context_form_applied`, unless the user stated one. A refusal is a result record `{status: refused,
     reason, detail}` with the estimate, the window, the window's label and source, no child spawned and a distinct non-zero exit
     that reuses no runner exit code; the review loop reports that lane as failed (the lane switch and the closed ping reasons
     are Phase 40's, which reuse this list). The reasons are a closed list with a locking test: `prompt_over_window`,
     `value_control_char`, `path_outside_roots`, `path_unresolvable`; disjoint from Phase 37's setting reasons, Phase 38.1's
     error classes and the lens notes. A refusal never alters the prompt, never changes the lane's model or runtime and never
     cancels another lane.
   - Acceptance: fixtures: a prompt over a stated window is refused with the numbers and no spawn; a prompt of exactly the window
     passes; no window shows `unknown` and runs; a user override beats a catalog value; an applied context form with an
     unverified effect shows `unknown`; the refusal result carries a reason from the closed list; two lanes with different windows
     get independent outcomes in one review; the list is compared with the SKILL.md table and the disjointness test.
   - *Amended 2026-11-23 (Phases 35, 37 and 38.1 shipped; Live facts added 2026-11-23):* the window is read by one new accessor over
     the cached catalog (the `resolve_route` pattern): the live `[[models.context]]` override first (`catalog_context.override_for`,
     label `user-stated`), then the catalog runtime row's `context` fact with its label and source; anything else is `unknown`.
     The refusal exit is 65 (free in `STATUS_TABLE`; 69 now also carries 38.1's `bad_request`). The disjointness test covers
     `SETTING_REASONS`, `ROW_CLASSES` and the `--describe` `classes` keys, `FINDING_CODES` and the lens notes. The runner's prose
     blocks are part of what is sent: the estimate counts them as R5's amendment says.
   - *Amended 2026-11-23, plan fix pass (read in the code):* a context form can also ride in the model id: the runner prints a
     `setting context=` line only when a context is requested (`cross-ai.mjs:2027-2029` returns first), and the dispatch never
     requests one (`runner_dispatch.py:104-105`, `context=None`); so a lane model id that carries the row's bracket context form
     counts as an applied context form for this check (39-06 `window_for`), which makes that lane's window `unknown` unless the user
     stated one. That is conservative: it never refuses a lane.

8. **A value embedded in a prompt that holds a control character or points outside the repository or skill roots is rejected
   (REV-04)**.
   - Current: the review prompt embeds the document path and lens-less guidance paths unchecked; the files named in a plan or a
     findings list are embedded as given.
   - Target: one validator checks every value the composer or the dispatch embeds (file lists, plan and spec paths, lens paths,
     the guidance paths): a value is rejected when it holds a control character (Unicode categories `Cc`, `Zl`, `Zp` and the
     bidirectional and zero-width format characters U+200B to U+200F, U+202A to U+202E, U+2060 to U+2064, U+2066 to U+2069 and
     U+FEFF), is empty or not a string, cannot be resolved, or its resolved real path lies outside the repository root of the
     dispatch's working directory and outside every skill root the scan of R1 found (a symlink is resolved first, so a link out
     of a root is rejected). The rejection names the value's position and reason (`value_control_char`, `path_outside_roots`,
     `path_unresolvable`) and shows the value with control characters escaped. The validator rejects, it does not rewrite.
   - Acceptance: fixtures for a path with a newline, a bidi override, an empty string, a non-string, a symlink that leaves the
     repository, a path in a sibling checkout, a path inside a skill root and a path inside the repository; the first six are
     rejected with the right reason and the last two pass; a rejected value never reaches the prompt.
   - *Amended 2026-11-23 (Phase 37 shipped; Live facts added 2026-11-23):* the values also include each `--skill-path` and
     `--mcp-config` path the dispatch passes to the runner (the run-scoped MCP file lives under the run directory, which counts as
     inside the allowed roots only for that one value). The runner's own `CONTROL_CHAR_RE` is C0 and C1 only; R6's amendment widens
     the runner's skill checks to this set.
   - *Amended 2026-11-23, plan fix pass (read in the code):* the agents-tooling guidance path resolves to the machine-level
     `~/.agents/AGENTS-TOOLING.md` (`detection.resolve_agents_tooling_path`, `detection.py:1359-1365`), outside every repository and
     skill root, so refusing a lane for it would refuse every lane on a normal machine. The two guidance paths
     (`SHARED_TOOLING_PATH`, `AGENTS_TOOLING_PATH`) are composer-chosen context, not caller input: one that fails this validator is
     not embedded, and its block line reads `<NAME>: omitted (<reason>)` with the reason from this list (R4's edge row "an absent
     agents-tooling file omits its line"). Every caller-supplied value (document, plan, spec and file-list paths, a skill path, the
     MCP file) that fails is refused for the lane under R7 (exit 65). Nothing is rewritten in either case. A labeled
     multi-worktree review runs in the first document's worktree (spec-review SKILL.md:321-322), so a document in another worktree
     lies outside the dispatch's repository root: as the edge row for a sibling checkout says, it is rejected
     (`path_outside_roots`), never passed around the validator; the skill text tells the caller to review such a set one worktree
     at a time. The checklist and framework-profile paths the review skill writes into its own prompt text lie in the installed
     skill's directory, a skill root, and are passed in the file list like every other embedded path. A path that does not exist
     yet (an execute plan names files it will create) is not unresolvable: its existing parent folders and links are resolved and
     the containment check applies to that real parent; `path_unresolvable` is for a value whose resolution fails (39-03).
   - *Amended 2026-11-23, orchestrator decisions (supersede the two fix-pass sentences they name):* (a) never remove a feature: a
     document from another worktree in a labeled multi-worktree review is NOT refused; the worktree root of each document the
     caller names is an allowed root for that document value only, and the block's note reads `documents from other worktrees:
     <n> (<root>, ...)`; this supersedes "it is rejected ... one worktree at a time" above; a sibling checkout not named as a review
     document is still rejected. (b) A dispatch called without `--files` keeps today's behaviour: no refusal and no capability
     block, with one stderr note naming the missing flag (R8's empty edge row, amended); exit 65 stays for a real refusal (a prompt
     over the lane's known window, and a rejected value that is embedded). (c) An invalid guidance path is omitted and also named
     in the summary line (`; note: guidance omitted: <NAME> (<reason>)`).
   - *Amended 2026-11-23, phase 39 code review (read in the code, `skill_table.skill_roots`; 39-REVIEW.md HIGH-1):* each skill
     directory the scan finds is a skill root too, so a skill directory linked into a host root (ai-kit's installer links every
     skill directory) passes, and the installed review skill's checklist, framework-profile and tooling-guidance paths lie inside
     the roots as the fix-pass note above assumes; a `SKILL.md` linked out of a real in-root directory and a link inside the
     repository are still outside. Before the review only the host roots counted, which refused every subprocess review outside
     the ai-kit checkout. The owner confirms this reading (todo `review-notes-left-open-by-phase-39`). In decision (a) the
     other-worktree allowance applies to review lanes only (an execute lane's file there is still outside).
   - *Amended 2026-11-23, orchestrator decision (never remove a feature; read in the code, `capability_block.profile_cache_root`):*
     the review skill's learned framework-profile cache (`~/.claude/cache/framework-profiles`, SKILL.md `CACHE_DIR`) is an
     allowed root for `--files` and guidance values, so a review that embeds a learned profile runs as before phase 39; a sibling
     folder and a link out of the cache are still outside.

9. **File-editing lenses run as an optional pass after approval (REV-03)**.
   - Current: no lens runs after a review; the review loop ends at approval.
   - Target: after the reviewers approve, a pass may run the present `edit_lens` skills on a lane whose capabilities show
     `write` of `workspace` or `full`, with the file list validated by R8, the block's lens delivery (R5) and a prompt that names
     the approved files only. The pass is off unless `[review] edit_lens_pass` is true in the layered config; an unattended run
     does not enable it. When it runs, its edits are left uncommitted in the working tree, the loop prints the diff summary and the
     owner accepts or rejects them before the review counts as finished; a rejection restores the files from the recorded
     pre-pass content. A lane with `write` of `none` or `unknown` is not used for the pass.
   - Acceptance: with the key unset no pass runs and the review result is unchanged; with it set and a fake write-capable lane the
     pass records the pre-pass content, the diff summary is printed and a rejection restores byte-equal files; a read-only lane
     is never chosen; a rejected path (R8) is skipped by name.
   - *Amended 2026-11-23 (owner decision; Live facts added 2026-11-23):* the default-off key with a diff the owner accepts is
     confirmed (`OWNER-DECISIONS-2026-11-16.md:52-54`); the provisional mark of D-14 is lifted. The run lock is the runner's, taken
     in execute mode, so the pass runs as an execute-role runner call. *(orchestrator decision 2026-11-23: today only codex lanes show a
     write capability, codex exec `full` and codex with `--codex-sandbox workspace-write` `workspace` (39-02's capability values), so
     the pass runs only on those; recorded, accepted)*

10. **The GSD config skill reads the shared table (REV-05)**.
    - Current: `skill_scan.ponytail_visibility` answers from a hardcoded name tuple over `host.HOSTS`; `inventory.py` has no
      role field.
    - Target: `inventory` gains a `skill_roles` field built from the shared table (through `load_ai_kit_spec_module`) and
      `ponytail_visibility` is derived from it with the same output shape and the same hosts it covers today, so plan files that
      validate the old shape are unchanged; the hardcoded `PONYTAIL_SKILLS` tuple is removed. Lens wiring from the table is
      Phase 44's. A missing review package leaves `skill_roles` absent with the existing "module unavailable" note, never an
      error.
    - Acceptance: on a fixture home the derived `ponytail_visibility` equals the old output byte for byte; the inventory carries
      `skill_roles` for each host; a copilot fixture appears in `skill_roles` while `ponytail_visibility` keeps its five hosts;
      with the review package missing the inventory still builds and says so.
    - *Amended 2026-11-23, plan fix pass (read in the code):* the old `ponytail_visibility` scans the skill roots GSD reports
      (`skill_scan.py:293-306`; gsd-core maps codex to `~/.agents/skills`, `runtime-homes.cjs:509-534`), while `skill_roles` reads
      ai-kit's own host roots, and the plugin names `ponytail-gain` and `ponytail-help` have no seed row; so byte-equal output is
      reached by deriving the visibility from the shared module's root scan over GSD's roots with the name rule `ponytail` or
      `ponytail-*` (39-09), not from the `skill_roles` field. With the whole review package missing, the inventory already stops at
      `host.resolve_gsd_core` (`host.py:126-128`, `SIBLING_MISSING`) before any skill field is built, an existing behaviour this
      phase does not change; the acceptance is met for the case this phase adds: the review package present without its
      `skill_table` module leaves `skill_roles` absent with a warning and the inventory builds.

11. **Review and execute share one builder and the spec-config flow shows it (REV-04, REV-05)**.
    - Current: spec-review and the execute adapter each call the guidance composer with their own arguments; the owner picking a
      lane in spec-config sees no capability view.
    - Target: `dispatch-reviewer`, `dispatch-execute` and `capability-block` call the same builder with the same arguments for the
      same lane (a test pins it). The read-only `check-reviewer` and `config-status` style outputs of Phase 36 print one capability
      summary line per lane from the same builder (read-only, no spawn), so the owner sees what a lane can and cannot do before
      choosing it. herdr is not used: the summary is plain text the skill prints; the review skill's own pane use is unchanged.
    - Acceptance: one test compares the three entry points' output for a fixture lane; the summary line appears in the
      spec-config check output for a fixture config and is absent from no lane.
    - *Amended 2026-11-23 (Phase 36 shipped; Live facts added 2026-11-23):* `check-reviewer` prints one JSON object, so its summary
      is one more string key, `capability`, in that object; `config-status` prints per-layer lines, so it gains one
      `capability <runtime>/<model> <role>: <summary>` line per lane of the resolved `[lanes]` table after them. Both come from the
      builder with no spawn of the lane (the `--print-argv` call is the runner's read-only dry run). *(plan fix pass, read in the
      code: the lane resolver drops a stored `route` field (`_combine_role` calls `_drop_stored_routes`, `config_io.py:680-691`), so a saved lane counts as native only when it has
      neither a runtime nor a command; its summary reads `native lane, no tool claims`)*

12. **Skill text, docs, closed lists and the judge bar (JDG-04, HUB-09)**.
    - Current: `ai-kit-spec-review/SKILL.md`, `references/tooling-guidance.md`, `reviewer-prompts.md` and `cross-ai-dispatch.md`
      describe the parent-PATH tool map and no lens; `ai-kit-spec-config/SKILL.md` has no sorting step.
    - Target: `ai-kit-spec-review/SKILL.md` documents the capability block, the lens delivery rules, the refusal result and the
      optional after-approval pass (history in a trailing section); `ai-kit-spec-config/SKILL.md` gains the sorting step (jev
      present and absent paths, the owner's confirmation, the confirm command); the superpowers adapter's SKILL.md changes only if
      its dispatch text names the old tool map; `tooling-guidance.md`, `reviewer-prompts.md`, `cross-ai-dispatch.md` (the
      `detect-tools` step becomes the child-PATH rule), the READMEs and the config documentation for `[skills.roles]`,
      `[review] edit_lens_pass` and the existing `[[models.context]]` follow. Every SKILL.md changed meets the judge bar (new-shape
      evals and tests, no critical or high finding or grade B or better, no regression beyond variation); `ai-kit-spec-review`
      keeps the bar Phase 36 set. The hardcoding guard passes on every file this phase changes; no skill, rail or default names a
      model or provider other than `router-env/<x>`.
    - Acceptance: the judge loop ends with no critical or high finding or a B or better (recorded in 39-VERIFICATION.md); doc-contract
      tests pin the three closed lists (roles, refusal reasons, lens notes), the block's section names and the config keys;
      `make test` passes.
    - *Amended 2026-11-23 (Phases 37 and 38.1 shipped; Live facts added 2026-11-23):* the docs describe lens delivery through the
      runner's forms and report lines (R5's amendment), the MCP pick (R1's amendment) and the new capabilities values; the
      `ai-kit-cross-ai` SKILL.md, which documents the runner's lines, joins the judge loop only if its text changes. The dated notes
      in REQUIREMENTS.md (REV-03 to REV-05) and ROADMAP.md (Phase 39) for these amendments are a plan task, as 38.1 did.

## Boundaries

**In scope:**
- The shared role table, its scan and the optional sorter with owner confirmation (R1, R2, R10), the capability line in the
  runner (R3), the block builder and its entry points (R4, R11), lens delivery and the skill-path setting (R5, R6), the pre-spawn
  window check and the embedded-value validator (R7, R8), the optional after-approval pass (R9), skill text, docs and the judge
  bar (R12).

**Out of scope:**
- Lane switching, the closed ping-reason list, resilient review and jev picking lanes (Phase 40; it reuses this phase's refusal
  reasons), the loop changes beyond the after-approval pass step (Phase 40 owns the loop).
- The host's `context_length_exceeded` answer after a call (Phase 38.1's `bad_request`), setting reasons and forms (Phase 37 and
  38.1; this phase adds one setting and one capability line to that surface), the catalog and window source (Phase 35).
- Lens wiring into GSD agents from the table and the vertical-slices runbook (Phases 44 and 45), the superpowers adapter's use of
  lenses at `receiving-code-review` (Phase 42, EXE-02).
- A GSD hook route that passes `--prepend-file`: the `capability-block` command makes it possible, but the pre-spawn window
  refusal is Python-side only, and wiring a rendered hook to generate the block file or to carry a window to the runner is
  Phase 44's (the runner never reads the catalog).
- Replacing the five existing host skill-root copies and the `RUNTIMES` or `CBM_REGISTRATION_KEYS` seed tables (listed as
  findings; none of them decides a lane here).
- Verifying path reading on hosts other than the three primary ones, probing every model's window, tokenizers per model.

## Constraints

- Runtime code stays stdlib-only; the sorter reaches jev only through its own ladder client and never imports it silently.
- The runner stays plain Node, calls no jev, no herdr, no network and no catalog; the capability line and the setting are pure
  functions of the row, the role and the argv.
- Every config write (`[skills.roles]`) is atomic through the existing writer; JSONC surgical edits preserve other bytes.
- Tests run in a scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1`, read no `.planning/` path, call no real host and use fake runner
  output and a fake jev; live checks are recorded spikes under `tmp/`.
- No diagnostic or label is shown with more certainty than its source: every capability, form and window carries its label, and
  `unknown` is a first-class value. The token estimate is labeled estimated and judged.
- Skill content and MCP names are untrusted data: a skill description goes to jev as data only, a skill body is inlined only for
  a lens the table names and between delimiters, and nothing read from a skill is run.
- The embedded-value validator rejects; nothing in this phase trims, rewrites or silently drops a prompt, a path or a lens.
- English only; the hardcoding guard applies; skill names and tool names are allowed, model and provider names are not.
- A SKILL.md describes behavior; provenance and version history live in a trailing section. The runner template version is bumped
  by the plan so pristine copies upgrade, and the live copy is re-rendered with `make check-dogfood` closing the step. *(amended
  2026-11-23: template 11 to 12 in the phase's last code wave, the 38.1-12 shape; see "Live facts added 2026-11-23")*

## Acceptance Criteria

- [ ] The shared table reports presence from the scan only, marks unmatched skills `unsorted`, reads MCP names without values,
      and one test locks the role list across code, seed file and SKILL.md (R1).
- [ ] The sorter proposes only with a confident jev answer, shows confidence and "advisory", and writes only a confirmed sort as
      `user-stated` (R2).
- [ ] `--print-argv` prints a capabilities line for every runtime and role, `unknown` where the argv does not show a fact, and a
      planted tool flag changes it (R3).
- [ ] Each lane's block tells it only what its capabilities allow, resolves tools against the child's PATH, names codebase-memory-mcp
      only when its binary is on that PATH, and is byte-equal across the three entry points (R4, R11).
- [ ] Lens delivery follows the rules, inlines unmodified text, skips a non-fitting lens whole with a named note and never
      cuts the base prompt (R5, R6).
- [ ] A prompt over a known window is refused before spawn with the numbers, an unknown window is not capped, and a bad embedded
      value is rejected with a reason from the closed list (R7, R8).
- [ ] The after-approval pass is off by default, runs only on a write-capable lane, shows the diff and restores on rejection (R9).
- [ ] The GSD config skill's lens visibility is derived from the shared table with unchanged output (R10).
- [ ] The three closed lists and the config keys are doc-contract pinned, the changed SKILL.md files meet the judge bar, the guard
      passes and `make test` passes (R12).

## Edge Coverage

**Coverage:** 64/64 applicable edges resolved · 0 unresolved (64 engine rows from `edge_floor.py floor`) *(amended 2026-11-23: R5 gained 2 engine rows and, in the plan fix pass, R7 and R8 gained 1 each, each marked `(added 2026-11-23 ...)`, 68/68)*

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| boundary | R1 | ✅ covered | A host with zero skill roots or zero MCP entries yields empty lists, a skills root holding one directory without a SKILL.md yields none for it, and a 300-character description is read in full while a 301st character is cut by the existing `DESCRIPTION_MAX` |
| adjacency | R1 | ✅ covered | The same skill name under two roots (agents root and claude root) is two rows with their own `path` and `root_kind`; a seed row and a user-stated role for one name resolve to the user-stated role |
| empty | R1 | ✅ covered | A missing root, an empty plugin manifest and an absent config each give an empty list and no error; an unreadable config gives `unknown` for MCP of that host only |
| encoding | R1 | ✅ covered | Names are matched exactly (`SKILL_NAME_RE` fullmatch, case-sensitive); a name with a character outside the pattern is not addressable and is listed `unsorted` with `addressable: false` |
| ordering | R1 | ✅ covered | Rows are sorted by (root kind, root, name) as `scan_skills` does today; the sort is pinned by a test |
| precision | R1 | 🧪 backstop | No numeric tolerance; description length is a fixed cut |
| concurrency | R1 | ✅ covered | The scan is read-only with no shared state; two parallel scans of one home give equal results (a test runs two calls over one fixture) |
| adjacency | R2 | ✅ covered | A skill that already has a seed row or a user-stated role is not offered to the sorter; a skill sorted once is not asked again |
| empty | R2 | ✅ covered | No unsorted skill gives an empty proposal list and no jev call; an empty description sends the name only |
| encoding | R2 | ✅ covered | The description is sent as UTF-8 text with control characters removed and cut at 300 characters; the recorded request is checked for that |
| ordering | R2 | 🧪 backstop | Proposals follow the table's sort order; a re-ask by jev may differ in confidence, never in what is written |
| concurrency | R2 | ✅ covered | `confirm-skill-role` writes through the atomic splicing writer; two confirms of different names both survive a read-modify-write (a test writes twice) |
| boundary | R3 | ✅ covered | An empty tool list (`--tools ""`) is `shell: no`; `--tools` naming only read tools is `no`; a name list containing `bash` or a wildcard is `yes`; a list the row cannot parse is `unknown` |
| adjacency | R3 | ✅ covered | A tool list and an exclusion list that name the same tool (copilot `--available-tools` with `--excluded-tools`) resolve to excluded; the test pins the copilot review argv |
| empty | R3 | ✅ covered | An argv without any tool or mode flag gives `unknown` for write and shell, never `yes` |
| encoding | R3 | ✅ covered | Flags are compared as exact ASCII strings and `--flag=value` forms are split once; a value with a comma list is split on commas only |
| ordering | R3 | ✅ covered | Later flags in the final argv win over earlier ones for the same option, as the host's own parser does where known; otherwise the field is `unknown` |
| precision | R3 | 🧪 backstop | Values are a closed enum, no numbers |
| concurrency | R3 | 🧪 backstop | `--print-argv` is a pure read that migrates and writes nothing (the existing WR-53 guarantee) |
| adjacency | R4 | ✅ covered | When the MCP registration and the CLI form are both possible the block prints one line only (never both for one lane), as the current builder does |
| empty | R4 | ✅ covered | A lane with no known fact prints only the "unknown, make no assumption" lines; no PATH tool found prints no tool line; an absent agents-tooling file omits its line |
| encoding | R4 | ✅ covered | The block is UTF-8 text; every path in it passes R8; the `TOOL_AVAILABILITY` JSON keeps sorted keys and compact separators so the prompt is stable across runs |
| ordering | R4 | ✅ covered | Section order is fixed (lane, access, tools, code index, skills, settings) and pinned by the fixture comparison |
| concurrency | R4 | ✅ covered | Two lanes of one review build independent blocks from their own argv and child PATH; no shared mutable state |
| adjacency | R5 | ✅ covered | Two lenses with the same name on two roots resolve to the first root in the scan order and the second is not delivered again |
| empty | R5 | ✅ covered | No present lens gives no lens section and no note; a lens with an empty SKILL.md is delivered as an empty body with a `not_present` style note named by the test *(amended 2026-11-23: the runner refuses an empty SKILL.md for the whole lane, `cross-ai.mjs:6499`, so the lens is not passed and gets the note `not_present`)* |
| boundary | R5 | ✅ covered | A lens body of exactly 65,536 bytes is passed and one byte more is skipped with `path_rejected` (the runner refuses `n > FILE_READ_MAX`); on an argv lane a prompt with its prose blocks of exactly `prompt.max_bytes` passes and one byte more skips the last lens with `over_window` (added 2026-11-23: R5's amendment names the runner's read cap and argv cap, and its edge floor gained this row) |
| precision | R5 | 🧪 backstop | Every size is an integer byte count compared with `>` as the runner does; no tolerance (added 2026-11-23: same reason) |
| encoding | R5 | ✅ covered | An inlined body is read as strict UTF-8 and embedded unmodified between delimiters with its sha256; a body that fails UTF-8 gets `path_rejected` for its path, not a lossy decode |
| ordering | R5 | ✅ covered | Lenses are added in table order (role, then name), and the budget rule keeps that order; a skipped lens does not reorder the rest |
| concurrency | R5 | 🧪 backstop | Lens files are read once per dispatch; an edit during the call has no effect until the next call |
| adjacency | R6 | ✅ covered | Two `--skill-path` values naming the same directory apply once; a path that is also inside the working tree is applied as given |
| empty | R6 | ✅ covered | No `--skill-path` leaves the argv byte-equal to Phase 37's; an empty value is a usage error naming the flag |
| encoding | R6 | ✅ covered | The value is checked by the same validator rules as R8 inside the runner (a plain-Node copy of the control-character and root checks, pinned equal to the Python rule by a shared fixture) *(amended 2026-11-23: the control-character half only; the root check stays Python's, 37 R13, see R6's amendment)* |
| ordering | R6 | ✅ covered | Several paths are passed in the order given, each as its own flag occurrence |
| concurrency | R6 | 🧪 backstop | Pure argv planning, no state |
| boundary | R7 | ✅ covered | Estimate equal to the window passes, one token more is refused; a window of zero or a non-integer is not a known window (shown unknown); the estimate of an empty prompt is zero |
| adjacency | R7 | ✅ covered | Windows from the catalog and a user override for the same (runtime, model) resolve to the override; a catalog value with no label is shown with label unknown and still refuses (an exact integer is a fact) |
| empty | R7 | ✅ covered | An empty prompt is not refused by this check (the runner's `empty_stdin` owns it); a lane with no catalog entry shows `unknown` and runs |
| encoding | R7 | ✅ covered | The estimate counts UTF-8 bytes divided by the constant, rounded up; multi-byte text counts its bytes, which under-counts dense scripts and is stated as the limit |
| ordering | R7 | ✅ covered | The check runs after the block and lens text are composed and before the spawn; it is the last step so it sees the real prompt |
| precision | R7 | ✅ covered | The estimate is an integer from `ceil(bytes / constant)`; the refusal detail prints estimate, window, label and the constant, so a reader sees the rounding rule |
| concurrency | R7 | ✅ covered | Two lanes of one review get independent window checks, each from its own preview and model id; one lane's refusal never changes or cancels another (the two-lane acceptance test) (added 2026-11-23: R7's plan fix-pass note changed its text and its edge floor gained this row) |
| adjacency | R8 | ✅ covered | A path equal to the repository root passes, a path that only shares a name prefix with a root (`repo-other`) is outside (compared by path components, not by string prefix) |
| empty | R8 | ✅ covered | An empty or whitespace-only value, a non-string and a missing file list are rejected with a reason, never treated as "no files" silently *(amended 2026-11-23, orchestrator decision: a dispatch called without `--files` keeps today's behaviour: no refusal and no capability block, with the stderr note `ai-kit-spec: no capability block built: no --files given (pass --files to get the lane's capability block)`; it is not treated as "no files" silently because the note names it)* |
| encoding | R8 | ✅ covered | Control characters are matched by Unicode category and the listed code points after no normalization; a non-NFC name is compared as given (the filesystem decides equality) |
| ordering | R8 | ✅ covered | The first bad value in the list is named with its position; all bad values are reported in one result so a caller fixes them together |
| concurrency | R8 | 🧪 backstop | A path can change between check and spawn (check-then-use); the validator runs immediately before the spawn and the limit is stated |
| idempotency | R8 | 🧪 backstop | Validating the same values twice gives the same rejections in the same order; the validator reads paths and writes nothing (added 2026-11-23: R8's plan fix-pass note changed its text and its edge floor gained this row) |
| adjacency | R9 | ✅ covered | An approved file that a lens would edit and that is also on a rejected path is skipped by name, the others continue |
| empty | R9 | ✅ covered | No present `edit_lens` skill, or an empty approved file list, runs no pass and says so |
| encoding | R9 | ✅ covered | Pre-pass content is stored as bytes and restored as bytes (a test restores a file with non-UTF-8 content) |
| ordering | R9 | ✅ covered | The pass runs strictly after the final approval record; the diff summary prints before the owner's accept or reject |
| concurrency | R9 | ✅ covered | The pass takes the Phase 38 run lock through the runner (a held lock is `locked`, not an edit); restoring happens only for files the pass recorded |
| adjacency | R10 | ✅ covered | A skill present under two hosts' roots appears once per host in `skill_roles` and once in the derived visibility of each host that has it |
| empty | R10 | ✅ covered | A host with no skills root gives an empty list in both fields as today |
| encoding | R10 | ✅ covered | Output stays JSON with the same key set; the validator of plan files is unchanged |
| ordering | R10 | ✅ covered | Names stay sorted within a host as `ponytail_visibility` sorts them today |
| concurrency | R10 | 🧪 backstop | Inventory is a read-only scan |
| adjacency | R11 | ✅ covered | The three entry points differ only in who calls them; their output for one lane is compared byte for byte |
| empty | R11 | ✅ covered | A config with no lanes prints no summary line and no error |
| encoding | R11 | 🧪 backstop | Plain text lines |
| ordering | R11 | ✅ covered | Summary lines follow the lane order of the config |
| adjacency | R12 | ✅ covered | Each role, each refusal reason and each lens note has exactly one SKILL.md table row; the doc-contract test compares the sets |
| empty | R12 | ✅ covered | A changed SKILL.md with no evals fails the judge bar |
| encoding | R12 | 🧪 backstop | Plain Markdown and test text |
| ordering | R12 | ✅ covered | The table row order is pinned by the doc-contract test |
| concurrency | R12 | 🧪 backstop | The judge loop runs per skill and shares no state |

## Prohibitions (must-NOT)

**Coverage:** 10/10 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT let a seed row, a role or a table decide that a skill or server is present, or block a lane: presence comes from the scan, and a row never refuses anything | R1 | resolved | verification: test — a seed-listed skill missing from the fixture home is absent, and a runtime outside every table still gets a block |
| MUST NOT send a skill body, a path, a config value or an MCP server name to jev, and MUST NOT write a role the owner did not confirm | R2 | resolved | verification: test — the recorded request holds name and description only, and no command writes an unconfirmed sort |
| MUST NOT state a capability the final argv does not show: a fact the argv leaves open is `unknown`, and the block never tells a lane about a tool its capabilities exclude | R3, R4 | resolved | verification: test — a pi or copilot review block holds no shell tool, no `rg` advice and no CLI form, and an argv with no tool flag prints `unknown` |
| MUST NOT resolve a tool against the parent's PATH for a lane block, or name codebase-memory-mcp when its binary is not on the child's PATH | R4 | resolved | verification: test — a fake child PATH without the binary yields no code-index line even when the parent's PATH has it |
| MUST NOT trim, cut, rewrite or silently drop the base prompt, a path or an inlined lens; a lens that does not fit is skipped whole and named | R5, R7, R8 | resolved | verification: test — an inlined body is byte-equal to its file, an over-window lens appears as a note, and a refused prompt is unchanged |
| MUST NOT deliver a lens by path where the lane's applied settings carry no verified or probed path form, and MUST NOT present an unverified form as applied | R5, R6 | resolved | verification: test — copilot and claude fixtures report `unverified_form` and inline the lens |
| MUST NOT refuse a lane on an unknown window or on a window whose context form has an unverified effect, and MUST NOT let a refusal change another lane, the model or the runtime | R7 | resolved | verification: test — an unknown window runs, an applied context form shows `unknown`, and two lanes in one review get independent results |
| MUST NOT embed a value with a control character or a real path outside the repository and the skill roots, and MUST NOT rewrite such a value to make it pass | R8 | resolved | verification: test — the rejection fixtures including a symlink out of a root and a sibling-prefix path *(amended 2026-11-23, orchestrator decision, never remove a feature: the worktree of a document the caller names in a labeled multi-worktree review is an allowed root for that document's value only, named in the block's note; any other path outside the roots is still rejected)* |
| MUST NOT run a file-editing lens pass unless the owner enabled it, on a lane that is not write-capable, or keep its edits without the owner's acceptance | R9 | resolved | verification: test — key unset runs nothing, a read-only lane is never chosen, a rejection restores byte-equal files |
| MUST NOT call jev, herdr, the network or a real host from the runner or from any test, and MUST NOT use a model or provider name other than `router-env/<x>` in code, seed rows, fixtures or docs | R2, R3, R12 | resolved | verification: test — the module tripwire, the arch rule that the template names neither client, and the hardcoding guard |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.86  | 0.75 | ✓      | Roadmap goal, REV-03 to REV-05, four prior phases' handoffs and the live argv per host |
| Boundary Clarity   | 0.84  | 0.70 | ✓      | Lane switching and the loop to 40, hook-route wiring to 44, context-exceeded to 38.1, forms to 37 |
| Constraint Clarity | 0.80  | 0.65 | ✓      | stdlib, labels on every fact, runner pure, rejection never rewrites, GSD hook limits stated |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | Each requirement ties to fixture output, a locking test or a doc-contract pin |
| **Ambiguity**      | 0.16  | ≤0.20| ✓      | 1 − (0.35×0.86 + 0.25×0.84 + 0.20×0.80 + 0.20×0.82) |

Open for the plan (not blocking): the bytes-per-token constant's calibration against recorded host usage; whether a read-only claude
plan lane or an opencode plan agent can run a shell (unverified: `shell` stays `unknown` until the spike); the exact `skill_roles`
inventory field shape; the UI extension list's single home (reuse of the adapter's list); the execute-start spike's three hosts.
*(amended 2026-11-23, from the code: the spike is not run in this run (no consent line for live host calls), so `shell` stays
`unknown` for claude, opencode, cursor and codex review and every path form keeps its label; the UI list cannot move to one home,
because the review package may not import the adapter and the adapter's `task_classification.py` may not import the review package
(frozen allowlist, `tests/test_arch.py:1632-1665`): the review package keeps the list once for the lanes and a drift test pins the
adapter's `_FRONTEND_EXTENSIONS` equal to it, so no third copy exists)*

## Interview Log

Interactive path, one round in the phase subagent; no owner question was needed for this phase (one provisional item is flagged
for the owner's confirmation). The open items went through jev (one request, ten items; a second-opinion request for the five
confident answers that contradicted the live evidence): one advisory answer per item, and `needs_fallback` items are decided by
own reasoning. Summaries only, advisory. Rule: `mvp-mode` inactive, so the best design wins over the smallest diff.

| Round | Perspective | Question summary | jev (advisory) | Decision locked |
|-------|-------------|------------------|----------------|-----------------|
| 1 | Researcher | What does each host's final argv let a lane do, and what does the guidance builder tell it today? | none; live `--print-argv` per runtime and role, host helps, code reading | Facts in Background; findings list |
| 1 | Boundary Keeper | Where are a lane's capability facts computed? | laya none_of_these 0.85 (contradicts the evidence); second opinion typesafe runner_row low 0.70 | **Own reasoning:** the runner row computes them from the final argv, one place for review, execute and the GSD hook (R3, ledger); **jev overridden** |
| 1 | Simplifier | Default lens delivery when path reading is unverified? | typesafe inline_unless_verified 0.95 (laya none low 0.38) | Inline unless the host's documentation or a recorded probe verifies the path (R5) |
| 1 | Failure Analyst | How are tokens estimated for the pre-spawn check? | laya none_of_these 0.75 (contradicts the evidence); second opinion typesafe low_ratio_estimate 0.89 | Under-counting fixed ratio, labeled estimated and judged (R7); **jev overridden** |
| 1 | Failure Analyst | Which window applies when a context flag has an unverified effect? | typesafe unknown_unless_user_stated 0.86 (laya none low 0.64) | `unknown` for that lane unless the user stated one (R7) |
| 1 | Boundary Keeper | Where does the shared table live? | laya none_of_these 0.85 (contradicts the evidence); second opinion typesafe review_package_module 0.80 | A new module in the review skill's package read by the GSD config skill through the existing loader (R1); **jev overridden** |
| 1 | Boundary Keeper | Where is a confirmed sort kept? | typesafe config_roles_table 0.97 (laya none low 0.57) | `[skills.roles]` in the layered config, labeled user-stated (R2) |
| 1 | Simplifier | How is an unknown skill sorted? | laya none_of_these 0.93 (contradicts the evidence); second opinion typesafe helper_with_fallback low 0.79 | **Own reasoning:** jev when present, one item per skill from name and description only, advisory, owner confirms each, otherwise unsorted (R2, ledger); **jev overridden** |
| 1 | Failure Analyst | How does a lens with no file on any host reach other lanes? | laya none_of_these low 0.39; second opinion typesafe native_only_named 0.86 | Native lane of its own host only, other lanes get a named note (R5) |
| 1 | Boundary Keeper | How does the after-approval editing pass run? | typesafe opt_in_with_diff 0.83 (laya none low 0.28) | Off by default, write-capable lane, diff shown, owner accepts (R9); **needs owner confirmation** (the requirement wording says the pass runs) *(amended 2026-11-23: confirmed, `OWNER-DECISIONS-2026-11-16.md:52-54`)* |
| 1 | Simplifier | Is herdr used to show a capability view or probe path reading? | typesafe not_used 0.87 (laya none low 0.63) | Not used; plain text and headless probes (R11, Constraints) |

---

*Phase: 39-lane-capability-blocks-and-lens-skills*
*Spec created: 2026-11-16*
*Amended: 2026-11-23 (cross-phase amendment: what Phases 37, 38 and 38.1 shipped, gsd-core 1.22.0, grok not a target)*
