---
phase: 16-ai-kit-spec-extensions
verified: 2026-10-15T05:30:00Z
status: passed
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
  - "skills/ai-kit-spec-review/ai_kit_spec/cache.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/catalog_build.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/cli.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/config_io.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/detection.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py"
  - "skills/ai-kit-spec-review/references/ranking-weights.toml"
  - "tests/fixtures/codex_debug_models.json"
  - "tests/fixtures/opencode_models_verbose.txt"
  - "tests/test_ai_kit_spec.py"
covered_digest: "v3:sha256:8b1138c0ed7eece2b87ccc148ea8fc2538a812d210546f441f3656019fc8c5e4"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 4/4
  gaps_closed:
    - "Real codex/pi host signal: non-interactive `codex exec` and `pi -p` runs with the parent's host signals scrubbed print codex and pi (16.1-24 Task 1); the interactive-session check moves to Deferred Items (Phases 20 and 22, RUN-10)"
  gaps_remaining: []
  regressions: []
deferred:
  - truth: "detect-current-runtime prints codex from inside a real INTERACTIVE codex session (CODEX_THREAD_ID exported into the interactive host's tool subprocesses)"
    addressed_in: "Phase 20"
    evidence: "Phase 20 goal: 'The skill is confirmed working from real codex and opencode host sessions, resolving the two open verifications the spec left pending.' (EVAL-04, 20 D-05); RUN-10 assigns the interactive item to Phases 20 and 22"
  - truth: "detect-current-runtime prints pi from inside a real INTERACTIVE pi session (PI_CODING_AGENT exported into the interactive host's tool subprocesses)"
    addressed_in: "Phase 22"
    evidence: "Phase 22 goal: 'The skill is confirmed working from a real pi host session; pi's \"not live-validated\" label is lifted.'"
  - truth: "detect-runtimes enumerates pi models (the fifth host named in the phase goal)"
    addressed_in: "Phase 18"
    evidence: "REQUIREMENTS.md SPEC-05: 'detect-runtimes enumerates pi (pi --list-models) ... moved from Phase 22 to Phase 18 on 2026-10-14' (split out of SPEC-02 by Phase 16 D-06)"
---

# Phase 16: ai_kit_spec Extensions Verification Report

**Phase Goal:** The shared `ai_kit_spec` package correctly detects pi and codex host sessions, enumerates all five hosts' real models, and carries the richer catalog/ranker fields the curated-config rewrite depends on.
**Verified:** 2026-10-15
**Status:** passed
**Re-verification:** Yes. The previous report (2026-10-14) was `human_needed` on one item, the real-host codex/pi signal. Plan 16.1-24 Task 1 produced new live evidence (D-24, RUN-10).

