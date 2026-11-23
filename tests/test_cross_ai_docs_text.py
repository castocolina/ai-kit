"""37-22: pin runner documentation, hosting and marked-region adjacency (SPEC R11)."""

import collections
import importlib
import json
import re
import sys
import unittest
from pathlib import Path

from tests.test_arch_hardcoded_models import scan_text

REPO = Path(__file__).resolve().parent.parent
DISPATCH = REPO / "skills/ai-kit-spec-review/references/cross-ai-dispatch.md"
RUNNER_MD = REPO / "skills/ai-kit-gsd-curated-config/references/runner.md"
README = REPO / "README.md"
DESIGN = REPO / "docs/config/design.md"
CLAUDE_PROFILE = REPO / "skills/ai-kit-spec-review/references/cli-profiles/claude.md"
SPEC_CONFIG_SKILL = REPO / "skills/ai-kit-spec-config/SKILL.md"
TEMPLATE = REPO / "skills/ai-kit-spec-review/references/cross-ai.mjs"
ERROR_CLASSIFIER_DIR = REPO / "skills/ai-kit-spec-review"
CURATED_SKILL = REPO / "skills/ai-kit-gsd-curated-config/SKILL.md"
REVIEW_SKILL = REPO / "skills/ai-kit-spec-review/SKILL.md"
SECTION = "## Lane capability block, lenses and refusals"
PROMPTS = REPO / "skills/ai-kit-spec-review/references/reviewer-prompts.md"
GUIDANCE = REPO / "skills/ai-kit-spec-review/references/tooling-guidance.md"
SUPERVISION_FLAGS = ("--baseline", "--forbid", "--idle-timeout", "--plan-id", "--sweep")
RUNNER_FLAGS = (
    "--role", "--effort", "--codex-effort", "--context", "--escalate-runtime",
    "--escalate-model", "--session-id", "--host", "--skill-path", "--skill-name",
    "--mcp-config", "--argv-file", "--describe",
)


def dispatch_status_names(text) -> set[str]:
    section = text.split("## Status line to reason", 1)[1].split("\n## ", 1)[0]
    return {name for line in section.splitlines() if line.startswith("|")
            for name in re.findall(r"`([a-z_]+)`", line.split("|")[1])}


def runner_status_names() -> set[str]:
    text = TEMPLATE.read_text(encoding="utf-8")
    match = re.search(r"^const STATUS_TABLE = \{(.*?)^\};", text, re.MULTILINE | re.DOTALL)
    assert match is not None
    return set(re.findall(r"^\s+([a-z_]+): \{", match.group(1), re.MULTILINE))


def template_allowlist(text):
    block = text.split("const RUNTIMES = {", 1)[1].split("\n};", 1)[0]
    parts = re.split(r"^  ([a-z][a-z0-9-]*): \{$", block, flags=re.MULTILINE)
    result = {}
    for name, body in zip(parts[1::2], parts[2::2], strict=True):
        match = re.search(r"reviewExtras: \[([^]]*)\]", body)
        if match:
            flags = re.findall(r"['\"](--[a-z-]+)['\"]", match.group(1))
            if flags:
                result[name] = flags
    return result


def opt_in_paragraph(text):
    return text.split("**Opt-in skills and MCP servers:**", 1)[1].split("\n\n", 1)[0]


def doc_allowlist(paragraph):
    text = paragraph.split("review allowlist (", 1)[1].split(")", 1)[0]
    return {part.split()[0]: re.findall(r"`(--[a-z-]+)", part) for part in text.split("; ")}


def allowlist_problems(doc_map, template_map):
    return [f"{key}: doc {doc_map.get(key)} template {template_map.get(key)}"
            for key in sorted(doc_map.keys() | template_map.keys())
            if doc_map.get(key) != template_map.get(key)]


