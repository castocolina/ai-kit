"""Unit commands for the unit flow (plan 29.1-01): start, guard, checkpoint, ready, show.

Each command takes the argparse namespace from fold.py. `args.unit` is a flow_record.Unit
(or None), `args.fold_step(merged_refs)` returns a fold Result, `args.signals` is
(finished, verified) for --phase and (None, None) otherwise. Every report uses
flow_record.render: first line `flow <command> <unit>: <branch>`, last `outcome: ...`.
"""

import flow_boundary
import flow_git
import flow_mvp
import flow_pr
import flow_stack
from flow_record import (
    FlowError,
    Unit,
    consented,
    find_entry,
    read_record,
    read_settings,
    render,
    write_record,
)

_EXIT_BAD_INPUT = frozenset({"bad_value", "missing_field", "unknown_field"})


def _unit_of(entry):
    return Unit(id=entry["id"], kind=entry["kind"], target=entry["target"],
                branch=entry["branch"], title=entry["title"], goal=entry.get("goal", ""),
                mvp=entry.get("mvp", False))


def merged_refs(repo, settings, record):
    """refs/heads/<branch> of every unit recorded merged or merged on the remote."""
    refs = []
    for entry in record["units"]:
        if entry["state"] == "merged" or flow_git.merged_on_remote(repo, settings, entry):
            refs.append(f"refs/heads/{entry['branch']}")
    return refs


def catch_up(repo, settings, record):
    """Push every recorded pending (folded, skipped) tip, bottom-up, with its own lease."""
    lines = []
    for entry in record["units"]:
        pending = entry.get("pending")
        if pending is None:
            continue
        flow_git.push(repo, settings, record, [(entry["branch"], entry["pushed"], pending)])
        entry["pushed"] = pending
        entry["pending"] = None
        write_record(repo, record)  # the remote moved; record it before any forge call
        lines.append(f"caught up unit {entry['id']}: pushed {pending[:12]}")
        if entry["pr"] is None and not entry.get("mvp"):  # an MVP unit opens no PR
            lines.extend(_pr_step(repo, settings, record, _unit_of(entry), entry))
            write_record(repo, record)
    return lines


def _pr_step(repo, settings, record, unit, entry):
    """Open or update the PR after a recorded push. A forge failure becomes a report note:
    the push stays recorded, so the next lease is right."""
    try:
        if entry["pr"] is None:
            entry["pr"], notes = flow_pr.ensure_pr(repo, settings, record, unit, entry)
            return notes
        flow_pr.update_pr(repo, settings, unit, entry)
        return [f"PR {entry['pr']} text updated"]
    except FlowError as exc:
        return [f"PR step failed: {exc.reason}: {exc.detail}"]


def _sync(repo, settings, record):
    flow_stack.sync(repo, settings, record)


def _require_entry(record, unit):
    entry = find_entry(record, unit.id)
    if entry is None:
        raise FlowError("not_started", f"unit {unit.id} is not recorded; run start first")
    return entry


def _check_parent(repo, entry):
    """wrong_parent unless the unit's recorded parent tip is an ancestor of its branch."""
    branch = entry["branch"]
    tip = flow_git.rev(repo, f"refs/heads/{branch}")
    if tip is None:
        return
    if not flow_git.is_ancestor(repo, entry["parent_tip"], f"refs/heads/{branch}"):
        fork = flow_git.merge_base(repo, f"refs/heads/{branch}", entry["parent_tip"])
        raise FlowError(
            "wrong_parent",
            f"expected parent {entry['parent']} at {entry['parent_tip'][:12]}; "
            f"branch {branch} forks from {fork[:12] or 'nothing'}")


def _switch(repo, branch, parent_tip):
    if flow_git.rev(repo, f"refs/heads/{branch}") is None:
        flow_git.run_git(repo, "branch", branch, parent_tip)
    flow_git.run_git(repo, "switch", branch)


def _restore_branch(repo, entry):
    """Recreate a deleted local unit branch at its pending or pushed tip, never at parent_tip
    (a branch without the unit's commits would rewind the remote on the next push)."""
    if flow_git.rev(repo, f"refs/heads/{entry['branch']}") is not None:
        return
    tip = entry.get("pending") or entry.get("pushed")
    if tip is None:
        raise FlowError("branch_missing",
                        f"branch {entry['branch']} is gone and the record holds no tip for it")
    flow_git.run_git(repo, "branch", entry["branch"], tip)


