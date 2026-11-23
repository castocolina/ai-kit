---
phase: 38-runner-hardening-and-run-safety
plan: 26
subsystem: judge
tags: [skill-judge, loop-38, jdg-04, referee-one, referee-two]

requires: [38-25]
provides:
  - "Loop 38 records for ai-kit-cross-ai and ai-kit-gsd-curated-config (round 1 each), judged by referee-one and referee-two only; REJUDGE.md and facts.json regenerated"
  - "Both skills meet the bar in round 1 without regression; each took the fix rule (3 high findings) with one fix commit and its fixes.md"
  - "Phase-closing make test under the run guard and the added-line scan, both green"

key-files:
  modified:
    - .planning/judge/REJUDGE.md
    - .planning/judge/facts.json
    - .planning/judge/loops/38.json
    - .planning/judge/verdicts/38/
    - skills/ai-kit-cross-ai/SKILL.md
    - skills/ai-kit-gsd-curated-config/SKILL.md
    - skills/ai-kit-gsd-curated-config/references/runner.md

requirements-completed: [JDG-04]

executor: "orchestrator action in the main checkout (cross_ai false); judge lanes opencode router-env/my-referee-one and router-env/my-referee-two through the project runner, review mode, --host none"
---

# Phase 38 Plan 26: Loop 38 skill-judge loop and the phase-closing gate

Commits (pre-fold): round 1 records `86e801a`; round 1 fixes `af71f6f` (ai-kit-cross-ai) and `a44fcc5` (ai-kit-gsd-curated-config).

Status: Task 1 (live herdr sweep) SKIPPED for lack of consent; Tasks 2 and 3 complete.

## Live sweep check

SKIPPED, not run: the consent line `p38-live-sweep real-home: allowed` is absent from `tmp/run-2026-11-19/ledger.md`, and the orchestrator's brief for this run said not to run part (1). No herdr tab was opened, `live.py` was not written, and no real herdr was called (the judge lanes ran with `--host none`). `hosted timing: unverified (no real-home consent)`.

What stands in for it: the fake-herdr cases in the runner self-test from plans 38-20 and 38-21, which pass in the e2e shards of the final gate below. These are the `sweep-` cases: a dead run closed by id and complete label; a live run, another host's record, an unreadable record and a tab that matches the label prefix only, each left alone; `--host none`; the herdr-hang and close-hang caps; the automatic sweep before the lock; and `sweep-sigkill-e2e`, where a hosted lane's runner is killed by SIGKILL, its launcher group is ended, and `--sweep` closes exactly its tab and removes its run directory. The `host-lock-*` and `state-*` cases also count. They prove the logic against herdr's JSON shapes as the fake reproduces them. They do not prove a real herdr's answers, its live `tab_not_found` envelope or a real pane's timing.

Owner item: write the consent line and run Task 1 as the plan specifies, or decide that the fake-herdr proof is enough.

## Judged set

`tmp/judge-38/judged.py` (`judged self-check: ok`) uses base `93c229b^` (= `9f7a3c5`). Its SKILL.md diff is the same as the one from the merge base with unit 37 (`42bad13`), because the two commits in between touch only planning files. Changed: ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-spec-execute-superpowers. Fact-only: ai-kit-spec-review (its SKILL.md did not change). `judged-decisions.txt`:

