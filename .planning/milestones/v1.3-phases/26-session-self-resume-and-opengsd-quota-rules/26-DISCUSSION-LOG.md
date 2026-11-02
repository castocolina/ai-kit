# Phase 26: Session self-resume and OpenGSD quota rules - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-10-14
**Phase:** 26-session-self-resume-and-opengsd-quota-rules
**Mode:** assumptions (`--analyze --all --batch`), decision ladder, best over easy, CodeGraph
**Areas analyzed:** Wake home and CLI; wake state; liveness and resume directory; OS timer; firing, lock and resume command; `opengsd` condition; rule IDs and signals; executor wiring; tests

## Assumptions Presented

The analyzer was `gsd-assumptions-analyzer` (sonnet), with 63 tool calls.
- It ran `codegraph sync` and read the `--help` output of claude, codex, pi, opencode,
  systemctl and systemd-run.
- It read `man systemd.timer` and `systemd.service`, the user's systemd user units (read-only),
  `/proc` for the host process, and `runtime-identity --raw`.
- It created no timer and made no model calls.

| Assumption | Confidence | Evidence |
|---|---|---|
| New dedicated skill | Likely | four callers; sibling `sys.path` import precedent |
| `done` subcommand | Likely | SPEC R5 edge on disarm waiting for the lock |
| Hosts keyed by runtime labels | Confident | `detection.py:20` lacks pi; `config_io.py:100` |
| XDG state dir | Likely | Phase 25 waits in the cache dir |
| mkstemp writes | Confident | `cache.py:25`; `stack_cache.py:96-118` |
| Created-paths list | Likely | R5/R6 remove-exactly requirement |
| `/proc` + boot id | Likely | `CLAUDE_PID` live; ticks since boot |
| Launch directory | Likely (spike) | `/proc/$CLAUDE_PID/cwd` ≠ shell cwd; transcript path |
| OnCalendar + Persistent | Confident | `man systemd.timer` (systemd 259) |
| Enable + stamp cleanup | Likely | live stamp files; `clean --what=state` |
| Cron fallback | Unclear | SPEC write constraint; no crontab here |
| Count every wake | Likely | SPEC R5 MUST NOT |
| Resume argv table | Unclear (spike) | `--help` of all four; `--bg --resume` |
| Permission mode | Unclear | session launch flags read from `/proc` cmdline |
| In-session companion | Unclear (spike) | R4 owner unspecified |
| Separate identity probe | Likely | `test_ai_kit_rules_common.py:148-154` hermeticity |
| Upstream-order resolver | Likely | `discuss-phase.md:118`; `gsd_catalog.py` drift |
| Notices pass-through | Unclear | `remediation.py`; `aggregate.py:51` |
| R18 flat, R19 groups | Likely | R04 precedent |
| Threshold per framework | Unclear | superpowers always runs one plan |
| Refuse in child | Unclear (spike) | `CLAUDE_CODE_CHILD_SESSION` in subagent |
| AST isolation rule | Likely | `test_arch.py` non-vacuity convention |

## jev screening

One Laya call per item; `needs_fallback` items batched to TypeSafe direct; high-confidence Laya
answers that contradicted the evidence got a TypeSafe `--second-opinion`. Summaries only.

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| B1 home | shared_lib 0.52 (fb) | module_in_existing 0.55 (fb) | **Own reasoning:** new skill (D-01, ledger) |
| B2 done | no_wait_flag 0.43 (fb) | done_command 0.94 | D-02 |
| B3 state dir | same_cache 0.38 (fb) | xdg_state 0.78 | D-05 |
| B4 created list | derive 0.89 | record_list 0.98 (second opinion) | **Laya overridden**: D-07 |
| B5 liveness | proc_bootid 0.52 (fb) | proc_bootid 0.98 | D-08 |
| B6 pid source | env_then_walk 0.58 (fb) | env_then_walk 0.95 | D-08 |
| B7 cron | amend_marked_line 0.48 (fb) | drop_cron 0.88 | D-14 |
| B8 count | count_all 0.53 (fb) | count_resumes 0.79 | **Own reasoning:** count all, per the locked MUST NOT (D-11, ledger) |
| B9 resume mode | background_only 0.64 (fb) | spike_decides_headless_default 0.90 | D-15 |
| B10 companion | arm_reports_companion 0.40 (fb) | document_gap 0.92 | **Own reasoning:** arm reports the companion (D-20, ledger) |
| B11 probe place | extend_shared 0.70 (fb) | separate_probe 0.95 | D-17 |
| B12 resolver | new_shared_upstream 0.69 (fb) | new_shared_upstream 1.00 | D-18 |
| B13 notices | check_only 0.95 | flag_through 0.68 (second opinion, fb) | **Own reasoning:** flag through both outputs (D-19, ledger) |
| B14 signals | flat 0.88 | groups 0.94 (second opinion) | **Laya overridden**: D-22 |
| B15 threshold | always 0.79 | per_framework_units 0.87 (second opinion) | **Laya overridden**: D-23 |
| B16 child refuse | instructions_only 0.84 | refuse_markers 0.97 (second opinion) | **Laya overridden**: D-24 |
| B17 isolation test | ast_rule 0.74 | – | D-25 |
| B18 enable | enable_full_cleanup 0.82 | – | D-13 |
| B19 permission | always_bypass 0.38 (fb) | explicit_at_arm 0.81 | D-21; the default value is deferred to uz |

