# Phase 40: Resilient review sized by jev - Context

**Gathered:** 2026-11-23 (interactive, after 40-SPEC.md)
**Status:** Ready for planning

<domain>
## Phase Boundary

`ai-kit-spec-review` survives a failing lane without running on a lane nobody chose: a flagged `usage_limited` lane that hits
quota switches at once to its fallback; every chosen lane is pinged before round 1 (and later only lanes that failed or went
stale) and a blocked one is replaced from the owner's order; a review with a replaced, failed or unresolved lane is reported
partial; jev classifies reviewer-fixer disagreements and sizes the review on top of deterministic signals; a superpowers plan
with no fold step gets a HIGH finding.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**8 requirements are locked.** See `40-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `40-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** the flagged-lane switch, the per-round ping, the closed reason list and the partial report; jev
classification and sizing with their no-jev behavior; the fold-step finding; docs, evals, tests and the judge loop.
**Out of scope (from SPEC.md):** switching an unflagged lane on any class; the runner's own retry and classification and the
blocked-until writer; execute-side switching (Phases 41, 42); code review after execution and jev-picked executors (Phase 42); a
new jev backend or a change to the shared jev client.

</spec_lock>

<decisions>
## Implementation Decisions

### Reasons, ping and partial report
- **D-01: The closed reason list is the existing `REASONS` tuple in `ai_kit_spec/error_classifier.py`, extended** with the
  review-level reasons (candidates: `replaced`, `never_resolved`, `no_lane_left`; names fixed at plan time); a ping or lane
  failure reuses the nine existing reasons. The lock is the existing tests that read the set
  (`tests/test_ai_kit_spec.py:3490`, `tests/test_ai_kit_spec_runtimes_table.py:776`) extended, plus the quota-policy text test
  that reads the classifier file. **Own reasoning** (jev not asked): a second list would drift from the first. Ledger.
  - Evidence: `error_classifier.py:16` is a closed tuple the probe stores as the entry's reason (`quota.py`).
  - **Reversibility:** costly — `REASONS` is read by the probe, the superpowers dispatch injection and several tests.
- **D-02: A ping is `probe_reviewer_quota` run for each chosen lane concurrently** with stdlib `concurrent.futures`, each with its
  own timeout through the probe seam; the quota cache TTL (`refresh_quota_cache`) is the "went stale" rule, and a lane that
  returned a report in the previous round is marked fresh in the round log and not pinged. Clock and probe are seams, so tests
  use fake lanes and a fake clock. **Own reasoning:** the probe already exists and the owner chose "failed or stale" cadence.
  Ledger.
- **D-03: The partial status lives in the Step 5 report.** The report names the judged lanes and every other lane with its
  reason; an approval in such a run reads "Approved (partial)"; a run with no lane judged reads "not reviewed". **Own reasoning:**
  SKILL.md:524 already keeps a pending lane from reading as Approved. Ledger.

### Flagged-lane switch and the blocked-until record
- **D-04: The switch is a small module beside `routing.py`** (name at plan time). Input: the failed lane's result with its reason,
  the role's lanes and order. Output: a replacement key or none. Only reason `quota` on a lane flagged `usage_limited` switches,
  through `lane_usage_limit` and `lane_fallback`; every other case returns none. Dispatch of a flagged lane passes
  `--pool <provider>:free` (the runner doc: "a caller of a usage-limited lane always passes `--pool`", otherwise an ok run does
  not clear the record). **Own reasoning.** Ledger.
- **D-05: The blocked-until record is read through the runner's `--blocked-status <pool>`** (one validated reader, spawns nothing,
  `blocked_until=<time|-> failures=<n>`), only for a flagged lane that carries a pool; no runner or node, or a missing or
  malformed record, reads as none and never blocks a lane. **Own reasoning:** the record is written by the runner under
  `${XDG_STATE_HOME:-~/.local/state}/ai-kit/spec/blocked/` and its parser is in `cross-ai.mjs`; a Python re-parse would be a
  second reader. **Confirmed by the owner 2026-11-25 (was PROVISIONAL, needs owner confirmation, as in the SPEC).** Ledger.

### jev
- **D-06: Both jev uses go through one new module** (name at plan time) built on the existing `jev_names.ask_items` pattern:
  `classify_disagreements` (one item per finding, classes `owner_decision`, `mechanical`, `reviewer_wrong`) and `size_review` (one
  item set per sizing). Summaries only; a missing jev, an error, `needs_fallback` or a low answer returns a sentinel and the
  caller takes today's path. A CRITICAL or HIGH finding never takes a `mechanical` or `reviewer_wrong` route. **Own reasoning.**
  Ledger.
- **D-07: Deterministic signals are one function** (`security`, `data`, `irreversible`) over the plan's own files and text, tested
  at each trigger and with none; any signal forces two lanes before jev is asked. The exact trigger rules are fixed at plan time
  with held-out fixtures.

### Fold-step finding
- **D-08: The fold-step check is a deterministic script in `ai-kit-spec-review`** (superpowers plan archetype only) whose result
  merges into the reviewer report as a HIGH finding with a `Required:` line, using the wording that `ai-kit-spec-execute-superpowers`
  documents. **Own reasoning:** a checklist item judged by a reviewer model can miss it and cannot give a deterministic fixture
  pair. Ledger.

