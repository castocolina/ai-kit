import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock


def load_module():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "tools", "setup.py")
    spec = importlib.util.spec_from_file_location("setup", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


setup = load_module()


class TestResolvePaths(unittest.TestCase):
    def test_defaults(self):
        env = {"HOME": "/home/u"}
        p = setup.resolve_paths(env)
        self.assertEqual(p.install_dir, "/home/u/.local/share/ai-kit")
        self.assertEqual(p.claude_dir, "/home/u/.claude")
        self.assertEqual(p.settings, "/home/u/.claude/settings.json")
        self.assertEqual(p.config_dir, "/home/u/.config/ai-kit")
        self.assertEqual(p.config_toml, "/home/u/.config/ai-kit/statusline.toml")
        self.assertEqual(p.sample, "/home/u/.local/share/ai-kit/tools/statusline.toml.sample")
        self.assertEqual(p.status_line, "/home/u/.local/share/ai-kit/tools/status-line.py")

    def test_env_overrides(self):
        env = {
            "HOME": "/home/u",
            "AI_KIT_DIR": "/opt/kit",
            "CLAUDE_CONFIG_DIR": "/cfg/claude",
            "XDG_DATA_HOME": "/xdg/data",
            "XDG_CONFIG_HOME": "/xdg/config",
        }
        p = setup.resolve_paths(env)
        # AI_KIT_DIR wins over XDG_DATA_HOME
        self.assertEqual(p.install_dir, "/opt/kit")
        self.assertEqual(p.claude_dir, "/cfg/claude")
        self.assertEqual(p.config_dir, "/xdg/config/ai-kit")

    def test_xdg_data_home_without_ai_kit_dir(self):
        env = {"HOME": "/home/u", "XDG_DATA_HOME": "/xdg/data"}
        p = setup.resolve_paths(env)
        self.assertEqual(p.install_dir, "/xdg/data/ai-kit")

    def test_categories_constant(self):
        self.assertEqual(setup.CATEGORIES, ("agents", "commands", "skills"))


class TestEnumerate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "skills", "alpha"))
        os.makedirs(os.path.join(self.tmp, "skills", "nope"))  # no SKILL.md
        os.makedirs(os.path.join(self.tmp, "commands"))
        os.makedirs(os.path.join(self.tmp, "agents"))
        with open(os.path.join(self.tmp, "skills", "alpha", "SKILL.md"), "w") as f:
            f.write("---\nname: alpha\n---\nbody\n")
        with open(os.path.join(self.tmp, "commands", "doit.md"), "w") as f:
            f.write("---\nname: doit\n---\nbody\n")
        with open(os.path.join(self.tmp, "commands", "bad.md"), "w") as f:
            f.write("no front matter here\n")
        with open(os.path.join(self.tmp, "commands", "notmd.txt"), "w") as f:
            f.write("---\n")
        with open(os.path.join(self.tmp, "agents", "helper.md"), "w") as f:
            f.write("---\nname: helper\n---\nbody\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_validate_skill_needs_dir_and_skill_md(self):
        self.assertTrue(setup.validate_entry("skills", os.path.join(self.tmp, "skills", "alpha")))
        self.assertFalse(setup.validate_entry("skills", os.path.join(self.tmp, "skills", "nope")))

    def test_validate_command_needs_md_with_front_matter(self):
        self.assertTrue(setup.validate_entry("commands", os.path.join(self.tmp, "commands", "doit.md")))
        self.assertFalse(setup.validate_entry("commands", os.path.join(self.tmp, "commands", "bad.md")))
        self.assertFalse(setup.validate_entry("commands", os.path.join(self.tmp, "commands", "notmd.txt")))

    def test_validate_unknown_category_is_false(self):
        self.assertFalse(setup.validate_entry("widgets", self.tmp))

    def test_enumerate_returns_only_valid_entries(self):
        entries = setup.enumerate_entries(self.tmp)
        self.assertEqual([n for n, _ in entries["skills"]], ["alpha"])
        self.assertEqual([n for n, _ in entries["commands"]], ["doit.md"])
        self.assertEqual([n for n, _ in entries["agents"]], ["helper.md"])

    def test_enumerate_missing_category_dir_is_empty_list(self):
        empty = tempfile.mkdtemp()
        try:
            entries = setup.enumerate_entries(empty)
            self.assertEqual(entries, {"agents": [], "commands": [], "skills": []})
        finally:
            shutil.rmtree(empty, ignore_errors=True)


class TestInstalledLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "skills", "alpha"))
        os.makedirs(os.path.join(self.claude, "skills"))
        os.makedirs(os.path.join(self.claude, "commands"))
        os.makedirs(os.path.join(self.claude, "agents"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_picks_up_ai_kit_symlinks_only(self):
        # ai-kit symlink (target inside install dir)
        tgt = os.path.join(self.install, "skills", "alpha")
        os.symlink(tgt, os.path.join(self.claude, "skills", "alpha"))
        # foreign symlink (target elsewhere)
        os.symlink("/tmp/elsewhere", os.path.join(self.claude, "skills", "foreign"))
        # a real directory (not a symlink)
        os.makedirs(os.path.join(self.claude, "skills", "realdir"))
        links = setup.installed_links(self.claude, self.install)
        self.assertEqual(links["skills"], {"alpha": tgt})
        self.assertEqual(links["commands"], {})
        self.assertEqual(links["agents"], {})

    def test_missing_category_dir_is_empty(self):
        shutil.rmtree(os.path.join(self.claude, "agents"))
        links = setup.installed_links(self.claude, self.install)
        self.assertEqual(links["agents"], {})


class TestTty(unittest.TestCase):
    def test_is_interactive_none_is_false(self):
        self.assertFalse(setup.is_interactive(None))

    def test_is_interactive_stream_is_true(self):
        self.assertTrue(setup.is_interactive(io.StringIO()))

    def test_ask_yes_no_default_on_blank(self):
        tty = io.StringIO("\n")
        self.assertTrue(setup.ask_yes_no(tty, "ok? ", default=True))
        tty = io.StringIO("\n")
        self.assertFalse(setup.ask_yes_no(tty, "ok? ", default=False))

    def test_ask_yes_no_explicit_yes_no(self):
        self.assertTrue(setup.ask_yes_no(io.StringIO("y\n"), "?", default=False))
        self.assertTrue(setup.ask_yes_no(io.StringIO("Y\n"), "?", default=False))
        self.assertTrue(setup.ask_yes_no(io.StringIO("yes\n"), "?", default=False))
        self.assertFalse(setup.ask_yes_no(io.StringIO("n\n"), "?", default=True))
        self.assertFalse(setup.ask_yes_no(io.StringIO("no\n"), "?", default=True))

    def test_ask_yes_no_eof_returns_default(self):
        self.assertTrue(setup.ask_yes_no(io.StringIO(""), "?", default=True))
        self.assertFalse(setup.ask_yes_no(io.StringIO(""), "?", default=False))


class TestLinkOne(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.dest = os.path.join(self.tmp, ".claude", "skills")
        os.makedirs(os.path.join(self.install, "skills", "alpha"))
        os.makedirs(self.dest)
        self.target = os.path.join(self.install, "skills", "alpha")
        self.link = os.path.join(self.dest, "alpha")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def counts(self):
        return setup.new_counts()

    def test_link_one_creates(self):
        c = self.counts()
        setup.link_one(self.link, self.target, dry=False, counts=c)
        self.assertEqual(os.readlink(self.link), self.target)
        self.assertEqual(c["linked"], 1)

    def test_link_one_idempotent(self):
        c = self.counts()
        os.symlink(self.target, self.link)
        setup.link_one(self.link, self.target, dry=False, counts=c)
        self.assertEqual(c["linked"], 0)
        self.assertEqual(c["relinked"], 0)

    def test_link_one_relinks_drifted_ai_kit_link(self):
        c = self.counts()
        drift = os.path.join(self.install, "skills", "old")
        os.makedirs(drift)
        os.symlink(drift, self.link)
        setup.link_one(self.link, self.target, dry=False, counts=c)
        self.assertEqual(os.readlink(self.link), self.target)
        self.assertEqual(c["relinked"], 1)

    def test_link_one_leaves_foreign_symlink(self):
        c = self.counts()
        os.symlink("/tmp/elsewhere", self.link)
        setup.link_one(self.link, self.target, dry=False, counts=c)
        self.assertEqual(os.readlink(self.link), "/tmp/elsewhere")
        self.assertEqual(c["skip_foreign"], 1)

    def test_link_one_leaves_real_file(self):
        c = self.counts()
        os.makedirs(self.link)
        setup.link_one(self.link, self.target, dry=False, counts=c)
        self.assertTrue(os.path.isdir(self.link) and not os.path.islink(self.link))
        self.assertEqual(c["skip_real"], 1)

    def test_link_one_dry_run_mutates_nothing(self):
        c = self.counts()
        setup.link_one(self.link, self.target, dry=True, counts=c)
        self.assertFalse(os.path.lexists(self.link))
        self.assertEqual(c["linked"], 1)  # still counted as intended

    def test_unlink_one_removes_link(self):
        c = self.counts()
        os.symlink(self.target, self.link)
        setup.unlink_one(self.link, dry=False, counts=c)
        self.assertFalse(os.path.lexists(self.link))
        self.assertEqual(c["unlinked"], 1)

    def test_unlink_one_dry_run(self):
        c = self.counts()
        os.symlink(self.target, self.link)
        setup.unlink_one(self.link, dry=True, counts=c)
        self.assertTrue(os.path.lexists(self.link))
        self.assertEqual(c["unlinked"], 1)


class TestPruneStale(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "skills"))
        os.makedirs(os.path.join(self.claude, "skills"))
        os.makedirs(os.path.join(self.claude, "commands"))
        os.makedirs(os.path.join(self.claude, "agents"))
        # 'gone' was linked but the repo entry is deleted (dangling target)
        self.gone = os.path.join(self.claude, "skills", "gone")
        os.symlink(os.path.join(self.install, "skills", "gone"), self.gone)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def counts(self):
        return setup.new_counts()

    def test_interactive_prunes_on_yes(self):
        c = self.counts()
        tty = io.StringIO("y\n")
        stale = setup.prune_stale(self.claude, self.install, present={}, tty=tty, dry=False, counts=c)
        self.assertEqual(stale, ["skills/gone"])
        self.assertFalse(os.path.lexists(self.gone))
        self.assertEqual(c["pruned"], 1)

    def test_interactive_keeps_on_no(self):
        c = self.counts()
        tty = io.StringIO("n\n")
        setup.prune_stale(self.claude, self.install, present={}, tty=tty, dry=False, counts=c)
        self.assertTrue(os.path.lexists(self.gone))
        self.assertEqual(c["pruned"], 0)

    def test_headless_auto_removes_and_warns(self):
        c = self.counts()
        stale = setup.prune_stale(self.claude, self.install, present={}, tty=None, dry=False, counts=c)
        self.assertEqual(stale, ["skills/gone"])
        self.assertFalse(os.path.lexists(self.gone))
        self.assertEqual(c["pruned"], 1)

    def test_present_entry_is_not_stale(self):
        # 'gone' is in the present set for skills → not pruned
        c = self.counts()
        present = {"skills": {"gone"}}
        stale = setup.prune_stale(self.claude, self.install, present, tty=None, dry=False, counts=c)
        self.assertEqual(stale, [])
        self.assertTrue(os.path.lexists(self.gone))


class TestSelectSkills(unittest.TestCase):
    def entries(self):
        # (name, dummy path) tuples; path unused by select_skills
        return {
            "skills": [("alpha", "/i/skills/alpha"), ("beta", "/i/skills/beta"),
                       ("gamma", "/i/skills/gamma")],
            "commands": [("doit.md", "/i/commands/doit.md")],
            "agents": [],
        }

    def test_first_run_defaults_all_on(self):
        # installed is empty for every category → first-ever install
        installed = {"skills": {}, "commands": {}, "agents": {}}
        sel = setup.select_skills(self.entries(), installed, tty=None)
        self.assertEqual(sel["skills"], {"alpha", "beta", "gamma"})
        self.assertEqual(sel["commands"], {"doit.md"})

    def test_headless_keeps_existing_selection_new_stays_off(self):
        # alpha+beta linked previously; gamma is NEW upstream → stays OFF headless
        installed = {"skills": {"alpha": "x", "beta": "x"}, "commands": {}, "agents": {}}
        sel = setup.select_skills(self.entries(), installed, tty=None)
        self.assertEqual(sel["skills"], {"alpha", "beta"})

    def test_interactive_toggle_flips_a_row(self):
        installed = {"skills": {"alpha": "x"}, "commands": {}, "agents": {}}
        # menu shows skills 1=alpha[x] 2=beta[ ] 3=gamma[ ] 4=doit.md[ ];
        # user types "2" to enable beta, then Enter to accept
        tty = io.StringIO("2\n\n")
        sel = setup.select_skills(self.entries(), installed, tty=tty)
        self.assertEqual(sel["skills"], {"alpha", "beta"})

    def test_interactive_all_then_none(self):
        installed = {"skills": {}, "commands": {}, "agents": {}}
        tty = io.StringIO("a\n\n")  # 'a' = all, then accept
        sel = setup.select_skills(self.entries(), installed, tty=tty)
        self.assertEqual(sel["skills"], {"alpha", "beta", "gamma"})
        tty = io.StringIO("n\n\n")  # 'n' = none, then accept
        sel = setup.select_skills(self.entries(), installed, tty=tty)
        self.assertEqual(sel["skills"], set())


class TestApplySelection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        for n in ("alpha", "beta"):
            os.makedirs(os.path.join(self.install, "skills", n))
        os.makedirs(os.path.join(self.claude, "skills"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_links_selected_unlinks_deselected(self):
        entries = {"skills": [("alpha", os.path.join(self.install, "skills", "alpha")),
                              ("beta", os.path.join(self.install, "skills", "beta"))],
                   "commands": [], "agents": []}
        # pre-link beta so it can be deselected
        os.symlink(os.path.join(self.install, "skills", "beta"),
                   os.path.join(self.claude, "skills", "beta"))
        c = setup.new_counts()
        setup.apply_selection({"skills": {"alpha"}, "commands": set(), "agents": set()},
                              entries, self.claude, dry=False, counts=c)
        self.assertTrue(os.path.islink(os.path.join(self.claude, "skills", "alpha")))
        self.assertFalse(os.path.lexists(os.path.join(self.claude, "skills", "beta")))
        self.assertEqual(c["linked"], 1)
        self.assertEqual(c["unlinked"], 1)


class TestWireStatusline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.settings = os.path.join(self.tmp, "settings.json")
        self.sl = os.path.join(self.tmp, "ai-kit", "tools", "status-line.py")
        os.makedirs(os.path.dirname(self.sl))
        open(self.sl, "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def read(self):
        with open(self.settings) as f:
            return json.load(f)

    def test_absent_sets_silently(self):
        ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertTrue(ok)
        cmd = self.read()["statusLine"]["command"]
        self.assertIn(self.sl, cmd)
        self.assertIn("python3 -S", cmd)

    def test_already_ai_kit_refreshes_silently(self):
        with open(self.settings, "w") as f:
            json.dump({"statusLine": {"type": "command",
                                      "command": "python3 -S " + self.sl}}, f)
        ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertTrue(ok)

    def test_foreign_requires_confirm_yes_overwrites(self):
        with open(self.settings, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "/usr/bin/mybar"}}, f)
        tty = io.StringIO("y\n")
        ok = setup.wire_statusline(self.settings, self.sl, tty=tty, dry=False)
        self.assertTrue(ok)
        self.assertIn(self.sl, self.read()["statusLine"]["command"])

    def test_foreign_decline_leaves_untouched(self):
        with open(self.settings, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "/usr/bin/mybar"}}, f)
        tty = io.StringIO("n\n")
        ok = setup.wire_statusline(self.settings, self.sl, tty=tty, dry=False)
        self.assertFalse(ok)
        self.assertEqual(self.read()["statusLine"]["command"], "/usr/bin/mybar")

    def test_foreign_headless_does_not_overwrite(self):
        with open(self.settings, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "/usr/bin/mybar"}}, f)
        ok = setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        self.assertFalse(ok)
        self.assertEqual(self.read()["statusLine"]["command"], "/usr/bin/mybar")

    def test_preserves_other_keys(self):
        with open(self.settings, "w") as f:
            json.dump({"theme": "dark", "model": "opus"}, f)
        setup.wire_statusline(self.settings, self.sl, tty=None, dry=False)
        data = self.read()
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["model"], "opus")

    def test_dry_run_does_not_write(self):
        setup.wire_statusline(self.settings, self.sl, tty=None, dry=True)
        self.assertFalse(os.path.exists(self.settings))


