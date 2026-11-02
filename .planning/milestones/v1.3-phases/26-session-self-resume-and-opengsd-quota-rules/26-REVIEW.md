# Phase 26 code review

Scope: source changed by Phase 26 (base `66baac3`, the commit before 26-01, to the head before this review),
excluding `.planning/` and `tmp/`: the `ai-kit-session-wake` skill and package, the five changed skills' code,
`skills/_shared/ai_kit_rules_common`, `tools/`, `skills/ai-kit-spec-review/references/cross-ai.mjs`, and the tests.

## Method

- Own review with the ponytail lens (simplest correct code, dead code, unsafe edge cases, tests that do not test) and a
  security and robustness pass (atomic writes, shell injection, systemd unit generation, state files, real-home access).
  The `gsd-code-reviewer` agent was not spawned: it writes its own REVIEW.md, which would have dirtied the tree
  while the cross-AI lane ran.
- Cross-AI: `router-env/my-referee-two` through pi (route probed with a PONG first), two read-only lanes with a diff file
  each (A: session wake, hook, tools, runner; B: rules-common, rules-agents, rules-all, execute-gsd, execute-superpowers).
  Both exited 0, tree clean. `my-referee-one` is down; `my-referee-three` was not needed (one judge is enough);
  no native Opus.
- Certainty: every cross-AI claim was re-checked by running code against the checkout before being accepted or refuted.

## Findings

Counts: Critical 0, High 0, Medium 2, Low 3 (accepted); refuted 4 (one reported High, two Medium, one Low).

### Accepted

#### M1 (Medium) fire, disarm, done and status crash on an unsafe session id
`skills/ai-kit-session-wake/ai_kit_session_wake/cli.py` (`_pick_target`, `_status`). Only `arm` caught the
`ValueError` from `session_paths`; `fire`, `disarm` and `done` printed a traceback (exit 1) although `main` promises
"every refusal is an exit code", and `status --session-id ../../x` built its state path from the raw flags.
Reproduced with `disarm --session-id a/b`. Fix: validate host and id once in `_pick_target` and `_status` (exit 2).
Found by: own review. Status: fixed in `e14804b` (test `TestStatus.test_unsafe_ids_and_hosts_exit_2_and_touch_nothing`, red before the fix).

#### M2 (Medium) the wake state is not validated for the fields fire indexes directly
`skills/ai-kit-session-wake/ai_kit_session_wake/state.py` (`validate_state`). `pid_start`, `boot_id`, `wake_source`,
`permission_source` and `armed_at` were never checked; `is_alive` and the refresh read them with `[]`, so a damaged
state raised a `KeyError` instead of being removed by name as an invalid state (T-26-40).
Found by: referee-two (its "dead host looks alive" scenario was wrong, the KeyError is what happens; the gap is real).
Status: fixed in `d81251f` (six new `_MUTATIONS` cases in `tests/test_ai_kit_session_wake_fire.py`, all red before the fix).

#### L1 (Low) `$` doubled in `Environment=` values
`skills/ai-kit-session-wake/ai_kit_session_wake/units.py` (`_escape`). systemd does no variable expansion in
`Environment=`, so a `PATH` or `HOME` containing `$` was written as `$$`. A newline in a value was not escaped either.
Found by: own review. Status: fixed in `2cdb228` (`TestServiceEscaping`, red before the fix).

#### L2 (Low) `--reset-at` with a non-ASCII digit raises
`skills/ai-kit-session-wake/ai_kit_session_wake/reset_parse.py` (`parse_reset_at`). `"²".isdigit()` is true and
`float()` refuses it: a `ValueError` traceback. Found by: own review. Status: fixed in `9feabb9` (`test_reset_at_forms` gains the superscript case, red before the fix).

#### L3 (Low) left, not fixed
`_resolve_pid` (`arm.py`) has the same `isdigit` shape for `CLAUDE_PID`; `_refresh_arm` does not catch a state file
that a concurrent disarm removed between its read and `update_state`; `implementer-status`
(`ai_kit_spec_superpowers/cli.py`) assumes the dispatch JSON is an object. All need a hand-damaged environment or a
race against the owner's own disarm, none loses data. Status: left (Low).

### Refuted (cross-AI claims)

#### R1 (reported High) failed first arm unlinks a directory
Claim: `_rollback_first_arm` raises `IsADirectoryError` on the wants symlink and aborts the rollback.
Refuted: the path is `<unit dir>/timers.target.wants/<timer>`, a leaf entry; `os.unlink` of a missing leaf raises
`FileNotFoundError`, which `contextlib.suppress(FileNotFoundError)` in `_rollback_first_arm` (`arm.py`) catches; an
existing symlink is simply removed. The unit directory is never the unlink target. No change.

#### R2 (reported Medium) atomic replace leaves files world-readable
Claim: `mkstemp` uses the umask. Refuted: `tempfile.mkstemp` always creates the file 0600 (documented). Run with
`umask 022`: `write_json_atomic` gives mode 0600 on the first write and on the rewrite
(`state.py` `_atomic_write`). No change.

#### R3 (reported Medium) Maven row signal and count flag use `-t` instead of `-T`
Claim: the clause `mvn -T 0.4C test` never matches `-t 0.4c`. Refuted: `_row_hits` and `hardcoded_worker_counts`
compare against lower-cased text and lower-cased flags (`classification.py` `_stack_form_finding`, `_flag_pattern`
call `.lower()`). Run: `mvn -T 8 test` and `mvn -T 2C test` are flagged, `mvn -T 0.4C test` is not, and the clause
contains `-t 0.4c` once lower-cased. No change.

#### R4 (reported Low) `%h` specifier in `Description=`
Claim: a session id such as `100%h` changes the unit text. Refuted: `SESSION_ID_RE` is `^[A-Za-z0-9_-]{1,128}$`
(`state.py`), so `%` is refused before any unit is rendered; the host comes from the `HOSTS` table. No change.

## Checked and fine

- No `shell=True`; every subprocess is an argv list with the seams env; the hook runs the shim as an argv list and
  kills its process group at the deadline.
- State, unit and marker writes all go through `_atomic_write` (mkstemp, fsync, `os.replace`, 0700 directory); the lock
  file is created once with `O_EXCL` and the locked inode is re-checked.
- Runtime modules import only the stdlib and sibling `ai_kit_*` packages; no absolute machine path in repo files; the
  real home is reached only through the seams env (tests use scratch roots).
- The OpenGSD probe runs the project's own gsd-tools only when `.planning/` exists, with a PATH/HOME-only env, prints
  the path, and `AI_KIT_SKIP_GSD_PROBE` skips it.
- `ruff`, `pyright`, `pylint` pass on the reviewed tree before the fixes.

## Fix status

- M1 fixed `e14804b`, M2 fixed `d81251f`, L1 fixed `2cdb228`, L2 fixed `9feabb9`; each commit carries its test.
- L3 (three Low edge cases) left, reasons above.
- R1-R4 refuted with file evidence; no change.
- Gates after the fixes: `make test-unit` 61/61 modules plus 1/1 uv module, `make arch-test` 66 tests, `make pyright`,
  `make ruff` and `make validate` green.
