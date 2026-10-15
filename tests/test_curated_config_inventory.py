"""Inventory tracer, gsd-core resolution, probe fail-closed paths, and real-gsd smoke (17-03)."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import catalog_adapter, cli, gsd_catalog, host, plan_io, presets
from ai_kit_spec import gsd_tools

from tests.test_ai_kit_gsd_curated_config import _RealGsdTestCase

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def make_gsd_install(install_root, version="1.16.0", *, include_config_schema=True):
    """Minimal fake gsd-core tree under `install_root` (the install root, not project root)."""
    bin_dir = os.path.join(install_root, "bin")
    lib_dir = os.path.join(bin_dir, "lib")
    os.makedirs(lib_dir, exist_ok=True)
    with open(os.path.join(install_root, "VERSION"), "w", encoding="utf-8") as fh:
        fh.write(version + "\n")
    with open(os.path.join(bin_dir, "gsd-tools.cjs"), "w", encoding="utf-8") as fh:
        fh.write("// fake\n")
    with open(os.path.join(lib_dir, "model-catalog.cjs"), "w", encoding="utf-8") as fh:
        fh.write("// fake\n")
    if include_config_schema:
        with open(os.path.join(lib_dir, "config-schema.cjs"), "w", encoding="utf-8") as fh:
            fh.write("// fake\n")
    return os.path.join(bin_dir, "gsd-tools.cjs")


_FRESH_FETCH_JSON = json.dumps(
    {
        "models_dev_ok": True,
        "artificial_analysis_ok": True,
        "fetch_skipped": False,
    }
)


def seed_cache(xdg_cache_home, runtimes, catalog):
    """Seed ai-kit spec cache files under a scratch ``XDG_CACHE_HOME``."""
    cache_dir = os.path.join(xdg_cache_home, "ai-kit", "spec")
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, "runtimes.json"), "w", encoding="utf-8") as fh:
        json.dump(runtimes, fh)
    with open(os.path.join(cache_dir, "model-catalog.json"), "w", encoding="utf-8") as fh:
        json.dump(catalog, fh)
    return cache_dir


def _inventory_env(home, runtimes=None, catalog=None):
    xdg = os.path.join(home, "xdg-cache")
    seed_cache(
        xdg,
        runtimes if runtimes is not None else {"clis": {}},
        catalog if catalog is not None else {"_meta": {"schema_version": 1}},
    )
    return {"HOME": home, "PATH": "", "XDG_CACHE_HOME": xdg}


def _default_tables_from_argv(argv):
    keys = json.loads(argv[6])
    return json.dumps(
        {
            "runtime_profile_map": {"codex": {"opus": {"model": "gpt-5.6-sol"}}},
            "model_profiles": {"gsd-planner": {"adaptive": "opus"}},
            "agent_to_phase_type": {"gsd-planner": "planning"},
            "valid_keys": {"accepted": keys, "rejected": []},
        }
    )


class FakeRun:
    """Records subprocess argv; answers git, node `-e`, and ai-kit-spec.py calls."""

    def __init__(self, git_answers=None, node_stdout=None, spec_answers=None):
        self.argv_log: list[list] = []
        self.kw_log: list[dict] = []
        self.git_answers = git_answers or {}
        self.node_stdout = node_stdout
        self.spec_answers = spec_answers or {}

    def _default_spec_answer(self, cmd):
        sub = cmd[2]
        if sub == "detect-runtimes":
            return 0, "{}"
        if sub == "fetch-model-catalog":
            return 0, _FRESH_FETCH_JSON
        return 1, ""

    def _answer_spec(self, cmd):
        if len(cmd) < 3 or not str(cmd[1]).endswith("ai-kit-spec.py"):
            return None
        sub = cmd[2]
        answer = self.spec_answers.get(sub, self._default_spec_answer(cmd))
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def __call__(self, cmd, **kw):
        self.argv_log.append(list(cmd))
        self.kw_log.append(dict(kw))
        if cmd and cmd[0] == "git":
            key = cmd[-1]
            if key in self.git_answers:
                rc, out = self.git_answers[key]
                return subprocess.CompletedProcess(cmd, rc, out, "")
            return subprocess.CompletedProcess(cmd, 128, "", "")
        spec = self._answer_spec(cmd)
        if spec is not None:
            rc, out = spec
            return subprocess.CompletedProcess(cmd, rc, out, "")
        if len(cmd) >= 3 and cmd[0] == "node" and cmd[1] == "-e":
            out = self.node_stdout
            if callable(out):
                out = out(cmd)
            elif out is None:
                out = _default_tables_from_argv(cmd)
            return subprocess.CompletedProcess(cmd, 0, out, "")
        return subprocess.CompletedProcess(cmd, 1, "", "")


def run_inventory(project, env, fake, *extra):
    stdout = io.StringIO()
    stderr = io.StringIO()
    argv = ["inventory", "--project-dir", project, *extra]
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(
            argv,
            which_fn=lambda name: "node" if name == "node" else None,
            env_fn=lambda: dict(env),
            run_fn=fake,
        )
    err = stderr.getvalue()
    raw = stdout.getvalue()
    parsed = json.loads(raw) if code == 0 and raw.strip() else None
    return code, parsed, err


def real_gsd_run(child_env, node_bin, fallback=None):
    """Allow only real node/git subprocesses in real-gsd tests."""

    def _run(cmd, **kw):
        if cmd and (cmd[0] == node_bin or cmd[0] == "git"):
            merged = {**kw, "env": child_env}
            return subprocess.run(cmd, **merged)
        if fallback is not None:
            return fallback(cmd, **kw)
        raise AssertionError(f"real-gsd test reached a non-node/git subprocess: {cmd[:3]}")

    return _run


class TestInventoryTracer(unittest.TestCase):
    def test_end_to_end_fake_claude_gsd_core(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        install = os.path.join(project, ".claude", "gsd-core")
        make_gsd_install(install)
        env = _inventory_env(home)
        fake = FakeRun()
        code, parsed, _err = run_inventory(project, env, fake, "--host", "opencode")
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertEqual(parsed["schema_version"], 1)
        self.assertEqual(parsed["host"], "opencode")
        self.assertEqual(parsed["host_source"], "flag")
        self.assertEqual(parsed["gsd_core"]["path"], install)
        self.assertEqual(parsed["gsd_core"]["scope"], "local")
        self.assertEqual(parsed["gsd_core"]["version"], "1.16.0")
        node_calls = [a for a in fake.argv_log if a and a[0] == "node"]
        self.assertEqual(len(node_calls), 1)
        argv = node_calls[0]
        self.assertEqual(argv[1], "-e")
        self.assertEqual(argv[3], os.path.join(install, "bin", "lib", "model-catalog.cjs"))
        self.assertEqual(argv[4], os.path.join(install, "bin", "lib", "config-schema.cjs"))
        self.assertEqual(argv[5], project)
        self.assertEqual(json.loads(argv[6]), presets.closed_key_set("opencode"))
        script = argv[2]
        for key in presets.closed_key_set("opencode"):
            if "." not in key:
                continue  # undotted keys can appear as substrings of export names in the script
            self.assertNotIn(key, script)
        out_buf = io.StringIO()
        with contextlib.redirect_stdout(out_buf):
            cli.main(
                ["inventory", "--project-dir", project, "--host", "opencode"],
                which_fn=lambda name: "node" if name == "node" else None,
                env_fn=lambda: dict(env),
                run_fn=fake,
            )
        self.assertEqual(out_buf.getvalue(), plan_io.canonical_json(parsed))

    def test_local_gsd_core_roots_matches_gsd_core_roots_prefix(self):
        root = "/tmp/proj"
        env = {"HOME": "/tmp/h"}
        self.assertEqual(
            gsd_tools.local_gsd_core_roots(root),
            gsd_tools.gsd_core_roots(env, root)[:3],
        )

    def test_real_gsd_run_allows_node_and_git_only(self):
        child_env = {"HOME": "/tmp/x", "PATH": ""}
        node = "/usr/bin/node"
        run = real_gsd_run(child_env, node)
        with mock.patch("subprocess.run") as mocked:
            mocked.return_value = subprocess.CompletedProcess(["git"], 0, "", "")
            run(["git", "-C", "p", "rev-parse", "--show-toplevel"], capture_output=True)
            _, kwargs = mocked.call_args
            self.assertIs(kwargs["env"], child_env)
        with self.assertRaisesRegex(AssertionError, "non-node/git"):
            run([sys.executable, "x/ai-kit-spec.py", "detect-runtimes"])
        seen = []

        def fake(cmd, **kw):
            seen.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        run2 = real_gsd_run(child_env, node, fallback=fake)
        run2([sys.executable, "x/ai-kit-spec.py", "detect-runtimes"])
        self.assertEqual(len(seen), 1)


class TestRealGsdInventory(_RealGsdTestCase):
    def test_inventory_each_host_against_checkout_gsd_core(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        self.require_real_gsd(project)
        xdg = os.path.join(self.child_env["HOME"], "xdg-cache")
        seed_cache(xdg, {"clis": {}}, {"_meta": {"schema_version": 1}})
        self.child_env["XDG_CACHE_HOME"] = xdg
        self.resolve_env["XDG_CACHE_HOME"] = xdg
        version_path = os.path.join(_REPO_ROOT, ".claude", "gsd-core", "VERSION")
        with open(version_path, encoding="utf-8") as fh:
            expected_version = fh.read().strip()
        for host_name in host.HOSTS:
            spec_fake = FakeRun()
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = cli.main(
                    ["inventory", "--project-dir", project, "--host", host_name],
                    which_fn=lambda name: self.node_bin if name == "node" else None,
                    env_fn=lambda: dict(self.resolve_env),
                    run_fn=real_gsd_run(
                        self.child_env, self.node_bin, fallback=spec_fake
                    ),
                )
            self.assertEqual(code, 0, host_name)
            parsed = json.loads(stdout.getvalue())
            self.assertEqual(parsed["gsd_core"]["version"], expected_version)
            self.assertEqual(parsed["gsd_core"]["scope"], "local")
            self.assertIn("gsd-planner", parsed["gsd_core"]["model_profiles"])
            self.assertEqual(parsed["gsd_core"]["valid_keys"]["rejected"], [])
            spec_calls = [
                a
                for a in spec_fake.argv_log
                if len(a) >= 3 and str(a[1]).endswith("ai-kit-spec.py")
            ]
            self.assertEqual(len(spec_calls), 2, host_name)
            self.assertEqual(spec_calls[0][2], "detect-runtimes")
            self.assertEqual(spec_calls[1][2], "fetch-model-catalog")
            for argv, kw in zip(spec_fake.argv_log, spec_fake.kw_log, strict=True):
                if len(argv) >= 3 and str(argv[1]).endswith("ai-kit-spec.py"):
                    self.assertEqual(kw.get("env"), self.resolve_env)


class TestCatalogTracer(unittest.TestCase):
    def _tracer_fixture(self):
        runtimes = {
            "clis": {
                "codex": {
                    "installed": True,
                    "models": ["gpt-5.6-sol", "gpt-5.6-luna"],
                    "reasoning_modes": {
                        "gpt-5.6-sol": ["low", "medium"],
                        "gpt-5.6-luna": ["low"],
                    },
                },
                "opencode": {
                    "installed": True,
                    "models": ["openai/gpt-5.6-sol", "router-env/my-coding"],
                },
            }
        }
        catalog = {
            "_meta": {"schema_version": 1},
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {
                    "codex": {"model_id": "gpt-5.6-sol"},
                    "opencode": {"model_id": "openai/gpt-5.6-sol"},
                },
                "pricing": {"input_per_1m": 4},
                "scores": {
                    "intelligence_index": 40,
                    "coding_index": 35,
                    "agentic_index": 30,
                },
                "image_input": True,
                "image_input_source": "models_dev",
            },
            "openai/gpt-5.6-luna": {
                "provider": "openai",
                "runtimes": {"codex": {"model_id": "gpt-5.6-luna"}},
                "pricing": {"input_per_1m": 0.2},
                "scores": {
                    "intelligence_index": 20,
                    "coding_index": 20,
                    "agentic_index": 20,
                },
            },
            "router-env/my-coding": {
                "provider": "router-env",
                "is_router": True,
                "heuristic_confirmed": ["is_router"],
                "name_declared_purpose": "execute",
                "runtimes": {"opencode": {"model_id": "router-env/my-coding"}},
            },
        }
        return runtimes, catalog

    def test_inventory_catalog_and_candidates(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        runtimes, catalog = self._tracer_fixture()
        env = _inventory_env(home, runtimes, catalog)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun()
        code, parsed, _err = run_inventory(project, env, fake, "--host", "codex")
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertEqual(parsed["catalog"], {"state": "fresh", "scored": True})
        self.assertEqual(
            parsed["candidate_heuristic_fields"],
            ["family", "fast_twin_of", "vendor"],
        )
        self.assertEqual(len(parsed["candidates"]), 4)
        models = [(c["runtime"], c["model"]) for c in parsed["candidates"]]
        self.assertEqual(models, sorted(models))
        sol = next(
            c for c in parsed["candidates"]
            if c["runtime"] == "codex" and c["model"] == "gpt-5.6-sol"
        )
        self.assertTrue(sol["is_host"])
        self.assertEqual(sol["catalog_key"], "openai/gpt-5.6-sol")
        self.assertEqual(sol["price"], 4)
        self.assertEqual(sol["vendor"], "openai")
        self.assertEqual(sol["score_axes"], 3)
        self.assertEqual(set(sol["purpose_scores"].keys()), {
            "planning", "general", "mechanical", "execution", "review",
        })
        for c in parsed["candidates"]:
            if c["runtime"] == "opencode":
                self.assertFalse(c["is_host"])
        router = next(c for c in parsed["candidates"] if c["model"] == "router-env/my-coding")
        self.assertIsNone(router["vendor"])
        self.assertTrue(router["router_confirmed"])
        self.assertEqual(router["purpose_scores"], {})
        spec_calls = [
            a for a in fake.argv_log if len(a) >= 3 and str(a[1]).endswith("ai-kit-spec.py")
        ]
        self.assertEqual(len(spec_calls), 2)
        detect, fetch = spec_calls
        self.assertEqual(detect[2], "detect-runtimes")
        self.assertEqual(detect[3], "--if-stale")
        self.assertTrue(detect[4].endswith("runtimes.json"))
        self.assertEqual(fetch[2], "fetch-model-catalog")
        self.assertIn("--runtimes-json", fetch)
        self.assertIn("--catalog-path", fetch)
        self.assertIn("--cwd", fetch)
        self.assertIn(project, fetch)
        self.assertIn("--if-stale", fetch)
        for argv, kw in zip(fake.argv_log, fake.kw_log, strict=True):
            if len(argv) >= 3 and str(argv[1]).endswith("ai-kit-spec.py"):
                self.assertEqual(kw.get("env"), env)


class TestCatalogStates(unittest.TestCase):
    def _run_with_fetch(self, home, project, catalog, spec_answers):
        runtimes = {"clis": {"codex": {"installed": True, "models": ["gpt-5.6-sol"]}}}
        env = _inventory_env(home, runtimes, catalog)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun(spec_answers=spec_answers)
        code, parsed, _err = run_inventory(project, env, fake, "--host", "codex")
        self.assertEqual(code, 0)
        assert parsed is not None
        return parsed

    def test_fetch_skipped_is_fresh_without_warning(self):
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        catalog = {
            "_meta": {},
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"codex": {"model_id": "gpt-5.6-sol"}},
                "scores": {"intelligence_index": 1, "coding_index": 1, "agentic_index": 1},
            },
        }
        parsed = self._run_with_fetch(
            home,
            project,
            catalog,
            {
                "fetch-model-catalog": (
                    0,
                    json.dumps(
                        {
                            "fetch_skipped": True,
                            "models_dev_ok": False,
                            "artificial_analysis_ok": False,
                        }
                    ),
                )
            },
        )
        self.assertEqual(parsed["catalog"]["state"], "fresh")
        self.assertEqual(parsed["warnings"], [])

    def test_models_dev_ok_aa_fail_warns(self):
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        catalog = {
            "_meta": {},
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"codex": {"model_id": "gpt-5.6-sol"}},
                "scores": {"intelligence_index": 1, "coding_index": 1, "agentic_index": 1},
            },
        }
        parsed = self._run_with_fetch(
            home,
            project,
            catalog,
            {
                "fetch-model-catalog": (
                    0,
                    json.dumps(
                        {
                            "fetch_skipped": False,
                            "models_dev_ok": True,
                            "artificial_analysis_ok": False,
                        }
                    ),
                )
            },
        )
        self.assertEqual(parsed["catalog"]["state"], "fresh")
        self.assertIn(
            "Artificial Analysis refresh failed; scores from cache", parsed["warnings"]
        )

    def test_fetch_failure_is_stale_with_warning(self):
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        catalog = {
            "_meta": {},
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"codex": {"model_id": "gpt-5.6-sol"}},
                "scores": {"intelligence_index": 1, "coding_index": 1, "agentic_index": 1},
            },
        }
        parsed = self._run_with_fetch(
            home, project, catalog, {"fetch-model-catalog": (1, "")}
        )
        self.assertEqual(parsed["catalog"]["state"], "stale")
        self.assertIn("catalog refresh failed; using the stale cache", parsed["warnings"])

    def test_fetch_timeout_is_stale(self):
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        catalog = {
            "_meta": {},
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"codex": {"model_id": "gpt-5.6-sol"}},
            },
        }
        parsed = self._run_with_fetch(
            home,
            project,
            catalog,
            {"fetch-model-catalog": subprocess.TimeoutExpired("fetch", 120)},
        )
        self.assertEqual(parsed["catalog"]["state"], "stale")

    def test_both_sources_failed_not_skipped_is_stale(self):
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        catalog = {
            "_meta": {},
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"codex": {"model_id": "gpt-5.6-sol"}},
            },
        }
        parsed = self._run_with_fetch(
            home,
            project,
            catalog,
            {
                "fetch-model-catalog": (
                    0,
                    json.dumps(
                        {
                            "fetch_skipped": False,
                            "models_dev_ok": False,
                            "artificial_analysis_ok": False,
                        }
                    ),
                )
            },
        )
        self.assertEqual(parsed["catalog"]["state"], "stale")

    def test_empty_catalog_is_none(self):
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        parsed = self._run_with_fetch(home, project, {"_meta": {}}, {})
        self.assertEqual(parsed["catalog"], {"state": "none", "scored": False})
        for c in parsed["candidates"]:
            self.assertEqual(c["score_axes"], 0)
            self.assertEqual(c["purpose_scores"], {})

    def test_unscored_catalog_scored_false(self):
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        catalog = {
            "_meta": {},
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"codex": {"model_id": "gpt-5.6-sol"}},
                "pricing": {"input_per_1m": 4},
                "scores": {
                    "intelligence_index": None,
                    "coding_index": None,
                    "agentic_index": None,
                },
            },
        }
        parsed = self._run_with_fetch(home, project, catalog, {})
        self.assertFalse(parsed["catalog"]["scored"])
        for c in parsed["candidates"]:
            self.assertEqual(c["purpose_scores"], {})

    def test_detect_failure_still_fetches(self):
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        env = _inventory_env(home, {"clis": {}}, {"_meta": {}})
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun(spec_answers={"detect-runtimes": (1, "")})
        code, parsed, _err = run_inventory(project, env, fake, "--host", "codex")
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertIn(
            "detect-runtimes failed; using the cached runtimes snapshot",
            parsed["warnings"],
        )
        fetch_calls = [
            a for a in fake.argv_log if len(a) > 2 and a[2] == "fetch-model-catalog"
        ]
        self.assertEqual(len(fetch_calls), 1)

    def test_refresh_argv(self):
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        env = _inventory_env(home)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun()
        run_inventory(project, env, fake, "--host", "codex", "--refresh")
        spec_calls = [
            a for a in fake.argv_log if len(a) >= 3 and str(a[1]).endswith("ai-kit-spec.py")
        ]
        detect, fetch = spec_calls
        self.assertEqual(detect[2:4], ["detect-runtimes", "--save"])
        self.assertNotIn("--if-stale", detect)
        self.assertNotIn("--if-stale", fetch)


class TestBuildCandidates(unittest.TestCase):
    """Direct ``build_candidates`` unit tests for D-04, D-12..D-15 field rules."""

    def _weights(self):
        ranker = gsd_catalog.load_ai_kit_spec_module("model_ranker")
        assert ranker is not None
        return ranker.load_ranking_weights()

    def test_fast_twin_same_runtime_only(self):
        runtimes = {
            "clis": {
                "cursor-agent": {
                    "installed": True,
                    "models": [
                        "gpt-5.6-sol-high",
                        "gpt-5.6-sol-high-fast",
                        "composer-2.5",
                        "composer-2.5-fast",
                    ],
                },
                "opencode": {
                    "installed": True,
                    "models": ["openai/gpt-5.5-fast"],
                },
            }
        }
        out = catalog_adapter.build_candidates(runtimes, {}, "cursor-agent", self._weights())
        by_model = {c["model"]: c for c in out}
        self.assertEqual(by_model["gpt-5.6-sol-high-fast"]["fast_twin_of"], "gpt-5.6-sol-high")
        self.assertEqual(by_model["composer-2.5-fast"]["fast_twin_of"], "composer-2.5")
        self.assertIsNone(by_model["openai/gpt-5.5-fast"]["fast_twin_of"])

    def test_family_groups_effort_variants(self):
        runtimes = {
            "clis": {
                "codex": {
                    "installed": True,
                    "models": ["gpt-5.6-sol-high", "gpt-5.6-sol-low", "gpt-5.6-sol-high-fast"],
                }
            }
        }
        out = catalog_adapter.build_candidates(runtimes, {}, "codex", self._weights())
        families = {c["model"]: c["family"] for c in out}
        self.assertEqual(families["gpt-5.6-sol-high"], "gpt-5.6-sol")
        self.assertEqual(families["gpt-5.6-sol-low"], "gpt-5.6-sol")
        self.assertEqual(families["gpt-5.6-sol-high-fast"], "gpt-5.6-sol")

    def test_vendor_inference(self):
        entries = {
            "requesty/gpt-5.6-sol-medium": {
                "provider": "requesty",
                "runtimes": {"cursor-agent": {"model_id": "gpt-5.6-sol-medium"}},
            },
            "zai-coding-plan/glm-5.3": {
                "provider": "zai-coding-plan",
                "runtimes": {"opencode": {"model_id": "zai-coding-plan/glm-5.3"}},
            },
            "xai/grok-4.6": {
                "provider": "xai",
                "runtimes": {"opencode": {"model_id": "xai/grok-4.6"}},
            },
            "mystery/model": {
                "provider": "mystery",
                "runtimes": {"opencode": {"model_id": "mystery/model"}},
            },
            "router-env/r": {
                "provider": "router-env",
                "is_router": True,
                "runtimes": {"opencode": {"model_id": "router-env/r"}},
            },
        }
        runtimes = {
            "clis": {
                "cursor-agent": {"installed": True, "models": ["gpt-5.6-sol-medium"]},
                "opencode": {
                    "installed": True,
                    "models": [
                        "zai-coding-plan/glm-5.3",
                        "xai/grok-4.6",
                        "mystery/model",
                        "router-env/r",
                    ],
                },
            }
        }
        out = catalog_adapter.build_candidates(runtimes, entries, "cursor-agent", self._weights())
        by_model = {c["model"]: c for c in out}
        self.assertEqual(by_model["gpt-5.6-sol-medium"]["vendor"], "openai")
        self.assertEqual(by_model["zai-coding-plan/glm-5.3"]["vendor"], "zhipu")
        self.assertEqual(by_model["xai/grok-4.6"]["vendor"], "xai")
        self.assertIsNone(by_model["mystery/model"]["vendor"])
        self.assertIsNone(by_model["router-env/r"]["vendor"])

    def test_router_confirmed_rules(self):
        entries = {
            "router-env/a": {
                "provider": "router-env",
                "is_router": True,
                "heuristic_confirmed": ["is_router"],
                "name_declared_purpose": "execute",
                "runtimes": {"opencode": {"model_id": "router-env/a"}},
            },
            "router-env/b": {
                "provider": "router-env",
                "is_router": True,
                "name_declared_purpose": "execute",
                "runtimes": {"opencode": {"model_id": "router-env/b"}},
            },
            "router-env/c": {
                "provider": "router-env",
                "is_router": True,
                "heuristic_confirmed": ["is_router"],
                "runtimes": {"opencode": {"model_id": "router-env/c"}},
            },
        }
        runtimes = {
            "clis": {
                "opencode": {
                    "installed": True,
                    "models": ["router-env/a", "router-env/b", "router-env/c"],
                }
            }
        }
        out = catalog_adapter.build_candidates(runtimes, entries, "opencode", self._weights())
        by_model = {c["model"]: c for c in out}
        self.assertTrue(by_model["router-env/a"]["router_confirmed"])
        self.assertFalse(by_model["router-env/b"]["router_confirmed"])
        self.assertFalse(by_model["router-env/c"]["router_confirmed"])

    def test_score_axes_count(self):
        entries = {
            "a/m": {
                "provider": "a",
                "runtimes": {"codex": {"model_id": "m1"}},
                "scores": {"intelligence_index": 40, "coding_index": 30, "agentic_index": 20},
            },
            "b/m": {
                "provider": "b",
                "runtimes": {"codex": {"model_id": "m2"}},
                "scores": {"intelligence_index": 40, "coding_index": None},
            },
        }
        runtimes = {"clis": {"codex": {"installed": True, "models": ["m1", "m2", "m3"]}}}
        out = catalog_adapter.build_candidates(runtimes, entries, "codex", self._weights())
        by_model = {c["model"]: c for c in out}
        self.assertEqual(by_model["m1"]["score_axes"], 3)
        self.assertEqual(by_model["m2"]["score_axes"], 1)
        self.assertEqual(by_model["m3"]["score_axes"], 0)

    def test_mechanical_floor_and_score_exact(self):
        entries = {
            "openai/low-code": {
                "provider": "openai",
                "runtimes": {"codex": {"model_id": "low-code"}},
                "scores": {"intelligence_index": 40, "coding_index": 20, "agentic_index": 30},
            },
            "openai/ok-code": {
                "provider": "openai",
                "runtimes": {"codex": {"model_id": "ok-code"}},
                "scores": {"intelligence_index": 40, "coding_index": 40, "agentic_index": 30},
            },
        }
        runtimes = {
            "clis": {"codex": {"installed": True, "models": ["low-code", "ok-code"]}}
        }
        ranker = gsd_catalog.load_ai_kit_spec_module("model_ranker")
        assert ranker is not None
        weights = ranker.load_ranking_weights()
        pool = [
            {**entries["openai/low-code"], "key": "openai/low-code"},
            {**entries["openai/ok-code"], "key": "openai/ok-code"},
        ]
        out = catalog_adapter.build_candidates(runtimes, entries, "codex", weights)
        low = next(c for c in out if c["model"] == "low-code")
        self.assertNotIn("mechanical", low["purpose_scores"])
        for purpose in ranker.CANONICAL_PURPOSES:
            if purpose not in low["purpose_scores"]:
                continue
            direct = ranker.score_candidates(pool, purpose, weights)
            by_key = {row["key"]: row["score_exact"] for row in direct}
            self.assertEqual(low["purpose_scores"][purpose], by_key["openai/low-code"])

    def test_price_precision(self):
        entries = {
            "p/a": {
                "provider": "p",
                "runtimes": {"codex": {"model_id": "a"}},
                "pricing": {"input_per_1m": 4.4},
            },
            "p/b": {
                "provider": "p",
                "runtimes": {"codex": {"model_id": "b"}},
                "pricing": {"input_per_1m": 0.825},
            },
        }
        runtimes = {"clis": {"codex": {"installed": True, "models": ["a", "b"]}}}
        out = catalog_adapter.build_candidates(runtimes, entries, "codex", self._weights())
        prices = {c["model"]: c["price"] for c in out}
        self.assertEqual(prices["a"], 4.4)
        self.assertEqual(prices["b"], 0.825)

    def test_duplicate_catalog_key_picks_lexicographic_smaller(self):
        entries = {
            "z/z": {
                "provider": "z",
                "runtimes": {"cursor-agent": {"model_id": "m"}},
            },
            "a/a": {
                "provider": "a",
                "runtimes": {"cursor-agent": {"model_id": "m"}},
            },
        }
        runtimes = {"clis": {"cursor-agent": {"installed": True, "models": ["m"]}}}
        out = catalog_adapter.build_candidates(runtimes, entries, "cursor-agent", self._weights())
        self.assertEqual(out[0]["catalog_key"], "a/a")

    def test_skips_uninstalled_and_non_str_models(self):
        runtimes = {
            "clis": {
                "codex": {"installed": False, "models": ["x"]},
                "opencode": {"installed": True, "models": ["good", 12, "good"]},
            }
        }
        out = catalog_adapter.build_candidates(runtimes, {}, "opencode", self._weights())
        self.assertEqual([c["model"] for c in out], ["good"])
        self.assertEqual(out[0]["runtime"], "opencode")


class TestGsdCoreResolution(unittest.TestCase):
    def _home_env(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        return home, _inventory_env(home)

    def test_local_claude_wins_over_global(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"), version="1.16.0")
        make_gsd_install(os.path.join(home, ".claude", "gsd-core"), version="9.9.9")
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["gsd_core"]["scope"], "local")
        self.assertEqual(parsed["gsd_core"]["version"], "1.16.0")
        self.assertEqual(
            parsed["gsd_core"]["path"], os.path.join(project, ".claude", "gsd-core")
        )

    def test_global_only_is_labelled_global(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        global_root = os.path.join(home, ".claude", "gsd-core")
        make_gsd_install(global_root, version="1.16.0")
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["gsd_core"]["scope"], "global")
        self.assertEqual(parsed["gsd_core"]["path"], global_root)

    def test_pi_prefers_dot_pi_over_dot_claude(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".pi", "gsd-core"), version="1.16.0")
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"), version="9.9.9")
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake, "--host", "pi")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["gsd_core"]["path"], os.path.join(project, ".pi", "gsd-core"))

    def test_claude_host_ignores_dot_pi(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".pi", "gsd-core"), version="9.9.9")
        claude_root = os.path.join(project, ".claude", "gsd-core")
        make_gsd_install(claude_root, version="1.16.0")
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["gsd_core"]["path"], claude_root)

    def test_pi_global_from_pi_agent_home(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        pi_global = os.path.join(home, ".pi", "agent", "gsd-core")
        make_gsd_install(pi_global, version="1.16.0")
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake, "--host", "pi")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["gsd_core"]["scope"], "global")
        self.assertEqual(parsed["gsd_core"]["path"], pi_global)

    def test_pi_missing_install_lists_dot_pi_first(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        fake = FakeRun()
        code, _parsed, err = run_inventory(project, env, fake, "--host", "pi")
        self.assertEqual(code, 2)
        first = os.path.join(project, ".pi", "gsd-core", "bin", "gsd-tools.cjs")
        self.assertIn(first, err)

    def test_worktree_global_warns_when_main_has_local(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        main = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        self.addCleanup(shutil.rmtree, main, ignore_errors=True)
        make_gsd_install(os.path.join(home, ".claude", "gsd-core"))
        make_gsd_install(os.path.join(main, ".claude", "gsd-core"))
        git_answers = {
            "--show-toplevel": (0, project + "\n"),
            "--git-common-dir": (0, os.path.join(main, ".git") + "\n"),
        }
        fake = FakeRun(git_answers=git_answers)
        code, parsed, _ = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(len(parsed["warnings"]), 1)
        self.assertIn(main, parsed["warnings"][0])
        self.assertIn("versions can differ", parsed["warnings"][0])

    def test_worktree_no_warning_without_main_local(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        main = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        self.addCleanup(shutil.rmtree, main, ignore_errors=True)
        make_gsd_install(os.path.join(home, ".claude", "gsd-core"))
        git_answers = {
            "--show-toplevel": (0, project + "\n"),
            "--git-common-dir": (0, os.path.join(main, ".git") + "\n"),
        }
        fake = FakeRun(git_answers=git_answers)
        code, parsed, _ = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["warnings"], [])

    def test_local_install_skips_git_common_dir(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun()
        run_inventory(project, env, fake, "--host", "claude")
        common_calls = [
            a for a in fake.argv_log if a[:3] == ["git", "-C", project] and "--git-common-dir" in a
        ]
        self.assertEqual(common_calls, [])

    def test_no_install_lists_searched_paths(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        fake = FakeRun()
        code, _parsed, err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("searched:", err)
        self.assertIn(os.path.join(project, "gsd-core", "bin", "gsd-tools.cjs"), err)
        self.assertIn(os.path.join(home, ".claude", "gsd-core", "bin", "gsd-tools.cjs"), err)

    def test_missing_host_flag_exits_two(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun()
        code, _parsed, err = run_inventory(project, env, fake)
        self.assertEqual(code, 2)
        self.assertIn("pass --host", err)

    def test_opencode_detected_without_flag(self):
        _home, env = self._home_env()
        env["OPENCODE"] = "1"
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake)
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["host"], "opencode")
        self.assertEqual(parsed["host_source"], "detected")

    def test_missing_sibling_exits_two_no_node(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun()
        with mock.patch.object(gsd_catalog, "load_ai_kit_spec_module", return_value=None):
            code, _parsed, err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("ai-kit-spec-review", err)
        node_calls = [a for a in fake.argv_log if a and a[0] == "node"]
        self.assertEqual(node_calls, [])


class TestProbeFailures(unittest.TestCase):
    def _project_with_install(self, *, include_config_schema=True):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        root = os.path.join(project, ".claude", "gsd-core")
        make_gsd_install(root, include_config_schema=include_config_schema)
        env = _inventory_env(home)
        return project, env, root

    def test_node_null_stdout_fails_closed(self):
        project, env, root = self._project_with_install()
        fake = FakeRun(node_stdout="null")
        code, _parsed, err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("isValidConfigKey unavailable", err)
        self.assertIn(root, err)
        self.assertIn("1.16.0", err)

    def test_node_nonzero_exit_fails_closed(self):
        project, env, root = self._project_with_install()

        def bad_node(cmd, **kw):
            if cmd[0] == "node":
                return subprocess.CompletedProcess(cmd, 1, "null", "")
            return FakeRun()(cmd, **kw)

        code, _parsed, err = run_inventory(project, env, bad_node, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("isValidConfigKey unavailable", err)
        self.assertIn(root, err)

    def test_node_timeout_fails_closed(self):
        project, env, root = self._project_with_install()

        def timeout_node(cmd, **kw):
            if cmd[0] == "node":
                raise subprocess.TimeoutExpired(cmd, 30)
            return FakeRun()(cmd, **kw)

        code, _parsed, err = run_inventory(project, env, timeout_node, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("isValidConfigKey unavailable", err)
        self.assertIn(root, err)

    def test_missing_node_skips_probe(self):
        project, env, _root = self._project_with_install()
        fake = FakeRun()
        with mock.patch.object(gsd_catalog, "resolve_node_binary", return_value=None):
            code, _parsed, err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("node", err.lower())
        node_calls = [a for a in fake.argv_log if a and a[0] == "node"]
        self.assertEqual(node_calls, [])

    def test_missing_config_schema_cjs(self):
        project, env, root = self._project_with_install(include_config_schema=False)
        fake = FakeRun()
        code, _parsed, err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn(root, err)
        self.assertIn("config-schema.cjs", err)

    def test_parse_tables_output_rejects_malformed(self):
        from ai_kit_gsd_curated_config.gsd_catalog import _parse_tables_output

        good_keys = ["a"]
        good = json.dumps(
            {
                "runtime_profile_map": {"x": {"y": {}}},
                "model_profiles": {"p": {}},
                "agent_to_phase_type": {"a": "b"},
                "valid_keys": {"accepted": good_keys, "rejected": []},
            }
        )
        self.assertIsNotNone(_parse_tables_output(good))
        for bad in ("x", "[]", "{}", json.dumps({"model_profiles": {"p": {}}})):
            self.assertIsNone(_parse_tables_output(bad))
        empty_profiles = json.dumps(
            {
                "runtime_profile_map": {"x": {"y": {}}},
                "model_profiles": {},
                "agent_to_phase_type": {"a": "b"},
                "valid_keys": {"accepted": [], "rejected": []},
            }
        )
        self.assertIsNone(_parse_tables_output(empty_profiles))
        bad_accepted = json.dumps(
            {
                "runtime_profile_map": {"x": {"y": {}}},
                "model_profiles": {"p": {}},
                "agent_to_phase_type": {"a": "b"},
                "valid_keys": {"accepted": "nope", "rejected": []},
            }
        )
        self.assertIsNone(_parse_tables_output(bad_accepted))
        bad_rejected = json.dumps(
            {
                "runtime_profile_map": {"x": {"y": {}}},
                "model_profiles": {"p": {}},
                "agent_to_phase_type": {"a": "b"},
                "valid_keys": {"accepted": [], "rejected": [1]},
            }
        )
        self.assertIsNone(_parse_tables_output(bad_rejected))

    def test_inventory_does_not_mutate_project_tree(self):
        project, env, _root = self._project_with_install()
        before = {}
        for dirpath, _dirnames, filenames in os.walk(project):
            for name in filenames:
                path = os.path.join(dirpath, name)
                with open(path, "rb") as fh:
                    before[path] = fh.read()
        fake = FakeRun()
        code, _parsed, _err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        after = {}
        for dirpath, _dirnames, filenames in os.walk(project):
            for name in filenames:
                path = os.path.join(dirpath, name)
                with open(path, "rb") as fh:
                    after[path] = fh.read()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
