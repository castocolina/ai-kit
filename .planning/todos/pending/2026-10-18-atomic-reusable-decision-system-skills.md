---
created: 2026-10-18T17:21:10.347Z
title: Atomic, reusable decision-system skills on Jev
area: skills
severity: major
files:
  - .planning/docs/system-one-decision-skill/PLAN.md (main checkout)
  - .planning/todos/pending/2026-10-11-execute-system-one-decision-skill-plan.md (main checkout)
  - .planning/todos/pending/2026-10-14-wire-jev-fast-decision-cross-host-discovery-scaffolding.md (main checkout)
  - skills/ai-kit-gsd-spec-discuss/scripts/decide.py
---

## Problem

The decision system exists only as pieces: a reviewed plan on `main`
(`.planning/docs/system-one-decision-skill/PLAN.md`, 17 rounds, with a Jev 1.14 addendum), two
pending todos on `main`, the global `jev-fast-decision` skill that only Claude Code can
discover, and the `decide.py ladder` embedded in the Phase 24 skill, which the v1.3 run used at
every decision point. None of it is a roadmap phase. The owner needs it soon, as a set of atomic,
reusable skills that any flow can inject (GSD gates, review and plan-checker triage, planning
side decisions), so trivial-but-slow structured judgments stop burning long deliberation and
scarce planner quota (the planner model ran close to exhaustion on 2026-10-18).

## Solution

- Owner direction (2026-10-18): the System One plan owns backend complexity (Laya, TypeSafe,
  Zen, consent, probes, error taxonomy); this work packages it as small skills with clear seams
  so another escalation system can be added, or a piece removed, later.
- Reuse the Phase 24 detection semantics ("optional and detected, never assumed") and the
  existing `decide.py` ladder instead of a second implementation.
- Cross-host discovery (pi, opencode, codex, cursor) per the 2026-10-14 todo.
- Jev 1.14 (per the plan addendum) supports more context, new question types (e.g. `box`) and
  images, so it could judge a UI. Whether it accepts several images and compares them is a
  research question.
- Honest limit: Jev answers structured choices (option pick, yes/no, triage, rubric scores); it
  does not write plans. In the v1.3 run most Laya answers came back as low-confidence fallbacks,
  so the skill must keep the advisory + "reason it yourself" contract.
- An optional, separately installable hook knob in ai-kit setup (see the tool-advisory todo).

## Research notes (2026-10-18, fast pass)

- Plan status: not executed. The live global skill has only `SKILL.md`, `reference.md` and
  `scripts/jev_review.py`; a reference implementation of the plan sits in its `scratchpad/v3/skill/`
  (45 tests green on 2026-10-11). The pending 2026-10-11 todo carries corrections the plan lacks.
- `decide.py` today: Laya per item -> one TypeSafe batch for errored/low items -> own reasoning;
  `choice` and `noul` only (no `score`, `box`, images); no Zen; consent persisted in
  `jev-consent.json` (the plan uses a per-session env var).
- Breakage risk: `decide.py` pins `JEV_RESPONSE_MODEL=jev-1.13.0` and `jev_review.py` requires an exact
  `model` match, so every TypeSafe answer turns `invalid_response` once `jev-latest` moves to
  `jev-1.14.0` (TypeSafe announced the move about a week after the 2026-10-14 release; inferred, not
  observed). Decide: pin a versioned id or accept `jev-1.x.y`.
- Jev 1.14 (docs.typesafe.ai): `choice` (<=255 options), `score` (2-10 levels), `noul`, `box`
  (1.14, image only). 64k tokens per request / 32k per question by default, 262k with the
  long-context danger-zone header. Images are experimental ("dreamer-ready"): several per request,
  comparison is a documented pattern (reference vs state, options by example image, frame
  sequences, tiles); PNG/JPEG, 280-1568 px, 16 MiB per file, 32 MiB per request. Unlimited
  questions per request over one shared state (parallel; documented 12x cheaper than separate
  calls). $0.042 per million input tokens.
- Local Laya (`laya[serve]==0.4.2`, not TypeSafe's model): `/health`, `/v1/systemone`,
  `/v1/systemone/batch` (unknown to the plan); silently truncates long input; images, `box`,
  `score` unverified; weak on design questions.
- Open for the phase researcher: Laya batch isolation and limits; version pinning; Zen's role;
  consent model; the atomic-skill boundary (per question type vs one shared client, without
  duplicating `jev_review.py`); adding `score` and handling 400 `max_tokens_exceeded` and 529.

## Promoted

Promoted to Phase 21.1 on 2026-10-18 (ROADMAP and REQUIREMENTS updated). Owner-approved order: 21.1 -> 21.2 -> 21.3, all before Phases 22 and 23.
