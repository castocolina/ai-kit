---
phase: 26
slug: session-self-resume-and-opengsd-quota-rules
status: SECURED
threats_total: 45
threats_secured: 45
threats_open: 0
threats_open_nonblocking: 0
asvs_level: 1
block_on: high
audited: 2026-10-30
audited_head: 94e7fe0
---

# Phase 26 Security Audit

The threat register comes from the `<threat_model>` blocks of 26-01 to 26-12: 44 numbered threats
(`T-26-01` to `T-26-44`) plus the shared `T-26-SC` row. Each mitigation was checked in the shipped
code at HEAD `94e7fe0` and tied to a passing test. Two threats are `accept` rows (T-26-32 and
T-26-37) and are closed by a documented residual risk.

Verdict: SECURED, 45/45. No threat reaches the `block_on: high` threshold. One low-severity gap
(T-26-30) was open at the start of the audit and is closed by `fix(26-secure)` in this phase.

## Verification runs (this audit)

- Targeted unit modules, all passing: `test_ai_kit_session_wake`, `test_ai_kit_session_wake_fire`,
  `test_ai_kit_session_wake_reset`, `test_claude_session_wake_hook`, `test_arch`,
  `test_ai_kit_project_rules_agents`, `test_ai_kit_project_rules_all`,
  `test_ai_kit_project_rules_all_e2e`, `test_ai_kit_rules_common`, `test_ai_kit_spec_gsd`,
  `test_ai_kit_spec_superpowers`, `test_curated_config_script` and `test_cross_ai_runner_e2e`
  (which runs the runner `--self-test`).
- `skill-judge/check_verdicts.py` prints `verdicts ok`; `--gate` prints three `gate pending:` lines,
  so the phase is correctly not reported as skill-judge accepted (see T-26-43).
- Install surface: since the phase base, `uv.lock` is unchanged and `pyproject.toml` gained one
  pyright `extraPaths` line. The new runtime Python imports only the standard library and in-repo
  modules (`ai_kit_spec.detection`). No `package.json` or lockfile changed.
- No absolute machine path appears in the touched code or docs.

## Threat register

