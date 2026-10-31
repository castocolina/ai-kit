"""Property sweep, golden file and R18/R19 parity for the generated goal prompt (GPS-02..04).

Every scenario runs the real CLI layer on a temporary git repository: `goal_prompt.build_detect`
and `goal_prompt.run_render`, with a faked host seam. Nothing prompts, nothing touches a real home
and nothing runs a model. Regenerate the committed golden with:

    UPDATE_GOLDEN=1 python3 -m unittest tests.test_ai_kit_spec_goal_prompt_golden

and read the diff before committing it (SPEC acceptance: a human reads the golden).
"""

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, NamedTuple

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
GOLDEN = REPO / "tests" / "fixtures" / "goal_prompt" / "golden" / "opengsd-recommended.md"
sys.path.insert(0, str(SCRIPTS))
for rules_dir in (REPO / "skills" / "_shared", REPO / "skills" / "ai-kit-project-rules-agents"):
    sys.path.insert(0, str(rules_dir))

import goal_prompt
import gp_common
import gp_host
import gp_render
from ai_kit_project_rules_agents import rules as agent_rules
from ai_kit_rules_common.classification import check_rules

from tests import goal_prompt_fixtures as fx
from tests.test_ai_kit_spec_goal_prompt_cli import MATRIX_ROWS, FakeRun, host_routes

TODAY = "2026-01-02"
FENCE = "````"
SHARED = "## Rails"
HEADINGS = gp_render.HEADINGS
UNIT = "Unit tests alone never count as done."
OBJECTIVE = "Ship phases 16 to 17 with the curated config checks green."
WAKE_REL = "ai-kit-session-wake/ai-kit-session-wake.py"
SPEC_REL = "ai-kit-spec-review/ai-kit-spec.py"
DECIDE_REL = "ai-kit-gsd-spec-discuss/scripts/decide.py"
UPSTREAM = {
    "from": re.compile(r"--from\s+[0-9]+[A-Z]?(?:\.[0-9]+)*"),
    "to": re.compile(r"--to\s+[0-9]+[A-Z]?(?:\.[0-9]+)*"),
    "only": re.compile(r"--only\s+[0-9]+[A-Z]?(?:\.[0-9]+)*"),
}
CONVERGE = re.compile(r"(?:^|[ \t])--converge(?:[ \t]|$)")
FLAGS_LINE = re.compile(r"^/gsd-autonomous( --(from|to|only) [0-9][0-9.]*| --converge)+$")
PHASES = [
    fx.phase_spec("16", "Foundation", plans=2, cross_ai=2, verification=True),
    fx.phase_spec("16.1", "Hotfix", plans=1),
    fx.phase_spec("17", "Surfaces", spec=False, plans=2),
]
CODEX_ROWS = [
    {"host": "codex", "primitive": "/goal", "kind": "goal", "surface": "slash-command",
     "survives_stall": False, "survives_process_death": False, "survives_reboot": False,
     "rank": 0, "source": "unverified", "version_floor": None, "evidence": "fixture"},
    {"host": "codex", "primitive": "systemd user timer", "kind": "os-timer", "surface": "cli",
     "survives_stall": True, "survives_process_death": True, "survives_reboot": True,
     "rank": 3, "source": "unverified", "version_floor": None, "evidence": "fixture"},
]
E2E_TARGETS = {
    "e2e-test": "python3 -m unittest discover -s tests/e2e",
    "test-unit": "python3 -m unittest",
}
GSD_ANSWERS = {
    "work_set": {"kind": "phases", "numbers": ["16", "16.1", "17"]},
    "target_host": "claude",
    "native_execution": False,
    "mockups": [],
    "strategy": None,
    "objective": OBJECTIVE,
    "output_dir": None,
}
PLANS_ABC = {
    "work_set": {"kind": "plans", "files": [
        "docs/superpowers/plans/a.md", "docs/superpowers/plans/b.md",
        "docs/superpowers/plans/c.md"]},
    "target_host": "claude", "native_execution": False, "mockups": [],
    "strategy": None, "objective": OBJECTIVE, "output_dir": None,
}


def _gsd_e2e(repo: Path) -> None:
    fx.opengsd_project(repo, PHASES)
    fx.makefile(repo, E2E_TARGETS)


def _gsd_no_e2e(repo: Path) -> None:
    fx.opengsd_project(repo, PHASES)


