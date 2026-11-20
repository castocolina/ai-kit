"""Fake herdr CLI for Phase 35 tests: helper only, not a test module.

It answers an exact argv table and logs every call as JSON lines.
"""

import json
import stat
import sys
from pathlib import Path


def write_herdr_fake(bin_dir: str | Path, answers: dict, log_path: str | Path) -> Path:
    """Write an executable herdr fake that answers exact argv tuples."""
    bin_path = Path(bin_dir)
    bin_path.mkdir(parents=True, exist_ok=True)
    fake = bin_path / "herdr"
    script = f"""#!{sys.executable}
import json, sys
_ANSWERS = {answers!r}
with open({str(log_path)!r}, "a", encoding="utf-8") as _handle:
    _handle.write(json.dumps({{"argv": sys.argv[1:]}}) + "\\n")
_hit = _ANSWERS.get(tuple(sys.argv[1:]))
if _hit is None:
    sys.exit(1)
sys.stdout.write(_hit[1])
sys.exit(_hit[0])
"""
    fake.write_text(script, encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return fake


def herdr_calls(log_path: str | Path) -> list:
    """Return logged argv lists in call order; a missing log means no calls."""
    path = Path(log_path)
    if not path.is_file():
        return []
    return [json.loads(line)["argv"] for line in path.read_text(encoding="utf-8").splitlines()]
