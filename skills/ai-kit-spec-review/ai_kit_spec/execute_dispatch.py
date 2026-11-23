"""Direct process dispatch for ai-kit-spec-execute's own resolved candidates -- bypasses any
target framework's own config-write/hook indirection (e.g. GSD's workflow.cross_ai_command,
which only exists to tell GSD's OWN execute-phase step what to shell out to, and only fires
after a whole GSD-specific config round-trip). This module IS the dispatch: it composes the
exec guidance (model-selection override, incremental progress, honest failure reporting,
the lane's capability block (capability_block.compose_for_lane), whose soft-confinement
sentence follows the lane's write capability) and runs one candidate through the cross-AI
runner in exec mode (D-11). A native (runtime is None) candidate is never routed here -- it has
no subprocess to dispatch at all; the caller executes it in-process.

The runner runs every exec CLI with full permissions except codex, which runs under
`--codex-sandbox workspace-write` (D-27). That sandbox still allows writes to /tmp and
$TMPDIR regardless of the target dir. Soft confinement is prompt guidance, not a security
boundary (D-27)."""
import os
import shlex
from collections.abc import Callable
from typing import NamedTuple

from ai_kit_spec import runner_facts
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
from ai_kit_spec.commands import execute_cli_error
from ai_kit_spec.detection import runtime_id
from ai_kit_spec.dispatch_guidance import build_dispatch_reinforcement_guidance
from ai_kit_spec.runner_dispatch import (
    EXEC_NOTES,
    RunnerSeams,
    RunnerSpec,
    run_runner,
    spec_with_effort,
    stderr_print,
)


def build_soft_confinement_guidance(target_dir: str) -> str:
    """Prompt guidance for a runtime the runner does not OS-confine (everything outside
    the OS sandbox). Neither cursor nor opencode nor pi has a flag that genuinely confines
    writes, so the only mitigation is telling the dispatched CLI, explicitly, that target_dir
    is the only place it may write. This is guidance, not a security boundary."""
    return (
        f"This dispatch has NO operating-system-level write confinement -- you must never "
        f"write, move, rename, or delete any file outside {target_dir} for any reason, even "
        f"temporarily or as a scratch/backup location. Treat {target_dir} as the only writable "
        f"location that exists."
    )


class ExecuteSeams(NamedTuple):
    runner_fn: Callable = run_runner
    runner_seams: RunnerSeams = RunnerSeams()
    print_fn: Callable[[str], None] = stderr_print
    compose_fn: Callable[..., ComposeResult] = compose_for_lane
    compose_seams: ComposeSeams = ComposeSeams()
    build_reinforcement_fn: Callable[..., str] = build_dispatch_reinforcement_guidance
    build_soft_confinement_fn: Callable[[str], str] = build_soft_confinement_guidance


class ExecuteDispatchSpec(NamedTuple):
    candidate: dict
    prompt: str
    target_dir: str
    timeout: int
    format_block: str | None = None
    tool_availability: dict | None = None
    agents_tooling_path: object = None
    code_index_registered: bool = False
    files: tuple | None = ()


def build_execute_guidance(
    spec: ExecuteDispatchSpec, seams: ExecuteSeams,
) -> tuple[ComposeResult, str]:
    """Prefix the reinforcement and task with the lane's capability block.

    Soft confinement rides the block for write full or unknown; without --files (no block, no
    preview) the write reach is unknown, so the sentence stays, as before phase 39.
    """
    candidate = spec.candidate
    reinforcement = seams.build_reinforcement_fn(
        f"{candidate['runtime']}, model {candidate['model']}", spec.format_block
    )
    text = reinforcement + "\n\n" + spec.prompt
    if not spec.prompt.strip():
        return ComposeResult(), spec.prompt
    if spec.files is None:
        soft = seams.build_soft_confinement_fn(spec.target_dir)
        return ComposeResult(), "\n\n".join((reinforcement, soft, spec.prompt))
    composed = seams.compose_fn(
        LaneRequest(candidate["runtime"], candidate["model"], "execute", spec.target_dir,
                    _runner_spec(candidate, spec),
                    soft_confinement=seams.build_soft_confinement_fn(spec.target_dir)),
        text, spec.files, seams.runner_seams.env_fn(), seams.compose_seams,
    )
    return composed, text


def _runner_spec(candidate: dict, spec: ExecuteDispatchSpec) -> RunnerSpec:
    """One exec-mode runner spec; runner_flags adds codex's OS write confinement (D-27)."""
    return spec_with_effort(candidate["runtime"], candidate["model"], "exec", spec.timeout,
                            {**candidate, "cwd": spec.target_dir})


def _refuse_candidate(candidate: dict, target_dir: str) -> str:
    """The ValueError text for a candidate that must not be spawned, or "" when it may."""
    runtime = candidate["runtime"]
    if runtime is None:
        return (
            "dispatch_execute is for cross-AI (runtime-set) candidates only -- a native "
            "(runtime is None) candidate executes in-process and never reaches this function"
        )
    rejection = execute_cli_error(runtime, runner_facts.stored_fact(dict(os.environ)))
    if rejection:
        return rejection
    if not os.path.isdir(target_dir):
        return f"target dir {target_dir} does not exist"
    return ""


def dispatch_execute(
    spec: ExecuteDispatchSpec,
    seams: ExecuteSeams | None = None,
) -> dict:
    """Composes the exec guidance and runs the candidate through the runner in exec mode."""
    active = seams or ExecuteSeams()
    if isinstance(spec.candidate["runtime"], str):  # a legacy name runs as its runtime id
        spec = spec._replace(
            candidate={**spec.candidate, "runtime": runtime_id(spec.candidate["runtime"])}
        )
    candidate = spec.candidate
    refusal = _refuse_candidate(candidate, spec.target_dir)
    if refusal:
        raise ValueError(refusal)
    note = EXEC_NOTES.get(candidate["runtime"])
    if note:
        active.print_fn(note)
    composed, text = build_execute_guidance(spec, active)
    try:
        if composed.refusal:
            raise LaneRefused(composed.refusal)
        if composed.window is not None and composed.window["value"] is None:
            active.print_fn(f"ai-kit-spec: window for {candidate['runtime']}/{candidate['model']}: "
                            f"unknown ({composed.window['note'] or composed.window['label']}); "
                            "not capped")
        result = active.runner_fn(lane_spec(_runner_spec(candidate, spec), composed),
                                  with_block(composed.block, text), active.runner_seams)
    finally:
        cleanup(composed)
    return {
        "runtime": candidate["runtime"],
        "model": candidate["model"],
        "command": shlex.join(result.argv),
        "stdout": result.stdout,
        "returncode": result.returncode,
        "timed_out": result.timed_out,
        "reason": result.reason,
        "status": result.status,
    }
