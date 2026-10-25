# ai-kit-gsd-curated-config — skill-judge report (opencode router-env/my-referee-one, read-only review mode)

Round 6, skill digest `c3f432f44f2da7b7`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

Runner status: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=159s out=653400 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0`

## Skill judgment: ai-kit-gsd-curated-config

**112/120 — A (93.3%).** Strong **Process/Tool** skill with predominantly project-specific knowledge (estimated Expert:Activation:Redundant ratio **85:10:5**).

Read the full requested rubric, all 405 lines of `SKILL.md`, both local references (`runner.md`: 90 lines; `v1-path.md`: 47 lines), the linked quota policy, and the requested diff. No `scripts/` directory exists in this skill.

### Dimension scores

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Valuable GSD-specific contracts and edge cases; some repeated instructions. |
| D2: Mindset + Procedures | 15/15 | Strong trust, approval, migration and recovery decision points. |
| D3: Anti-Pattern Quality | 15/15 | Specific prohibitions explain consequences, particularly fallback and rollback hazards. |
| D4: Specification Compliance | 15/15 | Valid frontmatter; description clearly covers capabilities, situations and trigger terms. |
| D5: Progressive Disclosure | 12/15 | Explicit conditional loading and “Do NOT load” guidance, but repeated runner details inflate the main body. |
| D6: Freedom Calibration | 15/15 | Appropriately constrained writes, owner decisions and cross-AI dispatch behavior. |
| D7: Pattern Recognition | 9/10 | Clear Process/Tool structure; duplicated reference material weakens compactness. |
| D8: Practical Usability | 13/15 | Comprehensive failure handling; one documented output field does not match implementation. |
| **Total** | **112/120** | **A** |

### Phase 25 assessment

The core policy is correctly represented:

- **One CLI per call, no missing-CLI fallback:** `SKILL.md:216–228`.
- **Mandatory shared-policy loading after non-`ok` output:** `SKILL.md:221–225`; the linked policy specifies same-session retries, new sessions, cross-call router cooldowns and the four-hour cap.
- **Confirmed versus inferred router authorization:** `SKILL.md:105–112`, `references/runner.md:43–49`.
- **Verbatim evidence and no autonomous harness/provider/model/native-session switch:** `SKILL.md:244–251`.
- **Legacy active-runner protection:** `SKILL.md:263–275` correctly distinguishes the active script from `.new` and blocks unsafe reliance on pre-template-7 behavior.

### Findings

Paths below are relative to `skills/ai-kit-gsd-curated-config/`.

1. **Minor — `ensure-runner` is documented as emitting a field it does not return.**  
   **Evidence:** `SKILL.md:354` says an edited older runner reports `script.active: false`; `references/runner.md:55–58` repeats that assertion in the upgrade discussion. However, `ai_kit_gsd_curated_config/cross_ai_script.py:339–344` returns only `ready`, `runner`, `guidance` and `notes`.  
   **Concrete fix:** Reserve `script.active: false` for v2 `apply`. Describe `ensure-runner` using its actual `runner` result, notes and `ready: false` below template 7.

2. **Minor — Repeated runner contracts dilute otherwise good progressive disclosure.**  
   **Evidence:** The inactive-`.new`/active-header rule appears in `SKILL.md:263–275`, `354`, `375–377` and `references/runner.md:55–85`. The no-switch rule is substantially repeated at `SKILL.md:249–251` and `378–380`.  
   **Concrete fix:** Keep one compact safety rule and loading trigger in `SKILL.md`; retain upgrade mechanics in `references/runner.md`, and shorten the subcommand table and NEVER entries to pointers.

No files were changed or credentials read. Runtime tests and live dispatches were not run; behavioral conclusions are based on static inspection.

DIGEST c3f432f44f2da7b7
CURRENT 112/120
CRITICAL 0 IMPORTANT 0
