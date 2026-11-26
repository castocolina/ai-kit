"""Host-config audit: scratch HOME only; a change is an observation and never changes a result."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute-superpowers")
)

from ai_kit_spec import host_config
from ai_kit_spec_superpowers import cli as superpowers_cli
from ai_kit_spec_superpowers import dispatch_injection

INJECTION = {
    "mode": "external_cli",
    "key": "lane-a",
    "runtime": "codex",
    "model": "fake/placeholder-model-1",
    "effort": None,
    "service_tier": None,
}
T_BEFORE = 1_700_000_000_000_000_000
T_AFTER = 1_700_000_100_000_000_000
SETTINGS = ".claude/settings.json"


def _touch(home, rel, t=T_AFTER):
    path = os.path.join(home, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("{}")
    os.utime(path, ns=(t, t))


class _BrokenStream(io.StringIO):
    def write(self, _text):
        raise OSError("stream closed")


class _ScratchHome(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = tmp.name
        self.env = {"HOME": self.home}
        _touch(self.home, SETTINGS, T_BEFORE)

    def _dispatch(self, fake):
        return dispatch_injection.dispatch_superpowers_task(
            dispatch_injection.DispatchTaskRequest(INJECTION, "do the task", self.home, 900),
            seams=dispatch_injection.SuperpowersDispatchSeams(
                dispatch_execute_fn=fake, env_fn=lambda: dict(self.env)
            ),
        )


class TestHostConfigAudit(_ScratchHome):
    def test_a_lane_that_touches_a_config_file_is_reported(self):
        def fake(_spec):
            _touch(self.home, SETTINGS)
            return {"returncode": 0, "stdout": "ok"}

        err = io.StringIO()
        with redirect_stderr(err):
            result = self._dispatch(fake)
        path = os.path.join(self.home, SETTINGS)
        self.assertEqual(result["host_config_changed"], [path])
        text = err.getvalue()
        self.assertIn(host_config.OBSERVATION.format(path=path), text)
        self.assertTrue(text.rstrip("\n").endswith(host_config.NOT_CHECKED))
        self.assertEqual(result["returncode"], 0)

    def test_a_lane_that_touches_nothing_reports_nothing(self):
        def fake(_spec):
            return {"returncode": 0, "stdout": "ok"}

        err = io.StringIO()
        with redirect_stderr(err):
            result = self._dispatch(fake)
        self.assertEqual(result["host_config_changed"], [])
        self.assertEqual(err.getvalue(), "")

    def test_a_dispatch_that_raises_keeps_its_exception_and_reports(self):
        def fake(_spec):
            _touch(self.home, SETTINGS)
            raise RuntimeError("lane broke")

        err = io.StringIO()
        with redirect_stderr(err), self.assertRaisesRegex(RuntimeError, "lane broke"):
            self._dispatch(fake)
        self.assertIn(
            host_config.OBSERVATION.format(path=os.path.join(self.home, SETTINGS)), err.getvalue()
        )

    def test_a_failing_stderr_stream_never_replaces_the_dispatch_exception(self):
        def raising(_spec):
            _touch(self.home, SETTINGS)
            raise RuntimeError("lane broke")

        with redirect_stderr(_BrokenStream()), self.assertRaisesRegex(RuntimeError, "lane broke"):
            self._dispatch(raising)

        def returning(_spec):
            _touch(self.home, SETTINGS, T_AFTER + 1)
            return {"returncode": 0, "stdout": "ok"}

        with redirect_stderr(_BrokenStream()):
            result = self._dispatch(returning)
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["host_config_changed"], [os.path.join(self.home, SETTINGS)])

    def test_a_closed_or_missing_stderr_never_replaces_the_dispatch_exception(self):
        def raising(_spec):
            _touch(self.home, SETTINGS)
            raise RuntimeError("lane broke")

        closed = io.StringIO()
        closed.close()
        with redirect_stderr(closed), self.assertRaisesRegex(RuntimeError, "lane broke"):
            self._dispatch(raising)

        def returning(_spec):
            _touch(self.home, SETTINGS, T_AFTER + 1)
            return {"returncode": 0, "stdout": "ok"}

        out = io.StringIO()
        with redirect_stderr(None), redirect_stdout(out):
            result = self._dispatch(returning)
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["host_config_changed"], [os.path.join(self.home, SETTINGS)])
        self.assertEqual(out.getvalue(), "")

    def test_a_stat_error_is_unavailable_never_a_change(self):
        def denied(_path):
            raise PermissionError("denied")

        def missing(_path):
            raise FileNotFoundError("gone")

        self.assertEqual(
            set(host_config.snapshot(self.env, stat_fn=denied).values()), {host_config.UNAVAILABLE}
        )
        self.assertEqual(set(host_config.snapshot(self.env, stat_fn=missing).values()), {None})
        before = host_config.snapshot(self.env)
        after = host_config.snapshot(self.env, stat_fn=denied)
        self.assertEqual(host_config.changed(before, after), [])
        self.assertEqual(
            host_config.unavailable(before, after), list(host_config.HOST_CONFIG_FILES)
        )
        lines = host_config.observation_lines(
            self.env, [], host_config.unavailable(before, after)
        )
        joined = "\n".join(lines)
        self.assertIn(
            host_config.UNAVAILABLE_FOR.format(path=os.path.join(self.home, SETTINGS)), lines
        )
        self.assertNotIn("changed during the lane", joined)
        self.assertNotIn(host_config.NOT_CHECKED, lines)


class TestHostConfigAuditEdges(_ScratchHome):
    def _main(self, argv):
        out = io.StringIO()
        code = superpowers_cli.main(argv, env_fn=lambda: dict(self.env), stdout=out)
        return code, out.getvalue()

    def _snap_path(self, name="snap.json"):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return os.path.join(folder.name, name)

    def test_two_touched_files_are_reported_in_list_order(self):
        before = host_config.snapshot(self.env)
        _touch(self.home, ".gsd/defaults.json")
        _touch(self.home, ".claude.json")
        paths = host_config.changed(before, host_config.snapshot(self.env))
        self.assertEqual(paths, [".claude.json", ".gsd/defaults.json"])
        lines = host_config.observation_lines(self.env, paths)
        self.assertEqual(len(lines), 3)
        self.assertIn(os.path.join(self.home, ".claude.json"), lines[0])
        self.assertIn(os.path.join(self.home, ".gsd/defaults.json"), lines[1])
        self.assertEqual(lines[2], host_config.NOT_CHECKED)

    def test_a_path_with_spaces_and_non_ascii_is_verbatim(self):
        home = os.path.join(self.home, "home with space \u00fc")
        os.makedirs(home)
        env = {"HOME": home}
        before = host_config.snapshot(env)
        _touch(home, ".codex/config.toml")
        paths = host_config.changed(before, host_config.snapshot(env))
        lines = host_config.observation_lines(env, paths)
        self.assertIn(os.path.join(home, ".codex/config.toml"), lines[0])

    def test_a_listed_folder_is_never_read(self):
        rel = ".cursor/mcp.json"
        inner = os.path.join(self.home, rel, "inner.json")
        os.makedirs(os.path.dirname(inner))
        with open(inner, "w", encoding="utf-8") as f:
            f.write("{}")
        before = host_config.snapshot(self.env)
        self.assertIsNone(before[rel])
        os.utime(inner, ns=(T_AFTER, T_AFTER))
        self.assertEqual(host_config.changed(before, host_config.snapshot(self.env)), [])

    def test_a_failing_lane_keeps_its_return_code(self):
        def fake(_spec):
            _touch(self.home, SETTINGS)
            return {"returncode": 1, "stdout": ""}

        with redirect_stderr(io.StringIO()):
            result = self._dispatch(fake)
        self.assertEqual(result["returncode"], 1)
        self.assertEqual(result["host_config_changed"], [os.path.join(self.home, SETTINGS)])

    def test_cli_snapshot_then_compare(self):
        snap = self._snap_path()
        code, out = self._main(["host-config-audit", "--snapshot", snap])
        self.assertEqual((code, out), (0, ""))
        with open(snap, encoding="utf-8") as f:
            self.assertEqual(set(json.load(f)), set(host_config.HOST_CONFIG_FILES))
        rel = ".config/opencode/opencode.jsonc"
        _touch(self.home, rel)
        code, out = self._main(["host-config-audit", "--compare", snap])
        self.assertEqual(code, 0)
        expected = host_config.observation_lines(self.env, [rel])
        self.assertEqual(out, "\n".join(expected) + "\n")
        self._main(["host-config-audit", "--snapshot", snap])
        self.assertEqual(self._main(["host-config-audit", "--compare", snap]), (0, ""))

    def test_cli_compare_reports_an_unusable_snapshot(self):
        unavailable = "ai-kit-spec: observation: host-config audit unavailable: {}\n"
        missing = self._snap_path("missing.json")
        self.assertEqual(
            self._main(["host-config-audit", "--compare", missing]),
            (0, unavailable.format(f"cannot read {missing}")),
        )
        good = host_config.snapshot(self.env)
        short = {k: v for k, v in good.items() if k != SETTINGS}
        bad_cases = [
            [1],
            {},
            short,
            {**good, "extra": 1},
            {**good, SETTINGS: True},
            {**good, SETTINGS: "x"},
        ]
        for index, content in enumerate(bad_cases):
            path = self._snap_path(f"bad{index}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(content, f)
            code, out = self._main(["host-config-audit", "--compare", path])
            self.assertEqual(code, 0)
            self.assertEqual(out, unavailable.format(f"{path} is not a host-config snapshot"))
            self.assertNotIn("changed during the lane", out)
        with self.assertRaises(SystemExit) as ctx, redirect_stderr(io.StringIO()):
            self._main(["host-config-audit", "--snapshot", "a", "--compare", "b"])
        self.assertEqual(ctx.exception.code, 2)
        flagged = self._snap_path("flagged.json")
        with open(flagged, "w", encoding="utf-8") as f:
            json.dump({**good, SETTINGS: host_config.UNAVAILABLE}, f)
        code, out = self._main(["host-config-audit", "--compare", flagged])
        self.assertEqual(code, 0)
        self.assertEqual(
            out,
            host_config.UNAVAILABLE_FOR.format(path=os.path.join(self.home, SETTINGS)) + "\n",
        )
        self.assertNotIn("changed during the lane", out)

    def test_cli_snapshot_write_failure_is_an_observation(self):
        blocker = self._snap_path("blocker")
        with open(blocker, "w", encoding="utf-8") as f:
            f.write("x")
        target = os.path.join(blocker, "snap.json")
        code, out = self._main(["host-config-audit", "--snapshot", target])
        self.assertEqual(code, 0)
        self.assertTrue(
            out.startswith("ai-kit-spec: observation: host-config audit unavailable: cannot write ")
        )
        self.assertFalse(os.path.exists(target))


SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "ai-kit-spec-execute-superpowers"
RUN_SNAPSHOT = 'host-config-audit --snapshot "$RUN_DIR/host-config-before.json"'
RUN_COMPARE = 'host-config-audit --compare "$RUN_DIR/host-config-before.json"'
RM_SNAPSHOT = 'rm -f "$RUN_DIR/host-config-before.json"'


class TestHostConfigAuditDocs(unittest.TestCase):
    def test_reference_section_lists_every_file(self):
        text = (SKILL_DIR / "references" / "dispatch-external-cli.md").read_text(encoding="utf-8")
        lines = text.splitlines()
        self.assertEqual(lines.count("## Host-config audit"), 1)
        for rel in host_config.HOST_CONFIG_FILES:
            self.assertIn(rel, text)
        self.assertIn(host_config.OBSERVATION.format(path="<path>"), text)
        self.assertIn(host_config.UNAVAILABLE_FOR.format(path="<path>"), text)
        self.assertIn("before the empty-result stop", text)
        self.assertIn("before `## Classify`", text)
        self.assertLess(lines.index("## Host-config audit"), lines.index("## Classify"))

    def test_skill_native_line_names_both_commands(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        native = [ln for ln in text.splitlines() if RUN_SNAPSHOT in ln]
        self.assertEqual(len(native), 1)
        line = native[0]
        for needle in (
            RUN_COMPARE,
            "references/dispatch-external-cli.md#host-config-audit",
            "the session fallback and a failed native launch included",
        ):
            self.assertIn(needle, line)
        self.assertLess(line.index(RM_SNAPSHOT), line.index(RUN_SNAPSHOT))
        self.assertLess(line.index(RUN_SNAPSHOT), line.index(RUN_COMPARE))
        self.assertLess(line.index(RUN_COMPARE), line.rindex(RM_SNAPSHOT))
        self.assertIn("real-home guard is not applicable to a native dispatch", text)
        for rel in host_config.HOST_CONFIG_FILES:
            self.assertNotIn(rel, text)


if __name__ == "__main__":
    unittest.main()
