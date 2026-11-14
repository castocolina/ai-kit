"""tools/judge_loop.py: the judge prompt, lane ingest and the record checker.

Every test builds its own fixture skill-judge package and git repository in a temp dir;
no test reads the installed skill-judge, a host CLI or the repo's .planning/.
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("judge_loop", REPO_ROOT / "tools" / "judge_loop.py")
assert _SPEC is not None and _SPEC.loader is not None
judge_loop = importlib.util.module_from_spec(_SPEC)
sys.modules["judge_loop"] = judge_loop
_SPEC.loader.exec_module(judge_loop)

DIMS = judge_loop.DIMS
HAS_GIT = shutil.which("git") is not None
SHA_A = "a" * 40
STATUS_OK = ("AIKIT-XAI status=ok cli=cli-a model=model-a exit=0 cli_rc=0 elapsed=1s out=1 "
             "tree=clean")


def _git_env(base):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_CEILING_DIRECTORIES"] = str(base)
    return env


def _git(repo, env, *args):
    argv = ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid",
            "-c", "commit.gpgsign=false", "-c", f"core.hooksPath={os.devnull}", "-C", str(repo)]
    proc = subprocess.run([*argv, *args], env=env, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"git {args} failed: {proc.stderr}")
    return proc.stdout


def make_package(base):
    """A fixture skill-judge: rubric pin v4 and spec_sha of 40 a, two cited spec files."""
    pkg = Path(base) / "skill-judge"
    (pkg / "references" / "agentskills").mkdir(parents=True)
    (pkg / "SKILL.md").write_text("# skill-judge fixture\n", encoding="utf-8")
    (pkg / "references" / "rubric.md").write_text(
        f"rubric_version: 4\nspec_sha: {SHA_A}\n\n"
        "| Dim | Name | Max | Source |\n|---|---|---|---|\n"
        "| D1 | One | 20 | references/agentskills/alpha.md#one; "
        "references/agentskills/beta.md#two |\n"
        "| D2 | Two | 15 | references/agentskills/alpha.md#three |\n", encoding="utf-8")
    (pkg / "references" / "agentskills" / "alpha.md").write_text("alpha spec\n", encoding="utf-8")
    (pkg / "references" / "agentskills" / "beta.md").write_text("beta spec\n", encoding="utf-8")
    (pkg / "references" / "verdict.schema.json").write_text("{}\n", encoding="utf-8")
    return pkg


def make_repo(base, files):
    """A committed git repository holding `files` (rel path -> text) on branch main."""
    repo = Path(base) / "repo"
    repo.mkdir(parents=True)
    env = _git_env(base)
    _git(repo, env, "init", "-q", "-b", "main")
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-q", "-m", "fixture")
    return repo


def commit_change(repo, rel, text):
    """Rewrite one tracked file and commit it, so the skill digest moves."""
    env = _git_env(repo.parent)
    (repo / rel).write_text(text, encoding="utf-8")
    _git(repo, env, "add", "--", rel)
    _git(repo, env, "commit", "-q", "-m", f"change {rel}")


def make_verdict(skill, judge, drops=None, maxima=None):
    """A rubric-v4 verdict; `drops` maps a dimension to (points lost, severity)."""
    maxima = maxima or {"D1": 20, **{d: 15 for d in DIMS[1:]}}
    drops = drops or {}
    scores, findings = {}, []
    for dim in DIMS:
        lost, severity = drops.get(dim, (0, None))
        scores[dim] = maxima[dim] - lost
        assert scores[dim] >= 0, f"a drop larger than {dim}'s maximum is a test bug"
        if lost:
            findings.append({"id": f"F{len(findings) + 1}", "dimension": dim,
                             "severity": severity, "file": f"skills/{skill}/SKILL.md",
                             "line": 1, "evidence": "fixture evidence", "fix": "fixture fix"})
    total, max_total = sum(scores.values()), sum(maxima.values())
    pct = round(total / max_total * 100, 1)
    return {"skill": skill, "judge": judge, "rubric_version": 4, "spec_sha": SHA_A,
            "scores": scores, "max": maxima, "total": total, "max_total": max_total,
            "percent": pct, "grade": judge_loop.grade_of(pct), "findings": findings}


def bar_rec(judge, pct, high=False):
    """A minimal scored record for the bar: one judge's percent, with one high finding if asked."""
    findings = [{"id": "F1", "severity": "high"}] if high else []
    return {"skill": "demo-a", "round": 1, "judge": judge,
            "verdict": {"percent": pct, "findings": findings}}


def prior_at(pct):
    """A prior loop's round state holding one valid verdict at `pct`, as loop 32."""
    return "32", {"valid": [bar_rec("p", pct)]}


def write_lane(lane_dir, status_line, out_text):
    """A lane folder: stderr with the status line, stdout with the verdict text."""
    lane = Path(lane_dir)
    lane.mkdir(parents=True, exist_ok=True)
    (lane / "lane.err").write_text((status_line + "\n") if status_line else "", encoding="utf-8")
    (lane / "lane.out").write_text(out_text, encoding="utf-8")
    return lane


SKILL_REPO_FILES = {
    "skills/demo-alpha/SKILL.md": "# demo-alpha\n",
    "skills/demo-alpha/scripts/run.py": "print('run')\n",
    "tests/test_alpha.py": 'SKILL = "demo-alpha"\n',
    "skills/demo-beta/SKILL.md": "# demo-beta\n",
    "skills/demo-beta/references/note.md": "a note\n",
    "tests/test_beta.py": 'SKILL = "demo-beta"\n',
    "skills/demo-beta-fixer/SKILL.md": "# demo-beta-fixer\n",
    "skills/demo-gamma/SKILL.md": "# demo-gamma\n",
    "skills/demo-gamma/demo_gamma.py": "print('gamma')\n",
    "skills/demo-delta/SKILL.md": "# demo-delta\n",
    "skills/demo-delta/scripts/template.py.txt": "print('template')\n",
    "skills/demo-eps/SKILL.md": "# demo-eps\n",
    "skills/demo-eps/pkg/__init__.py": "\n",
}


