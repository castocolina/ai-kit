import importlib.util
import json
import os
import stat
import sys
import tempfile
import time
import types
import unittest

_HERE = os.path.dirname(__file__)
_MODULE_PATH = os.path.join(_HERE, "..", "tools", "status-line.py")
_DOCTOR_PATH = os.path.join(_HERE, "..", "tools", "statusline-doctor.py")


def load_module():
    spec = importlib.util.spec_from_file_location("status_line", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod          # register so @dataclass can resolve cls.__module__
    spec.loader.exec_module(mod)
    return mod


def load_doctor():
    spec = importlib.util.spec_from_file_location("statusline_doctor", _DOCTOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sl = load_module()
doctor = load_doctor()   # introspection (--print-config / --check) lives here (Phase 4)


def _ctx_from_env(raw, env, cfg, t_start=None):
    """Resolve the per-render SHELL inputs from `env` and build a Context — the
    test-side mirror of what safe_render does in production (terminal size, HOME,
    claude_dir, effort). Returns (ctx, cols, lines) for call-site convenience."""
    cols, lines, assumed = sl.probe_terminal_size(env)
    home = env.get("HOME", "")
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    ctx = sl.core_build_context(raw, cfg, sl.core_default_theme(), cols, lines, assumed, t_start,
                           effort=sl.cfg_resolve_effort(raw), home=home, claude_dir=claude_dir)
    return ctx, cols, lines


def write_script(directory, name, body, executable=True):
    """Write a provider script and (by default) chmod +x it. Returns its path."""
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    if executable:
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


class TestParseHeader(unittest.TestCase):
    def test_full_header(self):
        lines = ["#!/bin/sh\n",
                 "# ai-kit-segment: line=2 after=clock id=aws timeout=3 ttl=30\n",
                 "echo hi\n"]
        fields = sl.core_parse_segment_header(lines)
        self.assertEqual(fields["position"], ("after", "clock"))
        self.assertEqual(fields["line"], "2")
        self.assertEqual(fields["id"], "aws")
        self.assertEqual(fields["timeout"], "3")
        self.assertEqual(fields["ttl"], "30")

    def test_bare_start_end(self):
        self.assertEqual(sl.core_parse_segment_header(["# ai-kit-segment: start\n"])["position"],
                         ("start", ""))
        self.assertEqual(sl.core_parse_segment_header(["# ai-kit-segment: end\n"])["position"],
                         ("end", ""))

    def test_no_header_returns_none(self):
        self.assertIsNone(sl.core_parse_segment_header(["#!/bin/sh\n", "echo hi\n"]))

    def test_header_present_but_empty_fields(self):
        self.assertEqual(sl.core_parse_segment_header(["# ai-kit-segment:\n"]), {})


class TestDiscover(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir, ignore_errors=True))
        # cache_dir is the resolved per-provider output cache directory (…/ai-kit/segments)
        self.cache_dir = os.path.join(self.dir, "cache", "ai-kit", "segments")

    def test_executable_with_header_is_discovered(self):
        write_script(self.dir, "aws.sh",
                     "#!/bin/sh\n# ai-kit-segment: line=2 after=clock id=aws ttl=30\necho hi\n")
        specs = sl.core_discover_external(self.dir, default_ttl=10, cache_dir=self.cache_dir)
        self.assertEqual(len(specs), 1)
        s = specs[0]
        self.assertEqual(s.id, "aws")
        self.assertEqual(s.position, ("after", "clock"))
        self.assertEqual(s.line, 2)
        self.assertEqual(s.ttl, 30)
        self.assertEqual(s.timeout, 2.0)
        self.assertTrue(s.cache_path.endswith(os.path.join("ai-kit", "segments", "aws")))

    def test_no_header_uses_defaults_and_stem_id(self):
        write_script(self.dir, "clockx", "#!/bin/sh\necho hi\n")
        specs = sl.core_discover_external(self.dir, default_ttl=7, cache_dir=self.cache_dir)
        self.assertEqual(specs[0].id, "clockx")
        self.assertEqual(specs[0].position, ("end", ""))
        self.assertEqual(specs[0].line, 0)        # 0 => "last row", resolved at placement
        self.assertEqual(specs[0].ttl, 7)

    def test_non_executable_skipped(self):
        write_script(self.dir, "noexec", "#!/bin/sh\necho hi\n", executable=False)
        self.assertEqual(sl.core_discover_external(self.dir, 10, self.cache_dir), [])

    def test_sorted_by_filename_then_id(self):
        write_script(self.dir, "b.sh", "#!/bin/sh\n# ai-kit-segment: id=zeta\necho\n")
        write_script(self.dir, "a.sh", "#!/bin/sh\n# ai-kit-segment: id=omega\necho\n")
        ids = [s.id for s in sl.core_discover_external(self.dir, 10, self.cache_dir)]
        self.assertEqual(ids, ["omega", "zeta"])   # a.sh before b.sh

    def test_missing_dir_returns_empty(self):
        self.assertEqual(sl.core_discover_external("/no/such/dir", 10, self.cache_dir), [])


class TestSanitize(unittest.TestCase):
    def test_first_non_empty_line(self):
        self.assertEqual(sl.util_sanitize_external("\n\n  hello \n second\n", 40), "  hello")

    def test_keeps_sgr_strips_other_csi(self):
        # \033[33m kept (SGR), \033[2J (clear) and cursor move \033[1A stripped
        out = sl.util_sanitize_external("\033[33mhi\033[0m\033[2J\033[1A", 40)
        self.assertEqual(out, "\033[33mhi\033[0m")

    def test_strips_osc_and_control_chars(self):
        out = sl.util_sanitize_external("\033]0;title\007ab\tc", 40)
        self.assertEqual(out, "abc")

    def test_truncates_to_avail_and_resets(self):
        out = sl.util_sanitize_external("\033[33mabcdef\033[0m", 3)
        self.assertEqual(sl.util_visible_width(out), 3)
        self.assertTrue(out.endswith(sl.RESET))

    def test_empty_after_sanitize_returns_none(self):
        self.assertIsNone(sl.util_sanitize_external("\033[2J\n", 40))
        self.assertIsNone(sl.util_sanitize_external("   \n", 40))

    def test_avail_zero_returns_none(self):
        self.assertIsNone(sl.util_sanitize_external("hi", 0))


class TestRunExternal(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cache = tempfile.mkdtemp()
        import shutil
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(self.cache, ignore_errors=True))

    def _spec(self, path, ttl=10, timeout=2.0):
        return sl.ExtSpec(id="t", path=path, line=1, position=("end", ""),
                          timeout=timeout, ttl=ttl,
                          cache_path=os.path.join(self.cache, "t"))

    def _data(self):
        return types.SimpleNamespace(
            raw={"workspace": {"current_dir": self.dir}}, work_dir=self.dir
        )

    def test_runs_and_returns_first_line(self):
        p = write_script(self.dir, "p", "#!/bin/sh\necho '\033[33mhi\033[0m'\n")
        self.assertEqual(sl.core_run_external(self._spec(p), self._data(), 40),
                         "\033[33mhi\033[0m")

    def test_receives_cols_via_env(self):
        p = write_script(self.dir, "p", '#!/bin/sh\necho "cols=$AI_KIT_SEGMENT_COLS"\n')
        self.assertEqual(sl.core_run_external(self._spec(p), self._data(), 17), "cols=17")

    def test_receives_segment_block_on_stdin(self):
        p = write_script(self.dir, "p",
                         '#!/usr/bin/env python3\n'
                         'import sys, json\n'
                         'd = json.load(sys.stdin)\n'
                         'print(d["segment"]["avail_cols"], d["segment"]["id"])\n')
        self.assertEqual(sl.core_run_external(self._spec(p), self._data(), 9), "9 t")

    def test_runs_in_workspace_dir(self):
        p = write_script(self.dir, "p", "#!/bin/sh\npwd\n")
        out = sl.core_run_external(self._spec(p), self._data(), 200)
        self.assertEqual(os.path.realpath(out), os.path.realpath(self.dir))

    def test_nonzero_exit_returns_none(self):
        p = write_script(self.dir, "p", "#!/bin/sh\necho x\nexit 1\n")
        self.assertIsNone(sl.core_run_external(self._spec(p), self._data(), 40))

    def test_timeout_returns_none(self):
        p = write_script(self.dir, "p", "#!/bin/sh\nsleep 5\n")
        self.assertIsNone(sl.core_run_external(self._spec(p, timeout=0.3), self._data(), 40))

    def test_empty_output_returns_none(self):
        p = write_script(self.dir, "p", "#!/bin/sh\nexit 0\n")
        self.assertIsNone(sl.core_run_external(self._spec(p), self._data(), 40))

    def test_caches_within_ttl(self):
        # writes a counter file each run; second call within ttl must not re-run
        counter = os.path.join(self.dir, "n")
        p = write_script(self.dir, "p",
                         f'#!/bin/sh\nprintf x >> "{counter}"\necho hi\n')
        spec = self._spec(p, ttl=100)
        self.assertEqual(sl.core_run_external(spec, self._data(), 40), "hi")
        self.assertEqual(sl.core_run_external(spec, self._data(), 40), "hi")
        with open(counter) as f:
            self.assertEqual(f.read(), "x")        # ran exactly once

    def test_ttl_zero_always_reruns(self):
        counter = os.path.join(self.dir, "n")
        p = write_script(self.dir, "p",
                         f'#!/bin/sh\nprintf x >> "{counter}"\necho hi\n')
        spec = self._spec(p, ttl=0)
        sl.core_run_external(spec, self._data(), 40)
        sl.core_run_external(spec, self._data(), 40)
        with open(counter) as f:
            self.assertEqual(f.read(), "xx")       # ran twice

    def test_ttl_expiry_reruns(self):
        # A cache older than ttl must miss and re-invoke the provider. Age the
        # cache file via os.utime instead of sleeping.
        counter = os.path.join(self.dir, "n")
        p = write_script(self.dir, "p",
                         f'#!/bin/sh\nprintf x >> "{counter}"\necho hi\n')
        spec = self._spec(p, ttl=30)
        self.assertEqual(sl.core_run_external(spec, self._data(), 40), "hi")  # run 1, writes cache
        old = time.time() - 31                                          # > ttl in the past
        os.utime(spec.cache_path, (old, old))
        self.assertEqual(sl.core_run_external(spec, self._data(), 40), "hi")  # cache stale -> run 2
        with open(counter) as f:
            self.assertEqual(f.read(), "xx")       # ran twice

    def test_unwritable_cache_dir_runs_uncached(self):
        # An unwritable cache dir must NOT break rendering: the provider still
        # runs and returns output, and (cache write having failed) every render
        # re-runs it rather than serving a stale value.
        counter = os.path.join(self.dir, "n")
        p = write_script(self.dir, "p",
                         f'#!/bin/sh\nprintf x >> "{counter}"\necho hi\n')
        ro = os.path.join(self.cache, "ro")
        os.makedirs(ro)
        os.chmod(ro, 0o500)                        # read+exec, no write
        self.addCleanup(lambda: os.chmod(ro, 0o700))   # so cleanup can rmtree
        spec = sl.ExtSpec(id="t", path=p, line=1, position=("end", ""),
                          timeout=2.0, ttl=100,
                          cache_path=os.path.join(ro, "sub", "t"))   # makedirs will fail
        self.assertEqual(sl.core_run_external(spec, self._data(), 40), "hi")
        self.assertEqual(sl.core_run_external(spec, self._data(), 40), "hi")
        self.assertFalse(os.path.exists(spec.cache_path))   # nothing cached
        with open(counter) as f:
            self.assertEqual(f.read(), "xx")       # ran twice (never cached)


class TestResolveExternal(unittest.TestCase):
    def test_config_has_external_default_none(self):
        cfg = sl.cfg_default_config()
        self.assertIsNone(cfg.external)

    def test_defaults(self):
        d, ttl = sl.cfg_resolve_external({}, {})
        self.assertEqual(ttl, 10)
        self.assertTrue(d.endswith(os.path.join("ai-kit", "segments")))

    def test_file_overrides(self):
        raw = {"external": {"ttl": 25, "dir": "/tmp/segs"}}
        d, ttl = sl.cfg_resolve_external(raw, {})
        self.assertEqual((d, ttl), ("/tmp/segs", 25))

    def test_env_wins(self):
        # FR-1.6: env overrides now applied by cfg_env_apply_overrides, not cfg_resolve_external.
        # Old names are back-compat aliases; test at the combined TOML+env layer.
        raw = {"external": {"ttl": 25, "dir": "/tmp/segs"}}
        env = sl.cfg_env_normalize(
            {"CC_AI_KIT_SEGMENTS_DIR": "/env/segs", "CC_AI_KIT_EXTERNAL_TTL": "3"}
        )
        d, ttl = sl.cfg_resolve_external(raw, env)
        _, d, ttl, _ = sl.cfg_env_apply_overrides(env, {}, d, ttl, {})
        self.assertEqual((d, ttl), ("/env/segs", 3))

    def test_bad_env_ttl_falls_back_to_file(self):
        # FR-1.6: bad env TTL now handled by cfg_env_apply_overrides (prints warning, ignores).
        raw = {"external": {"ttl": 25}}
        env = {"CC_AI_KIT_EXTERNAL_CACHE_TTL": "notanint"}
        d, ttl = sl.cfg_resolve_external(raw, env)
        _, _d, ttl, _ = sl.cfg_env_apply_overrides(env, {}, d, ttl, {})
        self.assertEqual(ttl, 25)


class TestPlace(unittest.TestCase):
    def _layout(self):
        return [sl.Line(0, ["path", "branch"]),
                sl.Line(20, ["model", "clock"]),
                sl.Line(30, ["context", "memory"])]

    def _spec(self, sid, line, position):
        return sl.ExtSpec(id=sid, path=f"/x/{sid}", line=line, position=position,
                          timeout=2.0, ttl=10, cache_path=f"/c/{sid}")

    def test_after_key(self):
        layout, final = sl.cfg_place_external(self._layout(),
                                           [self._spec("aws", 2, ("after", "clock"))])
        self.assertEqual(layout[1].segments, ["model", "clock", "aws"])
        self.assertEqual(final[0].line, 2)

    def test_before_key(self):
        layout, _ = sl.cfg_place_external(self._layout(),
                                       [self._spec("x", 2, ("before", "clock"))])
        self.assertEqual(layout[1].segments, ["model", "x", "clock"])

    def test_start_and_end(self):
        layout, _ = sl.cfg_place_external(self._layout(), [
            self._spec("s", 1, ("start", "")), self._spec("e", 1, ("end", ""))])
        self.assertEqual(layout[0].segments, ["s", "path", "branch", "e"])

    def test_line_zero_means_last_row(self):
        layout, final = sl.cfg_place_external(self._layout(),
                                           [self._spec("z", 0, ("end", ""))])
        self.assertEqual(layout[2].segments, ["context", "memory", "z"])
        self.assertEqual(final[0].line, 3)         # resolved to the last row

    def test_out_of_range_clamps_to_last(self):
        layout, final = sl.cfg_place_external(self._layout(),
                                           [self._spec("z", 9, ("end", ""))])
        self.assertEqual(layout[2].segments[-1], "z")
        self.assertEqual(final[0].line, 3)

    def test_missing_ref_appends(self):
        layout, _ = sl.cfg_place_external(self._layout(),
                                       [self._spec("z", 2, ("after", "nope"))])
        self.assertEqual(layout[1].segments, ["model", "clock", "z"])

    def test_min_rows_preserved(self):
        layout, _ = sl.cfg_place_external(self._layout(),
                                       [self._spec("z", 2, ("end", ""))])
        self.assertEqual([ln.min_rows for ln in layout], [0, 20, 30])


class TestLoadConfigExternal(unittest.TestCase):
    def setUp(self):
        import shutil
        self.dir = tempfile.mkdtemp()
        self.segs = os.path.join(self.dir, "segs")
        os.makedirs(self.segs)
        self.cfg = os.path.join(self.dir, "statusline.toml")
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))

    def _env(self, **extra):
        env = {"CC_AI_KIT_CONFIG": self.cfg, "CC_AI_KIT_SEGMENTS_DIR": self.segs,
               "XDG_CACHE_HOME": os.path.join(self.dir, "cache"), "HOME": self.dir}
        env.update(extra)
        return env

    def test_discovered_provider_enabled_by_default_and_placed(self):
        write_script(self.segs, "sysmem",
                     "#!/bin/sh\n# ai-kit-segment: line=1 end\necho hi\n")
        cfg = sl.cfg_load_config(self._env())
        self.assertTrue(cfg.segments.get("sysmem"))            # default-on
        self.assertIn("sysmem", cfg.layout[0].segments)        # placed on row 1
        self.assertEqual([s.id for s in cfg.external.providers], ["sysmem"])

    def test_explicit_disable_in_toml_is_honored(self):
        write_script(self.segs, "sysmem", "#!/bin/sh\necho hi\n")
        with open(self.cfg, "w") as f:
            f.write("[segments]\nsysmem = false\n")
        cfg = sl.cfg_load_config(self._env())
        self.assertFalse(cfg.segments["sysmem"])

    def test_env_toggle_disables_external(self):
        write_script(self.segs, "sysmem", "#!/bin/sh\necho hi\n")
        cfg = sl.cfg_load_config(self._env(CC_AI_KIT_SEGMENT_SYSMEM="0"))
        self.assertFalse(cfg.segments["sysmem"])

    def test_no_providers_keeps_external_empty(self):
        cfg = sl.cfg_load_config(self._env())
        self.assertIsNotNone(cfg.external)
        self.assertEqual(cfg.external.providers, [])


