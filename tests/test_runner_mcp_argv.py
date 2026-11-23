"""37-15: lane MCP servers through the runner's --print-argv (SPEC R14)."""

import json
import os
import subprocess
import tempfile
import unittest

from tests.cross_ai_selftest import _real_node_executable

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE = os.path.join(REPO_ROOT, "skills", "ai-kit-spec-review", "references", "cross-ai.mjs")
LANE_ID = {
    "claude": "placeholder-model-1", "codex": "placeholder-model-1",
    "copilot": "placeholder-model-1", "cursor": "placeholder-model-1",
    "opencode": "fake/placeholder-model-1", "pi": "fake/placeholder-model-1",
}
SERVERS = {"placeholder-server-b": {"command": "placeholder-cmd"},
           "placeholder-server-a": {"url": "https://example.invalid/mcp"}}


class _McpCase(unittest.TestCase):
    def setUp(self):
        # The real node: a launcher shim may run itself again under the scratch HOME below.
        node = _real_node_executable()
        if node is None:
            self.skipTest("no real node executable on PATH")
        self.node: str = node
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cwd = os.path.realpath(self._tmp.name)

    def _run(self, *args):
        env = os.environ.copy()
        env.update(HOME=self.cwd, XDG_CONFIG_HOME=os.path.join(self.cwd, "config"),
                   XDG_STATE_HOME=os.path.join(self.cwd, "state"), AI_KIT_REFUSE_REAL_HOME="1")
        return subprocess.run([self.node, TEMPLATE, "--print-argv", *args], cwd=self.cwd,
                              capture_output=True, text=True, timeout=60, env=env)

    @staticmethod
    def _argv(proc):
        line = next(line for line in proc.stdout.splitlines() if "\t" in line)
        return json.loads(line.split("\t")[2])

    @staticmethod
    def _mcp_lines(proc):
        return [line for line in proc.stderr.splitlines()
                if line.startswith("cross-ai: setting mcp=")]

    def _write_mcp(self, doc=None, raw=None, mode=0o600, name="mcp.json") -> str:
        path = os.path.join(self.cwd, name)
        with open(path, "wb") as file:
            file.write(raw if raw is not None else json.dumps(
                {"mcpServers": SERVERS if doc is None else doc}).encode())
        os.chmod(path, mode)
        return name


