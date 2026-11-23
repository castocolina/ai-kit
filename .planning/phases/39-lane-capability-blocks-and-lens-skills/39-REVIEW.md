---
phase: 39-lane-capability-blocks-and-lens-skills
reviewed: 2026-11-23T16:30:00Z
reviewed_head: 83d7b98
diff_range: "04fd6ca..83d7b98 (excluding .planning and tests/fixtures/cross_ai_selftest_secs.json)"
depth: standard (deep on capability_block, prompt_guard, lens_delivery, skill_table, edit_pass and the config writers)
files_reviewed: 30
findings:
  critical: 0
  high: 1
  medium: 7
  low: 17
  info: 8
  total: 33
fixed: 13
deferred: 12
kept: 0
status: fixed_or_tracked
---

# Phase 39 code review

Three passes over `04fd6ca..83d7b98`: the cross-AI review lanes of `.planning/config.json` (referee-one and
referee-two, opencode with `router-env/my-referee-one` and `router-env/my-referee-two`, each run once through
`.planning/scripts/cross-ai.mjs --mode review` after a one-word probe), the executor's own read of the Python modules, the
runner's new `laneCapabilities` block and the docs against the code, and the open-item list the run ledger and the plan
summaries carried. Every finding below was checked in the code or with a recorded run before it was rated; the
lanes' severities were re-rated where the code showed a narrower reach.

Lanes: both probes answered. referee-one returned 17 findings in the asked format (3 high, 13 medium, 1 low as it rated
them). referee-two exited 0 but returned no finding: its answer is a transcript of tool calls whose results it invented
(it quoted functions `ponytail_name` and `skill_rows` and a test body of `test_control_chars_match_python` that exist
nowhere in the checkout). It is recorded as a failed lane and was not substituted; its one concrete claim (the runner's
`PROMPT_CONTROL_RE` is not pinned to the shared fixture) is refuted by the self-test case at
`cross-ai-selftest.mjs:10350-10356`, which checks every code point of `tests/fixtures/prompt_control_chars.json`.

Fixes went in as neutral-scope `fix(39)` commits with their tests (hooks ran on each, never skipped): `575382a`,
`ac668fe` and `2a49b04` (pre-fold shas; the review checkpoint folds them). Thirteen tests (fourteen runs) were run on the version of
their product file before the fix and failed there, then passed on the fix (`tmp/review-39/red_proof.py` and
`red_proof2.py`, not committed): `test_symlinked_install_keeps_the_shared_path`, `test_skill_roots`,
`test_relative_override_is_checked_and_embedded_absolute`, `test_control_char_file_refused_with_all_rejections`,
`test_other_worktree_document_runs_with_note`, `test_execute_without_files_keeps_the_confinement_sentence`,
`test_accept_keeps_edits_and_drops_record`, `test_other_commands_never_load_the_sort_module`,
`test_invalid_name_and_role_refused`, `test_confirm_skill_role_writes_same_entry`, `test_render_toml_cli_holds_the_lock`,
`test_id_carried_bracket_is_unknown` (twice: the context key, then the bare bracket) and
`test_lock_leaves_no_folder_after_a_failed_write`. The native-lane, draft-versus-final and pending-record tests
strengthen coverage of code that was already right and had no red run. No
runner template, SKILL.md or reference text changed, so the live runner copy stays a pristine render; the code changes
under `skills/ai-kit-spec-review/` and `skills/ai-kit-gsd-curated-config/` leave those two skills' judge digests stale
by design until their next loop. Deferred items and owner decisions are in
`.planning/todos/pending/2026-11-23-review-notes-left-open-by-phase-39.md`.

## High

### HIGH-1: a symlinked skill install refused every subprocess review outside the ai-kit checkout (fixed, 575382a)

