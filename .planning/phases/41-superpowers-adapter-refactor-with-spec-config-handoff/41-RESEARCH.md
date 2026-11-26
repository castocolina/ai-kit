# Phase 41: Superpowers adapter refactor with spec-config handoff - Research

**Researched:** 2026-11-25
**Domain:** ai-kit's superpowers execute adapter (Markdown skill flow plus a stdlib Python shim), the shared `ai_kit_spec` library, the cross-AI runner template
**Confidence:** HIGH for in-repo facts (every discrete value below was read this session); MEDIUM for design recommendations (no spike, no live run)

Tags used: `[VERIFIED: path:line]` = file opened this session, anchor quoted verbatim; `[ASSUMED]` = my inference, needs confirmation.
Repo paths only; no host command, network call or spike was used. Only read-only commands ran (`rg`, `git check-ignore`, `node --version`, `python3 --version`).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
D-01 to D-09 of `41-CONTEXT.md` are locked (single definitions in `references/state-management.md` and `references/resolution-stops.md`; flags gate rounds 4 and 5 through `lane_escalation` and `escalation_target(role_lanes, key, kind)`; lane-table boolean fallback flag with one reader next to `lane_usage_limit`, jev pick through the `jev_names` pattern; two caller-fed builders in `dispatch_guidance.py`; real-home variable in every spawned lane; stdlib host-config audit over a fixed list; executor switch reuses the Phase 40 switch module and `--blocked-status`; vertical-slice build order; researcher answers the five open questions). Not restated here; not re-discussed.

### Claude's Discretion
Names (the flag, the builders, the audit module), the marker for an ai-kit checkout, the audit file list and the exact report wording.

### Deferred Ideas (OUT OF SCOPE)
A note for open-gsd about its plan template; failing a lane on a changed host config.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXE-01 | one resume path, one owner-stop path, flag-gated escalation | A1, B6, B12 |
| EXE-04 | opt-in session-model fallback | B7 |
| EXE-05 | gates and commit guard in briefs; checks around a run | A2 to A5, items a-f, B8 |
| EXE-08 | real-home guard and host-config audit | B9, B10 |
| EXE-09 | flagged executor lane switch | B11 |
</phase_requirements>

## Summary

The adapter's single-definition work (R1) is a pure documentation move, but eleven existing doc-contract tests pin duplicated sentences across SKILL.md, `escalation.md` and `state-management.md`, and SKILL.md sits exactly at its 300-line cap. R1 therefore has to amend those pins (the SPEC says existing tests pass unchanged) and has to run first so R9's pointers have room.

Requirement 5 mostly describes defects of GSD's plan template and executor, not of ai-kit code. Real examples exist in the Phase 27 summaries (a `tail -n 3 | grep` verify line broken by pyright's update banner; `git status --porcelain` clean-tree checks failing on the orchestrator's `.planning/config.json`). The runner's `uncommitted_edits` is informational and has no notion of the owner's config file; `coverage=` is `n/a` for every superpowers prompt because the prompt has no `<task>` block. No agent-branch allow-list exists in ai-kit code; its only home is GSD's `gsd-executor.md`.

Two facts contradict the SPEC's Background (see "SPEC contradictions"): the runner does build an executor prompt (`EXEC_PREAMBLE`), and D-02's `escalation_target` walks the roster in the opposite direction to the capability floor that `escalation.md` enforces.

**Primary recommendation:** Build in D-08 order, but amend the SPEC first (record the contradictions below), start with R1 consolidation plus the test-pin amendments, and route every new lane-flag read through `lane_settings.py` (the arch test `tests/test_lane_settings.py` enforces that).

## SPEC contradictions found (the planner amends the SPEC, not this file)

