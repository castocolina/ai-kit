# Phase 26: Session self-resume and OpenGSD quota rules - Pattern Map

**Mapped:** 2026-10-25
**Files analyzed:** 27 (new and modified)
**Analogs found:** 25 / 27
All analog paths below are git-tracked (checked with `git ls-files`). Line numbers are from the worktree at mapping time.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `skills/ai-kit-session-wake/ai-kit-session-wake.py` | shim | request-response | `skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py` | exact |
| `skills/ai-kit-session-wake/SKILL.md` | skill doc | n/a | `skills/ai-kit-project-rules-agents/SKILL.md` | role |
| `ai_kit_session_wake/cli.py` | controller (dispatcher) | request-response | `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py` | role |
| `ai_kit_session_wake/state.py` | model/store | file-I/O | `skills/_shared/ai_kit_rules_common/stack_cache.py` | exact (writer) |
| `ai_kit_session_wake/liveness.py` | utility | file-I/O (/proc) | `skills/ai-kit-spec-review/ai_kit_spec/detection.py` (env/PATH seams) | partial |
| `ai_kit_session_wake/hosts.py` | config table | transform | `detection.py` `RUNTIMES` / `detect_current_runtime` | role |
| `ai_kit_session_wake/units.py` | service | file-I/O + subprocess | `ai_kit_spec/gsd_tools.py` (injected callables) | partial |
| `ai_kit_session_wake/fire.py` | service | event-driven | `ai_kit_spec/gsd_tools.py` (seams) + `stack_cache` flock-free writer | partial |
| `ai_kit_session_wake/matrix.py`, `reset_parse.py` | utility | transform | `ai_kit_spec/gsd_tools.py` (pure fns, NamedTuple results) | partial |
| `skills/_shared/ai_kit_rules_common/gsd_identity.py` | utility | request-response (subprocess) | `ai_kit_spec/gsd_tools.py` `resolve_gsd_tools` | role |
| `skills/_shared/ai_kit_rules_common/classification.py` (mod) | utility | transform | itself, lines 14-23 | exact |
| `.../remediation.py` (mod, `notices`, `verbatim`) | utility | transform | itself | exact |
| `skills/_shared/ai_kit_rules_common/tool_catalog.py` (mod, R20 table) | config | transform | `OUT_OF_TAXONOMY_GROUPS` in same file | exact |
| `skills/ai-kit-project-rules-agents/.../rules.py` (mod, R18-R20) | config | transform | R17 entry, lines 235-246 | exact |
| `.../ai_kit_project_rules_agents/cli.py` (mod, merge `opengsd` presence) | controller | request-response | itself, `check` lines 157-164 | exact |
| `skills/ai-kit-project-rules-all/.../aggregate.py` (mod, merge `notices`) | controller | batch | itself, lines 40-60 | exact |
| `skills/ai-kit-spec-review/references/cross-ai.mjs` (mod, `AI_KIT_CROSS_AI_CHILD`) | utility | request-response | `childEnv` line 3638 | exact |
| `skills/ai-kit-spec-execute-gsd/SKILL.md`, `-superpowers/SKILL.md` (mod) | skill doc | n/a | themselves + `tests/test_quota_policy_text.py` constraints | exact |
| `tools/setup.py` (mod: `HOOK_REGISTRY` row, `HOOK_SUMMARIES`, `PI_SKILLS`) | config | n/a | rows at 1766-1790; line 47 | exact |
| `tools/hooks/claude_session_wake.py` | hook | event-driven | `tools/hooks/claude_tool_reminder.py` | exact |
| `pyproject.toml` (pyright `extraPaths`) | config | n/a | existing `extraPaths` entries | exact |
| `tests/test_ai_kit_session_wake.py` (+ splits) | test | n/a | `tests/test_ai_kit_project_rules_agents.py` fixtures lines 30-53 | exact |
| `tests/test_arch.py` (mod, new class + non-vacuity) | test | AST | `TestArchNonVacuity` line 1345; `check_*` helpers 454-530 | exact |
| `tests/test_quota_policy_text.py` (existing, must stay green) | test | text | itself, lines 36-60 | n/a |
| Makefile/pre-commit lists | generated | n/a | run `python3 tools/gen_test_groups.py`, never hand-edit | n/a |
| `README.md:39`, `rules.py:1`, `rule_checker.py:9`, agents `SKILL.md:3,10`, makefile `SKILL.md:17` ("17 rules" -> 19/20) | docs | n/a | grep strings | exact |

