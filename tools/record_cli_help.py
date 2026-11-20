"""Maintainer command (35 D-14): record opencode help into tests/fixtures/cli_help/opencode/.
Tests never run it. Usage: python3 tools/record_cli_help.py --home <scratch dir>"""

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tests" / "fixtures" / "cli_help" / "opencode"
COMMANDS = (
    ("version.txt", ["--version"]),
    ("help.txt", ["--help"]),
    ("run-help.txt", ["run", "--help"]),
    ("models-help.txt", ["models", "--help"]),
)


def child_env(home: Path, base) -> dict:
    """Build a clean host environment rooted under the requested scratch home."""
    env = {key: value for key, value in base.items() if not key.startswith("OPENCODE_")}
    env.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "XDG_STATE_HOME": str(home / ".local" / "state"),
            "AI_KIT_REFUSE_REAL_HOME": "1",
            "OPENCODE_DISABLE_AUTOUPDATE": "1",
            "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
            "OPENCODE_CONFIG_PROJECT_DISABLE": "1",
        }
    )
    return env


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def _record_commands(binary: str, home: Path, env: dict) -> int:
    for filename, command_args in COMMANDS:
        result = subprocess.run(
            [binary, *command_args],
            capture_output=True,
            text=True,
            env=env,
            cwd=home,
            timeout=30,
            check=False,
        )
        if result.returncode:
            print(f"{filename}: exit {result.returncode}", file=sys.stderr)
            return 1
        text = result.stdout if result.stdout or not result.stderr else result.stderr
        _write_atomic(OUT / filename, text)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Record installed opencode help fixtures")
    parser.add_argument("--home", required=True)
    args = parser.parse_args(argv)
    home = Path(args.home).resolve()
    binary = shutil.which("opencode")
    if binary is None:
        print("opencode not found", file=sys.stderr)
        return 1

    folders = (
        home,
        home / ".config",
        home / ".cache",
        home / ".local" / "share",
        home / ".local" / "state",
    )
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    env = child_env(home, os.environ)
    if _record_commands(binary, home, env):
        return 1

    version_text = (OUT / "version.txt").read_text(encoding="utf-8")
    match = re.search(r"(\d+\.\d+\.\d+)", version_text)
    if match is None:
        print("version.txt: no semantic version found", file=sys.stderr)
        return 1
    version = match.group(1)
    metadata = {
        "version": version,
        "recorded": time.strftime("%Y-%m-%d"),
        "commands": [
            "opencode --version",
            "opencode --help",
            "opencode run --help",
            "opencode models --help",
        ],
    }
    _write_atomic(OUT / "meta.json", json.dumps(metadata, indent=1) + "\n")
    print(f"recorded opencode {version} into {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
