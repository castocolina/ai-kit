# Phase 20 — skill-judge gate (EVAL-04, EVAL-05)

JUDGED_PATH: `skills/ai-kit-gsd-curated-config/SKILL.md`
JUDGED_COMMIT: `94f4806`
BASELINE: 109/120 in-session / 114/120 pi (Phase 19 final; the floor per judge)
SCORE: in-session pending / pi 114/120
CRITICAL: in-session pending / pi 0
IMPORTANT: in-session pending / pi 0
FIX_ITERATIONS_USED: 1 of 2

The digest covers `SKILL.md` and `references/`. Digest judged: `1a79713ef16f7bff`.

| Judge | Digest judged | Score | Critical/Important left | Verdict | Report |
|---|---|---:|---|---|---|
| in-session | 1a79713ef16f7bff | pending | pending | pending (orchestrator) | `skill-judge/in-session.md` |
| pi gpt-6.1-sol xhigh (initial) | 1a79713ef16f7bff | 115/120 | 0/1 | fail; superseded | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md` (initial attempt) |
| pi gpt-6.1-sol xhigh (fix round 1) | 1a79713ef16f7bff | 114/120 | 0/0 | pass | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md` |
| Phase 19 final in-session | 9cddf0a5892fba97 | 109/120 | 0/0 | context | `.planning/phases/19-evaluation-on-claude/19-SKILL-JUDGE.md` |
| Phase 19 final pi gpt-6.1-sol xhigh | 9cddf0a5892fba97 | 114/120 | 0/0 | context | `.planning/phases/19-evaluation-on-claude/19-SKILL-JUDGE.md` |

Both pi attempts were status `ok`, tree clean, and unchanged digest. The fix-round report meets its Phase 19 floor (114), with zero Critical and Important findings. The pi row passes. The in-session judge is pending orchestrator; no judge verdict is claimed for it.

## Judge attempts

| Attempt | Remaining before attempt | Result | Status line |
|---|---:|---|---|
| Initial pi | 1506 s | kept report | `AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=189s out=5360 tree=clean action=stop` |
| Fix-round pi 1 | 1030 s | kept report | `AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=205s out=5250 tree=clean action=stop` |

No judge process ran while files were written outside `tmp/`; each report was written under `tmp/judge/out`, checked for secrets and `$HOME`, then moved into this directory. The evaluation snapshot stayed unchanged. Secret-scan initially flagged the runner stderr path containing `$HOME`; it was redacted to `<home>`, after which both secret scan and home-path scan passed.

## Verdict: BLOCKED: in-session judge pending (orchestrator)
