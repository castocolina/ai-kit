Judge: opus
Reviewed-sha256: 4c59f5c4841437e80d5f593ecdf95ef8d2cee6209aa8005901a69ff1db1a2697
Lane: native subagent completed
Score: 99
Critical: 0
Important: 3

# Skill Evaluation Report: ai-kit-cross-ai

**Summary**
- **Score:** 99/120, grade B.
- **Pattern:** a Process/Tool hybrid. SKILL.md is 168 lines and there are two references, 180 and 86 lines.
- **Knowledge ratio (Expert:Activation:Redundant):** about 75:15:10.
- **Verdict:** The skill describes the Phase 25.1 runner accurately. I checked it against `skills/ai-kit-spec-review/references/cross-ai.mjs` template 8, and these all match:
  - the exit table (cross-ai.mjs:1160-1178);
  - one runtime per call, with `--prefer` running only its first entry (4354-4355, 4432);
  - the soft ladder defaults and jitter (77-93, 3132-3138);
  - the 14400 s cap that cannot be raised (3026-3074);
  - the stopped-lane refusal (3929);
  - the copilot argv prompt (1442);
  - the self-test case names (6046, 6439, 6587).

  No passage tells a caller to switch harness, provider or model. SKILL.md:33-35, 141, 146-148 and policy:20-21, 129-131 all forbid it. Sibling skills point to this skill and do not copy its rules.

**Dimension scores**

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Dense, runner-specific facts. The scratch-dir and argv rules repeat. |
| D2 Mindset + Procedures | 12 | 15 | Strong procedures for launch, read, hard tier and GSD. Little guidance on how to judge cases it doesn't list. |
| D3 Anti-Patterns | 12 | 15 | Good "never switch" and "never answer skip" rules with reasons. Some pitfalls give no reason (kill by PID, file mode). |
| D4 Spec / Description | 12 | 15 | Says what and when, but lacks the failure keywords that would trigger it. The body's "When to use" repeats the description. |
| D5 Progressive Disclosure | 13 | 15 | MANDATORY trigger for launch-and-wait. The policy reference has no trigger in the workflow and no "Do NOT load" note. |
| D6 Freedom Calibration | 13 | 15 | Low freedom on fragile steps (one wait, same lane, no switch). That fits. |
| D7 Pattern | 8 | 10 | Clear numbered process. The reference doubles as a tool spec. |
| D8 Practical Usability | 12 | 15 | Missing decisions for GSD prompts after non-hard-tier exits, for having no CronCreate, and for scratch dirs in other projects. |

**Findings**

1. **Important: the scratch-dir rule is too loose, and the example can break review lanes in other projects.** SKILL.md:44-46 and launch-and-wait.md:7-9 say the lane directory may be "a gitignored one". The examples use `tmp/lane-…` (SKILL.md:51, launch-and-wait.md:27, 83).
   - The runner fingerprints every ignored file by its file metadata (mode, size, timestamps). It skips only files inside a directory that is ignored as a whole (cross-ai.mjs:3574-3588).
   - `lane.err` grows during the run, because heartbeats go to stderr. If it sits in an untracked or partly ignored directory, a review lane stops with `contract_violation tree=dirty`.
   - `tmp/` is ignored in ai-kit, but not necessarily in a target project.
   - **Fix:** use `L=$(mktemp -d)` in the examples, or require "a directory git ignores as a whole (`git check-ignore -q tmp/`)".

2. **Important: the GSD answer rule in section 7 has no condition.** SKILL.md:139 says "When GSD asks retry, skip or abort: wait `retry_after_s`, then answer retry."
   - Exits 1, 2, 69 (`stopped=class`), 124, 127 and a bare 75 carry no `retry_after_s`. For those the section gives no answer, so an agent may answer retry.
   - **Fix:** "Answer retry only after an exit 75 that carries `retry_after_s=`, once that wait has passed. On every other non-zero exit, give the section 6 notice and answer abort."

3. **Important: the description lacks the keywords that would trigger it on a failure.** SKILL.md:3-9 never mentions:
   - `cross-ai.mjs` or `AIKIT-XAI`;
   - quota, 429, rate limit, `retry_after_s`, or exit 75/69;
   - the runtime names pi, opencode, codex, cursor and copilot.

   An agent that hits a quota error from a lane may never load this skill. **Fix:** add those terms. Drop the body section at SKILL.md:20-24, which repeats the description.

4. **Minor: no fallback when Claude Code has no CronCreate.** SKILL.md:133-135 and launch-and-wait.md:45-46 ("No other wake exists") assume CronCreate is present. Subagent and SDK sessions may not have it; this judge's own tool list does not include it. **Fix:** "If CronCreate is unavailable, use the print-and-stop path."

5. **Minor: the `stopped=` values and the causes of a bare 75 are not documented.**
   - The runner emits `stopped=` as class, dirty-tree, rungs, deadline, cap or hard-waits (cross-ai.mjs:3963, 4093, 4232, 4011-4012).
   - A bare 75 comes from the dirty-tree gate (4228-4233) or from a state file it cannot write (3993-3996).
   - SKILL.md:100 and 124 name only some of these. **Fix:** add a one-line legend.

6. **Minor: the argv warning is confusing.** SKILL.md:40-42 and 152-153 warn against putting the prompt on argv. The runner has no argv-prompt option; for copilot the runner itself moves stdin onto argv (cross-ai.mjs:1438-1443). **Fix:** "The prompt always goes on stdin. For copilot the runner passes it on argv, where it shows in the process table."

7. **Minor: repeated text.** The scratch-dir and tree-dirty rule appears at SKILL.md:44-46, 63-65 and 156-157, and again at launch-and-wait.md:7-9. **Fix:** keep it once in section 2.

8. **Minor: the example state path comes from the self-test.** SKILL.md:130 shows a self-test temp path (`/tmp/xai-st-…/home-<case>/.local/state/<case>/…`). That layout is the test harness's, not the real one, which is `${XDG_STATE_HOME:-~/.local/state}/ai-kit/spec/cycles/<root-hash>/<lane>.json` (cross-ai.mjs:3225-3251). **Fix:** replace the path with that placeholder shape.

9. **Minor: planning decision ids in a portable reference.** subprocess-quota-policy.md:47 (D-10), 76 (D-02) and 84 (D-03) cite decision ids that a reader outside ai-kit cannot look up. **Fix:** drop them.

10. **Minor: no loading trigger for the policy reference.** SKILL.md:16-18 and 163-166 only list `subprocess-quota-policy.md`. **Fix:** add "Read it when you configure `cross_ai_retry`, add an overlay row, or interpret `route=`/`rule=`. A plain launch-and-read does not need it."

11. **Minor: the copilot env claim is narrower than the code.** policy:161 says "Copilot review … drops `COPILOT_ALLOW_ALL`". The runner clears it in both modes (cross-ai.mjs:1447). **Fix:** "Copilot never passes on `COPILOT_ALLOW_ALL`."

I did not run `--self-test`, and I did not check gsd-core's "skip runs on the main executor" claim against gsd-core source. Only cursor's `[effort=…]` model format was checked; the codex and claude formats were not.

DIGEST 4c59f5c4841437e8
CURRENT 99/120
CRITICAL 0 IMPORTANT 3
