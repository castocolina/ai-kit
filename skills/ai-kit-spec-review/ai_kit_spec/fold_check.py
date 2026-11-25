"""The superpowers fold-step check: a plan whose last task names no fold step gets one HIGH
finding. cli.py registers check-fold-step and uses read_extra_findings for merge-reports; this
module never imports cli."""

import argparse
import re
import sys

from ai_kit_spec import review_reports

FOLD_SKILL = "ai-kit-commit-fold"
FOLD_TODO = "Fold the plan's commits (ai-kit-commit-fold)"
EXTRA_TAG = "fold-check"

_TASK_RE = re.compile(r"^### Task ")
_STOP_RE = re.compile(r"^#{1,3} ")
_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_MARK_RE = re.compile(r"ai-kit-commit-fold|fold the plan's commits", re.IGNORECASE)
_STEP_LINE_RE = re.compile(r"^\s*(#{1,6} |- \[[ xX]\] )")
_ARCHETYPE_SPLIT_RE = re.compile(r"[+,\s]+")

FINDING_LINE = (
    "- **Plan has no fold step** — Location: {doc}, last ### Task. Required: add a final task "
    "\"### Task {n}: " + FOLD_TODO + "\" with one checkbox that runs the " + FOLD_SKILL
    + " fold step. Why: a superpowers plan that ends without the fold step leaves its commits "
    "unfolded and its unit unpushed."
)


def _real_lines(text: str) -> list[str]:
    """The lines of text outside fenced code blocks, by the CommonMark fence rule."""
    kept = []
    fence = None
    for line in text.splitlines():
        m = _FENCE_RE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
            else:
                kept.append(line)
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                and not m.group(2).strip():
            fence = None
    return kept


def fold_finding(text: str, doc: str) -> str | None:
    """The two-line HIGH finding block for the document doc, or None when the last real task
    names the fold step or there is no task."""
    lines = _real_lines(text)
    starts = [i for i, line in enumerate(lines) if _TASK_RE.match(line)]
    if not starts:
        return None
    end = len(lines)
    for i in range(starts[-1] + 1, len(lines)):
        if _STOP_RE.match(lines[i]) and not _TASK_RE.match(lines[i]):
            end = i
            break
    for line in lines[starts[-1]:end]:
        if _STEP_LINE_RE.match(line) and _MARK_RE.search(line):
            return None
    return "### HIGH\n" + FINDING_LINE.format(doc=doc, n=len(starts) + 1) + "\n"


def wants_check(framework: str, archetype: str) -> bool:
    """True for a superpowers plan: the framework id and a plan archetype."""
    return framework == "superpowers" and "plan" in _ARCHETYPE_SPLIT_RE.split(archetype.strip())


def read_extra_findings(path: str) -> list:
    """argparse type for merge-reports --extra-findings: [(fold-check, text)] when the file
    holds a finding, else []."""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise argparse.ArgumentTypeError(
            f"cannot read {path}: {exc.__class__.__name__}") from exc
    if review_reports.parse_findings(text):
        return [(EXTRA_TAG, text)]
    if not text.strip():
        return []
    raise argparse.ArgumentTypeError(f"{path}: no finding parses")


def cmd_check_fold_step(args, deps) -> int:
    """Print the fold finding for a superpowers plan, nothing otherwise; exit 0 (2 for an
    unreadable document)."""
    if not wants_check(args.framework, args.archetype):
        return 0
    try:
        with open(args.doc, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ai-kit-spec: check-fold-step cannot read {args.doc}: {exc.__class__.__name__}",
              file=sys.stderr)
        return 2
    finding = fold_finding(text, args.doc)
    if finding is not None:
        print(finding, end="")
    return 0


def register_parsers(sub) -> None:
    """Register the check-fold-step command."""
    parser = sub.add_parser(
        "check-fold-step",
        help="print a HIGH finding when a superpowers plan's last task names no fold step",
    )
    parser.add_argument("--doc", required=True)
    parser.add_argument("--framework", required=True, help="framework profile id, or none")
    parser.add_argument("--archetype", required=True,
                        help="one or more archetypes, joined by + or ,")


COMMANDS = {"check-fold-step": cmd_check_fold_step}
