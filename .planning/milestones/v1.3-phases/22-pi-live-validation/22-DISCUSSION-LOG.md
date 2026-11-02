# Phase 22: Pi Live Validation - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-10-14
**Phase:** 22-pi-live-validation
**Mode:** assumptions (`--analyze --all --batch`), jev screening, best over easy, CodeGraph
**Areas analyzed:** What GSD does on pi; pi plans and matrix; R1 parser and R4 smoke

## Assumptions Presented

The analyzer was `gsd-assumptions-analyzer` (sonnet), with 85 tool calls. It ran a scratch
`--pi --local` install under a temp HOME, a fake-ExtensionAPI handler probe and a localhost mock
provider. No real model call; the real `~/.pi/agent` and `~/.gsd/defaults.json` are unchanged.

| Assumption | Confidence | Evidence |
|---|---|---|
| GSD on pi spawns nothing | Confident | `gsd.cjs:290-380`; scratch install tree |
| Only `pi.sonnet` steers, session-wide | Likely | `gsd.cjs:233-272,386`; handler probe; mock wire log |
| Evidence ladder L0–L3, trust recorded | Confident | `resolve-model` returns `""` under `omit` |
| pi plan: opt-in bare `pi.sonnet` only | Likely | hook passes the value verbatim |
| Matrix oracle host-parameterized | Confident | 17 D-21; `RUNTIME_PROFILE_MAP.pi` |
| `agent_skills` inert on pi | Likely (inferred) | no agent files installed |
| RPC JSON beats the table | Likely | `list-models.js:10-18` `toFixed(1)`; RPC 0.17 s |
| Installer under temp HOME | Confident | `install.js:6963-7012` |
| pi preconditions (signal, `--skill`, login) | Confident | `detection.py:83-86`; settings.json |

## jev screening

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| E1 verdict vocabulary | fourth_verdict 0.94 | – | D-02 |
| E2 pi plan | fill_all 0.74 | opt_in_bare 0.53 (fb), second opinion | **Own reasoning:** opt-in bare `pi.sonnet`; `fill_all` writes inert keys and breaking `provider/model` strings (D-05, ledger) |
| E3 agent_skills | label_agent_skills 0.73 | – | D-06 |
| E4 parser source | hybrid 0.46 (fb) | rpc_source 0.75 | D-04 |

## Corrections Made

No user corrections. Amendments: 22-SPEC R1 (RPC source and its edge rows), R2 (fourth
verdict), R3 (agent_skills, opt-in sonnet key); 18 D-25; 17 D-22.

## External Research

Routed to the researcher (CONTEXT `<specifics>`): real-provider steering, pi trust persistence,
`thinkingLevelMap` nulls, upstream gsd-core quirks.