def run_main(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = judge_loop.main(argv)
    return code, out.getvalue()


ANSWER = "AIKIT-SENTINEL-0a1b2c3d-4e5f6a7b-8c9d0e1f"
NATIVE = "native:fixture"


def _status(status="ok", exit_code=0, tree="clean"):
    return (f"AIKIT-XAI status={status} cli=cli-a model=m exit={exit_code} cli_rc=0 elapsed=1s "
            f"out=1 tree={tree}")


def write_probe(probe_dir, judge, token, out_text, status_line):
    """A probe lane folder: the expected answer, then the lane's stdout and stderr."""
    lane = Path(probe_dir) / judge_loop.judge_slug(judge)
    lane.mkdir(parents=True, exist_ok=True)
    (lane / "token").write_text(token + "\n", encoding="utf-8")
    return write_lane(lane, status_line, out_text)


@unittest.skipUnless(HAS_GIT, "git not installed")
class TestTracer(unittest.TestCase):
    """One skill, one judge, end to end: prompt, fixture lane, ingest, check."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="judge-loop-test-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.pkg = make_package(self.base)
        self.repo = make_repo(self.base, {
            "skills/demo-alpha/SKILL.md": "# demo-alpha\n",
            "skills/demo-alpha/scripts/run.py": "print('run')\n",
            "tests/test_alpha.py": 'SKILL = "demo-alpha"\n',
        })
        self.lanes = self.base / "lanes"
        self.records = self.base / "rec"
        inputs = {"schema": 1, "skills": {"demo-alpha": {
            "batch": "32.1", "last_v4": None, "old_score": None}}, "excluded": {}}
        pool = judge_loop.choose_pool(["cli-a:model-a"], NATIVE, [
            {"judge": "cli-a:model-a", "usable": True, "status_line": STATUS_OK, "reason": ""}])
        count = judge_loop.count_skill(self.repo, "demo-alpha", inputs["skills"]["demo-alpha"],
                                       None)
        write_records(self.records, inputs, {"32": {"pool": pool,
                                                    "counts": {"demo-alpha": count}}}, [])

    def _report(self):
        code, _out = run_main(["--root", str(self.repo), "report", str(self.records)])
        self.assertEqual(code, 0)

    def _prompt(self, judge="cli-a:model-a"):
        return run_main(["--root", str(self.repo), "prompt", "--loop", "32", "--round", "1",
                         "--judge", judge, "--skill", "demo-alpha", "--out", str(self.lanes),
                         "--judge-package", str(self.pkg)])

    def _lane(self):
        return self.lanes / "32" / "demo-alpha" / "r1" / "cli-a_model-a"

    def _verdict_line(self):
        return json.dumps(make_verdict("demo-alpha", "cli-a:model-a"))

    def test_prompt_writes_prompt_and_manifest(self):
        code, _out = self._prompt()
        self.assertEqual(code, 0)
        self.assertTrue((self._lane() / "prompt.md").is_file())
        manifest = json.loads((self._lane() / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["judge"], "cli-a:model-a")
        self.assertEqual((manifest["rubric_version"], manifest["spec_sha"]), (4, SHA_A))
        self.assertEqual(manifest["modules"], ["tests/test_alpha.py"])

    def test_ingest_records_the_lane_and_check_prints_the_current_line(self):
        self._prompt()
        write_lane(self._lane(), STATUS_OK, self._verdict_line() + "\n")
        code, _out = run_main(["--root", str(self.repo), "ingest", "--lane-dir",
                               str(self._lane()), "--records", str(self.records)])
        self.assertEqual(code, 0)
        record_file = self.records / "verdicts" / "32" / "demo-alpha" / "r1" / "cli-a_model-a.json"
        record = json.loads(record_file.read_text(encoding="utf-8"))
        self.assertEqual(record["verdict"], make_verdict("demo-alpha", "cli-a:model-a"))
        self.assertEqual(len(record["attempts"]), 1)
        self.assertEqual(record["attempts"][0]["status_line"], STATUS_OK)
        self._report()
        code, out = run_main(["--root", str(self.repo), "check", str(self.records),
                              "--skills", "demo-alpha", "--judges", "cli-a:model-a"])
        self.assertEqual(code, 0)
        self.assertIn("judge-loop: demo-alpha: loop 32 round 1 (rounds 1); judges cli-a:model-a; "
                      "worst 100.0 A; critical 0; high 0; bar met: no critical or high finding; "
                      "digest current", out)

    def test_check_reports_stale_digest_after_a_skill_edit(self):
        self._prompt()
        write_lane(self._lane(), STATUS_OK, self._verdict_line() + "\n")
        run_main(["--root", str(self.repo), "ingest", "--lane-dir", str(self._lane()),
                  "--records", str(self.records)])
        commit_change(self.repo, "skills/demo-alpha/SKILL.md", "# demo-alpha changed\n")
        self._report()
        code, out = run_main(["--root", str(self.repo), "check", str(self.records),
                              "--skills", "demo-alpha", "--judges", "cli-a:model-a"])
        self.assertEqual(code, 0)
        self.assertIn("digest stale", out)

    def test_check_rejects_a_judge_that_is_not_in_the_list(self):
        self._prompt()
        write_lane(self._lane(), STATUS_OK, self._verdict_line() + "\n")
        run_main(["--root", str(self.repo), "ingest", "--lane-dir", str(self._lane()),
                  "--records", str(self.records)])
        self._report()
        code, out = run_main(["--root", str(self.repo), "check", str(self.records),
                              "--skills", "demo-alpha", "--judges", "cli-b:model-b"])
        self.assertEqual(code, 1)
        self.assertIn("judge cli-a:model-a is not in the judge list", out)


BIG = {dim: 125 for dim in DIMS}
DET_TWO = {"count": 2, "reasons": ["no rubric-v4 verdict"], "last_v4": None,
           "jev": {"asked": False, "item": None, "level": None,
                   "note": "not asked (deterministic two)"}}
DEMO_SKILLS = ("demo-a", "demo-b", "demo-c")
QUOTA_LINE = ("AIKIT-XAI status=quota cli=cli-a model=model-a exit=75 cli_rc=1 elapsed=1s "
              "out=0 tree=clean")


def full_verdict(skill, judge):
    """A rubric-v4 verdict with every score at its maximum and no findings (grade A)."""
    return make_verdict(skill, judge)


def make_record(loop, skill, rnd, judge, verdict, digest="0" * 64, status_line=STATUS_OK,
                note=None, substitute=None):
    """A record as ingest writes it; a None verdict is one failed attempt and no verdict."""
    ok = verdict is not None
    attempt = {"status_line": status_line, "note": note, "lane_ok": ok,
               "verdict_line": json.dumps(verdict) if ok else None,
               "error": None if ok else "lane is not usable"}
    return {"schema": 1, "loop": loop, "skill": skill, "round": rnd, "judge": judge,
            "digest": digest, "rubric_version": 4, "spec_sha": SHA_A, "embedded": [],
            "modules": ["tests/test_alpha.py"], "ships_code": False,
            "prompt_sha256": "0" * 64, "substitute": substitute, "attempts": [attempt],
            "verdict": verdict}


def write_records(records, inputs, loops, recs, refutations=None):
    """Write inputs.json, loops/<loop>.json, each record at its path and the refutation files."""
    records = Path(records)
    judge_loop.atomic_write_json(records / "inputs.json", inputs)
    for loop, data in loops.items():
        judge_loop.atomic_write_json(records / "loops" / f"{loop}.json", data)
    for record in recs:
        judge_loop.atomic_write_json(judge_loop.record_path(
            records, record["loop"], record["skill"], record["round"], record["judge"]), record)
    for loop, entries in (refutations or {}).items():
        judge_loop.atomic_write_json(records / "refutations" / f"{loop}.json", entries)


def demo_inputs():
    return {"schema": 1, "skills": {
        "demo-a": {"batch": "32.1", "last_v4": None,
                   "old_score": {"value": "106/120 (88.3%)", "source": "fixture"}},
        "demo-c": {"batch": "32.1", "last_v4": None, "old_score": None},
        "demo-b": {"batch": "32.2", "last_v4": None, "old_score": None}},
        "excluded": {"zz-rules": "fixture reason", "aa-fold": "fixture reason"}}


def demo_pool(judges=("cli-a:model-a", "cli-b:model-b")):
    probes = [{"judge": j, "usable": True, "status_line": STATUS_OK, "reason": ""}
              for j in judges]
    return judge_loop.choose_pool(list(judges), NATIVE, probes)


@unittest.skipUnless(HAS_GIT, "git not installed")
class ReportFixture(unittest.TestCase):
    """Three demo skills in a git repo and the loop 32 records: demo-a (84.0 and 80.0 with a
    high), demo-b (one full verdict), demo-c (one failed attempt, no verdict)."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="judge-loop-report-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        files = {f"skills/{n}/SKILL.md": "demo\n" for n in DEMO_SKILLS}
        files["tests/test_demo.py"] = 'SKILLS = ("demo-a", "demo-b")\n'
        self.repo = make_repo(self.base, files)
        self.records = self.base / "rec"
        recs = [
            make_record("32", "demo-a", 1, "cli-a:model-a",
                        make_verdict("demo-a", "cli-a:model-a", drops={"D1": (20, "medium")})),
            make_record("32", "demo-a", 1, "cli-b:model-b",
                        make_verdict("demo-a", "cli-b:model-b",
                                     drops={"D1": (20, "high"), "D2": (5, "medium")})),
            make_record("32", "demo-b", 1, "cli-a:model-a",
                        full_verdict("demo-b", "cli-a:model-a")),
            make_record("32", "demo-c", 1, "cli-a:model-a", None, status_line=QUOTA_LINE),
        ]
        loops = {"32": {"pool": demo_pool(), "counts": {n: DET_TWO for n in DEMO_SKILLS}}}
        write_records(self.records, demo_inputs(), loops, recs)

    def _render(self):
        return judge_loop.render_report(self.records)

    def _report(self):
        return run_main(["--root", str(self.repo), "report", str(self.records)])

    def _check(self, *args):
        return run_main(["--root", str(self.repo), "check", str(self.records), *args])

    def _put(self, record):
        judge_loop.atomic_write_json(judge_loop.record_path(
            self.records, record["loop"], record["skill"], record["round"], record["judge"]),
            record)

    def _drop(self, skill, judge, rnd=1):
        os.remove(judge_loop.record_path(self.records, "32", skill, rnd, judge))

    def _loop_file(self, loop="32"):
        return self.records / "loops" / f"{loop}.json"

    def _edit_loop(self, edit, loop="32"):
        path = self._loop_file(loop)
        data = json.loads(path.read_text(encoding="utf-8"))
        edit(data)
        judge_loop.atomic_write_json(path, data)


class TestReport(ReportFixture):
    def test_judged_rows_bar_cells_history_and_pin(self):
        text = self._render()
        self.assertIn("| demo-a | 32.1 | 32 | 1 | 1 | 2 | 2: no rubric-v4 verdict | 80.0 | B | 0 | "
                      "1 | 0 | met: grade B or better | 4.0 | 000000000000 |", text)
        self.assertIn("| demo-b | 32.2 | 32 | 1 | 1 | 1 (second judge unavailable) | "
                      "2: no rubric-v4 verdict | 100.0 | A | 0 | 0 | 0 | "
                      "met: no critical or high finding | - | 000000000000 |", text)
        self.assertIn("| demo-c | 32.1 | 32 | 1 | 1 | 0 | 2: no rubric-v4 verdict | - | - | - | - "
                      "| 0 | not judged | - | - |", text)
        self.assertLess(text.index("| demo-a | 32.1"), text.index("| demo-c | 32.1"))
        self.assertLess(text.index("| demo-c | 32.1"), text.index("| demo-b | 32.2"))
        self.assertIn("| demo-c | 32 | 1 | cli-a:model-a | " + QUOTA_LINE
                      + "; error: lane is not usable | - | not judged |", text)
        self.assertGreater(text.index("106/120 (88.3%)"),
                           text.index("## History: last 120-point results"))
        self.assertIn("Rubric: loop 32: version 4, spec_sha " + SHA_A, text)
        self.assertIn("is its base for the batch phases' regression check", text)
        self.assertLess(text.index("| aa-fold |"), text.index("| zz-rules |"))
        self.assertIn("Members: cli-a:model-a, cli-b:model-b", text)
        self.assertIn("| 105/125 | 84.0 | B | 0 | 0 |", text)

    def test_rendering_twice_gives_identical_bytes(self):
        self.assertEqual(self._render(), self._render())

    def test_a_worst_judge_at_79_9_with_a_high_finding_is_not_met(self):
        self._put(make_record("32", "demo-a", 1, "cli-b:model-b",
                              make_verdict("demo-a", "cli-b:model-b",
                                           drops={"D1": (125, "high"), "D2": (76, "medium")},
                                           maxima=BIG)))
        self.assertIn("| demo-a | 32.1 | 32 | 1 | 1 | 2 | 2: no rubric-v4 verdict | 79.9 | C | 0 | "
                      "1 | 0 | not met | 4.1 | 000000000000 |", self._render())

    def test_a_native_substitute_has_its_row_and_wins_no_tie(self):
        self._drop("demo-a", "cli-b:model-b")
        self._put(make_record("32", "demo-a", 1, "cli-a:model-a",
                              full_verdict("demo-a", "cli-a:model-a")))
        self._put(make_record("32", "demo-a", 1, "native:fixture",
                              full_verdict("demo-a", "native:fixture"),
                              substitute={"replaces": "cli-b:model-b",
                                          "reason": "cli-b lane hit its quota"}))
        text = self._render()
        self.assertEqual(judge_loop._last_round(self.records, "demo-a")["worst"]["judge"],
                         "cli-a:model-a")
        self.assertIn("replaces cli-b:model-b: cli-b lane hit its quota", text)
        self.assertLess(text.index("| demo-a | 32 | 1 | cli-a:model-a |"),
                        text.index("| demo-a | 32 | 1 | native:fixture |"))
        self.assertIn("| demo-a | 32.1 | 32 | 1 | 1 | 2 | 2: no rubric-v4 verdict | 100.0 | A | 0 "
                      "| 0 | 0 | met: no critical or high finding | 0.0 | 000000000000 |", text)
        order = judge_loop.judge_order
        self.assertEqual(order(demo_pool(), ["native:fixture", "cli-a:model-a"]),
                         ["cli-a:model-a", "cli-b:model-b", "native:fixture"])
        self.assertEqual(order({}, ["z:m", "a:m"]), ["a:m", "z:m"])
        self._report()
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a",
                                "cli-b:model-b", "native:fixture")
        self.assertEqual(code, 0, out)

    def test_a_missing_count_record_raises_the_named_error(self):
        self._edit_loop(lambda data: data["counts"].pop("demo-a"))
        with self.assertRaises(judge_loop.JudgeLoopError) as caught:
            self._render()
        self.assertEqual(str(caught.exception), "demo-a: no count record in loops/32.json")

    def test_an_input_skill_with_no_verdict_folder_raises_the_named_error(self):
        inputs = demo_inputs()
        inputs["skills"]["demo-d"] = {"batch": "32.3", "last_v4": None, "old_score": None}
        judge_loop.atomic_write_json(self.records / "inputs.json", inputs)
        with self.assertRaises(judge_loop.JudgeLoopError) as caught:
            self._render()
        self.assertEqual(str(caught.exception), "demo-d: no verdict records")


class TestEvalsAndTests(ReportFixture):
    def setUp(self):
        super().setUp()
        evals = self.repo / "skills" / "demo-a" / "evals"
        evals.mkdir(parents=True, exist_ok=True)
        (evals / "evals.json").write_text(
            json.dumps({"skill_name": "demo-a", "evals": [{"id": 1}, {"id": 2}, {"id": 3}]}),
            encoding="utf-8")
        self._write_queries("demo-a", [True, True, False, False])
        self._write_queries("demo-b", [True] * 16)
        inputs = demo_inputs()
        inputs["skills"]["demo-a"]["deferred"] = {"text": "Phase 98", "source": "fixture"}
        inputs["skills"]["demo-c"]["deferred"] = {"text": "Phase 99", "source": "fixture"}
        judge_loop.atomic_write_json(self.records / "inputs.json", inputs)

    def _write_queries(self, skill, flags):
        folder = self.repo / "skills" / skill / "evals"
        folder.mkdir(parents=True, exist_ok=True)
        queries = [{"query": f"q{i}", "should_trigger": flag}
                   for i, flag in enumerate(flags, start=1)]
        (folder / "trigger-queries.json").write_text(json.dumps(queries), encoding="utf-8")

    def test_report_writes_facts_and_the_section(self):
        code, out = self._report()
        self.assertEqual(code, 0, out)
        facts = json.loads((self.records / "facts.json").read_text(encoding="utf-8"))
        self.assertEqual(facts, {"schema": 1, "skills": {
            "demo-a": {"evals": 3, "queries": 4, "near_misses": 2,
                       "modules": ["tests/test_demo.py"]},
            "demo-b": {"evals": None, "queries": 16, "near_misses": 0,
                       "modules": ["tests/test_demo.py"]},
            "demo-c": {"evals": None, "queries": None, "near_misses": None, "modules": []}}})
        text = (self.records / judge_loop.REPORT_NAME).read_text(encoding="utf-8")
        self.assertIn("## Evals and tests", text)
        self.assertIn("| Skill | evals.json | Trigger queries | Near-misses | Test modules | "
                      "Brought to the bar by |", text)
        self.assertIn("| demo-a | 3 evals | 4 | 2 | 1 | - |", text)
        self.assertIn("| demo-c | none | none | none | 0 | Phase 99 |", text)
        self.assertIn("| demo-b | none | 16 | 0 | 1 | not named |", text)
        self.assertIn("- demo-a: tests/test_demo.py", text)
        self.assertIn("- demo-c: no script test found", text)
        self.assertLess(text.index("| demo-a | 3 evals"), text.index("| demo-c | none"))
        self.assertLess(text.index("| demo-c | none"), text.index("| demo-b | none"))
        section = text.split("## Evals and tests", 1)[1].split("\n## ", 1)[0]
        self.assertNotIn("aa-fold", section)
        self.assertNotIn("zz-rules", section)

    def test_render_is_byte_stable_and_check_passes(self):
        self._report()
        text = self._render()
        self.assertEqual(text, self._render())
        self.assertEqual((self.records / judge_loop.REPORT_NAME).read_text(encoding="utf-8"),
                         text)
        code, out = self._check("--skills", "demo-a", "demo-b", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 0, out)

    def test_without_facts_the_section_says_how_to_create_them(self):
        self.assertIn("No facts snapshot; run: python3 tools/judge_loop.py report <records>",
                      self._render())

    def test_a_malformed_deferred_entry_is_refused(self):
        inputs = demo_inputs()
        inputs["skills"]["demo-a"]["deferred"] = {"text": "", "source": "fixture"}
        judge_loop.atomic_write_json(self.records / "inputs.json", inputs)
        with self.assertRaises(judge_loop.JudgeLoopError) as caught:
            judge_loop.load_inputs(self.records)
        self.assertEqual(str(caught.exception),
                         "inputs.json: skill demo-a has a malformed deferred")

    def test_a_malformed_eval_file_fails_report_naming_its_path(self):
        (self.repo / "skills" / "demo-a" / "evals" / "evals.json").write_text(
            "{not json", encoding="utf-8")
        code, out = self._report()
        self.assertEqual(code, 1)
        self.assertIn("skills/demo-a/evals/evals.json", out)

    def test_a_tree_change_after_the_report_is_a_drift_note(self):
        self._report()
        self._write_queries("demo-b", [True] * 17)
        code, out = self._check("--skills", "demo-a", "demo-b", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 0, out)
        self.assertIn("demo-b: facts drift", out)

    def test_a_malformed_eval_file_fails_check_naming_its_path(self):
        self._report()
        (self.repo / "skills" / "demo-a" / "evals" / "trigger-queries.json").write_text(
            "{not json", encoding="utf-8")
        code, out = self._check("--skills", "demo-a", "demo-b", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 1)
        self.assertIn("skills/demo-a/evals/trigger-queries.json", out)

    def test_drift_is_computed_only_for_the_checked_skills(self):
        self._report()
        self._write_queries("demo-b", [True] * 17)
        _code, out = self._check("--skills", "demo-a")
        self.assertNotIn("demo-b: facts drift", out)


