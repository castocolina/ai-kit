"""Mode-preserving atomic writer. Resolves symlinks before replace."""

from __future__ import annotations

import os
import stat
import tempfile


def write_preserving_mode(path: str, text: str) -> None:
    """Atomically write `text` to `path`, preserving mode and symlink target.

    `os.path.realpath` first so POSIX rename(2) writes through a symlink
    rather than replacing the link with a regular file. `os.chmod` copies
    the original mode onto the temp file before replace (mkstemp is 0600).
    """
    target = os.path.realpath(path)
    mode = stat.S_IMODE(os.stat(target).st_mode)
    dirname = os.path.dirname(target) or "."
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
