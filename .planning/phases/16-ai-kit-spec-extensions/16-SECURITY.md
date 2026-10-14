---
phase: "16"
slug: "ai-kit-spec-extensions"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-14"
---

# Phase 16 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| codex binary stdout -> `parse_codex_debug_models` | Output of an external, independently versioned CLI is parsed into cache data | model slugs, effort names (low) |
| `opencode models --verbose` stdout -> runtimes.json | External CLI output (~8.5k lines) whose format can change | model ids, `image_input` flags (low) |
| process environment -> `detect_current_runtime` | Inherited env vars, read only as presence booleans | host labels (low) |
| `native_runtime` value -> review-spec.toml / model-catalog.json | The detected label passes two schema validators | closed value set (low) |
| cache files on disk -> ai_kit_spec loaders | runtimes.json / model-catalog.json may be stale, truncated, hand-edited or old | cache data (low) |
| `confirm-catalog-entry --entry-json` -> model-catalog.json | A wizard-produced, user-influenced payload names the key to write | catalog entry (low) |
| models.dev payload -> `_meta.anthropic_model_ids` / `image_input` / claude entries | Third-party JSON decides recorded ids, a capability flag and limits | model metadata (medium) |
| `references/ranking-weights.toml` -> `load_ranking_weights` | Bundled data file at a fixed path | ranking weights (low) |
| catalog entry scores -> `_passes_floor` | Third-party Artificial Analysis scores decide exclusion | scores (low) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-16-01 | Spoofing | `_RUNTIME_ENV_SIGNALS` | low | accept | Informational host label only; no access decision uses it (see Accepted Risks) | closed |
| T-16-01b | Tampering | `_VALID_NATIVE_RUNTIME` | low | mitigate | Closed value set gains only `pi`; `test_unrecognized_native_runtime_value_is_rejected`, `test_render_toml_rejects_invalid_native_runtime_value` | closed |
| T-16-02 | Denial of Service | `parse_codex_debug_models` / `detect_codex_models` | medium | mitigate | Never-raise parser, `timeout=15`, `(OSError, TimeoutExpired)` guard; degrade matrix in `TestParseCodexDebugModels` | closed |
| T-16-02b | Tampering | `detect_codex_models` exit status | medium | mitigate | Non-zero exit yields `[]`; `test_nonzero_exit_with_valid_json_returns_empty`, `test_codex_nonzero_exit_omits_models_key`, `test_result_without_returncode_returns_empty` | closed |
| T-16-03 | Elevation of Privilege | `detect_codex_models` invocation | high | mitigate | argv list `[binary, "debug", "models"]`, never `shell=True` (`detection.py:216`); `test_invokes_the_resolved_real_binary_with_an_argv_list` | closed |
| T-16-04 | Information Disclosure | runtimes.json / model-catalog.json | low | mitigate | Only slug and effort names are copied; `test_instruction_payload_is_never_persisted` | closed |
| T-16-05 | Tampering | `merge_catalog_entry` / `confirm-catalog-entry` | low | mitigate | `_meta` rejected as a model id (`model_catalog.CATALOG_META_KEY`); file left byte-identical on rejection | closed |
| T-16-06 | Tampering | runtimes.json / model-catalog.json writes | low | mitigate / accept | Interrupt-safe `cache_write_json` (tmp + `os.replace`); concurrent writers unsupported (see Accepted Risks); `test_unreadable_or_non_object_cache_redetects_without_raising` | closed |
| T-16-06b | Denial of Service | `--if-stale` gating | low | mitigate | A bad or missing version only forces an extra refresh (OR composition, tests) | closed |
| T-16-07 | Repudiation | `clis.claude.models_source` / `models_as_of` | medium | mitigate | Every claude entry labels its source and date; fallback labeled `dated-fallback` | closed |
| T-16-07b | Tampering / DoS | `_meta.anthropic_model_ids` | low | mitigate | Only well-formed dict rows kept; `test_anthropic_model_ids_keeps_only_well_formed_rows`, `test_malformed_anthropic_rows_never_crash_or_get_recorded` | closed |
| T-16-07c | Denial of Service | `detect-runtimes --if-stale` freshness edge | low | mitigate | The edge forces at most one extra re-detect; agreeing snapshots skipped (tests) | closed |
| T-16-07d | Spoofing | claude candidate -> models.dev row | medium | mitigate | `anthropic` provider hint for claude only; `test_anthropic_hint_is_claude_only` | closed |
| T-16-07e | DoS / scope | same-fetch materialization | low | mitigate | Bounded by the anthropic id list; `test_narrowed_snapshot_scope_never_widens`, `test_materialization_is_lazy` | closed |
| T-16-08 | Denial of Service | `parse_opencode_verbose_image_input` | low | mitigate | Never-raise linear block parser, `timeout=15`; garbage and partial-input tests | closed |
| T-16-09 | Tampering | `image_input` values | medium | mitigate | Only an explicit bool is written; schema rejects non-bool values | closed |
| T-16-09b | Tampering | verbose header -> model attribution | medium | mitigate | Header must equal `providerID/id`; `test_parse_swapped_headers_result_is_empty`, `test_parse_mismatched_then_matching_keeps_matching`, `test_detect_nonzero_exit_with_valid_output_returns_empty` | closed |
| T-16-09c | Tampering | stale `image_input` across fetch-skipped runs | medium | mitigate | `image_input_source` provenance; `test_image_input_source_requires_a_bool_image_input`, `test_fetch_skipped_runtime_true_to_false_transition` | closed |
| T-16-10 | Tampering | `load_ranking_weights` | low | mitigate | Fixed bundled path; finite-number validation; fallback to a copy of `DEFAULT_WEIGHTS` | closed |
| T-16-11 | Denial of Service | mechanical floor | low | accept | Empty result without Artificial Analysis scores is by design (16 D-11) (see Accepted Risks) | closed |
| T-16-12 | Repudiation | phase completion claim | medium | mitigate | 16-06 Task 3 ran every tier and hook target separately; SUMMARY ends with `GATE PASSED` | closed |
| T-16-13 | Tampering | base-commit triage worktree | low | mitigate | Detached `ai-kit-p16-base.*` worktree removed in the same task; no global prune | closed |
| T-16-14 | Elevation of Privilege | claude enumeration | high | mitigate | Claude is never executed during enumeration; `test_claude_is_never_executed` | closed |
| T-16-15 | Elevation of Privilege | opencode `--verbose` invocation | high | mitigate | argv list `[binary, "models", "--verbose"]`, never `shell=True` (`detection.py:310`) | closed |
| T-16-SC | Tampering | package installs | low | accept | No plan installs a package (stdlib-only runtime) (see Accepted Risks) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-16-01 | T-16-01 | Host detection is informational; env signals get the same trust as the existing four (01.2 precedent) | plan 16-02 (cross-AI reviewed) | 2026-09-24 |
| AR-16-02 | T-16-06 | Concurrent cache writers share a fixed `.tmp` name; every caller is a sequential single-user CLI, and hardening `cache_write_json` touches every writer that shares it | plan 16-03 (cross-AI reviewed) | 2026-09-24 |
| AR-16-03 | T-16-11 | Without Artificial Analysis scores the mechanical floor is empty by design (16 D-11); Phase 17 falls back explicitly | plan 16-06 (cross-AI reviewed) | 2026-09-24 |
| AR-16-04 | T-16-SC | No package installs in any Phase 16 plan | plans 16-01..16-06 | 2026-09-24 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-14 | 25 | 25 | 0 | orchestrator (L1 grep: mitigation code and named tests checked; the named tests pass) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-14