## Pattern Assignments

### Shim `skills/ai-kit-session-wake/ai-kit-session-wake.py`
**Analog:** `skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py` (lines 11-21; sibling `sys.path` insert so `ai_kit_spec` resolves)
```python
import importlib
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, "..", "ai-kit-spec-review"))

main = importlib.import_module("ai_kit_spec_gsd.cli").main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```
Minimal alternative (no sibling) is `skills/ai-kit-project-rules-agents/ai-kit-project-rules-agents.py` (7 lines, `from ...cli import main; sys.exit(main(sys.argv[1:]))`). Use the first only if `hosts.py` imports `RUNTIMES` from `ai_kit_spec.detection`.

### `cli.py` (six subcommands, argparse-free dispatcher)
**Analog:** `ai_kit_project_rules_agents/cli.py` (`check`/`remediate` return dicts at 157-170; `main(argv: list[str]) -> int` at 171). Copy the `main(argv) -> int` signature and dict-returning handlers; handlers take seams (`run_fn`, `which_fn`, `now_fn`, `env`) as keyword defaults.

### `state.py` (atomic JSON, mkstemp + fsync + replace)
**Analog:** `skills/_shared/ai_kit_rules_common/stack_cache.py` lines 96-118. Do not import it (`_shared` is unreachable on copy installs, D-01); copy the body, and drop the wrapper payload.
```python
fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
except OSError:
    with contextlib.suppress(OSError):
        os.unlink(tmp)
    raise
```
Project rule also names `_read_json_checked()` / `_atomic_write_json()` in `tools/setup.py` for runtime-config writes; wake state is ai-kit's own file, so the stack_cache copy is the right shape. flock: stdlib `fcntl.flock(fd, LOCK_EX | LOCK_NB)` (no analog in repo; see No Analog).

### `hosts.py`
**Analog:** `ai_kit_spec/detection.py` `RUNTIMES` table and `detect_current_runtime` (line 231; fixed order pi > opencode > cursor > codex > claude, truthiness `if env.get(var):`). Key rows by runtime label (D-04); do not edit `RUNTIMES` (single source of truth, `KNOWN_CLIS` lacks `pi`). Resume argv table values come from CONTEXT D-15 as amended by spike 003 (pi: `-p --session-id <id>`).

### Seams (liveness, units, fire, matrix, reset_parse)
**Analog:** `ai_kit_spec/gsd_tools.py:117-133`; every effect is an injected callable with a real default.
```python
def resolve_gsd_tools(
    env: Mapping[str, str] | None = None,
    start: str | None = None,
    isfile_fn: Callable[[str], bool] = os.path.isfile,
    run_fn: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    which_fn: Callable[..., str | None] = shutil.which,
) -> str | None:
    env = env if env is not None else dict(os.environ)
    ...
```
Results as `NamedTuple` (`GsdTools`, line 136). Respect pylint caps: max-args 5, max-branches 12, max-statements 50 (use keyword-only seam bundles or a small dataclass to stay under 5 args).

### `gsd_identity.py` (probe -> `ok | unverified | absent`)
**Analog:** `resolve_gsd_tools` above (shape of seams). Per RESEARCH Q5 option (a): take the resolved tools path as an argument; the agents `cli.py` does the sibling import of `ai_kit_spec.gsd_tools` (pattern already used by `ai_kit_gsd_curated_config.model_detect.resolve_ai_kit_spec_path`). Keep `_shared` dependency-free. Strict parse: `json.loads`, dict, `packageName == "@opengsd/gsd-core"`; other valid JSON -> `absent`; non-zero exit/timeout/invalid -> `unverified`. Do not touch `check_tool_presence` (hermetic, `test_ai_kit_rules_common.py:148-154`).

