---
phase: 18
fixed_at: 2026-10-15
review_path: .planning/phases/18-cross-ai-skills-apply-pipeline/18-REVIEW.md
scope: "Batch A (CR-01..05, WR-01..13, IN-01..12) + C-IN-09, PT-07/PT-11 (batch A sites), PT-10, PT-15, PT-17, PT-20, PT-22 + optional C-W12 hand-off"
iteration: 1
findings_in_scope: 39
fixed: 38
skipped: 1
status: partial
---
# Phase 18 Batch A: Code Review Fix Report

**Source review:** `18-REVIEW.md`, section "# Batch A", plus the batch A items handed over by `18-REVIEW-FIX-B.md` (PT-07, PT-11 call sites) and `18-REVIEW-FIX-C.md` (C-IN-09, PT-10, optional C-W12), and the ponytail items on batch A files.
**Commit range:** `728f43d..07f2ab9` (24 commits on `gsd/v1.3-curated-config-v2`, after `32c9a42`), plus this report.
**Where verification ran:** in this checkout (`.claude/worktrees/v13-curated-config-v2`). No separate review-fix worktree was used.

**Verification (final tree):**
- `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test`: ok (about 41 s; 31 s before, the added cases account for the rest).
- `make test-unit`: 37/37 modules plus 1/1 uv module pass. `make arch-test`: pass.
- `make e2e-test`, run twice: 7/7 Python e2e modules and 45/45 installer checks pass both times.
- `make ruff pylint pyright vulture`: all pass.
- After every self-test and e2e run, no process with its cwd under an `xai-st-*` dir was left, and no `/tmp/xai-st-*` dir remained. **Leftover processes after the last run: 0.**
- Every behavior change got a failing self-test case or Python test first, confirmed red against the unfixed code (or, for WR-01, WR-06 and the reaper, against a mutated copy).
- CR-04 was also checked under the real `gsd-tools run-with-timeout 3` with a SIGTERM-ignoring fake CLI: the status line was printed with `tree=dirty`, and the CLI was dead.

**Requires human verification** (logic, not just tests): CR-02, CR-03/CR-04, WR-03, WR-06, WR-12, and the codex part of CR-01.

## Fixed

### A-CR-01: stderr noise reclassified a successful run
**Fixed in** `5e7b92d`, codex follow-up `07f2ab9` (requires human verification for codex).
- A clean exit with an answer and no structured error is `ok`. stderr patterns only name a failure: a nonzero exit, a structured error, or an empty answer.
- Cases `okwarn` (503 and "wrote 401 lines" on stderr) and `empty-auth`.
- Codex: a stream `error` event followed by `turn.completed` no longer counts; `turn.failed` always does. The event shape is assumed, not live-verified (shortcut comment).

### A-CR-02: retry-later on a dirty or unknown tree
**Fixed in** `ac678cc` (requires human verification).
- The router-backed billing override runs first. Then any `fallback` or `retry-later` on a tree that is not clean becomes `stop`.
- Design choice: the exit code still names the status class (75 for quota). The status/exit table is a stable contract (D-30), and `action` is the instruction.
- A failed run whose tree cannot be read afterwards ends `unverified` (exit 1, stop).
- Cases `dirty-quota`, `dirty-billing-router` and `git-after-quota`.

### A-CR-03 / A-CR-04 / A-IN-05 / A-IN-08: the signal path
**Fixed in** `b463da0` (requires human verification).
- The handler only arms the abort. Every remaining wait is capped by a 2.5 s signal budget, inside run-with-timeout's 3 s grace.
  - Backoff sleeps wake up.
  - The running child gets SIGTERM, a 1 s grace, then a group SIGKILL before a 0.5 s drain. The grace is chosen when finalize runs.
- A second signal SIGKILLs the current group at once.
- `main()` reads the tree again and prints `status=signal` with the real state. `liveFields.tree` is `unknown` from each CLI spawn until a snapshot says otherwise.
- A backstop prints the line, kills the group and drops tracked temp dirs if `main` cannot finish in time. The temp dirs fix IN-05.
- `current` is now used (IN-08).
- Cases `sigterm-stubborn` (CLI ignores SIGTERM: exits within 2.9 s, `tree=dirty`, CLI dead), `sigterm-twice` and `sigterm-backoff`.
- `sigterm-hang` now expects `tree=dirty`, which is correct: the fake writes an untracked `gc.pid`.

