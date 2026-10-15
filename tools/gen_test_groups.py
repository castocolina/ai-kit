#!/usr/bin/env python3
"""Refresh the generated test-group listings in the Makefile and the hook config.

The runner discovers tests/test_*.py, so the listings are a projection of that
discovery, not a second list to maintain. Run this after adding or moving a
module; tests/test_gate_scope.py fails while a listing is stale (it compares
render() in memory and never writes).
"""
import contextlib
import os
import pathlib
import re
import subprocess
import sys
import tempfile

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


def render(
    makefile_text: str, hooks_text: str, listing: tuple[dict[str, str], dict[str, str]]
) -> tuple[str, str]:
    """The Makefile and hook-config text with refreshed listings; pure, writes nothing."""
    parsed, hook_listings = listing
    lines = group_lines(parsed)
    hooks = refresh_hook_entries(replace_block(hooks_text, lines), hook_listings)
    return replace_block(makefile_text, lines), hooks


def _atomic_write(path: pathlib.Path, text: str) -> None:
    """Replace path in one rename, so a concurrent reader never sees a partial file."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.chmod(tmp, path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def main() -> int:
    for path, text in zip(
        (MAKEFILE, HOOKS),
        render(MAKEFILE.read_text(), HOOKS.read_text(), groups()),
        strict=True,
    ):
        if path.read_text() != text:
            _atomic_write(path, text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
