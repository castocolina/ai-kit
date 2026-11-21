# Phase 36 code review

Reviewed: the whole phase diff `88440fc^..6a49df5` (code, tests, skills, docs; plan files as context) on 2026-11-21.
Method: a `gsd-code-reviewer` pass at standard depth over the 22 changed runtime modules and the new test modules (new
modules read in full, changed ones as diffs); a scan of every added line for asserts, `noqa`, pylint disables, broad
excepts, absolute paths, `type: ignore` and `grok`; a scan of tracked files for the removed keys; a usage scan of the
public names of the ten new modules; the orchestrator's items a to h; and SPEC R1, R4, R5, R6, R7, R12 and R13 run
against the real CLI in a scratch HOME under `tmp/`. Fixes ran through two lane fix-ups (pi, `router-env/my-coding`) or,
for doc, comment, test and one-line edits, directly.

## Findings by severity

Counts: 0 critical, 0 high, 3 medium, 8 low, 6 info.

- MEDIUM, fixed: a lane key holding a newline broke out of the generated ladder comment above `[lanes.policy.review]` and
  `[lanes.policy.execute]` (`config_io._ladder_comment_lines` wrote the key raw) and wrote its own TOML table outside
  `[lanes]`; the post-write check compares only `[lanes]`. The pattern predates the phase (flat ladder), but the phase
  rewrote it for two tables. The comment now prints the key through `clean_note` (997e53a).
- MEDIUM, fixed: `probe-quota --role execute|both` probed only the keys of the execute order, while the execute selector
  can pick every execute lane (contract amendment 11, `selectable_lanes`), so an unlisted execute lane got no quota probe.
  It now probes the selectable set; the `--check-only` reference and the `--role` help say so (e8d523a, 6273ea9).
- MEDIUM, kept: `render-toml` stores a hand-carried `effort` on a claude or copilot lane without a refusal. SPEC R4 states
  that case on its own: the wizard never asks for an effort on those runtimes and writes none, and "a lane written by
  hand with one prints `ignored: the runner has no effort flag for <runtime>` on every preview and dispatch" (checked:
  `build-command --runtime claude --effort high` and `--runtime copilot` print that line). Refusing it at write would drop
  the whole lane under render-toml's drop-with-warning rule, which loses more than it guards.
- LOW, fixed: `lane_order.rank` narrowed `judge` with an `assert` that vanishes under `python -O`; the window guard now
  checks it (3ee024d).
- LOW, fixed: a hand-written `effort` on a custom lane whose template has no `{effort}` dropped without a line in
  `render-command`; it now prints `NO_RUNTIME_IGNORED` (a session default never renders there: it has no command) (e8d523a).
- LOW, fixed: `data_use_source` accepted control characters (`\S`), and `lane_usage_limit` returned a hand-written note
  raw; the source must now be printable ASCII and the reader cleans the note (997e53a).
- LOW, fixed: `clean_note` deleted control characters, so a typed `daily cap`, newline, `100 requests` became
  `daily cap100 requests` (an existing round-trip test pinned `a dailycap`); a control character is now one space (997e53a).
- LOW, fixed: the migration's two bare `os.remove(dest)` calls could raise past its error handling, and a filesystem
  without hard links read "the next run finishes it" forever; both removals warn now, and the message names manual
  removal and `--keep-backup` (e8d523a).
- LOW, fixed: `propose-lanes` read a `cursor-agent` keyed runtimes snapshot as an empty row for its stale and price
  checks while the effort check normalised it; the file snapshot is normalised once at load (e8d523a).
- LOW, deferred: pi's listed-id rule (`known_ids`) is used by `offered_levels` but not by `effort_form` at preview, probe
  and dispatch, so a complete listed pi id ending in `:<level>` is offered levels that the call then reads as a carried
  effort. Phase 37 reworks the runner's effort path (todo below).
