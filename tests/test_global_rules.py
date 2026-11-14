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

LEGACY_START, LEGACY_END = global_rules.LEGACY_START, global_rules.LEGACY_END
BLOCK = global_rules.AIKIT_BLOCK
OLD = b"legacy installer text"


def _file_body(extra_outside=b""):
    # A legacy codegraph block sits mid-file; the codebase-memory-mcp migration replaces it.
    return (
        b"prefix\r\n"
        + LEGACY_START
        + b"\r\n"
        + OLD
        + b"\r\n"
        + LEGACY_END
        + b"\r\n"
        + OLD
        + b" tail \xc3\xa9"
        + extra_outside
    )


def _migrated_body(extra_outside=b""):
    return b"prefix\r\n" + BLOCK + b"\r\n" + OLD + b" tail \xc3\xa9" + extra_outside


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

    def write_one(self, host, body):
        os.makedirs(os.path.dirname(self.paths[host]), exist_ok=True)
        with open(self.paths[host], "wb") as fh:
            fh.write(body)

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

    def ctx(self):
        return config_doctor_checks.ReadContext(data=None, env=self.env, runner=None)


class TestHeadlessRewrite(_ScratchHome):
    def test_replaces_only_the_legacy_block_with_backups(self):
        self.write_all()
        result = self.run_setup("--headless", "--with-global-rules")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for host in ("claude", "codex", "gemini", "opencode"):
            self.assertEqual(self.read(host), _migrated_body(), host)
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
        self.assertEqual(result.stdout.count("already holds the codebase-memory-mcp block"), 4)

    def test_dry_run_prints_preview_and_changes_nothing(self):
        self.write_all()
        result = self.run_setup("--headless", "--with-global-rules", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            result.stdout.count("replace the codegraph block with the codebase-memory-mcp block"),
            4,
        )
        self.assertIn("  - " + LEGACY_START.decode("utf-8"), result.stdout)
        self.assertIn("  - " + OLD.decode("utf-8"), result.stdout)
        self.assertIn("  + " + global_rules.CBM_START.decode("utf-8"), result.stdout)
        self.assertIn(
            "  + ## codebase-memory-mcp (code and doc exploration)", result.stdout
        )
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

    def test_missing_file_and_block_without_markers_are_skipped(self):
        plain = b"no block here " + OLD
        self.write_one("codex", plain)
        result = self.run_setup("--headless", "--with-global-rules")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("skipped: missing file", result.stdout)
        self.assertIn("skipped: no codegraph or codebase-memory-mcp block", result.stdout)
        self.assertEqual(self.read("codex"), plain)


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
        self.assertIn(LEGACY_START, self.read("claude"))


