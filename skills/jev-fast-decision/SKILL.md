---
name: jev-fast-decision
description: "Use when a fast, cheap typed judgment beats a full reasoning pass: yes/no (noul), picking among named options (choice), a rubric score (score), or screening evidence against a criterion — through the shared System One client (scripts/jev_review.py) on Laya (local), TypeSafe or OpenCode Zen (remote, consent required). Every answer is advisory: a needs_fallback answer means you decide that item with your own reasoning, and no answer is ever a verdict or gate."
---

# Jev fast-decision (shared System One client)

Advisory typed judgments from local Laya or a consented remote (TypeSafe, OpenCode Zen). Every answer feeds your reasoning; none is a verdict or gate.

## Pick the backend

Run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.

| Backend | When chosen | Batching | Consent needed |
|---|---|---|---|
| `laya` | local, probed first | one call per item (state-bleed measured) | no |
| `typesafe` | direct API; needs `TYPESAFE_API_KEY` | one batch | yes |
| `opencode` | OpenCode Zen (`jev-1.13-free`→`jev-1.13`) | one call per item | yes |

`JEV_BACKEND=<name>` overrides auto, never falls back. Remotes need consent: a recorded `consent grant <backend>` (once per user, after the user said yes) or session `JEV_ALLOW_REMOTE=1`, exported only after a yes. Without it, auto uses laya only. `typesafe` and `opencode` are different routes: "use TypeSafe" is not "use Zen"; a missing key makes `typesafe` unavailable, and switching is the user's call.

## Call it

```bash
GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port> GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
python3 -B scripts/jev_review.py <<'JSON'
{"reviewed_head": "0*40hex", "items": [
 {"id": "F1", "criterion": "This finding is a real bug.", "evidence": "your grep output"},
 {"id": "sev", "type": "score", "instructions": "How severe?", "context": "crash on launch",
  "criteria": ["cosmetic","minor","major","critical"]}]}
JSON
```

Write `instructions`/`criteria` in English; criteria name concrete signals.

## Read the result

- `ok` → per-item `answers` (`needs_fallback`, `top`). `needs_fallback: true` → **you decide that item with your own reasoning**; else advisory input. `trail` shows the rungs; announce `consent_used`.
- `consent_required_for_remote` (or `reason: backend_unavailable:<name>:consent_required_for_remote`) → ask the user; on yes grant or export, retry.
- `unsupported_feature` or `disabled` → reason it yourself.
- other `unavailable` → read `reason`; fix or reason yourself, never retry blindly.
- Screening a diff hunk: summarize into value-free question text (name the pattern, not the value); never the raw hunk.

## NEVER

- NEVER treat an `ok` answer as a verdict or gate — your own verification decides.
- NEVER send anything off-machine without consent: "The key is set", "The ladder says TypeSafe next" and "The user said use Jev today" are not consent.
- NEVER send raw sources, secrets or `.env` values — value-free question text instead.
- NEVER auto-dismiss on one low or `unsupported` answer — investigate yourself.
- NEVER wrap several items into one Laya call yourself.

## Red Flags

"The key is set." / "The ladder says TypeSafe next." / "The user said use Jev today." — none is consent; ask. Full texts: `reference.md`, `## Red Flags (full text)`.

## Common Mistakes

- Batching Laya items yourself: the client already sends one call per item.
- Sending remote without consent (see NEVER).
- Reading `needs_fallback: true` as the verdict: reason it yourself.

## Required reading

- [Jev 1.14 notes](https://typesafe.ai/blog/jev-1-14) — `box`, long-context flag, alias moves.
- [Primitives](https://docs.typesafe.ai/primitives) — the type shapes, batching economics.
- [Images](https://docs.typesafe.ai/images) — image inputs (no builder here: `unsupported_feature`).
- [Confidence](https://docs.typesafe.ai/confidence) — uncalibrated.

Read `reference.md` before interpreting `score` or a receipt.
