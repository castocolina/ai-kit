# Skill evaluation: ai-kit-gsd-curated-config

**106/120 — B (Good).** Strong Tool/Process skill with substantial GSD-specific knowledge, explicit approval gates, and unusually clear permission and rollback disclosures. Estimated **Expert:Activation:Redundant ratio: 80:15:5**.

Read the full requested rubric, all 352 lines of `SKILL.md`, both references (`v1-path.md`: 47 lines; `runner.md`: 65 lines), and the requested diff. No bundled `scripts/` directory exists. Checked the changed validation paths against checkout-local gsd-core source.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Valuable resolver, migration, permission, and recovery knowledge; some repetition. |
| D2: Mindset + Procedures | 14/15 | Strong trust-first reasoning and domain-specific sequencing; recovery loses reference identity in one case. |
| D3: Anti-Pattern Quality | 15/15 | Specific prohibitions with concrete consequences and alternatives. |
| D4: Specification Compliance | 15/15 | Valid quoted frontmatter; description covers capabilities, scenarios, and trigger phrases. |
| D5: Progressive Disclosure | 12/15 | Both references have clear conditional loading; the main body still repeats several safeguards. |
| D6: Freedom Calibration | 12/15 | Appropriate approval constraints, but the resolver guarantee exceeds validation coverage. |
| D7: Pattern Recognition | 9/10 | Clear Tool/Process structure; dense exception handling slightly obscures the primary path. |
| D8: Practical Usability | 11/15 | Actionable commands and failure handling; stale-inventory and recovery-source gaps remain. |
| **Total** | **106/120** | **Good, with one Important finding.** |

### Findings

Paths below are relative to `skills/ai-kit-gsd-curated-config/`.

1. **Important — Newly set references bypass the live resolver check.**  
   **Evidence:** `SKILL.md:241–246,266–273` promises resolvable wiring and pre-write refusal. However, `ai_kit_gsd_curated_config/plan_io.py:697–701` checks `op == "set"` through inventory-based `skip_reason`; only kept references reach the live checks. `ai_kit_gsd_curated_config/skills.py:226–235` uses recorded location and escape facts, and `ai_kit_gsd_curated_config/apply.py:92–100` translates the same recorded row without checking the filesystem.  
   **Impact:** Inventory a healthy global skill, then remove it or retarget its `SKILL.md` outside permitted roots: a newly set entry can pass preflight and be written even though gsd-core skips it. The new live-check tests cover kept references, not this normal recommendation path.  
   **Fix:** Translate set values to their final references and validate them live before dry-run/apply, using the same checks as kept references. Add removal and retargeting tests for `op == "set"`.

2. **Minor — Recovery preserves names, not necessarily the healthy reference’s source.**  
   **Evidence:** `SKILL.md:262–265` says the printed fix “keeps every healthy reference.” But `ai_kit_gsd_curated_config/plan_io.py:713–730` reduces `global:foo` to `foo`, while `ai_kit_gsd_curated_config/skills.py:136–153` prefers a project copy.  
   **Impact:** If both project and global copies of `foo` exist, repairing another skipped skill can switch a healthy `global:foo` to `skills/foo`. That changes the instructions loaded, despite the preservation claim.  
   **Fix:** Detect ambiguous round-trips and require an explicit source decision, as already done for namespaced references. Until supported, qualify the preservation claim and warn about source changes.

3. **Minor — Repeated safeguards dilute the otherwise strong disclosure structure.**  
   **Evidence:** Dry-run approval appears at `SKILL.md:144–152`, `313–316`, and `340`; `.new` handling appears at `232–235` and `327`, with the detailed procedure in `references/runner.md:57–64`.  
   **Impact:** The main body spends extra context repeating rules rather than improving navigation.  
   **Fix:** Keep the authoritative rule at its workflow step and shorten later occurrences to cross-references; retain only brief high-risk reminders in NEVER.

The changes correctly replace silent trust-root decline with explicit refusal and document the widened, machine-specific trust boundary. The remaining Important gap is that live resolver parity applies to kept references but not newly set ones.

No commands that write files or tests were run; no credential files were read. Runtime behavior remains statically assessed, not execution-verified.

DIGEST 9ae11c2977b8de1d
CURRENT 106/120
CRITICAL 0 IMPORTANT 1
