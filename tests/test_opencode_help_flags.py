"""SPEC R9: keep opencode profile and runner flags grounded in recorded host help."""

import os
import re
import sys
import unittest
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

REPO = Path(__file__).resolve().parents[1]
HELP_DIR = REPO / "tests" / "fixtures" / "cli_help" / "opencode"
PROFILE = REPO / "skills" / "ai-kit-spec-review" / "references" / "cli-profiles" / "opencode.md"
TEMPLATE = REPO / "skills" / "ai-kit-spec-review" / "references" / "cross-ai.mjs"
FLAG_RX = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*(?![\w-])")


def extract_flags(text) -> set:
    return set(FLAG_RX.findall(text))


def recorded_flags() -> set:
    flags = set()
    for name in ("help.txt", "run-help.txt", "models-help.txt"):
        flags.update(extract_flags((HELP_DIR / name).read_text(encoding="utf-8")))
    return flags


def help_flags(name) -> set:
    return extract_flags((HELP_DIR / name).read_text(encoding="utf-8"))


def command_flags(text) -> dict:
    result = {"run": set(), "models": set()}
    for match in re.finditer(r"\[\s*'(run|models)'([^\]]*)\]", text):
        result[match.group(1)].update(extract_flags(match.group(2)))
    for match in re.finditer(r"opencode (run|models)\b([^\n\x60]*)", text):
        result[match.group(1)].update(extract_flags(match.group(2)))
    for line in text.splitlines():
        if line.strip().startswith("resume:"):
            result["run"].update(extract_flags(line))
    return result


def negative_claims(text) -> list:
    claims = []
    pattern = re.compile(
        r"\b(run|models)\b[^.]*?\b(?:has|takes|accepts) no (?:such flag|(--[a-z][a-z0-9-]*))"
    )
    for match in pattern.finditer(text):
        flag = match.group(2)
        if flag is None:
            prior = FLAG_RX.findall(text[: match.start()])
            if not prior:
                continue
            flag = prior[-1]
        claims.append((match.group(1), flag))
    return claims


def runner_opencode_text(template_text) -> str:
    lines = template_text.splitlines()
    for index, line in enumerate(lines):
        if line.rstrip() != "  opencode: {":
            continue
        start = index
        while start and lines[start - 1].startswith("  //"):
            start -= 1
        for end in range(index + 1, len(lines)):
            if lines[end].rstrip() == "  },":
                return "\n".join(lines[start : end + 1])
    raise AssertionError("opencode block not found")


def missing_flags(named, recorded) -> list:
    return sorted(set(named) - set(recorded))


class TestOpencodeHelpFlags(unittest.TestCase):
    def test_fixture_records_version(self):
        import json

        meta = json.loads((HELP_DIR / "meta.json").read_text(encoding="utf-8"))
        self.assertRegex(meta["version"], r"^\d+\.\d+\.\d+$")
        self.assertRegex(meta["recorded"], r"^\d{4}-\d{2}-\d{2}$")
        version_text = (HELP_DIR / "version.txt").read_text(encoding="utf-8")
        self.assertIn(meta["version"], version_text, msg="version.txt lacks meta.json version")

    def test_fixture_holds_known_flags(self):
        recorded = recorded_flags()
        expected = {
            "--standalone", "--server", "--auto", "--continue", "--session",
            "--model", "--agent", "--format", "--help", "--version",
        }
        missing = missing_flags(expected, recorded)
        self.assertEqual(missing, [], msg=f"recorded help is missing flags: {missing}")

    def test_profile_flags_in_help(self):
        named = extract_flags(PROFILE.read_text(encoding="utf-8"))
        missing = missing_flags(named, recorded_flags())
        self.assertEqual(missing, [], msg=f"{PROFILE} names unrecorded flags: {missing}")

    def test_runner_flags_in_help(self):
        block = runner_opencode_text(TEMPLATE.read_text(encoding="utf-8"))
        named = extract_flags(block)
        missing = missing_flags(named, recorded_flags())
        self.assertEqual(
            missing, [], msg=f"{TEMPLATE} opencode block names unrecorded flags: {missing}"
        )
        self.assertIn("'--standalone'", block, msg=f"{TEMPLATE} opencode block lost --standalone")

    def test_planted_stale_flag_fails(self):
        self.assertEqual(missing_flags({"--verbose"}, recorded_flags()), ["--verbose"])

    def test_whole_token(self):
        recorded = {"--standalone"}
        self.assertEqual(extract_flags("--session-id x --session y"), {"--session-id", "--session"})
        missing = missing_flags(extract_flags("use --standalone-x"), recorded)
        self.assertEqual(missing, ["--standalone-x"])

    def test_empty_profile_passes(self):
        self.assertEqual(missing_flags(extract_flags("no flags here"), recorded_flags()), [])

    def test_run_flags_in_run_or_global_help(self):
        text = runner_opencode_text(TEMPLATE.read_text(encoding="utf-8"))
        profile = PROFILE.read_text(encoding="utf-8")
        named = command_flags(text)["run"] | command_flags(profile)["run"]
        allowed = help_flags("run-help.txt") | help_flags("help.txt")
        self.assertEqual(missing_flags(named, allowed), [])

    def test_models_flags_in_models_or_global_help(self):
        text = runner_opencode_text(TEMPLATE.read_text(encoding="utf-8"))
        profile = PROFILE.read_text(encoding="utf-8")
        named = command_flags(text)["models"] | command_flags(profile)["models"]
        allowed = help_flags("models-help.txt") | help_flags("help.txt")
        self.assertEqual(missing_flags(named, allowed), [])

    def test_no_false_negative_claim(self):
        text = runner_opencode_text(TEMPLATE.read_text(encoding="utf-8"))
        profile = PROFILE.read_text(encoding="utf-8")
        allowed = {
            "run": help_flags("run-help.txt") | help_flags("help.txt"),
            "models": help_flags("models-help.txt") | help_flags("help.txt"),
        }
        invalid = [(command, flag) for command, flag in negative_claims(text + profile)
                   if flag in allowed[command]]
        self.assertEqual(invalid, [])

    def test_semantic_checks_catch_planted_cases(self):
        self.assertEqual(
            negative_claims(
                "--standalone is global. listModels (opencode models) has no such flag"
            ),
            [("models", "--standalone")],
        )
        self.assertEqual(command_flags("['run', '--qqflag']")["run"], {"--qqflag"})
        self.assertNotIn("--qqflag", help_flags("run-help.txt") | help_flags("help.txt"))
        self.assertEqual(
            command_flags(
                "    resume: (m, c, sid, mode) => [...RUNTIMES.opencode[mode](m, c), "
                "'--qqresume', sid],"
            )
            ["run"],
            {"--qqresume"},
        )


if __name__ == "__main__":
    unittest.main()