### A-CR-05: the backoff slept past the deadline
**Fixed in** `7bd6a91`.
- A transient error retries only when the wait plus 60 s fits before the deadline. The sleep is capped by the deadline.
- Case `backoff-deadline` (shipped `[30, 60]` backoff, `--timeout 3`): `capacity` in under 5 s.

### A-WR-01 / A-WR-02: piped output and a lost reader
**Fixed in** `98b0439`.
- WR-01: the runner exits from the write callbacks of both streams, with a bounded wait for a stalled reader. Case `big-pipe` (300 KB answer through a pipe).
- WR-02: EPIPE on stdout or stderr no longer crashes the runner. Logging stops and the run finishes under supervision.
- An `uncaughtException` hook SIGKILLs the current group, drops temp dirs and prints `status=crash`. In self-test mode it reaps the cases.
- Case `stderr-closed`.

### A-WR-03: the live timeout lookup differed from config-get
**Fixed in** `345aae8` (requires human verification).
- The lookup mirrors gsd-core's `readScopedConfigValue`:
  - first the key in `.planning[/project][/workstreams/ws]/config.json`;
  - then the root key, under `GSD_WORKSTREAM` only;
  - a bad segment reads as absent.
- Checked against the real `config-get`. Behavior change: a `GSD_WORKSTREAM` with `..` now falls to 300 s, as GSD's own fallback does when config-get rejects it.
- Not done: the stored active-workstream pointer is not read (shortcut comment).
- Five new deadline cases.

### A-WR-04: 403 spending limit classified as auth
**Fixed in** `0cef15e`.
- `billing` and `quota` now come before `auth`. `billing` also matches the free-tier error pi reported live.
- The pattern-order unit test was updated.

### A-WR-05: suffixed model specs failed the preflight
**Fixed in** `d4e5629`.
- Only the documented pi `:level` suffix and the opencode `#variant` suffix are stripped for the check. The log says the suffix itself was not validated.

### A-WR-06: the selected effort never reached the runner
**Fixed in** `8420125` (requires human verification).
- Design choice: a catalog pick on pi or codex records the effort target, clamped to the model's reasoning modes, in a new optional key `artifacts[0].config.effort`.
  - The key is absent when empty, so the goldens are unchanged.
  - It is skipped for router picks, for models without reasoning modes, and for ids that already name an effort.
- `plan_io` validates the key. `plan-set` and `plan-unset` of a runner model keep it in step. The renderer bakes it into `CONFIG.effort`.
- The runner passes pi `--thinking` (unless the model has a `:level` suffix) and codex `model_reasoning_effort`. `--codex-effort` still wins.
- SKILL.md gained a two-line note.

### A-WR-07 / A-WR-08: retry argv
**Fixed in** `2a44876`.
- WR-07: each pi review retry gets a fresh `--session-id`.
- WR-08: the codex resume argv keeps `--codex-effort` and `--codex-service-tier`.

### A-WR-09 / A-WR-10: self-test hermeticity
**Fixed in** `728f43d`.
- One async harness runs every case, with the runner in its own process group.
- The fakes record their pids. A per-case `finally` kills the runner group, the fakes' groups and escaped grandchildren, even when a check fails. On Linux this is every pid whose cwd is under the case dir; elsewhere, the recorded pids.
- Self-test mode owns SIGTERM, SIGINT and SIGHUP: it reaps, removes the tmp dir and exits 128+n.
- The grandchild checks fail when the pid file is missing.
- `sigterm-hang` signals only after the CLI started, then asserts that pi and its grandchild are dead.
- `reap-after-failure` SIGKILLs a runner mid-case and proves its orphaned CLI group is still reaped. This is the "no process survives a failing case" test, and it was mutation-checked.
- `review-commit` really commits now: `spawnSync` was never imported.
- `AIKIT_XAI_SELFTEST_CASES` selects cases.
- The Python e2e runs the self-test in its own session, kills the group on timeout, and checks that an interrupted self-test leaves no process and no tmp dir.

### A-WR-11: the strict encoder let config-set re-type strings
**Fixed in** `a3a970a`.
- The refusal mirrors JS `Number()`: decimal literals, 0x/0o/0b integers and whitespace-only strings.
- Strings `Number()` rejects (e.g. `1_000`) are no longer refused.

### A-WR-12: edits inside submodules were invisible
**Fixed in** `1fda1cf` (requires human verification).
- `treeState` lists the temp index's gitlinks. It snapshots each checked-out nested repo recursively (depth cap 8) and folds that repo's state in.
- An unreadable nested repo makes the state unknown.
- Cases `submodule-edit` and `submodule-review-ok`.

