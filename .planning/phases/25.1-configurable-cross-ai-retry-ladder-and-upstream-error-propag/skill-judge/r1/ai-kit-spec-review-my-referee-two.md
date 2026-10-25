Judge: my-referee-two
Reviewed-sha256: 6efb7723c3ca635d131295da929abda0a3fdc89e12ab88b5d3fa1a25d2c3911a
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=348s out=480935 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 105
Critical: 1
Important: 3

# Skill Evaluation Report: ai-kit-spec-review

**Total: 105/120 (87.5%, Grade B)** · Pattern: Process (orchestrator loop + Tool-pattern references) · Knowledge ratio E:A:R ≈ 75:20:5

**Verdict:** A genuinely expert orchestration skill whose 25.1 changes correctly describe and point at the ai-kit-cross-ai policy — with one load-bearing contradiction left behind in its own mandatory-read reference.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 17 | 20 | Worktree-root derivation, archetype ceiling, exit-code contract, dispatch hygiene are all expert-grade; minor repetition (`--cwd` first-entry rule ×3, self-referential SEEDS_DIR rationale, cross-ai-dispatch.md:5-18) |
| D2: Mindset + Procedures | 14 | 15 | Four "ask yourself" prompts (SKILL.md:68, 151, 392, 424) + non-obvious orderings (check-first-save-second, cross-ai-dispatch.md:123-127; branch-before-deleting, SKILL.md:326) |
| D3: Anti-Pattern Quality | 15 | 15 | Hard-rules table each with a real why — "a switch hides the stop and reviews with a lane nobody chose" (SKILL.md:465) is exactly experience-taught |
| D4: Spec Compliance | 14 | 15 | Description has WHAT+WHEN+explicit triggers+keywords; name valid; one dense run-on sentence |
| D5: Progressive Disclosure | 13 | 15 | MANDATORY full-file triggers ×3, conditional triggers, "Do NOT load" for cross-ai.mjs and cli-profiles (SKILL.md:153); gaps: findings 3 and 6 below |
| D6: Freedom Calibration | 14 | 15 | Fragile ops → verbatim commands, no-render rule, fail-closed parsing; right judgment at routing/surface points |
| D7: Pattern Recognition | 8 | 10 | Clean Process pattern; 480-line body is heavier than the ~200 ideal but properly layered |
| D8: Practical Usability | 11 | 15 | Decision tables, fallbacks, stated portability gaps — but the Critical contradiction (finding 1) gives an agent two incompatible answers on a destructive branch |

## 25.1 verification (what was checked against the code)

- `--runtime` one-per-call with `--prefer` first-entry alias: cross-ai.mjs:23-24, 4258-4288 ✓; cross-ai-dispatch.md:214 updated ✓
- Soft retry series + one session reset: cross-ai.mjs:2915-2918, 4030-4033 ✓
- Caller hard tier (`hard_waits_s`, notify-and-stop, never a switch): cross-ai.mjs:3047-3055, 3861-3890; exit-75 hint for **both** `transient` and `quota`, route-independent; bare 75 only on unwritable state (cross-ai.mjs:3849-3852) ✓ — matches SKILL.md:326-332 and ai-kit-cross-ai SKILL.md §4/§6/§8
- Upstream error body redacted and printed (`cross-ai: upstream body/fields`, cross-ai.mjs:1253-1258) ✓; SKILL.md:443-445 quotes it ✓
- Error catalog + owner overlay: cross-ai-errors.json, documented in ai-kit-cross-ai/references/subprocess-quota-policy.md:134-144 ✓
- Script-owned `--model` grammars and tool profiles: cross-ai.mjs:33, 4198-4210; mirrored in runner_dispatch.py:79-87 ✓
- Copilot runtime, honestly flagged unverified: detection.py:117-118, cross-ai.mjs:1431-1432 ✓
- Links `../ai-kit-cross-ai/SKILL.md` (SKILL.md:339) and `../../ai-kit-cross-ai/references/subprocess-quota-policy.md` (cross-ai-dispatch.md:247, 357, 361) all resolve ✓

