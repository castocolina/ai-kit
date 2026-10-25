# ai-kit-gsd-curated-config — skill-judge report (opencode router-env/my-referee-two, read-only review mode)

Round 5 (evidence round), skill digest `089d13c6a215b519`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

## Round 5: BLOCKED (the runner stopped the lane; no score)

Runner evidence lines:

```text
cross-ai: report status=crash lane=opencode/router-env/my-referee-two route=router attempts=1 cycles=0 first_failure=2026-10-25T04:25:46.793Z last_failure=2026-10-25T04:25:47.904Z stopped=class
AIKIT-XAI status=crash cli=opencode model=router-env/my-referee-two exit=1 cli_rc=1 elapsed=1s out=1148 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```

Upstream messages (OmniRoute, verbatim, trimmed):

```text
Combo has no executable targets
```

## Last completed report from this judge (round 2, an earlier digest; reference only, not this verdict's score)

All evidence gathered and verified against the implementation. Here is the evaluation.

# Skill Evaluation Report: ai-kit-gsd-curated-config

## Summary
- **Total Score**: 109/120 (90.8%) — Grade A
- **Pattern**: Process/Tool hybrid (phased workflow + exact-command decision tables, low freedom)
- **Knowledge Ratio**: E:A:R ≈ 85:15:0 — near-pure curated policy; no tutorial filler
- **Verdict**: An exemplary contract-heavy operations skill whose Phase 25 runner policy is described accurately and verified against the template and code; two Important precision defects remain, both narrow-edge.

**Phase 25 verification (all confirmed in code):** template 7 is current (`cross-ai.mjs:2`); one CLI per call, first `prefer` entry only, missing → `not_installed` exit 127 (`cross-ai.mjs:815`, policy §One CLI per call); `capS` 14400 clamp (`cross-ai.mjs:69,1762`); evidence line is the single last stderr line, `action=stop` on every status including clean exit 0 (`cross-ai.mjs:17,3322-3324`); `git_error`/`git_timeout` → exit 1, never a second CLI (`cross-ai.mjs:817-818`, old fallback wording correctly deleted in the diff); both pointers to `subprocess-quota-policy.md` resolve (SKILL.md:213, runner.md:42); SKILL.md does not restate the 4-hour cap — exactly what the policy file itself mandates ("A skill links here; it does not copy the rules"); the never-switch rule appears in body, NEVER list, and matches the policy verbatim in spirit. `router_backed` initial-set claim matches `recommend.py:544-555` / `cross_ai.py:106,109`.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 19 | 20 | Exit-code semantics, refusal→action maps, trust model, per-flow permission facts — none of this is model knowledge |
| D2: Mindset + Procedures | 14 | 15 | "Ask yourself: trusted checkout? v1-written? where does scratch live?" (SKILL.md:60-64) + exact one-Bash-call procedures |
| D3: Anti-Pattern Quality | 15 | 15 | 8-item NEVER list each with an expert why ("inventory … executes that project's JavaScript"); mistakes table adds why+fix |
| D4: Spec Compliance | 15 | 15 | Description (648 chars) has WHAT + WHEN ("Use when asked to…") + keywords incl. new `ensure-runner`, `cross-ai.mjs.new` triggers |
| D5: Progressive Disclosure | 13 | 15 | Excellent "Read when…" / "Do NOT load" triggers; 386 lines and a 55-line in-body refusal matrix cost tokens |
| D6: Freedom Calibration | 14 | 15 | Rigid exactly where writes are destructive (dry-run, end-the-turn, fingerprint); flexible only where user preference governs |
| D7: Pattern Recognition | 8 | 10 | Clean Process+Tool hybrid; the Skills section's bulk is the main structural deviation |
| D8: Practical Usability | 11 | 15 | Decision tables + recovery paths superb; two precision defects below |

## Findings

1. **Important — `router_backed` recompute rule overstated.** SKILL.md:104-106 says `plan-set script:cross-ai.model.<runner>` "recomputes it from **that same inventory rule**" recommend used. Recommend's rule includes `name_declared_purpose == "execute"` (`cross_ai.py:106`, `recommend.py:550`), but plan-set's recompute checks only `is_router` + `router_confirmed` (`plan_edit.py:208-218,241-245`), and the row-level `router_confirmed` folds in purpose ∈ {review, execute} (`catalog_adapter.py:34,384`). A user-confirmed **review**-purpose router re-picked as an execution model (present in the inventory, so no `--force` needed) therefore gets `router_backed: true` — quota-cycle authorization recommend would never grant. **Fix:** add one clause ("plan-set's recompute keeps the row's `is_router`+`router_confirmed` only; recommend additionally requires declared purpose `execute`") or align `_confirmed_router` to require purpose `execute`.

2. **Important — runner exit codes absent from the exit-code table.** The table (SKILL.md:30-36) is the natural lookup and covers only 0/1/2 of the Python CLI; exit 127 appears only inline (SKILL.md:119-120, 211) and exits 75/69 only via the external policy file. An agent seeing exit 127 from a dispatch has shell's "command not found" as prior and nothing in the table to correct it. **Fix:** one footnote row: "runner (cross-ai.mjs) exits, not this CLI: 127 `not_installed`, 75 quota/transient (re-entry contract in the policy), 69 terminal stop, 1 `git_error`/`git_timeout`."

3. **Minor — exit 127 placed in a plan-set bullet.** SKILL.md:117-121 documents a runner-dispatch outcome inside step 3, a Python-CLI step; a reader may expect `plan-set` itself to exit 127. **Fix:** move that sentence to "Cross-AI execution" (it already says it at line 211 — keep one).

4. **Minor — `.new`/template-header rule stated four times.** SKILL.md:249-256, SKILL.md:356-358, runner.md:52-59, runner.md:79-86. Defensible for a destructive path, but it is pure token cost; one normative statement plus the NEVER pointer suffices.

5. **Minor — Skills refusal matrix is reference-grade in-body content.** SKILL.md:258-312 (~55 lines of gsd-core reference-resolution rules) loads on every invocation though it matters only while resolving `agent_skills` choices. **Fix:** move to `references/skills-wiring.md` with a "Read when an `agent_skills` refusal or trusted-root choice comes up" trigger, matching the runner.md pattern.

## Top 3 Improvements
1. Reconcile the `router_backed` recompute wording with `plan_edit._confirmed_router` (Finding 1) — it is the Phase 25 authorization mechanism.
2. Add runner exit codes to the exit table (Finding 2).
3. Layer the Skills wiring matrix into `references/` (Finding 5) to bring SKILL.md under ~330 lines.

DIGEST 569fa19915950c3b
CURRENT 109/120
CRITICAL 0 IMPORTANT 2
