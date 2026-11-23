# 39-15 Summary: the review skill text for lane capability blocks, lenses and refusals

Status: complete. Commits 00a5ff1 (`docs(39-15): child-PATH rule, --files and lane capabilities in the review references`, Task 1) and
0c6e83c (`docs(39-15): lane capability block, lenses and refusals in the review skill`, Task 2). Executed through two cross-AI lanes (pi
router-env/my-coding), each status=ok on its first run (302 s, 530 s; the Task 2 lane's first commit attempt failed the hook on the eval
fixture rule, its second passed).

## What changed

- `SKILL.md` (spec-review): Step 0.7 no longer names `TOOL_AVAILABILITY_JSON`; the Step 1 dispatch snippet passes `--files <each DOC_PATHS
  entry> <each GROUNDING_DOCS entry, if any> <CHECKLIST_SKILL_MD> <FRAMEWORK_PROFILE_PATH, unless none>` in place of
  `--tool-availability-json`; Step 1 exit handling names exit 65 (pre-spawn refusal: quote the record, schedule nothing); new section
  `## Lane capability block, lenses and refusals` (block sections in order, the role, lens-note and refusal-reason tables, the window rule,
  the no-`--files` note, `--strict-mcp-config` replacing the host's other MCP servers on a claude lane, the owner-started
  `edit-lens-pass`); one `## Evidence` bullet.
- `references/cross-ai-dispatch.md`: Step 0.7 point 0 is the child-PATH rule (no `detect-tools` call); the Step 1 rationale describes
  `--files`, the no-`--files` stderr note, the other-worktree note and `path_outside_roots`; the pending-lane snippet and resume record
  pass `--files` and drop `tool_availability_json`; new `## Lane capabilities` section (fields and values, `{value, label}` with the
  `{state, source}` label object, `prompt {channel, max_bytes}`, the three code index routes, `--strict-mcp-config`, exit 65).
- `references/reviewer-prompts.md`: the native route carries `TOOL_AVAILABILITY = {}` and `LENS LINES: <LENS_LINES>`, filled from
  `capability-block ... --role review --native`.
- `references/tooling-guidance.md`: reads the capability block's `TOOL_AVAILABILITY` line, shell fact and `CODE INDEX` section.
- `evals/evals.json`: `edge-refused-lane-exit-65`, `edge-edit-lens-pass-owner-started` (15 cases).
- `tests/test_cross_ai_docs_text.py`: helpers `review_module`, `section_text`, `table_names`; constants `REVIEW_SKILL`, `PROMPTS`,
  `GUIDANCE`, `SECTION`; classes `LaneCapabilityReferences` (6 tests) and `LaneCapabilitySkillTables` (8 tests).

## Verification (run by the chunk agent)

- Acceptance: `TOOL_AVAILABILITY_JSON` 0 in cross-ai-dispatch.md, reviewer-prompts.md and SKILL.md; `^## Lane capabilities$` 1;
  `^## Lane capability block, lenses and refusals$` 1; spec-config `python3 "$TOOLS_PY" detect-tools` still 1; both eval ids 2; Makefile
  and `.pre-commit-config.yaml` untouched; `def test_` 17 -> 23 -> 31 (+14), no `unittest.skip`; every plan-named test exists under its
  plan name (14 of 14); `json.tool` exit 0; no grok text added (the one grok line in cross-ai-dispatch.md predates the plan).
- The `## Lane capabilities` block is in the file line for line (23/23); the SKILL.md block 54/56 lines verbatim, the two other lines
  carry the two additions listed under Deviations.
- Modules: test_cross_ai_docs_text (31), test_skill_text_history (45), test_ai_kit_spec_runtimes_table (63), test_ai_kit_spec (688),
  test_skill_evals_shape (6), test_gate_scope (62), test_spec_chain_text (40, lane) pass. Lanes: ruff, pyright, vulture, pylint exit 0;
  hooks pass (Task 2: 141/141, one over-budget module deferred to push).

## Deviations

- Two sentences added to the SKILL.md section beyond the plan's exact text (orchestrator decisions; shipped code
  `capability_block._access_section` and `edit_pass.pick_lane`): an execute lane whose `write` is `full` or `unknown` gets the
  no-confinement sentence word for word, `workspace` or `none` none; the after-approval pass runs only on a lane with `write`
  `workspace` or `full`, which at present only codex lanes report (`full` for a plain codex lane, `workspace` with
  `--codex-sandbox workspace-write`), and with no such lane it says so and runs nothing.
- The two new eval cases name the existing project fixture (`evals/files/active/project/aikit/config.toml` and its `demo.md`) and the
  setup sentence of the other review cases instead of `"files": []`: the hook's `test_review_fixtures_use_a_project_folder` (in
  tests/test_spec_chain_text.py) requires a project fixture for review evals.
- The re-wrapped Step 1 rationale paragraph keeps the no-`--files` note whole on its own line (longer than 100 columns), so the doc test
  finds it as one substring; several added SKILL.md lines are longer than the surrounding wrap (plan text copied as given).
- No synthetic pins (doc tests only; no patch or mock).
- The skill-judge loop was not run here: 39-18 judges the changed SKILL.md.