class TestRenderIntegration(unittest.TestCase):
    def setUp(self):
        import shutil
        self.dir = tempfile.mkdtemp()
        self.segs = os.path.join(self.dir, "segs")
        os.makedirs(self.segs)
        self.cfg = os.path.join(self.dir, "statusline.toml")
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))
        self.env = {"CC_AI_KIT_CONFIG": self.cfg, "CC_AI_KIT_SEGMENTS_DIR": self.segs,
                    "XDG_CACHE_HOME": os.path.join(self.dir, "cache"), "HOME": self.dir}

    def _render(self, cols=200, lines=40):
        cfg = sl.cfg_load_config(self.env)
        theme = sl.core_build_theme(cfg)
        raw = {"workspace": {"current_dir": self.dir},
               "context_window": {"used_percentage": 10, "context_window_size": 200000},
               "session_id": "x", "transcript_path": "", "rate_limits": {}}
        env = {**self.env, "STATUSLINE_COLS": str(cols), "STATUSLINE_LINES": str(lines)}
        data, _c, _l = _ctx_from_env(raw, env, cfg)
        return "\n".join(sl.core_render(data, cfg, theme))

    def test_external_segment_appears_in_render(self):
        write_script(self.segs, "ping",
                     "#!/bin/sh\n# ai-kit-segment: line=1 end\necho PONG\n")
        self.assertIn("PONG", self._render())

    def test_disabled_external_absent(self):
        write_script(self.segs, "ping", "#!/bin/sh\n# ai-kit-segment: line=1 end\necho PONG\n")
        with open(self.cfg, "w") as f:
            f.write("[segments]\nping = false\n")
        self.assertNotIn("PONG", self._render())

    def test_failing_provider_never_breaks_line(self):
        write_script(self.segs, "boom",
                     "#!/bin/sh\n# ai-kit-segment: line=1 end\nexit 3\n")
        out = self._render()
        self.assertNotIn("boom", out)              # omitted, no crash marker
        self.assertTrue(out)                        # line still renders

    def test_external_self_tiers_on_cols(self):
        write_script(self.segs, "t",
                     '#!/bin/sh\n# ai-kit-segment: line=1 end\n'
                     'if [ "$AI_KIT_SEGMENT_COLS" -ge 10 ]; then echo LONGFORM; '
                     'else echo S; fi\n')
        self.assertIn("LONGFORM", self._render(cols=200))


