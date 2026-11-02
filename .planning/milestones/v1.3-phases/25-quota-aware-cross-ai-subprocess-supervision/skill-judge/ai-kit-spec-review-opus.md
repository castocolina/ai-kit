# ai-kit-spec-review — skill-judge report (native Opus subagent, clean context)

Round 6, skill digest `e85ac2aec5c16f61`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

I scored ai-kit-spec-review at **102/120 (grade B)**, with no Critical findings and one Important one. The skill describes the Phase 25 runner policy correctly. I checked each claim against `cross-ai.mjs` and `ai_kit_spec/` and found no contradiction. It says plainly that the runner runs one CLI per call with no automatic fallback, that it never switches CLI, provider or model, and that it never moves the work to the native session. It also covers the transient ladder (same-session retries, then new sessions), the router cooldown cycles under the 4-hour cap, and the evidence lines on every stop. The rule against re-dispatching a failed lane elsewhere is in the hard-rules table at SKILL.md:475.

Everything was read-only. The one command I ran was an in-memory `node -e` that read the pattern table out of `cross-ai.mjs`. I did not run the self-test or a live dispatch.

| Dimension | Score | Max | Note |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Project-specific procedures and landmines (escaped `\` before `#` truncating the redirect, report size is not completion, bare `mktemp`); verbose rationale prose in places |
| D2 Mindset + Procedures | 13 | 15 | "Before X, ask yourself" prompts at Steps 0.5, 0.7, 3 and 5, plus procedures the model could not know |
| D3 Anti-Patterns | 12 | 15 | The NEVER block has only 2 items; the hard-rules table has reasons; many landmines are scattered in the prose |
| D4 Spec / Description | 14 | 15 | Says what it does, when to use it, and gives trigger keywords |
| D5 Progressive Disclosure | 12 | 15 | Good MANDATORY and "Do NOT load" triggers; but SKILL.md is 490 lines and the 384-line dispatch reference must be read in full on every run, even with `--no-cross-ai` |
| D6 Freedom Calibration | 14 | 15 | Fixed commands for the fragile dispatch, room for judgment in routing and the final message |
| D7 Pattern | 8 | 10 | Process pattern, at about 2.5x the typical length |
| D8 Usability | 12 | 15 | Wide edge-case coverage; small gaps in the pending-lane edge cases, policy wording and the diagram |

**Findings**

1. **Important. A router lane that is out of quota at probe time is switched away before dispatch, so the Phase 25 cooldown cycles never apply to it.**
   - Evidence: SKILL.md:157-165 says any failed probe marks the entry unavailable and the walk moves to the next entry, which may be another provider or the session default. `quota.py:215-217` counts an entry as available only when the probe reports no reason. A confirmed router lane's quota stop (exit 75 with `retry_after_s=`) maps to the reason `quota` (`error_classifier.py`, `STATUS_TO_REASON`), so it is marked unavailable. The cooldown machinery in `cross-ai.mjs:2493-2501` is therefore reached only when quota runs out after a passing probe.
   - This is the open owner item A1 (`25-VERIFICATION.md:87-89`). The skill does disclose the walk, but it never says that the walk overrides the router-cycle policy in exactly the case that policy exists for.
   - Fix: add one sentence to Step 0.7 naming this case and pointing to A1. Or, if the owner rules for it, have `probe-quota` treat a probe's router exit 75 with `retry_after_s=` as "pending, keep the lane" instead of unavailable.

2. **Minor. Each probe of a router lane that hits quota leaves a cycle-state file behind that is never cleaned up.**
   - Evidence: `quota.py:260` runs each probe in a fresh `mkdtemp` directory. The runner keys the state file on that directory (`cross-ai.mjs:1868-1873`) and writes it on a quota stop (`cross-ai.mjs:2477-2484`). The key's directory is deleted afterwards, so the file is never read or removed.
   - Fix: add `"XDG_STATE_HOME": cwd` to the probe environment in `quota.py:234`, next to `GIT_CEILING_DIRECTORIES`.

3. **Minor. The timeout wording in the policy file is slightly wrong.**
   - Evidence: `subprocess-quota-policy.md:20-21` says that with `attemptTimeoutS` at 0 "the attempt uses the whole deadline". In fact `attemptCapMs` keeps 60 s in reserve (`cross-ai.mjs:2347-2350`). The outcome is still a `timeout` stop (exit 124), because `ladderNext` cannot fit another rung (`cross-ai.mjs:1815-1816`).
   - Fix: write "uses the deadline minus a 60 s reserve, which no rung can fit".

4. **Minor. The policy describes the dirty-tree gate in exec-mode terms, but this skill runs reviews.**
   - Evidence: `subprocess-quota-policy.md:33-34`. The rung-2 gate applies only in exec mode (`cross-ai.mjs:2663`). In review mode any tree change between attempts is a `contract_violation` (`cross-ai.mjs:2643-2657`).
   - Fix: add "Review mode: any tree change stops as `contract_violation`."

5. **Minor. The policy says a cooldown exit happens only after rung 2, but a deadline stop after a quota hit also produces one.**
   - Evidence: `subprocess-quota-policy.md:41`. A deadline stop after a quota hit also exits 75 with `retry_after_s=` (`cross-ai.mjs:2648-2651`, through `cycleStop`).
   - Fix: write "after rung 2, or when the deadline ends the ladder after a quota hit".

6. **Minor. The order of reporting and acting differs between the policy and the skill.**
   - Evidence: the policy (`subprocess-quota-policy.md:85`) says to print the `AIKIT-XAI` and `cross-ai: report` lines before acting. SKILL.md:343-350 schedules the re-invoke first and quotes the lines only in Step 5 (SKILL.md:450).
   - Fix: in the pending-lane paragraph, quote both lines before scheduling.

7. **Minor. On resume, a failed lane's report is not deleted when its sibling is still pending.**
   - Evidence: in `cross-ai-dispatch.md:310-317`, the "sibling pending, record and end" branch comes before "anything else: delete the report". This still fails safe, since the runner writes stdout only on success, but it contradicts the delete-before-merge rule.
   - Fix: delete a non-zero, non-75 report before checking the sibling.

8. **Minor. The Step 5 router-quota message assumes there is a sibling lane.**
   - Evidence: the row at SKILL.md:450 says "Its sibling lane is merged now as single mode". Step 2 (SKILL.md:393) covers the one-reviewer case, where there is no sibling.
   - Fix: add the variant "(no sibling: nothing merged; this invocation ends)".

9. **Minor. The loop diagram does not show the Phase 25 paths.**
   - Evidence: `references/loop-diagram.md:9-68` has no pending-lane branch and no Resume entry. The repo's own instructions treat a stale diagram as a defect.
   - Fix: add a "pending router lane" path that skips Step 3 and goes to Surface, and a Resume path into the merge step.

10. **Minor. Token cost.**
    - Evidence: SKILL.md:153 requires reading all of `cross-ai-dispatch.md` even with `--no-cross-ai`, though only points 0-2 apply then. Part of `subprocess-quota-policy.md` is for GSD and maintainers, not this skill: the CONFIG knobs (lines 71-81), the unverified pattern ids (lines 103-107) and the instruction-file block (lines 109-119).
    - Fix: with `--no-cross-ai`, make only points 0-2 mandatory. Mark those three policy sections "Do NOT load for spec-review".

Not checked: `apply-findings.md` and `routing-table.md` beyond a keyword scan, and the earlier judge reports' individual findings.

DIGEST e85ac2aec5c16f61
CURRENT 102/120
CRITICAL 0 IMPORTANT 1
