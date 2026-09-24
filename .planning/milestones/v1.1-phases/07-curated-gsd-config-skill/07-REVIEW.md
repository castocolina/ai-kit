---
phase: 07-curated-gsd-config-skill
reviewed: 2026-09-11T08:23:20Z
depth: deep
files_reviewed: 12
files_reviewed_list:
  - skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/__init__.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_write.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/critical_agents.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/model_detect.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/preference_match.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/claude_md_detect.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/frontend_detect.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/workflow_defaults.py
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - tests/test_ai_kit_gsd_curated_config.py
findings:
  critical: 2
  warning: 4
  info: 1
  total: 7
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-09-11T08:23:20Z
**Depth:** deep
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the full `skills/ai-kit-gsd-curated-config/` package plus its 87-case
test module against the locked design in `07-CONTEXT.md` and all four
`07-0N-PLAN.md` files. The `gsd_write.py`/`gsd_catalog.py`/`critical_agents.py`
core (D-01, D-03) is genuinely well-built: every config write does go through
`config-set`/`config-new-project` subprocess calls (confirmed by AST scan —
zero `open()` calls on a config path), the boolean `"true"`/`"false"`
coercion is correct and tested, the heavy-tier sweep correctly excludes
`gsd-executor` from the iteration itself (not just a key-level dedupe, closing
the Cycle-2-flagged drift hole), the `re.escape` fix for `"next.js"` is present
and tested, and the D-07 27-key workflow bundle was independently verified
byte-for-value against this repo's own live `.planning/config.json` — every
value matches. Registration in `Makefile`/`.pre-commit-config.yaml`/
`pyproject.toml`/`README.md` under the renamed `ai-kit-gsd-curated-config`
name is complete and consistent (zero leftover `ai_kit_gsd_config` references
anywhere outside `.planning/`), and the full 87-test suite passes clean with
this repo's own `config.json` provably untouched.

However, two live-reproduced bugs undercut the phase's own stated design
goals badly enough to block: (1) importing `cli.py` unconditionally imports
`ai_kit_spec` at module scope with no fallback, so if the sibling
`ai-kit-spec-review` skill cannot be located, **every** subcommand — including
ones that have nothing to do with model detection, like `ensure-project` —
raises `ModuleNotFoundError` before argument parsing even begins; and (2)
`apply-execution --cli <x>` called without `--model` silently writes a
`workflow.cross_ai_command` containing the literal substring `None` as the
model id, reporting `cross_ai_command_written: true` and exit 0 — a fabricated,
broken command reported as success, which is exactly what D-05's "never a
fabricated command" guarantee exists to prevent. Both are demonstrated live
below, not asserted from reading alone.

## Critical Issues

### CR-01: Missing sibling skill crashes the ENTIRE CLI at import time, not just model-detection subcommands

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/preference_match.py:22-28`, `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py:19-25`

**Issue:** Both modules perform `from ai_kit_spec.<module> import <name>` at
module import time, gated only by `if _ai_kit_spec_shim is not None:
sys.path.insert(...)`. When `model_detect.resolve_ai_kit_spec_path` returns
`None` (the sibling `ai-kit-spec-review` skill isn't installed under any of
the three candidate locations — a real, plausible state if this skill is ever
distributed/installed independently, since `07-02-PLAN.md`'s own
`tracked_source_paths` note says `ai_kit_spec` "has no declared dependency
contract for being imported by a sibling skill"), `sys.path` is never
extended, and the unconditional `from ai_kit_spec... import ...` line right
below raises `ModuleNotFoundError`. Because `cli.py` does
`from . import (..., preference_match, cross_ai_build, ...)` at its own
top level, this exception propagates through `cli.py`'s import, meaning
**every single subcommand** — `ensure-project`, `apply-profile`,
`apply-critical-agents`, `apply-claude-md-path`, `apply-workflow-defaults` —
becomes entirely unusable, even though none of those five need `ai_kit_spec`
at all. This directly contradicts the "reasonable graceful degradation, not a
hard failure" principle 07-CONTEXT.md's Claude's Discretion section states for
exactly this dependency, and it is far worse than the documented failure mode
(a no-match detection result) — it is a total import-time crash of the whole
package. Live-reproduced:

```
$ python3 -c "
import os
real_isdir = os.path.isdir
os.path.isdir = lambda p: False if 'ai-kit-spec-review' in p else real_isdir(p)
from ai_kit_gsd_curated_config import cli
"
ModuleNotFoundError: No module named 'ai_kit_spec'
```

No test in `tests/test_ai_kit_gsd_curated_config.py` exercises this scenario
(`grep -n "ModuleNotFoundError\|ImportError" tests/...` returns nothing).

**Fix:** Wrap the `from ai_kit_spec... import ...` lines in both modules in a
`try/except ImportError` that falls back to a local, in-module implementation
(for `_hint_matches`, a two-line `re.search` equivalent already exists as
precedent in `frontend_detect.py`'s own `_hint_matches`; for
`build_execute_command`, degrade `build_execution_command` to always return
`None`) rather than letting the bare import raise. This preserves detection
functionality when the sibling skill IS present and degrades the
detection-only subcommands gracefully — without taking down the other nine
subcommands — when it is not.

### CR-02: `apply-execution --cli <x>` without `--model` silently writes a broken `cross_ai_command` containing the literal string "None", reported as success

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:179-197`