class TestCliSurface(unittest.TestCase):
    def setUp(self):
        import shutil
        self.dir = tempfile.mkdtemp()
        self.segs = os.path.join(self.dir, "segs")
        os.makedirs(self.segs)
        self.cfg = os.path.join(self.dir, "statusline.toml")
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))
        self.env = {"CC_AI_KIT_CONFIG": self.cfg, "CC_AI_KIT_SEGMENTS_DIR": self.segs,
                    "XDG_CACHE_HOME": os.path.join(self.dir, "cache"), "HOME": self.dir}

    def test_print_config_lists_external(self):
        write_script(self.segs, "sysmem", "#!/bin/sh\n# ai-kit-segment: line=1 end\necho hi\n")
        cfg = sl.cfg_load_config(self.env)
        blob = json.loads(doctor.cmd_print_config(cfg, self.env))
        self.assertEqual(blob["external"]["providers"][0]["id"], "sysmem")
        self.assertIn("ttl", blob["external"])
        # `dir` is the PROVIDERS directory, not the XDG cache dir.
        self.assertEqual(blob["external"]["dir"], self.segs)

    def test_validate_accepts_external_id_in_segments(self):
        write_script(self.segs, "sysmem", "#!/bin/sh\necho hi\n")
        with open(self.cfg, "w") as f:
            f.write("[segments]\nsysmem = false\n")
        self.assertEqual(doctor.validate_config_file(self.cfg, self.env), [])

    def test_validate_flags_unknown_external_key(self):
        with open(self.cfg, "w") as f:
            f.write("[external]\nbogus = 1\n")
        errs = doctor.validate_config_file(self.cfg, self.env)
        self.assertTrue(any("external" in e for e in errs))

    def test_validate_flags_bad_external_ttl(self):
        with open(self.cfg, "w") as f:
            f.write('[external]\nttl = "soon"\n')
        errs = doctor.validate_config_file(self.cfg, self.env)
        self.assertTrue(any("ttl" in e for e in errs))


