---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 13
subsystem: judge
tags: [skill-judge, loop-41, jdg-04, referee-one, referee-two, referee-three, ping-lanes]
requires: [41-12]
provides:
  - "Loop 41 records for ai-kit-cross-ai (1 round), ai-kit-spec-config (1 round) and ai-kit-spec-execute-superpowers (2 rounds); REJUDGE.md and facts.json regenerated"
  - "All three skills meet the AGENTS.md bar with no regression (closing gate); each last round's 2-3 high findings fixed under the no-rejudge rule; grade A missed on all three"
affects: [41-14]
key-files:
  created:
    - .planning/judge/loops/41.json
    - .planning/judge/verdicts/41/
  modified:
    - .planning/judge/REJUDGE.md
    - .planning/judge/facts.json
    - skills/ai-kit-cross-ai/SKILL.md
    - skills/ai-kit-cross-ai/references/
    - skills/ai-kit-spec-config/SKILL.md
    - skills/ai-kit-spec-config/references/
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/references/
    - skills/ai-kit-spec-execute-superpowers/evals/evals.json
requirements-completed: []
duration: 70min
completed: 2026-11-26
executor: "orchestrator delegate in the main checkout (cross_ai false); judge lanes opencode router-env/my-referee-one and -two (pool) and router-env/my-referee-three (third lane) through the project runner, review mode, --host none; three native Opus high substitutes (fresh ai-kit-judge subagents) in round 1; fix edits by fresh general-purpose subagents, reviewed and committed by the delegate"
---

# Phase 41 Plan 13: Loop 41 skill-judge loop

Commits: records r1 `71866f0`, r2 `84757bd`; fixes r1 `2a914c7` (cross-ai), `846f6b1` (spec-config), `aa4a4fb` (superpowers, before round 2); r2 `e00735a` (superpowers). Commit scope `docs(41)` / `fix(41)` by the orchestrator's brief (the plan wrote `docs(41-13)` / `fix(41-13)`).

## Judged set

