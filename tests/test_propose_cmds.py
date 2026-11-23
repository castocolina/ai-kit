"""Phase 36: propose-lanes (the proposal per purpose; no config, catalog or lane write)."""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, lane_effort, model_catalog

T = "2026-11-20T00:00:00Z"


def _key(n):
    return model_catalog.canonical_key("fake", f"placeholder-model-{n}")


def _fact(value):
    return {"value": value, "label": "measured", "source": "fixture", "fetched_at": T}


def _band(value):
    return {"value": value, "label": "judged", "source": "models.dev", "fetched_at": T,
            "confidence": "rule"}


def _entry(model_id, klass="flagship", tier="frontier", band="high", runtime="pi", **row_fields):
    return {"provider": "fake", "runtimes": {runtime: {"model_id": model_id, **row_fields}},
            "source": {}, "confidence": "low", "last_verified": "2026-11-20",
            "facts": {"tier": _fact(tier), "class": _fact(klass), "cost_band": _band(band)}}


def _catalog():
    entries = {_key(n): _entry(_key(n), band="high" if n == 2 else "free_or_local")
               for n in range(1, 8)}
    entries[_key(4)] = _entry(_key(4), band="free_or_local", runtime="opencode")
    entries[_key(6)] = _entry("placeholder-model-6", band="free_or_local", runtime="codex",
                              efforts=["high", "max"])
    eight = model_catalog.canonical_key("fake", "placeholder-model-8-free")
    entries[eight] = _entry("placeholder-model-8-free", runtime="claude", efforts=["high"])
    entries[_key(9)] = _entry(_key(9), klass="coding", tier="strong", band="low")
    entries[_key(90)] = _entry(_key(90), klass="unknown", tier="unknown")
    entries[_key(91)] = _entry(_key(91), usability={"state": "rejected", "at": T,
                                                     "via": "check-reviewer", "error": "boom"})
    alias = "router-env/placeholder-alias-1"
    entries[alias] = {"provider": "router-env", "runtimes": {"opencode": {"model_id": alias}},
                      "facts": {"class": {"value": "router", "label": "assumed",
                                          "source": "router-env alias naming", "fetched_at": T}},
                      "name_declared_purpose": "review"}
    return entries


class _Scratch(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-p36-propose-")
        self.addCleanup(shutil.rmtree, self.root)
        self.catalog_path = os.path.join(self.root, "catalog.json")
        self.runtimes_path = os.path.join(self.root, "runtimes.json")
        self.env = {"HOME": self.root, "XDG_CONFIG_HOME": os.path.join(self.root, "config"),
                    "AI_KIT_REFUSE_REAL_HOME": "1"}
        self._write_catalog(_catalog())
        self._write_runtimes({"clis": {rid: {"installed": True, "listing": "none"}
                                         for rid in ("pi", "opencode", "codex", "claude")}})

    def _write_catalog(self, entries):
        with open(self.catalog_path, "w", encoding="utf-8") as stream:
            json.dump({"_meta": {"schema_version": model_catalog.CATALOG_SCHEMA_VERSION},
                       **entries}, stream)

    def _write_runtimes(self, data):
        with open(self.runtimes_path, "w", encoding="utf-8") as stream:
            json.dump(data, stream)

    def _call(self, argv, **overrides):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv, env_fn=lambda: dict(self.env), **overrides)
        return code, out.getvalue(), err.getvalue()

    def _propose(self, purpose, *extra, **overrides):
        code, out, err = self._call(["propose-lanes", "--purpose", purpose, "--catalog-path",
                                     self.catalog_path, "--runtimes-json", self.runtimes_path,
                                     *extra], **overrides)
        return code, json.loads(out) if out else {}, err


