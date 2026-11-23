"""37-21: ai-kit-cross-ai documents the call vocabulary, the settings report and the status group,
locked to the runner source and --describe (SPEC R11, D-14)."""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills/ai-kit-cross-ai/SKILL.md"
LAUNCH = REPO / "skills/ai-kit-cross-ai/references/launch-and-wait.md"
TEMPLATE = REPO / "skills/ai-kit-spec-review/references/cross-ai.mjs"
FENCE_RE = re.compile(r"```(.*?)```", re.DOTALL)
sys.path.insert(0, str(REPO / "skills/ai-kit-gsd-curated-config"))
from ai_kit_gsd_curated_config import cross_ai

from tests.cross_ai_selftest import _real_node_executable, runner_env

FLAGS = ("--role", "--effort", "--codex-effort", "--context", "--escalate-runtime",
         "--escalate-model", "--session-id", "--host", "--skill-path", "--skill-name",
         "--mcp-config", "--argv-file", "--describe", "--print-argv")

REASONS_HEADING = "### Settings report"
GROUP_HEADING = "### Status line fields"
GROUP_KEYS = ("session", "applied", "ignored", "unknown", "escalate")


def _section(text, heading):
    start = text.find(heading)
    if start < 0:
        return ""
    nxt = text.find("\n## ", start + len(heading))
    return text[start:] if nxt < 0 else text[start:nxt]


def runner_list(name):
    match = re.search(rf"const {name}\s*=\s*(?:Object\.freeze\(|new Set\()?\s*\[(.*?)\]",
                      TEMPLATE.read_text(encoding="utf-8"), re.DOTALL)
    if not match:
        raise AssertionError(f"{name} not found in the runner template")
    return re.findall(r"['\"]([a-z_]+)['\"]", match.group(1))


def describe_json():
    node = _real_node_executable()
    if not node:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run([node, str(TEMPLATE), "--describe"], cwd=tmp, env=runner_env(tmp),
                              capture_output=True, text=True, timeout=60, check=False)
        if proc.returncode:
            raise AssertionError(proc.stderr[-300:])
        return json.loads(proc.stdout)


def reason_rows(text):
    return re.findall(r"^\| `([a-z_]+)` \|", _section(text, REASONS_HEADING), re.MULTILINE)


def names_sentence(text):
    for line in _section(text, REASONS_HEADING).splitlines():
        if line.startswith("The names, in print order:"):
            return re.findall(r"`([a-z_]+)`", line)
    return []


def group_problem(line, names):
    tokens = line.split()[1:]
    if any("=" not in token for token in tokens):
        return "invalid token"
    pairs = [token.split("=", 1) for token in tokens]
    keys = [pair[0] for pair in pairs]
    if len(set(keys)) != len(keys) or "cycles" not in keys:
        return "missing cycles or duplicate key"
    index = keys.index("cycles")
    if keys[index + 1:index + 6] != list(GROUP_KEYS):
        return "missing or misplaced group"
    if "retry_after_s" in keys and keys.index("retry_after_s") <= index + 5:
        return "misplaced retry"
    values = dict(pairs)
    if not values["session"]:
        return "empty session"
    for key in ("applied", "ignored", "unknown"):
        value = values[key]
        if value != "-" and any(not item or (item not in names and not item.startswith(
                ("skill:", "mcp:"))) for item in value.split(",")):
            return f"invalid {key}"
    if values["escalate"] not in ("-", "runtime", "model", "runtime,model"):
        return "invalid escalate"
    return None


def vocabulary_names(text):
    return re.findall(r"^\|.*\| `([a-z_]+)` \|$", _section(text, "### Call settings"),
                      re.MULTILINE)


