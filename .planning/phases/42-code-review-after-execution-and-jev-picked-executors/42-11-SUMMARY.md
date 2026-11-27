---
phase: 42-code-review-after-execution-and-jev-picked-executors
plan: 11
subsystem: judge
tags: [skill-judge, loop-42, jdg-04, referee-one, referee-three, ping-lanes]
requires: [42-10]
provides:
  - "Loop 42 records for ai-kit-spec-execute-superpowers (1 round); REJUDGE.md and facts.json regenerated"
  - "The adapter meets the AGENTS.md bar with no regression (closing gate); round 1's 3 high findings fixed under the no-rejudge rule; grade A missed (B 84.0)"
affects: [42-12]
key-files:
  created:
    - .planning/judge/loops/42.json
    - .planning/judge/verdicts/42/
  modified:
    - .planning/judge/REJUDGE.md
    - .planning/judge/facts.json
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/references/code-review.md
    - skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md
    - skills/ai-kit-spec-execute-superpowers/references/fold-step.md
    - tests/test_ai_kit_spec_superpowers.py
requirements-completed: []
duration: 30min
completed: 2026-11-27
executor: "orchestrator delegate in the main checkout (cross_ai false); judge lanes opencode router-env/my-referee-one and router-env/my-referee-three (pool) through the project runner, review mode, --host none; no native substitute needed; fix edits and commits by the delegate"
---

# Phase 42 Plan 11: Loop 42 skill-judge loop

Commits: records r1 `2da05b9`; fix r1 `b9aa7b3`.

## Judged set

`tmp/judge-42/judged.py` (`judged self-check: ok`), base `c98bab0^` (the commit that added 42-01-PLAN.md): `changed: ai-kit-spec-execute-superpowers`. `judged-decisions.txt`: `ai-kit-spec-execute-superpowers judged: SKILL.md changed`; `ai-kit-cross-ai` and `ai-kit-gsd-curated-config` were not listed (no template bump). Fact-only (a reference `.md` changed, SKILL.md not): `ai-kit-spec-config`, not judged. No roster edit. Drivers copied from `tmp/judge-41.1/` by `copy_drivers.py` (`pool sites: ok`; collisions exactly the two known harmless lines), plus the step 1b substitute branch (`lanes.py` `THREE`/`substitute_round`, `pool_identity.py`, `pool_check.py`, step exits in `prelaunch.sh`/`launch.sh`/`next_round.sh`, `reprobe_three.sh`, `gate_selftest.py` cases); `compile: ok`; `gate self-test: ok` (its all-ok, three-failed and one-failed rows are the three synthetic launch-gate cases). `p42-11 reviewed: cce9e30...` and the judges line were written to `tmp/judge-42/ledger.md` before the first probe.

## Loop 42 bar results

| Skill | Round | Worst percent | Grade | Bar | Prior base | Regression line | Findings (crit+imp+high) | decide.py row | Outcome | Fix commit |
|---|---|---|---|---|---|---|---|---|---|---|
| ai-kit-spec-execute-superpowers | 1 | 84.0 (referee-one) | B | met: grade B or better | 84.0 (loop 41 r2) | +0.0, no regression (gate and `regression.py` agree) | 3 (referee-one 3) | fix | bar met, then fixed under the no-rejudge rule | `b9aa7b3` |

Per round (percent, grade, critical/high): r1 referee-one B 84.0 (0/3), referee-three B 87.2 (0/0); 3 -> fix.

Count rule: `judge_loop.py count` gave 2 (no count-1 path).

Missed A: `p42-11 missed A: ai-kit-spec-execute-superpowers B 84.0` (both judges at B; target A not reached, the bar result stands).

## Loop 42 facts for the verifier

