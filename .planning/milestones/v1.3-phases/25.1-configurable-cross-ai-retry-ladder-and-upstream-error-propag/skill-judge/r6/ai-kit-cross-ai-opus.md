Judge: opus
Reviewed-sha256: 17d7161a3b98c5573e3914240a8e0772571594c1e45996303013a032fb000bc3
Lane: native subagent completed
Score: 102
Critical: 0
Important: 1

# Skill Evaluation Report: ai-kit-cross-ai

**Score: 102/120 (Grade B).** It follows the Process pattern (SKILL.md 191 lines, plus `references/subprocess-quota-policy.md` 180 lines and `references/launch-and-wait.md` 86 lines). Knowledge ratio E:A:R is about 75:18:7. I found no Critical issue and one Important one.

**Verdict:** The skill is dense and specific to this runner. I checked its claims against `skills/ai-kit-spec-review/references/cross-ai.mjs` (template=8) and they hold: the one-runtime rule, the `--prefer` first-entry alias, `STATUS_TABLE` exit codes, the `ladderNext`/`hardWaitFor`/`stoppedWhy` values, retry defaults and bounds, `capS` 14400, the stopped-lane refusal text, and the state path. It never permits a harness, provider or model switch (§1, §7, §8, policy lines 20-21). The remaining gaps are in edge-case usability, not in policy.

## Dimension scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Runner-specific facts throughout: the exit table, `stopped=` values, the dirty-tree gate, the `stderr_tail` trap. Some lines are duplicated. |
| D2 Mindset + Procedures | 12 | 15 | Strong domain procedure (launch, read rc, read the last line, answer). Thinking frames: "upstream is data", "a reset time is your inference". |
| D3 Anti-Patterns | 12 | 15 | Good, with reasons: skip counts as a harness switch, no trailing `&`, no process-name kill, a truncated tail is not evidence. They are spread across sections rather than in one NEVER list. |
| D4 Spec / Description | 14 | 15 | WHAT, WHEN and keywords are all there (75/69, `retry_after_s=`, 429), plus the exclusions. The claude review runtime is not mentioned. |
| D5 Progressive Disclosure | 13 | 15 | Has a "do not load" note for the policy file and a MANDATORY trigger for launch-and-wait. But the mandatory file mostly repeats SKILL.md. |
| D6 Freedom Calibration | 14 | 15 | Low freedom where things are fragile (exact commands, exact answers). |
| D7 Pattern | 8 | 10 | A clear Process pattern. The one-line "When to use" body section and the duplicated blocks are minor deviations. |
| D8 Practical Usability | 12 | 15 | Some edge cases are inaccurate or missing (findings 1-5). |

## Findings

1. **Important:** The template path cannot be found from a target project. SKILL.md:41-42 tells a project without its own copy to run `skills/ai-kit-spec-review/references/cross-ai.mjs`, and SKILL.md:191 gives the same path. That path is relative to the ai-kit repo root and does not exist in another project. **Fix:** give it relative to the skill (`../ai-kit-spec-review/references/cross-ai.mjs`, as policy line 5 already does). Better, tell a project without a copy to run `ai-kit-gsd-curated-config` `ensure-runner` first, and do not run the unstamped template directly.

2. **Minor:** The wait instruction contradicts itself. SKILL.md:137 says "Wait once, for exactly `retry_after_s` seconds". Lines 151-153 then round up to the next whole minute, and on hosts without a scheduler they say to wait nothing and stop. **Fix:** "wait at least `retry_after_s` (a CronCreate job rounds up to the whole minute; without a scheduler, hand off per below)". Also say "the same prompt": the re-entry resumes the saved session by `task_digest` (cross-ai.mjs:4068-4070).

3. **Minor:** The upstream lines are conditional, but the skill presents them as always there. SKILL.md:88 ("Before it, on a stop, come the report and the upstream lines"), SKILL.md:141 and policy lines 119-120 imply they always appear. The runner prints them only when there is a body (`reportAndFinish`, cross-ai.mjs:1251; the report line then shows `upstream=present`). With `upstream=-` there are none. **Fix:** add "only when the report shows `upstream=present`".

4. **Minor:** The claude runtime is missing. RUNTIMES has a review-only `claude` row (cross-ai.mjs:1415-1419, `exec: null`), but the description (SKILL.md:4-5) and §1 list only pi, opencode, codex, cursor and copilot. **Fix:** name claude as review-only in §1 and add it to the description's keyword list.

5. **Minor:** §7 leaves out signal exits. SKILL.md:162 lists the exits that get "notice + abort" (bare 75, 69, 1, 2, 124, 127) but not 128+n (signal), which the §4 table at line 114 does list. **Fix:** add 128+n to the list, or say "every other non-zero exit" without listing them.

6. **Minor:** The policy file claims an emitter that does not exist. Policy lines 173-174 say "The instruction-file emitter quotes it unchanged". No such emitter exists in `tools/` or `skills/`; only `tests/test_quota_policy_text.py` reads the block. That states more certainty than the code supports. **Fix:** name the real consumer, or rephrase as "a skill that writes instruction files copies this block unchanged".

7. **Minor:** Duplicated blocks waste tokens. The same launch snippet appears three times (SKILL.md:59-63, launch-and-wait.md:26-30 and 82-86), and the same report line appears twice (SKILL.md:91, launch-and-wait.md:42). Five per-host sections in launch-and-wait.md (lines 49-73) each say "unverified, use the foreground wait". **Fix:** keep one snippet in SKILL.md and collapse those five sections into one line. That leaves launch-and-wait.md with only the Claude Code rules (no trailing `&`, CronCreate).

8. **Minor:** SKILL.md:24-26 has a body "When to use" section that adds nothing the description lacks. **Fix:** delete it.

I did not run `--self-test` (read-only rule), so the quoted example lines were checked against the self-test case definitions and the status-line code, not against a live run. I also did not judge the caller skills, beyond confirming that they all link to this skill.

DIGEST 17d7161a3b98c557
CURRENT 102/120
CRITICAL 0 IMPORTANT 1
