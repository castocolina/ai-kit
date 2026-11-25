---
phase: 40-resilient-review-sized-by-jev
plan: 12
subsystem: judge
tags: [skill-judge, loop-40, jdg-04, rev-07, referee-one, referee-two, referee-three, ping-lanes]
requires: [40-11]
provides:
  - "Loop 40 records for ai-kit-spec-review (3 rounds), ai-kit-cross-ai (2 rounds) and ai-kit-spec-review-fixer (1 round); REJUDGE.md and facts.json regenerated"
  - "All three skills meet the AGENTS.md bar with no regression; the last round's 2-3 high findings of each fixed under the no-rejudge rule"
affects: [40-13]
key-files:
  created:
    - .planning/judge/loops/40.json
    - .planning/judge/verdicts/40/
    - skills/ai-kit-spec-review/references/lane-capabilities.md
    - skills/ai-kit-cross-ai/references/hosting-and-locks.md
    - skills/ai-kit-cross-ai/references/execute-checks.md
    - skills/ai-kit-cross-ai/references/setting-reasons.md
  modified:
    - .planning/judge/REJUDGE.md
    - .planning/judge/facts.json
    - skills/ai-kit-spec-review/SKILL.md
    - skills/ai-kit-spec-review/ai_kit_spec/review_reports.py
    - skills/ai-kit-spec-review/references/
    - skills/ai-kit-cross-ai/SKILL.md
    - skills/ai-kit-cross-ai/references/subprocess-quota-policy.md
    - skills/ai-kit-cross-ai/evals/
    - skills/ai-kit-spec-review-fixer/SKILL.md
    - tests/test_ai_kit_spec.py
    - tests/test_cross_ai_docs_text.py
    - tests/test_cross_ai_settings_text.py
    - tests/test_lane_failure_text.py
requirements-completed: []  # JDG-04 and REV-07: requirements.ready-ids reports both blocked; not marked
duration: 105min
completed: 2026-11-25
executor: "orchestrator delegate in the main checkout (cross_ai false); judge lanes opencode router-env/my-referee-one and -two (pool) and router-env/my-referee-three (third lane) through the project runner, review mode, --host none; one native Opus high substitute (fresh ai-kit-judge subagent); fix edits by fresh general-purpose subagents, reviewed and committed by the delegate"
---

# Phase 40 Plan 12: Loop 40 skill-judge loop

Commits: records r1 `57fa1e1`, r2 `2f58eeb`, r3 `7fb52be`; fixes r1 `cdaed6d` (fixer), `61515cd` (spec-review), `81ef7d0` (cross-ai); r2 `fbd2ad1` (cross-ai), `be2e88e` (spec-review); r3 `90b3fff` (spec-review). Commit scope `docs(40)` / `fix(40)` by the orchestrator's brief (the plan wrote `docs(40-12)` / `fix(40-12)`); subjects as the plan wrote them.

## Judged set

`tmp/judge-40/judged.py` (`judged self-check: ok`), base `d015384^` (the commit that added 40-01-PLAN.md): `changed: ai-kit-cross-ai ai-kit-spec-review ai-kit-spec-review-fixer`. `judged-decisions.txt`: the three ALWAYS skills `judged: SKILL.md changed`; `ai-kit-spec-review-checklist: not judged: no change`. No roster edit (scratch `inputs.json` byte-identical). Drivers: the step 0 allowlist copied from `tmp/judge-39.2/` by `copy_drivers.py` (all five checks ok, leftover `rg` empty, D9 adaptations present, `verdict_facts.py` path rewritten); collision hits were the loop id or prose (one comment `plan 39.2-09` in publish.py, comment only). Added: `third_lane_once.py`, `state_audit.py`, `ping_round.py`, rewritten `closing.sh` (`check --gate --skills` the three).

## Loop 40 bar results

