"""argparse CLI for ai-kit-opencode-providers."""

from __future__ import annotations

import argparse
import os
import sys

from ai_kit_opencode_providers.atomic_write import write_preserving_mode
from ai_kit_opencode_providers.config_paths import resolve_config_path
from ai_kit_opencode_providers.cross_reference import (
    collect_references,
    format_reference,
)
from ai_kit_opencode_providers.jsonc_edit import (
    iter_provider_entries,
    non_object_provider_keys,
    provider_summary,
    remove_provider,
    validate_removal,
)

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NO_CONFIG = 2


def cmd_remove(args, env, cwd, out, err) -> int:
    path = resolve_config_path(args.config, env)
    if not os.path.exists(path):
        print(f"error: no opencode config at {path}", file=err)
        return EXIT_NO_CONFIG
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: could not read {path}: {exc}", file=err)
        return EXIT_ERROR
    refs, audit = collect_references(args.provider_id, cwd, env)
    # WR-03: the qualifier text comes from each SourceStatus's own `.reason`
    # (set where the inactivity condition is actually computed, in
    # collect_references) rather than a string hardcoded here to the
    # "local-only" case -- so a future conditionally-inactive source is
    # explained correctly without touching this formatting code.
    inactive_reasons = {
        src: status.reason for src, status in audit if status == "scanned-inactive"
    }
    for audit_path, status in audit:
        print(f"cross-reference: {audit_path} {status}", file=out)
    for ref in refs:
        line = (
            f'warning: "{args.provider_id}" is referenced in '
            f"{format_reference(ref)}"
        )
        reason = inactive_reasons.get(ref.source_path)
        if reason is not None:
            line += f" (not active: {reason})"
        print(line, file=out)
    result = remove_provider(text, args.provider_id)
    if result is None:
        if args.provider_id in non_object_provider_keys(text):
            print(
                f'provider "{args.provider_id}" in {path} is not a '
                "config-based provider (its value is not an object) "
                "— nothing removed",
                file=out,
            )
        else:
            print(
                f'no provider "{args.provider_id}" in {path} — nothing to remove',
                file=out,
            )
        return EXIT_OK
    if not validate_removal(text, result, args.provider_id):
        print(
            f"error: refusing to write {path} — the edit could not be "
            "verified as structurally safe (the config may already be "
            "malformed); no changes were written",
            file=err,
        )
        return EXIT_ERROR
    try:
        write_preserving_mode(path, result)
    except OSError as exc:
        print(f"error: could not write {path}: {exc.strerror}", file=err)
        return EXIT_ERROR
    print(f'removed provider "{args.provider_id}" from {path}', file=out)
    return EXIT_OK


def cmd_list(args, env, cwd, out, err) -> int:
    path = resolve_config_path(args.config, env)
    if not os.path.exists(path):
        print(f"error: no opencode config at {path}", file=err)
        return EXIT_NO_CONFIG
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: could not read {path}: {exc}", file=err)
        return EXIT_ERROR
    entries = iter_provider_entries(text)
    if not entries:
        print(f"no config-based providers found in {path}", file=out)
    else:
        rows = [provider_summary(text, entry) for entry in entries]
        cells = [("ID", "NPM", "BASE URL")]
        for row in rows:
            cells.append(
                (
                    row["id"],
                    row["npm"] if row["npm"] is not None else "-",
                    row["baseURL"] if row["baseURL"] is not None else "-",
                )
            )
        widths = [
            max(len(cell[col]) for cell in cells) for col in range(3)
        ]
        for cell in cells:
            print(
                f"{cell[0]:<{widths[0]}}  {cell[1]:<{widths[1]}}  {cell[2]:<{widths[2]}}",
                file=out,
            )
    for key in non_object_provider_keys(text):
        print(
            f'note: "{key}" is a provider entry whose value is not an '
            "object — not a config-based provider, not listed above",
            file=out,
        )
    return EXIT_OK


def main(
    argv,
    env_fn=lambda: dict(os.environ),
    cwd_fn=os.getcwd,
    out=sys.stdout,
    err=sys.stderr,
) -> int:
    config_help = (
        "full path to opencode.jsonc (a FILE, not a directory); defaults to "
        "$OPENCODE_CONFIG_DIR/opencode.jsonc, else "
        "$XDG_CONFIG_HOME/opencode/opencode.jsonc, else "
        "~/.config/opencode/opencode.jsonc"
    )
    parser = argparse.ArgumentParser(
        prog="ai-kit-opencode-providers",
        description=(
            "List or remove config-based providers (object-valued entries "
            "under opencode.jsonc's \"provider\" key)."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_remove = sub.add_parser(
        "remove",
        help="remove a provider entry from opencode.jsonc",
        description=(
            "Remove one provider entry from the \"provider\" object, after "
            "a non-blocking cross-reference scan of review-spec and "
            "catalog files that only warns, never blocks."
        ),
    )
    p_remove.add_argument(
        "provider_id",
        help='the provider id (top-level key under "provider") to remove',
    )
    p_remove.add_argument("--config", default=None, help=config_help)
    p_list = sub.add_parser(
        "list",
        help="list config-based providers (id, npm, baseURL)",
        description=(
            'List config-based providers (object-valued entries under '
            '"provider") with their id, npm package, and options.baseURL.'
        ),
    )
    p_list.add_argument("--config", default=None, help=config_help)
    args = parser.parse_args(argv)
    env = env_fn()
    cwd = cwd_fn()
    if args.command == "remove":
        return cmd_remove(args, env, cwd, out, err)
    if args.command == "list":
        return cmd_list(args, env, cwd, out, err)
    return EXIT_ERROR
