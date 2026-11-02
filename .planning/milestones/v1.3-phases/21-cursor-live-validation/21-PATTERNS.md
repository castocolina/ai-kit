# Phase 21: Cursor Live Validation - Pattern Map

**Mapped:** 2026-10-18
**Files analyzed:** 15 (new/modified)
**Analogs found:** 15 / 15 (two are role-match only)

Scope: R1-R5, R8, SC5. Linking, wizard, `--cursor-agents` (setup.py, wizard_app.py) belong to backlog 999.7 and are NOT mapped.
All analog paths below were checked as git-tracked (`git ls-files`). `<D>` = `skills/ai-kit-spec-review/ai_kit_spec`, `<C>` = `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `<D>/detection.py` (scan-all PATH resolver, `real_path`, schema bump) | utility | request-response (PATH lookup) | same file `resolve_runtime_binary:167` | exact (modify) |
| `<D>/detection.py` (`parse_cursor_models` public + `detect_cursor_models`) | utility | transform | `parse_codex_debug_models:343` + `detect_codex_models:379` | exact |
| `<C>/host.py` (`"cursor": ".cursor"` first root, G1) | config | transform | same file `_HOST_FIRST_ROOT:21-26` (opencode entry) | exact |
| `tests/fixtures/cursor_models.txt`, `cursor_models_empty.txt`, failure fixture | test fixture | file-I/O | `tests/fixtures/codex_debug_models.json`, `opencode_models_verbose.txt` | role-match |
| `tests/test_ai_kit_spec.py` (parse_cursor_models cases) | test | transform | `CODEX_FIXTURE_PATH` loading `:110-122` | exact |
| `tests/test_ai_kit_spec_runtimes_table.py` (scan-all, no-shell, real_path, SC5) | test | request-response | `TestGuardedAgentBinary:190-240`, `test_non_claude_hosts_have_no_native_selectors:96-104` | exact |
| `cursor-agents/composer-worker.md`, `grok-worker.md` | static data | none | none in repo (use RESEARCH agent shape) | no analog |
| `tests/test_cursor_agents.py` | test | transform | `tests/test_ai_kit_spec_runtimes_table.py` (module layout), `parse_codex_debug_models` fixture tests | role-match |
| `tests/gsd_curated_eval.py` (G2 semantic guard, G3 cursor chain, G4 paths, G5 `--host` choices) | utility (dev harness) | batch | same file `_baked_chain:4276`, `_generated_paths:4296`, `snapshot` files map `:196-209` | exact (modify) |
| `tests/test_ai_kit_gsd_curated_config_matrix.py` (`TestResolveModelMatrixCursor`) | test | batch | `TestResolveModelMatrixCodex/Opencode:102-108` | exact |
| `tests/test_gsd_curated_eval.py` (collection pin 27 -> 36, G2-G4 tests) | test | batch | `TestMatrixModuleCollection:3833-3850` | exact |
| `tests/test_curated_config_inventory.py` (G1 regression) | test | request-response | `test_end_to_end_fake_claude_gsd_core:199-222` | exact |
| `skills/ai-kit-gsd-curated-config/SKILL.md:251`, `README.md:45`, `tests/test_curated_config_apply.py:2378` (label lift) | doc/test | none | same lines (modify) | exact |
| `21-SMOKE-CURSOR.md`, `21-INTERACTIVE-CURSOR.md` | evidence doc | none | `20-SMOKE-CODEX.md`, `20-INTERACTIVE-CODEX.md` (in `.planning/phases/20-*/`) | exact |
| `.planning/scripts/cross-ai.mjs` | runner | - | NOT changed (orchestrator decision) | - |

## Pattern Assignments

### `<D>/detection.py` resolver (utility, request-response)

**Analog:** `<D>/detection.py:167-179` (current first-hit, guarded).
```python
def resolve_runtime_binary(rid, which_fn=shutil.which, realpath_fn=os.path.realpath):
    for name in RUNTIMES[rid].binaries:
        found = which_fn(name)
        if not found:
            continue
        expected = _GUARDED_BINARIES.get(name)
        if expected is not None and os.path.basename(realpath_fn(found)) != expected:
            continue
        return found
    return None
