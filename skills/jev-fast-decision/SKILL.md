---
name: jev-fast-decision
description: "Use when a fast, cheap typed judgment beats a full reasoning pass: yes/no (noul), picking among named options (choice), a rubric score (score), or screening evidence against a criterion, through the shared System One client on Laya (local), TypeSafe (remote, consent required). Advisory only: needs_fallback means you decide that item yourself, and no answer is a verdict or gate. Not for building TypeSafe into an app (typesafe-ai) or for editing code."
---

# Jev fast-decision (shared System One client)

Advisory typed judgments from local Laya or a consented remote (TypeSafe). Every answer feeds your reasoning; none is a verdict or gate.

## Pick the backend

From this skill's directory, run `GSD_PATH_JEV=1 python3 -B scripts/jev_review.py --probe` before the first call of a session (`disabled` means the switch is off); read `backends/<selected>.md` before the first call with that backend.

| Backend | When chosen | Batching | Consent needed |
|---|---|---|---|
| `laya` | local, probed first | one call per item (state-bleed measured) | no |
| `typesafe` | direct API; needs `TYPESAFE_API_KEY` from the environment | one batch | yes |

`JEV_BACKEND=<name>` overrides auto, never falls back. Without consent, auto uses laya only; a missing key makes `typesafe` unavailable.

## Callers (other skills and hooks)

Callers use one entry point, `scripts/jev_review.py`, found through `## Installed-skill lookup` in `reference.md`: `ladder [--second-opinion]` (stdin `{"items": [...]}`), `detect`, and `consent grant|revoke|show <backend>`.

```bash
GSD_PATH_JEV=1 python3 -B scripts/jev_review.py ladder <<'JSON'
{"items": [{"id": "c1", "type": "choice", "instructions": "Which fix is smaller?", "criteria": {"a": "one file", "b": "three files"}}]}
JSON
```

An installed copy without `ladder` exits 2 with `invalid choice`: treat it as no backend and re-run the ai-kit installer. Decide the item yourself on `needs_fallback`, an error or no answer.

## Call it

Screen calls: request shape in `reference.md` (`## Request shape`). Read `reference.md` before `choice` (≥2 options), `score` or receipt.

## Read the result

- `ok` → match ids to `answers` or `errors`. `needs_fallback: true` → **you decide that item with your own reasoning**; otherwise advisory.
- `consent_required_for_remote` (auto mode), or `reason: backend_unavailable:<name>:consent_required_for_remote` (explicit remote) → ask the user; on yes grant or export, retry.
- otherwise → the status table in `reference.md`.

## Consent (asked here, never by the caller)

A remote row at `consent_required_for_remote` (a `--probe` row's `reason`, a `detect` row's `status`) needs the user's yes. Ask once, naming each backend and host, "summaries only, never code or secrets", and the revoke command `consent revoke <backend>`. On yes run `consent grant <backend>`; recorded consent asks nothing. After a ladder run, announce `consent_used` for backends that answered an item.

## NEVER

- NEVER treat an `ok` answer as a verdict or gate — your own verification decides.
- NEVER send anything off-machine without consent: "The key is set", "The ladder says TypeSafe next" and "The user said use Jev today" are not consent.
- NEVER send raw sources, secrets or `.env` values — value-free question text instead.
- NEVER auto-dismiss on one low or `unsupported` answer — investigate yourself.
- NEVER wrap several items into one Laya call yourself.

## When the docs matter

When you design a new item shape, meet an uncovered TypeSafe feature, or a capability fact looks stale: follow the `typesafe:typesafe-ai` skill's live-docs flow if installed (also as `typesafe-ai`); else start at `https://docs.typesafe.ai/llms.txt`, then `changelog.md`, then `models.md` (links: `reference.md`, `## Docs flow`). Never install or copy that skill.
