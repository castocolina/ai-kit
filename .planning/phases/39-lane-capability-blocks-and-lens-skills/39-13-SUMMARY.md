# 39-13 Summary: one builder for three entry points, the capability summary in spec-config checks, the adapter refusal

Status: complete. Commits ecf1f96 (`feat(39-13): Tracer: lane_summary and one capability line per lane in config-status`, Task 1, with
the regenerated test-group listings) and 3bc7898 (`feat(39-13): check-reviewer capability key, byte-equal block across the three entry
points, adapter refusal exits 65`, Tasks 2 and 3 in one lane and one commit). Executed through two cross-AI lanes (pi
router-env/my-coding), each status=ok on its first run (461 s, 328 s).

## What changed

- `capability_block.lane_summary(entry, role, cwd, env, seams)`: native (no runtime, no command), malformed (`invalid lane entry: ...`),
  custom (all-unknown facts) and runtime lanes (the `--print-argv` dry run with the flat lane settings and `extra`, no lens or MCP flags);
  runtime, model and key escaped; guidance-omitted notes in the summary (decision D6).
- `config_status.py`: `capability_lines(cwd, env, role)` reads the lanes with `cfg_resolve(..., migrate=False)` and prints one
  `capability <runtime>/<model> <role>: <summary>` line per lane after the `checked` lines, only for state `active`, all built before the
  first print; docstring updated.
- `cli.py`: `check-reviewer` gains the `capability` key (`_capability_key`, the effort override reaches the preview); `dispatch-reviewer`
  passes `compose_seams=capability_block.DEFAULT_SEAMS`.
- Superpowers adapter `cli.py`: `_cmd_dispatch_task` catches `capability_block.LaneRefused`, writes a dispatch-result object with
  `returncode` 65 and the record as `status` (classified `real_error`), writes no report, returns 65. The adapter's SKILL.md is unchanged.
- Tests: `tests/test_capability_entry_points.py` (new, 10 tests); `test_config_status` (first three lines plus capability lines, no
  node dry run), `test_config_herdr_identity` (the loop call wrapped in a `DEFAULT_SEAMS` patch), `test_ai_kit_spec_superpowers`
  (`test_dispatch_task_refusal_exits_65`).

## Verification (run by the chunk agent)

- Acceptance greps: `def capability_lines(...)` 1, `migrate=False` 1, `result["capability"] = _capability_key(args, rid, extra, deps)` 1,
  `except capability_block.LaneRefused as exc:` 1, `compose_seams=capability_block.DEFAULT_SEAMS` 1, `def test_three_entry_points_byte_equal_` 2.
- Under the scratch-HOME wrapper: test_capability_entry_points (10), test_compose_for_lane (26), test_config_status (25), test_ai_kit_spec
  (688), test_ai_kit_spec_superpowers (174), test_arch (118), test_effort_probe (23), test_catalog_usability (13), test_config_herdr_identity
  (4), test_spec_chain_text (40), test_gate_scope (62), test_arch_hardcoded_models (23) pass. Lanes: ruff, pyright, vulture, pylint exit 0;
  hooks 207/207 (Task 1, Makefile staged) and 144/144 (the curated-config matrix deferred to push). `detection.py`, the model-literal
  baseline, both runner copies and the adapter SKILL.md unchanged.

## Deviations

- Tasks 2 and 3 ran in one lane with one commit (the plan asks one commit per task).
- Synthetic pins in `tests/test_capability_entry_points.py` (not plan-named): `capability_block.resolve_shared_tooling_reference_path` is
  patched in `setUp` (the checkout's shared guidance file lies outside the fixture repository and its empty skill roots, so every summary
  would carry a `guidance omitted` note; the plan expected `notes == ()` in the fixture homes); the two byte-equality tests also patch
  `guidance_paths` to `(None, None, ())` and `lens_delivery.mcp_pick` to `[]` (each entry point would otherwise create its own MCP run
  directory, so the blocks would differ by a temporary path); they also patch `cli.effort_probe.probe_effort` for the effort case.
- `_capability_key` leaves the `runtime` key out of the entry when no runtime is given (`lane_summary` treats an absent key as a native
  lane); the plan's literal dict always carries `runtime`.
- The equality fixture keeps effort unset on both sides (the plan's stated limit: `capability-block` takes no effort knob).
- `cfg_resolve` kept the key-only native entry unchanged, so `test_native_lane_line` asserts on the printed line directly.
- One blank line (not two) before `def _capability_key` in cli.py; ruff passes (its E30x rules are not active).
