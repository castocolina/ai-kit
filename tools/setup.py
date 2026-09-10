#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["textual>=0.60"]
# ///
# ^ Consumed by `uv run tools/setup.py` to resolve textual into an ephemeral env
#   for the wizard ONLY. Plain `python3 tools/setup.py` ignores this comment; the
#   status-line render path never uses uv/textual (see plan Global Constraints).
"""ai-kit setup wizard + install engine (stdlib-only, like status-line.py).

Invoked by tools/install.sh after it has guaranteed the repo and python3 are on
disk. Subcommands: install (default), reconfigure, uninstall, doctor, check.
Flags: --dry-run.

Env overrides (mirrors install.sh):
  AI_KIT_DIR        install location (default: ${XDG_DATA_HOME:-~/.local/share}/ai-kit)
  CLAUDE_CONFIG_DIR Claude config dir (default: ~/.claude)
  CURSOR_CONFIG_DIR Cursor config dir (default: ~/.cursor)
  XDG_CONFIG_HOME   config base       (default: ~/.config)
"""

import argparse
import contextlib
import copy
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
import tomllib
from collections import namedtuple
from typing import cast

CATEGORIES = ("agents", "commands", "skills")

Paths = namedtuple(
    "Paths",
    "install_dir claude_dir settings config_dir config_toml sample status_line "
    "statusline_doctor segments_dir claude_hook cursor_dir cursor_hooks cursor_hook",
)


def resolve_paths(env):
    """Resolve every path the installer touches, mirroring install.sh's env
    precedence: AI_KIT_DIR > XDG_DATA_HOME/ai-kit; CLAUDE_CONFIG_DIR > ~/.claude;
    CURSOR_CONFIG_DIR > ~/.cursor; XDG_CONFIG_HOME/ai-kit > ~/.config/ai-kit."""
    home = env.get("HOME", "")
    install_dir = env.get("AI_KIT_DIR") or os.path.join(
        env.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share"), "ai-kit"
    )
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    cursor_dir = env.get("CURSOR_CONFIG_DIR") or os.path.join(home, ".cursor")
    config_base = env.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    config_dir = os.path.join(config_base, "ai-kit")
    return Paths(
        install_dir=install_dir,
        claude_dir=claude_dir,
        settings=os.path.join(claude_dir, "settings.json"),
        config_dir=config_dir,
        config_toml=os.path.join(config_dir, "statusline.toml"),
        sample=os.path.join(install_dir, "tools", "statusline.toml.sample"),
        status_line=os.path.join(install_dir, "tools", "status-line.py"),
        statusline_doctor=os.path.join(install_dir, "tools", "statusline-doctor.py"),
        segments_dir=os.path.join(config_dir, "segments"),
        claude_hook=os.path.join(
            install_dir, "tools", "hooks", "claude_session_start.py"),
        cursor_dir=cursor_dir,
        cursor_hooks=os.path.join(cursor_dir, "hooks.json"),
        cursor_hook=os.path.join(
            install_dir, "tools", "hooks", "cursor_session_start.py"),
    )


# ── Status-line config defaults (mirrors status-line.py SEGMENTS/LAYOUT) ───────
# Duplicated here, not imported: status-line.py's hyphenated filename isn't an
# importable module, and the wizard must run even while the renderer is mid-edit.
# TestTomlRead.test_segment_defaults_match_recipe_drift pins these to the recipe.
SEGMENT_DEFAULTS = {
    "path": True, "git_branch": True, "git_dirty": True, "alt_git_worktree": False,
    "model": True, "effort": True, "context": True, "todo": True,
    "alt_time_ago": False, "alt_time_clock": False,
    "alt_cost": False, "alt_time_session": False, "alt_time_api": False,
    "render_time": True, "slowest": True, "alt_term_dimensions": False,
    "lines": False,
    "chat_size": True, "alt_process_memory": False,
    "alt_h_rate_limit": False, "alt_w_rate_limit": False,
}
LAYOUT_DEFAULTS = [
    {"min_rows": 0,
     "segments": ["path", "git_branch", "alt_git_worktree", "git_dirty"]},
    {"min_rows": 20, "segments": ["model", "effort", "context", "todo"]},
    {"min_rows": 30, "segments": ["render_time", "slowest", "alt_term_dimensions",
                                  "alt_time_ago", "alt_time_clock", "lines",
                                  "alt_cost", "alt_time_session", "alt_time_api",
                                  "chat_size", "alt_process_memory",
                                  "alt_h_rate_limit", "alt_w_rate_limit"]},
]

# Fallback UI glyph for an external segment whose header omits `icon=`.
DEFAULT_SEGMENT_ICON = "●"

# Absolute path to the shipped built-in segment UI inventory.
INVENTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "segments_inventory.toml")


def load_segment_inventory(path):
    """Load the built-in segment UI inventory (description/sample/icon/line) keyed
    by segment name. Installer/wizard-only metadata; never read by the render path.
    Returns {key: {"description": str, "sample": str, "icon": str, "line": int}}.
    A missing/malformed file yields {} (fail-closed coverage is asserted by the
    arch test, not here)."""
    data = read_toml(path)
    inv = {}
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        inv[key] = {
            "description": str(val.get("description", "")),
            "sample": str(val.get("sample", "")),
            "icon": str(val.get("icon", "")),
            "line": int(val.get("line", 0)),
        }
    return inv


