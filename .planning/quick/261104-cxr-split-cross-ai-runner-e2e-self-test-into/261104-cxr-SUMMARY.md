---
phase: quick-261104-cxr
plan: 01
subsystem: test-infrastructure
status: complete
tags: [cross-ai, e2e, sharding, self-test, push-timing]
requires: []
provides:
  - "cross-ai.mjs --self-test-list with per-case logic or runtime kind"
  - "eight self-test shard e2e modules, generated from the template listing"
  - "tests/cross_ai_selftest.py shared harness and timing fixture"
affects:
  - tests/test_cross_ai_runner_e2e.py
  - tools/run_unittest_parallel.py
  - AGENTS.md
  - README.md
key-files:
  created:
    - tests/cross_ai_selftest.py
    - tests/fixtures/cross_ai_selftest_secs.json
    - tests/test_cross_ai_selftest_logic_{1..4}_e2e.py
    - tests/test_cross_ai_selftest_runtime_{1..4}_e2e.py
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - .planning/scripts/cross-ai.mjs
    - tests/test_cross_ai_runner_e2e.py
    - tools/run_unittest_parallel.py
    - tests/test_run_unittest_parallel.py
    - tests/test_staged_commit_e2e.py
    - tests/test_staged_mapper.py
    - Makefile
    - .pre-commit-config.yaml
    - AGENTS.md
    - README.md
commits:
  - "827ff30 feat(cross-ai): tag self-test cases logic or runtime and list them"
  - "dfbf3c5 test(cross-ai): split the runner self-test into timed logic and runtime shards"
metrics:
  tasks: 3
  commits: 2
  duration: n/a
---

# Quick 261104-cxr: Split cross-AI runner e2e self-test into shards

The runner template's 438-case self-test, previously run twice by `tests/test_cross_ai_runner_e2e.py` (recorded 366 s), now runs as eight shard modules of about 23-26 s each. Membership comes from the template's own `--self-test-list`; no case was removed or weakened.

## Results

- Kinds: 392 `logic`, 46 `runtime`. Every case lands in exactly one shard (ShardCoverageTest green).
- Shard times, from the timed e2e group run (`tmp/quick-xai-split/e2e_group.txt`):
  - logic_1 25.5 s, logic_2 25.3 s, logic_3 25.2 s, logic_4 25.5 s
  - runtime_1 23.8 s, runtime_2 24.1 s, runtime_3 23.4 s, runtime_4 22.7 s
- `tests.test_cross_ai_runner_e2e`: 366 s before, 17.6 s after (smoke run of a rendered copy plus the interrupt, load-factor, stop, dispatch and classify tests).
- `tests.test_precompact_shims_e2e`: 57.4 s (out of scope, reported only).
- E2E group wall time: 58 s (first run), 57 s (second run under the new submit order). Both under the 60 s budget.
- No cross-AI e2e module is recorded above 60 s; each shard is at most about 26 s.
- Push timing (`tmp/quick-xai-split/prepush.txt`, verdict pass): test hooks 55.4 s against the 60 s limit (unit and arch 34.4 s, wizard 21.0 s); pyright 9.6 s, vulture 1.9 s, check-dogfood 0.5 s, deferred-e2e 0.0 s (no push range, no module over the commit budget), push-worst 67.3 s. Before this phase: test hooks 183.9 s, push-worst 420.2 s.

## Task Commits

1. `827ff30` feat(cross-ai): tag self-test cases logic or runtime and list them
2. `dfbf3c5` test(cross-ai): split the runner self-test into timed logic and runtime shards

## Verification

- ruff, pyright, vulture pass; `pylint tools/run_unittest_parallel.py` 10.00/10.
- Nine cross-AI e2e modules pass (`=== ...: ok`).
- tests.test_gate_scope, tests.test_arch, tests.test_staged_mapper, tests.test_run_unittest_parallel pass.
- tests.test_staged_commit_e2e passes (13 tests).
- `make check-dogfood` passes (see deviation 3).
- staged_mapper selects all eight shards plus tests.test_cross_ai_runner_e2e for the template.
- ensure-runner: first run re-rendered, second run `keep-pristine`; template and rendered copy diffs mirror each other.

## Deviations from Plan

1. **[Process] Tool guard split commands.** The worktree guard refused several compound Bash commands as too complex to verify. They were split into plain commands; no command was changed in meaning.
2. **[Process] Real-home guard missed once.** The first staged-commit e2e run was started without `AI_KIT_REFUSE_REAL_HOME=1`. It passed; it was rerun with the variable set and passed again (13 tests).
3. **[Process] Accidental duplicate runs.** I started two extra copies by mistake: a duplicate of the runner-tests run (`tests.test_run_unittest_parallel` and peers, which completed exit 0 and does not change the result), and a duplicate `tools/time_prepush.py` that overlapped the first pre-push timing run. That first timing run was contaminated, so I stopped it and reran the timing once, cleanly. Only the clean run's figures are recorded in the docs.
4. **[Environment, pre-existing] check-dogfood warning.** `make check-dogfood` passes, but prints: the apply no-write guard was skipped because the checkout-local gsd-core is 1.20.0 and the guard needs 1.16 or 1.17, so apply writes to the live project are unguarded until it runs. Not caused by this change; not fixed here.
5. **[Content] Push-worst changed meaning.** The old 420.2 s worst case was dominated by deferred-e2e (352.4 s). After the split no e2e module is over the commit budget, so deferred-e2e is 0.0 s and push-worst is 67.3 s. AGENTS.md and README.md say so.

## Deferred Issues

None from this plan's tasks.

## Jev Calls

None.

## Self-Check: PASSED

- Commit 827ff30 and dfbf3c5 exist on branch worktree-agent-a5827e18563eeab93.
- Working tree clean after commit 2; this SUMMARY and the tmp/ and .claude/ tooling are untracked and not committed, per the constraints.