class TestCheck(ReportFixture):
    def test_defaults_take_the_pool_judges_and_the_native_id(self):
        self._drop("demo-a", "cli-b:model-b")
        self._put(make_record("32", "demo-a", 1, "cli-a:model-a",
                              full_verdict("demo-a", "cli-a:model-a")))
        self._put(make_record("32", "demo-a", 1, "native:fixture",
                              full_verdict("demo-a", "native:fixture"),
                              substitute={"replaces": "cli-b:model-b",
                                          "reason": "cli-b lane hit its quota"}))
        self._report()
        code, out = self._check("--skills", "demo-a")
        self.assertEqual(code, 0, out)
        self.assertIn("judges cli-a:model-a, native:fixture", out)

    def test_a_record_without_a_verdict_key_names_its_file(self):
        self._report()
        path = judge_loop.record_path(self.records, "32", "demo-a", 1, "cli-b:model-b")
        record = json.loads(path.read_text(encoding="utf-8"))
        del record["verdict"]
        judge_loop.atomic_write_json(path, record)
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 1)
        self.assertIn("cli-b_model-b.json: not a judge record (missing verdict)", out)
        self.assertNotIn("KeyError", out)

    def test_judge_strings_match_exactly_and_the_file_name_is_the_slug(self):
        self._put(make_record("32", "demo-a", 1, "Cli-A:model-a",
                              full_verdict("demo-a", "Cli-A:model-a")))
        self._report()
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 1)
        self.assertIn("judge Cli-A:model-a is not in the judge list", out)
        path = judge_loop.record_path(self.records, "32", "demo-b", 1, "cli-a:model-a")
        judge_loop.atomic_write_json(path.with_name("wrong.json"),
                                     make_record("32", "demo-b", 1, "cli-a:model-a",
                                                 full_verdict("demo-b", "cli-a:model-a")))
        code, out = self._check("--skills", "demo-b", "--judges", "cli-a:model-a")
        self.assertEqual(code, 1)
        self.assertIn("file wrong.json is not cli-a_model-a.json", out)

    def test_a_malformed_verdict_in_round_one_fails_a_three_round_skill(self):
        bad = make_verdict("demo-a", "cli-a:model-a", drops={"D1": (20, "medium")})
        bad["percent"] = 99.0
        self._put(make_record("32", "demo-a", 1, "cli-a:model-a", bad))
        for number in (2, 3):
            self._put(make_record("32", "demo-a", number, "cli-a:model-a",
                                  full_verdict("demo-a", "cli-a:model-a")))
        self._report()
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a")
        self.assertEqual(code, 1)
        self.assertIn("demo-a r1 cli-a:model-a: percent 99.0 != 84.0", out)

    def test_four_rounds_are_noted_then_fail_with_gate(self):
        for number in (2, 3, 4):
            self._put(make_record("32", "demo-a", number, "cli-a:model-a",
                                  full_verdict("demo-a", "cli-a:model-a")))
        self._report()
        judges = ("--judges", "cli-a:model-a", "cli-b:model-b")
        code, out = self._check("--skills", "demo-a", *judges)
        self.assertEqual(code, 0, out)
        self.assertIn("demo-a: loop 32 ran 4 rounds, over the cap of 3", out)
        self.assertIn("over the cap", out)
        code, out = self._check("--skills", "demo-a", *judges, "--gate")
        self.assertEqual(code, 1)

    def test_rounds_must_run_one_to_n_and_loops_count_apart(self):
        self._put(make_record("32", "demo-b", 3, "cli-a:model-a",
                              full_verdict("demo-b", "cli-a:model-a")))
        self._report()
        code, out = self._check("--skills", "demo-b", "--judges", "cli-a:model-a")
        self.assertEqual(code, 1)
        self.assertIn("demo-b: loop 32 rounds are not r1..r3", out)
        entry = judge_loop.with_base(demo_inputs()["skills"]["demo-a"], judge_loop.prior_base(
            self.repo, self.records, "demo-a", "32.1"))
        count = judge_loop.count_skill(self.repo, "demo-a", entry, None)
        loop_32_1 = {"pool": demo_pool(), "counts": {"demo-a": count}}
        judge_loop.atomic_write_json(self._loop_file("32.1"), loop_32_1)
        for number in (1, 2, 3):
            self._put(make_record("32.1", "demo-a", number, "cli-a:model-a",
                                  full_verdict("demo-a", "cli-a:model-a")))
        self._report()
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 0, out)
        self.assertIn("demo-a: loop 32.1 round 3 (rounds 3)", out)
        self.assertNotIn("over the cap", out)

    def test_worst_judge_decides_the_bar_and_gate_fails_it(self):
        self._put(make_record("32", "demo-a", 1, "cli-a:model-a",
                              make_verdict("demo-a", "cli-a:model-a",
                                           drops={"D1": (100, "medium")}, maxima=BIG)))
        self._put(make_record("32", "demo-a", 1, "cli-b:model-b",
                              make_verdict("demo-a", "cli-b:model-b",
                                           drops={"D1": (20, "high"), "D2": (7, "medium")})))
        self._report()
        judges = ("--judges", "cli-a:model-a", "cli-b:model-b")
        code, out = self._check("--skills", "demo-a", *judges)
        self.assertEqual(code, 0, out)
        self.assertIn("worst 78.4 C", out)
        self.assertIn("bar not met", out)
        code, out = self._check("--skills", "demo-a", *judges, "--gate")
        self.assertEqual(code, 1)
        self.assertIn("demo-a: bar not met", out)

    def test_a_refutation_counts_only_when_complete(self):
        self._put(make_record("32", "demo-a", 1, "cli-b:model-b",
                              make_verdict("demo-a", "cli-b:model-b",
                                           drops={"D1": (125, "high"), "D2": (76, "medium")},
                                           maxima=BIG)))
        entry = {"skill": "demo-a", "round": 1, "judge": "cli-b:model-b", "finding": "F1",
                 "location": "skills/demo-a/SKILL.md:1", "command": "python3 -c pass",
                 "output": "ok"}
        judges = ("--judges", "cli-a:model-a", "cli-b:model-b")
        self._report()
        code, out = self._check("--skills", "demo-a", *judges)
        self.assertIn("bar not met", out)
        incomplete = dict(entry)
        del incomplete["command"]
        judge_loop.atomic_write_json(self.records / "refutations" / "32.json", [incomplete])
        self._report()
        code, out = self._check("--skills", "demo-a", *judges)
        self.assertIn("bar not met", out)
        judge_loop.atomic_write_json(self.records / "refutations" / "32.json", [entry])
        self._report()
        code, out = self._check("--skills", "demo-a", *judges, "--gate")
        self.assertEqual(code, 0, out)
        self.assertIn("bar met: no critical or high finding", out)

    def test_a_refutation_needs_its_output_and_the_named_judges_own_finding(self):
        # cli-a holds F1 high and F2 medium (79.9); cli-b holds F1, F2, F3, all low (88.0).
        self._put(make_record("32", "demo-a", 1, "cli-a:model-a",
                              make_verdict("demo-a", "cli-a:model-a",
                                           drops={"D1": (125, "high"), "D2": (76, "medium")},
                                           maxima=BIG)))
        self._put(make_record("32", "demo-a", 1, "cli-b:model-b",
                              make_verdict("demo-a", "cli-b:model-b",
                                           drops={"D2": (5, "low"), "D3": (5, "low"),
                                                  "D4": (5, "low")})))
        entry = {"skill": "demo-a", "round": 1, "judge": "cli-a:model-a", "finding": "F1",
                 "location": "skills/demo-a/SKILL.md:1", "command": "python3 -c pass",
                 "output": "ok"}
        judges = ("--judges", "cli-a:model-a", "cli-b:model-b")
        no_output = {key: value for key, value in entry.items() if key != "output"}
        other_judges_id = dict(entry, finding="F3")
        same_id_other_judge = dict(entry, judge="cli-b:model-b")
        for entries in ([no_output], [other_judges_id], [same_id_other_judge]):
            judge_loop.atomic_write_json(self.records / "refutations" / "32.json", entries)
            self._report()
            code, out = self._check("--skills", "demo-a", *judges)
            self.assertEqual(code, 0, out)
            self.assertIn("bar not met", out, entries)
        judge_loop.atomic_write_json(self.records / "refutations" / "32.json", [entry])
        self._report()
        code, out = self._check("--skills", "demo-a", *judges)
        self.assertIn("bar met: no critical or high finding", out)

    def test_a_record_that_is_not_a_json_object_names_its_file(self):
        self._report()
        path = judge_loop.record_path(self.records, "32", "demo-a", 1, "cli-b:model-b")
        path.write_text("[1, 2]\n", encoding="utf-8")
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 1)
        self.assertIn("cli-b_model-b.json: not a judge record (missing ", out)
        self.assertNotIn("Traceback", out)

    def test_a_record_field_of_the_wrong_type_names_its_file(self):
        self._report()
        path = judge_loop.record_path(self.records, "32", "demo-a", 1, "cli-b:model-b")
        record = json.loads(path.read_text(encoding="utf-8"))
        record["judge"], record["digest"] = 5, ["x"]
        judge_loop.atomic_write_json(path, record)
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 1)
        self.assertIn("cli-b_model-b.json: not a judge record (wrong type: judge, digest)", out)
        self.assertNotIn("Traceback", out)

    def test_a_non_object_attempt_and_a_pool_probe_without_judge_are_named(self):
        self._report()
        path = judge_loop.record_path(self.records, "32", "demo-a", 1, "cli-b:model-b")
        record = json.loads(path.read_text(encoding="utf-8"))
        record["attempts"] = ["x"]
        judge_loop.atomic_write_json(path, record)
        self._edit_loop(lambda data: data["pool"]["probes"][0].pop("judge"))
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 1)
        self.assertIn("not a judge record (wrong type: attempts item)", out)
        self.assertNotIn("Traceback", out)
        code, out = self._report()
        self.assertEqual(code, 1)
        self.assertIn("wrong type: attempts item", out)
        judge_loop.atomic_write_json(path, dict(record, attempts=[{"status_line": STATUS_OK}]))
        code, out = self._report()
        self.assertEqual(code, 1)
        self.assertIn("loops/32.json: a pool probe or substitute has no judge", out)

    def test_a_gate_failure_still_compares_the_report(self):
        self._report()
        (self.records / judge_loop.REPORT_NAME).write_text("edited\n", encoding="utf-8")
        code, out = self._check("--skills", "demo-c", "--judges", "cli-a:model-a", "--gate")
        self.assertEqual(code, 1)
        self.assertIn("REJUDGE.md differs from the records", out)

    def test_a_failed_write_leaves_no_temp_file(self):
        target = self.base / "out" / "x.json"
        with self.assertRaises(UnicodeEncodeError):
            judge_loop.atomic_write_text(target, "lone \udc80 surrogate")
        self.assertEqual(list(target.parent.iterdir()), [])

    def _check_edited_verdict(self, edit):
        self._report()
        path = judge_loop.record_path(self.records, "32", "demo-a", 1, "cli-b:model-b")
        record = json.loads(path.read_text(encoding="utf-8"))
        edit(record["verdict"])
        judge_loop.atomic_write_json(path, record)
        return self._check("--skills", "demo-a", "--judges", "cli-a:model-a", "cli-b:model-b")

    def test_a_verdict_without_findings_is_a_problem_not_an_exception(self):
        code, out = self._check_edited_verdict(lambda verdict: verdict.pop("findings"))
        self.assertEqual(code, 1)
        self.assertIn("demo-a r1 cli-b:model-b:", out)
        self.assertIn("REJUDGE.md not checked: demo-a: an invalid verdict in loop 32", out)
        self.assertNotIn("Traceback", out)

    def test_a_finding_without_severity_is_a_problem_not_an_exception(self):
        code, out = self._check_edited_verdict(
            lambda verdict: verdict["findings"][0].pop("severity"))
        self.assertEqual(code, 1)
        self.assertIn("demo-a r1 cli-b:model-b:", out)
        self.assertNotIn("Traceback", out)

    def test_report_refuses_an_invalid_verdict_without_a_traceback(self):
        path = judge_loop.record_path(self.records, "32", "demo-a", 1, "cli-b:model-b")
        record = json.loads(path.read_text(encoding="utf-8"))
        record["verdict"].pop("total")
        judge_loop.atomic_write_json(path, record)
        code, out = self._report()
        self.assertEqual(code, 1)
        self.assertIn("demo-a: an invalid verdict in loop 32; run check", out)
        self.assertFalse((self.records / judge_loop.REPORT_NAME).exists())

    def test_one_round_judging_two_skill_texts_is_a_problem(self):
        self._report()
        path = judge_loop.record_path(self.records, "32", "demo-a", 1, "cli-b:model-b")
        record = json.loads(path.read_text(encoding="utf-8"))
        record["digest"] = "1" * 64
        judge_loop.atomic_write_json(path, record)
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 1)
        self.assertIn("demo-a: loop 32 round 1 records judged different skill text", out)

    def test_a_corrupt_loop_file_is_a_named_problem(self):
        self._report()
        self._loop_file().write_text("{not json", encoding="utf-8")
        code, out = self._check("--skills", "demo-a")
        self.assertEqual(code, 1)
        self.assertIn("32.json: not valid JSON", out)
        self.assertNotIn("Traceback", out)

    def test_a_loop_file_without_a_pool_orders_judges_by_name(self):
        self.assertEqual(judge_loop.judge_order({}, ["cli-b:model-b", "cli-a:model-a"]),
                         ["cli-a:model-a", "cli-b:model-b"])
        self._edit_loop(lambda data: data.pop("pool"))
        self._report()
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 0, out)
        self.assertIn("judges cli-a:model-a, cli-b:model-b", out)

    def test_recorded_count_must_match_the_rule_and_its_inputs(self):
        self._edit_loop(lambda data: data["counts"]["demo-a"].update(count=1))
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a")
        self.assertEqual(code, 1)
        self.assertIn("demo-a: recorded count differs from the rule's output", out)
        self._edit_loop(lambda data: data["counts"]["demo-a"].update(
            count=2, last_v4={"percent": 88.0, "critical": 0, "high": 0, "judged_at": None,
                              "source": "fixture"}))
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a")
        self.assertIn("demo-a: count inputs differ from inputs.json", out)

    def test_a_missing_count_record_is_reported_as_not_checked(self):
        self._report()
        self._edit_loop(lambda data: data["counts"].pop("demo-a"))
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a")
        self.assertEqual(code, 1)
        self.assertIn("demo-a: no count record in loops/32.json", out)
        self.assertIn("REJUDGE.md not checked: demo-a: no count record in loops/32.json", out)

    def test_jev_level_two_count_round_trips(self):
        base = _git(self.repo, _git_env(self.base), "rev-parse", "HEAD").strip()
        commit_change(self.repo, "skills/demo-a/SKILL.md", "demo changed\n")
        entry = {"batch": "32.1", "old_score": None,
                 "last_v4": {"percent": 88.0, "critical": 0, "high": 0, "judged_at": base,
                             "source": "fixture"}}
        choice = judge_loop.JEV_LEVELS[2]

        def fake_ask(item):
            return {"items": {"judge-count": {"decided_by": "laya", "laya": {
                "choice": choice, "top": 0.9, "fallback": False, "forced": False,
                "model": "m"}}}}

        count = judge_loop.count_skill(self.repo, "demo-a", entry, fake_ask)
        self.assertEqual(count["count"], 2)
        inputs = demo_inputs()
        inputs["skills"]["demo-a"] = entry
        judge_loop.atomic_write_json(self.records / "inputs.json", inputs)
        self._edit_loop(lambda data: data["counts"].update({"demo-a": count}))
        self._put(make_record("32", "demo-a", 1, "cli-a:model-a",
                              full_verdict("demo-a", "cli-a:model-a")))
        self._put(make_record("32", "demo-a", 1, "cli-b:model-b",
                              full_verdict("demo-a", "cli-b:model-b")))
        self._report()
        code, out = self._check("--skills", "demo-a", "--judges", "cli-a:model-a",
                                "cli-b:model-b")
        self.assertEqual(code, 0, out)
        self.assertNotIn("recorded count differs", out)

    def test_not_judged_fails_until_a_verdict_exists(self):
        self._report()
        code, out = self._check("--skills", "demo-c", "--judges", "cli-a:model-a")
        self.assertEqual(code, 1)
        self.assertIn("demo-c: not judged (no verdict in loop 32 round 1)", out)
        self._put(make_record("32", "demo-c", 1, "cli-a:model-a",
                              full_verdict("demo-c", "cli-a:model-a")))
        self._report()
        code, out = self._check("--skills", "demo-c", "--judges", "cli-a:model-a")
        self.assertEqual(code, 0, out)
        self.assertNotIn("not judged", out)

    def test_digest_state_notes_stale_and_require_current_fails(self):
        judges = ("--judges", "cli-a:model-a", "cli-b:model-b")
        self._report()
        code, first = self._check("--skills", "demo-a", *judges)
        self.assertEqual(code, 0, first)
        self.assertIn("stale digest", first)
        _code, second = self._check("--skills", "demo-a", *judges)
        self.assertEqual(first, second)
        code, out = self._check("--skills", "demo-a", *judges, "--require-current")
        self.assertEqual(code, 1)
        self.assertIn("demo-a: stale digest", out)
        digest = judge_loop.skill_digest(self.repo, "demo-a")
        self._put(make_record("32", "demo-a", 1, "cli-a:model-a",
                              make_verdict("demo-a", "cli-a:model-a",
                                           drops={"D1": (20, "medium")}), digest=digest))
        self._put(make_record("32", "demo-a", 1, "cli-b:model-b",
                              make_verdict("demo-a", "cli-b:model-b",
                                           drops={"D1": (20, "high"), "D2": (5, "medium")}),
                              digest=digest))
        self._report()
        code, out = self._check("--skills", "demo-a", *judges, "--require-current")
        self.assertEqual(code, 0, out)
        self.assertIn("digest current", out)

    def test_a_listed_skill_without_tracked_files_is_a_problem(self):
        inputs = demo_inputs()
        inputs["skills"]["demo-x"] = {"batch": "32.1", "last_v4": None, "old_score": None}
        judge_loop.atomic_write_json(self.records / "inputs.json", inputs)
        self._edit_loop(lambda data: data["counts"].update({"demo-x": DET_TWO}))
        self._put(make_record("32", "demo-x", 1, "cli-a:model-a",
                              full_verdict("demo-x", "cli-a:model-a")))
        self._report()
        code, out = self._check("--skills", "demo-x", "--judges", "cli-a:model-a")
        self.assertEqual(code, 1)
        self.assertIn("no tracked files for skill demo-x", out)

    def test_the_checker_names_no_reviewer_instance(self):
        source = (REPO_ROOT / "tools" / "judge_loop.py").read_text(encoding="utf-8")
        self.assertNotIn("referee", source.lower())