class VocabularyDocs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text(encoding="utf-8")

    def test_vocabulary_table_matches_runner_names(self):
        self.assertEqual(vocabulary_names(self.text), runner_list("SETTING_NAMES"))

    def test_documented_flags_exist_in_the_runner(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        for flag in FLAGS:
            self.assertIn(flag, self.text)
            self.assertIn(f"'{flag}'", template)

    def test_argv_file_lane_text(self):
        section = _section(self.text, "## 2. Launch")
        for value in ("{model}", "{effort}", "{session}", "no_slot", "stdin", "65536",
                      "`Claude`", "no formula for <id> in the runner; pass --argv-file, "
                      "or use a runtime it has a formula for"):
            self.assertIn(value, section)

    def test_hosting_text_states_switch_and_limits(self):
        section = _section(self.text, "## 2. Launch")
        for value in ("HERDR_ENV=1", "AIKIT_HOST=none", "--host none", "no_herdr", "host_failed",
                      "cross-ai: host herdr tab=", "ai-kit/spec/host/", "run.json", "setsid",
                      "fish", "nushell", "macOS", "unverified"):
            self.assertIn(value, section)

    def test_skills_and_mcp_text(self):
        for value in ("form=<name|path|prose>", "sha256", "mcpServers", "no_form", "mode_forbids"):
            self.assertIn(value, self.text)

    def test_session_paragraph(self):
        section = _section(self.text, "## 5. Chain review or execution")
        for value in ("`--session-id`", "`session=`", "mode_forbids",
                      "never falls back to a fresh session"):
            self.assertIn(value, section)

    def test_template_floor_is_the_shipped_version(self):
        self.assertIn(f"`template={cross_ai.TEMPLATE_VERSION}` or later",
                      _section(self.text, "## 2. Launch"))

    def test_evidence_is_the_last_heading(self):
        headings = [line for line in self.text.splitlines() if line.startswith("## ")]
        self.assertEqual(headings[-1], "## Evidence")
        self.assertLess(headings.index("## References"), headings.index("## Evidence"))


class SettingsReportDocs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text(encoding="utf-8")
        cls.describe = describe_json()

    def test_reason_table_matches_runner_and_describe(self):
        rows = reason_rows(self.text)
        self.assertEqual(rows, runner_list("SETTING_REASONS"))
        self.assertEqual(len(rows), 10)
        if self.describe is None:
            self.skipTest("node not on PATH: the --describe leg is skipped")
        self.assertEqual(rows, self.describe["reasons"])

    def test_setting_names_match_runner_and_describe(self):
        names = names_sentence(self.text)
        self.assertEqual(names, runner_list("SETTING_NAMES"))
        self.assertEqual(len(names), 11)
        if self.describe is None:
            self.skipTest("node not on PATH: the --describe leg is skipped")
        self.assertEqual(names, self.describe["settings"])

    def test_states_match_describe(self):
        for state in ("applied", "ignored", "unknown"):
            self.assertIn(f"- `{state}`:", _section(self.text, REASONS_HEADING))
        if self.describe is None:
            self.skipTest("node not on PATH: the --describe leg is skipped")
        self.assertEqual(self.describe["states"], ["applied", "ignored", "unknown"])

    def test_lock_catches_a_swapped_or_extra_row(self):
        rows = [line for line in self.text.splitlines() if re.match(r"^\| `[a-z_]+` \|", line)]
        swapped = self.text.replace(rows[0] + "\n" + rows[1], rows[1] + "\n" + rows[0])
        extra = self.text.replace(rows[-1], rows[-1] + "\n| `made_up` | x |")
        for text in (swapped, extra):
            self.assertNotEqual(reason_rows(text), runner_list("SETTING_REASONS"))


class StatusGroupDocs(unittest.TestCase):
    def test_sample_lines_carry_the_group(self):
        names = runner_list("SETTING_NAMES")
        for path, minimum in ((SKILL, 2), (LAUNCH, 1)):
            lines = [line for fence in FENCE_RE.findall(path.read_text(encoding="utf-8"))
                     for line in fence.splitlines() if line.startswith("AIKIT-XAI ")]
            self.assertGreaterEqual(len(lines), minimum)
            for line in lines:
                self.assertIsNone(group_problem(line, names), line)

    def test_group_check_catches_a_line_without_it(self):
        names = runner_list("SETTING_NAMES")
        prefix = "AIKIT-XAI model=fake/x attempts=1 cycles=0 "
        group = "session=- applied=model ignored=- unknown=- escalate=-"
        for line in (prefix, prefix + "retry_after_s=600 cycle=0 " + group,
                     prefix + group.replace("applied=model", "applied=bogus")):
            self.assertIsNotNone(group_problem(line, names))
        self.assertIsNone(group_problem(prefix + group, names))

    def test_group_fields_documented(self):
        section = _section(SKILL.read_text(encoding="utf-8"), GROUP_HEADING)
        for field in ("`session=`", "`applied=`", "`ignored=`", "`unknown=`", "`escalate=`",
                      "`--session-id`", "skill:<name>", "mcp:<name>"):
            self.assertIn(field, section)


if __name__ == "__main__":
    unittest.main()
