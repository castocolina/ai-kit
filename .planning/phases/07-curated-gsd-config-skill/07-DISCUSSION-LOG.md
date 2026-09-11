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

---

## Amendment (same day, follow-up session): critical-agent model/effort mapping

User returned to revise the model/effort part of the Write mechanism decision (D-03),
prompted by two reference docs: `docs/how-to/configure-model-profiles.md` and
`docs/AGENTS.md` (both `github.com/open-gsd/gsd-core`, `next` branch).

**Round 1 — initial ask:** use `model_profile: "budget"` but put critical agents on
opus+high via `model_overrides`/`effort`.

**Round 2 — my first proposal (rejected):** map "planner + reviewer agents" onto the
whole `verification` phase-type group (8 agents) plus planning. User pushed back:
some of those agents are "merely mechanical" (their words) and sweeping a whole
phase-type bucket onto opus+high was wrong — asked for each agent to be reviewed
individually against real data, not assumption, and for the skill to be able to
detect/discover the right classification from GSD's own components locally
(or live research) rather than anything hardcoded that could silently go stale.

**Verification performed:** queried the installed gsd-core's `model-catalog.cjs`
directly (`node -e "require(...)"`) for `AGENT_DEFAULT_TIERS` and
`AGENT_TO_PHASE_TYPE` — confirmed `gsd-verifier`/`gsd-code-reviewer` are `standard`
tier (not heavy) and most other verification-phase agents
(`gsd-plan-checker`/`gsd-integration-checker`/`gsd-nyquist-auditor`/
`gsd-ui-checker`/`gsd-ui-auditor`/`gsd-doc-verifier`) are `light` — validating the
user's pushback with real data.

**Round 3 — revised proposal (accepted):** one curated question (model_profile);
GSD's own `heavy`-tier agents automatically get opus+high (derived live, not
guessed); user's named top-up (`gsd-code-reviewer`) gets the same treatment
explicitly; research/execution phase-types floor to haiku, with GSD's own
override-precedence rules resolving the 3 agents that are both heavy-tier and
execution/research-tagged in favor of heavy (opus wins); everything else
(light/standard, unnamed) follows the base profile with no override. The skill's
actual logic must re-derive this from the live `model-catalog.cjs` exports at
run time, never ship a hardcoded snapshot.

**User's final answer:** "Matches" (accepted as described).

Superseded text in 07-CONTEXT.md's D-03: the original draft that said "gsd-planner
needs no override — already heavy tier" (still true, but now subsumed by the
general heavy-tier rule) and the code-reviewer-only override (now explicitly framed
as a named top-up on top of, not instead of, the heavy-tier rule).
