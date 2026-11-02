Judge: my-referee-two
Reviewed-sha256: 3dc6c519ffdd401af64b024d34c5e74899bffab948ee84c4968be0a24e66d79a
Lane: AIKIT-XAI status=ok cli=pi model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=360s out=4332 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 94
Critical: 0
Important: 3

# Skill Evaluation Report: ai-kit-spec-execute-superpowers

## Summary
- **Total Score**: 94/120 (78%)
- **Grade**: C
- **Pattern**: Process
- **Knowledge Ratio**: E:A:R ≈ 78:16:6
- **Verdict**: A genuine adapter contract with load-bearing decision trees, but three instructions would make an agent parse, match, or schedule the wrong thing.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 17 | 20 | Exclusion/resume/escalation rules are repo-specific and non-obvious |
| D2: Mindset vs Mechanics | 13 | 15 | Strong "ask before writing" framing plus exact domain procedures |
| D3: Anti-Pattern Quality | 14 | 15 | NEVER list names the failure each rule prevents |
| D4: Specification Compliance | 14 | 15 | Frontmatter has WHAT, WHEN, and out-of-scope keywords |
| D5: Progressive Disclosure | 12 | 15 | Mandatory reads exist, but no Do-NOT-load map and the body is dense |
| D6: Freedom Calibration | 13 | 15 | Low freedom fits fragile state; a few steps still require judgment |
| D7: Pattern Recognition | 8 | 10 | Clear phased process, longer and more cross-referential than the pattern wants |
| D8: Practical Usability | 3 | 15 | Wake identity, stderr match, and quota schedule rules contradict the code |

## Critical Issues

None. The defects mis-handle wake ownership, config consent, or a quota stop; they do not authorize a harness or model switch.

## Top 3 Improvements

1. Parse `armed`/`refreshed` the way `arm.py` prints it, and carry the whole session id.
2. Match the real untrusted-config stderr sentence, not a shortened substring.
3. State the one-shot wait condition exactly as `classify_dispatch_failure` implements it.

## Detailed Analysis

### D8
The procedures are unusually concrete, and the shim flags, JSON fields, and exclusion math check out against `cli.py` and `dispatch_injection.py`. Usability still fails because three decision points send the agent to the wrong branch.

## Findings

1. **Important** — `SKILL.md:160-163`. `WAKE_HOST="${WAKE_HOST_ID%%-*}"` and `WAKE_ID="${WAKE_HOST_ID#*-}"` split `armed <host>-<session-id>` on the first hyphen. Session ids may contain hyphens (`SESSION_ID_RE`, `skills/ai-kit-session-wake/ai_kit_session_wake/state.py:24`), and `arm` prints `armed {host}-{session_id}` (`arm.py:480`). A hyphenated id makes later `arm`/`done` target the wrong session. Fix: take the host from the known host table and the remainder as the id, or read both from the wake state file.

2. **Important** — `SKILL.md:227`. The skill waits for stderr containing `ignoring untrusted project-local config`. The emitter prints `ai-kit-spec: ignoring untrusted project-local config {path}; review its commands with ...` (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:410-414`). An agent matching the shortened sentence can miss the warning and dispatch on global config without asking. Fix: quote the full prefix through the path.

3. **Important** — `references/dispatch-external-cli.md:152-156` and `:177-183`. The text says any return code 69 or 75 with status `transient` or `quota` enters the quota branch, then schedules a wait for return code 75 whenever `RETRY_AFTER_S` and `CYCLE` are whole numbers. `classify_dispatch_failure` returns `quota` for 75 only when both tokens are whole numbers; a non-numeric hint such as `600s` is `real_error` (`dispatch_injection.py:441-450`, test at `tests/test_ai_kit_spec_superpowers.py:1000-1006`). Return code 69 is `quota` only when `retry_after_s` is absent (`dispatch_injection.py:451-454`). The written condition can schedule a wait the classifier rejected. Fix: schedule only after classification is `quota`, return code is 75, and both tokens match `[0-9]+`; state that 69 reaches this branch only as a tokenless owner stop.

4. **Minor** — `references/quota-wake.md:35`. The prompt says "fourteen placeholders" but the template binds sixteen named values (`SKILL_DIR` through `WAKE_ID` plus `REPORT_MODE`). Fix: count the substituted tokens.

5. **Minor** — `SKILL.md:346`. "Node 24 (GSD's floor, unverified" is stale. This checkout's research records `@opengsd/gsd-core` `engines.node >=24.0.0` (`.planning/phases/18.1-one-runtime-model/18.1-RESEARCH.md:231`). Fix: cite that source or drop "unverified."
