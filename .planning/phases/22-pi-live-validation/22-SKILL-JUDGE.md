# 22-07 — Skill-judge evidence (pi wording)

JUDGED_PATH: skills/ai-kit-gsd-curated-config/SKILL.md
JUDGED_COMMIT: 960eb90 (r1, after review fix a53569b)
PRE_CHANGE: 0e17b22 (digest f0c43a5da52a587d)
BASELINE: native Opus 105/120, opencode router-env/my-plan-review 112/120 (pre-change)
SCORE: native Opus 106/120, opencode router-env/my-plan-review 114/120 (r1)
CRITICAL: 0
IMPORTANT: 1 (native Opus r1; passes on CURRENT >= 96 with no regression)
FIX_ITERATIONS_USED: 0 of 2
Digest judged: 6faf9b459284c6f0.

The digest covers SKILL.md and references/. Judge set (owner, 2026-10-23): one clean-context native
Opus subagent and opencode `router-env/my-plan-review` through the cross-AI runner in review mode.

| Judge | Role | Digest judged | Score | Critical/Important left | Verdict | Report |
|---|---|---|---|---|---|---|
| native Opus (clean context) | pre-change baseline | f0c43a5da52a587d | 105/120 | 0/1 | context | skill-judge/pre-native-opus.md |
| opencode router-env/my-plan-review | pre-change baseline | f0c43a5da52a587d | 112/120 | 0/2 | context | skill-judge/pre-opencode-plan-review.md |
| native Opus (clean context) | post-change | 2e55b8f4212d167c | 106/120 | 0/0 | superseded (6faf9b459284c6f0) | skill-judge/post-native-opus.md |
| native Opus (clean context) | post-change r1 | 6faf9b459284c6f0 | 106/120 | 0/1 | pass | skill-judge/post-native-opus-r1.md |
| opencode router-env/my-plan-review | post-change | 2e55b8f4212d167c | 114/120 | 0/0 | superseded (6faf9b459284c6f0) | skill-judge/post-opencode-plan-review.md |
| opencode router-env/my-plan-review | post-change r1 | 6faf9b459284c6f0 | 114/120 | 0/0 | pass | skill-judge/post-opencode-plan-review-r1.md |

The pre-change digest is the one Phase 21's judge row was pending on, so these baseline rows also
record that tree's scores (Opus 105, opencode 112).

## Rounds

1. Pre-change baseline and post-change judges ran in parallel on unchanged digests. Both post rows
   pass (no Critical or Important, scores at or above each judge's baseline); no fix round needed.
2. r1 (2026-10-23): the code-review fix a53569b reworded the pi session-steer sentence, so the
   security audit (T-22-18) found the evidence stale. Both judges re-ran on 6faf9b459284c6f0: Opus
   106 (one Important, the v1 pre-flight wording at L60-63, which predates this phase) and opencode
   114; both pass the rule, so the earlier post rows are superseded.

## Judge attempts

- pre opencode: `AIKIT-XAI status=ok cli=opencode model=router-env/my-plan-review exit=0 cli_rc=0 elapsed=273s out=218882 tree=clean action=stop`
- post opencode: `AIKIT-XAI status=ok cli=opencode model=router-env/my-plan-review exit=0 cli_rc=0 elapsed=78s out=214628 tree=clean action=stop`
- post r1 opencode: `AIKIT-XAI status=ok cli=opencode model=router-env/my-plan-review exit=0 cli_rc=0 elapsed=94s out=305862 tree=clean action=stop`
- native Opus lanes: one clean-context subagent each, reports saved verbatim in summary form.

## Verdict: PASS
