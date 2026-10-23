# Phase 25: Quota-aware cross-AI subprocess supervision - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-10-14
**Phase:** 25-quota-aware-cross-ai-subprocess-supervision
**Mode:** assumptions (`--analyze --all --batch`), decision ladder, best over easy, CodeGraph
**Areas analyzed:** Pattern table and classifier; route-aware classes; live and post-hoc detection and reset time; wait, state and resume; skills, contracts and Phase 26 coupling

## Assumptions Presented

The analyzer was `gsd-assumptions-analyzer` (sonnet), with 54 tool calls. It ran `codegraph sync`
in the worktree, grepped local session logs (codex rollouts, opencode logs, claude transcripts)
for real limit messages, and read the installed CLIs' `--help` and pi's bundled retry classifier.
It made no model calls.

| Assumption | Confidence | Evidence |
|---|---|---|
| Matcher only in the runner | Likely | 18.1 R7/D-13; `quota.py:16-24`; `dispatch_injection.py:24-45` |
| Table as a marked block in the template | Likely | 18 D-26 hash header; `.planning/config.json` runner command |
| Specific phrases before generic codes | Likely | router `[401]` MonthlyLimitError ×12; cursor `ActionRequiredError` instances |
| Stdout events and stderr, no rollout files | Likely | opencode stdout error events; `codex_error_info` only in rollouts |
| Route from the confirmed catalog field | Likely | `model_catalog.py:231-260`; `model_heuristics.py:26-30` |
| Direct = closed prefix list | Unclear | Zen/Go/pi live failures |
| Direct-route cap wording reports | Unclear | cursor monthly cap; Zen/Go free-tier errors |
| Router-tail errors wait | Likely | 16-HANDOFF.md:124-127; uz's clarification |
| Kill only on terminal signals | Likely | opencode `AI_RetryError`; pi RETRYABLE set |
| Cursor keeps verified json mode | Likely | `agent --help`; `cross-ai.mjs:107` |
| Reset parsing, local time, IANA zone | Confident | six codex rollouts; claude `resets … (America/Santiago)` |
| Runner owns state | Likely | GSD path has no Python; 18 D-27 tree id |
| State in the cache dir | Likely | `ai-kit-spec-execute-gsd/SKILL.md:82-83`; temp-index snapshot |
| Task key per worktree plus objective | Unclear | `elaboration.md:84-87` |
| Probe, then resume | Likely | codex limit hits return in 1.5–4.3 s |
| One-shot chained wakes | Likely | todo research on CronCreate/ScheduleWakeup |
| `action=` scoped to the call | Likely | 18.1 D-11; dogfood `prefer` list |
| Native is not a candidate | Unclear | `elaboration.md:119`; `quota.py:13-14` |
| First snapshot only | Likely | `cross-ai.mjs:109,129,174,189` |
| Plan against contracts | Confident | STATE `completed_phases: 0`; ROADMAP 16.1/18/18.1 unchecked |
| New `billing_or_access` reason | Likely | 18.1 D-12; superpowers reason list |
| Review lane pending | Unclear | no hourly wake in `ai-kit-spec-review` |
| One policy reference | Likely | ROADMAP Phase 26 dependency |

## jev screening

One Laya call per item; `needs_fallback` items batched to TypeSafe direct; high-confidence Laya
answers that contradicted the evidence got a TypeSafe `--second-opinion`. Summaries only.

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| A1 classifier home | python_stamps 0.51 (fb) | runner_only 0.56 (fb) | **Own reasoning:** runner only, one matcher (D-01, ledger) |
| A2 table place | in_config 0.75 | marked_block 0.93 (second opinion) | **Laya overridden**: D-02 |
| A3 match order | auth_first 0.80 | specific_first 0.92 (second opinion) | **Laya overridden**: D-03 |
| A4 codex rollout | read_private_log 0.52 (fb) | read_private_log 0.68 (fb) | **Own reasoning:** stdout and stderr only (D-04, ledger) |
| A5 route source | confirmed_field 0.72 | – | D-05 |
| A6 direct list | non_router_is_direct 0.68 (fb) | prefix_list 0.78 | D-06 |
| A7 direct limit | cap_patterns_report 0.41 (fb) | cap_patterns_report 0.78 | D-07 |
| A8 router tail | all_but_bad_model 0.81 | tail_waits 0.87 (second opinion) | **Laya refined**: D-08 |
| A9 live kill | first_line 0.66 (fb) | terminal_only 0.99 | D-09 |
| A10 cursor stream | switch_stream 0.41 (fb) | keep_verified 0.98 | D-10 |
| A11 state owner | both 0.85 | runner_owned 0.72 (second opinion) | **Laya overridden**: D-12 |
| A12 state location | git_dir 0.74 | user_cache 0.95 (second opinion) | **Laya overridden**: D-13 |
| A13 task key | caller_id_else_worktree 0.59 (fb) | worktree_plus_objective 0.76 | D-14 |
| A14 probe | full_retry 0.88 | probe_then_resume 0.94 (second opinion) | **Laya overridden**: D-15 |
| A15 wake shape | oneshot_chain 0.46 (fb) | oneshot_chain 0.89 | D-16 |
| A16 action scope | verdict_per_call 0.39 (fb) | verdict_per_call 0.95 | D-17 |
| A17 native candidate | native_last 0.79 | native_not_candidate 0.58 (second opinion, fb) | **Own reasoning:** not a candidate (D-18, ledger) |
| A18 snapshot base | first_snapshot 0.56 (fb) | latest_snapshot 0.49 (fb) | **Own reasoning:** first snapshot (D-19, ledger) |
| A19 billing reason | configuration 0.39 (fb) | new_billing_access 0.99 | D-21 |
| A20 review lane | lane_pending 0.51 (fb) | lane_pending 0.94 | D-22 |
| A21 policy doc | one_reference 0.43 (fb) | one_reference 0.96 | D-23 |

## Live facts that changed the plan

- opencode's live text is `The usage limit has been reached` (APIError, 429) in stdout error
  events. codex's `codex_error_info` was seen only in rollout files.
- router-env's monthly limit arrives as `[401]` with `MonthlyLimitError`, so any auth-first
  table misclassifies it.
- Every live cursor `ActionRequiredError` was a usage limit or a plan gate, never a login
  problem.
- codex reset times are local time, 0.6–3.2 h ahead; claude prints an IANA zone.
- `ai-kit-spec-review` has no hourly wake today.

## Corrections Made

- 25-SPEC R1, R2, R8, Background and one R2 Edge Coverage row amended (D-01..D-08, D-22).
- 18.1-CONTEXT D-12 amended: `billing` → `billing_or_access`, not `auth` (D-21).
- 16.1-CONTEXT D-13 amended: the subprocess matcher lives in the runner (D-01).

## External Research

Open questions routed to the phase researcher are listed in CONTEXT `<deferred>`.
