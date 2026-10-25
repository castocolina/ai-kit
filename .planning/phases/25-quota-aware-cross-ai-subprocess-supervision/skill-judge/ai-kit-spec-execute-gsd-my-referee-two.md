# ai-kit-spec-execute-gsd — skill-judge report (opencode router-env/my-referee-two, read-only review mode)

Round 5 (evidence round), skill digest `0a5d05b298c07ee8`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

## Round 5: BLOCKED (the runner stopped the lane; no score)

Runner evidence lines:

```text
cross-ai: report status=crash lane=opencode/router-env/my-referee-two route=router attempts=1 cycles=0 first_failure=2026-10-25T04:25:46.794Z last_failure=2026-10-25T04:25:47.898Z stopped=class
AIKIT-XAI status=crash cli=opencode model=router-env/my-referee-two exit=1 cli_rc=1 elapsed=1s out=1148 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```

Upstream messages (OmniRoute, verbatim, trimmed):

```text
Combo has no executable targets
```

## Last completed report from this judge (round 2, an earlier digest; reference only, not this verdict's score)

# Skill Evaluation Report: ai-kit-spec-execute-gsd

**Scope read**: `SKILL.md` (480 lines), `references/dispatch-notes.md` (66 lines), the pointed-at ladder `../ai-kit-spec-review/references/subprocess-quota-policy.md`, plus spot-verification of the claims against the actual code (`cross-ai.mjs`, `ai_kit_spec_gsd/adapter.py`, `cli.py`, `gsd_config.py`, curated-config `ensure-runner`).

**Phase 25 verification** — the runner policy claims all check out against the implementation: one CLI per call with no fallback (`cross-ai.mjs:815` `not_installed: exit 127`, policy §One CLI per call), same-session→new-session rungs, router-lane exit 75 carrying `retry_after_s=`/`cycle=` (`cross-ai.mjs:910`), 4-hour cap → exit 69 (`capS: 14400`, `cross-ai.mjs:69`, policy:48-49), evidence lines (`cross-ai: report` + last-stderr `AIKIT-XAI`, self-test-enforced at `cross-ai.mjs:3322-3324`). SKILL.md:450-456 states the policy and points at the right file (both the `$REVIEW_SPEC_SKILL_DIR` form and the sibling-relative form resolve to a file that exists), and the never-switch rules (SKILL.md:23-27, 451-452, wake prompt 461-465) match the policy's caller contract exactly. The stale internal refs ("D-25", "Task 1 finding", "Phase 22", "design spec §9/§10") were all scrubbed in this diff.

## Summary
- **Total**: 109/120 (91%) — Grade A
- **Pattern**: Tool/Process hybrid (exact scripts + mode decision tree)
- **Knowledge ratio**: E:A:R ≈ 88:10:2
- **Verdict**: An expert-grade adapter skill whose Phase 25 policy pointers are verified-accurate; one real inconsistency remains on the non-CronCreate exit-75 path.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 19 | 20 | Trust model, hook allowlist, adapter-owned keys, workstream paths — near-zero filler; slight triplication of ladder rules |
| D2: Mindset + Procedures | 14 | 15 | "Mindset before writing anything here" (191-202) + procedures Claude could not invent |
| D3: Anti-Pattern Quality | 15 | 15 | 9 NEVER entries, each with the non-obvious why (e.g. 23-27: re-resolve rewrites the hook) |
| D4: Spec Compliance | 14 | 15 | WHAT/WHEN/KEYWORDS all present; run-on density, ~750 chars |
| D5: Progressive Disclosure | 13 | 15 | 480-line body (ideal <300); "read only if" triggers at both dispatch-notes links (242, 437); MANDATORY policy trigger (52) |
| D6: Freedom Calibration | 14 | 15 | Exact scripts and verbatim wake prompt for fragile writes; owner decides judgment calls |
| D7: Pattern Recognition | 9 | 10 | Clear Tool pattern; length is the only deviation |
| D8: Practical Usability | 11 | 15 | Main path airtight; exit-75 secondary path has a dangling reference (finding 1) and two imprecisions |

## Findings

1. **Important** — `SKILL.md:470-473` tells a host without `CronCreate`, at an exit-75 stop, to print "the exact state path (`$RESUME_STATE_PATH`, the `gsd-resume-<project-key>-<phase>.json` **Step 1 wrote**)". In the exit-75 flow Step 1 resolved `cross_ai_hook` and wrote no state file — `write-resumable-state` runs only in Step 1's `quota_exhausted` branch (154-175), which STOPs the wave. By the skill's own variable convention (89-92), `$RESUME_STATE_PATH` was also never captured in this wave. The owner is pointed at a nonexistent file.
 **Fix**: at that stop, re-run the Step 1 write-resumable-state block (all four inputs are in hand: `$CWD`, `$GSD_CONFIG_PATH`, `$PHASE_ID`, `$PHASE_PROMPT_FILE`) before printing the path — which also matches policy line 84 ("write resumable state where the skill already writes it") — and drop "Step 1 wrote".

2. **Minor** — `SKILL.md:474`: "A stop past the 4-hour cap exits 69, **like every other terminal stop**". Policy line 88: an off-router quota stop exits 75 (without `retry_after_s=`) and is equally unscheduled — so not every terminal stop is 69. An agent skimming this line could mis-ruler an off-router 75.
 **Fix**: "…exits 69 and nothing is scheduled; an off-router quota stop exits 75 without `retry_after_s=` and is scheduled nothing either."

3. **Minor** — `SKILL.md:450-451` compresses the ladder to "retries **a transient failure** in the same session, then in new sessions". Per policy (classes 17-24, rungs 26-33, "after rung 2 … exit 75" line 40), quota attempts also consume both rungs before a router lane's exit-75 cycle. The pointer mitigates it, but the one-sentence summary under-states the quota path.
 **Fix**: "retries a failed attempt (transient or quota) in the same session, then in new sessions, on that same CLI and model".

4. **Minor** — `SKILL.md:43-44`: a raw line break splits a sentence mid-clause ("…at `retry_after_s`.\nOn another host…"), exceeding the file's ~100-col wrap. Harmless when rendered, inconsistent on disk.
 **Fix**: rewrap those two lines.

## Top improvements
1. Fix finding 1 (write + print the state file at the exit-75 stop on scheduler-less hosts) — it is the one place the Phase 25 policy is pointed at incorrectly.
2. Tighten findings 2-3 so the inline ladder summary can't be trusted without the policy file.
3. Trim the ~30 lines of rule triplication (ladder rules appear in NEVER, Host-specific, and Step 3) toward the <300-line ideal.

DIGEST 30cdaeaa52318545
CURRENT 109/120
CRITICAL 0 IMPORTANT 1
