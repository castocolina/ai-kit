---
created: 2026-10-11T22:50:00.000Z
title: Execute the System One decision-skill plan (jev-fast-decision, 3 backends)
area: skills
severity: major
files:
  - .planning/docs/system-one-decision-skill/PLAN.md
  - .planning/docs/system-one-decision-skill/README.md
  - ~/.claude/skills/jev-fast-decision/
---

## Problem

The global skill `jev-fast-decision` has to choose between three System One backends and gate each one:

- **Local Laya:** sends one item per request.
- **TypeSafe direct.**
- **OpenCode Zen:** tries `jev-1.13-free` first, then falls back to the paid `jev-1.13`.

Every backend needs an availability probe, an explicit `JEV_BACKEND` choice, and consent for the remote ones. A low-confidence answer must hand off to the main orchestrator (`needs_fallback`).

The full plan was reviewed over 17 rounds and is at `.planning/docs/system-one-decision-skill/PLAN.md`.

## Solution

- **Execution mode:** run the plan with superpowers:executing-plans (native). The skill directory is not a git repo, so Task 0 snapshots it and each checkpoint is a `diff -ru`.
- **Prerequisite:** Tasks 0–4 work offline. Tasks 5–8 need llm-env's System One enabled and healthy on 127.0.0.1:8010, which comes from llm-env Plan A.
- **Owner choices at execution time:** Task 8 asks the owner for the judge lanes and the FIX command. Do not hardcode models.
- **Reference implementation:** `scratchpad/v3/skill/` has the plan's code applied and green (45 passed).

## Notes from the llm-env implementation (2026-10-12)

System One is implemented and running in llm-env (commits `a78b964..413faa0`). These facts change the Laya backend's assumptions in `PLAN.md`:

- **Endpoint and activation:** the service listens on `http://127.0.0.1:8010/v1/systemone` and has no auth. `make print-endpoints` prints the activation line: `GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:8010 GSD_PATH_JEV_TIMEOUT_SECONDS=20`.
- **Languages:** `english` and `multilingual` are both loaded by default. Weights are prefetched at setup and the service runs offline (`HF_HUB_OFFLINE=1`). Laya picks the checkpoint from the language of the `state`, not of the instructions. Non-English, very short, or accented text goes to `multilingual`, and all of it returns 200. To force the english checkpoint, send `"model": "english"` in the body.
- **Write the prompts in English:** this means `instructions` and `criteria`, whatever language the chat is in. The `state` stays in the user's language. Tests showed English instructions scoring the same or slightly better. The skill must translate or template them in English.
- **Concrete criteria:** a vague catch-all such as `other: "everything else"` lowers accuracy. Each criterion should name concrete signals, for example `billing: "charges, invoices, refunds"`.
- **Error taxonomy:** the skill should act on each kind of failure differently.

  | Response | Meaning | Skill action |
  |---|---|---|
  | `503` + `Retry-After: 1` | busy; more than 64 requests in flight (`LAYA_MAX_CONCURRENT`), no queue | wait 1 s, retry at most 2 times, then fall back |
  | `500` `inference failed` | the model failed | fall back without retrying |
  | `400` / `413` / `422` | bad request from the caller (skill bug) | escalate to the orchestrator; no remote fallback, since it would fail too |
  | connection refused or timeout | backend unavailable | fall back |

  "Fall back" means the next backend in auto mode. With an explicit `JEV_BACKEND=laya`, the skill reports the failure instead.

  Add a test per row.
- **Measured on an RX 9070 XT:**
  - **Sequential:** about 60 req/s at p50 ~15 ms.
  - **8 to 16 concurrent:** about 78 req/s at p50 100 to 200 ms, because the GPU serialises the work.
  - **First request after start:** already warm, since start sends a warm-up request.
  - **After 10 minutes idle:** both models unload (`LAYA_IDLE_UNLOAD_SECONDS=600`), and the next request takes about 0.4 s to reload.
  - **Idle CPU:** 0%.
  - **Process VRAM:** about 4.2 GB, against a reserve of 5120 MiB.
  - **Container RAM:** about 2.2 GB, with a floor of 2.5 GB and a cap of 4.5 GB.
  - **Leaks:** none. VRAM plateaued over a 20k-request soak.

  Use these values in place of the plan's older figures. `make system-one-benchmark` reproduces them.
