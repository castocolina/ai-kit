# 38-08 Summary: the self-test harness moved into cross-ai-selftest.mjs

Status: complete. Three commits, one per task, each through one cross-AI lane (pi router-env/my-coding), status=ok on its first run:
6036594 (`refactor(38-08): give the runner setters and a self-test hook so the harness can move`, 182 s), 27ea06f
(`refactor(38-08): move the self-test harness into cross-ai-selftest.mjs`, 263 s), c6bb49b
(`test(38-08): name the self-test harness beside the runner template`, 210 s).

## What changed

- The runner template keeps its state behind `setTable`, `setOverlayIds`, `setLog`; the crash and signal handlers call `selfTestHook`
  (set by `setSelfTestHook`); `RUNNER_FILE` replaces the harness's own `import.meta.url` read (26 harness assignments converted: 7/7/12).
- The harness (classifier fixtures, `caseCycleFile`, `hermeticEnv` through `blackBoxSelfTest`) lives in
  `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs` (9,593 lines) with one `import { ... } from './cross-ai.mjs'` list of 99
  names; the runner (5,873 lines, was 15,180+) ends with one `export { ... }` list of the same names and loads the sibling through
  `loadSelfTest()` only for `--self-test`/`--self-test-list`; a missing or zero-byte sibling prints
  `cross-ai: the self-test is not shipped in this copy; run it from the template` and exits 2.
- `SelfTestCeilingPins` reads template plus sibling; the two e2e tests that ran the self-test on another file now put the sibling beside it;
  `tests/cross_ai_selftest.py` names `SIBLING` and asserts it exists.

## Verification (run by the chunk agent)

- The orchestrator wrote seam.py, splice.py, refusal.sh and st.sh byte for byte from the plan and dry-ran them on a scratch copy of
  e500022 first; the published runner and sibling are byte-equal to that dry run (cmp), and the Task 1 template to the dry seam result.
- `--self-test-list` byte-equal to e500022 (627 lines) after each task; refusal.sh `refusal ok`; smoke cases `self-test ok`.
- `--print-argv` (pi exec/review, opencode exec/review, claude review, cursor exec, pi with `--model-pi`, a refused model) byte-equal to
  e500022 (session uuids normalised).
- Harness markers absent from the runner; no per-declaration export; `export {`, `loadSelfTest`, `SELF_TEST_FILE` once each; the sibling holds
  its import list, `blackBoxSelfTest` and `export { blackBoxSelfTest };` once each.
- Under the guard, two modules per call (peak 4 runner processes, never killed): the eight shard modules (30.1 to 34.8 s each, all under the
  60 s commit budget), test_cross_ai_runner_e2e, test_cross_ai_render_sync, test_runner_describe, test_runner_host_protocol,
  test_cross_ai_skill_text, test_runner_fork_chain, test_config_callers, test_arch, test_arch_hardcoded_models, test_runner_flags, the
  settings/skills/mcp argv modules, test_runner_claude_exec, test_runner_facts, test_gate_scope: all pass. Hooks: 128/128, 130/130, 190/190.

## Shipping check

- `rg -n "os.path.join\(claude_dir, \"skills\", name\)" tools/setup.py`: `1819: link_one(os.path.join(claude_dir, "skills", name), target, dry, counts)`
  (in `apply_additive_skills`, called by `_headless_link_skills` at 4532): one directory link per skill, so the sibling ships with the template.
- `rg -n "resolve_cross_ai_template_path|def render|def ensure_runner" .../cross_ai_script.py`: `141: def render(`, `151: path = mod.resolve_cross_ai_template_path()`,
  `358: def ensure_runner(`: only the template bytes are rendered. A scratch-HOME `ensure_runner` render: copy 260,896 bytes (template 260,841),
  no sibling, no harness marker; `--describe` and two `--print-argv` calls exit 0 with the real node; `--self-test` and `--self-test-list`
  print the refusal and exit 2.

## Deviations

- Lane method: the scripts were written by the orchestrator from the plan (not retyped by the lanes) and the lanes ran a trimmed verify
  list (two modules per call); the orchestrator ran the plan's module lists itself under the guard (above).
- Task 2's rendered-runner comment is split over two lines (ruff line length).
- Not this plan's: `tests/fixtures/cross_ai_selftest_secs.json` lacks `host-group-left` and `temp-dirs-gone` (cases added by earlier plans;
  every recorded name is still listed). Re-recording is plan 38-25's.
