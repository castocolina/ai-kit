# Phase 37: Shared runner options and session ids - Discussion Log (standard discuss mode (`--analyze --all --batch`) for the interactive path)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-16
**Phase:** 37-shared-runner-options-and-session-ids
**Mode:** interactive path: no owner question was unclear enough to relay (the owner answers only unclear gray areas in this
run); every gray area was screened with jev and decided by the decision table; no gsd-assumptions-analyzer run (the owner
did not ask for it; the scouting was done live in the phase subagent), best design over smallest diff
**Areas analyzed:** where effort forms live, the role flag, the provider, unknown runtimes, the model id gate, effort levels,
escalation flags, claude's execute formula, the describe command and its cache key, the status line grammar, session
contract and styles, test placement, the sync test, runner-file hardcoding, skills and docs, conditional jev and herdr

## Assumptions Presented

No analyzer ran. The scouting covered the runner's parse and main paths, every table-gating line, each host's effort,
session and permission flags in its own `--help`, the runner's dry-run output for each gate, the render path and the live
copy check, all live on 2026-11-16 (SPEC Background).

| Assumption | Confidence | Evidence |
|---|---|---|
| The runner can own every effort form | Confident | each host's form is a flag, a suffix or a bracket; a hook string has no Python layer and a bracket is a glob there |
| One session flag covers hosts that choose and hosts that mint ids | Likely | pi and copilot take a chosen id per their help; cursor, codex, claude resume ids they printed; continuing is help-text only |
| An unknown runtime can run without a formula | Likely | only from a declared argv file; the runner cannot learn flags from a CLI |
| claude's execute formula works under `-p` | Unclear | `--permission-mode` and `--dangerously-skip-permissions` both exist; one probe decides |
| opencode accepts a caller-chosen session id | Unclear | help says create-if-missing; the id shape is unverified |
| Adding a status line group breaks no caller | Confident | callers read by key; the self-test's pinned expression and two doc samples need a refresh |

## jev screening

Two requests: spec items (nine), discuss items (five). Summaries only.

| Item | jev | Outcome |
|---|---|---|
| effort forms home | laya runner_owns_forms low 0.38; typesafe runner_owns_forms low 0.60 | **Own reasoning:** the runner (D-01, ledger) |
| session contract | laya resume_only_printed low 0.42; typesafe one_flag_row_decides low 0.79 | **Own reasoning:** one flag, row decides (D-03, ledger) |
| unknown runtime | laya refuse_always low 0.43; typesafe refuse_always low 0.72 | **Own reasoning, jev overridden (low, contradicts the owner directive):** D-05 (ledger) |
| model id gate | floor_plus_advisory, choice 0.95 (laya drop_all low 0.69) | D-06 |
| effort levels | laya catalog_check low 0.67; typesafe shape_only low 0.58 | **Own reasoning:** D-07 (ledger) |
| escalation in the runner | carry_and_report, choice 0.98 (laya act_in_runner low 0.45) | D-08 |
| role versus mode | laya keep_mode_only low 0.44; typesafe role_flag_mode_alias low 0.76 | **Own reasoning:** D-02 (ledger) |
| claude execute formula | add_formula_unverified_label, choice 0.89 (laya low 0.51 agrees) | D-09 |
| provider flag | laya provider_flag low 0.63; typesafe derive_and_report low 0.57 | **Own reasoning:** D-04 (ledger) |
| runner row data | laya branches_in_main low 0.39; typesafe row_fields_one_planner low 0.78 | **Own reasoning:** D-11 (ledger) |
| status line grammar | laya append_last low 0.48; typesafe group_after_cycles low 0.56 | **Own reasoning:** D-12 (ledger) |
| describe cache key | key_by_template_hash, choice 0.99 (laya age_only low 0.60) | D-10 |
| behavior test home | split_by_cost, choice 0.93 (laya all_selftest low 0.36) | D-13 |
| opencode session style | minted_until_probe, choice 0.96 (laya both_try low 0.42) | D-03 |

