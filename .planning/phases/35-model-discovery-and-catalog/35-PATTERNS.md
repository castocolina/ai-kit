# Phase 35: Model discovery and catalog - Pattern Map

**Mapped:** 2026-11-19
**Files analyzed:** 40 (14 new modules or helpers, 13 new test modules, 6 fixture sets, 9 changed files)
**Analogs found:** 38 / 40 (no analog: external-module argparse registration, herdr fake's JSON answers)

All paths are git-tracked (checked with `git ls-files` for the analogs below). Base dir for modules: `skills/ai-kit-spec-review/ai_kit_spec/` (short: `AKS/`). Line numbers were verified against source on 2026-11-19; lines marked (R) come from 35-RESEARCH.md section 6 and were not re-opened.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `AKS/arena_source.py` | service (fetcher) | request-response, paged | `AKS/model_sources.py` | exact |
| `AKS/model_names.py` | utility | transform | `AKS/model_matcher.py` | role-match |
| `AKS/jev_names.py` | service (subprocess client) | request-response | `skills/ai-kit-commit-fold/scripts/fold_group.py:209-273` | exact (copy) |
| `AKS/catalog_bands.py` | utility | transform, pure | `AKS/model_matcher.py` (pure, no I/O) | role-match |
| `AKS/usability.py` | model/utility | CRUD on catalog entry | `AKS/model_catalog.py` `apply_heuristic_corrections` (R) | role-match |
| `AKS/optional_sources.py` | service | file-I/O + subprocess | `AKS/detection.py` `_probe_from` (injectable popen/urlopen) | partial |
| `AKS/models_config.py` | config | file-I/O | `AKS/config_io.py:881-949` | exact |
| `AKS/catalog_report.py` | utility | transform | `AKS/provider_check.py` (report text) (R) | role-match |
| `AKS/catalog_cmds.py` | controller (CLI) | request-response | `AKS/cli.py` `_register_*` + `_COMMANDS` | partial (no external-module precedent) |
| `tests/herdr_fakes.py` | test helper | event-driven fake | `tests/index_fakes.py` + `tests/host_fakes.py` | exact |
| `tests/test_catalog_listing.py`, `_usability`, `_optional_sources`, `_names`, `_bands`, `_arena`, `_context`, `_attribution`, `_stale` | test | scratch HOME + fake host | `tests/test_ai_kit_spec_check_providers.py` | exact |
| `tests/test_opencode_help_flags.py` | test | file-I/O | `tests/test_cross_ai_skill_text.py` (reads template + skill text) | role-match |
| `tests/test_models_config.py`, `tests/test_catalog_schema4.py` | test | file-I/O | `tests/test_ai_kit_spec_check_providers.py` `_Scratch` | role-match |
| `tests/test_arch_hardcoded_models.py` | test (arch) | scan + baseline | `tests/test_arch.py` `check_*` + `TestArchNonVacuity` + `_CROSS_SKILL_FROZEN` | exact |
| `tests/test_spec_config_catalog_text.py` | test (doc contract) | file-I/O | `tests/test_cross_ai_skill_text.py` | exact |
| `tools/record_cli_help.py` | utility (maintainer cmd) | file-I/O + subprocess | `tools/gen_test_groups.py` (small maintainer tool, atomic write) | role-match |
| `tests/fixtures/cli_help/opencode/*`, `meta.json` | fixture | static | `tests/fixtures/opencode_api_model.json` | role-match |
| `tests/fixtures/no_hardcoded_models_baseline.json` | fixture | static | `_CROSS_SKILL_FROZEN` (shape of "only shrinks") | role-match |
| MODIFY `AKS/detection.py`, `catalog_build.py`, `model_catalog.py`, `model_matcher.py`, `cli.py` | - | - | self | - |
| MODIFY `cli-profiles/opencode.md`, `cross-ai.mjs`, spec-config `SKILL.md` + `references/cli-model-selection.md`, `docs/config/design.md:52` | docs/config | - | self | - |
| MODIFY `tools/run_unittest_parallel.py:92`, then run `tools/gen_test_groups.py` | config | - | self | - |

## Pattern Assignments

### `AKS/arena_source.py` (service, paged request-response)

**Analog:** `AKS/model_sources.py`

**Contract** (`model_sources.py:1-8`): returns `(data, ok)`, never raises; network only behind injectable `fetch_fn`.

**Core pattern** (`model_sources.py:23-38`):
```python
def _http_get_json(url: str, headers: dict) -> dict:
    merged_headers = {"User-Agent": _USER_AGENT, **headers}
    req = urllib.request.Request(url, headers=merged_headers)
    with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_models_dev(fetch_fn=None) -> tuple:
    fetch_fn = fetch_fn or _http_get_json
    try:
        return fetch_fn(MODELS_DEV_URL, {}), True
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return {}, False
```
**Pagination with partial data -> `ok=False`** (`model_sources.py:50-62`): loop `while True`, `except (...): return collected, False`. Copy that shape for the per-category page loop; import `_http_get_json` and `_USER_AGENT` from `model_sources` rather than redefining them. Add: retry 3x then `/rows` fallback, a page ceiling (115, R), a `progress` callable argument, categories as one module constant tuple. Pass many inputs as one NamedTuple (pylint `max-args=5`), as `catalog_build.py:22-33` does:
```python
class CatalogSources(NamedTuple):
    models_dev_data: dict
    models_dev_ok: bool
    aa_models: list
    aa_ok: bool
```
Add `arena_data: dict` and `arena_ok: bool` here (this class is also built in `cli.py:517,527`).

**Test:** inject `fetch_fn` (no network); fixture is a small synthetic `tests/fixtures/arena_rows.json`.

---

### `AKS/jev_names.py` (service, subprocess request-response)

**Analog:** `skills/ai-kit-commit-fold/scripts/fold_group.py`. Make a faithful copy of `fold_group.py:209-273`; swap `jev_item` for one `choice` item per name.

**Lookup constants to copy verbatim** (`fold_group.py:26-35`):
```python
JEV_ENTRY_REL = os.path.join("jev-fast-decision", "scripts", "jev_review.py")
SKILLS_ROOTS = (
    ("CLAUDE_CONFIG_DIR", ".claude", "skills"),
    (None, ".agents", "skills"),
    ("XDG_CONFIG_HOME", ".config", "opencode/skills"),
    ("CURSOR_CONFIG_DIR", ".cursor", "skills"),
    ("PI_CODING_AGENT_DIR", ".pi/agent", "skills"),
)
```
**Own-root difference:** fold's `_own_skills_root()` (`:220-222`) is three dirnames up from `scripts/`. From `AKS/jev_names.py` the own skills root is `dirname` x4 of `__file__` (module, `ai_kit_spec`, `ai-kit-spec-review`, `skills`). Verify with a test that `find_jev` finds the repo's own `skills/jev-fast-decision`.

**ask_jev** (`fold_group.py:250-273`): copy as is (returns `(choice, "")`, `(None, "old"|"timeout"|"no answer")`). Item shape (`fold_group.py:240-247`): `{"id", "type": "choice", "instructions", "context", "criteria": {id: title}}`; context holds the host name and at most five candidate names, never configuration.

**ARCH TRAP (required in the same task):** add `"skills/ai-kit-spec-review/ai_kit_spec/jev_names.py"` to `LOOKUP_COPIES` (`tests/test_arch.py:1688-1697`); the `JEV_ENTRY_REL` assignment is exempt from `check_cross_skill_refs` (clean-form test `tests/test_arch.py:3271`). Run `python3 tools/run_unittest_parallel.py tests.test_arch` right after creating the file. Do NOT add anything to `_CROSS_SKILL_FROZEN` (it only shrinks, `:1632-1668`).

**Fake for tests** (`tests/test_ai_kit_commit_fold.py:102-110`): import `write_fake_jev(skills_root, table, log_path)`; its table key is a substring of the item's context, value the answered choice. The absent case is simply an empty scratch skills root (`_no_jev`, `:759-760`); the old-client case copies `_old_jev` (`:771-774`, `OLD_CLIENT` text). Pass a scratch `env` with a scratch `HOME`; never the real one.

---

### `AKS/model_names.py` and `AKS/catalog_bands.py` (utility, pure transform)

**Analog:** `AKS/model_matcher.py` (R 6.4): `_NON_ALNUM` (:15), `_FUZZY_THRESHOLD = 0.82` (:20), `_FUZZY_MARGIN = 0.05` (:21), `_normalize` (:24-27), `bare_model_part` (:30-33), `_EFFORT_TOKENS` (:55), `_strip_known_effort_suffix` (:63-93), `match_models_dev` (:96-142). Reuse by import (`from ai_kit_spec.model_matcher import _normalize, bare_model_part`), as `catalog_build.py:14-19` already imports private names. Ambiguity returns `None` there; the names module adds a variant returning the candidate list. `catalog_bands.py` has no I/O: `quartile_cuts`, `tier`, `cost_band`, `klass` exactly as the 35-RESEARCH 2.2 snippet (lines 152-181), `>=` so an edge goes to the higher band.

Module shape: first-line docstring, then stdlib imports, `typing.NamedTuple` for bundled args (see `catalog_build.py:1-4`); no banner blocks (banners are a status-line-role convention, `AGENTS.md` Architecture). Keep each function under `max-branches=12`, `max-returns=6` (`klass` has 7 returns in the research snippet: use a dict-driven table or split into two functions).

---

### `AKS/models_config.py` (config, file-I/O)

**Analog:** `AKS/config_io.py`

**Reader** (`config_io.py:554-558`; use as is):
```python
def cfg_layered_table(cwd: str, env: dict, *table_path: str) -> dict:
    project, user = cfg_load_layers(cwd, env)
    return {**_table_at(user, table_path), **_table_at(project, table_path)}
```
Call `config_io.cfg_layered_table(cwd, env, "models")`; defaults, source-name validation and a named `ConfigError` go in the new module (`ConfigError(where, msg)` as used at `config_io.py:934`).

**Writer** (`config_io.py:941-949`; copy the shape):
```python
def cfg_write_toml(path: str, config: dict) -> None:
    existing = ""
    if os.path.exists(path):
        raw = cfg_read_bytes(path)
        cfg_parse_toml_bytes(raw, path)
        existing = raw.decode("utf-8")
    toml_splice.publish(path, cfg_render_lanes(config, existing))
```
Splice calls (`config_io.py:885,890,893`): `toml_splice.set_table(text, ("models",), {...})`, `set_table(text, ("models","cache_days"), {...})`, `set_array(text, ("models","context"), entries)`. Never write the AA key here; read it with `load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY")` (`cli.py:518`).

---

### `AKS/usability.py` (model, per-(runtime, model) record)

**Analog:** `model_catalog.merge_catalog_entry` (`:223-255`) and `apply_heuristic_corrections` (`:271-305`, R). Records are written only through the validated merge.

**Merge fix to do FIRST (pitfall 2, `model_catalog.py:239-240`):**
```python
merged = {**existing, **entry}
merged["runtimes"] = {**existing.get("runtimes", {}), **entry.get("runtimes", {})}
```
Replace the second line by a per-runtime deep merge: for each id, `{**existing_rt.get(id, {}), **entry_rt[id]}`, keeping the explicit-`None`-clears rule of `:249`. Test: usability and `last_seen` survive a refresh that passes only `{model_id, ctx_window}`.

**Error line** recipe (R 6.11, `secret_shapes.py:99` `redact(text, marker)`): first line, `re.sub(r"[\x00-\x1f\x7f-\x9f]", "", s)`, `redact(line, "[redacted]")`, cap 200. Import: `from ai_kit_spec import secret_shapes`.

---

### `AKS/optional_sources.py` (service, file-I/O + subprocess)

**Analog:** `detection._probe_from` (`detection.py:889-915`): every side effect enters as an injectable (`popen_fn`, `urlopen_fn`); `finally` always stops the child. Follow that: `run_fn` and `env` are parameters; `HERDR_ENV=1` plus the CLI on PATH gate the herdr path; absent means a labeled skip, never an error. Web path: Python validates an agent-written JSON file (`{runtime, query, url, date, names[]}`), filters names by an id regex, drops control characters.

---

### `AKS/catalog_cmds.py` (controller, argparse registration) - NO EXISTING EXTERNAL-MODULE ANALOG

`cli.py` is the only place parsers live (`rg` found no `register` function outside it). Use the in-file shape and add the first external one.

**Registration shape** (`cli.py:144-146, 393-402`):
```python
def _register_cache_detect_parsers(sub: argparse._SubParsersAction) -> None:
    p_cache_path = sub.add_parser("cache-path")
    p_cache_path.add_argument("--kind", choices=["runtimes", "quota", "catalog"], required=True)
```
**Wiring points** (`cli.py:406-413`, `1066-1090`): in `_build_parser` add `catalog_cmds.register_parsers(sub)` after `_register_dispatch_parsers(sub)` (:412); in `_COMMANDS` add `**catalog_cmds.COMMANDS,` or one line per command. Handler signature is `(args: argparse.Namespace, deps: CliDeps) -> int` and prints JSON (`_cmd_check_reviewer`, `cli.py:1058-1065`). Import `CliDeps` lazily or pass what is needed to avoid a cycle (`cli.py` imports `catalog_cmds`): handlers take `deps` as a duck-typed argument and `catalog_cmds` never imports `cli`.

**Existing confirm commands to model `confirm-model` on:** `confirm-catalog-entry` (`cli.py:213-217`, handler :651-673) and `apply-heuristic-correction` (`:219-225`, :675-695).

---

### `AKS/cli.py` changes (exact spots)

- `_fetch_catalog_external_sources` (`cli.py:507-530`): replace the single `fetch-meta` `last_fetched` (`:510-513, 523`) with per-source ages (`{"sources": {...}}`; read the old shape as "all sources at `last_fetched`"). Add Arena after `:520`. Move the schema upgrade out of the network branch (`:524-525`, pitfall 4).
- `_cmd_check_reviewer` (`cli.py:1058-1065`) and parser (`:393-402`): add `--catalog-path`; after `probe_reviewer_quota` (`quota.py:267-282`) record `{state, at, via, error}` via the validated merge; a native entry (`quota.py:274-275`) maps to `unverified`, never `verified`.
- `_write_fetch_catalog_result` (R :552-563): add `arena_ok`, skip reasons, attribution lines.

### `AKS/detection.py` changes

- `RUNTIMES_SCHEMA_VERSION = 7` (`:40`, bump comment block `:31-39`).
- `parse_opencode_api_models` (`:709-737`): keep; add a sibling records parser. Reuse its strict-shape guard style (`isinstance` checks, skip never guess, never raises). `variants` is a list of `{id, settings}` (R 1.1).
- `_probe_from` (`:903-912`): replace the single `urlopen_fn` call with the 503 retry loop (R code example lines 539-548). The `except (OSError, ..., urllib.error.URLError, ...)` tuple at `:910-912` stays.
- Comment cites of 2.0.31 / 2.0.29 at `:57, :261, :692`; `build_runtimes_snapshot` (`:1054-1100`, R) adds `listed_from`.
- `model_catalog.py`: `CATALOG_SCHEMA_VERSION = 3` (`:17`) to 4; `_FIELD_TYPES` (:26-44, R); schema-3 test list in 35-RESEARCH section 7.
- `catalog_build.py`: `_FIRST_PARTY_PROVIDER_BY_CLI` (`:290`), `_preserved_or_fresh_ctx_window` (`:155`, the only ctx writer), `_process_catalog_candidate` (`:660`, add the router-env first branch). Keep `ctx_window` an int (`model_ranker._max_context_window`).

### `cross-ai.mjs`, `opencode.md`, docs (rewrite targets)

- `cross-ai.mjs:1355-1359` comment ("opencode 2.0.29 ... listModels has no such flag"): wrong on 2.3.2; `:1363-1364` argv formulas stay; `:1367` "the listing has no variants" false now. Add `model-example:` marker to example names. The project's own runner copy is a pristine render: re-render, then `make check-dogfood`.
- `cli-profiles/opencode.md`: `last_verified: 2026-08-28` (:7), `source:` (:8-10), ids in prose (:17-22), "opencode 2.0.29 `run --help`" (:24), formula block (:26-29) lacks `--standalone`, "the listing has no variants" (:33).
- `docs/config/design.md:52`: "`[models]`: ... Phase 35. Not read in Phase 33." Update; document the stable keys (R pitfall 11).

---

### `tests/herdr_fakes.py` (test helper, stateful fake)

**Analogs:** `tests/index_fakes.py` (stateful, JSON state file, per-call log) and `tests/host_fakes.py:32-42`.

**Log + exact-argv answer pattern** (`host_fakes.py:32-42`):
```python
_FAKE = """#!{python}
import json, sys
_ANSWERS = {answers!r}
with open({log!r}, "a", encoding="utf-8") as _handle:
    _handle.write(json.dumps({{"name": {name!r}, "argv": sys.argv[1:]}}) + "\\n")
_hit = _ANSWERS.get(tuple(sys.argv[1:]))
if _hit is None:
    sys.exit(1)
sys.stdout.write(_hit[1])
sys.exit(_hit[0])
"""
```
Writer shape: `fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)` (`:64`); `host_path(bin_dir)` puts it first on PATH (`:68-70`); `fake_calls(log)` reads the log (`:73-78`). From `index_fakes.py:27-55` copy: `load_state()` from a JSON file (absent means `{}`), `record(event, rc=None)` writing `{"name","argv","cwd","event"}`. herdr needs its own writer, not `write_host_fakes`: `HOST_NAMES` derives from `RUNTIMES` binaries (`host_fakes.py:21-23`) and has no herdr. First docstring paragraph states "helper only, not a test module" and the state keys (`index_fakes.py:1-18`). Tests pass `env={"HERDR_ENV": "1", "PATH": ...}` explicitly.

---

### Test modules for R1-R10 (scratch HOME, fake host)

**Analog:** `tests/test_ai_kit_spec_check_providers.py:1-70`

```python
_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))
from ai_kit_spec import cli, config_io, config_migrate

class _Scratch(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-p31-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.env = {
            "HOME": os.path.join(self.root, "home"),
            "XDG_CONFIG_HOME": os.path.join(self.root, "config"),
            "XDG_CACHE_HOME": os.path.join(self.root, "cache"),
            "XDG_DATA_HOME": os.path.join(self.root, "data"),
        }
```
Host listings are faked through `CliDeps` seams (`which_fn`, `run_fn`, `:67-70`), so no host CLI runs. Use a `p35-` prefix. Real-HOME rule: never `~`; the runner sets `AI_KIT_REFUSE_REAL_HOME=1`. Fixture ids use `router-env/<x>` (pi, opencode) or `placeholder-model-<n>` (bare-id hosts); not real names (it also must pass the new guard).

**Host-CLI fakes:** `write_host_fakes(bin_dir, {"opencode": {("models",): (0, "...")}})` then `host_path(bin_dir)`; assert `fake_calls(log)`.

### `tests/test_opencode_help_flags.py` (R9)

**Analog:** `tests/test_cross_ai_skill_text.py:14-27` for path constants (`REPO = pathlib.Path(__file__).resolve().parent.parent`; `TEMPLATE = REPO / "skills/ai-kit-spec-review/references/cross-ai.mjs"`). Flag regex `--[a-z][a-z0-9-]*` matched as whole tokens (so `--standalone-x` is not `--standalone`); sources: the profile, `cross-ai.mjs:1363-1364` argv formulas and the comment lines `:1355-1359`. Fixture path `tests/fixtures/cli_help/opencode/`. Non-vacuity: plant a stale flag in a copy and assert the check names it.

### `tests/test_spec_config_catalog_text.py` (R12, doc contract)

**Analog:** `tests/test_cross_ai_skill_text.py` (`SPEC_CONFIG_SKILL` constant at `:23`, `HEADINGS` list at `:41-45` pinned against the file text). Also reuse `CLI_MODEL_SELECTION_MD` / `SKILL_MD` constants from `tests/test_ai_kit_spec_check_providers.py:23-30`. Keep the existing pins green: `test_ai_kit_spec_check_providers.py`, `test_cross_ai_skill_text.py`, `test_ai_kit_spec_runtimes_table.py`; run `tests.test_skill_frontmatter` and `tests.test_skill_evals_shape`. The SKILL.md change needs the `skill-judge` loop (`AGENTS.md` Non-Negotiable Rules).

---

### `tests/test_arch_hardcoded_models.py` (arch, frozen baseline, non-vacuity)

**Analogs (all in `tests/test_arch.py`):**
- Tracked-file scan (`:2386-2397`):
```python
listed = subprocess.run(["git", "ls-files", "-z", "--", "skills", "tools"],
    cwd=_REPO_ROOT, check=True, capture_output=True).stdout.decode("utf-8").split("\0")
```
  guard with `GIT_WORK_TREE_AVAILABLE` / `GIT_WORK_TREE_SKIP` (`:2384`, defined `:2447`); copy the definitions into the new module, do not import `tests.test_arch` (loads a 3500-line module). Never read `.planning/` (skip `tests/fixtures/archived/`).
- Frozen-only-shrinks (`:1671-1680`): `cross_skill_allowlist_problems`; baseline problem function follows this shape, plus "path no longer violates" (`:2336-2337`: `sorted(keys - listed)` and `sorted(listed - keys)` assertions).
- Live test (`:2329-2337`): `hits, scanned = scan...; self.assertGreater(scanned, 0)`.
- Non-vacuity class (`:3228-3293`): one planted source per rule in a `forms` dict, `with self.subTest(form=form): self.assertIn(...)`; a `clean` dict asserts `[]`; and the grown-baseline test (`:3284-3292`):
```python
grown = dict(CROSS_SKILL_ALLOWLIST)
grown[("skills/alpha/x.py", "beta")] = "a reach added after the freeze"
self.assertNotEqual([], cross_skill_allowlist_problems(grown))
```
**Registration:** `tools/run_unittest_parallel.py:92` is `ARCH_MODULES = frozenset({"tests.test_arch"})`; add `"tests.test_arch_hardcoded_models"`, then `python3 tools/gen_test_groups.py` and commit the Makefile and `.pre-commit-config.yaml` changes (stale listing fails `tests/test_gate_scope.py:570-583`). Baseline shape: 35-RESEARCH 8.4 (lines 418-422).

### `tools/record_cli_help.py` (maintainer command)

**Analog:** `tools/gen_test_groups.py` (small tool: module docstring, `main() -> int`, `_atomic_write` at `:82`). Runs `opencode --version`, `--help`, `run --help`, `models --help`, writes the four files plus `meta.json {"version", "recorded"}`. Tests never run it (no test imports it other than possibly a pure flag-extraction helper).

---

## Shared Patterns

### Injectable seams, no network or host in tests
**Source:** `model_sources.py:1-8,30-38`; `detection.py:889` (`popen_fn`, `urlopen_fn`). Every new fetch or subprocess takes the callable as a parameter with a stdlib default.

### Atomic writes and validated merge
**Source:** `cache.py:23-24` (`cache_write_json`, no `sort_keys`; sort only in `catalog-report`), `model_catalog.py:223-255`. All catalog writes go through `merge_catalog_entry`; config writes through `toml_splice.publish`.

### Stdlib-only runtime code
`AGENTS.md`: no third-party imports in `ai_kit_spec/`. `tests/*` ruff bar is lighter.

### Pylint caps
`max-args=5`, `max-locals=15`, `max-branches=12`, `max-returns=6`, `max-statements=50` (`AGENTS.md`). Bundle args in NamedTuples (`catalog_build.py:22-33`).

### Test registration
New `tests/test_*.py` joins `unit` automatically but needs `python3 tools/gen_test_groups.py`; arch modules also go in `ARCH_MODULES`. Run one module: `python3 tools/run_unittest_parallel.py tests.test_x`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `AKS/catalog_cmds.py` registration | controller | request-response | all parsers live in `cli.py`; this is the first external registration (shape above) |
| herdr JSON answers in `tests/herdr_fakes.py` | test helper | event-driven | no stateful fake answers per-command JSON yet; extend `index_fakes.py` state-file pattern |
| `AKS/optional_sources.py` web ingestion | service | file-I/O | no agent-written-JSON ingestion exists; design from 35-RESEARCH 6.14 |

## Metadata

**Analog search scope:** `skills/ai-kit-spec-review/ai_kit_spec/`, `skills/ai-kit-commit-fold/scripts/`, `tests/` (fakes, arch, doc-contract), `tools/`
**Files read this pass:** about 18 (excerpts verified); the rest from 35-RESEARCH section 6
**Pattern extraction date:** 2026-11-19
