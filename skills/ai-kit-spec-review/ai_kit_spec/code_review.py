"""The code-review loop's pure parts: report normalization, the pass rule over parsed
findings, the cap, the changed paths and the review prompt. Lane dispatch, ping, switch
and merge stay the existing subcommands."""

import json
import os
import re
import subprocess
import sys
from typing import NamedTuple

from ai_kit_spec import lens_delivery, review_reports, secret_shapes, skill_table

CODE_REVIEW_CAP = 3
BLOCKING = ("CRITICAL", "HIGH")
SEVERITY_ORDER = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
SUPERPOWERS_SEVERITY = {"Critical": "CRITICAL", "Important": "HIGH", "Minor": "LOW"}
_HEADING_RE = re.compile(r"^#### (Critical|Important|Minor)\b", re.MULTILINE)
_SP_HEAD_RE = re.compile(r"^#### (Critical|Important)\b")
_AIKIT_HEAD_RE = re.compile(r"^### (CRITICAL|HIGH)\s*$")
_ANY_HEAD_RE = re.compile(r"^(#{1,6})(?:[ \t]|$)")
# a severity heading in another case, at level 2 or 3, or with a count reads as ai-kit's own;
# level 4 stays superpowers' shape
_LOOSE_SEVERITY_RE = re.compile(
    r"^#{2,3}[ \t]*(critical|high|medium|low)[ \t]*(?:\(\d+\))?[ \t]*:?[ \t]*$",
    re.IGNORECASE | re.MULTILINE)