def build_segment_meta(inventory, overrides):
    """Merge the built-in inventory (description/sample/icon/line) with per-key
    icon+line overrides from the user's statusline.toml. `overrides` is
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


def _statusline_icon_line_overrides(config_toml):
    """Read per-segment icon+line overrides from the user's statusline.toml, if
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
    """Whether the user's statusline.toml enables external segment `ext_id`.

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


def current_segments(path):
    """Resolved {key: bool}: SEGMENT_DEFAULTS merged with the file's [segments].
    Unknown keys and non-bool values in the file are ignored (defaults win), the
    same lenient policy the renderer applies."""
    seg = dict(SEGMENT_DEFAULTS)
    for k, v in (read_toml(path).get("segments") or {}).items():
        if k in seg and isinstance(v, bool):
            seg[k] = v
    return seg


def current_layout(path):
    """Resolved layout as a list of {"min_rows": int, "segments": [str]} dicts.
    Any [[line]] block in the file REPLACES the whole layout (all-or-nothing,
    matching the renderer); otherwise the default 3-row layout (deep-copied)."""
    raw = read_toml(path).get("line")
    if not raw:
        return [{"min_rows": r["min_rows"], "segments": list(r["segments"])}
                for r in LAYOUT_DEFAULTS]
    return [{"min_rows": int(item.get("min_rows", 0)),
             "segments": list(item.get("segments", []))} for item in raw]


def _bool_env(value):
    return "1" if value else "0"


def render_preview(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    status_line, segments, sample_json, env, layout=None, base_config=None,
):
    """Render the status line with the given segment toggles, for the live preview.

    Shells out to `python3 status-line.py` feeding `sample_json` on stdin and the
    toggles as CC_AI_KIT_SEGMENT_<KEY> env overrides (so it reflects in-memory
    edits before they are written). `env` carries only the keys to override
    (e.g. forced terminal size); it is merged ON TOP OF os.environ so the
    subprocess inherits PATH, HOME, and PYTHONPATH.

    When `layout` is provided (list of {"min_rows": int, "segments": [str]} dicts),
    a throwaway temp config is written with the patched layout and the subprocess
    reads it via CC_AI_KIT_CONFIG_FILE.  The temp file is deleted in a try/finally
    so it is never leaked, even on error.

    Returns the rendered text ("" on any failure — the preview is best-effort
    and must never crash the wizard)."""
    child = {**os.environ, **env}   # inherit full env; overrides layer on top
    # Force a wide, tall terminal so all rows/segments render in the preview
    # regardless of the wizard's own window size.
    child.setdefault("STATUSLINE_COLS", "200")
    child.setdefault("STATUSLINE_LINES", "40")
    for key, on in segments.items():
        child[f"CC_AI_KIT_SEGMENT_{key.upper()}"] = _bool_env(on)
    tmp_path = None
    try:
        if layout is not None:
            patched = patch_layout(base_config or "", layout)
            fd, tmp_path = tempfile.mkstemp(suffix=".toml", prefix="ai_kit_preview_")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(patched)
            except OSError:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
                return ""
            child["CC_AI_KIT_CONFIG_FILE"] = tmp_path
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


# One-line doc notes carried when a managed key is appended (keeps the recipe
# self-documenting). Lifted verbatim from tools/statusline.toml.sample comments.
_SEGMENT_NOTES = {
    "path": "📂 working directory, ~-relative   (pinned)",
    "git_branch": "git branch name",
    "git_dirty": "working-tree dirty marker",
    "alt_git_worktree": "⎇ active linked-worktree name",
    "todo": "📝 current TODO  (📝 in-progress / ⏸ pending)",
    "model": "active model name (e.g. Opus)",
    "alt_time_ago": "time since the session's first message",
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


def write_toml_preserving(path, text, statusline_doctor):
    """Atomically write `text` to `path`, then self-validate via the doctor.

    Writes to a sibling temp file and os.replace()s it into place (atomic). Then
    runs `statusline-doctor.py --doctor` against the result
    (CC_AI_KIT_CONFIG_FILE=path); if the doctor reports problems, the previous file
    content is restored and False is returned — the wizard must never leave a broken
    config (§5.1). Returns True on success."""
    prev = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            prev = f.read()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        return False
    env = dict(os.environ)
    env["CC_AI_KIT_CONFIG_FILE"] = path
    reason = ""
    try:
        proc = subprocess.run([sys.executable, "-S", statusline_doctor, "--doctor"],
                              capture_output=True, text=True, env=env, timeout=10,
                              check=False)
        ok = proc.returncode == 0
        if not ok:
            reason = ((proc.stdout or "") + (proc.stderr or "")).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        ok = False
        reason = str(exc)
    if not ok:
        if reason:
            # Surface WHY the doctor rejected it — a swallowed reason left the
            # user (and the install summary) with no clue what to fix.
            print("doctor rejected the status-line config:", file=sys.stderr)
            for line in reason.splitlines():
                print(f"  {line}", file=sys.stderr)
        if prev is None:
            os.unlink(path)
        else:
            # Restore the prior (already-valid) content atomically too, so an
            # interrupted revert can't leave a truncated config behind.
            rfd, rtmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".",
                                         suffix=".tmp")
            try:
                with os.fdopen(rfd, "w", encoding="utf-8") as f:
                    f.write(prev)
                os.replace(rtmp, path)
            except OSError:
                if os.path.exists(rtmp):
                    os.unlink(rtmp)
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


# Mirror status-line.py's canonical `_SEG_HEADER_RE` EXACTLY (whitespace-flexible
# after `#` and after the colon; NO leading indent — the marker sits at column 0)
# so the installer and the renderer never disagree on which files are providers
# (the two files can't import each other — hyphenated filename, see L64 — so the
# pattern is duplicated; keep it byte-identical to status-line.py's).
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
    the renderer's parser (`core_parse_segment_header` in status-line.py) does
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
        line = int(fields["line"]) if "line" in fields else len(LAYOUT_DEFAULTS) - 1
    except (TypeError, ValueError):
        line = len(LAYOUT_DEFAULTS) - 1
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


def discover_external_segments(paths, examples_dir):
    """Merge bundled (examples/segments/) and user (paths.segments_dir) external
    segments. Each entry carries {id, filename, name, path, default_on,
    description, icon, sample, line, provenance} where provenance is
    "bundled" | "user". On an id collision the USER entry wins (it shadows
    the bundled copy the user customized). All entries default OFF in the wizard
    unless statusline.toml enables them. `filename` is preserved from the
    winning entry and drives the install-destination in install_example_segments.
    Returned list is id-sorted."""
    merged = {}
    for e in discover_example_segments(examples_dir):
        merged[e["id"]] = e
    for e in _discover_user_segments(paths.segments_dir):
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


def install_example_segments(examples, config_dir, seg_state=None):
    """Install each chosen example external segment: copy it into the XDG-aware
    segments dir (`config_dir/segments` — `config_dir` comes from resolve_paths,
    so XDG_CONFIG_HOME is already honored), make it executable, and enable its
    `segments.<id>` toggle (set `seg_state[id] = True` when a state dict is
    given). Idempotent: a destination already holding the same bytes is left
    untouched and a re-run never duplicates (one fixed dest path per name); a
    stale copy is refreshed to the source bytes via an atomic temp-file replace.
    A provider whose source can't be read or whose destination is bad/blocked
    (name already a directory, unwritable dir) is SKIPPED with a warning rather
    than aborting the whole install. Returns the installed ids in input order."""
    seg_dir = os.path.join(config_dir, "segments")
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
    """True when path equals root or is nested under it (string test, mirrors
    install.sh is_inside on absolute paths)."""
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


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
                if _is_inside(target, install_dir):
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


def link_one(link_path, target, dry, counts):
    """Create or refresh one symlink, never clobbering a real file or a foreign
    symlink (port of install.sh link_one). 'foreign' = an existing symlink whose
    target is NOT inside the same install dir as `target`."""
    install_dir = _install_dir_of(link_path, target)
    if os.path.islink(link_path):
        cur = os.readlink(link_path)
        if cur == target:
            return
        if _is_inside(cur, install_dir):
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
    """Remove one ai-kit symlink (caller has already confirmed ownership)."""
    counts["unlinked"] += 1
    if not dry and os.path.lexists(link_path):
        os.remove(link_path)


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
    else:
        for item in stale:
            print(f"warn: removing dead ai-kit link {item} (entry removed upstream)",
                  file=sys.stderr)
    apply_stale_prune(claude_dir, stale, dry, counts)
    return stale


def predecessor_candidates(claude_dir, install_dir, entries):
    """List (cat, name, old_target, new_target) for links left by a PREVIOUS
    ai-kit install (e.g. a renamed repo uz-kit -> ai-kit). A candidate is a
    symlink at <claude>/<cat>/<name> that is foreign to the CURRENT install_dir
    yet carries the ai-kit <root>/<cat>/<name> shape (target basename == name,
    its parent dir name == cat) AND whose <name> is a current repo entry, so it
    can be re-pointed. Unrelated foreign symlinks (different shape, or no current
    entry) are excluded — we never touch a link that isn't recognizably ours."""
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
            if _is_inside(old, install_dir):
                continue                       # already a current ai-kit link
            if os.path.basename(old) != name:
                continue                       # not the ai-kit <cat>/<name> shape
            if os.path.basename(os.path.dirname(old)) != cat:
                continue
            if name not in by_name:
                continue                       # nothing current to re-point to
            out.append((cat, name, old, by_name[name]))
    return out


