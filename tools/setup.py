#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["textual>=0.60"]
# ///
# ^ Consumed by `uv run tools/setup.py` to resolve textual into an ephemeral env
#   for the wizard ONLY. Plain `python3 tools/setup.py` ignores this comment; the
#   status-line render path never uses uv/textual (see plan Global Constraints).
"""ai-kit setup wizard + install engine (stdlib-only, like claude-status-line.py).

Invoked by tools/install.sh after it has guaranteed the repo and python3 are on
disk. Subcommands: install (default), reconfigure, uninstall, doctor, check.
Flags: --dry-run, --examples=all|none|<ids>, --config-doctor, and the headless
set --headless / --skills=all|name1,name2 / --with-statusline[=claude,cursor] /
--with-hooks (the last three require --headless).

Env overrides (mirrors install.sh):
  AI_KIT_DIR        install location (default: the checkout holding this script)
  CLAUDE_CONFIG_DIR Claude config dir (default: ~/.claude)
  CURSOR_CONFIG_DIR Cursor config dir (default: ~/.cursor)
  XDG_CONFIG_HOME   config base       (default: ~/.config)
"""

import argparse
import contextlib
import copy
import functools
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from collections import namedtuple
from typing import cast

CATEGORIES = ("agents", "commands", "skills")

# D-14: skills also linked into <pi_dir>/skills, derived from the claude
# selection. pi is a primary host and gets the cross-AI guide too, and the session
# wake (26-10: an AGENTS.md rule names it, so pi must be able to discover it).
PI_SKILLS = frozenset({"ai-kit-cross-ai", "jev-fast-decision", "ai-kit-session-wake",
                       "ai-kit-commit-fold"})
_LEGACY_ENTRY = "status-line.py"
_CLAUDE_ENTRY = "claude-status-line.py"
_CURSOR_ENTRY = "cursor-status-line.py"

# The status-line hosts, in the order a headless run wires them (SPEC R11 ordering edge).
STATUSLINE_HOSTS = ("claude", "cursor")

# Cursor's own `statusLine` schema (bundle zod: type/command plus three optional
# integer knobs). Anything outside this key set is not a shape ai-kit may write.
_CURSOR_STATUSLINE_KEYS = frozenset(
    {"type", "command", "padding", "updateIntervalMs", "timeoutMs"})


def _sibling(name):
    """A tools/ sibling module, importable whatever the caller's sys.path.

    setup.py is loaded through importlib by tests and hooks with no guarantee
    that tools/ sits on sys.path, and runtime code imports no sibling at module
    level (a broken renderer import must never block uninstalling) — every
    lazy sibling read goes through this one helper."""
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    return importlib.import_module(name)


def _command_ownership():
    """The sibling command-ownership parser (see _sibling for the lazy pattern)."""
    return _sibling("command_ownership")


def _jsonc_reader():
    """The sibling JSONC scanner, on the same lazy footing (see _sibling)."""
    return _sibling("config_doctor_readers")


_LEGACY_TOML = "statusline.toml"

Paths = namedtuple(
    "Paths",
    "install_dir claude_dir pi_dir backups_dir settings config_dir config_toml "
    "sample status_line statusline_doctor segments_dir cursor_dir "
    "cursor_hooks opencode_dir cursor_config_dir cursor_cli_config "
    "cursor_status_line cursor_config_toml cursor_sample",
)


def _config_doctor_checks():
    """The shared runtime-config resolver, lazily (see _sibling)."""
    return _sibling("config_doctor_checks")


def resolve_paths(env):
    """Resolve every path the installer touches, mirroring install.sh's env
    precedence: AI_KIT_DIR > the checkout holding this script; CLAUDE_CONFIG_DIR > ~/.claude;
    CURSOR_CONFIG_DIR > ~/.cursor; XDG_CONFIG_HOME/ai-kit > ~/.config/ai-kit.

    The Cursor *config* pair (`cursor_config_dir`/`cursor_cli_config`, D-21) is the
    CLI's own layout — non-blank CURSOR_CONFIG_DIR, then non-blank
    $XDG_CONFIG_HOME/cursor, then ~/.cursor — resolved ONLY through
    `config_doctor_checks.resolve_runtime_config_paths()`, never duplicated here.
    `cursor_dir` stays the hooks' separate, older two-step rule (backlog 999.2),
    so the two can legitimately disagree when XDG_CONFIG_HOME is set without
    CURSOR_CONFIG_DIR."""
    home = env.get("HOME", "")
    install_dir = (env.get("AI_KIT_DIR")
                   or os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    pi_dir = env.get("PI_CODING_AGENT_DIR") or os.path.join(home, ".pi", "agent")
    backups_dir = _sibling("config_doctor_appliers").backups_root(env)
    cursor_dir = env.get("CURSOR_CONFIG_DIR") or os.path.join(home, ".cursor")
    config_base = env.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    opencode_dir = (env.get("OPENCODE_CONFIG_DIR") or
                    os.path.join(config_base, "opencode"))
    config_dir = os.path.join(config_base, "ai-kit")
    cursor_cli_config = _config_doctor_checks().resolve_runtime_config_paths(env)["cursor"]
    cursor_config_dir = os.path.dirname(cursor_cli_config)
    return Paths(
        install_dir=install_dir,
        claude_dir=claude_dir,
        pi_dir=pi_dir,
        backups_dir=backups_dir,
        settings=os.path.join(claude_dir, "settings.json"),
        config_dir=config_dir,
        config_toml=os.path.join(config_dir, "claude-statusline.toml"),
        sample=os.path.join(install_dir, "tools", "claude-statusline.toml.sample"),
        status_line=os.path.join(install_dir, "tools", _CLAUDE_ENTRY),
        statusline_doctor=os.path.join(install_dir, "tools", "statusline-doctor.py"),
        segments_dir=os.path.join(config_dir, "segments"),
        cursor_dir=cursor_dir,
        cursor_hooks=os.path.join(cursor_dir, "hooks.json"),
        opencode_dir=opencode_dir,
        cursor_config_dir=cursor_config_dir,
        cursor_cli_config=cursor_cli_config,
        cursor_status_line=os.path.join(install_dir, "tools", _CURSOR_ENTRY),
        cursor_config_toml=os.path.join(config_dir, "cursor-statusline.toml"),
        cursor_sample=os.path.join(install_dir, "tools", "cursor-statusline.toml.sample"),
    )


# ── Status-line host configuration (lazily resolved from each HOST's module) ─
# Q2 ruling: setup resolves a host's defaults/config filename/provider
# namespaces by importing claude_host/cursor_host LAZILY — on the preview and
# wire paths only. NO copied defaults or host-settings table is kept here.
# These tuples name `Paths` attributes per host (paths indirection, not data).
_STATUSLINE_PATH_FIELDS = {
    "claude": ("config_toml", "sample", "status_line", "settings"),
    "cursor": ("cursor_config_toml", "cursor_sample", "cursor_status_line",
               "cursor_cli_config"),
}
_HOST_LABELS = {"claude": "Claude Code", "cursor": "Cursor CLI"}
_WIRING_LABELS = {"claude": "settings.json", "cursor": "cli-config.json"}

# Fallback UI glyph for an external segment whose header omits `icon=`.
DEFAULT_SEGMENT_ICON = "●"

# Absolute path to the shipped built-in segment UI inventory.
INVENTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "segments_inventory.toml")


def host_config(host):
    """The host's status-line ConfigSpec (env prefix, config filename, segment/
    layout defaults, provider namespaces). Imports the host module LAZILY —
    only the wizard's preview/wire paths call this (uninstall imports no
    renderer module), so a broken renderer import can never block uninstalling."""
    module_id = {"claude": "claude_host", "cursor": "cursor_host"}[host]
    return _sibling(module_id).HOST.config


def load_segment_inventory(path, host="claude"):
    """Load the built-in segment UI inventory for ONE host (description/sample/
    icon/line) keyed by segment name. Per-host dimension (D-04): each entry
    may list `hosts = ["claude"]` (the default when absent), `hosts =
    ["cursor"]` or both, and a cursor-listing entry may carry `cursor_line`
    (used as that host's line). Installer/wizard-only metadata; never read by
    the render path. Returns {key: {description, sample, icon, line}} for
    entries that list `host`. A missing/malformed file yields {} (fail-closed
    coverage is asserted by the arch test, not here)."""
    data = read_toml(path)
    inv = {}
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        entry_hosts = val.get("hosts")
        if entry_hosts is None:
            entry_hosts = ["claude"]
        if host not in entry_hosts:
            continue
        line = int(val.get("line", 0))
        description = str(val.get("description", ""))
        sample = str(val.get("sample", ""))
        if host == "cursor":
            # D-01: a Cursor entry may carry its own wording (cursor_description, cursor_sample)
            line = int(val.get("cursor_line", line))
            description = str(val.get("cursor_description", description))
            sample = str(val.get("cursor_sample", sample))
        inv[key] = {
            "description": description,
            "sample": sample,
            "icon": str(val.get("icon", "")),
            "line": line,
        }
    return inv


def build_segment_meta(inventory, overrides):
    """Merge the built-in inventory (description/sample/icon/line) with per-key
    icon+line overrides from the user's claude-statusline.toml. `overrides` is
    {key: {"icon"?: str, "line"?: int}}. description/sample are inventory-only
    (never overridable). Returns {key: {description, sample, icon, line}}."""
    meta = {}
    for key, entry in inventory.items():
        ov = overrides.get(key, {})
        meta[key] = {
            "description": entry["description"],
            "sample": entry["sample"],
            "icon": ov["icon"] if "icon" in ov else entry["icon"],
            "line": int(ov["line"]) if "line" in ov else entry["line"],
        }
    return meta


def _statusline_paths(paths, host):
    """Resolve `(config_toml, sample, entry, wiring)` for one status-line host
    from the single already-resolved `Paths` object. Every wizard/persist path
    for a host comes through here — no call site picks paths from a second
    table, and a Cursor call never reuses a Claude-only name (D-20/C-D23-1)."""
    return tuple(getattr(paths, attr) for attr in _STATUSLINE_PATH_FIELDS[host])


def _statusline_icon_line_overrides(config_toml):
    """Read per-segment icon+line overrides from the user's claude-statusline.toml, if
    present. Returns {key: {"icon"?: str, "line"?: int}}. The renderer ignores
    these wizard-side override keys; this is installer/wizard metadata only."""
    data = read_toml(config_toml)
    seg = data.get("segments")
    out = {}
    if isinstance(seg, dict):
        for key, val in seg.items():
            if isinstance(val, dict):
                ov = {}
                if "icon" in val:
                    ov["icon"] = str(val["icon"])
                if "line" in val:
                    with contextlib.suppress(TypeError, ValueError):
                        ov["line"] = int(val["line"])
                if ov:
                    out[key] = ov
    return out


def _external_enabled_in_toml(config_toml, ext_id, default_on=False):
    """Whether the user's claude-statusline.toml enables external segment `ext_id`.

    `default_on` is the value when the file says nothing about this id — it should
    mirror the RENDERER's default: a provider present in the segments dir renders
    by default (default_on=True), while a not-yet-installed bundled example is an
    offer (default_on=False). An explicit `segments.<id> = true|false` (bool) or
    `[segments.<id>] enabled = true|false` always wins over the default."""
    seg = read_toml(config_toml).get("segments")
    if not isinstance(seg, dict):
        return default_on
    val = seg.get(ext_id)
    if isinstance(val, bool):
        return val
    if isinstance(val, dict):
        e = val.get("enabled")
        return e if isinstance(e, bool) else default_on
    return default_on


