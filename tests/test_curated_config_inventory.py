"""Inventory tracer, gsd-core resolution and probe fail-closed paths (17-03). The real-gsd
smoke runs live in the e2e-tier tests/test_curated_config_e2e.py."""
import contextlib
import hashlib
import io
import json
import os
import shutil
import stat
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

from ai_kit_gsd_curated_config import (
    catalog_adapter,
    cli,
    gsd_catalog,
    inventory,
    plan_io,
    presets,
    project_facts,
)
from ai_kit_spec import gsd_tools

from tests.test_curated_config_recommend import build, entry_map, make_inventory


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

    def __init__(
        self, git_answers=None, node_stdout=None, spec_answers=None, config_path_stdout=None
    ):
        self.argv_log: list[list] = []
        self.kw_log: list[dict] = []
        self.git_answers = git_answers or {}
        self.node_stdout = node_stdout
        self.spec_answers = spec_answers or {}
        self.config_path_stdout = config_path_stdout

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
        if len(cmd) >= 4 and cmd[0] == "node" and cmd[2] == "config-path":
            out = self.config_path_stdout
            if callable(out):
                out = out(cmd)
            if out is None:
                return subprocess.CompletedProcess(cmd, 1, "", "")
            return subprocess.CompletedProcess(cmd, 0, out, "")
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
            which_fn=lambda name, **_kw: "node" if name == "node" else None,
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
    def test_missing_project_dir_exits_2(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        missing = os.path.join(home, "does-not-exist-typo")
        fake = FakeRun()
        code, parsed, err = run_inventory(missing, _inventory_env(home), fake)
        self.assertEqual((code, parsed), (2, None))
        self.assertIn("is not a directory", err)
        self.assertEqual(fake.argv_log, [])

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
        node_calls = [a for a in fake.argv_log if a and a[0] == "node" and a[1] == "-e"]
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
                which_fn=lambda name, **_kw: "node" if name == "node" else None,
                env_fn=lambda: dict(env),
                run_fn=fake,
            )
        self.assertEqual(out_buf.getvalue(), plan_io.canonical_json(parsed))

    def test_local_gsd_core_roots_matches_gsd_core_roots_prefix(self):
        root = os.path.join(os.sep, "proj")
        env = {"HOME": os.path.join(os.sep, "h")}
        self.assertEqual(
            gsd_tools.local_gsd_core_roots(root),
            gsd_tools.gsd_core_roots(env, root)[:3],
        )

    def test_real_gsd_run_allows_node_and_git_only(self):
        child_env = {"HOME": os.path.join(os.sep, "x"), "PATH": ""}
        node = os.path.join(os.sep, "bin", "node")
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


