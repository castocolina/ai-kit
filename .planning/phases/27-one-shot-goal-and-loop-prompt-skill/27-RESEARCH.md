# Phase 27: One-shot goal and loop prompt skill - Research

**Researched:** 2026-10-31
**Domain:** a stdlib-only Python generator skill (`skills/ai-kit-spec-goal-prompt/`) that detects host primitives, GSD/superpowers scope and e2e commands, and renders one committable prompt file
**Confidence:** MEDIUM-HIGH (repo facts, host versions and GSD calls verified live; most non-Claude host primitives and non-Python zero-test behavior are unverified and labelled)

Tag legend: `[VERIFIED]` = ran it or read it on this machine today, evidence given. `[CITED]` = official page fetched today.
`[BINARY]` = string found in an installed binary (reverse-engineered, not documented behavior). `[ASSUMED]` = training knowledge or
inference, nothing observed; it must reach the prompt/SKILL.md as "unverified".

<user_constraints>
## User Constraints (from 27-CONTEXT.md and 27-SPEC.md)

Decisions D-01..D-28 are LOCKED (read `27-CONTEXT.md`); this file never re-opens them. The headlines that shape the plans:
- Skill `ai-kit-spec-goal-prompt`; Phase 24 layout (SKILL.md at most about 300 lines, `references/`, `scripts/`, `assets/`); self-contained at run time (sibling skills only through their CLIs; small helpers copied with parity tests).
- Agent asks (four questions), scripts never prompt; two subcommands `detect` and `render --answers <json>`.
- The matrix is a Python tuple of row dicts, one test per row; an OpenGSD scope yields exactly one strategy `/gsd-autonomous --converge` with flags-only first line (D-27); `/goal` or a loop only for non-OpenGSD scopes or on the user's request.
- One fenced block of labeled sections (D-28), paste block about 1,500 characters, rails about 60 lines (D-25); the `/goal` condition is at most 4,000 code points and names the rails file.
- E2E is the core of done, with a zero-test marker table (D-19) and printed process-group cleanup proof (D-20); jev advisory and text-only (D-21).
- The file is committable in a dated `goals/` subfolder (D-15); `string.Template` subclass with a rare delimiter and strict `substitute()` (D-14).
- Claude's discretion: the delimiter character, question wording, slug rules, the golden case inputs.

The executors of these plans are cheap cross-AI models: every task is small, every command path-agnostic.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research support |
|----|-------------|------------------|
| GPS-01 | Detect host primitives, scope; pick 1-3 strategies from a matrix | Host table below; Phase 26 `matrix --json` contract; GSD calls |
| GPS-02 | Emit a `.md` with rails, per-plan subagent, cross-AI per plan, quota directives | Template sections; D-16 readiness; R18/R19 signal parity |
| GPS-03 | E2E is the core of done; evidence printed; create-first when none | Zero-test table; Makefile/package/Playwright/PTY signals |
| GPS-04 | jev advisory, text-only; skill passes skill-judge | `decide.py detect` shape; skill-judge plan with a 3-round cap |
</phase_requirements>

## Summary

Everything the skill needs from other components already exists and has a stable CLI: `ai-kit-session-wake matrix --json` (schema_version 1, ten rows today), `ai-kit-spec.py detect-current-runtime` / `detect-runtimes`, `ai-kit-gsd-spec-discuss/scripts/decide.py detect`, the project-local `gsd-tools.cjs` (`query roadmap.analyze`, `query runtime-identity`, `query init.phase-op`, `query verification.status`) and `.planning/scripts/cross-ai.mjs --print-argv`. No new dependency is needed.

Three findings change or sharpen the plans (none contradicts a locked decision):
1. **Versions moved since the SPEC (2026-10-14).** Claude Code is 2.1.314 (the SPEC says 2.1.299), OpenGSD `runtime-identity` reports 1.17.0 (the SPEC says 1.16.0). The skill must read versions live and never hard-code them; the matrix floor 2.1.299 for CronCreate and `/goal` is a Phase 26 data row, not a Phase 27 constant.
2. **`/goal` semantics are now documented** (see Q1): setting a goal starts a turn with the condition itself as the directive, so the condition IS the instruction; the 4,000 cap is on "characters"; the evaluator judges only the transcript.
3. **Original GSD cannot be probed here.** Only OpenGSD 1.17.0 is installed, so whether original GSD has `/gsd-autonomous`, `runtime-identity` or `verification.status` is unverified. The matrix therefore labels an identity-unverified `.planning/` scope's `/gsd-autonomous` row "existence unverified for this install" and ranks it below `/goal` (own reasoning, ledgered, see Assumptions Log A1).

