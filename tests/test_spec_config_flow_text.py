"""Doc-contract tests for spec-config's question flow, skeleton and docs (36-24, 36-25, 36-28)."""

import os
import re
import shlex
import sys
import unittest
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, config_migrate, lane_data_use, lane_settings

REPO = Path(__file__).resolve().parents[1]
README = REPO / "README.md"
DESIGN = REPO / "docs" / "config" / "design.md"
AGENTS = REPO / "AGENTS.md"
REVIEW_ROW = "| [`ai-kit-spec-review`](skills/ai-kit-spec-review/SKILL.md) |"
CONFIG_ROW = "| [`ai-kit-spec-config`](skills/ai-kit-spec-config/SKILL.md) |"
ADAPTER_ROW = ("| [`ai-kit-spec-execute-superpowers`]"
               "(skills/ai-kit-spec-execute-superpowers/SKILL.md) |")
SKILL_DIR = REPO / "skills" / "ai-kit-spec-config"
SKILL = SKILL_DIR / "SKILL.md"
HEADLESS = SKILL_DIR / "references" / "headless.md"
CONFIG_FILE = SKILL_DIR / "references" / "config-file.md"
KEEP_ENV = "AI_KIT_KEEP_MIGRATION_BACKUP"
KEEP_ANSWER = "keep the old roster as `review-spec.toml.migrated`"
FLOW = SKILL_DIR / "references" / "wizard-flow.md"
FREE = SKILL_DIR / "references" / "free-lanes.md"
SELECTION = SKILL_DIR / "references" / "cli-model-selection.md"
RUN_LINE = re.compile(r"^- Run: `([^`]+)`$", re.MULTILINE)
LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
FLOW_COMMANDS = ("propose-lanes", "check-reviewer", "check-code-index-alternative")
FLOW_HEADINGS = (
    "## 1. Preferred runtimes per purpose",
    "## 2. Catalog inputs",
    "## 3. Proposal per purpose",
    "## 4. Free lanes",
    "## 5. Pair and effort per chosen lane",
    "## 6. Test the pair",
    "## 7. Session default",
    "## 8. Alternative lane",
    "## 9. Order per role",
    "## 10. Escalation",
    "## 11. Mode, strategy and timeouts",
)
PROPOSE_REVIEW_RUN = "- Run: `propose-lanes --purpose review"
CHECK_RUN = "- Run: `check-reviewer"
CODE_INDEX_RUN = "- Run: `check-code-index-alternative"
UNKNOWN_FIELDS_LINE = "An alias row or a model the owner names has no price or effort fields"
PLANTED_BAD_PURPOSE = "- Run: `propose-lanes --purpose both --catalog-path c --detect`"
PLANTED_OTHER_COMMAND = "- Run: `catalog-report --catalog-path c --detect`"
NO_EFFORT_LINE = "the runner has no effort flag for <runtime> yet, so no effort is stored"
ESCALATION_LINE = "stored and informational; no run reads them yet"
ALLOWANCE_LINE = "This test call spends part of the lane's allowance."
HERDR_LINE = "never in a herdr pane or by another agent"
PROPOSAL_KEYS = ("default_view", "pool", "wider", "zero_price", "aliases", "empty", "message",
                 "ranker_reason", "efforts", "efforts_refused", "efforts_source", "price",
                 "data_use_needed")
EFFORT_PROBE_WORDS = ("effort_probe", "accepted", "rejected", "inconclusive", "ignored",
                      "label", "error", "reason")
FREE_HEADINGS = (
    "## a. Data use first",
    "## b. Pool and usage limit",
    "## c. What is written",
    "## d. Fallback rule",
    "## e. Alternative lane",
    "## f. Who asks",
)
DECLINE_LINE = ("A no or a skip writes no lane: the lane leaves the set and no further question"
                " is asked about it.")
