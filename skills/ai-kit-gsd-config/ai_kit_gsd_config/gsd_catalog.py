"""Locates the installed gsd-core's gsd-tools.cjs and lib/model-catalog.cjs, and queries the
live AGENT_DEFAULT_TIERS/AGENT_TO_PHASE_TYPE export via a `node -e` subprocess call.

The install-root candidate list below mirrors the multi-host gsd-core install-root search
every GSD agent already performs (per-host env var with a `$HOME`-relative default, tried in
a fixed order) -- never narrow this to `~/.claude` alone; several hosts (Cursor, Codex,
OpenCode, Kilo, etc.) install gsd-core under their own config directory instead.
"""
import os
import shutil

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
