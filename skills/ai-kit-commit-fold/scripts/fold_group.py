"""Rule-based feature grouping for the fold engine (D-06, D-08, D-09).

Each commit joins the checkpoint candidate whose files it touches most. A commit that matches no
candidate joins the feature already holding one of its paths, else the nearest earlier commit's
feature. Features that share a changed path, or hold a code file and its test_<stem>.py, merge
into one feature, and the report says why. Docs paths and changed paths that no feature claims
go to the last feature.
"""

import dataclasses
import itertools
import posixpath

# shortcut: no import analysis, so a feature that depends on a file a later feature adds is not
# merged with it and its intermediate commit is not proven to build; upgrade with import-aware
# grouping (the folding policy states this limit)


@dataclasses.dataclass(frozen=True)
class Feature:
    ids: tuple[str, ...]
    title: str
    commits: tuple[str, ...]
    paths: frozenset[str]


@dataclasses.dataclass(frozen=True)
class _Group:
    """A candidate's commits (by index) and changed code paths, before its feature is built."""

    ids: tuple[str, ...]
    titles: tuple[str, ...]
    members: tuple[int, ...]
    paths: frozenset[str]


def _is_docs(path, docs_paths):
    return any(path.startswith(prefix) for prefix in docs_paths)


def _is_code(path):
    return path.endswith(".py") and not path.startswith("tests/")


def _test_name(path):
    return f"test_{posixpath.splitext(posixpath.basename(path))[0]}.py"


def _code_paths(commit, cp):
    return [path for path in commit.paths if not _is_docs(path, cp.docs_paths)]


def _pick(commit, cp):
    """Index of the candidate the commit's non-docs paths hit most (ties go to the lower index)."""
    code = _code_paths(commit, cp)
    best, best_hits = None, 0
    for index, candidate in enumerate(cp.candidates):
        files = frozenset(candidate.files)
        hits = sum(1 for path in code if path in files)
        if hits > best_hits:
            best, best_hits = index, hits
    return best


def _keys(commits, cp):
    """Candidate index per commit. Unmatched and docs-only commits take the feature holding one
    of their paths, else the nearest earlier commit's feature."""
    picks = [_pick(commit, cp) for commit in commits]
    holder = {}
    for commit, key in zip(commits, picks, strict=True):
        if key is not None:
            for path in _code_paths(commit, cp):
                holder.setdefault(path, key)
    keys, current = [], None
    for commit, key in zip(commits, picks, strict=True):
        if key is None:
            held = (holder[path] for path in _code_paths(commit, cp) if path in holder)
            key = next(held, current)
        if key is not None:
            current = key
        keys.append(key)
    first = next((key for key in keys if key is not None), None)
    return [first if key is None else key for key in keys]


def _identity(cp, key):
    if key is None:
        return (), (cp.unit,)
    candidate = cp.candidates[key]
    return (candidate.id,), (candidate.title,)


def _groups(cp, commits, keys, code_changed):
    """One group per candidate key, in first-appearance order."""
    members = {}
    for index, key in enumerate(keys):
        members.setdefault(key, []).append(index)
    groups = []
    for key, indexes in members.items():
        ids, titles = _identity(cp, key)
        paths = frozenset(path for index in indexes for path in commits[index].paths
                          if path in code_changed)
        groups.append(_Group(ids, titles, tuple(indexes), paths))
    return groups


def _pair_reason(first, second):
    """Why two groups must stay whole in one commit, or None."""
    shared = sorted(first.paths & second.paths)
    if shared:
        return f"shared {shared[0]}"
    for left, right in ((first, second), (second, first)):
        names = {posixpath.basename(path) for path in right.paths}
        for path in sorted(left.paths):
            if _is_code(path) and _test_name(path) in names:
                return f"{path} with its test"
    return None


def _join(left, right):
    return _Group(left.ids + right.ids, left.titles + right.titles,
                  tuple(sorted(left.members + right.members)), left.paths | right.paths)


def _merge(groups):
    """Merge groups until none shares a path or a code file with its test. Returns notes."""
    notes = []
    merged = True
    while merged:
        merged = False
        for i, j in itertools.combinations(range(len(groups)), 2):
            reason = _pair_reason(groups[i], groups[j])
            if reason:
                notes.append(f"merged {'+'.join(groups[i].ids + groups[j].ids)}: {reason}")
                groups[i] = _join(groups[i], groups[j])
                del groups[j]
                merged = True
                break
    return groups, notes


def _features(commits, groups, extra):
    """Feature objects in first-commit order; the extra paths go to the last feature."""
    ordered = sorted(groups, key=lambda group: group.members[0])
    features = []
    for position, group in enumerate(ordered):
        owned = group.paths | extra if position == len(ordered) - 1 else group.paths
        features.append(Feature(group.ids, "; ".join(group.titles),
                                tuple(commits[index].sha for index in group.members),
                                frozenset(owned)))
    return features


def rule_features(commits, cp, changed):
    """Group commits into features by candidate. Returns (features, "rules", note)."""
    docs = frozenset(path for path in changed if _is_docs(path, cp.docs_paths))
    code_changed = changed - docs
    keys = _keys(commits, cp)
    groups, notes = _merge(_groups(cp, commits, keys, code_changed))
    loose = code_changed - set().union(*(group.paths for group in groups))
    if all(key is None for key in keys):
        notes.append("no candidate matched; one feature")
    return _features(commits, groups, docs | loose), "rules", "; ".join(notes)


def group_features(commits, cp, changed):
    """The one grouping seam fold.py calls. Plan 29-10 asks jev here before the rules."""
    return rule_features(commits, cp, changed)