class TestUsage(unittest.TestCase):
    def test_check_without_a_subcommand_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            judge_loop.main([])
        self.assertEqual(caught.exception.code, 2)

    def test_judge_slug_replaces_unsafe_characters(self):
        self.assertEqual(judge_loop.judge_slug("cli-a:model-a"), "cli-a_model-a")
        with self.assertRaises(judge_loop.JudgeLoopError):
            judge_loop.judge_slug("")


def make_skill_repo(base):
    """The fixture repository of the prompt and ingest tests (SKILL_REPO_FILES, committed)."""
    return make_repo(base, SKILL_REPO_FILES)


def prompt_for(repo, pkg, out, skill="demo-alpha", judge="cli-a:model-a", number=1):
    request = judge_loop.PromptRequest("32", number, judge, skill, Path(out))
    return judge_loop.write_lane_prompt(repo, pkg, request)


@unittest.skipUnless(HAS_GIT, "git not installed")
class TestPrompt(unittest.TestCase):
    """The judge prompt: embedded files, the two readings, the module list and the probe."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="judge-loop-test-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.pkg = make_package(self.base)
        self.repo = make_skill_repo(self.base)
        self.out = self.base / "lanes"

    def test_embeds_each_file_in_full_and_in_order(self):
        lane = prompt_for(self.repo, self.pkg, self.out)
        prompt = (lane / "prompt.md").read_text(encoding="utf-8")
        manifest = json.loads((lane / "manifest.json").read_text(encoding="utf-8"))
        files = ["SKILL.md", "references/rubric.md", "references/agentskills/alpha.md",
                 "references/agentskills/beta.md", "references/verdict.schema.json"]
        positions = []
        for rel in files:
            self.assertIn((self.pkg / rel).read_text(encoding="utf-8"), prompt)
            positions.append(prompt.index(f"===== BEGIN EMBEDDED FILE skill-judge/{rel} "))
        self.assertEqual(positions, sorted(positions))
        self.assertEqual([entry["path"] for entry in manifest["embedded"]], files)
        for entry in manifest["embedded"]:
            data = (self.pkg / entry["path"]).read_bytes()
            self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())

    def test_fixed_rules_and_the_module_list_are_in_the_prompt(self):
        lane = prompt_for(self.repo, self.pkg, self.out)
        prompt = (lane / "prompt.md").read_text(encoding="utf-8")
        self.assertIn("3. Script tests live flat in tests/test_*.py, not in tests/skills/<name>/.",
                      prompt)
        self.assertIn("5. A skill ships runnable code when it has a tracked .py", prompt)
        self.assertIn("4. Script test modules for this skill: tests/test_alpha.py\n", prompt)
        self.assertEqual(json.loads((lane / "manifest.json").read_text(encoding="utf-8"))
                         ["modules"], ["tests/test_alpha.py"])

    def test_a_skill_without_a_test_module_gets_the_explicit_line(self):
        lane = prompt_for(self.repo, self.pkg, self.out, skill="demo-delta")
        prompt = (lane / "prompt.md").read_text(encoding="utf-8")
        self.assertIn("4. Script test modules for this skill: no script test found\n", prompt)

    def test_two_skills_prompts_differ_only_in_name_and_module_line(self):
        alpha = prompt_for(self.repo, self.pkg, self.out, skill="demo-alpha")
        beta = prompt_for(self.repo, self.pkg, self.out, skill="demo-beta")

        def normal(text, skill):
            text = re.sub(r"Script test modules for this skill: [^\n]*", "MODULES", text)
            return text.replace(skill, "SKILL")

        self.assertEqual(normal((alpha / "prompt.md").read_text(encoding="utf-8"), "demo-alpha"),
                         normal((beta / "prompt.md").read_text(encoding="utf-8"), "demo-beta"))

    def test_the_same_tree_gives_identical_prompt_bytes(self):
        first = prompt_for(self.repo, self.pkg, self.base / "one")
        second = prompt_for(self.repo, self.pkg, self.base / "two")
        self.assertEqual((first / "prompt.md").read_bytes(), (second / "prompt.md").read_bytes())

    def test_ships_code_follows_the_runnable_code_rule(self):
        expected = {"demo-alpha": True, "demo-gamma": True, "demo-eps": True,
                    "demo-beta": False, "demo-delta": False}
        for name, ships in expected.items():
            with self.subTest(skill=name):
                self.assertEqual(judge_loop.ships_code(self.repo, name), ships)

    def test_a_sibling_skill_name_is_not_in_the_digest(self):
        before = judge_loop.skill_digest(self.repo, "demo-beta")
        commit_change(self.repo, "skills/demo-beta-fixer/SKILL.md", "# changed\n")
        self.assertEqual(judge_loop.skill_digest(self.repo, "demo-beta"), before)

    def test_the_digest_is_the_same_from_a_sub_folder(self):
        root = judge_loop.find_root(None, cwd=self.repo / "skills" / "demo-alpha")
        self.assertEqual(root, self.repo.resolve())
        self.assertEqual(judge_loop.skill_digest(root, "demo-alpha"),
                         judge_loop.skill_digest(self.repo, "demo-alpha"))

    def test_a_bad_skill_name_is_refused(self):
        for name in ("demo/x", "../demo-alpha", "Demo-Alpha", ""):
            with self.subTest(name=name), self.assertRaises(judge_loop.JudgeLoopError):
                judge_loop.skill_files(self.repo, name)

    def test_a_rubric_without_the_pin_lines_stops_the_build(self):
        bad = make_package(self.base / "bad")
        rubric = bad / "references" / "rubric.md"
        rubric.write_text(rubric.read_text(encoding="utf-8").replace(
            "rubric_version: 4", "rubric_version four", 1), encoding="utf-8")
        code, out = run_main(["--root", str(self.repo), "prompt", "--loop", "32", "--round", "1",
                              "--judge", "cli-a:model-a", "--skill", "demo-alpha",
                              "--out", str(self.out), "--judge-package", str(bad)])
        self.assertEqual(code, 1)
        self.assertIn("rubric has no rubric_version/spec_sha pin lines", out)

    def test_probe_answer_carries_one_code_per_embedded_file(self):
        probe_out = self.base / "probe"
        code, _out = run_main(["--root", str(self.repo), "prompt", "--probe",
                               "--judge", "cli-a:model-a", "--out", str(probe_out),
                               "--judge-package", str(self.pkg)])
        self.assertEqual(code, 0)
        lane = probe_out / "cli-a_model-a"
        token = (lane / "token").read_text(encoding="utf-8").strip()
        self.assertRegex(token, r"^AIKIT-SENTINEL(?:-[0-9a-f]{8}){5}$")
        codes = token.split("-")[2:]
        lines = (lane / "prompt.md").read_text(encoding="utf-8").splitlines()
        ends = [i for i, line in enumerate(lines) if line.startswith("===== END EMBEDDED FILE")]
        self.assertEqual(len(ends), 5)
        for number, index in enumerate(ends, start=1):
            self.assertEqual(lines[index + 1], f"PROBE PART {number}: {codes[number - 1]}")
        self.assertEqual(lines[-1], "Reply now with only that word.")

    def test_two_probes_get_different_codes(self):
        tokens = []
        for name in ("first", "second"):
            run_main(["--root", str(self.repo), "prompt", "--probe", "--judge", "cli-a:model-a",
                      "--out", str(self.base / name), "--judge-package", str(self.pkg)])
            tokens.append((self.base / name / "cli-a_model-a" / "token").read_text(
                encoding="utf-8"))
        self.assertNotEqual(tokens[0], tokens[1])

    def test_probe_refuses_skill_and_round(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            judge_loop.main(["--root", str(self.repo), "prompt", "--probe", "--judge", "j",
                             "--skill", "demo-alpha", "--out", str(self.out)])
        self.assertEqual(caught.exception.code, 2)


@unittest.skipUnless(HAS_GIT, "git not installed")
class TestIngest(unittest.TestCase):
    """Ingest refusals (exit 1, nothing written), failed attempts (exit 0) and native lanes."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="judge-loop-test-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.pkg = make_package(self.base)
        self.repo = make_skill_repo(self.base)
        self.records = self.base / "rec"
        self.lane = prompt_for(self.repo, self.pkg, self.base / "lanes")

    def _good_verdict(self, **changes):
        verdict = make_verdict("demo-alpha", "cli-a:model-a")
        verdict.update(changes)
        return json.dumps(verdict)

    def _ingest(self, records=None, lane=None, *extra):
        return run_main(["--root", str(self.repo), "ingest", "--lane-dir",
                         str(lane or self.lane), "--records", str(records or self.records),
                         *extra])

    def _record_path(self, records=None, slug="cli-a_model-a"):
        return (records or self.records) / "verdicts" / "32" / "demo-alpha" / "r1" / f"{slug}.json"

    def _record(self, records=None, slug="cli-a_model-a"):
        return json.loads(self._record_path(records, slug).read_text(encoding="utf-8"))

    def test_refuses_a_verdict_from_another_judge(self):
        write_lane(self.lane, STATUS_OK, self._good_verdict(judge="cli-b:model-b") + "\n")
        code, out = self._ingest()
        self.assertEqual(code, 1)
        self.assertIn("judge", out)
        self.assertFalse(self._record_path().exists())

    def test_refuses_a_verdict_for_another_skill(self):
        write_lane(self.lane, STATUS_OK, self._good_verdict(skill="demo-beta") + "\n")
        code, _out = self._ingest()
        self.assertEqual(code, 1)
        self.assertFalse(self._record_path().exists())

    def test_refuses_a_verdict_under_another_pin(self):
        for changes in ({"rubric_version": 5}, {"spec_sha": "b" * 40}):
            with self.subTest(changes=changes):
                write_lane(self.lane, STATUS_OK, self._good_verdict(**changes) + "\n")
                code, _out = self._ingest(records=self.base / "pin")
                self.assertEqual(code, 1)
                self.assertFalse(self._record_path(records=self.base / "pin").exists())

    def test_refuses_a_second_verdict_for_the_same_round(self):
        write_lane(self.lane, STATUS_OK, self._good_verdict() + "\n")
        self.assertEqual(self._ingest()[0], 0)
        code, _out = self._ingest()
        self.assertEqual(code, 1)
        self.assertEqual(len(self._record()["attempts"]), 1)

    def test_refuses_a_record_of_another_judge_with_the_same_slug(self):
        path = self.records / "verdicts" / "32" / "demo-alpha" / "r1" / "cli-a_model-a.json"
        judge_loop.atomic_write_json(path, make_record("32", "demo-alpha", 1, "cli-a_model-a",
                                                       None))
        write_lane(self.lane, STATUS_OK, self._good_verdict() + "\n")
        code, out = self._ingest()
        self.assertEqual(code, 1)
        self.assertIn("belongs to judge", out)

    def test_a_failed_lane_records_an_attempt_without_a_verdict(self):
        good = self._good_verdict()
        bad_percent = json.dumps(dict(make_verdict("demo-alpha", "cli-a:model-a"), percent=99.0))
        outside = make_verdict("demo-alpha", "cli-a:model-a", drops={"D1": (5, "low")})
        outside["findings"][0]["file"] = "../../outside.md"
        missing = make_verdict("demo-alpha", "cli-a:model-a", drops={"D1": (5, "low")})
        missing["findings"][0]["file"] = "skills/demo-alpha/missing.md"
        beyond = make_verdict("demo-alpha", "cli-a:model-a", drops={"D1": (5, "low")})
        beyond["findings"][0]["line"] = 999
        quota = "AIKIT-XAI status=quota cli=cli-a model=model-a exit=75 cli_rc=75 tree=clean"
        dirty = STATUS_OK.replace("tree=clean", "tree=dirty")
        cases = {
            "quota": (quota, good + "\n"), "dirty tree": (dirty, good + "\n"),
            "no status line": (None, good + "\n"), "no verdict line": (STATUS_OK, ""),
            "two verdict lines": (STATUS_OK, good + "\n" + good + "\n"),
            "not JSON": (STATUS_OK, '{"skill": "demo-alpha", broken\n'),
            "wrong percent": (STATUS_OK, bad_percent + "\n"),
            "finding outside the root": (STATUS_OK, json.dumps(outside) + "\n"),
            "finding file missing": (STATUS_OK, json.dumps(missing) + "\n"),
            "finding line beyond the file": (STATUS_OK, json.dumps(beyond) + "\n"),
        }
        for index, (name, (status, text)) in enumerate(cases.items()):
            with self.subTest(case=name):
                records = self.base / f"failed-{index}"
                write_lane(self.lane, status, text)
                code, out = self._ingest(records=records)
                self.assertEqual(code, 0)
                self.assertIn("attempt recorded without a verdict", out)
                record = self._record(records=records)
                self.assertIsNone(record["verdict"])
                self.assertEqual(len(record["attempts"]), 1)
                self.assertIsNotNone(record["attempts"][0]["error"])

    def test_a_good_attempt_after_a_failed_one_keeps_one_record(self):
        quota = "AIKIT-XAI status=quota cli=cli-a model=model-a exit=75 cli_rc=75 tree=clean"
        write_lane(self.lane, quota, "")
        self.assertEqual(self._ingest()[0], 0)
        write_lane(self.lane, STATUS_OK, self._good_verdict() + "\n")
        self.assertEqual(self._ingest()[0], 0)
        record = self._record()
        self.assertEqual(len(record["attempts"]), 2)
        self.assertIsNotNone(record["attempts"][0]["error"])
        self.assertIsNone(record["attempts"][1]["error"])
        self.assertEqual(record["verdict"], make_verdict("demo-alpha", "cli-a:model-a"))

    def test_a_verdict_line_is_found_in_any_key_order(self):
        verdict = make_verdict("demo-alpha", "cli-a:model-a")
        reordered = {"judge": verdict["judge"], **verdict}
        for index, line in enumerate((json.dumps(reordered), json.dumps(verdict).replace(
                '{"skill"', '{ "skill"', 1))):
            with self.subTest(line=line[:20]):
                records = self.base / f"order-{index}"
                write_lane(self.lane, STATUS_OK, line + "\n")
                code, out = self._ingest(records=records)
                self.assertEqual(code, 0, out)
                self.assertIn("verdict recorded", out)

    def test_a_retry_with_another_digest_is_refused_and_the_record_is_kept(self):
        quota = "AIKIT-XAI status=quota cli=cli-a model=model-a exit=75 cli_rc=75 tree=clean"
        write_lane(self.lane, quota, "")
        self.assertEqual(self._ingest()[0], 0)
        manifest_path = self.lane / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["digest"] = "f" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        write_lane(self.lane, STATUS_OK, self._good_verdict() + "\n")
        code, out = self._ingest()
        self.assertEqual(code, 1)
        self.assertIn("digest differs from the recorded round", out)
        record = self._record()
        self.assertIsNone(record["verdict"])
        self.assertEqual(len(record["attempts"]), 1)

    def test_native_lane_records_the_note_and_no_status_line(self):
        note = "native, xhigh (frontmatter, documented; not observed)"
        write_lane(self.lane, None, self._good_verdict() + "\n")
        code, _out = self._ingest(None, None, "--native-note", note)
        self.assertEqual(code, 0)
        attempt = self._record()["attempts"][0]
        self.assertIsNone(attempt["status_line"])
        self.assertEqual(attempt["note"], note)

    def test_replaces_needs_a_reason_and_a_reason_needs_replaces(self):
        write_lane(self.lane, None, self._good_verdict() + "\n")
        for extra in (("--replaces", "cli-b:model-b"), ("--reason", "quota")):
            with self.subTest(extra=extra), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    judge_loop.main(["--root", str(self.repo), "ingest", "--lane-dir",
                                     str(self.lane), "--records", str(self.records), *extra])
                self.assertEqual(caught.exception.code, 2)

    def test_a_substitute_is_stored_with_its_reason(self):
        note = "native, xhigh (frontmatter, documented; not observed)"
        write_lane(self.lane, None, self._good_verdict() + "\n")
        self._ingest(None, None, "--native-note", note, "--replaces", "cli-b:model-b",
                     "--reason", "cli-b quota")
        self.assertEqual(self._record()["substitute"],
                         {"replaces": "cli-b:model-b", "reason": "cli-b quota"})


