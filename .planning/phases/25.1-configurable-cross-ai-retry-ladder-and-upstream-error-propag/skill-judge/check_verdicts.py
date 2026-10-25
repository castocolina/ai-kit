import glob, hashlib, os, re, sys
sys.path.insert(0, "skills/ai-kit-spec-review")
from ai_kit_spec.runner_dispatch import parse_status_line
J = sys.argv[1]
SKILLS = ["ai-kit-cross-ai", "ai-kit-spec-review", "ai-kit-spec-execute-gsd", "ai-kit-spec-execute-superpowers", "ai-kit-gsd-curated-config", "ai-kit-spec-config"]
JUDGES = {"opus": None, "my-referee-one": "router-env/my-referee-one", "my-referee-two": "router-env/my-referee-two"}
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
        assert d and d.get("cli") == "opencode" and d.get("model") == JUDGES[j], "Lane line is not the opencode " + JUDGES[j] + " lane: " + j
        ok = d.get("status") == "ok" and d.get("exit") == "0"
    assert ok == bool(re.search(r"^Score: \d+$", r, re.M)), "a finished lane has a Score line and an unfinished one has none: " + j
    return ok
p25 = open(".planning/phases/25-quota-aware-cross-ai-subprocess-supervision/25-SKILL-JUDGE.md", encoding="utf-8").read()
BASE = {m.group(1): int(m.group(2)) for m in re.finditer(r"^Skill: (\S+)\nVerdict: \S+\nBase score: (\d+)$", p25, re.M)}
assert sorted(BASE) == sorted(SKILLS[1:5]), BASE
s18 = open(".planning/phases/18.1-one-runtime-model/18.1-SKILL-JUDGE.md", encoding="utf-8").read().split("\n## ai-kit-spec-config\n", 1)[1].split("\n## ", 1)[0]
BASE["ai-kit-spec-config"] = min(int(m.group(1)) for m in re.finditer(r"^\|[^|\n]*\|[^|\n]*\| (\d+)/120 \|[^|\n]*\|[^|\n]*\| PASS \|", s18, re.M))
rounds = sorted(int(os.path.basename(p)[1:]) for p in glob.glob(J + "/skill-judge/r*") if os.path.basename(p)[1:].isdigit())
for n in rounds:
    fin = [num(r, "Score") for j in JUDGES for r in [report("ai-kit-cross-ai", n, j)] if r and done(r, j)]
    if fin:
        BASE["ai-kit-cross-ai"] = min(fin)
        break
t = open(J + "/25.1-SKILL-JUDGE.md", encoding="utf-8").read()
blocks = {m.group(1): m.group(2) for m in re.finditer(r"^Skill: (\S+)\n((?:.+\n?)*)", t, re.M)}
assert sorted(blocks) == sorted(SKILLS), sorted(blocks)
for n, b in blocks.items():
    v = re.search(r"^Verdict: (PASS|UNRESOLVED|FAIL|BLOCKED)$", b, re.M).group(1)
    rnd = num(b, "Round")
    last = max([k for k in rounds if any(report(n, k, j) for j in JUDGES)] or [0])
    assert rnd == last, "verdict " + n + " cites round " + str(rnd) + ", its latest judged round is " + str(last)
    sha = re.search(r"^Reviewed-sha256: ([0-9a-f]{64})$", b, re.M).group(1)
    assert sha == pkg(n), "stale verdict " + n + ": the package changed after round " + str(rnd) + "; a re-judge round is the only route"
    reps = [report(n, rnd, j) for j in JUDGES]
    assert all(reps), "missing report " + n
    for j, r in zip(JUDGES, reps):
        assert re.search(r"^Reviewed-sha256: " + sha + r"$", r, re.M), "report digest " + n + " " + j
    if not all([done(r, j) for j, r in zip(JUDGES, reps)]):
        assert v == "BLOCKED", "unfinished lane needs BLOCKED: " + n
        continue
    sc = num(b, "Score")
    assert sc == min(num(r, "Score") for r in reps), "lowest score " + n
    assert num(b, "Critical findings") == max(num(r, "Critical") for r in reps), "highest critical " + n
    assert num(b, "Important findings") == max(num(r, "Important") for r in reps), "highest important " + n
    assert num(b, "Base score") == BASE[n], "base " + n + " must be " + str(BASE.get(n))
    rule = (num(b, "Critical findings") == 0 and num(b, "Important findings") == 0) or sc >= 96
    want = "FAIL" if not rule else ("PASS" if sc >= BASE[n] else "UNRESOLVED")
    assert v == want, "verdict " + n + ": " + v + ", reports give " + want
print("verdicts ok")