class TestSampleProvider(unittest.TestCase):
    PATH = os.path.join(_HERE, "..", "examples", "segments", "sysmem")

    def test_is_executable_with_header(self):
        self.assertTrue(os.access(self.PATH, os.X_OK), "sysmem must be chmod +x")
        with open(self.PATH, encoding="utf-8") as f:
            head = [f.readline() for _ in range(10)]
        self.assertIsNotNone(sl.core_parse_segment_header(head))

    def test_runs_and_emits_one_sgr_line(self):
        spec = sl.ExtSpec(id="sysmem", path=os.path.abspath(self.PATH), line=1,
                          position=("after", "context"), timeout=3.0, ttl=0,
                          cache_path=os.path.join(tempfile.mkdtemp(), "sysmem"))
        data = types.SimpleNamespace(raw={}, work_dir=".")
        out = sl.core_run_external(spec, data, 40)
        # Renders on Linux/macOS; on an unsupported platform it cleanly drops (None).
        if out is not None:
            self.assertEqual(out.count("\n"), 0)
            self.assertLessEqual(sl.util_visible_width(out), 40)

    def test_short_budget_tiers_down_or_drops(self):
        spec = sl.ExtSpec(id="sysmem", path=os.path.abspath(self.PATH), line=1,
                          position=("end", ""), timeout=3.0, ttl=0,
                          cache_path=os.path.join(tempfile.mkdtemp(), "sysmem"))
        out = sl.core_run_external(spec, types.SimpleNamespace(raw={}, work_dir="."), 4)
        if out is not None:
            self.assertLessEqual(sl.util_visible_width(out), 4)


class TestRecipe(unittest.TestCase):
    PATH = os.path.join(_HERE, "..", "tools", "statusline.toml.sample")

    def test_recipe_has_commented_external_block(self):
        with open(self.PATH, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("[external]", text)
        self.assertIn("CC_AI_KIT_SEGMENTS_DIR", text)
        # Block ships fully commented (NO-OP): no live (uncommented) [external].
        for line in text.splitlines():
            self.assertNotEqual(line.strip(), "[external]",
                                "the [external] block must ship commented out")


if __name__ == "__main__":
    unittest.main()
