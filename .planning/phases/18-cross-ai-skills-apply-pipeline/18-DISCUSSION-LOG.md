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
