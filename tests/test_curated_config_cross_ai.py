"""XAI-01/XAI-02 selection tests: execution targets, D-39 defaults, value helpers."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)

from tests.test_curated_config_recommend import cand, entry_map, make_inventory, run_recommend


def exec_cand(model: str, runtime: str, execution: float = 80.0, price: float = 2.0, **fields):
    scores = {"execution": execution, "planning": 1.0, "general": 1.0, "review": 1.0}
    return cand(
        model,
        runtime=runtime,
        is_host=False,
        score_axes=1,
        purpose_scores=scores,
        price=price,
        **fields,
    )


class TestExecTargetsEndToEnd(unittest.TestCase):
    def test_pi_host_skips_itself(self):
        inv = make_inventory(
            host="pi",
            candidates=[
                exec_cand("m-cursor", "cursor-agent"),
                exec_cand("m-opencode", "opencode"),
                exec_cand("m-pi", "pi"),
            ],
        )
        inv["installed_runtimes"] = ["cursor-agent", "opencode", "pi"]
        code, plan, _, err = run_recommend(
            inv, "--profile", "adaptive", "--rigor", "standard", "--cross-ai-exec", "y"
        )
        self.assertEqual((code, err), (0, ""))
        assert plan is not None
        self.assertEqual(plan["artifacts"][0]["config"]["prefer"], ["cursor", "opencode"])

    def test_claude_without_pi_falls_to_cursor(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("m-cursor", "cursor-agent"),
                exec_cand("m-opencode", "opencode"),
            ],
        )
        inv["installed_runtimes"] = ["cursor-agent", "opencode"]
        code, plan, _, err = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
        self.assertEqual((code, err), (0, ""))
        assert plan is not None
        self.assertEqual(plan["artifacts"][0]["config"]["prefer"][0], "cursor")
        entry = entry_map(plan)["workflow.cross_ai_execution"]
        self.assertTrue(entry["value"])
        self.assertTrue(plan["cross_ai"]["exec"]["defaulted"])


if __name__ == "__main__":
    unittest.main()