UNKNOWN_LINE = "A missing or unreadable source is `unknown`, never a safe value."
LABEL_LINE = "`verified` only when the vendor's own documentation page was read in this run"
POOL_WARNING = ("Free models of <provider> appear to share one pool (reported by users, not"
                " confirmed by the vendor): another free model of <provider> is not a fallback"
                " for this one.")
FLAG_LINE = "Only a yes writes `usage_limited = true`"
FALLBACK_LINE = ("A usage-limited lane's fallback is the first lane of the same role, in that"
                 " role's order, that is neither usage-limited nor in the same pool")


def run_line_problems(text, allowed) -> list[str]:
    problems = []
    lines = RUN_LINE.findall(text)
    for command in lines:
        args = shlex.split(command)
        if not args or args[0] not in allowed:
            problems.append(f"unknown command: {command}")
            continue
        try:
            cli._build_parser().parse_args(args)
        except SystemExit:
            problems.append(f"invalid command: {command}")
    if not lines:
        problems.append("no documented commands")
    return problems


def section(text, heading) -> str:
    lines = text.splitlines()
    if heading not in lines:
        return ""
    result = []
    for line in lines[lines.index(heading) + 1:]:
        if line.startswith("## "):
            break
        result.append(line)
    return "\n".join(result)


def row(text, prefix) -> str:
    return next((line for line in text.splitlines() if line.startswith(prefix)), "")


def link_problems(path) -> list[str]:
    return [f"{path.name}: {target}" for target in LINK.findall(path.read_text(encoding="utf-8"))
            if not target.startswith(("http://", "https://"))
            and not (path.parent / target).exists()]


class TestWizardFlowText(unittest.TestCase):
    def setUp(self):
        self.flow = FLOW.read_text(encoding="utf-8")
        self.selection = SELECTION.read_text(encoding="utf-8")

    def test_steps_in_order(self):
        lines = self.flow.splitlines()
        indexes = [lines.index(heading) for heading in FLOW_HEADINGS]
        self.assertEqual(indexes, sorted(set(indexes)))

    def test_run_lines_parse(self):
        self.assertEqual([], run_line_problems(self.flow, FLOW_COMMANDS))
        self.assertTrue(run_line_problems(PLANTED_BAD_PURPOSE, FLOW_COMMANDS))
        self.assertTrue(run_line_problems(PLANTED_OTHER_COMMAND, FLOW_COMMANDS))

    def test_proposal_runs_before_any_effort_probe(self):
        self.assertLess(self.flow.index(PROPOSE_REVIEW_RUN), self.flow.index(CHECK_RUN))

    def test_effort_rules(self):
        text = section(self.flow, FLOW_HEADINGS[4])
        for word in (NO_EFFORT_LINE, "efforts_refused", "efforts_source", *EFFORT_PROBE_WORDS):
            self.assertIn(word, text)
        self.assertNotIn("build-command", text)
        lines = [line for line in self.flow.splitlines() if line.startswith(CHECK_RUN)]
        self.assertEqual(len(lines), 1)
        self.assertIn(" --effort ", lines[0])
        self.assertNotIn("--catalog-path", lines[0])

    def test_orders_and_escalation(self):
        order = section(self.flow, FLOW_HEADINGS[8])
        self.assertIn("[lanes.policy.review]", order)
        self.assertIn("[lanes.policy.execute]", order)
        escalation = section(self.flow, FLOW_HEADINGS[9])
        self.assertIn(ESCALATION_LINE, escalation)
        self.assertIn("two or more lanes", escalation)

    def test_proposal_keys_named(self):
        for key in PROPOSAL_KEYS:
            self.assertIn(f"`{key}`", self.flow)

    def test_allowance_line_before_every_free_lane_call(self):
        s5 = section(self.flow, FLOW_HEADINGS[4])
        self.assertLess(s5.index(ALLOWANCE_LINE), s5.index(CHECK_RUN))
        self.assertIn(ALLOWANCE_LINE, section(self.flow, FLOW_HEADINGS[5]))

    def test_unknown_fields_rule(self):
        text = section(self.flow, FLOW_HEADINGS[2])
        self.assertIn(UNKNOWN_FIELDS_LINE, text)
        self.assertIn("never zero", text)
        self.assertIn("a model the owner named", section(self.flow, FLOW_HEADINGS[4]))

    def test_code_index_check_runs_before_the_write(self):
        self.assertTrue(any(line.startswith(CODE_INDEX_RUN)
                            for line in section(self.flow, FLOW_HEADINGS[5]).splitlines()))
        self.assertLess(self.flow.index(CODE_INDEX_RUN), self.flow.index(FLOW_HEADINGS[10]))

    def test_catalog_inputs_point_to_the_proposal(self):
        for word in ("propose-lanes", "wizard-flow.md"):
            self.assertIn(word, self.selection)
        for word in ("score_candidates", "python3 -c", "no_exec"):
            self.assertNotIn(word, self.selection)

    def test_no_seed_flag_in_spec_config_text(self):
        for path in SKILL_DIR.rglob("*.md"):
            if "evals" not in path.parts:
                self.assertNotIn("review_only", path.read_text(encoding="utf-8"), str(path))

    def test_selection_links_resolve(self):
        self.assertEqual([], link_problems(SELECTION))