class TestProposeLanes(_Scratch):
    def test_review_groups_and_shape(self):
        code, data, err = self._propose("review")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(list(data), ["purpose", "default_view", "ranking", "jev", "stale_checked",
                                      "pool", "zero_price", "aliases", "wider", "alternative",
                                      "empty", "message"])
        expected = [_key(n) for n in range(1, 8)] + [
            model_catalog.canonical_key("fake", "placeholder-model-8-free"), _key(90)]
        self.assertEqual([x["key"] for x in data["pool"]], expected)
        self.assertEqual([x["rank"] for x in data["pool"]], list(range(1, 10)))
        self.assertEqual(data["default_view"], 5)
        self.assertEqual(data["jev"], {"requested": False, "found": False, "asked": 0,
                                       "answered": 0, "window": 12, "stable_top": 0.8})
        self.assertEqual(data["pool"][-1]["ranker_reason"], "scorer: tier or class unknown")
        self.assertEqual([x["key"] for x in data["wider"]], [_key(9)])
        self.assertEqual(data["aliases"][0]["label"], "assumed: router-env alias naming")
        self.assertFalse(data["empty"])

    def test_execute_pool(self):
        _, data, _ = self._propose("execute")
        self.assertEqual([x["key"] for x in data["pool"]], [_key(9), _key(90)])
        self.assertEqual(len(data["wider"]), 8)
        self.assertEqual(data["aliases"], [])

    def test_zero_group_cap_and_rows(self):
        _, data, _ = self._propose("review")
        self.assertEqual([x["key"] for x in data["zero_price"]], [_key(n) for n in (1, 3, 4, 5, 6)])
        self.assertEqual(data["pool"][0]["pool_key"], "fake:free")
        self.assertEqual(data["pool"][0]["price"]["state"], "zero")
        self.assertTrue(data["pool"][0]["data_use_needed"])
        self.assertEqual(data["pool"][7]["price"]["state"], "nonzero")

    def test_jev_confident_reorders_pool_and_group(self):
        def judge(pairs):
            return [("excellent fit" if i == 6 else "fair fit", 0.9, "")
                    for i, _ in enumerate(pairs)]
        _, data, _ = self._propose("review", "--jev", score_judge_fn=lambda env: judge)
        self.assertEqual(data["pool"][0]["key"], _key(7))
        self.assertEqual(data["jev"]["asked"], 7)
        self.assertEqual(data["jev"]["answered"], 7)
        self.assertEqual(data["zero_price"][0]["key"], _key(7))

    def test_jev_low_keeps_the_scorer_order(self):
        judge = lambda pairs: [("excellent fit", 0.7, "") for _ in pairs]
        _, data, _ = self._propose("review", "--jev", score_judge_fn=lambda env: judge)
        self.assertEqual(data["ranking"], "scorer")
        self.assertEqual(data["pool"][0]["ranker_reason"], "scorer: jev gave a low answer")
        self.assertEqual(data["pool"][7]["ranker_reason"], "scorer: outside the jev window")

    def test_jev_absent_or_not_requested(self):
        seam = mock.Mock(return_value=None)
        _, data, _ = self._propose("review", score_judge_fn=seam)
        seam.assert_not_called()
        _, data, _ = self._propose("review", "--jev", score_judge_fn=seam)
        self.assertFalse(data["jev"]["found"])
        self.assertEqual(data["ranking"], "scorer")

    def test_legacy_cursor_snapshot_matches_canonical(self):
        self._write_catalog({_key(1): _entry("placeholder-model-1", runtime="cursor")})
        row = {"installed": True, "listing": "ok", "models": ["placeholder-model-1"]}
        self._write_runtimes({"clis": {"cursor": row}})
        code, canonical, err = self._propose("review")
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(canonical["pool"])
        self._write_runtimes({"clis": {"cursor-agent": row}})
        code, legacy, err = self._propose("review")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(legacy, canonical)

    def test_runtime_filter(self):
        _, data, _ = self._propose("review", "--runtime", "opencode")
        self.assertEqual([x["key"] for x in data["pool"]], [_key(4)])
        self.assertEqual(len(data["aliases"]), 1)

    def test_alternative_with_avoid_pool_and_skip(self):
        _, data, _ = self._propose("review", "--avoid-pool", "fake:free")
        self.assertEqual(data["alternative"]["key"], _key(2))
        _, data, _ = self._propose("review", "--avoid-pool", "fake:free", "--skip", "pi:" + _key(2))
        self.assertEqual(data["alternative"]["key"],
                         model_catalog.canonical_key("fake", "placeholder-model-8-free"))

    def test_bad_filters_exit_2(self):
        for flag, value in (("--skip", "nocolon"), ("--avoid-pool", "fake")):
            code, _, err = self._propose("review", flag, value)
            self.assertEqual(code, 2)
            self.assertIn("bad " + flag + " value:", err)

    def test_effort_levels_per_row(self):
        _, data, _ = self._propose("review")
        self.assertEqual(data["pool"][5]["efforts"], ["high"])
        self.assertEqual(data["pool"][5]["efforts_refused"][0][0], "max")
        self.assertEqual(data["pool"][7]["efforts"], [])

    def test_malformed_numbers_still_propose(self):
        entries = _catalog()
        entries[_key(2)]["pricing"] = {"input_per_1m": "cheap", "output_per_1m": "x"}
        entries[_key(2)]["runtimes"]["pi"]["ctx_window"] = "big"
        self._write_catalog(entries)
        code, data, _ = self._propose("review")
        self.assertEqual(code, 0)
        self.assertIsInstance(data["pool"][1]["score"], (int, float))

    def test_malformed_listing_still_proposes(self):
        self._write_runtimes({"clis": {"opencode": {"installed": True, "listing": "ok",
                                                      "models": None}}})
        code, data, _ = self._propose("review")
        self.assertEqual(code, 0)
        self.assertIn(_key(4), [x["key"] for x in data["pool"]])

    def test_listed_ids_built_once(self):
        self._write_catalog({_key(n): _entry(_key(n)) for n in range(1, 401)})
        with mock.patch.object(lane_effort, "listed_ids", wraps=lane_effort.listed_ids) as listed:
            code, data, _ = self._propose("review")
        self.assertEqual((code, len(data["pool"]), listed.call_count), (0, 400, 1))

    def test_empty_pool_and_empty_catalog(self):
        self._write_catalog({_key(9): _catalog()[_key(9)]})
        _, data, _ = self._propose("review")
        self.assertTrue(data["empty"])
        self._write_catalog({})
        code, _, err = self._propose("review")
        self.assertEqual(code, 2)
        self.assertIn("model catalog is empty", err)