I verified the CURRENT code on `gsd/v1.3-curated-config-v2`, after the Phase 16.1 refactors (argv dispatch table `_COMMANDS` in `cli.py`, catalog build moved to `catalog_build.py`, `mkstemp` atomic cache writes in `cache.py`, `HOST_SIGNAL_ENV_VARS` scrub set, trust gate and error classifier). I did not rely on the old SUMMARY claims. I ran every test listed below myself.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `detect-current-runtime` identifies pi and codex in addition to opencode/cursor/claude, precedence pi > opencode > cursor > codex > claude | VERIFIED | `detection.py:51-58` `_RUNTIME_ENV_SIGNALS` is the 6-row tuple (codex owns two adjacent rows); `detect_current_runtime` (`:71`) walks it with a truthiness check. Dispatch: `cli.py:865` maps `detect-current-runtime` to `_cmd_detect_current_runtime` (`:365`). I ran the real entry point with all six signals unset, then set: none -> `unknown`; all five -> `pi`; opencode+cursor+codex+claude -> `opencode`; cursor+codex+claude -> `cursor`; `CODEX_THREAD_ID`+claude -> `codex`; `CODEX_VERSION`+claude -> `codex`; claude -> `claude`; pi -> `pi`; `PI_CODING_AGENT=""`+claude -> `claude`. `"pi"` is accepted as `native_runtime` in `model_catalog.py:53` and `config_io.py:177`. `TestDetectCurrentRuntime`, `TestRuntimePrecedenceMatrix` and `TestPiHostEndToEnd` pass. Real hosts (non-interactive): see the next section. |
| 2 | `detect-runtimes` enumerates real models for codex (`codex debug models`) and claude (aliases + catalog ids + dated fallback) through the actual binaries, with fixture-validated parsers | VERIFIED | `detect_codex_models` (`detection.py:224`) runs `[binary, "debug", "models"]` as an argv list with `timeout=15`; `binary` comes from `shutil.which` via `detect_installed_clis`. A non-zero exit, OSError, timeout or bad JSON all give `[]`. `parse_codex_debug_models` keeps only `visibility == "list"`. `claude_runtime_fields` (`:382`) never executes claude. `grep shell=True\|bash -i` over `ai_kit_spec/*.py` finds nothing. Live (16.1-24): `clis.codex.models` has 7 slugs, each with `reasoning_modes`; `clis.claude` went from `dated-fallback` (4 ids) to `catalog` (17 ids, as of 2026-10-15); opencode has 44 ids and cursor-agent 259. The fixture tests pass: `TestParseCodexDebugModels`, `TestDetectCodexModels`, `TestCodexEnumerationEndToEnd`, `TestClaudeFallback`, `TestClaudeEnumerationEndToEnd`. |
| 3 | Catalog entries can carry optional `image_input` and `reasoning_modes`; cache files written before the change still load | VERIFIED | `model_catalog.py:28-33` `_FIELD_TYPES` declares `reasoning_modes: list`, `image_input: bool` and `image_input_source: str`, plus the pairing rule (`:150-152`). In the refreshed real catalog all 195 entries validate. `image_input` is `(True, models_dev)` 154, `(False, models_dev)` 10 and absent 31. No entry has `false` without a source. All 7 codex entries carry `reasoning_modes`. The same 195 entries with `image_input`/`image_input_source`/`reasoning_modes` removed (the old shape) validate with 0 errors. `image_input="yes"` is rejected. `TestCatalogSchemaVersion`, `TestImageInputEndToEnd` and `TestValidateCatalogEntry` pass. See the Warning on the opencode `--verbose` source. |
| 4 | The ranker accepts planning/general/mechanical/execution/review through the ranking-weights file; `review`/`execute` keep working as aliases | VERIFIED | `model_ranker.py:18-19` has `CANONICAL_PURPOSES` and `PURPOSE_ALIASES = {"execute": "execution", "review": "review"}`. `ranking-weights.toml` has all five sections plus `[mechanical.floor]`. I loaded the shipped file and scored 60 real catalog entries: planning 60, general 60, mechanical 20 (the floor drops the rest), execution 60, review 60, execute 60. `execute` returns exactly what `execution` returns. A weights file with only `[review]` and `[execute]` loads, and missing purposes come from defaults. `TestPurposeAliasesEndToEnd`, `TestRankerPurposeFloor`, `TestLoadRankingWeights` and `TestScoreCandidates` pass. |

**Score:** 4/4 truths verified (0 behavior-unverified). Precedence, degrade, convergence and alias behavior are all exercised by passing tests and by direct CLI runs, not by symbol presence alone.

### Plan-level must-haves (re-checked against current code)

