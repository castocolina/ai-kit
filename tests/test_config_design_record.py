"""Fitness test for the settings inventory and decision record docs/config/design.md (SPEC R1,
R2; D-05, D-06; plan 33-11 Task 1).

The labels come from the path functions the code uses, called with synthetic environments, and
from the runner template's file-name literals. Each label must appear in the record's
`## Assignments` table exactly once with a non-empty assignment. The test reads docs/ only, never
.planning/, and creates nothing on disk."""

import importlib.util
import re
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
RECORD = REPO / "docs/config/design.md"
SPEC_DIR = REPO / "skills" / "ai-kit-spec-review"
TOOLS_DIR = REPO / "tools"
SKILLS_DIR = REPO / "skills"
JEV_SCRIPT = REPO / "skills" / "jev-fast-decision" / "scripts" / "jev_review.py"
FLOW_RECORD = REPO / "skills" / "ai-kit-commit-fold" / "scripts" / "flow_record.py"
RUNNER_TEMPLATE = REPO / "skills" / "ai-kit-spec-review" / "references" / "cross-ai.mjs"

sys.path.insert(0, str(SPEC_DIR))
sys.path.insert(0, str(TOOLS_DIR))
import claude_host
import common_config
import cursor_host
from ai_kit_spec import cache, config_io, config_migrate, detection, local_secrets, model_catalog

PROJECT_ROOT = "/p"
USER_HOME = "/h"
USER_ENV = {"HOME": USER_HOME}
USER_BASE = config_io.cfg_config_base(USER_ENV)
CACHE_BASE = cache.cache_base(USER_ENV)
USER_PREFIX = "${XDG_CONFIG_HOME:-~/.config}/ai-kit/"
CACHE_PREFIX = "${XDG_CACHE_HOME:-~/.cache}/ai-kit/spec/"
SECTIONS = ["Decision", "Roles", "Trust", "Resolver rule", "Assignments", "Tables", "Inventory",
            "Environment-only settings", "Other tools' files", "State and caches"]
TABLE_NAMES = ["[models]", "[lanes]", "[[lanes.review]]", "[[lanes.execute]]", "[runner]",
               "[runner.retry]", '[runner.retry.scopes."<scope>"]', "[jev]", "[hooks]"]
NAME_SPLIT = re.compile(r"[.\-_\[\]\"/]")


def _under(path, base):
    if not path.startswith(base + "/"):
        raise AssertionError(f"{path} is not under {base}")
    return path[len(base) + 1:]


def _load_jev_review():
    spec = importlib.util.spec_from_file_location("jev_review_record", JEV_SCRIPT)
    assert spec is not None and spec.loader is not None, JEV_SCRIPT
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collected_labels():
    """Every settings or state location the path functions and runner literals name, as the
    record writes it: project paths relative to the project, user and cache paths behind
    their resolved prefix."""
    labels = set()
    local = config_io.cfg_local_path(PROJECT_ROOT)
    labels.add(_under(local, PROJECT_ROOT))
    labels.add(_under(config_migrate.legacy_path(local), PROJECT_ROOT))
    flow_text = FLOW_RECORD.read_text(encoding="utf-8")
    flow = re.search(r'SETTINGS_REL = Path\("\.aikit"\) / "([^"]+)"', flow_text)
    if flow is None:
        raise AssertionError("flow_record.py no longer holds SETTINGS_REL")
    labels.add(".aikit/" + flow.group(1))
    global_path = config_io.cfg_global_path(USER_ENV)
    labels.add(USER_PREFIX + _under(global_path, USER_BASE))
    labels.add(USER_PREFIX + _under(config_migrate.legacy_path(global_path), USER_BASE))
    trust = config_io.cfg_trust_store_dir(USER_ENV)
    labels.add(USER_PREFIX + _under(trust, USER_BASE))
    labels.add(USER_PREFIX + _under(config_migrate.legacy_trust_dir(trust), USER_BASE))
    labels.add(USER_PREFIX + _under(local_secrets.secrets_env_path(USER_ENV), USER_BASE))
    jev = _load_jev_review()
    with mock.patch.dict("os.environ", {"HOME": USER_HOME}, clear=True):
        labels.add(USER_PREFIX + _under(jev.consent_path(), USER_BASE))
    for spec in (claude_host.SPEC, cursor_host.SPEC):
        status_line = common_config.cfg_config_path(USER_ENV, spec)
        labels.add(USER_PREFIX + _under(status_line, USER_BASE))
        segments = common_config.cfg_segments_dir(None, USER_ENV, spec.provider_dir)
        labels.add(USER_PREFIX + _under(segments, USER_BASE))
    labels.add(CACHE_PREFIX + _under(model_catalog.cache_catalog_path(USER_ENV), CACHE_BASE))
    return labels


def runner_literal_labels():
    """File names the runner template spells out: its user-dir JSON files and its GSD config."""
    text = RUNNER_TEMPLATE.read_text(encoding="utf-8")
    labels = {USER_PREFIX + name
              for name in re.findall(r"'(cross-ai(?:-errors)?\.json)'", text)}
    if "'config.json'" in text:
        labels.add(".planning/config.json")
    return labels


def all_labels():
    return collected_labels() | runner_literal_labels()


def record_text():
    return RECORD.read_text(encoding="utf-8")


