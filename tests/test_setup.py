import importlib.util
import io
import json
import os
import shutil
import sys
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

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_INPUT = os.path.join(FIXTURE_DIR, "sample-input.json")
SAMPLE_RECIPE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "tools", "statusline.toml.sample")
EDITED_RECIPE = os.path.join(FIXTURE_DIR, "statusline-edited.toml")


class TestFixture(unittest.TestCase):
    def test_sample_input_is_valid_json_with_required_keys(self):
        with open(SAMPLE_INPUT) as f:
            raw = json.load(f)
        for key in ("model", "workspace", "cost", "context_window"):
            self.assertIn(key, raw)
        self.assertIn("display_name", raw["model"])
        self.assertIn("used_percentage", raw["context_window"])


class TestTomlRead(unittest.TestCase):
    def test_read_toml_missing_returns_empty(self):
        self.assertEqual(setup.read_toml("/no/such/file.toml"), {})

    def test_read_toml_malformed_returns_empty(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("this is = = not toml\n")
            path = f.name
        self.addCleanup(os.unlink, path)
        self.assertEqual(setup.read_toml(path), {})

    def test_current_segments_defaults_on_noop_recipe(self):
        # The shipped sample is all-commented (a no-op) -> pure defaults.
        seg = setup.current_segments(SAMPLE_RECIPE)
        self.assertTrue(seg["path"])
        self.assertFalse(seg["cost"])        # cost OFF by default
        self.assertFalse(seg["dimensions"])  # dimensions OFF by default
        self.assertEqual(set(seg), set(setup.SEGMENT_DEFAULTS))

    def test_current_segments_merges_file_override(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[segments]\ncost = true\nmemory = false\n")
            path = f.name
        self.addCleanup(os.unlink, path)
        seg = setup.current_segments(path)
        self.assertTrue(seg["cost"])
        self.assertFalse(seg["memory"])
        self.assertTrue(seg["path"])         # untouched default survives

    def test_current_layout_default_on_noop_recipe(self):
        layout = setup.current_layout(SAMPLE_RECIPE)
        self.assertEqual([r["segments"] for r in layout],
                         [["path", "branch", "dirty", "todo"],
                          ["model", "time_ago", "clock", "effort", "lines",
                           "cost", "total_time", "api_time"],
                          ["render_time", "dimensions", "context",
                           "chat_size", "memory", "rate_limits", "slowest"]])

    def test_current_layout_file_replaces_all(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write('[[line]]\nmin_rows = 0\nsegments = ["path", "context"]\n')
            path = f.name
        self.addCleanup(os.unlink, path)
        layout = setup.current_layout(path)
        self.assertEqual(layout, [{"min_rows": 0, "segments": ["path", "context"]}])

    def test_segment_defaults_match_recipe_drift(self):
        # Drift guard: every [segments] key commented in the recipe must exist in
        # SEGMENT_DEFAULTS with the same default bool.
        import re as _re
        with open(SAMPLE_RECIPE) as f:
            text = f.read()
        in_seg = False
        for line in text.splitlines():
            if line.strip().startswith("# [segments]"):
                in_seg = True
                continue
            if in_seg and _re.match(r"#\s*\[", line):   # next section header
                break
            m = _re.match(r"#\s*(\w+)\s*=\s*(true|false)\b", line)
            if in_seg and m:
                key, val = m.group(1), m.group(2) == "true"
                self.assertIn(key, setup.SEGMENT_DEFAULTS)
                self.assertEqual(setup.SEGMENT_DEFAULTS[key], val,
                                 f"{key} default drifted from recipe")


class TestRenderPreview(unittest.TestCase):
    def _status_line(self):
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tools", "status-line.py")

    def test_preview_renders_and_reflects_toggle_off(self):
        seg = dict(setup.SEGMENT_DEFAULTS)
        with open(SAMPLE_INPUT) as f:
            sample_json = f.read()
        on = setup.render_preview(self._status_line(), seg, sample_json, {})
        self.assertIn("Opus", on)            # model segment present by default
        seg["model"] = False
        off = setup.render_preview(self._status_line(), seg, sample_json, {})
        self.assertNotIn("Opus", off)        # toggling model off removes it

    def test_preview_passes_env_overrides_for_every_segment(self):
        # cost is OFF by default; turning it on must surface the 🪙 marker.
        seg = dict(setup.SEGMENT_DEFAULTS)
        seg["cost"] = True
        with open(SAMPLE_INPUT) as f:
            sample_json = f.read()
        out = setup.render_preview(self._status_line(), seg, sample_json, {})
        self.assertIn("🪙", out)

    def test_preview_never_raises_on_renderer_error(self):
        # A bogus interpreter/path must degrade to an empty string, not crash.
        out = setup.render_preview("/no/such/status-line.py",
                                   dict(setup.SEGMENT_DEFAULTS), "{}", {})
        self.assertEqual(out, "")


class TestPatchSegments(unittest.TestCase):
    def test_uncomments_and_sets_single_key(self):
        text = ("# [segments]\n"
                "# path = true          # 📂 working directory\n"
                "# cost = false         # 🪙 session cost\n")
        out = setup.patch_segments(text, {"cost": True})
        self.assertIn("[segments]\n", out)              # header uncommented
        self.assertIn("cost = true", out)               # key flipped + live
        self.assertIn("# 🪙 session cost", out)          # trailing comment kept
        self.assertIn("# path = true", out)             # untouched key still commented

    def test_only_changed_key_touched(self):
        text = ("# [segments]\n"
                "# cost = false\n"
                "# memory = true\n")
        out = setup.patch_segments(text, {"cost": True})
        self.assertIn("cost = true", out)
        self.assertIn("# memory = true", out)           # memory untouched

    def test_set_false_writes_live_false(self):
        text = "# [segments]\n# memory = true\n"
        out = setup.patch_segments(text, {"memory": False})
        self.assertIn("memory = false", out)

    def test_appends_missing_key_with_note(self):
        text = "# [segments]\n# path = true\n"
        out = setup.patch_segments(text, {"clock": False})
        self.assertIn("clock = false", out)
        self.assertIn("⏰", out)                          # the clock note glyph

    def test_no_changes_returns_text_unchanged(self):
        text = "# [segments]\n# cost = false\n"
        self.assertEqual(setup.patch_segments(text, {}), text)

    def test_preserves_lines_outside_segments(self):
        text = ("# version = 1\n"
                "# [segments]\n# cost = false\n"
                "# [palette]\n# RED = \"31\"\n")
        out = setup.patch_segments(text, {"cost": True})
        self.assertIn("# version = 1\n", out)
        self.assertIn("# [palette]\n# RED = \"31\"\n", out)

    def test_result_parses_as_valid_toml(self):
        text = ("# [segments]\n"
                "# path = true\n# cost = false\n")
        out = setup.patch_segments(text, {"cost": True})
        import tomllib
        parsed = tomllib.loads(out)
        self.assertEqual(parsed["segments"]["cost"], True)


class TestPatchLayout(unittest.TestCase):
    LINES = [
        {"min_rows": 0, "segments": ["path", "branch"]},
        {"min_rows": 20, "segments": ["model", "clock"]},
    ]

    def test_writes_all_blocks_live(self):
        text = ("# [[line]]\n# min_rows = 0\n"
                '# segments = ["path", "branch", "dirty", "todo"]\n'
                "# [[line]]\n# min_rows = 20\n"
                '# segments = ["model", "clock"]\n')
        out = setup.patch_layout(text, self.LINES)
        import tomllib
        parsed = tomllib.loads(out)
        self.assertEqual([r["segments"] for r in parsed["line"]],
                         [["path", "branch"], ["model", "clock"]])
        self.assertEqual([r["min_rows"] for r in parsed["line"]], [0, 20])

    def test_preserves_surrounding_sections(self):
        text = ("# [segments]\n# cost = false\n"
                "# [[line]]\n# min_rows = 0\n# segments = [\"path\"]\n"
                "# [palette]\n# RED = \"31\"\n")
        out = setup.patch_layout(text, self.LINES)
        self.assertIn("# [segments]\n# cost = false\n", out)
        self.assertIn("# [palette]\n# RED = \"31\"\n", out)

    def test_roundtrip_parses(self):
        text = "# [[line]]\n# min_rows = 0\n# segments = [\"path\"]\n"
        out = setup.patch_layout(text, self.LINES)
        import tomllib
        tomllib.loads(out)          # must not raise

    def test_idempotent_no_accumulation(self):
        # Running patch_layout twice must produce byte-identical output (no ##
        # header lines or other material accumulates on re-runs).
        text = ("# [[line]]\n# min_rows = 0\n"
                '# segments = ["path", "branch", "dirty", "todo"]\n'
                "# [[line]]\n# min_rows = 20\n"
                '# segments = ["model", "clock"]\n')
        first = setup.patch_layout(text, self.LINES)
        second = setup.patch_layout(first, self.LINES)
        self.assertEqual(first, second)


class TestWritePreserving(unittest.TestCase):
    def _status_line(self):
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tools", "status-line.py")

    def test_writes_valid_toml_and_validates(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statusline.toml")
            ok = setup.write_toml_preserving(
                path, "[segments]\ncost = true\n", self._status_line())
            self.assertTrue(ok)
            with open(path) as f:
                self.assertIn("cost = true", f.read())

    def test_rejects_broken_output_and_reverts(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statusline.toml")
            with open(path, "w") as f:
                f.write("# good original\n")
            # An unknown segment key fails the doctor.
            ok = setup.write_toml_preserving(
                path, "[segments]\nbogus_key = true\n", self._status_line())
            self.assertFalse(ok)
            with open(path) as f:
                self.assertEqual(f.read(), "# good original\n")   # reverted


def _diff_lines(a, b):
    al, bl = a.splitlines(), b.splitlines()
    return [(i, x, y) for i, (x, y) in enumerate(zip(al, bl)) if x != y] + \
           [("len", len(al), len(bl))] if len(al) != len(bl) else \
           [(i, x, y) for i, (x, y) in enumerate(zip(al, bl)) if x != y]


class TestGoldenPreservation(unittest.TestCase):
    def test_one_segment_toggle_changes_only_that_line(self):
        with open(EDITED_RECIPE) as f:
            before = f.read()
        after = setup.patch_segments(before, {"cost": True})
        diffs = _diff_lines(before, after)
        self.assertEqual(len(diffs), 1, diffs)               # exactly one line changed
        _, old, new = diffs[0]
        self.assertIn("cost = false", old)
        self.assertIn("cost = true", new)
        # palette / ramp / external / version / comment all intact
        for marker in ('RED = "38;5;196"', "hand-tuned brighter red",
                       "[ramp.context]", "[external]", "# version = 1",
                       "my own note"):
            self.assertIn(marker, after)

    def test_palette_and_ramp_blocks_byte_for_byte(self):
        with open(EDITED_RECIPE) as f:
            before = f.read()
        after = setup.patch_segments(before, {"memory": False})
        for block in ("[palette]\nRED = \"38;5;196\"      # hand-tuned brighter red\n"
                      "BLUE = \"38;5;33\"\n",
                      "[ramp.context]\n10 = \"WHITE\"\n50 = \"RED+bold\"\n"
                      "inf = \"MAGENTA_DARK+bold\"\n"):
            self.assertIn(block, after)


class TestExternalSeam(unittest.TestCase):
    def test_external_block_survives_segment_patch(self):
        with open(EDITED_RECIPE) as f:
            before = f.read()
        after = setup.patch_segments(before, {"cost": True})
        self.assertIn("[external]\nttl = 60\n"
                      'dir = "~/.config/ai-kit/segments"\n', after)

    def test_external_block_survives_layout_patch(self):
        with open(EDITED_RECIPE) as f:
            before = f.read()
        after = setup.patch_layout(before, [{"min_rows": 0, "segments": ["path"]}])
        self.assertIn("[external]\nttl = 60\n", after)


class TestWizardLoop(unittest.TestCase):
    def _state(self):
        return {"segments": dict(setup.SEGMENT_DEFAULTS),
                "layout": [{"min_rows": 0, "segments": ["path", "branch", "dirty"]},
                           {"min_rows": 20, "segments": ["model", "clock"]}],
                "dirty": False}

    def test_toggle_by_number_flips_segment(self):
        st = self._state()
        order = sorted(st["segments"])          # numbering is sorted-key order
        idx = order.index("cost") + 1
        st2, err = setup._apply_wizard_command(st, str(idx))
        self.assertIsNone(err)
        self.assertTrue(st2["segments"]["cost"])
        self.assertTrue(st2["dirty"])

    def test_move_up_reorders_within_line(self):
        st, err = setup._apply_wizard_command(self._state(), "move branch up")
        self.assertIsNone(err)
        self.assertEqual(st["layout"][0]["segments"][:2], ["branch", "path"])

    def test_move_down_reorders_within_line(self):
        st, err = setup._apply_wizard_command(self._state(), "move path down")
        self.assertIsNone(err)
        self.assertEqual(st["layout"][0]["segments"][:2], ["branch", "path"])

    def test_move_across_lines(self):
        st, err = setup._apply_wizard_command(self._state(), "move clock line 1")
        self.assertIsNone(err)
        self.assertIn("clock", st["layout"][0]["segments"])
        self.assertNotIn("clock", st["layout"][1]["segments"])

    def test_worktree_is_a_normal_segment(self):
        # worktree migrated from the [git] knob to a regular segment toggle: it
        # appears in SEGMENT_DEFAULTS (ON) and flips like any other segment.
        self.assertTrue(setup.SEGMENT_DEFAULTS.get("worktree"))
        st = self._state()
        order = sorted(st["segments"])
        idx = order.index("worktree") + 1
        st2, err = setup._apply_wizard_command(st, str(idx))
        self.assertIsNone(err)
        self.assertFalse(st2["segments"]["worktree"])   # was ON, toggled OFF
        self.assertTrue(st2["dirty"])

    def test_worktree_command_no_longer_special(self):
        # The dedicated `worktree` wizard command is gone.
        _, err = setup._apply_wizard_command(self._state(), "worktree")
        self.assertIsNotNone(err)

    def test_unknown_command_returns_error(self):
        st, err = setup._apply_wizard_command(self._state(), "frobnicate")
        self.assertIsNotNone(err)

    def test_move_unknown_segment_errors(self):
        _, err = setup._apply_wizard_command(self._state(), "move nope up")
        self.assertIsNotNone(err)

    def test_save_writes_only_diff_from_recipe(self):
        # Integration: a save against the shipped recipe writes a valid file that
        # toggles cost on and preserves the palette section.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statusline.toml")
            with open(SAMPLE_RECIPE) as f:
                original = f.read()
            with open(path, "w") as f:
                f.write(original)
            status_line = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "tools", "status-line.py")
            ok = setup.save_statusline_config(
                path, {"cost": True}, None, status_line)
            self.assertTrue(ok)
            import tomllib
            with open(path, "rb") as f:
                parsed = tomllib.load(f)
            self.assertTrue(parsed["segments"]["cost"])
            with open(path) as f:
                self.assertIn("# [palette]", f.read())   # palette comments intact


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


class TestAdoptPredecessorLinks(unittest.TestCase):
    """Links left behind by a PREVIOUS ai-kit install (e.g. a renamed repo:
    uz-kit -> ai-kit). They are foreign to the current install_dir but carry the
    ai-kit <root>/<cat>/<name> shape, so the wizard can re-point or drop them."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")        # current install
        self.old = os.path.join(self.tmp, "uz-kit")            # previous install
        self.claude = os.path.join(self.tmp, ".claude")
        for root in (self.install, self.old):
            os.makedirs(os.path.join(root, "skills"))
        for cat in setup.CATEGORIES:
            os.makedirs(os.path.join(self.claude, cat))
        # a link from the OLD install still in ~/.claude
        self.link = os.path.join(self.claude, "skills", "alpha")
        os.symlink(os.path.join(self.old, "skills", "alpha"), self.link)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def entries(self):
        # 'alpha' is a current repo entry, so it can be re-pointed
        return {"skills": [("alpha", os.path.join(self.install, "skills", "alpha"))],
                "commands": [], "agents": []}

    def test_detects_predecessor_link(self):
        cands = setup.predecessor_candidates(self.claude, self.install, self.entries())
        self.assertEqual([(c, n) for c, n, _, _ in cands], [("skills", "alpha")])

    def test_ignores_link_into_current_install(self):
        os.remove(self.link)
        os.symlink(os.path.join(self.install, "skills", "alpha"), self.link)
        self.assertEqual(setup.predecessor_candidates(self.claude, self.install, self.entries()), [])

    def test_ignores_unrelated_foreign_symlink(self):
        # user's own symlink, not ai-kit-shaped (basename mismatch) -> left alone
        weird = os.path.join(self.claude, "skills", "mine")
        os.symlink("/somewhere/else/notes.md", weird)
        cands = setup.predecessor_candidates(self.claude, self.install, self.entries())
        self.assertNotIn("mine", [n for _, n, _, _ in cands])

    def test_ignores_predecessor_with_no_current_entry(self):
        # link from old install whose name is NOT a current repo entry -> can't re-point
        orphan = os.path.join(self.claude, "skills", "ghost")
        os.symlink(os.path.join(self.old, "skills", "ghost"), orphan)
        cands = setup.predecessor_candidates(self.claude, self.install, self.entries())
        self.assertNotIn("ghost", [n for _, n, _, _ in cands])

    def test_interactive_repoint_default(self):
        c = setup.new_counts()
        tty = io.StringIO("\n")                # blank = accept default (re-point)
        setup.adopt_predecessor_links(self.claude, self.install, self.entries(),
                                      tty=tty, dry=False, counts=c)
        self.assertEqual(os.readlink(self.link), os.path.join(self.install, "skills", "alpha"))
        self.assertEqual(c["relinked"], 1)

    def test_interactive_drop_on_no(self):
        c = setup.new_counts()
        tty = io.StringIO("n\n")
        setup.adopt_predecessor_links(self.claude, self.install, self.entries(),
                                      tty=tty, dry=False, counts=c)
        self.assertFalse(os.path.lexists(self.link))
        self.assertEqual(c["pruned"], 1)

    def test_headless_leaves_links_untouched(self):
        c = setup.new_counts()
        items = setup.adopt_predecessor_links(self.claude, self.install, self.entries(),
                                              tty=None, dry=False, counts=c)
        self.assertEqual(items, ["skills/alpha"])
        self.assertEqual(os.readlink(self.link), os.path.join(self.old, "skills", "alpha"))
        self.assertEqual(c["relinked"], 0)
        self.assertEqual(c["pruned"], 0)

    def test_dry_run_mutates_nothing(self):
        c = setup.new_counts()
        tty = io.StringIO("\n")
        setup.adopt_predecessor_links(self.claude, self.install, self.entries(),
                                      tty=tty, dry=True, counts=c)
        self.assertEqual(os.readlink(self.link), os.path.join(self.old, "skills", "alpha"))


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
        # Validate under the SAME interpreter the wizard writes/validates with,
        # not a bare "python3" that PATH might resolve to a different venv.
        self.assertEqual(args[0], sys.executable)

    def test_check_shells_out_with_check_flag(self):
        env = {"HOME": "/h", "AI_KIT_DIR": "/i"}
        with mock.patch.object(setup.subprocess, "call", return_value=2) as call:
            rc = setup.cmd_check(env)
        self.assertEqual(rc, 2)
        self.assertIn("--check", call.call_args[0][0])
        self.assertEqual(call.call_args[0][0][0], sys.executable)


class TestMenuWiring(unittest.TestCase):
    def test_statusline_branch_invokes_wizard(self):
        """Verify that cmd_install's interactive branch delegates to run_statusline_wizard.

        E5b defines cmd_install(env, tty, dry) — it resolves Paths internally from env.
        Passing a pre-resolved Paths namedtuple would cause AttributeError (env.get(...)
        would be called on a namedtuple). Always pass an env dict.

        E5c wires the real wizard into that call. This test replaces run_statusline_wizard
        with a spy and drives cmd_install through an interactive tty stub to confirm the
        wizard is reached.
        """
        called = {}
        orig = setup.run_statusline_wizard
        setup.run_statusline_wizard = lambda paths, tty, dry: called.setdefault("ok", True)
        self.addCleanup(lambda: setattr(setup, "run_statusline_wizard", orig))
        # Feed a tty that looks interactive to is_interactive() and selects
        # "Status line" (option 2 in the E5b two-option menu) then quits.
        tty = io.StringIO("2\nq\n")
        # cmd_install(env, tty, dry) — pass an env dict, NOT a resolved Paths namedtuple.
        setup.cmd_install(dict(os.environ), tty, dry=True)
        self.assertTrue(called.get("ok"),
                        "run_statusline_wizard was not called — check the Status-line branch in cmd_install")


if __name__ == "__main__":
    unittest.main()
