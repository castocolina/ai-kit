#!/usr/bin/env python3
"""Fold finished work into one commit per logical feature (ai-kit-commit-fold).

Usage:
  fold.py fold <checkpoint.json|-> [--repo DIR] [--mode inline|subagent]
  fold.py gsd --phase N [--repo DIR] [--mode inline|subagent]
  fold.py superpowers --plan FILE [--base SHA] [--base-branch NAME] [--repo DIR] [--mode M]
  fold.py status --phase N [--repo DIR]

Exit 0 when folded or nothing to fold, 1 when refused, 2 for an unreadable or invalid checkpoint.
The status subcommand is read-only and always exits 0.
"""

import argparse
import json
import re
import sys

import fold_adapters
import fold_engine
import fold_group
from fold_engine import FoldError

_PHASE = re.compile(r"\d+(?:\.\d+)?")


def _phase(text):
    if not _PHASE.fullmatch(text):
        raise argparse.ArgumentTypeError("phase must be a number such as 7 or 2.1")
    return text


def _add_common(parser):
    parser.add_argument("--repo", default=".", help="repository (default: current directory)")
    parser.add_argument("--mode", choices=("inline", "subagent"), default="inline")


def build_parser():
    parser = argparse.ArgumentParser(prog="fold.py", description=(__doc__ or "").split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command")
    fold = sub.add_parser("fold", help="fold one checkpoint into logical commits")
    fold.add_argument("checkpoint", help="checkpoint JSON file, or - for stdin")
    _add_common(fold)
    gsd = sub.add_parser("gsd", help="fold every finished GSD plan of a phase, in plan order")
    gsd.add_argument("--phase", required=True, type=_phase)
    _add_common(gsd)
    superpowers = sub.add_parser("superpowers", help="fold a finished superpowers plan branch")
    superpowers.add_argument("--plan", required=True, help="superpowers plan file")
    superpowers.add_argument("--base", default=None, help="commit below the plan's first commit")
    superpowers.add_argument("--base-branch", default=None, help="base branch name")
    _add_common(superpowers)
    status = sub.add_parser("status", help="list each plan of a phase as folded or not")
    status.add_argument("--phase", required=True, type=_phase)
    _add_common(status)
    return parser


def _read(path):
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _emit(result):
    print(fold_engine.render_report(result))
    return 0 if result.outcome in ("folded", "nothing_to_fold") else 1


def _refused(unit, repo, mode, exc):
    return fold_engine.Result(
        unit=unit, ref=fold_adapters.current_ref(repo), before=0, after=0, tree="", tag="",
        outcome="refused", reason=exc.reason, grouping="", note=exc.detail, mode=mode)


def _no_work(unit, repo, mode):
    return fold_engine.Result(
        unit=unit, ref=fold_adapters.current_ref(repo), before=0, after=0, tree="", tag="",
        outcome="nothing_to_fold", reason="", grouping="", note="", mode=mode)


def _fold_checkpoint(args):
    try:
        checkpoint = fold_engine.load_checkpoint(_read(args.checkpoint))
    except (OSError, ValueError, FoldError) as exc:
        print(f"fold: cannot read checkpoint: {exc}", file=sys.stderr)
        return 2
    return _emit(fold_engine.fold(args.repo, checkpoint, fold_group.group_features, args.mode))


def _next_plan(repo, phase, skip):
    """(unit, checkpoint, error) of the first finished plan with commits to fold, in plan order."""
    for unit, state in fold_adapters.gsd_plans(repo, phase):
        if state != "finished" or unit in skip:
            continue
        try:
            checkpoint = fold_adapters.gsd_checkpoint(repo, phase, unit)
        except FoldError as exc:
            return unit, None, exc
        if checkpoint is not None:
            return unit, checkpoint, None
    return None, None, None


def _gsd(args):
    phase_unit = f"phase-{fold_adapters.padded_phase(args.phase)}"
    skip, folded, unit = set(), False, phase_unit
    try:
        while True:
            unit, checkpoint, error = _next_plan(args.repo, args.phase, skip)
            if error is not None:
                return _emit(_refused(unit, args.repo, args.mode, error))
            if checkpoint is None:
                break
            result = fold_engine.fold(args.repo, checkpoint, fold_group.group_features, args.mode)
            if result.outcome == "nothing_to_fold":
                skip.add(unit)
                continue
            if result.outcome == "refused":
                return _emit(result)
            print(fold_engine.render_report(result))
            folded = True
    except FoldError as exc:
        return _emit(_refused(unit, args.repo, args.mode, exc))
    if not folded:
        return _emit(_no_work(phase_unit, args.repo, args.mode))
    return 0


def _superpowers(args):
    unit = fold_adapters.superpowers_unit(args.plan)
    try:
        checkpoint = fold_adapters.superpowers_checkpoint(
            args.repo, args.plan, args.base, args.base_branch)
    except FoldError as exc:
        return _emit(_refused(unit, args.repo, args.mode, exc))
    return _emit(fold_engine.fold(args.repo, checkpoint, fold_group.group_features, args.mode))


def _status(args):
    try:
        lines = fold_adapters.phase_status(args.repo, args.phase)
    except (FoldError, OSError) as exc:
        print(f"status: {exc}")
        return 0
    for line in lines:
        print(line)
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    handlers = {"fold": _fold_checkpoint, "gsd": _gsd, "superpowers": _superpowers,
                "status": _status}
    if args.command not in handlers:
        parser.print_usage(sys.stderr)
        return 2
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
