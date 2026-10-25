# ai-kit-spec-review — skill-judge report (opencode router-env/my-referee-one, read-only review mode)

Round 5 (evidence round), skill digest `458a2dd3c1b61497`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

## Round 5: BLOCKED (the runner stopped the lane; no score)

Runner evidence lines:

```text
cross-ai: report status=quota lane=opencode/router-env/my-referee-one route=router attempts=7 cycles=0 first_failure=2026-10-25T04:25:46.793Z last_failure=2026-10-25T04:41:06.679Z stopped=deadline
AIKIT-XAI status=quota cli=opencode model=router-env/my-referee-one exit=75 cli_rc=1 elapsed=920s out=5192 tree=clean action=stop route=router rule=text-pre-dispatch pattern=verified attempts=7 cycles=0 retry_after_s=600 cycle=0
```

Upstream messages (OmniRoute, verbatim, trimmed):

```text
Service temporarily unavailable: all targets were skipped by pre-dispatch filters (Session (5h) 100% conn:dd6b6ba2; Session (5h) 100% conn:f48bcb3c)
Service temporarily unavailable: all targets were skipped by pre-dispatch filters (Session (5h) 100% conn:f48bcb3c)
[429]: The usage limit has been reached (reset after 4h 15m 3s)
```

## Last completed report from this judge (round 4, an earlier digest; reference only, not this verdict's score)

# Skill evaluation: `ai-kit-spec-review`

**94/120 (C).** The skill provides strong framework-aware review guidance and links directly to the new subprocess policy. Its normal dispatch path selects one CLI per call and forbids post-failure switches of harness, provider, or model. The Phase 25 runner and resume path still have defects that prevent the policy from being reliable. This was a static, read-only review; I did not run the runner or its self-test.

| Dimension | Score | Assessment |
|---|---:|---|
| D1 Knowledge Delta | 17/20 | Worktree grounding and framework routing add specific expertise. |
| D2 Mindset + Procedures | 13/15 | Lifecycle ceilings and dispatch order guide decisions. |
| D3 Anti-Patterns | 13/15 | Clear prohibitions with reasons. |
| D4 Specification Compliance | 15/15 | Valid frontmatter; description states what, when, and triggers. |
| D5 Progressive Disclosure | 11/15 | Explicit load triggers, but a 487-line body and mandatory 369-line reference are heavy. |
| D6 Freedom Calibration | 10/15 | Fragile resume and runner operations need safer constraints. |
| D7 Pattern Recognition | 8/10 | Recognizable process pattern. |
| D8 Practical Usability | 7/15 | Resume, cap, and evidence defects affect real stops. |
| **Total** | **94/120** | |

1. **Critical — Resume converts a fixed dispatch into a shell script.** [`references/cross-ai-dispatch.md:268–295`](skills/ai-kit-spec-review/references/cross-ai-dispatch.md#L268-L295) tells the agent to substitute paths and arguments into `-cmd.sh`, then run it with `bash`. A quoted heredoc prevents expansion *while writing*, not when Bash later executes substituted text; a document path containing shell syntax can execute then. **Fix:** persist an argv array as data and resume with a no-shell subprocess call, preserving the selected CLI and model.

2. **Critical — Review execution can delete a file in the caller’s home.** [`references/cross-ai.mjs:2488–2489`](skills/ai-kit-spec-review/references/cross-ai.mjs#L2488-L2489) unconditionally removes `$HOME/.fake-git-hang` after a child attempt, including in review mode. **Fix:** remove this test-marker cleanup from production execution and confine it to the self-test harness.

3. **Important — A quota episode can request a cooldown beyond its four-hour cap.** [`references/cross-ai.mjs:1795–1808`](skills/ai-kit-spec-review/references/cross-ai.mjs#L1795-L1808) checks the call deadline before the episode cap; [`references/cross-ai.mjs:2454–2462`](skills/ai-kit-spec-review/references/cross-ai.mjs#L2454-L2462) can then emit exit 75 with a full cooldown for a deadline stop. That conflicts with [`references/subprocess-quota-policy.md:48–49`](skills/ai-kit-spec-review/references/subprocess-quota-policy.md#L48-L49). **Fix:** enforce the absolute cap before admitting any rung or cooldown, including inside `cycleStop`; test a near-cap, short-deadline call.

4. **Important — Unconfirmed routes can inherit router-cycle state.** [`references/cross-ai.mjs:2396–2428`](skills/ai-kit-spec-review/references/cross-ai.mjs#L2396-L2428) loads and applies saved state without first confirming the current route. A later `--route-<cli> unknown` call for the same CLI/model can receive a cooldown or stored session, contrary to [`references/subprocess-quota-policy.md:35–40`](skills/ai-kit-spec-review/references/subprocess-quota-policy.md#L35-L40). **Fix:** load router-cycle state only for confirmed router routes; test a router call followed by an explicitly unknown-route call.

5. **Important — Stop evidence is incomplete for some failures.** Immediate classified stops increment attempts but return before setting failure timestamps, and an empty-answer stop increments neither attempts nor the per-failure log ([`references/cross-ai.mjs:2540–2575`](skills/ai-kit-spec-review/references/cross-ai.mjs#L2540-L2575)). The final report can therefore disagree with the documented evidence contract ([`references/subprocess-quota-policy.md:61–67`](skills/ai-kit-spec-review/references/subprocess-quota-policy.md#L61-L67)). **Fix:** record the attempt and timestamps before every failure return; test immediate auth/quota and empty answers.

6. **Minor — A short, unterminated limit message is not detected live.** The stderr relay checks a partial line only after it exceeds its buffer cap ([`references/cross-ai.mjs:1116–1128`](skills/ai-kit-spec-review/references/cross-ai.mjs#L1116-L1128)); a child that prints `quota exceeded` without a newline and hangs can wait for the attempt deadline. **Fix:** inspect the pending stderr fragment on each chunk and assert prompt termination in the live-partial self-test.

7. **Minor — Early cycle refusals leave a temporary directory.** The runner creates it at [`references/cross-ai.mjs:2384`](skills/ai-kit-spec-review/references/cross-ai.mjs#L2384), but the cap and not-yet-due returns at lines 2408–2422 precede the cleanup `finally` at lines 2650–2652. **Fix:** validate saved state before creating the directory, or move those returns inside the cleanup scope.

No files were changed; executable behavior and host scheduling remain unverified by this read-only review.

DIGEST 0255c52b8ea93d62
CURRENT 94/120
CRITICAL 2 IMPORTANT 3
