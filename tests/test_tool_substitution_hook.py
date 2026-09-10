import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_SETUP_PATH = os.path.join(_REPO, "tools", "setup.py")
_DETECT_PATH = os.path.join(_REPO, "tools", "hooks", "detect.py")
_WRAPPER_PATH = os.path.join(_REPO, "tools", "hooks", "claude_session_start.py")
_CURSOR_WRAPPER_PATH = os.path.join(_REPO, "tools", "hooks", "cursor_session_start.py")
_PRECOMMIT_PATH = os.path.join(_REPO, ".pre-commit-config.yaml")
_MAKEFILE_PATH = os.path.join(_REPO, "Makefile")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")

_VERIFIED_RTK_SHOW = """\
rtk Configuration:

[ok] Hook: rtk hook claude (native binary command)
[ok] RTK.md: /home/bazzite/.claude/RTK.md (slim mode)
[ok] Global (~/.claude/CLAUDE.md): @RTK.md reference
[--] Local (./CLAUDE.md): not found
[ok] settings.json: RTK hook configured
[ok] OpenCode: plugin installed (/home/bazzite/.config/opencode/plugins/rtk.ts)
[ok] Cursor hook: registered in hooks.json
"""


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_setup():
    return _load("setup", _SETUP_PATH)


def load_detect():
    return _load("detect", _DETECT_PATH)


setup = load_setup()
detect = load_detect()


