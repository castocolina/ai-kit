"""Advisory jev calls of the review loop.

Summaries only; no jev, an error or a low answer keeps today's path, and a CRITICAL or
HIGH finding always reaches the owner."""

import functools
import json
import re
import subprocess
import sys
import time
from typing import NamedTuple

from ai_kit_spec import (
    code_review,
    config_io,
    jev_names,
    lane_switch,
    quota,
    review_log,
    review_reports,
    review_signals,
    routing,
)
from ai_kit_spec.cache import cache_read_json, cache_write_text
from ai_kit_spec.code_review import _summary_text
from ai_kit_spec.lane_order import STABLE_TOP

CLASSIFY_QUESTION = (
    "A document fixer did not apply this review finding. "
    "Judged only from this summary, which class fits?"
)
CLASSES = {
    "owner_decision": "a strategy or scope choice only the document's author can make",
    "mechanical": "a plain text edit can satisfy the finding",
    "reviewer_wrong": "the finding is mistaken or does not apply",
}
CODE_CLASSIFY_QUESTION = (
    "A code fixer did not apply this code review finding. "
    "Judged only from this summary, which class fits?"
)
CODE_CLASSES = {
    "owner_decision": "a design or scope choice only the code's owner can make",
    "mechanical": "a plain code change can satisfy the finding",
    "reviewer_wrong": "the finding is mistaken or does not apply",
}
# The only severities jev may route away from the owner.
SKIPPABLE = ("MEDIUM", "LOW")
TITLE_CHARS = 80
REASON_CHARS = 160
LANES_QUESTION = (
    "How many independent review lanes does this plan need, judged only from these facts?"
)
REVIEWER_QUESTION = (
    "Which candidate lane should review this plan first, judged only from these facts?"
)
LANE_CRITERIA = {"one": "one review lane is enough",
                 "two": "two independent review lanes are needed"}
ARCHETYPES = ("intent", "requirements", "design", "plan")
FRAMEWORKS = ("superpowers", "spec-kit", "openspec", "kiro", "gsd", "bmad")
NO_SECOND = "the roster has no second eligible lane"
EXECUTE_QUESTION = (
    "An implementer lane finished one task run. "
    "Judged only from these status tokens, which class fits the run?"
)
EXECUTE_CLASSES = ("done", "partial", "another_round")
EXECUTE_CRITERIA = {
    "done": "the task is finished and goes to review",
    "partial": "the task is finished with concerns the review must see",
    "another_round": "the task likely needs more work before it is done",
}
IMPLEMENTER_STATUSES = ("DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED")
# the runner's reported statuses (its reportAndFinish calls); any other word is dropped
RUNNER_STATUSES = (
    "bad_model", "contract_violation", "crash", "empty_stdin", "locked",
    "no_change", "no_model", "not_installed", "ok", "partial", "signal",
    "timeout", "usage",
)
# the runner's FINDING_CODES, in its order; any other code is dropped
RUNNER_FINDING_CODES = (
    "no_commit", "task_uncovered", "admits_skipped", "forbidden_path",
    "no_tree_change", "outside_plan_files", "uncommitted_edits",
    "baseline_replaced", "coverage_unchecked",
)
_COVERAGE_RE = re.compile(r"(\d{1,6})/(\d{1,6})")
NO_MATCH = "ai-kit-spec: classify-disagreements: no item matched the summary"
FIT_QUESTION = ("A code reviewer gave this finding a severity. Judged only from this summary "
                "(the kind of problem, the test tier, whether it reproduces, whether end "
                "users reach it, MVP or production), does the severity fit?")
FIT_CLASSES = ("fits", "higher", "lower")
FIT_CRITERIA = {"fits": "the severity fits the problem",
                "higher": "the problem deserves a higher severity",
                "lower": "the problem deserves a lower severity"}
_SUMMARY_RE = re.compile(r"^- \*\*(.+?)\*\* — Severity: ([A-Za-z-]+)\.\s*(.*)$")


class Finding(NamedTuple):
    title: str
    severity: str
    source: str
    reason: str
    matched: bool  # False = no unique report match


