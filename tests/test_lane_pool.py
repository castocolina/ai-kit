"""Phase 36: lane_pool (propose-lanes candidate rows and groups)."""

import ast
import copy
import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import lane_pool
from ai_kit_spec.model_catalog import canonical_key

T = "2026-11-20T00:00:00Z"


def _fact(value):
    return {"value": value, "label": "measured", "source": "fixture", "fetched_at": T}


def _key(n):
    return canonical_key("fake", f"placeholder-model-{n}")


def _entry(n, klass="flagship", tier="frontier", band="high", runtimes=("pi",), **fields):
    return {"provider": "fake", "runtimes": {rid: {"model_id": _key(n)} for rid in runtimes},
            "source": {}, "confidence": "low", "last_verified": "2026-11-20",
            "facts": {"tier": _fact(tier), "class": _fact(klass), "cost_band": _fact(band)},
            **fields}


def _rows(entry, snapshot=None):
    entries = {_key(1): entry}
    return lane_pool.build_rows(entries, snapshot or {"clis": {}})


def _split(entry, purpose="review", snapshot=None, fresh=False):
    entries = {_key(1): entry}
    snapshot = snapshot or {"clis": {}}
    return lane_pool.split_pools(lane_pool.build_rows(entries, snapshot), purpose, snapshot,
                                 entries, fresh)


class TestRows(unittest.TestCase):
    def test_one_row_per_runtime_sorted(self):
        entry = _entry(1, runtimes=("pi", "opencode"))
        entry["runtimes"]["pi"]["efforts"] = ["high", 3]
        entry["facts"]["strengths"] = _fact(["coding", "bogus"])
        rows = lane_pool.build_rows({"_meta": {"schema_version": 4}, _key(1): entry}, {})
        self.assertEqual([(r.key, r.runtime) for r in rows],
                         [(_key(1), "opencode"), (_key(1), "pi")])
        row = rows[1]
        self.assertEqual((row.tier, row.klass, row.cost_band), ("frontier", "flagship", "high"))
        self.assertEqual((row.strengths, row.efforts, row.usability, row.provider_prefix),
                         (("coding",), ("high",), "unverified", "fake"))

    def test_out_of_list_fact_is_unknown(self):
        entry = _entry(1, tier="huge")
        self.assertEqual(_rows(entry)[0].tier, "unknown")
        del entry["facts"]["class"]["label"]
        self.assertEqual(_rows(entry)[0].klass, "unknown")
        entry["facts"] = {}
        row = _rows(entry)[0]
        self.assertEqual((row.tier, row.klass, row.cost_band, row.strengths),
                         ("unknown", "unknown", "unknown", ()))

    def test_malformed_facts_read_unknown(self):
        for name, allowed in (("tier", ("frontier",)), ("class", ("flagship",)),
                              ("cost_band", ("high",))):
            for field in ("label", "value"):
                for bad in ([], {}, 3, None):
                    with self.subTest(name=name, field=field, bad=bad):
                        item: dict = _fact(allowed[0])
                        if bad is None:
                            del item[field]
                        else:
                            item[field] = bad
                        entry = {"facts": {name: item}}
                        self.assertEqual(lane_pool.fact_value(entry, name, allowed), "unknown")
                        if field == "label":
                            self.assertIsNone(lane_pool.checked_fact(entry, name))
            for facts in ([], {name: "bad"}):
                self.assertEqual(lane_pool.fact_value({"facts": facts}, name, allowed), "unknown")

    def test_class_decides_review_and_execute_pool(self):
        entry = _entry(1)
        self.assertEqual(len(_split(entry).pool), 1)
        self.assertEqual(len(_split(entry, "execute").wider), 1)


