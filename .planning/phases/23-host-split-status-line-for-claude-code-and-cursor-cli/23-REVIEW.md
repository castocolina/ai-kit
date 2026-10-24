---
phase: "23"
depth: standard
reviewer: "cross-AI opencode router-env/my-plan-review (code) + ponytail pass (same lane)"
diff_base: 143c78a
status: fixed
findings: { critical: 2, warning: 11, info: 0, ponytail_medium: 5, ponytail_low: 5 }
fixed_in: [4010a24, 4bb2161, 747e5f1, 8febb76, 9ce6106, c258489, c8b6a92, 17bf28e, b02891a]
---

# Phase 23 — Code Review

Reviewed `git diff 143c78a..HEAD -- . ':!.planning'` (75 files) through the cross-AI lane, plus a
ponytail pass on the same lane. The orchestrator confirmed both Criticals against
`tools/command_ownership.py` before dispatching. Fixes ran on pi in two runs (the first hit the
deadline after 8 commits), and the orchestrator re-ran every gate afterwards.

## Dispositions

- CR-01 quote rewriting in migrated commands (`$` and `$(...)` paths became shell substitutions):
  `shlex.join` is returned unchanged, and the tests compare parsed argv (4010a24).
- CR-02 Python option values taken as the script: ownership now accepts only an explicit
  no-argument flag allowlist; `-c`, `-m`, `-X`/`-W` and unknown options are foreign, with
  counterexamples on both hosts (4010a24).
- WR-01/WR-02 refresher lifetime bound by the fetch deadline; an optional-call timeout no longer
  discards required usage (747e5f1).
- WR-03/WR-04 an absent individual limit is no longer "extra off"; the negative TTL applies only
  after an error (4bb2161).
- WR-05..WR-08 wizard: declining the last host keeps earlier adoptions; approval covers only the
  commands shown; a Claude filesystem error no longer aborts Cursor's commit; offline save
  validation fails closed on renderer failures (`--check-render`) (8febb76).
- WR-09 the doctor diagnoses a type-broken TOML instead of crashing (9ce6106). WR-10 the memory
  example honors the width budget (c258489). WR-11 the audit's history guard handles shallow
  clones (c8b6a92).
- Ponytail P1-P10 taken (b02891a): one sibling-import helper, no re-imports, one hidden
  QuotaResult, `util_display_dir` reuse, the dead `rate` ramp band dropped (a user
  `[ramp.rate]` now warns as unknown; sample and README updated), `cfg_env_label` reuse, a flat
  ternary, hoisted test imports, a single `dict(env)`. The Claude byte oracle stayed green.

## Reviewer reports (verbatim)

## Findings

### CR-01: Migration turns safely quoted paths into shell substitutions
**File:** tools/command_ownership.py:39  
**Issue:** Replacing `shlex.join()`’s single quotes with double quotes changes shell semantics. An existing command pointing to `'/data/$(id) kit/tools/status-line.py'` is migrated to `"/data/$(id) kit/tools/claude-status-line.py"`. Claude’s shell executes the substitution instead of treating it as a literal directory name. Ordinary `$variable` paths also break. This violates the migration’s command-preservation requirement.  
**Fix:** Return `shlex.join(argv)` unchanged. Test parsed arguments rather than requiring double quotes, and add literal `$` and `$(...)` path cases.

### CR-02: Ownership detection mistakes Python option values for the script
**File:** tools/command_ownership.py:16  
**Issue:** `_script_index()` selects the first argument not starting with `-`, without interpreting Python options. For example, `python3 -X /synthetic/ai-kit/tools/claude-status-line.py -c 'print(123)'` does not execute ai-kit—the path is the value of `-X`—but is classified as owned. Detection, migration and uninstall therefore can modify or remove foreign commands. This contradicts D-23’s exact command ownership requirement.  
**Fix:** Recognize only explicitly supported interpreter forms and flags. Reject `-c`, `-m`, and options consuming arguments unless parsed correctly; require the matched path to be the actual script argument. Add these cases to the shared ownership tests.