def _local_only(repo, record, parent_tip, paths=()):
    """Commits on HEAD above parent_tip that no remote branch and no recorded unit holds."""
    units = [ref for ref in (f"refs/heads/{item['branch']}" for item in record["units"])
             if flow_git.rev(repo, ref) is not None]
    argv = ["rev-list", "--reverse", "HEAD", "--not", parent_tip, "--remotes", *units]
    return flow_git.run_git(repo, *argv, *(["--", *paths] if paths else [])).split()


def _carry(repo, record, unit, start, paths):
    """Switch to the unit branch (created when new), keeping the local-only commits that touch
    the plan paths (start --plan: the plan file and the spec its **Spec:** line names; --phase:
    the phase directory). Returns (report lines, carried commit count).

    Every commit between parent_tip and HEAD is a local-only plan commit: the branch starts at
    HEAD. Otherwise only the plan commits are cherry-picked onto parent_tip from a clean tree
    (unrelated local commits stay off the unit); a failed pick is aborted, HEAD restored, the new
    branch deleted and the start refused.
    """
    parent, parent_tip = start
    if flow_git.rev(repo, f"refs/heads/{unit.branch}") is not None:
        paths = ()  # an existing branch is reused as it is
    tracked = [path for path in paths if flow_git.rev(repo, f"HEAD:./{path}") is not None]
    local = _local_only(repo, record, parent_tip, tracked) if tracked else []
    if not local:
        _switch(repo, unit.branch, parent_tip)
        return [], 0
    between = flow_git.run_git(repo, "rev-list", f"{parent_tip}..HEAD").split()
    head = flow_git.head_branch(repo) or flow_git.rev(repo, "HEAD")
    if flow_git.is_ancestor(repo, parent_tip, "HEAD") and len(between) == len(local):
        _switch(repo, unit.branch, flow_git.rev(repo, "HEAD"))
        return [f"carried {len(local)} local commit(s) from {head}: the plan stays"], len(local)
    if flow_git.run_git(repo, "status", "--porcelain", "--untracked-files=no").strip():
        raise FlowError("dirty_tree", "commit or discard the working tree changes, then re-run "
                                      "start (the plan's local commits must be carried)")
    back = ["switch", head] if flow_git.head_branch(repo) else ["switch", "--detach", head]
    _switch(repo, unit.branch, parent_tip)
    try:
        flow_git.run_git(repo, "cherry-pick", *local)
    except FlowError as exc:
        if flow_git.rev(repo, "CHERRY_PICK_HEAD") is not None:
            flow_git.run_git(repo, "cherry-pick", "--abort")
        flow_git.run_git(repo, *back)
        flow_git.run_git(repo, "branch", "-D", unit.branch)
        raise FlowError(
            "plan_not_carried",
            f"cannot cherry-pick the {len(local)} local commit(s) holding the plan onto {parent} "
            f"({exc.detail}); nothing changed. Show the owner these commands: "
            f"git switch -c {unit.branch} {parent_tip[:12]}, "
            f"git cherry-pick {' '.join(sha[:12] for sha in local)}, resolve, then re-run start"
        ) from exc
    return [f"carried {len(local)} local commit(s) from {head} by cherry-pick"], len(local)


def _run(command, args, body):
    """Run one command body; refusals become a rendered report with exit 1 (2 for bad input)."""
    unit = args.unit
    unit_id = unit.id if unit else "-"
    branch = unit.branch if unit else "-"
    try:
        lines, outcome = body(args, unit)
    except FlowError as exc:
        text = render(command, unit_id, branch, [f"refused: {exc.reason}: {exc.detail}"],
                      f"refused {exc.reason}")
        print(text)
        return 2 if exc.reason in _EXIT_BAD_INPUT else 1
    print(render(command, unit_id, branch, lines, outcome))
    return 0


