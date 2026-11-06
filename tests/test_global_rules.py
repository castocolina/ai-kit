import datetime
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TOOLS_DIR = os.path.join(_REPO, "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
import config_doctor_checks
import global_rules

START, END = global_rules.START, global_rules.END
INST, AIKIT = global_rules.INSTALLER_SENTENCE, global_rules.AIKIT_SENTENCE


def _file_body(extra_outside=b""):
    # The installer sentence first appears inside the block: the rewrite is in-block.
    return (
        b"prefix\r\n"
        + START
        + b"\r\n"
        + INST
        + b"\r\n"
        + END
        + b"\r\n"
        + INST
        + b" tail \xc3\xa9"
        + extra_outside
    )


class _ScratchHome(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="ai-kit-p30-")
        self.addCleanup(shutil.rmtree, self.home, True)
        self.paths = {
            "claude": os.path.join(self.home, ".claude", "CLAUDE.md"),
            "codex": os.path.join(self.home, ".codex", "AGENTS.md"),
            "gemini": os.path.join(self.home, ".gemini", "GEMINI.md"),
            "opencode": os.path.join(self.home, ".config", "opencode", "AGENTS.md"),
        }
        self.state = os.path.join(self.home, "state")
        self.env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": self.home,
            "XDG_STATE_HOME": self.state,
            "XDG_CONFIG_HOME": os.path.join(self.home, ".config"),
            "CLAUDE_CONFIG_DIR": os.path.join(self.home, ".claude"),
            "CODEX_HOME": os.path.join(self.home, ".codex"),
            "AI_KIT_REFUSE_REAL_HOME": "1",
        }
        # T-30-12: every host path the code resolves lies under this scratch HOME
        for _host, path in global_rules.global_instruction_paths(self.env):
            self.assertTrue(os.path.realpath(path).startswith(os.path.realpath(self.home) + os.sep),
                            path)

    def write_all(self, body=None):
        for path in self.paths.values():
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(body if body is not None else _file_body())

    def read(self, host):
        with open(self.paths[host], "rb") as fh:
            return fh.read()

    def run_setup(self, *extra):
        argv = [sys.executable, os.path.join(_REPO, "tools", "setup.py"), "install", *extra]
        return subprocess.run(
            argv, cwd=_REPO, env=self.env, capture_output=True, text=True, check=False
        )

    def backups(self):
        root = os.path.join(self.state, "ai-kit", "backups", "global-rules")
        return sorted(os.listdir(root)) if os.path.isdir(root) else []


