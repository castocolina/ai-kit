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

from ai_kit_spec import cli, config_io, trust


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


class _FakeResult:
    returncode = 0
    stdout = ""
    stderr = ""


class TrustEnvTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cwd = tempfile.mkdtemp(dir=self._tmp.name)
        self.home = tempfile.mkdtemp(dir=self._tmp.name)
        self.xdg = tempfile.mkdtemp(dir=self._tmp.name)
        self.env_patcher = mock.patch.dict(
            os.environ, {"HOME": self.home, "XDG_CONFIG_HOME": self.xdg})
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

        def rec(argv, **kwargs):
            calls.append(list(argv))
            return _FakeResult()

        quota_path = os.path.join(self.cwd, "quota.json")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["probe-quota", "--cwd", self.cwd, "--quota-path", quota_path],
                            run_fn=rec)
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
        self.assertEqual(calls[0][0], sys.executable)

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

    def test_global_only_reviewer_needs_no_trust(self):
        calls = []

        def rec(argv, **kwargs):
            calls.append(list(argv))
            return _FakeResult()

        cfg_dir = os.path.join(self.xdg, "ai-kit")
        os.makedirs(cfg_dir, exist_ok=True)
        with open(os.path.join(cfg_dir, "review-spec.toml"), "w", encoding="utf-8") as f:
            f.write('[[reviewers]]\nkey = "g"\nmodel = "m"\nvendor = "v"\ncli = "codex"\n'
                    f'command = "{self.PROBE_CMD}"\n[policy]\nladder = ["g"]\n')
        quota_path = os.path.join(self.cwd, "quota.json")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["probe-quota", "--cwd", self.cwd, "--quota-path", quota_path],
                            run_fn=rec)
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)

    def test_resolve_reviewers_never_lists_untrusted_local_key(self):
        self.write_local(_local_spec(self.PROBE_CMD))
        quota_path = os.path.join(self.cwd, "quota.json")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["resolve-reviewers", "--cwd", self.cwd,
                             "--quota-path", quota_path])
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


if __name__ == "__main__":
    unittest.main()
