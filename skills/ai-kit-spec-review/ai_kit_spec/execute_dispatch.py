"""Direct process dispatch for ai-kit-spec-execute's own resolved candidates -- bypasses any
target framework's own config-write/hook indirection (e.g. GSD's workflow.cross_ai_command,
which only exists to tell GSD's OWN execute-phase step what to shell out to, and only fires
after a whole GSD-specific config round-trip). This module IS the dispatch: it builds the real
command via commands.build_execute_command, composes a reinforced prompt (model-selection
override, incremental progress, honest failure reporting, tool/MCP guidance, and -- for the two
CLIs with no OS-level write confinement -- an explicit soft-confinement instruction), and runs it
for real via dispatch.dispatch_with_heartbeat. A native (cli is None) candidate is never routed
here -- it has no subprocess to dispatch at all; the caller executes it in-process."""
from ai_kit_spec.commands import NO_HARD_SANDBOX_CLIS, build_execute_command
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


def dispatch_execute(candidate: dict, prompt: str, target_dir: str, heartbeat_interval: int,
                      timeout: int, format_block: str | None = None,
                      tool_availability: dict | None = None, agents_tooling_path=None,
                      codegraph_registered: bool = False,
                      build_execute_command_fn=build_execute_command,
                      build_tooling_guidance_fn=build_tooling_guidance,
                      build_reinforcement_fn=build_dispatch_reinforcement_guidance,
                      build_soft_confinement_fn=build_soft_confinement_guidance,
                      dispatch_fn=dispatch_with_heartbeat) -> dict:
    """Resolves `candidate`'s real execute-mode command, composes the full reinforced prompt, and
    actually runs it (a real subprocess, real heartbeat, real timeout enforcement) via
    dispatch_with_heartbeat. Returns dispatch_with_heartbeat's own result dict plus `cli`/`model`/
    `command` so a caller can log/report what was actually run without re-deriving it.

    `candidate["cli"]` must not be None -- a native candidate has no command to build or process
    to dispatch; routing one here is a caller bug, not a runtime condition to degrade from."""
    cli = candidate["cli"]
    if cli is None:
        raise ValueError(
            "dispatch_execute is for cross-AI (cli-set) candidates only -- a native "
            "(cli is None) candidate executes in-process and never reaches this function"
        )
    # effort/service_tier: structural params a builder may or may not use (codex does; grok,
    # claude, cursor-agent, opencode's execute builders ignore them via their own **_params) --
    # passed through unconditionally, same as build_reviewer_command's own review-mode contract.
    command_template = build_execute_command_fn(
        cli, target_dir=target_dir, effort=candidate.get("effort"),
        service_tier=candidate.get("service_tier"))
    command = command_template.format(model=candidate["model"])
    resolved_label = f"{cli}, model {candidate['model']}"
    guidance_sections = [build_reinforcement_fn(resolved_label, format_block)]
    tool_guidance = build_tooling_guidance_fn(
        cli, tool_availability or {}, agents_tooling_path, codegraph_registered,
        shared_reference_path=resolve_shared_tooling_reference_path())
    if tool_guidance:
        guidance_sections.append(tool_guidance)
    if cli in NO_HARD_SANDBOX_CLIS:
        guidance_sections.append(build_soft_confinement_fn(target_dir))
    full_prompt = "\n\n".join(guidance_sections) + "\n\n" + prompt
    result = dispatch_fn(command, full_prompt, heartbeat_interval, timeout)
    return {"cli": cli, "model": candidate["model"], "command": command, **result}
