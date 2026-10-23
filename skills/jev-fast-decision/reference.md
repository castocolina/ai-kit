# Jev fast-decision — reference: shapes, capability matrix, hosts

Resolve the client as `scripts/jev_review.py` relative to this skill's root.

## Request shape

```json
{"reviewed_head": "<40-hex-char string>", "items": [ ... ]}
```

Each item needs a unique, non-empty `id` plus one of:

| Shape | Keys | Produces |
| --- | --- | --- |
| Shorthand | `id`, `criterion`, `evidence` | a `choice` question over the fixed rubric `supported`/`partial`/`unsupported`/`unclear` |
| Choice | `id`, `type: "choice"`, `instructions`, `criteria` (map, ≥2 named options), optional `context` | one named option |
| Noul | `id`, `type: "noul"`, `instructions`, optional `criteria` (`{"true":..., "false":...}`), optional `context` | one yes/no probability |
| Score | `id`, `type: "score"`, `instructions`, `criteria` (2–10 ordered level descriptions, low→high), optional `context` | a position along the rubric |

Write `instructions`/`context` or `criterion`/`evidence` as self-contained English text — the model sees only what is in `state`, not the conversation. Put the material being judged in that item's own `context` (or inline in `instructions`); a question with nothing to judge against still gets a confident-looking, meaningless answer.

## Response shape

An `ok` result carries `status`, `backend` and `model` (the rung that gave every final answer, `null` when answers came from different rungs), `answers`, plus `trail` (per-item ordered rung entries, each with `request_sha256`), `attempts`, `unavailable`, `usage`, `request_sha256` (over every body sent), `reviewed_head`, `backends` (the probe entries), `remote_available` and `consent_used` where relevant, and `errors` for item-level failures.

| Type | Answer fields |
| --- | --- |
| `choice` | `choice`, `probabilities` (sum to 1 within rounding), `confidence` (0–1) |
| `noul` | `noul` (0=no, 1=yes) — no `confidence` field |
| `score` | `score` (0..levels−1, may fall between levels), `legend`, `level` (winning index), `probabilities`, `confidence` |

