"""Parity of ai-kit's one user-dir rule across every copy that cannot share code (SPEC R10,
D-19, D-27; plan 33-03). The rule: an absolute XDG_CONFIG_HOME (surrounding whitespace removed)
gives <xdg>/ai-kit; otherwise an absolute HOME gives <home>/.config/ai-kit; otherwise there is
no user dir. HOME comes from the environment only: every copy runs with the ambient home lookups
patched to fail, so no test reads a real config.

Copies: config_io.cfg_config_base, local_secrets.secrets_env_path, jev_review._config_dir,
jev_config.cfg_config_base (the jev-fast-decision copy, plan 34-01), the runner's aiKitConfigDir
(node) and, in Task 2, tools/common_config.cfg_ai_kit_dir and setup.resolve_paths."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_DIR = os.path.join(REPO, "skills", "ai-kit-spec-review")
JEV_SCRIPT = os.path.join(REPO, "skills", "jev-fast-decision", "scripts", "jev_review.py")
JEV_CONFIG = os.path.join(REPO, "skills", "jev-fast-decision", "scripts", "jev_config.py")
RUNNER_TEMPLATE = os.path.join(REPO, "skills", "ai-kit-spec-review", "references", "cross-ai.mjs")
ERROR = "ERROR"

sys.path.insert(0, SPEC_DIR)
from ai_kit_spec import config_io, local_secrets

sys.path.insert(0, os.path.join(REPO, "tools"))
import claude_host
import common_config

# (environment, expected user dir or ERROR). Synthetic strings only; nothing is created on disk.
CASES = [
    ({"XDG_CONFIG_HOME": "/abs/xdg", "HOME": "/srv/u"}, "/abs/xdg/ai-kit"),
    ({"XDG_CONFIG_HOME": " /abs/xdg ", "HOME": "/srv/u"}, "/abs/xdg/ai-kit"),
    ({"XDG_CONFIG_HOME": "rel/xdg", "HOME": "/srv/u"}, "/srv/u/.config/ai-kit"),
    ({"XDG_CONFIG_HOME": "", "HOME": "/srv/u"}, "/srv/u/.config/ai-kit"),
    ({"XDG_CONFIG_HOME": "   ", "HOME": "/srv/u"}, "/srv/u/.config/ai-kit"),
    ({"XDG_CONFIG_HOME": "/srv/u/.config", "HOME": "/srv/u"}, "/srv/u/.config/ai-kit"),
    ({"HOME": "/srv/u"}, "/srv/u/.config/ai-kit"),
    ({"HOME": "rel-home"}, ERROR),
    # C1-3: HOME unset or empty is no absolute home in every copy (no ambient fallback).
    ({"XDG_CONFIG_HOME": "/abs/xdg"}, "/abs/xdg/ai-kit"),
    ({}, ERROR),
    ({"HOME": ""}, ERROR),
    ({"XDG_CONFIG_HOME": "rel/xdg", "HOME": ""}, ERROR),
]


def _load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


jev_review = _load_file("jev_review_parity", JEV_SCRIPT)
jev_config = _load_file("jev_config_parity", JEV_CONFIG)


def _outcome(fn):
    """The directory fn returns, or ERROR when it signals no user dir. An AssertionError
    (an ambient home lookup) is not caught: it fails the test."""
    try:
        value = fn()
    except (config_io.ConfigError, OSError, SystemExit):
        return ERROR
    return value or ERROR


def _local_secrets_dir(env):
    path = local_secrets.secrets_env_path(env)
    return os.path.dirname(path) if path is not None else None


def _jev_dir(env):
    with mock.patch.dict(os.environ, env, clear=True):
        return jev_review._config_dir()


def _runner_function_source():
    with open(RUNNER_TEMPLATE, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith("function aiKitConfigDir(env) {"))
    end = next(i for i in range(start, len(lines)) if lines[i] == "}")
    return "\n".join(lines[start:end + 1])


def _runner_outcomes(envs):
    # A throwing home function fails the node run (non-zero exit), so an ambient home lookup
    # cannot pass silently.
    script = ("const path = require('node:path'); const os = require('node:os');\n"
              "os.homedir = () => { throw new Error('ambient home lookup'); };\n"
              + _runner_function_source() + "\n"
              "const cases = JSON.parse(process.argv[1]);\n"
              "process.stdout.write(JSON.stringify(cases.map((env) => aiKitConfigDir(env))));\n")
    proc = subprocess.run(
        ["node", "-e", script, json.dumps(envs)],
        capture_output=True, text=True, timeout=30, check=True,
        env={"PATH": os.environ.get("PATH", ""), "AI_KIT_REFUSE_REAL_HOME": "1"})
    return [value or ERROR for value in json.loads(proc.stdout)]


class TestConfigDirParity(unittest.TestCase):
    def _assert_table(self, label, outcomes):
        self.assertEqual(len(outcomes), len(CASES))
        for (env, expected), got in zip(CASES, outcomes, strict=True):
            self.assertEqual(got, expected, f"{label} disagrees with the rule for {env}")

    def test_config_io_copy(self):
        with mock.patch("os.path.expanduser", side_effect=AssertionError("ambient home lookup")):
            outcomes = [_outcome(lambda env=env: config_io.cfg_config_base(env))
                        for env, _ in CASES]
        self._assert_table("config_io.cfg_config_base", outcomes)

    def test_local_secrets_copy(self):
        with mock.patch("os.path.expanduser", side_effect=AssertionError("ambient home lookup")):
            outcomes = [_outcome(lambda env=env: _local_secrets_dir(env)) for env, _ in CASES]
        self._assert_table("local_secrets.secrets_env_path", outcomes)

    def test_jev_review_copy(self):
        with mock.patch("os.path.expanduser", side_effect=AssertionError("ambient home lookup")):
            outcomes = [_outcome(lambda env=env: _jev_dir(env)) for env, _ in CASES]
        self._assert_table("jev_review._config_dir", outcomes)

    def test_jev_config_copy(self):
        def user_dir(env):  # the copy has its own ConfigError class, so map it here
            try:
                return jev_config.cfg_config_base(env)
            except jev_config.ConfigError:
                return ERROR

        with mock.patch("os.path.expanduser", side_effect=AssertionError("ambient home lookup")):
            outcomes = [user_dir(env) for env, _ in CASES]
        self._assert_table("jev_config.cfg_config_base", outcomes)

    def test_common_config_copy(self):
        with mock.patch("os.path.expanduser", side_effect=AssertionError("ambient home lookup")):
            outcomes = [_outcome(lambda env=env: common_config.cfg_ai_kit_dir(env))
                        for env, _ in CASES]
        self._assert_table("common_config.cfg_ai_kit_dir", outcomes)

    def test_setup_resolve_paths_follows_common_config(self):
        setup = _load_file("setup_parity", os.path.join(REPO, "tools", "setup.py"))

        def config_dir(env):
            try:
                return setup.resolve_paths(env).config_dir
            except SystemExit as exc:
                self.assertIn("no absolute home directory", str(exc))
                return ERROR

        outcomes = [config_dir(env) for env, _ in CASES]
        self._assert_table("setup.resolve_paths", outcomes)
        for env, _ in CASES:
            if common_config.cfg_ai_kit_dir(env):
                self.assertEqual(setup.resolve_paths(env).config_dir,
                                 common_config.cfg_ai_kit_dir(env))

    def test_status_line_without_home_reads_defaults(self):
        self.assertEqual(common_config.cfg_config_path({"HOME": "rel-home"}, claude_host.SPEC),
                         "")
        self.assertEqual(common_config.cfg_config_path({}, claude_host.SPEC), "")
        self.assertEqual(common_config.cfg_load_toml(""), {})

    def test_runner_copy(self):
        if shutil.which("node") is None:
            self.skipTest("node not on PATH")
        self._assert_table("runner aiKitConfigDir", _runner_outcomes([env for env, _ in CASES]))

    def test_rule_check_is_not_vacuous(self):
        def relative_xdg_rule(env):  # deliberately different: takes a relative XDG as is
            xdg = env.get("XDG_CONFIG_HOME", "").strip()
            if xdg:
                return os.path.join(xdg, "ai-kit")
            home = env.get("HOME", "")
            return os.path.join(home, ".config", "ai-kit") if os.path.isabs(home) else ERROR

        def ambient_home_rule(env):  # deliberately different: an empty HOME falls back
            xdg = env.get("XDG_CONFIG_HOME", "").strip()
            if os.path.isabs(xdg):
                return os.path.join(xdg, "ai-kit")
            home = env.get("HOME") or os.path.expanduser("~")
            return os.path.join(home, ".config", "ai-kit") if os.path.isabs(home) else ERROR

        relative_case = {"XDG_CONFIG_HOME": "rel/xdg", "HOME": "/srv/u"}
        self.assertNotEqual(relative_xdg_rule(relative_case), "/srv/u/.config/ai-kit")
        with mock.patch("os.path.expanduser", return_value="/pw/home"):
            self.assertNotEqual(ambient_home_rule({"HOME": ""}), ERROR)

    def test_both_secret_readers_read_one_file(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        xdg = os.path.join(home, "xdg")
        os.makedirs(os.path.join(xdg, "ai-kit"))
        path = os.path.join(xdg, "ai-kit", "secrets.env")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("ARTIFICIAL_ANALYSIS_API_KEY=sentinel-123\n")
        os.chmod(path, 0o600)
        env = {"HOME": home, "XDG_CONFIG_HOME": xdg}
        self.assertEqual(local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY"),
                         "sentinel-123")
        with mock.patch.dict(os.environ, env, clear=True):
            jev_path = os.path.join(jev_review._config_dir(), "secrets.env")
        self.assertEqual(jev_path, local_secrets.secrets_env_path(env))
        self.assertEqual(jev_review._secrets_env_value(jev_path, "ARTIFICIAL_ANALYSIS_API_KEY"),
                         ("sentinel-123", None))


if __name__ == "__main__":
    unittest.main()
