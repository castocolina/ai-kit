# ai-kit-spec-execute-superpowers — skill-judge report (opencode router-env/my-referee-two, read-only review mode)

Round 5 (evidence round), skill digest `beff20e2e6df85d9`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

## Round 5: BLOCKED (the runner stopped the lane; no score)

Runner evidence lines:

```text
cross-ai: report status=crash lane=opencode/router-env/my-referee-two route=router attempts=1 cycles=0 first_failure=2026-10-25T04:25:46.794Z last_failure=2026-10-25T04:25:47.819Z stopped=class
AIKIT-XAI status=crash cli=opencode model=router-env/my-referee-two exit=1 cli_rc=1 elapsed=1s out=1148 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```

Upstream messages (OmniRoute, verbatim, trimmed):

```text
Combo has no executable targets
```

## Last completed report from this judge (round 2, an earlier digest; reference only, not this verdict's score)

# Skill Evaluation Report: ai-kit-spec-execute-superpowers

## Summary
- **Total Score**: 112/120 (93%) — Grade A
- **Pattern**: Process (phased workflow) + Navigation (mandatory reference reads at decision points)
- **Knowledge Ratio**: E:A:R ≈ 85:13:2 — near-pure expert delta
- **Verdict**: A dense, verified adapter contract for a fragile multi-runtime dispatch; every Phase 25 claim cross-checks against the code and the sibling quota policy.

**Phase 25 verification** (the review's focus): SKILL.md:39–47 and 378–384 state the no-fallback/never-switch rule; `subprocess-quota-policy.md` exists at the exact path given (SKILL.md:55–58 → `../ai-kit-spec-review/references/subprocess-quota-policy.md`) and is pointed at, not restated. Exit codes verify against `cross-ai.mjs`: quota/transient → 75 (lines 812–813), auth/billing/permission/bad_model → 69 (808–811), capped cycle → 69 (2461: `capped ? 69 : 75`); `retry_after_s`/`cycle` live only in the parsed `AIKIT-XAI` status dict (`runner_dispatch.py:241,514`), matching SKILL.md:321–331; evidence-lines-first ordering (SKILL.md:315–320) mirrors policy §"What a skill does on a stop" verbatim. The reason vocabulary (SKILL.md:174–179) matches `error_classifier.py:23–55` exactly. The one-wake/one-CLI contract and the persisted-injection re-dispatch are internally consistent across SKILL.md, all three references, and `cli.py`.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Proprietary contract knowledge throughout; slight cost from repeating the owner-rule in five places |
| D2: Mindset + Procedures | 14 | 15 | "Permanent or same-wave?" framing + exact ladder/state procedures Claude cannot know |
| D3: Anti-Pattern Quality | 14 | 15 | 9-item NEVER index, each with its non-obvious failure mode (e.g. runtime-id-excludes-nothing) |
| D4: Spec Compliance / Description | 15 | 15 | WHAT + WHEN + keywords + an explicit negative trigger (not for executing-plans) |
| D5: Progressive Disclosure | 14 | 15 | MANDATORY reads embedded at each decision point; design-notes is opt-in; 422 lines is heavy but bash lives in references |
| D6: Freedom Calibration | 14 | 15 | Low freedom where one wrong move burns quota or destroys report evidence; judgment left to the host harness |
| D7: Pattern Recognition | 9 | 10 | Clean Process pattern with navigation triggers |
| D8: Practical Usability | 14 | 15 | Every branch leaf covered and code-verified; one resume ambiguity, one doc-shape drift |

## Findings

**Important**

1. **Terminal quota stop persists `injection_json`, creating a resume ambiguity.** The quota-branch state write (SKILL.md:333–337, state-management.md:111–135) runs for the whole `"quota"` classification — including exit-69 terminal stops where step 4 schedules nothing (SKILL.md:338–345). The resume rules then split by actor, not by file: state-management.md:51–59 (owner resume → re-enter Step 2) vs 61–64 ("When the state file holds `injection_json`, the wake re-dispatches that object unchanged … skips `resolve-injection`"). An agent resuming an exit-69 state sees `injection_json` in its restored file and two plausible readings; worst case it re-dispatches a capped lane instead of re-resolving. Fix: one clause in state-management.md's "Initial and resume values" — "`injection_json` in the file matters only to a one-shot wake; an owner-controlled resume re-enters Step 2 regardless (for a terminal stop it is inert)."

**Minor**

2. **Stale shape listing in design-notes.** design-notes.md:19–22 lists the `quota_exhausted` payload without `ladder_keys`, but the code emits it (`cli.py:147`) and escalation.md:51 depends on it ("every mode, `quota_exhausted` included"). Fix: add `ladder_keys` to that tuple.
3. **`--heartbeat-interval` required-but-unused is documented, not fixed.** SKILL.md:274 admits it; `cli.py:420` requires it and `_cmd_dispatch_task` never reads it, so every caller passes a dummy. Fix in code (drop or default the flag) rather than documenting the wart.
4. **Repetition cost of the owner rule.** "Never switch harness, provider or model" appears at SKILL.md:39–45, 313, 370–373, 378–384 and design-notes.md:116–133. Deliberate reinforcement of the one load-bearing rule, but the NEVER-index entry could shed its duplicated ladder-pointer text. Token cost only.
5. **Native-dispatch failure handling is silent.** Classification and the failure ladder exist only for `external_cli` (SKILL.md:283–287); a native `Agent`-tool error is left to subagent-driven-development by implication (SKILL.md:205–214). One sentence stating that inheritance explicitly would close the gap.

## Top 3 Improvements
1. Disambiguate `injection_json` on owner resumes of terminal stops (Finding 1).
2. Sync design-notes' payload shapes with the emitted JSON (Finding 2).
3. State the native-failure fallback explicitly (Finding 5).

DIGEST 41fbf0552697cc22
CURRENT 112/120
CRITICAL 0 IMPORTANT 1
