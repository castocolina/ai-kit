# Skill Evaluation: ai-kit-gsd-curated-config

All locations below are relative to `skills/ai-kit-gsd-curated-config/`.

## Summary

- **Score:** 114/120 — **95%, Grade A**
- **Pattern:** Tool, supported by a phased Process workflow.
- **Estimated knowledge ratio:** Expert 85% / Activation 10% / Redundant 5%.
- **Verdict:** Strong, domain-specific operational guidance with excellent approval and recovery safeguards. One important boundary-handling gap remains.

This was a read-only assessment; commands were not executed.

## Structure and knowledge scan

| File | Size | Assessment |
|---|---:|---|
| `SKILL.md` | 315 lines | Valid frontmatter; focused operational workflow |
| `references/runner.md` | 61 lines | Conditional runner maintenance and upgrade details |
| `references/v1-path.md` | 47 lines | Explicitly secondary legacy workflow |

**Expert content:** trust and resolution rules, migration removals, runner permissions, rollback states, follow-up fingerprints, skill wiring, and both references.

**Activation content:** command lookup, shell-state reminders, approval/reporting reminders.

**Redundant content:** several common-mistake rows restate instructions already given completely in the workflow.

## Dimension scores

| Dimension | Score | Evidence and justification |
|---|---:|---|
| **D1: Knowledge Delta** | **18/20** | High-value specifics include project-local code execution (`SKILL.md:22–28`), managed-family removals (`125–132`), and committed-versus-rollback recovery (`174–180`). Repeated instructions consume avoidable tokens; see finding 2. |
| **D2: Mindset + Appropriate Procedures** | **15/15** | The preflight questions (`60–67`) shape reasoning around trust, migration, and artifact placement. The workflow supplies non-obvious procedures for whole-list edits, runner choices, and fingerprint-bound approval (`109–169`). |
| **D3: Anti-Pattern Quality** | **15/15** | Specific prohibitions explain consequences: hand edits bypass validation (`278–279`), inventory executes checkout JavaScript (`280`), and v1 can overwrite v2 runner selection (`285–287`). |
| **D4: Specification Compliance** | **15/15** | Valid frontmatter (`1–4`). The description identifies capabilities, explicit triggering requests, searchable paths, and the boundary with `gsd-settings`/`gsd-config`. |
| **D5: Progressive Disclosure** | **15/15** | The v1 reference is restricted to that flow (`12–13`); runner details have explicit scenario-based loading instructions (`222–225`). Neither reference is orphaned, and the main file remains below 500 lines. |
| **D6: Freedom Calibration** | **12/15** | Fragile writes appropriately require review, exact dry-run rows, and a separate approval turn (`134–142`). Offline/no-write handling lacks an equally explicit boundary, while elicitation is unnecessarily rigid; see findings 1 and 3. |
| **D7: Pattern Recognition** | **10/10** | Appropriate Tool/Process combination: command examples, phased checkpoints, failure-state routing, narrowly loaded references, and a concise command index (`58–189`, `257–268`). |
| **D8: Practical Usability** | **14/15** | Strong coverage of stale inventories, unresolved choices, rollback failures, inactive `.new` files, and changed follow-ups. The v1 detector-output instructions need exact JSON field handling; see finding 4. |

## Findings

### Critical

None.

### Important

**1. Offline/no-write requests have disclosure guidance but no explicit stop-or-consent branch.**  
**Location:** `SKILL.md:71` — “say so before running it offline or on a no-write request.”

Lines `69–74` acknowledge cache writes and possible network activity, but disclosure alone does not authorize those effects when the user prohibited them. No safe alternative or refusal branch is specified.

**Fix:** Explicitly stop before `inventory` when its effects conflict with the request. Ask permission to relax the restriction, or explain that fresh inventory cannot be produced under it. Do not imply that `--refresh` being absent makes inventory offline or non-writing.

### Minor

**2. Several common-mistake rows duplicate complete workflow instructions.**  
**Locations:** `SKILL.md:295–296` and `SKILL.md:301–304`.

These repeat stdout capture (`69–78`), scratch placement (`64–67`), cleanup handling (`177–180`), dry-run presentation (`134–142`), and exact `approve_with` execution (`157–161`). The repetition adds little new diagnostic knowledge.

**Fix:** Keep troubleshooting rows that contribute distinct symptoms or remedies; consolidate the repeated safeguards into their primary workflow locations.

**3. The four-question rule unnecessarily re-asks already supplied choices.**  
**Location:** `SKILL.md:81` — “Ask the user, in one message, four questions — nothing else.”

The unconditional instruction also applies when the initiating request already specifies profile, rigor, review, and execution choices. That adds friction to a skill advertised as the faster configuration path without protecting a fragile operation.

**Fix:** Reuse explicit answers already provided and ask only for missing or ambiguous choices. Preserve all subsequent review and write-approval gates.

**4. The v1 reference describes detector results as scalars instead of identifying their JSON fields.**  
**Locations:** `references/v1-path.md:23–24`.

The reference says to skip when the path detector “prints `null`” and to use “that boolean” from frontend detection. The bundled implementation actually emits `{"path": null}` and `{"frontend_present": false}` (`ai_kit_gsd_curated_config/cli.py:433`, `:439`). A literal interpretation can miss the skip condition or pass the wrong value.

**Fix:** Specify: skip when `.path` is null; otherwise pass `.path`. Pass `.frontend_present` as lowercase `true`/`false` to both UI flags.

## Top three improvements

1. Add an explicit offline/no-write refusal or permission branch.
2. Document the v1 detectors’ exact JSON fields.
3. Remove duplicated troubleshooting instructions while retaining distinct recovery knowledge.

CURRENT 114/120
CRITICAL 0
IMPORTANT 1

DIGEST b924ac84e1d6d3c9
