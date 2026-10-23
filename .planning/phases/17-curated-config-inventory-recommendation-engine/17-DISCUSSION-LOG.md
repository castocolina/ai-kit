# Phase 17: Curated-Config Inventory & Recommendation Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-23
**Phase:** 17-curated-config-inventory-recommendation-engine
**Mode:** --analyze (a trade-off analysis was presented before each question)
**Areas discussed:** Native tier maps, Price ceiling, Undecidable slots, Existing config

---

## Native tier maps

**Question: when should `model_profile_overrides.<host>.<tier>` be written on non-claude hosts?**
- Only when the native slot is invalid (not on the host's list, or over the ceiling) ✓
- Always write all three slots
- Native slot plus a score-margin upgrade

**Evidence presented:** gsd-core 1.14's `RUNTIME_PROFILE_MAP`:
- claude = `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5` (stale, but aliases are
  used);
- codex = `gpt-5.6-sol`/`terra`/`luna`;
- opencode = `anthropic/claude-*`, which is not in the user's 81-model opencode list.

## Price ceiling

**Question: how should the rigor price ceiling work?**
- A relative percentile of the host's eligible models ✓
- Absolute $/1M caps
- A price weight only

**Question: how are models with unknown price (e.g. router-env/*) handled?**
- The user's free-text answer: "That models are ready analyzed by user".
- Follow-up question: how should user-analyzed router models be treated?
  - Preferred for their declared role, exempt from the cap ✓
  - Exempt from the cap only
  - Let me explain

## Undecidable slots

**Question: how should `plan.json` represent slots `recommend` can't decide?**
- `needs_choice` entries; `apply` refuses until they are resolved; deterministic ties; missing
  specialists get a warning ✓
- A low-confidence guess
- Omit the key and add a note

## Existing config

**Question: how should existing values in plan-managed families be treated?**
- Authoritative, with a visible `op: unset` for stale entries and the existing value on every
  entry ✓
- Additive only
- Ask per conflict

## Claude's Discretion

- The percentile values per rigor.
- plan.json schema details.
- Skill-scan depth.
- The layout of the mapping tables.

## Deferred Ideas

None.

---

# Update 2026-10-14 (assumptions mode)

**Mode:** assumptions (`--analyze --all --batch`), jev screening, best over easy, CodeGraph
**Input:** `17-SPEC.md` (c3800e6) plus the 2026-09-23 decisions D-01..D-08, kept as locked.

The analyzer was `gsd-assumptions-analyzer` (sonnet), with jev-fast-decision through
`agent_skills`, best over easy in its brief, and CodeGraph instructions. It ran live checks
against gsd-core 1.16 in scratch projects and an isolated catalog cache. No secret values
were read; the Artificial Analysis key was checked by name only.

## Live facts that changed the plan
- An Artificial Analysis key is configured; a live fetch scored 196 of 254 entries. The
  "no key, price-only" claim in 16.1 R18, ROADMAP 16.1 SC6 and the 17 SPEC was corrected.
- gsd-core is 1.16.0; `isValidConfigKey` accepts 125 central keys, 16 patterns and 86
  capability keys.
- With a project config present, gsd-tools ignores `~/.gsd/defaults.json`.
- `config-set model_policy null` fails on the whole object; unset goes per leaf. 18-CONTEXT D-07
  and SPEC R13 were amended.
- The catalog provider is reseller-attributed, the ranker rounds to 1 decimal, cursor joins
  143 of 259 ids, and all 79 `-fast` ids have twins.
- `claude_md_detect` already prefers `AGENTS.md`; only the config value is stale.

## jev screening

One Laya call per item; `needs_fallback` items batched to TypeSafe direct. The probability
shown is the chosen option's.

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| K01 valid keys | central_only 0.74 | probe_closed_set 0.97 (second opinion) | **Laya overridden:** central-only rejects the 86 live capability keys (D-09) |
| K02 conflicts | verified_behavior (fb) | verified_behavior 0.88 | D-10 |
| K03 gsd-core scope | label_and_warn 0.74 | – | D-11 |
| K04 unscored | catalog_wide (fb) | per_pool_and_pick 0.82 | D-12 |
| K05 `-fast` link | adapter_field (fb) | adapter_field 0.58 | D-13 |
| K06 vendor | provider_as_is (fb) | inferred_strict 0.34 (fb) | **Own reasoning:** inferred_strict; reseller rows make the raw provider meaningless, and lenient fallback would let a reseller row count as a different vendor (D-14) |
| K07 tie precision | add_exact_field (fb) | add_exact_field 0.95 | D-15 |
| K08 ceiling sample | every_pair 0.91 | families 1.00 (second opinion) | **Laya overridden:** effort variants repeat one price and would skew the percentile (D-16) |
| K09 tier slots | used_tiers_only (fb) | used_tiers_only 0.98 | D-17 |
| K10 schema | add_keep_and_source 0.88 | – | D-18 |
| K11 cross-AI slots | placeholders 0.76 | – | D-19 |
| K12 goldens | static_files (fb) | shared_tables_builder 0.94 | D-20 |

## Corrections Made

No user corrections. D-08's global `model_policy` wording was refined by verified behavior
(D-10), and its unset now goes per leaf; the user's intent (remove a shadowing project
policy, never edit the global file) is unchanged.
