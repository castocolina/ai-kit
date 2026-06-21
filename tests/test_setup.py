import importlib.util
import io
import json
import os
import re
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
                         [["path", "branch", "worktree", "dirty", "todo"],
                          ["model", "time_ago", "clock", "effort", "lines",
                           "cost", "total_time", "api_time"],
                          ["render_time", "dimensions", "context",
                           "chat_size", "memory", "rate_limits", "slowest"]])

    def test_layout_defaults_match_status_line(self):
        # Drift guard: setup.LAYOUT_DEFAULTS must mirror the canonical default
        # LAYOUT in tools/status-line.py (the renderer's source of truth), so the
        # wizard's default layout can never silently diverge — e.g. dropping the
        # worktree segment from the identity row (the T4.2 regression).
        sl_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "tools", "status-line.py")
        spec = importlib.util.spec_from_file_location("status_line_drift", sl_path)
        sl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sl)
        expected = [{"min_rows": ln.min_rows, "segments": list(ln.segments)}
                    for ln in sl.LAYOUT]
        self.assertEqual(setup.LAYOUT_DEFAULTS, expected)

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
    return [(i, x, y) for i, (x, y) in enumerate(zip(al, bl, strict=False)) if x != y] + \
           [("len", len(al), len(bl))] if len(al) != len(bl) else \
           [(i, x, y) for i, (x, y) in enumerate(zip(al, bl, strict=False)) if x != y]


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


class TestDiscoverExampleSegments(unittest.TestCase):
    """T5.1: scan examples/segments/, parse the '# ai-kit-segment:' header for
    id=, and offer every example pre-checked (default ON)."""

    _HEADER = ("#!/usr/bin/env python3\n"
               "# ai-kit-segment: line=1 after=context id=sysmem ttl=10\n"
               "import sys\n")

    def _mk(self, body, name="sysmem"):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        p = os.path.join(d, name)
        with open(p, "w") as f:
            f.write(body)
        return d, p

    def test_parse_segment_header_extracts_fields(self):
        fields = setup._parse_segment_header(self._HEADER)
        self.assertEqual(fields["id"], "sysmem")
        self.assertEqual(fields["ttl"], "10")
        self.assertEqual(fields["after"], "context")

    def test_parse_segment_header_none_when_absent(self):
        self.assertIsNone(setup._parse_segment_header("#!/bin/sh\necho hi\n"))

    def test_parse_segment_header_mirrors_renderer_whitespace(self):
        # T5.5 (G5 M1): must accept EXACTLY the forms the renderer's _SEG_HEADER_RE
        # (^#\s*ai-kit-segment:\s*(.*?)\s*$) accepts — extra spaces after '#', no
        # space at all, and extra spaces after the colon — so setup and
        # status-line.py never disagree on which files are valid providers.
        for hdr in ("#  ai-kit-segment: id=x ttl=5\n",
                    "#ai-kit-segment: id=x\n",
                    "# ai-kit-segment:   id=x\n"):
            fields = setup._parse_segment_header(hdr)
            self.assertIsNotNone(fields, hdr)
            self.assertEqual(fields["id"], "x", hdr)
        # ...and REJECTS a leading-indented marker, exactly as the renderer does
        # (the marker sits at column 0) — no inverted installer/renderer drift.
        self.assertIsNone(setup._parse_segment_header("   # ai-kit-segment: id=x\n"))

    def test_seg_header_regex_literal_matches_renderer(self):
        # C3a (C3 review M1): drift guard — setup and status-line.py cannot import
        # each other (hyphenated filename), so the `# ai-kit-segment:` matcher is
        # duplicated. Pin the two compiled-pattern LITERALS byte-identical so a
        # future edit to one regex can't silently diverge installer from renderer
        # (the behavioral test above only checks fixed example strings).
        sl_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "tools", "status-line.py")
        spec = importlib.util.spec_from_file_location("status_line_hdr_drift", sl_path)
        sl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sl)
        self.assertEqual(setup._SEG_HEADER_RE.pattern, sl._SEG_HEADER_RE.pattern)

    def test_discover_finds_sysmem_pre_checked(self):
        d, _ = self._mk(self._HEADER)
        found = setup.discover_example_segments(d)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["id"], "sysmem")
        self.assertTrue(found[0]["default_on"])           # offered pre-checked

    def test_discover_skips_files_without_marker(self):
        d, _ = self._mk("#!/bin/sh\necho plain\n", name="plain")
        self.assertEqual(setup.discover_example_segments(d), [])

    def test_discover_missing_dir_is_empty(self):
        self.assertEqual(
            setup.discover_example_segments("/no/such/dir/xyz"), [])

    def test_discover_real_examples_dir(self):
        # Integration: the shipped examples/segments/ must expose sysmem.
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        found = setup.discover_example_segments(
            os.path.join(repo, "examples", "segments"))
        self.assertIn("sysmem", {e["id"] for e in found})


