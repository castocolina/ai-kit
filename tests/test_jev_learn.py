"""Behaviour of the Laya records module skills/jev-fast-decision/scripts/jev_learn.py (plan 34-03):
the version order, the fingerprint, the version-keyed records and the fetch-once of the published
notes. Every fetch is an injected fake over tests/fixtures/jev/laya-upstream.json, and the state
folder is a temp directory, so nothing touches the network or the real environment."""

import copy
import importlib.util
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from tests.test_jev_fast_decision import (
    _REAL_PUBLIC_GET,
    JR,
    JevStub,
    _ClientCase,
    closed_port_url,
    noul_item,
    payload,
)

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

    def test_idle_never_borrows_another_versions_fingerprint(self):
        """WR-201: an idle Laya on version B must not take version A's fingerprint."""
        moved = copy.deepcopy(FIX["health_loaded"])
        moved["revisions"] = {"laya-english": "rev-b2"}
        loaded_b = self._server("0.4.27")
        loaded_a = {"health": moved, "openapi": FIX["openapi"], "configured_version": "0.4.99"}
        idle_b = {"health": FIX["health_idle"], "openapi": FIX["openapi"],
                  "configured_version": "0.4.27"}
        self._learn(loaded_b, FakeFetch(_version_pages("0.4.27")))
        self._learn(loaded_a, FakeFetch(_version_pages("0.4.99")))
        before = self._bytes_on_disk()
        idle = FakeFetch({})
        out = self._learn(idle_b, idle)
        self.assertEqual(out["record"], "known")
        self.assertEqual(idle.calls, [])
        self.assertEqual(self._bytes_on_disk(), before)
        back = FakeFetch({})
        self.assertEqual(self._learn(loaded_b, back)["record"], "known")
        self.assertEqual(back.calls, [])

    def test_a_missing_first_fingerprint_is_filled_in_without_a_refetch(self):
        """IN-203: no /openapi.json on the first probe stores no fingerprint; the next good probe
        fills it in, reports known and fetches nothing."""
        blind = {"health": FIX["health_loaded"], "openapi": None, "configured_version": "0.4.27"}
        first = self._learn(blind, FakeFetch(_version_pages("0.4.27")))
        self.assertEqual(first["record"], "new")
        self.assertIsNone(self._stored()["0.4.27"]["fingerprint"])
        again = FakeFetch({})
        out = self._learn(self._server("0.4.27"), again)
        self.assertEqual(out["record"], "known")
        self.assertEqual(again.calls, [])
        full = jev_learn.fingerprint(FIX["health_loaded"], FIX["openapi"], {})
        self.assertEqual(self._stored()["0.4.27"]["fingerprint"], full["fingerprint"])
        moved = copy.deepcopy(FIX["health_loaded"])
        moved["revisions"] = {"laya-english": "rev-b2"}
        later = {"health": moved, "openapi": FIX["openapi"], "configured_version": "0.4.27"}
        changed = self._learn(later, FakeFetch(_version_pages("0.4.27")))
        self.assertEqual(changed["record"], "changed")

    def test_image_needs_image_input_wording(self):
        """IN-402: a Docker image is not an image feature; image input is."""
        self.assertEqual(jev_learn.features_in("The Docker image is smaller now."), [])
        self.assertEqual(jev_learn.features_in("Now accepts images in a request."), ["image"])
        self.assertEqual(jev_learn.features_in("Added image input support."), ["image"])
        linked = "[Images](https://docs.typesafe.ai/images.md) can go in the `state`."
        self.assertEqual(jev_learn.features_in(linked), ["image"])

    def test_a_version_never_reads_a_longer_versions_section(self):
        """IN-401: 0.4.2 must not match the heading of 0.4.2.1."""
        text = (
            "## What's new in 0.4.2.1\n\nlonger version note\n\n"
            "## What's new in 0.4.2 (2026-01-01)\n\nshort version note\n"
        )
        self.assertEqual(
            jev_learn.section(text, "0.4.2"),
            "## What's new in 0.4.2 (2026-01-01)\n\nshort version note",
        )
        self.assertEqual(jev_learn.section("## What's new in 0.4.2.1\n\nx\n", "0.4.2"), "")

    def test_idle_without_a_version_borrows_only_from_fp_records(self):
        self._learn(self._server("0.4.27"), FakeFetch(_version_pages("0.4.27")))
        idle = {"health": FIX["health_idle"], "openapi": FIX["openapi"], "configured_version": None}
        out = self._learn(idle, FakeFetch({}))
        self.assertEqual(out["record"], "pending_idle")
        self.assertIsNone(out["fingerprint"])

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

    def test_a_404_version_page_settles_as_no_published_notes(self):
        """WR-202: PyPI answering 404 for the version is an answer, so the key is recorded once."""
        readme = _bytes(FIX["readme"])
        pages = {PYPI_0_4_99: FileNotFoundError("http_404"), jev_learn.README_URL: readme}
        out = self._learn(self._server("0.4.99"), FakeFetch(pages))
        self.assertEqual(out["record"], "new")
        self.assertEqual(self._stored()["0.4.99"]["status"], "no_published_notes")
        self.assertNotIn("notice", out)
        again = FakeFetch({})
        self.assertEqual(self._learn(self._server("0.4.99"), again)["record"], "known")
        self.assertEqual(again.calls, [])

    def test_a_404_plus_an_outage_still_records_nothing(self):
        pages = {PYPI_0_4_99: FileNotFoundError("http_404"), jev_learn.README_URL: OSError("down")}
        out = self._learn(self._server("0.4.99"), FakeFetch(pages))
        self.assertEqual(out["record"], "fetch_failed")
        self.assertFalse(os.path.exists(self.records))

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