def _start(args, unit):
    repo = args.repo
    if unit is None:
        raise FlowError("bad_value", "start needs a unit selector")
    settings, record = read_settings(repo), read_record(repo)
    _sync(repo, settings, record)
    lines = catch_up(repo, settings, record) if consented(repo) else []
    head = flow_git.head_branch(repo)
    joined = next((item for item in record["units"]
                   if item["kind"] == "hotfix" and item["branch"] == head), None)
    if joined is not None and find_entry(record, unit.id) is None:
        return [*lines, f"joins hotfix unit {joined['id']}"], "done"
    existing = find_entry(record, unit.id)
    if existing is not None:
        _check_parent(repo, existing)
        _restore_branch(repo, existing)
        _switch(repo, existing["branch"], existing["parent_tip"])
        return [*lines, f"reuses unit {unit.id}"], "nothing to do"
    parent, parent_tip = flow_git.start_point(repo, settings, record, unit.target)
    if parent_tip is None:
        raise FlowError("no_trunk", f"{parent} does not resolve to a commit")
    branch_ref = f"refs/heads/{unit.branch}"
    if flow_git.rev(repo, branch_ref) is not None and not flow_git.is_ancestor(
            repo, parent_tip, branch_ref):
        fork = flow_git.merge_base(repo, branch_ref, parent_tip)
        raise FlowError(
            "wrong_parent",
            f"branch {unit.branch} exists and is not on {parent} "
            f"(expected {parent_tip[:12]}, forks from {fork[:12] or 'nothing'})")
    carried_lines, carried = _carry(repo, record, unit, (parent, parent_tip),
                                    getattr(args, "plan_paths", ()))
    record["units"].append({
        "id": unit.id, "kind": unit.kind, "target": unit.target, "branch": unit.branch,
        "parent": parent, "parent_tip": parent_tip, "pr": None, "state": "open",
        "mvp": unit.mvp, "pushed": None, "pending": None, "tags": [], "title": unit.title,
        "goal": unit.goal, "checkpoints": 0, "carried": carried,
    })
    write_record(repo, record)
    return [*lines, f"started unit {unit.id} on {parent}", *carried_lines], "done"


def _guard(args, unit):
    repo = args.repo
    record = read_record(repo)
    _check_parent(repo, _require_entry(record, unit))
    return [], "nothing to do"


def _checkpoint(args, unit):
    repo = args.repo
    settings, record = read_settings(repo), read_record(repo)
    entry = _require_entry(record, unit)
    _sync(repo, settings, record)
    lines = catch_up(repo, settings, record) if consented(repo) else []
    _check_parent(repo, entry)
    if flow_git.head_branch(repo) != unit.branch:
        raise FlowError("ref_mismatch", f"HEAD is on {flow_git.head_branch(repo) or 'no branch'}"
                                        f", not the unit branch {unit.branch}; switch to it")
    old_tip = flow_git.rev(repo, f"refs/heads/{unit.branch}")
    result = args.fold_step(merged_refs(repo, settings, record))
    if result.outcome == "refused":
        raise FlowError(result.reason, result.note)
    if result.tag:
        entry["tags"].append(result.tag)
    if result.outcome == "nothing_to_fold":
        lines.append("nothing to fold")
    else:
        lines.append(f"folded {result.before} -> {result.after} commits ({result.grouping})")
    new_tip = flow_git.rev(repo, f"refs/heads/{unit.branch}")
    if new_tip is None:
        raise FlowError("git_error", f"branch {unit.branch} does not resolve after the fold")
    _cascade_if_moved(repo, settings, record, unit, old_tip)
    signals = getattr(args, "signals", (None, None))
    if args.final or signals[0] is True:
        entry["state"] = "finished"
    entry["checkpoints"] += 1
    # MVP units too: a draft-PR fallback (mvp_below_unmerged) must still push the rewrite
    if old_tip is not None and old_tip != new_tip and not (
            flow_git.is_ancestor(repo, old_tip, new_tip)):
        # the fold rewrote the branch: record the new tip as pending so a failed push can retry
        entry["pending"] = new_tip
        write_record(repo, record)
    outcome, notes = _publish(repo, settings, record, entry, unit)
    lines.extend(notes)
    write_record(repo, record)
    return lines, outcome


def _cascade_if_moved(repo, settings, record, unit, old_tip):
    """A fold that rewrote this unit restacks the unmerged units above it (plan 03 fills it)."""
    new_tip = flow_git.rev(repo, f"refs/heads/{unit.branch}")
    if old_tip is None or new_tip is None or flow_git.is_ancestor(repo, old_tip, new_tip):
        return
    index = next(i for i, item in enumerate(record["units"]) if item["id"] == unit.id)
    above = [item for item in record["units"][index + 1:]
             if item["kind"] == "stacked" and item["state"] != "merged"]
    if above:
        write_record(repo, record)
        flow_stack.cascade(repo, settings, record, moved_unit=unit.id, old_tip=old_tip)


