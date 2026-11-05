"""Owner-started merge chain for the unit flow (plan 29.1-03 Task 3).

`fold.py merge-chain` runs only when the owner starts it. Every unmerged stacked unit's PR is
checked for base and state before any merge; then the walk goes bottom-up, one `pr merge --merge
--match-head-commit <tip>` per ready PR. After each merge the unit is recorded merged, the next
PR is retargeted to the trunk, and the merged unit's branches and recorded backup tags are
deleted (checkout-safe: a branch checked out in another worktree is kept and named), then the
local trunk is fast-forwarded. A run first finishes the cleanup of any unit recorded merged whose
branch or tags a failed earlier run left behind. A draft, a pending or failing check, or a
conflict stops the walk by name. When the units were linked into a GitHub stack (`linked` in the
record, set by the gh-stack PR step) GitHub refuses that synchronous merge, so one PUT
.../pulls/<last ready PR>/merge-async (head pinned by `sha`) merges the ready prefix and its
result is polled for a bounded time. `--unit-id` merges one recorded hotfix PR into its target and
touches no stacked unit.
"""

import contextlib
import fcntl
import json
import os
import subprocess
import time

import flow_git
import flow_pr
import flow_stack
from flow_git import primary_remote, run_git
from flow_record import (
    FlowError,
    common_dir,
    consented,
    find_entry,
    read_record,
    read_settings,
    render,
    write_record,
)

LOCK_NAME = "ai-kit-flow.lock"
_FIELDS = "number,state,isDraft,baseRefName,headRefName,headRefOid,mergeable,statusCheckRollup"
MERGE_WAIT, POLL_EVERY = 300, 5  # seconds; the docs give no polling interval
_now, _sleep = time.monotonic, time.sleep  # test seams


@contextlib.contextmanager
def chain_lock(repo):
    """Hold an flock on <git common dir>/ai-kit-flow.lock for one run.

    The file persists; the kernel drops the lock when the holder exits, so a lock file left by a
    dead run is simply taken over. The pid in the file is for the refusal report only."""
    path = common_dir(repo) / LOCK_NAME
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            held = os.read(fd, 32).decode("ascii", "replace").strip() or "unknown"
            raise FlowError("chain_locked",
                            f"another merge chain run (pid {held}) holds {LOCK_NAME}") from None
        os.ftruncate(fd, 0)
        os.write(fd, str(os.getpid()).encode("ascii"))
        yield
    finally:
        os.close(fd)


def _view(repo, settings, number):
    code, text, err = flow_pr.pr_cmd_split(repo, settings, "view", str(number), "--json", _FIELDS)
    if code != 0:
        raise FlowError("pr_failed", flow_pr.failure_line(text, err, "gh pr view"))
    return json.loads(text)


def _check_state(view):
    """'' when every check passed, else the stop reason."""
    for check in view.get("statusCheckRollup") or []:
        # CheckRun entries carry `conclusion`, StatusContext entries carry `state`.
        outcome = check.get("conclusion") or check.get("state") or ""
        if outcome in ("", "PENDING", "IN_PROGRESS", "QUEUED", "EXPECTED"):
            return "check pending"
        if outcome not in ("SUCCESS", "SKIPPED", "NEUTRAL"):
            return "check failing"
    return ""


def _stop_reason(view):
    if view["isDraft"]:
        return "draft"
    checks = _check_state(view)
    if checks:
        return checks
    mergeable = view.get("mergeable")
    if mergeable == "UNKNOWN":
        return "mergeability pending"
    if mergeable != "MERGEABLE":
        return "conflict"
    return ""


def _merge(repo, settings, entry, view):
    tip = flow_git.rev(repo, f"refs/heads/{entry['branch']}")
    code, out, err = flow_pr.pr_cmd_split(repo, settings, "merge", str(view["number"]), "--merge",
                                          "--match-head-commit", tip)
    if code != 0:
        raise FlowError("pr_failed", flow_pr.failure_line(out, err, "gh pr merge"))


