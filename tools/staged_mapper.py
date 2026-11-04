#!/usr/bin/env python3
"""Map staged files to the test modules that cover them, through a name index.

The index is rebuilt on every call and never cached: it holds the source of every
tests/*.py file and, per test module, a reach text (its own source plus, transitively, the
source of each tests/ helper it names). A module covers a unit when its reach text names it.
This module only reads the tree and the staged list; it writes nothing, so commits in two
worktrees cannot interfere.

The staged list comes from `git diff --cached`, which compares the index with HEAD: a
`git commit --amend` maps only what is staged now, not the changes already in the commit being
amended, which ran at their own commit.

shortcut: a test that reaches files only through a glob or directory walk (skills/*/SKILL.md)
is not selected for them; the push stage's full suites cover it; upgrade if a commit-stage
miss is ever observed.
"""
import os
import re
import subprocess
from collections.abc import Collection, Mapping
from pathlib import Path, PurePosixPath
from typing import NamedTuple

NO_BOUND_BEFORE = r"(?<![\w-])"
NO_BOUND_AFTER = r"(?![\w-])"


class MapperError(Exception):
    """The index or the staged list could not be built; the caller runs more tests."""


class Index(NamedTuple):
    modules: tuple[str, ...]  # `tests.<stem>` of every tests/test_*.py, sorted
    reach: Mapping[str, str]  # module -> own source plus the helpers it names, transitively
    corpus: str  # every tests/*.py source, concatenated


class Decision(NamedTuple):
    modules: tuple[str, ...]  # every covering module, sorted (empty on a full run)
    by_path: Mapping[str, tuple[str, ...]]  # staged path -> its covering modules
    arch: bool  # a staged .py under skills/, tools/ or tests/: the arch group joins
    full_reason: str | None  # set: run the full unit and arch groups, and why


def _token(name: str) -> str:
    """Regex for `name` as a whole token: not glued to a letter, digit, `_` or `-`."""
    return f"{NO_BOUND_BEFORE}{re.escape(name)}{NO_BOUND_AFTER}"


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise MapperError(f"cannot read {path.name}: {type(exc).__name__}: {exc}") from exc


def _reach(source: str, helpers: Mapping[str, str]) -> str:
    """`source` plus, transitively, the source of every helper it names."""
    parts, named, todo = [source], set[str](), [source]
    while todo:
        text = todo.pop()
        for stem, body in helpers.items():
            if stem not in named and re.search(_token(stem), text):
                named.add(stem)
                parts.append(body)
                todo.append(body)
    return "\n".join(parts)


def build_index(root: Path) -> Index:
    """Read every root/tests/*.py; an unreadable or undecodable file raises MapperError."""
    tests = root / "tests"
    if not tests.is_dir():
        raise MapperError(f"no tests folder under {root.name}")
    sources = {path.stem: _read(path) for path in sorted(tests.glob("*.py"))}
    helpers = {stem: text for stem, text in sources.items() if not stem.startswith("test_")}
    modules = {stem: text for stem, text in sources.items() if stem.startswith("test_")}
    return Index(
        modules=tuple(f"tests.{stem}" for stem in modules),
        reach={f"tests.{stem}": _reach(text, helpers) for stem, text in modules.items()},
        corpus="\n".join(sources.values()),
    )


def _tool_forms(stem: str) -> tuple[str, ...]:
    """The code forms in which a test names the tool `stem`; a bare word is not one."""
    name, tok = re.escape(stem), _token(stem)
    names_in_list = r"\bfrom\s+tools(?:\.hooks)?\s+import\s+"
    return (
        f"{NO_BOUND_BEFORE}{name}\\.py",
        f"[\"']{name}[\"']",
        f"\\bimport\\s+{tok}",
        f"\\bfrom\\s+{tok}\\s+import\\b",
        f"{names_in_list}(?:[^\\n()]*?[\\s,])?{tok}",  # `from tools import a, b as c`
        f"{names_in_list}\\([^)]*?{tok}",  # `from tools import (a,\n    b)`
        f"(?<=\\w)\\.{name}{NO_BOUND_AFTER}",  # a dotted module path ending in `.<stem>`
    )


