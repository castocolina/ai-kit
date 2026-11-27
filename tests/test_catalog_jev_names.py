"""Tests for the optional catalog jev seam."""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import jev_names  # noqa: I001
from tests.test_ai_kit_commit_fold import OLD_CLIENT, write_fake_jev


class TestJevNames(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.skills = self.root / "skills"
        self.home = self.root / "home"
        self.env = {"HOME": str(self.home), "PATH": os.environ.get("PATH", "")}
        self.log = self.root / "calls.jsonl"

    def _fake(self, table):
        write_fake_jev(self.skills, table, self.log)

    def _name_judge(self, table):
        self._fake(table)
        judge = jev_names.name_judge(self.env, str(self.skills))
        self.assertIsNotNone(judge)
        assert judge is not None
        return judge

    def test_confident_name_answer(self):
        result = self._name_judge({"placeholder-model-7": "e1"})([
            ("placeholder-model-7", ["placeholder-model-71", "placeholder-model-72"])
        ])
        self.assertEqual(result, [("placeholder-model-72", 0.9, "")])
        payload = json.loads(self.log.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["items"]), 1)
        context = payload["items"][0]["context"]
        self.assertIn("placeholder-model-71", context)
        self.assertIn("placeholder-model-72", context)
        self.assertNotIn(str(self.home), context)

    def test_item_holds_names_only(self):
        item = jev_names.name_item(0, "placeholder-model-7", ["placeholder-model-71"])
        self.assertIn("placeholder-model-7", item["context"])
        self.assertEqual(set(item["criteria"]), {"e0", "none"})
        self.assertNotIn(str(self.home), json.dumps(item))

    def test_find_jev_default_root(self):
        entry = jev_names.find_jev({"HOME": str(self.home)})
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertTrue(entry.endswith("jev-fast-decision/scripts/jev_review.py"))
        self.assertTrue(os.path.isfile(entry))

    def test_low_answer(self):
        self._fake({})
        judge = jev_names.name_judge(self.env, str(self.skills))
        assert judge is not None
        self.assertEqual(judge([("placeholder-model-7", ["placeholder-model-71"])]),
                         [(None, None, "no answer")])

    def test_absent_jev(self):
        self.assertIsNone(jev_names.name_judge(self.env, str(self.skills)))
        self.assertIsNone(jev_names.class_judge(self.env, str(self.skills)))

    def test_old_client(self):
        entry = self.skills / "jev-fast-decision" / "scripts" / "jev_review.py"
        entry.parent.mkdir(parents=True)
        entry.write_text(OLD_CLIENT, encoding="utf-8")
        judge = jev_names.name_judge(self.env, str(self.skills))
        assert judge is not None
        self.assertEqual(judge([("placeholder-model-7", ["placeholder-model-71"])]),
                         [(None, None, "old")])

    def test_timeout(self):
        self._fake({})

        def timeout(*_args, **_kwargs):
            raise subprocess.TimeoutExpired(cmd="x", timeout=1)

        judge = jev_names.name_judge(self.env, str(self.skills), timeout)
        assert judge is not None
        self.assertEqual(judge([("placeholder-model-7", ["placeholder-model-71"])]),
                         [(None, None, "timeout")])

    def test_class_judge(self):
        self._fake({"placeholder-model-9": "coding"})
        judge = jev_names.class_judge(self.env, str(self.skills))
        assert judge is not None
        self.assertEqual(judge([("placeholder-model-9", "no measured fields")]),
                         [("coding", 0.9, "")])

    def test_one_call_per_batch(self):
        judge = self._name_judge({"placeholder-model-7": "e0"})
        pairs = [("placeholder-model-7", ["placeholder-model-71"]),
                 ("placeholder-model-7", ["placeholder-model-72"])]
        judge(pairs)
        rows = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]["items"]), 2)

    def test_fallback_forced_malformed_rejected(self):
        item = jev_names.name_item(0, "placeholder-model-7", ["placeholder-model-71"])
        for flags in ({"needs_fallback": True}, {"forced": True}, {"fallback": True},
                      {"omit_top": True}, {"top": 1.4}):
            column = {"choice": "e0", "top": 0.9, **flags}
            if flags.get("omit_top"):
                column.pop("top")
            column.pop("omit_top", None)
            output = json.dumps({"items": {"n0": {"decided_by": "fake", "fake": column}}})
            run = lambda *_args, _output=output, **_kwargs: subprocess.CompletedProcess(
                [], 0, stdout=_output, stderr=""
            )
            answer = jev_names.ask_items("entry", [item], self.env, run)["n0"]
            self.assertIsNone(answer[0])
            self.assertIn(answer[2], ("low", "no answer"))
        for output in ('{"items": []}', '[1]', '{"items": {"n0": "x"}}'):
            run = lambda *_args, _output=output, **_kwargs: subprocess.CompletedProcess(
                [], 0, stdout=_output, stderr=""
            )
            self.assertEqual(jev_names.ask_items("entry", [item], self.env, run)["n0"],
                             (None, None, "no answer"))

    def test_undecodable_reply_is_no_answer(self):
        item = jev_names.name_item(0, "placeholder-model-7", ["placeholder-model-71"])

        def run(*_args, **_kwargs):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        self.assertEqual(jev_names.ask_items("entry", [item], self.env, run, strict=True),
                         {"n0": (None, None, "no answer")})

    def test_batches_respect_size_guard(self):
        payloads = []

        def run(_args, input, **_kwargs):
            payloads.append(input)
            items = json.loads(input)["items"]
            response = {item["id"]: {"decided_by": "own_reasoning"} for item in items}
            return subprocess.CompletedProcess([], 0, stdout=json.dumps({"items": response}),
                                                stderr="")

        pairs = [(f"placeholder-model-{i}", ["x" * 80]) for i in range(40)]
        items = [jev_names.name_item(i, name, names) for i, (name, names) in enumerate(pairs)]
        jev_names.ask_items("entry", items, self.env, run)
        self.assertGreater(len(payloads), 1)
        self.assertTrue(all(len(payload) <= jev_names.BATCH_CHARS for payload in payloads))

    def test_names_cleaned_and_mapped_back(self):
        original = "a\n\x1b" + "x" * 497
        self._fake({"placeholder-model-7": "e0"})
        judge = jev_names.name_judge(self.env, str(self.skills))
        assert judge is not None
        result = judge([("placeholder-model-7", [original])])
        self.assertEqual(result[0][0], original)
        payload = json.loads(self.log.read_text(encoding="utf-8"))["items"][0]
        self.assertEqual(payload["criteria"]["e0"], "a" + "x" * 79)
        self.assertNotIn("\n", json.dumps(payload))
        self.assertNotIn("\x1b", json.dumps(payload))

    def test_none_choice_unmatched(self):
        item = jev_names.name_item(0, "x", ["a", "b"])
        self.assertEqual(set(item["criteria"]), {"e0", "e1", "none"})
        self._fake({"placeholder-model-7": "none"})
        judge = jev_names.name_judge(self.env, str(self.skills))
        assert judge is not None
        self.assertEqual(judge([("placeholder-model-7", ["a", "b"])]),
                         [(None, 0.9, "none")])


if __name__ == "__main__":
    unittest.main()