class TestDoctorRow(_ScratchHome):
    def test_read_reports_leftover_block_then_codebase_memory_mcp_block(self):
        self.write_all()
        self.assertEqual(
            config_doctor_checks.read_cbm_global_block(self.ctx()),
            "leftover codegraph block (codebase-memory-mcp replaces it): "
            "claude, codex, gemini, opencode",
        )
        result = config_doctor_checks.apply_row("cbm-global-block", self.ctx(), False)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["current_display"], "codebase-memory-mcp block")
        self.assertEqual(config_doctor_checks.read_cbm_global_block(self.ctx()),
                         "codebase-memory-mcp block")

    def test_no_block_anywhere_reads_no_block(self):
        self.assertEqual(config_doctor_checks.read_cbm_global_block(self.ctx()), "no block")

    def test_dry_apply_writes_nothing(self):
        self.write_all()
        result = config_doctor_checks.apply_row("cbm-global-block", self.ctx(), True)
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
        result = config_doctor_checks.apply_row("cbm-global-block", self.ctx(), False)
        self.assertFalse(result["ok"])
        self.assertIn("backup failed", result["reason"])
        self.assertTrue(result["lines"])

    def test_row_attributes_name_the_installer_source(self):
        rows = config_doctor_checks.CONFIG_DOCTOR_ROWS
        row = next(r for r in rows if r.id == "cbm-global-block")
        self.assertEqual(row.runtime, "cross")
        self.assertEqual(row.scope, "global")
        self.assertFalse(row.reads_section_file)
        self.assertEqual(row.confidence, "MEDIUM")
        self.assertIn("leftover codegraph 1.6.2 installer block with the codebase-memory-mcp block",
                      row.why)
        self.assertIn("installer", row.why)


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
        self.assertNotIn(global_rules.AIKIT_BLOCK, self.read("claude"))

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
            self.assertEqual(fh.read(), _migrated_body())

    def test_one_marker_block_is_skipped_and_read_does_not_raise(self):
        partial = LEGACY_START + b"\n" + OLD + b"\n"
        self.write_one("claude", partial)
        self.assertEqual(config_doctor_checks.read_cbm_global_block(self.ctx()), "no block")
        ok, lines = global_rules.apply(self.env, False)
        self.assertTrue(ok)
        self.assertTrue(any("block with only one marker" in line for line in lines), lines)
        self.assertEqual(self.read("claude"), partial)

    def test_codebase_memory_mcp_block_stays_byte_equal(self):
        body = global_rules.CBM_START + b"\ninstaller text\n" + global_rules.CBM_END
        self.write_one("claude", body)
        ok, lines = global_rules.apply(self.env, False)
        self.assertTrue(ok)
        self.assertEqual(self.read("claude"), body)
        self.assertTrue(
            any(line.startswith("claude") and "already holds" in line for line in lines), lines
        )
        self.assertEqual(self.backups(), [])

    def test_codebase_memory_mcp_and_legacy_blocks_together_stay_byte_equal(self):
        body = (
            global_rules.CBM_START
            + b"\ninstaller text\n"
            + global_rules.CBM_END
            + b"\n"
            + LEGACY_START
            + b"\n"
            + OLD
            + b"\n"
            + LEGACY_END
        )
        self.write_one("claude", body)
        ok, _lines = global_rules.apply(self.env, False)
        self.assertTrue(ok)
        self.assertEqual(self.read("claude"), body)

    def test_lone_codebase_memory_mcp_start_marker_is_skipped_byte_equal(self):
        body = global_rules.CBM_START + b"\ninstaller text\n"
        self.write_one("claude", body)
        ok, lines = global_rules.apply(self.env, False)
        self.assertTrue(ok)
        self.assertTrue(any("block with only one marker" in line for line in lines), lines)
        self.assertEqual(self.read("claude"), body)

    def test_no_instruction_file_is_created(self):
        ok, lines = global_rules.apply(self.env, False)
        self.assertTrue(ok)
        self.assertTrue(any("missing file" in line for line in lines), lines)
        for path in self.paths.values():
            self.assertFalse(os.path.lexists(path), path)

    def test_repeated_legacy_blocks_are_ambiguous_and_byte_equal(self):
        body = (
            LEGACY_START
            + b"\n"
            + OLD
            + b"\n"
            + LEGACY_END
            + b"\n"
            + LEGACY_START
            + b"\n"
            + OLD
            + b"\n"
            + LEGACY_END
        )
        self.write_one("claude", body)
        ok, lines = global_rules.apply(self.env, False)
        self.assertTrue(ok)
        self.assertTrue(any("repeated or nested block markers" in line for line in lines), lines)
        self.assertEqual(self.read("claude"), body)

    def test_nested_legacy_blocks_are_ambiguous_and_byte_equal(self):
        body = (
            LEGACY_START
            + b"\n"
            + LEGACY_START
            + b"\n"
            + OLD
            + b"\n"
            + LEGACY_END
            + b"\n"
            + LEGACY_END
        )
        self.write_one("claude", body)
        ok, lines = global_rules.apply(self.env, False)
        self.assertTrue(ok)
        self.assertTrue(any("repeated or nested block markers" in line for line in lines), lines)
        self.assertEqual(self.read("claude"), body)

    def test_reversed_legacy_pair_is_skipped_byte_equal(self):
        body = LEGACY_END + b"\n" + OLD + b"\n" + LEGACY_START
        self.write_one("claude", body)
        ok, lines = global_rules.apply(self.env, False)
        self.assertTrue(ok)
        self.assertTrue(any("block with only one marker" in line for line in lines), lines)
        self.assertEqual(self.read("claude"), body)

    def test_doctor_value_names_ambiguous_hosts(self):
        self.write_all()
        self.write_one("claude", LEGACY_START + b"\n" + LEGACY_START + b"\n" + LEGACY_END)
        value = config_doctor_checks.read_cbm_global_block(self.ctx())
        self.assertTrue(value.endswith("; ambiguous markers: claude"), value)

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
        self.assertEqual(self.read("claude"), _migrated_body())

    @unittest.skipUnless(NOT_ROOT, "file modes are not enforced for root")
    def test_unreadable_codex_row_reads_and_catalog_still_builds(self):
        self.write_all()
        os.chmod(self.paths["codex"], 0)
        self.addCleanup(os.chmod, self.paths["codex"], 0o600)
        value = config_doctor_checks.read_cbm_global_block(self.ctx())
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
        self.assertEqual(self.read("claude"), _migrated_body())
        self.assertEqual([n for n in os.listdir(gemini_dir) if n.startswith(".ai-kit-global-")], [])


if __name__ == "__main__":
    unittest.main()
