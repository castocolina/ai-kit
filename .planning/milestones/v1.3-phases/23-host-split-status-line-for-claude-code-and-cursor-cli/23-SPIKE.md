---
status: pending-owner
decision: pending
---

# Phase 23 Cursor Status-Line Spike

## Purpose

Record owner-only facts needed to validate inferred Dashboard normalization and choose the
fetch strategy mechanically. No live run has been performed in this execution.

## Approvals and safety

This run reads the real Cursor token and consumes quota, so obtain explicit owner approval first.
Never write the real `cli-config.json`: make a scratch `CURSOR_CONFIG_DIR`, copy the existing
config there, and add `statusLine` only to the scratch copy. Delete the scratch directory after
the capture. If this approach fails, a key-level revert requires explicit owner approval and a
0600 backup outside the repository. The real config is never the fallback target.

## Owner runbook

Use `<checkout>` for the repository root and `<scratch>` for a private temporary directory.
Re-check the installed Cursor CLI's statusLine schema, update behavior, config resolver, and
payload contract against its current documentation before running.

1. **S1 — Payload capture and cadence.** Create `<scratch>/cursor-config`, copy the existing
   `cli-config.json` into it, and add `statusLine: {"type":"command","command":"python3
   <checkout>/.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/live/spike_capture.py
   --out <scratch>/bundle --sleep-ms 1200"}` to that scratch copy. Start Cursor with
   `CURSOR_CONFIG_DIR=<scratch>/cursor-config cursor-agent` and a parameterized model if
   available. Observe emitted payloads, update cadence, render width, and whether the next update
   kills the sleeping capture. Record the shortest update gap and kill result.
2. **S2 — Raw Dashboard responses.** Run
   `python3 <checkout>/.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/live/spike_probe.py
   --out <scratch>/responses --samples 20` using the production transport. Record all three
   methods' response shapes and units, including absent optional fields and
   `included_usage_period`. Do not copy token or Authorization values.
3. **S3 — Sequential and concurrent p50/p95.** Have the probe record sequential and concurrent
   timing samples separately. Preserve raw numeric timings in `<scratch>/timings.json`; observe
   p50/p95 and the render p95 from S1.
4. **S4 — Update cadence and kill-by-next-update.** Confirm that the delayed capture was
   terminated by a later status-line update, not by a process-group kill. Observe whether a
   process retaining stdout blocks completion. Record the shortest measured update gap.
5. **S5 — Token facts and torn reads.** Record whether `auth.json` is rewritten while the
   refresher reads it, whether a torn read is observed, and any observed token lifetime or 401
   response. Never copy or expose credentials; report only outcomes.
6. **S6 — Real included usage period.** Record the exact enum value and response field location.
   This is live evidence for the inferred `planInfo.includedUsagePeriod` mapping.
7. **S7 — R12 live run.** With the wired status line, run `cursor-agent` and record observed
   rendering and behavior. This is owner-only and remains pending until performed.

After collection, run `python3 <checkout>/.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/live/spike_check.py
<scratch>/bundle` and record its computed decision. Keep all results in this document's table.

## Results

| Step | Evidence | Result |
|---|---|---|
| S1 | Scratch payload capture, config safety and cadence | not run (owner) |
| S2 | Raw responses from three Dashboard methods | not run (owner) |
| S3 | Sequential/concurrent latency samples and p50/p95 | not run (owner) |
| S4 | Debounce and kill-by-next-update observation | not run (owner) |
| S5 | Token lifetime and torn-read observations | not run (owner) |
| S6 | Real `included_usage_period` | not run (owner) |
| S7 | R12 live run with wired status line | not run (owner) |

## Decision rule

Select inline fetch only when concurrent p95 plus render p95 is below both the shortest observed
update gap and 300 ms. Otherwise select the detached refresher. The checker computes this result;
the owner does not choose by judgment.

## Promotion

`spike_check.py --promote <scratch>` may promote redacted real responses into
`tests/fixtures/cursor/dashboard_real/` only after all validation and redaction checks pass.
Then `/gsd-plan-phase 23 --gaps` adds real-fixture normalization tables and lifts the STL-03
real-response fixture clause and STL-04.

## Orchestrator close-out

Confirm all seven results are recorded, verify `spike_check.py --record` exits 0 and its decision
matches the computed rule, inspect promoted fixtures for secrets, and run the phase gates. Keep
this record pending until the owner has performed every step.

## Phase status

Automated part complete (2026-10-24):

- Gates on the phase tip, all exit 0: `uv run ruff check tools skills tests`, `uv run pyright`
  (0 errors), `uv run vulture`, `make test`, `make validate`, and the clean-room
  `make e2e-docker`. In the container (no `.git` by design), the git-history audit and
  legacy-reference tests and the node-dependent tracer tests skip with a reason; they run in
  `make test`.
- Final audit conformance: `split_hash_mismatches()` and `split_location_problems()` return `[]`.
  The D-05 oracle fixtures are unchanged since the oracle commit b3fc4fd.
- `live/spike_check.py --record 23-SPIKE.md` exits 1 with exactly S1-S7, each `not run (owner)`.
  Secret-scan over this file and `tests/fixtures/cursor/` is clean.
- Live check from the branch in a scratch HOME (2026-10-24): the Claude and Cursor entries
  render. With a synthetic fresh cache the Cursor quota segments show the gauge and `≈`; with
  no cache the refresher writes only under the XDG cache dir (`auth_missing`), never the CWD.
  `setup.py install --headless --with-statusline=claude,cursor` migrates the legacy Claude
  `statusLine.command` (other keys untouched), wires Cursor's `cli-config.json`, and is stable
  on rerun. Both doctors pass. The dry run's contradictory "foreign" warning for the pre-rename
  entry was fixed in 9b0e632.
- No SKILL.md changed in this phase, so no skill-judge run.
- D-12 (deleting the POC's credential-bearing `.bak` copy) is **not done by the run**: an
  irreversible delete of a credential file is left to the owner's explicit confirmation.

The phase is `human_needed` until the owner runs S1-S7 (`23-SPIKE.md` kit). STL-01, STL-02 and
STL-05 are ready for `/gsd-verify-work 23`. STL-03 is ready except its real-response fixture
clause, and STL-04 stays Pending. The D-13 presumption (cache-only render plus detached
refresher) stays in force until the checker's decision line says otherwise. Next orchestrator
steps: `/gsd-secure-phase 23`; after the merge to local main, `python3 tools/setup.py install`
migrates the machine's Claude line (run rule 6); then `/gsd-verify-work 23`.
