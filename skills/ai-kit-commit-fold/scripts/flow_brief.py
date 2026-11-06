"""The unit brief: a plain file the next agents read; it only says which documents mention a name.

The brief names the previous unit's range and changed files, tells each agent to explore the
changed code with codegraph, and lists the tracked documents that mention the changed names. A
listed document only mentions a name; the brief never claims that a document explains a symbol.
"""

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import flow_git
import flow_index
from flow_record import FlowError

BRIEF_REL = Path(".aikit") / "brief" / "SKILL.md"
MENTION_CAP = 10
MAX_EXPLORE_FILES = 50  # shortcut: explore gets at most 50 code files; raise it when units grow
CODE_SUFFIXES = (".py", ".js", ".cjs", ".mjs", ".ts", ".tsx", ".jsx", ".sh", ".go", ".rs", ".java",
                 ".kt", ".rb", ".c", ".h", ".cpp", ".cs", ".swift", ".php")
DOC_SUFFIXES = (".md", ".mdx", ".rst", ".txt")
_READ_NOTE = (
    "Read this after the phase SPEC and CONTEXT: locked decisions win over these hints. "
    "It belongs to the unit named on the unit: line; if that is not your unit, say the brief "
    "belongs to another unit and ignore it. If the unit: line says next, this brief is for you "
    "when you are writing the next unit's plan."
)
_EXPLORE = (
    "Run `codegraph_explore` (or `codegraph explore \"<files>\"` in a shell) on the changed code "
    "files above for their symbols, callers and blast radius. If the index is missing or stale, "
    "run `codegraph init -y` or `codegraph sync` first."
)
_NO_CODE = ("No code file changed in this range (documents or config only), "
            "so there is nothing to explore.")
_MENTION_NOTE = ("A listed document only mentions a name; confirm what it says about the symbol "
                 "with `codegraph_explore` or by reading it.")
_STATUS = {"A": "added", "M": "modified", "D": "removed", "T": "modified"}
_HEADER = re.compile(r"^\*\*`([^`]+)`\*\* — (.*)$")
_ITEM = re.compile(r"^([A-Za-z_$][\w$.]*)(?:\(([a-z_]+)\))?$")
_MORE = re.compile(r"^\+(\d+) more$")
NO_BRIEF = (
    "# Unit brief\n"
    "\n"
    "no brief: no boundary step has written a brief in this checkout yet. Say that no brief was "
    "found and continue; run fold.py boundary, or ask the orchestrator, to write one.\n"
)


@dataclass(frozen=True)
class BriefFacts:  # pylint: disable=too-many-instance-attributes  # one field per brief fact
    """Everything `render` needs; built by flow_boundary.boundary."""

    unit: str
    branch: str
    head: str
    point: str
    written: str
    base_branch: str = ""
    previous: str | None = None
    previous_branch: str = ""
    unit_range: tuple[str, str] | None = None
    changed: tuple = ()
    names: tuple[str, ...] = ()
    names_label: str = ""
    mentions: dict[str, list[str]] = field(default_factory=dict)


def _decode(raw):
    return raw.decode("utf-8", "surrogateescape")


def is_code(path):
    """A code file outside `.planning/` (the explore and mention rules use this)."""
    return path.endswith(CODE_SUFFIXES) and not path.startswith(".planning/")


def changed_files(top, base, end):
    """(status, path, old_path) of `git diff --name-status -M -z base end`, sorted by path."""
    proc = subprocess.run(["git", "-C", str(top), "diff", "--name-status", "-M", "-z", base, end],
                          capture_output=True, check=False)
    if proc.returncode != 0:
        raise FlowError("git_error", f"git diff {base[:12]}..{end[:12]} failed")
    tokens = [token for token in proc.stdout.split(b"\0") if token]
    entries, index = [], 0
    while index < len(tokens):
        status = _decode(tokens[index])[:1]
        if status in ("R", "C"):
            old, new = _decode(tokens[index + 1]), _decode(tokens[index + 2])
            index += 3
            entries.append(("R", new, old) if status == "R" else ("A", new, None))
        else:
            entries.append((_STATUS.get(status, status), _decode(tokens[index + 1]), None))
            index += 2
    return sorted(entries, key=lambda entry: entry[1])


def explore_names(top, code_paths, run, which):
    """(symbol names, label) from one `codegraph explore` call over `code_paths`."""
    if not code_paths:
        return [], "file names only: no code file changed in this range"
    if which("codegraph") is None:
        return [], "file names only: the codegraph CLI is not installed"
    rc, out, _err = run(["codegraph", "explore", " ".join(code_paths)], top)
    if rc != 0:
        return [], f"file names only: codegraph explore failed, exit {rc}"
    names, dropped = set(), 0
    for line in out.splitlines():
        header = _HEADER.match(line)
        if not header:
            continue
        for item in header.group(2).split(", "):
            more = _MORE.match(item)
            if more:
                dropped += int(more.group(1))
                continue
            found = _ITEM.match(item)
            if found:
                names.add(found.group(1))
    if not names:
        return [], "file names only: codegraph explore listed no names"
    if dropped:
        return sorted(names), (f"symbol names from `codegraph explore`, partial: {dropped} more "
                               "not listed by codegraph; plus file names")
    return sorted(names), "symbol names from `codegraph explore` plus file names"


