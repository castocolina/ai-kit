# 39-12 Summary: one composer per lane, the dispatch wiring and the `capability-block` command

Status: complete. Commits 49540c1 (`feat(39-12): Tracer: compose_for_lane, ComposeResult and the capability-block command`, Task 1,
with the regenerated test-group listings), 06b7c76 (`feat(39-12): lens plan, MCP run file and final window check; dispatch-reviewer
wired, refusal exit 65`, Task 2), 854941f (`test(39-12): dispatch-reviewer refusal, no-files note, other-worktree note, argv cap and
lane independence`, Task 2 follow-up) and 316fda6 (`feat(39-12): dispatch-execute wired to the composer, refusal exit 65`, Task 3).
Executed through four cross-AI lanes (pi router-env/my-coding), each status=ok on its first run (568 s, 600 s, 152 s, 452 s).
Preceded by the neutral fix 7f120c1 (`fix(39): child_path drops empty and relative PATH entries`).

## What changed

- `capability_block.py`: `LaneRequest`, `ComposeSeams`/`DEFAULT_SEAMS`, `ComposeResult`, `LaneRefused`, `with_block`, `lane_spec`,
  `cleanup`, `guidance_paths` (a guidance path that fails R8 is omitted with its reason, never a refusal), `_doc_worktrees` (orchestrator
  decision D1: a document in another worktree of the same repository is an allowed root for the file values only and is named in a
  `note:` line; a separate repository is still `path_outside_roots`), `_value_refusal` (cwd, skill paths, files and the MCP file through
  `validate_values`, all rejections in one record), `_checked`, `_mcp` (run directory owned from the line after `mkdtemp`, removed on any
  failure), the final-block window and argv-cap check with whole-lens skipping (`_final`, `_plan`), the native branch (lens lines only),
  `compose_for_lane` (no `--files`: an empty `ComposeResult`, decision D2) and the read-only `capability-block` command.
- `reviewer_dispatch.py`: `ReviewerSeams.compose_fn`/`compose_seams` replace the three tooling-guidance seams; the compose runs after the
  native, skip-route and model checks, once per dispatch; a blank prompt is sent as given; the unknown-window note; `LaneRefused` on a
  refusal; `cleanup` in `finally`; `ReviewerDispatchSpec.files`.
- `execute_dispatch.py`: `ExecuteSeams.compose_fn`/`compose_seams` replace `build_tooling_guidance_fn`; `build_execute_guidance` returns
  `(ComposeResult, text)` with the soft-confinement sentence passed through `LaneRequest` (the block shows it for `write` `full` or
  `unknown`, D-04); `OS_SANDBOXED_EXEC` no longer imported; `ExecuteDispatchSpec.files`; the refusal raises `LaneRefused`; `cleanup` in
  `finally`.
- `cli.py`: `--files` on `dispatch-reviewer` and `dispatch-execute` (default None: no block plus the stderr note), the ignored
  `--tool-availability-json` note, `except LaneRefused` before `except ValueError` in both handlers (record JSON on stderr, exit 65,
  empty stdout), the `capability-block` wiring.
- Tests: `tests/test_compose_for_lane.py` (new, 26 tests); the existing dispatch tests in `test_ai_kit_spec`, `_runner_dispatch`,
  `_env_scrub`, `test_cross_ai_runner_e2e` and `test_ai_kit_spec_superpowers` moved to `compose_fn`; `_runtimes_table` reads
  `runner_dispatch.OS_SANDBOXED_EXEC`.

## Verification (run by the chunk agent)

- Acceptance greps: `def compose_for_lane(...)` 1, `class LaneRefused(ValueError)` 1, `capability_block.register_parsers(sub)` 1,
  `build_tooling_guidance` in reviewer_dispatch none, `except LaneRefused as exc:` 2, `code_index_registered_fn` in tests none,
  `OS_SANDBOXED_EXEC` in execute_dispatch none, `build_tooling_guidance_fn` in tests and skills none, the soft-confinement call 1,
  `REFUSED_EXIT` in cli.py 2.