def unit_tokens(path: str) -> tuple[str, ...]:
    """Regexes (any one matching selects a module) for the unit a staged path belongs to."""
    parts = PurePosixPath(path).parts
    head, name = (parts[0], parts[-1]) if parts else ("", "")
    if head in ("", ".planning"):
        return ()
    if head == "skills" and len(parts) >= 3:
        return (_token(parts[1]),)
    if head == "tools" and name.endswith(".py") and (
        len(parts) == 2 or (len(parts) == 3 and parts[1] == "hooks")
    ):
        return _tool_forms(name.removesuffix(".py"))
    if head == "tests" and len(parts) == 2 and name.endswith(".py"):
        return (_token(name.removesuffix(".py")),)
    if head == "tests" and len(parts) >= 3 and parts[1] == "fixtures":
        folders = parts[2:-1]
        every_folder = "\\A" + "".join(f"(?=[\\s\\S]*?{_token(f)})" for f in folders)
        return (_token(name), *((every_folder,) if folders else ()))
    return (_token(name),)


def _is_test_module(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return (len(parts) == 2 and parts[0] == "tests"
            and parts[1].startswith("test_") and parts[1].endswith(".py"))


def covering_modules(index: Index, path: str) -> frozenset[str]:
    """The test modules whose reach text names the unit of `path`; a staged test module
    that still exists covers itself."""
    patterns = [re.compile(token) for token in unit_tokens(path)]
    found = {
        module for module, text in index.reach.items()
        if any(pattern.search(text) for pattern in patterns)
    }
    own = f"tests.{PurePosixPath(path).stem}"
    if _is_test_module(path) and own in index.reach:
        found.add(own)
    return frozenset(found)


def _is_shared(path: str, shared: Collection[str]) -> bool:
    """An exact entry of `shared`, or a path under an entry ending in `/`."""
    return path in shared or any(e.endswith("/") and path.startswith(e) for e in shared)


def _full(reason: str) -> Decision:
    return Decision(modules=(), by_path={}, arch=False, full_reason=reason)


def _named_in_corpus(index: Index, path: str) -> bool:
    return any(re.search(token, index.corpus) for token in unit_tokens(path))


def decide(root: Path, paths: Collection[str], shared: Collection[str]) -> Decision:
    """The covering modules of `paths`, or a full-run reason when they cannot be trusted.

    A full run is decided for: a path in `shared` (the runner's shared test machinery); a
    tests/ helper or fixture covering two or more modules (computed, so no second list can
    drift); a path the tests sources name but no module covers (an empty answer for a file the
    index says is covered). The paths are sorted and de-duplicated first and the shared pass
    runs before the index is built, so neither the order they were staged in nor the order of
    the triggers changes the decision. Raises MapperError when the index cannot be built.
    """
    ordered = sorted(set(paths))
    for path in ordered:
        if _is_shared(path, shared):
            return _full(f"shared test machinery: {path}")
    index = build_index(root)
    by_path: dict[str, tuple[str, ...]] = {}
    for path in ordered:
        covering = covering_modules(index, path)
        if path.startswith("tests/") and not _is_test_module(path) and len(covering) >= 2:
            return _full(f"shared test helper or fixture: {path} ({len(covering)} modules)")
        if not covering and _named_in_corpus(index, path):
            return _full(f"empty answer for covered file {path}")
        by_path[path] = tuple(sorted(covering))
    return Decision(
        modules=tuple(sorted({m for modules in by_path.values() for m in modules})),
        by_path=by_path,
        arch=any(_is_python_source(path) for path in ordered),
        full_reason=None,
    )


def _is_python_source(path: str) -> bool:
    return path.endswith(".py") and path.split("/", 1)[0] in ("skills", "tools", "tests")


def staged_paths(root: Path) -> list[str]:
    """The staged paths (deletions and both sides of a rename included), run as an argv list."""
    argv = ["git", "diff", "--cached", "--name-only", "-z", "--no-renames"]
    try:
        proc = subprocess.run(argv, cwd=root, capture_output=True, check=False)
    except OSError as exc:
        raise MapperError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        detail = proc.stderr.decode(errors="replace").strip()
        raise MapperError(f"git diff --cached failed: {detail}")
    return [os.fsdecode(raw) for raw in proc.stdout.split(b"\0") if raw]
