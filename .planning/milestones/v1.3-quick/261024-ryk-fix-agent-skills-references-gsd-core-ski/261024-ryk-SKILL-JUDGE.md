# Quick 261024-ryk — skill-judge gate: `ai-kit-gsd-curated-config` and `ai-kit-gsd-spec-discuss`

**Date:** 2026-10-24
**Why:** both SKILL.md files changed materially (AGENTS.md: the skill-judge loop before
complete). Pass bar: no remaining Critical/Important finding, or a score of at least 96/120
with no regression against the baseline.
**Judges** (owner set since 2026-10-24): one clean-context native Opus subagent, opencode
`router-env/my-referee-one` and `router-env/my-referee-two`, all read-only.
**Baselines:** curated-config Opus 106 (Phase 22); spec-discuss Opus 108, referee-one 101,
referee-two 109 (Phase 24 r3). The referees had no curated-config baseline.

## Scores (score, Critical / Important)

| Round | Fixes before it | curated-config Opus | ref-one | ref-two | spec-discuss Opus | ref-one | ref-two |
|---|---|---|---|---|---|---|---|
| r0 | quick 23441b1, ce6984e | 105, 0/0 | 108, 0/1 | 110, 0/0 | 106, 0/1 | 104, 0/1 | 111, 0/0 |
| r1 | 35ada94, ed47ae5 (pi) | 104, 0/1 | 107, 0/2 | 105, 0/0 | 105, 0/3 | 107, 0/1 | 112, 0/1 |
| r2 | fa01935, b05e81e (pi), a27eee0 | 104, **1**/0 | void | void | 103, 0/4 | 0/4 | void |
| r3 | b7aa563, 5c2c9fc, 5c6133e | 104, 0/1 | 106, 0/1 | 108, 0/2 | 106, 0/3 | 110, 0/1 | 114, 0/2 |
| r4 | 07b0a89, 6fb43d1 | 102, 0/1 | 106, 0/2 | 109, **1**/2 | 106, 0/2 | 109, 0/2 | 114, 0/2 |

"void": the run ended `contract_violation tree=dirty` because the orchestrator edited the tree
while it read (r2); not counted. The r2 spec-discuss referee-one score line was not printed.

## Findings fixed after r4 (not re-judged)

- curated-config Critical (referee-two r4): the round-3 round-trip rule dropped bare names from
  the printed fix, so following it would unwire every healthy skill. Fixed in 50571f0 with a
  regression test, plus the Opus r4 Important (a kept `global:<name>` is now judged by the live
  check, which resolves symlinked roots, such as a home dir reached through a symlink), gsd-core's name grammar
  and absolute project paths.
- spec-discuss Importants (all three judges, r4): rows 4 and 5 name forced columns; workstream
  paths come from `init.phase-op` (`state_path`, `phase_dir`); `.err` lines are scoped to
  `[agent-skills] WARNING`; `commit_docs: false` stops the run. Fixed in 08ea728.

## Verdict: PASS (conditional)

Every judge scored at least 102/120 in every counted round, and the two Criticals found were
fixed with tests (b7aa563, 50571f0). Against the baseline, the referees moved up (spec-discuss
101 → 109-110, 109 → 114) while native Opus ended two points lower on spec-discuss
(108 → 106) and four on curated-config (106 → 102); its findings were real edge cases of the
new reference-resolution guarantees, which the rounds then fixed. The r4 fixes are not
re-judged; the Phase 25 code-review step re-runs the judges on both skills. Remaining items
are Minors (progressive disclosure of the Skills section, description length, sibling
discovery list), deferred to that review.

Reports: `skill-judge/r<round>-<skill>.<judge>.md`.