def apply_predecessor_links(claude_dir, cands, repoint, dry, counts):
    """Apply the repoint/delete decision for each predecessor-link candidate
    (mutating). `cands` is predecessor_candidates()'s output:
    (cat, name, old, new_target)."""
    for cat, name, _old, new_target in cands:
        link = os.path.join(claude_dir, cat, name)
        if not dry:
            if os.path.lexists(link):
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


def _read_json(path):
    """Load a JSON object, or {} on any error / non-dict (mirrors install.sh)."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path, data):
    """Write JSON with a 2-space indent + trailing newline, creating parents."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


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


def _read_json_checked(path):
    """Three-state JSON reader: absent / ok-dict / unreadable.

    Distinct from `_read_json`, which collapses all three into `{}`. Treating
    that `{}` as "fresh file, safe to create" would replace an existing but
    unparseable settings.json with a brand-new file containing only ai-kit's
    entry — the corruption PROJECT.md's core value forbids.
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

    Adapted from skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py
    rather than imported (a tools/ module importing a skills/ package would be a
    layering violation). Fresh files get mode 0o600 — the mode both hosts' own
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


def _refresh_or_append_claude_hook(entries, command):
    """Replace an existing ai-kit SessionStart entry in place, or append one."""
    new_entry = {
        "matcher": CLAUDE_HOOK_MATCHER,
        "hooks": [{"type": "command", "command": command}],
    }
    for index, entry in enumerate(entries):
        for hook in entry.get("hooks") or []:
            if CLAUDE_HOOK_MARKER in hook.get("command", ""):
                entries[index] = new_entry
                return True
    entries.append(new_entry)
    return False


def wire_hook_claude(settings, hook_script, dry):
    """Append-if-absent Claude Code SessionStart entry for the briefing wrapper.

    Never materializes ~/.claude/settings.json when the parent directory does
    not exist. Never overwrites a config it cannot fully interpret. Writes
    through `_atomic_write_json`; an OSError leaves the target byte-identical
    and returns False rather than aborting a wizard commit.
    """
    if not os.path.isdir(os.path.dirname(settings) or "."):
        print("skipped Claude Code SessionStart hook — no claude dir")
        return False
    ok, data, _ = _load_hook_config(
        settings, CLAUDE_HOOK_EVENT, nested=True)
    if not ok:
        return False
    assert data is not None  # ok True <=> data is a dict, see _load_hook_config
    hooks = data.setdefault("hooks", {})
    entries = hooks.setdefault(CLAUDE_HOOK_EVENT, [])
    command = "python3 -S " + hook_script
    _refresh_or_append_claude_hook(entries, command)
    if dry:
        print(f"would wire SessionStart hook -> {command}")
        return True
    try:
        _atomic_write_json(settings, data)
    except OSError as exc:
        print(f"warn: failed to write {settings}: {exc}", file=sys.stderr)
        return False
    print(f"wired SessionStart hook -> {command}")
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
    command = "python3 -S " + hook_script
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


def wire_statusline(settings, status_line, tty, dry, assume_overwrite=False):
    """Point settings.json's statusLine.command at the bundled status-line.py
    (with `python3 -S`), preserving all other keys. FR-5.5 double-confirm:
      - absent / already ai-kit  → set/refresh silently
      - a DIFFERENT command      → show it and require an explicit 'y'; on a
                                   headless run (no tty) refuse and leave it.
    ``assume_overwrite`` short-circuits the foreign-command guard: the caller
    (the in-UI adoption gate) already asked the user "replace it with ai-kit?"
    and got a yes, so re-prompting on the terminal would be a redundant second
    question. Returns True when statusLine now points at ai-kit, False when
    left untouched."""
    desired = "python3 -S " + status_line
    data = _read_json(settings)
    cur = data.get("statusLine")
    cur_cmd = cur.get("command", "") if isinstance(cur, dict) else ""
    if cur_cmd and status_line not in cur_cmd and not assume_overwrite:
        # a foreign status line — guard it
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
    _write_json(settings, data)
    return True


def detect_statusline(paths):
    """Read-only: classify settings.json's statusLine for the adoption gate.

    Returns {"state": "unset"|"ours"|"foreign", "current_command": str|None}.
      - "ours"    iff the command invokes the resolved paths.status_line
                  (XDG-aware substring match — NOT a hard-coded string).
      - "foreign" iff a statusLine is configured but does not reference our script.
      - "unset"   iff absent, empty, or file is missing/malformed.

    statusLine may be a bare string or an object with a "command" key (both
    shapes are supported by Claude Code).  Writes nothing."""
    data = _read_json(paths.settings)
    cur = data.get("statusLine")
    if isinstance(cur, dict):
        cur_cmd = cur.get("command", "")
    elif isinstance(cur, str):
        cur_cmd = cur
    else:
        cur_cmd = ""
    if not cur_cmd:
        return {"state": "unset", "current_command": None}
    if paths.status_line in cur_cmd:
        return {"state": "ours", "current_command": cur_cmd}
    return {"state": "foreign", "current_command": cur_cmd}


def copy_recipe_if_absent(sample, config_toml, dry):
    """Copy the recipe to config_toml ONLY if absent (E4a behavior). On a re-run
    it is never overwritten — the TOML is the user's persisted status-line config."""
    if not os.path.isfile(sample):
        return
    if os.path.isfile(config_toml):
        return
    if dry:
        print(f"would copy {sample} -> {config_toml}")
        return
    os.makedirs(os.path.dirname(config_toml), exist_ok=True)
    with open(sample, encoding="utf-8") as src, \
         open(config_toml, "w", encoding="utf-8") as dst:
        dst.write(src.read())


