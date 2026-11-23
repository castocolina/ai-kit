---
phase: 39-lane-capability-blocks-and-lens-skills
plan: 19
subsystem: gate
tags: [closing-gate, make-test, e2e-docker, grok-scan, real-config-audit]

requires: [39-18]
provides:
  - "The four dated 2026-11-23 notes present (REQUIREMENTS.md REV-03, REV-04, REV-05; ROADMAP.md Phase 39)"
  - "make test green once at the end of the phase for the pinned candidate, plus every other gate, the clean-room e2e-docker included"
  - "No line added by unit 39 names grok; no mtime change observed on the six listed paths during the gate"

key-files:
  modified:
    - tests/cross_ai_selftest.py
    - tests/test_lens_delivery.py
    - tests/test_prompt_guard.py
    - tests/test_runner_preview.py

requirements-completed: [REV-03, REV-04, REV-05, JDG-04]

executor: "orchestrator action in the main checkout (cross_ai false)"
---

# Phase 39 Plan 19: Closing gate

Precondition: 39-18-SUMMARY.md gives every judged skill a met bar. cross-ai and curated-config were fixed under the no-rejudge rule. spec-review and spec-config met the bar by grade in round 3, with their open findings recorded for the owner. The orchestrator accepted that as complete. The plan-add commit `d06064a` exists, and the tree was clean.

## Repair and restart

The first candidate `3126b76` passed every gate but `make e2e-docker` (exit 2): in the container, `test-unit-core` reported `182/185 modules passed`. `tests.test_lens_delivery`, `tests.test_prompt_guard` and `tests.test_runner_preview` failed with `no real node executable on PATH` / `node not on PATH`, because the clean-room image has no node by design. Plans 39-06, 39-07 and 39-11 require a missing node to fail on a checkout, never to skip silently.

Orchestrator decision: skip only in the clean room. Commit `7c02d64` (`fix(39): node-gated tests skip only in the clean-room image`, tests only) adds `require_real_node` to `tests/cross_ai_selftest.py`. A missing node skips only when the repo root has no `.git` (the build context drops it, `.dockerignore:4`, and `run.sh` runs `git init` only after `make test`), and fails everywhere else. It is used at the four sites (`TestRunnerSync.setUp` and `test_lens_notes_closed_and_disjoint` in test_lens_delivery, `TestRefusalDisjoint.setUp` in test_prompt_guard, `TestLaneFactsFromTheRunner.setUp` in test_runner_preview). The three existing `skipUnless` sites of test_runner_preview are unchanged.

`TestRequireRealNode` in test_runner_preview pins the behaviour with a synthetic PATH and repo root:
- no node with a `.git` directory fails;
- no node with a `.git` worktree file fails;
- no node with no `.git` skips.

A verbose host run of the three modules showed 57 tests ok, with no skipped test. Both tasks then restarted on candidate `7c02d64`.

## Dated notes

- `.planning/REQUIREMENTS.md:288`: `*(amended 2026-11-23, 39-SPEC "Live facts added 2026-11-23": lens text is not inlined by Python any more; ...)*`
- `.planning/REQUIREMENTS.md:301`: `*(amended 2026-11-23, 39-SPEC "Live facts added 2026-11-23": the capabilities line is the runner's stderr line cross-ai: capabilities <JSON>, ...)*`
- `.planning/REQUIREMENTS.md:307`: `*(amended 2026-11-23, 39-SPEC "Live facts added 2026-11-23": the table also picks the MCP servers a lane gets: ...)*`
- `.planning/ROADMAP.md:977`: `*(amended 2026-11-23, 39-SPEC "Live facts added 2026-11-23": Phase 37 shipped the runner's skill and MCP flags, ...)*`

## Final gate

- Candidate SHA `7c02d6478a89c3a263a484bb9d79aa270e6c6efa`. HEAD and a clean tracked tree matched it before and after every gate. No memory floor was applied (owner decision 2026-11-23); the orch-guard watchdog is the protection. /tmp stayed at 55-58 % and /var/home at 65 %.
- `run_gate.py` (candidate pin, `running-<sha>` claim, `UV_OFFLINE=1`) printed guard `exit 0 peak_runner_procs 8 killed: no`, `head-after ok`, `guard-rc 0`.
- `check_gate.py` printed `gate self-check: ok`, `gate: ok 7c02d6478a89c3a263a484bb9d79aa270e6c6efa`. Tier lines: unit `185/185 modules passed`, unit-uv `3/3`, integration `9/9`, e2e `29/29`, arch `2/2`. Installer: `48 passed, 0 failed`.
- `survivors.py`: `survivors: none` (no matching survivors detected). The scratch TMPDIR was removed.

