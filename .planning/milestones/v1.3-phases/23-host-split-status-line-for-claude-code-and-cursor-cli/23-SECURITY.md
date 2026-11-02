---
phase: "23"
slug: host-split-status-line-for-claude-code-and-cursor-cli
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
block_on: high
created: "2026-10-24"
---

# Phase 23 — Security

> Threat register, accepted risks and audit trail for the host-split status line (Claude Code + Cursor CLI).
> Audited at HEAD (diff base 143c78a), including the code-review fixes 4010a24..b02891a and the latest test guard.
> Verified by reading the cited code and re-running the suites; documentation was not accepted as evidence.

**Verdict: OPEN_THREATS.** 58 threats (57 IDs plus the repeated T-23-SC): 55 closed, 1 open-blocking, 1 open-non-blocking, 1 accepted-pending-owner.

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| cursor_quota -> Cursor `auth.json` | the only credential reader (`probe_access_token`) | bearer `accessToken` |
| cursor_quota -> network | the only networking module (arch rule `check_networking_imports`) | bearer token out, untrusted JSON in |
| env -> endpoint | `CURSOR_API_ENDPOINT` is attacker-influenced | endpoint URL |
| render -> detached refresher | `start_new_session` spawn, cache-only render | derived quota numbers |
| setup / wizard -> host configs | Claude `settings.json`, Cursor `cli-config.json`, ai-kit TOML | user config files |
| Cursor CLI -> entry stdin | untrusted payload JSON | status payload |
| owner probe / POC worktree | owner-run, outside the shipped code | real token, POC backup |

## Threat Register

Status: closed, open (blocking), open — below high threshold (non-blocking), or accepted-pending-owner. Evidence paths are relative to the repo root.