1. **The runner has an executor prompt builder.** SPEC Background says "`cross-ai.mjs` has no executor-prompt builder". `[VERIFIED: skills/ai-kit-spec-review/references/cross-ai.mjs:140-148]`: `const EXEC_PREAMBLE = \`` ... `<executor_rules>` ... `You run unattended. No human will answer questions or approve anything: never stop to ask, decide and continue.` ... `Never run git push and never use --no-verify.` ... `</executor_rules>`. It is prepended at `:7145` (`composePrompt(skillPlan.promptPrefix, prepended, raw, o.preamble ? (o.mode === 'exec' ? EXEC_PREAMBLE : REVIEW_PREAMBLE) : '')`) unless `--no-preamble` (`:6729`, `:56`). The Python dispatch always passes it: `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:285-286]` `"--timeout", timeout, "--outer-timeout", outer, "--no-preamble",`. So: the superpowers adapter (Python path) gets only `dispatch_guidance.py` prose; a GSD lane started through `workflow.cross_ai_command` (no `--no-preamble` in the live command, `.planning/config.json:46`) gets `EXEC_PREAMBLE`. That is very likely the "two briefs ai-kit ships" the owner meant. `EXEC_PREAMBLE` names no gates and no commit guard. Editing it is a runner template change (see "Template change procedure").
2. **The brief's template path is wrong.** `skills/ai-kit-cross-ai/references/cross-ai.mjs` does not exist. The template is `skills/ai-kit-spec-review/references/cross-ai.mjs` (`find` this session); the dogfood copy is `.planning/scripts/cross-ai.mjs`. `ai-kit-cross-ai` holds only docs (`execute-checks.md`, `SKILL.md`).
3. **R1 acceptance conflicts with existing pins.** SPEC R1: "existing 14 evals and `tests/test_ai_kit_spec_superpowers.py` pass unchanged". But `[VERIFIED: tests/test_ai_kit_spec_superpowers.py:3304-3312]` pins the same pinned-resume sentences in SKILL.md, `escalation.md` and `state-management.md` (`"`injection_json` is pinned: it re-dispatches unchanged at any `$FIX_ROUND`"` in SKILL.md; `"a restored `injection_json` always re-dispatches unchanged at any round"` in escalation.md; `"that always goes to Step 3, at any `$FIX_ROUND`"` in state-management.md), and `[VERIFIED: tests/test_ai_kit_spec_superpowers.py:3336-3343]` requires two sentences (`"is only the source of `ladder_keys`: never act on its mode or dispatch it"`, `"before any dispatch, compute the floor from the restored `$ESCALATION_ANCHOR_KEY`"`) in all three files. A consolidation that leaves one copy must edit these tests (they pin duplicates). The acceptance line should read "pass except the multi-file pins this requirement removes".
4. **SKILL.md is at its cap.** `[VERIFIED: tests/test_ai_kit_spec_superpowers.py:3642]` `self.assertLessEqual(len(text.splitlines()), 300)`; SKILL.md is 300 lines now. R9's "short pointers in SKILL.md" cannot land before R1 frees lines.
5. **D-02 direction mismatch.** `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:170-184]` `escalation_target` loops `for lane in lanes[index + 1:]:` (lanes after the stuck one in roster order). `[VERIFIED: skills/ai-kit-spec-execute-superpowers/references/escalation.md:28]` requires "only a candidate ranked **strictly above** the stuck one counts as a bump" (earlier in `ladder_keys`, most-preferred first, `:26-27`). Also `escalation_target` takes `role_lanes` in list order, while `ladder_keys` is the narrowed, ranked order. Calling `escalation_target` literally would pick a lane the floor forbids. Recommendation (not a re-discussion of D-02's gating intent): use `lane_escalation` as the gate; filter the floor-surviving candidates by kind (runtime differs, or same runtime and different model) per flag; feed `escalation_target` only after the lanes are ordered by `ladder_keys`, or do not call it. The owner/planner decides; I mark it unresolved (Open Question 1).
6. **`wizard-flow.md` calls the flags informational.** `[VERIFIED: skills/ai-kit-spec-config/references/wizard-flow.md:73]` "Say in one line that these flags are stored and informational: dispatch passes them to the runner, which reports them as ignored and never starts another lane from them." After R2 this sentence is false for the execute role; spec-config text (and its judged SKILL.md surface) must change with R2.
7. **SPEC R5 premise.** Items (a) to (e) come from GSD plan/executor defects (A5, items table); only (f) is wholly ai-kit's. See "Items (a)-(f)".

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pinned resume, owner stop docs | Skill docs (`references/*.md`) | doc-contract tests | pure documentation placement |
| Flag-gated escalation | Skill flow prose (`escalation.md`) | `lane_settings.py` reader; a CLI hook (B6) | escalation is prose today |
| Session-model fallback flag | `lane_settings.py` reader + `config_io` writer | spec-config `wizard-flow.md`; adapter prose | flags live in config.toml |
| Gate/guard guidance | `dispatch_guidance.py` (shared) | `execute_dispatch.py`, adapter `cli.py` | one shared module, caller-fed text |
| Real-home guard | spawn layer (`runner_dispatch.child_env` / seams) | `dispatch_injection.py` marker call | env is built where the child is spawned |
| Host-config audit | new small stdlib module in `ai_kit_spec` | adapter prose (report) | seed data, never a decider |
| Executor lane switch | `lane_switch.py` (shared, role parameter) | adapter `cli.py` selection | reuse of Phase 40 module |

## Standard Stack

No new dependency. Runtime code stays stdlib-only (AGENTS.md; SPEC Constraints). Python 3.15.2 and Node v24.21.0 are present on this machine `[VERIFIED: python3 --version, node --version]`.

### Package Legitimacy Audit
No external package is installed by this phase. Not applicable.

## Part A: the SPEC's open questions

### A1. Resume and stop blocks today

Files: `skills/ai-kit-spec-execute-superpowers/SKILL.md` (S), `references/*.md` (path abbreviated `refs/`). Line numbers read this session.

| File | Lines / heading | Defines | Duplicate of |
|------|-----------------|---------|--------------|
| S | 152 "A restored `injection_json` is pinned: it re-dispatches unchanged at any `$FIX_ROUND`." | resume | state-management 117-125 |
| S | 154-160 "**Resume check — before any resolution**" | resume (RESUME_FOUND, Seed, Restore, round >= 4 rule) | state-management 53-125 |
| S | 218, 235-242 "Clear the resume state when a dispatch succeeds" | resume-file lifecycle | state-management (owner of the file) |
| refs/state-management.md | 53-125 "## Initial and resume values" (Seed, Restore script, pin rules 111-125) | resume (the real mechanics) | primary |
| refs/state-management.md | 127-186 "## Resumable state: writing it", 188-218 "## Pinned-injection state write" | resume write | primary (stop text 134-141, 185-186 repeats the quota-key rule that resolution-stops 48-55 holds) |
| refs/state-management.md | 220-267 "## Owner-named replacement pair" | owner decision after a stop | primary |
| refs/escalation.md | 6-12 ("a restored `injection_json` always re-dispatches unchanged at any round") | resume | state-management 111-125 |
| refs/quota-wake.md | 12-23 (wake prompt steps 1-2: bind, Restore) | resume (prompt text) | state-management Restore (must stay literal: it is pasted into a woken session) |
| refs/quota-wake.md | 49-54 "## Resume of that wake" | resume | state-management 117-125, 220-221 (near verbatim) |
| refs/dispatch-external-cli.md | 203-205, 232-235 ("an owner re-invoke re-dispatches the pinned injection") | resume (restated) | state-management 117-125 |
| refs/config-check.md | 7-11 and block 1 (`RESUMED`, `CONFIG_CHECK=`) | resume of the config check (a different topic) | overlaps the Restore check (51 comment) |
| S | 184-187, 205-207 | stop (resolve-injection non-zero, no_candidate, quota_exhausted) | resolution-stops 8-55 |
| S | 225-228 | stop (empty/unknown anchor) | escalation 43-49 |
| S | 252-253 | stop (failed native dispatch) | none |
| S | 266-272 (dispatch outcome list) | stop (every 69, bare 75, real_error) | dispatch-external-cli 117-235 |
| refs/resolution-stops.md | 8-55 (exit codes, untrusted-config ask, no_candidate, quota_exhausted) | stop (resolve-time) | primary for resolve stops |
| refs/escalation.md | 43-49, 115-134 ("If the re-resolution reports quota_exhausted or no_candidate") | stop | resolution-stops 48-55 (re-lists the recoverable branch) |
| refs/dispatch-external-cli.md | 98-99, 117, 175-205 ("**Schedule-or-stop.**"), 206-235 ("`real_error`") | stop (dispatch-time) | none in S's list but S 266-272 summarizes it |
| refs/session-wake.md | 58-71 "## Close the session wake" | stop side effect (close wake) | S 292-296 |
| refs/config-check.md | 17-27 (answer (3), points 5 and 6) | stop (no-config) | none |

Duplicates to remove (quotes anchor them): (i) the pin rule `re-dispatches unchanged at any` appears in S:152, state-management.md:119-125 (`"a restored `injection_json` ..."`), escalation.md:11-12, quota-wake.md:51-53; (ii) the restored-round-4 rule `is only the source of `ladder_keys`: never act on its mode or dispatch it` appears in S:160, state-management.md:111-112, escalation.md:9-10 (tests pin all three); (iii) the recoverable-quota branch in state-management.md:134-141 vs resolution-stops.md:48-55 vs escalation.md:115-126; (iv) the dispatch outcome list in S:266-272 vs dispatch-external-cli.md Classify.

Proposed headings (exact text; add a `## ` line, one per path, no date, no phase id, no D-id so `tests/test_skill_text_history.py` stays quiet):
- `references/state-management.md`: `## Pinned resume` (holds: RESUME_FOUND meaning, Seed, Restore, pin-at-any-round, round >= 4 floor rule, the wake/owner re-dispatch rule, state-file lifecycle). Keep "## Resumable state: writing it", "## Pinned-injection state write" and "## Owner-named replacement pair" as writers under it.
- `references/resolution-stops.md`: `## Owner stop` (holds: every outcome that ends a run for the owner: resolve exit codes, `no_candidate`, `quota_exhausted` both branches, empty anchor, dispatch quota 69/75, `real_error`, the session-model-fallback error, the "close the wake" note).
- Links: `references/state-management.md#pinned-resume` and `references/resolution-stops.md#owner-stop` from SKILL.md Step 2/3, `quota-wake.md`, `session-wake.md`, `escalation.md`, `dispatch-external-cli.md`.

Pitfalls specific to D-01 `[VERIFIED]`:
- `resolution-stops.md` today says `MANDATORY read when resolve-injection exits non-zero ... Do NOT load it when the result is native or external_cli with a clean stderr` (`:3-5`) and S:205-207 says `Do NOT load it for any other mode`. Widening it to dispatch-time stops changes that trigger; `tests/test_ai_kit_spec_superpowers.py:3647-3650` requires every reference except `state-management.md` to carry a `Do NOT load` clause in `body + text`, and every reference to be named as `references/<name>` in SKILL.md or the dispatch reference. Keep a `Do NOT load` clause (rewrite the condition) or the progressive-disclosure test fails.
- `state-management.md` already has no `Do NOT load` (exempt at `:3648`), which suits a resume definition read on every restore.
- A doc-contract counting marker headings must scan SKILL.md and `references/*.md` (not `design-notes.md`) for exactly one line equal to each heading; its non-vacuity counterpart plants a second copy.

### A2. `uncommitted_edits`, the owner's config file, `coverage=`

`uncommitted_edits` today `[VERIFIED: cross-ai.mjs:6432-6438]`:
```
if (b.head && end.head) {
  const endDirty = await diffNames(end.head, endTree, cwd, limit);
  const baseDirty = await diffNames(b.head, baseTree, cwd, limit);
  ...
  uncommitted = endDirty.filter((p) => !baseDirty.includes(p));
```
and the finding is info only: `[VERIFIED: cross-ai.mjs:6338]` `const FINDING_RESULTS = Object.freeze({ no_commit: 'partial', task_uncovered: 'partial', admits_skipped: 'partial', forbidden_path: 'contract_violation' });` (no `uncommitted_edits` key); `[VERIFIED: skills/ai-kit-cross-ai/references/execute-checks.md:17]` `| 7. | `uncommitted_edits` | info | the end tree differs from HEAD in paths that were clean at the baseline |`. So it never fails a run and has **no** notion of an owner config file. A path already dirty at the baseline is excluded by name (even if the lane edits it further). A path clean at baseline that someone edits during the lane is named, informational. Ignored files never appear by path: `treeState` folds them as a stat signature (`cross-ai.mjs:5369-5385`) and `diffNames` uses only the `write-tree` half (`split('\t')[0]`, `:6429`).

Which file is "the owner's config file": the evidence is `.planning/config.json` for GSD runs. `[VERIFIED: .planning/milestones/v1.3-phases/27-one-shot-goal-and-loop-prompt-skill/27-09-SUMMARY.md:118]` "`test -z "$(git status --porcelain)"` includes `.planning/config.json`, which the orchestrator modifies on purpose. Checked as `git status --porcelain -- . ':!.planning/config.json'`", also 27-10-SUMMARY.md:132, 27-11-SUMMARY.md:129, 27-14-SUMMARY.md:108. For a superpowers/ai-kit execute lane the owner's config is `.aikit/config.toml`, which is git-ignored in this repo `[VERIFIED: git check-ignore -v → .gitignore:12:.aikit/ .aikit/config.toml]`; whether other projects ignore `.aikit/` is unknown. `.planning/config.json` is not ignored (check-ignore printed no rule for it).

So the "clean-tree check that ignores the config file" defect lives in plan verify lines (GSD plan template), not in the runner. The runner needs no change for (b).

`coverage=` `[VERIFIED: cross-ai.mjs:6355]` `return { coverage: input.tasks.length === 0 ? 'n/a' : `${cov.covered}/${cov.checkable}`, ...}`; tasks come from `parseTasks(prompt)` (`:6274-6292`), which reads only `<task ...>` blocks (type absent or not `checkpoint*`), each with `<name>` and `<files>`; a task is covered when a commit since the baseline touched one of its files (`coverageOf`, `:6304-6314`). `[VERIFIED: skills/ai-kit-cross-ai/references/execute-checks.md:7]`. The superpowers adapter composes a prompt with `<objective>` and `<files>` (dispatch-external-cli.md:43-49) and no `<task>` block, so every superpowers dispatch prints `coverage=n/a` and gets no `task_uncovered`/`no_commit` finding. The adapter's own progress signals are `implementer-status` (the STATUS of one dispatch: `[VERIFIED: ai_kit_spec_superpowers/cli.py:371-374]` `_cmd_implementer_status`), the resume scalars (`SEEDED_TASK`, `FIX_ROUND`) and subagent-driven-development's ledger (not ai-kit's). Nothing counts "tasks actually done". The Phase 27 mismatch was GSD's `state.update-progress` (`27-OWNER-CAPTURES.md:37` item (d)), outside this repo.

### A3. Agent-branch allow-list and dispatch paths

The only allow-list is GSD's. `[VERIFIED: .claude/agents/gsd-executor.md:515]` `if ! echo "$ACTUAL_BRANCH" | grep -Eq '^((worktree-)?agent-|worktree-wf_)[A-Za-z0-9._/-]+$'; then`. It runs only when `[ -f .git ] && [ "$SEQUENTIAL" != "true" ]` (`:511`, i.e. an agent-isolated linked worktree whose prompt has no `<sequential_execution>` block, `:507-510`). `rg` over `skills/` and `tools/` found no allow-list of agent branches, and no `agent-*` check in `cross-ai.mjs` or the superpowers adapter (rg for `allow-list|agent-\*|sequential_execution|commit guard|worktree-agent` returned nothing relevant there). Evidence of the uneven application: `27-OWNER-CAPTURES.md:38` "Executors skipped or obeyed the GSD agent-branch allow-list differently: 27-03, 27-05 did not apply it on `gsd/v1.3-curated-config-v2` (no `<sequential_execution>` block), 27-08 hit the commit gate and then received the block from the coordinator."

Dispatch paths of a superpowers task and what each applies today:

| Path | Where | Branch check | Commit guard |
|------|-------|--------------|--------------|
| Native subagent (`mode == "native"`) | SKILL.md:246-253; host `Agent` tool | none (in-process; brief carries only the unit-brief line, `:244`) | none from ai-kit; the host framework's own |
| External CLI first dispatch | `dispatch-task` → `dispatch_superpowers_task` → `execute_dispatch.dispatch_execute` → runner `--no-preamble` | none | prose of `dispatch_guidance.py` only (no guard text) ; runner `forbidden_path`/`outside_plan_files` are path checks, not branch checks |
| Fix-round re-dispatch | same call with `--report-mode append` | none | same |
| Resumed / quota-wake task | pinned injection through the same `dispatch-task` (quota-wake.md:26-28) | none | same |

Fact that blocks reading (d) literally: ai-kit unit branches (e.g. `gsd/phase-41-superpowers-...`, this checkout's branch) do not match the `agent-*` regex, and GSD's own code skips the check for sequential runs for that reason. Applying the regex on superpowers paths would refuse every commit on a unit branch. A meaningful "same way on every path" for superpowers is therefore a caller-supplied guard text through the R4 commit-guard builder, not an ai-kit-side branch regex. `[ASSUMED]` (meaning to be confirmed).

### A4. How an adapter learns the project's gate commands

What ai-kit reads today (rg over `skills/`): `skills/ai-kit-spec-goal-prompt/scripts/gp_e2e.py:28` `GATE_TARGETS = ("test", "lint", "validate", "test-unit")` with `_gate_signals` (`:144`) scanning Makefile targets (and package scripts), and `skills/_shared/ai_kit_rules_common/makefile_parse.py` (`parse_makefile_targets`, `parse_makefile_recipe`). `arch-test` is not in `GATE_TARGETS`. The superpowers adapter reads none of this. No code in the adapter reads AGENTS.md; the plan's task text can carry `Run:` lines (superpowers plans), which the controller already holds as the brief.

Recommendation, consistent with D-04 (builders take caller text, hold no wording): the controller (SKILL.md Step 3 compose) writes the gate commands as plain text into a file passed to `dispatch-task` (new `--gates-file`, mirroring `--format-block-file`), taking them from the project's own instruction file (AGENTS.md "unit and arch groups" lines) or the plan's verify lines; with no source it writes nothing and the builder returns nothing. Do not add Makefile discovery to the adapter in this phase: it would duplicate `gp_e2e.py` across skills (each skill must stay standalone). `[ASSUMED]` that a caller-written file is acceptable to the owner (the SPEC allows "a project's gate commands"); the narrowest option.

### A5. What a version banner breaks: a real example

Found. `[VERIFIED: .planning/milestones/v1.3-phases/27-one-shot-goal-and-loop-prompt-skill/27-05-SUMMARY.md:111]`: "**5. Verify command for pyright.** The plan's `uv run pyright ... | tail -n 3 | grep -q '0 errors'` exits 1 as written, because pyright prints a version-update banner after its summary line. Run without the `tail`, pyright reports `0 errors, 0 warnings, 0 informations`. The code is clean; the command is not." Same defect in 27-04-SUMMARY.md:108, 27-06-SUMMARY.md:130, 27-07-SUMMARY.md:121, 27-08-SUMMARY.md:107, 27-09-SUMMARY.md:116, and owner capture `27-OWNER-CAPTURES.md:37` (a) "failed as written in 27-04, 27-05, 27-06, 27-07, 27-08 and 27-09". So a banner breaks a verify line that judges a tool by its last N output lines (`tail -n 3 | grep`), not the tool's exit code. The plan template is GSD's (out of scope to edit); ai-kit can only give caller text: a gates/guard builder line telling the implementer to judge a gate by its exit code, never by `tail` of its output. `[ASSUMED]` that this is the intended meaning of "tolerate banners".

### Items (a) to (f) of SPEC requirement 5

| Item | Current behavior (verified) | Proposed testable meaning | Fake-lane test target | Runner template change? |
|------|------------------------------|---------------------------|-----------------------|-------------------------|
| (a) verify lines pass on a banner | Defect is in GSD plan verify lines (A5); ai-kit composes none for superpowers. `dispatch_guidance.py` has no verify text. | The gates builder (R4) carries one caller-supplied rule: judge a gate command by its exit code; never by `tail`/`grep` of its output. Test: builder frames caller text verbatim; a fixture gate text containing `tail -n 3 | grep` is not rewritten (no interpretation). | `ai_kit_spec.dispatch_guidance` (new builder) and `execute_dispatch.build_execute_guidance` | No |
| (b) clean-tree check ignores the owner's config file | Runner: `uncommitted_edits` info only, path-level, no config notion (A2). Plan verify lines were the defect. | Two parts, `[ASSUMED]`: (1) the guard builder's caller text names the exclusion pathspec (`-- . ':!<config path>'`) for clean-tree checks, config path chosen by the caller (`.planning/config.json` for GSD, none for ai-kit's git-ignored `.aikit/config.toml`); (2) no runner change, since the finding is info and never blocking. | `dispatch_guidance` guard builder; no runner test | No |
| (c) progress counter equals tasks done | `coverage=n/a` for superpowers (no `<task>` block); GSD mismatch is `state.update-progress` (outside repo) (A2) | Choose between (i) leave `n/a` and document it, or (ii) wrap the dispatched task in one `<task><name>...</name><files>...</files></task>` block in `dispatch-external-cli.md` Compose so the runner reports `coverage=1/1` or `0/1` and `no_commit`/`task_uncovered`. Caution on (ii): `partial` writes no answer to stdout (SKILL.md of ai-kit-cross-ai line 263) and the adapter classifies `partial` as `real_error` (`dispatch_injection.py:425,458-459`), so a task with no commit would become a stop instead of a review. Owner decision needed (Open Question 3). Default recommendation: (i). | `ai_kit_spec_superpowers.dispatch_injection.dispatch_classification` for (ii) | No |
| (d) agent-branch allow-list on every path | Exists only in `gsd-executor.md:515`; no ai-kit code; superpowers paths apply nothing (A3) | The commit-guard builder (R4) is included in every superpowers dispatch path that composes guidance (external first dispatch, fix round, resumed) when the caller supplies guard text; the native path gets the same text through the adapter's brief (prose, no code path exists to test except the CLI hook in B8). No ai-kit regex. | `dispatch_injection.dispatch_superpowers_task` with a fake `dispatch_execute_fn` asserting the text in the composed prompt for all three external paths | No |
| (e) commit guard uniform across paths | none in ai-kit; GSD guard in `gsd-executor.md:486-521` | Same as (d): one builder, one composition point (`build_dispatch_reinforcement_guidance`), asserted for first dispatch, fix round, and resumed re-dispatch (they all go through `dispatch-task`). | same | No |
| (f) gates named in the guidance | not present (`dispatch_guidance.py` four builders only) | R4 gates builder returns the supplied text framed once, nothing when none. | `dispatch_guidance` unit tests; `dispatch_superpowers_task` fixture | No |

If the owner instead wants the guard text in GSD lanes, that needs an `EXEC_PREAMBLE` edit (template change, SPEC contradiction 1) and is a different scope.

### Template change procedure (only if a runner edit is ever chosen)

`make check-dogfood` requires `.planning/scripts/cross-ai.mjs` to be a pristine render `[VERIFIED: tools/check_dogfood.py:112-113]` `if state != "pristine": problems.append(f"{RUNNER_REL} is {state}, not pristine")`. The template's line 2 is `// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=13 sha256=UNSTAMPED` (`cross-ai.mjs:2`); the dogfood copy carries `template=13 sha256=dbd96b00...` (`.planning/scripts/cross-ai.mjs:2`). `[VERIFIED: skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:60]` `TEMPLATE_VERSION = 13`; `tests/fixtures/runner_describe_golden.json` also holds `template_version`, and `tests/test_curated_config_script.py:344-358` (`test_template_version_bump`) shows a bumped template yields plan kind `change`. Re-render: `python3 skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py ensure-runner --cwd <repo root>` (subcommand documented at SKILL.md:360 of that skill; prints `{ready, runner, notes}`). Whether a template edit requires a `TEMPLATE_VERSION` bump is `[ASSUMED]` yes (the in-place upgrade path keys on it). This phase's recommended scope needs none of this.

## Part B: facts the planner needs

### B6. Escalation today

Rounds 4 and 5 are **prose only**: no CLI subcommand reads flags. The adapter's subcommands (`[VERIFIED: ai_kit_spec_superpowers/cli.py:479-486]`) are `resolve-injection`, `dispatch-task`, `classify-dispatch-failure`, `implementer-status`, `resume-exclusions`, `write-resumable-state`. The escalation rule is `references/escalation.md` (floor script at `:53-65`, re-resolve at `:83-99`) driven by SKILL.md:220-233. `lane_escalation` has no reader in the adapter: `[VERIFIED: tests/test_lane_settings.py:239]` `ALLOWED_READERS = {"runner_dispatch.py": frozenset({"lane_escalation"}), ...` and `escalation_target` is in no module's allowed set (only `tests/test_spec_config_lane_json.py:90` calls it). `runner_dispatch.spec_with_effort` reads `lane_escalation(knobs)` (`:104`) to pass `--escalate-runtime/--escalate-model` to the runner, but the superpowers dispatch candidate drops the flags: `[VERIFIED: dispatch_injection.py:384-385]` `candidate = {"runtime": injection["runtime"], "model": injection["model"], "effort": injection.get("effort"), "service_tier": injection.get("service_tier")}` and `assemble_candidates` (`:181-188`) copies no flag or `pool`. The injection JSON (`_injection_for`, `:295-308`) also carries none.

Smallest testable hook: a new adapter subcommand (for example `escalation-gate`) that takes the stuck key plus `--injection-json` / ladder, reads the execute lanes through `assemble_candidates`' source (`cfg_resolve`), calls `lane_settings.lane_escalation` on the anchor lane and prints `{runtime: bool, model: bool, keys_allowed: [...]}` (allowed floor candidates by kind). `escalation.md`'s resolve block calls it before the floor computation and adds the allowed set to `--escalation-excluded-keys-json` (that channel is exactly for floor exclusions). Flag reading must live behind `lane_settings` helpers: `tests/test_lane_settings.py:473-486` fails any module outside `ALLOWED_READERS` that names a reader or holds a flag literal (`escalate_runtime`, `escalate_model`, `usage_limited`), so the planner adds the new module to `ALLOWED_READERS` (and a non-vacuity row at `:488-516`). Both flags false must report the stuck task and keep the lane; today's STOP text for "no more capable candidate" (escalation.md:125-134) is the nearest existing report.

### B7. Session-model fallback (R3)

How session-model mode dispatches natively: `[VERIFIED: references/config-check.md:98-103]` block 3 writes `{"mode": "native", "key": "", "runtime": "", "model": "", "ladder_keys": []}` to `$RUN_DIR/INJECTION_JSON.json` and `INJECTION_MODE=native`; SKILL.md Step 3 `mode == "native"` then omits `model` (`SKILL.md:246-251`). Today it is entered only through `CONFIG_CHECK` `once` or `notice` (`SKILL.md:152`). Only Claude Code selects a model per call `[VERIFIED: skills/ai-kit-spec-config/references/session-default.md:8]` "Today only Claude Code selects a model per call (its sonnet, opus, haiku and fable aliases); every other host runs only its session default natively." So a jev haiku/sonnet pick can only take effect on a Claude Code host; elsewhere the fallback runs the session default and skips the pick (state this in the doc and test it).

Reading a boolean: `[VERIFIED: lane_settings.py:96-100]` `_bool_setting(entry, name)` returns `entry.get(name, False)`, raising `LaneSettingError(f"{entry.get('key', '<unknown>')}: '{name}' must be a boolean")`; `lane_usage_limit` (`:103-107`) is the model. `LANE_FLAG_KEYS = ("escalate_runtime", "escalate_model", "usage_limited")` (`:11`) are per-lane-entry flags (checked by `_problems`, dropped when false by `normalise_lane_settings`).

Where a role-level boolean lives: `[lanes]` holds `strategy`, `policy` and role arrays (`config_io.py:425-438`); `[lanes.policy.review|execute]` hold a `ladder`. `[VERIFIED: config_io.py:1037]` `return {k: v for k, v in raw.items() if k != "ladder"}, raw["ladder"]` and `:1060-1061` `if ladder: written[role] = {**extra, "ladder": ladder}`: extra keys of a role table survive a write only when its ladder is non-empty, and `[VERIFIED: config_io.py:1034-1036]` a role table with no `ladder` list is rejected (`needs a table with a 'ladder' list; not written`). The reader side tolerates extra keys: `role_orders._table_ladder` (`:31-41`) reads only `ladder`. Flat `[lanes.policy]` keys also survive (`written = {k: v for k, v in policy.items() if k != "ladder" and k not in role_orders.ROLES}`, `:1052`) and `cfg_resolve` merges them (`:701-706`). Recommendation: `[lanes.policy.execute] session_fallback = true` (name is Claude's discretion), written only when true, because a role with an execute lane always has a ladder (spec-config SKILL.md:358 "a role's `review` or `execute` table only when that role has a lane"); the reader goes next to `lane_usage_limit` in `lane_settings.py` and can reuse `_bool_setting({"key": "policy.execute", **table}, name)` so the error names the key. Keep the literal inside `lane_settings.py`; if it is added to `LANE_FLAG_KEYS`, `_problems`/`normalise_lane_settings` would treat it as a lane-entry key, so use a separate constant instead (and keep `test_writer_and_defaults_set_no_flag`, `tests/test_lane_settings.py:518-524`, green: off by default means nothing is written).

Spec-config location: the question flow lives in `references/wizard-flow.md`, not in SKILL.md. Headings `[VERIFIED: wizard-flow.md:67,71,75]`: `## 9. Order per role`, `## 10. Escalation`, `## 11. Mode, strategy and timeouts`. The execute-role flags step is `## 10. Escalation`; add the fallback question there (or as `## 10`'s second paragraph, or a new numbered section before `## 11`), and extend Step 3's JSON shape sentence in `skills/ai-kit-spec-config/SKILL.md:358` (`"execute": {"ladder": ["<key>"]}`) plus `references/config-file.md` "Lane entry fields". Any renumbering must keep the doc tests (`tests/test_cross_ai_docs_text.py`) green; I did not run them.

Where the adapter applies it: the fallback trigger is `resolve-injection` returning `mode` `no_candidate` or `quota_exhausted` (SKILL.md:205-207 STOP today; `cli.py:194-197`, `:233-235`), plus exit 2 conditions that are not config errors. With the flag on, run config-check block 3's native injection instead of STOP; with it off the error must name `ai-kit-spec-config`. Edge: `quota_exhausted` with `any_quota_recoverable == True` currently writes resumable state and stops (resolution-stops.md:48-55); fallback must decide whether to pre-empt it (flag on: yes, per SPEC "all unavailable, blocked or out of quota").

jev pick: `[VERIFIED: jev_names.py:140]` `def ask_items(entry: str, items: list, env, run=subprocess.run, strict=False) -> dict:` returns `{item_id: (choice, top, reason)}`; items are dicts like `class_item` (`:96-103`): `{"id": f"k{index}", "type": "choice", "instructions": CLASS_QUESTION, "context": ..., "criteria": {name: name for name in CLASSES}}`; `jev_names.class_judge`/`find_jev` give the entry. "Confident": `[VERIFIED: jev_review.py:194-196]` `def _confident(answer): choice, top, reason = answer; return reason == "" and choice is not None and top is not None and top >= STABLE_TOP` with `[VERIFIED: lane_order.py:14]` `STABLE_TOP = 0.80`; `_column_answer` already returns `reason "low"` when `needs_fallback`/`forced`/`fallback` is set (`jev_names.py:130-131`), covering the SPEC's `needs_fallback` edge. `_confident` is private in `jev_review.py`; the adapter needs its own copy of the same predicate or a public helper (arch note: jev lookups are `LOOKUP_COPIES`-checked, below). Summaries only: the item `context` must be a short summary of the task class, never the brief, code or diff (SPEC prohibition).

Model-name guard for "haiku"/"sonnet": `[VERIFIED: tests/test_arch_hardcoded_models.py:48-64]` the rules are position-based (`KEYVAL` `model = "x"`, `FLAGVAL` `--model x`, `SLASH`, `NAME_ASSIGN` for constants named `*MODEL*|*ALIAS*|*SELECTOR*`, `native_selectors=(`); a bare word with none of `-./0-9:` is not "modelish" (`_modelish`, `:84-85`) except under strict keyval/flag rules. Existing legitimate seed: `[VERIFIED: detection.py:129]` `native_selectors=("fable", "opus", "sonnet", "haiku"),` (baselined). So a constant such as `JEV_PICKS = ("haiku", "sonnet")` should pass, `model="haiku"` or `{"model": "haiku"}` would hit. I did not run the test; confirm by running `tests/test_arch_hardcoded_models.py` after writing the module. Prefer deriving the allowed picks as the intersection of `detection.RUNTIMES["claude"].native_selectors` with the two names, so the seed stays single-sourced.

LOOKUP_COPIES: `[VERIFIED: tests/test_arch.py:1688-1698]` lists files that carry a jev skills-root lookup (`JEV_ENTRY_REL`, `SKILLS_ROOTS`); a new module that re-assigns either must join it (`test_every_lookup_copy_is_compared`, `:2481`). Import `ai_kit_spec.jev_names.find_jev`/`ask_items` instead of copying.

### B8. Dispatch guidance (R4)

`dispatch_guidance.py` (83 lines) read in full this session: four builders (`build_model_selection_override_guidance(resolved_label)`, `build_incremental_progress_guidance()`, `build_output_format_guidance(format_block)`, `build_failure_reporting_guidance()`) and the composer `[VERIFIED: dispatch_guidance.py:68-82]` `def build_dispatch_reinforcement_guidance(resolved_label: str, format_block: str | None) -> str:` returning `"\n\n".join(sections)` with order override, progress, failure reporting, then the format block last. The module docstring (`:1-17`) states it never edits a framework's prose and "Framework-specific knowledge ... is never hardcoded here -- callers supply it". D-04 asks gates and guard after failure reporting and before the format block.

Callers: only `execute_dispatch.py` `[VERIFIED: execute_dispatch.py:33,63,88-90]` (`ExecuteSeams.build_reinforcement_fn` defaulting to the composer; `build_execute_guidance` calls `seams.build_reinforcement_fn(f"{candidate['runtime']}, model {candidate['model']}", spec.format_block)`). The superpowers CLI reaches it through `cli.py:325-334` `_dispatch_guidance_for_cli` → `SuperpowersDispatchGuidance(format_block, tool_availability, agents_tooling_path, code_index_registered)` (`dispatch_injection.py:66-70`) → `ExecuteDispatchSpec` (`:386-396`). Tests call the composer positionally: `tests/test_ai_kit_spec.py:5237,5246` (`build_dispatch_reinforcement_guidance("claude, tier opus", None)`), so new parameters need defaults to keep these byte-identical.

Existing argparse of `dispatch-task` (`cli.py:431-451`): `--injection-json`, `--prompt-file`, `--target-dir`, `--heartbeat-interval`, `--timeout`, `--format-block-file`, `--report-file`, `--report-mode`. There is no caller-text argument for gates or a guard; the pattern to copy is `--format-block-file` (file, never argv text). Carrying path: new optional `--gates-file` and `--guard-file` → `SuperpowersDispatchGuidance` new fields → `ExecuteDispatchSpec` new fields → `build_execute_guidance` → composer. Note `ExecuteDispatchSpec.files` defaults to `()` (`execute_dispatch.py:76`) so the superpowers path uses `compose_for_lane` (not the soft-confinement branch).

Native path: no code composes guidance for a native subagent (SKILL.md:246-253); to include gates/guard there the adapter needs prose, or a small subcommand that prints the composed block. Without it, "every superpowers implementer dispatch includes them" is only true for `external_cli`. Flag for the planner (Open Question 4).

### B9. Real-home guard (R6)

Honored only by `tools/setup.py`: `[VERIFIED: tools/setup.py:5186-5198]` `def _refuses_real_home(env):` ... `if env.get("AI_KIT_REFUSE_REAL_HOME") != "1": return False` ... `return os.path.realpath(home) == os.path.realpath(real)`; invoked at `:5311-5314` (`if not dry and _refuses_real_home(env): print("error: AI_KIT_REFUSE_REAL_HOME is set and HOME is the real user home; refusing to write ...`). So the variable in a lane protects only a `setup.py` run, not arbitrary writes to `~/.claude`; the report should say so. `skills/ai-kit-cross-ai/SKILL.md:378` already documents this ("In an ai-kit checkout, `AI_KIT_REFUSE_REAL_HOME=1` makes `tools/setup.py` refuse a run whose HOME is the real home.").

Where the lane env is built (Python path): `[VERIFIED: runner_dispatch.py:163-173]` `child_env(extra, env)` copies `env` or `os.environ`, drops `HOST_SIGNAL_ENV_VARS`, then applies `extra`; the spawn passes `env=child_env(env=work.seams.env_fn())` (`:554`); `RunnerSeams.env_fn` (`:306`) is the one seam. `dispatch_execute` takes no env; `ExecuteSeams.runner_seams` carries it (`execute_dispatch.py:57-65`, `run_runner(..., active.runner_seams)` at `:153-154`), and `dispatch_superpowers_task` passes no seams (`dispatch_injection.py:386`). Smallest change: an `ExecuteDispatchSpec` field (for example `extra_env: dict | None`) merged by `dispatch_execute` into `active.runner_seams._replace(env_fn=...)`; or `child_env(extra=...)` via a new `RunnerSpec`-independent argument. `detection.run_in_own_group` / `bounded_run` accept `**kwargs` to `Popen` (`detection.py:955-982`) so `env=` flows, but the execute spawn does not use them (`_popen_supervised` uses `work.seams.popen_fn`).

Runner to child: `[VERIFIED: cross-ai.mjs:5410-5416]` `function childEnv(extra, baseEnv) { const env = { ...baseEnv, ...extra }; for (const k of CONFIG.scrubEnv) ...` and `:5751` `const env = childEnv(rt.env, process.env);`; the shipped `scrubEnv` holds only host signals (`AI_AGENT`, `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SSE_PORT`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`, `CODEX_VERSION`, `CURSOR_AGENT`, `OPENCODE`, `PI_CODING_AGENT`, `:122-133`). So `AI_KIT_REFUSE_REAL_HOME` passes through the runner to the lane unchanged. GSD-launched lanes: GSD runs `workflow.cross_ai_command` directly; the variable reaches the lane if it is in that process's environment. Fact: this checkout's live config already prefixes it: `[VERIFIED: .planning/config.json:46]` `"cross_ai_command": "env AI_KIT_REFUSE_REAL_HOME=1 node .planning/scripts/cross-ai.mjs --runtime pi --model router-env/my-coding --mode exec"`, while the curated-config default is `CROSS_AI_COMMAND = "node .planning/scripts/cross-ai.mjs"` (`cross_ai.py:12`) and its guard compares against that exact string (`plan_io.py:882-892`), so a prefixed command is a hand edit that `plan_edit` treats as non-default. A GSD-side fix needs a curated-config change (command or env), not a runner template change; R6's SPEC text covers "the runner's execute role", which is only reachable that way. `[ASSUMED]` the owner wants the curated-config command left alone in this phase.

Checkout marker proposal (fixed at plan time, held-out fixtures): a pair only this repo holds, both files checked relative to a candidate root: `skills/ai-kit-spec-review/ai_kit_spec/detection.py` and `tools/setup.py` (both read this session, both exist; `rg` for an existing "ai-kit checkout" detector found none in `skills/` or `tools/`). Resolution: from `cwd`, walk parents (stdlib, no subprocess) until both marker files exist; a linked worktree has its own checkout of those files, so the walk finds it; a subdirectory resolves by walking up. Do not use `git rev-parse --show-toplevel` (needs the git binary, and `GIT_DIR` environment overrides can mislead; the runner itself walks parents for `.git`, `cross-ai.mjs:5307-5318`). The existing runner uses the same walk idea in `inGitTree`.

### B10. Host-config audit (R7)

Files that exist as concepts in the code (read this session):
- `.claude/settings.json` (`config_doctor_checks.py:115` via `resolve_runtime_config_paths`; `setup.py:137`), `.claude.json` (`detection.py:1410`, `os.path.join(env.get("CLAUDE_CONFIG_DIR") or home, ".claude.json")`)
- `.config/opencode/opencode.json` and `opencode.jsonc` (`jsonc_read.py:169-172`; `config_doctor_checks.py:116`)
- `.codex/config.toml` (`config_doctor_checks.py:117`; `detection.py:1421`)
- `.cursor/cli-config.json` (`config_doctor_checks.py:118`), `.cursor/mcp.json` (`detection.py:1415`), `.cursor/hooks.json` (`setup.py:145`)
- `.gsd/defaults.json` (`ai_kit_gsd_curated_config/inventory.py:116`)
- `.copilot/mcp-config.json` (`detection.py:1418`)
- pi: only `.pi/agent/extensions/cbmem.ts` appears (`detection.py:1424`); no pi settings file is named anywhere I read. Unknown whether pi has a settings file the owner cares about; not listed as a concept.

Proposed fixed list (HOME-relative, files only, audit order): `.claude/settings.json`, `.claude.json`, `.config/opencode/opencode.json`, `.config/opencode/opencode.jsonc`, `.codex/config.toml`, `.cursor/cli-config.json`, `.cursor/mcp.json`, `.cursor/hooks.json`, `.copilot/mcp-config.json`, `.gsd/defaults.json`. The owner's 2026-11-23 observation named "two real config files" without names; which two is unknown.

Existing path tables (seed data, never a decider): `tools/config_doctor_checks.py:84-119` `resolve_runtime_config_paths(env)` (four runtimes, env-aware, but under `tools/`, which skills must not import) and `ai_kit_spec/detection.py:1402-1427` `_cbm_config_paths(runtime, env)` (private; six runtimes; absolute-path filter) plus `ai_kit_spec/jsonc_read.py:157-173` `opencode_user_config_paths`. Recommendation: a new small `ai_kit_spec` module with the HOME-relative tuple above and a function that snapshots `os.stat(...).st_mtime_ns` for each existing file (`None` for missing), resolved against `env["HOME"]` so tests use a scratch HOME. Env overrides (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `XDG_CONFIG_HOME`, `OPENCODE_CONFIG_DIR`) make a pure HOME-relative list incomplete; either honor them as the existing resolvers do or state the limit in the report (observation label). `[ASSUMED]` HOME-only is acceptable for v1 (D-06 says "resolved against the process's HOME").

### B11. Executor switch (R8)

Functions in `lane_switch.py` read this session (`skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py`):
- `review_lane(config, key)` `:30-33`: `config.get("review", [])` hardcoded.
- `next_lane(config, base_key, exclude, route_fn)` `:46-61`: `lane_settings.selectable_lanes("review", config.get("review"), role_orders.role_order(config, "review"))` hardcoded.
- `flagged_replacement(config, key, reason, exclude, route_fn)` `:182-193`: through `review_lane` (hardcoded) then `lane_usage_limit(lane).limited` and `next_lane`.
- `replacement_row` `:211-217`: through `review_lane`.
- `review_routes(config, deps)` `:224-227`: `config.get("review", [])` and `routing.host_context("review", ...)`.
- `pool_status(lane, now_s, reader)` `:112-124`, `pool_keys`, `pool_decisions` `:134-151`, `blocked_reader(deps)` `:154-159`, `blocked_until` `:77-98`, `blocked_cache_entries` `:162-179`: **role-free** (take lanes/lists). `lane_settings.lane_free_pool` `:116-126`: role-free.
- `cmd_switch_lane` `:242-286` is review-only by construction (reviewers JSON, review lane log).

Smallest change: add `role: str = "review"` to `review_lane`, `next_lane`, `flagged_replacement`, `replacement_row` (and a mode `"exec"` for the host context in `review_routes` or a new execute twin); every review caller passes nothing and stays byte-identical. Execute order for selection is `selectable_lanes("execute", lanes, order)`, which appends unordered execute lanes (`lane_settings.py:152-160`). One existing guard: `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/cli.py:952-955]` `if args.role == "review": existing = lane_switch.blocked_cache_entries(...)`: `probe-quota --role execute` skips the blocked-pool step on purpose today; the adapter's own quota refresh is `ai_kit_spec_superpowers/cli.py:174-187` `_refresh_quota_for_candidates`, the natural place to call `blocked_cache_entries(lanes, ladder_keys, existing_quota, time.time(), blocked_reader(deps))` before `build_dispatch_injection` (`CliDeps` already has `which_fn`, `run_fn`, `env_fn`, `cli.py:89-93`, which `blocked_reader` needs).

How the adapter learns a dispatch stopped on quota today: `dispatch_classification` `[VERIFIED: dispatch_injection.py:462-466]` `elif returncode == 75 and retry is not None and cycle is not None: cls = "quota_cycle"` / `elif ((returncode in (69, 75) and status.get("status") in ("transient", "quota") and not malformed) or dispatch_result.get("reason") == "quota"): cls = "quota"`; CLI `classify-dispatch-failure` (`cli.py:365-368`); SKILL.md and `dispatch-external-cli.md` Classify/Schedule-or-stop (`:136-205`); `references/quota-wake.md` prompt. Today every `quota` is an owner stop and `quota_cycle` gets one wait (SKILL.md:268-272). R8 changes the `quota` branch for a flagged lane. Note NEVER at SKILL.md:31-33 ("Never switch harness, provider or model after a failed or unusable run ... Do not re-run `resolve-injection` to recover"): the flagged-lane switch is the owner-authorized exception (SPEC Background: "a lane flagged `usage_limited` switches at once to the first unflagged lane of a different pool"); the NEVER text and `TestPinnedResumeAndReturnCode69OneRule` need a scoped carve-out.

`--pool` on the review side: `[VERIFIED: reviewer_dispatch.py:117-119]` `runner_spec = (review_spec(...)._replace(pool=lane_settings.lane_free_pool(entry.get("extra") or {})) if runtime else None)` and `runner_dispatch.runner_flags` emits `["--pool", spec.pool]` (`:245-246`), `RunnerSpec.pool` at `:91`. Execute equivalent: `execute_dispatch._runner_spec` (`:106-109`) returns `spec_with_effort(...)` with no pool; add `._replace(pool=lane_settings.lane_free_pool(candidate))` there. That requires the dispatch candidate (built in `dispatch_superpowers_task`, `dispatch_injection.py:384-385`) to carry the lane's `usage_limited` and `pool`, which it does not today (B6). `lane_free_pool` in `execute_dispatch.py` also needs `ALLOWED_READERS["execute_dispatch.py"]` (`tests/test_lane_settings.py:239-243` allows it only in `reviewer_dispatch.py`, `quota.py`, `lane_switch.py`).

### B12. Guards that bind new code

| Guard | Rule (quoted) | Effect on this phase |
|-------|---------------|----------------------|
| `tests/test_lane_settings.py:473-486` | `test_only_lane_settings_holds_a_flag_literal`, `test_no_module_calls_a_lane_reader`; scans `skills/ai-kit-spec-review/ai_kit_spec` and `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers` (`SCANNED`, `:233-234`) | Any flag literal (`escalate_runtime`, `escalate_model`, `usage_limited`) outside `lane_settings.py`, and any reader name outside `ALLOWED_READERS` (`:239-243`), fails. Add each new calling module with exactly the readers it calls; add `session_fallback`-style reader inside `lane_settings.py`. |
| `tests/test_arch.py:1688-1698`, `:2481` | `LOOKUP_COPIES` (jev lookup copies) and `test_every_lookup_copy_is_compared` | Do not assign `JEV_ENTRY_REL`/`SKILLS_ROOTS` in new code; import `jev_names`. |
| `tests/test_arch.py:2225,2405` | `test_rule1_host_prefix_literals_stay_in_host`; `test_no_test_calls_a_host_cli` (no test spawns a host CLI by name; `tests/host_fakes.py` exempt) | Fake-lane tests must use `host_fakes`, never name a host binary as a spawned program. |
| `tests/test_arch_hardcoded_models.py` | position-based model-name rule, baseline only shrinks (`:1-2`, `:48-64`) | See B7. Fixtures use `placeholder-model-N`, `fake/...` (`ALLOWED`, `:48-50`). |
| `tests/test_skill_text_history.py` | `DATE_RE`, `AS_OF_RE`, `PHASE_DIR_RE`, `PHASE_FILE_RE`, `BACKLOG_RE` (`999.N`), `DECISION_RE` (`D-N`), `REFEREE_RE`, tool-version regex, read from each SKILL.md main flow (above a trailing `## Evidence`) | No dates, phase ids, D-ids, `referee-` names, or tool versions in SKILL.md; provenance goes under a trailing `## Evidence`. The scan covers SKILL.md (`history_hits`, `:105`); references have a separate pointer rule (`test_pointer_in_a_reference_file_fails`, `:484`): no phase folders, backlog ids, referee names in references either. |
| `tests/test_skill_evals_shape.py` | `len(evals) < 5` fails; unique ids; casual/precise/edge id prefixes (`:33-40`, `:183`); files under `evals/files/`; no machine path | New evals use ids `casual-`, `precise-`, `edge-` and no absolute path. |
| `tests/test_ai_kit_spec_superpowers.py` | 26 doc-text pins to the files this phase edits; SKILL.md `<= 300` lines (`:3642`); every reference needs `MANDATORY` and a `Do NOT load` (`:3647-3650`) | R1/R9 must amend the pins and respect the cap; see contradictions 3 and 4. |
| `tests/test_cross_ai_docs_text.py`, `tests/test_role_orders.py` | doc-text and role-order tests (files exist; not read in depth) | Re-run after the spec-config and role-table edits. |

Adapter evals now: **14** `[VERIFIED: evals/evals.json]` (ids: `casual-run-superpowers-plan`, `precise-external-cli-pair`, `precise-fold-after-review`, `precise-start-before-first-task`, `edge-plan-without-fold-step`, `edge-fold-refused`, `edge-executing-plans-out-of-scope`, `precise-no-config-chains-spec-config`, `precise-config-active-never-asks`, `edge-spec-config-missing-stops`, `edge-no-way-to-ask-notice`, `edge-no-config-stop-answer`, `precise-no-config-once-native`, `edge-review-only-roster-still-asks`). The SPEC needs four more (fallback, flag-gated escalation, flagged-lane switch, host-config audit): 18.

## Architecture Patterns

### System flow (execute lane)

```
plan task -> [Step 1 config-check: none? ask / spec-config] -> Step 2 resolve-injection
   |-- native/external_cli injection ----------------------------+
   |-- no_candidate / quota_exhausted --> flag on? --> session-model native injection
   |                                      flag off --> Owner stop (names ai-kit-spec-config)
   v
Step 3 compose guidance (override, progress, failure, [gates], [guard], format) 
   -> external_cli: dispatch-task -> dispatch_execute (env + AI_KIT_REFUSE_REAL_HOME in checkout) 
        before: audit snapshot -> runner -> after: audit snapshot -> report
   -> classify: ok | quota_cycle | quota (flagged lane? switch to fallback of other pool) | real_error
   -> fix round 4/5: lane_escalation gate -> floor candidates filtered by kind -> re-resolve
```

### Recommended edits by file
- `lane_settings.py`: role-level fallback reader (next to `lane_usage_limit`).
- `dispatch_guidance.py`: two builders; composer gains two optional params (defaults keep today's output).
- `dispatch_injection.py`: candidate and injection carry the lane flags and pool; marker call for the guard env.
- `execute_dispatch.py`: pool and env wiring; new spec fields.
- `lane_switch.py`: `role` parameter default `"review"`.
- new `ai_kit_spec` module: host-config audit; new adapter subcommands: escalation gate, session fallback, optional guidance printer.
- docs: `state-management.md`, `resolution-stops.md`, `escalation.md`, `config-check.md`, `dispatch-external-cli.md`, SKILL.md, spec-config `wizard-flow.md`, SKILL.md 358.

### Anti-patterns
- Putting the fallback or escalation flags as string literals anywhere but `lane_settings.py` (arch test fails).
- Adding a Makefile gate scraper to the adapter (duplicates `gp_e2e.py`).
- Applying `^((worktree-)?agent-|worktree-wf_)` to unit branches.
- Failing a lane on the audit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Boolean flag reading with a named error | custom parsing | `_bool_setting` in `lane_settings.py` | existing rule, tested |
| Next lane of another pool | new fallback walker | `lane_settings.lane_fallback` through `lane_switch.next_lane` with `role` | Phase 40 rule, tested |
| Blocked-until read | direct state-file read | `lane_switch.blocked_until` / `blocked_reader` over `--blocked-status` | the one sanctioned reader; never blocks on a bad record |
| jev call | own subprocess to jev | `jev_names.find_jev` + `ask_items` | batching, advisory failure shapes |
| Atomic config write | direct file write | `config_io.cfg_render_lanes` / `toml_splice` | preserves every other byte |
| Child env build | ad hoc `os.environ` copy | `runner_dispatch.child_env` / `RunnerSeams.env_fn` | host-signal scrub already there |

## Common Pitfalls

1. **Role table with no ladder is rejected on write** (`config_io.py:1034-1036`); the flag must ride a role table that has a ladder, or a flat key.
2. **Flags never reach the runner on the superpowers path** (`dispatch_injection.py:384-385`): escalation, pool and switch all depend on carrying lane settings through the injection.
3. **`resolution-stops.md` load trigger** (see A1): widening it breaks the progressive-disclosure test unless a `Do NOT load` clause stays.
4. **NEVER section vs flagged switch** (SKILL.md:31-33): scope the exception to a flagged lane with the owner's flag.
5. **Quota-wake prompt is self-contained text** (`quota-wake.md:8-36`); it must keep its literal restore steps even after the definition moves (its tests pin the order, `test_quota_wake_prompt_order_is_bind_paths_resume_found_scalars_restore`, `:3363`).
6. **`partial` is a `real_error`** (`dispatch_injection.py:425,458`); wrapping tasks in `<task>` blocks changes outcomes.
7. **`.aikit/` ignore rule is repo-specific**; do not assume `.aikit/config.toml` is invisible to clean-tree checks elsewhere.
8. **Jev pick is host-specific**: only Claude Code takes a per-call model.

## Code Examples

Reader shape to copy `[VERIFIED: lane_settings.py:96-107]`:
```python
def _bool_setting(entry: dict, name: str) -> bool:
    value = entry.get(name, False)
    if not isinstance(value, bool):
        raise LaneSettingError(f"{entry.get('key', '<unknown>')}: '{name}' must be a boolean")
    return value
```
Pool pass on the review side to mirror for execute `[VERIFIED: reviewer_dispatch.py:117-119]`:
```python
runner_spec = (review_spec(runtime, entry["model"], entry.get("extra"),
                           spec.timeout_tiers[0], cwd=spec.cwd)._replace(
    pool=lane_settings.lane_free_pool(entry.get("extra") or {})) if runtime else None)
```
Env seam `[VERIFIED: runner_dispatch.py:306]`: `env_fn: Callable[[], dict] = lambda: dict(os.environ)`.

## State of the Art / Runtime State Inventory

Not a rename phase; no runtime-state inventory. Stored resume files (`superpowers-resume-*.json`) keep their schema; the consolidation changes docs only.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "tolerate banners" means "judge a gate by exit code, not output tail" | A5, item (a) | wrong meaning drives a wrong builder line |
| A2 | Meaning (d)/(e) = one caller-fed guard builder on every external path, no ai-kit regex | A3, items (d)/(e) | owner may want a branch check in code |
| A3 | Caller-written `--gates-file` is the narrowest gate source | A4 | owner may want auto-discovery |
| A4 | Item (c): leave `coverage=n/a`, document it | items table | `<task>` wrapping might be wanted |
| A5 | Template edits need a `TEMPLATE_VERSION` bump | Template change | wasted or missed bump |
| A6 | Leave the curated-config `CROSS_AI_COMMAND` unchanged for GSD lanes | B9 | R6's runner-execute-role clause unmet for GSD |
| A7 | HOME-relative list without env overrides is enough for v1 | B10 | missed files under custom config dirs |
| A8 | Role-table placement `[lanes.policy.execute]` for the fallback flag | B7 | planner may prefer a flat key |

## Open Questions

1. **D-02 direction.** Does "escalate along the flag" mean candidates above the anchor (the floor, `escalation.md:28`) filtered by kind, or lanes after the key (`escalation_target`)? Recommendation: floor-filtered; the owner confirms.
2. **EXEC_PREAMBLE scope.** Is the owner's "two briefs" `dispatch_guidance.py` plus `EXEC_PREAMBLE`? If yes, GSD-lane guidance needs a template edit and re-render (procedure above); otherwise untouched.
3. **Item (c).** `n/a` and document, or `<task>` wrapping with `partial` consequences?
4. **Native path text.** How do gates/guard reach a native subagent (prose in SKILL.md vs a printing subcommand)?
5. **Which two real config files were rewritten on 2026-11-23?** Unknown; decides whether the audit list needs more entries.
6. **pi settings file.** Not named in code; unknown.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | all code/tests | yes | 3.15.2 | none |
| node | runner `--blocked-status`, self-tests | yes | v24.21.0 | a missing node already returns None in `blocked_until` |
| uv | unit-uv/integration tiers | not probed | - | `make test` provisions |
| host CLIs | never used (tripwire) | n/a | - | fake lanes via `tests/host_fakes.py` |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest`, run per module by `tools/run_unittest_parallel.py` |
| Config file | `pyproject.toml` (lint), runner groups in `tools/run_unittest_parallel.py` |
| Quick run command | `python3 tools/run_unittest_parallel.py <module>` (module-name form not verified this session; AGENTS.md shows `--group <name>`) |
| Full suite command | `make test`; `make e2e-test`; `make e2e-docker`; `python3 -m unittest tests.test_wizard_pty` |

### Phase Requirements to Test Map
| Req | Behavior | Module (existing = E, new = N) |
|-----|----------|--------------------------------|
| R1 | exactly one marker heading each, second copy fails | N `tests/test_adapter_single_definitions.py` (with non-vacuity); amend E `tests/test_ai_kit_spec_superpowers.py` pins |
| R2 | flag gating (each flag, both, neither, non-boolean refused) | N `tests/test_adapter_escalation_flags.py`; E `tests/test_lane_settings.py` (reader allowlist, flag literal) |
| R3 | fallback on/off, jev pick, round-trip through spec-config write | N `tests/test_adapter_session_fallback.py`; E `tests/test_lane_settings.py`, `tests/test_role_orders.py` (role table), E `tests/test_cross_ai_docs_text.py` (spec-config text) |
| R4 | builders, order, braces framed verbatim, no framework name, dispatch fixture | E `tests/test_ai_kit_spec.py:5217-5246` region (extend) or N `tests/test_dispatch_guidance_gates.py`; E `tests/test_ai_kit_spec_superpowers.py` (`TestDispatchSuperpowersTask`) |
| R5 | six items per table above | N `tests/test_adapter_exec_checks.py` |
| R6 | env var inside a fixture ai-kit checkout (root, subdir, linked worktree), absent in a plain repo, inherited other value forced to 1 | N `tests/test_adapter_real_home_guard.py` |
| R7 | audit reports changed synthetic file in a scratch HOME, none when untouched, spaces/non-ASCII path verbatim, never fails lane | N `tests/test_host_config_audit.py` |
| R8 | four cases + no eligible fallback + same-pool skip + order; review callers byte-identical | N `tests/test_adapter_executor_switch.py`; E review-side tests for lane_switch/lane_ping stay green |
| R9 | single location per topic, narrowed escalation wording | in N doc-contract module of R1 |
| R10 | evals (+4), skill-judge loops | E `tests/test_skill_evals_shape.py`; `make check-dogfood` (judge records) |

Test names are proposals; no such file exists yet `[ASSUMED]`.

### Sampling Rate
- Per task commit: the staged-tests hook (`tools/run_unittest_parallel.py --staged`).
- Per wave merge: `python3 tools/run_unittest_parallel.py` over the touched modules plus `tests.test_arch`, `tests.test_lane_settings`, `tests.test_skill_text_history`, `tests.test_arch_hardcoded_models`.
- Phase gate: `make test`, `make e2e-test`, `make e2e-docker`, `python3 -m unittest tests.test_wizard_pty` green (R10 changes spec-config's SKILL.md surface, so the wizard PTY suite must stay green), `make check-dogfood` after any template touch.

### Wave 0 Gaps
- [ ] R1 doc-contract module with a non-vacuity row.
- [ ] `ALLOWED_READERS` rows for each new reader caller.
- [ ] Fixture ai-kit checkout builder (two marker files) and linked-worktree fixture (no host CLI; `git worktree` via the git binary is allowed in tests, host CLIs are not).
- [ ] Scratch-HOME audit fixtures.

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | caller text framed verbatim, never interpolated (`str.join`, no `format` on caller text); booleans refused with the key named |
| V6 Cryptography | no | none |
| V8/V14 data protection | yes | only summaries to jev; never code, diffs, config values or secrets; audit prints paths, never contents |
| V12 Files | yes | audit reads `st_mtime_ns` only, files only, no recursion; atomic config writes via the existing writer |

Known threats: prompt injection through caller text (framed as data, one frame); real-home writes by an unattended lane (variable set; note it protects only `setup.py`); secret exposure in the audit report (paths only).

## Sources

Primary (read this session): `skills/ai-kit-spec-execute-superpowers/SKILL.md`, its `references/{state-management,resolution-stops,escalation,quota-wake,session-wake,dispatch-external-cli,config-check}.md`, `ai_kit_spec_superpowers/{cli,dispatch_injection}.py`, `skills/ai-kit-spec-review/ai_kit_spec/{dispatch_guidance,lane_settings,lane_switch,execute_dispatch,runner_dispatch,reviewer_dispatch,jev_names,role_orders,detection,jsonc_read}.py` and parts of `config_io.py`, `cli.py`, `jev_review.py`; `skills/ai-kit-spec-review/references/cross-ai.mjs` (cited ranges); `skills/ai-kit-cross-ai/{SKILL.md,references/execute-checks.md}`; `skills/ai-kit-spec-config/references/wizard-flow.md`; `tools/setup.py`, `tools/config_doctor_checks.py`; `tests/test_lane_settings.py`, `tests/test_arch.py`, `tests/test_arch_hardcoded_models.py`, `tests/test_skill_text_history.py`, `tests/test_skill_evals_shape.py`, `tests/test_ai_kit_spec_superpowers.py`; Phase 27 summaries; `.claude/agents/gsd-executor.md`; `41-SPEC.md`, `41-CONTEXT.md`.

## Metadata

**Research date:** 2026-11-25
**Valid until:** until `cross-ai.mjs`, `lane_settings.py` or the adapter references change (30 days at most; fast-moving).

Not checked: whether the listed tests currently pass (none was run); `tests/test_cross_ai_docs_text.py` and `tests/test_role_orders.py` contents beyond their test names; the exact module-name argument form of `run_unittest_parallel.py`; GSD's runtime behavior for `workflow.cross_ai_command` env inheritance (only the runner side was read).
