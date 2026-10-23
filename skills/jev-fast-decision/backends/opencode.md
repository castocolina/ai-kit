# Backend: opencode (OpenCode Zen — remote, consent required)

OpenCode Zen's System One endpoint. A remote row: it runs only with consent (a recorded
`consent grant opencode` or a session `JEV_ALLOW_REMOTE` naming it). The gate covers both ids
below — the free promotion does not waive consent.

## Endpoints and ids

- `JEV_OPENCODE_URL` is the complete POST target, defaulting to the documented
  `https://opencode.ai/inference/systemone/v1/systemone` (opencode.ai/docs/zen, checked
  2026-10-23); the client does not append a path or follow redirects. A live check on 2026-10-11
  also saw `/zen/v1/systemone` answer. The URL must be `https` (else `insecure_url`). The
  probe is a bearer `GET /inference/v1/models` on the same origin — Zen's documented model list
  (opencode.ai/docs/zen, 2026-10-23). The docs show that list without auth, so a 200 proves the
  endpoint is reachable, not that the key works: `--probe` marks this row `key_check:
  unverified`, and a bad key first shows up as a 401/403 on the question itself.
- Ordered model ids: `jev-1.13-free`, then `jev-1.13`. `JEV_OPENCODE_MODEL` pins one id: the
  client then sends only that id, so there is no free-to-paid step.
  Responses fullmatch `jev-<version>` (SPEC R5); the result's `model` is the id that answered. Choice
  probabilities may arrive as integers 0/1.
- One question per call on this row (`batch: false`).

## Free-to-paid and the budget-429 rule

- Current client behavior (verified in `scripts/jev_review.py`): 402/429 advances from
  `jev-1.13-free` to `jev-1.13`; 5xx retries the same model with bounded backoff, then escalates;
  network errors escalate; other 4xx errors are caller errors. The client currently discards the
  error body, so it does not special-case a 400 `Model is unavailable` response. Do not rely on
  a free-to-paid transition for 5xx, network errors or 400 until code and tests implement it.
- A paid 429 is `Account budget exceeded`: the item escalates past this row, and since Zen is the
  last rung it ends there with `http_429` — the client never asks the user for budget. An
  `attempts` entry is written only when the row's final outcome is a failure, and its
  `model` is the id that gave that error: a free 429 recovered by the paid id leaves none, both
  refused leaves `{"backend": "opencode", "model": "jev-1.13", "reason": "http_429"}`.
- The free-tier reset window is undocumented (issue #32391; reported waits run from hours to
  about 17 h; no `Retry-After`).
- Key: `OPENCODE_ZEN_API_KEY`, else the `opencode-zen.key` field of
  `${PI_CODING_AGENT_DIR:-~/.pi/agent}/keys.json` (pi's key file; 0600 enforced like TypeSafe's —
  a group- or world-readable file is refused). Agent shells that do not inherit login-shell
  exports still get the file source.

## Client identity

The script sends `User-Agent: jev-fast-decision/2.0` — Zen's Cloudflare edge answers 1010 to
the bare `Python-urllib/x.y` default. Do not spoof the OpenCode client UA (issue #42074).

## Status

`choice`, `noul` and batch are `verified-live` on `jev-1.13-free` (14/14, 2026-10-11; the client
still sends one item per call); `score`, images, `box` and long context are `unverified` (the Zen
docs list text ids only), so this row refuses them: in auto mode a `score` item skips it, and with
`JEV_BACKEND=opencode` one `score` item stops the whole request with `unsupported_feature`. Live use is
waiting for budget; when it returns, confirm which endpoint path answers and record it here.
