"""0b-9 / 38.1 D-30 (37-02): every flag a runner row names is in the recorded help of the command that takes it, and the recorded help carries no personal data."""  # noqa: E501

import json
import os
import pwd
import re
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import secret_shapes

from tests.test_opencode_help_flags import extract_flags

REPO = Path(__file__).resolve().parents[1]
HELP_ROOT = REPO / "tests" / "fixtures" / "cli_help"
TEMPLATE = REPO / "skills" / "ai-kit-spec-review" / "references" / "cross-ai.mjs"
ROW_RX = re.compile(r"^  ([a-z][a-z0-9-]*): \{$")
SUB_RX = re.compile(r"\[\s*'(exec|run|models)'(\s*,\s*'resume')?")
HOME_RX = re.compile(r"/(?:home|Users)/(?!user/)[^/\s]+/")
MAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
GENERIC_LOGINS = frozenset({"root", "user", "runner", "ubuntu", "admin", "node", "vscode"})
BINARIES = {
    "claude": "claude", "codex": "codex", "copilot": "copilot", "cursor": "cursor-agent",
    "opencode": "opencode", "pi": "pi",
}
# Effort, session, context, skill and MCP forms of R3, R7, R13, R14 and 0b-7,
# plus formula flags, per the help of the command that takes them.
KNOWN_FORM_FLAGS = {
    "claude": {"help.txt": ("--effort", "--resume", "--session-id", "--mcp-config",
                            "--strict-mcp-config", "--permission-mode",
                            "--dangerously-skip-permissions", "--output-format", "--model")},
    "codex": {"help.txt": ("--config",),
              "exec-help.txt": ("--json", "--sandbox", "--skip-git-repo-check")},
    "copilot": {"help.txt": ("--reasoning-effort", "--session-id", "--context",
                             "--additional-mcp-config", "--add-dir", "--disable-builtin-mcps",
                             "--model")},
    "cursor": {"help.txt": ("--resume", "--approve-mcps", "--output-format", "--model",
                            "--workspace", "--mode")},
    "opencode": {"help.txt": ("--session",),
                 "run-help.txt": ("--session", "--model", "--format", "--agent")},
    "pi": {"help.txt": ("--thinking", "--session-id", "--skill", "--no-skills", "--no-mcp",
                        "--model")},
}


def runner_rows(template_text: str) -> dict[str, str]:
    lines = template_text.splitlines()
    try:
        start = lines.index("const RUNTIMES = {")
        end = lines.index("};", start + 1)
    except ValueError as exc:
        raise AssertionError("RUNTIMES block not found") from exc
    rows = {}
    for index in range(start + 1, end):
        match = ROW_RX.match(lines[index].rstrip())
        if match:
            first = index
            while first > start and lines[first - 1].startswith("  //"):
                first -= 1
            last = next(i for i in range(index + 1, end) if lines[i].rstrip() == "  },")
            rows[match.group(1)] = "\n".join(lines[first : last + 1])
    return rows


def help_flags(path: Path) -> set[str] | None:
    return extract_flags(path.read_text(encoding="utf-8")) if path.is_file() else None


def formula_contexts(block: str) -> dict[str, set[str]]:
    contexts: dict[str, set[str]] = {}
    spans = []
    for match in SUB_RX.finditer(block):
        depth = 0
        for index in range(match.start(), len(block)):
            if block[index] == "[":
                depth += 1
            elif block[index] == "]":
                depth -= 1
                if depth == 0:
                    break
        else:
            raise AssertionError("unclosed formula array")
        name = "exec-resume-help.txt" if match.group(2) else f"{match.group(1)}-help.txt"
        contexts.setdefault(name, set()).update(extract_flags(block[match.start() : index + 1]))
        spans.append((match.start(), index + 1))
    rest = block
    for first, last in reversed(spans):
        rest = rest[:first] + rest[last:]
    commands = set(contexts) - {"models-help.txt"}
    for line in rest.splitlines():
        name = "help.txt"
        if len(commands) == 1 and line.strip().startswith("resume:") and "[mode](" in line:
            name = next(iter(commands))
        contexts.setdefault(name, set()).update(extract_flags(line))
    return {name: flags for name, flags in contexts.items() if flags}


def host_problems(rows: dict[str, str], help_root: Path) -> list[str]:
    problems = []
    for host, block in sorted(rows.items()):
        if not (help_root / host / "help.txt").is_file():
            problems.append(f"{host}: no recorded help under tests/fixtures/cli_help/{host}/")
            continue
        for name, named in sorted(formula_contexts(block).items()):
            recorded = help_flags(help_root / host / name)
            if recorded is None:
                problems.append(
                    f"{host}: no recorded {name} under tests/fixtures/cli_help/{host}/ "
                    f"for {', '.join(sorted(named))}"
                )
            elif missing := sorted(named - recorded):
                problems.append(f"{host}: {name} lacks {', '.join(missing)}")
    return problems


