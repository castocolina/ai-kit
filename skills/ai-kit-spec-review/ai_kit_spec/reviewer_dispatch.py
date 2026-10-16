"""Direct dispatch for ai-kit-spec-review's own external-CLI reviewer entries -- wraps
dispatch.dispatch_with_polling with the review-specific prompt composition (tooling guidance
only; no model-selection-override/incremental-progress/failure-reporting reinforcement, since
a reviewer's own checklist skill (ai-kit-spec-review-checklist) already owns that contract).
Read-only by construction: the command this module runs is always rendered from a review-mode
`command` template (built by commands.build_reviewer_command and stored on the reviewer entry),
never an execute-mode one -- this module itself has no read/write distinction to enforce, that
lives entirely in which builder produced the entry's `command` before it ever reaches here."""
from collections.abc import Callable
from typing import Any, NamedTuple

from ai_kit_spec.commands import ResolvedReviewer, render_reviewer_command
from ai_kit_spec.detection import check_codegraph_mcp_usable
from ai_kit_spec.dispatch import dispatch_with_polling
from ai_kit_spec.tooling_guidance import (
    build_tooling_guidance,
    resolve_shared_tooling_reference_path,
)


class ReviewerSeams(NamedTuple):
    dispatch_fn: Callable[..., dict] = dispatch_with_polling
    build_tooling_guidance_fn: Callable[..., str] = build_tooling_guidance
    resolve_shared_reference_fn: Callable[[], Any] = resolve_shared_tooling_reference_path
    render_command_fn: Callable[..., list[str]] = render_reviewer_command
    codegraph_health_fn: Callable[[Any], bool] = check_codegraph_mcp_usable


class ReviewerDispatchSpec(NamedTuple):
    reviewer_entry: dict
    prompt: str
    timeout_tiers: list[int]
    tool_availability: dict
    agents_tooling_path: object = None


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


def dispatch_reviewer(
    spec: ReviewerDispatchSpec,
    seams: ReviewerSeams | None = None,
) -> dict:
    """Compose the reviewer prompt and run the entry's command via dispatch_with_polling."""
    active = seams or ReviewerSeams()
    runtime, full_prompt = _reviewer_full_prompt(spec, active)
    entry = spec.reviewer_entry
    resolved = ResolvedReviewer(
        key=entry.get("key", ""),
        model=entry.get("model", ""),
        vendor=entry.get("vendor", ""),
        runtime=runtime,
        command=entry.get("command"),
        extra=entry.get("extra") or {},
    )
    command = active.render_command_fn(resolved, full_prompt)
    return active.dispatch_fn(command, full_prompt, spec.timeout_tiers)
