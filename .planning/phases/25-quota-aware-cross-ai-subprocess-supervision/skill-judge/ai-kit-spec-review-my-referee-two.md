# ai-kit-spec-review — skill-judge report (opencode router-env/my-referee-two, read-only review mode)

Round 5 (evidence round), skill digest `458a2dd3c1b61497`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

## Round 5: BLOCKED (the runner stopped the lane; no score)

Runner evidence lines:

```text
cross-ai: report status=crash lane=opencode/router-env/my-referee-two route=router attempts=1 cycles=0 first_failure=2026-10-25T04:25:46.793Z last_failure=2026-10-25T04:25:47.914Z stopped=class
AIKIT-XAI status=crash cli=opencode model=router-env/my-referee-two exit=1 cli_rc=1 elapsed=1s out=1148 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```

Upstream messages (OmniRoute, verbatim, trimmed):

```text
Combo has no executable targets
```

## Last completed report from this judge (round 2, an earlier digest; reference only, not this verdict's score)

# Skill Evaluation Report: ai-kit-spec-review

## Summary
- **Total Score**: 110/120 (91.7%)
- **Grade**: A — production-ready expert skill
- **Pattern**: Process (phased orchestrator loop) with Navigation + Tool elements
- **Knowledge Ratio**: E:A:R ≈ 85:13:2
- **Verdict**: Near-pure expert knowledge, fail-closed at every seam; the Phase 25 policy (one CLI per call, failure ladder, router cycles under the 4-hour cap, evidence lines, never switch on its own) is described in SKILL.md and `subprocess-quota-policy.md` and matches the actual implementation in `cross-ai.mjs` / `ai_kit_spec/` everywhere I checked.

## Phase 25 verification (code ↔ docs)
- **One CLI per call, no fallback**: `cross-ai.mjs:5957,6034,6048–6052` — first `prefer` entry only, missing → `not_installed` exit 127, "no other CLI runs (no automatic fallback)". Matches `subprocess-quota-policy.md:7–13`.
- **Ladder**: `ladderNext` (`cross-ai.mjs:1784–1810`) — rung 1 same-session (≤3, only when resumable), rung 2 new sessions (≤3, same CLI+model), dirty-tree stop (`2625–2629`); defaults at `69–70,83`. Matches policy rungs §26–33.
- **Router cycles + 4-h cap**: `cycleStop` (`2454–2462`) exits 75 with `retry_after_s=`/`cycle=` when not capped, 69 past cap; cap arithmetic `1799–1807`; XDG state file, task-digest-gated sid reuse (`2465–2477`), pre-due refusal without spawning (`2415–2422`), `stale-state-fresh-start` (`2404–2407`). Matches policy §35–52.
- **Evidence on every stop**: `cross-ai: attempt` (`2356–2362`), `cross-ai: report …` (`2364–2369`), `AIKIT-XAI … action=stop route= rule= pattern= attempts= cycles=` with conditional `retry_after_s=` (`894–916`). SKILL.md:296–317 now redirects stderr to `.err` and orders those lines read — correct.
- **Exit-code contract holds end-to-end**: STATUS_TABLE (`799–819`: quota/transient→75, auth/billing/bad_model→69); `dispatch-reviewer --stdout-only` propagates the runner's real returncode (`cli.py:976–978`); the Python tier loop re-runs **only** on timeout/124 (`runner_dispatch.py:596–608`), so a 75 is never swallowed. Off-router 75 carries no `retry_after_s` (pinned regex `3833–3834`), exactly as SKILL.md:317–321 branches.
- **Never switch on its own**: stated at SKILL.md:328–333 and policy:12–13, and the runner structurally cannot comply otherwise. The probe walk (SKILL.md:157–165) is correctly bounded as owner-ladder pre-selection — matches `cli.py:675–685` + `quota.py:190–191,215–220`. Router confirmation only via `--route-<cli>`/`routerBacked` (`routeOf` 1603–1618; catalog-confirmed `resolve_route` in `runner_dispatch.py:194–226`).

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 18 | 20 | Worktree-derived roots, archetype ceilings, lifecycle scoping, pending-lane lifecycle — all genuinely expert; near-zero redundancy |
| D2: Mindset + Procedures | 14 | 15 | "Ask yourself" prompts at Steps 0.5/0.7/3/5 + exact dispatch contract Claude couldn't invent |
| D3: Anti-Pattern Quality | 14 | 15 | Hard-rules table with non-obvious whys (context contamination, phantom worktree findings); owner rule; "probe walk is not permission to switch" |
| D4: Specification Compliance | 15 | 15 | Description has WHAT/WHEN/trigger keywords incl. named frameworks; valid frontmatter |
| D5: Progressive Disclosure | 13 | 15 | Textbook MANDATORY-triggers + explicit "Do NOT load" (`cross-ai.mjs`, `cli-profiles/`); SKILL.md at 499 lines is at the ceiling and the per-run mandatory read set totals ~1,175 lines |
| D6: Freedom Calibration | 14 | 15 | Verbatim bash and "never render the command yourself" for fragile dispatch; judgment freedom for detection/surfacing |
| D7: Pattern Recognition | 9 | 10 | Masterful Process-pattern orchestrator |
| D8: Practical Usability | 13 | 15 | Decision tables at every branch; code-verified; one resume-fidelity gap and one ambiguous enumeration (below) |