`skill_table.skill_roots` returned only the real paths of the host skill roots. ai-kit's installer links each skill
directory into a host root (`<host root>/ai-kit-spec-review` points at the clone), so the real path of the checklist
`SKILL.md` and of the seed framework profiles lies outside every root unless the project is the ai-kit checkout
itself. The review skill passes `"<CHECKLIST_SKILL_MD>"` in `--files` (SKILL.md Step 1, point 3), so every subprocess
review lane in any other project was refused with exit 65 `path_outside_roots`, and `SHARED_TOOLING_PATH` was omitted
from every block (`guidance_paths`, capability_block.py:527). Reproduced with a scratch HOME holding the two skills as
links and a scratch git project (`tmp/review-39/probe_roots.py`: `path_outside_roots` for the checklist, the shared path
omitted). `skill_roots` now adds the real path of each skill directory the scan found (the curated inventory and the
`skill-table` JSON are unchanged); a SKILL.md linked out of a real in-root directory and a link inside the repository
are still outside (existing tests). New tests run `guidance_paths` unpatched against the real resolvers
(`TestGuidancePathsUnpatched`); `test_skill_roots` pins the linked directory. The same roots feed two other readers, so
a linked lens directory now passes `check_lens` (it was `path_rejected`) and `classify-skills` now sends a linked skill's
description to jev (it sent the name alone); both follow from the same reading and have no test of their own. A dated
note in 39-SPEC R8 records the reading; the owner confirms it (todo).

## Medium

### MEDIUM-1: the other-worktree allowance applied to execute lanes too (fixed, 575382a)

`_lane` computed `_doc_worktrees` for every `--files` list (capability_block.py:544), so a `dispatch-execute` or
edit-pass file in a sibling worktree of the same repository passed. The orchestrator decision allows it for the
documents of a labeled multi-worktree review only; the lookup now runs for review lanes only, and
`test_other_worktree_document_runs_with_note` adds the execute refusal. Within one review every value is a caller-named
review file, so the allowance stays shared across that list (as the docs say). (referee-one F1, rated high by the lane.)

### MEDIUM-2: project-layer `[skills.roles]` needs no trust step (deferred, owner decision)

`user_roles` reads `[skills.roles]` from the project layer like `[models]` and `[runner]`; only command-bearing lanes
are trust-gated (config_io.py:568-591), so a cloned project can pick which installed skill bodies are inlined into its
lanes' prompts. That follows the layered-config design; changing it is an owner decision (todo). (referee-one F2, rated
high by the lane: the content goes only to the owner's own configured lanes.)

### MEDIUM-3: a relative AGENTS_TOOLING_PATH was checked against one file and embedded as another (fixed, 575382a)

`resolve_agents_tooling_path` accepts a relative override that exists from the process's cwd; `guidance_paths` validated
it relative to the repository and embedded the relative spelling, which the lane resolves from its own cwd. Both paths
are now made absolute first, then checked and embedded (`test_relative_override_is_checked_and_embedded_absolute`).
(referee-one F4.)

### MEDIUM-4: `dispatch-execute` without `--files` lost the soft-confinement sentence (fixed, 575382a)

Decision (b) keeps a dispatch without `--files` as before (no block, one stderr note), but the sentence now rode only the
block, so those calls lost an instruction they always had. With no preview the lane's write reach is unknown, which
D-04 gives the sentence: `build_execute_guidance` now places it between the reinforcement and the task, and no composer
runs (`test_execute_without_files_keeps_the_confinement_sentence`). On that path a codex lane now gets the sentence too,
which the pre-39 builder skipped for codex (`OS_SANDBOXED_EXEC`); an extra write-only-here instruction is harmless.
(referee-one F5; found by both passes.)

### MEDIUM-5: an effort-only cursor bracket dropped the known window (fixed, 575382a, 2a49b04)

`window_for` read any bracket suffix in the model id as an applied context form (prompt_guard.py:154), so
`model[effort=high]` lost its catalog window and was never capped. The window now stays unknown unless the bracket is
provably not a context form: every entry is `key=value` with a key other than `context` (`[effort=high]`,
`[effort=high,fast=false]` keep the catalog value; `[context=1m]`, `[effort=high,context=1m]`, a bare `[1m]` and `[=x]`
stay unknown). The first fix (`575382a`) counted only `context=` brackets, which would have capped a bare `[1m]`; the
second closes that. Only cursor's row has a bracket suffix (`detection.RUNTIMES`). (referee-one F7.)

