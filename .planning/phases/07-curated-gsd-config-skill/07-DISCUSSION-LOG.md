# Phase 7: Curated GSD Config Skill - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-10
**Phase:** 7-Curated GSD Config Skill
**Areas discussed:** Write mechanism (incl. model/effort/cross-ai mapping), New vs. existing config, Relationship to gsd-settings/gsd-config

---

## Write mechanism

Options presented:
- Call existing gsd-tools CLI (recommended) — config-new-project/config-set, reuses built-in schema validator
- Hand-write the JSON directly

**User's choice (free text):** Call existing CLI, but "part of both" — the skill needs inference (detection of CLIs/models in the environment, reusing existing detection code), not pure copy-paste.
**Notes:** User gave detailed preference patterns for plan-review models (plan-review/gpt-sol/glm-5.2-5.3/opus, runtimes opencode/cursor) and execution models (coding/executor pattern, composer-2.5+, grok-4.6+, deepseek-flash, luna, haiku), plus workflow-flag intent (most on, intel+codegraph+worktrees on, frontend-detected ui_phase/ui_review, default effort with select high-effort/opus agents, haiku for gsd-executor's cross-ai-failure fallback). This required live verification before follow-up questions: fetched open-gsd's `next`-branch `CONFIGURATION.md` and cross-checked the installed gsd-core v1.13.0's `config-schema.manifest.json` directly, confirming `model_overrides`, `effort.*`, `dynamic_routing.*`, `review.reviewer_instances.*` are all live, supported keys. Also located ai-kit's own existing `ai_kit_spec` CLI/model detection pipeline as the reuse target.

Follow-up correction from user: the `ONESHOT-RULES.md` Rule-7 circuit-breaker is ai-kit-specific and not assumed present elsewhere — `model_overrides.gsd-executor: "haiku"` is simply a universal default regardless. Also clarified `cross_ai_command` (literal command string, gets explicit `--model`/effort flags) vs. plan-review-convergence (resolves via `review.models`/`review.reviewer_instances`, already has a user-side shim for default-model selection).

Landmine raised: `cross_ai_command` must never bake in a resolved absolute path for the executable (observed regression) — always the bare command name.

`claude_md_path` follow-up: user wants a detection helper inside the skill (checks which instruction-file variant exists, prefers AGENTS.md family), explicitly declined tracking ai-kit's own config update as a separate item — implicit future behavior once the skill exists.

---

## New vs. existing config

Options presented:
- Merge, touch only curated keys (recommended)
- Regenerate the whole file

**User's choice:** Merge, touch only curated keys (recommended option).

---

## Relationship to gsd-settings/gsd-config

Options presented:
- Replace outright
- Coexist as a faster alternative entry point (recommended)
- Wrap gsd-settings' interactive flow

**User's choice:** Coexist as a faster alternative (recommended option).

---

## Claude's Discretion

- Exact phrasing/order of the curated question set.
- Frontend-detection heuristic implementation details.
- Graceful-degradation behavior when no detected model matches a stated preference pattern.

## Deferred Ideas

None — discussion stayed within Phase 7 scope.
