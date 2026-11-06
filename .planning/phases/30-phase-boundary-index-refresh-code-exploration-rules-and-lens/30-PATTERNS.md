# Phase 30 - Pattern Map

**Mapped:** 2026-11-05. Files analyzed: ~30 (per RESEARCH U10). Analogs found: all key ones. All analog paths are git-tracked source.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `skills/ai-kit-commit-fold/scripts/flow_index.py` | command module | batch/subprocess | `scripts/flow_unit.py` (`_run`, `cmd_*`) | exact |
| `scripts/flow_boundary.py`, `flow_brief.py` | command module | request-response + file-I/O | `scripts/flow_unit.py` + `flow_record._atomic_write_json` | exact |
| `scripts/fold.py` (register `index`, `boundary`) | dispatcher | request-response | its own `_FLOW_HANDLERS` | exact |
| `tests/index_fakes.py` | test fake | event-driven log | `tests/forge_fakes.py` (`write_forge_fakes`) | exact |
| `tests/test_flow_index*.py`, `test_flow_boundary.py` | test | e2e real git | `tests/test_flow_contract.py` `_FlowCase` | exact |
| `tests/test_rules_docs.py` | doc-contract test | transform | `tests/test_flow_docs.py` `TestShipRule` | exact |
| `gsd/ai-kit-commit-fold/capability.json`, `ai-kit-fold.cjs` | config/adapter | request-response | themselves (`steps`, `VERBS`) | exact |
| `tools/config_doctor_checks.py`, `config_doctor_appliers.py` | check rows | CRUD | own rows; `atomic_write_json` | exact |
| `tools/global_rules.py`, `marked_block.py`, `setup_dev.py` | utility | file-I/O | `tools/setup.py` `_atomic_write_json`, existing marked_block | role |
| `AGENTS.md`, `docs/run-book/graphify.md`, SKILL.md files, `.planning/lens-brief/SKILL.md` | docs | n/a | existing AGENTS Workflow bullets | role |

## Pattern Assignments

### Command modules (flow_index / flow_boundary / flow_brief)
**Analog:** `skills/ai-kit-commit-fold/scripts/flow_unit.py`

Imports are flat sibling modules (lines 9-13): `import flow_git`, `import flow_record`, `from flow_record import (...)`.

Run wrapper, lines 168-181 (refusals via `FlowError`, rendered report, exit 1, or 2 for bad input):
```python
def _run(command, args, body):
    unit = args.unit
    try:
        lines, outcome = body(args, unit)
    except FlowError as exc:
        print(render(command, unit_id, branch, [f"refused: {exc.reason}: {exc.detail}"], f"refused {exc.reason}"))
        return 2 if exc.reason in _EXIT_BAD_INPUT else 1
    print(render(command, unit_id, branch, lines, outcome))
    return 0
```
Entry point, lines 363-364: `def cmd_start(args): return _run("start", args, _start)`.

Boundary: tool absence must give a report line and exit 0, not a raise. Route every external call through one `run_tool(argv, cwd)` seam (argv list, no shell).

### `scripts/fold.py` registration
**Analog:** `fold.py:31-42`. Add `"index": ("flow_index", "cmd_index")` and `"boundary": ("flow_boundary", "cmd_boundary")` to `_FLOW_HANDLERS`. Add `sub.add_parser(...)` beside the existing ones at lines ~97-122, with `--point` and `--detach` flags. A missing module or function fails closed with exit 2.

### Atomic write (brief, status file, queue)
**Analog:** `flow_record.py:112-127`. Copy the shape; skills stay self-contained, so never import across skills.
```python
fd, temp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        ...; handle.flush(); os.fsync(handle.fileno())
    os.replace(temp, path)
except BaseException:
    if os.path.exists(temp): os.unlink(temp)
    raise
```
A text or bytes variant is needed for the SKILL.md brief; mirror `config_doctor_appliers.atomic_write_json` for that.