`tmp/judge-41/judged.py` (`judged self-check: ok`), base `26b13b1^` (the commit that added 41-01-PLAN.md): `changed: ai-kit-cross-ai ai-kit-gsd-curated-config ai-kit-spec-config ai-kit-spec-execute-superpowers`. `judged-decisions.txt`: the three ALWAYS skills `judged: SKILL.md changed`; `ai-kit-gsd-curated-config not judged: template number 13 to 14 only` (its diff is the one line `template 13` to `template 14`). No roster edit. Drivers: the step 0 allowlist copied from `tmp/judge-40/` by `copy_drivers.py` (`round scope: ok`, `leftover.sh` empty, confirmations hit, `compile: ok`); collision hits were the loop id or the known exceptions. Added for this plan: `launch_gate.py` (per-key ping lines decide, a missing line is failed, never the exit code), `pool_identity.py`, `gate_selftest.py` (`gate self-test: ok`: every launch-table row, `pool_identity.py` failing on a synthetic `native:opus-high` member, copies of the unmodified `third_lane_once.py` on each row's expected outcome), wrappers gated on `gate-r<N>.txt`. The `p41-13 reviewed:` and judges lines were written by the delegate from the orchestrator's ledger entry 13:45 (reviewed HEAD `f7eb571`).

## Loop 41 bar results

| Skill | Round | Worst percent | Grade | Bar | Prior base | Regression line | Findings (crit+imp+high) | decide.py row | Outcome | Judged SKILL.md digest | Fix commit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ai-kit-cross-ai | 1 | 85.6 (referee-one) | B | met: grade B or better | 84.8 (loop 40 r2) | +0.8, no regression | 3 (referee-one 3) | fix | bar met, then fixed under the no-rejudge rule | `8b02a887a04e4ed5097b56cf3bd7db9d2ee416767c2e3af68e91936711c3ff6b` | `2a914c7` |
| ai-kit-spec-config | 1 | 88.8 (referee-one) | B | met: grade B or better | 84.8 (loop 39.1.3 r3) | +4.0, no regression | 2 (referee-one 2) | fix | bar met, then fixed under the no-rejudge rule | `3e3b0d133a3094bbea9908eeb6c5b7db22595f55fd7830d66f62cea856eb2be0` | `846f6b1` |
| ai-kit-spec-execute-superpowers | 2 | 88.0 worst grade B (lowest percent 84.0, referee-three) | B | met: grade B or better | 87.2 (loop 36 r1) | -3.2, no regression (gate `bar_with_base`, `regression.py` agrees) | 3 (referee-one 3) | fix | bar met, then fixed under the no-rejudge rule | `a8cbf076d63b4df7d0c6af584d5a36f120be5853f827b70fe406c9e46163e349` | `e00735a` |

Per round (percent, grade, critical/high):
- ai-kit-cross-ai r1: one B 85.6 (0/3), two A 98.4 (0/0), Opus substitute for referee-three B 86.4 (0/0); 3 -> fix.
- ai-kit-spec-config r1: one B 88.8 (0/2), two A 96.0 (0/0), Opus substitute B 89.6 (0/0); 2 -> fix.
- ai-kit-spec-execute-superpowers r1: one B 83.2 (0/4), two A 99.2 (0/0), Opus substitute B 88.0 (0/0); 4 -> next-round (fixes `aa4a4fb`). r2: one B 88.0 (0/3), two A 95.2 (0/0), three B 84.0 (0/0); 3 -> fix.

Count rule: `judge_loop.py count` gave 2 for all three skills (no count-1 path, no extra advisory lane).

Missed A (ledger lines): `p41-13 missed A: ai-kit-cross-ai B 85.6`, `p41-13 missed A: ai-kit-spec-config B 88.8`, `p41-13 missed A: ai-kit-spec-execute-superpowers B 84.0`. referee-two gave A in every verdict; referee-one, referee-three and the Opus substitute stayed at B. Owner question: `loop 41: ai-kit-spec-config ended at B 88.8; grade A is the target; decide` (the bar result stands as recorded).

## Loop 41 facts for the verifier

- The judges scored each skill's text with its evals as transcript-assessed text, not executed runs. The behavioural evidence is `tests/test_adapter_single_definitions.py`, `tests/test_adapter_escalation_flags.py`, `tests/test_adapter_session_fallback.py`, `tests/test_host_config_audit.py`, `tests/test_adapter_executor_switch.py`, `tests/test_dispatch_guidance_gates.py`, `tests/test_lane_settings.py`, `tests/test_spec_config_flow_text.py`, `tests/test_ai_kit_spec_superpowers.py` and the runner self-test cases `realhome-*`, run by plan 41-14's `make test` (all modules passed in this plan's unit+arch run, 206/206).
- Referee ping before every round (`ai-kit-spec.py ping-lanes`, keys `judge-referee-one/-two/-three`, `--cwd tmp/judge-41/ping/project`): r1 and r2 each `ping judge-referee-one: ok`, `ping judge-referee-two: ok`, `ping judge-referee-three: ok`; launch gate `pool: launch`, `third: referee-three` both rounds. Runner state after the r1 ping 0 files; after the r2 ping 1 file under `spec/cycles` (a pi-router cycle record of another project).
- Probes (round 1): referee-two usable; referee-one's first probe was rejected (`answer is not the sentinel`: its first line matched the token exactly, then an extra line), so `lanes.py pool` put `native:opus-high` into the pool and `pool_identity.py` stopped the plan with the owner question before any judge work. Orchestrator decision 08:10: the rejected probe moved to `tmp/judge-41/rejected/probe-r1-attempt1/`, one fresh probe of referee-one (new prompt and token, new session) passed (exact token, 23 s), `lanes.py pool` rebuilt the pool as referee-one + referee-two (`native:opus-high` only as `pool.native`, `substitutes: []`), `pool_identity.py: ok`. `legacy retry: none`; `loop record: ok`; `pool check (before)/(after)`: ok every round; `pool identity: ok` before every assign; `third_lane_once.py` exit 0 every round; `evals gate: ok`; `tests.test_skill_evals_shape` ok.
- Lane events: r1 referee-three failed on all three skills after its one retry (both attempts `status=ok exit=0`, ingest refused: verdict judge `o<U+200D>pencode:...`, a zero-width joiner, as in loops 39.1 and 40), so one fresh read-only `ai-kit-judge` subagent on Opus, effort high, given only that skill's `native:opus-high` prompt.md, substituted per skill (owner rule 2026-11-24); answers saved verbatim to `lane.out` with HTML entities restored (`&gt;`, `&lt;`), ingested with `--native-note "native Opus high, substitute for referee-three" --replaces opencode:router-env/my-referee-three`, summaries `advisory-substitute-opus.md`. r1 cross-ai referee-two verdict refused by ingest (`sum(scores) 124 != total 119`), relaunch 1 of 3 through `relaunch_one.py` succeeded. r2 referee-three passed first attempt. Every high finding's claim was checked against the cited code before fixing (cross-ai.mjs `MODEL_ID_FLOOR`, `liveOuterTimeoutS`, execute findings branch, `sameSessionArgv`, `--describe` claude `formulas.exec: true`; ai_kit_spec `to_resolved`, `routing._route_shape`, `_cmd_trust_local`; `fold.py boundary --help`): none quoted text that does not exist, none refuted.
- Frozen tree: HEAD equalled `head.txt` (`f7eb571`, `aa4a4fb`) and no tracked file changed from each launch until `check.py`, `pool_check.py after` and the audits ran.
- `check.py` exit 0 before every fix commit; `check-dogfood: ok` after every records commit and on the final tree; closing `judge_loop.py check .planning/judge --gate --skills ai-kit-cross-ai ai-kit-spec-config ai-kit-spec-execute-superpowers` exit 0 with a `: loop 41` line per skill (`bar met: grade B or better; digest stale`). REJUDGE.md rebuilt with `judge_loop.py report` after the last fix: no diff. `cleanup.sh`: `cleanup: ok`; `tmp/judge-41/home` absent.
- Fix work (each fix commit's hook passed: 16/16, 14/14, 27/27, 27/27 modules; `fix_tests.sh` 22/22 before each): cross-ai model-id checks, execute findings on successful attempts only, timeout fallback, exit-75 relaunch only after `locked`; spec-config probe consent preview and recheck carry each lane's effective fields, custom entries leave the execute set before tests, migrate-only branch confirms through `check-providers`; superpowers state-write exit checks, digest keeps the task not the session, refusals do not undo earlier stages, `boundary --next` accepts `--repo`, eval `exclude` shape, restored-round routing, Node floor read live, codex sandbox source with a commit-policy stop, config-check three load points (r1), then round-4 restore to the escalation gate, claude takes the shim's route, trust preview discloses a pending migration, session fallback at rounds 4-5 (r2). No test file edited.

## Stale-digest notes

- Stale before the loop: ai-kit-commit-fold, ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss, ai-kit-session-wake, ai-kit-spec-config, ai-kit-spec-execute-superpowers, ai-kit-spec-goal-prompt, ai-kit-spec-review, ai-kit-spec-review-checklist, ai-kit-spec-review-fixer, ai-kit-usage-metrics, jev-fast-decision.
- Stale by design after their last-round no-rejudge fixes (`intentional-stale.txt`): ai-kit-cross-ai (`2a914c7`), ai-kit-spec-config (`846f6b1`), ai-kit-spec-execute-superpowers (`e00735a`). `stale_after.py` exits 1 only for `judged still stale: ['ai-kit-spec-execute-superpowers']` for that reason (as loop 40 did for spec-review). Plan 41-14's digest comparison should match the judged digests above plus these fix commits.

## Mtime check of the listed paths

`real_config_audit.py compare`: `mtime check of the listed paths: unchanged` after every round's lanes and at the end. `audit_real_config.py tmp/judge-41/audit.marker`: flagged=5 after the r1 ping and probes, 13 after the r1 lanes, 17 at the r2 ping, 19 from the r2 lanes to the end. All are host-session writes, listed, not chased: host Claude Code (`~/.claude/skills/synced`, `plugins/store`, `.ponytail-active`, `ponytail-modes/`, `history.jsonl`, `jobs/892a2729`) and the codex daemon (`~/.codex` logs, models_cache, app-server-daemon, packages, tmp). Nothing under `~/.config/opencode`, `~/.pi` (beyond session noise) or `~/.gsd`. Runner state at the end: 8 files, 1 pi-router cycle record plus 7 locks/baselines/host files of a home-mobility pi execute run (lock root home-mobility) started 14:48:35, after this loop's last lane ended at 14:45; this loop starts no pi process.

## Deviations

- Round 1 stopped once at the pool identity gate (referee-one's first probe answer carried an extra line); resumed by the orchestrator's 08:10 decision with one fresh probe, not by the plan text.
- The judges never saw the no-rejudge fixes (`2a914c7`, `846f6b1`, `e00735a`). The superpowers r1 fix adds one new stop (a commit-needing codex task stops when Git metadata is read-only) and the r2 fix tells the owner that `trust-local --show` can migrate a pending old roster; `_cmd_trust_local` in ai-kit-spec-review still migrates before `--show` (code of another skill, not changed here).
- Medium findings not taken (no further round for any skill): cross-ai body size and eval fixtures; spec-config step numbering, body size, private-helper preflight, eval fixtures; superpowers description, body moves, write-boundary rule, wake eval, decision table.
- Commit scope `fix(41)` / `docs(41)` per the orchestrator brief instead of the plan's `41-13` scope.
