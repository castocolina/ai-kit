---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
reviewed: 2026-11-26T15:11:09Z
depth: standard
files_reviewed: 44
files_reviewed_list:
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - skills/ai-kit-spec-review/references/cross-ai-selftest.mjs
  - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
  - skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py
  - skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py
  - skills/ai-kit-spec-review/ai_kit_spec/host_config.py
  - skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py
  - skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py
  - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
  - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
  - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/session_pick.py
  - skills/ai-kit-spec-execute-superpowers/SKILL.md
  - skills/ai-kit-spec-execute-superpowers/references/escalation.md
  - skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md
  - skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md
  - skills/ai-kit-spec-execute-superpowers/references/state-management.md
  - skills/ai-kit-spec-execute-superpowers/references/config-check.md
  - skills/ai-kit-spec-execute-superpowers/references/quota-wake.md
  - skills/ai-kit-spec-execute-superpowers/references/session-wake.md
  - skills/ai-kit-spec-execute-superpowers/evals/evals.json
  - skills/ai-kit-spec-execute-superpowers/evals/files/escalation-off/project/aikit/config.toml
  - skills/ai-kit-spec-execute-superpowers/evals/files/flagged-quota/project/aikit/config.toml
  - skills/ai-kit-spec-execute-superpowers/evals/files/session-fallback/project/aikit/config.toml
  - skills/ai-kit-spec-config/SKILL.md
  - skills/ai-kit-spec-config/evals/evals.json
  - skills/ai-kit-spec-config/references/config-file.md
  - skills/ai-kit-spec-config/references/free-lanes.md
  - skills/ai-kit-spec-config/references/headless.md
  - skills/ai-kit-spec-config/references/wizard-flow.md
  - skills/ai-kit-cross-ai/SKILL.md
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py
  - skills/ai-kit-gsd-curated-config/references/runner.md
  - README.md
  - Makefile
  - tools/run_unittest_parallel.py
  - tests/test_adapter_escalation_flags.py
  - tests/test_adapter_executor_switch.py
  - tests/test_adapter_session_fallback.py
  - tests/test_adapter_single_definitions.py
  - tests/test_host_config_audit.py
  - tests/test_dispatch_guidance_gates.py
  - tests/test_lane_settings.py
  - tests/test_arch.py
findings:
  critical: 1
  warning: 4
  info: 7
  total: 12
  necessity: 0
status: issues_found
---

# Phase 41: Code Review Report

**Reviewed:** 2026-11-26T15:11:09Z
**Depth:** standard
**Files Reviewed:** 44
**Status:** issues_found

## Summary

Scope: the source changes in `1420a53..af30cc2` excluding `.planning/` (60 files). Read against `41-SPEC.md`,
`41-CONTEXT.md`, `41-REVIEWS.md` (including the "Open concerns after cycle 2" list) and the deviation notes in the
`41-*-SUMMARY.md` files. The owner decisions of 2026-11-25 apply: EXE-09 is confirmed for execute lanes, and
`EXEC_PREAMBLE` stays unchanged.

Most of the phase holds up when traced through the connected code:

- **Real-home guard.** `aiKitCheckout` in `cross-ai.mjs:5322-5331` stops at the first `.git` and needs both markers. It
  applies only to `--mode exec` and overrides an inherited value (`:5764`). The resulting `env` reaches both the headless
  spawn (`runOnce`, `:6010`) and the herdr path (`childOpts.env` → `hostedChild` → `writeRunDir` → the `env` file that
  the launcher sources, `:4818-4819`).
- **Self-test harness.** `hermeticEnv` (`cross-ai-selftest.mjs:1691`) builds the environment from scratch. So the
  positive cases prove that the runner itself set the variable; it was not inherited.
- **Executor switch.** It acts only on the runner's own evidence. `quota_evidence` reads `status.status == "quota"`,
  or a `reason == "quota"` that `runner_dispatch._runner_reason` derives only from a trailer that counts or from an exit
  code. A transient or capacity result never switches.
- **Host-config audit.** It only calls `stat` and never opens a listed file. It never changes a result's return code,
  and a native run always exits 0.
