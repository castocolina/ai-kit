import os
import shlex
import shutil
import subprocess

from ai_kit_spec.cache import cache_base
from ai_kit_spec.vendor import _MODEL_TIER_SUFFIXES

RUNTIMES_TTL_SECONDS = 30 * 24 * 3600   # ~30 days: CLI/model presence is near-static

# ── Runtime/CLI detection ───────────────────────────────────────────────

KNOWN_CLIS = ("claude", "codex", "opencode", "grok", "cursor-agent")


def cache_runtimes_path(env: dict) -> str:
    return os.path.join(cache_base(env), "runtimes.json")


def detect_installed_clis(which_fn=shutil.which) -> dict:
    """{cli_name: absolute_path_or_None} for each KNOWN_CLIS entry."""
    return {cli: which_fn(cli) for cli in KNOWN_CLIS}


def detect_opencode_models(binary: str, run_fn=subprocess.run) -> list:
    """Runs `<binary> models`; one model id per non-blank line. opencode is
    the only known-installed multi-provider CLI today (confirmed live:
    lists opencode-go/kimi-k3, opencode-go/qwen3.8-max, opencode-go/grok-4.6,
    etc. under its own routing) — other CLIs name their model directly on
    invocation with no separate list subcommand to parse."""
    try:
        result = run_fn([binary, "models"], capture_output=True, text=True,
                         check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]


