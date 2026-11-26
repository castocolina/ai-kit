# Phase 41: Superpowers adapter refactor with spec-config handoff - Pattern Map

**Mapped:** 2026-11-25
**Files analyzed:** 9 groups
**Analogs found:** 9 / 9 (item 4 partial)

All paths are repo-relative and git-tracked. `SR` = `skills/ai-kit-spec-review/ai_kit_spec`.

## File Classification

| New/Modified file | Role | Data flow | Closest analog | Match |
|---|---|---|---|---|
| `SR/lane_settings.py` (new role-level bool reader) | utility | transform | `lane_settings.py:_bool_setting`, `lane_usage_limit` (96-107) | exact |
| `SR/lane_switch.py` (role-parameter + execute switch) | service/command | request-response | `lane_switch.py:next_lane`, `flagged_replacement`, `cmd_switch_lane` (46, 182, 242) | exact |
| `SR/dispatch_guidance.py` (two builders) | utility | transform | `dispatch_guidance.py:build_failure_reporting_guidance`, `build_dispatch_reinforcement_guidance` (55-82) | exact |
| new stdlib module (audit, checkout marker, lane env) | utility | file-I/O | `tools/setup.py:_refuses_real_home` (5186); `runner_dispatch.child_env` (163) | role-match |
| `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py` | controller | request-response | `cli.py:_build_parser`, `_COMMANDS`, `_cmd_write_resumable_state` (385-486) | exact |
| jev haiku/sonnet pick | service | request-response | `SR/skill_classify.py:classify` (112-131) | exact |
| spec-config execute-role question + writer | docs + config | CRUD | `skills/ai-kit-spec-config/references/free-lanes.md` section b/c (19-25) | role-match |
| doc-contract tests | test | transform | `tests/test_ai_kit_spec_superpowers.py:TestPinnedResumeAndReturnCode69OneRule` (3293) | exact |
| `skills/ai-kit-spec-execute-superpowers/evals/evals.json` | config | static | same file (4 existing evals) | exact |

## Pattern Assignments

### 1. `SR/lane_settings.py` - session-model fallback flag reader

**Analog:** `lane_settings.py:96-113`. The reader section sits under the banner `# ── Readers (...) ──` (line 76); add the new reader and NamedTuple/`LANE_FLAG_KEYS` entry there.

```python
def _bool_setting(entry: dict, name: str) -> bool:
    value = entry.get(name, False)
    if not isinstance(value, bool):
        raise LaneSettingError(f"{entry.get('key', '<unknown>')}: '{name}' must be a boolean")
    return value

def lane_escalation(entry: dict) -> Escalation:
    """36 D-06 / SPEC R5: read escalation flags; non-booleans raise a named error."""
    return Escalation(_bool_setting(entry, "escalate_runtime"),
                      _bool_setting(entry, "escalate_model"))
```

Conventions: the key must join three places or it is not "written only when true / refused when non-boolean":
`LANE_FLAG_KEYS` (line 11, drives `normalise_lane_settings` dropping false and `_problems` "must be a boolean") and
`MODEL_BOUND` (line 13, settings dropped on a pair change). Tests: `tests/test_lane_settings.py` (reader raise with key
named, false dropped), `tests/test_config_role_write.py` (write refusal, e.g. `_lane(..., usage_limited="yes")` at line 200).
Note: "role-level" in the SPEC sits on a lane-table entry (D-03); no role-level table exists, so the reader takes an entry dict.

### 2. `SR/lane_switch.py` - execute switch

**Analog:** `lane_switch.py`. Review is hardcoded in three places the planner must parameterize: `review_lane` (line 32,
`config.get("review")`), `next_lane` (47-48, `selectable_lanes("review", ...)` and `role_order(config, "review")`), and
`review_routes` (226). `flagged_replacement` (182-193) is already role-neutral except for calling `review_lane`.

```python
def next_lane(config: dict, base_key: str, exclude, route_fn) -> str | None:
    ordered = lane_settings.selectable_lanes("review", config.get("review"),
                                             role_orders.role_order(config, "review"))
    ...
        pick = lane_settings.lane_fallback([lane for lane in ordered
                                            if lane["key"] not in excluded], base_key)
```

Note `selectable_lanes` (`lane_settings.py:152`) already has an execute mode (ordered lanes plus the rest in roster order).
`pool_status(lane, now_s, reader)` (112) and `blocked_reader(deps)` (154) are already role-free: reuse as is.
Command pattern to copy for the subcommand (289-300): `register_parsers(sub)` with `sub.add_parser("switch-lane", ...)`
and `COMMANDS = {"switch-lane": cmd_switch_lane}`; `cmd_switch_lane` validates args (exit 2), re-raises
`config_io.ConfigError`, maps `(OSError, ValueError, KeyError, TypeError)` to a stderr line and exit 2; `_switch_lane` prints
`switched <old> -> <new>` (exit 0) or `not switched <old>: <reason>` (exit 1). Tests: `tests/test_lane_switch.py`; fake route
function and deps seams (`which_fn`, `env_fn`, `run_fn`) as there.
Caution: `_switch_lane` reads review round state (`review_log.round_states`, `reviewers.json`); the execute switch has no round
log, so it needs its own thin caller, not a copy of `_switch_lane`.

