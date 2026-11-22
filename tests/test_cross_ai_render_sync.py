"""SPEC R8 / RUN-06 (37-11): a copy rendered through the installer's ensure_runner equals
 the shipped template outside the config block, holds only the CONFIG assignment inside it, and
 gives the same --print-argv output. Reads no planning folder."""

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "skills" / "ai-kit-gsd-curated-config"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import cross_ai, cross_ai_script

from tests.cross_ai_selftest import SIBLING, TEMPLATE, _real_node_executable, run_group, runner_env
from tests.test_cross_ai_runner_e2e import _git_init, write_fake_opencode

_SPEC = importlib.util.spec_from_file_location(
    "check_dogfood", REPO_ROOT / "tools" / "check_dogfood.py")
assert _SPEC is not None and _SPEC.loader is not None
check_dogfood = importlib.util.module_from_spec(_SPEC)
sys.modules["check_dogfood"] = check_dogfood
_SPEC.loader.exec_module(check_dogfood)

# Only wall-clock seconds and generated session UUIDs vary between identical runs.
ELAPSED_RX = re.compile(r"\belapsed=\d+s\b")
GENERATED_SESSION_RX = re.compile(
    r'("--session-id",")[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(")'
    r'|(\bsession=)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'
)
CHOSEN_RUNTIMES = ("copilot", "pi")
RUNTIMES_UNDER_TEST = ("claude", "codex", "copilot", "cursor", "opencode", "pi")
PROBE_IDS = {"pi": "fake/placeholder-model-1", "opencode": "fake/placeholder-model-1"}
LANE_ARGV = ["placeholder-cli-1", "--model", "{model}", "--effort", "{effort}"]
SELF_TEST_REFUSAL = "cross-ai: the self-test is not shipped in this copy; run it from the template"
HARNESS_MARKERS = (b"async function blackBoxSelfTest(", b"const FAKE_PRELUDE = String.raw\x60",
                   b"const CLASSIFY_CASES = [", b"function hermeticEnv(")


def normalized(text: str, generated: bool) -> str:
    text = ELAPSED_RX.sub("elapsed=<n>s", text)
    if generated:
        text = GENERATED_SESSION_RX.sub(
            lambda match: (match.group(1) + "<uuid>" + match.group(2))
            if match.group(1) else match.group(3) + "<uuid>", text)
    return text


def generated_session(runtime: str, args: list[str]) -> bool:
    return runtime in CHOSEN_RUNTIMES and "--session-id" not in args


def matrix_cases() -> list[tuple[str, list[str]]]:
    cases = [
        (f"{runtime}-{role}", ["--runtime", runtime, "--role", role, "--model",
                              PROBE_IDS.get(runtime, "placeholder-model-1")])
        for runtime in RUNTIMES_UNDER_TEST for role in ("review", "execute")
    ]
    cases.extend([
        ("codex-effort", ["--runtime", "codex", "--role", "execute", "--model",
                          "placeholder-model-1", "--effort", "high"]),
        ("cursor-session", ["--runtime", "cursor", "--role", "execute", "--model",
                            "placeholder-model-1", "--session-id", "placeholder-session-1"]),
        ("argv-file", ["--runtime", "placeholder-cli-1", "--argv-file", "lane.json", "--role",
                       "review", "--model", "placeholder-model-1", "--effort", "high"]),
    ])
    return cases


def run_matrix(node: str, script: Path, tmp: str, cases) -> dict[str, tuple[int, str, str]]:
    cwd = os.path.join(tmp, "cwd")
    os.makedirs(cwd, exist_ok=True)
    (Path(cwd) / "lane.json").write_text(json.dumps(LANE_ARGV), encoding="utf-8")
    env = runner_env(tmp)
    results = {}
    for name, args in cases:
        proc = subprocess.run([node, str(script), "--print-argv", *args], cwd=cwd, env=env,
                              capture_output=True, text=True, timeout=60, check=False)
        generated = generated_session(args[args.index("--runtime") + 1], args)
        results[name] = (proc.returncode, normalized(proc.stdout, generated),
                         normalized(proc.stderr, generated))
    return results