class DispatchAndRunnerDocs(unittest.TestCase):
    def test_dispatch_names_the_vocabulary_and_group(self):
        text = DISPATCH.read_text(encoding="utf-8")
        for value in ("`--role review`", "`--host auto`", "`--session-id`", "`session=`",
                      "`applied`", "`ignored`", "`unknown`", "`escalate`", "cross-ai: setting"):
            self.assertIn(value, text)

    def test_dispatch_drops_the_old_mode_flag(self):
        self.assertNotIn("`--mode review`", DISPATCH.read_text(encoding="utf-8"))

    def test_dispatch_hosting_paragraph(self):
        text = DISPATCH.read_text(encoding="utf-8")
        for value in ("AIKIT_HOST=none", "HERDR_ENV=1", "no_herdr", "host_failed",
                      "ai-kit/spec/host/"):
            self.assertIn(value, text)

    def test_runner_md_lists_the_call_flags(self):
        text = RUNNER_MD.read_text(encoding="utf-8")
        template = TEMPLATE.read_text(encoding="utf-8")
        for flag in RUNNER_FLAGS:
            self.assertIn(flag, text)
            self.assertIn(f"'{flag}'", template)
        for value in ("AIKIT_HOST=none", "no_herdr", "host_failed", "ai-kit/spec/host/"):
            self.assertIn(value, text)

    def test_runner_md_review_allowlist_matches_template(self):
        template = template_allowlist(TEMPLATE.read_text(encoding="utf-8"))
        paragraph = opt_in_paragraph(RUNNER_MD.read_text(encoding="utf-8"))
        doc = doc_allowlist(paragraph)
        self.assertTrue(template)
        self.assertEqual(allowlist_problems(doc, template), [])
        for value in ("review allowlist", "--strict-mcp-config", "--additional-mcp-config"):
            self.assertIn(value, paragraph)
        for flags in doc.values():
            for flag in ("--mcp-config", "--strict-mcp-config", "--additional-mcp-config"):
                self.assertNotIn(flag, flags)

    def test_allowlist_check_catches_an_extra_or_misattributed_flag(self):
        template = template_allowlist(TEMPLATE.read_text(encoding="utf-8"))
        first = next(iter(template))
        extra = {key: list(value) for key, value in template.items()}
        extra[first].append("--extra-flag")
        moved = {key: list(value) for key, value in template.items()}
        moved["placeholder-cli-1"] = [moved[first].pop(0)]
        self.assertTrue(allowlist_problems(extra, template))
        self.assertTrue(allowlist_problems(moved, template))


class ReadmeAndProfileDocs(unittest.TestCase):
    def test_readme_rows_name_the_runner_facts(self):
        lines = README.read_text(encoding="utf-8").splitlines()
        cross = next(line for line in lines if line.startswith("| [`ai-kit-cross-ai`]"))
        curated = next(line for line in lines if line.startswith("| [`ai-kit-gsd-curated-config`]"))
        for value in ("settings report", "session ids", "`--argv-file`", "herdr",
                      "idle watchdog", "`locked`", "`partial`", "`--sweep`"):
            self.assertIn(value, cross)
        for value in ("cross-ai: setting", "`--host auto`", "`AIKIT_HOST=none`",
                      "no automatic fallback", "run lock"):
            self.assertIn(value, curated)

    def test_claude_profile_names_the_execute_formula(self):
        text = CLAUDE_PROFILE.read_text(encoding="utf-8")
        for value in ("execute formula", "unverified", "no_formula"):
            self.assertIn(value, text)
        for value in ("an exec attempt exits 2", "until it reads the runner's own"):
            self.assertNotIn(value, text)

    def test_spec_config_effort_sentence_names_the_generic_flag(self):
        self.assertNotIn("the runner passes it as `--codex-effort`",
                         SPEC_CONFIG_SKILL.read_text(encoding="utf-8"))


def review_module(name):
    sys.path.insert(0, str(ERROR_CLASSIFIER_DIR))
    try:
        return importlib.import_module(f"ai_kit_spec.{name}")
    finally:
        sys.path.remove(str(ERROR_CLASSIFIER_DIR))


def section_text(text, heading, stop=("## ",)):
    assert heading in text
    lines = text.splitlines()
    start = lines.index(heading)
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith(stop)), len(lines))
    return "\n".join(lines[start:end])


