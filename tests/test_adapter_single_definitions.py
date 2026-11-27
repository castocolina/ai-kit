"""The adapter's pinned resume and owner stop are each defined once.

Every other file links there.
"""

import pathlib
import re
import shutil
import tempfile
import unittest

SKILL_DIR = (
    pathlib.Path(__file__).resolve().parents[1] / "skills" / "ai-kit-spec-execute-superpowers"
)
MARKERS = {
    "## Pinned resume": "state-management.md",
    "## Owner stop": "resolution-stops.md",
    "## Host-config audit": "dispatch-external-cli.md",
    "## Lane transport": "dispatch-external-cli.md",
    "## Executor pick": "dispatch-external-cli.md",
    "<!-- lite-block:start -->": "lite-block.md",
    "## Code review (after the final review, before Step 5)": "SKILL.md",
}
RULES = {
    "re-dispatches unchanged at any": "state-management.md",
    "is only the source of `ladder_keys`": "state-management.md",
    "a bare 75 and any other quota class are owner stops": "resolution-stops.md",
    "is classified `quota` but is an owner stop": "resolution-stops.md",
    'Only a classified `"quota_cycle"`': "resolution-stops.md",
    "not a stop; Classify continues": "resolution-stops.md",
    "resumable state, then STOP this wave and report the reasons per key": "resolution-stops.md",
    "cannot honor the capability bump": "resolution-stops.md",
    "no pick is a verified bump": "resolution-stops.md",
    "of the automatic round (the gate ran this round) must be a key the gate allowed": (
        "escalation.md"
    ),
    "Session-model fallback first.": "resolution-stops.md",
    "write `$RUN_DIR/gates.txt` with the project's gate commands": "SKILL.md",
    "**Gates and commit guard.**": "dispatch-external-cli.md",
    (
        "snapshots the modification times of these files under the lane's HOME "
        "before and after the lane"
    ): "dispatch-external-cli.md",
    "**Flagged switch.** Runs for every classified": "dispatch-external-cli.md",
    "renewed after three rounds, before a round starts": "dispatch-external-cli.md",
    "executor pick: <dispatched key> (default: ": "dispatch-external-cli.md",
}
# The links SKILL.md must hold.
LINKS = (
    "references/state-management.md#pinned-resume",
    "references/resolution-stops.md#owner-stop",
    "references/escalation.md",
    "references/dispatch-external-cli.md#host-config-audit",
    "references/code-review.md",
    "references/lite-block.md",
)
# The sibling-relative links each reference file must hold.
SOURCE_LINKS = {
    "escalation.md": ("state-management.md#pinned-resume", "resolution-stops.md#owner-stop"),
    "session-wake.md": ("resolution-stops.md#owner-stop",),
    "state-management.md": ("resolution-stops.md#owner-stop",),
    "quota-wake.md": ("state-management.md#pinned-resume",),
    "dispatch-external-cli.md": (
        "state-management.md#pinned-resume",
        "resolution-stops.md#owner-stop",
    ),
}
HOMES = ("state-management.md", "resolution-stops.md", "dispatch-external-cli.md")
ANCHOR_LINK = re.compile(r"\]\(([^)\s#]+)#([^)\s]+)\)")


def docs(root: pathlib.Path) -> dict:
    """Map SKILL.md and every reference (but design-notes.md) to its text."""
    found = {"SKILL.md": (root / "SKILL.md").read_text(encoding="utf-8")}
    for path in sorted((root / "references").glob("*.md")):
        if path.name != "design-notes.md":
            found[path.name] = path.read_text(encoding="utf-8")
    return found


def doc_path(root: pathlib.Path, name: str) -> pathlib.Path:
    """Return the path of a doc by its name."""
    return root / name if name == "SKILL.md" else root / "references" / name


def marker_files(root: pathlib.Path, marker: str) -> list:
    """Return one name per line that equals the marker."""
    names: list = []
    for name, text in docs(root).items():
        names.extend([name] * sum(1 for line in text.splitlines() if line.rstrip() == marker))
    return names


def rule_files(root: pathlib.Path, phrase: str) -> list:
    """Return one name per occurrence of the phrase."""
    names: list = []
    for name, text in docs(root).items():
        flat = " ".join(text.split())
        names.extend([name] * flat.count(phrase))
    return names


def slug(heading: str) -> str:
    """Return the anchor slug of a heading line."""
    return re.sub(r"[^a-z0-9 -]", "", heading.lstrip("#").strip().lower()).replace(" ", "-")


def link_problems(root: pathlib.Path) -> list:
    """Return the links to a home whose file or heading does not exist."""
    problems: list = []
    for name, text in docs(root).items():
        for target, anchor in ANCHOR_LINK.findall(text):
            if target.rsplit("/", 1)[-1] not in HOMES:
                continue
            path = doc_path(root, name).parent / target
            if not path.is_file():
                problems.append(f"{name}: {target}#{anchor}")
                continue
            heads = [
                line
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.startswith(("## ", "### "))
            ]
            if not any(slug(line) == anchor for line in heads):
                problems.append(f"{name}: {target}#{anchor}")
    return problems