def _confirmed(repo, settings, entry):
    """True when the forge reports the PR MERGED, or its tip is in the remote trunk."""
    if _view(repo, settings, entry["pr"]).get("state") == "MERGED":
        return True
    return flow_git.merged_on_remote(repo, settings, entry)


def _confirmed_prefix(repo, settings, ready, lines):
    for index, entry in enumerate(ready):
        if not _confirmed(repo, settings, entry):
            lines.append(f"stopped at {entry['id']}: merge not confirmed")
            return ready[:index]
    return ready


def _fetch(repo, settings):
    if consented(repo):
        run_git(repo, "fetch", "--prune", "-q", primary_remote(repo, settings))


def _head_branch(repo):
    """The checked-out branch name, or '' when HEAD is detached (symbolic-ref exits 1 then)."""
    proc = subprocess.run(["git", "-C", str(repo), "symbolic-ref", "--short", "-q", "HEAD"],
                          capture_output=True, text=True, check=False)
    return proc.stdout.strip()


def _worktree_of(repo, branch):
    """The path of another worktree that has `branch` checked out, else None."""
    current = os.path.realpath(run_git(repo, "rev-parse", "--show-toplevel").strip())
    path = None
    for line in run_git(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = os.path.realpath(line[len("worktree "):])
        elif line == f"branch refs/heads/{branch}" and path != current:
            return path
    return None


def _retire(repo, settings, record, entry, next_branch):
    """Record the unit merged, then delete its remote and local branch and its recorded tags.

    Checkout-safe: a branch checked out here moves to the next unmerged unit's branch (or the
    remote trunk when none); a branch checked out in another worktree is kept and named."""
    entry["state"] = "merged"
    write_record(repo, record)
    branch = entry["branch"]
    remote = primary_remote(repo, settings)
    if flow_git.rev(repo, f"refs/remotes/{remote}/{branch}") is not None:
        flow_git.delete_remote(repo, settings, record, branch)
    remote_ref = f"refs/remotes/{remote}/{entry['target']}"
    lines = []
    if flow_git.rev(repo, f"refs/heads/{branch}") is not None:
        elsewhere = _worktree_of(repo, branch)
        if elsewhere is not None:
            lines.append(f"kept local {branch}: checked out in {elsewhere}")
        else:
            if _head_branch(repo) == branch:
                if next_branch is not None:
                    run_git(repo, "switch", next_branch)
                else:
                    run_git(repo, "switch", "--detach", remote_ref)
            if flow_git.is_ancestor(repo, f"refs/heads/{branch}", remote_ref):
                run_git(repo, "branch", "-D", branch)
    for tag in entry.get("tags", []):
        if flow_git.rev(repo, f"refs/tags/{tag}") is not None:
            run_git(repo, "tag", "-d", tag)
    return lines


def _resume_cleanup(repo, settings, record):
    """Retire units recorded merged whose branch or tags survive a failed earlier cleanup."""
    remote = primary_remote(repo, settings)
    unmerged = _unmerged(record)
    next_branch = unmerged[0]["branch"] if unmerged else None
    lines = []
    for entry in record["units"]:
        if entry["kind"] != "stacked" or entry["state"] != "merged":
            continue
        refs = [f"refs/heads/{entry['branch']}", f"refs/remotes/{remote}/{entry['branch']}",
                *(f"refs/tags/{tag}" for tag in entry.get("tags", []))]
        if any(flow_git.rev(repo, ref) is not None for ref in refs):
            lines.extend(_retire(repo, settings, record, entry, next_branch))
            lines.append(f"cleaned up: {entry['id']}")
    return lines


def _fast_forward(repo, settings, targets):
    """Move each local trunk that is behind the remote trunk, never backwards."""
    remote = primary_remote(repo, settings)
    for target in sorted(targets):
        local = flow_git.rev(repo, f"refs/heads/{target}")
        remote_tip = flow_git.rev(repo, f"refs/remotes/{remote}/{target}")
        if local is None or remote_tip is None or local == remote_tip:
            continue
        if not flow_git.is_ancestor(repo, local, remote_tip):
            continue
        if _head_branch(repo) == target:
            run_git(repo, "merge", "--ff-only", "-q", remote_tip)
        else:
            run_git(repo, "update-ref", f"refs/heads/{target}", remote_tip, local)


def _retarget(repo, settings, entry, trunk):
    """Point the next PR at the trunk before its parent's branch is deleted (R4 adjacency)."""
    code, out, err = flow_pr.pr_cmd_split(repo, settings, "edit", str(entry["pr"]), "--base", trunk)
    if code != 0:
        raise FlowError("pr_failed", flow_pr.failure_line(out, err, "gh pr edit"))


def _api_json(repo, *args):
    code, out, err = flow_pr.run_gh_split(repo, "api", *args)
    if code != 0:
        raise FlowError("pr_failed", flow_pr.failure_line(out, err, "gh api merge-async"))
    try:
        return json.loads(out)
    except ValueError:
        raise FlowError("pr_failed", "gh api merge-async: no JSON answer") from None


def _merge_async(repo, settings, top):
    """PUT .../pulls/<n>/merge-async, the documented merge for a stacked PR: it merges <n> and
    its open downstack PRs; `sha` pins <n>'s head (T-29.1-10). Polls the uuid result until it
    leaves `pending` or MERGE_WAIT passes. Returns the last result's status."""
    slug = flow_git.github_repo(repo, primary_remote(repo, settings))
    path = f"repos/{slug}/pulls/{top['pr']}/merge-async"
    result = _api_json(repo, "--method", "PUT", path, "--raw-field", "merge_method=merge",
                       "--raw-field", f"sha={top['pushed']}")
    uuid = (result.get("details") or {}).get("uuid")
    deadline = _now() + MERGE_WAIT
    while result.get("status") == "pending" and uuid:
        result = _api_json(repo, f"{path}/{uuid}")
        if result.get("status") != "pending" or _now() >= deadline:
            break
        _sleep(POLL_EVERY)
    if result.get("status") == "failed":
        message = (result.get("details") or {}).get("message") or "merge failed"
        raise FlowError("pr_failed", f"merge-async: {flow_pr.redact(str(message))}")
    return result.get("status")


def _stack_chain(repo, settings, record, unmerged, until):
    """Linked GitHub stack: one merge-async on the last ready PR merges the ready prefix."""
    ready, lines = [], []
    for entry in unmerged:
        if not entry.get("linked"):
            lines.append(f"stopped at {entry['id']}: not linked into the GitHub stack")
            break
        view = _view(repo, settings, entry["pr"])
        reason = _stop_reason(view)
        if not reason and view.get("headRefOid") != entry["pushed"]:
            reason = "PR head differs from the recorded pushed sha"  # downstack heads: no pin
        if reason:
            lines.append(f"stopped at {entry['id']}: {reason}")
            break
        ready.append(entry)
        if until == entry["id"]:
            break
    if not ready:
        return lines
    status = _merge_async(repo, settings, ready[-1])
    if status != "merged":
        lines.append(f"merge-async for #{ready[-1]['pr']}: {status}")
    _fetch(repo, settings)
    ready = _confirmed_prefix(repo, settings, ready, lines)
    for entry in ready:
        entry["state"] = "merged"
    write_record(repo, record)
    rest = [e for e in unmerged if e["state"] != "merged"]
    next_branch = rest[0]["branch"] if rest else None
    if ready and rest and not rest[0].get("linked"):
        _retarget(repo, settings, rest[0], ready[-1]["target"])  # its base branch goes next
    targets = set()
    for entry in ready:
        lines.append(f"merged: {entry['id']} (#{entry['pr']})")
        lines.extend(_retire(repo, settings, record, entry, next_branch))
        targets.add(entry["target"])
    _fast_forward(repo, settings, targets)
    return lines


def _unmerged(record):
    return [e for e in record["units"] if e["kind"] == "stacked" and e["state"] != "merged"]


def _need_pr(entry):
    if entry["pr"] is None:
        raise FlowError("no_pr", f"{entry['id']} has no PR number; open one before merge-chain")


def _chain(repo, settings, record, until):
    unmerged = _unmerged(record)
    branches = {e["branch"] for e in unmerged}
    for entry in unmerged:
        _need_pr(entry)
    for entry in unmerged:
        view = _view(repo, settings, entry["pr"])
        expected = entry["parent"] if entry["parent"] in branches else entry["target"]
        if view["baseRefName"] != expected:
            raise FlowError("base_mismatch",
                            f"{entry['id']} PR base is {view['baseRefName']}, expected {expected}")
    if any(entry.get("linked") for entry in unmerged):
        return _stack_chain(repo, settings, record, unmerged, until)
    lines, targets = [], set()
    for index, entry in enumerate(unmerged):
        view = _view(repo, settings, entry["pr"])
        reason = _stop_reason(view)
        if reason:
            lines.append(f"stopped at {entry['id']}: {reason}")
            break
        _merge(repo, settings, entry, view)
        _fetch(repo, settings)
        if not _confirmed(repo, settings, entry):
            lines.append(f"stopped at {entry['id']}: merge not confirmed")
            break
        entry["state"] = "merged"
        write_record(repo, record)
        lines.append(f"merged: {entry['id']} (#{entry['pr']})")
        targets.add(entry["target"])
        next_branch = None
        if index + 1 < len(unmerged):
            next_branch = unmerged[index + 1]["branch"]
            _retarget(repo, settings, unmerged[index + 1], entry["target"])
        lines.extend(_retire(repo, settings, record, entry, next_branch))
        if until == entry["id"]:
            break
    if targets:
        _fast_forward(repo, settings, targets)
    return lines


def _hotfix(repo, settings, record, unit_id):
    entry = find_entry(record, unit_id)
    if entry is None:
        raise FlowError("not_started", f"unit {unit_id} is not recorded")
    if entry["kind"] != "hotfix":
        raise FlowError("not_hotfix", f"{unit_id} is a stacked unit, not a hotfix")
    _need_pr(entry)
    view = _view(repo, settings, entry["pr"])
    if view["baseRefName"] != entry["target"]:
        raise FlowError("base_mismatch", f"hotfix PR base is {view['baseRefName']}")
    reason = _stop_reason(view)
    if reason:
        return [f"stopped at {unit_id}: {reason}"]
    _merge(repo, settings, entry, view)
    _fetch(repo, settings)
    if not _confirmed(repo, settings, entry):
        return [f"stopped at {unit_id}: merge not confirmed"]
    lines = _retire(repo, settings, record, entry, None)
    _fast_forward(repo, settings, {entry["target"]})
    return [f"merged: {unit_id} (#{entry['pr']})", *lines]


def cmd_merge_chain(args):
    repo = args.repo
    try:
        settings, record = read_settings(repo), read_record(repo)
        if flow_stack.restack_pending(repo):
            raise FlowError("restack_pending", "fold.py restack --continue or --abort first")
        if not consented(repo):
            raise FlowError("no_consent", "merge-chain pushes and merges; grant consent first")
        if args.until is not None and args.until not in {e["id"] for e in _unmerged(record)}:
            raise FlowError("bad_value", f"--until {args.until} is not an unmerged stacked unit")
        with chain_lock(repo):
            _fetch(repo, settings)
            if args.hotfix_id:
                lines = _hotfix(repo, settings, record, args.hotfix_id)
            else:
                lines = _resume_cleanup(repo, settings, record)
                lines.extend(_chain(repo, settings, record, args.until))
    except FlowError as exc:
        print(render("merge-chain", "-", "-", [f"refused: {exc.reason}: {exc.detail}"],
                     f"refused {exc.reason}"))
        return 1
    print(render("merge-chain", "-", "-", lines, "done"))
    return 0
