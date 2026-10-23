## Assessment

Read both `SKILL.md` files and all three references in each package. This is a read-only assessment; commands were inspected, not executed.

Both versions follow a **Process/Tool hybrid**: resolve an executor, preserve exclusion state, inject dispatch, and leave review ownership with the upstream harness. CURRENT adds useful runtime-routing, confinement, prerequisite, and uncertainty disclosures, but introduces an unresolved non-Claude native-escalation case.

### Scores

| Rubric dimension | Max | BASELINE | CURRENT | Evidence and rationale |
|---|---:|---:|---:|---|
| **D1: Knowledge Delta** | 20 | 15 | 16 | Exclusion provenance, append-only reports, and capability-floor handling are genuinely specialized knowledge. CURRENT adds valuable `unverified` routing and confinement distinctions. Both repeat substantial historical “finding/recurrence guard” explanations. |
| **D2: Mindset + Appropriate Procedures** | 15 | 14 | 14 | “Is this exclusion permanent or same-wave only?” (`SKILL.md:93–95`, both versions) transfers a useful thinking framework alongside exact procedures. Decisions when capability cannot be established remain incomplete. |
| **D3: Anti-Pattern Quality** | 15 | 15 | 15 | The NEVER section (`SKILL.md:18–42`, both) identifies concrete failure modes and explains their consequences: ineffective exclusions, permanent quota lockouts, overwritten evidence, and futile scheduled retries. |
| **D4: Specification Compliance** | 15 | 15 | 15 | Valid frontmatter and name. Both descriptions state WHAT, WHEN, trigger terminology, and the explicit exclusion of `executing-plans`. CURRENT updates the terminology to runtime/model pairs. |
| **D5: Progressive Disclosure** | 15 | 13 | 13 | Mandatory reference-loading triggers are embedded before state handling and escalation; design notes are conditional. Explicit “do not load escalation for ordinary rounds” guidance and leaner mandatory references would improve layering. |
| **D6: Freedom Calibration** | 15 | 12 | 11 | Exact commands appropriately constrain fragile state handling. Both nevertheless permit an unproven capability bump when ranking information is missing. CURRENT additionally delegates native model escalation to hosts it says cannot select another model. |
| **D7: Pattern Recognition** | 10 | 9 | 9 | Clear resolve → inject → classify → hand-back structure. The main files remain manageable—approximately 290 and 321 lines—but repeated rationale makes the package less compact than an excellent Process/Tool implementation. |
| **D8: Practical Usability** | 15 | 10 | 10 | Strong quota, trust, report-preservation, and failure branches. Both have an escalation-resume counterexample. CURRENT’s additional routing and prerequisite coverage is offset by its unsupported native-escalation path. |
| **Total** | **120** | **103** | **103** | **Both Grade B (85.8%).** CURRENT improves operational disclosure, but not overall reliability enough to increase its total. |

Approximate Expert:Activation:Redundant content ratios: **BASELINE 70:15:15**, **CURRENT 75:12:13**. These are qualitative estimates; repetition, rather than elementary tutorials, causes most token waste.

## CURRENT findings

### Critical

None identified.

### Important

1. **The escalation floor is not reconstructible reliably after a quota pause.**  
   **Lines:** `skills/ai-kit-spec-execute-superpowers/references/escalation.md:89–99`; related persisted fields at `references/state-management.md:134–138`.

   The reference claims that no escalation state needs persistence, then recomputes the floor from whichever candidate fresh resolution selects. That candidate need not be the implementer whose failure originally required escalation.

   **Counterexample:** With ladder `[A, B]`, B is stuck and round 4 requires A, but A has no quota. After quota recovery, resume selects A; recomputing the floor relative to A excludes both A and B, stopping without trying the now-available intended escalation.

   **Fix:** Persist the escalation origin or capability threshold separately from failure exclusions, and retain that threshold when resuming the same pending round. **Inherited from BASELINE.**

2. **The missing-key fallback cannot enforce “MORE CAPABLE.”**  
   **Lines:** `skills/ai-kit-spec-execute-superpowers/references/escalation.md:44–60`.

   When the stuck key is absent from `ladder_keys`, `idx = len(ladder)` excludes only the stuck key. Every listed candidate remains eligible, although none has been established as more capable. Preventing reselection of the same key is not equivalent to enforcing a capability increase.

   **Fix:** Re-establish a comparable ranking or stop with an explicit capability-ordering error; do not treat unknown relative capability as a proven bump. **Inherited from BASELINE.**

3. **Non-Claude native execution has no actionable rounds 4–5 escalation path.**  
   **Lines:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:181–187`; reinforced by `references/escalation.md:15–18`.

   CURRENT says other hosts can run only their session default natively and must omit `model`, while leaving the required model bump to the upstream harness’s native judgment “with no ladder.” It supplies no branch for a host that cannot perform that bump.

   **Fix:** Explicitly transition to a more-capable subprocess pair, or stop and explain that the configured host cannot satisfy the escalation requirement. **Introduced by CURRENT’s broader native-host support.**

### Minor

4. **Mandatory references contain excessive historical review commentary.**  
   **Lines:** `skills/ai-kit-spec-execute-superpowers/references/state-management.md:12–18, 72–88, 99–129`.

   Repeated “CRITICAL finding,” “recurrence guard,” and task-number history restate invariants already explained elsewhere. Because this reference is mandatory for every execution, that repetition imposes recurring context cost.

   **Fix:** Keep each invariant and its non-obvious consequence once; consolidate historical explanations into the conditionally loaded design notes.

5. **The non-quota stop explanation overstates permanence.**  
   **Lines:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:155–163`.

   CURRENT lists `"capacity"` and `"git_timeout"` among reasons, then describes every non-quota outcome as something “waiting never fixes.” That is stronger than the documented policy warrants: a failure may be transient without qualifying for automatic quota recovery.

   **Fix:** Say these failures are **not eligible for this adapter’s automatic quota-wake policy**, rather than asserting that waiting cannot resolve them.

BASELINE 103/120
CURRENT 103/120
CRITICAL 0
IMPORTANT 3
