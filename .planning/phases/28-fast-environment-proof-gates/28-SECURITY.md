---
phase: "28"
slug: "fast-environment-proof-gates"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-04"
---

# Phase 28 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| test module -> host CLIs on the caller's PATH | a test or the product code it runs can spawn a real, credentialed host CLI | host credentials, paid model calls |
| test module -> owner's home | HOME, XDG and host config-dir variables point at real configuration | owner config files (sensitive) |
| commit hook env -> test subprocesses | git index and work-tree variables reach a test's own git calls | the real git index |
| environment -> runner template | `AIKIT_XAI_SELFTEST_LOAD` is caller-controlled | a load reading (untrusted number) |
| template -> rendered project copies | the dogfood copy and copies in other repos run real cross-AI work | real run limits |
| test temp dir -> enclosing git repository | a temp dir inside a repo lets git see the repo | the enclosing repo's history and index |
| check-dogfood -> live project files | the only sanctioned reader of `.planning/config.json` and the runner copy | owner-local config (dirty, uncommitted) |
| live `.planning/` and archived data -> tests and fixtures | owner-local history must not decide a result; copies may carry paths or keys | machine paths, key-like strings |
| staged file names -> runner and git | file names are attacker-shaped strings to the mapper | file names (untrusted text) |
| hook config and pushed refs -> commit and push gates | a config edit or an unseen ref can weaken a gate | gate decisions |
| matrix and timing runs -> source checkout and owner's home | the tools clone the checkout and run the suites again | owner venv, home, reports |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-28-01 | Information disclosure | `run_module` env, host CLIs | high | mitigate | `baseline_env` (temp HOME, `AI_KIT_REFUSE_REAL_HOME=1`, drops host signals, `HOME_OVERRIDE_VARS`, `CREDENTIAL_ENV_VARS`, host config prefixes); tripwire first on PATH; `tool_cache_forwards` caches only; TripwireTest, BaselineEnvTest, DriftTest | closed |
| T-28-02 | Tampering | `write_tripwire`, `write_host_fakes` | low | mitigate | names from `HOST_CLI_NAMES` / `HOST_NAMES` only; `shlex.quote` / `repr` for paths | closed |
| T-28-03 | Tampering | git variables in module env | medium | mitigate | `baseline_env` drops `GIT_*` except `GIT_EXEC_PATH`; sets `GIT_CEILING_DIRECTORIES`, `GIT_CONFIG_NOSYSTEM` | closed |
| T-28-04 | Tampering | `measuredLoadPerCpu`, real run limits | high | mitigate | reading only inside `blackBoxSelfTest`; `SelfTestCeilingPins` pins the real limits and `budgetMs` | closed |
| T-28-05 | Denial of service | `loadFactor` | low | mitigate | non-finite or <= 0 gives 1; clamped to 4 | closed |
| T-28-22 | Denial of service | module process groups, interrupt handling, self-test runners | medium | mitigate | own session per module, group-only `killpg`, SIGTERM then SIGKILL after `MODULE_STOP_GRACE_SECS`, interrupt cancels futures and stops live groups; self-test forwards SIGTERM to `selfTestAbort`; ModuleDeadlineTest, StopGroupTest; no `stress-ng` left (checked 2026-11-04) | closed |
| T-28-06 | Tampering | `tests/test_worktree_e2e.py` git calls | low | mitigate | `GIT_CEILING_DIRECTORIES` set to the test's temp root | closed |
| T-28-07 | Information disclosure | `tmp/p28/longpath.sh` | low | mitigate | one-off script, gone with no clone or scratch HOME left; its job is now the matrix long-path environment (T-28-17/18/19) | closed |
| T-28-08 | Tampering | `check_no_write` guard runs | high | mitigate | sha256 fingerprint of live files before and after; `--root` elsewhere refused without `--skip-no-write`; skipped guard counted and warned; matrix hashes the resolved gsd-core folder | closed |
| T-28-09 | Information disclosure | check-dogfood output | low | mitigate | prints relative paths, test ids and reasons only | closed |
| T-28-23 | Elevation of privilege | check-dogfood runs test code at push | medium | mitigate | three fixed `GUARD_TESTS` (pinned to existing methods), argv list, own session, 600 s limit, baseline env and tripwire; timeout or host call is a problem | closed |
| T-28-10 | Information disclosure | `tests/fixtures/archived/**`, `repo-config.json` | medium | mitigate | machine-path and key-like grep over the fixtures is empty | closed |
| T-28-11 | Tampering | fixture files | low | mitigate | tests only read fixtures, write to temp copies; `git status --porcelain tests/fixtures/archived` empty | closed |
| T-28-12 | Elevation of privilege | archived `.py.txt` checkers | low | accept | see Accepted Risks Log | closed |
| T-28-28 | Information disclosure | host CLI by absolute path or `executable=` | medium | mitigate | `check_no_host_cli_calls` basename and literal `executable=` match, non-vacuity cases; variable-built remainder named in its docstring | closed |
| T-28-13 | Tampering | `staged_paths`, `decide`, uv subprocess | medium | mitigate | argv lists, no shell; names matched as text; uv gets discovered module names only | closed |
| T-28-14 | Elevation of privilege | `--staged` fail-open | high | mitigate | any exception runs the full unit and arch groups; stale machinery exits 2; covered file with empty answer forces a full run; e2e cases e/f and mapper-error cases | closed |
| T-28-15 | Repudiation | commit-stage bypass | low | accept | see Accepted Risks Log | closed |
| T-28-16 | Tampering | hook config, `SHARED_MACHINERY`, `COMMIT_E2E_BUDGET_SECS` | medium | mitigate | `staged_hook_errors`, `deferred_hook_errors`, `shared_machinery_errors`, `recorded_secs_errors` in `tests/test_gate_scope.py` with non-vacuity cases | closed |
| T-28-26 | Tampering | `--pushed` refs | medium | mitigate | refs as argv; a `-`-prefixed ref raises before git runs and falls back to every over-budget module | closed |
| T-28-27 | Elevation of privilege | commit budget, multi-ref pushes | high | mitigate | `_proof_refusal` (HEAD is the pushed commit, no outside commits); fallback to every over-budget module on no range, bad ref, failed proof or mapper error; unrecorded module deferred; known tag gaps in a `shortcut:` comment; e2e cases j, k, m, n | closed |
| T-28-17 | Information disclosure | matrix environments | high | mitigate | scratch HOME per environment with `AI_KIT_REFUSE_REAL_HOME=1`; caches only forwarded; outer shims fail the matrix on a host call | closed |
| T-28-18 | Tampering | `make_long_checkout` | medium | mitigate | source only read; unlink before write, no write through a link; `.planning/` removed only after a successful clone; pinned in `tests/test_env_matrix.py` | closed |
| T-28-19 | Denial of service | scratch space | low | mitigate | scratch root removed in a `finally` | closed |
| T-28-24 | Repudiation | matrix and timing reports | high | mitigate | `baseline_env` drops `AI_KIT_TEST_REPORT_DIR`; reports created exclusively, duplicates flagged; one report per expected module | closed |
| T-28-25 | Tampering | owner `.venv` via `UV_PROJECT_ENVIRONMENT` | medium | mitigate | `UV_NO_SYNC=1` in the long-path environment | closed |
| T-28-20 | Information disclosure | `tools/time_prepush.py` runs | medium | mitigate | fresh temp HOME per hook with `AI_KIT_REFUSE_REAL_HOME=1`, caches only forwarded; runner baseline and tripwire inside | closed |
| T-28-21 | Repudiation | recorded times | medium | mitigate | record line with date, cpus, load, share, workers; verdict from `load_reports` / `baseline_problems`, all-skipped and total checks; unrounded total vs 60.0; failed auxiliary hook exits 1; TestVerdict | closed |
| T-28-SC | Tampering | npm/pip/cargo installs | low | accept | see Accepted Risks Log | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

