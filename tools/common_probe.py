"""Host-neutral side-effecting probes for the Phase 23 D-02 status-line split."""
# pyright: strict

import json
import os
import subprocess
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional

from common_types import (
    GIT_CACHE_TTL,
    GIT_TIMEOUT_S,
    Env,
    GitSnapshot,
    fmt_ago,
    util_branch_from_porcelain,
    util_git_cache_path,
    util_to_int,
)

if TYPE_CHECKING:
    from common_render import Context
    from common_types import Config

# ═══ 3. probe_ — side-effecting data gatherers (git / proc / fs / subprocess) ═


# Two sub-tiers: raw gatherers on primitives (probe_git_snapshot(work_dir), …) and
# the memoized segment-facing accessors signed (ctx) (probe_git_for, probe_rss, …).
# Classified by NATURE (side-effecting), not by which segment consumes them.


def probe_terminal_size(env: Env) -> tuple[int, int, bool]:
    """Resolve (cols, lines, assumed). Fallback chain, first hit wins per dimension:
      1. STATUSLINE_COLS / STATUSLINE_LINES env
      2. COLUMNS / LINES env
      3. stty size      (via /dev/tty)
      4. tput cols/lines (via /dev/tty — macOS / setups where stty size is absent)
      5. assumed 200x40 default (assumed=True)"""
    def _int(*keys: str) -> int | None:
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
            with open("/dev/tty", encoding="utf-8") as tty:
                def _run(*cmd: str) -> str:
                    return subprocess.run(list(cmd), stdin=tty, capture_output=True,
                                          text=True, timeout=1, check=False).stdout
                size = _run("stty", "size").split()
                if len(size) == 2:
                    lines = lines or int(size[0])
                    cols = cols or int(size[1])
                if cols is None or lines is None:
                    cols = cols or util_to_int(_run("tput", "cols").strip())
                    lines = lines or util_to_int(_run("tput", "lines").strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    assumed = False
    if cols is None:
        cols, assumed = 200, True
    if lines is None:
        lines, assumed = 40, True
    return cols, lines, assumed


def probe_git_worktree_info(work_dir: str) -> tuple[bool, bool, str, str, str]:
    """(in_repo, is_worktree, wt_name, root_name, root_path) from ONE `git
    rev-parse`. is_worktree is True when work_dir sits in a linked worktree
    (git-dir != git-common-dir). wt_name is that worktree directory's
    basename (from --show-toplevel), only when in a linked worktree; ""
    otherwise. root_name/root_path are the MAIN checkout's directory
    basename/absolute-path — dirname of --git-common-dir, the one physical
    .git store every worktree of a repo shares, so both stay the same no
    matter which worktree work_dir is in. --git-common-dir normally ends in
    "/.git" and dirname() of that is the repo root; but a bare repo (or an
    unusual layout) can report a --git-common-dir that does NOT end in
    "/.git" — there, dirname() would walk one directory too far up and
    report the repo's PARENT as root_name/root_path. Guard: only take
    dirname() when the common-dir's basename is literally ".git"; otherwise
    the common-dir IS the root, so use it directly.
    --path-format=absolute forces all three rev-parse outputs to be absolute
    so this dirname()/basename() math is correct regardless of the caller's
    cwd, and so root_path is always a usable absolute path. Outside any repo
    -> (False, False, "", "", "")."""
    try:
        out = subprocess.run(
            ["git", "-C", work_dir, "rev-parse", "--path-format=absolute",
             "--git-dir", "--git-common-dir", "--show-toplevel"],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_S, check=False).stdout
    except subprocess.TimeoutExpired:
        return False, False, "", "", ""
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False, False, "", "", ""                 # not a git repo
    is_worktree = lines[0] != lines[1]          # git-dir != git-common-dir
    common_dir = lines[1].rstrip("/")
    # bare repo / unusual layout: no ".git" to strip
    root_dir = os.path.dirname(common_dir) if os.path.basename(common_dir) == ".git" else common_dir
    root_name = os.path.basename(root_dir)
    top = lines[2] if len(lines) >= 3 else ""
    name = os.path.basename(top.rstrip("/")) if (is_worktree and top) else ""
    return True, is_worktree, name, root_name, root_dir


def probe_worktree_info_cached(
    work_dir: str, ttl: int, cache_base: str,
) -> tuple[bool, bool, str, str, str]:
    """probe_git_worktree_info wrapped in an on-disk TTL cache — the worktree rev-parse
    rarely changes, so it is cached ~ttl s keyed by work_dir. The cache is active
    only when ttl > 0 AND a cache_base is resolved: ttl <= 0 forces a fresh
    rev-parse every render, and an empty cache_base means no cache location was
    resolved (a direct/test call with no Config) so we never touch disk — this is
    what keeps such calls from writing a stray `./git/` under the cwd. In
    production cfg_load_config always supplies a real cache_base. Cache I/O is
    best-effort."""
    cached = ttl > 0 and bool(cache_base)
    path = util_git_cache_path(work_dir, cache_base) if cached else ""
    if cached:
        try:
            if time.time() - os.stat(path).st_mtime < ttl:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                return (d["in_repo"], d["is_worktree"], d["wt_name"],
                        d.get("root_name", ""), d.get("root_path", ""))
        except (OSError, ValueError, KeyError):
            pass
    info = probe_git_worktree_info(work_dir)
    if cached:                          # caching off (ttl<=0 or no cache_base) -> never write
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"in_repo": info[0], "is_worktree": info[1],
                           "wt_name": info[2], "root_name": info[3],
                           "root_path": info[4]}, f)
        except OSError:
            pass
    return info