```
Delta: for guarded names iterate every PATH dir (RESEARCH "Resolver delta": `_path_hits` using `which_fn(name, path=d)`; the test seam is `functools.partial(shutil.which, path=tmpbin)`, so keep `which_fn(name)` for unguarded names and scan dirs only for guarded ones, or the partial would be bypassed - decide the seam in the plan). `cursor-agent` stays first; `agent` accepted at the first hit whose realpath basename is `cursor-agent`. Keep `detect_installed_clis:182` signature. Add `real_path` next to `path` in the snapshot builder (`build_runtimes_snapshot`, ~`:984-1000`) and bump `RUNTIMES_SCHEMA_VERSION = 5` (`:28`; its comment requires it). Runtime stays stdlib-only, `run_fn` list argv, never `shell=True`.

### `<D>/detection.py` models parser split (utility, transform)

**Analog:** `parse_codex_debug_models:343` / `detect_codex_models:379-392`.
```python
def detect_codex_models(binary: str, run_fn=subprocess.run) -> list | None:
    try:
        result = run_fn([binary, *_list_argv("codex")], capture_output=True, text=True,
                        check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    stdout = _listing_stdout(result)   # gates on returncode 0
    if stdout is None:
        return None
    return parse_codex_debug_models(stdout)
```
Existing to replace: `_parse_cursor_models:281-297` (requires `" - "`) and `detect_cursor_agent_models:300-314` (same try/`_listing_stdout` shape; keep it as the thin wrapper or rename to `detect_cursor_models`). New pure `parse_cursor_models(stdout)` = RESEARCH skeleton (ANSI strip, skip header/`Tip:`, first token id, `No models available for this account.` -> `[]`, nothing parsed -> `None`). Docstring style: codex's (what is read, what returns None, never raises). Update the docstring note about `privacyCache` rewrite.

### `<C>/host.py` (config, G1)

**Analog:** `<C>/host.py:20-26`.
```python
_HOST_FIRST_ROOT = {
    "pi": ".pi",
    # Local root ... observed in the ai-kit Phase 20 smoke (gsd-core 1.17.0 installer, ...)
    "opencode": ".opencode",
}
```
Add `"cursor": ".cursor"` with a comment citing the Phase 21 installer observation (`.cursor/gsd-core`). Update the module docstring lines 3-5 (names only pi/opencode).

### `tests/test_curated_config_inventory.py` (G1 regression)

**Analog:** `:199-222` `test_end_to_end_fake_claude_gsd_core` (it already passes `--host opencode` against `.claude/gsd-core`). Copy `make_gsd_install(os.path.join(project, ".cursor", "gsd-core"))`, `run_inventory(..., "--host", "cursor")`, assert `parsed["gsd_core"]["path"] == install` and scope `local`; also a case where both `.claude/gsd-core` and `.cursor/gsd-core` exist and cursor wins.

### `tests/test_ai_kit_spec_runtimes_table.py` (SPEC-06, SC5)

**Analog:** `TestGuardedAgentBinary:190-240`. Pattern: real temp-dir symlinks, `_which_in(bin_dir)` helper (`:181`), `_touch` (`:189`).
```python
real = os.path.join(tmp, "versions", "cursor-agent"); _touch(real)
os.symlink(real, os.path.join(bin_dir, "agent"))
found = detection.resolve_runtime_binary("cursor", which_fn=_which_in(bin_dir))
```
New cases: grok-first PATH then cursor later (two bin dirs, scan-all finds the later `agent`); both names -> one report; shell function invisible (no PATH entry -> None); `real_path` recorded; `detect_cursor_models` called with a fake `run_fn` that asserts `argv` is a list and `shell` kwarg is not truthy. If the scan-all needs a `path=` aware seam, add a sibling helper to `_which_in` (or use `functools.partial(shutil.which, path=tmpbin)` per D-09).
SC5: extend `test_non_claude_hosts_have_no_native_selectors:96-104`:
```python
self.assertEqual(detection.RUNTIMES["cursor"].native_selectors, ())
self.assertFalse(host_can_select("cursor", "composer-2.5", "cursor"))
```

### `tests/test_ai_kit_spec.py` (parse_cursor_models tests) and fixtures

**Analog:** `tests/test_ai_kit_spec.py:92-122` (provenance comment block next to the constant, then `CODEX_FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", ...)`). Add `CURSOR_MODELS_FIXTURE_PATH` with a provenance comment (command `cursor-agent models`, version 2026.10.14-941492e, date, zero-width chars kept, 265 unique ids). Failure fixture: label it synthetic (RESEARCH open question 5). Assertions: `composer-2.5` and `grok-4.7-medium` present, 79 `-fast` ids, nameless `auto (current, default)` kept, ANSI stripped, empty notice -> `[]`, exit 1 -> `None`.

### `cursor-agents/*.md` (static data) - no repo analog

Use RESEARCH shape verbatim (unquoted single-line scalars, non-empty body, `name` equals filename stem, not `gsd-*`):
```markdown
---
name: composer-worker
description: Executes one already-planned task end to end on a pinned non-fast model
model: composer-2.5
---
<short body>
```
`grok-worker.md` pins `grok-4.7-medium`. Top-level dir `cursor-agents/` (not `agents/`, which links into `~/.claude/agents`). Check `tests/test_gate_scope.py`/installer file listings do not choke on a new top-level dir.

### `tests/test_cursor_agents.py` (new unit module, transform)

**Analog layout:** `tests/test_ai_kit_spec_runtimes_table.py:1-25` (docstring, `unittest`, repo-relative paths, no absolute paths). Resolve repo root via `os.path.dirname(__file__)`. Contents: ported `Ks` parser (RESEARCH code example, `re.M`), field allowlist, D-07 static rule, D-08 (`id in fixture` and `not id.endswith("-fast")`), `skipUnless(shutil.which("node"))` parity test running the same JS regex via `node -e` with a list argv, optional live `gsd_catalog.query_agent_catalog` cross-check. New `tests/test_*.py` joins the `unit` group automatically (AGENTS.md); `tests/test_gate_scope.py` pins group lists - run it, regenerate with `tools/gen_test_groups.py` only if it demands.

### `tests/gsd_curated_eval.py` harness (G2-G5)

**G2** analog `:196-209`: strict file map, today `f"{HOME_LABEL}/.cursor/cli-config.json": home / ".cursor" / "cli-config.json"` with the comment about the listing probe. Cursor runs need a semantic digest of only `modelParameters`, `subagentModels`, `exploreSubagentModel` (hash of the allowlisted subset, never read `authInfo`/`auth.json`), plus listings for `~/.cursor/{agents,skills,hooks.json}`. Follow the existing `_dir_names(...)` listing pattern used for `.planning` backups.
**G3** analog `_baked_chain:4276-4345`: existing branch `if ctx.host == "codex": promised_map = ... else: ...`. Add `elif ctx.host == "cursor"`: `promised_map = {agent: None for agent in agents}` and report "resolve-model only"; `_baked_models:4254` globs `gsd-*.md` for non-codex, which already works (all `None`).
**G4** analog `_generated_paths:4296-4306`: prefixes loop `("gsd-core", "plugins/gsd-core.js")`; add cursor `hooks`, `hooks.json`, `scripts`, `.gsd-*` (report-only).
**G5** `:4896` `choices=("claude", "codex", "opencode")` -> add `"cursor"`.
Also `_host_model` (`:522-542`) needs per-tier `model_profile_overrides.cursor.<tier>` or `resolve_model_ids == omit` handling (RESEARCH Answer 3).

### `tests/test_ai_kit_gsd_curated_config_matrix.py` (G5)

**Analog:** `:102-108`.
```python
class TestResolveModelMatrixOpencode(TestResolveModelMatrix):
    HOST = "opencode"
```
Add `TestResolveModelMatrixCursor` with `HOST = "cursor"`; update the module docstring (line 1). Real HOME is required (setUpClass uses `pathlib.Path.home()`).

### `tests/test_gsd_curated_eval.py` pin

**Analog:** `TestMatrixModuleCollection:3833-3850`: update the class list to include `TestResolveModelMatrixCursor`, the count 27 -> 36, rename the test (`...three_host_classes_only`). Add unit tests for G2 (privacyCache rewrite passes, modelParameters change fails), G3, G4 beside the existing snapshot/chain tests.

### Label lift (`SKILL.md:251`, `README.md:45`, `test_curated_config_apply.py:2378`)

Current: `| cursor / pi hosts | **not live-validated** |`; README: "cursor/pi not live-validated"; test `required = ("not live-validated", ...)`. Change in the same commit as `21-SMOKE-CURSOR.md`: row -> `| pi hosts | **not live-validated** |` plus a cursor evidence pointer; README likewise; the test literal stays valid (pi) - add an assertion that "cursor / pi" is gone. Any SKILL.md change triggers the skill-judge loop (floors 109/120 in-session, 116/120 pi, per `20-SKILL-JUDGE.md`).

### Evidence docs

**Analog:** `.planning/phases/20-opencode-codex-live-validation*/20-SMOKE-CODEX.md` and `20-INTERACTIVE-CODEX.md` (glob `.planning/phases/20-*/`). Interactive script structure: title, "Before you start" bullets (checkout root via `git rev-parse --show-toplevel`, clean `git status --porcelain`, node on PATH, `--installer-dir` fallback, nothing edits global config), then numbered `REQUIRED - **title**` steps with a fenced `text` block and `expect:` line, names-only env dump. Cursor adaptation: TUI step, compare only user-owned keys by hash, optional SC5 per-call `model` probe from `--output-format stream-json`. Headless dispatch: `.planning/scripts/cross-ai.mjs --prefer cursor --model-cursor composer-2.5 --mode exec --no-preamble --child-pgid-file <f>` under a scratch CURSOR_CONFIG_DIR/XDG_CONFIG_HOME with the login file symlinked; judge success by `smoke exit=0` plus the evidence file, not runner status.

## Shared Patterns

### Injectable seams, no shell
**Source:** `<D>/detection.py:167,300,379` (`which_fn`, `realpath_fn`, `run_fn` defaults). **Apply to:** all detection changes and their tests. List argv, `capture_output`, `timeout=15`, `except (OSError, subprocess.TimeoutExpired)`.

### Test hygiene
**Source:** `tests/test_ai_kit_spec_runtimes_table.py` (`tempfile.TemporaryDirectory`, `os.symlink`, `_touch`). **Apply to:** every new test. Synthetic temp dirs only; never the real `~/.cursor`; no absolute paths; scratch under `./tmp/`.

### Provenance comments for fixtures
**Source:** `tests/test_ai_kit_spec.py:92-122`. **Apply to:** `cursor_models*.txt` constants.

### Certainty labelling
`<D>/detection.py:48-51` `_LABEL_CURSOR` stays `source-inspected-only` unless the smoke's names-only env dump shows `CURSOR_AGENT` from a live cursor shell; a change needs its own assertion (existing pin covers pi/codex only, `test_ai_kit_spec.py:1334-1354`).

## No Analog Found

| File | Role | Reason |
|---|---|---|
| `cursor-agents/*.md` | static data | First shipped Cursor subagent files; use RESEARCH agent shape and the ported `Ks` parser |
| Cursor `real_path` field in `runtimes.json` | schema | No prior `real_path` key; follow the schema-bump comment at `detection.py:28` |

## Metadata

**Analog search scope:** `skills/ai-kit-spec-review/ai_kit_spec`, `skills/ai-kit-gsd-curated-config`, `tests/`, `.planning/phases/20-*`
**Files scanned:** ~14 read (targeted ranges), CodeGraph synced once
**Pattern extraction date:** 2026-10-18

## PATTERN MAPPING COMPLETE