def _lowered(headers):
    """Header names in lower case, so an assertion does not depend on how the client spelt them."""
    return {name.lower(): value for name, value in headers.items()}


def _loopback_only_get(url, *args, **kwargs):
    """The real keyless fetcher for a 127.0.0.1 URL; any other host (the TypeSafe docs included)
    fails like a down network, so no test in this class can reach the internet."""
    if urllib.parse.urlsplit(url).hostname != "127.0.0.1":
        raise OSError(f"test blocks a fetch off loopback: {url}")
    return _REAL_PUBLIC_GET(url, *args, **kwargs)


class TestProbeLearning(_ClientCase):
    """The probe learns from a local Laya and from upstream, end to end against in-process stubs:
    the upstream URL constants point at a 127.0.0.1 stub, and the real keyless fetcher runs."""

    def setUp(self):
        super().setUp()
        # The real keyless fetcher, wrapped so each test can count its calls.
        self.fetch = mock.Mock(wraps=_loopback_only_get)
        patcher = mock.patch.object(JR, "_public_get", self.fetch)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_fetch_off_loopback_is_blocked(self):
        """IN-205: the wrapped fetcher refuses the TypeSafe docs URLs like any off-loopback host."""
        for url in (jev_learn.DOCS_INDEX_URL, jev_learn.DOCS_CHANGELOG_URL,
                    jev_learn.DOCS_MODELS_URL, jev_learn.README_URL):
            with self.assertRaises(OSError):
                self.fetch(url)

    def run_argv(self, argv):
        """main(argv): (exit code, the parsed stdout JSON)."""
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out):
            code = JR.main(argv)
        return code, json.loads(out.getvalue())

    def closed_base(self):
        """An upstream origin on a port nothing listens on: every fetch to it fails."""
        return closed_port_url().replace("/v1/systemone", "")

    def upstream(self, stub):
        """Point the three upstream URL constants at `stub`: the only place a fetch may go."""
        base = f"http://127.0.0.1:{stub.port}"
        urls = {
            "PYPI_VERSION_URL": base + "/pypi/laya/{version}/json",
            "PYPI_LATEST_URL": base + "/pypi/laya/json",
            "README_URL": base + "/README.md",
        }
        for name, url in urls.items():
            patcher = mock.patch.object(JR._LEARN, name, url)
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_user_config(self, text):
        folder = os.path.join(os.environ["XDG_CONFIG_HOME"], "ai-kit")
        os.makedirs(folder, exist_ok=True)
        Path(folder, "config.toml").write_text(text, encoding="utf-8")

    def records_file(self):
        return os.path.join(os.environ["XDG_STATE_HOME"], "ai-kit", "jev",
                            jev_learn.LAYA_RECORDS)

    def records_bytes(self):
        with open(self.records_file(), "rb") as handle:
            return handle.read()

    def test_probe_records_the_configured_version_once(self):
        self.write_user_config('[jev]\nlaya_version = "0.4.27"\n')
        pages = {
            "/pypi/laya/0.4.27/json": _bytes(FIX["pypi_0_4_27"]),
            "/README.md": _bytes(FIX["readme"]),
        }
        with JevStub(health_body=FIX["health_loaded"], openapi=FIX["openapi"]) as laya, \
                JevStub(pages=pages) as upstream:
            self.point_at(laya)
            self.upstream(upstream)
            code, report = self.run_probe()
            self.assertEqual(code, 0)
            entry = self.backend_entry(report, "laya")
            self.assertEqual(entry["version"], "0.4.27")
            self.assertEqual(entry["version_source"], "config")
            self.assertRegex(entry["fingerprint"], HEX12)
            self.assertEqual(entry["record"], "new")
            self.assertEqual(entry["documented_upstream"], ["batch", "long_context"])
            with open(self.records_file(), encoding="utf-8") as handle:
                self.assertIn("0.4.27", json.load(handle))
            gets = [record for record in upstream.requests if record["method"] == "GET"]
            self.assertEqual([record["path"] for record in gets],
                             ["/pypi/laya/0.4.27/json", "/README.md"])
            for record in gets:
                headers = _lowered(record["headers"])
                self.assertNotIn("authorization", headers)
                self.assertEqual(headers["user-agent"], "jev-fast-decision/2.0")
            _code, again = self.run_probe()
            self.assertEqual(self.backend_entry(again, "laya")["record"], "known")
            self.assertEqual(len(upstream.requests), 2, "a second probe makes no upstream request")

    def test_check_updates_refreshes_the_known_key(self):
        self.write_user_config('[jev]\nlaya_version = "0.4.27"\n')
        pages = {
            "/pypi/laya/0.4.27/json": _bytes(FIX["pypi_0_4_27"]),
            "/README.md": _bytes(FIX["readme"]),
        }
        with JevStub(health_body=FIX["health_loaded"], openapi=FIX["openapi"]) as laya, \
                JevStub(pages=pages) as upstream:
            self.point_at(laya)
            self.upstream(upstream)
            self.run_probe()
            seen = len(upstream.requests)
            code, out = self.run_argv(["--check-updates"])
            self.assertEqual(code, 0)
            self.assertEqual(out["status"], "ok")
            self.assertEqual(out["updates"]["laya"]["record"], "refreshed")
            self.assertEqual(len(upstream.requests) - seen, 2)
            # The Laya stays up; only the upstream moves to a closed port, so the refresh fails.
            before = self.records_bytes()
            closed = self.closed_base()
            with mock.patch.object(JR._LEARN, "PYPI_VERSION_URL",
                                   closed + "/pypi/laya/{version}/json"), \
                    mock.patch.object(JR._LEARN, "README_URL", closed + "/README.md"):
                _code, failed = self.run_argv(["--check-updates"])
            self.assertEqual(failed["updates"]["laya"]["record"], "fetch_failed")
            self.assertIn("previous records kept", failed["updates"]["laya"]["notice"])
            self.assertEqual(self.records_bytes(), before)

    def test_check_updates_is_disabled_with_the_knob_off(self):
        os.environ["GSD_PATH_JEV"] = "0"
        code, out = self.run_argv(["--check-updates"])
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "disabled")
        self.fetch.assert_not_called()

    def test_probe_under_a_deadline_never_fetches(self):
        self.write_user_config('[jev]\nlaya_version = "0.4.27"\n')
        os.environ["GSD_PATH_JEV_DEADLINE_SECONDS"] = "30"
        with JevStub(health_body=FIX["health_loaded"], openapi=FIX["openapi"]) as laya:
            self.point_at(laya)
            code, report = self.run_probe()
        self.assertEqual(code, 0)
        entry = self.backend_entry(report, "laya")
        self.assertEqual(entry["record"], "skipped_deadline")
        self.assertEqual(entry["version_source"], "not_read")
        self.fetch.assert_not_called()
        # IN-403: the probe's own /health check is the only request Laya sees; no identity reads.
        self.assertEqual([record["path"] for record in laya.requests], ["/health"])

    def test_unreachable_laya_reports_no_version(self):
        self.write_user_config('[jev]\nlaya_version = "0.4.27"\n')
        code, report = self.run_probe()  # the base case points Laya at a closed port
        self.assertEqual(code, 0)
        entry = self.backend_entry(report, "laya")
        self.assertEqual(entry["version_source"], "unreachable")
        self.assertIsNone(entry["fingerprint"])
        self.assertEqual(entry["record"], "unknown")
        self.fetch.assert_not_called()

    def test_new_upstream_feature_keeps_the_cell(self):
        self.write_user_config('[jev]\nlaya_version = "0.4.27"\n')
        pages = {
            "/pypi/laya/0.4.27/json": _bytes(FIX["pypi_0_4_27"]),
            "/README.md": _bytes(FIX["readme"]),
        }
        with JevStub(health_body=FIX["health_loaded"], openapi=FIX["openapi"]) as laya, \
                JevStub(pages=pages) as upstream:
            self.point_at(laya)
            self.upstream(upstream)
            _code, report = self.run_probe()
        self.assertEqual(self.backend_entry(report, "laya")["documented_upstream"],
                         ["batch", "long_context"])
        cells = JR.row_named("laya")["cells"]
        self.assertEqual(cells[JR.LONG_CONTEXT][0], "unsupported")
        self.assertEqual(cells[JR.BATCH][0], "unsupported")

    def test_answer_path_never_fetches(self):
        self.write_user_config('[jev]\nlaya_version = "0.4.27"\n')
        self.fetch.side_effect = AssertionError("the answer path fetched")
        self.enable(None)
        with JevStub() as laya:
            self.point_at(laya)
            out = self.run_screen(payload(noul_item("a")))
        self.assertEqual(out["status"], "ok")
        self.fetch.assert_not_called()

    def test_probe_and_fetch_carry_no_key(self):
        self.write_user_config('[jev]\nlaya_version = "0.4.27"\n')
        sentinel = "sk-sentinel-" + "7" * 20
        os.environ["LAYA_API_KEY"] = sentinel
        os.environ["TYPESAFE_API_KEY"] = sentinel
        pages = {
            "/pypi/laya/0.4.27/json": _bytes(FIX["pypi_0_4_27"]),
            "/README.md": _bytes(FIX["readme"]),
        }
        with JevStub(health_body=FIX["health_loaded"], openapi=FIX["openapi"]) as laya, \
                JevStub(pages=pages) as upstream:
            self.point_at(laya)
            self.upstream(upstream)
            _code, text = self.run_probe_text()
        self.assertNotIn(sentinel, text)
        self.assertTrue(upstream.requests)
        for record in upstream.requests:
            headers = _lowered(record["headers"])
            self.assertNotIn("authorization", headers)
            self.assertNotIn(sentinel, " ".join(headers.values()))

    def test_learn_survives_an_address_that_vanished_after_the_probe(self):
        """WR-101 follow-up: a usable probe whose address reads as None learns nothing, no crash."""
        row = {**JR.row_named("laya"), "url": lambda: (None, "invalid_url:jev_laya_url")}
        fields = JR._laya_learn(row, {"usable": True})
        self.assertEqual(fields["record"], "unknown")
        self.assertEqual(fields["version_source"], "unreachable")
        self.fetch.assert_not_called()

    def test_relative_xdg_state_home_is_ignored(self):
        """WR-205: a relative XDG_STATE_HOME falls back to ~/.local/state, like the XDG spec."""
        home = os.environ["HOME"]
        fallback = os.path.join(home, ".local", "state", "ai-kit")
        for value in ("relative-state", "./x", " "):
            with self.subTest(value=value), mock.patch.dict(os.environ, {"XDG_STATE_HOME": value}):
                self.assertEqual(JR._state_dir(), fallback)
                self.assertEqual(JR.answer_log_path(), os.path.join(fallback, "jev-answers.jsonl"))
        absolute = os.path.join(home, "abs-state")
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": absolute}):
            self.assertEqual(JR._state_dir(), os.path.join(absolute, "ai-kit"))

    def test_probe_reads_the_laya_address_once(self):
        """WR-101: an address that changes after the probe's first read is not dialed by the
        learn step: the identity GETs go where the probe went."""
        with JevStub(health_body=FIX["health_loaded"]) as laya:
            self.point_at(laya)
            row = JR.row_named("laya")
            original = row["url"]

            def flip():
                found = original()
                os.environ["JEV_LAYA_URL"] = closed_port_url()  # the config changes after this read
                return found

            with mock.patch.dict(row, {"url": flip}):
                code, report = self.run_probe()
        self.assertEqual(code, 0)
        self.assertTrue(self.backend_entry(report, "laya")["usable"])
        paths = [record["path"] for record in laya.requests]
        self.assertIn("/openapi.json", paths)

    def test_unusable_home_writes_no_state_under_the_cwd(self):
        """WR-501: no absolute XDG_STATE_HOME and an empty or relative HOME is no state dir."""
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        previous = os.getcwd()
        os.chdir(scratch)
        self.addCleanup(os.chdir, previous)
        for home in ("", "rel-home"):
            env = {"HOME": home, "XDG_STATE_HOME": "relative-state", "TYPESAFE_API_KEY": "",
                   "JEV_API_KEY": "", "JEV_API_KEY_FILE": ""}
            with self.subTest(home=home), mock.patch.dict(os.environ, env):
                with self.assertRaises(OSError):
                    JR._state_dir()
                JR.append_answer_log(["{}\n"])
                self.assertFalse(JR._typesafe_note_model("vendor/model-2026-01-01"))
                self.assertFalse(JR._typesafe_note_unknown("vendor/model-2026-01-01", ["x"]))
                self.assertEqual(JR._typesafe_learn(None, None), {"model_record": "write_failed"})
                self.assertIsNone(JR._typesafe_key()[0])
                self.assertEqual(os.listdir(scratch), [])

    def test_public_fetch_maps_404_to_file_not_found_and_5xx_to_oserror(self):
        with JevStub(health=404) as missing, self.assertRaises(FileNotFoundError):
            _REAL_PUBLIC_GET(f"http://127.0.0.1:{missing.port}/x")
        with JevStub(health=503) as down, self.assertRaises(OSError) as raised:
            _REAL_PUBLIC_GET(f"http://127.0.0.1:{down.port}/x")
        self.assertNotIsInstance(raised.exception, FileNotFoundError)

    def test_public_fetch_stops_at_its_deadline(self):
        drip = {"drip": 0.05, "body": "x" * 400, "headers": {"Content-Length": "400"}}
        with JevStub(pages={"/README.md": drip}) as upstream, \
                mock.patch.object(JR, "_FETCH_TIMEOUT", 0.5):
            started = time.monotonic()
            with self.assertRaises(OSError):
                _REAL_PUBLIC_GET(f"http://127.0.0.1:{upstream.port}/README.md")
            self.assertLess(time.monotonic() - started, 3.0)

    def test_trickling_laya_identity_stops_at_its_deadline(self):
        drip = {"drip": 0.05, "body": "x" * 400, "headers": {"Content-Length": "400"}}
        with JevStub(health_body=FIX["health_loaded"], pages={"/openapi.json": drip}) as laya:
            self.point_at(laya)
            started = time.monotonic()
            code, report = self.run_probe()
            self.assertLess(time.monotonic() - started, 3.0)
        self.assertEqual(code, 0)
        entry = self.backend_entry(report, "laya")
        self.assertIsNone(entry["fingerprint"])
        self.assertEqual(entry["record"], "unknown")


if __name__ == "__main__":
    unittest.main()