def table_names(text, header):
    assert header in text
    lines = text.splitlines()
    names = []
    for line in lines[lines.index(header) + 1:]:
        if not line.startswith("|"):
            break
        if re.fullmatch(r"\|[-| ]+\|", line):
            continue
        match = re.fullmatch(r"`([^`]+)`", line.split("|")[1].strip())
        assert match is not None
        names.append(match.group(1))
    return names


class SpecConfigAndConfigDocs(unittest.TestCase):
    def test_sorting_step_has_both_paths_and_the_confirm(self):
        sec = section_text(SPEC_CONFIG_SKILL.read_text(encoding="utf-8"),
                           "### Step 1.6 — Sort unknown skills (optional)", stop=("## ", "### "))
        for value in ("classify-skills --cwd", "advisory", "jev absent: nothing proposed",
                      "addressable", "Step 2.1", "confirm-skill-role --name", "--global",
                      "[skills.roles]", "user-stated", "never runs", "only after the owner agrees"):
            self.assertIn(value, sec)

    def test_capability_line_is_role_specific(self):
        self.assertIn("review-role dry run", SPEC_CONFIG_SKILL.read_text(encoding="utf-8"))

    def test_step_four_runs_config_status(self):
        sec = section_text(SPEC_CONFIG_SKILL.read_text(encoding="utf-8"),
                           "### Step 4 — Report", stop=("## ", "### "))
        for value in ("config-status --cwd <project root>",
                      "capability <runtime>/<model> <role>: <summary>", "pending",
                      "non-zero exit", "an earlier confirm stays written"):
            self.assertIn(value, sec)

    def test_never_list_forbids_an_unconfirmed_sort(self):
        self.assertIn("**Never write a skill role the owner did not confirm**",
                      SPEC_CONFIG_SKILL.read_text(encoding="utf-8"))

    def test_design_doc_names_every_sortable_role_and_the_keys(self):
        text = DESIGN.read_text(encoding="utf-8")
        for value in ("[skills.roles]", "edit_lens_pass", "[[models.context]]", "exit 65"):
            self.assertIn(value, text)
        for role in review_module("skill_table").ROLES:
            if role != "unsorted":
                self.assertIn(f"`{role}`", text)

    def test_readme_rows_name_the_block_and_the_sorter(self):
        text = README.read_text(encoding="utf-8")
        for value in ("capability block", "classify-skills", "confirm-skill-role"):
            self.assertIn(value, text)

    def test_new_text_names_no_model(self):
        for path in (SPEC_CONFIG_SKILL, DESIGN, README):
            self.assertEqual(scan_text(str(path), path.read_text(encoding="utf-8")), [])


class LaneCapabilitySkillTables(unittest.TestCase):
    def test_roles_lock_code_seed_file_and_table(self):
        sec = section_text(REVIEW_SKILL.read_text(encoding="utf-8"), SECTION)
        st = review_module("skill_table")
        self.assertEqual(table_names(sec, "| Role | Meaning |"), list(st.ROLES))
        self.assertEqual(list(st.ROLES),
                         json.loads(Path(st.SEED_PATH).read_text(encoding="utf-8"))["roles"])
        for row in st.load_seed():
            self.assertIn(row["role"], st.ROLES)
            self.assertNotEqual(row["role"], "unsorted")

    def test_refusal_reasons_table_equals_code_list(self):
        sec = section_text(REVIEW_SKILL.read_text(encoding="utf-8"), SECTION)
        self.assertEqual(table_names(sec, "| Reason | When |"),
                         list(review_module("prompt_guard").REFUSAL_REASONS))

    def test_lens_notes_table_equals_code_list(self):
        sec = section_text(REVIEW_SKILL.read_text(encoding="utf-8"), SECTION)
        self.assertEqual(table_names(sec, "| Note | When |"),
                         list(review_module("lens_delivery").LENS_NOTES))

    def test_each_item_has_exactly_one_row(self):
        sec = section_text(REVIEW_SKILL.read_text(encoding="utf-8"), SECTION)
        names = [name for header in ("| Role | Meaning |", "| Reason | When |", "| Note | When |")
                 for name in table_names(sec, header)]
        self.assertTrue(all(count == 1 for count in collections.Counter(names).values()))

    def test_refusal_exit_is_documented(self):
        sec = section_text(REVIEW_SKILL.read_text(encoding="utf-8"), SECTION)
        self.assertIn(f"exits {review_module('prompt_guard').REFUSED_EXIT}", sec)

    def test_block_sections_in_order(self):
        sec = section_text(REVIEW_SKILL.read_text(encoding="utf-8"), SECTION)
        line = next(line for line in sec.splitlines() if "`LANE`," in line)
        self.assertEqual(re.findall(r"`([A-Z ]+)`", line),
                         list(review_module("capability_block").SECTIONS))

    def test_config_keys_and_commands_named(self):
        sec = section_text(REVIEW_SKILL.read_text(encoding="utf-8"), SECTION)
        for value in ("[skills.roles]", "[review] edit_lens_pass", "[[models.context]]",
                      "capability-block", "skill-table", "edit-lens-pass --cwd", "--accept",
                      "--reject", "never starts it", "changed after",
                      "neither recorded nor restored",
                      "replaces the host's other MCP servers for that lane"):
            self.assertIn(value, sec)

    def test_new_text_names_no_model(self):
        sec = section_text(REVIEW_SKILL.read_text(encoding="utf-8"), SECTION)
        self.assertEqual(scan_text(str(REVIEW_SKILL), sec), [])


