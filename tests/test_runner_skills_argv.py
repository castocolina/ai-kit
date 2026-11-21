"""37-13: lane skills through the runner's --print-argv (SPEC R13)."""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE = os.path.join(REPO_ROOT, "skills", "ai-kit-spec-review", "references", "cross-ai.mjs")
LANE_ID = {
    "claude": "placeholder-model-1", "codex": "placeholder-model-1",
    "copilot": "placeholder-model-1", "cursor": "placeholder-model-1",
    "opencode": "fake/placeholder-model-1", "pi": "fake/placeholder-model-1",
}
BODY = b"# placeholder skill\n\nUse the word placeholder-token-1.\n"
# Filled from Task 1's 37-SPIKE.md rule (Q4: claude name, Q5: copilot path).
EXPECTED_SKILL_FORMS = {
    "claude": {"name": "unverified", "path": "unverified"},
    "copilot": {"name": "unverified", "path": "unverified"},
    "pi": {"name": "unknown", "path": "verified"},
    "cursor": {"name": "unknown", "path": "unknown"},
    "codex": {"name": "unknown", "path": "unknown"},
    "opencode": {"name": "unknown", "path": "unknown"},
}


def _expected(rt, by_name, has_path, fits_root=False) -> str:
    forms = EXPECTED_SKILL_FORMS[rt]
    if by_name and forms['name'] == 'verified':
        return 'applied form=name'
    if has_path and forms['path'] == 'verified' and (rt != 'copilot' or fits_root):
        return 'applied form=path'
    if has_path:
        return 'applied form=prose'
    if rt == 'pi':
        return 'ignored reason=mode_forbids'
    if forms['name'] == 'unverified':
        return 'ignored reason=unverified_form'
    return 'ignored reason=no_form'


class _SkillCase(unittest.TestCase):
    def setUp(self):
        if shutil.which("node") is None:
            self.skipTest("node not on PATH")
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cwd = os.path.realpath(self._tmp.name)

    def _write_skill(self, dir_name, body=BODY, fm_name=None) -> str:
        directory = os.path.join(self.cwd, "skills", dir_name)
        os.makedirs(directory)
        if fm_name is not None:
            body = b"---\nname: " + fm_name.encode() + b"\n---\n" + body
        with open(os.path.join(directory, "SKILL.md"), "wb") as file:
            file.write(body)
        return directory

    def _run(self, *args):
        env = os.environ.copy()
        env.update(HOME=self.cwd, XDG_CONFIG_HOME=os.path.join(self.cwd, "config"),
                   XDG_STATE_HOME=os.path.join(self.cwd, "state"), AI_KIT_REFUSE_REAL_HOME="1")
        return subprocess.run(["node", TEMPLATE, "--print-argv", *args], cwd=self.cwd,
                              capture_output=True, text=True, timeout=60, env=env)

    @staticmethod
    def _argv(proc):
        line = next(line for line in proc.stdout.splitlines() if "\t" in line)
        return json.loads(line.split("\t")[2])

    @staticmethod
    def _skill_lines(proc):
        return [line for line in proc.stderr.splitlines()
                if line.startswith("cross-ai: setting skill=")]

    @staticmethod
    def _block_lines(proc):
        return [line for line in proc.stderr.splitlines()
                if line.startswith("cross-ai: skill-block ")]


