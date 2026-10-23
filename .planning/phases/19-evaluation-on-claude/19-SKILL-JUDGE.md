# Phase 19 — skill-judge gate (EVAL-02)

JUDGED_PATH: skills/ai-kit-gsd-curated-config/SKILL.md
JUDGED_COMMIT: 86ad793
BASELINE: 105/120 (v1, Phase 07-04; reference, not a floor)
SCORE: 109/120 (pi gpt-6.1-sol: 114/120; pi glm-5.3: unavailable)
CRITICAL: 0
IMPORTANT: 0
FIX_ITERATIONS_USED: 2 of 3

The digest covers `SKILL.md` and `references/`. Pass rule per judge (D-06): `CURRENT >= 96`, `CRITICAL 0` and
`IMPORTANT 0`. Phase rule (18.1-22 form): the in-session judge passes, at least one pi judge passes,
and every non-superseded row for the digest passes or is `unavailable`. The in-session judge alone never
passes the skill. The loop also requires no GREEN regression on the same digest
(`19-PRESSURE-TESTS.md`, live `GREEN (sonnet)` rows on `9cddf0a5892fba97`).

| Judge | Digest judged | Score | Critical/Important left | Verdict | Report |
| --- | --- | --- | --- | --- | --- |
| v1 07-04 | - | 105/120 | 0/0 | context | r-v1 |
| pi gpt-6.1-sol xhigh (18.1 post-review) | 551234cc5f4f55cc | 112/120 | 0/0 | context | r-18.1a |
| pi glm-5.3 xhigh (18.1 post-review) | 551234cc5f4f55cc | n/a | n/a | context | r-18.1b |
| independent (18.1 post-review) | 551234cc5f4f55cc | 106/120 | 0/0 | context | r-18.1c |
| pi gpt-6.1-sol xhigh r2 | 9cddf0a5892fba97 | 114/120 | 0/0 | pass | r2a |
| pi glm-5.3 xhigh r2 | 9cddf0a5892fba97 | n/a | n/a | unavailable, capacity | r2b |
| in-session r2 | 9cddf0a5892fba97 | 109/120 | 0/0 | pass | r2c |

- r-v1: `.planning/milestones/v1.1-phases/07-curated-gsd-config-skill/07-04-SUMMARY.md`
- r-18.1a, r-18.1b, r-18.1c: `.planning/phases/18.1-one-runtime-model/18.1-SKILL-JUDGE.md` (`## ai-kit-gsd-curated-config`)
- r2a: `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh-r2.md` (4 Minor findings)
- r2b: `skill-judge/ai-kit-gsd-curated-config-pi-glm-5.3-xhigh-r2.md`, tried twice 60 s apart, both
  `AIKIT-XAI status=capacity cli=pi model=zai-coding-cn/glm-5.3:xhigh exit=75 cli_rc=1 elapsed=147s out=0 tree=clean action=retry-later`
  (weekly capacity limit until 2026-10-21)
- r2c: `skill-judge/in-session-r2.md` (5 Minor findings)

### Judge rounds

| Judge | Digest judged | Score | Critical/Important left | Verdict | Report |
| --- | --- | --- | --- | --- | --- |
| pi gpt-6.1-sol xhigh (round 0, 19-08) | f29ad8427446ce45 | 111/120 | 0/1 | fail, superseded (235e930d29d7d34c) | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md` |
| pi glm-5.3 xhigh (round 0, 19-08) | f29ad8427446ce45 | n/a | n/a | unavailable, capacity, superseded (235e930d29d7d34c) | `skill-judge/ai-kit-gsd-curated-config-pi-glm-5.3-xhigh.md` |
| in-session (round 0, 19-08) | f29ad8427446ce45 | 108/120 | 0/0 | pass, superseded (235e930d29d7d34c) | `skill-judge/in-session.md` |
| pi gpt-6.1-sol xhigh r1 | 235e930d29d7d34c | 113/120 | 0/1 | fail, superseded (9cddf0a5892fba97) | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh-r1.md` |
| pi glm-5.3 xhigh r1 | 235e930d29d7d34c | n/a | n/a | unavailable, capacity, superseded (9cddf0a5892fba97) | `skill-judge/ai-kit-gsd-curated-config-pi-glm-5.3-xhigh-r1.md` |
| in-session r1 | 235e930d29d7d34c | 109/120 | 0/0 | pass, superseded (9cddf0a5892fba97) | `skill-judge/in-session-r1.md` |

Fix rounds:

- Round 1 (f88594a, digest `235e930d29d7d34c`) addresses pi gpt-6.1-sol round-0 F1 (Important): the NEVER rule "Never skip the plan review or the dry run" was unscoped, but the kept v1 path has neither step.
  - The rule now names the v2 flow and points to `references/v1-path.md`, which says to show each `apply-*` command and run it only after the user answers.
  - GREEN j1: every gating check passes.
- Round 2 (86ad793, digest `9cddf0a5892fba97`) addresses pi gpt-6.1-sol r1 finding 1 (Important): "v1 requires informed approval without providing a pre-write effects preview."
  - The v1 rule now asks for the command with its passed values. It says that every `apply-*` except `apply-profile` and `apply-claude-md-path` also writes keys its flags do not show, which v1 cannot preview; this was checked against `ai_kit_gsd_curated_config/cli.py`. A full preview is routed to the v2 dry run.
  - GREEN j2: every gating check passes.

## Rejected findings

(none)

## Decisions routed through jev

(none in this gate; the 19-07 REFACTOR decision is in `19-PRESSURE-TESTS.md`)

## Verdict: PASS

## Phase decisions for owner review

- human_needed | 19-PRESSURE-TESTS.md | 19-07-D-full-key-r2 | laya `refactor_round_2` (0.9807); round 2 ran (19e3d3d) | the orchestrator agreed: SKILL.md step 4 already asked for the full key, and the D green-r1 agent grouped against it; GREEN r2 then passed every gating check
- human_needed | 19-09-SUMMARY.md | eval-D-trusted-roots-answer | owner review: opus D refused the bare "yes" as an answer to the open trusted-roots `needs_choice` and never applied; the sonnet re-sample passed | `pressure/D-green-opus.md` turn 3; decide whether `evals/03-v1-written-config.md` should answer that choice explicitly
- human_needed | 19-SKILL-JUDGE.md | glm-5.3-unavailable | `unavailable, capacity` in rounds 0, r1 and r2 (weekly limit until 2026-10-21) | the PASS rests on the in-session judge and pi gpt-6.1-sol (114/120, 0/0); the phase rule allows `unavailable`
- human_needed | 19-09-SUMMARY.md | v1-suite-package-attribute | owner review: `_reimport_with_ai_kit_spec_blocked` in the v1 test module leaves a degraded module bound on the package | worked around on the harness side (c326bbd); the v1 test module was left untouched (Run rule 8)
- advisory | 19-07-SUMMARY.md | B ensure_runner_disclosed | `fail (non-gating)` in RED-a, RED-b and every GREEN round | informational per jev 19-Q6; not routed
