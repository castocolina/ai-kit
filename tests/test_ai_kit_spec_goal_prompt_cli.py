"""Tests for skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py: the `detect` and `render`
subcommands (GPS-01, GPS-02; D-04, D-05).

Every host probe goes through an injected seam. `FakeRun` answers by the exact trailing argv
elements and records each call. Nothing prompts (`input` is patched to raise), nothing touches a
real home or runs a model, and every write lands in a temporary repository.
"""

import contextlib
import io
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
import goal_prompt
import gp_host

from tests import goal_prompt_fixtures as fx

TODAY = "2026-01-02"
WAKE_REL = "ai-kit-session-wake/ai-kit-session-wake.py"
SPEC_REL = "ai-kit-spec-review/ai-kit-spec.py"
JEV_REL = "jev-fast-decision/scripts/jev_review.py"
AVAILABILITY = {"available", "not seen", "unverified", "absent"}
USAGE_SOURCES = {"official docs", "live", "third-party", "binary strings", "unverified"}
PHASES = [
    fx.phase_spec("16", "Foundation", plans=2, cross_ai=2, verification=True),
    fx.phase_spec("16.1", "Hotfix", plans=1),
    fx.phase_spec("17", "Surfaces", spec=False, plans=2),
]
MATRIX_ROWS = [
    {
        "host": "claude", "primitive": "/goal", "kind": "goal", "surface": "slash-command",
        "survives_stall": False, "survives_process_death": False, "survives_reboot": False,
        "rank": 0, "source": "verified", "version_floor": "2.1.299", "evidence": "fixture",
    },
    {
        "host": "claude", "primitive": "CronCreate recurring", "kind": "schedule",
        "surface": "tool", "survives_stall": True, "survives_process_death": False,
        "survives_reboot": False, "rank": 1, "source": "verified", "version_floor": "2.1.299",
        "evidence": "fixture",
    },
    {
        "host": "claude", "primitive": "systemd user timer", "kind": "os-timer",
        "surface": "cli", "survives_stall": True, "survives_process_death": True,
        "survives_reboot": True, "rank": 3, "source": "verified", "version_floor": "2.1.310",
        "evidence": "fixture",
    },
    {
        "host": "claude", "primitive": "/loop", "kind": "loop", "surface": "slash-command",
        "survives_stall": False, "survives_process_death": False, "survives_reboot": False,
        "rank": 0, "source": "unverified", "version_floor": None, "evidence": "fixture",
    },
]


class FakeRun:
    """Stands in for HostSeams.run: answers by exact trailing argv elements, records calls."""

    def __init__(self, routes=()):
        self.routes = list(routes)
        self.calls = []
        self.options = []  # (timeout, cwd) per call, so the seam's arguments stay observable

    def __call__(self, argv, timeout, cwd=None):
        self.calls.append(list(argv))
        self.options.append((timeout, cwd))
        for suffix, rc, out in self.routes:
            if tuple(argv[-len(suffix):]) == tuple(suffix):
                return rc, out
        return 127, ""

    def queries(self):
        return [argv for argv in self.calls if "query" in argv]


def host_routes(rows=MATRIX_ROWS, current="claude"):
    return [
        (("matrix", "--json"), 0, json.dumps({"schema_version": 1, "rows": rows})),
        (("detect-current-runtime",), 0, json.dumps({"host": current})),
        (("--version",), 0, f"{current} 2.1.314 (fixture)"),
        (("--help",), 0, "usage: fixture /goal /loop"),
        (("detect-runtimes",), 0, json.dumps({"clis": {}})),
        (("detect",), 0, json.dumps({"backends": {}})),
    ]


def cli_seams(run, skills_dir, *, home=fx.FAKE_HOME):
    host = gp_host.HostSeams(run=run, which=lambda name: f"fake-bin/{name}", environ={})
    return goal_prompt.CliSeams(
        host=host, today=TODAY, home=home, secrets=(), skills_dir=skills_dir
    )