| Gate (one at a time, under orch-guard) | Exit | Count line |
|---|---|---|
| make test (run_gate.py) | 0 | 185/185, 3/3, 9/9, 29/29, 2/2; 48 passed, 0 failed |
| make lint | 0 | shellcheck, py-compile Passed |
| make validate | 0 | ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest core and wizard, check-dogfood Passed |
| make test-unit | 0 | 185/185, 3/3 |
| make e2e-test | 0 | 29/29; 48 passed, 0 failed |
| make e2e-test-modules | 0 | 29/29 (matrix 35 tests in 158.0 s) |
| make e2e-test-install | 0 | 48 passed, 0 failed |
| python3 -m unittest tests.test_wizard_pty | 0 | Ran 14 tests, OK |
| make e2e-docker (podman, `git archive HEAD` plus `.claude/gsd-core`) | 0 | 185/185, 3/3, 9/9, 29/29, 48 passed 0 failed, 2/2, lint Passed, `==> ai-kit clean-room E2E: PASS` |
| edge_floor.py check 39-SPEC.md | 0 | ok true, 68 floor rows, 68 table rows, none missing |
| make check-dogfood | 0 | `check-dogfood: ok` (stale-digest notes only; spec-review and spec-config current) |

The logs and their last 20 lines are in `tmp/run-2026-11-19/gates-39/<name>.log` and the guard logs; the first candidate's logs are in `gates-39/run-3126b76/`. Every gate ran in its own process group, with the group ids in `gates-39/pgids.txt`. `final_check.py` found all ten groups ended. It saw 0 processes of this run; the 2 matching processes were a pi referee-one review lane of this checkout that started after the gates, not started by this plan, and were left alone. The six running podman containers belong to other projects.

## Grok scan

`scan self-check: ok`, `scan: base 6ade14b2fe (merge base with gsd/phase-38.1-runner-error-classification-and-retry-policy-inserted)`, `scan: ok (no new line naming grok)`. The scan covers added lines outside `.planning/` and `tests/fixtures/cli_help` only.

## Real-config audit

- During the gate: `mtime check of the listed paths: unchanged`. The snapshot (5 files present) was taken before `make test`, and the compare ran after the final `make check-dogfood`.
- Since the phase start: `phase mtimes: changed (informational)`. `.claude/settings.json` (2026-11-23 10:58:51, cause unknown) and `.cursor/cli-config.json` (14:05:34, inside the loop 39 round 1 lane window; the lanes were opencode only; cause unknown) show `CHANGED after the phase start`. `.config/opencode/opencode.jsonc`, `.codex/config.toml` and `.pi/agent/settings.json` are unchanged; `.config/opencode/opencode.json` is absent. This is evidence for the owner, not a gate failure, and nothing was reverted.

## Owner items

- Install and live re-check: not run in this plan. It is pending and needs the owner's ship step per AGENTS.md; the installer suite in make test is not that check.
- D-18 live probe (path reading and shell use on claude, opencode and pi): not run, no consent line. No real-home probe ran.
- `~/.claude/settings.json` changed at 10:58:51 on 2026-11-23, cause unknown. `~/.cursor/cli-config.json` changed at 14:05:34, cause unknown.
- The accepted limit of 39-17 and the cap-* cases' shard times are recorded in 39-17-SUMMARY.md.
- Loop 39 open findings after round 3: ai-kit-spec-config 5 and ai-kit-spec-review 4 (listed in 39-18-SUMMARY.md). The spec-review file-size finding needs a SPEC amendment (39-SPEC.md:670 pins the SKILL.md tables).
- Node in the clean-room image: the container now skips the node-dependent checks, as the older node modules do. Adding node to the image would run them there, with unknown results; that stays the owner's choice.

## Deviations

- The repair commit `7c02d64` restarted both tasks on the new SHA, as the plan says. Beyond the plan's single `make test`, the orchestrator's full gate list ran.
- `mem_check.py` printed `mem: ok` before the first candidate's run; it was not a precondition (owner decision 2026-11-23).