### Docs and order
- **D-09: A new `references/lane-failure.md`** holds the ping, the flagged switch, the partial status, the reason list and the jev
  classes; SKILL.md (560 lines) gets the narrowed hard rule (lines 540, 398, 419) and short pointers; `loop-diagram.md` and
  `apply-findings.md` show the ping, the switch and the partial status.
- **D-10: Build order is a vertical slice.** (1) reasons, ping and partial report with fake lanes; (2) the flagged switch and the
  blocked-until read; (3) the jev adapters with their no-jev paths; (4) the fold-step check; (5) evals, docs and the skill-judge
  loops of `ai-kit-spec-review`, `ai-kit-spec-review-fixer` and `ai-kit-spec-review-checklist`.

### Claude's Discretion
Module and function names, the review-level reason names, the exact deterministic trigger rules, and the per-ping timeout default
(configurable, with a test seam).

### Folded Todos
None folded. REV-01 to REV-08 come from REQUIREMENTS.md and the ROADMAP criteria.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements
- `.planning/phases/40-resilient-review-sized-by-jev/40-SPEC.md` — Locked requirements — MUST read before planning
- `.planning/ROADMAP.md` §Phase 40 and `.planning/REQUIREMENTS.md` REV-01, REV-02, REV-06, REV-07, REV-08

### Earlier decisions this phase builds on
- `.planning/phases/36-spec-config-as-the-hub/36-CONTEXT.md` D-16 (flag, reader, fallback), D-20 to D-22 (pools)
- `.planning/phases/38.1-runner-error-classification-and-retry-policy-inserted/38.1-CONTEXT.md` D-12 (direct lane stops), D-23 to D-27
  (blocked-until record)
- `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-CONTEXT.md` D-03 (fold step; REV-08 coupling)

### Code and docs the phase touches
- `skills/ai-kit-spec-review/SKILL.md` (Step 0.7 probe walk, lines 177-190; hard rules 398, 419, 540; Step 5 report 502-524)
- `skills/ai-kit-spec-review/ai_kit_spec/quota.py` (`probe_reviewer_quota`, `refresh_quota_cache`), `reviewer_dispatch.py`,
  `routing.py` (`route_all`), `lane_settings.py` (`lane_usage_limit`, `lane_fallback`), `error_classifier.py` (`REASONS`),
  `jev_names.py` (`ask_items`)
- `skills/ai-kit-spec-review/references/apply-findings.md`, `loop-diagram.md`, `cross-ai.mjs` (blocked-until reader, line 4042 on)
- `skills/ai-kit-cross-ai/references/subprocess-quota-policy.md` §Blocked-until record
- `skills/ai-kit-spec-review-fixer/SKILL.md` (CRITICAL/HIGH rule, line 48), `skills/ai-kit-spec-review-checklist/`
- `skills/ai-kit-spec-execute-superpowers/` (the fold step's documented wording)

### Tests that pin or must keep passing
- `tests/test_ai_kit_spec.py` (REASONS), `tests/test_ai_kit_spec_runtimes_table.py`, `tests/test_quota_policy_text.py`,
  `tests/test_cross_ai_docs_text.py`, `tests/test_role_orders.py` (probe and usage-limited lane)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `probe_reviewer_quota`, `ProbeSeams`, `refresh_quota_cache` (`quota.py`): the ping and its cache.
- `lane_usage_limit`, `lane_fallback`, `selectable_lanes` (`lane_settings.py`): the flag reader and the fallback rule, unused by
  spec-review today.
- `jev_names.ask_items` with its `strict` option, `skill_classify.py` and `lane_order.py`: the jev call pattern and its no-answer
  handling.
- The runner's `--blocked-status` and `--pool` flags (`cross-ai.mjs`).

### Established Patterns
- A table or list is seed data and never a decider; a missing record reads as none and never blocks (38.1).
- Every jev path has a tested no-jev behavior and sends summaries only.
- Fake lanes and seams (clock, probe) instead of real model calls in tests.

### Integration Points
- Step 0.7 (reviewer resolution) for sizing and the first ping; Step 1 dispatch for the flagged switch; Step 5 report for the
  partial status and the jev disagreement step; the superpowers plan path for the fold-step check.

</code_context>

<specifics>
## Specific Ideas

The owner's flag-and-ping-only answer keeps the never-switch-on-our-own rule for every unflagged lane: SKILL.md's blanket "never
re-dispatch a failed lane" becomes "an unflagged lane never switches", with the flagged-lane exception named.

</specifics>

<deferred>
## Deferred Ideas

- Switching an unflagged lane on transient, bad_model or crash classes (the owner chose against it for now; revisit with run
  evidence).
- An execute-side counterpart of the flagged switch (Phases 41 and 42).

### Reviewed Todos (not folded)
- 26 other todos matched by keyword only; none concerns lane failure, ping or jev sizing.

</deferred>

---

*Phase: 40-Resilient review sized by jev*
*Context gathered: 2026-11-23*
