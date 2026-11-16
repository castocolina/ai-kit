---
phase: 33-one-config-design
plan: 03
subsystem: infra
tags: [config-dir, parity-test, atomic-write, status-line, secrets]

# Dependency graph
requires:
  - "33-02: runner aiKitConfigDir (the node copy of the user-dir rule)"
provides:
  - "One user-dir rule in config_io, local_secrets, jev_review, tools/common_config (cfg_ai_kit_dir) and setup.resolve_paths"
  - "tests/test_config_dir_parity.py: every copy on the same cases, ambient home lookups failing"
  - "Status-line recovery publishes the regenerated file by os.replace (live file never written in place)"
affects: [33-04, 33-05, 33-06]

# Actuals (#2632): chars/4 over the realized diff (base b95c787 .. HEAD)
actuals:
  tokens: 13161
  tasks: 3
  commits: 2
plan_head_before: b95c7871e550828c958264d1e7fc8575bcd4f2e2
plan_head_after: b2730cdd1e3bd41bb8359493961a20d4cbf14192

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One user-dir rule: absolute XDG_CONFIG_HOME (trimmed), else absolute HOME/.config, else no dir; HOME from env only"
    - "Parity test runs each copy alone; the node copy runs with os.homedir throwing"

key-files:
  created:
    - tests/test_config_dir_parity.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
    - skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py
    - skills/jev-fast-decision/scripts/jev_review.py
    - tools/common_config.py
    - tools/setup.py
    - tests/test_setup.py
    - tests/test_ai_kit_spec.py
    - tests/test_external_segments.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "config_io, local_secrets, jev_review, common_config and setup.resolve_paths return no user dir for an unset, empty or relative HOME; no copy calls an ambient home lookup."
  - "local_secrets.secrets_env_path returns None when there is no absolute home; load_secret returns None."
  - "setup.resolve_paths exits with a message when there is no absolute home; opencode's folder keeps its own rule."
  - "cfg_config_path and cfg_segments_dir return an empty string with no absolute home, so defaults apply."

patterns-established:
  - "Copies that cannot share code are pinned by tests/test_config_dir_parity.py CASES (shared table, C1-3 HOME-unset and HOME-empty rows)."

requirements-completed: []  # Not marked by this executor. CFG-01: the resolver rule and its parity acceptance (SPEC R10) are met. CFG-04: only the status-line recovery is atomic here; the roster writer and migrations belong to later plans. Orchestrator to decide.

coverage:
  - id: D1
    description: "Every user-dir copy resolves by one rule, including HOME unset and empty, with ambient lookups failing"
    verification:
      - kind: other
        ref: "tests/test_config_dir_parity.py (CASES; test_config_io_copy, test_local_secrets_copy, test_jev_review_copy, test_common_config_copy, test_setup_resolve_paths_follows_common_config, test_runner_copy)"
        status: pass
    human_judgment: false
  - id: D2
    description: "local_secrets and jev_review read the same secrets.env under XDG_CONFIG_HOME; the parity test is non-vacuous"
    verification:
      - kind: other
        ref: "tests/test_config_dir_parity.py test_both_secret_readers_read_one_file, test_rule_check_is_not_vacuous"
        status: pass
    human_judgment: false
  - id: D3
    description: "Status-line recovery backs up, then publishes by os.replace; the live file is never written in place; an interrupted replace keeps it; mode kept"
    verification:
      - kind: other
        ref: "tests/test_setup.py TestRecoverIncompatibleConfig: test_live_file_is_never_written_in_place, test_interrupted_replace_keeps_the_live_file, test_recovery_keeps_the_file_mode"
        status: pass
    human_judgment: false

# Metrics
duration: unknown (plan start time was not recorded)
completed: 2026-11-15
status: complete
---

# Phase 33: One config design, Plan 03 Summary

**One user-dir rule (absolute XDG_CONFIG_HOME, else absolute HOME/.config, else none) in every Python copy and the runner, pinned by a parity test; status-line recovery replaces the live file by rename**

## Performance

- **Duration:** unknown (the plan start time was not recorded)
- **Tasks:** 3 completed (Task 1 in 4d62eeb; Tasks 2 and 3 in b2730cd)
- **Files modified:** 10 (1 created)

## Accomplishments

