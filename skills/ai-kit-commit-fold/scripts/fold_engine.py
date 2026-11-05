"""Fold engine for ai-kit-commit-fold: one checkpoint in, one commit per feature out.

The engine reads only the framework-neutral checkpoint (schema 1) and names no framework.
Folded commits are built with git plumbing in a temporary index, so the working tree and the
real index are never touched. The branch moves once, by compare-and-swap, after the tree proofs
and the backup tag.
"""

import dataclasses
import os
import re
import subprocess
import tempfile

REASONS = frozenset({
    "bad_checkpoint", "policy_missing", "dirty_tree", "branch_moved", "no_base_branch",
    "range_on_base_branch", "range_on_merged_branch", "foreign_merge", "tree_mismatch",
    "tag_exists", "git_error",
})

_SCRUBBED = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
POLICY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "references", "folding-policy.md")
_UNIT = re.compile(r"[A-Za-z0-9._-]{1,64}")
_REF = re.compile(r"refs/heads/[A-Za-z0-9._/-]{1,200}")
_REF_ANY = re.compile(r"refs/[A-Za-z0-9._/-]{1,200}")
_SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_TYPES = ("feat", "fix", "refactor", "perf", "test", "docs", "build", "ci", "style", "chore")
_TYPE_PREFIX = re.compile("(" + "|".join(_TYPES) + r")(?:\(|!|:)")
_TITLE_MAX = 60
_NOTE_MAX = 200


class FoldError(Exception):
    """A refusal: `reason` is one of REASONS and `detail` is one short human line."""

    def __init__(self, reason, detail=""):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclasses.dataclass(frozen=True)
class Candidate:
    id: str
    title: str
    files: tuple[str, ...]
    summary: str = ""


@dataclasses.dataclass(frozen=True)
class Checkpoint:  # pylint: disable=too-many-instance-attributes  # one field per schema key
    unit: str
    ref: str
    base: str
    end: str
    tip: str
    base_branch: str
    merged_refs: tuple[str, ...]
    own_merge_subjects: tuple[str, ...]
    candidates: tuple[Candidate, ...]
    docs_paths: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class Commit:
    sha: str
    parents: tuple[str, ...]
    subject: str
    raw_message: bytes
    author: tuple[str, str, str]
    paths: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class Result:  # pylint: disable=too-many-instance-attributes  # one field per report input
    unit: str
    ref: str
    before: int
    after: int
    tree: str
    tag: str
    outcome: str
    reason: str
    grouping: str
    note: str
    mode: str


def _bad(detail):
    return FoldError("bad_checkpoint", detail)


def _str_list(data, key):
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _bad(f"{key} must be a list of strings")
    return tuple(value)


def _ref_list(data, key):
    refs = _str_list(data, key)
    if not all(_REF_ANY.fullmatch(ref) for ref in refs):
        raise _bad(f"{key} entries must be full ref names (refs/...)")
    return refs


def _sha(data, key, default=None):
    value = data.get(key, default)
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise _bad(f"{key} must be a full commit sha")
    return value


def _candidate(item):
    if not isinstance(item, dict) or not isinstance(item.get("id"), str):
        raise _bad("candidate needs a string id")
    if not isinstance(item.get("title"), str):
        raise _bad("candidate needs a string title")
    files = item.get("files")
    if not isinstance(files, list) or not all(isinstance(path, str) for path in files):
        raise _bad("candidate files must be a list of strings")
    summary = item.get("summary", "")
    if not isinstance(summary, str):
        raise _bad("candidate summary must be a string")
    return Candidate(item["id"], item["title"], tuple(files), summary)


def load_checkpoint(data):
    """Validate a schema-1 checkpoint dict; unknown keys are ignored (forward compatible)."""
    schema = data.get("schema") if isinstance(data, dict) else None
    if isinstance(schema, bool) or schema != 1:
        raise _bad("schema must be 1")
    unit = data.get("unit")
    if not isinstance(unit, str) or not _UNIT.fullmatch(unit):
        raise _bad("unit must be 1-64 characters of A-Z a-z 0-9 . _ -")
    ref = data.get("ref")
    if not isinstance(ref, str) or not _REF.fullmatch(ref):
        raise _bad("ref must be refs/heads/<branch>")
    base_branch = data.get("base_branch")
    if not isinstance(base_branch, str) or not base_branch:
        raise _bad("base_branch must be a non-empty string")
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        raise _bad("candidates must be a list")
    tip = _sha(data, "tip")
    return Checkpoint(
        unit=unit,
        ref=ref,
        base=_sha(data, "base"),
        end=_sha(data, "end", tip),
        tip=tip,
        base_branch=base_branch,
        merged_refs=_ref_list(data, "merged_refs"),
        own_merge_subjects=_str_list(data, "own_merge_subjects"),
        candidates=tuple(_candidate(item) for item in candidates),
        docs_paths=_str_list(data, "docs_paths"),
    )