class Route(NamedTuple):
    title: str
    severity: str
    source: str
    klass: str | None
    confidence: float | None
    route: str
    note: str


class Classified(NamedTuple):
    jev: str
    routes: list


class ClassifyOptions(NamedTuple):
    """Optional classify inputs: jev's root, (iteration, cap) and the finding kind."""
    own_root: str | None = None
    limits: tuple = (None, None)
    kind: str = "document"


class SizeInput(NamedTuple):
    config: dict
    reviewers: list
    text: str
    paths: list
    archetype: str
    framework: str
    quota: dict  # the raw quota cache
    routes: dict  # lane key -> route, as lane_switch.review_routes returns it
    source_vendor: str
    cross_ai: bool


class Sizing(NamedTuple):
    reviewers: list
    reason: str


class ExecuteFacts(NamedTuple):
    status: str
    runner_status: str
    findings: tuple
    coverage: str


class LaneClass(NamedTuple):
    klass: str
    decided_by: str  # "jev" or "default"
    confidence: float | None
    note: str


def _section(text: str, prefix: str) -> list:
    """Lines after the first line starting with `prefix`, up to the next `### ` heading."""
    lines = text.splitlines()
    for start, line in enumerate(lines):
        if line.startswith(prefix):
            body = []
            for later in lines[start + 1:]:
                if later.startswith("### "):
                    break
                body.append(later)
            return body
    return []


def _strip_reason(rest: str, lead: str, tail: str) -> str:
    rest = rest.strip()
    if rest.startswith(lead):
        rest = rest[len(lead):]
    rest = rest.strip()
    if rest.endswith(tail):
        rest = rest[: -len(tail)]
    rest = rest.strip()
    return rest[:-1].rstrip() if rest.endswith(".") else rest


def summary_bullets(summary_text: str) -> list:
    """(title, claimed_severity, source, reason, line) for each escalated or skipped bullet.

    The `### Status:` line is never read: a summary that lists a skipped or escalated
    finding is classified whatever its Status."""
    out = []
    sections = (
        ("### Findings escalated", "escalated",
         "Reason for escalation: ", "Caller decision needed."),
        ("### Findings skipped", "skipped", "Reason: ", "NOT addressed in this pass."),
    )
    for prefix, source, lead, tail in sections:
        for line in _section(summary_text, prefix):
            m = _SUMMARY_RE.match(line)
            if m:
                out.append((m.group(1), m.group(2), source,
                            _strip_reason(m.group(3), lead, tail), line))
    return out


def _unparsed_summary(summary_text: str) -> bool:
    """True when a non-blank line under the escalated or skipped section is no summary bullet."""
    return any(
        line.strip() and not _SUMMARY_RE.match(line)
        for prefix in ("### Findings escalated", "### Findings skipped")
        for line in _section(summary_text, prefix))


def _match(report: list, title: str, line: str) -> int | None:
    """Index of the unique report finding for a summary bullet, or None."""
    same = [i for i, f in enumerate(report) if f["title"].strip() == title.strip()]
    if len(same) == 1:
        return same[0]
    at_line = [i for i in same if report[i]["location"] in line]
    return at_line[0] if len(at_line) == 1 else None


def disagreement_items(report_text: str, summary_text: str, cap_reached: bool) -> list:
    """Findings to classify: summary bullets, plus every unmatched report finding at the cap."""
    report = review_reports.parse_findings(report_text)
    items = []
    used = set()
    for title, claimed, source, reason, line in summary_bullets(summary_text):
        i = _match(report, title, line)
        if i is None:
            items.append(Finding(title, claimed.upper(), source, reason, False))
        else:
            used.add(i)
            items.append(Finding(title, report[i]["severity"] or "none", source, reason, True))
    if cap_reached:
        items.extend(
            Finding(f["title"], f["severity"] or "none", "cap-open", "", True)
            for i, f in enumerate(report) if i not in used
        )
    return items