- LOW, kept: the pool key pattern accepts any lowercase tier while the refusal reads `<provider>:free`. The shape is the
  locked contract's (36-RESEARCH.md section 0 item 2, `^[A-Za-z0-9._-]{1,64}:[a-z]{1,16}$`) and only the wizard writes
  the key; the duplicate constant goes to the todo.
- INFO, deferred: `role_orders.ordered_lanes` (named by contract item 7) has no runtime caller; `DEFAULT_POLICY` keeps
  `"ladder": []`; small duplicates (the control-character class in four modules, `JEV_ERROR`, `class_label`, cursor
  bracket parsing). Todo below.
- INFO, kept: a project's legacy flat ladder loses to a user per-role table: the documented rule (36-RESEARCH.md Part A
  section 4: a role table from either layer beats a legacy ladder from either layer), with a warning.
- INFO, kept: custom command entries get route `no_formula` in exec mode, wider than contract item 10's wording; it is
  SPEC R7's "`no_formula` replaces `review_only`", and the detail names why (a custom lane runs in review mode only).
- INFO: the four readers (`lane_usage_limit`, `lane_escalation`, `lane_fallback`, `escalation_target`) have no runtime
  caller by design (SPEC R5 and R12 d; pinned by the source-scan guard in `tests/test_lane_settings.py`).
- INFO: every config write goes through `toml_splice.publish` (tempfile plus `os.replace`); no third-party import in
  runtime code; no absolute path; no model literal outside `router-env/<x>` and the placeholder forms; the grok lines in
  added text are message-text edits of existing tests and one existing doc line (contract item 11).

## Orchestrator items

- a. Fixed (d066f84): `references/escalation.md` (three places) and the `compute_ladder_keys` docstring named the removed
  flat `policy.ladder`; the adapter reads `role_order(resolved, "execute")`, so the text now names the execute order
  (`ladder_keys`: the `[lanes.policy.execute]` ladder, then any unlisted execute lane). The adapter SKILL.md is unchanged
  (299 lines).
- b. Fixed (d066f84): Step 2.7's "review-only default" described `split_by_purpose`'s legacy filing of an absent
  `purpose` under review (correct, pinned by `test_session_default_purpose_matches_the_writer`), not the removed key;
  reworded to "that fallback for an absent `purpose`". Steps 2.4 and 2.6 agree with `cli-model-selection.md` after
  36-24: the lane's `purpose` comes from the set confirmed in `wizard-flow.md` step 3, as Step 2.6 says.
- c. Fixed (3ee024d): the extra `secret_shapes.redact` pass in `effort_probe` is kept: it redacts a key glued to a
  control character before `sanitize_error` strips the control (lesson 3 of the lane notes); a new assertion pins it.
  The tests now carry the plan's behaviour lines: `error` and `reason` None and `level` on an accepted call; through
  `check-reviewer` the exact `effort_probe` key set, the `^accepted by a call on \d{4}-\d{2}-\d{2}$` label and `available`
  and `answered` true; state, probe and label of every ignored, inconclusive and rejected outcome.
- d. Confirmed: every phrase of 36-25's named constants is pinned by `tests/test_spec_config_flow_text.py` (checked by
  script) except the full headless sentence, which is pinned by its opening marker; the full sentence is in SKILL.md.
  Accepted.
- e. Fixed (d066f84): against `e4b965e^`, three pass criteria were missing: the GSD case's framework `gsd`, archetype
  `plan` and path-only reviewer prompt (SKILL.md line 36: every reviewer reads the file from disk, so the behaviour holds
  for GSD); the generic case's no crash or hang; the ambiguous case's FRAMEWORK_PROFILE_PATH none after the fallback.
  All three are assertions now; nothing else of the four files was lost.
- f. Confirmed: the 36-11 edit (`test_execute_lane_merges_project_over_user_within_execute_only` asserts no `effort`)
  matches MODEL_BOUND: `_drop_model_bound` drops `effort` when the project restates a different `model` without
  restating it. The 36-18 baseline edit removed exactly one `keyval x/y` line of one file; nothing else changed there,
  and `tests.test_arch_hardcoded_models` passes.
