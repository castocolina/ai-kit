# Phase 35 code review

Reviewed: the whole phase diff `19ed975..1b6db2b` (code, tests, skills, docs; plan files as context) on 2026-11-20.
Method: every new source module read in full, the larger diffs (`cli.py`, `detection.py`, `model_catalog.py`,
`catalog_build.py`) read as diffs, a scan of all added lines for absolute paths, printed secrets, `noqa`, pylint
disables, asserts, broad excepts and `grok`, and the SPEC requirements R1 to R12 checked against the code.
Fixes ran through lane fix-ups (pi, `router-env/my-coding`, owner change of 2026-11-20) or, for one-line edits, directly.

## Findings by severity

- MEDIUM, fixed: `cache_read_json` (`ai_kit_spec/cache.py:15`) raised `UnicodeDecodeError` for non-UTF-8 bytes, so
  `fetch-model-catalog` crashed on such a catalog before its recovery could run. Now a ValueError reads as None (2d5f7d6).
- MEDIUM, fixed: `locked_catalog_update(..., replace_unreadable=True)` (`model_catalog.py`) replaced a file that
  only failed with an OSError and destroyed a corrupt file without a copy (AGENTS.md no-data-loss rule). Now an OSError
  read never replaces; a corrupt file (invalid JSON, invalid UTF-8, not an object) is saved to `<catalog>.corrupt`
  through the atomic byte writer before it is replaced; the fetch command reports the ValueError instead of a traceback (387607a).
- LOW, fixed: `catalog_report._listed_rows` crashed on a non-dict host row; `listing_state` had a branch repeating
  its default; `_extra_row` served two unrelated rows through a flag; `_optional_rows_input` had an unused parameter (72ad153).
- LOW, fixed: seven asserts that only satisfied pyright (vanish under `python -O`) replaced by `TypeGuard` and real
  checks; a non-table `[models]` now raises `ConfigError` instead of `AttributeError` (c0b66db).
- LOW, fixed: `catalog_tiers` called the private `catalog_bands._num` under a pylint disable; now public `is_num` (d89432c).
- LOW, fixed: a `grok` runtime key in a new test fixture (`tests/test_catalog_cmds.py`), against the run rule (72ad153).
- LOW, fixed: SKILL.md NEVER rule and landmine still demanded `group-models` (eb4ab23).
- INFO, kept: `optional_sources.record_names` reads and writes the optional-names store without a lock (last write
  wins, one user, atomic write). Not worth a lock; recorded as a limit.
- INFO, kept: schema 4 is stamped after every fetch run, even when every source failed (plan 35-27 wording); a failed
  source keeps `ok: false` in the sidecar, so the next `--if-stale` run refetches it.
- INFO: no secret is printed or stored (`check-reviewer` redacts detail and reason; the AA key never enters
  `config.toml`, the catalog or the raw source cache); web queries use a fixed template for a known runtime id; pane
  and web names pass `sanitize_name`; every catalog write is atomic (`cache_write_json`, `cache_write_bytes`,
  `toml_splice.publish`); no absolute path or non-router model literal was found in added source or tests.

## Review list decisions

1. Lint suppressions: fixed. arena_source docstring wrapped, `noqa` and the file-level pylint disable removed;
   `catalog_attribution.py` disable removed (ruff and pylint pass without them); `catalog_tiers` protected-access disable removed (71eacba, d89432c).
2. Narrowing asserts: fixed in `models_config.py`, `model_names.py`, `catalog_bands.py` (TypeGuard), `catalog_tiers.py`, `model_catalog.py`,
   `catalog_build.py` (one dead assert removed, one real raise), `cli._claude_seed_provider` (c0b66db). `make pyright` stays at 0 errors.
3. `test_catalog_schema4.py` walrus and pointless `assertTrue`: removed (62cbbb9).
4. Guard module: the unused local `actual` in `baseline_problems` removed (62cbbb9). The missing import preamble is not needed: the guard scans text and imports nothing from `skills/`.
5. 35-14: the Artificial Analysis matcher receiving `match_name` is correct and needed (both matchers strip the provider part with `bare_model_part`, so the resolved identity reaches AA too); kept. 35-17: `esc` only after names were found is correct (with no list boundary the pane is closed anyway and no state is worth leaving);
   records emptied when `pane close` fails is conservative (a pane that may still run copilot with permission prompts off is reported, the user re-runs); kept, pinned by `test_failed_close_reported`.
   35-15: the routing test edit is a required consequence of the new `--version` call (kept); schema 7 is now asserted stale (62cbbb9). 35-16 asserts: fixed (item 2).
