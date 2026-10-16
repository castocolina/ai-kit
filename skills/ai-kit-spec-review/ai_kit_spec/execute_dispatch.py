"""Direct process dispatch for ai-kit-spec-execute's own resolved candidates -- bypasses any
target framework's own config-write/hook indirection (e.g. GSD's workflow.cross_ai_command,
which only exists to tell GSD's OWN execute-phase step what to shell out to, and only fires
after a whole GSD-specific config round-trip). This module IS the dispatch: it builds the real
command via commands.build_execute_command, composes a reinforced prompt (model-selection
override, incremental progress, honest failure reporting, tool/MCP guidance, and -- for the two
CLIs with no OS-level write confinement -- an explicit soft-confinement instruction), and runs
it for real via dispatch.dispatch_with_heartbeat as an ARGV list with no shell (D-10). A native
(cli is None) candidate is never routed here -- it has no subprocess to dispatch at all; the
caller executes it in-process."""
import shlex
from collections.abc import Callable
from typing import NamedTuple

from ai_kit_spec.commands import NO_HARD_SANDBOX_CLIS, build_execute_command
from ai_kit_spec.detection import runtime_id
from ai_kit_spec.dispatch import dispatch_with_heartbeat
from ai_kit_spec.dispatch_guidance import build_dispatch_reinforcement_guidance
from ai_kit_spec.tooling_guidance import (
    build_tooling_guidance,
    resolve_shared_tooling_reference_path,
)


def build_soft_confinement_guidance(target_dir: str) -> str:
    """The only mitigation available for cursor-agent/opencode (NO_HARD_SANDBOX_CLIS, see
    commands.py) -- neither CLI's own flags genuinely confine writes (confirmed live, twice
    each), so the sole remaining defense is telling the dispatched CLI, explicitly and
    unambiguously, that target_dir is the only place it may write at all."""
    return (
        f"This dispatch has NO operating-system-level write confinement -- you must never "
        f"write, move, rename, or delete any file outside {target_dir} for any reason, even "
        f"temporarily or as a scratch/backup location. Treat {target_dir} as the only writable "
        f"location that exists."
    )


class ExecuteSeams(NamedTuple):
    build_execute_command_fn: Callable[..., str] = build_execute_command
    build_tooling_guidance_fn: Callable[..., str] = build_tooling_guidance
    build_reinforcement_fn: Callable[..., str] = build_dispatch_reinforcement_guidance
    build_soft_confinement_fn: Callable[[str], str] = build_soft_confinement_guidance
    dispatch_fn: Callable[..., dict] = dispatch_with_heartbeat


class ExecuteDispatchSpec(NamedTuple):
    candidate: dict
    prompt: str
    target_dir: str
    heartbeat_interval: int
    timeout: int
    format_block: str | None = None
    tool_availability: dict | None = None
    agents_tooling_path: object = None
    codegraph_registered: bool = False


def _compose_execute_prompt(
    spec: ExecuteDispatchSpec, seams: ExecuteSeams
) -> tuple[list[str], str]:
    candidate = spec.candidate
    cli = candidate["cli"]
    command_template = seams.build_execute_command_fn(
        cli,
        target_dir=spec.target_dir,
        effort=candidate.get("effort"),
        service_tier=candidate.get("service_tier"),
    )
    argv = [token.format(model=candidate["model"]) for token in shlex.split(command_template)]
    resolved_label = f"{cli}, model {candidate['model']}"
    guidance_sections = [seams.build_reinforcement_fn(resolved_label, spec.format_block)]
    tool_guidance = seams.build_tooling_guidance_fn(
        cli,
        spec.tool_availability or {},
        spec.agents_tooling_path,
        spec.codegraph_registered,
        shared_reference_path=resolve_shared_tooling_reference_path(),
    )
    if tool_guidance:
        guidance_sections.append(tool_guidance)
    if runtime_id(cli) in NO_HARD_SANDBOX_CLIS:
        guidance_sections.append(seams.build_soft_confinement_fn(spec.target_dir))
    full_prompt = "\n\n".join(guidance_sections) + "\n\n" + spec.prompt
    return argv, full_prompt


def dispatch_execute(
    spec: ExecuteDispatchSpec,
    seams: ExecuteSeams | None = None,
) -> dict:
    """Resolves `spec.candidate`'s real execute-mode command, composes the prompt, and runs it."""
    active = seams or ExecuteSeams()
    cli = spec.candidate["cli"]
    if cli is None:
        raise ValueError(
            "dispatch_execute is for cross-AI (cli-set) candidates only -- a native "
            "(cli is None) candidate executes in-process and never reaches this function"
        )
    argv, full_prompt = _compose_execute_prompt(spec, active)
    result = active.dispatch_fn(argv, full_prompt, spec.heartbeat_interval, spec.timeout)
    return {
        "cli": cli,
        "model": spec.candidate["model"],
        "command": shlex.join(argv),
        **result,
    }
