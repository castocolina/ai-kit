# 38-09 Summary: the harness move pinned by tests

Status: complete. One commit for the three tasks, 2341823
(`test(38-09): pin the harness move: a rendered copy without it, the export-list rule and the sibling scans`), through one cross-AI lane
(pi router-env/my-coding), status=ok on its first run (261 s). No runner or sibling code changed.

## What changed

- tests/test_cross_ai_render_sync.py: `SELF_TEST_REFUSAL`, `HARNESS_MARKERS` and `TestRenderedCopyWithoutHarness`: an `ensure_runner`
  copy holds no harness marker (all four are in the sibling), has no sibling beside it, stays within 4096 bytes of the template; it runs
  `--print-argv` and one fake opencode review lane to `AIKIT-XAI status=ok`; `--self-test` and `--self-test-list` refuse with exit 2, also
  with a zero-byte sibling.
- tests/test_arch.py: `SELFTEST_SIBLING`, `selftest_import_problems` (one export list, one runner import list, no per-declaration export,
  every export declared, every import exported), `sibling_herdr_problems`; three rule tests on the real files (the jev rule runs on the
  sibling as is) and two non-vacuity tests with the plan's exact expected lists.
- tests/test_config_callers.py: `RUNNER_SIBLING`; `ALLOWED_GSD_WRITES` names the sibling's `runSelfTestCase`/`blackBoxSelfTest`; both runner
  scans read the sibling too.

## Verification (run by the chunk agent)

- Acceptance greps: the four render-sync names once each, the old import line is the only removed line of that file, the eight arch names
  once each, `RUNNER_SIBLING` and the sibling label once each, no old `cross-ai.mjs::runSelfTestCase|blackBoxSelfTest` label; no change
  under skills/ in this commit.
- Lane: render_sync + arch, config_callers + gate_scope, arch_hardcoded_models + cross_ai_skill_text, runner_host_protocol pass; make
  ruff/pyright/vulture exit 0; hook 9/9. Wave 4 gates: see the ledger (c38-2).

## Deviations

- One commit for the three tasks (the chunk's lane prompt) instead of one per task; the checkpoint folds a plan into one commit anyway.
- Two long lines wrapped for ruff.