def mentions(top, names):
    """Each name -> the sorted tracked documents outside `.planning/` that hold it whole-word."""
    found = {name: [] for name in names}
    if not names:
        return found
    patterns = {name: re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")
                for name in names}
    listing = subprocess.run(["git", "-C", str(top), "ls-files", "-z"],
                             capture_output=True, check=False)
    for raw in listing.stdout.split(b"\0"):
        rel = _decode(raw)
        if not rel or not rel.endswith(DOC_SUFFIXES) or rel.startswith(".planning/"):
            continue
        try:
            text = (Path(top) / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name, pattern in patterns.items():
            if pattern.search(text):
                found[name].append(rel)
    return {name: sorted(paths) for name, paths in found.items()}


def search(top, changed, run, which):
    """(names, label, mentions) for the changed files: explore and file names, then mentions."""
    code = [path for _status, path, _old in changed
            if is_code(path) and (Path(top) / path).is_file()][:MAX_EXPLORE_FILES]
    explored, label = explore_names(top, code, run, which)
    file_names = {os.path.basename(path) for _status, path, _old in changed}
    file_names |= {os.path.basename(old) for _status, _path, old in changed if old}
    names = tuple(sorted(set(explored) | file_names))
    return names, label, mentions(top, names)


def _change_line(entry):
    status, path, old = entry
    if status == "R":
        return f"- renamed `{old}` -> `{path}`"
    return f"- {_STATUS.get(status, status)} `{path}`"


def _explore_text(facts):
    if any(is_code(path) for _status, path, _old in facts.changed):
        return _EXPLORE
    return _NO_CODE


def _names_line(facts):
    label = facts.names_label or "file names only"
    listed = ", ".join(f"`{name}`" for name in facts.names) or "none"
    return f"Names searched ({label}): {listed}"


def _mention_lines(facts):
    hits = [(name, paths) for name, paths in sorted(facts.mentions.items()) if paths]
    if not hits:
        return ["No tracked document outside `.planning/` mentions them."]
    lines = []
    for name, paths in hits:
        if len(paths) > MENTION_CAP:
            shown = ", ".join(f"`{path}`" for path in paths[:MENTION_CAP])
            lines.append(f"- `{name}`: in {len(paths)} documents; first {MENTION_CAP}: {shown}")
        else:
            lines.append(f"- `{name}`: " + ", ".join(f"`{path}`" for path in paths))
    return lines


def render(facts):
    """The brief text: stamp lines, read-order note, previous unit, files, explore, mentions."""
    lines = [
        "# Unit brief",
        "",
        f"unit: {facts.unit}",
        f"branch: {facts.branch}",
        f"head: {facts.head}",
        f"point: {facts.point}",
        f"written: {facts.written}",
        "",
        _READ_NOTE,
        "",
        "## Previous unit",
    ]
    if facts.previous is None:
        lines.append(f"No previous unit: this is the first unit on `{facts.base_branch}`.")
    elif facts.unit_range is None:
        lines.append(f"Previous unit {facts.previous}: range unknown "
                     "(its branch and pushed tip are gone).")
    else:
        start, end = facts.unit_range
        lines.append(f"Previous unit {facts.previous} (`{facts.previous_branch}`), "
                     f"range `{start[:12]}..{end[:12]}`.")
    lines += ["", "## Changed files"]
    lines += [_change_line(entry) for entry in facts.changed] or ["No file changed in this range."]
    lines += ["", "## Explore", _explore_text(facts), "", "## Documents that mention them"]
    lines += [_names_line(facts), _MENTION_NOTE, *_mention_lines(facts)]
    return "\n".join(lines) + "\n"


def write_brief(top, text):
    """Replace the brief atomically: a temporary file in the same folder, then os.replace."""
    path = Path(top) / BRIEF_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    # copied from flow_record._atomic_write_json; text variant
    fd, temp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise
    return path


def ensure_brief(top):
    """Write the no-brief file only when the brief is missing."""
    if not (Path(top) / BRIEF_REL).is_file():
        write_brief(top, NO_BRIEF)


def _worktrees(top):
    """Each `git worktree list --porcelain -z` record as a dict of its fields."""
    proc = subprocess.run(["git", "-C", str(top), "worktree", "list", "--porcelain", "-z"],
                          capture_output=True, check=False)
    records, current = [], {}
    for token in proc.stdout.split(b"\0"):
        if not token:
            if current:
                records.append(current)
                current = {}
            continue
        key, _sep, value = _decode(token).partition(" ")
        current[key] = value
    if current:
        records.append(current)
    return records


def seed_worktree(top):
    """Give a checkout its brief before the index job: a copy from a worktree at the same HEAD."""
    head = flow_git.rev(top, "HEAD") or ""
    notes = flow_index.ensure_excluded(top, [".aikit"])
    own = os.path.realpath(top)
    sources = []
    for record in _worktrees(top):
        path = record.get("worktree", "")
        candidate = Path(path) / BRIEF_REL
        if path and os.path.realpath(path) != own and record.get("HEAD") == head \
                and candidate.is_file():
            sources.append(candidate)
    if sources:
        newest = max(sources, key=lambda source: source.stat().st_mtime)
        write_brief(top, newest.read_text(encoding="utf-8", errors="replace"))
        notes.append(f"brief: copied from {newest.parents[2]}")
    else:
        ensure_brief(top)
        notes.append(f"brief: none at {head[:12]}; wrote the no-brief file")
    return notes


# registers the brief seeding hook; re-importing this module replaces the entry, never duplicates it
flow_index.SEED_HOOKS[:] = [hook for hook in flow_index.SEED_HOOKS
                            if getattr(hook, "__module__", "") != __name__]
flow_index.SEED_HOOKS.append(seed_worktree)