def unwire_statusline(settings, install_dir, dry):
    """Uninstall: remove the statusLine ONLY if it points into install_dir (never
    clobber a foreign one). Preserves all other settings keys."""
    data = _read_json(settings)
    cur = data.get("statusLine")
    cur_cmd = cur.get("command", "") if isinstance(cur, dict) else ""
    if not (cur_cmd and _is_inside_str(install_dir, cur_cmd)):
        return
    if dry:
        print("would clear ai-kit statusLine")
        return
    data.pop("statusLine", None)
    _write_json(settings, data)


def _entry_is_ours_nested(entry, marker):
    """True when any nested command string contains `marker`."""
    return any(marker in hook.get("command", "") for hook in entry.get("hooks") or [])


def _commit_unwire(path, data, dry, would_msg):
    """Honour dry, then atomically rewrite `path`. Never raises."""
    if dry:
        print(would_msg)
        return
    try:
        _atomic_write_json(path, data)
    except OSError as exc:
        print(f"warn: failed to write {path}: {exc}", file=sys.stderr)


def unwire_hook_claude(settings, dry):
    """Remove ai-kit's own SessionStart entry; leave every foreign entry."""
    ok, data, _ = _load_hook_config(settings, CLAUDE_HOOK_EVENT, nested=True)
    if not ok:
        return
    assert data is not None  # ok True <=> data is a dict, see _load_hook_config
    hooks = data.get("hooks") or {}
    if CLAUDE_HOOK_EVENT not in hooks:
        return
    entries = hooks[CLAUDE_HOOK_EVENT]
    kept = [e for e in entries if not _entry_is_ours_nested(e, CLAUDE_HOOK_MARKER)]
    if kept == entries:
        return
    hooks[CLAUDE_HOOK_EVENT] = kept
    _commit_unwire(settings, data, dry, "would remove ai-kit SessionStart hook")


def unwire_hook_cursor(cursor_hooks, dry):
    """Remove ai-kit's own sessionStart entry; leave every foreign entry."""
    parent = os.path.dirname(cursor_hooks) or "."
    if not os.path.isdir(parent) or not os.path.isfile(cursor_hooks):
        return
    ok, data, _ = _load_hook_config(cursor_hooks, CURSOR_HOOK_EVENT)
    if not ok:
        return
    assert data is not None  # ok True <=> data is a dict, see _load_hook_config
    hooks = data.get("hooks") or {}
    if CURSOR_HOOK_EVENT not in hooks:
        return
    entries = hooks[CURSOR_HOOK_EVENT]
    kept = [
        e for e in entries
        if CURSOR_HOOK_MARKER not in e.get("command", "")
    ]
    if kept == entries:
        return
    hooks[CURSOR_HOOK_EVENT] = kept
    _commit_unwire(
        cursor_hooks, data, dry, "would remove ai-kit sessionStart hook")


def _is_inside_str(install_dir, command):
    """True when the install dir appears in the command string (the loose test
    install.sh uses for uninstall: `idir in str(command)`)."""
    return install_dir in command


def _segment_changes_vs_recipe(path, segments):
    """The {key: bool} subset of `segments` that DIFFERS from what `path` currently
    resolves to — the minimal set of segment keys to patch (key granularity).

    Only BUILT-IN segment keys (those present in the recipe) are considered:
    external/drop-in segments (e.g. ``system_memory``) are persisted as their own
    files, never as ``[segments]`` entries, and the doctor rejects an unknown key
    in that table. ``state["segments"]`` carries external on/off state for the
    examples installer, so it is filtered HERE rather than upstream."""
    current = current_segments(path)
    return {k: v for k, v in segments.items()
            if k in current and current.get(k) != v}