| Skill | Round | Worst percent | Grade | Bar | Prior base | Regression line | Findings (crit+imp+high) | decide.py row | Outcome | Judged SKILL.md digest | Fix commit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ai-kit-spec-review | 3 | 86.4 worst grade B (lowest percent 84.8, referee-three) | B | met: grade B or better | 82.4 (loop 39 r3) | +2.4, no regression | 3 (referee-one 3) | fix | bar met, then fixed under the no-rejudge rule | `7908c077efc6edb5085ce731c42448d054e9b2eddc87598e289ffa110d3515ae` | `90b3fff` |
| ai-kit-cross-ai | 2 | 84.8 (referee-one) | B | met: grade B or better | 84.8 (loop 39 r1) | +0.0, no regression | 3 (referee-one 3) | fix | bar met, then fixed under the no-rejudge rule | `80cafd32a04393c3d8a2e165dd7fd6d7000822e1165d7a9881a8ac35dbeabedc` | `fbd2ad1` |
| ai-kit-spec-review-fixer | 1 | 88.0 worst grade B (lowest percent 87.2, referee-three) | B | met: grade B or better | 81.6 (loop 32.1 r1) | +5.6, no regression | 2 (referee-one 2) | fix | bar met, then fixed under the no-rejudge rule | `adcc12c2fb10e41ff793e8dfacc9072e5e048d3ec9d7c7499f61233a37525fc7` | `cdaed6d` |

Per round (percent, grade, critical/high):
- ai-kit-spec-review r1: one B 85.6 (0/4), two A 92.8 (0/1), three C 77.6 (0/1); bar not met; 6 -> next-round (fixes `61515cd`). r2: one B 84.8 (0/5), two A 93.6, three B 85.6; bar met; 5 -> next-round (fixes `be2e88e`). r3: one B 86.4 (0/3), two A 97.6, three B 84.8; 3 -> fix.
- ai-kit-cross-ai r1: one B 80.8 (0/3), two A 96.0, three B 81.6 (0/1); bar met; 4 -> next-round (fixes `81ef7d0`). r2: one B 84.8 (0/3), two A 98.4, Opus substitute for referee-three B 87.2 (0/0); 3 -> fix.
- ai-kit-spec-review-fixer r1: one B 88.0 (0/2), two A 95.2, three B 87.2; 2 -> fix.

Missed A (ledger lines): `p40-12 missed A: ai-kit-spec-review B 84.8`, `p40-12 missed A: ai-kit-cross-ai B 84.8`, `p40-12 missed A: ai-kit-spec-review-fixer B 87.2`. referee-two gave A in every round; referee-one and referee-three stayed at B.

## Loop 40 facts for the verifier

