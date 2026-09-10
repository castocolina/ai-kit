"""argparse-free CLI: capture / refine / dashboard / run."""

from __future__ import annotations

import json
import os
import sys

from ai_kit_usage_metrics import (
    capture_claude,
    dashboard,
    paths,
    raw_store,
    refined_store,
    refiner,
)

CAPTURE_SOURCES = {"claude": capture_claude.capture}


def _read_raw_jsonl(path: str) -> list[dict]:
    if not os.path.isfile(path):
        return []
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError:
                continue
    return records


def cmd_capture(env: dict) -> None:
    for name, fn in CAPTURE_SOURCES.items():
        try:
            cursor = raw_store.read_cursor(env, name)
            result = fn(env, cursor)
            raw_store.append_records(paths.raw_jsonl_path(env, name), result.records)
            raw_store.write_cursor(env, name, result.cursor)
        except Exception as exc:
            print(f"capture[{name}] failed: {exc}", file=sys.stderr)


def cmd_refine(env: dict) -> None:
    records = _read_raw_jsonl(paths.raw_jsonl_path(env, "claude"))
    rows = refiner.refine_simple_commands(records, env)
    conn = refined_store.open_refined_db(env)
    try:
        refined_store.insert_commands(conn, rows)
    finally:
        conn.close()


def cmd_dashboard(env: dict) -> None:
    db_path = paths.refined_db_path(env)
    output = paths.dashboard_html_path(env)
    if not os.path.isfile(db_path):
        dashboard.generate(None, output)
        return
    conn = refined_store.open_refined_db_readonly(env)
    try:
        dashboard.generate(conn, output)
    finally:
        conn.close()


def main(argv, env=None) -> int:
    resolved: dict = dict(os.environ) if env is None else env
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: ai-kit-usage-metrics.py {capture|refine|dashboard|run}")
        return 0
    cmd = argv[0]
    if cmd == "capture":
        cmd_capture(resolved)
        return 0
    if cmd == "refine":
        cmd_refine(resolved)
        return 0
    if cmd == "dashboard":
        cmd_dashboard(resolved)
        return 0
    if cmd == "run":
        cmd_capture(resolved)
        cmd_refine(resolved)
        cmd_dashboard(resolved)
        return 0
    print(f"unknown subcommand: {cmd}", file=sys.stderr)
    return 2