def read_toml(path):
    """Parse the TOML at `path`. Missing / empty / malformed → {} (never raises).
    Read-only — the wizard writes back via surgical text patch, not re-emit."""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, IsADirectoryError):
        return {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def current_segments(path, host="claude"):
    """Resolved {key: bool} for one host: that host's SEGMENTS defaults (lazily
    from its HOST.config) merged with the file's [segments]. Unknown keys and
    non-bool values in the file are ignored (defaults win), the same lenient
    policy the renderer applies."""
    seg = dict(host_config(host).default_segments)
    for k, v in (read_toml(path).get("segments") or {}).items():
        if k in seg and isinstance(v, bool):
            seg[k] = v
    return seg


def current_layout(path, host="claude"):
    """Resolved layout for one host as a list of {"min_rows": int,
    "segments": [str]} dicts. Any [[line]] block in the file REPLACES the whole
    layout (all-or-nothing, matching the renderer); otherwise the host's own
    default layout (deep-copied from its HOST.config)."""
    raw = read_toml(path).get("line")
    if not raw:
        return [{"min_rows": ln.min_rows, "segments": list(ln.segments)}
                for ln in host_config(host).default_layout]
    return [{"min_rows": int(item.get("min_rows", 0)),
             "segments": list(item.get("segments", []))} for item in raw]


def _bool_env(value):
    return "1" if value else "0"


def _preview_child_env(host, env, segments):
    """The preview subprocess environment: the full ``os.environ`` plus the
    caller's overrides plus one ``<PREFIX>SEGMENT_<KEY>`` toggle per segment.
    The prefix comes from the host's lazily-resolved ``HOST.config`` (D-20), so
    a Cursor preview never receives Claude's ``CC_AI_KIT_*`` names — and the
    terminal is forced wide/tall so every row renders regardless of the
    wizard's own window size."""
    prefix = host_config(host).env_prefix
    child = {**os.environ, **env}   # inherit full env; overrides layer on top
    child.setdefault("STATUSLINE_COLS", "200")
    child.setdefault("STATUSLINE_LINES", "40")
    for key, on in segments.items():
        child[f"{prefix}SEGMENT_{key.upper()}"] = _bool_env(on)
    return child


def _preview_layout_file(layout, base_config, child, host):
    """Write the patched layout to a throwaway temp config and point the host's
    own ``CONFIG_FILE`` variable at it. Returns the temp path (the caller
    deletes it) or None when the write failed and the preview must be skipped."""
    patched = patch_layout(base_config or "", layout)
    fd, tmp_path = tempfile.mkstemp(suffix=".toml", prefix="ai_kit_preview_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(patched)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        return None
    child[host_config(host).env_prefix + "CONFIG_FILE"] = tmp_path
    return tmp_path


def render_preview(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    status_line, segments, sample_json, env, layout=None, base_config=None,
    host="claude",
):
    """Render the status line with the given segment toggles, for the live preview.

    Shells out to the HOST's real status-line entry (`python3 -S <entry>`)
    feeding `sample_json` on stdin and the toggles as the host's
    <PREFIX>SEGMENT_<KEY> env overrides (so it reflects in-memory edits before
    they are written). The prefix and the config-file variable come from the
    host's lazily-resolved `HOST.config` (D-20) — never a copied table, never a
    hardcoded Claude variable on a Cursor call. `env` carries only the keys to
    override (e.g. forced terminal size); it is merged ON TOP OF os.environ so
    the subprocess inherits PATH, HOME, and PYTHONPATH.

    When `layout` is provided (list of {"min_rows": int, "segments": [str]}
    dicts), a throwaway temp config is written with the patched layout and the
    subprocess reads it via the host's CONFIG_FILE variable. The temp file is
    deleted in a finally so it is never leaked, even on error.

    For Cursor the payload is the SAME shape plus a private synthetic cache
    under a temporary XDG_CACHE_HOME (D-24) — never a real `~/.cursor/auth.json`
    or `~/.cursor/cli-config.json` read, never a network reach: the synthetic
    cache is fresh, so no detached refresher is ever spawned.

    Returns the rendered text ("" on any failure — the preview is best-effort
    and must never crash the wizard)."""
    child = _preview_child_env(host, env, segments)
    tmp_path = None
    cache_dir = None
    try:
        if layout is not None:
            tmp_path = _preview_layout_file(layout, base_config, child, host)
            if tmp_path is None:
                return ""
        if host == "cursor":
            cache_dir = tempfile.mkdtemp(prefix="ai_kit_cursor_preview_")
            _seed_cursor_synthetic_cache(cache_dir, child)
        try:
            proc = subprocess.run(
                [sys.executable, "-S", status_line],
                input=sample_json, capture_output=True, text=True,
                env=child, timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            return ""
        if proc.returncode != 0:
            return ""
        return proc.stdout.rstrip("\n")
    finally:
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
        if cache_dir is not None:
            shutil.rmtree(cache_dir, ignore_errors=True)


def _seed_cursor_synthetic_cache(cache_dir, child):
    """D-24: give the Cursor preview a PRIVATE, token-free cache so the real
    Cursor entry renders its Cursor-only segments (showing `≈` on the
    mid-cycle synthetic values) without ever reading a credential or reaching
    the network. The cache schema comes from ``cursor_quota`` itself —
    imported lazily, on this preview path only — with ``core_synthetic_cache``
    shaping the data and ``probe_write_cache`` publishing it through the
    renderer's own atomic write into the temp dir's ai-kit cache root.
    ``XDG_CACHE_HOME`` is repointed at the temp dir and ``XDG_CONFIG_HOME``
    at an empty sibling, so the child's auth path resolves into nothing: even
    a stale cache could only end in ``auth_missing`` (no token → no fetch),
    the fresh cache never spawns the refresher, and afterwards the temp cache
    dir holds no ``usage.lock``."""
    cursor_quota = importlib.import_module("cursor_quota")
    cache_path, _lock = cursor_quota.probe_cache_paths(
        os.path.join(cache_dir, "ai-kit"))
    cursor_quota.probe_write_cache(
        cache_path, cursor_quota.core_synthetic_cache(time.time()))
    child["XDG_CACHE_HOME"] = cache_dir
    child["XDG_CONFIG_HOME"] = os.path.join(cache_dir, "xdg-config")


# One-line doc notes carried when a managed key is appended (keeps the recipe
# self-documenting). Lifted verbatim from tools/claude-statusline.toml.sample comments.
_SEGMENT_NOTES = {
    "path": "📂 working directory, ~-relative   (pinned)",
    "git_branch": "git branch name",
    "git_dirty": "working-tree dirty marker",
    "alt_git_worktree": "⎇ active linked-worktree name",
    "todo": "📝 current TODO  (📝 in-progress / ⏸ pending)",
    "model": "active model name (e.g. Opus)",
    "alt_time_ago": "time since the last transcript write",
    "alt_time_clock": "⏰ current wall-clock time",
    "effort": "🧠 reasoning-effort ladder + level ([auto] when auto)",
    "lines": "📃 lines added / removed this session",
    "alt_cost": "🪙 session cost in USD            (OFF by default)",
    "alt_time_session": "💬 total session duration",
    "alt_time_api": "📡 cumulative API response time",
    "render_time": "⏱ status-line's own render time, SLO/SLA-colored",
    "slowest": "🐌 slowest single segment this render (name + duration)",
    "alt_term_dimensions": "terminal size cols×lines (? if assumed)  (debug; OFF by default)",
    "context": "📊 context-window % used (and max) (pinned)",
    "chat_size": "💾 bytes since last compaction/total on disk (+ compaction count)",
    "alt_process_memory": "🧮 agent process memory (RSS)",
    "alt_h_rate_limit": "⚡ 5-hour rate-limit bucket (time-only reset)",
    "alt_w_rate_limit": "⚡ 7-day rate-limit bucket (weekday reset)",
}

# A managed key line, optionally commented, capturing key + trailing comment:
#   "# alt_cost = false   # 🪙 ..."   ->  key="alt_cost", trailing="# 🪙 ..."
_KEY_RE = re.compile(
    r"^(?P<indent>\s*)#?\s*(?P<key>\w+)\s*=\s*[^#\n]*?(?P<trail>\s*#.*)?$")


def _header_name(line):
    """The bracketed header name on `line` (commented or not), else None.
    "# [segments]" -> "segments"; "[ramp.context]" -> "ramp.context"."""
    m = re.match(r"^\s*#?\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*$", line)
    return m.group(1) if m else None


def patch_segments(text, changes):
    """Surgically set the given {key: bool} segment toggles in `text`'s raw TOML.

    Key-granularity: rewrites ONLY each changed key's `key = value` line in place
    (uncommenting it and the [segments] header), appends a missing key with its
    doc note, and leaves every other byte — comments, [palette], [ramp.*],
    [external], the version line — untouched. Returns the patched text."""
    if not changes:
        return text
    lines = text.splitlines(keepends=True)
    out = []
    in_seg = False
    seg_header_idx = None          # index in `out` of the [segments] header line
    written = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        name = _header_name(line)
        if name is not None:                       # a section header
            if in_seg:                             # leaving [segments]: append rest
                _append_missing(out, changes, written)
                in_seg = False
            if name == "segments":
                in_seg = True
                seg_header_idx = len(out)
                out.append(line)                   # may be uncommented below
                i += 1
                continue
            out.append(line)
            i += 1
            continue
        if in_seg:
            m = _KEY_RE.match(line)
            if m and m.group("key") in changes:
                key = m.group("key")
                trail = m.group("trail") or ""
                nl = "\n" if line.endswith("\n") else ""
                out.append(f"{m.group('indent')}{key} = "
                           f"{'true' if changes[key] else 'false'}{trail}{nl}")
                written.add(key)
                i += 1
                continue
        out.append(line)
        i += 1
    if in_seg:                                     # [segments] ran to EOF
        _append_missing(out, changes, written)
    # If we wrote any live key, the [segments] header must be live too.
    if written and seg_header_idx is not None:
        out[seg_header_idx] = re.sub(r"^(\s*)#\s*", r"\1", out[seg_header_idx], count=1)
    return "".join(out)


def _append_missing(out, changes, written):
    """Append any not-yet-written changed segment keys to the end of the
    [segments] block, each with its recipe doc note."""
    for key, val in changes.items():
        if key in written:
            continue
        note = _SEGMENT_NOTES.get(key, "")
        comment = f"          # {note}" if note else ""
        out.append(f"{key} = {'true' if val else 'false'}{comment}\n")
        written.add(key)


def _host_key_literal(value):
    """TOML literal for one host scalar: `true`/`false` or a two-place number."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return f"{float(value):.2f}"


def patch_host_keys(text, table, values):  # pylint: disable=too-many-locals
    """Surgically set the host scalars `values` ({key: bool | float | None}) under
    the `[table]` header of `text`'s raw TOML (D-03, D-12), like `patch_segments`.

    A live or commented key line is rewritten in place; a live `[table]` header wins
    over a commented one, which is uncommented in place only when no live one
    exists; a missing key is inserted after the last rewritten key line (else right
    after the header); a missing table is appended. A `None` value (no override)
    comments out a live key line and never appends. Every other byte is kept.
    Returns the input unchanged when no line changes."""
    if not values:
        return text
    lines = text.splitlines(keepends=True)
    headers = [i for i, line in enumerate(lines) if _header_name(line) == table]
    start = next((i for i in headers if not lines[i].lstrip().startswith("#")),
                 headers[0] if headers else None)
    if start is None:
        live = {k: v for k, v in values.items() if v is not None}
        if not live:
            return text
        head = text if not text or text.endswith("\n") else text + "\n"
        body = "".join(f"{k} = {_host_key_literal(v)}\n" for k, v in live.items())
        return f"{head}\n[{table}]\n{body}"
    end = next((i for i in range(start + 1, len(lines))
                if _header_name(lines[i]) is not None), len(lines))
    written, last_key = set(), start
    for i in range(start + 1, end):
        m = _KEY_RE.match(lines[i])
        if not m or m.group("key") not in values or m.group("key") in written:
            continue
        key, indent, value = m.group("key"), m.group("indent"), values[m.group("key")]
        if value is None:
            if not lines[i].lstrip().startswith("#"):
                lines[i] = f"{indent}# {lines[i][len(indent):]}"
            continue
        nl = "\n" if lines[i].endswith("\n") else ""
        lines[i] = f"{indent}{key} = {_host_key_literal(value)}{m.group('trail') or ''}{nl}"
        written.add(key)
        last_key = i
    missing = [k for k, v in values.items() if v is not None and k not in written]
    if missing:
        if lines[last_key] and not lines[last_key].endswith("\n"):
            lines[last_key] += "\n"
        lines[last_key + 1:last_key + 1] = [
            f"{k} = {_host_key_literal(values[k])}\n" for k in missing]
    if written or missing:
        lines[start] = re.sub(r"^(\s*)#\s*", r"\1", lines[start], count=1)
    return "".join(lines)


def current_host_keys(path, host="claude"):
    """Each host scalar table's values from the file at `path` (D-03, D-12): the
    defaults for a missing file, table or key, and for an invalid value; a valid
    file value replaces its default, coerced to its kind (lenient, like
    `current_segments`)."""
    common = _sibling("common_config")
    raw = read_toml(path)
    result = {}
    for table, defaults in (host_config(host).host_scalars or {}).items():
        values = dict(defaults)
        section = raw.get(table)
        for key, value in (section.items() if isinstance(section, dict) else []):
            if common.cfg_host_key_problem(defaults, key, value) is not None:
                continue
            if common.cfg_scalar_kind(defaults[key]) == "bool":
                values[key] = bool(value)
            elif value is not None:
                values[key] = float(value)
        result[table] = values
    return result


def cursor_limit_text(env, now):
    """The Cursor spend limit as ai-kit's own Cursor quota cache holds it (D-12).

    A local read of one file only: no API call, no refresher, no directory is
    created, and never `~/.cursor`."""
    not_read = ("Cursor spend limit: not read yet (no ai-kit Cursor quota cache) "
                "— set an override to alert")
    common, cq = _sibling("common_config"), _sibling("cursor_quota")
    base = common.cfg_cache_base(dict(env))
    if not os.path.isabs(base):
        return not_read
    cache = cq.probe_read_cache(os.path.join(base, "cursor", "usage.json"))
    if cache is None:
        return not_read
    quota = cq.core_quota_state(cache, now)
    if quota.od_kind == "fixed" and quota.od_ceiling_usd:
        fetched = quota.fetched_at if quota.fetched_at is not None else now
        age = _sibling("common_types").fmt_ago(max(0, now - fetched))
        return (f"Cursor spend limit: ${quota.od_ceiling_usd:.2f} "
                f"(ai-kit quota cache, read {age}; inferred ≈)")
    if quota.od_kind == "unlimited":
        return "Cursor spend limit: none (unlimited on Cursor) — set an override to alert"
    if quota.od_kind == "disabled":
        return "Cursor spend limit: none (extra spend is off on Cursor)"
    return not_read


def _render_line_blocks(lines):
    """The full [[line]] section as live TOML text (all-or-nothing).

    Emits ONLY the TOML [[line]] blocks — no ## comment headers — so the
    output is byte-identical across re-runs (idempotent)."""
    chunks = []
    for row in lines:
        segs = ", ".join(f'"{s}"' for s in row["segments"])
        chunks.append(f"[[line]]\nmin_rows = {int(row['min_rows'])}\n"
                      f"segments = [{segs}]\n")
    return "".join(chunks)


def patch_layout(text, lines):
    """Replace the file's [[line]] layout with `lines` (all-or-nothing), preserving
    every other section byte-for-byte. `lines` is a list of
    {"min_rows": int, "segments": [str]} dicts.

    Idempotent: running patch_layout twice yields a byte-identical result. Any
    prior wizard-authored `##` comment lines immediately preceding the [[line]]
    region are stripped during the parse pass so they do not accumulate."""
    src = text.splitlines(keepends=True)
    out = []
    block = _render_line_blocks(lines)
    region_start = None
    i = 0
    n = len(src)
    while i < n:
        name = _header_name(src[i])
        if name == "line":
            # Consume the whole contiguous [[line]] region: this header, its body,
            # and any immediately-following [[line]] headers + bodies.
            if region_start is None:
                # Also strip any wizard-authored ## header lines that immediately
                # precede this [[line]] block (they would accumulate on re-runs).
                while out and out[-1].lstrip().startswith("##"):
                    out.pop()
                region_start = len(out)
            i += 1
            while i < n:
                nm = _header_name(src[i])
                if nm == "line":
                    i += 1
                    continue
                if nm is None:
                    # a body line (min_rows / segments / blank) — part of the region
                    is_body = src[i].strip() == "" or re.match(
                        r"^\s*#?\s*(min_rows|segments)\b", src[i])
                    if is_body:
                        i += 1
                        continue
                break
            continue
        out.append(src[i])
        i += 1
    if region_start is None:                 # no [[line]] region existed: append
        if out and not out[-1].endswith("\n"):
            out.append("\n")
        out.append(block)
    else:
        out.insert(region_start, block)
    return "".join(out)


def _offline_dry_render(entry, candidate, sample_json, host):
    """Render the CANDIDATE once, fully offline (D-19/D-24), before it is
    published: the host's real entry with that host's CONFIG_FILE variable
    pointed at the candidate file.

    For Cursor the child gets a fresh synthetic quota cache under a temporary
    ``XDG_CACHE_HOME`` and an empty ``XDG_CONFIG_HOME`` (same seeding as the
    preview), so the render can neither fetch nor schedule the detached
    refresher — a fresh cache never needs a refresh and no auth path resolves.
    The child runs with the entry's ``--check-render`` flag: the renderer stays
    never-blank in normal use, but in check mode it exits nonzero when the
    pipeline raised or any segment builder failed — renderer-reported failures
    must reject the candidate, not sail through on the exit-code-0 the normal
    renderer guarantees even while printing its error line.
    Returns True when the entry exits 0; any spawn failure counts as a
    rejection (fail closed: an unrenderable candidate is never published).
    """
    child = dict(os.environ)
    child[host_config(host).env_prefix + "CONFIG_FILE"] = candidate
    child.setdefault("STATUSLINE_COLS", "200")
    child.setdefault("STATUSLINE_LINES", "40")
    cache_dir = None
    try:
        if host == "cursor":
            cache_dir = tempfile.mkdtemp(prefix="ai_kit_cursor_render_")
            _seed_cursor_synthetic_cache(cache_dir, child)
        try:
            proc = subprocess.run(
                [sys.executable, "-S", entry, "--check-render"], input=sample_json,
                capture_output=True, text=True, env=child,
                timeout=10, check=False)
        except (OSError, subprocess.SubprocessError):
            return False
        return proc.returncode == 0
    finally:
        if cache_dir is not None:
            shutil.rmtree(cache_dir, ignore_errors=True)


def _candidate_file(path, text):
    """Write the candidate TOML to a sibling temp file in the target's own
directory (same filesystem, so the later ``os.replace`` is atomic). Returns the
temp path, or None when the candidate could not be written at all."""
    dirname = os.path.dirname(path) or "."
    try:
        os.makedirs(dirname, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".candidate")
    except OSError:
        # makedirs/mkstemp run outside the fdopen handler above: an
        # unwritable target directory must degrade to "no candidate" (the
        # caller rejects the publish) instead of raising out of the commit.
        return None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        return None
    return tmp


def _doctor_structural_ok(candidate, statusline_doctor, host):
    """The OFFLINE structural step of a publish: this host's doctor in
``--host <host> --check <candidate>`` mode with that host's own config-file env
variable pointed at the candidate bytes, so even the doctor's resolution step
runs against exactly what is about to be published. Never ``--doctor`` (that is
the fetch-capable path). Returns ``(ok, reason)``."""
    env = dict(os.environ)
    env[host_config(host).env_prefix + "CONFIG_FILE"] = candidate
    try:
        proc = subprocess.run([sys.executable, "-S", statusline_doctor,
                               "--host", host, "--check", candidate],
                              capture_output=True, text=True, env=env,
                              timeout=10, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if proc.returncode == 0:
        return True, ""
    return False, ((proc.stdout or "") + (proc.stderr or "")).strip()


def _report_rejected_candidate(reason, render_rejected):
    """Say OUT LOUD why a candidate was not published (a swallowed reason left
the user and the install summary with no clue what to fix)."""
    label = "dry render rejected" if render_rejected else "doctor rejected"
    print(f"{label} the status-line config:", file=sys.stderr)
    for line in reason.splitlines():
        print(f"  {line}", file=sys.stderr)


def write_toml_preserving(path, text, statusline_doctor, host="claude"):
    """Publish `text` to `path` OFFLINE (D-23 / D23-C3 / D-19): validate a
    candidate FIRST, then publish it atomically — the live file is never briefly
    invalid.

    1. write the candidate to a sibling temp file in the same directory;
    2. validate it OFFLINE by the doctor's structural check with this host's own
       config-file env var pointed at the candidate (`--host <host>
       --check <candidate>`), so even the doctor's resolution step is exercised
       against the exact bytes about to be published;
    3. when the caller also hands over the host's entry (the `(doctor, entry)`
       shape), dry-render that candidate OFFLINE with the host's sample payload
       — for Cursor against a fresh synthetic quota cache, so the render
       triggers no fetch and no detached refresher (the network-active
       `--doctor` is never used on a save path);
    4. only on success publish it with `os.replace()` and return True. A
       rejected candidate is deleted, the LIVE file is left byte-untouched, the
       reason is printed (a swallowed reason left the user and the install
       summary with no clue what to fix), and False is returned — the wizard
       must never leave a broken config (§5.1).

    `statusline_doctor` may be a path or a (doctor, entry) tuple; with a plain
    path only the structural step runs (the legacy/headless call shapes)."""
    entry = None
    if isinstance(statusline_doctor, tuple):
        statusline_doctor, entry = statusline_doctor
    tmp = _candidate_file(path, text)
    if tmp is None:
        return False
    ok, reason = _doctor_structural_ok(tmp, statusline_doctor, host)
    render_rejected = False
    if ok and entry is not None and not _offline_dry_render(
            entry, tmp, _read_sample_json(host), host):
        # Step 3: the offline synthetic-quota dry render rejected these bytes.
        ok = False
        render_rejected = True
    if not ok:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        if reason or render_rejected:
            _report_rejected_candidate(reason, render_rejected)
        return False
    try:
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except OSError as exc:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        # A rejected candidate has its own message above; a FAILED publish needs
        # one too, or the install summary reports a host as unwritable with no
        # reason at all. The live file is still byte-untouched here.
        print(f"warn: could not publish {path}: {exc}", file=sys.stderr)
        return False
    return True


_DESC_MAX = 200


def _cap_desc(desc: str) -> str:
    """Collapse whitespace to one line and cap at ``_DESC_MAX`` chars,
    preferring a word boundary and marking truncation with an ellipsis."""
    desc = " ".join(desc.split())
    if len(desc) <= _DESC_MAX:
        return desc
    cut = desc[:_DESC_MAX - 1]
    sp = cut.rfind(" ")
    if sp > _DESC_MAX // 2:  # prefer a word boundary when one is close
        cut = cut[:sp]
    return cut.rstrip() + "…"


def _read_component_desc(abspath: str) -> str:
    """Return the ``description:`` value from a component's YAML frontmatter.

    For skills ``abspath`` is a directory — the frontmatter lives in
    ``{abspath}/SKILL.md``.  For commands and agents it is the ``.md`` file
    directly.  Handles both inline values (``description: text``) and YAML
    block scalars (``description: >-`` or ``|`` with the text on the
    following indented lines), folding multi-line values into a single
    space-joined string.  The result is collapsed to one line and capped at
    ``_DESC_MAX`` characters (an ellipsis marks truncation).  Returns ``""``
    if the file is absent, unreadable, or has no ``description`` in its
    frontmatter.
    """
    if not abspath:
        return ""
    candidate = os.path.join(abspath, "SKILL.md") if os.path.isdir(abspath) else abspath
    try:
        with open(candidate, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return ""
    if not lines or lines[0].rstrip() != "---":
        return ""

    desc = ""
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.rstrip() == "---":  # frontmatter ended without a description
            return ""
        if line.startswith("description:"):
            rest = line[len("description:"):].strip()
            if rest[:1] in ("|", ">"):  # YAML block scalar — gather the body
                parts = []
                i += 1
                while i < len(lines):
                    nxt = lines[i]
                    if nxt.rstrip() == "---":
                        break
                    if nxt.strip() and not nxt[:1].isspace():
                        break  # a new, less-indented top-level key
                    parts.append(nxt.strip())
                    i += 1
                desc = " ".join(p for p in parts if p)
            else:  # inline value (optionally quoted)
                desc = rest.strip("'\"")
            break
        i += 1

    return _cap_desc(desc)


def validate_entry(cat, path):
    """Port of install.sh validate_entry. skills: a dir containing SKILL.md.
    commands/agents: a *.md file whose first line is the YAML front-matter
    fence '---'. Unknown category: False."""
    if cat == "skills":
        return os.path.isdir(path) and os.path.isfile(os.path.join(path, "SKILL.md"))
    if cat in ("commands", "agents"):
        if not (os.path.isfile(path) and path.endswith(".md")):
            return False
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                first = f.readline()
        except OSError:
            return False
        return first.startswith("---")
    return False


def enumerate_entries(install_dir):
    """For each category, the sorted list of (name, abspath) entries in the
    freshly-synced checkout that pass validate_entry. Malformed entries are
    dropped (install.sh warned + counted them; the wizard simply omits them)."""
    out = {}
    for cat in CATEGORIES:
        src = os.path.join(install_dir, cat)
        found = []
        if os.path.isdir(src):
            for name in sorted(os.listdir(src)):
                path = os.path.join(src, name)
                if validate_entry(cat, path):
                    found.append((name, path))
        out[cat] = found
    return out


# Mirror claude-status-line.py's canonical `_SEG_HEADER_RE` EXACTLY (whitespace-flexible
# after `#` and after the colon; NO leading indent — the marker sits at column 0)
# so the installer and the renderer never disagree on which files are providers
# (the two files can't import each other — hyphenated filename, see L64 — so the
# pattern is duplicated; keep it byte-identical to claude-status-line.py's).
_SEG_HEADER_RE = re.compile(r"^#\s*ai-kit-segment:\s*(.*?)\s*$")


def _parse_segment_header(text):
    """Parse an external segment's `# ai-kit-segment: k=v k=v …` marker line into
    a {key: value} dict. Recognizes the renderer keys (`id`, `line`, `after`,
    `before`, `timeout`, `ttl`) AND the wizard-only OPTIONAL UI keys
    (`name`, `description`, `icon`, `sample`) — the latter are read installer-side
    only; the renderer's parser never sees them (render-path purity). Scans the
    head of the file; returns None when no marker line is present. Bare tokens
    (no `=`) are ignored. Values may be double-quoted to hold spaces/punctuation
    (e.g. `description="System available RAM"`); quoting is wizard-side only —
    the renderer's parser (`core_parse_segment_header` in claude-status-line.py) does
    not need it since it never reads the UI keys. This is the single source of
    truth for the `id` that drives the `segments.<id>` toggle."""
    for line in text.splitlines():
        m = _SEG_HEADER_RE.match(line)
        if m:
            fields = {}
            try:
                tokens = shlex.split(m.group(1), posix=True)
            except ValueError:
                tokens = m.group(1).split()   # malformed quotes → graceful fallback
            for tok in tokens:
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    fields[k] = v
            return fields
    return None


def discover_example_segments(examples_dir):
    """Scan `examples_dir` for shippable example external segments, each carrying
    a `# ai-kit-segment: … id=<id> …` header. Returns a list of
    {id, filename, name, path, default_on, description, icon, sample, line}
    sorted by id. `filename` is the real filesystem filename (used as the
    install-destination by install_example_segments). `default_on` is always
    True (every example is OFFERED pre-checked). The UI keys come from the
    OPTIONAL self-describing header (`name`/`description`/`icon`/`sample`);
    missing fields fall back to id-as-name, blank description,
    DEFAULT_SEGMENT_ICON, and the last layout line. Files without the marker or
    without an `id` are skipped; a missing dir yields []."""
    out = []
    try:
        names = sorted(os.listdir(examples_dir))
    except OSError:
        return out
    for name in names:
        path = os.path.join(examples_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                head = f.read(4096)
        except OSError:
            continue
        fields = _parse_segment_header(head)
        if not fields or "id" not in fields:
            continue
        out.append(_external_entry(fields, name, path, provenance="bundled"))
    return sorted(out, key=lambda e: e["id"])


def _external_entry(fields, filename, path, provenance):
    """Build the wizard-facing external-segment dict from a parsed header, applying
    the self-describing fallbacks (id-as-name, blank description, default icon,
    last layout line). `filename` is the real filesystem filename (used as the copy
    destination); `name` is the UI display label (header `name=` or id fallback).
    `provenance` is "bundled" or "user"."""
    try:
        line = int(fields["line"]) if "line" in fields else \
            len(host_config("claude").default_layout) - 1
    except (TypeError, ValueError):
        line = len(host_config("claude").default_layout) - 1
    seg_id = fields["id"]
    return {
        "id": seg_id,
        "filename": filename if filename is not None else seg_id,
        "name": fields.get("name") or seg_id,
        "path": path,
        "default_on": True,
        "description": fields.get("description", ""),
        "icon": fields.get("icon") or DEFAULT_SEGMENT_ICON,
        "sample": fields.get("sample", ""),
        "line": line,
        "provenance": provenance,
    }


def _discover_user_segments(segments_dir):
    """Scan the user dir (the same one the renderer reads) for external segments,
    tagged provenance="user". Same header contract as bundled examples; a missing
    dir yields []."""
    out = []
    try:
        names = sorted(os.listdir(segments_dir))
    except OSError:
        return out
    for name in names:
        path = os.path.join(segments_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                head = f.read(4096)
        except OSError:
            continue
        fields = _parse_segment_header(head)
        if not fields or "id" not in fields:
            continue
        out.append(_external_entry(fields, name, path, provenance="user"))
    return out


def discover_external_segments(paths, examples_dir, host="claude"):
    """Merge bundled (examples/segments/) and user (this host's provider dir)
    external segments. Bundled examples are host-neutral drop-ins; the user
    dimension is read from `_provider_dir(paths, host)` so a Cursor host never
    sees Claude's user segments and vice versa (D-22). Each entry carries
    {id, filename, name, path, default_on, description, icon, sample, line,
    provenance} where provenance is
    "bundled" | "user". On an id collision the USER entry wins (it shadows
    the bundled copy the user customized). All entries default OFF in the wizard
    unless claude-statusline.toml enables them. `filename` is preserved from the
    winning entry and drives the install-destination in install_example_segments.
    Returned list is id-sorted."""
    merged = {}
    for e in discover_example_segments(examples_dir):
        merged[e["id"]] = e
    for e in _discover_user_segments(_provider_dir(paths, host)):
        merged[e["id"]] = e        # user overrides bundled
    return sorted(merged.values(), key=lambda e: e["id"])


def _atomic_write_executable(dst, data):
    """Write `data` to `dst` atomically and 0o755: a temp file in the SAME dir +
    os.replace, so an interrupted write never leaves a truncated (yet chmod-+x,
    about-to-be-exec'd) provider in place. Raises OSError on a bad/blocked dest
    (a name that is a directory, an unwritable dir) — the caller skips it."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dst), prefix=".seg-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, 0o755)
        os.replace(tmp, dst)                         # atomic; both already +x
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def install_example_segments(examples, config_dir, seg_state=None,
                            provider_dir="segments"):
    """Install each chosen example external segment: copy it into the XDG-aware
    provider dir (`config_dir/<provider_dir>` — `config_dir` comes from
    resolve_paths, so XDG_CONFIG_HOME is already honored; `provider_dir` comes
    from the host's own ConfigSpec so a Cursor example lands in
    `segments-cursor`, never Claude's dir), make it executable, and enable its
    `segments.<id>` toggle (set `seg_state[id] = True` when a state dict is
    given). Idempotent: a destination already holding the same bytes is left
    untouched and a re-run never duplicates (one fixed dest path per name); a
    stale copy is refreshed to the source bytes via an atomic temp-file replace.
    A provider whose source can't be read or whose destination is bad/blocked
    (name already a directory, unwritable dir) is SKIPPED with a warning rather
    than aborting the whole install. Returns the installed ids in input order."""
    seg_dir = os.path.join(config_dir, provider_dir)
    os.makedirs(seg_dir, exist_ok=True)
    ids = []
    for ex in examples:
        try:
            with open(ex["path"], "rb") as f:
                want = f.read()
        except OSError:
            continue
        dst = os.path.join(seg_dir, ex["filename"])
        cur = None
        if os.path.isfile(dst):
            try:
                with open(dst, "rb") as f:
                    cur = f.read()
            except OSError:
                cur = None
        try:
            if cur != want:                          # refresh only when changed
                _atomic_write_executable(dst, want)
            else:
                os.chmod(dst, 0o755)                 # unchanged: just reassert +x
        except OSError as e:
            print(f"examples: skipped {ex['filename']} ({e})", file=sys.stderr)
            continue
        if seg_state is not None:
            seg_state[ex["id"]] = True               # enable segments.<id>
        ids.append(ex["id"])
    return ids


def resolve_example_selection(flag, examples):
    """Resolve which discovered `examples` to install from the `--examples` value.
    None (flag absent) or `all` → every example (they are default-ON / pre-checked);
    `none` → []; otherwise a comma/space-separated id list → the matching examples
    in discovery order, unknown ids ignored. `all`/`none` are case-insensitive."""
    if flag is None:
        return list(examples)
    norm = flag.strip().lower()
    if norm == "all":
        return list(examples)
    if norm == "none":
        return []
    wanted = {t for t in re.split(r"[,\s]+", flag.strip()) if t}
    return [e for e in examples if e["id"] in wanted]


def select_examples(examples, flag, tty):
    """Choose which example external segments to install. A `--examples` flag ⇒
    governed PURELY by resolve_example_selection with NO prompting. No flag ⇒
    accept the pre-checked default (every example, default-ON). Interactive
    selection returns in Phase 2 via the Textual app (Task 2.1).
    Returns the chosen list of example dicts."""
    if flag is not None:
        return resolve_example_selection(flag, examples)
    return list(examples)


def _is_inside(path, root):
    """True when path (its parent resolved, its leaf kept) lies in root, both
    resolved, compared by path components (so ai-kit is not inside ai-kit-old).
    The leaf is not followed, so a symlink inside the kit is not taken out of it."""
    leaf = os.path.join(os.path.realpath(os.path.dirname(path)), os.path.basename(path))
    real_root = os.path.realpath(root)
    try:
        return leaf == real_root or os.path.commonpath([leaf, real_root]) == real_root
    except ValueError:
        return False


def installed_links(claude_dir, install_dir):
    """For each category, the {name: target} of ai-kit symlinks currently under
    ~/.claude/<category>/ — i.e. symlinks whose target points into install_dir.
    Foreign symlinks and real files are ignored. This IS the persisted skill
    selection: no state file (§4)."""
    out = {}
    for cat in CATEGORIES:
        dest = os.path.join(claude_dir, cat)
        found = {}
        if os.path.isdir(dest):
            for name in sorted(os.listdir(dest)):
                link = os.path.join(dest, name)
                if not os.path.islink(link):
                    continue
                target = os.readlink(link)
                if _is_inside(os.path.join(os.path.dirname(link), target), install_dir):
                    found[name] = target
        out[cat] = found
    return out


class _StdTty:
    """Adapts separate sys.stdin/sys.stdout into one tty-like object exposing
    readline()/write()/flush()/isatty()/close(). close() is a no-op — we must
    not close the process's own std streams."""

    def __init__(self, rstream, wstream):
        """Store the read and write streams."""
        self._r, self._w = rstream, wstream

    def readline(self):
        """Read one line from stdin."""
        return self._r.readline()

    def write(self, text):
        """Write text to stdout."""
        return self._w.write(text)

    def flush(self):
        """Flush the write stream."""
        return self._w.flush()

    def isatty(self):
        """Always True — only constructed when both streams are real TTYs."""
        return True

    def tell(self):
        """Raise OSError; std streams are not seekable."""
        raise OSError("std tty is not seekable")

    def seek(self, offset, whence=0):
        """Raise OSError; std streams are not seekable."""
        raise OSError("std tty is not seekable")

    def close(self):
        """No-op — must not close the process's own std streams."""


def open_tty():
    """Open an interactive terminal stream, or return None when none exists.

    Prefers /dev/tty (so `curl | bash` — where stdin is the script pipe — still
    reaches the keyboard). The handle is built getpass-style as
    ``TextIOWrapper(FileIO(os.open("/dev/tty", O_RDWR|O_NOCTTY)))`` rather than
    ``open("/dev/tty", "r+")``: builtin r+ creates a BufferedRandom that demands
    a seekable raw stream, and a terminal is not seekable, so it raises
    "not seekable" on every TTY. The FileIO+TextIOWrapper path has no seek probe.

    When /dev/tty cannot be opened (no controlling terminal — IDE task runners,
    some sandbox contexts), fall back to sys.stdin/stdout ONLY when BOTH are real
    TTYs — a direct local run where stdin literally is the keyboard. When nothing
    is usable, return None; the caller fails closed (no headless path)."""
    try:
        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
        return io.TextIOWrapper(
            io.FileIO(fd, "r+"), encoding="utf-8", line_buffering=True
        )
    except OSError:
        pass
    if _stream_isatty(sys.stdin) and _stream_isatty(sys.stdout):
        return _StdTty(sys.stdin, sys.stdout)
    return None


@contextlib.contextmanager
def stdin_on_tty():
    """Point fd 0 at the controlling terminal for the duration of the wizard.

    Under ``curl … | bash`` the process inherits the *script pipe* as stdin, so
    fd 0 is not a TTY.  Textual's Linux driver reads keystrokes from
    ``sys.__stdin__.fileno()`` (fd 0) — not from any handle we pass it — so
    without this the full-screen wizard cannot be driven and would hang or abort.
    When fd 0 is already a TTY (a direct terminal run, or our PTY tests) this is
    a no-op.  The original fd 0 is restored on exit (even on exception).

    Only stdin is touched: Textual writes its escape sequences to stderr (fd 2),
    which under ``curl | bash`` is still the user's terminal, so stdout/stderr are
    left exactly as the caller arranged them."""
    if os.isatty(0):
        yield
        return
    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    except OSError:
        # No controlling terminal — require_tty() has already failed closed
        # upstream, so this branch is unreachable in the current call graph (a
        # usable tty is a precondition for reaching launch_wizard). Kept as
        # defense-in-depth: proceed without redirect rather than mask the path.
        # NOTE: a future caller that invokes stdin_on_tty() WITHOUT the
        # require_tty gate would leave fd 0 unredirected and the TUI undrivable;
        # gate any new call site the same way rather than relying on this.
        yield
        return
    saved = os.dup(0)
    try:
        os.dup2(tty_fd, 0)
        os.close(tty_fd)
        yield
    finally:
        os.dup2(saved, 0)
        os.close(saved)


def is_interactive(tty):
    """True when a usable tty stream is present (a human at a terminal)."""
    return tty is not None


def require_tty(tty):
    """Fail closed: the wizard is interactive-only. With no usable terminal,
    print one clear reason and exit non-zero — never a silent headless default.
    Returns `tty` unchanged so callers can narrow the type in one expression:
    ``tty = require_tty(open_tty())``."""
    if not is_interactive(tty):
        print("setup: no interactive terminal available — run this in a real "
              "terminal (the wizard cannot run headless).", file=sys.stderr)
        sys.exit(2)
    return tty


def _tty_write(tty, text):
    """Write to the tty without consuming pending input. An io.StringIO shares
    one buffer for reads and writes; a naive write at the read cursor would
    clobber seeded test input. We append the prompt at the END of the buffer and
    restore the read cursor, so seeded input survives. A real /dev/tty is not
    seekable (separate read/write underneath), so we just write."""
    try:
        read_pos = tty.tell()
        tty.seek(0, 2)  # end of buffer
        tty.write(text)
        tty.seek(read_pos)
    except (OSError, ValueError):
        tty.write(text)
    tty.flush()


def ask_yes_no(tty, prompt, default=False):
    """Prompt on the tty for a yes/no. Blank line or EOF returns `default`.
    Accepts y/yes/n/no (case-insensitive)."""
    suffix = " [Y/n] " if default else " [y/N] "
    _tty_write(tty, prompt + suffix)
    line = tty.readline()
    if not line:
        return default
    answer = line.strip().lower()
    if not answer:
        return default
    if answer in ("y", "yes"):
        return True
    if answer in ("n", "no"):
        return False
    return default


def new_counts():
    """Mutable counter dict threaded through the link/unlink/prune ops, mirroring
    install.sh's n_linked / n_relinked / n_pruned / n_skip_foreign / n_skip_real."""
    return {"linked": 0, "relinked": 0, "unlinked": 0,
            "pruned": 0, "skip_foreign": 0, "skip_real": 0}


def _install_dir_of(link, target):
    """The install root a target points into — its first two path components are
    <install_dir>/<category>; we treat the target's dirname's dirname as root."""
    return os.path.dirname(os.path.dirname(target))


def link_one(link_path, target, dry, counts, install_dir=None):
    """Create or refresh one symlink, never clobbering a real file or a foreign
    symlink (port of install.sh link_one). 'foreign' = an existing symlink whose
    target is NOT inside the same install dir as `target`. Nested hook targets
    pass their explicit install root; category links retain the inferred root."""
    install_dir = install_dir or _install_dir_of(link_path, target)
    if os.path.islink(link_path):
        cur = os.readlink(link_path)
        if cur == target:
            return
        if _is_inside(os.path.join(os.path.dirname(link_path), cur), install_dir):
            counts["relinked"] += 1
            if not dry:
                os.remove(link_path)
                os.symlink(target, link_path)
        else:
            counts["skip_foreign"] += 1
            print(f"warn: {link_path} points outside ai-kit ({cur}) — leaving it alone",
                  file=sys.stderr)
    elif os.path.exists(link_path):
        counts["skip_real"] += 1
        print(f"warn: {link_path} exists and is not a symlink — leaving it alone",
              file=sys.stderr)
    else:
        counts["linked"] += 1
        if not dry:
            os.makedirs(os.path.dirname(link_path), exist_ok=True)
            os.symlink(target, link_path)


def unlink_one(link_path, dry, counts):
    """Remove one ai-kit symlink (caller has already confirmed ownership). A link
    that vanishes between detection and removal is counted gone, not an error."""
    counts["unlinked"] += 1
    if not dry and os.path.lexists(link_path):
        with contextlib.suppress(FileNotFoundError):
            os.remove(link_path)


def _backup_stamp():
    """UTC stamp for a backup claim dir name (a function so tests can fix it)."""
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _backup_entry(path, root_dir, name):
    """Move `path` (a dir, file or symlink) into an exclusively claimed
    <root_dir>/<name>.bak-<stamp> dir (D-15). The claim is made with os.mkdir
    (exclusive — the idea of config_backup.py's _claim_copy, done with a
    directory because the entry may be any of the three shapes), numbering
    -1, -2, ... on a collision. Returns the moved entry's path inside the
    claim. On a move failure the claim is removed ONLY when it is empty (across
    filesystems shutil.move copies with copytree then deletes the source, so a
    failure can leave a populated claim AND a partial source — deleting the
    claim could destroy the only full copy); a non-empty claim is kept, one
    `warn:` line names source and destination, and the error re-raises."""
    os.makedirs(root_dir, mode=0o700, exist_ok=True)
    stamp = _backup_stamp()
    claim = os.path.join(root_dir, f"{name}.bak-{stamp}")
    n = 0
    while True:
        try:
            os.mkdir(claim, 0o700)
            break
        except FileExistsError:
            n += 1
            claim = os.path.join(root_dir, f"{name}.bak-{stamp}-{n}")
    try:
        dest = os.path.join(claim, name)
        shutil.move(path, dest)
    except OSError as exc:
        if not os.listdir(claim):
            os.rmdir(claim)
            detail = "nothing was moved"
        else:
            detail = (f"the partial copy stays at {claim}; "
                      "check both before retrying")
        print(f"warn: moving {path} to {claim} failed ({exc}); {detail}",
              file=sys.stderr)
        raise
    return dest


def stale_link_candidates(claude_dir, install_dir, present):
    """B - A: ai-kit symlinks under ~/.claude whose repo entry no longer exists
    (deleted upstream). `present` maps cat -> set(names) still in the repo.
    Pure detection — read-only, never mutates. Returns the 'cat/name' list."""
    installed = installed_links(claude_dir, install_dir)
    stale = []
    for cat in CATEGORIES:
        keep = present.get(cat, set())
        for name in sorted(installed[cat]):
            if name in keep:
                continue
            link = os.path.join(claude_dir, cat, name)
            # only stale if its target no longer resolves (entry removed upstream)
            if os.path.exists(link):
                continue
            stale.append(f"{cat}/{name}")
    return stale


def apply_stale_prune(claude_dir, stale, dry, counts):
    """Remove each 'cat/name' stale link (mutating). Counts as pruned, not
    unlinked — pruned/unlinked are distinct tallies."""
    for item in stale:
        cat, name = item.split("/", 1)
        unlink_one(os.path.join(claude_dir, cat, name), dry, counts)
        counts["pruned"] += 1
        counts["unlinked"] -= 1


def _prune_headless(root, stale, dry, counts):
    """Headless prune: one warn line per dead ai-kit link (sorted), then remove them."""
    for item in sorted(stale):
        print(f"warn: removing dead ai-kit link {item} (entry removed upstream)",
              file=sys.stderr)
    apply_stale_prune(root, stale, dry, counts)


def prune_stale(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    claude_dir, install_dir, present, tty, dry, counts,
):
    """B − A: ai-kit symlinks under ~/.claude whose repo entry no longer exists
    (deleted upstream). `present` maps cat -> set(names) still in the repo.
    Interactive: warn by name, offer to prune (confirmed). Headless: auto-remove
    the dead link + print a warning (§4). Returns the list of 'cat/name' pruned
    (or, when the user declines, the list that WAS offered)."""
    stale = stale_link_candidates(claude_dir, install_dir, present)
    if not stale:
        return []
    if is_interactive(tty):
        banner = "\nThese ai-kit links point at entries removed upstream:\n"
        banner += "".join(f"  - {item}\n" for item in stale)
        _tty_write(tty, banner)
        if not ask_yes_no(tty, "prune them?", default=False):
            return stale  # offered, declined
        apply_stale_prune(claude_dir, stale, dry, counts)
    else:
        _prune_headless(claude_dir, stale, dry, counts)
    return stale


def _headless_prune_roots(paths, entries, dry, counts):
    """Headless installs and reconfigures prune dead ai-kit links first: the claude
    root, then the pi root when it exists (its skills/ items only, as the wizard
    filters). Never creates the pi dir."""
    present = {cat: {n for n, _ in entries[cat]} for cat in CATEGORIES}
    prune_stale(paths.claude_dir, paths.install_dir, present, None, dry, counts)
    if os.path.isdir(paths.pi_dir):
        pi_stale = [i for i in stale_link_candidates(paths.pi_dir, paths.install_dir, present)
                    if i.startswith("skills/")]
        _prune_headless(paths.pi_dir, pi_stale, dry, counts)


def predecessor_candidates(claude_dir, install_dir, entries):
    """List (cat, name, old_target, new_target) for links left by a PREVIOUS
    ai-kit install (e.g. a renamed repo uz-kit -> ai-kit). A candidate is a
    symlink at <claude>/<cat>/<name> that is foreign to the CURRENT install_dir
    yet carries the ai-kit <root>/<cat>/<name> shape (target basename == name,
    its parent dir name == cat) AND whose <name> is a current repo entry, so it
    can be re-pointed. The link must ALSO be dangling (its target does not
    resolve): a live target is someone's content and belongs to the replace
    path (headless --replace-existing / the wizard's replace gate), never to
    this gate. Unrelated foreign symlinks (different shape, live, or no current
    entry) are excluded — we never touch a link that isn't recognizably ours
    and gone."""
    out = []
    for cat in CATEGORIES:
        by_name = dict(entries.get(cat, []))
        dest = os.path.join(claude_dir, cat)
        if not os.path.isdir(dest):
            continue
        for name in sorted(os.listdir(dest)):
            link = os.path.join(dest, name)
            if not os.path.islink(link):
                continue
            old = os.readlink(link)
            if _is_inside(os.path.join(os.path.dirname(link), old), install_dir):
                continue                       # already a current ai-kit link
            if os.path.exists(link):
                continue                       # live target: foreign content, replace path's job
            if os.path.basename(old) != name:
                continue                       # not the ai-kit <cat>/<name> shape
            if os.path.basename(os.path.dirname(old)) != cat:
                continue
            if name not in by_name:
                continue                       # nothing current to re-point to
            out.append((cat, name, old, by_name[name]))
    return out


def apply_predecessor_links(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        claude_dir, cands, repoint, dry, counts, backup_dir=None):
    """Apply the repoint/delete decision for each predecessor-link candidate
    (mutating). `cands` is predecessor_candidates()'s output:
    (cat, name, old, new_target). With `backup_dir` given and not dry, each old
    link is first moved into <backup_dir>/<name>.bak-<stamp>/ (SPEC R8: the
    gate removes nothing without a backup); without it the old removal stays
    (only the legacy raw-terminal adopt_predecessor_links relies on that)."""
    for cat, name, _old, new_target in cands:
        link = os.path.join(claude_dir, cat, name)
        if not dry:
            if os.path.lexists(link):
                if backup_dir is not None:
                    dest = _backup_entry(link, backup_dir, name)
                    print(f"moved {link} -> {dest}")
                else:
                    os.remove(link)
            if repoint:
                os.symlink(new_target, link)
        counts["relinked" if repoint else "pruned"] += 1


def adopt_predecessor_links(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    claude_dir, install_dir, entries, tty, dry, counts,
):
    """Resolve links from a previous ai-kit install. Interactive: list them and
    ask whether to re-point to THIS install (default) or drop them. Headless:
    warn only and leave them alone — never silently clobber a foreign link.
    Returns the list of 'cat/name' candidates found."""
    cands = predecessor_candidates(claude_dir, install_dir, entries)
    items = [f"{cat}/{name}" for cat, name, _, _ in cands]
    if not cands:
        return []
    if not is_interactive(tty):
        for it in items:
            print(f"warn: {it} links to a previous ai-kit install — run setup "
                  "interactively to re-point or delete it", file=sys.stderr)
        return items
    n = len(items)
    warn = _WARN if _use_color(tty) else ""
    bold = _BOLD if _use_color(tty) else ""
    rst = _RESET if _use_color(tty) else ""
    banner = "\nThese links point at a PREVIOUS ai-kit install (e.g. a renamed repo):\n"
    banner += "".join(f"  - {it}\n" for it in items)
    banner += (
        f"\n{warn}  ⚠  Answering No DELETES these {n} stale link(s) — "
        f"this cannot be undone.{rst}\n\n"
        f"  {bold}Yes{rst} → re-point all {n} link(s) to THIS install (each link recreated here)\n"
        f"  {bold}No{rst}  → {warn}DELETE{rst} all {n} stale link(s) from ~/.claude\n"
        "         (only these dangling links are removed — your files and this\n"
        "         install are left untouched)\n")
    _tty_write(tty, banner)
    prompt = (f"Re-point them to this install?  "
              f"{warn}(No DELETES the {n} stale link(s)){rst}")
    repoint = ask_yes_no(tty, prompt, default=True)
    apply_predecessor_links(claude_dir, cands, repoint, dry, counts)
    return items


_ACCENT = "\033[36m"   # cyan — enabled rows
_DIM = "\033[2m"       # dimmed — disabled rows
_WARN = "\033[1;33m"   # bold yellow — destructive emphasis
_BOLD = "\033[1m"      # bold
_RESET = "\033[0m"


def _use_color(tty):
    """ANSI emphasis is safe only on a real terminal with NO_COLOR unset.
    A test ``io.StringIO`` reports ``isatty() == False`` → plain text."""
    if os.environ.get("NO_COLOR"):
        return False
    isatty_fn = getattr(tty, "isatty", None)
    return callable(isatty_fn) and bool(isatty_fn())


def _first_run(installed):
    """True when nothing is linked in any category — the only time the wizard
    defaults all-on (§4 consequence 1)."""
    return all(not installed[cat] for cat in CATEGORIES)


def _default_selection(entries, installed):
    """The pre-checked set per category: first-ever install → all entries on;
    otherwise → keep exactly what is already linked (a NEW upstream entry stays
    OFF until the user toggles it, §4 consequence 2)."""
    first = _first_run(installed)
    sel = {}
    for cat in CATEGORIES:
        names = [n for n, _ in entries[cat]]
        if first:
            sel[cat] = set(names)
        else:
            sel[cat] = {n for n in names if n in installed[cat]}
    return sel


class Selection:
    """The shared in-memory pick model behind both the install skill-picker and
    the status-line segment toggle. Holds an ORDERED list of (category, name)
    items each with an enabled flag, plus a cursor. It owns ONLY *what is on* and
    *where the cursor sits* — never layout, dirtiness, or persistence (callers
    compose those around it). Both flows mutate it the same way (toggle / set_all
    / move_cursor) and project it back out (category_sets / enabled_map)."""

    def __init__(self, items):
        # items: iterable of (category, name, enabled)
        self.items = [[cat, name, bool(on)] for cat, name, on in items]
        self.cursor = 0

    def __len__(self):
        return len(self.items)

    def toggle(self, index):
        """Flip the enabled flag of the item at `index`."""
        self.items[index][2] = not self.items[index][2]

    def toggle_cursor(self):
        """Toggle the item currently under the cursor."""
        if self.items:
            self.toggle(self.cursor)

    def set_all(self, value):
        """Set every item's enabled flag to `value`."""
        for it in self.items:
            it[2] = bool(value)

    def set_category(self, cat: str, value: bool) -> None:
        """Set all items in `cat` to `value`."""
        for it in self.items:
            if it[0] == cat:
                it[2] = bool(value)

    def move_cursor(self, delta):
        """Move the cursor by `delta`, clamped to the item range."""
        if self.items:
            self.cursor = max(0, min(len(self.items) - 1, self.cursor + delta))

    def enabled_map(self):
        """{name: enabled} over every item, order-preserving."""
        return {name: on for _cat, name, on in self.items}

    def category_sets(self, categories=None):
        """{category: {names that are enabled}} — only the ON items appear in a
        category's set. A category with any item present always gets a key; when
        `categories` is given, every listed category gets a key too (empty set if
        it has no enabled items), so callers need no post-projection backfill."""
        out = {c: set() for c in categories} if categories else {}
        for cat, name, on in self.items:
            s = out.setdefault(cat, set())
            if on:
                s.add(name)
        return out


def select_skills(entries, installed, tty):
    """The pre-checked selection the wizard seeds from. Interaction now lives in
    the Textual app; this is the pure default projection (no prompting)."""
    return _default_selection(entries, installed)


def resolve_skills_flag(flag, entries):
    """Parse --skills' value against the live skills entries. Returns
    (chosen: set[str] | None, unknown: list[str]). `flag is None` means the
    flag was not passed at all -- (None, []), the caller's signal to skip
    skill linking entirely (bare --headless). 'all' (case-insensitive, like
    resolve_example_selection's, tools/setup.py:812) means every valid skill
    name. Otherwise the value is tokenized exactly as --examples' id list is --
    re.split(r"[,\\s]+", ...), so 'alpha,beta' and 'alpha beta' both work
    (tools/setup.py:820) -- and intersected against valid names; any name not
    present is returned in `unknown` for the caller to warn about (never
    silently dropped, never a hard failure) -- this includes the case where
    EVERY requested name is unknown, which returns an empty `chosen` set
    alongside a non-empty `unknown` list (the caller must not mistake this for
    "nothing requested").

    Unlike --examples there is NO 'none' value: bare --headless already means
    "link nothing", so the literal 'none' is just an ordinary unknown name."""
    if flag is None:
        return None, []
    valid = {name for name, _ in entries.get("skills", [])}
    if flag.strip().lower() == "all":
        return set(valid), []
    requested = {t for t in re.split(r"[,\s]+", flag.strip()) if t}
    chosen = requested & valid
    unknown = sorted(requested - valid)
    return chosen, unknown


def apply_additive_skills(names, entries, claude_dir, dry, counts):
    """Link every name in `names` (skills category only) via link_one -- NEVER
    unlinks anything. Unlike apply_selection, there is no deselect branch: an
    existing ai-kit link for a skill NOT in `names` is left exactly as it is.
    This is the headless-path primitive -- 'nothing touched unless asked.'
    Any OSError link_one raises (e.g. a permission failure) propagates to the
    caller uncaught -- cmd_install_headless is responsible for catching it
    and mapping it to the documented exit-code-1 failure case."""
    by_name = dict(entries.get("skills", []))
    for name in sorted(names):
        target = by_name.get(name)
        if target is None:
            continue
        link_one(os.path.join(claude_dir, "skills", name), target, dry, counts)


def apply_selection(selection, entries, claude_dir, dry, counts):
    """Reconcile to the chosen set: link every selected entry (A∩B keep / A−B
    new-selected), unlink any currently-linked ai-kit entry that is NOT selected.
    Does not prune deleted-upstream links — that is prune_stale's job."""
    installed = installed_links(claude_dir, install_dir=_install_root(entries))
    for cat in CATEGORIES:
        chosen = selection.get(cat, set())
        by_name = dict(entries[cat])
        # link / re-point chosen
        for name in sorted(chosen):
            target = by_name.get(name)
            if target is None:
                continue
            link_one(os.path.join(claude_dir, cat, name), target, dry, counts)
        # unlink deselected (currently linked, in repo, but not chosen)
        for name in sorted(installed[cat]):
            if name in by_name and name not in chosen:
                unlink_one(os.path.join(claude_dir, cat, name), dry, counts)


def _install_root(entries):
    """Derive the install dir from any entry's path (<install>/<cat>/<name>)."""
    for cat in CATEGORIES:
        if entries[cat]:
            return os.path.dirname(os.path.dirname(entries[cat][0][1]))
    return ""


def _pi_entries(entries):
    """The entries the pi root can hold (D-14): skills whose names are in
    PI_SKILLS; the pi root carries no agents or commands."""
    return {"skills": [(n, p) for n, p in entries["skills"] if n in PI_SKILLS],
            "commands": [], "agents": []}


def sync_pi_links(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        paths, entries, dry, counts, names, mirror=False):
    """Mirror the claude skills selection into <pi_dir>/skills for PI_SKILLS
    names (D-14). `names` is the set of skill names the run selected; no pi
    state is stored — the claude links ARE the selection.

    Additive part (both call sites): for each PI_SKILLS name that is in
    `names`, has a repo entry AND a claude ai-kit link, link_one the pi path.
    A missing pi agent dir is a message and never created (SPEC R8 empty edge).

    Mirror part (`mirror=True`, the wizard commit only): a PI_SKILLS repo entry
    the commit's selection leaves unchecked is unlinked from the pi root — the
    selection decides, never the claude path's state (so a claude path
    link_one left alone costs no accepted pi link). Nothing else in the pi
    root is unlinked: a stale link (repo entry gone) belongs to the stale gate
    and a name outside PI_SKILLS is not this phase's.

    shortcut: under --dry-run the mirror reads the current claude links, so
    its counts can lag; fine until dry-run counts need to be exact."""
    by_name = dict(entries["skills"])
    if mirror:
        pi_installed = installed_links(paths.pi_dir, paths.install_dir)["skills"]
        for name in sorted(PI_SKILLS):
            if name in by_name and name in pi_installed and name not in names:
                unlink_one(os.path.join(paths.pi_dir, "skills", name), dry, counts)
    if not any(name in names and name in by_name for name in PI_SKILLS):
        return
    claude_installed = installed_links(paths.claude_dir, paths.install_dir)["skills"]
    for name in sorted(PI_SKILLS):
        if name not in names or name not in by_name:
            continue
        if name not in claude_installed:
            continue
        if not os.path.isdir(paths.pi_dir):
            print(f"note: pi agent dir {paths.pi_dir} not found; "
                  f"{name} not linked for pi", file=sys.stderr)
            continue
        link_one(os.path.join(paths.pi_dir, "skills", name), by_name[name],
                 dry, counts)


JSON_STATE_ABSENT = "absent"
JSON_STATE_OK = "ok"
JSON_STATE_UNREADABLE = "unreadable"

CLAUDE_HOOK_EVENT = "SessionStart"
CLAUDE_HOOK_MATCHER = "startup|compact"
CLAUDE_HOOK_MARKER = os.path.join("tools", "hooks", "claude_session_start.py")
# Cursor's event key differs from Claude Code's only in casing. Sharing one
# string would silently create a dead, never-fired key on one of the two
# hosts (RESEARCH Pitfall 2).
CURSOR_HOOK_EVENT = "sessionStart"
CURSOR_HOOK_MARKER = os.path.join("tools", "hooks", "cursor_session_start.py")


# ── Hook registry (D-11) ──────────────────────────────────────────────────────
HookRow = namedtuple(
    "HookRow",
    "id host event matcher script default experimental verdict timeout",
)

# A verdict is one of HOOK_VERDICTS, or "gap: <reason>" (reason bounded to 24
# characters by the 21.2 close-out so hook_description stays under the cap).
HOOK_VERDICTS = ("positive", "non-positive", "unmeasured")

# Recorded per-host verdicts (21.2-MEASUREMENTS.md); the 21.2 close-out edits
# only this dict
PRECOMPACT_VERDICTS = {
    "claude": "unmeasured",
    "pi": "unmeasured",
    "opencode": "unmeasured",
}

# D-11: flat rows, one per id x host x event; `default` is derived from the
# verdict for precompact rows and explicit for advisory rows.
HOOK_SUMMARIES = {
    "session-briefing": (
        "SessionStart briefing names installed modern tools for the user and model."
    ),
    "tool-advisor": (
        "PreToolUse advisor: suggests rg, bat, fd or sd for grep, cat, find or sed "
        "and reports large reads; advice only."
    ),
    "tool-reminder": "After grep/cat/sed/find, names output size and a better installed tool.",
    "decision-probe": "Reports whether jev-fast-decision backends are usable; off by default.",
    "precompact": "PreCompact pre-summary (local Laya).",
    "session-wake": (
        "StopFailure rate_limit: passes the host's reset text to an armed session wake; "
        "off by default, payload unverified."
    ),
}

HOOK_REGISTRY = (
    HookRow(
        id="session-briefing", host="claude", event=CLAUDE_HOOK_EVENT,
        matcher=CLAUDE_HOOK_MATCHER, script="tools/hooks/claude_session_start.py",
        default=True, experimental=False, verdict=None, timeout=None),
    HookRow(
        id="session-briefing", host="cursor", event=CURSOR_HOOK_EVENT,
        matcher=None, script="tools/hooks/cursor_session_start.py",
        default=True, experimental=False, verdict=None, timeout=None),
    HookRow(
        id="tool-advisor", host="claude", event="PreToolUse", matcher="Bash|Read|Grep|Glob",
        script="tools/hooks/claude_tool_advisor.py", default=True,
        experimental=False, verdict=None, timeout=3),
    HookRow(
        id="tool-advisor", host="pi", event="tool_result", matcher=None,
        script="tools/hooks/pi/ai-kit-tool-advisor.ts", default=True,
        experimental=False, verdict=None, timeout=None),
    HookRow(
        id="tool-reminder", host="claude", event="PostToolUse", matcher="Bash",
        script="tools/hooks/claude_tool_reminder.py", default=True,
        experimental=False, verdict=None, timeout=3),
    HookRow(
        id="tool-reminder", host="pi", event="tool_result", matcher=None,
        script="tools/hooks/pi/ai-kit-tool-reminder.ts", default=True,
        experimental=False, verdict=None, timeout=None),
    HookRow(
        id="decision-probe", host="claude", event="SessionStart", matcher="startup",
        script="tools/hooks/claude_decision_probe.py", default=False,
        experimental=False, verdict=None, timeout=5),
    HookRow(
        id="precompact", host="claude", event="PreCompact", matcher="manual|auto",
        script="tools/hooks/claude_precompact.py",
        default=PRECOMPACT_VERDICTS["claude"] == "positive",
        experimental=False, verdict=PRECOMPACT_VERDICTS["claude"], timeout=10),
    HookRow(
        id="precompact", host="claude", event="SessionStart", matcher="compact",
        script="tools/hooks/claude_precompact.py",
        default=PRECOMPACT_VERDICTS["claude"] == "positive",
        experimental=False, verdict=PRECOMPACT_VERDICTS["claude"], timeout=10),
    HookRow(
        id="precompact", host="pi", event="session_before_compact", matcher=None,
        script="tools/hooks/pi/ai-kit-precompact.ts",
        default=PRECOMPACT_VERDICTS["pi"] == "positive",
        experimental=False, verdict=PRECOMPACT_VERDICTS["pi"], timeout=None),
    HookRow(
        id="precompact", host="opencode", event="experimental.session.compacting",
        matcher=None, script="tools/hooks/opencode/ai-kit-precompact.ts",
        default=PRECOMPACT_VERDICTS["opencode"] == "positive",
        experimental=True, verdict=PRECOMPACT_VERDICTS["opencode"], timeout=None),
    HookRow(
        id="session-wake", host="claude", event="StopFailure", matcher="rate_limit",
        script="tools/hooks/claude_session_wake.py", default=False,
        experimental=True, verdict=None, timeout=10),
)

HOOK_IDS = tuple(dict.fromkeys(row.id for row in HOOK_REGISTRY))


def parse_hook_selector(value):
    """Parse `id` / `id:host` tokens (comma or whitespace separated) into
    (id, host-or-None) pairs in order. A token naming an unknown id, or a host
    no registry row carries, raises ValueError whose message is that token."""
    pairs = []
    for token in [t for t in re.split(r"[,\s]+", value.strip()) if t]:
        if ":" in token:
            hook_id, host = token.split(":", 1)
            if hook_id not in HOOK_IDS or not any(
                    row.id == hook_id and row.host == host for row in HOOK_REGISTRY):
                raise ValueError(token)
            pairs.append((hook_id, host))
        elif token in HOOK_IDS:
            pairs.append((token, None))
        else:
            raise ValueError(token)
    return pairs


def hook_rows(selection):
    """Registry rows matching any (id, host-or-None) pair, in registry order."""
    return tuple(
        row for row in HOOK_REGISTRY
        if any(row.id == hook_id and (host is None or row.host == host)
               for hook_id, host in selection)
    )


def _read_json_checked(path):
    """Three-state JSON reader: absent / ok-dict / unreadable.

    Collapsing all three states into `{}` would treat a corrupted file as
    "fresh file, safe to create" and replace an existing but unparseable
    settings.json with a brand-new file containing only ai-kit's entry — the
    corruption PROJECT.md's core value forbids. Pair it with
    `_atomic_write_json`, never with a plain open-for-write.
    """
    if not os.path.isfile(path):
        return JSON_STATE_ABSENT, {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (ValueError, OSError):
        return JSON_STATE_UNREADABLE, None
    if not isinstance(data, dict):
        return JSON_STATE_UNREADABLE, None
    return JSON_STATE_OK, data


def _atomic_write_json(path, data):
    """Atomically write JSON with indent=2 + trailing newline.

    Temp file plus os.replace, kept here rather than imported (a tools/ module
    importing a skills/ package would be a layering violation). Fresh files get
    mode 0o600 — the mode both hosts' own
    config files were measured to carry — rather than a umask-derived mode
    (os.umask is process-global and not thread-safe; this runs on a Textual
    worker thread). An existing target's real mode is copied, never overwritten.
    Unlink-then-re-raise on OSError is the durability contract the
    failure-injection test executes against.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    target = os.path.realpath(path)
    dirname = os.path.dirname(target) or "."
    existed = os.path.isfile(target)
    mode = stat.S_IMODE(os.stat(target).st_mode) if existed else 0o600
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    # Best-effort directory fsync: the rename above already succeeded, so a
    # failure here (seen on some network filesystems) must never be reported
    # to the caller as a write failure — the correctness-relevant guarantee
    # (the new content is durably in place under `target`) already holds.
    try:
        dir_fd = os.open(dirname, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def _hook_entries_shape_ok(entries, nested):
    """Per-element guard: every array member (and nested hooks members) is a dict.

    Returns (ok, reason) naming the first violation found.
    """
    for entry in entries:
        if not isinstance(entry, dict):
            return False, "non-dict array element"
        if nested and "hooks" in entry:
            inner = entry["hooks"]
            if not isinstance(inner, list):
                return False, "hooks value is not a list of dicts"
            for member in inner:
                if not isinstance(member, dict):
                    return False, "non-dict nested hook member"
    return True, ""


def _warn_hook_config(path, reason):
    """Refuse a config we cannot fully interpret, naming path and reason."""
    print(
        f"warn: {path}: {reason} — ai-kit will not overwrite a config file "
        "it cannot parse",
        file=sys.stderr,
    )


def _hook_container_reason(data, event_key, nested):
    """First container/element shape violation, or '' if the walk is safe."""
    if "hooks" in data and not isinstance(data.get("hooks"), dict):
        return "hooks is not an object"
    hooks = data.get("hooks")
    if not isinstance(hooks, dict) or event_key not in hooks:
        return ""
    entries = hooks[event_key]
    if not isinstance(entries, list):
        return f"hooks.{event_key} is not a list"
    ok, reason = _hook_entries_shape_ok(entries, nested)
    return "" if ok else reason


def _load_hook_config(path, event_key, nested=False):
    """Shared read-and-guard for both hosts' wiring routes.

    Returns (ok, data, created). When ok is True, every element the caller
    will walk is a dict, and on the nested side every member of every entry's
    hooks list is a dict too.
    """
    state, data = _read_json_checked(path)
    if state == JSON_STATE_UNREADABLE:
        _warn_hook_config(path, "cannot parse as a JSON object")
        return False, None, False
    if state == JSON_STATE_ABSENT:
        return True, {}, True
    reason = _hook_container_reason(data, event_key, nested)
    if reason:
        _warn_hook_config(path, reason)
        return False, None, False
    return True, data, False


def _refresh_or_append_claude_hook(entries, command,
                                   matcher=CLAUDE_HOOK_MATCHER,
                                   marker=CLAUDE_HOOK_MARKER, timeout=None):
    """Refresh ai-kit's hook object in place, or append a fresh entry.

    Ownership is per hook OBJECT, not per entry: only the hook dict whose
    `command` contains `marker` is replaced or moved. A user hook nested in
    ai-kit's entry — and every other key of that entry — survives both the
    in-place refresh (when the entry's matcher already equals `matcher`) and
    the move to a fresh entry (when it differs). The hook dict carries
    `timeout` only when it is not None, so entries written before timeouts
    existed stay byte-identical on refresh."""
    hook = {"type": "command", "command": command}
    if timeout is not None:
        hook["timeout"] = timeout
    for entry in entries:
        hooks = entry.get("hooks") or []
        for index, member in enumerate(hooks):
            if marker in member.get("command", ""):
                if entry.get("matcher") == matcher:
                    hooks[index] = hook
                else:
                    del hooks[index]
                    if not hooks:
                        entries.remove(entry)
                    entries.append({"matcher": matcher, "hooks": [hook]})
                return True
    entries.append({"matcher": matcher, "hooks": [hook]})
    return False


def _load_hook_config_multi(path, event_keys):
    """`_load_hook_config` over every event key at once: the grouped writer's
    guard. Validates each key's container shape BEFORE anything changes, so a
    file refused here stays byte-identical. Returns (ok, data); data is a dict
    ({} for an absent file) exactly when ok is True."""
    state, data = _read_json_checked(path)
    if state == JSON_STATE_UNREADABLE:
        _warn_hook_config(path, "cannot parse as a JSON object")
        return False, None
    if state == JSON_STATE_ABSENT:
        return True, {}
    assert data is not None
    for key in event_keys:
        reason = _hook_container_reason(data, key, nested=True)
        if reason:
            _warn_hook_config(path, reason)
            return False, None
    return True, data


def wire_claude_rows(settings, rows, install_dir, dry):
    """Write every Claude row of one hook id in ONE grouped atomic write
    (D-11): a PreCompact entry is never written without its compact
    SessionStart injector. One `_load_hook_config_multi` read-validate, per-row
    refresh-or-append, then one `_atomic_write_json`. Returns False on an absent
    Claude directory, refused file, or failed write."""
    if not os.path.isdir(os.path.dirname(settings) or "."):
        print("skipped Claude Code hook rows — no claude dir")
        return False
    events = sorted({row.event for row in rows})
    ok, data = _load_hook_config_multi(settings, events)
    if not ok:
        return False
    assert data is not None  # ok True <=> data is a dict
    hooks = data.setdefault("hooks", {})
    commands = []
    for row in rows:
        script_path = os.path.join(install_dir, *row.script.split("/"))
        command = "python3 -S " + shlex.quote(script_path)
        commands.append((row, command))
        entries = hooks.setdefault(row.event, [])
        _refresh_or_append_claude_hook(
            entries, command, matcher=row.matcher,
            marker=os.path.join(*row.script.split("/")), timeout=row.timeout)
    if dry:
        for row, command in commands:
            print(f"would wire {row.event} hook -> {command}")
        return True
    try:
        _atomic_write_json(settings, data)
    except OSError as exc:
        print(f"warn: failed to write {settings}: {exc}", file=sys.stderr)
        return False
    for row, command in commands:
        print(f"wired {row.event} hook ({row.id}) -> {command}")
    return True


def _refresh_or_append_cursor_hook(entries, command):
    """Replace an existing ai-kit sessionStart entry in place, or append one."""
    new_entry = {"type": "command", "command": command}
    for index, entry in enumerate(entries):
        if CURSOR_HOOK_MARKER in entry.get("command", ""):
            entries[index] = new_entry
            return True
    entries.append(new_entry)
    return False


def wire_hook_cursor(cursor_hooks, hook_script, dry):
    """Append-if-absent Cursor sessionStart entry for the briefing wrapper.

    Never materializes ~/.cursor/hooks.json when the parent directory does
    not exist. Never overwrites a config it cannot fully interpret. Writes
    through `_atomic_write_json`; an OSError leaves the target byte-identical
    and returns False rather than aborting a wizard commit. Top-level
    `version` is set to 1 only when `_load_hook_config` reported created.
    """
    if not os.path.isdir(os.path.dirname(cursor_hooks) or "."):
        print("skipped Cursor sessionStart hook — no cursor dir")
        return False
    ok, data, created = _load_hook_config(cursor_hooks, CURSOR_HOOK_EVENT)
    if not ok:
        return False
    assert data is not None  # ok True <=> data is a dict, see _load_hook_config
    hooks = data.setdefault("hooks", {})
    entries = hooks.setdefault(CURSOR_HOOK_EVENT, [])
    command = "python3 -S " + shlex.quote(hook_script)
    refreshed = _refresh_or_append_cursor_hook(entries, command)
    if created:
        data["version"] = 1
    if dry:
        print(f"would wire sessionStart hook -> {command}")
        return True
    try:
        _atomic_write_json(cursor_hooks, data)
    except OSError as exc:
        print(f"warn: failed to write {cursor_hooks}: {exc}", file=sys.stderr)
        return False
    action = "refreshed" if refreshed else "wired"
    print(f"{action} sessionStart hook -> {command}")
    return True


def _statusline_command(value):
    """Classify a settings.json `statusLine` value into its command string.

    Two shapes are supported (same as detect_statusline, tools/setup.py:1614):
    a bare string, or an object with a string "command". Returns:
      ""    → nothing configured (absent/None, or an object with no "command")
      str   → the configured command
      None  → an UNSUPPORTED shape (list/number/bool, or a "command" that is
              not a string). The caller must refuse and write nothing: we
              cannot describe what we would be destroying, so we don't.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "command" not in value:
            return ""
        cmd = value["command"]
        return cmd if isinstance(cmd, str) else None
    return None


def _command_is_ours(command, entry):
    """Whether a status-line command really RUNS `entry` (D-23, shared parser).

    Asks the one command-ownership parser (`command_ownership.rewrite_owned_command`)
    to rewrite the command onto itself: a non-None result means argv[0] is a
    supported Python interpreter and the script argument is EXACTLY `entry`.
    There is no substring match anywhere, so the counterexamples stay foreign on
    both hosts — a script with a `.backup`/`.bak` suffix, a foreign script that
    merely receives our path as an argument, and any shell form
    (`bash -c '...'`, `cd x && python3 ...`). Unrecognized shell forms stay
    foreign rather than being guessed at."""
    return _command_ownership().rewrite_owned_command(command, entry, entry) is not None


def _statusline_display(value):
    """Short, honest text for a statusLine value ai-kit cannot classify.

    Used only in prompts/warnings so a human can recognize the entry being
    protected: the bare string, an object's string command, else the JSON text
    of whatever shape it is (never a Python repr of a partially parsed blob)."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("command"), str):
        return value["command"]
    return json.dumps(value)


def _statusline_state(settings):
    """Read settings.json for wire_statusline: returns (data, cur_cmd), or
    (None, None) after printing one warning when the file exists but is not a
    JSON object, or when its statusLine has an unsupported shape. Split out of
    wire_statusline so that function stays at 6 returns (pylint max-returns)."""
    state, data = _read_json_checked(settings)
    if state == JSON_STATE_UNREADABLE:
        print(f"warn: {settings}: cannot parse as a JSON object — ai-kit will not "
              "overwrite a config file it cannot parse", file=sys.stderr)
        return None, None
    if state == JSON_STATE_ABSENT or not isinstance(data, dict):
        data = {}
    cur_cmd = _statusline_command(data.get("statusLine"))
    if cur_cmd is None:
        print(f"warn: {settings}: statusLine must be a string or an object with "
              "a string 'command' — ai-kit will not overwrite a statusLine it "
              "cannot read", file=sys.stderr)
        return None, None
    return data, cur_cmd


def wire_statusline(settings, status_line, tty, dry, assume_overwrite=False):
    """Point settings.json's statusLine.command at the bundled claude-status-line.py
    (with `python3 -S`), preserving all other keys. FR-5.5 double-confirm:
      - absent / already ai-kit  → set/refresh silently
      - a DIFFERENT command      → show it and require an explicit 'y'; on a
                                   headless run (no tty) refuse and leave it.
    ``assume_overwrite`` short-circuits the foreign-command guard: the caller
    (the in-UI adoption gate) already asked the user "replace it with ai-kit?"
    and got a yes, so re-prompting on the terminal would be a redundant second
    question.

    Reads via `_read_json_checked` (absent/ok/unreadable) and writes via
    `_atomic_write_json` — the same malformed-aware, atomic primitives
    the registry hook writers already use. A settings.json that
    exists but cannot be parsed as a JSON object is refused outright (never
    silently treated as "empty, safe to overwrite"), and a write failure
    leaves the file byte-identical rather than raising past the caller.

    statusLine may be a bare string or an object with a string "command" (both
    shapes are supported by Claude Code; detect_statusline classifies them
    through the same _statusline_command helper) — a foreign STRING command is
    guarded exactly like a foreign dict command, not silently treated as
    unset. Any OTHER shape (list/number/bool, or a non-string "command") is
    refused outright via _statusline_command — which is where this function and
    detect_statusline part ways: the reader reports such a shape as "unset",
    this writer refuses to touch it. The refusal happens BEFORE the assume_overwrite
    short-circuit and before the dry-run branch: assume_overwrite means a
    human already approved replacing a command we showed them, and we cannot
    show them a shape we don't understand.

    Ownership is the shared exact-argv test (_command_is_ours), not a substring:
    a `.backup`/`.bak` copy of our script, a foreign script that receives our
    path as an argument, and any shell form are foreign here exactly as they are
    in migration, detection and uninstall (D-23).

    Returns True when statusLine now points at ai-kit, False when left
    untouched (foreign command declined/refused headless, unsupported
    statusLine shape, unreadable settings.json, or a write failure)."""
    # Quoted as the cursor writer quotes its entry: a path with a space (a TMPDIR or install dir
    # with one) must reach the shell as one argument. shlex.quote is a no-op for a plain path.
    desired = "python3 -S " + shlex.quote(status_line)
    data, cur_cmd = _statusline_state(settings)
    if data is None:
        return False
    # The pre-rename entry of this same install is ours too: a dry run reads it before the
    # migration has rewritten it, and a failed migration is still ours to replace.
    legacy = os.path.join(os.path.dirname(status_line), _LEGACY_ENTRY)
    owned = cur_cmd and (_command_is_ours(cur_cmd, status_line)
                         or _command_is_ours(cur_cmd, legacy))
    if cur_cmd and not owned and not assume_overwrite:
        # a foreign status line (dict or bare-string form) — guard it
        if not is_interactive(tty):
            print(f"warn: settings.json has a foreign statusLine ({cur_cmd}) — not wiring "
                  "the ai-kit status line (headless)", file=sys.stderr)
            return False
        _tty_write(tty, f"\nsettings.json already sets a status line:\n  {cur_cmd}\n")
        if not ask_yes_no(tty, "overwrite it with the ai-kit status line?", default=False):
            print("statusLine left untouched (declined).", file=sys.stderr)
            return False
    if dry:
        print(f"would set statusLine -> {desired}")
        return True
    data["statusLine"] = {"type": "command", "command": desired}
    try:
        _atomic_write_json(settings, data)
    except OSError as exc:
        print(f"warn: failed to write {settings}: {exc}", file=sys.stderr)
        return False
    return True


def detect_statusline(paths):
    """Read-only: classify settings.json's statusLine for the adoption gate.

    Returns {"state": "unset"|"ours"|"foreign", "current_command": str|None}.
      - "ours"    iff the command's argv runs the resolved paths.status_line
                  EXACTLY (the shared _command_is_ours parser — no substring,
                  XDG-aware path, never a hard-coded string).
      - "foreign" iff a statusLine is configured but does not run our script.
      - "unset"   iff absent, empty, file is missing/malformed, or the statusLine
                  holds an UNSUPPORTED shape (a list/number/bool, or an object
                  whose "command" is not a string). The unsupported case used to
                  raise TypeError out of the `in` test below for a truthy
                  non-container "command" (e.g. {"command": 1}) — an uncaught
                  crash, since the wizard calls this during context population.
                  Classification is shared with wire_statusline via
                  _statusline_command; the two differ only in what they DO about
                  it (this reports "unset", the writer refuses to overwrite).

    statusLine may be a bare string or an object with a string "command" (both
    shapes are supported by Claude Code).  Writes nothing."""
    state, data = _read_json_checked(paths.settings)
    if state != JSON_STATE_OK or data is None:
        data = {}
    # _statusline_command returns "" for unset and None for an unsupported
    # shape; both are falsy, so both fall through to "unset" below.
    cur_cmd = _statusline_command(data.get("statusLine"))
    if not cur_cmd:
        return {"state": "unset", "current_command": None}
    if _command_is_ours(cur_cmd, paths.status_line):
        return {"state": "ours", "current_command": cur_cmd}
    return {"state": "foreign", "current_command": cur_cmd}


# ── Cursor status line: schema, detection, wiring (D-21/D-23) ───────────────

def _int_field_ok(value, minimum):
    """Whether an optional integer knob is absent, or an int at/above `minimum`.

    JSON `true`/`false` parse to Python bools, which ARE ints by subclassing, so
    the bool exclusion is load-bearing: `{"padding": true}` must not pass as `{"padding": 1}`."""
    if value is None:
        return True
    return (not isinstance(value, bool) and isinstance(value, int)
            and value >= minimum)


def _cursor_statusline_command(value):
    """The command string of a schema-valid Cursor statusLine, else None.

    Cursor's own schema (its bundle's zod object) is `type == "command"` plus a
    non-empty string `command`, with only `padding` (>= 0), `updateIntervalMs`
    and `timeoutMs` (positive ints) as optional siblings. A bare STRING command —
    the second shape Claude's settings.json allows — is a schema error HERE, and
    so is any unknown key or malformed sibling: this returns None and the caller
    treats it as foreign/refuses it rather than guessing (D-23).
    """
    if not isinstance(value, dict):
        return None
    if set(value) - _CURSOR_STATUSLINE_KEYS or value.get("type") != "command":
        return None
    command = value.get("command")
    if not isinstance(command, str) or not command:
        return None
    if not (_int_field_ok(value.get("padding"), 0)
            and _int_field_ok(value.get("updateIntervalMs"), 1)
            and _int_field_ok(value.get("timeoutMs"), 1)):
        return None
    return command


def _cursor_write_state(data, entry):
    """Classify a parsed cli-config dict as ('unset'|'ours'|'foreign', text).

    Shared by detect_statusline_cursor and wire_statusline_cursor so the reader
    and the writer can never disagree about what is ai-kit's — including in the
    re-read immediately before the atomic replace.
    """
    value = data.get("statusLine")
    if value is None:
        return "unset", None
    command = _cursor_statusline_command(value)
    if command is None:
        return "foreign", _statusline_display(value)
    if _command_is_ours(command, entry):
        return "ours", command
    return "foreign", command


def _cursor_config_read(cli_config):
    """(state, parsed-dict) for cli-config.json — state in json | jsonc | absent | bad.

    `json` is a strict JSON object (what the Cursor CLI itself writes); `jsonc` is
    an object that only parses once comments are stripped by the existing
    stdlib-only scanner; `bad` is unreadable, not-an-object, or not JSON at all.
    Reading tolerantly is what lets DETECTION report the real state of a commented
    file instead of claiming there is nothing to protect; the writer acts on that
    distinction separately.
    """
    if not os.path.isfile(cli_config):
        return "absent", {}
    try:
        with open(cli_config, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return "bad", None
    try:
        data = json.loads(text)
        return ("json", data) if isinstance(data, dict) else ("bad", None)
    except ValueError:
        pass
    try:
        data = json.loads(_jsonc_reader().strip_jsonc_comments(text))
    except ValueError:
        return "bad", None
    return ("jsonc", data) if isinstance(data, dict) else ("bad", None)


def detect_statusline_cursor(paths):
    """Read-only: classify cli-config.json's statusLine for the Cursor host.

    Returns {"state": "unset"|"ours"|"foreign", "current_command": str|None} on
    the same three-state contract as detect_statusline, decided by the same
    shared ownership parser. An absent file or one that is not JSON at all is
    "unset" (nothing to protect, and the writer still refuses to materialize a
    missing dir); a present entry that is not ai-kit's — including every shape the
    CLI's schema rejects — is "foreign". A commented (JSONC) file IS classified,
    not reported as unset, because reading is comment-tolerant. Writes nothing.
    """
    state, data = _cursor_config_read(paths.cursor_cli_config)
    if state in ("absent", "bad"):
        return {"state": "unset", "current_command": None}
    kind, text = _cursor_write_state(data, paths.cursor_status_line)
    return {"state": kind, "current_command": text}


def _cursor_config_for_write(cli_config):
    """The parsed cli-config.json to edit, or None after one warning.

    Absent -> {} (the caller has already checked the parent dir exists, so this
    is SPEC R11's adjacency edge: a dir with no config file yet gets a new one).
    Strict JSON object -> the parsed dict. `bad` -> None, never rewritten: ai-kit
    will not replace a file the Cursor CLI itself is unable to read. `jsonc` ->
    also None: ai-kit's writer emits plain JSON, so rewriting a file that only
    parses once comments are stripped would silently delete those comments — the
    file stays byte-for-byte untouched and the warning says exactly why. Cursor
    writes its own config as plain JSON, so this is the rare path, not the normal
    one (documented as a known gap in README rather than degraded silently).
    """
    state, data = _cursor_config_read(cli_config)
    if state == "bad":
        print(f"warn: {cli_config}: cannot parse as a JSON object — ai-kit will not "
              "overwrite a config file it cannot parse", file=sys.stderr)
        return None
    if state == "jsonc":
        print(f"warn: {cli_config}: holds JSONC comments, which ai-kit's plain-JSON "
              "writer would drop — leaving the file untouched", file=sys.stderr)
        return None
    if state == "absent":
        return {}
    return data


def _cursor_apply_statusline(data, ours, desired):
    """Set or refresh ai-kit's statusLine on `data` in place.

    An "ours" refresh changes ONLY `command`: the sibling `padding`/
    `updateIntervalMs`/`timeoutMs` the user configured stay exactly as they are.
    A NEW entry holds only `type` and `command` — ai-kit never writes a
    non-default knob it has not been asked for (D-23).
    """
    current = data.get("statusLine")
    if ours and isinstance(current, dict):
        current["command"] = desired
        return
    data["statusLine"] = {"type": "command", "command": desired}


def _cursor_confirm_overwrite(cli_config, command, tty, assume_overwrite):
    """Whether ai-kit may replace a foreign Cursor statusLine (never headless).

    Same FR-5.5 double-confirm as the Claude side: show the exact entry, require
    an explicit 'y', refuse silently on a headless run.
    """
    if assume_overwrite:
        return True
    if not is_interactive(tty):
        print(f"warn: {cli_config} has a foreign statusLine ({command}) — not wiring "
              "the ai-kit status line (headless)", file=sys.stderr)
        return False
    _tty_write(tty, f"\n{cli_config} already sets a status line:\n  {command}\n")
    if not ask_yes_no(tty, "overwrite it with the ai-kit status line?", default=False):
        print("statusLine left untouched (declined).", file=sys.stderr)
        return False
    return True


def _cursor_commit_statusline(cli_config, entry, desired, seen):
    """Re-read, re-classify, apply onto the FRESH content and replace atomically.

    The Cursor CLI rewrites its own cli-config.json during use, so the writer
    does not trust the read it classified a moment ago (D-23 write ordering): it
    reads and classifies again immediately before `_atomic_write_json` and
    applies its change to that content. `seen` is the entry text the caller
    classified (and, when foreign, showed the human): the write goes ahead only
    while the file still holds exactly that entry. Anything else — our command
    replaced by someone else's, an unset key that became foreign, a file that no
    longer parses — aborts the write instead of overwriting what appeared in
    between. Replacing the SAME foreign entry a human just approved is not a
    change, so that one proceeds.
    """
    fresh = _cursor_config_for_write(cli_config)
    if fresh is None:
        return False
    kind, command = _cursor_write_state(fresh, entry)
    if command != seen:
        _warn_hook_config(cli_config, f"statusLine is now {command!r} but {seen!r} "
                                      "was read — write aborted")
        return False
    _cursor_apply_statusline(fresh, kind == "ours", desired)
    try:
        _atomic_write_json(cli_config, fresh)
    except OSError as exc:
        print(f"warn: failed to write {cli_config}: {exc}", file=sys.stderr)
        return False
    return True


def wire_statusline_cursor(cli_config, entry, tty, dry, assume_overwrite=False):
    """Point cli-config.json's statusLine at the bundled cursor-status-line.py.

    The command is `python3 -S <entry>`, the entry path quoted when it holds
    whitespace: the CLI argv-splits the string with no shell, so shell forms
    and unquoted spaces are both wrong here. Claude's writer keeps its own
    (unquoted) form untouched — only this host is quoted.

    Returns True when statusLine now points at ai-kit, False when left
    untouched: the parent directory does not exist (never materialized, mirroring
    wire_hook_cursor), the file cannot be parsed, the entry is foreign and this
    is headless or the human declined, the entry became foreign before the
    replace, or the write failed.
    """
    if not os.path.isdir(os.path.dirname(cli_config) or "."):
        print("skipped ai-kit status line — no cursor dir")
        return False
    data = _cursor_config_for_write(cli_config)
    if data is None:
        return False
    kind, command = _cursor_write_state(data, entry)
    if kind == "foreign" and not _cursor_confirm_overwrite(
            cli_config, command, tty, assume_overwrite):
        return False
    desired = "python3 -S " + shlex.quote(entry)
    if dry:
        print(f"would set Cursor statusLine -> {desired}")
        return True
    return _cursor_commit_statusline(cli_config, entry, desired, command)


def statusline_host_present(paths, host):
    """Whether a status-line host's config directory already exists (never create it)."""
    return os.path.isdir({"claude": paths.claude_dir,
                          "cursor": paths.cursor_config_dir}[host])


def statusline_hosts_detected(paths):
    """The status-line hosts present on this machine, Claude first (SPEC R11)."""
    return [host for host in STATUSLINE_HOSTS if statusline_host_present(paths, host)]


class UndetectedStatuslineHost(ValueError):
    """A named status-line host is a valid name but is not installed here.

    A ValueError subclass so argparse-style callers can treat it as a usage
    error, while main() maps it to exit 1 ("not installed") instead of the
    exit 2 it gives an unknown name.
    """


def parse_statusline_hosts(value, detected):
    """Resolve a `--with-statusline=claude,cursor` value against `detected`.

    Returns the selection in detection order (so Claude is always wired before
    Cursor, whichever way the flag was typed) and de-duplicated. Raises
    ValueError naming the unknown host(s) — a usage error, exit 2 — or
    UndetectedStatuslineHost naming valid-but-undetected ones, exit 1. Pure: no
    filesystem access, so every row of the selection table is testable without a
    scratch tree.
    """
    names = [token.lower() for token in re.split(r"[,\s]+", value.strip()) if token]
    unknown = sorted({name for name in names if name not in STATUSLINE_HOSTS})
    if unknown:
        raise ValueError(f"unknown status-line host(s) {', '.join(unknown)} "
                         f"(known: {', '.join(STATUSLINE_HOSTS)})")
    missing = sorted({name for name in names if name not in detected})
    if missing:
        raise UndetectedStatuslineHost(
            f"status-line host(s) {', '.join(missing)} not detected — no such "
            "config directory on this machine")
    return [host for host in detected if host in set(names)]


def create_if_absent(dest, data):
    """Publish bytes without replacing a destination created by a concurrent writer."""
    directory = os.path.dirname(dest) or "."
    os.makedirs(directory, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".ai-kit-create-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_path, dest)
        except FileExistsError:
            return False
        except OSError:
            try:
                fallback_fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                return False
            try:
                with os.fdopen(fallback_fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError:
                with contextlib.suppress(OSError):
                    os.unlink(dest)
                raise
        return True
    finally:
        with contextlib.suppress(OSError):
            os.unlink(temp_path)


def _migrate_statusline_command(paths, dry):
    """Rewrite the old owned command through the checked atomic JSON path."""
    state, data = _read_json_checked(paths.settings)
    if state == JSON_STATE_UNREADABLE:
        print(f"warn: {paths.settings}: cannot parse as a JSON object; migration skipped",
              file=sys.stderr)
        return False
    if state != JSON_STATE_OK or data is None:
        return False
    status = data.get("statusLine")
    old_script = os.path.join(paths.install_dir, "tools", _LEGACY_ENTRY)
    replacement = _command_ownership().rewrite_owned_command(
        _statusline_command(status), old_script, paths.status_line)
    if replacement is None:
        return False
    if isinstance(status, dict):
        status["command"] = replacement
    else:
        data["statusLine"] = replacement
    if dry:
        print(f"would migrate statusLine command in {paths.settings}")
        return True
    try:
        _atomic_write_json(paths.settings, data)
    except OSError as exc:
        print(f"warn: failed to migrate {paths.settings}: {exc}", file=sys.stderr)
        return False
    return True


def _migrate_statusline_toml(paths, dry):
    """Publish the renamed TOML only when the destination is absent."""
    old_toml = os.path.join(paths.config_dir, _LEGACY_TOML)
    if os.path.exists(old_toml) and os.path.exists(paths.config_toml):
        print(f"warn: both {old_toml} and {paths.config_toml} exist; merge by hand",
              file=sys.stderr)
        return False
    if not os.path.isfile(old_toml):
        return False
    if dry:
        print(f"would migrate {old_toml} -> {paths.config_toml}")
        return True
    try:
        with open(old_toml, "rb") as handle:
            published = create_if_absent(paths.config_toml, handle.read())
        if not published:
            print(f"warn: could not publish {paths.config_toml}; kept {old_toml}",
                  file=sys.stderr)
            return False
        os.unlink(old_toml)
    except OSError as exc:
        print(f"warn: could not migrate {old_toml} -> {paths.config_toml}: {exc}",
              file=sys.stderr)
        return False
    return True


def migrate_statusline(paths, dry):
    """Migrate only owned legacy wiring and publish its config without replacement."""
    command_changed = _migrate_statusline_command(paths, dry)
    toml_changed = _migrate_statusline_toml(paths, dry)
    return command_changed or toml_changed


def copy_recipe_if_absent(sample, config_toml, dry):
    """Copy the recipe atomically only if absent, never replacing a user's config."""
    if not os.path.isfile(sample) or os.path.exists(config_toml):
        return
    if dry:
        print(f"would copy {sample} -> {config_toml}")
        return
    try:
        with open(sample, "rb") as handle:
            create_if_absent(config_toml, handle.read())
    except OSError as exc:
        print(f"warn: failed to copy {sample} -> {config_toml}: {exc}", file=sys.stderr)


def _claude_owned_entries(install_dir):
    """The Claude status-line entry paths ai-kit owns in an install: the current
    entry and the pre-rename legacy one, so a machine that was never
    re-installed still gets unwired."""
    tools = os.path.join(install_dir, "tools")
    return (os.path.join(tools, _CLAUDE_ENTRY), os.path.join(tools, _LEGACY_ENTRY))


def _claude_statusline_is_ours(value, install_dir):
    """Whether a settings.json statusLine runs one of ai-kit's own entries.

    Reads both shapes Claude allows (a bare string, an object with "command")
    through _statusline_command, then decides with the shared exact-argv parser
    — never a substring of the install dir, so a `.backup`/`.bak` copy of our
    script and a foreign script that merely receives our path as an argument
    stay foreign here too (D-23).
    """
    command = _statusline_command(value)
    if not command:
        return False
    return any(_command_is_ours(command, entry)
               for entry in _claude_owned_entries(install_dir))


def unwire_statusline(settings, install_dir, dry):
    """Uninstall: remove the statusLine ONLY if it runs ai-kit's own entry (never
    clobber a foreign one). Preserves all other settings keys.

    Reads through `_read_json_checked` and writes through `_atomic_write_json`
    (D-22): an absent, empty or unparseable settings.json is never written, and
    the rewrite is a same-directory os.replace — the old bytes survive intact
    until the new content is complete. Returns False when an unreadable file was
    skipped or the write failed (the statusLine may still be wired), else True."""
    state, data = _read_json_checked(settings)
    if state == JSON_STATE_UNREADABLE:
        _warn_hook_config(settings, "cannot parse as a JSON object; statusLine left as is")
        return False
    if state != JSON_STATE_OK or data is None:
        return True
    if not _claude_statusline_is_ours(data.get("statusLine"), install_dir):
        return True
    data.pop("statusLine", None)
    return _commit_unwire(settings, data, dry, "would clear ai-kit statusLine")


def unwire_statusline_cursor(cli_config, entry, dry):
    """Uninstall the Cursor host: remove ai-kit's statusLine and nothing else.

    The same three-state classification and the same atomic primitives as the
    Claude side: an absent file writes nothing, an unparseable or JSONC-commented
    file is skipped with a warning naming the reason (uninstall exits 1 for it),
    and a foreign or schema-invalid entry is left byte-identical. When the entry
    IS ours, `statusLine` is dropped whole — the optional `padding`/
    `updateIntervalMs`/`timeoutMs` siblings belong to it — while every other key
    of cli-config.json keeps its parsed value and order. Never materializes a
    missing config dir; TOML configs are untouched.
    """
    state, data = _cursor_config_read(cli_config)
    if state == "bad":
        _warn_hook_config(cli_config, "cannot parse as a JSON object; statusLine left as is")
        return False
    if state == "jsonc":
        print(f"warn: {cli_config}: holds JSONC comments that uninstall's plain-JSON "
              "writer would drop — leaving the file untouched", file=sys.stderr)
        return False
    if state != "json" or not isinstance(data, dict):
        return True                                # absent: nothing of ours to remove
    if _cursor_write_state(data, entry)[0] != "ours":
        return True
    data.pop("statusLine", None)
    return _commit_unwire(cli_config, data, dry, "would clear ai-kit Cursor statusLine")


def _entry_is_ours_nested(entry, marker):
    """True when any nested command string contains `marker`."""
    return any(marker in hook.get("command", "") for hook in entry.get("hooks") or [])


def _commit_unwire(path, data, dry, would_msg):
    """Honour dry, then atomically rewrite `path`. Never raises; False on a failed write."""
    if dry:
        print(would_msg)
        return True
    try:
        _atomic_write_json(path, data)
    except OSError as exc:
        print(f"warn: failed to write {path}: {exc}", file=sys.stderr)
        return False
    return True


def _drop_owned_hooks(entries, markers):
    """Remove only nested hook objects whose command contains a marker.
    Preserve user hook objects and every entry key; drop an entry only when its
    hooks list becomes empty. Entries without a hooks list remain unchanged."""
    changed = False
    kept_entries = []
    for entry in entries:
        if "hooks" not in entry:
            kept_entries.append(entry)
            continue
        hooks = entry["hooks"]
        kept_hooks = [hook for hook in hooks if not any(
            marker in hook.get("command", "") for marker in markers)]
        if kept_hooks != hooks:
            changed = True
            if kept_hooks:
                entry["hooks"] = kept_hooks
                kept_entries.append(entry)
        else:
            kept_entries.append(entry)
    return kept_entries, changed


def unwire_claude_rows(settings, rows, dry):
    """Unwire Claude registry rows in one guarded read/write, preserving
    foreign entries and user hooks nested in ai-kit's entries."""
    if not os.path.isfile(settings):
        return True
    events = sorted({row.event for row in rows})
    ok, data = _load_hook_config_multi(settings, events)
    if not ok:
        return False
    assert data is not None
    hooks = data.get("hooks") or {}
    changed = False
    for event in events:
        if event not in hooks:
            continue
        markers = [os.path.join(*row.script.split("/"))
                   for row in rows if row.event == event]
        hooks[event], event_changed = _drop_owned_hooks(hooks[event], markers)
        changed = changed or event_changed
    if not changed:
        return True
    return _commit_unwire(settings, data, dry, "would remove ai-kit hook rows")


def unwire_hook_rows(paths, rows, dry, counts):
    """Unwire selected registry rows and only links owned by this install."""
    ok = True
    claude_rows = [row for row in rows if row.host == "claude"]
    if claude_rows and not unwire_claude_rows(paths.settings, claude_rows, dry):
        ok = False
    cursor_rows = [row for row in rows if row.host == "cursor"]
    if cursor_rows and not unwire_hook_cursor(paths.cursor_hooks, dry):
        ok = False
    for row in rows:
        if row.host in ("claude", "cursor"):
            continue
        link_path = hook_link_path(paths, row)
        if link_path is not None and os.path.islink(link_path) and _is_inside(
                os.path.join(os.path.dirname(link_path), os.readlink(link_path)),
                paths.install_dir):
            try:
                unlink_one(link_path, dry, counts)
            except OSError as exc:
                print(f"warn: failed to unlink {link_path}: {exc}", file=sys.stderr)
                ok = False
    return ok


def hook_installed_hosts(paths, hook_id):
    """Hosts with an installed ai-kit hook row for `hook_id`."""
    installed = set()
    rows = [row for row in HOOK_REGISTRY if row.id == hook_id]
    claude_rows = [row for row in rows if row.host == "claude"]
    if claude_rows and os.path.isfile(paths.settings):
        ok, data = _load_hook_config_multi(paths.settings,
                                           sorted({row.event for row in claude_rows}))
        if ok and data is not None:
            hooks = data.get("hooks") or {}
            for row in claude_rows:
                if any(_entry_is_ours_nested(entry,
                          os.path.join(*row.script.split("/")))
                       for entry in hooks.get(row.event, [])):
                    installed.add("claude")
    for row in rows:
        if row.host == "cursor":
            if os.path.isfile(paths.cursor_hooks):
                state, data = _read_json_checked(paths.cursor_hooks)
                hooks = (data.get("hooks")
                         if state == JSON_STATE_OK and isinstance(data, dict) else None)
                entries = hooks.get(row.event, []) if isinstance(hooks, dict) else []
                marker = os.path.join(*row.script.split("/"))
                if isinstance(entries, list) and any(
                        isinstance(entry, dict) and marker in entry.get("command", "")
                        for entry in entries):
                    installed.add("cursor")
            continue
        if row.host == "claude":
            continue
        link_path = hook_link_path(paths, row)
        if link_path is not None and os.path.islink(link_path) and _is_inside(
                os.path.join(os.path.dirname(link_path), os.readlink(link_path)),
                paths.install_dir):
            installed.add(row.host)
    return installed


def hook_description(hook_id):
    """Compact, registry-driven one-line description capped at 200 chars."""
    rows = [row for row in HOOK_REGISTRY if row.id == hook_id]
    detail = "; ".join(
        (f"{host} ({'on' if row.default else 'off'})" if row.verdict is None
         else f"{host}: {row.verdict} ({'on' if row.default else 'off'})"
              + (", experimental" if row.experimental else ""))
        for host in dict.fromkeys(row.host for row in rows)
        for row in [next(item for item in rows if item.host == host)]
    )
    return _cap_desc(f"{HOOK_SUMMARIES[hook_id]} {detail}")


def unwire_hook_cursor(cursor_hooks, dry):
    """Remove ai-kit's own sessionStart entry; leave every foreign entry.
    False when the file was refused or the write failed."""
    parent = os.path.dirname(cursor_hooks) or "."
    if not os.path.isdir(parent) or not os.path.isfile(cursor_hooks):
        return True
    ok, data, _ = _load_hook_config(cursor_hooks, CURSOR_HOOK_EVENT)
    if not ok:
        return False
    assert data is not None  # ok True <=> data is a dict, see _load_hook_config
    hooks = data.get("hooks") or {}
    if CURSOR_HOOK_EVENT not in hooks:
        return True
    entries = hooks[CURSOR_HOOK_EVENT]
    kept = [
        e for e in entries
        if CURSOR_HOOK_MARKER not in e.get("command", "")
    ]
    if kept == entries:
        return True
    hooks[CURSOR_HOOK_EVENT] = kept
    return _commit_unwire(
        cursor_hooks, data, dry, "would remove ai-kit sessionStart hook")


def _segment_changes_vs_recipe(path, segments, host="claude"):
    """The {key: bool} subset of `segments` that DIFFERS from what `path` currently
    resolves to for `host` — the minimal set of segment keys to patch (key
    granularity).

    Only BUILT-IN segment keys (those present in that host's resolved config) are
    considered: external/drop-in segments (e.g. ``system_memory``) are persisted
    as their own files, never as ``[segments]`` entries, and the doctor rejects an
    unknown key in that table. ``state["segments"]`` carries external on/off state
    for the examples installer, so it is filtered HERE rather than upstream."""
    current = current_segments(path, host)
    return {k: v for k, v in segments.items()
            if k in current and current.get(k) != v}


def save_statusline_config(path, seg_changes, layout, statusline_doctor,  # pylint: disable=too-many-arguments,too-many-positional-arguments
                           host="claude", *, host_keys=None):
    """Apply the managed edits to the file at `path` via surgical text patches,
    then validate-offline + atomically publish. `seg_changes` is the minimal
    changed {key: bool}; `layout` is None (unchanged) or the full list of line
    dicts; `host_keys` is None or {table: {key: value}} (the host scalars, one
    patch per table, D-03). Returns True on success."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if seg_changes:
        text = patch_segments(text, seg_changes)
    if layout is not None:
        text = patch_layout(text, layout)
    for table, values in (host_keys or {}).items():
        text = patch_host_keys(text, table, values)
    return write_toml_preserving(path, text, statusline_doctor, host=host)


def _find_line(layout, seg):
    for li, row in enumerate(layout):
        if seg in row["segments"]:
            return li, row["segments"].index(seg)
    return None, None


def _apply_wizard_command(  # pylint: disable=too-many-return-statements
    state, cmd,
):
    """Pure state transition for one wizard command. Returns (new_state, error):
    on success error is None; on a bad command new_state is `state` unchanged and
    error is a human message. Recognized: a segment number, `move <seg> up|down`,
    `move <seg> line <n>`."""
    cmd = cmd.strip()
    st = copy.deepcopy(state)
    if cmd in ("a", "n"):                       # all-on / all-off
        st["segments"] = {k: (cmd == "a") for k in st["segments"]}
        st["dirty"] = True
        return st, None
    order = _wizard_order(st)                    # display order == toggle order
    if cmd.isdigit():
        n = int(cmd)
        if not 1 <= n <= len(order):
            return state, f"no segment #{n}"
        key = order[n - 1]                       # numbering is the menu's display order
        st["segments"][key] = not st["segments"][key]
        st["dirty"] = True
        return st, None
    parts = cmd.split()
    if len(parts) >= 3 and parts[0] == "move":
        seg = parts[1]
        li, pos = _find_line(st["layout"], seg)
        if li is None or pos is None:        # _find_line returns both-or-neither
            return state, f"segment '{seg}' is not in the layout"
        if parts[2] == "up" and pos > 0:
            row = st["layout"][li]["segments"]
            row[pos - 1], row[pos] = row[pos], row[pos - 1]
            st["dirty"] = True
            return st, None
        if parts[2] == "down" and pos < len(st["layout"][li]["segments"]) - 1:
            row = st["layout"][li]["segments"]
            row[pos + 1], row[pos] = row[pos], row[pos + 1]
            st["dirty"] = True
            return st, None
        if parts[2] == "line" and len(parts) == 4 and parts[3].isdigit():
            dst = int(parts[3]) - 1
            if not 0 <= dst < len(st["layout"]):
                return state, f"no line #{parts[3]}"
            st["layout"][li]["segments"].remove(seg)
            st["layout"][dst]["segments"].append(seg)
            st["dirty"] = True
            return st, None
        return state, f"can't move '{seg}' {' '.join(parts[2:])}"
    return state, f"unknown command: {cmd!r}"


def off_tray(state):
    """Segments currently toggled OFF.

    ON segments live in exactly one layout line; OFF segments live in the tray
    (in no line list).  ``off_tray`` returns the OFF segments.

    Definition: segments whose ``state["segments"][key]`` is falsy, in stable
    order — layout-line order (left to right, top to bottom) first, then any
    segment that is not referenced in any line, sorted alphabetically.  This
    matches ``_wizard_order``'s traversal so the UI is always deterministic and
    consistent with the menu numbering.
    """
    seen = []
    seen_set = set()
    for row in state["layout"]:
        for seg in row["segments"]:
            if seg in state["segments"] and seg not in seen_set:
                seen.append(seg)
                seen_set.add(seg)
    # segments not referenced in any layout line, sorted for stability
    extras = sorted(k for k in state["segments"] if k not in seen_set)
    ordered = seen + extras
    return [seg for seg in ordered if not state["segments"].get(seg)]


def layout_move(  # pylint: disable=too-many-return-statements
    state, seg, direction,
):
    """Pure 2-D move adapter for the wizard editor.  Returns ``(new_state, err)``
    matching ``_apply_wizard_command``'s contract: on success err is None and
    new_state has ``dirty=True``; on failure new_state is the unchanged input and
    err is a human-readable string.  The input state is NEVER mutated (deep-copy).

    Direction semantics
    -------------------
    left   — reorder within the segment's line toward the start (swap left).
             Delegates to ``_apply_wizard_command(state, "move <seg> up")``.
    right  — reorder within the line toward the end (swap right).
             Delegates to ``_apply_wizard_command(state, "move <seg> down")``.
    up     — move across lines toward the previous line.
             • If already on line 0 (top): send to the off-tray
               (set segments[seg]=False, remove from the line list).
             • Otherwise: move to the previous line via
               ``_apply_wizard_command(state, "move <seg> line <prev_1based>")``.
               If current 0-based index is li, previous 1-based = li  (li-1+1).
    down   — move across lines toward the next line.
             • If seg is in the off-tray (segments[seg] is False and not in any
               line): re-activate onto line 1
               (set segments[seg]=True, append to layout[0]["segments"]).
             • Otherwise if on a non-last line: move to the next line via
               ``_apply_wizard_command(state, "move <seg> line <next_1based>")``.
               next_1based = li + 2  (li is 0-based, next is li+1, 1-based = li+2).
             • If already on the last line: return an error.
    """
    if direction not in ("left", "right", "up", "down"):
        return state, f"unknown direction: {direction!r}"

    li, _pos = _find_line(state["layout"], seg)
    in_layout = li is not None

    # ── left / right: within-line reorder ──────────────────────────────────
    if direction == "left":
        if not in_layout:
            return state, f"segment '{seg}' is not in the layout"
        return _apply_wizard_command(state, f"move {seg} up")

    if direction == "right":
        if not in_layout:
            return state, f"segment '{seg}' is not in the layout"
        return _apply_wizard_command(state, f"move {seg} down")

    # ── up: cross-line toward previous ─────────────────────────────────────
    if direction == "up":
        if not in_layout:
            return state, f"segment '{seg}' is not in the layout"
        if li == 0:
            # top line → off-tray: toggle off + remove from line list
            st = copy.deepcopy(state)
            st["segments"][seg] = False
            st["layout"][0]["segments"].remove(seg)
            st["dirty"] = True
            return st, None
        # move to previous line; previous 0-based = li-1, 1-based = li
        return _apply_wizard_command(state, f"move {seg} line {li}")

    # ── down: cross-line toward next (direction == "down") ──────────────────
    seg_on = state["segments"].get(seg)
    if not in_layout and not seg_on:
        # off-tray → re-activate onto line 1 (layout index 0)
        st = copy.deepcopy(state)
        st["segments"][seg] = True
        st["layout"][0]["segments"].append(seg)
        st["dirty"] = True
        return st, None
    if not in_layout:
        return state, f"segment '{seg}' is not in the layout"
    num_lines = len(state["layout"])
    if li == num_lines - 1:
        return state, f"'{seg}' is already on the last line"
    # move to next line; next 0-based = li+1, 1-based = li+2
    return _apply_wizard_command(state, f"move {seg} line {li + 2}")


def layout_toggle(state, seg):
    """Toggle a segment between ON (in a layout line) and OFF (in the tray).

    ON segments live in exactly one layout line; OFF segments live in the tray
    (in no line list).  ``layout_toggle`` maintains this invariant:

    * If *seg* is ON (present in some layout line): set ``segments[seg]=False``
      and remove it from that line — moves to the tray.  Works from any line.
    * If *seg* is OFF (in the tray): set ``segments[seg]=True`` and append to
      ``layout[0]["segments"]`` — re-activates onto line 1.
    * If *seg* is unknown: return ``(state, "unknown segment '<seg>'")``.

    Deep-copies state; never mutates input.  Sets ``dirty=True`` on success.
    Returns ``(new_state, None)`` on success or ``(state, err_msg)`` on failure.
    """
    if seg not in state["segments"]:
        return state, f"unknown segment '{seg}'"
    st = copy.deepcopy(state)
    li, _pos = _find_line(st["layout"], seg)
    if li is not None:
        # Segment is ON — remove from its line and move to tray.
        st["segments"][seg] = False
        st["layout"][li]["segments"].remove(seg)
    else:
        # Segment is OFF (in tray) — re-activate onto line 1 (index 0).
        st["segments"][seg] = True
        st["layout"][0]["segments"].append(seg)
    st["dirty"] = True
    return st, None


# Friendly headers for the three default layout rows (keyed by min_rows);
# any other row falls back to "line N".
_ROW_LABELS = {0: "identity line", 20: "model line", 30: "diagnostics line"}

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _visible_len(s):
    """Length of `s` in terminal columns, ignoring SGR color escapes."""
    return len(_ANSI_RE.sub("", s))


def _trunc_visible(s, width):
    """Truncate `s` to `width` visible columns, keeping SGR escapes (counted as
    zero-width) and appending a reset if the text was cut, so color never bleeds."""
    if width <= 0:
        return ""
    out, vis, i, n = [], 0, 0, len(s)
    saw_sgr = False
    while i < n and vis < width:
        m = _ANSI_RE.match(s, i)
        if m:
            out.append(m.group())
            i = m.end()
            saw_sgr = True
            continue
        out.append(s[i])
        vis += 1
        i += 1
    if i < n and saw_sgr:        # truncated AND color in play → close it cleanly
        out.append(_RESET)       # (no spurious reset on plain text)
    return "".join(out)


def _wizard_groups(state):
    """The menu's segments grouped for display: one group per layout row (its
    segments in row order), then a trailing 'not in layout' group of any leftover
    segments (sorted). Single source of truth for both numbering and grouping."""
    groups, seen = [], set()
    for i, row in enumerate(state["layout"]):
        label = _ROW_LABELS.get(row.get("min_rows"), f"line {i + 1}")
        keys = [k for k in row["segments"]
                if k in state["segments"] and k not in seen]
        seen.update(keys)
        if keys:
            groups.append((label, keys))
    rest = [k for k in sorted(state["segments"]) if k not in seen]
    if rest:
        groups.append(("not in layout", rest))
    return groups


def _wizard_order(state):
    """The flat display order of segment keys — the contract a typed menu number
    resolves against (number N ⇒ the Nth key here). Derived from _wizard_groups
    so the menu and the toggle resolver can never disagree."""
    return [k for _label, keys in _wizard_groups(state) for k in keys]


def _env_truthy(val):
    """Standard env truthiness: 1/true/t/yes/y/on (case-insensitive)."""
    return str(val).strip().lower() in ("1", "true", "t", "yes", "y", "on")


def _stream_isatty(stream):
    try:
        return bool(stream.isatty())
    except (AttributeError, OSError, ValueError):
        return False


def _term_dimensions(env):
    """(cols, rows): COLUMNS/LINES from `env` when set, else the live terminal."""
    def _int(key):
        try:
            return int(env.get(key, "") or 0)
        except ValueError:
            return 0
    cols, rows = _int("COLUMNS"), _int("LINES")
    if cols and rows:
        return cols, rows
    sz = shutil.get_terminal_size((80, 24))
    return (cols or sz.columns), (rows or sz.lines)




def _provider_dir(paths, host):
    """The host's own external-segment provider directory, resolved from that
    host's lazily-read ConfigSpec (D-22) — `~/.config/ai-kit/segments` for
    Claude, `~/.config/ai-kit/segments-cursor` for Cursor. Same path the host's
    renderer reads when its AI_KIT_<HOST>_EXTERNAL_DIR override is unset."""
    return os.path.join(paths.config_dir, host_config(host).provider_dir)


def _persist_layout(paths, state, dry, known_ext_ids=None, host="claude"):  # pylint: disable=too-many-locals
    """Compute the host's minimal seg_changes + layout diff vs that host's own
    config, then delegate to ``save_statusline_config`` for the offline
    validation + atomic publish (FR-W.5 / D-23).  Returns True on success
    (including no-op and dry-run).

    ``known_ext_ids``, when given, is the set of external segment ids to treat
    as "already installed" for the boolean-toggle special-case below. An id
    EXCLUDED from ``known_ext_ids`` skips the explicit-boolean-write branch
    entirely — it is treated as "not yet installed", so no `<id> = bool` line
    is written and the renderer's own present-on-disk default (ON) applies.
    An id INCLUDED in ``known_ext_ids`` is eligible for an explicit write
    whenever ``state["segments"][id]`` differs from that default.

    This lets a caller that pre-installs a bundled example ONLY to satisfy the
    doctor's structural validation (see ``_make_wizard_commit`` in this
    module) still get correct behavior for BOTH desired states of a
    newly-installed example: exclude its id to preserve the original "not yet
    installed -> no explicit boolean, renderer shows it by default" outcome
    when the desired state IS on/default; include its id (the caller must do
    this explicitly — exclusion is not safe for every case) when the desired
    state is off, so an explicit `<id> = false` gets written instead of
    silently rendering on. The caller is responsible for deciding, per id,
    which of the two applies — this function only honors whatever set it is
    given. ``None`` (the default, used by every other caller) falls back to a
    live disk scan exactly as before."""
    cfg = _statusline_paths(paths, host)[0]
    if dry:
        print(f"[dry-run] would write {host}'s status-line config — no changes made",
              file=sys.stderr)
        return True
    seg_changes = _segment_changes_vs_recipe(cfg, state["segments"], host)
    # External toggles: only providers PRESENT in the segments dir are known to the
    # doctor (it rejects unknown [segments] keys), so only those may be written.
    # A not-yet-installed bundled example is handled by install_example_segments
    # (it copies the file → the renderer shows it by default) — never written here.
    # Write an explicit `<id> = bool` only when the desired state differs from the
    # renderer default (present → ON), e.g. to hide a provider with `<id> = false`.
    if known_ext_ids is not None:
        ext_ids_for_write = known_ext_ids
    else:
        ext_ids_for_write = {e["id"]
                             for e in _discover_user_segments(_provider_dir(paths, host))}
    for ext_id in ext_ids_for_write:
        if ext_id not in state["segments"]:
            continue
        desired = bool(state["segments"][ext_id])
        if desired != _external_enabled_in_toml(cfg, ext_id, default_on=True):
            seg_changes[ext_id] = desired
    layout = state["layout"] if state["layout"] != current_layout(cfg, host) \
        else None
    current = current_host_keys(cfg, host)
    # Only the keys that changed: an untouched key keeps its own bytes (AGENTS.md).
    key_changes = {t: {k: val for k, val in v.items() if val != current[t].get(k)}
                   for t, v in (state.get("host_keys") or {}).items() if t in current}
    key_changes = {t: v for t, v in key_changes.items() if v}
    if not (seg_changes or layout is not None or key_changes):
        return True   # nothing to write — already up-to-date
    # D-19: hand the publish primitive this host's entry too, so validation is
    # structural check PLUS an offline dry render of the candidate (synthetic
    # quota for Cursor) — never the fetch-capable `--doctor`.
    _cfg, _sample, entry, _wiring = _statusline_paths(paths, host)
    return save_statusline_config(cfg, seg_changes, layout,
                                  (paths.statusline_doctor, entry), host=host,
                                  host_keys=key_changes)


def _recover_incompatible_config(paths, dry, host="claude"):
    """If an existing HOST config is rejected by the doctor (e.g. it carries
    stale segment keys from a pre-rename ai-kit), back it up to ``<file>.bak``
    and regenerate a fresh one from that host's own recipe so the wizard's
    choices apply on a valid base. Returns True when a recovery happened.

    Uses the doctor's structural ``--host <host> --check`` (not ``--doctor``) so
    an environment-specific render failure never triggers a reset — only an
    actually-incompatible file does."""
    cfg, sample = _statusline_paths(paths, host)[:2]
    if not os.path.isfile(cfg) or not os.path.isfile(sample):
        return False
    env = dict(os.environ)
    env[host_config(host).env_prefix + "CONFIG_FILE"] = cfg
    try:
        proc = subprocess.run(
            [sys.executable, "-S", paths.statusline_doctor,
             "--host", host, "--check", cfg],
            capture_output=True, text=True, env=env, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    if proc.returncode == 0:
        return False                      # valid — keep the user's config as-is
    bak = cfg + ".bak"
    if dry:
        print(f"[dry-run] would back up incompatible {cfg} -> {bak} and "
              "regenerate from the recipe", file=sys.stderr)
        return True
    try:
        shutil.copyfile(cfg, bak)
        shutil.copyfile(sample, cfg)
    except OSError as exc:
        print(f"warn: could not reset incompatible config ({exc})", file=sys.stderr)
        return False
    print(f"note: your {host} status-line config was incompatible with this "
          "ai-kit version and has been reset to defaults.\n"
          f"      your previous file is preserved at {bak}", file=sys.stderr)
    return True


def persist_statusline(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    paths, state, adopt, dry, tty=None, assume_overwrite=False, known_ext_ids=None,
    host="claude",
):
    """Conditionally persist ONE host's status-line config + that host's wiring.

    adopt is False  -> NO-OP: write neither <host>.toml nor the host's wiring;
                       an existing status line is left untouched.
    adopt is True   -> ensure that host's OWN recipe exists (copy-if-absent),
                       write that host's config (offline-validated, published
                       atomically) via _persist_layout, then set that host's
                       wiring to `python3 -S <that host's entry>` UNLESS it
                       already points at ours (reconfigure leaves a correct,
                       possibly hand-edited command in place). Returns True on
                       success. Every path/entry/wiring target comes from the
                       single `_statusline_paths()` resolver over `Paths` plus
                       the host's lazily-read ConfigSpec — no call site chooses
                       paths from a second table, and no Claude-only name is
                       reused for a Cursor call (D-20/D-22/C-D23-1).

    ``known_ext_ids`` is forwarded to ``_persist_layout`` unchanged — see its
    own docstring; ``None`` (the default) preserves the original live-disk-scan
    behavior for every caller that doesn't need the pre-install-snapshot fix.

    Component symlinking is the caller's concern and runs INDEPENDENTLY of this
    function (a components-only install never calls persist_statusline with adopt
    True, so no status-line file is read or written)."""
    if not adopt:
        return True
    cfg, sample, entry, wiring = _statusline_paths(paths, host)
    # Adopting: the config TOML must exist before _persist_layout patches it.
    # copy-if-absent is gated here (NOT pre-wizard) so a non-adopting run never
    # materializes a status-line config (Task 10 constraint 1).
    copy_recipe_if_absent(sample, cfg, dry)
    # An existing config from an incompatible (e.g. pre-rename) ai-kit would be
    # rejected by the doctor and block the whole persist; recover it first.
    _recover_incompatible_config(paths, dry, host=host)
    if not _persist_layout(paths, state, dry, known_ext_ids=known_ext_ids,
                           host=host):
        return False
    detect = (detect_statusline if host == "claude" else detect_statusline_cursor)(paths)
    if detect["state"] == "ours":
        return True
    # Propagate the wire helper's return: True when the wiring now points at
    # ai-kit, False when left untouched (declined / headless-foreign). The
    # config write already succeeded, so a declined wire is not a hard
    # failure — but the caller can see what happened.
    if host == "claude":
        return wire_statusline(wiring, entry, tty, dry,
                               assume_overwrite=assume_overwrite)
    return wire_statusline_cursor(wiring, entry, tty, dry,
                                  assume_overwrite=assume_overwrite)


def _sample_input_path(host="claude"):
    """The preview payload for one host. Claude reads tests/fixtures/
    sample-input.json; Cursor reads tests/fixtures/sample-input-cursor.json —
    a Claude-shaped payload extended with the cursor:* fields. Missing file
    returns the path anyway; callers degrade to ``"{}"``."""
    name = ("sample-input-cursor.json" if host == "cursor"
            else "sample-input.json")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "tests", "fixtures", name)


def _read_sample_json(host):
    try:
        with open(_sample_input_path(host), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "{}"


def _engine_ns(paths, host, sample_json):
    """Bundle the engine callables for ONE host as a SimpleNamespace for
    injection into that host's HostView.  wizard_app calls these at runtime;
    they all live here so wizard_app imports nothing from setup.py.

    ``sample_json`` is captured by the ``_render_preview`` closure so the
    render call is self-contained (no shared mutable state). The closure passes
    the HOST's own entry, base config and host id — a Cursor preview never
    calls the Claude entry with Claude-only env names (D-20)."""
    # `types` is stdlib; the import is here (not top-level) because this helper
    # is only called from the wizard path (after uv re-exec), not from the
    # stdlib-only status-line render path.
    import types as _types  # pylint: disable=import-outside-toplevel

    cfg, sample, entry, _wiring = _statusline_paths(paths, host)

    def _render_preview(segments, layout=None, cols=None):
        base_config = None
        if layout is not None:
            cfg_src = cfg if os.path.isfile(cfg) else sample
            try:
                with open(cfg_src, encoding="utf-8") as fh:
                    base_config = fh.read()
            except OSError:
                base_config = ""
        env = {"STATUSLINE_COLS": str(cols), "STATUSLINE_LINES": "60"} if cols else {}
        return render_preview(entry, segments, sample_json, env,
                              layout=layout, base_config=base_config, host=host)

    extra = {}
    if host == "cursor":   # D-12: the read-only Cursor spend limit for the alert row
        extra["alert_limit_text"] = lambda: cursor_limit_text(os.environ, time.time())
    return _types.SimpleNamespace(
        render_preview=_render_preview,
        apply_command=_apply_wizard_command,
        groups=_wizard_groups,
        order=_wizard_order,
        layout_move=layout_move,
        layout_toggle=layout_toggle,
        off_tray=off_tray,
        **extra,
    )


def _hook_selection_items(paths):
    """Return the hooks category rows and installed-state baseline."""
    items = []
    initial = {}
    for hook_id in HOOK_IDS:
        installed = bool(hook_installed_hosts(paths, hook_id))
        on = installed or any(
            row.default and hook_host_present(paths, row.host)
            for row in hook_rows([(hook_id, None)])
        )
        items.append(("hooks", hook_id, on))
        initial[("hooks", hook_id)] = installed
    return items, initial


def _examples_segments_dir():
    """The repo's bundled example-segments directory — offered to EVERY
    detected host (D-18), unlike a host's own provider dir."""
    return os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "examples", "segments")


def _host_view_state(paths, cfg, host, external):
    """One host's wizard state dict: that host's OWN segment state, layout and
    adoption answer.

    Segment state = the host's built-in defaults/config plus every discovered
    external keyed by id. A provenance-"user" external lives in that host's
    provider dir and renders by default (ON unless the host's own config
    disables it); a "bundled" example is only in examples/ and is not yet
    installed, so it stays an OFF offer until chosen (D-18)."""
    segments = current_segments(cfg, host)
    for ext in external:
        segments[ext["id"]] = _external_enabled_in_toml(
            cfg, ext["id"], default_on=ext["provenance"] == "user")
    return {"segments": segments,
            "layout": current_layout(cfg, host), "dirty": False,
            "adopt": _detect_for(paths, host)["state"] == "ours",
            "host_keys": current_host_keys(cfg, host)}


def _host_done_hint(host, label):
    """The one-sentence next action for that host's own CLI."""
    if host == "claude":
        return f"Open a new {label} session to see your status line."
    return (f"Open a new {label} session (agent --resume) to see your "
            "status line.")


def _host_view(wizard_app_mod, paths, host, inventory=None):
    """Assemble one host's HostView: the host's OWN segment state, external
    segments, lazily-read ConfigSpec-derived metadata, per-host engine closure,
    live status-line callable, sample payload and gate/Done wording.

    Every path comes from `_statusline_paths()` over the already-resolved
    `Paths`; every default/filename/prefix from `host_config(host)` (lazy host
    module import). No second settings table and no copied defaults exist here
    (D-20/D-22)."""
    cfg, _sample, _entry, _wiring = _statusline_paths(paths, host)
    spec = host_config(host)
    if inventory is None:
        inventory = load_segment_inventory(INVENTORY_PATH, host)
    segment_meta = build_segment_meta(inventory,
                                      _statusline_icon_line_overrides(cfg))
    external = discover_external_segments(paths, _examples_segments_dir(), host=host)
    label = _HOST_LABELS.get(host, host)
    sample_json = _read_sample_json(host)
    return wizard_app_mod.HostView(
        id=host, label=label,
        config_label=f"~/.config/ai-kit/{spec.config_filename}",
        wiring_label=_WIRING_LABELS.get(host, "host settings"),
        state=_host_view_state(paths, cfg, host, external),
        # Live callable, not a frozen dict — re-read fresh every time the
        # wizard's gate needs it, mirroring the renderer's own re-probing.
        status_line=lambda: _detect_for(paths, host),
        segment_meta=segment_meta,
        external_segments=external,
        sample_json=sample_json,
        engine=_engine_ns(paths, host, sample_json),
        done_hint=_host_done_hint(host, label),
    )


def _detect_for(paths, host):
    """The host's live status-line adoption reading (claude/cursor share the
    `state` shape; the detection helpers differ only in wiring target)."""
    return (detect_statusline if host == "claude"
            else detect_statusline_cursor)(paths)


def _statusline_hosts_present(paths):
    """Status-line hosts to offer a host view for, Claude first.

    A host counts when its OWN config directory already exists — `~/.claude`
    (or CLAUDE_CONFIG_DIR) for Claude Code, the resolved Cursor config dir for
    Cursor CLI — never created by detection and never keyed on a binary on
    PATH. This is the SAME `statusline_host_present` rule the headless
    `--with-statusline` path uses (SPEC R11 / C-D12-2), so the wizard and the
    headless installer can never disagree about what is installed, and an
    absent dir means the wizard simply never offers that host instead of
    fabricating state for it."""
    return tuple(statusline_hosts_detected(paths))


GLOBAL_RULES_ITEM: tuple[str, str] = ("global rules", "codegraph sentence")


def _global_rules_review(rules_env):
    """The Review item for codegraph's sentence (Phase 30, D-11): None when no
    global file holds it, else the replace Changes and their preview lines."""
    if rules_env is None:
        return None
    global_rules = _sibling("global_rules")
    changes = [c for c in global_rules.plan_changes(rules_env) if c.status == "replace"]
    if not changes:
        return None
    return {"changes": changes, "preview": global_rules.preview_lines(changes)}


def _global_rules_items(review):
    """Selection items and initial state of the global-rules item: pre-checked,
    not installed yet (so confirming the default is a real write)."""
    if not review:
        return [], {}
    return [[*GLOBAL_RULES_ITEM, True]], {GLOBAL_RULES_ITEM: False}


def _build_wizard_context(  # pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments
    paths, entries, installed, wizard_app_mod, hosts=None,
    stale=None, predecessor_cands=None, pi_predecessor_cands=(), pi_stale=(),
    replace_cands=(), rules_review=None,
):
    """Construct the host-keyed WizardContext for launch_wizard (extracted for
    testability): the component selection/meta/housekeeping plus one HostView
    per status-line host (D-10/D-22).

    ``wizard_app_mod`` is the already-imported wizard_app module, passed
    explicitly so tests can supply ``tools.wizard_app`` without module-identity
    issues.

    ``hosts`` overrides detection (tests/stubbing); ``None`` resolves it from
    this machine: Claude when the `claude` binary is on PATH, Cursor when
    `~/.cursor/cli-config.json` exists.

    ``stale``/``predecessor_cands`` are launch_wizard's pre-computed detection
    results (Task 3): supplying them here only shapes ``ctx.housekeeping``'s
    display strings — defaulting to empty when omitted.

    ``_initial_enabled`` is keyed by the INSTALLED state, not the wizard's
    visual pre-selection.  On a first run the wizard pre-checks everything, but
    nothing is installed yet — so the baseline must be all-False to let
    ``_has_net_change`` (Task 5) correctly detect that confirming the defaults
    IS a write.  On a reconfigure, installed state equals the pre-selection so
    both representations agree."""
    stale = stale if stale is not None else []
    predecessor_cands = predecessor_cands if predecessor_cands is not None else []
    default = _default_selection(entries, installed)
    sel = Selection(
        (cat, name, name in default[cat])
        for cat in CATEGORIES
        for name, _ in entries[cat]
    )
    initial_enabled = {
        (cat, name): (name in installed[cat])
        for cat in CATEGORIES
        for name, _ in entries[cat]
    }
    hook_items, hook_initial = _hook_selection_items(paths)
    sel.items.extend([list(item) for item in hook_items])
    initial_enabled.update(hook_initial)
    rules_items, rules_initial = _global_rules_items(rules_review)
    sel.items.extend([list(item) for item in rules_items])
    initial_enabled.update(rules_initial)

    if hosts is None:
        hosts = _statusline_hosts_present(paths)
    inventory_claude = load_segment_inventory(INVENTORY_PATH, "claude")
    host_views = tuple(
        _host_view(wizard_app_mod, paths, host,
                   inventory=(inventory_claude if host == "claude" else None))
        for host in hosts
    )

    component_meta = {
        name: _read_component_desc(abspath)
        for cat in CATEGORIES
        for name, abspath in entries[cat]
    }
    component_meta.update({hook_id: hook_description(hook_id) for hook_id in HOOK_IDS})

    housekeeping = {
        "stale": stale + [f"{item} (pi)" for item in pi_stale],
        "predecessors": [f"{cat}/{name}" for cat, name, _old, _new in predecessor_cands]
                        + [f"{cat}/{name} (pi)"
                           for cat, name, _old, _new in pi_predecessor_cands],
        # Real content at a named skills link path (D-16) — default-No gate.
        "replace": [f"skills/{name} ({label})"
                    for label, _path, _target, name in replace_cands],
    }

    state = {"_initial_enabled": initial_enabled}
    if rules_review is not None:
        state["_global_rules"] = rules_review
    return wizard_app_mod.WizardContext(
        selection=sel,
        state=state,
        component_meta=component_meta,
        housekeeping=housekeeping,
        hosts=host_views,
    )


def apply_hook_selection(paths, checked, dry, counts):
    """Apply the wizard's checked hook ids per D-12: installed hosts plus
    present default-on hosts; an empty set means all present hosts. Unchecked
    ids remove the hook from every host where it is currently installed."""
    ok = True
    checked_ids = set(checked)
    for hook_id in HOOK_IDS:
        if hook_id in checked_ids:
            installed = hook_installed_hosts(paths, hook_id)
            selected_hosts = installed | {
                row.host for row in hook_rows([(hook_id, None)])
                if row.default and hook_host_present(paths, row.host)
            }
            if not selected_hosts:
                selected_hosts = {
                    row.host for row in hook_rows([(hook_id, None)])
                    if hook_host_present(paths, row.host)
                }
            rows = [row for row in hook_rows([(hook_id, None)])
                    if row.host in selected_hosts]
            result = wire_hook_rows(paths, rows, dry, counts)
            host_list = ", ".join(sorted(selected_hosts)) or "no present hosts"
            print(f"hooks: wired {hook_id} on {host_list}")
        else:
            hosts = hook_installed_hosts(paths, hook_id)
            rows = [row for row in hook_rows([(hook_id, None)]) if row.host in hosts]
            result = unwire_hook_rows(paths, rows, dry, counts)
            host_list = ", ".join(sorted(hosts)) or "no installed hosts"
            print(f"hooks: removed {hook_id} from {host_list}")
        if not result:
            ok = False
    return ok


def _commit_known_ext_ids(paths, host, state, examples_flag, dry):
    """Per-host version of the example-segment pre-install the commit needs.

    A discovered bundled example (e.g. system_memory) must exist under THIS
    host's provider dir before ``persist_statusline`` self-validates, otherwise
    the doctor rejects it as an unknown ``[[line]]`` segment — every discovered
    example is installed unconditionally (the Arrange board places every
    discovered segment somewhere, and the doctor validates every id present
    anywhere in ``[[line]]``, enabled or not).

    The pre-install disk snapshot is passed to ``_persist_layout`` as
    ``known_ext_ids``: without it, an off-by-default example installed moments
    ago would get an explicit ``segments.<id> = false`` written for it, masking
    a later ``--examples=all`` caller. An id whose DESIRED state is explicitly
    OFF is folded back into the set so an explicit ``false`` IS written instead
    of the present-on-disk ON default silently overriding a declined segment.

    "Desired" has two sources: an explicit ``--examples`` flag is AUTHORITATIVE
    (it wins over the wizard's toggles, mirroring ``resolve_example_selection``)
    while no flag falls back to the host's own ``state["segments"]`` toggles.

    Returns ``(known_ext_ids, segments)``: the set to persist with (empty when nothing
    was discovered) and the host's segment toggles to persist, where an explicit flag
    has replaced the wizard's toggle for every discovered example."""
    known = {e["id"] for e in _discover_user_segments(_provider_dir(paths, host))}
    segments = dict(state.get("segments") or {})
    examples_dir = os.path.join(paths.install_dir, "examples", "segments")
    examples = discover_example_segments(examples_dir)
    if examples and not dry:
        install_example_segments(examples, paths.config_dir,
                                provider_dir=host_config(host).provider_dir)
    if not examples:
        return known, segments
    if examples_flag is not None:
        desired_ids = {e["id"] for e in resolve_example_selection(examples_flag, examples)}
        segments.update({e["id"]: e["id"] in desired_ids for e in examples})
    else:
        desired_ids = {
            e["id"] for e in examples if (state.get("segments") or {}).get(e["id"], False)
        }
    newly_installed_desired_off = {
        e["id"] for e in examples
        if e["id"] not in known and e["id"] not in desired_ids
    }
    return known | newly_installed_desired_off, segments


def _commit_components(paths, entries, selection, dry, counts):
    """The component half of the wizard commit: the selected symlinks, the pi
    mirror and the hook rows. Runs once for the whole install (never per host).

    Returns ``(log, hooks_ok)`` with every diagnostic captured — this runs on a
    Textual worker thread, so it must not touch the real stdout/stderr."""
    sel = cast(Selection, selection)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        sel_sets = sel.category_sets(CATEGORIES)
        all_sets = sel.category_sets((*CATEGORIES, "hooks"))
        apply_selection(sel_sets, entries, paths.claude_dir, dry, counts)
        # The pi root mirrors the same selection (D-14): a deselected
        # PI_SKILLS entry is unlinked there too, through sync_pi_links'
        # mirror branch.
        sync_pi_links(paths, entries, dry, counts,
                      names=sel_sets["skills"], mirror=True)
        hooks_ok = apply_hook_selection(paths, all_sets.get("hooks", set()), dry, counts)
    return buf.getvalue(), hooks_ok


def _statusline_action(host_state, examples_forced=False):
    """The one host action table (D-06 as amended 2026-11-06): what the commit
    does to a host, decided by its toggle, start state and board. The wizard's
    Review text uses the same rule, so Review and commit never disagree.
    A state without `start_state` counts as `unset`; without `dirty` it counts
    as dirty, so a legacy state never skips a write."""
    host_state = host_state or {}
    start = host_state.get("start_state") or "unset"
    if host_state.get("adopt"):
        if start == "unset":
            return "wire"
        if start == "ours":
            dirty = host_state.get("dirty", True)
            return "update" if (dirty or examples_forced) else "unchanged"
        return "replace_foreign"
    if start == "ours":
        return "remove_ours"
    if start == "foreign":
        return ("remove_foreign" if host_state.get("foreign_choice") == "remove"
                else "keep_foreign")
    return "unchanged"


def _unwire_host(paths, host, dry):
    """Remove ai-kit's own wiring from ONE host and nothing else (R3, D-07)."""
    if host == "claude":
        return unwire_statusline(paths.settings, paths.install_dir, dry)
    return unwire_statusline_cursor(paths.cursor_cli_config, paths.cursor_status_line, dry)


def _same_bytes(path_a, path_b):
    """True when both files read and hold identical bytes; any read error is False."""
    try:
        with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
            return fa.read() == fb.read()
    except OSError:
        return False


def _prepare_foreign(paths, host, dry=False, cache=None):
    """Back up a foreign status line BEFORE the Review confirmation (D-08), through
    the doctor's one backup helper. Returns ``{"entry", "file", "backup"}`` or
    ``{"error"}``; a dry prepare takes no backup (``backup`` is ``""``). Never prints:
    the wizard is on screen while this runs. With a ``cache`` dict, a repeat call
    reuses the host's earlier result while the file still equals its backup, so a
    declined confirm does not take (and prune toward) a new backup per Enter."""
    detect = _detect_for(paths, host)
    if detect["state"] != "foreign":
        return {"error": "no foreign status line to back up"}
    path = paths.settings if host == "claude" else paths.cursor_cli_config
    if host == "cursor" and _cursor_config_read(path)[0] in ("jsonc", "bad"):
        return {"error": f"{path} holds JSONC comments or cannot be parsed; "
                         "ai-kit leaves it untouched"}
    prior = (cache or {}).get(host)
    if prior and prior["backup"] and _same_bytes(path, prior["backup"]):
        return prior
    backup = ""
    if not dry:
        try:
            backup = _sibling("config_doctor_appliers").backup_before_write(
                path, paths.backups_dir, host)
        except OSError as exc:
            return {"error": f"backup failed: {exc}"}
    info = {"entry": detect["current_command"] or "(unknown)", "file": path, "backup": backup}
    if cache is not None:
        cache[host] = info
    return info


def _remove_statusline_entry(paths, host, dry, approved):
    """Remove a foreign statusLine so the host shows its own default (D-06, owner
    decision 2026-11-06). The entry it pops is compared with `approved` in the same
    read; a mismatch (or an entry already gone) refuses. Writes no ai-kit line and
    touches no other key. Returns False on a refusal or a failed write."""
    if host == "claude":
        path = paths.settings
        state, data = _read_json_checked(path)
        if state == JSON_STATE_UNREADABLE:
            _warn_hook_config(path, "cannot parse as a JSON object; statusLine left as is")
            return False
        if state != JSON_STATE_OK or data is None:
            return True
        current = _statusline_command(data.get("statusLine"))
    else:
        path = paths.cursor_cli_config
        data = _cursor_config_for_write(path)
        if data is None:
            return False
        if not data:
            return True
        current = _cursor_write_state(data, paths.cursor_status_line)[1]
    if current != approved:
        print(f"error: {host} status-line command changed after approval "
              f"(approved {approved!r}, found {current!r}) — not removing a "
              "command you never approved; re-run the wizard to review it")
        return False
    data.pop("statusLine", None)
    return _commit_unwire(path, data, dry, "would remove the foreign statusLine")


def _commit_host_statusline(paths, host, host_state, dry, examples_flag):
    """ONE host's status-line commit, by `_statusline_action`: its own
    offline-validated write or removal, with its diagnostics captured into its
    OWN log string (T-23-53: a rejected Cursor candidate never blocks Claude and
    a host the user left alone is never written at all). Returns ``{"ok",
    "adopt", "log", "action"}``."""
    host_state = host_state or {}
    adopt = bool(host_state.get("adopt"))
    action = _statusline_action(host_state, examples_forced=examples_flag is not None)
    if action == "keep_foreign" or (action == "unchanged" and not adopt):
        # Owner decision 2026-11-06: nothing is written, no backup, no re-read.
        return {"ok": True, "adopt": adopt, "log": "", "action": action}
    hbuf = io.StringIO()
    if action in ("replace_foreign", "remove_foreign") and not host_state.get("foreign_ok"):
        hbuf.write(f"error: {host} foreign status line was not confirmed on Review; "
                   "nothing written\n")
        return {"ok": False, "adopt": adopt, "log": hbuf.getvalue(), "action": action}
    if not dry and "adopt_command" in host_state:
        # The gate approved ONE exact wiring value; publish or remove only while
        # the host's live wiring still IS that value. A mismatch means another
        # process changed the command after approval — the toggle is not blanket
        # overwrite permission for a command the user never saw.
        approved = host_state.get("adopt_command")
        fresh = _detect_for(paths, host).get("current_command")
        if fresh != approved:
            hbuf.write(
                f"error: {host} status-line command changed after approval "
                f"(approved {approved!r}, found {fresh!r}) — not replacing a "
                "command you never approved; re-run the wizard to review it\n")
            return {"ok": False, "adopt": adopt, "log": hbuf.getvalue(), "action": action}
    backup = host_state.get("foreign_backup")
    if (not dry and backup and action in ("replace_foreign", "remove_foreign")
            and not _same_bytes(
                paths.settings if host == "claude" else paths.cursor_cli_config, backup)):
        # The backup the user confirmed must still be the file about to be overwritten;
        # otherwise restoring it would lose whatever changed in between.
        hbuf.write(f"error: {host} config changed after the backup you confirmed "
                   f"({backup}) — not overwriting it; re-run the wizard to review it\n")
        return {"ok": False, "adopt": adopt, "log": hbuf.getvalue(), "action": action}
    host_ok = True
    try:
        with contextlib.redirect_stdout(hbuf), contextlib.redirect_stderr(hbuf):
            if action == "remove_ours":
                host_ok = _unwire_host(paths, host, dry)
            elif action == "remove_foreign":
                host_ok = _remove_statusline_entry(
                    paths, host, dry, host_state.get("adopt_command"))
            else:
                known_ext_ids, segments = _commit_known_ext_ids(
                    paths, host, host_state, examples_flag, dry)
                host_ok = persist_statusline(
                    paths, {**host_state, "segments": segments}, adopt, dry, tty=None,
                    assume_overwrite=True, known_ext_ids=known_ext_ids,
                    host=host)
    except OSError as exc:
        # A filesystem failure on THIS host (unwritable config directory,
        # failed candidate temp file, …) records that host's failed outcome
        # and must not abort the loop — the other hosts still commit (D-22).
        host_ok = False
        hbuf.write(f"error: {host} status-line commit failed: {exc}\n")
    return {"ok": bool(host_ok), "adopt": adopt, "log": hbuf.getvalue(), "action": action}


def _commit_global_rules(rules_env, rules_review, selection, dry):
    """Apply the global-rules rewrite the user reviewed, only while its item is on.
    Returns (ok, log); the files written are those still equal to the reviewed bytes."""
    if rules_review is None or rules_env is None:
        return True, ""
    on = any(cat == GLOBAL_RULES_ITEM[0] and name == GLOBAL_RULES_ITEM[1] and flag
             for cat, name, flag in cast(Selection, selection).items)
    if not on:
        return True, ""
    global_rules = _sibling("global_rules")
    ok, lines = global_rules.apply(rules_env, dry, reviewed=rules_review["changes"])
    return ok, "".join(line + "\n" for line in lines)


def _make_wizard_commit(  # pylint: disable=too-many-arguments
        paths, entries, dry, counts, examples_flag=None, *, rules_env=None, rules_review=None):
    """Build the ``commit`` callable the wizard runs IN-UI on Review-confirm.

    It performs the real install — component symlinks, then, per host the user
    adopted at that host's gate, that host's offline-validated config write plus
    that host's wiring — honoring the adopt decision already made in the UI
    (``assume_overwrite`` so a foreign command isn't re-prompted on the
    terminal). Hosts are committed in detection order (Claude first) and one
    host's failure never skips the others (D-11).

    ``examples_flag`` is the CLI ``--examples`` value (``None``/``"all"``/
    ``"none"``/an id list). It is the AUTHORITATIVE desired state for every
    discovered bundled example when given, overriding each host's own toggle —
    see ``_commit_known_ext_ids`` for why the distinction is load-bearing.

    The callable is invoked from a Textual worker thread, so it must NOT print
    to stdout/stderr (that would corrupt the alternate screen). All diagnostics
    the inner functions emit (doctor rejection reason, incompatible-config reset
    note, …) are captured per host into the returned outcome's ``log`` string;
    the caller prints it AFTER the app exits. Returns
    ``{"ok": bool, "adopt": bool, "log": str, "hosts": {host: {"ok", "adopt",
    "log", "action"}}}`` — the component-level keys keep the single-host shape,
    ``hosts`` carries the per-host outcome the Done screen and ``cmd_install``
    consume. ``action`` is the host's ``_statusline_action`` name (``wire``,
    ``update``, ``unchanged``, ``remove_ours``, ``keep_foreign``,
    ``remove_foreign``, ``replace_foreign``); a host the toggle leaves alone is
    never written, whatever its action."""
    def commit(selection, states):
        component_log, hooks_ok = _commit_components(
            paths, entries, selection, dry, counts)
        hosts_out = {}
        for host, host_state in (states or {}).items():
            hosts_out[host] = _commit_host_statusline(
                paths, host, host_state, dry, examples_flag)
        adopt_any = any(o["adopt"] for o in hosts_out.values())
        rules_ok, rules_log = _commit_global_rules(rules_env, rules_review, selection, dry)
        ok = bool(hooks_ok) and all(o["ok"] for o in hosts_out.values()) and rules_ok
        host_log = "\n".join(o["log"] for o in hosts_out.values() if o["log"])
        return {"ok": ok, "adopt": adopt_any,
                "log": component_log + rules_log + (host_log + "\n" if host_log else ""),
                "hosts": hosts_out}
    return commit


def _make_apply_housekeeping(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    paths, entries, stale, predecessor_cands, dry, counts,
    pi_predecessor_cands=(), pi_stale=(), replace_cands=(), log_sink=None,
    rules_review=None,
):
    """Build the apply_housekeeping(prune, repoint) callable the wizard runs
    IN-UI right after its housekeeping gate is answered (before Choose becomes
    usable). Applies the stale-prune and/or predecessor-repoint decision on
    BOTH roots (claude and pi, D-17), then rebuilds installed_links + the
    default component selection from scratch — a repointed predecessor link
    becomes a current ai-kit link, which can change which components default
    to pre-checked on Choose (mirrors the ordering the old CLI-side
    prune_stale/adopt_predecessor_links -> installed_links sequence relied
    on). Each predecessor answer moves the old link into the per-root backups
    dir first (SPEC R8). A pi link this callable creates (a pi-only repoint)
    pre-checks that skill in the returned selection, so the commit links its
    claude path and the mirror keeps the pi link.

    Like `commit`, this runs on a Textual worker thread, so it must NOT print
    to the real stdout/stderr: everything the inner helpers emit is captured
    into the returned dict's `log` string.

    ``replace_cands`` is launch_wizard's pre-computed replace_candidates list
    (the real content standing at a skills link path, minus the paths the
    predecessor gates own). With ``replace`` true, backup_and_link (D-15/D-16)
    moves each into the per-root backups dir and links the repo copy; every
    pi-labelled candidate it linked joins the pre-checked set, so the commit
    keeps an accepted pi-only replace instead of the mirror unlinking it.
    ``log_sink``, when a list, receives the captured log in a ``finally`` —
    even when a later move raises — so launch_wizard can print where each
    backup went after the wizard has exited."""
    def apply_housekeeping(prune, repoint, replace=False):
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                if stale and prune:
                    apply_stale_prune(paths.claude_dir, stale, dry, counts)
                if pi_stale and prune:
                    apply_stale_prune(paths.pi_dir, pi_stale, dry, counts)
                if predecessor_cands:
                    apply_predecessor_links(
                        paths.claude_dir, predecessor_cands, repoint, dry, counts,
                        backup_dir=os.path.join(paths.backups_dir, "claude"))
                if pi_predecessor_cands:
                    apply_predecessor_links(
                        paths.pi_dir, pi_predecessor_cands, repoint, dry, counts,
                        backup_dir=os.path.join(paths.backups_dir, "pi"))
                if replace and replace_cands:
                    # The replace gate's explicit yes: move each into the
                    # per-root backups dir (D-15) and link the repo copy
                    # (D-16). Its `moved` lines reach the returned log.
                    backup_and_link(replace_cands, paths, dry, counts)
                installed = installed_links(paths.claude_dir, paths.install_dir)
                default = _default_selection(entries, installed)
                default = {cat: set(names) for cat, names in default.items()}
                # A pi link created here must survive the commit's mirror:
                # pre-check the skill so the commit links its claude path and
                # never unlinks the accepted pi link (D-14; replace: D-16).
                precheck = ({name for _c, name, _o, _n in pi_predecessor_cands}
                            if repoint else set())
                if replace:
                    precheck |= {name for label, _p, _t, name in replace_cands
                                 if label == "pi"}
                for name in precheck:
                    default["skills"].add(name)
                hook_items, hook_initial = _hook_selection_items(paths)
                rules_items, rules_initial = _global_rules_items(rules_review)
                sel = Selection(
                    [(cat, name, name in default[cat])
                     for cat in CATEGORIES
                     for name, _ in entries[cat]] + hook_items + rules_items
                )
                initial_enabled = {
                    (cat, name): (name in installed[cat])
                    for cat in CATEGORIES
                    for name, _ in entries[cat]
                }
                initial_enabled.update(hook_initial)
                initial_enabled.update(rules_initial)
        finally:
            # Even when a later move raises, the log captured so far (with the
            # backup destinations of the moves that succeeded) reaches the
            # sink — launch_wizard prints it after the wizard has exited.
            if isinstance(log_sink, list):
                log_sink.append(buf.getvalue())
        return {"selection": sel, "initial_enabled": initial_enabled,
                "log": buf.getvalue()}
    return apply_housekeeping


def launch_wizard(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    paths, entries, installed, tty, dry, counts, examples_flag=None, env=None,
):
    """Build the engine context and run the Textual wizard.  Applies the chosen
    selection on confirm; a None result (abort) leaves everything as-is.

    ``examples_flag`` is forwarded unchanged to ``_make_wizard_commit`` — see
    its docstring for why an explicit CLI ``--examples`` value must override
    the wizard's own segment toggles for the in-UI commit, not just the
    (now largely redundant, see IN-01) post-wizard install step in
    ``cmd_install``.

    Fail-closed / single-path: this function is only reached after
    ``require_tty(open_tty())`` in ``main()`` has guaranteed a real,
    Textual-drivable terminal.  If a non-real tty somehow reaches here,
    the program fails loud — it never silently applies defaults.

    Lazy import of wizard_app is intentional: this function is only reached
    after ensure_rich_runtime() has guaranteed textual is available."""
    # Guard: belt-and-suspenders — require_tty in main() is the primary gate.
    isatty_fn = getattr(tty, "isatty", None)
    if tty is None or not callable(isatty_fn) or not isatty_fn():
        print(
            "error: launch_wizard reached without a real terminal — this is a bug. "
            "require_tty() should have exited before this point.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Ensure tools/ is on sys.path so `import wizard_app` resolves regardless
    # of the caller's CWD (repo root in tests; tools/ when run directly).
    wizard_app = _sibling("wizard_app")

    present = {cat: {n for n, _ in entries[cat]} for cat in CATEGORIES}
    stale = stale_link_candidates(paths.claude_dir, paths.install_dir, present)
    predecessor_cands = predecessor_candidates(paths.claude_dir, paths.install_dir, entries)
    # The pi root's own stale links and predecessors (D-17). Only computed when
    # the pi agent dir exists — a missing one is a note at commit time, never
    # created.
    if os.path.isdir(paths.pi_dir):
        pi_stale = [item for item in
                    stale_link_candidates(paths.pi_dir, paths.install_dir, present)
                    if item.startswith("skills/")]
        pi_predecessor_cands = predecessor_candidates(
            paths.pi_dir, paths.install_dir, _pi_entries(entries))
    else:
        pi_stale, pi_predecessor_cands = [], ()
    # The replace gate's candidates (D-16): every real/foreign entry at a
    # named skills link path, minus the paths the predecessor gates already
    # own — the three gates' candidate sets stay disjoint, so no answer at an
    # earlier gate can touch a path this gate listed.
    pred_paths = ({os.path.join(paths.claude_dir, cat, name)
                   for cat, name, _o, _n in predecessor_cands}
                  | {os.path.join(paths.pi_dir, cat, name)
                     for cat, name, _o, _n in pi_predecessor_cands})
    replace_cands = [cand for cand in replace_candidates(
        paths, entries, [name for name, _ in entries["skills"]])
        if cand[1] not in pred_paths]
    # One host view per detected status-line host, built inside the context
    # assembly — never a copied Claude-only dict (D-22). A status-line host with
    # no state here is not offered at all: an empty hosts tuple means the flow
    # simply never reaches Arrange, not a new UI state.
    rules_env = os.environ
    rules_review = _global_rules_review(rules_env)
    ctx = _build_wizard_context(paths, entries, installed, wizard_app,
                                stale=stale, predecessor_cands=predecessor_cands,
                                pi_predecessor_cands=pi_predecessor_cands,
                                pi_stale=pi_stale, replace_cands=replace_cands,
                                rules_review=rules_review)
    # The real install (component symlinks + doctor-validated status-line write +
    # settings.json wiring) now runs INSIDE the wizard on Review-confirm, so the
    # Done screen reflects the actual result. Inject the commit + housekeeping
    # callables here, where paths/entries/dry/counts are in scope.
    hk_log: list[str] = []
    env = os.environ if env is None else env
    ctx = ctx._replace(
        commit=_make_wizard_commit(paths, entries, dry, counts, examples_flag=examples_flag,
                                   rules_env=rules_env, rules_review=rules_review),
        apply_housekeeping=_make_apply_housekeeping(
            paths, entries, stale, predecessor_cands, dry, counts,
            pi_predecessor_cands=pi_predecessor_cands, pi_stale=pi_stale,
            replace_cands=replace_cands, log_sink=hk_log, rules_review=rules_review),
        doctor=_make_doctor_factory(env, dry=dry),
        prepare_foreign=functools.partial(_prepare_foreign, paths, dry=dry, cache={}),
    )
    # An explicit --examples is the authority for the clean-reconfigure rule (the
    # wizard's Review and the commit read this one key; REVIEWS HIGH 4).
    ctx.state["_examples_forced"] = examples_flag is not None
    try:
        # curl | bash inherits the script pipe as fd 0; Textual reads keys from
        # fd 0, so redirect it onto the controlling terminal for the run.
        with stdin_on_tty():
            result = wizard_app.run_wizard(ctx)
    except wizard_app.WizardCrash as exc:
        reason = exc.args[0] if exc.args else exc
        result = getattr(exc, "result", None)
        if result is None:
            print(f"error: wizard failed — {reason}", file=sys.stderr)
            sys.exit(2)
        # The commit already ran: keep its log and result, only the screen after it failed.
        print(f"warning: the wizard screen failed after the install — {reason}", file=sys.stderr)
    finally:
        # The housekeeping log (every `moved <path> -> <dest>` backup line)
        # reaches the user on confirm, abort and crash alike — but only once
        # the alternate screen is gone, never while the wizard is up.
        hk_text = "\n".join(hk_log).strip()
        if hk_text:
            print(hk_text, file=sys.stderr)
    if result is None:
        return None
    # apply_selection + persist_statusline already ran in-UI via the commit
    # callback (their counts mutations are reflected in `counts`). Surface the
    # captured diagnostics now that the alternate screen is gone, and warn on a
    # settings write (status line or hook) that was refused or failed.
    # The per-host logs ride on each host's serialized state; concatenate in
    # host order so a two-host run prints both outcomes (never one merged blob).
    log = "\n".join(
        (st or {}).get("_commit_log", "").strip()
        for st in result.state.values() if isinstance(st, dict)
    ).strip()
    if log:
        print(log, file=sys.stderr)
    if any((st or {}).get("_commit_ok") is False
           for st in result.state.values() if isinstance(st, dict)):
        print(
            "warning: some settings could not be written — see the log above "
            "(component selections were still applied).",
            file=sys.stderr,
        )
    return result   # propagate wizard result to cmd_install (I-1)


def cmd_install(env, tty, dry, examples_flag=None):
    """Reconcile skills/agents/commands and wire the status line. Interactive-only
    and fail-closed: ``require_tty`` exits before this function is ever called with
    tty=None, so tty is always a real terminal here. The ``reconfigure`` subcommand
    is install without first-run defaults — when anything is already linked,
    _first_run() is False, so the selection keeps existing state."""
    paths = resolve_paths(env)
    migrate_statusline(paths, dry)
    entries = enumerate_entries(paths.install_dir)
    counts = new_counts()
    installed = installed_links(paths.claude_dir, paths.install_dir)

    # A: choose what to install + segment layout via Textual wizard (Task 2.1+).
    # Stale-link pruning and predecessor-link repointing (previously raw
    # pre-UI terminal prompts here) now happen INSIDE the wizard's housekeeping
    # gate — see launch_wizard / _build_wizard_context / _make_apply_housekeeping.
    result = launch_wizard(paths, entries, installed, tty, dry, counts,
                           examples_flag=examples_flag, env=env)

    # Example external segments (system_memory, …). Aborting the wizard
    # (result is None) is a full no-op — nothing further is installed. On a
    # confirmed install the wizard's own segment toggles drive what gets
    # installed (no double-prompt, I-1); an explicit --examples flag
    # (all|none|<ids>) overrides that selection.
    if result is not None:
        examples = discover_example_segments(
            os.path.join(paths.install_dir, "examples", "segments"))
        if examples:
            # One pass per host the wizard actually showed: each host's own
            # segment toggles drive its own provider dir, an explicit
            # --examples flag still wins (the same "flag wins" contract the
            # in-UI commit uses), and one host's install never skips another's.
            for host, host_state in result.state.items():
                if not isinstance(host_state, dict):
                    continue          # only host-keyed states, never a stray key
                seg_state = host_state.get("segments") or {}
                if not host_state.get("adopt"):
                    continue          # a declined host wrote nothing, install nothing
                if examples_flag is not None:
                    chosen = select_examples(examples, examples_flag, tty)
                else:
                    chosen = [e for e in examples if seg_state.get(e["id"], False)]
                if chosen and not dry:
                    ids = install_example_segments(
                        chosen, paths.config_dir,
                        provider_dir=host_config(host).provider_dir)
                    print(f"examples ({host}): installed {len(ids)} external "
                          f"segment(s): {', '.join(ids)}")

    print(f"summary: {counts['linked']} linked, {counts['relinked']} relinked, "
          f"{counts['unlinked']} unlinked, {counts['pruned']} pruned, "
          f"{counts['skip_foreign']} foreign-skipped, {counts['skip_real']} real-skipped")
    print(f"ai-kit installed at {paths.install_dir}")
    print(f"doctor: {_doctor_cmd(paths)}")
    if dry:
        print("(dry-run — no changes were made)")
    return 0


def _headless_paths_and_entries(env):
    """resolve_paths + enumerate_entries behind ONE error boundary. Returns
    (paths, entries), or (None, None) after printing one warning — the
    exit-code-1 path the headless contract requires instead of a traceback.

    enumerate_entries is the call that can actually raise: it does os.path.isdir
    + os.listdir on install_dir (tools/setup.py:605-606), e.g. an AI_KIT_DIR that
    exists but is not readable. resolve_paths (tools/setup.py:49-77) is pure
    env.get + os.path.join with no filesystem access and cannot raise OSError; it
    is inside this try only so the boundary still holds if it ever grows I/O."""
    try:
        paths = resolve_paths(env)
        return paths, enumerate_entries(paths.install_dir)
    except OSError as exc:
        print(f"warn: headless setup could not resolve install paths/entries: {exc}",
              file=sys.stderr)
        return None, None


def _headless_link_skills(  # pylint: disable=too-many-arguments
        skills_flag, entries, claude_dir, dry, counts, *, replaced=frozenset()):
    """Resolve --skills and link the result additively. Returns (ok, chosen).

    `replaced` holds the link paths a --dry-run --replace-existing pass would
    have moved and linked (backup_and_link counted them): they are skipped
    here, so the dry run predicts the real run instead of reporting them as
    blocked.

    `chosen` is resolve_skills_flag's value -- None when --skills was not passed
    at all, an empty set when it named only unknown skills -- so the caller can
    tell those two apart in the summary line.

    `ok` is False only when a skill that EXISTS in the repo was requested and is
    NOT linked afterwards. Two shapes of that: link_one raising OSError (a real
    filesystem error), or link_one recording a conflict in counts -- it bumps
    skip_foreign (the link path is a symlink pointing outside ai-kit) or
    skip_real (the link path is a real file/dir) and returns normally, so the
    only way to see it is to compare the counters around the call. An unknown
    NAME keeps ok True: nothing was asked of the filesystem.

    Budget: 5 args + 5 locals = 10 of 15; 5 branches of 12; 4 returns of 6."""
    chosen, unknown = resolve_skills_flag(skills_flag, entries)
    for name in unknown:
        print(f"warn: --skills named unknown skill {name!r} — skipping", file=sys.stderr)
    if not chosen:
        return True, chosen
    blocked_before = counts["skip_foreign"] + counts["skip_real"]
    to_link = {name for name in chosen
               if os.path.join(claude_dir, "skills", name) not in replaced}
    try:
        apply_additive_skills(to_link, entries, claude_dir, dry, counts)
    except OSError as exc:
        print(f"warn: failed to link one or more requested skills: {exc}",
              file=sys.stderr)
        return False, chosen
    if counts["skip_foreign"] + counts["skip_real"] > blocked_before:
        print("warn: one or more requested skills were left alone (a foreign "
              "symlink or a real file occupies the link path) — re-run with "
              "--replace-existing to back it up and link the repo copy — see "
              "the warnings above", file=sys.stderr)
        return False, chosen
    return True, chosen


def replace_candidates(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        paths, entries, names):
    """The real content standing at a named link path that --replace-existing
    (D-16) would move into the backups dir: for each skills entry in `names`,
    the claude path and (PI_SKILLS names, existing pi dir) the pi path. A path
    is a candidate when it exists (lexists) and is NOT a current ai-kit link:
    real dirs, files, live foreign links AND dangling links all count — the
    flag is the explicit confirmation, and headless never runs the predecessor
    gate (the wizard's replace gate drops the paths its own gates own).
    Returns (label, path, target, name) tuples."""
    by_name = dict(entries["skills"])
    claude_installed = installed_links(paths.claude_dir, paths.install_dir)["skills"]
    pi_installed = (installed_links(paths.pi_dir, paths.install_dir)["skills"]
                    if os.path.isdir(paths.pi_dir) else {})
    out = []
    for name in sorted(names):
        target = by_name.get(name)
        if target is None:
            continue
        for label, root, installed in (
                ("claude", paths.claude_dir, claude_installed),
                ("pi", paths.pi_dir, pi_installed)):
            if label == "pi" and name not in PI_SKILLS:
                continue
            path = os.path.join(root, "skills", name)
            if not os.path.lexists(path) or name in installed:
                continue
            out.append((label, path, target, name))
    return out


def backup_and_link(cands, paths, dry, counts):
    """Move each candidate into its per-root backups dir (D-15) and link the
    repo copy in its place. When link_one raises after the move, the entry is
    moved back, the empty claim removed, a `warn:` line printed and skip_real
    counted, so a failed replace never leaves the skill path empty (the caller
    exits 1). Returns the paths a dry run would have moved and linked (each
    counted as linked), so the link steps can skip them; empty when not dry."""
    planned = set()
    for label, path, target, name in cands:
        if dry:
            print(f"would move {path} to {os.path.join(paths.backups_dir, label)}")
            planned.add(path)
            counts["linked"] += 1
            continue
        dest = _backup_entry(path, os.path.join(paths.backups_dir, label), name)
        print(f"moved {path} -> {dest}", file=sys.stderr)
        claim = os.path.dirname(dest)
        try:
            link_one(path, target, dry, counts)
        except OSError as exc:
            shutil.move(dest, path)
            os.rmdir(claim)
            print(f"warn: linking {path} failed ({exc}); "
                  "restored it from the backup", file=sys.stderr)
            counts["skip_real"] += 1
    return planned


def _headless_sync_pi(  # pylint: disable=too-many-arguments
        paths, entries, dry, counts, chosen, *, replaced=frozenset()):
    """Run sync_pi_links for a headless --skills run (additive, never unlinks:
    mirror=False). Only called when `chosen` is not None — a bare or hooks-only
    headless run never touches the pi root. Returns False when the mirror hit a
    foreign link or real content at a pi link path (link_one counted it). A pi
    path in `replaced` (a dry run's planned move) is skipped, as in
    _headless_link_skills."""
    blocked_before = counts["skip_foreign"] + counts["skip_real"]
    names = {name for name in chosen
             if os.path.join(paths.pi_dir, "skills", name) not in replaced}
    sync_pi_links(paths, entries, dry, counts, names=names, mirror=False)
    if counts["skip_foreign"] + counts["skip_real"] > blocked_before:
        print("warn: one or more pi links were left alone (a foreign symlink "
              "or a real file occupies the pi link path) — see the warnings "
              "above", file=sys.stderr)
        return False
    return True


def _headless_wire_statusline(paths, hosts, dry):
    """Wire the ai-kit status line on every selected host, Claude before Cursor.

    Only hosts whose config directory is actually there are wired: like the hook
    writers, headless setup never CREATEs ~/.claude or the Cursor config dir
    (wire_statusline has no host-presence guard of its own and
    _atomic_write_json would os.makedirs the parent). An absent dir is a benign
    skip -> exit 0; naming such a host explicitly is refused earlier, at command
    entry, so the guard here is the backstop for a dir that disappears between
    validation and write.

    `hosts` is empty only when nothing was asked for or nothing was detected:
    the run reports that there is nothing to wire and still succeeds (SPEC R11
    empty edge). Budget: 2 args + 4 locals (ok, wired, host, result) = 6 of 15;
    5 branches of 12; 1 return of 6."""
    ok = True
    wired = 0
    for host in STATUSLINE_HOSTS:
        if host not in hosts:
            continue
        if not statusline_host_present(paths, host):
            print(f"skipped ai-kit status line — no {host} dir")
            continue
        wired += 1
        result = (wire_statusline(paths.settings, paths.status_line, None, dry)
                  if host == "claude" else
                  wire_statusline_cursor(paths.cursor_cli_config,
                                         paths.cursor_status_line, None, dry))
        ok = ok and result
    if not wired:
        print("headless: no status-line host detected — nothing to wire")
    return ok


def _statusline_selection(raw, detected):
    """Resolve `--with-statusline` to its host list at command entry (D-23).

    The bare form names every host, so the wiring step can report each one whose
    config directory is absent as a benign skip (the --with-hooks precedent)
    instead of silently ignoring it. The `=<hosts>` form is parsed against what
    was detected: ordered Claude-first, de-duplicated, and never containing an
    unknown or undetected name by the time this returns.
    """
    if not isinstance(raw, str):
        return list(STATUSLINE_HOSTS)
    return parse_statusline_hosts(raw, detected)


def _statusline_request(with_statusline):
    """The host list a headless run should wire, or None when the flag was absent.

    main() resolves `--with-statusline=<hosts>` at command entry; a bare flag
    (True) reaching here means a caller bypassed main(), so it gets the same
    all-hosts meaning: every name is then filtered by the dir-presence guard in
    _headless_wire_statusline rather than rejected.
    """
    if with_statusline is False:
        return None
    if isinstance(with_statusline, (list, tuple)):
        return list(with_statusline)
    return list(STATUSLINE_HOSTS)


def hook_host_present(paths, host):
    """Whether the host's config directory already exists (never create it)."""
    host_dirs = {"claude": paths.claude_dir, "cursor": paths.cursor_dir,
                 "pi": paths.pi_dir, "opencode": paths.opencode_dir}
    return os.path.isdir(host_dirs[host])


def hook_link_path(paths, row):
    """The link location for a symlink row; Claude rows are config-backed."""
    if row.host == "cursor":
        return None
    if row.host == "pi":
        return os.path.join(paths.pi_dir, "extensions", os.path.basename(row.script))
    if row.host == "opencode":
        return os.path.join(paths.opencode_dir, "plugins", os.path.basename(row.script))
    return None


def _wire_cursor_rows(paths, rows, dry):
    """Wire Cursor briefing rows through the existing Cursor writer."""
    if not rows:
        return True
    present = hook_host_present(paths, "cursor")
    script_path = os.path.join(paths.install_dir, *rows[0].script.split("/"))
    return not present or wire_hook_cursor(paths.cursor_hooks, script_path, dry)


def wire_hook_rows(paths, rows, dry, counts):
    """Wire all selected hook rows by host, using guarded Claude writes and
    owned symlinks for pi/opencode. Every host is attempted; absent hosts are
    benign skips, while a failed write or foreign path makes the result false."""
    ok = True
    claude_rows = [row for row in rows if row.host == "claude"]
    if claude_rows:
        present = hook_host_present(paths, "claude")
        result = wire_claude_rows(paths.settings, claude_rows, paths.install_dir, dry)
        if present and not result:
            ok = False
    if not _wire_cursor_rows(paths, [row for row in rows if row.host == "cursor"], dry):
        ok = False
    for row in rows:
        if row.host in ("claude", "cursor"):
            continue
        if not hook_host_present(paths, row.host):
            print(f"skipped {row.id} for {row.host} — no {row.host} dir")
            continue
        link_path = hook_link_path(paths, row)
        target = os.path.join(paths.install_dir, *row.script.split("/"))
        before_foreign = counts["skip_foreign"]
        before_real = counts["skip_real"]
        try:
            link_one(link_path, target, dry, counts, install_dir=paths.install_dir)
        except OSError as exc:
            print(f"warn: failed to link {link_path}: {exc}", file=sys.stderr)
            ok = False
        if counts["skip_foreign"] > before_foreign or counts["skip_real"] > before_real:
            ok = False
    return ok


def _headless_wire_hook_ids(paths, selection, dry, counts):
    """Wire selected registry rows; absent hosts are expected skips."""
    return wire_hook_rows(paths, hook_rows(selection), dry, counts)


def _headless_wire_default_hooks(paths, dry, counts):
    """Wire every default row once in registry order."""
    rows = [row for row in HOOK_REGISTRY if row.default]
    return wire_hook_rows(paths, rows, dry, counts)


def _headless_install_examples(paths, examples_flag, dry):
    """Install the example segments --examples selects, reusing the same
    primitives cmd_install uses (select_examples never touches tty on the
    flag-given branch, so None is a safe tty here).

    Returns False when an explicitly requested install did not happen:
    install_example_segments raising OSError (its own os.makedirs of the
    segments dir, on an unwritable/blocked config dir), or returning FEWER ids
    than were picked -- its documented per-provider skip (unreadable source, bad
    destination), already warned about on stderr by install_example_segments
    itself, summarized once more here so the exit code has a stated reason.
    An empty selection (--examples=none, or nothing discovered) is True:
    nothing was asked of the filesystem.

    Budget: 3 args + 4 locals (examples, picked, ids, exc) = 7 of 15;
    4 branches of 12; 5 returns of 6."""
    examples = discover_example_segments(
        os.path.join(paths.install_dir, "examples", "segments"))
    picked = select_examples(examples, examples_flag, None) if examples else []
    if not picked:
        return True
    if dry:
        print(f"would install {len(picked)} external segment(s): "
              f"{', '.join(e['id'] for e in picked)}")
        return True
    try:
        ids = install_example_segments(picked, paths.config_dir)
    except OSError as exc:
        print(f"warn: examples: could not install into {paths.config_dir}: {exc}",
              file=sys.stderr)
        return False
    print(f"examples: installed {len(ids)} external segment(s): {', '.join(ids)}")
    if len(ids) < len(picked):
        print(f"warn: examples: {len(picked) - len(ids)} requested segment(s) were "
              "skipped (see the warnings above)", file=sys.stderr)
        return False
    return True


def _headless_summary(requested, skills_matched_nothing, counts):
    """The single stdout summary line for a headless run. Pure -- no I/O -- so
    the three cases are unit-testable without a temp dir. `requested` is False
    only for bare --headless; `skills_matched_nothing` distinguishes
    `--skills ghost` (asked for something, nothing valid matched) from it."""
    if not requested:
        return ("headless: nothing requested — pass --skills/--with-statusline/"
                "--with-hooks/--examples to link or wire something")
    if skills_matched_nothing:
        return ("headless: --skills matched no valid names — nothing linked "
                "(see warnings above)")
    return (f"headless summary: {counts['linked']} linked, "
            f"{counts['relinked']} relinked, {counts['skip_foreign']} foreign-skipped, "
            f"{counts['skip_real']} real-skipped")


def _headless_replace(paths, entries, skills_flag, dry, counts):
    """The --replace-existing pass: the paths a dry run would move (empty
    for a real run), or None when an entry could not be backed up.

    main() already rejects --replace-existing without --headless --skills, so
    skills_flag is not None here and resolve_skills_flag is pure; the set is
    the same one _headless_link_skills re-resolves (unknown names are warned
    there). Under --dry-run backup_and_link prints `would move`, links nothing
    and returns the planned paths, which the link steps then skip."""
    try:
        return backup_and_link(
            replace_candidates(paths, entries, resolve_skills_flag(skills_flag, entries)[0]),
            paths, dry, counts)
    except OSError:
        # _backup_entry has already reported the failure naming source and
        # destination; keep going so the linking step runs (link_one leaves
        # whatever is still at an unmoved path alone).
        print("warn: --replace-existing could not back up every entry "
              "(see above)", file=sys.stderr)
        return None


def _headless_apply_global_rules(env, dry):
    """--with-global-rules: rewrite codegraph's sentence in the four global files.

    Prints one line per file (and the preview under --dry-run); False when a backup or
    write failed. Skips (missing file, no block) are not failures."""
    global_rules = _sibling("global_rules")
    ok, lines = global_rules.apply(env, dry)
    for line in lines:
        print(line)
    return ok


def cmd_install_headless(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        env, dry, skills_flag, with_statusline, with_hooks, examples_flag=None,
        replace_existing=False, with_global_rules=False):
    """The --headless counterpart to cmd_install: no Textual, no tty, no
    require_tty gate. Bare (all flags falsy) only prunes dead ai-kit links (claude
    root, then the pi root when it exists) and links or wires nothing -- 'nothing
    linked unless asked' (and nothing fetched -- see the plan's sync note;
    this function never syncs the repo, headless or not). --skills links
    additively (apply_additive_skills, never unlinks). --with-statusline/
    --with-hooks independently opt into wiring those, reusing the existing
    tty-safe primitives (wire_statusline is now itself headless-safe -- see
    Task 1 -- and registry hook writers already were); both wiring
    flags treat an absent host config dir as a benign skip and create nothing
    (_headless_wire_statusline supplies that guard for the status line). In this
    entry point `with_statusline` is the host list main() resolved at command
    entry — bare form every host, `=<hosts>` the validated selection — so Claude
    is always wired before Cursor and an unknown/undetected name never reaches
    a write. --examples
    composes unchanged with the existing discover_example_segments/
    select_examples/install_example_segments primitives cmd_install already
    uses for its own --examples override.

    Exit code: 0 for success, the bare no-op, an unrecognized --skills NAME, or
    a host whose config dir doesn't exist (expected skip, not a failure). 1 when
    anything explicitly requested did not happen: a malformed/unreadable config
    file, an unsupported statusLine shape, a foreign statusLine headless mode
    cannot confirm, a write failure, a requested skill blocked by a foreign
    symlink or a real file, an OSError linking a requested skill, a failed or
    partial --examples install, or enumerate_entries raising OSError while
    resolving the checkout (the first statement below, before anything else
    runs; resolve_paths shares that boundary defensively but does no I/O).
    Every requested category is attempted even after an earlier one fails --
    a refused statusLine must not silently skip --with-hooks -- and the
    non-zero exit is reported once, at the end.

    Six arguments, one over pylint's max-args/max-positional-arguments: the
    localized disable above matches this file's existing practice for CLI-shaped
    entry points (render_preview, prune_stale, persist_statusline,
    launch_wizard). Body budget: 6 args + 8 locals (paths, entries, counts, ok,
    chosen, requested, replaced, only_invalid_skills) = 14 of 15 max-locals
    (`with_statusline` is re-normalized in place, never a second local);
    6 branches of 12; 3 returns of 6."""
    # The --with-global-rules parameter is one local over the budget note above.
    # pylint: disable=too-many-locals
    paths, entries = _headless_paths_and_entries(env)
    if paths is None:
        return 1
    counts = new_counts()
    # Headless installs prune dead ai-kit links (claude root, then pi root) before
    # linking; the wizard asks first.
    _headless_prune_roots(paths, entries, dry, counts)

    # Re-normalized in place (not a new local): main() already resolved
    # `--with-statusline=<hosts>` at command entry, so this is the host list to
    # wire; True only when a caller bypassed main() (same meaning as the bare
    # form), None when the flag was absent.
    with_statusline = _statusline_request(with_statusline)
    requested = (skills_flag is not None or with_statusline is not None
                 or with_hooks or examples_flag is not None)
    if requested:
        migrate_statusline(paths, dry)
    replaced =(_headless_replace(paths, entries, skills_flag, dry, counts)
                if replace_existing else set())
    ok, chosen = _headless_link_skills(skills_flag, entries, paths.claude_dir,
                                       dry, counts, replaced=frozenset(replaced or ()))
    ok = ok and replaced is not None
    # Only a run that named --skills links into the pi root; bare --headless and
    # hooks/statusline-only runs only prune its dead ai-kit links (above) and leave
    # every other pi link as it was.
    if chosen is not None and not _headless_sync_pi(paths, entries, dry,
                                                    counts, chosen,
                                                    replaced=frozenset(replaced or ())):
        ok = False
    if with_statusline is not None and not _headless_wire_statusline(
            paths, with_statusline, dry):
        ok = False
    if with_hooks is True:
        if not _headless_wire_default_hooks(paths, dry, counts):
            ok = False
    elif with_hooks and not _headless_wire_hook_ids(paths, with_hooks, dry, counts):
        ok = False
    if examples_flag is not None and not _headless_install_examples(
            paths, examples_flag, dry):
        ok = False
    if with_global_rules and not _headless_apply_global_rules(env, dry):
        ok = False

    only_invalid_skills = (skills_flag is not None and not chosen
                           and with_statusline is None and not with_hooks
                           and examples_flag is None)
    print(_headless_summary(requested, only_invalid_skills, counts))
    if dry:
        print("(dry-run — no changes were made)")
    if not ok:
        print("headless: one or more requested operations could not complete "
              "(see warnings above) — exiting non-zero", file=sys.stderr)
        return 1
    return 0


def cmd_uninstall(env, dry, hooks=None):
    """Remove every ai-kit symlink under ~/.claude, ai-kit's own statusLine on EACH
    status-line host (Claude's settings.json first, then Cursor's cli-config.json —
    only when that entry is ai-kit's), and ai-kit's own session-start hook entries
    from both Claude Code and Cursor. Foreign hook entries and foreign statusLines
    are never touched, and one host's file is never modified while unwiring the
    other. Leaves install_dir, foreign links, and both config TOMLs in place.
    Exits 1 when a settings file could not be read or rewritten, so ai-kit may
    still be wired."""
    paths = resolve_paths(env)
    counts = new_counts()
    if hooks is None:
        installed = installed_links(paths.claude_dir, paths.install_dir)
        for cat in CATEGORIES:
            for name in sorted(installed[cat]):
                unlink_one(os.path.join(paths.claude_dir, cat, name), dry, counts)
        # The pi root holds skills only (D-14/D-17); foreign links and real dirs
        # are never touched (installed_links only reports ai-kit symlinks).
        if os.path.isdir(paths.pi_dir):
            pi_installed = installed_links(paths.pi_dir, paths.install_dir)
            for name in sorted(pi_installed["skills"]):
                unlink_one(os.path.join(paths.pi_dir, "skills", name), dry, counts)
        selected_rows = HOOK_REGISTRY
        hook_ok = unwire_hook_rows(paths, selected_rows, dry, counts)
        print(f"removed {counts['unlinked']} ai-kit symlink(s). "
              f"install dir left in place: {paths.install_dir}")
        # Per host and independent: an unparseable or foreign Cursor config
        # never stops Claude's entry from being removed, or the other way round.
        unwired = [unwire_statusline(paths.settings, paths.install_dir, dry),
                   unwire_statusline_cursor(paths.cursor_cli_config,
                                            paths.cursor_status_line, dry),
                   hook_ok]
    else:
        hook_ok = unwire_hook_rows(paths, hook_rows(hooks), dry, counts)
        print(f"removed hook entries for: {', '.join(dict.fromkeys(i for i, _h in hooks))}")
        unwired = [hook_ok]
    print(f"removed {counts['unlinked']} ai-kit symlink(s). "
          f"install dir left in place: {paths.install_dir}")
    if not all(unwired):
        print("uninstall: one or more settings files could not be updated "
              "(see warnings above) — exiting non-zero", file=sys.stderr)
        return 1
    return 0


def _doctor_cmd(paths):
    """A concrete, copy-pasteable doctor command for this install."""
    return (f"{os.path.basename(sys.executable) or 'python3'} "
            f"{paths.statusline_doctor} --doctor")


def cmd_doctor(env):
    """Delegate to statusline-doctor.py --doctor (E5a); return its exit code. Run
    under THIS interpreter (not a bare 'python3' PATH lookup) so the doctor validates
    with the same Python the wizard writes/validates the config with."""
    paths = resolve_paths(env)
    return subprocess.call([sys.executable, "-S", paths.statusline_doctor, "--doctor"])


def cmd_check(env):
    """Delegate to statusline-doctor.py --check (E5a); return its exit code."""
    paths = resolve_paths(env)
    return subprocess.call([sys.executable, "-S", paths.statusline_doctor, "--check"])


def cmd_config_doctor(env, tty, dry):
    """Launch the Config Doctor TUI.

    ``dry`` is accepted at this call site for symmetry with other cmd_*
    entry points; apply itself is driven per-row through the injected
    ``apply`` closure (``apply_row(..., dry=...)``), never by this flag.
    """
    isatty_fn = getattr(tty, "isatty", None)
    if tty is None or not callable(isatty_fn) or not isatty_fn():
        print(
            "error: cmd_config_doctor reached without a real terminal — this is a bug. "
            "require_tty() should have exited before this point.",
            file=sys.stderr,
        )
        sys.exit(2)

    ctx = _config_doctor_ctx(env)
    with stdin_on_tty():
        _sibling("config_doctor_app").run_config_doctor(ctx)
    return 0


def _config_doctor_ctx(env):
    """The Config Doctor's catalog and apply closure for this env, shared by
    `--config-doctor` and the wizard's `d` key (D-13). The catalog is built on
    each call; the apply closure runs `apply_row`, which goes through plan 01's
    guarded apply (it re-reads the target right before the replace)."""
    config_doctor_checks = _sibling("config_doctor_checks")
    catalog = config_doctor_checks.build_catalog(env)
    apply_ctx = config_doctor_checks.ReadContext(data=None, env=env, runner=None)

    def apply(row_id, dry):
        # TOCTOU: the closure itself does not re-read the file; the guarded apply
        # does, between backup and replace. Atomicity is with respect to the
        # value this closure itself computed.
        return config_doctor_checks.apply_row(row_id, apply_ctx, dry)

    return _sibling("config_doctor_app").ConfigDoctorContext(catalog=catalog, apply=apply)


def _as_dry_run(ctx):
    """The doctor context with every apply forced to a preview whose result says so:
    a dry applier still reports the target as ``current_display``, and the doctor
    would otherwise show that unwritten value as the machine's current state."""
    base = ctx.apply

    def dry_apply(row_id, _dry):
        res = base(row_id, True)
        if isinstance(res, dict) and res.get("ok"):
            shown = res.get("current_display", res.get("after"))
            if shown is not None:
                res = {**res, "current_display": f"{shown} (dry run, not written)"}
        return res
    return ctx._replace(apply=dry_apply)


def _make_doctor_factory(env, dry=False):
    """The factory the wizard calls on `d`: a fresh ConfigDoctorScreen per call
    (D-13). With `dry` (an install --dry-run) every confirmed apply is a preview
    and the exit hint says so, so the dry run writes nothing."""
    def factory():
        ctx = _config_doctor_ctx(env)
        hint = "Esc returns to Done."
        if dry:
            ctx = _as_dry_run(ctx)
            hint ="Esc returns to Done. Dry run: applies are previews; nothing is written."
        return _sibling("config_doctor_app").ConfigDoctorScreen(ctx, exit_hint=hint)
    return factory


# ---------------------------------------------------------------------------
# uv bootstrap — ensure textual (and the whole rich runtime) is available
# before any wizard UI code runs.  The status-line RENDER path must never
# call these (it stays stdlib-only).
# ---------------------------------------------------------------------------

def _textual_importable():
    """True when `textual` can be imported in THIS interpreter."""
    return importlib.util.find_spec("textual") is not None


def _under_uv(env):
    return env.get("AI_KIT_UV_REEXEC") == "1"


def _have_uv():
    """Path to the uv binary, or None. Checks PATH then ~/.local/bin (astral default)."""
    cand = shutil.which("uv")
    if cand:
        return cand
    fallback = os.path.expanduser("~/.local/bin/uv")
    return fallback if os.path.exists(fallback) else None


def _install_uv(tty):
    """Install uv via the official astral installer, after showing the exact
    command and getting consent. Returns True on success, False on decline,
    cancel (Ctrl-C), or failure.

    SECURITY: `shell=True` is required because the official installer is a
    `download | sh` PIPE (two processes joined by the shell). It is safe by
    construction: `cmd` is one of two FIXED string literals below — no user
    input, no f-string interpolation of external data is ever spliced into it,
    so there is no command-injection surface. Do NOT refactor `cmd` to include
    any caller-supplied value; if that ever changes, this must stop using a
    shell. The exact command is printed and consented to before running."""
    if shutil.which("curl"):
        cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"
    elif shutil.which("wget"):
        cmd = "wget -qO- https://astral.sh/uv/install.sh | sh"
    else:
        print("setup: uv install needs curl or wget; neither found.", file=sys.stderr)
        return False
    try:
        _tty_write(tty, f"\n  uv is required for the wizard. Install it now with:\n    {cmd}\n")
        if not ask_yes_no(tty, "  run this?", default=True):
            return False
        # cmd is a constant literal (see SECURITY note) — shell is the pipe runner.
        return subprocess.run(cmd, shell=True, check=False).returncode == 0
    except KeyboardInterrupt:
        return False
    except OSError:
        return False


def _reexec_under_uv(uv_path):
    """Re-exec this script under `uv run` so the PEP-723 deps resolve. Sets the
    loop-guard marker first. Normally never returns; on OSError prints a clear
    stderr reason and exits 3."""
    env = dict(os.environ, AI_KIT_UV_REEXEC="1")
    script = os.path.abspath(__file__)
    try:
        os.execve(uv_path, [uv_path, "run", "--script", script, *sys.argv[1:]], env)
    except OSError as exc:
        print(f"setup: failed to exec uv at {uv_path!r}: {exc}", file=sys.stderr)
        sys.exit(3)


def ensure_rich_runtime(env):
    """Guarantee textual is importable, or fail closed. Re-exec under uv at most
    once (env marker guards the loop)."""
    if _textual_importable():
        return
    if _under_uv(env):                       # already re-exec'd, still missing → stop
        print("setup: textual is unavailable under uv — cannot launch the wizard.",
              file=sys.stderr)
        sys.exit(3)
    uv_path = _have_uv()
    if uv_path is None:
        tty = open_tty()
        if tty is None:
            print(
                "setup: uv is required for the wizard and no terminal is available"
                " to confirm installing it.",
                file=sys.stderr,
            )
            sys.exit(3)
        if not _install_uv(tty):
            print("setup: uv is required for the wizard and was not installed.",
                  file=sys.stderr)
            sys.exit(3)
        # Re-resolve after install; uv may now be at ~/.local/bin/uv.
        uv_path = _have_uv()
        if uv_path is None:
            print("setup: uv install reported success but binary not found.",
                  file=sys.stderr)
            sys.exit(3)
    _reexec_under_uv(uv_path)               # normally never returns


def _refuses_real_home(env):
    """Unattended-executor guard: with AI_KIT_REFUSE_REAL_HOME=1 a run whose HOME is the
    account's real home writes nothing (a cross-AI executor once ran a real install from a
    worktree, 2026-10-24). Scratch-HOME tests and the owner's own runs are unaffected."""
    if env.get("AI_KIT_REFUSE_REAL_HOME") != "1":
        return False
    import pwd  # pylint: disable=import-outside-toplevel
    try:
        real = pwd.getpwuid(os.getuid()).pw_dir
    except (KeyError, OSError):
        return True  # cannot tell: refuse, the guard exists to fail closed
    home = env.get("HOME") or real
    return os.path.realpath(home) == os.path.realpath(real)


def main(argv=None):  # pylint: disable=too-many-return-statements,too-many-branches,too-many-statements
    """Parse the subcommand and dispatch. Default subcommand is install."""
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="setup.py", add_help=True)
    parser.add_argument(
        "subcommand",
        nargs="?",
        default="install",
        choices=["install", "reconfigure", "uninstall", "doctor", "check"],
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--examples", default=None, metavar="all|none|<ids>",
        help="example external segments to install (non-interactive); "
             "comma/space-separated ids, or all/none. Default: offer pre-checked.")
    parser.add_argument(
        "--config-doctor",
        action="store_true",
        help="launch the config diagnostics TUI (per-item apply, explicit confirm)",
    )
    parser.add_argument("--headless", action="store_true",
                         help="non-interactive install/reconfigure: no wizard, "
                              "no tty required. "
                              "Bare form only prunes dead ai-kit links and links/wires nothing; "
                              "combine with --skills/--with-statusline/--with-hooks/"
                              "--examples.")
    parser.add_argument("--skills", default=None, metavar="all|name1,name2",
                         help="(--headless only) skills to link additively — "
                              "never unlinks anything not named.")
    parser.add_argument("--with-statusline", nargs="?", const=True, default=False,
                        metavar="<claude,cursor>",
                        help="(--headless only) bare wires every detected host, "
                             "Claude before Cursor; =<claude,cursor> wires exactly "
                             "those hosts (unknown name: usage error, valid but not "
                             "installed: error before any write).")
    parser.add_argument("--with-hooks", nargs="?", const=True, default=False,
                        metavar="<id[:host],...>",
                        help="(--headless only) bare wires rows marked on below; "
                             "=<id[:host],...> wires exactly those rows additively: "
                             + "; ".join(hook_description(i) for i in HOOK_IDS))
    parser.add_argument("--with-global-rules", action="store_true",
                        help="(--headless only) rewrite codegraph's \"user decides\" sentence "
                             "in the global instruction files (backup first; --dry-run previews)")
    parser.add_argument("--hooks", default=None, metavar="<id[:host],...>",
                        help="(uninstall only) remove only these hooks")
    parser.add_argument(
        "--replace-existing", action="store_true",
        help="(--headless --skills only) move a real dir or foreign symlink "
             "standing at a named skill's link path into "
             "${XDG_STATE_HOME:-~/.local/state}/ai-kit/backups/<root>/ before "
             "linking the repo copy.")
    args = parser.parse_args(argv)
    if (args.skills is not None or args.with_statusline
            or args.with_hooks is not False or args.with_global_rules) and not args.headless:
        parser.error("--skills/--with-statusline/--with-hooks/--with-global-rules "
                     "require --headless")
    if isinstance(args.with_hooks, str):
        tokens = [t for t in re.split(r"[,\s]+", args.with_hooks.strip()) if t]
        if not tokens:
            print("warn: --with-hooks= named no hook id; nothing wired",
                  file=sys.stderr)
            args.with_hooks = []
        else:
            try:
                args.with_hooks = parse_hook_selector(args.with_hooks)
            except ValueError as exc:
                parser.error(f"--with-hooks: unknown hook {str(exc)!r} "
                             f"(known: {', '.join(HOOK_IDS)})")
    if args.hooks is not None:
        if args.subcommand != "uninstall":
            parser.error("--hooks is only valid with uninstall")
        tokens = [t for t in re.split(r"[,\s]+", args.hooks.strip()) if t]
        if not tokens:
            print("warn: --hooks= named no hook id; nothing removed", file=sys.stderr)
            args.hooks = []
        else:
            try:
                args.hooks = parse_hook_selector(args.hooks)
            except ValueError as exc:
                parser.error(f"--hooks: unknown hook {str(exc)!r} "
                             f"(known: {', '.join(HOOK_IDS)})")
    if args.replace_existing and not (args.headless and args.skills is not None):
        parser.error("--replace-existing requires --headless and --skills")
    if args.headless and args.subcommand not in ("install", "reconfigure"):
        parser.error("--headless is only valid with the install/reconfigure subcommands")
    if args.headless and args.config_doctor:
        parser.error("--headless and --config-doctor cannot be combined")
    env = os.environ
    if not env.get("HOME", ""):
        print("error: HOME is unset or empty; set HOME to your home directory", file=sys.stderr)
        return 2
    if args.with_statusline is not False:
        # Host selection is validated at command entry: nothing — no migration,
        # no replacement, no link, no hook, no example, no config write — has
        # happened yet, so an unknown or undetected host cannot leave a partial
        # install behind (SPEC R11/D-23).
        detected = statusline_hosts_detected(resolve_paths(env))
        try:
            args.with_statusline = _statusline_selection(args.with_statusline, detected)
        except UndetectedStatuslineHost as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        except ValueError as exc:
            parser.error(str(exc))
    dry = args.dry_run
    if not dry and _refuses_real_home(env):
        print("error: AI_KIT_REFUSE_REAL_HOME is set and HOME is the real user home; refusing "
              "to write (use a scratch HOME, or --dry-run)", file=sys.stderr)
        return 2
    if args.config_doctor:
        ensure_rich_runtime(env)
        tty = cast("_StdTty", require_tty(open_tty()))
        try:
            return cmd_config_doctor(env, tty, dry)
        finally:
            tty.close()
    if args.subcommand in ("install", "reconfigure"):
        if args.headless:
            return cmd_install_headless(
                env, dry, args.skills, args.with_statusline, args.with_hooks,
                examples_flag=args.examples,
                replace_existing=args.replace_existing,
                with_global_rules=args.with_global_rules)
        ensure_rich_runtime(env)              # may re-exec; must be BEFORE open_tty
        tty = cast("_StdTty", require_tty(open_tty()))  # fail-closed (FR-W.1/B)
        try:
            return cmd_install(env, tty, dry,
                               examples_flag=args.examples)
        finally:
            tty.close()
    if args.subcommand == "uninstall":
        return cmd_uninstall(env, dry, hooks=args.hooks)
    if args.subcommand == "doctor":
        return cmd_doctor(env)
    if args.subcommand == "check":
        return cmd_check(env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