### `classification.py` (condition tri-state)
**Analog / edit site:** lines 14-23.
```python
CONDITION_ALWAYS = "always"

def evaluate_condition(condition: str, tool_presence: dict) -> bool:
    if condition == CONDITION_ALWAYS:
        return True
    if condition.startswith("tool-presence:"):
        name = condition.split(":", 1)[1]
        return bool(tool_presence.get(name, False))
    return False   # unknown condition -> silently False; `opengsd` must not land here
```
Add `opengsd` (reads `presence["opengsd"]`) and `stack-detected`; `check_rules` emits `{"status": "not_applicable", "unverified": True, "reason": ...}` for `unverified`. Tool-scoped groups hard-code the `modern-cli:` prefix in `_classify_tool_scoped_groups`; generalise, do not add per-language branches.

### `rules.py` R18/R19/R20
**Analog:** R17 entry (lines 235-246), the last tuple element; dict keys `id, category, criticality, condition, signals, summary`.
```python
{
    "id": "R17",
    "category": "workflow",
    "criticality": CRITICALITY_MEDIUM,
    "condition": CONDITION_ALWAYS,
    "signals": ("concise", "no excess documentation", "narrative"),
    "summary": ("..."),
},
```
R18: `CRITICALITY_HIGH`, `"condition": "opengsd"`, flat signals `("session wake", "self-resume", "resume by session id")`, plus `"verbatim": True` where fixed. R19: plain groups (tuple of tuples, R04 shape), derived from the `## Pointer for instruction files` block in `subprocess-quota-policy.md` (lines ~171-180), summary equals that pointer; add the repo-only sync test. R20: condition `stack-detected`.

### `remediation.py` / `aggregate.py` (`notices`)
**Analog:** `aggregate.py` 40-60 merges `remediate`/`blocked`/`failed` via `.extend`, then sorts by `criticality`; add `notices` the same way (additive key, check `test_returns_dict_never_bare_list`). `remediation.py` currently skips `not_applicable`; copy `unverified` ones into `report["notices"]` and carry `verbatim` into the entry.

### `cross-ai.mjs` child marker
**Analog:** `childEnv(extra, baseEnv)` at line 3638 (`{...baseEnv, ...extra}`, then scrub). Set `AI_KIT_CROSS_AI_CHILD: '1'` through the runtime `env` (`rt.env`, used at 3884 and 10301) or in `childEnv` itself so every child inherits it; make sure `CONFIG.scrubEnv` does not remove it. Both call sites (3884 spawn, 10301 listing) go through `childEnv`, so one edit covers both.

### `tools/hooks/claude_session_wake.py` (StopFailure hook)
**Analog:** `tools/hooks/claude_tool_reminder.py` lines 1-34; fail-open `sys.excepthook`, `os._exit(0)`, stdlib only, `read_stdin` from `claude_session_start`. Replace the advisor call with: parse stdin JSON (`session_id`, `error`, `error_details`, `last_assistant_message`) and call `ai-kit-session-wake arm --reset-text ...` via `subprocess.run` (no `shell=True`; `tests/test_arch.py` has `check_no_shell_true`).

### `tools/setup.py` registry
**Analog:** `HookRow` namedtuple (1733-1736: `id host event matcher script default experimental verdict timeout`) and rows 1766-1790.
```python
HookRow(
    id="tool-advisor", host="claude", event="PreToolUse", matcher="Bash|Read",
    script="tools/hooks/claude_tool_advisor.py", default=True,
    experimental=False, verdict=None, timeout=3),
```
New row: `id="session-wake", host="claude", event="StopFailure", matcher="rate_limit", script="tools/hooks/claude_session_wake.py", default=False, experimental=True, verdict=None, timeout=...`; add `HOOK_SUMMARIES["session-wake"]`. `PI_SKILLS` (line 47) gains `"ai-kit-session-wake"`; update `tests/test_setup.py` and `tests/test_jev_skill_install_e2e.py:69` pi-set expectations, and `tests/test_hook_registry*.py` row pins.

