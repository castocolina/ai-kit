"""R5 trust lifecycle + R13 loud-config-error tests for the project-local review-spec.toml
trust gate (Plan 16.1-08, HARD-03/HARD-05). Every test uses temp HOME/XDG_CONFIG_HOME --
never the real user config."""
import io
import json
import os
import shlex
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute-gsd"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute-superpowers"))

from ai_kit_spec import cli, config_io, trust
from ai_kit_spec.runner_dispatch import RunnerResult


def _local_spec(argv_cmd: str) -> bytes:
    # TOML literal strings ('...') need no escaping, so shlex.quote's single-quoted form is
    # valid TOML as-is -- the template is exactly what split_command_template will tokenize.
    return (
        'strategy = "local-only"\n'
        "[[reviewers]]\n"
        'key = "local"\n'
        'model = "m"\n'
        'vendor = "v"\n'
        'cli = "codex"\n'
        f"command = {shlex.quote(argv_cmd)}\n"
        "[policy]\n"
        'mode = "single"\n'
        'ladder = ["local"]\n'
    ).encode()


# probe-quota routes every reviewer first: no real binary lookup, listing or runtimes build.
NO_RUNTIMES = {"which_fn": lambda _name: None, "run_fn": lambda *_a, **_k: None}


def _probe_ok():
    return RunnerResult(0, "", {"status": "ok"}, None, False, ["node", "runner"], "")


class TrustEnvTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cwd = tempfile.mkdtemp(dir=self._tmp.name)
        self.home = tempfile.mkdtemp(dir=self._tmp.name)
        self.xdg = tempfile.mkdtemp(dir=self._tmp.name)
        self.cache = tempfile.mkdtemp(dir=self._tmp.name)
        self.env_patcher = mock.patch.dict(
            os.environ, {"HOME": self.home, "XDG_CONFIG_HOME": self.xdg,
                         "XDG_CACHE_HOME": self.cache})
        self.env_patcher.start()
        self.addCleanup(self.env_patcher.stop)
        self.store = config_io.cfg_trust_store_dir(dict(os.environ))

    def write_local(self, raw: bytes) -> str:
        local_dir = os.path.join(self.cwd, ".aikit")
        os.makedirs(local_dir, exist_ok=True)
        path = os.path.join(local_dir, "review-spec.toml")
        with open(path, "wb") as f:
            f.write(raw)
        return path