def _gsd_unready(repo: Path) -> None:
    fx.opengsd_project(repo, PHASES)
    fx.makefile(repo, E2E_TARGETS)
    fx.write(repo, ".planning/config.json", json.dumps({"workflow": {}}) + "\n")


def _plans_chain(repo: Path) -> None:
    fx.superpowers_project(repo, {
        "a.md": fx.plan_text("Plan A"),
        "b.md": fx.plan_text("Plan B", depends_on="a.md"),
        "c.md": fx.plan_text("Plan C"),
    })


def _plan_single(repo: Path) -> None:
    fx.superpowers_project(repo, {"a.md": fx.plan_text("Plan A")})


def _free_ignored(repo: Path) -> None:
    fx.write(repo, ".gitignore", "tmp/\n")


class Scenario(NamedTuple):
    name: str
    project: Any
    captures: tuple | None
    detect_args: tuple
    answers: dict
    rows: Any
    order: bool
    upstream: dict | None


SCENARIOS = (
    Scenario("opengsd-recommended", _gsd_e2e, (PHASES, True), ("--work-set", "phases:16-17"),
             GSD_ANSWERS, None, True, {"from": "16", "to": "17", "only": ""}),
    Scenario("opengsd-native", _gsd_e2e, (PHASES, True), ("--work-set", "phases:16-17"),
             {**GSD_ANSWERS, "native_execution": True}, None, True,
             {"from": "16", "to": "17", "only": ""}),
    Scenario("opengsd-user-goal", _gsd_e2e, (PHASES, True), ("--work-set", "phases:16-17"),
             {**GSD_ANSWERS, "strategy": "goal"}, None, True,
             {"from": "16", "to": "17", "only": ""}),
    Scenario("opengsd-mockup", _gsd_e2e, (PHASES, True), ("--work-set", "phases:16-17"),
             {**GSD_ANSWERS, "mockups": ["docs/mockups/home.png"]}, None, True,
             {"from": "16", "to": "17", "only": ""}),
    Scenario("opengsd-readiness-failed", _gsd_unready, (PHASES, True),
             ("--work-set", "phases:16-17"), GSD_ANSWERS, None, True,
             {"from": "16", "to": "17", "only": ""}),
    Scenario("gsd-unproven", _gsd_e2e, (PHASES, False), ("--work-set", "phases:16-17"),
             GSD_ANSWERS, None, True, {"from": "16", "to": "17", "only": ""}),
    Scenario("superpowers-chain", _plans_chain, None, (), PLANS_ABC, None, True, None),
    Scenario("superpowers-single-plan", _plan_single, None, (),
             {**PLANS_ABC, "work_set": {"kind": "plans",
                                        "files": ["docs/superpowers/plans/a.md"]}},
             None, False, None),
    Scenario("no-e2e-create-first", _gsd_no_e2e, (PHASES, True),
             ("--work-set", "phases:16-17"), GSD_ANSWERS, None, True,
             {"from": "16", "to": "17", "only": ""}),
    Scenario("host-without-goal-or-loop", _plans_chain, None, (), PLANS_ABC, [], True, None),
    Scenario("codex-target", _plans_chain, None, ("--target-host", "codex"), PLANS_ABC,
             MATRIX_ROWS + CODEX_ROWS, True, None),
    Scenario("free-text-tmp", _free_ignored, None,
             ("--work-set", "free:tidy the parser module"),
             {"work_set": {"kind": "free", "text": "tidy the parser module"},
              "target_host": "claude", "native_execution": False, "mockups": [],
              "strategy": None, "objective": "", "output_dir": None},
             None, False, None),
    Scenario("opengsd-single-phase", _gsd_e2e, (PHASES, True), ("--work-set", "phases:16"),
             {**GSD_ANSWERS, "work_set": {"kind": "phases", "numbers": ["16"]}}, None, True,
             {"from": "16", "to": "", "only": "16"}),
)


class Outcome(NamedTuple):
    detect: dict
    payload: dict
    text: str


def _stand_in_skills(root: Path) -> str:
    skills = root / "skills"
    for rel in (WAKE_REL, SPEC_REL, DECIDE_REL):
        fx.write(skills, rel, "# stand-in sibling CLI; never executed\n")
    return str(skills)


