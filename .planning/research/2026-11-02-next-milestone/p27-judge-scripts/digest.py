"""Print the package digest the checker would compute at HEAD (tracked files of the skill)."""

import importlib.util
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(REPO)
path = ".planning/phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/check_verdicts.py"
spec = importlib.util.spec_from_file_location("check_verdicts", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(module.pkg())
