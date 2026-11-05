"""Black-box text test for the jev-fast-decision callers (Phase 29, SPEC R10, JEV-06).

The prose and generated text of every caller of jev-fast-decision names no backend, consent step
or probe status, and a caller SKILL.md that mentions jev says that `needs_fallback` or no answer
leaves the decision to the default. Only skills/jev-fast-decision/ may name those details.

Reads skills/ and tests/fixtures/ only (never .planning/, never a host config) and writes no file.
The goal-prompt builders are read through gp_sections, the way the golden test imports them.
"""

import ast
import glob
import os
import re
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKILLS = os.path.join(REPO, "skills")
SCRIPTS = os.path.join(SKILLS, "ai-kit-spec-goal-prompt", "scripts")
GOLDEN_DIR = os.path.join(REPO, "tests", "fixtures", "goal_prompt", "golden")
EXEMPT_SKILL = "jev-fast-decision"
CALLERS = (
    "ai-kit-gsd-spec-discuss",
    "ai-kit-commit-fold",
    "ai-kit-spec-goal-prompt",
    "ai-kit-spec-execute-superpowers",
)
_TERMS = (
    ("laya", r"laya"),
    ("typesafe", r"typesafe"),
    ("opencode zen", r"opencode\s+zen"),
    ("zen", r"\bzen\b"),
    ("system one", r"system\s+one"),
    ("consent", r"consent"),
    ("--probe", r"--probe"),
    ("missing_api_key", r"missing_api_key"),
    ("backend_unavailable", r"backend_unavailable"),
    ("key_check", r"key_check"),
    ("key_source", r"key_source"),
    ("JEV_BACKEND", r"JEV_BACKEND"),
    ("JEV_ALLOW_REMOTE", r"JEV_ALLOW_REMOTE"),
    ("JEV_MIN_CONFIDENCE", r"JEV_MIN_CONFIDENCE"),
    ("decide.py", r"decide\.py"),
)
# Case-insensitive on purpose: "OpenCode Zen", "opencode zen" and "LAYA" all count.
FORBIDDEN = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in _TERMS}
JEV_MENTION = re.compile(r"\bjev", re.IGNORECASE)
FALLBACK_RULE = re.compile(
    r"needs_fallback[^.]{0,80}no answer|no answer[^.]{0,80}needs_fallback", re.IGNORECASE
)
_WRITE_METHODS = frozenset({"write_text", "write_bytes", "unlink", "rmtree", "mkdir", "makedirs"})
# The unit flow's push consent (commit-fold's per-repository push approval) is not the jev
# backend consent this rule guards. Only its literal flow forms are cleared: the skipped-push
# outcome, the `fold.py consent` verbs, "push consent", the settings key's gloss and the
# `no_consent` reason code. Any other consent wording, such as "no consent", "consent status"
# or a bare `consent` key, still counts.
_PUSH_CONSENT = re.compile(
    r"skipped \(no consent\)|fold\.py consent (?:grant|revoke|status)\b|\bpush consent\b"
    r"|push approval \(`consent`\)|`no_consent`",
    re.IGNORECASE,
)

sys.path.insert(0, SCRIPTS)

import gp_sections  # after the path insert, as the golden test does


def scan(text):
    """The forbidden names found in text, in FORBIDDEN order."""
    text = _PUSH_CONSENT.sub(" ", text)
    return [name for name, pattern in FORBIDDEN.items() if pattern.search(text)]


def fallback_problems(label, text):
    """A caller SKILL.md that mentions jev must say `needs_fallback` or no answer means the
    default decides. Other texts, and texts with no jev mention, are not checked for it."""
    if not label.endswith("SKILL.md") or not JEV_MENTION.search(text):
        return []
    if FALLBACK_RULE.search(text):
        return []
    return [f"{label}: mentions jev without a needs_fallback or no-answer rule"]


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _rel(path):
    return os.path.relpath(path, REPO).replace(os.sep, "/")


def caller_texts():
    """(label, text) for each caller's SKILL.md (required), README and references (when
    present), each golden goal-prompt file, and the goal-prompt builders' generated text."""
    texts = []
    for skill in CALLERS:
        folder = os.path.join(SKILLS, skill)
        skill_md = os.path.join(folder, "SKILL.md")
        texts.append((_rel(skill_md), _read(skill_md)))
        optional = [os.path.join(folder, "README.md")]
        optional += sorted(glob.glob(os.path.join(folder, "references", "*.md")))
        for path in optional:
            if os.path.isfile(path):
                texts.append((_rel(path), _read(path)))
    for path in sorted(glob.glob(os.path.join(GOLDEN_DIR, "*.md"))):
        texts.append((_rel(path), _read(path)))
    texts.append(("gp_sections.decision_lines()", "\n".join(gp_sections.decision_lines())))
    texts.append(
        (
            "gp_sections.report_lines(usable)",
            "\n".join(gp_sections.report_lines({"usable": True})),
        )
    )
    texts.append(
        (
            "gp_sections.report_lines(unusable)",
            "\n".join(
                gp_sections.report_lines({"usable": False, "reason": "no usable backend"})
            ),
        )
    )
    return texts


