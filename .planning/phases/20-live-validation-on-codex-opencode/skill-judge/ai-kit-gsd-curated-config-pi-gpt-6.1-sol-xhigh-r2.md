# CURRENT skill evaluation

**Score: 113/120 — A (94.2%)**  
**Pattern:** Process + Tool, with conditional reference navigation.  
**Approximate knowledge ratio:** Expert 80% / Activation 15% / Redundant 5%.

Read `SKILL.md` and both reference files completely. This was a read-only, static review; no commands or runtime tests were executed.

Paths below are relative to `skills/ai-kit-gsd-curated-config/`.

## Dimension scores

| Dimension | Score | Assessment |
|---|---:|---|
| **D1: Knowledge Delta** | **18/20** | High-value, package-specific knowledge: inventory side effects, whole-family removals, trusted-root merging, inactive `.new` artifacts, and committed-versus-rolled-back states (`SKILL.md:69–74, 114–132, 171–189`). Some safeguards and readiness details are repeated across sections and references. |
| **D2: Mindset + Appropriate Procedures** | **14/15** | Transfers useful reasoning: establish checkout trust, identify migration provenance, distinguish reachability from health, and separate approval from execution (`SKILL.md:60–67, 134–168, 235–244`). The four model profiles lack decision guidance, especially how adaptive differs from rigor. |
| **D3: Anti-Pattern Quality** | **15/15** | Excellent specific prohibitions with consequences: forced command values bypass guards, v1 overwrites v2 routing, manual edits bypass validation, and restoring after committed cleanup warnings undoes success (`SKILL.md:268–302`). These are genuine operational landmines rather than generic warnings. |
| **D4: Specification Compliance** | **15/15** | Valid frontmatter, matching lowercase-hyphenated name, and a description containing functionality, explicit activation scenarios, searchable paths, and cross-AI terminology (`SKILL.md:1–4`). |
| **D5: Progressive Disclosure** | **14/15** | Manageable 313-line main file; references are short and conditionally triggered. The v1 reference explicitly says to load it only for that flow (`SKILL.md:12–13`); runner loading scenarios are explicit (`SKILL.md:221–224`). Some runner readiness detail remains duplicated in the main command table. |
| **D6: Freedom Calibration** | **15/15** | Appropriately restrictive for config mutation: validated subcommands, explicit choices, full-key dry-run disclosure, a separate approval turn, fingerprint-bound follow-ups, and recovery-marker preservation (`SKILL.md:97–178, 272–287`). |
| **D7: Pattern Recognition** | **10/10** | Strong Process/Tool hybrid: six clear stages, concrete commands, checkpoints, failure branches, a command reference, and secondary-flow navigation (`SKILL.md:58–189, 255–266`). |
| **D8: Practical Usability** | **12/15** | Comprehensive handling of installation failures, stale inventory, rollback failures, cleanup warnings, runner uncertainty, and degraded v1 execution. Deductions concern the cross-flow host-review guarantee and an inconsistent flag inventory, detailed below. |

## Findings

### Important

1. **The host-review prohibition is stated universally but is only enforced by the v2 path.**  
   **Lines:** `SKILL.md:216–219`; `references/v1-path.md:18–20, 38–39`.

   “The host CLI is never a review lane” conflicts with the kept v1 instructions to pass the detected reviewer unchanged. Static implementation inspection confirms that v1 can select the host: `ai_kit_gsd_curated_config/preference_match.py:47, 125–131` supplies a native `claude`/`opus` fallback, and `ai_kit_gsd_curated_config/cli.py:364–400` adds the selected reviewer without host exclusion.

   **Fix:** Qualify the guarantee as **v2-only** and explicitly disclose v1’s possible same-host/native fallback, or enforce the prohibition in v1 as well. Otherwise an agent can incorrectly describe same-host review as independently cross-AI.

### Minor

1. **Model-profile selection lacks the domain-specific distinction needed for an informed answer.**  
   **Lines:** `SKILL.md:81–91`.

   Rigor receives concrete cost and behavior explanations, but `quality / balanced / budget / adaptive` are merely listed. “Adaptive recommended” does not explain its interaction with rigor.

   **Fix:** Add a compact profile comparison or a targeted reference trigger explaining each profile’s effect and how profile and rigor differ.

2. **Runner readiness and approval safeguards are repeated beyond useful activation reminders.**  
   **Lines:** `SKILL.md:265, 272–287, 299–302`; `references/runner.md:32–40`.

   The main command table repeats much of the conditionally loaded runner readiness matrix. Several common-mistake rows also restate adjacent workflow and NEVER rules nearly verbatim.

   **Fix:** Keep the safety checkpoints in the workflow, shorten the command-table entry to its contract and reference link, and retain only mistake rows that add a distinct symptom or recovery action.

3. **The runner reference says “three flags” while describing four distinct options.**  
   **Lines:** `references/runner.md:12–24`.

   The section lists `--outer-timeout`, `--prepend-file`, and `--codex-sandbox`, but also describes the independently named `--no-preamble`.

   **Fix:** Document all four explicitly, or describe them as three feature groups rather than three flags.

CURRENT 113/120
CRITICAL 0
IMPORTANT 1