class TestGracefulRefreshTimeout(unittest.TestCase):
    """B-WR-05: a timed-out refresh child gets SIGTERM (so the probe can clean up) before
    SIGKILL."""

    def _child(self, body):
        return [sys.executable, "-c", "import os, signal, sys, time\n" + body]

    def test_timeout_sends_sigterm_first(self):
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        marker = os.path.join(scratch, "got-sigterm")
        body = (
            "def h(*_):\n"
            f"    open({marker!r}, 'w').close(); sys.exit(0)\n"
            "signal.signal(signal.SIGTERM, h)\n"
            "time.sleep(30)\n"
        )
        with self.assertRaises(subprocess.TimeoutExpired):
            catalog_adapter._run_graceful(self._child(body), timeout=2, env=dict(os.environ))
        self.assertTrue(os.path.exists(marker))

    def test_sigterm_ignoring_child_is_killed_after_grace(self):
        body = "signal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(30)\n"
        with mock.patch.object(catalog_adapter, "_TERM_GRACE_S", 0.5), \
                self.assertRaises(subprocess.TimeoutExpired):
            catalog_adapter._run_graceful(self._child(body), timeout=0.5, env=dict(os.environ))

    def test_grace_outlasts_probe_server_stop(self):
        """The child's SIGTERM cleanup (_stop_server: SIGTERM wait, then SIGKILL wait) must
        finish inside the grace with headroom, or our SIGKILL orphans its opencode server."""
        from ai_kit_spec import detection

        worst = detection._STOP_TERM_WAIT_S + detection._STOP_KILL_WAIT_S
        self.assertGreaterEqual(catalog_adapter._TERM_GRACE_S, worst + 5)

    def test_production_run_uses_graceful_runner(self):
        with mock.patch.object(catalog_adapter, "_run_graceful",
                               side_effect=subprocess.TimeoutExpired("x", 1)) as graceful:
            self.assertIsNone(catalog_adapter._run(subprocess.run, ["x"], {}))
        graceful.assert_called_once()


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

    def test_missing_vendor_module_is_sibling_error(self):
        """B-WR-08: an old sibling without ai_kit_spec.vendor fails, never zero candidates."""
        real = gsd_catalog.load_ai_kit_spec_module

        def no_vendor(name):
            return None if name == "vendor" else real(name)

        with mock.patch.object(gsd_catalog, "load_ai_kit_spec_module", side_effect=no_vendor):
            self.assertIsNone(catalog_adapter._load_spec_stack())
            with self.assertRaisesRegex(ImportError, "ai-kit-spec-review"):
                catalog_adapter.build_candidates({"clis": {}}, {}, "codex", {})

    def test_failed_opencode_probe_surfaces_warning(self):
        """C-WR-02: a recorded probe failure reaches the inventory warnings."""
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        runtimes = {"clis": {"opencode": {"installed": True, "models": [],
                                          "image_input_probe": "failed"}}}
        env = _inventory_env(home, runtimes, {"_meta": {"schema_version": 1}})
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        code, parsed, _err = run_inventory(project, env, FakeRun(), "--host", "opencode")
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertIn(catalog_adapter._PROBE_WARN, parsed["warnings"])

    def test_models_dev_failure_warns_even_when_aa_succeeds(self):
        """B-WR-04: never a silent 'fresh' when prices/capabilities came from cache."""
        state, warns = catalog_adapter._catalog_state(
            {"models_dev_ok": False, "artificial_analysis_ok": True, "fetch_skipped": False},
            {"openai/x": {}},
        )
        self.assertEqual(state, "fresh")
        self.assertIn(catalog_adapter._MODELS_DEV_WARN, warns)

    def test_failed_fetch_with_router_only_rows_is_none(self):
        """17-VERIFICATION WR: a first run with both sources down writes router-only rows
        (no source flags); that is no cache, not a stale one."""
        failed = {"models_dev_ok": False, "artificial_analysis_ok": False, "fetch_skipped": False}
        router_only = {"router-env/my-coding": {"source": {"models_dev": False,
                                                           "artificial_analysis": False,
                                                           "manual": False}}}
        self.assertEqual(catalog_adapter._catalog_state(failed, router_only), ("none", []))
        cached = {"openai/x": {"source": {"models_dev": True}}}
        self.assertEqual(catalog_adapter._catalog_state(failed, cached)[0], "stale")

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

    def test_aa_fail_on_unscored_catalog_claims_no_cache(self):
        """B-IN-04: with no scores anywhere, an AA failure never says "from cache"."""
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
        result = {"fetch_skipped": False, "models_dev_ok": True, "artificial_analysis_ok": False}
        parsed = self._run_with_fetch(
            home, project, catalog, {"fetch-model-catalog": (0, json.dumps(result))}
        )
        self.assertIn(
            "Artificial Analysis unavailable (no key or fetch failed); catalog unscored",
            parsed["warnings"],
        )
        self.assertFalse(any("scores from cache" in w for w in parsed["warnings"]))

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

    def test_detect_failure_without_snapshot_says_so(self):
        """B-IN-04: no cached runtimes snapshot means no fallback to claim."""
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        env = _inventory_env(home, {}, {"_meta": {}})
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun(spec_answers={"detect-runtimes": (1, "")})
        code, parsed, _err = run_inventory(project, env, fake, "--host", "codex")
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertIn("detect-runtimes failed; no cached runtimes snapshot", parsed["warnings"])
        self.assertFalse(any("using the cached" in w for w in parsed["warnings"]))

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

    def test_pi_router_candidate_from_merged_catalog(self):
        spec_cli = gsd_catalog.load_ai_kit_spec_module("cli")
        assert spec_cli is not None
        existing = {
            "router-env/my-coding": {
                "batch_mode": False,
                "confidence": "low",
                "fallback_quota": True,
                "heuristic_confirmed": ["is_router"],
                "is_router": True,
                "last_verified": "2026-10-15",
                "name_declared_purpose": "execute",
                "provider": "router-env",
                "runtimes": {
                    "opencode": {"ctx_window": None, "model_id": "router-env/my-coding"},
                },
                "source": {
                    "artificial_analysis": False,
                    "manual": False,
                    "models_dev": False,
                },
            }
        }
        discovered = [{"cli": "pi", "model_id": "router-env/my-coding"}]
        catalog, rejections, unmatched = spec_cli.build_model_catalog(
            discovered,
            spec_cli.CatalogSources({}, False, [], False),
            existing,
        )
        self.assertEqual(rejections, [])
        self.assertEqual(unmatched, [])
        runtimes = {
            "clis": {
                "pi": {"installed": True, "models": ["router-env/my-coding"]},
            }
        }
        out = catalog_adapter.build_candidates(
            runtimes, catalog, "claude", self._weights()
        )
        self.assertEqual(len(out), 1)
        cand = out[0]
        self.assertEqual(cand["runtime"], "pi")
        self.assertTrue(cand["is_router"])
        self.assertTrue(cand["router_confirmed"])
        self.assertEqual(cand["name_declared_purpose"], "execute")
        self.assertFalse(cand["is_host"])


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
        main = tempfile.mkdtemp(suffix="{x}")  # B-WR-06: braces in a path stay literal
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


