---
phase: 13
reviewers: [opencode]
reviewed_at: 2026-09-14T12:26:00Z
plans_reviewed: [13-01-PLAN.md, 13-02-PLAN.md, 13-03-PLAN.md, 13-04-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 13 (Cycle 2)

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
(none)
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

Cycle 1's 16 findings are in the plan bodies, not just the ledgers, grounded against live source (HEAD `7beed6b`). New seam found: 13-03's long-form volume requirement vs 13-02's scalar-only sequence reader.

## 13-01

**Summary.** Tracer still stands up the skill on SC1/SC5 plus the root-scoped gate. Live interfaces match. Cycle 1's unreadable-wrap overclaim is closed in the plan body as D-D23.

**Strengths**
- Gate edges are this repo's own (`tests/e2e/docker/Dockerfile`, `e2e-docker`). Clause (iv) prefix-after-normalization is the right rule.
- Identifier anchors are now the real ones (missing-target loop + build-wiring finding); the coincidental line-463 citation is correctly named as such.
- Registration surfaces match; the package glob is why 13-02/13-03 need no gate-file edits.

**Concerns.** None new at MEDIUM+. Residual executor risk is forgetting the wrap on every shared-parser call — D-D23 already states this.

**Risk Assessment.** **LOW.**

**Ledger Verification** — Findings 1, 9, 10 all **RESOLVED**, verified against live line numbers.

## 13-02

**Summary.** Hard plan: indentation-aware stdlib compose parser + SC2/SC3. Cycle 1 flow-mapping and declared-values-only gaps are now pinned as limits with containment fixtures.

**Strengths**
- D-D7's block-end rule is the defect D-01 exists to prevent, tested with two differently-nested services.
- Bounds exclusive, numbers match ROADMAP SC2. Unreadable duration -> advisory, not silence.
- `depends_on` three bare forms, per-entry not whole-block.
- The filename-literal-ban check was actually rebuilt (interpolated from live tuples), not just patched.

**Concerns**
- **LOW — the exclusive-bounds check does not pin a fractional-second discriminator.** The stated 5.001s example is not what the verify assertion actually checks; an integer-only parser could still pass. Pin the discriminator to include a fractional part and assert the specific out-of-bounds issue code.

**Suggestions.** Consider adding a `block_sequence`-of-mappings reader to D-D7 now, since 13-03 Task 3 needs long-form volume entries and cannot touch `compose_parse.py` itself (see 13-03 below).

**Risk Assessment.** **MEDIUM.** New residual is the volumes-sequence-of-mappings hole 13-03 walks into.

**Ledger Verification** — Findings 2, 3, 11, 12 all **RESOLVED**, verified against live line numbers.

## 13-03

**Summary.** D-04 expansion with a third advisory outcome, correctly isolated from the taxonomy/classifier. Cycle 1 tiebreak / source-literal / mixed-volume findings are in the body. New seam: long-form volumes vs 13-02's scalar sequence reader.

**Strengths**
- Three outcomes, five named reasons, fixed evaluation order.
- `HOT_RELOAD_TOOLS` correctly kept beside, not inside, the taxonomy/baseline-stacks tables.
- Token-boundary matching with a total-order tiebreak, cross-process hash-seed determinism probe.
- Mixed unreadable-volume state is now an explicit precedence rule, not a leftover bullet.

**Concerns**
- **MEDIUM — long-form `type: bind` volumes are required by this plan but unparseable by 13-02's own scalar-only sequence reader, and this plan's `files_modified` explicitly excludes `compose_parse.py`.** A long-form volume entry is a sequence of mappings, not scalars — 13-02's `block_sequence` reader as specified cannot produce it, and this plan forbids a private re-scan. The executor cannot satisfy this plan's Task 3 pairing without violating one of the two plans' own stated boundaries. Short-form bind mounts (`./src:/app`) already discharge ROADMAP SC4 on their own — this is an internal inconsistency between plans, not a missing capability.
- **LOW — anonymous volumes (a bare path with no colon) are not a bind mount** and must be explicitly excluded from the bind-mount grammar, not treated as conforming because they start with `/` or `.`.

**Suggestions.** Either extend 13-02's D-D7 with a sequence-of-mappings reader and add `compose_parse.py` to this plan's `files_modified`, or descope long-form volume detection from this plan's Task 3 entirely and state short-form-only as a SKILL.md limit. Do not leave both requirements standing as currently written.

**Risk Assessment.** **MEDIUM.** The long-form-volumes seam is the one new executor trap that will fail a required test or force a second, unauthorized parser.

**Ledger Verification** — Findings 4, 5, 6, 13, 14 all **RESOLVED**, verified against live line numbers.

## 13-04

**Summary.** Correct last plan: installability only here. Cycle 1's incomplete CONTEXT sweep and missing seventh limit are now a five-floor sweep and a SUMMARY-reconciled conditional.

**Strengths**
- Six required limits plus a seventh conditional on what 13-02's own SUMMARY actually records — reads the SUMMARY rather than assuming.
- No Python edits in this plan. README: one added line, zero removed.
- No-baseline bar with a recorded history search; name freeze is confirm-only.

**Concerns**
- **LOW — the "per-service" shape-check token requires the literal hyphenated form.** A limit sentence phrased without the hyphen (e.g. "not per service") would fail the mechanical check even though it says the same thing — write the limit with the hyphenated token verbatim.
- **LOW — the seventh-limit reconciliation check is a loose substring match on the word "flow".** Any 13-02 SUMMARY mentioning flow *sequences* (which are in-scope, not a limit) would force an unnecessary seventh limit. Tighten the match to the specific "flow-mapping" phrase.

**Risk Assessment.** **LOW** for code (owns none). **MEDIUM** for shipped claims. Cycle 1's two MEDIUMs are addressed in the body.

**Ledger Verification** — Findings 7, 8, 15, 16 all **RESOLVED**, verified against live line numbers.

---

## Cross-plan

Wave order still matches the dependency graph. Shared-package edits stay additive.

**New cross-plan defect:** 13-03's long-form volume requirement vs 13-02's scalar-only `block_sequence` reader, with `compose_parse.py` locked out of 13-03's own `files_modified`. Must be closed — either extend 13-02's parser and file list, or descope long-form from 13-03 — before execution.

**Overall risk: MEDIUM.** Cycle 1's 16 findings are genuinely in the plan bodies and match the live tree. Remaining risk is the volumes-parser seam plus three trivial verify-check precision gaps — not missing success criteria.

## Current HIGH Concerns

(none)

## Current Actionable Non-HIGH Concerns

1. **MEDIUM (13-02/13-03 cross-plan)** — 13-03's Task 3 requires detecting long-form `type: bind` volume mappings, but 13-02's `block_sequence` compose-sequence reader only handles scalar sequence items, and 13-03's `files_modified` explicitly excludes `compose_parse.py`. Resolve by either (a) extending 13-02's D-D7 with a sequence-of-mappings reader and adding `compose_parse.py` to 13-03's `files_modified`, or (b) descoping long-form volume detection from 13-03 and stating short-form-only as a SKILL.md limit. Pick one; do not leave both requirements standing.
2. **LOW (13-02)** — The healthcheck-bounds exclusivity verify check does not actually pin a fractional-second discriminator (the plan's own stated `5.001s` example is not what the assertion checks); an integer-only duration parser could still pass. Tighten the assertion to require a fractional-second value and the specific out-of-bounds issue code.
3. **LOW (13-03)** — Anonymous volumes (a bare path with no colon, e.g. `- /app/data`) must be explicitly excluded from the bind-mount grammar, not treated as conforming just because they start with `/` or `.`.
4. **LOW (13-04)** — Two verify-check precision gaps: (a) the "per-service" shape-check token requires the literal hyphenated form — write the limit sentence with that exact token; (b) the seventh-limit reconciliation check is a loose substring match on "flow" that would misfire on an in-scope mention of flow *sequences* — tighten it to match "flow-mapping" specifically.

## Consensus Summary

Single-reviewer cycle (opencode only) — no cross-reviewer consensus to synthesize. All findings above are from the single opencode (xai/grok-4.6, reasoning=high) pass, which re-verified all 16 cycle-1 dispositions against live source before surfacing new issues.

### Agreed Strengths
N/A — single reviewer.

### Agreed Concerns
N/A — single reviewer.

### Divergent Views
N/A — single reviewer.

CYCLE_SUMMARY: current_high=0 current_actionable=4