## Live facts that changed the plan

- The status line grammar is pinned by the self-test (`STATUS_HEAD_RE`) and two doc samples come from real self-test output, so
  adding fields touches the self-test and the docs (D-12).
- `tools/check_dogfood.py` already compares the live copy with the template, but it reads `.planning/`, which no test may do;
  RUN-06 therefore needs a scratch render (D-18).
- `build_reviewer_model_id` already composes cursor brackets in Python (including a `context` key), which is why moving the forms
  into the runner deletes code instead of adding a second place (D-01).
- A cursor bracket model is a glob class in GSD's word-split hook string, so a hook can carry effort only as a plain flag (D-01).
- codex's `exec resume` has no sandbox flag, so a read-only role cannot resume: `mode_forbids` (D-03).
- claude has a documented `--session-id <uuid>` and `--resume <id>`, and two live candidates for the execute permission flag (D-09).

## Corrections Made

- ROADMAP Phase 37 and RUN-01, RUN-02, RUN-06 gain dated notes (code anchors, criteria 1 to 3, new criteria 5 and 6, the judge
  bar moves to 7); 36-CONTEXT D-05 and D-08 note that the Python forms and mirrors are transitional.

## External Research

None. No web source was needed; every claim is from the installed hosts' own `--help`, the runner's dry-run output and the
repository.

# Update 2026-11-16 (re-run 2, herdr hosting, interactive path)

**Input:** `37-SPEC.md` (R1 to R11 kept verbatim) and the 2026-11-16 CONTEXT (D-01 to D-21 kept). One owner directive: where herdr is
available the runner may open a tab, run a lane in it and close what it opened; never required. Owner answers only unclear gray areas;
none was unclear enough to relay. Added D-22 to D-29 and R12 (RUN-12); D-20 is amended in place.
**Mode:** interactive path, jev screening (laya and typesafe through the ladder), best design over smallest diff, live checks with
herdr 0.9.5 and opencode 2.3.0 in labeled, closed tabs.
**Areas analyzed:** where hosting lives, its trigger and switch-off, the result channel, the environment handoff, ownership and
cleanup, interactive agents versus lanes, composition with settings, sessions, `--argv-file` and the evidence line, the free lane's limit.

## jev screening

One ladder request, six items, summaries only (no code, config values or keys).

| Item | jev | Outcome |
|---|---|---|
| placement | inside_runner_transport, typesafe 0.89 (laya none_of_these low 0.51) | D-22 |
| trigger | availability_with_flag, typesafe 0.89 (laya always_when_available low 0.39) | D-23 |
| result channel | laya forced; typesafe screen_scrape_marker low 0.63 | **Own reasoning, jev overridden:** D-24 (ledger) |
| interactive agent | caller_transport_later_phase, typesafe 0.98 (laya none_of_these low 0.43) | D-27 |
| switch-off | laya none_of_these 0.83; second opinion typesafe config_key low 0.67 | **Own reasoning:** D-23 (ledger, needs owner confirmation) |
| environment handoff | laya none_of_these low 0.56; typesafe tab_env_arguments low 0.65 | **Own reasoning, jev overridden:** D-25 (ledger) |

## Live facts that changed the plan

- The first plan sketch used `herdr pane wait-output` with a marker line; the live check showed a literal match fires on the typed
  command line, and an interactive TUI reply is never returned by `agent prompt --wait`, so the result channel became files with an exit
  file and the wait command was dropped (D-24).
- opencode 2.3.0's TUI has no `--model` flag and hides the headless error events, which moved interactive hosting out of the runner (D-27).
- A free opencode lane hit its daily limit during the probe (`provider.free-limit`, 429, about 6 h 44 min): the first captured wording for
  38.1, and the reason the runner gets no free-lane rule (D-29).
