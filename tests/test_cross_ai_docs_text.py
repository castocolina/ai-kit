"""37-22: pin runner documentation, hosting and marked-region adjacency (SPEC R11)."""

import re
import unittest
from pathlib import Path

from tests.test_arch_hardcoded_models import scan_text

REPO = Path(__file__).resolve().parent.parent
DISPATCH = REPO / "skills/ai-kit-spec-review/references/cross-ai-dispatch.md"
RUNNER_MD = REPO / "skills/ai-kit-gsd-curated-config/references/runner.md"
README = REPO / "README.md"
CLAUDE_PROFILE = REPO / "skills/ai-kit-spec-review/references/cli-profiles/claude.md"
SPEC_CONFIG_SKILL = REPO / "skills/ai-kit-spec-config/SKILL.md"
TEMPLATE = REPO / "skills/ai-kit-spec-review/references/cross-ai.mjs"
RUNNER_FLAGS = (
    "--role", "--effort", "--codex-effort", "--context", "--escalate-runtime",
    "--escalate-model", "--session-id", "--host", "--skill-path", "--skill-name",
    "--mcp-config", "--argv-file", "--describe",
)


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
        for value in ("settings report", "session ids", "`--argv-file`", "herdr"):
            self.assertIn(value, cross)
        for value in ("cross-ai: setting", "`--host auto`", "`AIKIT_HOST=none`",
                      "no automatic fallback"):
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