def _env(**extra):
    env = {key: value for key, value in os.environ.items() if key not in _SCRUBBED}
    env.update(extra)
    return env


def _run(repo, args, data=None, env=None):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        input=data, capture_output=True, env=env or _env(), check=False,
    )


def _first_line(stderr):
    lines = stderr.decode("utf-8", "replace").strip().splitlines()
    return lines[0] if lines else ""


def _git(repo, *args, data=None, env=None):
    proc = _run(repo, args, data=data, env=env)
    if proc.returncode != 0:
        detail = _first_line(proc.stderr) or f"git {args[0]} exited {proc.returncode}"
        raise FoldError("git_error", detail)
    return proc.stdout


def _rev(repo, spec):
    """The object id of `spec`, or None when it does not resolve."""
    proc = _run(repo, ("rev-parse", "--verify", "--quiet", spec))
    return proc.stdout.decode().strip() if proc.returncode == 0 else None


def _commit(repo, sha):
    raw = _git(repo, "cat-file", "commit", sha)
    header, _, message = raw.partition(b"\n\n")
    parents = tuple(line[len(b"parent "):].decode() for line in header.split(b"\n")
                    if line.startswith(b"parent "))
    ident = _git(repo, "log", "-1", "--format=%an%x00%ae%x00%ad", "--date=raw", sha)
    name, email, date = ident.decode("utf-8", "replace").rstrip("\n").split("\0")
    diff = _git(repo, "diff-tree", "-r", "-z", "--no-commit-id", "--name-only", "--no-renames",
                parents[0], sha)
    paths = tuple(path.decode("utf-8") for path in diff.split(b"\0") if path)
    subject = message.split(b"\n", 1)[0].decode("utf-8", "replace")
    return Commit(sha, parents, subject, message, (name, email, date), paths)


def range_commits(repo, cp):
    """The commits of base..end, oldest first, merges excluded (own merge-backs fold away)."""
    listed = _git(repo, "rev-list", "--reverse", "--topo-order", "--no-merges",
                  f"{cp.base}..{cp.end}")
    return [_commit(repo, sha.decode()) for sha in listed.split()]


def _changes(repo, cp):
    """Changed paths of base..end, and the subset deleted by the range."""
    listed = _git(repo, "diff", "--name-status", "-z", "--no-renames", cp.base, cp.end)
    tokens = [token for token in listed.split(b"\0") if token]
    changed, deleted = set(), set()
    for status, raw in zip(tokens[0::2], tokens[1::2], strict=True):
        path = raw.decode("utf-8")
        changed.add(path)
        if status.startswith(b"D"):
            deleted.add(path)
    return frozenset(changed), frozenset(deleted)


def _entry(repo, end, path):
    listed = _git(repo, "ls-tree", "-z", end, "--", path).split(b"\0")[0]
    fields = listed.split(b"\t", 1)[0].split()
    if len(fields) != 3:
        raise FoldError("git_error", f"{path} is not in {end[:12]}")
    mode, _kind, blob = fields
    return mode.decode(), blob.decode()


def _commit_type(subjects):
    found = {match.group(1) for match in map(_TYPE_PREFIX.match, subjects) if match}
    return next((kind for kind in _TYPES if kind in found), "chore")


def _message(unit, title, members):
    kind = _commit_type([member.subject for member in members])
    title = _CONTROL.sub(" ", title).strip()
    if len(title) > _TITLE_MAX:
        title = title[: _TITLE_MAX - 3] + "..."
    body = b"\n".join(member.raw_message.rstrip(b"\n") + b"\n" for member in members)
    return f"{kind}({unit}): {title}\n\n".encode() + body + f"\nAi-Kit-Fold: {unit}\n".encode()


def _stage(repo, cp, feature, deleted, env):
    """Put the feature's final-state paths into the temporary index."""
    for path in sorted(feature.paths):
        if path in deleted:
            _git(repo, "update-index", "--force-remove", "--", path, env=env)
        else:
            mode, blob = _entry(repo, cp.end, path)
            _git(repo, "update-index", "--add", "--cacheinfo", mode, blob, path, env=env)


def _author_env(index, author):
    """Folded commits keep the author of the feature's first commit; the committer is current."""
    name, email, date = author
    return _env(GIT_INDEX_FILE=index, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email,
                GIT_AUTHOR_DATE=date)


