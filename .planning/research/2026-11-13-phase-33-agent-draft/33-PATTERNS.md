# Phase 33: One config design - Pattern Map

**Mapped:** 2026-11-13
**Files analyzed:** 22 new/modified (grouped where one analog serves several)
**Analogs found:** 21 / 22 (one partial: the JS span scanner has a Python port source only)

All analog paths below are git-tracked (checked with `git ls-files` for the main ones: `cache.py`, `trust.py`, `tools/setup.py`, `tools/config_doctor_appliers.py`, `cross-ai.mjs`, `tests/test_skill_text_history.py`, `tools/judge_loop.py`, the 32.4-07 plan). `tmp/judge-32.4/` is untracked scratch (gitignored `tmp/`) and is a copy source for drivers only, never an edit target. Root `ai_kit_spec/` means `skills/ai-kit-spec-review/ai_kit_spec/`. The dogfood copy `.planning/scripts/cross-ai.mjs` is re-rendered, never hand-edited (D-16).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `ai_kit_spec/toml_splice.py` (new) | utility | transform | `tools/setup.py` `patch_host_keys` (545-592) + `jsonc_read.py` scanner (18-91) | role-match |
| `ai_kit_spec/layered_config.py` (new) | utility | transform | `config_io.py` `_combine_layers`/`cfg_combine` (418-450) | exact |
| `ai_kit_spec/config_migrate.py` (new) | service | file-I/O, one-shot | `tools/setup.py` `create_if_absent` (2752-2783) + `trust.py` | role-match |
| `ai_kit_spec/cache.py` `cache_write_bytes` (mod) | utility | file-I/O | `tools/config_doctor_appliers.py` `write_toml_region_replace` (86-99, fsync) | exact |
| `tools/setup.py` `_recover_incompatible_config` (mod) | service | file-I/O | `setup.py` `_atomic_write_executable` (1122-1135) | exact |
| `config_io.py` `cfg_config_base` (resolver, Python skill) | utility | request-response | itself (268-280); this is the one rule | exact |
| `local_secrets.py` `secrets_env_path` (mod) | utility | request-response | `cfg_config_base` | exact |
| `jev_review.py` `_config_dir` (mod) | utility | request-response | `cfg_config_base` (copy + parity test) | role-match |
| `tools/common_config.py` `cfg_config_path`, `cfg_segments_dir` (mod) | utility | request-response | `cfg_config_base` (copy) | role-match |
| `tools/setup.py:122` (mod) | config | request-response | `cfg_config_base` (copy) | role-match |
| `cross-ai.mjs` `aiKitConfigDir` (mod) | utility | request-response | `cfg_config_base` (JS copy at 3073-3076) | role-match |
| `cross-ai.mjs` `resolveRetry` + `migrateGsdBlocks` (mod/new) | service | file-I/O | `resolveRetry` (3208-3268), `readJsonObject` (3056-3069) | exact |
| `cross-ai.mjs` JS span scanner (new) | utility | transform | `config_doctor_appliers.py` `_find_top_level_key_span` (312-350) | partial (Python source) |
| `cross-ai.mjs` atomic JSON write with fsync + GSD lock (new) | utility | file-I/O | `writeCycleState` (3410-3423) | exact |
| `cross-ai.mjs` self-test cases (new/rewritten) | test | request-response | `retry-config-project` (9033), `retry-config-read-only` (9198), `pure-retry-user-config-without-home` (5990) | exact |
| `.planning/scripts/cross-ai.mjs` (re-render) | config | batch | `ensure-runner` (no edit) | exact |
| `tests/test_config_design_record.py` (new) | test | transform | `tests/test_skill_text_history.py` | role-match |
| `tests/test_config_doc_names.py` (new) | test | transform | `tests/test_skill_text_history.py` (`shipped_markdown` 125-133, non-vacuity class 294) | exact |
| `tests/test_config_dir_parity.py` (new) | test | request-response | `tests/test_gate_scope.py` `load_tool` (53) | role-match |
| `tests/test_config_migrate.py` (new) | test | file-I/O | `tests/test_ai_kit_spec_trust.py` `TrustEnvTestCase` (48-69) | exact |
| `tests/test_atomic_publish.py` / `test_toml_splice.py` (new) | test | file-I/O | `tests/test_setup.py:6801-6823`, `:6803-6810` | exact |
| `docs/config/design.md` (new; dir absent) | docs | n/a | none tracked; follow D-04/D-05 row format | none |
| judge plan + `tmp/judge-33/` drivers | plan/script | batch | `32.4-07-PLAN.md` + `tmp/judge-32.4/*.py` | exact |