class TestVerdictValidation(unittest.TestCase):
    """validate_verdict: exact keys, arithmetic, grade bands, findings and the pin."""

    pin = (4, "a" * 40)

    def test_all_max_verdict_without_findings_is_valid(self):
        verdict = make_verdict("demo-alpha", "cli-a:model-a")
        self.assertEqual(judge_loop.validate_verdict(verdict, self.pin), [])

    def test_a_below_max_score_needs_a_finding(self):
        verdict = make_verdict("demo-alpha", "cli-a:model-a", drops={"D1": (10, "high")})
        verdict["findings"] = []
        self.assertIn("D1 is below its max but has no finding",
                      judge_loop.validate_verdict(verdict, self.pin))

    def test_duplicate_finding_ids_are_invalid(self):
        verdict = make_verdict("demo-alpha", "cli-a:model-a",
                               drops={"D1": (5, "low"), "D2": (5, "low")})
        for finding in verdict["findings"]:
            finding["id"] = "F1"
        self.assertIn("duplicate finding id F1", judge_loop.validate_verdict(verdict, self.pin))

    def test_percent_80_is_grade_b_and_79_9_is_grade_c(self):
        maxima = {dim: 125 for dim in DIMS}
        grade_b = make_verdict("demo-alpha", "cli-a:model-a", maxima=maxima,
                               drops={"D1": (125, "high"), "D2": (75, "medium")})
        grade_c = make_verdict("demo-alpha", "cli-a:model-a", maxima=maxima,
                               drops={"D1": (125, "high"), "D2": (76, "medium")})
        self.assertEqual((grade_b["total"], grade_b["max_total"], grade_b["percent"],
                          grade_b["grade"]), (800, 1000, 80.0, "B"))
        self.assertEqual((grade_c["total"], grade_c["percent"], grade_c["grade"]),
                         (799, 79.9, "C"))
        self.assertEqual(judge_loop.validate_verdict(grade_b, self.pin), [])
        self.assertEqual(judge_loop.validate_verdict(grade_c, self.pin), [])

    def test_malformed_verdicts_are_rejected_with_their_message(self):
        def base():
            return make_verdict("demo-alpha", "cli-a:model-a")

        above = base()
        above["scores"]["D1"] = 21
        wrong_total = base()
        wrong_total["total"] += 1
        wrong_grade = base()
        wrong_grade["grade"] = "B"
        missing_key = base()
        del missing_key["grade"]
        extra_key = dict(base(), extra=1)
        short_sha = dict(base(), spec_sha="a" * 39)
        cases = {
            "a score exceeds its max": above, "sum(scores)": wrong_total,
            "grade B != A": wrong_grade,
            "keys are not exactly the schema's": missing_key,
            "spec_sha is not 40 hex": short_sha,
        }
        for message, verdict in cases.items():
            with self.subTest(message=message):
                errors = judge_loop.validate_verdict(verdict, self.pin)
                self.assertTrue(any(message in error for error in errors), errors)
        self.assertEqual(judge_loop.validate_verdict(extra_key, self.pin),
                         ["keys are not exactly the schema's"])