def probe_git_snapshot(work_dir: str, config: Optional["Config"] = None) -> "GitSnapshot":
    """The single git probe behind the `git_branch`, `git_dirty`, and
    `alt_git_worktree` segments.

    `config` is the resolved Config object — the probe reads its cache TTL and
    cache_base FROM it (never from env, never as bare args). config=None (direct/
    test calls with no Config) falls back to the built-in defaults.

    Returns GitSnapshot(in_repo, branch, dirty, is_worktree, wt_name, root_name,
    root_path). `branch` and `dirty` come from one always-fresh `git status --porcelain --branch`
    (full untracked walk); the worktree rev-parse is cached ~ttl s on disk under
    cache_base/git/ (it rarely changes). The probe owns its policy and always
    does the full work — there are no per-call gating knobs: laziness is the
    compute gate (Context._git only runs when an enabled git segment reads a git
    field, so a disabled git segment never triggers the probe at all)."""
    ttl = (config.git or {}).get("cache_ttl", GIT_CACHE_TTL) if config else GIT_CACHE_TTL
    cache_base = config.cache_base if config else ""
    try:
        out = subprocess.run(
            ["git", "-C", work_dir, "status", "--porcelain", "--branch"],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_S, check=False
        ).stdout.splitlines()
    except subprocess.TimeoutExpired:
        out = []
    branch = util_branch_from_porcelain(out[0] if out else "")
    changes = out[1:]   # change lines follow the `## <branch>` header
    if any(ln.startswith(("??", "A", "D")) or ln.startswith(" D") for ln in changes):
        dirty = "untracked"
    elif any(ln.strip() for ln in changes):
        dirty = "modified"
    else:
        dirty = "clean"
    in_repo, is_worktree, wt_name, root_name, root_path = probe_worktree_info_cached(
        work_dir, ttl, cache_base)
    return GitSnapshot(in_repo, branch, dirty, is_worktree, wt_name, root_name, root_path)