### Executor SKILL.md edits
Add an `arm` step before first dispatch (-gsd: before `Skill(gsd-execute-phase)` when >= 2 PLAN.md; -superpowers: >= 2 tasks) and a final `done` step. Constraint from `tests/test_quota_policy_text.py:36-60`: `WAKE_RE = \bhourly\b|every hour|recurring` and no `CronCreate` line in executor text. Call only `ai-kit-session-wake arm|done`. Both SKILL.md files go through skill-judge.

### Tests
**Fixtures analog:** `tests/test_ai_kit_project_rules_agents.py:33-53`.
```python
def fake_bin(root, names, body):
    os.makedirs(root, exist_ok=True)
    for name in names:
        path = os.path.join(root, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.chmod(path, 0o755)
    return root

def scoped_env(bin_dir, home):
    return {"PATH": bin_dir, "HOME": home,
            "XDG_CONFIG_HOME": os.path.join(home, ".config"),
            "XDG_DATA_HOME": os.path.join(home, ".local", "share"),
            "XDG_CACHE_HOME": os.path.join(home, ".cache")}
```
Add `XDG_STATE_HOME`. Fake `systemctl`/`loginctl`/host CLIs append argv, cwd, env-var names to a log. Never real systemd, never real home. Liveness: real `sleep` child. Overlap: two real `fire` subprocesses.
**Arch analog:** `tests/test_arch.py` `_parse` (341), `_imported_modules` (439), `check_import_direction` (454), `check_no_shell_true` (760); `TestArchNonVacuity` at 1345 feeds synthetic source strings and asserts the checker flags violations and passes clean ones. New rule (D-25): session-wake package never imports `write_resumable_state` or names Phase 25 wait paths; Phase 25 code never imports the wake package. Each gets a violating and a clean synthetic case.
**Registration:** `python3 tools/gen_test_groups.py` then `tests/test_gate_scope.py`; real `node` runs go in `E2E_MODULES`.

## Shared Patterns

### Seams over globals
**Source:** `ai_kit_spec/gsd_tools.py:117-133`. Apply to every new module with effects (systemctl, loginctl, notify-send, /proc, clock).

### Atomic write
**Source:** `stack_cache.py:96-118`. Apply to state, `.done`, and any unit file write.

### Runtime labels and env discrimination
**Source:** `detection.py:231` `detect_current_runtime` (truthy env check). Apply to `hosts.py` and the cross-AI child refusal.

### Fail-open hooks
**Source:** `claude_tool_reminder.py:7-17`. Apply to the StopFailure hook.

### Certainty labelling
Project rule: reverse-engineered or inferred results (reset parse, StopFailure fields, reboot survival, non-Linux liveness) are printed with an `inferred` / `unverified` flag in `arm`, `status`, `matrix`, and notices.

## No Analog Found

| File / concern | Role | Data Flow | Reason |
|---|---|---|---|
| `fcntl.flock` non-blocking lock in `state.py`/`fire.py` | utility | file-I/O | No flock use in repo; use stdlib per RESEARCH "Don't Hand-Roll" |
| `units.py` systemd unit rendering | service | file-I/O | No in-repo unit writer; use RESEARCH Code Examples (verified with `systemd-analyze --user verify`) |
| `liveness.py` `/proc/<pid>/stat` parse | utility | file-I/O | None; RESEARCH "Liveness" example (field 22 after last `)`) |
| `reset_parse.py` (`zoneinfo`) | utility | transform | Phase 25 parser superseded (D-37); own fixtures, labelled inferred |

## Metadata

**Analog search scope:** `skills/`, `skills/_shared/`, `tools/`, `tools/hooks/`, `tests/`
**Files scanned:** about 25 read or grepped
**Pattern extraction date:** 2026-10-25
