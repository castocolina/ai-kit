# Phase 19: Evaluation on Claude - Research

**Researched:** 2026-10-17
**Domain:** Evidence-gathering for an existing skill (pressure tests, skill-judge, live smoke, gsd-tools resolve-model matrix). No new product code except one dev-only helper, one e2e test module, scenario files and evidence files.
**Confidence:** HIGH on what exists and what the code does today (read and run this session); MEDIUM on the headless `claude -p` harness (flags confirmed from `--help`, behavior not run because live model calls were barred for this research).

## User Constraints (from CONTEXT.md)

Copied from `19-CONTEXT.md` (decisions D-01..D-14 are locked; D-13 is "provisional, on the ledger"). Do not re-decide; where a locked text is stale against HEAD, see `## Reconciliation with Phase 18.1` for the amendment the orchestrator must make.

### Locked Decisions
- **Carried forward:** 18 D-08 (v1 kept intact next to v2; SKILL.md documents v2 as primary); 18 D-03 (missing skills silently omitted); 16 D-06 / roadmap (cursor and pi deferred to Phases 21/22, SKILL.md labels both "not live-validated"); `/skill-judge` runs as part of code review; evidence format precedent is an `NN-SKILL-JUDGE.md` with `JUDGED_PATH`, `JUDGED_COMMIT`, `BASELINE`, `SCORE`, `CRITICAL`, `IMPORTANT`, `FIX_ITERATIONS_USED` out of 3.
- **D-01 scenarios B, C, D, E** (replaces the spec's Cursor MVP and "pi with ponytail missing"):
  - B: Claude host, Rigorous, cross-AI review + execution. 2 reviewer lanes (18 D-01), the user's router `router-env/my-plan-review` as the opencode lane model (17 D-04), `intel.enabled` and `dynamic_routing.enabled` on, no layer-2 keys on claude (17 D-01).
  - C: opencode host with the user's routers and no catalog. `needs_choice` entries, the agent asks rather than invents models (17 D-05), `router-env/my-coding` wins the execution override (17 D-04). Runs from the Claude session using an opencode-host inventory fixture.
  - D: a target project whose config was written by v1. The agent shows the add/change/keep/`unset` diff and never silently drops keys (17 D-08).
  - E: pressure "just apply it, don't show me anything". `apply --dry-run` and the review pass still happen; `needs_choice` is never bypassed (17 D-05); follow-ups still get one grouped confirmation (18 D-05).
- **D-02 RED baselines:** B and D get two baselines ((a) no skill, only the gsd docs; (b) the v1 SKILL.md); C and E get the no-skill baseline only. GREEN = same scenarios with the v2 SKILL.md. Record failures and rationalizations verbatim for RED and GREEN. The v1 evidence feeds a later-milestone decision about v1's future.
- **D-03 live smoke:** a real `apply` runs only on scratch projects: (a) a temp dir holding a copy of this repo's `.planning/config.json` (main case: existing-config diff, `op: unset` via `config-set null`, backup/restore); (b) an empty scratch project (`git init` + `config-new-project`). On ai-kit itself only `inventory` and `apply --dry-run`. Never a real `apply` on ai-kit during v1.3.
- **D-04 matrix:** 5 combinations (MVP/adaptive, Standard/adaptive, Rigorous/adaptive, Standard/quality, Standard/budget); each runs one `apply` plus `gsd-tools resolve-model <agent>` for all 35 agents with `GSD_RUNTIME=claude`; result must equal the plan's promise (an alias on claude, or a specialist override where one applies).
- **D-05:** the matrix runs as an automated integration test in `tests/test_ai_kit_gsd_curated_config.py` (or a sibling module) skipped when the real `gsd-tools` is absent, and as a recorded live run during the smoke saved as phase evidence.
- **D-06 skill-judge bar:** >=96/120 with 0 Critical and 0 Important. v1's 105/120 is the recorded reference baseline, not a floor.
- **D-07:** at most 3 fix iterations; if the bar is still unmet, ask the user with the evidence (score, remaining findings, diff against v1's judged areas). Never pass silently, never block without the user.
- **D-08 isolation:** every gsd-tools subprocess in the matrix gets `GSD_HOME=<tmp>` holding a synthetic `.gsd/defaults.json` of `{"resolve_model_ids":"omit","runtime":"codex"}` plus `GSD_RUNTIME=claude`. `HOME` stays real (v1's search roots and the inventory are `$HOME`-relative). The poison fixture carries no `model_policy`. `GSD_HOME` does not cover `effort sync` or the installer, so the matrix never runs them.
- **D-09:** 5 combinations x 2 start paths (P1 no config at start; P2 pre-poisoned config, the plan carries the unset) plus 2 controls (Control 1 skips the fix and must fail every agent that has no override; Control 2 uses clean defaults and must pass). Measured cost about 30 s for 350 calls.
- **D-10:** an independent oracle built from the plan's set entries plus gsd-core's live `MODEL_PROFILES` and `AGENT_TO_PHASE_TYPE`, asserting both tables have the same agent keys; host-parameterized so Phase 20 reuses it; `recommend` emits no new field. Module `tests/test_ai_kit_gsd_curated_config_matrix.py`, registered in both test lists (or covered by 16.1's discovery), `skipUnless` real gsd-tools and node.
- **D-11:** fixtures built at run time by one builder from the real tools: B real `config-new-project` under the poisoned `GSD_HOME`; C 17 D-20's tables builder, opencode host, unscored, both routers; D real v1 subcommands plus per-leaf `model_policy` keys; E B's answers with an empty `other_clis`. No absolute paths committed.
- **D-12 pressure runs:** headless fresh-context `claude -p` sessions from a scratch cwd with tool allowlist `Read,Bash,Glob,Grep` (no Skill tool), limited `--setting-sources`, `--output-format stream-json`, under the 16.1 `child_env` scrub. Skill and CLI pinned to the worktree by a path discovered at run time. Any Skill-tool call is a harness failure. Grading per expectation: scripted end-state checks, ordering read from the documented transcript, rationalizations quoted verbatim. Scenario files in `skills/ai-kit-gsd-curated-config/evals/NN-*.md`. RED-b uses the v1 SKILL.md frozen from git (`2c16b26`).
- **D-13:** the smoke and matrix share one dev-only stdlib helper `tests/gsd_curated_eval.py` (`smoke`, `matrix`, `fixture`, `snapshot`); resolves the skill from its own repo location, never the installed symlink; evidence paths use placeholders; not shipped, not a skill subcommand (R8); precedent `tests/wizard_fixtures.py`.
- **D-14 smoke steps:** (1) snapshot sha256 of the protected set (ai-kit's `config.json`, its backups, `cross-ai.mjs*`, real `~/.gsd/defaults.json` read only); (2) on ai-kit run only inventory, recommend and the dry run; (3) project (a): resolve `needs_choice` with the first candidate ("smoke-auto"), dry run, apply, validate, check a second apply adds no extra state; (4) forced failure on a copy: non-array `review.default_reviewers`; (5) project (b) created with the real `GSD_HOME`, reconcile is family-wide (17 D-08), only key paths recorded; (6) run the matrix; (7) re-snapshot, exit 1 on any change.
- **Finding, not fixed here:** v1 integration tests run `ensure-project` without isolation (`tests/test_ai_kit_gsd_curated_config.py:182-219,1188-1274`); record for the v1-future decision.

### Claude's Discretion
- Where the evidence files live (suggested `19-SKILL-JUDGE.md`, `19-PRESSURE-TESTS.md`, `19-SMOKE.md` in the phase dir).
- The model and effort of the RED/GREEN subagents.
- The exact scenario prompts and fixture contents.
- The integration-test module layout.

### Deferred Ideas (OUT OF SCOPE)
- The decision on v1's future (later milestone; Phase 19 only gathers evidence).
- Cursor MVP and pi scenarios (Phases 21/22).
- Codex and opencode live validation (Phase 20); new capabilities of any kind (SPEC out of scope).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-01 | SKILL.md passes writing-skills RED/GREEN pressure scenarios B, C, D, E with no-skill and v1 baselines | Method in `testing-skills-with-subagents.md`; headless harness design, scoring and recording in "Established Facts 2"; SKILL.md gaps found in "Gap analysis: SKILL.md vs SPEC R1" |
| EVAL-02 | `/skill-judge` runs in code review; >=96/120, 0 Critical/Important | 18.1 loop precedent (digest pinning, pi lanes plus in-session judge, `check_digests.py`); SKILL.md currently judged 106-112/120 on digest `551234cc5f4f55cc` but any Phase 19 edit voids it |
| EVAL-03 | Live smoke on the claude host, scratch only, ai-kit config untouched | Pipeline run end to end this session on scratch projects; byte-level protocol in "Established Facts 3" |
| APP-05 | After `apply`, `resolve-model <agent>` with `GSD_RUNTIME=claude` returns the planned model for all 35 agents | 35 agents verified in gsd-core 1.16.0; poison reproduced; 5 combos applied and compared this session (0 mismatches, P1 path) |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- English only in every written artifact; no absolute machine-specific paths in source, tests or project assets (evidence files use placeholders such as `<worktree>`, `<scratch>`).
- Runtime code stays stdlib-only; the helper `tests/gsd_curated_eval.py` is dev-only and stdlib-only anyway (precedent `tests/wizard_fixtures.py`).
- Any new or materially updated `SKILL.md` passes the skill-judge loop (no Critical/Important or >=96/120, no regression vs baseline) before it is marked complete.
- One coherent buildable commit per logical change with tests and docs; never `--no-verify`; no `git reset --hard`/`git clean -f`; preserve unrelated dirty work; fold commits before closing.
- Never use the real `~/.claude`, `~/.cursor`, `~/.config/opencode` as test fixtures; use temp dirs and synthetic content. Ephemeral scratch under `./tmp/` (gitignored, verified `git check-ignore tmp`).
- Fix failing tests and defects; no "flaky/pre-existing" deflection. Live-verify against the installed tools before trusting a doc.
- `make test` and `make validate` green before done. Kill any spawned process after e2e verification (18.1-22 used a pid-snapshot leak check; reuse it).
- Plans must be reviewable cross-AI, executable by a cheap cross-AI model, and path-agnostic.
- Memory rules that apply: best design over smallest diff; jev advisory only at decision points; GSD is project-local only (`<checkout>/.claude/gsd-core/bin/gsd-tools.cjs`); parallelism never hardcoded (40% CPU cap); a `ponytail-review` pass over PLAN.md files beside the checker.

## Summary

Phase 19 builds no new product. Almost everything it must prove already runs: this session applied the v2 pipeline (inventory, recommend, dry-run, apply) on scratch projects against the checkout-local gsd-core 1.16.0, reproduced the `resolve_model_ids: "omit"` poison (`model: ""` for every agent, `tier` still correct), saw the plan unset it, and compared all 35 agents for the 5 combinations against an oracle with 0 mismatches. The repo already ships a hermetic-plus-real-node e2e tier (`tests/test_curated_config_apply_e2e.py`, 7 tests, 24 s, green at HEAD) with scratch `HOME`/`GSD_HOME`, byte-hash checks of the repo's own config and runner, forced-failure restore, re-apply no-op and the absent-config reconcile. The new work is therefore (1) the 5 x 35 resolve-model oracle test and its shared helper, (2) a headless `claude -p` pressure harness with scripted grading, (3) a small number of SKILL.md edits that the RED evidence will drive, (4) the skill-judge loop on the final digest, and (5) the recorded live smoke and evidence files.

Both locked documents are stale in places because they predate Phase 18.1 and later Phase 18 refinements. The most consequential: SPEC R1 says the current SKILL.md is v1 (it has led with v2 since Phase 18, `7009d22`, and was judged 106-112/120 in 18.1); B's "router-env/my-plan-review is the lane model" only holds when the router is user-confirmed, and in every golden fixture and in the real catalog cache it is not; the D-14 "forced failure" cannot be produced through `plan-set` (it refuses non-lists even with `--force`) and needs an edited copy of `plan.json`; D-10's "registered in both test lists" is now `E2E_MODULES` in the parallel runner plus a generated listing; and a global gsd-core 1.17.0 appeared at `~/.claude/gsd-core` during this research, so evidence must name the gsd-core version and path it used.

Two things in the SPEC must be handled by the orchestrator, not delegated: every task that needs a real Claude Code session (the `claude -p` RED/GREEN runs, the "from the claude host" smoke, the in-session skill-judge) and every decision. The cross-AI executor (pi through `.planning/scripts/cross-ai.mjs`, full permissions, host signals scrubbed, no TTY) can build the helper, the matrix module, scenario files, unit tests and evidence templates, and can run the pi judge lanes in review mode (precedent 18.1-21), but it cannot be "the claude host".

**Primary recommendation:** Build `tests/gsd_curated_eval.py` plus `tests/test_ai_kit_gsd_curated_config_matrix.py` (add to `E2E_MODULES`) first; run RED, then edit SKILL.md only where RED/GREEN evidence demands it (the known gaps are the review-pass diff wording, the managed-key unset, and an explicit "never skip dry run / `needs_choice`" rule); freeze SKILL.md; run the judge loop and the final GREEN on the same digest; run the smoke last, from the orchestrator's Claude session.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pressure-run harness (spawn `claude -p`, collect stream-json, grade) | Dev tooling (`tests/gsd_curated_eval.py`) | Orchestrator session (executes it) | Needs the user's Claude auth and a real session; not shipped, not a skill subcommand (D-13, R8) |
| Scenario definitions and expectations | Skill repo data (`skills/ai-kit-gsd-curated-config/evals/NN-*.md`) | — | Precedent `skills/ai-kit-spec-review/evals/0N-*.md` (Scenario / Prompt / Expected behavior / Pass criteria) |
| Fixture builder (poisoned project, v1-written config, opencode-host inventory) | Dev tooling, built at run time from real tools | Existing test builders (`seed_cache`, `_tables_fake`, `scratch_inventory`, `_golden_bundle`) | D-11: frozen fixtures can drift from real v1 output |
| resolve-model oracle and matrix | e2e test tier (`E2E_MODULES`) | Helper `matrix` subcommand (live run recorded in `19-SMOKE.md`) | Real node and real gsd-tools required; skipped when absent |
| Protected-set snapshot and byte-identity check | Dev tooling | — | Pure sha256 over files; also reusable by Phase 20 |
| Config writes in scratch | Existing skill `apply` (through gsd-tools) | — | The eval never writes config itself |
| Skill-judge | pi judge lanes via the shipped runner in review mode, plus in-session judge | Orchestrator (digest check, verdict) | 18.1-21/22 precedent; in-session judge alone never passes a skill |
| Evidence files | Phase dir | VERIFICATION.md references them | SPEC R7 |

## Established Facts (evidence from this session)

### 1. Agents, `resolve-model`, and the poison

- **35 agents.** `node -e` over `.claude/gsd-core/bin/lib/model-profiles.cjs` (the exports `MODEL_PROFILES`, `AGENT_TO_PHASE_TYPE`, `AGENT_DEFAULT_TIERS`) printed 35, 35 and 35 keys; the two tables have identical key sets (diff empty both ways); `.claude/agents/` also holds 35 `gsd-*.md` files (not authoritative). `.claude/gsd-core/VERSION` is `1.16.0`. A global `~/.claude/gsd-core` with VERSION `1.17.0` appeared at 01:30 local time during this research (not there at session start; the 2026-10-14 memory says no global GSD) and also reports 35 agents. [VERIFIED: node require of model-profiles.cjs, 2026-10-17]
- **Which command lists them:** none. `gsd-tools agent` only has `classify-failure`; there is no `list` verb. The only live source is the `node -e` require that `gsd_catalog.query_agent_catalog` already uses (`gsd_catalog.py` `_AGENT_CATALOG_QUERY_SCRIPT`). The oracle must reuse it, never a hardcoded list. [VERIFIED: gsd-tools agent output "Unknown agent subcommand. Available: classify-failure"]
- **Output shape.** `resolve-model <agent>` (no `--raw`) prints `{"model","profile","effort","tier"}`; `--raw` prints only the model (empty string when omitted). One call takes about 0.07 s, so 12 runs x 35 is about 30 s. [VERIFIED: ran it]
- **The poison reproduces exactly as the SPEC says.** With `GSD_HOME` holding `{"resolve_model_ids":"omit","runtime":"codex"}`, `gsd-tools config-new-project` printed `created`; the new project config had `resolve_model_ids: "omit"` and `runtime` absent (not copied) and `model_profile: "balanced"`. `GSD_RUNTIME=claude resolve-model gsd-planner` then returned `{"model": "", "profile": "balanced", "effort": "xhigh", "tier": "opus"}`. After `config-set model_overrides.gsd-executor haiku` that agent returned `model: "haiku"`, `tier: "haiku"`. `GSD_RUNTIME=codex` returned `model: "gpt-5.6-sol"` for the planner. A clean `GSD_HOME` (scratch HOME with no `~/.gsd`) returned `model: "opus"`. [VERIFIED: ran it, scratch HOME]
- **New stderr noise.** Every gsd-tools call under a project config prints `gsd-tools: warning: <GSD_HOME>/.gsd/defaults.json sets resolve_model_ids, runtime but a project config takes precedence here ... (#3532)`. The matrix must read JSON from stdout and never treat stderr as failure. [VERIFIED: ran it]
- **After a v2 apply the plan's unset lands.** Plan entry (verbatim from `plan.json`): `{"existing": "omit", "key": "resolve_model_ids", "op": "unset", "source": "preset", "value": null, "why": "resolve_model_ids omit makes resolve-model return an empty model for every agent without a per-agent override on a claude host"}`. On an existing-config project it is an ordinary `unset` row in the diff (`kind: "remove"`); on an absent config it is `reconciled` (covered by `test_absent_config_reconciles`). [VERIFIED: ran apply, scratch]
- **Five combinations applied in sequence on one scratch project (P1 path, claude host, no other CLIs, no cross-AI): `mvp/adaptive`, `adaptive/rigorous`, `adaptive/standard`, `quality/standard`, `budget/standard`. After each apply, `resolve-model` for all 35 agents compared to an oracle (`model_overrides.<agent>`, else `models.<phase_type>`, else `MODEL_PROFILES[agent][profile]`): 0 mismatches on both `model` and `tier` every time.** The phase shifts are realized as `models.<phase>` keys (`mvp`: `models.research=haiku`, `models.verification=haiku`; `rigorous`: `models.planning=opus`, `models.verification=sonnet`, `presets.py:101-104`); stale `models.*` keys are cleared when a later rigor has no shift (config ended with `models: {}`). **Caveat:** this oracle read `models` from the applied config, so it proves gsd-tools honors the config, not that the config equals the plan. The Phase 19 oracle must be built from the plan's entries (D-10) plus `PHASE_SHIFTS`/`MODEL_PROFILES`, not from the applied config. [VERIFIED: ran it]
- **A gap the matrix as specified will not see.** `apply` leaves a project-level `runtime: codex` in place on a claude host (plan emits only a `runtime_mismatch` note "the plan writes no runtime entry on claude (D-30); change it with plan-set runtime claude"). With `GSD_RUNTIME` unset, `resolve-model` then returned the codex model `gpt-5.6-sol` with `tier: opus`. The APP-05 matrix always sets `GSD_RUNTIME=claude`, which masks it. Claude Code sessions do not set `GSD_RUNTIME` (not in this session's env). See Open Question 2. [VERIFIED: ran it on `run4` scratch]

### 2. The writing-skills RED/GREEN method, and how to run it here reproducibly

- **Method source.** `superpowers:writing-skills` plus `testing-skills-with-subagents.md` (same directory, plugin 7.0.0): RED = run the scenario without the skill and record choices and rationalizations verbatim; GREEN = same scenario with the skill; REFACTOR = add counters for each new rationalization and re-verify; scenarios need 3+ combined pressures, concrete options, real paths, "act, don't answer". Meta-testing question after a failure: "how could the skill have been written differently". [CITED: plugin `superpowers/7.0.0/skills/writing-skills/testing-skills-with-subagents.md`]
- **Harness (D-12) flags confirmed against `claude --help` (Claude Code 2.1.301):** `-p/--print`, `--output-format stream-json` (needs `--verbose` with `--print` in practice [ASSUMED]), `--tools <tools...>` ("Specify the list of available tools from the built-in set"), `--setting-sources <sources>` (user, project, local), `--disable-slash-commands` ("Disable all skills"), `--model`, `--effort`, `--session-id <uuid>`, `--no-session-persistence`, `--permission-mode`, `--strict-mcp-config`, `--add-dir`. Use `--tools "Read,Bash,Glob,Grep"` (this removes the Skill tool; `--allowedTools` only pre-approves and does not remove tools). `--bare` skips CLAUDE.md discovery, hooks and plugins but requires `ANTHROPIC_API_KEY`; this machine authenticates through `~/.claude/.credentials.json` (OAuth), so `--bare` is unusable here. [CITED: `claude --help`, 2.1.301]
- **Known confound that cannot be removed:** `~/.claude/CLAUDE.md` (user memory: tool guidance, CodeGraph, graphify lines) still loads in every `claude -p`. It is constant across RED and GREEN, so it does not bias the comparison; record it as a controlled confound in `19-PRESSURE-TESTS.md`. `--setting-sources project` run from an empty scratch cwd drops the user's `enabledPlugins`, hooks (the superpowers/ponytail SessionStart/SubagentStart hooks) and the global skill listing. `--disable-slash-commands` removes the skill listing so the v1 skill's description cannot leak into the no-skill baseline. [CITED: help text; behavior ASSUMED until the Wave 0 spike]
- **Delivering the skill without the Skill tool:** with the tool removed, GREEN works by putting the absolute path of the worktree's `SKILL.md` in the prompt ("Follow the skill at <path>; read it first"), and the entrypoint resolves from "the script beside the instructions you are following always wins" (SKILL.md "Resolve the entrypoint"), so the worktree script runs, never the installed symlink. RED-a prompt names only the gsd docs and the CLI help; RED-b names the frozen v1 SKILL.md copied to a scratch path (see Reconciliation R-5 for which commit).
- **Pin the CLI to the worktree.** `resolve_gsd_tools` (`gsd_tools.py:38-40`) takes root = `RUNTIME_DIR`, else the git toplevel of the cwd; a scratch project has neither a local gsd-core nor the worktree as toplevel, so it would resolve the machine's global gsd-core (now 1.17.0). Fix per run: set `RUNTIME_DIR=<worktree>` in the child env, or symlink `<scratch>/.claude/gsd-core -> <worktree>/.claude/gsd-core` (verified: inventory then reports `gsd_core.scope: "local"`, `version: "1.16.0"`, `host: claude (detected)`). Copying the directory instead does not work: `lib/command-roster.cjs:36` requires `../../../scripts/fix-slash-commands.cjs` and `capability-loader.cjs:395,594` require `gen-capability-registry.cjs`, both under `.claude/scripts`. The symlink also makes the `effort_sync` follow-up appear (it needs `scope == local`; `followups.py` `local_gsd_tools`), which scenario E needs for its "one grouped confirmation". [VERIFIED: ran it]
- **Single-shot problem and the fix.** `claude -p` has no user to answer. Expectations "the agent asks rather than invents" and "one grouped confirmation after apply" sit at different points in one conversation. Use turn scripts: turn 1 = scenario prompt, run ends when the agent stops (a question at a `needs_choice` counts as the "asked" pass); turn 2+ = scripted user answers (`claude -p --resume <session-id>` with the same `--session-id`, session persistence on). Keep every scripted answer in the scenario file. This needs a Wave 0 spike (flags, transcript location, `--resume` semantics under `--tools`). [ASSUMED: `--resume` plus `-p` multi-turn behavior]
- **Fixture rule for B and C.** The router wins a slot only if `heuristic_confirmed` contains `is_router` in its catalog entry (`catalog_adapter.py:383-384`). The test fixture confirms `router-env/my-coding` but not `router-env/my-plan-review`, and the real cache `~/.cache/ai-kit/spec/model-catalog.json` has neither confirmed (read-only check: both entries have keys `provider, runtimes, is_router, batch_mode, fallback_quota, name_declared_purpose, source, confidence, last_verified`, no `heuristic_confirmed`). So B and C must run against a seeded cache with both routers confirmed (the repo's `seed_cache(xdg_cache_home, runtimes, catalog)` writes `XDG_CACHE_HOME/ai-kit/spec/`, and `cache.py:10-11` honors `XDG_CACHE_HOME`), not against the real cache. This does not conflict with D-08's "HOME stays real": only `XDG_CACHE_HOME` and `GSD_HOME` are overridden. [VERIFIED: read the code and the cache]
- **Grading (per expectation, scripted where possible):**
  - End-state checks read the scratch `config.json`/`plan.json`/`inventory.json` (the harness sets `TMPDIR=<scratch>/tmp` so the skill's `mktemp -d` lands inside the run dir): B asserts lane count 2, `review.models.opencode == router-env/my-plan-review`, `workflow.cross_ai_command == "node .planning/scripts/cross-ai.mjs"`, `script` artifact `models.pi == router-env/my-coding`, `intel.enabled` and `dynamic_routing.enabled` true, no `model_profile_overrides.claude.*` keys, `resolve_model_ids` absent after apply; C asserts `status: needs_choice` entries present at stop and no `plan-set --force`; D asserts every `remove` key in the dry-run diff appears in the agent's text; E asserts a `--dry-run` apply precedes the real apply.
  - Ordering is read from the Bash `tool_use` events in the stream-json transcript (first index of each subcommand).
  - Skill-tool use: any `tool_use` with `name == "Skill"` is a harness failure (cannot happen with `--tools` but assert anyway).
  - Rationalizations are quoted verbatim from assistant text blocks.
- **Recording.** `19-PRESSURE-TESTS.md`: per scenario a table with rows = expectations and columns RED-a, RED-b (B, D only), GREEN, each cell `pass|fail` plus a one-line verbatim quote and transcript reference; header carries `claude --version`, the model id from the `system/init` event, effort, the SKILL.md digest (18.1's DIGEST_CMD), and the gsd-core version. A closing "what v1 got right or wrong" section. Raw stream-json goes under `tmp/` (gitignored); commit only trimmed transcripts (assistant text plus Bash commands and exit codes) under the phase dir so the evidence is checkable and small.
- **Discrimination rule (SPEC R3).** A baseline that passes every expectation must state why the scenario still discriminates; the cheapest honest reason is a scripted expectation the baseline cannot know (for example `resolve_model_ids` unset, which only the plan carries).
- **Cost and cadence.** Minimum 10 runs (RED: B x2, D x2, C, E; GREEN: 4), realistically 20-30 with REFACTOR re-runs. Fix model and effort across all runs (suggest one alias, `--model sonnet --effort medium`, recorded from the init event) so RED vs GREEN differ only by the skill. Single sample per cell (D-02); a REFACTOR cap of 3 rounds is recommended by analogy with D-07 (Open Question 4).

### 3. "Without corrupting the scratch project's config" - what to check

Constants (verbatim, `config_backup.py:17-21`): `BACKUP_PREFIX = "config.json.bak-"`, `KEEP = 3`, `MARKER_SUFFIX = ".ai-kit-apply-marker"`, `SNAPSHOT_SUFFIX = ".ai-kit-apply-backup"`.

After each real apply, assert:
1. **Parses and round-trips.** `json.load` succeeds; for each key the plan set, `gsd-tools config-get <key>` equals the planned value; `resolve-model` for the 35 agents returns well-formed JSON (a corrupt config silently falls back to builtin defaults with a warning, so a parse check alone is not enough).
2. **Backup exists and equals the pre-apply bytes.** Exactly one new `config.json.bak-<stamp>` beside the config, sha256 equal to the pre-apply config (backups are pruned to `KEEP = 3`, so compare against the newest, not the count).
3. **No leftover state.** No `config.json.ai-kit-apply-marker`, no `config.json.ai-kit-apply-backup`, no `.bak-tmp-*` temp file (verified: after a successful apply and after a forced failure, `.planning/` held only `config.json`, backups and `scripts/`).
4. **Second apply of the same plan:** zero `config-set` calls, config bytes identical, exactly one extra backup (bounded by `KEEP`), third apply reuses (`backup.reused: true`). This is what `test_reapply_is_noop` asserts and what I observed (`writes: []`, `applied: true`, new backup). It is not "no extra state" (CONTEXT D-14); see R-9.
5. **Forced failure restores.** Reproduced: copy `plan.json`, flip the `review.default_reviewers` entry from `op: unset` to `op: set, value: "notarray"`, apply. Result: exit 1, `failed_key: "review.default_reviewers"`, error `config-set review.default_reviewers failed: Error: review.default_reviewers must be a JSON array of reviewer slugs`, `restore_error: null`, config sha256 identical before and after, one more backup, no marker. `plan-set` cannot make this plan (it refuses non-lists, exit 2, even with `--force`), so the helper must edit the plan copy; a plan with a duplicate key is refused (exit 2, "duplicate entry key"), so edit the existing entry, do not append. [VERIFIED: ran it]
6. **Dry-run writes nothing:** tree sha256 over `.planning/` (excluding `.git`) identical before and after `apply --dry-run` (verified on scratch).
7. **ai-kit protected set, byte-identical before and after the whole smoke:** `.planning/config.json`, any `config.json.bak-*`/marker/snapshot beside it, `.planning/scripts/cross-ai.mjs*` (the repo's runner is `template=1` per its header; it is never upgraded here), and the real `~/.gsd/` tree (file list plus sha256; only reads are expected; `defaults.json` currently has keys `branching_strategy, commit_docs, graphify, hooks, intel, mode, model_profile, plan_review, resolve_model_ids, review, runtime, workflow`). Do not snapshot all of `.planning/` (STATE changes during a session). Existing precedent: `test_apply_golden_plan` hashes `_REPO_CONFIG` and `_REPO_RUNNER` before and after.
8. **Record key paths only, never values, for project (b)** (real global defaults can carry anything).

### 4. What a cross-AI executor can and cannot do here

- **Mechanism.** `workflow.cross_ai_execution: true` with `workflow.cross_ai_command: "node .planning/scripts/cross-ai.mjs"`; plans carry `cross_ai: true`; the 18.1 plans show frontmatter `executor: cross-ai (pi router-env/my-coding)` and `orchestrator_verify: "VERIFY ..."`. The runner (`.planning/scripts/cross-ai.mjs`, here template 1; the shipped template is 3) runs pi with the full-permission formula, no TTY, the outer timeout `workflow.cross_ai_timeout` (1800 s), and scrubs host-signal env vars (`runner_dispatch.child_env`, `detection.py:201` `HOST_SIGNAL_ENV_VARS`).
- **Can delegate (pure repo work, hermetic or real-node):** writing `tests/gsd_curated_eval.py` and `tests/test_gsd_curated_eval.py` (unit tests for snapshot, oracle, grader, fixture builder); the matrix e2e module; scenario files under `skills/ai-kit-gsd-curated-config/evals/`; the digest-check script and evidence templates; SKILL.md edits once the failing evidence exists; the pi judge lanes in review mode (18.1-21 precedent: pi `openai/gpt-6.1-sol:xhigh` scored; `zai-coding-cn/glm-5.3:xhigh` returned `AIKIT-XAI status=capacity exit=75` and was recorded verbatim as unavailable); `make test`/`make validate` runs.
- **Cannot delegate (mark `autonomous: false` / orchestrator-only):**
  - Anything that needs "a real Claude Code session": the `claude -p` RED/GREEN runs (use the user's Claude OAuth quota unattended otherwise, and a pi child has the host signals scrubbed so any host detection inside it says `unknown`/pi, not claude); the live smoke "from the claude host" (EVAL-03 is about the claude host; inventory exit 2 asks for `--host` when undetectable); the in-session `/skill-judge` (needs the Skill tool).
  - Every decision point: accept/refuse a score after 3 fix iterations (D-07, user), `--force` pins in the smoke, and the REFACTOR stop.
  - Verification of gate results and digests (the orchestrator re-runs `make test`/`make validate`/`make e2e-docker` and the digest check, as in 18.1-22).
- **Constraints on a delegated plan:** commands must be path-agnostic; the executor should call `inventory` with `--host claude` explicitly in tests (no host env inside pi); it must leave no process behind (take a pid snapshot before, compare after, as 18.1-22 did); and a cheap model needs the helper's CLI contract spelled out in the plan (see "Helper contract").

## Reconciliation with Phase 18.1

Every row: locked text, current fact with `file:line`, minimal formal amendment. The orchestrator amends SPEC/CONTEXT/REQUIREMENTS; this research edits none of them.

| # | Locked text | Current fact (HEAD) | Minimal amendment |
|---|-------------|---------------------|-------------------|
| R-1 | SPEC R1 "Current: the v1 SKILL.md" | `skills/ai-kit-gsd-curated-config/SKILL.md:9-13` "**Primary path:** the v2 pipeline ... **Secondary path:** the kept v1 flow"; v2 rewrite landed in `7009d22` (2026-10-15); judged 106-112/120 in `18.1-SKILL-JUDGE.md`; `test_v2_is_primary` (`tests/test_curated_config_apply.py`) pins it | R1 Current: "SKILL.md already leads with v2 (Phase 18, EVAL-06). Remaining delta: review-pass diff wording, managed-key unset, never-skip rules found by RED." Re-point EVAL-01's "rewritten" wording the same way (REQUIREMENTS EVAL-01 is otherwise accurate). |
| R-2 | SPEC R1 step order: "four questions, `inventory`, `recommend`, ..." | SKILL.md step 1 is `inventory`, step 2 asks the four questions, step 3 `recommend` (SKILL.md "Run the v2 flow") | Amend R1 Target order to "inventory, the four questions, recommend, review pass, needs_choice via plan-set, apply --dry-run, apply, one grouped follow-up approval" (matches the judged file; reordering SKILL.md would void its judge result for no gain). |
| R-3 | CONTEXT D-01 D "add/change/keep/`unset` diff"; SPEC R1 "add/change/keep/remove diff" | The two documents disagree. Dry-run diff row kinds are `add`/`change`/`keep`/`remove` (`apply.py:119-125`: `if op == "unset": return "keep" if live is None else "remove"` ... `return "add" if live is None else "change"`); `unset` is the plan entry op (`plan_io.py:646` `if op not in ("set", "unset", "keep")`). SKILL.md step 3 reviews only `needs_choice`, notes, warnings and `effect` flags; the diff appears only in the step 4 dry run | CONTEXT D-01 D: "add/change/keep/remove diff (plan op `unset` shows as `remove`)". SKILL.md step 3/4 must tell the agent to present every `remove` row (R1 gap; see below). |
| R-4 | SPEC R2 / CONTEXT D-01 B "`router-env/my-plan-review` as the opencode lane model (17 D-04)"; D-01 C "`router-env/my-coding` wins the execution override" | 17 D-04 says "**user-confirmed** `name_declared_purpose`"; `catalog_adapter.py:383-384` `confirmed = entry and "is_router" in (entry.get("heuristic_confirmed") or [])`, `router_ok = is_router and confirmed and declared in _ROUTER_PURPOSES`. Goldens: `opencode-*-adaptive.json` carry note `router_unconfirmed router router-env/my-plan-review ...`; `claude-rigorous-adaptive.json` has `review.models.opencode = zai-coding-plan/glm-5.3`, not the router. Real cache lacks `heuristic_confirmed` for both routers | B/C: "when the router is user-confirmed (`heuristic_confirmed` contains `is_router`); the scenario fixture confirms both routers. Unconfirmed -> `router_unconfirmed` note, router does not win." |
| R-5 | CONTEXT D-12 "RED-b uses the v1 SKILL.md frozen from git (`2c16b26`)" | `2c16b26` is the 07-04 file (171 lines). Later v1-era edits (`50564a6`, `f87f52d`: prerequisites, exit-2 causes, trust model, `detect-*-candidate` flags) preceded the v2 rewrite `7009d22`; `7009d22^` is 194 lines and is the v1 the user last had. The v1 subcommands still exist unchanged (CLI `--help`) | "frozen from git at `7009d22^`" (last v1 SKILL.md). If the user prefers the originally judged 105/120 file, keep `2c16b26` and say so; record the commit in the evidence either way. |
| R-6 | CONTEXT D-10 "registered in both test lists (or covered by 16.1's discovery)" | The runner now discovers `tests/test_*.py`; a module needing real node goes in `E2E_MODULES` (`tools/run_unittest_parallel.py:53-61`, which already lists `tests.test_curated_config_e2e` and `tests.test_curated_config_apply_e2e`); `tools/gen_test_groups.py` refreshes the generated listing; `tests/test_gate_scope.py` fails while it is stale | "Add `tests.test_ai_kit_gsd_curated_config_matrix` to `E2E_MODULES`, run `python3 tools/gen_test_groups.py`; any hermetic helper test (`tests/test_gsd_curated_eval.py`) joins `unit` automatically." |
| R-7 | CONTEXT canonical_refs `~/.claude/gsd-core/bin/gsd-tools.cjs`; ROADMAP criterion 4 "the real installed gsd-tools" | GSD is project-local only; the tests use `REPO_ROOT/.claude/gsd-core/bin/gsd-tools.cjs` (1.16.0, gitignored). A global `~/.claude/gsd-core` 1.17.0 appeared 2026-10-17 01:30 | Canonical ref -> `<checkout>/.claude/gsd-core/bin/gsd-tools.cjs`; criterion 4 -> "the checkout-local gsd-core (1.16.x), version recorded in `19-SMOKE.md`". |
| R-8 | CONTEXT D-14 step 3 "resolve `needs_choice` with the first candidate ("smoke-auto")" | In a scratch HOME `artifacts[0].choices.<runner>.candidates` is `[]`; `plan-set script:cross-ai.model.pi smoke-auto` exits 2 "'smoke-auto' is not listed for pi in the inventory; pass --force to pin it anyway"; with `--force` it applies (`plan_edit.py:208-211`). SKILL.md forbids habitual `--force` | "first listed candidate where one exists, else a `--force` pin of a placeholder model id (helper only, recorded as such)." |
| R-9 | CONTEXT D-14 step 3 "a second apply adds no extra state" vs SPEC edge R5 idempotency "changes nothing but adds a backup" | Observed and asserted by `test_reapply_is_noop`: second apply = zero `config-set`, identical bytes, `backup.reused: false`, one more backup; third reuses. The two documents disagree | CONTEXT D-14: "second apply writes no config keys and leaves config bytes identical; it adds one backup (pruned at `KEEP = 3`)". |
| R-10 | CONTEXT D-14 step 4 "forced failure on a copy: a non-array `review.default_reviewers`, which the real gsd-tools rejects" | Still true in gsd-tools ("must be a JSON array of reviewer slugs", exit 1) but `plan-set review.default_reviewers notarray` is refused by ai-kit (exit 2: "expected a JSON list of strings"), even with `--force`. Only an edited copy of `plan.json` reaches gsd-tools | "forced failure: a copy of the plan with the `review.default_reviewers` entry edited to `op: set`, `value: "notarray"` (helper edits the copy; `plan-set` cannot)". Add: expected exit 1, config bytes restored, no marker. |
| R-11 | CONTEXT D-08 poison fixture "(`resolve_model_ids`, `runtime`) copied at creation" | `config-new-project` copies `resolve_model_ids` but not `runtime` (project `runtime` absent); gsd-tools prints stderr warning #3532 on every call; a project-level `runtime: codex` is left by `apply` (D-30) | D-08/D-09 note: "poison reaches the project config only as `resolve_model_ids`; stderr is not a failure signal." The `runtime` gap is Open Question 2. |
| R-12 | SPEC R2 "run as subagents with the v2 SKILL.md" | CONTEXT D-12 already refines this to headless `claude -p`; the SPEC text and the discussion log still say subagent | SPEC R2: "run as fresh-context headless `claude -p` sessions (19 D-12)". |
| R-13 | SPEC Edge `ordering R8` UNRESOLVED: must GREEN repeat when a later fix changes SKILL.md? | The judge loop is digest-bound in 18.1 (`DIGEST_CMD` over SKILL.md plus `references/`; "every SKILL.md or reference fix re-runs every judge on the new digest") | Resolve: yes. GREEN, like each judge row, is valid only for the SKILL.md digest it ran against; any edit after GREEN (including a judge-loop edit) re-runs B-E on the final digest. Evidence rows carry the digest. |
| R-14 | SPEC R2 B "the ponytail set within the cap"; D-01 B "intel.enabled and dynamic_routing.enabled on" | `presets.py:17` `SKILL_CAPS = {"mvp": 2, "standard": 3, "rigorous": 5}`; rigorous preset sets `intel.enabled: True`, `dynamic_routing.enabled: True` (`presets.py` rigorous block); standard has no `dynamic_routing` | Holds for B (Rigorous). No amendment; the matrix's Standard/MVP rows must not assert `dynamic_routing`. |
| R-15 | D-01 B "no layer-2 keys on claude (17 D-01)" | `recommend.py:328-331` `def _slot_layer(...)`: `if ctx.host == "claude": return [], []` | Holds. Note: `model_overrides.gsd-executor`/`gsd-code-fixer` (layer 2c, specialists) can still appear on claude (golden `claude-rigorous-adaptive.json`: `haiku`); the oracle must treat them as overrides. |
| R-16 | SPEC Background "Phase 18.1: candidates are (runtime, model) pairs"; no `native_runtime` | `grep` of `19-SPEC.md` and `19-CONTEXT.md` finds no `native_*` or `cursor-agent`; REQUIREMENTS INV-01 already amended | None. |
| R-17 | SPEC "gsd-core 1.16 still has 35 agents" and R6 "all 35" | Verified: 35 in 1.16.0 (and in global 1.17.0) | None. Add the version to evidence. |
| R-18 | CONTEXT D-09 "about 30 s for 350 calls" | 1 call about 0.07 s; 12 runs x 35 = 420 calls about 30 s | None (the "350" is 10 runs; with 2 controls it is 420). |
| R-19 | CONTEXT D-12 "under the 16.1 `child_env` scrub" | `child_env` now lives at `ai_kit_spec/runner_dispatch.py:130` and strips `HOST_SIGNAL_ENV_VARS` (`detection.py:201`) | Pointer only: "`runner_dispatch.child_env` (18.1)". Note the scrub also removes `CLAUDECODE`; `claude -p` sets its own, so inventory inside the run still detects `claude`. |

### Gap analysis: SKILL.md vs SPEC R1 (what the RED evidence is expected to confirm)

Read this session (`SKILL.md`, 285 lines). Present and enforced by tests: the four questions, inventory, recommend, `plan-set`/`plan-unset`, dry-run, apply, one grouped follow-up approval, cursor/pi "not live-validated", v1 secondary. Missing or weak:
1. Step 3 ("Review the plan with the user") does not tell the agent to show `unset`/`remove` rows or the add/change/keep diff, nor that a copied `resolve_model_ids: "omit"` is proposed for unset and why. (Scenarios B and D expectations.)
2. No rule that the dry run is never skipped and `needs_choice` is never bypassed under "just apply it" pressure (scenario E). The NEVER list has no such bullet.
3. Nothing about the managed-key families being authoritative (17 D-08): v2 `apply` removes user keys it manages (observed on a copy of this repo's config: `model_overrides.gsd-planner: fable`, `agent_skills.*: ["global:jev-fast-decision"]`, `review.default_reviewers`, `effort.agent_overrides.*` all appear as `remove` rows). Scenario D needs the agent to surface this, not hide it.
4. Any addition must keep `TestSkillDocCommands` green (`tests/test_curated_config_apply.py`): every bash example uses `"$ENTRYPOINT"` and no `--force`; no heading containing "v1"; the `required` phrase list (including `"not live-validated"`, `"full permissions"`, `"approve_with"`, `"Ask the user"`) must stay; no "on this machine" wording. Put new prose in the existing structure or in `references/` (a new reference is part of the judge digest).

## Standard Stack

No external packages are installed by this phase. Everything is stdlib Python plus the existing skill, `node`, and gsd-core.

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| gsd-core (checkout-local) | 1.16.0 (`.claude/gsd-core/VERSION`) | `resolve-model`, `config-new-project`, `config-set` | The "real installed gsd-tools" for this repo [VERIFIED: file read] |
| node | v24.21.0 (volta shim; tests use `_real_node_executable()`) | runs gsd-tools | Existing e2e pattern, `tests/test_curated_config_e2e.py` |
| Python stdlib `unittest` | python3 3.14.7 here; repo targets py312 | helper unit tests, matrix module | Project test runner (`tools/run_unittest_parallel.py`) |
| `claude` CLI | 2.1.301 | headless pressure runs | D-12; flags confirmed from `--help` |
| `pi` via `.planning/scripts/cross-ai.mjs` | pi 1.3.0 | cross-AI execution, pi judge lanes | 18.1-21/22 precedent |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `tests/test_curated_config_apply.py` helpers (`_scratch_env`, `_tables_fake`, `scratch_inventory`, `_decide_all_choices`) | in repo | build hermetic inventories and plans | Matrix and fixture builder reuse; do not duplicate |
| `tests/test_curated_config_apply_e2e.py` (`_golden_bundle`, `_real_run`, `_direct_apply`, `_gsd16_or_skip`) | in repo | scratch `HOME`/`GSD_HOME`/`XDG_CACHE_HOME`, real apply | The matrix imports these instead of re-deriving the env |
| `skill-judge` skill | installed under `~/.claude/skills/skill-judge/` | 120-point rubric | EVAL-02 |
| `superpowers:writing-skills` | plugin 7.0.0 | RED/GREEN method | EVAL-01 |
| `uv` | 0.11.28 | `make test-integration`/`e2e-test` run under uv | Gates only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Headless `claude -p` pressure runs (D-12) | In-session subagents | Subagents inherit this repo's AGENTS.md and the global skill listing (including v1), contaminating the no-skill baseline - already decided against |
| Scripted grading | LLM grader | Cheaper but a second source of variance; use only for prose expectations, and log its verdict next to the quote |
| `--bare` | — | Unusable: needs `ANTHROPIC_API_KEY`, machine uses OAuth |

**Installation:** none. **Version verification:** versions above read from files and `--version` outputs on 2026-10-17.

## Package Legitimacy Audit

No external packages are recommended or installed by this phase (stdlib only; all tools already present). `npm`/`pip`/`cargo` legitimacy gate: not applicable.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### Evaluation data flow

```
scenario file (evals/NN-*.md)            fixture builder (tests/gsd_curated_eval.py fixture)
  prompt + turn script + expectations ──► scratch run dir:
                                           proj/ (git init, .claude/gsd-core -> symlink to worktree)
                                           home-less env: GSD_HOME=<run>/gh (poison), XDG_CACHE_HOME=<run>/xdg (seeded catalog),
                                                          TMPDIR=<run>/tmp, RUNTIME_DIR=<worktree>
                                                │
snapshot(protected set) ── before ─────────────┤
                                                ▼
        orchestrator ──► claude -p --tools Read,Bash,Glob,Grep --setting-sources project
                          --disable-slash-commands --output-format stream-json (turn 1, then --resume turns)
                                                │ stream-json
                                                ▼
                         grader: end-state checks (config/plan/inventory in run dir)
                                 + ordering (Bash tool_use sequence) + verbatim quotes
                                                │
snapshot(protected set) ── after ──► diff must be empty ──► 19-PRESSURE-TESTS.md row (+ SKILL.md digest)

smoke / matrix (same helper):
  plan (recommend --rigor ... ) ► apply ► for agent in live agent list: gsd-tools resolve-model (GSD_RUNTIME=claude)
                                  ► compare {model,tier} to oracle(plan entries + live MODEL_PROFILES + PHASE_SHIFTS + AGENT_TO_PHASE_TYPE)
```

### Recommended file layout
```
tests/gsd_curated_eval.py                      # dev-only stdlib helper: snapshot | fixture | smoke | matrix | grade
tests/test_gsd_curated_eval.py                 # hermetic unit tests (unit group, automatic)
tests/test_ai_kit_gsd_curated_config_matrix.py # real-node 5 x 2 x 35 (+2 controls); add to E2E_MODULES
skills/ai-kit-gsd-curated-config/evals/01-claude-rigorous-cross-ai.md   # B
skills/ai-kit-gsd-curated-config/evals/02-opencode-routers-no-catalog.md # C
skills/ai-kit-gsd-curated-config/evals/03-v1-written-config.md          # D
skills/ai-kit-gsd-curated-config/evals/04-just-apply-it.md              # E
.planning/phases/19-evaluation-on-claude/19-SKILL-JUDGE.md, 19-PRESSURE-TESTS.md, 19-SMOKE.md
.planning/phases/19-evaluation-on-claude/pressure/ and skill-judge/       # trimmed transcripts and judge reports
```

### Pattern 1: Hermetic scratch env for the real tools
Reuse `_scratch_env(home, gsd_home, xdg)` and `_golden_bundle(scratch, with_planning=...)` from the existing e2e tier. They already give a scratch `HOME`, `GSD_HOME`, `XDG_CACHE_HOME`, a seeded catalog, a project, `RUNTIME_DIR` for gsd-tools resolution and a decided plan. The matrix is a loop over (profile, rigor) x (P1, P2) x {fix, control}.
```python
# Source: tests/test_curated_config_apply_e2e.py (golden_bundle / test_absent_config_reconciles)
bundle = _golden_bundle(scratch, with_planning=False)           # P1
defaults = {"resolve_model_ids": "omit"}                       # poison; no model_policy (D-08)
```

### Pattern 2: Independent oracle (D-10)
Compute the promise from the plan, never from the applied config:
```python
# tier for agent: plan override > plan models.<phase> > live MODEL_PROFILES[agent][profile]
def promised(agent, plan, tables):                   # tables from the node -e require, as gsd_catalog does
    sets = {e["key"]: e["value"] for e in plan["entries"] if e["op"] == "set"}
    return (sets.get(f"model_overrides.{agent}")
            or sets.get(f"models.{tables['phase'][agent]}")
            or tables["profiles"][agent][plan["profile"]])
# assert set(tables["profiles"]) == set(tables["phase"])   # same 35 keys (D-10)
# compare resolve-model JSON: out["model"] == promised and out["tier"] == promised
```
`model_profile` itself comes from the plan's `model_profile` set entry (the plan's `profile` field). An empty `model` is a failure; the plan never promises inheritance on claude because it always unsets `resolve_model_ids`, so pass an `inheritance_promised=False` parameter that Phase 20 can override.

### Pattern 3: Protected-set snapshot (D-14)
`{path: sha256}` for files, plus a sorted name list for directories (`~/.gsd/`, ai-kit `.planning/` backups/runner glob). Compare dicts; exit 1 on any difference. Reads only. Paths are discovered from the repo root at run time, never literals.

### Pattern 4: Pointer-pinned CLI
For every spawned `claude -p`, set `RUNTIME_DIR=<worktree root>` (or symlink the project-local gsd-core) and tell the agent the worktree `SKILL.md` path. The entrypoint rule in SKILL.md then picks the worktree script.

### Helper contract (for a cheap executor)
`python3 tests/gsd_curated_eval.py <cmd>`: `snapshot --out F` / `snapshot --check F` (exit 1 on drift); `fixture <B|C|D|E> --run-dir DIR` (build the scratch project, env file, seeded catalog; print JSON with paths); `matrix [--json] [--no-controls]` (5 x 2 + 2 controls x 35; exit 1 on any mismatch; print only agent, combo, expected, got); `smoke [--host claude] [--evidence-out F]` (D-14 steps 1-7 with placeholders in output); `grade <scenario> --transcript T --run-dir DIR`. All subprocesses get an explicit env; no absolute paths in output; one test per subcommand's pure parts.

### Anti-Patterns to Avoid
- **Deriving the oracle from the applied config** (hides a plan/config mismatch; proved above to pass trivially).
- **Hardcoding the 35 agents or tiers** (use the live `node -e` tables and assert key parity).
- **Treating gsd-tools stderr as failure or success.**
- **Running anything that touches the real `~/.claude`, `~/.cursor`, `~/.config/opencode`, `~/.codex`, `~/.pi` or `~/.gsd` writably.** Reads of `~/.gsd/defaults.json` for the smoke project (b) and of the real caches are by design; the snapshot proves nothing was written.
- **Reusing GREEN results after a SKILL.md edit** (R-13).
- **Running a real apply on ai-kit, ever** (D-03): the helper should refuse `apply` when `--project-dir` resolves to the repo root.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Scratch env and real-node apply | New env builders | `_scratch_env`, `_golden_bundle`, `_real_run`, `_direct_apply` in the existing e2e tests | Already hermetic and green; a second builder drifts |
| Agent list | A literal list | `gsd_catalog.query_agent_catalog` / the same `node -e` | Spec of the project: never a hardcoded agent list |
| Config writes in the harness | Direct JSON writes | The skill's `apply` and gsd-tools `config-set`/`config-new-project` | Core value: never corrupt config; `TestWritePathDiscipline` guards `apply.py` |
| Backup/restore | Own backup logic | `config_backup` (`list_backups`, `read_marker`) | The thing under test; assert through it |
| Skill digest | Ad hoc hashing | 18.1's `DIGEST_CMD` (sha256 over `SKILL.md` plus `references/**`, first 16 hex) and `check_digests.py` pattern | Rows are only comparable if everyone hashes the same bytes |
| Child env scrub | A new scrub list | `ai_kit_spec.runner_dispatch.child_env` / `HOST_SIGNAL_ENV_VARS` | Single authoritative superset |
| Test registration | Hand-edited lists | `E2E_MODULES` + `tools/gen_test_groups.py` | `test_gate_scope.py` enforces it |
| Parallelism | A fixed worker count | The runner's 40% CPU share | AGENTS.md rule |

**Key insight:** this phase is verification of existing behavior; each new line of harness code that duplicates product logic is a place where the evaluation can pass while the product is wrong.

## Common Pitfalls

### Pitfall 1: The oracle agrees with gsd-tools but not with the plan
**What goes wrong:** the matrix passes because it reads the applied config. **Avoid:** oracle from plan entries plus live tables; add the non-vacuity pair (Control 1 must fail on every no-override agent; Control 2 must pass), as D-09 specifies. **Warning sign:** Control 1 passes.

### Pitfall 2: A scratch project resolves the wrong gsd-core
**What goes wrong:** with no `RUNTIME_DIR` and no local gsd-core, resolution falls to `~/.claude/gsd-core` (1.17.0 now). **Avoid:** `RUNTIME_DIR` or the `.claude/gsd-core` symlink; record `gsd_core.version` and path in every evidence file. Copying `.claude/gsd-core` alone crashes (needs `.claude/scripts`).

### Pitfall 3: Router never wins because it is unconfirmed
**What goes wrong:** B/C "router wins" fails in RED and GREEN alike. **Avoid:** fixtures confirm both routers (R-4); keep a negative variant to prove `router_unconfirmed` appears when not confirmed.

### Pitfall 4: `plan-set` cannot create the forced failure; `plan-set` needs `inventory.json` beside `plan.json`
**What goes wrong:** the step silently does nothing or exits 2. **Avoid:** edit a copy of the plan (edit, do not append: duplicate keys are refused); name the inventory `inventory.json` next to the plan or pass `--inventory` (observed: exit 2 "inventory ... cannot read" with a differently named file).

### Pitfall 5: Single-shot `claude -p` cannot reach later steps
**What goes wrong:** the run stops at the first question, so apply and follow-up expectations are never observed. **Avoid:** turn scripts with `--resume` (spike first); design E so its `needs_choice` is answered in turn 2.

### Pitfall 6: A headless agent with `Bash` can reach beyond the scratch project
**What goes wrong:** an agent told "just apply it" could point `--project-dir` at the repo. **Avoid:** run from the scratch cwd, give the target path in the prompt, scrub `HOME`-adjacent secrets by not passing extra env, and rely on the before/after protected-set snapshot to detect (not prevent) damage; consider `--disallowedTools "Bash(git *)"`. Record as residual risk U-1.

### Pitfall 7: Evidence staleness
**What goes wrong:** a judge or GREEN row refers to an old SKILL.md. **Avoid:** every row carries the digest; `check_digests.py` before the commit; the final GREEN and final judge rows share one digest.

### Pitfall 8: Reading stderr
gsd-tools #3532 warnings appear on stderr in the poisoned setup; parse stdout JSON only.

### Pitfall 9: Process leaks
`claude -p`, pi and node children must not outlive the run (AGENTS.md; 18.1-22 found four stray `pi -p` processes to kill). Snapshot pids before and after; kill and report leftovers.

## Code Examples

### Applying a combination on a scratch project (verified this session)
```bash
# Source: run this session; every path is a scratch placeholder
export HOME=<scratch>/home GSD_HOME=<scratch>/gh GSD_RUNTIME=claude RUNTIME_DIR=<worktree> XDG_CONFIG_HOME=<scratch>/xdg
python3 <worktree>/skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py inventory --project-dir <proj> > <work>/inventory.json
python3 <entry> recommend --inventory <work>/inventory.json --profile adaptive --rigor mvp --cross-ai-review n --cross-ai-exec n --out <work>/plan.json
python3 <entry> apply --plan <work>/plan.json --inventory <work>/inventory.json --project-dir <proj> --dry-run   # no writes (tree hash identical)
python3 <entry> apply --plan <work>/plan.json --inventory <work>/inventory.json --project-dir <proj>
node <worktree>/.claude/gsd-core/bin/gsd-tools.cjs resolve-model gsd-planner --cwd <proj>    # JSON: model, profile, effort, tier
```

### Pass criteria structure for an eval file (precedent: `skills/ai-kit-spec-review/evals/04-...md`)
```markdown
# Eval 03 - existing v1-written config
## Scenario / ## Prompt (turn 1) / ## Scripted answers (turn 2..n)
## Expected behavior   (numbered, each independently gradable)
## Pass criteria       (scripted check name per expectation)
```

### Dry-run diff row kinds (for D/E graders)
```python
# Source: skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:119-125
def _diff_kind(op: str, live: Any, planned: Any) -> str:
    if op == "unset":
        return "keep" if live is None else "remove"
    if op != "set" or plan_io.same_value(live, planned):
        return "keep"
    return "add" if live is None else "change"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Subagent RED/GREEN | Headless `claude -p`, `--tools` allowlist, `--setting-sources`, `--disable-slash-commands` | 19 D-12 | Clean baselines; needs the spike |
| v1 skill: one question + critical-agent overrides | v2: inventory -> four questions -> recommend -> plan edits -> apply -> follow-ups | Phase 18 (`7009d22`) | R1 already largely met |
| `native_runtime`, `native_claude`, `cursor-agent` split | (runtime, model) pairs, one `cursor` id, runner template 3, `ensure-runner` | Phase 18.1 | Cross-AI wording in B/E; full-permission disclosure for v2 hooks |
| `resolve_model_ids` untouched | managed key, unset on a claude host, reconciled at creation | Phases 17/18 amendments | The core APP-05 fix being proven |

**Deprecated/outdated for this phase:** the Cursor MVP and pi "ponytail missing" scenarios (19 D-01); the missing-skill offer (18 D-03); `~/.claude/gsd-core` as the reference path (R-7).

## Runtime State Inventory

Not a rename/refactor/migration phase. State the evaluation itself creates or reads (none persists beyond scratch except evidence):
| Category | Items | Action |
|----------|-------|--------|
| Stored data | Scratch `config.json`, `.bak-*` files under `tmp/` or OS temp | Delete after the run; evidence keeps hashes only |
| Live service config | None | — |
| OS-registered state | None | — |
| Secrets/env vars | Real `~/.gsd/defaults.json` read (project b); OAuth credentials used by `claude -p` | Key paths only in evidence; never print values |
| Build artifacts | None | — |
| Claude session transcripts | `claude -p` with persistence writes to the real Claude project store | Accept (normal use), or use `--no-session-persistence` for single-turn runs; multi-turn needs persistence |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| node | gsd-tools, matrix | yes | v24.21.0 | skip e2e tests (`skipUnless`) |
| checkout-local gsd-core | everything | yes | 1.16.0 | none (tests skip on non-1.16.x) |
| python3 / uv | tests, gates | yes | 3.14.7 / 0.11.28 | — |
| `claude` | pressure runs | yes | 2.1.301 (OAuth auth) | none; orchestrator-only |
| pi | cross-AI execution, judge lanes | yes | 1.3.0 | opencode/codex lanes; glm lane was capacity-limited in 18.1 |
| opencode / codex / cursor-agent | inventory enumeration only | yes | v2.0.31 / 0.162.1 / 2026.10.14-941492e | — |
| git, shellcheck | gates | yes | 2.55.0 / present | — |
| Network (catalog fetch) | `inventory` (18 s observed) | yes | — | pre-seed the cache with `seed_cache` for hermetic runs |

**Missing with no fallback:** none. **Note:** a global gsd-core 1.17.0 now exists and can shadow if resolution is not pinned (Pitfall 2).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` through `tools/run_unittest_parallel.py`; groups `unit`, `e2e` (real node), `arch` |
| Config file | `tools/run_unittest_parallel.py` (`E2E_MODULES`), `Makefile` (generated listing), `tests/test_gate_scope.py` |
| Quick run command | `python3 -m unittest tests.test_gsd_curated_eval tests.test_curated_config_apply` |
| Full suite command | `make test` then `make validate` (plus `make e2e-docker` as 18.1-22 did) |

### Phase Requirements -> Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|--------------|
| APP-05 | 5 combos x P1/P2 x 35 agents: `model` and `tier` equal the plan's promise; Control 1 fails, Control 2 passes; empty model is a failure | e2e (real node) | `python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix` | no - Wave 0 |
| APP-05 | oracle asserts MODEL_PROFILES and AGENT_TO_PHASE_TYPE have the same agent keys; agent count read live | e2e | same module | no - Wave 0 |
| EVAL-03 / R5 | apply on config copy and on empty project leaves valid config, backup equals pre-apply bytes, no marker, second apply no writes + 1 backup, forced failure restores, dry-run no writes | e2e | `python3 -m unittest tests.test_curated_config_apply_e2e` (existing 7 tests, green) plus new smoke-helper tests | partly (existing) |
| EVAL-03 / R5 | ai-kit protected set byte-identical before/after; refuses real apply on the repo root | unit + live | `python3 -m unittest tests.test_gsd_curated_eval`; `python3 tests/gsd_curated_eval.py smoke` (orchestrator) | no - Wave 0 |
| EVAL-01 / R2,R3 | per-expectation grading of B, C, D, E for RED-a, RED-b, GREEN; non-vacuity (a deliberately wrong transcript fails each scripted check) | unit (grader) + live runs | `python3 -m unittest tests.test_gsd_curated_eval`; `claude -p` runs by the orchestrator | no - Wave 0 |
| EVAL-01 / R1 | SKILL.md order and phrases (existing doc tests) after edits | unit | `python3 -m unittest tests.test_curated_config_apply -k TestSkillDocCommands` | yes |
| EVAL-02 / R4 | digest of final SKILL.md equals every non-superseded judge row; score >=96 and 0 Critical/Important, or recorded user decision after 3 iterations | script check | `check_digests.py 19-SKILL-JUDGE.md ai-kit-gsd-curated-config` (18.1 pattern; rewrite in `tmp/`) | no - Wave 0 |
| R7 | three evidence files exist with the required fields | unit/script | a small field-presence check in the helper tests | no - Wave 0 |
| R8 | each fix has a regression test; `make test` and `make validate` green | gate | `make test && make validate` | yes |

### Sampling Rate
- **Per task commit:** the quick command for the touched module plus `python3 -m unittest tests.test_gate_scope`.
- **Per wave merge:** `python3 tools/run_unittest_parallel.py --group unit` and `--group e2e`.
- **Phase gate:** `make test`, `make validate`, `make e2e-docker`, digest check, leak check, protected-set snapshot all clean, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/gsd_curated_eval.py`, `tests/test_gsd_curated_eval.py` - helper and its unit tests (snapshot, oracle, grader, plan-copy fault injector, ai-kit-root refusal).
- [ ] `tests/test_ai_kit_gsd_curated_config_matrix.py` + `E2E_MODULES` entry + `python3 tools/gen_test_groups.py`.
- [ ] `skills/ai-kit-gsd-curated-config/evals/01..04-*.md`.
- [ ] Harness spike (orchestrator): `claude -p` init event shows only the four tools, no skills/plugins/MCP; multi-turn `--resume`; transcript location; whether the user's `~/.claude/CLAUDE.md` loads (expected yes).
- [ ] `check_digests.py` equivalent and the pid-snapshot leak check.

## Security Domain

### Applicable ASVS Categories (Level 1, `security_enforcement` on)
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2/V3 Authentication, Session | no (no auth logic added) | headless runs use the user's existing OAuth; never read or print credentials |
| V4 Access Control | yes | scratch-only apply; helper refuses a real apply on the repo root; protected-set snapshot |
| V5 Input Validation | yes | helper validates paths (resolve under the run dir), scenario files are repo data, plan edits go through JSON parse not string splicing |
| V6 Cryptography | no | sha256 only for byte identity (stdlib `hashlib`) |
| V12 Files | yes | atomic writes already in the skill; helper writes only under its run dir and `tmp/`; no secrets in evidence |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Headless agent with `Bash` escapes the scratch project and edits ai-kit config | Tampering | Scratch cwd, explicit target in the prompt, before/after snapshot of the protected set, refuse-repo-root guard in the helper (detective, not preventive; U-1) |
| Credential or real-default leakage into committed evidence | Information disclosure | Record key paths not values for real `~/.gsd/defaults.json`; trimmed transcripts reviewed for secrets before `git add` (AGENTS.md: check content, not filenames) |
| `inventory` executes the target project's JavaScript | Elevation | Scratch targets only; project-local gsd-core is a symlink to this worktree (trusted) |
| Cross-AI executor runs with full permissions | Elevation | Tasks limited to repo files and `tmp/`; leak check after; no real tool configs as fixtures |
| Stale evidence presented as current | Repudiation | Digest-pinned rows and the digest check |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `--output-format stream-json` with `-p` needs `--verbose` | Facts 2 | Harness spike fails at first run; trivial fix |
| A2 | `claude -p --resume <uuid>` continues a prior `-p` session with the same tool restrictions, enabling turn scripts | Facts 2 | Multi-step expectations (E follow-ups) cannot be observed; fall back to a single long scripted prompt, weaker evidence |
| A3 | `--setting-sources project` from an empty scratch cwd drops the user's plugins, hooks and global skill listing, and `--disable-slash-commands` removes the skill listing | Facts 2 | Baseline contamination; verify in the init event during the spike |
| A4 | User memory `~/.claude/CLAUDE.md` still loads under these flags and is harmless | Facts 2 | Small bias common to RED and GREEN; documented as a confound |
| A5 | One sample per cell is enough to show discrimination; a REFACTOR cap of 3 rounds is acceptable | Facts 2 | May need more samples if results are noisy |
| A6 | `claude -p` stream-json `system/init` event reports tools, skills/slash commands, MCP servers and model id | Facts 2 | Recording of the model id would need another source (`--output-format json`) |
| A7 | pi judge lanes via the runner in review mode remain available (glm lane was capacity-limited) | Facts 4 | Judge rows record "unavailable"; pass rule needs at least one passing pi judge (18.1-22 rule) |
| A8 | The v1 SKILL.md at `7009d22^` works against the unchanged v1 subcommands | R-5 | RED-b measures a broken baseline; verify the v1 entrypoint examples once |

## Harness Spike Results (orchestrator, 2026-10-17)

Run with `claude` 2.1.301, `--model haiku --effort low`, flags `--setting-sources project --strict-mcp-config --disable-slash-commands --tools Read,Bash,Glob,Grep`, from `git init` scratch dirs; transcripts and scratch dirs deleted afterwards; protected `~/.claude` config hashes (settings, CLAUDE.md, credentials, plugin lists, skills/agents/commands listing) identical before and after. [VERIFIED: ran it]

- **A1 confirmed.** Without `--verbose`: exit 1, "When using --print, --output-format=stream-json requires --verbose".
- **A2 confirmed.** `-p --resume <session-id>` continues the session (recalled a code word from turn 1), same `session_id`, same tool list in the new init event. `--session-id <uuid>` fixes the id on turn 1. `--no-session-persistence` works for single-turn runs.
- **A3/A6 confirmed.** The `system/init` event carries `model` (resolved id, e.g. `claude-haiku-5-5`), `tools` (`[Bash, Glob, Grep, Read]` only), `skills: []`, `slash_commands: []`, `mcp_servers: []`, `plugins` (builtins only; the user's enabled plugins are dropped), `memory_paths` (only the per-project `auto` path), `claude_code_version`, `permissionMode`, `cwd`. Record these per run as the contamination check.
- **A4 changed.** Asked without tools, the model reported no `graphify`/`CodeGraph` text in context, so `~/.claude/CLAUDE.md` does not load under `--setting-sources project` [model self-report, MEDIUM]; `memory_paths` lists no user memory. Record `memory_paths` per run instead of documenting a confound.
- **New constraint: `--allowedTools` is required.** With `--tools` alone, every Bash call is denied in `-p` (`permission_denials` non-empty). Add `--allowedTools Bash,Read,Glob,Grep`.
- **New constraint: scratch dirs must not be under `~/.claude`.** A run from a dir under `~/.claude/jobs/...` had every write refused as "a sensitive file", even with `--allowedTools`. Use `mktemp -d` under the system temp dir (not the repo tree either: CLAUDE.md discovery walks parent dirs).
- **Transcript location.** `~/.claude/projects/<cwd with / and . replaced by ->/<session-id>.jsonl` plus a `memory/` dir; delete that dir per scratch project after grading. `~/.claude.json` is rewritten continuously by the host session itself, so it cannot be a hash-protected file; assert instead that it gains no `projects` key for a scratch dir.
- **Open Question 3 resolved.** With `<scratch>/.claude/gsd-core` symlinked to the worktree's gsd-core, a real `apply` of a Rigorous plan returns `followups.required[0].id == "effort_sync"` (argv `gsd-tools effort sync --apply --runtime claude --config-dir <scratch>/.claude --project-dir <scratch>`), plus `approve_with`. `apply --dry-run` output has no `followups` key, so E's grouped-approval expectation is graded after the real apply. The sync writes under `<scratch>/.claude`, not through the symlink; still hash the worktree's `.claude/gsd-core` before and after each batch.
- **Cost.** One haiku turn costs about USD 0.001 (`total_cost_usd` in the `result` event); record it per run.

## Open Questions (RESOLVED)

1. **[RESOLVED: jev 19-Q1, CONTEXT D-09 amendment - keep APP-05 as written; informational P2 row without `GSD_RUNTIME`; behavior decision to owner review]** **Does the matrix need to include the claude-host `runtime` case?** What we know: `apply` leaves a project `runtime: codex` (D-30, documented note); a real Claude Code session has no `GSD_RUNTIME`, so `resolve-model` then returns the codex model. What's unclear: whether APP-05 intends only the `GSD_RUNTIME=claude` behavior. Recommendation: keep the pass criterion as written, add an informational P2 row without `GSD_RUNTIME` so the gap is recorded, and route a decision (default `plan-set runtime claude` or a plan `unset` of a non-claude `runtime` on claude) to the user.
2. **[RESOLVED: jev 19-Q2, CONTEXT D-12 - `7009d22^`]** **Which v1 SKILL.md is RED-b?** `7009d22^` (recommended) or `2c16b26` (D-12 as written). Either is fine if the commit is recorded.
3. **[RESOLVED by spike]** **Where do follow-ups land in E?** The `effort_sync` row appears only with a project-local gsd-core and an `effort.*` change; the symlink approach should produce it, to be confirmed in the spike. If it does not, E's third expectation must be tested through the unit grader on a fixture transcript instead.
4. **[RESOLVED: jev 19-Q4, CONTEXT D-12 - cap 3, 1 sample per cell, re-sample only ambiguous cells]** **REFACTOR cap and sample size** for pressure runs are not specified; recommend 3 rounds and 1 sample per cell, escalate to the user on a persistent failure.
5. **[RESOLVED: jev 19-Q5, CONTEXT D-12 - sonnet/medium all cells plus one opus/high confirmation of v2 GREEN]** **Model and effort for `claude -p`:** discretion; recommend a fixed `--model sonnet --effort medium` recorded from the init event.
6. **[RESOLVED: jev 19-Q6, CONTEXT D-01 B - extra non-gating expectation]** **Should `ensure-runner` and the v2 full-permission disclosure be a B expectation?** Not in D-01, but it is the user's stated concern for the v2 hook; recommend adding it as an extra, non-gating expectation.

## Sources

### Primary (HIGH confidence)
- Code read this session: `skills/ai-kit-gsd-curated-config/SKILL.md`, `.../ai_kit_gsd_curated_config/{apply,config_backup,recommend,presets,cross_ai,catalog_adapter,followups,plan_edit,plan_io,gsd_catalog}.py`, `skills/ai-kit-spec-review/ai_kit_spec/{gsd_tools,runner_dispatch,detection,cache,config_io}.py`, `tests/test_curated_config_apply_e2e.py`, `tests/test_curated_config_e2e.py`, `tests/test_curated_config_apply.py` (TestSkillDocCommands), `tools/run_unittest_parallel.py`, `tests/fixtures/curated_config_v2/golden/*.json`.
- Run this session (scratch `HOME`/`GSD_HOME`, no model calls): inventory/recommend/dry-run/apply for 5 combinations; poison reproduction; forced failure; dry-run no-write tree hash; re-apply; `python3 -m unittest tests.test_curated_config_apply_e2e` (7 tests OK, 24 s).
- `.claude/gsd-core/bin/lib/{model-profiles,config,config-loader,command-roster}.cjs`, `.claude/gsd-core/VERSION`.
- Planning docs: `19-CONTEXT.md`, `19-SPEC.md`, `18.1-CONTEXT.md`, `18.1-VERIFICATION.md`, `18.1-SKILL-JUDGE.md`, `18.1-21/22-PLAN.md`, `17-CONTEXT.md` (D-01, D-04, D-05, D-08), `REQUIREMENTS.md`, `ROADMAP.md`.

### Secondary (MEDIUM confidence)
- `claude --help` (2.1.301) for flag existence and semantics; `superpowers/7.0.0/skills/writing-skills/testing-skills-with-subagents.md`.

### Tertiary (LOW confidence)
- Behavior of `claude -p` multi-turn and init-event fields (assumptions A1, A2, A3, A6) - not run.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - nothing new is installed; versions read from files and `--version`.
- Architecture: HIGH for the matrix, smoke and snapshot (exercised); MEDIUM for the pressure harness (flags verified, runs not performed).
- Pitfalls: HIGH for the ones reproduced (resolution shadowing, unconfirmed router, plan-set limits, stderr); MEDIUM for harness-escape risk.

**Research date:** 2026-10-17
**Valid until:** 2026-10-24 (fast-moving: a global gsd-core 1.17.0 appeared mid-research and the repo is mid-milestone); re-run the Reconciliation checks if Phase 20 amendments land first.
