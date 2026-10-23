"""Phase 22 owner tooling: the capture trimmer's fail-closed behavior and the live self-tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / ".planning" / "phases" / "22-pi-live-validation" / "live"
TRIMMER = LIVE / "trim_pi_capture.py"

MODEL = {
    "id": "claude-sonnet-x",
    "name": "Sonnet X",
    "provider": "anthropic",
    "api": "anthropic-messages",
    "contextWindow": 200000,
    "maxTokens": 8192,
    "reasoning": True,
    "cost": {"input": 3, "output": 15},
    "baseUrl": "https://leak.example/v1",
    "apiKey": "sk-should-not-survive",
}


def _response(models: list, success: bool = True) -> str:
    envelope = {
        "id": "req-1",
        "type": "response",
        "command": "get_available_models",
        "success": success,
        "data": {"models": models},
    }
    return json.dumps(envelope) + "\n"


def _trim(raw_text: str, out_dir: Path) -> tuple[int, Path, str]:
    raw = out_dir / "raw.jsonl"
    out = out_dir / "capture.json"
    raw.write_text(raw_text, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-I", str(TRIMMER), str(raw), str(out), "--pi-version", "0.0.0-test"],
        capture_output=True, text=True, timeout=120, check=False,
    )
    return proc.returncode, out, proc.stderr


class TestCaptureTrimmer(unittest.TestCase):
    def test_trims_to_allowlist_and_drops_transport_fields(self):
        with tempfile.TemporaryDirectory(prefix="pi-trim-test-") as tmp:
            rc, out, err = _trim(_response([MODEL]), Path(tmp))
            self.assertEqual(rc, 0, err)
            text = out.read_text(encoding="utf-8")
            lowered = text.lower()
            self.assertNotIn("baseurl", lowered)
            self.assertNotIn("apikey", lowered)
            self.assertNotIn("sk-should-not-survive", text)
            self.assertNotIn("leak.example", text)
            payload = json.loads(text)
            self.assertEqual(payload["data"]["models"][0]["id"], "claude-sonnet-x")
            self.assertEqual(payload["_capture"]["count"], 1)
            self.assertEqual(payload["_capture"]["providers"], {"anthropic": 1})
            self.assertEqual(payload["_capture"]["pi_version"], "0.0.0-test")

    def test_fails_closed_on_unsuccessful_response_without_output(self):
        with tempfile.TemporaryDirectory(prefix="pi-trim-test-") as tmp:
            rc, out, _ = _trim(_response([MODEL], success=False), Path(tmp))
            self.assertNotEqual(rc, 0)
            self.assertFalse(out.exists())

    def test_fails_closed_when_no_get_available_models_response(self):
        with tempfile.TemporaryDirectory(prefix="pi-trim-test-") as tmp:
            rc, out, _ = _trim("not json\n", Path(tmp))
            self.assertNotEqual(rc, 0)
            self.assertFalse(out.exists())

    def test_fails_closed_on_two_responses(self):
        with tempfile.TemporaryDirectory(prefix="pi-trim-test-") as tmp:
            rc, out, _ = _trim(_response([MODEL]) + _response([MODEL]), Path(tmp))
            self.assertNotEqual(rc, 0)
            self.assertFalse(out.exists())

    def test_forbidden_marker_inside_an_allowed_field_is_refused(self):
        leaking = dict(MODEL, name='Bearer token in display name')
        with tempfile.TemporaryDirectory(prefix="pi-trim-test-") as tmp:
            rc, out, err = _trim(_response([leaking]), Path(tmp))
            self.assertNotEqual(rc, 0)
            self.assertIn("forbidden", err)
            self.assertFalse(out.exists())


class TestLiveSelfTests(unittest.TestCase):
    def _self_test(self, script: str) -> None:
        proc = subprocess.run(
            [sys.executable, "-I", str(LIVE / script), "--self-test"],
            capture_output=True, text=True, timeout=300, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_pi_mock_provider_self_test_passes(self):
        self._self_test("pi_mock_provider.py")

    def test_check_pi_live_self_test_passes(self):
        self._self_test("check_pi_live.py")


if __name__ == "__main__":
    unittest.main()