class TestMcpForms(_McpCase):
    def test_copilot_additional_after_profile(self):
        name = self._write_mcp()
        for mode in ('review', 'exec'):
            with self.subTest(mode=mode):
                args = ('--runtime', 'copilot', '--model', LANE_ID['copilot'], '--mode', mode)
                plain = self._run(*args)
                proc = self._run(*args, '--mcp-config', name)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                argv = self._argv(proc)
                self.assertEqual(argv, [*self._argv(plain),
                    '--additional-mcp-config', '@' + os.path.join(self.cwd, name)])
                if mode == 'review':
                    self.assertLess(argv.index('--disable-builtin-mcps'),
                                    argv.index('--additional-mcp-config'))
                self.assertEqual(self._mcp_lines(proc), [
                    f'cross-ai: setting mcp={server} applied' for server in SERVERS])

    def test_claude_pair_golden(self):
        name = self._write_mcp()
        for mode in ("review", "exec"):
            with self.subTest(mode=mode):
                args = ("--runtime", "claude", "--model", LANE_ID["claude"], "--mode", mode)
                plain = self._run(*args)
                proc = self._run(*args, "--mcp-config", name)
                self.assertEqual(plain.returncode, 0, plain.stderr)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                suffix = ["--mcp-config", os.path.join(self.cwd, name), "--strict-mcp-config"]
                self.assertEqual(self._argv(proc), self._argv(plain) + suffix)
                if mode == "review":
                    self.assertEqual(self._argv(proc), ["-p", "--model", LANE_ID["claude"],
                        "--output-format", "json", "--permission-mode", "plan", *suffix])
                self.assertEqual(self._mcp_lines(proc), [
                    "cross-ai: setting mcp=placeholder-server-b applied",
                    "cross-ai: setting mcp=placeholder-server-a applied",
                ])

    def test_ignored_hosts_keep_argv(self):
        name = self._write_mcp()
        for rt in ('pi', 'codex', 'cursor', 'opencode'):
            for mode in ('exec', 'review'):
                with self.subTest(rt=rt, mode=mode):
                    args = ('--runtime', rt, '--model', LANE_ID[rt], '--mode', mode)
                    plain = self._run(*args)
                    proc = self._run(*args, '--mcp-config', name)
                    reason = ('mode_forbids' if rt == 'pi' and mode == 'review' else
                              'unverified_form' if rt == 'codex' else 'no_form')
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(self._argv(proc), self._argv(plain))
                    self.assertEqual(self._mcp_lines(proc), [
                        f'cross-ai: setting mcp={server} ignored reason={reason}'
                        for server in SERVERS])

    def test_argv_file_lane_no_slot(self):
        name = self._write_mcp()
        with open(os.path.join(self.cwd, 'lane.json'), 'w', encoding='utf-8') as file:
            json.dump(['placeholder-cli-1', '--model', '{model}'], file)
        args = ('--runtime', 'placeholder-cli-1', '--argv-file', 'lane.json',
                '--model', 'placeholder-model-1')
        plain = self._run(*args)
        proc = self._run(*args, '--mcp-config', name)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._argv(proc), self._argv(plain))
        self.assertEqual(self._mcp_lines(proc), [
            f'cross-ai: setting mcp={server} ignored reason=no_slot' for server in SERVERS])

    def test_no_flag_no_line_and_no_approval_flag(self):
        name = self._write_mcp()
        for rt in LANE_ID:
            for mode in ('exec', 'review'):
                with self.subTest(rt=rt, mode=mode):
                    args = ('--runtime', rt, '--model', LANE_ID[rt], '--mode', mode)
                    plain = self._run(*args)
                    proc = self._run(*args, '--mcp-config', name)
                    self.assertEqual(plain.returncode, 0, plain.stderr)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(self._mcp_lines(plain), [])
                    for flag in ('--mcp-config', '--strict-mcp-config', '--additional-mcp-config'):
                        self.assertNotIn(flag, self._argv(plain))
                    if rt == 'cursor' and mode == 'exec':
                        self.assertEqual(self._argv(plain).count('--approve-mcps'), 1)
                        self.assertEqual(self._argv(proc).count('--approve-mcps'), 1)

    def test_values_never_printed(self):
        key = 'sk-' + 'Q' * 40
        name = self._write_mcp({'placeholder-server-b': {'command': 'placeholder-cmd',
            'args': ['--token', key], 'env': {'PLACEHOLDER_TOKEN': key}},
            'placeholder-server-a': {'url': 'https://example.invalid/mcp',
                                     'headers': {'Authorization': 'Bearer ' + key}}})
        for rt, mode in (('claude', 'exec'), ('claude', 'review'), ('copilot', 'exec'),
                         ('copilot', 'review'), ('pi', 'review')):
            with self.subTest(rt=rt, mode=mode):
                proc = self._run('--runtime', rt, '--model', LANE_ID[rt], '--mode', mode,
                                 '--mcp-config', name)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                for value in (key, 'placeholder-cmd', 'example.invalid', 'mcpServers'):
                    self.assertNotIn(value, proc.stdout + proc.stderr)
                self.assertTrue(all(key not in arg for arg in self._argv(proc)))

    def test_boundaries_and_case(self):
        cases = [(b'{"mcpServers":{"a":{},"' + b'a' * 64 + b'":{}}}', ['a', 'a' * 64]),
                 (b'{"mcpServers":{"Placeholder-server-a":{},"placeholder-server-a":{}}}',
                  ['Placeholder-server-a', 'placeholder-server-a']),
                 (b'{"mcpServers":{"2":{},"1":{},"placeholder-server-c":{}}}',
                  ['2', '1', 'placeholder-server-c'])]
        raw = b'{"mcpServers":{"a":{}}}'
        cases.append((raw + b' ' * (65536 - len(raw)), ['a']))
        for raw, names in cases:
            with self.subTest(names=names):
                name = self._write_mcp(raw=raw)
                proc = self._run('--runtime', 'claude', '--model', LANE_ID['claude'],
                                 '--mode', 'review', '--mcp-config', name)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(self._mcp_lines(proc), [
                    f'cross-ai: setting mcp={server} applied' for server in names])

    def test_relative_path_reaches_argv_absolute(self):
        name = self._write_mcp()
        for rt, flag, prefix in (('claude', '--mcp-config', ''),
                                 ('copilot', '--additional-mcp-config', '@')):
            with self.subTest(rt=rt):
                proc = self._run('--runtime', rt, '--model', LANE_ID[rt], '--mcp-config', name)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                argv = self._argv(proc)
                self.assertEqual(argv[argv.index(flag) + 1], prefix + os.path.join(self.cwd, name))


class TestMcpUsageErrors(_McpCase):
    def test_usage_errors_named(self):
        key = 'sk-' + 'Q' * 40
        key_bytes = key.encode()
        cases = [(b'{}', 0o640), (b'{}', 0o604), (b'[]', 0o600), (b'{}', 0o600),
                 (b'{"mcpServers":{}}', 0o600), (b'{"mcpServers":[]}', 0o600),
                 (b'{"mcpServers":{"bad name":{"x":"' + key_bytes + b'"}}}', 0o600),
                 (b'{"mcpServers":{"' + b'a' * 65 + b'":{}}}', 0o600),
                 (b'{"mcpServers":{"a":{},"a":{}}}', 0o600),
                 (b'{"mcpServers":{"a":{"x":1,"x":2}}}', 0o600),
                 (b'{"mcpServers":{"a":{"' + key_bytes + b'":1,"' + key_bytes +
                  b'":2}}}', 0o600),
                 (b'{"mcpServers":{"a":{"token":"' + key_bytes + b'"', 0o600),
                 (b'{', 0o600), (b'{"mcpServers":{"a":{"x":"\xff"}}}', 0o600),
                 (b'\xef\xbb\xbf{"mcpServers":{"a":{}}}', 0o600), (b' ' * 65537, 0o600)]
        paths = [(self._write_mcp(raw=raw, mode=mode, name=f'case-{i}'), i)
                 for i, (raw, mode) in enumerate(cases)]
        os.makedirs(os.path.join(self.cwd, 'directory'))
        paths += [('missing', 16), ('directory', 17), ('', 18)]
        for name, index in paths:
            with self.subTest(case=index):
                proc = self._run('--runtime', 'claude', '--model', LANE_ID['claude'],
                                 '--mcp-config', name)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn('AIKIT-XAI status=usage', proc.stderr)
                self.assertTrue(any(line.startswith('cross-ai: ') and '--mcp-config' in line
                                    for line in proc.stderr.splitlines()))
                self.assertNotIn(key, proc.stdout + proc.stderr)
                if index == 10:
                    self.assertIn('(key not shown)', proc.stderr)
                if index == 11:
                    self.assertIn('(content not shown)', proc.stderr)
