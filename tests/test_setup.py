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

try:
    import textual  # noqa: F401
    HAVE_TEXTUAL = True
except ImportError:
    HAVE_TEXTUAL = False


def _import_wizard_app():
    """Import the SAME wizard_app module object setup.launch_wizard imports.

    launch_wizard puts tools/ on sys.path and does ``import wizard_app`` (bare),
    so patching ``tools.wizard_app`` would patch a different module object and the
    real Textual TUI would launch (and hang). Importing the bare name here returns
    exactly the module launch_wizard will reuse from sys.modules."""
    tools_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import wizard_app  # pylint: disable=import-outside-toplevel
    return wizard_app

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
        self.assertFalse(seg["alt_cost"])             # alt_cost OFF by default
        self.assertFalse(seg["alt_term_dimensions"])  # dimensions OFF by default
        self.assertEqual(set(seg), set(setup.SEGMENT_DEFAULTS))

    def test_current_segments_merges_file_override(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[segments]\nalt_cost = true\nalt_process_memory = false\n")
            path = f.name
        self.addCleanup(os.unlink, path)
        seg = setup.current_segments(path)
        self.assertTrue(seg["alt_cost"])
        self.assertFalse(seg["alt_process_memory"])
        self.assertTrue(seg["path"])         # untouched default survives

    def test_current_layout_default_on_noop_recipe(self):
        layout = setup.current_layout(SAMPLE_RECIPE)
        self.assertEqual([r["segments"] for r in layout],
                         [["path", "git_branch", "alt_git_worktree", "git_dirty", "todo"],
                          ["model", "alt_time_ago", "alt_time_clock", "effort", "lines",
                           "alt_cost", "alt_time_session", "alt_time_api"],
                          ["render_time", "slowest", "alt_term_dimensions",
                           "context", "chat_size", "alt_process_memory", "alt_rate_limits"]])

    def test_layout_defaults_match_status_line(self):
        # Drift guard: setup.LAYOUT_DEFAULTS must mirror the canonical default
        # LAYOUT in tools/status-line.py (the renderer's source of truth), so the
        # wizard's default layout can never silently diverge — e.g. dropping the
        # worktree segment from the identity row (the T4.2 regression).
        sl_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "tools", "status-line.py")
        spec = importlib.util.spec_from_file_location("status_line_drift", sl_path)
        sl = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = sl       # register so @dataclass can resolve cls.__module__
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
        # alt_cost is OFF by default; turning it on must surface the 🪙 marker.
        seg = dict(setup.SEGMENT_DEFAULTS)
        seg["alt_cost"] = True
        with open(SAMPLE_INPUT) as f:
            sample_json = f.read()
        out = setup.render_preview(self._status_line(), seg, sample_json, {})
        self.assertIn("🪙", out)

    def test_preview_never_raises_on_renderer_error(self):
        # A bogus interpreter/path must degrade to an empty string, not crash.
        out = setup.render_preview("/no/such/status-line.py",
                                   dict(setup.SEGMENT_DEFAULTS), "{}", {})
        self.assertEqual(out, "")

    def test_preview_layout_produces_different_output_no_leak(self):
        """render_preview with a reordered layout yields different output; no temp files leaked."""
        seg = dict(setup.SEGMENT_DEFAULTS)
        with open(SAMPLE_INPUT) as f:
            sample_json = f.read()
        with open(SAMPLE_RECIPE, encoding="utf-8") as f:
            base_config = f.read()
        default_out = setup.render_preview(self._status_line(), seg, sample_json, {})
        # Reorder layout: swap segments so row 1 has model only (no path)
        reordered = [
            {"min_rows": 0, "segments": ["model"]},
            {"min_rows": 20, "segments": []},
        ]
        reorder_out = setup.render_preview(
            self._status_line(), seg, sample_json, {},
            layout=reordered, base_config=base_config,
        )
        self.assertNotEqual(default_out, reorder_out,
                            "layout reorder must change preview output")
        # No temp files leaked — nothing matching the prefix should exist in /tmp
        import glob as _glob  # pylint: disable=import-outside-toplevel
        leaked = _glob.glob("/tmp/ai_kit_preview_*.toml")
        self.assertEqual(leaked, [], f"temp file(s) leaked: {leaked}")


class TestPreviewFixture(unittest.TestCase):
    """Fixture-shape pin test (Task 3.3 / C.2 #7).

    Asserts that the checked-in sample-input.json fixture is rich enough for
    the real renderer to produce non-empty output that does NOT fall back to
    the "(preview unavailable)" sentinel.  This guards against fixture drift
    that would silently break the live-preview pane.
    """

    _STATUS_LINE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "tools", "status-line.py")
    _RECIPE = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "tools", "statusline.toml.sample")

    def test_fixture_drives_renderer_without_unavailable(self):
        """sample-input.json must produce a real render (not empty / unavailable)."""
        with open(setup._sample_input_path(), encoding="utf-8") as f:  # pylint: disable=protected-access
            sample = f.read()
        out = setup.render_preview(
            self._STATUS_LINE,
            setup.current_segments(self._RECIPE),
            sample,
            {},
        )
        self.assertTrue(out, "render_preview returned empty string — fixture may have drifted")
        self.assertNotIn("(preview unavailable)", out,
                         "render produced the unavailable sentinel — fixture may have drifted")


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
        out = setup.patch_segments(text, {"alt_time_clock": False})
        self.assertIn("alt_time_clock = false", out)
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
    def _statusline_doctor(self):
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tools", "statusline-doctor.py")

    def test_writes_valid_toml_and_validates(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statusline.toml")
            ok = setup.write_toml_preserving(
                path, "[segments]\nalt_cost = true\n", self._statusline_doctor())
            self.assertTrue(ok)
            with open(path) as f:
                self.assertIn("alt_cost = true", f.read())

    def test_rejects_broken_output_and_reverts(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statusline.toml")
            with open(path, "w") as f:
                f.write("# good original\n")
            # An unknown segment key fails the doctor.
            ok = setup.write_toml_preserving(
                path, "[segments]\nbogus_key = true\n", self._statusline_doctor())
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
               "# ai-kit-segment: line=1 after=context id=system_memory ttl=10\n"
               "import sys\n")

    def _mk(self, body, name="system_memory"):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        p = os.path.join(d, name)
        with open(p, "w") as f:
            f.write(body)
        return d, p

    def test_parse_segment_header_extracts_fields(self):
        fields = setup._parse_segment_header(self._HEADER)
        self.assertEqual(fields["id"], "system_memory")
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
        sys.modules[spec.name] = sl       # register so @dataclass can resolve cls.__module__
        spec.loader.exec_module(sl)
        self.assertEqual(setup._SEG_HEADER_RE.pattern, sl._SEG_HEADER_RE.pattern)

    def test_discover_finds_system_memory_pre_checked(self):
        d, _ = self._mk(self._HEADER)
        found = setup.discover_example_segments(d)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["id"], "system_memory")
        self.assertTrue(found[0]["default_on"])           # offered pre-checked

    def test_discover_skips_files_without_marker(self):
        d, _ = self._mk("#!/bin/sh\necho plain\n", name="plain")
        self.assertEqual(setup.discover_example_segments(d), [])

    def test_discover_missing_dir_is_empty(self):
        self.assertEqual(
            setup.discover_example_segments("/no/such/dir/xyz"), [])

    def test_discover_real_examples_dir(self):
        # Integration: the shipped examples/segments/ must expose system_memory.
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        found = setup.discover_example_segments(
            os.path.join(repo, "examples", "segments"))
        self.assertIn("system_memory", {e["id"] for e in found})

    def test_discover_surfaces_ui_metadata_with_fallbacks(self):
        full = ("#!/usr/bin/env python3\n"
                "# ai-kit-segment: id=full line=1 icon=💻 name=Full "
                "description=desc sample=9G\n")
        d, _ = self._mk(full)
        e = setup.discover_example_segments(d)[0]
        self.assertEqual(e["name"], "Full")
        self.assertEqual(e["description"], "desc")
        self.assertEqual(e["icon"], "💻")
        self.assertEqual(e["sample"], "9G")
        self.assertEqual(e["line"], 1)

    def test_discover_applies_fallbacks_for_id_only(self):
        d, _ = self._mk("# ai-kit-segment: id=bare\n")
        e = setup.discover_example_segments(d)[0]
        self.assertEqual(e["name"], "bare")          # id-as-name
        self.assertEqual(e["description"], "")       # blank
        self.assertEqual(e["icon"], setup.DEFAULT_SEGMENT_ICON)
        self.assertEqual(e["line"], len(setup.LAYOUT_DEFAULTS) - 1)  # last line

    def test_parse_quoted_values(self):
        """T0.1: quoted values with spaces parse to the full phrase."""
        hdr = ('# ai-kit-segment: id=system_memory name="System memory" '
               'description="System available RAM" sample="12.0 GiB free" '
               'icon=💻 line=1 after=context ttl=10\n')
        fields = setup._parse_segment_header(hdr)
        self.assertEqual(fields["name"], "System memory")
        self.assertEqual(fields["description"], "System available RAM")
        self.assertEqual(fields["sample"], "12.0 GiB free")
        # Unquoted tokens still parse correctly
        self.assertEqual(fields["id"], "system_memory")
        self.assertEqual(fields["line"], "1")
        self.assertEqual(fields["ttl"], "10")

    def test_parse_quoted_value_with_apostrophe(self):
        """T0.2: values with apostrophe/punctuation inside double quotes."""
        hdr = "# ai-kit-segment: id=x description=\"don't panic\" sample=ok\n"
        fields = setup._parse_segment_header(hdr)
        self.assertEqual(fields["description"], "don't panic")
        self.assertEqual(fields["sample"], "ok")

    def test_parse_id_only_header_unchanged(self):
        """T0.3: bare id-only header still parses (regression guard)."""
        hdr = "# ai-kit-segment: id=foo\n"
        fields = setup._parse_segment_header(hdr)
        self.assertEqual(fields, {"id": "foo"})

    def test_discover_real_examples_surfaces_quoted_description(self):
        """T0.5: shipped system_memory header uses quoted values; discover returns
        the real-space strings (not underscore-escaped)."""
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        found = setup.discover_example_segments(
            os.path.join(repo, "examples", "segments"))
        sm = next((e for e in found if e["id"] == "system_memory"), None)
        self.assertIsNotNone(sm, "system_memory not found in examples/segments/")
        self.assertEqual(sm["name"], "System memory")
        self.assertEqual(sm["description"], "System available RAM")
        self.assertEqual(sm["sample"], "12.0 GiB free")


