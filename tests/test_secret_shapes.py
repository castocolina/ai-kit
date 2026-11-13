"""Tests for the shared key-shape scanner (skills/ai-kit-spec-review/ai_kit_spec/secret_shapes.py).

Every sample is synthetic: a provider prefix plus repeated filler, built at run time, so no whole
key literal sits in this file. detect names shapes and never returns the match; redact puts the
caller's marker in place of each match and leaves text with no match unchanged.
"""

import importlib.util
import re
import time
import unittest
from pathlib import Path

CANONICAL = (
    Path(__file__).resolve().parent.parent
    / "skills" / "ai-kit-spec-review" / "ai_kit_spec" / "secret_shapes.py"
)


def _load():
    """The canonical file, loaded by path under its own module name."""
    spec = importlib.util.spec_from_file_location("secret_shapes_under_test", CANONICAL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shapes = _load()
MARKER = "<m>"
# (shape name, prefix, filler, minimum filler count): prefix + filler * count is found, one less
# is not.
MINIMUMS = (
    ("github_token", "ghp_", "a", 20),
    ("github_pat", "github_pat_", "a", 20),
    ("google_api_key", "AIza", "a", 20),
    ("slack_token", "xoxb-", "a", 12),
    ("aws_access_key_id", "AKIA", "A", 16),
    ("gitlab_token", "glpat-", "a", 16),
    ("xai_api_key", "xai-", "a", 16),
    ("stripe_key", "sk_live_", "a", 16),
    ("huggingface_token", "hf_", "a", 30),
    ("npm_token", "npm_", "a", 36),
    ("groq_key", "gsk_", "a", 20),
    ("sk_rk_key", "sk-", "a", 8),
)
# Every documented prefix of the rows that have several: (shape name, prefixes, filler, count).
PREFIXES = (
    ("github_token", ("ghp_", "gho_", "ghu_", "ghs_", "ghr_"), "a", 20),
    ("slack_token", ("xoxa-", "xoxb-", "xoxp-", "xoxo-", "xoxs-", "xoxr-", "xoxe-", "xapp-",
                     "xwfp-"), "a", 12),
    ("aws_access_key_id", ("AKIA", "ASIA", "ABIA", "ACCA"), "A", 16),
    ("gitlab_token", ("glpat-", "gloas-", "gldt-", "glrt-", "glrtr-", "glcbt-", "glptt-",
                      "glft-", "glimt-", "glagent-", "glwt-", "glsoat-", "glffct-"), "a", 16),
    ("stripe_key", ("sk_live_", "sk_test_", "rk_live_", "rk_test_"), "a", 16),
    ("sk_rk_key", ("sk-", "rk-"), "a", 8),
)
PEM_LABEL = "RSA PRIVATE KEY"
PEM_HEADER = "-----BEGIN " + PEM_LABEL + "-----"
PEM_FOOTER = "-----END " + PEM_LABEL + "-----"
BARE_PREFIXES = ("ghp_", "github_pat_", "AIza", "xoxb-", "AKIA", "glpat-", "xai-", "eyJ",
                 "sk_live_", "hf_", "npm_", "gsk_", "sk-", "-----BEGIN")
WRONG_CASE = ("SK-" + "a" * 24, "GHP_" + "a" * 36, "akia" + "A" * 16, "Xoxb-" + "a" * 12,
              "aiza" + "a" * 20)
NEAR_MISSES = (
    "0123456789abcdef" * 2 + "01234567",
    "12345678-1234-abcd-1234-1234567890ab",
    "risk-assessment",
    "Basic authentication",
    "sk-learn",
    "phase 32.3 of 47.1",
    "/gsd-autonomous --from 32 --to 34",
    "task-" + "a" * 24,
    "disk-usage-report-daily",
    "TASK-BODY",
    "xapp-config",
    "xoxb-token",
    "hf_transfer enabled",
    "npm_config_cache_dir",
    "eyJ alone",
)
# Documented matches, not defects: the sk_rk_key body takes `-` so the runner's hyphenated
# sentinel stays redacted, and an all-capitals word after ASIA cannot be told from a key id.
KNOWN_MATCHES = (
    ("sk-learn-pipeline-config", "sk_rk_key"),
    ("ASIA" + "B" * 16, "aws_access_key_id"),
)
SEPARATORS = (",", " ", '"')


def _jwt(header=10, payload=10, signature=10):
    return "eyJ" + "a" * header + ".eyJ" + "a" * payload + "." + "a" * signature


SAMPLES = {name: prefix + filler * count for name, prefix, filler, count in MINIMUMS}
SAMPLES["jwt"] = _jwt()
SAMPLES["pem_private_key"] = PEM_HEADER
NAMES = [name for name, _source in shapes.SHAPES]


class TestDetectAndRedact(unittest.TestCase):
    def test_each_sample_is_named_and_never_returned(self):
        for name in NAMES:
            with self.subTest(shape=name):
                found = shapes.detect("k " + SAMPLES[name] + " v")
                self.assertEqual([name], found)
                self.assertNotIn(SAMPLES[name], " ".join(found))

    def test_redact_puts_the_marker_in_place_of_each_sample(self):
        for name in NAMES:
            with self.subTest(shape=name):
                self.assertEqual("k <m> v", shapes.redact("k " + SAMPLES[name] + " v", MARKER))

    def test_clean_text_is_returned_unchanged(self):
        for text in (*NEAR_MISSES, "plain prose with nothing secret in it."):
            with self.subTest(text=text):
                self.assertEqual([], shapes.detect(text))
                self.assertEqual(text, shapes.redact(text, MARKER))

    def test_empty_text(self):
        self.assertEqual([], shapes.detect(""))
        self.assertEqual("", shapes.redact("", MARKER))

    def test_none_is_a_caller_bug(self):
        with self.assertRaises(TypeError):
            shapes.detect(None)
        with self.assertRaises(TypeError):
            shapes.redact(None, MARKER)

    def test_names_come_once_in_table_order(self):
        text = " ".join(SAMPLES[name] for name in reversed(NAMES))
        text += " " + SAMPLES["aws_access_key_id"]
        self.assertEqual(NAMES, shapes.detect(text))
        self.assertEqual(" ".join([MARKER] * (len(NAMES) + 1)), shapes.redact(text, MARKER))

    def test_redact_is_idempotent_and_never_nests(self):
        for name in NAMES:
            with self.subTest(shape=name):
                once = shapes.redact("k " + SAMPLES[name] + " v", MARKER)
                self.assertEqual(once, shapes.redact(once, MARKER))
                self.assertEqual(1, once.count(MARKER))

    def test_a_token_holding_another_shape_is_one_marker(self):
        # A row that matched first inside a longer token would leave the rest of it visible.
        nested = (
            ("gitlab_token", "glpat-" + "a" * 8 + "-" + "AKIA" + "X" * 16 + "z" * 64),
            ("slack_token", "xoxb-" + "1" * 12 + "-ghp_" + "b" * 36 + "-" + "c" * 30),
        )
        for name, sample in nested:
            with self.subTest(shape=name):
                self.assertEqual(MARKER, shapes.redact(sample, MARKER))

    def test_a_key_glued_before_a_pem_block_leaves_no_body(self):
        # The generic row takes the block's opening dashes; the union of both spans still
        # covers the whole block.
        body = "MIIB" + "a" * 60
        sample = "sk-" + "a" * 8 + PEM_HEADER + "\n" + body + "\n" + PEM_FOOTER
        redacted = shapes.redact(sample, MARKER)
        self.assertEqual(MARKER, redacted)
        self.assertNotIn(body, redacted)

    def test_a_4096_bit_sized_key_body_is_fully_redacted(self):
        # The END tail is capped at 16384 characters; a 4096-bit key body is about 3.2 KB.
        body = "\n".join(["MIIJ" + "A" * 60] + ["B" * 64] * 50)
        block = PEM_HEADER + "\n" + body + "\n" + PEM_FOOTER
        self.assertEqual("x " + MARKER + " y", shapes.redact("x " + block + " y", MARKER))

    def test_many_unclosed_opening_lines_finish_quickly(self):
        # Without the cap each opening line would scan the rest of the text for an END line.
        text = (PEM_HEADER + "x" * 20 + "\n") * 8000
        start = time.perf_counter()
        shapes.redact(text, MARKER)
        self.assertLess(time.perf_counter() - start, 3.0)

    def test_non_ascii_neighbours_are_kept(self):
        text = "café " + SAMPLES["xai_api_key"] + " naïve"
        self.assertEqual("café <m> naïve", shapes.redact(text, MARKER))
        # The lookbehind is ASCII-only, so a non-ASCII letter glued before a key does not hide
        # it, and Python and JavaScript agree.
        self.assertEqual(["sk_rk_key"], shapes.detect("é" + SAMPLES["sk_rk_key"]))


class TestShapeTable(unittest.TestCase):
    def test_minimum_is_found_and_one_short_is_not(self):
        for name, prefix, filler, count in MINIMUMS:
            with self.subTest(shape=name):
                self.assertEqual([name], shapes.detect(prefix + filler * count))
                self.assertEqual([], shapes.detect(prefix + filler * (count - 1)))

    def test_jwt_segment_floors(self):
        self.assertEqual(["jwt"], shapes.detect(_jwt()))
        for short in ((9, 10, 10), (10, 9, 10), (10, 10, 9), (10, 10, 0)):
            with self.subTest(segments=short):
                self.assertEqual([], shapes.detect(_jwt(*short)))

    def test_pem_lines(self):
        self.assertEqual(["pem_private_key"], shapes.detect(PEM_HEADER))
        block = PEM_HEADER + "\n" + "MIIB" + "a" * 60 + "\n" + PEM_FOOTER
        self.assertEqual(MARKER, shapes.redact(block, MARKER))
        self.assertEqual(["pem_private_key"], shapes.detect("-----BEGIN " + "CERTIFICATE-----"))
        self.assertEqual([], shapes.detect("-----BEGIN " + PEM_LABEL + "----"))
        self.assertEqual([], shapes.detect("-----BEGIN rsa private key-----"))

    def test_every_documented_prefix(self):
        for name, prefixes, filler, count in PREFIXES:
            for prefix in prefixes:
                with self.subTest(shape=name, prefix=prefix):
                    self.assertEqual([name], shapes.detect(prefix + filler * count))
                    self.assertEqual([], shapes.detect(prefix + filler * (count - 1)))

    def test_bare_prefixes_are_not_keys(self):
        for text in BARE_PREFIXES:
            with self.subTest(text=text):
                self.assertEqual([], shapes.detect(text))

    def test_wrong_case_is_not_a_key(self):
        for text in WRONG_CASE:
            with self.subTest(text=text):
                self.assertEqual([], shapes.detect(text))

    def test_near_misses_are_clean(self):
        for text in NEAR_MISSES:
            with self.subTest(text=text):
                self.assertEqual([], shapes.detect(text))
                self.assertEqual(text, shapes.redact(text, MARKER))

    def test_documented_known_matches(self):
        for text, name in KNOWN_MATCHES:
            with self.subTest(text=text):
                self.assertEqual([name], shapes.detect(text))

    def test_non_ascii_body_is_not_a_key(self):
        self.assertEqual([], shapes.detect("ghp_" + "é" * 20))
        self.assertEqual([], shapes.detect("AKIA" + "Ä" * 16))

    def test_sources_read_the_same_in_python_and_javascript(self):
        self.assertEqual(len(NAMES), len(set(NAMES)))
        self.assertEqual("sk_rk_key", NAMES[-1])
        for name, source in shapes.SHAPES:
            with self.subTest(shape=name):
                self.assertRegex(name, r"^[a-z][a-z0-9_]*$")
                self.assertEqual(0, re.compile(source).groups)
                self.assertNotIn("(?i", source)
                self.assertNotIn("\\b", source)


class TestEscapesAndTails(unittest.TestCase):
    def test_key_after_a_json_or_percent_escape_is_found_and_redacted(self):
        # An escape letter or hex digit glued before the key must not hide it.
        for lead in ("x\\n", "x\\r", "x\\t", "x%3D", "x%0a"):
            for name in NAMES:
                if name == "pem_private_key":
                    continue
                with self.subTest(lead=lead, shape=name):
                    text = lead + SAMPLES[name]
                    self.assertIn(name, shapes.detect(text))
                    self.assertEqual(lead + MARKER, shapes.redact(text, MARKER))

    def test_jwt_lookalike_repeat_finishes_quickly(self):
        text = "eyJ-" * 16384
        for call in (lambda: shapes.detect(text), lambda: shapes.redact(text, MARKER)):
            start = time.perf_counter()
            call()
            self.assertLess(time.perf_counter() - start, 1.0)

    def test_unclosed_pem_block_loses_its_body(self):
        lines = ["MIIB" + "a" * 60] * 20
        block = PEM_HEADER + "\n" + "\n".join(lines)
        self.assertEqual("k " + MARKER + " v", shapes.redact("k " + block + " v", MARKER))
        self.assertEqual(MARKER, shapes.redact(block, MARKER))


class TestAdjacency(unittest.TestCase):
    def test_keys_joined_by_one_character_are_each_found(self):
        github, generic = SAMPLES["github_token"], SAMPLES["sk_rk_key"]
        aws = SAMPLES["aws_access_key_id"]
        for sep in SEPARATORS:
            with self.subTest(sep=sep):
                text = github + sep + generic
                self.assertEqual(["github_token", "sk_rk_key"], shapes.detect(text))
                self.assertEqual(MARKER + sep + MARKER, shapes.redact(text, MARKER))
                self.assertEqual(MARKER + sep + MARKER, shapes.redact(aws + sep + github, MARKER))

    def test_sk_key_glued_before_a_github_token_is_one_match(self):
        # The reverse order is a recorded assumption, not tested: a GitHub token followed
        # directly by an sk- key ends at the hyphen and leaves the hyphen and the second body.
        glued = "sk-" + "a" * 8 + SAMPLES["github_token"]
        self.assertEqual(["sk_rk_key"], shapes.detect(glued))
        self.assertEqual(MARKER, shapes.redact(glued, MARKER))
