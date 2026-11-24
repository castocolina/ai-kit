"""39 R9, D-14: the optional after-approval pass of file-editing lenses.

Off unless [review] edit_lens_pass is true; one execute-role runner call on a lane whose
final argv shows write workspace or full; the owner accepts or rejects the diff; a rejection
restores the recorded bytes. cli.py registers it; this module never imports cli.
"""

import base64
import difflib
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Callable
from contextlib import contextmanager
from typing import NamedTuple

from ai_kit_spec import capability_block, config_io, prompt_guard, skill_table
from ai_kit_spec.detection import runtime_id
from ai_kit_spec.execute_dispatch import build_soft_confinement_guidance
from ai_kit_spec.runner_dispatch import RunnerSeams, run_runner, spec_with_effort

MSG_OFF = "edit-lens-pass: off ([review] edit_lens_pass is not true); no pass ran"
MSG_NO_LENS = "edit-lens-pass: no edit_lens skill present; no pass ran"
MSG_NO_FILES = "edit-lens-pass: no approved files; no pass ran"
MSG_NO_LANE = ("edit-lens-pass: no configured execute lane shows write workspace or full; "
               "no pass ran")
MSG_PENDING = "edit-lens-pass: a pass is waiting for --accept or --reject ({path})"
MSG_RUNNING = "edit-lens-pass: the pass is still running ({path})"
MSG_LOCKED = "edit-lens-pass: lane locked (runner status locked); no pass ran"
MSG_KEPT = "edit-lens-pass: the lane ended with status {status}; the record is kept"
MSG_SCOPE = ("edit-lens-pass: only the approved files are recorded; check git status for "
             "other changes")
MSG_HINT = ("edit-lens-pass: review the diff, then run edit-lens-pass --cwd {cwd} --accept or "
            "edit-lens-pass --cwd {cwd} --reject")
MSG_SKIPPED = "edit-lens-pass: skipped {shown} ({reason})"
MSG_CHANGED = "edit-lens-pass: {rel} changed after the pass; not restored, the record is kept"
MSG_NONE_WAITING = "edit-lens-pass: no pass is waiting"
MSG_ACCEPTED = "edit-lens-pass: accepted {n} file(s)"
MSG_RESTORED = "edit-lens-pass: restored {rel}"
MSG_REJECTED = "edit-lens-pass: rejected, {n} file(s) restored"
MSG_BUSY = "edit-lens-pass: another accept or reject is running"
MSG_NO_GIT = ("edit-lens-pass: not a git checkout; changes outside the approved files cannot "
              "be detected")
MSG_OUTSIDE = ("edit-lens-pass: changes outside the approved files: {paths}; a rejection "
               "will not undo them")
MSG_INTERRUPTED = "edit-lens-pass: the pass was interrupted; restoring the recorded files"
EDIT_PROMPT = ("Apply the loaded editing skills to these approved files only, in place, and change "
               "no other file:\n{files}\nLeave the edits uncommitted; the owner reviews the diff.")


def pass_enabled(cwd: str, env: dict) -> bool:
    """Read the opt-in from layered configuration."""
    return config_io.cfg_layered_table(cwd, env, "review").get("edit_lens_pass") is True


def _run(spec, prompt, env):
    return run_runner(spec, prompt, RunnerSeams(env_fn=lambda: dict(env)))


class PassSeams(NamedTuple):
    """Replaceable external operations."""
    print_argv_fn: Callable = capability_block.DEFAULT_SEAMS.print_argv_fn
    scan_fn: Callable = skill_table.scan
    run_fn: Callable = _run
    print_fn: Callable = print


DEFAULT_PASS_SEAMS = PassSeams()


class PassRequest(NamedTuple):
    """One requested edit pass."""
    cwd: str
    files: tuple
    env: dict
    timeout_s: int = 1800


def record_path(cwd, env) -> str:
    """Return the checkout-specific private state path."""
    base = env.get("XDG_STATE_HOME") or os.path.join(env.get("HOME", ""), ".local", "state")
    key = hashlib.sha256(prompt_guard.repo_root(cwd).encode("utf-8")).hexdigest()[:16]
    return os.path.join(base, "ai-kit", "edit-pass", key, "record.json")


