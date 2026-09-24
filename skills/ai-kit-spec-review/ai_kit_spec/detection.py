import json
import os
import shlex
import shutil
import subprocess

from ai_kit_spec.cache import cache_base
from ai_kit_spec.vendor import _MODEL_TIER_SUFFIXES

RUNTIMES_TTL_SECONDS = 30 * 24 * 3600   # ~30 days: CLI/model presence is near-static

# 16 D-12: pre-Phase-16 snapshots carry no key and are treated as version 1; bump this
# whenever the snapshot shape gains data a consumer relies on.
RUNTIMES_SCHEMA_VERSION = 2

# ── Runtime/CLI detection ───────────────────────────────────────────────

KNOWN_CLIS = ("claude", "codex", "opencode", "grok", "cursor-agent")


def cache_runtimes_path(env: dict) -> str:
    return os.path.join(cache_base(env), "runtimes.json")


def detect_installed_clis(which_fn=shutil.which) -> dict:
    """{cli_name: absolute_path_or_None} for each KNOWN_CLIS entry."""
    return {cli: which_fn(cli) for cli in KNOWN_CLIS}


# Fixed check order per 16 D-01, as amended by Phase 20 D-02 (replaces 01.2 D-02's claude-first
# order). When CLIs nest, env vars accumulate and the innermost CLI must win, so claude --
# usually the outer orchestrator -- is checked last. The label "cursor" still differs from
# KNOWN_CLIS's "cursor-agent" binary-name entry on purpose (01.2 D-09); this tuple never
# touches KNOWN_CLIS.
_RUNTIME_ENV_SIGNALS = (
    ("pi", "PI_CODING_AGENT"),
    ("opencode", "OPENCODE"),
    ("cursor", "CURSOR_AGENT"),
    ("codex", "CODEX_THREAD_ID"),
    ("codex", "CODEX_VERSION"),
    ("claude", "CLAUDECODE"),
)


def detect_current_runtime(env: dict | None = None) -> str:
    """Which CLI is hosting THIS process right now.

    Walks `_RUNTIME_ENV_SIGNALS` in the documented fixed order and returns the
    first label whose env var is truthy, or `"unknown"` when none match
    (D-04: never silently omitted). A present-but-empty value (e.g.
    `CLAUDECODE=""`) is treated as falsy/absent — implemented via a plain
    truthiness check (`if env.get(var):`, never a bare `var in env` presence
    check). That is a deliberate contract matching ordinary env-var
    conventions, not an accident of `if env.get(var):`'s default behavior.

    Unlike `detect_installed_clis`/`build_runtimes_snapshot`, this is never
    cached or TTL'd (D-01/D-03): which CLI hosts a process is fixed for that
    process's whole lifetime, cheap to recompute, and never needs
    cross-process persistence. Nested-subprocess env vars accumulate, so
    two signals may both be set; the function never claims to resolve "true
    immediate parent" beyond what the fixed order establishes (D-02/D-03).
    The fixed order is pi > opencode > cursor > codex > claude
    (16 D-01, amended by Phase 20 D-02).

    Signal verification is NOT uniform — never treat all six as equally
    confirmed (AGENTS.md certainty-labeling; 01.2-RESEARCH.md Common Pitfall 2):

    - pi (`PI_CODING_AGENT`): source-inspected-only — confirmed in the
      installed `@earendil-works/pi-coding-agent` package's
      `dist/config.js`, not live-verified from a real pi session (16 D-03;
      live validation is Phase 22).
    - opencode (`OPENCODE`): live-verified (01.2) via a live spawned
      `opencode run` subprocess.
    - cursor (`CURSOR_AGENT`): source-inspected-only — confirmed via the
      installed cursor-agent bundle's own `index.js`, not a live subprocess.
    - codex (`CODEX_THREAD_ID`): observed in real codex session shell
      snapshots under `~/.codex/sessions` (the snapshot preamble exports
      `CODEX_THREAD_ID` from `__CODEX_SNAPSHOT_OVERRIDE_1`; 20 occurrences,
      16 D-02) — not yet live-verified from a codex host (Phase 20,
      EVAL-04).
    - codex (`CODEX_VERSION`): source-inspected-only — confirmed via
      openai/codex's open-source `exec_env.rs`, not a live subprocess.
    - claude (`CLAUDECODE`): live-verified (01.2) via the process's own
      env dump.
    """
    env = env if env is not None else os.environ
    for label, var in _RUNTIME_ENV_SIGNALS:
        if env.get(var):
            return label
    return "unknown"