class TestSelfDescribingHeader(unittest.TestCase):
    def test_parses_optional_ui_keys(self):
        text = ("#!/usr/bin/env python3\n"
                "# ai-kit-segment: id=demo line=2 icon=💻 name=DemoSeg "
                "description=shows_a_demo sample=42units\n")
        f = setup._parse_segment_header(text)
        self.assertEqual(f["id"], "demo")
        self.assertEqual(f["icon"], "💻")
        self.assertEqual(f["name"], "DemoSeg")
        self.assertEqual(f["description"], "shows_a_demo")
        self.assertEqual(f["sample"], "42units")

    def test_id_only_header_has_no_ui_keys(self):
        f = setup._parse_segment_header("# ai-kit-segment: id=bare\n")
        self.assertEqual(f["id"], "bare")
        self.assertNotIn("name", f)
        self.assertNotIn("description", f)


class TestInstallExampleSegments(unittest.TestCase):
    """T5.2: copy chosen examples into the XDG-aware segments dir, chmod +x,
    enable segments.<id>, idempotent."""

    _BODY = ("#!/usr/bin/env python3\n"
             "# ai-kit-segment: line=1 after=context id=system_memory ttl=10\n"
             "print('hi')\n")

    def setUp(self):
        self.src_dir = tempfile.mkdtemp()
        self.cfg_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.src_dir, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.cfg_dir, ignore_errors=True)
        src = os.path.join(self.src_dir, "system_memory")
        with open(src, "w") as f:
            f.write(self._BODY)
        self.examples = [{"id": "system_memory", "filename": "system_memory",
                          "name": "system_memory", "path": src, "default_on": True}]

    def _dest(self):
        return os.path.join(self.cfg_dir, "segments", "system_memory")

    def test_install_copies_chmods_and_enables(self):
        seg = {}
        ids = setup.install_example_segments(self.examples, self.cfg_dir, seg)
        self.assertEqual(ids, ["system_memory"])
        self.assertTrue(os.path.isfile(self._dest()))
        self.assertTrue(os.access(self._dest(), os.X_OK))     # executable
        with open(self._dest()) as f:
            self.assertEqual(f.read(), self._BODY)            # content copied
        self.assertTrue(seg["system_memory"])                 # toggle flipped on

    def test_install_is_idempotent(self):
        setup.install_example_segments(self.examples, self.cfg_dir, {})
        setup.install_example_segments(self.examples, self.cfg_dir, {})
        seg_dir = os.path.join(self.cfg_dir, "segments")
        self.assertEqual(os.listdir(seg_dir), ["system_memory"])  # no duplicate
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
        os.makedirs(os.path.join(seg_dir, "system_memory"))  # dest name pre-exists as a dir
        good_src = os.path.join(self.src_dir, "other")
        with open(good_src, "w") as f:
            f.write(self._BODY)
        examples = [self.examples[0],
                    {"id": "other", "filename": "other", "name": "other",
                     "path": good_src, "default_on": True}]
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
        landed = os.path.join(xdg, "ai-kit", "segments", "system_memory")
        self.assertTrue(os.path.isfile(landed))


class TestDiscoverInstallFilenameVsId(unittest.TestCase):
    """E2E: a segment whose filesystem filename differs from its header id/name
    must install to the filesystem filename, expose id for toggle, and name for UI.
    This tests the filename/id/name separation added in the Task-4 review fix."""

    _BODY = ("#!/usr/bin/env python3\n"
             "# ai-kit-segment: line=1 after=context id=cpu name=CPU_load ttl=10\n"
             "print('cpu')\n")

    def setUp(self):
        self.src_dir = tempfile.mkdtemp()
        self.cfg_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.src_dir, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.cfg_dir, ignore_errors=True)
        # Filesystem filename ("my_cpu_seg") differs from header id ("cpu") and name ("CPU_load")
        src = os.path.join(self.src_dir, "my_cpu_seg")
        with open(src, "w") as f:
            f.write(self._BODY)

    def test_discover_install_uses_filesystem_filename_not_id_or_name(self):
        examples = setup.discover_example_segments(self.src_dir)
        self.assertEqual(len(examples), 1)
        ex = examples[0]
        # id comes from header
        self.assertEqual(ex["id"], "cpu")
        # name (UI label) comes from header name=
        self.assertEqual(ex["name"], "CPU_load")
        # filename (copy destination) is the real filesystem filename
        self.assertEqual(ex["filename"], "my_cpu_seg")

        seg_state = {}
        ids = setup.install_example_segments(examples, self.cfg_dir, seg_state)

        # installed file lands at <segdir>/my_cpu_seg (filesystem filename)
        installed = os.path.join(self.cfg_dir, "segments", "my_cpu_seg")
        self.assertTrue(os.path.isfile(installed),
                        "file should be at my_cpu_seg, not cpu or CPU_load")
        # NOT at the id path
        self.assertFalse(os.path.isfile(os.path.join(self.cfg_dir, "segments", "cpu")))
        # NOT at the name path
        self.assertFalse(os.path.isfile(os.path.join(self.cfg_dir, "segments", "CPU_load")))
        # toggle uses id
        self.assertTrue(seg_state.get("cpu"), "toggle should be keyed on id=cpu")
        # return list uses id
        self.assertEqual(ids, ["cpu"])


class TestSelectExamples(unittest.TestCase):
    """T5.3: headless flag contract `--examples=all|none|<ids>`. Headless/flag
    paths NEVER prompt; flags/defaults govern selection."""

    def _ex(self, *ids):
        # Minimal dict for selection-only tests. Intentionally omits `filename`,
        # `description`, `icon`, `sample`, `line`, and `provenance` — those fields
        # are not consulted by select_examples / resolve_example_selection.
        return [{"id": i, "name": i, "path": f"/x/{i}", "default_on": True}
                for i in ids]

    def _ids(self, chosen):
        return [e["id"] for e in chosen]

    # ---- pure resolver ----
    def test_resolve_default_none_is_all(self):
        ex = self._ex("system_memory", "cost")
        self.assertEqual(self._ids(setup.resolve_example_selection(None, ex)),
                         ["system_memory", "cost"])

    def test_resolve_all_and_none(self):
        ex = self._ex("system_memory", "cost")
        self.assertEqual(self._ids(setup.resolve_example_selection("all", ex)),
                         ["system_memory", "cost"])
        self.assertEqual(setup.resolve_example_selection("none", ex), [])
        self.assertEqual(setup.resolve_example_selection("ALL", ex), ex)   # case-insens
        self.assertEqual(setup.resolve_example_selection("None", ex), [])

    def test_resolve_explicit_ids(self):
        ex = self._ex("system_memory", "cost", "weather")
        self.assertEqual(self._ids(setup.resolve_example_selection("system_memory,weather", ex)),
                         ["system_memory", "weather"])
        # space/comma tolerant, unknown ids ignored
        self.assertEqual(self._ids(setup.resolve_example_selection("cost nope", ex)),
                         ["cost"])

    # ---- select_examples: headless / flag never prompts ----
    def test_select_headless_no_flag_is_all(self):
        ex = self._ex("system_memory")
        self.assertEqual(setup.select_examples(ex, None, tty=None), ex)

    def test_select_headless_flag_governs(self):
        ex = self._ex("system_memory", "cost")
        self.assertEqual(setup.select_examples(ex, "none", tty=None), [])
        self.assertEqual(self._ids(setup.select_examples(ex, "cost", tty=None)),
                         ["cost"])

    def test_main_parses_examples_flag(self):
        # --examples is accepted by the CLI and reaches cmd_install.
        fake_tty = io.StringIO()
        with mock.patch.object(setup, "ensure_rich_runtime"), \
             mock.patch.object(setup, "cmd_install", return_value=0) as ci, \
             mock.patch.object(setup, "open_tty", return_value=fake_tty), \
             mock.patch.object(fake_tty, "close", return_value=None):
            setup.main(["install", "--examples=none"])
        self.assertEqual(ci.call_args.kwargs.get("examples_flag"), "none")


