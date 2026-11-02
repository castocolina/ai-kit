---
name: jev-fast-decision
description: "Use when you (the agent) need a fast, cheap typed judgment instead of spending a full reasoning pass or spawning a subagent: yes/no (noul), picking among named options (choice), or a rubric score (score) — e.g. screening whether evidence supports a criterion, triaging a batch of candidate findings, routing among options, or rating severity. Supports batching several independent typed questions in one request. Calls TypeSafe AI's Jev model via OpenCode Zen. NOT for anything that needs to read/write code, run commands, or hold multi-step context — Jev answers typed questions against the state you supply (text; images too via TypeSafe's image flag, though this helper sends text only), nothing else. Advisory only: a Jev answer can inform your next step but never substitutes for your own verification or satisfies a gate on its own."
---

# Jev fast-decision screening (via OpenCode Zen)

Jev is TypeSafe AI's "System One" model: given a short `state` and one or
more typed questions, it returns typed answers with probabilities (`confidence` summarizes how peaked they are; TypeSafe does not claim it is calibrated)
— in parallel, per request, far cheaper and faster than a full reasoning
turn. This is a **fork** of `open-gsd/gsd-path`'s `jev-review` helper,
re-pointed from TypeSafe's direct API to **OpenCode Zen**, so it uses the
OpenCode Zen key already present on this machine (`opencode auth login`)
instead of a separate TypeSafe account.

**Disabled by default.** Nothing calls this unless you explicitly set the
env vars below for the session — never assume it's on.

## When to reach for it

- **Screening evidence** — does existing evidence actually support a review
  criterion, before looking closer yourself? (shorthand below; `choice` type)
- **Triaging a batch** — classify candidate findings into likely-real vs.
  likely-noise before investigating each one.
- **Routing/picking** — choosing among a short, named list of options when
  the choice is a classification, not a design decision (`choice` type).
- **Yes/no gating** — a single boolean judgment, e.g. "does this text ask
  for escalation?" (`noul` type).
- **Rating along a rubric** — severity, confidence, quality tier, etc., when
  the levels are describable in advance (`score` type).
- **Batching heterogeneous questions** — ask several independent choice/
  noul/score questions against the same `state` in one request; they run in
  parallel and cannot see each other's answers.

**Not for:** anything requiring tool use, multi-turn context, or judgment
that depends on code you haven't already summarized into the question text.
It answers against the state you give it — nothing else.

## Required reading: Jev's current capabilities (as of 2026-10-15)

