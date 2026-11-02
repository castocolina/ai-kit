"""Reproduce the 27-SKILL-JUDGE.md verdict and gate from the committed skill-judge reports.

Usage (from the repository root):
  check_verdicts.py <phase-dir> [--gate]   prints `verdicts ok` (and `gate ok` / `gate pending: ...`)
  check_verdicts.py --self-test            prints `self-test ok`; reads no files
Stdlib only; the status-line parser below is a copy so the checker imports no other skill.
"""

import glob
import hashlib
import json
import os
import re
import subprocess
import sys

SKILL = "ai-kit-spec-goal-prompt"
DIMS = [f"D{i}" for i in range(1, 9)]
KEYS = {"skill", "judge", "rubric_version", "spec_sha", "scores", "max", "total", "max_total",
        "percent", "grade", "findings"}
FINDING_KEYS = {"id", "dimension", "severity", "file", "line", "evidence", "fix"}
SEVERITIES = {"critical", "high", "medium", "low"}
# Every judge runs through pi; there is no Opus entry (owner rule, 2026-10-31).
JUDGES = {"my-referee-one": "router-env/my-referee-one",
          "my-referee-two": "router-env/my-referee-two",
          "my-referee-three": "router-env/my-referee-three"}
_STATUS_PREFIX = "AIKIT-XAI "


def parse_status_line(line):
    """The `key=value` tokens of an `AIKIT-XAI ` line, or None for anything else."""
    if not line.startswith(_STATUS_PREFIX):
        return None
    return dict(token.split("=", 1) for token in line.split() if "=" in token)


def grade_of(pct):
    return "A" if pct >= 90 else "B" if pct >= 80 else "C" if pct >= 70 else "D" if pct >= 60 else "F"


def validate_verdict(v, rubric):
    """Errors of one verdict object against verdict.schema.json (hand-checked) and its arithmetic."""
    if not isinstance(v, dict) or set(v) != KEYS:
        return ["keys are not exactly the schema's"]
    errs = []
    for name in ("scores", "max"):
        d = v[name]
        if not isinstance(d, dict) or set(d) != set(DIMS) or not all(
                type(x) is int and x >= 0 for x in d.values()):
            return [name + " is not exactly D1..D8 integers"]
    if type(v["total"]) is not int or type(v["max_total"]) is not int or type(v["rubric_version"]) is not int:
        return ["total, max_total and rubric_version must be integers"]
    if not isinstance(v["spec_sha"], str) or not re.fullmatch(r"[0-9a-f]{40}", v["spec_sha"]):
        errs.append("spec_sha is not 40 hex")
    if (v["rubric_version"], v["spec_sha"]) != rubric:
        errs.append("rubric_version/spec_sha differ from the Rubric: line")
    if sum(v["scores"].values()) != v["total"]:
        errs.append("sum(scores) %d != total %d" % (sum(v["scores"].values()), v["total"]))
    if sum(v["max"].values()) != v["max_total"]:
        errs.append("sum(max) %d != max_total %d" % (sum(v["max"].values()), v["max_total"]))
    if any(v["scores"][d] > v["max"][d] for d in DIMS):
        errs.append("a score exceeds its max")
    if not isinstance(v["percent"], (int, float)) or v["max_total"] <= 0:
        return errs + ["percent or max_total unusable"]
    pct = round(v["total"] / v["max_total"] * 100, 1)
    if v["percent"] != pct:
        errs.append("percent %s != %s" % (v["percent"], pct))
    if v["grade"] != grade_of(pct):
        errs.append("grade %s != %s" % (v["grade"], grade_of(pct)))
    if not isinstance(v["findings"], list):
        return errs + ["findings is not a list"]
    for f in v["findings"]:
        if (not isinstance(f, dict) or set(f) != FINDING_KEYS or f["severity"] not in SEVERITIES
                or f["dimension"] not in DIMS
                or not (f["line"] is None or (type(f["line"]) is int and f["line"] >= 1))
                or not all(isinstance(f[k], str) and f[k] for k in ("id", "file", "evidence", "fix"))):
            errs.append("a finding is malformed")
            break
    return errs


