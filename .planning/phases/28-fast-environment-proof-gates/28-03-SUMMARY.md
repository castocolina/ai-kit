---
phase: 28-fast-environment-proof-gates
plan: 03
subsystem: testing
tags: [tests, environment-independence, frozen-clock, git-ceiling]
requires: []
provides:
  - "test_worktree_e2e passes with TMPDIR inside a git work tree"
  - "tool-substitution compose tests independent of checkout path length"
  - "precompact header counts independent of machine speed (frozen clock)"
affects: [tests/test_worktree_e2e.py, tests/test_tool_substitution_hook.py, tests/test_precompact_core.py]
tech-stack:
  added: []
  patterns: ["GIT_CEILING_DIRECTORIES pinned to the test temp root", "FrozenClockMixin on the existing _monotonic seam"]
key-files:
  created: []
  modified:
    - tests/test_worktree_e2e.py
    - tests/test_tool_substitution_hook.py
    - tests/test_precompact_core.py
key-decisions:
  - "Clock frozen at 0.0 (not 1000.0) so the 0.2 s budget arithmetic stays exact"
  - "TestCap joined the frozen-clock classes: it asserts one client call per chunk (70 chunks), which depends on the budget"
requirements-completed: [GATE-03]
status: complete
duration: ~25 min
completed: 2026-11-03
commits: 2
plan_head_before: 7b0ce148ef16a75c341a721d8a6ca4a5093baeee
plan_head_after: 6939d3a2d66d15c9f1c67430d41c20fb5b1c216d
actuals:
  tokens: 6000
  tasks: 2
  commits: 2
---

# Phase 28 Plan 03: Environment-proof tests Summary

The no-git e2e case, the two tool-substitution Usage-path tests and the precompact header-count tests no longer depend on where the checkout or TMPDIR sits, or on machine speed. No product code changed; `CLASSIFY_SECONDS = 8.0` is untouched.

## Commits

- febe174 test(28-03): pin no-git e2e and compose tests against checkout/temp location
- 6939d3a test(28-03): run precompact header-count tests on a frozen clock

## Task 1 (tracer): location-proof tests

- `tests/test_worktree_e2e.py`: `GIT_CEILING_DIRECTORIES=cls.tmp` in the setUpClass `git` helper env (new) and in `_render`'s env.
- `tests/test_tool_substitution_hook.py`: `test_compose_has_guidance_flags` patches `detect.__file__` to `/r/tools/hooks/detect.py`. `test_usage_path_collapses_a_symlinked_home` builds `<real>/r/tools/hooks/` under a temp dir, symlinks `home` to `real`, patches `detect.__file__` and `expanduser`, and asserts `" Usage: ~/r/"` (stricter than the planned `" Usage: ~/"`). No long-path twin added; `test_usage_suffix_dropped_if_line_would_exceed_limit` is unchanged.
- Step 1 reproduction: with `TMPDIR` set to `tmp/p28/wt` inside the worktree (`bash tmp/p28/repro.sh tests.test_worktree_e2e`), `test_outside_repo_hides_worktree_segment` FAILED (rc=1; the status line showed the enclosing worktree's `⎇ agent-...`). 28-01's baseline env was NOT committed in this worktree at that time (`git log --oneline -1 -- tools/run_unittest_parallel.py` printed 2c34a58, the 27-09 commit), so the failure was not hidden by a runner ceiling. After the fix the same command passes.
- Long clone: `tmp/p28/longpath.sh` clones committed history with `git clone --quiet --local --no-hardlinks` (the `--no-hardlinks` was added because plain `--local` failed with "Invalid cross-device link" between the worktree and `/tmp`). Path length 224; scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1`, deleted by an EXIT trap. Result: `4/4 modules passed`, exit 0 (tool_substitution_hook 73 tests, goal_prompt cli 43, render 78, pointer 32). The clone has no gitignored `.claude/gsd-core`; none of the four modules runs gsd-core.

## Task 2: precompact frozen clock

- `FrozenClockMixin(CoreEnvMixin)` patches `core._monotonic` to 0.0 in `setUp` (cleanup via `addCleanup`); its docstring carries the 83 s hung-stub bound (3 s + 40 x 2 s).
- Applied to `TestTracerCorePresummarize`, `TestHeaderCounts`, `TestCoreEdges` (so `test_chunk_max_chunks_dropped_counted` is frozen; `test_classify_stops_below_ten_ms` keeps its own `_monotonic` patch, which overrides inside its block), `TestRealClientContract` (loopback count tests) and `TestCap`.
- Classes that kept the real clock: `TestBudget` only (its tests patch the clock themselves or need real time, e.g. `test_budget_hung_child_killed`). The other classes (`TestChunking`, `TestPrivateDir`, `TestPiEntry`, `TestOpencodeEntry`, `TestMainEntry`, `TestChunkLimitWithinClientGuard`, `TestLowConfidencePolicy`) were left alone: they assert no header counts or budget behaviour. No frozen-clock test asserts a positive `elapsed_ms` (`rg elapsed_ms` finds no match in the file).
- `TestCap` is a small extension beyond the plan's list: `test_cap_newest_kept_whole_and_no_model_call` asserts `len(argvs) == 1 + len(chunks)` for 70 chunks, which is budget-dependent. Its hung-stub bound is 3 s + 70 x 2 s = 143 s, still inside 900 s.
- `test_header_counts_hold_on_a_tiny_budget`: `CLASSIFY_SECONDS` 0.2, `run_probe` and `classify_chunk` faked in-process; asserts exact 40/40/0 counts and per-label counts, 41 recorded timeouts all `<= 0.2 + 1e-9`, and no stub log file (no client process started). `CLASSIFY_SECONDS` is patched only there and in `TestBudget`.

## Verification (commands and exit codes)

- `bash tmp/p28/repro.sh tests.test_worktree_e2e tests.test_tool_substitution_hook` (TMPDIR inside the work tree): 2/2 modules passed, exit 0.
- `bash tmp/p28/longpath.sh`: path length 224, 4/4 passed, exit 0.
- `python3 tools/run_unittest_parallel.py tests.test_precompact_core tests.test_tool_substitution_hook`: 2/2 passed, exit 0 (precompact module ~30 s; I did not measure the pre-change duration).
- `uv run pyright` on the three files: 0 errors. Pre-commit hooks (ruff, py-compile) passed on both commits.
- Acceptance greps: `GIT_CEILING_DIRECTORIES` count 2; `realpath(_REPO)` no match; `return_value=1000.0` no match; `git diff --stat` on `tools/hooks/precompact_core.py` empty.
- Not run: `make test` (other wave-1 plans edit the runner; Plan 02 Task 3 owns the all-tier run).

## Deviations from Plan

**1. [Rule 3 - Blocking] `git clone --local` hardlink failure** — `tmp/p28/longpath.sh` needed `--no-hardlinks` (cross-device). Script is gitignored; no repo change.

**2. [Rule 2 - Scope] TestCap added to the frozen-clock classes** (see above).

## Known Stubs

None.

## Self-Check: PASSED

- febe174 and 6939d3a are ancestors of HEAD; the three modified test files exist; working tree clean before this summary.
