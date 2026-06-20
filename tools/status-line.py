#!/usr/bin/env python3
"""Claude Code status line — modular Python port of statusline.sh.

Reads the status JSON on stdin and prints up to three ANSI-colored lines.
Layout is driven by SEGMENTS (on/off), LAYOUT (template), and BUILDERS
(key -> builder(data, avail)). The packer is the authority on show/hide;
builders auto-deprioritize to fit. See the "HOW TO CUSTOMIZE" block near the
bottom. Stdlib only. The .sh original is kept as a fallback.
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import unicodedata
try:
    import tomllib
except ModuleNotFoundError:        # Python < 3.11 — degrade to env-only config.
    tomllib = None
from collections import namedtuple
from datetime import datetime

# ═══ CONFIG — edit freely ════════════════════════════════════════════════════
# Per-segment on/off. Set False to hide a segment entirely: its builder is never
# called AND its data is never gathered, so a disabled segment costs nothing —
# `build_data` skips the matching probe (git/transcript/RSS/etc.). Invariant:
# keep "path" True so the identity line always emits.
SEGMENTS = {
    # identity line
    "path": True, "branch": True, "dirty": True, "worktree": True, "todo": True,
    # model row
    "model": True, "time_ago": True, "clock": True, "effort": True,
    "lines": True, "cost": False, "total_time": True, "api_time": True,
    # diagnostics row (dimensions is a debug aid — off by default)
    "render_time": True, "dimensions": False, "context": True, "chat_size": True,
    "memory": True, "rate_limits": True,
}

# Identity-line tuning.
PATH_MAX_LEN = 20       # ~-collapsed path longer than this collapses to its basename
CONTEXT_BAR_CELLS = 10  # context bar width; ▌ half-cells give 5% resolution

# Packing: reserve a few cols so emoji-width miscounts don't wrap the line.
RIGHT_MARGIN = 4
SEP = " | "

# ═══ Layout template — edit to reorder / move / re-line segments ═════════════
# One Line per row. `segments` lists keys LEFT->RIGHT; leftmost = highest
# priority (kept first when space is tight). `min_rows` gates the whole row by
# terminal height. Reorder = move a key within a list; move between rows = cut
# and paste a key; hide = flip its SEGMENTS flag.
Line = namedtuple("Line", "min_rows segments")
LAYOUT = [
    Line(0,  ["path", "branch", "worktree", "dirty", "todo"]),
    Line(20, ["model", "time_ago", "clock", "effort", "lines",
              "cost", "total_time", "api_time"]),
    Line(30, ["render_time", "dimensions", "context", "chat_size", "memory", "rate_limits"]),
]
PINNED = {"path", "context"}   # always rendered even if they overflow the budget

# Resolved configuration: the result of merging internal defaults < TOML file <
# env. `segments` is a {key: bool} dict, `layout` a list[Line], `palette` a
# {NAME: "sgr;params"} dict of overrides (empty = no override), `ramps` a
# {band: {threshold: colorspec}} dict of whole-band overrides (empty = no
# override). External drop-in segments are E4c and are intentionally not part of
# this type yet.
# Scalar behaviour knobs that aren't segments/colors. The worktree feature
# migrated to the `segments.worktree` toggle (see SEGMENTS); `[git]` now carries
# `cache_ttl` (seconds) — how long the shared git_snapshot worktree probe is
# cached. Precedence: this default < TOML `[git] cache_ttl` < env CC_AI_KIT_GIT_TTL.
_GIT_CACHE_TTL = 5                  # default seconds the worktree probe is cached
_GIT_DEFAULTS = {"cache_ttl": _GIT_CACHE_TTL}
# Deprecated `[git]` keys: silently accepted (no warning) and ignored, so an old
# config carrying `[git] worktree = true/false` keeps loading cleanly after the
# knob moved to `segments.worktree`.
_GIT_LEGACY_IGNORED = frozenset({"worktree"})


def _git_key_problem(k, v):
    """Classify one `[git]` key/value so load_config and validate_config_file share
    a single validation rule (each formats its own message). Returns:
      'legacy'  — a deprecated key the caller should silently skip,
      'unknown' — not a recognized `[git]` key,
      'bad_ttl' — cache_ttl is not an int (bools excluded),
      None      — acceptable."""
    if k in _GIT_LEGACY_IGNORED:
        return "legacy"
    if k not in _GIT_DEFAULTS:
        return "unknown"
    if k == "cache_ttl" and (not isinstance(v, int) or isinstance(v, bool)):
        return "bad_ttl"
    return None

# `git` and `external` default to None so older Config(...) call sites (which
# pass only the original fields) keep working; consumers read git via
# (cfg.git or {}) and external via (cfg.external or []).
Config = namedtuple("Config", "segments layout palette ramps git external",
                    defaults=(None, None))


def default_config():
    """A Config snapshotting the current module-global defaults (SEGMENTS/LAYOUT,
    no palette/ramp overrides). Copies are returned so callers cannot mutate
    globals."""
    return Config(segments=dict(SEGMENTS), layout=list(LAYOUT), palette={}, ramps={},
                  git=dict(_GIT_DEFAULTS))


# ═══ Config resolution (defaults < TOML file < env) ══════════════════════════
_ENV_TRUE = {"1", "true", "t", "y", "yes", "on"}
_ENV_FALSE = {"0", "false", "f", "n", "no", "off"}


def env_bool(env, name):
    """Tri-state bool from env[name]: True / False / None (unset or unrecognized).
    None means 'no override' so callers fall through to file/default."""
    v = env.get(name)
    if v is None:
        return None
    v = v.strip().lower()
    if v in _ENV_TRUE:
        return True
    if v in _ENV_FALSE:
        return False
    return None


def config_path(env):
    """Resolved TOML path: CC_AI_KIT_CONFIG, else
    ${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/statusline.toml."""
    explicit = env.get("CC_AI_KIT_CONFIG")
    if explicit:
        return os.path.expanduser(explicit)
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "ai-kit", "statusline.toml")


def _load_toml(path):
    """Parse the TOML at path. Missing/empty/malformed/no-tomllib → {} (a dim
    warning to stderr on a malformed file). Never raises."""
    if tomllib is None:
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"{_DIM}status-line: ignoring config {path}: {e}{RESET}", file=sys.stderr)
        return {}


def _resolve_segments(defaults, file_seg, env):
    """defaults < file [segments] < CC_AI_KIT_SEGMENT_<KEY> env. Each file entry
    is dropped with a dim warning if its key is unknown OR its value is not a
    bool (e.g. `cost = "true"` instead of `cost = true`); only bool file values
    for known keys are honored. Env always overrides whatever the file resolved."""
    seg = dict(defaults)
    for k, v in (file_seg or {}).items():
        if k not in seg:
            print(f"{_DIM}status-line: unknown segment '{k}' in config{RESET}",
                  file=sys.stderr)
        elif not isinstance(v, bool):
            print(f"{_DIM}status-line: segment '{k}' must be true/false, "
                  f"got {v!r} — ignored{RESET}", file=sys.stderr)
        else:
            seg[k] = v
    for k in seg:
        ov = env_bool(env, f"CC_AI_KIT_SEGMENT_{k.upper()}")
        if ov is not None:
            seg[k] = ov
    return seg


def _resolve_layout(default_layout, raw_lines):
    """If the file has ANY [[line]] block, it REPLACES the whole layout
    (all-or-nothing — a partial layout can't silently drop segments). Otherwise
    keep the default. Each block: min_rows (default 0) + segments list."""
    if not raw_lines:
        return list(default_layout)
    return [Line(int(item.get("min_rows", 0)), list(item.get("segments", [])))
            for item in raw_lines]


def _resolve_external(raw, env):
    """Resolve (segments_dir, default_ttl) from defaults < [external] file < env.
    Env: CC_AI_KIT_SEGMENTS_DIR (dir), CC_AI_KIT_EXTERNAL_TTL (int seconds)."""
    file_ext = raw.get("external") or {}
    ttl = 10
    fv = file_ext.get("ttl")
    if isinstance(fv, int) and not isinstance(fv, bool):
        ttl = fv
    ev = env.get("CC_AI_KIT_EXTERNAL_TTL")
    if ev is not None:
        try:
            ttl = int(ev)
        except ValueError:
            pass
    return _segments_dir(file_ext, env), ttl


def _place_external(layout, specs):
    """Insert each spec's id into the resolved layout at its row/position and
    return (new_layout, finalized_specs). Resolves line=0 to the last row and
    clamps out-of-range rows (with a dim warning). Specs are applied in their
    (filename, id) sort order so same-slot externals are deterministic."""
    if not layout:
        return list(layout), []
    rows = [list(ln.segments) for ln in layout]
    nrows = len(rows)
    final = []
    for spec in specs:
        want = spec.line or nrows                      # 0 => last row
        idx = want - 1
        if idx < 0 or idx >= nrows:
            print(f"{_DIM}status-line: segment '{spec.id}' line={want} out of range "
                  f"— clamped to row {nrows}{RESET}", file=sys.stderr)
            idx = nrows - 1
        kind, ref = spec.position
        segs = rows[idx]
        if kind == "start":
            segs.insert(0, spec.id)
        elif kind == "after" and ref in segs:
            segs.insert(segs.index(ref) + 1, spec.id)
        elif kind == "before" and ref in segs:
            segs.insert(segs.index(ref), spec.id)
        else:                                          # end, or after/before missing ref
            segs.append(spec.id)
        final.append(spec._replace(line=idx + 1))
    new_layout = [Line(layout[i].min_rows, rows[i]) for i in range(nrows)]
    return new_layout, final


def load_config(env):
    """Resolve the full Config: internal defaults < TOML file < env.

    Resolves segments, layout, palette, ramps, and the [git] knobs. Also
    discovers external drop-in providers from the [external] `dir` (default
    ~/.config/ai-kit/segments) BEFORE resolving segments — so each provider id
    is a known segment key (enabled by default, disable via `[segments] <id> =
    false`) — and places them into the layout. The resolved providers land in
    Config.external (a list of finalized ExtSpec); the global default cache TTL
    and providers dir are recoverable via _resolve_external(raw, env)."""
    base = default_config()
    raw = _load_toml(config_path(env))

    # External providers first: their ids must be known segment keys before
    # _resolve_segments runs, so `[segments] <id> = false` is honored (not warned)
    # and they default to enabled.
    ext_dir, ext_ttl = _resolve_external(raw, env)
    specs = discover_external(ext_dir, ext_ttl, env)
    seg_defaults = dict(base.segments)
    for s in specs:
        seg_defaults.setdefault(s.id, True)

    segments = _resolve_segments(seg_defaults, raw.get("segments"), env)
    layout = _resolve_layout(base.layout, raw.get("line"))
    layout, external = _place_external(layout, specs)
    palette = {}
    for k, v in (raw.get("palette") or {}).items():
        if k in _PALETTE_DEFAULTS:
            palette[k] = str(v)
        else:
            print(f"{_DIM}status-line: unknown palette key '{k}'{RESET}", file=sys.stderr)
    ramps = {}
    for band, table in (raw.get("ramp") or {}).items():
        if band not in _RAMP_DEFAULTS:
            print(f"{_DIM}status-line: unknown ramp '{band}'{RESET}", file=sys.stderr)
            continue
        if not isinstance(table, dict):
            print(f"{_DIM}status-line: ramp '{band}' must be a table — ignored{RESET}",
                  file=sys.stderr)
            continue
        ramps[band] = {str(k): str(v) for k, v in table.items()}
    git = dict(_GIT_DEFAULTS)
    for k, v in (raw.get("git") or {}).items():
        problem = _git_key_problem(k, v)
        if problem == "legacy":
            continue                               # deprecated, tolerated, no effect
        if problem == "unknown":
            print(f"{_DIM}status-line: unknown [git] key '{k}'{RESET}", file=sys.stderr)
        elif problem == "bad_ttl":
            print(f"{_DIM}status-line: [git] cache_ttl must be an integer, "
                  f"got {v!r} — ignored{RESET}", file=sys.stderr)
        else:
            git[k] = v
    ttl_env = env.get("CC_AI_KIT_GIT_TTL")         # env wins over file
    if ttl_env is not None:
        try:
            git["cache_ttl"] = int(ttl_env)
        except ValueError:
            print(f"{_DIM}status-line: CC_AI_KIT_GIT_TTL must be an integer, "
                  f"got {ttl_env!r} — ignored{RESET}", file=sys.stderr)
    return Config(segments=segments, layout=layout, palette=palette, ramps=ramps,
                  git=git, external=external)


# ═══ Palette ════════════════════════════════════════════════════════════════
# Fixed (non-overridable) colors.
RESET = "\033[0m"
BG_LIGHTGRAY = "\033[47m"
_DIM = "\033[90m"             # fixed dim grey for stderr warnings (palette-independent)
_WARN = "\033[33m"            # fixed yellow for failure markers (palette-independent)


def _doctor_cmd():
    """A concrete, copy-pasteable doctor invocation for THIS install — resolved
    from the running interpreter and this file's path (~-collapsed). Never a bare
    '--doctor', which would assume the user is sitting in a repo clone."""
    py = os.path.basename(sys.executable) or "python3"
    path = os.path.abspath(__file__)
    home = os.path.expanduser("~")
    if path == home or path.startswith(home + os.sep):
        path = "~" + path[len(home):]
    return f"{py} {path} --doctor"

# Overridable palette: NAME -> default SGR params (no "\033[" / "m" wrapper).
# Values are pure hues — no baked-in bold. Emphasis is expressed on the ramp
# bands via "+modifiers" (e.g. "RED+bold"); see _RAMP_DEFAULTS. A [palette]
# override replaces a value here; build_theme resolves these into a Theme.
_PALETTE_DEFAULTS = {            # pure hues — no baked-in bold
    "GREY": "90", "WHITE": "97", "CYAN": "36", "GREEN": "32", "RED": "31",
    "YELLOW": "33", "MAGENTA": "35", "ORANGE": "38;5;208",
    "BLUE": "38;5;39",           # lightened (was 38;5;33); shade reviewed on-terminal
    "LIGHTBLUE": "38;5;75", "MAGENTA_DARK": "38;5;90",
}   # ORANGE_BOLD / MAGENTA_DARK_BOLD removed — bold now lives on the ramp band

# Ramps as data: band -> [(threshold, colorspec)]. Threshold keys go through
# _parse_threshold (percent / byte-suffix / inf); colorspecs through parse_color
# against the resolved palette. [ramp.X] in config REPLACES a band wholesale.
_RAMP_DEFAULTS = {
    "context": [(10, "WHITE"), (15, "CYAN"), (20, "BLUE"), (25, "GREEN"),
                (30, "YELLOW"), (40, "ORANGE+bold"), (50, "RED+bold"),
                ("inf", "MAGENTA_DARK+bold")],
    "rate": [(50, "GREEN"), (80, "YELLOW"), ("inf", "RED+bold")],
    "chat_size": [("512k", "WHITE"), ("1M", "CYAN"), ("2M", "LIGHTBLUE"),
                  ("3M", "GREEN"), ("4M", "YELLOW"), ("5M", "ORANGE"),
                  ("10M", "RED+bold"), ("inf", "MAGENTA")],
    # render_time: the status line's own run time (SLO/SLA). Thresholds are time
    # units (ns/µs/ms/s); green under the SLO, yellow under the SLA, red beyond.
    "render_time": [("50ms", "GREEN"), ("150ms", "YELLOW"), ("inf", "RED+bold")],
}

# Effort ladder: level -> (palette name, fill count 1..5). Palette-derived but
# NOT user-configurable. `auto` is a setting and `ultracode` reports as xhigh —
# neither is a level here.
_EFFORT_DEFAULTS = {
    "low": ("CYAN", 1), "medium": ("BLUE", 2), "high": ("YELLOW", 3),
    "xhigh": ("ORANGE", 4), "max": ("RED", 5),
}
_EFFORT_GLYPHS = "▁▃▄▆█"

INF = float("inf")


# ═══ External drop-in segments (E4c) ═════════════════════════════════════════
# A provider is an executable in the segments dir. Its first 10 lines may carry
#   # ai-kit-segment: line=<N> (after=<key>|before=<key>|start|end) [id=<slug>] [timeout=<s>] [ttl=<s>]
# It is modeled as a synthetic builder inserted into the resolved layout, so the
# existing packer handles placement/priority/overflow unchanged.
ExtSpec = namedtuple("ExtSpec", "id path line position timeout ttl cache_path")

_SEG_HEADER_RE = re.compile(r"^#\s*ai-kit-segment:\s*(.*?)\s*$")


def parse_segment_header(lines):
    """Parse the `# ai-kit-segment:` header from a file's first lines.

    Returns a dict of the raw string fields present (`line`/`id`/`timeout`/`ttl`
    as strings, `position` as a (kind, ref) tuple) — possibly empty if the header
    line exists but lists nothing. Returns None when no header line is present."""
    for ln in lines:
        m = _SEG_HEADER_RE.match(ln)
        if m is None:
            continue
        fields = {}
        for tok in m.group(1).split():
            if tok in ("start", "end"):
                fields["position"] = (tok, "")
            elif "=" in tok:
                k, v = tok.split("=", 1)
                if k in ("after", "before"):
                    fields["position"] = (k, v)
                elif k in ("line", "id", "timeout", "ttl"):
                    fields[k] = v
        return fields
    return None


def _cache_base(env):
    """${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit — root of every ai-kit on-disk cache."""
    base = env.get("XDG_CACHE_HOME") or os.path.join(env.get("HOME", ""), ".cache")
    return os.path.join(base, "ai-kit")


def _segments_cache_dir(env):
    """…/ai-kit/segments — per-provider output cache."""
    return os.path.join(_cache_base(env), "segments")


def _segments_dir(file_external, env):
    """Resolve the providers directory: CC_AI_KIT_SEGMENTS_DIR > [external].dir >
    ${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/segments."""
    d = env.get("CC_AI_KIT_SEGMENTS_DIR") or (file_external or {}).get("dir")
    if d:
        return os.path.expanduser(d)
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "ai-kit", "segments")


def discover_external(directory, default_ttl, env):
    """Scan `directory` for executable providers and return a list of ExtSpec,
    sorted by (filename, id). Non-executable files are skipped with a dim warning.
    A file with no header still loads with all defaults (line=0 => last row at
    placement, position=end, id=stem, timeout=2s, ttl=default_ttl)."""
    if not directory or not os.path.isdir(directory):
        return []
    cache_dir = _segments_cache_dir(env)
    specs = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        if not os.access(path, os.X_OK):
            print(f"{_DIM}status-line: segment '{name}' not executable — skipped{RESET}",
                  file=sys.stderr)
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                head = [f.readline() for _ in range(10)]
        except OSError:
            continue
        fields = parse_segment_header(head) or {}
        sid = fields.get("id") or os.path.splitext(name)[0]
        try:
            timeout = float(fields.get("timeout", 2))
        except (TypeError, ValueError):
            timeout = 2.0
        try:
            ttl = int(fields.get("ttl", default_ttl))
        except (TypeError, ValueError):
            ttl = default_ttl
        try:
            line = int(fields["line"]) if "line" in fields else 0
        except (TypeError, ValueError):
            line = 0
        specs.append(ExtSpec(
            id=sid, path=path, line=line,
            position=fields.get("position", ("end", "")),
            timeout=timeout, ttl=ttl,
            cache_path=os.path.join(cache_dir, sid)))
    specs.sort(key=lambda s: (os.path.basename(s.path), s.id))
    return specs


_SGR_SEQ = re.compile(r"\x1b\[[0-9;]*m")            # an SGR color/style escape
_CSI_SEQ = re.compile(r"\x1b\[[0-9;?]*([A-Za-z])")  # any CSI; group = final byte
_OSC_SEQ = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_STRAY_ESC = re.compile(r"\x1b(?!\[[0-9;]*m)")      # ESC not starting an SGR
_C0_CTRL = re.compile(r"[\x00-\x09\x0b-\x1a\x1c-\x1f\x7f]")  # controls (incl. TAB) except NL/ESC


def _truncate_visible(s, avail):
    """Cut s to at most `avail` visible cells, preserving zero-width SGR escapes,
    appending RESET if any SGR was emitted. avail <= 0 -> ''."""
    if avail <= 0:
        return ""
    out, width, i, n, saw_sgr = [], 0, 0, len(s), False
    while i < n:
        m = _SGR_SEQ.match(s, i)
        if m:
            out.append(m.group(0))
            saw_sgr = True
            i = m.end()
            continue
        w = char_width(s[i])
        if width + w > avail:
            break
        out.append(s[i])
        width += w
        i += 1
    res = "".join(out)
    if saw_sgr and not res.endswith(RESET):
        res += RESET
    return res


def _sanitize_external(text, avail):
    """First non-empty line of `text`, SGR colors kept, every other control/CSI/OSC
    sequence stripped, width-truncated to `avail`. None if nothing renderable."""
    line = next((c for c in text.splitlines() if c.strip()), "").rstrip()
    if not line:
        return None
    line = _OSC_SEQ.sub("", line)
    line = _CSI_SEQ.sub(lambda m: m.group(0) if m.group(1) == "m" else "", line)
    line = _STRAY_ESC.sub("", line)
    line = _C0_CTRL.sub("", line)
    if not line.strip():
        return None
    return _truncate_visible(line, avail) or None


def _position_str(position):
    """('after','clock') -> 'after:clock'; ('end','') -> 'end'."""
    kind, ref = position
    return f"{kind}:{ref}" if ref else kind


def _cache_read(spec):
    """Cached raw output line if present and younger than ttl, else None.
    ttl <= 0 always misses (forces a re-run every render)."""
    if spec.ttl <= 0:
        return None
    try:
        age = time.time() - os.stat(spec.cache_path).st_mtime
    except OSError:
        return None
    if age >= spec.ttl:
        return None
    try:
        with open(spec.cache_path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _cache_write(spec, text):
    """Best-effort: persist raw output. Unwritable cache dir -> silently skip."""
    try:
        os.makedirs(os.path.dirname(spec.cache_path), exist_ok=True)
        with open(spec.cache_path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass


def _run_provider(spec, data, avail):
    """Spawn the provider with the status JSON + segment block on stdin, the
    AI_KIT_SEGMENT_* env mirror, and cwd = workspace dir. Returns the raw first
    non-empty stdout line, or None on timeout / non-zero exit / no output."""
    pos = _position_str(spec.position)
    payload = json.dumps({**(data.get("raw") or {}),
                          "segment": {"id": spec.id, "avail_cols": avail,
                                      "line": spec.line, "position": pos}})
    env = dict(os.environ)
    env.update({"AI_KIT_SEGMENT_COLS": str(avail), "AI_KIT_SEGMENT_ID": spec.id,
                "AI_KIT_SEGMENT_LINE": str(spec.line), "AI_KIT_SEGMENT_POSITION": pos})
    try:
        proc = subprocess.run(
            [spec.path], input=payload, capture_output=True, text=True,
            timeout=spec.timeout, cwd=data.get("work_dir") or ".", env=env)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        if line.strip():
            return line
    return None


def run_external(spec, data, avail):
    """TTL-cached, timeout-bounded provider invocation. Returns the sanitized,
    width-fitted segment string, or None to omit the segment."""
    raw_line = _cache_read(spec)
    if raw_line is None:
        raw_line = _run_provider(spec, data, avail)
        if raw_line is None:
            return None
        _cache_write(spec, raw_line)
    return _sanitize_external(raw_line, avail)


def pick_color(pct, ramp):
    """Return the color for the first ceil that pct is strictly below."""
    for ceil, color in ramp:
        if pct < ceil:
            return color
    return ramp[-1][1]


# ═══ Display width ═══════════════════════════════════════════════════════════
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")
# BMP symbols we render that terminals draw 2 cells wide (east_asian_width
# misclassifies these as narrow). Add a codepoint here if a new wide BMP glyph
# is introduced in a segment.
_WIDE_BMP = {0x23F0, 0x23F1, 0x23F8, 0x26A1}  # ⏰ ⏱ ⏸ ⚡


def char_width(ch):
    """Display cells for one char: 0 (combining/zero-width), 1, or 2 (wide)."""
    if unicodedata.combining(ch):
        return 0
    o = ord(ch)
    if o >= 0x1F300:                                  # emoji / pictographs (SMP)
        return 2
    if o in _WIDE_BMP:
        return 2
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def visible_width(s):
    """Terminal display width of s, ignoring ANSI SGR escapes."""
    return sum(char_width(c) for c in _ANSI_RE.sub("", s))


def _first_fitting(variants, avail):
    """Return the first (richest) truthy variant whose display width fits avail.

    None if none fit. Builders pass their variants rich-first so the widest
    affordable detail level wins; returning None is a builder self-hiding."""
    for v in variants:
        if v and visible_width(v) <= avail:
            return v
    return None


# ═══ Color engine ════════════════════════════════════════════════════════════
# One parser produces every SGR escape. Base forms (by shape): palette NAME
# (letter-led, resolved against `palette`), raw SGR ("38;5;208" passthrough), or
# hex ("#rgb"/"#rrggbb"/"#rrggbbaa", alpha dropped). "+bold/+dim/+italic/
# +underline" modifiers prepend 1/2/3/4 in ascending order. Invalid -> None.
_MOD_SGR = {"bold": "1", "dim": "2", "italic": "3", "underline": "4"}


def _hex_to_sgr(spec):
    """'#rgb' / '#rgba' / '#rrggbb' / '#rrggbbaa' -> '38;2;r;g;b' (alpha
    dropped). None if not valid hex of a supported length."""
    h = spec[1:]
    if len(h) in (3, 4):                 # short form: expand each nibble, drop alpha
        h = "".join(c * 2 for c in h[:3])
    elif len(h) == 8:                    # long form with alpha: drop the alpha byte
        h = h[:6]
    if len(h) != 6 or re.fullmatch(r"[0-9a-fA-F]{6}", h) is None:
        return None
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"38;2;{r};{g};{b}"


def parse_color(spec, palette=None):
    """Resolve a colorspec to '\\033[...m', or None if invalid. See section
    header for the grammar. `palette` ({NAME: sgr params}) is required only for
    name lookups; raw-SGR and hex specs ignore it."""
    if not spec:
        return None
    base, *mod_names = str(spec).split("+")
    base = base.strip()
    mods = []
    for m in mod_names:
        code = _MOD_SGR.get(m.strip().lower())
        if code is None:
            return None
        mods.append(code)
    if base.startswith("#"):
        params = _hex_to_sgr(base)
    elif base[:1].isalpha():
        params = (palette or {}).get(base)
    elif re.fullmatch(r"[0-9;]+", base):
        params = base
    else:
        params = None
    if params is None:
        return None
    ordered = sorted(set(mods), key=int)
    return "\033[" + ";".join(ordered + [params]) + "m"


_THRESHOLD_MULT = {"k": 1024, "M": 1024 ** 2, "G": 1024 ** 3}
# Time thresholds (render_time ramp) resolve to NANOSECONDS, matching what the
# segment measures via time.perf_counter_ns(). "µs" and ASCII "us" both accepted.
_TIME_MULT_NS = {"ns": 1, "us": 1000, "µs": 1000, "ms": 1_000_000, "s": 1_000_000_000}


def _parse_threshold(key):
    """Ramp threshold -> comparable number. 'inf'/inf -> INF; '512k'/'5M'/'1G'
    -> bytes (1024-based); '50ms'/'2s'/'500us'/'100ns' -> nanoseconds; bare int /
    numeric string -> that int (a percent). Raises ValueError on anything else."""
    if isinstance(key, float):
        return key
    if isinstance(key, int):
        return key
    s = str(key).strip()
    if s.lower() == "inf":
        return INF
    m = re.fullmatch(r"(\d+)([kMG])", s)
    if m:
        return int(m.group(1)) * _THRESHOLD_MULT[m.group(2)]
    m = re.fullmatch(r"(\d+)(ns|µs|us|ms|s)", s)
    if m:
        return int(m.group(1)) * _TIME_MULT_NS[m.group(2)]
    return int(s)   # ValueError on garbage


class Theme:
    """Resolved colors for one render. `palette` maps NAME -> bare SGR params;
    `ramps` band -> [(ceil, escape)]; `effort` level -> (escape, bar). `c()`
    memoizes parse_color and never raises (invalid spec -> '')."""

    def __init__(self, palette, ramps, effort):
        self.palette = palette
        self.ramps = ramps
        self.effort = effort
        self._cache = {}

    def c(self, spec):
        if spec not in self._cache:
            self._cache[spec] = parse_color(spec, self.palette) or ""
        return self._cache[spec]


def _resolve_palette(overrides):
    """Merge _PALETTE_DEFAULTS with `overrides` ({NAME: spec}); each override
    value is parsed (hex / raw SGR / +mods — no name nesting) to bare params. A
    bad value warns and keeps the default."""
    palette = dict(_PALETTE_DEFAULTS)
    for name, value in (overrides or {}).items():
        if name not in _PALETTE_DEFAULTS:
            continue                       # unknown keys already warned in load_config
        esc = parse_color(value, palette=None)
        if esc is None:
            print(f"{_DIM}status-line: bad palette {name}={value!r} — keeping "
                  f"default{RESET}", file=sys.stderr)
            continue
        palette[name] = esc[2:-1]          # strip "\033[" .. "m" -> bare params
    return palette


def _resolve_ramp(pairs, palette, band, fallback):
    """Resolve [(threshold, colorspec)] -> [(ceil, escape)] sorted ascending.
    A bad band color falls back to that ceil's color in `fallback`; a bad
    threshold abandons the override and returns `fallback` whole. `fallback` is
    None only when resolving the built-in defaults (known-good)."""
    fb = dict(fallback) if fallback else {}
    out = []
    for thr, spec in pairs:
        try:
            ceil = _parse_threshold(thr)
        except ValueError:
            print(f"{_DIM}status-line: bad ramp [{band}] threshold {thr!r} — "
                  f"keeping default{RESET}", file=sys.stderr)
            return list(fallback) if fallback else out
        esc = parse_color(spec, palette)
        if esc is None:
            esc = fb.get(ceil, "")
            print(f"{_DIM}status-line: bad ramp [{band}] color {spec!r} — using "
                  f"default band{RESET}", file=sys.stderr)
        out.append((ceil, esc))
    out.sort(key=lambda ce: ce[0])
    return out


def _build_effort(palette):
    """level -> (color escape, bar string). Filled glyphs in the level's color,
    the rest in grey (the effort-ladder layout)."""
    grey = parse_color("GREY", palette) or ""
    out = {}
    for level, (name, n) in _EFFORT_DEFAULTS.items():
        color = parse_color(name, palette) or ""
        rest = _EFFORT_GLYPHS[n:]
        bar = f"{color}{_EFFORT_GLYPHS[:n]}" + (f"{grey}{rest}" if rest else "")
        out[level] = (color, bar)
    return out


def build_theme(cfg):
    """Resolve a Config's palette + ramps + effort into a Theme."""
    palette = _resolve_palette(cfg.palette)
    ramps = {}
    for band, default_pairs in _RAMP_DEFAULTS.items():
        default_ramp = _resolve_ramp(default_pairs, palette, band, None)
        override = (cfg.ramps or {}).get(band)
        ramps[band] = (default_ramp if override is None
                       else _resolve_ramp(override.items(), palette, band, default_ramp))
    return Theme(palette, ramps, _build_effort(palette))


def default_theme():
    """Theme from default_config() (no overrides)."""
    return build_theme(default_config())


# ═══ Formatters ══════════════════════════════════════════════════════════════
def fmt_number(n):
    """Thousands separators: 1234567 -> '1,234,567'."""
    return f"{int(n):,}"


def fmt_time_ms(ms):
    """Human-readable duration from milliseconds (matches statusline.sh)."""
    ms = int(ms)
    if ms < 1000:
        return f"{ms}ms"
    if ms < 60_000:
        return f"{ms // 1000}s"
    if ms < 3_600_000:
        return f"{ms // 60_000}m {(ms % 60_000) // 1000}s"
    return f"{ms // 3_600_000}h {(ms % 3_600_000) // 60_000}m"


def fmt_tokens(n):
    """200000 -> '200K', 1000000 -> '1M'."""
    n = int(n)
    if n >= 1_000_000:
        return f"{n // 1_000_000}M"
    if n >= 1000:
        return f"{n // 1000}K"
    return str(n)


def fmt_ago(secs):
    """Seconds since last activity as an 'ago' string."""
    secs = int(secs)
    if secs <= 0:
        return "just now"
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60}s ago"
    return f"{secs // 3600}h {(secs % 3600) // 60}m ago"


def fmt_bytes(n):
    """IEC byte size matching `numfmt --to=iec --suffix=B`: ceiling rounding,
    one decimal only when the scaled value is < 10."""
    n = int(n)
    if n < 1024:
        return f"{n}B"
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    if v < 10:
        return f"{math.ceil(v * 10) / 10:.1f}{units[i]}"
    return f"{math.ceil(v)}{units[i]}"


def fmt_duration(ns):
    """Adaptive duration from nanoseconds: ns / µs / ms / s, picking the largest
    unit that keeps the value >= 1. One decimal only when the scaled value is
    < 10 (matching fmt_bytes' style)."""
    ns = int(ns)
    if ns < 1000:
        return f"{ns}ns"
    for div, suffix in ((1_000_000_000, "s"), (1_000_000, "ms"), (1000, "µs")):
        if ns >= div:
            v = ns / div
            return f"{v:.1f}{suffix}" if v < 10 else f"{v:.0f}{suffix}"


# ═══ Rate-limit helpers ══════════════════════════════════════════════════════
_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15,
    "twenty": 20, "thirty": 30, "sixty": 60,
}
_UNIT_ABBR = {
    "hour": "h", "hours": "h", "day": "d", "days": "d",
    "week": "w", "weeks": "w", "month": "mo", "months": "mo",
}


def rate_key_label(key):
    """five_hour -> '5h', thirty_day -> '30d'. Unknown words pass through."""
    num, _, unit = key.partition("_")
    num = _NUM_WORDS.get(num, num)
    unit = _UNIT_ABBR.get(unit, unit)
    return f"{num}{unit}"


def rate_color(pct, theme):
    return pick_color(float(pct), theme.ramps["rate"])


# ═══ Segment builders ════════════════════════════════════════════════════════
# Contract: every builder is seg_x(data, avail, theme) -> str | None.
#   avail = display cells available to this segment at its position.
#   Return None when there is no data, OR when even the smallest variant does
#   not fit avail (the builder self-deprioritizes). Otherwise return the richest
#   variant that fits, via _first_fitting([rich, ..., minimal], avail).
# The packer (pack_line) supplies avail and owns the final keep/skip decision.
# To add a segment: write seg_x(data, avail, theme), add it to BUILDERS, list its key
# in a LAYOUT line, add a SEGMENTS flag. See the HOW TO CUSTOMIZE block below.

# NOTE: the effort bars live on the Theme (theme.effort), resolved by
# _build_effort from the palette so a [palette] override re-colors them too.
# `ultracode` is NOT a level (it reports as xhigh + standing multi-agent
# permission), and `auto` is a *setting*, not a resolved level — neither belongs
# in the table. The auto setting is surfaced as a "[auto]" suffix in seg_effort.


def _display_dir(work_dir, home):
    shown = work_dir
    if home and work_dir.startswith(home):
        shown = "~" + work_dir[len(home):]
    if len(shown) <= PATH_MAX_LEN:
        return shown
    return os.path.basename(work_dir.rstrip("/")) or shown


def _dirty_mark(dirty, theme):
    if dirty == "untracked":
        return f"{theme.c('RED')}✗{RESET}"
    if dirty == "modified":
        return f"{theme.c('YELLOW')}~{RESET}"
    return ""


# ── identity line ────────────────────────────────────────────────────────────
def seg_path(data, avail, theme):
    return f"{theme.c('BLUE')}{_display_dir(data['work_dir'], data['home'])}{RESET}"  # floor


def seg_branch(data, avail, theme):
    branch = data.get("branch")
    if not branch:
        return None
    # FR-7.2: branch shows ONLY the branch — the worktree glyph moved to the
    # dedicated `worktree` segment.
    return _first_fitting([f"{theme.c('GREY')}[{branch}]{RESET}"], avail)


def seg_dirty(data, avail, theme):
    mark = _dirty_mark(data.get("dirty", "clean"), theme)
    return _first_fitting([mark], avail) if mark else None


def _trunc_cols(s, limit):
    """Truncate s to at most `limit` display columns, appending `…` if cut.
    Column-aware (uses char_width) so a wide/multibyte name can't blow the budget."""
    if sum(char_width(c) for c in s) <= limit:
        return s
    out, width = [], 0
    for c in s:
        cw = char_width(c)
        if width + cw > limit - 1:          # reserve one column for the ellipsis
            break
        out.append(c)
        width += cw
    return "".join(out) + "…"


def seg_worktree(data, avail, theme):
    # `worktree` names the ACTIVE linked worktree the session sits in — never a
    # list. Mirrors `dirty`'s "absence is the neutral state" convention: hidden
    # outside a repo. On the main checkout it shows a dimmed, struck `⎇ wt`
    # placeholder — GREY (not just strikethrough) so it stays distinct from the
    # cyan active form even on terminals that don't render SGR-9.
    if not data.get("in_repo"):
        return None
    if not data.get("is_worktree"):
        return _first_fitting([f"{theme.c('GREY')}\033[9m⎇ wt{RESET}"], avail)
    name = _trunc_cols(data.get("wt_name") or "", 20)
    return _first_fitting([f"{theme.c('CYAN')}⎇ {name}{RESET}"], avail)


def seg_todo(data, avail, theme):
    state, text = data.get("todo_state"), data.get("todo_text")
    if not text:
        return None
    limit = avail - 4                      # room for icon + space + ellipsis
    if limit < 6:                          # too cramped to be useful -> hide
        return None
    if len(text) > limit:
        text = text[:limit - 1] + "…"
    if state == "in_progress":
        return f"📝 {theme.c('YELLOW')}{text}{RESET}"
    if state == "pending":
        return f"⏸  {theme.c('GREY')}{text}{RESET}"
    return None


# ── model row ────────────────────────────────────────────────────────────────
def seg_model(data, avail, theme):
    name = data.get("model_name") or data.get("model_id")
    if not name:
        return None
    return _first_fitting([f"{theme.c('CYAN')}{name}{RESET}"], avail)


def seg_time_ago(data, avail, theme):
    ago = data.get("ago")
    if not ago:
        return None
    return _first_fitting([f"{theme.c('WHITE')}{ago}{RESET}"], avail)


def seg_clock(data, avail, theme):
    return _first_fitting([f"⏰{data['clock']}"], avail)


def seg_effort(data, avail, theme):
    level = data.get("effort", "")
    if not level:
        return None
    # Unknown level (stale/future): no color on the word, all-grey ladder — a safe
    # degraded display. resolve_effort already strips "auto", so it never lands here.
    color, bar = theme.effort.get(level.lower(), ("", f"{theme.c('GREY')}▁▃▄▆█"))
    word = f"{color}{level}{RESET}"
    bars = f"🧠 {bar}{RESET}"
    if data.get("effort_auto"):
        # effortLevel is unset/auto in settings: flag the resolved level as
        # auto-chosen. The flag degrades [auto] -> * -> dropped as space tightens.
        variants = [f"{bars} {word} {theme.c('GREY')}[auto]{RESET}",
                    f"{bars} {color}{level}*{RESET}",
                    f"{bars} {word}",
                    bars]
    else:
        variants = [f"{bars} {word}", bars]
    return _first_fitting(variants, avail)


def seg_lines(data, avail, theme):
    s = (f"📃{BG_LIGHTGRAY}{theme.c('GREEN')}+{fmt_number(data['added'])}{RESET}"
         f"/{BG_LIGHTGRAY}{theme.c('RED')}-{fmt_number(data['removed'])}{RESET}")
    return _first_fitting([s], avail)


def seg_cost(data, avail, theme):
    return _first_fitting([f"🪙${float(data['cost']):.3f}"], avail)


def seg_total_time(data, avail, theme):
    return _first_fitting([f"💬{fmt_time_ms(data['total_ms'])}"], avail)


def seg_api_time(data, avail, theme):
    return _first_fitting([f"📡{fmt_time_ms(data['api_ms'])}"], avail)


# ── diagnostics row ──────────────────────────────────────────────────────────
def seg_render_time(data, avail, theme):    # status-line's own run time, SLO/SLA-colored
    t0 = data.get("t_start")
    if t0 is None:                      # not timed (e.g. direct builder calls) -> omit
        return None
    elapsed = time.perf_counter_ns() - t0
    color = pick_color(elapsed, theme.ramps["render_time"])
    return _first_fitting([f"⏱ {color}{fmt_duration(elapsed)}{RESET}"], avail)


def seg_dimensions(data, avail, theme):
    mark = "?" if data.get("dim_assumed") else ""
    return _first_fitting([f"{data['cols']}×{data['lines']}{mark}"], avail)


def seg_context(data, avail, theme):
    pct = int(data["context_pct"])
    color = pick_color(pct, theme.ramps["context"])
    pct_only = f"📊 {color}{pct}%{RESET}"
    # Measure in half-cells (5% each) and round up, so any pct > 0 shows >= ▌.
    halves = 0 if pct <= 0 else min(2 * CONTEXT_BAR_CELLS, math.ceil(pct / 5))
    full_n, half = divmod(halves, 2)
    bar_f = "█" * full_n + ("▌" if half else "")
    bar_e = "░" * (CONTEXT_BAR_CELLS - full_n - half)
    bar = f"{color}{bar_f}{theme.c('GREY')}{bar_e}{RESET}"
    mid = f"📊 {bar} {color}{pct}%{RESET}"
    full = f"📊 {bar} {color}{pct}% of {fmt_tokens(data['context_max'])}{RESET}"
    return _first_fitting([full, mid, pct_only], avail) or pct_only  # floor


def seg_chat_size(data, avail, theme):
    n = data.get("chat_bytes")
    if n is None:
        return None
    color = pick_color(n, theme.ramps["chat_size"])
    return _first_fitting([f"💾 {color}{fmt_bytes(n)}{RESET}"], avail)


def seg_memory(data, avail, theme):
    n = data.get("mem_bytes")
    if n is None:
        return None
    return _first_fitting([f"🧮 {fmt_bytes(n)}"], avail)


def _reset_suffix(reset, detail):
    """Reset stamp at the requested detail: 'long' | 'short' | 'none'.
    Pure formatting of resets_at in local time — never compared against the
    clock, so a wrong system time or a timezone change can't change what shows."""
    if reset is None or detail == "none":
        return ""
    dt = datetime.fromtimestamp(reset)
    if detail == "long":
        return f" (↺ {dt.strftime('%b %d %H:%M')})"   # e.g. Jun 07 14:10
    return f" (↺ {dt.strftime('%m-%d %H:%M')})"        # e.g. 06-07 14:10


def _rate_str(rate_limits, detail, theme):
    # Show every bucket that reports a percentage. Visibility never depends on
    # the clock — the reset stamp is shown only when there's room (via detail),
    # so timezone shifts / clock skew can't make a bucket vanish.
    parts = []
    for key in sorted(rate_limits):
        info = rate_limits[key] or {}
        pct = info.get("used_percentage")
        if pct is None:
            continue
        reset = info.get("resets_at")
        if reset is not None:
            reset = int(reset)
        color = rate_color(pct, theme)
        suffix = _reset_suffix(reset, detail)
        parts.append(f"{rate_key_label(key)}: {color}{round(float(pct))}%{RESET}{suffix}")
    return "⚡ " + " | ".join(parts) if parts else None


def seg_rate_limits(data, avail, theme):
    rate_limits = data.get("rate_limits")
    if not rate_limits:
        return None
    return _first_fitting([_rate_str(rate_limits, "long", theme),
                           _rate_str(rate_limits, "short", theme),
                           _rate_str(rate_limits, "none", theme)], avail)


# ═══ Segment registry — key -> builder(data, avail, theme) ═══════════════════
# Editable surface (SEGMENTS + LAYOUT) is at the top of the file; this registry
# (key -> builder function) stays next to the builders it wires up.
BUILDERS = {
    "path": seg_path, "branch": seg_branch, "worktree": seg_worktree,
    "dirty": seg_dirty, "todo": seg_todo,
    "model": seg_model, "time_ago": seg_time_ago, "clock": seg_clock,
    "effort": seg_effort, "lines": seg_lines, "cost": seg_cost,
    "total_time": seg_total_time, "api_time": seg_api_time,
    "render_time": seg_render_time, "dimensions": seg_dimensions, "context": seg_context,
    "chat_size": seg_chat_size, "memory": seg_memory,
    "rate_limits": seg_rate_limits,
}


def make_external_builder(spec):
    """Wrap an ExtSpec as a seg_x(data, avail, theme)-shaped builder so pack_line
    treats it exactly like a built-in. theme is unused (the provider colors itself)."""
    def _builder(data, avail, theme):
        return run_external(spec, data, avail)
    return _builder


def _builders_for(cfg):
    """The built-in BUILDERS merged with one synthetic builder per external
    provider (keyed by id). External ids never collide with built-ins by design;
    if a user names one after a built-in, the external wins for that render."""
    builders = dict(BUILDERS)
    for spec in (cfg.external or []):
        builders[spec.id] = make_external_builder(spec)
    return builders


# ═══ Extractors ═══════════════════════════════════════════════════════════════
def _to_int(s):
    """Parse a stripped string to int, or None on empty/non-numeric input."""
    try:
        return int(s) if s else None
    except ValueError:
        return None


def terminal_size(env):
    """Resolve (cols, lines, assumed). Fallback chain, first hit wins per dimension:
      1. STATUSLINE_COLS / STATUSLINE_LINES env
      2. COLUMNS / LINES env
      3. stty size      (via /dev/tty)
      4. tput cols/lines (via /dev/tty — macOS / setups where stty size is absent)
      5. assumed 200x40 default (assumed=True)"""
    def _int(*keys):
        for k in keys:
            v = env.get(k)
            if v and str(v).isdigit() and int(v) > 0:
                return int(v)
        return None

    cols = _int("STATUSLINE_COLS", "COLUMNS")
    lines = _int("STATUSLINE_LINES", "LINES")
    if cols is None or lines is None:
        # One controlling-tty open serves both probes: stty first, then tput as the
        # macOS/terminfo fallback (_run closes over `tty` intentionally).
        try:
            with open("/dev/tty") as tty:
                def _run(*cmd):
                    return subprocess.run(list(cmd), stdin=tty, capture_output=True,
                                          text=True, timeout=1).stdout
                size = _run("stty", "size").split()
                if len(size) == 2:
                    lines = lines or int(size[0])
                    cols = cols or int(size[1])
                if cols is None or lines is None:
                    cols = cols or _to_int(_run("tput", "cols").strip())
                    lines = lines or _to_int(_run("tput", "lines").strip())
        except Exception:
            pass
    assumed = False
    if cols is None:
        cols, assumed = 200, True
    if lines is None:
        lines, assumed = 40, True
    return cols, lines, assumed


def _branch_from_porcelain(header):
    """Extract the branch from a `git status --porcelain --branch` header line
    (the `## ...` line). Returns "" for a detached HEAD, matching the old
    `git branch --show-current` behaviour. Git forbids ".." in refnames, so the
    "..." upstream separator can never collide with a branch name."""
    if not header.startswith("## "):
        return ""
    rest = header[3:]
    if rest.startswith("HEAD (no branch)"):                       # detached
        return ""
    for prefix in ("No commits yet on ", "Initial commit on "):   # unborn branch
        if rest.startswith(prefix):
            return rest[len(prefix):].strip()
    return rest.split("...", 1)[0].strip()                        # branch[...upstream]


# The single shared git probe result. `branch`, `dirty`, and `worktree` are
# independent segments but all read from one GitSnapshot — no duplicated git
# querying. wt_name is the active linked-worktree's directory basename ("" on
# the main checkout or outside a repo).
GitSnapshot = namedtuple("GitSnapshot", "in_repo branch dirty is_worktree wt_name")


def _git_worktree_info(work_dir):
    """(in_repo, is_worktree, name) from ONE `git rev-parse`. is_worktree is True
    when work_dir sits in a linked worktree (git-dir != git-common-dir). name is
    that worktree directory's basename (from --show-toplevel), only when in a
    linked worktree; "" otherwise. Outside any repo → (False, False, "")."""
    out = subprocess.run(
        ["git", "-C", work_dir, "rev-parse",
         "--git-dir", "--git-common-dir", "--show-toplevel"],
        capture_output=True, text=True).stdout
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False, False, ""                 # not a git repo
    is_worktree = lines[0] != lines[1]          # git-dir != git-common-dir
    top = lines[2] if len(lines) >= 3 else ""
    name = os.path.basename(top.rstrip("/")) if (is_worktree and top) else ""
    return True, is_worktree, name


def _git_cache_path(work_dir, env):
    """Per-work_dir cache file for the worktree probe under …/ai-kit/git/
    (shares `_cache_base` with the external-segment cache)."""
    key = hashlib.sha1(os.path.abspath(work_dir).encode()).hexdigest()[:16]
    return os.path.join(_cache_base(env), "git", key)


def _worktree_info_cached(work_dir, ttl, env):
    """_git_worktree_info wrapped in an on-disk TTL cache — the worktree rev-parse
    rarely changes, so it is cached ~ttl s keyed by work_dir. ttl <= 0 always
    misses (forces a fresh rev-parse every render). Cache I/O is best-effort."""
    path = _git_cache_path(work_dir, env)
    if ttl > 0:
        try:
            if time.time() - os.stat(path).st_mtime < ttl:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                return d["in_repo"], d["is_worktree"], d["wt_name"]
        except (OSError, ValueError, KeyError):
            pass
    info = _git_worktree_info(work_dir)
    if ttl > 0:                                     # ttl<=0 never reads, so never write
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"in_repo": info[0], "is_worktree": info[1], "wt_name": info[2]}, f)
        except OSError:
            pass
    return info


