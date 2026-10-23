# Backend: laya (local)

`laya` is the local System One server from the llm-env stack: a Jev checkpoint served on the
loopback interface. It is the ladder's first rung because it is local — no consent needed, no
data leaves the machine.

## Endpoint and activation

- Default `http://127.0.0.1:8010/v1/systemone`; probe is `GET /health` on the same origin.
- `JEV_LAYA_URL` / `AI_KIT_LAYA_URL` override the endpoint — **loopback only**; a non-loopback
  value is refused with `non_loopback_url` and nothing is sent. The legacy `JEV_API_URL` is
  honoured only when it is itself loopback.
- Activation line:
  `GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port> GSD_PATH_JEV_TIMEOUT_SECONDS=20`
- `LAYA_API_KEY` is an optional bearer; Laya needs no auth today.
- `JEV_LAYA_MODEL` pins the request model (default `jev-1`; responses fullmatch `laya-*`).

## One item per request

Laya reads the **whole `state`** for every question, so several items in one call bleed their
contexts into each other. Measured example (2026-10-10): a pricing question's winning option
went from billing 0.46 (alone) to 0.86 once a billing item rode along in the same call. The
client already sends one request per item on this row and puts only that item in each
`state.items`; never wrap several items into one Laya call yourself.

## Answer shape specifics

- Probabilities are rounded to 4 decimals, so a 3-way sum can be 0.9999 (the client tolerates
  2e-2 of drift overall).
- `answer_confidence` summarizes how peaked the distribution is; it is not calibrated, and
  `top` — not `confidence` — is what `needs_fallback` compares against the row's threshold.
- A state over the row's 2000-character guard is force-flagged (`needs_fallback: true`)
  without a request being trusted. Inside Laya's own limits, the model window (english 512 /
  multilingual 1024 tokens) truncates silently unless the server reports `usage.truncated`;
  `LAYA_JEV_STRICT=1` hides those fields, which is why the client keeps its own size guard.
  Laya refuses a state over 50,000 characters with `413`.
- Threshold: the row's `min_confidence` is calibrated from the live 32-case eval in this repo
  (see the eval object below); `JEV_MIN_CONFIDENCE` overrides it for one call.

## Errors

| Failure | Client action |
| --- | --- |
| 503 (+ `Retry-After`) | retry, at most 2, capped wait, then escalate |
| 400 / 413 / 422 | final `caller_error:http_<code>` for that item — a caller bug fails remotely too, so it never escalates |
| 401/403, other 5xx, network | escalate to the next rung, or the item error on an explicit backend |

Never retry blindly: fix the cause (input, timeout, server down) or reason the item yourself.

## Measured figures (2026-10-12, llm-env check-server)

choice/noul/score all `verified-live`; ~12 ms per call on the dGPU; idle unload after 600 s.

## Laya eval object (live, 2026-10-19)

Stored in `.planning/phases/21.1-atomic-reusable-decision-system-skills/eval/eval-results.json`
alongside `repeat_max_prob_diff` and `vague_alone_top`; `--calibrate` derives the row's
`min_confidence` from it. The v3 0.6 default came from synthetic rows, not from these.

## Starting it

`make start` in the llm-env repo with `system_one.enabled: true` in `models.yml` (provisioning
plan); check with `curl -sf http://127.0.0.1:8010/health`.
