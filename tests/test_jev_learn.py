"""Behaviour of the Laya records module skills/jev-fast-decision/scripts/jev_learn.py (plan 34-03):
the version order, the fingerprint, the version-keyed records and the fetch-once of the published
notes. Every fetch is an injected fake over tests/fixtures/jev/laya-upstream.json, and the state
folder is a temp directory, so nothing touches the network or the real environment."""

import copy
import importlib.util
import json
import os
import re
import shutil
import stat
import tempfile
import threading
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "skills" / "jev-fast-decision" / "scripts" / "jev_learn.py"
FIXTURE = REPO / "tests" / "fixtures" / "jev" / "laya-upstream.json"


def _load():
    spec = importlib.util.spec_from_file_location("jev_learn_under_test", MODULE)
    assert spec is not None and spec.loader is not None, MODULE
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


jev_learn = _load()
FIX = json.loads(FIXTURE.read_text(encoding="utf-8"))
PYPI_0_4_27 = jev_learn.PYPI_VERSION_URL.format(version="0.4.27")
PYPI_0_4_99 = jev_learn.PYPI_VERSION_URL.format(version="0.4.99")
HEX12 = re.compile(r"^[0-9a-f]{12}$")


class FakeFetch:
    """Maps a URL to bytes, or to an exception to raise; an unmapped URL is an OSError."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        page = self.pages.get(url)
        if page is None:
            raise OSError("no fake page")
        if isinstance(page, BaseException):
            raise page
        return page


def _bytes(obj):
    if isinstance(obj, (dict, list)):
        return json.dumps(obj).encode("utf-8")
    if isinstance(obj, str):
        return obj.encode("utf-8")
    return obj


SYNTHETIC_0_4_99 = {
    "info": {
        "version": "0.4.99",
        "description": "# laya\n\n## What's new in 0.4.99\n\n"
        "* **Synthetic note** for the tests.\n\n## Where to go next\n\nmore\n",
    }
}


def _latest_pages():
    """The latest PyPI page and the README: the upstream of a Laya with no exposed version."""
    return {
        jev_learn.PYPI_LATEST_URL: _bytes(FIX["pypi_latest"]),
        jev_learn.README_URL: _bytes(FIX["readme"]),
    }


def _version_pages(version):
    """The per-version PyPI page and the README for a configured version (0.4.27 or 0.4.99)."""
    page = {"0.4.27": FIX["pypi_0_4_27"], "0.4.99": SYNTHETIC_0_4_99}[version]
    return {
        jev_learn.PYPI_VERSION_URL.format(version=version): _bytes(page),
        jev_learn.README_URL: _bytes(FIX["readme"]),
    }


class TestLayaRecords(unittest.TestCase):
    def setUp(self):
        root = tempfile.mkdtemp(prefix="jev-learn-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        self.state = os.path.join(root, "state")
        self.records = os.path.join(self.state, "jev", jev_learn.LAYA_RECORDS)
        self.verified = {"verified": ("choice", "noul", "score")}

    def _stored(self):
        with open(self.records, encoding="utf-8") as handle:
            return json.load(handle)

    def _bytes_on_disk(self):
        with open(self.records, "rb") as handle:
            return handle.read()

    def _server(self, configured="0.4.27"):
        return {
            "health": FIX["health_loaded"],
            "openapi": FIX["openapi"],
            "configured_version": configured,
        }

    def _learn(self, server, fetch, options=None):
        return jev_learn.learn_laya(server, self.state, fetch, options or {})

    def test_unknown_version_fetches_once_and_records(self):
        server = {
            "health": FIX["health_loaded"],
            "openapi": FIX["openapi"],
            "configured_version": "0.4.27",
        }
        fetch = FakeFetch(
            {PYPI_0_4_27: _bytes(FIX["pypi_0_4_27"]), jev_learn.README_URL: _bytes(FIX["readme"])}
        )
        out = jev_learn.learn_laya(server, self.state, fetch, self.verified)
        self.assertEqual(out["record"], "new")
        self.assertEqual(out["version"], "0.4.27")
        self.assertEqual(out["version_source"], "config")
        self.assertRegex(out["fingerprint"], HEX12)
        self.assertEqual(out["documented_upstream"], ["batch", "long_context"])
        self.assertIn("not verified here", out["notice"])
        self.assertEqual(fetch.calls, [PYPI_0_4_27, jev_learn.README_URL])
        entry = self._stored()["0.4.27"]
        self.assertTrue(entry["notes"].startswith("## What's new in 0.4.27"))
        self.assertEqual(entry["sources"], [PYPI_0_4_27, jev_learn.README_URL])

    def test_known_key_never_fetches(self):
        server = {
            "health": FIX["health_loaded"],
            "openapi": FIX["openapi"],
            "configured_version": "0.4.27",
        }
        first = FakeFetch(
            {PYPI_0_4_27: _bytes(FIX["pypi_0_4_27"]), jev_learn.README_URL: _bytes(FIX["readme"])}
        )
        jev_learn.learn_laya(server, self.state, first, self.verified)
        again = FakeFetch({})
        out = jev_learn.learn_laya(server, self.state, again, self.verified)
        self.assertEqual(out["record"], "known")
        self.assertEqual(again.calls, [])

    def test_version_source_order(self):
        def identity(health, configured):
            server = {"health": health, "openapi": FIX["openapi"], "configured_version": configured}
            return jev_learn.laya_identity(server, {})

        served = identity(dict(FIX["health_loaded"], version="0.5.0"), "0.4.27")
        self.assertEqual((served["version"], served["version_source"]), ("0.5.0", "server"))
        configured = identity(FIX["health_loaded"], "0.4.27")
        self.assertEqual(
            (configured["version"], configured["version_source"]), ("0.4.27", "config")
        )
        bare = identity(FIX["health_loaded"], None)
        self.assertIsNone(bare["version"])
        self.assertEqual(bare["version_source"], "not_exposed")
        self.assertRegex(bare["key"], r"^fp:[0-9a-f]{64}$")

    def test_not_exposed_fetches_latest_and_notes_it_may_differ(self):
        server = {
            "health": FIX["health_loaded"],
            "openapi": FIX["openapi"],
            "configured_version": None,
        }
        fetch = FakeFetch(_latest_pages())
        out = jev_learn.learn_laya(server, self.state, fetch, {})
        self.assertEqual(out["record"], "new")
        self.assertEqual(fetch.calls, [jev_learn.PYPI_LATEST_URL, jev_learn.README_URL])
        entry = self._stored()[out["record_key"]]
        self.assertEqual(entry["upstream_version"], "0.4.34")
        self.assertIn("may differ", entry["note"])
        self.assertTrue(entry["notes"].startswith("## What's new in 0.4.34"))

    def test_route_or_revision_change_is_a_new_fingerprint(self):
        base = jev_learn.fingerprint(FIX["health_loaded"], FIX["openapi"], {})["fingerprint"]
        self.assertRegex(base, r"^[0-9a-f]{64}$")
        more_routes = copy.deepcopy(FIX["openapi"])
        more_routes["paths"]["/v1/extra"] = {"post": {"summary": "Extra"}}
        moved = copy.deepcopy(FIX["health_loaded"])
        moved["revisions"] = {"laya-english": "rev-b2"}
        busier = dict(FIX["health_loaded"], idle_seconds=99.0)
        routed = jev_learn.fingerprint(FIX["health_loaded"], more_routes, {})
        self.assertNotEqual(routed["fingerprint"], base)
        revised = jev_learn.fingerprint(moved, FIX["openapi"], {})
        self.assertNotEqual(revised["fingerprint"], base)
        unchanged = jev_learn.fingerprint(busier, FIX["openapi"], {})
        self.assertEqual(unchanged["fingerprint"], base)

    def test_idle_reuses_the_last_matching_fingerprint(self):
        loaded = {
            "health": FIX["health_loaded"],
            "openapi": FIX["openapi"],
            "configured_version": None,
        }
        first = jev_learn.learn_laya(loaded, self.state, FakeFetch(_latest_pages()), {})
        idle = {"health": FIX["health_idle"], "openapi": FIX["openapi"], "configured_version": None}
        again = FakeFetch({})
        out = jev_learn.learn_laya(idle, self.state, again, {})
        self.assertEqual(out["fingerprint"], first["fingerprint"])
        self.assertTrue(out["idle"])
        self.assertEqual(out["record"], "known")
        self.assertEqual(again.calls, [])

    def test_idle_without_a_record_waits(self):
        server = {
            "health": FIX["health_idle"],
            "openapi": FIX["openapi"],
            "configured_version": None,
        }
        fetch = FakeFetch({})
        out = jev_learn.learn_laya(server, self.state, fetch, {})
        self.assertEqual(out["record"], "pending_idle")
        self.assertNotIn("record_key", out)
        self.assertIsNone(out["fingerprint"])
        self.assertEqual(fetch.calls, [])

    def test_same_version_new_fingerprint_is_changed(self):
        server = {
            "health": FIX["health_loaded"],
            "openapi": FIX["openapi"],
            "configured_version": "0.4.27",
        }
        first = jev_learn.learn_laya(server, self.state, FakeFetch(_version_pages("0.4.27")), {})
        self.assertEqual(first["record"], "new")
        moved = copy.deepcopy(FIX["health_loaded"])
        moved["revisions"] = {"laya-english": "rev-b2"}
        moved_server = {"health": moved, "openapi": FIX["openapi"], "configured_version": "0.4.27"}
        second = FakeFetch(_version_pages("0.4.27"))
        changed = jev_learn.learn_laya(moved_server, self.state, second, {})
        self.assertEqual(changed["record"], "changed")
        self.assertEqual(changed["previous_fingerprint"], first["fingerprint"])
        self.assertEqual(len(second.calls), 2)
        new_full = jev_learn.fingerprint(moved, FIX["openapi"], {})["fingerprint"]
        self.assertEqual(self._stored()["0.4.27"]["fingerprint"], new_full)
        same = FakeFetch({})
        self.assertEqual(
            jev_learn.learn_laya(moved_server, self.state, same, {})["record"], "known"
        )
        self.assertEqual(same.calls, [])
        more = copy.deepcopy(FIX["openapi"])
        more["paths"]["/v1/extra"] = {"post": {"summary": "Extra"}}
        routed_server = {"health": moved, "openapi": more, "configured_version": "0.4.27"}
        routed = jev_learn.learn_laya(
            routed_server, self.state, FakeFetch(_version_pages("0.4.27")), {}
        )
        self.assertEqual(routed["record"], "changed")
        self.assertEqual(routed["previous_fingerprint"], changed["fingerprint"])

    def test_idle_with_a_configured_version_waits_or_reuses(self):
        idle = {
            "health": FIX["health_idle"],
            "openapi": FIX["openapi"],
            "configured_version": "0.4.99",
        }
        fetch = FakeFetch({})
        waits = jev_learn.learn_laya(idle, self.state, fetch, {})
        self.assertEqual(waits["record"], "pending_idle")
        self.assertNotIn("record_key", waits)
        self.assertEqual(fetch.calls, [])
        loaded = {
            "health": FIX["health_loaded"],
            "openapi": FIX["openapi"],
            "configured_version": "0.4.99",
        }
        recorded = jev_learn.learn_laya(loaded, self.state, FakeFetch(_version_pages("0.4.99")), {})
        self.assertEqual(recorded["record"], "new")
        again = FakeFetch({})
        reuse = jev_learn.learn_laya(idle, self.state, again, {})
        self.assertEqual(reuse["record"], "known")
        self.assertEqual(again.calls, [])

    def test_failed_fetch_keeps_records_and_says_so(self):
        jev_learn.write_records(self.records, {"0.4.20": {"status": "ok", "notes": "kept"}})
        before = self._bytes_on_disk()
        down = self._learn(self._server(), FakeFetch({}))
        self.assertEqual(down["record"], "fetch_failed")
        self.assertIn("previous records kept", down["notice"])
        self.assertEqual(self._bytes_on_disk(), before)
        for body in ([], {"info": None}):
            fetch = FakeFetch({PYPI_0_4_27: _bytes(body), jev_learn.README_URL: OSError("down")})
            out = self._learn(self._server(), fetch)
            self.assertEqual(out["record"], "fetch_failed")
            self.assertIn(PYPI_0_4_27, out["notice"])
            self.assertIn("unexpected JSON shape", out["notice"])
            self.assertEqual(self._bytes_on_disk(), before)

    def test_no_published_notes(self):
        page = {"info": {"version": "0.4.99", "description": "# laya\n\nNo notes here.\n"}}
        fetch = FakeFetch({PYPI_0_4_99: _bytes(page), jev_learn.README_URL: _bytes(FIX["readme"])})
        out = self._learn(self._server("0.4.99"), fetch)
        self.assertEqual(out["record"], "new")
        entry = self._stored()["0.4.99"]
        self.assertEqual(entry["status"], "no_published_notes")
        self.assertEqual(entry["notes"], "")

    def test_invalid_utf8_is_replaced_and_stored_as_text(self):
        description = "## What's new in 0.4.27\n\n* Note BAD here.\n\n## Where to go next\n"
        raw = json.dumps({"info": {"version": "0.4.27", "description": description}})
        raw = raw.encode("utf-8").replace(b"BAD", b"\xff")
        fetch = FakeFetch({PYPI_0_4_27: raw, jev_learn.README_URL: _bytes(FIX["readme"])})
        out = self._learn(self._server(), fetch)
        self.assertEqual(out["record"], "new")
        notes = self._stored()["0.4.27"]["notes"]
        self.assertIsInstance(notes, str)
        self.assertIn("�", notes)

    def test_notes_are_trimmed(self):
        body = "## What's new in 0.4.27\n\n" + "x" * 10000 + "\n\n## Where to go next\n"
        page = {"info": {"version": "0.4.27", "description": body}}
        fetch = FakeFetch({PYPI_0_4_27: _bytes(page), jev_learn.README_URL: _bytes(FIX["readme"])})
        self._learn(self._server(), fetch)
        self.assertEqual(len(self._stored()["0.4.27"]["notes"]), jev_learn.NOTES_MAX_CHARS)

    def test_force_refresh_and_skipped_deadline(self):
        first = self._learn(
            self._server(),
            FakeFetch(_version_pages("0.4.27")),
            {"now": "2026-11-15T10:00:00+00:00"},
        )
        self.assertEqual(first["record"], "new")
        again = FakeFetch(_version_pages("0.4.27"))
        options = {"force": True, "now": "2026-11-16T10:00:00+00:00"}
        refreshed = self._learn(self._server(), again, options)
        self.assertEqual(refreshed["record"], "refreshed")
        self.assertEqual(len(again.calls), 2)
        self.assertEqual(self._stored()["0.4.27"]["checked_at"], "2026-11-16T10:00:00+00:00")
        deadline = FakeFetch({})
        skipped = self._learn(self._server("0.4.20"), deadline, {"fetch_allowed": False})
        self.assertEqual(skipped["record"], "skipped_deadline")
        self.assertEqual(deadline.calls, [])

    def test_parallel_writers_leave_one_entry(self):
        results = []

        def writer():
            fetch = FakeFetch(_version_pages("0.4.27"))
            results.append(self._learn(self._server(), fetch))

        threads = [threading.Thread(target=writer) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(results), 2)
        self.assertIn("0.4.27", self._stored())

    def test_records_are_private(self):
        self._learn(self._server(), FakeFetch(_version_pages("0.4.27")))
        folder = os.path.dirname(self.records)
        self.assertEqual(stat.S_IMODE(os.stat(self.records).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(folder).st_mode) & 0o077, 0)
        leftovers = [name for name in os.listdir(folder) if name.startswith(".jev-records-")]
        self.assertEqual(leftovers, [])

    def test_verified_features_are_never_reported_new(self):
        body = (
            "## What's new in 0.4.27\n\n* **Choice questions** are faster.\n"
            "* **Batch scoring** through the batch route.\n\n## Where to go next\n"
        )
        page = {"info": {"version": "0.4.27", "description": body}}
        fetch = FakeFetch({PYPI_0_4_27: _bytes(page), jev_learn.README_URL: _bytes(FIX["readme"])})
        out = self._learn(self._server(), fetch, {"verified": ("choice",)})
        self.assertEqual(out["documented_upstream"], ["batch"])
        self.assertNotIn("choice", out["notice"])

    def test_pypi_failing_alone_records_nothing(self):
        pypi_down = {PYPI_0_4_27: OSError("down"), jev_learn.README_URL: _bytes(FIX["readme"])}
        out = self._learn(self._server(), FakeFetch(pypi_down))
        self.assertEqual(out["record"], "fetch_failed")
        self.assertIn(PYPI_0_4_27, out["notice"])
        self.assertFalse(os.path.exists(self.records))
        self.assertEqual(
            self._learn(self._server(), FakeFetch(_version_pages("0.4.27")))["record"], "new"
        )
        before = self._bytes_on_disk()
        forced = self._learn(self._server(), FakeFetch(pypi_down), {"force": True})
        self.assertEqual(forced["record"], "fetch_failed")
        self.assertEqual(self._bytes_on_disk(), before)
        latest_down = {
            jev_learn.PYPI_LATEST_URL: OSError("down"),
            jev_learn.README_URL: _bytes(FIX["readme"]),
        }
        loaded = {
            "health": FIX["health_loaded"],
            "openapi": FIX["openapi"],
            "configured_version": None,
        }
        self.assertEqual(self._learn(loaded, FakeFetch(latest_down))["record"], "fetch_failed")
        self.assertEqual(self._bytes_on_disk(), before)

    def test_readme_failing_alone_keeps_found_notes(self):
        fetch = FakeFetch(
            {PYPI_0_4_27: _bytes(FIX["pypi_0_4_27"]), jev_learn.README_URL: OSError("down")}
        )
        out = self._learn(self._server(), fetch)
        self.assertEqual(out["record"], "new")
        entry = self._stored()["0.4.27"]
        self.assertEqual(entry["status"], "ok")
        self.assertTrue(entry["notes"].startswith("## What's new in 0.4.27"))
        self.assertEqual(entry["sources"], [PYPI_0_4_27])
        self.assertIn(jev_learn.README_URL, out["notice"])
        self.assertIn("OSError", out["notice"])
        self.assertIn("recorded from the sources that answered", out["notice"])


if __name__ == "__main__":
    unittest.main()
