Judge: my-referee-two
Reviewed-sha256: 7996e22222cd63cd1178a0a10cac115b814e4c26cccb511e4eaa31d588c4b5c1
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=372s out=519007 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 109
Critical: 0
Important: 2

All evidence is in. The skill's claims cross-check cleanly against the runner source, the dispatch layer, and the canonical policy; two accuracy gaps remain. Report:

# Skill Evaluation Report: ai-kit-spec-review

**Total: 109/120 (91%) — Grade A** · Pattern: Process (phased workflow + Tool elements) · E:A:R ≈ 85:13:2
Scope reviewed: SKILL.md (489 ln) + all 9 references/ files + cli-profiles/ (5) + the runner `cross-ai.mjs` and `ai_kit_spec/` sources it drives, cross-checked against the canonical `skills/ai-kit-cross-ai/SKILL.md` + its 2 references, and the Phase 25.1 diff (`35a0368~1..HEAD`).

Phase 25.1 verification: `--runtime` one-runtime-per-call with `--prefer` first-entry alias confirmed in `cross-ai.mjs:23-24` and `runner_dispatch.py:199-202` (`--prefer <rt> --model-<rt>` → `--runtime <rt> --model <rt>`); script-owned model grammars (`PI_MODEL_ID_SRC`/`OPENCODE_MODEL_ID_SRC`, `runner_dispatch.py:53-61`); Copilot runtime (`detection.py` v7, `"copilot": Runtime(("copilot",), (), runner=True)`); catalog + owner overlay with 50 ms bound (`cross-ai.mjs:1122-1126, 1637-1667`; 73 rows, 17 honestly labeled `unverified`); redacted upstream pass-through (`cross-ai.mjs:1518-1560, 1855-1862`); policy pointers all resolve and the skill never instructs a switch (hard-rules table row "Never re-dispatch a failed subprocess lane…", SKILL.md:474; "Never switch harness, provider or model", SKILL.md:349). No stale link to the moved `references/subprocess-quota-policy.md` remains.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 18 | 20 | Near-pure expert content: worktree-root derivation, archetype ceilings, pre-dispatch ladder vs post-dispatch no-switch, exit 69/75 contract. Slight duplication of cross-ai-dispatch.md in Step 1 prose. |
| D2: Mindset + Procedures | 14 | 15 | "Ask yourself" prompts at Steps 0.5/3/5 + genuinely unknown procedures (persist-before-dispatch, resume files, merge lock). |
| D3: Anti-Pattern Quality | 14 | 15 | "Have actually bitten this loop" NEVERs + hard-rules table with hard-won reasons ("a switch hides the stop and reviews with a lane nobody chose"). |
| D4: Spec Compliance / Description | 15 | 15 | WHAT + WHEN + trigger keywords + explicit invocation phrases; name valid. |
| D5: Progressive Disclosure | 13 | 15 | Excellent MANDATORY triggers + "Do NOT load cross-ai.mjs / cli-profiles"; 489 ln body near the 500 dump ceiling, ideal <300. |
| D6: Freedom Calibration | 14 | 15 | Verbatim templates/exact commands where fragility is high; judgment left where safe (surface wording). |
| D7: Pattern Recognition | 9 | 10 | Clean Process pattern with Tool decision tables. |
| D8: Practical Usability | 12 | 15 | Decision tables + fail-closed edges everywhere, but findings 1–2 below sit in the most critical error path, and Step 1's dispatch block is a ~30-line run-on. |

## Findings

1. **Important — exit-69 evidence list is a union across sub-cases, not per-case.** `SKILL.md:334-337` tells the caller an exit 69 (stop *or* lane-stopped refusal) prints "`cross-ai: report`, `cross-ai: upstream`, `cross-ai: lane stopped` and `AIKIT-XAI` lines verbatim from its `.err`" — but a real stop has no `lane stopped` line, and a refusal has *no* report/upstream lines at all (the runner returns immediately after `cross-ai: state` + `cross-ai: lane stopped`, `cross-ai.mjs:3817-3827`; canonical policy requires only report/upstream/AIKIT-XAI on a stop, `ai-kit-cross-ai/references/subprocess-quota-policy.md:160-163`). A literal executor treats missing lines as an anomaly. **Fix:** "…quote whichever of those lines the `.err` actually contains — a stop has `report`(+`upstream`) and `AIKIT-XAI`; a refusal has only `state`, `lane stopped` and `AIKIT-XAI`."

2. **Important — hard-tier wait row omits the upstream lines, breaking the switch-combo-hint reporting chain.** `SKILL.md:449` quotes `cross-ai: report`, `cross-ai: state` and the last `AIKIT-XAI`, but the runner also emits `cross-ai: upstream body=/fields=` on an exit-75 stop (`cross-ai.mjs:1252-1258`; `cross-ai-dispatch.md:358-361`), and the policy's rule is that an upstream "pick another combo" hint is reported to the owner, never acted on (`subprocess-quota-policy.md:125-127`). The sibling Failure row (`SKILL.md:452-454`) does quote them; the wait row — the one the owner reads while a lane is pending — drops the exact channel a prompt-injection hint would arrive on. **Fix:** add `cross-ai: upstream` to the row's quote list.

3. **Minor — 489-line body, dense run-on blocks in the most critical branch.** `SKILL.md:294-349` (Step 1 subprocess) mixes six exit/outcome rules in one paragraph. Fix: move the rationale sentences (e.g. 321-328) into `cross-ai-dispatch.md`'s existing rationale section, keep Step 1 as command + branch table.

4. **Minor — degraded path still pays the full read.** `SKILL.md:153` mandates reading all 383 lines of `cross-ai-dispatch.md` even for `--no-cross-ai`/tools-missing runs that use only points 0–2. Fix: allow "read points 0–2 (first ~125 lines)" on that path.

5. **Minor — wait-length wording mismatch.** `cross-ai-dispatch.md:293-294` schedules "at `retry_after_s` seconds (at least 60 s, rounded up to the next whole minute)" vs canonical "for exactly `retry_after_s` seconds" (`ai-kit-cross-ai/SKILL.md:120-122`). Rounding up is safe, but say it in one place. Fix: state the round-up rule in the canonical policy or drop it here.

6. **Minor — "on any route" over-breadth.** `SKILL.md:330-331` / `cross-ai-dispatch.md:245-247` extend the exit-75 hard tier to "any route", but a `custom` lane never emits an `AIKIT-XAI` line (`runner_dispatch.py:655-657`, `status=None`), so the branch is unreachable there. Fix: "any runner route (a `custom` lane has no `AIKIT-XAI` line and never reaches this branch)".

**Top improvement:** fix findings 1–2 together — both are one-clause edits to the exit-69/75 quoting instructions, and they close the only gaps in an otherwise correctly-delegated caller contract.

DIGEST 7996e22222cd63cd
CURRENT 109/120
CRITICAL 0 IMPORTANT 2

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=372s out=519007 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
