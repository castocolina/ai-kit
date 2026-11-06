#!/usr/bin/env python3
"""Fold finished work into one commit per logical feature (ai-kit-commit-fold).

Usage:
  fold.py fold <checkpoint.json|-> [--repo DIR] [--mode inline|subagent]
  fold.py gsd --phase N [--repo DIR] [--mode inline|subagent]
  fold.py superpowers --plan FILE [--base SHA] [--base-branch NAME] [--repo DIR] [--mode M]
  fold.py status --phase N [--repo DIR]
  fold.py start|guard|checkpoint|ready|show <unit selector> [--repo DIR]   (unit flow, plan 29.1-01)
  fold.py hotfix | restack | merge-chain | consent | settings | gsd-health   (unit flow)
  fold.py index [--repo DIR]   (refresh the codegraph index and graphify graph; exit 0)

Exit 0 when folded or nothing to fold, 1 when refused, 2 for an unreadable or invalid checkpoint.
The status subcommand is read-only and always exits 0.
"""

import argparse
import dataclasses
import importlib
import json
import os
import re
import sys

import flow_git
import flow_index
import flow_record
import fold_adapters
import fold_engine
import fold_group
from fold_engine import FoldError

# command -> (module, function); a module or function that is missing fails closed (exit 2).
_FLOW_HANDLERS = {
    "start": ("flow_unit", "cmd_start"),
    "guard": ("flow_unit", "cmd_guard"),
    "checkpoint": ("flow_unit", "cmd_checkpoint"),
    "ready": ("flow_unit", "cmd_ready"),
    "show": ("flow_unit", "cmd_show"),
    "consent": ("flow_record", "cmd_consent"),
    "settings": ("flow_record", "cmd_settings"),
    "hotfix": ("flow_stack", "cmd_hotfix"),
    "restack": ("flow_stack", "cmd_restack"),
    "merge-chain": ("flow_merge", "cmd_merge_chain"),
    "boundary": ("flow_boundary", "cmd_boundary"),
}
_UNIT_COMMANDS = ("start", "guard", "checkpoint", "ready", "show", "boundary")
_BAD_INPUT = frozenset({"bad_value", "missing_field", "unknown_field", "bad_checkpoint"})

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
    index = sub.add_parser("index", help="refresh the codegraph index and graphify graph")
    index.add_argument("--repo", default=".", help="repository (default: current directory)")
    mode = index.add_mutually_exclusive_group()
    mode.add_argument("--detach", action="store_true",
                      help="post-checkout hook: queue a new worktree for a detached runner")
    mode.add_argument("--drain", action="store_true", help="run queued index jobs")
    index.add_argument("--lock-fd", type=int, default=None,
                       help="with --drain: the job lock is already held through this fd")
    _add_flow_parsers(sub)
    return parser


def _add_repo(parser):
    parser.add_argument("--repo", default=".", help="repository (default: current directory)")


def _add_selector(parser, allow_next=False):
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--unit", dest="unit_file", metavar="FILE|-",
                       help="unit contract JSON, or - for stdin")
    group.add_argument("--phase", type=_phase, help="GSD phase number (GSD adapter)")
    group.add_argument("--plan", help="superpowers plan file (superpowers adapter)")
    group.add_argument("--unit-id", dest="unit_id", help="an already recorded unit")
    if allow_next:
        group.add_argument("--next", action="store_true",
                           help="no unit yet: brief the top stacked unit as the previous unit")


