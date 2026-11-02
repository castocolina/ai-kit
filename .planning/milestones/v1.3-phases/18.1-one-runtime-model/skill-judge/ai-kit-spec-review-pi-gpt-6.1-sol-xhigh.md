# Comparative skill evaluation

**CURRENT is a modest improvement, not a complete reliability fix.** It adds useful runtime/model routing knowledge and clearer uncertainty handling, while retaining several execution-contract defects shared with BASELINE.

This was a **read-only, static evaluation** of both `SKILL.md` files and their `references/` directories. Commands and live-verification claims were not executed.

Both versions follow a **Process + Tool** pattern. Estimated knowledge mix, excluding executable assets: BASELINE **75% Expert / 15% Activation / 10% Redundant**; CURRENT **78% / 14% / 8%**.

## Scores by dimension

References below are relative to each version’s `ai-kit-spec-review/` directory.

| Dimension | BASELINE | CURRENT | Evidence and justification |
|---|---:|---:|---|
| **D1: Knowledge Delta** | **17/20** | **18/20** | Strong domain knowledge: document-owned worktree roots, archetype ceilings, framework-owned revision, and report persistence. CURRENT adds valuable native/subprocess/custom distinctions and explains `unverified` precisely (`SKILL.md:231–271`). Repeated rationales and historical failure narratives prevent maximum scores. |
| **D2: Mindset + Appropriate Procedures** | **14/15** | **14/15** | “Archetype is a ceiling” and lifecycle-aware scoping transfer expert judgment, not merely mechanics (`SKILL.md:78–156`, both). Exact dispatch and revision procedures complement that thinking. Entry-flow and iteration-accounting inconsistencies remain. |
| **D3: Anti-Pattern Quality** | **15/15** | **15/15** | Excellent specific prohibitions with consequences: wrong-checkout grounding, context contamination, parallel editing, premature cleanup, and unapproved configuration trust. These are concrete operational landmines rather than generic warnings. |
| **D4: Specification Compliance / Description** | **15/15** | **15/15** | Valid name/frontmatter. The description supplies WHAT, WHEN, framework names, review terminology, invocation phrases, and flags (`SKILL.md:1–4`, both). Activation guidance is present in metadata, not confined to the body. |
| **D5: Progressive Disclosure** | **11/15** | **11/15** | Mandatory reference-loading triggers and explicitly optional navigation resources are good. However, the bodies remain **533 and 553 lines**, with substantial dispatch templates and repeated explanations still loaded unconditionally. Move more execution detail behind the existing triggers. |
| **D6: Freedom Calibration** | **11/15** | **12/15** | Strict report paths, sequencing, trust gates, and fail-closed parsing appropriately constrain fragile orchestration. CURRENT improves calibration by distinguishing unchecked models from verified routes. Exact host-specific APIs and incomplete fallback contracts still constrain portability incorrectly. |
| **D7: Pattern Recognition** | **8/10** | **8/10** | Both have a recognizable phased process with tool-oriented branches and checkpoints. The lengthy preparation section, repeated rules, and embedded implementation detail weaken the otherwise appropriate pattern. |
| **D8: Practical Usability** | **8/15** | **8/15** | Both cover many realistic failures and framework routes. CURRENT improves runner/profile guidance, but namespace, fallback initialization, completion detection, mixed-route ownership, and iteration-cap gaps still require the executing agent to repair the instructions. |
| **Total** | **99/120** | **101/120** | Both **Grade B**: strong knowledge content, but execution reliability needs attention. |

## Reference inventory

Sizes are in lines; paths are relative to `references/`.

| File | BASELINE | CURRENT |
|---|---:|---:|
| `apply-findings.md` | 131 | 131 |
| `cross-ai-dispatch.md` | 230 | 278 |
| `loop-diagram.md` | 69 | 69 |
| `routing-table.md` | 20 | 20 |
| `tooling-guidance.md` | 25 | 25 |
| `cli-profiles/claude.md` | 43 | 45 |
| `cli-profiles/codex.md` | 57 | 47 |
| `cli-profiles/cursor-agent.md` → `cursor.md` | 139 | 121 |
| `cli-profiles/grok.md` | 63 | 53 |
| `cli-profiles/opencode.md` | 50 | 44 |
| `ranking-weights.toml` | 71 | 71 |
| `cross-ai.mjs` | approximately 2,500 | approximately 3,000 |

