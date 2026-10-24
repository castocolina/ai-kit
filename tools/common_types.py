"""Data tables and type declarations for the Phase 23 D-02 status-line split."""
# pyright: strict

import hashlib
import math
import os
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from common_render import Theme  # pylint: disable=cyclic-import  # annotation-only edge

# Environment dict: a snapshot of os.environ captured once in main() (D6).
# Mapping[str, str] covers both plain dict and os.environ (_Environ[str]).
Env = Mapping[str, str]

# ═══ 1. DEFAULTS — data-only: segment/layout/palette/ramp tables + type decls ═




# Per-segment on/off. Set False to hide a segment entirely: its builder is never
# called, so its data is never read and the matching lazy probe (git/transcript/
# RSS/etc.) never runs — a disabled segment costs nothing. Invariant: keep "path"
# True so the identity line always emits.
SEGMENTS = {
    # identity line
    "path": True, "git_branch": True, "git_dirty": True, "alt_git_worktree": False,
    # model row (kept lean by design — todo alone can eat the row's width, so
    # every optional alt_ variant prefers the diagnostics row instead)
    "model": True, "effort": True, "context": True, "todo": True,
    "alt_time_ago": False, "alt_time_clock": False,
    "alt_cost": False, "alt_time_session": False, "alt_time_api": False,
    # diagnostics row (alt_term_dimensions is a debug aid — off by default)
    "render_time": True, "slowest": True, "alt_term_dimensions": False,
    "lines": False,
    "chat_size": True, "alt_process_memory": False,
    "alt_h_rate_limit": False, "alt_w_rate_limit": False,
}


# Identity-line tuning.
PATH_MAX_LEN = 50      # fixed budget for path's two structural variants (full path, parent/name)


CONTEXT_BAR_CELLS = 10  # context bar width; ▌ half-cells give 5% resolution


# Packing: reserve a few cols so emoji-width miscounts don't wrap the line.
RIGHT_MARGIN = 4


SEP = " | "


# One Line per row. `segments` lists keys LEFT->RIGHT; leftmost = highest
# priority (kept first when space is tight). `min_rows` gates the whole row by
# terminal height. Reorder = move a key within a list; move between rows = cut
# and paste a key; hide = flip its SEGMENTS flag.
class Line(NamedTuple):
    """One display row: minimum terminal height to show it + ordered segment keys."""

    min_rows: int
    segments: list[str]


LAYOUT = [
    Line(0,  ["path", "git_branch", "alt_git_worktree", "git_dirty"]),
    Line(20, ["model", "effort", "context", "todo"]),
    Line(30, ["render_time", "slowest", "alt_term_dimensions",
              "alt_time_ago", "alt_time_clock", "lines", "alt_cost",
              "alt_time_session", "alt_time_api",
              "chat_size", "alt_process_memory", "alt_h_rate_limit", "alt_w_rate_limit"]),
]


PINNED = {"path", "context"}   # always rendered even if they overflow the budget


# Meta-segments: they report the whole render, not a single builder, so the
# `slowest` readout never names them as the culprit (its own output + render_time).
SLOWEST_META = frozenset({"slowest", "render_time"})


# Resolved configuration: the result of merging internal defaults < TOML file <
# env. `segments` is a {key: bool} dict, `layout` a list[Line], `palette` a
# {NAME: "sgr;params"} dict of overrides (empty = no override), `ramps` a
# {band: {threshold: colorspec}} dict of whole-band overrides (empty = no
# override). External drop-in segments are E4c and are intentionally not part of
# this type yet.
# Scalar behaviour knobs that aren't segments/colors. The worktree feature
# migrated to the `segments.alt_git_worktree` toggle (see SEGMENTS); `[git]` now carries
# `cache_ttl` (seconds) — how long the shared probe_git_snapshot worktree probe is
# cached. Precedence: this default < TOML `[git] cache_ttl` < env CC_AI_KIT_GIT_CACHE_TTL.
GIT_CACHE_TTL = 5                  # default seconds the worktree probe is cached


EXTERNAL_CACHE_TTL = 10            # default seconds an external provider's output is cached


