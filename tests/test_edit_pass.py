"""Hermetic edit-pass tracer tests."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "ai-kit-spec-review"))

from ai_kit_spec import cli, config_io, edit_pass, skill_table
from ai_kit_spec.runner_dispatch import RunnerResult

CAP_LINE = ('cross-ai: capabilities {"write":{"value":"WRITE","label":{"state":"verified",'
            '"source":"from argv"}},"shell":{"value":"unknown","label":{"state":"unknown",'
            '"source":"not shown by the final argv"}},"skills":{"value":"unknown","label":'
            '{"state":"unknown","source":"not shown by the final argv"}},"mcp":{"value":'
            '"unknown","label":{"state":"unknown","source":"not shown by the final argv"}},'
            '"prompt":{"channel":"stdin","max_bytes":null}}')


class TestEditPass(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        self.addCleanup(shutil.rmtree, self.root)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.skill = self.root / "edit-a"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_bytes(b"---\nname: edit-a\n---\nEdit body.\n")
        (self.repo / "a.txt").write_bytes(b"one\n")
        (self.repo / "b.bin").write_bytes(b"\xff\xfe\x00raw")
        self.env = {"HOME": str(self.root / "home"), "XDG_CONFIG_HOME": str(self.root / "xdg"),
                    "XDG_STATE_HOME": str(self.root / "state"),
                    "XDG_CACHE_HOME": str(self.root / "cache"), "PATH": str(self.root / "bin")}
        config = Path(config_io.cfg_global_path(self.env))
        config.parent.mkdir(parents=True)
        config.write_text('[review]\nedit_lens_pass = true\n[[lanes.execute]]\nkey = "e1"\n'
                          'runtime = "codex"\nmodel = "fake/placeholder-model-1"\n')
        self.lines = []
        self.calls = []
        self.scan = {"agents": {"skills": [{"name": "edit-a", "role": "edit_lens",
                                           "path": str(self.skill)}], "mcp": [], "mcp_note": None}}
        self.patcher = mock.patch.object(skill_table, "skill_roots", return_value=[str(self.root)])
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def run_pass(self):
        def run(spec, prompt, env):
            self.calls.append((spec, prompt, env))
            (self.repo / "a.txt").write_bytes(b"two\n")
            (self.repo / "b.bin").write_bytes(b"\x00changed")
            return RunnerResult(0, "", {"status": "ok"}, None, False, [], "")

        seams = edit_pass.PassSeams(
            print_argv_fn=lambda *_: [CAP_LINE.replace("WRITE", "workspace")],
            scan_fn=lambda *_: self.scan, run_fn=run, print_fn=self.lines.append)
        req = edit_pass.PassRequest(str(self.repo), ("a.txt", "b.bin"), self.env)
        return edit_pass.run_pass(req, seams)

    def seams(self, run=None, preview=None):
        return edit_pass.PassSeams(
            print_argv_fn=preview or (lambda *_: [CAP_LINE.replace("WRITE", "workspace")]),
            scan_fn=lambda *_: self.scan,
            run_fn=run or (lambda *_: self.fail("unexpected runner call")),
            print_fn=self.lines.append)

    def request(self, files=("a.txt",)):
        return edit_pass.PassRequest(str(self.repo), files, self.env)

    def config(self, text):
        Path(config_io.cfg_global_path(self.env)).write_text(text)

    def test_key_unset_runs_nothing(self):
        for text in ("", '[review]\nedit_lens_pass = "true"\n'):
            self.config(text)
            self.assertEqual(edit_pass.run_pass(self.request(), self.seams()), 0)
            self.assertEqual(self.lines[-1], edit_pass.MSG_OFF)

    def test_no_edit_lens_runs_nothing(self):
        self.scan = {}
        self.assertEqual(edit_pass.run_pass(self.request(), self.seams()), 0)
        self.assertEqual(self.lines[-1], edit_pass.MSG_NO_LENS)

    def test_empty_file_list_runs_nothing(self):
        self.assertEqual(edit_pass.run_pass(self.request(()), self.seams()), 0)
        self.assertEqual(self.lines[-1], edit_pass.MSG_NO_FILES)
        self.assertFalse(Path(edit_pass.record_path(str(self.repo), self.env)).exists())

    def test_read_only_lane_never_chosen(self):
        self.config('[review]\nedit_lens_pass = true\n[[lanes.execute]]\nkey = "e1"\n'
                    'runtime = "codex"\nmodel = "placeholder-model-1"\n'
                    '[[lanes.execute]]\nkey = "e2"\nruntime = "codex"\n'
                    'model = "placeholder-model-2"\n')
        writes = {"placeholder-model-1": "none", "placeholder-model-2": "unknown"}
        def preview(spec, _env):
            return [CAP_LINE.replace("WRITE", writes[spec.model])]
        self.assertEqual(edit_pass.run_pass(self.request(), self.seams(preview=preview)), 0)
        self.assertEqual(self.lines[-1], edit_pass.MSG_NO_LANE)
        self.assertFalse(Path(edit_pass.record_path(str(self.repo), self.env)).exists())
        writes["placeholder-model-2"] = "full"
        def run(spec, *_):
            self.assertEqual(spec.model, "placeholder-model-2")
            return RunnerResult(0, "", {"status": "ok"}, None, False, [], "")
        self.assertEqual(edit_pass.run_pass(self.request(), self.seams(run, preview)), 0)
        self.assertEqual(edit_pass.accept(str(self.repo), self.env, self.lines.append), 0)
        def final_read_only(spec, _env):
            value = "unknown" if spec.skill_names else "workspace"
            return [CAP_LINE.replace("WRITE", value)]
        self.assertEqual(edit_pass.run_pass(self.request(), self.seams(preview=final_read_only)), 0)
        self.assertEqual(self.lines[-1], edit_pass.MSG_NO_LANE)
        self.assertFalse(Path(edit_pass.record_path(str(self.repo), self.env)).exists())

    def test_rejected_path_skipped_by_name(self):
        (self.root / "outside.txt").write_text("outside")
        def run(_spec, prompt, _env):
            self.assertIn("- a.txt", prompt)
            self.assertNotIn("outside.txt", prompt)
            return RunnerResult(0, "", {"status": "ok"}, None, False, [], "")
        self.assertEqual(edit_pass.run_pass(self.request(("a.txt", "../outside.txt")),
                                            self.seams(run)), 0)
        self.assertTrue(any(line.startswith("edit-lens-pass: skipped ") and
                            line.endswith("(path_outside_roots)") for line in self.lines))
        record = json.loads(Path(edit_pass.record_path(str(self.repo), self.env)).read_text())
        self.assertEqual([row["rel"] for row in record["files"]], ["a.txt"])

    def test_locked_result_is_no_edit(self):
        run = lambda *_: RunnerResult(75, "", {"status": "locked"}, None, False, [], "")
        self.assertEqual(edit_pass.run_pass(self.request(), self.seams(run)), 75)
        self.assertEqual(self.lines[-1], edit_pass.MSG_LOCKED)
        self.assertFalse(Path(edit_pass.record_path(str(self.repo), self.env)).exists())

    def test_quota_75_keeps_the_record(self):
        def run(*_):
            (self.repo / "a.txt").write_bytes(b"two\n")
            return RunnerResult(75, "", {"status": "quota"}, None, False, [], "")
        self.assertEqual(edit_pass.run_pass(self.request(), self.seams(run)), 75)
        self.assertIn(edit_pass.MSG_KEPT.format(status="quota"), self.lines)
        record = json.loads(Path(edit_pass.record_path(str(self.repo), self.env)).read_text())
        self.assertEqual(record["state"], "ready")
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 0)

    def test_second_pass_cannot_claim(self):
        path = Path(edit_pass.record_path(str(self.repo), self.env))
        self.assertTrue(edit_pass._claim(str(path), {"state": "running", "pid": os.getpid()}))
        self.assertEqual(edit_pass.run_pass(self.request(), self.seams()), 2)
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 2)
        self.assertEqual(edit_pass.accept(str(self.repo), self.env, self.lines.append), 2)
        self.assertTrue(all(line.startswith("edit-lens-pass: the pass is still running")
                            for line in self.lines))

    def test_accept_keeps_edits_and_drops_record(self):
        self.assertEqual(self.run_pass(), 0)
        self.assertEqual(edit_pass.accept(str(self.repo), self.env, self.lines.append), 0)
        self.assertIn(edit_pass.MSG_ACCEPTED.format(n=2), self.lines)
        self.assertEqual((self.repo / "a.txt").read_bytes(), b"two\n")
        self.assertEqual(edit_pass.accept(str(self.repo), self.env, self.lines.append), 1)
        self.assertEqual(self.lines[-1], edit_pass.MSG_NONE_WAITING)
        # Nothing waiting: neither decision creates the record folder for its lock.
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 1)
        self.assertEqual(self.lines[-1], edit_pass.MSG_NONE_WAITING)
        self.assertFalse(Path(edit_pass.record_path(str(self.repo), self.env)).parent.exists())

    def test_pending_record_blocks_a_second_run(self):
        self.assertEqual(self.run_pass(), 0)
        path = edit_pass.record_path(str(self.repo), self.env)
        self.assertEqual(edit_pass.run_pass(self.request(), self.seams()), 2)
        self.assertEqual(self.lines[-1], edit_pass.MSG_PENDING.format(path=path))
        self.assertEqual(len(self.calls), 1)

    def test_reject_keeps_owner_changes(self):
        self.assertEqual(self.run_pass(), 0)
        (self.repo / "a.txt").write_bytes(b"owner\n")
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 1)
        self.assertIn(edit_pass.MSG_CHANGED.format(rel="a.txt"), self.lines)
        self.assertEqual((self.repo / "a.txt").read_bytes(), b"owner\n")
        self.assertEqual((self.repo / "b.bin").read_bytes(), b"\xff\xfe\x00raw")

    def test_reject_revalidates_recorded_paths(self):
        self.assertEqual(self.run_pass(), 0)
        path = Path(edit_pass.record_path(str(self.repo), self.env))
        record = json.loads(path.read_text())
        outside = self.root / "outside.txt"
        outside.write_text("owner")
        record["files"][0]["path"] = str(outside)
        path.write_text(json.dumps(record))
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 1)
        self.assertEqual(outside.read_text(), "owner")
        self.assertTrue(any(line.startswith("edit-lens-pass: skipped ") for line in self.lines))

    def test_unlisted_edit_blocks_successful_reject(self):
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c",
                        "user.email=test@example.invalid", "commit", "-qm", "initial"], check=True)
        def run(*_):
            (self.repo / "a.txt").write_bytes(b"two\n")
            (self.repo / "other.txt").write_bytes(b"other\n")
            return RunnerResult(0, "", {"status": "ok"}, None, False, [], "")
        self.assertEqual(edit_pass.run_pass(self.request(), self.seams(run)), 0)
        self.assertTrue(any("other.txt" in line for line in self.lines))
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 1)
        self.assertEqual((self.repo / "a.txt").read_bytes(), b"one\n")
        self.assertTrue(any("other.txt" in line for line in self.lines))

    def test_interrupted_pass_can_be_rejected(self):
        path = Path(edit_pass.record_path(str(self.repo), self.env))
        proc = subprocess.Popen([sys.executable, "--version"], stdout=subprocess.DEVNULL)
        proc.wait()
        rows = edit_pass._snapshot([str(self.repo / "a.txt")], str(self.repo))
        self.assertTrue(edit_pass._claim(str(path), {"state": "running", "pid": proc.pid,
                                                    "repo": str(self.repo), "files": rows}))
        (self.repo / "a.txt").write_bytes(b"two\n")
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 0)
        self.assertIn(edit_pass.MSG_INTERRUPTED, self.lines)

    def test_retry_after_partial_reject_and_mode(self):
        (self.repo / "b.bin").chmod(0o755)
        self.assertEqual(self.run_pass(), 0)
        (self.repo / "a.txt").write_bytes(b"owner\n")
        (self.repo / "b.bin").unlink()
        # The deleted post-pass file is an owner change; restore its post bytes for retry.
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 1)
        (self.repo / "a.txt").write_bytes(b"two\n")
        (self.repo / "b.bin").write_bytes(b"\x00changed")
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 0)
        self.assertEqual((self.repo / "b.bin").stat().st_mode & 0o777, 0o755)

    def test_concurrent_decision_is_busy(self):
        path = Path(edit_pass.record_path(str(self.repo), self.env))
        path.parent.mkdir(parents=True)
        (path.parent / "decide.lock").touch()
        self.assertEqual(edit_pass.accept(str(self.repo), self.env, self.lines.append), 2)
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 2)
        self.assertEqual(self.lines, [edit_pass.MSG_BUSY, edit_pass.MSG_BUSY])

    def test_deleted_file_is_reported_and_restored(self):
        def run(*_):
            (self.repo / "b.bin").unlink()
            return RunnerResult(0, "", {"status": "ok"}, None, False, [], "")
        self.assertEqual(edit_pass.run_pass(self.request(("b.bin",)), self.seams(run)), 0)
        self.assertIn("deleted b.bin", self.lines)
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 0)
        self.assertEqual((self.repo / "b.bin").read_bytes(), b"\xff\xfe\x00raw")

    def test_cli_run_accept_reject(self):
        def run(*_):
            (self.repo / "a.txt").write_bytes(b"two\n")
            return RunnerResult(0, "", {"status": "ok"}, None, False, [], "")
        output = io.StringIO()
        seams = self.seams(run)._replace(print_fn=print)
        with (mock.patch.object(edit_pass, "DEFAULT_PASS_SEAMS", seams),
              contextlib.redirect_stdout(output)):
            args = ["edit-lens-pass", "--cwd", str(self.repo)]
            self.assertEqual(cli.main([*args, "--files", "a.txt"], env_fn=lambda: self.env), 0)
            self.assertEqual(cli.main([*args, "--reject"], env_fn=lambda: self.env), 0)
            self.assertEqual((self.repo / "a.txt").read_bytes(), b"one\n")
            self.assertEqual(cli.main([*args, "--files", "a.txt"], env_fn=lambda: self.env), 0)
            self.assertEqual(cli.main([*args, "--accept"], env_fn=lambda: self.env), 0)
        self.assertIn("edited a.txt", output.getvalue())
        self.assertIn(f"--cwd {self.repo}", output.getvalue())
        self.assertEqual((self.repo / "a.txt").read_bytes(), b"two\n")

    def test_reject_restores_non_utf8_bytes(self):
        self.assertEqual(self.run_pass(), 0)
        self.assertIn("edited a.txt +1 -1", self.lines)
        self.assertIn("edited b.bin +1 -1", self.lines)
        self.assertIn(edit_pass.MSG_SCOPE, self.lines)
        self.assertEqual(self.lines[-1], edit_pass.MSG_HINT.format(cwd=str(self.repo)))
        self.assertEqual(edit_pass.reject(str(self.repo), self.env, self.lines.append), 0)
        self.assertEqual((self.repo / "a.txt").read_bytes(), b"one\n")
        self.assertEqual((self.repo / "b.bin").read_bytes(), b"\xff\xfe\x00raw")
        self.assertFalse(Path(edit_pass.record_path(str(self.repo), self.env)).parent.exists())

    def test_run_spec_is_execute_with_edit_lens_flags(self):
        self.assertEqual(self.run_pass(), 0)
        self.assertEqual(len(self.calls), 1)
        spec, prompt, _env = self.calls[0]
        self.assertEqual((spec.mode, spec.runtime), ("exec", "codex"))
        self.assertEqual(spec.skill_names, ("edit-a",))
        self.assertEqual(spec.skill_paths, (os.path.realpath(self.skill),))
        self.assertIn("- a.txt\n- b.bin\n", prompt)