class TestTrustLifecycle(TrustEnvTestCase):
    PROBE_CMD = f"{sys.executable} -c pass"

    def probe_quota(self):
        calls = []

        def rec(spec, prompt, seams):
            del prompt, seams
            calls.append(getattr(spec, "argv", None) or [spec.runtime, spec.model])
            return _probe_ok()

        quota_path = os.path.join(self.cwd, "quota.json")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["probe-quota", "--cwd", self.cwd, "--quota-path", quota_path],
                            runner_fn=rec, custom_fn=rec, **NO_RUNTIMES)
        return code, calls, out.getvalue(), err.getvalue()

    def test_untrusted_local_probes_nothing_and_warns(self):
        self.write_local(_local_spec(self.PROBE_CMD))
        code, calls, _, err = self.probe_quota()
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertIn("trust-local", err)
        self.assertIn(config_io.cfg_local_path(self.cwd), err)

    def test_show_prints_argv_and_writes_nothing(self):
        path = self.write_local(_local_spec(self.PROBE_CMD))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["trust-local", "--cwd", self.cwd, "--show"])
        self.assertEqual(code, 0)
        line = json.loads(out.getvalue().strip().splitlines()[0])
        self.assertEqual(line["key"], "local")
        self.assertEqual(line["argv"], [sys.executable, "-c", "pass"])
        self.assertFalse(line["trusted"])
        self.assertEqual(line["path"], os.path.realpath(path))
        self.assertFalse(os.path.exists(self.store))

    def show_lines(self):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["trust-local", "--cwd", self.cwd, "--show"]), 0)
        return [json.loads(x) for x in out.getvalue().strip().splitlines()]

    def test_show_lists_runtime_and_custom_entries(self):
        factory = "codex exec --sandbox read-only --skip-git-repo-check -m {model}"
        custom = "mycli --fast {model}"
        text = ('strategy = "local-only"\n'
                '[[reviewers]]\nkey = "codex"\ncli = "codex"\n'
                'model = "gpt-5.6-sol"\n'
                f"command = '{factory}'\n"
                '[[reviewers]]\nkey = "custom"\ncli = "mycli"\n'
                'model = "custom-model"\n'
                f"command = '{custom}'\n")
        self.write_local(text.encode())
        lines = self.show_lines()
        self.assertEqual([line["key"] for line in lines], ["codex", "custom"])
        # a factory-shaped legacy command normalizes to a runtime: the runner's argv
        self.assertEqual(lines[0]["argv"][2:4], ["--prefer", "codex"])
        self.assertIn("--model-codex", lines[0]["argv"])
        self.assertNotIn("<prompt>", lines[0]["argv"])
        # an unknown cli keeps its own command; this template names no {prompt}
        self.assertEqual(lines[1]["argv"], ["mycli", "--fast", "custom-model"])

    def test_show_renders_a_pair_with_its_top_level_knobs(self):
        # B-WR-06: the consent argv carries the same effort flag dispatch passes.
        self.write_local(b'strategy = "local-only"\n[[reviewers]]\nkey = "c"\n'
                         b'runtime = "codex"\nmodel = "gpt"\neffort = "high"\n')
        argv = self.show_lines()[0]["argv"]
        self.assertEqual(argv[argv.index("--codex-effort") + 1], "high")

    def test_show_renders_placeholder_hidden_flag_and_executable(self):
        # A-CR-01: a placeholder must never hide what runs -- the consent display shows the
        # rendered argv, with only the prompt kept symbolic.
        self.write_local(
            b'strategy = "local-only"\n[[reviewers]]\nkey = "x"\ncli = "codex"\n'
            b'model = "gpt-5"\ntool = "./evil-tool"\n'
            b'flag = "--dangerously-bypass-approvals-and-sandbox"\n'
            b'command = "{tool} exec {flag} -m {model} {prompt}"\n')
        line = self.show_lines()[0]
        self.assertEqual(line["argv"], ["./evil-tool", "exec",
                                        "--dangerously-bypass-approvals-and-sandbox",
                                        "-m", "gpt-5", "<prompt>"])

    def test_show_renders_local_fields_merged_into_a_global_command(self):
        # global-merge: a local entry with no command of its own can still fill the global
        # command's placeholders, so --show must render the merged entry.
        cfg_dir = os.path.join(self.xdg, "ai-kit")
        os.makedirs(cfg_dir, exist_ok=True)
        with open(os.path.join(cfg_dir, "review-spec.toml"), "w", encoding="utf-8") as f:
            f.write('[[reviewers]]\nkey = "g"\nmodel = "m"\nvendor = "v"\ncli = "codex"\n'
                    'flag = "--safe"\ncommand = "codex exec {flag} -m {model}"\n')
        self.write_local(b'[[reviewers]]\nkey = "g"\nflag = "--yolo"\n')
        line = self.show_lines()[0]
        # a non-factory command stays custom, so the merged local flag is visible
        self.assertEqual(line["key"], "g")
        self.assertEqual(line["argv"], ["codex", "exec", "--yolo", "-m", "m"])
        self.assertFalse(line["trusted"])
        self.assertEqual(line["path"],
                         os.path.realpath(config_io.cfg_local_path(self.cwd)))

    def test_show_reports_shell_syntax_refusal_not_an_argv(self):
        self.write_local(_local_spec("x; rm -rf ~"))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["trust-local", "--cwd", self.cwd, "--show"])
        self.assertEqual(code, 0)
        line = json.loads(out.getvalue().strip().splitlines()[0])
        self.assertEqual(line["key"], "local")
        self.assertNotIn("argv", line)
        self.assertIn("shell syntax", line["error"])

    def test_trust_local_records_and_probe_then_runs(self):
        path = self.write_local(_local_spec(self.PROBE_CMD))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["trust-local", "--cwd", self.cwd])
        self.assertEqual(code, 0)
        self.assertIn("trusted", out.getvalue())
        self.assertIn("sha256=", out.getvalue())
        records = os.listdir(self.store)
        self.assertEqual(len(records), 1)
        with open(os.path.join(self.store, records[0]), encoding="utf-8") as f:
            record = json.load(f)
        self.assertEqual(record["path"], os.path.realpath(path))
        self.assertEqual(record["sha256"], trust.content_sha256(_local_spec(self.PROBE_CMD)))
        code, calls, _, _ = self.probe_quota()
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], [sys.executable, "-c", "pass"])

    def test_edit_after_trust_reblocks(self):
        path = self.write_local(_local_spec(self.PROBE_CMD))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["trust-local", "--cwd", self.cwd]), 0)
        with open(path, "ab") as f:
            f.write(b"# edit\n")
        _, calls, _, err = self.probe_quota()
        self.assertEqual(calls, [])
        self.assertIn("trust-local", err)

    def test_crlf_only_edit_needs_new_trust(self):
        path = self.write_local(_local_spec(self.PROBE_CMD))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["trust-local", "--cwd", self.cwd]), 0)
        with open(path, "rb") as f:
            raw = f.read()
        with open(path, "wb") as f:
            f.write(raw.replace(b"\n", b"\r\n"))
        _, calls, _, _ = self.probe_quota()
        self.assertEqual(calls, [])

    def test_revoke_removes_trust(self):
        self.write_local(_local_spec(self.PROBE_CMD))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["trust-local", "--cwd", self.cwd]), 0)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["trust-local", "--cwd", self.cwd, "--revoke"])
        self.assertEqual(code, 0)
        self.assertIn("revoked 1 trust record(s)", out.getvalue())
        _, calls, _, _ = self.probe_quota()
        self.assertEqual(calls, [])

    def test_revoke_works_after_the_file_is_deleted(self):
        # A-IN-07: records of a deleted/moved config must stay removable through the CLI.
        path = self.write_local(_local_spec(self.PROBE_CMD))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["trust-local", "--cwd", self.cwd]), 0)
        os.unlink(path)
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["trust-local", "--cwd", self.cwd, "--revoke"]), 0)
        self.assertIn("revoked 1 trust record(s)", out.getvalue())
        self.assertEqual(os.listdir(self.store), [])

    def test_non_object_trust_record_reads_untrusted_and_revoke_skips_it(self):
        # A-IN-01: a trust record holding a JSON list/string must not crash the gate.
        path = self.write_local(_local_spec(self.PROBE_CMD))
        with open(path, "rb") as f:
            raw = f.read()
        real = os.path.realpath(path)
        os.makedirs(self.store, exist_ok=True)
        name = trust.trust_key(real, trust.content_sha256(raw)) + ".json"
        with open(os.path.join(self.store, name), "w", encoding="utf-8") as f:
            f.write("[1, 2]")
        self.assertFalse(trust.is_trusted(self.store, real, raw))
        self.assertEqual(trust.revoke_trust(self.store, real), 0)
        _, calls, _, err = self.probe_quota()
        self.assertEqual(calls, [])
        self.assertIn("trust-local", err)

    def test_surrogate_escaped_path_hashes_without_raising(self):
        self.assertEqual(len(trust.trust_key("/p/\udcff.toml", "0" * 64)), 64)

    def test_unreadable_local_config_exits_2(self):
        # A-IN-01: a directory where the file should be is a ConfigError (exit 2), not a raw
        # IsADirectoryError traceback.
        os.makedirs(config_io.cfg_local_path(self.cwd))
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = cli.main(["probe-quota", "--cwd", self.cwd, "--quota-path",
                             os.path.join(self.cwd, "q.json")], run_fn=lambda *a, **k: None)
        self.assertEqual(code, 2)
        self.assertIn("config error", err.getvalue())

    def test_render_toml_out_never_trusts_the_file_it_writes(self):
        # C-WR-05/D-09: the wizard's write path must leave the local file untrusted.
        json_path = os.path.join(self.cwd, "cfg.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"policy": {"mode": "single", "ladder": ["local"]},
                       "reviewers": [{"key": "local", "model": "m", "vendor": "v",
                                      "cli": "codex", "command": self.PROBE_CMD}]}, f)
        local = config_io.cfg_local_path(self.cwd)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["render-toml", "--json-config", json_path,
                                       "--out", local]), 0)
        self.assertTrue(os.path.exists(local))
        self.assertFalse(os.path.isdir(self.store) and os.listdir(self.store))
        _, calls, _, err = self.probe_quota()
        self.assertEqual(calls, [])
        self.assertIn("trust-local", err)

    def test_global_only_reviewer_needs_no_trust(self):
        calls = []

        def rec(spec, prompt, seams):
            del prompt, seams
            calls.append(getattr(spec, "argv", None) or [spec.runtime])
            return _probe_ok()

        cfg_dir = os.path.join(self.xdg, "ai-kit")
        os.makedirs(cfg_dir, exist_ok=True)
        with open(os.path.join(cfg_dir, "review-spec.toml"), "w", encoding="utf-8") as f:
            f.write('[[reviewers]]\nkey = "g"\nmodel = "m"\nvendor = "v"\ncli = "codex"\n'
                    f'command = "{self.PROBE_CMD}"\n[policy]\nladder = ["g"]\n')
        quota_path = os.path.join(self.cwd, "quota.json")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["probe-quota", "--cwd", self.cwd, "--quota-path", quota_path],
                            runner_fn=rec, custom_fn=rec, **NO_RUNTIMES)
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)

    def test_resolve_reviewers_never_lists_untrusted_local_key(self):
        self.write_local(_local_spec(self.PROBE_CMD))
        quota_path = os.path.join(self.cwd, "quota.json")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["resolve-reviewers", "--cwd", self.cwd,
                             "--quota-path", quota_path],
                            which_fn=lambda _name: None, run_fn=lambda *_a, **_k: None)
        self.assertEqual(code, 0)
        self.assertNotIn('"local"', out.getvalue())

    def test_concurrent_trust_records_stay_valid(self):
        path = self.write_local(_local_spec(self.PROBE_CMD))
        real = os.path.realpath(path)
        with open(path, "rb") as f:
            raw = f.read()
        errors = []

        def writer():
            try:
                trust.record_trust(self.store, real, raw)
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        with open(os.path.join(self.store, trust.trust_key(
                real, trust.content_sha256(raw)) + ".json"), encoding="utf-8") as f:
            record = json.load(f)
        self.assertEqual(record["path"], real)
        self.assertEqual(record["sha256"], trust.content_sha256(raw))
        self.assertTrue(trust.is_trusted(self.store, real, raw))



