---
phase: 33-one-config-design
plan: 04
subsystem: infra
tags: [toml, cross-ai-runner, retry-config, migration, gsd-config, self-test]

# Dependency graph
requires:
  - "Plan 02: TOML-subset reader (parseTomlSubset, readTomlSubset), readConfigText, splitTomlName, the quote-aware header constants, retryScope, aiKitConfigDir"
provides:
  - "migrateRetrySources: one-time move of the GSD workflow.cross_ai_retry blocks (root, workstream, scopes) into .aikit/config.toml and of the user cross-ai.json into the user config.toml; the GSD file keeps every other byte; [runner] migrated_from records each source"
  - "mergeTomlTable and upsertTomlKeys: verified, re-read, atomic config.toml merge located by segment identity"
  - "writeFileAtomic, removeRetryBlock (JSON span scanner), tomlValueText"
affects: [33-06 (docs and proofs for the migration), 33-01 and 33-03 (CFG-04 writers), 33-07 (CFG-06)]

# Actuals (#2632): chars/4 over the realized diff (base b95c787 .. HEAD)
actuals:
  tokens: 34540
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Snapshot, merge, retire, record: each legacy source is merged into its target, retired only while it still equals the snapshot that was merged, and recorded last"
    - "Verified merge: splice, parse with parseTomlSubset, re-read before publishing (rebuild at most twice), publish atomically, re-read after publishing"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - .planning/scripts/cross-ai.mjs
    - tests/fixtures/cross_ai_selftest_secs.json
    - tools/run_unittest_parallel.py

key-decisions:
  - "A block's own line is removed whole; a last-position block takes the comma before it, so the GSD file stays valid JSON and every other byte is kept (verified by re-parse against the original object minus the block)."
  - "A scope table is keyed by the scope the runner resolves (retryScope), so a bracketed scope such as p[1] is written with JSON.stringify escapes that the quote-aware reader reads back."
  - "Concurrency has no lock (D-25): a source is retired only after its values are confirmed in the target and only while it equals its snapshot; a concurrent publish keeps the source for the next run."
  - "A migration error is logged as one notice and never stops the dispatch; every migration read goes through readConfigText, so invalid UTF-8 is never re-published."

patterns-established:
  - "Migration self-tests use pure cases with scratch folders under os.tmpdir(), a collected log, and patched fs.renameSync restored in finally"

requirements-completed: []  # Plan frontmatter lists CFG-03, CFG-04, CFG-06. Not marked complete: requirements.ready-ids reports all three blocked by sibling plans (see Issues Encountered).

coverage:
  - id: D1
    description: "The runner moves a root and a workstream/scope workflow.cross_ai_retry block into .aikit/config.toml and removes the block from the GSD file, keeping every other byte"
    verification:
      - kind: other
        ref: "tests/cross_ai_selftest.py run_cases: retry-migrate-project, retry-migrate-workstream, retry-migrate-keeps-bytes, retry-migrate-last-key, retry-migrate-symlink, retry-migrate-conflict, retry-migrate-quoted-header, retry-migrate-bracket-scope, pure-json-span-string-final, pure-toml-upsert-lines"
        status: pass
    human_judgment: false
  - id: D2
    description: "The user cross-ai.json moves into the user config.toml and is renamed cross-ai.json.migrated; a re-added block or JSON is ignored with a notice; a second run writes nothing"
    verification:
      - kind: other
        ref: "tests/cross_ai_selftest.py run_cases: retry-migrate-user-json, retry-migrate-readded, retry-migrate-second-run, retry-migrate-race, retry-migrate-user-json-changed"
        status: pass
    human_judgment: false
  - id: D3
    description: "Interruption, overlapping publish and changed sources keep every value in one of the two files and converge on the next run; invalid UTF-8 migrates nothing; a repository without .planning/ runs with no .planning created"
    verification:
      - kind: other
        ref: "tests/cross_ai_selftest.py run_cases: retry-migrate-interrupted, retry-migrate-overwritten, retry-migrate-snapshot-changed, retry-migrate-invalid-utf8, retry-migrate-invalid-utf8-target, no-planning-run"
        status: pass
    human_judgment: false

# Metrics
duration: unknown (plan start time was not recorded)
completed: 2026-11-15
status: complete
plan_head_before: b95c7871e550828c958264d1e7fc8575bcd4f2e2
plan_head_after: ec4b935043a4739058541fbe838fa83364f2a0eb
commits: 3
---

