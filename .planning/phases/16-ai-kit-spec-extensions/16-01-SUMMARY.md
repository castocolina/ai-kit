---
phase: 16-ai-kit-spec-extensions
plan: 01
subsystem: ai_kit_spec
executor: cross-ai (opencode run --model router-env/my-coding)
actuals:
  commits: 2
key-files:
  created:
    - tests/fixtures/codex_debug_models.json
  modified:
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/model_detect.py
    - skills/ai-kit-spec-config/SKILL.md
    - skills/ai-kit-spec-config/references/cli-model-selection.md
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - tests/test_ai_kit_spec.py
completed: 2026-09-24
---

# Phase 16 Plan 01: Codex model enumeration end-to-end Summary

## What changed

`detect-runtimes` now enumerates codex's real, user-selectable models from the actual codex binary (`[<resolved-path>, "debug", "models"]`, 15s timeout, argv list — never a shell string), and `fetch-model-catalog` carries each model's CLI-reported reasoning effort levels into the model catalog's existing `reasoning_modes` field — end-to-end.

- **Parser + detection** (`detection.py`): new `parse_codex_debug_models` (JSON stdout → `[{"id", "reasoning_modes"}]`, `visibility == "list"` only, first-slug-wins, reads only `slug`/`visibility`/`supported_reasoning_levels[].effort`, every malformed input degrades to `[]` and never raises) and `detect_codex_models` (mirrors the opencode/cursor-agent parser shape; non-zero exit is a failure and yields `[]`, as does a stub result without `returncode`). `build_runtimes_snapshot` gained a `codex` branch that sets `models` + `reasoning_modes` only on a non-empty enumeration — otherwise the entry stays `{"installed": True, "path": ...}` (the degrade path, so single-provider reconciliation is unchanged). Stale comments claiming codex has no models list were corrected.
- **Catalog plumbing** (`cli.py`): new `_runtime_meta_from_snapshot` (extracts per-`(cli, model_id)` `reasoning_modes` from the runtimes snapshot; malformed input skipped, never raised) and `_apply_runtime_meta` (copies a non-empty CLI-reported list onto an entry). `build_model_catalog` takes a new last `runtime_meta` parameter, applies it on BOTH matched paths immediately before `merge_catalog_entry`, and carries it through BOTH `unmatched.append` sites (via a local `record`) so a brand-new codex slug's effort levels still reach the wizard's confirmation payload.
- **Fixture**: `tests/fixtures/codex_debug_models.json` — trimmed capture of real `codex debug models` output (codex-cli 0.147.0, captured 2026-09-23; six slugs in order, `model_messages` replaced by a placeholder). Provenance recorded in a comment block next to `CODEX_FIXTURE_PATH` in the test file.
- **Tests**: `TestCodexEnumerationEndToEnd` (5 tracer tests: fixture → detect-runtimes → runtimes.json → fetch-model-catalog → catalog `reasoning_modes`; hidden slugs excluded; `instructions_template`/`model_messages` never persisted; every written codex entry passes `validate_catalog_entry`; unmatched slug carries `reasoning_modes`), `TestParseCodexDebugModels` + `TestDetectCodexModels` (the full degrade matrix incl. non-zero exit and argv/timeout/no-shell pins), plus 3 `TestBuildRuntimesSnapshot` cases (models+reasoning_modes from fixture; OSError → exact bare entry; exit 1 → exact bare entry).
- **Wizard docs corrected**: `ai-kit-spec-config/SKILL.md` no longer claims codex cannot be enumerated (now points at `clis.codex.models` and the degrade-to-research path); `cli-model-selection.md` updated both multi-provider/single-provider parentheticals and documents copying an unmatched entry's CLI-reported `reasoning_modes` verbatim into the confirmation entry; `ai_kit_gsd_curated_config/model_detect.py`'s `build_candidate_pool` docstring now matches the post-Phase-16 snapshot shape (docstring-only).

## Files

