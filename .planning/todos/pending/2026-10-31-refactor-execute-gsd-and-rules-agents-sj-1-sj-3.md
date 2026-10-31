---
created: 2026-10-31T03:01:00.476Z
title: Refactor execute-gsd and rules-agents (SJ-1, SJ-3)
area: skills
severity: major
files:
  - skills/ai-kit-spec-execute-gsd/SKILL.md
  - skills/ai-kit-project-rules-agents/SKILL.md
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
