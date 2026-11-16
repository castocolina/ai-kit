---
phase: "34"
slug: "jev-backends-by-host-and-laya-calibration"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-15"
---

# Phase 34 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| user/project config.toml -> jev settings | file content (possibly from a cloned repo's `.aikit/`) becomes settings | plan 01 |
| agent answer -> config_set | a value typed by the user through the agent is written to the user config | plan 01 |
| project `.aikit/config.toml` -> Laya address | a cloned repo can name any host as `laya_url` | plan 02 |
| client -> configured Laya host | item text crosses to that host | plan 02 |
| probe output -> agent transcript | labels and hints reach the conversation | plan 02 |
| upstream pages (PyPI, GitHub) -> record | untrusted web text becomes a stored note an agent may read | plan 03 |
| Laya /health and /openapi.json -> identity | server-provided JSON decides the record key | plan 03 |
| parent shell env -> child client env | callers decide what control state reaches the client | plan 04 |
| project config -> knob | a cloned repo's `.aikit/config.toml` can carry `[jev] enabled` | plan 04 |
| docs.typesafe.ai pages -> record | public web text becomes a stored note | plan 05 |
| remote answer's model id -> local state | a server-supplied string is written to disk | plan 05 |
| client -> PyPI, GitHub raw, docs.typesafe.ai | public keyless GETs from --probe and --check-updates | plan 06 |
| client -> configured Laya origin | GET /health and /openapi.json | plan 06 |
| remote answer -> local state | a model id string becomes a pending record | plan 06 |
| stored web notes -> agent | the agent reads upstream text the client saved | plan 07 |
| skill text -> agent behaviour | the docs decide what the agent claims and asks | plan 07 |
| future edits -> skill tree | a later change could reintroduce a removed backend or a delegated install step | plan 08 |
| docs -> downstream agents | REQUIREMENTS, ROADMAP and the design record steer later planners | plan 08 |
| orchestrator machine -> live Laya | the calibration sends 32 labelled items to the configured Laya | plan 09 |
| orchestrator machine -> TypeSafe | the spike sends five requests off the machine | plan 09 |
| live runs -> real user files | the client could write state or config under the real HOME | plan 09 |
| repo -> external judge lanes | read-only review lanes read the tree through a host CLI | plan 10 |
| judged skill text -> judge | prompt injection from the text under judgment | plan 10 |
| scratch records -> committed records | lane-derived data enters the repository | plan 10 |

---

## Threat Register