### A-WR-13 / A-PT-17 / C-IN-09: Rigorous with one lane and no note
**Fixed in** `059501f`.
- The note fires whenever fewer lanes than wanted are chosen, and it names the reason (SPEC R2).
- New fixture test. Goldens are unchanged.

### A-IN-01, A-IN-04, A-IN-06, A-IN-07, A-IN-09
**Fixed in** `36d5975`.
- IN-01: the attempt log shows the real time left.
- IN-04: `Object.hasOwn` for CLI names.
- IN-06: the hermetic env for the flaky check.
- IN-07: `cli_rc=-` when the CLI never ran.
- IN-09: a review-only CLI anywhere in an exec prefer list is refused before the first spawn.

### A-IN-02: tautological assertion
**Fixed in** `c6f7483`. The test parses the deadline line and compares it with the configured timeout.

### A-IN-03: unborn HEAD detection depended on English messages
**Fixed in** `d8b0a88`.
- `rev-parse --verify -q HEAD` now decides. The fake git can emulate a translated message (`unborn-head-l10n`).

### A-IN-10: a config-set timeout echoed the value
**Fixed in** `c2125ea`. The timeout returns a fixed message that names only the key.

### A-IN-11 / A-PT-11: umask briefly set to 0
**Fixed in** `d6e4945`.
- `cache.umask_file_mode` reads `Umask:` from `/proc/self/status`, with the set/restore fallback elsewhere.
- `cross_ai_script._publish` reuses it.
- The recommend I/O-boundary test exempts the process's own `/proc` status read.

### A-PT-07 / A-PT-10
**Fixed in** `814fb18`.
- PT-07: `cross_ai.timeout_ok` is the one timeout predicate, used by `timeout_value` and `plan_io.timeout_problem`.
- PT-10: `_declared_routers(pool, purpose)` serves both the execute and review router filters.

### A-PT-15 / A-PT-22: dead runner branches and listing boilerplate
**Fixed in** `1ee81c4`. Parts also landed in `ac678cc`, `98b0439` and `728f43d`.
- PT-15: removed the always-true `bad_model` branch, the second review-dirty check, the two-branch `.then` and the `go` wrapper. `tryNextCli` is one expression.
- PT-22: listing formulas moved into `RUNTIMES[*].list`. `writeExe` plus a shared prelude now writes the fakes, one case harness replaces two, and the git env is built once.

### A-PT-20: cross_ai_script leftovers
**Fixed in** `833d0f5`.
- `command_argv` is deleted; the test checks the GSD word split instead.
- `_stamp` drops its unused parameter.
- `_note_new` uses a state table, and `_divert_to_new` became a `_replace` call.

### C-W12 (optional batch C hand-off)
**Fixed in** `ef910f0`. The "no <runtime> models enumerated" reason moved from `recommend._exec_targets` into `cross_ai.exec_targets`.

## Skipped

### A-IN-12: each snapshot rehashes the whole tree
**File:** `skills/ai-kit-spec-review/references/cross-ai.mjs` (`treeState`)
**Reason:** the suggested fix trades correctness for an unmeasured speedup.
- Seeding the temp index from `.git/index` makes `git add -A` trust the index's assume-unchanged and skip-worktree bits and its fsmonitor state.
- A CLI edit to such a file would then read as `tree=clean`, which is exactly the false certainty SPEC R5 forbids.
- The review did not measure the slowdown either. It stays open: the next step is to measure it on a large repo before choosing a fix.
**Original issue:** each snapshot hashes every file into an empty index; on a large or LFS repo the 10 s git cap could turn runs into `unverified`.

## Not in scope
- PT-18, PT-19 and PT-21 touch only batch B files (`apply.py`, `followups.py`, `plan_edit.py`). This batch was limited to the consider items on batch A files.
- `detection.py`, `local_secrets.py` and `tooling_guidance.py` had no batch A findings, and were not changed.

## Files outside the batch A list touched
- `plan_io.py`: WR-06 `effort` validation and PT-07.
- `plan_edit.py`: WR-06 effort sync.
- `recommend.py`: C-W12 hand-off.
- `skills/ai-kit-gsd-curated-config/SKILL.md`: the WR-06 note.
- Tests: `test_curated_config_plan_edit.py`, `test_curated_config_recommend.py` (the IN-11 `/proc` exemption).

---

_Fixed: 2026-10-15_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
