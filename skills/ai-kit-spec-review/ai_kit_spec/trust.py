"""Per-content-hash trust for project-local review-spec.toml files (D-08/D-09, Plan 16.1-08).

A cloned repository's `.aikit/review-spec.toml` names commands a third party controls, so its
exact content must be trusted before any of those commands can be spawned -- direnv/mise style:
the user reviews the exact argv once (`trust-local --show`), records consent, and any later edit
(byte-level, including line endings or encoding) invalidates it because the trust record is keyed
by realpath and sha256 of the raw bytes.

Records live under ai-kit's OWN config dir (`${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/
review-spec-trust/`), never in the project -- a repo must not be able to trust itself. Writes go
through cache.cache_write_json (mkstemp + os.replace), so two sessions trusting the same file
concurrently never collide or leave a half-written record.
"""
import hashlib
import os
import time

from ai_kit_spec.cache import cache_read_json, cache_write_json


def content_sha256(raw: bytes) -> str:
    """Hex sha256 over the file's raw bytes (pre-decoding, so any encoding or line-ending
    change yields a different hash and needs a new trust)."""
    return hashlib.sha256(raw).hexdigest()


def trust_key(real_path: str, sha: str) -> str:
    """Record name: sha256(realpath NUL content-sha256) -- binds consent to both the exact
    file (via realpath) and its exact content."""
    return hashlib.sha256(real_path.encode("utf-8") + b"\0" + sha.encode("ascii")).hexdigest()


def is_trusted(store_dir: str, real_path: str, raw: bytes) -> bool:
    """True only when a record for (real_path, sha256(raw)) exists and still carries both
    values -- a record is never trusted on filename alone."""
    record = cache_read_json(os.path.join(store_dir, trust_key(real_path, content_sha256(raw))
                                          + ".json"))
    if record is None:
        return False
    return record.get("path") == real_path and record.get("sha256") == content_sha256(raw)


def record_trust(store_dir: str, real_path: str, raw: bytes) -> str:
    """Write the trust record for (real_path, raw bytes); returns the record path."""
    sha = content_sha256(raw)
    record_path = os.path.join(store_dir, trust_key(real_path, sha) + ".json")
    cache_write_json(record_path, {
        "path": real_path,
        "sha256": sha,
        "trusted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    return record_path


def revoke_trust(store_dir: str, real_path: str) -> int:
    """Delete every trust record in store_dir whose `path` equals real_path (an edit after a
    trust produces a new key, so revocation must sweep by path, not by key). Missing store
    dir -> 0."""
    count = 0
    try:
        names = os.listdir(store_dir)
    except OSError:
        return 0
    for name in names:
        if not name.endswith(".json"):
            continue
        record = cache_read_json(os.path.join(store_dir, name))
        if record is not None and record.get("path") == real_path:
            try:
                os.unlink(os.path.join(store_dir, name))
                count += 1
            except OSError:
                pass
    return count