GIT_DEFAULTS = {"cache_ttl": GIT_CACHE_TTL}




# ── Color & effort defaults (the override baselines) ─────────────────────────
# Overridable palette: NAME -> default SGR params (no "\033[" / "m" wrapper).
# Values are pure hues — no baked-in bold. Emphasis is expressed on the ramp
# bands via "+modifiers" (e.g. "RED+bold"); see _RAMP_DEFAULTS. A [palette]
# override replaces a value here; core_build_theme resolves these into a Theme.
PALETTE_DEFAULTS = {            # pure hues — no baked-in bold
    "GREY": "90", "WHITE": "97", "CYAN": "36", "GREEN": "32", "RED": "31",
    "YELLOW": "33", "MAGENTA": "35", "ORANGE": "38;5;208",
    "BLUE": "38;5;39",           # lightened (was 38;5;33); shade reviewed on-terminal
    "LIGHTBLUE": "38;5;75", "MAGENTA_DARK": "38;5;90",
}   # ORANGE_BOLD / MAGENTA_DARK_BOLD removed — bold now lives on the ramp band


# Ramps as data: band -> [(threshold, colorspec)]. Threshold keys go through
# util_parse_threshold (percent / byte-suffix / inf); colorspecs through util_parse_color
# against the resolved palette. [ramp.X] in config REPLACES a band wholesale.
RAMP_DEFAULTS = {
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
    # slowest: the single per-segment SLO/SLA ramp the `slowest` segment colors by
    # (one shared band — NO per-segment override bands). Tighter than render_time
    # since it grades ONE builder, not the whole render.
    "slowest": [("15ms", "GREEN"), ("40ms", "YELLOW"), ("inf", "RED+bold")],
}


# Effort ladder: level -> (palette name, fill count 1..5). Palette-derived but
# NOT user-configurable. `auto` is a setting and `ultracode` reports as xhigh —
# neither is a level here.
EFFORT_DEFAULTS = {
    "low": ("CYAN", 1), "medium": ("BLUE", 2), "high": ("YELLOW", 3),
    "xhigh": ("ORANGE", 4), "max": ("RED", 5),
}


EFFORT_GLYPHS = "▁▃▄▆█"


# `git` and `external` default to None so older Config(...) call sites (which
# pass only the original fields) keep working; consumers guard with
# (cfg.git or {}) and (cfg.external.providers if cfg.external else []).
class ExternalConf(NamedTuple):
    """Resolved external-segment configuration for one render pass."""

    dir: str               # providers directory (was Config.segments_dir)
    cache_ttl: int         # default cache TTL in seconds
    providers: list[Any]   # finalized ExtSpec list (was Config.external)


class Config(NamedTuple):
    """Resolved, validated configuration for one render pass."""

    segments: dict[str, bool]
    layout: list[Line]
    palette: dict[str, str]
    ramps: dict[str, dict[str, str]]
    git: dict[str, int] | None = None
    external: "ExternalConf | None" = None
    cache_base: str = ""


# Fixed (non-overridable) colors.
RESET = "\033[0m"


BG_LIGHTGRAY = "\033[47m"


DIM = "\033[90m"             # fixed dim grey for stderr warnings (palette-independent)


WARN = "\033[33m"            # fixed yellow for failure markers (palette-independent)


INF = float("inf")


# The single shared git probe result. `git_branch`, `git_dirty`, and
# `alt_git_worktree` are independent segments but all read from one GitSnapshot —
# no duplicated git querying. wt_name is the active linked-worktree's directory
# basename ("" on the main checkout or outside a repo).
class GitSnapshot(NamedTuple):
    """One-shot result from the shared git probe (branch, dirty, worktree)."""

    in_repo: bool
    branch: str
    dirty: str
    is_worktree: bool
    wt_name: str
    root_name: str = ""    # main checkout's dir basename; same across every worktree
    root_path: str = ""    # main checkout's absolute dir path; root_name is its basename


# ── External drop-in segments (E4c) ──────────────────────────────────────────


