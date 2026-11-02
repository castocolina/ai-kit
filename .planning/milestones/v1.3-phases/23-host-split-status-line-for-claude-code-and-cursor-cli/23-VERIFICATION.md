---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
verified: 2026-10-24T12:00:00Z
status: human_needed
score: 5/5 roadmap criteria verified automatically; 2 clauses owner-pending (STL-04, STL-03 real fixtures)
covered_files: [".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-01-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-01-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-02-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-02-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-03-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-03-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-04-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-04-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-05-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-05-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-06-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-06-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-07-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-07-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-08-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-08-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-09-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-09-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-10-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-10-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-11-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-11-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-12-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-12-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-13-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-13-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-14-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-14-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-15-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-15-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-16-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-16-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-17-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-17-SUMMARY.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-18-PLAN.md", ".planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-18-SUMMARY.md", "tools/claude_host.py", "tools/common_render.py", "tools/cursor_quota.py", "tools/cursor_segments.py", "tools/setup.py"]
covered_digest: "v3:sha256:295ffa45e0f65ef6e063d4a46f9f4e991cfe095c27d9f5557752864993ca1555"
behavior_unverified: 0
human_verification:
  - test: "S1 Payload capture and cadence (scratch CURSOR_CONFIG_DIR, spike_capture.py)"
    expected: "Shortest update gap, render width and kill result recorded in 23-SPIKE.md"
    why_human: "Reads the real Cursor session; owner approval required"
  - test: "S2 Raw Dashboard responses from the three methods (spike_probe.py --samples 20)"
    expected: "Shapes and units recorded, no token values"
    why_human: "Uses the real token and consumes quota"
  - test: "S3 Sequential and concurrent p50/p95"
    expected: "Timings recorded; spike_check.py computes inline-vs-refresher decision"
    why_human: "Live network timing"
  - test: "S4 Debounce and kill-by-next-update"
    expected: "Delayed capture killed by a later update, not by a process-group kill"
    why_human: "Needs a running cursor-agent"
  - test: "S5 Token lifetime and torn reads"
    expected: "Outcomes only, no credentials copied"
    why_human: "Credential file; owner-only"
  - test: "S6 Real included_usage_period enum value and location"
    expected: "Confirms the inferred planInfo.includedUsagePeriod mapping"
    why_human: "Needs a live response"
  - test: "S7 R12 live cursor-agent run with the wired status line"
    expected: "Model, context, three quota segments render with gauge colors and the inferred marker"
    why_human: "Visual, real host"
  - test: "D-12 delete the POC credential-bearing cli-config.json.bak"
    expected: "File absent at its exact path"
    why_human: "Irreversible credential-file delete left to owner confirmation"
---

# Phase 23: Host-split status line Verification Report

**Phase Goal:** Cursor CLI status line next to Claude's; `tools/status-line.py` split into common/claude/cursor modules plus isolated `cursor_quota.py`, shared 5/10/15 gauge.
**Status:** human_needed (designed end state; no failures found)
**Re-verification:** No

## Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Phase A split: Claude byte-identical, lint clean, stale doc fixed/deleted | VERIFIED | `tools/status-line.py` and `docs/architecture/status-line-pipeline.md` are gone; `claude_*`, `common_*` modules and 13-line `claude-status-line.py` exist; `uv run ruff check tools skills tests` passes; byte-oracle tests are inside the 408 passing tests |
| 2 | Phase B: Cursor line, three quota segments, cache/auth/endpoint/git-timeout/TOML-error rules; redacted real fixtures | VERIFIED except real-fixture clause | `probe_validate_endpoint` enforces https `*.cursor.sh`; `GIT_TIMEOUT_S` on every git call in `common_probe.py`; `tests.test_cursor_quota` and `tests.test_status_line` pass; only synthetic/POC-redacted fixtures exist (`tests/fixtures/cursor/dashboard`), no `dashboard_real/` yet |
| 3 | Render vs fetch timing measured before choosing | UNCERTAIN (owner) | Spike kit and checker exist; S1-S7 all `not run (owner)`; D-13 presumption (cache-only render + detached refresher) is in force and implemented |
| 4 | C1/C2: `--with-statusline[=claude,cursor]` headless and wizard per host | VERIFIED (automated) | Flag resolved at command entry in `tools/setup.py`; scratch-HOME live check recorded in 23-SPIKE.md; wizard tests inside the suite |
| 5 | Entries reachable, arch rules pass, gates green | VERIFIED (targeted) | `tests.test_arch` OK; `make test`/`validate`/`e2e-docker` green per orchestrator and 23-SPIKE.md, not re-run here |

Targeted run: `python3 -m unittest tests.test_arch tests.test_cursor_quota tests.test_status_line` ran 408 tests, OK.
`spike_check.py --record 23-SPIKE.md` exited 1 with exactly S1-S7 `not run (owner)`.

## Requirements Coverage

| Req | Status | Note |
|---|---|---|
| STL-01 | SATISFIED | split, rename, lint, doc removal confirmed |
| STL-02 | SATISFIED (automated); live look is S7 | |
| STL-03 | SATISFIED except "redacted real Dashboard responses are fixtures" | stays Pending until S2/promote |
| STL-04 | PENDING (owner) | needs S1-S7 and the computed decision |
| STL-05 | SATISFIED (automated), gates by orchestrator | |

## Warnings (non-blocking)

- ROADMAP.md shows `17/18 plans executed` and `23-18-PLAN.md` unchecked although 23-18-SUMMARY.md exists; tick on phase close.
- `.planning/PROJECT.md` still references `tools/status-line.py` at lines 71, 150, 165 (historical/known-debt text; amend when the milestone closes).
- REQUIREMENTS.md traceability still lists all STL rows as Pending.
- D-12 credential `.bak` deletion not done (owner decision).

## Anti-patterns

No debt markers or stubs examined beyond ruff; review (23-REVIEW.md) shows 2 Critical and 11 Warning findings fixed in 9 commits.

---

_Verified: 2026-10-24_
_Verifier: Claude (gsd-verifier)_
