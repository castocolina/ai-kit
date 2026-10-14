#!/usr/bin/env python3
"""Compute a SPEC's edge-coverage floor with gsd-core's edge-probe engine, or check a SPEC by it.

stdlib only; fails closed (exit 2) when node or the engine is missing.

    edge_floor.py floor <NN-SPEC.md> [--engine PATH]   # engine JSON on stdout
    edge_floor.py check <NN-SPEC.md> [--engine PATH]   # exit 1 when the table drifts

The table may add rows over the floor only when the Resolution cell carries "(added ...)", and an
`unclassified` row must stay "⚠ UNRESOLVED".
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from typing import Any

ENGINE_REL = os.path.join("bin", "lib", "edge-probe.cjs")
_REQ_RE = re.compile(r"^(\d+)\. \*\*(.+?)\*\*(.*?)(?=^\d+\. \*\*|\Z)", re.S | re.M)


def section(text: str, heading: str) -> str:
    """Body of `## heading` up to the next `## ` heading ("" when absent)."""
    match = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    return match.group(1) if match else ""


def requirements(spec_text: str) -> list[dict[str, str]]:
    """One rule, no truncation: the title plus every non-empty body line, bullets stripped."""
    reqs = []
    for match in _REQ_RE.finditer(section(spec_text, "Requirements")):
        body = " ".join(line.strip().lstrip("-").strip()
                        for line in match.group(3).splitlines() if line.strip())
        reqs.append({"id": f"R{match.group(1)}", "text": f"{match.group(2)}. {body}".strip()})
    return reqs


def engine_candidates(env: Mapping[str, str], cwd: str) -> list[str]:
    """edge-probe.cjs locations, in the spec workflow's order plus the other hosts."""
    home = env.get("HOME", "~")
    xdg = env.get("XDG_CONFIG_HOME", "").strip() or os.path.join(home, ".config")
    runtime = env.get("RUNTIME_DIR", "").strip() or cwd
    roots = [os.path.join(runtime, "gsd-core"), runtime, os.path.join(runtime, ".claude"),
             os.path.join(env.get("CLAUDE_CONFIG_DIR", "").strip()
                          or os.path.join(home, ".claude"), "gsd-core"),
             os.path.join(xdg, "opencode", "gsd-core"), os.path.join(home, ".codex", "gsd-core"),
             os.path.join(home, ".cursor", "gsd-core"),
             os.path.join(home, ".pi", "agent", "gsd-core")]
    return [os.path.expanduser(os.path.join(root, ENGINE_REL)) for root in roots]


def find_engine(env: Mapping[str, str], cwd: str, override: str | None) -> str | None:
    """First existing engine path, or None."""
    for path in ([override] if override else []) + engine_candidates(env, cwd):
        if os.path.isfile(path):
            return path
    return None


def run_engine(engine: str, reqs: list[dict[str, str]],
               run: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """Run the engine; raise RuntimeError on any failure (fail closed)."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node not found")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "requirements.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(reqs, handle)
        out = run([node, engine, path], capture_output=True, text=True, check=False, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"edge-probe exited {out.returncode}")
    result = json.loads(out.stdout)
    if not isinstance(result, dict) or not isinstance(result.get("items"), list):
        raise RuntimeError("edge-probe returned no items")
    return result


def table_rows(spec_text: str) -> list[dict[str, str]]:
    """The Edge Coverage table rows, header and separator skipped."""
    rows = []
    for line in section(spec_text, "Edge Coverage").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not line.lstrip().startswith("|") or len(cells) < 4:
            continue
        if cells[0].lower() == "category" or set(cells[0]) <= set("-: "):
            continue
        rows.append({"category": cells[0], "requirement": cells[1], "status": cells[2],
                     "resolution": " | ".join(cells[3:])})
    return rows


def compare(floor: dict[str, Any], rows: list[dict[str, str]]) -> dict[str, Any]:
    """Missing floor rows, unmarked extra rows, and unclassified rows not left unresolved."""
    want = {(item["category"], item["requirement_id"]) for item in floor["items"]}
    have = {(row["category"], row["requirement"]): row for row in rows}
    missing = sorted(want - set(have))
    unmarked = sorted(key for key in set(have) - want
                      if "(added" not in have[key]["resolution"])
    unclassified = sorted(key for key, row in have.items()
                          if key[0] == "unclassified" and "UNRESOLVED" not in row["status"])
    return {"ok": not (missing or unmarked or unclassified), "floor_rows": len(want),
            "table_rows": len(rows), "missing": missing, "unmarked_extra": unmarked,
            "unclassified_not_unresolved": unclassified}


def main(argv: list[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    """Exit 0 ok, 1 drift (check), 2 fail closed."""
    parser = argparse.ArgumentParser(
        prog="edge_floor.py", description=(__doc__ or "").split("\n", 1)[0])
    parser.add_argument("command", choices=("floor", "check"))
    parser.add_argument("spec")
    parser.add_argument("--engine", help="path to edge-probe.cjs")
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    try:
        with open(args.spec, encoding="utf-8") as handle:
            text = handle.read()
        engine = find_engine(env, os.getcwd(), args.engine)
        if not engine:
            raise RuntimeError("edge-probe.cjs not found (install gsd-core or pass --engine)")
        floor = run_engine(engine, requirements(text))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(json.dumps({"error": str(error), "fail_closed": True}), file=sys.stderr)
        return 2
    if args.command == "floor":
        print(json.dumps(floor, indent=1))
        return 0
    result = compare(floor, table_rows(text))
    print(json.dumps(result, indent=1))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