## Pattern Assignments

### `ai_kit_spec/toml_splice.py` (utility, transform)

**Analog A (structure of an in-place key rewrite):** `tools/setup.py` `patch_host_keys` 545-592. Copy: split with `splitlines(keepends=True)`, find the table by header, rewrite only changed key lines keeping the trailing comment, insert missing keys after the last rewritten key, return text unchanged when nothing changes.
```python
lines = text.splitlines(keepends=True)
headers = [i for i, line in enumerate(lines) if _header_name(line) == table]
...
nl = "\n" if lines[i].endswith("\n") else ""
lines[i] = f"{indent}{key} = {_host_key_literal(value)}{m.group('trail') or ''}{nl}"
...
lines[last_key + 1:last_key + 1] = [f"{k} = {_host_key_literal(values[k])}\n" for k in missing]
```
**Do NOT copy `_KEY_RE` (`setup.py:463-464`):** `r"^(?P<indent>\s*)#?\s*(?P<key>\w+)\s*=\s*[^#\n]*?(?P<trail>\s*#.*)?$"` mis-reads a `#` inside a quoted value (RESEARCH Q3, verified by run). Write a quote-aware scanner instead.

**Analog B (scanner style):** `ai_kit_spec/jsonc_read.py` 18-91: per-character `kinds` list built by small `_classify_in_string/_in_line/_in_block/_in_code` step functions driven by a `mode` dict; reuse that shape for TOML states (basic string, literal string, `"""`/`'''`, comment, bracket depth):
```python
def _classify_step(text, kinds, i, n, mode):
    if mode["in_string"] or mode["escaped"]:
        return _classify_in_string(text, kinds, i, mode)
    if mode["in_line"]:
        return _classify_in_line(text, kinds, i, mode)
    ...
    return _classify_in_code(text, kinds, i, n, mode)
```
**Publish gate (validate before write):** `tools/config_doctor_appliers.py:86-99`:
```python
try:
    tomllib.loads(new_text)
except tomllib.TOMLDecodeError:
    return False
...
fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    handle.write(new_text); handle.flush(); os.fsync(handle.fileno())
os.replace(tmp, path)
```
In the splicer the gate compares `tomllib.loads(result)` to the intended dict and raises `ConfigError` (publish goes through `cache_write_bytes`). Value rendering reuses `config_io._toml_value` (453-461). Add a `# shortcut:` comment for the unrefreshed `# Priority fallback order` block (RESEARCH Q3 item 10).

---

### `ai_kit_spec/layered_config.py` (utility, transform)

**Analog:** `config_io.py` `_combine_layers` 418-432 and `cfg_combine` 435-450 (merge rule, local-only exception, the user file is never read under `local-only`):
```python
local_only = bool(local) and local.get("strategy") == "local-only"
merged, policy, local_notes, global_notes, notes = _combine_layers(
    local, {} if local_only else cfg_load_toml(global_path))
```
**Gate/parse order** from `cfg_resolve` 398-415: read bytes once, parse BEFORE the trust check (malformed reported either way), then `is_trusted(cfg_trust_store_dir(env), os.path.realpath(local_path), raw)`; untrusted = layer ignored with a warning. `load_layered(name, cwd, env, *, parse, gate=None, skip_user_if=None)` generalises exactly this (`gate=None` for `config.toml`). Keep `cfg_merge_reviewers` (358-382) as the domain merge for `[[reviewers]]`.
`jev-fast-decision` gets a stdlib copy (no `ai_kit_spec` import; cross-skill reaches are frozen by `tests/test_arch.py`); the parity test feeds one case table to both.