Notes (non-blocking):
- T-28-20: `hook_env` keeps the caller's config-dir and credential variables for the outer hook processes (pre-commit, make); only the runner's module children are scrubbed. This matches the declared mitigation; the outer processes run no test or host CLI themselves.
- The one-off proof scripts `tmp/p28/stress_selftest.sh` (T-28-22) and `tmp/p28/proof_count.py` (T-28-27) no longer exist; their results are in the 28-02 and 28-07 summaries, and the code-level mitigations are present and tested.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-28-01 | T-28-12 | The archived `.py.txt` checkers are this repo's own committed scripts, run on fixture data only: in an isolated child interpreter (`sys.executable -I`) in `tests/test_pi_live_tools.py`, and imported in-process through `SourceFileLoader` in `tests/test_tool_advisor_core.py`. Same trust as any test module. | plan 28-05 | 2026-11-04 |
| AR-28-02 | T-28-15 | A commit-stage bypass is visible as the hook's exit code; AGENTS.md forbids `--no-verify`, and the push stage still runs the full suites. | plan 28-06 | 2026-11-04 |
| AR-28-03 | T-28-SC | No package-manager install in this phase; new tools and `tests/host_fakes.py` import stdlib or repo modules only, and no dependency was added to `pyproject.toml`, `uv.lock` or `package.json`. | plans 28-01 to 28-09 | 2026-11-04 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-04 | 29 | 29 | 0 | gsd-security-auditor (ASVS L1, block_on high) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-04
