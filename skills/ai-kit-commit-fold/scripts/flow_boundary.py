"""The boundary step (plan 30-04): refresh the indexes, then rewrite the unit brief.

`fold.py boundary` runs it at a unit's start (`start` calls it), before planning and before the
first execution wave. It never commits. It writes the brief, the index files, `.git/info/exclude`
(`.aikit/`), and a `.graphifyignore` line it reports as `note:`; the owner commits that line.
"""

import datetime
import functools
import shutil
import time
from dataclasses import dataclass

import flow_brief
import flow_git
import flow_index
import fold_adapters
from flow_index import _run_tool, _top_of
from flow_record import FlowError, common_dir, find_entry, read_record, render

_BAD_INPUT = frozenset({"bad_value", "missing_field", "unknown_field"})


def _utc_now():
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Seams:
    """The injectable seams, in one object so the functions stay within pylint's arg count."""

    run: object = _run_tool
    which: object = shutil.which
    clock: object = time.monotonic
    sleep: object = time.sleep
    now: object = _utc_now
    lock_deadline_s: int = 600


def previous_unit(record, unit_id):
    """The last stacked entry before `unit_id`; for an unrecorded or None id, the last other one."""
    units = record["units"]
    ids = [entry["id"] for entry in units]
    if unit_id in ids:
        before = [entry for entry in units[:ids.index(unit_id)] if entry["kind"] == "stacked"]
        return before[-1] if before else None
    others = [entry for entry in units if entry["kind"] == "stacked" and entry["id"] != unit_id]
    return others[-1] if others else None


def unit_range(repo, entry):
    """(base, end) of a recorded unit: its parent tip to its branch tip, else to its pushed tip.
    None (the brief's "range unknown") when either commit is gone, e.g. pruned after a squash."""
    base = entry.get("parent_tip")
    tip = flow_git.rev(repo, f"refs/heads/{entry['branch']}") or entry.get("pushed")
    if not base or not tip:
        return None
    if any(flow_git.rev(repo, f"{sha}^{{commit}}") is None for sha in (base, tip)):
        return None
    return (base, tip)


def _facts(top, record, unit, point, seams):
    previous = previous_unit(record, unit.id if unit else None)
    span = unit_range(top, previous) if previous else None
    changed = tuple(flow_brief.changed_files(top, *span)) if span else ()
    names, label, found = flow_brief.search(top, changed, seams.run, seams.which)
    return flow_brief.BriefFacts(
        unit=unit.id if unit else "next (for whoever writes the next unit's plan)",
        branch=unit.branch if unit else (flow_git.head_branch(top) or "-"),
        head=(flow_git.rev(top, "HEAD") or "")[:12],
        point=point,
        written=seams.now(),
        base_branch=unit.target if unit else fold_adapters.base_branch(top),
        previous=previous["id"] if previous else None,
        previous_branch=previous["branch"] if previous else "",
        unit_range=span,
        changed=changed,
        names=names,
        names_label=label,
        mentions=found,
    )


def _summary(facts):
    if facts.previous is None:
        return "no previous unit"
    count = len(facts.changed)
    return f"previous unit {facts.previous}, {count} changed file{'' if count == 1 else 's'}"


def boundary(repo, unit, point, phase=None, seams=None):
    """Refresh both indexes under the job lock, then write the brief; returns (lines, outcome).

    The execution point (`wave`) of a phase whose wave-1 plans all have summaries is skipped:
    the first wave is over, so no tool runs and the brief is left as it is.
    """
    seams = seams or Seams()
    top = _top_of(repo)
    if top is None:
        raise FlowError("bad_value", f"{repo} is not inside a git checkout")
    record = read_record(repo)
    if unit is not None and find_entry(record, unit.id) is not None:
        head = flow_git.head_branch(top)
        if head != unit.branch:
            raise FlowError("ref_mismatch",
                            f"HEAD is on {head or 'no branch'}, not the unit branch "
                            f"{unit.branch}; switch to it")
    if point == "wave" and phase is not None and fold_adapters.index_wave_one_done(top, phase):
        return ["wave 1 finished: boundary skipped"], "nothing to do"
    common = common_dir(top)
    release = functools.partial(flow_index.launch_runner, common, top)
    lines = []
    with flow_index.index_lock(common, seams.clock, seams.sleep, seams.lock_deadline_s,
                               on_release=release) as held:
        if held:
            lines += flow_index.refresh(top, seams.run, seams.which, seams.clock, seams.sleep)
        else:
            lines.append(f"index: lock held past {seams.lock_deadline_s} s; indexes not "
                         "refreshed, retried at the next point")
        facts = _facts(top, record, unit, point, seams)
        lines += flow_index.ensure_excluded(top, [".aikit"])
        flow_brief.write_brief(top, flow_brief.render(facts))
    lines.append(f"brief: {flow_brief.BRIEF_REL.as_posix()} ({_summary(facts)})")
    notes = [line[len("note: "):] for line in lines if line.startswith("note: ")]
    lines = [line for line in lines if not line.startswith("note: ")]
    if notes:
        lines.append("note: " + "; ".join(notes))
    return lines, "done"


def cmd_boundary(args):
    """`fold.py boundary (<selector> | --next) --point start|plan|wave`."""
    unit = getattr(args, "unit", None)
    unit_id = unit.id if unit else "next"
    branch = unit.branch if unit else "-"
    try:
        lines, outcome = boundary(args.repo, unit, args.point,
                                  phase=getattr(args, "phase", None))
    except FlowError as exc:
        text = render("boundary", unit_id, branch,
                      [f"refused: {exc.reason}: {exc.detail}"], f"refused {exc.reason}")
        print(text)
        return 2 if exc.reason in _BAD_INPUT else 1
    print(render("boundary", unit_id, branch, lines, outcome))
    return 0
