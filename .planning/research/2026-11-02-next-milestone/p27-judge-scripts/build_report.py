"""Build one skill-judge report file from a cross-ai lane's output.

Usage: build_report.py <judge> <lane-output-file...> --sha <sha256> --out <report path>
The lane output files (stdout and stderr of cross-ai.mjs) are scanned for the AIKIT-XAI status
line and for the verdict JSON line. The header numbers come from the verdict JSON.
"""

import json
import sys

args = sys.argv[1:]
judge = args[0]
sha = args[args.index("--sha") + 1]
out = args[args.index("--out") + 1]
files = [a for a in args[1:args.index("--sha")]]

lines = []
for name in files:
    with open(name, encoding="utf-8", errors="replace") as handle:
        lines += handle.read().splitlines()
status = [ln for ln in lines if ln.startswith("AIKIT-XAI ")]
verdicts = [ln.strip() for ln in lines if ln.strip().startswith('{"skill"')]
lane = status[-1] if status else "AIKIT-XAI status=missing"
head = [f"Judge: {judge}", f"Lane: {lane}", f"Reviewed-sha256: {sha}"]
if verdicts:
    v = json.loads(verdicts[-1])
    crit = sum(f["severity"] == "critical" for f in v["findings"])
    imp = sum(f["severity"] == "high" for f in v["findings"])
    head += [f"Score: {v['total']}", f"Max: {v['max_total']}", f"Percent: {v['percent']}",
             f"Grade: {v['grade']}", f"Critical: {crit}", f"Important: {imp}",
             f"Verdict: {verdicts[-1]}", "", verdicts[-1]]
with open(out, "w", encoding="utf-8") as handle:
    handle.write("\n".join(head))
print("\n".join(head[:9]))