class TestInstallExampleSegments(unittest.TestCase):
    """T5.2: copy chosen examples into the XDG-aware segments dir, chmod +x,
    enable segments.<id>, idempotent."""

    _BODY = ("#!/usr/bin/env python3\n"
             "# ai-kit-segment: line=1 after=context id=sysmem ttl=10\n"
             "print('hi')\n")

    def setUp(self):
        self.src_dir = tempfile.mkdtemp()
        self.cfg_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.src_dir, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.cfg_dir, ignore_errors=True)
        src = os.path.join(self.src_dir, "sysmem")
        with open(src, "w") as f:
            f.write(self._BODY)
        self.examples = [{"id": "sysmem", "name": "sysmem", "path": src,
                          "default_on": True}]

    def _dest(self):
        return os.path.join(self.cfg_dir, "segments", "sysmem")

    def test_install_copies_chmods_and_enables(self):
        seg = {}
        ids = setup.install_example_segments(self.examples, self.cfg_dir, seg)
        self.assertEqual(ids, ["sysmem"])
        self.assertTrue(os.path.isfile(self._dest()))
        self.assertTrue(os.access(self._dest(), os.X_OK))     # executable
        with open(self._dest()) as f:
            self.assertEqual(f.read(), self._BODY)            # content copied
        self.assertTrue(seg["sysmem"])                        # toggle flipped on

    def test_install_is_idempotent(self):
        setup.install_example_segments(self.examples, self.cfg_dir, {})
        setup.install_example_segments(self.examples, self.cfg_dir, {})
        seg_dir = os.path.join(self.cfg_dir, "segments")
        self.assertEqual(os.listdir(seg_dir), ["sysmem"])     # no duplicate
        self.assertTrue(os.access(self._dest(), os.X_OK))

    def test_install_refreshes_changed_file(self):
        # A stale copy already present is updated to the source bytes.
        os.makedirs(os.path.join(self.cfg_dir, "segments"))
        with open(self._dest(), "w") as f:
            f.write("#!/bin/sh\necho OLD\n")
        setup.install_example_segments(self.examples, self.cfg_dir, {})
        with open(self._dest()) as f:
            self.assertEqual(f.read(), self._BODY)

    def test_install_skips_bad_dest_without_aborting(self):
        # T5.5 (G5 H1): a destination that already exists as a directory (an
        # unwritable/blocked dest) must NOT crash the whole install — that one
        # provider is skipped and the others still install.
        seg_dir = os.path.join(self.cfg_dir, "segments")
        os.makedirs(os.path.join(seg_dir, "sysmem"))    # dest name pre-exists as a dir
        good_src = os.path.join(self.src_dir, "other")
        with open(good_src, "w") as f:
            f.write(self._BODY)
        examples = [self.examples[0],
                    {"id": "other", "name": "other", "path": good_src,
                     "default_on": True}]
        ids = setup.install_example_segments(examples, self.cfg_dir, {})
        self.assertEqual(ids, ["other"])                # bad skipped, good kept
        self.assertTrue(os.path.isfile(os.path.join(seg_dir, "other")))
        self.assertTrue(os.access(os.path.join(seg_dir, "other"), os.X_OK))

    def test_install_is_xdg_aware(self):
        # config_dir comes from resolve_paths → XDG_CONFIG_HOME/ai-kit; the copy
        # must land under $XDG_CONFIG_HOME/ai-kit/segments/, not a hardcoded ~.
        xdg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, xdg, ignore_errors=True)
        paths = setup.resolve_paths({"XDG_CONFIG_HOME": xdg, "HOME": xdg})
        setup.install_example_segments(self.examples, paths.config_dir, {})
        landed = os.path.join(xdg, "ai-kit", "segments", "sysmem")
        self.assertTrue(os.path.isfile(landed))