## Live-verified host primitives (this machine, 2026-10-31)

| Host | Installed | `/goal` | Loop / schedule | Evidence and label |
|------|-----------|---------|-----------------|--------------------|
| claude | 2.1.314 (also 2.1.310, 2.1.312 under `~/.local/share/claude/versions`) | yes, documented; floor 2.1.139 | tools `CronCreate`, `CronList`, `CronDelete`, `ScheduleWakeup`, `Monitor`, `RemoteTrigger`, `PushNotification`; skill `/loop` (bundled skill) | `[CITED]` goal and scheduled-tasks pages (fetched today). `[BINARY]` 2.1.314 holds the strings CronCreate x17, ScheduleWakeup x15, `/goal` x26, `/loop` x47, RemoteTrigger x5. Availability in a given session is only known to that session (see Q7). |
| codex | codex-cli 0.162.1 | `codex features list` prints `goals stable true` `[VERIFIED]`; usage `/goal [<objective>\|clear\|edit\|pause\|resume]` and the notices "Goal hit usage limits (/goal resume)" `[BINARY]` | none found (no ScheduleWakeup string; `cron` x13 and `/loop` x1 hits are inconclusive) | usage syntax is reverse-engineered, so the prompt labels codex `/goal` usage "unverified" |
| opencode | v2.0.31 | none | none | `opencode --help` and `opencode run --help` carry no goal, loop, schedule, cron or ralph keyword `[VERIFIED]`; community wrappers `[ASSUMED]` |
| pi | 1.3.0 | none | none | `pi --help` grep empty `[VERIFIED]`; third-party schedulers `[ASSUMED]` |
| cursor-agent | 2026.10.22-27dcf5f | none | none | `cursor-agent --help` grep empty `[VERIFIED]` |

Phase 26's survival matrix (read through the CLI, not by import) `[VERIFIED]`, `python3 skills/ai-kit-session-wake/ai-kit-session-wake.py matrix --json`:
`schema_version` 1 and ten rows, each with `host, primitive, kind, surface, survives_stall, survives_process_death, survives_reboot, source, evidence, unverified, version_floor, rank`.
Rows today: claude `systemd user timer` (os-timer, cli, verified, floor 2.1.310), `CronCreate one-shot` and `CronCreate recurring` (schedule, tool, verified, 2.1.299, survives stall only), `/goal` (goal, slash-command, verified, 2.1.299, survives nothing), `ScheduleWakeup` (wake, tool, unverified), `/loop` (loop, slash-command, unverified), `cloud routine` (schedule, slash-command, unverified); codex `systemd user timer` (unverified, 0.162.1); pi (verified, 1.3.0) and opencode (verified, 2.0.31) `systemd user timer`. There is no cursor row: the skill treats a host with no row as "no primitive known".

### Two labels per primitive (D-07), as the code must compute them

- **Availability here**: `available (version X >= floor Y)` when the host is the current one and its binary version meets `version_floor`; `not seen` for an agent-reported tool name the agent could not see; `unverified` for a non-current target host (the version probe is skipped, never guessed); `absent` only for a primitive a `--help` or feature probe positively lacks (opencode, pi and cursor-agent have no goal row at all, so the table reports "no primitive in --help").
- **Usage source**: `official docs` (claude `/goal`, CronCreate, `/loop`), `live` (the matrix row `source: verified`), `third-party` (codex `/goal` usage, community wrappers), `binary strings` (reverse-engineered).

## Research questions (from 27-CONTEXT `<deferred>`)

### Q1. Is `/goal` text also the agent's instruction? Can it invoke a slash command? Is the cap in characters?  `[CITED]`
Setting a goal "starts a turn immediately, with the condition itself as the directive", so the condition is the instruction. "The condition can be up to 4,000 characters"; the binary's error text says "goal condition exceeds the canonicalized-length cap" `[BINARY]`, so the cap counts canonicalized characters (the plan counts Python code points and keeps the generated condition well under 4,000 so canonicalization cannot push it over). The evaluator "doesn't run commands or read files independently": the condition must be demonstrable from the transcript, so the prompt makes the agent print each proof. Whether the agent can invoke a slash command from inside a goal turn is not documented: `[ASSUMED]` yes for skills, and `/gsd-autonomous` as a goal's first line is not relied on (D-27 puts it in a plain paste, not a `/goal`).

