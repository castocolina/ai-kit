---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 11
subsystem: superpowers adapter (executor switch wiring and docs)
tags: [superpowers, lanes, quota, executor-switch, docs]
requires: [41-10]
provides:
  - "lane_switch.fallback_outcome(config, key, quota_proven, exclude, route_fn) over flagged_lane and next_lane (role execute); lane_switch.lazy_routes(config, deps, routes_fn=None)"
  - "adapter subcommand executor-fallback --cwd --key --dispatch-result --exclude-keys-file --injection-file (exit 0 switched, 1 not switched with a reason, 2 unreadable input file)"
  - "Classify step **Flagged switch** in references/dispatch-external-cli.md (temporary SWITCH_INJECTION_JSON/SWITCH_EXCLUDE_JSON/SWITCH_BACKUP_JSON files, SWITCH_JSON answer, scalar SWITCHED)"
  - "the one exception named in the NEVER bullet, the same-round ban, ## Owner stop, the quota wake, escalation.md, cross-ai sections 6 and 8, and spec-config's usage_limited docs"
affects: [41-12, 41-13, 41-14]
key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
    - tests/test_adapter_executor_switch.py
    - skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md
    - skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md
    - skills/ai-kit-spec-execute-superpowers/references/quota-wake.md
    - skills/ai-kit-spec-execute-superpowers/references/escalation.md
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - tests/test_ai_kit_spec_superpowers.py
    - skills/ai-kit-cross-ai/SKILL.md
    - tests/test_lane_failure_text.py
    - skills/ai-kit-spec-config/references/free-lanes.md
    - skills/ai-kit-spec-config/references/config-file.md
    - tests/test_spec_config_flow_text.py
decisions:
  - "Owner rule (2026-11-25): the executor switch acts only on the runner's own quota evidence (quota_evidence), never replaces an unflagged lane, and reports a flagged lane with no eligible fallback instead of replacing it."
metrics:
  tasks: 3
  commits: 3
---

# Phase 41 Plan 11: executor switch wiring and docs Summary

`executor-fallback` moves an execute lane the owner flagged `usage_limited` to its configured fallback of another pool, but
only when the saved runner result proves quota (`quota_evidence`), only to the first eligible lane of the owner's execute
order that the task's ranked candidates hold and its exclusions do not, and it routes only after the three refusals (not
quota, unknown lane, unflagged). A transient or capacity 69/75 never switches; a flagged lane with no eligible fallback is
reported (`no fallback`), never replaced. The Classify **Flagged switch** step replaces `INJECTION_JSON.json` only after the
re-resolve validates (mode and key) and the move and scalar write succeed, and every rule that forbade the move names the
one exception; cross-ai and spec-config's flag docs name both readers of the flag.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 90b1caf | feat(41-11): move a flagged execute lane to its fallback after a proven quota stop |
| 2 | c70872f | docs(41-11): run the flagged-lane switch before any quota wait or owner stop |
| 3 | 85e5b0f | docs(41-11): name the superpowers adapter as a reader of the owner's usage_limited flag |

Cross-AI lanes (pi, router-env/my-coding), one per task from per-task prompts with checked anchors
(`tmp/run-2026-11-23/anchors-41-11.md`; Task 1's code anchors re-checked after 41-10), each AIKIT-XAI `status=ok attempts=1`:
Task 1 306 s (hook 165/165 + uv 22/22, curated matrix deferred to push), Task 2 170 s (hook 26/26), Task 3 59 s (hook 24/24).

## Verification (chunk executor, own runs)

- Task 1 (at 90b1caf): `def fallback_outcome(` 1; `def lazy_routes(config: dict, deps, routes_fn=None):` 1;
  `"executor-fallback"` 2 and `--dispatch-result` 4 in cli.py; no `lane_usage_limit`/`lane_free_pool` in the adapter cli;
  22 tests in the executor-switch module. Base for the scope check: 381625b (`tmp/run-2026-11-23/p41-11/base.txt`).
- Task 2: `**Flagged switch.**` 1, `executor-fallback --cwd` 1, `SWITCH_INJECTION_JSON.json` 6; `|| true` 0 before and after;
  no `executor-fallback` in resolution-stops.md, quota-wake.md or SKILL.md; the NEVER text with the exception 1; the quota-wake
  exception 1; the escalation pointer 1; the pinned texts kept (never switch, stop sentence, bare 75, fourteen placeholders,
  `For this re-dispatch only`); no `SWITCH_RE` match in added lines.
- Task 3: both cross-ai sentences 1 each; `no run reads` gone from free-lanes.md and config-file.md; the readers line 1;
  `Never switch harness, provider or model` kept.
- Scope 381625b..85e5b0f = the fourteen files_modified; no phase, plan, decision or requirement id in added lines;
  tests/test_lane_switch.py and tests/test_lane_ping.py unchanged; baseline unchanged; EXEC_PREAMBLE untouched.
- Modules: adapter_executor_switch 22, lane_switch 30, lane_ping 34, lane_settings 58, ai_kit_spec_superpowers 180,
  adapter_single_definitions 9, adapter_escalation_flags 28, skill_text_history 45, quota_policy_text 20,
  cross_ai_skill_text 40, lane_failure_text 32, spec_config_flow_text 41, spec_config_lane_json 6, arch 118,
  arch_hardcoded_models 23: all ok.
- Gates after the plan: unit + arch groups under the watchdog `206/206 modules passed` (peak 8, not killed); `make ruff`,
  `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each (`check-dogfood: ok`; judge stale-digest
  and facts-drift notes only).
- Deferred e2e: `tests.test_ai_kit_gsd_curated_config_matrix` under the watchdog, 35 tests ok in 151.3 s, `1/1 modules passed`
  (guard exit 0, not killed).
- SKILL.md body words: ai-kit-spec-execute-superpowers 3763 -> 3789 (290 -> 290 lines); ai-kit-cross-ai 6354 -> 6372
  (403 -> 404 lines); ai-kit-spec-config unchanged (6476).

## Deviations

- Task 1: the handler is split into `_read_json_file`, `_load_fallback_inputs`, `_execute_roster` and `_add_fallback_parser`
  (pylint locals, statements and line length); behaviour as planned.
- Task 2: the test shim string in `_switch_run` uses f-strings (ruff UP031).
- Task 3: the section 6 paragraph is reflowed over four lines; its last line is longer than the neighbouring prose lines
  (open for code review: re-wrap).
- Both changed SKILL.md files need the skill-judge loop at the phase's judge step.
