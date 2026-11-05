"""Feature grouping for the fold engine: jev proposes, the rules decide (D-06..D-09, D-07, D-13).

jev-fast-decision's ladder entry point is asked once per commit, one `choice` item each: the
candidate ids are the options, and the item carries only the commit subject, the path names
and the candidate titles. A jev grouping is used only when every commit has an answer and no
code file lands in a feature other than its test's. Otherwise the rules decide: each commit
joins the checkpoint candidate whose files it touches most. A commit that matches no candidate
joins the feature already holding one of its paths, else the nearest earlier commit's feature.
Features that share a changed path, or hold a code file and its test_<stem>.py, merge into one
feature, and the report says why. Docs paths and changed paths that no feature claims go to the
last feature.
"""

import dataclasses
import itertools
import json
import os
import posixpath
import subprocess
import sys

# shortcut: no import analysis, so a feature that depends on a file a later feature adds is not
# merged with it and its intermediate commit is not proven to build; upgrade with import-aware
# grouping (the folding policy states this limit)

# The client's entry point, relative to a skills root: the lookup's last step, per root.
JEV_ENTRY_REL = os.path.join("jev-fast-decision", "scripts", "jev_review.py")
# A lookup copy of jev_ladder.py's SKILLS_ROOTS (same values; a test compares the parsed tuples).
SKILLS_ROOTS = (
    ("CLAUDE_CONFIG_DIR", ".claude", "skills"),
    (None, ".agents", "skills"),
    ("XDG_CONFIG_HOME", ".config", "opencode/skills"),
    ("CURSOR_CONFIG_DIR", ".cursor", "skills"),
    ("PI_CODING_AGENT_DIR", ".pi/agent", "skills"),
)
JEV_QUESTION = ("Which feature does this commit belong to? "
                "Pick the feature whose files and purpose the commit changes.")
JEV_CONTEXT_CHARS = 1400
JEV_TITLE_CHARS = 200
JEV_TIMEOUT_SECONDS = 40
OLD_CLIENT_NOTE = ("jev: entry point missing; update jev-fast-decision "
                   "(re-run the ai-kit installer)")


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


def _keys(commits, cp, picks=None):
    """Candidate index per commit. Unmatched and docs-only commits take the feature holding one
    of their paths, else the nearest earlier commit's feature. `picks` replaces the rule picks."""
    if picks is None:
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


def _assemble(commits, cp, changed, keys):
    """Features from per-commit candidate keys, merged by the shared-path and test rules.
    Returns (features, note)."""
    docs = frozenset(path for path in changed if _is_docs(path, cp.docs_paths))
    code_changed = changed - docs
    groups, notes = _merge(_groups(cp, commits, keys, code_changed))
    loose = code_changed - set().union(*(group.paths for group in groups))
    if all(key is None for key in keys):
        notes.append("no candidate matched; one feature")
    return _features(commits, groups, docs | loose), "; ".join(notes)


def rule_features(commits, cp, changed):
    """Group commits into features by candidate. Returns (features, "rules", note)."""
    features, note = _assemble(commits, cp, changed, _keys(commits, cp))
    return features, "rules", note


def _rules_with(note, commits, cp, changed):
    """The rule grouping, with the jev note (why jev was not used) placed first."""
    features, _source, rules_note = rule_features(commits, cp, changed)
    return features, "rules", "; ".join(part for part in (note, rules_note) if part)


# ─── jev proposal ─────────────────────────────────────────────────────────────

def skills_roots(env, own_root):
    """The skills dirs to search, in lookup order: `own_root` first when given, then the
    SKILLS_ROOTS rows (the variable's value when set, else HOME plus the fallback)."""
    home = env.get("HOME", "~")
    roots = [own_root] if own_root else []
    for variable, fallback, suffix in SKILLS_ROOTS:
        base = (env.get(variable, "").strip() if variable else "") or os.path.join(home, fallback)
        roots.append(os.path.join(base, suffix))
    return [os.path.expanduser(root) for root in roots]


