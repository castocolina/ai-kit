#!/usr/bin/env python3
"""Phase 22 close-out checker, run by the owner and the orchestrator; it reads files only."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

REQUIRED = ("C1", "S1", "S2", "S3", "S4", "S5", "D9")
OPTIONAL = ("L3a", "L3b", "L3c")
R4_R5 = ("S1", "S2", "S3", "S4", "S5")
SKILL_MD = Path("skills/ai-kit-gsd-curated-config/SKILL.md")
DETECTION_PY = Path("skills/ai-kit-spec-review/ai_kit_spec/detection.py")
REAL_FIXTURE = Path("tests/fixtures/pi_rpc_get_available_models_real.json")


def results(kit_text: str) -> dict[str, str]:
    """Read result cells from rows in the Results table."""
    found: dict[str, str] = {}
    for line in kit_text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] in (*REQUIRED, *OPTIONAL):
            found[cells[0]] = cells[-1]
    return found


def check(kit_path: str | Path, root: Path) -> list[str]:
    """Return close-out problems for a runbook and its project tree."""
    try:
        kit_text = Path(kit_path).read_text(encoding="utf-8")
    except OSError as exc:
        return [f"kit cannot be read: {exc}"]
    row_results = results(kit_text)
    problems = []
    for row_id in REQUIRED:
        result = row_results.get(row_id, "missing")
        if result != "pass":
            problems.append(f"{row_id}: {result}")
    for row_id in OPTIONAL:
        result = row_results.get(row_id, "missing")
        if not (
            result in ("pass", "not run (owner declined)")
            or result.startswith("inconclusive (")
            or result.startswith("fail (")
        ):
            problems.append(f"{row_id}: unresolved ({result})")

    try:
        skill_text = (root / SKILL_MD).read_text(encoding="utf-8")
    except OSError as exc:
        return [*problems, f"SKILL.md cannot be read: {exc}"]
    pi_row = next((line for line in skill_text.splitlines() if line.startswith("| pi hosts |")), "")
    lifted = bool(pi_row) and "not live-validated" not in pi_row
    if lifted and any(row_results.get(row_id) != "pass" for row_id in R4_R5):
        problems.append("pi label lifted without R4/R5 evidence (S1-S5 must all pass)")
    if all(row_results.get(row_id) == "pass" for row_id in REQUIRED) and not lifted:
        problems.append("close-out pending: lift the pi label (SKILL.md row, README row, test pins)")
    if not pi_row or "session-steer" not in pi_row:
        problems.append("pi row lost the verdict")
    if any(row_results.get(row_id, "").startswith("fail (") for row_id in OPTIONAL):
        problems.append("L3 refuted the steer: a decimal phase is required (SPEC R7), not a close-out edit")
    elif any(row_results.get(row_id) == "pass" for row_id in ("L3a", "L3c")):
        # L3b runs without the override, so a pass there is a baseline, not steering evidence.
        if "session-steer (live L3" not in pi_row:
            problems.append("close-out pending: update the verdict to session-steer (live L3 ...)")
    elif "session-steer (static + mock evidence)" not in pi_row:
        problems.append("pi row must retain session-steer (static + mock evidence)")

    if row_results.get("D9") == "pass":
        try:
            detection_text = (root / DETECTION_PY).read_text(encoding="utf-8")
        except OSError:
            detection_text = ""
        if "live-verified (Phase 22)" not in detection_text:
            problems.append("close-out pending: _LABEL_PI")
    if row_results.get("C1") == "pass":
        try:
            fixture_text = (root / REAL_FIXTURE).read_text(encoding="utf-8")
        except OSError:
            fixture_text = ""
        if '"_capture"' not in fixture_text:
            problems.append("close-out pending: commit the trimmed capture")
    return problems


def _self_test() -> list[str]:
    """Exercise the pending state, happy path, and close-out rejection edges."""
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        kit = root / "kit.md"
        skill_path = root / SKILL_MD
        detection_path = root / DETECTION_PY
        fixture_path = root / REAL_FIXTURE
        skill_path.parent.mkdir(parents=True)
        detection_path.parent.mkdir(parents=True)
        fixture_path.parent.mkdir(parents=True)
        base_rows = {row_id: "pass" for row_id in REQUIRED}
        base_rows.update({row_id: "not run (owner declined)" for row_id in OPTIONAL})

        def write_kit(values: dict[str, str]) -> None:
            rows = "\n".join(f"| {key} | step | - | - | - | {value} |" for key, value in values.items())
            kit.write_text(f"## Results\n{rows}\n", encoding="utf-8")

        def write_state(lifted: bool, verdict: str = "session-steer (static + mock evidence)") -> None:
            label = "validated" if lifted else "**not live-validated**"
            skill_path.write_text(f"| pi hosts | {label} | {verdict} |\n", encoding="utf-8")
            detection_path.write_text("live-verified (Phase 22)\n", encoding="utf-8")
            fixture_path.write_text('{"_capture": {}}\n', encoding="utf-8")

        cases: list[tuple[str, dict[str, str], bool, str, int, str | None]] = []
        pending = {row_id: "pending (owner)" for row_id in (*REQUIRED, *OPTIONAL)}
        cases.append(("staged kit", pending, False, "session-steer (static + mock evidence)", 1, "C1: pending (owner)"))
        cases.append(("all-pass close-out", base_rows.copy(), True, "session-steer (static + mock evidence)", 0, None))
        s3_fail = base_rows.copy()
        s3_fail["S3"] = "fail (x)"
        cases.append(("lifted with S3 failing", s3_fail, True, "session-steer (static + mock evidence)", 1, "pi label lifted without R4/R5 evidence"))
        cases.append(("label still on", base_rows.copy(), False, "session-steer (static + mock evidence)", 1, "close-out pending: lift the pi label"))
        l3a = base_rows.copy()
        l3a["L3a"] = "pass"
        cases.append(("L3a pass static verdict", l3a, True, "session-steer (static + mock evidence)", 1, "session-steer (live L3"))
        l3b = base_rows.copy()
        l3b["L3b"] = "fail (served model unchanged)"
        cases.append(("L3b refutation", l3b, True, "session-steer (static + mock evidence)", 1, "decimal phase"))
        l3c = base_rows.copy()
        l3c["L3c"] = "pending (owner)"
        cases.append(("L3c unresolved", l3c, True, "session-steer (static + mock evidence)", 1, "L3c: unresolved"))
        missing_c1 = base_rows.copy()
        del missing_c1["C1"]
        cases.append(("C1 missing", missing_c1, True, "session-steer (static + mock evidence)", 1, "C1: missing"))
        cases.append(("detection label missing", base_rows.copy(), True, "session-steer (static + mock evidence)", 1, "_LABEL_PI"))
        cases.append(("fixture missing", base_rows.copy(), True, "session-steer (static + mock evidence)", 1, "trimmed capture"))
        l3a_live = base_rows.copy()
        l3a_live["L3a"] = "pass"
        cases.append(("L3a live verdict", l3a_live, True, "session-steer (live L3 on provider)", 0, None))

        failures = []
        for name, row_values, lifted, verdict, expected_code, expected_text in cases:
            write_kit(row_values)
            write_state(lifted, verdict)
            if name == "detection label missing":
                detection_path.write_text("source-inspected-only\n", encoding="utf-8")
            if name == "fixture missing":
                fixture_path.unlink()
            actual = check(kit, root)
            actual_code = 0 if not actual else 1
            if actual_code != expected_code or (expected_text and not any(expected_text in item for item in actual)):
                failures.append(f"{name}: expected exit {expected_code} with {expected_text!r}; got {actual!r}")
        return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Phase 22 pi live-validation close-out")
    parser.add_argument("kit", nargs="?", help="interactive pi runbook")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        failures = _self_test()
        if failures:
            for failure in failures:
                print(f"self-test failed: {failure}")
            return 1
        print("self-test ok")
        return 0
    if args.kit is None:
        parser.error("the kit path is required unless --self-test is used")
    failures = check(args.kit, args.root)
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print("pi live checks ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
