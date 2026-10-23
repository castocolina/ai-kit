# Phase 17: Curated-Config Inventory & Recommendation Engine - Pattern Map

**Mapped:** 2026-10-15
**Files analyzed:** 19 (10 skill modules, 3 ai_kit_spec edits, 1 doc edit, 3 tests, 1 fixture dir, plus cli.py)
**Analogs found:** 17 / 19

The base path `SK=skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config` is used below.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `SK/cli.py` (add `inventory`, `recommend`) | controller | request-response | `SK/cli.py` itself (`_COMMAND_HANDLERS`, `_cmd_detect_frontend`) | exact |
| `SK/host.py` (NEW) | utility | request-response (env/fs probe) | `SK/gsd_catalog.py` `resolve_gsd_tools_path`, `cli._resolve_node_and_gsd_tools` | exact |
| `SK/gsd_catalog.py` (EXTEND `query_gsd_tables`) | service | subprocess (node -e) | `SK/gsd_catalog.py` `query_agent_catalog` | exact |
| `SK/catalog_adapter.py` (NEW) | service | subprocess to ai_kit_spec CLI | `SK/model_detect.py` | exact |
| `SK/project_facts.py` (NEW) | utility | file-I/O (read-only) | `SK/frontend_detect.py`, `SK/claude_md_detect.py` | exact |
| `SK/inventory.py` (NEW) | service | orchestration/transform | `cli._heavy_sweep_result` / `cli._cmd_apply_execution` | role-match |
| `SK/roles.py` (NEW) | model (data + pure) | transform | `SK/critical_agents.py`, `SK/workflow_defaults.py` | role-match |
| `SK/presets.py` (NEW, data only) | config/data | none | `SK/workflow_defaults.py` | exact |
| `SK/recommend.py` (NEW, pure) | service | transform | `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py` `score_candidates` | role-match |
| `SK/plan_io.py` (NEW) | utility | file-I/O (atomic write) | `skills/ai-kit-spec-review/ai_kit_spec/cache.py` `cache_write_text` | exact |
| `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py` (EDIT `score_exact`) | service | transform | itself, `_score_one_entry` | exact |
| `skills/ai-kit-spec-review/ai_kit_spec/detection.py` (EDIT D-24, schema 2->3) | service | subprocess/HTTP | itself, `detect_opencode_image_input` | exact |
| `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py` | — | — | no change expected (RESEARCH Pattern 6) | n/a |
| `skills/ai-kit-spec-config/references/cli-model-selection.md` (EDIT ~line 159) | doc | — | itself | exact |
| `tests/test_curated_config_inventory.py` (NEW) | test | — | `tests/test_ai_kit_gsd_curated_config.py` | exact |
| `tests/test_curated_config_recommend.py` (NEW) | test | — | `tests/test_ai_kit_gsd_curated_config.py` | exact |
| `tests/test_curated_config_golden.py` (NEW) | test | golden | `tests/fixtures/golden/` (inputs.json + expected.txt) | partial |
| `tests/fixtures/curated_config_v2/` (NEW) | fixture | — | `tests/fixtures/golden/`, `tests/fixtures/opencode_models_verbose.txt` | partial |

## Pattern Assignments

### `SK/cli.py` (controller, request-response)
**Analog:** itself. Imports block `SK/cli.py:12-21` (relative `from . import ...`, alphabetical; add new modules there). Dispatch `SK/cli.py:480-505`:
```python
_COMMAND_HANDLERS = {
    "ensure-project": _cmd_ensure_project,
    ...
    "apply-workflow-defaults": _cmd_apply_workflow_defaults,
}

def main(argv: list, which_fn=shutil.which, run_fn=subprocess.run,
         env_fn=lambda: dict(os.environ)) -> int:
    args = _build_parser().parse_args(argv)
    handler = _COMMAND_HANDLERS.get(args.command)
    ...
    return handler(args, which_fn, run_fn, env_fn)
```
- Every handler signature is `(args, which_fn, run_fn, env_fn)`; add subparsers in `_build_parser()` (`SK/cli.py:432-478`).
- `--profile` choices reuse `VALID_MODEL_PROFILES` (`SK/cli.py:23`), not gsd's `VALID_PROFILES`.
- v1 handlers stay untouched (D-08 of Phase 18 / CONTEXT).
- `recommend` handler: read inventory JSON, call pure `recommend.build_plan(...)`, hand to `plan_io` for output. No `run_fn` use.

