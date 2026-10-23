"""Builds the `workflow.cross_ai_command` string for execution delegation (D-26, D-27).

The command is the project-local runner hook from `ai_kit_spec.runner_dispatch`, not a
direct CLI invocation. Mirrors `ai_kit_spec_gsd/gsd_cross_ai.py`'s thin-wrapper pattern
(return `None`, never raise) -- this module does NOT import from `ai_kit_spec_gsd`, a
sibling skill with its own install-root resolution, not a dependency of this skill.

The `sys.path`-injection-via-`model_detect.resolve_ai_kit_spec_path` pattern this module uses
is the SAME one `preference_match.py` already established. The import is wrapped in
`try/except ImportError` (same pattern as `preference_match.py`): its absence must degrade
`build_execution_command` to its own documented `None` return, never crash the whole CLI at
import time. (Every gsd-tools write in `cli.py` does require the sibling, through the shared
`ai_kit_spec.gsd_tools` wrappers (D-18), and exits 2 without it.)
"""
import os
import sys
from collections.abc import Callable
from typing import Any

from . import model_detect

_THIS_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ai_kit_spec_shim = model_detect.resolve_ai_kit_spec_path(_THIS_SKILL_DIR)
if _ai_kit_spec_shim is not None:
    _ai_kit_spec_skill_dir = os.path.dirname(_ai_kit_spec_shim)
    if _ai_kit_spec_skill_dir not in sys.path:
        sys.path.insert(0, _ai_kit_spec_skill_dir)

execute_cli_error: Callable[[str], str | None] | None
runtime_id: Callable[[str], str] | None
project_runner_command: Callable[..., str | None] | None
RunnerSpec: Callable[..., Any] | None

try:
    from ai_kit_spec.commands import execute_cli_error
    from ai_kit_spec.detection import runtime_id
    from ai_kit_spec.runner_dispatch import RunnerSpec, project_runner_command
except ImportError:
    # `ai_kit_spec` is optional at import time (module docstring above): if its skill
    # directory can't be resolved, or the sibling install is missing/broken, this module must
    # not take the whole CLI down at import time.
    # `build_execution_command` below checks for this sentinel and returns `None` (its own
    # documented "no match" contract) instead of calling it. Without the sibling there is no
    # supported-CLI list to validate `--cli` against either, so execute_cli_error is None and
    # the documented `no_builder` degrade path applies. reviewer_slug then keeps the name as
    # given.
    execute_cli_error = None
    runtime_id = None
    project_runner_command = None
    RunnerSpec = None

# Closed reviewer slugs. Unknown names are rejected before any config write.
REVIEWER_SLUGS = ("claude", "cursor", "opencode")


def reviewer_slug(cli) -> str | None:
    """Map a runtime id, or the legacy `cursor-agent` name, onto a reviewer slug."""
    name = cli if runtime_id is None else runtime_id(cli)
    if name in REVIEWER_SLUGS:
        return name
    return None


def reject_execute_cli(cli):
    """Return a rejection message when `cli` is unsupported, else `None`."""
    if execute_cli_error is None:
        return None
    return execute_cli_error(cli)


def build_execution_command(cli, model, project_dir=None, execute_command_fn=None):
    """The project-local runner hook for `cli`, or `None` when it cannot be built.

    `project_dir` is unused: the hook is a project-root-relative path. `execute_command_fn`
    remains only so an injected builder still works; the default builds the runner hook.
    Returns `None` (never raises) when the sibling import failed or the runtime is not an
    execute target."""
    del project_dir
    if execute_command_fn is not None:
        try:
            return execute_command_fn(cli, target_dir="").format(model=model)
        except (ValueError, AttributeError):
            return None
    return _runner_hook(cli, model)


def _runner_hook(cli, model) -> str | None:
    if project_runner_command is None or RunnerSpec is None or runtime_id is None:
        return None
    runtime = runtime_id(cli)
    sandbox = "workspace-write" if runtime == "codex" else None
    return project_runner_command(RunnerSpec(runtime, model, "exec", 0, codex_sandbox=sandbox))


def unsafe_hook_token(cli, model) -> bool:
    """True when the sibling is present but the hook cannot carry `model` (a shell or glob
    character, which GSD's unquoted hook would split or expand); `no_builder` is the absent
    sibling."""
    if project_runner_command is None:
        return False
    return _runner_hook(cli, model) is None