- **Session fallback.** It is gated three ways:
  - `--fix-round >= 4`, escalation keys or `--no-fallback` skip it (`cli.py:272`);
  - a flag that is off prints the spec-config line;
  - a non-boolean flag exits 2.
- **jev.** jev gets only the task-type summary, with `cwd` bound to the project.
- **Stdlib and atomic writes.** Every new runtime module is stdlib-only. The config write goes through the existing
  atomic `render-toml` path.

Key concerns:

- **CR-01 (critical).** The executor's flagged switch runs on any classified quota stop, fix rounds 4 and 5 included. It
  never consults the escalation gate. A round-4 bump that hits quota can therefore re-dispatch the stuck anchor, or a
  lane the anchor's flags forbid. This was reproduced against the real helpers.
- **WR-01.** The commit guard's clean-tree command is relative to the working directory. Run from a subdirectory, it
  reports a clean tree that is not clean (probed with real git).
- **WR-02.** The arch test's cross-skill frozen list grew by one row. Its own comment says the list may only shrink.

Not assessed:

- The skill-judge records, because plans 41-13 and 41-14 have no SUMMARY at this commit.
- Live eval execution.
- These diffs were not read: `tests/test_ai_kit_spec_superpowers.py`, `tests/test_lane_failure_text.py`,
  `tests/test_spec_chain_text.py`, `tests/test_spec_config_flow_text.py`, `tests/test_ai_kit_spec_check_providers.py`,
  `tests/test_curated_config_script.py`, the regenerated `tests/fixtures/cross_ai_selftest_secs.json`,
  `tests/fixtures/runner_describe_golden.json`, `.pre-commit-config.yaml` (generated group comment) and the seven curated-config golden fixtures (template number only).

Necessity: `necessity-review.md` was read. No necessity finding: the new guards sit at trust boundaries (CLI arguments,
snapshot files, environment, hand-edited TOML), or exist for pyright narrowing.

Runs made for this review: `tests.test_adapter_executor_switch` and `tests.test_adapter_escalation_flags` (2/2 modules
passed), and the runner self-test cases `realhome-exec-checkout-subdir`, `realhome-exec-plain-repo` and
`realhome-exec-linked-worktree` (`self-test ok`). Scratch repros sat under `tmp/p41-review/`; their output is quoted
below.

## Critical Issues

### CR-01: The flagged executor switch bypasses the rounds 4–5 escalation gate

**Files:** `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:176-224`,
`skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:674-691`,
`skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:46-62` (via `lane_settings.py:157-160`)

**Issue:**

- **Where the switch runs.** The **Flagged switch** step runs "for every classified quota_cycle and quota". It has no
  fix-round condition and never reads `$RUN_DIR/ESCALATION_ALLOWED_JSON.json` or `ESCALATION_EXCLUDE_JSON.json`.
- **What `executor-fallback` excludes.** Only `EXCLUDED_KEYS_JSON` plus roster keys outside the task's `ladder_keys`.
- **How the fallback is picked.** `next_lane` → `lane_fallback` → `_fallback_from` scans the whole role order from the
  top. It returns the first unflagged lane of another pool, whether that lane ranks above or below the anchor.
- **What the switch block then does.** Its re-resolve checks only that the key equals `SWITCH_KEY`. The allowed-key
  check in `escalation.md:94-97` is never re-run.

This contradicts:

- the owner's decision of 2026-11-23 (1): "a stuck task escalates only along an enabled flag" (SPEC Background, R2);
- `escalation.md:88`: "A real candidate ... of the automatic round ... must be a key the gate allowed";
- `resolution-stops.md:71`: "Never dispatch a same-or-weaker candidate as a substitute";
- `resolution-stops.md:83`: "a re-resolved key the gate did not allow ... dispatch nothing".

**Failure scenario (reproduced with the real `escalation_gate` and `lane_switch.fallback_outcome`):**

1. The roster is `lane-top` (opencode, `usage_limited`, pool `prov:free`) above `lane-anchor` (codex,
   `escalate_runtime`). `lane-anchor` is stuck at round 4.
2. The gate prints `{'escalate': True, 'allowed': ['lane-top'], 'exclude': ['lane-anchor'], ...}`. Round 4 dispatches
   `lane-top`, which stops on quota.