def save_statusline_config(path, seg_changes, layout, statusline_doctor):
    """Apply the managed edits to the file at `path` via surgical text patches,
    then atomically write + doctor-validate. `seg_changes` is the minimal changed
    {key: bool}; `layout` is None (unchanged) or the full list of line dicts.
    Returns True on success."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if seg_changes:
        text = patch_segments(text, seg_changes)
    if layout is not None:
        text = patch_layout(text, layout)
    return write_toml_preserving(path, text, statusline_doctor)


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




def _persist_layout(paths, state, dry, known_ext_ids=None):
    """Compute the minimal seg_changes + layout diff vs disk, then delegate to
    ``save_statusline_config`` for the atomic write + doctor validation + auto-
    revert (FR-W.5).  Returns True on success (including no-op and dry-run).

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
    if dry:
        print("[dry-run] would write status-line config — no changes made",
              file=sys.stderr)
        return True
    seg_changes = _segment_changes_vs_recipe(paths.config_toml, state["segments"])
    # External toggles: only providers PRESENT in the segments dir are known to the
    # doctor (it rejects unknown [segments] keys), so only those may be written.
    # A not-yet-installed bundled example is handled by install_example_segments
    # (it copies the file → the renderer shows it by default) — never written here.
    # Write an explicit `<id> = bool` only when the desired state differs from the
    # renderer default (present → ON), e.g. to hide a provider with `<id> = false`.
    if known_ext_ids is not None:
        ext_ids_for_write = known_ext_ids
    else:
        ext_ids_for_write = {e["id"] for e in _discover_user_segments(paths.segments_dir)}
    for ext_id in ext_ids_for_write:
        if ext_id not in state["segments"]:
            continue
        desired = bool(state["segments"][ext_id])
        if desired != _external_enabled_in_toml(paths.config_toml, ext_id, default_on=True):
            seg_changes[ext_id] = desired
    layout = state["layout"] if state["layout"] != current_layout(paths.config_toml) \
        else None
    if not (seg_changes or layout is not None):
        return True   # nothing to write — already up-to-date
    return save_statusline_config(paths.config_toml, seg_changes, layout,
                                  paths.statusline_doctor)


def _recover_incompatible_config(paths, dry):
    """If an existing statusline.toml is rejected by the doctor (e.g. it carries
    stale segment keys from a pre-rename ai-kit), back it up to ``<file>.bak`` and
    regenerate a fresh one from the recipe so the wizard's choices apply on a
    valid base. Returns True when a recovery happened.

    Uses the doctor's structural ``--check`` (not ``--doctor``) so an
    environment-specific render failure never triggers a reset — only an
    actually-incompatible file does."""
    cfg = paths.config_toml
    if not os.path.isfile(cfg) or not os.path.isfile(paths.sample):
        return False
    try:
        proc = subprocess.run(
            [sys.executable, "-S", paths.statusline_doctor, "--check", cfg],
            capture_output=True, text=True, timeout=10, check=False)
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
        shutil.copyfile(paths.sample, cfg)
    except OSError as exc:
        print(f"warn: could not reset incompatible config ({exc})", file=sys.stderr)
        return False
    print("note: your status-line config was incompatible with this ai-kit "
          "version and has been reset to defaults.\n"
          f"      your previous file is preserved at {bak}", file=sys.stderr)
    return True


def persist_statusline(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    paths, state, adopt, dry, tty=None, assume_overwrite=False, known_ext_ids=None,
):
    """Conditionally persist the status-line config + wire settings.json.

    adopt is False  -> NO-OP: write neither statusline.toml nor settings.json's
                       statusLine; an existing status line is left untouched.
    adopt is True   -> ensure the recipe exists (copy-if-absent), write
                       statusline.toml (doctor-validated, auto-revert) via
                       _persist_layout, then set settings.json statusLine to
                       `python3 -S <status_line>` UNLESS it already points at ours
                       (reconfigure leaves a correct, possibly hand-edited command
                       in place). Returns True on success.

    ``known_ext_ids`` is forwarded to ``_persist_layout`` unchanged — see its
    own docstring; ``None`` (the default) preserves the original live-disk-scan
    behavior for every caller that doesn't need the pre-install-snapshot fix.

    Component symlinking is the caller's concern and runs INDEPENDENTLY of this
    function (a components-only install never calls persist_statusline with adopt
    True, so no status-line file is read or written)."""
    if not adopt:
        return True
    # Adopting: the config TOML must exist before _persist_layout patches it.
    # copy-if-absent is gated here (NOT pre-wizard) so a non-adopting run never
    # materializes a statusline.toml (Task 10 constraint 1).
    copy_recipe_if_absent(paths.sample, paths.config_toml, dry)
    # An existing config from an incompatible (e.g. pre-rename) ai-kit would be
    # rejected by the doctor and block the whole persist; recover it first.
    _recover_incompatible_config(paths, dry)
    if not _persist_layout(paths, state, dry, known_ext_ids=known_ext_ids):
        return False
    if detect_statusline(paths)["state"] == "ours":
        return True
    # Propagate wire_statusline's return (Task 9 left it discarded): True when
    # statusLine now points at ai-kit, False when left untouched (declined /
    # headless-foreign). The config write already succeeded, so a declined wire
    # is not a hard failure — but the caller can see what happened.
    return wire_statusline(paths.settings, paths.status_line, tty, dry,
                           assume_overwrite=assume_overwrite)


def _sample_input_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "tests", "fixtures", "sample-input.json")