class TestRecipeAndUnwire(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sample = os.path.join(self.tmp, "sample.toml")
        self.cfg = os.path.join(self.tmp, "ai-kit", "statusline.toml")
        with open(self.sample, "w") as f:
            f.write("# recipe\nrender_time = true\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_copy_when_absent(self):
        setup.copy_recipe_if_absent(self.sample, self.cfg, dry=False)
        with open(self.cfg) as f:
            self.assertIn("recipe", f.read())

    def test_skip_when_present(self):
        os.makedirs(os.path.dirname(self.cfg))
        with open(self.cfg, "w") as f:
            f.write("# user edited\n")
        setup.copy_recipe_if_absent(self.sample, self.cfg, dry=False)
        with open(self.cfg) as f:
            self.assertIn("user edited", f.read())

    def test_unwire_only_when_ai_kit(self):
        settings = os.path.join(self.tmp, "settings.json")
        install_dir = os.path.join(self.tmp, "ai-kit")
        with open(settings, "w") as f:
            json.dump({"statusLine": {"type": "command",
                                      "command": "python3 -S " + install_dir + "/tools/status-line.py"},
                       "theme": "dark"}, f)
        setup.unwire_statusline(settings, install_dir, dry=False)
        with open(settings) as f:
            data = json.load(f)
        self.assertNotIn("statusLine", data)
        self.assertEqual(data["theme"], "dark")

    def test_unwire_leaves_foreign(self):
        settings = os.path.join(self.tmp, "settings.json")
        install_dir = os.path.join(self.tmp, "ai-kit")
        with open(settings, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "/usr/bin/mybar"}}, f)
        setup.unwire_statusline(settings, install_dir, dry=False)
        with open(settings) as f:
            data = json.load(f)
        self.assertEqual(data["statusLine"]["command"], "/usr/bin/mybar")


class TestCmdInstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "skills", "alpha"))
        os.makedirs(os.path.join(self.install, "tools"))
        with open(os.path.join(self.install, "skills", "alpha", "SKILL.md"), "w") as f:
            f.write("---\nname: alpha\n---\n")
        open(os.path.join(self.install, "tools", "status-line.py"), "w").close()
        with open(os.path.join(self.install, "tools", "statusline.toml.sample"), "w") as f:
            f.write("# recipe\n")
        self.env = {"HOME": self.tmp, "AI_KIT_DIR": self.install,
                    "CLAUDE_CONFIG_DIR": self.claude,
                    "XDG_CONFIG_HOME": os.path.join(self.tmp, ".config")}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_headless_first_run_links_all_skips_statusline(self):
        # tty None → headless: link defaults (all-on first run), no statusLine wiring
        rc = setup.cmd_install(self.env, tty=None, dry=False)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.islink(os.path.join(self.claude, "skills", "alpha")))
        # headless never wires the status line
        self.assertFalse(os.path.exists(os.path.join(self.claude, "settings.json")))

    def test_interactive_wires_statusline(self):
        # accept the all-on default (Enter), then accept status-line wiring path
        tty = io.StringIO("\n")
        rc = setup.cmd_install(self.env, tty=tty, dry=False)
        self.assertEqual(rc, 0)
        with open(os.path.join(self.claude, "settings.json")) as f:
            self.assertIn("status-line.py", f.read())
        # recipe copied
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, ".config", "ai-kit", "statusline.toml")))

    def test_dry_run_mutates_nothing(self):
        rc = setup.cmd_install(self.env, tty=None, dry=True)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.lexists(os.path.join(self.claude, "skills", "alpha")))


class TestCmdUninstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "skills", "alpha"))
        os.makedirs(os.path.join(self.claude, "skills"))
        os.symlink(os.path.join(self.install, "skills", "alpha"),
                   os.path.join(self.claude, "skills", "alpha"))
        os.symlink("/tmp/elsewhere", os.path.join(self.claude, "skills", "foreign"))
        self.env = {"HOME": self.tmp, "AI_KIT_DIR": self.install,
                    "CLAUDE_CONFIG_DIR": self.claude}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_removes_ai_kit_links_keeps_foreign_and_install(self):
        rc = setup.cmd_uninstall(self.env, dry=False)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.lexists(os.path.join(self.claude, "skills", "alpha")))
        self.assertTrue(os.path.lexists(os.path.join(self.claude, "skills", "foreign")))
        self.assertTrue(os.path.isdir(self.install))


class TestCmdDelegation(unittest.TestCase):
    def test_doctor_shells_out_to_status_line(self):
        env = {"HOME": "/h", "AI_KIT_DIR": "/i"}
        with mock.patch.object(setup.subprocess, "call", return_value=0) as call:
            rc = setup.cmd_doctor(env)
        self.assertEqual(rc, 0)
        args = call.call_args[0][0]
        self.assertIn("/i/tools/status-line.py", args)
        self.assertIn("--doctor", args)

    def test_check_shells_out_with_check_flag(self):
        env = {"HOME": "/h", "AI_KIT_DIR": "/i"}
        with mock.patch.object(setup.subprocess, "call", return_value=2) as call:
            rc = setup.cmd_check(env)
        self.assertEqual(rc, 2)
        self.assertIn("--check", call.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
