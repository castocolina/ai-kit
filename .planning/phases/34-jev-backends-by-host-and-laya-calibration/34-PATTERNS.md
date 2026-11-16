# Phase 34: jev backends by host and Laya calibration - Pattern Map

**Mapped:** 2026-11-15
**Files analyzed:** 13 new/modified (plus docs)
**Analogs found:** 13 / 13 (all analog paths verified git-tracked)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `skills/jev-fast-decision/scripts/jev_config.py` (new) | utility (reader+splicer copy) | file-I/O | `skills/ai-kit-spec-review/ai_kit_spec/config_io.py` + `toml_splice.py` | exact (AST copy) |
| `skills/jev-fast-decision/scripts/jev_learn.py` (new) | service (version, fingerprint, records, fetch) | request-response + file-I/O | `jev_review.py` `_exchange`/`_read_body`/`write_consent`/`_state_dir` | role-match |
| `skills/jev-fast-decision/scripts/jev_review.py` (mod) | client/CLI | request-response | itself (`_laya_*` adapters, `TABLE`) | exact |
| `skills/jev-fast-decision/scripts/jev_ladder.py` (mod: `child_env`, sibling load) | utility | request-response | `_load_secret_shapes` (`jev_ladder.py:61-73`) | exact |
| `skills/jev-fast-decision/scripts/eval_cases.py` (mod: record metadata) | script | batch | itself | exact |
| `tests/test_jev_config.py` (new) | test | file-I/O | `_ClientCase` (`test_jev_fast_decision.py:313`) | role-match |
| `tests/test_jev_config_parity.py` (new) | test | transform (AST compare) | `tests/test_config_dir_parity.py` | role-match |
| `tests/test_jev_learn.py`, `tests/test_jev_typesafe_models.py` (new) | test | request-response | `JevStub` + `_ClientCase` | exact |
| `tests/test_jev_fast_decision_guard.py` (new) | test | file scan | `TestDocs` (`test_jev_fast_decision.py:2334`) | role-match |
| `tests/test_jev_doc_contract.py` (new) | test | file scan | `TestDocs` | exact |
| `tests/test_secret_shapes_copy_install.py` (mod) | test | file-I/O | itself | exact |
| `Makefile`, `.pre-commit-config.yaml` (regenerated) | config | batch | `tools/gen_test_groups.py` | exact |
| loop 34 judge records/plan | planning | batch | `.planning/phases/33-one-config-design/33-12-PLAN.md` | exact |

## Pattern Assignments

### `jev_config.py` and the sibling-load wiring (utility, file-I/O)

**Analog (load):** `skills/jev-fast-decision/scripts/jev_ladder.py:61-73`
```python
def _load_secret_shapes() -> Any:
    path = Path(__file__).resolve().parent / "secret_shapes.py"
    spec = importlib.util.spec_from_file_location("jev_secret_shapes", path)
    if spec is None or spec.loader is None or not path.is_file():
        raise ImportError(f"jev-fast-decision: cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
_SECRET_SHAPES = _load_secret_shapes()
```
Copy for `jev_config` / `jev_learn` (change filename and module name). Do not `import ai_kit_spec` (cross-skill reach is arch-forbidden).

**Analog (content, copy verbatim, AST-identical):** `config_io.py:545-558` (`_table_at`, `cfg_layered_table`), closure of 9 defs: `ConfigError` (296), `cfg_config_base` (267), `cfg_global_path` (291), `cfg_local_path` (262), `cfg_load_toml` (312), `cfg_parse_toml_bytes` (342), `cfg_load_layers` (540), plus the `try: import tomllib` guard (lines 8-13).
```python
def cfg_layered_table(cwd: str, env: dict, *table_path: str) -> dict:
    project, user = cfg_load_layers(cwd, env)
    return {**_table_at(user, table_path), **_table_at(project, table_path)}
```
Splicer: `toml_splice.py` `set_table` (429) + `publish` (780), closure 42 defs; `publish` also needs `cache_write_bytes` from `ai_kit_spec/cache.py`.
Call shape: `new_text = set_table(text, ("jev",), {"laya_url": url}); publish(path, new_text)`. `config set` accepts only `laya_url`, `laya_version`, `enabled`.