class TestWizardLoop(unittest.TestCase):
    def _state(self):
        return {"segments": dict(setup.SEGMENT_DEFAULTS),
                "layout": [{"min_rows": 0,
                            "segments": ["path", "git_branch", "git_dirty"]},
                           {"min_rows": 20, "segments": ["model", "alt_time_clock"]}],
                "dirty": False}

    def test_toggle_by_number_flips_segment(self):
        st = self._state()
        order = setup._wizard_order(st)         # numbering is display order
        idx = order.index("alt_cost") + 1
        st2, err = setup._apply_wizard_command(st, str(idx))
        self.assertIsNone(err)
        self.assertTrue(st2["segments"]["alt_cost"])
        self.assertTrue(st2["dirty"])

    def test_move_up_reorders_within_line(self):
        st, err = setup._apply_wizard_command(self._state(), "move git_branch up")
        self.assertIsNone(err)
        self.assertEqual(st["layout"][0]["segments"][:2], ["git_branch", "path"])

    def test_move_down_reorders_within_line(self):
        st, err = setup._apply_wizard_command(self._state(), "move path down")
        self.assertIsNone(err)
        self.assertEqual(st["layout"][0]["segments"][:2], ["git_branch", "path"])

    def test_move_across_lines(self):
        st, err = setup._apply_wizard_command(self._state(), "move alt_time_clock line 1")
        self.assertIsNone(err)
        self.assertIn("alt_time_clock", st["layout"][0]["segments"])
        self.assertNotIn("alt_time_clock", st["layout"][1]["segments"])

    def test_worktree_is_a_normal_segment(self):
        # worktree migrated from the [git] knob to a regular segment toggle: it
        # appears in SEGMENT_DEFAULTS (OFF by default — opt-in) and flips like any other segment.
        self.assertFalse(setup.SEGMENT_DEFAULTS.get("alt_git_worktree"))
        st = self._state()
        order = setup._wizard_order(st)
        idx = order.index("alt_git_worktree") + 1
        st2, err = setup._apply_wizard_command(st, str(idx))
        self.assertIsNone(err)
        self.assertTrue(st2["segments"]["alt_git_worktree"])    # was OFF, toggled ON
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
        # toggles alt_cost on and preserves the palette section.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statusline.toml")
            with open(SAMPLE_RECIPE) as f:
                original = f.read()
            with open(path, "w") as f:
                f.write(original)
            statusline_doctor = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "tools", "statusline-doctor.py")
            ok = setup.save_statusline_config(
                path, {"alt_cost": True}, None, statusline_doctor)
            self.assertTrue(ok)
            import tomllib
            with open(path, "rb") as f:
                parsed = tomllib.load(f)
            self.assertTrue(parsed["segments"]["alt_cost"])
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
        self.assertEqual(p.statusline_doctor,
                         "/home/u/.local/share/ai-kit/tools/statusline-doctor.py")

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

    def test_set_category_false_flips_only_target_category(self):
        sel = self._sel()
        sel.set_category("skills", False)
        self.assertFalse(sel.items[0][2])  # alpha: True → False
        self.assertFalse(sel.items[1][2])  # beta: False → stays False
        self.assertTrue(sel.items[2][2])   # doit.md: True → unchanged

    def test_set_category_true_flips_only_target_category(self):
        sel = self._sel()
        sel.set_category("skills", True)
        self.assertTrue(sel.items[0][2])   # alpha: True → stays True
        self.assertTrue(sel.items[1][2])   # beta: False → True
        self.assertTrue(sel.items[2][2])   # doit.md: True → unchanged


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

    def test_headless_first_run_links_all_and_wires_statusline(self):
        # launch_wizard is patched to apply the default selection AND adopt the
        # status line (matching first-run all-on + adopt behaviour) WITHOUT the
        # Textual TUI. After Task 10 the statusLine wiring + recipe copy are gated
        # on the wizard's adopt decision via persist_statusline — not pre-wizard.
        def _apply_defaults(paths, entries, installed, tty, dry, counts):
            default = setup._default_selection(entries, installed)
            setup.apply_selection(default, entries, paths.claude_dir, dry, counts)
            state = {"segments": dict(setup.SEGMENT_DEFAULTS),
                     "layout": [dict(l) for l in setup.LAYOUT_DEFAULTS],
                     "dirty": False, "adopt": True}
            setup.persist_statusline(paths, state, adopt=True, dry=dry, tty=tty)

        with mock.patch.object(setup, "launch_wizard", side_effect=_apply_defaults):
            rc = setup.cmd_install(self.env, tty=None, dry=False)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.islink(os.path.join(self.claude, "skills", "alpha")))
        with open(os.path.join(self.claude, "settings.json")) as f:
            self.assertIn("status-line.py", f.read())

    def test_components_only_run_does_not_wire_statusline(self):
        # Task 10 constraint 1: a wizard run that does NOT adopt (components-only)
        # must write no statusline.toml and never touch settings.json statusLine —
        # because cmd_install no longer wires the status line pre-wizard.
        def _components_only(paths, entries, installed, tty, dry, counts):
            default = setup._default_selection(entries, installed)
            setup.apply_selection(default, entries, paths.claude_dir, dry, counts)
            # no persist_statusline call — adopt is implicitly False

        with mock.patch.object(setup, "launch_wizard", side_effect=_components_only):
            rc = setup.cmd_install(self.env, tty=None, dry=False)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.islink(os.path.join(self.claude, "skills", "alpha")))
        self.assertFalse(os.path.isfile(
            os.path.join(self.tmp, ".config", "ai-kit", "statusline.toml")))
        settings = os.path.join(self.claude, "settings.json")
        if os.path.isfile(settings):
            with open(settings) as f:
                self.assertNotIn("statusLine", json.load(f))

    def test_dry_run_mutates_nothing(self):
        # launch_wizard patched to no-op so plain python3 never imports textual.
        with mock.patch.object(setup, "launch_wizard"):
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
        self.assertIn("/i/tools/statusline-doctor.py", args)
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


class TestOpenTty(unittest.TestCase):
    def test_dev_tty_opened_getpass_style(self):
        # /dev/tty must be opened via os.open + FileIO/TextIOWrapper (NOT
        # builtin open("r+"), which raises "not seekable" on every terminal).
        sentinel = object()
        with mock.patch.object(setup.os, "open", return_value=7) as osopen, \
             mock.patch.object(setup.io, "FileIO") as fileio, \
             mock.patch.object(setup.io, "TextIOWrapper",
                               return_value=sentinel) as wrapper:
            self.assertIs(setup.open_tty(), sentinel)
            osopen.assert_called_once_with(
                "/dev/tty", setup.os.O_RDWR | setup.os.O_NOCTTY
            )
            fileio.assert_called_once_with(7, "r+")
            self.assertIs(wrapper.call_args.args[0], fileio.return_value)

    def test_falls_back_to_std_streams_when_both_are_ttys(self):
        with mock.patch.object(setup.os, "open",
                               side_effect=OSError(6, "No such device")), \
             mock.patch.object(setup.sys, "stdin")  as si, \
             mock.patch.object(setup.sys, "stdout") as so:
            si.isatty.return_value = True
            so.isatty.return_value = True
            tty = setup.open_tty()
            self.assertIsNotNone(tty)            # a usable interactive stream
            self.assertTrue(setup.is_interactive(tty))

    def test_none_when_dev_tty_fails_and_stdin_is_pipe(self):
        # curl | bash WITHOUT a controlling terminal: /dev/tty open fails and
        # stdin is the script pipe → not interactive → fail closed.
        with mock.patch.object(setup.os, "open",
                               side_effect=OSError(6, "No such device")), \
             mock.patch.object(setup.sys, "stdin")  as si, \
             mock.patch.object(setup.sys, "stdout") as so:
            si.isatty.return_value = False
            so.isatty.return_value = True
            self.assertIsNone(setup.open_tty())

    def test_none_when_nothing_is_a_tty(self):
        with mock.patch.object(setup.os, "open",
                               side_effect=OSError(6, "No such device")), \
             mock.patch.object(setup.sys, "stdin")  as si, \
             mock.patch.object(setup.sys, "stdout") as so:
            si.isatty.return_value = False
            so.isatty.return_value = False
            self.assertIsNone(setup.open_tty())


