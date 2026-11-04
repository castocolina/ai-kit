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
miss is ever observed. A tool that another tool loads by path is selected only when the
loader's test names it.
"""
import argparse
import importlib.util
import os
import re
import statistics
import subprocess
import sys
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
    modules: tuple[str, ...]  # every covering module, sorted (empty when index_built is False)
    by_path: Mapping[str, tuple[str, ...]]  # staged path -> its covering modules
    arch: bool  # a staged .py under skills/, tools/ or tests/: the arch group joins
    full_reason: str | None  # set: run the full unit and arch groups, and why
    index_built: bool = True  # False: shared machinery and no index, so no covering set is known


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
        # a dotted module path ending in `.<stem>` or a helper `.<stem>` / `._<stem>` of its module
        f"(?<=\\w)\\._?{name}{NO_BOUND_AFTER}",
    )


# Skill folders whose bare name selected more than half of the unit and arch modules (40 of 79,
# measured 2026-11-04): their tests read them by path, so only path forms select them. Every other
# folder keeps the bare token: its tests name it in install lists and constants that do read it.
TIGHT_SKILL_FOLDERS = frozenset({"ai-kit-spec-review"})


def _skill_forms(folder: str) -> tuple[str, ...]:
    """The regexes that select a test naming the skill folder `folder`. A tight folder is selected
    by a code form that reads it: a path string (`skills/<name>`), a path join (`"skills", "<name>"`
    or `"skills" / "<name>"`) or a path relative to skills/ (`<name>/file`). A bare quoted name is a
    value there (the goal-prompt tests name a candidate skill that way), so it selects nothing.
    shortcut: a test that reads a tight skill through a variable holding only the bare name is not
    selected; the push stage's full suites cover it; upgrade if a commit-stage miss is observed."""
    if folder not in TIGHT_SKILL_FOLDERS:
        return (_token(folder),)
    name = re.escape(folder)
    return (
        f"skills/{name}{NO_BOUND_AFTER}",
        f"[\"']skills[\"']\\s*[,/]\\s*[\"']{name}[\"']",
        f"(?<![\\w/-]){name}/",
    )


def unit_tokens(path: str) -> tuple[str, ...]:
    """Regexes (any one matching selects a module) for the unit a staged path belongs to."""
    parts = PurePosixPath(path).parts
    head, name = (parts[0], parts[-1]) if parts else ("", "")
    if head in ("", ".planning"):
        return ()
    if head == "skills" and len(parts) >= 3:
        return _skill_forms(parts[1])
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


def _named_in_corpus(index: Index, path: str) -> bool:
    return any(re.search(token, index.corpus) for token in unit_tokens(path))