class TestFreeLanesText(unittest.TestCase):
    def setUp(self):
        self.free = FREE.read_text(encoding="utf-8")
        self.flow = FLOW.read_text(encoding="utf-8")

    def test_sections_in_order(self):
        lines = self.free.splitlines()
        indexes = [lines.index(heading) for heading in FREE_HEADINGS]
        self.assertEqual(indexes, sorted(set(indexes)))

    def test_data_use_comes_first_and_a_decline_writes_no_lane(self):
        text = section(self.free, FREE_HEADINGS[0])
        for phrase in ("before anything else about the lane", DECLINE_LINE, UNKNOWN_LINE,
                       LABEL_LINE):
            self.assertIn(phrase, text)
        self.assertIn("free-lanes.md", section(self.flow, FLOW_HEADINGS[3]))

    def test_data_use_record_matches_the_code(self):
        for item in (*lane_data_use.DATA_USE_KEYS, *lane_data_use.DATA_USE_VALUES,
                     *lane_data_use.DATA_USE_LABELS):
            self.assertIn(f"`{item}`", self.free)

    def test_no_data_use_command(self):
        self.assertTrue(all(line.startswith("propose-lanes ")
                            for line in RUN_LINE.findall(self.free)))
        self.assertEqual([], run_line_problems(self.free, ("propose-lanes",)))

    def test_pool_warning_and_owner_flag(self):
        text = section(self.free, FREE_HEADINGS[1])
        self.assertIn(POOL_WARNING, text)
        self.assertIn(FLAG_LINE, text)
        self.assertIn("pool_key", section(self.free, FREE_HEADINGS[2]))

    def test_fallback_and_alternative(self):
        self.assertIn(FALLBACK_LINE, section(self.free, FREE_HEADINGS[3]))
        text = section(self.free, FREE_HEADINGS[4])
        match = RUN_LINE.search(text)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertIn("--avoid-pool", match.group(1))
        self.assertIn("--skip", match.group(1))
        for phrase in ("Nothing refuses the role", "that lane's own pool only",
                       "two runs, each avoiding only its own pool"):
            self.assertIn(phrase, text)

    def test_questions_stay_with_the_owner(self):
        self.assertIn(HERDR_LINE, self.free)
        self.assertIn(HERDR_LINE, self.flow)

    def test_flow_and_free_links_resolve(self):
        self.assertEqual([], link_problems(FREE) + link_problems(FLOW))


def between(text, start, end) -> str:
    return text[text.index(start):text.index(end, text.index(start))]


