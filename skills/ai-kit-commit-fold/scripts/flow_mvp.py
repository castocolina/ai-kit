"""MVP fast path for the unit flow (plan 29.1-02): fast-forward the target, then push it.

A unit with `mvp` true and no unmerged stacked unit recorded below it moves its local target to
the folded unit tip with `update-ref` (old tip expected, never a merge commit) and pushes the
target with a plain push. Git itself rejects that push unless it is a fast-forward; the target is
never leased or forced. Every other case is refused by its reason code.
"""

import flow_git
from flow_record import FlowError


def _unmerged_below(record, unit_id):
    """Ids of the stacked units recorded above the target and before this unit, unmerged."""
    below = []
    for entry in record["units"]:
        if entry["id"] == unit_id:
            break
        if entry["kind"] == "stacked" and entry["state"] != "merged":
            below.append(entry["id"])
    return below


def _checked_out_where(repo, target):
    """The worktree path that has refs/heads/<target> checked out, or None."""
    path = None
    for line in flow_git.run_git(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line == f"branch refs/heads/{target}":
            return path
    return None


def fast_forward(repo, settings, record, entry, unit):
    """Move the local target to the folded unit tip and push it; (outcome, report lines).

    Refusals are FlowError: mvp_below_unmerged (an unmerged unit sits below), mvp_diverged (the
    local or the remote target holds commits the unit does not), mvp_target_checked_out.
    """
    target = unit.target
    below = _unmerged_below(record, entry["id"])
    if below:
        raise FlowError("mvp_below_unmerged", f"unmerged units below: {', '.join(below)}")
    new_tip = flow_git.rev(repo, f"refs/heads/{unit.branch}")
    if new_tip is None:
        raise FlowError("git_error", f"branch {unit.branch} does not resolve")
    remote = flow_git.primary_remote(repo, settings)
    local_target = flow_git.rev(repo, f"refs/heads/{target}")
    remote_target = flow_git.rev(repo, f"refs/remotes/{remote}/{target}")
    if local_target is None:
        raise FlowError("mvp_diverged", f"local {target} does not exist")
    if not flow_git.is_ancestor(repo, local_target, new_tip):
        raise FlowError("mvp_diverged", f"local {target} holds commits the unit does not")
    if remote_target is not None and not flow_git.is_ancestor(repo, remote_target, new_tip):
        raise FlowError("mvp_diverged", f"remote {target} holds commits the unit does not")
    where = _checked_out_where(repo, target)
    if where is not None:
        raise FlowError("mvp_target_checked_out", f"{target} is checked out in {where}")
    if local_target == new_tip and remote_target == new_tip:
        return "nothing to do", ["nothing to push"]
    flow_git.run_git(repo, "update-ref", f"refs/heads/{target}", new_tip, local_target)
    try:
        flow_git.push(repo, settings, record, [(target, None, None)])
    except FlowError as exc:
        raise FlowError("push_failed", f"target push failed; local {target} is ahead") from exc
    return "done", [f"fast-forwarded {target} to {new_tip[:12]}", f"pushed {target}"]
