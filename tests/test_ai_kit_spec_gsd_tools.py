"""Tests for the one shared gsd-tools resolver and config write wrappers
(`ai_kit_spec.gsd_tools`, D-18): launcher-order candidates pinned to `edge_floor.py`'s
`engine_candidates`, project-local-first resolution (R17) and the wrapper argv shapes. All
filesystem fixtures live in tempfile dirs. The real gsd-core `previousValue` contract the plan
16.1-10 undo log relies on is pinned by `TestRealGsdTools` in the e2e-tier
`tests/test_ai_kit_spec_e2e.py`."""
import importlib
import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

gsd_tools = importlib.import_module("ai_kit_spec.gsd_tools")


def _load_edge_floor():
    spec = importlib.util.spec_from_file_location(
        "edge_floor_under_test",
        os.path.join(_REPO_ROOT, "skills", "ai-kit-gsd-spec-discuss", "scripts", "edge_floor.py"),
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EDGE_FLOOR = _load_edge_floor()


def _mkdtemp():
    d = tempfile.mkdtemp()
    return d


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def recording_run(results):
    """run_fn returning `subprocess.CompletedProcess` per `(rc, stdout, stderr)`, repeating
    the last once exhausted, and recording every argv on `.calls`."""
    pending = list(results)

    def _run(argv, **_kwargs):
        _run.calls.append(list(argv))
        rc, stdout, stderr = pending.pop(0) if pending else (0, "", "")
        return subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr=stderr)

    _run.calls = []
    return _run


GSD_TOOLS_SUFFIX = gsd_tools.GSD_TOOLS_REL
EDGE_SUFFIX = EDGE_FLOOR.ENGINE_REL


class TestResolverOrder(unittest.TestCase):
    """D-18/R17: candidate order is GSD's own launcher order, pinned to edge_floor."""

    def test_gsd_core_roots_project_local_first_then_host_homes(self):
        env = {"HOME": "H"}
        roots = gsd_tools.gsd_core_roots(env, "R")
        self.assertEqual(roots[:3], ["R/gsd-core", "R/.claude/gsd-core", "R/.codex/gsd-core"])
        self.assertEqual(roots[3:], [os.path.join(h, "gsd-core") for h in
                                     gsd_tools._host_homes(env)])

    def test_skill_md_lists_project_local_roots_first_in_resolver_order(self):
        # R17: the SKILL.md lookup text names the same local roots, in the same order,
        # as gsd_core_roots, and before any host-home install.
        skill = os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-execute-gsd", "SKILL.md")
        with open(skill, encoding="utf-8") as f:
            text = f.read()
        documented = re.findall(r"`(<root>/[^`]+)`", text)
        self.assertEqual(documented[:3], gsd_tools.gsd_core_roots({"HOME": "H"}, "<root>")[:3])
        first_local = text.index("`<root>/gsd-core`")
        self.assertNotIn("$HOME", text[:first_local])

    def test_non_launcher_candidates_match_edge_floor_engine_candidates(self):
        env = {
            "HOME": _mkdtemp(),
            "XDG_CONFIG_HOME": _mkdtemp(),
            "CODEX_HOME": _mkdtemp(),
            "CLAUDE_CONFIG_DIR": _mkdtemp(),
        }
        self.addCleanup(shutil.rmtree, env["HOME"], ignore_errors=True)
        self.addCleanup(shutil.rmtree, env["XDG_CONFIG_HOME"], ignore_errors=True)
        self.addCleanup(shutil.rmtree, env["CODEX_HOME"], ignore_errors=True)
        self.addCleanup(shutil.rmtree, env["CLAUDE_CONFIG_DIR"], ignore_errors=True)
        root = _mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        ours = gsd_tools.gsd_tools_candidates(env, root)
        theirs = EDGE_FLOOR.engine_candidates(env, root)
        ours_stripped = [p[: -len(GSD_TOOLS_SUFFIX)] for p in ours]
        theirs_stripped = [p[: -len(EDGE_SUFFIX)] for p in theirs]
        self.assertEqual(ours_stripped, theirs_stripped)

    def test_launcher_candidate_from_path_and_absent_without_path(self):
        tree = _mkdtemp()
        self.addCleanup(shutil.rmtree, tree, ignore_errors=True)
        home = _mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        start = _mkdtemp()  # empty: the checkout's own .claude/gsd-core is never a candidate
        self.addCleanup(shutil.rmtree, start, ignore_errors=True)
        bin_dir = os.path.join(tree, "gsd-core", "bin")
        launcher = _write(os.path.join(bin_dir, "gsd_run"), "#!/bin/sh\n")
        os.chmod(launcher, os.stat(launcher).st_mode | stat.S_IXUSR | stat.S_IXGRP
                 | stat.S_IXOTH)
        gsd_tools_path = _write(os.path.join(bin_dir, "gsd-tools.cjs"), "// fake\n")
        env = {"HOME": home, "PATH": bin_dir}
        candidates = gsd_tools.gsd_tools_candidates(env, start)
        self.assertEqual(candidates[-1], gsd_tools_path)
        self.assertEqual(gsd_tools.resolve_gsd_tools(env, start=start), gsd_tools_path)
        no_path_env = {"HOME": home}
        self.assertEqual(gsd_tools.gsd_tools_candidates(no_path_env, start),
                         candidates[:-1])
        self.assertIsNone(gsd_tools.resolve_gsd_tools(no_path_env, start=start))


