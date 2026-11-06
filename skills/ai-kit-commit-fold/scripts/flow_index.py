"""Index refresh for one checkout: codegraph and graphify (30-01: R2, R3, D-08, D-12).

This module never reads files under `.codegraph/` (D-08): every codegraph decision comes
from `codegraph status --json`. Every tool call passes the checkout as `cwd` and `.` as its
own argv element, never a joined shell string. A failing or missing tool is reported as a
line and never raises, so `fold.py index` exits 0. Project-specific copies and locks live in
the adapter layer (`fold_adapters`), so this flow module names no framework.
"""

import contextlib
import datetime
import fcntl
import functools
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import flow_record
import fold_adapters

LOCK_NAME = "ai-kit-index.lock"
QUEUE_NAME = "ai-kit-index-queue"
QUEUE_LOCK_NAME = "ai-kit-index-queue.lock"
LOG_NAME = "ai-kit-index.log"
_FOLD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fold.py")
# Hooks run before a new checkout is queued: each gets the checkout top level, returns lines.
SEED_HOOKS: list = []


def _run_tool(argv, cwd, timeout=900):
    """Run one tool; return (rc, stdout, stderr). A missing or hung tool is not an exception."""
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False,
                              timeout=timeout)
    except FileNotFoundError:
        return 127, "", "not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"
    return proc.returncode, proc.stdout, proc.stderr


def _first_line(text, limit=80):
    lines = text.strip().splitlines()
    return (lines[0] if lines else "")[:limit]


