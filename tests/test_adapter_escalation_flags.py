"""Fix rounds 4 and 5 escalate only along the stuck lane's flags (fake lanes only)."""

import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute-superpowers")
)

from ai_kit_spec import config_io, lane_settings
from ai_kit_spec_superpowers import cli
from ai_kit_spec_superpowers.dispatch_injection import escalation_gate

SUPER_DIR = (
    pathlib.Path(__file__).resolve().parents[1] / "skills" / "ai-kit-spec-execute-superpowers"
)

TOP = {"key": "lane-top", "runtime": "opencode", "model": "fake/placeholder-model-3"}
SAME = {"key": "lane-same", "runtime": "codex", "model": "placeholder-model-2"}
ANCHOR = {"key": "lane-anchor", "runtime": "codex", "model": "placeholder-model-1"}
BELOW = {"key": "lane-below", "runtime": "codex", "model": "placeholder-model-4"}
NEW = {"key": "lane-new", "runtime": "opencode", "model": "fake/placeholder-model-5"}
LADDER = ["lane-top", "lane-same", "lane-anchor", "lane-below"]


def flag(runtime=False, model=False) -> dict:
    result = {}
    if runtime:
        result[lane_settings.LANE_FLAG_KEYS[0]] = True
    if model:
        result[lane_settings.LANE_FLAG_KEYS[1]] = True
    return result


def lanes(**flags) -> list:
    return [TOP, SAME, {**ANCHOR, **flags}, BELOW]


class TestEscalationGate(unittest.TestCase):
    def test_model_flag_moves_only_to_same_runtime(self):
        gate = escalation_gate(lanes(**flag(model=True)), "lane-anchor", LADDER)
        self.assertTrue(gate["escalate"])
        self.assertEqual(["lane-same"], gate["allowed"])
        self.assertEqual("flags", gate["reason"])

    def test_runtime_flag_moves_only_to_another_runtime(self):
        gate = escalation_gate(lanes(**flag(runtime=True)), "lane-anchor", LADDER)
        self.assertTrue(gate["escalate"])
        self.assertEqual(["lane-top"], gate["allowed"])

    def test_both_flags_keep_todays_floor(self):
        gate = escalation_gate(lanes(**flag(runtime=True, model=True)), "lane-anchor", LADDER)
        self.assertEqual(["lane-top", "lane-same"], gate["allowed"])
        self.assertEqual(["lane-anchor", "lane-below"], gate["exclude"])

    def test_both_off_keep_the_lane(self):
        gate = escalation_gate(lanes(), "lane-anchor", LADDER)
        self.assertFalse(gate["escalate"])
        self.assertEqual(["lane-anchor"], gate["allowed"])
        self.assertEqual("off", gate["reason"])
        self.assertEqual(["lane-below", "lane-same", "lane-top"], gate["exclude"])

    def test_flag_with_no_target_keeps_the_lane(self):
        roster = [TOP, {**SAME, "runtime": "opencode"}, {**ANCHOR, **flag(model=True)}, BELOW]
        gate = escalation_gate(roster, "lane-anchor", LADDER)
        self.assertFalse(gate["escalate"])
        self.assertEqual("no-target", gate["reason"])

    def test_a_lane_added_since_the_ladder_is_excluded(self):
        gate = escalation_gate([*lanes(**flag(model=True)), NEW], "lane-anchor", LADDER)
        self.assertIn("lane-new", gate["exclude"])
        self.assertEqual(["lane-same"], gate["allowed"])

    def test_non_boolean_flag_is_refused_with_the_key(self):
        bad = {lane_settings.LANE_FLAG_KEYS[1]: "yes"}
        with self.assertRaises(lane_settings.LaneSettingError) as ctx:
            escalation_gate(lanes(**bad), "lane-anchor", LADDER)
        self.assertIn("lane-anchor", str(ctx.exception))
        self.assertIn("must be a boolean", str(ctx.exception))

    def test_empty_or_unknown_anchor_raises(self):
        for anchor in ("", "lane-gone"):
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                escalation_gate(lanes(), anchor, LADDER)

    def test_anchor_without_execute_lane(self):
        roster = [TOP, SAME, BELOW]
        with self.assertRaises(ValueError) as ctx:
            escalation_gate(roster, "lane-anchor", LADDER)
        self.assertNotIsInstance(ctx.exception, lane_settings.LaneSettingError)
        self.assertEqual("empty or unknown anchor", str(ctx.exception))