class TestPool(unittest.TestCase):
    """The judge pool from probe results (SPEC R3): order, substitutes, the loop record."""

    JUDGES = ["cli-a:m", "cli-b:m", "cli-c:m"]

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="judge-pool-test-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.probes = self.base / "probes"
        self.records = self.base / "rec"

    def _lanes(self, judges, usable):
        """A probe lane per judge: the usable ones echo the answer, the rest exit 75 (quota)."""
        for judge in judges:
            if judge in usable:
                write_probe(self.probes, judge, ANSWER, ANSWER + "\n", _status())
            else:
                write_probe(self.probes, judge, ANSWER, ANSWER + "\n",
                            _status(status="quota", exit_code=75))

    def _pool(self, judges, usable):
        self._lanes(judges, usable)
        results = [judge_loop.probe_result(self.probes, judge) for judge in judges]
        return judge_loop.choose_pool(judges, NATIVE, results)

    def _cli(self, judges, native=NATIVE):
        return run_main(["--root", str(self.base), "pool", "--loop", "32", "--judges", *judges,
                         "--native", native, "--probe-dir", str(self.probes),
                         "--records", str(self.records)])

    def test_two_usable_judges_form_the_pool_in_order(self):
        pool = self._pool(self.JUDGES, usable=self.JUDGES)
        self.assertEqual(pool["members"], ["cli-a:m", "cli-b:m"])
        self.assertEqual(pool["substitutes"], [])
        self.assertEqual([probe["judge"] for probe in pool["probes"]], self.JUDGES)

    def test_first_two_usable_judges_win_when_an_earlier_one_fails(self):
        pool = self._pool(self.JUDGES, usable=["cli-b:m", "cli-c:m"])
        self.assertEqual(pool["members"], ["cli-b:m", "cli-c:m"])
        self.assertEqual(pool["substitutes"], [])
        self.assertFalse(pool["probes"][0]["usable"])

    def test_one_usable_judge_gets_the_native_id_as_a_substitute(self):
        pool = self._pool(self.JUDGES, usable=["cli-b:m"])
        self.assertEqual(pool["members"], ["cli-b:m", NATIVE])
        self.assertEqual(pool["substitutes"], [{
            "judge": NATIVE, "reason": "only one configured judge passed its probe"}])

    def test_no_usable_judge_leaves_the_native_id_alone(self):
        pool = self._pool(self.JUDGES, usable=[])
        self.assertEqual(pool["members"], [NATIVE])
        self.assertEqual(pool["substitutes"], [{
            "judge": NATIVE, "reason": "no configured judge passed its probe"}])

    def test_empty_judge_list_leaves_the_native_id_alone(self):
        pool = judge_loop.choose_pool([], NATIVE, [])
        self.assertEqual(pool["members"], [NATIVE])
        self.assertEqual(pool["substitutes"], [{"judge": NATIVE, "reason": "judge list empty"}])

    def test_native_id_in_the_judge_list_is_refused(self):
        with self.assertRaisesRegex(judge_loop.JudgeLoopError, "must not be in the judge list"):
            judge_loop.choose_pool([NATIVE], NATIVE, [])

    def test_a_judge_listed_twice_is_refused(self):
        with self.assertRaisesRegex(judge_loop.JudgeLoopError, "appears twice"):
            self._pool(["cli-a:m", "cli-a:m"], usable=["cli-a:m"])

    def test_usable_probe_reports_its_status_line_and_no_reason(self):
        write_probe(self.probes, "cli-a:m", ANSWER, ANSWER + "\n", _status())
        self.assertEqual(judge_loop.probe_result(self.probes, "cli-a:m"),
                         {"judge": "cli-a:m", "usable": True, "status_line": _status(),
                          "reason": ""})

    def test_unusable_probe_reasons(self):
        cases = [
            ("preamble before the answer", "I think it is " + ANSWER + "\n", _status(),
             "answer is not the sentinel"),
            ("only the last code", "AIKIT-SENTINEL-8c9d0e1f\n", _status(),
             "answer is not the sentinel"),
            ("codes out of order", "AIKIT-SENTINEL-4e5f6a7b-0a1b2c3d-8c9d0e1f\n", _status(),
             "answer is not the sentinel"),
            ("timed out", ANSWER + "\n", _status(status="timeout", exit_code=124),
             "status timeout exit 124 tree clean"),
            ("dirty tree", ANSWER + "\n", _status(tree="dirty"), "status ok exit 0 tree dirty"),
            ("no status line", ANSWER + "\n", "boot noise", "no AIKIT-XAI line"),
        ]
        for number, (name, out_text, status, reason) in enumerate(cases):
            with self.subTest(case=name):
                probes = self.base / f"case{number}"
                write_probe(probes, "cli-a:m", ANSWER, out_text, status)
                result = judge_loop.probe_result(probes, "cli-a:m")
                self.assertFalse(result["usable"])
                self.assertEqual(result["reason"], reason)

    def test_missing_lane_err_is_no_probe_output(self):
        write_probe(self.probes, "cli-a:m", ANSWER, ANSWER + "\n", _status())
        (self.probes / "cli-a_m" / "lane.err").unlink()
        self.assertEqual(judge_loop.probe_result(self.probes, "cli-a:m"),
                         {"judge": "cli-a:m", "usable": False, "status_line": None,
                          "reason": "no probe output"})

    def test_cli_pool_writes_the_loop_record_and_keeps_other_keys(self):
        self._lanes(["cli-a:m", "cli-b:m"], usable=["cli-a:m", "cli-b:m"])
        code, out = self._cli(["cli-a:m", "cli-b:m"])
        self.assertEqual(code, 0)
        self.assertIn("judge-loop: probe cli-a:m: usable", out)
        self.assertIn("judge-loop: pool 32: cli-a:m, cli-b:m", out)
        loop_file = self.records / "loops" / "32.json"
        loop = json.loads(loop_file.read_text(encoding="utf-8"))
        self.assertEqual(loop["loop"], "32")
        self.assertEqual(loop["pool"]["members"], ["cli-a:m", "cli-b:m"])
        judge_loop.update_loop_file(self.records, "32", "counts", {})
        loop = json.loads(loop_file.read_text(encoding="utf-8"))
        self.assertEqual(loop["pool"]["members"], ["cli-a:m", "cli-b:m"])
        self.assertIn("counts", loop)

    def test_cli_pool_prints_unusable_probes_and_the_substitute(self):
        self._lanes(["cli-a:m"], usable=[])
        code, out = self._cli(["cli-a:m"])
        self.assertEqual(code, 0)
        self.assertIn("judge-loop: probe cli-a:m: unusable (status quota exit 75 tree clean)", out)
        self.assertIn(f"judge-loop: substitute {NATIVE}: no configured judge passed its probe",
                      out)
        self.assertIn(f"judge-loop: pool 32: {NATIVE}", out)

    def test_cli_native_equal_to_a_judge_exits_1_without_writing(self):
        code, out = self._cli(["cli-a:m"], native="cli-a:m")
        self.assertEqual(code, 1)
        self.assertIn("judge-loop: the native id must not be in the judge list", out)
        self.assertFalse((self.records / "loops" / "32.json").exists())

    def test_bad_loop_id_is_refused_before_any_path_is_built(self):
        with self.assertRaises(judge_loop.JudgeLoopError):
            judge_loop.update_loop_file(self.records, "../x", "pool", {})
        self.assertFalse(self.records.exists())


def _last(percent, critical=0, high=0, judged_at: str | None = "abc1234"):
    return {"percent": percent, "critical": critical, "high": high, "judged_at": judged_at,
            "source": "fixture"}


def ladder_answer(item_id, level_text, backend="laya"):
    """A ladder document that answers one score item with `level_text` from one backend."""
    column = {"choice": level_text, "top": 0.9, "fallback": False, "forced": False,
              "model": "m"}
    return {"items": {item_id: {"decided_by": backend, backend: column}}}


class FakeAsk:
    """A stand-in for the jev call: records each item and answers or raises."""

    def __init__(self, answer=None, error=None):
        self.answer = answer
        self.error = error
        self.items = []

    def __call__(self, item):
        self.items.append(item)
        if self.error is not None:
            raise self.error
        return self.answer