3. Relay folds `lane-top` into `EXCLUDED_KEYS_JSON`. `fallback_outcome` then returns `lane-anchor ''`, and
   `switch target allowed by the gate: False`.
4. The switch block re-resolves with `--escalation-excluded-keys-json ["lane-top"]`, gets `lane-anchor`, sets
   `SWITCHED=1` and dispatches the stuck lane again as the round-4 "bump".

Second case (repro output `gate2 ... 'reason': 'off'`, `switch2: lane-other '' allowed: False`): both flags are off and
the anchor itself is flagged. A quota stop moves the stuck task to another runtime at round 4, although its flags allow
no move.

**Fix:** At an automatic rounds 4–5 round, the switch must stay inside the gate.

- When `$FIX_ROUND -ge 4` and `$RUN_DIR/ESCALATION_ALLOWED_JSON.json` exists, pass the gate's exclude set to
  `executor-fallback`, for example a new `--escalation-exclude-file` merged into `exclude` in `_cmd_executor_fallback`.
- Run the allowed-key check on `SWITCH_KEY` before the move. With no allowed fallback, `SWITCHED=0` and the owner stop
  applies.
- Add a fake-lane test with the two rosters above.

```bash
ESC_ARGS=()
if [ "${FIX_ROUND:-0}" -ge 4 ] && [ -f "$RUN_DIR/ESCALATION_EXCLUDE_JSON.json" ]; then
  ESC_ARGS=(--escalation-exclude-file "$RUN_DIR/ESCALATION_EXCLUDE_JSON.json")
fi
python3 "$SHIM" executor-fallback ... "${ESC_ARGS[@]}" > "$RUN_DIR/SWITCH_JSON.json" || SWITCH_RC=$?
```

## Warnings

### WR-01: The commit guard's clean-tree command gives a false clean from a subdirectory

**File:** `skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py:92-97`

**Issue:** The guard tells the implementer to judge cleanliness with `` `git status --porcelain -- . ':!<path>'` ``.
Both `.` and `:!<path>` resolve against the working directory. An implementer that has `cd`'d into a subdirectory sees
only that subdirectory, so edits elsewhere are hidden. In a scratch repo with untracked `other.txt`, `sub/x.txt` and
`.aikit/config.toml`, running from `sub/` printed only `'?? sub/\n'` (`other.txt` is missing). The runner's own
exclusion already uses a top-anchored literal pathspec for this reason (`cross-ai.mjs:5353`,
`:(top,exclude,literal)`).

**Fix:** Emit a top-anchored literal form. Probed: from `sub/` it prints `'?? other.txt\n?? sub/\n'`, and from the root
the same.

```python
excludes = " ".join(f"':(top,exclude,literal){p}'" for p in owner_config_paths)
text += ("... a clean-tree check leaves them out: `git status --porcelain -- ':(top)' " + excludes + "`.")
```

`literal` also makes the leading-character and glob rejections of `_unsupported_owner_config` unnecessary (see IN-02).
The apostrophe and newline checks still matter for the shell quoting.

### WR-02: The cross-skill frozen list grew, against the rule that it may only shrink

**File:** `tests/test_arch.py:1617-1620,1668-1671`

**Issue:** The allowlist comment at `tests/test_arch.py:1564-1567` says: "The list may only shrink: `_CROSS_SKILL_FROZEN`
is the set it is checked against". Phase 41 adds a new module, `session_pick.py`, that imports `ai_kit_spec`, and adds
a row for it to both the allowlist and the frozen set. The freeze exists to stop new cross-skill edges. Adding the row
by hand defeats it, and the next agent can copy the pattern. `dispatch_injection.py`, which is already allowlisted, is
the only caller of `pick_session_model` (`dispatch_injection.py:38,210`).

**Fix:** Move `SESSION_PICKS`, `PICK_QUESTION` and `pick_session_model` into `dispatch_injection.py`. Alternatively, put
the picker in `ai_kit_spec` and import it from the existing allowlisted module. Then drop both new rows.

### WR-03: `GUIDANCE_READY` outlives the run and reuses stale gates and guard files

