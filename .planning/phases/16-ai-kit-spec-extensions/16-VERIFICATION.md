---
phase: 16-ai-kit-spec-extensions
verified: 2026-10-14T18:00:00Z
status: human_needed
score: 4/4 must-haves verified
covered_files:
  - ".planning/phases/16-ai-kit-spec-extensions/16-01-PLAN.md"
  - ".planning/phases/16-ai-kit-spec-extensions/16-01-SUMMARY.md"
  - ".planning/phases/16-ai-kit-spec-extensions/16-02-PLAN.md"
  - ".planning/phases/16-ai-kit-spec-extensions/16-02-SUMMARY.md"
  - ".planning/phases/16-ai-kit-spec-extensions/16-03-PLAN.md"
  - ".planning/phases/16-ai-kit-spec-extensions/16-03-SUMMARY.md"
  - ".planning/phases/16-ai-kit-spec-extensions/16-04-PLAN.md"
  - ".planning/phases/16-ai-kit-spec-extensions/16-04-SUMMARY.md"
  - ".planning/phases/16-ai-kit-spec-extensions/16-05-PLAN.md"
  - ".planning/phases/16-ai-kit-spec-extensions/16-05-SUMMARY.md"
  - ".planning/phases/16-ai-kit-spec-extensions/16-06-PLAN.md"
  - ".planning/phases/16-ai-kit-spec-extensions/16-06-SUMMARY.md"
  - "skills/ai-kit-spec-config/SKILL.md"
  - "skills/ai-kit-spec-config/references/cli-model-selection.md"
  - "skills/ai-kit-spec-review/ai_kit_spec/cli.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/config_io.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/detection.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py"
  - "skills/ai-kit-spec-review/references/ranking-weights.toml"
  - "tests/fixtures/codex_debug_models.json"
  - "tests/fixtures/opencode_models_verbose.txt"
  - "tests/test_ai_kit_spec.py"
covered_digest: "v3:sha256:19a4c14e79864739e40a02de46b463206a64313d965a016fbf3fd3070f076544"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Run detect-current-runtime from inside a real interactive codex session (and, optionally, a real pi session)"
    expected: "Prints {\"native_runtime\": \"codex\"} (or \"pi\") with no other signal set; confirms CODEX_THREAD_ID / PI_CODING_AGENT are actually exported into the host's tool subprocesses"
    why_human: "Needs a real interactive codex/pi host session; this verifier runs inside Claude Code. The codex live check is deliberately deferred to Phase 20 (EVAL-04, 20 D-05); the pi live check to Phase 22. The code path and precedence are proven by tests and by CLI runs with synthetic env vars; only the claim that the real hosts set these variables is unproven, and the docstring already labels both signals source-inspected-only / not yet live-verified."
---

# Phase 16: ai-kit-spec extensions Verification Report

