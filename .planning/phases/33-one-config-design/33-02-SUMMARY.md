---
phase: 33-one-config-design
plan: 02
subsystem: infra
tags: [toml, cross-ai-runner, retry-config, self-test, node-builtins]

# Dependency graph
requires: []
provides:
  - "Runner reads [runner.retry] per key from the project .aikit/config.toml, then the user config.toml, then CONFIG.retry, then RETRY_DEFAULTS"
  - "Node built-in TOML-subset reader for the runner (runner tables parsed, [[lanes.*]] and other tables opaque; collisions refused in either order)"
  - "One user-dir rule in the runner (aiKitConfigDir: absolute XDG_CONFIG_HOME, else absolute HOME, else none; no ambient home lookup)"
affects: [33-04 (GSD block and user cross-ai.json migration), 33-05 (trust), 33-06 (docs)]

# Actuals (#2632): chars/4 over the realized diff (base a0918f9 .. HEAD)
actuals:
  tokens: 28367
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-key source cascade (project, user, CONFIG, defaults) with validateRetryKey on every value"
    - "Quote-aware TOML header matching shared by the reader and the value scanner (splitTomlName, scanBasicString)"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - .planning/scripts/cross-ai.mjs
    - tests/fixtures/cross_ai_selftest_secs.json
    - tools/run_unittest_parallel.py

key-decisions:
  - "Tasks 1 and 2 ship in one commit (f03a46f): the Task 1 template alone leaves the old GSD-sourced retry cases red, and the commit hook runs the shards."
  - "The scope key is the active GSD scope path (retryScope); the scope table wins over [runner.retry] for that scope only."
  - "A table/key collision in either order, an unknown header name and an out-of-subset value skip the whole file with one notice; the next source fills the keys."
  - "aiKitConfigDir returns null when neither XDG_CONFIG_HOME nor HOME is absolute; the user layer is then skipped with one notice, never read from the working folder or the account home."

patterns-established:
  - "Self-test fixtures write config.toml through writeCaseFile; pure cases call parseTomlSubset, splitTomlName and aiKitConfigDir directly"

requirements-completed: []  # Plan frontmatter lists CFG-03, CFG-06, CFG-01; partially covered here (read side only). Not marked complete: migration (Plan 04) and the no-foreign-key and no-GSD proofs remain. See Issues Encountered.

coverage:
  - id: D1
    description: "Runner reads [runner.retry] per key from project and user config.toml, with the active scope table, CONFIG and defaults as later sources"
    verification:
      - kind: other
        ref: "tests/cross_ai_selftest.py run_cases: retry-config-project, retry-config-user, retry-config-per-key, retry-config-workstream, retry-config-scope-active-only, retry-config-bracket-scope, retry-config-precedence"
        status: pass
    human_judgment: false
  - id: D2
    description: "TOML-subset reader: supported values, CRLF, quoted header names, refusals and table/key collisions in both orders, invalid UTF-8 skipped with one notice"
    verification:
      - kind: other
        ref: "tests/cross_ai_selftest.py run_cases: pure-toml-subset-values, pure-toml-subset-crlf, pure-toml-subset-refusals, pure-toml-subset-bracket-names, retry-config-invalid-utf8, retry-config-out-of-subset"
        status: pass
    human_judgment: false
  - id: D3
    description: "The runner's user-dir rule has no ambient home lookup and skips the user layer when HOME is not absolute"
    verification:
      - kind: other
        ref: "tests/cross_ai_selftest.py run_cases: pure-config-dir-rule, pure-retry-user-config-without-home"
        status: pass
    human_judgment: false

# Metrics
duration: unknown (plan start time was not recorded)
completed: 2026-11-15
status: complete
---

# Phase 33: One config design, Plan 02 Summary

**Runner reads its retry tuning per key from `[runner.retry]` in the project and user `config.toml` through a node built-in TOML-subset reader, with 449 self-test cases (439 before)**

## Performance

- **Duration:** unknown (the plan start time was not recorded)
- **Tasks:** 3 completed (Tasks 1 and 2 in one commit, Task 3 in its own)
- **Files modified:** 4

## Accomplishments

- The retry cascade reads `.aikit/config.toml` and `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml`, then `CONFIG.retry`, then `RETRY_DEFAULTS`, per key with today's validation.
- A scope table `[runner.retry.scopes."<scope>"]` wins over `[runner.retry]` for the active GSD scope only; scope names may hold brackets and quotes (`p[1]`).
- The GSD `workflow.cross_ai_retry` block and the user `cross-ai.json` are no longer read. Their migration is Plan 04.
- The TOML-subset reader fails closed: anything outside the subset, a table/key collision in either order, an unknown header name or invalid UTF-8 skips that file with one notice.
- `readConfigText` holds the existence, confinement, file-type, size and UTF-8 checks once for JSON and TOML.
- `aiKitConfigDir` follows the one resolver rule and never calls `os.homedir`.
- The 15 retry cases that pinned the old sources now write `config.toml`; 10 cases are new (`pure-toml-subset-values`, `pure-toml-subset-crlf`, `pure-toml-subset-refusals`, `pure-config-dir-rule`, `retry-config-invalid-utf8`, `retry-config-precedence`, `retry-config-scope-active-only`, `retry-config-out-of-subset`, `pure-toml-subset-bracket-names`, `retry-config-bracket-scope`).

## Task Commits

1. **Tasks 1 and 2: runner reads retry tuning from config.toml** - `f03a46f` (feat)
2. **Task 3: refresh self-test shard timings** - `72dfd70` (chore)

