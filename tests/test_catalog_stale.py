"""Regression tests for proof-based catalog report states."""

import json
import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec.catalog_build import CatalogSources, build_model_catalog
from ai_kit_spec.catalog_report import context_line, listing_state, report_rows


def _entry(model_id, runtime, **fields):
    row = {"model_id": model_id}
    row.update(fields.pop("runtime_fields", {}))
    return {
        "provider": "fake", "runtimes": {runtime: row}, "source": {},
        "confidence": "high", "last_verified": "2026-11-19", **fields,
    }


def _clis(**overrides):
    defaults = {
        "opencode": {"installed": True, "listing": "ok", "models": [],
                     "listed_from": {"command": "models", "version": "v1", "at": "T"}},
        "pi": {"installed": True, "listing": "none"},
        "copilot": {"installed": True, "listing": "none"},
    }
    defaults.update(overrides)
    return {"clis": defaults}


def _rows(catalog, clis=None, fresh=False, optional=None):
    return report_rows(catalog, {"clis": clis or {}}, optional=optional, fresh=fresh)


def _by_id(rows, model_id):
    return next(row for row in rows if row.model_id == model_id)


class TestStaleOnProof(unittest.TestCase):
    def test_removed_after_good_listing_and_failed_listing(self):
        catalog = {
            "fake/placeholder-model-1": _entry("router-env/placeholder-model-1", "opencode",
                                                runtime_fields={"last_seen": "seen-1"}),
            "fake/placeholder-model-2": _entry("router-env/placeholder-model-2", "opencode",
                                                runtime_fields={"last_seen": "seen-2"}),
            "fake/placeholder-model-3": _entry("router-env/placeholder-model-3", "pi"),
        }
        clis = {
            "opencode": {"installed": True, "listing": "ok",
                         "models": ["router-env/placeholder-model-1"],
                         "listed_from": {"at": "listing-time"}},
            "pi": {"installed": True, "listing": "failed", "listing_error": "exit 1: boom"},
        }
        rows = _rows(catalog, clis, fresh=True)
        self.assertEqual([(row.runtime, row.model_id) for row in rows], [
            ("opencode", "router-env/placeholder-model-1"),
            ("opencode", "router-env/placeholder-model-2"),
            ("pi", "router-env/placeholder-model-3"),
        ])
        self.assertEqual(_by_id(rows, "router-env/placeholder-model-2").stale,
                         "stale (not in the listing of listing-time; last seen seen-2)")
        self.assertEqual(_by_id(rows, "router-env/placeholder-model-2").listing, "not listed")
        self.assertEqual(_by_id(rows, "router-env/placeholder-model-1").listing, "listed")
        failed = _by_id(rows, "router-env/placeholder-model-3")
        self.assertEqual(failed.stale, "not checked")
        self.assertEqual(failed.listing, "listing failed: exit 1: boom")

    def test_reappearing_model_not_stale(self):
        catalog = {
            "fake/placeholder-model-2": _entry("router-env/placeholder-model-2", "opencode"),
            "fake/placeholder-model-3": _entry("router-env/placeholder-model-3", "pi"),
        }
        clis = {
            "opencode": {"installed": True, "listing": "ok",
                         "models": ["router-env/placeholder-model-2"]},
            "pi": {"installed": True, "listing": "ok",
                   "models": ["router-env/placeholder-model-3"]},
        }
        self.assertFalse(any(row.stale for row in _rows(catalog, clis, fresh=True)))

    def test_usability_display(self):
        catalog = {
            "fake/placeholder-model-1": _entry("router-env/placeholder-model-1", "opencode",
                runtime_fields={"usability": {"state": "verified", "at": "2026-11-19T00:00:00Z",
                                               "via": "check-reviewer"}}),
            "fake/placeholder-model-2": _entry("router-env/placeholder-model-2", "opencode",
                runtime_fields={"usability": {"state": "rejected", "at": "T",
                                               "via": "check-reviewer", "error": "boom"}}),
            "fake/placeholder-model-3": _entry("router-env/placeholder-model-3", "opencode"),
        }
        clis = {"opencode": {"installed": True, "listing": "ok", "models": [
            "router-env/placeholder-model-1", "router-env/placeholder-model-2",
            "router-env/placeholder-model-3"], "model_records": {
                "router-env/placeholder-model-1": {"enabled": False}}}}
        rows = _rows(catalog, clis)
        self.assertEqual(_by_id(rows, "router-env/placeholder-model-1").usability,
                         "listed disabled by host")
        self.assertEqual(_by_id(rows, "router-env/placeholder-model-2").usability,
                         "rejected T: boom")
        self.assertEqual(_by_id(rows, "router-env/placeholder-model-3").usability, "unverified")


