# Phase 33: One config design - Pattern Map

**Mapped:** 2026-11-14
**Files analyzed:** 22 (new or modified)
**Analogs found:** 19 / 22 (all re-verified at HEAD; every path is git-tracked source under `skills/`, `tools/`, `tests/`)

The 2026-11-13 draft was not copied. Line numbers below are HEAD.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py` (new) | utility | transform / file-I/O | `tools/config_doctor_appliers.py` `write_toml_region_replace` (69-99) + `find_object_span` (281) | role-match |
| `skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py` (new) | service | batch / file-I/O | `tools/setup.py` `_recover_incompatible_config` (3467) + `ai_kit_spec/trust.py` | role-match |
| `ai_kit_spec/config_io.py` (mod: layered `config.toml` reader, paths, resolver copy) | service | request-response | itself (`cfg_config_base` 268, `cfg_load_toml` 309, `cfg_parse_toml_bytes` 339, `cfg_resolve` 389) | exact |
| `ai_kit_spec/trust.py` (mod: digest of command-bearing lane entries) | utility | transform | itself (`content_sha256`, `trust_key`, `is_trusted`, `record_trust`) | exact |
| `ai_kit_spec/cache.py` (mod: fsync of file and folder, 0600) | utility | file-I/O | `tools/config_doctor_appliers.py` 56-66 + 92-98 (fsync file and dir) | exact |
| `ai_kit_spec/local_secrets.py` (mod: resolver copy) | utility | request-response | `config_io.cfg_config_base` | role-match |
| `skills/jev-fast-decision/scripts/jev_review.py` `_config_dir` (mod: D-27) | utility | request-response | itself (981-985) | exact |
| `tools/common_config.py` (mod: one resolver function; `cfg_config_path` 263, `cfg_segments_dir` 498) | utility | request-response | itself (273, 506) | exact |
| `skills/ai-kit-spec-review/references/cross-ai.mjs` (mod: `readTomlSubset`, retry sources, span scanner, migration, line splicer, `aiKitConfigDir`) | service | file-I/O | itself: `readJsonObject` (3058), `aiKitConfigDir` (3075), `resolveRetry` (3210), `scopedConfigPaths` (3018), `writeCycleState` (3412) | exact |
| `cross-ai.mjs` new self-test cases | test | n/a | `classifyCases()` 2475-2510 (`{name, kind, pure}`); runtime cases at 2590 | exact |
| `tools/setup.py` `_recover_incompatible_config` (mod: temp + `os.replace` after `.bak`) | utility | file-I/O | `_atomic_write_json` (2052) | exact |
| `docs/config/design.md` (new) | doc | n/a | none in repo for this shape (see No Analog) | none |
| `tests/test_toml_splice.py` | test | transform | `tests/test_ai_kit_spec_jsonc_read.py` (fixture dict + drift/non-vacuity) | role-match |
| `tests/test_config_migrate.py` | test | file-I/O | `tests/test_ai_kit_spec_trust.py` (49-58 env) + `tests/test_ai_kit_spec_legacy_config.py` | role-match |
| `tests/test_config_layers.py` | test | request-response | `tests/test_ai_kit_spec.py` `TestResolveConfig` (280-309) | exact |
| `tests/test_config_callers.py` | test | request-response | `tests/test_ai_kit_spec_check_providers.py`, `test_ai_kit_spec_trust.py` (CLI via `cli`, patched env) | role-match |
| `tests/test_config_no_planning.py` | test | e2e | `tests/cross_ai_selftest.py` (hermetic env, `run_group`) + `tests/test_cross_ai_runner_e2e.py` | role-match |
| `tests/test_config_dir_parity.py` | test | transform | `tests/test_ai_kit_spec_jsonc_read.py` (load a tools/ module by path, compare, non-vacuous guard) | exact |
| `tests/test_config_design_record.py` | test | structural | `tests/test_arch.py` (ast, non-vacuity class) | role-match |
| cross-ai self-test shard timings | config | n/a | `tests/fixtures/cross_ai_selftest_secs.json` via `python3 tests/cross_ai_selftest.py --record-times` | exact |
| `skills/ai-kit-spec-config/SKILL.md`, README | doc | n/a | existing text, edit in place | exact |

## Pattern Assignments

### `toml_splice.py` (utility, transform)

**Analog:** `tools/config_doctor_appliers.py` (model it, never import: tools/ and skills/ layering).

**Validate-first, fsync, replace** (69-99):
```python
try:
    tomllib.loads(new_text)
except tomllib.TOMLDecodeError:
    return False