**File:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:237` (with `:125-126` and `:282`)

**Issue:**

- **Write rule.** The gates and guard files are written only when "the loaded scalar `GUIDANCE_READY` is not
  `$TASK_N`".
- **Lifetimes.** The scalar file is per plan (`superpowers-run-${PROJECT_KEY}-scalars.env`), and `RUN_DIR` is a
  persistent folder in the cache directory.
- **Cleanup.** Step 5 clears only `FOLD_BASE` and `UNIT_FLOW`. Nothing clears `GUIDANCE_READY` when a run ends or a new
  run starts. `config-check.md` clears its own `CONFIG_CHECK` on a fresh start; this scalar has no equivalent.

**Failure scenario:** A plan runs to its last task N; the scalar file ends with `GUIDANCE_READY=N`. The owner edits the
plan's verify lines or the instruction file's gates, then re-runs the plan. Tasks 1..N-1 rewrite their files, but task
N finds `GUIDANCE_READY == N` and reuses the old `gates.txt` and `guard.txt` from the earlier run. A single-task plan
always reuses them.

**Fix:** Clear the scalar where a run starts fresh, and when the resume state is seeded (`printf 'GUIDANCE_READY=\n'`
in the "Seed a new task" block when `SEEDED_TASK` is another task). Better: key the scalar on the run, for example
`GUIDANCE_READY=<TASK_N>@<FOLD_BASE>`.

### WR-04: `escalation-gate` exits 2 for an anchor dropped from the roster, which the docs do not list

**Files:** `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:615-622`,
`skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:203-205`,
`skills/ai-kit-spec-execute-superpowers/references/escalation.md:55`

**Issue:**

- **The case.** The anchor is still in the saved `ladder_keys`, but the owner has since removed its lane from the live
  roster.
- **What the code does.** `escalation_candidates` raises `LaneSettingError("<anchor>: not an execute lane")`, a
  `ValueError` subclass caught first. The command exits 2.
- **What the docs say.** `escalation.md:55` says exit 2 means "a non-boolean flag, or an unreadable injection file", and
  exit 3 means an empty or unknown anchor. `resolution-stops.md:70` defines the unknown anchor as "the config changed"
  and routes it to the owner-pick question.
- **The effect.** A changed config can thus land on the generic exit-2 stop. The owner is never offered the pick that
  the docs promise for exactly that situation.

**Fix:** In `escalation_gate`, treat an anchor missing from the live roster like one missing from `ladder_keys`
(raise `ValueError("empty or unknown anchor")`, so exit 3). Alternatively, document the third exit-2 cause and its stop.
Add a CLI test: anchor in `LADDER`, absent from the roster, expect the exit-3 STOP line.

## Info

### IN-01: A closed stderr stream replaces the lane's own exception in the audit (executor item 8)

**File:** `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:448-458`

**Issue:** The `finally` block suppresses only `OSError` around `print(line, file=sys.stderr)`. A repro with
`redirect_stderr` to a closed `StringIO` and a fake lane that raises printed:

```text
escaped: ValueError I/O operation on closed file
context: RuntimeError lane broke
```

In `_cmd_dispatch_task` this would turn a `LaneRefused` into a traceback instead of the `REFUSED_EXIT` JSON. A related
point: when Python starts with fd 2 closed, `sys.stderr` is `None`, and `print(file=None)` writes to stdout ahead of the
result JSON. Neither happens with the documented `2> "$DISPATCH_BASE.err"` redirect.

**Fix:** Use `contextlib.suppress(OSError, ValueError)`, and skip the print when `sys.stderr is None`.

### IN-02: The shared guard builder trusts its paths; only the adapter CLI validates them (executor item 10)

**Files:** `skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py:82-97`,
`skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:413-429`

**Issue:** `build_commit_guard_guidance` wraps each path in raw single quotes and pathspec magic. The quote, magic and
glob checks live only in the superpowers CLI, which is today's single producer (`grep owner_config_paths`). A future
`ai-kit-spec-execute-*` adapter calling the shared builder directly would emit broken shell text for a path with an
apostrophe. The rejection list itself is sound; the real-git probe confirmed that `_x` dies with `Unimplemented
pathspec magic`, and a path with a space and a colon works. But with `literal` magic (WR-01) the list could shrink to:
non-empty, relative, no `..`, no apostrophe, printable.

**Fix:** Move `_unsupported_owner_config` beside the builder in `dispatch_guidance.py` and call it there.

### IN-03: The two gate files are not written all-or-nothing

**File:** `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:589-605`

**Issue:** If the second `os.replace` fails, the new `ESCALATION_EXCLUDE_JSON.json` sits beside the previous round's
`ESCALATION_ALLOWED_JSON.json`, and `.tmp` files stay behind. `escalation.md:55` says that "only on success does it
write" both. The impact is small because the block stops on the exit 2, but a stale allowed file is what the owner-pick
path deletes on purpose.

**Fix:** On failure, remove both `.tmp` files and any file already replaced in this call. Alternatively, write one JSON
object holding both lists.

### IN-04: Two tests claim more than they check

**Files:** `tests/test_dispatch_guidance_gates.py:93-101`, `tests/test_dispatch_guidance_gates.py:606-623`

**Issue:**

- `test_supported_path_excludes_only_that_file` compares the guard text only and runs no git. The cwd defect of WR-01
  passes it.
- `test_unpinned_resume_writes_the_files_on_first_dispatch` writes `gates.txt`, `guard.txt` and `GUIDANCE_READY=2`
  itself, then asserts that the dispatch block passes them on. It proves the hand-off, not "writes the files on first
  dispatch" (that step is prose for the controller).

**Fix:** Rename both tests to what they prove, or add a scratch-repo git run for the first one.

### IN-05: The guard on the herdr hosted path is traced, not tested

**File:** `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs:9405-9513`

**Issue:** All six `realhome-*` cases run headless. The hosted path reaches the guard only through `opts.env` →
`writeRunDir` → `hostEnvText` (`cross-ai.mjs:4889,4818`). The launcher starts with `env -i` and then sources that file
(`:4789-4791`), so a future change that rebuilds the env there would silently drop the guard.

**Fix:** Add one hosted case with the existing fake herdr that asserts `realhome.seen == '1'`.

### IN-06: Owner question: the session fallback also fires on task narrowing (`no_candidate`)

**File:** `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:332-337`

**Issue:** SPEC R3 names three triggers: unavailable, blocked or out of quota. The implementation also falls back when
every configured lane is narrowed out by affinity or context. The test `test_real_narrowing_to_no_candidate_falls_back`
pins this, as planned in 41-04. With the flag on, the curation-gap stop (`resolution-stops.md:37-39`, "report `detail`")
never reaches the owner, and a lane that is healthy but too small is replaced by the session model. This is a design
choice for the owner, not a proven violation.

**Fix:** Confirm with the owner. If narrowing should stay a stop, drop the `_emit_or_fallback` wrapper on the
"no execute candidate survived" branch.

### IN-07: The spec-config JSON example shows `"session_fallback": true` inline (executor item 4)

**File:** `skills/ai-kit-spec-config/SKILL.md:358`

**Issue:** The copyable shape example carries the flag, and only a parenthetical says that only a yes adds it. An agent
that copies the example verbatim writes an opt-in the owner never gave. The NEVER rule at `:45` covers this in prose.

**Fix:** Drop the key from the example and keep the sentence ("on a yes, add `\"session_fallback\": true` to the
execute table").