def answers(**overrides):
    base = {
        "work_set": {"kind": "phases", "numbers": ["16", "16.1", "17"]},
        "target_host": "claude",
        "native_execution": False,
        "mockups": [],
        "strategy": None,
        "objective": "Finish the foundation phases",
        "output_dir": None,
    }
    base.update(overrides)
    return base


class TestCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        fx.git_init(self.repo)
        self.skills = self.root / "skills"
        for rel in (WAKE_REL, SPEC_REL, JEV_REL):
            fx.write(self.skills, rel, "# stand-in sibling CLI; never executed\n")
        self.host_run = FakeRun(host_routes())
        self.seams = cli_seams(self.host_run, str(self.skills))
        prompt = mock.patch("builtins.input", side_effect=AssertionError("must never prompt"))
        prompt.start()
        self.addCleanup(prompt.stop)

    def call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = goal_prompt.main(list(argv), self.seams)
        return code, out.getvalue(), err.getvalue()

    def detect(self, *extra):
        code, out, err = self.call("detect", "--repo", str(self.repo), *extra)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def captures(self, phases=PHASES, opengsd=True):
        """Write the captured JSON outside the repo; return the flags that name the files."""
        base = self.root / "captures"
        fx.write(base, "roadmap.json", json.dumps(fx.roadmap_json(phases)))
        fx.write(base, "identity.json", json.dumps(fx.identity_json(opengsd)))
        for number, doc in fx.phase_op_json(self.repo, phases).items():
            fx.write(base / "ops", f"{number}.json", json.dumps(doc))
        return [
            "--roadmap", str(base / "roadmap.json"),
            "--identity", str(base / "identity.json"),
            "--phase-op", str(base / "ops"),
        ]

    def write_json(self, name, document):
        path = self.root / name
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def render(self, detect_doc, answers_doc, *extra):
        detect_path = self.write_json("detect.json", detect_doc)
        answers_path = self.write_json("answers.json", answers_doc)
        return self.call(
            "render", "--repo", str(self.repo), "--detect", str(detect_path),
            "--answers", str(answers_path), *extra,
        )

    # ─── detect: scope kinds ──────────────────────────────────────────────────

    def test_opengsd_mixed_phases_detect_as_opengsd(self):
        fx.opengsd_project(self.repo, PHASES)
        result = self.detect(*self.captures())
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["scope"]["kind"], "opengsd")
        self.assertEqual(result["scope"]["identity"], "opengsd")
        self.assertEqual([p["number"] for p in result["scope"]["phases"]], ["16", "16.1", "17"])

    def test_original_gsd_detects_as_gsd_unproven(self):
        fx.opengsd_project(self.repo, PHASES)
        result = self.detect(*self.captures(opengsd=False))
        self.assertEqual(result["scope"]["kind"], "gsd-unproven")
        self.assertEqual(result["scope"]["identity"], "unverified")

    def test_superpowers_plans_only_detect_as_superpowers_in_dependency_order(self):
        fx.superpowers_project(
            self.repo,
            {"a.md": fx.plan_text("Plan A"), "b.md": fx.plan_text("Plan B", depends_on="a.md")},
        )
        result = self.detect()
        self.assertEqual(result["scope"]["kind"], "superpowers")
        self.assertEqual([p["file"] for p in result["scope"]["plans"]], ["a.md", "b.md"])
        self.assertEqual(result["scope"]["order"], ["a.md", "b.md"])

    def test_a_plan_cycle_is_named_and_does_not_block_an_unrelated_selection(self):
        fx.superpowers_project(
            self.repo,
            {
                "a.md": fx.plan_text("Plan A", depends_on="`b.md`"),
                "b.md": fx.plan_text("Plan B", depends_on="`a.md`"),
                "c.md": fx.plan_text("Plan C"),
            },
        )
        code, _out, err = self.call("detect", "--repo", str(self.repo))
        self.assertEqual(code, 2)
        self.assertIn("dependency cycle", json.loads(err)["error"])
        self.assertNotIn("roadmap", json.loads(err)["error"])
        result = self.detect("--work-set", "plans:c.md")
        self.assertEqual(result["scope"]["order"], ["c.md"])

    def test_neither_framework_detects_none_and_asks_for_free_text(self):
        result = self.detect()
        self.assertEqual(result["scope"]["kind"], "none")
        self.assertIsNotNone(result["scope"]["ask"])
        self.assertEqual(result["strategies"], [])

    def test_planning_plus_plans_without_a_work_set_asks_both(self):
        fx.opengsd_project(self.repo, PHASES)
        fx.superpowers_project(self.repo, {"a.md": fx.plan_text("Plan A")})
        result = self.detect(*self.captures())
        self.assertEqual(result["scope"]["kind"], "both")
        self.assertIsNotNone(result["scope"]["ask"])
        self.assertEqual(result["strategies"], [])

    def test_planning_plus_plans_without_a_work_set_or_captures_still_asks_both(self):
        # A missing roadmap is fatal only for a phases work set (contract: exit 2 then).
        fx.opengsd_project(self.repo, PHASES)
        fx.superpowers_project(self.repo, {"a.md": fx.plan_text("Plan A")})
        result = self.detect()
        self.assertEqual(result["scope"]["kind"], "both")
        self.assertIsNotNone(result["scope"]["ask"])
        self.assertEqual(result["strategies"], [])

    # ─── detect: host labels and strategies ──────────────────────────────────

    def test_primitives_carry_availability_and_usage_labels(self):
        result = self.detect()
        self.assertEqual(result["host"]["current"], "claude")
        self.assertEqual(result["host"]["target"], "claude")
        self.assertTrue(result["primitives"])
        for prim in result["primitives"]:
            self.assertIn(prim["availability"], AVAILABILITY)
            self.assertIn(prim["usage_source"], USAGE_SOURCES)
        goal = [p for p in result["primitives"] if p["primitive"] == "/goal"]
        self.assertEqual({p["availability"] for p in goal}, {"available"})

    def test_non_current_target_makes_every_primitive_unverified(self):
        result = self.detect("--target-host", "codex")
        self.assertEqual(result["host"]["target"], "codex")
        self.assertTrue(result["primitives"])
        self.assertEqual({p["availability"] for p in result["primitives"]}, {"unverified"})

    def test_strategies_hold_one_to_three_entries_with_one_recommended(self):
        fx.opengsd_project(self.repo, PHASES)
        strategies = self.detect(*self.captures())["strategies"]
        self.assertTrue(1 <= len(strategies) <= 3)
        self.assertEqual(sum(1 for s in strategies if s["recommended"]), 1)

    def test_derived_and_e2e_fields_are_present(self):
        result = self.detect()
        self.assertEqual(set(result["derived"]), {"must_outlive", "provable"})
        self.assertIsInstance(result["e2e"]["commands"], list)
        self.assertIs(result["e2e"]["none"], True)

    def test_wake_and_runner_fields_are_present(self):
        fx.opengsd_project(self.repo, PHASES)
        result = self.detect(*self.captures())
        self.assertEqual(set(result["wake"]), {"primitive", "label"})
        self.assertEqual(result["wake"]["primitive"], "systemd user timer")
        self.assertEqual(result["runner"]["command"], "node .planning/scripts/cross-ai.mjs")
        self.assertIn("label", result["runner"])

    def test_symlinked_config_is_not_read(self):
        fx.opengsd_project(self.repo, PHASES)
        outside = self.root / "outside.json"
        outside.write_text(
            json.dumps({"workflow": {"cross_ai_command": "node elsewhere/cross-ai.mjs"}}),
            encoding="utf-8",
        )
        config = self.repo / ".planning" / "config.json"
        config.unlink(missing_ok=True)
        config.symlink_to(outside)
        result = self.detect(*self.captures())
        self.assertEqual(result["runner"]["command"], "")

    def test_config_is_read_only_up_to_one_mebibyte(self):
        fx.opengsd_project(self.repo, PHASES)
        document = {"workflow": {"cross_ai_command": "node elsewhere/cross-ai.mjs"}}
        config = self.repo / ".planning" / "config.json"
        config.write_text(json.dumps(document), encoding="utf-8")
        self.assertEqual(self.detect(*self.captures())["runner"]["command"],
                         "node elsewhere/cross-ai.mjs")
        config.write_text(json.dumps({**document, "pad": "x" * (1 << 20)}), encoding="utf-8")
        self.assertEqual(self.detect(*self.captures())["runner"]["command"], "")

    def test_candidate_skills_are_the_sibling_directories_present(self):
        siblings = self.root / "siblings"
        (siblings / "ai-kit-cross-ai").mkdir(parents=True)
        (siblings / "ai-kit-session-wake").mkdir(parents=True)
        self.seams = cli_seams(self.host_run, str(siblings))
        result = self.detect()
        self.assertEqual(result["candidate_skills"], ["ai-kit-cross-ai", "ai-kit-session-wake"])

    def test_empty_skills_dir_gives_no_candidate_skills(self):
        empty = self.root / "empty-siblings"
        empty.mkdir()
        self.seams = cli_seams(self.host_run, str(empty))
        self.assertEqual(self.detect()["candidate_skills"], [])

    def test_unknown_tool_names_are_reported(self):
        result = self.detect("--tools", "CronCreate,Bogus")
        self.assertEqual(result["unrecognized_tools"], ["Bogus"])

    def test_jev_absent_from_every_skills_dir_is_named_and_detect_still_writes(self):
        empty = self.root / "no-jev-skills"
        empty.mkdir()
        self.seams = cli_seams(self.host_run, str(empty))
        # The lookup also searches HOME-based dirs, so a scratch HOME keeps this deterministic.
        with mock.patch.dict(os.environ, {"HOME": str(self.root / "no-home")}):
            result = self.detect()
        self.assertEqual(
            result["jev"], {"usable": False, "reason": "jev-fast-decision not installed"}
        )

    def test_detect_takes_jev_client_and_rejects_the_old_flag(self):
        parser = goal_prompt.build_parser()
        self.assertEqual(parser.parse_args(["detect", "--jev-client", "x.py"]).jev_client, "x.py")
        with self.assertRaises(goal_prompt.UsageError):
            parser.parse_args(["detect", "--decide-cli", "x.py"])

    def test_jev_client_naming_a_file_is_probed_before_the_lookup(self):
        override = self.root / "override" / "jev_review.py"
        fx.write(self.root / "override", "jev_review.py", "# stand-in; never executed\n")
        route = ((str(override), "detect"), 0, json.dumps({"backends": {}}))
        self.host_run.routes.insert(0, route)
        code, _out, err = self.call(
            "detect", "--repo", str(self.repo), "--jev-client", str(override)
        )
        self.assertEqual(code, 0, err)
        self.assertIn([sys.executable, str(override), "detect"], self.host_run.calls)

    # ─── detect: work sets ───────────────────────────────────────────────────

    def test_phase_range_selects_exactly_the_roadmap_phases_in_range(self):
        fx.opengsd_project(self.repo, PHASES)
        result = self.detect(*self.captures([*PHASES, fx.phase_spec("18", "Later")]),
                             "--work-set", "phases:16-17")
        self.assertEqual([p["number"] for p in result["scope"]["phases"]], ["16", "16.1", "17"])

    def test_phase_list_form_selects_the_listed_phases(self):
        fx.opengsd_project(self.repo, PHASES)
        result = self.detect(*self.captures(), "--work-set", "phases:16,17")
        self.assertEqual([p["number"] for p in result["scope"]["phases"]], ["16", "17"])

    def test_malformed_phase_ranges_exit_two_with_a_json_error(self):
        fx.opengsd_project(self.repo, PHASES)
        for value in ("phases:16-", "phases:x-9", "phases:", "phases:16-17-18"):
            with self.subTest(value=value):
                code, out, err = self.call(
                    "detect", "--repo", str(self.repo), "--work-set", value, *self.captures()
                )
                self.assertEqual(code, 2)
                self.assertIn("error", json.loads(err))
                self.assertEqual(out, "")

    def test_free_and_plans_work_sets_need_no_capture_and_make_no_gsd_call(self):
        fx.write(self.repo, ".planning/PROJECT.md", "# Fixture\n")
        fx.superpowers_project(self.repo, {"a.md": fx.plan_text("Plan A")})
        free = self.detect("--work-set", "free:tidy the parser")
        plans = self.detect("--work-set", "plans:a.md")
        self.assertEqual(free["scope"]["kind"], "none")
        self.assertEqual(plans["scope"]["kind"], "superpowers")
        self.assertEqual(self.host_run.queries(), [])

    def test_plans_work_set_restricts_the_plans_and_their_order(self):
        fx.superpowers_project(
            self.repo,
            {"a.md": fx.plan_text("Plan A"), "b.md": fx.plan_text("Plan B"),
             "c.md": fx.plan_text("Plan C")},
        )
        result = self.detect("--work-set", "plans:a.md,c.md")
        self.assertEqual([p["file"] for p in result["scope"]["plans"]], ["a.md", "c.md"])
        self.assertEqual(result["scope"]["order"], ["a.md", "c.md"])

    def test_unknown_plan_in_work_set_exits_two_without_echoing_it(self):
        fx.superpowers_project(self.repo, {"a.md": fx.plan_text("Plan A")})
        code, _out, err = self.call(
            "detect", "--repo", str(self.repo), "--work-set", "plans:zzz-missing.md"
        )
        self.assertEqual(code, 2)
        self.assertIn("error", json.loads(err))
        self.assertNotIn("zzz-missing", err)

    # ─── detect: captures ────────────────────────────────────────────────────

    def test_captured_files_never_run_a_gsd_query(self):
        fx.opengsd_project(self.repo, PHASES)
        self.detect(*self.captures())
        self.assertEqual(self.host_run.queries(), [])

    def test_gsd_cmd_runs_only_the_three_read_only_queries_as_list_argv(self):
        fx.opengsd_project(self.repo, PHASES)
        self.host_run.routes += [
            (("query", "roadmap.analyze"), 0, json.dumps(fx.roadmap_json(PHASES))),
            (("query", "runtime-identity"), 0, json.dumps(fx.identity_json(True))),
        ]
        ops = fx.phase_op_json(self.repo, PHASES)
        self.host_run.routes += [
            (("query", "init.phase-op", number), 0, json.dumps(doc))
            for number, doc in ops.items()
        ]
        result = self.detect("--gsd-cmd", "node tools/gsd-tools.cjs", "--work-set", "phases:16-17")
        self.assertEqual([p["number"] for p in result["scope"]["phases"]], ["16", "16.1", "17"])
        queries = self.host_run.queries()
        self.assertTrue(queries)
        for argv in queries:
            self.assertEqual(argv[:2], ["node", "tools/gsd-tools.cjs"])
            self.assertEqual(argv[2], "query")
        self.assertEqual({argv[3] for argv in queries},
                         {"roadmap.analyze", "runtime-identity", "init.phase-op"})
        self.assertEqual({argv[4] for argv in queries if argv[3] == "init.phase-op"},
                         {"16", "16.1", "17"})

    def test_planning_work_set_without_captures_exits_two_naming_the_flags(self):
        fx.opengsd_project(self.repo, PHASES)
        code, out, err = self.call(
            "detect", "--repo", str(self.repo), "--work-set", "phases:16,17"
        )
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        message = json.loads(err)["error"]
        self.assertIn("--roadmap", message)
        self.assertIn("--gsd-cmd", message)

    def test_detect_output_never_holds_the_temp_root_or_the_home(self):
        fx.opengsd_project(self.repo, PHASES)
        code, out, err = self.call("detect", "--repo", str(self.repo), *self.captures())
        self.assertEqual(code, 0, err)
        self.assertNotIn(str(self.root), out)
        self.assertNotIn(fx.FAKE_HOME, out)

    def test_real_seams_read_no_credentials_and_point_at_this_skills_dir(self):
        seams = goal_prompt.real_seams()
        self.assertEqual(seams.secrets, ())
        self.assertEqual(seams.skills_dir, gp_host.SKILLS_DIR)
        self.assertRegex(seams.today, r"^\d{4}-\d{2}-\d{2}$")

    # ─── render ──────────────────────────────────────────────────────────────

    def test_render_writes_one_goal_file_and_prints_the_contract(self):
        fx.opengsd_project(self.repo, PHASES)
        detect_doc = self.detect(*self.captures())
        code, out, err = self.render(detect_doc, answers())
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertTrue(payload["path"].startswith(".planning/goals/"))
        text = (self.repo / payload["path"]).read_text(encoding="utf-8")
        self.assertIn("/gsd-autonomous --from 16 --to 17 --converge", text)
        for key in ("strategies", "conditions", "sections", "paste_chars", "rails_lines",
                    "warnings", "dropped"):
            self.assertIn(key, payload)

    def test_render_refuses_a_gapped_phase_set_that_autonomous_would_widen(self):
        fx.opengsd_project(self.repo, PHASES)
        detect_doc = self.detect(*self.captures())
        gapped = answers(work_set={"kind": "phases", "numbers": ["16", "17"]})
        code, _out, err = self.render(detect_doc, gapped)
        self.assertEqual(code, 2)
        self.assertIn("contiguous", json.loads(err)["error"])
        self.assertFalse((self.repo / ".planning" / "goals").exists())

    def test_many_long_plan_titles_still_fit_the_goal_condition(self):
        long = "long title " * 14
        titles = {f"p{i:02d}.md": fx.plan_text(f"Plan {i} {long}") for i in range(14)}
        fx.superpowers_project(self.repo, titles)
        detect_doc = self.detect()
        doc = answers(strategy="goal", work_set={"kind": "plans", "files": sorted(titles)})
        code, out, err = self.render(detect_doc, doc)
        self.assertEqual(code, 0, err)
        conditions = json.loads(out)["conditions"]
        self.assertTrue(conditions and conditions[0]["chars"] <= 1800)

    def test_render_rejects_an_absolute_out_dir_without_writing(self):
        fx.opengsd_project(self.repo, PHASES)
        detect_doc = self.detect(*self.captures())
        outside = self.root / "outside"
        code, _out, err = self.render(detect_doc, answers(), "--out-dir", str(outside))
        self.assertEqual(code, 2)
        self.assertIn("inside the repository", json.loads(err)["error"])
        self.assertFalse(outside.exists())

    def test_render_write_failure_exits_two_with_a_json_error(self):
        fx.opengsd_project(self.repo, PHASES)
        detect_doc = self.detect(*self.captures())
        with mock.patch("gp_render.write_atomic", side_effect=PermissionError("denied")):
            code, _out, err = self.render(detect_doc, answers())
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(err), {"error": "cannot read or write a file"})

    def test_missing_repo_exits_two_for_detect_and_render(self):
        missing = str(self.root / "nope")
        code, _out, err = self.call("detect", "--repo", missing)
        self.assertEqual(code, 2)
        self.assertIn("--repo", json.loads(err)["error"])
        fx.opengsd_project(self.repo, PHASES)
        detect_doc = self.detect(*self.captures())
        detect_path = self.write_json("detect.json", detect_doc)
        answers_path = self.write_json("answers.json", answers())
        code, _out, err = self.call(
            "render", "--repo", missing, "--detect", str(detect_path),
            "--answers", str(answers_path),
        )
        self.assertEqual(code, 2)
        self.assertIn("--repo", json.loads(err)["error"])

    def test_empty_phase_list_is_not_reported_as_plan_files(self):
        code, _out, err = self.call("detect", "--repo", str(self.repo), "--work-set", "phases:,")
        self.assertEqual(code, 2)
        self.assertIn("phase", json.loads(err)["error"])
        self.assertNotIn("plan files", json.loads(err)["error"])

    def test_render_bad_answers_exit_two_naming_the_field_never_the_value(self):
        fx.opengsd_project(self.repo, PHASES)
        detect_doc = self.detect(*self.captures())
        missing = answers()
        del missing["work_set"]
        cases = {
            "work_set": missing,
            "numbers": answers(work_set={"kind": "phases", "numbers": [16]}),
            "output_dir": answers(output_dir="/abs/secret-place-xyz"),
        }
        for field, doc in cases.items():
            with self.subTest(field=field):
                code, _out, err = self.render(detect_doc, doc)
                self.assertEqual(code, 2)
                self.assertIn(field, json.loads(err)["error"])
                self.assertNotIn("secret-place-xyz", err)

    def test_render_rejects_answers_that_are_not_json(self):
        fx.opengsd_project(self.repo, PHASES)
        detect_doc = self.detect(*self.captures())
        detect_path = self.write_json("detect.json", detect_doc)
        broken = self.root / "answers.json"
        broken.write_text("{not json", encoding="utf-8")
        code, _out, err = self.call(
            "render", "--repo", str(self.repo), "--detect", str(detect_path),
            "--answers", str(broken),
        )
        self.assertEqual(code, 2)
        self.assertIn("--answers", json.loads(err)["error"])

    def test_render_with_an_unreadable_detect_file_exits_two_naming_the_flag(self):
        code, _out, err = self.call(
            "render", "--repo", str(self.repo), "--detect", str(self.root / "missing.json"),
            "--answers", str(self.root / "missing-answers.json"),
        )
        self.assertEqual(code, 2)
        self.assertIn("--detect", json.loads(err)["error"])

    def test_goal_request_without_a_goal_primitive_is_dropped_not_rendered(self):
        self.host_run.routes = host_routes(rows=[r for r in MATRIX_ROWS if r["kind"] != "goal"])
        fx.opengsd_project(self.repo, PHASES)
        detect_doc = self.detect(*self.captures())
        code, out, err = self.render(detect_doc, answers(strategy="goal"))
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertIn("goal", [d["id"] for d in payload["dropped"]])
        self.assertNotIn("goal", [s["id"] for s in payload["strategies"]])
        text = (self.repo / payload["path"]).read_text(encoding="utf-8")
        self.assertFalse(any(line.startswith("/goal ") for line in text.split("\n")))

    def test_autonomous_request_on_superpowers_is_reported_as_dropped(self):
        fx.superpowers_project(self.repo, {"a.md": fx.plan_text("Plan A")})
        detect_doc = self.detect()
        request = answers(
            work_set={"kind": "plans", "files": ["docs/superpowers/plans/a.md"]},
            strategy="autonomous",
        )
        code, out, err = self.render(detect_doc, request)
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertIn("autonomous", [d["id"] for d in payload["dropped"]])
        self.assertNotIn("autonomous", [s["id"] for s in payload["strategies"]])

    # ─── arguments ───────────────────────────────────────────────────────────

    def test_no_subcommand_and_unknown_subcommand_exit_two(self):
        for argv in ([], ["bogus"]):
            with self.subTest(argv=argv):
                code, out, err = self.call(*argv)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn("error", json.loads(err))

    def test_unknown_target_host_exits_two_naming_the_flag(self):
        code, _out, err = self.call(
            "detect", "--repo", str(self.repo), "--target-host", "nope-host"
        )
        self.assertEqual(code, 2)
        self.assertIn("--target-host", json.loads(err)["error"])
        self.assertNotIn("nope-host", err)

    def test_unknown_work_set_kind_exits_two_naming_the_flag(self):
        code, _out, err = self.call(
            "detect", "--repo", str(self.repo), "--work-set", "bogus:16"
        )
        self.assertEqual(code, 2)
        self.assertIn("--work-set", json.loads(err)["error"])


