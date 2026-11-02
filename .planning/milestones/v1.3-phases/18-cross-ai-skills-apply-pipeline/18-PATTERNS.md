# Phase 18: cross-ai-skills-apply-pipeline - Pattern Map

**Mapped:** 2026-10-15
**Files analyzed:** 27 new/modified
**Analogs found:** 25 / 27

Paths: `P` = `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config`, `S` = `skills/ai-kit-spec-review/ai_kit_spec`. All analogs are git-tracked source (`.planning/scripts/cross-ai.mjs` verified with `git ls-files`).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `S/detection.py` (+`parse_pi_models`, `detect_pi_models`, `clis.pi`, schema 3 to 4) | utility | request-response (CLI probe) | `detect_cursor_agent_models` (detection.py:144) + `parse_codex_debug_models` (:196) | exact |
| `S/gsd_tools.py` (strict encoder) | utility | transform | `_coerce_value` (gsd_tools.py:150) | exact |
| `S/local_secrets.py` (`secret_is_set`) | utility | file-I/O | `load_secret` (local_secrets.py:11) | exact |
| `S/cross_ai_template.py` (path resolver) | utility | file-I/O | `S/tooling_guidance.py` style, `resolve_agents_tooling_path` (detection.py:774) | role-match |
| `P/inventory.py` (review_lanes, skills, system_one_backend, key probes) | service | request-response | itself: `_probe_gsd_tables` (:133), `_assemble_inventory` (:340) | exact |
| `P/gsd_catalog.py` (lane query node script) | service | request-response | `_GSD_TABLES_QUERY_SCRIPT` (gsd_catalog.py:146) | exact |
| `P/presets.py` (new MANAGED keys) | config | transform | itself (`closed_key_set` :185, flatten :225) | exact |
| `P/skill_scan.py` | utility | file-I/O | `P/frontend_detect.py`, `P/project_facts.py` | role-match |
| `P/cross_ai.py` (pure lanes/targets) | service | transform | `P/roles.py` + `recommend._cross_ai_layer` (:744) | role-match |
| `P/skills.py` (pure affinity) | service | transform | `P/roles.py`, `recommend._slot_layer` | role-match |
| `skills/ai-kit-gsd-curated-config/skill_affinity.json` | config | static data | `tests/fixtures/curated_config_v2/model-catalog.json` (shape only) | partial |
| `P/recommend.py` (new layers, `artifacts[]`) | service | transform | `_cross_ai_layer` (:744), `make_entry` (:79) | exact |
| `P/plan_schema.py` / `P/plan_io.py` (`load_plan`, validator) | model/utility | file-I/O | `load_inventory` (plan_io.py:194), `_validate_inventory` (:48) | exact |
| `P/plan_edit.py` (plan-set/unset) | service | transform | `recommend._drop_rejected` (recommend.py:900) + `plan_io.write_plan` | role-match |
| `P/config_backup.py` | utility | file-I/O | `S/cache.py:cache_write_text` (:27) | role-match |
| `P/apply.py` | service | batch / request-response | `cli._cmd_apply_profile` and friends, `gsd_tools.config_set` (:163) | role-match |
| `P/followups.py` | service | transform | `recommend` notes + `cli._cmd_recommend` summary | partial |
| `P/cross_ai_script.py` (renderer, hash header) | utility | transform / file-I/O | `P/cross_ai_build.py` + header of `.planning/scripts/cross-ai.mjs` | role-match |
| `P/cli.py` (plan-set, plan-unset, apply, followups) | controller | request-response | `_cmd_recommend` (:458), `_COMMAND_HANDLERS` (:583) | exact |
| `skills/ai-kit-spec-review/references/cross-ai.mjs` | utility (runner template) | streaming/subprocess | `.planning/scripts/cross-ai.mjs` (read only, never edit) | exact |
| `skills/ai-kit-gsd-curated-config/SKILL.md`, README row | docs | n/a | existing SKILL.md (skill-judge loop) | exact |
| `tests/test_curated_config_{cross_ai,skills,plan_edit,apply,followups,script}.py` | test | unit | `tests/test_curated_config_recommend.py`, `_inventory.py` | exact |
| `tests/test_curated_config_apply_e2e.py` | test | e2e | `tests/test_curated_config_e2e.py` | exact |
| `tools/run_unittest_parallel.py` `E2E_MODULES` | config | n/a | itself (:53) | exact |
| `tests/test_arch.py` additions | test | AST | itself | exact |
| `tests/fixtures/curated_config_v2/*` (pi models, lanes) | fixture | n/a | `tests/fixtures/curated_config_v2/gsd_tables_1_16.json`, `tests/fixtures/codex_debug_models.json` | exact |
| golden regen | fixture | n/a | `tests/fixtures/curated_config_v2/golden`, `test_curated_config_golden.py` (`UPDATE_GOLDEN=1`) | exact |

## Pattern Assignments