def finding_item(index: int, finding: Finding, kind: str = "document") -> dict:
    """One jev item built from summaries only."""
    if kind == "code":
        title = _summary_text(finding.title, TITLE_CHARS)
        return {
            "id": f"d{index}", "type": "choice", "instructions": CODE_CLASSIFY_QUESTION,
            "context": (f"Severity: {finding.severity}. Finding: {title}. "
                        f"Source: {finding.source}."),
            "criteria": dict(CODE_CLASSES),
        }
    reason = _summary_text(finding.reason, REASON_CHARS) or "none"
    title = _summary_text(finding.title, TITLE_CHARS)
    return {
        "id": f"d{index}", "type": "choice", "instructions": CLASSIFY_QUESTION,
        "context": (f"Severity: {finding.severity}. Finding: {title}. "
                    f"Fixer: {reason}. Source: {finding.source}."),
        "criteria": dict(CLASSES),
    }


def _confident(answer) -> bool:
    choice, top, reason = answer
    return reason == "" and choice is not None and top is not None and top >= STABLE_TOP


def route_for(finding: Finding, answer: tuple, limits: tuple) -> Route:
    """owner, fixer or skipped; only a confident answer on a MEDIUM or LOW finding moves it."""
    choice, top, _reason = answer
    iteration, cap = limits
    confident = _confident(answer)
    head = (finding.title, finding.severity, finding.source, choice, top)
    if finding.severity not in SKIPPABLE or not confident or choice == "owner_decision":
        return Route(*head, "owner", "")
    if choice == "mechanical":
        if iteration is not None and cap is not None and iteration < cap:
            return Route(*head, "fixer", "")
        return Route(*head, "owner", "")
    if choice == "reviewer_wrong":
        return Route(*head, "skipped", f"jev: reviewer_wrong ({top:.2f})")
    return Route(*head, "owner", "")


def classify_disagreements(items: list, env, run=subprocess.run,
                           opts: ClassifyOptions | None = None) -> Classified:
    """Route every finding; routes keep the input order."""
    opts = opts or ClassifyOptions()
    to_send = [f for f in items if f.matched]
    unmatched = {id(f): Route(f.title, f.severity, f.source, None, None, "owner",
                              "no unique report match")
                 for f in items if not f.matched}
    if not to_send:
        return Classified("not needed", [unmatched[id(f)] for f in items])
    entry = jev_names.find_jev(env, opts.own_root)
    if entry is None:
        status = "absent"
        by_id = {id(f): Route(f.title, f.severity, f.source, None, None, "owner", "jev absent")
                 for f in to_send}
    else:
        status = "asked"
        built = [finding_item(i, f, opts.kind) for i, f in enumerate(to_send)]
        answers = jev_names.ask_items(entry, built, env, run, strict=True)
        by_id = {
            id(f): route_for(f, answers.get(item["id"], (None, None, "no answer")), opts.limits)
            for f, item in zip(to_send, built, strict=True)
        }
    by_id.update(unmatched)
    return Classified(status, [by_id[id(f)] for f in items])


def _entry(route: Route) -> dict:
    out = {"title": route.title, "severity": route.severity, "source": route.source,
           "class": route.klass, "confidence": route.confidence}
    if route.note:
        out["reason"] = route.note
    return out


def cmd_classify_disagreements(args, deps) -> int:
    """Print the advisory routes (owner, fixer, skipped) as JSON."""
    try:
        with open(args.report, encoding="utf-8") as handle:
            report = handle.read()
        summary = ""
        if args.fix_summary:
            with open(args.fix_summary, encoding="utf-8") as handle:
                summary = handle.read()
    except OSError as error:
        print(f"classify-disagreements: {error}", file=sys.stderr)
        return 2
    if args.kind == "code" and _unparsed_summary(summary):
        print(NO_MATCH, file=sys.stderr)
        return 3
    # jev reads its project layer from the reviewed root, so the run starts there.
    result = classify_disagreements(
        disagreement_items(report, summary, args.cap_reached), deps.env_fn(),
        functools.partial(deps.run_fn, cwd=args.cwd),
        ClassifyOptions(limits=(args.iteration, args.cap), kind=args.kind),
    )
    out = {"jev": result.jev, "owner": [], "fixer": [], "skipped": []}
    for route in result.routes:
        out[route.route].append(_entry(route))
    if args.owner_out:
        try:
            for entry in out["owner"]:
                review_log.append_event(args.owner_out, entry)
        except OSError as error:
            print(f"classify-disagreements: {error}", file=sys.stderr)
            return 2
    print(json.dumps(out, indent=2))
    return 0