# Phase 33: One config design, Plan 04 Summary

**The runner migrates its legacy retry settings once: the GSD `workflow.cross_ai_retry` blocks and the user `cross-ai.json` move into `config.toml` through verified, re-read, atomic merges, and the GSD file keeps every other byte, with 21 new self-test cases (470 in total).**

## Performance

- **Duration:** unknown (the plan start time was not recorded)
- **Tasks:** 3 completed, each committed
- **Files modified:** 4

## Accomplishments

- `migrateRetrySources(cwd, env)` runs in `main` directly before `resolveRetry`, so the moved values apply on the same call.
- Project scope: the root block goes to `[runner.retry]`, a workstream or project block to `[runner.retry.scopes."<scope>"]`; the notice names the source, the table and that the project file is per checkout.
- User scope: `cross-ai.json` values go to the user `config.toml` `[runner.retry]`, and the file is renamed `cross-ai.json.migrated` (or `.migrated.<n>`), so its full text stays recoverable.
- `[runner] migrated_from` records each migrated source; a block or JSON file found again in a recorded source is ignored with a one-line notice.
- Conflicts: the target's own key wins and the conflicting key is named in a notice, never a value.
- Every migration read goes through `readConfigText` (strict UTF-8, confinement, type and size checks); a source or target that fails is left byte-equal with one notice.
- The GSD file is rewritten through a temp file, fsync and rename beside its real path, so a symlink stays a link and its mode is kept.

## Task Commits

1. **Task 1: a root GSD block moves into the project config.toml** - `71910e5` (feat). Also contains the user-JSON branch of `migrateRetrySources`, see Deviations.
2. **Task 2: self-test cases for the user JSON, re-added sources, scopes, byte-keeping, symlinks, conflicts, quoted and bracketed headers, invalid UTF-8, no-`.planning` run** - `44c0e01` (test)
3. **Task 3: interruption, race, overlapping publish and changed-source cases; refreshed timings** - `ec4b935` (test)

## Files Created/Modified

- `skills/ai-kit-spec-review/references/cross-ai.mjs` - template: `writeFileAtomic`, `findJsonKeySpan`, `removeRetryBlock`, `tomlValueText`, `upsertTomlKeys`, `mergeTomlTable`, `migrateRetrySources`, the scratch helpers `migrationScratch`, `collectLog`, `patchRenameOnce`, and 21 new self-test cases; the comments named by the plan.
- `.planning/scripts/cross-ai.mjs` - dogfood copy, re-rendered by `ensure-runner` only.
- `tests/fixtures/cross_ai_selftest_secs.json` - timings for 470 cases (`--record-times`).
- `tools/run_unittest_parallel.py` - logic shard ceilings 25 -> 24 for `logic_1..4` (the only `update` lines the shard run printed).

## Decisions Made

