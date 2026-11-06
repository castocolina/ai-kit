# Phase 31: Removals and small defects - Pattern Map

**Mapped:** 2026-11-06
**Files analyzed:** 12 new/modified code areas (removals are deletions and need no analog)
**Analogs found:** 12 / 12 (paths are repo-relative, all tracked)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `skills/ai-kit-spec-review/ai_kit_spec/cli.py` (`check-providers` parser + `_cmd_check_providers` + `_COMMANDS` row) | controller (CLI subcommand) | request-response | same file: `detect-runtimes` / `detect-tools` (parser L142-163, `_cmd_detect_tools` L~410, `_COMMANDS` L~990) | exact |
| new provider-check logic module in `ai_kit_spec/` (scan 3 sources, format lines) | service | transform | `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cross_reference.py` (to be deleted: carry `scan_review_spec`, `scan_catalog`, `review_spec_strategy`, `SourceStatus`, `collect_references`, `format_reference`) | exact (port) |
| new read-only JSONC reader in `ai_kit_spec/` | utility | transform | `tools/config_doctor_readers.py` (`strip_jsonc_comments` L106, `strip_trailing_commas` L137, `read_jsonc_checked` L179, `get_nested` L201) | exact (copy) |
| drift test for the JSONC reader | test | transform | `tests/test_ai_kit_rules_common.py` L1285-1310 (copy-vs-source equality with message) and L1619 `test_drift_guard_is_non_vacuous` | role-match |
| `tools/setup.py` headless prune wiring (`prune_stale` call in install/reconfigure headless) | controller | batch | `prune_stale` L1378 (already has non-interactive branch), `_headless_*` L4114+ | exact |
| `tools/setup.py` resolved-path helper replacing `_is_inside` | utility | transform | `_is_inside` L1076 (callers: L1097, 1279, 1426, 2824, 2865) | exact |
| `tools/install.sh` `is_inside` | utility | transform | its own `is_inside` (setup.py docstring says it mirrors it) | exact |
| rtk tracked-file ban test (new test module) | test | batch | `tests/test_tool_substitution_hook.py` L1299 `test_no_hook_file_mentions_the_rewrite_tool` (to be replaced) + `TestArchNonVacuity` `tests/test_arch.py` L2539 | role-match |
| edge-floor guard e2e test | test | batch | `tests/test_ai_kit_gsd_spec_discuss_e2e.py` (named skipUnless node + engine) | exact |
| goal-prompt `@file:` helper | utility | file-I/O | `_gsd_json` `skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py` L248 | exact |
| runtime-list drift test | test | transform | `tests/test_ai_kit_spec_runtimes_table.py` L465-490 (`assertLessEqual` superset checks to tighten) | exact |
| AGENTS.md link test | test | file-I/O | `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py` `_parse_link_target` L30, `_without_fenced_code`, `_LINK_RE` | role-match |
| pi wording doc-contract test | test | file-I/O | `tests/test_ai_kit_spec_goal_prompt_skilltext.py` (reads SKILL.md, pins facts) | role-match |

## Pattern Assignments

### `check-providers` subcommand (`cli.py`)

Register in the parser function beside the others, handler `(args, deps) -> int`, row in `_COMMANDS`.

```python
sub.add_parser("detect-tools")                      # L~140
p_detect = sub.add_parser("detect-runtimes")        # L148, flags via add_argument

def _cmd_detect_tools(args: argparse.Namespace, deps: CliDeps) -> int:
    print(json.dumps(detect_tool_availability(which_fn=deps.which_fn)))
    return 0

_COMMANDS = {
    "detect-tools": _cmd_detect_tools,
    "detect-runtimes": _cmd_detect_runtimes,       # L994
```

Use `deps.env_fn()`, `deps.which_fn`, `deps.run_fn` (never real subprocess) so tests inject fakes. Served providers: `detection.detect_opencode_models(binary, run_fn, env)` (detection.py L297; returns list of `provider/model` lines or `None`). Provider = part before `/`. Catalog: use `cache_read_json(cache_catalog_path(deps.env_fn()))` and `split_catalog_meta` (skip `_meta`). Exit 0 always. Plain-text output (not JSON), unlike detect-*.

