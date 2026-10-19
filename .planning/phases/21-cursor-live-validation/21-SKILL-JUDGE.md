# Phase 21 — skill-judge gate (EVAL-07)

JUDGED_PATH: `skills/ai-kit-gsd-curated-config/SKILL.md`
JUDGED_COMMIT: bea59cc (fix round 2; the LIFT commit 3a36abd and fix round 1 23de1f8 precede it)
BASELINE: 109/120 in-session / 116/120 pi (Phase 20 final; the floor per judge)
SCORE: in-session 110/120 / pi 114/120 (final digest)
CRITICAL: in-session 0 / pi 0
IMPORTANT: in-session 0 / pi 0
FIX_ITERATIONS_USED: 2 of 2 (round 1 23de1f8, round 2 bea59cc; orchestrator)

The digest covers `SKILL.md` and `references/`. Digest judged: `85da5a6682d937c5`.

| Judge | Digest judged | Score | Critical/Important left | Verdict | Report |
|---|---|---:|---|---|---|
| Phase 20 final in-session | ea3200ce9624de80 | 109/120 | 0/0 | context | `.planning/phases/20-live-validation-on-codex-opencode/20-SKILL-JUDGE.md` |
| Phase 20 final pi gpt-6.1-sol xhigh | ea3200ce9624de80 | 116/120 | 0/0 | context | `.planning/phases/20-live-validation-on-codex-opencode/20-SKILL-JUDGE.md` |
| in-session | 85da5a6682d937c5 | 110/120 | 0/0 | pass | `skill-judge/in-session.md` |
| pi gpt-6.1-sol xhigh | 85da5a6682d937c5 | 114/120 | 0/0 | below the 116 floor (owner review) | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md` |
| pi gpt-6.1-sol xhigh (round 2) | 7d1a986df40b63a8 | 114/120 | 0/0 | below floor, superseded (85da5a6682d937c5) | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh-r2.md` |
| pi gpt-6.1-sol xhigh (round 1, orchestrator) | b924ac84e1d6d3c9 | 114/120 | 0/1 | fail, superseded (7d1a986df40b63a8) | `skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh-r1.md` |
| in-session (round 1) | b924ac84e1d6d3c9 | 109/120 | 0/0 | pass, superseded (85da5a6682d937c5) | `skill-judge/in-session-r1.md` |
| in-session (executor dispatch) | b924ac84e1d6d3c9 | pending | pending | superseded (orchestrator report written) | — |
| pi gpt-6.1-sol xhigh (executor attempt 1) | b924ac84e1d6d3c9 | unavailable | n/a | unavailable (quota), superseded (b924ac84e1d6d3c9 orchestrator round) | — |
| pi gpt-6.1-sol xhigh (executor attempt 2) | b924ac84e1d6d3c9 | unavailable | n/a | unavailable (quota), superseded (b924ac84e1d6d3c9 orchestrator round) | — |

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

- **Orchestrator round 1 (digest `b924ac84e1d6d3c9`).** In-session 109/120 0/0. The pi judge was retried
  every 10 min while its ChatGPT subscription-sharing limit held; one run at 23:50 produced a report
  but the runner withheld it (`contract_violation`, tree dirty from a concurrent Phase 21.1 review
  commit; the judge had read-only tools). On a clean tree: pi 114/120 with 1 Important (an offline or
  no-write request had disclosure but no stop branch). Fix round 1 (23de1f8): inventory now stops and
  asks on such a request.
- **Round 2 (digest `7d1a986df40b63a8`).** pi 114/120 0/0, still under its 116 floor. Fix round 2
  (bea59cc): quoted `--project-dir "<target>"` / `--path "<detected path>"`, merged the two repeated
  dry-run/full-key mistake rows, corrected runner.md's flag-count sentence. pi Minor 2 (profile
  guidance) not applied: it needs verified gsd-core behavior.
- **Final (digest `85da5a6682d937c5`).** In-session 110/120 0/0; pi 114/120 0/0. Both fix rounds used.
  The cap decision went through the jev ladder (Laya B 0.43 fallback); own reasoning chose B: AGENTS.md
  requires no regression versus baseline, pi sits 2 below its Phase 20 116 on three successive digests
  (its Phase 20 range was 113-116, so this may be judge variance), and calling it PASS would claim more
  than verified. Owner review decides whether 114 is variance.

## Judge attempts

| Attempt | Result | Status line |
|---|---|---|
| Executor pi attempt 1 | quota, retried after 60 s | `AIKIT-XAI status=quota cli=pi model=openai/gpt-6.1-sol:xhigh exit=75 cli_rc=1 elapsed=6s out=0 tree=clean action=retry-later` |
| Executor pi attempt 2 | quota, second failure -> judge unavailable | `AIKIT-XAI status=quota cli=pi model=openai/gpt-6.1-sol:xhigh exit=75 cli_rc=1 elapsed=4s out=0 tree=clean action=retry-later` |

| Orchestrator pi round 1 (clean tree) | report kept (-r1) | `AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=180s out=6159 tree=clean action=stop` |
| Orchestrator pi round 2 | report kept (-r2) | `AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=149s out=5829 tree=clean action=stop` |
| Orchestrator pi final | report kept | `AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=160s out=6337 tree=clean action=stop` |

HUMAN_NEEDED: pi gpt-6.1-sol scored 114/120 (0 Critical, 0 Important) against its 116/120 Phase 20 baseline after both fix rounds; owner decides whether that is judge variance (accept as PASS) or a regression to fix.

## Verdict: UNRESOLVED (owner review: pi 114/120 below its 116 baseline; 0 Critical, 0 Important on both judges)