| Threat ID | Category | Component | Severity | Disposition | Evidence | Status |
|-----------|----------|-----------|----------|-------------|----------|--------|
| T-23-01 | Info disclosure | golden fixtures | low | mitigate | no `/home`, `/var/home` or `/Users` in any phase-added fixture (rg over `tests/fixtures`) | closed |
| T-23-02 | Tampering | entry subprocess env | medium | mitigate | `tests/test_status_line.py:3552` explicit env dict with `GIT_CEILING_DIRECTORIES`, merged only with `extra_env` | closed |
| T-23-03 | Tampering | audit table vs code | medium | mitigate | `tests/test_arch.py` TestSplitAudit against base blob 143c78a (blob present, suite green, no skips) | closed |
| T-23-04 | DoS | `git show` in a test | low | accept | accepted, see Accepted Risks Log | closed |
| T-23-05 | Info disclosure | POC salvage | high | mitigate | `tests/fixtures/cursor/payload_poc_redacted.json` holds only `<redacted>` strings and numbers; no auth fields | closed |
| T-23-06 | Info disclosure | owner probe | high | mitigate | `live/spike_probe.py` calls `cursor_quota.probe_fetch_quota` only; evidence holds normalized data; `--self-test` canned fetch, asserts no token/Bearer (ran, ok) | closed |
| T-23-07 | Info disclosure | `spike_check.py --promote` | high | mitigate | `check_bundle` regex scan (JWT, Bearer, email, UUID) blocks, then `redact()` replaces every string; `--self-test` ok. Note U2: the promote copy step is broken (fail-closed) | closed |
| T-23-08 | Spoofing | FakeDashboard | low | mitigate | `tests/cursor_fakes.py:108` binds `("127.0.0.1", 0)` | closed |
| T-23-09 | DoS | runner simulator children | low | mitigate | no stray test/refresher/PTY process after the suites (ps check) | closed |
| T-23-10 | Tampering | split modules | medium | mitigate | AST-hash audit plus byte oracles; `tests.test_arch`, `test_status_line` green | closed |
| T-23-11 | Repudiation | test rewrite | low | mitigate | assertion-diff checker was run during 23-04 (23-04-SUMMARY); scratch tool is not retained, so this is one-time evidence only | closed |
| T-23-12 | Tampering | sibling import resolution | low | accept | accepted, see Accepted Risks Log | closed |
| T-23-13 | DoS | broken render after the move | medium | mitigate | entry oracle and worktree/memory e2e in the suites (green) | closed |
| T-23-14 | Tampering | config env prefix | medium | mitigate | prefix is a host constant (`tools/claude_host.py:89`, cursor host); `test_cursor_status_line.py:385` isolation test | closed |
| T-23-15 | DoS | bad TOML | medium | mitigate | `safe_render` doctor line; `tools/statusline-doctor.py` diagnoses type-broken config (WR-09 fix 9ce6106) | closed |
| T-23-16 | Info disclosure | provider env mirror | low | mitigate | Claude mirror pinned by `tests/fixtures/golden/strict_provider_capture.json` oracle | closed |
| T-23-17 | DoS | git probes | medium | mitigate | `timeout=GIT_TIMEOUT_S` on both calls, `TimeoutExpired` handled (`tools/common_probe.py:97,168`) | closed |
| T-23-18 | Tampering | Context contract | low | mitigate | `rg "ctx\.host" tools/common_*.py` finds no generic reader | closed |
| T-23-19 | Tampering | migrate_statusline (settings) | high | mitigate | `tools/setup.py:2583-2610`: `_read_json_checked`, exact-argv `rewrite_owned_command`, `_atomic_write_json`; CR-01/CR-02 fixed (`tools/command_ownership.py:12-64`); `test_setup` ownership and counterexample tests green | closed |
| T-23-20 | Tampering | TOML move | high | mitigate | `tools/setup.py:2613-2637`: both-present warns and changes nothing; `create_if_absent` (`os.link`, exclusive-create fallback) never overwrites; `test_lost_publication_race_preserves_source_and_winner` | closed |
| T-23-21 | DoS | create_if_absent race | medium | mitigate | `tools/setup.py:2549-2580` `FileExistsError` winner semantics, temp always unlinked in `finally`; race and failure-injection tests green | closed |
| T-23-22 | DoS | hard rename upgrade gap | low | accept | accepted, see Accepted Risks Log | closed |
| T-23-23 | Tampering | core_normalize | medium | mitigate | `util_number` rejects bool/NaN/inf/negative (`tools/cursor_quota.py:70-80`); non-dict shapes become `{}`; table tests green | closed |
| T-23-24 | Info disclosure | normalized data | high | mitigate | ABSENT in full: `core_normalize` stores `included_period` as the raw server string (`cursor_quota.py:162-165,184`), so the data dict is not "numbers and enums only"; the declared test (no string longer than the enum set) does not exist (`tests/test_cursor_quota.py:672` only calls `json.dumps`). Demonstrated: a 5000-char `includedUsagePeriod` survives into the data. Re-audit 2026-10-24: `included_period` is clamped to a closed enum and a hostile 5,000-char value is tested (f88a98e). | closed |
| T-23-25 | Repudiation | inferred values shown as fact | medium | mitigate | `QuotaResult.confidence` defaults to `inferred` and `core_quota_state` always sets it (`cursor_quota.py:33,233`) | closed |
| T-23-26 | Info disclosure | redirect handling | high | mitigate | `NoRedirect.redirect_request` returns None (`cursor_quota.py:509-517`); `test_redirect_refused_before_second_server_receives_request` | closed |
| T-23-27 | Info disclosure | endpoint override | high | mitigate | `probe_validate_endpoint` (https, exact `cursor.sh` or `.cursor.sh` suffix, port 443/None, no userinfo, no path/query) runs before `probe_access_token` (`cursor_quota.py:634-637`); requests use the canonical rebuilt host; `test_endpoint_validation_and_rejection_precedes_auth` | closed |
| T-23-28 | Info disclosure | token handling | high | mitigate | only `accessToken` is read (`:503`); token appears only in the Authorization header (`:593`); every diagnostic is a constant string; doctor token-absence test uses the real flow. Test gap: the quota-module token test only exercises the early-reject path Re-audit 2026-10-24: the declared test now exists (832303b). | closed |
| T-23-29 | Spoofing | TLS | medium | mitigate | no `ssl`, context or verify override anywhere in `tools/`; stdlib default verification | closed |
| T-23-30 | DoS | slow Dashboard | medium | mitigate | per-call timeout, concurrent calls, body deadline via `read1` (`cursor_quota.py:599-621`). The absolute deadline is NOT enforced while response headers arrive: a local server sending header bytes every 0.5 s kept `probe_dashboard_call` running 8 s past a 2 s deadline (PoC, removed). See Open Items Re-audit 2026-10-24: an absolute-deadline watchdog (`shutdown(SHUT_RDWR)`) bounds connect, headers and body, with loopback header-trickle tests (3719f68). | closed |
| T-23-31 | Info disclosure | cache and lock files | high | mitigate | 0700 dir (`makedirs` + `chmod`, lstat symlink and owner checks, `:295-307`); 0600 temp via `fchmod` (`:331`), lock `O_NOFOLLOW` + 0600 (`:355-357`); data is derived values (see T-23-24 for the one string). Mode asserted at `test_cursor_quota.py:89,100,159`; no test walks every cache file for the token Re-audit 2026-10-24: the declared test now exists (832303b). | closed |
| T-23-32 | Tampering | cache dir symlink | medium | mitigate | `probe_cache_paths` refuses symlink, non-dir and foreign owner; `test_symlink_cache_directory_is_refused` | closed |
| T-23-33 | DoS | refresh storm | medium | mitigate | non-blocking `flock` single-flight (`:347-363`), negative TTL only after a failure (`:265-266`, WR-04 fix); contender and killed-holder tests green. A stuck fetch holds the lock (T-23-30) | closed |
| T-23-34 | Info disclosure | refresher argv/env | high | mitigate | argv is `[python, "-S", realpath(__file__), "--refresh"]`, env is the render's own (`:396-402`), the child re-reads the token itself. No test asserts the production argv Re-audit 2026-10-24: the declared test now exists (832303b). | closed |
| T-23-35 | Elevation | new-session spawn | low | mitigate | rule 11 allowlist names `tools/cursor_quota.py` with its reason (`tests/test_arch.py:844-851`); child is ai-kit's own module under `-S` | closed |
| T-23-36 | Tampering | payload parsing | medium | mitigate | `core_cursor_context` validates `render_width_chars` (bool excluded) and coerces fields (`tools/cursor_payload.py:55-91`); malformed-payload tests green | closed |
| T-23-37 | Info disclosure | cross-host env/config | medium | mitigate | separate prefixes and provider namespaces; `test_config_env_isolation_and_cursor_toggle`, `test_config_namespace_provider_namespace_and_no_network_render` | closed |
| T-23-38 | Repudiation | inferred quota shown as fact | medium | mitigate | `≈` on quota segments (`tools/cursor_segments.py`), doctor label `_QUOTA_LABEL` | closed |
| T-23-39 | DoS | network in render | high | mitigate | `check_networking_imports` confines networking imports to functions of `cursor_quota.py` (no other `urllib`/`socket`/`http` use in `tools/*.py`); render calls only `probe_read_quota`, which spawns the detached refresher | closed |
| T-23-40 | Info disclosure | networking outside cursor_quota | high | mitigate | same rule, `test_networking_imports_are_confined` green with its non-vacuity twin; `auth.json` and `accessToken` appear only in `cursor_quota.py` (rg) | closed |
| T-23-41 | Tampering | cross-host coupling | medium | mitigate | dependency-direction and host-import rules in `tests/test_arch.py` (60 tests green) | closed |
| T-23-42 | Repudiation | stale docs | low | mitigate | `check_legacy_references`; `docs/architecture/status-line-pipeline.md` deleted | closed |
| T-23-43 | Info disclosure | doctor output | high | mitigate | `quota_report` prints state, age, constant diagnostic and hint only (`tools/statusline-doctor.py:416-448`); `test_token_absent_from_stdout_and_stderr` | closed |
| T-23-44 | DoS | doctor foreground fetch | low | mitigate | skips the refresh when `probe_try_lock` fails (`:429-431`); fetch bounded by per-call timeouts | closed |
| T-23-45 | Repudiation | inferred quota | medium | mitigate | every report line carries `(inferred — undocumented Cursor API)` | closed |
| T-23-46 | Tampering | foreign statusLine | high | mitigate | three-state classification (`setup.py:2158-2245,2318-2333`), interactive yes else headless refusal on both hosts (`:2226-2235,2425-2441`); `test_matrix_foreign_headless_exits_one_on_both_hosts` | closed |
| T-23-47 | Tampering | concurrent CLI rewrite | medium | mitigate | `_cursor_commit_statusline` re-reads and re-classifies before `_atomic_write_json`, aborts on a changed entry (`:2444-2472`); injected-race test | closed |
| T-23-48 | Tampering | malformed config | medium | mitigate | `_read_json_checked` / `_cursor_config_read`; bad and JSONC files refused for wire and unwire (`:2383-2407,2706-2731`) | closed |
| T-23-49 | Elevation | command string | low | mitigate | Cursor command is `python3 -S ` + `shlex.quote(entry)` (`:2499`); Claude form is the unchanged pre-existing unquoted one (see U5) | closed |
| T-23-50 | DoS | host selection | low | mitigate | `parse_statusline_hosts` raises on unknown/undetected names before any write (`:2526-2546`) | closed |
| T-23-51 | Info disclosure | Cursor preview | high | mitigate | temp `XDG_CACHE_HOME` with a synthetic fresh cache, `XDG_CONFIG_HOME` repointed, no refresher, temp dir removed (`setup.py:318-331,386-388,407-419`) | closed |
| T-23-52 | Tampering | per-host commit | high | mitigate | `write_toml_preserving`: candidate, offline doctor `--check`, `--check-render` dry render, then `os.replace`; rejected candidate deleted, live file untouched (`:687-750`); WR-05..WR-08 fixed | closed |
| T-23-53 | DoS | one host failing | medium | mitigate | `_commit_host_statusline` catches `OSError` per host (`:3739-3745`); isolation tests green | closed |
| T-23-54 | Tampering | declined host | high | mitigate | declined state has `adopt: False` and `_commit_host_statusline` writes nothing; `test_declining_a_host_leaves_its_files_byte_identical` (both hosts) | closed |
| T-23-55 | DoS | orphaned PTY children | low | mitigate | no stray PTY/wizard process after the suites (ps check) | closed |
| T-23-56 | Info disclosure | POC `tmp/cli-config.json.bak` | high | mitigate | D-12 delete deliberately deferred to the owner. Not performed or required by this audit. See Accepted Risks Log | accepted-pending-owner |
| T-23-57 | Repudiation | claimed live results | medium | mitigate | `spike_check.py --record 23-SPIKE.md` exits 1 with exactly S1-S7 `not run (owner)`; 23-VERIFICATION.md is `human_needed` | closed |
| T-23-SC | Tampering | npm/pip/cargo installs | high | mitigate | `pyproject.toml` diff is a comment only; no lockfile change; the new modules import stdlib and sibling modules only | closed |