def _add_flow_parsers(sub):
    for name in _UNIT_COMMANDS:
        parser = sub.add_parser(name, help=f"unit flow: {name}")
        _add_selector(parser, allow_next=name == "boundary")
        _add_repo(parser)
        if name == "checkpoint":
            parser.add_argument("--checkpoint", metavar="FILE|-", help="checkpoint JSON")
            parser.add_argument("--base", default=None, help="fold base for --plan")
            parser.add_argument("--final", action="store_true", help="unit is finished")
        if name == "boundary":
            parser.add_argument("--point", required=True, choices=("start", "plan", "wave"),
                                help="start of the unit, before planning, or before wave 1")
    hotfix = sub.add_parser("hotfix", help="start a hotfix unit on a target branch")
    hotfix.add_argument("--target", required=True)
    hotfix.add_argument("--name", required=True)
    _add_repo(hotfix)
    restack = sub.add_parser("restack", help="restack units after a lower unit moved")
    restack.add_argument("--continue", dest="continue_", action="store_true")
    restack.add_argument("--abort", action="store_true")
    restack.add_argument("--note", action="append", default=[], metavar="PATH=HOW")
    _add_repo(restack)
    merge = sub.add_parser("merge-chain", help="merge the recorded units in stack order")
    group = merge.add_mutually_exclusive_group()
    group.add_argument("--until", dest="until", metavar="UNIT_ID")
    group.add_argument("--unit-id", dest="hotfix_id", metavar="HOTFIX_ID")
    _add_repo(merge)
    consent = sub.add_parser("consent", help="grant, revoke or show consent for this repo")
    consent.add_argument("action", choices=("grant", "revoke", "status"))
    consent.add_argument("--add-exclude", action="store_true")
    _add_repo(consent)
    settings = sub.add_parser("settings", help="show or set the flow settings")
    settings.add_argument("action", choices=("show", "set"))
    settings.add_argument("--remote")
    settings.add_argument("--target", action="append")
    settings.add_argument("--gate", action="append")
    _add_repo(settings)
    health = sub.add_parser("gsd-health", help="GSD adapter health gate (exit 0 when healthy)")
    _add_repo(health)


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


def _flow_refusal(command, reason, detail):
    print(f"flow {command}: refused: {reason}: {detail}")
    return 2 if reason in _BAD_INPUT else 1


def _load_contract(args, data):

    return flow_record.load_unit(data, flow_record.read_settings(args.repo)["targets"][0])


def _checkpoint_step(args, unit):
    """fold_step for --unit and --unit-id: fold the checkpoint file, bound to the unit branch."""

    def step(merged_refs):
        if args.checkpoint is None:
            raise flow_record.FlowError("bad_value", "checkpoint needs --checkpoint FILE|-")
        try:
            cp = fold_engine.load_checkpoint(_read(args.checkpoint))
        except (OSError, ValueError, FoldError) as exc:
            raise flow_record.FlowError("bad_checkpoint", getattr(exc, "detail", str(exc))) \
                from exc
        if cp.ref != f"refs/heads/{unit.branch}":
            raise flow_record.FlowError("ref_mismatch", f"checkpoint ref {cp.ref} is not the unit")
        cp = dataclasses.replace(cp, merged_refs=tuple(cp.merged_refs) + tuple(merged_refs),
                                 base_branch=unit.target)
        return fold_engine.fold(args.repo, cp, fold_group.group_features, "inline")

    return step


def _phase_step(args, unit):
    """fold_step for --phase: fold every pending GSD checkpoint of the phase, in plan order."""

    def step(merged_refs):
        skip, last = set(), None
        while True:
            plan_unit, checkpoint, error = _next_plan(args.repo, args.phase, skip)
            if error is not None:
                raise flow_record.FlowError(error.reason, error.detail)
            if checkpoint is None:
                break
            checkpoint = dataclasses.replace(
                checkpoint, merged_refs=tuple(checkpoint.merged_refs) + tuple(merged_refs),
                base_branch=unit.target)
            result = fold_engine.fold(args.repo, checkpoint, fold_group.group_features, "inline")
            if result.outcome == "nothing_to_fold":
                skip.add(plan_unit)
                continue
            if result.outcome == "refused":
                return result
            last = result
        return last if last is not None else _no_work(unit.id, args.repo, "inline")

    return step


def _plan_step(args, unit):
    """fold_step for --plan: fold from the recorded parent tip, or from --base when given."""

    def step(merged_refs):
        entry = flow_record.find_entry(flow_record.read_record(args.repo), unit.id)
        parent_tip = _fold_base(args.repo, entry) if entry is not None else None
        if (args.base is not None and parent_tip is not None
                and not flow_git.is_ancestor(args.repo, parent_tip, args.base)):
            raise flow_record.FlowError("bad_value", "--base must descend from parent_tip")
        try:
            checkpoint = fold_adapters.superpowers_checkpoint(
                args.repo, args.plan, args.base or parent_tip, unit.target)
        except FoldError as exc:
            raise flow_record.FlowError(exc.reason, exc.detail) from exc
        checkpoint = dataclasses.replace(checkpoint, merged_refs=tuple(merged_refs),
                                         base_branch=unit.target)
        return fold_engine.fold(args.repo, checkpoint, fold_group.group_features, "inline")

    return step