def missing_links(root: pathlib.Path) -> list:
    """Return the required sibling links a reference file lacks."""
    texts = docs(root)
    return [
        f"{name}: {link}"
        for name, links in SOURCE_LINKS.items()
        for link in links
        if f"]({link})" not in texts[name]
    ]


class TestSingleDefinitions(unittest.TestCase):
    def test_each_source_links_its_home(self):
        self.assertEqual([], missing_links(SKILL_DIR))

    def test_kept_handoff_text(self):
        flat = " ".join(docs(SKILL_DIR)["quota-wake.md"].split())
        self.assertIn("it does not pick another candidate.", flat)
        self.assertIn("printf 'LAST_DISPATCHED_KEY=%s", docs(SKILL_DIR)["dispatch-external-cli.md"])

    def test_each_marker_once(self):
        for marker, home in MARKERS.items():
            self.assertEqual([home], marker_files(SKILL_DIR, marker), marker)

    def test_each_rule_only_in_its_home(self):
        for phrase, home in RULES.items():
            self.assertEqual([home], rule_files(SKILL_DIR, phrase), phrase)

    def test_skill_links_the_homes(self):
        text = docs(SKILL_DIR)["SKILL.md"]
        for link in LINKS:
            self.assertIn(link, text)

    def test_links_to_the_homes_resolve(self):
        self.assertEqual([], link_problems(SKILL_DIR))

    def test_no_config_check_comes_first(self):
        text = docs(SKILL_DIR)["SKILL.md"]
        self.assertLess(
            text.index("**No-config check, before the start step"),
            text.index("references/start-step.md"),
        )
        self.assertLess(text.index("references/start-step.md"), text.index("**Resume check"))

    def test_a_planted_second_copy_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "skill"
            shutil.copytree(SKILL_DIR, copy)
            refs = copy / "references"
            with (refs / "escalation.md").open("a", encoding="utf-8") as handle:
                handle.write(
                    "\n## Pinned resume\n\n"
                    "A restored injection re-dispatches unchanged at any round.\n"
                )
            self.assertEqual(2, len(marker_files(copy, "## Pinned resume")))
            self.assertEqual(2, len(rule_files(copy, "re-dispatches unchanged at any")))
            with (refs / "state-management.md").open("a", encoding="utf-8") as handle:
                handle.write("\nIt re-dispatches unchanged at any round.\n")
            self.assertEqual(
                2, rule_files(copy, "re-dispatches unchanged at any").count("state-management.md")
            )
            with (refs / "quota-wake.md").open("a", encoding="utf-8") as handle:
                handle.write("\n[x](references/state-management.md#pinned-resume)\n")
                handle.write("\n## Owner stop\n")
            self.assertEqual(2, len(marker_files(copy, "## Owner stop")))
            problems = link_problems(copy)
            self.assertEqual(1, len(problems), problems)
            self.assertTrue(problems[0].startswith("quota-wake.md:"))

    def test_a_removed_pointer_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "skill"
            shutil.copytree(SKILL_DIR, copy)
            path = copy / "references" / "quota-wake.md"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace("](state-management.md#pinned-resume)", "](state-management.md)"),
                encoding="utf-8",
            )
            self.assertEqual(
                ["quota-wake.md: state-management.md#pinned-resume"], missing_links(copy)
            )


class TestNewTopicHomes(unittest.TestCase):
    def test_skill_md_holds_no_topic_detail(self):
        text = docs(SKILL_DIR)["SKILL.md"]
        self.assertNotIn(".copilot/mcp-config.json", text)
        self.assertNotIn("SWITCH_INJECTION_JSON", text)
        self.assertNotIn("## Host-config audit", text)

    def test_a_second_copy_of_a_new_rule_is_caught(self):
        sentence = "**Flagged switch.** Runs for every classified"
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "skill"
            shutil.copytree(SKILL_DIR, copy)
            refs = copy / "references"
            extra = "\n" + sentence + " quota stop.\n"
            with (refs / "state-management.md").open("a", encoding="utf-8") as handle:
                handle.write(extra)
            self.assertEqual(
                ["dispatch-external-cli.md", "state-management.md"],
                sorted(rule_files(copy, sentence)),
            )
            with (refs / "dispatch-external-cli.md").open("a", encoding="utf-8") as handle:
                handle.write(extra)
            self.assertEqual(2, rule_files(copy, sentence).count("dispatch-external-cli.md"))
            with (refs / "quota-wake.md").open("a", encoding="utf-8") as handle:
                handle.write("\n## Host-config audit\n")
            self.assertEqual(2, len(marker_files(copy, "## Host-config audit")))


if __name__ == "__main__":
    unittest.main()
