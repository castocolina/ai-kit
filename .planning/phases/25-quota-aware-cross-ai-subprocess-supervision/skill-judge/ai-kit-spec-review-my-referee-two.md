# ai-kit-spec-review — skill-judge report (opencode router-env/my-referee-two, read-only review mode)

Round 6, skill digest `e85ac2aec5c16f61`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

Runner status: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=355s out=485900 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0`

All checks are complete — I verified the docs against the implementation on every load-bearing claim (clamps, exit codes, state-file semantics, `STATUS_TO_REASON`/`_EXIT_FALLBACK` tables, review-only flag, aliases, probe-walk fallback, evidence-line formats, unverified capture ids, anchors). Report below.

# Skill Evaluation Report: ai-kit-spec-review

- **Total**: 111/120 (92.5%) — **Grade A**
- **Pattern**: Process (phased orchestration with checkpoints + navigation to references)
- **Knowledge ratio**: ~E:90 / A:8 / R:2 — nearly pure expert operational knowledge
- **Verdict**: A rigorous, implementation-verified orchestration spec; Phase 25 policy is described and pointed at correctly, with one real coverage gap in the new pending-lane flow.

## Dimension table

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 19 | 20 | Exit-code contracts, ladder semantics, resume files, merge lock, worktree-root derivation — no "what is X" filler anywhere |
| D2 Mindset + Procedures | 15 | 15 | "Ask yourself" frames at Steps 0.5/0.7/3/5 + genuinely non-guessable procedures (argv-as-JSON resume, CronCreate prompt text, fail-closed deletes) |
| D3 Anti-Pattern Quality | 14 | 15 | Hard-rules table with reasons; "a switch hides the stop and reviews with a lane nobody chose" (SKILL.md:475) is expert-grade |
| D4 Specification Compliance | 14 | 15 | Description has WHAT/WHEN/KEYWORDS + explicit trigger phrases; ~700 chars, long but every clause triggers |
| D5 Progressive Disclosure | 14 | 15 | MANDATORY reads at exact workflow points; explicit "Do NOT load" for `cross-ai.mjs` and `cli-profiles/` (SKILL.md:153); SKILL.md at 490/500 lines |
| D6 Freedom Calibration | 14 | 15 | Verbatim bash/prompts where fragile, ask-once judgment where not; unruled probe walk honestly flagged (SKILL.md:163-165) |
| D7 Pattern Recognition | 9 | 10 | Masterful Process application with navigation elements |
| D8 Practical Usability | 12 | 15 | Decision tables per status/exit code, working commands, host-capability fallbacks; deductions for findings 1, 3, 5 |

## Findings

1. **[Important] Two-pending-lanes iteration has no defined branch.** `references/cross-ai-dispatch.md:265-267` says "Merge the sibling now as single mode" when a lane goes pending, but point 1 (`:263`) forbids merging a pending lane — if *both* lanes exit 75 with `retry_after_s=` (realistic: double mode, both entries on the same router-backed provider hitting quota together), the sibling is itself pending and has no report. SKILL.md:393's "no sibling" out is defined as "(one reviewer)", which doesn't cover a 2-reviewer run whose sibling is pending. The resume side handles it correctly (`cross-ai-dispatch.md:310-313` "sibling still pending → record and end" + merge lock), so only the initial invocation's merge/surface is undefined. **Fix**: one sentence in the pending-lane section: "If both lanes are pending, merge nothing — surface the router-quota row for both lanes and end this invocation after scheduling both one-shots."

2. **[Minor] Policy file never acknowledges the pre-dispatch probe walk.** `references/subprocess-quota-policy.md:8-10` ("The rest of the list is the owner's menu, used only when the owner names one") reads as contradicting SKILL.md:157-165, where `probe-quota`+`resolve-reviewers` automatically move to the next configured entry (possibly another provider) before dispatch. Different layers (runner vs resolver — verified: the runner takes only `--prefer`'s first entry, `cross-ai.mjs:23`), but the caller contract should say so. **Fix**: add to "One CLI per call": "The resolver's pre-dispatch probe walk (SKILL.md Step 0.7) is selection, not the runner switching; it is the shipped behavior, owner not yet ruled."

3. **[Minor] Exit-75-without-`retry_after_s=` causes omit the unwritable-state case.** SKILL.md:328-330 and `cross-ai-dispatch.md:248-249` enumerate exactly two causes ("an off-router quota stop, or an exhausted transient ladder"). The runner also emits a bare 75 on a *confirmed router lane* when the cycle state file is unwritable (`cross-ai.mjs:2476-2477` comment, `:2499` `retryAfterS: capped || !stateWritable ? undefined : …`). Behavior is correctly fail-closed and logged (`cross-ai: cycle state unwritable`), but the contract doesn't list it. **Fix**: append "or an unwritable cycle state file on a router lane (see its `cross-ai:` line)" to either enumeration.

4. **[Minor] Re-invoke time diverges between the two docs.** `cross-ai-dispatch.md:289-290` schedules "at `retry_after_s` seconds (at least 60 s, rounded up to the next whole minute)"; `subprocess-quota-policy.md:100` says "exactly one one-shot `CronCreate` at `retry_after_s`" — and `cooldownS` clamps to `0..capS` (`cross-ai.mjs:1784-1787`), so `retry_after_s=0` is reachable. **Fix**: state the ≥60 s cron-granularity floor in the policy file (or cite it from the dispatch doc) so the declared source of truth and the lifecycle doc agree.

5. **[Minor] Merge lock has no lifecycle.** `cross-ai-dispatch.md:312-313` creates `iter<N>-merge.lock` via `mkdir` but nothing ever removes it, and SKILL.md:484-490 (Cleanup) doesn't mention it. A crash between lock acquisition and merge leaves a stale lock that permanently blocks the merge for that `RUN_TMP_DIR`. **Fix**: one line — the lock is removed after the merge, and a resume that finds a lock older than its own dispatch may remove it.

6. **[Minor] Skill-level evals lag the Phase 25 machinery.** `evals/` holds 4 routing/detection scenarios; none exercises the pending-router-lane/resume path, the exit-75 branch table, or the evidence-line quoting rules. (The runner core itself is well covered by `--self-test` — e.g. `router-quota-early-reentry`, `stale-state-fresh-start`, clamps, `router-inferred`.) **Fix**: add `evals/05-router-quota-pending-lane.md`: exit 75 + `route=router` + `retry_after_s=` → sibling merged single-mode, resume files written, one one-shot scheduled, no fixer, router-quota Surface row quoting `iter<N>-<key>.err`.

**Verified accurate (no finding)**: exit-code semantics (75 router-quota w/ `retry_after_s`+`cycle`, bare 75, 69 cap, 127, 124, 2) match `cross-ai.mjs:808-815` and `error_classifier.py`; clamps 0..3 / 10..1800 / 0..14400 / 0..capS match `mjs:1768-1788`; state file key = checkout+lane+model, mode 0600, atomic rename, task digest from `<objective>` (`mjs:1863-1901`); `router-inferred` gets no cycles (`mjs:122-123`); early re-entry refused pre-dispatch (`mjs:2443-2452`); `STATUS_TO_REASON`/`_EXIT_FALLBACK` tables identical to code; `claude` `review_only=True` and `fable` alias (`detection.py:112-113`); "never switch harness/provider/model" stated consistently in SKILL.md:341, 475 and policy; evidence-line quoting required on every stop (SKILL.md:323-325, 453-457); all markdown anchors resolve.

Skipped: full line-by-line read of `cross-ai.mjs` (6292 lines — verified claims by targeted inspection + self-test names instead) and running `--self-test`; risk: a behavior mismatch invisible to the spots I checked could survive, though every sampled claim held.

DIGEST e85ac2aec5c16f61
CURRENT 111/120
CRITICAL 0 IMPORTANT 1