class TestSelectExamples(unittest.TestCase):
    """T5.3: headless flag contract `--examples=all|none|<ids>`. Headless/flag
    paths NEVER prompt; flags/defaults govern selection."""

    def _ex(self, *ids):
        return [{"id": i, "name": i, "path": f"/x/{i}", "default_on": True}
                for i in ids]

    def _ids(self, chosen):
        return [e["id"] for e in chosen]

    # ---- pure resolver ----
    def test_resolve_default_none_is_all(self):
        ex = self._ex("sysmem", "cost")
        self.assertEqual(self._ids(setup.resolve_example_selection(None, ex)),
                         ["sysmem", "cost"])

    def test_resolve_all_and_none(self):
        ex = self._ex("sysmem", "cost")
        self.assertEqual(self._ids(setup.resolve_example_selection("all", ex)),
                         ["sysmem", "cost"])
        self.assertEqual(setup.resolve_example_selection("none", ex), [])
        self.assertEqual(setup.resolve_example_selection("ALL", ex), ex)   # case-insens
        self.assertEqual(setup.resolve_example_selection("None", ex), [])

    def test_resolve_explicit_ids(self):
        ex = self._ex("sysmem", "cost", "weather")
        self.assertEqual(self._ids(setup.resolve_example_selection("sysmem,weather", ex)),
                         ["sysmem", "weather"])
        # space/comma tolerant, unknown ids ignored
        self.assertEqual(self._ids(setup.resolve_example_selection("cost nope", ex)),
                         ["cost"])

    # ---- select_examples: headless / flag never prompts ----
    def test_select_headless_no_flag_is_all(self):
        ex = self._ex("sysmem")
        self.assertEqual(setup.select_examples(ex, None, tty=None), ex)

    def test_select_headless_flag_governs(self):
        ex = self._ex("sysmem", "cost")
        self.assertEqual(setup.select_examples(ex, "none", tty=None), [])
        self.assertEqual(self._ids(setup.select_examples(ex, "cost", tty=None)),
                         ["cost"])

    def test_select_flag_bypasses_prompt_even_with_tty(self):
        # An explicit --examples flag must short-circuit the interactive offer.
        ex = self._ex("sysmem")
        with mock.patch.object(setup, "chip_select") as cs, \
             mock.patch.object(setup, "_mode_a_available", return_value=True):
            result = setup.select_examples(ex, "none", tty=object())
        cs.assert_not_called()
        self.assertEqual(result, [])

    def test_select_interactive_mode_a_delegates(self):
        ex = self._ex("sysmem", "cost")

        def fake_chip(sel, stdin, stdout, env, preview=None):
            sel.set_all(False)
            sel.items[0][2] = True            # keep only the first (sysmem)
            return sel

        with mock.patch.object(setup, "_mode_a_available", return_value=True), \
             mock.patch.object(setup, "chip_select", side_effect=fake_chip):
            result = setup.select_examples(ex, None, tty=object())
        self.assertEqual(self._ids(result), ["sysmem"])

    def test_select_interactive_incapable_terminal_keeps_pre_checked(self):
        # Gate closed (dumb/narrow tty): no chip prompt — accept the pre-checked
        # default (every example, default-ON).
        ex = self._ex("sysmem", "cost")
        with mock.patch.object(setup, "_mode_a_available", return_value=False), \
             mock.patch.object(setup, "chip_select") as cs:
            result = setup.select_examples(ex, None, tty=object())
        cs.assert_not_called()
        self.assertEqual(result, ex)

    def test_main_parses_examples_flag(self):
        # --examples is accepted by the CLI and reaches cmd_install.
        with mock.patch.object(setup, "cmd_install", return_value=0) as ci, \
             mock.patch.object(setup, "open_tty", return_value=None):
            setup.main(["install", "--examples=none"])
        self.assertEqual(ci.call_args.kwargs.get("examples_flag"), "none")


class TestWizardLoop(unittest.TestCase):
    def _state(self):
        return {"segments": dict(setup.SEGMENT_DEFAULTS),
                "layout": [{"min_rows": 0, "segments": ["path", "branch", "dirty"]},
                           {"min_rows": 20, "segments": ["model", "clock"]}],
                "dirty": False}

    def test_toggle_by_number_flips_segment(self):
        st = self._state()
        order = setup._wizard_order(st)         # numbering is display order
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
        order = setup._wizard_order(st)
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
        _st, err = setup._apply_wizard_command(self._state(), "frobnicate")
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