class TestStdinOnTty(unittest.TestCase):
    """stdin_on_tty() points fd 0 at /dev/tty when stdin is not a TTY
    (the curl | bash shape), and restores it afterwards."""

    def test_noop_when_stdin_already_tty(self):
        # A direct terminal run (or the PTY tests): fd 0 is already a TTY, so
        # the helper must NOT touch the fds at all.
        with mock.patch.object(setup.os, "isatty", return_value=True) as isatty, \
             mock.patch.object(setup.os, "open") as op, \
             mock.patch.object(setup.os, "dup2") as dup2:
            with setup.stdin_on_tty():
                pass
            isatty.assert_called_once_with(0)
            op.assert_not_called()
            dup2.assert_not_called()

    def test_redirects_and_restores_when_stdin_not_tty(self):
        # curl | bash: fd 0 is the script pipe. The helper opens /dev/tty, dup2s
        # it onto fd 0 for the body, then restores the saved fd 0 on exit.
        order = []
        with mock.patch.object(setup.os, "isatty", return_value=False), \
             mock.patch.object(setup.os, "open", return_value=7) as op, \
             mock.patch.object(setup.os, "dup", return_value=9) as dup, \
             mock.patch.object(setup.os, "dup2",
                               side_effect=lambda a, b: order.append((a, b))), \
             mock.patch.object(setup.os, "close",
                               side_effect=lambda fd: order.append(("close", fd))):
            with setup.stdin_on_tty():
                # inside the body: /dev/tty (fd 7) is now fd 0; saved fd is 9.
                self.assertIn((7, 0), order)        # redirected before yield
                self.assertNotIn((9, 0), order)     # not yet restored
            op.assert_called_once_with("/dev/tty", os.O_RDWR | os.O_NOCTTY)
            dup.assert_called_once_with(0)          # saved the original fd 0
            self.assertEqual(order[-2:], [(9, 0), ("close", 9)])  # restore + close saved

    def test_restores_on_exception(self):
        # The finally must restore fd 0 even when the body raises.
        order = []
        with mock.patch.object(setup.os, "isatty", return_value=False), \
             mock.patch.object(setup.os, "open", return_value=7), \
             mock.patch.object(setup.os, "dup", return_value=9), \
             mock.patch.object(setup.os, "dup2",
                               side_effect=lambda a, b: order.append((a, b))), \
             mock.patch.object(setup.os, "close",
                               side_effect=lambda fd: order.append(("close", fd))):
            with self.assertRaises(ValueError), setup.stdin_on_tty():
                raise ValueError("boom")
            self.assertEqual(order[-2:], [(9, 0), ("close", 9)])  # restored despite raise

    def test_proceeds_when_dev_tty_unavailable(self):
        # No controlling terminal at all (require_tty fails closed upstream):
        # the helper must not crash — it yields without redirecting.
        with mock.patch.object(setup.os, "isatty", return_value=False), \
             mock.patch.object(setup.os, "open",
                               side_effect=OSError(6, "No such device")), \
             mock.patch.object(setup.os, "dup2") as dup2:
            with setup.stdin_on_tty():
                pass
            dup2.assert_not_called()


class TestFailClosed(unittest.TestCase):
    def test_install_exits_nonzero_when_no_tty(self):
        with mock.patch.object(setup, "ensure_rich_runtime"), \
             mock.patch.object(setup, "open_tty", return_value=None), \
             mock.patch.object(setup.sys, "stderr", new_callable=io.StringIO) as err:
            with self.assertRaises(SystemExit) as cm:
                setup.main(["install"])
            self.assertEqual(cm.exception.code, 2)
            self.assertIn("terminal", err.getvalue().lower())

    def test_reconfigure_exits_nonzero_when_no_tty(self):
        with mock.patch.object(setup, "ensure_rich_runtime"), \
             mock.patch.object(setup, "open_tty", return_value=None), \
             mock.patch.object(setup.sys, "stderr", new_callable=io.StringIO) as err:
            with self.assertRaises(SystemExit) as cm:
                setup.main(["reconfigure"])
            self.assertEqual(cm.exception.code, 2)
            self.assertIn("terminal", err.getvalue().lower())