def _build(repo, cp, commits, features, deleted):
    """Build the folded commits in a temporary index; return the last commit id."""
    fd, index = tempfile.mkstemp(prefix="ai-kit-fold-index-")
    os.close(fd)
    os.remove(index)
    env = _env(GIT_INDEX_FILE=index)
    by_sha = {commit.sha: commit for commit in commits}
    try:
        _git(repo, "read-tree", cp.base, env=env)
        parent = cp.base
        for feature in features:
            _stage(repo, cp, feature, deleted, env)
            members = [by_sha[sha] for sha in feature.commits]
            tree = _git(repo, "write-tree", env=env).decode().strip()
            message = _message(cp.unit, feature.title, members)
            parent = _git(repo, "commit-tree", tree, "-p", parent, "-F", "-", data=message,
                          env=_author_env(index, members[0].author)).decode().strip()
        return parent
    finally:
        if os.path.exists(index):
            os.remove(index)


def _before_swap(repo):
    """Test seam: plan 29-06 patches this to move the branch just before the swap."""
    del repo


def _swap(repo, cp, new_tip):
    name = f"ai-kit-fold/{cp.unit}/{cp.tip[:12]}"
    existing = _rev(repo, f"refs/tags/{name}^{{commit}}")
    created = existing is None
    if created:
        _git(repo, "tag", name, cp.tip)
    elif existing != cp.tip:
        raise FoldError("tag_exists", f"{name} already points at another commit")
    _before_swap(repo)
    try:
        _git(repo, "update-ref", "-m", f"ai-kit-fold {cp.unit}", cp.ref, new_tip, cp.tip)
    except FoldError as exc:
        if created:
            _run(repo, ("tag", "-d", name))
        raise FoldError("branch_moved", exc.detail) from exc
    return name


def _prove_segment(repo, cp, new):
    """The folded segment must hold exactly the end tree. An unresolved id proves nothing."""
    tree = _rev(repo, f"{new}^{{tree}}")
    if tree is None or tree != _rev(repo, f"{cp.end}^{{tree}}"):
        raise FoldError("tree_mismatch", "folded segment tree differs from the end tree")


def _prove_target(repo, cp, target):
    tree = _rev(repo, f"{target}^{{tree}}")
    if tree is None or tree != _rev(repo, f"{cp.tip}^{{tree}}"):
        raise FoldError("tree_mismatch", "swap target tree differs from the tested tip tree")
    return tree


def _resolved(repo, specs):
    """The object ids of the specs that resolve; a spec that does not resolve is skipped."""
    return [sha for sha in (_rev(repo, spec) for spec in specs) if sha]