def _capture_flags(root: Path, phases: list, opengsd: bool) -> list[str]:
    base = root / "captures"
    fx.write(base, "roadmap.json", json.dumps(fx.roadmap_json(phases)))
    fx.write(base, "identity.json", json.dumps(fx.identity_json(opengsd)))
    return ["--roadmap", str(base / "roadmap.json"), "--identity", str(base / "identity.json"),
            "--phase-op", str(_write_phase_ops(root, base, phases))]


def _write_phase_ops(root: Path, base: Path, phases: list) -> Path:
    ops = base / "ops"
    for number, doc in fx.phase_op_json(root / "repo", phases).items():
        fx.write(ops, f"{number}.json", json.dumps(doc))
    return ops


def run_scenario(scn: Scenario, root: Path) -> tuple[Outcome, Any, Any, list[str], Path]:
    """Build the project, detect, render once; returns the outcome, seams, parser, render argv
    and the repository."""
    repo = root / "repo"
    repo.mkdir()
    fx.git_init(repo)
    scn.project(repo)
    rows = scn.rows if scn.rows is not None else MATRIX_ROWS
    host = gp_host.HostSeams(run=FakeRun(host_routes(rows)),
                             which=lambda name: f"fake-bin/{name}", environ={})
    seams = goal_prompt.CliSeams(host=host, today=TODAY, home=fx.FAKE_HOME,
                                 secrets=(fx.SENTINEL_KEY,), skills_dir=_stand_in_skills(root))
    flags = list(scn.detect_args)
    if scn.captures is not None:
        flags += _capture_flags(root, *scn.captures)
    parser = goal_prompt.build_parser()
    detect_doc = goal_prompt.build_detect(
        parser.parse_args(["detect", "--repo", str(repo), *flags]), seams)
    detect_path = root / "detect.json"
    detect_path.write_text(json.dumps(detect_doc), encoding="utf-8")
    answers_path = root / "answers.json"
    answers_path.write_text(json.dumps(scn.answers), encoding="utf-8")
    render_argv = ["render", "--repo", str(repo), "--detect", str(detect_path),
                   "--answers", str(answers_path)]
    payload = goal_prompt.run_render(parser.parse_args(render_argv), seams)
    text = (repo / payload["path"]).read_text(encoding="utf-8")
    return Outcome(detect_doc, payload, text), seams, parser, render_argv, repo


# ─── text helpers (the property checks read the generated text, not the code) ─────────


def _sections_of(lines: list[str]) -> dict[str, list[str]]:
    """Lines under each labeled heading; a fence, the shared marker or a new `## ` ends one."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in lines:
        if line in HEADINGS:
            current = line
            sections.setdefault(line, [])
        elif line == FENCE or line.startswith("## "):
            current = None
        elif current is not None:
            sections[current].append(line)
    return sections


def _blocks(text: str) -> list[list[str]]:
    """Each fenced block's lines WITHOUT the fence lines."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if line == FENCE:
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
        elif current is not None:
            current.append(line)
    return blocks


def _rails(text: str) -> list[str]:
    """Lines of the shared `## Rails` section, [] when the file has none."""
    lines = text.split("\n")
    return lines[lines.index(SHARED) + 1:] if SHARED in lines else []


def _upstream_flags(block_with_fences: list[str]) -> dict[str, Any]:
    """The workflow's own extraction (autonomous.md lines 27-58), with the fence lines included:
    grep -oE then awk '{print $2}' keeps the last match; ONLY also sets FROM."""
    values: dict[str, str] = {}
    for name, pattern in UPSTREAM.items():
        matches = [m.group(0).split()[1] for line in block_with_fences
                   for m in pattern.finditer(line)]
        values[name] = matches[-1] if matches else ""
    if values["only"]:
        values["from"] = values["only"]
    converge = any(CONVERGE.search(line) for line in block_with_fences)
    return {**values, "converge": converge}


def _rule_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if line.strip() and line not in HEADINGS and line != SHARED]


def _expected_headings(scn: Scenario) -> tuple[str, ...]:
    return HEADINGS if scn.order else tuple(h for h in HEADINGS if h != "ORDER")


def _section_text(text: str, name: str) -> str:
    lines = text.split("\n")
    return "\n".join(_sections_of(lines).get(name, []))


def _quota_text(text: str) -> str:
    return _section_text(text, "QUOTA")