class TestUvBootstrap(unittest.TestCase):
    def test_returns_quietly_when_textual_importable(self):
        with mock.patch.object(setup, "_textual_importable", return_value=True), \
             mock.patch.object(setup, "_reexec_under_uv") as rx:
            setup.ensure_rich_runtime({"AI_KIT_UV_REEXEC": "1"})
            rx.assert_not_called()

    def test_reexecs_once_when_uv_present_and_textual_missing(self):
        with mock.patch.object(setup, "_textual_importable", return_value=False), \
             mock.patch.object(setup, "_have_uv", return_value="/usr/bin/uv"), \
             mock.patch.object(setup, "_reexec_under_uv", side_effect=SystemExit(0)) as rx:
            with self.assertRaises(SystemExit):
                setup.ensure_rich_runtime({})        # marker absent → may re-exec
            rx.assert_called_once_with("/usr/bin/uv")

    def test_no_reexec_loop_when_marker_already_set(self):
        # Under uv (marker set) but textual STILL missing → fail closed, never loop.
        with mock.patch.object(setup, "_textual_importable", return_value=False), \
             mock.patch.object(setup.sys, "stderr", new_callable=io.StringIO) as err:
            with self.assertRaises(SystemExit) as cm:
                setup.ensure_rich_runtime({"AI_KIT_UV_REEXEC": "1"})
            self.assertEqual(cm.exception.code, 3)
            self.assertIn("textual", err.getvalue().lower())

    def test_exits_when_uv_missing_and_consent_declined(self):
        with mock.patch.object(setup, "_textual_importable", return_value=False), \
             mock.patch.object(setup, "_have_uv", return_value=None), \
             mock.patch.object(setup, "open_tty", return_value=io.StringIO("n\n")), \
             mock.patch.object(setup.sys, "stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as cm:
                setup.ensure_rich_runtime({})
            self.assertEqual(cm.exception.code, 3)

    def test_exits_3_when_uv_missing_and_no_tty(self):
        # No tty available → fail closed with uv-specific message, not generic require_tty.
        with mock.patch.object(setup, "_textual_importable", return_value=False), \
             mock.patch.object(setup, "_have_uv", return_value=None), \
             mock.patch.object(setup, "open_tty", return_value=None), \
             mock.patch.object(setup.sys, "stderr", new_callable=io.StringIO) as err:
            with self.assertRaises(SystemExit) as cm:
                setup.ensure_rich_runtime({})
            self.assertEqual(cm.exception.code, 3)
            self.assertIn("uv", err.getvalue().lower())
            self.assertIn("terminal", err.getvalue().lower())

    def test_reexecs_once_after_successful_install(self):
        # uv absent → _install_uv returns True → re-resolve finds uv → reexec called once.
        uv_after_install = "/home/user/.local/bin/uv"
        have_uv_calls = iter([None, uv_after_install])
        with mock.patch.object(setup, "_textual_importable", return_value=False), \
             mock.patch.object(setup, "_have_uv", side_effect=have_uv_calls), \
             mock.patch.object(setup, "open_tty", return_value=io.StringIO("y\n")), \
             mock.patch.object(setup, "_install_uv", return_value=True), \
             mock.patch.object(setup, "_reexec_under_uv", side_effect=SystemExit(0)) as rx:
            with self.assertRaises(SystemExit):
                setup.ensure_rich_runtime({})
            rx.assert_called_once_with(uv_after_install)


class TestLayoutModel(unittest.TestCase):
    """T3.1: layout-model adapters — off_tray and layout_move."""

    def _state(self):
        # Three layout lines; "cost" is OFF and not in any line (off-tray).
        return {
            "segments": {"path": True, "model": True, "cost": False},
            "layout": [
                {"min_rows": 0,  "segments": ["path"]},
                {"min_rows": 20, "segments": ["model"]},
            ],
            "dirty": False,
        }

    # ---- off_tray --------------------------------------------------------

    def test_off_tray_returns_toggled_off_segments(self):
        st = self._state()
        tray = setup.off_tray(st)
        self.assertIn("cost", tray)
        self.assertNotIn("path", tray)
        self.assertNotIn("model", tray)

    def test_off_tray_stable_order(self):
        # off_tray returns a list (stable order; repeated calls agree)
        st = self._state()
        self.assertEqual(setup.off_tray(st), setup.off_tray(st))

    def test_off_tray_empty_when_all_on(self):
        st = self._state()
        st["segments"]["cost"] = True
        self.assertEqual(setup.off_tray(st), [])

    # ---- brief's three pinned tests ---------------------------------------

    def test_left_right_reorders_within_line(self):
        st = self._state()
        st["layout"][0]["segments"] = ["path", "model"]
        st2, err = setup.layout_move(st, "model", "left")
        self.assertIsNone(err)
        self.assertEqual(st2["layout"][0]["segments"], ["model", "path"])

    def test_up_from_top_line_sends_to_off_tray(self):
        st2, err = setup.layout_move(self._state(), "path", "up")
        self.assertIsNone(err)
        self.assertIn("path", setup.off_tray(st2))
        self.assertFalse(st2["segments"]["path"])

    def test_min_width_gate_preserved_on_move(self):
        # "model" is on line 2 (index 1); moving up lands on line 1 (index 0).
        st2, _ = setup.layout_move(self._state(), "model", "up")
        self.assertEqual([ln["min_rows"] for ln in st2["layout"]], [0, 20])

    # ---- additional coverage ----------------------------------------------

    def test_up_from_middle_line_lands_on_previous_not_tray(self):
        # "model" is on line index 1; moving up → line index 0, still on.
        st2, err = setup.layout_move(self._state(), "model", "up")
        self.assertIsNone(err)
        self.assertIn("model", st2["layout"][0]["segments"])
        self.assertNotIn("model", st2["layout"][1]["segments"])
        self.assertNotIn("model", setup.off_tray(st2))
        self.assertTrue(st2["segments"]["model"])
        self.assertTrue(st2["dirty"])

    def test_down_from_off_tray_reactivates_onto_line_1(self):
        # "cost" is OFF (off-tray). Moving it down should re-activate it on line 0.
        st2, err = setup.layout_move(self._state(), "cost", "down")
        self.assertIsNone(err)
        self.assertIn("cost", st2["layout"][0]["segments"])
        self.assertTrue(st2["segments"]["cost"])
        self.assertNotIn("cost", setup.off_tray(st2))
        self.assertTrue(st2["dirty"])

    def test_down_from_non_last_line_moves_to_next_line(self):
        # "path" is on line 0; moving down → line 1.
        st2, err = setup.layout_move(self._state(), "path", "down")
        self.assertIsNone(err)
        self.assertIn("path", st2["layout"][1]["segments"])
        self.assertNotIn("path", st2["layout"][0]["segments"])
        self.assertTrue(st2["dirty"])

    def test_down_from_last_line_is_noop_or_error(self):
        # "model" is on line 1 (the last line). down must return an error.
        import copy
        base = self._state()
        original = copy.deepcopy(base)
        st, err = setup.layout_move(base, "model", "down")
        self.assertIsNotNone(err)
        self.assertEqual(st, original)

    def test_right_at_end_of_line_is_noop_or_error(self):
        # "path" is the only segment on line 0; moving right must return an error.
        import copy
        base = self._state()
        original = copy.deepcopy(base)
        st, err = setup.layout_move(base, "path", "right")
        self.assertIsNotNone(err)
        self.assertEqual(st, original)

    def test_left_at_start_of_line_is_noop_or_error(self):
        # "path" is at position 0 on line 0; moving left must return an error.
        import copy
        base = self._state()
        original = copy.deepcopy(base)
        st, err = setup.layout_move(base, "path", "left")
        self.assertIsNotNone(err)
        self.assertEqual(st, original)

    def test_layout_move_down_from_tray_does_not_mutate_input(self):
        # Pure-function guard: down-from-tray path must not mutate the input state.
        import copy
        st = self._state()
        original = copy.deepcopy(st)
        setup.layout_move(st, "cost", "down")  # "cost" is OFF (off-tray)
        self.assertEqual(st, original)

    def test_round_trip_up_to_tray_then_down_restores_membership(self):
        # path: up → tray; then down → back on line 0.
        st1, _ = setup.layout_move(self._state(), "path", "up")
        self.assertIn("path", setup.off_tray(st1))
        st2, err = setup.layout_move(st1, "path", "down")
        self.assertIsNone(err)
        self.assertIn("path", st2["layout"][0]["segments"])
        self.assertTrue(st2["segments"]["path"])
        self.assertNotIn("path", setup.off_tray(st2))

    def test_layout_move_does_not_mutate_input(self):
        # Pure function: original state must be unchanged.
        import copy
        st = self._state()
        original = copy.deepcopy(st)
        setup.layout_move(st, "path", "up")
        self.assertEqual(st, original)

    def test_dirty_set_on_success(self):
        st = self._state()
        self.assertFalse(st["dirty"])
        st2, err = setup.layout_move(st, "model", "up")
        self.assertIsNone(err)
        self.assertTrue(st2["dirty"])

    def test_invalid_direction_returns_error(self):
        _, err = setup.layout_move(self._state(), "path", "sideways")
        self.assertIsNotNone(err)

    # ---- layout_toggle -------------------------------------------------------

    def test_toggle_on_to_off_seg_leaves_line(self):
        # "path" is ON (line 0). Toggle → moves to tray.
        st2, err = setup.layout_toggle(self._state(), "path")
        self.assertIsNone(err)
        self.assertNotIn("path", st2["layout"][0]["segments"])
        self.assertFalse(st2["segments"]["path"])
        self.assertIn("path", setup.off_tray(st2))
        self.assertTrue(st2["dirty"])

    def test_toggle_off_to_on_seg_appears_on_line_0(self):
        # "cost" is OFF (tray). Toggle → re-activates on line 0.
        st2, err = setup.layout_toggle(self._state(), "cost")
        self.assertIsNone(err)
        self.assertIn("cost", st2["layout"][0]["segments"])
        self.assertTrue(st2["segments"]["cost"])
        self.assertNotIn("cost", setup.off_tray(st2))
        self.assertTrue(st2["dirty"])

    def test_toggle_round_trip_restores_state(self):
        # Toggle "path" OFF then ON; membership should be restored (on line 0).
        base = self._state()
        st1, _ = setup.layout_toggle(base, "path")
        self.assertIn("path", setup.off_tray(st1))
        st2, err = setup.layout_toggle(st1, "path")
        self.assertIsNone(err)
        self.assertIn("path", st2["layout"][0]["segments"])
        self.assertTrue(st2["segments"]["path"])
        self.assertNotIn("path", setup.off_tray(st2))

    def test_toggle_preserves_min_rows(self):
        # min_rows must survive a toggle cycle.
        base = self._state()
        st1, _ = setup.layout_toggle(base, "model")   # ON→OFF
        self.assertEqual([ln["min_rows"] for ln in st1["layout"]], [0, 20])
        st2, _ = setup.layout_toggle(st1, "model")    # OFF→ON
        self.assertEqual([ln["min_rows"] for ln in st2["layout"]], [0, 20])

    def test_toggle_unknown_seg_returns_error(self):
        _, err = setup.layout_toggle(self._state(), "nonexistent")
        self.assertIsNotNone(err)
        self.assertIn("nonexistent", err)

    def test_toggle_does_not_mutate_input(self):
        # Pure function: original state must be unchanged after toggle.
        import copy
        st = self._state()
        original = copy.deepcopy(st)
        setup.layout_toggle(st, "path")
        self.assertEqual(st, original)

    def test_toggle_on_from_non_first_line(self):
        # "model" is ON on line 1 (not line 0). Toggle → tray regardless of line.
        st2, err = setup.layout_toggle(self._state(), "model")
        self.assertIsNone(err)
        self.assertNotIn("model", st2["layout"][1]["segments"])
        self.assertFalse(st2["segments"]["model"])
        self.assertIn("model", setup.off_tray(st2))


class TestPersistRoundTrip(unittest.TestCase):
    """T3.4: _persist_layout writes the minimal diff through save_statusline_config
    (doctor-validated path), and the written result round-trips correctly."""

    _REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _statusline_doctor(self):
        return os.path.join(self._REPO, "tools", "statusline-doctor.py")

    def _sample_recipe(self):
        return os.path.join(self._REPO, "tools", "statusline.toml.sample")

    def _paths(self, cfg_path):
        """Minimal Paths-like namespace pointing at the temp config."""
        import types as _types
        return _types.SimpleNamespace(
            config_toml=cfg_path,
            statusline_doctor=self._statusline_doctor(),
        )

    def _seed_recipe(self):
        """Copy statusline.toml.sample to a tempfile; return its path."""
        with tempfile.NamedTemporaryFile(
            "w", suffix=".toml", delete=False, dir=tempfile.gettempdir()
        ) as tmp:
            tmp_name = tmp.name
        shutil.copy(self._sample_recipe(), tmp_name)
        self.addCleanup(os.unlink, tmp_name)
        return tmp_name

    # ------------------------------------------------------------------
    # 1. Layout change round-trips and doctor passes
    # ------------------------------------------------------------------

    def test_layout_change_round_trips_and_doctor_passes(self):
        cfg = self._seed_recipe()
        state = {
            "segments": setup.current_segments(cfg),
            "layout": setup.current_layout(cfg),
            "dirty": True,
        }
        # Make a real layout change: reverse line 0's segment list.
        state["layout"][0]["segments"].reverse()
        expected_line0 = list(state["layout"][0]["segments"])

        ok = setup._persist_layout(self._paths(cfg), state, dry=False)
        self.assertTrue(ok)

        # Re-read and assert round-trip.
        actual_layout = setup.current_layout(cfg)
        self.assertEqual(actual_layout[0]["segments"], expected_line0)

    def test_doctor_passes_after_persist(self):
        """The doctor must exit 0 on the written config."""
        import subprocess
        cfg = self._seed_recipe()
        state = {
            "segments": setup.current_segments(cfg),
            "layout": setup.current_layout(cfg),
            "dirty": True,
        }
        state["layout"][0]["segments"].reverse()

        ok = setup._persist_layout(self._paths(cfg), state, dry=False)
        self.assertTrue(ok)

        env = dict(os.environ, CC_AI_KIT_CONFIG_FILE=cfg)
        proc = subprocess.run(
            [sys.executable, "-S", self._statusline_doctor(), "--check"],
            env=env, capture_output=True,
        )
        self.assertEqual(proc.returncode, 0,
                         f"doctor failed:\n{proc.stdout.decode()}\n{proc.stderr.decode()}")

    # ------------------------------------------------------------------
    # 2. Dry-run writes nothing
    # ------------------------------------------------------------------

    def test_dry_run_writes_nothing(self):
        cfg = self._seed_recipe()
        with open(cfg, "rb") as f:
            before = f.read()

        state = {
            "segments": setup.current_segments(cfg),
            "layout": setup.current_layout(cfg),
            "dirty": True,
        }
        state["layout"][0]["segments"].reverse()

        ok = setup._persist_layout(self._paths(cfg), state, dry=True)
        self.assertTrue(ok)

        with open(cfg, "rb") as f:
            after = f.read()
        self.assertEqual(before, after, "dry-run must not modify the file")

    # ------------------------------------------------------------------
    # 3. No-op returns True without writing
    # ------------------------------------------------------------------

    def test_noop_returns_true(self):
        cfg = self._seed_recipe()
        state = {
            "segments": setup.current_segments(cfg),
            "layout": setup.current_layout(cfg),
            "dirty": False,
        }
        # Nothing changed — _persist_layout should return True immediately.
        ok = setup._persist_layout(self._paths(cfg), state, dry=False)
        self.assertTrue(ok)

    # ------------------------------------------------------------------
    # 4. Segment toggle round-trips
    # ------------------------------------------------------------------

    def test_segment_toggle_round_trips(self):
        cfg = self._seed_recipe()
        segs = setup.current_segments(cfg)
        # Find a segment that is currently False and flip it.
        target = next(k for k, v in segs.items() if not v)
        segs[target] = True
        state = {
            "segments": segs,
            "layout": setup.current_layout(cfg),
            "dirty": True,
        }

        ok = setup._persist_layout(self._paths(cfg), state, dry=False)
        self.assertTrue(ok)

        reread = setup.current_segments(cfg)
        self.assertTrue(reread[target], f"{target} should now be True on disk")

    # ------------------------------------------------------------------
    # 5. Drift guard: patch_layout round-trip preserves membership + min_rows
    # ------------------------------------------------------------------

    def test_patch_layout_round_trip_preserves_membership_and_min_rows(self):
        """Extend the drift guard: a layout retrieved from the sample, mutated,
        written via patch_layout, then re-read via current_layout must preserve
        all original segments (just reordered) and min_rows values."""
        original_layout = setup.current_layout(self._sample_recipe())
        # Reverse line 0's segments (a structural mutation, not a content loss).
        mutated = [dict(row, segments=list(row["segments"])) for row in original_layout]
        mutated[0]["segments"].reverse()

        cfg = self._seed_recipe()
        with open(cfg, encoding="utf-8") as f:
            text = f.read()
        patched = setup.patch_layout(text, mutated)
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(patched)

        reread = setup.current_layout(cfg)
        for i, (orig, rr) in enumerate(zip(original_layout, reread, strict=True)):
            self.assertEqual(orig["min_rows"], rr["min_rows"],
                             f"line {i} min_rows changed")
            self.assertEqual(set(orig["segments"]), set(rr["segments"]),
                             f"line {i} segment membership changed")


class TestLaunchWizardCrash(unittest.TestCase):
    """Task 4.1 — launch_wizard converts WizardCrash to non-zero exit; clean
    abort still returns normally (exit 0 / no SystemExit).

    launch_wizard does a lazy ``import wizard_app`` inside the function body,
    so we inject a fake module into sys.modules to control its behaviour
    without importing Textual (which requires uv).
    """

    def _make_fake_wizard_module(self):
        """Return a mock module that looks enough like wizard_app to satisfy
        launch_wizard: WizardCrash, WizardContext, and run_wizard."""
        mod = mock.MagicMock()

        class WizardCrash(Exception):
            pass

        mod.WizardCrash = WizardCrash
        mod.WizardContext = mock.MagicMock  # not called in these paths
        return mod

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "tools"))
        # Stub a sample-input file so _sample_input_path() resolves.
        os.makedirs(os.path.join(self.install, "tools"), exist_ok=True)
        sample = os.path.join(self.install, "tools", "sample-input.json")
        with open(sample, "w") as f:
            f.write("{}")
        self.env = {"HOME": self.tmp, "AI_KIT_DIR": self.install,
                    "CLAUDE_CONFIG_DIR": self.claude,
                    "XDG_CONFIG_HOME": os.path.join(self.tmp, ".config")}
        self._orig_sample_path = setup._sample_input_path  # type: ignore[attr-defined]
        setup._sample_input_path = lambda: sample           # type: ignore[assignment]

    def tearDown(self):
        setup._sample_input_path = self._orig_sample_path  # type: ignore[assignment]
        shutil.rmtree(self.tmp, ignore_errors=True)
        # Remove any injected fake wizard_app so later tests start clean.
        sys.modules.pop("wizard_app", None)

    def _make_paths(self):
        """Return a minimal paths object that satisfies launch_wizard."""
        paths = setup.resolve_paths(self.env)
        # Ensure config_toml exists so current_segments/current_layout don't crash.
        os.makedirs(os.path.dirname(paths.config_toml), exist_ok=True)
        with open(paths.config_toml, "w") as f:
            f.write("")
        return paths

    def test_wizard_crash_exits_nonzero(self):
        """If run_wizard raises WizardCrash, launch_wizard must sys.exit(2)."""
        fake_mod = self._make_fake_wizard_module()

        def _crashing_run_wizard(_ctx):
            raise fake_mod.WizardCrash(RuntimeError("boom"))

        fake_mod.run_wizard = _crashing_run_wizard
        sys.modules["wizard_app"] = fake_mod  # type: ignore[assignment]

        paths = self._make_paths()
        entries = {cat: [] for cat in setup.CATEGORIES}
        installed = {cat: set() for cat in setup.CATEGORIES}
        fake_tty = mock.MagicMock()
        fake_tty.isatty.return_value = True

        with mock.patch.object(setup.sys, "stderr", new_callable=io.StringIO) as err, \
             self.assertRaises(SystemExit) as cm:
            setup.launch_wizard(paths, entries, installed, fake_tty, False,
                                setup.new_counts())

        self.assertEqual(cm.exception.code, 2)
        self.assertIn("error", err.getvalue().lower())

    def test_clean_abort_does_not_exit(self):
        """If run_wizard returns None (user aborted), launch_wizard must return
        normally — no SystemExit, no error message."""
        fake_mod = self._make_fake_wizard_module()
        fake_mod.run_wizard = lambda _ctx: None          # clean abort
        sys.modules["wizard_app"] = fake_mod             # type: ignore[assignment]

        paths = self._make_paths()
        entries = {cat: [] for cat in setup.CATEGORIES}
        installed = {cat: set() for cat in setup.CATEGORIES}
        fake_tty = mock.MagicMock()
        fake_tty.isatty.return_value = True

        # Should return without raising and print nothing to stderr.
        with mock.patch.object(setup.sys, "stderr", new_callable=io.StringIO) as err:
            setup.launch_wizard(paths, entries, installed, fake_tty, False,
                                setup.new_counts())
        self.assertEqual(err.getvalue(), "")