class TestLoudConfigErrors(TrustEnvTestCase):
    """R13 (Plan 16.1-08 Task 2): a malformed or non-UTF-8 review-spec.toml raises
    ConfigError and stops all three CLIs with exit 2 + the path on stderr; a missing file
    stays a silent default and a zero-byte file is valid TOML."""

    def test_missing_file_is_still_empty_dict(self):
        self.assertEqual(config_io.cfg_load_toml(os.path.join(self.cwd, "nope.toml")), {})

    def test_zero_byte_file_is_valid_toml(self):
        path = os.path.join(self.cwd, "empty.toml")
        open(path, "wb").close()
        self.assertEqual(config_io.cfg_load_toml(path), {})

    def test_malformed_toml_raises_with_path_and_parser_message(self):
        path = self.write_local(b"[[reviewers]\nkey=")
        with self.assertRaises(config_io.ConfigError) as ctx:
            config_io.cfg_load_toml(path)
        self.assertIn(path, str(ctx.exception))
        self.assertIn(path, ctx.exception.path)

    def test_non_utf8_bytes_raise_config_error_naming_path(self):
        path = self.write_local(b"\xff\xfe = 1")
        with self.assertRaises(config_io.ConfigError) as ctx:
            config_io.cfg_load_toml(path)
        self.assertEqual(ctx.exception.path, path)

    def test_missing_tomllib_on_existing_file_raises(self):
        path = self.write_local(b'[policy]\nmode = "single"\n')
        with mock.patch.object(config_io, "tomllib", None), \
                self.assertRaises(config_io.ConfigError) as ctx:
            config_io.cfg_load_toml(path)
        self.assertIn("Python 3.11+", ctx.exception.message)

    def test_two_readers_of_one_malformed_file_both_report(self):
        path = self.write_local(b"[[reviewers]\nkey=")
        errors = []

        def reader():
            try:
                config_io.cfg_load_toml(path)
            except config_io.ConfigError as exc:
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(errors), 2)
        for exc in errors:
            self.assertEqual(exc.path, path)

    def _write_global(self, raw: bytes) -> None:
        cfg_dir = os.path.join(self.xdg, "ai-kit")
        os.makedirs(cfg_dir, exist_ok=True)
        with open(os.path.join(cfg_dir, "review-spec.toml"), "wb") as f:
            f.write(raw)

    def test_review_spec_main_exits_2_on_malformed_local(self):
        self.write_local(b"[[reviewers]\n")
        quota_path = os.path.join(self.cwd, "quota.json")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["resolve-reviewers", "--cwd", self.cwd,
                             "--quota-path", quota_path],
                            which_fn=lambda _name: None, run_fn=lambda *_a, **_k: None)
        self.assertEqual(code, 2)
        self.assertIn(config_io.cfg_local_path(self.cwd), err.getvalue())

    def test_review_spec_main_exits_2_on_malformed_global(self):
        self._write_global(b"[[reviewers]\n")
        quota_path = os.path.join(self.cwd, "quota.json")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["resolve-reviewers", "--cwd", self.cwd,
                             "--quota-path", quota_path],
                            which_fn=lambda _name: None, run_fn=lambda *_a, **_k: None)
        self.assertEqual(code, 2)
        self.assertIn(os.path.join(self.xdg, "ai-kit", "review-spec.toml"), err.getvalue())

    def test_gsd_cli_exits_2_on_malformed_local(self):
        from ai_kit_spec_gsd import cli as gsd_cli
        self.write_local(b"[[reviewers]\n")
        err = io.StringIO()
        with redirect_stderr(err):
            code = gsd_cli.main(["resolve-dispatch", "--cwd", self.cwd,
                                 "--target-dir", self.cwd,
                                 "--quota-path", os.path.join(self.cwd, "quota.json")])
        self.assertEqual(code, 2)
        self.assertIn(config_io.cfg_local_path(self.cwd), err.getvalue())

    def test_superpowers_cli_exits_2_on_malformed_local(self):
        from ai_kit_spec_superpowers import cli as superpowers_cli
        self.write_local(b"[[reviewers]\n")
        task_path = os.path.join(self.cwd, "task-1-brief.md")
        with open(task_path, "w", encoding="utf-8") as f:
            f.write("### Task 1\n**Files:**\n- Create: `a.py`\n")
        err = io.StringIO()
        with redirect_stderr(err):
            code = superpowers_cli.main(["resolve-injection", "--cwd", self.cwd,
                                         "--task-file", task_path,
                                         "--quota-path", os.path.join(self.cwd, "q.json")])
        self.assertEqual(code, 2)
        self.assertIn(config_io.cfg_local_path(self.cwd), err.getvalue())

    def test_malformed_untrusted_local_still_exits_2(self):
        # Parsing happens BEFORE the trust check (D-08 interpretation) -- the malformed
        # file here was never trusted, and the loud error fires regardless.
        self.write_local(b"[[reviewers]\n")
        quota_path = os.path.join(self.cwd, "quota.json")
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = cli.main(["probe-quota", "--cwd", self.cwd, "--quota-path", quota_path])
        self.assertEqual(code, 2)
        self.assertIn(config_io.cfg_local_path(self.cwd), err.getvalue())


if __name__ == "__main__":
    unittest.main()
