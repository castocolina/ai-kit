"""Tests for tools/statusline-doctor.py — the extracted introspection CLI.

The doctor script imports the render core (status-line.py) one-way via its own
importlib shim; this test module loads the doctor script the same way and exercises
parse_args / cmd_print_config / cmd_check / cmd_doctor / validate_config_file.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

_HERE = os.path.dirname(__file__)
_DOCTOR_PATH = os.path.join(_HERE, "..", "tools", "statusline-doctor.py")


def load_module():
    spec = importlib.util.spec_from_file_location("statusline_doctor", _DOCTOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


doctor = load_module()
sl = doctor.sl   # the render core the doctor imported


class TestCLI(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_parse_args_defaults(self):
        ns = doctor.parse_args([])
        self.assertFalse(ns.print_config)
        self.assertIs(ns.check, doctor._NO_CHECK)

    def test_print_config_emits_resolved_json(self):
        import json
        cfg = sl.Config(segments={"path": True}, layout=[sl.Line(0, ["path"])],
                        palette={"BLUE": "1;34"}, ramps={})
        out = doctor.cmd_print_config(cfg, {})
        parsed = json.loads(out)
        self.assertEqual(parsed["segments"], {"path": True})
        self.assertEqual(parsed["layout"], [{"min_rows": 0, "segments": ["path"]}])
        self.assertEqual(parsed["palette"], {"BLUE": "1;34"})

    def test_check_valid_returns_zero(self):
        path = self._write('[segments]\ncost = true\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 0)

    def test_check_unknown_segment_returns_one(self):
        path = self._write('[segments]\nbogus = true\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_layout_ref_returns_one(self):
        path = self._write('[[line]]\nsegments = ["nope"]\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_malformed_returns_one(self):
        path = self._write('= = not toml')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_palette_hex_returns_one(self):
        path = self._write('[palette]\nBLUE = "#zzz"\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_unknown_modifier_returns_one(self):
        path = self._write('[palette]\nRED = "31+blink"\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_ramp_color_returns_one(self):
        path = self._write('[ramp.context]\n10 = "NOTACOLOR"\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_ramp_threshold_returns_one(self):
        path = self._write('[ramp.context]\noops = "RED"\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_valid_palette_and_ramp_returns_zero(self):
        path = self._write('[palette]\nBLUE = "#3399ff"\n'
                           '[ramp.rate]\n50 = "GREEN"\ninf = "RED+bold"\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 0)


class TestValidateConfigFile(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_check_flags_unknown_and_bad_ttl_but_not_legacy_worktree(self):
        # `bogus` and a bad cache_ttl are flagged; legacy `worktree` is NOT.
        path = self._write('[git]\nbogus = true\nworktree = "x"\ncache_ttl = "nope"\n')
        errors = doctor.validate_config_file(path, {"HOME": "/h"})
        self.assertTrue(any("bogus" in e for e in errors), errors)
        self.assertTrue(any("cache_ttl" in e for e in errors), errors)
        self.assertFalse(any("worktree" in e for e in errors), errors)


class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Resolve config to a path that does NOT exist → defaults, which are valid.
        self.env = {"HOME": self.tmp,
                    "CC_AI_KIT_CONFIG": os.path.join(self.tmp, "absent.toml")}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_doctor_ok_on_defaults(self):
        rc = doctor.cmd_doctor(self.env)
        self.assertEqual(rc, 0)

    def test_doctor_flags_a_raising_builder(self):
        def boom(data, avail, theme):
            raise RuntimeError("x")
        with mock.patch.dict(sl.BUILDERS, {"path": boom}):
            rc = doctor.cmd_doctor(self.env)
        self.assertEqual(rc, 1)

    def test_doctor_flags_a_raising_disabled_builder(self):
        # A builder that is DISABLED by default (`alt_cost`) must still be
        # dry-rendered: the doctor catches a builder that would crash once enabled.
        self.assertFalse(sl.cfg_default_config().segments.get("alt_cost"))
        def boom(data, avail, theme):
            raise RuntimeError("x")
        with mock.patch.dict(sl.BUILDERS, {"alt_cost": boom}):
            rc = doctor.cmd_doctor(self.env)
        self.assertEqual(rc, 1)

    def test_doctor_flags_invalid_config_file(self):
        bad = os.path.join(self.tmp, "bad.toml")
        with open(bad, "w") as f:
            f.write("[segments]\nthis_is_not_a_segment = true\n")
        env = dict(self.env, CC_AI_KIT_CONFIG=bad)
        rc = doctor.cmd_doctor(env)
        self.assertEqual(rc, 1)

    def test_check_flag_still_works(self):
        # Back-compat: --check path is untouched.
        rc = doctor.cmd_check(os.path.join(self.tmp, "absent.toml"), self.env)
        self.assertEqual(rc, 1)   # absent file → cmd_check reports it (existing behavior)


if __name__ == "__main__":
    unittest.main()
