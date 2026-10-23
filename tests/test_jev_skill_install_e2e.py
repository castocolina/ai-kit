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
        os.makedirs(os.path.join(self.pi, "skills"))
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

    def test_uninstall_removes_both_links(self):
        r = self.run_setup("install", "--headless", "--skills", JEV)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # foreign content in both roots must survive
        foreign = os.path.join(self.home, "elsewhere")
        os.makedirs(foreign)
        foreign_link = self.link(self.pi, "foreign")
        os.symlink(foreign, foreign_link)
        mine = self.link(self.claude, "mine")
        os.makedirs(mine)
        with open(os.path.join(mine, "marker"), "w", encoding="utf-8") as f:
            f.write("keep")
        r = self.run_setup("uninstall")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertFalse(os.path.lexists(self.link(self.claude, JEV)))
        self.assertFalse(os.path.lexists(self.link(self.pi, JEV)))
        self.assertEqual(os.readlink(foreign_link), foreign)
        self.assertTrue(os.path.isdir(mine))
        self.assertTrue(os.path.exists(os.path.join(mine, "marker")))

    def test_real_dir_survives_without_flag(self):
        claude_jev = self.link(self.claude, JEV)
        os.makedirs(claude_jev)
        marker = os.path.join(claude_jev, "marker")
        with open(marker, "w", encoding="utf-8") as f:
            f.write("keep")
        r = self.run_setup("install", "--headless", "--skills", JEV)
        self.assertEqual(r.returncode, 1, msg=r.stderr)
        self.assertTrue(os.path.isfile(marker), "real dir untouched")
        self.assertFalse(os.path.exists(
            os.path.join(self.state, "ai-kit", "backups")),
            "no backup without the flag")

    def test_real_dir_moved_with_flag(self):
        claude_jev = self.link(self.claude, JEV)
        os.makedirs(claude_jev)
        marker = os.path.join(claude_jev, "marker")
        with open(marker, "w", encoding="utf-8") as f:
            f.write("keep")
        r = self.run_setup("install", "--headless", "--skills", JEV,
                           "--replace-existing")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(os.readlink(claude_jev),
                         os.path.join(self.kit, "skills", JEV))
        backups = os.path.join(self.state, "ai-kit", "backups", "claude")
        claims = os.listdir(backups)
        self.assertEqual(len(claims), 1)
        self.assertTrue(claims[0].startswith(JEV + ".bak-"))
        self.assertTrue(os.path.isfile(
            os.path.join(backups, claims[0], JEV, "marker")))
        self.assertIn("moved", r.stderr)
        self.assertIn(claude_jev, r.stderr)

    def test_dry_run_with_flag_predicts_success(self):
        # WR-08: a dry run of a replace that would succeed exits 0, never
        # advises the flag it already has, and moves nothing.
        claude_jev = self.link(self.claude, JEV)
        pi_jev = self.link(self.pi, JEV)
        for path in (claude_jev, pi_jev):
            os.makedirs(path)
        r = self.run_setup("--dry-run", "install", "--headless", "--skills", JEV,
                           "--replace-existing")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn(f"would move {claude_jev}", r.stdout)
        self.assertIn(f"would move {pi_jev}", r.stdout)
        self.assertNotIn("re-run with --replace-existing", r.stderr)
        self.assertNotIn("leaving it alone", r.stderr)
        for path in (claude_jev, pi_jev):
            self.assertTrue(os.path.isdir(path) and not os.path.islink(path))
        self.assertFalse(os.path.exists(os.path.join(self.state, "ai-kit", "backups")))

    def test_foreign_pi_link_moved_with_flag(self):
        elsewhere = os.path.join(self.home, "elsewhere", "skills", JEV)
        os.makedirs(elsewhere)
        pi_jev = self.link(self.pi, JEV)
        os.symlink(elsewhere, pi_jev)
        r = self.run_setup("install", "--headless", "--skills", JEV,
                           "--replace-existing")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(os.readlink(pi_jev),
                         os.path.join(self.kit, "skills", JEV))
        backups = os.path.join(self.state, "ai-kit", "backups", "pi")
        claims = os.listdir(backups)
        self.assertEqual(len(claims), 1)
        moved = os.path.join(backups, claims[0], JEV)
        self.assertTrue(os.path.islink(moved))
        self.assertEqual(os.readlink(moved), elsewhere,
                         "the symlink moved as a symlink; its target untouched")
        self.assertTrue(os.path.isdir(elsewhere))

    def test_flag_scope(self):
        # without --headless, or without --skills: argparse error (exit 2)
        for args in (("install", "--replace-existing"),
                     ("install", "--headless", "--replace-existing")):
            r = self.run_setup(*args)
            self.assertEqual(r.returncode, 2, msg=r.stderr)
        # a real dir at another skill's path not named in --skills is untouched
        other_dir = self.link(self.claude, OTHER)
        os.makedirs(other_dir)
        with open(os.path.join(other_dir, "marker"), "w", encoding="utf-8") as f:
            f.write("keep")
        r = self.run_setup("install", "--headless", "--skills", JEV,
                           "--replace-existing")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertTrue(os.path.isdir(other_dir))
        self.assertFalse(os.path.islink(other_dir))

    def test_headless_without_skills_keeps_pi_links(self):
        # The shape the commit mirror removes when the skill is unselected:
        # an ai-kit pi link with no claude counterpart. Bare and hooks-only
        # headless runs are pure no-ops for the pi root (T-21.1-30).
        target = os.path.join(self.kit, "skills", JEV)
        os.makedirs(os.path.join(self.pi, "skills"), exist_ok=True)
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