### `SK/host.py` (utility)
**Analog:** `SK/cli.py:38-63` `_resolve_node_and_gsd_tools` (returns `(value, error)` tuple, one-line error naming what is missing, never lets `None` reach `subprocess.run`) and `SK/gsd_catalog.py:38-71` (`resolve_gsd_tools_path(env, isfile_fn, start)`, `resolve_node_binary(which_fn)`). Keep DI params `env`, `isfile_fn`, `which_fn`. Consume Phase 16.1's shared `ai_kit_spec/gsd_tools.py` via `gsd_catalog.load_gsd_tools()` (`SK/gsd_catalog.py:21`), do not add another resolver copy.

### `SK/gsd_catalog.py` EXTEND: `query_gsd_tables()` (service, subprocess)
**Analog:** `SK/gsd_catalog.py:73-115`:
```python
_AGENT_CATALOG_QUERY_SCRIPT = (
    "try { const m = require(process.argv[1]); "
    "process.stdout.write(JSON.stringify({tiers: m.AGENT_DEFAULT_TIERS, "
    "phaseTypes: m.AGENT_TO_PHASE_TYPE})); } "
    "catch (e) { process.stdout.write('null'); }"
)

def query_agent_catalog(node_bin, model_catalog_path, run_fn=subprocess.run):
    try:
        result = run_fn(
            [node_bin, "-e", _AGENT_CATALOG_QUERY_SCRIPT, model_catalog_path],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    return _parse_catalog_output(result.stdout)
```
- New script body = RESEARCH Pattern 1 (argv[1] model-catalog.cjs, argv[2] config-schema.cjs, argv[3] cwd, argv[4] JSON keys). Paths and keys as argv, never interpolated.
- Add a `_parse_tables_output` validator mirroring `_parse_catalog_output` (`:81-94`): reject non-dict / missing keys -> `None`, never partial.
- Add `resolve_config_schema_cjs_path` mirroring `resolve_model_catalog_cjs_path` (`:48`).

### `SK/catalog_adapter.py` (service, subprocess to ai_kit_spec CLI)
**Analog:** `SK/model_detect.py` (lines 1-40+): locate sibling `ai-kit-spec.py` via `resolve_ai_kit_spec_path(this_skill_dir, env, isdir_fn)` and shell it with `run_fn`; reshape JSON. Call `detect-runtimes --if-stale` and `fetch-model-catalog ... --if-stale` per RESEARCH Pattern 2 state rules. Cross-skill Python import only for one proven helper (`model_ranker.score_candidates`), as `preference_match.py`/`cross_ai_build.py` already do.

### `SK/project_facts.py` (utility, read-only file-I/O)
**Analog:** `SK/frontend_detect.py:1-30`: `isfile_fn=os.path.isfile` and `read_fn` DI, never raises, malformed input degrades to "no signal". Reuse `frontend_detect.detect_frontend_present` and `claude_md_detect` rather than re-implementing.

### `SK/inventory.py` (orchestration)
**Analog:** `SK/cli.py:108-135` `_heavy_sweep_result` / `_cmd_apply_execution` `:199-257` for gathering ctx + emitting one JSON result. Inventory does all I/O (CONTEXT "Established Patterns"); carry `schema_version` like `detection.py:431` `{"schema_version": RUNTIMES_SCHEMA_VERSION, ...}`. Read-only: never call `config-set`.