### WR-01: The deadline does not bound the detached refresher’s lifetime
**File:** tools/cursor_quota.py:614  
**Issue:** `response.read(65536)` can perform many socket reads before returning. A server sending one byte just before each socket timeout keeps that call alive beyond the monotonic deadline. `executor.shutdown(wait=False)` returns, but Python waits for its executor threads during interpreter shutdown. The detached refresher remains alive and holds `usage.lock`, blocking subsequent refreshes indefinitely. The deadline test only delays the response before sending it; it does not exercise a trickling body or process exit.  
**Fix:** Use incremental body reads that return after available data, checking the absolute deadline between reads, and ensure outstanding transport workers terminate before the refresher exits. Add a trickling-response subprocess test that asserts the production refresher exits and releases its lock within the bound.

### WR-02: An optional-call timeout discards successful required usage
**File:** tools/cursor_quota.py:572  
**Issue:** If `GetCurrentPeriodUsage` succeeds but `GetHardLimit` or `GetPlanInfo` exceeds the deadline, any pending future causes `probe_submit_calls()` to return `None`. `probe_fetch_all()` then discards all completed results and reports a total network failure. With no previous cache, valid included/API usage disappears solely because an optional method timed out. This contradicts D-10’s requirement that optional failures degrade only their dependent data.  
**Fix:** Preserve completed results and represent unfinished methods as individual failures. Fail the whole fetch only when the required usage method fails or is unfinished. Test a successful usage response alongside each optional timeout.

### WR-03: An absent optional individual limit falsely reports “extra off”
**File:** tools/cursor_quota.py:105  
**Issue:** Missing `individualLimit` is converted to `0.0`, so non-team usage immediately takes the disabled branch. For `{"individualUsed":520,"limitType":"user"}`, even `{"hardLimit":20}` or an unlimited hard limit produces `disabled`; without hard-limit evidence it also claims disabled rather than unavailable. The recorded contract identifies `individual_limit` as optional, so absence is not evidence of zero. This contradicts D-10’s absence and classification rules.  
**Fix:** Preserve `None` for an absent individual limit. Apply the disabled branch only to an explicit zero, then use hard-limit evidence for absent individual limits. Add absent-versus-explicit-zero cases with fixed, unlimited and failed hard-limit responses.

### WR-04: Successful refreshes are also subject to the negative-cache TTL
**File:** tools/cursor_quota.py:268  
**Issue:** Every successful refresh records `last_attempt_at`, but `core_needs_refresh()` applies the 600-second negative TTL without checking whether the attempt failed. A cache successfully fetched at time 1000 becomes stale after 1120, yet does not refresh until 1600. Normal operation therefore displays stale quota for roughly eight minutes of every ten-minute interval, contrary to D-16’s 120-second freshness and failure-only negative caching.  
**Fix:** Apply `NEGATIVE_TTL_S` only when the last attempt failed. A successfully populated cache should become refreshable immediately after `FRESH_TTL_S`. Test both cases using the complete cache shape produced by `probe_refresh()`.

### WR-05: Declining the last host prevents saving an earlier adopted host
**File:** tools/wizard_app.py:1237  
**Issue:** `_has_net_change()` checks only the active pane’s adoption state. With unchanged component selections, adopt and arrange Claude, then decline Cursor. Cursor remains the active pane, so Review reports “Nothing to write” and refuses to commit Claude’s changes. The existing scenario is masked by fixtures whose component selection already differs from its initial state. This violates D-22’s independent host decisions.  
**Fix:** Check whether any host pane is adopted, alongside component changes. Add the two-host scenario with component selections exactly equal to `_initial_enabled`.

### WR-06: Wizard approval authorizes replacing commands the user never saw
**File:** tools/setup.py:3722  
**Issue:** The adoption gate stores only `adopt=True`; commit passes `assume_overwrite=True` without retaining the approved wiring value. If the user approves foreign command A and another process changes it to B while Arrange is open, commit replaces B without approval. Cursor’s reread does not help: its first comparison value is captured during commit, after B appeared. This violates the explicit replacement decision and D-23’s preservation intent.  
**Fix:** Store the wiring value approved at the gate and compare it with fresh wiring before publishing that host’s changes. Refuse or re-prompt when it differs; do not use adoption as blanket overwrite permission.

### WR-07: A filesystem exception on Claude aborts Cursor’s commit
**File:** tools/setup.py:3756  
**Issue:** The per-host loop does not catch `OSError`. `_candidate_file()` calls `makedirs()` and `mkstemp()` outside its own handler at lines 648–649. If Claude’s existing config is readable but its directory is not writable, candidate creation raises `PermissionError`, escapes the loop, and prevents a writable Cursor host from being attempted. Existing isolation tests cover rejection return values rather than this filesystem failure. This contradicts D-22’s independent per-host outcomes.  
**Fix:** Catch filesystem errors at each host’s commit boundary, record that host’s failed outcome and diagnostic, and continue. Add a first-host candidate-creation failure test asserting the second host still commits.

