"""Unit tests of the hook registry (D-11): row shape, the selector parser,
the grouped Claude writer and unwirer, per-hook-object ownership (Round 4),
and the registry-driven helpers the headless/wizard paths share.

Everything runs in a temp HOME — never the real ~/.claude.
"""
import contextlib
import importlib.util
import io
import json
import os
import shlex
import shutil
import sys
import tempfile
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_SETUP_PATH = os.path.join(_REPO, "tools", "setup.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


setup = _load("setup_hook_registry", _SETUP_PATH)

PRECOMPACT_CLAUDE_ROWS = [
    row for row in setup.HOOK_REGISTRY
    if row.id == "precompact" and row.host == "claude"
]


def _wire_settings(tmp, initial=None):
    claude = os.path.join(tmp, "claude")
    os.makedirs(claude, exist_ok=True)
    settings = os.path.join(claude, "settings.json")
    if initial is not None:
        with open(settings, "w", encoding="utf-8") as handle:
            json.dump(initial, handle)
    return settings


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class TestRegistryShape(unittest.TestCase):
    def test_registry_rows_shape(self):
        rows = [row for row in setup.HOOK_REGISTRY if row.id == "precompact"]
        self.assertEqual(
            [(r.host, r.event) for r in rows],
            [("claude", "PreCompact"), ("claude", "SessionStart"),
             ("pi", "session_before_compact"),
             ("opencode", "experimental.session.compacting")])
        for row in rows:
            with self.subTest(row=row.event):
                self.assertTrue(os.path.isfile(os.path.join(_REPO, *row.script.split("/"))))
                self.assertTrue(row.verdict in setup.HOOK_VERDICTS
                                or row.verdict.startswith("gap:"))
                self.assertEqual(row.default, row.verdict == "positive")
                self.assertEqual(row.experimental, row.host == "opencode")
        self.assertEqual(setup.HOOK_IDS, ("precompact",))


class TestParseHookSelector(unittest.TestCase):
    def test_parse_hook_selector(self):
        self.assertEqual(setup.parse_hook_selector("precompact"),
                         [("precompact", None)])
        self.assertEqual(
            setup.parse_hook_selector("precompact:pi, precompact:claude"),
            [("precompact", "pi"), ("precompact", "claude")])
        for bad in ("nope", "precompact:cursor", "install"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as ctx:
                    setup.parse_hook_selector(bad)
                self.assertEqual(str(ctx.exception), bad)

    def test_hook_rows_selection(self):
        rows = setup.hook_rows([("precompact", "pi")])
        self.assertEqual([r.host for r in rows], ["pi"])
        self.assertEqual(len(setup.hook_rows([("precompact", None)])), 4)
        self.assertEqual(setup.hook_rows([("ghost", None)]), ())


class TestRefreshKeepsNestedUserHook(unittest.TestCase):
    """Round 4: ownership is per hook object, not per entry."""

    def _rows_case(self, same_matcher):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        row = PRECOMPACT_CLAUDE_ROWS[0]  # PreCompact, matcher manual|auto
        marker = os.path.join(*row.script.split("/"))
        entry_matcher = row.matcher if same_matcher else "different"
        ours_old = {
            "type": "command",
            "command": "python3 -S /old/" + marker,
        }
        user = {"type": "command", "command": "echo mine"}
        initial = {"hooks": {"PreCompact": [
            {"matcher": entry_matcher, "hooks": [user, ours_old], "note": "x"},
        ]}}
        settings = _wire_settings(tmp, initial)
        kit = os.path.join(tmp, "kit")
        os.makedirs(os.path.join(kit, "tools", "hooks"), exist_ok=True)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(setup.wire_claude_rows(
                settings, [row], kit, dry=False))
        data = _read(settings)
        entries = data["hooks"]["PreCompact"]
        ours = [e for e in entries if any(
            marker in h.get("command", "") for h in e.get("hooks") or [])]
        self.assertEqual(len(ours), 1)
        if same_matcher:
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry["note"], "x")
            self.assertEqual(entry["matcher"], row.matcher)
            self.assertEqual(entry["hooks"][0], user)
            self.assertEqual(len(entry["hooks"]), 2)
            self.assertIn("python3 -S ", entry["hooks"][1]["command"])
            self.assertEqual(entry["hooks"][1]["timeout"], row.timeout)
        else:
            kept = [e for e in entries if e is not ours[0]
                    and e.get("note") == "x"]
            self.assertEqual(len(kept), 1)
            self.assertEqual(kept[0]["hooks"], [user])
            self.assertEqual(kept[0]["matcher"], "different")
            self.assertEqual(ours[0]["matcher"], row.matcher)
            self.assertEqual(len(ours[0]["hooks"]), 1)

    def test_refresh_keeps_nested_user_hook(self):
        # subTest per plan: same-matcher in-place refresh and differing-matcher move.
        for same in (True, False):
            with self.subTest(same_matcher=same):
                self._rows_case(same)

    def test_briefing_refresh_keeps_nested_user_hook(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        user = {"type": "command", "command": "echo mine"}
        ours_old = {
            "type": "command",
            "command": "python3 -S /old/" + setup.CLAUDE_HOOK_MARKER,
        }
        settings = _wire_settings(tmp, {"hooks": {"SessionStart": [
            {"matcher": setup.CLAUDE_HOOK_MATCHER,
             "hooks": [user, ours_old], "note": "x"},
        ]}})
        wrapper = os.path.join(tmp, "kit", "claude_session_start.py")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(setup.wire_hook_claude(settings, wrapper, dry=False))
        entry = _read(settings)["hooks"]["SessionStart"][0]
        self.assertEqual(entry["note"], "x")
        self.assertEqual(entry["matcher"], setup.CLAUDE_HOOK_MATCHER)
        self.assertEqual(entry["hooks"][0], user)
        self.assertEqual(len(entry["hooks"]), 2)
        self.assertEqual(entry["hooks"][1]["command"],
                         "python3 -S " + shlex.quote(wrapper))
        self.assertNotIn("timeout", entry["hooks"][1])


class TestOneAtomicReplacePerFile(unittest.TestCase):
    def test_one_atomic_replace_per_settings_file(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        foreign = {"theme": "dark", "hooks": {"PreCompact": [
            {"matcher": "manual", "hooks": [
                {"type": "command", "command": "echo foreign"}]}]}}
        settings = _wire_settings(tmp, foreign)
        kit = os.path.join(tmp, "kit")
        os.makedirs(os.path.join(kit, "tools", "hooks"), exist_ok=True)
        real_replace = os.replace
        calls = []

        def counting(src, dst):
            if os.path.realpath(dst) == os.path.realpath(settings):
                calls.append(dst)
            return real_replace(src, dst)

        with mock.patch.object(setup.os, "replace", side_effect=counting), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(setup.wire_claude_rows(
                settings, PRECOMPACT_CLAUDE_ROWS, kit, dry=False))
        self.assertEqual(len(calls), 1)
        data = _read(settings)
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["hooks"]["PreCompact"][0], foreign["hooks"]["PreCompact"][0])
        self.assertEqual(len(data["hooks"]["PreCompact"]), 2)
        # Second wiring refreshes in place: still one ai-kit entry per event.
        calls.clear()
        with mock.patch.object(setup.os, "replace", side_effect=counting), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(setup.wire_claude_rows(
                settings, PRECOMPACT_CLAUDE_ROWS, kit, dry=False))
        self.assertEqual(len(calls), 1)
        data = _read(settings)
        self.assertEqual(len(data["hooks"]["PreCompact"]), 2)
        self.assertEqual(len(data["hooks"]["SessionStart"]), 1)


class TestClaudeRowsGuard(unittest.TestCase):
    def test_malformed_settings_refused_whole_file(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        claude = os.path.join(tmp, "claude")
        os.makedirs(claude)
        settings = os.path.join(claude, "settings.json")
        payload = b'{"hooks": {"SessionStart": "nope"}}\n'
        with open(settings, "wb") as handle:
            handle.write(payload)
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            ok = setup.wire_claude_rows(
                settings, PRECOMPACT_CLAUDE_ROWS, tmp, dry=False)
        self.assertFalse(ok)
        self.assertIn("not a list", buf.getvalue())
        with open(settings, "rb") as handle:
            self.assertEqual(handle.read(), payload)


class TestHookPathsAndDescription(unittest.TestCase):
    def test_opencode_dir_precedence(self):
        home = "/tmp/home"
        xdg = "/tmp/xdg"
        paths = setup.resolve_paths({"HOME": home, "XDG_CONFIG_HOME": xdg,
                                     "OPENCODE_CONFIG_DIR": "/tmp/oc"})
        self.assertEqual(paths.opencode_dir, "/tmp/oc")
        paths = setup.resolve_paths({"HOME": home, "XDG_CONFIG_HOME": xdg})
        self.assertEqual(paths.opencode_dir, os.path.join(xdg, "opencode"))
        paths = setup.resolve_paths({"HOME": home})
        self.assertEqual(paths.opencode_dir, os.path.join(home, ".config", "opencode"))
        rows = [r for r in setup.HOOK_REGISTRY if r.id == "precompact"]
        self.assertIsNone(setup.hook_link_path(paths, rows[0]))
        self.assertEqual(setup.hook_link_path(paths, rows[2]),
                         os.path.join(paths.pi_dir, "extensions", "ai-kit-precompact.ts"))
        self.assertEqual(setup.hook_link_path(paths, rows[3]),
                         os.path.join(paths.opencode_dir, "plugins", "ai-kit-precompact.ts"))

    def test_hook_description_and_help(self):
        desc = setup.hook_description("precompact")
        self.assertLessEqual(len(desc), 200)
        for host in ("claude", "pi", "opencode"):
            row = next(r for r in setup.HOOK_REGISTRY if r.host == host)
            self.assertIn(f"{host}: {row.verdict} ({'on' if row.default else 'off'})", desc)
        self.assertIn("experimental", desc)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as ctx:
            setup.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("PreCompact pre-summary (local Laya).", out.getvalue())
        for host in ("claude", "pi", "opencode"):
            self.assertIn(f"{host}: unmeasured (off)", out.getvalue())

    def test_hook_description_gap_verdicts(self):
        rows = []
        for row in setup.HOOK_REGISTRY:
            if row.id == "precompact":
                reason = {"claude": "a" * 24, "pi": "b" * 24,
                          "opencode": "c" * 24}[row.host]
                row = row._replace(verdict="gap: " + reason, default=False)
            rows.append(row)
        with mock.patch.object(setup, "HOOK_REGISTRY", tuple(rows)):
            desc = setup.hook_description("precompact")
        self.assertLessEqual(len(desc), 200)
        for reason in ("a" * 24, "b" * 24, "c" * 24):
            self.assertIn(reason, desc)
        self.assertNotIn("…", desc)


class TestUninstallKeepsNestedUserHook(unittest.TestCase):
    def test_uninstall_keeps_nested_user_hook(self):
        for briefing in (False, True):
            with self.subTest(briefing=briefing):
                tmp = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
                if briefing:
                    event, marker, unwire = (
                        "SessionStart", setup.CLAUDE_HOOK_MARKER,
                        lambda path: setup.unwire_hook_claude(path, False))
                else:
                    row = PRECOMPACT_CLAUDE_ROWS[0]
                    event, marker = row.event, os.path.join(*row.script.split("/"))
                    unwire = lambda path, row=row: setup.unwire_claude_rows(
                        path, [row], False)
                user = {"type": "command", "command": "echo mine"}
                ours = {"type": "command", "command": "python3 -S /old/" + marker}
                only_ours = {"matcher": "only-ours", "hooks": [ours]}
                mixed = {"matcher": "keep", "hooks": [user, ours], "note": "x"}
                settings = _wire_settings(tmp, {"hooks": {event: [only_ours, mixed]}})
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertTrue(unwire(settings))
                entries = _read(settings)["hooks"][event]
                self.assertEqual(entries, [{"matcher": "keep", "hooks": [user],
                                            "note": "x"}])


class TestHookSelectionItems(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.claude = os.path.join(self.tmp, "claude")
        self.env = {"HOME": self.tmp, "AI_KIT_DIR": _REPO,
                    "CLAUDE_CONFIG_DIR": self.claude,
                    "PI_CODING_AGENT_DIR": os.path.join(self.tmp, "pi"),
                    "OPENCODE_CONFIG_DIR": os.path.join(self.tmp, "opencode")}
        self.paths = setup.resolve_paths(self.env)

    def test_hook_selection_items_precheck(self):
        items, initial = setup._hook_selection_items(self.paths)
        self.assertEqual(items, [("hooks", "precompact", False)])
        self.assertFalse(initial[("hooks", "precompact")])
        os.makedirs(self.claude)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(setup.wire_claude_rows(
                self.paths.settings, PRECOMPACT_CLAUDE_ROWS, _REPO, False))
        items, initial = setup._hook_selection_items(self.paths)
        self.assertEqual(items, [("hooks", "precompact", True)])
        self.assertTrue(initial[("hooks", "precompact")])

    def test_hook_selection_prechecks_default_present_host(self):
        os.makedirs(self.claude)
        rows = tuple(row._replace(default=(row.host == "claude"))
                     for row in setup.HOOK_REGISTRY)
        with mock.patch.object(setup, "HOOK_REGISTRY", rows):
            items, initial = setup._hook_selection_items(self.paths)
        self.assertTrue(items[0][2])
        self.assertFalse(initial[("hooks", "precompact")])

    def test_apply_hook_selection_wires_and_unwires(self):
        os.makedirs(self.claude)
        foreign = {"matcher": "manual", "hooks": [{"type": "command",
                                                       "command": "echo foreign"}]}
        with open(self.paths.settings, "w", encoding="utf-8") as handle:
            json.dump({"hooks": {"PreCompact": [foreign]}}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(setup.apply_hook_selection(
                self.paths, {"precompact"}, False, setup.new_counts()))
        data = _read(self.paths.settings)
        self.assertEqual(len(data["hooks"]["PreCompact"]), 2)
        self.assertEqual(len(data["hooks"]["SessionStart"]), 1)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(setup.apply_hook_selection(
                self.paths, set(), False, setup.new_counts()))
        data = _read(self.paths.settings)
        self.assertEqual(data["hooks"]["PreCompact"], [foreign])
        self.assertEqual(data["hooks"]["SessionStart"], [])

    def test_apply_hook_selection_default_hosts_only(self):
        pi = os.path.join(self.tmp, "pi")
        os.makedirs(pi)
        rows = tuple(row._replace(default=(row.host == "pi"))
                     for row in setup.HOOK_REGISTRY)
        with mock.patch.object(setup, "HOOK_REGISTRY", rows), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(setup.apply_hook_selection(
                self.paths, {"precompact"}, False, setup.new_counts()))
        self.assertTrue(os.path.islink(os.path.join(
            pi, "extensions", "ai-kit-precompact.ts")))
        self.assertFalse(os.path.exists(self.paths.settings))


try:
    import textual  # noqa: F401
    HAVE_TEXTUAL = True
except ImportError:
    HAVE_TEXTUAL = False


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestWizardHookRouting(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.env = {"HOME": self.tmp, "AI_KIT_DIR": _REPO,
                    "CLAUDE_CONFIG_DIR": os.path.join(self.tmp, "claude"),
                    "CURSOR_CONFIG_DIR": os.path.join(self.tmp, "cursor"),
                    "PI_CODING_AGENT_DIR": os.path.join(self.tmp, "pi"),
                    "OPENCODE_CONFIG_DIR": os.path.join(self.tmp, "opencode"),
                    "XDG_CONFIG_HOME": os.path.join(self.tmp, "xdg"),
                    "XDG_STATE_HOME": os.path.join(self.tmp, "state")}
        self.paths = setup.resolve_paths(self.env)
        os.makedirs(self.paths.claude_dir)

    def _wizard_app(self):
        tools = os.path.join(_REPO, "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
        import wizard_app
        return wizard_app

    def _context(self):
        entries = setup.enumerate_entries(self.paths.install_dir)
        installed = {cat: set() for cat in setup.CATEGORIES}
        return setup._build_wizard_context(
            self.paths, entries, installed, "{}", self._wizard_app())

    def test_wizard_commit_routes_hooks(self):
        ctx = self._context()
        self.assertIn(["hooks", "precompact", False], ctx.selection.items)
        self.assertEqual(ctx.component_meta["precompact"],
                         setup.hook_description("precompact"))
        ctx.selection.toggle(ctx.selection.items.index(["hooks", "precompact", False]))
        commit = setup._make_wizard_commit(
            self.paths, setup.enumerate_entries(self.paths.install_dir), False,
            setup.new_counts())
        outcome = commit(ctx.selection, ctx.state)
        self.assertTrue(outcome["ok"])
        self.assertIn("PreCompact", outcome["log"])
        self.assertTrue(os.path.isfile(self.paths.settings))

    def test_housekeeping_keeps_hooks_row(self):
        self._context()
        entries = setup.enumerate_entries(self.paths.install_dir)
        housekeeping = setup._make_apply_housekeeping(
            self.paths, entries, [], [], False, setup.new_counts())
        result = housekeeping(False, False)
        self.assertIn(["hooks", "precompact", False], result["selection"].items)
        self.assertFalse(result["initial_enabled"][("hooks", "precompact")])


class TestHookCommandQuoting(unittest.TestCase):
    def test_wire_hook_claude_quotes_script_path(self):
        tmp = tempfile.mkdtemp(prefix="ai kit ")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        settings = _wire_settings(tmp, {})
        wrapper = os.path.join(tmp, "claude_session_start.py")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(setup.wire_hook_claude(settings, wrapper, dry=False))
        command = _read(settings)["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertEqual(command, "python3 -S " + shlex.quote(wrapper))
        self.assertEqual(shlex.split(command), ["python3", "-S", wrapper])


if __name__ == "__main__":
    unittest.main()
