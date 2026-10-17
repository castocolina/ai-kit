"""Per-call routing (D-08, D-15, D-19, D-20, D-22, D-31; SPEC R3, R8).

Every test injects fakes and a scratch cache. Nothing here touches a real CLI, node,
or the user's own config and cache directories.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import routing
from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.cli import main
from ai_kit_spec.config_io import cfg_render_toml, cfg_resolve, cfg_write_toml
from ai_kit_spec.detection import (
    CLAUDE_FALLBACK_MODEL_IDS,
    CLAUDE_MODEL_ALIASES,
    RUNTIMES_SCHEMA_VERSION,
    claude_runtime_fields,
)
from ai_kit_spec.runner_dispatch import RunnerResult


def _ok(argv, **_kwargs):
    return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


def _scratch_env(root):
    """HOME, XDG config and XDG cache under `root`; never the user's own directories."""
    env = {name: os.path.join(root, sub) for name, sub in
           (("HOME", "home"), ("XDG_CONFIG_HOME", "xdg"), ("XDG_CACHE_HOME", "cache"))}
    os.makedirs(os.path.join(env["XDG_CONFIG_HOME"], "ai-kit"), exist_ok=True)
    os.makedirs(env["XDG_CACHE_HOME"], exist_ok=True)
    return env


def _snapshot(clis):
    return {"schema_version": RUNTIMES_SCHEMA_VERSION, "clis": clis}


def _read(path):
    with open(path, encoding="utf-8") as stream:
        return stream.read()


