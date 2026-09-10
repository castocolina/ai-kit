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
    inactive = {src for src, status in audit if status == "scanned-inactive"}
    for audit_path, status in audit:
        print(f"cross-reference: {audit_path} {status}", file=out)
    for ref in refs:
        line = (
            f'warning: "{args.provider_id}" is referenced in '
            f"{format_reference(ref)}"
        )
        if ref.source_path in inactive:
            line += (
                ' (not active: local review-spec sets strategy = "local-only")'
            )
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
    parser = argparse.ArgumentParser(prog="ai-kit-opencode-providers")
    sub = parser.add_subparsers(dest="command", required=True)
    p_remove = sub.add_parser("remove")
    p_remove.add_argument("provider_id")
    p_remove.add_argument("--config", default=None)
    p_list = sub.add_parser("list")
    p_list.add_argument("--config", default=None)
    args = parser.parse_args(argv)
    env = env_fn()
    cwd = cwd_fn()
    if args.command == "remove":
        return cmd_remove(args, env, cwd, out, err)
    if args.command == "list":
        return cmd_list(args, env, cwd, out, err)
    return EXIT_ERROR
