# Phase 27: One-shot goal and loop prompt skill - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-10-14
**Phase:** 27-one-shot-goal-and-loop-prompt-skill
**Mode:** assumptions (`--analyze --all --batch`), decision ladder, best over easy, CodeGraph
**Areas analyzed:** Skill name and layout; generator CLI and questions; detection and the Phase 26 coupling; superpowers dependencies; strategy matrix; prompt file; OpenGSD readiness; e2e, zero-tests and cleanup; jev; tests and gates

## Assumptions Presented

The analyzer was `gsd-assumptions-analyzer` (sonnet), with 69 tool calls. It ran the following:
- `codegraph sync`;
- `roadmap analyze`, `init phase-op` and `runtime-identity` (read-only);
- `codex features list` and the hosts' `--help`;
- `cross-ai.mjs --print-argv` (offline);
- `decide.py detect`;
- a unittest zero-tests probe in a scratch directory.

It made no model calls.

| Assumption | Confidence | Evidence |
|---|---|---|
| `ai-kit-spec-goal-prompt` name | Unclear | `detect_framework.py`; `setup.py:516` |
| Phase 24 layout | Confident | 24 D-14; skill-judge layer list |
| CLI-boundary reuse | Likely | `_shared` ImportError on copy installs; 07 D-02 |
| Agent asks, script never prompts | Confident | Phase 24 scripts |
| detect/render, agent-reported tools | Likely | deferred tools in this session |
| Matrix via Phase 26 CLI | Likely | 26-SPEC R1 |
| Two labels per primitive | Likely | `codex features list` goals stable |
| Phase state sources | Confident | `roadmap analyze` lacks SPEC; `init phase-op` fields |
| Depends-on convention | Likely | writing-plans 6.4.1 header; 3/38 plans |
| Per-plan nesting | Unclear | `plan-review-convergence.md:171` |
| Matrix as code constant | Likely | `rules.py` RULES |
| Derive outlive/provable | Unclear | four-question cap |
| Block per strategy | Unclear | SPEC R2 |
| Flags-only autonomous line | Confident | `autonomous.md:21-62` |
| Strict custom-delimiter template | Likely | shell and JSON in the rails |
| Goals subfolder | Unclear | `.gitignore:17`; detect_framework substring |
| Readiness checks | Likely | `--print-argv` live; `config.json` |
| `cross_ai: true` frontmatter | Confident | `execute-phase.md:78-79,415` |
| Multi-signal e2e | Likely | Makefile `e2e-test`; PTY tests |
| Zero-tests marker table | Likely | unittest exit 5 live |
| Process-group cleanup | Likely | AGENTS.md Testing |
| Consent-gated jev | Likely | 24 D-07/D-10/D-11 |
| Properties plus one golden | Likely | Phase 24 tests |
| Explicit gate entries | Confident | `.pre-commit-config.yaml`, Makefile, pyproject |

## jev screening

One Laya call per item; `needs_fallback` items batched to TypeSafe direct. No high-confidence Laya
answer contradicted the evidence, so no second opinion was needed. Summaries only.

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| C1 name | goal_prompt 0.55 (fb) | spec_goal_prompt 0.84 | D-01 |
| C2 reuse | cli_boundary_and_copies 0.47 (fb) | cli_boundary_and_copies 0.97 | D-03 |
| C3 tools | agent_reports 0.36 (fb) | agent_reports 0.99 | D-05 |
| C4 matrix reuse | owner_cli_json 0.46 (fb) | owner_cli_json 0.82 | D-06 |
| C5 labels | one_label 0.57 (fb) | two_labels 0.96 | D-07 |
| C6 deps | depends_on_line_plus_ask 0.55 (fb) | depends_on_line_plus_ask 0.99 | D-08 |
| C7 nesting | inline_in_plan_subagent 0.44 (fb) | orchestrator_runs_task_dispatch 0.82 | D-09 (provisional; research item 3; ledger for uz) |
| C8 matrix home | python_constant 0.68 (fb) | python_constant 0.91 | D-10 |
| C9 derive | always_true 0.59 (fb) | derive_and_show 0.95 | D-11 |
| C10 blocks | block_per_strategy 0.60 (fb) | block_per_strategy 0.57 (fb) | **Own reasoning:** one block per strategy (D-13, ledger) |
| C11 template | code_sections 0.41 (fb) | custom_delimiter_strict 0.82 | D-14 |
| C12 location | dated_goals_subdir 0.43 (fb) | ignored_tmp 0.68 (fb) | **Own reasoning:** committable goals subfolder (D-15, ledger) |
| C13 readiness | runner_cli_and_reviewers 0.41 (fb) | runner_cli_and_reviewers 0.97 | D-16 |
| C14 e2e signals | multi_signal 0.81 | – | D-18 |
| C15 zero tests | generic_wording 0.67 (fb) | marker_table_plus_count 0.96 | D-19 |
| C16 cleanup | plain_instruction 0.52 (fb) | groups_and_printed_proof 0.95 | D-20 |
| C17 jev route | consented_guarded_route 0.57 (fb) | consented_guarded_route 1.00 | D-21 |
| C18 tests | properties_plus_one_golden 0.36 (fb) | properties_plus_one_golden 0.76 | D-22 |

## Live facts that changed the plan

- `/gsd-autonomous` greps its whole argument string for flags, so rails cannot follow it.
- GSD delegates a plan to cross-AI only when the plan's frontmatter has `cross_ai: true` and the
  config enables it.
- Superpowers plans have no dependency field.
- Deferred tools are invisible to a script, so the agent must report them.
- `--print-argv` and `decide.py detect` print absolute paths, so their output stays out of the
  file.

## Corrections Made

- 27-SPEC R1, R2, R3, R4 and R5 amended. Four Edge Coverage rows were added and the floor was
  recomputed; the check passes.
- 26-CONTEXT D-02 refined: `matrix --json` is a public contract for Phase 27.

## External Research

The open questions are listed in CONTEXT `<deferred>`.

# Update 2026-10-14 (uz answer)

- D-09: the orchestrator is the user-facing session and can launch subagents; reusing a subagent or starting a fresh one is its judgment. SPEC R4 amendment superseded; research item 3 moot.