class TestInjectedSeams(unittest.TestCase):
    """B-IN-05: node calls see the injected env and gsd_run lookup uses the injected which."""

    def test_node_calls_get_injected_env_and_which(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        env = {**_inventory_env(home), "GSD_HOME": home, "PATH": "injected-path"}
        fake = FakeRun()
        seen_which = []

        def which(name, **kw):
            seen_which.append((name, kw.get("path")))
            return "node" if name == "node" else None

        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(
                ["inventory", "--project-dir", project, "--host", "claude"],
                which_fn=which, env_fn=lambda: dict(env), run_fn=fake,
            )
        self.assertEqual(code, 0, stderr.getvalue())
        node_kws = [kw for a, kw in zip(fake.argv_log, fake.kw_log, strict=True)
                    if a and a[0] == "node"]
        self.assertTrue(node_kws)
        for kw in node_kws:
            self.assertEqual(kw.get("env"), env)
        self.assertIn(("gsd_run", "injected-path"), seen_which)


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
            if cmd[0] == "node" and len(cmd) >= 2 and cmd[1] == "-e":
                return subprocess.CompletedProcess(cmd, 1, "", "volta: shim error\n")
            return FakeRun()(cmd, **kw)

        code, _parsed, err = run_inventory(project, env, bad_node, "--host", "claude")
        self.assertEqual(code, 2)
        # node itself failed: never blamed on isValidConfigKey.
        self.assertNotIn("isValidConfigKey", err)
        self.assertIn("node exited 1: volta: shim error", err)
        self.assertIn(root, err)

    def test_node_spawn_error_fails_closed(self):
        project, env, root = self._project_with_install()

        def missing_node(cmd, **kw):
            if cmd[0] == "node" and len(cmd) >= 2 and cmd[1] == "-e":
                raise FileNotFoundError(2, "No such file or directory")
            return FakeRun()(cmd, **kw)

        code, _parsed, err = run_inventory(project, env, missing_node, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertNotIn("isValidConfigKey", err)
        self.assertIn("node failed to start (No such file or directory)", err)
        self.assertIn(root, err)

    def test_node_timeout_fails_closed(self):
        project, env, root = self._project_with_install()

        def timeout_node(cmd, **kw):
            if cmd[0] == "node" and len(cmd) >= 2 and cmd[1] == "-e":
                raise subprocess.TimeoutExpired(cmd, 30)
            return FakeRun()(cmd, **kw)

        code, _parsed, err = run_inventory(project, env, timeout_node, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("node timed out after 30s", err)
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
                "model_profiles": {"p": {"adaptive": "opus", "balanced": "sonnet"}},
                "agent_to_phase_type": {"a": "b"},
                "valid_keys": {"accepted": good_keys, "rejected": []},
            }
        )
        parsed = _parse_tables_output(good)
        assert parsed is not None
        # gsd-core's agent-first table is normalized to profile -> {agent: tier}.
        self.assertEqual(
            parsed["model_profiles"], {"adaptive": {"p": "opus"}, "balanced": {"p": "sonnet"}}
        )
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


def _tree_snapshot(root: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        key = rel_dir if rel_dir != "." else "."
        out[key] = "dir"
        for name in filenames:
            rel = os.path.relpath(os.path.join(dirpath, name), root)
            with open(os.path.join(dirpath, name), "rb") as handle:
                out[rel] = hashlib.sha256(handle.read()).hexdigest()
    return out


def _lock_tree(root: str) -> list[tuple[str, int]]:
    saved: list[tuple[str, int]] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for name in filenames:
            path = os.path.join(dirpath, name)
            saved.append((path, os.stat(path).st_mode))
            os.chmod(path, stat.S_IRUSR)
        for name in dirnames:
            path = os.path.join(dirpath, name)
            saved.append((path, os.stat(path).st_mode))
            os.chmod(path, stat.S_IRUSR | stat.S_IXUSR)
    return saved


def _unlock_tree(saved: list[tuple[str, int]]) -> None:
    for path, mode in saved:
        with contextlib.suppress(OSError):
            os.chmod(path, mode)


class TestCompleteInventory(unittest.TestCase):
    def _tracer_fixture(self):
        runtimes = {
            "clis": {
                "codex": {"installed": True, "models": ["gpt-5.6-sol", "gpt-5.6-luna"]},
                "opencode": {"installed": True, "models": ["openai/gpt-5.6-sol"]},
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
                "scores": {
                    "intelligence_index": 40,
                    "coding_index": 35,
                    "agentic_index": 30,
                },
            },
        }
        return runtimes, catalog

    def test_complete_inventory_feeds_recommend(self):
        home = tempfile.mkdtemp()
        gsd_home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, gsd_home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        planning = os.path.join(project, ".planning")
        os.makedirs(planning, exist_ok=True)
        config_path = os.path.join(planning, "config.json")
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "model_policy": {"provider": "generic"},
                    "runtime": "codex",
                    "model_overrides": {"gsd-planner": "opus"},
                    "secret_token": "x",
                },
                handle,
            )
        with open(os.path.join(project, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("# agents\n")
        with open(os.path.join(project, "package.json"), "w", encoding="utf-8") as handle:
            json.dump({"dependencies": {"react": "18"}}, handle)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        os.makedirs(os.path.join(gsd_home, ".gsd"), exist_ok=True)
        defaults_path = os.path.join(gsd_home, ".gsd", "defaults.json")
        with open(defaults_path, "w", encoding="utf-8") as handle:
            json.dump({"runtime": "codex", "brave_api_key": "k"}, handle)
        runtimes, catalog = self._tracer_fixture()
        env = _inventory_env(home, runtimes, catalog)
        env["GSD_HOME"] = gsd_home

        def _tables_stdout(cmd):
            keys = json.loads(cmd[6])
            payload = {
                "runtime_profile_map": {
                    "opencode": {
                        "opus": {"model": "openai/gpt-5.6-sol"},
                        "sonnet": {"model": "openai/gpt-5.6-sol"},
                        "haiku": {"model": "openai/gpt-5.6-sol"},
                    }
                },
                # gsd-core 1.16's real agent-first MODEL_PROFILES shape.
                "model_profiles": {
                    "gsd-planner": {"adaptive": "opus", "balanced": "opus"},
                    "gsd-executor": {"adaptive": "sonnet", "balanced": "sonnet"},
                    "gsd-verifier": {"adaptive": "sonnet", "balanced": "sonnet"},
                    "gsd-plan-checker": {"adaptive": "haiku", "balanced": "sonnet"},
                    "gsd-code-reviewer": {"adaptive": "sonnet", "balanced": "sonnet"},
                    "gsd-ui-auditor": {"adaptive": "haiku", "balanced": "sonnet"},
                    "gsd-dom-verifier": {"adaptive": "haiku", "balanced": "sonnet"},
                    "gsd-ui-researcher": {"adaptive": "sonnet", "balanced": "sonnet"},
                    "gsd-code-fixer": {"adaptive": "sonnet", "balanced": "sonnet"},
                },
                "agent_to_phase_type": {
                    "gsd-planner": "planning",
                    "gsd-executor": "execution",
                },
                "valid_keys": {"accepted": keys, "rejected": []},
            }
            return json.dumps(payload)

        fake = FakeRun(config_path_stdout=config_path, node_stdout=_tables_stdout)
        code, parsed, _err = run_inventory(project, env, fake, "--host", "opencode")
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertTrue(parsed["project"]["frontend"])
        self.assertEqual(
            parsed["project"]["instruction_files"],
            {"AGENTS.md": True, "CLAUDE.md": False},
        )
        self.assertTrue(parsed["existing_config"]["exists"])
        self.assertNotIn("secret_token", parsed["existing_config"]["values"])
        self.assertEqual(parsed["global_defaults"]["path"], defaults_path)
        self.assertEqual(parsed["global_defaults"]["values"], {"runtime": "codex"})
        kinds = {(c["kind"], c["scope"]) for c in parsed["conflicts"]}
        self.assertIn(("model_policy", "project"), kinds)
        self.assertIn(("runtime", "project"), kinds)
        info_kinds = {(i["kind"], i["scope"]) for i in parsed["info"]}
        self.assertIn(("runtime", "global"), info_kinds)
        node_calls = [a for a in fake.argv_log if a and a[0] == "node" and a[1] == "-e"]
        keys = json.loads(node_calls[0][6])
        self.assertIn("model_policy.provider", keys)
        self.assertIn("model_overrides.gsd-planner", keys)
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = os.path.join(tmp, "inventory.json")
            out_path = os.path.join(tmp, "plan.json")
            with open(inv_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(parsed))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                io.StringIO()
            ):
                rec_code = cli.main(
                    [
                        "recommend",
                        "--inventory",
                        inv_path,
                        "--profile",
                        "adaptive",
                        "--rigor",
                        "standard",
                        "--out",
                        out_path,
                    ]
                )
            self.assertEqual(rec_code, 0)
            with open(out_path, encoding="utf-8") as handle:
                plan = json.load(handle)
            self.assertEqual(plan["schema_version"], 1)
            keys = {e["key"]: e for e in plan["entries"]}
            self.assertEqual(keys["model_profile"]["value"], "adaptive")
            for tier in ("opus", "sonnet", "haiku"):
                self.assertIn(f"model_profile_overrides.opencode.{tier}", keys)



# A synthetic root, never touched on disk (classify_conflicts only joins paths onto it).
_PROJ = os.path.join(os.sep, "p")


class TestConflictMatrix(unittest.TestCase):
    def _facts(self, **kw):
        base = {"planning_dir_present": False, "instruction_file": None}
        base.update(kw)
        return base

    def test_project_model_policy_conflict(self):
        existing = {
            "path": "p",
            "exists": True,
            "values": {"model_policy": {"provider": "generic"}},
        }
        conflicts, info = inventory.classify_conflicts(
            "codex", existing, {"values": {}}, self._facts(), _PROJ
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["scope"], "project")
        self.assertEqual(info, [])

    def test_global_model_policy_latent_no_planning(self):
        existing = {"path": "p", "exists": False, "values": {}}
        global_defaults = {"values": {"model_policy": {"provider": "g"}}}
        conflicts, info = inventory.classify_conflicts(
            "codex", existing, global_defaults, self._facts(), _PROJ
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["effect"], inventory._LATENT)
        self.assertIn("read at resolution while .planning/ is absent", conflicts[0]["why"])
        self.assertEqual(info, [])

    def test_global_model_policy_latent_with_planning_dir(self):
        existing = {"path": "p", "exists": False, "values": {}}
        global_defaults = {"values": {"model_policy": {"provider": "g"}}}
        conflicts, _info = inventory.classify_conflicts(
            "codex",
            existing,
            global_defaults,
            self._facts(planning_dir_present=True),
            _PROJ,
        )
        self.assertEqual(len(conflicts), 1)
        self.assertNotIn("read at resolution while .planning/ is absent", conflicts[0]["why"])

    def test_global_model_policy_inert_with_project_config(self):
        existing = {"path": "p", "exists": True, "values": {"runtime": "codex"}}
        global_defaults = {"values": {"model_policy": {"provider": "g"}}}
        conflicts, info = inventory.classify_conflicts(
            "codex", existing, global_defaults, self._facts(), _PROJ
        )
        self.assertEqual(conflicts, [])
        self.assertEqual(len(info), 1)
        self.assertIn("#3532", info[0]["why"])

    def test_both_policies_project_conflict_and_global_info(self):
        existing = {
            "path": "p",
            "exists": True,
            "values": {"model_policy": {"provider": "p"}},
        }
        global_defaults = {"values": {"model_policy": {"provider": "g"}}}
        conflicts, info = inventory.classify_conflicts(
            "codex", existing, global_defaults, self._facts(), _PROJ
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["scope"], "project")
        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]["scope"], "global")

    def test_claude_project_resolve_omit(self):
        existing = {"path": "p", "exists": True, "values": {"resolve_model_ids": "omit"}}
        conflicts, info = inventory.classify_conflicts(
            "claude", existing, {"values": {}}, self._facts(), _PROJ
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["kind"], "resolve_model_ids")
        self.assertEqual(info, [])

    def test_claude_global_omit_latent(self):
        existing = {"path": "p", "exists": False, "values": {}}
        global_defaults = {"values": {"resolve_model_ids": "omit"}}
        conflicts, info = inventory.classify_conflicts(
            "claude", existing, global_defaults, self._facts(), _PROJ
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["effect"], inventory._LATENT)
        self.assertEqual(info, [])
        # B-IN-03: with .planning/ absent gsd-core already reads the global omit.
        self.assertIn("read at resolution while .planning/ is absent", conflicts[0]["why"])
        with_planning, _ = inventory.classify_conflicts(
            "claude", existing, global_defaults, self._facts(planning_dir_present=True), _PROJ
        )
        self.assertNotIn("read at resolution", with_planning[0]["why"])

    def test_claude_global_omit_inert(self):
        existing = {"path": "p", "exists": True, "values": {}}
        global_defaults = {"values": {"resolve_model_ids": "omit"}}
        conflicts, info = inventory.classify_conflicts(
            "claude", existing, global_defaults, self._facts(), _PROJ
        )
        self.assertEqual(conflicts, [])
        self.assertEqual(len(info), 1)

    def test_codex_no_resolve_model_ids_entries(self):
        existing = {"path": "p", "exists": True, "values": {"resolve_model_ids": "omit"}}
        global_defaults = {"values": {"resolve_model_ids": "omit"}}
        conflicts, info = inventory.classify_conflicts(
            "codex", existing, global_defaults, self._facts(), _PROJ
        )
        self.assertEqual(conflicts, [])
        self.assertEqual(info, [])

    def test_project_runtime_mismatch(self):
        existing = {"path": "p", "exists": True, "values": {"runtime": "codex"}}
        conflicts, info = inventory.classify_conflicts(
            "opencode", existing, {"values": {}}, self._facts(), _PROJ
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["kind"], "runtime")
        self.assertEqual(info, [])

    def test_project_runtime_matches_host(self):
        existing = {"path": "p", "exists": True, "values": {"runtime": "opencode"}}
        conflicts, _info = inventory.classify_conflicts(
            "opencode", existing, {"values": {}}, self._facts(), _PROJ
        )
        self.assertFalse(any(c["kind"] == "runtime" for c in conflicts))

    def test_global_runtime_info_only(self):
        existing = {"path": "p", "exists": True, "values": {"runtime": "opencode"}}
        global_defaults = {"values": {"runtime": "codex"}}
        conflicts, info = inventory.classify_conflicts(
            "opencode", existing, global_defaults, self._facts(), _PROJ
        )
        self.assertFalse(any(c["kind"] == "runtime" for c in conflicts))
        self.assertEqual(len([i for i in info if i["kind"] == "runtime"]), 1)

    def test_gsd_home_global_defaults_path(self):
        home = tempfile.mkdtemp()
        gsd_home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, gsd_home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        os.makedirs(os.path.join(gsd_home, ".gsd"), exist_ok=True)
        defaults_path = os.path.join(gsd_home, ".gsd", "defaults.json")
        with open(defaults_path, "w", encoding="utf-8") as handle:
            json.dump({"runtime": "codex"}, handle)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        env = _inventory_env(home)
        env["GSD_HOME"] = gsd_home
        code, parsed, _err = run_inventory(project, env, FakeRun(), "--host", "codex")
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertEqual(parsed["global_defaults"]["path"], defaults_path)

    def test_claude_md_path_missing_info(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        with open(os.path.join(project, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("x")
        os.makedirs(os.path.join(project, ".planning"), exist_ok=True)
        with open(os.path.join(project, ".planning", "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"claude_md_path": "./CLAUDE.md"}, fh)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        code, parsed, _err = run_inventory(
            project, _inventory_env(home), FakeRun(), "--host", "codex"
        )
        self.assertEqual(code, 0)
        assert parsed is not None
        claude_info = [i for i in parsed["info"] if i["kind"] == "claude_md_path"]
        self.assertEqual(len(claude_info), 1)
        self.assertIn("./CLAUDE.md", claude_info[0]["why"])
        self.assertIn("./AGENTS.md", claude_info[0]["why"])

    def _inventory_with_config(self, config):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        os.makedirs(os.path.join(project, ".planning"), exist_ok=True)
        with open(os.path.join(project, ".planning", "config.json"), "w", encoding="utf-8") as fh:
            json.dump(config, fh)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        code, parsed, err = run_inventory(
            project, _inventory_env(home), FakeRun(), "--host", "codex"
        )
        self.assertEqual(code, 0, err)
        assert parsed is not None
        return parsed

    def test_legacy_depth_reads_as_granularity(self):
        """B-IN-06: gsd-core hoists a top-level depth into an absent granularity
        (configuration.cjs normalization 4), so the plan shows a change, not an add."""
        parsed = self._inventory_with_config({"depth": "quick"})
        existing = parsed["existing_config"]
        self.assertEqual(existing["values"]["granularity"], "coarse")
        self.assertNotIn("depth", existing["values"])
        self.assertEqual(existing["legacy_depth"], "quick")
        depth_info = [i for i in parsed["info"] if i["kind"] == "depth"]
        self.assertEqual(len(depth_info), 1)
        self.assertEqual(depth_info[0]["key"], "depth")
        self.assertIn("legacy top-level depth", depth_info[0]["why"])
        plan = build(make_inventory(existing=existing))
        self.assertEqual(entry_map(plan)["granularity"]["existing"], "coarse")

    def test_legacy_depth_unmapped_value_passes_through(self):
        parsed = self._inventory_with_config({"depth": "custom"})
        self.assertEqual(parsed["existing_config"]["values"]["granularity"], "custom")

    def test_granularity_wins_over_legacy_depth(self):
        parsed = self._inventory_with_config({"depth": "quick", "granularity": "fine"})
        existing = parsed["existing_config"]
        self.assertEqual(existing["values"]["granularity"], "fine")
        self.assertNotIn("legacy_depth", existing)
        self.assertFalse(any(i["kind"] == "depth" for i in parsed["info"]))

    def test_unreadable_project_config_warning(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        os.makedirs(os.path.join(project, ".planning"), exist_ok=True)
        bad = os.path.join(project, ".planning", "config.json")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        code, parsed, _err = run_inventory(
            project, _inventory_env(home), FakeRun(), "--host", "codex"
        )
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertTrue(parsed["existing_config"]["exists"])
        self.assertEqual(parsed["existing_config"]["values"], {})
        self.assertTrue(any("unreadable" in w for w in parsed["warnings"]))

    def test_non_utf8_project_config_warning(self):
        """T-17-25: a Latin-1 config.json is unreadable-and-ignored, never a traceback."""
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        os.makedirs(os.path.join(project, ".planning"), exist_ok=True)
        with open(os.path.join(project, ".planning", "config.json"), "wb") as handle:
            handle.write(b'{"model_profile": "caf\xe9"}')
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        code, parsed, _err = run_inventory(
            project, _inventory_env(home), FakeRun(), "--host", "codex"
        )
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertEqual(parsed["existing_config"]["values"], {})
        self.assertTrue(any("unreadable" in w for w in parsed["warnings"]))

    def test_deeply_nested_json_is_unreadable(self):
        """T-17-25: json's RecursionError on pathological nesting is unreadable too."""
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        path = os.path.join(scratch, "config.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("[" * 200000 + "]" * 200000)
        data, warn = inventory._read_json_object(path)
        self.assertIsNone(data)
        assert warn is not None
        self.assertIn("unreadable", warn)


class TestProjectFacts(unittest.TestCase):
    def _facts(self, project):
        return project_facts.project_facts(project, None)

    def test_non_utf8_files_degrade_never_raise(self):
        """B-CR-03: a Latin-1 README.md/package.json is a degraded fact, not a traceback."""
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        with open(os.path.join(project, "README.md"), "wb") as handle:
            handle.write(b"Caf\xe9 React app\n")
        with open(os.path.join(project, "package.json"), "wb") as handle:
            handle.write(b'{"dependencies": {"pg": "1"}, "description": "caf\xe9"}')
        facts = self._facts(project)
        self.assertTrue(facts["frontend"])
        self.assertTrue(facts["db"])

    def test_unreadable_dirs_degrade(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        with mock.patch.object(project_facts.os, "listdir", side_effect=PermissionError):
            self.assertFalse(project_facts.detect_intel_index(project))
            self.assertEqual(project_facts.list_skills(project), [])

    def test_instruction_files_neither(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        facts = self._facts(project)
        self.assertEqual(facts["instruction_files"], {"AGENTS.md": False, "CLAUDE.md": False})
        self.assertIsNone(facts["instruction_file"])

    def test_instruction_files_agents_only(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        with open(os.path.join(project, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("a")
        facts = self._facts(project)
        self.assertTrue(facts["instruction_files"]["AGENTS.md"])
        self.assertEqual(facts["instruction_file"], "./AGENTS.md")

    def test_instruction_files_claude_only(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        with open(os.path.join(project, "CLAUDE.md"), "w", encoding="utf-8") as handle:
            handle.write("c")
        facts = self._facts(project)
        self.assertEqual(facts["instruction_file"], "./CLAUDE.md")

    def test_instruction_files_both_prefers_agents(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        for name in ("AGENTS.md", "CLAUDE.md"):
            with open(os.path.join(project, name), "w", encoding="utf-8") as handle:
                handle.write(name)
        facts = self._facts(project)
        self.assertEqual(facts["instruction_file"], "./AGENTS.md")

    def test_frontend_vue_package_json(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        with open(os.path.join(project, "package.json"), "w", encoding="utf-8") as handle:
            json.dump({"dependencies": {"vue": "3"}}, handle)
        self.assertTrue(self._facts(project)["frontend"])

    def test_frontend_readme_without_hints(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        with open(os.path.join(project, "README.md"), "w", encoding="utf-8") as handle:
            handle.write("plain readme\n")
        self.assertFalse(self._facts(project)["frontend"])

    def test_db_prisma_schema(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        os.makedirs(os.path.join(project, "prisma"), exist_ok=True)
        with open(os.path.join(project, "prisma", "schema.prisma"), "w", encoding="utf-8") as fh:
            fh.write("model X {}\n")
        self.assertTrue(self._facts(project)["db"])

    def test_db_migrations_directory(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        os.makedirs(os.path.join(project, "migrations"), exist_ok=True)
        self.assertTrue(self._facts(project)["db"])

    def test_db_package_json_pg(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        with open(os.path.join(project, "package.json"), "w", encoding="utf-8") as handle:
            json.dump({"dependencies": {"pg": "8"}}, handle)
        self.assertTrue(self._facts(project)["db"])

    def test_db_malformed_package_json_false(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        with open(os.path.join(project, "package.json"), "w", encoding="utf-8") as handle:
            handle.write("{")
        self.assertFalse(self._facts(project)["db"])

    def test_intel_index_with_json(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        intel = os.path.join(project, ".planning", "intel")
        os.makedirs(intel, exist_ok=True)
        with open(os.path.join(intel, "file-roles.json"), "w", encoding="utf-8") as handle:
            json.dump({}, handle)
        self.assertTrue(self._facts(project)["intel_index_present"])

    def test_intel_empty_dir_false(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        os.makedirs(os.path.join(project, ".planning", "intel"), exist_ok=True)
        self.assertFalse(self._facts(project)["intel_index_present"])

    def test_list_skills_sorted(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        for root, name in ((".claude/skills", "a"), (".agents/skills", "b")):
            skill_dir = os.path.join(project, root, name)
            os.makedirs(skill_dir, exist_ok=True)
            with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
                handle.write("skill")
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        code, parsed, _err = run_inventory(
            project, _inventory_env(home), FakeRun(), "--host", "codex"
        )
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertEqual(
            parsed["skills"],
            [
                {"name": "a", "root": ".claude/skills"},
                {"name": "b", "root": ".agents/skills"},
            ],
        )


class TestReadOnly(unittest.TestCase):
    def _readonly_project(self):
        home = tempfile.mkdtemp()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        os.makedirs(os.path.join(project, ".planning"), exist_ok=True)
        with open(os.path.join(project, ".planning", "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"runtime": "codex"}, fh)
        with open(os.path.join(project, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("a")
        with open(os.path.join(project, "package.json"), "w", encoding="utf-8") as handle:
            json.dump({"dependencies": {"react": "1"}}, handle)
        skill_dir = os.path.join(project, ".claude", "skills", "demo")
        os.makedirs(skill_dir, exist_ok=True)
        with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as handle:
            handle.write("s")
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        return home, project

    def test_hermetic_inventory_byte_identical(self):
        home, project = self._readonly_project()
        before = _tree_snapshot(project)
        saved = _lock_tree(project)
        self.addCleanup(_unlock_tree, saved)
        try:
            code, _parsed, _err = run_inventory(
                project, _inventory_env(home), FakeRun(), "--host", "codex"
            )
            self.assertEqual(code, 0)
        finally:
            _unlock_tree(saved)
        self.assertEqual(before, _tree_snapshot(project))


if __name__ == "__main__":
    unittest.main()