## Executor items left for review

1. **41-02, `lane-new` added to the roster in `test_unavailable_anchor_is_a_quota_stop`. Confirmed sound.** The gate
   excludes only live-roster keys and `ladder_keys` (`dispatch_injection.py:224-225`). The fake resolver lists
   `lane-new` first, so without it in the roster the resolver would pick it, and the test would show a fixture artefact
   rather than the quota stop. In a real run the candidates come from that same roster. No finding.
2. **`escalation.md` allowed-key block uses `python3 -c` (plan-specified). Confirmed, no defect.** The same file
   (`:74,83`) and SKILL.md (`:163,171,189`) already use `python3 -c` with argv-passed values. The block passes its JSON
   and key as argv, never re-parsed. It fails closed: a missing file makes `json.loads('')` exit 1, which is the STOP.
   The no-inline rule binds agent shell calls in this repo, not the shipped controller text.
3. **The `test_arch` frozen list gained a `session_pick.py` row. Confirmed as a defect: WR-02.**
4. **The spec-config JSON example shows `"session_fallback": true` inline. Confirmed: IN-07.**
5. **A session-fallback test passes the literal `"haiku"` as a fake jev answer. Confirmed, harmless.**
   `test_adapter_session_fallback.py:57,63,203` use the literal. The picker tests iterate `session_pick.SESSION_PICKS`
   (`:67`), and `test_picks_stay_native_selectors` pins the set. The literal is the contract word, not a vendor model
   id. Using `SESSION_PICKS[0]` would remove the duplication. No finding.
