# 37-03 Summary: the runner's call vocabulary and strict call-file readers

Status: complete. Executed by the cross-AI lane (pi `router-env/my-coding`, `AIKIT-XAI status=ok exit=0 elapsed=559s attempts=1 cycles=0`), verified by the orchestrator.

## Commits

- b3ca3e9 `feat(37-03): parse shared runner options` (`skills/ai-kit-spec-review/references/cross-ai.mjs` only, +238 -4; the commit hook passed, 128/128 modules per the lane)

## What was done

- `parseArgs` takes `--role review|execute` (drives `o.mode`; `--mode` stays an alias; a disagreement is exit 2 `cross-ai: --role and --mode disagree`), `--effort <level>` (`--codex-effort` is an alias; differing values are a usage error), `--context`, `--escalate-runtime`, `--escalate-model`, `--session-id`, `--host auto|none`, repeatable `--skill-path` and `--skill-name`, `--mcp-config`, `--argv-file` and `--describe`. Each value is shape-checked (`LEVEL_RE`, `CONTEXT_RE`, `SESSION_ID_RE`, `SKILL_NAME_RE`, `CONTROL_CHAR_RE`) and stored on the options; no argv changes yet.
- The closed `CODEX_EFFORTS` parse check is replaced by `LEVEL_RE`, so `--codex-effort max` reaches codex as `model_reasoning_effort=max`; `CODEX_EFFORTS` and `PI_THINKING` stay declared for main's `knobs`. Self-test `codex-effort-bogus` now uses `Bogus` (still exit 2, by shape).
- `FILE_READ_MAX = 65536`, `readCallFile(flag, relPath, { cwdOnly, mode, cwd })` (realpath and cwd containment, non-blocking open, dev/ino match between stat and fstat, regular file only, forbidden-mode mask, size cap, strict UTF-8, BOM refused) and `strictJson` (duplicate keys refused at any depth, escaped duplicates included).
- 33 new self-test cases: six `reader-*` (one `runtime` kind, the FIFO case) and 27 `vocab-*` (23 usage rows plus `vocab-role-alias`, `vocab-boundaries-pass`, `vocab-stored-only`, `vocab-codex-effort-level`); the flag doc comment documents every new flag.

## Evidence (orchestrator re-run, scratch HOME)

- `--print-argv --runtime pi --model fake/ok --role review` holds `"--no-mcp"`; `--role review --mode exec` exits 2 with the exact line; codex `--codex-effort max` carries `model_reasoning_effort=max`; the parse-only flag set leaves pi's argv equal to a run without them.
- No-flag argv equals the 9b3ba32 template's for pi exec and review, codex exec, claude review, copilot exec, cursor review, opencode exec and codex exec with `--codex-effort high` (session id and temp path normalised).
- Acceptance greps: `CODEX_EFFORTS.has(o.codexEffort)` 0; five shape constants; `FILE_READ_MAX` 1; `readCallFile`/`strictJson` 2; `name: 'reader-` 6; vocab rows 23; vocab objects 4; all required message and API strings present.
- `--self-test-list`: 515 cases, 468 logic, 47 runtime (482 at HEAD plus 33). Cases `codex-effort-bogus`, `codex-knobs`, `argv-codex-effort-flag-wins`, `cursor-mode-exec-usage`, the six reader cases and all 27 vocab cases: `self-test ok`.
- The eight self-test shard modules: 8/8 passed. `test_lane_effort`, `test_ai_kit_spec_runtimes_table`, `test_runtime_list_drift`, `test_opencode_help_flags`, `test_cross_ai_skill_text`, `test_arch_hardcoded_models`, `test_curated_config_script`, `test_cli_help_flags`: 8/8 passed.
- Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` passed; `tmp/p37-03` removed. Tree clean.
- Real-config audit: the orchestrating Claude session's files, another agent's `~/.codex` files and `~/.cursor/cli-config.json` (08:38); the lane's pi session shows no cursor-agent call, so that file is not from this plan.

## Deviations

- One commit for the three tasks instead of one per task (the end state is the same; the wave fold merges plan commits anyway).
- The lane's first run of the four vocab pass-through cases failed (`.code` instead of `.status`); fixed before the commit.
- The live copy `.planning/scripts/cross-ai.mjs` is not re-rendered here (plan 37-23 does it), so it now differs from the template outside the config block.