## Files Created/Modified

- `skills/ai-kit-spec-review/references/cross-ai.mjs` - template: TOML-subset reader, config reads, resolver rule, rewritten and new self-test cases
- `.planning/scripts/cross-ai.mjs` - dogfood copy, re-rendered by `ensure-runner` only (`make check-dogfood` renders it pristine)
- `tests/fixtures/cross_ai_selftest_secs.json` - per-case seconds for 449 cases
- `tools/run_unittest_parallel.py` - logic shard ceilings 22 -> 25 in `E2E_RECORDED_SECS` (runtime shards unchanged at 24)

## Decisions Made

- Tasks 1 and 2 share one commit because the Task 1 template alone fails the commit hook (old GSD-sourced cases stay red).
- The scratch driver `tmp/p33/02/scope.py` and the other `tmp/p33/02/` helpers are not committed.

## Deviations from Plan

**1. [Rule 3 - Blocking] Commit boundary: Tasks 1 and 2 in one commit**
- **Found during:** Task 1 commit.
- **Issue:** The Task 1 template alone leaves the old retry cases pinning GSD and `cross-ai.json`, so the staged self-test shards fail and the hook blocks the commit.
- **Fix:** Tasks 1 and 2 land as one buildable commit (`f03a46f`); Task 3's timings are a second commit (`72dfd70`).
- **Verification:** Commit hook `staged tests` passed 69/69 modules for `f03a46f` and `unit+arch` passed 127/127 for `72dfd70`.

**2. [Rule 1 - Bug] Synthetic `/home/u` fixture strings broke an existing arch test**
- **Found during:** The commit hook (`tests.test_ai_kit_spec`, `test_no_absolute_home_paths_or_header_state`).
- **Issue:** The new `pure-config-dir-rule` rows used `/home/u`, a banned fragment in the template.
- **Fix:** Synthetic HOME values changed to `/srv/u`; the rules tested are unchanged.
- **Verification:** `tests.test_ai_kit_spec` 693/693 ok.

**3. [Protocol] Plan-start ledger not written**
- **Issue:** The `gsd-plan-head-before-33-02` ledger was not written before the first commit; the Write tool refuses paths outside the worktree, and the ledger lives in the main repository's git metadata.
- **Fix:** `commits` is measured from the verified spawn base `a0918f9885798f088851de934cda86c1bbb0ae9c` (`git rev-list --count`), which the branch check asserted at start.

**Total deviations:** 3 (2 auto-fixed, 1 protocol). **Impact:** None on behaviour; the commit boundary is the only change to the plan's per-task commit shape.

## Issues Encountered

- **`make check-dogfood` exits 1 (pre-existing, not fixed here).** The runner-copy check passes (no "not pristine" line). The failures are judge-record problems for skills this plan does not touch (`ai-kit-usage-metrics`, `jev-fast-decision`, and others: stale digests and facts drift for `ai-kit-spec-review` and `ai-kit-spec-goal-prompt`). The extracted HEAD copy shows the same problem lines, so they predate this plan. Refreshing them is the loop-33 judging work (SPEC R11), not this plan's.
- **The no-write guard is skipped in the worktree** (no checkout-local `gsd-tools.cjs`, as the run rules describe); the check prints this as a warning.
- **Stale docs (out of this plan's files):** `skills/ai-kit-cross-ai/SKILL.md`, `skills/ai-kit-cross-ai/references/subprocess-quota-policy.md`, `skills/ai-kit-gsd-curated-config/SKILL.md` and `references/runner.md` still name `workflow.cross_ai_retry` and `cross-ai.json`. `tests/test_cross_ai_skill_text.py` pins some of that text, so it stays green until the docs plan changes both.
- **Requirements not marked complete:** CFG-03 and CFG-06 need Plan 04's migration and the no-foreign-key and no-GSD proofs; CFG-01 is not touched by this plan. `requirements-completed` is empty for that reason.
- **Parity test not present:** `tests/test_config_dir_parity.py` does not exist yet (it is Plan 03's). The runner copy of the rule is covered by `pure-config-dir-rule`.

## Verification (run in this worktree)

| Command | Result |
| --- | --- |
| `scope.py list` | `list cases: 449`, `list rc: 0` (HEAD: 439) |
| `scope.py cases retry-config-project,retry-config-caps-clamp,deadline-1800` | `cases rc: 0` |
| `scope.py mine` (27 cases) | `cases rc: 0` |
| `scope.py render` | `render rc: 0` |
| `scope.py shards` (8 shard modules) | `shards rc: 0`; logic 22 -> 25 updated |
| `scope.py dogfood` (`make check-dogfood`) | `dogfood rc: 2` (make's exit for the failed hook), pre-existing judge-record problems (see Issues); the runner-copy check passes |
| `unit.sh` (`test_cross_ai_skill_text`, `test_curated_config_script`, `test_check_dogfood`) | `unit rc: 0` (30 + 45 + 44 tests) |
| Commit hook, `f03a46f` | staged tests 69/69 modules passed |
| Commit hook, `72dfd70` | unit + arch 127/127 modules passed; self-test shards passed |

## Next Phase Readiness

- Plan 04 can migrate the GSD block and the user `cross-ai.json` into `[runner.retry]`; the reader and the scope rule it targets are in place (`retryScope`, `parseTomlSubset`).
- Open items above: the dogfood judge records (loop 33), the stale docs, and the requirement status for CFG-01, CFG-03 and CFG-06.

---
*Phase: 33-one-config-design*
*Completed: 2026-11-15*

## Self-Check: PASSED