### `SK/roles.py`, `SK/presets.py` (data + pure)
**Analog:** `SK/workflow_defaults.py:1-40`: module docstring stating source/date of literals and which keys are deliberately excluded (double-write guard), then a literal dict constant. `SK/critical_agents.py` for agent-list data + small pure helpers.

### `SK/recommend.py` (pure transform)
**Analog:** `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:253-280` `score_candidates`: returns shallow copies, never mutates inputs, deterministic sort. Add explicit tie-break keys (sort by `(-score_exact, id)`), since `sorted(..., key=score, reverse=True)` alone is only stable-order. No subprocess/clock/fs imports (REC-01) — enforce with a test that patches `subprocess.run`/`open` to raise.

### `SK/plan_io.py` (atomic write)
**Analog:** `skills/ai-kit-spec-review/ai_kit_spec/cache.py:28-45`:
```python
fd, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)
except BaseException:
    if os.path.exists(tmp):
        with contextlib.suppress(OSError):
            os.unlink(tmp)
    raise
```
Canonical dump: `json.dumps(obj, sort_keys=True, indent=2)`; digest via `hashlib.sha256` over the canonical inventory bytes. Prefer reusing this helper (or copy it locally, as `opencode-providers/atomic_write.py` does) rather than a third variant.

### `ai_kit_spec/model_ranker.py` EDIT (D-15)
`_score_one_entry` (`:227-251`) ends with `return {**entry, "score": round(score, 1)}`. Add `"score_exact": score` in the same dict; leave `score` unchanged for existing callers.

### `ai_kit_spec/detection.py` EDIT (D-24)
**Analog:** `detect_opencode_image_input` (`:325-341`): `run_fn` call wrapped in `try/except (OSError, subprocess.TimeoutExpired): return {}`, require `returncode == 0`, delegate to a pure `parse_*` that never raises. New `/api/model` source follows the same shape (pure parser + thin I/O wrapper). Bump `RUNTIMES_SCHEMA_VERSION = 2` (`:16`) to 3; `runtimes_schema_is_current` (`:369`) then invalidates old caches automatically.

### `references/cli-model-selection.md` EDIT
Lines ~157-160 name `opencode models --verbose` as the image source; update to the D-24 source wording.

### Tests (`tests/test_curated_config_*.py`)
**Analog:** `tests/test_ai_kit_gsd_curated_config.py:1-50`: `sys.path.insert(0, .../skills/ai-kit-gsd-curated-config)` relative to `__file__`, then `from ai_kit_gsd_curated_config import ...`; reuse/copy `make_fake_run(results)` (records `.calls`, returns `subprocess.CompletedProcess`). Temp dirs only, never real configs. Register new modules in the `test-unit` Makefile tier.

## Shared Patterns

- **DI for side effects:** `which_fn`, `run_fn`, `env_fn`, `isfile_fn`, `read_fn` defaults on every I/O function (`SK/cli.py:495-500`, `SK/gsd_catalog.py:38-59`).
- **Fail-closed parsing:** subprocess failure / bad JSON -> `None` or `{}`, never a partial result (`SK/gsd_catalog.py:81-115`, `detection.py:325-341`).
- **Structured errors:** one-line message naming the missing piece, exit 2 with searched paths (`SK/cli.py:38-63`).
- **Atomic writes:** `cache.py:28-45` pattern.
- **Stdlib only** in all runtime modules.

## No Analog Found

| File | Reason |
|---|---|
| `tests/test_curated_config_golden.py` (15 goldens via a tables builder, D-20) | Only `tests/fixtures/golden/` (inputs/expected pair for status line) exists; use RESEARCH's golden design. |
| `tests/fixtures/curated_config_v2/gsd_tables_1_16.json` | New fixture; capture from a live `query_gsd_tables` run against installed gsd-core 1.16. |

## Metadata
**Search scope:** `skills/ai-kit-gsd-curated-config/`, `skills/ai-kit-spec-review/ai_kit_spec/`, `tests/`
**Files scanned:** ~12