class TestSkillSkeleton(unittest.TestCase):
    def setUp(self):
        self.skill = SKILL.read_text(encoding="utf-8")
        self.headless = HEADLESS.read_text(encoding="utf-8")

    def test_headless_stop_comes_right_after_detection(self):
        markers = ('python3 "$TOOLS_PY" detect-tools',
                   'If the host has no structured-question tool',
                   '**If `--check-only` was passed**', 'python3 "$TOOLS_PY" detect-runtimes --save')
        indexes = [self.skill.index(item) for item in markers]
        self.assertEqual(indexes, sorted(indexes))
        self.assertIn('(references/headless.md)', self.skill)

    def test_headless_block_writes_nothing(self):
        for phrase in ('ai-kit-spec-config cannot ask here; no config, cache or trust record '
                       'was written.',
                       'Installed runtimes:', 'Questions it would ask:',
                       'A person must run ai-kit-spec-config.'):
            self.assertIn(phrase, self.headless)
        self.assertNotIn('--save', self.headless)
        self.assertEqual([], RUN_LINE.findall(self.headless))

    def test_never_additions(self):
        text = between(self.skill, '## NEVER', '### Step 1 —')
        for phrase in ("Never let the proposal's order stand as the owner's pick",
                       'Never ask a wizard question in a herdr pane or of another agent',
                       'Never write a lane whose data-use confirmation was declined or skipped',
                       "Never set `usage_limited`, `escalate_runtime` or `escalate_model` "
                       "without the owner's explicit yes"):
            self.assertIn(phrase, text)

    def test_description_names_both_callers(self):
        front = self.skill.split('---', 2)[1]
        self.assertIn('ai-kit-spec-execute-superpowers', front)
        self.assertIn('proposes a review set and an execute set', front)
        self.assertNotIn('warns no config exists', front)

    def test_step_2_2_points_to_the_flow(self):
        text = between(self.skill, '#### Step 2.2', '#### Step 2.3')
        for phrase in ('(references/wizard-flow.md)', '(references/free-lanes.md)', 'MANDATORY',
                       'once per chosen model'):
            self.assertIn(phrase, text)

    def test_per_role_orders_replace_the_shared_ladder(self):
        self.assertNotIn('policy.ladder', self.skill)
        text = between(self.skill, '### Step 3 —', '### Step 4 —')
        for phrase in ('"review": {"ladder"', '"execute": {"ladder"', '[--keep-backup]'):
            self.assertIn(phrase, text)
        for role in ('review', 'execute'):
            self.assertIn(f'[lanes.policy.{role}]', self.skill[self.skill.index('### Step 4 —'):])

    def test_migration_line(self):
        self.assertNotIn('stays recoverable', self.skill)
        text = between(self.skill, '#### Step 2.1', '#### Step 2.2')
        self.assertIn('--keep-backup', text)
        self.assertIn('review-spec.toml.migrated', text)

    def test_keep_answer_on_every_route(self):
        text = between(self.skill, '#### Step 2.1', '#### Step 2.2')
        self.assertEqual(2, text.count(KEEP_ANSWER))
        self.assertLess(text.index('A global roster already exists at'), text.index(KEEP_ANSWER))
        self.assertLess(text.index(KEEP_ANSWER), text.index('**Replacement gate'))
        self.assertGreater(text.rindex(KEEP_ANSWER), text.index('**Replacement gate'))

    def test_no_real_alias_names_in_step_2_7(self):
        text = between(self.skill, '#### Step 2.7', '#### Step 2.8')
        self.assertIn('placeholder-alias-1', text)
        self.assertNotIn('never a full model id like', text)
        self.assertNotIn('pick one of those four', text)

    def test_cursor_effort_is_a_lane_key(self):
        # Judge loop 39.1.1 r1: the cursor id rules moved to references/runtime-ids.md.
        step = between(self.skill, '#### Step 2.4', '#### Step 2.5')
        self.assertIn('(references/runtime-ids.md)', step)
        ref = (SKILL_DIR / "references" / "runtime-ids.md").read_text(encoding="utf-8")
        for text in (step, ref):
            self.assertNotIn('[--effort <e>] [--fast', text)
            self.assertNotIn('effort/fast/context', text)
        self.assertIn('Leave `--effort` out', ref)

    def test_allowance_line_in_step_2_5(self):
        self.assertIn(ALLOWANCE_LINE, between(self.skill, '#### Step 2.5', '#### Step 2.6'))

    def test_skill_links_resolve(self):
        self.assertEqual([], link_problems(SKILL) + link_problems(HEADLESS))

    def test_render_toml_passes_the_proposal_evidence(self):
        text = between(self.skill, '### Step 3 —', '### Step 4 —')
        self.assertIn('--catalog-path <catalog> --runtimes-json "$RUNTIMES_JSON"', text)
        cli._build_parser().parse_args(['render-toml', '--json-config', 'c.json', '--out', 't.toml',
                                        '--replace', '--keep-backup', '--catalog-path', 'c',
                                        '--runtimes-json', 'r'])