| ID | Sev | Disp | Mitigation | Evidence | Status |
|----|-----|------|------------|----------|--------|
| T-26-01 | medium | mitigate | Child marker set after both scrub loops | `cross-ai.mjs:3642`; case `child-marker-env` (parent value `0`); `test_cross_ai_runner_e2e` `--self-test` | CLOSED |
| T-26-02 | medium | mitigate | Dogfood copy re-rendered through `ensure-runner` and pinned | `.planning/scripts/cross-ai.mjs`; `TestDogfoodCopy.test_dogfood_copy_matches_template_body` | CLOSED |
| T-26-03 | high | mitigate | Session id charset check before any path or unit name; every `ExecStart` word escaped; no shell | `state.py:24,66`; `units.py:54-65`; `TestServiceEscaping.test_dollar_is_doubled_only_in_execstart` | CLOSED |
| T-26-04 | high | mitigate | `Environment=` carries PATH, HOME and four XDG dirs only | `units.py:21-28,95-104`; `TestArmSafety.test_secret_sentinels_never_reach_any_written_file_or_systemctl_log` | CLOSED |
| T-26-05 | high | mitigate | Liveness by pid + start time + boot id; checked before and under the lock | `liveness.py:85-91`; `fire.py:310,420`; `test_recorded_pid_with_other_start_time_resumes_once`, `..._other_boot_id_...` | CLOSED |
| T-26-06 | medium | mitigate | Permission mode recorded and printed; `unknown`/`default` add no flag; claude always `--permission-prompts none` | `hosts.py:33,92-96`; `arm.py:498-509`; `TestPermissionMode.test_bypass_copied_and_replayed` | CLOSED |
| T-26-25 | medium | mitigate | AST isolation rules both ways with non-vacuity cases | `test_arch.py:775-840,1830,1839`; `TestArchNonVacuity.test_wake_isolation_flags_phase25_reach` | CLOSED |
| T-26-40 | high | mitigate | `validate_state` on every read; `created` deleted only when it equals one of the wake's own absolute paths; `fire` re-checks under the lock | `state.py:230-247`; `fire.py:96-121,298-312,386`; `test_same_named_files_in_foreign_folders_survive`, `test_one_field_invalid_states_are_removed_by_name` | CLOSED |
| T-26-07 | high | mitigate | Charset check before any write | `state.py:63-72`; `TestArmIdentity.test_missing_empty_and_unsafe_ids_refused_without_writes` | CLOSED |
| T-26-08 | high | mitigate | Sentinel test over every written file; allowlisted env; 0600/0700 modes | `units.py:95`; `state.py:75-90`; sentinel test as T-26-04 | CLOSED |
| T-26-09 | medium | mitigate | `update_state` serializes the refresh with the wake-count increment | `state.py:128-153`; `test_update_state_serializes_fifty_plus_fifty_increments` | CLOSED |
| T-26-10 | low | mitigate | Interpreter check refuses before any write | `arm.py:128-163`; `test_shebang_interpreter_is_checked_against_filtered_path` | CLOSED |
| T-26-11 | high | mitigate | Marker check plus ancestor scan before any write | `arm.py:168-181`; `liveness.py:143`; `TestChildRefusal.test_marker_refuses_and_writes_nothing` | CLOSED |
| T-26-12 | high | mitigate | Bypass copied only from the host's own command line; override validated | `hosts.py:92-96`; `arm.py:263-270`; `test_arm_flag_override_and_invalid_refused` | CLOSED |
| T-26-13 | medium | mitigate | Id checked before any glob; exact stem match; truncated listing is `unknown`; argv list with timeout | `hosts.py:117-195`; `TestSessionProbe.test_longer_ids_missing_and_pi_fire_gives_up`, `test_opencode_truncated_arm_refuses_fire_skips` | CLOSED |
| T-26-14 | low | mitigate | Unverified sources printed as unverified | `hosts.py` `verified`/`evidence`; `arm.py:496-509`; `test_ancestor_unverified_nearest_match` | CLOSED |
| T-26-15 | high | mitigate | Hard cap 24 under a lock; one finish step; done marker first | `state.py:22,178-187`; `fire.py:446-490`; `TestGiveUp`, `TestFireSequence` | CLOSED |
| T-26-16 | high | mitigate | Non-blocking flock for the whole resume; liveness before and under the lock | `fire.py:310,417-431`; `TestOverlap`, `TestFireInterleaving` | CLOSED |
| T-26-17 | medium | mitigate | `RESUME_TIMEOUT_S` with process-group kill; bounded `notify-send` | `fire.py:37-38,152,344-379`; `test_resume_timeout_kills_group_and_records_124`, `test_slow_notifier_is_bounded_and_never_fails_the_fire` | CLOSED |
| T-26-18 | low | mitigate | Notice names the state path, reason and exit code only | `fire.py:164-166`; `test_give_up_notifies_once_with_session_bus` | CLOSED |
| T-26-19 | high | mitigate | Only `calendar_line` of a parsed UTC datetime reaches the unit | `arm.py:469-470`; `reset_parse.py:154-160`; `TestResetGrammar`, `TestResetTracer` | CLOSED |
| T-26-20 | medium | mitigate | Runner redaction policy ported; hex runs; 2000 code-point cap | `reset_parse.py:57-148`; `TestResetEvidence.test_structured_payload_keys_are_redacted`; hook `test_structured_error_details_store_the_redacted_value_only` | CLOSED |
| T-26-41 | medium | mitigate | Failed first arm and failed refresh roll back | `arm.py:573-665`; `TestArmRollback` (4 tests) | CLOSED |
| T-26-21 | medium | mitigate | Reset refused outside (now, now + 7 d]; hourly wake stands; ASCII-digit guard | `reset_parse.py:18,165-172,261-265`; `arm.py:325-348`; `test_seven_day_edges`, `test_reset_at_seven_day_edges` | CLOSED |
| T-26-22 | high | mitigate | argv list, no shell; hook payload type-checked and capped | `claude_session_wake.py:61-100`; `TestStopFailureHook` | CLOSED |
| T-26-23 | medium | mitigate | `--only-if-armed`: only a session its orchestrator armed is refreshed | `arm.py:204-214`; `test_an_unarmed_session_writes_nothing`, `test_a_payload_without_resets_never_calls_arm` | CLOSED |
| T-26-24 | low | mitigate | 8 s monotonic deadline, group kill, fail-open | `claude_session_wake.py:34-42,92-117`; `claude_session_start.py:47`; `TestHookDeadline` | CLOSED |
| T-26-26 | medium | mitigate | Probe: argv list, 5 s timeout, env PATH and HOME only; path printed on stderr | `gsd_identity.py:102-112`; `cli.py:181`; `test_probe_env_holds_only_path_and_home` | CLOSED |
| T-26-27 | medium | mitigate | Exact `packageName` equality; other shapes `absent` or `unverified` | `gsd_identity.py:46-59`; `test_exact_package_is_ok`, `test_lookalike_and_other_packages_are_absent` | CLOSED |
| T-26-28 | medium | mitigate | Probe env restricted; no env value in a finding | `gsd_identity.py:102-112`; `test_probe_env_holds_only_path_and_home` | CLOSED |
| T-26-44 | high | mitigate | e2e tests clear the env, drop host-home overrides, skip without checkout-local gsd-tools, assert the probe ran that file | `test_ai_kit_project_rules_all_e2e.py:49,75,110,139,155-158` | CLOSED |
| T-26-29 | low | mitigate | `unverified` reaches `notices` in remediate and the aggregate | `aggregate.py:36-54`; `test_unverified_notice_reaches_rules_all_aggregate` | CLOSED |
| T-26-30 | low | mitigate | Line-by-line scan; runner-phrase gap bounded to 200 characters | `classification.py` `_runner_pattern`, `hardcoded_worker_counts`; `TestParallelTestTable.test_a_very_long_line_scans_in_bounded_time` | CLOSED (fixed in this audit) |
| T-26-31 | low | mitigate | Dated sources; unknown stacks listed and their clause says so | `classification.py:31-36,263-298`; `test_unverified_stack_clause_says_so_and_is_listed`, `test_every_row_has_a_dated_source_and_a_clause` | CLOSED |
| T-26-32 | medium | accept | Residual risk (subagent running `done`/`disarm` is undetectable) stated in the SKILL.md NEVER list; worst case an early disarm, never a wrong resume | `ai-kit-session-wake/SKILL.md:23-26` | CLOSED (accepted) |
| T-26-33 | low | mitigate | Shim resolved once, as the sibling of the loaded executor skill; no home path | `ai-kit-spec-execute-gsd/references/session-wake.md:26`; `ai-kit-spec-execute-superpowers/SKILL.md:149`; `test_ai_kit_spec_gsd.py:2275-2379`, `test_ai_kit_spec_superpowers.py:2591-2633` | CLOSED |
| T-26-34 | low | mitigate | Every wake result is printed and never fails the run | `ai-kit-spec-execute-gsd/SKILL.md:361`; `ai-kit-spec-execute-superpowers/SKILL.md:135` | CLOSED |
| T-26-42 | medium | mitigate | `WAKE_OWNED=1` only after this run's own `armed` line; `done` passes host and id and runs only then | `ai-kit-spec-execute-superpowers/SKILL.md:159-164,369-374`; `ai-kit-spec-execute-gsd/references/session-wake.md:46,123`; `WAKE_OWNED` tests | CLOSED |
| T-26-35 | medium | mitigate | Digest-bound reports and verdicts; stale digest or round fails the checker | `check_verdicts.py:58-64` | CLOSED |
| T-26-36 | low | mitigate | Checker recomputes lowest score and highest counts | `check_verdicts.py:73-82` | CLOSED |
| T-26-43 | medium | mitigate | `--gate` passes only PASS or an `Owner-decision:` line; the three other verdicts are carried as pending | `check_verdicts.py:84-92`; live `--gate` exits 1 with 3 `gate pending:` lines; SJ-1..SJ-3 in `26-OWNER-CAPTURES.md` | CLOSED |
| T-26-37 | low | accept | Packages sent to judge lanes are public repo docs; no credential or config is sent | `26-11-PLAN.md` threat row | CLOSED (accepted) |
| T-26-38 | medium | mitigate | Live unit check under `env -i` with scratch HOME and XDG dirs; no arm, enable or reload | `26-12-SUMMARY.md`; `26-OWNER-CAPTURES.md` note (f) discloses a judge-lane read-only breach | CLOSED |
| T-26-39 | medium | mitigate | Every unverified behavior is an owner capture naming what it flips | `26-OWNER-CAPTURES.md` items 1-12 | CLOSED |
| T-26-SC | high | mitigate | No package installed in any plan | `uv.lock` unchanged; one pyright `extraPaths` line in `pyproject.toml`; stdlib-only import scan | CLOSED |

