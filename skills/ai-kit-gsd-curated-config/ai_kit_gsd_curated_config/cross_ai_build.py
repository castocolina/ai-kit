"""Builds the fully-rendered `workflow.cross_ai_command` string for execution delegation
(D-04/D-05, 07-CONTEXT.md), reusing `ai_kit_spec.commands.build_execute_command` -- the
already-live-verified per-CLI execute-mode command-string factory -- instead of hand-writing
opencode/cursor-agent invocation syntax. Mirrors `ai_kit_spec_gsd/gsd_cross_ai.py`'s own
thin-wrapper pattern (catch `ValueError`, return `None`) as a self-contained function -- this
module does NOT import from `ai_kit_spec_gsd`, a sibling skill with its own separate
install-root resolution, not a dependency of this skill.

The `sys.path`-injection-via-`model_detect.resolve_ai_kit_spec_path` pattern this module uses to
import `build_execute_command` is the SAME one `preference_match.py` already established -- no
second, divergent resolution strategy for the same sibling skill. The import is wrapped in
`try/except ImportError` (same pattern as `preference_match.py`): `ai_kit_spec` is not a
declared dependency, so its absence must degrade `build_execution_command` to its own
documented `None` return, never crash the whole CLI at import time.
"""
import os
import sys

from . import model_detect

_THIS_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ai_kit_spec_shim = model_detect.resolve_ai_kit_spec_path(_THIS_SKILL_DIR)
if _ai_kit_spec_shim is not None:
    _ai_kit_spec_skill_dir = os.path.dirname(_ai_kit_spec_shim)
    if _ai_kit_spec_skill_dir not in sys.path:
        sys.path.insert(0, _ai_kit_spec_skill_dir)

try:
    from ai_kit_spec.commands import build_execute_command  # pyright: ignore
except ImportError:
    # `ai_kit_spec` is a best-effort sibling, never a hard dependency (module docstring above):
    # if its skill directory can't be resolved, or the sibling install is missing/broken, this
    # skill must keep working rather than take the whole CLI down at import time.
    # `build_execution_command` below checks for this sentinel and returns `None` (its own
    # documented "no match" contract) instead of calling it.
    build_execute_command = None  # pyright: ignore[reportAssignmentType]

# The only three CLI names this plan's two ladders can ever resolve to. Looking up any other
# key raises KeyError -- never silently substitutes the raw CLI name as a fallback slug, which
# would write an invalid key config-set would reject anyway. Note cursor-agent maps to the
# SHORTER slug "cursor", never the raw CLI binary name (confirmed live against
# capability-registry.cjs's real reviewer-slug vocabulary).
CLI_TO_REVIEWER_SLUG = {"opencode": "opencode", "cursor-agent": "cursor", "claude": "claude"}


def build_execution_command(cli, model, project_dir, execute_command_fn=build_execute_command):
    """Returns the fully-rendered command string (no unfilled `{model}` placeholder remaining)
    when `execute_command_fn` successfully returns a template for `cli`; returns `None` (never
    raises) when `execute_command_fn` raises `ValueError` for an unimplemented CLI. The returned
    string never contains `project_dir` rendered as anything other than `shlex.quote`d --
    delegated entirely to `execute_command_fn`; this function itself never re-quotes or
    re-escapes it. Also returns `None` when `execute_command_fn` is the `None` sentinel (the
    `ai_kit_spec` import failed at module load -- graceful degradation, never a crash)."""
    if execute_command_fn is None:
        return None
    try:
        template = execute_command_fn(cli, target_dir=project_dir)
    except ValueError:
        return None
    return template.format(model=model)
