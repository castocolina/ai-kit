"""Direct dispatch for ai-kit-spec-review's own external reviewer entries.

A table-runtime entry (route `subprocess` or `unverified`) runs through the cross-AI runner in
review mode. A custom entry (a `command` and no runtime, D-21) runs through the fixed-argv
launcher. A `native` route never reaches a subprocess: the host runs it. Tooling guidance is
prefixed onto the prompt; a reviewer's own checklist skill owns the review contract.
"""
from collections.abc import Callable
from typing import Any, NamedTuple

from ai_kit_spec import routing
from ai_kit_spec.commands import ResolvedReviewer, render_reviewer_command
from ai_kit_spec.detection import check_codegraph_mcp_usable
from ai_kit_spec.runner_dispatch import (
    CustomSpec,
    RunnerResult,
    RunnerSeams,
    review_spec,
    run_custom_command,
    run_runner_tiers,
)
from ai_kit_spec.tooling_guidance import (
    build_tooling_guidance,
    resolve_shared_tooling_reference_path,
)


class ReviewerSeams(NamedTuple):
    runner_tiers_fn: Callable[..., RunnerResult] = run_runner_tiers
    custom_fn: Callable[..., RunnerResult] = run_custom_command
    runner_seams: RunnerSeams = RunnerSeams()
    build_tooling_guidance_fn: Callable[..., str] = build_tooling_guidance
    resolve_shared_reference_fn: Callable[[], Any] = resolve_shared_tooling_reference_path
    codegraph_health_fn: Callable[[Any], bool] = check_codegraph_mcp_usable


class ReviewerDispatchSpec(NamedTuple):
    reviewer_entry: dict
    prompt: str
    timeout_tiers: list[int]
    tool_availability: dict
    agents_tooling_path: object = None
    cwd: str | None = None


def _reviewer_full_prompt(
    spec: ReviewerDispatchSpec, seams: ReviewerSeams
) -> tuple[str | None, str]:
    runtime = spec.reviewer_entry.get("runtime")
    codegraph_registered = bool(runtime) and seams.codegraph_health_fn(runtime)
    tooling_guidance = seams.build_tooling_guidance_fn(
        runtime,
        spec.tool_availability or {},
        spec.agents_tooling_path,
        codegraph_registered,
        shared_reference_path=seams.resolve_shared_reference_fn(),
    )
    full_prompt = (tooling_guidance + "\n\n" + spec.prompt) if tooling_guidance else spec.prompt
    return runtime, full_prompt


def _result_dict(result: RunnerResult) -> dict:
    return {
        "stdout": result.stdout, "returncode": result.returncode, "timed_out": result.timed_out,
        "reason": result.reason, "status": result.status, "argv": result.argv,
    }


def _dispatch_runtime(entry: dict, spec: ReviewerDispatchSpec, prompt: str,
                      seams: ReviewerSeams) -> dict:
    runner_spec = review_spec(entry["runtime"], entry["model"], entry.get("extra"),
                              spec.timeout_tiers[0], cwd=spec.cwd)
    result = seams.runner_tiers_fn(runner_spec, spec.timeout_tiers, prompt, seams.runner_seams)
    return _result_dict(result)


def _dispatch_custom(entry: dict, spec: ReviewerDispatchSpec, prompt: str,
                     seams: ReviewerSeams) -> dict:
    resolved = ResolvedReviewer(
        key=entry.get("key", ""), model=entry.get("model", ""), vendor=entry.get("vendor", ""),
        runtime=None, command=entry.get("command"), extra=entry.get("extra") or {},
    )
    custom = CustomSpec(
        resolved.key, render_reviewer_command(resolved, prompt), spec.timeout_tiers, cwd=spec.cwd,
    )
    return _result_dict(seams.custom_fn(custom, prompt, seams.runner_seams))


def dispatch_reviewer(
    spec: ReviewerDispatchSpec,
    seams: ReviewerSeams | None = None,
) -> dict:
    """Compose the reviewer prompt and run the entry through the runner or the launcher."""
    active = seams or ReviewerSeams()
    if not spec.timeout_tiers:
        raise ValueError("timeout_tiers must name at least one tier -- got an empty list")
    runtime, full_prompt = _reviewer_full_prompt(spec, active)
    entry = spec.reviewer_entry
    key = entry.get("key", "")
    if entry.get("route") == "native" or not (runtime or entry.get("command")):
        raise ValueError(
            f"reviewer {key} routes native; the host runs it, not dispatch-reviewer"
        )
    if entry.get("route") in routing.SKIP_ROUTES:
        raise ValueError(f"reviewer {key} route {entry['route']}: not dispatchable")
    if runtime:
        if not entry.get("model"):
            raise ValueError(f"reviewer {key} names runtime {runtime} but no model")
        return _dispatch_runtime(entry, spec, full_prompt, active)
    return _dispatch_custom(entry, spec, full_prompt, active)
