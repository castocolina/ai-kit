import os
import shutil
import subprocess

from ai_kit_spec.cache import cache_base
from ai_kit_spec.vendor import _MODEL_TIER_SUFFIXES

RUNTIMES_TTL_SECONDS = 30 * 24 * 3600   # ~30 days: CLI/model presence is near-static

# ── Runtime/CLI detection ───────────────────────────────────────────────

KNOWN_CLIS = ("claude", "codex", "opencode", "grok", "cursor-agent", "gemini")


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
