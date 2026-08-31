"""Pure command-string formatting for GSD's own workflow.cross_ai_command hook -- confirmed a
general shell-command hook, already fully implemented by GSD itself (Task 1 finding 1). This
module builds ONE string; GSD's own cross_ai_delegation step does the piping/capture/retry. No
wrapper program, no subprocess dispatch, no heartbeat routing lives in this plan at all."""
from ai_kit_spec.commands import build_execute_command


def build_cross_ai_command(resolved_candidate: dict, target_dir: str,
                            execute_command_fn=build_execute_command):
    """Bug fix (2026-08-30): this used to also decline whenever `cli` was a member of
    KNOWN_GSD_RUNTIMES ("codex", "grok", "opencode", "claude", ... -- GSD's own vocabulary of
    runtime names it *could* run a phase under). That confused "GSD's runtime concept knows this
    CLI name" with "THIS candidate is actually reachable natively" -- the two are only the same
    candidate when it also carries a curated tier in KNOWN_GSD_TIERS, and adapter.py's
    resolve_gsd_dispatch ALREADY tries that native_tier route first and only calls this function
    after it fails (no curated tier, or a tier GSD doesn't honor). Keeping the runtime-name check
    here made every already-implemented, live-verified execute builder for those CLI names
    (codex's included) permanently unreachable in the real dispatch flow -- confirmed live:
    build_execute_command('codex', ...) returns a real command, but the old
    build_cross_ai_command({'cli': 'codex', ...}, ...) returned None regardless, every time. The
    only genuinely native case left to check here is cli is None (current-session dispatch,
    no CLI at all -- never needs a shell hook)."""
    cli = resolved_candidate["cli"]
    if cli is None:
        return None  # true native (current-session) dispatch -- no hook needed
    try:
        # effort/service_tier: same structural params execute_dispatch.dispatch_execute threads
        # through on the direct-dispatch path -- live-verified missing here 2026-08-31 (codex's
        # -c model_reasoning_effort flag silently dropped from the GSD cross_ai_hook command,
        # even though the candidate carried effort: "high").
        template = execute_command_fn(cli, target_dir=target_dir,
                                       effort=resolved_candidate.get("effort"),
                                       service_tier=resolved_candidate.get("service_tier"))
    except ValueError:
        return None  # no live-verified execute-mode builder for this CLI -- decline, don't guess
    return template.format(model=resolved_candidate["model"])