### `tests/test_jev_config_parity.py` (test, AST compare)

**Analog:** `tests/test_config_dir_parity.py`: `_load_file` helper (51-56) and the table-driven check (34-48, 106-110):
```python
def _load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
```
Also add a `test_jev_config_copy` method there for `cfg_config_base` in the new copy (it lists every user-dir copy, tests 112-132), including the non-vacuity case (`test_rule_check_is_not_vacuous`, line 162). Parity itself: `ast.dump` equality of each copied def against `config_io` / `toml_splice` (no analog for AST-compare in this file; arch tests use `ast`).

### `jev_learn.py` (service; fetch seam, records)

**Atomic write analog:** `jev_review.py:1013-1027` (`write_consent`): generalize into one `_write_json_atomic(path, data)`.
```python
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".jev-consent-")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True); handle.write("\n")
    os.replace(tmp, path)
except BaseException:
    if os.path.exists(tmp): os.unlink(tmp)
    raise
```
**State dir:** `jev_review.py:1604-1609` `_state_dir()` returns `<XDG_STATE_HOME|$HOME/.local/state>/ai-kit`; records at `os.path.join(_state_dir(), "jev")`.
**HTTP:** reuse `_Deadline` (114), `_exchange(deadline, timeout, remote=True)` (208), `_read_body(stream, cap, deadline)` (1342). Catch `OSError`, `ValueError`, `http.client.HTTPException`, `UnicodeError` only (arch rule 9). No `Authorization`, plain User-Agent. No fetch inside `_selection`/`_laya_probe`/`screen()`.
**Seam rule:** `TestSeam` (`tests/test_jev_fast_decision.py:1262`): module-level functions in `jev_review.py` holding `laya`/`typesafe` must be named `_laya_*`/`_typesafe_*`; put new logic in the siblings.
**Fingerprint/key:** code in 34-RESEARCH.md "Version, fingerprint, record key" (apply Resolved Open Question 3: skip loaded/revisions when `loaded == []`).

### `tests/test_jev_learn.py`, `test_jev_typesafe_models.py`, `test_jev_config.py` (test, request-response)

**Analog:** `tests/test_jev_fast_decision.py`
`JevStub` (132-210): in-process `ThreadingHTTPServer`; its `do_GET` answers every path with `{"status":"ok"}` (168-172), so extend with a `health_body` option and `/openapi.json`:
```python
def do_GET(self):
    stub.record("GET", self.path, {}, b"")
    self.reply(stub.health, b'{"status":"ok"}')
```
`_ClientCase.setUp` (313-329): temp HOME, `XDG_*` into it, `JEV_LAYA_URL=closed_port_url()` under `mock.patch.dict(os.environ, ..., clear=True)`; helpers `point_at`, `enable`, `run_screen`, `run_main`. Import by `from tests.test_jev_fast_decision import JevStub, _ClientCase`. Pass a temp `cwd` to every config read. For the answer-path test patch `fetch_public` to raise. Tests that change: `test_probe_laya_up` (413), `test_probe_uses_get_health_and_never_posts` (480), `test_probe_laya_url_sources` (428), `test_probe_non_loopback_laya` (466), `test_probe_reports_mycreds_fallback_and_expected_sources` (~1247).

### `tests/test_jev_doc_contract.py`, `tests/test_jev_fast_decision_guard.py` (test, file scan)