# ── Process RSS (cross-platform) ──────────────────────────────────────────────
# Platform probe: Linux → /proc readers; macOS/other → `ps` readers; any read
# failure → None (the segment hides). Three facts per pid — command name, parent
# pid, resident memory (kB) — exposed by six thin readers (_comm/_ppid/_rss_kb ×
# _via_proc/_via_ps). probe_rss_bytes picks a backend by the probe and walks the
# parent chain, returning RSS ONLY on a confirmed `claude` ancestor — otherwise
# None, so it never reports a stray process (the wezterm <10mb bug). The readers
# return comm verbatim; probe_rss_bytes is the single basename-normalization point.
def probe_comm_via_proc(pid: int) -> str | None:
    """Read process name from /proc/<pid>/comm, or None on error."""
    try:
        with open(f"/proc/{pid}/comm", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def probe_ppid_via_proc(pid: int) -> int | None:
    """Read parent PID from /proc/<pid>/stat field 4, or None on error."""
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
            return int(f.read().split()[3])
    except (OSError, IndexError, ValueError):
        return None


def probe_rss_kb_via_proc(pid: int) -> int | None:
    """Read VmRSS (kB) from /proc/<pid>/status, or None on error."""
    try:
        with open(f"/proc/{pid}/status", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except (OSError, IndexError, ValueError):
        return None
    return None


def probe_ps_field(pid: int, fieldname: str) -> str | None:
    """One `ps -o <fieldname>= -p <pid>` value as a stripped string, or None."""
    try:
        out = subprocess.run(["ps", "-o", f"{fieldname}=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=1,
                             check=False).stdout.strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def probe_comm_via_ps(pid: int) -> str | None:
    """Read process name via `ps -o comm=`, or None on error."""
    return probe_ps_field(pid, "comm")


def probe_ppid_via_ps(pid: int) -> int | None:
    """Read parent PID via `ps -o ppid=`, or None on error."""
    return util_to_int(probe_ps_field(pid, "ppid"))


def probe_rss_kb_via_ps(pid: int) -> int | None:
    """Read RSS (kB) via `ps -o rss=`, or None on error."""
    return util_to_int(probe_ps_field(pid, "rss"))


def probe_has_proc() -> bool:
    """True when the Linux /proc filesystem is available (else the ps readers are used)."""
    return os.path.isdir("/proc")


def probe_cmdline_via_proc(pid: int) -> str | None:
    """Command line of /proc/<pid> with NUL separators as spaces, or None on error.

    Non-UTF-8 bytes are decoded with replacement; callers only substring-match it."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read()
    except OSError:
        return None
    return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()


def probe_exe_via_proc(pid: int) -> str | None:
    """Program path of /proc/<pid> (the exe link), or None on error."""
    try:
        return os.readlink(f"/proc/{pid}/exe")
    except OSError:
        return None


def probe_cmdline_via_ps(pid: int) -> str | None:
    """Command line via `ps -o command=`, or None on error."""
    return probe_ps_field(pid, "command")


def probe_ancestor_rss_bytes(match: "Callable[[int], bool | None]", depth: int) -> int | None:
    """VmRSS (bytes) of the nearest ancestor for which match(pid) is True, or None.

    The walk starts at os.getppid(), so the status-line script itself is never matched.
    match(pid) returns None for an unreadable entry, which ends the walk; the walk also
    stops when the parent is 0 or the pid itself, or after `depth` ancestors."""
    use_proc = probe_has_proc()
    ppid_of = probe_ppid_via_proc if use_proc else probe_ppid_via_ps
    rss_kb_of = probe_rss_kb_via_proc if use_proc else probe_rss_kb_via_ps

    pid = os.getppid()
    for _ in range(depth):
        verdict = match(pid)
        if verdict is None:
            return None
        if verdict:
            kb = rss_kb_of(pid)
            return kb * 1024 if kb is not None else None
        parent = ppid_of(pid)
        if parent is None or parent in (0, pid):
            return None
        pid = parent
    return None


# ── per-render memoized probe accessors (module-level; cost lands in FR-R.2) ──

def probe_memo(ctx: "Context", key: str, fn: "Callable[[], Any]") -> Any:
    """Run fn() once per render, caching the result on ctx.probe_cache."""
    cache = ctx.probe_cache
    if key not in cache:
        cache[key] = fn()
    return cache[key]


def probe_git_for(ctx: "Context") -> "GitSnapshot":
    """Memoized git snapshot for this render (branch/dirty/worktree/…)."""
    return probe_memo(ctx, "git",
                 lambda: probe_git_snapshot(ctx.work_dir, ctx.line_conf))


def probe_transcript_ago(ctx: "Context") -> str:
    """Memoized age of the payload's transcript file (time since its last write), or ''."""
    def _compute() -> str:
        path = ctx.transcript_path
        if not path or not os.path.isfile(path):
            return ""
        try:
            return fmt_ago(int(time.time()) - int(os.path.getmtime(path)))
        except OSError:
            return ""
    return probe_memo(ctx, "ago", _compute)