def machine_identity() -> tuple[str, str]:
    entry = pwd.getpwuid(os.getuid())
    return entry.pw_dir, entry.pw_name


def scrub_problems(name: str, text: str, identity: tuple[str, str] | None = None) -> list[str]:
    problems = []
    if HOME_RX.search(text):
        problems.append(f"{name}: home path")
    home, login = identity or machine_identity()
    if len(home) > 1 and home in text:
        problems.append(f"{name}: this machine's home directory")
    if len(login) >= 4 and login not in GENERIC_LOGINS and re.search(
        rf"(?<![\w-]){re.escape(login)}(?![\w-])", text
    ):
        problems.append(f"{name}: this machine's login name")
    if MAIL_RX.search(text):
        problems.append(f"{name}: account or e-mail address")
    shapes = secret_shapes.detect(text)
    if shapes:
        problems.append(f"{name}: key shape {', '.join(shapes)}")
    return problems


def fixture_files() -> list[Path]:
    return sorted(p for p in HELP_ROOT.rglob("*") if p.is_file())


def command_file(command: str, binary: str) -> str:
    words = command.split()
    if not words or words[0] != binary:
        raise AssertionError(f"{command}: not a {binary} command")
    if words[1:] == ["--version"]:
        return "version.txt"
    if words[1:] == ["--help"]:
        return "help.txt"
    if len(words) > 2 and words[-1] == "--help":
        return "-".join(words[1:-1]) + "-help.txt"
    raise AssertionError(f"{command}: not a recorded help or version command")


class TestRowFlagsRecorded(unittest.TestCase):
    def test_every_row_flag_is_recorded(self):
        rows = runner_rows(TEMPLATE.read_text(encoding="utf-8"))
        self.assertTrue({"claude", "codex", "copilot", "cursor", "opencode", "pi"} <= set(rows))
        self.assertEqual(host_problems(rows, HELP_ROOT), [])

    def test_fixtures_carry_no_personal_data(self):
        files = fixture_files()
        self.assertTrue(files)
        problems = [problem for path in files for problem in scrub_problems(
            str(path.relative_to(REPO)), path.read_text(encoding="utf-8")
        )]
        self.assertEqual(problems, [])


