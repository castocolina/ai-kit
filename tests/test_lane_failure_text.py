"""references/lane-failure.md: reason table equals REASONS; docs name the lane-failure behaviour."""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "ai-kit-spec-review"))

from ai_kit_spec.error_classifier import REASONS

LANE_FAILURE = REPO / "skills/ai-kit-spec-review/references/lane-failure.md"
REVIEW_SKILL = REPO / "skills/ai-kit-spec-review/SKILL.md"
DISPATCH = REPO / "skills/ai-kit-spec-review/references/cross-ai-dispatch.md"
CROSS_AI_SKILL = REPO / "skills/ai-kit-cross-ai/SKILL.md"
EXCEPTION = (
    "The one exception is the owner's own choice: ai-kit-spec-review runs the configured "
    "fallback of a lane the owner flagged usage_limited after that lane's quota stop "
    "(its references/lane-failure.md)."
)
SWITCH_FIRST_RESUME = "first, on any nonzero exit, when a round log exists"
EXIT75_BULLET = "   - exit 75 with `retry_after_s=` again:"
FOLD_FIRST = "run SKILL.md Step 1's fold check first, before Step 1.5"
SECTIONS = (
    "## Ping before a round",
    "## Flagged-lane switch",
    "## Partial status",
    "## Reasons",
    "## jev classes and sizing",
    "## Commands",
    "## Evidence",
)
KEY_RE = re.compile(r"^\| `([a-z_]+)` \|", re.MULTILINE)
SUMMARIES_ONLY = (
    "It receives summaries only: never code, diffs, file contents, config values or secrets."
)
COMMANDS = (
    "size-review",
    "ping-lanes",
    "switch-lane",
    "check-fold-step",
    "classify-disagreements",
    "merge-reports",
    "dispatch-reviewer",
    "--lane-log",
    "--extra-findings",
    "--owner-out",
)


NARROWED = (
    "Never re-dispatch a failed unflagged lane to another CLI, provider, model or the native "
    "session; a lane the owner flagged usage_limited that fails with reason quota switches once "
    "to its fallback (references/lane-failure.md)."
)
PINNED = (
    "Never switch harness, provider or model. The one exception is the flagged-lane switch in "
    "references/lane-failure.md."
)
OLD_BLANKET = "failed subprocess lane"


def blanket_lines(text):
    return [line for line in text.splitlines() if OLD_BLANKET in line]


def section(text, heading):
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


def table_keys(text):
    return KEY_RE.findall(section(text, "## Reasons"))


class TestReasonTable(unittest.TestCase):
    def setUp(self):
        self.text = LANE_FAILURE.read_text(encoding="utf-8")

    def test_reason_table_equals_reasons(self):
        keys = table_keys(self.text)
        self.assertEqual(sorted(keys), sorted(REASONS))
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(keys), 13)

    def test_lock_catches_an_added_or_removed_key(self):
        added = self.text.replace("| `quota` |", "| `zzz_new` | x |\n| `quota` |", 1)
        removed = self.text.replace("| `git_timeout` |", "| git_timeout |", 1)
        self.assertNotEqual(set(table_keys(added)), set(REASONS))
        self.assertNotEqual(set(table_keys(removed)), set(REASONS))


class TestLaneFailureDoc(unittest.TestCase):
    def setUp(self):
        self.text = LANE_FAILURE.read_text(encoding="utf-8")

    def test_sections_in_order(self):
        indices = [self.text.index(h) for h in SECTIONS]
        self.assertEqual(indices, sorted(indices))
        self.assertEqual(SECTIONS[-1], "## Evidence")
        self.assertEqual(self.text.count("\n## "), len(SECTIONS))
        self.assertEqual(self.text.rfind("\n## "), self.text.index("\n## Evidence"))

    def test_jev_gets_summaries_only(self):
        self.assertIn(SUMMARIES_ONLY, section(self.text, "## jev classes and sizing"))

    def test_blocked_until_reader(self):
        self.assertIn("--blocked-status <pool>", section(self.text, "## Flagged-lane switch"))
        self.assertNotIn("PROVISIONAL", self.text)

    def test_status_wordings(self):
        self.assertIn("Approved (partial)", self.text)
        self.assertIn("not reviewed", self.text)

    def test_commands_section_names_every_command(self):
        commands = section(self.text, "## Commands")
        for name in COMMANDS:
            with self.subTest(name=name):
                self.assertIn(name, commands)