## Findings

1. **Critical — the mandatory-read reference contradicts SKILL.md and the canonical policy on the exit-75 branch.** cross-ai-dispatch.md:244-246 and 256-261 gate the keep-report/re-invoke path on `route=router` and say "A `route=router-inferred` lane gets no cycles: its quota stop is a bare exit 75, a failed lane." Template 8 emits the exit-75 `retry_after_s=` hard-tier hint for both `transient` and `quota` with no route condition (cross-ai.mjs:3861-3890; ai-kit-cross-ai SKILL.md exit table: "75 | quota, transient"), and SKILL.md:326-329 says exactly that. An orchestrator following this reference (read in full on *every* run, SKILL.md:153) would delete a transient-lane hint report per cross-ai-dispatch.md:250 ("Every other nonzero exit deletes…") instead of scheduling the one-shot re-invoke. **Fix:** rewrite the "Pending router lane" section trigger to "exit 75 with `retry_after_s=` (hard tier, any soft class)", drop the router-inferred sentence (route= remains only error-catalog row admission, cross-ai.mjs:1618-1624), and rename the section "Pending lane (hard tier)".
2. **Important — "Status line to reason" table is stale for template 8** (cross-ai-dispatch.md:335-357): still titled "Template 7", lists `idle_stall` (zero occurrences in the template-8 runner), and omits the hard-tier tokens (`stopped=`, `due_at=`, `retry_after_s=… cycle=`) and the `cross-ai: upstream` line SKILL.md:443-445 now requires quoting. **Fix:** retitle to template 8, drop or version-scope `idle_stall`, add the missing tokens and upstream line.
3. **Important — the canonical-policy pointer lost its read trigger.** SKILL.md:339-340 is now a bare two-line footnote ("Cross-AI caller contract: …ai-kit-cross-ai/SKILL.md"); the pre-25.1 text (removed in 06bf79b) made the caller contract MANDATORY "before acting on any subprocess stop". Nothing now says when to open the canonical skill. **Fix:** restore the trigger: "read it before acting on any exit 69 or 75".
4. **Important — the probe walk is a provider switch the skill makes on its own, disclosed but unresolved** (SKILL.md:157-169): a failed probe moves the review to the next configured entry "which may be another provider", and an out-of-quota confirmed lane is "walked past, so its cooldown cycles never start" — in tension with canonical §8 ("Never switch harness, provider or model, on any failure, in the runner or in a caller"). The skill honestly flags it as "shipped pre-dispatch behavior (the owner has not ruled on it yet)". **Fix:** either record the owner ruling (config ladder order = standing consent) in the policy file, or gate the walk behind a user confirmation like the trust-local flow.
5. **Minor — stale router-era naming.** Surface row "Router quota cooldown" (SKILL.md:440) and resume pointer "pending router lane section" (SKILL.md:232-233) name the template-7 concept; the 25.1 behavior is the class-agnostic hard tier. Rename to "hard-tier wait"/"pending lane".
6. **Minor — cross-ai-errors.json is an uncovered 965-line data file.** It sits in references/ with no mention in SKILL.md or cross-ai-dispatch.md and no "Do NOT load" note (only cross-ai.mjs and cli-profiles are excluded, SKILL.md:153). **Fix:** add it to the do-not-load line with a pointer to subprocess-quota-policy.md:134-144.
7. **Minor — no cli-profiles entry for the new copilot runtime.** references/cli-profiles/ has claude/codex/cursor/grok/opencode only, while copilot's flags/error shapes are the ones explicitly marked unverified (detection.py:117, cross-ai.mjs:1431-1432). **Fix:** add copilot.md carrying the same unverified flag, or note the gap where SKILL.md:216-217 describes the runtime table.

Note: by the repo's own gate ("no remaining Critical/Important finding, or score ≥ 96/120") this skill is **not** complete despite 105/120 — finding 1 must be fixed.

DIGEST 6efb7723c3ca635d
CURRENT 105/120
CRITICAL 1 IMPORTANT 3

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=348s out=480935 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