class TestGsdAtFileReply(unittest.TestCase):
    """A gsd-tools reply that starts with `@file:` names the file that holds its JSON."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        fx.git_init(self.repo)
        self.skills = self.root / "skills"
        for rel in (WAKE_REL, SPEC_REL, JEV_REL):
            fx.write(self.skills, rel, "# stand-in sibling CLI; never executed\n")
        self.host_run = FakeRun(host_routes())
        self.seams = cli_seams(self.host_run, str(self.skills))
        prompt = mock.patch("builtins.input", side_effect=AssertionError("must never prompt"))
        prompt.start()
        self.addCleanup(prompt.stop)
        fx.opengsd_project(self.repo, PHASES)
        self.host_run.routes += [
            (("query", "runtime-identity"), 0, json.dumps(fx.identity_json(True))),
        ]
        ops = fx.phase_op_json(self.repo, PHASES)
        self.host_run.routes += [
            (("query", "init.phase-op", number), 0, json.dumps(doc))
            for number, doc in ops.items()
        ]

    def call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = goal_prompt.main(list(argv), self.seams)
        return code, out.getvalue(), err.getvalue()

    def detect_with_roadmap_reply(self, reply):
        self.host_run.routes.insert(0, (("query", "roadmap.analyze"), 0, reply))
        return self.call("detect", "--repo", str(self.repo),
                         "--gsd-cmd", "node tools/gsd-tools.cjs",
                         "--work-set", "phases:16-17")

    def test_at_file_roadmap_reply_is_read_from_the_named_file(self):
        roadmap = self.root / "roadmap-big.json"
        roadmap.write_text(json.dumps(fx.roadmap_json(PHASES)), encoding="utf-8")
        code, out, err = self.detect_with_roadmap_reply(f"@file:{roadmap}\n")
        self.assertEqual(code, 0, err)
        numbers = [p["number"] for p in json.loads(out)["scope"]["phases"]]
        self.assertEqual(numbers, ["16", "16.1", "17"])

    def test_bad_at_file_replies_fail_with_the_existing_roadmap_error(self):
        message = "the --gsd-cmd roadmap query failed or did not print JSON"
        bad_file = self.root / "not-json.txt"
        bad_file.write_text("plain words, not JSON", encoding="utf-8")
        replies = {
            "missing file": f"@file:{self.root / 'missing.json'}",
            "empty path": "@file:",
            "unreadable JSON": f"@file:{bad_file}",
            "prefix not at start": f"note @file:{bad_file}",
        }
        for label, reply in replies.items():
            with self.subTest(label):
                code, out, err = self.detect_with_roadmap_reply(reply)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertEqual(json.loads(err)["error"], message)

    def test_load_reply_reads_the_file_once_and_plain_json_parses_as_before(self):
        payload = self.root / "payload.json"
        payload.write_text(json.dumps({"phases": []}), encoding="utf-8")
        with mock.patch("builtins.open", wraps=open) as opener:
            parsed = goal_prompt._load_gsd_reply(f"@file:{payload}")
        self.assertEqual(parsed, {"phases": []})
        self.assertEqual(opener.call_count, 1)
        self.assertEqual(goal_prompt._load_gsd_reply('{"a": 1}'), {"a": 1})


if __name__ == "__main__":
    unittest.main()