## Live facts that changed the plan

- `Persistent=true` only works with `OnCalendar=` (systemd 259 man page).
- `KNOWN_CLIS` has no `pi`.
- The host's launch directory differs from the shell's (the worktree), and the transcript is
  keyed by the launch directory.
- pi `--session-id` and opencode `--session` create a missing session.
- Claude Code 2.1.299 has `--bg --resume <id>` and `agents`/`attach`.
- A subagent shares the main session's `CLAUDE_CODE_SESSION_ID` and sets
  `CLAUDE_CODE_CHILD_SESSION`.

## Corrections Made

- 26-SPEC R1, R3, R6, R7, R8 and two Edge Coverage rows amended. One R3 idempotency row was
  added; the floor was recomputed and the check passes.
- REQUIREMENTS QTA-04 and QTA-05, and ROADMAP Phase 26, amended (resume by id, two rules,
  no cloud routine for local sessions).

## External Research

Open questions and the spike list are in CONTEXT `<specifics>` and `<deferred>`.

# Update 2026-10-14 (uz answer)

- D-21 default: copy the original session's permission flags (refined in CONTEXT).

# Update 2026-10-24 (assumptions mode)

**Input:** `26-SPEC.md` with the 2026-10-24 R4/R7 amendments (committed in `f1cb7c4`), Phase 25.1's
SPEC and CONTEXT (`a73bcd3`, `52476a1`), and the 2026-10-14 CONTEXT (D-01..D-27 kept; refined
bullets only).

## Assumptions Presented

The analyzer was `gsd-assumptions-analyzer` (opus), 39 tool calls, in the background beside the
25.1 analyzer. It read `man systemd.timer` (systemd 259), ran `systemd-analyze calendar` on sample
reset times, checked `notify-send` 0.8.8 and the user manager's environment (names only), and read
strings from the installed Claude Code 2.1.310 binary (reverse-engineered). It armed no unit and
ran no AI CLI.

| Assumption | Confidence | Evidence |
|---|---|---|
| Reset wake as a second `OnCalendar=` on the persistent timer | Likely | `man systemd.timer`; transient units die at reboot (`man systemd.unit`) |
| Pre-reset fires not counted; 7-day bound | Likely | 25.1-EVIDENCE Claude `seven_day`; `tools/claude_segments.py:83-142` |
| `arm --reset-at/--reset-text` plus a Claude `StopFailure` hook row | Unclear | 2.1.310 binary strings; `tools/setup.py:1732-1800` |
| Journal plus best-effort `notify-send` from `fire` | Likely | live `notify-send`, linger on |
| Phase 26 notifies only its own give-up | Likely | 25.1-SPEC R3; D-25 |
| R19 signals from the pointer, with a sync test | Likely | 25-09-PLAN pointer draft; `rules.py` literal matching |
| `verbatim` flag through remediation and Step C | Likely | agents SKILL.md Step C; `remediation.py` |
| Executors call only the wake CLI | Likely | 25-09 text test |
| Resume prompt continues hard-tier waits | Likely | 25.1-SPEC R3 |
| 25 D-24 parser fixture superseded | Confident | 25.1-SPEC Boundaries; no parser in `cross-ai.mjs` |

## jev screening

One local call per item; `needs_fallback` items go to the first consented remote (TypeSafe).
Summaries only.

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| B1 reset timer | extra_calendar_entry 0.43 (fb) | extra_calendar_entry 0.86 | D-28 |
| B2 cap counting | count_all 0.57 (fb) | skip_before_reset_bounded 0.74 (fb) | **Own reasoning:** counting all disarms before a weekly reset; the 7-day bound keeps "never forever" (D-29, ledger) |
| B3 reset capture | agent_only 0.50 (fb) | option_plus_host_hook 0.98 | D-30 |
| B4 notice channel | host_push 0.47 (fb) | journal_plus_best_effort_desktop 0.98 | D-31 |
| B5 notice ownership | both 0.87 | own_giveup_only 0.99 (second opinion) | **Laya overridden**: D-32 |
| B6 R19 signals | from_pointer_with_sync_test 0.72 | – | D-33 |
| B7 verbatim flag | verbatim_flag 0.45 (fb) | verbatim_flag 0.99 | D-34 |
| B8 executor text | call_tool_only 0.79 | – | D-35 |
| B9 resume prompt | prompt_says_continue 0.48 (fb) | prompt_says_continue 0.91 | D-36 |

## Live facts that changed the plan

- systemd 259 accepts repeated `OnCalendar=` entries and catches up persistent timers; transient
  timers do not survive a reboot (D-28).
- Claude Code 2.1.310's binary names a `StopFailure` hook with a `rate_limit` matcher
  (reverse-engineered, unverified) (D-30).
- The draft instruction-file pointer (25-09) contains none of R19's "10-minute"/"4-hour"/"route-aware"
  signals (D-33).

## Corrections Made

- 26-SPEC R4's 2026-10-24 amendment narrowed: the hard-tier notice is the 25.1 caller's (D-32);
  ROADMAP Phase 26 SC 5 and QTA-04 amended to match; 25-CONTEXT D-24 marked superseded (D-37).
- 26-SPEC Edge Coverage: the floor was recomputed (46 rows); three R4 rows for the amendment and
  the six R9 rows missing since 2026-10-14 were added; the check passes.