| Plan | Truth | Status | Evidence |
|------|-------|--------|----------|
| 16-01 | Codex `models` lists only `visibility == "list"`; `reasoning_modes` reaches the existing catalog field; failures degrade with no `models` key; no `model_messages` stored | VERIFIED | Fixture tests pass. In the live cache, 7 codex entries carry `reasoning_modes`. `parse_codex_debug_models` reads only `slug`, `visibility` and `supported_reasoning_levels[].effort`. |
| 16-02 | pi/codex detection; pi is accepted by both validators; docstring confidence labels; `KNOWN_CLIS` has no pi | VERIFIED | `detection.py:20` `KNOWN_CLIS` has no pi. The docstring (`:94-111`) labels pi and `CODEX_VERSION` source-inspected-only and `CODEX_THREAD_ID` not yet live-verified from a codex host. That is still accurate: the new evidence is non-interactive only. |
| 16-03 | `schema_version` on `runtimes.json` and `_meta.schema_version` on the catalog; missing or older versions refresh; atomic single-writer cache | VERIFIED | Real cache: `runtimes.json.schema_version == 2` (`runtimes_schema_is_current` True), and `_meta` is a top-level key with `schema_version: 2`. 16.1-29 replaced the fixed `<path>.tmp` with `mkstemp` + `os.replace` (`cache.py:23-39`). That is stronger than the 16-03 contract, not a regression. The sibling `_meta` readers pass (`tests.test_ai_kit_opencode_providers`, `tests.test_ai_kit_usage_metrics`: 235 tests OK). |
| 16-04 | Claude converges through the real refresh order with no loop; dated fallback labeled | VERIFIED | Live, below: detect 1 gives `dated-fallback`, fetch 1 records 17 anthropic ids, detect 2 re-detects once and gives `catalog`, fetch 2 is skipped. I then ran a fifth `detect-runtimes --if-stale` on a scratch copy of the refreshed cache (`PATH=/nonexistent`, so it could not reach any CLI). It printed `{}`, so the edge does not loop. `claude_runtime_is_current(runtimes, catalog)` is True on the real cache. |
| 16-05 | `image_input` provenance (`models_dev` / `opencode`); never `false` without a source; opencode `--verbose` source with degrade on non-zero exit | VERIFIED (code and fixture); live opencode source inactive, see the Warning | `catalog_build.py:119-151` handles models.dev and `:252-269` the opencode runtime source. `TestOpencodeVerboseImageInput` and `TestImageInputEndToEnd` pass. Live: the installed opencode is v2.0.29 and rejects `--verbose` (`Unrecognized flag: --verbose`, exit 1). As contracted, the result is `{}` with no `clis.opencode.image_input` key. |
| 16-06 | Five purposes, aliases, bool-rejecting validation, floor before normalization; skill-judge gate | VERIFIED | Ranker spot-check above. Skill-judge: `16-SKILL-JUDGE.md` 104/120 with 0 Critical/Important. The 16.1 re-judge (`16.1-SKILL-JUDGE-ai-kit-spec-config.md`) gives 99/120 against a 96 baseline, with no Important finding. |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `skills/ai-kit-spec-review/ai_kit_spec/detection.py` | VERIFIED | `_RUNTIME_ENV_SIGNALS`, `HOST_SIGNAL_ENV_VARS`, `detect_codex_models`, `parse_codex_debug_models`, `claude_runtime_fields`, `claude_runtime_is_current`, `runtimes_schema_is_current`, `detect_opencode_image_input`, all wired from `build_runtimes_snapshot` and `cli.py`. |
| `skills/ai-kit-spec-review/ai_kit_spec/cli.py` | VERIFIED | `_COMMANDS` dispatch (`:862-885`). `_cmd_detect_runtimes` (`:369`) has the three AND-ed skip conditions (TTL, schema, claude freshness). `_cmd_fetch_model_catalog` (`:526`) handles `_meta` and the skip sidecar. |
| `skills/ai-kit-spec-review/ai_kit_spec/catalog_build.py` | VERIFIED | `image_input` sourcing, `_runtime_meta_from_snapshot`, `_apply_runtime_meta`. |
| `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py`, `config_io.py` | VERIFIED | New fields, validators, `CATALOG_SCHEMA_VERSION`, `split_catalog_meta`/`join_catalog_meta`, `pi` in both native-runtime sets. |
| `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py`, `references/ranking-weights.toml` | VERIFIED | Five purposes, aliases, floor. |
| `tests/fixtures/codex_debug_models.json`, `tests/fixtures/opencode_models_verbose.txt` | VERIFIED | Real captures, used by the passing parser tests. |
| `skills/ai-kit-spec-config/SKILL.md`, `references/cli-model-selection.md` | VERIFIED | Codex enumeration and pi native runtime documented; skill-judge bar met. |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `ai-kit-spec.py` | `ai_kit_spec.cli.main` | `_dispatch` -> `_COMMANDS[args.command]` | WIRED (the live runs went through this path) |
| `build_runtimes_snapshot` | `detect_codex_models` / `claude_runtime_fields` / `detect_opencode_image_input` | direct calls (`detection.py:436-458`) | WIRED |
| `detect-runtimes --if-stale` | runtimes cache | TTL + `runtimes_schema_is_current` + `claude_runtime_is_current` | WIRED (live: refresh, re-detect once, then `{}`) |
| `fetch-model-catalog` | runtimes `reasoning_modes` / `image_input` | `_runtime_meta_from_snapshot` / `_apply_runtime_meta` | WIRED (7 codex entries carry `reasoning_modes`) |
| catalog `_meta.anthropic_model_ids` | runtimes `clis.claude.models` | `claude_runtime_fields(_read_default_catalog())` | WIRED (17 ids converged) |
| `ranking-weights.toml` | `score_candidates` | `load_ranking_weights` -> `resolve_purpose` | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| `clis.codex.models` / `reasoning_modes` | `codex debug models` stdout | PATH-resolved codex binary | Yes, 7 live slugs (`gpt-6.1-sol` ... `gpt-5.6-luna`) | FLOWING |
| catalog `image_input` | models.dev `modalities.input` | live HTTP fetch (`models_dev_ok: true`) | Yes, 164 entries with a models.dev statement | FLOWING |
| catalog `image_input` (opencode source) | `opencode models --verbose` | opencode v2.0.29 | No: the flag no longer exists, so the result is `{}` | STATIC (degrades as contracted, see the Warning) |
| `clis.claude.models` | catalog `_meta.anthropic_model_ids` | models.dev anthropic provider | Yes, 17 ids, as of 2026-10-15 | FLOWING |