def git_snapshot(work_dir, untracked=True, want_worktree=True, ttl=_GIT_CACHE_TTL, env=None):
    """The single git probe behind the `branch`, `dirty`, and `worktree` segments.

    Returns GitSnapshot(in_repo, branch, dirty, is_worktree, wt_name). `branch`
    and `dirty` come from one always-fresh `git status --porcelain --branch`; the
    worktree rev-parse is cached ~`ttl`s on disk (it rarely changes). Each call is
    gated on what the caller will actually render:
      * untracked=False adds --untracked-files=no, skipping git's untracked-file
        walk (the slow part of `status` on large trees). Pass it when `dirty` is
        off; dirty then can't report "untracked" (only modified/clean).
      * want_worktree=False skips the rev-parse (and its cache) entirely; in_repo,
        is_worktree, wt_name stay at their defaults. Pass it when `worktree` is off."""
    env = env or {}
    status_args = ["status", "--porcelain", "--branch"]
    if not untracked:
        status_args.append("--untracked-files=no")
    out = subprocess.run(["git", "-C", work_dir, *status_args],
                         capture_output=True, text=True).stdout.splitlines()
    branch = _branch_from_porcelain(out[0] if out else "")
    changes = out[1:]   # change lines follow the `## <branch>` header
    if any(ln.startswith(("??", "A", "D")) or ln.startswith(" D") for ln in changes):
        dirty = "untracked"
    elif any(ln.strip() for ln in changes):
        dirty = "modified"
    else:
        dirty = "clean"
    in_repo, is_worktree, wt_name = False, False, ""
    if want_worktree:
        in_repo, is_worktree, wt_name = _worktree_info_cached(work_dir, ttl, env)
    return GitSnapshot(in_repo, branch, dirty, is_worktree, wt_name)