6. **41-06's unpinned-resume test writes `"injection_json": null`. Confirmed, harmless.** Restore treats null like a
   missing key (`state-management.md:101-102`, `if inj:`), and the test asserts that no `INJECTION_JSON.json` is
   written. Its name overclaims for another reason (IN-04).
7. **41-07's linked-worktree self-test repeats the path literal. Confirmed, cosmetic.**
   `cross-ai-selftest.mjs:9462,9471`. Also, the `git worktree add` result is unchecked (`:9463`). A failed add surfaces
   as a throw from `fs.statSync` in `check` rather than a named message. No finding.
8. **The audit swallows only `OSError`, and a closed stream raises `ValueError`. Confirmed by repro: IN-01.**
9. **41-10: `_replace(pool=...)` wraps over two lines, and the session-fallback test's config lane differs from the
   resolved flagged lane. Both confirmed, no defect.** The wrap at `execute_dispatch.py:113-115` is style only, and
   `RunnerSpec.pool` reaches `--pool` (`runner_dispatch.py:245-246`, pinned by `TestExecutorPool`). In
   `test_sole_blocked_pool_with_session_fallback_runs_native` (`test_adapter_executor_switch.py:285-300`), the TOML lane
   has no `usage_limited` while the injected candidates use `FLAGGED`. Only the policy flag is read from the file, so
   the test stays valid, but the fixture is inconsistent.
10. **41-05: the owner-config check rejects some leading characters, backslashes and non-printables, after a real git
    probe. Confirmed.** A fresh probe for this review agrees: an apostrophe-free path with a space and a colon is
    excluded correctly. Two caveats, filed separately: the generated command is cwd-relative (WR-01), and the
    validation does not sit with the shared builder (IN-02).

## Resolution

Fix chunk c8-41, 2026-11-26. Every behaviour fix has a test that failed before the fix; the red output is kept in
`tmp/run-2026-11-23/lane-41-RF-fix-<group>/`. PT ids are the findings of `tmp/p41-review/ponytail-review.md`.

Two decisions came from the orchestrator, not the owner:

- **The switch at rounds 4-5.** The flagged quota switch picks only from lanes that pass both rules: the escalation
  gate's floor and the usage_limited switch rule. With no such lane, the switch reports the lane and replaces nothing.
- **The session fallback.** It does not run when task narrowing leaves no candidate. It runs only when no configured
  executor is available.

Two choices were made inside the chunk:

- At round 4 or later with no gate file, the switch block runs no switch.
- `GUIDANCE_READY` is cleared in config-check block 1's fresh-start branch. `FOLD_BASE` was not used as the key,
  because it survives a fold that did not end `done`.

