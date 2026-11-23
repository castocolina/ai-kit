"""36 D-04, D-05, D-06, D-16, D-20, D-23 / SPEC R3, R12 b, R13:
The wizard JSON example in config-file.md renders through the writer unchanged.
"""

import io
import json
import os
import re
import sys
import tomllib
import unittest
from contextlib import redirect_stderr
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import config_io, lane_data_use, lane_settings

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "skills" / "ai-kit-spec-config" / "references" / "config-file.md"
HEADING = "## Example: the JSON the wizard passes to render-toml"
DATE = "2000-01-02"
FENCE = "`" * 3
BLOCK_RX = re.compile(FENCE + "json\n(.*?)\n" + FENCE, re.S)


def _example_block() -> str:
    text = DOC.read_text(encoding="utf-8").split(HEADING, 1)[1]
    match = BLOCK_RX.search(text)
    assert match is not None
    return match.group(1)


def _example_config() -> dict:
    return json.loads(_example_block().replace("YYYY-MM-DD", DATE))


def _render() -> tuple[str, str]:
    err = io.StringIO()
    with redirect_stderr(err):
        text = config_io.cfg_render_lanes(_example_config(), "")
    return text, err.getvalue()


class TestWizardLaneJson(unittest.TestCase):
    def test_example_renders_without_any_message(self):
        text, err = _render()
        self.assertTrue(text)
        self.assertEqual(err, "")

    def test_every_lane_key_survives_in_its_role(self):
        config = _example_config()
        parsed = tomllib.loads(_render()[0])["lanes"]
        for role in ("review", "execute"):
            expected = [lane for lane in config["lanes"] if lane["purpose"] == role]
            self.assertEqual(parsed[role], expected)

    def test_orders_are_per_role(self):
        policy = tomllib.loads(_render()[0])["lanes"]["policy"]
        self.assertEqual(policy, _example_config()["policy"])
        self.assertNotIn("ladder", policy)

    def test_example_holds_every_new_lane_key(self):
        lanes = _example_config()["lanes"]
        keys = set().union(*(lane.keys() for lane in lanes))
        self.assertTrue({"effort", "effort_source", "escalate_runtime", "escalate_model",
                         "usage_limited", "usage_limit_note", "pool",
                         *lane_data_use.DATA_USE_KEYS} <= keys)
        for lane in lanes:
            for flag in ("escalate_runtime", "escalate_model", "usage_limited"):
                if flag in lane:
                    self.assertIs(lane[flag], True)

    def test_example_has_no_date_and_no_alias(self):
        block = _example_block()
        self.assertNotRegex(block, r"\d{4}-\d{2}-\d{2}")
        self.assertNotIn("router-env/", block)

    def test_example_flags_have_targets(self):
        config = _example_config()
        for role in ("review", "execute"):
            by_key = {lane["key"]: lane for lane in config["lanes"] if lane["purpose"] == role}
            ordered = [by_key[key] for key in config["policy"][role]["ladder"]]
            for lane in ordered:
                for kind in ("runtime", "model"):
                    if lane.get("escalate_" + kind):
                        target = lane_settings.escalation_target(ordered, lane["key"], kind)
                        self.assertIsNotNone(target)
                        if lane["key"] == "review-main":
                            expected = "review-second" if kind == "runtime" else "review-third"
                            self.assertEqual(target, expected)


if __name__ == "__main__":
    unittest.main()
