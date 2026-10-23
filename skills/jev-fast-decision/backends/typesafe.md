# Backend: typesafe (remote, consent required)

TypeSafe's direct Jev API. A remote row: it runs only with consent (a recorded
`consent grant typesafe` or a session `JEV_ALLOW_REMOTE` naming it), and everything you send
leaves the machine.

## Endpoint, models, keys

- URL: `POST https://api.typesafe.ai/v1/systemone` (override `JEV_TYPESAFE_URL`); the probe is a
  bearer `GET /v1/models` on the same origin — it checks the key before any question is sent.
- Request model: `jev-latest`. **The alias moves**: `jev-preview` is 1.14.0, and `jev-latest`
  moves onto it about a week after a release; `jev-1.13.0` stays available for a while.
  Versioned request ids are documented (`docs.typesafe.ai/models`, cited 2026-10-18) but not
  live-tested here — pin with `JEV_TYPESAFE_MODEL` if you need a fixed id, and accept any
  response whose `model` fullmatches `typesafe-*` (the exact returned string is unverified on
  this host: record it on the first live call).
- Key sources, in order: `TYPESAFE_API_KEY`, then the first line of
  `${XDG_STATE_HOME:-~/.local/state}/typesafe/api_key` (0600 enforced — a world-readable key
  file is refused). Non-interactive agent shells do not inherit login-shell exports, so the
  file source is the one that works there; export the variable only for the session, after the
  user consented.

## Behaviour

- Batching: one request whose `state` holds every item (no per-question channel contamination
  observed — `verified-live`, todo notes 2026-10-13/14). Probabilities are rounded to
  2 decimals (a 3-way sum can be 0.99).
- Images and `box` are documented (1.14; images header, PNG/JPEG, 280–1568 px, 16 MiB/file,
  32 MiB/request) but this client has no builder: such items return `unsupported_feature`.
- Long context: 64k per request / 32k per question documented; the
  `TypeSafe-Danger-Zone-Long-Context: true` header raises both to 262k (not built here).

## Errors

| Failure | Client action |
| --- | --- |
| 401 / 403 | escalate + `unauthorized` (the key is wrong) |
| 503 (+ `Retry-After`) | retry, at most 2, then escalate |
| 402 | next model id; there is none here, so the item ends with `http_402` (final: the ladder does not move on to OpenCode Zen) |
| other 4xx | final `caller_error:http_<code>` for that item |

## Consent

Questions go to `api.typesafe.ai`; **retention terms unverified** — the grant announcement says
exactly that and promises nothing about deletion or storage. Revoke any time with
`consent revoke typesafe`.
