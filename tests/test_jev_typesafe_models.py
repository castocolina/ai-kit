"""Behaviour of the TypeSafe model records in
skills/jev-fast-decision/scripts/jev_learn.py (plan 34-05, SPEC R4): a new versioned model id is
noted locally, the official doc flow is read once per pending id, and what the docs say is recorded
as documented upstream, never as verified here. Every fetch is an injected fake over
tests/fixtures/jev/typesafe-docs.json, and the state folder is a temp directory, so nothing touches
the network or the real environment."""

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_jev_fast_decision import JR, JevStub, _ClientCase, noul_item, payload
from tests.test_jev_learn import FakeFetch

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "skills" / "jev-fast-decision" / "scripts" / "jev_learn.py"
FIXTURE = REPO / "tests" / "fixtures" / "jev" / "typesafe-docs.json"


def _load():
    spec = importlib.util.spec_from_file_location("jev_learn_typesafe_under_test", MODULE)
    assert spec is not None and spec.loader is not None, MODULE
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


jev_learn = _load()
DOCS = json.loads(FIXTURE.read_text(encoding="utf-8"))
# (keyword for the fake, fixture key, URL) for the three doc pages the flow reads.
PAGES = (
    ("index", "llms", jev_learn.DOCS_INDEX_URL),
    ("changelog", "changelog", jev_learn.DOCS_CHANGELOG_URL),
    ("models", "models", jev_learn.DOCS_MODELS_URL),
)


# The models page with one question type the skill does not know (a primitive named Rank).
RANKED_MODELS = DOCS["models"].replace(
    "Choice, Score, Noul, Box |", "Choice, Score, Noul, Box, Rank |"
)


def _docs_fetch(**changes):
    """A FakeFetch over the fixture pages. A keyword (index, changelog, models) replaces that page:
    a str is its new text, an exception is raised for it."""
    pages = {}
    for key, doc_key, url in PAGES:
        value = changes.get(key, DOCS[doc_key])
        pages[url] = value.encode("utf-8") if isinstance(value, str) else value
    return FakeFetch(pages)