class TestProposeReadOnly(_Scratch):
    def test_catalog_and_tree_unchanged(self):
        def tree():
            return sorted(os.path.join(root, f) for root, _, files in os.walk(self.root)
                          for f in files)
        with open(self.catalog_path, "rb") as stream:
            before = stream.read(), os.stat(self.catalog_path).st_mtime_ns, tree()
        self._propose("review", "--jev", score_judge_fn=lambda env: lambda pairs: [])
        with open(self.catalog_path, "rb") as stream:
            self.assertEqual(before, (stream.read(), os.stat(self.catalog_path).st_mtime_ns,
                                      tree()))

    def test_detect_goes_through_the_seams_only(self):
        which = mock.Mock(return_value=None)
        fail = mock.Mock(side_effect=AssertionError("unexpected host call"))
        code, out, _ = self._call(["propose-lanes", "--purpose", "review", "--catalog-path",
                                   self.catalog_path, "--detect"], which_fn=which, run_fn=fail,
                                  popen_fn=fail, urlopen_fn=fail)
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["stale_checked"])
        self.assertTrue(which.called)
        fail.assert_not_called()

    def test_jev_items_hold_closed_facts_only(self):
        entries = _catalog()
        entries[_key(1)]["usage_limit_note"] = "NOTE-SENTINEL"
        self._write_catalog(entries)
        seen = []
        def judge(pairs):
            seen.extend(pairs)
            return []
        self._propose("review", "--jev", score_judge_fn=lambda env: judge)
        self.assertTrue(seen)
        for purpose, facts in seen:
            self.assertEqual(purpose, "review")
            self.assertTrue(facts.startswith("Facts: tier "))
            for forbidden in ("NOTE-SENTINEL", "placeholder", "fake", "router-env", self.root):
                self.assertNotIn(forbidden, facts)


if __name__ == "__main__":
    unittest.main()