**Phase Goal:** The shared `ai_kit_spec` package correctly detects pi and codex host sessions, enumerates all five hosts' real models, and carries the richer catalog/ranker fields the curated-config rewrite depends on.
**Verified:** 2026-10-14
**Status:** human_needed (all four success criteria verified; one live-host signal check cannot be run here and is deliberately deferred)
**Re-verification:** No, initial verification
**Worktree:** `gsd/v1.3-curated-config-v2`; the CURRENT code was verified, not the 2026-09-24 snapshot. No regression from the roughly 125 later commits was found.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `detect-current-runtime` identifies pi and codex and honors pi > opencode > cursor > codex > claude | VERIFIED | `detection.py:33-40` `_RUNTIME_ENV_SIGNALS` is the exact 6-row tuple (codex owns two adjacent rows). I ran the real CLI (`ai-kit-spec.py detect-current-runtime`) with every other signal unset first. None -> `unknown`. pi+opencode+cursor+codex+claude -> `pi`. opencode+cursor+codex+claude -> `opencode`. cursor+codex+claude -> `cursor`. `CODEX_THREAD_ID`+claude -> `codex`. `CODEX_VERSION`+claude -> `codex`. claude alone -> `claude`. pi alone -> `pi`. `"pi"` accepted as `native_runtime` in both `model_catalog.py:39` and `config_io.py:97`. `TestDetectCurrentRuntime`, `TestRuntimePrecedenceMatrix`, `TestPiHostEndToEnd` pass. |
| 2 | `detect-runtimes` enumerates real models for codex (`codex debug models`) and claude (aliases + catalog ids + dated fallback) via the real binaries (never shell functions/aliases), with fixture-validated parsers | VERIFIED | `detect_codex_models` (`detection.py:201`) calls `run_fn([binary, "debug", "models"], ..., timeout=15)` with an argv list and no shell, where `binary` comes from `shutil.which`. A non-zero exit, OSError, timeout and bad JSON all degrade to `[]`. `parse_codex_debug_models` keeps `visibility == "list"` slugs only. The fixture `tests/fixtures/codex_debug_models.json` is real captured output (codex-cli 0.147.0, 6 slugs, 2 hidden). `claude_runtime_fields` returns aliases `fable/opus/sonnet/haiku` plus catalog ids (`models_source: catalog`) or the dated fallback (`dated-fallback`, as-of 2026-09-23); claude is never executed (`run_fn` is not called for it). No `shell=True`/`bash -i` anywhere in the enumeration path (the only `shell=True` hits are the pre-existing codegraph-MCP command builders). Live run below. |
| 3 | Catalog entries carry optional `image_input` and populated `reasoning_modes`; pre-change cache files still load | VERIFIED | `model_catalog.py:28-33` `_FIELD_TYPES` has `reasoning_modes: list`, `image_input: bool` and `image_input_source: str`, plus a rule that a source requires a bool `image_input`. A live catalog entry validates. The same entry with those 3 fields stripped (pre-change shape) validates (`None`). `image_input="yes"` is rejected. A legacy catalog file with no `_meta` and no new fields, fed to `fetch-model-catalog --if-stale`, exited 0, re-fetched, and was upgraded to `_meta.schema_version 2` with `image_input` populated on 176 entries. |
| 4 | Ranker accepts planning/general/mechanical/execution/review via the ranking-weights file; `review`/`execute` keep working as aliases | VERIFIED | `model_ranker.py:18-19` `CANONICAL_PURPOSES` and `PURPOSE_ALIASES = {"execute": "execution", "review": "review"}`. The shipped `ranking-weights.toml` has all five sections, plus `[mechanical.floor] coding_index = 35`. I ran `score_candidates` on a synthetic set under all five purposes and under `execute`. Each returned a ranking, and `execute` equals `execution` exactly. An old-format file containing only `[review]`/`[execute]` loads, `[execute]` is renamed to `execution`, and the missing purposes are filled from defaults. `mechanical` floor excludes entries below 35 or without a score. The wizard reference (`cli-model-selection.md:183-201`) is the only consumer and passes a `purpose`; the legacy names still resolve. |

**Score:** 4/4 truths verified (0 behavior-unverified). Precedence, degrade and alias behavior are exercised by passing tests and by direct CLI/function runs, not by symbol presence alone.

### Plan-level must-haves spot-checked against current code

| Plan truth | Status | Evidence |
|------------|--------|----------|
| 16-01: codex `models` lists only `visibility == "list"`, `reasoning_modes` map per slug, written to the existing catalog `reasoning_modes`, carried on `unmatched` | VERIFIED | Live: `clis.codex.models` = 7 slugs, `reasoning_modes` has 7 keys (e.g. `['low','medium','high','xhigh','max','ultra']`). The scratch catalog has 7 `openai/gpt-*` entries with `reasoning_modes`, and `openai/gpt-6.1-sol` carries `image_input: true`. Codex is absent from `unmatched`. |
| 16-03: `runtimes.json` and `model-catalog.json` carry `schema_version` (D-12); older/missing counts as stale | VERIFIED | Live: `runtimes.json.schema_version == 2`, `model-catalog.json._meta.schema_version == 2`. `TestRuntimesSchemaVersion`, `TestCatalogSchemaVersion`, `TestCacheStaleness` pass. |
| 16-04: claude convergence through the real refresh order, no loop | VERIFIED | Live sequence, see Spot-Checks. |
| 16-05: `image_input` provenance (`models_dev` / `opencode`), never `false` without a source | VERIFIED | Live: `(True, models_dev): 160`, `(False, models_dev): 16`, `(None, None): 31`. No `false` without a source. |
| 16-06: bool-rejecting numeric validation, optional per-purpose floor, `review` self-alias | VERIFIED | `TestPurposeAliasesEndToEnd` and `TestRankerPurposeFloor` pass. Code at `model_ranker.py:112,150,204`. |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `skills/ai-kit-spec-review/ai_kit_spec/detection.py` | VERIFIED | Substantive and wired: `_RUNTIME_ENV_SIGNALS`, `parse_codex_debug_models`, `detect_codex_models`, `claude_runtime_fields`, `claude_runtime_is_current`, `runtimes_schema_is_current`, `parse_opencode_verbose_image_input`. All called from `build_runtimes_snapshot` and `cli.py`. |
| `skills/ai-kit-spec-review/ai_kit_spec/cli.py` | VERIFIED | `detect-current-runtime` (`:883`), `detect-runtimes --if-stale` with three AND-ed skip conditions (`:888-908`), `fetch-model-catalog` with `_meta` handling (`:963,1082,1106`). |
| `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py` | VERIFIED | New fields and validators, `CATALOG_SCHEMA_VERSION`, `split_catalog_meta`. |
| `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py` + `references/ranking-weights.toml` | VERIFIED | Five purposes, aliases, floor. The TOML matches `DEFAULT_WEIGHTS`. |
| `tests/fixtures/codex_debug_models.json` | VERIFIED | Real capture, 7064 bytes, 6 models. |
| `tests/fixtures/opencode_models_verbose.txt` | VERIFIED | Real `opencode models --verbose` blocks. |
| `skills/ai-kit-spec-config/SKILL.md`, `references/cli-model-selection.md` | VERIFIED | Updated for codex enumeration and the pi native runtime. `16-SKILL-JUDGE.md` records 104/120, 0 Critical/Important, no regression. |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `build_runtimes_snapshot` | `detect_codex_models` / `claude_runtime_fields` / `detect_opencode_image_input` | direct calls (`detection.py:~415-430`) | WIRED |
| `detect-runtimes` CLI | runtimes cache | `--save` / `--if-stale` with schema and claude-freshness gates | WIRED (live: refresh, then `{}`) |
| `fetch-model-catalog` | runtimes `reasoning_modes` / `image_input` | `_runtime_meta_from_snapshot` / `_apply_runtime_meta` | WIRED (live: 7 codex entries carry `reasoning_modes`) |
| catalog `_meta.anthropic_model_ids` | runtimes `clis.claude.models` | `claude_runtime_fields(catalog_fn())` | WIRED (live convergence) |
| `ranking-weights.toml` | `score_candidates` | `load_ranking_weights` -> `resolve_purpose` | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| `clis.codex.models` / `reasoning_modes` | real `codex debug models` stdout | binary resolved by `shutil.which` | Yes (7 live models, newer than the fixture) | FLOWING |
| catalog `image_input` | models.dev `modalities.input` | live HTTP fetch | Yes (176 populated) | FLOWING |
| `clis.claude.models` | catalog `_meta.anthropic_model_ids` | models.dev anthropic provider, 17 ids | Yes | FLOWING |

