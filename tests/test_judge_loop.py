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
        code, out = run_main(["--root", str(self.repo), "check", str(self.records),
                              "--skills", "demo-alpha", "--judges", "cli-a:model-a"])
        self.assertEqual(code, 0)
        self.assertIn("judge-loop: demo-alpha: loop 32 round 1 (rounds 1); judges cli-a:model-a; "
                      "worst 100.0 A; critical 0; high 0; digest current", out)

    def test_check_reports_stale_digest_after_a_skill_edit(self):
        self._prompt()
        write_lane(self._lane(), STATUS_OK, self._verdict_line() + "\n")
        run_main(["--root", str(self.repo), "ingest", "--lane-dir", str(self._lane()),
                  "--records", str(self.records)])
        commit_change(self.repo, "skills/demo-alpha/SKILL.md", "# demo-alpha changed\n")
        code, out = run_main(["--root", str(self.repo), "check", str(self.records),
                              "--skills", "demo-alpha", "--judges", "cli-a:model-a"])
        self.assertEqual(code, 0)
        self.assertIn("digest stale", out)

    def test_check_rejects_a_judge_that_is_not_in_the_list(self):
        self._prompt()
        write_lane(self._lane(), STATUS_OK, self._verdict_line() + "\n")
        run_main(["--root", str(self.repo), "ingest", "--lane-dir", str(self._lane()),
                  "--records", str(self.records)])
        code, out = run_main(["--root", str(self.repo), "check", str(self.records),
                              "--skills", "demo-alpha", "--judges", "cli-b:model-b"])
        self.assertEqual(code, 1)
        self.assertIn("judge cli-a:model-a is not in the judge list", out)


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
        judge_loop.atomic_write_json(path, {"judge": "cli-a_model-a", "verdict": None,
                                            "attempts": []})
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


if __name__ == "__main__":
    unittest.main()