class TestReviewSkillRule(unittest.TestCase):
    def setUp(self):
        self.text = REVIEW_SKILL.read_text(encoding="utf-8")

    def test_narrowed_rule_present(self):
        for needle in (NARROWED, PINNED, "never switch lanes after a refusal"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_old_blanket_rule_absent(self):
        self.assertEqual(blanket_lines(self.text), [])
        old = (
            "Never re-dispatch a " + OLD_BLANKET
            + " to another CLI, provider, model or the native session."
        )
        self.assertNotEqual(blanket_lines(self.text.replace(NARROWED, old)), [])

    def test_status_wordings(self):
        self.assertIn("Approved (partial)", self.text)
        self.assertIn("not reviewed", self.text)

    def test_ping_runs_whatever_size_review_exited(self):
        para = next(
            ln for ln in self.text.splitlines() if ln.startswith("**Ping before the round**"))
        self.assertIn("whatever `size-review` exited", para)
        self.assertNotIn("whenever `$RUN_TMP_DIR/lanes.jsonl` exists", para)
        doc = LANE_FAILURE.read_text(encoding="utf-8")
        self.assertIn("A nonzero exit leaves `reviewers.json` unchanged:", doc)
        self.assertNotIn("A nonzero exit leaves `reviewers.json` and the round log unchanged", doc)
        self.assertIn("the ping still runs before round 1 and starts the round log", doc)

    def test_steps_point_to_the_new_commands(self):
        for needle in (
            "references/lane-failure.md",
            "size-review",
            "ping-lanes",
            "switch-lane",
            "check-fold-step",
            "--extra-findings",
            "--lane-log",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)


def switch_first(p5):
    return (
        SWITCH_FIRST_RESUME in p5
        and EXIT75_BULLET in p5
        and p5.index(SWITCH_FIRST_RESUME) < p5.index(EXIT75_BULLET)
    )


class TestWiringDocs(unittest.TestCase):
    def test_partial_outcome_is_kept(self):
        skill = REVIEW_SKILL.read_text(encoding="utf-8")
        self.assertIn("Approved (partial)", section(skill, "## Cleanup"))
        self.assertIn("Approved (partial)", section(skill, "### Step 5"))

    def test_dispatch_reference_logged_and_switch_first(self):
        text = DISPATCH.read_text(encoding="utf-8")
        sec = section(text, "## Step 1 subprocess dispatch")
        self.assertIn("switch-lane", sec)
        self.assertIn("merge-reports --lane-log", sec)
        pend = section(text, "## Pending lane (hard tier)")
        self.assertIn('--lane-log "$RUN_TMP_DIR/lanes.jsonl" --round <N>', pend)
        self.assertIn("switch-lane", pend)

    def test_dispatch_reference_sizes_after_resolve(self):
        text = DISPATCH.read_text(encoding="utf-8")
        start = text.index("5. Resolve the reviewer list")
        end = text.index("6. **(Active cross-AI path only")
        self.assertIn("size-review", text[start:end])

    def test_cross_ai_never_switch_names_one_exception(self):
        sec = section(CROSS_AI_SKILL.read_text(encoding="utf-8"), "## 8. Never switch")
        self.assertIn(EXCEPTION, sec)
        self.assertIn("Never switch harness, provider or model", sec)

    def test_resume_switches_first_and_folds_before_merge(self):
        text = DISPATCH.read_text(encoding="utf-8")
        pend = section(text, "## Pending lane (hard tier)")
        p5 = pend[pend.index("5. **On the re-invoke**") :]
        self.assertTrue(switch_first(p5))
        self.assertLess(
            p5.index(FOLD_FIRST), p5.index("then merge this lane with the sibling's report")
        )
        self.assertIn("re-read now", p5)
        for needle in ('quota_json "$QUOTA_JSON"', "lane_log ", "framework_id ", "doc_archetypes "):
            with self.subTest(needle=needle):
                self.assertIn(needle, pend)
        bad = p5.replace(SWITCH_FIRST_RESUME, "x", 1).replace(
            EXIT75_BULLET, EXIT75_BULLET + " " + SWITCH_FIRST_RESUME, 1
        )
        self.assertFalse(switch_first(bad))


LOOP_DIAGRAM = REPO / "skills/ai-kit-spec-review/references/loop-diagram.md"


class TestLoopDiagram(unittest.TestCase):
    def setUp(self):
        self.text = LOOP_DIAGRAM.read_text(encoding="utf-8")

    def test_diagram_shows_ping_switch_and_partial(self):
        for needle in (
            "ping-lanes",
            "switch-lane",
            "check-fold-step",
            "classify-disagreements",
            '"Approved (partial)"',
            '"No lane left"',
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_logged_path_is_conditional(self):
        for needle in (
            '[label="--no-cross-ai or session default: no sizing, no ping"]',
            '[label="active cross-AI path"]',
            '[label="round log exists"]',
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_next_iterations_go_through_the_ping(self):
        for label in (
            '[label="Edits Applied (next iter)"]',
            '[label="Edits Applied (no validate, next iter)"]',
            '[label="yes (no validate, next iter)"]',
            '[label="sound (next iter)"]',
        ):
            with self.subTest(label=label):
                self.assertIn('-> "Ping lanes (ping-lanes)" ' + label, self.text)


APPLY_FINDINGS = REPO / "skills/ai-kit-spec-review/references/apply-findings.md"
APPLY_SUMMARIES = (
    "jev receives summaries only: never code, diffs, file contents, config values or secrets."
)


def subsection(text, heading):
    start = text.index(heading)
    end = text.find("\n### ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


class TestApplyFindings(unittest.TestCase):
    def setUp(self):
        self.text = APPLY_FINDINGS.read_text(encoding="utf-8")

    def test_round_context_names_ping_switch_partial(self):
        for needle in ("ping-lanes", "switch-lane", "Approved (partial)"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_classify_and_repass_line(self):
        for needle in (
            "classify-disagreements",
            "- Mechanical re-pass: <MECHANICAL_TITLES>",
            APPLY_SUMMARIES,
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_fold_finding_reaches_writing_plans(self):
        sl = self.text[self.text.index("#### Step 3b-skill") : self.text.index("#### Step 3b-cmd")]
        for needle in (
            "Fold the plan's commits (ai-kit-commit-fold)",
            "superpowers:writing-plans",
            "last ### Task",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, sl)


class TestSkillClassifyWiring(unittest.TestCase):
    def setUp(self):
        self.skill = REVIEW_SKILL.read_text(encoding="utf-8")

    def test_classify_runs_on_any_listed_skip(self):
        sec = subsection(self.skill, "### Step 4")
        for needle in (
            "**Classify first.**",
            "whatever its Status line",
            "at most one re-pass per iteration",
            "--owner-out $RUN_TMP_DIR/owner-items.json",
            "the fixer processes only those findings",
            'with no "Decide manually"',
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, sec)
        row = [ln for ln in sec.splitlines() if ln.startswith("| `### Status: Edits Applied`")]
        self.assertEqual(len(row), 1)
        self.assertIn(
            "Classify first when the summary lists an escalated or skipped finding.", row[0]
        )

    def test_cap_row_classifies(self):
        step2 = subsection(self.skill, "### Step 2").splitlines()
        head = "| `### Status: Issues Found — fix and re-invoke` |"
        issues = [ln for ln in step2 if ln.startswith(head)]
        self.assertEqual(len(issues), 1)
        self.assertIn("--cap-reached", issues[0])
        self.assertIn("--owner-out", issues[0])
        step5 = subsection(self.skill, "### Step 5").splitlines()
        cap = [ln for ln in step5 if ln.startswith("| Cap reached |")]
        self.assertEqual(len(cap), 1)
        for needle in (
            "Drop `Decide manually.` only when this cap's `classify-disagreements` exited 0",
            "holds no item",
            "without `TOOLS_PY` or on a nonzero exit, keep `Decide manually.`",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, cap[0])
        self.assertNotIn("with none, drop `Decide manually.`", cap[0])

    def test_surface_names_jev_routes(self):
        sec = subsection(self.skill, "### Step 5")
        for needle in (
            "(jev: <class> <confidence>, advisory)",
            "skipped (jev: reviewer_wrong",
            "lists the items of `$RUN_TMP_DIR/owner-items.json` as owner decisions",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, sec)


# The two safety snippets of cross-ai-dispatch.md, run as written: the resume wrapper always
# leaves a terminal `.exit` record, and the run folder removal deletes only a folder this run
# marked as its own under the temp root.
def _snippet(pattern, flags):
    match = re.search(pattern, DISPATCH.read_text(encoding="utf-8"), flags)
    return match.group(1) if match else ""


WRAPPER = _snippet(r"```bash\n(python3 -c 'import json,subprocess,sys\n.*?)```", re.S)
MARKER = _snippet(r"^   (python3 -c 'import os,sys; d=os\.path\.realpath.*)$", re.M)
REMOVE = _snippet(r"^(python3 -c 'import os,shutil,sys;.*)$", re.M)


def _bash(cmd, env=None):
    return subprocess.run(["bash", "-c", cmd], env=env, capture_output=True, text=True,
                          check=False, timeout=60)


class TestResumeWrapperSnippet(unittest.TestCase):
    def _run(self, argv_text):
        with tempfile.TemporaryDirectory() as tmp:
            lane = Path(tmp) / "lane"
            Path(f"{lane}-argv.json").write_text(argv_text, encoding="utf-8")
            _bash(WRAPPER.replace("$RUN_TMP_DIR/iter<N>-<key>", str(lane)))
            return (Path(f"{lane}.exit").read_text(encoding="utf-8").strip(),
                    Path(f"{lane}.err").read_text(encoding="utf-8"))

    def test_snippets_present(self):
        for snippet in (WRAPPER, MARKER, REMOVE):
            self.assertTrue(snippet)

    def test_success_writes_the_child_exit_code(self):
        self.assertEqual(self._run('["true"]')[0], "0")

    def test_launch_errors_still_write_a_record(self):
        for argv in ('["/nonexistent/ai-kit-no-such-binary"]', "{not json", '{"a": 1}'):
            with self.subTest(argv=argv):
                code, err = self._run(argv)
                self.assertEqual(code, "127")
                self.assertIn("cross-ai: resume launch failed:", err)


class TestRunFolderRemovalSnippet(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.root = self.base / "root"
        self.root.mkdir()
        self.env = {**os.environ, "TMPDIR": str(self.root)}

    def _sh(self, cmd, path):
        return _bash(cmd.replace('"$RUN_TMP_DIR"', f"'{path}'"), self.env)

    def _made(self, name, marked=True, parent=None):
        d = (parent or self.root) / name
        d.mkdir()
        if marked:
            self._sh(MARKER, d)
        return d

    def test_removes_its_own_folder(self):
        d = self._made("repo-br-feat-iter-aaaaaa")
        self.assertEqual(self._sh(REMOVE, d).returncode, 0)
        self.assertFalse(d.exists())

    def test_keeps_every_unverified_folder(self):
        real = self._made("repo-br-feat-iter-cccccc")
        link = self.root / "link-iter-cccccc"
        link.symlink_to(real)
        forged = self._made("repo-br-feat-iter-eeeeee", marked=False)
        (forged / ".aikit-run-id").write_text("/elsewhere\n", encoding="utf-8")
        cases = {
            "no marker": (self._made("repo-br-feat-iter-bbbbbb", marked=False), None),
            "symlink": (link, real),
            "outside root": (self._made("repo-br-feat-iter-dddddd", parent=self.base), None),
            "wrong marker": (forged, None),
            "no -iter- name": (self._made("repo-br-feat-xxxxxx"), None),
        }
        for name, (path, kept) in cases.items():
            with self.subTest(case=name):
                result = self._sh(REMOVE, path)
                self.assertEqual(result.returncode, 3)
                self.assertIn("ownership not verified", result.stdout)
                self.assertTrue((kept or path).exists())


if __name__ == "__main__":
    unittest.main()