- `config_io.cfg_config_base`, `local_secrets.secrets_env_path`, `jev_review._config_dir` and `common_config.cfg_ai_kit_dir` share the rule. The `expanduser` fallbacks are gone; HOME comes from env only.
- `local_secrets` now honors `XDG_CONFIG_HOME`, so `load_secret` and `jev_review` read the same `secrets.env`.
- `tools/setup.resolve_paths` takes ai-kit's folder from `cfg_ai_kit_dir` and exits with a message when there is no absolute home.
- `tests/test_config_dir_parity.py` runs six copies (config_io, local_secrets, jev_review, common_config, setup.resolve_paths, and the runner's `aiKitConfigDir` through node) on 12 cases, including the C1-3 HOME-unset and HOME-empty rows, with `os.path.expanduser` patched to raise and node's `os.homedir` made to throw.
- `_recover_incompatible_config` keeps its `.bak` copy, writes the recipe to a temp file beside the live file with the old mode, and publishes it with `os.replace`. An interrupted replace leaves the live file unchanged and removes the temp file.

## Task Commits

1. **Task 1: one rule across the skill copies and the runner** - `4d62eeb` (feat)
2. **Tasks 2 and 3: status line resolves by the one rule; recovery replaces atomically** - `b2730cd` (feat)

## Files Created/Modified

- `tests/test_config_dir_parity.py` - created; parity table and per-copy tests
- `skills/ai-kit-spec-review/ai_kit_spec/config_io.py` - `cfg_config_base` rule, no ambient fallback
- `skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py` - `_config_base`, `secrets_env_path` may return None
- `skills/jev-fast-decision/scripts/jev_review.py` - `_config_dir` raises OSError without a home; `_typesafe_key` reads an empty path then
- `tools/common_config.py` - `cfg_ai_kit_dir`; `cfg_config_path` and `cfg_segments_dir` use it
- `tools/setup.py` - `resolve_paths` config_dir via `cfg_ai_kit_dir`; `_recover_incompatible_config` atomic publish
- `tests/test_setup.py` - three new TestRecoverIncompatibleConfig tests
- `tests/test_ai_kit_spec.py` - `test_base_is_never_relative_to_the_cwd` rewritten; `test_cfg_resolve_surfaces_the_default_when_config_omits_it` passes `dict(os.environ)`
- `tests/test_external_segments.py` - `test_defaults` gets its own temporary HOME (expectation unchanged)
- `Makefile`, `.pre-commit-config.yaml` - regenerated by `tools/gen_test_groups.py`

## Decisions Made

- An unset, empty or relative HOME means no user dir in every copy; no copy consults the ambient home (SPEC R10: no absolute home is an error).
- opencode's folder (`OPENCODE_CONFIG_DIR` or `config_base/opencode`) keeps its own rule; the plan limits this change to ai-kit's folder.

## Deviations from Plan

**1. [Rule 3 - Blocking] Tasks 2 and 3 share one commit (b2730cd)**
- **Found during:** Task 2 commit preparation.
- **Issue:** Both tasks edit `tools/setup.py` in separate hunks; splitting them needs interactive `git add -p`, which is not available.
- **Fix:** One buildable commit covering both tasks. The commit hook passed after the fix in the next item.
- **Verification:** `scope.py all` green before commit; the commit hook passed 31/31 modules.

**2. [Rule 1 - Bug] `test_external_segments.test_defaults` used an env with no absolute HOME**
- **Found during:** commit hook for Tasks 2 and 3 (first attempt refused).
- **Issue:** The test passed `{}`; the one user-dir rule now returns no directory, so the segments dir became "" instead of a relative path.
- **Fix:** The test gets its own temporary HOME (the plan's permitted change). Its expectation (`endswith ai-kit/segments`) is unchanged.
- **Commit:** included in b2730cd.

**3. [Rule 1 - Bug] Task 1 first commit refused by ruff**
- **Found during:** Task 1 commit hook.
- **Issue:** `RUF100` (an unused `noqa E402`, which this ruff config does not enable) and `B905` (`zip` without `strict=`).
- **Fix:** Removed the `noqa`, added `strict=True`. Re-committed as 4d62eeb.

**4. [Protocol] Synthetic home is `/srv/u`, not the plan's `/home/u`**
- **Issue:** The runner template carries an arch rule that bans the `/home/u` fragment (the same finding as wave 1, 33-02 deviation 2).
- **Fix:** All synthetic HOME values in CASES use `/srv/u`. The rows are otherwise the plan's rows.

**5. [Coverage addition] Extra parity row**
- An absolute XDG with surrounding whitespace (`" /abs/xdg "`) is added to CASES to pin the trim rule (D-27). Not in the plan's list; it adds coverage only.

**Total deviations:** 5 (2 auto-fixed bugs, 1 blocking-commit boundary, 1 fixture literal, 1 added row). **Impact:** None on behaviour. The commit boundary is the only change to the per-task commit shape.

## Issues Encountered

- Not verified here: `make check-dogfood` (a pre-push hook). Wave 1 recorded pre-existing judge-record failures in that target; this plan touches no skill text or judge record, so they are expected to be unchanged. Not re-run in this worktree.
- The orchestrator decides the requirement status. CFG-01 (resolver) acceptance is met; CFG-04 is only partly met (recovery only).

## Verification (run in this worktree, HEAD b2730cd)

| Command | Result |
| --- | --- |
| `scope.py test` (7 modules: config_dir_parity, ai_kit_spec, jev_fast_decision, status_line, setup, gate_scope, arch) | `tests rc: 0`, 7/7 modules passed |
| `scope.py all` lint: `make ruff`, `make pyright`, `make pylint`, `make vulture` | `lint ruff rc: 0`, `lint pyright rc: 0`, `lint pylint rc: 0`, `lint vulture rc: 0` |
| `make pyright` re-run on the final tree | pyright Passed |
| `make test` (test-unit, test-integration, e2e-test incl. test_install.sh, arch-test) | exit 0; unit 117/117, unit-uv 3/3, integration 9/9, e2e 25/25, arch 1/1 modules passed |
| Commit hook, 4d62eeb | ruff, pylint, py-compile, staged tests passed |
| Commit hook, b2730cd | ruff, pylint, py-compile, staged tests passed (31/31) |
| `expanduser` in config_io.py and local_secrets.py | no matches |
| `shutil.copyfile(sample, cfg)` in setup.py | no matches; `os.replace(tmp, target)` present |

## Self-Check: PASSED

- Commits exist: `git rev-list --count b95c787..HEAD` = 2 (4d62eeb, b2730cd).
- Created file exists: tests/test_config_dir_parity.py.