- CR-01: fixed, 981fab5 (`executor-fallback --exclude-keys-file` is repeatable; at round 4 or later the Flagged switch
  passes the gate's `ESCALATION_EXCLUDE_JSON.json` as a second exclude file, and with no gate file it runs no switch).
- WR-01: fixed, 16114c4 (`git status --porcelain -- ':(top)' ':(top,exclude,literal)<path>'`; a real-git test runs it
  from the root and from a subdirectory).
- WR-02: fixed, 91fbc53 (the picker moved into `dispatch_injection.py`, `session_pick.py` deleted, both arch rows dropped).
- WR-03: fixed, e4d799a (a fresh start of the plan clears `GUIDANCE_READY` in config-check block 1).
- WR-04: fixed, 1af985f (an anchor missing from the live roster exits 3 with the owner-pick stop).
- IN-01: fixed, c5f23c7 (the print is skipped when `sys.stderr` is None; `OSError` and `ValueError` are suppressed).
- IN-02: fixed, 425ff6a (the check lives in `dispatch_guidance.py` and the builder runs it; the CLI's exit 2 is unchanged).
- IN-03: fixed, c5f23c7 (a failed write removes both temp files and both gate files).
- IN-04: fixed, 16114c4 (the first test runs real git) and 425ff6a (the second test is renamed
  `test_unpinned_resume_passes_the_recorded_files_to_the_dispatch`).
- IN-05: fixed, f5a8f0a (self-test case `realhome-exec-hosted`; it fails against a copy that drops the variable from the
  hosted env file; its time is not yet recorded in `tests/fixtures/cross_ai_selftest_secs.json`).
- IN-06: fixed, 23e9ab6 (the orchestrator's session-fallback decision: `no_candidate` is never replaced by the session
  model).
- IN-07: fixed, 5ebae05 (the inline example drops the flag; the sentence says where it goes on a yes).
- Executor items 1-10: covered by the items above or confirmed sound; items 3, 4, 8 and 10 are WR-02, IN-07, IN-01 and
  IN-02.
- PT-1: fixed, 981fab5 (the same fix as CR-01).
- PT-2: fixed, 8a7fff8 (one reader on `cache_read_json` for both commands; a missing `ladder_keys` is exit 2 in both).
- PT-3: not taken (kept as defence in depth, as the plan review asked; it costs little).
- PT-4, PT-5, PT-6, PT-7, PT-11, PT-12: done in chunk c9-41 (below).
- PT-8: not taken (plan 41-10 specified `role` as the helpers' role seam).
- PT-9: done in chunk c9-41 (below; 23e9ab6 had already removed one of the two "no execute candidate survived"
  matches).
- PT-10: not taken (the field is kept as the documented result shape for callers).

Fix chunk c9-41, 2026-11-26. The text groups change no test file: every string a test pins stays where the test reads it,
so a cut that would move a pinned string was left out and is named below.

- Stale switch answer (found in the c8-41 close-out): fixed, 806043d (the Flagged switch block deletes
  `SWITCH_JSON.json` first, so a round that ran no switch leaves no earlier answer; the red test is kept in
  `tmp/run-2026-11-23/lane-41-RF-fix-s/red.txt`).
- PT-7: fixed, cf86fee (`_add_guidance_args` adds the three guidance arguments to both parsers).
- PT-9: fixed, 376cf98 (`NO_CANDIDATE_PREFIX` in `dispatch_injection.py`, one match; `_emit_or_fallback` reads
  `loaded.escalation_exclude`).
- PT-11: fixed, 14e9bec (the switched answer of `executor-fallback` carries `exclude`; the block reads it and writes no
  `SWITCH_EXCLUDE_JSON.json`). Five exact-answer assertions gained the new key; none was weakened.
- PT-12: fixed, 118117b (`_kind_matches` is shared by `escalation_target` and a one-line `escalation_candidates` filter).
- PT-4: partly fixed, b203e7a (the recipe's sources, deletes, scalar line and reuse rule moved to
  `state-management.md` "Gates and guard inputs"; the session-fallback paragraph points to the rounds 4-5 sentence; the
  audit's missing-snapshot note moved to `dispatch-external-cli.md`). Body 3808 -> 3627 words. Not done: the clause in
  the rounds 4-5 sentence (pinned verbatim by `test_spec_chain_text` and `test_adapter_session_fallback`) and the audit
  line as a bash block (`test_host_config_audit` pins it as one line).
- PT-5: fixed, a6d734c (the headless, `--check-only`, removed-runtime, migration delete/keep, codex bare-id, flat timeout
  and stderr-capture repeats became pointers; the vendor-less per-mode detail moved to `config-file.md` "Lane entry
  fields"). Body 6481 -> 6253 words. Not done: the `session_fallback` parenthetical, rewritten by 5ebae05 and pinned by
  `test_spec_config_flow_text`.
- PT-6: fixed, 4d3357e (section 8 holds the one statement; section 6 keeps its two pinned phrases and a pointer).
  Body 6372 -> 6355 words.
- IN-05 time: fixed, 5667669 (the self-test times re-recorded on a quiet machine, now holding `realhome-exec-hosted`;
  four `E2E_RECORDED_SECS` entries updated from the shard run).

---

_Reviewed: 2026-11-26T15:11:09Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
