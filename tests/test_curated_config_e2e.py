"""Real gsd-core runs for ai-kit-gsd-curated-config: the e2e tier (C-IN-06).

Every class here spawns real `node` against this checkout's own `.claude/gsd-core` under a
temp HOME, and skips when node or that gsd-core is missing. The hermetic suites stay in the
unit tier. Regenerate the tables fixture:
``UPDATE_GOLDEN=1 python3 -m unittest tests.test_curated_config_e2e -k TestGoldenTables``.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import (
    cli,
    gsd_catalog,
    host,
    plan_io,
    presets,
    workflow_defaults,
)
from ai_kit_spec import gsd_tools

# A module alias, not `from ... import TestReadOnly`: a TestCase bound here would rerun here.
import tests.test_curated_config_inventory as inventory_tests
from tests.test_curated_config_golden import FIXTURES, POLICY, REPO_ROOT, _tables_body
from tests.test_curated_config_inventory import (
    FakeRun,
    _lock_tree,
    _tree_snapshot,
    _unlock_tree,
    real_gsd_run,
    seed_cache,
)

_REPO_ROOT = str(REPO_ROOT)


class _RealGsdTestCase(unittest.TestCase):
    """Runs the CLI against the real gsd-tools it resolves for a temp project, under a
    temp HOME so gsd-core never reads the caller's real `~/.gsd` defaults or host homes.
    `RUNTIME_DIR` (resolver only, never the child env) points at this checkout, whose
    project-local gsd-core is the one the CLI then finds; without it, or without node,
    the test skips."""

    def setUp(self):
        super().setUp()
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.child_env = {"PATH": os.environ.get("PATH", ""), "HOME": home}
        self.resolve_env = {**self.child_env, "RUNTIME_DIR": _REPO_ROOT}

    def require_real_gsd(self, project_dir):
        self.node_bin = _real_node_executable()
        tools = gsd_catalog.resolve_gsd_tools_path(self.resolve_env, start=project_dir)
        if self.node_bin is None or tools is None:
            self.skipTest("no node, or no gsd-tools the CLI resolves for a temp project")

    def run_cli(self, argv):
        child_env, resolve_env, node_bin = self.child_env, self.resolve_env, self.node_bin
        return cli.main(
            argv,
            which_fn=lambda name: node_bin if name == "node" else None,
            env_fn=lambda: dict(resolve_env),
            run_fn=lambda cmd, **kw: subprocess.run(cmd, env=child_env, **kw),
        )

def _real_node_executable():
    """node's real binary, not a version-manager shim (volta, asdf, ...) that would look
    for its own state under the temp HOME; `None` when node is missing or broken."""
    if shutil.which("node") is None:
        return None
    try:
        proc = subprocess.run(
            ["node", "-e", "process.stdout.write(process.execPath)"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 and os.path.isfile(proc.stdout) else None

def real_gsd_paths() -> tuple[gsd_catalog.GsdCorePaths, str] | str:
    """The checkout-local gsd-core 1.16.0 paths, or the reason they are unusable."""
    node_bin = _real_node_executable()
    if node_bin is None:
        return "no node executable"
    tools = REPO_ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs"
    if not tools.is_file():
        return "no checkout-local .claude/gsd-core"
    version = gsd_tools.gsd_core_version(str(tools))
    if version != "1.16.0":
        return f"checkout-local gsd-core is {version}; gsd_tables_1_16.json pins 1.16.0"
    model_catalog = gsd_catalog.resolve_model_catalog_cjs_path(str(tools))
    config_schema = gsd_catalog.resolve_config_schema_cjs_path(str(tools))
    if not model_catalog or not config_schema:
        return "gsd-core lib/model-catalog.cjs or lib/config-schema.cjs missing"
    paths = gsd_catalog.GsdCorePaths(node_bin, model_catalog, config_schema, host.HOSTS)
    return paths, version

class TestRealIntegration(_RealGsdTestCase):
    """Skips itself when the CLI cannot resolve a real gsd-core for a temp project -- the
    hermetic unit tests above never depend on this, but a box with gsd-core installed in
    this checkout gets one real end-to-end proof."""

    def test_tracer_against_real_installed_gsd_tools(self):
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        self.require_real_gsd(scratch)
        exit1 = self.run_cli(["ensure-project", "--project-dir", scratch])
        self.assertEqual(exit1, 0)
        exit2 = self.run_cli(["apply-profile", "--project-dir", scratch, "--profile", "budget"])
        self.assertEqual(exit2, 0)
        with open(os.path.join(scratch, ".planning", "config.json"), encoding="utf-8") as f:
            config = json.load(f)
        self.assertEqual(config.get("model_profile"), "budget")

    def test_this_repos_own_config_is_never_touched(self):
        repo_config_path = os.path.join(_REPO_ROOT, ".planning", "config.json")
        with open(repo_config_path, "rb") as f:
            before = f.read()
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        self.require_real_gsd(scratch)
        self.run_cli(["ensure-project", "--project-dir", scratch])
        self.run_cli(["apply-profile", "--project-dir", scratch, "--profile", "budget"])
        with open(repo_config_path, "rb") as f:
            after = f.read()
        self.assertEqual(before, after)

class TestMergeModeEndToEnd(_RealGsdTestCase):
    """D-09 (07-CONTEXT.md): proves merge mode's two contracts end-to-end against a REAL
    installed gsd-core -- (1) a brand-new project correctly falls through Plan 01's
    `ensure-project` before this plan's own subcommands apply the curated bundle, and (2) an
    EXISTING `.planning/config.json` fixture with unrelated pre-existing keys is left
    byte-identical on those keys after the run. Skips itself when no gsd-core is installed on
    the machine running the suite, same pattern as `TestRealIntegration` above -- both halves
    require the REAL `config-set`/`config-new-project` subcommands actually mutating a file on
    disk, not a faked subprocess."""

    def setUp(self):
        super().setUp()
        self._scratch_dirs = []
        self.addCleanup(self._cleanup_scratch_dirs)

    def _cleanup_scratch_dirs(self):
        for d in self._scratch_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _mkscratch(self):
        d = tempfile.mkdtemp()
        self._scratch_dirs.append(d)
        return d

    def test_merge_mode_end_to_end(self):
        # (1) Fresh project, no .planning/ at all -- must fall through ensure-project first.
        fresh = self._mkscratch()
        self.require_real_gsd(fresh)
        exit_ensure = self.run_cli(["ensure-project", "--project-dir", fresh])
        self.assertEqual(exit_ensure, 0)
        exit_bundle = self.run_cli(
            [
                "apply-workflow-defaults",
                "--project-dir",
                fresh,
                "--ui-phase",
                "false",
                "--ui-review",
                "false",
            ]
        )
        self.assertEqual(exit_bundle, 0)
        fresh_config_path = os.path.join(fresh, ".planning", "config.json")
        with open(fresh_config_path, encoding="utf-8") as f:
            fresh_config = json.load(f)
        fresh_workflow = fresh_config.get("workflow", {})
        for key, expected_value in workflow_defaults.WORKFLOW_DEFAULTS.items():
            self.assertEqual(fresh_workflow.get(key), expected_value, key)

        # (2) Existing config with unrelated keys, hand-written (never via gsd-tools) -- must
        # be left byte-identical on those keys after apply-workflow-defaults runs.
        existing = self._mkscratch()
        planning_dir = os.path.join(existing, ".planning")
        os.makedirs(planning_dir, exist_ok=True)
        fixture = {
            "some_other_key": "untouched",
            "workflow": {"some_other_workflow_key": "keep-me"},
        }
        existing_config_path = os.path.join(planning_dir, "config.json")
        with open(existing_config_path, "w", encoding="utf-8") as f:
            json.dump(fixture, f)

        exit_bundle_existing = self.run_cli(
            [
                "apply-workflow-defaults",
                "--project-dir",
                existing,
                "--ui-phase",
                "false",
                "--ui-review",
                "false",
            ]
        )
        self.assertEqual(exit_bundle_existing, 0)
        with open(existing_config_path, encoding="utf-8") as f:
            after_config = json.load(f)
        self.assertEqual(after_config.get("some_other_key"), "untouched")
        self.assertEqual(
            after_config.get("workflow", {}).get("some_other_workflow_key"), "keep-me"
        )

class TestRealGsdInventory(_RealGsdTestCase):
    def _recommend_round_trip(self, inv, host_name):
        """The real inventory feeds recommend with no test-side reshaping (CR-01)."""
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = os.path.join(tmp, "inventory.json")
            with open(inv_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(inv))
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = cli.main(
                    [
                        "recommend", "--inventory", inv_path, "--profile", "adaptive",
                        "--rigor", "standard", "--out", os.path.join(tmp, "plan.json"),
                    ]
                )
            self.assertEqual(code, 0, f"{host_name}: {err.getvalue()}")

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
                    which_fn=lambda name, **_kw: self.node_bin if name == "node" else None,
                    env_fn=lambda: dict(self.resolve_env),
                    run_fn=real_gsd_run(
                        self.child_env, self.node_bin, fallback=spec_fake
                    ),
                )
            self.assertEqual(code, 0, host_name)
            parsed = json.loads(stdout.getvalue())
            self.assertEqual(parsed["gsd_core"]["version"], expected_version)
            self.assertEqual(parsed["gsd_core"]["scope"], "local")
            self.assertIn("gsd-planner", parsed["gsd_core"]["model_profiles"]["adaptive"])
            rejected = set(parsed["gsd_core"]["valid_keys"]["rejected"])
            closed = set(presets.closed_key_set(host_name))
            self.assertFalse(closed & rejected, host_name)
            self._recommend_round_trip(parsed, host_name)
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

class TestReadOnlyRealGsd(_RealGsdTestCase):
    def test_real_gsd_inventory_read_only(self):
        ro = inventory_tests.TestReadOnly()
        ro.setUp()
        self.addCleanup(ro.doCleanups)
        _home, project = ro._readonly_project()
        self.require_real_gsd(project)
        xdg = os.path.join(self.child_env["HOME"], "xdg-cache")
        seed_cache(xdg, {"clis": {}}, {"_meta": {"schema_version": 1}})
        self.child_env["XDG_CACHE_HOME"] = xdg
        self.resolve_env["XDG_CACHE_HOME"] = xdg
        before = _tree_snapshot(project)
        saved = _lock_tree(project)
        self.addCleanup(_unlock_tree, saved)
        spec_fake = FakeRun()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(
                    ["inventory", "--project-dir", project, "--host", "codex"],
                    which_fn=lambda name, **_kw: self.node_bin if name == "node" else None,
                    env_fn=lambda: dict(self.resolve_env),
                    run_fn=real_gsd_run(self.child_env, self.node_bin, fallback=spec_fake),
                )
            self.assertEqual(code, 0)
        finally:
            _unlock_tree(saved)
        self.assertEqual(before, _tree_snapshot(project))

class TestRealGsdLanes(_RealGsdTestCase):
    def test_query_returns_lanes_roots_and_extra_keys(self):
        paths_or_skip = real_gsd_paths()
        if isinstance(paths_or_skip, str):
            self.skipTest(paths_or_skip)
        paths, _version = paths_or_skip
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        self.child_env["GSD_HOME"] = self.child_env["HOME"]
        self.resolve_env["GSD_HOME"] = self.child_env["HOME"]
        run = real_gsd_run(self.child_env, paths.node_bin)
        result = gsd_catalog.query_gsd_tables(
            paths, project, ["model_profile"], run_fn=run
        )
        self.assertIsNotNone(result)
        assert result is not None
        lanes = result["review_lanes"]
        self.assertIsInstance(lanes, list)
        codex = next(row for row in lanes if row.get("slug") == "codex")
        self.assertEqual(codex["binary"], "codex")
        self.assertEqual(codex["model_key"], "review.models.codex")
        self.assertEqual(codex["effort_key"], "review.effort.codex")
        self.assertEqual(codex["default_effort"], "high")
        cursor = next(row for row in lanes if row.get("slug") == "cursor")
        self.assertEqual(cursor["binary"], "cursor-agent")
        self.assertIsNone(cursor["effort_key"])
        roots = result["skills_roots"]
        self.assertIsInstance(roots, dict)
        home = self.child_env["HOME"]
        self.assertEqual(roots["claude"], os.path.join(home, ".claude", "skills"))
        self.assertEqual(roots["codex"], os.path.join(home, ".agents", "skills"))
        accepted = result["valid_keys"]["accepted"]
        self.assertIn("agent_skills.gsd-executor", accepted)
        self.assertIn("review.models.codex", accepted)

    def test_inventory_carries_lanes(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        self.require_real_gsd(project)
        self.child_env["GSD_HOME"] = self.child_env["HOME"]
        self.resolve_env["GSD_HOME"] = self.child_env["HOME"]
        xdg = os.path.join(self.child_env["HOME"], "xdg-cache")
        seed_cache(xdg, {"clis": {}}, {"_meta": {"schema_version": 1}})
        self.child_env["XDG_CACHE_HOME"] = xdg
        self.resolve_env["XDG_CACHE_HOME"] = xdg
        spec_fake = FakeRun()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cli.main(
                ["inventory", "--project-dir", project, "--host", "claude"],
                which_fn=lambda name, **_kw: self.node_bin if name == "node" else None,
                env_fn=lambda: dict(self.resolve_env),
                run_fn=real_gsd_run(
                    self.child_env, self.node_bin, fallback=spec_fake
                ),
            )
        self.assertEqual(code, 0)
        parsed = json.loads(stdout.getvalue())
        self.assertEqual(parsed["schema_version"], plan_io.INVENTORY_SCHEMA_VERSION)
        self.assertTrue(parsed["gsd_core"]["review_lanes"])
        self.assertIsInstance(parsed["gsd_core"]["skills_roots"], dict)
        self.assertIsInstance(parsed["installed_runtimes"], list)
        inv_path = os.path.join(project, "inventory.json")
        with open(inv_path, "w", encoding="utf-8") as handle:
            handle.write(plan_io.canonical_json(parsed))
        loaded, err = plan_io.load_inventory(inv_path)
        self.assertIsNone(err)
        self.assertIsNotNone(loaded)


class TestGoldenTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._paths = real_gsd_paths()
        if isinstance(cls._paths, str):
            raise unittest.SkipTest(f"fixture not re-validated: {cls._paths}")
        cls.paths, cls.gsd_version = cls._paths
        cls.scratch = tempfile.mkdtemp()
        cls.child_env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": cls.scratch,
            "GSD_HOME": cls.scratch,
        }
        # Store on instance dict via list so unittest does not bind the nested _run fn.
        cls._gsd_runner = [real_gsd_run(cls.child_env, cls.paths.node_bin)]
        cls.project = os.path.join(cls.scratch, "project")
        os.makedirs(cls.project)

    @classmethod
    def tearDownClass(cls):
        import shutil

        shutil.rmtree(cls.scratch, ignore_errors=True)

    def _union_keys(self) -> list[str]:
        keys: set[str] = set()
        for host_name in host.HOSTS:
            keys.update(presets.closed_key_set(host_name))
        return sorted(keys)

    def test_union_keys_match_fixture(self):
        keys = self._union_keys()
        raw_stdout: list[str] = []

        def capture(cmd, **kw):
            res = self._gsd_runner[0](cmd, **kw)
            raw_stdout.append(res.stdout)
            return res

        result = gsd_catalog.query_gsd_tables(self.paths, self.project, keys, run_fn=capture)
        self.assertIsNotNone(result)
        assert result is not None
        rejected = set(result["valid_keys"]["rejected"])
        closed = set(keys)
        self.assertFalse(closed & rejected)
        raw_node = json.loads(raw_stdout[-1])
        raw_profiles = raw_node["model_profiles"]
        if os.environ.get("UPDATE_GOLDEN"):
            meta = {
                "gsd_core_version": self.gsd_version,
                "keys": "union of presets.closed_key_set over host.HOSTS",
            }
            # Fixture stores raw agent-first MODEL_PROFILES; skills_roots vary with HOME.
            payload = {
                k: v
                for k, v in {**result, "model_profiles": raw_profiles, "_meta": meta}.items()
                if k != "skills_roots"
            }
            (FIXTURES / "gsd_tables_1_16.json").write_text(
                plan_io.canonical_json(payload) + "\n", encoding="utf-8"
            )
            self.skipTest("UPDATE_GOLDEN set: rewrote gsd_tables_1_16.json; assertion skipped")
        body = _tables_body()
        self.assertEqual(raw_profiles, body["model_profiles"])
        expected = {**body, "model_profiles": gsd_catalog.profile_first(body["model_profiles"])}
        compare = {k: v for k, v in result.items() if k != "skills_roots"}
        self.assertEqual(compare, expected)
        roots = result["skills_roots"]
        assert isinstance(roots, dict)
        home = self.scratch
        self.assertEqual(roots["claude"], os.path.join(home, ".claude", "skills"))
        self.assertEqual(roots["codex"], os.path.join(home, ".agents", "skills"))

    def test_model_policy_unset_keys_accepted(self):
        flat = presets.flatten_config({"model_policy": POLICY})
        keys = sorted(flat)
        result = gsd_catalog.query_gsd_tables(
            self.paths, self.project, keys, run_fn=self._gsd_runner[0]
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["valid_keys"]["rejected"], [])
        self.assertIn(
            "model_policy.runtime_tiers.codex.opus",
            result["valid_keys"]["accepted"],
        )

if __name__ == "__main__":
    unittest.main()