_ITEM_RE = re.compile(r"^(?:\d+\.|[-*])\s+(.+)$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# the closed set of "no finding here" lines: None, None found., No critical issues., _None_, ...
_EMPTY_RE = re.compile(
    r"^(?:[-*]\s+)?((?:\*\*|[_*])?)(?:none(?: found)?|no(?: (?:critical|important|minor|high"
    r"|medium|low))? issues?(?: found)?)\.?\1\.?$", re.IGNORECASE)
_SUB_RE = re.compile(r"^\s+(?:[-*]\s+)?(File|Issue|Impact|Fix):\s*(\S.*)$", re.IGNORECASE)
_PATH_LINE_RE = re.compile(r"[\w./-]+:\d+")
_ASSESSMENT_RE = re.compile(r"^### Assessment\b", re.MULTILINE)
TITLE_CHARS = 80
OMITTED = "[omitted]"
INCOMPLETE = "ai-kit-spec: code review report incomplete: {}"
REVIEW_LENS = "ponytail-review"
UI_LENS = "impeccable"
MISSING_LENS = "ai-kit-spec: lens {} not installed; the review runs without it"
CONTROL_PATH = ("ai-kit-spec: code-review-paths: dropped a path holding a control "
                "character: {!r}")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SPAN_RE = re.compile(r"`[^`]*`|\"[^\"]*\"|“[^”]*”|(?<!\w)'[^'\n]*'(?!\w)")
_UNSAFE_TOKEN_RE = re.compile(r"[/\\=]|:\S|[0-9A-Fa-f]{8,}")
_LABELS_RE = re.compile(r"(?:^|\s)Labels: (.+)$")
LABEL_VALUES = {"kind": ("logic", "security", "performance", "style", "docs", "other"),
                "tier": ("unit", "integration", "e2e", "none"),
                "repro": ("yes", "no"),
                "reach": ("user", "internal"),
                "stage": ("mvp", "production")}
CODE_REVIEW_PROMPT = (
    "Review the code change between {base} and {head} against the plan in {plan}.\n"
    "Change: {description}\n"
    "\n"
    "Run `git diff --stat {base}..{head}` and `git diff {base}..{head}` yourself and "
    "read the changed files you need. Judge correctness, safety, tests and whether the "
    "change does what the plan asks.\n"
    "\n"
    "Answer in this report shape exactly: the headings `### CRITICAL`, `### HIGH`, "
    "`### MEDIUM` and `### LOW`, each followed by one bullet per finding, "
    "each bullet on one line:\n"
    "- **<title>** — Location: <path:line>. Required: <fix>. Why: <reason>. Labels: "
    "kind=<logic|security|performance|style|docs|other>; "
    "tier=<unit|integration|e2e|none>; repro=<yes|no>; "
    "reach=<user|internal>; stage=<mvp|production>.\n"
    "Leave a heading empty when it has no finding. End with one line, either "
    "`### Status: Approved` or `### Status: Issues Found — fix and re-invoke`.\n"
)


def _summary_text(text: str, limit: int) -> str:
    text = _SPAN_RE.sub(OMITTED, text)
    tokens = [OMITTED if _UNSAFE_TOKEN_RE.search(tok) else tok for tok in text.split()]
    shown = "".join(ch for ch in " ".join(tokens) if ch.isprintable())
    shown = secret_shapes.redact(shown, "[redacted]")
    return secret_shapes.redact(shown[:limit], "[redacted]")


def _prompt_description(text: str) -> str:
    """The reviewer prompt's description: one line, control characters dropped and secret
    shapes redacted; paths and quoted text stay, since the reviewer reads the diff itself."""
    shown = secret_shapes.redact(" ".join(text.split()), "[redacted]")
    shown = "".join(ch for ch in shown if ch.isprintable())
    return secret_shapes.redact(shown, "[redacted]")


def finding_labels(finding: dict) -> dict:
    """The five fit labels from the tail of a finding's why text; a missing or invalid
    label reads unknown."""
    m = _LABELS_RE.search(finding.get("why") or "")
    pairs = {}
    for part in m.group(1).split(";") if m else ():
        key, sep, value = part.partition("=")
        words = value.split()
        if sep and words:
            # a value stops at whitespace and loses trailing periods: "mvp.. See a.py." -> mvp
            pairs[key.strip()] = words[0].rstrip(".")
    return {key: pairs.get(key) if pairs.get(key) in values else "unknown"
            for key, values in LABEL_VALUES.items()}


class IncompleteReport(ValueError):
    """A lane report that cannot be trusted as a finished review."""


class Verdict(NamedTuple):
    state: str  # "pass" | "fix" | "cap_stop"
    round_no: int
    cap: int
    blocking: list
    listed: list


def _heading_level(line: str) -> int:
    """The level of a markdown heading line; 0 for any other line."""
    match = _ANY_HEAD_RE.match(line)
    return len(match.group(1)) if match else 0


def _sections(text: str, head_re) -> list:
    """Every heading occurrence that `head_re` matches, with its body: the lines up
    to the next heading of the same or a higher level."""
    lines = text.splitlines()
    sections = []
    index = 0
    while index < len(lines):
        if head_re.match(lines[index]):
            level = _heading_level(lines[index])
            body = []
            end = index + 1
            while end < len(lines) and not 0 < _heading_level(lines[end]) <= level:
                body.append(lines[end])
                end += 1
            sections.append((lines[index], body))
            index = end
        else:
            index += 1
    return sections


def _top_items(body: list) -> list:
    """Top-level list items of one section body as (text, sub) pairs: sub maps each
    indented File, Issue, Impact or Fix line's key to its texts; the explicit empty
    marker is no item."""
    items = []
    for index, line in enumerate(body):
        item_match = _ITEM_RE.match(line)
        if not item_match:
            continue
        if _EMPTY_RE.match(item_match.group(1).strip()):
            continue
        sub: dict = {}
        for follow in body[index + 1:]:
            if not follow[:1].isspace():
                break
            sub_match = _SUB_RE.match(follow)
            if sub_match:
                sub.setdefault(sub_match.group(1).capitalize(), []).append(
                    " ".join(sub_match.group(2).split()).rstrip("."))
        items.append((" ".join(item_match.group(1).split()), sub))
    return items


def _aikit_items(body: list) -> list:
    """ai-kit bullets parsed from one section body."""
    return review_reports.parse_findings("\n".join(body) + "\n")


def _superpowers_findings(text: str) -> list:
    """Findings under the superpowers code-reviewer severity headings, location and
    text kept."""
    findings = []
    for heading, body in _sections(text, _HEADING_RE):
        head_match = _HEADING_RE.match(heading)
        assert head_match is not None
        severity = SUPERPOWERS_SEVERITY[head_match.group(1)]
        for item, sub in _top_items(body):
            bold_match = _BOLD_RE.search(item)
            title = bold_match.group(1) if bold_match else item[:TITLE_CHARS]
            plain = _BOLD_RE.sub(r"\1", item).rstrip(".")
            path_match = _PATH_LINE_RE.search(item)
            location = (sub["File"][0].split()[0] if sub.get("File")
                        else path_match.group(0) if path_match else "")
            findings.append({"severity": severity, "title": title, "location": location,
                             "required": "; ".join(sub.get("Fix", [])) or plain,
                             "why": "; ".join(sub.get("Issue", []) + sub.get("Impact", []))
                             or plain})
    return findings


def _blocking_gap(sections: list, parse) -> str | None:
    """The first CRITICAL or HIGH heading whose body has text but no parsed finding
    and no explicit empty marker, or a list item that does not parse."""
    for heading, body in sections:
        rows = [line.strip() for line in body if line.strip()]
        if not rows:
            continue
        if len(rows) == 1 and _EMPTY_RE.match(rows[0]):
            continue
        parsed = parse(body)
        if not parsed:
            return f"{heading.strip()} has text but no parsed finding"
        items = [m for m in map(_ITEM_RE.match, body)
                 if m and not _EMPTY_RE.match(m.group(1).strip())]
        if len(items) > len(parsed):
            return f"{heading.strip()} has a list item that does not parse"
    return None


def _stray_finding(text: str) -> bool:
    """True when a finding bullet's nearest heading above it is no severity heading."""
    heading = ""
    for line in text.splitlines():
        if _heading_level(line):
            heading = line
        elif any(f["severity"] is None
                 for f in review_reports.parse_findings(f"{heading}\n{line}\n")):
            return True
    return False


def normalize_report(text: str) -> list:
    """Findings of a finished ai-kit or superpowers report; IncompleteReport otherwise."""
    status = review_reports.report_status(text)
    superpowers = _HEADING_RE.search(text) is not None
    if status == "failure":
        raise IncompleteReport("the report status is Failure")
    if status is not None and superpowers:
        raise IncompleteReport(
            "the report mixes a ### Status: line with superpowers severity headings")
    if status is not None:
        text = _LOOSE_SEVERITY_RE.sub(lambda m: f"### {m.group(1).upper()}", text)
        if _stray_finding(text):
            raise IncompleteReport("a finding sits under no severity heading")
        findings = review_reports.parse_findings(text)
        if status == "issues" and not findings:
            raise IncompleteReport("the status says Issues Found but no finding parsed")
        gap = _blocking_gap(_sections(text, _AIKIT_HEAD_RE), _aikit_items)
    elif _ASSESSMENT_RE.search(text) and superpowers:
        findings = _superpowers_findings(text)
        gap = _blocking_gap(_sections(text, _SP_HEAD_RE), _top_items)
    else:
        raise IncompleteReport(
            "no ### Status: line, and no ### Assessment line with a superpowers severity heading")
    if gap is not None:
        raise IncompleteReport(gap)
    return findings


def render_report(findings: list, tag: str = "report") -> str:
    """ai-kit's report shape for normalized findings; a finding outside the four
    severities is listed under MEDIUM."""
    by_severity = {severity: [] for severity in SEVERITIES}
    for index, finding in enumerate(findings, start=1):
        severity = finding.get("severity")
        if severity not in SEVERITIES:
            severity = "MEDIUM"
        location = " ".join(str(finding.get("location", "")).split())
        if not location:
            location = f"unstated ({tag}-{index})"
        title = " ".join(str(finding.get("title", "")).split())
        required = " ".join(str(finding.get("required", "")).split())
        why = " ".join(str(finding.get("why", "")).split())
        by_severity[severity].append(
            f"- **{title}** — Location: {location}. Required: {required}. Why: {why}.")
    lines = ["## Review: code"]
    for severity in SEVERITIES:
        if by_severity[severity]:
            lines.append(f"### {severity}")
            lines.extend(by_severity[severity])
    lines.append("### Status: Issues Found — fix and re-invoke" if findings
                 else "### Status: Approved")
    return "\n".join(lines) + "\n"


def fit_severity(severity, fit) -> tuple:
    """The severity a fit class gives: higher raises one level, lower moves only MEDIUM
    to LOW; a CRITICAL or HIGH finding is never lowered."""
    if severity not in SEVERITY_ORDER or fit in (None, "fits"):
        return severity, ""
    if fit == "higher":
        return SEVERITY_ORDER[min(SEVERITY_ORDER.index(severity) + 1,
                                  len(SEVERITY_ORDER) - 1)], ""
    if fit == "lower":
        if severity == "MEDIUM":
            return "LOW", ""
        return severity, "never lowered" if severity in BLOCKING else ""
    return severity, ""


def check_fit(findings: list, rows: list) -> None:
    """Refuse fit rows that break the fit rule or whose CRITICAL or HIGH result the
    report lacks; rows of several lane reports may cover one merged finding."""
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("new_severity") != fit_severity(
                row.get("severity"), row.get("fit"))[0]:
            raise ValueError(f"fit row {i} does not follow the fit rule")
        if row.get("new_severity") in BLOCKING and not any(
                f.get("severity") == row["new_severity"]
                and f.get("location") == row.get("location") for f in findings):
            raise ValueError(
                f"fit row {i}: its {row['new_severity']} finding is missing from the report")


def _check_fit_file(path: str, findings: list) -> None:
    """The fit rows file (UTF-8 JSON) checked against the report's findings."""
    with open(path, encoding="utf-8") as handle:
        rows = json.load(handle)
    if not isinstance(rows, list):
        raise ValueError("the fit file is not a list")
    check_fit(findings, rows)


def review_verdict(findings: list, round_no: int, cap: int = CODE_REVIEW_CAP) -> Verdict:
    """Pass when no CRITICAL or HIGH finding is open; MEDIUM and LOW are listed and
    never block."""
    blocking = [f for f in findings if f.get("severity") in BLOCKING]
    listed = [f for f in findings if f.get("severity") not in BLOCKING]
    if not blocking:
        state = "pass"
    elif round_no < cap:
        state = "fix"
    else:
        state = "cap_stop"
    return Verdict(state, round_no, cap, blocking, listed)


def review_paths(base: str, head: str, cwd: str, run=subprocess.run) -> list:
    """The changed paths between two revisions, byte for byte: deleted paths dropped,
    a renamed file under its new name."""
    if not base or base.startswith("-") or not head or head.startswith("-"):
        raise ValueError(f"bad revision: {base!r}..{head!r}")
    proc = run(["git", "-C", cwd, "diff", "--name-only", "-z", "--diff-filter=d",
                f"{base}..{head}", "--"], capture_output=True, check=False, timeout=60)
    if proc.returncode != 0:
        raise ValueError(
            f"git diff failed: {proc.stderr.decode('utf-8', 'replace').strip()[:200]}")
    entries = proc.stdout.decode("utf-8", "surrogateescape").split("\0")
    paths = [entry if not entry.startswith("-") else f"./{entry}"
             for entry in entries if entry]
    return sorted(set(paths))


def missing_lenses(table: dict, paths: list) -> list:
    """The code-review lenses the skill discovery has no row for: ponytail-review always,
    impeccable for a UI path."""
    wanted = [REVIEW_LENS] + ([UI_LENS] if any(
        path.lower().endswith(lens_delivery.UI_EXTENSIONS) for path in paths) else [])
    present = {row.get("name") for entry in table.values() if isinstance(entry, dict)
               for row in entry.get("skills") or []}
    return [name for name in wanted if name not in present]


def _read_report(path: str) -> str:
    """The report file as strict UTF-8 text; anything else is an incomplete report."""
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise IncompleteReport("the file is not valid UTF-8") from error


def cmd_code_review_normalize(args, _deps) -> int:
    """Write one lane's normalized report: exit 0, 4 incomplete, 2 unreadable."""
    try:
        findings = normalize_report(_read_report(args.report))
        rendered = render_report(findings, os.path.splitext(os.path.basename(args.report))[0])
        if len(review_reports.parse_findings(rendered)) != len(findings):
            raise IncompleteReport("the normalized report does not parse back")
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    except IncompleteReport as error:
        print(INCOMPLETE.format(error), file=sys.stderr)
        return 4
    except OSError as error:
        print(f"code-review-normalize: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"report": args.out, "findings": len(findings)}))
    return 0


def cmd_code_review_prompt(args, _deps) -> int:
    """Write the review prompt; the description is one line with secrets redacted."""
    try:
        prompt = CODE_REVIEW_PROMPT.format(
            base=args.base, head=args.head, plan=args.plan,
            description=_prompt_description(args.description))
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(prompt)
    except OSError as error:
        print(f"code-review-prompt: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"prompt": args.out}))
    return 0


def cmd_code_review_verdict(args, _deps) -> int:
    """Print the round verdict JSON: exit 0 pass, 1 fix, 3 cap stop, 4 incomplete
    report, 2 bad input."""
    if args.round < 1 or args.cap < 1:
        print("code-review-verdict: --round and --cap must be 1 or more", file=sys.stderr)
        return 2
    try:
        findings = normalize_report(_read_report(args.report))
    except IncompleteReport as error:
        print(INCOMPLETE.format(error), file=sys.stderr)
        return 4
    except OSError as error:
        print(f"code-review-verdict: {error}", file=sys.stderr)
        return 2
    if args.fit_json:
        try:
            _check_fit_file(args.fit_json, findings)
        except (OSError, ValueError) as error:
            print(f"code-review-verdict: {error}", file=sys.stderr)
            return 2
    verdict = review_verdict(findings, args.round, args.cap)
    print(json.dumps(verdict._asdict()))
    return {"pass": 0, "fix": 1, "cap_stop": 3}[verdict.state]


def cmd_code_review_paths(args, deps) -> int:
    """Print the changed paths of a base..head range as JSON: a control-character path
    is dropped and named on stderr, a missing lens is named on stderr."""
    try:
        paths = review_paths(args.base, args.head, args.cwd, deps.run_fn)
        kept = [path for path in paths if not _CONTROL_RE.search(path)]
        dropped = [path for path in paths if _CONTROL_RE.search(path)]
        for path in dropped:
            print(CONTROL_PATH.format(path), file=sys.stderr)
        for name in missing_lenses(skill_table.scan(deps.env_fn(), args.cwd), kept):
            print(MISSING_LENS.format(name), file=sys.stderr)
        print(json.dumps(kept))
        return 0
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(f"code-review-paths: {error}", file=sys.stderr)
        return 2


def register_parsers(sub) -> None:
    """Register the code-review commands."""
    prompt = sub.add_parser(
        "code-review-prompt",
        help="write the ai-kit code-review prompt for a base..head range")
    prompt.add_argument("--base", required=True)
    prompt.add_argument("--head", required=True)
    prompt.add_argument("--plan", required=True)
    prompt.add_argument("--description", required=True)
    prompt.add_argument("--out", required=True)
    normalize = sub.add_parser(
        "code-review-normalize",
        help="write a lane's code-review report in ai-kit's shape: "
             "exit 0, 4 incomplete, 2 unreadable")
    normalize.add_argument("--report", required=True)
    normalize.add_argument("--out", required=True)
    verdict = sub.add_parser(
        "code-review-verdict",
        help="the round verdict: exit 0 pass, 1 fix, 3 cap stop, "
             "4 incomplete report, 2 bad input")
    verdict.add_argument("--report", required=True)
    verdict.add_argument("--round", type=int, required=True)
    verdict.add_argument("--cap", type=int, default=CODE_REVIEW_CAP)
    verdict.add_argument("--fit-json", default=None,
                         help="classify-findings rows to check against the report before "
                              "the verdict")
    paths = sub.add_parser(
        "code-review-paths",
        help="list the changed paths of a base..head range for dispatch-reviewer --files; "
             "names a missing lens on stderr")
    paths.add_argument("--base", required=True)
    paths.add_argument("--head", required=True)
    paths.add_argument("--cwd", required=True)


COMMANDS = {
    "code-review-prompt": cmd_code_review_prompt,
    "code-review-normalize": cmd_code_review_normalize,
    "code-review-verdict": cmd_code_review_verdict,
    "code-review-paths": cmd_code_review_paths,
}
