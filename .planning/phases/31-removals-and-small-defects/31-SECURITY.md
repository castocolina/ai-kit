---
phase: "31"
slug: "removals-and-small-defects"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-06"
---

# Phase 31 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| installer -> user home | `tools/setup.py` and `tools/install.sh` create and remove symlinks under the claude and pi skills roots and rewrite host statusLine config | link paths, host config files (user-owned) |
| repo / user config -> check-providers | `check-providers` reads review-spec TOML, the model catalog and opencode JSON(C) files, some of them repo-controlled | provider ids and model refs only; secrets never read |
| live CLI -> check-providers | `opencode models` listing output | provider/model ids |
| repo -> tests | rtk-ban and AGENTS.md link tests read tracked files and call `git` | file text, paths |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-31-01 | Tampering | deleting the GSD execute adapter | medium | mitigate | only the three retired skill trees and their tests deleted; all recoverable from 8a74d94 | closed |
| T-31-02 | Tampering | `ensure_runner` write | low | mitigate | `cross_ai_script._publish` -> `cache` mkstemp + `os.replace`; no guidance writer left; `test_ensure_runner_reports_ready_without_guidance` | closed |
| T-31-03 | Information Disclosure | `check_providers_report`, `jsonc_read` | high | mitigate | prints provider ids and model refs only; never opens `auth.json`; `test_secret_values_and_auth_file_are_never_read_or_printed` | closed |
| T-31-04 | Tampering | `jsonc_read.read_provider_names` | medium | mitigate | read-only, 1 MiB cap, strict UTF-8; parse errors including `RecursionError` return None (fixed in 0be1acb, `test_deeply_nested_file_returns_none`) | closed |
| T-31-05 | Denial of Service | `detect_opencode_models` | low | mitigate | `_run_opencode`: private cwd, probe env, 15 s timeout; tests use a fake `run_fn` | closed |
| T-31-06 | Tampering | `apply_stale_prune` / `unlink_one` | high | mitigate | only symlinks whose target is inside the kit and gone; `os.remove`, no rmtree; `test_neighbours_of_a_dead_link_survive` | closed |
| T-31-07 | Spoofing | `_is_inside` | high | mitigate | parent resolved, leaf kept, `commonpath` component compare; `TestIsInsidePathComponents` | closed |
| T-31-08 | Tampering | empty `HOME` | medium | mitigate | `setup.py` returns 2 before any path resolution and before the real-home refusal; `install.sh` exits 1 before `$HOME` expands; tests in `test_setup.py` and `tests/test_install.sh` 1d | closed |
| T-31-09 | Denial of Service | link vanishes before removal | low | mitigate | `unlink_one` suppresses `FileNotFoundError`; other `OSError` warns and the run goes on (1b48f0a); `test_link_vanishing_before_removal_counts_as_gone`, `test_unremovable_link_warns_and_the_run_goes_on` | closed |
| T-31-10 | Tampering | `_load_gsd_reply` | low | mitigate | `@file:` redirect only on the prefix, one read-only open, failures -> ValueError -> None; `TestGsdAtFileReply` | closed |
| T-31-11 | Elevation of Privilege | `check_edge_floors` | low | accept | argv list, `timeout=120`, no shell (`check_dogfood.py`) | closed |
| T-31-12 | Tampering | deleting the opencode-providers skill | medium | mitigate | only tracked paths deleted; the removed writers were the only writers; new code only reads | closed |
| T-31-13 | Information Disclosure | herdr pi live check | medium | mitigate | scratch HOME, no copied credentials, variable names only; closed 2026-11-06: pi printed `PI_CODING_AGENT`, `PI_MODEL`, `PI_PROVIDER`, `PI_REASONING_LEVEL`, `PI_SESSION_FILE`, `PI_SESSION_ID`, names recorded, no values (31-VERIFICATION.md) | closed |
| T-31-14 | Tampering | usage-metrics stored rtk data | high | mitigate | docstring-only diff in `skills/ai-kit-usage-metrics/`; `TestCaptureRtk` uses a scratch `XDG_DATA_HOME` | closed |
| T-31-15 | Denial of Service | `banned_mentions` | low | mitigate | tracked files only, NUL-byte binary skip, `errors="replace"`, one `git ls-files -z` call | closed |
| T-31-16 | Tampering | `git check-ignore` call | low | mitigate | argv list, `-C <root>`, `-q`; existence check first (review WR-07 notes the missing `--`, low, follow-up) | closed |
| T-31-17 | Spoofing | untrusted local review-spec | medium | mitigate | `trust.is_trusted` gates the local file; `local-only` applies only when trusted; `test_untrusted_local_does_not_deactivate_global` | closed |
| T-31-SC (plans 01-06) | Tampering | package installs | low | accept | no lock file or dependency change in the phase diff; `pyproject.toml` only loses `extraPaths` entries | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-31-01 | T-31-11 | the edge-floor guard runs the repo's own test runner with an argv list, a timeout and no shell, on the owner's machine only | plan 31-04 threat model | 2026-11-06 |
| AR-31-02 | T-31-SC | no package was installed or upgraded in this phase (no lock file change) | plans 31-01..06 threat models | 2026-11-06 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-06 | 23 | 22 | 1 (non-blocking, T-31-13) | gsd-security-auditor (opus), T-31-04 fixed by orchestrator in 0be1acb |
| 2026-11-06 (close-out) | 23 | 23 | 0 | orchestrator: T-31-13 closed by the herdr pi check |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-06 (T-31-13 closed 2026-11-06, names only recorded in 31-VERIFICATION.md)