class TestModelRecords(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="jev-typesafe-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.state = os.path.join(self.root, "state")
        self.records = os.path.join(self.state, "jev", jev_learn.MODEL_RECORDS)

    def _stored(self):
        with open(self.records, encoding="utf-8") as handle:
            return json.load(handle)

    def _bytes_on_disk(self):
        with open(self.records, "rb") as handle:
            return handle.read()

    def _learn(self, fetch, **options):
        return jev_learn.learn_models(self.state, fetch, options)

    def test_new_model_id_is_noted_then_read_once(self):
        self.assertTrue(jev_learn.note_model(self.state, "jev-1.14.0"))
        self.assertEqual(set(self._stored()["jev-1.14.0"]), {"status", "first_seen"})
        fetch = _docs_fetch()
        out = self._learn(fetch)
        self.assertEqual(out["model_record"], "new")
        self.assertEqual(out["model_ids"], ["jev-1.14.0"])
        self.assertEqual(out["serves"], ["box", "image", "long_context"])
        self.assertEqual(out["new_primitives"], [])
        entry = self._stored()["jev-1.14.0"]
        self.assertEqual(entry["status"], "recorded")
        self.assertIn("Model ID `jev-1.14.0`", entry["notes"])
        self.assertEqual(entry["primitives_documented"], ["box", "choice", "noul", "score"])
        self.assertEqual(len(fetch.calls), 3)
        again = _docs_fetch()
        self.assertEqual(self._learn(again)["model_record"], "known")
        self.assertEqual(again.calls, [])

    def test_known_alias_and_missing_ids_record_nothing(self):
        for model_id in ("jev-latest", None, ""):
            self.assertFalse(jev_learn.note_model(self.state, model_id))
        self.assertFalse(os.path.exists(self.records))
        self.assertTrue(jev_learn.note_model(self.state, "jev-1.14.0"))
        before = self._bytes_on_disk()
        self.assertFalse(jev_learn.note_model(self.state, "jev-1.14.0"))
        self.assertFalse(jev_learn.note_model(self.state, "jev-latest"))
        self.assertEqual(self._bytes_on_disk(), before)

    def test_two_pending_ids_read_the_docs_once(self):
        jev_learn.note_model(self.state, "jev-1.14.0", now="2026-11-14T09:00:00+00:00")
        jev_learn.note_model(self.state, "jev-1.15.0", now="2026-11-15T09:00:00+00:00")
        fetch = _docs_fetch()
        out = self._learn(fetch)
        self.assertEqual(out["model_ids"], ["jev-1.14.0", "jev-1.15.0"])
        self.assertEqual(len(fetch.calls), 3)
        stored = self._stored()
        self.assertEqual(stored["jev-1.14.0"]["status"], "recorded")
        absent = stored["jev-1.15.0"]
        self.assertEqual(absent["status"], "recorded")
        self.assertEqual(absent["notes"], "")
        self.assertEqual(absent["serves"], [])
        self.assertEqual(absent["primitives_documented"], [])

    def test_failed_fetch_keeps_ids_pending(self):
        jev_learn.note_model(self.state, "jev-1.14.0")
        before = self._bytes_on_disk()
        out = self._learn(
            _docs_fetch(index=OSError("down"), changelog=OSError("down"), models=OSError("down"))
        )
        self.assertEqual(out["model_record"], "fetch_failed")
        self.assertIn("stay pending", out["notice"])
        self.assertEqual(self._stored()["jev-1.14.0"]["status"], "pending")
        self.assertEqual(self._bytes_on_disk(), before)

    def test_unknown_primitive_is_flagged(self):
        jev_learn.note_model(self.state, "jev-1.14.0")
        out = self._learn(_docs_fetch(models=RANKED_MODELS))
        self.assertEqual(out["new_primitives"], ["rank"])
        self.assertEqual(self._stored()["jev-1.14.0"]["new_primitives"], ["rank"])

    def test_index_links_off_the_docs_site_are_ignored(self):
        jev_learn.note_model(self.state, "jev-1.14.0")
        evil = "https://evil.example/changelog.md"
        index = DOCS["llms"].replace(jev_learn.DOCS_CHANGELOG_URL, evil)
        fetch = _docs_fetch(index=index)
        out = self._learn(fetch)
        self.assertEqual(out["model_record"], "new")
        self.assertEqual(
            fetch.calls,
            [jev_learn.DOCS_INDEX_URL, jev_learn.DOCS_CHANGELOG_URL, jev_learn.DOCS_MODELS_URL],
        )

    def test_force_refresh_deadline_skip_and_empty(self):
        empty = FakeFetch({})
        self.assertEqual(self._learn(empty)["model_record"], "none")
        self.assertEqual(empty.calls, [])
        jev_learn.note_model(self.state, "jev-1.14.0", now="2026-11-14T09:00:00+00:00")
        self.assertEqual(self._learn(_docs_fetch())["model_record"], "new")
        refresh = _docs_fetch()
        out = self._learn(refresh, force=True, now="2026-11-16T10:00:00+00:00")
        self.assertEqual(out["model_record"], "refreshed")
        self.assertEqual(out["model_ids"], ["jev-1.14.0"])
        self.assertEqual(len(refresh.calls), 3)
        self.assertEqual(self._stored()["jev-1.14.0"]["checked_at"], "2026-11-16T10:00:00+00:00")
        jev_learn.note_model(self.state, "jev-1.15.0", now="2026-11-15T09:00:00+00:00")
        deadline = FakeFetch({})
        skipped = self._learn(deadline, fetch_allowed=False)
        self.assertEqual(skipped["model_record"], "skipped_deadline")
        self.assertEqual(skipped["model_ids"], ["jev-1.15.0"])
        self.assertEqual(deadline.calls, [])

    def test_each_doc_page_failing_alone(self):
        jev_learn.note_model(self.state, "jev-1.14.0")
        before = self._bytes_on_disk()
        failing = (
            ("changelog", jev_learn.DOCS_CHANGELOG_URL),
            ("models", jev_learn.DOCS_MODELS_URL),
        )
        for page, url in failing:
            with self.subTest(page=page):
                out = self._learn(_docs_fetch(**{page: OSError("down")}))
                self.assertEqual(out["model_record"], "fetch_failed")
                self.assertIn(url, out["notice"])
                self.assertEqual(self._bytes_on_disk(), before)
        out = self._learn(_docs_fetch(index=OSError("down")))
        self.assertEqual(out["model_record"], "new")
        self.assertIn("llms.txt not read", out["notice"])
        self.assertEqual(self._stored()["jev-1.14.0"]["status"], "recorded")

    def test_unknown_primitive_or_option_triggers_one_doc_read(self):
        jev_learn.note_model(self.state, "jev-1.14.0")
        self.assertEqual(self._learn(_docs_fetch())["model_record"], "new")
        names = ["primitive:rank", "option:explanation", "option:bad name"]
        self.assertTrue(jev_learn.note_unknown(self.state, "jev-1.14.0", names))
        entry = self._stored()["jev-1.14.0"]
        self.assertEqual(entry["status"], "pending")
        self.assertEqual(entry["unknown_seen"], ["option:explanation", "primitive:rank"])
        fetch = _docs_fetch(models=RANKED_MODELS)
        out = self._learn(fetch)
        self.assertEqual(len(fetch.calls), 3)
        self.assertEqual(out["model_record"], "new")
        self.assertEqual(out["unknown_seen"], ["option:explanation", "primitive:rank"])
        self.assertEqual(out["unknown_documented"], ["primitive:rank"])
        stored = self._stored()["jev-1.14.0"]
        self.assertEqual(stored["unknown_seen"], ["option:explanation", "primitive:rank"])
        before = self._bytes_on_disk()
        self.assertFalse(jev_learn.note_unknown(self.state, "jev-1.14.0", names))
        self.assertEqual(self._bytes_on_disk(), before)
        self.assertTrue(jev_learn.note_unknown(self.state, None, ["primitive:grade"]))
        self.assertEqual(self._stored()["jev-1.14.0"]["status"], "pending")
        self.assertIn("primitive:grade", self._stored()["jev-1.14.0"]["unknown_seen"])
        fresh = os.path.join(self.root, "fresh")
        self.assertFalse(jev_learn.note_unknown(fresh, None, ["primitive:grade"]))
        self.assertFalse(os.path.exists(fresh))

    def test_secret_shaped_unknown_name_is_dropped(self):
        jev_learn.note_model(self.state, "jev-1.14.0")
        secret = "option:" + "AKIA" + "X" * 16
        before = self._bytes_on_disk()
        self.assertFalse(jev_learn.note_unknown(self.state, "jev-1.14.0", [secret]))
        self.assertEqual(self._bytes_on_disk(), before)
        kept = jev_learn.note_unknown(self.state, "jev-1.14.0", [secret, "primitive:rank"])
        self.assertTrue(kept)
        self.assertEqual(self._stored()["jev-1.14.0"]["unknown_seen"], ["primitive:rank"])
        self.assertNotIn("AKIA", self._bytes_on_disk().decode("utf-8"))


def _no_fetch(testcase, label):
    """Patch the public fetcher to fail the test if anything calls it; returns the mock."""
    patcher = mock.patch.object(JR, "_public_get", side_effect=AssertionError(label))
    fetch = patcher.start()
    testcase.addCleanup(patcher.stop)
    return fetch


class TestAnswerPathModels(_ClientCase):
    """The answer path notes a new TypeSafe model id, and the next probe reads the docs once for
    it (plan 34-06, SPEC R4, D-09). No answer, refusal or probe path fetches on the answer side."""

    def setUp(self):
        super().setUp()
        self.records = os.path.join(JR._state_dir(), "jev", "typesafe-models.json")

    def stored(self):
        with open(self.records, encoding="utf-8") as handle:
            return json.load(handle)

    def bytes_on_disk(self):
        with open(self.records, "rb") as handle:
            return handle.read()

    def write_records(self, data):
        os.makedirs(os.path.dirname(self.records), exist_ok=True)
        with open(self.records, "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def test_answer_notes_a_new_model_id_without_fetching(self):
        self.enable_remote("typesafe")
        fetch = _no_fetch(self, "the answer path fetched")
        with JevStub(model="jev-1.15.0", places=2) as stub:
            self.point_remote("typesafe", stub)
            out = self.run_screen(payload(noul_item("a")))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["model"], "jev-1.15.0")
        self.assertEqual(self.stored()["jev-1.15.0"]["status"], "pending")
        fetch.assert_not_called()

    def test_probe_reads_the_docs_once_for_a_pending_id(self):
        self.enable_remote("typesafe")
        _no_fetch(self, "the answer path fetched")
        with JevStub(model="jev-1.15.0", places=2) as stub:
            self.point_remote("typesafe", stub)
            self.run_screen(payload(noul_item("a")))
        docs = _docs_fetch()
        with mock.patch.object(JR, "_public_get", docs):
            code, report = self.run_probe()
        self.assertEqual(code, 0)
        typesafe = self.backend_entry(report, "typesafe")
        self.assertEqual(typesafe["model_record"], "new")
        self.assertEqual(typesafe["model_ids"], ["jev-1.15.0"])
        self.assertEqual(len(docs.calls), 3)
        again = _docs_fetch()
        with mock.patch.object(JR, "_public_get", again):
            _code, second = self.run_probe()
        self.assertEqual(self.backend_entry(second, "typesafe")["model_record"], "known")
        self.assertEqual(again.calls, [])

    def test_known_id_and_laya_answers_record_nothing(self):
        self.enable_remote("typesafe")
        JR._LEARN.note_model(JR._state_dir(), "jev-1.14.0")
        before = self.bytes_on_disk()
        _no_fetch(self, "the answer path fetched")
        with JevStub(model="jev-1.14.0", places=2) as stub:
            self.point_remote("typesafe", stub)
            self.run_screen(payload(noul_item("a")))
        self.assertEqual(self.bytes_on_disk(), before)
        for name in ("JEV_BACKEND", "JEV_ALLOW_REMOTE", "TYPESAFE_API_KEY"):
            os.environ.pop(name, None)
        self.enable(None)  # auto: Laya answers first, and no TypeSafe row is configured
        with JevStub(model="laya-rl-agent") as laya:
            self.point_at(laya)
            out = self.run_screen(payload(noul_item("a")))
        self.assertEqual(out["backend"], "laya")
        self.assertEqual(self.bytes_on_disk(), before)

    def test_answer_with_an_unknown_field_is_noted_without_fetching(self):
        self.enable_remote("typesafe")
        fetch = _no_fetch(self, "the answer path fetched")
        with JevStub(model="jev-1.14.0", places=2, extra={"explanation": "x"}) as stub:
            self.point_remote("typesafe", stub)
            out = self.run_screen(payload(noul_item("a")))
        self.assertEqual(out["status"], "ok")
        fetch.assert_not_called()
        entry = self.stored()["jev-1.14.0"]
        self.assertEqual(entry["status"], "pending")
        self.assertEqual(entry["unknown_seen"], ["option:explanation"])
        docs = _docs_fetch()
        with mock.patch.object(JR, "_public_get", docs):
            _code, report = self.run_probe()
        typesafe = self.backend_entry(report, "typesafe")
        self.assertEqual(typesafe["model_record"], "new")
        self.assertEqual(typesafe["unknown_seen"], ["option:explanation"])

    def test_item_with_an_unknown_type_is_noted_at_refusal(self):
        self.enable(None)
        self.write_records({"jev-1.14.0": {"status": "recorded",
                                           "first_seen": "2026-11-15T00:00:00+00:00"}})
        item = {"id": "r1", "type": "rank", "instructions": "Rank the fixes.",
                "criteria": {"a": "one", "b": "two"}}
        fetch = _no_fetch(self, "the refusal fetched")
        with JevStub(model="laya-rl-agent") as laya:
            self.point_at(laya)
            out = self.run_screen(payload(item))
        self.assertEqual(out["status"], "unavailable")
        self.assertTrue(out["reason"].startswith("invalid_input"), out["reason"])
        entry = self.stored()["jev-1.14.0"]
        self.assertEqual(entry["status"], "pending")
        self.assertEqual(entry["unknown_seen"], ["primitive:rank"])
        self.assertEqual(laya.requests, [], "the refusal comes before any request")
        fetch.assert_not_called()

    def test_item_refused_by_the_feature_pass_is_noted(self):
        self.enable(None)
        self.write_records({"jev-1.14.0": {"status": "recorded",
                                           "first_seen": "2026-11-15T00:00:00+00:00"}})
        item = {"id": "r2", "type": "rank", "instructions": "Rank the screenshots.",
                "criteria": {"a": "one", "b": "two"}, "images": ["one.png"]}
        fetch = _no_fetch(self, "the refusal fetched")
        with JevStub(model="laya-rl-agent") as laya:
            self.point_at(laya)
            out = self.run_screen(payload(item))
        self.assertEqual(out["status"], "unavailable")
        self.assertEqual(out["reason"], "unsupported_feature")
        entry = self.stored()["jev-1.14.0"]
        self.assertEqual(entry["status"], "pending")
        self.assertEqual(entry["unknown_seen"], ["primitive:rank"])
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