def _with_second_lane(inputs: SizeInput) -> list:
    """The rows a two-lane review would use: the configured rows plus the first lane of the
    resolver's double-mode pick that is not already a row."""
    if len(inputs.reviewers) >= 2:
        return list(inputs.reviewers)
    policy = dict(inputs.config.get("policy", {}), mode="double")
    config = dict(inputs.config, policy=policy)
    picked = quota.resolve_reviewers(
        config, routing.unroutable_quota(inputs.quota, inputs.routes), inputs.source_vendor,
        inputs.cross_ai, warn_fn=lambda _msg: None)
    present = {r["key"] for r in inputs.reviewers}
    extra = next((p for p in picked
                  if p.key not in present and p.key != quota.NO_CONFIG_FALLBACK.key), None)
    if extra is not None:
        row = extra._asdict()
        row["route"] = inputs.routes.get(row["key"], "native")
        return [*inputs.reviewers, row]
    return list(inputs.reviewers)


def _label(value, allowed: tuple) -> str:
    return value if value in allowed else "other"


def sizing_items(inputs: SizeInput, candidates: list) -> tuple:
    """(jev items, token -> lane key); only lanes that can end up in the rows are offered."""
    facts = review_signals.plan_facts(inputs.text)
    t, f, s, c = facts["tasks"], facts["files"], facts["steps"], facts["complexity"]
    ctx = (f"Plan facts: tasks {t}, files {f}, steps {s}, complexity {c}, "
           f"archetype {_label(inputs.archetype, ARCHETYPES)}, "
           f"framework {_label(inputs.framework, FRAMEWORKS)}. Signals: none.")
    items = [{"id": "lanes", "type": "choice", "instructions": LANES_QUESTION,
              "context": ctx, "criteria": dict(LANE_CRITERIA)}]
    tokens = {f"p{i + 1}": row["key"] for i, row in enumerate(candidates)}
    if len(tokens) >= 2:
        items.append({
            "id": "reviewer", "type": "choice", "instructions": REVIEWER_QUESTION,
            "context": ctx,
            "criteria": {token: f"candidate lane {token[1:]}" for token in tokens},
        })
    return items, tokens


def _apply_answers(inputs: SizeInput, answers: dict, candidates: list, tokens: dict) -> Sizing:
    lanes = answers.get("lanes", (None, None, "no answer"))
    if not _confident(lanes):
        return Sizing(list(inputs.reviewers), "jev low: configured count kept")
    choice, top, _reason = lanes
    if choice not in ("one", "two"):
        return Sizing(list(inputs.reviewers), "jev low: configured count kept")
    rows = list(candidates)
    pick = answers.get("reviewer", (None, None, "no answer"))
    if _confident(pick):
        first = next((r for r in rows if r["key"] == tokens.get(pick[0])), None)
        if first is not None:
            rows = [first] + [r for r in rows if r is not first]
    if choice == "one":
        rows = rows[:1]
    reason = f"jev {choice} ({top:.2f})"
    if choice == "two" and len(rows) == 1:
        reason += f"; {NO_SECOND}"
    return Sizing(rows, reason)


def size_review(inputs: SizeInput, env, run=subprocess.run, *, own_root=None) -> Sizing:
    """Deterministic signals force two lanes; otherwise jev, when present, sizes the review."""
    candidates = _with_second_lane(inputs)
    signals = review_signals.plan_signals(inputs.text, inputs.paths)
    if signals:
        names = ", ".join(signals)
        if len(candidates) >= 2:
            return Sizing(candidates, f"signal {names}")
        return Sizing(candidates, f"signal {names} wants two lanes; {NO_SECOND}")
    entry = jev_names.find_jev(env, own_root)
    if entry is None:
        return Sizing(list(inputs.reviewers), "jev absent: configured count kept")
    items, tokens = sizing_items(inputs, candidates)
    answers = jev_names.ask_items(entry, items, env, run, strict=True)
    return _apply_answers(inputs, answers, candidates, tokens)


