"""XDG-honoring path resolution for the usage-metrics store.

Every function takes an explicit `env: dict` and never reads `os.environ`
directly, matching `tools/config_doctor_checks.py::resolve_runtime_config_paths`.
Precedence style ported from the sibling skill
`skills/ai-kit-opencode-providers` `config_paths.py`
(not imported — skill packages do not cross-import).
"""

from __future__ import annotations

import os


def usage_metrics_base(env: dict) -> str:
    """`${XDG_DATA_HOME:-$HOME/.local/share}/ai-kit/usage-metrics`."""
    return os.path.join(
        env.get("XDG_DATA_HOME")
        or os.path.join(env.get("HOME", ""), ".local", "share"),
        "ai-kit",
        "usage-metrics",
    )


def raw_dir(env: dict) -> str:
    return os.path.join(usage_metrics_base(env), "raw")


def refined_db_path(env: dict) -> str:
    return os.path.join(usage_metrics_base(env), "refined", "refined.db")


def cursors_dir(env: dict) -> str:
    return os.path.join(usage_metrics_base(env), "cursors")


def dashboard_html_path(env: dict) -> str:
    return os.path.join(usage_metrics_base(env), "dashboard.html")


def raw_jsonl_path(env: dict, source_name: str) -> str:
    return os.path.join(raw_dir(env), f"{source_name}.jsonl")


def claude_projects_dir(env: dict) -> str:
    """`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects`.

    Mirrors `tools/setup.py`'s CLAUDE_CONFIG_DIR-then-$HOME/.claude precedence.
    """
    return os.path.join(
        env.get("CLAUDE_CONFIG_DIR") or os.path.join(env.get("HOME", ""), ".claude"),
        "projects",
    )


def _xdg_data_home(env: dict) -> str:
    return env.get("XDG_DATA_HOME") or os.path.join(
        env.get("HOME", ""), ".local", "share"
    )


def opencode_db_path(env: dict) -> str:
    """`${XDG_DATA_HOME:-$HOME/.local/share}/opencode/opencode.db`."""
    return os.path.join(_xdg_data_home(env), "opencode", "opencode.db")


def opencode_storage_dir(env: dict) -> str:
    """`${XDG_DATA_HOME:-$HOME/.local/share}/opencode/storage`."""
    return os.path.join(_xdg_data_home(env), "opencode", "storage")


def rtk_history_db_path(env: dict) -> str:
    """`${XDG_DATA_HOME:-$HOME/.local/share}/rtk/history.db`."""
    return os.path.join(_xdg_data_home(env), "rtk", "history.db")


def rtk_tee_dir(env: dict) -> str:
    """`${XDG_DATA_HOME:-$HOME/.local/share}/rtk/tee`."""
    return os.path.join(_xdg_data_home(env), "rtk", "tee")


def codex_sessions_dir(env: dict) -> str:
    """`${CODEX_HOME:-$HOME/.codex}/sessions`."""
    return os.path.join(
        env.get("CODEX_HOME") or os.path.join(env.get("HOME", ""), ".codex"),
        "sessions",
    )


def cursor_projects_dir(env: dict) -> str:
    """`${CURSOR_CONFIG_DIR:-$HOME/.cursor}/projects`.

    Two-step only: CURSOR_CONFIG_DIR then $HOME/.cursor. The
    XDG_CONFIG_HOME/cursor leg of 04-01-PLAN.md's cli-config.json
    precedence is deliberately not ported — no live evidence confirms
    Cursor relocates SESSION data (projects/chats) the same way it
    relocates its config file.
    """
    return os.path.join(
        env.get("CURSOR_CONFIG_DIR")
        or os.path.join(env.get("HOME", ""), ".cursor"),
        "projects",
    )


def catalog_path(env: dict) -> str:
    """`${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/spec/model-catalog.json`.

    Ported from the sibling skill's `config_paths.catalog_path` (not imported).
    """
    if env.get("XDG_CACHE_HOME"):
        base = env["XDG_CACHE_HOME"]
    else:
        base = os.path.join(env.get("HOME", ""), ".cache")
    return os.path.join(base, "ai-kit", "spec", "model-catalog.json")