---

### `ai_kit_spec/config_migrate.py` (service, file-I/O)

**Publish-if-absent:** `tools/setup.py` `create_if_absent` 2752-2783 (copy the mkstemp-in-target-dir, fsync, `os.link`, `FileExistsError` = another process won, `O_EXCL` fallback, `finally` unlink temp). `ai_kit_spec` cannot import `tools/`; port it (skills never import tools).
**Trust carry:** `trust.py` 34-53:
```python
def is_trusted(store_dir, real_path, raw) -> bool: ...
def record_trust(store_dir, real_path, raw) -> str:
    cache_write_json(record_path, {"path": real_path, "sha256": sha, "trusted_at": ...})
```
Key = `sha256(realpath NUL content-sha)`. Migration: `is_trusted(old store, realpath(old), raw)` then `record_trust(lanes-trust, realpath(new AFTER publish), raw)` BEFORE renaming old to `review-spec.toml.migrated` (Pitfalls 4 and 5). State machine `{old only, new only, both-equal, both-different, neither}` per RESEARCH Pattern 2. Check paths (`check-providers`, `--check-only`, `provider_check.scan_review_spec` 92-110 / `_scan_sources` 171-186) call a read-only `peek_legacy`, never `ensure_migrated`. This is the only module allowed to name `review-spec.toml` / `review-spec-trust`.

---

### `ai_kit_spec/cache.py` `cache_write_bytes` fsync (utility, file-I/O)

**Current (27-42):** mkstemp, optional chmod, write, `os.replace`, cleanup on `BaseException`. **Add** (copy from `config_doctor_appliers.py:60-66` dir-fsync and `:94-98` file fsync):
```python
with os.fdopen(fd, "wb") as f:
    f.write(data); f.flush(); os.fsync(f.fileno())
os.replace(tmp, path)
# then: dir_fd = os.open(parent, os.O_RDONLY); os.fsync(dir_fd); os.close(dir_fd)   # wrapped in try/except OSError: pass
```
Keep the existing `except BaseException` unlink-temp block unchanged.

---

### `tools/setup.py` `_recover_incompatible_config` (service, file-I/O)

**Fix line 3497** `shutil.copyfile(sample, cfg)` (non-atomic): publish via temp + `os.replace`. Nearest helper `_atomic_write_executable` (`setup.py:1122-1135`, mkstemp in the target dir, `os.replace`, mode 0o755): add a `mode` parameter (default `0o755`) rather than a second helper; keep `shutil.copyfile(cfg, bak)` (3496) for the backup. Existing tests: `tests/test_setup.py:3420-3477`; interrupted-publish test style: `tests/test_setup.py:6801-6823` (patch `setup.os.replace` with a `refuse` wrapper that raises for the temp suffix, assert target unchanged and no leftover temp names):
```python
real_replace = os.replace
def refuse(src, dst):
    if str(src).endswith(".candidate"):
        raise OSError("injected: publish failed")
    return real_replace(src, dst)
with mock.patch.object(setup.os, "replace", side_effect=refuse): ...
```

---

### Resolver copies (R9, D-17), one rule per boundary