class TestDrops(unittest.TestCase):
    def test_rejected_dropped(self):
        entry = _entry(1)
        entry["runtimes"]["pi"]["usability"] = {"state": "rejected", "at": T, "error": "boom"}
        self.assertEqual(lane_pool.drop_reason(_rows(entry)[0], {}, set(), False), "rejected")
        self.assertEqual(_split(entry), lane_pool.PoolSplit([], [], [], []))

    def test_disabled_by_host_dropped(self):
        entry = _entry(1, runtimes=("opencode",))
        snap = {"clis": {"opencode": {"model_records": {_key(1): {"enabled": False}}}}}
        self.assertEqual(lane_pool.drop_reason(_rows(entry, snap)[0], {}, set(), False),
                         "listed disabled by host")
        self.assertFalse(_split(entry, snapshot=snap).pool)

    def test_stale_only_when_fresh(self):
        row = _rows(_entry(1))[0]
        cli = {"listing": "ok", "models": [_key(2)]}
        self.assertEqual(lane_pool.drop_reason(row, cli, set(), True), "stale")
        self.assertIsNone(lane_pool.drop_reason(row, cli, set(), False))

    def test_stale_provider_dropped(self):
        entry = _entry(1, runtimes=("opencode",))
        row = _rows(entry)[0]
        cli = {"listing": "ok", "models": [_key(1)]}
        self.assertEqual(lane_pool.drop_reason(row, cli, {"fake"}, True), "stale provider")
        self.assertIsNone(lane_pool.drop_reason(row, cli, set(), True))
        snap = {"clis": {"opencode": {"listing": "ok",
                                      "models": ["router-env/placeholder-model-9"]}}}
        self.assertFalse(_split(entry, snapshot=snap, fresh=True).pool)

    def test_unmatched_dropped(self):
        entry = _entry(1)
        entry["runtimes"]["pi"]["match"] = {"value": "unmatched", "label": "judged",
            "source": "ai-kit name rule", "fetched_at": T, "confidence": "rule"}
        self.assertEqual(lane_pool.drop_reason(_rows(entry)[0], {}, set(), True), "unmatched")
        self.assertFalse(_split(entry).pool)

    def test_plain_row_kept(self):
        row = _rows(_entry(1))[0]
        for fresh in (True, False):
            self.assertIsNone(lane_pool.drop_reason(row, {}, set(), fresh))

    def test_invalid_listing_is_not_stale(self):
        snap = {"clis": {"opencode": {"installed": True, "listing": "ok", "models": None}}}
        result = _split(_entry(1, runtimes=("opencode",)), snapshot=snap, fresh=True)
        self.assertEqual(len(result.pool), 1)


class TestGroups(unittest.TestCase):
    def test_unknown_class_and_unknown_tier(self):
        for purpose in ("review", "execute"):
            self.assertEqual(len(_split(_entry(1, klass="unknown"), purpose).unknown), 1)
        entry = _entry(1)
        del entry["facts"]["tier"]
        self.assertEqual(len(_split(entry).unknown), 1)
        self.assertEqual(len(_split(entry, "execute").wider), 1)

    def test_alias_with_declared_purpose(self):
        entry = _entry(1, klass="router", provider="router-env", name_declared_purpose="review")
        entry["runtimes"]["pi"]["model_id"] = "router-env/placeholder-alias-1"
        result = _split(entry)
        self.assertEqual(result.aliases[0][1], "purpose from the name: review")
        self.assertEqual((result.pool, result.unknown, result.wider), ([], [], []))
        self.assertFalse(_split(entry, "execute").aliases)

    def test_alias_without_purpose(self):
        entry = _entry(1, klass="router", provider="router-env")
        for purpose in ("review", "execute"):
            self.assertEqual(_split(entry, purpose).aliases[0][1], "purpose unknown")

    def test_rejected_alias_dropped(self):
        entry = _entry(1, provider="router-env")
        entry["runtimes"]["pi"]["usability"] = {"state": "rejected"}
        self.assertFalse(_split(entry).aliases)

    def test_runtime_filter(self):
        entry = _entry(1, runtimes=("pi", "opencode"))
        rows = lane_pool.build_rows({_key(1): entry}, {}, ("pi",))
        self.assertEqual([row.runtime for row in rows], ["pi"])

    def test_imports_stay_in_the_catalog_layer(self):
        path = os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review", "ai_kit_spec",
                            "lane_pool.py")
        with open(path, encoding="utf-8") as stream:
            text = stream.read()
        names = set()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                names.update(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module)
                names.update(item.name for item in node.names)
        for name in ("cli", "config_io", "detection", "ai_kit_spec.cli",
                     "ai_kit_spec.config_io", "ai_kit_spec.detection"):
            self.assertNotIn(name, names)
        self.assertNotIn("review_only", text)

    def test_inputs_not_mutated(self):
        entries = {_key(1): _entry(1)}
        before = copy.deepcopy(entries)
        rows = lane_pool.build_rows(entries, {})
        lane_pool.split_pools(rows, "review", {}, entries, True)
        self.assertEqual(entries, before)


if __name__ == "__main__":
    unittest.main()