class TestFlagCheckNonVacuity(unittest.TestCase):
    def test_planted_stale_flag_fails(self):
        rows = runner_rows(TEMPLATE.read_text(encoding="utf-8"))
        problems = host_problems(
            {"claude": rows["claude"] + "\n    // --placeholder-stale-flag"}, HELP_ROOT
        )
        self.assertEqual(problems, ["claude: help.txt lacks --placeholder-stale-flag"])

    def test_missing_record_fails(self):
        block = "  placeholder-cli-1: {\n    bins: ['placeholder-cli-1'],\n  },"
        self.assertEqual(
            host_problems({"placeholder-cli-1": block}, HELP_ROOT),
            ["placeholder-cli-1: no recorded help under "
             "tests/fixtures/cli_help/placeholder-cli-1/"],
        )

    def test_flag_checked_against_its_own_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host = root / "placeholder-cli-1"
            host.mkdir()
            (host / "help.txt").write_text("--top-only", encoding="utf-8")
            (host / "run-help.txt").write_text("--run-only", encoding="utf-8")
            def check(block):
                return host_problems({"placeholder-cli-1": block}, root)

            self.assertEqual(
                check("exec: (m) => ['run', '--top-only'],"),
                ["placeholder-cli-1: run-help.txt lacks --top-only"],
            )
            block = ("exec: (m) => ['run', '--run-only'],\n"
                     "    resume: (m, c, sid, mode) => "
                     "[...RUNTIMES.placeholder-cli-1[mode](m, c), '--run-only', sid],")
            self.assertEqual(check(block), [])
            self.assertEqual(
                check("exec: (m) => ['exec', 'resume', '--run-only'],"),
                ["placeholder-cli-1: no recorded exec-resume-help.txt under "
                 "tests/fixtures/cli_help/placeholder-cli-1/ for --run-only"],
            )

    def test_span_keeps_nested_arrays_and_line_breaks(self):
        block = ("  x: {\n    resume: (m, c, sid, mode) => ['exec', 'resume', "
                 "...(mode === 'exec' ? ['--a-flag'] : []),\n      '--b-flag', sid],\n"
                 "    list: { argv: ['models'] },\n  },")
        self.assertEqual(
            formula_contexts(block), {"exec-resume-help.txt": {"--a-flag", "--b-flag"}}
        )

    def test_partial_token_flag_is_its_own_flag(self):
        self.assertEqual(extract_flags("--skill-path d --skill x"), {"--skill-path", "--skill"})
        self.assertEqual(
            host_problems({"pi": "  pi: {\n    flag: '--skill-path',\n  },"}, HELP_ROOT),
            ["pi: help.txt lacks --skill-path"],
        )

    def test_row_discovery_reads_nested_forms(self):
        text = ("const RUNTIMES = {\n  // seed: placeholder\n  placeholder-cli-1: {\n"
                "    forms: {\n      effort: { flag: '--effort' },\n    },\n  },\n"
                "  placeholder-cli-2: {\n    bins: [],\n  },\n};\n")
        rows = runner_rows(text)
        self.assertEqual(list(rows), ["placeholder-cli-1", "placeholder-cli-2"])
        self.assertTrue(rows["placeholder-cli-1"].startswith("  // seed: placeholder"))
        self.assertIn("--effort", rows["placeholder-cli-1"])
        with self.assertRaises(AssertionError):
            runner_rows("not a table")

    def test_fixture_dirs_match_runner_rows(self):
        rows = runner_rows(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(sorted(p.name for p in HELP_ROOT.iterdir() if p.is_dir()), sorted(rows))


class TestScrubNonVacuity(unittest.TestCase):
    def test_home_paths_and_identity_flagged(self):
        identity = ("/srv/placeholder-home", "placeholderlogin")
        for text in ("see /home/someone/projects", "see /Users/someone/x"):
            self.assertEqual(scrub_problems("x", text, identity), ["x: home path"])
        self.assertEqual(scrub_problems("x", "for example /home/user/projects", identity), [])
        self.assertEqual(
            scrub_problems("x", "in /srv/placeholder-home/a", identity),
            ["x: this machine's home directory"],
        )
        self.assertEqual(
            scrub_problems("x", "made by placeholderlogin", identity),
            ["x: this machine's login name"],
        )
        self.assertEqual(scrub_problems("x", "the runner", ("/srv/h", "runner")), [])

    def test_account_and_key_shape_flagged_without_echo(self):
        identity = ("/srv/h", "placeholderlogin")
        self.assertEqual(
            scrub_problems("x", "write to someone@example.com", identity),
            ["x: account or e-mail address"],
        )
        key = "sk-" + "A" * 24
        problems = scrub_problems("x", "token " + key, identity)
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("x: key shape "))
        self.assertTrue(all(key not in problem for problem in problems))


class TestRecordedHelpMeta(unittest.TestCase):
    def test_meta_and_version(self):
        for host in sorted(BINARIES):
            with self.subTest(host=host):
                directory = HELP_ROOT / host
                meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
                self.assertRegex(meta["version"], r"^\d+\.\d+\.\d+$")
                self.assertRegex(meta["recorded"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertIsInstance(meta["commands"], list)
                self.assertTrue(meta["commands"])
                self.assertTrue(all(isinstance(item, str) for item in meta["commands"]))
                self.assertIn(
                    meta["version"], (directory / "version.txt").read_text(encoding="utf-8")
                )

    def test_command_file_names(self):
        for command, binary, expected in (
            ("claude --help", "claude", "help.txt"),
            ("claude --version", "claude", "version.txt"),
            ("codex exec resume --help", "codex", "exec-resume-help.txt"),
            ("cursor-agent --help", "cursor-agent", "help.txt"),
        ):
            self.assertEqual(command_file(command, binary), expected)
        for command, binary in (("codex exec", "codex"), ("pi --help", "claude")):
            with self.assertRaises(AssertionError):
                command_file(command, binary)

    def test_meta_commands_name_every_file(self):
        for host in sorted(BINARIES):
            with self.subTest(host=host):
                directory = HELP_ROOT / host
                meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
                expected = {command_file(c, BINARIES[host]) for c in meta["commands"]}
                expected.add("meta.json")
                self.assertEqual({p.name for p in directory.iterdir() if p.is_file()}, expected)

    def test_known_form_flags_recorded(self):
        for host in sorted(BINARIES):
            with self.subTest(host=host):
                for name, flags in KNOWN_FORM_FLAGS[host].items():
                    recorded = help_flags(HELP_ROOT / host / name)
                    self.assertIsNotNone(recorded)
                    assert recorded is not None
                    self.assertEqual(sorted(set(flags) - recorded), [])


if __name__ == "__main__":
    unittest.main()