*Severity: critical > high > medium > low. Only open threats at or above `high` count toward `threats_open`.*

## Open Items

**Blocking (`threats_open: 1`)**

- T-23-24 (high): clamp `included_period` to a closed set (for example `weekly`/`monthly`/None) in `core_normalize`/`util_plan_window`, and add the declared test (serialize the normalized data and the written cache, assert no string outside the enum set, and assert the token is absent from every file under the cache base). Practical exposure is low, since only the server could place a string there and the cache is 0600, but the declared invariant is not enforced.

**Non-blocking**

- T-23-30 (medium): enforce the absolute deadline during the header phase (for example a watchdog that closes the socket at the deadline, or a hard `os._exit` in the refresher) and add a trickling-header subprocess test next to `test_trickling_body_subprocess_refresher_exits_within_the_bound`. Requires a trusted-TLS `*.cursor.sh` peer or a proxy, and costs only quota freshness, because the render stays cache-only.

## Unregistered Flags

No `## Threat Flags` section exists in any 23-NN-SUMMARY.md. Observations from the audit (not mapped to a threat ID, none blocking):

- U1 (fixed 4d94465: the shown command is pinned for hosts adopted at wizard open, with a concurrent-foreign-write test): a host already `ours` when the wizard pane is built is auto-adopted with no `adopt_command` pin (`tools/wizard_app.py:331` vs `:1083-1088`), so `_commit_host_statusline` skips the changed-command check (`setup.py:3717`) and commits with `assume_overwrite=True`. A foreign command written concurrently during the wizard session would be replaced unseen. Residual of WR-06.
- U2 (fixed a29ec73: pathlib join, real newline, `promote_bundle()` self-test into a temp dir): `live/spike_check.py --promote` raises `TypeError` at `"tests" / "fixtures"` (str / str) and writes a literal `\\n`; fail-closed, so nothing is promoted, but the owner promotion step cannot work as written.
- U3: the default opener honors `HTTPS_PROXY`; TLS stays end-to-end, so the token is not exposed to the proxy.
- U4: on darwin `probe_auth_path` ignores `XDG_CONFIG_HOME`, so the preview/dry-render repoint does not isolate the credential path there; the fresh synthetic cache is what prevents a refresh.
- U5: Claude wiring writes an unquoted `python3 -S <path>` (pre-existing since 143c78a); a path with spaces or shell metacharacters misbehaves. The path comes from the user's own install dir.
- U6: if `probe_write_cache` fails, no attempt is recorded, so the negative cache never engages and each stale render may spawn a (lock-serialized) refresh.

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-23-01 | T-23-04 | a missing git object fails the test loudly; no network, no write | PLAN 23-02 (accept) | 2026-10-24 |
| AR-23-02 | T-23-12 | entry runs with `python3 -S` from the install dir; `sys.path[0]` is the script's real directory, so a cwd module cannot shadow a split module | PLAN 23-05 (accept) | 2026-10-24 |
| AR-23-03 | T-23-22 | owner decision (no shim) for the hard rename; README documents recovery; the next setup run repairs it | PLAN 23-08 (accept) | 2026-10-24 |
| AR-23-04 | T-23-56 | D-12, deleting the POC credential backup (outside this checkout), is deferred to the owner; accepted-pending-owner, not counted in `threats_open`. Residual: a 0644 file holding `authInfo` stays on the owner's disk until deleted | owner (pending confirmation) | 2026-10-24 |

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-24 | 58 | 55 | 2 (1 blocking, 1 non-blocking), 1 accepted-pending-owner | gsd-security-auditor |
| 2026-10-24 | 58 | 57 | 0, 1 accepted-pending-owner (AR-23-04) | orchestrator re-audit after f88a98e..4484d7f (six gates green) |

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed (T-23-24 and T-23-30 closed)
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-24; D-12 stays accepted-pending-owner
