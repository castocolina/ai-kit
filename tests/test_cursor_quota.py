"""Synthetic-fixture tests for Cursor quota normalization and state."""

import json
import unittest
from typing import cast

from tests.cursor_fakes import load_dashboard_fixture
from tools.cursor_quota import (
    FRESH_TTL_S,
    NEGATIVE_TTL_S,
    WEEK_MS,
    QuotaResult,
    core_needs_refresh,
    core_normalize,
    core_quota_state,
    core_synthetic_cache,
    util_number,
)


class TestCursorQuota(unittest.TestCase):
    def test_fixture_happy_path_normalizes_and_states(self):
        data = core_normalize(
            load_dashboard_fixture("usage_pro"),
            load_dashboard_fixture("hard_limit_fixed"),
            load_dashboard_fixture("plan_info_monthly"),
        )
        self.assertEqual(data["cycle_start_ms"], 1791590400000)
        self.assertEqual(data["cycle_end_ms"], 1794268800000)
        self.assertEqual(data["included_pct"], 50)
        self.assertEqual(data["api_pct"], 100)
        self.assertEqual(data["od_kind"], "fixed")
        self.assertEqual(data["od_used_usd"], 5.2)
        self.assertEqual(data["od_ceiling_usd"], 5.0)
        self.assertEqual(data["included_period"], "monthly")
        json.dumps(data)
        result = core_quota_state({"data": data, "data_fetched_at": 90}, 100)
        self.assertIsInstance(result, QuotaResult)
        self.assertEqual(result.state, "ok")
        self.assertEqual(result.confidence, "inferred")
        self.assertEqual(result.included_window, (1791590400000, 1794268800000))
        self.assertTrue(all(not isinstance(value, str) or value in {
            "monthly", "weekly", "unspecified", "fixed", "unlimited", "disabled", "unavailable"
        } for value in data.values()))

    def test_numeric_validation(self):
        for value in (True, "abc", float("nan"), float("inf"), -5, None, object()):
            with self.subTest(value=repr(value)):
                self.assertIsNone(util_number(value))

    def test_string_epoch_and_derive_else_hide(self):
        self.assertEqual(
            core_normalize(load_dashboard_fixture("usage_string_ms"),
                           load_dashboard_fixture("hard_limit_fixed"),
                           load_dashboard_fixture("plan_info_monthly")),
            core_normalize(load_dashboard_fixture("usage_pro"),
                           load_dashboard_fixture("hard_limit_fixed"),
                           load_dashboard_fixture("plan_info_monthly")),
        )
        usage = load_dashboard_fixture("usage_missing_percents")
        data = core_normalize(usage, None, None)
        self.assertEqual(data["included_pct"], 50)
        self.assertIsNone(data["api_pct"])
        usage["planUsage"]["limit"] = 0
        self.assertIsNone(core_normalize(usage, None, None)["included_pct"])
        usage["planUsage"].pop("includedSpend")
        self.assertIsNone(core_normalize(usage, None, None)["included_pct"])

    def test_invalid_dashboard_numbers_are_hidden(self):
        for invalid in (True, "abc", float("nan"), float("inf"), -5):
            with self.subTest(invalid=repr(invalid)):
                usage = load_dashboard_fixture("usage_pro")
                usage["planUsage"]["totalPercentUsed"] = invalid
                usage["planUsage"]["includedSpend"] = invalid
                usage["spendLimitUsage"]["individualUsed"] = invalid
                data = core_normalize(usage, None, None)
                self.assertIsNone(data["included_pct"])
                self.assertIsNone(data["od_used_usd"])

    def test_absent_proto_numeric_is_zero(self):
        usage = load_dashboard_fixture("usage_no_plan")
        self.assertEqual(core_normalize(usage, None, None)["od_used_usd"], 0)

    def test_hard_limit_classes_and_team_evidence(self):
        usage = load_dashboard_fixture("usage_team")
        team_without_evidence = core_normalize(usage, None, None)
        self.assertEqual(team_without_evidence["od_kind"], "unavailable")
        self.assertEqual(core_normalize(usage, {}, None)["od_kind"], "unavailable")
        for fixture, expected in (("hard_limit_unlimited", "unlimited"),
                                  ("hard_limit_disabled", "disabled")):
            with self.subTest(fixture=fixture):
                result = core_normalize(usage, load_dashboard_fixture(fixture), None)
                self.assertEqual(result["od_kind"], expected)
        usage["spendLimitUsage"]["individualLimit"] = 1000
        individual = core_normalize(usage, None, None)
        self.assertEqual((individual["od_kind"], individual["od_ceiling_usd"]), ("fixed", 10))
        usage["spendLimitUsage"].pop("individualLimit")
        for pooled_limit, expected in ((2000, "fixed"), (0, "unavailable"), (None, "unavailable")):
            usage["spendLimitUsage"]["pooledLimit"] = pooled_limit
            with self.subTest(pooled_limit=pooled_limit):
                result = core_normalize(usage, load_dashboard_fixture("hard_limit_fixed"), None)
                self.assertEqual(result["od_kind"], expected)
                if expected == "fixed":
                    self.assertEqual(result["od_ceiling_usd"], 20)
                    self.assertEqual(result["od_used_usd"], 5.2)
        usage["spendLimitUsage"]["individualLimit"] = 0
        personal = load_dashboard_fixture("usage_pro")
        personal["spendLimitUsage"]["individualLimit"] = 0
        result = core_normalize(personal, load_dashboard_fixture("hard_limit_unlimited"), None)
        self.assertEqual(result["od_kind"], "disabled")

    def test_windows_and_billing_cycle_fallback(self):
        usage = load_dashboard_fixture("usage_pro")
        weekly = core_normalize(usage, None, load_dashboard_fixture("plan_info_weekly"))
        reset = cast(int, weekly["included_resets_at_ms"])
        result = core_quota_state({"data": weekly, "data_fetched_at": 1}, 2)
        self.assertEqual(result.included_window, (reset - WEEK_MS, reset))
        monthly = core_normalize(usage, None, None)
        monthly_result = core_quota_state({"data": monthly, "data_fetched_at": 1}, 2)
        self.assertEqual(monthly_result.included_window, (1791590400000, 1794268800000))
        weekly_no_reset = load_dashboard_fixture("plan_info_weekly")
        weekly_no_reset["planInfo"].pop("includedUsageResetsAt")
        self.assertIsNone(core_quota_state({"data": core_normalize(usage, None, weekly_no_reset),
                                            "data_fetched_at": 1}, 2).included_window)
        fallback = load_dashboard_fixture("usage_pro")
        fallback.pop("billingCycleEnd")
        fallback_result = core_normalize(
            fallback, None, load_dashboard_fixture("plan_info_monthly"))
        self.assertEqual(fallback_result["cycle_end_ms"], 1794268800000)
        conflict = load_dashboard_fixture("usage_pro")
        conflict["billingCycleEnd"] = 123
        conflict_result = core_normalize(
            conflict, None, load_dashboard_fixture("plan_info_monthly"))
        self.assertEqual(conflict_result["cycle_end_ms"], 123)

    def test_states_and_refresh_edges(self):
        data = core_normalize(load_dashboard_fixture("usage_pro"), None, None)
        for age, expected in ((FRESH_TTL_S, "ok"), (FRESH_TTL_S + 0.5, "stale")):
            with self.subTest(age=age):
                cache = {"data": data, "data_fetched_at": 100}
                self.assertEqual(core_quota_state(cache, 100 + age).state, expected)
        cycle_end = cast(float, data["cycle_end_ms"])
        self.assertEqual(core_quota_state({"data": data, "data_fetched_at": 100},
                                          cycle_end / 1000).state, "cycle_ended")
        auth = {"data": data, "data_fetched_at": 100, "last_attempt_at": 101,
                "last_error_kind": "auth_expired"}
        self.assertEqual(core_quota_state(auth, 102).state, "auth_expired")
        auth["last_error_kind"] = "auth_unsupported"
        self.assertEqual(core_quota_state(auth, 102).state, "auth_unsupported")
        network = {"data": data, "data_fetched_at": 100, "last_attempt_at": 101,
                   "last_error_kind": "network_error"}
        self.assertEqual(core_quota_state(network, 102).state, "stale")
        no_data_error = {"last_error_kind": "network_error"}
        self.assertEqual(core_quota_state(no_data_error, 102).state, "network_error")
        self.assertEqual(core_quota_state({}, 102).state, "absent")
        self.assertTrue(core_needs_refresh({}, 102))
        self.assertFalse(core_needs_refresh({"data_fetched_at": 100}, 100))
        self.assertFalse(core_needs_refresh({"data_fetched_at": 1, "last_attempt_at": 100}, 400))
        self.assertTrue(core_needs_refresh({"data_fetched_at": 1, "last_attempt_at": 100},
                                           100 + NEGATIVE_TTL_S + 1))
        synthetic = core_synthetic_cache(500)
        self.assertEqual(core_quota_state(synthetic, 500).state, "ok")


if __name__ == "__main__":
    unittest.main()
