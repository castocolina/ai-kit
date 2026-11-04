"""The parallel runner must fail the gate when any module fails."""
import ast
import contextlib
import importlib.util
import io
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "ai-kit-spec-review"))
sys.path.insert(0, str(REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"))
import gp_host
from ai_kit_spec import detection

from tests import host_fakes

RUNNER = pathlib.Path(__file__).resolve().parent.parent / "tools" / "run_unittest_parallel.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_unittest_parallel", RUNNER)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(RUNNER), *args],
                          capture_output=True, text=True, check=False, cwd=cwd)


class RunUnittestParallelTest(unittest.TestCase):
    def test_all_pass_exits_zero(self) -> None:
        proc = run("tests.test_arch")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("1/1 modules passed", proc.stdout)

    def test_one_failure_exits_nonzero_and_names_it(self) -> None:
        proc = run("tests.test_arch", "tests.no_such_module")
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("failed: tests.no_such_module", proc.stdout)

    def test_no_modules_is_usage_error(self) -> None:
        self.assertEqual(run().returncode, 2)


class WorkerCountTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner()

    def test_share_of_synthetic_cpu_counts(self) -> None:
        counts = [self.runner.worker_count(20, cpus) for cpus in (24, 4, 1, None)]
        self.assertEqual(counts, [9, 1, 1, 1])

    def test_override_can_lower_but_never_raise(self) -> None:
        self.assertEqual(self.runner.worker_count(20, 24, share_env="0.9"), 9)
        self.assertEqual(self.runner.worker_count(20, 24, share_env="0.25"), 6)

    def test_unusable_override_keeps_the_cap(self) -> None:
        for share_env in ("abc", "0", "-1"):
            self.assertEqual(self.runner.worker_count(20, 24, share_env=share_env), 9, share_env)

    def test_never_more_workers_than_modules(self) -> None:
        self.assertEqual(self.runner.worker_count(3, 24), 3)


class AvailableCpusTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner()

    def test_prefers_process_cpu_count(self) -> None:
        with unittest.mock.patch.object(
            self.runner.os, "process_cpu_count", lambda: 7, create=True
        ):
            self.assertEqual(self.runner.available_cpus(), 7)

    def test_falls_back_to_affinity_then_cpu_count(self) -> None:
        with self._without("process_cpu_count"), unittest.mock.patch.object(
            self.runner.os, "sched_getaffinity", lambda _pid: {0, 1, 2}, create=True
        ):
            self.assertEqual(self.runner.available_cpus(), 3)
        with self._without("process_cpu_count"), self._without("sched_getaffinity"), \
                unittest.mock.patch.object(self.runner.os, "cpu_count", lambda: 5):
            self.assertEqual(self.runner.available_cpus(), 5)

    def _without(self, name: str) -> unittest.mock._patch:
        return unittest.mock.patch.object(self.runner.os, name, None, create=True)


class GroupingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner()

    def test_every_module_in_exactly_one_group(self) -> None:
        discovered = self.runner.discover_modules()
        groups = self.runner.group_modules(discovered)
        assigned = [module for names in groups.values() for module in names]
        self.assertCountEqual(assigned, discovered)
        self.assertEqual(len(assigned), len(set(assigned)))

    def test_unit_excludes_every_explicit_set(self) -> None:
        groups = self.runner.group_modules(self.runner.discover_modules())
        explicit = set().union(*self.runner.EXPLICIT_GROUPS.values())
        self.assertTrue(explicit.isdisjoint(groups["unit"]))


