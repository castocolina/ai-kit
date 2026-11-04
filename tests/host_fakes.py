"""Scratch-only fakes for host CLIs: the one shared helper for tests that need a host's output.

This is the only `tests/` file allowed to name a host binary as a command. The runner puts a
tripwire ahead of PATH that fails any module calling a real host CLI; a test that needs a
host's answer puts the fake bin dir from `write_host_fakes` first on its own PATH instead.
"""

import json
import os
import stat
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-spec-review"))
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"))

import gp_host
from ai_kit_spec.detection import RUNTIMES

HOST_NAMES = tuple(sorted(
    {name for row in RUNTIMES.values() for name in row.binaries} | set(gp_host.HOST_BINARY.values())
))

Answers = dict[tuple[str, ...], tuple[int, str]]

CLAUDE_ANSWERS: Answers = {
    ("--version",): (0, "2.1.300 (Claude Code)\n"),
    ("--help",): (0, "Usage: claude\n  goal  set a goal\n  loop  repeat\n  schedule  cron\n"),
}

_FAKE = """#!{python}
import json, sys
_ANSWERS = {answers!r}
with open({log!r}, "a", encoding="utf-8") as _handle:
    _handle.write(json.dumps({{"name": {name!r}, "argv": sys.argv[1:]}}) + "\\n")
_hit = _ANSWERS.get(tuple(sys.argv[1:]))
if _hit is None:
    sys.exit(1)
sys.stdout.write(_hit[1])
sys.exit(_hit[0])
"""


def write_host_fakes(
    bin_dir: str | Path,
    answers: dict[str, Answers] | None = None,
    log_path: str | Path | None = None,
) -> str:
    """One executable fake per host name in `bin_dir`; each logs a JSON line to `log_path`
    (default `<bin_dir>/host-fakes.log`) and answers only its exact argv table."""
    bin_path = Path(bin_dir)
    bin_path.mkdir(parents=True, exist_ok=True)
    log = str(log_path if log_path is not None else bin_path / "host-fakes.log")
    table: dict[str, Answers] = {"claude": CLAUDE_ANSWERS} if answers is None else answers
    for name in HOST_NAMES:
        fake = bin_path / name
        fake.write_text(
            _FAKE.format(
                python=sys.executable, answers=dict(table.get(name, {})), log=log, name=name,
            ),
            encoding="utf-8",
        )
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(bin_path)


def host_path(bin_dir: str | Path, base: str | None = None) -> str:
    """`bin_dir` first, then `base` (default: the current PATH)."""
    return str(bin_dir) + os.pathsep + (base if base is not None else os.environ.get("PATH", ""))


def fake_calls(log_path: str | Path) -> list[dict]:
    """The calls the fakes logged, oldest first; an absent log is no calls."""
    path = Path(log_path)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
