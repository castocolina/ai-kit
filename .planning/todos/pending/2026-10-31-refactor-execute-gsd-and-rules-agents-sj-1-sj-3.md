---
created: 2026-10-31T03:01:00.476Z
title: Refactor execute-gsd and rules-agents (SJ-1, SJ-3)
area: skills
severity: major
files:
  - skills/ai-kit-spec-execute-gsd/SKILL.md
  - skills/ai-kit-project-rules-agents/SKILL.md
  - skills/ai-kit-spec-execute-superpowers/SKILL.md
  - .planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-SKILL-JUDGE.md
---

## Problem

Phase 26 closed with two skills whose skill-judge verdicts the owner accepted as-is and deferred
(owner message, 2026-10-30), because the judge kept finding new detail in these large skills
round after round:

- `ai-kit-spec-execute-gsd` (SJ-1): UNRESOLVED, round 15 score 101 against the carried base 105,
  0 Critical and 2 Important open.
- `ai-kit-project-rules-agents` (SJ-3): FAIL, round 15 score 93, 1 Critical and 2 Important open.
  The Critical (an unattended `git restore` could discard uncommitted edits) was refuted by
  definition: a `clean` file is tracked and unmodified at backup time. It is a wording issue.

Both are pending a refactor, not accepted as good.

## Solution

Refactor both skills so a re-judge passes without a carried exception. Decide the rules-agents
refactor together with backlog item 999.16 (one event-keyed playbook skill for the
`ai-kit-project-rules-*` family), since that item may change where its content lives.

Evidence: `.planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-SKILL-JUDGE.md`
(verdicts, rounds, owner decisions), the judge reports under
`.planning/phases/26-session-self-resume-and-opengsd-quota-rules/skill-judge/r15/`, and the
owner captures SJ-1 and SJ-3 in `26-OWNER-CAPTURES.md` in the same phase directory.

## SJ-2: ai-kit-spec-execute-superpowers (deferred by the owner, 2026-10-31)

Round 24 scored 86/120 (72%, grade C), 1 Critical and 2 Important, under the original skill-judge
rubric; rounds 18-24 with the same judge scored 104, 89, 96, 97, 96, (23 invalid), 86. The judge
varies about 8 points on an unchanged package, so the skill is noise-limited at about 86-104/120.
Real defects found on the way were fixed (79edce6, ff1429f, 8a1ec6f, 034f05e, 36ee536). The cause
is structural: many resume paths (pinned resume, escalation re-entry, wake, owner stop), and each
one opens a new edge case in the next judge round.

Refactor goal: remove the alternative resume paths, leaving a single pinned-resume path and a
single owner-stop path. Then re-judge with the NEW percent-based skill-judge rubric (max 125, not
comparable with the 120-point scores above), embedding `references/rubric.md` and the spec sources
it cites in the judge prompt; the old prompt builder embedded only `SKILL.md`.

Proposal (not applied): replace the AGENTS.md pass rule `score >= 96/120` with a percent-based one,
since the installed rubric no longer has a 120-point maximum.

Dependency: backlog item 999.17 (lite or strong executor choice through jev-fast-decision) changes the same skills (`ai-kit-spec-execute`, `-gsd`, `-superpowers`, `ai-kit-spec-review`) and is built on the resume paths this refactor leaves.