class TestCallerText(unittest.TestCase):
    """SPEC R10 over the live caller texts: the callers name no jev backend, consent or probe."""

    def test_callers_are_read_and_none_is_the_exempt_skill(self):
        labels = [label for label, _text in caller_texts()]
        self.assertTrue(any(label.endswith("SKILL.md") for label in labels))
        self.assertFalse(
            any(label.startswith(f"skills/{EXEMPT_SKILL}/") for label in labels), labels
        )

    def test_every_caller_text_names_no_backend_consent_or_probe(self):
        for label, text in caller_texts():
            with self.subTest(label=label):
                self.assertEqual([], scan(text))

    def test_push_consent_clearance_is_narrow(self):
        # Non-vacuity: the flow's push-consent forms are cleared; jev backend consent is not.
        self.assertEqual([], scan("Pushes need push consent; `fold.py consent grant` records it."))
        self.assertEqual([], scan("outcome: u skipped (no consent)"))
        self.assertEqual([], scan("Run `fold.py consent revoke`; push approval (`consent`)."))
        self.assertEqual(["consent"], scan("The backend consent step asks first."))
        self.assertEqual(["consent"], scan("Consent is asked before the consent step."))
        for sample in ("When jev runs with no consent, it decides locally.",
                       "jev reads the `consent` key",
                       "jev: consent status is checked first",
                       "If the owner gives no consent to the remote backend",
                       "`consent grant` stores the remote backend's approval"):
            with self.subTest(sample=sample):
                self.assertEqual(["consent"], scan(sample))

    def test_every_caller_skill_states_the_default_decides(self):
        for label, text in caller_texts():
            with self.subTest(label=label):
                self.assertEqual([], fallback_problems(label, text))

    def test_findings_do_not_depend_on_file_order(self):
        texts = caller_texts()
        forward = {label: scan(text) for label, text in texts}
        backward = {label: scan(text) for label, text in reversed(texts)}
        self.assertEqual(forward, backward)


class TestCallerTextNonVacuity(unittest.TestCase):
    """The scanner and the fallback rule each flag a violation and pass a clean text."""

    def test_scanner_flags_each_forbidden_term(self):
        for name in FORBIDDEN:
            with self.subTest(term=name):
                self.assertIn(name, scan(f"Use the {name} path here."))

    def test_scanner_is_case_insensitive_for_backend_names(self):
        for sample in ("OpenCode Zen", "opencode zen", "LAYA", "Typesafe"):
            with self.subTest(sample=sample):
                self.assertTrue(scan(f"see {sample} for details"))

    def test_scanner_finds_the_terms_in_real_jev_text(self):
        # jev-fast-decision is exempt because it names these details; the scanner must work on it.
        jev = _read(os.path.join(SKILLS, EXEMPT_SKILL, "SKILL.md"))
        self.assertNotEqual([], scan(jev))

    def test_clean_caller_text_with_no_jev_mention_passes_both_checks(self):
        text = "Ask the user a question and wait for the reply, then continue.\n"
        self.assertEqual([], scan(text))
        self.assertEqual([], fallback_problems("skills/x/SKILL.md", text))

    def test_jev_mention_needs_the_default_decides_rule(self):
        text = "Ask the jev-fast-decision skill about the choice.\n"
        self.assertNotEqual([], fallback_problems("skills/x/SKILL.md", text))
        stated = text + "A needs_fallback or no answer means the default decides.\n"
        self.assertEqual([], fallback_problems("skills/x/SKILL.md", stated))

    def test_module_source_opens_no_file_for_writing(self):
        with open(__file__, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        writes = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name == "open":
                modes = list(node.args[1:2]) + [k.value for k in node.keywords if k.arg == "mode"]
                for mode in modes:
                    if isinstance(mode, ast.Constant) and set(str(mode.value)) & set("wax+"):
                        writes.append(node.lineno)
            elif name in _WRITE_METHODS:
                writes.append(node.lineno)
        self.assertEqual([], writes)


if __name__ == "__main__":
    unittest.main()
