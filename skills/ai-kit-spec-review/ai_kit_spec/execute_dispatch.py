"""Direct process dispatch for ai-kit-spec-execute's own resolved candidates -- bypasses any
target framework's own config-write/hook indirection (e.g. GSD's workflow.cross_ai_command,
which only exists to tell GSD's OWN execute-phase step what to shell out to, and only fires
after a whole GSD-specific config round-trip). This module IS the dispatch: it composes the
exec guidance (model-selection override, incremental progress, honest failure reporting,
tool/MCP guidance, and -- for every runtime the OS does not confine -- an explicit
soft-confinement instruction) and runs one candidate through the cross-AI runner in exec mode
(D-11). A native (runtime is None) candidate is never routed here -- it has no subprocess to
dispatch at all; the caller executes it in-process.

The runner runs every exec CLI with full permissions except codex, which runs under
`--codex-sandbox workspace-write` (D-27). That sandbox still allows writes to /tmp and
$TMPDIR regardless of the target dir. Soft confinement is prompt guidance, not a security
boundary (D-27)."""
import os
import shlex
from collections.abc import Callable
from typing import NamedTuple

from ai_kit_spec.commands import execute_cli_error
from ai_kit_spec.detection import runtime_id
from ai_kit_spec.dispatch_guidance import build_dispatch_reinforcement_guidance
from ai_kit_spec.runner_dispatch import (
    OS_SANDBOXED_EXEC,
    PI_EXEC_NOTE,
    RunnerSeams,
    RunnerSpec,
    run_runner,
    stderr_print,
)
from ai_kit_spec.tooling_guidance import (
    build_tooling_guidance,
    resolve_shared_tooling_reference_path,
)


def build_soft_confinement_guidance(target_dir: str) -> str:
    """Prompt guidance for a runtime the runner does not OS-confine (everything outside
    OS_SANDBOXED_EXEC). Neither cursor nor opencode nor pi has a flag that genuinely confines
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
    build_tooling_guidance_fn: Callable[..., str] = build_tooling_guidance
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
    codegraph_registered: bool = False


def build_execute_guidance(spec: ExecuteDispatchSpec, seams: ExecuteSeams) -> str:
    """The one composer of the exec guidance: reinforcement (with the format block), tooling
    guidance, and soft confinement for every runtime the OS does not confine.

    The runner runs every exec CLI with full permissions except codex under `--codex-sandbox
    workspace-write`, which still allows writes to /tmp and $TMPDIR. Soft confinement is prompt
    guidance, not a security boundary."""
    candidate = spec.candidate
    runtime = candidate["runtime"]
    sections = [
        seams.build_reinforcement_fn(
            f"{runtime}, model {candidate['model']}", spec.format_block
        )
    ]
    tool_guidance = seams.build_tooling_guidance_fn(
        runtime,
        spec.tool_availability or {},
        spec.agents_tooling_path,
        spec.codegraph_registered,
        shared_reference_path=resolve_shared_tooling_reference_path(),
    )
    if tool_guidance:
        sections.append(tool_guidance)
    if runtime not in OS_SANDBOXED_EXEC:
        sections.append(seams.build_soft_confinement_fn(spec.target_dir))
    return "\n\n".join(sections)


def _runner_spec(candidate: dict, spec: ExecuteDispatchSpec) -> RunnerSpec:
    """One exec-mode runner spec; runner_flags adds codex's OS write confinement (D-27)."""
    return RunnerSpec(
        candidate["runtime"], candidate["model"], "exec", spec.timeout, cwd=spec.target_dir,
        effort=candidate.get("effort"), service_tier=candidate.get("service_tier"),
    )


def _refuse_candidate(candidate: dict, target_dir: str) -> str:
    """The ValueError text for a candidate that must not be spawned, or "" when it may."""
    runtime = candidate["runtime"]
    if runtime is None:
        return (
            "dispatch_execute is for cross-AI (runtime-set) candidates only -- a native "
            "(runtime is None) candidate executes in-process and never reaches this function"
        )
    rejection = execute_cli_error(runtime)
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
    if candidate["runtime"] == "pi":
        active.print_fn(PI_EXEC_NOTE)
    result = active.runner_fn(
        _runner_spec(candidate, spec),
        build_execute_guidance(spec, active) + "\n\n" + spec.prompt,
        active.runner_seams,
    )
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
