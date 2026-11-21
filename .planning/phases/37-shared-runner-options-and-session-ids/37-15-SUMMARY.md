# 37-15 Summary: lane MCP servers through the runner (`--mcp-config`)

Status: complete in two per-task lanes (pi `router-env/my-coding`), verified by the orchestrator.

## Lanes

- fix-a (Task 1): `status=ok exit=0 elapsed=491s attempts=1`, commit 851fbac (hook 129/129).
- fix-b (Tasks 2 and 3): `status=ok exit=0 elapsed=895s attempts=1`, commit 237f71b (hook 129/129; the lane also ran `make test` on its own: unit 177/177, unit-uv 3/3, integration 9/9, e2e 26/26, installer 48 passed, arch 2/2).
- No plan-as-written lane (runner-heavy): prompts were built from the plan's own task blocks plus orchestrator anchor notes checked against 36492cf.

## Commits

- 851fbac `feat(37-15): --mcp-config on claude reaches the argv as --mcp-config <abs> --strict-mcp-config`
- 237f71b `feat(37-15): MCP forms on every row, named usage errors and the spawn-level self-test`

## What was done

- Rows carry `forms.mcp`: claude `--mcp-config <abs> --strict-mcp-config` verified, copilot `--additional-mcp-config @<abs>` verified (after the review profile flags), codex unverified, pi, cursor and opencode `mcp: null`; the argv-file row gets a `no_slot` form.
- `MCP_SERVER_RE`, `loadMcpConfig` (read once through `readCallFile` with `mode: 0o077`, `strictJson`, constant content-free parse errors, index-only name errors), `JSON_KEY_ORDER` and `jsonKeys` (textual key order recorded by `strictJson`'s scan, `__proto__`-safe walk), pure `planMcp` (`mode_forbids` for pi's `--no-mcp` review profile, then `no_form`/`unverified_form`), the `mcp` handler in `SETTING_HANDLERS`, `callOf`'s trailing `mcp` passed at both call sites, `mcp = loadMcpConfig(o)` inside 37-13's loader try.
- Formulas: `...(c.adds?.mcp || [])` is the last spread of the claude and copilot exec and review formulas; no `reviewExtras` list changed; no approval flag added.
- Fakes: copilot `fake-readonly` leaves the tree untouched; both fakes record `mcpCount` from the file their argv names. Logic case `mcp-review-lanes-applied`.
- `tests/test_runner_mcp_argv.py` (37-02 stub, replaced): `TestMcpForms` (8), `TestMcpUsageErrors` (1).

## Evidence (orchestrator re-run, `tmp/run-2026-11-19/c6-verify-37-15.sh 36492cf`)

- Acceptance greps: the five names 5, `mode: 0o077` 3, strict/additional 5, `mcp: ` 10, pi `reviewExtras: ['--skill']` 1, no `reviewExtras` with mcp, case name 1, `mode !== 'readonly'` 1, `const mcpCount = ` 2; 9 tests, `TestMcpUsageErrors` 1, grok 0 (none added); only the plan's two files changed.
- `--print-argv` with a two-server file: claude review ends `--mcp-config <abs> --strict-mcp-config`, copilot review ends `--disable-builtin-mcps --additional-mcp-config @<abs>`, both with two `applied` lines in file order and `mcp:` entries in the status group; pi review `mode_forbids`, codex exec `unverified_form`, argv unchanged.
- Self-test list 606 (605 + `mcp-review-lanes-applied	logic`); 10 named cases (the new one, skill-prose-claude-stdin, copilot-exec-ok, copilot-argv-review, reader-strict-json, skill-prose-copilot-argv, settings-run-lines, ok, argv-file-exec-ok, argv-file-print-argv) print `self-test ok`.
- `--print-argv` output byte-equal to the 37-14 fold (36492cf) for 14 calls without `--mcp-config`.
- Modules 8/8 (mcp_argv, skills_argv, cli_help_flags, arch_hardcoded_models, arch, settings_argv, status_group, runner_flags) and 10/10 (the eight self-test shards, runner_e2e, exec_formula); verbose: all 9 MCP tests `ok`, none skipped. Baseline json and detection.py unchanged. Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0.

## Deviations

- `SETTING_NAMES` already listed `mcp`, `planSettings` already created `adds.mcp` and `statusGroup` already printed `mcp:<value>` (earlier plans), so Task 1 added only the handler; both `--print-argv` and the run path build the call with `callOf`, so `mcp` is passed at both call sites instead of a separate print-argv literal.
- No `.planning/scripts/cross-ai.mjs` change and no shard-time refresh (both 37-23's).
