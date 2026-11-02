# ai-kit-spec-execute-superpowers — skill-judge report (native Opus subagent, clean context)

Round 6, skill digest `9fa91a3b0024ebf5`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

**Skill-judge report: ai-kit-spec-execute-superpowers**

**Score: 101/120 (84%, grade B).** No Critical findings. The Phase 25 policy is described correctly, and its main claims hold against the code. Three Important findings below; all are wording and layout, not wrong behavior.

**Scope.** I read the full rubric (`~/.claude/skills/skill-judge/SKILL.md`), then `SKILL.md` (461 lines), `references/escalation.md`, `references/state-management.md`, `references/design-notes.md`, the linked `skills/ai-kit-spec-review/references/subprocess-quota-policy.md`, and `git diff 11ac3eb..HEAD`. I checked the claims against `ai_kit_spec_superpowers/{cli,dispatch_injection}.py`, `ai_kit_spec/{execute_dispatch,runner_dispatch,error_classifier}.py` and `cross-ai.mjs`.

**Claims that match the code:**
- **One CLI per call:** `runner_flags` passes only `--prefer <runtime>`.
- **Router confirmation:** a lane counts as router only when the model catalog's `fallback_quota` is confirmed. `resolve_route` then adds `--route-<cli> router`.
- **Where the tokens live:** `retry_after_s` and `cycle` exist only inside `status`, which is the parsed `AIKIT-XAI` line (`execute_dispatch.py:150-151`).
- **Exit codes:** exit 75 and exit 69 both classify as `"quota"`. A cooldown that would run past the cap returns exit 69 (`cross-ai.mjs:2494-2500`). A re-entry before the due time returns exit 75 with the remaining wait (`2443-2449`), which the "75 plus both tokens" rule handles.
- **Evidence lines:** the stderr relay passes every line through (`runner_dispatch.py:262-271`), so they do land in `$DISPATCH_BASE.err`.
- **Task digest:** it hashes only `<objective>` (`cross-ai.mjs:1863`), and the guidance text injected ahead of the prompt has no `<objective>` tag.
- **Writes outside the task files:** SDD's `.superpowers/sdd/` directory is ignored entirely, so writing the report and prompt files there does not trip the dirty-tree gate.
- **Exit status:** `dispatch-task` exits 0 even when the runner fails; only a refused candidate exits non-zero, with no JSON.

### Dimension scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 16 | 20 | Almost all content is project-specific (the three exclusion sets, write-then-append, status read from stdout, digest and `<files>` rules). Some content is repeated (exec confinement, the round 4–5 rationale and "two current rules" appear in both SKILL.md and the references). |
| D2 Mindset + Procedures | 13 | 15 | "Before touching any exclusion-set variable, ask…" is a real thinking frame, plus procedures an agent could not invent. |
| D3 Anti-Patterns | 14 | 15 | The NEVER index gives a non-obvious reason per item and points to where each is used. |
| D4 Spec / Description | 13 | 15 | Strong WHAT, and the WHEN is routed through ai-kit-spec-execute. No user-phrased triggers; no mention of external CLI dispatch or the quota/stop behavior. |
| D5 Progressive Disclosure | 12 | 15 | MANDATORY triggers sit inside the workflow, and design-notes has a "read only when" gate. But SKILL.md is 461 lines, and Step 3 alone is about 260. |
| D6 Freedom Calibration | 13 | 15 | Fragile state work is exact bash. Prompt composition (the `<objective>`/`<files>` blocks, the WRITE/APPEND sentence) is prose with no template, even though the session reuse depends on it byte for byte. |
| D7 Pattern | 8 | 10 | A Process/Tool hybrid, clearly structured. |
| D8 Usability | 12 | 15 | Edge cases are well covered. The ordering and ambiguity issues below cut into it. |

### Findings

**1. Important: the skill contradicts itself on whether escalation is settled.** `SKILL.md:415-417` calls pre-dispatch selection and the rounds 4–5 escalation "the shipped behavior, still awaiting the owner's confirmation". `design-notes.md:138-139` says "The executable steps state them as current behavior, not as open questions". This is the exact rule the owner's "never switch model on its own" constraint touches. An agent may stop to ask, or may refuse the round-4 bump. Note that `escalation.md`'s re-resolution can also land on a `native` session-default entry (`resolve-injection` can return `native`), which is a hand-off to the native session.
- **Fix:** in SKILL.md, keep one present-tense sentence: "Pre-dispatch selection along `policy.ladder` (Step 2's pick, the round 4–5 bump) is authorized; nothing after a failed dispatch is." Move the "awaiting confirmation" history to design-notes only. In `escalation.md`, say explicitly whether a `native` bump is allowed.