class TestLocalFirst(unittest.TestCase):
    """R17 adjacency: with both a project-local and a global fake gsd-core, the local one
    wins; each alone is found; neither returns None."""

    def test_project_local_wins_over_home_install(self):
        project = _mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        home = _mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        local = _write(os.path.join(project, ".claude", "gsd-core", "bin", "gsd-tools.cjs"))
        _write(os.path.join(home, ".claude", "gsd-core", "bin", "gsd-tools.cjs"))
        env = {"HOME": home, "RUNTIME_DIR": project}
        self.assertEqual(gsd_tools.resolve_gsd_tools(env, start=project), local)

    def test_global_only_found(self):
        home = _mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        start = _mkdtemp()
        self.addCleanup(shutil.rmtree, start, ignore_errors=True)
        expected = _write(os.path.join(home, ".codex", "gsd-core", "bin", "gsd-tools.cjs"))
        env = {"HOME": home}
        self.assertEqual(gsd_tools.resolve_gsd_tools(env, start=start), expected)

    def test_none_when_nothing_found(self):
        home = _mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        start = _mkdtemp()
        self.addCleanup(shutil.rmtree, start, ignore_errors=True)
        self.assertIsNone(gsd_tools.resolve_gsd_tools({"HOME": home}, start=start))


class TestCoreVersion(unittest.TestCase):
    def test_non_utf8_version_file_is_none(self):
        """T-17-25: a non-UTF-8 VERSION file reads as unknown, never a traceback."""
        root = _mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, "bin"))
        with open(os.path.join(root, "VERSION"), "wb") as f:
            f.write(b"1.16\xff\n")
        self.assertIsNone(gsd_tools.gsd_core_version(os.path.join(root, "bin", "gsd-tools.cjs")))


