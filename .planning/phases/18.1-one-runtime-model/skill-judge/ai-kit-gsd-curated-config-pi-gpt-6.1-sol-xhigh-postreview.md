## Assessment

**CURRENT improves on BASELINE: 112/120 versus 106/120.** It preserves the domain-specific safeguards while improving entrypoint selection, degraded-success reporting, runner-permission distinctions, and conditional reference loading.

Read both skills completely and both CURRENT references. BASELINE’s supplied directory has **no `references/` directory**; its guidance is self-contained. Verification was read-only source inspection, not execution.

| Structure | BASELINE | CURRENT |
|---|---|---|
| `SKILL.md` | 295 lines | 285 lines |
| References | None present | `runner.md`: 53 lines; `v1-path.md`: 40 lines |
| Pattern | Tool + Process | Tool + Process, with conditional navigation |
| Estimated Expert:Activation:Redundant ratio | 80:17:3 | 83:15:2 |
| Grade | **B — 88.3%** | **A — 93.3%** |

## Scores by rubric dimension

Here, **B** means BASELINE’s `SKILL.md`; **C** means CURRENT’s `SKILL.md`.

| Dimension | Max | BASELINE | CURRENT | Evidence and justification |
|---|---:|---:|---:|---|
| **D1: Knowledge Delta** | 20 | **18** | **18** | Both supply substantial non-generic knowledge: inventory digests, pseudo-keys, trusted-root merging, apply markers, and approval fingerprints. CURRENT adds useful runner distinctions. Neither earns full marks because safeguards recur across the workflow, NEVER list, and mistakes table. |
| **D2: Mindset + Appropriate Procedures** | 15 | **13** | **14** | Both combine preflight questions with the domain-specific inventory → recommendation → choice resolution → dry-run → apply sequence. CURRENT strengthens the reasoning behind fail-closed dispatch: “nothing proves the first one wrote nothing” (C:166–169). A compact initial decision tree would make normal setup, legacy setup, and repair easier to distinguish. |
| **D3: Anti-Pattern Quality** | 15 | **15** | **15** | Both explain concrete hazards rather than offering generic caution: hand edits bypass validation; habitual `--force` bypasses command guards; v1 can replace v2’s execution configuration; restoring after committed cleanup warnings undoes successful work. |
| **D4: Specification Compliance** | 15 | **15** | **15** | Both have valid required frontmatter and a compliant name. Their identical description explicitly covers WHAT, WHEN, and searchable triggers including `.planning/config.json`, GSD-agent skill wiring, and cross-AI runners. |
| **D5: Progressive Disclosure** | 15 | **11** | **14** | BASELINE always loads the legacy command sequence and runner-maintenance details. CURRENT conditionally routes to `references/v1-path.md` (C:12–13) and `references/runner.md` (C:199–202). Explicit “do not load either reference during ordinary v2 setup” guidance would complete the layering. |
| **D6: Freedom Calibration** | 15 | **13** | **14** | Both appropriately constrain fragile configuration writes and approval commands while leaving model choices to the user. CURRENT improves version matching by selecting the adjacent entrypoint first (C:44–56), and distinguishes full-permission v2 execution from sandboxed v1 Codex execution (C:180–191). Its reference’s validation command still needs hook-specific arguments. |
| **D7: Pattern Recognition** | 10 | **9** | **9** | Both clearly apply an appropriate Tool/Process pattern: exact commands, decision branches, checkpoints, recovery states, and anti-patterns. CURRENT’s navigation is useful, though the main body still mixes the primary workflow with substantial operational reference material. |
| **D8: Practical Usability** | 15 | **12** | **13** | Both cover rollback, stale plans, unresolved choices, and follow-up approval. CURRENT fixes BASELINE’s generic v1 exit-zero interpretation and replaces mandatory full-JSON output (B:293–295) with decision-preserving summaries (C:278–285). Remaining reference inaccuracies and diagnostic gaps are listed below. |
| **Total** | **120** | **106** | **112** | **CURRENT gains six points without a rubric-dimension regression.** |

## CURRENT findings

**Critical:** None.  
**Important:** None.

### Minor

1. **The flag overview incorrectly claims an exhaustive count.**  
   **Location:** `skills/ai-kit-gsd-curated-config/references/runner.md:12–20`  
   “Template 3 understands three flags” is inaccurate: the same section mentions the additional `--no-preamble`, and the bundled parser supports numerous other flags. Change this to **“Key flags relevant to these hooks”**, or identify the section as a selected subset.

2. **The live-timeout lookup omits supported scoping and fallback behavior.**  
   **Location:** `skills/ai-kit-gsd-curated-config/references/runner.md:38–40`  
   The documented paths omit `GSD_PROJECT`. The bundled runner also falls back to the root configuration when a workstream lacks the timeout key, then uses a 300-second default when no usable value exists (`skills/ai-kit-spec-review/references/cross-ai.mjs:439–450`). Include those branches so timeout troubleshooting points at the configuration actually read.

3. **The post-merge diagnostic assumes a CONFIG-backed v2 hook.**  
   **Location:** `skills/ai-kit-gsd-curated-config/references/runner.md:45–51`  
   Bare `node .planning/scripts/cross-ai.mjs --print-argv` does not reproduce v1 hooks that supply runtime, model, and sandbox arguments on the command line. Such runners can print `NO MODEL`; `--print-argv` nevertheless exits successfully. Instruct agents to preserve the configured hook’s arguments when adding `--print-argv`, and explicitly reject `MISSING`/`NO MODEL` for intended targets.

BASELINE 106/120
CURRENT 112/120
CRITICAL 0
IMPORTANT 0
