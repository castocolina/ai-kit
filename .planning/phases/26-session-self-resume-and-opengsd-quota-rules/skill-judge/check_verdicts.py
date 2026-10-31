import glob, hashlib, os, re, sys
sys.path.insert(0, "skills/ai-kit-spec-review")
from ai_kit_spec.runner_dispatch import parse_status_line
J = sys.argv[1]
GATE = "--gate" in sys.argv[2:]
SUMMARY = "--summary" in sys.argv[2:]
SKILLS = ["ai-kit-session-wake", "ai-kit-spec-execute-gsd", "ai-kit-spec-execute-superpowers", "ai-kit-project-rules-agents", "ai-kit-project-rules-all"]
# Judge sets differ by round (owner changes of 2026-10-30): rounds 1-3 ran the native Opus
# subagent plus referee-one and referee-two through opencode; later rounds ran referee-two
# and referee-three through pi, with no native Opus. A round counts every finished lane it has.
JUDGES = {"opus": None, "my-referee-one": "router-env/my-referee-one",
          "my-referee-two": "router-env/my-referee-two", "my-referee-three": "router-env/my-referee-three"}
# Base scores; the source of each is the comment. session-wake is computed below.
BASE = {
    "ai-kit-spec-execute-gsd": 105,  # 25.1-SKILL-JUDGE.md round 5
    "ai-kit-spec-execute-superpowers": 110,  # 25.1-SKILL-JUDGE.md, carried from Phase 18.1
    "ai-kit-project-rules-agents": 99,  # 16.1-SKILL-JUDGE-independent.md
    "ai-kit-project-rules-all": 95,  # 16.1-SKILL-JUDGE-independent.md
}
def pkg(n):
    r = "skills/" + n + "/"
    fs = sorted(["SKILL.md"] + [os.path.relpath(p, r) for p in glob.glob(r + "references/**/*.md", recursive=True)])
    return hashlib.sha256("".join(hashlib.sha256(open(r + f, "rb").read()).hexdigest() + "  " + f + "\n" for f in fs).encode()).hexdigest()
def num(b, k):
    m = re.search(r"^" + k + r": (\d+)$", b, re.M)
    assert m, k
    return int(m.group(1))
def report(n, rnd, j):
    p = "%s/skill-judge/r%d/%s-%s.md" % (J, rnd, n, j)
    return open(p, encoding="utf-8").read() if os.path.isfile(p) else None
def done(r, j):
    assert re.search(r"^Judge: " + re.escape(j) + r"$", r, re.M), "Judge line is not " + j
    m = re.search(r"^Lane: (.+)$", r, re.M)
    assert m, "no Lane line: " + j
    lane = m.group(1).strip()
    if JUDGES[j] is None:
        assert lane.startswith("native subagent "), "the opus report needs a native Lane line"
        ok = lane == "native subagent completed"
    else:
        d = parse_status_line(lane)
        assert d and d.get("cli") in ("opencode", "pi") and d.get("model") == JUDGES[j], "Lane line is not an opencode or pi " + JUDGES[j] + " lane: " + j
        ok = d.get("status") == "ok" and d.get("exit") == "0"
    assert ok == bool(re.search(r"^Score: \d+$", r, re.M)), "a finished lane has a Score line and an unfinished one has none: " + j
    return ok
rounds = sorted(int(os.path.basename(p)[1:]) for p in glob.glob(J + "/skill-judge/r*") if os.path.basename(p)[1:].isdigit())
for n in rounds:
    fin = [num(r, "Score") for j in JUDGES for r in [report("ai-kit-session-wake", n, j)] if r and done(r, j)]
    if fin:
        BASE["ai-kit-session-wake"] = min(fin)  # the lowest score of its first finished round
        break
t = open(J + "/26-SKILL-JUDGE.md", encoding="utf-8").read()
blocks = {m.group(1): m.group(2) for m in re.finditer(r"^Skill: (\S+)\n((?:.+\n?)*)", t, re.M)}
assert sorted(blocks) == sorted(SKILLS), sorted(blocks)
for n, b in blocks.items():
    v = re.search(r"^Verdict: (PASS|UNRESOLVED|FAIL|BLOCKED)$", b, re.M).group(1)
    rnd = num(b, "Round")
    last = max([k for k in rounds if any(report(n, k, j) for j in JUDGES)] or [0])
    assert rnd == last, "verdict " + n + " cites round " + str(rnd) + ", its latest judged round is " + str(last)
    sha = re.search(r"^Reviewed-sha256: ([0-9a-f]{64})$", b, re.M).group(1)
    assert sha == pkg(n), "stale verdict " + n + ": the package changed after round " + str(rnd) + "; a re-judge round is the only route"
    reps = {j: report(n, rnd, j) for j in JUDGES}
    reps = {j: r for j, r in reps.items() if r}
    assert reps, "missing report " + n
    for j, r in reps.items():
        assert re.search(r"^Reviewed-sha256: " + sha + r"$", r, re.M), "report digest " + n + " " + j
    fin = {j: r for j, r in reps.items() if done(r, j)}
    if not fin:
        assert v == "BLOCKED", "no finished lane needs BLOCKED: " + n
        continue
    sc = num(b, "Score")
    assert sc == min(num(r, "Score") for r in fin.values()), "lowest score " + n
    assert num(b, "Critical findings") == max(num(r, "Critical") for r in fin.values()), "highest critical " + n
    assert num(b, "Important findings") == max(num(r, "Important") for r in fin.values()), "highest important " + n
    assert num(b, "Base score") == BASE[n], "base " + n + " must be " + str(BASE.get(n))
    rule = (num(b, "Critical findings") == 0 and num(b, "Important findings") == 0) or sc >= 96
    want = "FAIL" if not rule else ("PASS" if sc >= BASE[n] else "UNRESOLVED")
    assert v == want, "verdict " + n + ": " + v + ", reports give " + want
print("verdicts ok")
if SUMMARY:  # percentage and grade per skill, from the skill-judge scale (A 90%+, B 80-89, C 70-79, D 60-69, F <60)
    for n, b in blocks.items():
        if re.search(r"^Score: (\d+)$", b, re.M):
            sc = num(b, "Score")
            pct = round(sc * 100 / 120)
            grade = "A" if sc * 100 >= 90 * 120 else "B" if sc * 100 >= 80 * 120 else "C" if sc * 100 >= 70 * 120 else "D" if sc * 100 >= 60 * 120 else "F"
            bs = num(b, "Base score")
            print("%s: %d/120 = %d%% grade %s; base %d/120 = %d%%; %s" % (n, sc, pct, grade, bs, round(bs * 100 / 120), re.search(r"^Verdict: (\S+)$", b, re.M).group(1)))
if GATE:
    owner = set(re.findall(r"^Owner-decision: (\S+) accepts (PASS|UNRESOLVED|FAIL|BLOCKED) \(.+\)$", t.split("\n## Owner decisions\n", 1)[1].split("\n## ", 1)[0] if "\n## Owner decisions\n" in t else "", re.M))
    pend = []
    for n, b in blocks.items():
        v = re.search(r"^Verdict: (\S+)$", b, re.M).group(1)
        if v != "PASS" and (n, v) not in owner:
            pend.append("gate pending: %s %s" % (n, v))
    if pend:
        print("\n".join(pend))
        sys.exit(1)
    print("gate ok")