### Behavioral Spot-Checks and Live Checks (scratch `XDG_CACHE_HOME`, nothing in the user's real cache)

Scratch dir: a fresh `mktemp -d` under the session scratchpad. No writes to `~/.claude`, `~/.cursor`, `~/.config/opencode`, `~/.codex`, `~/.pi` or `~/.gsd` were made by me. The detection commands do execute `codex debug models`, `opencode models`, `opencode models --verbose` and `cursor-agent models` as the code under test intends. Those CLIs may touch their own state dirs; I did not inspect that. `ARTIFICIAL_ANALYSIS_API_KEY` was not set, so AA scores were not exercised (the `artificial_analysis_ok: True` flag was reported anyway).

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Host precedence through the real CLI | `ai-kit-spec.py detect-current-runtime` under 8 env combinations | all 8 as expected (criterion 1) | PASS |
| Live enumeration | `detect-runtimes --save <scratch>/runtimes.json` | exit 0, `schema_version: 2`, codex 7 models / 7 reasoning_modes, claude `dated-fallback` (4 ids + 4 aliases), opencode 56, cursor-agent 259, grok installed. cursor-agent was enumerated although the interactive shell wraps it in a function, because PATH resolution found the real binary. | PASS |
| Live catalog | `fetch-model-catalog --runtimes-json ... --catalog-path ...` | exit 0, `models_dev_ok: True`, 207 entries, 0 rejections, `_meta.schema_version 2`, 17 `anthropic_model_ids`, `image_input` 160 true / 16 false / 31 absent, 7 codex entries with `reasoning_modes` | PASS |
| Claude convergence | `detect --if-stale`, `fetch --if-stale`, `detect --if-stale`, `fetch --if-stale` | 1: re-detect, claude becomes `catalog` with 17 ids, as-of 2026-10-14. 2: fetch skipped (`fetch_skipped: true`), no claude id in `unmatched`. 3: prints `{}` (converged, no loop). 4: no error. | PASS |
| Legacy catalog loads | strip `_meta` and the new fields from the catalog, then `fetch-model-catalog --if-stale` | exit 0, re-fetched, upgraded to schema 2 | PASS |
| Ranker | `score_candidates` for 5 purposes + `execute`; old `[review]/[execute]` TOML | all rank, `execute` == `execution`, old file loads | PASS |
| Phase 16.1 criterion 6 ("runtimes.json carries schema_version, model-catalog.json exists") | inspected the scratch files | `schema_version: 2` in both | PASS |

### Test Runs (executed by me)

