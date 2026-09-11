import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-config"),
)

from ai_kit_gsd_config import (
    cli,
    critical_agents,
    cross_ai_build,
    gsd_catalog,
    gsd_write,
    model_detect,
    preference_match,
)


def make_fake_run(results):
    """Returns a callable matching `subprocess.run`'s signature, consuming `results` (a list
    of `(returncode, stdout, stderr)` tuples) in order -- repeating the last one once
    exhausted -- and recording every invoked argv on `.calls` so assertions can inspect
    exactly what was shelled out."""
    pending = list(results)

    def _fake_run(argv, **_kwargs):
        _fake_run.calls.append(list(argv))
        if pending:
            returncode, stdout, stderr = pending.pop(0)
        else:
            returncode, stdout, stderr = 0, "", ""
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)

    _fake_run.calls = []
    return _fake_run


def fake_run(returncode, stdout="", stderr=""):
    """Single-result convenience wrapper over `make_fake_run`, matching `subprocess.run`'s
    signature for injection as `run_fn`."""
    return make_fake_run([(returncode, stdout, stderr)])


FAKE_NODE_BIN = "/usr/bin/node"


def _which_stub(path=FAKE_NODE_BIN):
    return lambda name: path if name == "node" else None


def _make_fake_install(root, include_model_catalog=True):
    """Builds a scratch fake-install tree `<root>/gsd-core/bin/gsd-tools.cjs` (and optionally
    its `lib/model-catalog.cjs` sibling) so `resolve_gsd_tools_path`/
    `resolve_model_catalog_cjs_path` resolve against REAL files on disk, never a mocked
    function -- only the eventual `node`/gsd-tools subprocess call is faked via `run_fn`."""
    bin_dir = os.path.join(root, "gsd-core", "bin")
    os.makedirs(bin_dir, exist_ok=True)
    gsd_tools_path = os.path.join(bin_dir, "gsd-tools.cjs")
    with open(gsd_tools_path, "w", encoding="utf-8") as f:
        f.write("// fake gsd-tools.cjs for hermetic tests\n")
    if include_model_catalog:
        lib_dir = os.path.join(bin_dir, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        with open(os.path.join(lib_dir, "model-catalog.cjs"), "w", encoding="utf-8") as f:
            f.write("// fake model-catalog.cjs for hermetic tests\n")
    return gsd_tools_path


class TestTracerEnsureProjectAndApplyProfile(unittest.TestCase):
    """Task 1 tracer: one model_profile answer travels from the CLI entrypoint through
    gsd-tools to a schema-validated config.json -- proven here via the exact argv shape
    shelled out, with no real subprocess/filesystem dependency."""

    def setUp(self):
        self.scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)
        self.fake_install_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.fake_install_root, ignore_errors=True)
        self.fake_gsd_tools_path = _make_fake_install(self.fake_install_root)

    def test_ensure_project_then_apply_profile_argv_shapes(self):
        run = make_fake_run([(0, "", ""), (0, "model_profile=budget", "")])
        env_fn = lambda: {"CLAUDE_CONFIG_DIR": self.fake_install_root}

        exit1 = cli.main(
            ["ensure-project", "--project-dir", self.scratch],
            which_fn=_which_stub(),
            run_fn=run,
            env_fn=env_fn,
        )
        exit2 = cli.main(
            ["apply-profile", "--project-dir", self.scratch, "--profile", "budget"],
            which_fn=_which_stub(),
            run_fn=run,
            env_fn=env_fn,
        )

        self.assertEqual(exit1, 0)
        self.assertEqual(exit2, 0)
        self.assertEqual(
            run.calls[0],
            [
                FAKE_NODE_BIN,
                self.fake_gsd_tools_path,
                "config-new-project",
                "--cwd",
                self.scratch,
                "--raw",
            ],
        )
        self.assertEqual(
            run.calls[1],
            [
                FAKE_NODE_BIN,
                self.fake_gsd_tools_path,
                "config-set",
                "model_profile",
                "budget",
                "--project-dir",
                self.scratch,
                "--raw",
            ],
        )


class TestApplyProfileValidation(unittest.TestCase):
    def test_unknown_profile_rejected_before_any_subprocess_call(self):
        run = make_fake_run([])
        with self.assertRaises(SystemExit) as ctx:
            cli.main(
                ["apply-profile", "--project-dir", "/fake/project", "--profile", "bogus"],
                which_fn=_which_stub(),
                run_fn=run,
                env_fn=lambda: {},
            )
        self.assertNotEqual(ctx.exception.code, 0)
        self.assertEqual(run.calls, [])