class TestConfigFileText(unittest.TestCase):
    def setUp(self):
        self.text = CONFIG_FILE.read_text(encoding='utf-8')

    def test_role_tables_and_lane_settings(self):
        for phrase in ('`[lanes.policy.review]`', '`[lanes.policy.execute]`', '## Lane settings',
                       *(f'`{key}`' for key in lane_settings.MODEL_BOUND)):
            self.assertIn(phrase, self.text)

    def test_migration_default_and_read_only_commands(self):
        self.assertNotIn('stays recoverable', self.text)
        for phrase in (f'{KEEP_ENV}=1', 'render-toml --keep-backup', '## Read-only commands',
                       '`config-status --cwd <project root>`', '`propose-lanes --purpose review`'):
            self.assertIn(phrase, self.text)
        self.assertTrue(config_migrate.keep_backup_from_env({KEEP_ENV: '1'}))
        self.assertFalse(config_migrate.keep_backup_from_env({}))


class TestConfigDocsText(unittest.TestCase):
    def setUp(self):
        self.readme = README.read_text(encoding="utf-8")
        self.design = DESIGN.read_text(encoding="utf-8")
        self.agents = AGENTS.read_text(encoding="utf-8")

    def test_readme_skill_rows(self):
        review = row(self.readme, REVIEW_ROW)
        for phrase in ("config-status", "no exec formula"):
            self.assertIn(phrase, review)
        self.assertNotIn("review-only", review)
        config = row(self.readme, CONFIG_ROW)
        for phrase in ("propose-lanes", "[lanes.policy.review]", "data-use note"):
            self.assertIn(phrase, config)
        self.assertIn("config-status", row(self.readme, ADAPTER_ROW))

    def test_readme_config_section(self):
        text = section(self.readme, "## ai-kit configuration")
        for phrase in ("[lanes.policy.review]", "[lanes.policy.execute]", "config-status",
                       "--keep-backup", KEEP_ENV, ".retiring"):
            self.assertIn(phrase, text)
        self.assertNotIn("stays recoverable as", text)

    def test_agents_names_the_seed_advice(self):
        self.assertIn("seed advice text", self.agents)
        self.assertNotIn("review-only flag", self.agents)

    def test_design_record_tables_and_keys(self):
        text = section(self.design, "## Tables")
        for key in ("[lanes.policy.review]", "[lanes.policy.execute]", "config-status",
                    "propose-lanes", *lane_settings.MODEL_BOUND):
            self.assertIn(f"`{key}`", text)
        self.assertNotIn("Phase 36", text)

    def test_design_record_migration_default(self):
        text = section(self.design, "## Environment-only settings")
        for phrase in (f"`{KEEP_ENV}`", "keep_backup_from_env", ".retiring"):
            self.assertIn(phrase, text)
        for heading in ("## Assignments", "## Inventory"):
            self.assertEqual(
                section(self.design, heading).count("deleted after the value check"), 2)


if __name__ == "__main__":
    unittest.main()
