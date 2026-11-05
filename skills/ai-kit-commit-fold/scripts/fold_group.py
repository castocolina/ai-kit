"""Rule-based feature grouping for the fold engine (D-06, D-08).

Each commit joins the checkpoint candidate whose files it touches most. Docs paths and changed
paths that no feature claims go to the last feature. A candidate that matches no commit makes no
feature. Merging features that share a path belongs to plan 29-06.
"""

import dataclasses


@dataclasses.dataclass(frozen=True)
class Feature:
    ids: tuple[str, ...]
    title: str
    commits: tuple[str, ...]
    paths: frozenset[str]


def _is_docs(path, docs_paths):
    return any(path.startswith(prefix) for prefix in docs_paths)


def _pick(commit, cp):
    """Index of the candidate the commit's non-docs paths hit most (ties go to the lower index)."""
    code = [path for path in commit.paths if not _is_docs(path, cp.docs_paths)]
    best, best_hits = None, 0
    for index, candidate in enumerate(cp.candidates):
        files = frozenset(candidate.files)
        hits = sum(1 for path in code if path in files)
        if hits > best_hits:
            best, best_hits = index, hits
    return best


def _keys(commits, cp):
    """Candidate index per commit. Unmatched and docs-only commits take the nearest earlier key."""
    keys, current = [], None
    for commit in commits:
        key = _pick(commit, cp)
        if key is not None:
            current = key
        keys.append(current)
    first = next((key for key in keys if key is not None), None)
    return [first if key is None else key for key in keys]


def _identity(cp, key):
    if key is None:
        return (), cp.unit
    candidate = cp.candidates[key]
    return (candidate.id,), candidate.title


def _rows(commits, keys, code_changed):
    """(key, members, paths) per feature, in first-commit order."""
    order, groups = [], {}
    for commit, key in zip(commits, keys, strict=True):
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(commit)
    return [(key, groups[key],
             {path for commit in groups[key] for path in commit.paths if path in code_changed})
            for key in order]


def _features(cp, rows, extra):
    """Feature objects; the extra paths (docs and unclaimed changes) go to the last feature."""
    features = []
    for position, (key, members, paths) in enumerate(rows):
        ids, title = _identity(cp, key)
        owned = paths | extra if position == len(rows) - 1 else paths
        features.append(Feature(ids, title, tuple(member.sha for member in members),
                                frozenset(owned)))
    return features


def rule_features(commits, cp, changed):
    """Group commits into features by candidate. Returns (features, "rules", note)."""
    keys = _keys(commits, cp)
    docs = frozenset(path for path in changed if _is_docs(path, cp.docs_paths))
    rows = _rows(commits, keys, changed - docs)
    # shortcut: a path two features both claim is staged in both commits (no shared-path merge
    # yet); upgrade with plan 29-06's grouping rules
    loose = (changed - docs) - set().union(*(paths for _key, _members, paths in rows))
    features = _features(cp, rows, docs | loose)
    note = "" if any(key is not None for key in keys) else "no candidate matched; one feature"
    return features, "rules", note


def group_features(commits, cp, changed):
    """The one grouping seam fold.py calls. Plan 29-10 asks jev here before the rules."""
    return rule_features(commits, cp, changed)