class TestWizardMenu(unittest.TestCase):
    """Polished mode-B numbered menu: grouped by layout row, contiguous
    display-order numbering shared with the toggle resolver, a redundant on/off
    word column, and an ASCII preview footer."""

    def _state(self):
        return {
            "segments": {"path": True, "branch": True, "dirty": False,
                         "model": True, "clock": True, "cost": False},
            "layout": [{"min_rows": 0, "segments": ["path", "branch", "dirty"]},
                       {"min_rows": 20, "segments": ["model", "clock"]}],
            "dirty": False,
        }

    def test_wizard_order_is_layout_then_sorted_rest(self):
        # layout rows in row order, then any non-laid-out segment (sorted).
        self.assertEqual(
            setup._wizard_order(self._state()),
            ["path", "branch", "dirty", "model", "clock", "cost"])

    def test_menu_numbers_are_contiguous_in_display_order(self):
        buf = io.StringIO()
        setup._print_segments(buf, self._state())
        nums = [int(m) for m in re.findall(r"^\s*(\d+)\.", buf.getvalue(), re.M)]
        self.assertEqual(nums, [1, 2, 3, 4, 5, 6])     # 1..n, no gaps

    def test_menu_groups_segments_by_layout_row(self):
        out = io.StringIO()
        setup._print_segments(out, self._state())
        text = out.getvalue()
        self.assertIn("identity line", text)
        self.assertIn("model line", text)
        self.assertIn("not in layout", text)           # trailing group for cost
        self.assertLess(text.index("model line"), text.index("not in layout"))
        self.assertLess(text.index("not in layout"), text.index("cost"))

    def test_menu_shows_on_off_word_column(self):
        out = io.StringIO()
        setup._print_segments(out, self._state())
        # strip SGR escapes so the word column is matched on plain text
        lines = [setup._ANSI_RE.sub("", l) for l in out.getvalue().splitlines()]
        dirty_line = next(l for l in lines if re.search(r"\bdirty\b", l))
        path_line = next(l for l in lines if re.search(r"\bpath\b", l))
        self.assertIn("off", dirty_line)               # disabled → word 'off'
        self.assertIn("on", path_line)                 # enabled → word 'on'

    def test_menu_number_matches_displayed_toggle(self):
        # The visible-order contract: typing N flips the Nth displayed segment.
        st = self._state()
        for n, key in enumerate(setup._wizard_order(st), 1):
            before = st["segments"][key]
            st2, err = setup._apply_wizard_command(st, str(n))
            self.assertIsNone(err)
            self.assertEqual(st2["segments"][key], not before)

    def test_menu_rejects_out_of_range_number(self):
        st = self._state()
        st2, err = setup._apply_wizard_command(st, str(len(st["segments"]) + 5))
        self.assertIsNotNone(err)
        self.assertEqual(st2, st)                       # unchanged, no raise

    def test_menu_all_on_and_none_off(self):
        st = self._state()
        on, err = setup._apply_wizard_command(st, "a")
        self.assertIsNone(err)
        self.assertTrue(all(on["segments"].values()))
        self.assertTrue(on["dirty"])
        off, err = setup._apply_wizard_command(st, "n")
        self.assertIsNone(err)
        self.assertFalse(any(off["segments"].values()))

    def test_preview_footer_ascii_prefix_and_truncates(self):
        colored = "\033[36mhello\033[0m world this is a very long status-line bar"
        lines = setup._preview_lines(colored, cols=20)
        self.assertTrue(all(l.startswith("  preview | ") for l in lines))
        self.assertNotIn("▏", "".join(lines))      # no ▏ box-drawing glyph
        for l in lines:
            self.assertLessEqual(setup._visible_len(l), 20)

    def test_preview_footer_unavailable_when_empty(self):
        lines = setup._preview_lines("", cols=80)
        self.assertEqual(len(lines), 1)
        self.assertIn("(preview unavailable)", lines[0])


class _FakeStream:
    def __init__(self, isatty=True, encoding="utf-8"):
        self._isatty = isatty
        self.encoding = encoding

    def isatty(self):
        return self._isatty