class TestResolveMissing(unittest.TestCase):
    def test_missing_node_binary_exits_2(self):
        run = make_fake_run([])
        exit_code = cli.main(
            ["ensure-project", "--project-dir", "/fake/project"],
            which_fn=lambda name: None,
            run_fn=run,
            env_fn=lambda: {},
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(run.calls, [])

    def test_missing_gsd_tools_path_exits_2(self):
        # Override HOME (not just one host's own env var) to a nonexistent directory so
        # every candidate in gsd_catalog.GSD_CORE_ROOT_CANDIDATES' default-path fallback
        # also misses -- otherwise this dev machine's own real installs (e.g. ~/.claude,
        # ~/.cursor) would still resolve via the unoverridden candidates' HOME-relative
        # defaults, masking the "nothing found" path this test exists to cover.
        run = make_fake_run([])
        exit_code = cli.main(
            ["ensure-project", "--project-dir", "/fake/project"],
            which_fn=_which_stub(),
            run_fn=run,
            env_fn=lambda: {"HOME": "/definitely/nonexistent/home"},
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(run.calls, [])


class TestRealIntegration(unittest.TestCase):
    """Skips itself when no gsd-core is actually installed on the machine running the suite --
    the hermetic unit tests above never depend on this, but a dev box or CI box with gsd-core
    installed gets one real end-to-end proof."""

    _REAL_GSD_TOOLS = gsd_catalog.resolve_gsd_tools_path(dict(os.environ))

    @unittest.skipUnless(_REAL_GSD_TOOLS is not None, "no installed gsd-core found on this machine")
    def test_tracer_against_real_installed_gsd_tools(self):
        scratch = tempfile.mkdtemp()
        try:
            exit1 = cli.main(["ensure-project", "--project-dir", scratch])
            self.assertEqual(exit1, 0)
            exit2 = cli.main(["apply-profile", "--project-dir", scratch, "--profile", "budget"])
            self.assertEqual(exit2, 0)
            with open(os.path.join(scratch, ".planning", "config.json"), encoding="utf-8") as f:
                config = json.load(f)
            self.assertEqual(config.get("model_profile"), "budget")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    @unittest.skipUnless(_REAL_GSD_TOOLS is not None, "no installed gsd-core found on this machine")
    def test_this_repos_own_config_is_never_touched(self):
        repo_config_path = os.path.join(
            os.path.dirname(__file__), "..", ".planning", "config.json"
        )
        with open(repo_config_path, "rb") as f:
            before = f.read()
        scratch = tempfile.mkdtemp()
        try:
            cli.main(["ensure-project", "--project-dir", scratch])
            cli.main(["apply-profile", "--project-dir", scratch, "--profile", "budget"])
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        with open(repo_config_path, "rb") as f:
            after = f.read()
        self.assertEqual(before, after)


class TestGsdCatalogResolution(unittest.TestCase):
    def test_resolve_gsd_tools_path_returns_first_existing_candidate(self):
        def isfile_fn(path):
            return path == os.path.join("CURSOR_ROOT", "gsd-core", "bin", "gsd-tools.cjs")

        env = {"CLAUDE_CONFIG_DIR": "/nope", "CURSOR_CONFIG_DIR": "CURSOR_ROOT"}
        result = gsd_catalog.resolve_gsd_tools_path(env, isfile_fn)
        self.assertEqual(result, os.path.join("CURSOR_ROOT", "gsd-core", "bin", "gsd-tools.cjs"))

    def test_resolve_gsd_tools_path_returns_none_when_nothing_found(self):
        self.assertIsNone(gsd_catalog.resolve_gsd_tools_path({}, lambda path: False))

    def test_resolve_model_catalog_cjs_path_present(self):
        result = gsd_catalog.resolve_model_catalog_cjs_path(
            "/root/gsd-core/bin/gsd-tools.cjs", lambda path: True
        )
        self.assertEqual(result, "/root/gsd-core/bin/lib/model-catalog.cjs")

    def test_resolve_model_catalog_cjs_path_absent(self):
        result = gsd_catalog.resolve_model_catalog_cjs_path(
            "/root/gsd-core/bin/gsd-tools.cjs", lambda path: False
        )
        self.assertIsNone(result)

    def test_resolve_model_catalog_cjs_path_none_when_gsd_tools_path_is_none(self):
        self.assertIsNone(gsd_catalog.resolve_model_catalog_cjs_path(None))

    def test_resolve_node_binary_delegates_to_which_fn(self):
        resolved = gsd_catalog.resolve_node_binary(lambda name: "/usr/bin/node")
        self.assertEqual(resolved, "/usr/bin/node")
        self.assertIsNone(gsd_catalog.resolve_node_binary(lambda name: None))


FAKE_CATALOG_PATH = "/fake/model-catalog.cjs"


class TestQueryAgentCatalog(unittest.TestCase):
    def test_non_zero_exit_returns_none(self):
        run = fake_run(1, stdout="", stderr="boom")
        self.assertIsNone(gsd_catalog.query_agent_catalog(FAKE_NODE_BIN, FAKE_CATALOG_PATH, run))

    def test_stdout_null_returns_none(self):
        run = fake_run(0, stdout="null")
        self.assertIsNone(gsd_catalog.query_agent_catalog(FAKE_NODE_BIN, FAKE_CATALOG_PATH, run))

    def test_missing_key_returns_none(self):
        run = fake_run(0, stdout=json.dumps({"tiers": {"a": "heavy"}}))
        self.assertIsNone(gsd_catalog.query_agent_catalog(FAKE_NODE_BIN, FAKE_CATALOG_PATH, run))

    def test_malformed_json_returns_none(self):
        run = fake_run(0, stdout="{not json")
        self.assertIsNone(gsd_catalog.query_agent_catalog(FAKE_NODE_BIN, FAKE_CATALOG_PATH, run))

    def test_empty_dict_values_return_none(self):
        run = fake_run(0, stdout=json.dumps({"tiers": {}, "phaseTypes": {}}))
        self.assertIsNone(gsd_catalog.query_agent_catalog(FAKE_NODE_BIN, FAKE_CATALOG_PATH, run))

    def test_well_formed_payload_round_trips_unchanged(self):
        payload = {"tiers": {"a": "heavy"}, "phaseTypes": {"a": "execution"}}
        run = fake_run(0, stdout=json.dumps(payload))
        result = gsd_catalog.query_agent_catalog(FAKE_NODE_BIN, FAKE_CATALOG_PATH, run)
        self.assertEqual(result, payload)

    def test_timeout_returns_none(self):
        def timeout_run(argv, **_kwargs):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=10)

        self.assertIsNone(
            gsd_catalog.query_agent_catalog(FAKE_NODE_BIN, FAKE_CATALOG_PATH, timeout_run)
        )


class TestGsdWrite(unittest.TestCase):
    def test_ensure_config_exists_true_on_exit_zero(self):
        run = fake_run(0)
        self.assertTrue(
            gsd_write.ensure_config_exists(FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", run)
        )

    def test_ensure_config_exists_false_on_nonzero_exit(self):
        run = fake_run(1, stderr="boom")
        self.assertFalse(
            gsd_write.ensure_config_exists(FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", run)
        )

    def test_config_set_success_returns_stdout(self):
        run = fake_run(0, stdout="model_profile=budget")
        ok, output = gsd_write.config_set(
            FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", "model_profile", "budget", run
        )
        self.assertTrue(ok)
        self.assertEqual(output, "model_profile=budget")

    def test_config_set_failure_returns_stderr(self):
        run = fake_run(1, stderr="Error: bad key")
        ok, output = gsd_write.config_set(
            FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", "bogus.key", "x", run
        )
        self.assertFalse(ok)
        self.assertEqual(output, "Error: bad key")

    def test_config_set_coerces_python_bool_to_lowercase_string(self):
        run_true = make_fake_run([(0, "ok", "")])
        gsd_write.config_set(
            FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", "some.flag", True, run_true
        )
        self.assertIn("true", run_true.calls[0])
        self.assertNotIn("True", run_true.calls[0])

        run_false = make_fake_run([(0, "ok", "")])
        gsd_write.config_set(
            FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", "some.flag", False, run_false
        )
        self.assertIn("false", run_false.calls[0])
        self.assertNotIn("False", run_false.calls[0])


class TestComputeOverrides(unittest.TestCase):
    def test_none_returns_only_unconditional_pairs(self):
        result = critical_agents.compute_overrides(None)
        self.assertEqual(len(result), 5)
        self.assertEqual(result["model_overrides.gsd-code-reviewer"], "opus")
        self.assertEqual(result["effort.agent_overrides.gsd-code-reviewer"], "high")
        self.assertEqual(result["model_overrides.gsd-executor"], "haiku")
        self.assertEqual(result["models.research"], "haiku")
        self.assertEqual(result["models.execution"], "haiku")

    def test_empty_dict_same_as_none(self):
        self.assertEqual(
            critical_agents.compute_overrides({}), critical_agents.compute_overrides(None)
        )

    def test_heavy_agent_gets_opus_high(self):
        tiers = {
            "fake-heavy-agent": "heavy",
            "fake-standard-agent": "standard",
            "gsd-code-reviewer": "standard",
            "gsd-executor": "standard",
        }
        result = critical_agents.compute_overrides(tiers)
        self.assertEqual(result["model_overrides.fake-heavy-agent"], "opus")
        self.assertEqual(result["effort.agent_overrides.fake-heavy-agent"], "high")

    def test_standard_and_light_agents_write_nothing(self):
        tiers = {"fake-standard-agent": "standard", "fake-light-agent": "light"}
        result = critical_agents.compute_overrides(tiers)
        self.assertNotIn("model_overrides.fake-standard-agent", result)
        self.assertNotIn("model_overrides.fake-light-agent", result)
        self.assertNotIn("effort.agent_overrides.fake-standard-agent", result)
        self.assertNotIn("effort.agent_overrides.fake-light-agent", result)

    def test_unconditional_pairs_always_present_alongside_sweep(self):
        tiers = {"fake-heavy-agent": "heavy"}
        result = critical_agents.compute_overrides(tiers)
        self.assertEqual(result["model_overrides.gsd-executor"], "haiku")
        self.assertEqual(result["models.research"], "haiku")
        self.assertEqual(result["models.execution"], "haiku")

    def test_executor_tier_drift_never_gets_a_conflicting_effort_override(self):
        """07-REVIEWS.md Cycle 2 self-verification finding: a future gsd-core reclassifying
        gsd-executor as "heavy" must never add effort.agent_overrides.gsd-executor, which
        would contradict the unconditional haiku floor for that agent."""
        tiers = {"gsd-executor": "heavy"}
        result = critical_agents.compute_overrides(tiers)
        self.assertEqual(result["model_overrides.gsd-executor"], "haiku")
        self.assertNotIn("effort.agent_overrides.gsd-executor", result)

    def test_code_reviewer_reclassified_heavy_is_harmless_overlap(self):
        tiers = {"gsd-code-reviewer": "heavy"}
        result = critical_agents.compute_overrides(tiers)
        self.assertEqual(result["model_overrides.gsd-code-reviewer"], "opus")
        self.assertEqual(result["effort.agent_overrides.gsd-code-reviewer"], "high")


class TestApplyCriticalAgentsCli(unittest.TestCase):
    def setUp(self):
        self.fake_install_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.fake_install_root, ignore_errors=True)

    def test_heavy_sweep_succeeds_and_writes_unconditional_plus_heavy_keys(self):
        _make_fake_install(self.fake_install_root, include_model_catalog=True)
        env_fn = lambda: {"CLAUDE_CONFIG_DIR": self.fake_install_root}

        query_payload_json = json.dumps(
            {
                "tiers": {"fake-heavy-agent": "heavy", "fake-standard-agent": "standard"},
                "phaseTypes": {"fake-heavy-agent": "planning", "fake-standard-agent": "execution"},
            }
        )
        # 5 unconditional config-set calls, then the node -e query call, then 2 sweep
        # config-set calls for the one synthetic heavy agent's two keys.
        results = [(0, "ok", "")] * 5 + [(0, query_payload_json, "")] + [(0, "ok", "")] * 2
        run = make_fake_run(results)

        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = cli.main(
                ["apply-critical-agents", "--project-dir", "/fake/project"],
                which_fn=_which_stub(),
                run_fn=run,
                env_fn=env_fn,
            )
        self.assertEqual(exit_code, 0)

        written_keys = {call[3] for call in run.calls if "config-set" in call}
        for key in critical_agents.compute_overrides(None):
            self.assertIn(key, written_keys)
        self.assertIn("model_overrides.fake-heavy-agent", written_keys)
        self.assertIn("effort.agent_overrides.fake-heavy-agent", written_keys)
        self.assertNotIn("model_overrides.fake-standard-agent", written_keys)

        summary = json.loads(buf.getvalue())
        self.assertTrue(summary["heavy_sweep_applied"])
        self.assertEqual(summary["unconditional_written"], 5)
        self.assertEqual(summary["heavy_agents_written"], 2)
        self.assertIsNone(summary["degraded_reason"])

    def test_model_catalog_not_found_degrades_but_still_writes_unconditional_keys(self):
        _make_fake_install(self.fake_install_root, include_model_catalog=False)
        env_fn = lambda: {"CLAUDE_CONFIG_DIR": self.fake_install_root}

        run = make_fake_run([(0, "ok", "")] * 5)

        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = cli.main(
                ["apply-critical-agents", "--project-dir", "/fake/project"],
                which_fn=_which_stub(),
                run_fn=run,
                env_fn=env_fn,
            )
        self.assertEqual(exit_code, 0)

        written_keys = {call[3] for call in run.calls if "config-set" in call}
        for key in critical_agents.compute_overrides(None):
            self.assertIn(key, written_keys)

        summary = json.loads(buf.getvalue())
        self.assertFalse(summary["heavy_sweep_applied"])
        self.assertEqual(summary["unconditional_written"], 5)
        self.assertEqual(summary["heavy_agents_written"], 0)
        self.assertEqual(summary["degraded_reason"], "model_catalog_not_found")

    def test_live_query_failed_degrades_but_still_writes_unconditional_keys(self):
        _make_fake_install(self.fake_install_root, include_model_catalog=True)
        env_fn = lambda: {"CLAUDE_CONFIG_DIR": self.fake_install_root}

        # 5 unconditional config-set calls succeed, then the node -e query call fails
        # (non-zero exit) -- the dynamic sweep must degrade, not crash or under-write.
        results = [(0, "ok", "")] * 5 + [(1, "", "node: boom")]
        run = make_fake_run(results)

        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = cli.main(
                ["apply-critical-agents", "--project-dir", "/fake/project"],
                which_fn=_which_stub(),
                run_fn=run,
                env_fn=env_fn,
            )
        self.assertEqual(exit_code, 0)

        written_keys = {call[3] for call in run.calls if "config-set" in call}
        for key in critical_agents.compute_overrides(None):
            self.assertIn(key, written_keys)

        summary = json.loads(buf.getvalue())
        self.assertFalse(summary["heavy_sweep_applied"])
        self.assertEqual(summary["unconditional_written"], 5)
        self.assertEqual(summary["degraded_reason"], "live_query_failed")


class TestResolveAiKitSpecPath(unittest.TestCase):
    """model_detect.resolve_ai_kit_spec_path -- mirrors ai-kit-spec-execute-gsd/SKILL.md's own
    Step 0 multi-candidate resolution pattern for the SAME sibling skill."""

    def test_plugin_root_candidate_wins_when_present(self):
        def isdir_fn(path):
            return path == os.path.join("/plugin/root", "skills", "ai-kit-spec-review")

        result = model_detect.resolve_ai_kit_spec_path(
            os.path.join("/somewhere", "skills", "ai-kit-gsd-config"),
            env={"CLAUDE_PLUGIN_ROOT": "/plugin/root", "HOME": "/home/nope"},
            isdir_fn=isdir_fn,
        )
        self.assertEqual(
            result, os.path.join("/plugin/root", "skills", "ai-kit-spec-review", "ai-kit-spec.py")
        )

    def test_home_claude_skills_candidate_when_no_plugin_root(self):
        def isdir_fn(path):
            return path == os.path.join("/home/user", ".claude", "skills", "ai-kit-spec-review")

        result = model_detect.resolve_ai_kit_spec_path(
            os.path.join("/somewhere", "skills", "ai-kit-gsd-config"),
            env={"HOME": "/home/user"},
            isdir_fn=isdir_fn,
        )
        self.assertEqual(
            result,
            os.path.join("/home/user", ".claude", "skills", "ai-kit-spec-review", "ai-kit-spec.py"),
        )

    def test_sibling_of_this_skill_fallback(self):
        def isdir_fn(path):
            return path == os.path.join("/somewhere", "skills", "ai-kit-spec-review")

        result = model_detect.resolve_ai_kit_spec_path(
            os.path.join("/somewhere", "skills", "ai-kit-gsd-config"),
            env={"HOME": "/nonexistent"},
            isdir_fn=isdir_fn,
        )
        self.assertEqual(
            result, os.path.join("/somewhere", "skills", "ai-kit-spec-review", "ai-kit-spec.py")
        )

    def test_none_when_nothing_found(self):
        result = model_detect.resolve_ai_kit_spec_path(
            os.path.join("/somewhere", "skills", "ai-kit-gsd-config"),
            env={"HOME": "/nonexistent"},
            isdir_fn=lambda path: False,
        )
        self.assertIsNone(result)


class TestBuildCandidatePool(unittest.TestCase):
    def test_opencode_only(self):
        snapshot = {
            "clis": {
                "opencode": {"installed": True, "models": ["a", "b"]},
                "cursor-agent": {"installed": False},
                "claude": {"installed": True},
            }
        }
        self.assertEqual(model_detect.build_candidate_pool(snapshot), {"opencode": ["a", "b"]})

    def test_cursor_only(self):
        snapshot = {
            "clis": {
                "opencode": {"installed": False},
                "cursor-agent": {"installed": True, "models": ["x"]},
            }
        }
        self.assertEqual(model_detect.build_candidate_pool(snapshot), {"cursor-agent": ["x"]})

    def test_neither_installed(self):
        snapshot = {
            "clis": {
                "opencode": {"installed": False},
                "cursor-agent": {"installed": False},
            }
        }
        self.assertEqual(model_detect.build_candidate_pool(snapshot), {})

    def test_installed_but_models_absent_cli_omitted(self):
        snapshot = {"clis": {"claude": {"installed": True, "path": "/usr/bin/claude"}}}
        self.assertEqual(model_detect.build_candidate_pool(snapshot), {})

    def test_none_snapshot_returns_empty_pool(self):
        self.assertEqual(model_detect.build_candidate_pool(None), {})


class TestVersionAtLeast(unittest.TestCase):
    def test_composer_below_threshold_fails(self):
        self.assertFalse(preference_match._version_at_least("composer-2.4", "composer", "2.5"))

    def test_composer_equal_and_above_pass(self):
        self.assertTrue(preference_match._version_at_least("composer-2.5", "composer", "2.5"))
        self.assertTrue(preference_match._version_at_least("composer-2.6", "composer", "2.5"))

    def test_composer_patch_version_passes(self):
        self.assertTrue(preference_match._version_at_least("composer-2.5.1", "composer", "2.5"))

    def test_grok_below_threshold_fails(self):
        self.assertFalse(preference_match._version_at_least("grok-4.5", "grok", "4.6"))

    def test_no_trailing_version_segment_returns_false_never_raises(self):
        self.assertFalse(preference_match._version_at_least("composer", "composer", "2.5"))


class TestBestExecutionCandidate(unittest.TestCase):
    def test_coding_or_executor_rule(self):
        pool = {"opencode": ["router-env/my-coding"]}
        self.assertEqual(
            preference_match.best_execution_candidate(pool),
            ("opencode", "router-env/my-coding", "coding-or-executor"),
        )

    def test_composer_rule(self):
        pool = {"opencode": ["composer-2.5"]}
        self.assertEqual(
            preference_match.best_execution_candidate(pool),
            ("opencode", "composer-2.5", "composer>=2.5"),
        )

    def test_grok_rule(self):
        pool = {"opencode": ["grok-4.6"]}
        self.assertEqual(
            preference_match.best_execution_candidate(pool), ("opencode", "grok-4.6", "grok>=4.6")
        )

    def test_deepseek_flash_rule(self):
        pool = {"opencode": ["deepseek-flash"]}
        self.assertEqual(
            preference_match.best_execution_candidate(pool),
            ("opencode", "deepseek-flash", "deepseek-flash"),
        )

    def test_luna_rule(self):
        pool = {"opencode": ["luna"]}
        self.assertEqual(
            preference_match.best_execution_candidate(pool), ("opencode", "luna", "luna")
        )

    def test_priority_order_earlier_rule_wins_even_when_listed_later(self):
        # "luna" (a later rule) sits ahead of "router-env/my-coding" (an earlier rule) in the
        # opencode list -- the earlier rule (coding-or-executor) must still win.
        pool = {"opencode": ["luna", "router-env/my-coding"]}
        self.assertEqual(
            preference_match.best_execution_candidate(pool),
            ("opencode", "router-env/my-coding", "coding-or-executor"),
        )

    def test_cursor_agent_only_fallback_when_opencode_has_no_match(self):
        pool = {"opencode": ["unrelated-model"], "cursor-agent": ["router-env/my-executor"]}
        self.assertEqual(
            preference_match.best_execution_candidate(pool),
            ("cursor-agent", "router-env/my-executor", "coding-or-executor"),
        )

    def test_no_match_returns_none(self):
        pool = {"opencode": ["unrelated-model"], "cursor-agent": ["also-unrelated"]}
        self.assertIsNone(preference_match.best_execution_candidate(pool))


class TestBestReviewCandidate(unittest.TestCase):
    def test_plan_review_rule(self):
        pool = {"opencode": ["router-env/my-plan-review"]}
        self.assertEqual(
            preference_match.best_review_candidate(pool),
            ("opencode", "router-env/my-plan-review", "plan-review"),
        )

    def test_gpt_sol_rule(self):
        pool = {"opencode": ["gpt-5.6-sol"]}
        self.assertEqual(
            preference_match.best_review_candidate(pool), ("opencode", "gpt-5.6-sol", "gpt-sol")
        )

    def test_glm_rule(self):
        pool = {"opencode": ["glm-5.2"]}
        self.assertEqual(
            preference_match.best_review_candidate(pool),
            ("opencode", "glm-5.2", "glm-5.2-or-5.3"),
        )

    def test_priority_order_earlier_rule_wins(self):
        pool = {"opencode": ["glm-5.2", "router-env/my-plan-review"]}
        self.assertEqual(
            preference_match.best_review_candidate(pool),
            ("opencode", "router-env/my-plan-review", "plan-review"),
        )

    def test_cursor_agent_only_fallback(self):
        pool = {"opencode": ["unrelated"], "cursor-agent": ["router-env/my-plan-review"]}
        self.assertEqual(
            preference_match.best_review_candidate(pool),
            ("cursor-agent", "router-env/my-plan-review", "plan-review"),
        )

    def test_empty_pool_returns_native_last_resort(self):
        self.assertEqual(
            preference_match.best_review_candidate({}), ("claude", "opus", "native-last-resort")
        )


class TestBuildExecutionCommand(unittest.TestCase):
    def test_fake_builder_fills_model_placeholder(self):
        def fake_execute_command_fn(cli_name, **params):
            return "opencode run -m {model} --dir " + params["target_dir"] + " --auto"

        result = cross_ai_build.build_execution_command(
            "opencode",
            "router-env/my-coding",
            "/fake/project",
            execute_command_fn=fake_execute_command_fn,
        )
        self.assertNotIn("{model}", result)
        self.assertIn("router-env/my-coding", result)

    def test_unknown_cli_returns_none_never_raises(self):
        def fake_execute_command_fn(cli_name, **params):
            raise ValueError(f"no builder for {cli_name}")

        result = cross_ai_build.build_execution_command(
            "unknown-cli",
            "some-model",
            "/fake/project",
            execute_command_fn=fake_execute_command_fn,
        )
        self.assertIsNone(result)


class TestCliToReviewerSlug(unittest.TestCase):
    def test_cursor_agent_maps_to_cursor_not_itself(self):
        self.assertEqual(cross_ai_build.CLI_TO_REVIEWER_SLUG["cursor-agent"], "cursor")
        self.assertNotEqual(cross_ai_build.CLI_TO_REVIEWER_SLUG["cursor-agent"], "cursor-agent")

    def test_opencode_and_claude_map_to_themselves(self):
        self.assertEqual(cross_ai_build.CLI_TO_REVIEWER_SLUG["opencode"], "opencode")
        self.assertEqual(cross_ai_build.CLI_TO_REVIEWER_SLUG["claude"], "claude")


class TestApplyExecutionCli(unittest.TestCase):
    def setUp(self):
        self.fake_install_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.fake_install_root, ignore_errors=True)
        _make_fake_install(self.fake_install_root)
        self.env_fn = lambda: {"CLAUDE_CONFIG_DIR": self.fake_install_root}

    def test_real_candidate_writes_both_keys(self):
        run = make_fake_run([(0, "ok", ""), (0, "ok", "")])
        buf = io.StringIO()
        with (
            unittest.mock.patch.object(
                cross_ai_build,
                "build_execution_command",
                return_value="opencode run -m router-env/my-coding --dir /fake/project --auto",
            ),
            contextlib.redirect_stdout(buf),
        ):
            exit_code = cli.main(
                [
                    "apply-execution",
                    "--project-dir",
                    "/fake/project",
                    "--cli",
                    "opencode",
                    "--model",
                    "router-env/my-coding",
                ],
                which_fn=_which_stub(),
                run_fn=run,
                env_fn=self.env_fn,
            )
        self.assertEqual(exit_code, 0)
        written_keys = [call[3] for call in run.calls if "config-set" in call]
        self.assertEqual(written_keys, ["workflow.cross_ai_execution", "workflow.cross_ai_command"])
        summary = json.loads(buf.getvalue())
        self.assertTrue(summary["cross_ai_execution_written"])
        self.assertTrue(summary["cross_ai_command_written"])
        self.assertIsNone(summary["degraded_reason"])

    def test_no_candidate_writes_only_execution_flag(self):
        run = make_fake_run([(0, "ok", "")])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = cli.main(
                ["apply-execution", "--project-dir", "/fake/project"],
                which_fn=_which_stub(),
                run_fn=run,
                env_fn=self.env_fn,
            )
        self.assertEqual(exit_code, 0)
        written_keys = [call[3] for call in run.calls if "config-set" in call]
        self.assertEqual(written_keys, ["workflow.cross_ai_execution"])
        summary = json.loads(buf.getvalue())
        self.assertTrue(summary["cross_ai_execution_written"])
        self.assertFalse(summary["cross_ai_command_written"])
        self.assertEqual(summary["degraded_reason"], "no_candidate")


class TestApplyReviewCli(unittest.TestCase):
    def setUp(self):
        self.fake_install_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.fake_install_root, ignore_errors=True)
        _make_fake_install(self.fake_install_root)
        self.env_fn = lambda: {"CLAUDE_CONFIG_DIR": self.fake_install_root}

    def _run_apply_review(self, config_get_stdout, config_get_returncode=0):
        results = [
            (0, "ok", ""),  # workflow.plan_review_convergence
            (0, "ok", ""),  # review.effort.opencode
            (config_get_returncode, config_get_stdout, ""),  # config-get review.default_reviewers
            (0, "ok", ""),  # review.default_reviewers write
            (0, "ok", ""),  # review.models.<slug> write
        ]
        run = make_fake_run(results)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = cli.main(
                [
                    "apply-review",
                    "--project-dir",
                    "/fake/project",
                    "--cli",
                    "opencode",
                    "--model",
                    "router-env/my-plan-review",
                ],
                which_fn=_which_stub(),
                run_fn=run,
                env_fn=self.env_fn,
            )
        return exit_code, run, json.loads(buf.getvalue())

    def test_existing_list_with_different_slug_merges_both(self):
        exit_code, run, summary = self._run_apply_review(json.dumps(["claude"]))
        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["default_reviewers"], ["claude", "opencode"])
        review_writes = [
            call for call in run.calls
            if "config-set" in call and call[3] == "review.default_reviewers"
        ]
        self.assertEqual(len(review_writes), 1)
        self.assertEqual(json.loads(review_writes[0][4]), ["claude", "opencode"])

    def test_absent_key_writes_fresh_one_element_list(self):
        exit_code, _run, summary = self._run_apply_review("", config_get_returncode=1)
        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["default_reviewers"], ["opencode"])

    def test_already_contains_resolved_slug_dedupes(self):
        """07-REVIEWS.md Cycle 2 MEDIUM: the realistic fresh-project -> apply-review path, where
        a global ~/.gsd/defaults.json has already pre-seeded review.default_reviewers with the
        same slug this run resolves to -- the dedupe must leave the list unchanged, and
        review.models.<slug>/review.effort.opencode must still be written/confirmed with THIS
        run's resolved values, never silently skipped because the slug was already present."""
        exit_code, run, summary = self._run_apply_review(json.dumps(["opencode"]))
        self.assertEqual(exit_code, 0)
        self.assertEqual(summary["default_reviewers"], ["opencode"])
        review_writes = [
            call for call in run.calls
            if "config-set" in call and call[3] == "review.default_reviewers"
        ]
        self.assertEqual(json.loads(review_writes[0][4]), ["opencode"])
        model_writes = [
            call for call in run.calls
            if "config-set" in call and call[3] == "review.models.opencode"
        ]
        self.assertEqual(len(model_writes), 1)
        self.assertEqual(model_writes[0][4], "router-env/my-plan-review")
        effort_writes = [
            call for call in run.calls
            if "config-set" in call and call[3] == "review.effort.opencode"
        ]
        self.assertEqual(len(effort_writes), 1)
        self.assertTrue(summary["review_effort_opencode_written"])
        self.assertTrue(summary["plan_review_convergence_written"])


if __name__ == "__main__":
    unittest.main()