- The judges scored each skill's text with its evals as transcript-assessed text, not executed runs. The behavioural evidence for SPEC R1-R7 is `tests/test_review_log.py`, `tests/test_lane_ping.py`, `tests/test_lane_switch.py`, `tests/test_jev_review.py`, `tests/test_review_signals.py`, `tests/test_fold_check.py`, `tests/test_lane_failure_text.py`, run by plan 40-13's `make test` (all passed in this plan's unit+arch run, 200/200 modules).
- Referee ping before every round (`ai-kit-spec.py ping-lanes`, keys `judge-referee-one/-two/-three`, `--cwd tmp/judge-40/ping/project`): r1, r2 and r3 each `ping judge-referee-one: ok`, `ping judge-referee-two: ok`, `ping judge-referee-three: ok`, exit 0; runner state after each ping: 0 files.
- Probes (round 1): referee-one usable (18 s), referee-two usable (19 s); pool 40 = referee-one, referee-two; `native:opus-high` recorded as `pool.native`. Count (`--no-jev`): 2 for all three skills (no count-1 path, no extra advisory lane). `legacy retry: none`; `loop record: ok`; `pool check (before)/(after)`: ok every round; `third_lane_once.py` exit 0 every round; `evals gate: ok`; `tests.test_skill_evals_shape` ok.
- Lane events: r2 cross-ai referee-two verdict refused by ingest (`sum(scores) 122 != total 112`), relaunch 1 of 3 succeeded. r2 cross-ai referee-three failed after its one retry (both attempts `status=ok exit=0`, ingest refused: verdict judge with a zero-width joiner, `o<U+200D>pencode:...`), so a fresh read-only `ai-kit-judge` subagent on Opus, effort high, given only the `native:opus-high` prompt.md, substituted (owner rule 2026-11-24); ingested with `--native-note "native Opus high, substitute for referee-three" --replaces opencode:router-env/my-referee-three`, summary `advisory-substitute-opus.md`. Every other lane passed on the first attempt. Every high finding's cited code was opened (cross-ai.mjs session, execute-findings and blocked-until paths, review_reports.py `_status_value`, config_io.py `resolve_timeout_tiers`, gsd-core `closed-phase-gate.md`): none quoted text that does not exist.
- Frozen tree: HEAD equalled `head.txt` (`a219f8a`, `81ef7d0`, `be2e88e`) and no tracked file changed from each launch until `check.py`, `pool_check.py after` and the audits ran.
- `check.py` exit 0 before every fix commit; `check-dogfood: ok` after every records commit and on the final tree; closing `judge_loop.py check .planning/judge --gate --skills ai-kit-cross-ai ai-kit-spec-review ai-kit-spec-review-fixer` exit 0 with a `: loop 40` line per skill (`bar met: grade B or better; digest stale`). REJUDGE.md was rebuilt with `judge_loop.py report` after the last fix: no diff. `cleanup.sh`: `cleanup: ok`; `tmp/judge-40/home` absent.
- Fix work: SKILL.md bodies moved detail verbatim to references (spec-review 580 -> 498 lines; cross-ai 48534 -> 39942 bytes); one code fix with a red/green regression test (`review_reports.py`: only `Approved` and `Approved (partial)` approve). Each fix commit's hook passed (5/5, 155/155, 16/16, 16/16, 155/155, 155/155 modules).

## Stale-digest notes

- Stale before the loop: ai-kit-commit-fold, ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss, ai-kit-session-wake, ai-kit-spec-config, ai-kit-spec-execute-superpowers, ai-kit-spec-goal-prompt, ai-kit-spec-review, ai-kit-spec-review-checklist, ai-kit-spec-review-fixer, ai-kit-usage-metrics, jev-fast-decision.
- Stale by design after their last-round no-rejudge fixes (`intentional-stale.txt`): ai-kit-spec-review-fixer (`cdaed6d`), ai-kit-cross-ai (`fbd2ad1`), ai-kit-spec-review (`90b3fff`). `stale_after.py` reports ai-kit-spec-review as judged-still-stale for that reason (as loop 39.1.3 did). Plan 40-13's digest comparison should match the judged digests above plus these fix commits.

## Mtime check of the listed paths

`real_config_audit.py compare`: `mtime check of the listed paths: unchanged` after every round's lanes (snapshots before each round). `audit_real_config.py tmp/judge-40/audit.marker`: flagged=2 after the r1 ping, 21 after the r1 lanes, 32 from the r2 ping to the end. All are host-session or other-project writes, listed, not chased: host Claude Code (`~/.claude/plugins/store`, `plugins/cache/*/.in_use/795396` of a claude process started 18:37, `plugins/synced`, `known_marketplaces.json`, `plugin-directory-cache-v2.json`, `skills/synced`, `jobs/`, `.ponytail-active`, `ponytail-modes/`, `history.jsonl`, `.last-cleanup`), the codex daemon (`~/.codex` logs, models_cache, app-server-daemon, packages, tmp), and `~/.pi/agent/settings.json` (18:59:26) and `models-store.json` (18:59:28): the loop starts no pi process, and every pi session file newer than the marker belongs to the home-mobility or gitid projects (home-mobility sessions 18:54 and 19:01). Nothing under `~/.config/opencode`. Runner state after the r1 lanes listed 7 files of a home-mobility pi execute run (locks, baselines, host), not this loop's; 0 files after every ping.

## Deviations

- Real-config audit: `~/.pi/agent/settings.json` (one of the eight paths `real_config_audit.py` watches) and `models-store.json` changed at 18:59, between the round 1 validation and the round 2 snapshot, so the "unchanged" compare lines hold only per round. The plan stops on a flagged path; the run continued because the change is attributed to the home-mobility project's pi sessions (pi session files 18:54 and 19:01, the loop starts no pi process). The attribution is inferred, not proven; the owner decides.
- The judges never saw the round-3 no-rejudge fix of ai-kit-spec-review (`90b3fff`): it adds an owner-consent step before a native GSD revise whose write or commit scope reaches beyond the named documents, which can pause an unattended plan-review run at that point.
- Gates ran at `90b3fff`; the SUMMARY commit is docs-only. The commit hooks deferred `tests.test_ai_kit_gsd_curated_config_matrix` to push; it was not run here.
- The Opus substitute's answer was saved to `lane.out` from the subagent's final message (angle brackets restored where the message showed HTML entities); ingest validated it.

- Wrapper scripts were adapted from `tmp/judge-39.1.3/` (py.sh, pgid_add.py, launch/next_round/validate/finish_round/end) with the plan's order: ping before probes, count only in round 1, no re-count in later rounds.
- Fixes covered shared mediums too (goal grade A); none removed behaviour. Test modules retargeted to moved text keep every check (`test_cross_ai_settings_text`, `test_cross_ai_docs_text`).
- Commit scope `fix(40)` / `docs(40)` per the orchestrator brief instead of the plan's `40-12` scope.