- `tests/fixtures/codex_debug_models.json` — created (Task 1)
- `skills/ai-kit-spec-review/ai_kit_spec/detection.py` — modified (Task 1)
- `skills/ai-kit-spec-review/ai_kit_spec/cli.py` — modified (Task 1)
- `tests/test_ai_kit_spec.py` — modified (Tasks 1 and 2)
- `skills/ai-kit-spec-config/SKILL.md` — modified (Task 2)
- `skills/ai-kit-spec-config/references/cli-model-selection.md` — modified (Task 2)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/model_detect.py` — modified, docstring only (Task 2)

## Commits

```
051cea1 test(16-01): pin codex parser degrade contract and document codex enumeration
87c5afa feat(16-01): enumerate codex models end-to-end into the model catalog
```

## Test results

- Task 1 verify (`TestCodexEnumerationEndToEnd` + `TestBuildRuntimesSnapshot` + `TestBuildModelCatalog` + `TestFetchModelCatalogCli`): `Ran 57 tests` — **OK** (exit 0)
- Task 2 verify 1 (`TestParseCodexDebugModels` + `TestDetectCodexModels` + `TestBuildRuntimesSnapshot` + `TestCodexEnumerationEndToEnd`): `Ran 28 tests` — **OK** (exit 0; 16 parser/detector tests as required)
- Task 2 verify 2 (six stdlib modules): `Ran 927 tests` — **OK** (exit 0; pre-change broad baseline was 903)
- `python3 -m unittest tests.test_ai_kit_spec`: `Ran 464 tests` — **OK** (pre-change baseline 459; count only grows)
- `make test-unit`: **exit 2** — `Ran 2559 tests in 11.664s`, `FAILED (errors=1, skipped=20)`; the single error is the pre-existing environment failure listed below. All Phase 16 test classes and every file this plan touched pass inside it.

## Pre-existing failures

- `ERROR: test_real_render_produces_image (tests.test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image)` (provisional) — `render_mermaid.MermaidRenderError: mermaid render failed at line 1: node:internal/modules/cjs/loader:1520 ... Error: Cannot find module '/home/bazzite/.local/share/pnpm/global/v11/ca026-19fa5b731c0-0ac52087022f9fc0/node_modules/@mermaid-js/mermaid-cli/src/cli.js'` — a broken/removed local `@mermaid-js/mermaid-cli` pnpm-global install on this machine. Neither the failing test, its traceback, nor `render_mermaid.py` is touched by any file this plan modified; per the objective's rule it is reported verbatim (provisional) rather than fixed by editing unrelated code. Reproduced at the failing state; 16-06 Task 3 owns confirming it at the pre-phase base commit.

## Pending orchestrator gates

skill-judge: skills/ai-kit-spec-config/SKILL.md — pending (orchestrator-owned, blocking)

## Decisions honored

- **16 D-05**: codex enumeration runs `codex debug models` from the real PATH-resolved binary; the parser is built from the real captured output stored as the test fixture `tests/fixtures/codex_debug_models.json`, and every failure mode degrades to an empty or partial list, never a crash.
- **16 D-06**: `detect_opencode_models` / `detect_cursor_agent_models` and their snapshot branches are untouched; pi enumeration remains deferred to Phase 22.
- **16 D-07**: codex is invoked as an argv list on the `which_fn`-resolved real binary (`timeout=15`, no `shell=True`, no command string, never `bash -i`), pinned by `test_invokes_the_resolved_real_binary_with_an_argv_list`.
- **16 D-08**: reasoning levels land in the catalog's existing, already-validated `reasoning_modes` field; no new reasoning field was added (`model_catalog.py` unchanged).
- **Orchestrator resolution 3**: the fixture is derived from the real capture in 16-RESEARCH.md Pattern 2 and stored as a file under `tests/fixtures/` (provenance comment documents kept-vs-replaced fields and why the 259 KB raw capture is not committed).

## Deviations

None. (One incidental cleanup beyond the letter of the plan: the new tests read files via `with open(...)` context managers / a `_read_file` helper to avoid unclosed-file `ResourceWarning`s; test content and coverage are exactly as specified.)

## Cross-AI execution (orchestrator record)

- Executor: `opencode run --model router-env/my-coding` (cross_ai: true), prompt = plan <objective> + <tasks> via stdin.
- Automatic session resumes after transient provider errors: 2.
- Orchestrator verification: re-ran make test-unit independently: 2559 tests, only error = pre-existing mmdc environment test (test_markdown_to_pdf.TestRenderRealMmdc), untouched by this plan; 2 feat/test commits reviewed (87c5afa, 051cea1).