| Command | Result |
|---------|--------|
| `python3 -m unittest tests.test_ai_kit_spec` | 594 tests, OK |
| Broad regression: `tests.test_ai_kit_spec tests.test_ai_kit_spec_gsd tests.test_ai_kit_spec_superpowers tests.test_ai_kit_gsd_curated_config tests.test_ai_kit_opencode_providers tests.test_ai_kit_usage_metrics` | 1041 tests, OK (skipped=3) |
| The 21 named classes from 16-VALIDATION.md quick/per-task commands (`TestDetectCurrentRuntime`, `TestBuildRuntimesSnapshot`, `TestValidateCatalogEntry`, `TestLoadRankingWeights`, `TestScoreCandidates`, `TestCacheStaleness`, `TestPiHostEndToEnd`, `TestRuntimePrecedenceMatrix`, `TestParseCodexDebugModels`, `TestDetectCodexModels`, `TestCodexEnumerationEndToEnd`, `TestClaudeFallback`, `TestClaudeRuntimeFreshness`, `TestClaudeCatalogMaterialization`, `TestClaudeEnumerationEndToEnd`, `TestImageInputEndToEnd`, `TestOpencodeVerboseImageInput`, `TestPurposeAliasesEndToEnd`, `TestRankerPurposeFloor`, `TestRuntimesSchemaVersion`, `TestCatalogSchemaVersion`) | 192 tests, OK |
| `make test-unit` (offline uv env) | OK (22 + 6 tests in the tail) |
| `make arch-test` | 22 tests, OK |
| `make ruff` (pre-commit hook) | Passed (confirms the WR-01..WR-04 fixes are still in place) |

I did not re-run `make test-integration`, `make e2e-test` or the other `make validate` hook targets (pylint, pyright, vulture, shellcheck). 16-06's gate ran them; I trust that record only for those.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| SPEC-01 | 16-02 | pi and codex host detection, precedence pi > opencode > cursor > codex > claude | SATISFIED (real-host signal unproven, see Human Verification) | Truth 1 |
| SPEC-02 | 16-01, 16-03, 16-04 | codex and claude enumeration via real binaries, fixture-validated parsers | SATISFIED | Truth 2 |
| SPEC-03 | 16-01, 16-03, 16-05 | optional `image_input`, populated `reasoning_modes`, old caches still load | SATISFIED | Truth 3 |
| SPEC-04 | 16-06 | five ranker purposes, `review`/`execute` aliases | SATISFIED | Truth 4 |

All four IDs declared in PLAN frontmatter (SPEC-01, -02, -03, -04) appear in REQUIREMENTS.md and map to Phase 16 in its traceability table. No orphaned Phase 16 requirement: the Phase 16 rows in the table are exactly SPEC-01..04. SPEC-05 (pi enumeration, Phase 18) and SPEC-06 (cursor wrapper, Phase 21) are out of scope here by D-06. REQUIREMENTS.md still shows these four as `Pending` / unchecked. That is a tracking artifact for the orchestrator to flip, not a code gap.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| (all phase-modified source, TOML and docs) | `TBD`/`FIXME`/`XXX` debt markers | none found | clean |

Review findings WR-01..WR-04 and IN-01 were all fixed (`99ccb98`). `make ruff` passes now.

### Deferred Items

None. The codex real-host live check is listed under Human Verification because VALIDATION.md and ROADMAP defer it to Phase 20 (EVAL-04); it is a documented manual check, not a code gap.

### Human Verification Required

#### 1. Real codex (and pi) host signal

**Test:** From inside a real interactive codex session, run `python3 skills/ai-kit-spec-review/ai-kit-spec.py detect-current-runtime`. Do the same from a real pi session if practical.
**Expected:** `{"native_runtime": "codex"}` (or `"pi"`), with `CODEX_THREAD_ID` / `PI_CODING_AGENT` present in the tool subprocess environment.
**Why human:** Needs a real codex/pi host; this verification ran inside Claude Code. Codex is deferred to Phase 20 (EVAL-04, 20 D-05) and pi to Phase 22. The `detect_current_runtime` docstring already labels pi, `CODEX_THREAD_ID` and `CODEX_VERSION` as source-inspected-only or observed-in-snapshots, not live-verified. `REQUIREMENTS.md` also notes that `CODEX_VERSION` is absent from the codex 0.153.4 binary and is expected to be dropped by Phase 20 D-05. That is not a defect here, since detection also reads `CODEX_THREAD_ID`.

### Gaps Summary

No gaps. All four ROADMAP success criteria hold on the current code, with live evidence from the real codex, opencode and cursor-agent binaries and from models.dev, plus 1041 passing regression tests. The status is `human_needed` solely because the real-host codex/pi signal check cannot be run from a Claude Code host and is intentionally deferred.

---

_Verified: 2026-10-14_
_Verifier: Claude (gsd-verifier)_