- **Live-validated cases:** llm-env's `make check-server` already runs five single-request cases against the live service:

  | Type | Case | Result |
  |---|---|---|
  | choice | billing | 0.98 |
  | choice | technical | 0.95 |
  | noul | destructive | 0.77 |
  | noul | safe | 0.18 |
  | score | urgent | argmax "2", 0.99 |

  Reuse them as Laya exemplars in `evals/cases.jsonl`. They are English, one item per request, and have clear margins.
- **Not in the plan:** `make backup` (OmniRoute combos + connections) exists in llm-env since `acd5a17`. It does not touch System One.

## Notes from live use in tools-installer (2026-10-13/14)

The live skill was used for 19 decisions while specifying and discussing tools-installer Phases 17–25 (session 0a994334). These findings change the plan:

- **TypeSafe direct rounds probabilities to 2 decimals.** With the plan's `_PROB_SUM_TOLERANCE = 1e-3` (also in `scratchpad/v3/skill`), valid answers came back `invalid_response`. The live skill now uses `2e-2`; the plan must carry the same value, with a test that a 2-decimal answer summing to 0.99 or 1.01 is accepted.
- **Laya is weak on design questions.** It scored ≤0.05–0.67 on them (mostly `needs_fallback`), against TypeSafe's 0.60–1.00. The escalation that worked: Laya first, one item per call; TypeSafe direct on `needs_fallback` (batching is fine there); the main model's own reasoning when both are low. The plan's auto mode should implement exactly this ladder.
- **The live TypeSafe activation:** `JEV_API_URL=https://api.typesafe.ai/v1/systemone JEV_MODEL=jev-latest JEV_RESPONSE_MODEL=jev-1.13.0`, with the key read from a file into `JEV_API_KEY` and never printed.
- **The Zen budget is exhausted.** It returns 429 "Policy budget exceeded" on `jev-1.13-free` too; bare `jev-free` gives "Model is unavailable". The free→paid ladder has to treat a 429 budget error as "backend unavailable", not as a transient error to retry.
- **Decisions must be logged:** each decision needs a Laya column, a TypeSafe column and the locked decision with its reason, and an override when the project docs contradict the model. ai-kit will ship this chain as a spec/discuss skill (v1.3 roadmap), with the decision models optional.
- **Jev 1.14 capabilities (uz, 2026-10-15) — required reading before executing the plan:** [Jev 1.14 release notes](https://typesafe.ai/blog/jev-1-14), [Primitives](https://docs.typesafe.ai/primitives), [Images](https://docs.typesafe.ai/images), [Confidence](https://docs.typesafe.ai/confidence).
  - Jev supports images on both 1.13 and 1.14: header `TypeSafe-Danger-Zone-Images: true`; top-level `assets` (multipart `part` or `data_base64`+`format`); PNG or JPEG only, 280–1568 px per side, 16 MiB per file, 32 MiB per request.
  - 1.14 adds a `box` type (one bounding box) and a long-context flag. It ships as `jev-preview`; `jev-latest` follows about a week later.
  - `confidence` is a peakedness summary, not a calibration guarantee. `noul` has no `confidence`; use p or |2p−1|. Set thresholds per question and per risk.
  - The rework must decide how image questions, `box` and the `jev-preview`/`jev-latest` choice reach each backend (TypeSafe direct; Laya and Zen support unverified). The live skill already got a "Required reading" note (2026-10-15).
- **Target home (uz, 2026-10-15):** `jev-fast-decision` stays a global skill (`~/.claude/skills/jev-fast-decision`, not under VCS) for now. The plan's end state moves it into this repo's pack as `skills/<name>/`, installed by `tools/install.sh`/`tools/setup.py` with a symlink like every other ai-kit skill. tools-installer's `global:jev-fast-decision` entries in `.planning/config.json` would then point at the ai-kit copy. Fold the live edits made on 2026-10-15 (the "Required reading" section) into the repo copy when it moves.