## Live-check record (plan 16.1-24 Task 1, D-24)

Source: transcript `tmp/16.1-24-live-checks.txt` and `.planning/phases/16.1-hardening/16.1-24-SUMMARY.md`. Task 1 ran from this checkout's own entry point against the real `~/.cache/ai-kit/spec`, with stdin closed and a 600 s timeout per command. Outputs below are trimmed; each command's full JSON is in the transcript.

**Branch-code proof** (transcript line 1; the path is under `git rev-parse --show-toplevel`):

```
ai_kit_spec.__file__: <checkout>/skills/ai-kit-spec-review/ai_kit_spec/__init__.py
```

**The four `--if-stale` commands** (`RT=~/.cache/ai-kit/spec/runtimes.json`, `CAT=~/.cache/ai-kit/spec/model-catalog.json`, both taken from `cache-path`):

```
$ timeout 600 python3 skills/ai-kit-spec-review/ai-kit-spec.py detect-runtimes --if-stale "$RT" < /dev/null
{"schema_version": 2, "clis": {"claude": {..., "models_source": "dated-fallback", ...}, "codex": {7 models}, "opencode": {44}, "grok": {installed}, "cursor-agent": {259}}}
exit=0
$ timeout 600 python3 skills/ai-kit-spec-review/ai-kit-spec.py fetch-model-catalog --if-stale --runtimes-json "$RT" --catalog-path "$CAT" < /dev/null
{"catalog_path": ".../model-catalog.json", "entry_count": 195, "rejections": [], ..., "models_dev_ok": true, "artificial_analysis_ok": true, "fetch_skipped": false}
exit=0
$ timeout 600 python3 skills/ai-kit-spec-review/ai-kit-spec.py detect-runtimes --if-stale "$RT" < /dev/null
{"schema_version": 2, "clis": {"claude": {..., "models": [17 ids], "models_source": "catalog", ...}, ...}}
exit=0
$ timeout 600 python3 skills/ai-kit-spec-review/ai-kit-spec.py fetch-model-catalog --if-stale --runtimes-json "$RT" --catalog-path "$CAT" < /dev/null
{"catalog_path": ".../model-catalog.json", "entry_count": 195, "rejections": [], ..., "models_dev_ok": false, "artificial_analysis_ok": false, "fetch_skipped": true}
exit=0
```

