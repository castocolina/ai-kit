# Phase 21: Cursor Live Validation - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-10-14
**Mode:** assumptions (`--analyze --all --batch`, lean calibration), jev screening, best over easy, CodeGraph

The analyzer (sonnet, 84 tool calls) read the cursor-agent 2026.10.01 bundle read-only, diffed the plan1 branch, and ran `cursor-agent` under a scratch HOME and `CURSOR_CONFIG_DIR`. It wrote nothing under the real `~/.cursor` and never read `auth.json`.

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| D1 setup category | destination_helper 0.58 (fb) | destination_helper 1.00 | D-02 |
| D2 test module | append 0.98 | new_module 0.99 (second opinion) | **Laya overridden:** plan1 appends to the same file (D-04) |
| D3 unknown name | exit_nonzero 0.72 | – | D-05 |
| D4 spike first | spike_first 0.39 (fb) | spike_first 1.00 | D-01 |
| D5 non-fast proof | scratch_config 0.39 (fb) | scratch_config 0.99 | D-08 |
| D6 `agent` scan | first_hit 0.40 (fb) | scan_all_path 0.68 (fb) | **Own reasoning:** scan every PATH entry; first-hit works here only by PATH order luck (D-09, ledger) |

Key finding: the CLI bundle's subagent loader appears to scan only workspace-relative agent folders, not `~/.cursor/agents`. The D-01 spike settles this before R6/R7 planning.

No user corrections.