# A provider is an executable in the segments dir. Its first 10 lines may carry
#   # ai-kit-segment: line=<N> (after=<key>|before=<key>|start|end)
#                     [id=<slug>] [timeout=<s>] [ttl=<s>]
# It is modeled as a synthetic builder inserted into the resolved layout, so the
# existing packer handles placement/priority/overflow unchanged.
class ExtSpec(NamedTuple):
    """Metadata for one external segment provider discovered from the segments dir."""

    id: str
    path: str
    line: int
    position: tuple[str, str]
    timeout: float
    ttl: int
    cache_path: str

# ═══ 4. fmt_ — pure formatters (number / tokens / duration / bytes / ago) ═════


# Formatters are pure value→display-string and consumer-independent: the same
# fmt_ produces the same text regardless of which segment calls it.


def fmt_number(n: int | float) -> str:
    """Thousands separators: 1234567 -> '1,234,567'."""
    return f"{int(n):,}"


def fmt_time_ms(ms: int | float) -> str:
    """Human-readable duration from milliseconds (matches statusline.sh)."""
    ms = int(ms)
    if ms < 1000:
        return f"{ms}ms"
    if ms < 60_000:
        return f"{ms // 1000}s"
    if ms < 3_600_000:
        return f"{ms // 60_000}m {(ms % 60_000) // 1000}s"
    return f"{ms // 3_600_000}h {(ms % 3_600_000) // 60_000}m"


def fmt_tokens(n: int | float) -> str:
    """200000 -> '200K', 1000000 -> '1M'."""
    n = int(n)
    if n >= 1_000_000:
        return f"{n // 1_000_000}M"
    if n >= 1000:
        return f"{n // 1000}K"
    return str(n)


def fmt_ago(secs: int | float) -> str:
    """Seconds since last activity as an 'ago' string."""
    secs = int(secs)
    if secs <= 0:
        return "just now"
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60}s ago"
    return f"{secs // 3600}h {(secs % 3600) // 60}m ago"


def fmt_bytes(n: int | float) -> str:
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


def fmt_duration(ns: int | float) -> str:
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
    return f"{ns}ns"

# ═══ 5. util_ — pure non-format helpers (color / width / truncate / fit / parse)


# Shared by default; classify by NATURE, not caller. A helper keeps its prefix even
# if only one tier calls it today (a caller-based name rots when reuse appears).
# Extraction seam: git/proc-only helpers travel with those probes if ever
# externalized; the cross-tier ones are the irreducible shared core. The exact
# caller census is regenerable on demand via AST — not kept here.


_SGR_SEQ = re.compile(r"\x1b\[[0-9;]*m")            # an SGR color/style escape


_CSI_SEQ = re.compile(r"\x1b\[[0-9;?]*([A-Za-z])")  # any CSI; group = final byte


_OSC_SEQ = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")


_STRAY_ESC = re.compile(r"\x1b(?!\[[0-9;]*m)")      # ESC not starting an SGR


_C0_CTRL = re.compile(r"[\x00-\x09\x0b-\x1a\x1c-\x1f\x7f]")  # controls (incl. TAB) except NL/ESC


def util_truncate_visible(s: str, avail: int) -> str:
    """Cut s to at most `avail` visible cells, preserving zero-width SGR escapes,
    appending RESET if any SGR was emitted. avail <= 0 -> ''."""
    if avail <= 0:
        return ""
    out: list[str] = []
    width, i, n, saw_sgr = 0, 0, len(s), False
    while i < n:
        m = _SGR_SEQ.match(s, i)
        if m:
            out.append(m.group(0))
            saw_sgr = True
            i = m.end()
            continue
        w = util_char_width(s[i])
        if width + w > avail:
            break
        out.append(s[i])
        width += w
        i += 1
    res = "".join(out)
    if saw_sgr and not res.endswith(RESET):
        res += RESET
    return res


def util_pick_color(pct: float, ramp: list[tuple[float, str]]) -> str:
    """Return the color for the first ceil that pct is strictly below."""
    for ceil, color in ramp:
        if pct < ceil:
            return color
    return ramp[-1][1]


_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