The second `detect-runtimes --if-stale` re-detects instead of printing `{}`. That is the 16-04 claude freshness edge: fetch 1 recorded anthropic ids, so the cached `dated-fallback` claude entry is stale exactly once. My fifth run, on a scratch copy of the resulting cache, printed `{}`.

**Post-check cache state** (I read the real files myself; I did not trust the SUMMARY): `runtimes.json` `schema_version` = **2**. `model-catalog.json` has a top-level **`_meta`** = `{schema_version: 2, anthropic_model_ids: 17 ids, anthropic_model_ids_as_of: "2026-10-15"}` and 195 entries. 150 of the 195 carry an Artificial Analysis score. Both files were last written at 00:56:02 -0300 on 2026-10-15, after the transcript's commands.

## Real-host evidence (NON-INTERACTIVE only)

The codex and pi evidence comes from **non-interactive** `codex exec` and `pi -p` runs. It does not come from interactive sessions. `tmp/16.1-24-scrubbed-run.py` removed every name in `HOST_SIGNAL_ENV_VARS` from the parent environment, closed stdin and set a 600 s timeout. So the signal each child saw was set by the host CLI itself, not inherited from the parent pi/Claude session.

- `codex exec -s read-only -C . "Run python3 skills/ai-kit-spec-review/ai-kit-spec.py detect-current-runtime ..."` (codex-cli 0.162.1, `tmp/16.1-24-codex-evidence.txt`). The raw tool output is in the log: `/bin/bash -lc 'python3 skills/ai-kit-spec-review/ai-kit-spec.py detect-current-runtime' ... succeeded in 0ms: {"native_runtime": "codex"}`, exit 0. The log does not show which codex variable was set. `CODEX_THREAD_ID` is the likely one, because REQUIREMENTS.md records that `CODEX_VERSION` is absent from the codex 0.153.4 binary. That is an inference.
- `pi -p --no-session --model router-env/my-coding --tools bash "Run ... detect-current-runtime ..."` (`tmp/16.1-24-pi-evidence.txt`): `{"native_runtime": "pi"}`, exit 0. The log holds only the model's relayed answer, not the raw tool output, so this evidence is weaker than the codex log.

This proves that both host CLIs export their detection signal into tool subprocesses in non-interactive mode. Whether the interactive codex and pi sessions do the same is still unproven. That check is a Deferred Item owned by Phases 20 (codex) and 22 (pi), per RUN-10. The `detect_current_runtime` docstring still labels these signals honestly and does not claim them as live-verified, which matches the evidence.

## Config fingerprint guard (16.1-24 T-16.1-47)

The guard **failed** on one file. `~/.cursor/cli-config.json` changed from `6828b001...` to `8b2e3a00...` during the live checks; I re-hashed it and got `8b2e3a00...`. Its mtime is 2026-10-15 00:55:29 -0300, which falls inside the first `detect-runtimes` call (the catalog fetch sidecar is stamped 00:55:34). That call runs `cursor-agent models`. The other five fingerprinted files (`~/.claude/settings.json`, `~/.config/opencode/opencode.jsonc`, `~/.codex/config.toml`, `~/.gsd/defaults.json`, `~/.pi/agent/settings.json`) are unchanged.

