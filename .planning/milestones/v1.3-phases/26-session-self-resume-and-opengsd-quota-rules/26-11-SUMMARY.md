---
phase: 26-session-self-resume-and-opengsd-quota-rules
plan: 11
executor: orchestrator with subagent fixers
requirements-completed: []
orchestrator_verify: "make test-unit 61/61, arch, pyright, ruff green; check_verdicts.py verdicts ok; gate pending 3"
---

# Phase 26 Plan 11: skill-judge on the five changed skills

Fifteen judge rounds ran on ai-kit-session-wake, ai-kit-spec-execute-gsd, ai-kit-spec-execute-superpowers,
ai-kit-project-rules-agents and ai-kit-project-rules-all. Every real finding was fixed in a
`fix(26-11)` commit with a test; findings the code refuted are recorded with file and line in the
fix logs. The final verdicts are in `26-SKILL-JUDGE.md`.

## Result

- PASS: ai-kit-session-wake (108, 0/0), ai-kit-project-rules-all (102, 0 Critical, 1 Important, base 95).
- UNRESOLVED: ai-kit-spec-execute-gsd (101 against the carried base 105).
- FAIL: ai-kit-spec-execute-superpowers (94, 3 Important), ai-kit-project-rules-agents (93, 1 Critical, 2 Important).
- `check_verdicts.py` prints `verdicts ok`; `--gate` holds the three non-PASS skills pending, all listed
  under `## Pending acceptance` and carried into 26-12 with the owner questions.

## Judges and concurrent lanes

Judges changed on the owner's instructions (see the verdict file). Review lanes need a clean tree, so
nothing edited or committed while a lane ran. In the shared checkout the lanes ran concurrently as
follows (local time, 2026-10-30): round 7 referee-two and referee-three in parallel (16:3x-17:2x),
round 8 the same pair (17:08-17:24), round 12 referee-two from 19:55 beside a waiting referee-three
probe, round 15 referee-two alone (21:41-22:03). Two lanes were killed by SIGTERM at 17:20:12, probably
by another session's cleanup of the shared router; they were rerun. A background job was reaped once for
low system memory and restarted on the owner's word.

## Findings to carry

- The judge is not deterministic: an unchanged package moved from 115 with 0 Important to 108 with 1.
- tests/test_tool_substitution_hook compose test depends on the checkout path length (the Usage suffix
  is dropped above 200 characters).
- The wizard PTY tests needed 160 rows at 25 skills (fixed in tests/test_wizard_pty.py).
