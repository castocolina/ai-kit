"""Phase 22 evidence gates and owner-tool self-tests."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE = ROOT / ".planning" / "phases" / "22-pi-live-validation"
LIVE = PHASE / "live"
# Commit cleanliness, tmp/ cleanup and full make gates are execution-time-only checks.
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
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return proc.returncode, out, proc.stderr


def _spike_ok(text: str) -> bool:
    headings = (
        "## L0 (static)",
        "## L1 (fake ExtensionAPI)",
        "## L2 (localhost mock)",
        "## L3 (owner)",
        "## Findings (R7)",
        "## Verdict",
    )
    if not all(h in text.splitlines() for h in headings):
        return False
    if any(not re.search(rf"^\| {letter} ", text, re.M) for letter in "ABCD"):
        return False
    if len(re.findall(r"^\| L3[abc] .*not run \(owner\)", text, re.M)) != 3:
        return False
    rows = {}
    for line in text.splitlines():
        match = re.match(r"^\| ([ABCD]) \|", line)
        if match:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            rows[match.group(1)] = cells
    if any(len(rows.get(letter, [])) != 7 for letter in "ABCD"):
        return False
    verdicts = re.findall(r"^verdict: .*$", text, re.M)
    if len(verdicts) != 1 or "no fix needed" not in text:
        return False
    verdict = verdicts[0]
    passed = (
        rows["A"][5] == "steered-id"
        and all(rows[k][5] == "selected" for k in "BC")
        and all(rows[k][6] == "pass" for k in "ABC")
    )
    inconclusive = all(rows[k][5] in ("", "empty") for k in "ABCD") and verdict.startswith(
        "verdict: inconclusive ("
    )
    return (verdict == "verdict: session-steer (static + mock evidence)") == passed and (
        passed or inconclusive or verdict.startswith("verdict: blocked (")
    )


def _smoke_ok(text: str) -> bool:
    headings = (
        "## Session",
        "## Headless harness run (agent)",
        "## Real-home guard",
        "## Interactive run (owner)",
        "## R4 and R5 status",
        "## Fixes (R7)",
    )
    if not all(h in text.splitlines() for h in headings):
        return False
    verdicts = re.findall(r"^headless verdict: .*$", text, re.M)
    return (
        len(verdicts) == 1
        and re.fullmatch(
            r"headless verdict: (green \(attempt [0-9]+: smoke exit=0, matrix ran: [0-9]+ checks, "
            r"5 hook probes, protected set unchanged, real-home snapshot ok\)|"
            r"red \(attempt [0-9]+: .+\))",
            verdicts[0],
        )
        is not None
        and "not run (owner)" in text.split("## Interactive run (owner)", 1)[1].split("\n## ", 1)[0]
        and "No other fix was needed" in text
    )


def _interactive_ok(text: str) -> bool:
    headings = (
        "## Before you start",
        "## Steps",
        "## Results",
        "## Send back",
        "## Orchestrator close-out",
    )
    required = ("C1", "S1", "S2", "S3", "S4", "S5", "D9", "L3a", "L3b", "L3c")
    if not all(h in text.splitlines() for h in headings):
        return False
    if any(
        not re.search(rf"^### {row} \((REQUIRED|OPTIONAL)\) — ", text, re.M) for row in required
    ):
        return False
    if any(
        fragment not in text
        for fragment in (
            "trim_pi_capture.py",
            "pi --skill skills/ai-kit-gsd-curated-config",
            "--host-rewrite '<home>/.pi/agent/settings.json'",
            "gsd-plan-phase 22 --gaps",
            "check_pi_live.py",
        )
    ):
        return False
    return re.search(r"(^|[ `(\"])/(home|var/home|Users)/", text, re.M) is None


def _judge_gate(phase: Path, judge_text: str, *, check_digest: bool = True) -> bool:
    """Apply the phase plan's per-judge baseline and quality rule."""
    if (
        check_digest
        and "digests ok"
        not in subprocess.run(
            [
                sys.executable,
                str(ROOT / "tests" / "gsd_curated_eval.py"),
                "digest",
                "--check",
                str(phase / "22-SKILL-JUDGE.md"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    ):
        return False
    if len(re.findall(r"^## Verdict: ", judge_text, re.M)) != 1 or not re.search(
        r"FIX_ITERATIONS_USED: [0-2] of 2", judge_text
    ):
        return False
    verdict_match = re.search(r"^## Verdict: (.*)$", judge_text, re.M)
    if verdict_match is None:
        return False
    verdict = verdict_match.group(1)
    if verdict != "PASS":
        return verdict.startswith(
            "UNRESOLVED (user decision required; jev advises "
        ) or verdict.startswith("BLOCKED: ")
    rows = {}
    for line in judge_text.splitlines():
        if line.startswith("| ") and "post-change" in line and "superseded" not in line:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 7:
                rows[cells[0]] = cells
    for judge in ("native Opus (clean context)", "opencode router-env/my-plan-review"):
        matching = [cells for key, cells in rows.items() if key == judge]
        if len(matching) != 1 or matching[0][5] != "pass":
            return False
        report_path = phase / matching[0][6]
        baseline_matches = re.findall(
            r"^CURRENT ([0-9]+)/120",
            (
                phase
                / "skill-judge"
                / (
                    "pre-native-opus.md"
                    if judge.startswith("native")
                    else "pre-opencode-plan-review.md"
                )
            ).read_text(encoding="utf-8"),
            re.M,
        )
        report = report_path.read_text(encoding="utf-8")
        current = re.findall(r"^CURRENT ([0-9]+)/120", report, re.M)
        critical = re.findall(r"^CRITICAL ([0-9]+)", report, re.M)
        important = re.findall(r"^IMPORTANT ([0-9]+)", report, re.M)
        if not baseline_matches or not current or not critical or not important:
            return False
        score, baseline = int(current[-1]), int(baseline_matches[-1])
        if score < baseline or not (
            (int(critical[-1]) == 0 and int(important[-1]) == 0) or score >= 96
        ):
            return False
    return True


class TestPhaseEvidenceGates(unittest.TestCase):
    def _nonvacuous(self, checker, evidence: str, replacement: tuple[str, str]) -> None:
        with tempfile.TemporaryDirectory(prefix="pi-evidence-test-") as tmp:
            copy = Path(tmp) / "evidence.md"
            tampered = evidence.replace(replacement[0], replacement[1])
            self.assertNotEqual(tampered, evidence)
            copy.write_text(tampered, encoding="utf-8")
            self.assertFalse(checker(copy, tampered))

    def test_spike_evidence_verdict_consistency_and_secret_scan(self):
        path = PHASE / "22-SPIKE-PI-AGENTS.md"
        text = path.read_text(encoding="utf-8")
        self.assertTrue(_spike_ok(text))
        self.assertNotIn(os.path.expanduser("~"), text)
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tests/gsd_curated_eval.py"), "secret-scan", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn(os.path.expanduser("~"), text)
        self._nonvacuous(
            lambda _p, t: _spike_ok(t),
            text,
            ("verdict: session-steer (static + mock evidence)", "verdict: blocked (tampered)"),
        )

    def test_smoke_evidence_verdict_secret_scan_and_no_home_path(self):
        path = PHASE / "22-SMOKE-PI.md"
        text = path.read_text(encoding="utf-8")
        self.assertTrue(_smoke_ok(text))
        self.assertEqual(
            subprocess.run(
                [sys.executable, str(ROOT / "tests/gsd_curated_eval.py"), "secret-scan", str(path)],
                cwd=ROOT,
                capture_output=True,
                check=False,
            ).returncode,
            0,
        )
        self.assertNotRegex(text, r"(^|[ `(\"])/(home|var/home|Users)/")
        home = "/home/synthetic-user"
        self._nonvacuous(
            lambda _p, t: (
                _smoke_ok(t) and re.search(r"(^|[ `(\"])/(home|var/home|Users)/", t, re.M) is None
            ),
            text,
            ("## Session", "## Session\n" + home),
        )

    def test_interactive_runbook_structure_and_portability(self):
        path = PHASE / "22-INTERACTIVE-PI.md"
        text = path.read_text(encoding="utf-8")
        self.assertTrue(_interactive_ok(text))
        self._nonvacuous(
            lambda _p, t: _interactive_ok(t),
            text,
            ("## Before you start", "## Before you start\n/home/synthetic-user/path"),
        )

    def test_skill_judge_gate_uses_non_superseded_rows_and_digest_check(self):
        path = PHASE / "22-SKILL-JUDGE.md"
        text = path.read_text(encoding="utf-8")
        self.assertTrue(_judge_gate(PHASE, text))
        # Skip the committed digest check for this synthetic score-regression copy.
        with tempfile.TemporaryDirectory(prefix="pi-judge-test-") as tmp:
            copy_phase = Path(tmp)
            (copy_phase / "skill-judge").mkdir()
            for name in (
                "pre-native-opus.md",
                "pre-opencode-plan-review.md",
                "post-native-opus-r1.md",
                "post-opencode-plan-review-r1.md",
            ):
                (copy_phase / "skill-judge" / name).write_text(
                    (PHASE / "skill-judge" / name).read_text(encoding="utf-8"), encoding="utf-8"
                )
            (copy_phase / "22-SKILL-JUDGE.md").write_text(text, encoding="utf-8")
            tampered = text.replace(
                "106/120 | 0/1 | pass | skill-judge/post-native-opus-r1.md",
                "90/120 | 0/1 | pass | skill-judge/post-native-opus-r1.md",
            )
            (copy_phase / "22-SKILL-JUDGE.md").write_text(tampered, encoding="utf-8")
            report = copy_phase / "skill-judge/post-native-opus-r1.md"
            report.write_text(
                report.read_text(encoding="utf-8").replace("CURRENT 106/120", "CURRENT 90/120"),
                encoding="utf-8",
            )
            self.assertFalse(_judge_gate(copy_phase, tampered, check_digest=False))


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
        leaking = dict(MODEL, name="Bearer token in display name")
        with tempfile.TemporaryDirectory(prefix="pi-trim-test-") as tmp:
            rc, out, err = _trim(_response([leaking]), Path(tmp))
            self.assertNotEqual(rc, 0)
            self.assertIn("forbidden", err)
            self.assertFalse(out.exists())


class TestLiveSelfTests(unittest.TestCase):
    def _self_test(self, script: str) -> None:
        proc = subprocess.run(
            [sys.executable, "-I", str(LIVE / script), "--self-test"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_pi_mock_provider_self_test_passes(self):
        self._self_test("pi_mock_provider.py")

    def test_check_pi_live_self_test_passes(self):
        self._self_test("check_pi_live.py")


if __name__ == "__main__":
    unittest.main()