def matrix_differences(first: dict, second: dict) -> list[str]:
    differences = []
    for name, (code, out, err) in first.items():
        other_code, other_out, other_err = second[name]
        if code != other_code:
            differences.append(f"{name}: exit {code} != {other_code}")
        elif out != other_out:
            differences.append(f"{name}: stdout differs")
        elif err != other_err:
            differences.append(f"{name}: stderr differs")
    return differences


def sync_problems(template: bytes, copy: bytes) -> list[str]:
    problems = []
    state = cross_ai_script.script_state(copy)
    if state != "pristine":
        problems.append(f"copy is {state}, not pristine")
    try:
        different = (
            cross_ai_script.template_version(copy) != cross_ai_script.template_version(template)
        )
    except ValueError:
        different = True
    if different:
        problems.append("copy template version differs from the template")
    outside = check_dogfood._outside_config(copy)
    if outside is None or outside != check_dogfood._outside_config(template):
        problems.append("copy differs from the template outside the config block")
        return problems
    try:
        config = cross_ai_script.template_config(copy)
    except ValueError:
        problems.append("copy config block is not one CONFIG assignment")
        return problems
    if cross_ai_script.render(template, config) != copy:
        problems.append("copy config block holds more than the CONFIG assignment")
    return problems


def render_copy(project: str) -> tuple[dict, Path]:
    # Use the installer's own render path in the scratch project only.
    result = cross_ai_script.ensure_runner(project)
    return result, Path(project) / cross_ai.SCRIPT_PATH


class TestRenderedCopyInSync(unittest.TestCase):
    def test_rendered_copy_is_in_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            result, copy_path = render_copy(str(project))
            self.assertIs(result["ready"], True)
            self.assertEqual(result["runner"], "add")
            self.assertTrue(copy_path.resolve().is_relative_to(Path(tmp).resolve()))
            template = Path(TEMPLATE).read_bytes()
            copy = copy_path.read_bytes()
            self.assertEqual(cross_ai_script.script_state(copy), "pristine")
            self.assertEqual(cross_ai_script.template_version(copy),
                             cross_ai_script.template_version(template))
            self.assertEqual(sync_problems(template, copy), [])


