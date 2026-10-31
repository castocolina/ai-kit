"""Tests for skills/ai-kit-spec-goal-prompt/scripts/gp_host.py (GPS-01, GPS-02, GPS-04).

Every subprocess goes through an injected `HostSeams`, so these tests fake each run. No test
runs a real model, a `decide.py` ladder call, the network, or touches a real home or credential.
Fake results are keyed by argv tuples and never carry an absolute machine path.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import gp_host


class FakeRun:
    """Callable seam: maps an argv tuple to (rc, stdout); unknown argv yields (127, "")."""

    def __init__(self, replies=None):
        self.replies = dict(replies or {})
        self.calls = []

    def __call__(self, argv, timeout, cwd=None):
        key = tuple(argv)
        self.calls.append(key)
        return self.replies.get(key, (127, ""))


def seams(run=None, which=None, environ=None):
    """HostSeams with every binary found under a fake directory, unless `which` says otherwise."""
    return gp_host.HostSeams(
        run=run if run is not None else FakeRun(),
        which=which if which is not None else (lambda name: f"fake-bin/{name}"),
        environ=environ if environ is not None else {},
    )


def matrix_reply(rows, schema=1):
    return json.dumps({"schema_version": schema, "rows": rows})


def _row(host, primitive):
    return {"host": host, "primitive": primitive}


class TestMatrixRead(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.wake = os.path.join(self.tmp.name, "ai-kit-session-wake.py")
        Path(self.wake).write_text("# stand-in for the sibling CLI; never executed\n", "utf-8")
        self.argv = (sys.executable, self.wake, "matrix", "--json")

    def _read(self, rc=0, stdout=""):
        run = FakeRun({self.argv: (rc, stdout)})
        result = gp_host.read_matrix(seams(run), wake_cli=self.wake)
        return result, run

    def test_two_rows_read_as_session_wake(self):
        rows = [_row("claude", "/goal"), _row("pi", "systemd user timer")]
        result, run = self._read(stdout=matrix_reply(rows))
        self.assertEqual(result, (rows, "session-wake"))
        self.assertEqual(run.calls, [self.argv])

    def test_nonzero_exit_gives_fixed_reason(self):
        result, _ = self._read(rc=1, stdout=matrix_reply([]))
        self.assertEqual(result, (None, "exit 1"))

    def test_empty_stdout_is_not_json(self):
        result, _ = self._read(rc=0, stdout="")
        self.assertEqual(result, (None, "not json"))

    def test_bad_json_is_not_json(self):
        result, _ = self._read(rc=0, stdout="{not json")
        self.assertEqual(result, (None, "not json"))

    def test_other_schema_version_is_refused(self):
        result, _ = self._read(rc=0, stdout=matrix_reply([], schema=2))
        self.assertEqual(result, (None, "schema 2"))

    def test_missing_rows_list_is_refused(self):
        result, _ = self._read(rc=0, stdout=json.dumps({"schema_version": 1}))
        self.assertEqual(result, (None, "no rows"))

    def test_missing_cli_never_calls_a_subprocess(self):
        run = FakeRun()
        missing = os.path.join(self.tmp.name, "absent-session-wake.py")
        result = gp_host.read_matrix(seams(run), wake_cli=missing)
        self.assertEqual(result, (None, "cli missing"))
        self.assertEqual(run.calls, [])

    def test_failure_reasons_carry_no_path(self):
        cases = [
            self._read(rc=1, stdout=""),
            self._read(rc=0, stdout="x"),
            self._read(rc=0, stdout=matrix_reply([], schema=2)),
        ]
        for result, _ in cases:
            reason = result[1]
            self.assertIsNone(result[0])
            self.assertNotIn("/", reason)
            self.assertNotIn(self.tmp.name, reason)

    def test_default_sibling_path_resolves_to_the_real_cli(self):
        path = gp_host.sibling_cli("ai-kit-session-wake/ai-kit-session-wake.py")
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(os.path.basename(path), "ai-kit-session-wake.py")

    def test_override_wins_over_the_sibling_default(self):
        self.assertEqual(gp_host.sibling_cli("ignored/x.py", override="given.py"), "given.py")


class TestHostFacts(unittest.TestCase):
    def test_version_parsed_from_claude_banner(self):
        run = FakeRun({("claude", "--version"): (0, "2.1.314 (Claude Code)\n")})
        self.assertEqual(gp_host.host_version(seams(run), "claude"), "2.1.314")

    def test_version_parsed_from_bare_pi_output(self):
        run = FakeRun({("pi", "--version"): (0, "1.3.0\n")})
        self.assertEqual(gp_host.host_version(seams(run), "pi"), "1.3.0")

    def test_version_parsed_after_a_word_prefix(self):
        run = FakeRun({("opencode", "--version"): (0, "opencode v2.0.31\n")})
        self.assertEqual(gp_host.host_version(seams(run), "opencode"), "2.0.31")

    def test_missing_binary_has_no_version_and_no_call(self):
        run = FakeRun()
        self.assertIsNone(gp_host.host_version(seams(run, which=lambda _name: None), "claude"))
        self.assertEqual(run.calls, [])

    def test_output_without_a_version_is_none(self):
        run = FakeRun({("claude", "--version"): (0, "no digits here\n")})
        self.assertIsNone(gp_host.host_version(seams(run), "claude"))

    def test_nonzero_version_exit_is_none(self):
        run = FakeRun({("claude", "--version"): (1, "2.1.314\n")})
        self.assertIsNone(gp_host.host_version(seams(run), "claude"))

    def test_version_ge_compares_numerically(self):
        self.assertTrue(gp_host.version_ge("2.1.314", "2.1.299"))
        self.assertFalse(gp_host.version_ge("2.1.9", "2.1.10"))

    def test_version_ge_refuses_an_unknown_version(self):
        self.assertFalse(gp_host.version_ge(None, "1.0"))
        self.assertTrue(gp_host.version_ge("1.0", None))

    def _spec_cli(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        spec = os.path.join(tmp.name, "ai-kit-spec.py")
        Path(spec).write_text("# stand-in for the sibling CLI; never executed\n", "utf-8")
        return spec

    def test_current_host_parsed_from_detect_current_runtime(self):
        spec = self._spec_cli()
        argv = (sys.executable, spec, "detect-current-runtime")
        run = FakeRun({argv: (0, '{"host": "claude"}')})
        self.assertEqual(gp_host.current_host(seams(run), spec), "claude")

    def test_current_host_failures_are_none(self):
        spec = self._spec_cli()
        argv = (sys.executable, spec, "detect-current-runtime")
        for reply in [(1, '{"host": "claude"}'), (0, "not json"), (0, '{"other": 1}')]:
            with self.subTest(reply=reply):
                self.assertIsNone(gp_host.current_host(seams(FakeRun({argv: reply})), spec))

    def test_current_host_missing_cli_is_none_without_a_call(self):
        run = FakeRun()
        self.assertIsNone(gp_host.current_host(seams(run), "no-such-ai-kit-spec.py"))
        self.assertEqual(run.calls, [])

    def test_help_mentions_a_goal_keyword(self):
        run = FakeRun({("opencode", "--help"): (0, "Usage: opencode run\n  Goal mode\n")})
        self.assertTrue(gp_host.help_mentions(seams(run), "opencode"))

    def test_help_without_a_keyword_is_false(self):
        run = FakeRun({("opencode", "--help"): (0, "Usage: opencode run [message]\n")})
        self.assertFalse(gp_host.help_mentions(seams(run), "opencode"))

    def test_help_with_a_missing_binary_is_none(self):
        run = FakeRun()
        self.assertIsNone(gp_host.help_mentions(seams(run, which=lambda _name: None), "pi"))
        self.assertEqual(run.calls, [])

    def test_real_seams_maps_a_missing_program_to_127(self):
        run = gp_host.real_seams().run
        self.assertEqual(run(["ai-kit-no-such-program-for-tests"], 5, None), (127, ""))

    def test_no_shell_true_in_the_module(self):
        source = (SCRIPTS / "gp_host.py").read_text("utf-8")
        self.assertNotIn("shell=True", source)


ROWS = [
    {
        "host": "claude",
        "primitive": "systemd user timer",
        "kind": "os-timer",
        "surface": "cli",
        "survives_stall": True,
        "survives_process_death": True,
        "survives_reboot": True,
        "source": "verified",
        "evidence": "spike 001",
        "unverified": ["reboot"],
        "version_floor": "2.1.310",
        "rank": 3,
    },
    {
        "host": "claude",
        "primitive": "CronCreate one-shot",
        "kind": "schedule",
        "surface": "tool",
        "survives_stall": True,
        "survives_process_death": False,
        "survives_reboot": False,
        "source": "verified",
        "evidence": "spike 004",
        "unverified": [],
        "version_floor": "2.1.299",
        "rank": 1,
    },
    {
        "host": "claude",
        "primitive": "CronCreate recurring",
        "kind": "schedule",
        "surface": "tool",
        "survives_stall": True,
        "survives_process_death": False,
        "survives_reboot": False,
        "source": "verified",
        "evidence": "spike 004",
        "unverified": [],
        "version_floor": "2.1.299",
        "rank": 1,
    },
    {
        "host": "claude",
        "primitive": "/goal",
        "kind": "goal",
        "surface": "slash-command",
        "survives_stall": False,
        "survives_process_death": False,
        "survives_reboot": False,
        "source": "verified",
        "evidence": "spike 004",
        "unverified": [],
        "version_floor": "2.1.299",
        "rank": 0,
    },
    {
        "host": "claude",
        "primitive": "ScheduleWakeup",
        "kind": "wake",
        "surface": "tool",
        "survives_stall": False,
        "survives_process_death": False,
        "survives_reboot": False,
        "source": "unverified",
        "evidence": "no spike",
        "unverified": ["all"],
        "version_floor": None,
        "rank": 0,
    },
    {
        "host": "claude",
        "primitive": "/loop",
        "kind": "loop",
        "surface": "slash-command",
        "survives_stall": False,
        "survives_process_death": False,
        "survives_reboot": False,
        "source": "unverified",
        "evidence": "no spike",
        "unverified": ["all"],
        "version_floor": None,
        "rank": 0,
    },
    {
        "host": "claude",
        "primitive": "cloud routine",
        "kind": "schedule",
        "surface": "slash-command",
        "survives_stall": False,
        "survives_process_death": False,
        "survives_reboot": False,
        "source": "unverified",
        "evidence": "no spike",
        "unverified": ["all"],
        "version_floor": None,
        "rank": 0,
    },
    {
        "host": "codex",
        "primitive": "systemd user timer",
        "kind": "os-timer",
        "surface": "cli",
        "survives_stall": True,
        "survives_process_death": True,
        "survives_reboot": True,
        "source": "unverified",
        "evidence": "unverified floor",
        "unverified": ["all"],
        "version_floor": "0.162.1",
        "rank": 3,
    },
    {
        "host": "pi",
        "primitive": "systemd user timer",
        "kind": "os-timer",
        "surface": "cli",
        "survives_stall": True,
        "survives_process_death": True,
        "survives_reboot": True,
        "source": "verified",
        "evidence": "spike",
        "unverified": [],
        "version_floor": "1.3.0",
        "rank": 3,
    },
    {
        "host": "opencode",
        "primitive": "systemd user timer",
        "kind": "os-timer",
        "surface": "cli",
        "survives_stall": True,
        "survives_process_death": True,
        "survives_reboot": True,
        "source": "verified",
        "evidence": "spike",
        "unverified": [],
        "version_floor": "2.0.31",
        "rank": 3,
    },
]

EXPECTED_KEYS = {
    "host",
    "primitive",
    "kind",
    "surface",
    "availability",
    "usage_source",
    "survives_stall",
    "survives_process_death",
    "survives_reboot",
    "rank",
    "note",
}


def _prims(
    rows=ROWS,
    *,
    target="claude",
    current="claude",
    version: str | None = "2.1.314",
    tools=(),
    help_seen=None,
):
    seen = gp_host.Seen(frozenset(tools), help_seen)
    return gp_host.build_primitives(
        rows, target=target, current=current, version=version, seen=seen
    )


def _by(prims, name):
    return next(p for p in prims if p["primitive"] == name)


class TestPrimitives(unittest.TestCase):
    def test_goal_is_available_at_or_above_its_floor_with_official_docs(self):
        goal = _by(_prims(), "/goal")
        self.assertEqual(goal["availability"], "available")
        self.assertEqual(goal["usage_source"], "official docs")

    def test_a_seen_tool_name_is_available(self):
        one_shot = _by(_prims(tools={"CronCreate"}), "CronCreate one-shot")
        self.assertEqual(one_shot["availability"], "available")

    def test_an_unseen_tool_is_not_seen_and_never_absent(self):
        prims = _prims(tools={"CronCreate"})
        self.assertEqual(_by(prims, "ScheduleWakeup")["availability"], "not seen")
        self.assertNotIn("absent", {p["availability"] for p in prims})

    def test_loop_without_a_floor_stays_unverified_even_on_a_new_version(self):
        self.assertEqual(_by(_prims(), "/loop")["availability"], "unverified")

    def test_version_below_the_floor_keeps_goal_unverified(self):
        self.assertEqual(_by(_prims(version="2.1.200"), "/goal")["availability"], "unverified")

    def test_unknown_current_version_keeps_goal_unverified(self):
        self.assertEqual(_by(_prims(version=None), "/goal")["availability"], "unverified")

    def test_non_current_host_rows_are_all_unverified_including_the_codex_goal(self):
        prims = _prims(target="codex", current="claude")
        self.assertTrue(prims)
        self.assertEqual({p["availability"] for p in prims}, {"unverified"})
        goal = _by(prims, "/goal")
        self.assertEqual(goal["usage_source"], "binary strings")
        self.assertIn("/goal [<objective>|clear|edit|pause|resume]", goal["note"])
        self.assertIn("unverified", goal["note"])

    def test_opencode_help_without_a_keyword_is_absent_on_the_none_row(self):
        prims = _prims(
            ROWS, target="opencode", current="opencode", version="2.0.31", help_seen=False
        )
        self.assertEqual({p["kind"] for p in prims}, {"os-timer", "none"})
        none = _by(prims, "none")
        self.assertEqual(none["availability"], "absent")
        self.assertEqual(none["note"], "no native goal or loop primitive found in --help")

    def test_opencode_help_true_or_unknown_keeps_the_none_row_unverified(self):
        for help_seen in (True, None):
            with self.subTest(help_seen=help_seen):
                prims = _prims(
                    target="opencode", current="opencode", version="2.0.31", help_seen=help_seen
                )
                self.assertEqual(_by(prims, "none")["availability"], "unverified")

    def test_cursor_has_only_the_none_row(self):
        prims = _prims(target="cursor", current="cursor", version="1.0.0", help_seen=False)
        self.assertEqual([p["kind"] for p in prims], ["none"])
        self.assertEqual(prims[0]["availability"], "absent")

    def test_cursor_as_non_current_host_is_unverified(self):
        prims = _prims(target="cursor", current="claude", help_seen=False)
        self.assertEqual([p["availability"] for p in prims], ["unverified"])

    def test_two_labels_are_computed_independently(self):
        timer = _by(_prims(), "systemd user timer")
        self.assertEqual((timer["availability"], timer["usage_source"]), ("available", "live"))
        goal = _by(_prims(), "/goal")
        self.assertEqual(
            (goal["availability"], goal["usage_source"]), ("available", "official docs")
        )

    def test_non_current_verified_row_keeps_live_usage_but_unverified_availability(self):
        timer = _by(_prims(target="pi", current="claude"), "systemd user timer")
        self.assertEqual((timer["availability"], timer["usage_source"]), ("unverified", "live"))

    def test_every_primitive_has_exactly_the_contract_keys(self):
        for prim in _prims(help_seen=False):
            self.assertEqual(set(prim), EXPECTED_KEYS)

    def test_a_missing_matrix_builds_only_the_extra_and_none_rows(self):
        prims = gp_host.build_primitives(
            None, target="codex", current=None, version=None, seen=gp_host.Seen(frozenset(), None)
        )
        self.assertEqual([p["primitive"] for p in prims], ["/goal"])
        self.assertEqual({p["availability"] for p in prims}, {"unverified"})

    def test_degraded_primitives_carry_the_matrix_reason_and_stay_unverified(self):
        prims = gp_host.degraded_primitives("exit 1", "claude")
        self.assertTrue(prims)
        self.assertEqual({p["availability"] for p in prims}, {"unverified"})
        for prim in prims:
            self.assertTrue(prim["note"].startswith("matrix missing: exit 1"))

    def test_unrecognized_tool_names_are_listed_never_matched_loosely(self):
        names = ["CronCreate", "Bogus", "Monitor", "bogus"]
        self.assertEqual(gp_host.unrecognized_tools(names, ROWS), ["Bogus", "bogus"])


READY_CONFIG = {
    "workflow": {
        "cross_ai_execution": True,
        "cross_ai_command": "node .planning/scripts/cross-ai.mjs",
        "plan_review_convergence": True,
    },
    "review": {"default_reviewers": ["pi", "opencode"]},
}
PRINT_ARGV_OK = (
    "cross-ai: resolved runner\n"
    'pi\tfake-bin/pi\t["pi","--print"]\n'
    'opencode\tfake-bin/opencode\t["opencode"]\n'
)
DETECT_OK = json.dumps(
    {"schema_version": 7, "clis": {"pi": {"installed": True}, "opencode": {"installed": True}}}
)


def _which(name):
    return "fake-bin/node" if name == "node" else None


class ReadinessBase(unittest.TestCase):
    """A temporary repo with a stand-in runner script and a stand-in sibling CLI."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(os.path.join(self.repo, ".planning", "scripts"))
        self.script = os.path.join(self.repo, ".planning", "scripts", "cross-ai.mjs")
        Path(self.script).write_text("// stand-in runner; never executed\n", "utf-8")
        self.spec = os.path.join(self.tmp.name, "ai-kit-spec.py")
        Path(self.spec).write_text("# stand-in sibling CLI; never executed\n", "utf-8")
        self.write_config(READY_CONFIG)

    def write_config(self, config=None, raw=None):
        path = os.path.join(self.repo, ".planning", "config.json")
        if raw is not None:
            Path(path).write_text(raw, "utf-8")
        elif config is not None:
            Path(path).write_text(json.dumps(config), "utf-8")

    def fake_run(self, print_argv=(0, PRINT_ARGV_OK), detect=(0, DETECT_OK)):
        return FakeRun(
            {
                ("node", ".planning/scripts/cross-ai.mjs", "--print-argv"): print_argv,
                (sys.executable, self.spec, "detect-runtimes"): detect,
            }
        )

    def readiness(self, run=None, native=False):
        run = run if run is not None else self.fake_run()
        seam = seams(run, which=_which)
        return gp_host.cross_ai_readiness(seam, self.repo, native=native, spec_cli=self.spec), run


