"""Tests for the synthetic Arena datasets-server reader."""

import json
import os
import sys
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))
from ai_kit_spec import arena_source

_FIXTURE = Path(__file__).parent / "fixtures" / "arena_rows.json"


class _Server:
    def __init__(self, rows):
        self.rows = rows
        self.urls = []
        self.rows_snapshot = rows

    def __call__(self, url, headers):
        self.urls.append(url)
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query)
        selected = (
            self.rows_snapshot
            if parsed.path.endswith("/rows")
            else [
                row
                for row in self.rows
                if row.get("category") == query["where"][0].split("='")[1][:-1]
            ]
        )
        offset = int(query["offset"][0])
        length = int(query["length"][0])
        return {
            "rows": [{"row": row} for row in selected[offset : offset + length]],
            "num_rows_total": len(selected),
        }


class TestArenaSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(_FIXTURE.read_text(encoding="utf-8"))["rows"]

    def fetch(self, server, **kwargs):
        return arena_source.fetch_arena(
            fetch_fn=server, sleep_fn=lambda seconds: None, page_length=2, **kwargs
        )

    def test_reads_seven_categories(self):
        data, ok = self.fetch(_Server(self.rows))
        self.assertTrue(ok)
        self.assertEqual(set(data["categories"]), set(arena_source.ARENA_CATEGORIES))
        self.assertEqual(data["categories"]["overall"]["placeholder-model-1"]["rating"], 1100)

    def test_filter_url_shape(self):
        server = _Server(self.rows)
        self.fetch(server)
        urls = [url for url in server.urls if urllib.parse.urlsplit(url).path.endswith("/filter")]
        self.assertTrue(urls)
        for url in urls:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            self.assertEqual(query["dataset"], ["lmarena-ai/leaderboard-dataset"])
            self.assertEqual(query["config"], ["text"])
            self.assertEqual(query["split"], ["latest"])
            self.assertEqual(query["length"], ["2"])
            self.assertEqual(
                query["where"], ['"category"=\'' + query["where"][0].split("='")[1][:-1] + "'"]
            )

    def test_progress_lines(self):
        lines = []
        self.fetch(_Server(self.rows), progress=lines.append)
        self.assertTrue(all(line.startswith("arena: ") for line in lines))
        self.assertGreaterEqual(len({line.split()[1] for line in lines}), 7)

    def test_records_config_and_split(self):
        data, _ = self.fetch(_Server(self.rows))
        self.assertEqual(data["config"], "text")
        self.assertEqual(data["split"], "latest")

    def test_skips_bad_rows(self):
        data, ok = self.fetch(_Server(self.rows))
        self.assertTrue(ok)
        self.assertNotIn("placeholder-model-6", data["categories"]["overall"])

    def test_retry_then_success(self):
        server = _Server(self.rows)
        sleeps = []
        attempts = 0

        def transient(url, headers):
            nonlocal attempts
            if urllib.parse.urlsplit(url).path.endswith("/filter") and attempts < 2:
                attempts += 1
                raise urllib.error.URLError("temporary")
            return server(url, headers)

        data, ok = arena_source.fetch_arena(transient, sleep_fn=sleeps.append, page_length=2)
        self.assertTrue(ok)
        self.assertEqual(sleeps, [1.0, 1.0])
        self.assertEqual(data["categories"]["overall"]["placeholder-model-1"]["rating"], 1100)

    def test_rows_fallback(self):
        server = _Server(self.rows)

        def broken_math(url, headers):
            if urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("where") == [
                "\"category\"='math'"
            ]:
                raise OSError("offline")
            return server(url, headers)

        data, ok = arena_source.fetch_arena(
            broken_math, sleep_fn=lambda seconds: None, page_length=2
        )
        self.assertTrue(ok)
        self.assertIn("placeholder-model-1", data["categories"]["math"])

    def test_fallback_failure_keeps_partial(self):
        server = _Server(self.rows)

        def broken_math_and_rows(url, headers):
            parsed = urllib.parse.urlsplit(url)
            if parsed.path.endswith("/rows") or urllib.parse.parse_qs(parsed.query).get(
                "where"
            ) == ["\"category\"='math'"]:
                raise OSError("offline")
            return server(url, headers)

        data, ok = arena_source.fetch_arena(
            broken_math_and_rows, sleep_fn=lambda seconds: None, page_length=2
        )
        self.assertFalse(ok)
        self.assertIn("placeholder-model-1", data["categories"]["overall"])

    def test_fallback_replaces_not_mixes(self):
        server = _Server(self.rows)
        server.rows_snapshot = [
            row for row in self.rows if row.get("model_name") != "placeholder-model-1"
        ]

        def broken_math(url, headers):
            if urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("where") == [
                "\"category\"='math'"
            ]:
                raise OSError("offline")
            return server(url, headers)

        data, ok = arena_source.fetch_arena(
            broken_math, sleep_fn=lambda seconds: None, page_length=2
        )
        self.assertTrue(ok)
        self.assertNotIn("placeholder-model-1", data["categories"]["overall"])

    def test_page_ceiling(self):
        server = _Server(self.rows)
        with mock.patch.object(arena_source, "PAGE_CEILING", 2):
            data, ok = arena_source.fetch_arena(
                server, sleep_fn=lambda seconds: None, page_length=1
            )
        self.assertFalse(ok)
        self.assertFalse(
            any(urllib.parse.urlsplit(url).path.endswith("/rows") for url in server.urls)
        )
        self.assertIn("placeholder-model-1", data["categories"]["overall"])

    def test_whole_fetch_deadline(self):
        server = _Server(self.rows)
        ticks = iter(range(0, 10000, 100))
        data, ok = arena_source.fetch_arena(
            server, sleep_fn=lambda seconds: None, page_length=1, clock_fn=lambda: next(ticks)
        )
        self.assertFalse(ok)
        self.assertLessEqual(len(server.urls), 4)
        self.assertFalse(
            any(urllib.parse.urlsplit(url).path.endswith("/rows") for url in server.urls)
        )
        self.assertIsInstance(data, dict)

    def test_malformed_pages_fail(self):
        pages = (
            {"rows": []},
            {"rows": "bad", "num_rows_total": 0},
            {"rows": ["bad"], "num_rows_total": 1},
        )
        for page in pages:
            with self.subTest(page=page):
                data, ok = arena_source.fetch_arena(
                    lambda url, headers, result=page: result,
                    sleep_fn=lambda seconds: None,
                )
                self.assertFalse(ok)
                self.assertIsInstance(data, dict)

    def test_premature_empty_page_fails(self):
        def empty_late(url, headers):
            return {"rows": [], "num_rows_total": 500}

        data, ok = arena_source.fetch_arena(
            empty_late, sleep_fn=lambda seconds: None, page_length=100
        )
        self.assertFalse(ok)
        self.assertIsInstance(data, dict)

    def test_outage_never_raises(self):
        data, ok = arena_source.fetch_arena(
            lambda url, headers: (_ for _ in ()).throw(OSError("offline")),
            sleep_fn=lambda seconds: None,
        )
        self.assertFalse(ok)
        self.assertEqual(data["config"], "text")


if __name__ == "__main__":
    unittest.main()