def _check_policy():
    try:
        with open(POLICY_PATH, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        text = ""
    if not text.strip():
        raise FoldError("policy_missing", "the folding policy text is missing or empty")


def _count(repo, *args):
    return int(_git(repo, "rev-list", "--count", *args).decode().strip())


def _check_ancestry(repo, cp):
    """base must be an ancestor of end, and end must sit on the first-parent chain of tip."""
    proc = _run(repo, ("merge-base", "--is-ancestor", cp.base, cp.end))
    if proc.returncode == 1:
        raise FoldError("bad_checkpoint", "base is not an ancestor of end")
    if proc.returncode != 0:
        raise FoldError("git_error", _first_line(proc.stderr))
    chain = _git(repo, "rev-list", "--first-parent", cp.tip).split()
    if cp.end.encode() not in chain:
        raise FoldError("bad_checkpoint", "end is not on the first-parent chain of tip")


def _check_not_reachable(repo, cp, refs, reason):
    """Refuse when a commit of base..tip is reachable from one of refs (SPEC R4)."""
    if not refs:
        return
    span = f"{cp.base}..{cp.tip}"
    if _count(repo, span, "--not", *refs) != _count(repo, span):
        raise FoldError(reason, "a commit of the range is already on that branch")


def _check_merges(repo, cp):
    """Only GSD's own merge-backs may sit in base..end; each folds away (D-05)."""
    for sha in _git(repo, "rev-list", "--merges", f"{cp.base}..{cp.end}").decode().split():
        subject = _git(repo, "log", "-1", "--format=%s", sha).decode("utf-8", "replace").strip()
        if not any(prefix and subject.startswith(prefix) for prefix in cp.own_merge_subjects):
            raise FoldError("foreign_merge",
                            f"merge {sha[:12]} is not one of GSD's own merge-backs")


def _guard(repo, cp):
    """Every refusal that must hold before any write; each leaves the repository as it was."""
    _check_policy()
    if _git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise FoldError("dirty_tree", "tracked files have uncommitted changes")
    if _rev(repo, cp.ref) != cp.tip:
        raise FoldError("branch_moved", f"{cp.ref} is no longer at the tested tip")
    base_refs = _resolved(repo, (f"refs/heads/{cp.base_branch}",
                                 f"refs/remotes/origin/{cp.base_branch}"))
    if not base_refs:
        raise FoldError("no_base_branch",
                        f"neither {cp.base_branch} nor origin/{cp.base_branch} resolves")
    _check_ancestry(repo, cp)
    _check_not_reachable(repo, cp, base_refs, "range_on_base_branch")
    _check_not_reachable(repo, cp, _resolved(repo, cp.merged_refs), "range_on_merged_branch")
    _check_merges(repo, cp)


def _segment(repo, cp, commits, features, deleted):
    """Build the folded segment of base..end and prove it holds exactly the end tree."""
    seg = _build(repo, cp, commits, features, deleted)
    _prove_segment(repo, cp, seg)
    return seg


def _replayed(repo, cp):
    """The commits after end on the tip's first-parent chain, oldest first."""
    return _git(repo, "rev-list", "--reverse", "--first-parent",
                f"{cp.end}..{cp.tip}").decode().split()


def _replay(repo, cp, seg):
    """Re-create each commit after end on top of the segment, tree-identical (ruling 4).

    Each replayed commit keeps its tree, raw message, author and non-first parents; only its
    first parent changes. Runs after the segment proof, so the final proof cannot pass a bad
    segment by replaying trees that are correct on their own.
    """
    new = seg
    for sha in _replayed(repo, cp):
        commit = _commit(repo, sha)
        tree = _git(repo, "rev-parse", f"{sha}^{{tree}}").decode().strip()
        extra = [item for parent in commit.parents[1:] for item in ("-p", parent)]
        name, email, date = commit.author
        env = _env(GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_AUTHOR_DATE=date)
        new = _git(repo, "commit-tree", tree, "-p", new, *extra, "-F", "-",
                   data=commit.raw_message, env=env).decode().strip()
    return new


def _fold(repo, cp, group, mode, seen):
    _guard(repo, cp)
    commits = range_commits(repo, cp)
    seen["before"] = len(commits)
    if len(commits) < 2:
        return Result(unit=cp.unit, ref=cp.ref, before=len(commits), after=len(commits),
                      tree="", tag="", outcome="nothing_to_fold", reason="", grouping="",
                      note="", mode=mode)
    changed, deleted = _changes(repo, cp)
    features, source, note = group(commits, cp, changed)
    new = _replay(repo, cp, _segment(repo, cp, commits, features, deleted))
    tree = _prove_target(repo, cp, new)
    tag = _swap(repo, cp, new)
    # after: the folded features plus the non-merge commits replayed after end (merges excluded)
    after = len(features) + _count(repo, "--no-merges", "--first-parent", f"{cp.end}..{cp.tip}")
    return Result(unit=cp.unit, ref=cp.ref, before=len(commits), after=after,
                  tree=tree, tag=tag, outcome="folded", reason="", grouping=source,
                  note=note, mode=mode)


def fold(repo, cp, group, mode):
    """Fold the checkpoint's range. Every outcome, refusals included, comes back as a Result."""
    seen = {"before": 0}
    try:
        return _fold(repo, cp, group, mode, seen)
    except FoldError as exc:
        count = seen["before"]
        return Result(unit=cp.unit, ref=cp.ref, before=count, after=count, tree="", tag="",
                      outcome="refused", reason=exc.reason, grouping="", note=exc.detail,
                      mode=mode)


def _commit_line(result):
    note = _CONTROL.sub("", result.note)[:_NOTE_MAX]
    if result.grouping:
        suffix = f" (grouping: {result.grouping}" + (f"; {note}" if note else "") + ")"
    elif note:
        suffix = f" ({note})"
    else:
        suffix = ""
    return f"{result.before} -> {result.after}{suffix}"[:_NOTE_MAX]


def _outcome_words(result):
    if result.outcome == "folded":
        return "folded"
    if result.outcome == "nothing_to_fold":
        return "nothing to fold"
    return f"refused {result.reason}"


def render_report(result):
    """The fixed five-line plain-text report: unit, counts, tree, tag, outcome."""
    if result.outcome == "folded":
        tree_line = f"tree: equal {result.tree[:12]}"
        tag_line = f"tag: {result.tag}"
    else:
        tree_line, tag_line = "tree: not checked", "tag: none"
    return "\n".join([
        f"fold {result.unit}: {result.ref}",
        f"commits: {_commit_line(result)}",
        tree_line,
        tag_line,
        f"outcome: {result.unit} {_outcome_words(result)} ({result.mode})",
    ])
