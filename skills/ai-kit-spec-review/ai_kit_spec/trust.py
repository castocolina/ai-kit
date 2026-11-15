"""Per-content-hash trust for project-local roster files (D-08/D-09 Plan 16.1-08, D-11 Plan 33-05).

A cloned repository's project roster names commands a third party controls, so its command-bearing
entries must be trusted before any of those commands can be spawned -- direnv/mise style: the user
reviews the exact argv once (`trust-local --show`), records consent, and a later change to a
command-bearing entry invalidates it. A record pins the file's realpath and the sha256 of the
bytes it is given. For the legacy roster file (a migration source, see config_migrate) those bytes
are the raw file bytes (`content_sha256`); for `config.toml` they are the canonical JSON of the
command-bearing lane
entries (`command_lanes_bytes`, D-11), so reformatting or an unrelated table keeps trust.

Records live under ai-kit's OWN config dir (`${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/`), never in
the project -- a repo must not be able to trust itself. Writes go through cache.cache_write_json
(mkstemp + os.replace), so two sessions trusting the same file concurrently never collide or leave
a half-written record.
"""
import hashlib
import json
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
    # fsencode, not .encode("utf-8"): a surrogate-escaped (non-UTF-8) path must not raise.
    return hashlib.sha256(os.fsencode(real_path) + b"\0" + sha.encode("ascii")).hexdigest()


def is_trusted(store_dir: str, real_path: str, raw: bytes) -> bool:
    """True only when a record for (real_path, sha256(raw)) exists and still carries both
    values -- a record is never trusted on filename alone."""
    record = cache_read_json(os.path.join(store_dir, trust_key(real_path, content_sha256(raw))
                                          + ".json"))
    if not isinstance(record, dict):  # missing, or a non-object JSON value
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
        if isinstance(record, dict) and record.get("path") == real_path:
            try:
                os.unlink(os.path.join(store_dir, name))
                count += 1
            except OSError:
                pass
    return count


def _entry_key(entry: dict):
    key = entry.get("key")
    return key if isinstance(key, str) else None


def command_lanes_bytes(lanes: dict, user_command_keys: frozenset = frozenset()) -> bytes | None:
    """Canonical bytes of the command-running lane entries (D-11), or None when there are none.

    The list holds `[role, entry]` for roles in sorted order and entries in file order, for every
    entry that has a `command` key, and for every entry whose `key` is in the command keys: the
    user roster's command keys (`user_command_keys`, passed by the caller; an entry that overrides
    a user command entry changes its arguments) plus the `key` of every command entry in this
    file, in any role. cfg_merge_reviewers folds a row with the same `key` into the command entry
    and its fields fill the command's placeholders, so such a row is part of the digest (review
    concern C1-12). Over-inclusion is fail-closed: an extra entry in the digest only means an edit
    to it needs a new trust. Reformatting, comments and unrelated tables do not change these bytes.
    """
    roles = sorted(role for role, items in lanes.items() if isinstance(items, list))
    entries = [(role, entry) for role in roles for entry in lanes[role] if isinstance(entry, dict)]
    command_keys = set(user_command_keys)
    for _role, entry in entries:
        key = _entry_key(entry)
        if "command" in entry and key is not None:
            command_keys.add(key)
    picked = [[role, entry] for role, entry in entries
              if "command" in entry or (_entry_key(entry) is not None
                                        and _entry_key(entry) in command_keys)]
    if not picked:
        return None
    return json.dumps(picked, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("utf-8")