class TestWrappers(unittest.TestCase):
    """The config-* wrapper argv shapes and the `previousValue` contract (D-17/RUN-11)."""

    TOOLS = gsd_tools.GsdTools("node", "/g/gsd-tools.cjs")

    def test_config_set_argv_and_none_unset(self):
        run = recording_run([(0, '{"updated": true}', "")])
        ok, output = gsd_tools.config_set(self.TOOLS, "/p", "a.b", None, run_fn=run)
        self.assertTrue(ok)
        self.assertEqual(output, '{"updated": true}')
        self.assertEqual(
            run.calls[0],
            ["node", "/g/gsd-tools.cjs", "config-set", "a.b", "null",
             "--project-dir", "/p"],
        )
        self.assertNotIn("--raw", run.calls[0])

    def test_config_set_coercion(self):
        for value, expected in [(True, "true"), (False, "false"), (["x", "y"], '["x", "y"]'),
                                ({"k": 1}, '{"k": 1}'), ("s", "s")]:
            run = recording_run([(0, "ok", "")])
            gsd_tools.config_set(self.TOOLS, "/p", "k", value, run_fn=run)
            self.assertEqual(run.calls[0][4], expected)

    def test_config_set_failure_returns_stderr(self):
        ok, output = gsd_tools.config_set(
            self.TOOLS, "/p", "k", 1, run_fn=recording_run([(1, "", "Error: bad")])
        )
        self.assertFalse(ok)
        self.assertEqual(output, "Error: bad")

    def test_prior_value_shapes(self):
        self.assertEqual(
            gsd_tools.prior_value('{"updated": true, "key": "k", "value": 2, "previousValue": 1}'),
            (True, 1),
        )
        self.assertEqual(
            gsd_tools.prior_value('{"updated": true, "key": "k", "value": 2}'), (False, None)
        )
        self.assertIsNone(gsd_tools.prior_value("k=2"))
        self.assertIsNone(gsd_tools.prior_value("[1]"))

    def test_config_get_found(self):
        got = gsd_tools.config_get(
            self.TOOLS, "/p", "x", run_fn=recording_run([(0, '["a"]', "")])
        )
        self.assertEqual(got.found, True)
        self.assertEqual(got.value, ["a"])
        self.assertIsNone(got.error)

    def test_config_get_clean_miss_has_no_error(self):
        got = gsd_tools.config_get(
            self.TOOLS, "/p", "x",
            run_fn=recording_run([(1, "", "Error: Key not found: x")]),
        )
        self.assertEqual(got, (False, None, None))

    def test_config_get_other_failure_carries_stderr(self):
        got = gsd_tools.config_get(
            self.TOOLS, "/p", "x", run_fn=recording_run([(1, "", "boom")])
        )
        self.assertEqual(got, (False, None, "boom"))

    def test_config_get_non_json_output_names_it(self):
        got = gsd_tools.config_get(
            self.TOOLS, "/p", "x", run_fn=recording_run([(0, "not json", "")])
        )
        self.assertFalse(got.found)
        self.assertIn("not json", got.error)

    def test_config_path(self):
        run = recording_run([(0, "/p/.planning/config.json\n", "")])
        self.assertEqual(
            gsd_tools.config_path(self.TOOLS, "/p", run_fn=run), "/p/.planning/config.json"
        )
        self.assertEqual(
            run.calls[0], ["node", "/g/gsd-tools.cjs", "config-path", "--cwd", "/p"]
        )
        self.assertIsNone(
            gsd_tools.config_path(self.TOOLS, "/p", run_fn=recording_run([(1, "", "err")]))
        )

    def test_config_path_timeout_or_spawn_error_is_none(self):
        """B-WR-03: a hung or unspawnable gsd-tools never blocks or crashes the caller."""
        seen = []

        def raiser(exc):
            def run(cmd, **kw):
                seen.append(kw.get("timeout"))
                raise exc
            return run

        for exc in (subprocess.TimeoutExpired("node", 10), OSError("no node")):
            self.assertIsNone(gsd_tools.config_path(self.TOOLS, "/p", run_fn=raiser(exc)))
        self.assertEqual(seen, [10, 10])

    def test_ensure_config_exists(self):
        run = recording_run([(0, "ok", "")])
        self.assertTrue(gsd_tools.ensure_config_exists(self.TOOLS, "/p", run_fn=run))
        self.assertEqual(
            run.calls[0],
            ["node", "/g/gsd-tools.cjs", "config-new-project", "--cwd", "/p", "--raw"],
        )
        self.assertFalse(
            gsd_tools.ensure_config_exists(self.TOOLS, "/p", run_fn=recording_run([(1, "", "")]))
        )

    def test_ensure_config_exists_timeout_and_spawn_error_are_false(self):
        seen = []

        def raiser(exc):
            def run(_cmd, **kw):
                seen.append((kw.get("timeout"), kw.get("env")))
                raise exc
            return run

        for exc in (subprocess.TimeoutExpired("node", 120), OSError("no node")):
            self.assertFalse(
                gsd_tools.ensure_config_exists(
                    self.TOOLS, "/p", run_fn=raiser(exc), env={"A": "1"}, timeout=120
                )
            )
        self.assertEqual(seen, [(120, {"A": "1"}), (120, {"A": "1"})])



