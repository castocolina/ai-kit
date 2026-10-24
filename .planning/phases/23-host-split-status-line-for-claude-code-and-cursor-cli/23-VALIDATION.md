---
phase: "23"
slug: "host-split-status-line-for-claude-code-and-cursor-cli"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-23"
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` via `tools/run_unittest_parallel.py` (groups unit, unit-uv, integration, e2e, arch); phase-dir owner tools with `--self-test` |
| **Config file** | `Makefile`, `.pre-commit-config.yaml` (generated group listing, pinned by `tests/test_gate_scope.py`), `pyproject.toml` |
| **Quick run command** | `python3 -m unittest <touched test module>` |
| **Full suite command** | `make test && make validate` |
| **Estimated runtime** | ~600 seconds full; quick < 30 seconds |

---

## Sampling Rate

- **After every task commit:** the touched module's quick command (the plan's `<verify>`), plus the D-05 oracle classes for every Part A task
- **After every plan wave:** `python3 tools/run_unittest_parallel.py --group unit --group arch`; `uv run python tools/run_unittest_parallel.py --group integration` when `tools/wizard_app.py` or `tools/setup.py` changed; `--group e2e` when an entry or setup changed
- **Before `/gsd-verify-work`:** `make test` and `make validate` green (23-18 Task 1)
- **Max feedback latency:** 30 seconds (quick)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | STL-01 (R2) | T-23-01 | fixtures hold placeholders only | golden | `python3 -m unittest tests.test_status_line.TestFullGoldenAnsi` | ❌ W0 | ✅ green |
| 23-01-02 | 01 | 1 | STL-01, STL-02 (R10) | T-23-02 | entry runs with an explicit scratch env | subprocess golden | `python3 -m unittest tests.test_status_line` | ❌ W0 | ✅ green |
| 23-02-01 | 02 | 1 | STL-01 (R1) | T-23-03 | table pinned to base AST hashes | arch | `python3 -m unittest tests.test_arch.TestSplitAudit` | ❌ W0 | ✅ green |
| 23-02-02 | 02 | 1 | STL-01 (R1) | T-23-03 | disagreements explained | arch + non-vacuity | `python3 -m unittest tests.test_arch` | ✅ extend | ✅ green |
| 23-03-01 | 03 | 1 | STL-03, STL-04 | T-23-08 / T-23-09 | loopback only, children reaped | unit | `python3 -m unittest tests.test_cursor_fakes` | ❌ W0 | ✅ green |
| 23-03-02 | 03 | 1 | STL-02 | T-23-05 | POC payload redacted, one file read | unit + secret-scan | `python3 -m unittest tests.test_cursor_fakes` | ❌ W0 | ✅ green |
| 23-03-03 | 03 | 1 | STL-04 | T-23-06 / T-23-07 | owner tools never print/promote tokens | self-test | `python3 <phase>/live/spike_check.py --self-test` (and probe, capture) | ❌ W0 | ⬜ pending |
| 23-04-01 | 04 | 2 | STL-01 (R2) | T-23-10 / T-23-11 | pure move, assertions unchanged | unit + checker | `python3 <phase>/live/split_check_tests.py` | ❌ (plan creates) | ⬜ pending |
| 23-04-02 | 04 | 2 | STL-01 | T-23-10 | caller-module patch targets | unit | `python3 -m unittest tests.test_status_line tests.test_external_segments tests.test_statusline_doctor tests.test_arch` | ✅ | ✅ green |
| 23-04-03 | 04 | 2 | STL-01 | T-23-10 | AST-hash conformance | arch | `python3 tools/run_unittest_parallel.py --group unit --group arch` | ✅ extend | ⬜ pending |
| 23-05-01 | 05 | 3 | STL-01 | T-23-12 / T-23-13 | thin entry renders the oracle | unit + subprocess | `python3 -m unittest tests.test_status_line tests.test_arch` | ✅ | ✅ green |
| 23-05-02 | 05 | 3 | STL-01 | T-23-13 | only core_discover_builders generalized | full suite | `make test && make validate` | ✅ | ⬜ pending |
| 23-06-01 | 06 | 4 | STL-01, STL-03 (D-17 TOML) | T-23-15 | bad TOML renders the doctor line | unit | `python3 -m unittest tests.test_status_line tests.test_arch` | ✅ | ✅ green |
| 23-06-02 | 06 | 4 | STL-01, STL-02 | T-23-14 / T-23-16 | host prefixes only in `*_host.py` | arch + full | `make test && make validate` | ✅ | ⬜ pending |
| 23-07-01 | 07 | 5 | STL-01 | T-23-18 | generic code never reads ctx.host | unit | `python3 -m unittest tests.test_status_line` | ✅ | ✅ green |
| 23-07-02 | 07 | 5 | STL-02 (R4) | — | gauge bit-identical, boundaries | unit | `python3 -m unittest tests.test_status_line` | ✅ | ✅ green |
| 23-07-03 | 07 | 5 | STL-03 (git timeouts) | T-23-17 | fake slow git cannot stall | unit + full | `make test && make validate` | ✅ | ⬜ pending |
| 23-08-01 | 08 | 6 | STL-01 (R2, R3) | T-23-22 | hard rename, references clean | unit + e2e | `make test` | ✅ | ⬜ pending |
| 23-08-02 | 08 | 6 | STL-01 (R3), STL-05 (R11 race) | T-23-19..21 | foreign untouched, no overwrite, race-safe | unit | `python3 -m unittest tests.test_setup.TestStatuslineMigration tests.test_setup.TestCreateIfAbsent` | ✅ extend | ✅ green |
| 23-09-01 | 09 | 7 | STL-01, STL-05 | T-23-41 | dependency direction enforced | arch | `python3 -m unittest tests.test_arch` | ✅ extend | ✅ green |
| 23-09-02 | 09 | 7 | STL-03 (R8 arch) | T-23-40 | networking only in cursor_quota, lazily | arch | `python3 -m unittest tests.test_arch` | ✅ extend | ✅ green |
| 23-09-03 | 09 | 7 | STL-01 (R3) | T-23-42 | legacy references only in allowlist | arch + full | `make test && make validate` | ✅ extend | ⬜ pending |
| 23-10-01 | 10 | 2 | STL-03 (R7) | T-23-23 / T-23-24 | token-free normalized data | unit | `python3 -m unittest tests.test_cursor_quota` | ❌ W0 (plan creates) | ✅ green |
| 23-10-02 | 10 | 2 | STL-03 (R7, R9) | T-23-25 | inferred confidence, strict parsing | unit | `python3 -m unittest tests.test_cursor_quota` | ✅ | ✅ green |
| 23-11-01 | 11 | 3 | STL-03 (R8) | T-23-28 / T-23-29 | read-only accessToken, default TLS | unit + loopback | `python3 -m unittest tests.test_cursor_quota` | ✅ | ✅ green |
| 23-11-02 | 11 | 3 | STL-03 (R8) | T-23-26 / T-23-27 / T-23-30 | http, foreign host, redirect refused | unit + loopback | `python3 -m unittest tests.test_cursor_quota` + secret-scan | ✅ | ⬜ pending |
| 23-12-01 | 12 | 5 | STL-03 (R9), STL-04 (mechanics) | T-23-31 / T-23-34 / T-23-35 | 0600 token-free cache, token-free argv | unit + CLI | `python3 -m unittest tests.test_cursor_quota tests.test_arch` | ✅ | ✅ green |
| 23-12-02 | 12 | 5 | STL-03 (R9), STL-04 | T-23-32 / T-23-33 | single-flight, negative cache, kill survival | unit + runner simulator | `make test && make validate` | ✅ | ⬜ pending |
| 23-13-01 | 13 | 6 | STL-02 (R6) | T-23-36 | defensive payload parsing | unit + subprocess | `python3 -m unittest tests.test_cursor_status_line` | ❌ W0 (plan creates) | ✅ green |
| 23-13-02 | 13 | 6 | STL-02 (R4, R6) | T-23-38 | every quota segment marked ≈ | unit | `python3 -m unittest tests.test_cursor_status_line` | ✅ | ✅ green |
| 23-13-03 | 13 | 6 | STL-02 (R10), STL-03 (R9 env) | T-23-37 / T-23-39 | host isolation, no network in render | unit + full | `make test && make validate` | ✅ | ⬜ pending |
| 23-14-01 | 14 | 8 | STL-05 (R11) | T-23-47 / T-23-49 | schema-valid atomic Cursor wiring | unit + headless run | `python3 -m unittest tests.test_setup` | ✅ | ✅ green |
| 23-14-02 | 14 | 8 | STL-05 (R11) | T-23-46 / T-23-48 / T-23-50 | foreign never overwritten headless | unit matrix + full | `make test && make validate` | ✅ | ⬜ pending |
| 23-15-01 | 15 | 7 | STL-05 (R11 doctor) | T-23-43 / T-23-44 | doctor never prints the token | unit | `python3 -m unittest tests.test_statusline_doctor` | ✅ | ✅ green |
| 23-15-02 | 15 | 7 | STL-05 | T-23-45 | inferred label on quota | unit + full | `make test && make validate` | ✅ | ⬜ pending |
| 23-16-01 | 16 | 9 | STL-05 (R12) | — | seam keeps wizard free of host imports | unit + integration (uv) | `uv run python tools/run_unittest_parallel.py --group integration` | ✅ | ⬜ pending |
| 23-16-02 | 16 | 9 | STL-05, STL-02 (D-24) | T-23-51 | preview never reaches network | unit + integration | `python3 -m unittest tests.test_setup tests.test_arch` | ✅ | ✅ green |
| 23-16-03 | 16 | 9 | STL-05 | T-23-52 / T-23-53 | per-host validated atomic commit | unit + full | `make test && make validate` | ✅ | ⬜ pending |
| 23-17-01 | 17 | 10 | STL-05 (R12) | T-23-54 | declined host untouched | pilot (uv) | `uv run python tools/run_unittest_parallel.py --group integration` | ✅ | ⬜ pending |
| 23-17-02 | 17 | 10 | STL-05 (R12) | T-23-54 / T-23-55 | two-host PTY, no orphans | PTY (uv) + full | `make test && make validate` | ✅ extend | ⬜ pending |
| 23-18-01 | 18 | 11 | all | — | project-wide gates | full suite | `make test && make validate` (+ ruff, pyright, vulture) | ✅ | ⬜ pending |
| 23-18-02 | 18 | 11 | STL-03, STL-04 | T-23-56 / T-23-57 | POC credential copy removed; no claimed live pass | checker | `python3 <phase>/live/spike_check.py --record <phase>/23-SPIKE.md` exits 1 | ✅ | ⬜ pending |
| 23-18-03 | 18 | 11 | all | — | status recorded | doc check | `grep -qx '## Phase status' <phase>/23-SPIKE.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_status_line.py` D-05 oracle classes + `tests/fixtures/golden/` raw-ANSI, entry and provider fixtures (23-01)
- [x] `tests/fixtures/statusline_split/audit.md` + `TestSplitAudit` (23-02)
- [x] `tests/cursor_fakes.py`, `tests/test_cursor_fakes.py`, `tests/fixtures/cursor/` (23-03)
- [x] `tests/test_cursor_quota.py` (23-10) and `tests/test_cursor_status_line.py` (23-13), each followed by `python3 tools/gen_test_groups.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real Cursor payload capture under a scratch `CURSOR_CONFIG_DIR` | STL-04 (R5) | needs the owner's Cursor login and approval | `23-SPIKE.md` S1 |
| Real Dashboard responses, units, `included_usage_period` | STL-03 (R7 fixtures), STL-04 | needs the real token and quota | `23-SPIKE.md` S2, S6, then `spike_check.py --promote` |
| p50/p95 latency, update cadence, kill-by-next-update in a live session | STL-04 (R5) | live TUI timing | `23-SPIKE.md` S3, S4 |
| Token lifetime and torn `auth.json` reads | STL-03 | live CLI behavior | `23-SPIKE.md` S5 |
| Real `cursor-agent` run with the wired line, ANSI and multi-line rendering | STL-05 (R12) | live TUI | `23-SPIKE.md` S7 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending owner review