### `S/detection.py` pi parser (utility, request-response)
**Analogs:** `detect_cursor_agent_models` (:144-166) for the run wrapper, `parse_codex_debug_models` (:196) for a separate pure parser + fixture.
```python
try:
    result = run_fn([binary, "models"], capture_output=True, text=True,
                     check=False, timeout=15)
except (OSError, subprocess.TimeoutExpired):
    return []
```
Split pure `parse_pi_models(stdout)` (defensive: non-dict/blank entries skipped, dedupe via `seen` set like `_parse_one_codex_debug_model` :184) from `detect_pi_models(binary, run_fn)`. Flag pi as "not live-validated" (AGENTS.md certainty rule). Never call `cursor-agent models` in tests (rewrites `~/.cursor/cli-config.json`, docstring :152). Bump `RUNTIMES_SCHEMA_VERSION` and check `runtimes_schema_is_current` (:641) and `build_runtimes_snapshot` (:687).

### `S/gsd_tools.py` strict encoder
Extend next to `_coerce_value` (:150-160): None -> `"null"`, bool -> `"true"/"false"`, list/dict -> `json.dumps`, else `str`. New strict variant should reject unsupported types (raise) instead of `str()`. Wrapper convention to copy from `config_set` (:163-188): `(bool, str)` return, never raises on subprocess failure, `except OSError as exc: return False, str(exc)`, no `--raw` (`prior_value` :190 reads `previousValue`).

### `S/local_secrets.py` `secret_is_set`
Copy `load_secret` (:11-28) logic but return only `bool` (presence-only, never return the value, never log it):
```python
if env.get(key): return env[key]
with open(secrets_env_path(env), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, _, v = line.partition("=")
```
Tests use temp HOME with synthetic secrets only.

### `P/gsd_catalog.py` lane query + `P/inventory.py`
**Analog:** `_GSD_TABLES_QUERY_SCRIPT` (gsd_catalog.py:146-155): one `node -e` script, `process.argv` paths, try/catch writing `'null'` on failure, parsed by `_parse_tables_output` (json.loads, `None` on error). Add a sibling lane script with the same null-on-failure convention (RESEARCH Pattern 3 has the JS body). `inventory._probe_gsd_tables` (inventory.py:133) and `_probe_keys` (:119) are where the extended key probes (`agent_skills.<agent>`, lane `model_key`/`effort_key`) plug in, because `recommend._drop_rejected` (recommend.py:900) raises for unprobed keys. `_assemble_inventory` (:340) gets the additive fields; keep `INVENTORY_SCHEMA_VERSION = 1` (plan_io.py:15) and extend `_validate_inventory` (plan_io.py:48) with the new optional keys using `_ill`/`_missing` helpers.

### `P/recommend.py` new layers (service, transform)
**Analog:** `_cross_ai_layer` (recommend.py:744-786). Signature `(ctx: PlanCtx, _prior_entries: list) -> tuple[list, list]` returning `(entries, notes)`; entries made only via `make_entry(ctx, key, value, source, why, **extra)` (:79); unresolved choices use `status="needs_choice", candidates=[]` (the Phase 18 slot reserved at :776-785 must now be filled, replace the "reserved for Phase 18" placeholders). Curated affinity data enters via `RecommendOpts` (:12), never read inside `recommend`. Imports allowed: only `plan_schema, presets, roles` plus new PURE `cross_ai`/`skills` (recommend.py:9). `TestPurity` (tests/test_curated_config_recommend.py:1746-1771) patches subprocess/socket/time/open and import-checks `("recommend","presets","roles","plan_schema")`: add `cross_ai` and `skills` to that tuple and keep `skill_scan` out. Reuse `roles` vendor inference and tie-breaks (RESEARCH Pattern 1) instead of re-deriving.

### `P/plan_io.py` `load_plan` + `P/plan_edit.py`
**Analog:** `load_inventory` (plan_io.py:194-209): returns `(obj | None, "one-line error; rerun ...")`, handles `OSError` (strerror) and `ValueError` separately, then a validator returning a problem string. Write back through `write_plan` (plan_io.py:244-260), which uses the shared `cache.cache_write_text` via `gsd_catalog.load_ai_kit_spec_module("cache")`, umask-derived mode, and raises `OSError` when the sibling is missing. `canonical_json` / `inventory_digest` live in pure `plan_schema.py` (26 lines); keep `PLAN_SCHEMA_VERSION` handling there. `out_path_problem` (plan_io.py:212) is the guard to reuse for plan-set/unset targets.

### `P/config_backup.py` + `P/apply.py`
**Analog for atomic writes:** `cache_write_text` (S/cache.py:27-49):
```python
fd, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")
try:
    if mode is not None: os.chmod(tmp, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(text)
    os.replace(tmp, path)
except BaseException:
    if os.path.exists(tmp):
        with contextlib.suppress(OSError): os.unlink(tmp)
    raise
```
Backup claim: mkstemp copy then `os.link(tmp, final)` (RESEARCH Pattern 4); restore: mkstemp in the config dir + `os.chmod(tmp, mode)` + `os.replace` (Pattern 5; pass `mode=` since mkstemp is 0600; cache_write_text writes text only, so bytes restore needs its own mkstemp block). Apply writes go through `gsd_tools.config_set` (never edit config.json directly), order `config-new-project --cwd` first, then `config-set --project-dir` (anti-pattern in RESEARCH). Error message style: `f"ai-kit-gsd-curated-config: {error}"` on stderr, exit 2.