def self_test():
    rubric = (4, "a" * 40)
    good = {"skill": SKILL, "judge": "my-referee-two", "rubric_version": 4, "spec_sha": "a" * 40,
            "scores": {d: 10 for d in DIMS}, "max": {d: 15 for d in DIMS}, "total": 80,
            "max_total": 120, "percent": 66.7, "grade": "D", "findings": []}
    assert validate_verdict(good, rubric) == [], validate_verdict(good, rubric)
    assert validate_verdict(dict(good, percent=70.0), rubric), "wrong percent passed"
    assert validate_verdict(dict(good, grade="B"), rubric), "wrong grade passed"
    short = dict(good, scores={d: 10 for d in DIMS[:-1]})
    assert validate_verdict(short, rubric), "missing dimension passed"
    print("self-test ok")


def num(b, k):
    m = re.search(r"^" + re.escape(k) + r": (\d+)$", b, re.M)
    assert m, k
    return int(m.group(1))


def pkg():
    """sha256 over `<sha256 of file>  <path>\\n` of every tracked file of the skill, sorted."""
    files = sorted(subprocess.check_output(["git", "ls-files", "--", "skills/" + SKILL],
                                           text=True).split())
    return hashlib.sha256("".join(
        hashlib.sha256(open(f, "rb").read()).hexdigest() + "  " + f + "\n" for f in files
    ).encode()).hexdigest()


def verdict_of(r):
    m = re.search(r"^Verdict: (\{.*\})$", r, re.M)
    return json.loads(m.group(1)) if m else None


def lane_ok(r, j):
    assert re.search(r"^Judge: " + re.escape(j) + r"$", r, re.M), "Judge line is not " + j
    m = re.search(r"^Lane: (.+)$", r, re.M)
    assert m, "no Lane line: " + j
    d = parse_status_line(m.group(1).strip())
    assert d and d.get("cli") == "pi" and d.get("model") == JUDGES[j], "Lane line is not a pi " + JUDGES[j] + " lane"
    return d.get("status") == "ok" and d.get("exit") == "0"


def finished(r, j, rubric):
    """True for a finished lane whose verdict reproduces; header numbers must equal the JSON."""
    ok = lane_ok(r, j)
    v = verdict_of(r)
    errs = validate_verdict(v, rubric) if ok and v else ["no verdict"]
    has_score = bool(re.search(r"^Score: \d+$", r, re.M))
    if not ok or errs:
        assert not has_score, "an unfinished or invalid report has no Score line: " + j
        assert ok is False or "invalid verdict" in r or not v, "an invalid verdict must say so: " + j
        return False
    assert has_score, "a finished report needs a Score line: " + j
    assert v["judge"] == j and v["skill"] == SKILL, "verdict names another judge or skill: " + j
    crit = sum(f["severity"] == "critical" for f in v["findings"])
    imp = sum(f["severity"] == "high" for f in v["findings"])
    assert (num(r, "Score"), num(r, "Max"), num(r, "Critical"), num(r, "Important")) == (
        v["total"], v["max_total"], crit, imp), "header numbers differ from the verdict JSON: " + j
    assert re.search(r"^Percent: " + re.escape(str(v["percent"])) + r"$", r, re.M), "Percent header: " + j
    assert re.search(r"^Grade: " + v["grade"] + r"$", r, re.M), "Grade header: " + j
    return True