def _write_temp(path, record):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle)
        os.chmod(tmp, 0o600)
        return tmp
    except BaseException:
        os.unlink(tmp)
        raise


def _claim(path, record) -> bool:
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    tmp = _write_temp(path, record)
    try:
        try:
            os.link(tmp, path)
        except FileExistsError:
            return False
        return True
    finally:
        os.unlink(tmp)


def _publish(path, record):
    tmp = _write_temp(path, record)
    try:
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _load(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None


def _state(record) -> str:
    if record.get("state") == "running":
        try:
            os.kill(record["pid"], 0)
        except ProcessLookupError:
            return "interrupted"
        except PermissionError:
            pass
    return record["state"]


@contextmanager
def _decision_lock(path):
    """Yield True when locked, False when busy, None when no record folder exists.

    No folder means no pass is waiting, so nothing is created for a lock.
    """
    lock = os.path.join(os.path.dirname(path), "decide.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        yield False
        return
    except FileNotFoundError:
        yield None
        return
    os.close(fd)
    try:
        yield True
    finally:
        if os.path.exists(lock):
            os.unlink(lock)


def _git_state(repo):
    try:
        head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True,
                              check=False, timeout=30)
        status = subprocess.run(["git", "-C", repo, "status", "--porcelain=v1", "-z",
                                 "--untracked-files=all"], capture_output=True, check=False,
                                timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if head.returncode or status.returncode:
        return None
    entries = status.stdout.decode("utf-8", "surrogateescape").split("\0")
    dirty = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        if len(entry) >= 4:
            dirty.append(entry[3:])
            if "R" in entry[:2] or "C" in entry[:2]:
                index += 1
                if index < len(entries):
                    dirty.append(entries[index])
        index += 1
    return {"head": head.stdout.decode("ascii").strip(), "dirty": sorted(dirty)}


def _approved(req, scan):
    del scan
    repo = prompt_guard.repo_root(req.cwd)
    bad = prompt_guard.validate_values([(f"files[{i}]", v) for i, v in enumerate(req.files)],
                                       repo, [], base=repo)
    rejected = {item["position"] for item in bad}
    kept = []
    for i, value in enumerate(req.files):
        if f"files[{i}]" in rejected:
            continue
        path = os.path.realpath(os.path.join(repo, value))
        if not os.path.isfile(path):
            bad.append({"shown": prompt_guard.escape_value(value), "reason": "path_unresolvable"})
        elif path not in kept:
            kept.append(path)
    return kept, bad


def pick_lane(cwd, env, seams):
    """Select the first configured lane whose preview reports write access."""
    entries = config_io.cfg_resolve_quiet(cwd, env)
    for entry in entries.get("execute") or []:
        if not isinstance(entry, dict) or not entry.get("runtime"):
            continue
        spec = spec_with_effort(runtime_id(entry["runtime"]), entry.get("model", ""), "exec", 1800,
                                {**entry, **(entry.get("extra") or {}), "cwd": cwd})
        lines = seams.print_argv_fn(spec, env)
        if capability_block.lane_facts(lines).write["value"] in ("workspace", "full"):
            return spec, lines
    return None


def _diff_line(rel, before: bytes, after: bytes | None) -> str:
    if after is None:
        return f"deleted {rel}"
    if before == after:
        return f"unchanged {rel}"
    diff = list(difflib.unified_diff(before.decode("utf-8", "replace").splitlines(),
                                     after.decode("utf-8", "replace").splitlines(), lineterm=""))
    added = sum(line.startswith("+") for line in diff[2:])
    removed = sum(line.startswith("-") for line in diff[2:])
    return f"edited {rel} +{added} -{removed}"


def _preflight(req, seams):
    if not pass_enabled(req.cwd, req.env):
        seams.print_fn(MSG_OFF)
        return 0
    path = record_path(req.cwd, req.env)
    record = _load(path)
    if record is not None:
        msg = MSG_RUNNING if _state(record) == "running" else MSG_PENDING
        seams.print_fn(msg.format(path=path))
        return 2
    scan = seams.scan_fn(req.env, req.cwd)
    if not any(row.get("role") == "edit_lens" for host in scan.values()
               if isinstance(host, dict) for row in host.get("skills", [])):
        seams.print_fn(MSG_NO_LENS)
        return 0
    files, bad = _approved(req, scan)
    for row in bad:
        seams.print_fn(MSG_SKIPPED.format(**row))
    if not files:
        seams.print_fn(MSG_NO_FILES)
        return 0
    picked = pick_lane(req.cwd, req.env, seams)
    if picked is None:
        seams.print_fn(MSG_NO_LANE)
        return 0
    return files, picked[0]


def _snapshot(files, repo):
    rows = []
    for path in files:
        with open(path, "rb") as handle:
            raw = handle.read()
        rows.append({"path": path, "rel": os.path.relpath(path, repo), "pre_sha256": _sha(raw),
                     "pre_b64": base64.b64encode(raw).decode("ascii"), "post_sha256": None,
                     "mode": stat.S_IMODE(os.stat(path).st_mode), "restored": False})
    return rows


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read_current(path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except FileNotFoundError:
        return None


def _finish(req, seams, record, before, result):
    path = record_path(req.cwd, req.env)
    after = _git_state(record["repo"])
    outside = []
    if before is not None and after is not None:
        outside = sorted(set(after["dirty"]) - set(before["dirty"]) -
                         {row["rel"] for row in record["files"]})
        if before["head"] != after["head"]:
            outside.append("HEAD moved")
    record.update(state="ready", outside=outside)
    for row in record["files"]:
        current = _read_current(row["path"])
        row["post_sha256"] = None if current is None else _sha(current)
    _publish(path, record)
    if outside:
        seams.print_fn(MSG_OUTSIDE.format(paths=", ".join(outside)))
    for row in record["files"]:
        seams.print_fn(_diff_line(row["rel"], base64.b64decode(row["pre_b64"]),
                                  _read_current(row["path"])))
    if result.returncode != 0:
        seams.print_fn(MSG_KEPT.format(status=(result.status or {}).get("status")))
    seams.print_fn(MSG_SCOPE)
    seams.print_fn(MSG_HINT.format(cwd=req.cwd))
    return 0 if result.returncode == 0 else (result.returncode or 1)


def _execute(req, seams, state):
    files, spec = state
    repo = prompt_guard.repo_root(req.cwd)
    spec = spec._replace(cwd=repo, timeout_s=req.timeout_s)
    rels = tuple(os.path.relpath(file, repo) for file in files)
    text = EDIT_PROMPT.format(files="\n".join("- " + rel for rel in rels))
    lane = capability_block.LaneRequest(spec.runtime, spec.model, "execute", repo, spec,
                                       soft_confinement=build_soft_confinement_guidance(repo),
                                       lens_role="edit_lens")
    composed = capability_block.compose_for_lane(
        lane, text, rels, req.env,
        capability_block.ComposeSeams(print_argv_fn=seams.print_argv_fn, scan_fn=seams.scan_fn))
    try:
        return _execute_composed(req, seams, (files, spec, text), composed)
    finally:
        capability_block.cleanup(composed)


def _execute_composed(req, seams, inputs, composed):
    files, spec, text = inputs
    if composed.refusal:
        seams.print_fn(json.dumps(composed.refusal, sort_keys=True))
        return 65
    if not composed.skill_names:
        seams.print_fn(MSG_NO_LENS)
        return 0
    if composed.facts.write["value"] not in ("workspace", "full"):
        seams.print_fn(MSG_NO_LANE)
        return 0
    repo = spec.cwd
    before = _git_state(repo)
    if before is None:
        seams.print_fn(MSG_NO_GIT)
    path = record_path(req.cwd, req.env)
    record = {"version": 1, "state": "running", "pid": os.getpid(), "repo": repo,
              "files": _snapshot(files, repo)}
    if not _claim(path, record):
        existing = _load(path)
        msg = MSG_RUNNING if existing and _state(existing) == "running" else MSG_PENDING
        seams.print_fn(msg.format(path=path))
        return 2
    result = seams.run_fn(capability_block.lane_spec(spec, composed),
                          capability_block.with_block(composed.block, text), req.env)
    if (result.status or {}).get("status") == "locked":
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)
        seams.print_fn(MSG_LOCKED)
        return 75
    return _finish(req, seams, record, before, result)


def run_pass(req: PassRequest, seams: PassSeams) -> int:
    """Run an opted-in edit pass and retain its byte snapshot for a decision."""
    state = _preflight(req, seams)
    return state if isinstance(state, int) else _execute(req, seams, state)


def _restore(row, repo, interrupted, print_fn):
    path = row["path"]
    bad = prompt_guard.validate_values([("file", path)], repo, [], base=repo)
    if bad or (os.path.exists(path) and not os.path.isfile(path)):
        print_fn(MSG_SKIPPED.format(shown=prompt_guard.escape_value(path),
                                    reason="path_unresolvable"))
        return False
    try:
        raw = base64.b64decode(row["pre_b64"], validate=True)
    except (ValueError, TypeError):
        raw = b""
    if _sha(raw) != row["pre_sha256"]:
        print_fn(MSG_SKIPPED.format(shown=prompt_guard.escape_value(path),
                                    reason="path_unresolvable"))
        return False
    current = _read_current(path)
    digest = None if current is None else _sha(current)
    if not interrupted and digest != row["post_sha256"]:
        print_fn(MSG_CHANGED.format(rel=row["rel"]))
        return False
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        os.chmod(tmp, row["mode"])
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    row.update(restored=True, post_sha256=row["pre_sha256"])
    return True


def _reject_locked(path, print_fn):
    record = _load(path)
    if record is None:
        print_fn(MSG_NONE_WAITING)
        return 1
    state = _state(record)
    if state == "running":
        print_fn(MSG_RUNNING.format(path=path))
        return 2
    if state == "interrupted":
        print_fn(MSG_INTERRUPTED)
    count = 0
    for row in record["files"]:
        if (not row.get("restored")
                and _restore(row, record["repo"], state == "interrupted", print_fn)):
            _publish(path, record)
            count += 1
            print_fn(MSG_RESTORED.format(rel=row["rel"]))
    outside = record.get("outside", [])
    if outside:
        print_fn(MSG_OUTSIDE.format(paths=", ".join(outside)))
    complete = all(row.get("restored") for row in record["files"]) and not outside
    if complete:
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)
    print_fn(MSG_REJECTED.format(n=count))
    return 0 if complete else 1


def accept(cwd, env, print_fn) -> int:
    """Keep the edits and discard a completed pass record."""
    path = record_path(cwd, env)
    with _decision_lock(path) as locked:
        if locked is False:
            print_fn(MSG_BUSY)
            return 2
        record = None if locked is None else _load(path)
        if not record:
            print_fn(MSG_NONE_WAITING)
            return 1
        if _state(record) == "running":
            print_fn(MSG_RUNNING.format(path=path))
            return 2
        shutil.rmtree(os.path.dirname(path))
        print_fn(MSG_ACCEPTED.format(n=len(record["files"])))
        return 0


def reject(cwd, env, print_fn) -> int:
    """Restore recorded bytes unless the owner changed them after the pass."""
    path = record_path(cwd, env)
    with _decision_lock(path) as locked:
        if locked is False:
            print_fn(MSG_BUSY)
            return 2
        if locked is None:
            print_fn(MSG_NONE_WAITING)
            return 1
        return _reject_locked(path, print_fn)


def register_parsers(sub) -> None:
    """Register the optional edit pass command."""
    parser = sub.add_parser(
        "edit-lens-pass",
        help=("run the optional after-approval pass of edit_lens skills, or accept or reject "
              "its diff"),
    )
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--files", nargs="*", default=[])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--accept", action="store_true")
    group.add_argument("--reject", action="store_true")
    parser.add_argument("--timeout", type=int, default=1800)


def cmd_edit_lens_pass(args, deps) -> int:
    """Run or decide an edit pass."""
    env = deps.env_fn()
    cwd = os.path.abspath(args.cwd)
    if args.accept:
        return accept(cwd, env, print)
    if args.reject:
        return reject(cwd, env, print)
    return run_pass(PassRequest(cwd, tuple(args.files), env, args.timeout), DEFAULT_PASS_SEAMS)


COMMANDS = {"edit-lens-pass": cmd_edit_lens_pass}