class TestResolveRoutes(unittest.TestCase):
    def setUp(self):
        routing._REFRESHED.clear()

    def _env(self, root):
        return {**_scratch_env(root), "OPENCODE": "1"}

    def _write_config(self, xdg, reviewers, ladder):
        cfg_write_toml(
            os.path.join(xdg, "ai-kit", "review-spec.toml"),
            {"policy": {"mode": "single", "ladder": ladder}, "reviewers": reviewers},
        )

    def _write_runtimes(self, env, snapshot, age_s):
        path = routing.cache_runtimes_path(env)
        cache_write_json(path, snapshot)
        stamp = time.time() - age_s
        os.utime(path, (stamp, stamp))
        return path

    def _snapshot(self, models):
        return _snapshot({"opencode": {"installed": True, "path": "/fake/opencode",
                                       "models": models}})

    def _resolve(self, root, env, run_fn, popen_fn=None, which_fn=None):
        out, err = io.StringIO(), io.StringIO()
        kwargs = {"run_fn": run_fn, "env_fn": lambda: dict(env),
                  "which_fn": which_fn or (lambda _name: None)}
        if popen_fn is not None:
            kwargs["popen_fn"] = popen_fn
        with mock.patch.dict(os.environ, env, clear=True), \
                redirect_stdout(out), redirect_stderr(err):
            code = main(["resolve-reviewers", "--cwd", root, "--cross-ai",
                         "--quota-path", os.path.join(root, "quota.json")], **kwargs)
        return code, out.getvalue(), err.getvalue()

    def test_routed_ladder(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            self._write_config(env["XDG_CONFIG_HOME"], [
                {"key": "op-good", "runtime": "opencode", "model": "zen/listed",
                 "vendor": "opencode"},
                {"key": "op-bad", "runtime": "opencode", "model": "zen/missing",
                 "vendor": "opencode"},
                {"key": "sd", "model": "", "vendor": ""},
            ], ["op-good", "op-bad", "sd"])
            self._write_runtimes(env, self._snapshot(["zen/listed"]), 120)
            calls = []

            def run_fn(argv, **_kwargs):
                calls.append(list(argv))
                return _ok(argv)

            code, stdout, stderr = self._resolve(root, env, run_fn)
            self.assertEqual(code, 0)
            result = json.loads(stdout)
            self.assertEqual([row["key"] for row in result], ["op-good"], stderr)
            self.assertEqual(result[0]["route"], "subprocess")
            self.assertIn("skipping reviewer op-bad: route bad_model", stderr)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], "/fake/opencode")
            self.assertIn("models", calls[0])

    def test_probe_quota_probes_only_dispatchable_routes(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            self._write_config(env["XDG_CONFIG_HOME"], [
                {"key": "op-good", "runtime": "opencode", "model": "zen/listed",
                 "vendor": "opencode"},
                {"key": "op-bad", "runtime": "opencode", "model": "zen/missing",
                 "vendor": "opencode"},
                {"key": "cx", "runtime": "codex", "model": "gpt-x", "vendor": "openai"},
            ], ["op-good", "op-bad", "cx"])
            self._write_runtimes(env, self._snapshot(["zen/listed"]), 30)
            probed = []

            def runner(spec, _prompt, _seams):
                probed.append(spec.model)
                return RunnerResult(0, "", {"status": "ok"}, None, False, [], "")

            with mock.patch.dict(os.environ, env, clear=True), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = main(["probe-quota", "--cwd", root,
                             "--quota-path", os.path.join(root, "quota.json")],
                            env_fn=lambda: dict(env), which_fn=lambda _name: None,
                            run_fn=_ok, runner_fn=runner)
            self.assertEqual(code, 0)
            self.assertEqual(probed, ["zen/listed"])

    def _probe_no_save(self, root, env, run_fn, which_fn):
        def runner(_spec, _prompt, _seams):
            return RunnerResult(0, "", {"status": "ok"}, None, False, [], "")

        with mock.patch.dict(os.environ, env, clear=True), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return main(["probe-quota", "--cwd", root, "--no-save-runtimes",
                         "--quota-path", os.path.join(root, "quota.json")],
                        env_fn=lambda: dict(env), which_fn=which_fn, run_fn=run_fn,
                        runner_fn=runner)

    def test_no_save_runtimes_builds_and_refreshes_without_writing(self):
        def run_fn(argv, **_kwargs):
            if os.path.basename(argv[0]) == "opencode" and "models" in argv:
                return subprocess.CompletedProcess(argv, 0, stdout="zen/new\n", stderr="")
            return _ok(argv)

        def which_fn(name):
            return f"/fake/{name}" if name == "opencode" else None

        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            self._write_config(env["XDG_CONFIG_HOME"], [
                {"key": "op", "runtime": "opencode", "model": "zen/new", "vendor": "opencode"},
            ], ["op"])
            # Cold cache: the build happens in memory only.
            self.assertEqual(self._probe_no_save(root, env, run_fn, which_fn), 0)
            self.assertFalse(os.path.exists(routing.cache_runtimes_path(env)))
            # Stale cache that misses the model: the targeted refresh never writes back.
            path = self._write_runtimes(env, self._snapshot(["zen/old"]), 120)
            before = (_read(path), os.stat(path).st_mtime)
            routing._REFRESHED.clear()
            self.assertEqual(self._probe_no_save(root, env, run_fn, which_fn), 0)
            self.assertEqual((_read(path), os.stat(path).st_mtime), before)

    def test_bad_model_never_spawns(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            self._write_config(env["XDG_CONFIG_HOME"], [
                {"key": "op-bad", "runtime": "opencode", "model": "zen/missing",
                 "vendor": "opencode"},
            ], ["op-bad"])
            self._write_runtimes(env, self._snapshot(["zen/listed"]), 120)
            seen = []

            def record(argv, **_kwargs):
                seen.append(list(argv))
                return _ok(argv)

            code, stdout, _stderr = self._resolve(root, env, record, popen_fn=record)
            self.assertEqual(code, 0)
            result = json.loads(stdout)
            self.assertEqual(result[0]["key"], "session-default")
            self.assertFalse(any("zen/missing" in str(argv) for argv in seen))

    def test_session_default_route(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            code, stdout, _stderr = self._resolve(root, env, _ok)
            self.assertEqual(code, 0)
            result = json.loads(stdout)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["key"], "session-default")
            self.assertEqual(result[0]["route"], "native")

    def test_saved_session_default_round_trips_into_dispatch_reviewer(self):
        """V2: a saved session default resolves native and dispatch-reviewer spawns nothing."""
        from ai_kit_spec import detection
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            self._write_config(env["XDG_CONFIG_HOME"], [{"key": "sd", "model": ""}], ["sd"])
            code, stdout, stderr = self._resolve(root, env, _ok)
            self.assertEqual(code, 0, stderr)
            result = json.loads(stdout)
            self.assertEqual([(r["key"], r["model"], r["route"]) for r in result],
                             [("sd", "", "native")])
            reviewers = os.path.join(root, "reviewers.json")
            prompt = os.path.join(root, "prompt.txt")
            with open(reviewers, "w", encoding="utf-8") as handle:
                handle.write(stdout)
            with open(prompt, "w", encoding="utf-8") as handle:
                handle.write("review this")

            def never(*_args):
                raise AssertionError("a native session default must not spawn")

            skip = detection.CodegraphProbe(False, False, None, "skip")
            err = io.StringIO()
            with mock.patch.object(detection, "probe_codegraph", return_value=skip), \
                    redirect_stdout(io.StringIO()), redirect_stderr(err):
                code = main(["dispatch-reviewer", "--reviewers-json", reviewers, "--index", "0",
                             "--prompt-file", prompt, "--timeout-tiers", "600"],
                            runner_tiers_fn=never, custom_fn=never)
            self.assertEqual(code, 1)
            self.assertIn("routes native", err.getvalue())

    def test_cache_missing_builds_once_without_targeted_refresh(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            self._write_config(env["XDG_CONFIG_HOME"], [
                {"key": "op-good", "runtime": "opencode", "model": "zen/listed",
                 "vendor": "opencode"},
            ], ["op-good"])
            calls = []

            def run_fn(argv, **_kwargs):
                calls.append(list(argv))
                if os.path.basename(argv[0]) == "opencode" and "models" in argv:
                    return subprocess.CompletedProcess(argv, 0, stdout="zen/listed\n", stderr="")
                return _ok(argv)

            def which_fn(name):
                return f"/fake/{name}" if name == "opencode" else None

            code, stdout, _stderr = self._resolve(root, env, run_fn, which_fn=which_fn)
            self.assertEqual(code, 0)
            result = json.loads(stdout)
            self.assertEqual(result[0]["route"], "subprocess")
            listings = [argv for argv in calls if argv[1:] == ["models"]]
            self.assertEqual(len(listings), 1)
            self.assertTrue(os.path.exists(routing.cache_runtimes_path(env)))

    def test_listing_timeout_is_unverified(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            self._write_config(env["XDG_CONFIG_HOME"], [
                {"key": "op-good", "runtime": "opencode", "model": "zen/listed",
                 "vendor": "opencode"},
            ], ["op-good"])

            def which_fn(name):
                return "/fake/opencode" if name == "opencode" else None

            def run_fn(argv, **_kwargs):
                raise subprocess.TimeoutExpired(argv, 15)

            code, stdout, stderr = self._resolve(root, env, run_fn, which_fn=which_fn)
            self.assertEqual(code, 0)
            result = json.loads(stdout)
            self.assertEqual(result[0]["key"], "op-good")
            self.assertEqual(result[0]["route"], "unverified")
            self.assertIn("dispatching reviewer op-good unverified", stderr)
            self.assertNotIn("bad_model", stderr)


def _entry(runtime, model, command=None):
    entry = {"key": "k", "runtime": runtime, "model": model}
    if command is not None:
        entry["command"] = command
        entry.pop("runtime")
    return entry


def _inventory(installed, models):
    return routing.Inventory(installed=frozenset(installed), models=models)


class TestRouting(unittest.TestCase):
    def _route(self, entry, host, mode, inventory):
        return routing.route(routing.RouteInput.of(entry), host, mode, inventory)

    def test_table(self):
        listed = _inventory(["opencode", "codex", "claude"], {
            "opencode": ("zen/x",), "codex": ("gpt-x",),
            "claude": ("opus", "claude-opus-5-5"),
        })
        cases = [
            (_entry(None, ""), "opencode", "review", listed, "native"),
            (_entry("claude", "opus"), "claude", "review", listed, "native"),
            (_entry("claude", "claude-opus-5-5"), "claude", "review", listed, "subprocess"),
            (_entry("claude", "claude-opus-5-5"), "claude", "exec", listed, "review_only"),
            (_entry("opencode", "zen/x"), "opencode", "review", listed, "subprocess"),
            (_entry("claude", "opus"), "codex", "review", listed, "subprocess"),
            (_entry("claude", "opus"), "codex", "exec", listed, "review_only"),
            (_entry("codex", "gpt-x"), "unknown", "review", listed, "subprocess"),
            (_entry("grok", "grok-4"), "opencode", "review", _inventory(["grok"], {}),
             "no_inventory"),
            (_entry("codex", "gpt-x"), "opencode", "review",
             _inventory(["codex"], {"codex": None}), "unverified"),
            (_entry("opencode", "zen/x"), "claude", "review",
             _inventory(["opencode"], {"opencode": ()}), "bad_model"),
            (_entry("gemini", "g"), "claude", "review", listed, "unknown_runtime"),
            (_entry("gemini", ""), "claude", "review", listed, "unknown_runtime"),
            ({"key": "k", "runtime": ["codex"], "model": ""}, "claude", "review",
             listed, "unknown_runtime"),
            (_entry("codex", ""), "claude", "review", listed, "no_model"),
            (_entry("codex", "gpt-x"), "claude", "review", _inventory([], {}), "not_installed"),
            ({"key": "k", "command": "mycli {model}", "model": "m"}, "claude", "review",
             listed, "custom"),
            ({"key": "k", "command": "mycli {model}", "model": "m"}, "claude", "exec",
             listed, "review_only"),
            ({"key": "k", "runtime": ["codex"], "model": "gpt-x"}, "claude", "review",
             listed, "unknown_runtime"),
        ]
        for entry, host, mode, inventory, expected in cases:
            with self.subTest(entry=entry, host=host, mode=mode):
                self.assertEqual(self._route(entry, host, mode, inventory), expected)

    def test_merged_custom_entry_routes_custom(self):
        from ai_kit_spec.config_io import cfg_combine

        with tempfile.TemporaryDirectory() as root:
            xdg = os.path.join(root, "xdg")
            os.makedirs(os.path.join(xdg, "ai-kit"))
            factory = "codex exec --sandbox read-only --skip-git-repo-check -m {model}"
            path = os.path.join(xdg, "ai-kit", "review-spec.toml")
            with open(path, "w", encoding="utf-8") as stream:
                stream.write('[[reviewers]]\nkey="k"\ncli="codex"\nmodel="gpt-5.6-sol"\n'
                             f"command={json.dumps(factory)}\n")
            custom = "mycli --fast {model}"
            merged = cfg_combine({"reviewers": [{"key": "k", "command": custom}]},
                                 {"HOME": os.path.join(root, "home"), "XDG_CONFIG_HOME": xdg},
                                 warn_fn=lambda _msg: None, local_path="local.toml")
            self.assertEqual(
                self._route(merged["reviewers"][0], "claude", "review",
                            _inventory(["codex"], {"codex": ()})),
                "custom")

    def test_suffixes_are_stripped_before_membership(self):
        inventory = _inventory(["cursor", "opencode", "pi"], {
            "cursor": ("gpt-6",), "opencode": ("zen/x",), "pi": ("p/m",),
        })
        cases = [
            (_entry("cursor", "gpt-6[effort=high]"), "subprocess"),
            (_entry("opencode", "zen/x#high"), "subprocess"),
            (_entry("pi", "p/m:high"), "subprocess"),
        ]
        for entry, expected in cases:
            with self.subTest(model=entry["model"]):
                self.assertEqual(self._route(entry, "claude", "review", inventory), expected)


class TestClaudeInventory(unittest.TestCase):
    def test_no_recorded_ids_uses_aliases_and_dated_fallback(self):
        inventory = routing.inventory_from_snapshot({
            "schema_version": RUNTIMES_SCHEMA_VERSION,
            "clis": {"claude": {"installed": True, "aliases": list(CLAUDE_MODEL_ALIASES)}},
        })
        self.assertEqual(
            inventory.models["claude"],
            tuple(CLAUDE_MODEL_ALIASES) + tuple(CLAUDE_FALLBACK_MODEL_IDS))

    def test_recorded_ids_keep_first_seen_order(self):
        inventory = routing.inventory_from_snapshot({
            "schema_version": RUNTIMES_SCHEMA_VERSION,
            "clis": {"claude": {"installed": True, "models": ["b", "a", "b"],
                                "aliases": list(CLAUDE_MODEL_ALIASES)}},
        })
        self.assertEqual(
            inventory.models["claude"], (*tuple(CLAUDE_MODEL_ALIASES), "b", "a"))


class TestTargetedRefresh(unittest.TestCase):
    def setUp(self):
        routing._REFRESHED.clear()

    def _env(self, root):
        env = _scratch_env(root)
        # The opencode lister makes its private dir from os.environ, not the routed env.
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        return env

    def _context(self, env, which_fn, run_fn):
        seams = routing.RuntimesSeams(which_fn=which_fn, run_fn=run_fn, popen_fn=_ok,
                                       urlopen_fn=lambda *_a, **_k: None)
        return routing.RouteContext(host="claude", mode="review", env=env, seams=seams)

    def _age(self, env, seconds):
        path = routing.cache_runtimes_path(env)
        stamp = time.time() - seconds
        os.utime(path, (stamp, stamp))

    def test_second_call_does_not_relist(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            calls = []

            def run_fn(argv, **_kwargs):
                calls.append(list(argv))
                raise subprocess.TimeoutExpired(argv, 15)

            cache_write_json(
                routing.cache_runtimes_path(env),
                _snapshot({"opencode": {"installed": True, "path": "/fake/opencode"}}))
            self._age(env, 120)
            entries = [{"key": "k", "runtime": "opencode", "model": "zen/x"}]
            ctx = self._context(env, lambda _name: "/fake/opencode", run_fn)
            routing.route_all(entries, ctx)
            routing.route_all(entries, ctx)
            self.assertEqual(len(calls), 1)

    def test_refresh_keeps_the_cached_row_fields(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)

            def run_fn(argv, **_kwargs):
                if os.path.basename(argv[0]) == "codex":
                    stdout = '{"models": [{"slug": "gpt-new", "visibility": "list"}]}'
                else:
                    stdout = "zen/new\n"
                return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")

            image = {"image_input": ["zen/old"], "image_input_source": "probe",
                     "image_input_probe": {"zen/old": True}}
            path = routing.cache_runtimes_path(env)
            cache_write_json(path, _snapshot({
                "codex": {"installed": True, "path": "/fake/codex", "models": ["gpt-old"],
                          "reasoning_modes": {"gpt-old": ["high"]}},
                "opencode": {"installed": True, "path": "/fake/opencode",
                             "models": ["zen/old"], **image},
            }))
            self._age(env, 120)
            entries = [{"key": "c", "runtime": "codex", "model": "gpt-new"},
                       {"key": "o", "runtime": "opencode", "model": "zen/new"}]
            ctx = self._context(env, lambda name: f"/fake/{name}", run_fn)
            routes = routing.route_all(entries, ctx)
            self.assertEqual(routes, {"c": "subprocess", "o": "subprocess"})
            written = cache_read_json(path)
            assert written is not None
            self.assertEqual(written["clis"]["codex"]["reasoning_modes"], {"gpt-old": ["high"]})
            for field, value in image.items():
                self.assertEqual(written["clis"]["opencode"][field], value)

    def test_young_cache_is_not_refreshed(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            calls = []

            def run_fn(argv, **_kwargs):
                calls.append(list(argv))
                return _ok(argv)

            cache_write_json(
                routing.cache_runtimes_path(env),
                _snapshot({"opencode": {"installed": True, "path": "/fake/opencode"}}))
            entries = [{"key": "k", "runtime": "opencode", "model": "zen/x"}]
            routes = routing.route_all(entries, self._context(env, lambda _n: "/fake/opencode",
                                                              run_fn))
            self.assertEqual(routes["k"], "unverified")
            self.assertEqual(calls, [])

    def test_not_installed_resolves_binary_only_until_found(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            calls = []
            found = {"now": False}

            def which_fn(name):
                return "/fake/codex" if name == "codex" and found["now"] else None

            def run_fn(argv, **_kwargs):
                calls.append(list(argv))
                return subprocess.CompletedProcess(argv, 0, stdout='{"models": []}', stderr="")

            others = {"pi": {"installed": False}}
            path = routing.cache_runtimes_path(env)
            cache_write_json(path, _snapshot({"codex": {"installed": False}, **others}))
            before = cache_read_json(path)
            self._age(env, 120)
            entries = [{"key": "k", "runtime": "codex", "model": "gpt-x"}]
            ctx = self._context(env, which_fn, run_fn)
            routes = routing.route_all(entries, ctx)
            self.assertEqual(routes["k"], "not_installed")
            self.assertEqual(calls, [])
            written = cache_read_json(path)
            assert written is not None
            self.assertEqual(written["clis"]["pi"], others["pi"])

            routing._REFRESHED.clear()
            found["now"] = True
            self._age(env, 120)
            routes = routing.route_all(entries, ctx)
            self.assertEqual(len(calls), 1)
            self.assertEqual(routes["k"], "bad_model")
            written = cache_read_json(path)
            assert before is not None and written is not None
            self.assertEqual(written["clis"]["pi"], before["clis"]["pi"])

    def test_failed_refresh_stays_unverified_and_empty_listing_becomes_bad_model(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)

            def run_fn(argv, **_kwargs):
                if os.path.basename(argv[0]) == "codex":
                    raise subprocess.TimeoutExpired(argv, 15)
                return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

            path = routing.cache_runtimes_path(env)
            cache_write_json(path, _snapshot({
                "codex": {"installed": True, "path": "/fake/codex"},
                "opencode": {"installed": True, "path": "/fake/opencode"},
            }))
            self._age(env, 120)
            entries = [
                {"key": "cx", "runtime": "codex", "model": "gpt-x"},
                {"key": "op", "runtime": "opencode", "model": "zen/x"},
            ]
            routes = routing.route_all(entries, self._context(env, lambda n: f"/fake/{n}", run_fn))
            self.assertEqual(routes["cx"], "unverified")
            self.assertEqual(routes["op"], "bad_model")
            written = cache_read_json(path)
            assert written is not None
            self.assertNotIn("models", written["clis"]["codex"])
            self.assertEqual(written["clis"]["opencode"]["models"], [])

    def test_claude_never_relisted(self):
        with tempfile.TemporaryDirectory() as root:
            env = self._env(root)
            catalog = {"_meta": {"anthropic_model_ids": ["claude-opus-5-5"]}}
            cache_write_json(routing.cache_catalog_path(env), catalog)
            fields = claude_runtime_fields(catalog)
            path = routing.cache_runtimes_path(env)
            cache_write_json(path, _snapshot(
                {"claude": {"installed": True, "path": "/fake/claude", **fields}}))
            self._age(env, 120)
            seen = {"run": [], "which": []}

            def run_fn(argv, **_kwargs):
                seen["run"].append(list(argv))
                return _ok(argv)

            def which_fn(name):
                seen["which"].append(name)
                return f"/fake/{name}"

            entries = [{"key": "k", "runtime": "claude", "model": "claude-unknown-9"}]
            ctx = self._context(env, which_fn, run_fn)
            routes = routing.route_all(entries, ctx)
            self.assertEqual(routes["k"], "bad_model")
            self.assertEqual(seen["run"], [])
            self.assertEqual(seen["which"], [])
            stored = cache_read_json(path)
            assert stored is not None
            self.assertEqual(stored["clis"]["claude"]["models"], fields["models"])

            routing._REFRESHED.clear()
            cache_write_json(path, _snapshot({"claude": {"installed": False}}))
            self._age(env, 120)
            entries = [{"key": "k", "runtime": "claude", "model": "claude-opus-5-5"}]
            routes = routing.route_all(entries, ctx)
            self.assertEqual(routes["k"], "subprocess")
            self.assertEqual(seen["run"], [])
            self.assertEqual(seen["which"], ["claude"])
            expected = claude_runtime_fields(catalog)["models"]
            stored = cache_read_json(path)
            assert stored is not None
            self.assertEqual(stored["clis"]["claude"]["models"], expected)
            self.assertIn("claude-opus-5-5", expected)
            self.assertNotEqual(expected, list(CLAUDE_FALLBACK_MODEL_IDS))


class TestUnverifiedNote(unittest.TestCase):
    def setUp(self):
        routing._REFRESHED.clear()

    def test_unverified_line_once(self):
        with tempfile.TemporaryDirectory() as root:
            home = os.path.join(root, "home")
            xdg = os.path.join(root, "xdg")
            cache = os.path.join(root, "cache")
            os.makedirs(os.path.join(xdg, "ai-kit"))
            os.makedirs(cache)
            env = {"HOME": home, "XDG_CONFIG_HOME": xdg, "XDG_CACHE_HOME": cache}
            cfg_write_toml(
                os.path.join(xdg, "ai-kit", "review-spec.toml"),
                {"policy": {"mode": "single", "ladder": ["cx"]},
                 "reviewers": [{"key": "cx", "runtime": "codex", "model": "gpt-x",
                                "vendor": "openai"}]})
            path = routing.cache_runtimes_path(env)
            cache_write_json(path, {"schema_version": RUNTIMES_SCHEMA_VERSION,
                                    "clis": {"codex": {"installed": True,
                                                       "path": "/fake/codex"}}})
            stamp = time.time() - 120
            os.utime(path, (stamp, stamp))

            def run_fn(argv, **_kwargs):
                raise subprocess.TimeoutExpired(argv, 15)

            out, err = io.StringIO(), io.StringIO()
            with mock.patch.dict(os.environ, env, clear=True), \
                    redirect_stdout(out), redirect_stderr(err):
                code = main(["resolve-reviewers", "--cwd", root, "--cross-ai",
                             "--quota-path", os.path.join(root, "quota.json")],
                            run_fn=run_fn, which_fn=lambda name: "/fake/codex",
                            env_fn=lambda: dict(env))
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue())[0]["route"], "unverified")
            self.assertEqual(err.getvalue().count("dispatching reviewer cx unverified"), 1)


class TestRouteNeverStored(unittest.TestCase):
    def test_render_rejects_route(self):
        err = io.StringIO()
        with redirect_stderr(err):
            rendered = cfg_render_toml({
                "reviewers": [{"key": "k", "runtime": "codex", "model": "gpt-x",
                               "route": "native"}]})
        self.assertNotIn("route", rendered)
        self.assertIn("'route' is decided per run and is never stored", err.getvalue())

    def test_load_drops_route_with_a_note(self):
        with tempfile.TemporaryDirectory() as root:
            xdg = os.path.join(root, "xdg")
            os.makedirs(os.path.join(xdg, "ai-kit"))
            path = os.path.join(xdg, "ai-kit", "review-spec.toml")
            with open(path, "w", encoding="utf-8") as stream:
                stream.write('[[reviewers]]\nkey="k"\nruntime="codex"\nmodel="gpt-x"\n'
                             'route="native"\n')
            notes = []
            resolved = cfg_resolve(root, {"HOME": os.path.join(root, "home"),
                                          "XDG_CONFIG_HOME": xdg}, warn_fn=notes.append)
            self.assertNotIn("route", resolved["reviewers"][0])
            self.assertTrue(any("route=native ignored" in note for note in notes))

    def test_resolve_output_has_route_but_the_file_never_gains_it(self):
        routing._REFRESHED.clear()
        with tempfile.TemporaryDirectory() as root:
            xdg = os.path.join(root, "xdg")
            os.makedirs(os.path.join(xdg, "ai-kit"))
            os.makedirs(os.path.join(root, "cache"))
            env = {"HOME": os.path.join(root, "home"), "XDG_CONFIG_HOME": xdg,
                   "XDG_CACHE_HOME": os.path.join(root, "cache")}
            path = os.path.join(xdg, "ai-kit", "review-spec.toml")
            cfg_write_toml(path, {"policy": {"mode": "single", "ladder": ["k"]},
                                  "reviewers": [{"key": "k", "model": "", "vendor": ""}]})
            with open(path, "rb") as stream:
                before = stream.read()
            out = io.StringIO()
            with mock.patch.dict(os.environ, env, clear=True), \
                    redirect_stdout(out), redirect_stderr(io.StringIO()):
                code = main(["resolve-reviewers", "--cwd", root, "--cross-ai",
                             "--quota-path", os.path.join(root, "quota.json")],
                            run_fn=_ok, which_fn=lambda _name: None, env_fn=lambda: dict(env))
            self.assertEqual(code, 0)
            self.assertIn("route", json.loads(out.getvalue())[0])
            with open(path, "rb") as stream:
                self.assertEqual(stream.read(), before)


class TestUnroutableQuota(unittest.TestCase):
    def test_stale_auth_row_for_a_native_reviewer_is_removed(self):
        quota = {"native": {"available": False, "reason": "auth"}, "bad": {"available": True}}
        result = routing.unroutable_quota(quota, {"native": "native", "bad": "bad_model"})
        self.assertNotIn("native", result)
        self.assertEqual(result["bad"], {"available": False, "reason": "bad_model"})


class TestOpencodePrivateDirUsesTheGivenEnv(unittest.TestCase):
    """The opencode lister's private cwd lives under the env routing was given, never under
    os.environ's cache: a test with a scratch env must not touch the real cache dir."""

    def setUp(self):
        routing._REFRESHED.clear()
        self.addCleanup(routing._REFRESHED.clear)

    def test_build_and_refresh_put_the_private_cwd_under_the_given_env(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as decoy:
            env = _scratch_env(root)
            cwds = []

            def fake_run(argv, **kwargs):
                cwds.append(kwargs["cwd"])
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")

            seams = routing.RuntimesSeams(
                lambda name: "/fake/opencode" if name == "opencode" else None, fake_run,
                mock.Mock(side_effect=OSError), mock.Mock(side_effect=OSError))
            with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": decoy}):
                routing.load_runtimes_snapshot(env, seams, force=True)
                ctx = routing.RouteContext("unknown", "review", env, seams)
                routing._refresh_runtime({"clis": {}}, "opencode", ctx)
            base = os.path.join(env["XDG_CACHE_HOME"], "ai-kit", "spec")
            self.assertTrue(cwds)
            self.assertEqual({os.path.dirname(cwd) for cwd in cwds}, {base})
            self.assertEqual(os.listdir(decoy), [])


if __name__ == "__main__":
    unittest.main()
