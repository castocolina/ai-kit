"""Opencode config path discovery (D-05) and local review-spec path."""

from __future__ import annotations

import os


def default_config_path(env: dict) -> str:
    """`${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}/opencode.jsonc`."""
    config_dir = env.get("OPENCODE_CONFIG_DIR")
    if config_dir:
        base = config_dir
    elif env.get("XDG_CONFIG_HOME"):
        base = os.path.join(env["XDG_CONFIG_HOME"], "opencode")
    else:
        base = os.path.join(env.get("HOME", ""), ".config", "opencode")
    return os.path.join(base, "opencode.jsonc")


def resolve_config_path(config_arg: str | None, env: dict) -> str:
    """`--config` is a full FILE path, not a directory."""
    if config_arg:
        return os.path.abspath(os.path.expanduser(config_arg))
    return default_config_path(env)


def local_review_spec_path(cwd: str) -> str:
    """`<cwd>/.aikit/review-spec.toml`."""
    return os.path.join(cwd, ".aikit", "review-spec.toml")
