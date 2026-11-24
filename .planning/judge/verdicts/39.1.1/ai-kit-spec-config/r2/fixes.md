# Loop 39.1.1 round 2 fixes: ai-kit-spec-config

Round 2 left no standing critical, important or high finding: referee-two's one high (D8-1) is refuted by a recorded
run (`refutations/39.1.1.json`: `tests.test_role_orders` shows a usage-limited lane is probed like any other, as
check-only.md states), the advisory referee-three lane had none, and referee-one's lane failed (quota-blocked route,
no verdict). The owner's brief for this loop aims at grade A, so the medium and low findings that cost points and have
a small, truthful fix are fixed here before round 3 (checked: `propose_cmds.py` row fields, `catalog_cmds.py`'s
exclusive `--detect`/`--runtimes-json` group, `cli.py` `_cmd_check_reviewer`, `runner_dispatch.py` `review_spec`).
No code changed.

- opencode:router-env/my-referee-three D5-1 (medium, body size): Step 4's nonzero-exit stop, effort-refusal re-ask and
  WARNING report moved verbatim to the new gated `references/write-failures.md`; SKILL.md keeps the exit check and
  the pointer. SKILL.md is 435 lines and about 6,400 words (round 1 judged 471 lines). Files: SKILL.md,
  `references/write-failures.md`.
- opencode:router-env/my-referee-three D1-1 (medium): Step 2.7's purpose paragraph shortened to the rule and one reason.
  File: SKILL.md.
- opencode:router-env/my-referee-three D8-1 (medium): Step 3 names `python3 "$TOOLS_PY" render-toml`, not a
  repository path. File: SKILL.md.
- opencode:router-env/my-referee-three D2-1 and D8-2 (low): NEVER and Gotchas now come before a `## Workflow` heading
  that holds Steps 0 to 4; Step 2.1 is a four-case decision list. File: SKILL.md.
- opencode:router-env/my-referee-three D3-1 (low): each Gotchas line names its consequence. File: SKILL.md.
- opencode:router-env/my-referee-three D1-2 (low): the host-tools note shortened. File: SKILL.md.
- opencode:router-env/my-referee-three D6-1 (low): `strength` stays unset unless the owner asks to tag lanes. Files:
  SKILL.md, `references/wizard-flow.md`.
- opencode:router-env/my-referee-three D4-1 (low): the implementation note "(always announces the exact path)" replaced by "names the target first" (1,012 characters; the limit is 1,024). File: SKILL.md.
- opencode:router-env/my-referee-three D7-1 (low): two direct positive trigger queries replaced by indirect ones. File:
  `evals/trigger-queries.json`.
- opencode:router-env/my-referee-two D2-1 (low): the two judgment calls moved from Step 2's preamble into
  wizard-flow step 3, where the owner picks; Step 2 states that wizard-flow sets the order. Files: SKILL.md,
  `references/wizard-flow.md`.
- opencode:router-env/my-referee-two D6-1 (medium): the shortlist rows name `model_id` too (the printed fields; the
  view size is the printed `default_view`). File: `references/wizard-flow.md`.
- opencode:router-env/my-referee-two D5-1 (medium): catalog.md says to run one `catalog-report` form (the command takes
  exactly one of `--detect` and `--runtimes-json`) and when `--detect` is the one. File: `references/catalog.md`.
- opencode:router-env/my-referee-two D7-1 (medium): the per-role-orders eval asserts the lane JSON (explicit purpose
  on every lane, the session-default lane's shape). File: `evals/evals.json`.
- opencode:router-env/my-referee-two D1-1 (low) and the round 1 loading-map note: cli-model-selection.md's header names
  both entry points (step 2 for items 1 to 4, step 6 for item 6). File: `references/cli-model-selection.md`.

Not changed: referee-two D8-2 asks to reorder the claude alias list; that sentence is the shared pair-rule paragraph
pinned by `tests/test_ai_kit_spec_runtimes_table.py` across two skills, and the sentence after it already names the
runtime table's selectors. Referee-two D3-1 proposes that execute selection already uses the usage-limit fallback;
`lane_settings.lane_fallback` has no caller outside the fallback warning, so "no run reads this yet" stays.
