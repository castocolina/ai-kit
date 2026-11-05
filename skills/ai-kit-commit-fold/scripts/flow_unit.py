"""Unit commands for the unit flow (plan 29.1-01): start, guard, checkpoint, ready, show.

Each command takes the argparse namespace from fold.py. `args.unit` is a flow_record.Unit
(or None), `args.fold_step(merged_refs)` returns a fold Result, `args.signals` is
(finished, verified) for --phase and (None, None) otherwise. Every report uses
flow_record.render: first line `flow <command> <unit>: <branch>`, last `outcome: ...`.
"""

import flow_git
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
        if entry["pr"] is None:
            entry["pr"] = flow_pr.open_draft(repo, settings, _unit_of(entry), entry, record)
        write_record(repo, record)
        lines.append(f"caught up unit {entry['id']}: pushed {pending[:12]}")
    return lines


def _sync(repo, settings, record):
    reason = flow_stack.sync(repo, settings, record)
    if reason:
        raise FlowError(reason, "fold.py restack")


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
    head = flow_git.run_git(repo, "symbolic-ref", "--short", "-q", "HEAD").strip()
    joined = next((item for item in record["units"]
                   if item["kind"] == "hotfix" and item["branch"] == head), None)
    if joined is not None and find_entry(record, unit.id) is None:
        return [*lines, f"joins hotfix unit {joined['id']}"], "done"
    existing = find_entry(record, unit.id)
    if existing is not None:
        _check_parent(repo, existing)
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
    _switch(repo, unit.branch, parent_tip)
    record["units"].append({
        "id": unit.id, "kind": unit.kind, "target": unit.target, "branch": unit.branch,
        "parent": parent, "parent_tip": parent_tip, "pr": None, "state": "open",
        "mvp": unit.mvp, "pushed": None, "pending": None, "tags": [], "title": unit.title,
        "goal": unit.goal, "checkpoints": 0,
    })
    write_record(repo, record)
    return [*lines, f"started unit {unit.id} on {parent}"], "done"


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
    if entry["pushed"] == new_tip:
        return "done", []
    if not consented(repo):
        entry["pending"] = new_tip
        return "skipped (no consent)", [f"skipped: {unit.id} push {unit.branch}"]
    flow_git.push(repo, settings, record, [(unit.branch, entry["pushed"], None)])
    entry["pushed"] = new_tip
    entry["pending"] = None
    notes = [f"pushed {unit.branch} at {new_tip[:12]}"]
    if entry["pr"] is None:
        entry["pr"] = flow_pr.open_draft(repo, settings, unit, entry, record)
        if entry["pr"] is not None:
            notes.append(f"draft PR {entry['pr']}")
    return "done", notes


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
    signals = getattr(args, "signals", (None, None))
    if signals[1] is False:
        raise FlowError("not_verified", "phase verification has not passed")
    if not consented(repo):
        return [*lines, f"skipped: {unit.id} ready"], "skipped (no consent)"
    if entry["pr"] is not None:
        flow_pr.mark_ready(repo, settings, entry)
        lines.append(f"PR {entry['pr']} marked ready")
    entry["state"] = "ready"
    write_record(repo, record)
    return lines, "done"


def cmd_start(args):
    return _run("start", args, _start)


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
