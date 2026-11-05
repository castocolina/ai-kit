"""Owner-started merge chain for the unit flow (plan 29.1-03 Task 3).

`fold.py merge-chain` runs only when the owner starts it. Every unmerged stacked unit's PR is
checked for base and state before any merge; then the walk goes bottom-up, one `pr merge --merge
--match-head-commit <tip>` per ready PR. After each merge the unit is recorded merged, the next
PR is retargeted to the trunk, and the merged unit's branches and recorded backup tags are
deleted. A draft, a pending or failing check, or a conflict stops the walk by name.
`--unit-id` merges one recorded hotfix PR into its target and touches no stacked unit.
Not built here: trunk fast-forward, the gh-stack single-call merge, checkout-safe branch
cleanup for a unit checked out in another worktree.
"""

import contextlib
import json
import os
import subprocess

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
_FIELDS = "number,state,isDraft,baseRefName,headRefName,mergeable,statusCheckRollup"


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextlib.contextmanager
def chain_lock(repo, pid_alive=_pid_alive):
    """Hold <git common dir>/ai-kit-flow.lock for one run; a dead holder's lock is taken over."""
    path = common_dir(repo) / LOCK_NAME
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            held = int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            held = 0
        if held and pid_alive(held):
            raise FlowError("chain_locked", f"another merge chain run holds {LOCK_NAME}") from None
        path.unlink(missing_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def _view(repo, settings, number):
    code, text = flow_pr.pr_cmd(repo, settings, "view", str(number), "--json", _FIELDS)
    if code != 0:
        raise FlowError("pr_failed", text.strip().splitlines()[0] if text.strip() else "gh pr")
    return json.loads(text)


def _check_state(view):
    """'' when every check passed, else the stop reason."""
    for check in view.get("statusCheckRollup") or []:
        conclusion = check.get("conclusion") or ""
        if conclusion in ("", "PENDING", "IN_PROGRESS", "QUEUED", "EXPECTED"):
            return "check pending"
        if conclusion != "SUCCESS":
            return "check failing"
    return ""


def _stop_reason(view):
    if view["isDraft"]:
        return "draft"
    checks = _check_state(view)
    if checks:
        return checks
    if view.get("mergeable") != "MERGEABLE":
        return "conflict"
    return ""


def _merge(repo, settings, entry, view):
    tip = flow_git.rev(repo, f"refs/heads/{entry['branch']}")
    code, text = flow_pr.pr_cmd(repo, settings, "merge", str(view["number"]), "--merge",
                                "--match-head-commit", tip)
    if code != 0:
        raise FlowError("pr_failed", text.strip().splitlines()[0] if text.strip() else "gh pr")


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
    flow_git.delete_remote(repo, settings, record, entry["branch"])
    branch = entry["branch"]
    remote_ref = f"refs/remotes/{primary_remote(repo, settings)}/{entry['target']}"
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
    code, text = flow_pr.pr_cmd(repo, settings, "edit", str(entry["pr"]), "--base", trunk)
    if code != 0:
        raise FlowError("pr_failed", text.strip().splitlines()[0] if text.strip()
                        else "gh pr edit")


def _stack_chain(repo, settings, record, unmerged, until):
    """gh-stack backend: one `gh stack merge <last ready PR> --merge` for the ready prefix."""
    ready, lines = [], []
    for entry in unmerged:
        view = _view(repo, settings, entry["pr"])
        reason = _stop_reason(view)
        if reason:
            lines.append(f"stopped at {entry['id']}: {reason}")
            break
        ready.append(entry)
        if until == entry["id"]:
            break
    if not ready:
        return lines
    code, text = flow_pr.run_gh(repo, "stack", "merge", str(ready[-1]["pr"]), "--merge")
    if code != 0:
        raise FlowError("pr_failed", text.strip().splitlines()[0] if text.strip() else "gh stack")
    for entry in ready:
        entry["state"] = "merged"
    write_record(repo, record)
    _fetch(repo, settings)
    rest = [e for e in unmerged if e["state"] != "merged"]
    next_branch = rest[0]["branch"] if rest else None
    targets = set()
    for entry in ready:
        lines.append(f"merged: {entry['id']} (#{entry['pr']})")
        lines.extend(_retire(repo, settings, record, entry, next_branch))
        targets.add(entry["target"])
    _fast_forward(repo, settings, targets)
    return lines


def _chain(repo, settings, record, until):
    unmerged = [e for e in record["units"] if e["kind"] == "stacked" and e["state"] != "merged"]
    branches = {e["branch"] for e in unmerged}
    for entry in unmerged:
        view = _view(repo, settings, entry["pr"])
        expected = entry["parent"] if entry["parent"] in branches else entry["target"]
        if view["baseRefName"] != expected:
            raise FlowError("base_mismatch",
                            f"{entry['id']} PR base is {view['baseRefName']}, expected {expected}")
    if settings["stack_backend"] == "gh-stack":
        return _stack_chain(repo, settings, record, unmerged, until)
    lines, targets = [], set()
    for index, entry in enumerate(unmerged):
        view = _view(repo, settings, entry["pr"])
        reason = _stop_reason(view)
        if reason:
            lines.append(f"stopped at {entry['id']}: {reason}")
            break
        _merge(repo, settings, entry, view)
        entry["state"] = "merged"
        write_record(repo, record)
        lines.append(f"merged: {entry['id']} (#{entry['pr']})")
        targets.add(entry["target"])
        _fetch(repo, settings)
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
    view = _view(repo, settings, entry["pr"])
    if view["baseRefName"] != entry["target"]:
        raise FlowError("base_mismatch", f"hotfix PR base is {view['baseRefName']}")
    reason = _stop_reason(view)
    if reason:
        return [f"stopped at {unit_id}: {reason}"]
    _merge(repo, settings, entry, view)
    _fetch(repo, settings)
    lines = _retire(repo, settings, record, entry, None)
    _fast_forward(repo, settings, {entry["target"]})
    return [f"merged: {unit_id} (#{entry['pr']})", *lines]


def cmd_merge_chain(args):
    repo = args.repo
    try:
        settings, record = read_settings(repo), read_record(repo)
        if flow_stack.restack_pending(repo):
            raise FlowError("restack_pending", "fold.py restack --continue or --abort first")
        with chain_lock(repo):
            _fetch(repo, settings)
            if args.hotfix_id:
                lines = _hotfix(repo, settings, record, args.hotfix_id)
            else:
                lines = _chain(repo, settings, record, args.until)
    except FlowError as exc:
        print(render("merge-chain", "-", "-", [f"refused: {exc.reason}: {exc.detail}"],
                     f"refused {exc.reason}"))
        return 1
    print(render("merge-chain", "-", "-", lines, "done"))
    return 0