Ported scan shape (from the skill being deleted; read it before deleting): sources print in order local, global, catalog as `scanned` / `scanned-inactive` / `absent` (`SourceStatus(str)` carries `.reason`); warning line `warning: "<provider>" is referenced in <file>: <key> model=<provider>/<model>` plus `(not active: local review-spec sets strategy = "local-only")`. Match on the model id provider only, never the `runtime` field. Never read `auth.json`, never print `apiKey`.

### JSONC reader + drift test

Copy `strip_jsonc_comments`, `strip_trailing_commas`, the `_classify*` helpers (L26-104) from `tools/config_doctor_readers.py`; add a function returning child names of `provider` and `providers` only. Config paths: `${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-~/.config}/opencode}/opencode.json(c)` plus project `opencode.json(c)` and `.opencode/opencode.json(c)`.

Drift test: load the skill module and `tools/config_doctor_readers.py` by path (like `_COMPOSE_PARSE_PATH` loader at test_ai_kit_rules_common.py L~2202), run both on shared synthetic fixtures (comments, trailing commas, escaped strings, v1 `provider` and v2 `providers`), `assertEqual` the parsed `provider` keys, with a message naming both files. Add a `test_drift_guard_is_non_vacuous` twin (mutate one side, assert mismatch).

### Headless prune (`tools/setup.py`)

```python
def prune_stale(claude_dir, install_dir, present, tty, dry, counts):  # L1378
    stale = stale_link_candidates(claude_dir, install_dir, present)
    if not stale: return []
    if is_interactive(tty): ...ask_yes_no(...)
    else:
        for item in stale:
            print(f"warn: removing dead ai-kit link {item} (entry removed upstream)", file=sys.stderr)
    apply_stale_prune(claude_dir, stale, dry, counts)
```

Call it from the headless install and reconfigure flows for the claude root and, if `os.path.isdir`, the pi root, before `_headless_link_skills` (L4133). Pi root skips with the existing note, never created. `stale_link_candidates` L1349 only removes links where `_is_inside(target, install_dir)` and `not os.path.exists(link)`; keep that guard. Handle a link vanished between detection and removal as gone (`unlink_one`).

### Resolved-path helper

Replace L1076:
```python
def _is_inside(path, root):
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)
```
with a version that applies `os.path.realpath` to both then compares via `os.path.commonpath([p, r]) == r` (so `ai-kit` is not inside `ai-kit-old`). A dangling link target: realpath still resolves the string lexically, fine. Resolve link targets relative to the link's dir (`os.readlink` may be relative). Same replacement at all five call sites. Kit dir: `AI_KIT_DIR`, else `realpath(__file__)` parent of `tools/`. Empty/unset HOME fails with a message.

### rtk ban test

Current form to replace:
```python
def test_no_hook_file_mentions_the_rewrite_tool(self):
    ...assertNotRegex(line.lower(), r"rtk", f"{path}:{line_number} mentions forbidden tool")
```
New: `git ls-files -z` from a repo root resolved from `__file__` (skip with a named reason if `git rev-parse --is-inside-work-tree` fails), `re.compile(r"\brtk\b", re.I)`, read bytes, skip if NUL in first 8192 bytes, decode `utf-8` `errors="replace"`. Exemption tuple `(prefix, reason)` for `.planning/`, `docs/prds/`, `docs/superpowers/`, the test itself, `skills/ai-kit-usage-metrics/`, `tests/test_ai_kit_usage_metrics.py`; a second check that usage-metrics SKILL.md has no `install rtk`, `rtk init`, `rtk <subcommand>`. Non-vacuity: factor the scanner into a function taking `(files, reader)` so a case feeds a synthetic path/content; pattern from `TestArchNonVacuity` (test_arch.py L2539: each rule has a pure function called on a snippet that must be flagged, and a clean snippet that must not). Use `subprocess` only for git (fine under the tripwire).

### Edge-floor guard e2e

```python
@unittest.skipUnless(shutil.which("node") and edge_floor.find_engine(os.environ, os.getcwd(), None),
                     "node or gsd-core edge-probe.cjs not installed")
def test_...(self):
    engine = edge_floor.find_engine(os.environ, os.getcwd(), None)
    self.assertEqual(edge_floor.main(["check", str(full), "--engine", engine], env=os.environ), 0)
    # row removed -> 1
```
Import `edge_floor` as that module does (`from tests.test_ai_kit_gsd_spec_discuss import edge_floor`). Loop `sorted(Path(".planning/phases").glob("*/*-SPEC.md"))`, report each failing path; exit 2 from the engine is a named skip. Fixture-row-removed case: copy `_spec_with` (L22-30). Register the module in `E2E_MODULES` (`tools/run_unittest_parallel.py` L107) and add its recorded time to `E2E_RECORDED_SECS`. Note the AGENTS.md says no test reads the repo `.planning/` (arch rule); this guard needs an explicit, commented exception in that arch rule or the plan must change the rule; flag to planner.