def _read_size_inputs(args) -> tuple:
    """(reviewers, plan text) from the files the command names."""
    with open(args.reviewers_json, encoding="utf-8") as handle:
        reviewers = json.load(handle)
    parts = []
    for doc in args.doc:
        with open(doc, encoding="utf-8") as handle:
            parts.append(handle.read())
    return reviewers, "\n".join(parts)


def cmd_size_review(args, deps) -> int:
    """Size the review and rewrite reviewers.json only when the sizing changes the rows."""
    config = config_io.cfg_resolve(args.cwd, deps.env_fn(), migrate=False)
    try:
        reviewers, text = _read_size_inputs(args)
    except (OSError, ValueError) as error:
        print(f"size-review: {error}", file=sys.stderr)
        return 2
    inputs = SizeInput(
        config, reviewers, text, review_signals.plan_paths(text), args.archetype,
        args.framework, cache_read_json(args.quota_path) or {},
        lane_switch.review_routes(config, deps), args.source_vendor, args.cross_ai)
    # jev reads its project layer from the reviewed root, so the run starts there.
    sizing = size_review(inputs, deps.env_fn(), functools.partial(deps.run_fn, cwd=args.cwd))
    try:
        # The event goes first: a failed write then leaves reviewers.json unchanged.
        review_log.append_event(args.lane_log, {
            "round": 0,
            "sizing": {"lanes": len(sizing.reviewers),
                       "keys": [r["key"] for r in sizing.reviewers], "reason": sizing.reason},
            "at": time.time()})
        if sizing.reviewers != reviewers:
            lane_switch.write_rows(args.reviewers_json, sizing.reviewers)
    except OSError as error:
        print(f"size-review: {error}", file=sys.stderr)
        return 2
    print(f"sizing: {len(sizing.reviewers)} lane(s): {sizing.reason}")
    return 0


def execute_default(status: str) -> str:
    """The implementer status read as a lane-result class: the default without jev."""
    return {"DONE": "done", "DONE_WITH_CONCERNS": "partial"}.get(status, "another_round")


def handover_status(status: str, klass: str) -> str:
    """The status handed to subagent-driven-development: only a DONE report changes,
    to DONE_WITH_CONCERNS when the class is not done."""
    return "DONE_WITH_CONCERNS" if status == "DONE" and klass != "done" else status


def execute_item(facts: ExecuteFacts) -> dict:
    """One jev item built from allowlisted values only."""
    status = facts.status if facts.status in IMPLEMENTER_STATUSES else "other"
    runner = facts.runner_status if facts.runner_status in RUNNER_STATUSES else "none"
    codes = ", ".join(sorted({c for c in facts.findings if c in RUNNER_FINDING_CODES})) or "none"
    m = _COVERAGE_RE.fullmatch(facts.coverage)
    coverage = f"{int(m.group(1))}/{int(m.group(2))}" if m else "none"
    return {
        "id": "e0", "type": "choice", "instructions": EXECUTE_QUESTION,
        "context": (f"Implementer status: {status}. Runner status: {runner}. "
                    f"Runner findings: {codes}. Coverage: {coverage}."),
        "criteria": dict(EXECUTE_CRITERIA),
    }


def classify_execute_result(facts: ExecuteFacts, env, run=subprocess.run,
                            *, own_root=None) -> LaneClass:
    """jev's class for one execute result; the status default when jev is absent, low or
    not asked (any report but DONE)."""
    default = execute_default(facts.status)
    if not facts.status:
        return LaneClass(default, "default", None, "no lane result")
    if facts.status != "DONE":  # only a DONE report's handover can change
        return LaneClass(default, "default", None, "not a DONE report")
    entry = jev_names.find_jev(env, own_root)
    if entry is None:
        return LaneClass(default, "default", None, "jev absent")
    answer = jev_names.ask_items(
        entry, [execute_item(facts)], env, run, strict=True).get("e0", (None, None, "no answer"))
    if not _confident(answer) or answer[0] not in EXECUTE_CLASSES:
        return LaneClass(default, "default", answer[1], "jev low")
    return LaneClass(answer[0], "jev", answer[1], "")


