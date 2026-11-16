"""Roster migration: a layer's old review-spec.toml into its config.toml (SPEC R4, R5; D-10, D-12).

This is the only Python module that names review-spec.toml and review-spec-trust (D-10). It imports
only trust and toml_splice from ai_kit_spec, so it cannot form an import cycle with the config
reader. An old roster is copied, never merged: its values land under `[lanes]` in config.toml,
the new file is re-read and compared, and only then is the old file renamed to `*.migrated`.
"""

import os
import tomllib

from ai_kit_spec import toml_splice, trust

LEGACY_NAME = "review-spec.toml"
LEGACY_TRUST_DIR = "review-spec-trust"
MIGRATED_SUFFIX = ".migrated"
_ATTEMPTS = 2
_REFUSED_INLINE = ("[[reviewers]] written as an inline array is not migrated; "
                   "rewrite it as [[reviewers]] tables")
_REFUSED_TABLES = ("reviewers tables other than [[reviewers]] entries are not migrated; "
                   "rewrite them as [[reviewers]] tables")


class LegacyRosterError(ValueError):
    """An old roster that cannot be migrated: unreadable, malformed or of a shape not written.

    Nothing is written when it is raised. Plan 07 maps it to the exit-2 ConfigError path.
    """

    def __init__(self, path: str, message: str):
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


# ── Paths and the old roster's values ────────────────────────────────────


def legacy_path(new_path: str) -> str:
    """The old roster beside a layer's config.toml."""
    return os.path.join(os.path.dirname(new_path), LEGACY_NAME)


def legacy_trust_dir(trust_dir: str) -> str:
    """The old trust store beside the new one (`review-spec-trust/` next to `config-trust/`)."""
    return os.path.join(os.path.dirname(os.path.normpath(trust_dir)), LEGACY_TRUST_DIR)


def pending(new_path: str):
    """The old roster path while a migration is still pending, else None."""
    old = legacy_path(new_path)
    return old if os.path.isfile(old) else None


def revoke_legacy_trust(new_path: str, trust_dir: str) -> int:
    """Remove the old-rule trust records of the old roster beside new_path (review concern C2-3).

    `trust-local --revoke` calls it before the first migration, so the migration's trust carry
    finds no legacy consent to re-key. Realpath also resolves a path whose file is already gone.
    """
    return trust.revoke_trust(legacy_trust_dir(trust_dir),
                              os.path.realpath(legacy_path(new_path)))


def split_by_purpose(entries) -> tuple[list, list]:
    """The (review, execute) entries of an old roster (D-24): `purpose = "execute"` goes to execute,
    `"both"` to each role, and anything else (no purpose included) to review."""
    review = []
    execute = []
    for entry in entries:
        purpose = entry.get("purpose") if isinstance(entry, dict) else None
        if purpose == "execute":
            execute.append(entry)
        elif purpose == "both":
            review.append(entry)
            execute.append(entry)
        else:
            review.append(entry)
    return review, execute


def lanes_from_legacy(old: dict) -> dict:
    """The [lanes] table an old roster parses to: its top-level keys, then its review and execute
    lanes (each only when non-empty)."""
    lanes = {key: value for key, value in old.items() if key != "reviewers"}
    review, execute = split_by_purpose(old.get("reviewers", []))
    if review:
        lanes["review"] = review
    if execute:
        lanes["execute"] = execute
    return lanes


def read_legacy(new_path: str):
    """(lanes_from_legacy(parsed), raw bytes) of the old roster beside new_path, or None."""
    old = legacy_path(new_path)
    raw = _read_bytes(old)
    if raw is None:
        return None
    return lanes_from_legacy(_parse_text(old, _decode(old, raw))), raw


# ── Text helpers ─────────────────────────────────────────────────────────


def _read_bytes(path: str):
    """The file's bytes, or None when it does not exist. migrate_layer reads every file only through
    here, so a test can wrap it to inject a concurrent write."""
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise LegacyRosterError(path, f"could not read ({exc})") from exc


