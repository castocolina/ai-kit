"""Phase 35: catalog schema and per-runtime merge (model_catalog.py)."""

import os
import sys
import tempfile
import threading
import time
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.model_catalog import (
    locked_catalog_update,
    merge_catalog_entry,
    rebase_on_current,
)


def _entry(runtimes):
    return {
        "provider": "router-env",
        "runtimes": runtimes,
        "source": {},
        "confidence": "low",
        "last_verified": "2026-11-19",
    }


KEY = "router-env/placeholder-model-1"
USABILITY = {
    "state": "verified",
    "at": "2026-11-19T00:00:00Z",
    "via": "check-reviewer",
    "error": None,
}


class TestRuntimeDeepMerge(unittest.TestCase):
    def _merge(self, existing, incoming):
        result, error = merge_catalog_entry({KEY: existing}, KEY, incoming)
        self.assertIsNone(error)
        return result[KEY]["runtimes"]

    def test_usability_and_last_seen_survive_refresh(self):
        old = _entry({"pi": {"model_id": "placeholder-model-1", "ctx_window": 1000,
                              "usability": USABILITY, "last_seen": "2026-11-19T00:00:00Z"}})
        new = _entry({"pi": {"model_id": "placeholder-model-1", "ctx_window": 2000}})
        self.assertEqual(self._merge(old, new)["pi"], {
            "model_id": "placeholder-model-1", "ctx_window": 2000,
            "usability": USABILITY, "last_seen": "2026-11-19T00:00:00Z",
        })

    def test_runtime_none_clears_key(self):
        old = _entry({"pi": {"model_id": "placeholder-model-1", "ctx_window": 1000}})
        new = _entry({"pi": {"model_id": "placeholder-model-1", "ctx_window": None}})
        self.assertEqual(self._merge(old, new)["pi"], {"model_id": "placeholder-model-1"})

    def test_usability_is_per_runtime(self):
        old = _entry({"pi": {"model_id": "placeholder-model-1", "usability": USABILITY}})
        fresh = _entry({"opencode": {"model_id": "router-env/placeholder-model-1"}})
        runtimes = self._merge(old, fresh)
        self.assertEqual(runtimes["pi"], {
            "model_id": "placeholder-model-1", "usability": USABILITY
        })
        self.assertEqual(runtimes["opencode"], {"model_id": "router-env/placeholder-model-1"})
        rejected = _entry({"opencode": {"model_id": "router-env/placeholder-model-1",
                                         "usability": {"state": "rejected"}}})
        self.assertEqual(self._merge(_entry(runtimes), rejected)["pi"]["usability"], USABILITY)

    def test_new_runtime_added(self):
        old = _entry({"pi": {"model_id": "placeholder-model-1"}})
        new = _entry({"opencode": {"model_id": "router-env/placeholder-model-1"}})
        self.assertEqual(self._merge(old, new), {
            "pi": {"model_id": "placeholder-model-1"},
            "opencode": {"model_id": "router-env/placeholder-model-1"},
        })


class TestLockedCatalogUpdate(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="p35-catalog-")
        self.path = os.path.join(self.root, "catalog.json")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)

    def test_parallel_writers_keep_every_entry(self):
        cache_write_json(self.path, {})

        def writer(index):
            def add(current):
                time.sleep(0.01)
                current[f"router-env/placeholder-model-{index}"] = {"index": index}
                return current
            locked_catalog_update(self.path, add)

        workers = [threading.Thread(target=writer, args=(index,)) for index in range(1, 9)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        stored = cache_read_json(self.path)
        assert stored is not None
        self.assertEqual(set(stored), {
            f"router-env/placeholder-model-{index}" for index in range(1, 9)
        })

    def test_unreadable_catalog_is_not_overwritten(self):
        with open(self.path, "wb") as handle:
            handle.write(b"{not json")
        with self.assertRaises(ValueError):
            locked_catalog_update(self.path, lambda current: current)
        with open(self.path, "rb") as handle:
            self.assertEqual(handle.read(), b"{not json")
        missing_path = os.path.join(self.root, "missing.json")
        received = []
        locked_catalog_update(
            missing_path, lambda current: received.append(current) or {"ok": True}
        )
        self.assertEqual(received, [{}])
        self.assertEqual(cache_read_json(missing_path), {"ok": True})

    def test_refresh_publish_keeps_concurrent_probe_and_confirmation(self):
        key = "fake/placeholder-model-1"
        second = "fake/placeholder-model-2"
        third = "fake/placeholder-model-3"
        original = {
            key: _entry({"pi": {"model_id": "placeholder-model-1", "ctx_window": 1000}}),
            second: _entry({"pi": {"model_id": "placeholder-model-2"}}),
        }
        cache_write_json(self.path, original)
        built_entry = _entry({"pi": {"model_id": "placeholder-model-1", "ctx_window": 2000}})
        built_entry["facts"] = {"class": {"value": "general", "label": "judged",
            "source": "ai-kit class rule", "fetched_at": "2026-11-20T00:00:00Z",
            "confidence": "rule"}}
        built = {key: built_entry, third: _entry({"pi": {"model_id": "placeholder-model-3"}})}

        def probe(current):
            current[key]["runtimes"]["pi"]["usability"] = USABILITY
            return current

        locked_catalog_update(self.path, probe)

        def confirm(current):
            current[key]["confirmed_fields"] = {"class": {"by": "confirm-model",
                "at": "2026-11-20T00:00:00Z", "note": ""}}
            current[key]["facts"] = {"class": {"value": "coding", "label": "user-stated",
                "source": "confirm-model", "fetched_at": "2026-11-20T00:00:00Z"}}
            return current

        locked_catalog_update(self.path, confirm)
        locked_catalog_update(self.path, lambda current: rebase_on_current(current, built))
        result = cache_read_json(self.path)
        assert result is not None
        self.assertEqual(result[key]["runtimes"]["pi"], {
            "model_id": "placeholder-model-1", "ctx_window": 2000, "usability": USABILITY
        })
        self.assertEqual(result[key]["confirmed_fields"], confirm_fields := {
            "class": {"by": "confirm-model", "at": "2026-11-20T00:00:00Z", "note": ""}
        })
        self.assertEqual(result[key]["facts"]["class"], {
            "value": "coding", "label": "user-stated", "source": "confirm-model",
            "fetched_at": "2026-11-20T00:00:00Z"
        })
        self.assertEqual(result[second], original[second])
        self.assertEqual(result[third], built[third])
        self.assertTrue(confirm_fields)


if __name__ == "__main__":
    unittest.main()
