#!/usr/bin/env python3
"""Fold one checkpointed run into one commit per logical feature (ai-kit-commit-fold).

Usage: fold.py fold <checkpoint.json|-> [--repo DIR] [--mode inline|subagent]

Exit 0 when folded or nothing to fold, 1 when refused, 2 for an unreadable or invalid checkpoint.
"""

import argparse
import json
import sys

import fold_engine
import fold_group


def build_parser():
    parser = argparse.ArgumentParser(prog="fold.py", description=(__doc__ or "").split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command")
    fold = sub.add_parser("fold", help="fold one checkpoint into logical commits")
    fold.add_argument("checkpoint", help="checkpoint JSON file, or - for stdin")
    fold.add_argument("--repo", default=".", help="repository to fold (default: current directory)")
    fold.add_argument("--mode", choices=("inline", "subagent"), default="inline")
    return parser


def _read(path):
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.command != "fold":
        parser.print_usage(sys.stderr)
        return 2
    try:
        checkpoint = fold_engine.load_checkpoint(_read(args.checkpoint))
    except (OSError, ValueError, fold_engine.FoldError) as exc:
        print(f"fold: cannot read checkpoint: {exc}", file=sys.stderr)
        return 2
    result = fold_engine.fold(args.repo, checkpoint, fold_group.group_features, args.mode)
    print(fold_engine.render_report(result))
    return 0 if result.outcome in ("folded", "nothing_to_fold") else 1


if __name__ == "__main__":
    sys.exit(main())