class TestReadiness(ReadinessBase):
    def test_ready_setup_proves_runner_listing_and_reviewers(self):
        result, _ = self.readiness()
        self.assertTrue(result["runner_ok"])
        self.assertTrue(result["cli_listed"])
        self.assertTrue(result["reviewers_ok"])
        self.assertEqual(result["clis"], ["pi", "opencode"])
        self.assertEqual(result["label"], "installed, not quota- or auth-verified")
        self.assertEqual(result["problems"], [])
        self.assertTrue(result["ready_for_cross_ai"])

    def test_ready_result_carries_no_path_from_the_probe_output(self):
        result, _ = self.readiness()
        serialized = json.dumps(result)
        self.assertNotIn("fake-bin", serialized)
        self.assertNotIn(self.tmp.name, serialized)
        self.assertNotIn(self.repo, serialized)

    def test_execution_flag_off_is_named(self):
        config = json.loads(json.dumps(READY_CONFIG))
        config["workflow"]["cross_ai_execution"] = False
        self.write_config(config)
        result, run = self.readiness()
        self.assertFalse(result["runner_ok"])
        self.assertIn("cross_ai_execution off", result["problems"])
        self.assertFalse(result["ready_for_cross_ai"])
        self.assertEqual(run.calls, [(sys.executable, self.spec, "detect-runtimes")])

    def test_unset_command_is_named(self):
        config = json.loads(json.dumps(READY_CONFIG))
        del config["workflow"]["cross_ai_command"]
        self.write_config(config)
        result, _ = self.readiness()
        self.assertIn("no cross_ai_command", result["problems"])
        self.assertFalse(result["runner_ok"])

    def test_missing_script_is_named(self):
        os.remove(self.script)
        result, _ = self.readiness()
        self.assertIn("script missing", result["problems"])
        self.assertFalse(result["runner_ok"])

    def test_missing_executable_is_named(self):
        run = self.fake_run()
        seam = seams(run, which=lambda name: None)
        result = gp_host.cross_ai_readiness(seam, self.repo, native=False, spec_cli=self.spec)
        self.assertIn("executable missing", result["problems"])
        self.assertNotIn(("node", ".planning/scripts/cross-ai.mjs", "--print-argv"), run.calls)

    def test_print_argv_exit_127_means_no_cli_listed(self):
        result, _ = self.readiness(self.fake_run(print_argv=(127, "")))
        self.assertTrue(result["runner_ok"])
        self.assertFalse(result["cli_listed"])
        self.assertIn("no external CLI listed", result["problems"])
        self.assertFalse(result["ready_for_cross_ai"])

    def test_print_argv_without_cli_lines_means_no_cli_listed(self):
        result, _ = self.readiness(self.fake_run(print_argv=(0, "cross-ai: nothing here\n")))
        self.assertFalse(result["cli_listed"])
        self.assertEqual(result["clis"], [])

    def test_foreign_runner_is_usability_unverified_and_never_probed(self):
        other = os.path.join(self.repo, ".planning", "scripts", "other-runner.mjs")
        Path(other).write_text("// stand-in\n", "utf-8")
        config = json.loads(json.dumps(READY_CONFIG))
        config["workflow"]["cross_ai_command"] = "node .planning/scripts/other-runner.mjs"
        self.write_config(config)
        result, run = self.readiness()
        self.assertIsNone(result["cli_listed"])
        self.assertEqual(result["label"], "usability unverified")
        self.assertTrue(result["runner_ok"])
        self.assertTrue(all("--print-argv" not in call for call in run.calls))

    def test_runner_command_with_a_foreign_launcher_is_never_executed(self):
        for command in (
            'sh -c "touch PWNED" cross-ai.mjs',
            "node -e x .planning/scripts/cross-ai.mjs",
            "node .planning/scripts/cross-ai.mjs --cli x",
        ):
            with self.subTest(command=command):
                config = json.loads(json.dumps(READY_CONFIG))
                config["workflow"]["cross_ai_command"] = command
                self.write_config(config)
                _result, run = self.readiness()
                self.assertTrue(all("--print-argv" not in call for call in run.calls))

    def test_runner_script_resolving_outside_the_repo_is_never_executed(self):
        outside = os.path.join(self.tmp.name, "elsewhere", "cross-ai.mjs")
        os.makedirs(os.path.dirname(outside))
        Path(outside).write_text("// stand-in\n", "utf-8")
        os.remove(self.script)
        os.symlink(outside, self.script)
        _result, run = self.readiness()
        self.assertTrue(all("--print-argv" not in call for call in run.calls))
        config = json.loads(json.dumps(READY_CONFIG))
        config["workflow"]["cross_ai_command"] = f"node {outside}"
        self.write_config(config)
        _result, run = self.readiness()
        self.assertTrue(all("--print-argv" not in call for call in run.calls))

    def test_reviewers_need_plan_review_convergence(self):
        config = json.loads(json.dumps(READY_CONFIG))
        config["workflow"]["plan_review_convergence"] = False
        self.write_config(config)
        result, _ = self.readiness()
        self.assertFalse(result["reviewers_ok"])
        self.assertIn("plan_review_convergence off", result["problems"])

    def test_uninstalled_reviewer_cli_is_named(self):
        detect = json.dumps({"clis": {"pi": {"installed": True}, "opencode": {"installed": False}}})
        result, _ = self.readiness(self.fake_run(detect=(0, detect)))
        self.assertFalse(result["reviewers_ok"])
        self.assertTrue(any("opencode" in problem for problem in result["problems"]))

    def test_reviewer_instance_maps_to_its_cli(self):
        config = json.loads(json.dumps(READY_CONFIG))
        config["review"] = {
            "default_reviewers": ["zed"],
            "reviewer_instances": {"zed": {"cli": "pi"}},
        }
        self.write_config(config)
        result, run = self.readiness()
        self.assertTrue(result["reviewers_ok"])
        self.assertIn((sys.executable, self.spec, "detect-runtimes"), run.calls)

    def test_detect_runtimes_failure_is_reviewers_not_ok(self):
        result, _ = self.readiness(self.fake_run(detect=(1, "")))
        self.assertFalse(result["reviewers_ok"])
        self.assertIn("detect-runtimes failed", result["problems"])

    def test_native_choice_keeps_the_facts_and_adds_the_flag(self):
        config = json.loads(json.dumps(READY_CONFIG))
        config["workflow"]["cross_ai_execution"] = False
        self.write_config(config)
        result, _ = self.readiness(native=True)
        self.assertIs(result["native"], True)
        self.assertFalse(result["runner_ok"])
        self.assertFalse(result["ready_for_cross_ai"])
        self.assertIn("cross_ai_execution off", result["problems"])
        self.assertFalse(any("native" in problem for problem in result["problems"]))

    def test_no_native_key_when_native_is_not_chosen(self):
        result, _ = self.readiness(native=False)
        self.assertNotIn("native", result)

    def test_missing_config_reads_as_no_config(self):
        os.remove(os.path.join(self.repo, ".planning", "config.json"))
        result, _ = self.readiness()
        self.assertFalse(result["runner_ok"])
        self.assertIn("no cross_ai_command", result["problems"])

    def test_invalid_config_reads_as_no_config(self):
        self.write_config(raw="{not json")
        result, _ = self.readiness()
        self.assertFalse(result["runner_ok"])
        self.assertFalse(result["ready_for_cross_ai"])

    def test_symlinked_config_reads_as_no_config(self):
        path = os.path.join(self.repo, ".planning", "config.json")
        outside = os.path.join(self.tmp.name, "outside.json")
        os.replace(path, outside)
        os.symlink(outside, path)
        result, run = self.readiness()
        self.assertFalse(result["runner_ok"])
        self.assertIn("no cross_ai_command", result["problems"])
        self.assertTrue(all("--print-argv" not in call for call in run.calls))

    def test_config_is_read_only_up_to_one_mebibyte(self):
        config = json.loads(json.dumps(READY_CONFIG))
        config["pad"] = "x" * (1 << 20)
        self.write_config(config)
        result, _ = self.readiness()
        self.assertFalse(result["runner_ok"])
        self.assertIn("no cross_ai_command", result["problems"])