# BMP symbols we render that terminals draw 2 cells wide (east_asian_width
# misclassifies these as narrow). Add a codepoint here if a new wide BMP glyph
# is introduced in a segment.
_WIDE_BMP = {0x23F0, 0x23F1, 0x23F8, 0x26A1}  # ⏰ ⏱ ⏸ ⚡


def util_char_width(ch: str) -> int:
    """Display cells for one char: 0 (combining/zero-width), 1, or 2 (wide)."""
    if unicodedata.combining(ch):
        return 0
    o = ord(ch)
    if 0xFE00 <= o <= 0xFE0F:                         # variation selectors render in-place
        return 0
    if o >= 0x1F300:                                  # emoji / pictographs (SMP)
        return 2
    if o in _WIDE_BMP:
        return 2
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def util_visible_width(s: str) -> int:
    """Terminal display width of s, ignoring ANSI SGR escapes."""
    return sum(util_char_width(c) for c in _ANSI_RE.sub("", s))


def util_first_fitting(variants: Sequence[str | None], avail: int) -> str | None:
    """Return the first (richest) truthy variant whose display width fits avail.

    None if none fit. Builders pass their variants rich-first so the widest
    affordable detail level wins; returning None is a builder self-hiding."""
    for v in variants:
        if v and util_visible_width(v) <= avail:
            return v
    return None


def util_two_state_cap(s: str, high: int, low: int) -> str:
    """Return s unchanged if it fits `high` columns; otherwise ellipsis-
    truncate it down to `low` columns via util_trunc_cols. A discrete jump,
    not a continuous shrink — the value either shows in full up to a
    comfortable width, or drops straight to a much shorter floor beyond it."""
    return s if util_visible_width(s) <= high else util_trunc_cols(s, low)


# Glyphs we model as wide (_WIDE_BMP) but that render NARROW bare on many
# terminals. Forcing VS16 (emoji presentation) makes them render wide everywhere
# so the single-space util_icon gap is always one clean column. ⏰ (U+23F0) is
# already EAW=W, so it is intentionally absent.
_ICON_VS16 = {"⏱", "⏸", "⚡"}  # ⏱ ⏸ ⚡


def util_icon(glyph: str, text: str) -> str:
    """Render `glyph` + exactly one space + `text` — the one place icon→text
    spacing is decided. Narrow-rendering glyphs get VS16 so the gap is one
    visible column regardless of terminal emoji handling."""
    g = f"{glyph}️" if glyph in _ICON_VS16 else glyph
    return f"{g} {text}"


# One parser produces every SGR escape. Base forms (by shape): palette NAME
# (letter-led, resolved against `palette`), raw SGR ("38;5;208" passthrough), or
# hex ("#rgb"/"#rrggbb"/"#rrggbbaa", alpha dropped). "+bold/+dim/+italic/
# +underline" modifiers prepend 1/2/3/4 in ascending order. Invalid -> None.
_MOD_SGR = {"bold": "1", "dim": "2", "italic": "3", "underline": "4"}


def util_hex_to_sgr(spec: str) -> str | None:
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


def util_parse_color(spec: Any, palette: dict[str, str] | None = None) -> str | None:
    """Resolve a colorspec to '\\033[...m', or None if invalid. See section
    header for the grammar. `palette` ({NAME: sgr params}) is required only for
    name lookups; raw-SGR and hex specs ignore it."""
    if not spec:
        return None
    base, *mod_names = str(spec).split("+")
    base = base.strip()
    mods: list[str] = []
    for m in mod_names:
        code = _MOD_SGR.get(m.strip().lower())
        if code is None:
            return None
        mods.append(code)
    if base.startswith("#"):
        params = util_hex_to_sgr(base)
    elif base[:1].isalpha():
        params = (palette or {}).get(base)
    elif re.fullmatch(r"[0-9;]+", base):
        params = base
    else:
        params = None
    if params is None:
        return None
    ordered = sorted(set(mods), key=int)
    return "\033[" + ";".join([*ordered, params]) + "m"


_THRESHOLD_MULT = {"k": 1024, "M": 1024 ** 2, "G": 1024 ** 3}