class TestCount(unittest.TestCase):
    """The judge count (SPEC R4): deterministic triggers, fixed word bands, the jev item."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="judge-count-test-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)

    def test_no_verdict_gives_two(self):
        self.assertEqual(judge_loop.deterministic_count(None), (2, ["no rubric-v4 verdict"]))

    def test_band_boundaries_decide_one_or_two(self):
        for percent, expected in [(72.9, 1), (73.0, 2), (80.0, 2), (87.0, 2), (87.1, 1)]:
            with self.subTest(percent=percent):
                self.assertEqual(judge_loop.deterministic_count(_last(percent))[0], expected)
        self.assertEqual(judge_loop.deterministic_count(_last(73.0))[1],
                         ["last percent 73.0 is within 7.0 points of 80"])

    def test_high_or_critical_finding_gives_two(self):
        self.assertEqual(judge_loop.deterministic_count(_last(88.0, high=1)),
                         (2, ["last verdict had a critical or high finding"]))
        count, reasons = judge_loop.deterministic_count(_last(84.0, high=1))
        self.assertEqual(count, 2)
        self.assertEqual(len(reasons), 2)

    def test_out_of_band_without_findings_gives_one(self):
        self.assertEqual(judge_loop.deterministic_count(_last(88.0)),
                         (1, ["no deterministic trigger"]))

    def test_percent_words_name_side_and_distance(self):
        self.assertEqual(judge_loop.percent_words(88.0),
                         "the last score sat just outside judge variation, above the pass mark")
        self.assertIn("far above", judge_loop.percent_words(96.0))
        self.assertIn("moderately far below", judge_loop.percent_words(68.0))

    def test_change_words_use_fixed_bands(self):
        def words(rows):
            return judge_loop.change_words(rows)
        self.assertEqual(words([])["skill_md"], "SKILL.md unchanged")
        self.assertEqual(words([(5, 0, "skills/x/SKILL.md")])["skill_md"],
                         "a few SKILL.md lines changed")
        self.assertEqual(words([(30, 0, "skills/x/SKILL.md")])["skill_md"],
                         "a moderate SKILL.md change")
        self.assertEqual(words([(60, 0, "skills/x/SKILL.md")])["skill_md"],
                         "a large SKILL.md change")
        self.assertEqual(words([(None, None, "skills/x/scripts/a.bin")])["scripts"], "none")
        self.assertEqual(words([(1, 0, "skills/x/references/a.md"),
                                (1, 0, "skills/x/evals/e.json")])["references"], "one or two files")
        self.assertEqual(words([(1, 0, "skills/x/references/a.md"),
                                (1, 0, "skills/x/references/b.md"),
                                (1, 0, "skills/x/references/c.md")])["references"],
                         "several files")

    def test_jev_item_is_pinned_to_fixed_words(self):
        rows = [(3, 1, "skills/x/SKILL.md"), (10, 0, "skills/x/references/a.md"),
                (5, 5, "skills/x/scripts/a.py"), (2, 0, "skills/x/evals/evals.json")]
        item = judge_loop.jev_item(judge_loop.percent_words(88.0), judge_loop.change_words(rows))
        self.assertEqual(item, {
            "id": "judge-count", "type": "score", "instructions": judge_loop.JEV_INSTRUCTIONS,
            "context": ("the last score sat just outside judge variation, above the pass mark; "
                        "no critical or high findings; a few SKILL.md lines changed; reference "
                        "files: one or two files; script files: one or two files; eval files: "
                        "one or two files."),
            "criteria": list(judge_loop.JEV_LEVELS)})
        text = json.dumps(item)
        self.assertNotIn("skills/", text)
        self.assertNotIn("x/", text)

    def test_jev_level_reads_the_decided_column(self):
        item = {"id": "judge-count", "criteria": list(judge_loop.JEV_LEVELS)}
        answer = ladder_answer("judge-count", judge_loop.JEV_LEVELS[2])
        self.assertEqual(judge_loop.jev_level(answer, item),
                         (2, f"jev level 2 ({judge_loop.JEV_LEVELS[2]}) from laya"))
        self.assertEqual(judge_loop.jev_level({"items": {}}, item),
                         (None, "jev gave no answer"))
        own = {"items": {"judge-count": {"decided_by": "own_reasoning"}}}
        self.assertEqual(judge_loop.jev_level(own, item),
                         (None, "jev needs_fallback (own reasoning)"))
        off_list = ladder_answer("judge-count", "a made-up level")
        self.assertEqual(judge_loop.jev_level(off_list, item),
                         (None, "jev answer is not one of the levels"))

    def test_final_count_composes_the_reasons(self):
        det = (1, ["no deterministic trigger"])
        self.assertEqual(judge_loop.final_count(det, 2, "note"),
                         (2, ["no deterministic trigger", "note: asks for two"]))
        self.assertEqual(judge_loop.final_count(det, 1, "note"),
                         (1, ["no deterministic trigger", "note: keeps one"]))
        self.assertEqual(judge_loop.final_count(det, None, "note"),
                         (1, ["no deterministic trigger", "note"]))
        self.assertEqual(judge_loop.final_count((2, ["r"]), None, "ignored"), (2, ["r"]))

    def test_ask_jev_sends_one_item_with_the_fixed_environment(self):
        seen = {}

        def fake_run(argv, **kwargs):
            seen["argv"], seen["kwargs"] = argv, kwargs
            return subprocess.CompletedProcess(argv, 0, stdout='{"items": {}}', stderr="")

        item = {"id": "judge-count", "type": "score"}
        self.assertEqual(judge_loop.ask_jev(item, "/fixture/jev_review.py", run=fake_run),
                         {"items": {}})
        self.assertEqual(seen["argv"][-2:], ["/fixture/jev_review.py", "ladder"])
        self.assertEqual(json.loads(seen["kwargs"]["input"]), {"items": [item]})
        self.assertEqual(seen["kwargs"]["env"]["GSD_PATH_JEV"], "1")
        # jev_ladder waits 30 * (1 + 3) + 10 = 130 s for its client; the outer call outlasts it
        self.assertGreater(seen["kwargs"]["timeout"], 130)

    def test_ask_jev_raises_jev_unavailable_on_a_failed_client(self):
        def failed_run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 2, stdout="", stderr="no backend")
        with self.assertRaises(judge_loop.JevUnavailable):
            judge_loop.ask_jev({"id": "judge-count"}, "/fixture/jev_review.py", run=failed_run)

    def test_find_jev_client_prefers_the_repo_and_finds_nothing_in_an_empty_home(self):
        repo = self.base / "repo"
        client = repo / "skills" / "jev-fast-decision" / "scripts" / "jev_review.py"
        client.parent.mkdir(parents=True)
        client.write_text("# fixture client\n", encoding="utf-8")
        home = {"HOME": str(self.base / "home")}
        self.assertEqual(judge_loop.find_jev_client(repo, {"HOME": home["HOME"]}, None),
                         str(client))
        self.assertIsNone(judge_loop.find_jev_client(self.base / "empty", home, None))
        override = self.base / "given.py"
        override.write_text("# fixture\n", encoding="utf-8")
        self.assertEqual(judge_loop.find_jev_client(self.base / "empty", home, override),
                         str(override))

    def test_load_inputs_names_the_skill_with_a_bad_batch(self):
        records = self.base / "rec"
        records.mkdir()
        (records / "inputs.json").write_text(json.dumps({
            "schema": 1, "skills": {"demo-gamma": {"last_v4": None}}, "excluded": {}}),
            encoding="utf-8")
        with self.assertRaisesRegex(judge_loop.JudgeLoopError, "demo-gamma has no valid batch"):
            judge_loop.load_inputs(records)

    def test_load_inputs_names_the_keys_a_skill_lacks(self):
        records = self.base / "rec"
        records.mkdir()
        (records / "inputs.json").write_text(json.dumps({
            "schema": 1, "skills": {"demo-gamma": {"batch": "32.1"}}, "excluded": {}}),
            encoding="utf-8")
        with self.assertRaises(judge_loop.JudgeLoopError) as caught:
            judge_loop.load_inputs(records)
        self.assertEqual(str(caught.exception),
                         "inputs.json: skill demo-gamma lacks last_v4, old_score")

    def test_load_inputs_refuses_a_name_in_both_maps(self):
        records = self.base / "rec"
        records.mkdir()
        (records / "inputs.json").write_text(json.dumps({
            "schema": 1, "skills": {"demo-alpha": {"batch": "32.1", "last_v4": None,
                                                   "old_score": None}},
            "excluded": {"demo-alpha": "reason"}}), encoding="utf-8")
        with self.assertRaises(judge_loop.JudgeLoopError) as caught:
            judge_loop.load_inputs(records)
        self.assertEqual(str(caught.exception),
                         "inputs.json: demo-alpha is in both skills and excluded")


@unittest.skipUnless(HAS_GIT, "git not installed")
class TestCountGit(unittest.TestCase):
    """The count against a fixture repository: the base commit, jev asked or not, the CLI."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="judge-count-git-test-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.repo = make_repo(self.base, SKILL_REPO_FILES)
        self.base_sha = _git(self.repo, _git_env(self.base), "rev-parse", "HEAD").strip()
        self.records = self.base / "rec"
        self.pkg = make_package(self.base)

    def _write_inputs(self, skills, excluded=None):
        self.records.mkdir(parents=True, exist_ok=True)
        (self.records / "inputs.json").write_text(json.dumps(
            {"schema": 1, "skills": skills, "excluded": excluded or {}}), encoding="utf-8")

    def _count(self, extra):
        return run_main(["--root", str(self.repo), "count", "--loop", "32",
                         "--records", str(self.records), "--judge-package", str(self.pkg), *extra])

    def test_numstat_is_none_for_an_unresolvable_base_and_refuses_bad_input(self):
        self.assertIsNone(judge_loop.numstat(self.repo, "deadbee", "demo-alpha"))
        self.assertIsNone(judge_loop.numstat(self.repo, "HEAD; rm", "demo-alpha"))
        with self.assertRaises(judge_loop.JudgeLoopError):
            judge_loop.numstat(self.repo, self.base_sha, "../demo-alpha")

    def test_numstat_lists_the_skill_rows_since_the_base(self):
        commit_change(self.repo, "skills/demo-alpha/SKILL.md", "# demo-alpha\nmore\n")
        self.assertEqual(judge_loop.numstat(self.repo, self.base_sha, "demo-alpha"),
                         [(1, 0, "skills/demo-alpha/SKILL.md")])

    def test_numstat_counts_an_uncommitted_edit_as_the_digest_does(self):
        (self.repo / "skills" / "demo-alpha" / "SKILL.md").write_text(
            "# demo-alpha\nmore\n", encoding="utf-8")
        self.assertEqual(judge_loop.numstat(self.repo, self.base_sha, "demo-alpha"),
                         [(1, 0, "skills/demo-alpha/SKILL.md")])

    def test_count_records_an_unresolvable_base_without_asking(self):
        ask = FakeAsk(error=AssertionError("must not be asked"))
        entry = {"last_v4": _last(88.0, judged_at="deadbee")}
        record = judge_loop.count_skill(self.repo, "demo-alpha", entry, ask)
        self.assertEqual(ask.items, [])
        self.assertEqual(record["count"], 1)
        self.assertEqual(record["jev"]["note"], "jev input absent: base commit deadbee not found")
        self.assertFalse(record["jev"]["asked"])

    def test_count_records_a_missing_base_commit_without_asking(self):
        ask = FakeAsk()
        record = judge_loop.count_skill(self.repo, "demo-alpha",
                                        {"last_v4": _last(88.0, judged_at=None)}, ask)
        self.assertEqual(record["jev"]["note"], "jev input absent: no base commit recorded")
        self.assertEqual(ask.items, [])

    def test_deterministic_two_is_never_asked(self):
        ask = FakeAsk(error=AssertionError("must not be asked"))
        record = judge_loop.count_skill(self.repo, "demo-alpha",
                                        {"last_v4": _last(73.0, judged_at=self.base_sha)}, ask)
        self.assertEqual(record["count"], 2)
        self.assertEqual(record["jev"], {"asked": False, "item": None, "level": None,
                                         "note": "not asked (deterministic two)"})

    def test_no_jev_flag_records_its_note(self):
        record = judge_loop.count_skill(self.repo, "demo-alpha",
                                        {"last_v4": _last(88.0, judged_at=self.base_sha)}, None)
        self.assertEqual(record["jev"]["note"], "jev not asked (--no-jev)")
        self.assertFalse(record["jev"]["asked"])
        self.assertEqual(record["count"], 1)

    def test_jev_level_two_raises_one_to_two_and_round_trips(self):
        ask = FakeAsk(ladder_answer("judge-count", judge_loop.JEV_LEVELS[2]))
        record = judge_loop.count_skill(self.repo, "demo-alpha",
                                        {"last_v4": _last(88.0, judged_at=self.base_sha)}, ask)
        note = f"jev level 2 ({judge_loop.JEV_LEVELS[2]}) from laya"
        self.assertEqual(len(ask.items), 1)
        self.assertEqual(record["count"], 2)
        self.assertEqual(record["reasons"], ["no deterministic trigger", f"{note}: asks for two"])
        self.assertEqual(record["jev"]["level"], 2)
        self.assertEqual(record["jev"]["note"], note)
        self.assertTrue(record["jev"]["asked"])
        self.assertEqual(record["jev"]["item"]["id"], "judge-count")
        det = judge_loop.deterministic_count(record["last_v4"])
        self.assertEqual(judge_loop.final_count(det, record["jev"]["level"], record["jev"]["note"]),
                         (record["count"], record["reasons"]))

    def test_jev_level_one_keeps_one(self):
        ask = FakeAsk(ladder_answer("judge-count", judge_loop.JEV_LEVELS[1]))
        record = judge_loop.count_skill(self.repo, "demo-alpha",
                                        {"last_v4": _last(88.0, judged_at=self.base_sha)}, ask)
        self.assertEqual(record["count"], 1)
        self.assertTrue(record["reasons"][-1].endswith(": keeps one"))

    def test_own_reasoning_and_unavailable_jev_keep_one(self):
        own = FakeAsk({"items": {"judge-count": {"decided_by": "own_reasoning"}}})
        record = judge_loop.count_skill(self.repo, "demo-alpha",
                                        {"last_v4": _last(88.0, judged_at=self.base_sha)}, own)
        self.assertEqual((record["count"], record["jev"]["note"]),
                         (1, "jev needs_fallback (own reasoning)"))
        down = FakeAsk(error=judge_loop.JevUnavailable("no backend"))
        record = judge_loop.count_skill(self.repo, "demo-alpha",
                                        {"last_v4": _last(88.0, judged_at=self.base_sha)}, down)
        self.assertEqual((record["count"], record["jev"]["note"], record["jev"]["asked"]),
                         (1, "jev unavailable: no backend", True))
        self.assertIsNone(record["jev"]["level"])

    def test_cli_count_writes_counts_for_each_skill_and_keeps_the_pool(self):
        self._write_inputs({
            "demo-alpha": {"batch": "32.1", "last_v4": _last(88.0, judged_at=self.base_sha),
                           "old_score": None},
            "demo-beta": {"batch": "32.2", "last_v4": _last(73.0, judged_at=self.base_sha),
                          "old_score": None}},
            excluded={"zz-out": "out of scope for this fixture"})
        judge_loop.update_loop_file(self.records, "32", "pool", {"members": ["cli-a:m"]})
        answer = ladder_answer("judge-count", judge_loop.JEV_LEVELS[1])
        client = self.base / "fake_client.py"
        (self.base / "answer.json").write_text(json.dumps(answer), encoding="utf-8")
        client.write_text("import sys\nfrom pathlib import Path\n"
                          "sys.stdin.read()\n"
                          "print(Path(__file__).with_name('answer.json').read_text())\n",
                          encoding="utf-8")
        code, out = self._count(["--client", str(client)])
        self.assertEqual(code, 0)
        level = judge_loop.JEV_LEVELS[1]
        self.assertIn(f"judge-loop: count demo-alpha: 1 (no deterministic trigger; "
                      f"jev level 1 ({level}) from laya: keeps one)", out)
        self.assertIn("judge-loop: count demo-beta: 2 (last percent 73.0 is within 7.0 points "
                      "of 80)", out)
        loop = judge_loop.read_loop_file(self.records, "32")
        self.assertEqual(sorted(loop["counts"]), ["demo-alpha", "demo-beta"])
        self.assertEqual(loop["pool"], {"members": ["cli-a:m"]})
        self.assertTrue(loop["counts"]["demo-alpha"]["jev"]["asked"])

    def test_cli_count_names_a_malformed_skill(self):
        self._write_inputs({"demo-gamma": {"last_v4": None}})
        code, out = self._count(["--no-jev"])
        self.assertEqual(code, 1)
        self.assertIn("demo-gamma", out)

    def test_cli_count_refuses_a_skill_in_both_maps_and_an_unknown_skill(self):
        self._write_inputs({"demo-alpha": {"batch": "32.1", "last_v4": None, "old_score": None}},
                           excluded={"demo-alpha": "reason"})
        code, out = self._count(["--no-jev"])
        self.assertEqual(code, 1)
        self.assertIn("judge-loop: inputs.json: demo-alpha is in both skills and excluded", out)
        self._write_inputs({"demo-alpha": {"batch": "32.1", "last_v4": None, "old_score": None}})
        code, out = self._count(["--no-jev", "--skill", "demo-zeta"])
        self.assertEqual(code, 1)
        self.assertIn("judge-loop: inputs.json: no skill demo-zeta", out)

    def test_cli_count_without_a_client_records_it_as_unavailable(self):
        self._write_inputs({"demo-alpha": {"batch": "32.1",
                                           "last_v4": _last(88.0, judged_at=self.base_sha),
                                           "old_score": None}})
        code, _out = self._count(["--client", str(self.base / "no-such-client.py")])
        self.assertEqual(code, 0)
        loop = judge_loop.read_loop_file(self.records, "32")
        self.assertEqual(loop["counts"]["demo-alpha"]["jev"]["note"],
                         "jev unavailable: no jev client found")


