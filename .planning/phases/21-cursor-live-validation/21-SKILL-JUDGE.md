# Phase 21 — skill-judge gate (EVAL-07)

JUDGED_PATH: `skills/ai-kit-gsd-curated-config/SKILL.md`
JUDGED_COMMIT: 3a36abdbbf5c (21-05 Task 1, the LIFT commit: cursor row split, README row, test pin)
BASELINE: 109/120 in-session / 116/120 pi (Phase 20 final; the floor per judge)
SCORE: in-session 109/120 / pi unavailable (quota)
CRITICAL: in-session 0 / pi n/a
IMPORTANT: in-session 0 / pi n/a
FIX_ITERATIONS_USED: 0 of 2 (no judge produced a scorable report)

The digest covers `SKILL.md` and `references/`. Digest judged: `b924ac84e1d6d3c9`.

| Judge | Digest judged | Score | Critical/Important left | Verdict | Report |
|---|---|---:|---|---|---|
| Phase 20 final in-session | ea3200ce9624de80 | 109/120 | 0/0 | context | `.planning/phases/20-live-validation-on-codex-opencode/20-SKILL-JUDGE.md` |
| Phase 20 final pi gpt-6.1-sol xhigh | ea3200ce9624de80 | 116/120 | 0/0 | context | `.planning/phases/20-live-validation-on-codex-opencode/20-SKILL-JUDGE.md` |
| in-session | b924ac84e1d6d3c9 | 109/120 | 0/0 | pass | `skill-judge/in-session.md` |
| in-session (executor dispatch) | b924ac84e1d6d3c9 | pending | pending | superseded (orchestrator report written) | — |
| pi gpt-6.1-sol xhigh (executor attempt 1) | b924ac84e1d6d3c9 | unavailable | n/a | unavailable (quota), retried | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md` |
| pi gpt-6.1-sol xhigh (executor attempt 2) | b924ac84e1d6d3c9 | unavailable | n/a | unavailable (quota), second failure | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md` |

## Rounds

- **Executor dispatch (digest `b924ac84e1d6d3c9`, 21-05 LIFT branch).** SKILL.md changed in
  Phase 21 regardless of the label (21-03's `Resolution order` sentence, 21-07's `(template 5)`
  sentence, plus Task 1's cursor row split), so the AGENTS.md skill rule applies and the judge
  runs in both branches. The pi judge ran through this repo's template-5 runner
  (`--prefer pi --model-pi openai/gpt-6.1-sol:xhigh --mode review --no-preamble --timeout 600
  --outer-timeout 630`) under the plan's 1800 s budget (1615-1712 s remaining at each attempt).
  Both attempts returned `status=quota` (subscription sharing usage limit); the plan allows one
  retry after 60 s, which was used, so the pi row records `judge unavailable` with the status
  line verbatim. The in-session row is the executor's pending marker: a cross-AI executor has no
  Skill tool, so the orchestrator (the Claude session with the Skill tool) must replace the
  marker with a real report before this gate can pass. A pending marker is not a PASS and is not
  a soft note: 21-06 Task 2's precondition refuses any `pending (orchestrator)` marker in this
  file or `skill-judge/`, so the phase cannot close until the orchestrator's report (with its own
  `DIGEST` line equal to the digest of the tree it judged) replaces the marker.
- No commit and no write outside `tmp/` while a judge ran; the digest was unchanged after the
  judge exited (`b924ac84e1d6d3c9` before and after); reports passed `secret-scan` and the
  `$HOME` grep before the batch move ($HOME hits in the scratch `.err` files were redacted to
  `<home>` and listed in 21-05-SUMMARY.md); `snapshot --check tmp/p21/plan05.before.json`
  prints `snapshot ok` (no `~/.cursor` or other allowlist write). No glm judge (run constraint).

## Judge attempts

| Attempt | Result | Status line |
|---|---|---|
| Executor pi attempt 1 | quota, retried after 60 s | `AIKIT-XAI status=quota cli=pi model=openai/gpt-6.1-sol:xhigh exit=75 cli_rc=1 elapsed=6s out=0 tree=clean action=retry-later` |
| Executor pi attempt 2 | quota, second failure -> judge unavailable | `AIKIT-XAI status=quota cli=pi model=openai/gpt-6.1-sol:xhigh exit=75 cli_rc=1 elapsed=4s out=0 tree=clean action=retry-later` |

## Verdict: BLOCKED: pi judge pending (quota)
