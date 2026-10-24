"""Synthetic-fixture tests for Cursor quota normalization and state."""

import json
import pathlib
import tempfile
import time
import unittest
from typing import cast
from unittest import mock

from tests.cursor_fakes import FakeDashboard, load_dashboard_fixture
from tools.cursor_quota import (
    FRESH_TTL_S,
    NEGATIVE_TTL_S,
    WEEK_MS,
    FetchContext,
    QuotaResult,
    core_needs_refresh,
    core_normalize,
    core_quota_state,
    core_synthetic_cache,
    probe_access_token,
    probe_auth_path,
    probe_build_opener,
    probe_dashboard_call,
    probe_fetch_all,
    probe_fetch_quota,
    util_number,
    util_validate_endpoint,
)


class TestCursorQuota(unittest.TestCase):
    def _auth_env(self, directory: str) -> tuple[dict[str, str], str]:
        home = pathlib.Path(directory) / "home"
        config = pathlib.Path(directory) / "config"
        auth = config / "cursor" / "auth.json"
        auth.parent.mkdir(parents=True)
        token = "synthetic-" + "cursor-" + "token"
        auth.write_text(json.dumps({"accessToken": token}), encoding="utf-8")
        return {"HOME": str(home), "XDG_CONFIG_HOME": str(config)}, token

    def test_auth_to_concurrent_transport_and_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            env, token = self._auth_env(directory)
            self.assertEqual(probe_access_token(env), (token, None))
            expected_parts = (
                load_dashboard_fixture("usage_pro"),
                load_dashboard_fixture("hard_limit_fixed"),
                load_dashboard_fixture("plan_info_monthly"),
            )
            expected = core_normalize(*expected_parts)
            with FakeDashboard() as dashboard:
                dashboard.script("GetCurrentPeriodUsage", body=expected_parts[0])
                dashboard.script("GetHardLimit", body=expected_parts[1])
                dashboard.script("GetPlanInfo", body=expected_parts[2])
                fetched = probe_fetch_all(dashboard.url, token, probe_build_opener(), 2.0)
                self.assertEqual(fetched, (*expected_parts, None))
                self.assertEqual(len(dashboard.requests), 3)
                self.assertTrue(all(
                    request["method"] == "POST"
                    and request["authorization"] == "Bearer " + token
                    for request in dashboard.requests
                ))
            env["CURSOR_API_ENDPOINT"] = "https://api2.cursor.sh"
            def fetch(base, fetched_token, opener, timeout_s):
                self.assertEqual(base, "https://api2.cursor.sh")
                self.assertEqual(fetched_token, token)
                return fetched
            normalized, error, _diagnostic = probe_fetch_quota(env, fetch=fetch)
            self.assertIsNone(error)
            self.assertEqual(normalized, expected)

    def test_dummy_token_never_appears_in_outputs_or_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            env, token = self._auth_env(directory)
            env["CURSOR_API_ENDPOINT"] = "http://api2.cursor.sh"
            with mock.patch(
                "tools.cursor_quota.probe_access_token", return_value=(token, None)
            ) as reader:
                capture = __import__("contextlib").redirect_stderr
                import io
                stderr = io.StringIO()
                with capture(stderr):
                    data, error, diagnostic = probe_fetch_quota(env)
            reader.assert_not_called()
            combined = repr((data, error, diagnostic, stderr.getvalue()))
            self.assertNotIn(token, combined)
            state = core_quota_state({"last_error_kind": "auth_missing"}, 10)
            self.assertEqual(state.state, "auth_missing")

    def test_endpoint_validation_and_rejection_precedes_auth(self):
        accepted = ("https://api2.cursor.sh", "https://cursor.sh", "https://API2.Cursor.sh/")
        rejected = (
            "http://api2.cursor.sh", "https://cursor.sh.evil.com", "https://xcursor.sh",
            "https://user:pw@api2.cursor.sh", "https://api2.cursor.sh:8443",
            "https://api2.cursor.sh/path", "ftp://api2.cursor.sh", "",
        )
        for endpoint in accepted:
            with self.subTest(endpoint=endpoint):
                self.assertIsNotNone(util_validate_endpoint(endpoint))
        for endpoint in rejected:
            with self.subTest(endpoint=endpoint):
                self.assertIsNone(util_validate_endpoint(endpoint))
        with mock.patch("tools.cursor_quota.probe_access_token") as reader:
            data, error, _ = probe_fetch_quota({"CURSOR_API_ENDPOINT": "http://api2.cursor.sh"})
        self.assertIsNone(data)
        self.assertEqual(error, "network_error")
        reader.assert_not_called()

    def test_auth_paths_and_token_error_kinds(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory) / "home"
            xdg = pathlib.Path(directory) / "xdg"
            env = {"HOME": str(home), "XDG_CONFIG_HOME": str(xdg),
                   "CURSOR_CONFIG_DIR": str(pathlib.Path(directory) / "other")}
            self.assertEqual(probe_auth_path(env, "linux"), str(xdg / "cursor" / "auth.json"))
            self.assertEqual(probe_auth_path({"HOME": str(home)}, "linux"),
                             str(home / ".config" / "cursor" / "auth.json"))
            self.assertEqual(probe_auth_path(env, "darwin"), str(home / ".cursor" / "auth.json"))
            self.assertEqual(probe_access_token(env), (None, "auth_missing"))
            auth = xdg / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            for content in ('{}', '{"apiKey":"ignored"}', '', '{'):
                auth.write_text(content, encoding="utf-8")
                expected = "network_error" if content in ("", "{") else "auth_unsupported"
                self.assertEqual(probe_access_token(env), (None, expected))
            auth.write_text('{"accessToken": 42}', encoding="utf-8")
            self.assertEqual(probe_access_token(env), (None, "auth_unsupported"))

    def test_redirect_refused_before_second_server_receives_request(self):
        with FakeDashboard() as destination:
            destination.script("GetCurrentPeriodUsage", body={})
            with FakeDashboard() as source:
                source.script("GetCurrentPeriodUsage", status=302, body={},
                              location=destination.url + "/redirected")
                result = probe_dashboard_call(
                    FetchContext(source.url, "synthetic", probe_build_opener(),
                                 time.monotonic() + 2, 2),
                    "GetCurrentPeriodUsage")
                self.assertEqual(result[1], "network_error")
                self.assertEqual(len(source.requests), 1)
                self.assertEqual(destination.requests, [])

    def test_required_call_failures_and_optional_call_degradation(self):
        responses = (
            load_dashboard_fixture("usage_pro"),
            load_dashboard_fixture("hard_limit_fixed"),
            load_dashboard_fixture("plan_info_monthly"),
        )
        for status, expected in ((401, "auth_expired"), (403, "auth_expired"),
                                 (500, "network_error")):
            with self.subTest(status=status), FakeDashboard() as dashboard:
                dashboard.script("GetCurrentPeriodUsage", status=status)
                result = self._fetch_scripted(dashboard, responses)
                self.assertEqual(result.error_kind, expected)
        without_individual = load_dashboard_fixture("usage_team")
        with FakeDashboard() as dashboard:
            dashboard.script("GetCurrentPeriodUsage", body=without_individual)
            dashboard.script("GetHardLimit", status=500)
            dashboard.script("GetPlanInfo", body=responses[2])
            result = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 2)
            self.assertIsNone(result.error_kind)
            normalized = core_normalize(result.usage, result.hard_limit, result.plan_info)
            self.assertEqual(normalized["od_kind"], "unavailable")
        with FakeDashboard() as dashboard:
            dashboard.script("GetCurrentPeriodUsage", body=responses[0])
            dashboard.script("GetHardLimit", body=responses[1])
            dashboard.script("GetPlanInfo", status=500)
            result = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 2)
            normalized = core_normalize(result.usage, result.hard_limit, result.plan_info)
            self.assertEqual(core_quota_state(
                {"data": normalized, "data_fetched_at": 1}, 2).included_window,
                (1791590400000, 1794268800000))

    @staticmethod
    def _fetch_scripted(dashboard, responses):
        for method, response in zip(("GetHardLimit", "GetPlanInfo"), responses[1:], strict=True):
            dashboard.script(method, body=response)
        return probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 2)

    def test_malformed_json_and_total_deadline(self):
        with FakeDashboard() as dashboard:
            dashboard.script("GetCurrentPeriodUsage", body="not an object")
            result = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 2)
            self.assertEqual(result.error_kind, "network_error")
        with FakeDashboard() as dashboard:
            for method in ("GetCurrentPeriodUsage", "GetHardLimit", "GetPlanInfo"):
                dashboard.script(method, body={"slow": True}, delay_s=0.4)
            started = time.monotonic()
            result = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 0.1)
            elapsed = time.monotonic() - started
            self.assertEqual(result.error_kind, "network_error")
            self.assertLess(elapsed, 0.3)

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