def fake_bin(root, names, body):
    """Write executable sh stubs named `names` under `root`."""
    os.makedirs(root, exist_ok=True)
    for name in names:
        path = os.path.join(root, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.chmod(path, 0o755)
    return root


def scoped_env(bin_dir, home):
    """Env whose PATH is exactly `bin_dir` and whose XDG dirs sit under `home`."""
    return {
        "PATH": bin_dir,
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "XDG_DATA_HOME": os.path.join(home, ".local", "share"),
        "XDG_CACHE_HOME": os.path.join(home, ".cache"),
    }


def precommit_hook_files_regex(hook_id):
    """Return the `files:` value for `- id: <hook_id>` by reading YAML as text."""
    with open(_PRECOMMIT_PATH, encoding="utf-8") as handle:
        text = handle.read()
    needle = f"- id: {hook_id}"
    start = text.find(needle)
    if start < 0:
        raise AssertionError(f"hook id {hook_id!r} not found in .pre-commit-config.yaml")
    rest = text[start:]
    nxt = rest.find("\n      - id:", len(needle))
    block = rest if nxt < 0 else rest[:nxt]
    match = re.search(r"^\s*files:\s*(\S+)\s*$", block, re.MULTILINE)
    if match is None:
        raise AssertionError(f"no files: value for hook {hook_id!r}")
    return match.group(1).strip().strip("'\"")


def _write_bytes(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(payload)


def _read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def _rtk_stub_body(stdout_text):
    return (
        "#!/bin/sh\n"
        "if [ \"$1\" = init ] && [ \"$2\" = --show ]; then\n"
        "cat <<'EOF'\n"
        f"{stdout_text}"
        "EOF\n"
        "fi\n"
        "exit 0\n"
    )


class TestClaudeWrapper(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.install = os.path.join(self.tmp, "ai-kit")
        self.hooks_dir = os.path.join(self.install, "tools", "hooks")
        os.makedirs(self.hooks_dir)
        shutil.copy(_DETECT_PATH, os.path.join(self.hooks_dir, "detect.py"))
        shutil.copy(_WRAPPER_PATH, os.path.join(self.hooks_dir, "claude_session_start.py"))
        self.wrapper = os.path.join(self.hooks_dir, "claude_session_start.py")
        os.chmod(self.wrapper, 0o755)
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(self.claude)
        self.settings = os.path.join(self.claude, "settings.json")
        self.bin_dir = os.path.join(self.tmp, "bin")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)

    def test_tracer_wired_entry_runs_and_emits_context(self):
        self.assertEqual(len(detect.CURATED_SUBSTITUTIONS), 5)
        foreign = {
            "theme": "dark",
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo foreign"}]},
                ],
            },
        }
        with open(self.settings, "w", encoding="utf-8") as handle:
            json.dump(foreign, handle)
        self.assertTrue(setup.wire_hook_claude(self.settings, self.wrapper, dry=False))
        with open(self.settings, encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(stored["theme"], "dark")
        self.assertEqual(
            stored["hooks"]["SessionStart"][0],
            foreign["hooks"]["SessionStart"][0],
        )
        commands = [
            hook.get("command", "")
            for entry in stored["hooks"]["SessionStart"]
            for hook in entry.get("hooks") or []
        ]
        ours = [c for c in commands if setup.CLAUDE_HOOK_MARKER in c]
        self.assertEqual(len(ours), 1)
        self.assertTrue(ours[0].startswith("python3 -S "))
        script = ours[0][len("python3 -S "):]
        fake_bin(self.bin_dir, ["rtk"], _rtk_stub_body(_VERIFIED_RTK_SHOW))
        fake_bin(self.bin_dir, ["rg"], "#!/bin/sh\nexit 0\n")
        env = scoped_env(self.bin_dir, self.home)
        proc = subprocess.run(
            [sys.executable, "-S", script],
            check=False,
            capture_output=True,
            text=True,
            env=env,
            stdin=subprocess.DEVNULL,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        output = payload["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn("rg", output["additionalContext"])

    def test_partial_stdin_payload_never_wedges(self):
        fake_bin(self.bin_dir, ["rtk"], _rtk_stub_body(_VERIFIED_RTK_SHOW))
        env = scoped_env(self.bin_dir, self.home)
        proc = subprocess.Popen(
            [sys.executable, "-S", self.wrapper],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        try:
            proc.stdin.write(b'{"hook_event_name": "SessionStart"')
            proc.stdin.flush()
            rc = proc.wait(timeout=10)
            self.assertEqual(rc, 0)
            json.loads(proc.stdout.read())
        finally:
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
            if proc.poll() is None:
                proc.kill()
                proc.wait()


class TestWiring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(self.claude)
        self.settings = os.path.join(self.claude, "settings.json")
        self.hook = os.path.join(
            self.tmp, "ai-kit", "tools", "hooks", "claude_session_start.py")

    def _capture_wire(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            result = setup.wire_hook_claude(self.settings, self.hook, dry=False)
        return result, buf.getvalue()

    def test_unparseable_settings_is_refused_not_clobbered(self):
        payload = b"{ this is not json KEEP-ME-12345\n"
        _write_bytes(self.settings, payload)
        before = _read_bytes(self.settings)
        result, err = self._capture_wire()
        self.assertFalse(result)
        self.assertIn(self.settings, err)
        self.assertEqual(_read_bytes(self.settings), before)

    def test_non_dict_settings_is_refused_not_clobbered(self):
        payload = b'[{"hooks": "nope"}]\n'
        _write_bytes(self.settings, payload)
        before = _read_bytes(self.settings)
        result, err = self._capture_wire()
        self.assertFalse(result)
        self.assertIn(self.settings, err)
        self.assertEqual(_read_bytes(self.settings), before)

    def test_non_dict_array_element_is_refused_not_clobbered(self):
        data = {
            "hooks": {
                "SessionStart": [
                    "bare-string-element",
                    {"hooks": [{"type": "command", "command": "echo foreign"}]},
                ],
            },
        }
        with open(self.settings, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
            handle.write("\n")
        before = _read_bytes(self.settings)
        result, err = self._capture_wire()
        self.assertFalse(result)
        self.assertIn(self.settings, err)
        self.assertEqual(_read_bytes(self.settings), before)

    def test_non_dict_nested_hook_member_is_refused_not_clobbered(self):
        data = {
            "hooks": {
                "SessionStart": [
                    {"matcher": "startup", "hooks": "not-a-list"},
                ],
            },
        }
        with open(self.settings, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
            handle.write("\n")
        before = _read_bytes(self.settings)
        result, err = self._capture_wire()
        self.assertFalse(result)
        self.assertIn(self.settings, err)
        self.assertEqual(_read_bytes(self.settings), before)

    def test_atomic_write_failure_leaves_target_byte_identical(self):
        data = {"theme": "dark", "hooks": {"SessionStart": []}}
        with open(self.settings, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
            handle.write("\n")
        before = _read_bytes(self.settings)
        listing = sorted(os.listdir(self.claude))

        def _boom(*_args, **_kwargs):
            raise OSError("injected replace failure")

        with mock.patch.object(os, "replace", side_effect=_boom), self.assertRaises(OSError):
            setup._atomic_write_json(self.settings, {"theme": "other"})
        self.assertEqual(_read_bytes(self.settings), before)
        self.assertEqual(sorted(os.listdir(self.claude)), listing)

        buf = io.StringIO()
        with mock.patch.object(os, "replace", side_effect=_boom), contextlib.redirect_stderr(buf):
            result = setup.wire_hook_claude(self.settings, self.hook, dry=False)
        self.assertFalse(result)
        self.assertTrue(buf.getvalue())
        self.assertEqual(_read_bytes(self.settings), before)
        self.assertEqual(sorted(os.listdir(self.claude)), listing)

    def test_absent_claude_dir_creates_nothing(self):
        missing_dir = os.path.join(self.tmp, "no-such-dir")
        settings = os.path.join(missing_dir, "settings.json")
        before = sorted(os.listdir(self.tmp))
        result = setup.wire_hook_claude(settings, self.hook, dry=False)
        self.assertFalse(result)
        self.assertFalse(os.path.exists(missing_dir))
        self.assertEqual(sorted(os.listdir(self.tmp)), before)

    def test_created_settings_file_is_mode_0600(self):
        self.assertFalse(os.path.isfile(self.settings))
        self.assertTrue(setup.wire_hook_claude(self.settings, self.hook, dry=False))
        mode = stat.S_IMODE(os.stat(self.settings).st_mode)
        self.assertEqual(mode, 0o600)

    def test_wizard_commit_wires_the_hook(self):
        home = tempfile.mkdtemp()
        install = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, install, ignore_errors=True)
        paths = setup.resolve_paths({"HOME": home, "AI_KIT_DIR": install})
        self.assertEqual(
            paths.claude_hook,
            os.path.join(install, "tools", "hooks", "claude_session_start.py"),
        )
        os.makedirs(paths.claude_dir, exist_ok=True)
        entries = {cat: [] for cat in setup.CATEGORIES}
        commit = setup._make_wizard_commit(
            paths, entries, dry=False, counts=setup.new_counts())
        result = commit(setup.Selection([]), {"adopt": False})
        self.assertIn("ok", result)
        self.assertIn("adopt", result)
        self.assertIn("log", result)
        self.assertEqual(set(result), {"ok", "adopt", "log"})
        with open(paths.settings, encoding="utf-8") as handle:
            data = json.load(handle)
        ours = [
            entry
            for entry in data["hooks"]["SessionStart"]
            if any(
                setup.CLAUDE_HOOK_MARKER in hook.get("command", "")
                for hook in entry.get("hooks") or []
            )
        ]
        self.assertEqual(len(ours), 1)

    def test_wizard_abort_leaves_settings_untouched(self):
        install = os.path.join(self.tmp, "ai-kit")
        os.makedirs(os.path.join(install, "skills", "alpha"))
        os.makedirs(os.path.join(install, "tools"))
        with open(os.path.join(install, "skills", "alpha", "SKILL.md"),
                  "w", encoding="utf-8") as handle:
            handle.write("---\nname: alpha\n---\n")
        open(os.path.join(install, "tools", "status-line.py"), "w",
             encoding="utf-8").close()
        with open(os.path.join(install, "tools", "statusline.toml.sample"),
                  "w", encoding="utf-8") as handle:
            handle.write("# recipe\n")
        env = {
            "HOME": self.tmp,
            "AI_KIT_DIR": install,
            "CLAUDE_CONFIG_DIR": self.claude,
            "XDG_CONFIG_HOME": os.path.join(self.tmp, ".config"),
        }
        paths = setup.resolve_paths(env)
        os.makedirs(paths.claude_dir, exist_ok=True)
        seed = {
            "theme": "dark",
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo foreign"}]},
                ],
            },
        }
        with open(paths.settings, "w", encoding="utf-8") as handle:
            json.dump(seed, handle)
            handle.write("\n")
        before = _read_bytes(paths.settings)
        with mock.patch.object(setup, "launch_wizard", return_value=None):
            rc = setup.cmd_install(env, tty=None, dry=False)
        self.assertEqual(rc, 0)
        self.assertEqual(_read_bytes(paths.settings), before)


_GSD_CURSOR_ENTRY = {
    "type": "command",
    "command": (
        '"$(for n in ...node resolution...)" '
        '"/home/bazzite/.cursor/hooks/gsd-cursor-session-start.js"'
    ),
    "gsd-managed": True,
}


def _cursor_hooks_doc(entries=None, version=1, extra=None):
    data = {
        "version": version,
        "hooks": {
            "sessionStart": list(entries if entries is not None else [_GSD_CURSOR_ENTRY]),
        },
    }
    if extra:
        data.update(extra)
    return data


class TestCursorWiring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.cursor = os.path.join(self.tmp, ".cursor")
        os.makedirs(self.cursor)
        self.hooks_json = os.path.join(self.cursor, "hooks.json")
        self.hook = os.path.join(
            self.tmp, "ai-kit", "tools", "hooks", "cursor_session_start.py")

    def _write_hooks(self, data):
        with open(self.hooks_json, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
            handle.write("\n")

    def _capture_wire(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf), contextlib.redirect_stdout(buf):
            result = setup.wire_hook_cursor(self.hooks_json, self.hook, dry=False)
        return result, buf.getvalue()

    def _ours(self, data):
        return [
            entry for entry in data["hooks"]["sessionStart"]
            if setup.CURSOR_HOOK_MARKER in entry.get("command", "")
        ]

    def test_gsd_entry_survives_value_identical(self):
        original = _GSD_CURSOR_ENTRY.copy()
        self._write_hooks(_cursor_hooks_doc())
        result, _ = self._capture_wire()
        self.assertTrue(result)
        with open(self.hooks_json, encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(len(stored["hooks"]["sessionStart"]), 2)
        self.assertEqual(stored["hooks"]["sessionStart"][0], original)

    def test_appended_entry_is_flat_no_matcher(self):
        self._write_hooks(_cursor_hooks_doc())
        self.assertTrue(setup.wire_hook_cursor(self.hooks_json, self.hook, dry=False))
        with open(self.hooks_json, encoding="utf-8") as handle:
            stored = json.load(handle)
        ours = self._ours(stored)
        self.assertEqual(len(ours), 1)
        entry = ours[0]
        self.assertEqual(entry["type"], "command")
        self.assertTrue(entry["command"].startswith("python3 -S "))
        self.assertNotIn("matcher", entry)
        self.assertNotIn("hooks", entry)

    def test_wiring_twice_does_not_duplicate(self):
        self._write_hooks(_cursor_hooks_doc())
        self.assertTrue(setup.wire_hook_cursor(self.hooks_json, self.hook, dry=False))
        self.assertTrue(setup.wire_hook_cursor(self.hooks_json, self.hook, dry=False))
        with open(self.hooks_json, encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(len(stored["hooks"]["sessionStart"]), 2)
        self.assertEqual(len(self._ours(stored)), 1)

    def test_existing_version_1_is_preserved(self):
        self._write_hooks(_cursor_hooks_doc(version=1))
        self.assertTrue(setup.wire_hook_cursor(self.hooks_json, self.hook, dry=False))
        with open(self.hooks_json, encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(stored["version"], 1)

    def test_existing_non_default_version_is_preserved(self):
        self._write_hooks(_cursor_hooks_doc(version=2))
        self.assertTrue(setup.wire_hook_cursor(self.hooks_json, self.hook, dry=False))
        with open(self.hooks_json, encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(stored["version"], 2)

    def test_created_hooks_json_gets_version_1(self):
        self.assertFalse(os.path.isfile(self.hooks_json))
        self.assertTrue(setup.wire_hook_cursor(self.hooks_json, self.hook, dry=False))
        with open(self.hooks_json, encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(stored["version"], 1)
        self.assertEqual(len(self._ours(stored)), 1)

    def test_absent_cursor_dir_creates_nothing(self):
        missing_dir = os.path.join(self.tmp, "no-such-cursor")
        hooks_json = os.path.join(missing_dir, "hooks.json")
        before = sorted(os.listdir(self.tmp))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            result = setup.wire_hook_cursor(hooks_json, self.hook, dry=False)
        self.assertFalse(result)
        self.assertFalse(os.path.exists(missing_dir))
        self.assertEqual(sorted(os.listdir(self.tmp)), before)
        self.assertIn("no cursor dir", buf.getvalue().lower())

    def test_hooks_not_object_is_refused(self):
        self._write_hooks({"version": 1, "hooks": "not-an-object"})
        before = _read_bytes(self.hooks_json)
        result, err = self._capture_wire()
        self.assertFalse(result)
        self.assertIn(self.hooks_json, err)
        self.assertEqual(_read_bytes(self.hooks_json), before)

    def test_session_start_not_array_is_refused(self):
        self._write_hooks({"version": 1, "hooks": {"sessionStart": {"type": "command"}}})
        before = _read_bytes(self.hooks_json)
        result, err = self._capture_wire()
        self.assertFalse(result)
        self.assertIn(self.hooks_json, err)
        self.assertEqual(_read_bytes(self.hooks_json), before)

    def test_unparseable_hooks_json_is_refused_not_clobbered(self):
        payload = b"{ this is not json KEEP-ME-CURSOR-12345\n"
        _write_bytes(self.hooks_json, payload)
        before = _read_bytes(self.hooks_json)
        result, err = self._capture_wire()
        self.assertFalse(result)
        self.assertIn(self.hooks_json, err)
        self.assertEqual(_read_bytes(self.hooks_json), before)

    def test_non_dict_hooks_json_is_refused_not_clobbered(self):
        payload = b'[{"hooks": "nope"}]\n'
        _write_bytes(self.hooks_json, payload)
        before = _read_bytes(self.hooks_json)
        result, err = self._capture_wire()
        self.assertFalse(result)
        self.assertIn(self.hooks_json, err)
        self.assertEqual(_read_bytes(self.hooks_json), before)

    def test_non_dict_array_element_is_refused_not_clobbered(self):
        data = _cursor_hooks_doc(entries=[_GSD_CURSOR_ENTRY, "bare-string-element"])
        self._write_hooks(data)
        before = _read_bytes(self.hooks_json)
        result, err = self._capture_wire()
        self.assertFalse(result)
        self.assertIn(self.hooks_json, err)
        self.assertEqual(_read_bytes(self.hooks_json), before)

    def test_atomic_write_failure_leaves_hooks_json_byte_identical(self):
        self._write_hooks(_cursor_hooks_doc())
        before = _read_bytes(self.hooks_json)
        listing = sorted(os.listdir(self.cursor))

        def _boom(*_args, **_kwargs):
            raise OSError("injected replace failure")

        buf = io.StringIO()
        with mock.patch.object(os, "replace", side_effect=_boom), contextlib.redirect_stderr(buf):
            result = setup.wire_hook_cursor(self.hooks_json, self.hook, dry=False)
        self.assertFalse(result)
        self.assertTrue(buf.getvalue())
        self.assertEqual(_read_bytes(self.hooks_json), before)
        self.assertEqual(sorted(os.listdir(self.cursor)), listing)

    def test_resolve_paths_honours_cursor_config_dir(self):
        paths = setup.resolve_paths({
            "HOME": "/home/u",
            "AI_KIT_DIR": "/opt/kit",
            "CURSOR_CONFIG_DIR": "/cfg/cursor",
        })
        self.assertEqual(paths.cursor_dir, "/cfg/cursor")
        self.assertEqual(paths.cursor_hooks, "/cfg/cursor/hooks.json")
        self.assertEqual(
            paths.cursor_hook,
            "/opt/kit/tools/hooks/cursor_session_start.py",
        )
        defaulted = setup.resolve_paths({"HOME": "/home/u", "AI_KIT_DIR": "/opt/kit"})
        self.assertEqual(defaulted.cursor_dir, "/home/u/.cursor")
        self.assertEqual(defaulted.cursor_hooks, "/home/u/.cursor/hooks.json")

    def test_wizard_commit_wires_cursor_hook(self):
        home = tempfile.mkdtemp()
        install = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, install, ignore_errors=True)
        paths = setup.resolve_paths({"HOME": home, "AI_KIT_DIR": install})
        os.makedirs(paths.claude_dir, exist_ok=True)
        os.makedirs(paths.cursor_dir, exist_ok=True)
        with open(paths.cursor_hooks, "w", encoding="utf-8") as handle:
            json.dump(_cursor_hooks_doc(), handle)
            handle.write("\n")
        original = _GSD_CURSOR_ENTRY.copy()
        entries = {cat: [] for cat in setup.CATEGORIES}
        commit = setup._make_wizard_commit(
            paths, entries, dry=False, counts=setup.new_counts())
        result = commit(setup.Selection([]), {"adopt": False})
        self.assertEqual(set(result), {"ok", "adopt", "log"})
        with open(paths.cursor_hooks, encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(stored["hooks"]["sessionStart"][0], original)
        ours = [
            entry for entry in stored["hooks"]["sessionStart"]
            if setup.CURSOR_HOOK_MARKER in entry.get("command", "")
        ]
        self.assertEqual(len(ours), 1)
        self.assertNotIn("matcher", ours[0])
        self.assertIn("sessionStart", result["log"])


class TestCursorWrapper(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.install = os.path.join(self.tmp, "ai-kit")
        self.hooks_dir = os.path.join(self.install, "tools", "hooks")
        os.makedirs(self.hooks_dir)
        shutil.copy(_DETECT_PATH, os.path.join(self.hooks_dir, "detect.py"))
        shutil.copy(_WRAPPER_PATH, os.path.join(self.hooks_dir, "claude_session_start.py"))
        shutil.copy(
            _CURSOR_WRAPPER_PATH, os.path.join(self.hooks_dir, "cursor_session_start.py"))
        self.claude_wrapper = os.path.join(self.hooks_dir, "claude_session_start.py")
        self.cursor_wrapper = os.path.join(self.hooks_dir, "cursor_session_start.py")
        os.chmod(self.claude_wrapper, 0o755)
        os.chmod(self.cursor_wrapper, 0o755)
        self.cursor = os.path.join(self.tmp, ".cursor")
        os.makedirs(self.cursor)
        self.hooks_json = os.path.join(self.cursor, "hooks.json")
        self.bin_dir = os.path.join(self.tmp, "bin")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)

    def _run(self, script, env):
        return subprocess.run(
            [sys.executable, "-S", script],
            check=False,
            capture_output=True,
            text=True,
            env=env,
            stdin=subprocess.DEVNULL,
        )

    def test_wired_command_emits_additional_context(self):
        with open(self.hooks_json, "w", encoding="utf-8") as handle:
            json.dump(_cursor_hooks_doc(), handle)
        self.assertTrue(
            setup.wire_hook_cursor(self.hooks_json, self.cursor_wrapper, dry=False))
        with open(self.hooks_json, encoding="utf-8") as handle:
            stored = json.load(handle)
        ours = [
            entry["command"] for entry in stored["hooks"]["sessionStart"]
            if setup.CURSOR_HOOK_MARKER in entry.get("command", "")
        ]
        self.assertEqual(len(ours), 1)
        self.assertTrue(ours[0].startswith("python3 -S "))
        script = ours[0][len("python3 -S "):]
        fake_bin(self.bin_dir, ["rtk"], _rtk_stub_body(_VERIFIED_RTK_SHOW))
        fake_bin(self.bin_dir, ["rg"], "#!/bin/sh\nexit 0\n")
        env = scoped_env(self.bin_dir, self.home)
        proc = self._run(script, env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(set(payload), {"additional_context"})
        self.assertIn("rg", payload["additional_context"])

    def test_empty_path_emits_empty_object(self):
        fake_bin(self.bin_dir, [], "#!/bin/sh\nexit 0\n")
        env = scoped_env(self.bin_dir, self.home)
        proc = self._run(self.cursor_wrapper, env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "{}")

    def test_both_hosts_carry_the_same_message(self):
        fake_bin(self.bin_dir, ["rtk"], _rtk_stub_body(_VERIFIED_RTK_SHOW))
        fake_bin(self.bin_dir, ["rg"], "#!/bin/sh\nexit 0\n")
        env = scoped_env(self.bin_dir, self.home)
        claude = self._run(self.claude_wrapper, env)
        cursor = self._run(self.cursor_wrapper, env)
        self.assertEqual(claude.returncode, 0, claude.stderr)
        self.assertEqual(cursor.returncode, 0, cursor.stderr)
        claude_msg = json.loads(claude.stdout)["hookSpecificOutput"]["additionalContext"]
        cursor_msg = json.loads(cursor.stdout)["additional_context"]
        self.assertEqual(claude_msg, cursor_msg)


_FOREIGN_CLAUDE_A = {
    "hooks": [{"type": "command", "command": "echo foreign-a"}],
}
_FOREIGN_CLAUDE_B = {
    "matcher": "startup",
    "hooks": [{"type": "command", "command": "echo foreign-b"}],
}


def _claude_ours(command):
    return {
        "matcher": setup.CLAUDE_HOOK_MATCHER,
        "hooks": [{"type": "command", "command": command}],
    }


class TestUnwire(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        self.cursor = os.path.join(self.tmp, ".cursor")
        os.makedirs(self.claude)
        os.makedirs(self.cursor)
        os.makedirs(os.path.join(self.install, "tools", "hooks"), exist_ok=True)
        self.settings = os.path.join(self.claude, "settings.json")
        self.hooks_json = os.path.join(self.cursor, "hooks.json")
        self.claude_hook = os.path.join(
            self.install, "tools", "hooks", "claude_session_start.py")
        self.cursor_hook = os.path.join(
            self.install, "tools", "hooks", "cursor_session_start.py")
        self.env = {
            "HOME": self.tmp,
            "AI_KIT_DIR": self.install,
            "CLAUDE_CONFIG_DIR": self.claude,
            "CURSOR_CONFIG_DIR": self.cursor,
        }

    def _write_json(self, path, data):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
            handle.write("\n")

    def _claude_cmd(self):
        return "python3 -S " + self.claude_hook

    def _cursor_cmd(self):
        return "python3 -S " + self.cursor_hook

    def _seed_both_wired(self):
        self._write_json(self.settings, {
            "theme": "dark",
            "hooks": {
                "SessionStart": [
                    _FOREIGN_CLAUDE_A,
                    _FOREIGN_CLAUDE_B,
                    _claude_ours(self._claude_cmd()),
                ],
            },
        })
        self._write_json(self.hooks_json, _cursor_hooks_doc(
            entries=[
                _GSD_CURSOR_ENTRY,
                {"type": "command", "command": self._cursor_cmd()},
            ],
            extra={"theme": "dark"},
        ))

    def _capture(self, fn):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            result = fn()
        return result, buf.getvalue()

    def test_foreign_entries_survive_value_identical(self):
        self._seed_both_wired()
        self._capture(lambda: setup.unwire_hook_claude(self.settings, dry=False))
        self._capture(lambda: setup.unwire_hook_cursor(self.hooks_json, dry=False))
        with open(self.settings, encoding="utf-8") as handle:
            claude = json.load(handle)
        with open(self.hooks_json, encoding="utf-8") as handle:
            cursor = json.load(handle)
        self.assertEqual(
            claude["hooks"]["SessionStart"],
            [_FOREIGN_CLAUDE_A, _FOREIGN_CLAUDE_B],
        )
        self.assertEqual(cursor["hooks"]["sessionStart"], [_GSD_CURSOR_ENTRY])
        self.assertTrue(cursor["hooks"]["sessionStart"][0]["gsd-managed"])

    def test_removing_only_entry_leaves_empty_array(self):
        self._write_json(self.settings, {
            "hooks": {"SessionStart": [_claude_ours(self._claude_cmd())]},
        })
        self._write_json(self.hooks_json, _cursor_hooks_doc(
            entries=[{"type": "command", "command": self._cursor_cmd()}],
        ))
        self._capture(lambda: setup.unwire_hook_claude(self.settings, dry=False))
        self._capture(lambda: setup.unwire_hook_cursor(self.hooks_json, dry=False))
        with open(self.settings, encoding="utf-8") as handle:
            claude = json.load(handle)
        with open(self.hooks_json, encoding="utf-8") as handle:
            cursor = json.load(handle)
        self.assertEqual(claude["hooks"]["SessionStart"], [])
        self.assertIn("hooks", claude)
        self.assertEqual(cursor["hooks"]["sessionStart"], [])
        self.assertIn("hooks", cursor)
        self.assertEqual(cursor["version"], 1)

    def test_no_ai_kit_entry_leaves_files_byte_identical(self):
        self._write_json(self.settings, {
            "theme": "dark",
            "hooks": {"SessionStart": [_FOREIGN_CLAUDE_A, _FOREIGN_CLAUDE_B]},
        })
        self._write_json(self.hooks_json, _cursor_hooks_doc())
        claude_before = _read_bytes(self.settings)
        cursor_before = _read_bytes(self.hooks_json)
        self._capture(lambda: setup.unwire_hook_claude(self.settings, dry=False))
        self._capture(lambda: setup.unwire_hook_cursor(self.hooks_json, dry=False))
        self.assertEqual(_read_bytes(self.settings), claude_before)
        self.assertEqual(_read_bytes(self.hooks_json), cursor_before)

    def test_unparseable_configs_are_refused_not_clobbered(self):
        _write_bytes(self.settings, b"{ this is not json KEEP-CLAUDE\n")
        _write_bytes(self.hooks_json, b"{ this is not json KEEP-CURSOR\n")
        claude_before = _read_bytes(self.settings)
        cursor_before = _read_bytes(self.hooks_json)
        _, claude_err = self._capture(
            lambda: setup.unwire_hook_claude(self.settings, dry=False))
        _, cursor_err = self._capture(
            lambda: setup.unwire_hook_cursor(self.hooks_json, dry=False))
        self.assertIn(self.settings, claude_err)
        self.assertIn(self.hooks_json, cursor_err)
        self.assertEqual(_read_bytes(self.settings), claude_before)
        self.assertEqual(_read_bytes(self.hooks_json), cursor_before)

    def test_atomic_write_failure_leaves_target_byte_identical_on_unwire(self):
        self._seed_both_wired()
        claude_before = _read_bytes(self.settings)
        cursor_before = _read_bytes(self.hooks_json)
        claude_listing = sorted(os.listdir(self.claude))
        cursor_listing = sorted(os.listdir(self.cursor))

        def _boom(*_args, **_kwargs):
            raise OSError("injected replace failure")

        buf = io.StringIO()
        with (
            mock.patch.object(os, "replace", side_effect=_boom),
            contextlib.redirect_stdout(buf),
            contextlib.redirect_stderr(buf),
        ):
            setup.unwire_hook_claude(self.settings, dry=False)
            setup.unwire_hook_cursor(self.hooks_json, dry=False)
        self.assertTrue(buf.getvalue())
        self.assertEqual(_read_bytes(self.settings), claude_before)
        self.assertEqual(_read_bytes(self.hooks_json), cursor_before)
        self.assertEqual(sorted(os.listdir(self.claude)), claude_listing)
        self.assertEqual(sorted(os.listdir(self.cursor)), cursor_listing)

    def test_non_dict_array_element_is_refused_on_unwire(self):
        self._write_json(self.settings, {
            "hooks": {
                "SessionStart": [
                    "bare-string-element",
                    _FOREIGN_CLAUDE_A,
                ],
            },
        })
        self._write_json(self.hooks_json, _cursor_hooks_doc(
            entries=[_GSD_CURSOR_ENTRY, "bare-string-element"],
        ))
        claude_before = _read_bytes(self.settings)
        cursor_before = _read_bytes(self.hooks_json)
        _, claude_err = self._capture(
            lambda: setup.unwire_hook_claude(self.settings, dry=False))
        _, cursor_err = self._capture(
            lambda: setup.unwire_hook_cursor(self.hooks_json, dry=False))
        self.assertIn(self.settings, claude_err)
        self.assertIn(self.hooks_json, cursor_err)
        self.assertEqual(_read_bytes(self.settings), claude_before)
        self.assertEqual(_read_bytes(self.hooks_json), cursor_before)
        _, cmd_err = self._capture(
            lambda: setup.cmd_uninstall(self.env, dry=False))
        self.assertIn(self.settings, cmd_err)
        self.assertIn(self.hooks_json, cmd_err)
        self.assertEqual(_read_bytes(self.settings), claude_before)
        self.assertEqual(_read_bytes(self.hooks_json), cursor_before)

    def test_non_dict_nested_hook_member_is_refused_on_unwire(self):
        self._write_json(self.settings, {
            "hooks": {
                "SessionStart": [
                    {"matcher": "startup", "hooks": "not-a-list"},
                ],
            },
        })
        before = _read_bytes(self.settings)
        _, err = self._capture(
            lambda: setup.unwire_hook_claude(self.settings, dry=False))
        self.assertIn(self.settings, err)
        self.assertEqual(_read_bytes(self.settings), before)
        _, cmd_err = self._capture(
            lambda: setup.cmd_uninstall(self.env, dry=False))
        self.assertIn(self.settings, cmd_err)
        self.assertEqual(_read_bytes(self.settings), before)

    def test_missing_configs_create_nothing(self):
        shutil.rmtree(self.claude)
        shutil.rmtree(self.cursor)
        before = sorted(os.listdir(self.tmp))
        self._capture(lambda: setup.unwire_hook_claude(self.settings, dry=False))
        self._capture(lambda: setup.unwire_hook_cursor(self.hooks_json, dry=False))
        self._capture(lambda: setup.cmd_uninstall(self.env, dry=False))
        self.assertFalse(os.path.exists(self.claude))
        self.assertFalse(os.path.exists(self.cursor))
        self.assertEqual(sorted(os.listdir(self.tmp)), before)

    def test_uninstall_twice_is_a_no_op(self):
        self._seed_both_wired()
        rc1, _ = self._capture(lambda: setup.cmd_uninstall(self.env, dry=False))
        self.assertEqual(rc1, 0)
        rc2, err2 = self._capture(lambda: setup.cmd_uninstall(self.env, dry=False))
        self.assertEqual(rc2, 0)
        self.assertNotIn("warn:", err2)
        self.assertNotIn("Traceback", err2)

    def test_other_top_level_keys_survive(self):
        self._seed_both_wired()
        self._capture(lambda: setup.unwire_hook_claude(self.settings, dry=False))
        self._capture(lambda: setup.unwire_hook_cursor(self.hooks_json, dry=False))
        with open(self.settings, encoding="utf-8") as handle:
            claude = json.load(handle)
        with open(self.hooks_json, encoding="utf-8") as handle:
            cursor = json.load(handle)
        self.assertEqual(claude["theme"], "dark")
        self.assertEqual(cursor["theme"], "dark")
        self.assertEqual(cursor["version"], 1)

    def test_dry_writes_nothing(self):
        self._seed_both_wired()
        claude_before = _read_bytes(self.settings)
        cursor_before = _read_bytes(self.hooks_json)
        _, claude_out = self._capture(
            lambda: setup.unwire_hook_claude(self.settings, dry=True))
        _, cursor_out = self._capture(
            lambda: setup.unwire_hook_cursor(self.hooks_json, dry=True))
        self.assertTrue(claude_out)
        self.assertTrue(cursor_out)
        self.assertEqual(_read_bytes(self.settings), claude_before)
        self.assertEqual(_read_bytes(self.hooks_json), cursor_before)

    def test_entry_with_no_hooks_key_is_kept(self):
        no_hooks = {"matcher": "startup"}
        self._write_json(self.settings, {
            "hooks": {
                "SessionStart": [
                    no_hooks,
                    _claude_ours(self._claude_cmd()),
                ],
            },
        })
        self._capture(lambda: setup.unwire_hook_claude(self.settings, dry=False))
        with open(self.settings, encoding="utf-8") as handle:
            claude = json.load(handle)
        self.assertEqual(claude["hooks"]["SessionStart"], [no_hooks])

    def test_cmd_uninstall_removes_ours_keeps_foreign_returns_0(self):
        self._seed_both_wired()
        rc, _ = self._capture(lambda: setup.cmd_uninstall(self.env, dry=False))
        self.assertEqual(rc, 0)
        with open(self.settings, encoding="utf-8") as handle:
            claude = json.load(handle)
        with open(self.hooks_json, encoding="utf-8") as handle:
            cursor = json.load(handle)
        self.assertEqual(
            claude["hooks"]["SessionStart"],
            [_FOREIGN_CLAUDE_A, _FOREIGN_CLAUDE_B],
        )
        self.assertEqual(cursor["hooks"]["sessionStart"], [_GSD_CURSOR_ENTRY])
        self.assertEqual(claude["theme"], "dark")
        self.assertEqual(cursor["version"], 1)


class TestGateRegistration(unittest.TestCase):
    def test_py_compile_regex_matches_hook_scripts(self):
        regex = precommit_hook_files_regex("py-compile")
        self.assertIsNotNone(re.search(regex, "tools/hooks/detect.py"))
        self.assertIsNotNone(
            re.search(regex, "tools/hooks/claude_session_start.py"))
        self.assertIsNotNone(
            re.search(regex, "tools/hooks/cursor_session_start.py"))

    def test_ruff_regex_matches_hook_scripts(self):
        regex = precommit_hook_files_regex("ruff")
        self.assertIsNotNone(re.search(regex, "tools/hooks/detect.py"))
        self.assertIsNotNone(
            re.search(regex, "tools/hooks/claude_session_start.py"))
        self.assertIsNotNone(
            re.search(regex, "tools/hooks/cursor_session_start.py"))

    def test_makefile_lint_compiles_hook_scripts(self):
        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            text = handle.read()
        compile_lines = [
            line for line in text.splitlines()
            if "py_compile" in line and not line.lstrip().startswith("#")
        ]
        self.assertTrue(
            any("tools/hooks" in line for line in compile_lines),
            compile_lines,
        )

    def test_pyright_includes_hook_dir(self):
        with open(_PYPROJECT_PATH, encoding="utf-8") as handle:
            text = handle.read()
        start = text.find("[tool.pyright]")
        self.assertGreaterEqual(start, 0)
        rest = text[start:]
        nxt = re.search(r"\n\[", rest[len("[tool.pyright]"):])
        block = rest if nxt is None else rest[: len("[tool.pyright]") + nxt.start() + 1]
        self.assertIn("tools/hooks", block)

    def test_hook_scripts_need_no_lint_suppression(self):
        with open(_PYPROJECT_PATH, encoding="utf-8") as handle:
            text = handle.read()
        start = text.find("[tool.ruff.lint.per-file-ignores]")
        self.assertGreaterEqual(start, 0)
        rest = text[start:]
        nxt = re.search(r"\n\[", rest[1:])
        block = rest if nxt is None else rest[: nxt.start() + 1]
        self.assertNotIn("tools/hooks", block)
        self.assertIn('"tests/*"', block)


class TestDetect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bin_dir = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin_dir)

    def _detect(self, names=(), rtk_body=None, runner=None):
        if rtk_body is not None:
            fake_bin(self.bin_dir, ["rtk"], rtk_body)
        if names:
            fake_bin(self.bin_dir, names, "#!/bin/sh\nexit 0\n")
        return detect.detect_substitutions(
            search_path=self.bin_dir, runner=runner)

    def test_confirmed_hook_from_verified_block(self):
        result = self._detect(rtk_body=_rtk_stub_body(_VERIFIED_RTK_SHOW))
        self.assertTrue(result["rtk_present"])
        self.assertEqual(result["rtk_hook_signal"], detect.RTK_SIGNAL_CONFIRMED)
        self.assertTrue(result["rtk_hook_active"])

    def test_not_registered_from_inferred_bracket(self):
        # The `[--] Hook: rtk hook claude` form is INFERRED from the `[ok]`/`[--]`
        # bracket convention observed elsewhere in the captured `rtk init --show`
        # output (the `[--] Local (./CLAUDE.md)` line). It was never captured
        # verbatim for the Hook line — the same confidence label `_probe_rtk_hook`
        # carries, applied to its own test fixture.
        body = _rtk_stub_body(
            "rtk Configuration:\n\n[--] Hook: rtk hook claude\n")
        result = self._detect(rtk_body=body)
        self.assertEqual(
            result["rtk_hook_signal"], detect.RTK_SIGNAL_NOT_REGISTERED)
        self.assertFalse(result["rtk_hook_active"])

    def test_reformat_is_unreadable(self):
        body = _rtk_stub_body("rtk Configuration:\nno hook line at all\n")
        result = self._detect(rtk_body=body)
        self.assertEqual(result["rtk_hook_signal"], detect.RTK_SIGNAL_UNREADABLE)
        self.assertFalse(result["rtk_hook_active"])

    def test_nonzero_exit_is_unreadable(self):
        body = "#!/bin/sh\nexit 1\n"
        result = self._detect(rtk_body=body)
        self.assertEqual(result["rtk_hook_signal"], detect.RTK_SIGNAL_UNREADABLE)
        self.assertFalse(result["rtk_hook_active"])

    def test_hanging_rtk_returns_within_budget(self):
        body = "#!/bin/sh\nsleep 30\n"
        started = time.monotonic()
        result = self._detect(rtk_body=body)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 5)
        self.assertEqual(result["rtk_hook_signal"], detect.RTK_SIGNAL_UNREADABLE)

    def test_absent_rtk_spawns_no_subprocess(self):
        calls = []

        def runner(*_args, **_kwargs):
            calls.append(True)
            raise AssertionError("runner must not be called when rtk is absent")

        result = self._detect(runner=runner)
        self.assertFalse(result["rtk_present"])
        self.assertEqual(result["rtk_hook_signal"], detect.RTK_SIGNAL_ABSENT)
        self.assertEqual(calls, [])

    def test_only_rg_and_eza_installed(self):
        result = self._detect(names=["rg", "eza"])
        installed = [(p["legacy"], p["modern"], p["installed"]) for p in result["pairs"]]
        self.assertEqual(
            installed,
            [
                ("cat", "bat", False),
                ("grep", "rg", True),
                ("find", "fd", False),
                ("sed", "sd", False),
                ("ls", "eza", True),
            ],
        )

    def test_legacy_binaries_are_not_a_substitution_signal(self):
        result = self._detect(names=["grep", "cat", "sed"])
        self.assertTrue(all(not p["installed"] for p in result["pairs"]))

    def test_probe_never_uses_a_shell(self):
        with open(_DETECT_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("shell=True", source)
        self.assertNotIn("shell = True", source)
        self.assertIn("[rtk_path, \"init\", \"--show\"]", source)

    def test_search_path_never_reads_os_environ(self):
        fake_bin(self.bin_dir, ["rg"], "#!/bin/sh\nexit 0\n")
        with mock.patch.dict(os.environ, {"PATH": "/definitely-not-this"}, clear=False):
            result = detect.detect_substitutions(search_path=self.bin_dir)
        installed = {p["modern"]: p["installed"] for p in result["pairs"]}
        self.assertTrue(installed["rg"])
        self.assertFalse(installed["bat"])
        self.assertFalse(result["rtk_present"])


def _pair(legacy, modern, installed):
    return {"legacy": legacy, "modern": modern, "installed": installed}


def _pairs(*moderns):
    wanted = set(moderns)
    return [
        _pair(legacy, modern, modern in wanted)
        for legacy, modern in detect.CURATED_SUBSTITUTIONS
    ]


def _detection(*, present=False, active=False, signal=None, moderns=()):
    if signal is None:
        if active:
            signal = detect.RTK_SIGNAL_CONFIRMED
        elif present:
            signal = detect.RTK_SIGNAL_NOT_REGISTERED
        else:
            signal = detect.RTK_SIGNAL_ABSENT
    return {
        "rtk_present": present,
        "rtk_hook_active": active,
        "rtk_hook_signal": signal,
        "pairs": _pairs(*moderns),
    }


class TestCompose(unittest.TestCase):
    def test_all_five_with_rewrite(self):
        moderns = tuple(m for _, m in detect.CURATED_SUBSTITUTIONS)
        msg = detect.compose_message(
            _detection(present=True, active=True, moderns=moderns))
        lines = msg.split("\n")
        self.assertEqual(len(lines), 6)
        self.assertIn("rewrites", lines[0])
        self.assertNotIn("truncat", lines[0].lower())
        for index, (legacy, modern) in enumerate(detect.CURATED_SUBSTITUTIONS, start=1):
            self.assertTrue(
                lines[index].startswith(f"- {modern} ({legacy}-class):"),
                lines[index],
            )

    def test_only_rg_omits_other_tools(self):
        msg = detect.compose_message(
            _detection(present=True, active=True, moderns=("rg",)))
        lines = msg.split("\n")
        self.assertEqual(len(lines), 2)
        self.assertIn("rewrites", lines[0])
        self.assertIn("rg", lines[1])
        for name in ("bat", "fd", "sd", "eza"):
            self.assertNotIn(name, msg)

    def test_rtk_absent_returns_no_rewrite_claim(self):
        msg = detect.compose_message(
            _detection(present=False, active=False, moderns=("rg", "fd", "eza")))
        lines = msg.split("\n")
        self.assertEqual(len(lines), 4)
        self.assertIn("no rtk rewrite is confirmed active", lines[0].lower())
        self.assertNotIn("rewrites", lines[0])
        self.assertIn("rg", msg)
        self.assertIn("fd", msg)
        self.assertIn("eza", msg)

    def test_unreadable_matches_absent(self):
        moderns = ("rg", "fd", "eza")
        absent = detect.compose_message(
            _detection(present=False, active=False, moderns=moderns))
        unread = detect.compose_message(_detection(
            present=True,
            active=False,
            signal=detect.RTK_SIGNAL_UNREADABLE,
            moderns=moderns,
        ))
        self.assertEqual(unread, absent)

    def test_rtk_present_but_not_registered_makes_no_rewrite_claim(self):
        moderns = ("rg", "fd", "eza")
        absent = detect.compose_message(
            _detection(present=False, active=False, moderns=moderns))
        unregistered = detect.compose_message(_detection(
            present=True,
            active=False,
            signal=detect.RTK_SIGNAL_NOT_REGISTERED,
            moderns=moderns,
        ))
        self.assertEqual(unregistered, absent)
        self.assertIn("no rtk rewrite is confirmed active", unregistered.lower())
        self.assertNotIn("rewrites", unregistered.split("\n")[0])

    def test_absent_and_no_binaries_is_empty(self):
        self.assertEqual(
            detect.compose_message(_detection(present=False, active=False)),
            "",
        )

    def test_active_with_no_binaries_is_rewrite_only(self):
        msg = detect.compose_message(
            _detection(present=True, active=True))
        self.assertIn("rewrites", msg)
        self.assertEqual(msg.count("\n"), 0)
        for name in ("bat", "rg", "fd", "sd", "eza"):
            self.assertNotIn(name, msg)

    def test_message_stays_compact(self):
        moderns = tuple(m for _, m in detect.CURATED_SUBSTITUTIONS)
        msg = detect.compose_message(
            _detection(present=True, active=True, moderns=moderns))
        self.assertLessEqual(len(msg.split("\n")), 7)
        self.assertLessEqual(len(msg), 800)
        self.assertFalse(msg.endswith("\n"))

    def test_probe_output_never_reaches_message(self):
        marker = "PLANTED-MARKER-DO-NOT-LEAK-xyzzy"
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        bin_dir = os.path.join(tmp, "bin")
        fake_bin(bin_dir, ["rtk"], _rtk_stub_body(
            _VERIFIED_RTK_SHOW + f"\n{marker}\n"))
        fake_bin(bin_dir, ["rg"], "#!/bin/sh\nexit 0\n")
        detection = detect.detect_substitutions(search_path=bin_dir)
        msg = detect.compose_message(detection)
        self.assertNotIn(marker, msg)
        self.assertTrue(msg)

    def test_message_is_host_agnostic(self):
        moderns = tuple(m for _, m in detect.CURATED_SUBSTITUTIONS)
        msg = detect.compose_message(
            _detection(present=True, active=True, moderns=moderns)).lower()
        for host in ("claude", "cursor", "opencode", "codex"):
            self.assertNotIn(host, msg)

    def test_malformed_detection_returns_empty(self):
        self.assertEqual(detect.compose_message({}), "")
        self.assertEqual(detect.compose_message({"pairs": "nope"}), "")
        self.assertEqual(detect.compose_message(None), "")

    def test_empty_path_wrapper_emits_empty_object(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        bin_dir = os.path.join(tmp, "bin")
        os.makedirs(bin_dir)
        env = scoped_env(bin_dir, tmp)
        proc = subprocess.run(
            [sys.executable, "-S", _WRAPPER_PATH],
            check=False,
            capture_output=True,
            text=True,
            env=env,
            stdin=subprocess.DEVNULL,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "{}")


class TestHostCoverageDocs(unittest.TestCase):
    def test_hooks_readme_exists(self):
        path = os.path.join(_REPO, "tools", "hooks", "README.md")
        self.assertTrue(os.path.isfile(path), path)

    def test_hooks_readme_has_required_headings(self):
        path = os.path.join(_REPO, "tools", "hooks", "README.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("## What these hooks do", text)
        self.assertIn("## Host coverage", text)
        self.assertIn("## Non-goals", text)

    def test_hooks_readme_names_opencode(self):
        path = os.path.join(_REPO, "tools", "hooks", "README.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("opencode", text.lower())

    def test_detect_docstring_names_opencode(self):
        with open(_DETECT_PATH, encoding="utf-8") as handle:
            text = handle.read()
        module_doc = text.split('"""', 2)[1]
        self.assertIn("opencode", module_doc.lower())