**Rule source (Python skill):** `config_io.py:268-280` `cfg_config_base`: absolute `XDG_CONFIG_HOME` else `$HOME/.config`, relative XDG ignored, no absolute home raises `ConfigError`, then `/ai-kit`.
```python
xdg = env.get("XDG_CONFIG_HOME", "")
if os.path.isabs(xdg):
    return os.path.join(xdg, "ai-kit")
home = env.get("HOME") or os.path.expanduser("~")
```
Divergent copies to fold (exact current text):
- `local_secrets.py:9` `return os.path.join(env.get("HOME", ""), ".config", "ai-kit", "secrets.env")` (ignores XDG; the bug).
- `jev_review.py:981-985` `_config_dir` (strips, `expanduser`, `os.environ` not an env arg).
- `tools/common_config.py:273` and `:506`: `base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")` (accepts relative XDG, empty HOME): two copies; make `:506` call the same function as `:273`.
- `tools/setup.py:122` `config_base = env.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")`.
- `cross-ai.mjs:3073-3076` `aiKitConfigDir(env)`: `env.XDG_CONFIG_HOME || path.join(env.HOME || os.homedir(), '.config')` (add the `path.isAbsolute` check to match).
Parity test: `tests/test_config_dir_parity.py` loads `jev_review.py`, `tools/common_config.py`, `tools/setup.py` by path (`tests/test_gate_scope.py:53` `load_tool`) and the runner function by `node` (or a small `node -e` extract), feeds the same `(HOME, XDG)` table incl. relative XDG and empty HOME, compares results.

---

### `cross-ai.mjs` retry sources + `migrateGsdBlocks` (service, file-I/O)

**Analog:** `resolveRetry` 3208-3268. Keep the loop shape; replace the GSD scoped-file source loop (3215-3224) by: (0) `migrateGsdBlocks(cwd, env)` before sources; (1) `.aikit/cross-ai.json` read through the existing confined reader:
```js
const userRoot = aiKitConfigDir(env);
const userFile = path.join(userRoot, 'cross-ai.json');
const userRead = readJsonObject(userFile, userRoot);      // 3226-3228: confined, 1 MiB cap, regular file
if (userRead.error) { log(`cross-ai: config ${userLabel} ${userRead.error}; retry keys from the next source`); }
else if (userRead.obj && Object.hasOwn(userRead.obj, 'cross_ai_retry')) sources.push({ label: userLabel, value: userRead.obj.cross_ai_retry });
```
Project file: `readJsonObject(path.join(cwd, '.aikit', 'cross-ai.json'), path.join(cwd, '.aikit'))`; scope label from `scopedConfigPaths` (3016-3025) via `path.relative(planningRoot, dirname(cfgPath))`. Per-key first-valid selection (3249-3263) and the one `cross-ai: retry ...` log line stay unchanged. Retire the comment/invariant at 3206-3207 ("Nothing here writes a config file").
**Confinement:** reuse `confinementError(file, rootDir)` (3036-3051) for every write (Pitfall 7).
**GSD lock (RESEARCH Q1):** `wx` open of `<dirname(realpath)>/.lock` with body `{pid, cwd, acquired}`, poll 50 ms up to 2 s then skip removal; re-read under lock; temp beside realpath; rename; unlink lock in `finally`. Example in RESEARCH "Code Examples".

### `cross-ai.mjs` atomic write helper (utility, file-I/O)

**Analog:** `writeCycleState` 3410-3423. Copy and add fsync (D-08):
```js
const tmp = path.join(path.dirname(file), `.${path.basename(file)}.${process.pid}.${crypto.randomUUID()}.tmp`);
const fd = fs.openSync(tmp, 'wx', 0o600);
try { fs.writeFileSync(fd, JSON.stringify(data)); fs.fsyncSync(fd); }   // fsyncSync is the addition
finally { fs.closeSync(fd); }
fs.renameSync(tmp, file);
```
Temp lives beside the target (never `os.tmpdir()`: trips the per-case TMPDIR assertion from the `/tmp`-leak fix); remove temp in `finally` on error. Write the file as 2-space JSON plus final newline (RESEARCH Pattern 5).

### `cross-ai.mjs` JS span scanner (utility, transform)

**Analog (Python, to port):** `tools/config_doctor_appliers.py` `_find_top_level_key_span` 312-350 (depth-1 walk with `_classify`, returns `(key_start, value_start, value_end)`) + `find_object_span` 281-296 (brace depth over code-kind chars). Generalise to member `cross_ai_retry` of top-level `workflow`; JSON has no comments so the classifier needs only string-with-escape tracking (drop the `//` and `/* */` states of `jsonc_read.py:47-64`). Refuse when `workflow` appears twice at depth 1. Gate: `JSON.stringify(JSON.parse(result))` equals the original minus the key, else write nothing. No JS analog exists in the template.

