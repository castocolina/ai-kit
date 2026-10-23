#!/usr/bin/env python3
"""Validate Phase 21.3 live evidence and scratch-environment isolation."""

from __future__ import annotations

import os
import re
import stat
import sys
from pathlib import Path

REQUIRED_ROWS = tuple(f"L-{host}{number}" for host, count in (("C", 8), ("P", 4)) for number in range(1, count + 1))
ISOLATION_VARS = (
    "HOME",
    "CLAUDE_CONFIG_DIR",
    "CURSOR_CONFIG_DIR",
    "PI_CODING_AGENT_DIR",
    "OPENCODE_CONFIG_DIR",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_STATE_HOME",
    "XDG_CACHE_HOME",
    "XDG_RUNTIME_DIR",
)
OPENCODE_ADAPTER = "tools/hooks/opencode/ai-kit-tool-advisor.ts"
LAST_OWN_PLAN = 8


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def preflight(env: dict[str, str]) -> list[str]:
    """Return isolation failures for a supplied environment mapping."""
    root = Path.cwd() / "tmp" / "p213"
    root_real = root.resolve()
    failures = []
    resolved: dict[str, Path] = {}
    for name in ISOLATION_VARS:
        value = env.get(name)
        if not value:
            failures.append(f"{name} is unset")
            continue
        path = Path(value)
        if not path.is_absolute():
            path = Path.cwd() / path
        real = path.resolve()
        resolved[name] = real
        if not _within(real, root_real):
            failures.append(f"{name} points outside tmp/p213")
    runtime = resolved.get("XDG_RUNTIME_DIR")
    if runtime is not None:
        try:
            info = runtime.stat()
        except OSError:
            failures.append("XDG_RUNTIME_DIR does not exist")
        else:
            if not stat.S_ISDIR(info.st_mode):
                failures.append("XDG_RUNTIME_DIR is not a directory")
            if info.st_uid != os.getuid():
                failures.append("XDG_RUNTIME_DIR is not owned by the current user")
            if stat.S_IMODE(info.st_mode) != 0o700:
                failures.append("XDG_RUNTIME_DIR mode is not 0700")
    return failures


def _adapter_plan_exists(directory: Path) -> bool:
    for plan in directory.glob("21.3-*-PLAN.md"):
        match = re.fullmatch(r"21\.3-(\d+)-PLAN\.md", plan.name)
        if not match or int(match.group(1)) <= LAST_OWN_PLAN:
            continue
        try:
            text = plan.read_text(encoding="utf-8")
        except OSError:
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        frontmatter = parts[1]
        listed = False
        in_files = False
        for line in frontmatter.splitlines():
            if line.startswith("files_modified:"):
                in_files = True
                continue
            if in_files and line and not line[0].isspace():
                in_files = False
            if in_files and re.fullmatch(r"\s*-\s*[`\"]?" + re.escape(OPENCODE_ADAPTER) + r"[`\"]?\s*", line):
                listed = True
                break
        if listed and (directory / f"21.3-{match.group(1)}-SUMMARY.md").is_file():
            return True
    return False


def check(path: str | Path) -> list[str]:
    """Return human-readable evidence failures for a LIVE markdown file."""
    live_path = Path(path)
    try:
        lines = live_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"LIVE file cannot be read: {exc}"]
    failures = []
    found: dict[str, list[str]] = {}
    for line in lines:
        if not line.startswith("| L-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells:
            found.setdefault(cells[0], []).append(cells[-1])
    for row in REQUIRED_ROWS:
        results = found.get(row, [])
        if len(results) != 1:
            failures.append(f"{row}: expected exactly one row, found {len(results)}")
        elif results[0] != "pass":
            failures.append(f"{row}: Result is {results[0]!r}, expected 'pass'")

    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "## S-OC")
    except StopIteration:
        failures.append("S-OC: section is missing")
        return failures
    section = lines[start + 1 :]
    result_lines = [line.strip() for line in section if line.strip().startswith("Result:")]
    launch_lines = [line.strip() for line in section if line.strip().startswith("Launched with:")]
    if not result_lines:
        failures.append("S-OC: Result line is missing")
        result = ""
    else:
        result = result_lines[0][len("Result:") :].strip()
        if result != "pass" and not result.startswith("fail ("):
            failures.append(f"S-OC: unresolved Result {result!r}")
    if not launch_lines:
        failures.append("S-OC: Launched with line is missing")
    elif "--standalone" not in launch_lines[0]:
        failures.append("S-OC: Launched with must contain --standalone")
    if result == "pass" and not _adapter_plan_exists(live_path.parent):
        failures.append("S-OC: pass requires a later adapter plan listing the adapter in files_modified and its SUMMARY")
    return failures


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--preflight"]:
        failures = preflight(dict(os.environ))
    elif len(args) == 1:
        failures = check(args[0])
    else:
        print("Usage: check_live.py <LIVE.md> | --preflight", file=sys.stderr)
        return 2
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: live evidence is complete" if args != ["--preflight"] else "PASS: scratch environment is isolated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
