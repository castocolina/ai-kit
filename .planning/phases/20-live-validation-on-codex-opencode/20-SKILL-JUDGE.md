# Phase 20 — skill-judge gate (EVAL-04, EVAL-05)

JUDGED_PATH: `skills/ai-kit-gsd-curated-config/SKILL.md`
JUDGED_COMMIT: `HEAD after the code-review fixes (runner.md IN-02 wording, db4cbc5)`
BASELINE: 109/120 in-session / 114/120 pi (Phase 19 final; the floor per judge)
SCORE: in-session 109/120 / pi 116/120 (post-review digest)
CRITICAL: in-session 0 / pi 0
IMPORTANT: in-session 0 / pi 0
FIX_ITERATIONS_USED: 2 of 2 (fix-loop rounds for a failing row: round 1 executor 94f4806, round 2 orchestrator c7089ff); plus one voluntary accuracy edit dd1ab1e made while both rows passed

The digest covers `SKILL.md` and `references/`. Digest judged: `ea3200ce9624de80`.

| Judge | Digest judged | Score | Critical/Important left | Verdict | Report |
|---|---|---:|---|---|---|
| in-session | ea3200ce9624de80 | 109/120 | 0/0 | pass | `skill-judge/in-session.md` |
| pi gpt-6.1-sol xhigh | ea3200ce9624de80 | 116/120 | 0/0 | pass | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md` |
| in-session (round 3) | 2663ee4bf6433cc1 | 109/120 | 0/0 | pass, superseded (ea3200ce9624de80) | `skill-judge/in-session-r3.md` |
| pi gpt-6.1-sol xhigh (round 3) | 2663ee4bf6433cc1 | 116/120 | 0/0 | pass, superseded (ea3200ce9624de80) | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh-r3.md` |
| in-session (round 2) | 721980032d31c5af | 109/120 | 0/0 | superseded (2663ee4bf6433cc1) | `skill-judge/in-session-r2.md` |
| pi gpt-6.1-sol xhigh (round 2) | 721980032d31c5af | 113/120 | 0/1 | fail, superseded (2663ee4bf6433cc1) | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh-r2.md` |
| pi gpt-6.1-sol xhigh (executor fix round 1) | 1a79713ef16f7bff | 114/120 | 0/0 | pass, superseded (721980032d31c5af) | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh-r1.md` |
| pi gpt-6.1-sol xhigh (executor initial) | 1a79713ef16f7bff | 115/120 | 0/1 | fail, superseded (1a79713ef16f7bff fix round) | report overwritten by the executor's fix round |
| in-session (executor dispatch) | 1a79713ef16f7bff | pending | pending | superseded (marker replaced by the orchestrator) | — |
| Phase 19 final in-session | 9cddf0a5892fba97 | 109/120 | 0/0 | context | `.planning/phases/19-evaluation-on-claude/19-SKILL-JUDGE.md` |
| Phase 19 final pi gpt-6.1-sol xhigh | 9cddf0a5892fba97 | 114/120 | 0/0 | context | `.planning/phases/19-evaluation-on-claude/19-SKILL-JUDGE.md` |

## Rounds

- **Executor dispatch (digest `1a79713ef16f7bff`).** pi initial 115 with 1 Important, fixed in
  94f4806; pi re-judge 114 0/0. The in-session row was left as the pending marker (no Skill tool
  in the cross-AI executor).
- **Voluntary accuracy edit dd1ab1e (digest `721980032d31c5af`).** With both rows passing, the
  orchestrator fixed stale runner.md text found while judging: "Template 3 understands three
  flags" under a template-4 heading, no mention of opencode `--standalone`, the readiness claim
  (the floor is template 3, `cross_ai_script._READY_TEMPLATE`), and the live-timeout ladder
  (`liveOuterTimeoutS`). Re-judge: in-session 109 0/0, pi 113 with 1 Important.
- **Fix round 2 c7089ff (digest `2663ee4bf6433cc1`).** pi's Important was verified in code:
  "the host CLI is never a review lane" held only for v2; v1 `detect-review-candidate`
  (`preference_match.best_review_candidate`, `cli._apply_review_writes`) has no host exclusion.
  SKILL.md now scopes the guarantee to v2 and v1-path.md tells the user to disclose a same-host
  review. No v1 behavior change (v1 kept). Re-judge: in-session 109 0/0, pi 116 0/0.
- **Post-code-review re-judge (digest `ea3200ce9624de80`).** The review fix for IN-02 narrowed
  runner.md's `--standalone` sentence to what was observed. Both judges re-run on the new digest:
  in-session 109 0/0, pi 116 0/0.

The cap-accounting call (fix the verified Important versus stop at UNRESOLVED) went through the
jev ladder: Laya fallback at 0.50 confidence, so the orchestrator decided on its own reasoning
(the alternatives left a known false statement in the skill or restored stale text). Owner
review item.

## Judge attempts

| Attempt | Result | Status line |
|---|---|---|
| Executor initial pi | kept report | `AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=189s out=5360 tree=clean action=stop` |
| Executor fix-round pi 1 | kept report | `AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=205s out=5250 tree=clean action=stop` |
| Orchestrator pi round 2 | kept report | `AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=172s out=5293 tree=clean action=stop` |
| Orchestrator pi round 3 | kept report | `AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=144s out=5017 tree=clean action=stop` |
| Orchestrator pi post-review | kept report | `AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=128s out=4686 tree=clean action=stop` |

No commit and no write outside `tmp/` while a judge ran; the digest was unchanged after each
round; reports passed `secret-scan` and the `$HOME` grep before the move. No glm judge (run
constraint). The code-review step reuses this file while its `Digest judged` equals the
committed digest.

## Verdict: PASS