def cmd_classify_execute_result(args, deps) -> int:
    """Print the advisory lane-result class as JSON and one log line."""
    facts = ExecuteFacts(args.status, args.runner_status,
                         tuple(c for c in args.findings.split(",") if c), args.coverage)
    # jev reads its project layer from the project root, so the run starts there.
    result = classify_execute_result(
        facts, deps.env_fn(), functools.partial(deps.run_fn, cwd=args.cwd))
    print(json.dumps({"class": result.klass, "decided_by": result.decided_by,
                      "confidence": result.confidence, "note": result.note,
                      "handover": handover_status(args.status, result.klass)}))
    print(f"ai-kit-spec: lane result: {result.klass} ({result.decided_by})", file=sys.stderr)
    return 0


def fit_item(index: int, finding: dict) -> dict:
    """One jev item built from the severity and the five labels only; no title, location,
    fix or reason text."""
    labels = code_review.finding_labels(finding)
    return {
        "id": f"f{index}", "type": "choice", "instructions": FIT_QUESTION,
        "context": (f"Severity: {finding.get('severity')}. Kind: {labels['kind']}. "
                    f"Test tier: {labels['tier']}. Reproducible: {labels['repro']}. "
                    f"End-user reach: {labels['reach']}. Stage: {labels['stage']}."),
        "criteria": dict(FIT_CRITERIA),
    }


def _fit_row(finding: dict, fit, decided_by: str, confidence, note: str) -> dict:
    """One fit row: the reviewer's severity, the fit class, and the severity it gives."""
    new, rule_note = code_review.fit_severity(finding.get("severity"), fit)
    return {"title": finding.get("title"), "severity": finding.get("severity"),
            "location": finding.get("location"), "new_severity": new, "fit": fit,
            "decided_by": decided_by, "confidence": confidence, "note": note or rule_note}


def classify_findings(findings: list, env, run=subprocess.run, *, own_root=None) -> tuple:
    """(jev status, one fit row per finding); a CRITICAL or HIGH finding is never lowered.
    A finding with no labels is not sent: the default row decides it."""
    if not findings:
        return "not needed", []

    def unsent_note(finding: dict) -> str:
        # a severity finding is left unsent only when it carries no labels
        return "no labels" if finding.get("severity") in code_review.SEVERITY_ORDER else ""

    sent = [i for i, f in enumerate(findings)
            if f.get("severity") in code_review.SEVERITY_ORDER
            and set(code_review.finding_labels(f).values()) != {"unknown"}]
    if not sent:
        return "not needed", [_fit_row(f, None, "default", None, unsent_note(f))
                              for f in findings]
    entry = jev_names.find_jev(env, own_root)
    if entry is None:
        return "absent", [_fit_row(f, None, "default", None, "jev absent") for f in findings]
    answers = jev_names.ask_items(
        entry, [fit_item(i, findings[i]) for i in sent], env, run, strict=True)
    rows = []
    for i, finding in enumerate(findings):
        if i not in sent:
            rows.append(_fit_row(finding, None, "default", None, unsent_note(finding)))
            continue
        answer = answers.get(f"f{i}", (None, None, "no answer"))
        if _confident(answer) and answer[0] in FIT_CLASSES:
            rows.append(_fit_row(finding, answer[0], "jev", answer[1], ""))
        else:
            rows.append(_fit_row(finding, None, "default", answer[1], "jev low"))
    return "asked", rows


