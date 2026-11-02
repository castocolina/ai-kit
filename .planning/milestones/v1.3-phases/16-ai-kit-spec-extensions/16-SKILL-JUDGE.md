# Phase 16 — skill-judge gate: `skills/ai-kit-spec-config/SKILL.md`

**Date:** 2026-09-24
**Why:** Plans 16-01 and 16-02 changed this SKILL.md, and AGENTS.md requires `/skill-judge` for
any materially updated SKILL.md. The pass bar is no remaining Critical or Important finding, or a
score of at least 96/120, with no regression against the baseline.
**Baseline:** the same file at `333cf04` (pre-phase). The two Phase 16 edits were:
- **16-01:** codex model enumeration via `codex debug models` → `clis.codex.models`.
- **16-02:** `native_runtime` gains `pi`, and innermost-CLI precedence
  pi > opencode > cursor > codex > claude.

## Summary

- **Total score:** 104/120 (87%), grade B. This passes the bar, which requires either
  ≥ 96 or no Critical/Important finding; both hold.
- **Pattern:** Process (Step 0 to Step 4), with Tool-level rigor in each step.
- **Knowledge ratio (E:A:R):** about 75:20:5.
- **Critical / Important findings:** 0 / 0.
- **Regression vs baseline:** none. Both Phase 16 edits make the skill more accurate:
  - the stale claim "codex … no live catalog check possible" is replaced by the real enumeration
    path plus a degrade path;
  - the list of `native_runtime` values now matches `detect_current_runtime`.

## Dimension scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1 Knowledge Delta | 17 | 20 | Live-verified landmines (bare codex model id, cursor id encoding, single-provider drop, `purpose`/`native_runtime` never omitted); some paragraphs are long |
| D2 Mindset + Procedures | 12 | 15 | Step 2 opens with the quota-reliability and strength-fit judgment; factory-first domain procedures |
| D3 Anti-Patterns | 13 | 15 | Specific NEVER list, each with a reason |
| D4 Specification | 13 | 15 | Description covers WHAT, WHEN and flags; keywords could add "reviewer ladder / fallback order" |
| D5 Progressive Disclosure | 13 | 15 | MANDATORY read-entire-file trigger plus explicit "Do NOT load", and per-CLI profile loading only; body is 338 lines |
| D6 Freedom Calibration | 14 | 15 | Fragile writes go through factory subcommands; judgment calls are left to the user |
| D7 Pattern | 9 | 10 | Declared Process + Tool rigor, applied consistently |
| D8 Usability | 13 | 15 | Edge cases (`--check-only` shadowing, unknown runtime, rejected-entry warnings) covered; very long paragraphs in 2.4 and 2.7 slow scanning |

## Findings

- **Minor (fixed in this gate):** Step 1 said only `opencode` carries a `models` list. After Phase
  16, codex and claude do too. Reworded to "its `models` list when present (opencode, codex and
  claude carry one; a CLI whose enumeration failed degrades to no list)".
- **Minor (not fixed, pre-existing and out of Phase 16 scope):** Steps 2.4 and 2.7 are dense
  single paragraphs. Splitting them into bullets would help D8, but that would be a
  restructure unrelated to this phase's edits.
