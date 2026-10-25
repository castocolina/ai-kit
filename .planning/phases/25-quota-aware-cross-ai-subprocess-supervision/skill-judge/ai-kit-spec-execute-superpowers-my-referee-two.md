# ai-kit-spec-execute-superpowers — skill-judge report (opencode router-env/my-referee-two, read-only review mode)

Round 6, skill digest `9fa91a3b0024ebf5`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

Runner status: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=312s out=604357 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0`

All verification done. Every load-bearing claim in the skill checked against the runner, the classifier, the CLI parsers, and the sibling policy file — and the working tree matches HEAD, so the diff I reviewed is what's on disk.

# Skill Evaluation Report: ai-kit-spec-execute-superpowers

**Pattern:** Process (phased Steps 0–4 with checkpoints/stop conditions) fused with Tool-style decision tables — appropriate for a stateful dispatch adapter. SKILL.md 461 lines + 386 lines of references.
**Knowledge ratio E:A:R ≈ 80:17:3** — nearly everything is earned operational knowledge; the only repetition is the declared NEVER-index convention (SKILL.md:20).

## Dimension table

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 18 | 20 | Pure expert content: mode-before-key reads, permanent-vs-same-wave exclusion split, token location inside `status`, digest-over-`<objective>` session reuse, `<files>` dirty-tree gate. No filler. |
| D2: Mindset + Procedures | 14 | 15 | Thinking frame at SKILL.md:109–111 ("is this exclusion permanent or same-wave only?") plus procedures Claude cannot know (resumable-state bash, wake protocol, `resume-exclusions`-only set arithmetic). |
| D3: Anti-Pattern Quality | 14 | 15 | Nine NEVER items, each with a non-obvious WHY (SKILL.md:22–47); repeated at point of use by design. |
| D4: Specification Compliance | 14 | 15 | Valid frontmatter; description has WHAT + WHEN + keywords (`docs/superpowers/plans/*.md`, subagent-driven-development) and a negative trigger (not for executing-plans). Dense but ~740 chars, valid YAML. |
| D5: Progressive Disclosure | 15 | 15 | MANDATORY reads embedded at exact points of use (SKILL.md:116, 193, 449, 55–58); design-notes.md gated by "read only when a rule looks arbitrary"; policy file linked, not copied — matching its own "links here; does not copy" rule (subprocess-quota-policy.md:3–5). |
| D6: Freedom Calibration | 14 | 15 | Fragile stateful protocol → low freedom: exact bash, fixed constants with justification, hard backgrounding rule. Judgment reserved for the delegated harness and the owner. |
| D7: Pattern Recognition | 9 | 10 | Clean Process+Tool fusion, deliberate and consistent. |
| D8: Practical Usability | 13 | 15 | Runnable commands, verified fallbacks (empty JSON → stop, no-JSON dispatch → relay stderr tail, empty STATUS → BLOCKED), edge cases covered. Gaps: findings 1–5 below. |

**Phase 25 accuracy check (all verified against code):** one-CLI-per-call/no-fallback (policy:8–13 ↔ SKILL.md:39–40, 415–421); failure ladder rung 1 same-session → rung 2 new sessions (policy:29–34 ↔ "the runner already ran its ladder"); router cycles across calls, `retry_after_s`+`cycle`, 4-hour cap → exit 69 (policy:37–55, `capS 14400` at cross-ai.mjs:69 ↔ SKILL.md:360–374); evidence lines on every stop (policy:63–69 ↔ SKILL.md:295, 339–341, 405–406); tokens live only in the `status` dict (execute_dispatch.py:151); both 75 and 69 classify `"quota"` (dispatch_injection.py:412–416); confirmed lane = catalog-confirmed `fallback_quota` → `--route-<cli> router` (runner_dispatch.py:213–226, 578–579, 182–183 — the flag *is* passed even though `execute_dispatch.py:98–103` leaves `route=None`, because `run_runner` resolves it); 1800 s floor (ai-kit-gsd-curated-config cross_ai.py:47); reason taxonomy incl. `capacity`/`billing_or_access`/`git_timeout` (error_classifier.py:16–26); `cache-path --kind quota` and `trust-local --cwd --show` exist (ai_kit_spec/cli.py:142–143, 266–271); `fable` alias (detection.py:112); Node 24 floor sourced in phase 18.1 research.

## Findings

1. **[Minor] Fold block precedes the order that gates it.** SKILL.md:325–334 presents the wave-fold bash, then SKILL.md:336–341 ("The evidence lines come before that fold … 1. Relay the evidence lines first … then run the fold block above") defines the true order. A linear executor writes state before relaying evidence — the exact inversion the text warns against. *Fix:* move the fold block under step 1, or prefix it with "(shown for reference; run it at step 1 below)".
2. **[Minor] Stale reason taxonomy in the shipped package docstring.** `ai_kit_spec_superpowers/dispatch_injection.py:99–113` (`QuotaExhaustedError`) lists only quota/auth/timeout/configuration/dispatch_unavailable/real_error + route names, while SKILL.md:174–179 and `error_classifier.py:16–26` also classify `billing_or_access`, `capacity`, `git_timeout`, and cli.py:133 sets `no_usable_dispatch`. *Fix:* replace the enumerated list with a pointer to `ai_kit_spec.error_classifier.REASONS` so the package cannot drift again.
3. **[Minor] Two scheduling constraints stated as fact without an in-repo source.** SKILL.md:368–369: "at least 60 s, rounded up to the next whole minute" and "the job lives only as long as the session" — neither CronCreate granularity claim appears in subprocess-quota-policy.md, while the skill does flag the no-scheduler printed row as unverified (SKILL.md:50–53). *Fix:* mark both as host-tool assumptions or cite CronCreate's minute granularity as their source.
4. **[Minor] Empty/unknown anchor gate sits after the computation it should gate.** references/escalation.md:40–49 computes `$ESCALATION_EXCLUDE_JSON` (an empty anchor silently yields `['""']`); only lines 56–61 say "**An empty or unknown anchor never dispatches.**" *Fix:* move the gate paragraph above the bash, or add a guard line (`[ -n "$ESCALATION_ANCHOR_KEY" ] || stop`) before the block.
5. **[Minor] "again before acting on a stop" is ambiguous for Step 2 stops.** SKILL.md:55–58 makes the policy read MANDATORY "before the first external dispatch, and again before acting on a stop", but Step 2's `quota_exhausted`/`no_candidate` stops (SKILL.md:169–197) can happen with no dispatch ever run, and "again" presumes a first read. *Fix:* "and again before acting on any stop, including a Step 2 resolution stop".

Skipped/not checked: `task_classification.py` and `cross-ai.mjs`'s self-test were not read in full; nothing was executed (read-only judge). All claims verified statically against source — a live dispatch run could still surprise.

DIGEST 9fa91a3b0024ebf5
CURRENT 111/120
CRITICAL 0 IMPORTANT 0
