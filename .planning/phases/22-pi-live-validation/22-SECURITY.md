---
phase: "22"
slug: pi-live-validation
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (high)
threats_open: 0
asvs_level: 1
block_on: high
created: "2026-10-23"
---

# Phase 22 - Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified at HEAD 960eb90 (diff base e3c1b93), including the review fixes a53569b..8bfa224.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| spike pi run / smoke -> pi agent dir and HOME | pi and the gsd-core installer write into the dirs they are pointed at | scratch dirs only; dummy key literal |
| pi RPC stdout -> parser | untrusted JSON becomes model records | model ids, integers |
| owner raw capture -> committed fixture | raw capture holds transport fields | allowlisted model fields only |
| user value -> plan -> project config -> every pi request | `pi.sonnet` is written verbatim into each request | a bare model id |
| harness snapshot -> real home | hashes protected files of the real config | hashes and labels only |
| repo files -> external judge models / judge output -> evidence | SKILL.md text out, scores back into tracked evidence | public skill text |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation (evidence) | Status |
|-----------|----------|-----------|----------|-------------|-----------------------|--------|
| T-22-01 | Information disclosure | spike pi runs, mock log | high | mitigate | 22-SPIKE-PI-AGENTS.md "Run conditions": `env -i`, scratch HOME/PI_CODING_AGENT_DIR, `dummy-not-a-key` only; `live/pi_mock_provider.py` binds 127.0.0.1 and logs only `{path, model}` (self-test ok); `secret-scan` over the phase dir and fixture exits 0; no `/home/bazzite` or `/var/home` string under the phase dir | closed |
| T-22-02 | Tampering | gsd-core installer run | high | mitigate | installer runs from a throwaway install HOME under an env allowlist (`INSTALL_ENV_KEEP`, tests/gsd_curated_eval.py `_install_local`); 22-SMOKE-PI.md "Local install" and "Real-home guard" (`snapshot --check`: ok) | closed |
| T-22-03 | Elevation of privilege | `--approve` on scratch project | medium | mitigate | spike arms A-D use `--approve` on the scratch project only; no `/trust` or persisted trust outside the scratch agent dir; pi `trust.json` and `settings.json` are strict snapshot entries (`PI_TRUST_LABEL`, `PI_SETTINGS_LABEL`, test `test_pi_settings_and_trust_are_strict`) | closed |
| T-22-04 | Denial of service | orphan mock or pi processes | low | mitigate | mock stops by SIGTERM handler; 22-01-SUMMARY.md line 108 records the leak check; `pgrep` at audit time shows no `pi_mock_provider` process | closed |
| T-22-05 | Tampering | `parse_pi_models` input validation | medium | mitigate | detection.py `_pi_json_line` (catches JSONDecodeError, ValueError, RecursionError), `_pi_models_envelope` (exactly one envelope, `success is True`), `_exact_int` (bool excluded); never raises; `TestPiRpcModels` passes (tests.test_ai_kit_spec OK) | closed |
| T-22-06 | Information disclosure | `trim_pi_capture.py` and committed fixtures | high | mitigate | `_ALLOWED_MODEL_FIELDS` allowlist, `_FORBIDDEN_MARKERS` fail-closed check, `secret_scan` on the staged file before `os.replace`; raw file read-only input; committed fixture `tests/fixtures/pi_rpc_get_available_models.json` passes secret-scan (rc 0) | closed |
| T-22-07 | Tampering / DoS | `plan-set` `pi.sonnet` | high | mitigate | `roles.pi_session_ids` (bare ids of `PI_PROVIDER` only), `plan_io.pi_sonnet_value_problem` called from plan_edit.py:496 (force-immune) and, after a53569b, from `load_plan_and_inventory` -> `pi_sonnet_problem`, which both `apply` (apply.py:55) and the CLI dry run (cli.py:604) use; tests `test_pi_sonnet_other_values_refused_even_forced`, `test_hand_edited_pi_sonnet_outside_provider_refused_before_write` pass | closed |
| T-22-08 | Repudiation (over-claim) | pi labels, SKILL.md pi row | medium | mitigate | SKILL.md:259 keeps `**not live-validated**` and `session-steer (static + mock evidence)`; verbatim pins in tests/test_curated_config_apply.py:2415-2508; recommend.py `_PI_NOTE`/`_PI_SESSION_EFFECT`; no pi `model_overrides` | closed |
| T-22-09 | Information disclosure | inventory env read | low | mitigate | inventory.py reads only `PI_PROVIDER`, pattern-validated by `_PI_PROVIDER_RE`, pi host only; test `test_pi_session_provider_recorded_on_pi_only` | closed |
| T-22-10 | Repudiation (vacuous oracle) | pi oracle `model == ""` | medium | mitigate | `_control_one` for pi expects every agent to fail with `resolve_model_ids` unset; `pi_hook_probe` compares wire to plan for 5 combos; `_matrix_failed` requires `len(probes) == len(COMBOS)`; smoke: control_1/2 ok, 5/5 probes | closed |
| T-22-11 | Tampering | matrix applies | medium | mitigate | `refuse_repo_apply` in `_apply_bundle` (gsd_curated_eval.py:749), scratch `GSD_HOME` per bundle, strict snapshot tests; smoke "protected set unchanged" | closed |
| T-22-12 | Information disclosure | `snapshot` pi entries | high | mitigate | snapshot lists only `agents`, `extensions`, `skills`, `gsd-core` trees plus `settings.json`/`trust.json`; `auth.json`, `models.json`, `models-store.json`, `sessions` never listed; hermetic test `test_pi_noncredential_trees_are_strict_and_sensitive_files_are_ignored`; WR-01 fix 8bfa224 hashes a symlinked root by link text only (`_tree_sha`) | closed |
| T-22-13 | Tampering | headless smoke | high | mitigate | scratch HOME/PI_CODING_AGENT_DIR, installer under own throwaway HOME, `refuse_repo_apply` (lines 4371, 4718), real-home `snapshot --check` ok in 22-SMOKE-PI.md | closed |
| T-22-14 | Repudiation (over-claim) | `22-SMOKE-PI.md` | medium | mitigate | labelled headless harness evidence; "Interactive run (owner): not run (owner)"; verdict line computed from attempt 2 files; SKILL.md label unchanged | closed |
| T-22-15 | Repudiation (over-claim) | pi label lift | high | mitigate | `live/check_pi_live.py` rejects a lifted row without S1-S5 pass and an unlifted row once they pass; L3b-only no longer earns a live verdict (5262e92); `--self-test` ok both directions | closed |
| T-22-16 | Information disclosure | owner artifacts, raw capture | high | mitigate | trimmer allowlist plus fail-closed marker/secret scan (see T-22-06); 22-INTERACTIVE-PI.md runbook; no owner artifacts committed yet (secret-scan of phase dir rc 0) | closed |
| T-22-17 | Tampering | owner run against `~/.pi/agent` | medium | mitigate | `snapshot --out/--check` wrapping, `--host-rewrite` choices restricted to `CURSOR_CLI_CONFIG_LABEL`, `PI_SETTINGS_LABEL`, `PI_TRUST_LABEL` (argparse `choices`); runbook steps in 22-INTERACTIVE-PI.md | closed |
| T-22-18 | Repudiation | judge evidence vs committed skill bytes | high | mitigate | Closed after re-run (r1): both judges re-ran on `6faf9b459284c6f0` (Opus 106, opencode 114, both pass); the earlier post rows are marked superseded and `digest --check` prints `digests ok`. Originally: commit a53569b (review fix) edited SKILL.md after the judges ran on digest `2e55b8f4212d167c`. At HEAD `python3 tests/gsd_curated_eval.py digest` prints `6faf9b459284c6f0` and `digest --check 22-SKILL-JUDGE.md` exits 1 (`2e55b8f4212d167c != 6faf9b459284c6f0`). The plan required a fix to supersede earlier post rows and re-run both judges; neither happened | closed |
| T-22-19 | Information disclosure | judge prompts | low | accept | see Accepted Risks Log AR-22-01 | closed |
| T-22-20 | Denial of service | hung judge | low | mitigate | runner deadlines and status lines recorded in 22-SKILL-JUDGE.md "Judge attempts" (`status=ok`, elapsed 273 s and 78 s, `tree=clean`); no leaked process at audit time | closed |
| T-22-21 | Elevation of privilege | cached package `pi/gsd.cjs` executed in node | low | accept | see Accepted Risks Log AR-22-02; `pi_hook_probe` uses a 60 s timeout and explicit env; WR-04 fix 8bfa224 enforces package version equals the tools version | closed |
| T-22-SC | Tampering | npm/pip/cargo installs (plans 01-07) | high | mitigate | no package manifest, lockfile or pyproject change in `e3c1b93..HEAD`; installer comes from the cache only (`_cached_installer`, "never npx in the smoke") | closed |