### WR-08: Offline save validation accepts renderer-reported failures
**File:** tools/setup.py:637  
**Issue:** `_offline_dry_render()` accepts any exit code 0. The real renderer deliberately catches pipeline and builder exceptions, prints warning/error output, and still exits 0. Consequently, an enabled builder that raises during candidate validation does not prevent publication. Mocking `_offline_dry_render()` to return `False`, as the rejection test does, cannot expose this mismatch.  
**Fix:** Provide an offline diagnostic render path that returns failure when the pipeline raises or `ctx.failed` is nonempty, while preserving the normal renderer’s never-blank behavior. Exercise that real path with a deliberately raising builder.

### WR-09: The doctor crashes on the bad TOML value it is supposed to diagnose
**File:** tools/statusline-doctor.py:465  
**Issue:** For `[[line]]` with `min_rows = "x"` and `segments = ["path"]`, structural validation returns no errors. `cmd_doctor()` then loads the config outside its exception handler and raises `ValueError`; `_env_problems()` also reloads it outside the handler. `--check` crashes through the same reload. The renderer correctly points users to this doctor, leaving the prescribed recovery path broken. The Claude weakness predates the split, but the new Cursor doctor inherits it despite D-17’s explicit bad-TOML requirement.  
**Fix:** Validate layout field types and keep config loading/environment binding inside the diagnostic guard. Return an actionable nonzero diagnostic rather than a traceback. Cover the exact D-17 input for both hosts.

### WR-10: Cursor’s bundled memory provider ignores its width budget
**File:** tools/setup.py:967  
**Issue:** Setup now offers the shared `system_memory` provider to Cursor, but `examples/segments/system_memory:64` reads only `AI_KIT_SEGMENT_COLS`. Cursor supplies `AI_KIT_CURSOR_PROVIDER_COLS`, so the provider defaults to 80 columns. At a nine-column budget it emits the long “GiB free” variant, which the renderer truncates instead of selecting the existing compact variant. D-18 explicitly requires this example on both hosts; Q1 deliberately separates their provider namespaces.  
**Fix:** Make the shared example read the host-neutral `segment.avail_cols` stdin field, or recognize both provider width variables. Add a narrow-budget Cursor provider subprocess test without changing Claude’s provider environment.

### WR-11: The audit’s history guard fails on the installer’s shallow clones
**File:** tests/test_arch.py:1089  
**Issue:** `_git_history_available()` checks only whether the current directory is inside a worktree. A shallow clone passes, but `TestSplitAudit.setUpClass()` subsequently fails when `git show` cannot find the audit’s pinned historical blob. The installer creates precisely this checkout shape with `git clone --depth 1`. The clean-room guard also raises during module import if `git` is absent rather than treating history as unavailable.  
**Fix:** Check availability of the actual pinned blob from the repository root and handle a missing Git executable. Skip only genuinely history-dependent checks when that blob is unavailable; keep current-tree checks active.

COUNTS critical=2 warning=11 info=0

## Ponytail pass (verbatim)

# Ponytail review — Phase 23 (`143c78a..HEAD`, excl. `.planning`)

**What this change does:** Splits the 2,622-line `tools/status-line.py` into `common_*` / `claude_*` / `cursor_*` role modules behind thin per-host entries, adds a Cursor status line backed by a normalized, cached, single-flight Dashboard quota fetch isolated in `cursor_quota.py` (the only networking module), hard-renames the Claude entry/TOML with idempotent migration, and makes `setup.py`, the doctor and the wizard multi-host — plus ~7k lines of tests, fixtures and golden renders. The move is disciplined: trust boundaries (endpoint-before-token, refused redirects, atomic+fsync writes, re-read-before-replace, quoted argv, git timeouts, bad-TOML error segment) are all present; I found no bug, no missing validation, no data-loss path.

## Findings

**Must fix:** none.

**Should fix:**