The orchestrator attributes the change to cursor-agent refreshing its own caches when ai-kit invokes it. **This is an inference, not a proof.** A later manual `cursor-agent models` call did not change the hash again. What I could verify: ai-kit has no write path to that file. The only `ai_kit_spec` writes are `cache_write_json` (to cache, trust and quota paths), `config_io.py:299` (review-spec.toml, not called by detect/fetch) and the dispatch prompt and stdout files. `detect_cursor_agent_models` runs `[binary, "models"]` and only reads stdout. Its docstring now records the behavior (ac21585).

**Effect on Phase 16 must-haves: none.** No Phase 16 truth or prohibition is about the invoked third-party CLIs leaving their own state untouched. The Phase 16 prohibitions cover shell/alias invocation, never executing claude, never writing an unsourced `image_input: false`, and confidence labels, and all of them hold. The prior report already noted that the detection commands run real CLIs that "may touch their own state dirs". The guard belongs to plan 16.1-24's HARD-05 prohibition ("MUST NOT write to any config outside ai-kit's own cache"). Whether a third-party CLI rewriting its own config while ai-kit calls it violates that prohibition is a Phase 16.1 decision (RUN-32), not a Phase 16 one. My own checks touched no file under `~/.claude`, `~/.cursor`, `~/.config/opencode`, `~/.codex`, `~/.pi` or `~/.gsd`. I ran `opencode models --verbose` once, and a before/after hash of `~/.config/opencode/*` shows no change. I did not run `cursor-agent`.

## Behavioral Spot-Checks (run by me)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Host precedence via the real CLI | `ai-kit-spec.py detect-current-runtime` under 9 env combinations | all as expected (truth 1) | PASS |
| Convergence, no loop | `detect-runtimes --if-stale` + `fetch-model-catalog --if-stale` on a scratch copy of the refreshed cache, `PATH=/nonexistent` | `{}` exit 0; `fetch_skipped: true`, 195 entries, 0 rejections | PASS |
| Real cache shape | read `runtimes.json` / `model-catalog.json` | `schema_version` 2; `_meta.schema_version` 2; 195 entries all validate; claude current against the catalog | PASS |
| Legacy entries load | the 195 entries with the new fields removed, through `validate_catalog_entry` | 0 errors | PASS |
| Ranker purposes and aliases | `score_candidates` for 5 purposes + `execute`; legacy `[review]/[execute]` TOML | all rank; `execute == execution`; legacy file loads | PASS |
| opencode `--verbose` source | `opencode models --verbose` (opencode v2.0.29) | exit 1 `Unrecognized flag: --verbose`; parser returns `{}` | DEGRADES AS CONTRACTED (Warning) |

### Test Runs (executed by me)

| Command | Result |
|---------|--------|
| The 21 named classes from 16-VALIDATION.md (`TestDetectCurrentRuntime` ... `TestCatalogSchemaVersion`) | 192 tests, OK |
| `python3 -m unittest tests.test_ai_kit_spec tests.test_ai_kit_spec_env_scrub tests.test_ai_kit_spec_trust tests.test_ai_kit_spec_gsd_tools tests.test_ai_kit_spec_gsd tests.test_ai_kit_spec_superpowers tests.test_ai_kit_gsd_curated_config` | 938 tests, OK |
| `python3 -m unittest tests.test_ai_kit_opencode_providers tests.test_ai_kit_usage_metrics` (the `_meta` sibling readers) | 235 tests, OK |
| `make arch-test` | 24 tests, OK |
| `make ruff` (pre-commit hook) | Passed |

I did not run `make test-integration`, `make e2e-test`, or the pylint, pyright, vulture and shellcheck hooks. The 16.1 plan gates own those.

### Probe Execution

