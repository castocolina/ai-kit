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


def project_root(env: Mapping[str, str], start: str) -> str:
    """`RUNTIME_DIR`, else the git toplevel of `start`, else `start` (gsd_run resolver rule)."""
    if env.get("RUNTIME_DIR", "").strip():
        return env["RUNTIME_DIR"].strip()
    try:
        out = subprocess.run(["git", "-C", start, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return start
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else start


def _host_homes(env: Mapping[str, str]) -> list[str]:
    """Host config homes, in gsd-core's own `gsd_run` resolver order (gsd-run-resolver.md)."""
    home = env.get("HOME", "~")
    xdg = env.get("XDG_CONFIG_HOME", "").strip() or os.path.join(home, ".config")

    def pick(names: tuple[str, ...], default: str) -> str:
        return next((env[n].strip() for n in names if env.get(n, "").strip()), default)

    return [pick(("CLAUDE_CONFIG_DIR",), os.path.join(home, ".claude")),
            pick(("ANTIGRAVITY_CONFIG_DIR",), os.path.join(home, ".gemini", "antigravity")),
            os.path.join(home, ".gemini", "antigravity-ide"),
            os.path.join(home, ".gemini", "antigravity-cli"),
            pick(("AUGMENT_CONFIG_DIR",), os.path.join(home, ".augment")),
            pick(("CLINE_CONFIG_DIR",), os.path.join(home, ".cline")),
            pick(("CODEBUDDY_CONFIG_DIR",), os.path.join(home, ".codebuddy")),
            pick(("CODEX_HOME",), os.path.join(home, ".codex")),
            pick(("COPILOT_CONFIG_DIR", "COPILOT_HOME"), os.path.join(home, ".copilot")),
            pick(("CURSOR_CONFIG_DIR",), os.path.join(home, ".cursor")),
            pick(("HERMES_HOME",), os.path.join(home, ".hermes")),
            pick(("KILO_CONFIG_DIR",), os.path.join(xdg, "kilo")),
            pick(("KIMI_CONFIG_DIR",), os.path.join(home, ".config", "agents")),
            os.path.join(home, ".agents"),
            pick(("KIMI_CODE_HOME",), os.path.join(home, ".kimi-code")),
            pick(("OPENCODE_CONFIG_DIR",), os.path.join(xdg, "opencode")),
            pick(("PI_CODING_AGENT_DIR",), os.path.join(home, ".pi", "agent")),
            pick(("QWEN_CONFIG_DIR",), os.path.join(home, ".qwen")),
            pick(("TRAE_CONFIG_DIR",), os.path.join(home, ".trae")),
            pick(("WINDSURF_CONFIG_DIR",), os.path.join(home, ".codeium", "windsurf")),
            pick(("ZCODE_CONFIG_DIR",), os.path.join(home, ".zcode")),
            pick(("GROK_AGENTS_HOME",), os.path.join(home, ".agents"))]


def engine_candidates(env: Mapping[str, str], root: str) -> list[str]:
    """edge-probe.cjs locations: project-local installs, then host homes, then `gsd_run` on PATH."""
    roots = [os.path.join(root, "gsd-core"), os.path.join(root, ".claude", "gsd-core"),
             os.path.join(root, ".codex", "gsd-core")]
    roots += [os.path.join(h, "gsd-core") for h in _host_homes(env)]
    paths = [os.path.expanduser(os.path.join(r, ENGINE_REL)) for r in roots]
    # gsd_run sits in gsd-core/bin/; the GSD shim puts that dir on PATH for later shells.
    launcher = shutil.which("gsd_run", path=env["PATH"]) if env.get("PATH") else None
    if launcher:
        paths.append(os.path.join(os.path.dirname(os.path.realpath(launcher)), "lib",
                                  os.path.basename(ENGINE_REL)))
    return paths


def find_engine(env: Mapping[str, str], start: str, override: str | None) -> str | None:
    """First existing engine path, or None."""
    for path in ([override] if override else []) + engine_candidates(env,
                                                                     project_root(env, start)):
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
        engine = find_engine(env, os.path.dirname(os.path.abspath(args.spec)), args.engine)
        if not engine:
            raise RuntimeError("edge-probe.cjs not found (install gsd-core or pass --engine)")
        reqs = requirements(text)
        if not reqs:  # an empty floor would let any table pass the gate
            raise ValueError("no requirements extracted: expected numbered **bold** entries "
                             "under ## Requirements")
        floor = run_engine(engine, reqs)
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