def _without_quota(text: str) -> str:
    kept: list[str] = []
    skipping = False
    for line in text.split("\n"):
        if line in HEADINGS:
            skipping = line == "QUOTA"
        if line == FENCE or line.startswith("## "):
            skipping = False
        if not skipping:
            kept.append(line)
    return "\n".join(kept)


class TestPropertySweep(unittest.TestCase):
    """Every scenario satisfies every generated-text property (SPEC acceptance 3, 4, 8)."""

    def test_every_scenario(self):
        for scn in SCENARIOS:
            with self.subTest(scenario=scn.name), tempfile.TemporaryDirectory() as tmp:
                self._check(scn, Path(tmp))

    def _check(self, scn: Scenario, root: Path) -> None:
        outcome, seams, parser, render_argv, repo = run_scenario(scn, root)
        text = outcome.text
        self.assertNotIn("--no-verify", text)
        self.assertNotIn("§§", text)
        self.assertNotIn(fx.FAKE_HOME, text)
        self.assertNotIn(str(root), text)
        self.assertNotIn(fx.SENTINEL_KEY, text)
        self.assertEqual(gp_common.scan_text(text, home=fx.FAKE_HOME,
                                             secrets=(fx.SENTINEL_KEY,)), [])
        self.assertFalse(re.search(r"(?:^|[\s`(])/[\w.-]+/", text), "absolute path in text")
        self.assertFalse(Path(outcome.payload["path"]).is_absolute())
        self.assertNotIn("..", outcome.payload["path"].split("/"))
        self._check_conditions(text)
        self._check_headings(scn, text)
        self._check_jev(text)
        self._check_blocks(scn, text)
        self._check_budgets(text)
        self._check_quota(text)
        self._check_done_when(outcome.detect, text)
        self._check_second_render(seams, parser, render_argv, repo, outcome.payload["path"], text)

    def _check_conditions(self, text: str) -> None:
        for line in text.split("\n"):
            if line.startswith(gp_render.GOAL_PREFIX):
                self.assertLessEqual(len(line[len(gp_render.GOAL_PREFIX):]), gp_render.GOAL_CAP)

    def _check_headings(self, scn: Scenario, text: str) -> None:
        present = set(text.split("\n"))
        for heading in _expected_headings(scn):
            self.assertIn(heading, present, f"heading missing: {heading}")

    def _check_jev(self, text: str) -> None:
        section = None
        for line in text.split("\n"):
            if line in HEADINGS:
                section = line
            elif line == FENCE or line.startswith("## "):
                section = None
            if re.search(r"\bjev", line, re.IGNORECASE):
                self.assertIn("advisory", line.lower(), f"jev line without advisory: {line}")
                self.assertNotIn(section, ("DONE WHEN", "STOP IF"))

    def _check_blocks(self, scn: Scenario, text: str) -> None:
        for block in _blocks(text):
            if not block or not block[0].startswith("/gsd-autonomous"):
                continue
            self.assertRegex(block[0], FLAGS_LINE)
            self.assertFalse(any(re.search(r"--[a-zA-Z]", line) for line in block[1:]))
            rules = _rule_lines(block[1:])
            self.assertLessEqual(len(rules), gp_render.RULE_CAP)
            self.assertTrue(all(len(line) <= gp_render.LINE_CAP for line in rules))
            if scn.upstream is not None:
                flags = _upstream_flags([FENCE, *block, FENCE])
                self.assertEqual(flags["converge"], True)
                self.assertEqual({k: flags[k] for k in ("from", "to", "only")}, scn.upstream)
        rails = _rails(text)
        if rails:
            rules = _rule_lines(rails)
            self.assertLessEqual(len(rules), gp_render.RULE_CAP)
            self.assertTrue(all(len(line) <= gp_render.LINE_CAP for line in rules))

    def _check_budgets(self, text: str) -> None:
        head = text.split(gp_render.OPEN_MARKER)[0]
        title, _, rest = head.partition("\n")
        wrapper = (rest if title.startswith("# ") else head).strip()
        sentences = re.split(r"(?<=[.!?])\s+", wrapper) if wrapper else []
        self.assertLessEqual(len(sentences), gp_render.WRAPPER_SENTENCES)
        self.assertLessEqual(len(wrapper), gp_render.WRAPPER_SHARE * len(text))

    def _check_quota(self, text: str) -> None:
        stripped = [line.lstrip("- ").strip() for line in text.split("\n")]
        self.assertTrue(any(line.startswith("A. This session") for line in stripped))
        self.assertTrue(any(line.startswith("B. Cross-AI children") for line in stripped))

    def _check_done_when(self, detect: dict, text: str) -> None:
        commands = [c["command"] for c in detect["e2e"]["commands"]]
        groups = [_sections_of(block).get("DONE WHEN", []) for block in _blocks(text)]
        groups.append(_sections_of(_rails(text)).get("DONE WHEN", []))
        done_groups = [group for group in groups if group]
        for group in done_groups:
            self.assertIn(UNIT, " ".join(group))
            for command in commands:
                self.assertIn(command, " ".join(group))

    def _check_second_render(self, seams, parser, render_argv, repo, first_path, first_text):
        payload = goal_prompt.run_render(parser.parse_args(render_argv), seams)
        self.assertTrue(payload["path"].endswith("-2.md"), payload["path"])
        self.assertEqual((repo / first_path).read_text(encoding="utf-8"), first_text)