Step 7c: SKIPPED. No Phase 16 PLAN or SUMMARY declares a `probe-*.sh`, and the repo has no `scripts/*/tests/probe-*.sh`.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| SPEC-01 | 16-02 | pi and codex host detection, precedence pi > opencode > cursor > codex > claude | SATISFIED | Truth 1, plus the non-interactive real-host evidence. The interactive check is deferred to Phases 20 and 22. |
| SPEC-02 | 16-01, 16-03, 16-04 | codex and claude enumeration through real binaries, fixture-validated parsers | SATISFIED | Truth 2, live |
| SPEC-03 | 16-01, 16-03, 16-05 | optional `image_input`, populated `reasoning_modes`, old caches load | SATISFIED | Truth 3. The opencode source is inactive on opencode v2 (Warning). |
| SPEC-04 | 16-06 | five ranker purposes, `review`/`execute` aliases | SATISFIED | Truth 4 |

No requirement is orphaned. The Phase 16 rows in REQUIREMENTS.md are exactly SPEC-01..04. SPEC-05 (pi enumeration, Phase 18) and SPEC-06 (cursor wrapper, Phase 21) were split out by D-06. REQUIREMENTS.md still shows SPEC-01..04 as `Pending`. Plan 16.1-24 Task 3 flips them through gsd-tools.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| phase source, TOML, skill docs | - | `TBD`/`FIXME`/`XXX` | none found | clean |
| `ai_kit_spec/*.py` | - | `shell=True` / `bash -i` | none found | clean |
| `detection.py:326` `detect_opencode_image_input` (live host) | - | external CLI drift: opencode v2.0.29 removed `models --verbose` | Warning | The second `image_input` source never contributes on this host. Opencode-only ids that models.dev does not cover (for example `router-env/my-coding`, `router-env/my-plan-review`) stay without `image_input`. Absent means unknown, and Phase 17 treats that as not vision-eligible (17-CONTEXT.md:34), so no wrong data is written. No later phase owns adapting to opencode v2; it needs a backlog entry. |

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | `detect-current-runtime` from an **interactive** codex session prints codex (`CODEX_THREAD_ID` exported to tool subprocesses) | Phase 20 | Phase 20 goal: "confirmed working from real codex and opencode host sessions" (EVAL-04, 20 D-05); RUN-10 |
| 2 | `detect-current-runtime` from an **interactive** pi session prints pi (`PI_CODING_AGENT` exported to tool subprocesses) | Phase 22 | Phase 22 goal: "confirmed working from a real pi host session; pi's 'not live-validated' label is lifted"; RUN-10 |
| 3 | pi model enumeration (the fifth host in the phase goal) | Phase 18 | SPEC-05, split out of SPEC-02 by Phase 16 D-06 |

### Human Verification Required

None. The single item from the previous report is now covered by non-interactive real-host evidence, and its interactive remainder is deferred to Phases 20 and 22 (RUN-10).

### Gaps Summary

No gaps. All four ROADMAP success criteria hold on the current, refactored code. The evidence is 1,197 tests I ran myself, direct CLI runs, the 16.1-24 live checks against the real ai-kit cache from this checkout's entry point (proven by the `ai_kit_spec.__file__` line), and non-interactive `codex exec` / `pi -p` runs.

Two things need attention. Neither one fails a Phase 16 must-have:

1. **Fingerprint guard:** `~/.cursor/cli-config.json` changed while ai-kit was invoking `cursor-agent models`. Attributing that to cursor-agent is an inference. ai-kit has no write path to the file. This is decided under 16.1 RUN-32 / HARD-05, not here.
2. **opencode v2 drift:** opencode v2.0.29 no longer accepts `models --verbose`, so the 16-05 opencode `image_input` source is inactive on this machine. The code degrades exactly as contracted. Recommend a backlog item to find opencode v2's capability source or retire this path.

---

_Verified: 2026-10-15_
_Verifier: Claude (gsd-verifier)_