def detect_cursor_agent_models(binary: str, run_fn=subprocess.run) -> list:
    """Runs `<binary> models`; each line is `<id> - <display name>` after
    a header ("Available models") and a blank line — confirmed live
    against a real authenticated install (2026.08.25-3e8eec8). Returns
    just the ids (before ` - `), skipping the header/blank lines and any
    line with no ` - ` separator (defensive — a format change should
    degrade to an empty/partial list here, never crash detection)."""
    try:
        result = run_fn([binary, "models"], capture_output=True, text=True,
                         check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return []
    models = []
    for ln in result.stdout.splitlines():
        ln = ln.strip()
        if " - " not in ln:
            continue
        models.append(ln.split(" - ", 1)[0].strip())
    return models


def group_models_by_family(models: list) -> dict:
    """Collapses tier/effort/mode variants of the same base model into one
    group, e.g. ["claude-opus-5-high", "claude-opus-5-high-fast",
    "claude-opus-5-low"] -> {"claude-opus-5": [...three ids...]}. Strips
    only a TRAILING run of tokens from `_MODEL_TIER_SUFFIXES` (hyphen-
    joined) off the end of each id — an id with no such trailing run
    becomes its own family unchanged (e.g. "auto", "composer-2.5"). This
    is a best-effort heuristic over a live-fetched, presumably-current
    catalog — it does not know which family is "newest" or "best" for
    any purpose; that judgment belongs to whoever (or whatever, e.g. a
    wizard doing live research on an unfamiliar name) is choosing among
    the returned families, not to this function. Preserves each model's
    original relative order within its group and preserves the order
    families are first seen in `models`."""
    groups = {}
    for model in models:
        parts = model.split("-")
        cut = len(parts)
        while cut > 1 and parts[cut - 1] in _MODEL_TIER_SUFFIXES:
            cut -= 1
        family = "-".join(parts[:cut]) or model
        groups.setdefault(family, []).append(model)
    return groups


def build_runtimes_snapshot(which_fn=shutil.which, run_fn=subprocess.run) -> dict:
    """{"clis": {name: {"installed": bool, "path"?: str, "models"?: [str]}}}.
    Pure function — the caller (this module's CLI entrypoint) decides
    whether/where to persist this via cache_write_json."""
    installed = detect_installed_clis(which_fn=which_fn)
    snapshot = {"clis": {}}
    for cli, binpath in installed.items():
        if not binpath:
            snapshot["clis"][cli] = {"installed": False}
            continue
        entry = {"installed": True, "path": binpath}
        if cli == "opencode":
            entry["models"] = detect_opencode_models(binpath, run_fn=run_fn)
        elif cli == "cursor-agent":
            entry["models"] = detect_cursor_agent_models(binpath, run_fn=run_fn)
        snapshot["clis"][cli] = entry
    return snapshot


def detect_tool_availability(which_fn=shutil.which) -> dict:
    """Deterministic presence check for the token-efficient tooling AGENTS-TOOLING.md
    recommends. codegraph is included here (binary presence only, Tier 1 of the two-tier
    check design §9 established) -- MCP registration per-client is a separate concern,
    see check_codegraph_mcp_healthy below."""
    return {name: which_fn(name) is not None
            for name in ("rg", "sd", "bat", "eza", "fd", "codegraph")}


def resolve_agents_tooling_path(env=None) -> str | None:
    """Machine-level file, not project-level -- never hardcode one user's absolute path.
    AGENTS_TOOLING_PATH env override wins IF it actually exists on disk; else the conventional
    ~/.agents/AGENTS-TOOLING.md location if it exists; else None (the caller omits tooling
    guidance entirely, same never-guess principle as the codegraph MCP check below). The
    override is validated, not trusted blindly -- a stale/misconfigured env var must never put
    an unverified path into a dispatch prompt."""
    env = env if env is not None else os.environ
    override = env.get("AGENTS_TOOLING_PATH")
    if override:
        return override if os.path.isfile(override) else None
    candidate = os.path.join(env.get("HOME", ""), ".agents", "AGENTS-TOOLING.md")
    return candidate if os.path.isfile(candidate) else None


# Confirmed live, 2026-08-30, against each installed CLI's own --help AND real invocations
# (`claude mcp list`, `codex mcp list`, `cursor-agent mcp list`, `opencode mcp list` all ran
# clean, exit 0, on this machine). grok is deliberately absent -- confirmed unsupported, never
# attempt a lookup for it.
#
# claude/codex: `mcp get <name>` is the PRIMARY check where it exists -- direct per-name lookup,
#   deterministic exit code (0 = registered, nonzero = "No MCP server named ..."). `mcp list`
#   is a FALLBACK for these two as well: `get`'s nonzero exit means "not registered" in the
#   common case, but could also mean something else went wrong with the `get` invocation itself
#   (a CLI bug, an auth hiccup) -- cross-checking via `list` before concluding "not registered"
#   costs one extra subprocess call only in the nonzero-exit case, and avoids a false negative
#   from trusting a single command's exit code alone.
# cursor-agent/opencode: no `get` subcommand exists (confirmed via --help) -- `mcp list` is the
#   ONLY check, not a fallback.
# All `mcp list` parsing looks for a line whose name token (text before the first ':') is
# exactly "codegraph"; every observed list format uses that "name: ..." convention.
#
# HEALTH, not just presence: confirmed live that a registered server can be currently
# disconnected -- `claude mcp list` showed `plugin:playwright:playwright: ... - ✘ Failed to
# connect — CONNECTION_CLOSED`, moments before `claude mcp get plugin:playwright:playwright`
# printed `Status: ✔ Connected` for that same server (connection state visibly fluctuates
# between calls). Registered-but-unhealthy must be treated the same as not-registered for the
# purpose this check serves -- telling a subagent to use a currently-broken MCP tool wastes a
# dispatch on a guaranteed failure. Both `get` and `list` output include a `Status:`/inline
# health indicator; look for an explicit failure signal in the relevant text before declaring
# healthy, never assume health from presence alone.
_SUPPORTED_CODEGRAPH_CLIENTS = frozenset({"claude", "codex", "cursor-agent", "opencode"})

_MCP_GET_COMMANDS = {"claude": "claude mcp get codegraph", "codex": "codex mcp get codegraph"}
_MCP_LIST_COMMANDS = {
    "claude": "claude mcp list", "codex": "codex mcp list",
    "cursor-agent": "cursor-agent mcp list", "opencode": "opencode mcp list",
}

# Confirmed live in claude's own output ("✔ Connected" / "✘ Failed to connect — ..."); codex/
# cursor-agent/opencode not yet observed with a real failing entry (nothing was registered to
# test against during this plan's own session) -- Task 3 Step 5's live smoke test must confirm
# these same signals appear (or find and add the real ones) for whichever of those three CLIs
# it tests against an actually-unhealthy server.
_UNHEALTHY_SIGNALS = ("✘", "failed to connect", "not connected")


def _text_is_healthy(text: str) -> bool:
    lowered = text.lower()
    return not any(signal.lower() in lowered for signal in _UNHEALTHY_SIGNALS)


def _codegraph_entry_healthy_in_list_output(stdout: str) -> bool:
    """False if no 'codegraph' entry is found at all (not registered). False if found but its
    own line shows a failure signal (registered but unhealthy -- treated the same as absent for
    this check's purpose). True only if found AND healthy."""
    for line in stdout.splitlines():
        name = line.split(":", 1)[0].strip()
        if name == "codegraph":
            return _text_is_healthy(line)
    return False


def check_codegraph_mcp_healthy(cli: str, run_fn=subprocess.run) -> bool:
    """Cheap, run every session, scoped to the one client about to be dispatched (never a
    one-time-ever check -- a client installed after codegraph's own setup would otherwise
    never get detected). Uses each client's own real MCP-inspection command, confirmed live
    against the actual installed CLI -- never reads a config file directly (a prior revision of
    this function did that and produced weak substring-match false positives). Verifies HEALTH,
    not just presence -- a registered-but-currently-disconnected server returns False here,
    same as if it were never registered at all (see the module-level note above for why).

    Where `mcp get <name>` exists (claude, codex), it is the primary, cheapest check -- one
    subprocess call, deterministic exit code, then a health-signal check on its own stdout.
    Only on a NONZERO `get` exit does this fall back to `mcp list` for that same client: a
    nonzero `get` exit usually means "not registered," but could also mean the `get` invocation
    itself hit an unrelated problem (a CLI bug, an auth hiccup) -- cross-checking via `list`
    before concluding "not registered" is one extra call in the uncommon case, in exchange for
    not trusting a single command's exit code as the only signal. cursor-agent/opencode have no
    `get` at all, so `list` is their only (not a fallback) check."""
    if cli not in _SUPPORTED_CODEGRAPH_CLIENTS:
        return False
    get_command = _MCP_GET_COMMANDS.get(cli)
    if get_command is not None:
        result = run_fn(get_command, shell=True, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return _text_is_healthy(result.stdout)
        # nonzero exit -- cross-check via `mcp list` before concluding "not registered"
    list_result = run_fn(_MCP_LIST_COMMANDS[cli], shell=True, capture_output=True, text=True,
                          check=False)
    return _codegraph_entry_healthy_in_list_output(list_result.stdout)


CODEGRAPH_INDEX_TIMEOUT_SECONDS = 15  # agreed minimum, safety margin over the typical <5s runtime


def ensure_codegraph_registered(cli: str, run_fn=subprocess.run,
                                 check_fn=check_codegraph_mcp_healthy) -> bool:
    """Runs every session, scoped to `cli` -- never a one-time-ever check (design spec §9,
    corrected during brainstorming: a client installed after codegraph's own setup would
    otherwise never get detected). Only `install` itself is conditional on check_fn's result."""
    if check_fn(cli):
        return True
    if cli not in _SUPPORTED_CODEGRAPH_CLIENTS:
        return False  # grok and any other unsupported client -- never attempt install
    run_fn(f"codegraph install --target={cli} --location=global --yes --init",
           shell=True, capture_output=True, text=True, check=False)
    return check_fn(cli)


def build_codegraph_index_command(target_dir: str) -> str:
    """sync first (fast, incremental), init as fallback (first-ever index for this repo) --
    confirmed real usage from the design discussion. Caller (the orchestrator, never the
    sandboxed reviewer/executor subagent) runs this with a minimum
    CODEGRAPH_INDEX_TIMEOUT_SECONDS timeout, before dispatch. target_dir is shell-quoted --
    this string is built for shell=True execution, same as every other command builder in this
    package; an unquoted path with a space or shell metacharacter would break or inject."""
    return f"cd {shlex.quote(target_dir)} && (codegraph sync || codegraph init)"