# ── Process RSS (cross-platform) ──────────────────────────────────────────────
# Platform probe: Linux → /proc readers; macOS/other → `ps` readers; any read
# failure → None (the segment hides). Three facts per pid — command name, parent
# pid, resident memory (kB) — exposed by six thin readers (_comm/_ppid/_rss_kb ×
# _via_proc/_via_ps). proc_rss_bytes picks a backend by the probe and walks the
# parent chain, returning RSS ONLY on a confirmed `claude` ancestor — otherwise
# None, so it never reports a stray process (the wezterm <10mb bug). The readers
# return comm verbatim; proc_rss_bytes is the single basename-normalization point.
def _comm_via_proc(pid):
    try:
        with open(f"/proc/{pid}/comm") as f:
            return f.read().strip()
    except OSError:
        return None


def _ppid_via_proc(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            return int(f.read().split()[3])
    except (OSError, IndexError, ValueError):
        return None


def _rss_kb_via_proc(pid):
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except (OSError, IndexError, ValueError):
        return None
    return None


def _ps_field(pid, field):
    """One `ps -o <field>= -p <pid>` value as a stripped string, or None."""
    try:
        out = subprocess.run(["ps", "-o", f"{field}=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=1).stdout.strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def _comm_via_ps(pid):
    return _ps_field(pid, "comm")


def _ppid_via_ps(pid):
    return _to_int(_ps_field(pid, "ppid"))


def _rss_kb_via_ps(pid):
    return _to_int(_ps_field(pid, "rss"))


def proc_rss_bytes():
    """Resident memory (bytes) of the ancestor `claude` process, or None.

    Cross-platform via a capability probe: Linux /proc, else `ps`. Walk up the parent
    chain (bounded) and return RSS only on a `claude` match."""
    use_proc = os.path.isdir("/proc")
    comm_of = _comm_via_proc if use_proc else _comm_via_ps
    ppid_of = _ppid_via_proc if use_proc else _ppid_via_ps
    rss_kb_of = _rss_kb_via_proc if use_proc else _rss_kb_via_ps

    pid = os.getppid()
    for _ in range(8):
        name = comm_of(pid)
        if name is None:
            return None
        # `ps -o comm=` can return a full path on macOS; normalize here so both
        # backends compare the same bare name.
        if os.path.basename(name) == "claude":
            kb = rss_kb_of(pid)
            return kb * 1024 if kb is not None else None
        parent = ppid_of(pid)
        if parent is None or parent in (0, pid):
            return None
        pid = parent
    return None


def transcript_bytes(path):
    if not path or not os.path.isfile(path):
        return None
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def _iter_tool_uses(line_obj, names):
    # In real transcripts message.content is a list of blocks for tool turns but
    # a plain string for text turns — only iterate when it is a list of dicts.
    content = (line_obj.get("message") or {}).get("content")
    if not isinstance(content, list):
        return
    for item in content:
        if isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") in names:
            yield item


def _pick_from_tasks(tasks):
    """Choose the active task from a managed-Task list (creation order). Active =
    the last in_progress, else the first pending. Returns (state, text) or None."""
    in_prog = [t for t in tasks if t.get("status") == "in_progress"]
    if in_prog:
        return "in_progress", in_prog[-1].get("activeForm") or in_prog[-1].get("subject", "")
    pending = [t for t in tasks if t.get("status") == "pending"]
    if pending:
        return "pending", pending[0].get("subject", "")
    return None


def _pick_from_todos(todos):
    """Choose the active item from a TodoWrite snapshot. Active = the first
    in_progress, else the first pending. Returns (state, text) or None."""
    in_prog = [t for t in todos if t.get("status") == "in_progress"]
    if in_prog:
        return "in_progress", in_prog[0].get("activeForm", "")
    pending = [t for t in todos if t.get("status") == "pending"]
    if pending:
        return "pending", pending[0].get("content", "")
    return None


def _safe_session(s):
    """A session id is used as a single path component under the tasks/todos dir.
    Reject anything with a path separator or parent ref so it cannot escape that
    directory (path traversal)."""
    return bool(s) and not re.search(r"[/\\]|\.\.", s)


def _todo_from_tasks_dir(config_dir, session):
    """Read Claude's materialized managed-Task state: one <id>.json per task under
    <config_dir>/tasks/<session>/. Returns (state, text) when task files exist
    (authoritative — may be (None, None) if all are done), else None to try the
    next source. This is O(task count) — no transcript replay."""
    if not _safe_session(session):
        return None
    d = os.path.join(config_dir, "tasks", session)
    try:
        names = [n for n in os.listdir(d) if n.endswith(".json")]
    except OSError:
        return None
    if not names:
        return None
    # Sort by numeric id so creation order (and thus "last in_progress") is stable.
    tasks = []
    for n in sorted(names, key=lambda x: int(x[:-5]) if x[:-5].isdigit() else 0):
        try:
            with open(os.path.join(d, n)) as f:
                tasks.append(json.load(f))
        except (OSError, ValueError):
            continue
    return _pick_from_tasks(tasks) or (None, None)


def _todo_from_todos_dir(config_dir, session):
    """Read Claude's materialized TodoWrite snapshot: the most recent
    <config_dir>/todos/<session>*-agent-*.json (a single todos array). Returns
    (state, text) when such a file exists, else None to try the next source."""
    if not _safe_session(session):
        return None
    d = os.path.join(config_dir, "todos")
    try:
        names = [n for n in os.listdir(d)
                 if n.startswith(session) and "-agent-" in n and n.endswith(".json")]
    except OSError:
        return None
    if not names:
        return None
    latest = max(names, key=lambda n: os.path.getmtime(os.path.join(d, n)))
    try:
        with open(os.path.join(d, latest)) as f:
            todos = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(todos, list):
        return None
    return _pick_from_todos(todos) or (None, None)


def _todo_from_transcript(path):
    """Last-resort fallback: replay the transcript JSONL to reconstruct task /
    todo state. O(transcript size) — used only when no materialized state exists
    (e.g. running outside Claude Code, or an unrecognized on-disk layout)."""
    if not path or not os.path.isfile(path):
        return None, None

    tasks = []
    try:
        with open(path) as fh:
            todo_snapshots = []
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(obj, dict):
                    continue
                for tu in _iter_tool_uses(obj, ("TaskCreate", "TaskUpdate")):
                    inp = tu.get("input", {})
                    if tu["name"] == "TaskCreate":
                        tasks.append({
                            "id": len(tasks) + 1,
                            "subject": inp.get("subject", ""),
                            "activeForm": inp.get("activeForm") or inp.get("subject", ""),
                            "status": "pending",
                        })
                    else:
                        tid = str(inp.get("taskId"))
                        for t in tasks:
                            if str(t["id"]) == tid and inp.get("status"):
                                t["status"] = inp["status"]
                for tu in _iter_tool_uses(obj, ("TodoWrite",)):
                    todo_snapshots.append(tu.get("input", {}).get("todos", []))
    except OSError:
        return None, None

    if tasks:
        return _pick_from_tasks(tasks) or (None, None)
    if todo_snapshots:
        return _pick_from_todos(todo_snapshots[-1]) or (None, None)
    return None, None


def current_todo(path, session=None, config_dir=None):
    """Return (state, text) for the active TODO, or (None, None).

    Prefer Claude's materialized state on disk — the managed-Task files, then a
    TodoWrite snapshot — which is cheap (O(task count)) and authoritative. Only
    when neither exists do we replay the transcript (O(transcript size)). Without
    session/config_dir (direct/test calls) we go straight to the transcript."""
    if session and config_dir:
        for source in (_todo_from_tasks_dir, _todo_from_todos_dir):
            got = source(config_dir, session)
            if got is not None:
                return got
    return _todo_from_transcript(path)


# ═══ Packing + render ════════════════════════════════════════════════════════
def safe_build(key, data, avail, theme, failed, builders=None):
    """Invoke one segment builder in isolation. On ANY exception, record `key`
    in the shared `failed` set and return a width-bounded warning marker instead
    of propagating — so a single bad segment can never blank the whole bar. The
    marker shows the segment name when it fits `avail`, else just the icon.
    `builders` defaults to the built-in BUILDERS registry."""
    builders = builders if builders is not None else BUILDERS
    try:
        return builders[key](data, avail, theme)
    except Exception:                              # noqa: BLE001 — isolation is the point
        failed.add(key)
        named = f"{_WARN}⚠{key}{RESET}"
        if visible_width(named) <= avail:
            return named
        return f"{_WARN}⚠{RESET}"


def pack_line(keys, data, cols, cfg=None, theme=None, failed=None, builders=None):
    """Best-fit pack enabled segments into cols - RIGHT_MARGIN.

    For each key (left->right), compute the space available at this position
    (budget - used - separator), ask the builder for content sized to it, and
    keep it if it is non-empty and fits — else skip it and keep trying the rest.
    Pinned segments are always kept. Order is priority: leftmost survive.
    `builders` carries the merged built-in + external map; defaults to that
    derived from cfg."""
    cfg = cfg or default_config()
    theme = theme or build_theme(cfg)
    failed = failed if failed is not None else set()
    builders = builders if builders is not None else _builders_for(cfg)
    budget = cols - RIGHT_MARGIN
    sep_w = visible_width(SEP)
    kept, used = [], 0
    for key in keys:
        if not cfg.segments.get(key, False):   # flag gate: not built => no compute
            continue
        sep = sep_w if kept else 0
        avail = budget - used - sep
        s = safe_build(key, data, max(avail, 0), theme, failed, builders)
        if not s:
            continue
        if key in PINNED or visible_width(s) <= avail:
            kept.append(s)
            used += visible_width(s) + sep
    return SEP.join(kept)


def diagnostic_line(failed):
    """One line naming the segments that crashed this render, pointing at the
    doctor. Returns None when nothing failed (no cost on the happy path)."""
    if not failed:
        return None
    names = ", ".join(sorted(failed))
    n = len(failed)
    noun = "segment" if n == 1 else "segments"
    return (f"{_WARN}⚠ {n} {noun} failed: {names} — "
            f"run the doctor: {_doctor_cmd()}{RESET}")


def render(data, cols, lines, cfg=None, theme=None):
    """Render up to len(cfg.layout) lines, gated by terminal height and width.
    A trailing diagnostic line is appended only when a builder crashed."""
    cfg = cfg or default_config()
    theme = theme or build_theme(cfg)
    builders = _builders_for(cfg)
    failed = set()
    out = []
    for ln in cfg.layout:
        if lines < ln.min_rows:
            continue
        packed = pack_line(ln.segments, data, cols, cfg, theme, failed, builders)
        if packed:
            out.append(packed)
    diag = diagnostic_line(failed)
    if diag:
        out.append(diag)
    return out


# ═══ HOW TO CUSTOMIZE ════════════════════════════════════════════════════════
# Three knobs at the top of the file drive everything:
#
#   SEGMENTS  — on/off flag per segment. False hides it everywhere and its
#               builder is never called (saves compute). Keep "path" True.
#   LAYOUT    — the template: a list of Line(min_rows, [segment keys]). Key order
#               in each list is LEFT->RIGHT priority; leftmost survive when the
#               terminal is narrow. min_rows gates the whole row by terminal rows.
#   BUILDERS  — maps each segment key to its builder(data, avail, theme) function.
#
# How show/hide is decided: the packer (pack_line) is the authority. It offers
# each builder the space available at its spot (avail) and keeps the result only
# if it is non-empty and fits; otherwise it skips it and tries the next. A
# builder cooperates by auto-deprioritizing itself — returning a compact variant
# for a small avail, or None when even its smallest variant will not fit.
# PINNED segments ("path", "context") are kept even if they overflow.
#
# Available segments (key -> what it shows):
#   path         working dir (~-collapsed; basename if long)     [pinned]
#   branch       git branch name
#   worktree     ⎇ active linked-worktree name (struck ⎇ wt on the main checkout)
#   dirty        ✗ untracked / ~ modified marker
#   todo         active TODO / task (truncated to fit)
#   model        model display name
#   time_ago     time since last transcript activity
#   clock        ⏰ wall clock HH:MM
#   effort       🧠 effort ramp bar (+ level word when room)
#   lines        📃 +added/-removed line counts
#   cost         🪙 session cost in USD (off by default)
#   total_time   💬 total session duration
#   api_time     📡 total API duration
#   render_time  ⏱ status-line.py's own run time, SLO/SLA-colored via the
#                render_time ramp
#   dimensions   terminal COLS×ROWS (off by default; debug)
#   context      📊 context-window usage bar + percent           [pinned]
#   chat_size    💾 transcript file size
#   memory       🧮 claude process RSS
#   rate_limits  ⚡ rate-limit buckets (+ reset times when room)
#
# Common edits:
#   * Toggle a segment:       flip its SEGMENTS[...] value.
#   * Reorder within a line:  move its key within that Line's list.
#   * Move to another line:   cut its key from one Line list, paste into another.
#   * Re-enable a removed one: ensure (a) SEGMENTS[key] is True, (b) the key is
#                             in some LAYOUT line, and (c) the key is in BUILDERS.
#                             All three are required for it to show.
#   * Add a NEW segment:
#       1. Write a builder:  def seg_foo(data, avail, theme):
#              if no_data: return None
#              return _first_fitting([rich_form, compact_form], avail)
#          (return None to hide; read what you need from `data`; let the builder
#          auto-deprioritize via _first_fitting on the avail it is offered).
#       2. Register it:      add  "foo": seg_foo  to BUILDERS.
#       3. Place it:         add  "foo"  to a LAYOUT line where you want it.
#       4. Flag it:          add  "foo": True  to SEGMENTS.
#       5. Test it:          add a case in tests/test_status_line.py.


# ═══ Entry point ══════════════════════════════════════════════════════════════
def resolve_effort(raw, env):
    """The *resolved* effort level (low..max) as a normalized lowercase string, or "".

    This is the live per-turn level the API reported, read from raw["effort"]["level"]
    (CLAUDE_EFFORT env as a fallback). It is never "auto" — auto is a *setting*, detected
    separately from disk by effort_setting_is_auto. A stray "auto" in the resolved field
    (transition states, env misuse) is normalized away so it can't reach the level table."""
    level = ((raw.get("effort") or {}).get("level") or env.get("CLAUDE_EFFORT", ""))
    level = level.strip().lower()
    return "" if level == "auto" else level


def effort_setting_is_auto(work_dir, home):
    """True when the effort *setting* is auto — i.e. `effortLevel` is absent (or
    literally "auto") across the settings chain.

    Precedence high->low: the project's .claude/settings.local.json, then
    .claude/settings.json, then ~/.claude/settings.json. The first file that defines
    `effortLevel` decides (explicit level -> not auto); if none define it, it's auto."""
    for path in (os.path.join(work_dir, ".claude", "settings.local.json"),
                 os.path.join(work_dir, ".claude", "settings.json"),
                 os.path.join(home, ".claude", "settings.json")):
        try:
            with open(path) as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(cfg, dict) and "effortLevel" in cfg:
            return str(cfg["effortLevel"]).strip().lower() == "auto"
    return True


def build_data(raw, env, segments=None, t_start=None, git_ttl=_GIT_CACHE_TTL):
    """Gather everything the builders read.

    Expensive probes — git (`git_snapshot`), the transcript parse (`current_todo`),
    process RSS (`proc_rss_bytes`), the effort-settings/file stats — run ONLY
    when their segment is enabled in `segments`. A disabled segment costs nothing
    to *compute*, not just nothing to *render*: this is the compute half of the
    same flag gate `pack_line` applies to rendering. `segments=None` computes
    everything (used by tests and as a degrade-safe default)."""
    def want(key):
        return segments is None or segments.get(key, False)

    model = raw.get("model") or {}
    cost = raw.get("cost") or {}
    ctx = raw.get("context_window") or {}
    workspace = raw.get("workspace") or {}
    work_dir = os.path.abspath(workspace.get("current_dir") or ".")
    transcript = raw.get("transcript_path") or ""
    home = env.get("HOME", "")
    # Session id + Claude config dir locate the materialized task/todo state that
    # current_todo prefers over replaying the transcript. session_id is provided
    # in the status-line input; it also equals the transcript file's basename.
    session = raw.get("session_id") or (
        os.path.splitext(os.path.basename(transcript))[0] if transcript else "")
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")

    cols, lines, assumed = terminal_size(env)

    # One shared git_snapshot feeds branch + dirty + worktree, gated as a unit on
    # any of the three git segments being enabled. Each probe inside is itself
    # gated: the untracked walk on the `dirty` segment, the worktree rev-parse on
    # the `worktree` segment (skipped entirely when that segment is off).
    branch, dirty, is_worktree, wt_name, in_repo = "", "clean", False, "", False
    if want("branch") or want("dirty") or want("worktree"):
        snap = git_snapshot(work_dir, untracked=want("dirty"),
                            want_worktree=want("worktree"), ttl=git_ttl, env=env)
        branch, dirty, is_worktree = snap.branch, snap.dirty, snap.is_worktree
        wt_name, in_repo = snap.wt_name, snap.in_repo

    ago = ""
    if want("time_ago") and transcript and os.path.isfile(transcript):
        ago = fmt_ago(int(time.time()) - int(os.path.getmtime(transcript)))

    effort = resolve_effort(raw, env)
    effort_auto = effort_setting_is_auto(work_dir, home) if want("effort") else False
    todo_state, todo_text = (current_todo(transcript, session, claude_dir)
                             if want("todo") else (None, None))

    data = {
        "raw": raw,
        "model_name": model.get("display_name", ""),
        "model_id": model.get("id", "unknown"),
        "effort": effort,
        "effort_auto": effort_auto,
        "work_dir": work_dir,
        "home": home,
        "branch": branch, "dirty": dirty, "is_worktree": is_worktree,
        "wt_name": wt_name, "in_repo": in_repo,
        "clock": time.strftime("%H:%M"), "ago": ago,
        # `or 0` (not get's default) so a PRESENT-but-null field — what a fresh
        # /clear session sends before any tokens/cost accrue — coalesces to 0
        # instead of raising on int()/math and blanking the whole bar.
        "added": cost.get("total_lines_added") or 0,
        "removed": cost.get("total_lines_removed") or 0,
        "cost": cost.get("total_cost_usd") or 0,
        "total_ms": cost.get("total_duration_ms") or 0,
        "api_ms": cost.get("total_api_duration_ms") or 0,
        "context_pct": int(ctx.get("used_percentage") or 0),
        "context_max": ctx.get("context_window_size") or 0,
        "chat_bytes": transcript_bytes(transcript) if want("chat_size") else None,
        "mem_bytes": proc_rss_bytes() if want("memory") else None,
        "rate_limits": raw.get("rate_limits") or {},
        "todo_state": todo_state, "todo_text": todo_text,
        "dim_assumed": assumed,
        "cols": cols, "lines": lines,
        "t_start": t_start,
    }
    return data, cols, lines


# ═══ CLI introspection ═══════════════════════════════════════════════════════
_NO_CHECK = object()   # sentinel: --check flag absent (vs. present with no FILE)

_ENV_HELP = """\
Environment variables:
  CC_AI_KIT_CONFIG         path to the TOML config file
  CC_AI_KIT_SEGMENT_<KEY>  per-segment bool toggle; KEY is the upper-cased
                           segment name (PATH, MODEL, COST, CONTEXT, ...).
                           true:  1 true t y yes on    false: 0 false f n no off
  CC_AI_KIT_GIT_TTL        int; seconds the git worktree probe is cached. Wins
                           over [git] cache_ttl (default 5).
  CC_AI_KIT_SEGMENTS_DIR   external drop-in segments directory (default
                           ${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments)
  CC_AI_KIT_EXTERNAL_TTL   default cache TTL (seconds) for external segments

Config precedence (low -> high): built-in defaults < TOML file < env."""


def cmd_print_config(cfg, env):
    """Resolved config as pretty JSON (no rendering)."""
    # The top-level external `ttl`/`dir` are the GLOBAL resolved defaults
    # (defaults < [external] file < env) — resolved the same way load_config
    # does, so they're meaningful even when zero providers are discovered and
    # are never confused with a single provider's per-header `ttl=` override
    # (those appear per-entry in the "providers" array below). `dir` is the
    # PROVIDERS directory (where scripts live), NOT the XDG cache dir.
    ext_providers = cfg.external or []
    ext_dir, ext_ttl = _resolve_external(_load_toml(config_path(env)), env)
    return json.dumps({
        "segments": cfg.segments,
        "layout": [{"min_rows": ln.min_rows, "segments": ln.segments}
                   for ln in cfg.layout],
        "palette": cfg.palette,
        "ramps": cfg.ramps,
        "git": cfg.git or {},
        "external": {
            "ttl": ext_ttl,
            "dir": ext_dir,
            "providers": [
                {"id": s.id, "path": s.path, "line": s.line,
                 "position": _position_str(s.position),
                 "timeout": s.timeout, "ttl": s.ttl}
                for s in ext_providers
            ],
        },
    }, indent=2)


def validate_config_file(path, env):
    """Return a list of human-readable error strings for the config at path
    (empty list = valid). Checks: parseability, unknown segment keys, unknown
    palette keys, palette color values, [[line]] segments that are not real
    builders, and [ramp.*] band names / thresholds / colors."""
    if tomllib is None:
        return ["tomllib unavailable (Python < 3.11): cannot validate"]
    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        return [f"{path}: no such file"]
    except (OSError, tomllib.TOMLDecodeError) as e:
        return [f"{path}: {e}"]
    errors = []
    defaults = default_config()
    ext_dir, ext_ttl = _resolve_external(raw, env)
    ext_ids = {s.id for s in discover_external(ext_dir, ext_ttl, env)}
    known_segments = set(defaults.segments) | ext_ids
    for k in (raw.get("segments") or {}):
        if k not in known_segments:
            errors.append(f"unknown segment key: {k}")
    for k in (raw.get("palette") or {}):
        if k not in _PALETTE_DEFAULTS:
            errors.append(f"unknown palette key: {k}")
    for name, value in (raw.get("palette") or {}).items():
        if name in _PALETTE_DEFAULTS and parse_color(str(value), palette=None) is None:
            errors.append(f"bad palette color: {name} = {value!r}")
    for i, line in enumerate(raw.get("line") or []):
        for seg in line.get("segments", []):
            if seg not in BUILDERS and seg not in ext_ids:
                errors.append(f"line[{i}] references unknown segment: {seg}")
    resolved_palette = _resolve_palette(
        {k: str(v) for k, v in (raw.get("palette") or {}).items()
         if k in _PALETTE_DEFAULTS})
    for band, table in (raw.get("ramp") or {}).items():
        if band not in _RAMP_DEFAULTS:
            errors.append(f"unknown ramp: {band}")
            continue
        if not isinstance(table, dict):
            errors.append(f"ramp [{band}] must be a table")
            continue
        for thr, spec in table.items():
            try:
                _parse_threshold(thr)
            except ValueError:
                errors.append(f"ramp [{band}] bad threshold: {thr!r}")
            if parse_color(str(spec), resolved_palette) is None:
                errors.append(f"ramp [{band}] bad color: {spec!r}")
    for k, v in (raw.get("git") or {}).items():
        problem = _git_key_problem(k, v)
        if problem == "unknown":
            errors.append(f"unknown [git] key: {k}")
        elif problem == "bad_ttl":
            errors.append(f"[git] cache_ttl must be an integer, got {v!r}")
    ext = raw.get("external")
    if ext is not None:
        if not isinstance(ext, dict):
            errors.append("[external] must be a table")
        else:
            for k in ext:
                if k not in ("ttl", "dir"):
                    errors.append(f"unknown [external] key: {k}")
            if "ttl" in ext and (not isinstance(ext["ttl"], int) or isinstance(ext["ttl"], bool)):
                errors.append(f"[external] ttl must be an integer, got {ext['ttl']!r}")
            if "dir" in ext and not isinstance(ext["dir"], str):
                errors.append(f"[external] dir must be a string, got {ext['dir']!r}")
    return errors


# A representative status JSON for the doctor's dry render. Self-contained (no
# fixture file): exercises every default builder so one that raises is surfaced.
_DOCTOR_SAMPLE = {
    "model": {"display_name": "Opus 4.8", "id": "claude-opus-4-8"},
    "cost": {"total_lines_added": 12, "total_lines_removed": 3,
             "total_cost_usd": 0.0123, "total_duration_ms": 45000,
             "total_api_duration_ms": 12000},
    "context_window": {"used_percentage": 42, "context_window_size": 200000},
    "workspace": {"current_dir": "."},
    "transcript_path": "",
    "session_id": "doctor-sample",
    "rate_limits": {},
    "effort": {"level": "high"},
}


def _dry_render_failures(cfg, theme, env):
    """Run EVERY builder once against the sample input — including segments that
    are disabled or absent from the layout — and return the set of segment keys
    whose builder raised. Dry-rendering only the enabled+reachable subset would
    let a broken disabled builder (e.g. `cost`) pass the doctor and then crash
    the moment the user enables it, which is exactly the failure class the doctor
    exists to catch. `safe_build` (not `pack_line`'s flag gate) does the catching,
    so we invoke it directly for each key.

    Note: this catches builders that crash on *valid* input. A builder that only
    raises on a missing/malformed key won't be surfaced by this happy-path sample."""
    failed = set()
    data, _cols, _lines = build_data(
        dict(_DOCTOR_SAMPLE), env, cfg.segments, time.perf_counter_ns(),
        git_ttl=(cfg.git or {}).get("cache_ttl", _GIT_CACHE_TTL))
    for key in BUILDERS:
        safe_build(key, data, 200, theme, failed)
    return failed


def cmd_doctor(env):
    """Validate the resolved config AND dry-render every segment builder (not just
    the enabled ones). Prints a report; returns process exit code (0 healthy, 1 if
    any problem)."""
    path = config_path(env)
    errors = []
    if os.path.exists(path):
        errors = [f"{path}: {e}" for e in validate_config_file(path, env)]
    failed = set()
    cfg = load_config(env)                         # never raises (degrades to defaults)
    try:
        theme = build_theme(cfg)
        failed = _dry_render_failures(cfg, theme, env)
    except Exception as e:                         # noqa: BLE001
        errors.append(f"render pipeline crashed: {e!r}")
    for e in errors:
        print(e, file=sys.stderr)
    for key in sorted(failed):
        print(f"segment '{key}' raised during render", file=sys.stderr)
    if errors or failed:
        print(f"after fixing, re-run: {_doctor_cmd()}", file=sys.stderr)
        return 1
    print(f"{path}: OK — config valid, all {len(BUILDERS)} segments render cleanly")
    return 0


def cmd_check(path, env):
    """Validate a config file; print result. Return process exit code (0/1)."""
    path = path or config_path(env)
    errors = validate_config_file(path, env)
    if errors:
        for e in errors:
            print(f"{path}: {e}", file=sys.stderr)
        return 1
    print(f"{path}: OK")
    return 0


def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="status-line.py",
        description="Claude Code status line. With no flags, reads the status "
                    "JSON on stdin and renders up to three ANSI lines.",
        epilog=_ENV_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--print-config", action="store_true",
                   help="resolve config (defaults < file < env), print it as "
                        "JSON, and exit (does not read stdin)")
    p.add_argument("--check", nargs="?", const=None, default=_NO_CHECK,
                   metavar="FILE",
                   help="validate a config file (default: the resolved path) "
                        "and exit non-zero if invalid")
    p.add_argument("--doctor", action="store_true",
                   help="validate the config AND dry-render every segment to "
                        "surface a builder that raises; exit non-zero if unhealthy")
    return p.parse_args(argv)


def safe_render(raw, env, cfg, theme, t_start):
    """Build data and render; on ANY unexpected failure return a single
    diagnostic line instead of a blank bar. Never raises. This is the backstop
    above safe_build's per-segment isolation (covers build_data itself)."""
    try:
        data, cols, lines = build_data(
            raw, env, cfg.segments, t_start,
            git_ttl=(cfg.git or {}).get("cache_ttl", _GIT_CACHE_TTL))
        return render(data, cols, lines, cfg, theme)
    except Exception:                              # noqa: BLE001 — never blank the bar
        return [f"{_WARN}⚠ status-line error — "
                f"run the doctor: {_doctor_cmd()}{RESET}"]


def main():
    t0 = time.perf_counter_ns()        # for the optional `render_time` self-timing segment
    args = parse_args(sys.argv[1:])
    if args.check is not _NO_CHECK:
        sys.exit(cmd_check(args.check, os.environ))
    if args.doctor:
        sys.exit(cmd_doctor(os.environ))
    cfg = load_config(os.environ)
    theme = build_theme(cfg)
    if args.print_config:
        print(cmd_print_config(cfg, os.environ))
        return
    try:
        raw = json.load(sys.stdin)
    except (ValueError, OSError):
        raw = {}
    print("\n".join(safe_render(raw, os.environ, cfg, theme, t0)))


if __name__ == "__main__":
    main()