class TestHeadlessRewrite(_ScratchHome):
    def test_rewrites_only_the_in_block_sentence_with_backups(self):
        self.write_all()
        result = self.run_setup("--headless", "--with-global-rules")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for host in ("claude", "codex", "gemini", "opencode"):
            self.assertEqual(self.read(host), _file_body().replace(INST, AIKIT, 1), host)
        self.assertEqual(len(self.backups()), 4)

    def test_report_lists_hosts_in_fixed_order(self):
        self.write_all()
        result = self.run_setup("--headless", "--with-global-rules")
        hosts = [line.split()[0] for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(hosts[:4], ["claude", "codex", "gemini", "opencode"])

    def test_second_run_gives_no_diff_and_no_new_backup(self):
        self.write_all()
        self.run_setup("--headless", "--with-global-rules")
        before = {h: self.read(h) for h in self.paths}
        backups_before = self.backups()
        result = self.run_setup("--headless", "--with-global-rules")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual({h: self.read(h) for h in self.paths}, before)
        self.assertEqual(self.backups(), backups_before)
        self.assertEqual(result.stdout.count("already ai-kit's wording"), 4)

    def test_dry_run_prints_preview_and_changes_nothing(self):
        self.write_all()
        result = self.run_setup("--headless", "--with-global-rules", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("  - " + INST.decode("utf-8"), result.stdout)
        self.assertIn("  + " + AIKIT.decode("utf-8"), result.stdout)
        for host in self.paths:
            self.assertEqual(self.read(host), _file_body())
        self.assertEqual(self.backups(), [])

    def test_bare_headless_touches_no_global_file(self):
        self.write_all()
        result = self.run_setup("--headless")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for host in self.paths:
            self.assertEqual(self.read(host), _file_body())

    def test_with_global_rules_without_headless_is_usage_error(self):
        self.write_all()
        result = self.run_setup("--with-global-rules")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        for host in self.paths:
            self.assertEqual(self.read(host), _file_body())

    def test_missing_file_and_block_without_sentence_are_skipped(self):
        os.makedirs(os.path.dirname(self.paths["codex"]), exist_ok=True)
        plain = b"no block here " + INST
        with open(self.paths["codex"], "wb") as fh:
            fh.write(plain)
        result = self.run_setup("--headless", "--with-global-rules")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("skipped: missing file", result.stdout)
        self.assertIn("skipped: no codegraph block", result.stdout)
        with open(self.paths["codex"], "rb") as fh:
            self.assertEqual(fh.read(), plain)


class TestApplyFunction(_ScratchHome):
    def test_changed_after_review_is_not_written(self):
        self.write_all()
        reviewed = [c for c in global_rules.plan_changes(self.env) if c.status == "replace"]
        with open(self.paths["claude"], "ab") as fh:
            fh.write(b"edited")
        ok, lines = global_rules.apply(self.env, False, reviewed=reviewed)
        self.assertTrue(ok)
        self.assertTrue(any("changed since it was reviewed; not written" in line for line in lines))
        self.assertTrue(self.read("claude").endswith(b"edited"))
        self.assertIn(INST, self.read("claude"))


class TestDoctorRow(_ScratchHome):
    def ctx(self):
        return config_doctor_checks.ReadContext(data=None, env=self.env, runner=None)

    def test_read_reports_installer_wording_then_ai_kit_wording(self):
        self.write_all()
        self.assertEqual(
            config_doctor_checks.read_codegraph_global_sentence(self.ctx()),
            "installer wording: claude, codex, gemini, opencode",
        )
        result = config_doctor_checks.apply_row("codegraph-global-sentence", self.ctx(), False)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["current_display"], "ai-kit wording")
        self.assertEqual(
            config_doctor_checks.read_codegraph_global_sentence(self.ctx()), "ai-kit wording"
        )

    def test_no_block_anywhere_reads_no_codegraph_block(self):
        self.assertEqual(
            config_doctor_checks.read_codegraph_global_sentence(self.ctx()), "no codegraph block"
        )

    def test_dry_apply_writes_nothing(self):
        self.write_all()
        result = config_doctor_checks.apply_row("codegraph-global-sentence", self.ctx(), True)
        self.assertTrue(result["ok"], result)
        for host in self.paths:
            self.assertEqual(self.read(host), _file_body())

    def test_failed_apply_reports_reason_and_lines(self):
        self.write_all()
        os.makedirs(os.path.join(self.state, "ai-kit", "backups", "global-rules"), exist_ok=True)
        os.chmod(os.path.join(self.state, "ai-kit", "backups", "global-rules"), 0o500)
        self.addCleanup(
            os.chmod, os.path.join(self.state, "ai-kit", "backups", "global-rules"), 0o700
        )
        result = config_doctor_checks.apply_row("codegraph-global-sentence", self.ctx(), False)
        self.assertFalse(result["ok"])
        self.assertIn("backup failed", result["reason"])
        self.assertTrue(result["lines"])

    def test_row_attributes_name_the_installer_source(self):
        rows = config_doctor_checks.CONFIG_DOCTOR_ROWS
        row = next(r for r in rows if r.id == "codegraph-global-sentence")
        self.assertEqual(row.runtime, "cross")
        self.assertEqual(row.scope, "global")
        self.assertFalse(row.reads_section_file)
        self.assertEqual(row.confidence, "MEDIUM")
        self.assertIn("codegraph 1.6.2", row.why)
        self.assertIn("installer", row.why)
        self.assertIn("may move the block or reword the sentence", row.why)


NOT_ROOT = hasattr(os, "geteuid") and os.geteuid() != 0


class TestEdges(_ScratchHome):
    def test_backup_names_claim_numbered_suffix_on_collision(self):
        directory = os.path.join(self.state, "ai-kit", "backups", "global-rules")
        first = global_rules._claim_backup(directory, "claude-x-CLAUDE.md", b"one")
        second = global_rules._claim_backup(directory, "claude-x-CLAUDE.md", b"two")
        self.assertEqual(os.path.basename(first), "claude-x-CLAUDE.md")
        self.assertEqual(os.path.basename(second), "claude-x-CLAUDE.md-1")
        with open(first, "rb") as fh:
            self.assertEqual(fh.read(), b"one")

    def test_same_clock_twice_keeps_both_backups(self):
        when = datetime.datetime(2026, 11, 5, 12, 0, tzinfo=datetime.UTC)
        self.write_all()
        global_rules.apply(self.env, False, now=when)
        self.write_all()
        ok, _lines = global_rules.apply(self.env, False, now=when)
        self.assertTrue(ok)
        names = [n for n in self.backups() if n.startswith("claude-")]
        self.assertEqual(len(names), 2, names)

    def test_changed_since_read_is_abandoned_and_kept(self):
        self.write_all()

        def append_byte(path):
            with open(path, "ab") as fh:
                fh.write(b"!")

        ok, lines = global_rules.apply(self.env, False, before_replace=append_byte)
        self.assertTrue(ok)
        self.assertTrue(any("changed since it was read" in line for line in lines), lines)
        self.assertTrue(self.read("claude").endswith(b"!"))
        self.assertNotIn(global_rules.AIKIT_SENTENCE, self.read("claude"))

    def test_reviewed_set_skips_unreviewed_replace(self):
        self.write_all()
        reviewed = [c for c in global_rules.plan_changes(self.env) if c.status == "replace"]
        reviewed = [c for c in reviewed if c.host != "gemini"]
        ok, lines = global_rules.apply(self.env, False, reviewed=reviewed)
        self.assertTrue(ok)
        self.assertTrue(any(line.startswith("gemini") and "not reviewed" in line for line in lines))
        self.assertEqual(self.read("gemini"), _file_body())

    def test_symlinked_target_is_rewritten_in_place(self):
        real = os.path.join(self.home, "real-claude.md")
        with open(real, "wb") as fh:
            fh.write(_file_body())
        os.makedirs(os.path.dirname(self.paths["claude"]), exist_ok=True)
        os.symlink(real, self.paths["claude"])
        ok, _lines = global_rules.apply(self.env, False)
        self.assertTrue(ok)
        self.assertTrue(os.path.islink(self.paths["claude"]))
        with open(real, "rb") as fh:
            self.assertEqual(fh.read(), _file_body().replace(INST, AIKIT, 1))

    def test_one_marker_block_is_skipped_and_read_does_not_raise(self):
        os.makedirs(os.path.dirname(self.paths["claude"]), exist_ok=True)
        partial = START + b"\n" + INST + b"\n"
        with open(self.paths["claude"], "wb") as fh:
            fh.write(partial)
        self.assertEqual(
            config_doctor_checks.read_codegraph_global_sentence(
                config_doctor_checks.ReadContext(data=None, env=self.env, runner=None)
            ),
            "no codegraph block",
        )
        ok, lines = global_rules.apply(self.env, False)
        self.assertTrue(ok)
        self.assertTrue(any("block with only one marker" in line for line in lines), lines)
        self.assertEqual(self.read("claude"), partial)

    @unittest.skipUnless(NOT_ROOT, "file modes are not enforced for root")
    def test_unreadable_file_is_skipped_and_others_rewritten(self):
        self.write_all()
        os.chmod(self.paths["codex"], 0)
        self.addCleanup(os.chmod, self.paths["codex"], 0o600)
        ok, lines = global_rules.apply(self.env, False)
        self.assertTrue(ok)
        self.assertTrue(
            any(line.startswith("codex") and "unreadable" in line for line in lines), lines
        )
        self.assertEqual(self.read("claude"), _file_body().replace(INST, AIKIT, 1))

    @unittest.skipUnless(NOT_ROOT, "file modes are not enforced for root")
    def test_unreadable_codex_row_reads_and_catalog_still_builds(self):
        self.write_all()
        os.chmod(self.paths["codex"], 0)
        self.addCleanup(os.chmod, self.paths["codex"], 0o600)
        value = config_doctor_checks.read_codegraph_global_sentence(
            config_doctor_checks.ReadContext(data=None, env=self.env, runner=None)
        )
        self.assertTrue(value.endswith("; unreadable: codex"), value)
        catalog = config_doctor_checks.build_catalog(
            self.env, runner=lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "")
        )
        self.assertTrue(catalog["sections"])

    @unittest.skipUnless(NOT_ROOT, "directory modes are not enforced for root")
    def test_read_only_target_dir_is_write_failed_and_loop_continues(self):
        self.write_all()
        gemini_dir = os.path.dirname(self.paths["gemini"])
        os.chmod(gemini_dir, 0o500)
        self.addCleanup(os.chmod, gemini_dir, 0o700)
        ok, lines = global_rules.apply(self.env, False)
        self.assertFalse(ok)
        self.assertTrue(
            any(line.startswith("gemini") and "write failed" in line for line in lines), lines
        )
        self.assertEqual(self.read("gemini"), _file_body())
        self.assertEqual(self.read("claude"), _file_body().replace(INST, AIKIT, 1))
        self.assertEqual([n for n in os.listdir(gemini_dir) if n.startswith(".ai-kit-global-")], [])


if __name__ == "__main__":
    unittest.main()