class TestModeAChips(unittest.TestCase):
    """Mode-A (arrow-key chip selector) pure helpers: the conjunctive activation
    gate, glyph/ASCII selection, scroll-window clamp, key parse, and the pure
    frame builder. The interactive loop itself is covered by the T4.5 pty E2E."""

    def _env(self, **over):
        env = {"TERM": "xterm-256color", "COLUMNS": "100", "LINES": "40"}
        env.update(over)
        return env

    def _sel(self, n=4, cursor=0):
        s = setup.Selection([("seg", f"item{i}", i % 2 == 0) for i in range(n)])
        s.cursor = cursor
        return s

    # ---- gate ----
    def test_gate_passes_when_all_conditions_hold(self):
        self.assertTrue(setup._mode_a_available(
            self._env(), _FakeStream(), _FakeStream()))

    def test_gate_fails_without_tty(self):
        self.assertFalse(setup._mode_a_available(
            self._env(), _FakeStream(isatty=False), _FakeStream()))
        self.assertFalse(setup._mode_a_available(
            self._env(), _FakeStream(), _FakeStream(isatty=False)))

    def test_gate_fails_on_dumb_or_empty_term(self):
        for term in ("dumb", ""):
            self.assertFalse(setup._mode_a_available(
                self._env(TERM=term), _FakeStream(), _FakeStream()))

    def test_gate_fails_when_terminal_too_small(self):
        self.assertFalse(setup._mode_a_available(
            self._env(COLUMNS="39"), _FakeStream(), _FakeStream()))
        self.assertFalse(setup._mode_a_available(
            self._env(LINES="7"), _FakeStream(), _FakeStream()))

    def test_gate_fails_when_aikit_plain_set(self):
        self.assertFalse(setup._mode_a_available(
            self._env(AIKIT_PLAIN="1"), _FakeStream(), _FakeStream()))

    def test_gate_ignores_no_color(self):
        # NO_COLOR strips color in rendering but must NOT disable mode A.
        self.assertTrue(setup._mode_a_available(
            self._env(NO_COLOR="1"), _FakeStream(), _FakeStream()))

    # ---- glyphs ----
    def test_chip_glyphs_unicode_by_default(self):
        g = setup._chip_glyphs(self._env(), _FakeStream(encoding="utf-8"))
        self.assertEqual(g["on"], "◉")
        self.assertEqual(g["cursor"], "❯")

    def test_chip_glyphs_ascii_on_dumb_term(self):
        g = setup._chip_glyphs(self._env(TERM="dumb"), _FakeStream())
        self.assertEqual(g["on"], "[x]")
        self.assertEqual(g["cursor"], ">")

    def test_chip_glyphs_ascii_when_encoding_cannot_represent(self):
        g = setup._chip_glyphs(self._env(), _FakeStream(encoding="ascii"))
        self.assertEqual(g["off"], "[ ]")

    def test_chip_glyphs_unicode_survives_no_color(self):
        g = setup._chip_glyphs(self._env(NO_COLOR="1"), _FakeStream(encoding="utf-8"))
        self.assertEqual(g["on"], "◉")          # NO_COLOR keeps glyphs

    # ---- window clamp ----
    def test_window_clamp_returns_zero_when_everything_fits(self):
        self.assertEqual(setup._clamp_window(3, 5, 10), 0)

    def test_window_clamp_keeps_cursor_visible(self):
        for cursor in range(20):
            top = setup._clamp_window(cursor, 20, 5)
            self.assertTrue(0 <= top <= cursor < top + 5)
            self.assertLessEqual(top, 20 - 5)

    def test_window_clamp_at_end_of_list(self):
        self.assertEqual(setup._clamp_window(19, 20, 5), 15)

    # ---- key parse ----
    def test_chip_parse_key_arrows_and_vim(self):
        self.assertEqual(setup._parse_key("\x1b[A"), "up")
        self.assertEqual(setup._parse_key("k"), "up")
        self.assertEqual(setup._parse_key("\x1b[B"), "down")
        self.assertEqual(setup._parse_key("j"), "down")

    def test_chip_parse_key_actions(self):
        self.assertEqual(setup._parse_key(" "), "toggle")
        self.assertEqual(setup._parse_key("a"), "all")
        self.assertEqual(setup._parse_key("n"), "none")
        self.assertEqual(setup._parse_key("\r"), "accept")
        self.assertEqual(setup._parse_key("\n"), "accept")
        for c in ("\x1b", "q", "\x03"):
            self.assertEqual(setup._parse_key(c), "cancel")

    def test_chip_parse_key_unknown_is_none(self):
        self.assertIsNone(setup._parse_key("z"))

    # ---- pure frame builder ----
    def test_chip_frame_focused_row_is_reverse_video(self):
        g = setup._chip_glyphs(self._env(), _FakeStream())
        lines = setup._chip_frame(self._sel(cursor=0), g, 100, 40)
        self.assertIn("\033[7m", lines[0])           # focused row reverse-video
        self.assertIn("\033[27m", lines[0])

    def test_chip_frame_shows_scroll_affordances_when_overflowing(self):
        g = setup._chip_glyphs(self._env(), _FakeStream())
        # 20 items, tiny terminal → must window + show ▲/▼ N more
        lines = setup._chip_frame(self._sel(n=20, cursor=10), g, 100, 12)
        joined = "\n".join(lines)
        self.assertIn("more", joined)
        self.assertTrue("▲" in joined or "▼" in joined)

    def test_chip_frame_includes_preview_and_hint(self):
        g = setup._chip_glyphs(self._env(), _FakeStream())
        lines = setup._chip_frame(self._sel(), g, 100, 40, preview="THE-BAR")
        joined = "\n".join(lines)
        self.assertIn("preview", joined)
        self.assertIn("THE-BAR", joined)
        self.assertIn("toggle", lines[-1])           # key-hint footer last

    def test_chip_frame_truncates_every_line_to_width(self):
        g = setup._chip_glyphs(self._env(), _FakeStream())
        sel = setup.Selection([("seg", "x" * 200, True)])
        lines = setup._chip_frame(sel, g, 20, 40, preview="y" * 200)
        for ln in lines:
            self.assertLessEqual(setup._visible_len(ln), 19)   # cols-1

    def test_chip_frame_no_severed_escape_sequences(self):
        # Narrow terminal: truncation must never cut mid-escape nor leave a
        # spurious/dangling ESC fragment once balanced SGR codes are stripped.
        g = setup._chip_glyphs(self._env(), _FakeStream())
        sel = self._sel(n=10, cursor=3)
        for cols in (40, 25, 20):
            for ln in setup._chip_frame(sel, g, cols, 40, preview="z" * 80):
                self.assertNotIn("\x1b", setup._ANSI_RE.sub("", ln))

    def test_chip_frame_plain_hint_has_no_spurious_reset(self):
        # The (uncolored) hint line must not carry a trailing reset it never opened.
        g = setup._chip_glyphs(self._env(), _FakeStream())
        lines = setup._chip_frame(self._sel(), g, 100, 40)
        self.assertNotIn("\033[0m", lines[-1])

    def test_chip_frame_shows_selection_tally(self):
        g = setup._chip_glyphs(self._env(), _FakeStream())
        lines = setup._chip_frame(self._sel(n=4), g, 100, 40)   # items 0,2 on → 2/4
        self.assertIn("(2/4 on)", lines[-1])

    # ---- _read_key disconnect / ESC handling (T4.6: H1, M1) ----
    def _fd_stdin(self, fd=7):
        s = _FakeStream()
        s.fileno = lambda: fd
        return s

    def test_read_key_oserror_is_cancel(self):
        # H1: terminal disconnect makes os.read raise OSError(EIO). _read_key
        # must surface it as a cancel (KeyboardInterrupt), never crash the run.
        with mock.patch.object(setup.os, "read", side_effect=OSError(5, "EIO")), \
                self.assertRaises(KeyboardInterrupt):
            setup._read_key(self._fd_stdin())

    def test_read_key_eof_is_cancel(self):
        # H1: platforms that return b"" at EOF instead of raising must also
        # cancel — not spin (b"" → _parse_key("") → None → 100% CPU busy-loop).
        with mock.patch.object(setup.os, "read", return_value=b""), \
                self.assertRaises(KeyboardInterrupt):
            setup._read_key(self._fd_stdin())

    def test_read_key_esc_then_letter_not_dropped(self):
        # M1: ESC followed by a non-'[' byte must not be silently swallowed —
        # the trailing key is acted on, not lost.
        reads = [b"\x1b", b"a"]
        with mock.patch.object(setup.os, "read",
                               side_effect=lambda fd, n: reads.pop(0)), \
             mock.patch("select.select", return_value=([7], [], [])):
            self.assertEqual(setup._read_key(self._fd_stdin()), "a")

    def test_read_key_lone_esc_is_cancel(self):
        # A lone ESC (nothing pending within the disambiguation window) cancels.
        with mock.patch.object(setup.os, "read", return_value=b"\x1b"), \
             mock.patch("select.select", return_value=([], [], [])):
            self.assertEqual(setup._read_key(self._fd_stdin()), "\x1b")

    def test_read_key_arrow_sequence_still_parses(self):
        # Regression: ESC '[' B (down-arrow) still resolves through the new path.
        reads = [b"\x1b", b"[", b"B"]
        with mock.patch.object(setup.os, "read",
                               side_effect=lambda fd, n: reads.pop(0)), \
             mock.patch("select.select", return_value=([7], [], [])):
            self.assertEqual(setup._read_key(self._fd_stdin()), "\x1b[B")


