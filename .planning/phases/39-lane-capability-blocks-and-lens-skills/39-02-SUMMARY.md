# 39-02 Summary: the runner's capabilities line and the row capability forms

Status: complete. Commits 2694695 (`feat(39-02): lane capabilities from the final argv, pi and copilot forms`), 6014a34
(`feat(39-02): capability facts for every row and the recorded capability fixture`) and 731d97c
(`test(39-02): capability line fixture comparison through the real runner`). Executed through three cross-AI lanes
(pi router-env/my-coding), one per task, each status=ok on its first run (324 s, 357 s, 170 s).

## What changed

- Runner template (still template 11): `forms.capabilities` on all six rows (pi and copilot tool lists with help-quoted labels,
  cursor `--mode ask|plan` and `--force` facts, codex sandbox and bypass facts with `CODEX_SANDBOX_LABEL`/`CODEX_BYPASS_LABEL`, claude
  tool lists, opencode no facts); the pure `laneCapabilities(row, role, argv, report)` with `capLabel`, `flagUses`, `factAt`,
  `toolListCaps`, `CAP_UNKNOWN` (exported: `laneCapabilities` only); `--print-argv` logs one stderr line
  `cross-ai: capabilities <JSON>` right after the skill-block lines. Labels are `{state, source}` objects; `prompt` is
  `{channel, max_bytes}` (copilot `argv`, 102119; every other row `stdin`, null).
- Harness: `CAPABILITIES_FIXTURE` and four `logic` cases `cap-pi-review-line`, `cap-print-argv-table`, `cap-planted-tools-flip`,
  `cap-pure-tool-lists`.
- `tests/fixtures/runner_capabilities.json` (18 lanes), the regenerated describe golden (six `capabilities` forms, nothing else),
  `TestCapabilitiesLine` in `tests/test_runner_skills_argv.py` (fixture table, line order, stdout three fields).

## Verification (run by the chunk agent)

- The six named cases (4 `cap-*`, `mcp-review-lanes-applied`, `lock-late-usage-no-lock`): `self-test ok`. `--self-test-list` 908 -> 912
  cases (logic 804 -> 808), the four new cases listed as `logic`.
- `--print-argv` of 14 calls (all six runtimes in both modes, codex workspace-write, pi idle timeout) against 7ffe392: stdout byte-equal,
  stderr equal once the capabilities line is removed; every call prints exactly one capabilities line (the SPEC R3 locked delta).
- Modules (two per call, scratch HOME): runner_skills_argv 14, runner_describe 20, runner_mcp_argv 9, runner_settings_argv 21,
  runner_preview 9, runner_claude_exec 6, effort_probe 23, jev_fast_decision 243, cli_help_flags 15, cross_ai_render_sync 11,
  arch_hardcoded_models 23, gate_scope 62: all pass. Acceptance greps 1/1/6/18/4/1/6. Lanes: lint.sh (ruff, pyright, vulture, pylint)
  exit 0; hooks 201/201, 201/201, 3/3.
- detection.py, the model baseline and the live copy `.planning/scripts/cross-ai.mjs` unchanged; template line stays `template=11`.

## Deviations

- None in behaviour. The fixture lanes are written as compact one-line JSON objects (the plan asked one line per lane; spacing free).
