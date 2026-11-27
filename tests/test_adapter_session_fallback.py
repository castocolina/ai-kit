"""The session-model fallback: flag, jev pick and stop message (fake lanes and a fake jev only)."""

import io
import json
import os
import pathlib
import re
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

from ai_kit_spec import config_io, detection, jev_names, lane_settings
from ai_kit_spec_superpowers import cli, dispatch_injection
from ai_kit_spec_superpowers.dispatch_injection import session_fallback_injection

CLAUDE_SIGNAL = detection.RUNTIMES["claude"].host_signals[0][0]
SUMMARY = "Task type: feature. Files named: 2. Fix round: 0."


def jev_run(choice, top=0.9, needs_fallback=False, returncode=0, calls=None):
    def run(argv, **kwargs):
        if calls is not None:
            calls.append(kwargs.get("input"))
        body = {
            "items": {
                "k0": {
                    "decided_by": "jev",
                    "jev": {"choice": choice, "top": top, "needs_fallback": needs_fallback},
                }
            }
        }
        return subprocess.CompletedProcess(argv, returncode, json.dumps(body), "")

    return run


class TestPickSessionModel(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.env = {"HOME": tmp.name}
        self.claude = {**self.env, CLAUDE_SIGNAL: "1"}
        patcher = mock.patch.object(jev_names, "find_jev", return_value="fake-jev-entry")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_non_claude_host_asks_nothing(self):
        calls = []
        result = dispatch_injection.pick_session_model(
            SUMMARY, self.env, jev_run("haiku", calls=calls)
        )
        self.assertEqual(result, ("", "host takes no model"))
        self.assertEqual(calls, [])

    def test_jev_absent(self):
        with mock.patch.object(jev_names, "find_jev", return_value=None):
            result = dispatch_injection.pick_session_model(SUMMARY, self.claude, jev_run("haiku"))
        self.assertEqual(result, ("", "jev absent"))

    def test_confident_pick_sets_the_model(self):
        for pick in dispatch_injection.SESSION_PICKS:
            result = dispatch_injection.pick_session_model(SUMMARY, self.claude, jev_run(pick))
            self.assertEqual(result, (pick, f"jev {pick} (0.90)"))

    def test_low_answer_keeps_the_session_model(self):
        result = dispatch_injection.pick_session_model(
            SUMMARY, self.claude, jev_run("haiku", top=0.5)
        )
        self.assertEqual(result, ("", "jev low: session model kept"))

    def test_needs_fallback_keeps_the_session_model(self):
        run = jev_run("haiku", needs_fallback=True)
        result = dispatch_injection.pick_session_model(SUMMARY, self.claude, run)
        self.assertEqual(result, ("", "jev low: session model kept"))

    def test_choice_outside_the_picks_is_discarded(self):
        run = jev_run("placeholder-alias-1")
        result = dispatch_injection.pick_session_model(SUMMARY, self.claude, run)
        self.assertEqual(result, ("", "jev low: session model kept"))

    def test_failed_run_keeps_the_session_model(self):
        result = dispatch_injection.pick_session_model(
            SUMMARY, self.claude, jev_run("haiku", returncode=1)
        )
        self.assertEqual(result, ("", "jev low: session model kept"))

        def broken(argv, **kwargs):
            raise OSError("no such file")

        result = dispatch_injection.pick_session_model(SUMMARY, self.claude, broken)
        self.assertEqual(result, ("", "jev low: session model kept"))

    def test_payload_holds_only_the_summary(self):
        calls = []
        dispatch_injection.pick_session_model(SUMMARY, self.claude, jev_run("haiku", calls=calls))
        self.assertEqual(len(calls), 1)
        items = json.loads(calls[0])["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["context"], SUMMARY)

    def test_picks_stay_native_selectors(self):
        self.assertLessEqual(
            set(dispatch_injection.SESSION_PICKS),
            set(detection.RUNTIMES["claude"].native_selectors),
        )


class TestSessionFallbackInjection(unittest.TestCase):
    ON = {"policy": {"execute": {lane_settings.SESSION_FALLBACK_KEY: True}}}
    OFF = {"policy": {"execute": {"ladder": []}}}

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.env = {"HOME": tmp.name}
        self.claude = {**self.env, CLAUDE_SIGNAL: "1"}
        patcher = mock.patch.object(jev_names, "find_jev", return_value="fake-jev-entry")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_flag_off_and_empty_config_ask_nothing(self):
        for config in (self.OFF, {}):
            with self.subTest(config=config):
                calls = []
                result = session_fallback_injection(
                    config, ["k"], SUMMARY, self.claude, jev_run("haiku", calls=calls)
                )
                self.assertIsNone(result)
                self.assertEqual(calls, [])

    def test_flag_on_non_claude_host_takes_no_model(self):
        result = session_fallback_injection(self.ON, ["k"], SUMMARY, self.env, jev_run("haiku"))
        assert result is not None
        self.assertEqual(result["model"], "")
        self.assertEqual(result["fallback"], "session")
        self.assertEqual(result["fallback_note"], "host takes no model")
        self.assertEqual(result["key"], "")
        self.assertEqual(result["mode"], "native")
        self.assertEqual(result["ladder_keys"], ["k"])

    def test_flag_on_confident_jev_sets_the_model(self):
        pick = dispatch_injection.SESSION_PICKS[1]
        result = session_fallback_injection(self.ON, [], SUMMARY, self.claude, jev_run(pick))
        assert result is not None
        self.assertEqual(result["model"], pick)


LANE_A = {"key": "lane-a", "runtime": "codex", "model": "placeholder-model-1"}
LANE_B = {"key": "lane-b", "runtime": "codex", "model": "placeholder-model-2"}
OUT = {"available": False, "reason": "quota", "detail": "usage limit reached"}
OFF_TEXT = "run ai-kit-spec-config to add one or to turn on the session-model fallback"


class TestResolveInjectionFallback(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.cwd = os.path.join(tmp.name, "project")
        os.makedirs(self.cwd)
        self.env = {
            "HOME": os.path.join(tmp.name, "home"),
            "XDG_CONFIG_HOME": os.path.join(tmp.name, "xdg"),
            "XDG_CACHE_HOME": os.path.join(tmp.name, "cache"),
            CLAUDE_SIGNAL: "1",
        }
        self.task = os.path.join(tmp.name, "task-1-brief.md")
        self.write_task("### Task 1\n**Files:**\n- Create: `README.md`\nUNIQUE-BRIEF-MARKER-7\n")
        patcher = mock.patch.object(jev_names, "find_jev", return_value="fake-jev-entry")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.jev_calls = []

    def write_task(self, text):
        with open(self.task, "w", encoding="utf-8") as handle:
            handle.write(text)

    def _scratch_roster(self, lanes, flag):
        execute: dict = {"ladder": [lane["key"] for lane in lanes]}
        if flag:
            execute[lane_settings.SESSION_FALLBACK_KEY] = True
        text = config_io.cfg_render_lanes(
            {
                "policy": {"execute": execute},
                "lanes": [{**lane, "purpose": "execute"} for lane in lanes],
            }
        )
        os.makedirs(os.path.dirname(config_io.cfg_global_path(self.env)), exist_ok=True)
        with open(config_io.cfg_global_path(self.env), "w", encoding="utf-8") as handle:
            handle.write(text)
        return text

    def _run_fn(self):
        def run(argv, **kwargs):
            self.jev_calls.append({"input": kwargs.get("input"), "cwd": kwargs.get("cwd")})
            body = {
                "items": {
                    "k0": {
                        "decided_by": "jev",
                        "jev": {"choice": "haiku", "top": 0.9, "needs_fallback": False},
                    }
                }
            }
            return subprocess.CompletedProcess(argv, 0, json.dumps(body), "")

        return run

    def resolve(self, lanes, quota, *extra, candidates=None, task=None):
        candidates = candidates if candidates is not None else [
            {
                "key": lane["key"], "model": lane["model"], "runtime": lane["runtime"],
                "vendor": "v", "task_affinity": None, "context_limit": None,
            }
            for lane in lanes
        ]
        keys = [c["key"] for c in candidates]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):
            rc = cli.main(
                ["resolve-injection", "--cwd", self.cwd, "--task-file", task or self.task,
                 "--quota-path", os.path.join(self.root, "quota.json"), *extra],
                assemble_candidates_fn=lambda cwd, env: (candidates, keys),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, ks, existing, _ttl: quota,
                route_all_fn=lambda entries, _ctx: {e["key"]: "subprocess" for e in entries},
                run_fn=self._run_fn(),
                env_fn=lambda: self.env,
                stdout=out,
            )
        return rc, out.getvalue(), err.getvalue()

    def test_flag_on_and_every_lane_out_runs_native(self):
        self._scratch_roster([LANE_A, LANE_B], True)
        rc, out, err = self.resolve([LANE_A, LANE_B], {"lane-a": OUT, "lane-b": OUT})
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertEqual(result["mode"], "native")
        self.assertEqual(result["key"], "")
        self.assertEqual(result["fallback"], "session")
        self.assertIn("this task runs on the session model", err)

    def test_sole_quota_out_lane_triggers_the_fallback(self):
        self._scratch_roster([LANE_A], True)
        rc, out, err = self.resolve([LANE_A], {"lane-a": OUT})
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["fallback"], "session")
        self.assertIn("this task runs on the session model", err)

    def test_real_narrowing_to_no_candidate_is_never_replaced(self):
        self._scratch_roster([LANE_A], True)
        with open(os.path.join(self.cwd, "big.py"), "w", encoding="utf-8") as handle:
            handle.write("x" * 4000)
        self.write_task("### Task 1\n**Files:**\n- Modify: `big.py`\n")
        small = [{"key": "lane-a", "model": "placeholder-model-1", "runtime": "codex",
                  "vendor": "v", "task_affinity": None, "context_limit": 10}]
        rc, out, err = self.resolve([LANE_A], {}, candidates=small)
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertEqual(result["mode"], "no_candidate")
        self.assertNotIn("fallback", result)
        self.assertNotIn("session model", err)
        self.assertEqual(self.jev_calls, [])

    def test_available_lane_is_never_replaced(self):
        self._scratch_roster([LANE_A], True)
        rc, out, err = self.resolve([LANE_A], {})
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["mode"], "external_cli")
        self.assertNotIn("session model", err)

    def test_flag_off_names_spec_config(self):
        self._scratch_roster([LANE_A, LANE_B], False)
        rc, out, err = self.resolve([LANE_A, LANE_B], {"lane-a": OUT, "lane-b": OUT})
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["mode"], "quota_exhausted")
        self.assertIn(OFF_TEXT, err)
        self.assertEqual(self.jev_calls, [])

    def assert_plain(self, *extra, lanes=(LANE_A, LANE_B)):
        lanes = list(lanes)
        quota = {lane["key"]: OUT for lane in lanes}
        self._scratch_roster(lanes, False)
        _rc, plain_out, _err = self.resolve(lanes, quota, *extra)
        self._scratch_roster(lanes, True)
        rc, out, err = self.resolve(lanes, quota, *extra)
        self.assertEqual(rc, 0)
        self.assertEqual(out, plain_out)
        self.assertEqual(json.loads(out)["mode"], "quota_exhausted")
        self.assertEqual(self.jev_calls, [])
        self.assertNotIn("session model", err)
        self.assertNotIn("turn on the session-model fallback", err)

    def test_round_four_never_falls_back(self):
        self.assert_plain("--fix-round", "4")

    def test_escalation_keys_never_fall_back(self):
        self.assert_plain("--escalation-excluded-keys-json", '["lane-b"]', "--fix-round", "2")

    def test_owner_named_pair_never_falls_back(self):
        self.assert_plain(
            "--escalation-excluded-keys-json", "[]", "--no-fallback", "--fix-round", "2",
            lanes=(LANE_A,),
        )

    def test_non_boolean_flag_exits_2(self):
        text = self._scratch_roster([LANE_A], True)
        key = lane_settings.SESSION_FALLBACK_KEY
        self.assertEqual(1, text.count(f"{key} = true"))
        with open(config_io.cfg_global_path(self.env), "w", encoding="utf-8") as handle:
            handle.write(text.replace(f"{key} = true", f'{key} = "yes"'))
        rc, out, err = self.resolve([LANE_A], {"lane-a": OUT})
        self.assertEqual(rc, 2)
        self.assertIn("policy.execute: 'session_fallback' must be a boolean", err)
        self.assertEqual(out, "")

    def test_brief_text_never_reaches_jev(self):
        self._scratch_roster([LANE_A], True)
        rc, _out, _err = self.resolve([LANE_A], {"lane-a": OUT})
        self.assertEqual(rc, 0)
        self.assertEqual(len(self.jev_calls), 1)
        for call in self.jev_calls:
            self.assertNotIn("UNIQUE-BRIEF-MARKER-7", call["input"])
            self.assertEqual(call["cwd"], self.cwd)
            context = json.loads(call["input"])["items"][0]["context"]
            self.assertRegex(
                context,
                re.compile(r"^Task type: [A-Za-z_-]+\. Files named: \d+\. Fix round: \d+\.$"),
            )