Every answer also carries `model` (what answered it), `backend`, `top` (the winning probability — what `needs_fallback` compares), `needs_fallback`, and `request_sha256`. `needs_fallback` is true when the answer was forced (the server reported `usage.truncated`, or the state exceeded the row's size guard) or when `top` is below the row's `min_confidence`.

## Interpreting answers

- `confidence` is **not calibrated**; a threshold must be set per question and per risk.
- `top`, not `confidence`, decides `needs_fallback`. On `noul` the signal is `p` itself or |2p−1|; near 0.5 means genuinely split, not "medium".
- `unsupported` at high confidence on non-empty evidence is the grounding check working — look harder, don't auto-dismiss.
- An empty-evidence shorthand item scores `unsupported` at ~99% by design.

## Status and reason

| Status / reason | Meaning | What you do |
| --- | --- | --- |
| `disabled` | `GSD_PATH_JEV` unset | reason it yourself |
| `ok` | answers under `answers` | read the recipe in SKILL.md; advisory only |
| `consent_required_for_remote` | a keyed remote is configured but not allowed this session | ask the user; on yes grant/export, retry |
| `unavailable` / `backend_unavailable:<name>:consent_required_for_remote` | explicit backend without consent | ask; on yes grant/export, retry |
| `unavailable` / `invalid_input` (+ `item`) | one bad item named in `item` | fix that item, retry explicitly |
| `unavailable` / other reasons (`http_503`, `unauthorized`, `network_error`, `deadline`, `no_backend_available`, `unsupported_feature`, ...) | read `reason`, `unavailable`, `attempts` | fix or reason it yourself; never retry blindly |
| `unsupported_feature` | the item asks for a shape no row can run, or the explicit `JEV_BACKEND` row cannot run one item (the whole request stops; e.g. `score` on `opencode`) | reason it yourself, or drop that item and retry |

## Receipts

Keep results in durable artifacts as advisory evidence, never in a verdict field: `reviewed_head`, `request_sha256`, `model`, per-item answers, `usage`. `request_sha256` is the sha256 over the concatenation of the exact request bodies sent, in send order; each answer's own `request_sha256` names the body it came from. Reuse a recorded receipt instead of re-calling when the exact request and revision are unchanged.

## Answer log

`${XDG_STATE_HOME:-~/.local/state}/ai-kit/jev-answers.jsonl` — one JSON line per dispatched item: `ts`, `caller` (from `JEV_CALLER`), `id`, `type`, `instructions`, and on an answer `backend`, `model`, `choice` or `score`, `top`, `needs_fallback`, `request_sha256`; on an error `backend`, `error`, `request_sha256`. `context`, criteria text and key values never enter a line. A log failure never changes the result.

## Consent record

`${XDG_CONFIG_HOME:-~/.config}/ai-kit/jev-consent.json` — `consent grant|revoke|show <backend>` writes and reads it, keyed by backend with `host` and `granted` (ISO date); a grant is bound to the row's current host, so an endpoint move needs a new grant. The session gate is `JEV_ALLOW_REMOTE`: `1` names every remote, a comma list names those rows, anything else opens nothing. A remote row runs when the gate names it or its record matches its current host. A grant's announcement says the questions go to that host and retention terms are unverified.

## Environment

| Variable | Meaning |
| --- | --- |
| `GSD_PATH_JEV` | exactly `1` enables screening (kill switch) |
| `GSD_PATH_JEV_TIMEOUT_SECONDS` | per-request socket timeout (required, positive) |
| `GSD_PATH_JEV_DEADLINE_SECONDS` | optional bound on the whole run, probes included |
| `JEV_BACKEND` | `auto` (default) or one row name; explicit never falls back |
| `JEV_ALLOW_REMOTE` | the session consent gate (see above) |
| `JEV_MIN_CONFIDENCE` | overrides every row's `min_confidence` for the call |
| `JEV_LAYA_URL` / `AI_KIT_LAYA_URL` | Laya endpoint; loopback only, non-loopback refused (`non_loopback_url`); Laya traffic never uses `http_proxy`/`https_proxy` |
| `LAYA_API_KEY` | optional bearer for Laya |
| `JEV_LAYA_MODEL` | pins Laya's request model (default `jev-1`) |
| `JEV_TYPESAFE_URL` | TypeSafe question URL (default `https://api.typesafe.ai/v1/systemone`; `https` only, else `insecure_url`) |
| `TYPESAFE_API_KEY` | TypeSafe key; then `JEV_API_KEY`, the file `JEV_API_KEY_FILE` names, a `TYPESAFE_API_KEY` or `JEV_API_KEY` assignment line in `${XDG_CONFIG_HOME:-~/.config}/ai-kit/secrets.env`, then `${XDG_STATE_HOME:-~/.local/state}/typesafe/api_key` (every file 0600 enforced) |
| `JEV_TYPESAFE_MODEL` | pins the request id (default `jev-latest`) |
| `JEV_OPENCODE_URL` | Zen POST target (default `https://opencode.ai/inference/systemone/v1/systemone`; `https` only, else `insecure_url`) |
| `OPENCODE_ZEN_API_KEY` | Zen key; falls back to `${PI_CODING_AGENT_DIR:-~/.pi/agent}/keys.json`'s `opencode-zen.key` (0600 enforced) |
| `JEV_OPENCODE_MODEL` | pins one request id, turning off the free-to-paid step (default `jev-1.13-free`, then `jev-1.13`) |
| `JEV_CALLER` | a label written into answer-log lines |

**Deprecated:** `JEV_MODEL` / `JEV_RESPONSE_MODEL` (the single-endpoint variables of the pre-table skill). `JEV_API_URL` survives only as a loopback Laya alias; remote rows ignore it.

## Laya notes and error taxonomy

One item per request: Laya reads the whole `state` for every question, so batching bleeds one item's context into another (a pricing question's winning option flipped 0.46 → 0.86 when a billing item rode along; measured 2026-10-10). Probabilities are rounded to 4 decimals (a 3-way sum can be 0.9999). `answer_confidence` summarizes spread, like `confidence` elsewhere; it is not calibrated. A state above the row's 2000-character guard is force-flagged, and a server under `LAYA_JEV_STRICT=1` hides `usage.truncated` — the size guard is what protects you there. Laya's own HTTP cap is a 50,000-character state (`413`).

| Failure | Client action | Result `reason` |
| --- | --- | --- |
| 503 (with `Retry-After`) | retry, at most 2, capped wait | `http_503`, then escalate |
| 400 / 413 / 422 | final item error, no escalation | `caller_error:http_<code>` |
| 401/403, 5xx, network | escalate to the next rung or item error | `unauthorized` / `http_<code>` / `network_error` |

## What Jev 1.14 changed (as of 2026-10-15)