# Time thresholds (render_time ramp) resolve to NANOSECONDS, matching what the
# segment measures via time.perf_counter_ns(). "µs" and ASCII "us" both accepted.
_TIME_MULT_NS = {"ns": 1, "us": 1000, "µs": 1000, "ms": 1_000_000, "s": 1_000_000_000}


def util_parse_threshold(key: str | int | float) -> float:
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


def util_gap_color(delta: float, theme: "Theme") -> str:
    """Quota-gap band color: |gap| in percentage points graded against the
    spec's INCLUSIVE bounds (<=5 GREEN, <11 YELLOW, <=15 ORANGE, >15 RED).
    Deliberately NOT util_pick_color -- that helper is strictly-below and
    cannot express <=5 / <11 / 11..15-inclusive."""
    if delta <= 5.0:
        return theme.c("GREEN")
    if delta < 11.0:
        return theme.c("YELLOW")
    if delta <= 15.0:
        return theme.c("ORANGE")
    return theme.c("RED")


def util_gap_sign(gap: float) -> str:
    """Pace sign glued to the displayed percentage by the caller: '+' when
    usage is at or behind the window clock (under pace -- slack), '-' when
    usage is ahead (burning faster than the clock). The sign is the gap
    direction INVERTED (gap = used - elapsed_pct); its magnitude is
    carried by the color band, never shown next to the number."""
    return "+" if gap <= 0.0 else "-"


def util_branch_from_porcelain(header: str) -> str:
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


def util_git_cache_path(work_dir: str, cache_base: str) -> str:
    """Per-work_dir cache file for the worktree probe under <cache_base>/git/."""
    key = hashlib.sha1(os.path.abspath(work_dir).encode()).hexdigest()[:16]
    return os.path.join(cache_base, "git", key)


def util_safe_session(s: Any) -> bool:
    """A session id is used as a single path component under the tasks/todos dir.
    Reject anything with a path separator or parent ref so it cannot escape that
    directory (path traversal)."""
    return bool(s) and not re.search(r"[/\\]|\.\.", s)


def util_display_dir(work_dir: str, home: str) -> str:
    """Return work_dir tiered: try the full ~-relative (or absolute) path
    and parent/basename against the PATH_MAX_LEN structural budget (richest
    first); if neither fits, fall to the basename alone via
    util_two_state_cap(name, 30, 20)."""
    stripped = work_dir.rstrip("/")
    full = ("~" + work_dir[len(home):]) if (home and work_dir.startswith(home)) else work_dir
    parent = os.path.basename(os.path.dirname(stripped))
    name = os.path.basename(stripped) or work_dir
    structural = util_first_fitting([full, f"{parent}/{name}"], PATH_MAX_LEN)
    return structural if structural is not None else util_two_state_cap(name, 30, 20)


def util_dirty_mark(dirty: str, theme: "Theme") -> str:
    """Return a colored dirty-state marker string ('✗', '~', or '') for the segment."""
    if dirty == "untracked":
        return f"{theme.c('RED')}✗{RESET}"
    if dirty == "modified":
        return f"{theme.c('YELLOW')}~{RESET}"
    return ""


def util_trunc_cols(s: str, limit: int) -> str:
    """Truncate s to at most `limit` display columns, appending `…` if cut.
    Column-aware (uses util_char_width) so a wide/multibyte name can't blow the budget."""
    if sum(util_char_width(c) for c in s) <= limit:
        return s
    out: list[str] = []
    width = 0
    for c in s:
        cw = util_char_width(c)
        if width + cw > limit - 1:          # reserve one column for the ellipsis
            break
        out.append(c)
        width += cw
    return "".join(out) + "…"


def util_to_int(s: str | None) -> int | None:
    """Parse a stripped string to int, or None on empty/non-numeric input. Pure
    probe-support parser (tput/ps output) — not config; see cfg_coerce for config."""
    try:
        return int(s) if s else None
    except ValueError:
        return None


def util_sanitize_external(text: str, avail: int) -> str | None:
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
    return util_truncate_visible(line, avail) or None


def util_position_str(position: tuple[str, str]) -> str:
    """('after','clock') -> 'after:clock'; ('end','') -> 'end'."""
    kind, ref = position
    return f"{kind}:{ref}" if ref else kind