def decide(root: Path, paths: Collection[str], shared: Collection[str]) -> Decision:
    """The covering modules of `paths`, and a full-run reason when they cannot be trusted.

    A full run is decided for: a path in `shared` (the runner's shared test machinery); a
    tests/ helper or fixture covering two or more modules (computed, so no second list can
    drift); a path the tests sources name but no module covers (an empty answer for a file the
    index says is covered). The covering modules are computed for every path even on a full run,
    so the runner still knows which e2e modules cover the paths. The paths are sorted and
    de-duplicated, and shared machinery takes precedence over the other triggers, so neither the
    order they were staged in nor the order of the triggers changes the decision. Shared
    machinery with an unbuildable index keeps its reason with index_built False; any other index
    failure raises MapperError.
    """
    ordered = sorted(set(paths))
    arch = any(_is_python_source(path) for path in ordered)
    shared_path = next((path for path in ordered if _is_shared(path, shared)), None)
    try:
        index = build_index(root)
    except MapperError:
        if shared_path is None:
            raise
        return Decision((), {}, arch, f"shared test machinery: {shared_path}", index_built=False)
    reason = f"shared test machinery: {shared_path}" if shared_path is not None else None
    by_path: dict[str, tuple[str, ...]] = {}
    for path in ordered:
        covering = covering_modules(index, path)
        if reason is None and path.startswith("tests/") and not _is_test_module(path) \
                and len(covering) >= 2:
            reason = f"shared test helper or fixture: {path} ({len(covering)} modules)"
        if reason is None and not covering and _named_in_corpus(index, path):
            reason = f"empty answer for covered file {path}"
        by_path[path] = tuple(sorted(covering))
    return Decision(
        modules=tuple(sorted({m for modules in by_path.values() for m in modules})),
        by_path=by_path,
        arch=arch,
        full_reason=reason,
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


def _git(root: Path, argv: list[str], refs: tuple[str, ...]) -> bytes:
    """Stdout of a git argv list run in root. A ref starting with `-` is refused before git runs."""
    for ref in refs:
        if ref.startswith("-"):
            raise MapperError(f"refusing ref {ref!r}: it starts with '-'")
    try:
        proc = subprocess.run(argv, cwd=root, capture_output=True, check=False)
    except OSError as exc:
        raise MapperError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        detail = proc.stderr.decode(errors="replace").strip()
        raise MapperError(f"git {argv[1]} failed: {detail}")
    return proc.stdout


def commit_sha(root: Path, ref: str) -> str:
    """The full sha that `ref` names as a commit."""
    argv = ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"]
    return _git(root, argv, (ref,)).decode().strip()


def pushed_paths(root: Path, from_ref: str, to_ref: str) -> list[str]:
    """The paths changed from `from_ref` to `to_ref`, three dots as pre-commit diffs a push."""
    argv = ["git", "diff", "--name-only", "-z", "--no-renames", f"{from_ref}...{to_ref}"]
    return [os.fsdecode(raw) for raw in _git(root, argv, (from_ref, to_ref)).split(b"\0") if raw]


def outside_commits(root: Path, to_ref: str) -> list[str]:
    """The commits a local branch or a worktree HEAD holds, no remote-tracking ref holds, and
    `to_ref`'s history does not hold. Tags and the stash are left out: an unpushed tag or backup
    branch is not a ref a push carries, and counting its commits would defeat the proof."""
    argv = ["git", "rev-list", "--exclude=refs/stash", "--exclude=refs/tags/*", "--all",
            "--not", "--remotes", to_ref]
    return _git(root, argv, (to_ref,)).decode().split()


DEFAULT_ROOT = Path(__file__).resolve().parent.parent
# Tracked files under these folders are units or planning files, not data files.
UNIT_DIRS = ("skills", "tools", "tests", ".planning")
DATA_FILE_LIMIT = 5


class UnitStats(NamedTuple):
    unit_count: int  # every skills/<name>/ folder, tools/*.py and tools/hooks/*.py file
    median_all: float  # covering-module count per unit, uncovered units counted as 0
    median_covered: float  # the same over covered units only
    max_count: int
    max_unit: str  # the first unit, in sorted order, that holds max_count
    uncovered: tuple[str, ...]  # units no test module names
    e2e_sets: int  # units whose covering set holds an e2e module
    top_data_files: tuple[tuple[str, int], ...]  # tracked non-unit files that select most modules


def units(root: Path) -> list[tuple[str, str]]:
    """(unit label, a path the mapper resolves to that unit), sorted: skill folders, then tools."""
    found: list[tuple[str, str]] = []
    skills = root / "skills"
    if skills.is_dir():
        for folder in sorted(skills.iterdir()):
            if folder.is_dir():
                found.append((f"skills/{folder.name}", f"skills/{folder.name}/SKILL.md"))
    tools = root / "tools"
    if tools.is_dir():
        for path in sorted(tools.glob("*.py")) + sorted((tools / "hooks").glob("*.py")):
            label = f"tools/{path.relative_to(tools).as_posix()}"
            found.append((label, label))
    return found


def unit_stats(index: Index, root: Path, tracked: Collection[str],
               e2e: Collection[str]) -> UnitStats:
    """The selectivity of the mapper over the checkout's units and its tracked data files."""
    per_unit = [(label, covering_modules(index, path)) for label, path in units(root)]
    counts = [len(covering) for _label, covering in per_unit]
    covered = [count for count in counts if count > 0]
    top_label, top = max(per_unit, key=lambda item: len(item[1]), default=("", frozenset()))
    e2e_names = set(e2e)
    candidates = [path for path in tracked if path.split("/", 1)[0] not in UNIT_DIRS]
    ranked = sorted(((path, len(covering_modules(index, path))) for path in candidates),
                    key=lambda item: (-item[1], item[0]))
    return UnitStats(
        unit_count=len(per_unit),
        median_all=statistics.median(counts) if counts else 0,
        median_covered=statistics.median(covered) if covered else 0,
        max_count=len(top),
        max_unit=top_label,
        uncovered=tuple(label for label, covering in per_unit if not covering),
        e2e_sets=sum(1 for _label, covering in per_unit if covering & e2e_names),
        top_data_files=tuple(ranked[:DATA_FILE_LIMIT]),
    )


def tracked_paths(root: Path) -> list[str]:
    """The git-tracked paths of root, run as an argv list."""
    argv = ["git", "ls-files", "-z"]
    try:
        proc = subprocess.run(argv, cwd=root, capture_output=True, check=False)
    except OSError as exc:
        raise MapperError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        raise MapperError(f"git ls-files failed: {proc.stderr.decode(errors='replace').strip()}")
    return [os.fsdecode(raw) for raw in proc.stdout.split(b"\0") if raw]


def _runner_tables() -> tuple[frozenset[str], frozenset[str]]:
    """(E2E_MODULES, SHARED_MACHINERY) from the runner, which owns them. The runner is loaded by
    path, as the runner loads this module, so this module never imports the runner by name."""
    path = Path(__file__).resolve().with_name("run_unittest_parallel.py")
    spec = importlib.util.spec_from_file_location("run_unittest_parallel", path)
    if spec is None or spec.loader is None:
        raise MapperError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.E2E_MODULES, module.SHARED_MACHINERY


def _print_stats(index: Index, root: Path, e2e: frozenset[str]) -> None:
    stats = unit_stats(index, root, tracked_paths(root), e2e)
    print(f"mapper: {stats.unit_count} units; covering modules per unit: "
          f"median {stats.median_all:g} (all units), median {stats.median_covered:g} "
          f"(covered units), max {stats.max_count} ({stats.max_unit}); "
          f"{stats.e2e_sets} covering sets hold an e2e module")
    for unit in stats.uncovered:
        print(f"mapper: uncovered unit {unit}")
    for path, count in stats.top_data_files:
        print(f"mapper: data file {path}: {count} modules")


def main(argv: list[str] | None = None) -> int:
    """`--stats` prints the mapper's selectivity over the checkout; positional paths print the
    decision for those paths without running a test. Exit 0; 2 on a usage error; 1 on a mapper
    error, which is printed."""
    parser = argparse.ArgumentParser(description="Map staged paths to covering test modules.")
    parser.add_argument("--stats", action="store_true", help="print the selectivity report")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="checkout to map")
    parser.add_argument("paths", nargs="*", help="staged paths to decide, without running a test")
    args = parser.parse_args(argv)
    if not args.stats and not args.paths:
        parser.print_usage(sys.stderr)
        return 2
    root = args.root.resolve()
    try:
        e2e, shared = _runner_tables()
        if args.stats:
            _print_stats(build_index(root), root, e2e)
            return 0
        decision = decide(root, args.paths, shared)
    except MapperError as exc:
        print(f"mapper error: {exc}")
        return 1
    if decision.full_reason is not None:
        print(f"full run: {decision.full_reason}")
    print(f"modules: {' '.join(decision.modules)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