- Under the scratch-HOME wrapper (real node first on PATH): test_compose_for_lane (26), test_ai_kit_spec (688), test_ai_kit_spec_env_scrub
  (3), test_ai_kit_spec_runtimes_table (63), test_ai_kit_spec_superpowers (173), test_ai_kit_spec_runner_dispatch (80),
  test_cross_ai_runner_e2e (28), test_arch_hardcoded_models (23), test_cli_help_flags (15), test_config_status (25), test_gate_scope (62),
  test_capability_block (16) pass. The lanes ran ruff, pyright, vulture and pylint with exit 0; the Task 3 hook ran 139/139 modules (the
  curated-config matrix deferred to push). `detection.py`, the model-literal baseline and both runner copies unchanged.

## Deviations

- Before this plan, commit 7f120c1 changed 39-10's `child_path`: only absolute PATH entries are kept (an empty or relative entry resolved
  against the lane cwd and found tools and the MCP command in the working directory; orchestrator decision). The 39-10 test case "a relative
  entry lists rg when cwd is set" now expects no tool line; the parameter is `_cwd` (unused, kept for the positional callers).
- Task 2's lane added only 8 of its 18 behavior tests (some merged: window over and unknown, lens delivered and skipped); a follow-up
  tests-only lane (854941f, a fourth commit of this plan) added the other nine, no product change.
- Test names that differ from the plan's: `test_window_over_refuses` and `test_unknown_window_runs` are one test
  `test_window_over_and_unknown` (both assertions kept: reason, `detail.window == 10`, the unknown window not capped on a 1,000,000-byte
  prompt); `test_lens_skipped_not_lane_refused` and `test_lens_delivered_with_runner_name` are one test `test_lens_delivered_and_skipped`
  (the skip case uses a fixed window of 250 tokens instead of "base estimate plus 10"; the delivered case checks the real path and that the
  second preview received the lens spec); `test_missing_files_skips_preview` plus `test_missing_file_list_builds_no_block` split the D2
  test; the old `test_code_index_registration_is_resolved_internally_not_asked_of_the_caller`,
  `test_custom_entry_never_runs_the_registration_check` and `test_includes_tool_guidance_when_provided` were renamed as the plan says.
- `test_native_lane_gets_lens_lines_only` uses a `pi` native request and asserts the lens line substring and no preview call, not the full
  block equality with a `claude` request the plan names (weaker than planned; open item).
- Synthetic pins in `tests/test_compose_for_lane.py` (not plan-named): `capability_block.guidance_paths` patched to `(None, None, ())` in
  `setUp` (the expected blocks would otherwise depend on the checkout's shared tooling file), and `lens_delivery.mcp_pick` patched to a fake
  pick in `test_mcp_dir_removed_when_publication_fails` (beside the plan-named `write_mcp_file` patch); `guidance_paths` never runs
  unpatched in the new test modules.
- Changed assertion outside the plan's list: `TestExecuteCliRejection.test_no_fact_never_refuses` (tests/test_ai_kit_spec.py) expected an
  empty stderr; it now expects the D2 no-block note (`dispatch-execute` without `--files`).
- `tests/test_ai_kit_spec_superpowers.py` (not in the plan's files list; in Task 3's verify list, covered by the plan's catch-all rule):
  the real-dispatch test gets `compose_fn=lambda *_a, **_k: ComposeResult()`.
- `compose_for_lane`'s signature stays on one line (the acceptance grep) with `# pylint: disable-next=line-too-long` and `# noqa: E501`.
- Helper split beyond the plan: `_git_value`, `_block_input`, `_delivery_bytes`, `_plan`; the custom and runner branches share
  `_block_input`; `ReviewerDispatchSpec.files` and `ExecuteDispatchSpec.files` are typed `tuple | None`; the `dispatch-execute` `--files`
  help text is split over odd string pieces (same words).
- D-04 as written: the soft-confinement sentence appears for an execute lane whose `write` is `full` or `unknown` (39-10's rule);
  `workspace` and `none` do not get it.
