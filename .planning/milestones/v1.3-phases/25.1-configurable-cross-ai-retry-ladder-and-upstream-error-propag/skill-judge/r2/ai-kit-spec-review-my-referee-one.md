Judge: my-referee-one
Reviewed-sha256: 7996e22222cd63cd1178a0a10cac115b814e4c26cccb511e4eaa31d588c4b5c1
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=301s out=1077019 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 95
Critical: 0
Important: 5

## Skill judgment: ai-kit-spec-review

**95/120 — Grade C (79.2%).** Strong domain-specific orchestration and explicit safety rules, but template-8 defects undermine retry reliability and dirty-tree protection.

Reviewed the 489-line `SKILL.md`, all 14 reference files, the linked entry point, and relevant Phase 25.1 changes. Pattern: **Process + Tool**. Estimated knowledge mix: **80% expert / 15% activation / 5% redundant**.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 17/20 | Valuable worktree, lifecycle and dispatch knowledge; historical explanations and repeated contracts add weight. |
| D2: Mindset + Procedures | 14/15 | Strong archetype ceilings, clean-context reasoning and framework-owned revision procedures. |
| D3: Anti-Pattern Quality | 14/15 | Specific prohibitions explain contamination, wrong-checkout grounding and unauthorized lane switching. |
| D4: Specification Compliance | 15/15 | Valid metadata; description clearly states capabilities, invocation scenarios and trigger terms. |
| D5: Progressive Disclosure | 11/15 | Mandatory and “do not load” triggers work, but routine dispatch requires substantial overlapping prose. |
| D6: Freedom Calibration | 9/15 | Appropriate constraints in principle; implementation bypasses a safety gate and rejects legitimate retries. |
| D7: Pattern Recognition | 8/10 | Recognizable, well-organized process/tool hybrid, weakened by repeated policy ownership. |
| D8: Practical Usability | 7/15 | Common paths are actionable; recovery defects and ineffective assertions leave important gaps. |
| **Total** | **95/120** | **Resolve the Important findings before acceptance.** |

### Findings

1. **Important — Copied-secret redaction can crash or miss literal copies.**  
   `skills/ai-kit-spec-review/references/cross-ai.mjs:1535–1536` uses a malformed regex-escape pattern. Parentheses or brackets in captured values can make `new RegExp()` throw; other metacharacters retain regex meaning.  
   **Fix:** use `/[.*+?^${}()|[\]\\]/g` and test copied values containing parentheses, brackets, dots and backslashes.

2. **Important — Fresh-session admission misses the failed attempt’s edits.**  
   `skills/ai-kit-spec-review/references/cross-ai.mjs:3948–3951,4104–4107` captures `seenSig` before execution. A `new` retry passes that same signature as both baseline and current state, so the gate accepts even when the failed child subsequently changed out-of-scope files. A reset similarly misses the latest attempt’s changes.  
   **Fix:** snapshot after failure, before retry admission, and compare against the appropriate baseline. Fail closed on snapshot errors; test an out-of-scope edit immediately before failure.

3. **Important — Cursor/OpenCode review retries reject their own resume flags.**  
   `skills/ai-kit-spec-review/references/cross-ai.mjs:3756–3759,4137–4139` compares resumed argv against the initial review formula. Runtime-owned `--resume`/`--session` arguments therefore become forbidden extras, producing `usage` instead of a soft retry.  
   **Fix:** validate against the trusted formula for the actual operation, including resume. Add resumable Cursor and OpenCode review tests.

4. **Important — Overlay bounds are checked after unrestricted reading.**  
   `skills/ai-kit-spec-review/references/cross-ai.mjs:2839,2850–2864` reads and parses the overlay before enforcing its 65,536-byte limit, then reads it again. Oversized files can exhaust memory; a FIFO can block before deadlines are established.  
   **Fix:** verify confinement, regular-file type and size before reading; parse once.

5. **Important — Hard-tier notices omit the upstream error body.**  
   `skills/ai-kit-spec-review/SKILL.md:449,452–455` requires upstream lines for terminal failures but omits them from the hard-tier wait notice. This loses the provider explanation precisely when the owner must understand a pending lane.  
   **Fix:** include `cross-ai: upstream` lines verbatim in the wait notice, treating them strictly as data, and defer evidence-trailer requirements to the canonical policy.

6. **Minor — Redaction assertions provide false confidence.**  
   `skills/ai-kit-spec-review/references/cross-ai.mjs:6653` uses `/acct-\\d+/`, which does not match the fake’s numeric account ID. At `:9456–9458,9542–9546`, state checks inspect only top-level files, missing nested cycle records.  
   **Fix:** correct the regex and inspect the specific cycle file or recursively inspect the synthetic state directory.

7. **Minor — Early refusals leak temporary directories.**  
   `skills/ai-kit-spec-review/references/cross-ai.mjs:3746,3769,3816–3856,3933,4160–4161` creates scratch space before early-return checks, outside the cleanup `try/finally`.  
   **Fix:** defer creation or place every subsequent path inside the cleanup scope.

**Policy assessment:** Canonical links resolve correctly. The instructions explicitly prohibit autonomous harness/provider/model switching and distinguish owner-configured pre-dispatch selection from recovery. Runtime/model grammar, profiles and Copilot are script-owned rather than improvised by the orchestrator.

No files changed or credentials read. Self-tests and live CLIs were not run; runtime findings are static, with the regex defect additionally checked in an isolated, file-free JavaScript evaluation.

DIGEST 7996e22222cd63cd
CURRENT 95/120
CRITICAL 0 IMPORTANT 5

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=301s out=1077019 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