### goal-prompt `@file:` helper

```python
def _gsd_json(args, seams, tokens, query):   # goal_prompt.py L248
    rc, out = seams.host.run([*tokens, "query", *query], GSD_TIMEOUT, args.repo)
    if rc != 0: return None
    try: return json.loads(out)
    except ValueError: return None
```
Add `_load_gsd_output(out)`: `if out.startswith("@file:")`: path = `out[6:].strip()`; empty path or `OSError` -> return None path (same failure as bad JSON); else read file then `json.loads`. Only a reply that STARTS with the prefix redirects. Callers at L274, 283, 293 all go through `_gsd_json`, so one change covers them; grep gp_*.py for other `json.loads` of gsd output.

### Runtime-list drift test

Extend `tests/test_ai_kit_spec_runtimes_table.py` near L465-490, where today's checks are `assertLessEqual(set(cross_ai.RUNNER_IDS), ids)`, `assertNotIn("copilot", ...)`. Add: a table of `(name, copy, expected, reason)`; `assertEqual(set(copy), set(expected))` with deliberate differences as an explicit reason dict (`RUNNER_IDS` minus claude); `HOST_BINARY` compared to `RUNTIMES` binaries (cursor -> `agent`); JS template list equal (change the superset). Non-vacuity: add a synthetic runtime to a copy only and assert the helper reports a difference.

### AGENTS.md link test

Reuse `_LINK_RE`, `_parse_link_target`, `_without_fenced_code` from `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py` (import via `sys.path` like the skilltext test does for `skills/ai-kit-project-rules-agents`). For each resolved target: `os.path.exists` else fail; then `git check-ignore -q <path>` (rc 0 = ignored = fail). Report all bad links in file order. Fixture test: temp git repo with a `.gitignore` entry and a linking AGENTS.md.

### pi wording doc-contract test

Pattern from `tests/test_ai_kit_spec_goal_prompt_skilltext.py`: `Path(__file__).resolve().parent.parent`, read `skills/ai-kit-gsd-curated-config/SKILL.md` (line ~134) and `recommend.py` L325 message, `assertIn` exact ASCII strings (`PI_PROVIDER`, `PI_MODEL`, "bash tool", "not for `!` commands or RPC bash").

## Shared Patterns

### Fakes and isolation
Tests use scratch HOME, `tests/host_fakes.py`, tripwire PATH (AGENTS.md Testing > Isolation); inject `run_fn`/`which_fn`/`env_fn` through `CliDeps`. Never real `opencode`/`pi`.

### Drift tests with non-vacuity
Copy-vs-source equality with a message, plus a `*_is_non_vacuous` test (test_ai_kit_rules_common.py L1619, L2280, L2323).

### Removal bookkeeping
Remove entries in place from `Makefile:12`, `.pre-commit-config.yaml:14,59`, `pyproject.toml` extraPaths, `tests/test_gate_scope.py:38-39`, `tests/test_arch.py:782,786,1799`, `tests/test_ai_kit_spec_runtimes_table.py`, `tests/test_quota_policy_text.py`, `tests/test_cross_ai_skill_text.py`, README rows.

## No Analog Found

| File | Reason |
|---|---|
| `install.sh` realpath handling | no prior symlink-alias test; build alias inside scratch HOME per D-05 (use `tests/test_install.sh` structure) |
| herdr pi live check (R9) | verification step, not code |

## Metadata

**Analog search scope:** `skills/ai-kit-spec-review`, `skills/ai-kit-spec-goal-prompt`, `skills/ai-kit-project-rules-agents`, `tools/`, `tests/`
**Tracked-source gate:** all named analogs are repo-tracked paths (no `.gsd` mirrors); the deleted-skill analog `cross_reference.py` must be ported before deletion.
**Pattern extraction date:** 2026-11-06