### 3. `SR/dispatch_guidance.py` - gates and commit guard builders

**Analog:** `build_failure_reporting_guidance` (55-65) for a fixed-prose builder; `build_output_format_guidance(format_block)`
(44-52) for a caller-fed builder holding no framework wording.

```python
def build_output_format_guidance(format_block: str) -> str:
    return ("Your entire final response ... MUST match this exact "
            "structure -- nothing before it, nothing after it:\n\n" + format_block)
```

Placement in `build_dispatch_reinforcement_guidance` (68-82): sections list is model override, incremental progress, failure
reporting, then `if format_block is not None: sections.append(...)` last. Insert the two new builders after
`build_failure_reporting_guidance()` and before the format block (D-04). The signature
`(resolved_label, format_block)` is the one callers pass through `execute_dispatch.py:63-89`
(`build_reinforcement_fn` seam, `spec.format_block`) and `cli.py:325-349`; add optional args with None defaults so GSD callers
and `tests/test_ai_kit_spec.py` stay unchanged. Module docstring rule: no framework wording, never edits another framework's prose.

### 4. New stdlib module (host-config audit, checkout marker, lane env)

**Analogs (no exact match; role-match only):**
- Guard semantics, `tools/setup.py:5186-5198` `_refuses_real_home(env)`: compares `realpath(HOME)` with `pwd.getpwuid(...).pw_dir`.
  `tools/setup.py` is not importable from skills; copy the idea, do not import it.
- Lane env: `SR/runner_dispatch.py:163-173` `child_env(extra, env)` copies env, scrubs `HOST_SIGNAL_ENV_VARS`, applies `extra` last:
  pass `extra={"AI_KIT_REFUSE_REAL_HOME": "1"}`. It is already called at `lane_switch.py:93`.
- Subprocess seam: `detection.run_in_own_group(argv, *, timeout, ...)` (955) and `detection.bounded_run(run_fn)` (980) with
  injectable `run_fn` in tests.
- HOME resolution from a passed env: `SR/jsonc_read.py:166` (`home = env.get("HOME") or os.path.expanduser("~")`) and
  `jev_names.py:55` `skills_roots` (HOME-relative root table, `os.path.expanduser`).
- Seed-data table convention: `RUNTIMES` in `SR/detection.py` (AGENTS.md architecture note: one table, never a decider).
Tests set a scratch HOME plus `AI_KIT_REFUSE_REAL_HOME=1` (`tools/run_unittest_parallel.py:456`). No existing code detects an
"ai-kit checkout"; `.planning/research` has none either: held-out fixtures decide the marker (D-05). No analog: a mtime snapshot
(`st_mtime_ns`) helper does not exist. Module placement: it is imported by both the adapter CLI and the runner dispatch, so
live beside `SR` modules; mind `tests/test_arch.py` rules for stdlib-only runtime code.

### 5. `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py`

**Analog:** the file's own pattern: a parser block in `_build_parser` (392-476), a handler `_cmd_*(args, deps: CliDeps) -> int`,
and an entry in `_COMMANDS` (479-486). The adapter does NOT use `register_parsers` / `COMMANDS` (that is the `SR` convention,
item 2); keep the adapter's `_COMMANDS` dict.

```python
def _cmd_write_resumable_state(args: argparse.Namespace, deps: CliDeps) -> int:
    state = json.loads(args.state_json)
    deps.write_resumable_state_fn(args.path, state)
    deps.stdout.write(json.dumps({"written": True, "path": args.path}))
    return 0
```

`dispatch-task` (431-451) takes file args (`--format-block-file`, read at 320-322 by `_load_dispatch_task_files`); add
`--gates-file` / `--guard-file` the same way and thread through `_dispatch_guidance_for_cli` (325). Outputs are JSON to
`deps.stdout`; side effects go through `CliDeps` fields (a NamedTuple seam, `_replace(**overrides)` in `main` 498-505);
`ConfigError` becomes exit 2. Tests: `tests/test_ai_kit_spec_superpowers.py` classes `TestCliDispatchTask` (1805),
`TestCliResumeExclusions` (2420), `TestCliWriteResumableState` (2442), `TestCliResolveInjection` (1180).

### 6. jev haiku/sonnet pick

**Analog:** `SR/skill_classify.py:112-131` `classify`.

```python
entry = jev_names.find_jev(env, own_root)
if entry is None:
    out["jev"] = "absent"
    return out
...
answers = jev_names.ask_items(entry, items, env, functools.partial(run, cwd=cwd), strict=True)
```

