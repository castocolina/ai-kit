Judge: opus
Reviewed-sha256: 1f5f09727354aee6c185d4f574da6e1e6aa4c5b34fed2e90ee9e4006fcb16bd1
Lane: native subagent completed
Score: 104
Critical: 0
Important: 4

# Skill Evaluation: ai-kit-spec-execute-superpowers

I scored the whole skill against the rubric: SKILL.md (459 lines), the three files under `references/`, and the `dispatch_injection.py` classifier, which the 25.1 diff changed. I checked the claims against `skills/ai-kit-cross-ai/SKILL.md`, its `references/subprocess-quota-policy.md`, `ai_kit_spec/runner_dispatch.py` and the runner template `cross-ai.mjs`.

**Pattern:** Process/Tool hybrid. **Knowledge ratio:** roughly E:A:R = 75:20:5.

**What the skill gets right:**
- It never switches harness, provider or model after a failure. Exit 75 with `retry_after_s=` and `cycle=` gets one one-shot wait, then the same pinned `injection_json` runs again (SKILL.md:356-370).
- An exit 69 (`stopped=hard-waits`, `stopped=cap`, `lane stopped=`) is an owner stop.
- The upstream lines are relayed verbatim (SKILL.md:338-340, 400-402).
- The `capacity` fix now says "a later retry on the same lane" (SKILL.md:180).
- The copilot exec note matches `runner_dispatch.py:175-182`.
- `dispatch-task` passes `--runtime`, `--outer-timeout` and `--route-<cli>` (`runner_dispatch.py:202-262`).
- The runner's stderr reaches `$DISPATCH_BASE.err` live (`runner_dispatch.py:287-300`).
- The classifier matches the runner's refusal and hard-tier shapes (`cross-ai.mjs:3922-4040`).

## Dimension scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Dense, repo-specific state and wake rules; some restated policy and repeated prose |
| D2 Mindset + Procedures | 13 | 15 | "Permanent vs same-wave" framing plus exact bash; non-obvious ordering (evidence before fold) |
| D3 Anti-Pattern Quality | 14 | 15 | NEVER index with reasons, each repeated where it applies |
| D4 Specification / Description | 14 | 15 | WHAT, WHEN and a "not for executing-plans" clause; one dense sentence |
| D5 Progressive Disclosure | 12 | 15 | MANDATORY triggers for state-management and escalation; the cross-AI policy link has no load trigger; 459 lines |
| D6 Freedom Calibration | 14 | 15 | Low freedom on fragile state and scheduling, correctly |
| D7 Pattern Recognition | 8 | 10 | Clear phased process; long for the pattern |
| D8 Practical Usability | 12 | 15 | Thorough edge cases, but there is a gap after the wake and an internal contradiction (findings 1-2) |

**Total: 104/120 (grade B).**

## Findings

1. **Important. No stop after the wake is scheduled.** SKILL.md:356-370 says to schedule one `CronCreate` wake (or print the re-invoke row) but never says to end the wave afterwards. An agent could go on to task N+1 while task N's wake is pending, and superpowers tasks are sequential. The runner would also refuse that same lane (pending `due_at`, `subprocess-quota-policy.md:114-115`).
   - Fix: add "Then STOP this wave and end the turn; do not start the next task until the wake's 'ok' path has handled this task's report."

2. **Important. "Never switch" is stated without its scope and contradicts the skill's own rounds 4-5 rule.**
   - SKILL.md:52-53 says "Never switch harness, provider or model." with no qualifier.
   - SKILL.md:411-417 and 440-452 prescribe a pre-dispatch re-resolution to a different ladder key, which may be another runtime.
   - The canonical rule, ai-kit-cross-ai SKILL.md:146, scopes it to "on any failure".
   - Fix: "Never switch harness, provider or model after a failed or unusable run (ai-kit-cross-ai §8). Pre-dispatch selection and the rounds 4-5 bump below are the only key changes, both pending owner confirmation."

3. **Important. The pointer to the canonical policy lost its load trigger.**
   - SKILL.md:39-42 and 52-53 are now bare links.
   - The replaced text was "MANDATORY before the first external dispatch, and again before acting on a stop" (see the 25.1 diff), so the canonical policy may never load.
   - Fix: "MANDATORY before the first `dispatch-task` and before acting on any non-zero exit: read `../ai-kit-cross-ai/SKILL.md` §4, §6 and §8. Read its `references/subprocess-quota-policy.md` only for config, catalog or overlay questions."

4. **Important. Router-only wording remains in two MANDATORY references.**
   - state-management.md:63 says "the one-shot router wake".
   - escalation.md:77-78 says "for the ruled router exit 75, the one-shot wake re-dispatches the same injection".
   - Since 25.1, a spent transient ladder also exits 75 with the hard tier (`subprocess-quota-policy.md:97`; SKILL.md:320-322, 356-357). An agent following these references could treat a transient exit 75 as an owner stop.
   - Fix: replace both with "an exit 75 carrying `retry_after_s=` and `cycle=` (router quota or a spent transient ladder)".

5. **Minor. The `"quota"` bullet calls every outcome time-bound, but some are terminal.** SKILL.md:320-322 says "time-bound hard-tier outcome". The classifier also returns `quota` for terminal cases: exit 69 hard-waits, cap, lane-refusal, and a bare 75 (`dispatch_injection.py:398-430`). Point 4 clarifies only later.
   - Fix: say in the bullet that it also covers terminal hard-tier stops, and that point 4 decides wait versus stop.

6. **Minor. Incomplete list of evidence lines.** SKILL.md:290 names only `cross-ai: report` and `AIKIT-XAI`. Points 1 and 4 also need the `cross-ai: upstream` lines and the `cross-ai: state` or `lane stopped=` path.
   - Fix: list all four.

7. **Minor. Leftover binding in the wake prompt.** The wake prompt binds `REVIEW_SKILL_DIR` (SKILL.md:376, counted in "nine placeholders" at :390), but nothing on the wake path uses it now that the policy pointer moved to ai-kit-cross-ai.
   - Fix: drop it and make the count eight.

8. **Minor. The design-notes section heading no longer fits, and it copies policy numbers.** design-notes.md:120-126 is headed "Why a failed dispatch is not re-dispatched" but describes a re-dispatch. It also hard-codes `hard_waits_s` defaults 600/900/1800, which the policy owns (`subprocess-quota-policy.md:103-105`) and which can drift.
   - Fix: retitle it "Why only the pinned injection is re-dispatched" and link the policy instead of the numbers.

9. **Minor. Repetition.** The text for hosts without a scheduler appears twice (SKILL.md:46-50 and 362-366), and the body is 459 lines, over the ~300-line ideal.
   - Fix: keep the copy at the point of use and turn the top one into a one-line index entry.

I did not run the test suites or the runner `--self-test`. The runner-shape checks were done by reading the source only.

DIGEST 1f5f09727354aee6
CURRENT 104/120
CRITICAL 0 IMPORTANT 4