### Q2. Does the multi-paragraph rest of a message become `$ARGUMENTS`? Other hosts?  `[PARTLY VERIFIED]`
`/gsd-autonomous` parses `$ARGUMENTS` with `grep -qE`/`grep -oE` over the whole string: `--from\s+[0-9]`, `--to\s+[0-9]`, `--only\s+[0-9]`, `--interactive`, `(^|[[:space:]])--(converge|cross-ai)([[:space:]]|$)` (`.claude/gsd-core/workflows/autonomous.md:18-62`, read today) `[VERIFIED]`. So every `--from N`-shaped token anywhere in the pasted block changes the run. Consequence for the plans: in an OpenGSD block, line 1 is the only line allowed to contain a `--` token and the rails text must not contain `--` followed by a letter at all (a test pins it, stricter than the grep). Whether the slash-command host passes the full multi-line message as `$ARGUMENTS` is `[ASSUMED]` yes (the existing hand-written v1.3 prompt relies on it); the first line carries the flags regardless.

### Q3. Agent tool at depth 1?  moot (D-09 refined).

### Q4. codex 0.162.1 `/goal` syntax, loop or schedule primitives?  `[BINARY]`
`/goal [<objective>|clear|edit|pause|resume]`, example "/goal improve benchmark coverage"; goal states "stalled" and "hit usage limits" resume with `/goal resume`. No cron or wake tool found. The prompt for codex uses the strategy `/goal` with usage labelled "unverified (binary strings only)", and the OS timer (Phase 26 codex row, itself `unverified`) is the survival path.

### Q5. Original GSD: `/gsd-autonomous`, `runtime-identity`, `verification.status`?  `[UNVERIFIED]`
Only OpenGSD is installed (`query runtime-identity` prints `{"packageName": "@opengsd/gsd-core", "version": "1.17.0"}` `[VERIFIED]`). Original GSD is not installed here and no other source was checked, so all three are unverified. `query verification.status <phase dir>` exists in OpenGSD 1.17.0 and prints a JSON object with `status`, `next_action`, `next_command`, `route`; for the Phase 26 directory it prints `status: "stale"` today (not `passed`), so the wrapper idea of D-12 must compare against the literal `passed` and treat any other value as not done `[VERIFIED]`. With D-27 this only matters for non-OpenGSD `.planning/` scopes, where the skill does not emit a `verification.status` guard (it cannot verify the command exists); the done checks name the phase's `VERIFICATION.md` instead.

### Q6. Zero-test behavior per runner (D-19 marker table)
| Runner | No tests: exit and text | Label |
|--------|-------------------------|-------|
| `python3 -m unittest discover` | exit 5, "Ran 0 tests in 0.000s" and "NO TESTS RAN" | `[VERIFIED]` scratch probe under `tmp/p27/probe` |
| `node --test` (Node built-in) | exit 0, summary line `tests 0` | `[VERIFIED]` |
| `go test ./...` | exit 0, `[no test files]` | `[VERIFIED]` |
| ai-kit shell harness (`tests/test_install.sh`) | final line `N passed, M failed` (`tests/test_install.sh:453`) | `[VERIFIED]` by reading the script today; D-19 analyzer run agrees |
| pytest | exit 5, "no tests ran" | `[ASSUMED]` (not installed here) |
| jest | exit 1 "No tests found" unless `--passWithNoTests` | `[ASSUMED]` |
| vitest | exit 1 "No test files found" | `[ASSUMED]` |
| Playwright | exit 1 "No tests found" | `[ASSUMED]` |
| Cypress | no count rule known | `[ASSUMED]`, count rule omitted |
| `cargo test` | exit 0 "running 0 tests" | `[ASSUMED]` (cargo not installed) |
The table is a labelled constant: each row carries `verified: bool`, and the prompt prints the unverified ones as "marker unverified: confirm the count by reading the output". The prompt requires every e2e command to print its count and treats exit 0 plus a zero count as not green regardless of the table.

### Q7. How can a session list its deferred-but-available tools?  `[VERIFIED in this session]`
The tool list shows only loaded tools; deferred tools appear by name in system reminders and are searchable with `ToolSearch` (`select:Name` or a keyword query). A keyword search for "cron schedule wakeup loop" in this research session returned `Monitor`, `ArtifactComments`, `SendMessage`, and no `CronCreate`, `CronList`, `CronDelete` or `ScheduleWakeup`: so in THIS session (a subagent) those tools are "unverified (not seen)", although the installed binary contains them. The SKILL.md therefore tells the agent: build `--tools` from the names in your own tool list plus a `ToolSearch` keyword query; a name you did not see is passed as nothing and reported "unverified (not seen)", never "absent". On hosts without `ToolSearch` the agent passes the names it knows are loaded.

