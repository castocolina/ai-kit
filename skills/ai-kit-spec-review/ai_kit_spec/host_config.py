"""Host-config audit: modification times of a fixed list of real host-config files before and
after a lane. The list is seed data; it never decides anything, and a change is only an
observation."""

import os
import stat

HOST_CONFIG_FILES = (
    ".claude/settings.json",
    ".claude.json",
    ".config/opencode/opencode.json",
    ".config/opencode/opencode.jsonc",
    ".codex/config.toml",
    ".cursor/cli-config.json",
    ".cursor/mcp.json",
    ".cursor/hooks.json",
    ".copilot/mcp-config.json",
    ".gsd/defaults.json",
)

OBSERVATION = (
    "ai-kit-spec: observation: {path} changed during the lane; a host may rewrite its own "
    "config, so this does not show the lane changed it"
)
NOT_CHECKED = (
    "ai-kit-spec: observation: config folders moved by CLAUDE_CONFIG_DIR, CODEX_HOME, "
    "XDG_CONFIG_HOME or OPENCODE_CONFIG_DIR are not checked"
)
UNAVAILABLE = "unavailable"
UNAVAILABLE_FOR = "ai-kit-spec: observation: host-config audit unavailable for {path}"


def home(env) -> str:
    return env.get("HOME") or os.path.expanduser("~")


def snapshot(env, stat_fn=os.stat) -> dict[str, int | str | None]:
    """Modification time in nanoseconds per listed file; None for a missing path or a non-file,
    UNAVAILABLE when the path cannot be read. Never raises, never opens a file."""
    result: dict[str, int | str | None] = {}
    for rel in HOST_CONFIG_FILES:
        try:
            st = stat_fn(os.path.join(home(env), rel))
        except (FileNotFoundError, NotADirectoryError):
            result[rel] = None
            continue
        except (OSError, ValueError):
            result[rel] = UNAVAILABLE
            continue
        result[rel] = st.st_mtime_ns if stat.S_ISREG(st.st_mode) else None
    return result


def changed(before: dict, after: dict) -> list[str]:
    return [
        rel
        for rel in HOST_CONFIG_FILES
        if UNAVAILABLE not in (before.get(rel), after.get(rel))
        and before.get(rel) != after.get(rel)
    ]


def unavailable(before: dict, after: dict) -> list[str]:
    return [rel for rel in HOST_CONFIG_FILES if UNAVAILABLE in (before.get(rel), after.get(rel))]


def observation_lines(env, paths: list, unavailable_paths=()) -> list[str]:
    lines = [OBSERVATION.format(path=os.path.join(home(env), rel)) for rel in paths]
    if paths:
        lines.append(NOT_CHECKED)
    lines.extend(
        UNAVAILABLE_FOR.format(path=os.path.join(home(env), rel)) for rel in unavailable_paths
    )
    return lines
