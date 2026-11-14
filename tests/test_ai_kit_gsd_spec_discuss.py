"""Tests for skills/ai-kit-gsd-spec-discuss/scripts (phase_range.py, edge_floor.py).

The skill's scripts never call jev: decision help is the `jev-fast-decision` skill's, asked by
the orchestrator (its tests live in tests/test_jev_fast_decision.py). The subprocess tests run the
real CLIs against a temp HOME and XDG tree, never the user's real config.
"""

import argparse
import ast
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
import unittest.mock
from pathlib import Path

from tests.test_jev_fast_decision import closed_port_url

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "ai-kit-gsd-spec-discuss" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import edge_floor
import phase_range


class _TmpHome(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        home = self.tmp / "home"
        home.mkdir()
        # Belt only: no script here reaches a backend, but a closed port keeps it that way.
        self.env = {"HOME": str(home),
                    "XDG_CONFIG_HOME": str(home / ".config"),
                    "XDG_STATE_HOME": str(home / ".local" / "state"),
                    "XDG_DATA_HOME": str(home / ".local" / "share"),
                    "PATH": os.environ.get("PATH", ""),
                    "JEV_LAYA_URL": closed_port_url()}


# ─── phase_range.py ───────────────────────────────────────────────────────────

def _args(start=None, end=None, phases=None):
    return argparse.Namespace(start=start, end=end, list=phases)


class TestPhaseRange(_TmpHome):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "phases"
        self.times = {}
        layout = {"16-a": [], "16.1-b": ["SPEC", "CONTEXT"], "17-c": ["SPEC", "CONTEXT"],
                  "18-d": ["SPEC"], "19-e": ["SPEC", "CONTEXT"]}
        for name, files in layout.items():
            (self.root / name).mkdir(parents=True)
            for kind in files:
                path = self.root / name / f"{name.split('-')[0]}-{kind}.md"
                path.write_text(kind)
                self.times[str(path)] = 100.0
        self.times[str(self.root / "17-c" / "17-SPEC.md")] = 200.0  # SPEC newer
        self.roadmap = {"phases": [
            {"number": "19", "disk_status": "discussed"},
            {"number": "16", "disk_status": "executed"},
            {"number": "17", "disk_status": "discussed"},
            {"number": "16.1", "disk_status": "discussed"},
            {"number": "18", "disk_status": "specified", "mode": "mvp"}]}

    def propose(self, args):
        return phase_range.propose(self.roadmap, str(self.root), args, timer=self.times.get)

    def test_no_range_proposes_undiscussed_with_reasons(self):
        got = self.propose(_args())
        self.assertEqual([(p["phase"], p["reason"]) for p in got["proposed"]],
                         [("17", "SPEC newer than CONTEXT"), ("18", "no CONTEXT")])
        self.assertEqual(got["proposed"][1]["mode"], "mvp")
        self.assertEqual(got["skipped"], [{"phase": "16", "reason": "executed"}])

    def test_explicit_range_and_list(self):
        self.assertEqual([p["phase"] for p in self.propose(_args("16.1", "18"))["proposed"]],
                         ["16.1", "17", "18"])
        self.assertEqual([p["phase"] for p in self.propose(_args(phases="19,16.1"))["proposed"]],
                         ["16.1", "19"])
        # a spaced list passes validation and selects the same phases (skill-judge round 3)
        self.assertEqual([p["phase"] for p in self.propose(_args(phases="19, 16.1"))["proposed"]],
                         ["16.1", "19"])

    def test_decimal_order(self):
        self.assertLess(phase_range.phase_key("16.1"), phase_range.phase_key("16.10"))
        self.assertLess(phase_range.phase_key("9"), phase_range.phase_key("16"))

    def test_nothing_left_to_discuss_proposes_nothing(self):
        self.roadmap = {"phases": [{"number": "16.1", "disk_status": "discussed"}]}
        self.assertEqual(self.propose(_args()), {"proposed": [], "skipped": []})

    def test_equal_timestamps_count_as_discussed(self):
        # SPEC and CONTEXT from one commit share a timestamp: discussed, not proposed.
        self.assertIsNone(phase_range.undiscussed_reason(str(self.root / "16.1-b"),
                                                         self.times.get))

    def _cli(self, text, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / "phase_range.py"),
                               "--roadmap", "-", *args],
                              input=text, capture_output=True, text=True, check=False,
                              cwd=self.tmp, timeout=30)

    def test_malformed_roadmap_exits_2(self):
        # WR-06: an error object, a non-object, a bad entry or a bad selector is exit 2.
        # An empty phases list is the real "nothing to do".
        for text in ('{"error":"engine failed"}', "[]", '{"phases":[null]}',
                     '{"phases":[{"number":"nope"}]}', "not json"):
            with self.subTest(text=text):
                out = self._cli(text)
                self.assertEqual(out.returncode, 2, out.stderr)
                self.assertNotIn("Traceback", out.stderr)
                self.assertNotIn("proposed", out.stdout)
        empty = self._cli('{"phases":[]}')
        self.assertEqual(empty.returncode, 0, empty.stderr)
        self.assertEqual(json.loads(empty.stdout)["proposed"], [])
        roadmap = json.dumps(self.roadmap)
        for args in (("--from", "18", "--to", "16"), ("--from", "abc",),
                     ("--list", "16,nope")):
            with self.subTest(args=args):
                out = self._cli(roadmap, *args)
                self.assertEqual(out.returncode, 2, out.stderr)
                self.assertNotIn("Traceback", out.stderr)

    def test_git_time_equal_later_spec_and_untracked_mtime(self):
        # D-18: commit time, not a substituted clock. Equal stamps are discussed; a later SPEC
        # commit is newer; an untracked SPEC falls back to mtime.
        repo = self.tmp / "gitphase"
        phase = repo / "09-x"
        phase.mkdir(parents=True)
        spec, context = phase / "09-SPEC.md", phase / "09-CONTEXT.md"
        spec.write_text("spec")
        context.write_text("context")
        early, later = "1577836800", "1577923200"

        def git(*args, stamp=early):
            subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=Test",
                            *args], cwd=repo, check=True, capture_output=True,
                           env={**os.environ, "GIT_AUTHOR_DATE": f"@{stamp}",
                                "GIT_COMMITTER_DATE": f"@{stamp}"})

        git("init")
        git("add", ".")
        git("commit", "-m", "both")
        self.assertEqual(phase_range.git_time(str(spec)), float(early))
        self.assertEqual(phase_range.git_time(str(context)), float(early))
        self.assertIsNone(phase_range.undiscussed_reason(str(phase), phase_range.git_time))
        spec.write_text("spec later")
        git("add", "09-x/09-SPEC.md", stamp=later)
        git("commit", "-m", "spec", stamp=later)
        self.assertEqual(phase_range.undiscussed_reason(str(phase), phase_range.git_time),
                         "SPEC newer than CONTEXT")
        other = repo / "10-y"
        other.mkdir()
        (other / "10-CONTEXT.md").write_text("context")
        git("add", "10-y/10-CONTEXT.md")
        git("commit", "-m", "context only")
        untracked = other / "10-SPEC.md"
        untracked.write_text("spec")
        os.utime(untracked, (int(later), int(later)))
        self.assertEqual(phase_range.git_time(str(untracked)), float(later))
        self.assertEqual(phase_range.undiscussed_reason(str(other), phase_range.git_time),
                         "SPEC newer than CONTEXT")