SKILL_DIR = (
    pathlib.Path(__file__).resolve().parents[1] / "skills" / "ai-kit-spec-execute-superpowers"
)


def _doc(rel: str) -> str:
    return " ".join((SKILL_DIR / rel).read_text(encoding="utf-8").split())


class TestFallbackDocs(unittest.TestCase):
    def test_owner_stop_names_the_fallback(self):
        raw = (SKILL_DIR / "references" / "resolution-stops.md").read_text(encoding="utf-8")
        text = _doc("references/resolution-stops.md")
        for needle in (
            "Session-model fallback first.",
            '"fallback": "session"',
            "turn on the session-model fallback",
            "is never replaced by the session model",
        ):
            self.assertIn(needle, text)
        self.assertGreater(
            raw.index("Session-model fallback first."), raw.index("## Owner stop")
        )

    def test_step_three_branch_comes_first(self):
        text = _doc("SKILL.md")
        self.assertLess(
            text.index("**Session fallback ("),
            text.index("**Rounds 4–5 capability escalation"),
        )
        for needle in (
            "or when the task's injection carries the session fallback",
            "an exception inside the native branch below, never a second launch path",
            "then dispatches through the native branch below unchanged",
        ):
            self.assertIn(needle, text)

    def test_escalation_and_resume_name_it(self):
        escalation = _doc("references/escalation.md")
        self.assertIn("runs rounds 4 and 5 like session-model mode", escalation)
        self.assertIn("--no-fallback", escalation)
        self.assertIn(
            "goes through Step 3's native branch with its session-fallback exception",
            _doc("references/state-management.md"),
        )

    def test_config_check_names_both_ways(self):
        text = _doc("references/config-check.md")
        self.assertIn("the owner's session-model fallback", text)
        self.assertNotIn("is its only way", text)

    def test_blocks_pass_the_fix_round(self):
        for rel in ("SKILL.md", "references/escalation.md"):
            self.assertIn('--fix-round "${FIX_ROUND:-0}"', _doc(rel))


if __name__ == "__main__":
    unittest.main()