class TestRenderedCopyWithoutHarness(unittest.TestCase):
    """38-08 / SPEC R8: a rendered copy carries no harness, runs lanes and refuses the self-test."""

    def test_copy_lacks_the_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            _, copy_path = render_copy(str(project))
            copy = copy_path.read_bytes()
            template = Path(TEMPLATE).read_bytes()
            sibling = Path(SIBLING).read_bytes()
            for marker in HARNESS_MARKERS:
                with self.subTest(marker=marker):
                    self.assertNotIn(marker, copy)
                    self.assertIn(marker, sibling)
            self.assertFalse((copy_path.parent / "cross-ai-selftest.mjs").exists())
            self.assertLessEqual(abs(len(copy) - len(template)), 4096)
            self.assertGreater(len(sibling), len(copy) // 2)

    def test_copy_runs_print_argv_and_a_fake_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            _, copy_path = render_copy(str(project))
            node = _real_node_executable()
            if node is None:
                self.skipTest("no node executable")
            env = runner_env(tmp)
            write_fake_opencode(os.path.join(tmp, "bin"))
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            _git_init(repo)
            calls = os.path.join(tmp, "calls.log")
            env["FAKE_CALLS"] = calls
            args = ["--runtime", "opencode", "--role", "review", "--model", "fake/ok"]
            preview = subprocess.run([node, str(copy_path), "--print-argv", *args], cwd=repo,
                                     env=env, capture_output=True, text=True, timeout=60,
                                     check=False)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertTrue(
                any(line.startswith("opencode\t") for line in preview.stdout.splitlines()),
                preview.stdout)
            prompt = os.path.join(tmp, "prompt.txt")
            Path(prompt).write_text("Review the change.\n", encoding="utf-8")
            with open(prompt, encoding="utf-8") as stdin:
                lane = run_group([node, str(copy_path), *args], 120, cwd=repo, env=env, stdin=stdin)
            self.assertEqual(lane.returncode, 0, lane.stderr)
            self.assertTrue(lane.stderr.splitlines()[-1].startswith(
                "AIKIT-XAI status=ok cli=opencode model=fake/ok "), lane.stderr)
            self.assertTrue(lane.stdout.strip(), lane.stderr)
            self.assertIn("opencode fake/ok", Path(calls).read_text(encoding="utf-8"))

    def test_copy_refuses_the_self_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            _, copy_path = render_copy(str(project))
            node = _real_node_executable()
            if node is None:
                self.skipTest("no node executable")
            env = runner_env(tmp)

            def refusal(flag):
                return subprocess.run([node, str(copy_path), flag], cwd=tmp, env=env,
                                      capture_output=True, text=True, timeout=60, check=False)

            for flag in ("--self-test", "--self-test-list"):
                with self.subTest(flag=flag):
                    proc = refusal(flag)
                    self.assertEqual(proc.returncode, 2, proc.stderr)
                    self.assertIn(SELF_TEST_REFUSAL, proc.stderr.splitlines())
            (copy_path.parent / "cross-ai-selftest.mjs").write_bytes(b"")
            proc = refusal("--self-test")
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn(SELF_TEST_REFUSAL, proc.stderr.splitlines())


class TestPrintArgvMatrix(unittest.TestCase):
    def test_matrix_helpers(self):
        cases = matrix_cases()
        self.assertEqual(len(cases), 15)
        self.assertEqual([name for name, _ in cases],
                         [f"{runtime}-{role}" for runtime in RUNTIMES_UNDER_TEST
                          for role in ("review", "execute")]
                         + ["codex-effort", "cursor-session", "argv-file"])
        uuid = "0f8fad5b-d9cb-469f-a165-70867728950e"
        text = f'["--session-id","{uuid}"] session={uuid}'
        self.assertEqual(normalized("x elapsed=12s y", False), "x elapsed=<n>s y")
        self.assertEqual(normalized(text, True), '["--session-id","<uuid>"] session=<uuid>')
        self.assertEqual(normalized(text, False), text)
        self.assertEqual(normalized(f"id {uuid}.", True), f"id {uuid}.")
        for runtime in CHOSEN_RUNTIMES:
            self.assertTrue(generated_session(runtime, ["--runtime", runtime]))
        self.assertFalse(generated_session("pi", ["--session-id", "x"]))
        self.assertFalse(generated_session("cursor", []))
        first = {"a": (0, "o", "e")}
        for second, expected in [((0, "o", "e"), []), ((2, "o", "e"), ["a: exit 0 != 2"]),
                                 ((0, "x", "e"), ["a: stdout differs"]),
                                 ((0, "o", "x"), ["a: stderr differs"])]:
            self.assertEqual(matrix_differences(first, {"a": second}), expected)
        self.assertEqual(matrix_differences(
            {"cursor-session": (0, "o", "session=placeholder-session-1")},
            {"cursor-session": (0, "o", "session=placeholder-session-2")}),
            ["cursor-session: stderr differs"])

    def test_template_and_copy_agree(self):
        node = _real_node_executable()
        if node is None:
            self.skipTest("node is not on PATH: the --print-argv matrix needs a real node")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            _, copy = render_copy(str(project))
            first = run_matrix(node, Path(TEMPLATE), tmp, matrix_cases())
            second = run_matrix(node, copy, tmp, matrix_cases())
            self.assertEqual(matrix_differences(first, second), [])
            for name, (code, _, _) in first.items():
                if name != "claude-execute":
                    self.assertEqual(code, 0, name)
            self.assertIn("model_reasoning_effort=high", first["codex-effort"][1])
            self.assertIn("session=placeholder-session-1", first["cursor-session"][2])
            self.assertIn("placeholder-cli-1", first["argv-file"][1])

    def test_matrix_catches_a_changed_formula(self):
        node = _real_node_executable()
        if node is None:
            self.skipTest("node is not on PATH: the --print-argv matrix needs a real node")
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(TEMPLATE).read_bytes()
            self.assertIn(b"'--trust'", template)
            mutated = template.replace(b"'--trust'", b"'--trusx'", 1)
            path = Path(tmp) / "mutated" / "cross-ai.mjs"
            path.parent.mkdir()
            path.write_bytes(
                cross_ai_script.render(mutated, cross_ai_script.template_config(template)))
            cases = [(name, args) for name, args in matrix_cases() if name.startswith("cursor-")]
            differences = matrix_differences(run_matrix(node, Path(TEMPLATE), tmp, cases),
                                             run_matrix(node, path, tmp, cases))
            self.assertTrue(differences)
            self.assertTrue(all(item.startswith("cursor-") for item in differences))


class TestSyncNonVacuity(unittest.TestCase):
    def test_changed_byte_outside_the_block_fails(self):
        template = Path(TEMPLATE).read_bytes()
        config = cross_ai_script.template_config(template)
        anchor = b"GSD_DEFAULT_TIMEOUT_S = 300;"
        changed = b"GSD_DEFAULT_TIMEOUT_S = 301;"
        self.assertEqual(template.count(anchor), 1)
        good = cross_ai_script.render(template, config)
        cases = [
            ("restamped", cross_ai_script.render(template.replace(anchor, changed, 1), config),
             ["copy differs from the template outside the config block"]),
            ("edited", good.replace(anchor, changed, 1),
             ["copy is edited, not pristine",
              "copy differs from the template outside the config block"]),
        ]
        for name, copy, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(sync_problems(template, copy), expected)

    def test_code_hidden_in_the_config_block_fails(self):
        template = Path(TEMPLATE).read_bytes()
        good = cross_ai_script.render(template, cross_ai_script.template_config(template))
        cases = [
            (b"// <config>\n", b"// <config>\nglobalThis.placeholderHidden = 1;\n",
             "copy config block holds more than the CONFIG assignment"),
            (b"};\n// </config>\n", b"};\nglobalThis.placeholderHidden = 1;\n// </config>\n",
             "copy config block is not one CONFIG assignment"),
        ]
        for anchor, replacement, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(good.count(anchor), 1)
                data = good.replace(anchor, replacement, 1)
                copy = cross_ai_script._stamp(data, cross_ai_script.template_version(data))
                self.assertEqual(sync_problems(template, copy), [expected])

    def test_config_only_edit_passes(self):
        template = Path(TEMPLATE).read_bytes()
        config = cross_ai_script.template_config(template)
        good = cross_ai_script.render(template, config)
        config["heartbeatS"] += 1
        edited = cross_ai_script.render(template, config)
        self.assertNotEqual(good, edited)
        self.assertEqual(sync_problems(template, edited), [])

    def test_each_render_uses_its_own_directory(self):
        template = Path(TEMPLATE).read_bytes()
        before = hashlib.sha256(template).hexdigest()
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            paths = []
            for tmp in (first, second):
                project = Path(tmp) / "project"
                project.mkdir()
                _, path = render_copy(str(project))
                self.assertTrue(path.resolve().is_relative_to(Path(tmp).resolve()))
                self.assertEqual(sync_problems(template, path.read_bytes()), [])
                paths.append(path)
            self.assertNotEqual(paths[0], paths[1])
        self.assertEqual(before, hashlib.sha256(Path(TEMPLATE).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