---

### `cross-ai.mjs` self-test cases (test, request-response)

**Case shape** (`retry-config-project` 9033-9046): `name`, `kind: 'logic'`, `args`, `stdin`, `planningConfig`, `exit`, `status` regex, `check: (r) => ...` counting lines that start with `cross-ai: retry `. **Setup-based:** `retry-config-user` 9048-9064 (`setup: (c) =>` writes under `c.home`/`c.repo`, returns `null`). **Two runs:** `retry-config-read-only` 9198-9247 (`second: {...}`, `setup` stamps bytes + mtime into `c.retryStamp`, `check: (both) =>` uses `both.first`/`both.again`); rewrite it so run 1 changes the GSD file (block removed) and run 2 changes nothing. **Pure case:** `pure-retry-user-config-without-home` 5990-6015 (`mkdtempSync(os.tmpdir(), 'xai-...-')`, patch `os.homedir`/`log`, `fs.rmSync(root, {recursive, force})` in `finally`). **`hermeticEnv`** 4637-4653 gives `PATH`, `HOME`, `XDG_CONFIG_HOME`, git identity; fixtures go under `c.repo`/`c.home`, never `c.tmpdir`. Cases to rewrite: the 11 listed in RESEARCH Q4. No new shard module (membership computed). Refresh `tests/fixtures/cross_ai_selftest_secs.json` (`python3 tests/cross_ai_selftest.py --record-times`) and `E2E_RECORDED_SECS`.

### Dogfood re-render

No edit: `python3 skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py ensure-runner --cwd .` then `python3 tools/check_dogfood.py` (expects `check-dogfood: ok`). Template stays at `template=8`; same-version body fix is accepted for a pristine copy.

---

### Test modules

**`tests/test_config_doc_names.py` (scan + non-vacuity):** copy `tests/test_skill_text_history.py` `shipped_markdown` (125-133: every `.md` outside `evals/` and `__pycache__`), but extend to `evals/**` `.md` and `.json`, `skills/**/*.py`, `tools/**/*.py`, `README.md`; exclude `docs/prds/`, `docs/superpowers/`, `docs/config/design.md`, `ai_kit_spec/config_migrate.py`; allow a line naming both old and new (migration note). Add a `class ...NonVacuity` like `TestHistoryRulesNonVacuity` (294) with a synthetic file that must be flagged.
**`tests/test_config_design_record.py`:** parse `docs/config/design.md` rows; each inventory row carries exactly one of `moves-now`, `conforms`, `separate`, `later:<phase>`; collect live names by calling path functions with scratch `cwd`/`env` (`os.path.basename`), load `jev_review.py` by path for `consent_path`, take runner file names from the template text by exact string. Never read `.planning/`.
**`tests/test_config_migrate.py`:** copy `TrustEnvTestCase` (`test_ai_kit_spec_trust.py:48-69`: `tempfile.TemporaryDirectory`, separate `cwd`/`home`/`xdg`/`cache`, `mock.patch.dict(os.environ, {"HOME": ..., "XDG_CONFIG_HOME": ..., "XDG_CACHE_HOME": ...})`, `store = config_io.cfg_trust_store_dir(dict(os.environ))`). Header imports pattern (lines 15-19): `sys.path.insert(0, .../skills/ai-kit-spec-review)` then `from ai_kit_spec import ...`. Add a symlinked `.aikit` case (Pitfall 5) and an interrupted case (patch `os.replace`/`os.link` to raise after publish, rerun, assert trust still valid).
**`tests/test_toml_splice.py`, `tests/test_atomic_publish.py`:** pitfall list in RESEARCH Q3 item 9; interrupt style from `tests/test_setup.py:6803-6810` (above); other `os.replace` patch examples at `test_setup.py:2149`, `:2506`, `:7104-7121`.
**After adding any module:** `python3 tools/gen_test_groups.py` (`tests/test_gate_scope.py:570-583` fails on a stale listing).