### `P/cli.py` subcommand wiring (controller)
**Analog:** `_cmd_recommend` (cli.py:458-495) and the table (:583-597):
```python
def _cmd_recommend(args, which_fn, run_fn, env_fn) -> int:
    del which_fn, run_fn, env_fn
    loaded, error = plan_io.load_inventory(args.inventory)
    if loaded is None:
        print(f"ai-kit-gsd-curated-config: {error}", file=sys.stderr)
        return 2
```
Add `plan-set`, `plan-unset`, `apply`, `followups` handlers with the same `(args, which_fn, run_fn, env_fn)` signature, register in `_COMMAND_HANDLERS`, and add argparse subparsers in `_build_parser` (:~580). `_cmd_inventory` (:436) shows the `--project-dir` isdir guard and `host.InventoryDeps(which_fn, run_fn, env_fn)` injection for tests. pylint max-args 5: bundle options in NamedTuples as `recommend.RecommendOpts` / `inventory.InventoryOpts` do.

### `P/cross_ai_script.py` + `references/cross-ai.mjs`
**Analog:** `.planning/scripts/cross-ai.mjs` (479 lines, tracked; READ ONLY). Line 2 header `// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=1 sha256=<hex>` is the pristine/edited detector: the renderer substitutes the `<config>`...`</config>` JSON block (lines ~35-53, valid JSON by contract "so regeneration can diff it"), recomputes the hash, and compares to classify pristine / edited / `.new`. The template ships `sha256=UNSTAMPED`. Exit-code contract (0, N, 124, 127, 2, 128+n), stdin prompt, flags `--prefer --model-<cli> --mode --timeout --print-argv --no-preamble --self-test`, stdlib-only node. `P/cross_ai_build.py` (sibling import via `model_detect.resolve_ai_kit_spec_path`, try/except ImportError degrade-to-None, lines 21-47) is the pattern for any sibling-skill import; its `CLI_TO_REVIEWER_SLUG` (line 54) is what lane matching by `probe.binary` replaces for v2.

### Tests
**Unit:** follow `tests/test_curated_config_recommend.py` (`make_inventory(...)`, `recommend.RecommendOpts("adaptive","rigorous","y","y")`) and `_inventory.py` (`FakeRun`, `seed_cache`, `_tree_snapshot`). Each new `P` module is under the module-level `sys.path.insert` pair used in `tests/test_curated_config_e2e.py:19-24`.
**E2E:** copy `tests/test_curated_config_e2e.py` header (docstring, sys.path inserts, imports of `real_gsd_run`, `_lock_tree`; skip when node / checkout gsd-core missing) for `test_curated_config_apply_e2e.py`; register `"tests.test_curated_config_apply_e2e"` in `E2E_MODULES` (tools/run_unittest_parallel.py:53-59). `tests/test_gate_scope.py` asserts every test module is gated exactly once via the runner (also check `tools/gen_test_groups.py` output stays in sync). Regenerate golden with `UPDATE_GOLDEN=1 python3 -m unittest tests.test_curated_config_e2e -k TestGoldenTables` style (see `test_curated_config_golden.py`).
**Arch:** extend `tests/test_arch.py` (AST rules, each with a `TestArchNonVacuity` counterpart) for the new modules.

## Shared Patterns

### Error/exit convention
**Source:** `P/cli.py:458-495`. One-line `ai-kit-gsd-curated-config: <msg>` to stderr, return 2; never a traceback; `except OSError` around writes.

### Atomic writes
**Source:** `S/cache.py:27-49`, reached via `gsd_catalog.load_ai_kit_spec_module("cache")` (plan_io.py:249). Every config/plan write; AGENTS.md mandates mkstemp + os.replace.

### Purity split
`recommend` imports only pure modules; I/O helpers (`skill_scan`) imported by `inventory` only. Enforced by `TestPurity` + arch tests.

### Determinism
`plan_schema.canonical_json` (sort_keys, indent 2, trailing newline) for every emitted JSON; same inputs give byte-identical plan (REC-01).

### Certainty labeling
Reverse-engineered or unverified (pi, cursor) data flagged in notes/`why`, never at documented confidence.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `P/followups.py` | service | transform | No existing followup/next-steps emitter; compose from `recommend` notes shape |
| `skill_affinity.json` | config | static data | No curated-data JSON beside a package yet; use RESEARCH D-33 shape |

## Constraints
Never edit `.planning/scripts/cross-ai.mjs` (live supervisor). No absolute paths in source/tests. pylint max-args 5, max-locals 15, max-branches 12; ruff line-length 100.

## Metadata
**Analog search scope:** `skills/ai-kit-gsd-curated-config`, `skills/ai-kit-spec-review/ai_kit_spec`, `tests/`, `tools/`, `.planning/scripts`
**Files scanned:** ~25 read or grepped
**Pattern extraction date:** 2026-10-15
