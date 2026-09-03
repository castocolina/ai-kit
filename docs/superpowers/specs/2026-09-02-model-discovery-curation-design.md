# Model Discovery & Curation — Design

**Date:** 2026-09-02
**Status:** Draft, pending user review

## 1. Problem

`docs/superpowers/specs/2026-08-28-ai-kit-spec-execute-design.md` §5 deferred
`task_affinity`/`context_limit` curation to `ai-kit-spec-config`'s
"WebSearch-informed research" — but this was never actually specified or
implemented. `docs/superpowers/plans/2026-08-29-ai-kit-spec-execute-superpowers.md`
(line 22) records this as a tracked CRITICAL finding: `ai-kit-spec-config`
never asks for or writes `task_affinity`/`context_limit` today, and
populating them is explicitly out of that plan's scope, deferred to
`ai-kit-spec-config`.

Today's `ai-kit-spec-config/SKILL.md` Step 2.2 does a lightweight,
per-unfamiliar-model WebSearch — checking recency and a rough
reasoning-vs-execution orientation — informally, with no scoring, no
ranking, and nothing persisted beyond the flat `review-spec.toml` reviewer
entry. There is no mechanism to:

- discover a CLI's full model catalog and evaluate each candidate against
  reliable external sources
- score models on reasoning, tool-calling, coding/intelligence/agentic
  benchmarks, context window, price, or batch-mode suitability
- rank candidates by *purpose* (review/analysis vs. execution) and present
  a ranked, purpose-labeled list for the user to choose from
- let `ai-kit-spec-review` and `ai-kit-spec-execute-*` consume
  purpose-curated models — both consumers share one undifferentiated
  ladder today, by design (`dispatch_injection.py` reuses
  `review-spec.toml` wholesale), which is correct for the ladder
  *mechanism* but wrong for *which entries* each consumer should prefer.

## 2. Goals / Non-goals

**Goals:**
- Deterministic, low-maintenance enrichment of discovered models with
  reasoning/coding/agentic/intelligence indices, context window, pricing,
  and speed — sourced from external APIs, not LLM guesswork.
- A purpose axis (`review` / `execute` / `both`) orthogonal to the
  existing `task_affinity` (frontend/backend/mixed) axis.
- Weighted, purpose-specific ranking presented to the user before they
  pick the ladder.
- Minimal, backward-compatible changes to `review-spec.toml` and its two
  consumers.

**Non-goals:**
- Exhaustive research of every model in existence. Discovery is scoped to
  what each CLI's own model catalog already surfaces (opencode, codex,
  cursor, native) — never OpenRouter's full marketplace, which is
  explicitly excluded as a *candidate source* (too many low-curated
  provider-hosts to choose from reliably) though its underlying data is
  not needed since Artificial Analysis and models.dev cover the same
  ground with cleaner data.
- Real-time/continuous model tracking. This is a periodic, cached
  discovery step run at `-config` time, not a background service.
- Changing `review-spec.toml`'s policy/ladder mechanics. The ladder,
  `mode` (single/double), and fallback ordering are unchanged — this
  design only improves what data informs the *defaults* offered during
  ladder construction, and adds a `purpose` filter at resolution time.

## 3. Data sources

Two external sources, both queried by the producer side
(`ai-kit-spec-config`) only — never by the consumers at review/execute
time:

