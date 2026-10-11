set -euo pipefail
skill=~/.claude/skills/jev-fast-decision
cp "$skill/scripts/jev_review.py" "$skill/notes/jev_review.py.before-calibrate"
python3 -B "$skill/scripts/eval_cases.py" --calibrate | tee "$skill/notes/calibration.json"
python3 -B -c 'import json,pathlib,re,sys; h=pathlib.Path.home()/".claude/skills/jev-fast-decision"; p=json.loads((h/"notes/calibration.json").read_text())["JEV_MIN_CONFIDENCE"]; a=(h/"scripts/jev_review.py").read_text(); b=(h/"notes/jev_review.py.before-calibrate").read_text()
for n,w in p.items():
    if w is None: continue
    pat="\""+n+"\": \\{.*?\"min_confidence\": (\\d+(?:\\.\\d+)?)"; aa,bb=re.findall(pat,a,flags=re.S),re.findall(pat,b,flags=re.S)
    if len(aa)!=1 or float(aa[0])!=w or len(bb)!=1: sys.exit(n)'
uv run --no-project --with pytest pytest "$skill/tests" -q