class TestReportStates(unittest.TestCase):
    def test_cached_listing_without_the_model_is_not_listed(self):
        catalog = {"fake/placeholder-model-1": _entry("router-env/placeholder-model-1", "pi")}
        clis = {"pi": {"installed": True, "listing": "ok",
                       "models": ["router-env/placeholder-model-2"]}}
        row = _by_id(_rows(catalog, clis), "router-env/placeholder-model-1")
        self.assertEqual(row.listing, "not listed")

    def test_non_dict_cli_row_is_skipped(self):
        self.assertEqual(report_rows({}, {"clis": {"pi": "oops"}}), [])

    def test_listing_state_without_listing_key_is_not_checked(self):
        self.assertEqual(listing_state({"installed": True}), "not checked")

    def test_stale_provider(self):
        catalog = {
            "fake/placeholder-model-1": _entry("fake/placeholder-model-1", "opencode"),
            "fake/placeholder-model-2": _entry("router-env/placeholder-model-2", "opencode"),
        }
        cli = {"opencode": {"installed": True, "listing": "ok",
                            "models": ["router-env/placeholder-model-2"]}}
        row = _by_id(_rows(catalog, cli, fresh=True), "fake/placeholder-model-1")
        self.assertIn("stale-provider", row.stale)
        self.assertIn("no listed model from fake", row.stale)

    def test_marked_by_source(self):
        catalog = {"fake/placeholder-model-1": _entry(
            "router-env/placeholder-model-1", "opencode",
            facts={"status": {"value": "deprecated", "label": "measured",
                               "source": "models.dev", "fetched_at": "T"}})}
        row = _by_id(_rows(catalog, {"opencode": {"installed": True, "listing": "ok",
                     "models": ["router-env/placeholder-model-1"]}}, fresh=True),
                     "router-env/placeholder-model-1")
        self.assertEqual(row.marked, "marked by source: deprecated (models.dev)")
        self.assertEqual(row.stale, "")

    def test_empty_and_no_listing(self):
        catalog = {
            "fake/placeholder-model-1": _entry("router-env/placeholder-model-1", "opencode"),
            "fake/placeholder-model-2": _entry("router-env/placeholder-model-2", "copilot"),
        }
        clis = {"opencode": {"installed": True, "listing": "ok", "models": []},
                "copilot": {"installed": True, "listing": "none"}}
        rows = _rows(catalog, clis, fresh=True)
        opencode = _by_id(rows, "router-env/placeholder-model-1")
        copilot = _by_id(rows, "router-env/placeholder-model-2")
        self.assertEqual(opencode.listing, "listed, empty")
        self.assertTrue(opencode.stale.startswith("stale"))
        self.assertEqual(copilot.listing, "installed, no listing")
        self.assertEqual(copilot.stale, "not checked")

    def test_context_line(self):
        value = {"value": 200000, "label": "measured", "source": "pi listing", "fetched_at": "T"}
        self.assertEqual(context_line({"context": value}), "200000 (measured, pi listing, T)")
        self.assertEqual(context_line({}), "unknown")

    def test_failed_listing_keeps_cache(self):
        entry = {"provider": "fake", "runtimes": {"pi": {"model_id": "placeholder-model-1",
                 "context": {"value": 200000, "label": "measured", "source": "fixture",
                              "fetched_at": "T"}, "last_seen": "T"}},
                 "source": {}, "confidence": "high", "last_verified": "2026-11-19"}
        existing = {"fake/placeholder-model-1": entry}
        result, rejected, unmatched = build_model_catalog(
            [], CatalogSources({}, False, [], False), existing)
        self.assertEqual(rejected, [])
        self.assertEqual(unmatched, [])
        self.assertEqual(json.dumps(result, sort_keys=True), json.dumps(existing, sort_keys=True))

    def test_failed_listing_with_old_models_not_checked(self):
        catalog = {"fake/placeholder-model-1": _entry("router-env/placeholder-model-1", "pi")}
        clis = {"pi": {"installed": True, "listing": "failed", "models": [
            "router-env/placeholder-model-2"]}}
        self.assertEqual(_by_id(_rows(catalog, clis, fresh=True),
                               "router-env/placeholder-model-1").stale, "not checked")

    def test_cached_listing_dated(self):
        catalog = {"fake/placeholder-model-1": _entry("router-env/placeholder-model-1", "pi")}
        clis = {"pi": {"installed": True, "listing": "ok", "models": [],
                       "listed_from": {"at": "2026-11-01T00:00:00Z"}}}
        cached = _by_id(_rows(catalog, clis), "router-env/placeholder-model-1")
        self.assertEqual(cached.stale, "not checked (cached 2026-11-01T00:00:00Z)")
        fresh = _by_id(_rows(catalog, clis, fresh=True), "router-env/placeholder-model-1")
        self.assertEqual(fresh.stale,
                         "stale (not in the listing of 2026-11-01T00:00:00Z; last seen never)")

    def test_facts_and_sources_shown(self):
        facts = {name: {"value": val, "label": "measured", "source": "fixture",
                        "fetched_at": "T"} for name, val in
                 (("tier", "strong"), ("class", "general"), ("cost_band", "low"))}
        catalog = {"fake/placeholder-model-1": _entry("router-env/placeholder-model-1", "pi",
                                                       facts=facts, runtime_fields={"listed_from": [
            {"label": "web, unverified", "url": "https://example.invalid", "date": "T"},
            {"label": "seed"}]})}
        row = _by_id(_rows(catalog, {"pi": {"installed": True, "listing": "none"}}),
                     "router-env/placeholder-model-1")
        for name in ("tier:", "class:", "cost_band:", "strong (measured, fixture, T)"):
            self.assertIn(name, row.facts)
        self.assertIn("web, unverified (https://example.invalid, T)", row.listed_from)
        self.assertIn("seed", row.listed_from)

    def test_optional_names_not_lost(self):
        candidate = {"name": "placeholder-model-9", "sources": [
            {"label": "web, unverified", "url": "https://example.invalid", "date": "T"}]}
        row = _by_id(_rows({}, {}, optional={"copilot": [candidate]}), "placeholder-model-9")
        self.assertEqual(row.listing, "not listed")
        self.assertEqual(row.stale, "unmatched")

    def test_listed_but_unmatched_shown(self):
        cli = {"opencode": {"installed": True, "listing": "ok", "models": [
            "router-env/placeholder-model-1", "router-env/placeholder-model-4"]}}
        catalog = {"fake/placeholder-model-1": _entry("router-env/placeholder-model-1", "opencode")}
        rows = _rows(catalog, cli)
        row = _by_id(rows, "router-env/placeholder-model-4")
        self.assertEqual((row.key, row.listing, row.stale), ("", "listed", "unmatched"))

    def test_host_row_without_candidates(self):
        rows = _rows({}, {"pi": {"installed": True, "listing": "ok", "models": []}})
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].model_id, rows[0].listing), ("-", "listed, empty"))

    def test_order_independent(self):
        one = _entry("router-env/placeholder-model-1", "pi")
        two = _entry("router-env/placeholder-model-2", "pi")
        first = _rows({"fake/placeholder-model-1": one, "fake/placeholder-model-2": two})
        second = _rows({"fake/placeholder-model-2": two, "fake/placeholder-model-1": one})
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