def detect_opencode_models(binary: str, run_fn=subprocess.run) -> list:
    """Runs `<binary> models`; one model id per non-blank line. opencode is
    one of the known-installed multi-provider CLIs (confirmed live: lists
    opencode-go/kimi-k3, opencode-go/qwen3.8-max, opencode-go/grok-4.6,
    etc. under its own routing) — codex is enumerated separately via its
    own `codex debug models` (detect_codex_models); claude and grok have
    no list subcommand."""
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


def parse_codex_debug_models(stdout) -> list:
    """Parses the JSON stdout of `codex debug models` into
    `[{"id": <slug>, "reasoning_modes": [<effort>, ...]}, ...]`, one entry
    per listed model, in output order. Built from a real capture
    (codex-cli 0.147.0, resolved via PATH — a volta shim, i.e. a real
    executable, not an alias/function; see
    tests/fixtures/codex_debug_models.json). Only models whose
    `visibility` is exactly the string "list" are returned: the "hide"
    entries (gpt-reserve, codex-auto-review) read as internal/reserved
    slugs, not user-selectable models, and a MISSING `visibility` key
    counts as hidden too. `reasoning_modes` collects each
    `supported_reasoning_levels[].effort` value, in order, without
    duplicates. Every malformed input degrades to [] (or to skipping just
    the malformed item) and never raises: a non-`str` input, invalid JSON,
    a non-dict top level, a missing/non-list `models`, a non-dict item, a
    non-str/blank `slug`, a duplicate slug (first occurrence wins), or a
    missing/non-list `supported_reasoning_levels`. The function reads only
    `slug`, `visibility` and `supported_reasoning_levels[].effort` — the
    real payload is ~260KB, almost all of it `model_messages`/
    `base_instructions` prompt text that must never be copied."""
    if not isinstance(stdout, str):
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict) or not isinstance(data.get("models"), list):
        return []
    parsed = []
    seen = set()
    for item in data["models"]:
        if not isinstance(item, dict):
            continue
        slug = item.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            continue
        if item.get("visibility") != "list":
            continue
        if slug in seen:
            continue
        seen.add(slug)
        levels = item.get("supported_reasoning_levels")
        modes = []
        if isinstance(levels, list):
            for level in levels:
                if not isinstance(level, dict):
                    continue
                effort = level.get("effort")
                if not isinstance(effort, str) or not effort.strip():
                    continue
                if effort in modes:
                    continue
                modes.append(effort)
        parsed.append({"id": slug, "reasoning_modes": modes})
    return parsed