def _decode(path: str, raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LegacyRosterError(path, f"not valid UTF-8 ({exc})") from exc


def _parse_text(path: str, text: str) -> dict:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise LegacyRosterError(path, str(exc)) from exc


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _final_newline(text: str) -> str:
    return text if not text or text.endswith("\n") else text + _newline(text)


def _close_index(text: str, start: int) -> int:
    """Index of the first `]` outside quotes at or after start (the end of a header's name)."""
    quote = ""
    index = start
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\" and quote == '"':
                index += 1
            elif char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "]":
            return index
        index += 1
    return len(text)


def _head_parts(line: str) -> tuple:
    """The indent of a table header line and what follows its closing brackets (a comment, the
    newline)."""
    body = line.lstrip()
    indent = line[: len(line) - len(body)]
    width = 2 if body.startswith("[[") else 1
    end = _close_index(body, width) + width
    return indent, body[end:]


def _with_head(block, path: tuple) -> list:
    """The block's lines with its header renamed to `path`; the comment lines above the header, the
    indent and any trailing comment are kept."""
    lines = list(block.lines)
    indent, trailing = _head_parts(lines[block.lead])
    open_, close = ("[[", "]]") if block.array else ("[", "]")
    name = ".".join(toml_splice.toml_key(part) for part in path)
    lines[block.lead] = indent + open_ + name + close + trailing
    return lines


# ── Legacy text to lanes text ────────────────────────────────────────────


def _refuse_inline_reviewers(old_path: str, root) -> None:
    # shortcut: inline-array rosters are refused, not migrated; migrate them when one is seen
    if any(span.key[:1] == ("reviewers",) for span in root.spans):
        raise LegacyRosterError(old_path, _REFUSED_INLINE)


def _entry_groups(old_path: str, blocks: list) -> list:
    """Each `[[reviewers]]` entry as the block indexes it spans: its own block, then the non-array
    blocks right after it under `reviewers` (its sub-tables)."""
    groups = []
    for index in range(1, len(blocks)):
        block = blocks[index]
        if block.path[:1] != ("reviewers",):
            continue
        if block.array and len(block.path) == 1:
            groups.append([index])
        elif not block.array and groups and groups[-1][-1] == index - 1:
            groups[-1].append(index)
        else:
            raise LegacyRosterError(old_path, _REFUSED_TABLES)
    return groups


def _root_lines(root, nl: str) -> list:
    """The root block with `[lanes]` placed before its first key, after the file-level comments;
    with no key, after the root's lines."""
    at = root.spans[0].start if root.spans else len(root.lines)
    return [*root.lines[:at], "[lanes]" + nl, *root.lines[at:]]


def _role_copy(blocks: list, members: list, role: str) -> list:
    lines = []
    for index in members:
        lines.extend(_with_head(blocks[index], ("lanes", role, *blocks[index].path[1:])))
    return lines


def _group_lines(blocks: list, members: list, entry: dict) -> list:
    """One reviewer entry, copied under each role its purpose names (D-24)."""
    review, execute = split_by_purpose([entry])
    lines = []
    if review:
        lines.extend(_role_copy(blocks, members, "review"))
    if execute:
        lines.extend(_role_copy(blocks, members, "execute"))
    return lines


def migrate_text(old_text: str, old_path: str = LEGACY_NAME) -> str:
    """The text of an old roster as a [lanes] table: root keys under `[lanes]`, each `[[reviewers]]`
    entry copied once per role it plays, and every other table renamed under `lanes.`."""
    text = _final_newline(old_text)
    entries = _parse_text(old_path, text).get("reviewers", [])
    try:
        blocks = toml_splice.split_blocks(text)
    except toml_splice.SpliceError as exc:
        raise LegacyRosterError(old_path, str(exc)) from exc
    _refuse_inline_reviewers(old_path, blocks[0])
    groups = _entry_groups(old_path, blocks)
    starts = {members[0]: number for number, members in enumerate(groups)}
    grouped = {index for members in groups for index in members}
    out = _root_lines(blocks[0], _newline(text))
    for index in range(1, len(blocks)):
        if index in starts:
            number = starts[index]
            out.extend(_group_lines(blocks, groups[number], entries[number]))
        elif index not in grouped:
            out.extend(_with_head(blocks[index], ("lanes", *blocks[index].path)))
    return "".join(out)


# ── Publishing the new config.toml ───────────────────────────────────────


def _joined(base_text: str, migrated: str) -> str:
    """The existing config.toml text kept byte for byte, one blank line, then the migrated lanes."""
    if not base_text:
        return migrated
    return _final_newline(base_text) + _newline(base_text) + migrated


def _check_new_text(old: str, new_text: str, base_doc: dict, expected: dict) -> None:
    if _parse_text(old, new_text) != {**base_doc, "lanes": expected}:
        raise LegacyRosterError(
            old, "migration check failed: the new file's values differ from the old file's")


def _publish(new_path: str, new_text: str) -> None:
    try:
        toml_splice.publish(new_path, new_text)
    except OSError as exc:
        raise LegacyRosterError(new_path, f"could not write ({exc})") from exc


def _changed_while(old: str, new_path: str) -> str:
    return (f"ai-kit-spec: {new_path} changed while {old} was migrating; the old file is kept "
            "and the next run finishes the migration")


def _new_wins(old: str, new_path: str) -> str:
    return (f"ai-kit-spec: {old} was not migrated: {new_path} already has a [lanes] table "
            "(the new roster wins; remove or rename the old file)")


def _publish_lanes(old: str, new_path: str, old_text: str, expected: dict, warn_fn) -> tuple:
    """Publish the lanes into config.toml, rebuilt from fresh bytes when the file changed (D-25).

    Returns (state, new_text): ("migrated", the published text), or ("completed", None),
    ("kept-new", None) or ("deferred", None).
    """
    for _attempt in range(_ATTEMPTS):
        base = _read_bytes(new_path) or b""
        base_text = _decode(new_path, base)
        base_doc = _parse_text(new_path, base_text)
        if "lanes" in base_doc:
            if base_doc["lanes"] == expected:
                return "completed", None
            warn_fn(_new_wins(old, new_path))
            return "kept-new", None
        new_text = _joined(base_text, migrate_text(old_text, old))
        _check_new_text(old, new_text, base_doc, expected)
        if (_read_bytes(new_path) or b"") == base:
            _publish(new_path, new_text)
            return "migrated", new_text
    warn_fn(_changed_while(old, new_path))
    return "deferred", None


def _published_intact(new_path: str, new_text: str) -> bool:
    """True while config.toml's [lanes] table is still the published one (C1-9). Only the table
    that trust covers is compared: another writer's change to a different table (the runner adding
    `[runner.retry]`) must not defer the migration and drop the carried trust (WR-04)."""
    now = _read_bytes(new_path) or b""
    return (_parse_text(new_path, _decode(new_path, now)).get("lanes")
            == _parse_text(new_path, new_text).get("lanes"))


def _carry_trust(old: str, new_path: str, raw: bytes, trust_dir: str, canonical) -> None:
    """Re-key a trusted old roster to the new file's canonical digest (D-11). Only the run that
    publishes carries trust (C1-10): a run cut off before this leaves the roster untrusted."""
    if canonical is None or not trust.is_trusted(legacy_trust_dir(trust_dir),
                                                  os.path.realpath(old), raw):
        return
    new_real = os.path.realpath(new_path)
    if not trust.is_trusted(trust_dir, new_real, canonical):
        trust.record_trust(trust_dir, new_real, canonical)


def _retired_name(old: str) -> str:
    target = old + MIGRATED_SUFFIX
    number = 0
    while os.path.exists(target):
        number += 1
        target = f"{old}{MIGRATED_SUFFIX}.{number}"
    return target


def _retire_old(old: str, new_path: str, raw: bytes, state: str, warn_fn) -> str:
    """Rename the old roster to `*.migrated` only while its bytes equal the snapshot (C1-6)."""
    now = _read_bytes(old)
    if now is None:
        return state
    if now != raw:
        warn_fn(f"ai-kit-spec: {old} changed during its migration to {new_path}; the old file is "
                "kept (the new roster wins; remove or rename the old file)")
        return "deferred"
    target = _retired_name(old)
    try:
        os.rename(old, target)
    except OSError as exc:
        warn_fn(f"ai-kit-spec: migrated {old} to {new_path} but could not rename the old file "
                f"({exc}); the next run finishes it")
        return state
    warn_fn(f"ai-kit-spec: migrated {old} to {new_path}; the old file is now {target}")
    return state


def migrate_layer(new_path: str, *, warn_fn, trust_dir: str | None = None,
                  trust_bytes_fn=None) -> str:
    """Migrate the old roster beside new_path into its config.toml; returns the status.

    "none": no old roster. "migrated": the lanes are published and the old file is renamed.
    "completed": config.toml already held the old roster's lanes; only the rename was left.
    "kept-new": config.toml holds other lanes, so the new roster wins and the old file is kept.
    "deferred": a concurrent write interrupted the run; the old file is kept.

    Trust is carried only by the run that publishes (`migrated`), never by `completed` (C1-10).
    With trust_dir and trust_bytes_fn (the project layer) a trusted old roster gets a record for
    the new file's realpath and canonical bytes; the user layer passes neither.
    """
    old = legacy_path(new_path)
    raw = _read_bytes(old)
    if raw is None:
        return "none"
    old_text = _decode(old, raw)
    expected = lanes_from_legacy(_parse_text(old, old_text))
    state, new_text = _publish_lanes(old, new_path, old_text, expected, warn_fn)
    if state in ("kept-new", "deferred"):
        return state
    if state == "migrated":
        if not _published_intact(new_path, new_text):
            warn_fn(_changed_while(old, new_path))
            return "deferred"
        if trust_dir is not None and trust_bytes_fn is not None:
            _carry_trust(old, new_path, raw, trust_dir, trust_bytes_fn(expected))
    return _retire_old(old, new_path, raw, state, warn_fn)
