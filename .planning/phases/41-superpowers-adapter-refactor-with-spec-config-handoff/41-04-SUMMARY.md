---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 04
subsystem: ai-kit-spec-execute-superpowers (resolve-injection session-model fallback, jev pick)
tags: [superpowers, session-fallback, jev, owner-stop]
requires: [41-03]
provides:
  - "session_pick.py: SESSION_PICKS, PICK_QUESTION, pick_session_model(summary, env, run) -> (model, note); notes `host takes no model`, `jev absent`, `jev low: session model kept`, `jev <pick> (<top>)`; jev only on a Claude Code host, one hand-built choice item whose context is the summary only"
  - "dispatch_injection.session_fallback_injection(config, ladder_keys, summary, env, run) -> dict | None: native injection with key \"\", runtime \"\", model (pick or \"\"), fallback \"session\", fallback_note; None when the flag is off"
  - "cli resolve-injection --fix-round (default 0) and --no-fallback; _emit_or_fallback at the three no-lane emit points (no candidates, quota exhausted, narrowing to no_candidate); round >= 4, escalation keys or --no-fallback print today's output with no config read and no jev call; flag off: today's output plus stderr `run ai-kit-spec-config to add one or to turn on the session-model fallback`; non-boolean flag exit 2; jev run bound to --cwd"
  - "resolution-stops.md `Session-model fallback first.`; SKILL.md Step 2 --fix-round and Step 3 session-fallback exception inside the native branch; escalation.md rounds 4-5 sentence and --no-fallback in the re-run block; state-management.md pinned-fallback and owner-named sentences; config-check.md names both ways onto the session model"
affects: [41-06, 41-09, 41-10, 41-12]
key-files:
  created:
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/session_pick.py
    - tests/test_adapter_session_fallback.py
  modified:
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md
    - skills/ai-kit-spec-execute-superpowers/references/escalation.md
    - skills/ai-kit-spec-execute-superpowers/references/config-check.md
    - skills/ai-kit-spec-execute-superpowers/references/state-management.md
    - tests/test_lane_settings.py
    - tests/test_spec_chain_text.py
    - tests/test_arch.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "tests/test_arch.py (outside the plan's file list): session_pick.py -> ai-kit-spec-review added to CROSS_SKILL_ALLOWLIST and _CROSS_SKILL_FROZEN beside the existing dispatch_injection.py row; the plan's new module imports ai_kit_spec and test_arch failed without the row"
  - "SKILL.md Step 3 says `(the advisory pick)` and `no new pick` where the plan said `(a jev pick)` and `no jev`: tests/test_ai_kit_caller_text.py rejects a caller SKILL.md that names jev without a needs_fallback or no-answer rule"
  - "The except blocks pass `emit` as functools.partial instead of a lambda (exc is unbound after the except block; ruff F821)"
  - "Follow-up 1a519d6: the _emit_or_fallback docstring said round >= 4 / escalation keys / --no-fallback 'is a plain resolution', the opposite of the code; it now says only a plain resolution may fall back"
metrics:
  tasks: 3
  commits: 4
---

# Phase 41 Plan 04: the adapter's session-model fallback and jev's haiku/sonnet pick Summary

When the owner turned on `session_fallback` and no execute lane is available on a plain Step 2 resolution, `resolve-injection`
now prints a native injection marked `"fallback": "session"` and stderr says the task runs on the session model. On a Claude Code
host jev may pick haiku or sonnet; only a confident listed answer sets the model, anything else (absent, low, needs_fallback, an
outside choice, a failed run) keeps the session model. jev sees only `Task type: <type>. Files named: <n>. Fix round: <r>.` and
runs in the `--cwd` folder. An available lane never reaches the fallback; a fix round of 4 or more, escalation keys or
`--no-fallback` (passed by escalation.md's re-run block, which also serves the keep-the-lane and owner-named paths) give today's
output and ask jev nothing. With the flag off, today's output gains one stderr line naming ai-kit-spec-config as the fix. The skill
text routes a fallback injection through the one native branch as an exception (no ladder escalation or model bump at rounds 4-5),
keeps a pinned fallback on resume, and refuses it for an owner-named pair.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 7b8869a | feat(41-04): add jev's advisory session-model pick |
| 2 | 663aac8 | feat(41-04): run the task on the session model when the owner's fallback is on |
| 3 | 7c04b39 | docs(41-04): describe the session-model fallback in the owner stop and Step 3 |
| follow-up | 1a519d6 | fix(41-04): say which resolve-injection calls may fall back to the session model |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 305 s
(its hook ran the full unit and arch groups, 208/208, because Makefile and .pre-commit-config.yaml were staged), Task 2 178 s,
Task 3 147 s, follow-up 75 s.

## Verification (chunk executor, own runs)

- Acceptance: Task 1 `SESSION_PICKS` 1, `def pick_session_model` 1, no `SKILLS_ROOTS|JEV_ENTRY_REL` (rg exit 1), plan base 7cf02fc
  recorded as a full sha, Makefile names the new module; Task 2 `def session_fallback_injection` 1, `_emit_or_fallback(` 4,
  spec-config line 1, `"--no-fallback"` 1, `functools.partial(deps.run_fn, cwd=args.cwd)` 1, the four named tests 4; the
  `ALLOWED_READERS` row holds both readers but is wrapped over two lines, so the plan's one-line grep prints 0; Task 3 all 1,
  `is its only way` 0, config-check.md names no config key, SKILL.md 281 lines; all subjects as planned. Scope check from the plan
  base: `files_modified` paths plus tests/test_arch.py (see decisions). Model-literal baseline unchanged; only `except
  LaneSettingError` added.
- Modules, two per call: test_adapter_session_fallback (27), test_ai_kit_spec_superpowers (175), test_lane_settings (58),
  test_adapter_escalation_flags (28), test_adapter_single_definitions (9), test_gate_scope (62), test_arch (118),
  test_arch_hardcoded_models (23), test_skill_text_history (45), test_spec_chain_text (40), test_ai_kit_caller_text (11),
  test_quota_policy_text (20): each pair `2/2 modules passed`. The staged mapper over every changed path selects (through the shared `.pre-commit-config.yaml`) three
  e2e modules, all inside the commit budget; run under the watchdog anyway: test_ai_kit_spec_goal_prompt_e2e (5),
  test_flow_index_e2e (4), test_staged_commit_e2e (13), each `1/1 modules passed` (peak 2, not killed). The resolve-injection
  tests are not vacuous: the refusal tests run with the flag on and the Claude signal set and assert no jev call and stdout equal to
  the flag-off output; the brief-marker test asserts exactly one recorded jev call first.
- Gates after the plan: unit + arch groups under the watchdog `203/203 modules passed` (peak 9, not killed); `make ruff`,
  `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each (at 1a519d6).
- ai-kit-spec-execute-superpowers SKILL.md body 3282 -> 3426 words (279 -> 281 lines).

## Deviations

- See decisions: the test_arch allowlist row, the two jev wordings in SKILL.md, functools.partial, the docstring follow-up.
