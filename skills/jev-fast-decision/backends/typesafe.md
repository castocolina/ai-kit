# Backend: typesafe (remote, consent required)

TypeSafe's direct Jev API. A remote row: it runs only with consent (a recorded
`consent grant typesafe` or a session `JEV_ALLOW_REMOTE` naming it), and everything you send
leaves the machine.

## Endpoint, models, keys

- URL: `POST https://api.typesafe.ai/v1/systemone` (override `JEV_TYPESAFE_URL`, which must be
  `https`: any other URL is refused as `insecure_url`); the probe is a bearer `GET /v1/models`
  on the same origin — it checks the key before any question is sent.
- Request model: `jev-latest`. **The alias moves**: `jev-preview` is 1.14.0, and `jev-latest`
  moves onto it about a week after a release; `jev-1.13.0` stays available for a while.
  Versioned request ids are documented (`docs.typesafe.ai/models`, cited 2026-10-18) but not
  live-tested here — pin with `JEV_TYPESAFE_MODEL` if you need a fixed id. Responses fullmatch
  `jev-<version>` (`jev-1.13.0`, `jev-1.14.0-preview`; SPEC R5): the response names the
  versioned id that answered, whatever alias was asked for.
- Key sources, in order (D-07): `TYPESAFE_API_KEY`, `JEV_API_KEY`, the first line of the file
  `JEV_API_KEY_FILE` names, a `TYPESAFE_API_KEY=` or `JEV_API_KEY=` line in
  `${XDG_CONFIG_HOME:-~/.config}/ai-kit/secrets.env`, then the first line of
  `${XDG_STATE_HOME:-~/.local/state}/typesafe/api_key`. Every file must be 0600 — a group- or
  world-readable one is refused. Non-interactive agent shells do not inherit login-shell
  exports, so the file sources are the ones that work there; export a variable only for the
  session, after the user consented.

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
| 402 | next model id; there is none here, so the item escalates to the next consented rung (OpenCode Zen); with no rung left it ends with `http_402` |
| other 4xx | final `caller_error:http_<code>` for that item |

## Consent

Questions go to `api.typesafe.ai`; **retention terms unverified** — the grant announcement says
exactly that and promises nothing about deletion or storage. Revoke any time with
`consent revoke typesafe`.