class TestRawMode(unittest.TestCase):
    """The termios raw-mode context manager guarantees terminal teardown on
    every exit path (normal, exception, SIGINT)."""

    @mock.patch.object(setup, "signal")
    @mock.patch.object(setup, "_termmode")
    @mock.patch.object(setup, "termios")
    def test_raw_mode_restores_terminal_on_exception(self, termios, termmode, sig):
        termios.tcgetattr.return_value = "SAVED"
        stream = io.StringIO()
        with self.assertRaises(ValueError), setup.RawMode(7, stream):
            raise ValueError("boom")
        termios.tcgetattr.assert_called_once_with(7)         # state saved
        termmode.setraw.assert_called_once_with(7)           # entered raw
        termios.tcsetattr.assert_called_once_with(           # restored via TCSADRAIN
            7, termios.TCSADRAIN, "SAVED")
        out = stream.getvalue()
        self.assertIn("\033[?25l", out)                      # cursor hidden on enter
        self.assertIn("\033[?25h", out)                      # cursor shown on exit

    @mock.patch.object(setup, "signal")
    @mock.patch.object(setup, "_termmode")
    @mock.patch.object(setup, "termios")
    def test_raw_mode_sigint_restores_and_exits_130(self, termios, termmode, sig):
        termios.tcgetattr.return_value = "SAVED"
        stream = io.StringIO()
        rm = setup.RawMode(3, stream)
        rm.__enter__()
        with self.assertRaises(SystemExit) as cm:
            rm._on_sigint(2, None)
        self.assertEqual(cm.exception.code, 130)             # 128 + SIGINT
        termios.tcsetattr.assert_called_once_with(3, termios.TCSADRAIN, "SAVED")
        self.assertTrue(stream.getvalue().endswith("\n"))    # newline after restore

    @mock.patch.object(setup, "signal")
    @mock.patch.object(setup, "_termmode")
    @mock.patch.object(setup, "termios")
    def test_raw_mode_teardown_survives_tcsetattr_error(self, termios, termmode, sig):
        # T4.7 / H2: a terminal disconnect can make tcsetattr raise during
        # teardown. That must NOT skip the cursor-show or the SIGINT-handler
        # restore, nor mask the body's exception by propagating its own.
        termios.tcgetattr.return_value = "SAVED"
        termios.error = Exception
        termios.tcsetattr.side_effect = Exception("EIO")
        sig.getsignal.return_value = "PREV"
        stream = io.StringIO()
        # the body's exception (not the tcsetattr error) is what propagates
        with self.assertRaises(ValueError), setup.RawMode(7, stream):
            raise ValueError("boom")
        self.assertIn("\033[?25h", stream.getvalue())        # cursor shown despite throw
        # prior SIGINT handler reinstalled despite the tcsetattr failure
        sig.signal.assert_any_call(sig.SIGINT, "PREV")

    @mock.patch.object(setup, "signal")
    @mock.patch.object(setup, "_termmode")
    @mock.patch.object(setup, "termios")
    def test_raw_mode_double_restore_is_idempotent(self, termios, termmode, sig):
        # The `active` guard makes a second teardown a no-op (e.g. SIGINT during
        # an already-exiting __exit__).
        termios.tcgetattr.return_value = "SAVED"
        stream = io.StringIO()
        rm = setup.RawMode(3, stream)
        rm.__enter__()
        rm._restore()
        termios.tcsetattr.reset_mock()
        rm._restore()                                        # second call: no-op
        termios.tcsetattr.assert_not_called()

    @mock.patch.object(setup, "signal")
    @mock.patch.object(setup, "_termmode", None)
    @mock.patch.object(setup, "termios", None)
    def test_raw_mode_is_noop_when_termios_unavailable(self, sig):
        stream = io.StringIO()
        with setup.RawMode(0, stream):                      # must not raise
            pass
        self.assertEqual(stream.getvalue(), "")              # nothing written


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
        self.assertTrue(setup.validate_entry(
            "commands", os.path.join(self.tmp, "commands", "doit.md")))
        self.assertFalse(setup.validate_entry(
            "commands", os.path.join(self.tmp, "commands", "bad.md")))
        self.assertFalse(setup.validate_entry(
            "commands", os.path.join(self.tmp, "commands", "notmd.txt")))

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
        stale = setup.prune_stale(self.claude, self.install, present={}, tty=tty,
                                  dry=False, counts=c)
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
        stale = setup.prune_stale(self.claude, self.install, present={}, tty=None,
                                  dry=False, counts=c)
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
        self.assertEqual(
            setup.predecessor_candidates(self.claude, self.install, self.entries()), [])

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