- `ai-kit-gsd-curated-config judged`: the refusals rule changed (plan-set and plan-unset no longer refuse; apply checks each entry through the project's gsd-core, with named skip cases). The diff also adds a `router_confirmed` rule, a `workflow.cross_ai_timeout` replacement rule and new runner statuses.
- `ai-kit-spec-execute-superpowers not judged`: the Classify outcome `quota` is split into the names `quota_cycle` and `quota`, and the caller action stays the same (only a 75 with `retry_after_s` and `cycle` gets one wait). This is a name substitution in one bullet.

`skills.r1.txt`: ai-kit-cross-ai, ai-kit-gsd-curated-config. Pool: referee-one and referee-two (opencode); no native judge, no referee-three. Count 2 per skill; the pool check passed before and after the lanes.

## Loop 38 bar results

| Skill | Round | Worst percent | Grade | Bar | Findings (crit+imp+high) | decide.py row |
|---|---|---|---|---|---|---|
| ai-kit-cross-ai | 1 | 86.4 | B | met (loop 37 base 83.2) | 3 | fix -> af71f6f |
| ai-kit-gsd-curated-config | 1 | 85.6 | B | met (loop 37 base 88.0) | 3 | fix -> a44fcc5 |

`regression.py` lines (informational only; the tool's `bar_with_base` row decides):

- `ai-kit-cross-ai: lowest 86.4 (2 valid, 0 invalid), loop 37 r3 base 83.2, delta +3.2, regression: no`
- `ai-kit-gsd-curated-config: lowest 85.6 (2 valid, 0 invalid), loop 37 r1 base 88.0, delta -2.4, regression: no`

Outcome for both skills: `bar met, then fixed under the no-rejudge rule`. Both keep their round 1 records; there is no round 2.

Fixed findings, one line each (the full text is in each `fixes.md`):

- ai-kit-cross-ai referee-one D8-1 (SKILL.md:43): the skill now says the preflight strips a variant suffix (opencode `#<variant>`): it checks the base id and never validates the suffix.
- ai-kit-cross-ai referee-one D8-2 (SKILL.md:138): the idle watchdog ends an attempt, not the call, and the final status line decides the result (124, a waitable 75, a bare 75 or 69).
- ai-kit-cross-ai referee-two D8-1 (SKILL.md:275): the hard-tier wait takes exactly one form, either a confirmed one-shot job or the print-and-stop handoff, never both.
- ai-kit-gsd-curated-config referee-one D8-1 (SKILL.md:168): re-run the dry run right before apply and compare its rows, because apply recomputes its writes from the live config. The skill names the window a concurrent edit still has. Binding apply to the preview in code is not done (see Open items).
- ai-kit-gsd-curated-config referee-one D8-3 (SKILL.md:354): tuning questions go to `gsd-config --advanced` and integration questions to `gsd-config --integrations`.
- ai-kit-gsd-curated-config referee-one D8-4 (runner.md:32, SKILL.md:234-236): workspace-write is described as a Codex sandbox mode, not a fixed allowlist. That the owner's Codex config can change the writable roots is flagged as not verified here.

## Loop 38 facts for the verifier

- Judges: referee-one `opencode:router-env/my-referee-one` configured; referee-two `opencode:router-env/my-referee-two` configured. Both probes were usable: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=21s out=2227 tree=clean ... attempts=1 cycles=0` and `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=23s out=2211 tree=clean ... attempts=1 cycles=0`. Both print `cross-ai: setting host=none applied`.
- Round 1 lanes (4): every one ended `AIKIT-XAI status=ok cli=opencode exit=0 cli_rc=0 tree=clean attempts=1 cycles=0`. referee-one took 331 s on cross-ai and 498 s on curated-config; referee-two took 403 s and 90 s. No lane failed or was rejected, nothing was re-run and no substitute judge was used.
- `verdict_facts.py` verdicts (percent, grade, critical, high): cross-ai 86.4 B (0, 2) and 89.6 B (0, 1); curated-config 85.6 B (0, 3) and 93.6 A (0, 0).
- `check.py` (`--require-current`) exited 0 before the fix commits, with the digest current for both skills.
- `gate.sh` (`judge_loop.py check .planning/judge --gate`) exited 0 before the fix commits.
- The closing `closing.sh` (`judge_loop.py check .planning/judge`) exited 0 after the fix commits. Both skills have a `loop 38 round 1` line with `bar met` and `digest stale` (stale by design). The notes are `stale digest` for both skills plus the eight skills that were stale before the loop; there is no facts-drift line.
- `make check-dogfood` before the records commit: `check-dogfood: ok` (no-write guard: 3 attempted, 3 executed, 0 skipped).
- `stale_after.py`: `stale ok` (before the fix commits). `evals_gate.py`: `evals gate: ok`. `tests.test_skill_evals_shape`: 1/1 before dispatch. `decide.py --self-check`: `decide self-check: ok`. `loop_record_check.py`: `loop record: ok`. `bar_table.py`: `regex self-check: ok`, `unmet.txt: 0 skill(s) not met`.

## Stale-digest notes

- Stale before the loop: ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss, ai-kit-session-wake, ai-kit-spec-config, ai-kit-spec-execute-superpowers, ai-kit-spec-review, ai-kit-spec-review-checklist, ai-kit-usage-metrics, jev-fast-decision.
- Stale by design after their fix commits (`tmp/judge-38/intentional-stale.txt`): ai-kit-cross-ai, ai-kit-gsd-curated-config. `report` was not re-run after a fix commit.

## Mtime check of the listed paths

`mtime check of the listed paths: unchanged`. The snapshot of the 5 files present was taken before the probes and compared after the round 1 lanes.

## Final gate

- `python3 tmp/run-2026-11-19/orch-guard.py tmp/run-2026-11-19/make-test-c38-9.log make test` ran after the last fix commit, with MemAvailable at 13994 MB and `/tmp` at 38 %. Guard: `exit 0 peak_runner_procs 8 killed: no`. Result lines: unit `178/178 modules passed`, unit-uv `3/3 modules passed`, integration `9/9 modules passed`, e2e `29/29 modules passed`, `tests/test_install.sh` `48 passed, 0 failed`, arch `2/2 modules passed`.
- `python3 tmp/judge-38/added_line_scan.py`: `scan self-check: ok`, `scan: base 42bad139bb (merge base with gsd/phase-37-shared-runner-options-and-session-ids)`, `scan: ok (no new line naming grok)`. The captures under `tests/fixtures/cli_help` are exempt.

## Deviations and notes

- Task 1 was skipped for lack of consent (see above).
- `lanes.py` passes `--host none` to every lane, so no judge lane can be hosted in the owner's herdr and the automatic sweep makes no herdr call.
- `make test` ran with the command and log path from the orchestrator's brief (`orch-guard.py tmp/run-2026-11-19/make-test-c38-9.log make test`), not through the plan's `tmp/judge-38/make_test.sh`.
- `relaunch_one.py` was copied but not needed.

## Open items

- Owner: the live herdr sweep proof (Task 1) waits for the consent line or the owner's decision.
- ai-kit-gsd-curated-config: `apply` does not bind its writes to the approved dry-run preview. The skill now tells the agent to re-run the dry run and compare; a check in code would close the gap.
- The fixed-allowlist wording for codex workspace-write is still present outside this loop's judged files: `skills/ai-kit-spec-review/references/cross-ai.mjs:61`, `skills/ai-kit-spec-review/references/cli-profiles/codex.md:33` and `skills/ai-kit-spec-execute-superpowers/references/design-notes.md:79`.
