# Jev fast-decision — type schemas, interpretation, receipts

Resolve the helper as `scripts/jev_review.py` relative to this skill's own
root directory (the same directory this file lives in).

## Request shape

```json
{"reviewed_head": "<40-hex-char string>", "items": [ ... ]}
```

Each item needs a unique, non-empty `id` plus one of:

| Shape | Keys | Produces |
| --- | --- | --- |
| Shorthand | `id`, `criterion`, `evidence` | a `choice` question over the fixed rubric `supported`/`partial`/`unsupported`/`unclear` |
| Choice | `id`, `type: "choice"`, `instructions`, `criteria` (map, ≥2 options, each a description string), optional `context` | picks one named option |
| Noul | `id`, `type: "noul"`, `instructions`, optional `criteria` (`{"true":..., "false":...}`), optional `context` | a single yes/no judgment |
| Score | `id`, `type: "score"`, `instructions`, `criteria` (array, 2–10 ordered level descriptions, low→high), optional `context` | a position along the rubric |

All items in one call run **in parallel against the same `state`** and
cannot see each other's answers — if one question's answer should change
how another is phrased, that's two sequential calls, not one batch.

`state` always contains the *entire* request — every item's text, not just
the one being judged. The script compensates by wrapping each general
item's `instructions` in a sentence that tells the model to look only at
that item's own entry and ignore the rest of `state.items`, and — when the
item has a `context` field — to judge using *that field by name*, the same
way the shorthand points at `state.items[id]` for `evidence` instead of
repeating it. **The `context` text is never copied into the instructions
sent to the model** — only its presence is noted — so there's no token
duplication and no untrusted content crosses into the instruction channel;
it stays in `state`, same as everything else. `context`, when given, must
be non-empty (whitespace-only is rejected as `invalid_input`). A
`choice`/`noul`/`score` item with no `context` and no material written
directly into `instructions` has nothing to judge against and will produce
a confident-looking but meaningless answer — the model will still try.

There's no documented hard cap on item count per request, but validation is
all-or-nothing: one malformed item invalidates the whole request before
anything is sent. Keep a batch to one coherent screening pass; a large,
heterogeneous batch increases both latency/cost and the blast radius of a
single bad item.

Write `instructions`/`context` or `criterion`/`evidence` as self-contained
text — the model sees only what's in `state`, not this conversation. Item
`id`s **are** sent as part of `state.items` (the scoping sentence the
script adds depends on this — it names the id directly), so don't treat an
id as hidden from the model; it just isn't the thing being judged.

## Response shape, per type

| Type | Answer fields |
| --- | --- |
| `choice` | `choice` (the picked option), `probabilities` (every option → probability, sums to 1), `confidence` (0–1) |
| `noul` | `noul` (0=no, 1=yes probability) — no separate `confidence` field; read the number itself as the confidence signal |
| `score` | `score` (position on the level number line, 0 to levels−1, can fall between levels), `legend` (level index → description), `probabilities` (level index → probability, sums to 1), `confidence` (0–1, derived from how spread the probabilities are) |

An `ok` top-level response also carries `model`, `reviewed_head`,
`request_sha256` (hash of the exact canonical request sent), and `usage`
(`input_tokens`/`output_tokens`).

## Interpreting answers

- **Confidence below ~0.7, or a `choice` answer of `unclear`:** treat it as
  no signal — investigate yourself rather than acting on it either way.
- **`unsupported` at high confidence on non-empty evidence:** look harder,
  don't auto-dismiss. An empty-evidence item scoring `unsupported` at ~99%
  is the grounding check working correctly, not a flaw.
- **`noul` near 0.5:** means genuinely split, not "medium" — don't treat it
  as a soft yes or soft no.
- **`score` confidence:** summarizes how concentrated the probability mass
  is across levels, not overall correctness or permission to act on it.
- Thresholds are domain-specific — validate on your own representative
  cases before trusting a cutoff, including the ones above.

## Status handling

`disabled` and `unavailable` are optional outcomes, not failed criteria —
the script exits zero for both and makes no automatic retries. Fix invalid
input/configuration before an explicit retry; otherwise fall back to
ordinary reasoning and keep the service failure visible in whatever
artifact you're writing, rather than silently proceeding as if nothing
happened.

When `reason` is `invalid_input` and the problem traces to one item (a
duplicate id, a malformed `criteria` shape, an empty `context`, etc.), the
response also carries an `item` field naming that item's `id` — fix that
one item rather than guessing across the whole batch. `invalid_response`
(a malformed answer from the service) is not currently tagged per item;
a single bad answer invalidates the whole batch with no indication which
one, since the noul/score response shapes haven't been live-verified yet
(only the original 4-way `choice` shorthand has — see Service behavior).

## Recording a receipt

If you keep the JSON result in a durable artifact (review notes, a decision
log), keep it as advisory evidence outside any fixed-format verdict field:
- `ok` → the full receipt: `reviewed_head`, `request_sha256`, `model`,
  per-item answers, and `usage`.
- `unavailable` → the `reason`, plus `reviewed_head`/`request_sha256` if
  they were computed before the failure (they're absent if input validation
  failed first).
- `disabled` → just the status; nothing else to record.

Reuse a recorded receipt instead of re-calling when the exact request and
reviewed revision are unchanged.

## Service behavior

Calls only `https://opencode.ai/zen/v1/systemone` with model id `jev-1.13`
(Zen's model string carries no patch suffix, unlike TypeSafe-direct's
`jev-1.13.0`). Sends an explicit `User-Agent` header — Zen's Cloudflare edge
returns error 1010 against the bare `Python-urllib/x.y` default, which
otherwise surfaces as an indistinguishable `unavailable`/`http_403`. Does
not follow redirects, echo provider error bodies, write files, or install
packages. There is no confidence cutoff built in: the calling agent owns
acceptance. Evaluate real accuracy on your own chosen evidence before
relying on this as a signal.

Sources: [HTTP API](https://docs.typesafe.ai/api.md),
[Choice](https://docs.typesafe.ai/primitives/choice.md),
[Noul](https://docs.typesafe.ai/primitives/noul.md),
[Score](https://docs.typesafe.ai/primitives/score.md),
[Confidence](https://docs.typesafe.ai/confidence.md).
