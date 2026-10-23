"""SPEC R8 end-to-end: real `python3 tools/setup.py` runs under a temp HOME
whose path contains a space (encoding edge). Covers the pi link root (D-14):
both links on install, no pi dir edge, no ~/.agents/skills, and the pure
no-op contract of bare / hooks-only headless runs (T-21.1-30).

Env holds only PATH plus the temp overrides — nothing can reach the real
~/.claude, ~/.pi, ~/.cursor, config or state dirs.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SETUP = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tools", "setup.py"))

JEV = "jev-fast-decision"
OTHER = "other-skill"


def _write_skill(kit, name):
    d = os.path.join(kit, "skills", name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(f"---\nname: {name}\n---\nbody\n")


class JevInstallE2E(unittest.TestCase):
    def setUp(self):
        # A space in the root path exercises the encoding edge (SPEC R8).
        self.home = tempfile.mkdtemp(prefix="jev install ")
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.kit = os.path.join(self.home, "kit")
        os.makedirs(os.path.join(self.kit, "skills"))
        _write_skill(self.kit, JEV)
        _write_skill(self.kit, OTHER)
        self.claude = os.path.join(self.home, "claude")
        self.pi = os.path.join(self.home, "pi agent")
        os.makedirs(self.pi)
        self.state = os.path.join(self.home, "state")
        self.config = os.path.join(self.home, "config")
        self.env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": self.home,
            "AI_KIT_DIR": self.kit,
            "CLAUDE_CONFIG_DIR": self.claude,
            "PI_CODING_AGENT_DIR": self.pi,
            "XDG_STATE_HOME": self.state,
            "XDG_CONFIG_HOME": self.config,
        }

    def run_setup(self, *args):
        return subprocess.run(
            [sys.executable, SETUP, *args],
            env=self.env, capture_output=True, text=True)

    def link(self, root, name):
        return os.path.join(root, "skills", name)

    def test_install_creates_both_links(self):
        r = self.run_setup("install", "--headless", "--skills",
                           f"{JEV},{OTHER}")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        claude_target = os.path.join(self.kit, "skills", JEV)
        self.assertEqual(os.readlink(self.link(self.claude, JEV)), claude_target)
        self.assertTrue(os.path.islink(self.link(self.claude, OTHER)))
        # pi gets only the PI_SKILLS member, pointing into the kit
        self.assertEqual(os.readlink(self.link(self.pi, JEV)), claude_target)
        self.assertFalse(os.path.lexists(self.link(self.pi, OTHER)))
        self.assertFalse(os.path.exists(os.path.join(self.home, ".agents")),
                         "nothing may be linked under ~/.agents/skills")

    def test_no_pi_dir(self):
        missing_pi = os.path.join(self.home, "no such pi")
        self.env["PI_CODING_AGENT_DIR"] = missing_pi
        r = self.run_setup("install", "--headless", "--skills", JEV)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn(missing_pi, r.stderr)
        self.assertFalse(os.path.exists(missing_pi),
                         "the pi agent dir must never be created")
        self.assertTrue(os.path.islink(self.link(self.claude, JEV)))

    def test_headless_without_skills_keeps_pi_links(self):
        # The shape the commit mirror removes when the skill is unselected:
        # an ai-kit pi link with no claude counterpart. Bare and hooks-only
        # headless runs are pure no-ops for the pi root (T-21.1-30).
        target = os.path.join(self.kit, "skills", JEV)
        os.makedirs(os.path.join(self.pi, "skills"))
        os.symlink(target, self.link(self.pi, JEV))
        for args in (("install", "--headless"),
                     ("install", "--headless", "--with-hooks")):
            r = self.run_setup(*args)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertEqual(os.readlink(self.link(self.pi, JEV)), target)
            self.assertFalse(os.path.lexists(self.link(self.claude, JEV)),
                             "no claude link may be created")


if __name__ == "__main__":
    unittest.main()