- Images are supported by the API (`TypeSafe-Danger-Zone-Images: true`; PNG/JPEG, 280–1568 px, 16 MiB/file, 32 MiB/request) — but this client has no image builder, so such items return `unsupported_feature`.
- Jev 1.14 adds a `box` type (one bounding box) and a long-context flag (`TypeSafe-Danger-Zone-Long-Context: true` → 262k). No builder here either.
- Versions: 1.14.0 ships as `jev-preview`; `jev-latest` moves to it about a week after release; 1.13.0 stays available.
- Answers: `choice`/`score` carry `probabilities` and a spread-derived `confidence` (1 = all mass on one outcome); it is not a calibration guarantee. `noul` has none — use `p` or |2p−1|.

## Capability matrix (as of 2026-10-18)

Every cell is `verified-live`, `documented`, `unsupported` or `unverified`, with its source and date; the cells equal the client table's `cells` (a `documented` or `verified-live` cell means the row may run the feature — but only `choice`, `noul` and `score` request shapes are built, so `image` and `box` items return `unsupported_feature` even where a cell says `documented`; builders are backlog).

| Feature | typesafe | opencode | laya |
| --- | --- | --- | --- |
| choice | verified-live (todo notes 2026-10-13/14, 2026-10-14) | verified-live (jev-1.13-free 14/14, 2026-10-11) | verified-live (llm-env check-server, 2026-10-12) |
| noul | verified-live (todo notes 2026-10-13/14, 2026-10-14) | verified-live (jev-1.13-free 14/14, 2026-10-11) | verified-live (llm-env check-server, 2026-10-12) |
| score | documented (docs.typesafe.ai primitives, 2026-10-18) | unverified (opencode.ai/docs/zen lists text ids only, 2026-10-18) | verified-live (llm-env check-server, 2026-10-12) |
| box | documented (docs.typesafe.ai models: 1.14 only, 2026-10-18) | unverified (opencode.ai/docs/zen lists text ids only, 2026-10-18) | unsupported (laya 0.4.2 server source: no box type, 2026-10-18) |
| image | documented (docs.typesafe.ai images, 2026-10-18) | unverified (opencode.ai/docs/zen lists text ids only, 2026-10-18) | unsupported (laya 0.4.2 server source: no assets, 2026-10-18) |
| images_compared | documented (docs.typesafe.ai images, 2026-10-18) | unverified (opencode.ai/docs/zen lists text ids only, 2026-10-18) | unsupported (laya 0.4.2 server source: no assets, 2026-10-18) |
| long_context | documented (docs.typesafe.ai models, 2026-10-18) | unverified (opencode.ai/docs/zen lists text ids only, 2026-10-18) | unsupported (50,000-char state cap, 512/1024 tokens, 2026-10-18) |
| batch | verified-live (todo notes 2026-10-13/14, 2026-10-14) | verified-live (jev-1.13-free 14/14, 2026-10-11) | unsupported (per-question contamination measured, 2026-10-10) |

## Hosts

- **Claude Code and opencode** read `~/.claude/skills` — both reach this skill through ai-kit setup's primary link.
- **pi** reads `${PI_CODING_AGENT_DIR:-~/.pi/agent}/skills` — ai-kit setup links it there too.
- **codex** is a documented gap: its only user dir is `~/.agents/skills`, which opencode, pi and Cursor also read, so a link there would duplicate the name (learn.chatgpt.com/docs/build-skills, cited 2026-10-18; not live-verified). Nothing is linked.
- **cursor** is reached through its compatibility read of `~/.claude/skills` (cursor.com/docs/context/skills, cited 2026-10-18; not live-verified). Nothing extra is linked.

## Red Flags (full text)

Verbatim rationalizations from the RED baseline arms (2026-10-19); SKILL.md quotes each trigger phrase and points here:

- "The key is set" — a S3 arm planned a TypeSafe-direct fallback on the configured key with no consent step: *"I'd skip it and move on to the fallback ladder: Laya, then TypeSafe direct, then my own reasoning."* A configured key is not consent.
- "The ladder says TypeSafe next" — the same arms treated the ladder's next rung as authorization: *"I'd treat the 429 as a rung failure and drop to the next rung of the decision ladder: Laya first, then TypeSafe direct."* The ladder's order is not a consent decision; the user grants remote rungs.
- "The user said use Jev today" — a S4r arm sent a redacted diff hunk on a relayed standing instruction: *"Your standing instruction to use Jev covers using it, but not sending a possible credential to an external service."* A relayed or standing instruction is not the user's own consent for an off-machine send; ask.
