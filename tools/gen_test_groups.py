#!/usr/bin/env python3
"""Refresh the generated test-group listings in the Makefile and the hook config.

The runner discovers tests/test_*.py, so the listings are a projection of that
discovery, not a second list to maintain. Run this after adding or moving a
module; tests/test_gate_scope.py fails while a listing is stale.
"""
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "tools" / "run_unittest_parallel.py"
MAKEFILE = REPO_ROOT / "Makefile"
HOOKS = REPO_ROOT / ".pre-commit-config.yaml"

BEGIN = "# BEGIN GENERATED test groups"
END = "# END GENERATED test groups"

def groups() -> tuple[dict[str, str], dict[str, str]]:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--list-groups"],
        capture_output=True, text=True, check=True,
    )
    parsed: dict[str, str] = {}
    hooks: dict[str, str] = {}
    for raw in proc.stdout.splitlines():
        name, modules = raw.split(": ", 1)
        (hooks if name.startswith("hook ") else parsed)[name.removeprefix("hook ")] = modules
    return parsed, hooks


def group_lines(parsed: dict[str, str]) -> list[str]:
    return [f"# {name}: {modules}" for name, modules in parsed.items()]


def replace_block(text: str, new_lines: list[str]) -> str:
    begin = text.index(BEGIN)
    end = text.index(END, begin)
    block = "\n".join([BEGIN, *new_lines, END])
    return text[:begin] + block + text[end + len(END):]


_ENTRY_RE = re.compile(r"(\s*)entry: (\S.*?)(?:\s+--\s.*)?$")


def _entry_match(line: str) -> re.Match[str] | None:
    return _ENTRY_RE.match(line)


def refresh_hook_entries(text: str, hook_listings: dict[str, str]) -> str:
    """Rewrite each hook entry's trailing module list from discovery."""
    lines = []
    current: str | None = None
    for line in text.splitlines():
        found = re.match(r"(\s*)- id: (\S+)", line)
        if found:
            current = found.group(2)
        elif current in hook_listings and (entry := _entry_match(line)):
            listed = hook_listings[current]
            line = f"{entry.group(1)}entry: {entry.group(2)} -- {listed}"
            current = None
        lines.append(line)
    return "\n".join(lines) + "\n"


def main() -> int:
    parsed, hook_listings = groups()
    lines = group_lines(parsed)
    MAKEFILE.write_text(replace_block(MAKEFILE.read_text(), lines))
    refreshed = replace_block(HOOKS.read_text(), lines)
    HOOKS.write_text(refresh_hook_entries(refreshed, hook_listings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
