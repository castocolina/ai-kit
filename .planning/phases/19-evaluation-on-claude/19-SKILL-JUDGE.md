# Phase 19 — skill-judge gate (EVAL-02)

JUDGED_PATH: skills/ai-kit-gsd-curated-config/SKILL.md
JUDGED_COMMIT: pending
BASELINE: 105/120 (v1, Phase 07-04; reference, not a floor)
SCORE: 108/120 (pi gpt-6.1-sol: 111/120; pi glm-5.3: unavailable)
CRITICAL: 0
IMPORTANT: 0
FIX_ITERATIONS_USED: 0 of 3

The digest covers `SKILL.md` and `references/`. Pass rule per judge (D-06): `CURRENT >= 96`, `CRITICAL 0` and
`IMPORTANT 0`. Phase rule (18.1-22 form): the in-session judge passes, at least one pi judge passes,
and every non-superseded row for the digest passes or is `unavailable`. The in-session judge alone never
passes the skill.

| Judge | Digest judged | Score | Critical/Important left | Verdict | Report |
| --- | --- | --- | --- | --- | --- |
| v1 07-04 | - | 105/120 | 0/0 | context | r-v1 |
| pi gpt-6.1-sol xhigh (18.1 post-review) | 551234cc5f4f55cc | 112/120 | 0/0 | context | r-18.1a |
| pi glm-5.3 xhigh (18.1 post-review) | 551234cc5f4f55cc | n/a | n/a | context | r-18.1b |
| independent (18.1 post-review) | 551234cc5f4f55cc | 106/120 | 0/0 | context | r-18.1c |
| pi gpt-6.1-sol xhigh | f29ad8427446ce45 | 111/120 | 0/1 | fail | r1 |
| pi glm-5.3 xhigh | f29ad8427446ce45 | n/a | n/a | unavailable, capacity | r2 |
| in-session | f29ad8427446ce45 | 108/120 | 0/0 | pass | r3 |

- r-v1: `.planning/milestones/v1.1-phases/07-curated-gsd-config-skill/07-04-SUMMARY.md`
- r-18.1a, r-18.1b, r-18.1c: `.planning/phases/18.1-one-runtime-model/18.1-SKILL-JUDGE.md` (`## ai-kit-gsd-curated-config`)
- r1: `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md`. Its one Important finding is F1: the NEVER rule
  "Never skip the plan review or the dry run" is not scoped to v2, while the kept v1 path has neither step.
- r2: `skill-judge/ai-kit-gsd-curated-config-pi-glm-5.3-xhigh.md`, tried twice 60 s apart, both
  `AIKIT-XAI status=capacity cli=pi model=zai-coding-cn/glm-5.3:xhigh exit=75 cli_rc=1 elapsed=147s out=0 tree=clean action=retry-later`
- r3: `skill-judge/in-session.md`

## Decisions routed through jev

(none)

## Verdict: PENDING (fix loop in 19-09)