- **[models.dev](https://models.dev/api.json)** — free, unauthenticated,
  single `GET`. Per-model: context window, max output tokens,
  input/output pricing, and boolean flags for `reasoning`, `tool_call`,
  `structured_output`, modalities. Always queried; no key to manage, no
  rate limit in practice.
- **[Artificial Analysis](https://artificialanalysis.ai/data-api/docs)**,
  free tier `GET /api/v2/language/models/free` — requires an API key
  (`x-api-key` header, stored at `~/.config/ai-kit/secrets.env` as
  `ARTIFICIAL_ANALYSIS_API_KEY`, never committed). Confirmed live
  (2026-09-02) to return exactly `artificial_analysis_intelligence_index`,
  `artificial_analysis_coding_index`, `artificial_analysis_agentic_index`,
  `pricing` (input/output/cache), and `performance`
  (`median_output_tokens_per_second`, time-to-first-token, end-to-end
  response time) — paginated, ~800 models across 4 pages of 200. Free
  tier has no `context_window` or tool-calling field (models.dev covers
  those) and is capped at 100 requests/24h. Queried only when a key is
  configured; absence degrades gracefully (see §6).

Neither source shares a clean `vendor/model` id with how CLIs name their
own models (e.g. opencode's `openai/gpt-5.6-sol`) — matching against
models.dev/AA's own `slug`/`name`/`model_creator` fields requires a
normalization + fuzzy-match step, not a direct key lookup.

Fields with **no external source** — computed locally, from what the
CLI/provider already declares, never researched:
- `is_router` — inferred from the provider/model-id naming at discovery
  time (e.g. a provider named `router-env` self-identifies; the user
  confirms/corrects during the wizard).
- `fallback_quota` — true when the router entry is known to have
  internal multi-backend fallback (same inference source as `is_router`).
- `batch_mode` — inferred from the model id/name (e.g. `-flash`,
  `-batch`, `-mini` suffixes correlate with non-interactive/batch
  suitability), confirmed/corrected by the user during the wizard.

## 4. Data flow

1. **Discover** candidates from each installed CLI's own model list
   (`detect-runtimes`, already exists) — opencode, codex, cursor, native.
   No OpenRouter enumeration.
2. **Match** each candidate's CLI-native id against models.dev and
   (if configured) Artificial Analysis, by normalized name/slug.
   Unmatched candidates get one targeted search + user confirmation
   before being added to the catalog with `source.manual = true` and
   `confidence = "low"`.
3. **Enrich** deterministically from whichever sources matched — no LLM
   inference for any field either source provides.
4. **Infer locally** `is_router` / `fallback_quota` / `batch_mode` from
   naming heuristics, surfaced to the user for confirmation.
5. **Persist** to the global `model-catalog.json` cache, schema-validated.
6. **Rank** per purpose using `references/ranking-weights.toml`'s fixed
   weights (§5), and present the ranked, purpose-labeled list to the
   user, asking for any unlisted preference before finalizing.
7. **Write** the user's confirmed selection into `review-spec.toml`
   (local + global, per existing Step 3), now including `purpose`,
   `is_router`, `fallback_quota` per reviewer entry.

## 5. Schema

### `model-catalog.json` (global cache, `~/.cache/ai-kit/spec/model-catalog.json`)

One entry per model, keyed by `vendor/model` (the CLI-native id):

```jsonc
{
  "openai/gpt-5.6-sol": {
    "provider": "openai",
    "runtimes": {
      "opencode": { "model_id": "openai/gpt-5.6-sol", "ctx_window": 400000 },
      "codex":    { "model_id": "gpt-5.6-sol", "ctx_window": 400000 }
    },
    "native": false,
    "reasoning_modes": ["low", "medium", "high"],
    "fast_mode": false,
    "speed_tier": "standard",
    "tokens_per_sec": 142.3,
    "max_output_tokens": 128000,
    "structured_output": true,
    "tool_calling": true,
    "pricing": { "input_per_1m": 3.5, "output_per_1m": 14.0 },
    "scores": {
      "intelligence_index": 68.4,
      "coding_index": 74.1,
      "agentic_index": 61.2
    },
    "batch_mode": true,
    "is_router": false,
    "fallback_quota": false,
    "source": { "models_dev": true, "artificial_analysis": true, "manual": false },
    "confidence": "high",
    "last_verified": "2026-09-02"
  }
}
```

Mandatory: `provider`, `runtimes` (≥1 entry), `source`, `confidence`,
`last_verified`. Everything else is optional — a missing field never
blocks catalog writes or ranking; it simply doesn't contribute to that
axis's score (§6, consistent with how `filter_by_affinity`/
`filter_by_context` already treat absent fields as "no preference").

### `review-spec.toml` — extended `[[reviewers]]` fields

```toml
[[reviewers]]
key = "opencode-sol"
model = "openai/gpt-5.6-sol"
vendor = "openai"
cli = "opencode"
command = "opencode run -m {model}"
purpose = "both"          # "review" | "execute" | "both"
task_affinity = "mixed"   # existing field, orthogonal axis
is_router = false
fallback_quota = false
```

`purpose`, `is_router`, `fallback_quota` join the existing set of
schema-validated flat TOML keys (alongside `strength`, `effort`,
`timeout_tiers`) — no nested tables introduced into `review-spec.toml`
itself; the richer, nested data stays in `model-catalog.json`. An entry
missing these new fields (pre-migration config) behaves exactly as
today: `purpose` absent means "no preference," included in every ladder
resolution regardless of consumer.

Validation: a schema (dataclass, same module that already validates
`_KNOWN_REVIEWER_FIELDS`) rejects a write with missing mandatory catalog
fields or type mismatches — enforced in both `render-toml` and the new
`fetch-model-catalog` subcommand. A rejected entry is dropped individually
with a reported reason; it never aborts the whole write.

## 6. Ranking

`score = Σ(normalized_axis_value × weight) / Σ(weights of present axes) + bonuses`

Absent axes are excluded from the weighted sum and the remaining weights
renormalize proportionally — never a penalty, only reduced signal.

**Default weights** (`references/ranking-weights.toml`, versioned with the
skill, fixed defaults — the user is never asked to set these per run):

| Axis | REVIEW | EXECUTE |
|---|---|---|
| `intelligence_index` | 0.30 | 0.15 |
| `coding_index` | 0.10 | 0.30 |
| `agentic_index` | 0.15 | 0.25 |
| `context_window` (log-scale normalized) | 0.15 | 0.10 |
| `tool_calling` (0/100) | 0.05 | 0.15 |
| `price` (inverted, normalized within the candidate set) | 0.15 | 0.15 |
| `speed_tier` / `tokens_per_sec` | 0.05 | 0.10 |

Weights are pre-normalization; EXECUTE's raw sum (1.20) is normalized to
1.0 at ranking time, same as REVIEW's (0.95).

**Bonuses** (additive, capped at +15 combined, applied after the
weighted score is scaled to 0–100):
- `batch_mode = true` → +8 (both purposes — plan/document analysis and
  execution are non-interactive by nature, so non-interactive
  tool-calling capability is a direct fit, not just a nice-to-have).
- `fallback_quota = true` → +5 (router resilience).
- `task_affinity` matches the plan/doc's scope (frontend/backend/mixed)
  → +2.

`price` and `tokens_per_sec` are min-max normalized **within the current
run's candidate set**, not against a fixed global ceiling — a new
expensive model tomorrow doesn't distort today's ranking retroactively.

**Presentation** (replaces today's lightweight Step 2.2 WebSearch):

```
REVIEW (flagship/reasoning) — top candidates:
  1. gpt-5.6-sol            score 87  (intelligence 91, batch✓, ctx 400k)
  2. grok-4.6                score 79  (intelligence 85, agentic 88)
  3. router-env (fallback✓)  score 74

EXECUTE (coding-agent) — top candidates:
  1. router-env (fallback✓)  score 90  (coding 89, tool_call✓)
  2. gpt-5.6-sol              score 81
  ...
Any preference not listed, or confirm this order for the ladder?
```

The user's confirmed N entries per purpose feed into the existing
Step 3 write (unchanged mechanics — ladder ordering, `mode`
single/double, `strategy`) with better-informed defaults instead of a
flat model list.

## 7. Consumer-side changes

`dispatch_injection.py` and `ai-kit-spec-review`'s config resolution both
read the same `review-spec.toml` ladder today, unfiltered — correct
mechanism (one config, one resolution path), incomplete filtering (no
purpose distinction). The fix is a filter added at each consumer's
existing resolution point, not a new mechanism:

- **`ai-kit-spec-review`**: filters the resolved ladder to
  `purpose in {"review", "both"}`. If that empties the ladder (an
  execute-only config), falls back to the unfiltered ladder with a
  one-time warning — never a hard failure.
- **`ai-kit-spec-execute-superpowers`**: filters to
  `purpose in {"execute", "both"}`, implemented as one more filter
  in `execute_selection.py`'s existing `filter_by_affinity`/
  `filter_by_context` chain — not a new mechanism.
- **Degradation**: identical to how `task_affinity`/`context_limit`
  already degrade — a missing `purpose` means "no preference," and a
  pre-migration `review-spec.toml` (no `purpose` field anywhere) behaves
  identically to today in both consumers.

## 8. Errors and staleness

- `model-catalog.json` TTL ~30 days, refreshed via `--if-stale` on each
  `-config` run (same pattern as `runtimes.json`); `fetch-model-catalog
  --force` for manual refresh.
- Network failure fetching either source: fall back to the existing
  cached catalog if present; if absent, affected fields stay `null` and
  discovery continues — never blocks the wizard.
- Artificial Analysis key missing, invalid, or 100/day quota exhausted:
  index/speed fields stay `null`; one-time notice
  ("no Artificial Analysis data — set `ARTIFICIAL_ANALYSIS_API_KEY` for
  full indices"); wizard continues on models.dev alone.
- Unmatched model (no hit in either source): one targeted search + user
  confirmation, written with `source.manual = true`, `confidence = "low"`.
- Schema-invalid catalog or TOML entry: that single entry is rejected
  and reported; the rest of the write proceeds.

## 9. Testing

- **Ranker**: pure function, no network — unit tests on fixture catalogs
  covering full-data scoring, missing-axis renormalization, and bonus
  application.
- **Matcher**: unit tests on known CLI-vs-external naming mismatches.
- **Fetchers**: unit tests against mocked HTTP responses; no live network
  calls in the test suite.
- **Consumers**: extend the existing `filter_by_affinity` test suite in
  `execute_selection.py` (and the equivalent in `ai-kit-spec-review`'s
  resolution) with `purpose` cases — empty-after-filter fallback, absent
  field treated as no-preference.

## 10. Implementation plan split

One spec (this document), two implementation plans:

- **Plan A (producer, larger)**: `ai-kit-spec-config` changes —
  `fetch-model-catalog` subcommand, matcher, ranker, schema validation,
  new wizard steps replacing today's Step 2.2, `ranking-weights.toml`.
- **Plan B (consumer, small)**: `purpose` filter added to
  `ai-kit-spec-review`'s ladder resolution and
  `execute_selection.py`'s existing filter chain. Independent of Plan A —
  testable against a hand-written `review-spec.toml` with `purpose` set
  manually, does not require Plan A to be complete or merged first.
