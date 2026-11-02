# Phase 18: Cross-AI, Skills & Apply Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-23
**Phase:** 18-cross-ai-skills-apply-pipeline
**Mode:** --analyze (a trade-off analysis was presented before each question). Part of the
discussion was held in Spanish at the user's choice; this log is in English per the project
constraint.
**Areas discussed:** Reviewer lanes, Skill wiring, Old CLI removal (→ v1 coexistence),
Apply follow-ups

---

## Reviewer lanes

**Question: how many cross-AI reviewer lanes?**
- 1 in Standard, 2 in Rigorous (a third provider when available) ✓
- Always 1
- Always 2 when possible

## Skill wiring

**Question: what reference form should be used?**
- The first options offered were native gsd forms or absolute paths.
- The user asked: "Shouldn't it just be the name, and the host recognizes it whether global or
  local?"
- Evidence shown: gsd-core `init.cjs` treats a bare name as a project path and skips global
  skills without `global:`.
- Follow-up answer: the user sees bare names, and the skill translates them internally ✓

**Question: how are missing recommended skills (ponytail) handled?**
- The user's answer: "Just add it if it exists; otherwise don't mention it." SKL-03 is
  amended accordingly.

**Question: what is the per-agent limit?**
- The user asked: "Is there even a limit?" The answer given: gsd has none; the cap exists
  because each skill injects its SKILL.md into every invocation of that agent.
- Follow-up options: no cap; keep 3; a cap per rigor ✓ (example 2/3/5)

## Old CLI removal → v1 coexistence

- The first question was answered with "I don't know which subcommands you mean". An
  explanation was requested, and the 11 v1 subcommands were then explained step by step.
- The user's answer: "They must not be deleted; that needs reviewing, since I haven't tested
  anything, and from what you describe it tried to cover a lot and did little."
- Follow-up options: review v1 first, then decide; coexist without touching v1 ✓; let me explain
- EVAL-06 is amended: no module removal.

## Apply follow-ups

- The first attempt was rejected by the user, who had not yet received the subcommand
  explanation. It was re-asked after the explanation.
- **Follow-ups:** one grouped confirmation ✓ / print only / one by one
- **Backups:** keep the last 3 ✓ / keep all

## Claude's Discretion

- The exact skill caps per rigor.
- The backup timestamp format.
- The prompt wording.
- The v1/v2 module layout.
- `plan-set` validation strictness.

## Deferred Ideas

- The future of the v1 CLI → a later milestone, after v2 is evaluated.

---

# Update 2026-10-14 (assumptions mode)

**Mode:** assumptions (`--analyze --all --batch`), jev screening, best over easy, CodeGraph
**Input:** `18-SPEC.md` (3b46df5, amended) plus the locked D-01..D-14.

The analyzer was `gsd-assumptions-analyzer` (sonnet), with jev-fast-decision through `agent_skills`, best over easy in its brief, and CodeGraph instructions. It made 95 tool calls, ran live scratch checks against gsd-core 1.16 and the cached 1.13.0 package, and made no network calls. Token files were not read.

## Live facts that changed the plan
- The cached gsd-core 1.13.0 ignores `config-set --dry-run` and writes, so a dry run validates with `isValidConfigKey` only (D-18).
- A gsd-tools revert leaves `"model_overrides": {}` and reformats the file, so a byte restore is needed (D-21).
- `config-path --ws` returns the workstream's config, which is where backups go (D-19).
- The registry: antigravity's model key is `review.models.agy`, `review.effort.cursor` is invalid, and 1.13 had a `gemini` lane (D-24).
- `skill-manifest` misses host roots, while `skills-root <host>` is right per host (D-31).
- gsd-core emits plugin directives without an existence check (D-32).
- The jev skill has no health endpoint, and its default URL is remote Zen (D-36).
- The installer with no location flag and no TTY installs globally for Claude (D-37).
- `effort sync` writes to the global agents directory for codex/opencode without `--config-dir` (D-38).
- `git status --porcelain` misses a re-edit of a dirty file (D-27).
- The dogfood script reads as user-edited (hash mismatch).

## jev screening

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| B01 dispatch | dispatch_table 0.41 (fb) | dispatch_table 0.89 | D-15 |
| B02 write path | legacy_widened 0.56 (fb) | shared_strict 0.96 | D-16 |
| B03 plan-set data | needs_choice_only 0.66 (fb) | require_inventory 0.69 (fb) | **Own reasoning:** require `--inventory` plus a digest check; one source of truth, and decided-slot pins are checked too (D-17, ledger) |
| B04 backup dedupe | always_new 0.64 (fb) | skip_identical 0.77 | D-20 (amends D-06's edge) |
| B05 restore | hybrid 0.43 (fb) | byte_restore_exception 0.92 | D-21 (SPEC prohibition amended) |
| B06 lanes | registry_runtime 0.67 (fb) | registry_runtime 0.97 | D-24 |
| B07 pi models | needs_choice 0.79 | parser_now 0.79 (second opinion) | **Laya overridden:** Phase 19 B expects a pi pick; SPEC-05 moved to Phase 18 (D-25) |
| B08 hash scope | raw_bytes_with_config 0.38 (fb) | raw_bytes_with_config 0.81 | D-26 |
| B09 artifacts | typed_artifacts 0.56 (fb) | typed_artifacts 0.98 | D-28 |
| B10 tree change | temp_index_tree 0.41 (fb) | temp_index_tree 0.79 | D-27 |
| B11 timeout | bake_and_min_live 0.54 (fb) | bake_and_min_live 0.79 | D-29 |
| B12 skills root | skills_root_cli 0.50 (fb) | skills_root_cli 0.56 (fb) | Both agree at low confidence; the evidence (skill-manifest 74/134) decides (D-31) |
| B13 plugin visibility | installed_only 0.55 (fb) | installed_enabled_exists 0.88 | D-32 |
| B14 "or" rule | both_agents 0.91 | one_agent_curated 0.55 (fb, second opinion) | **Own reasoning:** verifier only; the planner already holds core ponytail, and the MVP cap is 2 (D-33, ledger) |
| B15 trusted roots | per_skill_dir 0.50 (fb) | prefer_project_path 0.53 (fb) | **Own reasoning:** prefer the project path, else per-skill `~/` roots (D-34, ledger) |
| B16 jev detection | probe_example 0.58 (fb) | tcp_reach_and_key 1.00 | D-36 (amends R11 and 24 R5) |
| B17 effort sync | explicit_dirs_preview 0.63 (fb) | explicit_dirs_preview 0.98 | D-38 |

## Cross-phase effects
- SPEC-05 (pi enumeration) moved from Phase 22 to Phase 18. 22-SPEC R1, ROADMAP Phase 22 and 18.1's `no_inventory` note were amended.
- The template lives in `ai-kit-spec-review` (18.1 D-10). The analyzer had proposed curated-config; the 18.1 jev decision (TypeSafe 0.87) governs.
- The 18.1 couplings were folded in as D-30, and the R5 success rule was split for exec and review.

## Corrections Made

No user corrections. The locked decisions were refined, not replaced: D-06 (no new backup on an identical state) and D-07 (the restore exception).
