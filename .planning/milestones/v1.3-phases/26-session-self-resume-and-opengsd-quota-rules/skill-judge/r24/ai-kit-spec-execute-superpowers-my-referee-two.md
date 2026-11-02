Judge: my-referee-two
Reviewed-sha256: ac7532f867529b8cb1e0e8a420a2931430aafc3e2abe3cf2a0d89beb38d8e86b
Lane: AIKIT-XAI status=ok cli=pi model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=75s out=6913 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 86
Critical: 1
Important: 2

# Skill Evaluation Report: ai-kit-spec-execute-superpowers

## Summary
- **Total Score**: 86/120 (72%)
- **Grade**: C
- **Pattern**: Process (phased workflow with checkpoints), overloaded toward a Tool dump
- **Knowledge Ratio**: E:A:R ≈ 78:14:8
- **Verdict**: Genuine adapter knowledge with a correct decision tree, but one escalation path mislabels a permanent failure as recoverable quota and the body is too large to follow reliably.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 17 | 20 | Ladder keys vs runtime ids, pin-vs-re-resolve, write-once report, stdout status: real domain knowledge |
| D2: Mindset vs Mechanics | 12 | 15 | Strong "ask permanent vs same-wave" framing, then mostly exact bash |
| D3: Anti-Pattern Quality | 13 | 15 | NEVER list is specific and each rule has a non-obvious why |
| D4: Specification Compliance | 14 | 15 | name valid; description has WHAT, WHEN, keywords, and an explicit out-of-scope |
| D5: Progressive Disclosure | 8 | 15 | Triggers are mandatory and conditional, but SKILL.md is ~289 lines and the loaded set far exceeds 500 |
| D6: Freedom Calibration | 12 | 15 | Low freedom fits a fragile state machine; a few blocks still require hand assembly |
| D7: Pattern Recognition | 7 | 10 | Process pattern, but volume and cross-file pointers drift toward a dump |
| D8: Practical Usability | 3 | 15 | One wrong recovery path; quota wake and fix-round entry are contradictory |

## Critical Issues

1. A rounds 4–5 floor that exhausts only on non-quota reasons is told to write resumable state and report that a more-capable candidate is temporarily out of quota. The shim sets `any_quota_recoverable` from every eligible exclusion, including keys already dropped as permanent (`skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:130-145`). Following the reference locks those keys out and tells the owner to wait.

## Top 3 Improvements

1. In `references/escalation.md`, gate the recoverable branch on a `"quota"` reason among keys that are inside `ladder_keys` and outside the floor, not on the raw boolean.
2. Make the quota-wake prompt name `PLAN_FILE` and `TASK_N`, and state one rule for when a later fix round increments `$FIX_ROUND`.
3. Move Step 2 and Step 3 bash into the references they already require, and add a "Do NOT load" line per mode so a task does not pull the whole package.

## Detailed Analysis

Claims checked and held: shim flags (`cli.py:388-466`); `quota_exhausted` / `no_candidate` shapes (`cli.py:136-147`, `cli.py:193-196`); unverified still dispatches (`dispatch_injection.py:295-307`); status from stdout only (`dispatch_injection.py:406-419`); classify tokens (`dispatch_injection.py:422-459`); exit 2 for `purpose = "execute"` custom/grok/claude (`execute_selection.py:78-108`); untrusted prefix (`config_io.py:410`); Node absent → `dispatch_unavailable` (`runner_dispatch.py:66`, `runner_dispatch.py:589-591`); Node 24 citation (`.planning/phases/18.1-one-runtime-model/18.1-RESEARCH.md:231`); codex sandbox (`runner_dispatch.py:40`, `runner_dispatch.py:214-215`); `resolve_timeout_tiers` is review-side (`config_io.py:643`); hard-tier 4-hour cap (`skills/ai-kit-cross-ai/references/subprocess-quota-policy.md:90-107`); cross-ai sections 6 and 8 exist (`skills/ai-kit-cross-ai/SKILL.md:128`, `:168`); session-wake `arm`/`done` and `companion:` (`ai_kit_session_wake/cli.py:72-90`, `arm.py:521`).

D1–D4 are strong. D5 loses points because Step 2 always loads state-management, Step 3 then loads dispatch-external-cli, escalation, resolution-stops and quota-wake, and there is no "Do NOT load" for the files a given mode does not need. D8 is the failure: the agent cannot trust the escalation stop or the wake prompt.

## Findings

1. Critical — `references/escalation.md:112-116`. On `any_quota_recoverable == True` it says a more-capable candidate is only temporarily out of quota and tells the agent to merge `tried`/`reasons`, run `resume-exclusions`, and write resumable state. `cli.py:130-145` computes that flag over `merged_tried - escalation_exclude`, and `merged_tried` is `tried | exclude` (`cli.py:133`), so a permanent `"quota"` key already in `$PRIOR_EXCLUDED_KEYS_JSON` and still inside `ladder_keys` but outside the floor makes the flag true even when every key the floor could pick failed for `"auth"` or `"configuration"`. `resume-exclusions` (`dispatch_injection.py:160-162`) then persists those non-quota keys. The owner is told to wait for a candidate the floor cannot select. Fix: treat the stop as recoverable only when some key in `ladder_keys`, not in `$ESCALATION_EXCLUDE_JSON` and not already permanent, has reason `"quota"`; otherwise use the `False` branch.

2. Important — `references/quota-wake.md:13-18`. Step 1 binds `CWD` and `QUOTA_PATH` but not `PLAN_FILE` or `TASK_N`. Step 2 says both "are not among the substituted values" and then "fill its six placeholder lines from the step 1 and step 2 values of the same names." The task-paths block (`SKILL.md:107-108`) exits if `PLAN_FILE` or `TASK_N` is empty or still a placeholder, and that block is what creates `$RESUME_STATE_PATH` and `$SCALARS`. A woken agent that follows step 1 literally aborts before Restore. Fix: add `PLAN_FILE` and `TASK_N` to the fourteen substitutions (sixteen), and delete the "not among the substituted values" sentence.

3. Important — `SKILL.md:216-220` conflicts with `references/quota-wake.md:28-30`. Step 3 says every fix round starts by incrementing `$FIX_ROUND` and copying `$LAST_DISPATCHED_KEY` into the anchor, "new rounds only, never on a resume." The wake prompt says that after an ok re-dispatch, "a later fix round of this task starts at Step 3 with the restored pin." Step 3's increment runs before the pin exception is stated, so the agent can bump the round and move the anchor on a pinned pair that was not a new fix round. Fix: one sentence at `SKILL.md:216`: the increment runs only when subagent-driven-development has opened a new fix round; a wake or owner re-invoke of a pinned injection dispatches it and leaves both scalars unchanged.

4. Minor — `SKILL.md:274-276`. The Node 24 / `@opengsd/gsd-core` 1.17.0 engines claim matches `.planning/phases/18.1-one-runtime-model/18.1-RESEARCH.md:231` and the sentence already says it is not declared in this tree. The runner fails closed only when `node` is absent (`runner_dispatch.py:589-591`). No change required beyond keeping that caveat.

5. Minor — `references/design-notes.md:80-86`. `timeout_tiers` not carried by `assemble_candidates` (`dispatch_injection.py:183-194`) and `resolve_timeout_tiers` living on the review side (`config_io.py:643-652`) both check out. The note is accurate; it is reference-only and should stay behind the existing "do not load unless a rule looks arbitrary" trigger.