- The migration keeps the plan's order (merge, retire, record); the accepted residuals are recorded in T-33-11 and T-33-13, not reopened.
- The user cross-ai.json is renamed even when it holds no `cross_ai_retry` key (the plan's step is unconditional on content); its text stays in `cross-ai.json.migrated`.

## Deviations from Plan

**1. [Rule 3 - Blocking, plan split] The user-JSON branch landed in the Task 1 commit**
- **Found during:** Task 1 (writing `migrateRetrySources` as one function).
- **Issue:** The plan puts the user part in Task 2, but the function is one unit: leaving its user part out of Task 1 would have shipped a half-written migrator.
- **Fix:** The user branch is in `71910e5`. Task 2 (`44c0e01`) holds the user, scope, byte and invalid-UTF-8 cases, and Task 3 (`ec4b935`) holds the race and changed-source cases.
- **Verification:** Task 1's verify (`retry-migrate-project`, `retry-config-project`, `deadline-1800`) passed on `71910e5`; the commit hook passed for every commit (70/70 staged modules for the first two, 136/136 unit and arch for `ec4b935`).

**2. [Protocol] Plan-start ledger not written; duration not recorded**
- **Issue:** `gsd-plan-head-before-33-04` was not written before the first commit, and the start time was not captured.
- **Fix:** `commits` is measured with `git rev-list --count b95c787..HEAD` (3) from the spawn base the branch check asserted; `plan_head_before` is that base.

**3. [Tooling] Scratch driver `tmp/p33/04/scope.py` (not committed)**
- Written from the 33-02 description. `mine` runs the names the template defines and prints the absent ones, so the Task 2 verify ran before the Task 3 names existed; at Task 3 `mine` had no absent names.

**Total deviations:** 3 (1 blocking plan split, 2 protocol or tooling). **Impact:** None on behaviour; commit boundaries differ from the plan's split for the user branch only.

## Authentication Gates

None.

## Verification (run in this worktree)

| Command | Result |
| --- | --- |
| `scope.py render` (after each task) | `render rc: 0` |
| `scope.py cases retry-migrate-project,retry-config-project,deadline-1800` (Task 1) | `cases rc: 0` (exit 0) |
| `scope.py mine` (Task 2; 36 cases, 5 Task 3 names absent) | `cases rc: 0` (exit 0) |
| `scope.py mine` (Task 3; 41 cases, none absent) | `cases rc: 0` (exit 0) |
| `scope.py list` | `list cases: 470`, `list missing from template: none`, `list rc: 0` |
| `cross_ai_selftest.py --record-times` | `recorded 470 cases` (exit 0) |
| `scope.py shards` (first run; four `update` lines printed) | `shards rc: 0`; `logic_1..4` 25 -> 24 applied |
| `scope.py shards` (after the edit) | `shards rc: 0`, no `update` line |
| `scope.py dogfood` | `dogfood rc: 2` (make's exit); `runner copy pristine: True`; problem lines below |
| `run_unittest_parallel.py tests.test_cross_ai_skill_text tests.test_curated_config_script tests.test_check_dogfood tests.test_cross_ai_runner_e2e` | `4/4 modules passed` (exit 0) |
| Commit hook, Task 3 | unit+arch 136/136 (shared test machinery staged), staged tests passed |

`scope.py dogfood` problem lines (none is a `not pristine` line):
- worktree-only: `flow config not checked`, `lens wiring not checked`, `edge floors not checked` (no checkout-local gsd-core), and the no-write guard skipped for 3 cases (`gsd-tools resolves outside the checkout-local ...`, `no node or checkout-local gsd-tools.cjs`).
- judge records, stale digest or facts drift: `ai-kit-usage-metrics`, `jev-fast-decision`, `ai-kit-spec-config`, `ai-kit-spec-review` (stale digest and facts drift), `ai-kit-spec-review-checklist`, `ai-kit-session-wake`, `ai-kit-spec-execute-superpowers`, `ai-kit-gsd-spec-discuss`, `ai-kit-spec-goal-prompt` (facts drift). These predate this plan (33-02 reported the same class); the `ai-kit-spec-review` digest also sits over this template, so it changes again with this plan. Judge records are not edited here (loop 33, SPEC R11).

## Known Stubs

None.

## Threat Flags

None beyond the plan's register (T-33-10 to T-33-13 are the migration rows).

## Issues Encountered

- **Requirements stay open.** `requirements.ready-ids` reports CFG-03, CFG-04 and CFG-06 as blocked: CFG-03 and CFG-06 are declared by 33-06, CFG-04 by 33-01 and 33-03, CFG-06 also by 33-07. Nothing was marked; `REQUIREMENTS.md` is unchanged.
- **Stale docs remain** (33-02's list: `ai-kit-cross-ai`, `subprocess-quota-policy.md`, `ai-kit-gsd-curated-config`, `runner.md`), owned by 33-06.
- **Observation:** the project-layer notice for an invalid `.aikit/config.toml` names the first scoped GSD file even when that file holds no block (the plan's literal step). Harmless, but noisier than needed.
- **Residual, accepted (T-33-13):** a writer that read the target before our publish and renames after our post-publish re-read still replaces our values after our source is retired; `/gsd-secure-phase` reviews the row.

## Next Phase Readiness

- The runner side of the migration (CFG-03, CFG-06 runner part) is in place; the docs and the remaining no-foreign-key proofs are 33-06.
- CFG-04's runner side is atomic and lossless (`writeFileAtomic`, byte-keeping tests); the Python writers are 33-01 and 33-03.

---
*Phase: 33-one-config-design*
*Completed: 2026-11-15*

## Self-Check: PASSED