1. **Six copies of the lazy-sibling-import dance** (`tools/setup.py:61-69, 72-83, 97-106, 180-190`; pre-existing `:3885-3888, :4564-4566`)
   - Four *new* copies of "compute `tools_dir`, insert into `sys.path`, import sibling" were added this phase instead of one helper. A single `def _sibling(name): … return importlib.import_module(name)` turns each site into one line and makes the seventh copy trivial. ~18 lines saved.

2. **`importlib.import_module` re-imports modules already imported at the top of the same file** (`tools/cursor_quota.py:497-498, 541, 569, 588`)
   - `os`, `sys`, `time` are top-level imports (lines 8-16) of this very module; the arch rule (`tests/test_arch.py:check_networking_imports`) only requires *networking* modules to be lazy. `os_module`/`sys_module`/`runtime("time")` buy nothing — pure indirection in the credential-path function. Use the module-level names; keep `json`/`urllib`/`fcntl`/`concurrent.futures` lazy (those are genuinely deferred cost or optional). ~6 lines.

3. **Two hand-rolled "hidden" QuotaResult constructions of ~12 positional `None`s** (`tools/cursor_quota.py:213-226` and `:424-437`)
   - Give `QuotaResult`'s trailing fields defaults (`None`, `od_kind="unavailable"`) or a 3-line `_hidden(state, diagnostic)` helper; both sites collapse to one call, and the tests' `_quota(**overrides)` default dict shrinks too. ~22 lines.

4. **`_included` re-checks its own enablement and defeats the doctor** (`tools/cursor_segments.py:51-52`)
   - The packer already filters disabled keys (`common_render.py:335`), so production never reaches this check. Its only real effect: the doctor's every-builder dry render ("including segments that are disabled", `statusline-doctor.py:_dry_render_failures`) short-circuits before the body — the default-off `cursor_api` segment's gauge path is never exercised by `--doctor`. Delete the guard; adjust the test pinning it (`tests/test_cursor_status_line.py:236-238`). −3 lines, more doctor coverage.

5. **`seg_path` re-implements `util_display_dir` inline** (`tools/common_segments.py:36-46` vs `common_types.py:534-544`)
   - The in-repo branch duplicates the exact tiering (full ~-relative → parent/name → name floor) of the existing helper; `util_display_dir(snap.root_path, ctx.home)` is equivalent (`basename(root_path)` is `root_name`). Pre-existing duplication moved verbatim per D-05, but the split was the moment to merge, and the golden renders verify byte-identity. ~7 lines.

**Nice to have:**

6. **Dead `rate` ramp band** (`tools/claude_host.py:72`) — nothing reads `theme.ramps["rate"]` (only context/render_time/slowest/chat_size); a user's `[ramp.rate]` override silently does nothing. Delete the band (turns the useless override into an "unknown ramp" doctor warning — a message change, not a render change). 1 line.

7. **Env-var name projection duplicated** (`tools/common_config.py:87-88` vs `common_fmt.py:32-35`) — `cfg_source_get` re-derives the name `cfg_env_label` already owns; if one naming rule changes, the other silently diverges and env overrides stop applying. Call `cfg_env_label(path, prefix)`. 2 lines.

8. **Nested-ternary state pick** (`tools/cursor_quota.py:207-212`) — `state = error_kind if error_kind in {"auth_expired","auth_unsupported","auth_missing","network_error"} else "absent"` is the same logic in one line. 4 lines.

9. **Function-local import churn in tests** (`tests/test_cursor_quota.py:196, 220, 326, 371, 354-364`) — four local `from tools.cursor_quota import probe_release_lock` and three `__import__("threading")`; import once at top. ~7 lines.

10. **Double `dict(env)`** (`tools/cursor_payload.py:73`) — one local instead of two copies for the same call. 1 line.

Checked and deliberately not flagged: `tests/test_cursor_fakes.py` looks like mock-testing but pins load-bearing platform behavior (urllib's cross-origin redirect follow, the blocking-grandchild semantics D-13 rests on) — keep; `tests/fixtures/statusline_split/audit.md` is SPEC R1-required; the `Budget:` docstrings and `_ENV_HELP`/generated-help split follow pre-existing repo conventions with pinned tests.

**Verdict:** Ship — nothing blocking; findings 1-4 are cheap cleanups worth folding into the next touch of these files.
**Lean:** ≈ −70 lines possible.
**Not checked:** the wizard PTY suite and `make test`/`make validate` runs (read-only review; no commands executed beyond `git show/diff/grep`).

PONYTAIL high=0 medium=5 low=5