- The judges scored the skill text and its evals as transcript-assessed text, not executed runs. The behavioural evidence is `tests/test_code_review.py`, `tests/test_executor_pick.py`, `tests/test_lane_transport.py`, `tests/test_herdr_pane.py`, `tests/test_jev_review.py`, `tests/test_lens_delivery.py`, `tests/test_adapter_single_definitions.py` and `tests/test_ai_kit_spec_superpowers.py`, run by plan 42-12's `make test` (all passed in this plan's unit+arch run, 211/211).
- Referee ping before round 1 (`ai-kit-spec.py ping-lanes` through `ping_round.py 1`, keys `judge-referee-one`, `judge-referee-three`): `ping judge-referee-one: ok`, `ping judge-referee-three: ok`; launch gate `pool: launch`, `three: lane`; runner state after the ping 0 files.
- Probes: both usable first time (exact token; referee-one 13 s, referee-three 3 s); pool 42 = referee-one + referee-three; `pool identity: ok`; `loop record: ok`; `pool check (before)/(after)`: ok; `three_once.py` exit 0 (slot 1); `evals gate: ok`; `tests.test_skill_evals_shape` ok; `legacy retry: none`.
- Lanes: both ok on the first attempt (referee-one 546 s, referee-three 51 s); no relaunch, no substitute.
- Frozen tree: HEAD equalled `head.txt` (`cce9e30`) and no tracked file changed from the launch until `check.py`, `pool_check.py after` and the audits ran.
- `check.py` exit 0 before the fix commit; `check-dogfood: ok` after the records commit and on the final tree; closing `judge_loop.py check .planning/judge --gate --skills ai-kit-spec-execute-superpowers` exit 0 with its `: loop 42` line (`bar met: grade B or better; lowest percent 84.0, loop 41 base 84.0; digest stale`). REJUDGE.md rebuilt after the fix: no diff.
- Fix work (each high checked against the cited text and code, none refuted): the code-review fix dispatch branches on the class right after the Classify block and stops on a non-ok class without the task-level switch, state write or wake (`code-review.md`); the native status handoff is its own section `dispatch-external-cli.md#native-status`, read alone after a native dispatch, and both "do not load" lines name that exception (`SKILL.md`, `dispatch-external-cli.md`); Step 5 clears the start scalars on the plain fold's `folded` or `nothing to fold` with `UNIT_FLOW=0` (`fold.py superpowers` exits 0 for both), and `fold-step.md` names them. Pins in `tests/test_ai_kit_spec_superpowers.py`. `fix_tests.sh` 13/13 and the commit hook 31/31 passed. SKILL.md 296 lines and 3937 body words before, 296 lines and 3961 after.
- Gates on `b9aa7b3`: `make check-dogfood`, `ruff`, `pyright`, `vulture`, `pylint` exit 0; unit+arch under orch-guard exit 0 (211/211, peak 6, not killed).

## Stale-digest notes

- Stale before the loop: ai-kit-commit-fold, ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss, ai-kit-session-wake, ai-kit-spec-config, ai-kit-spec-execute-superpowers, ai-kit-spec-goal-prompt, ai-kit-spec-review, ai-kit-spec-review-checklist, ai-kit-spec-review-fixer, ai-kit-usage-metrics, jev-fast-decision.
- Stale by design after the round-1 no-rejudge fix (`intentional-stale.txt`): ai-kit-spec-execute-superpowers (`b9aa7b3`). `stale_after.py` exits 1 only for `judged still stale: ['ai-kit-spec-execute-superpowers']` for that reason, as in loop 41.

## Mtime check of the listed paths

`real_config_audit.py compare`: `mtime check of the listed paths: unchanged` after the probes, after the lanes and at the end. `audit_real_config.py tmp/judge-42/audit.marker`: flagged=4 after the ping, 6 after the probes, 13 from the lanes to the end. All are host-session writes, listed, not chased: host Claude Code (`~/.claude/plugins/store`, `skills/synced`) and the codex daemon (`~/.codex` logs, models_cache, app-server-daemon, packages, tmp). Nothing under `~/.config/opencode`, `~/.pi` (beyond session noise) or `~/.gsd`. Runner state after the lanes: 2 files (a lock and a baseline) of a pi run rooted at another checkout, started 18:56:30 while this loop ran only opencode lanes; 0 files at the end.

## Deviations

- Before any judge step, the delegate ran `tmp/judge-41.1/report.sh` by mistake, which regenerated `.planning/judge/REJUDGE.md` and `facts.json` (facts drift only); both were written back from their HEAD blobs by `tmp/judge-42/restore_accident.py` and the tree was clean before round 1.
- Medium findings not taken (no further round): body size and Exec confinement move, fix-round decision table, Gotchas section, quota-wake pointer, Codex source check date, Agent effort schema check, review background launch, transport eval fixture.