def cmd_classify_findings(args, deps) -> int:
    """Print the fit rows' path and jev status; write the rows and the adjusted report."""
    try:
        with open(args.report, encoding="utf-8") as handle:
            text = handle.read()
        findings = code_review.normalize_report(text)
        status, rows = classify_findings(
            findings, deps.env_fn(), functools.partial(deps.run_fn, cwd=args.cwd))
        cache_write_text(args.out, json.dumps(rows, indent=2))
        # the rows go first: --out-report may name the report file itself
        cache_write_text(args.out_report, code_review.render_report(
            [{**f, "severity": r["new_severity"]} for f, r in zip(findings, rows, strict=True)]))
    except (OSError, ValueError) as error:
        print(f"classify-findings: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"out": args.out, "jev": status}))
    n_jev = sum(1 for row in rows if row.get("decided_by") == "jev")
    n_default = sum(1 for row in rows if row.get("decided_by") == "default")
    print(f"ai-kit-spec: finding fit: jev {n_jev}, default {n_default}", file=sys.stderr)
    return 0


def register_parsers(sub) -> None:
    """Register the review loop's jev commands."""
    parser = sub.add_parser(
        "classify-disagreements",
        help="ask jev, when present, to classify escalated, skipped or open findings "
             "before the owner is asked (advisory)",
    )
    parser.add_argument("--cwd", required=True, help="the reviewed root")
    parser.add_argument("--report", required=True, help="the merged review report")
    parser.add_argument("--fix-summary", default=None, help="the fixer's Fix Summary")
    parser.add_argument("--cap-reached", action="store_true",
                        help="also classify every report finding the summary does not name")
    parser.add_argument("--iteration", type=int, default=None)
    parser.add_argument("--cap", type=int, default=None)
    parser.add_argument("--kind", choices=("code", "document"), default="document",
                        help="code: a code-review finding; document: a spec or plan finding")
    parser.add_argument("--owner-out", default=None,
                        help="append each owner item as one JSON line to this file "
                             "(the host collects them for the final message)")
    sizer = sub.add_parser(
        "size-review",
        help="size the review: deterministic signals force two lanes, else jev (advisory) "
             "picks one or two lanes and the first reviewer",
    )
    sizer.add_argument("--cwd", required=True, help="the reviewed root")
    sizer.add_argument("--reviewers-json", required=True, help="the reviewers.json to size")
    sizer.add_argument("--doc", action="append", required=True, help="a plan document to read")
    sizer.add_argument("--archetype", required=True)
    sizer.add_argument("--framework", required=True)
    sizer.add_argument("--lane-log", required=True, help="the lane log to append the event to")
    sizer.add_argument("--quota-path", required=True, help="the quota cache of Step 0.7")
    sizer.add_argument("--source-vendor", default="",
                       help="the value passed to resolve-reviewers")
    sizer.add_argument("--cross-ai", action="store_true",
                       help="the flag passed to resolve-reviewers")
    executor = sub.add_parser(
        "classify-execute-result",
        help="ask jev, when present, whether an execute lane's run is done, partial or needs "
             "another round (advisory)",
    )
    executor.add_argument("--cwd", required=True, help="the project root")
    executor.add_argument("--status", required=True, help="the implementer status token")
    executor.add_argument("--runner-status", default="", help="the runner's status token")
    executor.add_argument("--findings", default="",
                          help="the runner's finding codes, comma-separated")
    executor.add_argument("--coverage", default="",
                          help="the runner's coverage, covered/planned")
    fitter = sub.add_parser(
        "classify-findings",
        help="ask jev, when present, whether each code-review finding's severity fits "
             "(advisory; CRITICAL and HIGH are never lowered)",
    )
    fitter.add_argument("--cwd", required=True, help="the project root")
    fitter.add_argument("--report", required=True,
                        help="one normalized report: a lane's or the session model's")
    fitter.add_argument("--out", required=True, help="the fit rows file")
    fitter.add_argument("--out-report", required=True,
                        help="the normalized report with the fit applied; "
                             "may be the --report file")


COMMANDS = {
    "classify-disagreements": cmd_classify_disagreements,
    "size-review": cmd_size_review,
    "classify-execute-result": cmd_classify_execute_result,
    "classify-findings": cmd_classify_findings,
}