Verified by gsd-security-auditor (ASVS L1, block_on high) after the code-review fixes (05a7ff3..8da34f9).
T-34-29 was open (low, stale design.md cites after the fixes) and was closed by ccd67b3.

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-34-01 | Tampering | config_set / publish | high | mitigate | set_table re-parses and refuses a result that differs from the intended document; publish refuses invalid TOML and writes atomically (mkstemp, fsync, os.replace); a broken existing file is refused (`config_unwritable`), never overwritten; only `[jev]` changes Evidence: jev_config.py set_table/_verify, publish, cache_write_bytes; test_jev_config.py | closed |
| T-34-02 | Information disclosure | parse_value laya_url | medium | mitigate | a URL with a user name, a password, a query or a fragment is refused (query and fragment: review C2-2), so no credential-shaped URL part is stored in config.toml, echoed by `config set` or printed by later probes Evidence: jev_config.py valid_url/parse_value; test_set_refuses_bad_values_and_writes_nothing | closed |
| T-34-03 | Tampering | the copied reader and splicer | medium | mitigate | tests/test_jev_config_parity.py fails on any AST drift from Phase 33's modules Evidence: tests/test_jev_config_parity.py (AST equality, non-vacuity, count) | closed |
| T-34-04 | Elevation of privilege | knob from a broken or hostile file | medium | mitigate | an unparseable file or a non-boolean `enabled` turns jev off (fail closed) and names the problem; the session env stays the only override above the files Evidence: jev_config.py knob fail closed; test_knob_bad_value_and_broken_file_fail_closed | closed |
| T-34-SC (plan 01) | Tampering | package installs | low | accept | no package install in this plan (stdlib only) Evidence: no dependency change (git diff --stat 76269a2 HEAD over lock/manifest files is empty); stdlib only | closed |
| T-34-05 | Information disclosure | `_needs_consent`, `_send` | high | mitigate | a Laya host off loopback is gated by the host-bound consent record (`record_consent` keyed by backend and host) before any socket; invariant test over every TABLE row Evidence: _needs_consent/_remote_allowed before any socket; test_every_off_loopback_row_is_refused_before_a_socket | closed |
| T-34-06 | Spoofing | consent record host binding | medium | mitigate | a grant names the host at grant time; a later address change makes `record_consent` return None, so the row asks again (existing SPEC R6 adjacency rule, now covering Laya) Evidence: record_consent host binding; test_consent_record_for_another_host_is_no_consent | closed |
| T-34-07 | Information disclosure | probe output | medium | mitigate | key sources are labels only; `key_hint` is a fixed sentence from the TABLE literal; sentinel test on the probe text Evidence: _backend_entry labels only; test_probe_key_hint_without_env_key | closed |
| T-34-08 | Denial of service | malformed `laya_url` | low | mitigate | `valid_url` and the reason `invalid_url:<key>` make it a probe error, never an exception Evidence: _laya_url invalid_url:<key>; test_malformed_url_is_a_probe_error | closed |
| T-34-39 | Elevation of privilege | `allowed_remotes` session gate | high | mitigate | `JEV_ALLOW_REMOTE` opens remote rows only; a Laya off loopback opens only through `record_consent` bound to its current host, so a cloned project that moves `laya_url` cannot ride a session gate set for TypeSafe (review C1-3); test `test_session_gate_never_opens_an_off_loopback_laya` Evidence: _gate_open only for remote rows; test_session_gate_never_opens_an_off_loopback_laya | closed |
| T-34-40 | Information disclosure | `LAYA_API_KEY` to an off-loopback Laya | high | mitigate | `_laya_url` applies `_remote_url`'s https-or-loopback rule whenever a key is set and the host is off loopback, so the bearer never crosses plain http (review C1-4); test `test_off_loopback_http_laya_never_gets_a_key` with `_exchange` patched to fail Evidence: _remote_url insecure_url; test_off_loopback_http_laya_never_gets_a_key | closed |
| T-34-SC (plan 02) | Tampering | package installs | low | accept | no package install in this plan Evidence: no dependency change (git diff --stat 76269a2 HEAD over lock/manifest files is empty); stdlib only | closed |
| T-34-09 | Tampering | stored notes (prompt injection) | medium | mitigate | notes are decoded with replacement, stored as plain text, cut to 4,000 characters and never executed or rendered; Plan 07's SKILL.md and reference.md say they are data, never instructions Evidence: errors=replace decode, NOTES_MAX_CHARS; test_invalid_utf8_is_replaced_and_stored_as_text | closed |
| T-34-10 | Repudiation | capability claims | medium | mitigate | the module reports `documented_upstream ... not verified here` and never writes a capability cell; verified features are excluded Evidence: 'documented upstream, not verified here'; no TABLE cell writer | closed |
| T-34-11 | Tampering | records file | medium | mitigate | atomic mkstemp + os.replace, 0600 file, 0700 folder; a failed fetch, a partial fetch that found no notes (review C1-7), a PyPI document of an unexpected JSON shape (a failed source, review C3-3) or a failed write leaves the previous file untouched, forced refresh included Evidence: jev_learn write_records mkstemp+os.replace; test_failed_fetch_keeps_records_and_says_so | closed |
| T-34-41 | Repudiation | record identity under a version key | medium | mitigate | a version-keyed entry is `known` only while its stored fingerprint matches the loaded one; a changed route list or revision fetches once and reports `changed` (review C1-6); an idle server with no matching fingerprint waits (`pending_idle`) instead of fetching on a guess Evidence: _is_stale/_laya_decision/_idle_fingerprint; test_idle_never_borrows_another_versions_fingerprint | closed |
| T-34-12 | Tampering | version string in a URL | low | mitigate | the version is percent-quoted with `safe=""` before it enters the PyPI path (Plan 06 also validates the configured value with `valid_version`) Evidence: urllib.parse.quote(version); valid_version | closed |
| T-34-SC (plan 03) | Tampering | package installs | low | accept | no package install; `laya` on PyPI is read as data only Evidence: no dependency change (git diff --stat 76269a2 HEAD over lock/manifest files is empty); stdlib only | closed |
| T-34-13 | Elevation of privilege | child_env, client_env, ask_jev | medium | mitigate | only `GSD_PATH_JEV` crosses, as the user's own value; `JEV_ALLOW_REMOTE`, `JEV_BACKEND`, `JEV_MIN_CONFIDENCE` and the other `GSD_PATH_JEV*` stay scrubbed; tests pin both Evidence: jev_ladder child_env, precompact client_env scrub; test_ladder_child_env_scrubbed | closed |
| T-34-14 | Tampering | broken or hostile config | medium | mitigate | an unparseable file turns jev off with a named problem (fail closed); a project value cannot override the user's session env Evidence: knob env first; knob_off (CR-201); test_user_config_knob_off_reaches_the_hook_child | closed |
| T-34-15 | Denial of service | knob read per call | low | accept | two small TOML reads per `_send`; measured cost is negligible next to an HTTP call Evidence: one knob read and one URL read per _send | closed |
| T-34-SC (plan 04) | Tampering | package installs | low | accept | no package install in this plan Evidence: no dependency change (git diff --stat 76269a2 HEAD over lock/manifest files is empty); stdlib only | closed |
| T-34-16 | Tampering | doc_links (index redirect) | medium | mitigate | only links under `https://docs.typesafe.ai/` are followed; anything else falls back to the fixed default URLs Evidence: doc_links under DOCS_PREFIX only; test_jev_typesafe_models (evil.example) | closed |
| T-34-17 | Information disclosure | note_model on the answer path | medium | mitigate | the pending entry holds only `status` and `first_seen` under a versioned-id key that must match `_VERSIONED_ID`; no item text, context or key ever enters it Evidence: note_model _VERSIONED_ID fullmatch, {status, first_seen} only | closed |
| T-34-18 | Tampering | stored changelog notes | low | mitigate | decoded with replacement, cut to 4,000 characters, stored as text, labelled "documented upstream, not verified here"; an incomplete doc flow writes nothing (review C1-11) Evidence: learn_models writes only with changelog and models; test_failed_fetch_keeps_ids_pending | closed |
| T-34-42 | Information disclosure | note_unknown names from a response or a caller's item | medium | mitigate | only names fullmatching `primitive:` or `option:` plus a 64-character identifier are stored, at most 16, under a versioned-id key; a name holding a key shape the skill's `secret_shapes.detect` knows is dropped and never logged (review C2-4, sentinel test); no item text, value or context enters the record; one doc read per new name. Residual, accepted: a key with no known shape used as a JSON field name is bounded only by the identifier rule; it needs a caller or server to send a secret as a key name, and the record is a 0600 file in the user's own state Evidence: _screened_names, _SECRET_SHAPES drop, caps; test_secret_shaped_unknown_name_is_dropped | closed |
| T-34-SC (plan 05) | Tampering | package installs | low | accept | no package install; the official typesafe-ai skill is never installed or copied Evidence: no dependency change (git diff --stat 76269a2 HEAD over lock/manifest files is empty); stdlib only | closed |
| T-34-19 | Information disclosure | `_public_get` | high | mitigate | sends only `User-Agent`; no Authorization header is ever built there; a test against a local stub asserts the headers; probe text is checked for a sentinel key Evidence: _public_get User-Agent only; test_probe_and_fetch_carry_no_key | closed |
| T-34-20 | Denial of service | fetch on a hook or detect probe; trickling upstream or Laya | medium | mitigate | any `GSD_PATH_JEV_DEADLINE_SECONDS` disables the upstream fetch (`skipped_deadline`); each public fetch has a 5 s total `_Deadline` and each Laya identity GET a `_PROBE_TIMEOUT` one, armed in `_exchange` and checked in `_read_body` (review C1-13, trickle tests); 1 MiB cap; NoRedirect via `_exchange` Evidence: deadline skips fetch and identity GETs, 5 s, 1 MiB, NoRedirect; test_public_fetch_stops_at_its_deadline | closed |
| T-34-21 | Tampering | fetch on the answer path | high | mitigate | `screen` and `_selection` never call `_public_get`; `_note_models` and `_note_unknown_items` only write local notes; tested with a fetcher that fails on call, including the unknown-field, unknown-type and feature-refusal notes Evidence: answer path never reaches _public_get; test_answer_path_never_fetches | closed |
| T-34-22 | Spoofing / SSRF | fetched URLs | medium | mitigate | upstream URLs are module constants (https only via `_remote_url`); the only configurable origin is the Laya address already gated by Plan 02's consent rule; doc links are limited to docs.typesafe.ai (Plan 05) Evidence: upstream URLs are constants; _remote_url; consent gate before _laya_learn | closed |
| T-34-23 | Repudiation | capability cells | medium | mitigate | the TABLE cells are never written by learning code; a test checks the long_context and batch cells stay `unsupported` after upstream notes name them Evidence: test_new_upstream_feature_keeps_the_cell | closed |
| T-34-SC (plan 06) | Tampering | package installs | low | accept | no package install in this plan Evidence: no dependency change (git diff --stat 76269a2 HEAD over lock/manifest files is empty); stdlib only | closed |
| T-34-24 | Tampering | prompt injection through stored notes | medium | mitigate | SKILL.md and reference.md say the notes are unverified data, never instructions; an eval asserts the agent does not follow them Evidence: SKILL.md, reference.md; eval edge-laya-notes-new with a stored instruction record | closed |
| T-34-25 | Repudiation | over-claiming Laya accuracy | medium | mitigate | the limit sentence in SKILL.md and backends/laya.md with date, case count and percentage, pinned by a doc-contract test Evidence: SKILL.md limit line + ## Evidence date; laya.md; test_doc_limit_sentence_in_skill_and_laya_backend | closed |
| T-34-26 | Information disclosure | first-run answer | low | mitigate | reference.md says `config set` refuses a URL with a user name or password; the eval input files hold no key and no machine path Evidence: reference.md userinfo refused; evals/files hold no key or machine path | closed |
| T-34-SC (plan 07) | Tampering | package installs | low | accept | no package install in this plan Evidence: no dependency change (git diff --stat 76269a2 HEAD over lock/manifest files is empty); stdlib only | closed |
| T-34-27 | Tampering | skill tree (removed backend or delegated install) | medium | mitigate | the guard test runs in the unit tier on every commit that touches the skill and fails with the file and line; the delegation rule reads joined sentences with a verb-bound negation, and its non-vacuity fixtures include wrapped, named-repository, unrelated-negation and `not only` instructions (review C1-15 and its residual); the guard runs after Plan 07 (review C2-7), so it never gates a half-edited tree Evidence: guard test in the unit group; non-vacuity cases incl. Python constants (WR-106) | closed |
| T-34-28 | Elevation of privilege | a code path that runs a package manager or container tool | high | mitigate | the guard's code rule fails on any such string constant in the skill's Python, so no install, upgrade or restart of Laya can ship Evidence: guard code_problems on TOOL_ARGV/TOOL_TEXT; test_guard_flags_each_violation | closed |
| T-34-29 | Repudiation | stale line cites in the design record | low | mitigate | cites_check.py ties each cite to a backticked name on the same line Evidence: design.md cites re-mapped and checked after the close-out fixes (ccd67b3, tmp/auto/r325/c34/fix_cites.py) | closed |
| T-34-SC (plan 08) | Tampering | package installs | low | accept | no package install in this plan Evidence: no dependency change (git diff --stat 76269a2 HEAD over lock/manifest files is empty); stdlib only | closed |
| T-34-30 | Information disclosure | spike requests to TypeSafe | high | mitigate | sent only when the probe's typesafe row is usable under the user's own recorded consent and key; synthetic summaries with no code or secrets; the driver never grants consent and never prints a key Evidence: tmp/p34/09/live.py consent via recorded grant only; synthetic cases | closed |
| T-34-31 | Tampering | real state and config | high | mitigate | XDG_STATE_HOME points at tmp/p34/09/state; the driver snapshots the real ai-kit config folder's mtimes and fails on any change; the check runs after every `calibrate` outcome, a timed-out or unstartable `eval_cases` run included (review C3-2) Evidence: live.py scratch STATE, snapshot compare after each run | closed |
| T-34-32 | Tampering | `--calibrate` rewriting min_confidence | medium | mitigate | a rewrite is kept only with the jev tests green, the comment and backends/laya.md updated, and the SUMMARY naming it Evidence: no rewrite: laya.md proposal null, 0.7 kept | closed |
| T-34-33 | Repudiation | calibration claims | medium | mitigate | the record carries version or fingerprint, revision, n and date; "not run" is recorded with its reason, never left blank; a non-zero `eval_cases.py --calibrate` exit or a missing proposal is recorded as "not run" with its stderr kept (review C2-9, proved by `selftest`); a `--record` (900 s) or `--calibrate` (120 s) run that times out or cannot start is caught by `run_logged` (`subprocess.TimeoutExpired`, `OSError`) and recorded as a dated "not run" with its partial output kept (review C3-2, proved by `selftest` with a patched `subprocess.run`); the spike's answers are validated by `checked_response` and mapped by item id, and `selftest` proves the mapping on a stub before any live use (review C1-19) Evidence: eval_cases.py server identity per backend (WR-206); n != 32 exits 1 | closed |
| T-34-43 | Information disclosure | live driver's Laya address and health check | high | mitigate | the driver never resolves an address or opens a socket itself: `_laya_url`/`_laya_url_source` (on `laya_url_setting`, project layer and declined answer included) pick the host and the client's gate-first `_row_probe` refuses an off-loopback host without its consent record before any socket (review C1-17) Evidence: live.py uses the client's _laya_url/_row_probe only | closed |
| T-34-44 | Information disclosure | TypeSafe key resolution under a scratch state folder | high | mitigate | the driver reads only the client's key source label; for a state-file key it passes that file's path as `JEV_API_KEY_FILE`, replacing a set but unusable value, so the client reads the 0600 file itself; no key is copied, printed or written (review C1-18 and its residual) Evidence: live.py passes the key file path, never the value | closed |
| T-34-SC (plan 09) | Tampering | package installs | low | accept | no package install; no Laya upgrade step Evidence: no dependency change (git diff --stat 76269a2 HEAD over lock/manifest files is empty); stdlib only | closed |
| T-34-34 | Tampering | external lanes | high | mitigate | `--mode review` stops a lane on `tree=dirty`; outputs only under ignored `tmp/`; a verdict counts only with `tree=clean`; HEAD and tracked files checked unchanged at the checkpoint Evidence: runner tree= status; lanes.py fails a lane on tree=dirty | closed |
| T-34-35 | Information disclosure | host configs and HOME | high | mitigate | AI_KIT_REFUSE_REAL_HOME=1 for every child; the drivers read `.planning/config.json` only for judge ids; `effort-env` prints set or unset, never values Evidence: lanes.py child_env AI_KIT_REFUSE_REAL_HOME=1 | closed |
| T-34-36 | Tampering | publish step | high | mitigate | byte-for-byte copy refusing different existing bytes; generated report; `check --require-current` before the commit; check-dogfood guards every later push Evidence: publish.py byte compare; check.py --require-current; check-dogfood | closed |
| T-34-37 | Repudiation | substitutes | medium | mitigate | every substitute is a referee-three lane ingested with `--replaces` and `--reason`; verdict_facts lists every probe and substitution; quota and auth stops are reported, never retried on another model Evidence: judge_loop --replaces needs --reason; verdict_facts lists substitutes | closed |
| T-34-38 | Tampering | judged set | medium | mitigate | `judged.py` stops on any changed skill outside the judged and fact-only sets, and never judges commit-fold or a project-rules skill Evidence: judged.py excludes removed-later skills; unexpected set exits | closed |
| T-34-SC (plan 10) | Tampering | package installs | low | accept | no package install in this plan Evidence: no dependency change (git diff --stat 76269a2 HEAD over lock/manifest files is empty); stdlib only | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-34-01 | T-34-SC (plan 01) | no package install in this plan (stdlib only) | plan threat register (orchestrator-verified) | 2026-11-15 |
| AR-34-02 | T-34-SC (plan 02) | no package install in this plan | plan threat register (orchestrator-verified) | 2026-11-15 |
| AR-34-03 | T-34-SC (plan 03) | no package install; `laya` on PyPI is read as data only | plan threat register (orchestrator-verified) | 2026-11-15 |
| AR-34-04 | T-34-15 | two small TOML reads per `_send`; measured cost is negligible next to an HTTP call | plan threat register (orchestrator-verified) | 2026-11-15 |
| AR-34-05 | T-34-SC (plan 04) | no package install in this plan | plan threat register (orchestrator-verified) | 2026-11-15 |
| AR-34-06 | T-34-SC (plan 05) | no package install; the official typesafe-ai skill is never installed or copied | plan threat register (orchestrator-verified) | 2026-11-15 |
| AR-34-07 | T-34-SC (plan 06) | no package install in this plan | plan threat register (orchestrator-verified) | 2026-11-15 |
| AR-34-08 | T-34-SC (plan 07) | no package install in this plan | plan threat register (orchestrator-verified) | 2026-11-15 |
| AR-34-09 | T-34-SC (plan 08) | no package install in this plan | plan threat register (orchestrator-verified) | 2026-11-15 |
| AR-34-10 | T-34-SC (plan 09) | no package install; no Laya upgrade step | plan threat register (orchestrator-verified) | 2026-11-15 |
| AR-34-11 | T-34-SC (plan 10) | no package install in this plan | plan threat register (orchestrator-verified) | 2026-11-15 |
| AR-34-12 | T-34-06 residual (review IN-102) | A Laya consent grant is bound to the host only, not to scheme or port: without a key a project file can move a consented host from https to http or another port without a new grant (with a key, `insecure_url` still refuses http off loopback). Host-bound consent is the design accepted at planning (34 convergence, ledger 2026-11-15 18:10: 'off-loopback Laya needs host-bound consent'; SPEC: consent rules unchanged); no question text is sent to any host that was not granted. | orchestrator decision at planning, carried by the owner-locked SPEC constraint | 2026-11-15 |
| AR-34-13 | T-34-30/31/33/43/44, T-34-34..38 evidence | The evidence for these rows lives in ignored scratch drivers (tmp/p34/09/live.py, tmp/judge-34/*), as the plans specify; the committed records (laya.md calibration record, .planning/judge/) are what persists. | plan design (34-09, 34-10) | 2026-11-15 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-15 | 54 | 53 | 1 (T-34-29, low, non-blocking) | gsd-security-auditor (opus), close-out part 1 |
| 2026-11-15 | 54 | 54 | 0 | close-out part 1 after ccd67b3 (T-34-29 cites re-mapped and checked) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-15