class TestConditionBoundary(unittest.TestCase):
    def test_4000_code_points_pass_and_4001_fail(self):
        gp_render.check_condition("x" * gp_render.GOAL_CAP)
        with self.assertRaises(gp_common.GuardError):
            gp_render.check_condition("x" * (gp_render.GOAL_CAP + 1))


class TestGolden(unittest.TestCase):
    def test_recommended_opengsd_matches_the_committed_golden(self):
        with tempfile.TemporaryDirectory() as tmp:
            outcome, _, _, _, _ = run_scenario(SCENARIOS[0], Path(tmp))
        if os.environ.get("UPDATE_GOLDEN") == "1":
            GOLDEN.parent.mkdir(parents=True, exist_ok=True)
            GOLDEN.write_text(outcome.text, encoding="utf-8")
        self.assertEqual(
            GOLDEN.read_text(encoding="utf-8"), outcome.text,
            "golden drift; regenerate with: UPDATE_GOLDEN=1 "
            "python3 -m unittest tests.test_ai_kit_spec_goal_prompt_golden",
        )


class TestRuleParity(unittest.TestCase):
    """The generated QUOTA text satisfies Phase 26's R18 and R19 through check_rules (D-22)."""

    RULES = tuple(r for r in agent_rules.RULES if r["id"] in ("R18", "R19"))
    PRESENCE = {"opengsd": "ok"}

    def _statuses(self, text: str) -> dict[str, str]:
        findings = check_rules(text, self.PRESENCE, self.RULES, include_present=True)
        return {finding["id"]: finding["status"] for finding in findings}

    def test_opengsd_quota_text_makes_r18_and_r19_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            outcome, _, _, _, _ = run_scenario(SCENARIOS[0], Path(tmp))
        self.assertEqual(self._statuses(_quota_text(outcome.text)),
                         {"R18": "present", "R19": "present"})

    def test_without_the_quota_section_both_rules_are_missing_or_near_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            outcome, _, _, _, _ = run_scenario(SCENARIOS[0], Path(tmp))
        statuses = self._statuses(_without_quota(outcome.text))
        self.assertEqual(set(statuses), {"R18", "R19"})
        for rule_id, status in statuses.items():
            with self.subTest(rule=rule_id):
                self.assertIn(status, ("missing", "near_miss"))

    def test_shared_rails_quota_satisfies_both_rules(self):
        scn = next(s for s in SCENARIOS if s.name == "superpowers-chain")
        with tempfile.TemporaryDirectory() as tmp:
            outcome, _, _, _, _ = run_scenario(scn, Path(tmp))
        self.assertIn(SHARED, outcome.text.split("\n"))
        self.assertEqual(self._statuses(_quota_text(outcome.text)),
                         {"R18": "present", "R19": "present"})


class TestReadinessWarnings(unittest.TestCase):
    def test_readiness_problems_are_stdout_warnings_and_never_file_text(self):
        scn = next(s for s in SCENARIOS if s.name == "opengsd-readiness-failed")
        with tempfile.TemporaryDirectory() as tmp:
            outcome, _, _, _, _ = run_scenario(scn, Path(tmp))
        self.assertTrue(outcome.payload["warnings"])
        self.assertTrue(all(w.startswith("cross-AI readiness failed: ")
                            for w in outcome.payload["warnings"]))
        self.assertNotIn("cross-AI readiness failed", outcome.text)


if __name__ == "__main__":
    unittest.main()