6. `tools/record_cli_help.py`: a covering test was needed. `tests/test_record_cli_help.py` (six tests, fakes `which` and `subprocess.run`), generated group lists regenerated; `staged_mapper --stats` no longer lists it (212da62).
7. 35-20 notes: all three fixed (72ad153).
8. 35-21 None-valued context fact: kept. SPEC R6 requires "unknown, shown as unknown" and no guessed value: the stored fact has value None, `show()` and `context_line` print `unknown`, `ctx_window` is cleared to None through the explicit-None merge, and `_context_problem` accepts a None value on purpose. With models.dev down and no other source the cached context stays (outage rule).
   The fact's label (measured, models.dev) records that models.dev answered without a window.
9. Corrupt catalog and recovery: see the two MEDIUM findings; only a genuinely corrupt file is replaced, never a readable catalog or one with entries, and its bytes are kept. `replace_unreadable` stays keyword-only and is passed only by `fetch-model-catalog`. The seed tie-break in `catalog_facts.resolve_candidates` is correct: a bare id in the pool wins, then a seed-provider hit, else the resolver; it restores the 16 D-04 anthropic tie-break and is covered by `test_catalog_build_sources`. `catalog_cmds.Refused` is public because `cli.py` catches it from the locked update callbacks; kept.
10. 35-28 unused `entries` parameter: removed. 35-23 `optional_fetch_candidates` last-record-wins dedupe by (runtime, model_id) is a no-op safeguard: `optional_candidates` already merges names per id, so one record per name exists; kept.
11. SKILL.md line 67 (now: show the sorted, labeled `catalog-report` rows and the ranked blocks instead of a raw list), the "before grouping models" phrase and the "ungrouped" landmine fixed; `catalog.md` names the `.corrupt` backup. The `group-models` command stays in `cli.py` (tested, still a valid tool). The judged digest of `ai-kit-spec-config` is stale again by design until its next loop (eb4ab23).
12. The `<placeholder>` replace in `tests/test_spec_config_catalog_text.py` (the test lives there, not in `test_ai_kit_spec_check_providers.py`) was a no-op; removed, the angle-bracket arguments parse as plain values and the planted-command case keeps the test non-vacuous (62cbbb9).
13. Open items, recorded and not touched, see below.

## Fix commits

71eacba, 62cbbb9 (direct, trivial); c0b66db (lane A), 387607a (lane B), 212da62 (lane C, finished by the reviewer), 72ad153 (lane D), d89432c (lane E),
2d5f7d6 and eb4ab23 (direct). Lane runs: pi `router-env/my-coding`, AIKIT-XAI status=ok, exit 0, attempts 1, cycles 0, elapsed 434 s, 853 s, 247 s, 465 s and 439 s.
The probe before the first lane: status=no_change, exit 1, cli_rc 0.

## Open items (not fixed here)

- Artificial Analysis term 2.5 (model-selection products offered to third parties) is a risk for the owner to read; reported in 35-CONTEXT.md, not decided.
- The 23 deferred MEDIUM plan-review concerns stay in each plan's Review Dispositions Ledger (all 28 plans carry one).
- The foreign branch `staging/llm-env-parity-20261119T214610Z` and `stash@{0}` (on main, a stale wizard WIP) are not ours and untouched.
- Grok code stays (detection row, `build_grok_command`, `cursor-agents/grok-worker.md`, spec-config SKILL mentions); grok is not a target and this phase adds no grok content (one test fixture key removed).
- Cross-AI executor switched from my-coding-lite to my-coding on owner instruction 2026-11-20; plans 01-28 of phase 35 ran on my-coding-lite.
- The judge report (`REJUDGE.md` facts drift note) needs `judge_loop.py report .planning/judge` after the last skill change, and `ai-kit-spec-config` needs a new judge loop to refresh its digest (stale by design).
- Folded commit subjects such as `fix(35-26): 35-26` and the `Tracer:` prefixes are for the end-of-phase compaction to rewrite.
- Not fixed, low: `catalog_facts._merge_derived` and `_apply_entry` access `value.get(...)` on facts without a dict check when a cache holds a malformed fact (validated entries cannot, so only a hand-edited cache could trigger it).
