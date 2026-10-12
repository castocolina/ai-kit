#!/usr/bin/env python3
"""Cursor Agent statusline POC — not production; duplicates lean status-line patterns."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, BinaryIO

_FRESH_TTL = 120
_NEG_TTL = 600
_POST_TIMEOUT = 0.8
_METHODS = ("GetCurrentPeriodUsage", "GetHardLimit", "GetPlanInfo")

# ── constants ──────────────────────────────────────────────────────────────────

RESET = "\033[0m"
_DIM = "\033[90m"
SEP = " | "
_SLOWEST_META = frozenset({"render_time", "slowest"})
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")
_WIDE_BMP = {0x23F0, 0x23F1, 0x23F8, 0x26A1}

_PALETTE_DEFAULTS = {
    "GREY": "90",
    "WHITE": "97",
    "CYAN": "36",
    "GREEN": "32",
    "RED": "31",
    "YELLOW": "33",
    "ORANGE": "38;5;208",
    "BLUE": "38;5;39",
}

# Claude-parity column ergonomics.
PATH_MAX_LEN = 50
CONTEXT_BAR_CELLS = 10
RIGHT_MARGIN = 4
PINNED = frozenset({"path", "context"})

# Percent ramps (context / rate) + ns ramps (render_time / slowest).
_RAMP_PCT = {
    "context": [
        (10.0, "WHITE"),
        (15.0, "CYAN"),
        (20.0, "BLUE"),
        (25.0, "GREEN"),
        (30.0, "YELLOW"),
        (40.0, "ORANGE"),
        (50.0, "RED"),
        (math.inf, "RED"),
    ],
    "rate": [(50.0, "GREEN"), (80.0, "YELLOW"), (math.inf, "RED")],
}
_RAMP_NS = {
    "render_time": [(50_000_000.0, "GREEN"), (150_000_000.0, "YELLOW"), (math.inf, "RED")],
    "slowest": [(15_000_000.0, "GREEN"), (40_000_000.0, "YELLOW"), (math.inf, "RED")],
}

SEGMENTS: dict[str, bool] = {
    "path": True,
    "git_branch": True,
    "git_dirty": True,
    "alt_git_worktree": True,
    "model": True,
    "context": True,
    "included_total": True,
    "included_auto": True,
    "included_api": True,
    "reset": True,
    "on_demand": True,
    "process_memory": True,
    "system_memory": True,
    "render_time": True,
    "slowest": True,
}

# Claude-shaped rows: identity → model/context+quota → diagnostics.
LAYOUT: list[tuple[int, list[str]]] = [
    (0, ["path", "git_branch", "git_dirty", "alt_git_worktree"]),
    (
        0,
        [
            "model",
            "context",
            "included_total",
            "included_auto",
            "included_api",
            "reset",
            "on_demand",
        ],
    ),
    (0, ["render_time", "process_memory", "system_memory", "slowest"]),
]


class Config:
    """Resolved POC config: segments map + layout rows."""

    def __init__(
        self,
        segments: dict[str, bool],
        layout: list[tuple[int, list[str]]],
    ) -> None:
        self.segments = segments
        self.layout = layout


class Theme:
    """Palette + resolved ramps; `.c(name)` returns an SGR prefix."""

    def __init__(
        self,
        palette: dict[str, str],
        ramps: dict[str, list[tuple[float, str]]],
    ) -> None:
        self.palette = palette
        self.ramps = ramps
        self._cache: dict[str, str] = {}

    def c(self, name: str) -> str:
        if name not in self._cache:
            params = self.palette.get(name, "")
            self._cache[name] = f"\033[{params}m" if params else ""
        return self._cache[name]


def default_theme() -> Theme:
    palette = dict(_PALETTE_DEFAULTS)
    ramps: dict[str, list[tuple[float, str]]] = {}
    for band, pairs in {**_RAMP_PCT, **_RAMP_NS}.items():
        resolved: list[tuple[float, str]] = []
        for ceil, color in pairs:
            # Bold red for the top severity band (Claude RED+bold).
            if color == "RED" and ceil is math.inf:
                resolved.append((ceil, f"\033[1;{palette['RED']}m"))
            elif color == "ORANGE":
                resolved.append((ceil, f"\033[1;{palette['ORANGE']}m"))
            else:
                resolved.append((ceil, f"\033[{palette[color]}m"))
        ramps[band] = resolved
    return Theme(palette, ramps)


def util_char_width(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    o = ord(ch)
    if 0xFE00 <= o <= 0xFE0F:
        return 0
    if o >= 0x1F300:
        return 2
    if o in _WIDE_BMP:
        return 2
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def util_visible_width(s: str) -> int:
    return sum(util_char_width(c) for c in _ANSI_RE.sub("", s))


def util_pick_color(pct: float, ramp: list[tuple[float, str]]) -> str:
    for ceil, color in ramp:
        if pct < ceil:
            return color
    return ramp[-1][1]


def util_gap_color(delta: float, theme: Theme) -> str:
    if delta <= 5.0:
        return theme.c("GREEN")
    if delta < 11.0:
        return theme.c("YELLOW")
    if delta <= 15.0:
        return theme.c("ORANGE")
    return theme.c("RED")


def util_first_fitting(variants: list[str | None], avail: int) -> str | None:
    for v in variants:
        if v and util_visible_width(v) <= avail:
            return v
    return None


def util_icon(glyph: str, text: str) -> str:
    return f"{glyph} {text}"


def util_trunc_cols(s: str, limit: int) -> str:
    if util_visible_width(s) <= limit:
        return s
    out: list[str] = []
    width = 0
    for c in s:
        cw = util_char_width(c)
        if width + cw > limit - 1:
            break
        out.append(c)
        width += cw
    return "".join(out) + "…"


def util_two_state_cap(s: str, high: int, low: int) -> str:
    return s if util_visible_width(s) <= high else util_trunc_cols(s, low)


def util_display_dir(work_dir: str, home: str) -> str:
    """Tiered path: full ~-rel / parent/name / basename — Claude PATH_MAX_LEN."""
    stripped = work_dir.rstrip("/")
    full = (
        ("~" + work_dir[len(home) :])
        if (home and work_dir.startswith(home))
        else work_dir
    )
    parent = os.path.basename(os.path.dirname(stripped))
    name = os.path.basename(stripped) or work_dir or "?"
    structural = util_first_fitting([full, f"{parent}/{name}"], PATH_MAX_LEN)
    return structural if structural is not None else util_two_state_cap(name, 30, 20)


def fmt_tokens(n: int | float) -> str:
    n = int(n)
    if n >= 1_000_000:
        return f"{n // 1_000_000}M"
    if n >= 1000:
        return f"{n // 1000}K"
    return str(n)


def fmt_bytes(n: int | float) -> str:
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
    ns = int(ns)
    if ns < 1000:
        return f"{ns}ns"
    for div, suffix in ((1_000_000_000, "s"), (1_000_000, "ms"), (1000, "µs")):
        if ns >= div:
            v = ns / div
            return f"{v:.1f}{suffix}" if v < 10 else f"{v:.0f}{suffix}"
    return f"{ns}ns"


def config_path(env: dict[str, str]) -> Path:
    explicit = env.get("AI_KIT_CURSOR_POC_CONFIG_FILE")
    if explicit:
        return Path(os.path.expanduser(explicit))
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return Path(base) / "ai-kit" / "cursor-statusline-poc.toml"


def load_config(env: dict[str, str]) -> Config:
    segments = dict(SEGMENTS)
    layout = list(LAYOUT)
    path = config_path(env)
    if not path.is_file():
        return Config(segments=segments, layout=layout)
    try:
        with path.open("rb") as fh:
            raw = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return Config(segments=segments, layout=layout)
    file_seg = raw.get("segments") or {}
    if isinstance(file_seg, dict):
        for k, v in file_seg.items():
            if k in segments and isinstance(v, bool):
                segments[k] = v
    lines = raw.get("line")
    if lines:
        new_layout: list[tuple[int, list[str]]] = []
        for ln in lines:
            if not isinstance(ln, dict):
                continue
            segs = ln.get("segments") or []
            if not isinstance(segs, list):
                continue
            min_rows = int(ln.get("min_rows") or 0)
            new_layout.append((min_rows, [str(s) for s in segs]))
        if new_layout:
            layout = new_layout
    return Config(segments=segments, layout=layout)


def _hide_quota(*, fetched_at: float | int = 0, error: str | None = None) -> dict[str, Any]:
    q: dict[str, Any] = {
        "total_pct": None,
        "auto_pct": None,
        "api_pct": None,
        "on_demand": {"kind": "unavailable"},
        "cycle_start_ms": 0,
        "cycle_end_ms": 0,
        "fetched_at": fetched_at,
        "stale": True,
    }
    if error:
        q["error"] = error
    return q


def _pick(obj: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in obj:
            return obj[k]
    return None


def _as_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _as_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def resolve_auth_path(env: dict[str, str]) -> Path | None:
    home = Path(env.get("HOME") or Path.home())
    cands: list[Path] = []
    if env.get("CURSOR_CONFIG_DIR"):
        cands.append(Path(env["CURSOR_CONFIG_DIR"]) / "auth.json")
    if env.get("XDG_CONFIG_HOME"):
        cands.append(Path(env["XDG_CONFIG_HOME"]) / "cursor" / "auth.json")
    cands.append(home / ".config" / "cursor" / "auth.json")
    cands.append(home / ".cursor" / "auth.json")
    for p in cands:
        if p.is_file():
            return p
    return None


def _read_access_token(env: dict[str, str]) -> str | None:
    path = resolve_auth_path(env)
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    tok = data.get("accessToken")
    if isinstance(tok, str) and tok:
        return tok
    return None


def quota_cache_path(env: dict[str, str]) -> Path:
    base = env.get("XDG_CACHE_HOME") or os.path.join(env.get("HOME", ""), ".cache")
    return Path(base) / "ai-kit" / "cursor-statusline-poc" / "usage.json"


def write_quota_cache(env: dict[str, str], data: dict[str, Any]) -> None:
    path = quota_cache_path(env)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never persist token material.
    safe = {k: v for k, v in data.items() if k not in {"accessToken", "token"}}
    text = json.dumps(safe, separators=(",", ":"))
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".usage.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _read_quota_cache(env: dict[str, str]) -> dict[str, Any] | None:
    path = quota_cache_path(env)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def quota_endpoint_url(env: dict[str, str]) -> str:
    base = env.get("CURSOR_API_ENDPOINT") or "https://api2.cursor.sh"
    if not base.startswith("https://"):
        raise ValueError("CURSOR_API_ENDPOINT must be https://")
    return base.rstrip("/")


def redirect_allowed(from_url: str, to_url: str) -> bool:
    a = urllib.parse.urlparse(from_url)
    b = urllib.parse.urlparse(to_url)
    return a.scheme == "https" and b.scheme == "https" and a.netloc == b.netloc


class QuotaRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse cross-host redirects so Bearer tokens never leave api2.cursor.sh."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        old = req.get_full_url()
        if not redirect_allowed(old, newurl):
            raise urllib.error.HTTPError(
                newurl, code, "cross-host redirect refused", headers, None
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _default_urlopen():
    opener = urllib.request.build_opener(QuotaRedirectHandler())
    return opener.open


def normalize_quota_responses(
    period: dict[str, Any],
    hard: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    plan_usage = _pick(period, "planUsage", "plan_usage")
    spend = _pick(period, "spendLimitUsage", "spend_limit_usage") or {}
    if not isinstance(spend, dict):
        spend = {}
    plan_info = _pick(plan, "planInfo", "plan_info") or {}
    if not isinstance(plan_info, dict):
        plan_info = {}

    cycle_start = _as_int(_pick(period, "billingCycleStart", "billing_cycle_start")) or 0
    cycle_end = _as_int(_pick(period, "billingCycleEnd", "billing_cycle_end")) or 0
    if not cycle_end:
        cycle_end = _as_int(_pick(plan_info, "billingCycleEnd", "billing_cycle_end")) or 0

    if not isinstance(plan_usage, dict):
        return {
            "cycle_start_ms": cycle_start,
            "cycle_end_ms": cycle_end,
            "total_pct": None,
            "auto_pct": None,
            "api_pct": None,
            "on_demand": {"kind": "unavailable"},
        }

    total = _as_float(_pick(plan_usage, "totalPercentUsed", "total_percent_used"))
    if total is None:
        spend_inc = _as_float(_pick(plan_usage, "includedSpend", "included_spend"))
        limit = _as_float(_pick(plan_usage, "limit"))
        if spend_inc is not None and limit is not None and limit > 0:
            total = 100.0 * spend_inc / limit
        else:
            total = None
    auto = _as_float(_pick(plan_usage, "autoPercentUsed", "auto_percent_used"))
    api = _as_float(_pick(plan_usage, "apiPercentUsed", "api_percent_used"))

    used_cents = _as_float(_pick(spend, "individualUsed", "individual_used")) or 0.0
    used_dollars = used_cents / 100.0
    no_usage = bool(_pick(hard, "noUsageBasedAllowed", "no_usage_based_allowed"))
    hard_limit = _as_float(_pick(hard, "hardLimit", "hard_limit"))
    if hard_limit is None:
        hard_limit = 0.0

    if no_usage:
        on_demand: dict[str, Any] = {"kind": "disabled"}
    elif hard_limit >= 2147483647:
        on_demand = {"kind": "unlimited", "used_dollars": used_dollars}
    elif hard_limit > 0:
        on_demand = {
            "kind": "fixed",
            "used_dollars": used_dollars,
            "ceiling_dollars": float(hard_limit),
        }
    else:
        on_demand = {"kind": "disabled"}

    return {
        "cycle_start_ms": cycle_start,
        "cycle_end_ms": cycle_end,
        "total_pct": total,
        "auto_pct": auto,
        "api_pct": api,
        "on_demand": on_demand,
    }


def _usable_quota_fields(cache: dict[str, Any]) -> bool:
    if cache.get("total_pct") is not None:
        return True
    od = cache.get("on_demand")
    return isinstance(od, dict) and od.get("kind") not in (None, "unavailable")


def _normalize_error_only(cache: dict[str, Any], now: float | int) -> dict[str, Any]:
    if _usable_quota_fields(cache):
        out = dict(cache)
        out["stale"] = True
        return out
    return _hide_quota(fetched_at=cache.get("fetched_at", now), error=cache.get("error"))


def fetch_quota(
    env: dict[str, str],
    *,
    now: float | int,
    urlopen: Any = None,
) -> dict[str, Any]:
    """Fetch/normalize Dashboard quota with disk TTL cache. Never raises."""
    # shortcut: sync sequential fetch; no single-flight; live wire raises interval/timeout
    cache = _read_quota_cache(env)
    if cache is not None:
        fetched_at = float(cache.get("fetched_at") or 0)
        age = float(now) - fetched_at
        has_error = bool(cache.get("error"))
        if not has_error and age < _FRESH_TTL:
            out = dict(cache)
            out["stale"] = False
            return out
        if has_error and age < _NEG_TTL:
            return _normalize_error_only(cache, now)

    token = _read_access_token(env)
    last_good = None
    if cache is not None and _usable_quota_fields(cache):
        last_good = {k: v for k, v in cache.items() if k != "error"}

    if not token:
        if last_good is not None:
            out = dict(last_good)
            out["stale"] = True
            return out
        return _hide_quota(fetched_at=now)

    open_fn = urlopen if urlopen is not None else _default_urlopen()
    try:
        base = quota_endpoint_url(env)
    except ValueError as exc:
        neg = {**(last_good or {}), "error": str(exc), "fetched_at": now, "stale": True}
        if last_good is None:
            neg = _hide_quota(fetched_at=now, error=str(exc))
        write_quota_cache(env, neg)
        return neg

    bodies: list[dict[str, Any]] = []
    try:
        for method in _METHODS:
            url = f"{base}/aiserver.v1.DashboardService/{method}"
            req = urllib.request.Request(
                url,
                data=b"{}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Connect-Protocol-Version": "1",
                },
                method="POST",
            )
            with open_fn(req, timeout=_POST_TIMEOUT) as resp:
                raw = resp.read()
            bodies.append(json.loads(raw.decode("utf-8")))
    except Exception as exc:  # noqa: BLE001 — never raise out of fetch_quota
        neg = {**(last_good or {}), "error": str(exc), "fetched_at": now, "stale": True}
        if last_good is None:
            neg = _hide_quota(fetched_at=now, error=str(exc))
        else:
            # Keep usable fields from last-good.
            for k in ("total_pct", "auto_pct", "api_pct", "on_demand",
                      "cycle_start_ms", "cycle_end_ms"):
                if k in last_good:
                    neg[k] = last_good[k]
        write_quota_cache(env, neg)
        return neg

    period, hard, plan = bodies[0], bodies[1], bodies[2]
    q = normalize_quota_responses(period, hard, plan)
    q["fetched_at"] = now
    q["stale"] = False
    q.pop("error", None)
    write_quota_cache(env, q)
    return q


def util_branch_from_porcelain(header: str) -> str:
    if not header.startswith("## "):
        return ""
    rest = header[3:]
    if rest.startswith("HEAD (no branch)"):
        return ""
    for prefix in ("No commits yet on ", "Initial commit on "):
        if rest.startswith(prefix):
            return rest[len(prefix):].strip()
    return rest.split("...", 1)[0].strip()


def util_dirty_mark(dirty: str, theme: Theme) -> str:
    if dirty == "untracked":
        return f"{theme.c('RED')}✗{RESET}"
    if dirty == "modified":
        return f"{theme.c('YELLOW')}~{RESET}"
    return ""


def probe_git_snapshot(work_dir: str) -> dict[str, Any]:
    """POC plain-dict git snapshot (one rev-parse + porcelain status)."""
    empty = {
        "in_repo": False,
        "branch": "",
        "dirty": "clean",
        "is_worktree": False,
        "wt_name": "",
    }
    if not work_dir:
        return empty
    try:
        out = subprocess.run(
            [
                "git", "-C", work_dir, "rev-parse", "--path-format=absolute",
                "--git-dir", "--git-common-dir", "--show-toplevel",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return empty
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if len(lines) < 2:
        return empty
    is_worktree = lines[0] != lines[1]
    top = lines[2] if len(lines) >= 3 else ""
    wt_name = os.path.basename(top.rstrip("/")) if (is_worktree and top) else ""
    try:
        st = subprocess.run(
            ["git", "-C", work_dir, "status", "--porcelain", "--branch"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        ).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        st = []
    branch = util_branch_from_porcelain(st[0] if st else "")
    changes = st[1:]
    if any(ln.startswith(("??", "A", "D")) or ln.startswith(" D") for ln in changes):
        dirty = "untracked"
    elif any(ln.strip() for ln in changes):
        dirty = "modified"
    else:
        dirty = "clean"
    return {
        "in_repo": True,
        "branch": branch,
        "dirty": dirty,
        "is_worktree": is_worktree,
        "wt_name": wt_name,
    }


def probe_git_for(ctx: SimpleNamespace) -> dict[str, Any]:
    """Memoize one probe_git_snapshot per render on ctx._git."""
    if getattr(ctx, "_git", None) is None:
        ctx._git = probe_git_snapshot(ctx.work_dir)
    return ctx._git


# Process RSS (Claude-shaped: /proc on Linux, `ps` elsewhere). Cursor's Node
# host often reports /proc/<pid>/comm as "MainThread", so matching also reads
# the full command line — never fall back to this script's own RSS.
_HOST_COMM = frozenset({"cursor-agent", "agent"})


def _util_to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return None


def _ps_field(pid: int, fieldname: str) -> str | None:
    try:
        out = subprocess.run(
            ["ps", "-o", f"{fieldname}=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        ).stdout.strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def _comm_via_proc(pid: int) -> str | None:
    try:
        with open(f"/proc/{pid}/comm", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return None


def _ppid_via_proc(pid: int) -> int | None:
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as fh:
            return int(fh.read().split()[3])
    except (OSError, IndexError, ValueError):
        return None


def _rss_kb_via_proc(pid: int) -> int | None:
    try:
        with open(f"/proc/{pid}/status", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except (OSError, IndexError, ValueError):
        return None
    return None


def _cmdline_via_proc(pid: int) -> str | None:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    if not raw:
        return None
    return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip() or None


def _comm_via_ps(pid: int) -> str | None:
    return _ps_field(pid, "comm")


def _ppid_via_ps(pid: int) -> int | None:
    return _util_to_int(_ps_field(pid, "ppid"))


def _rss_kb_via_ps(pid: int) -> int | None:
    return _util_to_int(_ps_field(pid, "rss"))


def _cmdline_via_ps(pid: int) -> str | None:
    # macOS/BSD: `command` is argv joined; Linux procps accepts it too.
    return _ps_field(pid, "command")


def _is_cursor_host(comm: str | None, cmdline: str | None) -> bool:
    """True when this pid is the Cursor agent host (not the statusline script)."""
    if comm:
        base = os.path.basename(comm)
        if base in _HOST_COMM or "cursor-agent" in base:
            return True
    if cmdline and "cursor-agent" in cmdline:
        return True
    return False


def probe_process_rss_bytes() -> int | None:
    """RSS bytes of an ancestor cursor-agent host, or None if none found.

    Cross-platform like Claude's probe_rss_bytes: Linux /proc, else `ps`.
    Matches basename `cursor-agent`/`agent` on comm, or `cursor-agent` in the
    full command line (Node often sets comm to MainThread). Never reports this
    script's own RSS — a miss hides the segment instead of lying ~20MB.
    """
    use_proc = os.path.isdir("/proc")
    comm_of = _comm_via_proc if use_proc else _comm_via_ps
    ppid_of = _ppid_via_proc if use_proc else _ppid_via_ps
    rss_kb_of = _rss_kb_via_proc if use_proc else _rss_kb_via_ps
    cmdline_of = _cmdline_via_proc if use_proc else _cmdline_via_ps

    pid = os.getppid()
    for _ in range(12):
        name = comm_of(pid)
        cmdline = cmdline_of(pid)
        if name is None and cmdline is None:
            return None
        if _is_cursor_host(name, cmdline):
            kb = rss_kb_of(pid)
            return kb * 1024 if kb is not None else None
        parent = ppid_of(pid)
        if parent is None or parent in (0, pid):
            return None
        pid = parent
    return None


def probe_system_available_bytes() -> int | None:
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except (OSError, IndexError, ValueError):
        pass
    try:
        vm = subprocess.run(
            ["vm_stat"], capture_output=True, text=True, timeout=1, check=False
        )
        if vm.returncode == 0:
            page = 4096
            free = 0
            for line in vm.stdout.splitlines():
                if "page size of" in line:
                    page = int(
                        "".join(c for c in line.split("page size of")[1] if c.isdigit())
                    )
                for label in ("Pages free", "Pages inactive", "Pages speculative"):
                    if line.startswith(label + ":"):
                        free += int(line.rsplit(":", 1)[1].strip().rstrip("."))
            return free * page
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None


def build_context(
    payload: dict[str, Any],
    env: dict[str, str],
    *,
    now: float | int | None = None,
    theme: Theme | None = None,
    config: Config | None = None,
) -> SimpleNamespace:
    del now  # Task 5 uses now for quota; Task 1 keeps signature stable.
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    workspace = payload.get("workspace") if isinstance(payload.get("workspace"), dict) else {}
    ctx_win = payload.get("context_window") if isinstance(payload.get("context_window"), dict) else {}
    cols_raw = payload.get("render_width_chars")
    cols = int(cols_raw) if isinstance(cols_raw, int) and cols_raw > 0 else 80
    pct_raw = ctx_win.get("used_percentage")
    context_pct: float | None
    if isinstance(pct_raw, (int, float)):
        context_pct = float(pct_raw)
    else:
        context_pct = None
    size_raw = ctx_win.get("context_window_size")
    context_max = int(size_raw) if isinstance(size_raw, int) and size_raw > 0 else 0
    cfg = config if config is not None else load_config(env)
    th = theme if theme is not None else default_theme()
    return SimpleNamespace(
        work_dir=str(workspace.get("current_dir") or ""),
        home=env.get("HOME", ""),
        model_name=str(model.get("display_name") or ""),
        param_summary=str(model.get("param_summary") or ""),
        max_mode=bool(model.get("max_mode")),
        context_pct=context_pct,
        context_max=context_max,
        cols=cols,
        # Cursor payload has no terminal height; default tall so all rows show.
        lines=40,
        config=cfg,
        theme=th,
        t_start=None,
        slowest=None,
        _git=None,
    )


# ── segment stubs / Task 1 bodies ──────────────────────────────────────────────


def seg_path(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    shown = util_display_dir(ctx.work_dir or "?", ctx.home or "")
    # Degrade further into avail (Claude packs with shrinking avail; path is PINNED).
    variants = [
        shown,
        util_two_state_cap(os.path.basename(ctx.work_dir.rstrip("/")) or shown, 30, 20),
    ]
    pick = util_first_fitting(
        [f"{theme.c('BLUE')}{v}{RESET}" for v in variants], avail
    )
    return pick or f"{theme.c('BLUE')}{variants[-1]}{RESET}"


def seg_model(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    name = ctx.model_name
    if not name:
        return None
    colored = f"{theme.c('CYAN')}{name}{RESET}"
    extras: list[str] = []
    if ctx.param_summary:
        extras.append(str(ctx.param_summary))
    if ctx.max_mode:
        extras.append("max")
    rich = colored
    if extras:
        rich = f"{colored} · {' · '.join(extras)}"
    mid = (
        f"{colored} · max"
        if ctx.max_mode
        else colored
    )
    return util_first_fitting([rich, mid, colored], avail) or colored


def seg_context(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    if ctx.context_pct is None:
        return None
    pct = int(ctx.context_pct)
    color = util_pick_color(float(pct), theme.ramps["context"])
    pct_only = util_icon("📊", f"{color}{pct}%{RESET}")
    halves = 0 if pct <= 0 else min(2 * CONTEXT_BAR_CELLS, math.ceil(pct / 5))
    full_n, half = divmod(halves, 2)
    bar_f = "█" * full_n + ("▌" if half else "")
    bar_e = "░" * (CONTEXT_BAR_CELLS - full_n - half)
    bar = f"{color}{bar_f}{theme.c('GREY')}{bar_e}{RESET}"
    mid = util_icon("📊", f"{bar} {color}{pct}%{RESET}")
    if ctx.context_max > 0:
        full = util_icon(
            "📊", f"{bar} {color}{pct}% of {fmt_tokens(ctx.context_max)}{RESET}"
        )
        return util_first_fitting([full, mid, pct_only], avail) or pct_only
    return util_first_fitting([mid, pct_only], avail) or pct_only


def seg_git_branch(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    branch = probe_git_for(ctx).get("branch") or ""
    if not branch:
        return None
    shown = util_two_state_cap(branch, 30, 20)
    return util_first_fitting(
        [
            f"{theme.c('GREY')}[{util_icon('🌿', shown)}]{RESET}",
            f"{theme.c('GREY')}[{shown}]{RESET}",
        ],
        avail,
    )


def seg_alt_git_worktree(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    snap = probe_git_for(ctx)
    if not snap.get("in_repo"):
        return None
    if not snap.get("is_worktree"):
        return util_first_fitting(
            [f"{theme.c('GREY')}\033[9m⎇ wt{RESET}"], avail
        )
    name = util_two_state_cap(snap.get("wt_name") or "", 30, 20)
    return util_first_fitting([f"{theme.c('CYAN')}⎇ {name}{RESET}"], avail)


def seg_git_dirty(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    mark = util_dirty_mark(probe_git_for(ctx).get("dirty") or "clean", theme)
    return util_first_fitting([mark], avail) if mark else None


def seg_process_memory(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, theme
    n = probe_process_rss_bytes()
    if n is None:
        return None
    return util_first_fitting([util_icon("🧮", fmt_bytes(n))], avail)


def seg_system_memory(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx
    n = probe_system_available_bytes()
    if n is None:
        return None
    gib = n / (1024**3)
    color = (
        theme.c("GREEN")
        if gib >= 4
        else theme.c("YELLOW")
        if gib >= 1
        else f"\033[1;{theme.palette['RED']}m"
    )
    long_t = f"{color}💻 {gib:.1f} GiB free{RESET}"
    med_t = f"{color}💻 {gib:.1f}G{RESET}"
    short_t = f"{color}💻{gib:.0f}G{RESET}"
    return util_first_fitting([long_t, med_t, short_t], avail)


def seg_render_time(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    t0 = ctx.t_start
    if t0 is None:
        return None
    elapsed = time.perf_counter_ns() - t0
    color = util_pick_color(elapsed, theme.ramps["render_time"])
    return util_first_fitting(
        [util_icon("⏱", f"{color}{fmt_duration(elapsed)}{RESET}")], avail
    )


def seg_slowest(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    slow = ctx.slowest
    if not slow:
        return None
    name, ns = slow
    color = util_pick_color(ns, theme.ramps["slowest"])
    dur = f"{color}{fmt_duration(ns)}{RESET}"
    return util_first_fitting(
        [util_icon("🐌", f"{name} {dur}"), util_icon("🐌", dur)], avail
    )


def billing_pace_gap(
    used_pct: float,
    start_ms: int,
    end_ms: int,
    now_ms: int,
) -> float | None:
    if end_ms <= start_ms:
        return None
    elapsed = 100.0 * (now_ms - start_ms) / (end_ms - start_ms)
    elapsed = max(0.0, min(100.0, elapsed))
    return float(used_pct) - elapsed


def context_from_quota(quota: dict[str, Any], *, now_ms: int) -> SimpleNamespace:
    od = quota.get("on_demand") if isinstance(quota.get("on_demand"), dict) else {
        "kind": "unavailable"
    }
    total = quota.get("total_pct")
    used = float(od.get("used_dollars") or 0)
    hot = bool(
        isinstance(total, (int, float))
        and float(total) >= 100
        and used > 0
        and od.get("kind") in {"fixed", "unlimited"}
    )
    return SimpleNamespace(
        total_pct=total,
        auto_pct=quota.get("auto_pct"),
        api_pct=quota.get("api_pct"),
        on_demand=od,
        cycle_start_ms=int(quota.get("cycle_start_ms") or 0),
        cycle_end_ms=int(quota.get("cycle_end_ms") or 0),
        stale=bool(quota.get("stale")),
        now_ms=now_ms,
        on_demand_hot=hot,
    )


def _quota_suffix(ctx: SimpleNamespace) -> str:
    s = f"{_DIM}≈{RESET}"
    if getattr(ctx, "stale", False):
        s += " (stale)"
    return s


def _included_body(prefix: str, pct: float, theme: Theme) -> str:
    """Rate-ramp color on used % (Claude ⚡ buckets), whole label painted."""
    color = util_pick_color(float(pct), theme.ramps["rate"])
    return f"{color}{prefix} {int(pct)}%{RESET}"


def _included_variants(
    prefix: str, pct: float, ctx: SimpleNamespace, theme: Theme
) -> list[str]:
    body = _included_body(prefix, pct, theme)
    suf = _quota_suffix(ctx)
    rich = util_icon("⚡", f"{body}{suf}")
    mid = util_icon("⚡", body)
    return [rich, mid, body]


def seg_included_total(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    pct = getattr(ctx, "total_pct", None)
    if pct is None:
        return None
    return util_first_fitting(_included_variants("inc", float(pct), ctx, theme), avail)


def seg_included_auto(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    pct = getattr(ctx, "auto_pct", None)
    if pct is None:
        return None
    return util_first_fitting(_included_variants("auto", float(pct), ctx, theme), avail)


def seg_included_api(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    pct = getattr(ctx, "api_pct", None)
    if pct is None:
        return None
    return util_first_fitting(_included_variants("api", float(pct), ctx, theme), avail)


def seg_reset(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del theme
    end_ms = int(getattr(ctx, "cycle_end_ms", 0) or 0)
    if not end_ms:
        return None
    now_ms = int(getattr(ctx, "now_ms", 0) or 0)
    days = max(0, math.ceil((end_ms - now_ms) / 86_400_000))
    date = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).date().isoformat()
    suf = _quota_suffix(ctx)
    rich = f"↺ {date} ({days}d){suf}"
    mid = f"↺ {date}{suf}"
    short = f"↺ {days}d{suf}"
    return util_first_fitting([rich, mid, short], avail)


def seg_on_demand(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    od = getattr(ctx, "on_demand", None) or {}
    kind = od.get("kind")
    if kind == "unavailable" or kind is None:
        return None
    if kind == "disabled":
        body = "od off"
        color = ""
    elif kind == "fixed":
        used = float(od.get("used_dollars") or 0)
        ceil = float(od.get("ceiling_dollars") or 0)
        body = f"od ${used:.1f}/${ceil:g}"
        ratio = (100.0 * used / ceil) if ceil > 0 else 0.0
        color = util_pick_color(ratio, theme.ramps["rate"])
    elif kind == "unlimited":
        used = float(od.get("used_dollars") or 0)
        body = f"od ${used:.1f} no cap"
        color = theme.c("GREEN")
    else:
        return None
    if getattr(ctx, "on_demand_hot", False):
        color = "\x1b[1;31m"
    painted = f"{color}{body}{RESET}" if color else body
    suf = _quota_suffix(ctx)
    rich = util_icon("🪙", f"{painted}{suf}")
    mid = util_icon("🪙", painted)
    return util_first_fitting([rich, mid, f"{painted}{suf}"], avail)


BUILDERS: dict[str, Any] = {
    "path": seg_path,
    "git_branch": seg_git_branch,
    "alt_git_worktree": seg_alt_git_worktree,
    "git_dirty": seg_git_dirty,
    "model": seg_model,
    "context": seg_context,
    "included_total": seg_included_total,
    "included_auto": seg_included_auto,
    "included_api": seg_included_api,
    "reset": seg_reset,
    "on_demand": seg_on_demand,
    "process_memory": seg_process_memory,
    "system_memory": seg_system_memory,
    "render_time": seg_render_time,
    "slowest": seg_slowest,
}


def _safe_build(key: str, ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    fn = BUILDERS.get(key)
    if fn is None:
        return None
    try:
        return fn(ctx, avail, theme)
    except Exception:  # noqa: BLE001 — never-blank isolation
        return None


def _crown_slowest(ctx: SimpleNamespace, key: str, ns: int) -> None:
    if key in _SLOWEST_META:
        return
    cur = ctx.slowest
    if cur is None or ns > cur[1]:
        ctx.slowest = (key, ns)


def core_render(ctx: SimpleNamespace) -> str:
    cfg: Config = ctx.config
    theme: Theme = ctx.theme
    # Claude: reserve RIGHT_MARGIN so emoji-width miscounts don't wrap.
    budget = max(int(ctx.cols) - RIGHT_MARGIN, 1)
    sep_w = util_visible_width(SEP)
    built: dict[tuple[int, str], str] = {}
    term_lines = int(getattr(ctx, "lines", 40) or 40)

    # Pass A — non-meta (shrinking avail per line → builder variants pick fit)
    for line_i, (min_rows, keys) in enumerate(cfg.layout):
        if term_lines < min_rows:
            continue
        used = 0
        for key in keys:
            if not cfg.segments.get(key, False):
                continue
            if key in _SLOWEST_META:
                continue
            sep = sep_w if used else 0
            avail = max(budget - used - sep, 0)
            t0 = time.perf_counter_ns()
            s = _safe_build(key, ctx, avail, theme)
            ns = time.perf_counter_ns() - t0
            if not s:
                continue
            if key in PINNED or util_visible_width(s) <= avail:
                built[(line_i, key)] = s
                used += util_visible_width(s) + sep
                _crown_slowest(ctx, key, ns)

    # Pass B — meta once (full budget; placed per-line in assemble)
    meta_built: dict[str, str] = {}
    for min_rows, keys in cfg.layout:
        if term_lines < min_rows:
            continue
        for key in keys:
            if key not in _SLOWEST_META or key in meta_built:
                continue
            if not cfg.segments.get(key, False):
                continue
            s = _safe_build(key, ctx, budget, theme)
            if s:
                meta_built[key] = s

    # Assemble — PINNED always kept even if slightly over budget
    lines_out: list[str] = []
    for line_i, (min_rows, keys) in enumerate(cfg.layout):
        if term_lines < min_rows:
            continue
        line_built = {k: v for (i, k), v in built.items() if i == line_i}
        line_built.update(meta_built)
        kept: list[str] = []
        used = 0
        for key in keys:
            if not cfg.segments.get(key, False):
                continue
            s = line_built.get(key)
            if not s:
                continue
            sep = sep_w if kept else 0
            if key in PINNED or used + sep + util_visible_width(s) <= budget:
                kept.append(s)
                used += util_visible_width(s) + sep
        if kept:
            lines_out.append(SEP.join(kept))
    return "\n".join(lines_out)


def render_for_test(
    payload: dict[str, Any],
    env: dict[str, str],
    *,
    now: float | int | None = None,
) -> str:
    theme = default_theme()
    config = load_config(env)
    ctx = build_context(payload, env, now=now, theme=theme, config=config)
    ctx.t_start = time.perf_counter_ns()
    clock = time.time() if now is None else float(now)
    try:
        quota = fetch_quota(env, now=clock)
        qctx = context_from_quota(quota, now_ms=int(clock * 1000))
        for k, v in vars(qctx).items():
            setattr(ctx, k, v)
    except Exception:  # noqa: BLE001 — hide quota, keep local/payload
        pass
    return core_render(ctx)


def render_from_raw(
    raw: bytes,
    env: dict[str, str],
    *,
    dump_payload_path: str | None = None,
    now: float | int | None = None,
) -> str:
    if dump_payload_path:
        path = Path(dump_payload_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".poc-dump.", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(raw)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    try:
        if not raw.strip():
            return ""
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            return ""
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        return ""
    return render_for_test(payload, env, now=now)


def safe_render(
    raw: bytes,
    env: dict[str, str],
    *,
    now: float | int | None = None,
) -> str:
    try:
        return render_from_raw(raw, env, now=now)
    except Exception:  # noqa: BLE001 — never raises
        return ""


def main(
    argv: list[str] | None = None,
    stdin: BinaryIO | None = None,
    env: dict[str, str] | None = None,
) -> int:
    argv = list(sys.argv if argv is None else argv)
    env = dict(os.environ if env is None else env)
    dump_path: str | None = None
    if "--dump-payload" in argv:
        i = argv.index("--dump-payload")
        if i + 1 < len(argv):
            dump_path = argv[i + 1]
    src = sys.stdin.buffer if stdin is None else stdin
    raw = src.read()
    out = render_from_raw(raw, env, dump_payload_path=dump_path)
    if out:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