def _git_out(top, *args):
    proc = subprocess.run(["git", "-C", top, *args], capture_output=True, text=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else ""


# ---- codegraph (R2) -------------------------------------------------------------------------


def _codegraph_status(top, run, exe):
    rc, out, _ = run([exe, "status", "--json"], top)
    if rc != 0:
        return None
    try:
        data = json.loads(out)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _codegraph_run(top, run, exe, verb, reason):
    """Run one codegraph verb and return its report line (the R2 line forms)."""
    rc, _, err = run([exe, *verb], top)
    shown = " ".join(["codegraph", *verb])
    if rc == 0:
        return f"codegraph: ran {shown}" + (f" {reason}" if reason else "")
    if "lock" in err.lower():
        return f"codegraph: {shown} refused: codegraph's lock is held; retried at the next point"
    return (f"codegraph: {shown} failed (exit {rc}: {_first_line(err)}); "
            "retried at the next point")


def codegraph_step(top, run=_run_tool, which=shutil.which):
    """R2 choice order: no own index -> `init -y`; reindex recommended -> `index`; else `sync`."""
    exe = which("codegraph")
    own = os.path.isdir(os.path.join(top, ".codegraph"))
    if exe is None:
        verb = "sync" if own else "init -y"
        return f"codegraph: not installed; would run codegraph {verb}"
    if not own:
        return _codegraph_run(top, run, exe, ["init", "-y"], "(no index of its own)")
    status = _codegraph_status(top, run, exe)
    if status is None:
        return _codegraph_run(top, run, exe, ["index"], "(status unreadable)")
    if status.get("worktreeMismatch") or status.get("initialized") is False:
        reason = "(worktreeMismatch)" if status.get("worktreeMismatch") else "(no index of its own)"
        return _codegraph_run(top, run, exe, ["init", "-y"], reason)
    if (status.get("index") or {}).get("reindexRecommended"):
        return _codegraph_run(top, run, exe, ["index"], "(reindex recommended)")
    return _codegraph_run(top, run, exe, ["sync"], "")


# ---- graphify (R3) --------------------------------------------------------------------------


def _graph_built_at_head(top):
    """True when graphify-out/graph.json is a graph object, with a node list, built at HEAD."""
    try:
        with open(os.path.join(top, "graphify-out", "graph.json"), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return False
    head = _git_out(top, "rev-parse", "HEAD")
    return (isinstance(data, dict) and isinstance(data.get("nodes"), list)
            and bool(head) and data.get("built_at_commit") == head)


def _graphify_version(top, run, exe):
    rc, out, _ = run([exe, "--version"], top)
    lines = out.strip().splitlines()
    return lines[0] if rc == 0 and lines else "unknown"


def _status_fields(status, rc, duration_ms, head, version):
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"ts": stamp, "status": status, "exit_code": rc, "duration_ms": duration_ms,
            "head_at_build": head, "graphify_version": version}


def _build_failed_line(rc, err):
    if rc != 0:
        return (f"graphify: graphify update . failed (exit {rc}: {_first_line(err)}); "
                "previous graph kept")
    return "graphify: graphify update . wrote no graph; previous graph kept"


def graphify_step(top, run=_run_tool, which=shutil.which, clock=time.monotonic, sleep=time.sleep):
    """`graphify update .` in the checkout, then the project copy when it applies."""
    exe = which("graphify")
    if exe is None:
        return "graphify: not installed; would run graphify update ."
    if fold_adapters.index_project(top):
        held = fold_adapters.index_lock_wait(top, clock, sleep)
        if held is not None:
            return fold_adapters.index_lock_line(held, "build")
    started = clock()
    rc, _, err = run([exe, "update", "."], top)
    duration_ms = int((clock() - started) * 1000)
    head = _git_out(top, "rev-parse", "HEAD")
    copy = fold_adapters.index_copy_applies(top)
    if rc != 0 or not _graph_built_at_head(top):
        if copy:
            fold_adapters.index_write_status(
                top, _status_fields("failed", rc, duration_ms, head, "unknown"))
        return _build_failed_line(rc, err)
    if not copy:
        return ("graphify: ran graphify update .; graphify-out only "
                f"({fold_adapters.index_copy_skip_reason(top)})")
    # shortcut: the project's rebuilder can still start between this check and the copy;
    # its hook is not ours to edit, so the next boundary point rebuilds and recopies
    held = fold_adapters.index_lock_wait(top, clock, sleep)
    if held is not None:
        return fold_adapters.index_lock_line(held, "copy")
    fields = _status_fields("ok", rc, duration_ms, head, _graphify_version(top, run, exe))
    fold_adapters.index_publish_copy(top, fields)
    return f"graphify: ran graphify update .; copied to .planning/graphs/ (built at {head[:12]})"


# ---- refresh and the bare command -----------------------------------------------------------


def ensure_excluded(top, rels):
    """Add `<rel>/` to the common `info/exclude` for each unignored rel; return note lines."""
    notes = []
    exclude = flow_record.common_dir(top) / "info" / "exclude"
    for rel in rels:
        # The directory itself, not a file inside it: codegraph's own `*` .gitignore hides the
        # contents but leaves its `.gitignore` visible, so a probe inside would never add the entry.
        text = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
        if f"{rel}/" in text.splitlines():
            continue
        probe = subprocess.run(["git", "-C", top, "check-ignore", "-q", "--", rel],
                               capture_output=True, check=False)
        if probe.returncode == 0:
            continue
        prefix = "\n" if text and not text.endswith("\n") else ""
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with open(exclude, "a", encoding="utf-8") as handle:
            handle.write(f"{prefix}{rel}/\n")
        notes.append(f"note: ignored {rel}/ in .git/info/exclude")
    return notes


def refresh(top, run=_run_tool, which=shutil.which, clock=time.monotonic, sleep=time.sleep):
    """One refresh of `top`: codegraph line, graphify line, then the note lines."""
    codegraph_line = codegraph_step(top, run, which)
    graphify_line = graphify_step(top, run, which, clock, sleep)
    notes = []
    if fold_adapters.index_project(top) and which("graphify") is not None:
        note = fold_adapters.index_ensure_graphifyignore(top)
        if note:
            notes.append(note)
    rels = [".codegraph", "graphify-out"]
    if fold_adapters.index_copy_applies(top):
        rels.append(".planning/graphs")
    return [codegraph_line, graphify_line, *notes, *ensure_excluded(top, rels)]


# ---- job queue, log and the one-at-a-time lock (30-01: D-03 trigger one) ---------------------


def log_line(common, text):
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    # shortcut: the job log is never rotated; rotate when it passes 1 MB
    with open(common / LOG_NAME, "a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {text}\n")


@contextlib.contextmanager
def _queue_locked(common):
    with open(common / QUEUE_LOCK_NAME, "a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _queue_lines(common):
    queue = common / QUEUE_NAME
    return queue.read_text(encoding="utf-8").splitlines() if queue.is_file() else []


def _queue_pending(common):
    return bool(_queue_lines(common))


def enqueue(common, path):
    with _queue_locked(common), open(common / QUEUE_NAME, "a", encoding="utf-8") as handle:
        handle.write(f"{path}\n")


def pop(common):
    """Remove and return the first queued path, or None when the queue is empty."""
    with _queue_locked(common):
        lines = _queue_lines(common)
        if not lines:
            return None
        fd, tmp = tempfile.mkstemp(dir=common, prefix=QUEUE_NAME + ".")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.writelines(f"{line}\n" for line in lines[1:])
        os.replace(tmp, common / QUEUE_NAME)
        return lines[0]


@contextlib.contextmanager
def index_lock(common, clock=time.monotonic, sleep=time.sleep, deadline_s=600, on_release=None):
    """Hold the one job lock: yield True when acquired, False past the deadline.

    On exit an acquired lock is released, then `on_release()` runs (its errors are swallowed).
    """
    acquired = False
    try:
        with open(common / LOCK_NAME, "a+", encoding="utf-8") as handle:
            try:
                end = clock() + deadline_s
                while not acquired:
                    try:
                        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        acquired = True
                    except BlockingIOError:
                        if clock() >= end:
                            break
                        sleep(0.5)
                yield acquired
            finally:
                if acquired:
                    fcntl.flock(handle, fcntl.LOCK_UN)
    finally:
        if acquired and on_release is not None:
            with contextlib.suppress(Exception):  # a failed hand-off never fails the holder
                on_release()


def launch_runner(common, top, popen=None):
    """Start the detached runner when the job lock is free and the queue holds a path."""
    with open(common / LOCK_NAME, "a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        if not _queue_pending(common):
            return False
        argv = [sys.executable, _FOLD, "index", "--drain", "--lock-fd", str(handle.fileno()),
                "--repo", top]
        (popen or subprocess.Popen)(
            argv, pass_fds=(handle.fileno(),), start_new_session=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True)
        return True


def run_job(path, common, run=_run_tool, which=shutil.which):
    """Index one queued checkout, logging start, the report lines and end."""
    if not os.path.isdir(path):
        log_line(common, f"skipped {path}: gone")
        return
    log_line(common, f"start {path}")
    for line in refresh(path, run, which):
        log_line(common, f"  {line}")
    log_line(common, f"end {path}")


def drain(common, lock_fd=None, run=_run_tool, which=shutil.which):
    """Run queued jobs in queue order; hand the lock back when the queue refills after release."""
    if lock_fd is not None:
        with os.fdopen(lock_fd, "a+", encoding="utf-8") as handle:
            _drain_locked(common, handle, run, which)
        return
    with open(common / LOCK_NAME, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        _drain_locked(common, handle, run, which)


def _drain_locked(common, handle, run, which):
    while True:
        path = pop(common)
        while path is not None:
            run_job(path, common, run, which)
            path = pop(common)
        fcntl.flock(handle, fcntl.LOCK_UN)
        if not _queue_pending(common):
            return
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return  # another holder took the lock; its release hands off the rest


def _queue_checkout(repo, env, popen):
    if (os.environ if env is None else env).get("PRE_COMMIT_FROM_REF") != "0" * 40:
        return
    top = _git_out(repo, "rev-parse", "--show-toplevel")
    common = flow_record.common_dir(top)
    for hook in SEED_HOOKS:
        try:
            for line in hook(top) or []:
                log_line(common, f"  {line}")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # a seed hook is arbitrary code; its failure only logs, the queue still gains the path
            log_line(common, f"seed failed: {exc}")
    enqueue(common, top)
    log_line(common, f"queued {top}")
    launch_runner(common, top, popen)


def detach(repo, env=None, popen=None):
    """The post-checkout hook body: queue a new checkout and start the runner; never fails git."""
    with contextlib.suppress(Exception):
        _queue_checkout(repo, env, popen)
    return 0


def _top_of(repo):
    proc = subprocess.run(["git", "-C", repo, "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def cmd_index(args):
    """`fold.py index [--repo DIR]`: refresh this checkout now; always exit 0 on tool failure.

    `--detach` (post-checkout hook) and `--drain [--lock-fd N]` (the detached runner) share
    the one job lock; see the module docstring of `launch_runner`.
    """
    if getattr(args, "detach", False):
        importlib.import_module("flow_brief")  # registers the brief seeding hook (30-04)
        return detach(args.repo)
    top = _top_of(args.repo)
    if top is None:
        print("index: not inside a git checkout")
        return 2
    common = flow_record.common_dir(top)
    if getattr(args, "drain", False):
        drain(common, lock_fd=getattr(args, "lock_fd", None))
        return 0
    branch = _git_out(top, "rev-parse", "--abbrev-ref", "HEAD") or "-"
    with index_lock(common, on_release=functools.partial(launch_runner, common, top)) as held:
        if not held:
            print("index: lock held past 600 s; indexes not refreshed, retried at the next point")
            return 0
        lines = refresh(top)
    print(flow_record.render("index", "-", branch, lines, "done"))
    return 0