### Q8. opencode, pi, cursor-agent native goal/loop/schedule?  `[VERIFIED: help text only]`
None. Their `--help` and `opencode run --help` carry no such keyword. Community wrappers stay `[ASSUMED]`/unverified; the skill never relies on them (SPEC out of scope: "native goal or loop support for hosts that lack one").

### Q9. Is `gsd-tools review-lane plan` read-only?  `[UNVERIFIED, not needed]`
`query review-lane` with no subcommand prints its usage (`review-lane <plan|invoke|sections|flags|dispatch-step|explicit-from-argv>`). The skill never calls `review-lane`; it is irrelevant to the generator. Dropped from the plans.

## Other live facts the plans rely on  `[VERIFIED]`

- `query roadmap.analyze` returns `{"milestones": [...], "phases": [{number, name, goal, mode, depends_on, plan_count, summary_count, has_context, disk_status, roadmap_complete, ...}]}`; there is no `has_spec` field (so SPEC presence comes from a `*-SPEC.md` glob, D-24). `query init.phase-op <N>` returns `phase_found, phase_dir, phase_number, has_research, has_context, has_plans, has_verification, has_reviews, plan_count, state_path, roadmap_path`; `phase_dir` and `state_path` are ABSOLUTE paths, so the skill must relativize or drop them before they reach the file (D-05).
- `.planning/config.json` carries `workflow.cross_ai_execution` (true), `workflow.cross_ai_command` (`node .planning/scripts/cross-ai.mjs`), `workflow.plan_review_convergence` (true) and `review.default_reviewers` (three ids) on this repo.
- `node .planning/scripts/cross-ai.mjs --print-argv` exits 0 offline and prints tab-separated `<cli>\t<absolute binary path>\t<argv json>` lines plus `cross-ai:` stderr-style lines; it contains absolute paths, so only its exit code and the CLI names are used (D-05, D-16).
- `python3 skills/ai-kit-spec-review/ai-kit-spec.py detect-current-runtime` prints `{"host": "claude"}`; `detect-runtimes` prints `{"schema_version": 7, "clis": {<id>: {"installed": bool, "path": ..., ...}}}` with absolute paths (names and `installed` only are used).
- `python3 skills/ai-kit-gsd-spec-discuss/scripts/decide.py detect` prints `{"backends": {"laya": {status, usable, remote, ...}, "typesafe": {...}, "opencode": {...}}, "client": ...}`; jev is "usable" when some backend has `usable: true` and (it is local, or consent is on file); the skill reads `usable` and `remote` only (D-21). Do not run `ladder` in any test; no paid or remote jev call is ever made by this phase.
- The roadmap/test infrastructure facts: new `tests/test_*.py` modules join the `unit` group automatically; a module that runs real `node`, git worktrees or PTYs goes into the commented `E2E_MODULES` set in `tools/run_unittest_parallel.py`; `python3 tools/gen_test_groups.py` regenerates the Makefile/pre-commit listings (never hand-edit); `tests/test_gate_scope.py` fails while a listing is stale; pyright `extraPaths` in `pyproject.toml` needs `skills/ai-kit-spec-goal-prompt/scripts` for tests that import the scripts by name (precedent: `skills/ai-kit-gsd-spec-discuss/scripts`).
- The Choose screen PTY (`tests/test_wizard_pty.py`, `_PTY_ROWS = 160`) was sized for 25 skills (`f669709`); this phase adds the 26th, so the wizard PTY suite must be re-run (plan 27-10).
- `skills/_shared` is not importable on a copy install (07 D-02, 24 D-09): the new skill copies `phase_key` (from `phase_range.py:28`), the Makefile target regex (`makefile_parse.py:16`, `_TARGET_HEADER_RE`) and the lockfile-driven package runner order (`package_scripts.py`: pnpm-lock.yaml, yarn.lock, bun.lockb/bun.lock, else npm), each with a parity test that compares the copy with the original over a table of inputs.

## Architecture (what gets built)

