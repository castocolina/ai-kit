---
created: 2026-11-16T12:30:00Z
title: spec-config wizard owner observations (catalog first, short choice, only chosen lanes written)
area: skills
severity: major
resolves_phase: 35
files:
  - skills/ai-kit-spec-config/SKILL.md
  - skills/ai-kit-spec-config/references/cli-model-selection.md
  - skills/ai-kit-spec-review/ai_kit_spec/detection.py
  - skills/ai-kit-spec-review/ai_kit_spec/catalog_build.py
  - skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py
  - skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py
---

## Problem

The owner ran `/ai-kit-spec-config` on 2026-11-16, after Phase 33 redesigned the config file, and found the
wizard flow still wrong. Phase 33 changed the file, the migration and trust; the catalog and the question flow
belong to Phases 35 and 36. These observations must reach the spec and discuss of Phases 35 and 36 (the
2026-11-14 amendments there already say "catalog first, then propose review and coding sets").

1. **Catalog first, complete, with a refresh TTL.** Intended flow: detect the local harnesses and runtimes, list
   their models, dedup, look each model up in models.dev, Artificial Analysis and LM Arena (ELO), add the
   router-env attributes, and write one complete catalog JSON with per-model details and a refresh TTL. Today
   `~/.cache/ai-kit/spec/model-catalog.json` exists but lacks the full per-model detail (no Arena data).
2. **Then a short choice, per purpose.** Ask which runtimes the owner prefers for review and which for execute,
   then show the already-ranked models for each purpose, the best fit first, regardless of backend or frontend:
   review favours semi-frontier models (opus, sol); execute favours haiku, luna, sonnet, `*flash`, `*code`,
   composer, grok. Few selection steps.
3. **Review and execute must be clear in the questions.** The ladder / priority-fallback questions mixed both
   purposes; each purpose gets its own order.
4. **Write only what was chosen.** The owner named about 5 models for the ladder; the wizard wrote 19 lane entries
   and one mixed 18-key ladder into `.aikit/config.toml`. The written file holds only the chosen entries, with
   separate review and execute orders.
5. **No `.migrated` backup.** The owner says they never needed a backup of `review-spec.toml`; the wizard left
   `.aikit/review-spec.toml.migrated` (Phase 33 D-12 keeps the old file renamed). Revisit: delete the old file after
   a successful migration, or make the backup opt-in.
6. **router-env aliases are assumed, not asked.** `router-env/my-referee-*` (review) and `router-env/my-coding*`
   (execute) are the owner's router aliases: router, fallback quota, no per-model heuristic confirm question and no
   models.dev / Artificial Analysis lookup. Label them `assumed: router-env alias naming`, never verified.
7. **Copilot models through herdr.** `detect-runtimes` lists copilot with 0 models and `copilot --help` has no
   models subcommand (only interactive `/model` or `--model`). When the herdr skill is usable (HERDR_ENV=1), start
   copilot in a herdr pane with no permission prompts (`--allow-all` / `--yolo`), read `/model`, use those ids,
   close the pane; without herdr, say so and ask for the id (or `auto`).

Also seen in the same run:
- The wizard hand-edited the model catalog through ad-hoc tmp scripts and guessed the catalog key format: there is
  no factory subcommand to confirm a catalog entry.
- It hardcoded its scratch path in a script.
- spec-config cannot run from a subagent (step 2 needs the user); it should stop after detection and return the
  pending decisions.
- `check-providers` reported `.aikit/config.toml scanned-inactive (untrusted)` before that file existed.

## Solution

Fold items 1-2 and 6-7 into Phase 35 (model discovery and catalog) and items 3-5 into Phase 36 (spec-config as the
hub), together with the related todo `2026-10-29-unify-review-execute-lane-toml-effort-escalation-and-jev-classification`.
Add the "only the chosen entries are written" and the backup decision to their success criteria during spec and
discuss. A stopped partial implementation of items 6-7 exists, unapplied, at
`tmp/auto/r325/spec-config-router-env-partial.patch` (local scratch, not committed).