class TestSkillForms(_SkillCase):
    def test_pi_path_form(self):
        directory = self._write_skill("placeholder-skill-1")
        for mode in ("review", "exec"):
            with self.subTest(mode=mode):
                args = ("--runtime", "pi", "--model", LANE_ID["pi"], "--mode", mode)
                plain = self._run(*args)
                skill = self._run(*args, "--skill-path", directory)
                self.assertEqual(plain.returncode, 0, plain.stderr)
                self.assertEqual(skill.returncode, 0, skill.stderr)
                self.assertEqual(self._argv(skill)[-2:], ["--skill", os.path.realpath(directory)])
                self.assertEqual(self._argv(plain), self._argv(skill)[:-2])
                self.assertEqual(self._skill_lines(plain), [])
                self.assertEqual(self._skill_lines(skill), [
                    "cross-ai: setting skill=placeholder-skill-1 applied form=path",
                ])
                self.assertEqual(self._block_lines(skill), [])

    def test_prose_hosts_keep_argv(self):
        directory = self._write_skill('placeholder-skill-1')
        digest = hashlib.sha256(BODY).hexdigest()
        block = (f'<skill name="placeholder-skill-1" path="{os.path.realpath(directory)}" '
                 f'sha256="{digest}">\n').encode() + BODY + b'\n</skill>\n'
        for rt in ('claude', 'copilot', 'cursor', 'codex', 'opencode'):
            for mode in ('review', 'exec'):
                with self.subTest(rt=rt, mode=mode):
                    args = ('--runtime', rt, '--model', LANE_ID[rt], '--mode', mode)
                    plain = self._run(*args)
                    skill = self._run(*args, '--skill-path', directory)
                    self.assertEqual(skill.returncode, 0, skill.stderr)
                    self.assertEqual(self._argv(plain), self._argv(skill))
                    self.assertEqual(self._skill_lines(skill), [
                        'cross-ai: setting skill=placeholder-skill-1 '
                        f'{_expected(rt, False, True)}'])
                    self.assertEqual(self._block_lines(skill), [
                        f'cross-ai: skill-block placeholder-skill-1 bytes={len(block)} '
                        f'sha256={digest}'])

    def test_name_only_reasons(self):
        for rt in LANE_ID:
            for mode in ('review', 'exec'):
                with self.subTest(rt=rt, mode=mode):
                    args = ('--runtime', rt, '--model', LANE_ID[rt], '--mode', mode)
                    plain = self._run(*args)
                    skill = self._run(*args, '--skill-name', 'placeholder-skill-1')
                    self.assertEqual(skill.returncode, 0, skill.stderr)
                    self.assertEqual(self._argv(plain), self._argv(skill))
                    self.assertEqual(self._skill_lines(skill), [
                        'cross-ai: setting skill=placeholder-skill-1 '
                        f'{_expected(rt, True, False)}'])
                    self.assertEqual(self._block_lines(skill), [])

    def test_name_and_matching_path_are_one_skill(self):
        first = self._write_skill('placeholder-skill-1')
        other = self._write_skill('other-dir', fm_name='placeholder-skill-3')
        for rt, name, directory in (('pi', 'placeholder-skill-1', first),
                                    ('claude', 'placeholder-skill-3', other)):
            with self.subTest(rt=rt):
                proc = self._run('--runtime', rt, '--model', LANE_ID[rt], '--mode', 'review',
                                 '--skill-name', name, '--skill-path', directory)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(self._skill_lines(proc), [
                    f'cross-ai: setting skill={name} {_expected(rt, True, True)}'])

    def test_copilot_github_skills_layout(self):
        directory = os.path.join(self.cwd, 'proj', '.github', 'skills', 'placeholder-skill-1')
        os.makedirs(directory)
        with open(os.path.join(directory, 'SKILL.md'), 'wb') as file:
            file.write(BODY)
        args = ('--runtime', 'copilot', '--model', LANE_ID['copilot'], '--mode', 'review')
        plain = self._run(*args)
        proc = self._run(*args, '--skill-path', directory)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        expected = _expected('copilot', False, True, fits_root=True)
        self.assertEqual(self._skill_lines(proc), [
            f'cross-ai: setting skill=placeholder-skill-1 {expected}'])
        if expected == 'applied form=path':
            self.assertEqual(self._argv(proc)[-2:], ['--add-dir', os.path.join(self.cwd, 'proj')])
        else:
            self.assertEqual(self._argv(proc), self._argv(plain))

    def test_call_order_and_one_directory_once(self):
        first = self._write_skill('placeholder-skill-1')
        second = self._write_skill('placeholder-skill-2')
        link = os.path.join(self.cwd, 'link')
        os.symlink(first, link)
        proc = self._run('--runtime', 'claude', '--model', LANE_ID['claude'], '--mode', 'review',
                         '--skill-path', second, '--skill-path', first, '--skill-path', link)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._skill_lines(proc), [
            f'cross-ai: setting skill=placeholder-skill-{n} applied form=prose' for n in (2, 1)])
        self.assertEqual([line.split()[2] for line in self._block_lines(proc)],
                         ['placeholder-skill-2', 'placeholder-skill-1'])

    def test_argv_file_lane(self):
        directory = self._write_skill('placeholder-skill-1')
        with open(os.path.join(self.cwd, 'lane.json'), 'w', encoding='utf-8') as file:
            json.dump(['placeholder-cli-1', '--model', '{model}'], file)
        args = ('--runtime', 'placeholder-cli-1', '--argv-file', 'lane.json',
                '--model', LANE_ID['claude'])
        plain = self._run(*args)
        cases = (('--skill-name', 'placeholder-skill-1', 'ignored reason=no_slot'),
                 ('--skill-path', directory, 'applied form=prose'))
        for flag, value, expected in cases:
            with self.subTest(flag=flag):
                proc = self._run(*args, flag, value)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(self._argv(proc), self._argv(plain))
                self.assertEqual(self._skill_lines(proc), [
                    f'cross-ai: setting skill=placeholder-skill-1 {expected}'])

    def test_no_skill_flag_no_line(self):
        proc = self._run('--runtime', 'claude', '--model', LANE_ID['claude'], '--mode', 'review')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._skill_lines(proc), [])
        self.assertEqual(self._block_lines(proc), [])

    def test_size_and_name_boundaries(self):
        directory = self._write_skill('placeholder-skill-1', BODY + b'a' * (65536 - len(BODY)))
        args = ('--runtime', 'claude', '--model', LANE_ID['claude'])
        for flag, value, tail in (('--skill-path', directory, 'applied form=prose'),
                                  ('--skill-name', 'a', 'ignored reason=unverified_form'),
                                  ('--skill-name', 'a' * 64, 'ignored reason=unverified_form')):
            with self.subTest(flag=flag, length=len(value)):
                proc = self._run(*args, flag, value)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertTrue(any(line.endswith(tail) for line in self._skill_lines(proc)))


