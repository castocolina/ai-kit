from ai_kit_spec.detection import RUNTIMES


def host_can_select(runtime, model, host) -> bool:
    """Whether the host has a verified per-call selector for this model.

    Verified only for Claude Code aliases on Claude Code. Every other host is
    session-default-only until Phases 20-22 (R3).
    """
    return (
        isinstance(runtime, str)
        and runtime == host
        and runtime in RUNTIMES
        and isinstance(model, str)
        and model in RUNTIMES[runtime].native_selectors
    )