class TestStrictEncoder(unittest.TestCase):
    def test_encodes_allowed_values(self):
        enc = gsd_tools.encode_value_strict
        self.assertEqual(enc("k", None), "null")
        self.assertEqual(enc("k", True), "true")
        self.assertEqual(enc("k", ["b", "a"]), '["b","a"]')
        self.assertEqual(enc("k", {"b": 1, "a": 2}), '{"a":2,"b":1}')
        self.assertEqual(enc("k", 12), "12")
        self.assertEqual(enc("k", 1.5), "1.5")
        self.assertEqual(enc("k", "gpt-5.6-sol"), "gpt-5.6-sol")
        self.assertEqual(enc("k", "router-env/my-coding"), "router-env/my-coding")
        self.assertEqual(
            enc("k", "node .planning/scripts/cross-ai.mjs"),
            "node .planning/scripts/cross-ai.mjs",
        )

    def test_refuses_retyped_strings_and_bad_types(self):
        enc = gsd_tools.encode_value_strict
        for bad in ("true", "false", "null", "12", " 12", "1e3", "-0.5", "[1", "{x"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as ctx:
                    enc("my.key", bad)
                msg = str(ctx.exception)
                self.assertTrue(msg.startswith("my.key"))
                self.assertIn("re-typed", msg)
        for bad in (float("nan"), (1,), object()):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as ctx:
                    enc("my.key", bad)
                self.assertIn("my.key", str(ctx.exception))

    def test_refuses_non_serializable_containers(self):
        enc = gsd_tools.encode_value_strict
        for bad in ({"a": float("nan")}, [float("inf")], {"a": object()}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as ctx:
                    enc("my.key", bad)
                msg = str(ctx.exception)
                self.assertTrue(msg.startswith("my.key"))
                self.assertIsInstance(ctx.exception, ValueError)


class TestConfigSetStrict(unittest.TestCase):
    TOOLS = gsd_tools.GsdTools("node", "/g/gsd-tools.cjs")

    def test_success_argv_env_and_timeout(self):
        recorded = {}
        base_run = recording_run([(0, " ok \n", "")])

        def run(argv, **kw):
            recorded["kwargs"] = kw
            return base_run(argv, **kw)

        call = gsd_tools.ConfigCall(self.TOOLS, "/p", run, {"GSD_WORKSTREAM": "ws"})
        ok, output = gsd_tools.config_set_strict(
            call, "workflow.cross_ai_timeout", 1800,
        )
        self.assertTrue(ok)
        self.assertEqual(output, "ok")
        self.assertEqual(
            base_run.calls[0],
            [
                "node", "/g/gsd-tools.cjs", "query", "config-set",
                "workflow.cross_ai_timeout", "1800", "--project-dir", "/p",
            ],
        )
        self.assertEqual(recorded["kwargs"]["env"], {"GSD_WORKSTREAM": "ws"})
        self.assertEqual(recorded["kwargs"]["timeout"], 60)

    def test_encoder_refusal_spawns_nothing(self):
        run = recording_run([(0, "ok", "")])
        call = gsd_tools.ConfigCall(self.TOOLS, "/p", run)
        ok, output = gsd_tools.config_set_strict(call, "k", float("nan"))
        self.assertFalse(ok)
        self.assertIn("re-typed", output)
        self.assertEqual(run.calls, [])

    def test_failure_and_oserror_paths(self):
        run = recording_run([(1, "", "bad stderr")])
        call = gsd_tools.ConfigCall(self.TOOLS, "/p", run)
        ok, output = gsd_tools.config_set_strict(call, "k", 1)
        self.assertFalse(ok)
        self.assertEqual(output, "bad stderr")

        def boom(*a, **k):
            raise OSError("spawn failed")

        call2 = gsd_tools.ConfigCall(self.TOOLS, "/p", boom)
        ok2, output2 = gsd_tools.config_set_strict(call2, "k", 1)
        self.assertFalse(ok2)
        self.assertEqual(output2, "spawn failed")

    def test_env_none_passes_through(self):
        seen = {}

        def capture(argv, **kw):
            seen["env"] = kw.get("env")
            return subprocess.CompletedProcess(argv, 0, stdout="x", stderr="")

        call = gsd_tools.ConfigCall(self.TOOLS, "/p", capture, None)
        gsd_tools.config_set_strict(call, "k", 1)
        self.assertIsNone(seen["env"])


if __name__ == "__main__":
    unittest.main()
