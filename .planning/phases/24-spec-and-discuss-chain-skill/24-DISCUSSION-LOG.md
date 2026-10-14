# Phase 24: Spec-and-discuss chain skill - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-10-14
**Phase:** 24-spec-and-discuss-chain-skill
**Mode:** assumptions (`--analyze --all --batch`), jev screening, best over easy, CodeGraph
**Areas analyzed:** Invoking the GSD steps and portability; decide.py; SKILL.md, brief and quality rule; range, commits, ledger, amendments; edge floor, gates, registration

## Assumptions Presented

The analyzer was `gsd-assumptions-analyzer` (sonnet), with 77 tool calls. It ran `codegraph sync`
in the worktree, the edge engine over `24-SPEC.md` and timestamp checks in scratch; no remote
calls and no commits.

| Assumption | Confidence | Evidence |
|---|---|---|
| Never pass `--assumptions`; encode the intent | Confident | shim `SKILL.md:56-57`; `discuss-phase.md:26-32` |
| Workflow-file route | Likely | `agent-skills-bootstrap.md`; `plan-phase.md:236` |
| Discuss without `--auto` | Likely | `discuss-phase-assumptions.md:379-385,634-655` |
| SPEC in brief; in-place additive CONTEXT | Likely | no SPEC in the assumptions workflow; 17/18 markup |
| Host-conditional subagents | Likely | `init phase-op` keys; Codex orchestrator rule |
| Scrubbed child env | Confident | `jev_review.py:253-296`; prototype `:24,30` |
| CLI contract, per-item rejection | Likely | `jev_review.py:127-231`; 18.1 batch failure |
| Dedicated Laya URL variable | Unclear | 18 D-36; SPEC R5 unnamed |
| Key by name, standalone parser | Likely | `local_secrets.py:7-24` |
| Persistent per-user consent | Unclear | SPEC R2/R6 vs jev `SKILL.md:44-47` |
| Payload schema guard | Likely | real items ≤ 649 characters |
| Static client roots from `abspath(__file__)` | Likely | symlink experiment |
| Two-layer tests | Likely | AGENTS.md fail-closed note |
| Split-by-topic layout | Likely | skill-judge D5 |
| Analyzer returns questions | Likely | consent and log ownership |
| `phase.mvp-mode` resolver | Likely | `phase.cjs` cmdPhaseMvpMode; live output |
| CodeGraph marked block | Likely | 16.1 D-20 |
| Git commit time for the range | Likely | measured on Phases 16.1, 18, 19, 20 |
| Commit order | Confident | `41d3851`, `0716eee` |
| Temp ledger plus log marks | Likely | `deferred-ledger.md` |
| Cross-phase amendment step | Confident | 17/18 logs |
| `edge_floor.py` floor + check | Likely | engine run: 40 edges, 1 unclassified |
| Gates depend on 16.1 | Likely | per-skill allowlists today |
| README-only registration | Confident | `setup.py:582-610` |

## jev screening

One Laya call per item; `needs_fallback` items batched to TypeSafe direct. Summaries only.

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| C01 invoke | config_flip 0.60 (fb) | workflow_file 0.88 | D-02 |
| C02 auto | auto_accept 0.63 (fb) | emulate 0.89 | D-03 |
| C03 CONTEXT merge | merge_in_place 0.53 (fb) | merge_in_place 0.96 | D-04 |
| C04 subagent | always_inline 0.43 (fb) | conditional 0.99 | D-05 |
| C05 bad item | per_item 0.71 | – | D-07 |
| C06 Laya URL | client_var_loopback 0.72 | dedicated_only 0.61 (fb, second opinion) | **Own reasoning:** dedicated variable plus loopback fallback (D-08, ledger) |
| C07 key lookup | env_file_secrets 0.38 (fb) | env_file_secrets 0.99 | D-09 |
| C08 consent | session_only 0.65 (fb) | user_level_persistent 0.60 (fb) | **Own reasoning:** persistent per-user record, announced and revocable; needs uz's confirmation (D-10, ledger) |
| C09 payload guard | prose_only 0.50 (fb) | schema_caps_scan 0.83 | D-11 |
| C10 client locate | env_only 0.46 (fb) | static_roots 1.00 | D-12 |
| C11 tests | both_layers 0.93 | – | D-13 |
| C12 packaging | single_file 0.45 (fb) | split_by_topic 0.94 | D-14 |
| C13 who calls jev | analyzer_calls 0.93 | return_questions 0.92 (second opinion) | **Laya overridden**: D-15 |
| C14 MVP source | engine_resolver 0.63 (fb) | engine_resolver 0.56 (fb) | **Own reasoning:** engine resolver (D-16, ledger) |
| C15 CodeGraph | marked_block 0.59 (fb) | marked_block 0.98 | D-17 |
| C16 range | git_commit_time 0.55 (fb) | git_commit_time 0.82 | D-18 |
| C17 ledger | committed_file 0.57 (fb) | tempfile_plus_log_marks 0.79 | D-20 |
| C18 edge floor | inline_node 0.44 (fb) | wrapper_check 0.93 | D-22 |
| C19 gates | assume_landed 0.65 (fb) | sequence_after 0.82 | D-23 |

## Live facts that changed the plan

- The literal `--assumptions` flag writes no files and the overlay flags do nothing in
  assumptions mode: ROADMAP goal and SC1 amended.
- `config-get workflow.mvp_mode` exits "Key not found" when unset, and ROADMAP per-phase mode
  exists: SPEC R9 amended.
- ROADMAP SC2 (health endpoint, key file) and SC5 (setup registry) were stale: amended.
- 16.1 has not landed, so R13's regex gate coverage is a dependency: ROADMAP "Depends on"
  amended.

## Corrections Made

No user corrections.