## Gaps closed in this audit

- **T-26-30 (low)**: `_runner_pattern` joined runner words with `\b.*\b`, so `hardcoded_worker_counts`
  was quadratic on one very long line (about 1 s for 24,000 characters, with a Go, Maven or Rust
  marker file present). The gap is now `.{0,200}`. `test_a_very_long_line_scans_in_bounded_time`
  pins the time bound and a 150-character gap that still matches.
- **Owner-decision grammar (unregistered, fail-closed)**: the answer lines staged in
  `26-OWNER-CAPTURES.md` (for example `Owner-decision: ai-kit-spec-execute-gsd accept 101`) did not
  match the gate's grammar `Owner-decision: <skill> accepts <VERDICT> (<date>, <where>)`, so an
  owner pasting them would still see `gate pending`. The lines now use the gate grammar, and
  `tests/test_phase26_owner_captures.py` matches them against the checker's own regex.

## Accepted risks

- T-26-32: a subagent that runs `done`/`disarm` cannot be told apart from the orchestrator by env
  or process tree. The wake can only disarm early; it never resumes the wrong session. A hook-based
  agent guard is a backlog candidate.
- T-26-37: judge lanes receive public repo docs only.

## Unregistered flags

- `check_verdicts.py` has no dedicated unit test of its own checks (stale digest, tampered score);
  it is exercised by running it. It is a phase-local script bound to the real skill packages, so a
  fixture test would need a synthetic copy of the whole layout. Left as is; the live run backs
  T-26-35, T-26-36 and T-26-43.
- `26-OWNER-CAPTURES.md` states that live-unit behaviors (reboot survival, first fire, headless
  exit during a limit, StopFailure payload) are unverified. T-26-39 requires only that these
  captures exist and name what they flip; the behaviors themselves are not asserted here.
