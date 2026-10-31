Judge: my-referee-one
Reviewed-sha256: 7a8c37b5cbcbe91d4d4326f05113ce1aa111481093e50b9afa9606b85192cf02
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=764s out=486572 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 94
Critical: 2
Important: 3

## Dimension scores

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Strong repository-specific knowledge: ownership-aware cleanup, hook token restrictions, runner preparation, and retry semantics. Some safeguards are repeated unnecessarily. |
| D2: Mindset + Appropriate Procedures | 13/15 | Explains important decisions, particularly fresh resolution versus same-lane recovery. However, the handoff lacks a working-directory invariant. |
| D3: Anti-Pattern Quality | 14/15 | Specific, consequential prohibitions with reasons: no `skip`, no post-failure reselection, no raw vendor hook, and no implicit trust. |
| D4: Specification Compliance | 15/15 | Valid frontmatter, compliant name, and a description containing specific capabilities, activation scenarios, and searchable terms. |
| D5: Progressive Disclosure | 8/15 | The 543-line main file exceeds the recommended size. The 63-line reference has clear optional loading guidance, but holds history while substantial operational detail remains inline. |
| D6: Freedom Calibration | 10/15 | Appropriately precise for configuration and execution, but successful cleanup is incorrectly treated as proof of native dispatch. |
| D7: Pattern Recognition | 9/10 | Clear Process/Tool pattern with ordered stages and failure branches. |
| D8: Practical Usability | 7/15 | Detailed common-case instructions, undermined by two wrong-dispatch paths, inconsistent fallback cleanup, and a missing cross-call variable. |
| **Total** | **94/120** | **Grade C — substantial expert content, but not ready for unattended execution.** |

Approximate knowledge ratio: **Expert 75% / Activation 15% / Redundant 10%**.

## Findings

### 1. Critical — The GSD handoff is not bound to the supplied project root

**Package:** `skills/ai-kit-spec-execute-gsd/SKILL.md:474–482`

Steps 1–2 operate on the supplied `$CWD`, but Step 3 invokes GSD with only `$PHASE_ID`. Nothing requires the host session’s workspace to match `$CWD`, and passing `--cwd` to earlier Python commands does not change the workspace of a subsequent skill invocation.

The named repository command describes execution of all plans in the phase and resolves context inside its own workflow; it does not receive this adapter’s project-root argument (`.claude/commands/gsd-execute-phase.md:24–26,62`). A caller targeting another checkout can therefore configure one project and execute the same-numbered phase in another.

**Fix:** Before any writes, require the host workspace and active GSD command installation to match `$CWD`. If they differ, stop and instruct the owner to invoke the skill from the intended workspace; do not assume the later skill call inherits the Python command’s `--cwd`.

### 2. Critical — Cleanup success does not establish native-only execution

**Package:** `skills/ai-kit-spec-execute-gsd/SKILL.md:196–199,333–339`

The `native_tier` branch declares that execution is not cross-AI and proceeds after cleanup. But cleanup intentionally preserves user-owned workflow values.

Repository confirmation: `clear-workflow-keys` only clears keys satisfying `is_adapter_owned(...)` (`skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py:248–264`). If an enabled, user-owned `cross_ai_command` already exists and the plans opt into cross-AI, cleanup succeeds without disabling that hook. Under the package’s own delegation rules at lines 207–212, GSD can still execute it despite the supposedly native resolution.

**Fix:** After cleanup, inspect the effective workflow configuration. If an enabled hook remains, stop for an explicit owner decision rather than claiming native dispatch. Preserve the user’s configuration; do not silently erase it.

### 3. Important — Probe-time quota exhaustion bypasses the required cleanup

**Package:** `skills/ai-kit-spec-execute-gsd/SKILL.md:147–151`

This branch writes resumable state and stops before Step 2. Elsewhere, the skill requires every `fallback_notice` to stop **after cleanup** and specifically requires mode-transition cleanup whenever the mode is `fallback_notice` (lines 29–30 and 333–339).

Consequently, a quota-exhausted run can leave a previous adapter-owned cross-AI hook active. The persisted configuration does not satisfy the advertised mode-transition invariant.

**Fix:** Run ownership-aware cleanup on this branch before completing the stop. Preserve the resumable record, and surface cleanup failures rather than reporting only quota exhaustion.

### 4. Important — The wake block depends on a value never recorded across shell calls

**Package:** `skills/ai-kit-spec-execute-gsd/SKILL.md:444–446`

The wake path uses `$GSD_SKILL_DIR`, but Step 0 prints and records only `GSD_SHIM`, `TOOLS_PY`, and `CURATED_PY` (lines 73–80). The package explicitly states that separate Bash calls lose their variables and that later substitutions must use printed values (lines 82–85).

Following that protocol leaves no recorded `$GSD_SKILL_DIR` for this block. Executing it with the variable unset produces a relative sibling lookup, normally causing the requested multi-plan wake to be skipped as “not installed.”

**Fix:** Print and record `GSD_SKILL_DIR` in Step 0, or derive the wake path from the already-recorded `GSD_SHIM`.

### 5. Important — Step 3 can write machine-specific paths into a tracked phase artifact

**Package:** `skills/ai-kit-spec-execute-gsd/SKILL.md:374,398–405`

Step 3 appends `prepare-tooling` output directly to the supplied phase file. That command passes resolved tooling paths unchanged into its guidance builder (`skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py:285–293`).

The repository already distinguishes this from tracked-safe guidance: `_tracked_tooling_guidance` maps paths to home-relative notation or omits them explicitly because its output enters a tracked file (`skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py:333–354`). Step 3 bypasses that protection, so tracked plans can acquire nonportable machine-local paths.

**Fix:** Use the tracked-safe path normalization for guidance appended to phase artifacts, or keep machine-local guidance outside tracked files and explicitly pass it to execution.

### 6. Minor — Progressive disclosure moves history rather than the operational bulk

**Package:** `skills/ai-kit-spec-execute-gsd/SKILL.md:232–322,368–543`; `skills/ai-kit-spec-execute-gsd/references/dispatch-notes.md:31–63`

The reference is appropriately labelled optional; it should not require mandatory loading merely to satisfy a checklist. The structural weakness is that the main file contains lengthy shell implementations and repeated stop rules, while the reference mostly carries rationale and history.

**Fix:** Keep the dispatch decision tree, safety invariants, and handoff contract in `SKILL.md`. Move substantial command recipes into task-specific references with mandatory loading triggers at their execution points, and consolidate repeated safeguards.

**Not checked:** Live execution, scheduler behavior, CLI availability, or sandbox guarantees; this was a read-only source review.  
**Principal risk:** A nominally native handoff can execute in the wrong workspace or through a surviving cross-AI hook.