The executable runner and ranking data are legitimate packaged assets; their length is not itself a context-budget defect.

## CURRENT findings

### Critical

None identified.

### Important

1. **The mandatory generic-fixer prompt invokes the wrong skill name.**  
   **Location:** `skills/ai-kit-spec-review/references/apply-findings.md:38`  
   The VERBATIM prompt invokes `review-spec-fixer`, but the main skill’s constant and the installed sibling identify `ai-kit-spec-review-fixer`. Following the reference literally can prevent the default fix route from loading its required instructions. Update the prompt and the stale name at line 17.

2. **The no-cross-AI shortcut has an incomplete initialization contract.**  
   **Locations:** `skills/ai-kit-spec-review/SKILL.md:164`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:107–120`  
   The body permits skipping the reference, although that reference owns initialization of `RUN_TMP_DIR`, reviewer state, and tooling inputs consumed later. Even when loaded, its manually constructed fallback has no `route`, while Step 1 branches on `route`. Make minimal bootstrap unconditional and explicitly designate the fallback as native; skip only cross-AI discovery and resolution.

3. **Host-neutral native routing still depends on host-specific invocation APIs.**  
   **Locations:** `skills/ai-kit-spec-review/SKILL.md:240–250,346`; `skills/ai-kit-spec-review/references/apply-findings.md:26–29`  
   CURRENT describes native operation across hosts, but its VERBATIM reviewer prompt requires a `Skill` tool, and revision requires `Agent` plus `sonnet`. There is no executable alternative or capability-failure branch for hosts lacking those APIs. Provide a file-read invocation contract and capability-gated dispatch, or clearly stop with the required host capability rather than implying universal native availability.

4. **A stable report file is not proof that background dispatch finished.**  
   **Location:** `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:230–232`  
   The prescribed polling condition is file existence plus stopped growth. Shell redirection creates the file immediately; it can remain empty throughout a long review. This can advance to merging/parsing while the reviewer is still running. Wait for process/task completion and inspect its exit status before consuming the report.

5. **The slash-command revision branch does not increment the iteration counter.**  
   **Location:** `skills/ai-kit-spec-review/references/apply-findings.md:111–115`  
   This branch returns to Step 1 without the increment explicitly required by the generic-fixer and native-skill branches. Literal execution can repeatedly revise and review without reaching the configured cap. Centralize iteration advancement after successful revision/validation, exactly once per round.

6. **Mixed-archetype dispatch does not enforce the promised ownership boundary.**  
   **Locations:** `skills/ai-kit-spec-review/references/apply-findings.md:22,41–42`  
   The reference says the generic fixer handles only direct-edit findings before the native-owned route runs. Its prompt nevertheless receives the entire document set and entire report, with no allowed-finding or archetype restriction. For fused documents, that permits the generic fixer to rewrite native-owned material first. Pass an explicit finding scope or a filtered report while preserving the full report as evidence.

### Minor

1. **Successful persistence branches point past mandatory preparation.**  
   **Location:** `skills/ai-kit-spec-review/SKILL.md:31–32`  
   “Continue to Step 1” conflicts with the intervening root resolution, framework classification, lifecycle scoping, and reviewer resolution. Point these rows to Step 0.1.

2. **Missing-path behavior contradicts automatic document discovery.**  
   **Locations:** `skills/ai-kit-spec-review/SKILL.md:12,146–147`  
   Inputs require asking for paths and stopping, while lifecycle scoping specifies reviewing all existing documents when no paths were supplied. Define one entry rule: explicit paths versus a discovery request.

3. **Progressive disclosure leaves avoidable material in the main body.**  
   **Locations:** `skills/ai-kit-spec-review/SKILL.md:273–440,530–553`  
   Long prompt templates, repeated report-path explanations, and the extended cleanup incident narrative increase always-loaded context. Keep the branch contracts and cleanup invariant in `SKILL.md`; move detailed templates and historical rationale into conditionally loaded references.

BASELINE 99/120
CURRENT 101/120
CRITICAL 0
IMPORTANT 6
