#!/usr/bin/env python3
"""Propose the GSD phases a spec/discuss run should cover, each with its reason.

stdlib only. Input is `gsd-tools query roadmap analyze` JSON (a file, or stdin with `-`):

    phase_range.py --roadmap roadmap.json [--from N] [--to M] [--list N,M,...]

With no range, a phase is proposed when it has no CONTEXT or its SPEC is newer than its
CONTEXT (last git commit time, mtime for untracked files). Executed or complete phases are
skipped. Output: {"proposed": [{phase, dir, reason}], "skipped": [{phase, reason}]}.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
from collections.abc import Callable
from typing import Any

DONE_STATUSES = {"executed", "complete", "completed", "verified"}


def phase_key(number: str) -> tuple[int, ...]:
    """Numeric order for decimal phases: 16 < 16.1 < 16.2 < 17."""
    try:
        return tuple(int(part) for part in str(number).split("."))
    except ValueError:
        return (sys.maxsize,)


def phase_dir(phases_root: str, number: str) -> str | None:
    """The phase dir whose numeric prefix equals `number` (tolerates zero padding)."""
    for path in sorted(glob.glob(os.path.join(phases_root, "*-*"))):
        prefix = os.path.basename(path).split("-", 1)[0]
        if os.path.isdir(path) and phase_key(prefix) == phase_key(number):
            return path
    return None


def git_time(path: str, run: Callable[..., Any] = subprocess.run) -> float | None:
    """Last commit time of `path`, else its mtime (untracked), else None (missing)."""
    if not os.path.exists(path):
        return None
    try:
        out = run(["git", "log", "-1", "--format=%ct", "--", os.path.basename(path)],
                  cwd=os.path.dirname(path) or ".", capture_output=True, text=True,
                  check=False, timeout=10)
        stamp = (out.stdout or "").strip()
        if stamp:
            return float(stamp)
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return os.path.getmtime(path)


def first_match(directory: str, suffix: str) -> str | None:
    """The first `*-<suffix>` file in a phase dir."""
    hits = sorted(glob.glob(os.path.join(directory, f"*-{suffix}")))
    return hits[0] if hits else None


def undiscussed_reason(directory: str | None, timer: Callable[[str], float | None]) -> str | None:
    """Why a phase still needs spec/discuss, or None when it is discussed."""
    if not directory:
        return "no phase dir"
    context = first_match(directory, "CONTEXT.md")
    if not context:
        return "no CONTEXT"
    spec = first_match(directory, "SPEC.md")
    spec_time, context_time = (timer(spec) if spec else None), timer(context)
    if spec_time is not None and context_time is not None and spec_time > context_time:
        return "SPEC newer than CONTEXT"
    return None  # equal timestamps (one commit) count as discussed


def in_range(number: str, args: argparse.Namespace) -> bool:
    """Whether a phase is inside an explicit --list or --from/--to range."""
    if args.list:
        wanted = {phase_key(n) for n in args.list.split(",") if n.strip()}
        return phase_key(number) in wanted
    low = phase_key(args.start) if args.start else None
    high = phase_key(args.end) if args.end else None
    key = phase_key(number)
    return (low is None or key >= low) and (high is None or key <= high)


def propose(roadmap: dict[str, Any], phases_root: str, args: argparse.Namespace,
            timer: Callable[[str], float | None] = git_time) -> dict[str, list[dict[str, Any]]]:
    """Proposed and skipped phases in numeric order, each with its reason."""
    explicit = bool(args.list or args.start or args.end)
    proposed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    phases = sorted(roadmap.get("phases") or [], key=lambda p: phase_key(p.get("number", "")))
    for phase in phases:
        number = str(phase.get("number", ""))
        if explicit and not in_range(number, args):
            continue
        if phase.get("roadmap_complete") or phase.get("disk_status") in DONE_STATUSES:
            skipped.append({"phase": number, "reason": phase.get("disk_status") or "complete"})
            continue
        directory = phase_dir(phases_root, number)
        reason = undiscussed_reason(directory, timer)
        if explicit or reason:
            proposed.append({"phase": number, "dir": directory, "mode": phase.get("mode"),
                             "reason": reason or "explicitly requested"})
    return {"proposed": proposed, "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    """Exit 2 when the roadmap JSON is unreadable."""
    parser = argparse.ArgumentParser(
        prog="phase_range.py", description=(__doc__ or "").split("\n", 1)[0])
    parser.add_argument("--roadmap", required=True, help="roadmap analyze JSON file, or -")
    parser.add_argument("--phases-root", default=os.path.join(".planning", "phases"))
    parser.add_argument("--from", dest="start")
    parser.add_argument("--to", dest="end")
    parser.add_argument("--list", help="comma-separated phase numbers")
    args = parser.parse_args(argv)
    try:
        if args.roadmap == "-":
            roadmap = json.load(sys.stdin)
        else:
            with open(args.roadmap, encoding="utf-8") as handle:
                roadmap = json.load(handle)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": f"cannot read roadmap JSON: {error.__class__.__name__}"}),
              file=sys.stderr)
        return 2
    print(json.dumps(propose(roadmap, args.phases_root, args), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