**Issue:** `_cmd_apply_execution` only checks `if not args.cli:` before
calling `cross_ai_build.build_execution_command(args.cli, args.model,
args.project_dir)` — it never checks `args.model`. `argparse` also places no
`required-together` constraint between `--cli`/`--model` (both individually
`default=None`). If `--cli` is supplied without `--model` (a caller mistake,
or a bug in whatever orchestrates this skill), `build_execution_command` calls
`template.format(model=None)`, which happily renders the Python `None` as the
literal substring `"None"` in the command string — this is NOT `None` the
value (which `build_execution_command`'s own `None`-on-`ValueError` contract
would have caught), it's a real, non-`None`, syntactically valid-looking
command string that gets written straight to `workflow.cross_ai_command`, and
the summary reports `cross_ai_command_written: true, degraded_reason: null` —
a **complete success**, not a degrade. Live-reproduced:

```
$ python3 -c "... cli.main(['apply-execution','--project-dir','/tmp/x','--cli','opencode'], ...)"
exit 0
{"cross_ai_execution_written": true, "cross_ai_command_written": true, "degraded_reason": null}
config-set call: workflow.cross_ai_command = "opencode run -m None --dir /tmp/x --auto"
```

This directly violates 07-CONTEXT.md D-05 ("never a fabricated command") and
the skill's own SKILL.md NEVER section ("Never bake a resolved absolute path
into `workflow.cross_ai_command`" — the spirit of that guarantee is "never
write a command that doesn't correspond to something real"; a literal `None`
model id is exactly that). No test in `TestApplyExecutionCli` covers a
`--cli`-without-`--model` invocation — only the fully-paired and
fully-omitted cases are tested.

**Fix:** Treat `--cli`/`--model` as required-together in `_cmd_apply_execution`:

```python
if not args.cli or not args.model:
    degraded_reason = "no_candidate"
else:
    command = cross_ai_build.build_execution_command(args.cli, args.model, args.project_dir)
    ...
```

Add a test asserting that `--cli` alone (no `--model`) produces
`cross_ai_command_written: false` and no `config-set workflow.cross_ai_command`
call.

## Warnings

### WR-01: `apply-review`'s reviewer-slug lookup raises an unhandled `KeyError` for any unrecognized `--cli`, breaking the CLI's otherwise-consistent error-handling discipline

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:233`

**Issue:** `slug = cross_ai_build.CLI_TO_REVIEWER_SLUG[args.cli]` is a bare
dict subscript with no `try/except` and no `choices=` restriction on
`p_apply_review.add_argument("--cli", required=True)` (cli.py:392). Every
other subcommand in this file resolves errors into a clean stderr message
plus a documented exit code (`_resolve_node_and_gsd_tools`'s `error` tuple
pattern, `apply-profile`'s `choices=` rejection). `apply-execution`'s
equivalent risk is already handled gracefully — `build_execute_command`
raises `ValueError` for an unknown cli, which `cross_ai_build.
build_execution_command` catches and turns into a clean `None` — but
`apply-review`'s slug lookup has no equivalent guard, so a caller passing any
`--cli` value outside `{"opencode", "cursor-agent", "claude"}` (a typo, or a
future `detect-review-candidate` rule producing a fourth CLI name) crashes
with a raw Python traceback and Python's default exit code instead of the
CLI's own documented `2`/`1` failure shapes.

**Fix:** Add `choices=("opencode", "cursor-agent", "claude")` to
`p_apply_review`'s `--cli` argument (argparse will then produce a clean usage
error), or wrap the lookup: `slug = cross_ai_build.CLI_TO_REVIEWER_SLUG.get(args.cli)`
followed by an explicit stderr message + exit 1 when `slug is None`.

### WR-02: `frontend_detect.detect_frontend_present` can raise `ValueError` on a syntactically-valid-but-atypically-shaped `package.json`, violating its own documented "never raises" contract

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/frontend_detect.py:50-51`

