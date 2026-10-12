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

System One is implemented and running in llm-env (commits `a78b964..4c725d0`). These facts change the Laya backend's assumptions in `PLAN.md`:

- **Non-English input returns HTTP 500.** The service runs with `HF_HUB_OFFLINE=1` and `LAYA_MAX_LOADED` set to the number of configured models, and only `english` is loaded. Laya routes non-English or non-Latin text to the `multilingual` checkpoint, so such a request now returns `{"detail":"inference failed"}` in about 18 ms instead of downloading a model at runtime. The skill must treat a Laya 500 as `backend_unavailable:laya:http_500`, and then:
  - **auto mode:** fall through to the next backend;
  - **explicit `JEV_BACKEND=laya`:** report the failure and do not retry.

  Add a test for this. Accepting non-English input on Laya means adding `multilingual` to `system_one.models`, raising `vram_reserve_mib` by about 3 GB, and re-running `make setup`.
- **Measured on the real service:** p50 is about 13 ms per request on the RX 9070 XT, VRAM about 2993 MiB with `english` only, and idle CPU is 0%. Use these values instead of the plan's older ~12 ms / 1-core-idle figures. The idle burn was a ROCm 7.14 runtime bug, fixed in llm-env by switching to the torch `rocm7.2` wheels.
- **Endpoint and activation:** the service listens on `http://127.0.0.1:8010/v1/systemone` and has no auth. `make print-endpoints` prints the activation line: `GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:8010 GSD_PATH_JEV_TIMEOUT_SECONDS=20`.
- **Live-validated cases:** llm-env's `make check-server` already runs five single-request cases against the live service: choice billing (0.98), choice technical (0.95), noul destructive (0.77), noul safe (0.18), and score urgent (argmax "2", 0.99). Reuse them as Laya exemplars in `evals/cases.jsonl`. They are English, one item per request, and have clear margins.
- **Not in the plan:** `make backup` (OmniRoute combos + connections) exists in llm-env since `acd5a17`. It does not touch System One.
