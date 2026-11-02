"""Throwaway probe: render the long-goal eval scenario through the real CLI and print the result."""

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tests.test_ai_kit_spec_goal_prompt_evals import run_cli, stage_captures, stage_project

OBJECTIVE = sys.argv[1] if len(sys.argv) > 1 else "x"
STYLE = sys.argv[2] if len(sys.argv) > 2 else None

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    home = root / "home"
    home.mkdir()
    repo = stage_project("opengsd-mixed", root / "repo")
    caps = stage_captures(root / "caps", repo)
    detect = run_cli("detect", "--repo", str(repo), "--work-set", "phases:16-18",
                     "--roadmap", str(caps / "roadmap.json"),
                     "--identity", str(caps / "identity.json"),
                     "--phase-op", str(caps / "phase-op"), "--tools", "", home=str(home))
    print("detect rc", detect.returncode, detect.stderr[:300])
    (root / "detect.json").write_text(detect.stdout, encoding="utf-8")
    answers = {"work_set": {"kind": "phases", "numbers": ["16", "17", "18"]},
               "target_host": "claude", "native_execution": False, "mockups": [],
               "strategy": "goal", "objective": OBJECTIVE, "output_dir": None}
    if STYLE:
        answers["goal_style"] = STYLE
    (root / "answers.json").write_text(json.dumps(answers), encoding="utf-8")
    out = run_cli("render", "--repo", str(repo), "--detect", str(root / "detect.json"),
                  "--answers", str(root / "answers.json"), home=str(home))
    print("render rc", out.returncode, out.stderr[:300])
    print(out.stdout)
    if out.returncode == 0:
        path = repo / json.loads(out.stdout)["path"]
        text = path.read_text(encoding="utf-8")
        print(text[:900])
        print("...")
        print(text[text.index("## Full goal"):][:600] if "## Full goal" in text else "NO FULL GOAL")