**Issue:** `_package_json_signals_frontend` only wraps the `json.loads` call
in `try/except (json.JSONDecodeError, OSError)`; the subsequent
`deps.update(manifest.get("dependencies") or {})` /
`deps.update(manifest.get("devDependencies") or {})` calls are unguarded. If
`dependencies` (or `devDependencies`) parses as valid JSON but is a list or
string rather than an object — a real-world possibility for a hand-edited or
templated `package.json` — `dict.update()` on a non-mapping iterable raises
`ValueError`, not the documented "no signal, never raises" degrade. The
module's own docstring explicitly promises "Never raises on missing/malformed
input... a `package.json` that fails to parse degrades to 'no signal', never
an exception the caller has to catch," and this promise is broken. Live-
reproduced:

```python
>>> detect_frontend_present("/proj", isfile_fn, lambda p: '{"dependencies": ["react"]}')
ValueError: dictionary update sequence element #0 has length 5; 2 is required
```

`detect-frontend`'s CLI wrapper (`_cmd_detect_frontend`, `cli.py:272-275`) has
no exception handling either, so this crashes that subcommand entirely.

**Fix:** Validate the type before merging:

```python
deps_raw = manifest.get("dependencies")
if isinstance(deps_raw, dict):
    deps.update(deps_raw)
dev_deps_raw = manifest.get("devDependencies")
if isinstance(dev_deps_raw, dict):
    deps.update(dev_deps_raw)
```

### WR-03: `apply-review`'s reviewer-list merge assumes `config_get`'s result is a list without checking, risking silent corruption on a malformed pre-existing value

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:237`

**Issue:** `reviewers = list(existing) if existing else []`. `gsd_write.
config_get`'s own docstring documents that a non-`--raw` `config-get` on a
scalar (string) value decodes cleanly via `json.loads` — meaning if
`review.default_reviewers` were ever present in a target project's
`config.json` as a bare string (e.g. `"opencode"`, from a hand-edit, an older
schema version, or an unrelated bug elsewhere) rather than an array,
`json.loads('"opencode"')` returns the Python string `"opencode"`, and
`list("opencode")` explodes it into `['o','p','e','n','c','o','d','e']` — the
merge then treats each character as an independent "existing reviewer,"
silently corrupting the write. This is a real, if low-probability, gap in the
defensive type-checking `gsd_write.py`'s own module docstring shows this
codebase is otherwise careful about (e.g. its extensive discussion of exactly
this raw-vs-non-raw array-shape hazard for `config-get`).

**Fix:** `reviewers = list(existing) if isinstance(existing, list) else []`.

### WR-04: Untested degrade branches leave real bugs unguarded by the test suite

**File:** `tests/test_ai_kit_gsd_curated_config.py` (`TestApplyExecutionCli`, lines 742-798)

**Issue:** `_cmd_apply_execution`'s `degraded_reason == "no_builder"` branch
(cli.py:184) has zero test coverage — `grep -n "no_builder"
tests/test_ai_kit_gsd_curated_config.py` returns nothing. Combined with the
missing `--cli`-without-`--model` case (see CR-02), the test suite's
`TestApplyExecutionCli` class exercises only the two "both present" /
"both absent" corners of a 2×2 flag-presence matrix that has four corners.
Both of the untested corners correspond to real code paths, and one of them
(CR-02) is an active bug.

**Fix:** Add `test_partial_candidate_cli_without_model_is_not_written` (`--cli`
given, `--model` omitted — asserts `cross_ai_command_written: False` once
CR-02 is fixed) and `test_unimplemented_builder_degrades` (inject a
`build_execution_command` fake returning `None` — asserts
`degraded_reason == "no_builder"`).

## Info

### IN-01: `preference_match.py` and `cross_ai_build.py` each independently perform the same real-filesystem `sys.path` mutation as a module-import side effect

**File:** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/preference_match.py:21-26`, `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py:18-23`

**Issue:** Both modules call `model_detect.resolve_ai_kit_spec_path(...)` and
conditionally `sys.path.insert(0, ...)` at module scope (not inside a
function), meaning simply *importing* either module walks the real
filesystem and mutates global interpreter state before any subcommand
executes. This is a known, deliberate, documented pattern (both modules cite
it explicitly and it mirrors an existing convention in
`ai-kit-spec-execute-gsd`), but doing it twice (once per module, redundantly)
and doing it as an import-time side effect rather than inside a
lazily-invoked resolver function is a minor architectural smell — it's also
the direct mechanism behind CR-01 (an import-time crash has no chance to be
caught by a caller, since it fires before any of this package's own
try/except logic ever runs).

**Fix:** Not urgent on its own; if CR-01 is fixed by moving the `ai_kit_spec`
import inside a lazily-called function (rather than a bare module-level
`try/except ImportError`), this redundancy disappears as a side effect of
that fix.

---

_Reviewed: 2026-09-11T08:23:20Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
