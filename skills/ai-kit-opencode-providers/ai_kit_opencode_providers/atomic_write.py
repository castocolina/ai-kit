"""Mode-preserving atomic writer. Resolves symlinks before replace."""

from __future__ import annotations

import contextlib
import os
import stat
import tempfile


def write_preserving_mode(path: str, text: str) -> None:
    """Atomically write `text` to `path`, preserving mode and symlink target.

    `os.path.realpath` first so POSIX rename(2) writes through a symlink
    rather than replacing the link with a regular file. `os.chmod` copies
    the original mode onto the temp file before replace (mkstemp is 0600).

    WR-01: `os.replace` is atomic with respect to concurrent readers, but
    on its own gives no durability guarantee against a crash/power-loss
    immediately after it returns -- the filesystem may not have persisted
    the temp file's data blocks yet even though the rename itself was
    journaled, and the config could come back truncated after recovery.
    `os.fsync` the temp file's data before the replace, then `os.fsync` the
    containing directory's fd after, so the new bytes and the renamed
    directory entry are both durable before this function returns.

    WR-02: `mkstemp` creates the temp file owned by the current process's
    uid/gid, so a plain `os.replace` would silently hand the config's
    ownership to whoever is running this tool -- a real "corrupts the
    config's attributes" case if `opencode.jsonc` was deployed or is
    expected to be owned by a different user/group (e.g. provisioned by a
    setup step, or normally edited via `sudo`). `os.chown` the temp file to
    the original owner before replace; a permission-denied chown (a
    non-root process changing to a different uid) is swallowed rather than
    failing the whole write -- refusing to persist a successful edit over a
    chown permission error would be worse than leaving ownership as the
    writing process's own in that one narrow case. `AttributeError` is also
    swallowed since `os.chown` does not exist on Windows.
    """
    target = os.path.realpath(path)
    st = os.stat(target)
    mode = stat.S_IMODE(st.st_mode)
    dirname = os.path.dirname(target) or "."
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        with contextlib.suppress(OSError, AttributeError):
            os.chown(tmp, st.st_uid, st.st_gid)
        os.replace(tmp, target)
        dir_fd = os.open(dirname, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