- g. Reported: 27 entries carry `"cleaned_by": "36"` (one carries `"37"`). One is `ai_kit_spec/detection.py`, which phase
  36 rewrote and keeps by contract item 15 (its hits are the native-selector seed list R7 keeps). The other 26 are
  curated-config fixtures and tests (`tests/fixtures/curated_config_v2/**`, `tests/test_curated_config_*.py`,
  `tests/gsd_curated_eval.py`, `tests/test_gsd_curated_eval.py`) that phase 36 never touched. SPEC R8: "this phase cleans
  every file it rewrites"; its Out of scope: "cleaning baseline files this phase does not rewrite". HUB-09 and ROADMAP
  criterion 3 ask only for the guard and the shrink-only baseline. No removal is required; the 26 labels name no real
  owner and go to the todo for relabelling.
- h. Removed keys: no live `review_only`, `no_exec`, `usage_pool` or flat `policy.ladder` use outside legacy-input
  diagnostics, history docs and test names about `purpose = "review"`; `exec_formula` is the new field. Two stale test
  comments fixed (d066f84). Dead code and duplicates: see INFO. Narrowing asserts: one, fixed. Secrets and control
  characters: see the MEDIUM and LOW fixes. Atomic writes, stdlib-only, absolute paths: clean. Spot checks in a scratch
  HOME, each as the SPEC states: R1 `config-status` prints `none` and the two checked paths and writes nothing; R4 the
  effort forms (`:high`, `#high`, `[effort=high]`, `--codex-effort high`), the claude and copilot `ignored:` lines,
  nothing for no effort, codex `max` and an empty effort refused; R5 a non-boolean flag refused, a false flag not
  written; R6 `propose-lanes` on an empty catalog exits 2 naming the catalog step; R7 a claude execute lane accepted, an
  unknown runtime refused with the custom-lane message, `placeholder-cli-1` stored as a custom `command` lane; R12 a
  malformed pool and a pool without the data-use record refused, the only-flagged warning printed; R13 a label on
  `unknown`, a false confirmation and a missing key refused, a long line cut to 200 by the writer. R10 is skill text,
  pinned by `test_headless_block_writes_nothing`. render-toml reports refusals as "NOT written" warnings with exit 0
  (its phase 33 contract).

## Fix commits

d066f84 and 3ee024d (direct: docs, comments, evals, tests, one-line fix); 997e53a (lane A); e8d523a (lane B, finished by
the reviewer: the lane stopped without a commit because its session-default `render-command` case cannot render, so
that case became a custom lane without `{effort}`); 6273ea9 (direct, docs). Lane runs: pi `router-env/my-coding`,
AIKIT-XAI status=ok, exit 0, attempts 1, cycles 0, elapsed 403 s and 144 s. The real-config audit after each lane found
only host-session files (the Claude Code session, its skill sync, the codex app-server daemon's own logs, a pi session log).

## Open items (not fixed here)

- Todo `.planning/todos/pending/2026-11-21-review-notes-left-open-by-phase-36.md`: the 26 mislabelled baseline entries,
  the pi `known_ids` gap (Phase 37), the duplicates, `ordered_lanes` and the flat-ladder default.
- Judged skills touched after loop 36: `skills/ai-kit-spec-config/SKILL.md` (Step 2.7, one sentence) and
  `references/check-only.md` (three sentences), `skills/ai-kit-spec-execute-superpowers/references/escalation.md` (three
  sentences), `skills/ai-kit-spec-review/evals/evals.json` (three assertions). Their digests are stale by design until
  their next loop; no judge round was run.
- Grok code stays (detection row, `build_grok_command`, `cursor-agents/grok-worker.md`, spec-config mentions); this
  review added no grok content.
- Folded subjects such as `fix(36-29): 36-29` are for the end-of-phase compaction.