**Analog:** `TestDocs` (`test_jev_fast_decision.py:2334-2378`):
```python
SKILL_MD = (Path(__file__).resolve().parents[1] / "skills" / "jev-fast-decision" / "SKILL.md")
@classmethod
def setUpClass(cls):
    cls.skill_text = cls.SKILL_MD.read_text(encoding="utf-8")
    lines = cls.skill_text.splitlines()
    closes = [i for i, line in enumerate(lines) if line == "---"]
    cls.body = "\n".join(lines[closes[1] + 1:])
def test_doc_body_words(self):
    self.assertLess(len(self.body.split()), 500)
```
Constraints: SKILL.md body is 487 words, so the new sentences go mostly in `reference.md`. Name `SKILL.md`, `reference.md`, `backends/laya.md`, `jev_config.py`, `jev_learn.py` by path in test code so the staged mapper selects them. No test reads `.planning/` (arch rule). Guard scan walks `skills/jev-fast-decision/**` (host-folder `opencode` lines allowed).

### `tests/test_secret_shapes_copy_install.py` (test, copy-install, modify)

**Analog:** itself, lines 94-106: copy a lone script, run `python -I -B` import, assert `ImportError` naming the sibling:
```python
shutil.copy2(SKILLS / "jev-fast-decision" / "scripts" / "jev_ladder.py", tmp)
...
self.assertIn("ImportError", proc.stderr); self.assertIn("secret_shapes.py", proc.stderr)
```
Add the same for `jev_config.py` / `jev_learn.py`, and a full-skill copy case via `_run_copy(["jev-fast-decision"], "jev-fast-decision/scripts", ENTRIES[...])` (ENTRIES at 37-51).

### Test-group registration (config)

**Analog:** `tools/gen_test_groups.py` (docstring lines 2-8): a new `tests/test_*.py` joins `unit` automatically; run `python3 tools/gen_test_groups.py` and commit regenerated `Makefile` and `.pre-commit-config.yaml` in the same commit (`tests/test_gate_scope.py` fails while stale).

### Loop 34 plan (planning, batch)

**Analog:** `.planning/phases/33-one-config-design/33-12-PLAN.md`: frontmatter `wave: 8` (line 5), tool interface paragraph (line 96), `Task 1` tracer (101), `Task 2` checkpoint:human-action (141), `Task 3` publish records (166), frozen-tree rule (79), substitute.py quota handling (118). Copy drivers from `tmp/judge-33/` (untracked scratch; recreate path is that plan's Task 1 step 2), replace `33` by `34`. Last plan, wave after all code plans; judged set holds only `jev-fast-decision` (plus curated-config if its SKILL.md changes).

## Shared Patterns

### Stdlib-only, atomic write, no broad except
**Source:** `jev_review.py:1013-1027`; arch rules 8, 9, 12. **Apply to:** `jev_config.py`, `jev_learn.py`.

### Env isolation in tests
**Source:** `_ClientCase.setUp` (313-329). **Apply to:** all new jev test modules.

### Knob gate
**Source:** `jev_review.py:1420` (`_send`) and `1944` (`screen`) check `GSD_PATH_JEV == "1"`; callers forcing it: `jev_ladder.py:433` (`child_env`), `tools/judge_loop.py:1746`, `tools/hooks/precompact_core.py:121`. **Apply to:** per Resolved Open Question 1, callers forward only when set.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| AST-parity assertion in `test_jev_config_parity.py` | test | transform | Only value-parity tables exist (`test_config_dir_parity.py`); AST compare is new, use `ast.dump` per def |
| `--check-updates` flag | CLI | request-response | Parser has `--probe`/`--skip-local` only (`jev_review.py:1976-1979`); follow that flag style |

## Metadata

**Analog search scope:** `skills/jev-fast-decision/`, `skills/ai-kit-spec-review/ai_kit_spec/`, `tests/`, `tools/gen_test_groups.py`, `.planning/phases/33-one-config-design/`
**Files scanned:** about 14 (targeted reads and line greps)
**Pattern extraction date:** 2026-11-15