class TestSelectionModel(unittest.TestCase):
    """The shared in-memory pick model behind the install skill-picker and the
    status-line segment toggle: ordered (category, name) items + per-item
    enabled flag + a cursor. It owns ONLY what is on and where the cursor sits
    — never layout, dirtiness, or persistence."""

    def _sel(self):
        return setup.Selection([
            ("skills", "alpha", True),
            ("skills", "beta", False),
            ("commands", "doit.md", True),
        ])

    def test_len_and_initial_cursor(self):
        sel = self._sel()
        self.assertEqual(len(sel), 3)
        self.assertEqual(sel.cursor, 0)

    def test_toggle_flips_one_item(self):
        sel = self._sel()
        sel.toggle(1)
        self.assertTrue(sel.enabled_map()["beta"])
        sel.toggle(1)
        self.assertFalse(sel.enabled_map()["beta"])

    def test_toggle_cursor_flips_item_under_cursor(self):
        sel = self._sel()
        sel.cursor = 2
        sel.toggle_cursor()
        self.assertFalse(sel.enabled_map()["doit.md"])

    def test_set_all_true_then_false(self):
        sel = self._sel()
        sel.set_all(True)
        self.assertEqual(set(sel.enabled_map().values()), {True})
        sel.set_all(False)
        self.assertEqual(set(sel.enabled_map().values()), {False})

    def test_move_cursor_clamps_both_ends(self):
        sel = self._sel()
        sel.move_cursor(-5)
        self.assertEqual(sel.cursor, 0)
        sel.move_cursor(99)
        self.assertEqual(sel.cursor, 2)

    def test_category_sets_only_enabled(self):
        cats = self._sel().category_sets()
        self.assertEqual(cats["skills"], {"alpha"})
        self.assertEqual(cats["commands"], {"doit.md"})

    def test_enabled_map_covers_every_item(self):
        self.assertEqual(self._sel().enabled_map(),
                         {"alpha": True, "beta": False, "doit.md": True})

    def test_empty_selection_is_safe(self):
        sel = setup.Selection([])
        self.assertEqual(len(sel), 0)
        sel.toggle_cursor()          # no-op, must not raise
        sel.move_cursor(1)
        self.assertEqual(sel.cursor, 0)
        self.assertEqual(sel.enabled_map(), {})
        self.assertEqual(sel.category_sets(), {})


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

    def test_mode_a_selection_when_gate_open(self):
        # When _mode_a_available is True, select_skills drives the chip selector
        # (not the numbered menu) and projects its mutated Selection.
        installed = {"skills": {"alpha": "x"}, "commands": {}, "agents": {}}

        def fake_chip(sel, stdin, stdout, env, preview=None):
            sel.set_all(False)
            sel.items[0][2] = True               # first row is skills/alpha
            return sel

        with mock.patch.object(setup, "_mode_a_available", return_value=True), \
             mock.patch.object(setup, "chip_select", side_effect=fake_chip) as cs:
            result = setup.select_skills(self.entries(), installed, tty=object())
        cs.assert_called_once()
        self.assertEqual(result["skills"], {"alpha"})
        self.assertEqual(result["commands"], set())

    def test_mode_a_cancel_keeps_default(self):
        # esc/Ctrl-C in the chip selector (KeyboardInterrupt) keeps the default.
        installed = {"skills": {"alpha": "x", "beta": "x"}, "commands": {}, "agents": {}}
        with mock.patch.object(setup, "_mode_a_available", return_value=True), \
             mock.patch.object(setup, "chip_select", side_effect=KeyboardInterrupt):
            result = setup.select_skills(self.entries(), installed, tty=object())
        self.assertEqual(result["skills"], {"alpha", "beta"})

    def test_mode_a_error_falls_back_to_mode_b(self):
        # L2: a non-KeyboardInterrupt failure inside chip_select (e.g. a termios
        # error on a hostile terminal) must DEGRADE to the numbered menu, not
        # crash the installer. Here mode B reads the tty and Enter accepts.
        installed = {"skills": {}, "commands": {}, "agents": {}}
        with mock.patch.object(setup, "_mode_a_available", return_value=True), \
             mock.patch.object(setup, "chip_select",
                               side_effect=RuntimeError("boom")):
            result = setup.select_skills(
                self.entries(), installed, tty=io.StringIO("\n"))
        # fell through to mode B, accepted the first-run default (all on)
        self.assertEqual(result["skills"], {"alpha", "beta", "gamma"})

    def test_mode_b_when_gate_closed_does_not_call_chip(self):
        installed = {"skills": {}, "commands": {}, "agents": {}}
        with mock.patch.object(setup, "_mode_a_available", return_value=False), \
             mock.patch.object(setup, "chip_select") as cs:
            setup.select_skills(self.entries(), installed, tty=io.StringIO("\n"))
        cs.assert_not_called()

    def test_headless_equals_interactive_no_keypresses(self):
        # Strengthened contract: an interactive run that accepts immediately
        # (zero toggles — just Enter) yields EXACTLY the headless default for the
        # same inputs. Headless is interactive-with-zero-keypresses, not a
        # separate code path with its own defaulting.
        for installed in (
            {"skills": {}, "commands": {}, "agents": {}},                       # first run
            {"skills": {"alpha": "x", "beta": "x"}, "commands": {}, "agents": {}},  # NEW gamma off
        ):
            headless = setup.select_skills(self.entries(), installed, tty=None)
            interactive = setup.select_skills(
                self.entries(), installed, tty=io.StringIO("\n"))
            self.assertEqual(headless, interactive)


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
                                      "command": "python3 -S " + install_dir
                                      + "/tools/status-line.py"},
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
                        "run_statusline_wizard was not called — check the "
                        "Status-line branch in cmd_install")


if __name__ == "__main__":
    unittest.main()