def section(text, heading):
    lines = text.splitlines()
    start = next((i + 1 for i, line in enumerate(lines) if line.strip() == f"## {heading}"), None)
    if start is None:
        return None
    end = next((j for j in range(start, len(lines)) if lines[j].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def assignment_rows(text):
    """(location, layer, assignment, reason) for each data row of the Assignments table."""
    rows = []
    for line in (section(text, "Assignments") or "").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] == "Location" or set(cells[0]) <= set("-: "):
            continue
        found = re.search(r"`([^`]+)`", cells[0])
        rows.append((found.group(1) if found else "", cells[1], cells[2], cells[3]))
    return rows


def assignment_problems(rows, labels):
    problems = []
    counts = Counter(location for location, _layer, _assign, _reason in rows)
    for label in sorted(labels):
        if counts.get(label, 0) == 0:
            problems.append(f"no assignment row for {label}")
        elif counts[label] > 1:
            problems.append(f"{counts[label]} assignment rows for {label}")
    for location, _layer, assign, _reason in rows:
        if not location:
            problems.append("assignment row with no backticked location")
        elif location not in labels:
            problems.append(f"assignment row for a location no path function returns: {location}")
        if not assign.strip():
            problems.append(f"empty assignment for {location or '(no location)'}")
    return problems


def name_problems(names, hosts, skill_names):
    problems = []
    for name in names:
        if name in hosts:
            problems.append(f"{name} is a host id")
        for token in (part for part in NAME_SPLIT.split(name) if part):
            if token in hosts:
                problems.append(f"{name} names host {token}")
        for skill in skill_names:
            if skill and skill in name:
                problems.append(f"{name} names skill {skill}")
    return problems


def host_ids():
    return set(detection.RUNTIMES) | {"cursor-agent"}


def skill_names():
    names = set()
    for entry in SKILLS_DIR.iterdir():
        if not entry.is_dir() or entry.name == "_shared":
            continue
        names.add(entry.name.removeprefix("ai-kit-"))
    return names


class TestConfigDesignRecord(unittest.TestCase):
    def test_every_collected_location_has_one_assignment(self):
        rows = assignment_rows(record_text())
        self.assertEqual(assignment_problems(rows, all_labels()), [])

    def test_decision_names_both_paths_and_the_rule(self):
        decision = section(record_text(), "Decision") or ""
        self.assertIn(".aikit/config.toml", decision)
        self.assertIn("${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml", decision)
        self.assertIn("per key: project, then user, then built-in defaults", decision)

    def test_tables_section_lists_every_table(self):
        tables = section(record_text(), "Tables") or ""
        for name in TABLE_NAMES:
            self.assertIn(f"`{name}`", tables)

    def test_record_has_every_section(self):
        text = record_text()
        for heading in SECTIONS:
            self.assertIsNotNone(section(text, heading), heading)

    def test_new_names_carry_no_skill_or_host_name(self):
        tables = section(record_text(), "Tables") or ""
        names = ["config.toml", "config-trust", *re.findall(r"`(\[[^`]+\])`", tables)]
        self.assertEqual(name_problems(names, host_ids(), skill_names()), [])

    def test_record_holds_no_secret_value(self):
        text = record_text()
        self.assertIsNone(re.search(r"(?<![A-Za-z0-9])sk-", text))
        self.assertNotIn("ghp_", text)
        self.assertIsNone(re.search(
            r"(ARTIFICIAL_ANALYSIS_API_KEY|TYPESAFE_API_KEY|JEV_API_KEY)\s*=", text))

    def test_flow_settings_path_matches_the_code(self):
        self.assertRegex(FLOW_RECORD.read_text(encoding="utf-8"),
                         r'SETTINGS_REL = Path\("\.aikit"\) / "flow\.json"')


class TestRecordNonVacuity(unittest.TestCase):
    ROWS = [
        (".aikit/config.toml", "project", "config.toml", "the project layer"),
        (".aikit/flow.json", "project", "separate: unit flow", "its own file"),
    ]

    def test_a_missing_label_fails_the_assignment_check(self):
        problems = assignment_problems(self.ROWS, {".aikit/config.toml", ".aikit/flow.json",
                                                   ".aikit/review-spec.toml"})
        self.assertIn("no assignment row for .aikit/review-spec.toml", problems)

    def test_a_label_in_two_rows_fails(self):
        rows = [*self.ROWS, (".aikit/config.toml", "project", "config.toml", "again")]
        problems = assignment_problems(rows, {".aikit/config.toml", ".aikit/flow.json"})
        self.assertIn("2 assignment rows for .aikit/config.toml", problems)

    def test_an_empty_assignment_fails(self):
        rows = [(".aikit/config.toml", "project", "  ", "reason")]
        problems = assignment_problems(rows, {".aikit/config.toml"})
        self.assertIn("empty assignment for .aikit/config.toml", problems)

    def test_neutral_names_pass_and_skill_or_host_names_fail(self):
        hosts = {"claude", "codex"}
        skills = {"spec-config"}
        self.assertEqual(name_problems(["[runner.retry]"], hosts, skills), [])
        self.assertTrue(name_problems(["spec-config.toml"], hosts, skills))
        self.assertTrue(name_problems(["[claude]"], hosts, skills))


if __name__ == "__main__":
    unittest.main()
