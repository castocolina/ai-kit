"""Pure cross-AI execution target selection (18 D-09/D-10/D-15/D-28/D-39).

Imports only ``.presets`` and ``.roles``. Target ids are runner ids; ``RUNNER_CLI`` maps
them to inventory runtimes. The script artifact ``config`` is the sole copy of runner
settings (no parallel ``targets[]`` list).
"""
from typing import NamedTuple

from . import presets, roles

CROSS_AI_COMMAND = "node .planning/scripts/cross-ai.mjs"
SCRIPT_PATH = ".planning/scripts/cross-ai.mjs"
TEMPLATE_NAME = "cross-ai.mjs"
TEMPLATE_VERSION = 2
MIN_TIMEOUT_S = 1800
DEFAULT_PREFER = ("pi", "cursor", "opencode")
RUNNER_CLI = {
    "pi": "pi",
    "cursor": "cursor-agent",
    "opencode": "opencode",
    "codex": "codex",
}
EXEC_DEFAULT_HOSTS = ("claude", "codex")
EXEC_EFFORT_TARGET = "medium"
CROSS_AI_FLAG = "--cross-ai"
NO_TARGET_TEXT = "no installed cross-AI target (pi, cursor-agent, opencode)"
_ROUTER_WHY = "user-curated router (declared purpose: execute)"


class Target(NamedTuple):
    cli: str
    model: str | None
    source: str | None
    why: str
    router_backed: bool
    candidates: list


def _runtime_cands(inv: dict, runner_id: str) -> list:
    runtime = RUNNER_CLI[runner_id]
    return [c for c in inv["candidates"] if c.get("runtime") == runtime]


def _pick_for_runner(runner_id: str, cands: list, rigor: str) -> Target:
    ceiling = roles.host_ceiling(cands, presets.PRICE_PERCENTILE[rigor])
    routers = sorted(
        [
            c
            for c in cands
            if c.get("is_router")
            and c.get("router_confirmed")
            and c.get("name_declared_purpose") == "execute"
        ],
        key=lambda c: c["model"],
    )
    if routers:
        model = routers[0]["model"]
        return Target(runner_id, model, "router-declared", _ROUTER_WHY, True, [])
    pick = roles.best_pick(cands, "execution", EXEC_EFFORT_TARGET, ceiling.value)
    if pick is not None:
        why = roles.pick_why(pick, "execution", EXEC_EFFORT_TARGET, ceiling)
        return Target(runner_id, pick.candidate["model"], "catalog-score", why, False, [])
    fallback = roles.choice_candidates(cands, "execution", ceiling.value)
    return Target(
        runner_id,
        None,
        None,
        "no execution model within ceiling",
        False,
        fallback,
    )


def exec_targets(inv: dict, rigor: str, prefer=DEFAULT_PREFER) -> list[Target]:
    """Preference-ordered execution targets on installed non-host runtimes (18 D-10)."""
    host = inv["host"]
    installed = inv["installed_runtimes"]
    out: list[Target] = []
    for runner_id in prefer:
        if runner_id not in RUNNER_CLI:
            continue
        if runner_id == host:
            continue
        runtime = RUNNER_CLI[runner_id]
        if runtime not in installed:
            continue
        cands = _runtime_cands(inv, runner_id)
        out.append(_pick_for_runner(runner_id, cands, rigor))
    return out


def exec_default(host: str, targets: list) -> tuple[str, str]:
    """D-39 default for ``workflow.cross_ai_execution`` when the flag is omitted."""
    if host in EXEC_DEFAULT_HOSTS:
        if targets:
            names = ", ".join(t.cli for t in targets)
            return ("y", f"D-39: cross-AI execution defaults on {host} with target(s) {names}")
        return ("n", NO_TARGET_TEXT)
    return ("n", f"execution stays on the host for {host} (spec §6)")


def timeout_value(existing) -> int:
    if isinstance(existing, int) and not isinstance(existing, bool) and existing >= MIN_TIMEOUT_S:
        return existing
    return MIN_TIMEOUT_S


def manager_flags_value(existing) -> str:
    if isinstance(existing, str) and existing.strip():
        tokens = existing.split()
        if CROSS_AI_FLAG in tokens:
            return existing
        return existing.strip() + f" {CROSS_AI_FLAG}"
    return CROSS_AI_FLAG


def script_artifact(targets: list[Target], timeout: int) -> dict:
    models = {t.cli: t.model for t in targets if t.model is not None}
    choices = {t.cli: {"candidates": t.candidates} for t in targets if t.model is None}
    status = "needs_choice" if choices else "ok"
    why_tail = "; ".join(f"{t.cli}: {t.why}" for t in targets)
    return {
        "kind": "cross-ai-script",
        "path": SCRIPT_PATH,
        "template": TEMPLATE_NAME,
        "version": TEMPLATE_VERSION,
        "config": {
            "prefer": [t.cli for t in targets],
            "models": models,
            "outer_timeout_s": timeout,
            "router_backed": {t.cli: t.router_backed for t in targets if t.model is not None},
        },
        "choices": choices,
        "status": status,
        "source": "preset",
        "why": f"cross-AI execution runner (18 D-09); {why_tail}",
    }
