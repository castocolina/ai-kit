# 39-04 Summary: the per-host skill and MCP-name scan and the `skill-table` command

Status: complete. Commits 092d163 (`feat(39-04): scan host skill roots with roles and print them with skill-table`), 6b0ea0b
(`feat(39-04): claude plugin skills, descriptions, order and env dirs in the scan`) and b0c2944
(`feat(39-04): MCP server names per host and the scanned skill roots`). Executed through three cross-AI lanes (pi router-env/my-coding),
one per task (314 s, 322 s, 311 s). The first lane's run ended `status=contract_violation` (findings `forbidden_path`,
`outside_plan_files`) only because the orchestrator's `docs(39-03)` commit (STATE.md, ROADMAP.md, 39-03-SUMMARY.md) landed while it
ran; the lane's own commit touches only its three files and was verified and kept.

## What changed

- `skills/ai-kit-spec-review/ai_kit_spec/skill_table.py`: `SKILL_NAME_RE`, `HOST_SKILL_ROOTS` (claude, codex, opencode, cursor, copilot,
  pi, agents with their config-dir variables), `host_root`, `root_rows`, `_row_key` (global before plugin, then folder, then name),
  `scan(env, cwd)` (per host `{skills, roots, mcp, mcp_note, notes}`, no cache, seed and roles through `table_inputs`), enabled Claude
  plugin skills (`plugin_rows`, copied from the GSD config skill's scan, never imported), `DESCRIPTION_MAX = 300` and `read_description`
  (bounded read), `mcp_names` (keys only through detection's registration map; FIFO, oversize, unreadable or non-table servers make that
  host `unknown`; pi `unknown` with `PI_MCP_NOTE`; agents `[]` with `AGENTS_MCP_NOTE`; unsafe or secret-shaped names hidden and counted),
  `skill_roots(result)`, `cmd_skill_table`, `register_parsers`, `COMMANDS`.
- `skills/ai-kit-spec-review/ai_kit_spec/cli.py`: the `skill-table` subcommand wired (three lines).
- `tests/test_skill_table.py`: `TestScanTracer`, `TestScanEdges`, `TestScanMcp` (38 tests in the module).

## Verification (run by the chunk agent)

- Acceptance greps: `def scan(env, cwd) -> dict:` 1, cli wiring 2, no `SKILLS_ROOTS`/`JEV_ENTRY_REL`, `read_description` and
  `plugin_rows` 2, no reference to the curated-config package, `mcp_names` and `skill_roots` 2; detection.py and the model baseline
  unchanged.
- Under a scratch HOME with the per-module report check: test_skill_table 38, test_arch 118, test_config_doctor 85, test_ai_kit_spec 688,
  test_cbm_detection 20, test_arch_hardcoded_models 23, all `report check: ok`. Lanes: `make ruff`, `make pyright`, `make vulture`,
  `make pylint` exit 0; hooks 136/136 on each commit.

## Deviations

- Shorter docstrings than the plan's text (`scan`, `mcp_names`, `plugin_rows`; same content). The description and MCP constants sit
  after `COMMANDS` in the module (appended in task order).