- `tab close` ended a running `sh` plus `sleep` child, which is what makes the runner's own close a sufficient cleanup (D-26).
- A caller-chosen opencode session id of the form `ses_` plus 16 letters or digits was accepted headless and the TUI attached to it (D-03 note).

## Corrections Made

- 37 D-20 is amended in place (superseded markup); 37 SPEC constraint, R11 and prohibition rows amended; 36 D-19's open point is closed
  by a note in 36-CONTEXT; RUN-12 added to REQUIREMENTS.md; ROADMAP Phase 37 gains criterion 8 and Phase 42 a dated boundary note.

## External Research

None. Every claim is from the installed `herdr` and `opencode` help and the live probes (scripts and outputs under
`tmp/spec-discuss-35-39/`, not committed).

# Update 2026-11-21 (plan time, owner-directed amendments)

**Input:** `37-SPEC.md` (committed in `a111f5a`, R1 to R12 kept verbatim) and the 2026-11-16 CONTEXT (D-01 to D-29 kept; D-30 is
added by a later unit's carried amendment, so the new decisions start at D-31). Three owner inputs from the run's request notes:
skills handed to cross-AI lanes (2026-11-19), MCP servers for review and execution lanes (2026-11-19), grok is not a cross-AI
target (2026-11-19, confirmed as a directive 2026-11-20). Added R13, R14 and D-31 to D-34.
**Mode:** plan-time amendment in an autonomous run; owner-directed items are decided, not asked; no jev round and no analyzer
(the owner's words fix the design; one own-reasoning item, ledgered); live help read of the installed hosts; best design over
smallest diff.
**Areas analyzed:** the per-host skill forms (name, path, prose) and who falls back; the per-host MCP forms and the
config-file-only hosts; the report of both; the split with Phase 39; grok mentions; pool wording; couplings with 38, 38.1 and 39.

## Decisions

| Item | Source | Outcome |
|---|---|---|
| runner side versus Phase 39 | owner request 2026-11-19 | D-31: the runner records forms, delivers and reports; Phase 39 chooses |
| skill forms and order | owner request 2026-11-19 (order name, path, prose) | D-32, R13 |
| who applies the fallback | none (owner gave the order, not the place) | **Own reasoning:** the runner, which alone knows the forms; a GSD hook has no Python layer (D-32, ledger) |
| MCP forms and rules | owner request 2026-11-19 (only when needed, read-only by default, never the real host config, no secrets printed) | D-33, R14 |
| grok | owner directive 2026-11-20 | D-34: five SPEC lines superseded in place, no grok work, code left for Phase 39.1 |
| pools | 36 D-20 to D-22 | No pool is named in this phase's text; nothing to align |

## Live facts that changed the plan

Read on 2026-11-21 from each installed host's own `--help` and its `skill`/`mcp` subcommand help (read-only, no model call, no
host config read; outputs in the run folder `tmp/run-2026-11-19/p37-help/`, not committed). Versions: claude 2.1.330, codex 0.170.0, opencode 2.3.2,
pi 1.5.2, copilot 1.0.112, cursor-agent 2026.11.13.

| Host | Skill form (label) | MCP per-invocation form (label) |
|---|---|---|
| pi | path `--skill <path>` (help; loading under `--no-skills` from pi's docs) | none: `--no-mcp` only; `pi mcp` reads `~/.pi/agent/mcp.json` and a trusted project's `.pi/mcp.json` (help) |
| claude | name `/<name>` stated only inside the `--bare` text (help, indirect: unverified); `--add-dir`, `--plugin-dir` name no skill loading | `--mcp-config <configs...>` and `--strict-mcp-config` (help) |
| copilot | `--add-dir <dir>` loads `<dir>/.github/skills` (help, needs a layout: unverified); `copilot skill` lists discovery roots, no load-by-name flag | `--additional-mcp-config <json or @file>`, augments the user's copilot servers (help) |
| cursor-agent | none (`--add-dir` workspace root, `--plugin-dir` plugin) | none: `--approve-mcps` only approves servers from `.cursor/mcp.json` or `~/.cursor/mcp.json` (help) |
| codex | none (`--add-dir` writable directory) | none verified: `-c key=value` overrides `~/.codex/config.toml`, no MCP key named (help) |
| opencode | none (`run --file` attaches a file to the message) | none: `mcp` subcommand only, no flag on `run` (help) |

- The owner's note of 2026-11-19 holds on these versions (claude moved from 2.1.328 to 2.1.330 with the same MCP flags).
- The runner template on this branch already passes `--no-skills` in pi's formulas, `--no-mcp` in pi's review profile,
  `--approve-mcps` in cursor's exec formula and `--disable-builtin-mcps` in copilot's review profile; these shape the
  `mode_forbids` cases and stay unchanged (D-33).
- Phase 39's SPEC (on its unit branch) already planned `--skill-path` as a runner setting (39 R6, D-11) and inlining in its
  composer (39 R5, D-10); this phase takes over both runner-side parts (D-31).

## Handoffs (couplings for later units; amended when each unit is reached)

- **Phase 38** (SPEC and CONTEXT on its unit branch): no statement found that D-31 to D-34 contradict. The R13 and R14 self-test
  cases move with the harness to its sibling file.
- **Phase 38.1**: (1) its carried amendments to this phase's files name grok: the R2 bullet's host list in `37-SPEC.md`, the D-15
  refinement and D-30's recorded-help fixture list in `37-CONTEXT.md` (D-30 asks for `tests/fixtures/cli_help/grok.txt`); mark each
  superseded and drop the grok fixture; (2) its own SPEC live-facts line (`grok 1.0.52`) and its CONTEXT line `opencode, pi and grok
  none` get the same dated mark; (3) D-30's help-fixture test covers the new flags of R13 and R14 (`--skill`, `--mcp-config`,
  `--strict-mcp-config`, `--additional-mcp-config`); (4) D-30 says this phase's plan executes it, but the D-30 text exists only on the
  38.1 and 39 branches: carry it down to this unit before 37 is planned, as `c6cedee` did for 36; (5) this phase names no pool, so
  38.1's own adoption of the `provider:free` form needs nothing here.
- **Phase 39**: (1) R6 and D-11 (`--skill-path` as a runner setting) are now this phase's R13, same flag and forms, plus
  `--skill-name` and the runner's prose form; (2) R5 and D-10 keep lens selection, lens notes and the window check, and count the
  inlined bytes from the runner's `form=prose` report instead of inlining in the composer (same delimited format); (3) D-02's
  capabilities `skills` and `mcp` read this phase's `skill` and `mcp` lines; `host_config` stays its reading of the argv;
  (4) REV-05's table chooses servers by task kind (read-only by default) and writes the run-scoped MCP file this phase reads;
  (5) the repository-or-skill-root check stays its validator (39 D-11's plain-Node copy in the runner is its choice); (6) its ROADMAP
  code anchor "`--skill-path` setting" and its execute-lane skill delivery (owner request: execute lanes too, by task kind) go
  into its own amendment; (7) its D-19 says this phase's CONTEXT carries a handoff for `--skill-path`: that line is on the 39 branch
  only and now reads against D-31.

## Corrections Made

- `37-SPEC.md`: header count, an amendment paragraph in Background, R13 and R14, Boundaries in and out of scope, two acceptance
  lines, 14 engine edge rows (floor 72, `check` ok), four prohibition rows, five Interview Log rows, the footer; five grok lines
  marked superseded. `37-CONTEXT.md`: a refined spec-lock note and D-31 to D-34 with handoffs and open questions. REQUIREMENTS RUN-01
  and ROADMAP Phase 37 criterion 9 gain dated notes; the requirement total stays 193.

## External Research

None. Every claim is from the installed hosts' own help, the runner template and the planning files.
