"""The string GSD stores as `workflow.cross_ai_command` (D-26, D-27, D-30).

It names the project's own supervised runner (`.planning/scripts/cross-ai.mjs`), never an
installed path and never a raw vendor CLI: GSD's own `cross_ai_delegation` step pipes the task
prompt into that hook and captures its stdout. Codex is confined with `--codex-sandbox
workspace-write`. The guidance file is placed before the prompt and the runner's own preamble
is off, so nothing is said twice.
"""
from ai_kit_spec.runner_dispatch import RunnerSpec, project_runner_command


def build_cross_ai_command(resolved_candidate: dict):
    """The project-root-relative hook string, or None when no safe hook can be built.

    The hook is relative to the project root GSD runs it from. A native candidate (`runtime`
    None) needs no hook, and a runtime the runner cannot execute (or a token GSD's unquoted
    expansion cannot carry) returns None instead of a broken string."""
    runtime = resolved_candidate["runtime"]
    if runtime is None:
        return None  # true native (current-session) dispatch -- no hook needed
    spec = RunnerSpec(
        runtime, resolved_candidate["model"], "exec", 0,
        effort=resolved_candidate.get("effort"),
        service_tier=resolved_candidate.get("service_tier"),
    )
    return project_runner_command(spec, guidance=True)
