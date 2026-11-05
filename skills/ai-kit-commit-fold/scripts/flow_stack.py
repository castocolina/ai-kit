"""Stack reconciliation, cascade, conflict resolution and hotfix (plans 29.1-01 and 29.1-03).

`sync` runs first in every flow command except consent, settings and show. With consent it
fetches and records externally merged units as merged. When the remote trunk carries non-merge
commits that the bottom unmerged unit does not hold, it cascades the stack onto the trunk.

`cascade` restacks the unmerged units above a moved point with one `git rebase --update-refs
--onto <new> <old> <top>`. A rebase stop pauses it: the conflicting paths and the stage-0 index
are saved to the restack file, and nothing else is written. `restack --continue` checks the
agent's resolution (no conflict markers, only the conflicting paths changed), continues the
rebase, runs the adapter gates and then the project's own gates with the top unit checked out,
and only then pushes atomically, leased on the recorded `pushed` shas. Without project gates the
resolved stack stays local and unpushed (`no_gates`). Any refused step restores every branch.
The gh-stack backend and the merge chain are not built here (plan 29.1-03 Task 3).
"""

import json
import os
import re
import shlex
import subprocess

import flow_git
from flow_git import primary_remote, run_git
from flow_record import (
    FlowError,
    _atomic_write_json,
    common_dir,
    consented,
    find_entry,
    read_record,
    read_settings,
    render,
    write_record,
)

RESTACK_NAME = "ai-kit-restack.json"
_HOTFIX_NAME = re.compile(r"[A-Za-z0-9._-]{1,64}")
_MARKERS = ("<<<<<<<", ">>>>>>>")


class _GateFailure(FlowError):
    """A refusal after the rebase finished: `lines` carries the report's gates line."""

    def __init__(self, reason, detail, lines):
        super().__init__(reason, detail)
        self.lines = lines


def _restack_path(repo):
    return common_dir(repo) / RESTACK_NAME


def _load_state(repo):
    path = _restack_path(repo)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def restack_pending(repo):
    """True while a restack is paused or resolved and not yet published or aborted."""
    return _load_state(repo) is not None


def _save_state(repo, state):
    _atomic_write_json(_restack_path(repo), state)


def _clear_state(repo):
    _restack_path(repo).unlink(missing_ok=True)


def _toplevel(repo):
    return os.path.realpath(run_git(repo, "rev-parse", "--show-toplevel").strip())


def _dirty(repo):
    return bool(run_git(repo, "status", "--porcelain", "--untracked-files=no").strip())


def _rebase_in_progress(repo):
    for name in ("rebase-merge", "rebase-apply"):
        path = run_git(repo, "rev-parse", "--path-format=absolute", "--git-path", name)
        if os.path.isdir(path.strip()):
            return True
    return False