def detect_codex_models(binary: str, run_fn=subprocess.run) -> list:
    """Runs `<binary> debug models` (codex-cli 0.147.0, resolved via PATH —
    a volta shim, i.e. a real executable, not an alias/function) and
    parses its JSON stdout via `parse_codex_debug_models`, keeping only
    models whose `visibility` is "list" (the "hide" entries are
    internal/reserved slugs, not user-selectable). A non-zero exit is a
    FAILURE, not a success with a stale/partial payload: a failing command
    that still prints JSON must never populate models, so the result's
    `returncode` must be exactly 0 (the same gate
    ai_kit_gsd_curated_config/model_detect.py already applies); a `run_fn`
    stub returning None or an object without a `returncode` attribute
    yields []. Like every parser in this file, any failure degrades to []
    and never raises — an OSError/TimeoutExpired, invalid JSON, or an
    unexpected shape all return [] rather than crashing detection."""
    try:
        result = run_fn([binary, "debug", "models"], capture_output=True, text=True,
                        check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if getattr(result, "returncode", 1) != 0:
        return []
    return parse_codex_debug_models(getattr(result, "stdout", None))


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


def runtimes_schema_is_current(data) -> bool:
    """16 D-12: True only when `data` is a dict whose `schema_version` is a non-bool int
    >= RUNTIMES_SCHEMA_VERSION. Everything else (None, non-dict, missing key, a bool,
    a string, an older version) is False -- a missing or older version counts as stale
    whatever the TTL says. Never raises, never mutates its input."""
    if not isinstance(data, dict):
        return False
    version = data.get("schema_version")
    return isinstance(version, int) and not isinstance(version, bool) \
        and version >= RUNTIMES_SCHEMA_VERSION


def build_runtimes_snapshot(which_fn=shutil.which, run_fn=subprocess.run) -> dict:
    """{"schema_version": RUNTIMES_SCHEMA_VERSION, "clis": {name: {"installed": bool,
    "path"?: str, "models"?: [str], "reasoning_modes"?: {model_id: [effort, ...]}}}}.
    `models` is populated
    for opencode/cursor-agent always, and for codex when `codex debug
    models` enumeration succeeds; `reasoning_modes` (codex only) maps each
    enumerated model id to its CLI-reported effort levels, only for ids
    that actually have a non-empty effort list. Pure function — the caller
    (this module's CLI entrypoint) decides whether/where to persist this
    via cache_write_json."""
    installed = detect_installed_clis(which_fn=which_fn)
    snapshot = {"schema_version": RUNTIMES_SCHEMA_VERSION, "clis": {}}
    for cli, binpath in installed.items():
        if not binpath:
            snapshot["clis"][cli] = {"installed": False}
            continue
        entry = {"installed": True, "path": binpath}
        if cli == "opencode":
            entry["models"] = detect_opencode_models(binpath, run_fn=run_fn)
        elif cli == "cursor-agent":
            entry["models"] = detect_cursor_agent_models(binpath, run_fn=run_fn)
        elif cli == "codex":
            codex_models = detect_codex_models(binpath, run_fn=run_fn)
            if codex_models:
                entry["models"] = [m["id"] for m in codex_models]
                entry["reasoning_modes"] = {
                    m["id"]: m["reasoning_modes"]
                    for m in codex_models if m["reasoning_modes"]
                }
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


# The two multi-provider CLIs with their own per-model catalog (a single-vendor CLI's
# list - codex's enumerated slugs included - only ever serves that one vendor's models, so
# it can never be a *target* alternative for another CLI's model here; only these two
# multi-provider CLIs can).
_CODEGRAPH_CAPABLE_MULTI_PROVIDER_CLIS = ("cursor-agent", "opencode")


def find_codegraph_alternative(cli: str, model: str, runtimes_snapshot: dict) -> str | None:
    """Best-effort only (design spec §8, §14): when `cli` has no codegraph/MCP support (not in
    _SUPPORTED_CODEGRAPH_CLIENTS) but a substring match suggests the SAME base model is also
    reachable through a codegraph-capable CLI's own model catalog, return that CLI's name --
    informational only, never a hard filter. Model-id naming conventions differ across CLIs
    (e.g. "grok-4.6" vs. "cursor-grok-4.6-high") so this is a substring heuristic, not a
    guarantee; a missed match degrades silently to None, never a false claim."""
    if cli in _SUPPORTED_CODEGRAPH_CLIENTS:
        return None
    needle = model.lower()
    for candidate_cli in _CODEGRAPH_CAPABLE_MULTI_PROVIDER_CLIS:
        entry = runtimes_snapshot.get("clis", {}).get(candidate_cli, {})
        if not entry.get("installed"):
            continue
        for candidate_model in entry.get("models", []):
            if needle in candidate_model.lower():
                return candidate_cli
    return None


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
