"""Direct dispatch for ai-kit-spec-review's own external reviewer entries.

A table-runtime entry (route `subprocess` or `unverified`) runs through the cross-AI runner in
review mode. A custom entry (a `command` and no runtime, D-21) runs through the fixed-argv
launcher. A `native` route never reaches a subprocess: the host runs it. The lane's capability
block is prefixed onto the prompt; a reviewer's own checklist skill owns the review contract.
"""
import os
from collections.abc import Callable
from typing import NamedTuple

from ai_kit_spec import lane_settings, routing
from ai_kit_spec.capability_block import (
    ComposeResult,
    ComposeSeams,
    LaneRefused,
    LaneRequest,
    cleanup,
    compose_for_lane,
    lane_spec,
    with_block,
)
from ai_kit_spec.commands import ResolvedReviewer, render_reviewer_command
from ai_kit_spec.detection import removed_runtime_message
from ai_kit_spec.runner_dispatch import (
    CustomSpec,
    RunnerResult,
    RunnerSeams,
    review_spec,
    run_custom_command,
    run_runner_tiers,
)


class ReviewerSeams(NamedTuple):
    runner_tiers_fn: Callable[..., RunnerResult] = run_runner_tiers
    custom_fn: Callable[..., RunnerResult] = run_custom_command
    runner_seams: RunnerSeams = RunnerSeams()
    compose_fn: Callable[..., ComposeResult] = compose_for_lane
    compose_seams: ComposeSeams = ComposeSeams()


class ReviewerDispatchSpec(NamedTuple):
    reviewer_entry: dict
    prompt: str
    timeout_tiers: list[int]
    tool_availability: dict
    agents_tooling_path: object = None
    cwd: str | None = None
    files: tuple | None = ()
    # a resumed session a later lane hands the runner; None starts fresh
    session_id: str | None = None


def row_is_native(row: dict) -> bool:
    """A native route, or a row with neither a runtime nor a command: the host runs it."""
    return row.get("route") == "native" or not (row.get("runtime") or row.get("command"))


def row_resolved(row: dict) -> ResolvedReviewer:
    """The ResolvedReviewer of one reviewers.json row."""
    return ResolvedReviewer(key=row.get("key", ""), model=row.get("model", ""),
                            vendor=row.get("vendor", ""), runtime=row.get("runtime"),
                            command=row.get("command"), extra=row.get("extra") or {})


def _reviewer_full_prompt(spec: ReviewerDispatchSpec, seams: ReviewerSeams, runner_spec):
    entry = spec.reviewer_entry
    return seams.compose_fn(
        LaneRequest(entry.get("runtime"), entry.get("model", ""), "review",
                    spec.cwd or os.getcwd(), runner_spec),
        spec.prompt, spec.files, seams.runner_seams.env_fn(), seams.compose_seams)


def _result_dict(result: RunnerResult) -> dict:
    return {
        "stdout": result.stdout, "returncode": result.returncode, "timed_out": result.timed_out,
        "reason": result.reason, "status": result.status, "argv": result.argv,
    }


def _dispatch_runtime(runner_spec, spec: ReviewerDispatchSpec, prompt: str,
                      seams: ReviewerSeams) -> dict:
    result = seams.runner_tiers_fn(runner_spec, spec.timeout_tiers, prompt, seams.runner_seams)
    return _result_dict(result)


def _dispatch_custom(entry: dict, spec: ReviewerDispatchSpec, prompt: str,
                     seams: ReviewerSeams) -> dict:
    resolved = row_resolved(entry)._replace(runtime=None)
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
    entry = spec.reviewer_entry
    runtime = entry.get("runtime")
    key = entry.get("key", "")
    if row_is_native(entry):
        raise ValueError(
            f"reviewer {key} routes native; the host runs it, not dispatch-reviewer"
        )
    removed = removed_runtime_message(runtime)
    if removed is not None:
        raise ValueError(f"reviewer {key}: {removed}")
    if entry.get("route") in routing.SKIP_ROUTES:
        raise ValueError(f"reviewer {key} route {entry['route']}: not dispatchable")
    if runtime and not entry.get("model"):
        raise ValueError(f"reviewer {key} names runtime {runtime} but no model")
    runner_spec = (review_spec(runtime, entry["model"], entry.get("extra"),
                               spec.timeout_tiers[0], cwd=spec.cwd)._replace(
        pool=lane_settings.lane_free_pool(entry.get("extra") or {}),
        session_id=spec.session_id) if runtime else None)
    composed = (_reviewer_full_prompt(spec, active, runner_spec) if spec.prompt.strip()
                else ComposeResult())
    try:
        if composed.refusal:
            raise LaneRefused(composed.refusal)
        if composed.window is not None and composed.window["value"] is None:
            active.runner_seams.print_fn(
                f"ai-kit-spec: window for {runtime}/{entry.get('model')}: unknown "
                f"({composed.window['note'] or composed.window['label']}); not capped")
        prompt = with_block(composed.block, spec.prompt)
        if runner_spec is not None:
            return _dispatch_runtime(lane_spec(runner_spec, composed), spec, prompt, active)
        return _dispatch_custom(entry, spec, prompt, active)
    finally:
        cleanup(composed)
