"""Copy installs keep the shared key-shape scanner working (each caller from a real copy).

Each caller's skill folder is copied with no symlink and no __pycache__ into its own temporary
skills root; session-wake goes with ai-kit-spec-review, the sibling it already needs. A child
`python3 -I -B` with a temporary HOME runs the copy's real entry on a synthetic AWS-shaped key
and prints the result plus every loaded module file outside the copy and the interpreter, so a
copy that reaches back into this checkout fails. Session-wake copied alone still fails closed.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "skills"
SAMPLE = "AKIA" + "X" * 16
SIBLING_MISSING = "the ai-kit-spec-review sibling skill is missing beside"
# argv: the copied skills root, the folder to put on sys.path (relative to it), the sample.
CHILD_PRELUDE = (
    "import json, os, sys\n"
    "root, rel, sample = sys.argv[1], sys.argv[2], sys.argv[3]\n"
    "sys.path.insert(0, os.path.join(root, rel))\n"
)
CHILD_EPILOGUE = (
    "real_root = os.path.realpath(root) + os.sep\n"
    "allowed = tuple({os.path.realpath(p) + os.sep for p in (sys.prefix, sys.base_prefix,"
    " sys.exec_prefix, sys.base_exec_prefix)})\n"
    "files = sorted({os.path.realpath(m.__file__) for m in list(sys.modules.values())"
    " if getattr(m, '__file__', None)})\n"
    "outside = [f for f in files if not f.startswith(real_root) and not f.startswith(allowed)]\n"
    "print(json.dumps({'result': result, 'outside': outside}))\n"
)
ENTRIES = {
    "goal-prompt": (
        "import gp_common\n"
        "result = gp_common.scan_text('key ' + sample, home='', secrets=[])\n"
    ),
    "jev": (
        "import jev_ladder\n"
        "result = jev_ladder.item_error({'id': 'n', 'type': 'noul', 'instructions': 'Ship it?',"
        " 'context': 'key ' + sample})\n"
    ),
    "commit-fold": "import flow_pr\nresult = flow_pr.redact('key ' + sample)\n",
    "session-wake": (
        "from ai_kit_session_wake.reset_parse import redact\nresult = redact('key ' + sample)\n"
    ),
}


class TestCopyInstall(unittest.TestCase):
    def _run_copy(self, skills, rel, entry):
        """Copy `skills` into a fresh skills root and run `entry` there in a child process."""
        tmp = Path(tempfile.mkdtemp(prefix="ai-kit-shapes-copy-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root, home = tmp / "skills", tmp / "home"
        home.mkdir()
        for skill in skills:
            shutil.copytree(SKILLS / skill, root / skill, symlinks=False,
                            ignore=shutil.ignore_patterns("__pycache__"))
        for dirpath, dirnames, filenames in os.walk(root):
            self.assertNotIn("__pycache__", dirnames, dirpath)
            for name in dirnames + filenames:
                self.assertFalse(os.path.islink(os.path.join(dirpath, name)), name)
        env = {"HOME": str(home), "AI_KIT_REFUSE_REAL_HOME": "1",
               "PATH": os.environ.get("PATH", "")}
        proc = subprocess.run(
            [sys.executable, "-I", "-B", "-c", CHILD_PRELUDE + entry + CHILD_EPILOGUE,
             str(root), rel, SAMPLE],
            capture_output=True, text=True, env=env, cwd=tmp, timeout=60, check=False,
        )
        self.assertNotIn(SAMPLE, proc.stdout + proc.stderr)
        return proc

    def _caught(self, skills, rel, entry):
        proc = self._run_copy(skills, rel, entry)
        self.assertEqual(0, proc.returncode, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual([], report["outside"])
        return report["result"]

    def test_goal_prompt_copy_names_a_new_shape(self):
        result = self._caught(["ai-kit-spec-goal-prompt"], "ai-kit-spec-goal-prompt/scripts",
                              ENTRIES["goal-prompt"])
        self.assertEqual(["aws_access_key_id-shaped token present"], result)

    def test_jev_copy_refuses_a_new_shape(self):
        result = self._caught(["jev-fast-decision"], "jev-fast-decision/scripts", ENTRIES["jev"])
        self.assertEqual("secret_pattern_context", result)

    def test_commit_fold_copy_redacts_a_new_shape(self):
        result = self._caught(["ai-kit-commit-fold"], "ai-kit-commit-fold/scripts",
                              ENTRIES["commit-fold"])
        self.assertEqual("key [redacted]", result)

    def test_session_wake_copy_with_its_sibling_redacts_a_new_shape(self):
        result = self._caught(["ai-kit-session-wake", "ai-kit-spec-review"],
                              "ai-kit-session-wake", ENTRIES["session-wake"])
        self.assertEqual("key <redacted>", result)

    def test_session_wake_copy_alone_fails_closed(self):
        proc = self._run_copy(["ai-kit-session-wake"], "ai-kit-session-wake",
                              ENTRIES["session-wake"])
        self.assertNotEqual(0, proc.returncode)
        self.assertIn(SIBLING_MISSING, proc.stderr)
