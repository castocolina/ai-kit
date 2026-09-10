"""Declarative Config Doctor engine — check registry, path resolution, catalog.

Stdlib-only. Imports nothing from textual, setup.py, wizard_app.py, or any
skills/* package. This is the core engine Wave 2 (more rows) and Wave 3
(apply writers) extend without restructuring.
"""

from __future__ import annotations

import os
from typing import NamedTuple

import config_doctor_readers

UNKNOWN = config_doctor_readers.UNKNOWN

CONFIG_STATE_ABSENT = "absent"
CONFIG_STATE_OK = "ok"
CONFIG_STATE_UNREADABLE = "unreadable"

_READERS = {
    "claude": config_doctor_readers.read_json_checked,
    "cursor": config_doctor_readers.read_json_checked,
    "opencode": config_doctor_readers.read_jsonc_checked,
    "codex": config_doctor_readers.read_toml_checked,
}


class CheckRow(NamedTuple):
    id: str
    runtime: str
    scope: str
    check: str
    read: object
    recommended: object
    confidence: str
    why: str
    source: str
    apply: object = None
    reads_section_file: bool = True


def resolve_runtime_config_paths(env):
    """Absolute config-file paths for the four known runtimes.

    Precedence is each runtime's own, not ai-kit's installer paths:
    claude honors CLAUDE_CONFIG_DIR; cursor honors Cursor CLI's three-step
    layout (CURSOR_CONFIG_DIR, then XDG_CONFIG_HOME/cursor, then ~/.cursor)
    for cli-config.json; opencode honors OPENCODE_CONFIG_DIR > XDG_CONFIG_HOME
    > ~/.config; codex honors CODEX_HOME.
    """
    home = env.get("HOME", "")
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    if env.get("CURSOR_CONFIG_DIR"):
        cursor_dir = env["CURSOR_CONFIG_DIR"]
    elif env.get("XDG_CONFIG_HOME"):
        cursor_dir = os.path.join(env["XDG_CONFIG_HOME"], "cursor")
    else:
        cursor_dir = os.path.join(home, ".cursor")
    opencode_dir = env.get("OPENCODE_CONFIG_DIR")
    if opencode_dir:
        opencode_base = opencode_dir
    elif env.get("XDG_CONFIG_HOME"):
        opencode_base = os.path.join(env["XDG_CONFIG_HOME"], "opencode")
    else:
        opencode_base = os.path.join(home, ".config", "opencode")
    codex_dir = env.get("CODEX_HOME") or os.path.join(home, ".codex")
    return {
        "claude": os.path.join(claude_dir, "settings.json"),
        "opencode": os.path.join(opencode_base, "opencode.jsonc"),
        "codex": os.path.join(codex_dir, "config.toml"),
        "cursor": os.path.join(cursor_dir, "cli-config.json"),
    }


def evaluate_row(row, data):
    """Evaluate one CheckRow against parsed config data (or None if unreadable)."""
    value = UNKNOWN if data is None and row.reads_section_file else row.read(data)
    current_display = "unknown" if value is UNKNOWN else str(value)
    return {
        "id": row.id,
        "runtime": row.runtime,
        "scope": row.scope,
        "check": row.check,
        "current_value": value,
        "current_display": current_display,
        "recommended_value": row.recommended,
        "recommended_display": str(row.recommended),
        "confidence": row.confidence,
        "apply_eligible": row.apply is not None,
        "why": row.why,
        "source": row.source,
    }


def read_claude_retention(data):
    """cleanupPeriodDays, or Claude Code's documented 30-day default."""
    return config_doctor_readers.get_nested(data, "cleanupPeriodDays", default=30)


CONFIG_DOCTOR_ROWS = [
    CheckRow(
        id="claude-retention",
        runtime="claude",
        scope="runtime",
        check="Local transcript retention (cleanupPeriodDays)",
        read=read_claude_retention,
        recommended=3650,
        confidence="HIGH",
        why=(
            "Local transcript retention defaults to 30 days; raising it serves "
            "Phase 5's usage-metrics dashboard, which needs longer local history. "
            "cleanupPeriodDays: 0 must NEVER be recommended or applied — it is "
            "now rejected outright by Claude Code v2.1.89 rather than silently "
            "disabling persistence (the prior behavior GitHub #23710 described)."
        ),
        source="https://code.claude.com/docs/en/data-usage",
    ),
]


def build_catalog(env):
    """Presence-gated catalog: skip missing files; omit zero-row sections."""
    paths = resolve_runtime_config_paths(env)
    sections = []
    for runtime in ("claude", "opencode", "codex", "cursor"):
        path = paths[runtime]
        if not os.path.isfile(path):
            continue
        state, data = _READERS[runtime](path)
        matching = [row for row in CONFIG_DOCTOR_ROWS if row.runtime == runtime]
        if state == CONFIG_STATE_UNREADABLE:
            rows = [evaluate_row(row, None) for row in matching]
        else:
            rows = [evaluate_row(row, data) for row in matching]
        if not rows:
            continue
        sections.append({"runtime": runtime, "config_path": path, "rows": rows})
    return {"sections": sections}