class TestUserSegmentDiscovery(unittest.TestCase):
    def _seg(self, d, fname, header):
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, fname)
        with open(p, "w", encoding="utf-8") as f:
            f.write(header)
        os.chmod(p, 0o755)
        return p

    def test_segments_dir_resolves_under_config(self):
        paths = setup.resolve_paths({"HOME": "/home/x"})
        self.assertEqual(paths.segments_dir,
                         os.path.join("/home/x", ".config", "ai-kit", "segments"))

    def test_segments_dir_respects_xdg(self):
        paths = setup.resolve_paths({"HOME": "/home/x", "XDG_CONFIG_HOME": "/cfg"})
        self.assertEqual(paths.segments_dir, "/cfg/ai-kit/segments")

    def test_merges_bundled_and_user_tagged_by_provenance(self):
        home = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        examples = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, examples, ignore_errors=True)
        self._seg(examples, "b", "# ai-kit-segment: id=bundled_one line=1\n")
        userdir = os.path.join(home, ".config", "ai-kit", "segments")
        self._seg(userdir, "u", "# ai-kit-segment: id=user_one line=2\n")
        paths = setup.resolve_paths({"HOME": home})
        found = setup.discover_external_segments(paths, examples)
        by_id = {e["id"]: e for e in found}
        self.assertEqual(by_id["bundled_one"]["provenance"], "bundled")
        self.assertEqual(by_id["user_one"]["provenance"], "user")

    def test_user_wins_on_id_collision(self):
        home = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        examples = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, examples, ignore_errors=True)
        self._seg(examples, "dup", "# ai-kit-segment: id=dup name=Bundled line=1\n")
        userdir = os.path.join(home, ".config", "ai-kit", "segments")
        self._seg(userdir, "dup", "# ai-kit-segment: id=dup name=User line=2\n")
        paths = setup.resolve_paths({"HOME": home})
        found = setup.discover_external_segments(paths, examples)
        dup = [e for e in found if e["id"] == "dup"]
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0]["provenance"], "user")
        self.assertEqual(dup[0]["name"], "User")

    def test_missing_user_dir_no_crash(self):
        home = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        examples = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, examples, ignore_errors=True)
        self._seg(examples, "b", "# ai-kit-segment: id=only_bundled line=1\n")
        # user segments dir does NOT exist
        paths = setup.resolve_paths({"HOME": home})
        found = setup.discover_external_segments(paths, examples)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["provenance"], "bundled")


