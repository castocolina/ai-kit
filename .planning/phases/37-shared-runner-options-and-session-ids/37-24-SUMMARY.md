---
phase: 37-shared-runner-options-and-session-ids
plan: 24
subsystem: judge
tags: [skill-judge, loop-37, jdg-04, referee-one, referee-two]

requires: [37-23]
provides:
  - "Loop 37 records for ai-kit-cross-ai (rounds 1-3), ai-kit-gsd-curated-config (round 1) and ai-kit-spec-config (rounds 1-3), judged by referee-one and referee-two only; REJUDGE.md regenerated"
  - "ai-kit-cross-ai meets the bar for the first time (prior base 76.8, grade C); its inputs.json `deferred` entry is removed"
  - "ai-kit-spec-config ends round 3 with 5 high findings: recorded as it stands and returned to the owner"
  - "Seven fix commits under the fix rule or before the next round, each with its fixes.md"

key-files:
  modified:
    - .planning/judge/REJUDGE.md
    - .planning/judge/facts.json
    - .planning/judge/inputs.json
    - .planning/judge/loops/37.json
    - .planning/judge/verdicts/37/
    - skills/ai-kit-cross-ai/SKILL.md
    - skills/ai-kit-cross-ai/references/launch-and-wait.md
    - skills/ai-kit-cross-ai/references/subprocess-quota-policy.md
    - skills/ai-kit-gsd-curated-config/references/runner.md
    - skills/ai-kit-spec-config/SKILL.md
    - skills/ai-kit-spec-config/references/catalog.md
    - skills/ai-kit-spec-config/references/cli-model-selection.md
    - skills/ai-kit-spec-config/references/free-lanes.md
    - skills/ai-kit-spec-config/references/wizard-flow.md

requirements-completed: [RUN-01]

executor: "orchestrator action in the main checkout (cross_ai false); judge lanes opencode router-env/my-referee-one and router-env/my-referee-two through the project runner, review mode"
---

# Phase 37 Plan 24: Loop 37 skill-judge loop

Commits (pre-fold): round 1 records `3973eb4`; round 1 fixes `8860115` (ai-kit-gsd-curated-config), `cb86db4` (ai-kit-cross-ai), `6b31202` (ai-kit-spec-config); round 2 records `53a16c6`; round 2 fixes `abf3390` (ai-kit-cross-ai), `95869f5` (ai-kit-spec-config); round 3 records `5c70a92`; round 3 fix `bddf7d8` (ai-kit-cross-ai); gate fix `3545592` (ai-kit-spec-config, a line the old-name scan flagged).

Status: the loop is complete; the final `make test` gate is green after the Volta fork loop fix (see Final gate).

