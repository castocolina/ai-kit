---
phase: 19-evaluation-on-claude
plan: 10
executor: orchestrator (live Claude Code session)
requirements-completed: [EVAL-01, EVAL-02, EVAL-03, APP-05]
product_commit: deb85b3
key-files:
  modified:
    - .planning/phases/19-evaluation-on-claude/19-SKILL-JUDGE.md (JUDGED_COMMIT, owner-review index)
    - tests/gsd_curated_eval.py, tests/test_gsd_curated_eval.py (d0edb4f gate fixes)
orchestrator_verify: ""
---

# Plan 19-10 Summary: phase gates and owner-review index

## Gates

First run, at 18:42-18:45:
- `make test`: rc 0.
- `make validate`: rc 2, from pyright: 4 errors in `tests/gsd_curated_eval.py` and `tests/test_gsd_curated_eval.py`.
- `make e2e-docker`: rc 2. `tests.test_gsd_curated_eval` failed in the container on `test_pin_entrypoint_on_real_v1_text` (`git show 7009d22^:...` exit 128).

Both were test-harness defects, not product defects. They were fixed in d0edb4f:
- The grader's Optional/annotation gaps are typed.
- The stale-module test assignment is annotated.
- The v1-history test skips when the blob is absent. The image copies the repo without `.git` per `.dockerignore`; the test still runs on the host.

No `fix(19-10)` product commit was needed. The re-run, at 18:47-18:51, passed every gate:
- `make test`: rc 0. Last lines: unit `42/42 modules passed`, integration `4/4 modules passed` and `8/8 modules passed`, e2e `45 passed, 0 failed`, arch `1/1 modules passed` (32 tests).
- `make validate`: rc 0. ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest (core) and unittest (wizard, uv) all `Passed`.
- `make e2e-docker`: rc 0 (podman). The container ran `42/42`, `4/4`, `8/8` and `1/1` modules passed, plus `45 passed, 0 failed`, and ended with `==> ai-kit clean-room E2E: PASS`.

## Gate failures

- none after the re-run. The first-run failures and their fix are above.

## Defect fixes

- none in the product. Test-harness fix: d0edb4f `test(19-10)`, with its regression check: the skip was verified in a `git archive` copy with no `.git`.

## Checks

- Committed-digest check: ai-kit-gsd-curated-config: digest 9cddf0a5892fba97 in commit 86ad793. The judged paths are clean. `digest --check` printed `digests ok` on 19-SKILL-JUDGE.md and on 19-PRESSURE-TESTS.md (both GREEN columns).
- Product revision: `product_commit: deb85b3` in 19-SMOKE.md and 19-PRESSURE-TESTS.md equals the last commit touching the product paths.
- Evidence fields: all seven fields are in 19-SKILL-JUDGE.md, with `JUDGED_COMMIT: 86ad793`. The four scenarios and `## What v1 got right or wrong` are in 19-PRESSURE-TESTS.md; `## Matrix` and `unchanged` are in 19-SMOKE.md. The home-path grep found nothing, and secret-scan exited 0.
- Owner-review index: 5 lines (4 `human_needed`, 1 `advisory`) under `## Phase decisions for owner review` in 19-SKILL-JUDGE.md.
- Snapshot: `snapshot --check tmp/plan10.before.json` printed `snapshot ok`.
- Leak check: the diff against `tmp/pids-19-10.before` printed nothing, and no `ai-kit-e2e` container is left.
- ROADMAP.md is untouched. Nothing was added for the withdrawn v1 isolation finding.

## Gate artifacts

- Ignored cache entries the gates may create (`__pycache__/`, `.ruff_cache/`) are filtered by the stray-file check. The excluded tool-managed trees are `.venv/` and `.codegraph/`.

## Timeline

- 18:42:46 baseline written
- 18:42:48 start make test
- 18:45:09 make test rc=0
- 18:45:09 start make validate
- 18:45:30 make validate rc=2
- 18:45:30 start make e2e-docker
- 18:45:58 make e2e-docker rc=2
- 18:47:19 gate re-run after the gate-fix commit
- 18:47:19 start make test
- 18:49:37 make test rc=0
- 18:49:37 start make validate
- 18:50:25 make validate rc=0
- 18:50:25 start make e2e-docker
- 18:51:08 make e2e-docker rc=0