class TestEscalationGateCli(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.cwd = os.path.join(tmp.name, "project")
        os.makedirs(self.cwd)
        self.env = {"HOME": os.path.join(tmp.name, "home"),
                    "XDG_CONFIG_HOME": os.path.join(tmp.name, "xdg"),
                    "XDG_CACHE_HOME": os.path.join(tmp.name, "cache")}
        self.out = os.path.join(tmp.name, "out")
        os.makedirs(self.out)
        self.injection = os.path.join(self.out, "INJECTION_JSON.json")
        self.write_text(self.injection, json.dumps({"ladder_keys": LADDER}))

    @staticmethod
    def write_text(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def render(self, lane_list) -> str:
        return config_io.cfg_render_lanes({
            "policy": {"execute": {"ladder": LADDER}},
            "lanes": [{**lane, "purpose": "execute"} for lane in lane_list]})

    def write_roster(self, lane_list):
        self.write_text(config_io.cfg_global_path(self.env), self.render(lane_list))

    def invoke_gate(self, key, injection_file=None, out_dir=None):
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stderr(err):
            rc = cli.main(
                ["escalation-gate", "--cwd", self.cwd, "--anchor-key", key,
                 "--injection-file", injection_file or self.injection,
                 "--out-dir", out_dir or self.out],
                env_fn=lambda: dict(self.env), stdout=buf)
        return rc, buf.getvalue(), err.getvalue()

    def read_out(self, name):
        with open(os.path.join(self.out, name), encoding="utf-8") as handle:
            return json.load(handle)

    def gate_files(self):
        return [name for name in ("ESCALATION_EXCLUDE_JSON.json", "ESCALATION_ALLOWED_JSON.json")
                if os.path.exists(os.path.join(self.out, name))]

    def test_off_prints_the_notice_and_writes_both_files(self):
        self.write_roster(lanes())
        rc, stdout, stderr = self.invoke_gate("lane-anchor")
        self.assertEqual(0, rc)
        self.assertEqual(["lane-anchor"], json.loads(stdout)["allowed"])
        self.assertIn("ai-kit-spec: fix round stays on lane-anchor: "
                      "escalation is off for this lane", stderr)
        self.assertEqual(["lane-anchor"], self.read_out("ESCALATION_ALLOWED_JSON.json"))
        self.assertEqual(["lane-below", "lane-same", "lane-top"],
                         self.read_out("ESCALATION_EXCLUDE_JSON.json"))

    def test_no_target_prints_its_notice(self):
        self.write_roster([TOP, {**SAME, "runtime": "opencode"}, {**ANCHOR, **flag(model=True)},
                           BELOW])
        rc, _stdout, stderr = self.invoke_gate("lane-anchor")
        self.assertEqual(0, rc)
        self.assertIn("no lane above it matches the lane's escalation flags", stderr)

    def test_unknown_anchor_exits_3_and_writes_nothing(self):
        self.write_roster(lanes())
        for anchor in ("", "lane-gone"):
            with self.subTest(anchor=anchor):
                rc, stdout, stderr = self.invoke_gate(anchor)
                self.assertEqual(3, rc)
                self.assertIn("ai-kit-spec: STOP: empty or unknown ESCALATION_ANCHOR_KEY", stderr)
                self.assertEqual("", stdout)
                self.assertEqual([], self.gate_files())

    def test_anchor_dropped_from_the_roster_exits_3(self):
        kept = [TOP, SAME, BELOW]
        self.write_text(config_io.cfg_global_path(self.env), config_io.cfg_render_lanes({
            "policy": {"execute": {"ladder": [lane["key"] for lane in kept]}},
            "lanes": [{**lane, "purpose": "execute"} for lane in kept]}))
        rc, stdout, stderr = self.invoke_gate("lane-anchor")
        self.assertEqual(3, rc)
        self.assertIn("ai-kit-spec: STOP: empty or unknown ESCALATION_ANCHOR_KEY", stderr)
        self.assertEqual("", stdout)
        self.assertEqual([], self.gate_files())

    def test_non_boolean_flag_exits_2_with_the_key(self):
        name = lane_settings.LANE_FLAG_KEYS[1]
        text = self.render(lanes(**flag(model=True)))
        self.assertEqual(1, text.count(f"{name} = true"))
        self.write_text(config_io.cfg_global_path(self.env),
                        text.replace(f"{name} = true", f'{name} = "yes"'))
        rc, stdout, stderr = self.invoke_gate("lane-anchor")
        self.assertEqual(2, rc)
        self.assertIn(f"lane-anchor: '{name}' must be a boolean", stderr)
        self.assertEqual("", stdout)
        self.assertEqual([], self.gate_files())

    def test_unreadable_injection_file_exits_2(self):
        self.write_roster(lanes())
        bad_files = {"missing": None, "not-json": "{not json", "list": "[]",
                     "string-keys": json.dumps({"ladder_keys": "x"}),
                     "mixed-keys": json.dumps({"ladder_keys": ["lane-top", 3]}),
                     "no-keys": json.dumps({"mode": "external_cli"})}
        for label, content in bad_files.items():
            with self.subTest(label=label):
                path = os.path.join(self.root, f"bad-{label}.json")
                if content is not None:
                    self.write_text(path, content)
                rc, _stdout, stderr = self.invoke_gate("lane-anchor", injection_file=path)
                self.assertEqual(2, rc)
                self.assertIn(
                    f"ai-kit-spec: escalation-gate: unreadable --injection-file {path}\n", stderr)
                self.assertEqual([], self.gate_files())

    def test_unwritable_out_dir_exits_2(self):
        self.write_roster(lanes())
        not_a_dir = os.path.join(self.root, "plain-file")
        self.write_text(not_a_dir, "x")
        rc, stdout, stderr = self.invoke_gate("lane-anchor", out_dir=not_a_dir)
        self.assertEqual(2, rc)
        self.assertIn("ai-kit-spec: escalation-gate: cannot write", stderr)
        self.assertEqual("", stdout)

    def test_a_failed_second_rename_leaves_no_gate_file(self):
        self.write_roster(lanes())
        for name in ("ESCALATION_EXCLUDE_JSON.json", "ESCALATION_ALLOWED_JSON.json"):
            self.write_text(os.path.join(self.out, name), '["stale"]')
        real_replace = os.replace
        calls = []

        def replace(src, dst):
            calls.append(dst)
            if len(calls) == 2:
                raise OSError("disk full")
            real_replace(src, dst)

        with mock.patch.object(cli.os, "replace", side_effect=replace):
            rc, stdout, stderr = self.invoke_gate("lane-anchor")
        self.assertEqual(2, rc)
        self.assertIn("ai-kit-spec: escalation-gate: cannot write", stderr)
        self.assertEqual("", stdout)
        self.assertEqual(["INJECTION_JSON.json"], sorted(os.listdir(self.out)))


class TestGateFeedsTheResolver(TestEscalationGateCli):
    def resolve(self, exclude_keys, reasons, escalation_exclude):
        order = (NEW, TOP, SAME, ANCHOR, BELOW)
        keys = [lane["key"] for lane in order]
        candidates = [{"key": lane["key"], "model": lane["model"], "runtime": lane["runtime"],
                       "vendor": "v", "task_affinity": None, "context_limit": None}
                      for lane in order]
        task = os.path.join(self.root, "task-1-brief.md")
        self.write_text(task, "### Task 1\n**Files:**\n- Create: `README.md`\n")
        buf = io.StringIO()
        rc = cli.main(
            ["resolve-injection", "--cwd", self.cwd, "--task-file", task,
             "--quota-path", os.path.join(self.root, "quota.json"),
             "--exclude-keys-json", json.dumps(exclude_keys),
             "--excluded-reasons-json", json.dumps(reasons),
             "--escalation-excluded-keys-json", json.dumps(escalation_exclude)],
            assemble_candidates_fn=lambda cwd, env: (candidates, keys),
            cache_read_json_fn=lambda path: {}, cache_write_json_fn=lambda path, data: None,
            refresh_quota_cache_fn=lambda config, ks, existing, _ttl: {},
            route_all_fn=lambda entries, _ctx: {e["key"]: "subprocess" for e in entries},
            stdout=buf)
        return rc, json.loads(buf.getvalue())

    def test_stale_ladder_never_picks_the_new_lane(self):
        self.write_roster([*lanes(**flag(model=True)), NEW])
        rc, _stdout, _stderr = self.invoke_gate("lane-anchor")
        self.assertEqual(0, rc)
        exclude = self.read_out("ESCALATION_EXCLUDE_JSON.json")
        rc, result = self.resolve([], {}, exclude)
        self.assertEqual(0, rc)
        self.assertEqual("external_cli", result["mode"])
        self.assertEqual("lane-same", result["key"])
        self.assertIn(result["key"], self.read_out("ESCALATION_ALLOWED_JSON.json"))

    def test_unavailable_anchor_is_a_quota_stop(self):
        self.write_roster([*lanes(), NEW])
        rc, _stdout, _stderr = self.invoke_gate("lane-anchor")
        self.assertEqual(0, rc)
        exclude = self.read_out("ESCALATION_EXCLUDE_JSON.json")
        rc, result = self.resolve(["lane-anchor"], {"lane-anchor": "quota"}, exclude)
        self.assertEqual(0, rc)
        self.assertEqual("quota_exhausted", result["mode"])
        self.assertNotIn("key", result)


class TestEscalationDocs(unittest.TestCase):
    @staticmethod
    def flat(path) -> str:
        return " ".join(path.read_text(encoding="utf-8").split())

    def setUp(self):
        self.escalation = SUPER_DIR / "references" / "escalation.md"
        self.stops = SUPER_DIR / "references" / "resolution-stops.md"

    def test_reference_runs_the_gate_with_a_file(self):
        text = self.escalation.read_text(encoding="utf-8")
        self.assertIn("escalation-gate --cwd", text)
        self.assertIn('--injection-file "$RUN_DIR/INJECTION_JSON.json"', text)
        self.assertNotIn("ladder.index(stuck)", text)

    def test_reference_says_same_lane_not_a_bump(self):
        self.assertIn("the same lane, not a bump", self.flat(self.escalation))

    def test_owner_pick_drops_a_stale_allowed_file(self):
        flat = self.flat(self.escalation)
        self.assertIn("delete any `$RUN_DIR/ESCALATION_ALLOWED_JSON.json`", flat)
        self.assertIn("only when `$INJECTION_KEY` equals the picked key", flat)
        self.assertIn("An unavailable kept lane", self.flat(self.stops))

    def test_skill_points_at_the_flags(self):
        self.assertIn("flags decide whether, and along which kind, the round moves",
                      self.flat(SUPER_DIR / "SKILL.md"))

    def test_allowed_check_stops_on_a_key_outside_the_list(self):
        text = self.escalation.read_text(encoding="utf-8")
        block = next(b for b in re.findall(r"```bash\n(.*?)```", text, re.DOTALL)
                     if "ESCALATION_ALLOWED_JSON" in b)
        bash = shutil.which("bash")
        assert bash is not None
        with tempfile.TemporaryDirectory() as run:
            with open(os.path.join(run, "ESCALATION_ALLOWED_JSON.json"), "w",
                      encoding="utf-8") as handle:
                json.dump(["lane-same"], handle)

            def check(key):
                return subprocess.run(
                    [bash, "-c", block], env={**os.environ, "RUN_DIR": run, "INJECTION_KEY": key},
                    capture_output=True, text=True, timeout=60, check=False)

            self.assertEqual(0, check("lane-same").returncode)
            proc = check("lane-new")
            self.assertEqual(1, proc.returncode)
            self.assertIn("STOP", proc.stdout)


if __name__ == "__main__":
    unittest.main()