class TestRunnerSource(unittest.TestCase):
    def test_runner_names_no_host_settings_path(self):
        with open(TEMPLATE, encoding='utf-8') as file:
            text = file.read()
        text = text.split('function hermeticEnv(', 1)[0] + text.split('async function main(', 1)[1]
        banned = ('mcp.json', 'mcp-config.json', '.claude.json', 'opencode.jsonc',
                  '.claude/skills', '.agents/skills', '.copilot/skills', '.config/opencode/skills')
        for line in text.splitlines():
            if not line.strip().startswith(('//', '*')):
                for value in banned:
                    self.assertNotIn(value, line)


class TestSkillUsageErrors(_SkillCase):
    def test_usage_errors_named(self):
        missing = os.path.join(self.cwd, 'missing')
        regular = os.path.join(self.cwd, 'regular')
        with open(regular, 'wb') as file:
            file.write(b'x')
        empty_dir = os.path.join(self.cwd, 'empty-dir')
        os.makedirs(empty_dir)
        empty = self._write_skill('empty', b'')
        invalid = self._write_skill('invalid', b'\xff\xfe')
        bom = self._write_skill('bom', b'\xef\xbb\xbfabc')
        large = self._write_skill('large', b'a' * 65537)
        bad_control = os.path.join(self.cwd, 'bad\x01dir')
        os.makedirs(bad_control)
        bad_name = self._write_skill('Bad Name')
        key = 'sk-' + 'A' * 32
        secret_missing = os.path.join(self.cwd, key)
        secret_dir = os.path.join(self.cwd, key + '-dir')
        os.makedirs(secret_dir)
        with open(os.path.join(secret_dir, 'SKILL.md'), 'wb') as file:
            file.write(b'\xff')
        cases = [('--skill-path', value) for value in
                 (missing, regular, empty_dir, empty, invalid, bom, large, bad_control,
                  bad_name, '', secret_missing, secret_dir)]
        cases += [('--skill-name', value) for value in ('a' * 65, 'Placeholder', '')]
        for flag, value in cases:
            with self.subTest(flag=flag, case=cases.index((flag, value))):
                proc = self._run('--runtime', 'claude', '--model', LANE_ID['claude'], flag, value)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                lines = proc.stderr.splitlines()
                self.assertTrue(any(line.startswith('AIKIT-XAI status=usage') for line in lines))
                self.assertTrue(any(line.startswith('cross-ai: ') and flag in line
                                    for line in lines))
                self.assertNotIn(key, proc.stderr)