def _publish(repo, settings, record, entry, unit):
    """Push the folded tip with consent (and open the draft PR on the first push), else record
    it as pending and list the skipped push. Returns (outcome word, report lines)."""
    new_tip = flow_git.rev(repo, f"refs/heads/{unit.branch}")
    if new_tip is None:
        raise FlowError("git_error", f"branch {unit.branch} does not resolve")
    if not consented(repo):
        if entry["pushed"] == new_tip:
            return "nothing to do", ["nothing to push"]
        entry["pending"] = new_tip
        return "skipped (no consent)", [f"skipped: {unit.id} push {unit.branch}"]
    notes = []
    if unit.mvp:
        try:
            outcome, mvp_notes = flow_mvp.fast_forward(repo, settings, record, entry, unit)
        except FlowError as exc:
            if exc.reason != "mvp_below_unmerged":
                raise
            notes.append(f"{exc.reason}: {exc.detail}; opening a draft PR instead")
        else:
            entry["pushed"], entry["pending"] = new_tip, None
            return outcome, mvp_notes
    if entry["pushed"] == new_tip:
        return "nothing to do", [*notes, "nothing to push"]
    if entry["pushed"] and entry["pending"] != new_tip and not (
            flow_git.is_ancestor(repo, entry["pushed"], new_tip)):
        raise FlowError(
            "not_descendant",
            f"{unit.branch} at {new_tip[:12]} does not contain the pushed tip "
            f"{entry['pushed'][:12]}; the push would rewind the remote branch")
    flow_git.push(repo, settings, record, [(unit.branch, entry["pushed"], None)])
    entry["pushed"] = new_tip
    entry["pending"] = None
    write_record(repo, record)  # the remote moved; record it before any forge call
    notes.append(f"pushed {unit.branch} at {new_tip[:12]}")
    notes.extend(_pr_step(repo, settings, record, unit, entry))
    return "done", notes


def _not_ready_below(record, unit_id):
    """Ids of the unmerged stacked units recorded below this unit that are not ready yet."""
    below = []
    for entry in record["units"]:
        if entry["id"] == unit_id:
            break
        if entry["kind"] == "stacked" and entry["state"] not in ("ready", "merged"):
            below.append(entry["id"])
    return below


def _ready(args, unit):
    repo = args.repo
    settings, record = read_settings(repo), read_record(repo)
    entry = _require_entry(record, unit)
    _sync(repo, settings, record)
    lines = catch_up(repo, settings, record) if consented(repo) else []
    if entry["state"] == "ready":
        return lines, "nothing to do"
    if entry["state"] != "finished":
        raise FlowError("signal_order", "checkpoint --final must come before ready")
    below = _not_ready_below(record, entry["id"])
    if below:
        raise FlowError("signal_order", f"unit {below[-1]} below must be ready first")
    signals = getattr(args, "signals", (None, None))
    if signals[1] is False:
        raise FlowError("not_verified", "phase verification has not passed")
    if not consented(repo):
        return [*lines, f"skipped: {unit.id} ready"], "skipped (no consent)"
    if entry["pr"] is not None:
        flow_pr.mark_ready(repo, settings, entry)
        lines.append(f"PR {entry['pr']} marked ready")
    else:
        lines.append("no PR to mark ready")
    entry["state"] = "ready"
    write_record(repo, record)
    return lines, "done"


def _briefed_unit(repo, unit, lines):
    """The unit the boundary briefs: a joined hotfix unit when `start` joined one (30-04)."""
    joined = next((line for line in lines if line.startswith("joins hotfix unit ")), None)
    if joined is None:
        return unit
    return _unit_of(find_entry(read_record(repo), joined.rsplit(" ", 1)[1]))


def _start_and_boundary(args, unit):
    """`start`, then the boundary step at the unit's start; a boundary failure is one line."""
    lines, outcome = _start(args, unit)
    try:
        boundary_lines, _ = flow_boundary.boundary(
            args.repo, _briefed_unit(args.repo, unit, lines), "start",
            phase=getattr(args, "phase", None))
        lines.append("boundary: " + " | ".join(boundary_lines))
    except FlowError as exc:
        lines.append(f"boundary: skipped: {exc.reason}: {exc.detail}")
    except OSError as exc:
        lines.append(f"boundary: skipped: os_error: {exc}")
    except ValueError as exc:  # e.g. undecodable text; start's own change already went through
        lines.append(f"boundary: skipped: value_error: {exc}")
    return lines, outcome


def cmd_start(args):
    return _run("start", args, _start_and_boundary)


def cmd_guard(args):
    return _run("guard", args, _guard)


def cmd_checkpoint(args):
    return _run("checkpoint", args, _checkpoint)


def cmd_ready(args):
    return _run("ready", args, _ready)


def cmd_show(args):
    """Read-only: no sync and no remote call. Prints the state and PR lines."""
    record = read_record(args.repo)
    entry = find_entry(record, args.unit.id)
    if entry is None:
        print(render("show", args.unit.id, args.unit.branch, [], "refused not_started"))
        return 1
    print(f"state: {entry['state']}")
    print(f"pr: {entry['pr'] if entry['pr'] is not None else 'none'}")
    return 0