def _fold_base(repo, entry):
    """The recorded parent tip, or the last local planning commit start carried above it."""
    carried = entry.get("carried", 0)
    chain = flow_git.run_git(repo, "rev-list", "--reverse", "--first-parent",
                             f"{entry['parent_tip']}..refs/heads/{entry['branch']}").split()
    return chain[carried - 1] if 0 < carried <= len(chain) else entry["parent_tip"]


def _attach(args):
    """Resolve args.unit, args.fold_step and args.signals from the unit selector."""

    if args.unit_file is not None:
        args.unit = _load_contract(args, _read(args.unit_file))
        args.fold_step = _checkpoint_step(args, args.unit)
    elif args.unit_id is not None:
        entry = flow_record.find_entry(flow_record.read_record(args.repo), args.unit_id)
        if entry is None:
            raise flow_record.FlowError("not_started", f"unit {args.unit_id} is not recorded")
        args.unit = flow_record.Unit(
            id=entry["id"], kind=entry["kind"], target=entry["target"], branch=entry["branch"],
            title=entry["title"], goal=entry.get("goal", ""), mvp=entry.get("mvp", False))
        args.fold_step = _checkpoint_step(args, args.unit)
    elif args.phase is not None:
        args.unit = _load_contract(args, fold_adapters.gsd_unit(args.repo, args.phase))
        args.fold_step = _phase_step(args, args.unit)
        args.signals = fold_adapters.gsd_signals(args.repo, args.phase)
        args.plan_paths = (os.path.relpath(fold_adapters.phase_dir(args.repo, args.phase),
                                           args.repo),)
    else:
        args.unit = _load_contract(args, fold_adapters.superpowers_unit_contract(args.repo,
                                                                                 args.plan))
        args.fold_step = _plan_step(args, args.unit)
        # The planning commits: the plan file and the spec its **Spec:** line names.
        spec = fold_adapters.superpowers_spec_path(args.repo, args.plan)
        args.plan_paths = (os.path.relpath(os.path.join(args.repo, args.plan), args.repo),
                           *((spec,) if spec else ()))


def _flow(args):
    module_name, function_name = _FLOW_HANDLERS[args.command]
    try:
        handler = getattr(importlib.import_module(module_name), function_name)
    except (ImportError, AttributeError):
        print(f"fold.py: {args.command} is not available in this install", file=sys.stderr)
        return 2
    args.adapter_gates = fold_adapters.adapter_gates(args.repo)
    args.unit, args.fold_step, args.signals = None, None, (None, None)
    args.plan_paths = ()
    if args.command == "restack" and ((args.note and not args.continue_)
                                      or (args.continue_ and args.abort)):
        return _flow_refusal(args.command, "bad_value", "--note needs --continue; not both")
    if args.command == "checkpoint" and args.base is not None and args.plan is None:
        return _flow_refusal(args.command, "bad_value", "--base is only valid with --plan")
    if args.command in _UNIT_COMMANDS and not getattr(args, "next", False):
        try:
            _attach(args)
        except (flow_record.FlowError, FoldError) as exc:
            return _flow_refusal(args.command, exc.reason, exc.detail)
        except (OSError, ValueError) as exc:
            return _flow_refusal(args.command, "bad_value", str(exc))
    return handler(args)


def _gsd_health(args):
    ok, summary = fold_adapters.gsd_health(args.repo)
    print(summary)
    return 0 if ok else 1


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "index" and args.lock_fd is not None and not args.drain:
        parser.error("--lock-fd needs --drain")
    handlers = {"fold": _fold_checkpoint, "gsd": _gsd, "superpowers": _superpowers,
                "status": _status, "gsd-health": _gsd_health, "index": flow_index.cmd_index}
    if args.command in _FLOW_HANDLERS:
        return _flow(args)
    if args.command not in handlers:
        parser.print_usage(sys.stderr)
        return 2
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