Item builder to copy: `jev_names.class_item(index, model_name, summary)` (96-103; `criteria` = one key per class, context
`Known facts: {summary}` capped by `CONTEXT_CHARS`); `ask_items` returns `{id: (choice, top, reason)}` where reason is one of
`""`, `low`, `no answer`, `old`, `failed`, `timeout`; keep the choice only if it is `haiku`/`sonnet` and reason is empty,
else leave the session model (D-03). Test fakes: `tests/test_catalog_jev_names.py` (101-146): `run` lambda returning
`subprocess.CompletedProcess([], 0, stdout=json.dumps({"items": {"n0": {"decided_by": "fake", "fake": {"choice": ..., "top": 0.9}}}}), stderr="")`;
no-jev case: `find_jev({"HOME": scratch})` returns None (`test_find_jev_default_root`, line 56). `skill_classify` tests live in
`tests/test_jev_review.py`. Summaries only: no task text to jev.

### 7. spec-config execute-role question and writer

**Analog:** `skills/ai-kit-spec-config/references/free-lanes.md` section b (line 19-25):
"Is `<key>` usage-limited ... (1) yes, (2) no, (3) not sure." Only a yes writes `usage_limited = true`; no, not sure or skip writes nothing.
`SKILL.md` Step 2 (181-351) is the Ask step; the NEVER list line 45 names the three flags that need an explicit owner yes: add the
new flag there. Reference docs of the written shape: `references/config-file.md` lines 52, 117, 140-149 (flag list and TOML example).
There is no separate writer: lane dicts go through `lane_settings.normalise_lane_settings` / `validate_lane_settings` (item 1) and
the existing config write path (`SR/config_io.py`, `toml_splice`). Tests: `tests/test_spec_config_flow_text.py` (e.g.
`FLAG_LINE = "Only a yes writes ..."` line 79, NEVER-line pin at 278), `tests/test_spec_config_lane_json.py`,
`tests/test_toml_splice.py`, `tests/test_config_role_write.py`. Execute-role step: asked per execute lane, off by default.

### 8. Doc-contract tests (one definition per section)

**Analog:** `tests/test_ai_kit_spec_superpowers.py:3293-3325` `TestPinnedResumeAndReturnCode69OneRule`.

```python
@staticmethod
def _flat(path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())
...
self.assertIn("with a restored `$FIX_ROUND >= 4` and no `injection_json`", state)
self.assertNotIn("a resume that re-enters Step 2", skill)
```

Count style: `text.count("classify-dispatch-failure") == 1` (line 1085-1087), and `text.count("\n## ") == len(SECTIONS)` in
`tests/test_lane_failure_text.py:106` with its helpers `section(text, heading)` (71) and `table_keys` (77). Helpers `_SUPER_REFS`
and `_super_text()` are defined at the top of the superpowers test. For D-01 add one marker heading per topic and assert
`count(marker) == 1` across SKILL.md plus every `references/*.md` (glob, never a fixed list). New `tests/test_*.py` files join
the `unit` group automatically but the Makefile listing (line 12, a generated comment) goes stale: run
`python3 tools/gen_test_groups.py`; `tests/test_gate_scope.py` fails while stale.

### 9. `evals/evals.json`

**Analog:** the file itself; shape pinned by `tests/test_skill_evals_shape.py:19`
(`EVAL_KEYS = {"id", "prompt", "expected_output", "files", "assertions"}`) and the files rule at lines 57-63: every `files`
entry is a string starting with `evals/files/` (empty list allowed, as `precise-external-cli-pair` has `"files": []`).

```json
{ "id": "precise-fold-after-review", "prompt": "...", "expected_output": "...",
  "files": [], "assertions": ["...", "..."] }
```

Existing ids use `casual-*` / `precise-*` prefixes. A fixture needed by a new eval goes under
`skills/ai-kit-spec-execute-superpowers/evals/files/` (e.g. `plan-two-features.md` is there), repo-relative paths in prompts.

## Shared Patterns

- **Flags**: booleans, written only when true, refused when non-boolean with the key named (`lane_settings._bool_setting`, `_problems`).
- **NamedTuple seams**: `CliDeps` (adapter), `runner_dispatch.RunnerSeams(which_fn, env_fn, ...)`, `lane_switch` `deps` (`which_fn`, `env_fn`, `run_fn`, `popen_fn`, `urlopen_fn`); tests inject fakes, never the real host.
- **`register_parsers(sub)` + `COMMANDS`** in `SR` modules (`lane_switch.py:289-300`; same in `skill_classify.py`, `jev_review.py`, `propose_cmds.py`); adapter uses `_build_parser` + `_COMMANDS`.
- **Banner blocks**: `# ── Title ──` section comments in `SR` modules (`lane_settings.py:76`); `tests/test_arch.py` enforces the stricter banner rules for status-line modules only.
- **Test isolation**: scratch HOME + `AI_KIT_REFUSE_REAL_HOME=1`, host CLI stubs on PATH, synthetic content only; fake lanes and `placeholder-model-N` ids.

## No Analog Found

| File | Reason |
|---|---|
| host-config mtime snapshot/diff | no existing `st_mtime_ns` snapshot helper |
| "inside an ai-kit checkout" marker | nothing detects it today; fixed at plan time with held-out fixtures |

## Metadata

**Search scope:** `skills/ai-kit-spec-review/ai_kit_spec`, `skills/ai-kit-spec-execute-superpowers`, `skills/ai-kit-spec-config`, `tools/setup.py`, `tests/`.
**Pattern extraction date:** 2026-11-25
