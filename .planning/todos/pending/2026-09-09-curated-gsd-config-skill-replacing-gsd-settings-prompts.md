---
created: 2026-09-10T00:43:39.014Z
title: Curated GSD config skill (replace gsd-settings/gsd-config prompting)
area: tooling
resolves_phase: 7
severity: minor
files: []
---

## Problem

`gsd-settings` and `gsd-config` are annoying because they ask through the full question set
every time instead of just applying known preferences.

Build this skill (companion to the AGENTS.md rules checker todo) using the pipeline:
`/superpowers:writing-skills` → `/skill-judge` → `/naming-analyzer` (naming-analyzer picks
the final skill name).

Wanted behavior:
- A curated skill/command that asks a small set of simple questions (not the full
  gsd-config interrogation) and otherwise applies the user's own preset preferences.
- Generates the resulting `config.json` directly from those preferences.
- Validates the generated config against the open-GSD config JSON schema, if one exists.

Known preference defaults to bake in:
- High effort for analysis-type tasks.
- Haiku for execution-type tasks.
- Cross-AI execution enabled.
- Convergence of plan checks enabled.

## Solution

TBD — scaffold via `/superpowers:writing-skills`, evaluate with `/skill-judge`, then run
`/naming-analyzer` to pick the final skill name. Implementation should read/write the same
`config.json` shape `gsd-config`/`gsd-settings` produce today, just skip re-asking questions
already answered by the curated preference set above.