class TestJev(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.decide = os.path.join(self.tmp.name, "decide.py")
        Path(self.decide).write_text("# stand-in client; never executed\n", "utf-8")
        self.argv = (sys.executable, self.decide, "detect")

    def _status(self, reply):
        run = FakeRun({self.argv: reply})
        return gp_host.jev_status(seams(run), decide_cli=self.decide), run

    def test_local_usable_backend_is_usable(self):
        detect = {
            "backends": {
                "laya": {"usable": True, "remote": False},
                "typesafe": {"usable": False, "remote": True},
            }
        }
        status, _ = self._status((0, json.dumps(detect)))
        self.assertEqual(status, {"usable": True, "reason": "local backend usable"})

    def test_only_a_remote_usable_backend_counts_as_consented(self):
        detect = {
            "backends": {
                "laya": {"usable": False, "remote": False},
                "typesafe": {"usable": True, "remote": True},
            }
        }
        status, _ = self._status((0, json.dumps(detect)))
        self.assertEqual(status, {"usable": True, "reason": "consented remote backend"})

    def test_no_usable_backend_is_not_usable(self):
        detect = {"backends": {"laya": {"usable": False, "remote": False}}}
        status, _ = self._status((0, json.dumps(detect)))
        self.assertEqual(status, {"usable": False, "reason": "no usable backend"})

    def test_detect_exit_failure_is_fixed_reason(self):
        status, _ = self._status((1, ""))
        self.assertEqual(status, {"usable": False, "reason": "detect failed"})

    def test_detect_bad_json_is_fixed_reason(self):
        status, _ = self._status((0, "not json"))
        self.assertEqual(status, {"usable": False, "reason": "detect output not json"})

    def test_missing_client_never_calls_a_subprocess(self):
        run = FakeRun()
        status = gp_host.jev_status(seams(run), decide_cli="no-such-decide.py")
        self.assertEqual(status, {"usable": False, "reason": "decide.py missing"})
        self.assertEqual(run.calls, [])

    def test_jev_never_calls_the_ladder(self):
        detect = {"backends": {"laya": {"usable": True, "remote": False}}}
        _, run = self._status((0, json.dumps(detect)))
        self.assertEqual(run.calls, [self.argv])
        for call in run.calls:
            self.assertNotIn("ladder", call)

    def test_module_source_never_names_the_ladder_or_a_shell(self):
        source = (SCRIPTS / "gp_host.py").read_text("utf-8")
        self.assertNotIn("ladder", source)
        self.assertNotIn("shell=True", source)


class TestProbeEnvironment(unittest.TestCase):
    def test_probe_child_loses_credential_named_variables_only(self):
        code = "import json, os; print(json.dumps(sorted(os.environ)))"
        env = {"AIKIT_SECRET_SENTINEL": "x", "SOME_API_KEY": "x", "AIKIT_PLAIN": "x"}
        with mock.patch.dict(os.environ, env, clear=False):
            rc, out = gp_host._run([sys.executable, "-c", code], 20, None)
        self.assertEqual(rc, 0)
        names = json.loads(out)
        self.assertNotIn("AIKIT_SECRET_SENTINEL", names)
        self.assertNotIn("SOME_API_KEY", names)
        self.assertIn("AIKIT_PLAIN", names)
        self.assertIn("PATH", names)


if __name__ == "__main__":
    unittest.main()