## Findings

**Critical** — none.

**Important**

1. **The pending-lane CronCreate resume cannot reproduce "the identical command" it mandates.** The fenced cron prompt (SKILL.md:350–356) wakes a *fresh* session holding only `RUN_TMP_DIR`, iteration, and reviewer key, and orders it to "Re-run the identical dispatch-reviewer command … (same prompt file, timeout tiers and flags)". But the command's literal form is recorded only in the orchestrator's in-context working notes (cross-ai-dispatch.md:45–51) — never persisted to disk; `--tool-availability-json` (a fresh `detect-tools` output each run, cli.py:71) and the tier resolution are not recoverable byte-identically from `RUN_TMP_DIR`, and the optional `loop.log` (SKILL.md:183) is debug-only and doesn't capture the command. Non-Claude hosts get the literal command printed in the Step 5 row; the Claude Code cron path doesn't. **Fix**: when marking a lane pending (Step 1, point 3), write the exact dispatch command line to `$RUN_TMP_DIR/iter<N>-<key>-cmd.sh` and make the fenced cron prompt reference that file instead of "the identical command".

**Minor**

2. **Self-overlapping enumeration in the pending-lane lifecycle.** SKILL.md:358–361: "Merge the lane only from … the exit 69 the cap turns it into. **Every other nonzero exit, exit 69, auth**, off-router …" — `exit 69` appears in both the merge-source and the delete lists, and "every other nonzero exit" already subsumes the enumerated items. The real discriminator (cap-69 = `AIKIT-XAI status=quota` vs auth/bad_model, which are *also* exit 69 — STATUS_TABLE `cross-ai.mjs:808–812`) is not named at the branch point; a reader keying on exit code alone cannot tell them apart. Both misparses converge on the same failure surface, so impact is low. **Fix**: "…or when its `AIKIT-XAI` line reads `status=quota exit=69` (the cap). Any other stop — auth, bad model, off-router 75 (no `retry_after_s=`), any other nonzero exit — deletes the report, merges as failed, schedules nothing."
3. **"Single reviewer" is a modifier, not an outcome.** SKILL.md:461 lists it as a row among terminal outcomes (Approved/Cap/Failure…), but every single-reviewer run *also* ends in one of those rows; a reader emitting shapes from this table could double-shape the message. **Fix**: move it to a footnote ("in single mode, prefix the relevant row with the reviewer key and report path").

Not checked: the sibling `ai-kit-spec-review-checklist`/`-fixer` skills and framework seed profiles (outside this skill's directory), the ~5,900-line `cross-ai.mjs` self-test suite (constants and stop semantics sampled, not exhaustively read), and no live dispatch was executed — verification is by code reading only.

DIGEST 2a61dfd0ebfc024c
CURRENT 110/120
CRITICAL 0 IMPORTANT 1