**2. Important: in the quota branch, the code appears before the "relay evidence first" rule.** `SKILL.md:322-334` shows the fold block (`WAVE_TRIED_JSON`, `WAVE_REASONS_JSON`, `EXCLUDED_KEYS_JSON`) first. Only at `:336-341` does it say to relay the `cross-ai: report` and `AIKIT-XAI` lines "before reading any token or writing any state, then run the fold block above". An agent reading top-down runs the fold first, which breaks the policy's "print … verbatim, before acting" (`subprocess-quota-policy.md:85`), the core Phase 25 rule.
- **Fix:** put the relay as point 1, then the fold block as point 2, in reading order.

**3. Important: SKILL.md is too heavy; the quota-wake flow belongs in a reference.** `SKILL.md:322-403` (the fold, token reads, schedule-or-stop, the wake prompt, the resume note) is about 80 lines that only the rare mid-dispatch quota stop needs. That pushes the file to 461 lines, near the 500-line limit.
- **Fix:** move it to `references/quota-wake.md`, behind "MANDATORY when `CLASSIFICATION == "quota"`: read in full". Add a "Do NOT load on `ok` or `real_error`" line. Keep a 3-line stub in Step 3.

**4. Minor: the NEVER item names only `cycle=`.** `SKILL.md:42-43` says "a confirmed-router exit 75 carrying `cycle=`", but `:362-363` requires both `RETRY_AFTER_S` and `CYCLE`. An unwritable state file or a cap stop yields `cycle` without `retry_after_s` (`cross-ai.mjs:2499`).
- **Fix:** change it to "carrying both `retry_after_s=` and `cycle=`".

**5. Minor: the owner-resume guidance after the cap is incomplete.** `SKILL.md:371-374` says an unscheduled stop leads to an owner re-invoke that re-enters Step 2. After an exit 69, the stuck key carries a `"quota"` reason, so `resume-exclusions` drops it and Step 2 can pick it again. The runner then refuses it with an immediate exit 69 until `last_attempt_at` is more than 4 hours old (`cross-ai.mjs:2433-2441`).
- **Fix:** on exit 69, also report "this lane cannot run again until about 4 h after its last attempt; an earlier re-invoke re-resolves along the ladder and may pick a different pair".

**6. Minor: it is unclear whether the round 4–5 floor applies again on a resume.** `SKILL.md:260-262` says to increment `$FIX_ROUND` "(not on resume), then apply the Rounds 4–5 rule", and `:443` says the rule applies "after the increment". After the escalation quota stop (`escalation.md:88-93`), a resumed Step 2 runs without the floor and can pick the stuck or a weaker key. The example at `escalation.md:36-38` assumes the floor is applied again.
- **Fix:** add "On resume with `$FIX_ROUND >= 4`, apply the floor before dispatch, with no increment."

**7. Minor: "run backgrounded" has no portable form.** `SKILL.md:269-279` requires running the dispatch in the background, but the block is foreground syntax that relies on Claude Code's `run_in_background`.
- **Fix:** give a host-neutral form, e.g. `( python3 … ; echo "$?" > "$DISPATCH_BASE.exit" ) &`, plus a polling note for hosts with no completion notice.

**8. Minor: project-internal references leak into a portable skill.** "assumption A1 in the Phase 25 owner captures" (`design-notes.md:131`), "before Phase 25" (`:88`) and "curated-config's runner floor" (`SKILL.md:268`) mean nothing to an agent working in another repo.
- **Fix:** state the facts directly (whole-call budget is 1800 s, the same as the runner's default `outerTimeoutS`) and drop the planning-artifact names.

**9. Minor: the description omits external dispatch and failure behavior.** At `SKILL.md:3` there is no mention of cross-AI or external CLI dispatch, the runner, or "stops on failure, never switches model". There are also no user-phrased triggers such as "run my superpowers plan on codex/opencode".
- **Fix:** add one clause naming both, keeping the description under about 1,024 characters.

**Not checked:** I did not run `make test` or the runner's `--self-test`. I did not check whether `CronCreate` exists or fires on any host. The real CLIs' router behavior, and whether Codex's workspace-write sandbox allows writes in `.git`, stay unverified, as the skill itself already marks them.

DIGEST 9fa91a3b0024ebf5
CURRENT 101/120
CRITICAL 0 IMPORTANT 3