```
skills/ai-kit-spec-goal-prompt/
  SKILL.md                      about 300 lines; NEVER list; MANDATORY read triggers; four questions
  references/
    host-primitives.md          the two-label table above as the skill states it; unverified list
    strategy-matrix.md          one paragraph per matrix row (data lives in gp_matrix.py)
    e2e-and-evidence.md         signals, zero-test table, evidence format, cleanup proof
    worked-example.md           one OpenGSD run and one superpowers run, short
  scripts/
    goal_prompt.py              CLI: detect, render (non-interactive JSON in, JSON out)
    gp_common.py                phase_key copy, make-target regex copy, package-script reader copy, path/secret guards
    gp_scope.py                 GSD phases (D-24), identity, superpowers plans + Depends-on edges, order, stop-scope, scope kind
    gp_host.py                  host primitives (two labels), tools-seen, readiness (D-16), jev usability (D-21)
    gp_e2e.py                   e2e signal detection and the labelled zero-test table
    gp_matrix.py                RULES tuple, select(), derived outlive/provable
    gp_render.py                Template subclass, fill, budgets, guards, placement
    gp_sections.py              section builders per strategy (goal, loop, superpowers, OpenGSD, done variants)
  assets/prompt-template.md     string.Template source, rendered by gp_render.py; SKILL.md says "Do NOT load"
tests/goal_prompt_fixtures.py   fixture project builders (shared, not a test module)
tests/test_ai_kit_spec_goal_prompt_*.py   unit modules; ..._e2e.py in E2E_MODULES
```
Module names carry the `gp_` prefix because the scripts dir is put on `sys.path` by tests and pyright (`detect`/`matrix` would collide with common names).

## Assumptions Log

| # | Claim | Where used | Risk if wrong | Owner action |
|---|-------|------------|---------------|--------------|
| A1 | For a `.planning/` scope whose identity is not proven OpenGSD, `/gsd-autonomous` may not exist; it is offered last and labelled unverified | gp_matrix row `gsd-unproven` | A user on original GSD gets one extra, labelled, non-recommended block | confirm on an original-GSD checkout if one is ever installed |
| A2 | The pasted multi-line message becomes `$ARGUMENTS` in full (flags-only first line, no `--` token anywhere else) | OpenGSD block shape | none beyond the stricter test; a stray `--from 3` would change the run | none |
| A3 | The `/goal` evaluator counts canonicalized characters; the plan counts code points and keeps a 150-character safety margin below 4,000 in the golden, while still failing generation at 4,001 | `/goal` block | a condition at exactly 4,000 code points might be rejected by the host | owner capture: paste a 4,000-character goal once |
| A4 | codex `/goal` usage `[<objective>\|clear\|edit\|pause\|resume]` | codex strategy line | wrong usage text in a codex paste block | labelled unverified in the file |
| A5 | pytest, jest, vitest, Playwright, Cypress and cargo zero-test markers | marker table | an unlisted runner is "marker unverified"; the printed-count rule still applies | none |
| A6 | The agent's reported `--tools` list is honest and complete for the names it can see | detect | a missing name reads "not seen", never "absent" | none |

## Open questions for the owner (carried to the final plan's captures)

1. Does a pasted 4,000-code-point `/goal` condition get accepted by Claude Code (A3)? One manual paste.
2. Is the `/gsd-autonomous` flags-only first line followed by labeled sections parsed exactly as in the hand-written v1.3 prompt on a second project (A2)?
3. The unverified codex `/goal` usage and every non-Claude host's primitives (A4, Q8).

## Sources

- `[CITED]` https://code.claude.com/docs/en/goal and https://code.claude.com/docs/en/scheduled-tasks (fetched 2026-10-31).
- `[VERIFIED]` repo files: `skills/ai-kit-session-wake`, `skills/ai-kit-gsd-spec-discuss/scripts/phase_range.py`, `skills/_shared/ai_kit_rules_common/makefile_parse.py`, `skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/package_scripts.py`, `skills/ai-kit-spec-execute/detect_framework.py`, `.claude/gsd-core/workflows/autonomous.md`, `execute-phase.md` (cross_ai step), `.planning/config.json`, `.planning/scripts/cross-ai.mjs`.
- `[VERIFIED]` live probes: `claude/codex/opencode/pi/cursor-agent --version/--help`, `codex features list`, `gsd-tools query runtime-identity|roadmap.analyze|init.phase-op|verification.status`, scratch zero-test runs under `tmp/p27/probe`.
- `[BINARY]` installed `claude` 2.1.314 and `codex` 0.162.1 strings.