def _engine_ns(paths, sample_json):
    """Bundle the engine callables as a SimpleNamespace for injection into
    WizardContext.  wizard_app calls these at runtime; they all live here so
    wizard_app imports nothing from setup.py.

    ``sample_json`` is captured by the ``_render_preview`` closure so the
    render call is self-contained (no shared mutable state)."""
    # `types` is stdlib; the import is here (not top-level) because this helper
    # is only called from the wizard path (after uv re-exec), not from the
    # stdlib-only status-line render path.
    import types as _types  # pylint: disable=import-outside-toplevel

    def _render_preview(segments, layout=None):
        base_config = None
        if layout is not None:
            cfg = paths.config_toml if os.path.isfile(paths.config_toml) else paths.sample
            try:
                with open(cfg, encoding="utf-8") as fh:
                    base_config = fh.read()
            except OSError:
                base_config = ""
        return render_preview(paths.status_line, segments, sample_json, {},
                              layout=layout, base_config=base_config)

    return _types.SimpleNamespace(
        render_preview=_render_preview,
        apply_command=_apply_wizard_command,
        groups=_wizard_groups,
        order=_wizard_order,
        layout_move=layout_move,
        layout_toggle=layout_toggle,
        off_tray=off_tray,
    )


def _build_wizard_context(  # pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments
    paths, entries, installed, sample_json, wizard_app_mod, stale=None, predecessor_cands=None,
):
    """Construct WizardContext for launch_wizard (extracted for testability).

    ``wizard_app_mod`` is the already-imported wizard_app module, passed
    explicitly so tests can supply ``tools.wizard_app`` without module-identity
    issues (the bare ``import wizard_app`` in launch_wizard is a different object
    than ``from tools import wizard_app``).

    ``stale``/``predecessor_cands`` are launch_wizard's pre-computed detection
    results (Task 3): supplying them here only shapes ``ctx.housekeeping``'s
    display strings — defaulting to empty when omitted (existing callers that
    don't care about housekeeping keep working unmodified).

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

    sl_state = detect_statusline(paths)
    inventory = load_segment_inventory(INVENTORY_PATH)
    overrides = _statusline_icon_line_overrides(paths.config_toml)
    segment_meta = build_segment_meta(inventory, overrides)
    examples_dir = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "examples", "segments")
    external = discover_external_segments(paths, examples_dir)

    # Wizard segment state = built-in defaults/recipe, plus every discovered
    # external keyed by id. A discovered external's default mirrors the renderer:
    # provenance "user" means it lives in the segments dir and renders by default
    # (default ON, unless statusline.toml disables it); a "bundled" example is only
    # in examples/ and not yet installed, so it is an OFF offer until chosen.
    segments = current_segments(paths.config_toml)
    for e in external:
        on_by_default = e["provenance"] == "user"   # "user" = present in segments dir
        segments[e["id"]] = _external_enabled_in_toml(
            paths.config_toml, e["id"], default_on=on_by_default)

    component_meta = {
        name: _read_component_desc(abspath)
        for cat in CATEGORIES
        for name, abspath in entries[cat]
    }

    housekeeping = {
        "stale": stale,
        "predecessors": [f"{cat}/{name}" for cat, name, _old, _new in predecessor_cands],
    }

    return wizard_app_mod.WizardContext(
        selection=sel,
        state={"segments": segments,
               "layout": current_layout(paths.config_toml), "dirty": False,
               "adopt": sl_state["state"] == "ours",
               "_initial_enabled": initial_enabled},
        sample_json=sample_json,
        engine=_engine_ns(paths, sample_json),
        # Live callable, not a frozen dict — re-read fresh every time the
        # wizard's gate needs it, mirroring status-line.py's own re-probing.
        status_line=lambda: detect_statusline(paths),
        segment_meta=segment_meta,
        external_segments=external,
        component_meta=component_meta,
        housekeeping=housekeeping,
    )


def _make_wizard_commit(paths, entries, dry, counts, examples_flag=None):
    """Build the ``commit`` callable the wizard runs IN-UI on Review-confirm.

    It performs the real install — component symlinks, then (if the user adopted
    the status line at the gate) the doctor-validated config write + settings.json
    wiring — honoring the adopt decision already made in the UI (``assume_overwrite``
    so a foreign command isn't re-prompted on the terminal).

    ``examples_flag`` is the CLI ``--examples`` value (``None``/``"all"``/``"none"``/
    an id list), forwarded from ``cmd_install``. It is the AUTHORITATIVE desired
    state for every discovered bundled example when given (mirrors
    ``resolve_example_selection``'s own "flag wins" semantics), overriding the
    wizard's own toggle. ``None`` (no flag on the command line) falls back to the
    wizard's own ``state["segments"]`` toggle — see the in-body comment below for
    why this distinction is load-bearing.

    The callable is invoked from a Textual worker thread, so it must NOT print to
    stdout/stderr (that would corrupt the alternate screen). All diagnostics the
    inner functions emit (doctor rejection reason, incompatible-config reset note,
    …) are captured into the returned ``log`` string; the caller prints it AFTER
    the app exits. Returns an outcome dict the Done screen renders:
    ``{"ok": bool, "adopt": bool, "log": str}``."""
    def commit(selection, state):
        sel = cast(Selection, selection)
        adopt = bool(state.get("adopt"))
        buf = io.StringIO()
        ok = True
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            apply_selection(sel.category_sets(CATEGORIES), entries,
                            paths.claude_dir, dry, counts)
            wire_hook_claude(paths.settings, paths.claude_hook, dry)
            wire_hook_cursor(paths.cursor_hooks, paths.cursor_hook, dry)
            if adopt:
                # A discovered bundled example segment (e.g. system_memory) must
                # actually exist under paths.segments_dir before persist_statusline's
                # self-validating doctor call runs below — otherwise the doctor
                # rejects it as an unknown [[line]] segment, since cmd_install's own
                # example-segment install step (install_example_segments) would
                # otherwise only run AFTER the wizard returns. This applies
                # regardless of the segment's enabled/disabled toggle: the Arrange
                # board's state["layout"] places EVERY discovered segment somewhere
                # (a disabled one lands in the tray line, not omitted from the
                # layout array), and the doctor validates every id present anywhere
                # in [[line]] segments, not just the enabled ones — so filtering to
                # only toggled-on ids here would still leave a disabled-but-present
                # example unvalidatable.
                #
                # Snapshot which external ids were ALREADY on disk before this
                # install, then pass that snapshot as known_ext_ids to
                # persist_statusline: without it, _persist_layout would see the
                # example we're about to install as "already present" and write
                # an explicit `segments.<id> = false` for an off-by-default
                # example — masking it even for a caller (e.g. `--examples=all`,
                # applied later in cmd_install) that intends it visible. Passing
                # the pre-install snapshot preserves the original "not yet
                # installed -> no explicit boolean, renderer shows it by default"
                # outcome for a first-time install, while still letting the file
                # physically exist in time for the doctor's structural check.
                # install_example_segments is idempotent (skips unchanged
                # content) and does not itself enable a segment, so installing
                # every discovered example unconditionally here, and again,
                # redundantly, from cmd_install after the wizard returns, is
                # safe for the ON case — but the OFF case needs one more step:
                # a newly-installed example whose desired state is OFF must NOT
                # be left out of known_ext_ids, or _persist_layout's
                # boolean-toggle loop below can never see it and an explicit
                # `false` never gets written, so it renders ON by the same
                # present-on-disk default (tools/status-line.py:
                # seg_defaults.setdefault(id, True)) — silently overriding a
                # user who declined it in the Arrange board, or a fresh
                # `--examples=none` install. So: fold back in any
                # newly-installed id whose desired state is explicitly OFF,
                # forcing an explicit `false` write for it, while every
                # ON/untouched id keeps the original "not yet installed" -
                # renderer-default treatment.
                #
                # "Desired state" itself has two different sources depending
                # on how this install was driven, and getting this wrong
                # reintroduces the same bug from the other direction:
                #   - an explicit `--examples` flag on the command line
                #     (examples_flag is not None) is AUTHORITATIVE — it wins
                #     over the wizard's own toggles (cmd_install's post-wizard
                #     step already documents this "flag wins" contract), so
                #     `--examples=all` must render every discovered example
                #     ON even though the wizard's own default toggle for an
                #     un-installed bundled example starts OFF; `--examples=
                #     none`/an explicit id list must be honored exactly.
                #   - no flag ⇒ fall back to the wizard's own toggle
                #     (state["segments"]), so a user who never touches the
                #     Arrange board's example toggle (it defaults OFF for a
                #     not-yet-installed bundled example — see
                #     _build_wizard_context) gets the OFF outcome CR-01
                #     describes, and a user who explicitly turns it on gets ON.
                known_ext_ids = {e["id"] for e in _discover_user_segments(paths.segments_dir)}
                examples_dir = os.path.join(paths.install_dir, "examples", "segments")
                examples = discover_example_segments(examples_dir)
                if examples and not dry:
                    install_example_segments(examples, paths.config_dir)
                if examples_flag is not None:
                    desired_ids = {
                        e["id"] for e in resolve_example_selection(examples_flag, examples)
                    }
                else:
                    desired_ids = {
                        e["id"] for e in examples if state["segments"].get(e["id"], False)
                    }
                newly_installed_desired_off = {
                    e["id"] for e in examples
                    if e["id"] not in known_ext_ids and e["id"] not in desired_ids
                }
                ok = persist_statusline(
                    paths, state, adopt, dry, tty=None,
                    assume_overwrite=True,
                    known_ext_ids=known_ext_ids | newly_installed_desired_off,
                )
        return {"ok": ok, "adopt": adopt, "log": buf.getvalue()}
    return commit


def _make_apply_housekeeping(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    paths, entries, stale, predecessor_cands, dry, counts,
):
    """Build the apply_housekeeping(prune, repoint) callable the wizard runs
    IN-UI right after its housekeeping gate is answered (before Choose becomes
    usable). Applies the stale-prune and/or predecessor-repoint decision, then
    rebuilds installed_links + the default component selection from scratch —
    a repointed predecessor link becomes a current ai-kit link, which can
    change which components default to pre-checked on Choose (mirrors the
    ordering the old CLI-side prune_stale/adopt_predecessor_links ->
    installed_links sequence relied on)."""
    def apply_housekeeping(prune, repoint):
        if stale and prune:
            apply_stale_prune(paths.claude_dir, stale, dry, counts)
        if predecessor_cands:
            apply_predecessor_links(paths.claude_dir, predecessor_cands, repoint, dry, counts)
        installed = installed_links(paths.claude_dir, paths.install_dir)
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
        return {"selection": sel, "initial_enabled": initial_enabled}
    return apply_housekeeping


def launch_wizard(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    paths, entries, installed, tty, dry, counts, examples_flag=None,
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
    _tools_dir = os.path.dirname(os.path.abspath(__file__))
    if _tools_dir not in sys.path:
        sys.path.insert(0, _tools_dir)

    import wizard_app  # pylint: disable=import-outside-toplevel

    with open(_sample_input_path(), encoding="utf-8") as f:
        sample_json = f.read()
    present = {cat: {n for n, _ in entries[cat]} for cat in CATEGORIES}
    stale = stale_link_candidates(paths.claude_dir, paths.install_dir, present)
    predecessor_cands = predecessor_candidates(paths.claude_dir, paths.install_dir, entries)
    ctx = _build_wizard_context(paths, entries, installed, sample_json, wizard_app,
                                stale, predecessor_cands)
    # The real install (component symlinks + doctor-validated status-line write +
    # settings.json wiring) now runs INSIDE the wizard on Review-confirm, so the
    # Done screen reflects the actual result. Inject the commit + housekeeping
    # callables here, where paths/entries/dry/counts are in scope.
    ctx = ctx._replace(
        commit=_make_wizard_commit(paths, entries, dry, counts, examples_flag=examples_flag),
        apply_housekeeping=_make_apply_housekeeping(
            paths, entries, stale, predecessor_cands, dry, counts),
    )
    try:
        # curl | bash inherits the script pipe as fd 0; Textual reads keys from
        # fd 0, so redirect it onto the controlling terminal for the run.
        with stdin_on_tty():
            result = wizard_app.run_wizard(ctx)
    except wizard_app.WizardCrash as exc:
        reason = exc.args[0] if exc.args else exc
        print(f"error: wizard failed — {reason}", file=sys.stderr)
        sys.exit(2)
    if result is None:
        return None
    # apply_selection + persist_statusline already ran in-UI via the commit
    # callback (their counts mutations are reflected in `counts`). Surface the
    # captured diagnostics now that the alternate screen is gone, and warn on a
    # status-line write that the doctor rejected.
    log = (result.state.get("_commit_log") or "").strip()
    if log:
        print(log, file=sys.stderr)
    if result.state.get("_commit_ok") is False:
        print(
            "warning: the doctor rejected the status-line config — it was left "
            "unchanged (component selections were still applied).",
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
    entries = enumerate_entries(paths.install_dir)
    counts = new_counts()
    installed = installed_links(paths.claude_dir, paths.install_dir)

    # A: choose what to install + segment layout via Textual wizard (Task 2.1+).
    # Stale-link pruning and predecessor-link repointing (previously raw
    # pre-UI terminal prompts here) now happen INSIDE the wizard's housekeeping
    # gate — see launch_wizard / _build_wizard_context / _make_apply_housekeeping.
    result = launch_wizard(paths, entries, installed, tty, dry, counts,
                           examples_flag=examples_flag)

    # Example external segments (system_memory, …). Aborting the wizard
    # (result is None) is a full no-op — nothing further is installed. On a
    # confirmed install the wizard's own segment toggles drive what gets
    # installed (no double-prompt, I-1); an explicit --examples flag
    # (all|none|<ids>) overrides that selection.
    if result is not None:
        examples = discover_example_segments(
            os.path.join(paths.install_dir, "examples", "segments"))
        if examples:
            if examples_flag is not None:
                # Explicit --examples override wins over the wizard's toggles
                # (resolves the flag without prompting — flag is set).
                chosen = select_examples(examples, examples_flag, tty)
            else:
                # Drive install from the wizard's external-segment toggles
                # captured in result.state["segments"].
                seg_state = result.state["segments"]
                chosen = [e for e in examples if seg_state.get(e["id"], False)]
            if chosen and not dry:
                ids = install_example_segments(chosen, paths.config_dir)
                print(f"examples: installed {len(ids)} external segment(s): "
                      f"{', '.join(ids)}")

    print(f"summary: {counts['linked']} linked, {counts['relinked']} relinked, "
          f"{counts['unlinked']} unlinked, {counts['pruned']} pruned, "
          f"{counts['skip_foreign']} foreign-skipped, {counts['skip_real']} real-skipped")
    print(f"ai-kit installed at {paths.install_dir}")
    print(f"doctor: {_doctor_cmd(paths)}")
    if dry:
        print("(dry-run — no changes were made)")
    return 0


def cmd_uninstall(env, dry):
    """Remove every ai-kit symlink under ~/.claude, the ai-kit statusLine (only
    if it points into install_dir), and ai-kit's own session-start hook entries
    from both Claude Code and Cursor. Foreign hook entries are never touched.
    Leaves install_dir, foreign links, and the config TOML in place."""
    paths = resolve_paths(env)
    counts = new_counts()
    installed = installed_links(paths.claude_dir, paths.install_dir)
    for cat in CATEGORIES:
        for name in sorted(installed[cat]):
            unlink_one(os.path.join(paths.claude_dir, cat, name), dry, counts)
    unwire_statusline(paths.settings, paths.install_dir, dry)
    unwire_hook_claude(paths.settings, dry)
    unwire_hook_cursor(paths.cursor_hooks, dry)
    print(f"removed {counts['unlinked']} ai-kit symlink(s). "
          f"install dir left in place: {paths.install_dir}")
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
    """Launch the Config Doctor TUI (read-only in this phase).

    ``dry`` is accepted now so Wave 3's apply flow can read it from this same
    call site without a signature change. Nothing in this wave writes.
    """
    isatty_fn = getattr(tty, "isatty", None)
    if tty is None or not callable(isatty_fn) or not isatty_fn():
        print(
            "error: cmd_config_doctor reached without a real terminal — this is a bug. "
            "require_tty() should have exited before this point.",
            file=sys.stderr,
        )
        sys.exit(2)

    _tools_dir = os.path.dirname(os.path.abspath(__file__))
    if _tools_dir not in sys.path:
        sys.path.insert(0, _tools_dir)

    import config_doctor_app  # pylint: disable=import-outside-toplevel
    import config_doctor_checks  # pylint: disable=import-outside-toplevel

    catalog = config_doctor_checks.build_catalog(env)
    ctx = config_doctor_app.ConfigDoctorContext(catalog=catalog, apply=None)
    with stdin_on_tty():
        config_doctor_app.run_config_doctor(ctx)
    return 0


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


def main(argv=None):
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
        help="launch the config diagnostics TUI (read-only in this phase)",
    )
    args = parser.parse_args(argv)
    env = os.environ
    dry = args.dry_run
    if args.config_doctor:
        ensure_rich_runtime(env)
        tty = cast("_StdTty", require_tty(open_tty()))
        try:
            return cmd_config_doctor(env, tty, dry)
        finally:
            tty.close()
    if args.subcommand in ("install", "reconfigure"):
        ensure_rich_runtime(env)              # may re-exec; must be BEFORE open_tty
        tty = cast("_StdTty", require_tty(open_tty()))  # fail-closed (FR-W.1/B)
        try:
            return cmd_install(env, tty, dry,
                               examples_flag=args.examples)
        finally:
            tty.close()
    if args.subcommand == "uninstall":
        return cmd_uninstall(env, dry)
    if args.subcommand == "doctor":
        return cmd_doctor(env)
    if args.subcommand == "check":
        return cmd_check(env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