@unittest.skipUnless(HAS_GIT, "git not installed")
class TestPriorBase(unittest.TestCase):
    """The count base comes from the prior loop's worst round; its commit is found by digest."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="judge-prior-base-test-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.repo = make_repo(self.base, SKILL_REPO_FILES)
        self.base_sha = _git(self.repo, _git_env(self.base), "rev-parse", "HEAD").strip()
        self.records = self.base / "rec"
        self.pkg = make_package(self.base)
        self.digest_a = judge_loop.skill_digest(self.repo, "demo-alpha")
        self.inputs = {"schema": 1, "excluded": {}, "skills": {
            "demo-alpha": {"batch": "32.1", "last_v4": None, "old_score": None}}}
        verdict = make_verdict("demo-alpha", "cli-a:model-a", drops={"D1": (20, "high")})
        rec = make_record("32", "demo-alpha", 1, "cli-a:model-a", verdict, digest=self.digest_a)
        write_records(self.records, self.inputs, {"32": {"pool": demo_pool()}}, [rec])

    def _count(self, *extra):
        return run_main(["--root", str(self.repo), "count", "--records", str(self.records),
                         "--judge-package", str(self.pkg), *extra])

    def _check(self, *args):
        return run_main(["--root", str(self.repo), "check", str(self.records), *args])

    def _report(self):
        return run_main(["--root", str(self.repo), "report", str(self.records)])

    def _write_32_1(self):
        """A loop 32.1 round 1 verdict for demo-alpha, and its count record from the count rule."""
        verdict = full_verdict("demo-alpha", "cli-a:model-a")
        rec = make_record("32.1", "demo-alpha", 1, "cli-a:model-a", verdict, digest=self.digest_a)
        judge_loop.atomic_write_json(judge_loop.record_path(
            self.records, "32.1", "demo-alpha", 1, "cli-a:model-a"), rec)
        entry = judge_loop.with_base(self.inputs["skills"]["demo-alpha"], judge_loop.prior_base(
            self.repo, self.records, "demo-alpha", "32.1"))
        count = judge_loop.count_skill(self.repo, "demo-alpha", entry, None)
        judge_loop.atomic_write_json(self.records / "loops" / "32.1.json",
                                     {"pool": demo_pool(), "counts": {"demo-alpha": count}})

    def _edit_32_1(self, edit):
        path = self.records / "loops" / "32.1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        edit(data)
        judge_loop.atomic_write_json(path, data)

    def test_digest_at_matches_the_working_digest_of_that_commit(self):
        commit_change(self.repo, "skills/demo-alpha/SKILL.md", "# demo-alpha\nmore\n")
        head = _git(self.repo, _git_env(self.base), "rev-parse", "HEAD").strip()
        self.assertEqual(judge_loop.digest_at(self.repo, self.base_sha, "demo-alpha"),
                         self.digest_a)
        self.assertNotEqual(judge_loop.digest_at(self.repo, head, "demo-alpha"), self.digest_a)
        self.assertEqual(judge_loop.base_commit(self.repo, self.digest_a, "demo-alpha"),
                         self.base_sha)
        self.assertIsNone(judge_loop.base_commit(self.repo, "f" * 64, "demo-alpha"))
        self.assertIsNone(judge_loop.digest_at(self.repo, "HEAD", "demo-alpha"))

    def test_count_takes_the_prior_loop_base(self):
        code, out = self._count("--loop", "32.1", "--no-jev", "--skill", "demo-alpha")
        self.assertEqual(code, 0, out)
        record = judge_loop.read_loop_file(self.records, "32.1")["counts"]["demo-alpha"]
        self.assertEqual(record["last_v4"], {
            "percent": 84.0, "critical": 0, "high": 1, "judged_at": self.base_sha,
            "source": "verdicts/32/demo-alpha/r1/cli-a_model-a.json"})
        self.assertEqual(record["count"], 2)
        self.assertIn("last verdict had a critical or high finding", record["reasons"])

    def test_check_mirrors_the_prior_loop_base(self):
        self._write_32_1()
        self._report()
        code, out = self._check("--skills", "demo-alpha", "--judges", "cli-a:model-a")
        self.assertEqual(code, 0, out)
        self._edit_32_1(lambda data: data["counts"]["demo-alpha"]["last_v4"].update(percent=80.0))
        code, out = self._check("--skills", "demo-alpha", "--judges", "cli-a:model-a")
        self.assertEqual(code, 1)
        self.assertIn("demo-alpha: count inputs differ from the prior loop's base", out)

    def test_check_ignores_the_recorded_base_commit(self):
        self._write_32_1()
        self._report()
        self._edit_32_1(lambda data: data["counts"]["demo-alpha"]["last_v4"].update(
            judged_at="f" * 40))
        _code, out = self._check("--skills", "demo-alpha", "--judges", "cli-a:model-a")
        self.assertNotIn("count inputs differ from the prior loop's base", out)

    def test_loop_32_count_still_uses_inputs_json(self):
        code, out = self._count("--loop", "32", "--no-jev", "--skill", "demo-alpha")
        self.assertEqual(code, 0, out)
        record = judge_loop.read_loop_file(self.records, "32")["counts"]["demo-alpha"]
        self.assertIsNone(record["last_v4"])
        self.assertEqual(record["count"], 2)
        self.assertEqual(judge_loop._count_problems(self.records, "32", "demo-alpha",
                                                    self.inputs), [])

    def test_count_takes_its_pin_from_the_rubric_before_any_record_exists(self):
        # loop 32 is pinned v4; the rubric is now v5, and loop 32.1 has no record yet
        pkg5 = make_package(self.base / "v5")
        rubric = pkg5 / "references" / "rubric.md"
        rubric.write_text(rubric.read_text(encoding="utf-8").replace(
            "rubric_version: 4", "rubric_version: 5"), encoding="utf-8")
        code, out = self._count("--loop", "32.1", "--no-jev", "--skill", "demo-alpha",
                                "--judge-package", str(pkg5))
        self.assertEqual(code, 0, out)
        record = judge_loop.read_loop_file(self.records, "32.1")["counts"]["demo-alpha"]
        self.assertIsNone(record["last_v4"])
        verdict = full_verdict("demo-alpha", "cli-a:model-a")
        rec = {**make_record("32.1", "demo-alpha", 1, "cli-a:model-a", verdict,
                             digest=self.digest_a), "rubric_version": 5}
        judge_loop.atomic_write_json(judge_loop.record_path(
            self.records, "32.1", "demo-alpha", 1, "cli-a:model-a"), rec)
        self.assertEqual(judge_loop._count_problems(self.records, "32.1", "demo-alpha",
                                                    self.inputs), [])


@unittest.skipUnless(HAS_GIT, "git not installed")
class TestPriorLoop(ReportFixture):
    """The regression limit (SPEC R11): a round's lowest percent against the prior loop's."""

    def _demo_b_32_1(self, points_lost):
        """Loop 32.1 round 1 for demo-b losing `points_lost` of 1000, and its count record."""
        verdict = make_verdict("demo-b", "cli-a:model-a", drops={"D1": (points_lost, "low")},
                               maxima={d: 125 for d in DIMS})
        self._put(make_record("32.1", "demo-b", 1, "cli-a:model-a", verdict))
        entry = judge_loop.with_base(demo_inputs()["skills"]["demo-b"], judge_loop.prior_base(
            self.repo, self.records, "demo-b", "32.1"))
        count = judge_loop.count_skill(self.repo, "demo-b", entry, None)
        judge_loop.atomic_write_json(self._loop_file("32.1"), {"counts": {"demo-b": count}})
        self._report()

    def test_bar_without_prior_loop_is_unchanged(self):
        record = bar_rec("a", 65.0)
        self.assertEqual(judge_loop.bar_with_base(record, [], [record], None),
                         judge_loop._record_bar(record, []))

    def test_regression_boundary_in_tenths(self):
        record = bar_rec("a", 65.0)
        self.assertEqual(judge_loop.bar_with_base(record, [], [record], prior_at(72.0)),
                         (2, "met: no critical or high finding; lowest percent 65.0, "
                             "loop 32 base 72.0"))
        low = bar_rec("a", 64.9)
        self.assertEqual(judge_loop.bar_with_base(low, [], [low], prior_at(72.0)),
                         (0, "not met: lowest percent 64.9 is more than 7.0 points under the "
                             "loop 32 base 72.0"))

    def test_grade_b_clause_carries_the_base(self):
        record = bar_rec("a", 81.0, high=True)
        self.assertEqual(judge_loop.bar_with_base(record, [], [record], prior_at(72.0)),
                         (1, "met: grade B or better; lowest percent 81.0, loop 32 base 72.0"))

    def test_lowest_percent_decides_not_the_ranked_worst(self):
        a = bar_rec("a", 80.5, high=True)
        b = bar_rec("b", 78.0)
        self.assertIs(judge_loop.worst_record([a, b], [], ["a", "b"]), a)
        self.assertEqual(judge_loop.bar_with_base(a, [], [a, b], prior_at(87.2)),
                         (0, "not met: lowest percent 78.0 is more than 7.0 points under the "
                             "loop 32 base 87.2"))

    def test_report_and_gate_use_the_regression_limit(self):
        self._demo_b_32_1(70)
        self.assertIn("; lowest percent 93.0, loop 32 base 100.0 |", self._render())
        code, out = self._check("--skills", "demo-b", "--gate")
        self.assertEqual(code, 0, out)
        self.assertNotIn("demo-b: count inputs differ", out)
        self.assertNotIn("demo-b: recorded count differs", out)
        self._demo_b_32_1(71)
        self.assertIn("not met: lowest percent 92.9 is more than 7.0 points under the loop 32 "
                      "base 100.0", self._render())
        code, out = self._check("--skills", "demo-b", "--gate")
        self.assertEqual(code, 1)
        self.assertIn("demo-b: bar not met", out)
        self.assertNotIn("demo-b: count inputs differ", out)
        self.assertNotIn("demo-b: recorded count differs", out)

    def test_a_prior_loop_on_another_rubric_pin_gives_no_base(self):
        verdict = make_verdict("demo-b", "cli-a:model-a", drops={"D1": (100, "low")},
                               maxima={d: 125 for d in DIMS})
        for tweak, expect_base in (({"rubric_version": 5}, False), ({"spec_sha": "b" * 40}, False),
                                   ({}, True)):
            rec = {**make_record("32.1", "demo-b", 1, "cli-a:model-a", verdict), **tweak}
            self._put(rec)
            found = judge_loop.prior_worst(self.records, "demo-b", "32.1")
            # loop 32 is pinned (4, SHA_A): only the identical pin gives loop 32 as the base
            self.assertEqual(found[0] if found else None, "32" if expect_base else None, tweak)

    def test_loop_32_report_is_byte_identical(self):
        self._report()
        self.assertNotIn("lowest percent", self._render())
        code, out = self._check("--skills", "demo-b", "--judges", "cli-a:model-a")
        self.assertEqual(code, 0, out)

    def test_count_table_shows_the_base_used(self):
        self._demo_b_32_1(70)
        self.assertIn("| demo-b | 32.1 | 100.0 | 0 | 0 | - | "
                      "verdicts/32/demo-b/r1/cli-a_model-a.json | jev not asked (--no-jev) | 1 | "
                      "no deterministic trigger; jev not asked (--no-jev) |", self._render())


if __name__ == "__main__":
    unittest.main()
