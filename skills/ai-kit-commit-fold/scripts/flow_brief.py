"""The unit brief: a plain file the next agents read; it only says which documents mention a name.

The brief names the previous unit's range and changed files, tells each agent to explore the
changed code with codebase-memory-mcp, and lists the tracked documents that mention the changed
names. A listed document only mentions a name; the brief never claims that a document explains a
symbol.
"""

import json
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
MAX_QUERY_ROWS = 2000
# codebase-memory-mcp caps list_projects --limit at 500 (0.12.1); page with --offset
PROJECT_PAGE = 500
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
    "Explore the changed code files above with codebase-memory-mcp: `search_graph` and "
    "`trace_path` for their symbols and callers, `get_code_snippet` for source (the MCP tools, "
    "or `codebase-memory-mcp cli <tool> --flag value` in a shell). If `list_projects` shows no "
    "project for this checkout, run `index_repository` on it first."
)
_NO_CODE = ("No code file changed in this range (documents or config only), "
            "so there is nothing to explore.")
_MENTION_NOTE = ("A listed document only mentions a name; confirm what it says about the symbol "
                 "with `search_graph` or `get_code_snippet`, or by reading it.")
_STATUS = {"A": "added", "M": "modified", "D": "removed", "T": "modified"}
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


def cypher_quote(path):
    """A Cypher single-quoted literal: each backslash doubled first, then each quote escaped."""
    return "'" + path.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _cbm_project(top, run):
    """The project name whose root is this checkout, paging `list_projects`; None when absent."""
    want = os.path.realpath(top)
    offset = 0
    while True:
        rc, out, _ = run([flow_index.CBM, "cli", "list_projects", "--format", "json",
                          "--limit", str(PROJECT_PAGE), "--offset", str(offset)], top)
        if rc != 0:
            return None
        try:
            data = json.loads(out)
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        projects = data.get("projects")
        rows = ([row for row in projects if isinstance(row, dict)]
                if isinstance(projects, list) else [])
        for row in rows:
            if row.get("root_path") == want and isinstance(row.get("name"), str):
                return row["name"]
        if not data.get("has_more") or not rows:
            return None  # a page with has_more and no rows would loop forever
        offset += len(rows)


def _query_pages(top, run, project, query):
    """(rows, total, more, error) from `query_graph` pages up to MAX_QUERY_ROWS rows.

    The tool cuts a page at an output budget far below --max-rows, so page with the reported
    `next_offset`. `error` is a label when the first page is unusable; a later bad page just
    leaves `more` true.
    """
    rows, total, offset = [], None, 0
    while True:
        rc, out, _ = run([flow_index.CBM, "cli", "query_graph", "--project", project,
                          "--format", "json", "--max-rows", str(MAX_QUERY_ROWS),
                          "--offset", str(offset), "--query", query], top)
        first = offset == 0
        if rc != 0:
            return rows, total, not first, (
                f"file names only: codebase-memory-mcp query_graph failed, exit {rc}"
                if first else None)
        try:
            data = json.loads(out)
        except ValueError:
            data = None
        if not isinstance(data, dict):
            return rows, total, not first, (
                "file names only: codebase-memory-mcp query_graph output unreadable"
                if first else None)
        page = data.get("rows")
        page = page if isinstance(page, list) else []
        rows += page
        total = data.get("total", total)
        if not (data.get("has_more") or data.get("truncated")) or not page:
            return rows, total, False, None
        if len(rows) >= MAX_QUERY_ROWS:
            return rows, total, True, None
        next_offset = data.get("next_offset")
        offset = next_offset if isinstance(next_offset, int) and next_offset > offset \
            else offset + len(page)


def _query_names(rows, total, more):
    """(names, label) from the collected rows: the name column of each row."""
    names = {row[1] for row in rows
             if isinstance(row, list) and len(row) > 1 and isinstance(row[1], str)}
    if not names:
        return [], "file names only: codebase-memory-mcp listed no names"
    if more:
        return sorted(names), (f"symbol names from codebase-memory-mcp, partial: {len(rows)} of "
                               f"{total if total is not None else 'more'} rows; plus file names")
    return sorted(names), "symbol names from codebase-memory-mcp plus file names"


def explore_names(top, code_paths, run, which):
    """(symbol names, label): functions, methods and classes of `code_paths` in the index."""
    if not code_paths:
        return [], "file names only: no code file changed in this range"
    if which(flow_index.CBM) is None:
        return [], "file names only: the codebase-memory-mcp CLI is not installed"
    project = _cbm_project(top, run)
    if project is None:
        return [], "file names only: no codebase-memory-mcp index for this checkout"
    in_list = ", ".join(cypher_quote(path) for path in code_paths)
    query = (f"MATCH (f) WHERE f.file_path IN [{in_list}] AND "
             "(f:Function OR f:Method OR f:Class) RETURN f.file_path, f.name")
    rows, total, more, error = _query_pages(top, run, project, query)
    if error:
        return [], error
    return _query_names(rows, total, more)


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