Read these before designing a new kind of Jev call. They supersede older assumptions in this skill:
- [Jev 1.14 release notes](https://typesafe.ai/blog/jev-1-14)
- [Primitives](https://docs.typesafe.ai/primitives)
- [Images](https://docs.typesafe.ai/images)
- [Confidence](https://docs.typesafe.ai/confidence)

What they change:
- **Images are supported.** Send the `TypeSafe-Danger-Zone-Images: true` header. Each image goes in the top-level `assets` map, as a multipart `part` or as `data_base64` plus `format`. Reference it from `state`, `instructions` or `criteria`. Only PNG or JPEG, 280–1568 px per side, 16 MiB per file, 32 MiB per request. Jev 1.13 and 1.14 both accept images, but multimodal accuracy is weaker than text, so split image questions into simple parts.
- **New ways to ask.** Jev 1.14 adds a `box` type that returns one bounding box in an image. It also adds a long-context flag, `TypeSafe-Danger-Zone-Long-Context: true`.
- **Versions.** 1.14.0 ships as `jev-preview`, and `jev-latest` moves to it about a week after release. 1.13.0 stays available, with deprecation notices to come.
- **Answers.** Each `choice` and `score` answer carries `probabilities` and a `confidence` value, where 1 means all the probability is on one outcome and 0 means an even spread. `confidence` is not a calibration guarantee, so set thresholds per question and per risk. `noul` has no `confidence` field: use the yes-probability `p` itself, or compute |2p−1|.
- **This helper's gap (unverified beyond the docs).** `scripts/jev_review.py` sends text-only JSON to Zen `jev-1.13`. It sends no image header, no `assets` and no `box` type. Whether OpenCode Zen passes those through is unverified. For images or `box`, call TypeSafe's direct API.

## NEVER

- **NEVER** treat an `ok` answer as a verdict. It cannot satisfy or waive a
  criterion, change a gate, select a route, or authorize publication — your
  own verification still owns that decision.
- **NEVER** send text off this machine without the user's go-ahead first.
  "Disabled by default" is a kill switch, not consent — confirm with the
  user before the first call in a session, then only send the specific
  summarized criterion/evidence/instructions text the question needs.
- **NEVER** send raw source files, diffs that may contain secrets, credentials,
  or environment dumps — summarize into self-contained question text instead.
- **NEVER** remove the explicit `User-Agent` header from the script. Zen's
  Cloudflare edge silently 403s the bare `Python-urllib/x.y` default — easy
  to mistake for an auth problem (see `reference.md`).
- **NEVER** auto-dismiss a finding on a single `unsupported`/low-confidence
  answer alone, and never treat `unclear` or low confidence as a negative —
  both mean "investigate yourself," not "no."
- **NEVER** retry blindly on `unavailable` — fix the underlying cause
  (bad input, missing key, expired timeout) before retrying explicitly.
- **NEVER** ask a `choice`/`noul`/`score` question with nothing to judge
  against. `state` carries every item's text, not just the one in question
  — put the material being judged in that item's own `context` field (or
  inline in `instructions`), or the model answers confidently against
  nothing.

## Enable or disable

Set these in the session that will call it (not persisted — opt in each time):

| Variable | Value |
| --- | --- |
| `GSD_PATH_JEV` | Exactly `1` enables screening. Unset to disable. |
| `OPENCODE_API_KEY` | Optional. Your OpenCode Zen API key. When unset, the script falls back to the `opencode` entry (`type: "api"`) of opencode's own `~/.local/share/opencode/auth.json` (honors `XDG_DATA_HOME`) — only for the default Zen URL, never for `JEV_API_URL`. It reads only that one field and never prints it. |
| `GSD_PATH_JEV_TIMEOUT_SECONDS` | Positive finite seconds for the HTTP socket timeout — e.g. `20`. No default; required. |
| `JEV_API_URL` | Optional. Repoints the call at another System One server, e.g. local Laya `http://127.0.0.1:8000/v1/systemone`. With it set, an API key is optional. |
| `JEV_MODEL` / `JEV_RESPONSE_MODEL` | Optional. Request model string / model string the server returns. Laya: `jev-1` / `laya-rl-agent`. |
| `JEV_API_KEY` | Optional bearer key for the server at `JEV_API_URL` (falls back to `OPENCODE_API_KEY`). |
| `JEV_MIN_CONFIDENCE` | Optional, default `0.7`. Answers whose winning-option probability is below it carry `needs_fallback: true`: do not act on them, reason it through yourself (full model). |

> **Laya caveat — do not batch items with different `context`.** Laya reads the whole `state` for every
> question, so one item's context bleeds into the others (measured: a pricing question flipped from
> billing 0.46 to 0.86 once a billing item rode along in the same call). Send one call per item;
> at ~12 ms each it is cheap. Zen's Jev honours the per-item scope note, so batching is fine there.

## How to call it

Pipe one JSON object to the script. `items` can mix the shorthand and the
three general types in one batch:

```bash
GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
python3 -B ~/.claude/skills/jev-fast-decision/scripts/jev_review.py <<'JSON'
{
  "reviewed_head": "0000000000000000000000000000000000000000",
  "items": [
    {"id": "F1", "criterion": "This finding is a real bug, not a false positive.",
     "evidence": "grep output / reasoning you already have, as plain text"},
    {"id": "route", "type": "choice", "instructions": "Which team owns this ticket?",
     "context": "Customer message: \"My invoice charged me twice this month.\"",
     "criteria": {"billing": "about charges or invoices", "support": "about a product defect"}},
    {"id": "escalate", "type": "noul", "instructions": "Is the user asking for a human agent?",
     "context": "Customer message: \"This is the third time I've written in, please get me a person.\""},
    {"id": "severity", "type": "score", "instructions": "How severe is this bug?",
     "context": "Bug report: app crashes on launch for every user on iOS 18.",
     "criteria": ["cosmetic", "minor", "major", "critical"]}
  ]
}
JSON
```

`reviewed_head` must be a 40-hex-char string (a real commit SHA when you have
one; any syntactically valid placeholder otherwise). Each item needs a
unique, non-empty `id`, plus either:
- **Shorthand**: `criterion` + `evidence` (evidence may be empty — scores
  `unsupported` at high confidence by design, a grounding check not a flaw).
- **General**: `type` (`choice`/`noul`/`score`) + `instructions` + `criteria`
  shaped for that type (`choice`: ≥2 named options with descriptions;
  `noul`: optional `{"true":..., "false":...}`; `score`: 2–10 ordered level
  descriptions, low to high), plus an optional `context` string carrying the
  actual material being judged. `state` holds every item's text, not just
  the one in question — the script scopes each item's instructions to
  itself, but that only helps if the material to judge is actually *in*
  that item's `context` (or inline in `instructions`). A question with
  neither still gets a confident-looking, meaningless answer.

**Read the JSON status before anything else:**
- `disabled` → the env var wasn't set; proceed with ordinary reasoning.
- `unavailable` → network/auth/input problem (see `reason`); when `reason`
  is `invalid_input`, an `item` field often names the offending item's `id`
  — fix that item before retrying. Otherwise proceed with ordinary
  reasoning, don't retry blindly.
- `ok` → per-item answers under `answers`, shaped by type: `choice` gives
  `choice`/`probabilities`/`confidence`; `noul` gives a single `noul`
  probability (0=no, 1=yes, no separate confidence); `score` gives
  `score`/`legend`/`probabilities`/`confidence`. **This is advisory only.**

**MANDATORY — read `reference.md` before interpreting a `score` answer, before
recording any `ok` receipt in a durable artifact, or before building a
request with more than a couple of items.** It has the full type schemas,
confidence-interpretation guidance, and exact receipt format. Skip it for a
single quick shorthand choice call where you're only reading `choice`.
