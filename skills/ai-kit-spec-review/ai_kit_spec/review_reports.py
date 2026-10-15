import re

# ── Findings merge (review-spec/SKILL.md's Step 1.5 double-review reconciliation) ──

_SEVERITY_HEADINGS = {
    "CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW",
    "Cross-Document Consistency": "CROSS-DOC",
}
_SEVERITY_RE = re.compile(
    r"^### (CRITICAL|HIGH|MEDIUM|LOW|Cross-Document Consistency)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(
    r"^- \*\*(.+?)\*\* — Location: (.+?)\. Required: (.+?)\. Why: (.+?)\.\s*$",
    re.MULTILINE)


_STATUS_LINE_RE = re.compile(r"^### Status:\s*(.*)$", re.MULTILINE)


def report_status(report_text: str) -> str | None:
    """The report's declared status, from its LAST `### Status:` line (a report with
    two is malformed; the last one wins). Closed vocabulary (D-12): "approved" for a
    lowercase value starting `approved`; "failure" for one starting `failure`; anything
    else on a Status line ("issues found", unknown text) reads "issues"; no Status line
    at all returns None. Used by the merge-reports CLI subcommand (D-12/R7) so a failed
    or missing review lane can never merge into a false Approved."""
    matches = _STATUS_LINE_RE.findall(report_text)
    if not matches:
        return None
    value = matches[-1].strip().lower()
    if value.startswith("approved"):
        return "approved"
    if value.startswith("failure"):
        return "failure"
    return "issues"

def parse_findings(report_text: str) -> list:
    """[{severity, title, location, required, why}] in document order, per
    the review-spec-checklist output template (`### SEVERITY` headings —
    `CRITICAL`/`HIGH`/`MEDIUM`/`LOW`, plus `### Cross-Document Consistency`
    normalized to the `"CROSS-DOC"` severity tag — followed by
    `- **title** — Location: .... Required: .... Why: ....` bullets).
    `LOW` is recognized because a plan-archetype review may legitimately
    emit it (review-spec-checklist's Plan checklist defines a LOW/Tooling-
    Catchable tier); without recognizing it, its bullets would fall
    through to severity None and get silently re-labeled MEDIUM by
    `render_merged_report`, escalating severity that was never intended.
    A bullet appearing before any recognized heading (malformed input)
    still gets severity None."""
    sev_matches = list(_SEVERITY_RE.finditer(report_text))
    findings = []
    for m in _BULLET_RE.finditer(report_text):
        pos = m.start()
        severity = None
        for i, sm in enumerate(sev_matches):
            nxt = sev_matches[i + 1].start() if i + 1 < len(sev_matches) else len(report_text)
            if sm.start() <= pos < nxt:
                severity = _SEVERITY_HEADINGS[sm.group(1)]
                break
        findings.append({"severity": severity, "title": m.group(1), "location": m.group(2),
                          "required": m.group(3), "why": m.group(4)})
    return findings


def merge_findings(reports: list) -> list:
    """reports: [(reviewer_key, report_text), ...]. Union of every finding,
    each tagged with which reviewer(s) surfaced it. Findings sharing the
    exact same (severity, location) ACROSS DIFFERENT reports are combined
    into one entry with both reviewers tagged — deliberately NOT fuzzy
    title-text matching (two models rarely word the same finding
    identically), so this only merges the case where they flag literally
    the same passage. Within a single report, two distinct findings that
    happen to share a (severity, location) — e.g. two separate HIGH issues
    both in "§3" — are never collapsed into each other: only the first
    occurrence per report claims the bare (severity, location) key; any
    later same-report finding at that same key is disambiguated by adding
    its own title into the key, so it always survives as its own entry."""
    merged = {}
    order = []
    for key, text in reports:
        seen_this_report = set()
        for f in parse_findings(text):
            dedup_key = (f["severity"], f["location"])
            if dedup_key in seen_this_report:
                dedup_key = (f["severity"], f["location"], f["title"])
            seen_this_report.add((f["severity"], f["location"]))
            if dedup_key in merged:
                merged[dedup_key]["reviewers"].append(key)
            else:
                entry = dict(f)
                entry["reviewers"] = [key]
                merged[dedup_key] = entry
                order.append(dedup_key)
    return [merged[k] for k in order]


def render_merged_report(findings: list, doc_paths: str, any_source_issues: bool = False) -> str:
    """Renders CRITICAL/HIGH/MEDIUM/LOW under their own headings and
    CROSS-DOC findings under the same `### Cross-Document Consistency`
    heading the source reports use (never a raw `### CROSS-DOC`, which
    isn't part of the output template). A finding whose severity didn't
    match any recognized heading (malformed input — e.g. a bullet before
    any `### SEVERITY` heading) falls back to MEDIUM, tagged exactly as
    parsed — this can only happen on non-conforming input, since
    the merge-reports CLI subcommand already filters those out (via
    report_status) before this function ever runs. Deliberately
    drops each source report's own
    `### Document Type`/`### Files Read` lines — those describe a single
    reviewer's run, not a property of the merge — in favor of a fixed
    `cross-ai merged` marker.

    `any_source_issues` (from `report_status` on each raw source
    report, computed by the caller) is OR'd into the parsed-findings-based
    status: a report can legitimately say "Issues Found" while containing
    a bullet `_BULLET_RE` fails to parse (wrapped line, off-template
    punctuation), and without this the merge would silently downgrade that
    to "Approved" purely because no *parsed* finding survived."""
    by_sev = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": [], "CROSS-DOC": []}
    for f in findings:
        sev = f["severity"] if f["severity"] in by_sev else "MEDIUM"
        by_sev[sev].append(f)
    lines = [f"## Review: {doc_paths}", "### Document Type", "cross-ai merged"]
    any_issues = any(by_sev.values()) or any_source_issues
    heading_for = {"CRITICAL": "### CRITICAL", "HIGH": "### HIGH", "MEDIUM": "### MEDIUM",
                   "LOW": "### LOW", "CROSS-DOC": "### Cross-Document Consistency"}
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "CROSS-DOC"):
        items = by_sev.get(sev, [])
        if not items:
            continue
        lines.append(heading_for[sev])
        for f in items:
            tag = ", ".join(f["reviewers"])
            lines.append(f"- **{f['title']}** — Location: {f['location']}. "
                          f"Required: {f['required']}. Why: {f['why']}. (Reviewers: {tag})")
    lines.append(
        "### Status: Issues Found — fix and re-invoke" if any_issues else "### Status: Approved"
    )
    return "\n".join(lines) + "\n"