# ─── edge_floor.py ────────────────────────────────────────────────────────────

SPEC = textwrap.dedent("""\
    # Phase 9: X — Specification

    ## Requirements

    1. **Parse rows**.
       - Target: an empty list yields no rows; a row at the max width parses.
       - Acceptance: tests.

    2. **Write cache** (REQ-2).
       - Target: two concurrent writers leave one intact file.

    ## Boundaries

    nothing

    ## Edge Coverage

    | Category | Requirement | Status | Resolution / Reason |
    |----------|-------------|--------|---------------------|
    | empty | R1 | ✅ covered | Empty input yields [] |
    | boundary | R1 | ✅ covered | Max width parses (added by the author) |
    | unclassified | R2 | ✅ covered | wrong |
    | ordering | R2 | 🧪 backstop | unmarked extra |

    ## Prohibitions (must-NOT)
    """)


class TestEdgeFloor(unittest.TestCase):
    def test_requirements_extraction_rule(self):
        reqs = edge_floor.requirements(SPEC)
        self.assertEqual([r["id"] for r in reqs], ["R1", "R2"])
        self.assertTrue(reqs[0]["text"].startswith("Parse rows. "))
        self.assertIn("Target: an empty list yields no rows", reqs[0]["text"])
        self.assertIn("Acceptance: tests.", reqs[0]["text"])

    def test_partial_and_duplicate_requirements_fail_closed(self):
        # WR-04: a numbered line without a bold title must not disappear into R1, and a
        # repeated id must not be sent to the engine as two different requirements.
        partial = SPEC.replace("2. **Write cache** (REQ-2).", "2. Write cache.")
        duplicate = SPEC.replace("2. **Write cache**", "1. **Write cache**")
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._engine_at(Path(tmp))
            for name, text in (("partial", partial), ("duplicate", duplicate)):
                spec = Path(tmp) / f"{name}-SPEC.md"
                spec.write_text(text)
                with self.subTest(name=name):
                    self.assertRaises(ValueError, edge_floor.requirements, text)
                    err = io.StringIO()
                    with unittest.mock.patch("sys.stderr", err):
                        code = edge_floor.main(["check", str(spec), "--engine", engine],
                                               env={"HOME": tmp, "PATH": ""})
                    self.assertEqual(code, 2)
                    self.assertNotIn("Traceback", err.getvalue())

    def test_malformed_engine_row_exits_2_and_drift_exits_1(self):
        # WR-05: a row the engine did not actually fill is fail-closed, not coverage drift.
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "09-SPEC.md"
            spec.write_text(SPEC)
            engine = self._engine_at(Path(tmp))

            def run_with(stdout):
                def fake_run(cmd, **_kwargs):
                    return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

                err = io.StringIO()
                with unittest.mock.patch("edge_floor.shutil.which", return_value="node"), \
                        unittest.mock.patch("edge_floor.subprocess.run", fake_run), \
                        unittest.mock.patch("sys.stderr", err):
                    code = edge_floor.main(["check", str(spec), "--engine", engine],
                                           env={"HOME": tmp, "PATH": tmp})
                return code, err.getvalue()

            for payload in ('{"items":[{}]}', '{"items":[null]}',
                            '{"items":[{"category":1,"requirement_id":"R1"}]}'):
                with self.subTest(payload=payload):
                    code, err = run_with(payload)
                    self.assertEqual(code, 2)
                    self.assertNotIn("Traceback", err)
            code, err = run_with(
                '{"items":[{"category":"missing","requirement_id":"R9"}]}')
            self.assertEqual(code, 1, err)
            self.assertNotIn("Traceback", err)

    def test_compare_flags_missing_unmarked_and_unclassified(self):
        floor = {"items": [{"category": "empty", "requirement_id": "R1"},
                           {"category": "concurrency", "requirement_id": "R2"},
                           {"category": "unclassified", "requirement_id": "R2"}]}
        got = edge_floor.compare(floor, edge_floor.table_rows(SPEC))
        self.assertFalse(got["ok"])
        self.assertEqual(got["missing"], [("concurrency", "R2")])
        self.assertEqual(got["unmarked_extra"], [("ordering", "R2")])
        self.assertEqual(got["unclassified_not_unresolved"], [("unclassified", "R2")])

    def test_no_extracted_requirements_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = self._engine_at(root)
            for text in ("# Spec\n", "## Requirements\n\n1. Parse rows\n"):
                spec = root / "09-SPEC.md"
                spec.write_text(text)
                with self.subTest(text=text), unittest.mock.patch("sys.stderr"):
                    self.assertEqual(edge_floor.main(["check", str(spec), "--engine", engine],
                                                     env={"HOME": tmp}), 2)

    def test_missing_engine_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "09-SPEC.md"
            spec.write_text(SPEC)
            env = {"HOME": tmp, "RUNTIME_DIR": tmp}
            with unittest.mock.patch("sys.stderr"):
                self.assertEqual(edge_floor.main(["check", str(spec)], env=env), 2)

    @staticmethod
    def _engine_at(root: Path) -> str:
        path = root / "gsd-core" / "bin" / "lib" / "edge-probe.cjs"
        path.parent.mkdir(parents=True)
        path.write_text("")
        return str(path)

    def test_project_local_engine_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._engine_at(Path(tmp) / "proj" / ".claude")
            env = {"HOME": str(Path(tmp) / "home"), "RUNTIME_DIR": str(Path(tmp) / "proj")}
            self.assertEqual(edge_floor.find_engine(env, tmp, None), engine)

    def test_project_local_beats_host_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._engine_at(Path(tmp) / "home" / ".claude")
            local = self._engine_at(Path(tmp) / "proj")
            env = {"HOME": str(Path(tmp) / "home"), "RUNTIME_DIR": str(Path(tmp) / "proj")}
            self.assertEqual(edge_floor.find_engine(env, tmp, None), local)

    def test_gsd_run_on_path_is_last_resort(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._engine_at(Path(tmp) / "elsewhere")
            launcher = Path(engine).parent.parent / "gsd_run"
            launcher.write_text("#!/bin/sh\n")
            launcher.chmod(0o755)
            env = {"HOME": str(Path(tmp) / "home"), "RUNTIME_DIR": str(Path(tmp) / "proj"),
                   "PATH": str(launcher.parent)}
            self.assertEqual(edge_floor.find_engine(env, tmp, None), engine)


class TestSkillContract(unittest.TestCase):
    """Prose contracts the scripts cannot enforce: the SKILL.md and reference text the spec
    names as acceptance. Stdlib text checks, so a dropped rule fails the suite."""

    ROOT = Path(__file__).resolve().parent.parent / "skills" / "ai-kit-gsd-spec-discuss"

    def read(self, rel):
        return (self.ROOT / rel).read_text(encoding="utf-8")

    def test_frontmatter_names_the_skill_and_triggers_on_use_when(self):
        head = self.read("SKILL.md").split("---", 2)[1]
        self.assertIn("name: ai-kit-gsd-spec-discuss", head)
        self.assertIn("Use when", head)
        self.assertIn("Not for plan-phase or execute-phase", head)

    def test_description_is_within_the_1024_char_limit(self):
        # Agent Skills standard: frontmatter description <= 1024 characters.
        head = self.read("SKILL.md").split("---", 2)[1]
        line = next(l for l in head.splitlines() if l.startswith("description:"))
        self.assertLessEqual(len(line[len("description:"):].strip()), 1024)

    def test_quality_rule_reads_mode_and_states_both_branches(self):
        skill = self.read("SKILL.md")
        for needle in ("phase.mvp-mode", "workflow.mvp_mode", "--default false",
                       "`mvp-mode` inactive", "`mvp-mode` active"):
            self.assertIn(needle, skill)
        self.assertIn("Quality rule:", self.read("references/analyzer-brief.md"))

    def test_discuss_uses_assumptions_workflow_and_records_session(self):
        skill = " ".join(self.read("SKILL.md").split())  # the prose wraps across lines
        self.assertIn("discuss-phase-assumptions.md", skill)
        self.assertIn("never** pass `--assumptions`", skill)
        self.assertIn("state.record-session", skill)

    def test_setup_checks_agent_skills_wiring_and_never_edits_config(self):
        skill = " ".join(self.read("SKILL.md").split())
        for needle in ("query agent-skills gsd-assumptions-analyzer --json "
                       "2>\"<tmp>-analyzer.err\"",
                       "pass the parent of `phase_dir` to `phase_range.py --phases-root`",
                       "commit the `state_path` file",
                       "it does not parse `--ws` itself",
                       "gsd-advisor-researcher", "USER-PROFILE.md",
                       "after step 7, which decides the agents that run",
                       "the JSON reads `reason: resolved`, its `warnings` are empty",
                       "no line starting `[agent-skills] WARNING`",
                       "report it with its cause and continue", "ai-kit-gsd-curated-config",
                       "never edits config", "references/agent-skills-diagnostics.md",
                       "When the user passes `--ws <name>`, append `--ws=<name>`"):
            self.assertIn(needle, skill)
        self.assertNotIn("gsd_run query agent-skills", skill)
        self.assertNotIn("Continue only then", skill)
        diag = " ".join(self.read("references/agent-skills-diagnostics.md").split())
        for needle in ("[agent-skills] WARNING", "not_configured", "configured_empty",
                       "configured_unresolved", "not confined to the project directory",
                       "failed path check (symlink escape?)",
                       "Re-running curated-config fixes only path and wiring causes",
                       "The warnings decide", "acceptance trace, not a warning"):
            self.assertIn(needle, diag)

    def test_analyzer_never_calls_jev_even_when_the_skill_is_wired(self):
        skill = " ".join(self.read("SKILL.md").split())
        brief = " ".join(self.read("references/analyzer-brief.md").split())
        self.assertIn("`gsd-assumptions-analyzer` and `gsd-advisor-researcher` never call jev, "
                      "even when `jev-fast-decision` is wired into them", skill)
        self.assertNotIn("SKL-04", skill)
        self.assertIn('adds this one sentence to the advisor\'s spawn prompt: "Do NOT call '
                      'jev-fast-decision yourself, even when it is among your agent skills."',
                      skill)
        self.assertIn("never call jev even when `jev-fast-decision` is among your agent skills",
                      brief)
        self.assertIn("Asking jev and the log belong to the orchestrator (this skill).", skill)
        self.assertIn("never call jev even when `jev-fast-decision` is among your agent "
                      "skills", brief)
        self.assertNotIn("The same line goes in the `gsd-advisor-researcher` spawn prompt",
                         brief)

    def test_codegraph_block_is_gated_on_the_binary_and_an_index(self):
        brief = self.read("references/analyzer-brief.md")
        self.assertIn("<CODEGRAPH BLOCK", brief)
        self.assertIn("command -v codegraph", brief)
        self.assertIn("codegraph sync", brief)
        self.assertIn("codegraph_explore", brief)

    def test_decision_table_covers_blocking_by_confidence(self):
        table = self.read("references/decision-table.md")
        for cell in ("Non-blocking, high", "Non-blocking, low", "Blocking, high",
                     "Blocking, low"):
            self.assertIn(cell, table)

    def test_orchestrator_does_not_copy_client_limits(self):
        # The key inventory, size caps and worked-example lessons live with the client and the
        # decision table, not a second copy in the orchestrator.
        skill = self.read("SKILL.md")
        self.assertIn("follow its SKILL.md", skill)
        self.assertNotIn("8,000", skill)
        self.assertNotIn("2,000", skill)
        self.assertNotIn("0.75", self.read("references/decision-table.md"))
        self.assertNotIn("Lesson:", self.read("references/worked-examples.md"))

    def test_explicit_selection_still_runs_a_current_phase(self):
        # WR-08: the skip applies to the automatic proposal. An explicit range or list wins.
        skill = " ".join(self.read("SKILL.md").split())
        self.assertIn("Explicit `--from N --to M` or a list wins", skill)
        self.assertIn("automatic proposal skipped", skill)
        self.assertIn("explicit range or list still runs that phase", skill)

    def test_rules_cover_both_run_paths(self):
        # Round-3 item 2: no "the rules below are the auto path" scoping — the shared rules
        # are stated as both-paths, with the jev/analyzer split per path.
        skill = " ".join(self.read("SKILL.md").split())
        self.assertIn("**Rules that hold in both paths:**", skill)
        self.assertIn("the skill never plans or executes", skill)
        self.assertIn("the interactive path the user answers the workflow's prompts, and jev "
                      "only screens the items the user asks it to screen", skill)
        self.assertIn("in the auto path jev is asked about every open item", skill)

    def test_analyzer_never_starts_before_its_own_spec(self):
        # Round-3 item 3: pacing — phase K's analyzer needs K's SPEC committed and current.
        skill = " ".join(self.read("SKILL.md").split())
        self.assertIn("must never start before that phase's spec step has finished", skill)
        brief = self.read("references/analyzer-brief.md")
        self.assertIn("after this phase's spec step has finished", brief)
        self.assertNotIn("while phase <K> is being written", brief)

    def test_auto_flag_and_recommendation_rule(self):
        # Item 5: the skill takes an optional --auto; without it, one config-backed ask.
        # (Round 3 moved run-mode mechanics out of the description into the body, so the
        # flag wording is asserted in the body, not the frontmatter.)
        head = self.read("SKILL.md").split("---", 2)[1]
        self.assertIn("Two run modes, picked once: auto", head)
        skill = " ".join(self.read("SKILL.md").split())
        self.assertIn("Pick the run mode", skill)
        self.assertIn("With the skill's `--auto` flag: auto path", skill)
        self.assertIn("config-get mode", skill)
        self.assertIn("config-get workflow.mvp_mode", skill)
        self.assertIn("Key not found", skill)
        self.assertIn("default (`interactive`)", skill)
        # the recommendation rule: auto when yolo mode or the phase's mvp-mode is active —
        # the same per-phase source as the quality rule (round-3 item: read mvp once)
        self.assertIn("recommend the **auto path** when `mode` is `yolo` or the phase's "
                      "`mvp-mode` is active", skill)
        self.assertIn("**interactive path** otherwise", skill)
        self.assertIn("Never flip config keys to pick a path", skill)
        # per-phase steps follow the picked mode
        self.assertIn("arguments `N --auto` (auto path) or plain `N` (interactive path)", skill)
        self.assertIn("The **interactive path** runs `<workflows>/discuss-phase.md` instead", skill)
        self.assertIn("with the user answering its prompts", skill)
        # owner decision 2026-11-02: interactive discuss runs all gray areas, grouped
        # questions and trade-off tables
        self.assertIn("with arguments `N --analyze --all --batch`", skill)
        self.assertIn("read and execute `<workflows>/discuss-phase-assumptions.md` "
                      "with argument `N` — **never** pass `--assumptions`", skill)
        # every description of the interactive mode names the same three flags
        self.assertIn("discuss in standard mode with `--analyze --all --batch`, "
                      "the user answering", skill)
        self.assertIn("discuss-phase with `--analyze --all --batch`, the user answering", skill)
        self.assertIn("runs standard discuss mode with `--analyze --all --batch` instead", skill)
        self.assertNotIn("its standard discuss mode with the user answering", skill)
        # NEVER list keeps both guards
        self.assertIn("NEVER pass `--auto` to discuss in assumptions mode", skill)
        self.assertIn("`workflow.discuss_mode`, `mode` or `workflow.mvp_mode`", skill)

    def test_one_needs_confirmation_rule_in_both_places(self):
        # Item 2: flag only when an item would change or contradict a user-locked decision.
        rule = "would change or contradict"
        not_flagged = "agrees with"
        skill = " ".join(self.read("SKILL.md").split())
        table = " ".join(self.read("references/decision-table.md").split())
        for text in (skill, table):
            self.assertIn(rule, text)
            self.assertIn(not_flagged, text)
        self.assertIn("decision-table row 1, same rule", skill)
        self.assertIn("**The item would change or contradict a user-locked decision**", table)

    def test_jev_fallback_routes_to_own_reasoning(self):
        # A low, errored or missing jev answer goes to own reasoning (decision-table row 4).
        # A forced answer has its own line under row 4 (TestPhase324Contract pins it).
        table = " ".join(self.read("references/decision-table.md").split())
        self.assertIn("(`needs_fallback`, an error or no answer) → own reasoning against the "
                      "evidence", table)
        skill = " ".join(self.read("SKILL.md").split())
        self.assertIn("advisory evidence for the row that decides", skill)
        self.assertIn("`needs_fallback`, an error or no answer → **own reasoning**", skill)
        logs = " ".join(self.read("references/log-formats.md").split())
        for cell in ("`choice 0.NN`", "`low 0.NN`", "`not installed`", "`error: <code>`"):
            self.assertIn(cell, logs)
        self.assertNotIn("(forced)", logs)
        section6 = self.read("references/worked-examples.md").split("## 6.", 1)[1]
        self.assertIn("illustrative", section6)
        self.assertIn("Row 4 applies", section6)

    def test_worked_example_two_owns_the_low_second_opinion(self):
        # Item 3: a 0.74 (fb) TypeSafe second opinion is no high remote answer — own
        # reasoning, ledgered, never "Laya overridden".
        text = self.read("references/worked-examples.md")
        example2 = text.split("## 2.", 1)[1].split("## 3.", 1)[0]
        self.assertNotIn("Laya overridden", example2)
        self.assertIn("**Own reasoning:**", example2)
        self.assertIn("ledger", example2)

    def test_jev_call_count_and_prose_minors(self):
        # Item 4 + item 6 minors.
        skill = " ".join(self.read("SKILL.md").split())
        self.assertIn("Each step that has open items (spec and discuss separately, §1–§2) is one "
                      "jev request", skill)
        self.assertIn("spec and discuss separately", skill)
        self.assertIn("one second opinion", skill)
        self.assertNotIn("one client call per phase", skill)
        self.assertNotIn("init phase-op", skill)
        self.assertIn("init.phase-op", skill)
        self.assertIn("--roadmap <tmp>.json --from N --to M` (or `--list a,b`)", skill)
        self.assertIn("Get the roadmap first, for every case", skill)
        self.assertIn("CLAUDE_ENV_FILE", skill)
        self.assertIn("Print the resolved command", skill)
        self.assertIn("the `gsd_run` executable itself on the resolver's PATH-shim branch", skill)
        self.assertIn("query resolve-model gsd-assumptions-analyzer --raw", skill)
        self.assertNotIn("its output also carries the resolved analyzer model", skill)

    def test_prose_minors_round_three(self):
        skill = " ".join(self.read("SKILL.md").split())
        # the todo threshold is sourced, not invented
        self.assertIn("gsd-core's workflow constant", skill)
        # the Interview Log trigger uses the MANDATORY framing
        self.assertIn("MANDATORY — read `references/log-formats.md` before writing it", skill)
        # mvp is read once, per phase, for both the quality rule and the recommendation
        self.assertIn("do not read `workflow.mvp_mode` a second way", skill)
        # log formats parameterize run mode and round count
        logs = self.read("references/log-formats.md")
        self.assertIn("<Run mode and rounds:", logs)
        self.assertIn("<run mode: Assumptions Mode for the auto path", logs)
        self.assertIn("standard discuss mode (`--analyze --all --batch`) with the user",
                      " ".join(logs.split()))

    def test_readme_registers_the_skill(self):
        readme = (self.ROOT.parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("skills/ai-kit-gsd-spec-discuss/SKILL.md", readme)
        row = next(ln for ln in readme.splitlines()
                   if "skills/ai-kit-gsd-spec-discuss/SKILL.md" in ln)
        self.assertIn("interactive (discuss with `--analyze --all --batch`", row)


def _flat(text):
    return " ".join(text.split())


class TestPhase324Contract(unittest.TestCase):
    """One doc-contract test per phase 32.4 spec-discuss item (SPEC R5-R9).

    Each test matches whitespace-normalised text, so re-wrapping a line does not break it.
    """

    ROOT = Path(__file__).resolve().parent.parent / "skills" / "ai-kit-gsd-spec-discuss"

    def read(self, rel):
        return (self.ROOT / rel).read_text(encoding="utf-8")

    def description(self):
        head = self.read("SKILL.md").split("---", 2)[1]
        line = next(ln for ln in head.splitlines() if ln.startswith("description:"))
        return line[len("description:"):].strip()

    def test_handoff_runs_after_the_state_commit(self):
        skill = _flat(self.read("SKILL.md"))
        self.assertIn("Hand off to goal-prompt (auto path only)", skill)
        self.assertIn("After the range's `docs(state)` commit, prepare the autonomous-run prompt "
                      "for the discussed range", skill)
        self.assertLess(skill.index("query state.record-session"),
                        skill.index("Hand off to goal-prompt"))

    def test_handoff_supplies_the_discussed_range_and_the_runs_decisions(self):
        skill = _flat(self.read("SKILL.md"))
        for needle in ("the §0 step 1 `GOAL_MD` literal",
                       "the work set is the discussed phases in numeric order",
                       "`native_execution` comes from this run's decisions (default false)",
                       "Supply its answers instead of its four questions"):
            self.assertIn(needle, skill)

    def test_handoff_not_installed_and_empty_range_stop(self):
        skill = _flat(self.read("SKILL.md"))
        for needle in ("Empty `GOAL_MD`: say goal-prompt is not installed and stop.",
                       "stop earlier only on a blocker",
                       "A range in which no phase was discussed prepares no prompt "
                       "and says so."):
            self.assertIn(needle, skill)

    def test_forced_answer_has_its_own_line_under_row_4(self):
        table = _flat(self.read("references/decision-table.md"))
        for needle in ("A forced answer (`forced` true", "logged `forced`",
                       "shorten the item or split the request"):
            self.assertIn(needle, table)
        self.assertLess(table.index("4. **jev gave no confident answer**"),
                        table.index("A forced answer"))
        self.assertLess(table.index("A forced answer"),
                        table.index("5. **jev is not installed"))

    def test_commit_rule_counts_the_spec_commit(self):
        skill = _flat(self.read("SKILL.md"))
        self.assertIn("spec-phase's own SPEC commit is the phase's spec-step commit", skill)

    def test_own_analyzer_never_runs_while_its_context_is_written(self):
        skill = _flat(self.read("SKILL.md"))
        self.assertIn("start phase K+1's analyzer while you write phase K's CONTEXT", skill)
        self.assertIn("Phase K's own analyzer never runs while phase K's CONTEXT "
                      "is being written", skill)
        self.assertNotIn("start phase K's analyzer while you write phase K's CONTEXT", skill)

    def test_early_stop_still_records_the_session(self):
        skill = _flat(self.read("SKILL.md"))
        self.assertIn("An early stop", skill)
        self.assertIn("runs the same `state.record-session` with the stop reason "
                      "in `--stopped-at`", skill)
        self.assertIn("with its own `docs(state)` commit, even when no phase was committed",
                      skill)

    def test_a_start_refusal_stops_before_any_write(self):
        """§1's `start` refusal (dirty tree, wrong parent, ...) writes nothing, so the early-stop
        session record and its commit never apply to it."""
        skill = _flat(self.read("SKILL.md"))
        self.assertIn("A `start` refusal that stops the run (§1) stops before any write: "
                      "no `state.record-session` and no commit", skill)
        self.assertNotIn("or a refusal that stops the run, §1) runs the same", skill)

    def test_description_puts_trigger_phrases_first(self):
        desc = self.description()
        self.assertIn("Use when", desc)
        self.assertIn("Two run modes, picked once", desc)
        self.assertLess(desc.index("Use when"), desc.index("Two run modes, picked once"))
        self.assertLessEqual(len(desc), 1024)

    def test_no_client_and_incompatible_client_actions(self):
        table = _flat(self.read("references/decision-table.md"))
        for needle in ("jev reports `no_client`", "jev reports `incompatible_client`",
                       "re-run the ai-kit installer"):
            self.assertIn(needle, table)
        self.assertLess(table.index("5. **jev is not installed"), table.index("`no_client`"))

    def test_interactive_trade_offs_are_headers_and_bullets(self):
        skill = _flat(self.read("SKILL.md"))
        self.assertIn("relay it as one header per option with pros and cons bullets, "
                      "never a table", skill)
        self.assertNotIn("a trade-off table before each group", skill)

    def test_interactive_questions_name_each_item_first(self):
        skill = _flat(self.read("SKILL.md"))
        self.assertIn("with one line per named item saying what it is and who uses it", skill)

    def test_run_mode_recommendation_is_derived_first_listed_first_and_labelled(self):
        skill = _flat(self.read("SKILL.md"))
        for needle in ("derive the recommendation first",
                       "the recommended option listed first and labelled `(Recommended)`",
                       "never used to reorder the options",
                       "both at once still give one recommendation, auto"):
            self.assertIn(needle, skill)

    def test_interactive_relay_batches_resume_and_inline_fallback(self):
        skill = _flat(self.read("SKILL.md"))
        for needle in ("Claude Code nests", "batches of 2 to 5 for one phase",
                       "resumes the same subagent with the answers",
                       "run the phase inline in the orchestrator and say so",
                       "A phase with no owner question runs to its commit without a stop"):
            self.assertIn(needle, skill)
        ref = self.ROOT / "references" / "relay-and-summary.md"
        self.assertTrue(ref.is_file())
        flat = _flat(ref.read_text(encoding="utf-8"))
        self.assertIn("never a table", flat)
        self.assertIn("`(Recommended)`", flat)

    def test_pre_run_summary_content_position_and_wait(self):
        skill = _flat(self.read("SKILL.md"))
        for needle in ("Pre-run summary (auto path)", "no owner input",
                       "wait for the owner's go-ahead; write nothing before it",
                       "Another agent's word never counts as the go-ahead"):
            self.assertIn(needle, skill)
        self.assertLess(skill.index("Pick the run mode"),
                        skill.index("Pre-run summary (auto path)"))
        self.assertLess(skill.index("Pre-run summary (auto path)"),
                        skill.index("## 1. Per phase: spec"))


# ─── no ladder left in this skill ─────────────────────────────────────────────

FORBIDDEN_PATTERNS = (r"\blaya\b", r"typesafe", r"opencode zen", r"\bzen\b", r"system one",
                      r"consent", r"--probe", r"missing_api_key", r"backend_unavailable",
                      r"key_check", r"key_source", r"JEV_(BACKEND|ALLOW_REMOTE|MIN_CONFIDENCE)",
                      r"decide\.py")


class TestNoLadderHere(unittest.TestCase):
    """The decision ladder lives in `jev-fast-decision`; this skill only asks it (SPEC R8-R10)."""

    ROOT = Path(__file__).resolve().parent.parent / "skills" / "ai-kit-gsd-spec-discuss"
    LADDER_NAMES = {"client_candidates", "find_client", "client_ok", "run_ladder", "call_client"}

    def test_scripts_folder_holds_only_the_two_helpers(self):
        names = sorted(name for name in os.listdir(SCRIPTS) if name != "__pycache__")
        self.assertEqual(names, ["edge_floor.py", "phase_range.py"])

    def test_scripts_define_no_ladder_or_client_lookup(self):
        for name in ("edge_floor.py", "phase_range.py"):
            tree = ast.parse((SCRIPTS / name).read_text(encoding="utf-8"))
            defined = {node.name for node in ast.walk(tree)
                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            self.assertFalse(defined & self.LADDER_NAMES, name)

    def test_phase_range_runs_with_no_jev_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            out = subprocess.run(
                [sys.executable, str(SCRIPTS / "phase_range.py"), "--roadmap", "-"],
                input='{"phases":[]}', capture_output=True, text=True, cwd=tmp, timeout=30,
                env={"HOME": str(home), "PATH": os.environ.get("PATH", "")}, check=False)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["proposed"], [])

    def test_skill_asks_jev_as_a_black_box_and_routes_fallbacks_to_own_reasoning(self):
        skill = " ".join((self.ROOT / "SKILL.md").read_text(encoding="utf-8").split())
        self.assertIn("ask the `jev-fast-decision` skill and follow its SKILL.md", skill)
        self.assertIn("`needs_fallback`, an error or no answer → **own reasoning**", skill)

    def test_skill_names_no_backend_or_client_internal(self):
        skill = (self.ROOT / "SKILL.md").read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, skill, re.IGNORECASE))

    def test_references_name_no_backend_or_client_internal(self):
        for path in sorted((self.ROOT / "references").glob("*.md")):
            body = path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_PATTERNS:
                with self.subTest(file=path.name, pattern=pattern):
                    self.assertIsNone(re.search(pattern, body, re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