class TestSystemMemoryCanonicalHeader(unittest.TestCase):
    def test_shipped_example_is_self_describing(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        found = setup.discover_example_segments(
            os.path.join(repo, "examples", "segments"))
        e = next(x for x in found if x["id"] == "system_memory")
        self.assertTrue(e["name"])
        self.assertTrue(e["description"])
        self.assertEqual(e["icon"], "💻")
        self.assertTrue(e["sample"])


class TestStatusLineDetection(unittest.TestCase):
    def _paths(self, settings_payload):
        home = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        paths = setup.resolve_paths({"HOME": home})
        os.makedirs(os.path.dirname(paths.settings), exist_ok=True)
        if settings_payload is not None:
            with open(paths.settings, "w", encoding="utf-8") as f:
                json.dump(settings_payload, f)
        return paths

    def test_unset_when_absent(self):
        paths = self._paths({})
        d = setup.detect_statusline(paths)
        self.assertEqual(d["state"], "unset")
        self.assertIsNone(d["current_command"])

    def test_ours_when_command_invokes_resolved_status_line(self):
        paths = self._paths(None)
        cmd = "python3 -S " + paths.status_line
        with open(paths.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": {"type": "command", "command": cmd}}, f)
        d = setup.detect_statusline(paths)
        self.assertEqual(d["state"], "ours")
        self.assertEqual(d["current_command"], cmd)

    def test_foreign_when_other_command(self):
        paths = self._paths({"statusLine": {"type": "command", "command": "/usr/bin/mybar"}})
        d = setup.detect_statusline(paths)
        self.assertEqual(d["state"], "foreign")
        self.assertEqual(d["current_command"], "/usr/bin/mybar")

    def test_string_form_statusline_ours(self):
        paths = self._paths(None)
        cmd = "python3 -S " + paths.status_line
        with open(paths.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": cmd}, f)
        d = setup.detect_statusline(paths)
        self.assertEqual(d["state"], "ours")
        self.assertEqual(d["current_command"], cmd)

    def test_string_form_statusline_foreign(self):
        paths = self._paths({"statusLine": "/usr/bin/mybar"})
        d = setup.detect_statusline(paths)
        self.assertEqual(d["state"], "foreign")
        self.assertEqual(d["current_command"], "/usr/bin/mybar")

    def test_missing_settings_file_returns_unset(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        paths = setup.resolve_paths({"HOME": home})
        # Do NOT create the settings file
        d = setup.detect_statusline(paths)
        self.assertEqual(d["state"], "unset")
        self.assertIsNone(d["current_command"])

    def test_malformed_settings_file_returns_unset(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        paths = setup.resolve_paths({"HOME": home})
        os.makedirs(os.path.dirname(paths.settings), exist_ok=True)
        with open(paths.settings, "w", encoding="utf-8") as f:
            f.write("{ not valid json }")
        d = setup.detect_statusline(paths)
        self.assertEqual(d["state"], "unset")
        self.assertIsNone(d["current_command"])


class TestSegmentInventoryLoader(unittest.TestCase):
    def test_loads_shipped_inventory_shape(self):
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
        self.assertIn("path", inv)
        entry = inv["alt_process_memory"]
        self.assertEqual(entry["icon"], "🧮")
        self.assertEqual(entry["line"], 2)
        self.assertEqual(set(entry), {"description", "sample", "icon", "line"})

    def test_missing_file_yields_empty(self):
        self.assertEqual(setup.load_segment_inventory("/no/such/inv.toml"), {})


class TestConditionalPersistence(unittest.TestCase):
    def _paths(self):
        home = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        paths = setup.resolve_paths({"HOME": home})
        os.makedirs(paths.config_dir, exist_ok=True)
        os.makedirs(os.path.dirname(paths.settings), exist_ok=True)
        # seed a real status-line.py + doctor + recipe so writes can doctor-validate
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return paths, repo

    def _state(self):
        return {"segments": dict(setup.SEGMENT_DEFAULTS),
                "layout": [dict(l) for l in setup.LAYOUT_DEFAULTS], "dirty": False}

    def test_skip_writes_nothing(self):
        paths, _ = self._paths()
        ok = setup.persist_statusline(paths, self._state(), adopt=False, dry=False)
        self.assertTrue(ok)
        self.assertFalse(os.path.exists(paths.config_toml))
        self.assertFalse(os.path.exists(paths.settings))

    def test_adopt_sets_settings_statusline(self):
        paths, repo = self._paths()
        # point resolved status_line/doctor at the real repo tools so the doctor runs
        paths = paths._replace(
            status_line=os.path.join(repo, "tools", "status-line.py"),
            statusline_doctor=os.path.join(repo, "tools", "statusline-doctor.py"),
            sample=os.path.join(repo, "tools", "statusline.toml.sample"))
        # seed the recipe so save_statusline_config has a base file
        import shutil as _sh
        _sh.copy(paths.sample, paths.config_toml)
        ok = setup.persist_statusline(paths, self._state(), adopt=True, dry=False)
        self.assertTrue(ok)
        with open(paths.settings, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertIn(paths.status_line, data["statusLine"]["command"])
        self.assertTrue(data["statusLine"]["command"].startswith("python3 -S "))

    def test_reconfigure_leaves_existing_ours_statusline(self):
        paths, repo = self._paths()
        paths = paths._replace(
            status_line=os.path.join(repo, "tools", "status-line.py"),
            statusline_doctor=os.path.join(repo, "tools", "statusline-doctor.py"),
            sample=os.path.join(repo, "tools", "statusline.toml.sample"))
        import shutil as _sh
        _sh.copy(paths.sample, paths.config_toml)
        ours_cmd = "python3 -S " + paths.status_line   # already ours, possibly hand-edited
        with open(paths.settings, "w", encoding="utf-8") as f:
            json.dump({"statusLine": {"type": "command", "command": ours_cmd},
                       "other": 1}, f)
        ok = setup.persist_statusline(paths, self._state(), adopt=True, dry=False)
        self.assertTrue(ok)
        with open(paths.settings, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["statusLine"]["command"], ours_cmd)  # untouched
        self.assertEqual(data["other"], 1)


class TestBuildSegmentMeta(unittest.TestCase):
    def test_inventory_defaults_with_toml_overrides(self):
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
        # no overrides -> inventory defaults pass through
        meta = setup.build_segment_meta(inv, {})
        self.assertEqual(meta["alt_process_memory"]["icon"], "🧮")
        self.assertEqual(meta["context"]["line"], 2)
        # toml override wins for icon + line
        meta = setup.build_segment_meta(inv, {"context": {"icon": "X", "line": 0}})
        self.assertEqual(meta["context"]["icon"], "X")
        self.assertEqual(meta["context"]["line"], 0)
        # description/sample never come from overrides
        self.assertEqual(meta["context"]["description"], inv["context"]["description"])

    def test_icon_line_overrides_read_from_statusline_toml(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        paths = setup.resolve_paths({"HOME": home})
        os.makedirs(paths.config_dir, exist_ok=True)
        with open(paths.config_toml, "w", encoding="utf-8") as f:
            f.write('[segments.context]\nicon = "Z"\nline = 1\n'
                    '[segments.path]\nenabled = true\n')   # no icon/line -> ignored
        ov = setup._statusline_icon_line_overrides(paths.config_toml)
        self.assertEqual(ov["context"], {"icon": "Z", "line": 1})
        self.assertNotIn("path", ov)

    def test_overrides_missing_file_is_empty(self):
        self.assertEqual(setup._statusline_icon_line_overrides("/no/such.toml"), {})


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestWizardContextPopulation(unittest.TestCase):
    """Task 10: launch_wizard builds a context whose new fields have the right
    shapes, and a freshly-discovered external NOT in statusline.toml is OFF
    (externals default OFF — never pre-checked via default_on)."""

    def _env(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = {"HOME": home, "AI_KIT_DIR": repo}
        return env, setup.resolve_paths(env)

    def test_context_shape_and_external_off_by_default(self):
        _env, paths = self._env()
        os.makedirs(paths.segments_dir, exist_ok=True)
        # a fresh user external segment NOT mentioned in statusline.toml
        with open(os.path.join(paths.segments_dir, "freshseg"), "w",
                  encoding="utf-8") as f:
            f.write("#!/bin/sh\n# ai-kit-segment: id=freshseg name=Fresh\necho hi\n")
        # capture the context that launch_wizard would build by stubbing run_wizard
        captured = {}

        wa = _import_wizard_app()

        def _fake_run(ctx):
            captured["ctx"] = ctx
            return None   # abort -> launch_wizard returns without persisting

        entries = setup.enumerate_entries(paths.install_dir)
        installed = {cat: set() for cat in setup.CATEGORIES}

        class _FakeTty:
            def isatty(self):
                return True

        import contextlib
        with mock.patch.object(wa, "run_wizard", _fake_run), \
             mock.patch.object(setup, "stdin_on_tty",
                               return_value=contextlib.nullcontext()):
            setup.launch_wizard(paths, entries, installed, _FakeTty(), True,
                                setup.new_counts())

        ctx = captured["ctx"]
        # status_line shape
        self.assertIn("state", ctx.status_line)
        self.assertIn("current_command", ctx.status_line)
        self.assertEqual(ctx.status_line["state"], "unset")
        # adopt derived from detection (unset -> False)
        self.assertFalse(ctx.state["adopt"])
        # segment_meta carries built-in inventory keys
        self.assertIn("context", ctx.segment_meta)
        self.assertEqual(set(ctx.segment_meta["context"]),
                         {"description", "sample", "icon", "line"})
        # external discovered with provenance
        ids = {e["id"]: e for e in ctx.external_segments}
        self.assertIn("freshseg", ids)
        self.assertEqual(ids["freshseg"]["provenance"], "user")
        # the fresh external is OFF in the wizard's segment state (not pre-checked)
        self.assertIn("freshseg", ctx.state["segments"])
        self.assertFalse(ctx.state["segments"]["freshseg"])


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestCmdInstallSkipNoStatusline(unittest.TestCase):
    """Task 10 constraint 1: the REAL install flow routes status-line persistence
    through persist_statusline gated on the wizard's adopt decision. A wizard run
    that does NOT adopt must write no statusline.toml and leave settings.json's
    statusLine untouched — proving the production wiring, not just a unit."""

    def test_no_adopt_writes_no_statusline_and_no_settings(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = {"HOME": home, "AI_KIT_DIR": repo}
        paths = setup.resolve_paths(env)

        wa = _import_wizard_app()
        import contextlib

        def _fake_run(ctx):
            # confirm install but DO NOT adopt the status line
            st = dict(ctx.state)
            st["adopt"] = False
            return wa.WizardResult(selection=ctx.selection, state=st)

        class _FakeTty:
            def isatty(self):
                return True

        with mock.patch.object(wa, "run_wizard", _fake_run), \
             mock.patch.object(setup, "stdin_on_tty",
                               return_value=contextlib.nullcontext()), \
             mock.patch.object(setup, "apply_selection"):
            entries = setup.enumerate_entries(paths.install_dir)
            installed = {cat: set() for cat in setup.CATEGORIES}
            setup.launch_wizard(paths, entries, installed, _FakeTty(), False,
                                setup.new_counts())

        self.assertFalse(os.path.exists(paths.config_toml),
                         "components-only run must not write statusline.toml")
        # settings.json statusLine must be untouched (file may not even exist)
        if os.path.exists(paths.settings):
            with open(paths.settings, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertNotIn("statusLine", data)


class TestCmdInstallExternalReconcile(unittest.TestCase):
    """I-1: wizard result drives external-segment install; no double-prompt."""

    def _fake_result(self, seg_state):
        """Build a minimal WizardResult-shaped object (NamedTuple) with the
        given segments state dict."""
        import types
        return types.SimpleNamespace(
            selection=None,
            state={"segments": seg_state, "layout": [], "dirty": False, "adopt": False}
        )

    @mock.patch.object(setup, "install_example_segments", return_value=["system_memory"])
    @mock.patch.object(setup, "select_examples")
    @mock.patch.object(setup, "discover_example_segments")
    def test_interactive_install_uses_wizard_state_not_select_examples(
        self, mock_discover, mock_select, mock_install
    ):
        """When wizard returned a result, install_example_segments is called
        with exactly the wizard-enabled segments; select_examples is NOT called."""
        mock_discover.return_value = [
            {"id": "system_memory", "name": "System memory",
             "path": "/fake/system_memory", "filename": "system_memory",
             "default_on": True, "description": "", "icon": "\U0001f4bb",
             "sample": "", "line": 0, "provenance": "bundled"},
        ]
        # Simulate wizard: user ENABLED system_memory.
        fake_result = self._fake_result({"system_memory": True})

        # Invoke just the post-wizard example block logic. We call it via
        # cmd_install with launch_wizard mocked to return our fake result.
        with mock.patch.object(setup, "launch_wizard", return_value=fake_result), \
             mock.patch.object(setup, "resolve_paths", return_value=mock.MagicMock(
                 install_dir="/fake", config_dir="/fake/cfg",
                 claude_dir="/fake/.claude")), \
             mock.patch.object(setup, "enumerate_entries", return_value={
                 "agents": [], "commands": [], "skills": []}), \
             mock.patch.object(setup, "new_counts",
                               return_value=setup.new_counts()), \
             mock.patch.object(setup, "prune_stale"), \
             mock.patch.object(setup, "adopt_predecessor_links"), \
             mock.patch.object(setup, "installed_links", return_value={}), \
             mock.patch("builtins.print"):
            setup.cmd_install(os.environ.copy(), tty=mock.MagicMock(isatty=lambda: True),
                              dry=False, examples_flag=None)

        # select_examples must NOT have been called (no double-prompt).
        mock_select.assert_not_called()
        # install_example_segments IS called with the wizard-enabled segment.
        mock_install.assert_called_once()
        chosen_arg = mock_install.call_args[0][0]
        self.assertEqual([e["id"] for e in chosen_arg], ["system_memory"])

    @mock.patch.object(setup, "install_example_segments", return_value=[])
    @mock.patch.object(setup, "select_examples", return_value=[])
    @mock.patch.object(setup, "discover_example_segments")
    def test_abort_installs_no_examples(
        self, mock_discover, mock_select, mock_install
    ):
        """When the wizard is aborted (result=None), nothing further is
        installed: neither select_examples nor install_example_segments runs
        (abort is a full no-op for example segments too)."""
        mock_discover.return_value = [
            {"id": "system_memory", "name": "System memory",
             "path": "/fake/system_memory", "filename": "system_memory",
             "default_on": True, "description": "", "icon": "\U0001f4bb",
             "sample": "", "line": 0, "provenance": "bundled"},
        ]
        with mock.patch.object(setup, "launch_wizard", return_value=None), \
             mock.patch.object(setup, "resolve_paths", return_value=mock.MagicMock(
                 install_dir="/fake", config_dir="/fake/cfg",
                 claude_dir="/fake/.claude")), \
             mock.patch.object(setup, "enumerate_entries", return_value={
                 "agents": [], "commands": [], "skills": []}), \
             mock.patch.object(setup, "new_counts",
                               return_value=setup.new_counts()), \
             mock.patch.object(setup, "prune_stale"), \
             mock.patch.object(setup, "adopt_predecessor_links"), \
             mock.patch.object(setup, "installed_links", return_value={}), \
             mock.patch("builtins.print"):
            setup.cmd_install(os.environ.copy(), tty=mock.MagicMock(isatty=lambda: True),
                              dry=False, examples_flag="none")

        # Abort = no-op: neither path runs.
        mock_select.assert_not_called()
        mock_install.assert_not_called()

    @mock.patch.object(setup, "install_example_segments", return_value=["system_memory"])
    @mock.patch.object(setup, "select_examples", return_value=[])
    @mock.patch.object(setup, "discover_example_segments")
    def test_examples_flag_overrides_wizard_selection_on_confirm(
        self, mock_discover, mock_select, mock_install
    ):
        """On a confirmed install, an explicit --examples flag overrides the
        wizard's toggles via select_examples (no prompt — the flag is set)."""
        mock_discover.return_value = [
            {"id": "system_memory", "name": "System memory",
             "path": "/fake/system_memory", "filename": "system_memory",
             "default_on": True, "description": "", "icon": "\U0001f4bb",
             "sample": "", "line": 0, "provenance": "bundled"},
        ]
        # Wizard confirmed with system_memory toggled OFF; --examples=all must
        # override and select_examples governs the result.
        fake_result = self._fake_result({"system_memory": False})
        with mock.patch.object(setup, "launch_wizard", return_value=fake_result), \
             mock.patch.object(setup, "resolve_paths", return_value=mock.MagicMock(
                 install_dir="/fake", config_dir="/fake/cfg",
                 claude_dir="/fake/.claude")), \
             mock.patch.object(setup, "enumerate_entries", return_value={
                 "agents": [], "commands": [], "skills": []}), \
             mock.patch.object(setup, "new_counts",
                               return_value=setup.new_counts()), \
             mock.patch.object(setup, "prune_stale"), \
             mock.patch.object(setup, "adopt_predecessor_links"), \
             mock.patch.object(setup, "installed_links", return_value={}), \
             mock.patch("builtins.print"):
            setup.cmd_install(os.environ.copy(), tty=mock.MagicMock(isatty=lambda: True),
                              dry=False, examples_flag="all")

        # Explicit flag → select_examples governs the override path.
        mock_select.assert_called_once()


if __name__ == "__main__":
    unittest.main()
