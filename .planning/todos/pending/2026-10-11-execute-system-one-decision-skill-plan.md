---
created: 2026-10-11T22:50:00.000Z
title: Execute the System One decision-skill plan (jev-fast-decision, 3 backends)
area: skills
severity: major
files:
  - .planning/docs/system-one-decision-skill/PLAN.md
  - .planning/docs/system-one-decision-skill/README.md
  - ~/.claude/skills/jev-fast-decision/
---

## Problem

The global skill `jev-fast-decision` has to choose between three System One backends and gate each one:

- **Local Laya:** sends one item per request.
- **TypeSafe direct.**
- **OpenCode Zen:** tries `jev-1.13-free` first, then falls back to the paid `jev-1.13`.

Every backend needs an availability probe, an explicit `JEV_BACKEND` choice, and consent for the remote ones. A low-confidence answer must hand off to the main orchestrator (`needs_fallback`).

The full plan was reviewed over 17 rounds and is at `.planning/docs/system-one-decision-skill/PLAN.md`.

## Solution

- **Execution mode:** run the plan with superpowers:executing-plans (native). The skill directory is not a git repo, so Task 0 snapshots it and each checkpoint is a `diff -ru`.
- **Prerequisite:** Tasks 0–4 work offline. Tasks 5–8 need llm-env's System One enabled and healthy on 127.0.0.1:8010, which comes from llm-env Plan A.
- **Owner choices at execution time:** Task 8 asks the owner for the judge lanes and the FIX command. Do not hardcode models.
- **Reference implementation:** `scratchpad/v3/skill/` has the plan's code applied and green (45 passed).
