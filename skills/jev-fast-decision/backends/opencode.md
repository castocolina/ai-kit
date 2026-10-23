# Backend: opencode (OpenCode Zen — remote, consent required)

OpenCode Zen's System One endpoint. A remote row: it runs only with consent (a recorded
`consent grant opencode` or a session `JEV_ALLOW_REMOTE` naming it). The gate covers both ids
below — the free promotion does not waive consent.

## Endpoints and ids

- Default base: `https://opencode.ai/zen/v1` (override `JEV_OPENCODE_URL`). Two System One
  paths exist: the live-verified `/zen/v1/systemone` (this row's default, confirmed 2026-10-11)
  and the docs' `/inference/systemone/v1/systemone` (opencode.ai/docs/zen, cited 2026-10-18).
  If the default path ever 404s, point `JEV_OPENCODE_URL` at the other one; the client never
  follows redirects.
- Ordered model ids: `jev-1.13-free`, then `jev-1.13` (pin both with `JEV_OPENCODE_MODEL`).
  Responses fullmatch `opencode-*`; the result's `model` is the id that answered. Choice
  probabilities may arrive as integers 0/1.
- One question per call on this row (`batch: false`).

## Free-to-paid and the budget-429 rule

- Fall through from `jev-1.13-free` to `jev-1.13` only on: 429 with any body (including
  `FreeUsageLimitError`), 5xx, network error, or a 400 whose body says `Model is unavailable`
  (the free promotion ended). Never on other 400s or 401/403. No second try of the free id in
  the same call; no cooldown file.
- A paid 429 is `Account budget exceeded`: the ladder stops there — it never asks the user for
  budget. A free failure is an `attempts` entry such as
  `{"backend": "opencode", "model": "jev-1.13-free", "reason": "http_429"}`.
- The free-tier reset window is undocumented (issue #32391; reported waits run from hours to
  about 17 h; no `Retry-After`).
- Key: `OPENCODE_ZEN_API_KEY`, else the `opencode-zen.key` field of `~/.pi/agent/keys.json`.
  Agent shells that do not inherit login-shell exports still get the file source.

## Client identity

The script sends `User-Agent: jev-fast-decision/2.0` — Zen's Cloudflare edge answers 1010 to
the bare `Python-urllib/x.y` default. Do not spoof the OpenCode client UA (issue #42074).

## Status

`choice`, `noul` and batch are `verified-live` on `jev-1.13-free` (14/14, 2026-10-11); `score`,
images, `box` and long context are `unverified` (the Zen docs list text ids only). Live use is
waiting for budget; when it returns, confirm which endpoint path answers and record it here.