class LaneCapabilityReferences(unittest.TestCase):
    def test_capabilities_fields_and_values(self):
        sec = section_text(DISPATCH.read_text(encoding="utf-8"), "## Lane capabilities")
        for phrase in ("cross-ai: capabilities", "`{value, label}`", "an object `{state, source}`",
                       "`verified`, `unverified` or `unknown`", "`{channel, max_bytes}`"):
            self.assertIn(phrase, sec)
        self.assertNotIn("<state>: <source>", sec)
        fields = {"write": ("none", "workspace", "full", "unknown"),
                  "shell": ("yes", "no", "unknown"),
                  "skills": ("none", "path", "discovery", "unknown"),
                  "mcp": ("none", "host_config", "call_file", "unknown"),
                  "prompt": ("argv", "stdin", "max_bytes")}
        for field, values in fields.items():
            line = next(line for line in sec.splitlines() if line.startswith(f"| `{field}` |"))
            for value in values:
                self.assertIn(f"`{value}`", line)

    def test_point_zero_is_the_child_path_rule(self):
        text = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("found on the PATH of that lane's exact child environment", text)
        self.assertNotIn('python3 "$TOOLS_PY" detect-tools', text)

    def test_dispatch_passes_files_not_the_parent_map(self):
        skill, dispatch, prompts = (p.read_text(encoding="utf-8")
                                    for p in (REVIEW_SKILL, DISPATCH, PROMPTS))
        for text in (skill, dispatch, prompts):
            self.assertNotIn("TOOL_AVAILABILITY_JSON", text)
        for text in (skill, prompts):
            self.assertNotIn("--tool-availability-json", text)
        for text in (skill, dispatch):
            self.assertIn("--files <each DOC_PATHS entry> <each GROUNDING_DOCS entry, if any> "
                          "<CHECKLIST_SKILL_MD> <FRAMEWORK_PROFILE_PATH, unless none>", text)
            for phrase in ("one worktree at a time", "inside CODEBASE_ROOT", "--files` is refused"):
                self.assertNotIn(phrase, text)
        self.assertIn("documents from other worktrees: <n> (<root>, ...)", dispatch)
        self.assertIn("ai-kit-spec: no capability block built: no --files given "
                      "(pass --files to get the lane's capability block)", dispatch)
        self.assertIn("replaces the host's other MCP servers for that lane", dispatch)

    def test_native_route_makes_no_tool_claim(self):
        text = PROMPTS.read_text(encoding="utf-8")
        for phrase in ("- TOOL_AVAILABILITY = {}", "- LENS LINES: <LENS_LINES>",
                       "--role review --native --cwd <CODEBASE_ROOT>", "SHARED_TOOLING_PATH"):
            self.assertIn(phrase, text)
        self.assertNotIn("skill-table", text)

    def test_guidance_reads_the_block(self):
        text = GUIDANCE.read_text(encoding="utf-8")
        self.assertIn("capability block", text)
        self.assertIn("`CODE INDEX`", text)

    def test_lane_reference_text_names_no_model(self):
        for path in (DISPATCH, PROMPTS, GUIDANCE):
            self.assertEqual(scan_text(str(path), path.read_text(encoding="utf-8")), [])