class GroupModeTest(unittest.TestCase):
    def test_arch_group_passes(self) -> None:
        proc = run("--group", "arch")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("1/1 modules passed", proc.stdout)

    def test_unknown_group_is_usage_error(self) -> None:
        self.assertEqual(run("--group", "nope").returncode, 2)

    def test_mixing_group_and_module_names_is_usage_error(self) -> None:
        self.assertEqual(run("--group", "arch", "tests.test_arch").returncode, 2)

    def test_module_temp_directories_are_removed(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as parent:
            tests_dir = pathlib.Path(parent) / "tests"
            tests_dir.mkdir()
            (tests_dir / "__init__.py").write_text("")
            (tests_dir / "test_tempdir.py").write_text(
                "import tempfile\n"
                "path = tempfile.mkdtemp()\n"
                "print('CREATED_TEMP_DIR=' + path)\n"
                "import unittest\n"
                "class TestSynthetic(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(path)\n"
            )
            _, rc, output, _ = runner.run_module(
                "tests.test_tempdir", cwd=pathlib.Path(parent)
            )
            self.assertEqual(rc, 0, output)
            created = next(
                line.split("=", 1)[1] for line in output.splitlines()
                if line.startswith("CREATED_TEMP_DIR=")
            )
            self.assertFalse(pathlib.Path(created).exists())
            self.assertEqual(list(pathlib.Path(parent).iterdir()), [tests_dir])

    def test_module_with_no_tests_fails_its_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = pathlib.Path(tmp) / "tests"
            tests_dir.mkdir()
            (tests_dir / "__init__.py").write_text("")
            (tests_dir / "test_empty.py").write_text("# no TestCase in here\n")
            _, rc, output, _ = load_runner().run_module("tests.test_empty", cwd=pathlib.Path(tmp))
        self.assertNotEqual(rc, 0, output)
        self.assertIn("NO TESTS RAN", output)

    def test_runs_from_a_foreign_cwd(self) -> None:
        # Modules resolve against the repo root, not the caller's cwd (C-WR-07).
        with tempfile.TemporaryDirectory() as tmp:
            proc = run("--group", "arch", cwd=tmp)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("1/1 modules passed", proc.stdout)

    def test_a_hung_module_fails_with_a_timeout_line(self) -> None:
        runner = load_runner()
        with unittest.mock.patch.object(runner, "MODULE_TIMEOUT_SECS", 0.01):
            _, rc, output, _ = runner.run_module("tests.test_arch")
        self.assertEqual(rc, 124)
        self.assertIn("timed out", output)

    def test_stale_exception_name_exits_2(self) -> None:
        runner = load_runner()
        stale = runner.EXPLICIT_GROUPS["arch"] | {"tests.test_does_not_exist"}
        err = io.StringIO()
        with unittest.mock.patch.dict(runner.EXPLICIT_GROUPS, {"arch": stale}), \
                contextlib.redirect_stderr(err):
            rc = runner.main(["--group", "arch"])
        self.assertEqual(rc, 2)
        self.assertIn("tests.test_does_not_exist", err.getvalue())


_PASSING = (
    "import unittest\n"
    "class TestSynthetic(unittest.TestCase):\n"
    "    def test_ok(self):\n"
    "{body}\n"
)


class TripwireTest(unittest.TestCase):
    """A real host CLI call from a test fails its module (D-04)."""

    def _run(self, body: str) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = pathlib.Path(tmp) / "tests"
            tests_dir.mkdir()
            (tests_dir / "__init__.py").write_text("")
            (tests_dir / "test_synth.py").write_text(
                _PASSING.format(body="\n".join("        " + ln for ln in body.splitlines()))
            )
            _, rc, output, _ = load_runner().run_module("tests.test_synth", cwd=pathlib.Path(tmp))
        return rc, output

    def test_a_host_call_turns_a_passing_module_into_rc_1(self) -> None:
        rc, output = self._run(
            "import subprocess\n"
            "subprocess.run(['claude', '--version'], check=False)"
        )
        self.assertEqual(rc, 1, output)
        self.assertIn("tripwire:", output)
        self.assertIn("claude --version", output)

    def test_a_fake_earlier_on_path_wins(self) -> None:
        rc, output = self._run(
            "import os, subprocess, tempfile\n"
            "d = tempfile.mkdtemp()\n"
            "p = os.path.join(d, 'claude')\n"
            "open(p, 'w').write('#!/bin/sh\\nexit 0\\n')\n"
            "os.chmod(p, 0o755)\n"
            "env = dict(os.environ, PATH=d + os.pathsep + os.environ['PATH'])\n"
            "self.assertEqual(subprocess.run(['claude'], env=env, check=False).returncode, 0)"
        )
        self.assertEqual(rc, 0, output)
        self.assertNotIn("tripwire:", output)

    def test_a_module_with_no_host_call_is_clean(self) -> None:
        rc, output = self._run("pass")
        self.assertEqual(rc, 0, output)
        self.assertNotIn("tripwire:", output)

    def test_a_call_from_a_rebuilt_env_is_still_logged(self) -> None:
        rc, output = self._run(
            "import os, subprocess\n"
            "path = os.environ['PATH']\n"
            "subprocess.run(['codex', 'debug', 'models'], env={'PATH': path}, check=False)"
        )
        self.assertEqual(rc, 1, output)
        self.assertIn("codex debug models", output)

    def test_report_caps_the_logged_lines(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            log = pathlib.Path(tmp) / "calls.log"
            log.write_text("".join(f"claude call{n}\n" for n in range(25)))
            report = runner._tripwire_report(log)
        self.assertEqual(report.count("claude call"), 20)
        self.assertIn("... and 5 more calls", report)

    def test_which_resolves_every_host_into_the_tripwire_folder(self) -> None:
        rc, output = self._run(
            "import shutil\n"
            "print('WHICH=' + shutil.which('claude'))"
        )
        self.assertEqual(rc, 0, output)
        self.assertNotIn("tripwire:", output)
        found = next(ln.split("=", 1)[1] for ln in output.splitlines() if ln.startswith("WHICH="))
        self.assertTrue(found.endswith("/tripwire/bin/claude"), found)


def _baseline(runner, source: dict[str, str], temp: pathlib.Path) -> dict[str, str]:
    """`baseline_env` over `source` with a temp_dir and tripwire bin under `temp`."""
    return runner.baseline_env(source, temp, temp / "tripwire" / "bin")


class BaselineEnvTest(unittest.TestCase):
    """Every module starts from one pinned environment (D-06)."""

    # The approved forwards of KEPT_ENV_NAMES: each must come through as the caller set it.
    PINNED_FORWARDS = (
        "PUPPETEER_CACHE_DIR", "UV_CACHE_DIR", "UV_PYTHON_INSTALL_DIR", "VOLTA_HOME",
        "PUPPETEER_EXECUTABLE_PATH",
    )

    def setUp(self) -> None:
        self.runner = load_runner()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.temp = pathlib.Path(self._tmp.name) / "module"
        self.temp.mkdir()
        self.caller_home = pathlib.Path(self._tmp.name) / "caller-home"
        self.caller_home.mkdir()

    def _env(self, **extra: str) -> dict[str, str]:
        source = {"HOME": str(self.caller_home), "PATH": "/usr/bin", **extra}
        return _baseline(self.runner, source, self.temp)

    def test_signals_git_state_and_home_overrides_are_dropped(self) -> None:
        env = self._env(
            CLAUDECODE="1", CODEX_THREAD_ID="t", GIT_INDEX_FILE="/x", GIT_DIR="/y",
            GIT_EXEC_PATH="/exec", XDG_CONFIG_HOME="/xdg", CODEX_HOME="/codex",
            AI_KIT_TEST_CPU_SHARE="0.2", UNRELATED="keep",
        )
        for name in ("CLAUDECODE", "CODEX_THREAD_ID", "GIT_INDEX_FILE", "GIT_DIR",
                     "XDG_CONFIG_HOME", "CODEX_HOME"):
            self.assertNotIn(name, env)
        self.assertEqual(env["GIT_EXEC_PATH"], "/exec")
        self.assertEqual(env["AI_KIT_TEST_CPU_SHARE"], "0.2")
        self.assertEqual(env["UNRELATED"], "keep")

    def test_credentials_and_backend_urls_are_dropped(self) -> None:
        names = ("JEV_API_KEY", "JEV_API_URL", "TYPESAFE_API_KEY", "JEV_LAYA_URL")
        env = self._env(**dict.fromkeys(names, "secret"))
        for name in names:
            self.assertNotIn(name, env)

    def test_status_line_prefix_overrides_and_credential_file_are_dropped(self) -> None:
        names = ("CC_AI_KIT_CONFIG_FILE", "CC_AI_KIT_EXTERNAL_DIR",
                 "AI_KIT_CURSOR_CONFIG_FILE", "JEV_API_KEY_FILE")
        env = self._env(**dict.fromkeys(names, "/sentinel"))
        for name in names:
            self.assertNotIn(name, env)

    def test_pinned_values(self) -> None:
        env = self._env()
        self.assertEqual(env["HOME"], str(self.temp / "home"))
        self.assertTrue((self.temp / "home").is_dir())
        self.assertEqual(env["AI_KIT_REFUSE_REAL_HOME"], "1")
        for name in ("TMPDIR", "TEMP", "TMP"):
            self.assertEqual(env[name], str(self.temp))
        self.assertEqual(env["GIT_CEILING_DIRECTORIES"], str(self.temp.parent))
        self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(env["GIT_AUTHOR_NAME"], "ai-kit test")
        self.assertEqual(env["GIT_COMMITTER_EMAIL"], "test@ai-kit.invalid")
        self.assertTrue(env["PATH"].startswith(str(self.temp / "tripwire" / "bin") + os.pathsep))
        self.assertTrue(env["PATH"].endswith("/usr/bin"))

    def test_caller_set_forwards_are_kept_as_set(self) -> None:
        env = self._env(**{name: "/caller/" + name for name in self.PINNED_FORWARDS})
        for name in self.PINNED_FORWARDS:
            self.assertEqual(env[name], "/caller/" + name)

    def test_unset_forwards_are_computed_from_the_caller_home(self) -> None:
        (self.caller_home / ".volta").mkdir()
        env = self._env()
        self.assertEqual(env["PUPPETEER_CACHE_DIR"], str(self.caller_home / ".cache/puppeteer"))
        self.assertEqual(env["UV_CACHE_DIR"], str(self.caller_home / ".cache/uv"))
        self.assertEqual(env["VOLTA_HOME"], str(self.caller_home / ".volta"))
        self.assertNotIn("UV_PYTHON_INSTALL_DIR", env)

    def test_tool_cache_forwards_is_public_and_needs_no_home(self) -> None:
        self.assertEqual(self.runner.tool_cache_forwards({}), {})
        (self.caller_home / ".local/share/uv/python").mkdir(parents=True)
        forwards = self.runner.tool_cache_forwards({"HOME": str(self.caller_home)})
        self.assertEqual(
            forwards["UV_PYTHON_INSTALL_DIR"], str(self.caller_home / ".local/share/uv/python")
        )

    def test_synthetic_module_never_sees_the_callers_state(self) -> None:
        tools = pathlib.Path(__file__).resolve().parent.parent / "tools"
        sentinel = "/sentinel/owner-state"
        body = (
            "import os, sys, unittest\n"
            f"sys.path.insert(0, {str(tools)!r})\n"
            "import claude_host\n"
            "import common_config\n"
            "class TestSynthetic(unittest.TestCase):\n"
            "    def test_env(self):\n"
            "        for name in ('CLAUDECODE', 'GIT_INDEX_FILE', 'CC_AI_KIT_CONFIG_FILE'):\n"
            "            print('SEEN_' + name + '=' + repr(os.environ.get(name)))\n"
            "        print('HOME=' + os.environ['HOME'])\n"
            "        print('CFG=' + common_config.cfg_config_path(os.environ, claude_host.SPEC))\n"
        )
        caller = {"CLAUDECODE": "1", "GIT_INDEX_FILE": sentinel,
                  "CC_AI_KIT_CONFIG_FILE": sentinel + "/cfg.toml"}
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = pathlib.Path(tmp) / "tests"
            tests_dir.mkdir()
            (tests_dir / "__init__.py").write_text("")
            (tests_dir / "test_synth_env.py").write_text(body)
            with unittest.mock.patch.dict(os.environ, caller):
                _, rc, output, _ = self.runner.run_module(
                    "tests.test_synth_env", cwd=pathlib.Path(tmp)
                )
        self.assertEqual(rc, 0, output)
        self.assertNotIn(sentinel, output)
        for name in ("CLAUDECODE", "GIT_INDEX_FILE", "CC_AI_KIT_CONFIG_FILE"):
            self.assertIn(f"SEEN_{name}=None", output)
        lines = [ln for ln in output.splitlines() if ln.startswith(("HOME=", "CFG="))]
        values = dict(ln.split("=", 1) for ln in lines)
        self.assertTrue(values["CFG"].startswith(values["HOME"] + os.sep), output)


ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*_(HOME|DIR|FILE|PATH|ROOT|KEY|TOKEN|URL|SECRET)$")
KEPT_REASON_KINDS = ("not an env var:", "approved forward:", "set by the baseline:")


def env_name_hits(source: str) -> set[str]:
    """Every string constant in `source` shaped like an env name that points somewhere."""
    return {
        node.value for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and ENV_NAME_RE.match(node.value)
    }


def config_spec_prefixes(source: str) -> set[str]:
    """The env prefixes of every `ConfigSpec(...)` call: argument 0 and argument 7
    (`provider_env`), positional or keyword."""
    prefixes: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "ConfigSpec"):
            continue
        values = list(node.args[:1]) + list(node.args[7:8])
        values += [kw.value for kw in node.keywords if kw.arg in ("env_prefix", "provider_env")]
        prefixes |= {v.value for v in values
                     if isinstance(v, ast.Constant) and isinstance(v.value, str)}
    return prefixes


def _py_sources(*tops: str) -> list[str]:
    root = pathlib.Path(__file__).resolve().parent.parent
    return [p.read_text(encoding="utf-8") for top in tops for p in (root / top).rglob("*.py")]


class DriftTest(unittest.TestCase):
    """Every list the runner copies is pinned against its source (D-04, D-06)."""

    KEPT_ENV_NAMES = {
        "AI_KIT_REFUSE_REAL_HOME": "set by the baseline: forced to 1",
        "CACHE_ROOT": "not an env var: a module constant name in stack_cache.__all__",
        "CONFIG_FILE": "not an env var: the suffix of the prefix-built <prefix>CONFIG_FILE, "
                       "dropped through HOST_CONFIG_ENV_PREFIXES",
        "RUNBOOK_RELATIVE_PATH": "not an env var: a module constant name",
        "PUPPETEER_CACHE_DIR": "approved forward: Puppeteer's browser cache",
        "UV_CACHE_DIR": "approved forward: uv's package cache",
        "UV_PYTHON_INSTALL_DIR": "approved forward: uv's Python installs",
        "VOLTA_HOME": "approved forward: the volta node shim's home",
        "PUPPETEER_EXECUTABLE_PATH": "approved forward: a browser binary path, "
                                     "not host configuration",
        "GIT_EXEC_PATH": "set by the baseline: the one GIT_ variable git itself needs",
    }
    KEPT_PREFIXES = {
        "AI_KIT_SEGMENT_": "written only into provider children by common_render, "
                           "never read from the caller env",
    }

    def setUp(self) -> None:
        self.runner = load_runner()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.temp = pathlib.Path(self._tmp.name)

    def _survives(self, name: str) -> bool:
        source = {name: "x", "HOME": str(self.temp), "PATH": "/usr/bin"}
        return name in _baseline(self.runner, source, self.temp)

    def undecided_names(self, names: set[str]) -> list[str]:
        """Names that neither the baseline drops nor KEPT_ENV_NAMES explains."""
        return sorted(n for n in names if self._survives(n) and n not in self.KEPT_ENV_NAMES)

    def undecided_prefixes(self, prefixes: set[str]) -> list[str]:
        covered = tuple(self.runner.HOST_CONFIG_ENV_PREFIXES)
        return sorted(p for p in prefixes
                      if not p.startswith(covered) and p not in self.KEPT_PREFIXES)

    def test_host_names_and_signals_match_their_sources(self) -> None:
        table = {n for row in detection.RUNTIMES.values() for n in row.binaries}
        mapped = set(gp_host.HOST_BINARY.values())
        self.assertEqual(self.runner.HOST_CLI_NAMES, table | mapped)
        self.assertEqual(host_fakes.HOST_NAMES, tuple(sorted(self.runner.HOST_CLI_NAMES)))
        self.assertEqual(self.runner.HOST_SIGNAL_VARS, detection.HOST_SIGNAL_ENV_VARS)

    def test_every_config_spec_prefix_is_dropped_or_kept(self) -> None:
        found = set().union(*(config_spec_prefixes(s) for s in _py_sources("tools")))
        self.assertTrue(found, "the scan found no ConfigSpec prefix")
        self.assertEqual(self.undecided_prefixes(found), [])

    def test_prefix_scan_flags_a_new_prefix(self) -> None:
        text = 'ConfigSpec("FOO_", "f.toml", S, L, R, "a", "b", "BAR_")\n' \
               'ConfigSpec("X", "f", S, L, R, "a", "b", provider_env="BAZ_")'
        self.assertEqual(self.undecided_prefixes(config_spec_prefixes(text)),
                         ["BAR_", "BAZ_", "FOO_", "X"])

    def test_every_env_name_is_dropped_or_kept(self) -> None:
        found = set().union(*(env_name_hits(s) for s in _py_sources("tools", "skills")))
        self.assertTrue(found, "the scan found no env name")
        self.assertEqual(self.undecided_names(found), [])

    def test_name_scan_flags_a_new_path_and_a_new_credential_name(self) -> None:
        hits = env_name_hits('A = "FOO_CONFIG_FILE"\nB = "FOO_API_KEY"\nC = "not_a_name"')
        self.assertEqual(self.undecided_names(hits), ["FOO_API_KEY", "FOO_CONFIG_FILE"])

    def test_kept_reasons_use_one_of_three_kinds_and_forwards_are_pinned(self) -> None:
        for name, reason in self.KEPT_ENV_NAMES.items():
            self.assertTrue(reason.startswith(KEPT_REASON_KINDS), f"{name}: {reason}")
        forwards = {n for n, r in self.KEPT_ENV_NAMES.items() if r.startswith("approved forward:")}
        self.assertEqual(forwards, set(BaselineEnvTest.PINNED_FORWARDS))


if __name__ == "__main__":
    unittest.main()