os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
dirname = os.path.dirname(path) or "."
fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(new_text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
```
Directory fsync block is at 60-66 (`os.open(dirname, os.O_RDONLY)`, `os.fsync`, `os.close`, wrapped in `except OSError: pass`).

**Span style** (`find_object_span`, 281-296): classify each char (code / string / comment) once, walk only code chars. For TOML, classify the same way (basic string, literal string, `#` comment) and find `[table]` / `[[array]]` header lines only outside strings. D-08 contract: re-parse with `tomllib`, publish only when it equals the intended dict; a changed key is rewritten on its own line.

**Test the splicer like:** `tests/test_ai_kit_spec_jsonc_read.py` (fixtures dict at 26-34, a deliberately weaker copy as a non-vacuity proof at 49-58 and 84).

### `config_migrate.py` (service, batch)

**Analog:** `tools/setup.py` `_recover_incompatible_config` (3467-3504): back up first, notice on stderr, return bool, `dry` branch prints `[dry-run]`.
```python
bak = cfg + ".bak"
if dry: ...
try:
    shutil.copyfile(cfg, bak)
    shutil.copyfile(sample, cfg)
except OSError as exc:
    print(f"warn: could not reset incompatible config ({exc})", file=sys.stderr)
    return False
```
Phase change: keep the `.bak`, then publish through temp file plus `os.replace` (`_atomic_write_json`, setup.py 2052-2072: `os.path.realpath(path)` so a symlink stays a link, mode copied from an existing target else `0o600`, `mkstemp(dir=dirname)`, unlink-then-reraise on error).

**Parse errors:** reuse `config_io.cfg_parse_toml_bytes` (339-352, `ConfigError(path, msg)`, exit 2 in CLI mains). Legacy names: `cfg_local_path` (263, `.aikit/review-spec.toml`), `cfg_global_path` (289), `cfg_trust_store_dir` (283, `review-spec-trust`). After D-10 only `config_migrate.py` names them, so these helpers move or are renamed there.

**Trust carry (D-11):** `trust.is_trusted(store_dir, real_path, raw)` for the old rule, then `trust.record_trust` for the new key.

### `config_io.py` layered reader

**Resolver rule to copy** (268-280):
```python
xdg = env.get("XDG_CONFIG_HOME", "")
if os.path.isabs(xdg):
    return os.path.join(xdg, "ai-kit")
home = env.get("HOME") or os.path.expanduser("~")
if not os.path.isabs(home):
    raise ConfigError("$HOME", "no absolute home directory to hold ai-kit's config")
return os.path.join(home, ".config", "ai-kit")
```
Already ignores empty and relative; D-27 adds `.strip()` (a whitespace-only value is unset). Loader: `cfg_load_toml` (309-326: missing file gives `{}`, other failures `ConfigError`); read bytes once and parse the same buffer (`cfg_read_bytes` 329, `cfg_parse_toml_bytes` 339) so the trust decision and the parse share bytes.

### `trust.py` digest (D-11)

Keep `trust_key` (27-31, `os.fsencode(real_path) + b"\0" + sha`) and record shape `{"path","sha256","trusted_at"}` (44-53); replace `content_sha256(raw)` input with `sha256(json.dumps(list_of_[role, entry], sort_keys=True, separators=(",", ":")))` over lane entries that have `command`. Store dir renamed to `config-trust/`. `revoke_trust` (56-70) sweeps by `path`, unchanged.

### `cache.py` `cache_write_bytes` (27-42)

Add `os.fsync(f.fileno())` after `f.write` and a directory fsync (copy 60-66 of `config_doctor_appliers.py`). New files get `0600`: callers pass `mode=0o600` (the `os.chmod(tmp, mode)` hook already exists at 33-34). Keep the `BaseException` unlink-and-reraise.

### Resolver copies (D-19, D-27)

Copies: `config_io.cfg_config_base` (268), `local_secrets.secrets_env_path` (8-9, today `HOME/.config` only, ignores XDG: needs the rule), `jev_review._config_dir` (981-985, `.strip()` already, but `os.path.expanduser(base)` on a relative value: align), `common_config.cfg_config_path` (273) and `cfg_segments_dir` (506) (`env.get("XDG_CONFIG_HOME") or ...`, whitespace not handled), and the runner's `aiKitConfigDir` (3075: `env.XDG_CONFIG_HOME || path.join(env.HOME || os.homedir(), '.config')`). The tools/ and skills/ trees must not import each other, so each copy stays and the parity test pins them.

### `cross-ai.mjs` (service, file-I/O) - edit the template only

**Atomic publish to copy** (`writeCycleState`, 3412-3425):
```js
const tmp = path.join(path.dirname(file), `.${path.basename(file)}.${process.pid}.${crypto.randomUUID()}.tmp`);
const fd = fs.openSync(tmp, 'wx', 0o600);
try { fs.writeFileSync(fd, JSON.stringify(data)); } finally { fs.closeSync(fd); }
fs.renameSync(tmp, file);
```
Add `fs.fsyncSync(fd)` before close; write beside `fs.realpathSync(target)` so a symlink stays a link.

**Source loop to extend** (`resolveRetry`, 3210-3232): per source `{label, value}`, an error logs `cross-ai: config <label> <error>; retry keys from the next source` and continues. Insert the project and user `config.toml` sources (`[runner.retry]` then the scope table) before the `CONFIG.retry` fallback. `readJsonObject` (3058-3071) returns `{obj}` or `{error}`; `readTomlSubset` returns the same shape and reuses `confinementError` (3038), `CONFIG_READ_MAX`, `readOr`. Scope paths come from `scopedConfigPaths` (3018-3027, rejects `/`, `\`, `..` in `GSD_WORKSTREAM`/`GSD_PROJECT`); D-26 scope key is the path relative to `.planning/`. The "Nothing here writes a config file" comment near 3206 must be rewritten.

**Span scanner:** port `find_object_span` (`config_doctor_appliers.py` 281-296) and `_find_top_level_key_span` (312-344, returns `(key_start, value_start, value_end)`) to JS to remove the `cross_ai_retry` block.

**Self-test case shape** (2475-2504 and 2590 for runtime): `{ name: '...', kind: 'logic'|'runtime', pure: () => null | 'reason string' }`; null means pass. A case that waits on or measures a real clock is `runtime`. After adding, run `python3 tests/cross_ai_selftest.py --record-times` and refresh the shards.

### `tools/setup.py` recovery (3467)

Replace `shutil.copyfile(sample, cfg)` with temp-file-plus-`os.replace` after the `.bak` copy. Reuse the mkstemp/realpath pattern from `_atomic_write_json` (2052-2072).

## Test modules: closest analog and setup

All tests run behind the runner's tripwire and baseline env (AGENTS.md Testing); use synthetic HOME, never real config.

- `tests/test_toml_splice.py`: `test_ai_kit_spec_jsonc_read.py`. Head: `sys.path.insert(0, os.path.join(_REPO, "skills", "ai-kit-spec-review"))` then `from ai_kit_spec import ...`; `setUpClass` makes `tempfile.mkdtemp(prefix=...)`, `tearDownClass` removes it. Include a non-vacuity case.
- `tests/test_config_migrate.py`: `test_ai_kit_spec_trust.py` setUp (49-58): `tempfile.TemporaryDirectory()`, separate `cwd`, `home`, `xdg`, `cache` dirs via `mkdtemp(dir=...)`, `mock.patch.dict(os.environ, {"HOME":..., "XDG_CONFIG_HOME":..., "XDG_CACHE_HOME":...})`. Legacy fixtures: `test_ai_kit_spec_legacy_config.py`.
- `tests/test_config_layers.py`: `test_ai_kit_spec.py` `TestResolveConfig` (280-309): two mkdtemp dirs (project, global home) with `addCleanup(shutil.rmtree, ..., ignore_errors=True)`, `env = {"HOME": global_home}`, write the user file, trust the local one via `trust.record_trust(config_io.cfg_trust_store_dir(env), os.path.realpath(...), raw)`.
- `tests/test_config_callers.py`: `test_ai_kit_spec_check_providers.py` and `test_ai_kit_spec_trust.py` (`from ai_kit_spec import cli, config_io, trust`, `redirect_stdout/stderr`).
- `tests/test_config_no_planning.py`: `tests/cross_ai_selftest.py` hermetic env (line 61) and `run_group`; assert no `.planning/` appears in the scratch repo. Needs the runner template with a one-case self-test selector; check `tests/test_cross_ai_runner_e2e.py` for the entry. E2E tier: add a commented recorded time per AGENTS.md (`E2E_RECORDED_SECS`).
- `tests/test_config_dir_parity.py`: `test_ai_kit_spec_jsonc_read.py` 20-24 pattern (`importlib.util.spec_from_file_location` to load `tools/common_config.py` and `skills/jev-fast-decision/scripts/jev_review.py`); the JS copy runs through `node -e` on the template; cases: absolute, relative, empty, whitespace, no home. Fixtures at `test_ai_kit_spec.py` 208-225 show the existing assertions to extend.
- `tests/test_config_design_record.py`: `tests/test_arch.py` style (ast parse of the path functions, no import) with a `TestArchNonVacuity` counterpart; read `docs/config/design.md`, never `.planning/`.

## Shared Patterns

### Atomic publish
Source: `ai_kit_spec/cache.py` 27-42 (Python), `cross-ai.mjs` 3412-3425 (JS). Apply to splicer, migration, trust records, runner migration.

### Fail loudly on bad config
Source: `config_io.ConfigError` (294-306), CLI mains print to stderr and exit 2. Apply to migration step 1 and the layered reader. The runner differs: it logs one notice and falls to the next source.

### Never relative to cwd
Source: `config_io.cfg_config_base` (268-280): A-WR-01, a repo must not supply the "user" layer or trust store.

### Skills/tools layering
Copies, never imports, between `tools/` and `skills/`; parity tests pin them (precedent: jsonc_read vs config_doctor_readers).

## No Analog Found

| File | Role | Reason |
|---|---|---|
| `docs/config/design.md` | doc | no existing config record; build from `tmp/auto/33-inventory.md` (D-05) |
| JS `readTomlSubset` / JS line splicer | utility | no TOML code in the runner today; use `readJsonObject` shape and D-07 refusal list |
| Python TOML table/array-of-tables splicer logic | utility | doctor's helpers handle JSON spans; the TOML header scan is new |

## Metadata

**Analog search scope:** `skills/ai-kit-spec-review`, `skills/jev-fast-decision`, `tools/`, `tests/`
**Files read or grepped:** about 15
**Extraction date:** 2026-11-14

## PATTERN MAPPING COMPLETE
