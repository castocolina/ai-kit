"""Locates the installed gsd-core's gsd-tools.cjs and lib/model-catalog.cjs, and queries the
live AGENT_DEFAULT_TIERS/AGENT_TO_PHASE_TYPE export via a `node -e` subprocess call.

The install-root candidate list below mirrors the multi-host gsd-core install-root search
every GSD agent already performs (per-host env var with a `$HOME`-relative default, tried in
a fixed order) -- never narrow this to `~/.claude` alone; several hosts (Cursor, Codex,
OpenCode, Kilo, etc.) install gsd-core under their own config directory instead.
"""
import json
import os
import shutil
import subprocess

# (env_var_name, default_path_relative_to_home) pairs, in the exact canonical order every GSD
# planner/orchestrator agent already resolves gsd-tools.cjs through.
GSD_CORE_ROOT_CANDIDATES = (
    ("CLAUDE_CONFIG_DIR", ".claude"),
    ("HERMES_HOME", ".hermes"),
    ("CURSOR_CONFIG_DIR", ".cursor"),
    ("CODEX_HOME", ".codex"),
    ("GEMINI_CONFIG_DIR", ".gemini"),
    ("COPILOT_CONFIG_DIR", ".copilot"),
    ("WINDSURF_CONFIG_DIR", ".codeium/windsurf"),
    ("AUGMENT_CONFIG_DIR", ".augment"),
    ("TRAE_CONFIG_DIR", ".trae"),
    ("QWEN_CONFIG_DIR", ".qwen"),
    ("CODEBUDDY_CONFIG_DIR", ".codebuddy"),
    ("CLINE_CONFIG_DIR", ".cline"),
    ("GROK_AGENTS_HOME", ".agents"),
    ("ANTIGRAVITY_CONFIG_DIR", ".gemini/antigravity"),
    ("OPENCODE_CONFIG_DIR", ".config/opencode"),  # falls back through XDG_CONFIG_HOME first
    ("KILO_CONFIG_DIR", ".config/kilo"),  # falls back through XDG_CONFIG_HOME first
)

# The two candidates above whose default path is itself XDG_CONFIG_HOME-relative, not
# $HOME-relative -- XDG_CONFIG_HOME (when set) is consulted before the $HOME/default fallback.
_XDG_RELATIVE_SUBPATH = {
    "OPENCODE_CONFIG_DIR": "opencode",
    "KILO_CONFIG_DIR": "kilo",
}


def _resolve_root(env_var_name: str, default_relative: str, env: dict) -> str:
    explicit = env.get(env_var_name)
    if explicit:
        return explicit
    if env_var_name in _XDG_RELATIVE_SUBPATH:
        xdg_config_home = env.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            return os.path.join(xdg_config_home, _XDG_RELATIVE_SUBPATH[env_var_name])
    home = env.get("HOME") or os.path.expanduser("~")
    return os.path.join(home, default_relative)


def resolve_gsd_tools_path(env: dict | None = None, isfile_fn=os.path.isfile):
    """Returns the first existing `<root>/gsd-core/bin/gsd-tools.cjs` path across the
    canonical multi-host candidate list, or `None` when none exist. Never raises, never
    prints -- the caller decides how to report a miss."""
    env = env if env is not None else dict(os.environ)
    for env_var_name, default_relative in GSD_CORE_ROOT_CANDIDATES:
        root = _resolve_root(env_var_name, default_relative, env)
        candidate = os.path.join(root, "gsd-core", "bin", "gsd-tools.cjs")
        if isfile_fn(candidate):
            return candidate
    return None


def resolve_model_catalog_cjs_path(gsd_tools_path, isfile_fn=os.path.isfile):
    """Returns `<dirname(gsd_tools_path)>/lib/model-catalog.cjs` when that sibling file
    exists, else `None`. Never resolves `model-catalog.json` directly -- the `.cjs` module
    itself resolves that relative to its own `__dirname`, so this skill only ever needs the
    module path."""
    if not gsd_tools_path:
        return None
    candidate = os.path.join(os.path.dirname(gsd_tools_path), "lib", "model-catalog.cjs")
    return candidate if isfile_fn(candidate) else None


def resolve_node_binary(which_fn=shutil.which):
    """Every `node -e` call in this skill resolves `node` through this one function so a
    test can inject a fake resolver."""
    return which_fn("node")


# A single-line Node expression that requires `process.argv[1]` (the model-catalog.cjs path,
# passed as a real argv element -- never string-interpolated into the script body, avoiding
# any quoting hazard from a path containing a space or quote character) and writes
# `JSON.stringify({tiers: ..., phaseTypes: ...})` to stdout. If `require()` throws (a future
# gsd-core version without these exports), the script instead writes the literal string
# `null` to stdout and exits 0 -- this makes "exports missing" and "require failed" both
# collapse to the SAME detectable signal (`stdout == "null"`) rather than needing the caller
# to parse a Node stack trace.
_AGENT_CATALOG_QUERY_SCRIPT = (
    "try { const m = require(process.argv[1]); "
    "process.stdout.write(JSON.stringify({tiers: m.AGENT_DEFAULT_TIERS, "
    "phaseTypes: m.AGENT_TO_PHASE_TYPE})); } "
    "catch (e) { process.stdout.write('null'); }"
)


def query_agent_catalog(node_bin, model_catalog_path, run_fn=subprocess.run):
    """Returns the parsed `{"tiers": {...}, "phaseTypes": {...}}` dict on a clean `node -e`
    run (exit 0, valid JSON, both keys present and non-empty dicts); returns `None` on ANY
    of: non-zero exit, timeout, unparseable stdout, a parsed result missing either key, or
    either key not being a non-empty dict. Never returns a partial/malformed result for the
    caller to guess about."""
    try:
        result = run_fn(
            [node_bin, "-e", _AGENT_CATALOG_QUERY_SCRIPT, model_catalog_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    tiers = parsed.get("tiers")
    phase_types = parsed.get("phaseTypes")
    if not isinstance(tiers, dict) or not tiers:
        return None
    if not isinstance(phase_types, dict) or not phase_types:
        return None
    return {"tiers": tiers, "phaseTypes": phase_types}