### `tests/index_fakes.py`
**Analog:** `tests/forge_fakes.py:375-403`. The fake is a script template with `@TOKEN@` placeholders, filled by `_script()`, written to a bin dir, chmod 0o755. It logs each call, keeps state in a JSON file, and has `forge_state()` and `set_*()` helpers.
```python
def write_forge_fakes(bin_dir, state_path, log_path, gh_stack=False, signed_in=True):
    script = _script({"@PY@": sys.executable, "@LOG@": repr(str(log_path)), "@STATE@": repr(str(state_path)), ...})
    gh = bin_path / "gh"; gh.write_text(script, encoding="utf-8"); gh.chmod(0o755)
```
Do the same for fake `codegraph` and `graphify`, with the same log format (`host_fakes.fake_calls`). Keep the state helpers `forge_state`, `fail_next_edit` and `set_pr` as the model for `fail_next(...)`.

### Real-git test cases
**Analog:** `tests/test_flow_contract.py:40-65`. `_FlowCase.setUpClass` builds a template once in `tempfile.mkdtemp`, with `addClassCleanup(shutil.rmtree, ...)`. `setUp` does `shutil.copytree(template, case)`, uses an isolated `HOME` via `f.git_env(home)`, and pops `GH_TOKEN`. Subclass it for the boundary and index e2e tests. Add the e2e modules to `E2E_MODULES` and `E2E_RECORDED_SECS` in `tools/run_unittest_parallel.py`.

### Doc-contract tests (`test_rules_docs.py`)
**Analog:** `tests/test_flow_docs.py:211-231` (`TestShipRule`). Pattern: extract the rule bullet, then `_missing_steps(rule)==[]`, `_in_order(rule, ORDERED)`, plus non-vacuity (the reversed order fails; removing any one step reports exactly that step; a missing bullet fails). Keep that non-vacuity for every new rule. The brief template must contain the word "mentions" (test pin).

### GSD adapter (`capability.json`, `ai-kit-fold.cjs`)
**Analog:** `capability.json` `steps[]` (lines 19-33):
```json
{"point": "discuss:pre", "ref": {"command": "ai-kit-fold start"}, "produces": [], "consumes": [], "onError": "skip"}
```
Add `boundary-plan` and `boundary-wave` steps the same way, with `onError: skip`. Bump `version`. The `plan:pre` command step is never dispatched by plan-phase (Pitfall 1), so cover it with an e2e. In `ai-kit-fold.cjs:12`, add to `VERBS` (`start: 'start', ...`) for `boundary-plan` and `boundary-wave`. Update the usage string at line 71. Keep `.planning/config.json` changes to `config-set` only.

### Config doctor / setup rows
**Analog:** `tools/config_doctor_checks.py` existing check functions and `config_doctor_appliers.atomic_write_json`. `tools/setup.py` is the only file that gets the `Bash|Read|Grep|Glob` matcher row. Writes must use `_read_json_checked` and `_atomic_write_json`, and JSONC edits stay surgical.

## Shared Patterns
- **External tools:** a single `run_tool` seam (argv list). A missing CLI gives one report line and exit 0.
- **Locks:** take the lock in the git common dir. Never `os.remove` a lock you do not own. Honor graphify's `.rebuild.lock`.
- **Stdlib only** for runtime code. No `.planning/` writes in a non-GSD project.
- **Generated blocks** (`Makefile`, `.pre-commit-config.yaml`) are regenerated at wave end. Run plans sequentially in the U10 order.
- **Tests:** a new `tests/test_*.py` joins the `unit` group automatically. Never use real home config. Export `AI_KIT_REFUSE_REAL_HOME=1`.

## No Analog Found
| File | Reason |
|---|---|
| `tools/setup_dev.py` post-checkout detached queue runner (one flock) | No existing detached-runner pattern. Use RESEARCH architecture section. |
| `.planning/lens-brief/SKILL.md` | New tracked skill. Follow other SKILL.md files and run skill-judge. |

## Metadata
Search scope: `skills/ai-kit-commit-fold`, `tests/`, `tools/`. Extracted from files read in worktree `tmp/wt-30`.
