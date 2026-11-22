---
created: 2026-11-21T00:00:00.000Z
title: Review notes left open by phase 37
area: tooling
severity: minor
files:
  - .planning/phases/37-shared-runner-options-and-session-ids/37-REVIEW.md
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - skills/ai-kit-spec-review/ai_kit_spec/runner_facts.py
  - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py
  - skills/ai-kit-cross-ai/SKILL.md
  - AGENTS.md
---

## Problem

The phase 37 code review left these low-severity items open. None loses data, prints a secret or leaves a process
running; each one is a stall, a misleading message or a narrow window.

## Goal

Close each item below when the named module is next changed, with a test for each behaviour change.

## Notes

- Hosted lane abandon window: once the launch line is typed, an abandon path (a signal right after `pane run`, the pid
  grace running out) drops the env and prompt files and closes the tab, but a launcher that already passed `setsid` runs
  on unsupervised. Poll the pid file for a short bounded time and end a verified group before the close, or have the
  launcher exit on a cancel marker the runner writes first.
- A failed `--describe` fact is never current, so every snapshot load spawns `node --describe` again and may wait up to
  30 s. Treat a failed fact with the same template hash as current for a back-off window and record when it failed.
- `print_argv_lines` returns None for a missing node, a missing template and a runner usage refusal alike, so
  `build-model-id` and the effort probe report "node or the runner template is missing" for a runner refusal. Return the
  exit code with the lines and print the runner's own refusal line.
- `session=` on a call that stops before the lane starts can show an explicit id the planner reported ignored
  (`mode_forbids`). Set the shown id from the session entry: the id when applied (or on a chosen row), else none.
- ai-kit-cross-ai SKILL.md: the `bad_value` row names only a context label; an effort that fails the level shape is
  `bad_value` too. A SKILL.md text change goes with a `fixes.md` beside the judge round.
- The prose skill block writes the resolved path into `path="..."` unescaped and a `SKILL.md` body holding `</skill>`
  closes the block early. Escape the attribute and refuse (or delimit by sha256) such a body.
- curated-config `apply-execution`: `reject_execute_cli` passes no runner fact, so it never refuses (37 R9 lets only a
  recorded fact refuse); pass `runner_facts.stored_fact` like `dispatch-execute` does, and give the refusal its test back.
- The claude execute formula and its resume carry no live probe record (`CLAUDE_EXEC_FORMULA_RECORD` is null, the runner
  prints an unverified note). Record it from a live probe once the owner consents to a real-HOME spike.
- AGENTS.md push timing says no e2e module is over the commit budget; the refreshed table records
  `tests.test_ai_kit_gsd_curated_config_matrix` at 252 s, so it is deferred to push. Re-measure the push worst case and
  update that paragraph.
