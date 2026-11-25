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
# Detail moved out of SKILL.md behind gated read lines (loop 40 judge round 1, body size).
HOSTING = REPO / "skills/ai-kit-cross-ai/references/hosting-and-locks.md"
CHECKS = REPO / "skills/ai-kit-cross-ai/references/execute-checks.md"
REASONS = REPO / "skills/ai-kit-cross-ai/references/setting-reasons.md"
TEMPLATE = REPO / "skills/ai-kit-spec-review/references/cross-ai.mjs"
FENCE_RE = re.compile(r"```(.*?)```", re.DOTALL)
sys.path.insert(0, str(REPO / "skills/ai-kit-gsd-curated-config"))
from ai_kit_gsd_curated_config import cross_ai

from tests.cross_ai_selftest import _real_node_executable, runner_env

FLAGS = ("--role", "--effort", "--codex-effort", "--context", "--escalate-runtime",
         "--escalate-model", "--session-id", "--host", "--skill-path", "--skill-name",
         "--mcp-config", "--argv-file", "--describe", "--print-argv")

REASONS_HEADING = "### Settings report"
REASON_TABLE_HEADING = "## Reasons"
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
    """The reason table rows of references/setting-reasons.md, in file order."""
    return re.findall(r"^\| `([a-z_]+)` \|", _section(text, REASON_TABLE_HEADING), re.MULTILINE)


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
    if keys[index + 6:index + 8] != ["coverage", "findings"]:
        return "missing check group"
    if "retry_after_s" in keys and keys.index("retry_after_s") <= index + 5:
        return "misplaced retry"
    values = dict(pairs)
    if not re.fullmatch(r"\d+/\d+|n/a|-", values["coverage"]):
        return "invalid coverage"
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


STATUS_HEADING = "## 4. Read the result"
FINDINGS_HEADING = "# Execute result checks"
FLAGS_HEADING = "### Supervision flags"


def status_rows(text) -> list[tuple[str, int]]:
    rows = []
    for line in _section(text, STATUS_HEADING).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) > 1 and (re.fullmatch(r"\d+", cells[0]) or cells[0] == "128+n"):
            code = 128 if cells[0] == "128+n" else int(cells[0])
            rows.extend((name, code) for name in re.findall(r"`([a-z_]+)`", cells[1]))
    return rows


def finding_rows(text) -> list[tuple[str, str]]:
    """The finding table rows of references/execute-checks.md (one `# ` title, then the table)."""
    return re.findall(r"^\| \d+\. \| `([a-z_]+)` \| ([a-z_]+) \|",
                      _section(text, FINDINGS_HEADING), re.MULTILINE)


def flag_rows(text) -> list[str]:
    return re.findall(r"^\| `(--[a-z-]+)", _section(text, FLAGS_HEADING), re.MULTILINE)


def runner_statuses() -> dict[str, int]:
    text = TEMPLATE.read_text(encoding="utf-8")
    match = re.search(r"^const STATUS_TABLE = \{(.*?)^\};", text, re.MULTILINE | re.DOTALL)
    assert match is not None
    return {name: int(code) for name, code in re.findall(
        r"^\s+([a-z_]+): \{ exit: (\d+) \}", match.group(1), re.MULTILINE)}


def runner_flags() -> list[str]:
    text = TEMPLATE.read_text(encoding="utf-8")
    match = re.search(r"const SUPERVISION_FLAGS = Object\.freeze\(\[(.*?)\]\);", text)
    assert match is not None
    return re.findall(r"['\"](--[a-z-]+)['\"]", match.group(1))


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
        launch = _section(self.text, "## 2. Launch")
        self.assertIn("(references/hosting-and-locks.md)", launch)
        for value in ("AIKIT_HOST=none", "--host none", "run.json", "never re-invoke in a loop"):
            self.assertIn(value, launch)
        section = launch + HOSTING.read_text(encoding="utf-8")
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
        cls.reasons = REASONS.read_text(encoding="utf-8")
        cls.describe = describe_json()

    def test_reason_table_matches_runner_and_describe(self):
        self.assertIn("(references/setting-reasons.md)", _section(self.text, REASONS_HEADING))
        rows = reason_rows(self.reasons)
        self.assertEqual(rows, runner_list("SETTING_REASONS"))
        self.assertEqual(len(rows), 10)
        if self.describe is None:
            self.skipTest("node not on PATH: the --describe leg is skipped")
        self.assertEqual(rows, self.describe["reasons"])

    def test_reasons_named_in_the_skill_are_runner_reasons(self):
        line = next(line for line in _section(self.text, REASONS_HEADING).splitlines()
                    if line.startswith("The reasons are a closed list"))
        named = re.findall(r"`([a-z_]+)` \(", line)
        self.assertEqual(named, ["id_carries", "mode_forbids", "host_failed"])
        for reason in named:
            self.assertIn(reason, runner_list("SETTING_REASONS"))

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
        rows = [line for line in _section(self.reasons, REASON_TABLE_HEADING).splitlines()
                if re.match(r"^\| `[a-z_]+` \|", line)]
        swapped = self.reasons.replace(rows[0] + "\n" + rows[1], rows[1] + "\n" + rows[0])
        extra = self.reasons.replace(rows[-1], rows[-1] + "\n| `made_up` | x |")
        for text in (swapped, extra):
            self.assertNotEqual(reason_rows(text), runner_list("SETTING_REASONS"))


