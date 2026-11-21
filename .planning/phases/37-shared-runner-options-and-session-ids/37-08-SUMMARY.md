# 37-08 Summary: gates become facts

Status: complete after one no-change lane and two focused fix-up lanes (pi `router-env/my-coding`, same CLI and model throughout), verified by the orchestrator.

## Lanes

- Lane 1 (plan as written): `status=no_change exit=1 elapsed=40s tree=clean`, no edit.
- Fix-up a (XAI_FIXUP, the plan's Task 1 block verbatim plus framing): `status=ok exit=0 elapsed=435s attempts=1`, commit 1d30122.
- Fix-up b (XAI_FIXUP, the plan's Task 2 and 3 blocks verbatim plus framing): `status=ok exit=0 elapsed=684s attempts=1`, commit c434c97.

## Commits

- 1d30122 `feat(37-08): an id with no row passes parse and resolve and gets the named no-formula refusal`
- c434c97 `feat(37-08): one model id floor refuses, seed shapes advise, classify-only serves a cli with no row`

Each holds only `skills/ai-kit-spec-review/references/cross-ai.mjs`; the staged-tests hooks passed (128/128 modules each, per the lanes).

## What was done

- `RUNTIME_ID_RE`, `CLI_NAME_RE`, `ownValue(obj, key)`; `o.models` and `o.routes` are null-prototype maps; every CONFIG map read by a runtime name (`models`, `extraArgs`, `routerBacked`, `effort`) goes through `ownValue`.
- `parseArgs` checks `--runtime`, `--model-<cli>`, `--route-<cli>` and the running `--prefer` entry by charset only; `resolveRuntime` checks `CONFIG.runtime` and the first `CONFIG.prefer` entry by `RUNTIME_ID_RE` without printing the value; `main` refuses an id with no row with `cross-ai: no formula for <id> in the runner; pass --argv-file, or use a runtime it has a formula for` (usage, exit 2, no spawn).
- `MODEL_ID_FLOOR` (same source as `CURSOR_MODEL_ID`) refuses at parse for `--model` and every `--model-<cli>`, and in `main` for the resolved model (`cross-ai: the model for <runtime> must match ...`, value not printed); a row's seed shape prints the redacted advisory `cross-ai: note: model id shape is unusual for <runtime> (seed shape: ...)`; the live listing still ends `bad_model`. The pi comment no longer names a real tag.
- `--classify-only` classifies a cli with no row with the `cli: "*"` rows and `pattern: "unverified"`; only a cli outside `RUNTIME_ID_RE` is refused.
- 31 new or renamed self-test cases, all `logic`; `--self-test-list` 570 (542 + 28 new; three cases renamed).

## Evidence (orchestrator re-run, scratch HOME, `tmp/run-2026-11-19/c4-verify-37-08.sh`)

- Every acceptance grep at its expected count: `unknown runtime|unknown cli` 0, `known(` 0, CONFIG map reads 0, `modelRe` 0, the old `rt.modelId` refusal 0, `qwen3` 0, the old case name 0; the refusal, advisory, resolved-floor and classify lines 1 each; grok lines in the template 1 (none added); `router-env/` literals 2; `tests/fixtures/no_hardcoded_models_baseline.json` unchanged.
- All 31 names listed as `logic`; the three old names gone; the 31 plus `prefer-ignored-unknown-entry`, `ok`, `no_model`, `bad-model`, `pure-model-grammar`, `bad-model-id-0`, `bad-model-flag-0`, `model-other-runtime-not-checked`, `model-pi-colon-id`: `self-test ok`.
- Spot checks: `--runtime Claude` exits 2 with the named refusal; `--runtime pi --model glm --print-argv` exits 0 with the pi advisory; `--model -x` exits 2.
- `--print-argv` stdout equals the a9101a7 template for thirteen calls (eleven runtime and mode entries, pi with `--effort high`, cursor with `--session-id s-1`).
- Modules 5/5 (cli_help_flags, arch_hardcoded_models, runner_settings_argv, runner_dispatch, arch); eight shards plus `test_cross_ai_runner_e2e` and `test_ai_kit_spec_exec_formula_e2e` 10/10. Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0. Tree clean; the plan's scratch folder removed.
- Real-config audit (marker before lane 1): Claude host-session files (jobs, plugin store, skill sync), the codex daemon's logs and model cache, the lanes' pi sessions; none attributable to this plan.

## Deviations

- Existing case `cursor-bracket-other-rt` (`--print-argv --model-pi fake/ok[x=1]`) changed from exit 2 usage to exit 0 ok: it asserted the per-runtime charset that SPEC R5's floor replaces (lane lesson 4); comment reworded.
- The `--model` branch comment keeps the words `--model may` (two lines instead of the plan's one line): the plan's wording would remove the baseline hit `flag may` and force a baseline edit, which the plan's own acceptance forbids.
- `model-floor-refuses-*` builds its expected line as `` `cross-ai: ${'--model'} must match ...` `` so the hardcoded-model guard does not read `must` as a model literal; the expected text is unchanged.
- Executed as two fix-up lanes with one commit each instead of the plan's single commit (folded at the wave checkpoint).