def _worktrees(repo):
    """(path, branch) for every worktree that has a branch checked out."""
    pairs, path = [], None
    for line in run_git(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.startswith("branch refs/heads/") and path is not None:
            pairs.append((path, line[len("branch refs/heads/"):]))
    return pairs


def restore(repo, state):
    """Put every saved branch back at its starting tip and HEAD on branch_before.

    Detaches first so no checked-out branch blocks update-ref, then switches back, so HEAD,
    index and tracked files all match the saved tip. Never uses reset, clean or checkout paths.
    """
    if _dirty(repo):
        raise FlowError("dirty_tree", "changes appeared during the restack; restore stopped")
    run_git(repo, "switch", "--detach")
    for branch, saved in state["tips"].items():
        current = flow_git.rev(repo, f"refs/heads/{branch}")
        if current is not None and current != saved:
            run_git(repo, "update-ref", f"refs/heads/{branch}", saved, current)
    run_git(repo, "switch", state["branch_before"])
    _clear_state(repo)


def _abort_and_restore(repo, state):
    if _rebase_in_progress(repo):
        run_git(repo, "rebase", "--abort")
    restore(repo, state)


def _unmerged_above(record, moved_unit):
    """The unmerged stacked units above the moved unit, or all of them when none moved."""
    units = record["units"]
    start = 0
    if moved_unit is not None:
        start = next(i for i, entry in enumerate(units) if entry["id"] == moved_unit) + 1
    return [entry for entry in units[start:]
            if entry["kind"] == "stacked" and entry["state"] != "merged"]


def _preflight(repo, record, branches, old, top):
    """Refuse before any write: a branch checked out elsewhere, or a local branch outside the
    record that would move with --update-refs."""
    current = _toplevel(repo)
    for path, branch in _worktrees(repo):
        if branch in branches and os.path.realpath(path) != current:
            raise FlowError("branch_in_worktree", f"{branch} is checked out in {path}")
    recorded = {entry["branch"] for entry in record["units"]}
    top_ref = f"refs/heads/{top}"
    for ref in run_git(repo, "for-each-ref", "--format=%(refname)", "refs/heads").split():
        name = ref.removeprefix("refs/heads/")
        tip = flow_git.rev(repo, ref)
        if name in recorded or tip in (None, old):
            continue
        if flow_git.is_ancestor(repo, old, tip) and flow_git.is_ancestor(repo, tip, top_ref):
            raise FlowError("unrecorded_branch",
                            f"local branch {name} is not a recorded unit and sits in the range")


def _boundary(repo, settings, above, moved_entry, old_tip):
    """(new tip, old boundary) of one cascade: the remote trunk for a trunk move (old = the
    bottom unit's recorded parent_tip), else the moved branch (old = the checkpoint's old_tip)."""
    if moved_entry is None:
        remote = primary_remote(repo, settings)
        new_ref = f"refs/remotes/{remote}/{above[0]['target']}"
        old = above[0]["parent_tip"]
    else:
        new_ref = f"refs/heads/{moved_entry['branch']}"
        old = old_tip
    new = flow_git.rev(repo, new_ref)
    if new is None:
        raise FlowError("no_trunk", f"{new_ref} does not resolve")
    return new, old


def _tips(repo, branches):
    return {name: flow_git.rev(repo, f"refs/heads/{name}") for name in sorted(branches)}


def _conflicting(repo):
    out = run_git(repo, "diff", "--name-only", "--diff-filter=U", "-z")
    return [path for path in out.split("\0") if path]


def _stage_zero(repo):
    """path -> "<mode> <blob>" for every stage-0 index entry (NUL-separated, exact names)."""
    snapshot = {}
    for entry in run_git(repo, "ls-files", "-s", "-z").split("\0"):
        if not entry:
            continue
        meta, path = entry.split("\t", 1)
        mode, blob, stage = meta.split()
        if stage == "0":
            snapshot[path] = f"{mode} {blob}"
    return snapshot


def _pause(repo, state):
    """Keep the rebase paused: save the conflicting paths and the index snapshot, then refuse."""
    conflicts = _conflicting(repo)
    state.update(paused=True, conflicts=conflicts, index=_stage_zero(repo))
    state.setdefault("notes", {})
    _save_state(repo, state)
    raise FlowError("conflict", "paths: " + ", ".join(conflicts)
                    + "; then fold.py restack --continue or fold.py restack --abort")


def _rebase_units(repo, state, top, new, old):
    """git rebase --update-refs over old..top; a conflict pauses, any other stop restores."""
    try:
        run_git(repo, "switch", top)
        run_git(repo, "rebase", "--update-refs", "--onto", new, old, top)
    except FlowError as exc:
        if _rebase_in_progress(repo):
            _pause(repo, state)
        _abort_and_restore(repo, state)
        raise FlowError("rebase_conflict", f"{exc.detail}; every branch restored") from exc


def _rebased(repo, above, new):
    """(entry, new tip, new parent tip) for each restacked unit, bottom-up."""
    out, parent = [], new
    for entry in above:
        tip = flow_git.rev(repo, f"refs/heads/{entry['branch']}")
        out.append((entry, tip, parent))
        parent = tip
    return out


def _push_refs(repo, rebased, moved_entry):
    """Leased refs for the one atomic push: each pushed unit, and the moved unit when pushed."""
    refs = []
    for entry, tip, _parent in rebased:
        if entry["pushed"] is not None and tip != entry["pushed"]:
            refs.append((entry["branch"], entry["pushed"], None))
    if moved_entry is not None and moved_entry["pushed"] is not None:
        moved_tip = flow_git.rev(repo, f"refs/heads/{moved_entry['branch']}")
        if moved_tip != moved_entry["pushed"]:
            refs.append((moved_entry["branch"], moved_entry["pushed"], None))
    return refs


def _record_rebase(repo, rebased, pushed_now, moved_entry):
    """Each restacked unit's parent_tip; pushed or pending tips. Pending is a sha to push later."""
    for entry, tip, parent in rebased:
        entry["parent_tip"] = parent
        if entry["branch"] in pushed_now:
            entry["pushed"], entry["pending"] = tip, None
        elif tip != entry["pushed"]:
            entry["pending"] = tip
    if moved_entry is not None and moved_entry["branch"] in pushed_now:
        moved_entry["pushed"] = flow_git.rev(repo, f"refs/heads/{moved_entry['branch']}")
        moved_entry["pending"] = None


def _push_or_restore(repo, settings, record, state, refs):
    if not refs:
        return
    try:
        flow_git.push(repo, settings, record, refs)
    except FlowError:
        _abort_and_restore(repo, state)
        raise


def _publish(repo, settings, record, state):
    """After the rebase finished: leased push (with consent), record update, switch back.

    Units come from the saved state, so a resumed restack publishes the same set as the first.
    """
    above = [find_entry(record, unit_id) for unit_id in state["units"]]
    moved_entry = find_entry(record, state["moved_unit"]) if state["moved_unit"] else None
    rebased = _rebased(repo, above, state["new"])
    refs = _push_refs(repo, rebased, moved_entry) if consented(repo) else []
    _push_or_restore(repo, settings, record, state, refs)
    _record_rebase(repo, rebased, {branch for branch, _expected, _src in refs}, moved_entry)
    write_record(repo, record)
    run_git(repo, "switch", state["branch_before"])
    _clear_state(repo)
    return [entry["id"] for entry, _tip, _parent in rebased]


def cascade(repo, settings, record, moved_unit=None, old_tip=None):
    """Restack the unmerged units above a moved point; returns the restacked unit ids.

    Trunk case (moved_unit None): onto the remote trunk. Lower-unit case: onto the moved unit's
    branch, with old_tip (the checkpoint's old boundary). A clean rebase pushes every restacked
    unit that was pushed, plus the moved unit when pushed, in one atomic push leased on the
    recorded `pushed` shas. A rebase stop pauses (see `_pause`). Without consent nothing is
    pushed and each unit's new tip is kept as pending.
    """
    if _dirty(repo):
        raise FlowError("dirty_tree", "commit or discard the working tree changes first")
    head = run_git(repo, "symbolic-ref", "--short", "-q", "HEAD").strip()
    if not head:
        raise FlowError("detached_head", "check out a unit branch before restacking")
    above = _unmerged_above(record, moved_unit)
    if not above:
        return []
    moved_entry = find_entry(record, moved_unit) if moved_unit is not None else None
    new, old = _boundary(repo, settings, above, moved_entry, old_tip)
    if new == old:
        return []
    branches = {entry["branch"] for entry in above} | {head}
    if moved_entry is not None:
        branches.add(moved_entry["branch"])
    top = above[-1]["branch"]
    _preflight(repo, record, branches, old, top)
    state = {"schema": 1, "branch_before": head, "tips": _tips(repo, branches), "old": old,
             "new": new, "moved_unit": moved_unit, "units": [e["id"] for e in above],
             "top": top, "paused": False, "resolved": False}
    _save_state(repo, state)
    _rebase_units(repo, state, top, new, old)
    return _publish(repo, settings, record, state)


def _trunk_has_new_commits(repo, remote, bottom):
    """True when the remote trunk has non-merge commits the bottom unmerged unit lacks."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--no-merges", "--count",
         f"refs/remotes/{remote}/{bottom['target']}", f"^refs/heads/{bottom['branch']}"],
        capture_output=True, check=False)
    if proc.returncode != 0:
        return False
    return proc.stdout.decode("utf-8").strip() not in ("", "0")


def _sync_restacked(repo, settings, record):
    """Fetch with consent, reconcile merges, cascade when the trunk moved; returns the ids."""
    if _load_state(repo) is not None:
        raise FlowError("restack_pending", "fold.py restack --continue or fold.py restack --abort")
    remote = primary_remote(repo, settings)
    if consented(repo):
        run_git(repo, "fetch", "--prune", "-q", remote)
    changed = False
    for entry in record["units"]:
        if entry["state"] != "merged" and flow_git.merged_on_remote(repo, settings, entry):
            entry["state"] = "merged"
            changed = True
    if changed:
        write_record(repo, record)
    bottom = next((entry for entry in record["units"]
                   if entry["kind"] == "stacked" and entry["state"] != "merged"), None)
    if bottom is None or not _trunk_has_new_commits(repo, remote, bottom):
        return []
    return cascade(repo, settings, record)


def sync(repo, settings, record):
    """Fetch with consent, reconcile merges and cascade a moved trunk (flow_unit reads no value)."""
    _sync_restacked(repo, settings, record)


def _parse_notes(items):
    notes = {}
    for item in items or []:
        path, _sep, how = item.partition("=")
        notes[path] = how
    return notes


def _check_resolution(repo, state, notes):
    """Refuse a resolution with a conflict marker, a change outside the conflicting files, or an
    unstaged change; then stage the conflicting paths by name."""
    top = _toplevel(repo)
    conflicts = state["conflicts"]
    for path in conflicts:
        with open(os.path.join(top, path), encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.rstrip("\r\n")
                if stripped.startswith(_MARKERS) or stripped == "=======":
                    raise FlowError("bad_resolution", f"{path} still has a conflict marker")
    if conflicts:
        run_git(repo, "add", "--", *conflicts)
    current = _stage_zero(repo)
    for path in sorted(set(current) | set(state["index"])):
        if path not in conflicts and current.get(path) != state["index"].get(path):
            raise FlowError("bad_resolution", f"{path} changed outside the conflicting files")
    for path in run_git(repo, "diff", "--name-only", "-z").split("\0"):
        if path and path not in conflicts:
            raise FlowError("bad_resolution", f"{path} has an unstaged change")
    state["notes"] = {**state.get("notes", {}), **notes}


def _check_resolved_tips(repo, state):
    for branch, saved in state["resolved_tips"].items():
        if flow_git.rev(repo, f"refs/heads/{branch}") != saved:
            raise FlowError("bad_resolution", f"{branch} moved after the resolution was saved")


def _continue_rebase(repo, state):
    """Continue the paused rebase; another stop pauses again, any other failure restores."""
    try:
        run_git(repo, "-c", "core.editor=true", "rebase", "--continue")
    except FlowError as exc:
        if _rebase_in_progress(repo):
            _pause(repo, state)
        _abort_and_restore(repo, state)
        raise FlowError("rebase_conflict", f"{exc.detail}; every branch restored") from exc


def _save_resolved(repo, state, record):
    """Keep the resolved stack local: resolved true, the unit tips, and the branch back."""
    tips = {}
    for unit_id in state["units"]:
        entry = find_entry(record, unit_id)
        if entry is None:
            raise FlowError("not_started", f"unit {unit_id} is not recorded")
        tips[entry["branch"]] = flow_git.rev(repo, f"refs/heads/{entry['branch']}")
    state.update(resolved=True, paused=False, resolved_tips=tips)
    _save_state(repo, state)
    run_git(repo, "switch", state["branch_before"])


def _run_gates(repo, state, gates):
    """Run every gate with the top unit checked out; the first failure restores every branch."""
    run_git(repo, "switch", state["top"])
    cwd = _toplevel(repo)
    items = []
    for index, (label, argv) in enumerate(gates):
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, check=False)
        if proc.returncode != 0:
            items.append(f"{label} fail")
            items.extend(f"{later} not run" for later, _argv in gates[index + 1:])
            _abort_and_restore(repo, state)
            raise _GateFailure("gate_failed", f"{label} exited {proc.returncode}",
                               ["gates: " + "; ".join(items)])
        items.append(f"{label} pass")
    return "gates: " + "; ".join(items)


def _continue(repo, settings, record, args):
    """restack --continue: check, continue the rebase, gate, then publish."""
    state = _load_state(repo)
    if state is None:
        raise FlowError("restack_not_paused", "no restack is paused")
    notes = _parse_notes(args.note)
    if not state.get("resolved"):
        try:
            _check_resolution(repo, state, notes)
        except FlowError as exc:
            if exc.reason == "bad_resolution":
                _abort_and_restore(repo, state)
            raise
        _continue_rebase(repo, state)
    else:
        try:
            _check_resolved_tips(repo, state)
        except FlowError:
            _abort_and_restore(repo, state)
            raise
    gates = list(getattr(args, "adapter_gates", []))
    gates += [(shlex.join(argv), argv) for argv in settings["gates"]]
    resolved_lines = [f"resolved: {path} ({state['notes'].get(path) or '(how not stated)'})"
                      for path in state["conflicts"]]
    if not settings["gates"]:
        _save_resolved(repo, state, record)
        message = 'no gates configured: set them with fold.py settings set --gate "CMD"'
        raise _GateFailure("no_gates", message,
                           [*resolved_lines, "gates: none configured", message])
    gates_line = _run_gates(repo, state, gates)
    ids = _publish(repo, settings, record, state)
    return [*resolved_lines, gates_line], ids


def _pause_lines(repo):
    state = _load_state(repo) or {}
    lines = [f"conflict: {path}" for path in state.get("conflicts", [])]
    return [*lines, "next: fold.py restack --continue (or fold.py restack --abort)"]


def cmd_restack(args):
    """restack: sync on demand; --continue resolves a paused restack; --abort restores it."""
    repo = args.repo
    try:
        if args.abort:
            state = _load_state(repo)
            if state is None:
                raise FlowError("restack_not_paused", "no restack is paused")
            _abort_and_restore(repo, state)
            print(render("restack", "-", "-", ["restored: every branch at its starting tip"],
                         "aborted"))
            return 0
        settings, record = read_settings(repo), read_record(repo)
        if args.continue_:
            lines, ids = _continue(repo, settings, record, args)
            print(render("restack", "-", "-", [*lines, f"restacked: {', '.join(ids)}"], "done"))
            return 0
        restacked = _sync_restacked(repo, settings, record)
    except _GateFailure as exc:
        print(render("restack", "-", "-", [*exc.lines, f"refused: {exc.reason}: {exc.detail}"],
                     f"refused {exc.reason}"))
        return 1
    except FlowError as exc:
        if exc.reason == "conflict":
            print(render("restack", "-", "-", _pause_lines(repo), "paused"))
            return 1
        lines = [f"refused: {exc.reason}: {exc.detail}"]
        if exc.reason == "bad_resolution":
            lines.append("gates: none run")
        print(render("restack", "-", "-", lines, f"refused {exc.reason}"))
        return 1
    if restacked:
        print(render("restack", "-", "-", [f"restacked: {', '.join(restacked)}"], "done"))
    else:
        print(render("restack", "-", "-", [], "nothing to do"))
    return 0


def cmd_hotfix(args):
    """hotfix --target T --name N: branch hotfix/N at T's remote tip, recorded outside the stack.

    The hotfix is never a stacked unit: it is not the stack's top and is never restacked. A
    target must be in the settings targets (default the remote HEAD branch, else main).
    """
    repo, name, target = args.repo, args.name, args.target
    branch = f"hotfix/{name}"
    try:
        if not _HOTFIX_NAME.fullmatch(name):
            raise FlowError("bad_value", "name must match [A-Za-z0-9._-]{1,64}")
        settings, record = read_settings(repo), read_record(repo)
        if target not in settings["targets"]:
            raise FlowError("unknown_target", f"{target} is not in the targets setting")
        _sync_restacked(repo, settings, record)
        if find_entry(record, name) is not None or flow_git.rev(repo, f"refs/heads/{branch}"):
            raise FlowError("bad_value", f"{branch} already exists")
        if _dirty(repo):
            raise FlowError("dirty_tree", "commit or discard the working tree changes first")
        remote = primary_remote(repo, settings)
        tip = flow_git.remote_tip(repo, remote, target)
        if tip is None:
            raise FlowError("no_trunk", f"no remote {target} ref to branch from")
        run_git(repo, "branch", branch, tip)
        run_git(repo, "switch", branch)
        record["units"].append({
            "id": name, "kind": "hotfix", "target": target, "branch": branch, "parent": target,
            "parent_tip": tip, "pr": None, "state": "open", "mvp": False, "pushed": None,
            "pending": None, "tags": [], "title": f"Hotfix {name}", "goal": "", "checkpoints": 0,
        })
        write_record(repo, record)
    except FlowError as exc:
        print(render("hotfix", name, branch, [f"refused: {exc.reason}: {exc.detail}"],
                     f"refused {exc.reason}"))
        return 1
    print(render("hotfix", name, branch, [f"branched from {target} at {tip[:12]}"], "done"))
    return 0