*Status: open - closed*
*Severity: critical > high > medium > low - only open threats at or above `high` count toward threats_open*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-22-01 | T-22-19 | Only the public skill text and a rubric copy go to judges; no config, credential or user file is referenced. Declared `accept` in 22-07-PLAN.md. | plan 22-07 threat model | 2026-10-23 |
| AR-22-02 | T-22-21 | The cached gsd-core package is the same release the checkout pins and is already trusted as this repo's installer; version-matched, explicit env, 60 s timeout. Declared `accept` in 22-04-PLAN.md. | plan 22-04 threat model | 2026-10-23 |

---

## Unregistered Flags

None. The phase SUMMARY files carry no `## Threat Flags` section.

---

## Open Threat Detail

None open. Closed in the re-audit: T-22-18 (high). The original detail follows.

- T-22-18 (high, blocking at first audit): re-run both skill-judge lanes on the current SKILL.md digest (`6faf9b459284c6f0`), mark the earlier post rows in `22-SKILL-JUDGE.md` `superseded (6faf9b459284c6f0)`, add the new post rows, and confirm `python3 tests/gsd_curated_eval.py digest --check .planning/phases/22-pi-live-validation/22-SKILL-JUDGE.md` prints `digests ok`. The edit in a53569b is a wording-only sentence, but the plan's rule is that a fix voids the earlier rows. This audit changed no code or evidence.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-23 | 22 | 21 | 1 | gsd-security-auditor (ASVS L1, block_on high) |
| 2026-10-23 | 22 | 22 | 0 | orchestrator re-check after the r1 judge re-run (`digest --check`: digests ok) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-23 (T-22-18 closed by the r1 judge re-run)