Volta fork loop fix commits (outside the judged skills, by the orchestrator's executor): `ad5823b` (`fix(37)`: the goal-prompt dogfood detect env puts the real node binary first on PATH) and `f17cb4a` (`fix(37)`: the runner `--describe` and `--print-argv` children run in their own session and their whole process group is killed on a timeout or any error; regression test `tests/test_runner_fork_chain.py` with a self-running `node` shim capped at five links).

Judged set from git (`tmp/judge-37/judged.py`, materiality self-check ok): base `e400d38^`; changed ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-spec-config, ai-kit-spec-review; material and judged ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-spec-config; fact-only ai-kit-spec-review (no SKILL.md change). Pool: referee-one and referee-two (opencode), no native judge, no referee-three; count 2 per skill; pool check before and after ok in every round.

## Loop 37 bar results

| Skill | Round | Worst percent | Grade | Bar | Findings (crit+imp+high) | decide.py row |
|---|---|---|---|---|---|---|
| ai-kit-cross-ai | 1 | 85.6 | B | met | 5 | next-round; fixed before round 2 in cb86db4 |
| ai-kit-cross-ai | 2 | 84.8 | B | met | 4 | next-round; fixed before round 3 in abf3390 |
| ai-kit-cross-ai | 3 | 83.2 | B | met | 3 | fix -> bddf7d8 |
| ai-kit-gsd-curated-config | 1 | 88.0 | B | met | 1 | fix -> 8860115 |
| ai-kit-spec-config | 1 | 80.0 | B | not met (regression) | 6 | next-round; fixed before round 2 in 6b31202 |
| ai-kit-spec-config | 2 | 82.4 | B | met | 5 | next-round; fixed before round 3 in 95869f5 |
| ai-kit-spec-config | 3 | 84.0 | B | met | 5 | owner-round-3 (recorded as it stands, no fourth round) |

`regression.py` lines:

- round 1: `ai-kit-cross-ai: lowest 85.6 (2 valid, 0 invalid), loop 32 r1 base 76.8, delta +8.8, regression: no`
- round 1: `ai-kit-gsd-curated-config: lowest 88.0 (2 valid, 0 invalid), loop 33 r1 base 97.6, delta -9.6, regression: yes`
- round 1: `ai-kit-spec-config: lowest 80.0 (2 valid, 0 invalid), loop 36 r1 base 88.8, delta -8.8, regression: yes`
- round 2: `ai-kit-cross-ai: lowest 84.8 (2 valid, 0 invalid), loop 32 r1 base 76.8, delta +8.0, regression: no`
- round 2: `ai-kit-spec-config: lowest 82.4 (2 valid, 0 invalid), loop 36 r1 base 88.8, delta -6.4, regression: no`
- round 3: `ai-kit-cross-ai: lowest 83.2 (2 valid, 0 invalid), loop 32 r1 base 76.8, delta +6.4, regression: no`
- round 3: `ai-kit-spec-config: lowest 84.0 (2 valid, 0 invalid), loop 36 r1 base 88.8, delta -4.8, regression: no`

Rubric caveat (ai-kit-gsd-curated-config): its loop 33 record (97.6) was judged on rubric version 4; loop 37 uses rubric 5. `tools/judge_loop.py` compares only records on the same rubric pin, finds no comparable prior base and reports `bar met: grade B or better`; the scratch `regression.py` ignores the pin, so its `regression: yes` line is not a regression by the tool's rule. Owner-visible note, not a bar failure.

Owner item (ai-kit-spec-config, past the three-round cap): scores 80.0 / 90.4 (round 1), 82.4 / 87.2 (round 2), 84.0 / 91.2 (round 3), referee-one / referee-two. The bar is met in round 3 (grade B, lowest 84.0 vs base 88.8, no regression), but 5 high findings remain, unfixed:

- referee-one D8-1 (SKILL.md:138): the Step 1.5 skip branch for an unapproved pending roster is bypassed by `references/cli-model-selection.md:31`, which runs the same migrating `fetch-model-catalog`; on a cold cache the skip leaves no catalog for the proposal or the writer's `--catalog-path`.
- referee-one D8-2 (SKILL.md:435): "show its command text from the file" cannot show a command-bearing override that inherits its template from the user config, and a flattened preview keyed by lane key cannot say which role's argv it shows.
- referee-one D8-3 (references/wizard-flow.md:38): the unknown-effort probe is offered to custom command lanes, which the probe treats as unsupported for lane effort.
- referee-one D8-4 (references/check-only.md:27): the preflight embeds `$(pwd)` in a Python string literal (a path with an apostrophe breaks it), and "none was printed" does not tell an empty JSON result from a preflight failure.
- referee-two D8-1 (SKILL.md:28): "see its Step 0.7 point 0" should point at ai-kit-spec-review's `references/cross-ai-dispatch.md`.

Several of these (and round 1-2 findings fixed as text) name code behaviour (catalog discovery migrating rosters, the `trust-local --show` preview) that a code change, not skill text, would settle.

## Loop 37 facts for the verifier

- Judges: referee-one `opencode:router-env/my-referee-one` configured; referee-two `opencode:router-env/my-referee-two` configured. Probes both usable (`AIKIT-XAI status=ok ... exit=0`, 20 s each).
- Round 1 lanes (6): all `AIKIT-XAI status=ok cli=opencode exit=0 cli_rc=0 tree=clean attempts=1 cycles=0`; referee-one 304 s / 312 s / 495 s, referee-two 59 s / 68 s / 72 s.
- Round 2 lanes (4): all status=ok exit=0 tree=clean attempts=1; referee-one 179 s / 407 s, referee-two 77 s / 73 s.
- Round 3 lanes: referee-one cross-ai 454 s and spec-config 314 s, referee-two cross-ai 146 s, all status=ok exit=0 tree=clean. referee-two on ai-kit-spec-config: first run `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=87s out=480142 tree=clean ... attempts=1 cycles=0`, verdict rejected by ingest (`D1 is below its max but has no finding`, record verdict null; ledger line in `tmp/judge-37/ledger.md`). Orchestrator decision: re-run only that lane, same judge, new session, up to 3 attempts. Fresh attempt 1 (`tmp/judge-37/relaunch_one.py`, which keeps the judge's valid cross-ai record instead of refusing): `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=108s out=606215 tree=clean attempts=1 cycles=0`, dict verdict 91.2 A. No substitute judge was started.
- `verdict_facts.py` verdicts: cross-ai 85.6 B (5 high) / 88.8 B (0), 84.8 B (4) / 89.6 B (0), 83.2 B (3) / 91.2 A (0); curated-config 88.0 B (1) / 92.8 A (0); spec-config 80.0 B (6) / 90.4 A (0), 82.4 B (5) / 87.2 B (0), 84.0 B (4) / 91.2 A (1); no critical, no substitute.
- `check.py` (`--require-current`) exit 0 before each round's fix commits (rounds 1, 2 and 3).
- Closing `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/judge_loop.py check .planning/judge`: exit 0 after the last fix commit; `: loop 37` lines for ai-kit-cross-ai (round 3, bar met, digest stale), ai-kit-gsd-curated-config (round 1, bar met, digest stale) and ai-kit-spec-config (round 3, bar met, digest current); notes: `stale digest` for ai-kit-cross-ai and ai-kit-gsd-curated-config by design after their fix commits, plus seven skills stale before the loop; no facts-drift line.
- `make check-dogfood`: `check-dogfood: ok` before each of the three records commits.
- `stale_after.py`: `stale ok` in rounds 1, 2 and 3 (before the fix commits).
- `evals_gate.py`: `evals gate: ok` (each judged skill has an evals.json case; the scratch skill without evals fails as designed).
- `clear_deferred.py`: round 1 `deferred cleared` (ai-kit-cross-ai's latest bar met; report and check.py re-run, exit 0); rounds 2 and 3 `deferred already absent`.
- `decide.py --self-check`: `decide self-check: ok`.

## Stale-digest notes

- Stale before the loop: ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss, ai-kit-session-wake, ai-kit-spec-config, ai-kit-spec-execute-superpowers, ai-kit-spec-review, ai-kit-spec-review-checklist, ai-kit-usage-metrics, jev-fast-decision.
- Stale by design after their fix commits (`tmp/judge-37/intentional-stale.txt`): ai-kit-gsd-curated-config, ai-kit-cross-ai. `report` was not re-run after a fix commit.

`bar-results.json`:

- `bar ai-kit-cross-ai: met (round 3)`
- `bar ai-kit-gsd-curated-config: met (round 1)`
- `bar ai-kit-spec-config: met (round 3)`

## Mtime check of the listed paths

`mtime check of the listed paths: unchanged` (after each round's lanes and after the referee-two re-run; snapshot of 5 present files taken in round 1).

## Final gate

- `make test` run 1 (under `orch-guard.py`): unit tier `176/177 modules passed`, `failed: tests.test_config_callers` (a round 1 spec-config line named `review-spec.toml` without the word migration; the commit hook does not select that glob-reading module). Fixed in `3545592`.
- `make test` run 2 (under `orch-guard.py`): unit `177/177 modules passed`, unit-uv `3/3`, integration `9/9`; during the e2e group the guard killed the run: `exit -9 peak_runner_procs 219 killed: runners=219 mem_available_mb=8425`, the samples a chain of `/home/bazzite/.volta/bin/node .../cross-ai.mjs --describe` processes, each the child of the previous. This is the Volta-shim fork loop found in plan 37-20's chunk (under a test HOME without Volta's config the shim runs `node` from PATH, which is itself), reached here through product code: `ai_kit_spec/runner_facts.py:58` calls `read_runner_describe(which_fn("node"), ...)` from the runtimes snapshot, which e2e modules run under a temporary HOME. The fix is outside the judged skills' files, so it went back to the orchestrator (plan step 14).
- Root cause: run one module at a time under the guard, `tests.test_ai_kit_spec_goal_prompt_e2e` was killed (`exit -9 peak_runner_procs 341`, the same `--describe` chain). Its dogfood test gave the goal-prompt CLI an env of PATH (host fakes plus the caller's PATH), a temporary HOME and no `VOLTA_HOME`; the detect built the runtimes snapshot, whose `--describe` read found the Volta shim. `subprocess.run`'s timeout kills only the first link, so the orphaned chain kept forking after the kill. Fixed by `ad5823b` and `f17cb4a` (above); the regression test fails with the bounded run switched off (four links left alive) and passes with it.
- `make test` run 3 (under `orch-guard.py`, after the fix): `exit 0 peak_runner_procs 10 killed: no`; unit `178/178 modules passed`, unit-uv `3/3 modules passed`, integration `9/9 modules passed`, e2e `25/25 modules passed`, `tests/test_install.sh` `48 passed, 0 failed`, arch `2/2 modules passed`. The final gate is green.
- `python3 tmp/run-2026-11-19/p37-23/added_line_scan.py` (re-run after the fix): `scan: ok (0 expected-message edits, no new line naming grok)`.

## Deviations and notes

- The round 1 and round 2 fixes for skills taking `next-round` were made directly in the skills' own files before the next round (one fix commit per skill and round, with fixes.md), as loop 36 did, instead of a gap plan.
- While the referee-two re-run lane ran in round 3, two tracked ai-kit-cross-ai files were edited for about a minute and then restored byte-equal before the lane ended; the lane reported `tree=clean`. The round 3 fixes were re-applied after all lanes ended.
- `relaunch_one.py` (copied from loop 36) was changed to keep a judge's valid record of another skill instead of refusing, because referee-two also judged ai-kit-cross-ai in round 3.
- Processes: probe pids 1628973, 1628985; worker pgids 1639950, 1639951 (round 1), 2134259, 2134260 (round 2), 2342339, 2342340 (round 3), 2604162 (referee-two re-run); all ended.