class SupervisionDocs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text(encoding="utf-8")
        cls.hosting = HOSTING.read_text(encoding="utf-8")
        cls.checks = CHECKS.read_text(encoding="utf-8")
        cls.describe = describe_json()

    def test_supervision_text_names_each_rule(self):
        # SKILL.md keeps the caller rules; the moved detail lives in the two references.
        for value in ("--idle-timeout", "CONFIG.idleTimeoutS", "900", "`locked`",
                      "cross-ai: finding reason=", "coverage=", "findings=", "--sweep",
                      "cross-ai: sweep:", "jev-fast-decision",
                      "(references/hosting-and-locks.md)", "(references/execute-checks.md)"):
            self.assertIn(value, self.text)
        self.assertIn("never in a loop", self.text.lower())
        self.assertIn("never re-invoke in a loop", self.text.lower())
        for value in ("rule=idle-watchdog", "ai-kit/spec/locks/", "cross-ai: sweep:",
                      "herdr tab list", "never re-invoke in a loop"):
            self.assertIn(value, self.hosting)
        self.assertIn("CONFIG.idleTimeoutS", self.checks)

    def test_measured_figures_stated_once(self):
        docs = self.text + self.hosting + self.checks
        self.assertEqual(docs.count("250 ms"), 1)
        self.assertEqual(docs.count("twice the capture cap"), 1)

    def test_watchdog_is_no_longer_denied(self):
        for text in (self.text, self.hosting):
            self.assertIsNone(re.search(r"\bno idle watchdog\b", text, re.IGNORECASE))

    def test_evidence_dates_only_below_evidence(self):
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}", self.text.split("## Evidence")[0]))

    def test_status_rows_match_runner_and_describe(self):
        rows = status_rows(self.text)
        self.assertEqual(len(rows), len(dict(rows)))
        self.assertEqual(dict(rows), runner_statuses())
        if self.describe is None:
            self.skipTest("node not on PATH: the --describe leg is skipped")
        self.assertEqual(dict(rows), self.describe["statuses"])

    def test_skill_summary_names_every_blocking_finding(self):
        summary = _section(self.text, "### Execute result checks")
        self.assertIn("(references/execute-checks.md)", summary)
        for code, result in finding_rows(self.checks):
            if result != "info":
                self.assertIn(f"`{code}`", summary)
                self.assertIn(f"`{result}`", summary)

    def test_finding_rows_match_runner_and_describe(self):
        rows = finding_rows(self.checks)
        self.assertEqual([code for code, _ in rows], runner_list("FINDING_CODES"))
        if self.describe is None:
            self.skipTest("node not on PATH: the --describe leg is skipped")
        self.assertEqual(rows, [(f["code"], f["result"]) for f in self.describe["findings"]])

    def test_flag_rows_match_runner_and_describe(self):
        rows = flag_rows(self.text)
        self.assertEqual(rows, runner_flags())
        self.assertEqual(len(rows), 8)
        if self.describe is None:
            self.skipTest("node not on PATH: the --describe leg is skipped")
        self.assertEqual(rows, self.describe["supervision_flags"])

    def test_contract_catches_a_missing_extra_or_swapped_row(self):
        missing = self.text.replace(", `partial` | report", " | report", 1)
        duplicate = self.text.replace("| 1 | `no_change`", "| 1 | `ok`, `no_change`", 1)
        self.assertNotEqual(dict(status_rows(missing)), runner_statuses())
        duplicate_rows = status_rows(duplicate)
        self.assertNotEqual(len(duplicate_rows), len(dict(duplicate_rows)))
        lines = self.checks.splitlines()
        first = next(line for line in lines if line.startswith("| 1. | `no_commit`"))
        second = next(line for line in lines if line.startswith("| 2. | `task_uncovered`"))
        ninth = next(line for line in lines if line.startswith("| 9. | `coverage_unchecked`"))
        extra = self.checks.replace(ninth, ninth + "\n| 10. | `extra` | info | extra |")
        swapped = self.checks.replace(first + "\n" + second, second + "\n" + first)
        self.assertNotEqual(finding_rows(extra), finding_rows(self.checks))
        self.assertNotEqual(finding_rows(swapped), finding_rows(self.checks))
        lines = self.text.splitlines()
        sweep = next(line for line in lines if line.startswith("| `--sweep`"))
        self.assertNotEqual(flag_rows(self.text.replace(sweep, "")), runner_flags())


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
        group = "session=- applied=model ignored=- unknown=- escalate=- coverage=- findings=-"
        for line in (prefix, prefix + "session=- applied=model ignored=- unknown=- escalate=-",
                     prefix + "retry_after_s=600 cycle=0 " + group,
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