def _own_skills_root():
    """The skills dir that holds this skill (three dirnames up from this file)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_jev(env, own_root=None):
    """The first installed jev-fast-decision client in the lookup order, or None."""
    for root in skills_roots(env, own_root or _own_skills_root()):
        entry = os.path.join(root, JEV_ENTRY_REL)
        if os.path.isfile(entry):
            return entry
    return None


def jev_item(commit, candidates, index):
    """One choice item for one commit: its subject, its path names and the candidate titles."""
    subject = commit.subject.split("\n", 1)[0]
    features = "; ".join(f"{candidate.id} = {candidate.title}" for candidate in candidates)
    context = (f"Commit subject: {subject}. Paths: {', '.join(commit.paths)}. "
               f"Features: {features}")
    return {
        "id": f"c{index}",
        "type": "choice",
        "instructions": JEV_QUESTION,
        "context": context[:JEV_CONTEXT_CHARS],
        "criteria": {candidate.id: candidate.title[:JEV_TITLE_CHARS] or candidate.id
                     for candidate in candidates},
    }


def ask_jev(entry, item, env, run=subprocess.run, timeout=JEV_TIMEOUT_SECONDS):
    """One ladder call for one item. Returns (candidate id, ""), or (None, "old") when the
    client has no `ladder` entry point, or (None, "no answer") otherwise."""
    try:
        proc = run([sys.executable, entry, "ladder"], input=json.dumps({"items": [item]}),
                   capture_output=True, text=True, env=env, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return None, "no answer"
    if proc.returncode == 2 and "invalid choice" in (proc.stderr or ""):
        return None, "old"
    try:
        answer = json.loads(proc.stdout)
    except (TypeError, ValueError):
        return None, "no answer"
    rows = answer.get("items") if isinstance(answer, dict) else None
    row = rows.get(item["id"]) if isinstance(rows, dict) else None
    if not isinstance(row, dict) or not isinstance(row.get("decided_by"), str):
        return None, "no answer"
    column = row.get(row["decided_by"])
    choice = column.get("choice") if isinstance(column, dict) else None
    if isinstance(choice, str) and choice in item["criteria"]:
        return choice, ""
    return None, "no answer"


def validate_partition(assignment, commits, cp, changed):
    """Why a jev assignment (commit sha, candidate id pairs) must be refused, or None.

    Every non-docs commit goes to exactly one feature, and no code file lands in a feature that
    shares none of its test_<stem>.py's features. A shared path is not refused: the merge keeps
    it whole.
    """
    shas = [sha for sha, _feature in assignment]
    if len(set(shas)) != len(shas):
        return "commit placed twice"
    by_sha = {commit.sha: commit for commit in commits}
    if any(sha not in by_sha for sha in shas):
        return "commit not in range"
    placed = set(shas)
    if any(_code_paths(commit, cp) and commit.sha not in placed for commit in commits):
        return "commit left out"
    owners = {}
    for sha, feature in assignment:
        for path in _code_paths(by_sha[sha], cp):
            if path in changed:
                owners.setdefault(path, set()).add(feature)
    for path in sorted(owners):
        if not _is_code(path):
            continue
        for other in sorted(owners):
            if posixpath.basename(other) == _test_name(path) and not (
                    owners[path] & owners[other]):
                return f"splits {path} from its test"
    return None


def _ask_commits(entry, commits, cp, env, run):
    """jev's pick for each commit with code paths. Returns (picks, assignment, note): `picks`
    feeds the grouping, and `note` names why jev did not decide (an old client, or the first
    commit it did not answer), else it is empty."""
    index_of = {candidate.id: index for index, candidate in enumerate(cp.candidates)}
    picks, assignment = [], []
    for index, commit in enumerate(commits):
        if not _code_paths(commit, cp):
            picks.append(None)
            continue
        choice, why = ask_jev(entry, jev_item(commit, cp.candidates, index), env, run)
        if choice is None:
            note = OLD_CLIENT_NOTE if why == "old" else f"jev: no answer for c{index}"
            return picks, assignment, note
        picks.append(index_of[choice])
        assignment.append((commit.sha, choice))
    return picks, assignment, ""


def jev_features(commits, cp, changed, env=None, run=subprocess.run):
    """Features built on jev's per-commit choices. The rules decide when jev is missing, silent,
    old or wrong, and the note says which."""
    entry = find_jev(os.environ if env is None else env)
    if len(cp.candidates) < 2 or entry is None:
        return rule_features(commits, cp, changed)
    picks, assignment, note = _ask_commits(entry, commits, cp, env, run)
    if note:
        return _rules_with(note, commits, cp, changed)
    if not assignment:
        return rule_features(commits, cp, changed)
    reason = validate_partition(assignment, commits, cp, changed)
    if reason:
        return _rules_with(f"jev rejected: {reason}", commits, cp, changed)
    features, note = _assemble(commits, cp, changed, _keys(commits, cp, picks))
    return features, "jev", note


def group_features(commits, cp, changed):
    """The one grouping seam fold.py calls: jev first, the rules when it cannot decide."""
    return jev_features(commits, cp, changed)