class SupervisionDocsText(unittest.TestCase):
    def test_dispatch_table_covers_every_runner_status(self):
        text = DISPATCH.read_text(encoding="utf-8")
        self.assertTrue(runner_status_names() <= dispatch_status_names(text))

    def test_new_statuses_map_to_real_error(self):
        row = next(line for line in DISPATCH.read_text(encoding="utf-8").splitlines()
                   if "`partial`" in line and line.startswith("|"))
        self.assertIn("`locked`", row)
        self.assertTrue(row.endswith("| `real_error` |"))
        sys.path.insert(0, str(ERROR_CLASSIFIER_DIR))
        try:
            from ai_kit_spec.error_classifier import STATUS_TO_REASON

            self.assertEqual(STATUS_TO_REASON["partial"], "real_error")
            self.assertEqual(STATUS_TO_REASON["locked"], "real_error")
        finally:
            sys.path.remove(str(ERROR_CLASSIFIER_DIR))

    def test_dispatch_names_the_check_group_and_sweep(self):
        text = DISPATCH.read_text(encoding="utf-8")
        for value in ("`coverage`", "`findings`", "cross-ai: finding reason=", "--sweep",
                      "complete label", "cross-ai: note: an execute run holds this checkout"):
            self.assertIn(value, text)

    def test_runner_md_names_the_supervision_flags(self):
        text = RUNNER_MD.read_text(encoding="utf-8")
        template = TEMPLATE.read_text(encoding="utf-8")
        for flag in SUPERVISION_FLAGS:
            self.assertIn(flag, text)
            self.assertIn(f"'{flag}'", template)
        for value in ("idleTimeoutS", "forbiddenPaths", "admissionPhrases", "`locked`",
                      "`partial`", "coverage=", "findings="):
            self.assertIn(value, text)

    def test_status_scan_catches_a_missing_status(self):
        text = DISPATCH.read_text(encoding="utf-8")
        text = text.replace(", `locked` | `real_error` |", " | `real_error` |")
        self.assertFalse(runner_status_names() <= dispatch_status_names(text))

    def test_curated_skill_names_the_new_rules(self):
        text = CURATED_SKILL.read_text(encoding="utf-8")
        step =text.split("3. **Review the plan with the user**", 1)[1].split("```", 1)[0]
        for value in ("cross_ai_timeout", "1800", "current value",
                      "owner's router naming convention"):
            self.assertIn(value, step)
        refusal = text.split("**Refusals `--force` cannot bypass:**", 1)[1].split("\n- ", 1)[0]
        self.assertIn("buildAgentSkillsBlock", refusal)

    def test_curated_exit_sentence_names_the_new_statuses(self):
        text = CURATED_SKILL.read_text(encoding="utf-8").split("These are this CLI's exits.", 1)[1]
        paragraph = text.split("\n\n", 1)[0]
        for value in ("`partial`", "`locked`", "idle watchdog"):
            self.assertIn(value, paragraph)


class MarkedRegionInRunner(unittest.TestCase):
    def test_marker_covers_only_its_region_in_the_runner(self):
        bad = "/".join(("qqvendor", "qqmodel-7"))
        path = "skills/ai-kit-spec-review/references/cross-ai.mjs"
        base = TEMPLATE.read_text(encoding="utf-8").rstrip("\n").splitlines()
        n = len(base)
        first = "// model-example: `" + bad + "`"
        second = "// `" + bad + "` stays inside the marked region"
        third = "// `" + bad + "` sits beside the marked region"
        with_beside = "\n".join([*base, first, second, third]) + "\n"
        inside_only = "\n".join([*base, first, second]) + "\n"
        self.assertEqual([hit for hit in scan_text(path, with_beside) if hit[0] > n],
                         [(n + 3, "slash", bad)])
        self.assertEqual([hit for hit in scan_text(path, inside_only) if hit[0] > n], [])


if __name__ == "__main__":
    unittest.main()
