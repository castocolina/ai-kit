# Phase 28: Fast, environment-proof gates - Pattern Map

**Mapped:** 2026-11-03
**Files analyzed:** 22 new/modified
**Analogs found:** 21 / 22 (all analogs are git-tracked source; none are install mirrors)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `tools/run_unittest_parallel.py` (modify: baseline env, tripwire, `--staged`, shared-machinery set) | utility/runner | batch | itself (`run_module`, `stale_exception_names`, `EXPLICIT_GROUPS`) | exact |
| `tools/staged_mapper.py` (new, name is planner's; or inside runner) | utility | transform | `tools/gen_test_groups.py` (stdlib tool, pure functions, `_atomic_write`) | role-match |
| `.pre-commit-config.yaml` (new commit-stage hook + pre-push `check-dogfood`) | config | request-response | hooks `unittest` / `unittest-wizard` (lines 57-70) | exact |
| `Makefile` (`test-env-matrix`, `check-dogfood`, `.PHONY`) | config | batch | `arch-test`, `e2e-test` targets (lines 53-73) | exact |
| `tests/test_gate_scope.py` (extend) | test (structural) | transform | `TestGateScope` + `TestGateScopeNonVacuity` | exact |
| `tests/test_arch.py` (host-CLI AST rule + `.planning/` rule, with non-vacuity) | test (AST) | transform | `check_no_shell_true` + `test_rule8_*` + `TestArchNonVacuity` | exact |
| `tests/host_fakes.py` (new shared fake helper) | test helper | file-I/O | `tests/session_wake_fakes.py` (`_PRELUDE`, `scoped_env`), `tests/cursor_fakes.py` | role-match |
| `tests/test_staged_mapper.py` (new) | test | request-response | `tests/test_run_unittest_parallel.py`, `tests/test_gate_scope.py` | role-match |
| `tests/test_ai_kit_spec_goal_prompt_evals.py` (modify `eval_env`) | test | request-response | itself (`eval_env`, lines ~159-180) | exact |
| `tests/gsd_curated_eval.py` (read fixture, fakes) | test helper | request-response | itself | exact |
| `tests/test_precompact_core.py` (fix clock) | test | event-driven | `core._monotonic` seam (`tools/hooks/precompact_core.py:74`) | exact |
| `tests/test_markdown_to_pdf.py` + new e2e module (`TestRenderRealMmdc` moves) | test | file-I/O | `@unittest.skipUnless(shutil.which("mmdc"), ...)` (lines 75-83); e2e entries in `E2E_MODULES` | exact |
| `tests/test_worktree_e2e.py`, goal-prompt short-path test (env pinning) | test | file-I/O | existing "outside" dir at `tmp/outside` (`:59-61`) | role-match |
| `skills/ai-kit-spec-review/references/cross-ai.mjs` (load factor) | utility | request-response | its own harness sites (`runCaseProcess`, `waitFor`, `withinMs`) | exact |
| `.planning/scripts/cross-ai.mjs` (re-render, never hand-edit) | generated | transform | `TestDogfoodCopy` logic | exact |
| `tools/check_dogfood.py` (new) | utility | request-response | `TestDogfoodCopy` (`tests/test_curated_config_script.py:846-870`) + no-write guards in `tests/test_curated_config_e2e.py:130-140` | role-match |
| `tests/test_curated_config_script.py`, `_e2e.py`, `_apply_e2e.py` (temp copies) | test | file-I/O | same files | exact |
| `tests/fixtures/archived/<phase>/*` + `test_phase26_owner_captures.py`, `test_pi_live_tools.py`, `test_tool_advisor_core.py` | fixture/test | file-I/O | `tests/fixtures/curated_config_v2/golden/*` layout | role-match |
| `tests/test_cross_ai_runner_e2e.py` (self-test load cases) | test | request-response | existing self-test callers | exact |
| `tools/time_prepush.sh` (optional) | utility | batch | `tmp/p28/time_prepush.sh` (gitignored, method only) | no tracked analog |
| `AGENTS.md` Testing, `README.md` testing section, runner docstring | docs | n/a | existing Testing text | exact |

## Pattern Assignments

### `tools/run_unittest_parallel.py` (runner, batch)

**Analog:** itself. Extend, do not replace.

**Explicit set + pin pattern** (lines 41-77) for the shared-machinery set (D-03):
```python
ARCH_MODULES = frozenset({"tests.test_arch"})
...
EXPLICIT_GROUPS = {"arch": ARCH_MODULES, "unit-uv": UNIT_UV_MODULES,
                   "integration": INTEGRATION_MODULES, "e2e": E2E_MODULES}
```
Add `SHARED_MACHINERY = frozenset({...})` beside it with a commented reason; add a stale-name function modelled on this (lines 109-114):
```python
def stale_exception_names(discovered: list[str]) -> list[str]:
    found = set(discovered)
    return sorted(name for modules in EXPLICIT_GROUPS.values() for name in modules if name not in found)
```
and surface it as in `_modules_for_groups` (`return None, "error: stale exception names: " + ...`, exit 2).

**Env extension point** (`run_module`, lines 145-159): today only `os.environ.copy()` + TMPDIR/TEMP/TMP.
```python
with tempfile.TemporaryDirectory(prefix="aikit-ut-", ignore_cleanup_errors=True) as temp_dir:
    env = os.environ.copy()
    env.update({"TMPDIR": temp_dir, "TEMP": temp_dir, "TMP": temp_dir})
```
Change: drop host-signal vars and `GIT_INDEX_FILE/GIT_DIR/GIT_WORK_TREE/GIT_PREFIX/GIT_COMMON_DIR/GIT_OBJECT_DIRECTORY` (keep `GIT_EXEC_PATH`), set temp `HOME` + `AI_KIT_REFUSE_REAL_HOME=1`, write stubs into `temp_dir/trip`, prepend to PATH, set `AI_KIT_TRIPWIRE_LOG`; after `subprocess.run`, non-empty log forces rc=1 and appends calls to output. The tuple return `(module, rc, output, secs)` is consumed by `_run_all` (lines 225-237); keep it.

**Argument parsing and exit codes** (`main`, lines 200-222; `_parse_groups` 162-176): usage errors return 2 to stderr. Add `--staged FILE...` as another mode; keep `test_mixing_group_and_module_names_is_usage_error` true (`tests/test_run_unittest_parallel.py:113`). Zero staged files exit 0. Wrap staged mode in a broad `try` that falls back to full `unit`+`arch` groups.

**Worker count** reuse `worker_count`/`available_cpus` unchanged (40 percent cap).

---

### `tools/staged_mapper.py` (utility, transform)

**Analog:** `tools/gen_test_groups.py` (stdlib-only tool, pure `render` separate from I/O, argv-list subprocess, no writes). Mapper writes nothing, rebuilds the index each call. Use `subprocess.run([...], check=False)` argv lists only (never `shell=True`; `check_no_shell_true` in `tests/test_arch.py:760` is the house rule). Whole-token regex matching, sorted set output; deleted files via `git diff --cached --name-status`.

---

### `.pre-commit-config.yaml` (config)

**Analog:** `unittest` hook (lines 57-63):
```yaml
- id: unittest
  name: unittest (core)
  entry: python3 tools/run_unittest_parallel.py --group unit --group arch -- tests...
  language: system
  pass_filenames: false
  always_run: true
  stages: [pre-push]
```
New commit-stage hook: `language: system`, `entry: python3 tools/run_unittest_parallel.py --staged`, `pass_filenames: true`, `require_serial: true`, no stage line (default pre-commit), placed after `pylint` and before `unittest`. It lists no modules, so `gen_test_groups.refresh_hook_entries` (only rewrites ids in `hook_listings`) does not touch it. `check-dogfood`: pre-push, `pass_filenames: false`, `always_run: true`, no worker count.

### `Makefile` (config)

**Analog:** `arch-test` (lines 68-70) and `e2e-test` (64-67): one-line recipes through the runner, tabs, each added to `.PHONY` (line 15). `test-env-matrix` stays out of `test` and `validate`.

---

### `tests/test_gate_scope.py` (structural test)

**Analog:** itself. Extend, never bypass.

**Hook entry rule** (lines 319-334): `entries["unittest"].startswith("python3 tools/run_unittest_parallel.py --group unit --group arch -- ")`. Add an assertion that the new hook starts with `python3 tools/run_unittest_parallel.py --staged`, has no `--group`, and appears in `hook_entries`.

**Order rule** (lines 422-428):
```python
ids = hook_ids(self.hooks)
self.assertLess(ids.index("pylint"), ids.index("unittest"))
self.assertTrue(hook_require_serial(self.hooks, "pylint"))
```
Add new id between pylint and unittest, and `hook_require_serial(...)` for it. Caution: `test_hooks_cover_every_group_except_e2e` (336) uses `hook_group_names` over all entries; confirm it ignores `--staged`.

**No hardcoded workers** (345-349): already scans all hook entries and the runner, so the new hook and runner edits are covered.

**Non-vacuity pattern** (443-473): add one case per new rule, e.g. `test_flags_wizard_hook_first` style (`hook_order_errors([...])` returns a message list).

---

### `tests/test_arch.py` (AST rules)

**Analog:** `check_no_shell_true` (lines 760-772):
```python
def check_no_shell_true(tree):
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            ...
                violations.append(f"line {kw.lineno}: shell= must be constant False")
    return violations
```
Live rule test (lines 1065-1081) walks files with `os.walk` + `ast.parse` and `self.assertEqual([], violations)`. Non-vacuity (lines 1739-1745) parses synthetic source strings:
```python
bad_true = ast.parse("subprocess.run(x, shell=True)\n")
self.assertEqual(1, len(check_no_shell_true(bad_true)))
self.assertEqual([], check_no_shell_true(good))
```
New rules: `check_no_host_cli_calls(tree)` flagging only three forms (subprocess/Popen/os.exec*/os.system argv element, command string first shlex token, `shutil.which("<host>")`), exemption by path for `tests/host_fakes.py`; one `TestArchNonVacuity` case per form with synthetic `claude --version`. `check_no_planning_reader(tree)` for repo-root-rooted `.planning` joins (`/`, `os.path.join`, `Path(...)`, f-string) with a pinned empty exception list and a synthetic offender case. Expected live offenders listed in RESEARCH pitfall 10.

---

### `tests/host_fakes.py` (shared fake helper)

**Analog:** `tests/session_wake_fakes.py` lines 1-60: scratch-root PATH, one JSON log line per call, `_PRELUDE`.
```python
def scoped_env(root: str) -> dict[str, str]:
    home = os.path.join(root, "home")
    return {"PATH": os.path.join(root, "bin"), "HOME": home, ...,
            "AI_KIT_FAKE_LOG": os.path.join(root, "fake.log")}
```
Also `tests/cursor_fakes.py` (module docstring "Loopback-only fakes", fixtures under `tests/fixtures/<area>/`). Build one script keyed on argv (answers `--version` and `--help` for the names `gp_host.host_version`/`help_mentions` probe) rather than 80 files. Prepend its bin dir before the tripwire dir.

---

### `tests/test_ai_kit_spec_goal_prompt_evals.py` (eval module, the 162 s pole)

**Analog:** its own `eval_env` (about lines 159-180): removes `HOST_SIGNAL_ENV_VARS`, sets `CLAUDECODE=1`, fake HOME, `AI_KIT_REFUSE_REAL_HOME=1`, leaves PATH. Add a PATH built from the shared fake helper. `test_long_goal_eval_renders_the_pointer_form` needs the fake to return version/help text.

---

### `tests/test_precompact_core.py` (clock fix, D-08)

**Analog:** `core._monotonic` seam (`tools/hooks/precompact_core.py:74`) and the loop at test lines 173-193 (`test_header_counts_property`, 50 trials through `core.presummarize`). Patch with `unittest.mock.patch.object(core, "_monotonic", ...)` or `core.CLASSIFY_SECONDS`; product value stays 8 s.

---

### Mermaid e2e split (D-09)

**Analog:** `tests/test_markdown_to_pdf.py:75-83`:
```python
class TestRenderRealMmdc(unittest.TestCase):
    @unittest.skipUnless(shutil.which("mmdc"), "mmdc not installed")
    def test_real_render_produces_image(self):
```
Move to a new `tests/test_markdown_to_pdf_e2e.py`; add to `E2E_MODULES` with a comment (style of lines 62-70); skip reasons name `mmdc` and headless Chrome; run `python3 tools/gen_test_groups.py` to regenerate listings.

---

### `cross-ai.mjs` (load factor, D-10)

**Analog:** harness sites in `skills/ai-kit-spec-review/references/cross-ai.mjs`:
- line 5290 `setTimeout(() => end('case hung past 30s'), 30000)`
- lines 5297, 5299 `waitFor(..., 10000)`
- line 5348 `spec.signal.withinMs ?? 2900`; literals `withinMs: 2900` at 7179, 7199, 7496, 7504, 7513
- per-case `elapsedMs >=` ceilings at 6306, 6510, 7106, 7117, 7252, 7418, 7448, 7539, 7553, 7560, 7589, 7776, 7820, 9721; floors `< 2500` at 7152, 7428, 7471 stay unscaled.
Use one helper `scaled(ms)=Math.ceil(ms*LOAD_FACTOR)` (RESEARCH snippet), one shared constant for 2900, injected reading honoured only under `--self-test`. Add a grep-based guard test with non-vacuity. Re-render the dogfood copy via the curated-config render path (find entry in `skills/ai-kit-gsd-curated-config`; open question 2).

---

### `tools/check_dogfood.py` (D-11)

**Analog logic:** `TestDogfoodCopy` (`tests/test_curated_config_script.py:846-870`):
```python
copy = open(path, "rb").read(); template = _load_template()
cross_ai_script.template_version(copy) == cross_ai_script.template_version(template)
cross_ai_script.script_state(copy) == "pristine"
# outside(): shebang + body before "// <config>" + body from "// </config>"
```
and the no-write guard `tests/test_curated_config_e2e.py:130-140` (read `.planning/config.json` bytes before, run CLI on a scratch dir, assert bytes equal after). Stdlib script, exit 0/non-zero, wired to Makefile and a pre-push hook. Then those tests run on temp copies.

---

### Archived fixtures (D-12)

**Analog:** layout `tests/fixtures/<area>/...` (e.g. `tests/fixtures/curated_config_v2/golden/*.json`). Place copies in `tests/fixtures/archived/<phase>/`, each starting with a one-line header (source path, copy date). Offending readers: `tests/test_tool_advisor_core.py:336`, `tests/test_pi_live_tools.py:15`, `tests/test_phase26_owner_captures.py:8`.

## Shared Patterns

### Stdlib-only + argv lists
**Source:** `tools/gen_test_groups.py`, `tools/run_unittest_parallel.py`. No third-party imports; `subprocess` with argv lists, never `shell=True`.
**Apply to:** mapper, check_dogfood, any timing script.

### Atomic writes
**Source:** `tools/gen_test_groups.py:84` `_atomic_write` (mkstemp + `os.replace`, chmod preserved).
**Apply to:** any new tool that writes (mapper and check_dogfood write nothing).

### Structural rule + non-vacuity pair
**Source:** `tests/test_arch.py` `TestArchNonVacuity` (line 1441); `tests/test_gate_scope.py` `TestGateScopeNonVacuity` (line 443).
**Apply to:** host-CLI rule, `.planning/` rule, shared-machinery stale check, new hook rules.

### Fail-safe direction
**Source:** `_modules_for_groups` returns an error (exit 2) rather than silently running less; mapper errors run full `unit`+`arch`.

### Temp-dir isolation, no real homes
**Source:** `run_module` TemporaryDirectory, `scoped_env`, `AI_KIT_REFUSE_REAL_HOME=1`.
**Apply to:** every new test and helper.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `tools/time_prepush.sh` | utility | batch | The only analog (`tmp/p28/time_prepush.sh`) is gitignored; copy its shape from there, or keep it in the verification record |

## Metadata

**Analog search scope:** `tools/`, `tests/`, `.pre-commit-config.yaml`, `Makefile`, `skills/ai-kit-spec-review/references/cross-ai.mjs`
**Files scanned:** about 12 read or sampled (several via targeted ranges)
**Pattern extraction date:** 2026-11-03