def main(argv):
    if "--self-test" in argv:
        return self_test()
    j_dir, gate = argv[0], "--gate" in argv[1:]
    t = open(j_dir + "/27-SKILL-JUDGE.md", encoding="utf-8").read()
    m = re.search(r"^Rubric: version (\d+), spec_sha ([0-9a-f]{40})$", t, re.M)
    assert m, "no Rubric: line"
    rubric = (int(m.group(1)), m.group(2))

    def report(rnd, j):
        p = "%s/skill-judge/r%d/%s-%s.md" % (j_dir, rnd, SKILL, j)
        return open(p, encoding="utf-8").read() if os.path.isfile(p) else None

    rounds = sorted(int(os.path.basename(p)[1:]) for p in glob.glob(j_dir + "/skill-judge/r*")
                    if os.path.basename(p)[1:].isdigit())
    # The original loop is capped at three rounds. Rounds 4 to 6 exist only as post-review
    # confirmations (orchestrator decision; round 6 adds a second judge), and must be labelled so.
    assert rounds == list(range(1, len(rounds) + 1)) and len(rounds) <= 6, "rounds must be r1..r<=6"
    extra = ",".join(str(n) for n in rounds if n > 3)
    lab = re.search(r"^Post-review confirmation rounds: (\S+)$", t, re.M)
    assert (lab.group(1) if lab else "") == extra, "rounds above 3 need the label line: " + extra
    base = None
    for n in rounds:  # a new skill has no earlier baseline: the lowest finished percent of round 1
        fin = [verdict_of(r)["percent"] for j in JUDGES for r in [report(n, j)] if r and finished(r, j, rubric)]
        if fin:
            base = min(fin)
            break
    blocks = {mm.group(1): mm.group(2) for mm in re.finditer(r"^Skill: (\S+)\n((?:.+\n?)*)", t, re.M)}
    assert list(blocks) == [SKILL], list(blocks)
    b = blocks[SKILL]
    v = re.search(r"^Verdict: (PASS|UNRESOLVED|FAIL|BLOCKED)$", b, re.M).group(1)
    rnd = num(b, "Round")
    last = max([k for k in rounds if any(report(k, j) for j in JUDGES)] or [0])
    assert rnd == last, "verdict cites round %d, its latest judged round is %d" % (rnd, last)
    sha = re.search(r"^Reviewed-sha256: ([0-9a-f]{64})$", b, re.M).group(1)
    assert sha == pkg(), "stale verdict: the package changed after round %d; a re-judge round is the only route" % rnd
    reps = {j: r for j in JUDGES for r in [report(rnd, j)] if r}
    assert reps, "missing report"
    for j, r in reps.items():
        assert re.search(r"^Reviewed-sha256: " + sha + r"$", r, re.M), "report digest " + j
    fin = {j: r for j, r in reps.items() if finished(r, j, rubric)}
    if not fin:
        assert v == "BLOCKED", "no finished lane needs BLOCKED"
    else:
        low = min(fin.values(), key=lambda r: verdict_of(r)["percent"])
        pct = verdict_of(low)["percent"]
        crit = max(sum(f["severity"] == "critical" for f in verdict_of(r)["findings"]) for r in fin.values())
        imp = max(sum(f["severity"] == "high" for f in verdict_of(r)["findings"]) for r in fin.values())
        assert (num(b, "Critical findings"), num(b, "Important findings")) == (crit, imp), "severity counts"
        sc = re.search(r"^Score: (\d+)/(\d+)$", b, re.M)
        assert sc and (int(sc.group(1)), int(sc.group(2))) == (
            verdict_of(low)["total"], verdict_of(low)["max_total"]), "lowest score"
        assert re.search(r"^Percent: " + re.escape(str(pct)) + r"$", b, re.M), "percent"
        assert re.search(r"^Grade: " + grade_of(pct) + r"$", b, re.M), "grade"
        assert re.search(r"^Base percent: " + re.escape(str(base)) + r"$", b, re.M), "base percent must be %s" % base
        rule = (crit == 0 and imp == 0) or pct >= 80
        want = "FAIL" if not rule else ("PASS" if pct >= base else "UNRESOLVED")
        assert v == want, "verdict %s, reports give %s" % (v, want)
    sec = t.split("\n## Refuted findings\n", 1)[1].split("\n## ", 1)[0] if "\n## Refuted findings\n" in t else None
    assert sec is not None, "no Refuted findings section"
    for ln in sec.splitlines():
        if ln.startswith("- "):
            assert re.search(r"\S+:\d+", ln), "refuted finding without path:line: " + ln
    print("verdicts ok")
    if gate:
        osec = t.split("\n## Owner decisions\n", 1)[1].split("\n## ", 1)[0] if "\n## Owner decisions\n" in t else ""
        owner = set(re.findall(r"^Owner-decision: (\S+) accepts (PASS|UNRESOLVED|FAIL|BLOCKED) \(.+\)$", osec, re.M))
        if v != "PASS" and (SKILL, v) not in owner:
            print("gate pending: %s %s" % (SKILL, v))
            sys.exit(1)
        print("gate ok")


if __name__ == "__main__":
    main(sys.argv[1:])