## Validation Audit

**Audit run:** 2026-10-24 (validate-phase, State A). Requirements STL-01..STL-05.

| Module | Result |
|--------|--------|
| tests.test_arch | 60 tests, ok |
| tests.test_status_line | 317 tests, ok |
| tests.test_cursor_fakes | 6 tests, ok |
| tests.test_cursor_quota | 37 tests, ok |
| tests.test_cursor_status_line | 13 tests, ok |
| tests.test_statusline_doctor | 31 tests, ok |
| tests.test_external_segments | 57 tests, ok (includes one new test) |
| tests.test_setup | 421 tests, ok |
| live/spike_check.py --self-test | self-test ok |

**Gap filled:** STL-02 req 10 (Claude provider wire contract) had no byte-level pin; added `test_claude_provider_wire_contract_is_byte_identical` to `tests/test_external_segments.py`.

**Warnings:**
- The `23-04-01` row points at `tmp/p23/04/split_check_tests.py`, which no longer exists (scratch, removed). Its checks are covered by `tests.test_arch.TestSplitAudit` and the arch tests.
- `live/spike_check.py --self-test` is not wired into any unittest group, so `make test` does not run it.
- `make test && make validate` rows were not re-run in this audit and remain pending.

**Manual-only (owner, by design):** S1-S7 in `23-SPIKE.md`, STL-04 capture, and the STL-03 real-response clause.