---

### `docs/config/design.md` (docs)

No tracked analog: `docs/config/` does not exist. Follow D-04/D-05 and RESEARCH Q9: an inventory table with a fixed Assignment column (exactly one token per row), neutral names only, citation fixes from RESEARCH Q2 (658/690/831/853/908), the one-time `tree=dirty` note, unverified rows labelled (AGENTS.md sourcing rule). English only.

### Judge plan (loop 33)

**Plan shape:** `.planning/phases/32.4-batch-4-planning-skills-and-the-closing-report/32.4-07-PLAN.md` (3 tasks: tracer drivers, checkpoint wait for lanes, auto publish/report/check; `autonomous: false`, last wave, frozen tree until `lanes.py status` prints `all lanes ended`). **Drivers:** copy `tmp/judge-32.4/{lanes,judged,stage,publish,check,bar_table,copy_drivers,wait_lanes}.*` to `tmp/judge-33/` with `32.4` replaced by `33`. In `lanes.py` drop `NATIVE = "native:opus-xhigh"` (line 30), the `--native` arg to `pool` (381), native lane/sub-lane code (408-409, 457-473, 487-491), set `INSTANCES` (32) per D-19 (referee-one + referee-two, referee-three only as replacement via `ingest --replaces`). `judged.py`: `BASE=eabcd1a`, `EXPECTED=["ai-kit-gsd-curated-config","ai-kit-spec-config"]`, exit 1 on any other set. Closing: `python3 tools/judge_loop.py check .planning/judge` and `... --skills ai-kit-spec-config ai-kit-gsd-curated-config --require-current --gate`.

## Shared Patterns

### Atomic publish (all writers, D-08)
**Source:** `cache.py:27-42` (+fsync) for Python; `cross-ai.mjs:3410-3423` (+`fsyncSync`) for JS; temp always beside the target. Create-if-absent: `setup.py:2752-2783`.

### Trust (roster)
**Source:** `trust.py:34-53`. Rule unchanged (realpath + raw sha256); new store `lanes-trust/`; only `config_migrate.py` reads the old store.

### Confined config read
**Source:** `cross-ai.mjs:3036-3069` `confinementError` / `readJsonObject`. Apply to the project retry file, the user retry file, and the write target of the GSD block removal.

### Loud config errors
**Source:** `ConfigError` (`config_io.py:294`) for malformed or non-UTF-8 files, exit 2 in CLI mains; never a silent empty config. Apply to every new reader and the migration.

### Test isolation
**Source:** `TrustEnvTestCase` (`test_ai_kit_spec_trust.py:48-69`) and `AI_KIT_REFUSE_REAL_HOME=1`; no test reads `.planning/`; never a real config as a fixture.

### Python style
Imports in `ai_kit_spec` modules are package-absolute (`from ai_kit_spec.cache import ...`, `trust.py:18`); stdlib only; ruff line length 100; pylint limits (`max-args=5`, `max-locals=15`, `max-branches=12`).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `docs/config/design.md` | docs | n/a | `docs/config/` does not exist; use D-04/D-05 row contract |
| JS JSON-member span scanner | utility | transform | only the Python original exists (`config_doctor_appliers.py:281-350`); port it, no JS precedent |
| GSD `.lock` acquisition in JS | utility | file-I/O | protocol lives in gsd-core (`planning-workspace.cjs:384-425`, installed, not tracked ai-kit source); use RESEARCH "Code Examples" |

## Metadata

**Analog search scope:** `skills/ai-kit-spec-review/ai_kit_spec/`, `skills/ai-kit-spec-review/references/cross-ai.mjs`, `tools/`, `tests/`, `tmp/judge-32.4/`, 32.4-07 plan
**Files read:** about 14 (targeted ranges)
**Pattern extraction date:** 2026-11-13
