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


def catalog_path(env: dict) -> str:
    """`${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/spec/model-catalog.json`.

    Ported from the sibling skill's `config_paths.catalog_path` (not imported).
    """
    if env.get("XDG_CACHE_HOME"):
        base = env["XDG_CACHE_HOME"]
    else:
        base = os.path.join(env.get("HOME", ""), ".cache")
    return os.path.join(base, "ai-kit", "spec", "model-catalog.json")