### MEDIUM-6: `render-toml --out` did not take the folder lock it claims to share (fixed, ac668fe)

`cfg_folder_lock` was added to `cfg_write_toml` and `confirm_role`, but `_cmd_render_toml` publishes with
`toml_splice.publish` directly, so a render racing a confirm could drop the confirmed `[skills.roles]` entry; the old test
called `cfg_write_toml`, which no command calls. The read, migration and publish now run under the lock
(`test_render_toml_cli_holds_the_lock`). (referee-one F13.)

### MEDIUM-7: `confirm-skill-role` echoed the secret-shaped name it refused (fixed, 575382a)

The refusal printed `args.name!r` raw; it prints the redacted form now, and the handler also checks the role (the GSD
config skill's parser has no choices list, LOW-4). Test: a synthetic token appears in neither stream. (referee-one F16.)

## Low

- LOW-1 (fixed, 575382a): a NUL in a `--files` value reached `os.path.realpath` in `_doc_worktrees` before the validator
  and raised `ValueError` ("embedded null character") instead of a `value_control_char` refusal (`probe_nul.py`); values
  with a control character are skipped there now (the validator rejects them).
- LOW-2 (fixed, ac668fe): `edit-lens-pass --accept` or `--reject` with nothing waiting created the record folder for its
  lock and left it empty; `_decision_lock` no longer creates it.
- LOW-3 (fixed, 575382a): `test_lens_fits_draft_not_final` sized the window with the raw file bytes, so the planner's
  larger prose count skipped the lens before the final retry; it now uses the planner's count and asserts the preview
  ran with the lens flags and then without. (referee-one F17.)
- LOW-4 (fixed, ac668fe): every curated-config command loaded the review package's `skill_classify` while building its
  parser, and `load_ai_kit_spec_module` catches only `ImportError`, so a broken or newer sibling broke `ensure-project`
  and the rest. The two flags are registered without loading the module; the handler loads it and checks the role.
- LOW-5 (fixed, 575382a): `test_native_lane_gets_lens_lines_only` asserted a substring (39-12's open item); it compares the
  whole native block (the SKILLS lines only).
- LOW-17 (fixed, 2a49b04): `cfg_folder_lock` creates the config folder before the write; a refused or failed
  `confirm-skill-role`, and since MEDIUM-6 a failed `render-toml --out`, left an empty folder behind. The lock now
  removes a folder it created while it is still empty (`test_lock_leaves_no_folder_after_a_failed_write`). No read-only
  or check path takes the lock.
- LOW-6 (deferred): the edit pass snapshots before the runner's execute lock. (referee-one F3, rated high by the lane.)
- LOW-7 (deferred): the edit pass misses an already-dirty unapproved file the lane changed (documented limit).
  (referee-one F6.)
- LOW-8 (deferred): `capability-block` takes runtime, model and role only, so a non-default lane's block differs from its
  dispatch's. (referee-one F8.)
- LOW-9 (deferred): the summaries preview the bare argv, before lens and MCP planning. (referee-one F9.)
- LOW-10 (deferred): `capability-block` writes and removes a temporary MCP file, and its block names a route a GSD hook
  does not pass. (referee-one F11.)
- LOW-11 (deferred): a SIGTERM skips the MCP folder cleanup. (referee-one F12.)
- LOW-12 (deferred): pi `--exclude-tools` patterns are read as names in `toolListCaps` (runner template; no formula
  emits one). (referee-one F14.)
- LOW-13 (deferred): a non-UTF-8 checkout path raises out of the composer. (referee-one F15.)
- LOW-14 (deferred): `edit_pass.record_path` with no HOME and no XDG_STATE_HOME is cwd-relative.
- LOW-15 (deferred, owner decision): a learned framework profile under the profile cache is outside every root, so a
  cross-AI review that embeds it is refused (the SKILL says to rerun with `--no-cross-ai`).
- LOW-16 (deferred): the checklist SKILL.md calls `TOOL_AVAILABILITY` the tools installed "on this machine"; the block
  lists the lane's own PATH. A judged skill outside the diff.

## Info (checked, no change; INFO-2 became LOW-17)

- INFO-1: `check-reviewer` still runs its live probe before the `capability` key (referee-one F10): SPEC R11's amendment
  makes the summary one more key of that command's object; the summary itself spawns no lane.
- INFO-3: `ponytail_visibility` from `root_rows` skips `scan_root`'s other checks: for the names it reads they are
  equivalent (both require a `SKILL.md` that is a file; `_real_dir` only fails where `isfile` already did). 39-09's
  SUMMARY records the change; a deviation line it missed (the synthetic jev pin in the parity test) is added there.
- INFO-4: `laneCapabilities` shares one frozen `CAP_UNKNOWN` object; JSON output is unaffected and nothing mutates it
  (todo, at the next template change).
- INFO-5: 39-12 merged plan-named tests: `test_window_over_and_unknown` keeps both assertions (reason, `detail.window`,
  an unknown window on a 1,000,000-byte prompt), `test_lens_delivered_and_skipped` both (runner name in the flags, the
  `over_window` skip).
- INFO-6: 39-14's two plan-named tests: the diff-before-hint order is in `test_reject_restores_non_utf8_bytes` (the
  edited lines, then the hint as the last line); a pending (ready) record blocking a second run had no test and now has
  `test_pending_record_blocks_a_second_run`.
- INFO-7: the native and custom compose branches skip the window check: a native lane is never spawned by the dispatch,
  and a custom lane has no runtime, so its window is unknown (never capped).
- INFO-8: the spec-review file-size item is a known owner item (a SPEC amendment is needed) and was not changed.
- INFO-9: the added lines name no grok, no absolute home path and no model literal outside `fake/<x>`,
  `placeholder-model-<n>` and `router-env/<x>` (`tests.test_arch_hardcoded_models` ran in both commit hooks).

## Not read

The executor read the diffs of the Python modules, the runner's `laneCapabilities` hunk and the SKILL.md capability
section; it did not open the self-test harness cases (beyond the control-character case), `README.md`,
`docs/config/design.md`, the spec-config SKILL.md, `check-only.md` and evals, `tooling-guidance.md`,
`reviewer-prompts.md`, `apply-findings.md`, the cross-ai SKILL.md hunk, `jev_names.py`, the `.pre-commit-config.yaml`,
`Makefile` and `run_unittest_parallel.py` hunks, or the test modules `test_runner_preview`, `test_runner_skills_argv`,
`test_capability_entry_points`, `test_cross_ai_docs_text` and `test_runner_flags` beyond what a fix touched. referee-one
cited some of them (its findings above); referee-two's lane read nothing usable.

## Tests run on the fixes

Each commit's hook: 141/141, 144/144 and 141/141 covering modules (the 12 self-test shards, runner e2e, curated-config
e2e and apply e2e, config doctor under uv among them); the red proof (13 tests, above); `make pyright` and
`make vulture` passed on the whole tree, `make check-dogfood` ends `check-dogfood: ok` (stale-digest notes only), the
39 SPEC edge floor is `ok` (68 of 68 rows); then, under the guard at `2a49b04`, 13/13 modules: the curated-config matrix
(35 tests, 147.5 s), `tests.test_curated_config_e2e` (21), `tests.test_curated_config_apply_e2e` (8),
`tests.test_ai_kit_gsd_curated_config` (104) and the nine `tests.test_config_*` modules (callers 10, design record 11,
dir parity 10, doctor 85, herdr identity 4, layers 54, migrate 57, role write 18, status 25), none killed.
