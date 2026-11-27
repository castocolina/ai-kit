---
phase: 42-code-review-after-execution-and-jev-picked-executors
plan: 02
subsystem: ai-kit-spec-execute-superpowers (executor resolution)
tags: [jev, executor-pick, resolve-injection, native-effort]
requires: [42-01]
provides:
  - "ai_kit_spec/executor_pick.py: Pick, PICK_QUESTION, TASK_LABELS, catalog_class, candidate_labels, candidate_items, pick_executor, dispatch_record, pick_line"
  - "BuildInjectionOptions.pick_fn; the walk puts a confident pick first in `remaining` only (`ladder_keys` unchanged); after the walk one stderr line `ai-kit-spec: executor pick: <dispatched key> (jev, <c>)` or `(default: <note>)` and the injection field `pick`"
  - "CliDeps.pick_executor_fn, _catalog_entries, _pick_fn_for: the pick is built only on a plain first resolution (fix round 0, no escalation keys)"
  - "native injection carries `effort` (empty string when none); the adapter SKILL.md passes `model` and `effort` to the Claude Code `Agent` tool"
affects: [42-10]
key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/executor_pick.py
    - tests/test_executor_pick.py
  modified:
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - tests/test_ai_kit_spec_superpowers.py
    - tests/test_adapter_session_fallback.py
    - tests/test_adapter_executor_switch.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "The walk signature is kept on one line as the acceptance criterion pins it (124 characters), with `# noqa: E501` and `# pylint: disable-next=line-too-long` (existing repo pattern)"
  - "No file in this repo confirms that the `Agent` tool accepts `effort`; the SKILL.md sentence follows the owner's confirmed scope reading 6 (SPEC amendment 12)"
metrics:
  tasks: 2
  commits: 2
---

# Phase 42 Plan 02: jev picks the executor Summary

A plain `resolve-injection` asks jev once, from labels only (opaque tokens `c1..cN`, route kind, effort, catalog
class, task affinity, task type), which of the candidates the ladder walk can dispatch should implement the task.
A confident pick goes first in the walk's `remaining`; `ladder_keys` keeps today's order. No jev, a low or
`needs_fallback` answer, an error, an undecodable reply, one candidate, an over-long label context or a pick
outside the roster keeps today's order. After the walk, stderr names the dispatched key and the side that decided it,
and the injection gains the matching `pick` field; a quota-blocked pick logs `(default: jev pick unavailable)`, and full
exhaustion prints no pick line. Fix rounds and escalation resolutions build no pick. The native injection carries the
candidate's effort and SKILL.md tells Claude Code to pass it.

## Commits

- `973c4e1` feat(42-02): jev picks the executor among the filtered roster candidates (Task 1)
- `660d121` feat(42-02): native effort in the injection; every executor pick branch pinned (Task 2)

## Lane history

- Task 1: per-task fix-up lane `42-02-fix-a` (pi router-env/my-coding), status ok, 1302 s, one commit; hook 230/230
  modules plus 23/23 under uv; the hook deferred `tests.test_ai_kit_gsd_curated_config_matrix` to push.
- Task 2: per-task fix-up lane `42-02-fix-b`, status ok, 580 s, one commit; hook 28/28 modules.

## Checks (orchestrator chunk, own runs)

- Acceptance greps of both tasks: every EXPECT value met; SKILL.md 293 lines; `tests/fixtures/no_hardcoded_models_baseline.json` unchanged.
- 13 + 1 + 1 existing resolve-injection calls pass `pick_executor_fn=_no_pick`; the two callers outside the plan's files
  (`test_adapter_escalation_flags` resolver, `test_ai_kit_spec_trust` malformed-local) never build a pick: a probe with
  `jev_names.find_jev` made fatal ran both modules' tests, 39 ok.
- Makefile and `.pre-commit-config.yaml` add only `tests.test_executor_pick`; added shipped lines carry no phase, decision or requirement id and no date.
- Deferred e2e `tests.test_ai_kit_gsd_curated_config_matrix` run under the guard: 35 tests ok (151.6 s).
- Unit and arch groups under the guard: 207/207 modules passed (peak 7 runner processes); `tests.test_executor_pick` 27 tests.
- `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood`: exit 0 each.
- SKILL.md body words 3838 before, 3842 after.

## Deviations

- Walk signature on one line with lint pragmas (acceptance pins the one-line form).
- The first Task 1 test gained two assertions that use `executor_pick` (instructions equal `PICK_QUESTION`, criteria are
  opaque tokens) so the planned import is used (vulture).
- Allowed adaptation: `test_resolve_injection_prints_native_json` gained the `pick` field (Task 1) and `"effort": ""`
  (Task 2, a third whole-dict native assertion the plan did not list; same kind of change as the two listed).
- `TestWalkOrder`'s `jev(key)` records offered keys flat (`extend`) so the plan's own `["a/one", "c/three"]` assertion holds;
  a nested `with` was merged for ruff SIM117.
