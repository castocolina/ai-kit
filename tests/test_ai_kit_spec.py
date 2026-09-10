import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

# Bare module imports -- test classes in this file call module-qualified names like
# `detection.detect_tool_availability(...)`, `commands.build_execute_command(...)`, which need
# the module itself in scope, separately from the individual-function imports below. Only the
# modules actually referenced qualified (`module.attr(...)`) somewhere in this file belong here --
# a module whose members are ALL reached only via the individually-named imports below (and thus
# only via the `rs.<name>` shim) has no reason to be re-imported bare too.
from ai_kit_spec import (
    cli,
    commands,
    config_io,
    detection,
    dispatch,
    dispatch_guidance,
    execute_dispatch,
    execute_selection,
    local_secrets,
    model_catalog,
    model_heuristics,
    model_matcher,
    model_ranker,
    model_sources,
    quota,
    reviewer_dispatch,
    tooling_guidance,
)

# Every name imported below is used only reflectively (see the `globals()[_name]` loop building
# `rs` further down) -- ruff's static analysis cannot see that use and flags all of them F401;
# `noqa: F401` on each is therefore intentional, not an oversight.
from ai_kit_spec.cache import (  # noqa: F401
    cache_base,
    cache_is_stale,
    cache_read_json,
    cache_write_json,
)
from ai_kit_spec.cli import main  # noqa: F401
from ai_kit_spec.commands import (  # noqa: F401
    ResolvedReviewer,
    build_cursor_agent_model_id,
    build_reviewer_command,
    build_reviewer_model_id,
    render_reviewer_command,
)
from ai_kit_spec.config_io import (  # noqa: F401
    cfg_global_path,
    cfg_load_toml,
    cfg_local_path,
    cfg_merge_reviewers,
    cfg_render_toml,
    cfg_resolve,
    cfg_write_toml,
    tomllib,
)
from ai_kit_spec.detection import (  # noqa: F401
    KNOWN_CLIS,
    build_runtimes_snapshot,
    cache_runtimes_path,
    detect_cursor_agent_models,
    detect_installed_clis,
    detect_opencode_models,
    group_models_by_family,
)
from ai_kit_spec.quota import (  # noqa: F401
    NO_CONFIG_FALLBACK,
    cache_quota_path,
    probe_reviewer_quota,
    refresh_quota_cache,
    resolve_ladder_pick,
    resolve_reviewers,
)
from ai_kit_spec.review_reports import (  # noqa: F401
    merge_findings,
    parse_findings,
    render_merged_report,
    report_declares_issues,
    report_has_status,
)
from ai_kit_spec.vendor import infer_vendor_from_model  # noqa: F401


# Back-compat shim so every existing `rs.<name>` call in this file keeps working verbatim --
# avoids touching 146 existing test bodies for a pure module-boundary change. Explicit name
# list, not dir()-based reflection: a missing/misspelled export raises KeyError here (from
# globals()[_name]), at import time, instead of silently disappearing from `rs`.
class _RS:
    pass


rs = _RS()
for _name in (
    "cache_base", "cache_read_json", "cache_write_json", "cache_is_stale",
    "cache_runtimes_path", "detect_installed_clis", "detect_opencode_models",
    "detect_cursor_agent_models", "group_models_by_family", "build_runtimes_snapshot",
    "KNOWN_CLIS", "infer_vendor_from_model", "ResolvedReviewer", "resolve_ladder_pick",
    "resolve_reviewers", "cache_quota_path", "probe_reviewer_quota", "refresh_quota_cache",
    "NO_CONFIG_FALLBACK", "build_reviewer_command", "build_cursor_agent_model_id",
    "build_reviewer_model_id", "render_reviewer_command", "cfg_local_path", "cfg_global_path",
    "cfg_load_toml", "cfg_merge_reviewers", "cfg_resolve", "cfg_render_toml", "cfg_write_toml",
    "report_has_status", "report_declares_issues", "parse_findings", "merge_findings",
    "render_merged_report", "main",
    "tomllib", "os",
):
    setattr(rs, _name, globals()[_name])


class TestConfigPaths(unittest.TestCase):
    def test_local_path_under_cwd_aikit(self):
        self.assertEqual(rs.cfg_local_path("/repo"), "/repo/.aikit/review-spec.toml")

    def test_global_path_uses_xdg_config_home(self):
        env = {"XDG_CONFIG_HOME": "/x/config"}
        self.assertEqual(rs.cfg_global_path(env), "/x/config/ai-kit/review-spec.toml")

    def test_global_path_falls_back_to_home_dot_config(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(rs.cfg_global_path(env), "/home/u/.config/ai-kit/review-spec.toml")


class TestLoadToml(unittest.TestCase):
    def test_missing_file_returns_empty_dict(self):
        self.assertEqual(rs.cfg_load_toml("/no/such/file.toml"), {})

    def test_malformed_toml_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.toml")
            with open(path, "w", encoding="utf-8") as f:
                f.write("this is not [ valid toml")
            self.assertEqual(rs.cfg_load_toml(path), {})

    def test_valid_toml_parses(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "good.toml")
            with open(path, "w", encoding="utf-8") as f:
                f.write('[policy]\nmode = "double"\n')
            self.assertEqual(rs.cfg_load_toml(path), {"policy": {"mode": "double"}})


class TestMergeReviewers(unittest.TestCase):
    def test_local_overrides_matching_key_fields_only(self):
        global_list = [{"key": "codex-gpt", "model": "gpt-5.2", "effort": "high"}]
        local_list = [{"key": "codex-gpt", "effort": "low"}]
        merged = rs.cfg_merge_reviewers(global_list, local_list)
        self.assertEqual(merged, [{"key": "codex-gpt", "model": "gpt-5.2", "effort": "low"}])

    def test_local_only_key_is_appended(self):
        global_list = [{"key": "a", "model": "m1"}]
        local_list = [{"key": "b", "model": "m2"}]
        merged = rs.cfg_merge_reviewers(global_list, local_list)
        self.assertEqual([r["key"] for r in merged], ["a", "b"])

    def test_global_only_key_is_preserved(self):
        global_list = [{"key": "a", "model": "m1"}, {"key": "b", "model": "m2"}]
        local_list = [{"key": "a", "model": "m1-override"}]
        merged = rs.cfg_merge_reviewers(global_list, local_list)
        self.assertEqual([r["key"] for r in merged], ["a", "b"])
        self.assertEqual(merged[0]["model"], "m1-override")

    def test_entry_with_no_key_is_skipped_not_raised(self):
        # one hand-written mistake in review-spec.toml must not crash the
        # whole orchestrator (matches cfg_load_toml's never-raises contract)
        global_list = [{"key": "a", "model": "m1"}, {"model": "no-key-here"}]
        local_list = [{"model": "also-no-key"}]
        merged = rs.cfg_merge_reviewers(global_list, local_list)
        self.assertEqual([r["key"] for r in merged], ["a"])


class TestResolveConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.global_home = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.global_home, ignore_errors=True)
        self.env = {"HOME": self.global_home}
        os.makedirs(os.path.join(self.global_home, ".config", "ai-kit"), exist_ok=True)
        with open(os.path.join(self.global_home, ".config", "ai-kit", "review-spec.toml"),
                   "w", encoding="utf-8") as f:
            f.write('[policy]\nmode = "single"\nladder = ["a"]\n'
                    '[[reviewers]]\nkey = "a"\nmodel = "m1"\nvendor = "openai"\n')

    def test_no_local_file_uses_global_only(self):
        resolved = rs.cfg_resolve(self.tmp, self.env)
        self.assertEqual(resolved["policy"]["mode"], "single")
        self.assertEqual(resolved["reviewers"][0]["key"], "a")

    def test_local_only_strategy_ignores_global(self):
        os.makedirs(os.path.join(self.tmp, ".aikit"), exist_ok=True)
        with open(os.path.join(self.tmp, ".aikit", "review-spec.toml"),
                   "w", encoding="utf-8") as f:
            f.write('strategy = "local-only"\n[policy]\nmode = "double"\n')
        resolved = rs.cfg_resolve(self.tmp, self.env)
        self.assertEqual(resolved["policy"]["mode"], "double")
        # local declared no reviewers, global not consulted
        self.assertEqual(resolved["reviewers"], [])

    def test_global_merge_is_the_default_strategy(self):
        os.makedirs(os.path.join(self.tmp, ".aikit"), exist_ok=True)
        with open(os.path.join(self.tmp, ".aikit", "review-spec.toml"),
                   "w", encoding="utf-8") as f:
            f.write('[[reviewers]]\nkey = "a"\nmodel = "m1"\nvendor = "openai"\neffort = "low"\n')
        resolved = rs.cfg_resolve(self.tmp, self.env)
        self.assertEqual(resolved["policy"]["mode"], "single")  # inherited from global
        self.assertEqual(resolved["reviewers"][0]["effort"], "low")  # local override applied


class TestRenderAndWriteToml(unittest.TestCase):
    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_round_trips_through_tomllib(self):
        import tomllib  # noqa: F811 -- local re-import shadows the reflection-only module-level one
        config = {"policy": {"mode": "double", "ladder": ["a", "b"]},
                  "reviewers": [{"key": "a", "model": "m1", "vendor": "openai"}]}
        rendered = rs.cfg_render_toml(config)
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["policy"]["mode"], "double")
        self.assertEqual(parsed["policy"]["ladder"], ["a", "b"])
        self.assertEqual(parsed["reviewers"][0]["key"], "a")

    def test_write_toml_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "nested", "review-spec.toml")
            rs.cfg_write_toml(path, {"policy": {"mode": "single"}, "reviewers": []})
            self.assertTrue(os.path.exists(path))

    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_escapes_quotes_and_backslashes_in_strings(self):
        rendered = rs.cfg_render_toml({"policy": {}, "reviewers": [
            {"key": "a", "command": 'echo "hi" \\ done'}]})
        import tomllib  # noqa: F811 -- local re-import shadows the reflection-only module-level one
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["reviewers"][0]["command"], 'echo "hi" \\ done')

    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_renders_top_level_strategy_when_present(self):
        rendered = rs.cfg_render_toml({"strategy": "local-only", "policy": {"mode": "single"},
                                        "reviewers": []})
        import tomllib  # noqa: F811 -- local re-import shadows the reflection-only module-level one
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["strategy"], "local-only")

    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_omits_strategy_line_when_absent(self):
        rendered = rs.cfg_render_toml({"policy": {"mode": "single"}, "reviewers": []})
        import tomllib  # noqa: F811 -- local re-import shadows the reflection-only module-level one
        parsed = tomllib.loads(rendered)
        self.assertNotIn("strategy", parsed)

    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_ladder_renders_as_priority_fallback_comment(self):
        rendered = rs.cfg_render_toml(
            {"policy": {"mode": "double", "ladder": ["codex-gpt", "sonnet-native"]},
             "reviewers": []}
        )
        self.assertIn("# Priority fallback order", rendered)
        self.assertIn("#   1. codex-gpt", rendered)
        self.assertIn("#   2. sonnet-native", rendered)
        import tomllib  # noqa: F811 -- local re-import shadows the reflection-only module-level one
        parsed = tomllib.loads(rendered)  # comment must not break parsing
        self.assertEqual(parsed["policy"]["ladder"], ["codex-gpt", "sonnet-native"])

    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_empty_ladder_renders_no_priority_comment(self):
        rendered = rs.cfg_render_toml({"policy": {"mode": "single", "ladder": []}, "reviewers": []})
        self.assertNotIn("# Priority fallback order", rendered)

    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_single_mode_ladder_comment_omits_secondary_clause(self):
        rendered = rs.cfg_render_toml(
            {"policy": {"mode": "single", "ladder": ["codex-gpt", "sonnet-native"]},
             "reviewers": []}
        )
        self.assertIn("# Priority fallback order", rendered)
        self.assertNotIn("secondary", rendered)

    def test_render_toml_rejects_invalid_purpose_value(self):
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"}]}
        output = config_io.cfg_render_toml(config)
        self.assertNotIn("not-a-real-purpose", output)

    def test_render_toml_rejects_non_string_purpose_without_raising(self):
        # HIGH finding: a non-string (unhashable) purpose value must be REJECTED, never crash
        # cfg_render_toml with an unhandled TypeError from a bare `in <set>` membership test.
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v", "purpose": ["review", "execute"]}]}
        output = config_io.cfg_render_toml(config)  # must not raise
        self.assertNotIn("[[reviewers]]", output)

    def test_render_toml_keeps_valid_purpose_value(self):
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v", "purpose": "execute"}]}
        output = config_io.cfg_render_toml(config)
        self.assertIn('purpose = "execute"', output)

    def test_render_toml_rejects_invalid_native_runtime_value(self):
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v",
             "native_runtime": "planning"}]}
        output = config_io.cfg_render_toml(config)
        self.assertNotIn("planning", output)
        self.assertNotIn("[[reviewers]]", output)

    def test_render_toml_rejects_non_string_native_runtime_without_raising(self):
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v",
             "native_runtime": ["claude"]}]}
        output = config_io.cfg_render_toml(config)
        self.assertNotIn("[[reviewers]]", output)

    def test_render_toml_keeps_valid_native_runtime_value(self):
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v",
             "native_runtime": "unknown"}]}
        output = config_io.cfg_render_toml(config)
        self.assertIn('native_runtime = "unknown"', output)

    def test_render_toml_rejects_native_runtime_with_non_null_cli(self):
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v",
             "native_runtime": "claude", "cli": "codex"}]}
        output = config_io.cfg_render_toml(config)
        self.assertNotIn("[[reviewers]]", output)
        self.assertNotIn("native_runtime", output)

    def test_render_toml_keeps_native_runtime_when_cli_is_absent(self):
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v",
             "native_runtime": "claude"}]}
        output = config_io.cfg_render_toml(config)
        self.assertIn("[[reviewers]]", output)
        self.assertIn('native_runtime = "claude"', output)

    def test_render_toml_rejects_non_bool_is_router(self):
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v", "is_router": "yes"}]}
        output = config_io.cfg_render_toml(config)
        self.assertNotIn("is_router", output)

    def test_render_toml_drops_rejected_reviewer_from_the_ladder_too(self):
        # HIGH finding: a dangling policy.ladder reference to a dropped reviewer key produces
        # a config that LOOKS valid (parses fine) but resolve_ladder_pick can never satisfy.
        config = {"policy": {"mode": "single", "ladder": ["bad", "good"]}, "reviewers": [
            {"key": "bad", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"},
            {"key": "good", "model": "m2", "vendor": "v2"},
        ]}
        output = config_io.cfg_render_toml(config)
        self.assertNotIn('"bad"', output)
        ladder_line = next(line for line in output.splitlines() if line.startswith("ladder"))
        self.assertNotIn("bad", ladder_line)
        self.assertIn("good", ladder_line)

    def test_render_toml_no_dangling_ladder_warning_when_rejected_key_not_in_ladder(self):
        # MEDIUM finding: a rejected reviewer whose key was never referenced in policy.ladder
        # at all must not trigger the "dropped dangling reference" stderr warning -- only an
        # actual ladder/reviewers divergence should. cfg_render_toml prints rejections to
        # stderr (Step 5's implementation), not into its returned string, so capture stderr.
        config = {"policy": {"mode": "single", "ladder": ["good"]}, "reviewers": [
            {"key": "bad", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"},
            {"key": "good", "model": "m2", "vendor": "v2"},
        ]}
        import io
        from contextlib import redirect_stderr
        captured = io.StringIO()
        with redirect_stderr(captured):
            config_io.cfg_render_toml(config)
        self.assertNotIn("dangling", captured.getvalue())

    def test_render_toml_result_resolves_cleanly_through_cfg_resolve(self):
        # The dropped-entry write must be USABLE, not just superficially valid TOML -- round-trip
        # it through cfg_write_toml + cfg_resolve (this repo's real resolution path) and confirm
        # the ladder cfg_resolve sees contains no reference to the dropped key.
        config = {"policy": {"mode": "single", "ladder": ["bad", "good"]}, "reviewers": [
            {"key": "bad", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"},
            {"key": "good", "model": "m2", "vendor": "v2", "cli": "opencode",
             "command": "opencode run -m {model}"},
        ]}
        with tempfile.TemporaryDirectory() as d:
            path = config_io.cfg_local_path(d)  # ./.aikit/review-spec.toml under d
            config_io.cfg_write_toml(path, config)
            resolved = config_io.cfg_resolve(d, {"HOME": d})
            self.assertNotIn("bad", resolved["policy"]["ladder"])
            self.assertIn("good", resolved["policy"]["ladder"])


class TestCacheCatalogPath(unittest.TestCase):
    def test_uses_cache_base_convention(self):
        path = model_catalog.cache_catalog_path({"HOME": "/home/u"})
        self.assertEqual(path, "/home/u/.cache/ai-kit/spec/model-catalog.json")


class TestCanonicalKey(unittest.TestCase):
    def test_builds_vendor_slash_model(self):
        self.assertEqual(model_catalog.canonical_key("openai", "gpt-5.6-sol"),
                          "openai/gpt-5.6-sol")


class TestValidateCatalogEntry(unittest.TestCase):
    def _valid_entry(self, **overrides):
        entry = {"provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
                  "source": {"models_dev": True}, "confidence": "high",
                  "last_verified": "2026-09-02"}
        entry.update(overrides)
        return entry

    def test_valid_entry_returns_none(self):
        self.assertIsNone(model_catalog.validate_catalog_entry(
            "openai/gpt-5.6-sol", self._valid_entry()))

    def test_missing_mandatory_field_is_rejected(self):
        entry = {"provider": "openai", "runtimes": {"opencode": {}}}
        reason = model_catalog.validate_catalog_entry("openai/gpt-5.6-sol", entry)
        self.assertIsNotNone(reason)
        self.assertIn("source", reason)

    def test_empty_runtimes_is_rejected(self):
        entry = {"provider": "openai", "runtimes": {}, "source": {}, "confidence": "low",
                  "last_verified": "2026-09-02"}
        reason = model_catalog.validate_catalog_entry("x", entry)
        self.assertIsNotNone(reason)

    def test_none_on_a_mandatory_field_is_rejected(self):
        # Important finding: the None-skip meant for OPTIONAL fields (a signal to clear the
        # field on merge) must never extend to a mandatory field -- a mandatory field present
        # with value None is still missing its required value.
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(provider=None))
        self.assertIsNotNone(reason)
        self.assertIn("provider", reason)

    def test_missing_optional_fields_never_rejected(self):
        entry = {"provider": "openai", "runtimes": {"opencode": {}}, "source": {},
                  "confidence": "low", "last_verified": "2026-09-02"}
        self.assertIsNone(model_catalog.validate_catalog_entry("x", entry))

    def test_wrong_type_provider_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(provider=123))
        self.assertIsNotNone(reason)
        self.assertIn("provider", reason)

    def test_non_dict_runtimes_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(runtimes=["opencode"]))
        self.assertIsNotNone(reason)

    def test_unrecognized_confidence_value_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(confidence="very-sure"))
        self.assertIsNotNone(reason)
        self.assertIn("confidence", reason)

    def test_wrong_type_optional_field_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(batch_mode="yes"))
        self.assertIsNotNone(reason)
        self.assertIn("batch_mode", reason)

    def test_unrecognized_name_declared_purpose_value_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(name_declared_purpose="planning"))
        self.assertIsNotNone(reason)
        self.assertIn("name_declared_purpose", reason)

    def test_review_name_declared_purpose_is_accepted(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(name_declared_purpose="review"))
        self.assertIsNone(reason)

    def test_execute_name_declared_purpose_is_accepted(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(name_declared_purpose="execute"))
        self.assertIsNone(reason)

    def test_absent_name_declared_purpose_is_never_rejected(self):
        reason = model_catalog.validate_catalog_entry("x", self._valid_entry())
        self.assertIsNone(reason)

    def test_unrecognized_native_runtime_value_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(native_runtime="planning"))
        self.assertIsNotNone(reason)
        self.assertIn("native_runtime", reason)

    def test_valid_native_runtime_values_are_accepted(self):
        for value in ("claude", "opencode", "codex", "cursor", "unknown"):
            reason = model_catalog.validate_catalog_entry(
                "x", self._valid_entry(native_runtime=value))
            self.assertIsNone(reason, msg=value)

    def test_absent_native_runtime_is_never_rejected(self):
        reason = model_catalog.validate_catalog_entry("x", self._valid_entry())
        self.assertIsNone(reason)

    def test_native_runtime_rejected_when_cli_is_present(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(native_runtime="claude", cli="codex"))
        self.assertIsNotNone(reason)
        self.assertIn("native_runtime", reason)
        self.assertIn("cli", reason)

    def test_wrong_type_scores_subfield_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(scores={"intelligence_index": "high"}))
        self.assertIsNotNone(reason)
        self.assertIn("scores", reason)

    def test_correct_type_optional_fields_pass(self):
        entry = self._valid_entry(batch_mode=True, is_router=False, fallback_quota=False,
                                   tokens_per_sec=142.3, native=False,
                                   reasoning_modes=["low", "medium", "high"], fast_mode=False,
                                   speed_tier="standard",
                                   scores={"intelligence_index": 68.4, "coding_index": 74.1,
                                           "agentic_index": 61.2},
                                   pricing={"input_per_1m": 3.5, "output_per_1m": 14.0})
        self.assertIsNone(model_catalog.validate_catalog_entry("x", entry))

    def test_wrong_type_reasoning_modes_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(reasoning_modes="high"))
        self.assertIsNotNone(reason)
        self.assertIn("reasoning_modes", reason)

    def test_reasoning_modes_with_a_non_string_element_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(reasoning_modes=["low", 3]))
        self.assertIsNotNone(reason)
        self.assertIn("reasoning_modes", reason)

    def test_wrong_type_fast_mode_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(fast_mode="no"))
        self.assertIsNotNone(reason)
        self.assertIn("fast_mode", reason)

    def test_wrong_type_speed_tier_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(speed_tier=3))
        self.assertIsNotNone(reason)
        self.assertIn("speed_tier", reason)

    def test_malformed_last_verified_date_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(last_verified="09/02/2026"))
        self.assertIsNotNone(reason)
        self.assertIn("last_verified", reason)

    def test_runtime_entry_wrong_type_model_id_is_rejected(self):
        entry = self._valid_entry(runtimes={"opencode": {"model_id": 123}})
        reason = model_catalog.validate_catalog_entry("x", entry)
        self.assertIsNotNone(reason)
        self.assertIn("model_id", reason)

    def test_runtime_entry_wrong_type_ctx_window_is_rejected(self):
        entry = self._valid_entry(runtimes={"opencode": {"model_id": "m", "ctx_window": "big"}})
        reason = model_catalog.validate_catalog_entry("x", entry)
        self.assertIsNotNone(reason)
        self.assertIn("ctx_window", reason)

    def test_runtime_entry_correct_types_pass(self):
        entry = self._valid_entry(
            runtimes={"opencode": {"model_id": "openai/gpt-5.6-sol", "ctx_window": 400000}})
        self.assertIsNone(model_catalog.validate_catalog_entry("x", entry))


class TestMergeCatalogEntry(unittest.TestCase):
    def test_valid_entry_is_added(self):
        entry = {"provider": "openai", "runtimes": {"opencode": {}}, "source": {},
                  "confidence": "high", "last_verified": "2026-09-02"}
        catalog, reason = model_catalog.merge_catalog_entry({}, "openai/gpt-5.6-sol", entry)
        self.assertIsNone(reason)
        self.assertIn("openai/gpt-5.6-sol", catalog)

    def test_invalid_entry_is_rejected_and_catalog_unchanged(self):
        catalog, reason = model_catalog.merge_catalog_entry({"existing": {}}, "bad", {})
        self.assertIsNotNone(reason)
        self.assertEqual(catalog, {"existing": {}})

    def test_incoming_none_on_mandatory_field_is_rejected_not_silently_merged(self):
        # Important finding: an incoming entry that would strip a mandatory field to None via
        # the merge's None-clears-existing-field behavior must be rejected outright, never
        # persisted as a catalog entry missing a mandatory field.
        existing_entry = {"provider": "p", "runtimes": {"c": {}}, "source": {},
                           "confidence": "high", "last_verified": "2026-09-02"}
        catalog = {"k": existing_entry}
        entry = {"provider": None, "runtimes": {"c": {}}, "source": {}, "confidence": "high",
                  "last_verified": "2026-09-02"}
        catalog, reason = model_catalog.merge_catalog_entry(catalog, "k", entry)
        self.assertIsNotNone(reason)
        self.assertIn("provider", reason)
        self.assertEqual(catalog["k"]["provider"], "p")  # unchanged -- rejected merge never applied

    def test_does_not_mutate_input_catalog(self):
        original = {"existing": {}}
        entry = {"provider": "p", "runtimes": {"c": {}}, "source": {}, "confidence": "high",
                 "last_verified": "2026-09-02"}
        model_catalog.merge_catalog_entry(original, "new", entry)
        self.assertNotIn("new", original)

    def test_runtimes_merge_across_two_cli_writes_for_the_same_key(self):
        entry_a = {"provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
                   "source": {}, "confidence": "high", "last_verified": "2026-09-02"}
        catalog, _ = model_catalog.merge_catalog_entry({}, "openai/gpt-5.6-sol", entry_a)
        entry_b = {"provider": "openai", "runtimes": {"codex": {"model_id": "gpt-5.6-sol"}},
                   "source": {}, "confidence": "high", "last_verified": "2026-09-02"}
        catalog, reason = model_catalog.merge_catalog_entry(catalog, "openai/gpt-5.6-sol", entry_b)
        self.assertIsNone(reason)
        self.assertIn("opencode", catalog["openai/gpt-5.6-sol"]["runtimes"])
        self.assertIn("codex", catalog["openai/gpt-5.6-sol"]["runtimes"])

    def test_explicit_none_in_the_incoming_entry_clears_the_existing_field(self):
        # CRITICAL finding: a source's provenance flipping to false must actually clear the
        # field it used to own, not leave it behind under plain dict-spread's "absent key
        # means preserve" semantics.
        existing_entry = {"provider": "p", "runtimes": {"c": {}}, "source": {}, "confidence": "high",
                           "last_verified": "2026-09-02", "scores": {"intelligence_index": 91.0}}
        catalog = {"k": existing_entry}
        entry = {"provider": "p", "runtimes": {"c": {}}, "source": {}, "confidence": "high",
                  "last_verified": "2026-09-02", "scores": None}
        catalog, reason = model_catalog.merge_catalog_entry(catalog, "k", entry)
        self.assertIsNone(reason)
        self.assertNotIn("scores", catalog["k"])

    def test_key_absent_from_incoming_entry_still_preserves_the_existing_value(self):
        # Contrast with the test above: OMITTING a key (a source that's simply down this run,
        # never claiming anything about the field) must still preserve the cached value --
        # only an explicit None is a clear signal.
        existing_entry = {"provider": "p", "runtimes": {"c": {}}, "source": {}, "confidence": "high",
                           "last_verified": "2026-09-02", "scores": {"intelligence_index": 91.0}}
        catalog = {"k": existing_entry}
        entry = {"provider": "p", "runtimes": {"c": {}}, "source": {}, "confidence": "high",
                  "last_verified": "2026-09-02"}  # no "scores" key at all
        catalog, reason = model_catalog.merge_catalog_entry(catalog, "k", entry)
        self.assertIsNone(reason)
        self.assertEqual(catalog["k"]["scores"], {"intelligence_index": 91.0})


class TestCurrentCandidateKeys(unittest.TestCase):
    def test_keeps_only_keys_with_a_currently_discovered_runtime(self):
        catalog = {
            "openai/gpt-5.6-sol": {"runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}}},
            "xai/grok-old": {"runtimes": {"opencode": {"model_id": "xai/grok-old"}}},
        }
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        self.assertEqual(model_catalog.current_candidate_keys(catalog, discovered),
                          {"openai/gpt-5.6-sol"})


class TestApplyHeuristicCorrections(unittest.TestCase):
    def test_merges_corrected_fields_into_existing_entry(self):
        catalog = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                     "source": {}, "confidence": "low",
                                     "last_verified": "2026-09-02", "is_router": True}}
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"is_router": False, "batch_mode": True})
        self.assertIsNone(reason)
        self.assertFalse(updated["router-env/x"]["is_router"])
        self.assertTrue(updated["router-env/x"]["batch_mode"])

    def test_marks_every_corrected_field_confirmed_even_when_value_is_unchanged(self):
        # HIGH finding: the wizard must be able to tell "never asked" apart from "asked, and
        # the user's answer happened to match the heuristic's own guess" -- so a field must
        # be recorded as confirmed even when the "correction" leaves its value unchanged.
        catalog = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                     "source": {}, "confidence": "low",
                                     "last_verified": "2026-09-02", "is_router": True}}
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"is_router": True})  # confirmed as-is, not corrected
        self.assertIsNone(reason)
        self.assertTrue(updated["router-env/x"]["is_router"])
        self.assertEqual(updated["router-env/x"]["heuristic_confirmed"], ["is_router"])

    def test_heuristic_confirmed_accumulates_across_separate_calls(self):
        catalog = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                     "source": {}, "confidence": "low",
                                     "last_verified": "2026-09-02", "is_router": True,
                                     "heuristic_confirmed": ["is_router"]}}
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"batch_mode": False})
        self.assertIsNone(reason)
        self.assertEqual(updated["router-env/x"]["heuristic_confirmed"],
                          ["batch_mode", "is_router"])

    def test_unknown_key_is_a_no_op(self):
        catalog = {"existing": {}}
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "nonexistent", {"is_router": True})
        self.assertIsNone(reason)
        self.assertEqual(updated, catalog)

    def test_does_not_mutate_input_catalog(self):
        catalog = {"k": {"provider": "p", "runtimes": {"c": {}}, "source": {},
                          "confidence": "high", "last_verified": "2026-09-02", "is_router": True}}
        model_catalog.apply_heuristic_corrections(catalog, "k", {"is_router": False})
        self.assertTrue(catalog["k"]["is_router"])

    def test_correction_that_would_produce_a_schema_invalid_entry_is_rejected(self):
        # CRITICAL finding: apply_heuristic_corrections must not bypass the same type-checked
        # schema validation merge_catalog_entry already enforces -- cache_write_json only writes
        # atomically, it never validates, so this is the ONLY gate before a bad correction reaches
        # the cache.
        catalog = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                     "source": {}, "confidence": "low",
                                     "last_verified": "2026-09-02", "is_router": True}}
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"is_router": "not-a-bool"})
        self.assertIsNotNone(reason)
        self.assertIn("is_router", reason)
        self.assertTrue(updated["router-env/x"]["is_router"])  # unchanged -- rejected correction never applied


class TestCachePaths(unittest.TestCase):
    def test_base_uses_xdg_cache_home(self):
        env = {"XDG_CACHE_HOME": "/x/cache"}
        self.assertEqual(rs.cache_base(env), "/x/cache/ai-kit/spec")

    def test_base_falls_back_to_home_dot_cache(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(rs.cache_base(env), "/home/u/.cache/ai-kit/spec")

    def test_runtimes_and_quota_paths(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(rs.cache_runtimes_path(env),
                          "/home/u/.cache/ai-kit/spec/runtimes.json")
        self.assertEqual(rs.cache_quota_path(env), "/home/u/.cache/ai-kit/spec/quota.json")


class TestCacheReadWrite(unittest.TestCase):
    def test_read_missing_file_returns_none(self):
        self.assertIsNone(rs.cache_read_json("/no/such/file.json"))

    def test_write_then_read_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "data.json")
            rs.cache_write_json(path, {"a": 1})
            self.assertEqual(rs.cache_read_json(path), {"a": 1})

    def test_read_malformed_json_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not valid json")
            self.assertIsNone(rs.cache_read_json(path))


class TestCacheStaleness(unittest.TestCase):
    def test_missing_file_is_stale(self):
        self.assertTrue(rs.cache_is_stale("/no/such/file.json", 3600))

    def test_fresh_file_is_not_stale(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.json")
            rs.cache_write_json(path, {})
            self.assertFalse(rs.cache_is_stale(path, 3600))

    def test_old_file_is_stale(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.json")
            rs.cache_write_json(path, {})
            old = time.time() - 7200
            os.utime(path, (old, old))
            self.assertTrue(rs.cache_is_stale(path, 3600))


class TestDetectInstalledClis(unittest.TestCase):
    def test_reports_installed_and_missing(self):
        def fake_which(name):
            return f"/usr/bin/{name}" if name in ("claude", "codex") else None
        result = rs.detect_installed_clis(which_fn=fake_which)
        self.assertEqual(result["claude"], "/usr/bin/claude")
        self.assertEqual(result["codex"], "/usr/bin/codex")
        self.assertIsNone(result["cursor-agent"])

    def test_covers_all_known_clis(self):
        result = rs.detect_installed_clis(which_fn=lambda n: None)
        self.assertEqual(set(result.keys()), set(rs.KNOWN_CLIS))


class TestDetectCurrentRuntime(unittest.TestCase):
    def test_claudecode_signal_returns_claude(self):
        self.assertEqual(
            detection.detect_current_runtime(env={"CLAUDECODE": "1"}), "claude")

    def test_opencode_signal_returns_opencode(self):
        self.assertEqual(
            detection.detect_current_runtime(
                env={"OPENCODE": "1", "OPENCODE_PID": "12345"}),
            "opencode")

    def test_cursor_agent_signal_returns_cursor_not_cursor_agent(self):
        self.assertEqual(
            detection.detect_current_runtime(env={"CURSOR_AGENT": "1"}), "cursor")

    def test_codex_version_signal_returns_codex(self):
        self.assertEqual(
            detection.detect_current_runtime(env={"CODEX_VERSION": "0.153.4"}),
            "codex")

    def test_empty_env_returns_unknown(self):
        self.assertEqual(detection.detect_current_runtime(env={}), "unknown")

    def test_empty_string_signal_is_falsy_and_falls_through(self):
        self.assertEqual(
            detection.detect_current_runtime(env={"CLAUDECODE": ""}), "unknown")

    def test_nested_subprocess_fixed_order_winner_is_claude(self):
        self.assertEqual(
            detection.detect_current_runtime(
                env={"OPENCODE": "1", "CLAUDECODE": "1"}),
            "claude")

    def test_env_none_reads_live_os_environ(self):
        with unittest.mock.patch.dict(os.environ, {"CLAUDECODE": "1"}, clear=True):
            self.assertEqual(detection.detect_current_runtime(env=None), "claude")


class TestDetectOpencodeModels(unittest.TestCase):
    def test_parses_one_model_per_line(self):
        class FakeResult:
            stdout = "opencode-go/kimi-k3\nopencode-go/qwen3.8-max\n\n"
        result = rs.detect_opencode_models("/usr/bin/opencode",
                                            run_fn=lambda *a, **k: FakeResult())
        self.assertEqual(result, ["opencode-go/kimi-k3", "opencode-go/qwen3.8-max"])

    def test_returns_empty_list_on_failure(self):
        def fake_run(*a, **k):
            raise OSError("not found")
        self.assertEqual(rs.detect_opencode_models("/usr/bin/opencode", run_fn=fake_run), [])


class TestDetectCursorAgentModels(unittest.TestCase):
    def test_parses_id_before_dash_separator(self):
        # confirmed live against a real authenticated install
        # (2026.08.25-3e8eec8): "Available models" header, blank line,
        # then "<id> - <display name>" per line.
        class FakeResult:
            stdout = (
                "Available models\n\n"
                "auto - Auto (current, default)\n"
                "kimi-k3-high - Kimi K3 High\n"
                "glm-5.2-high - GLM 5.2\n"
            )
        result = rs.detect_cursor_agent_models("/usr/bin/cursor-agent",
                                                run_fn=lambda *a, **k: FakeResult())
        self.assertEqual(result, ["auto", "kimi-k3-high", "glm-5.2-high"])

    def test_skips_lines_with_no_separator(self):
        class FakeResult:
            stdout = "Available models\n\nauto - Auto (current, default)\n"
        result = rs.detect_cursor_agent_models("/usr/bin/cursor-agent",
                                                run_fn=lambda *a, **k: FakeResult())
        self.assertEqual(result, ["auto"])

    def test_returns_empty_list_on_failure(self):
        def fake_run(*a, **k):
            raise OSError("not found")
        self.assertEqual(rs.detect_cursor_agent_models("/usr/bin/cursor-agent",
                                                         run_fn=fake_run), [])


class TestInferVendorFromModel(unittest.TestCase):
    def test_opencode_namespaced_ids(self):
        self.assertEqual(rs.infer_vendor_from_model("opencode-go/kimi-k3"), "moonshot")
        self.assertEqual(rs.infer_vendor_from_model("opencode-go/qwen3.8-max"), "alibaba")
        self.assertEqual(rs.infer_vendor_from_model("opencode-go/grok-4.6"), "xai")
        self.assertEqual(rs.infer_vendor_from_model("opencode-go/gpt-5.6-luna"), "openai")

    def test_cursor_agent_bare_ids(self):
        self.assertEqual(rs.infer_vendor_from_model("claude-opus-5-thinking-high"), "anthropic")
        self.assertEqual(rs.infer_vendor_from_model("gpt-5.3-codex"), "openai")
        self.assertEqual(rs.infer_vendor_from_model("cursor-grok-4.6-high"), "xai")
        self.assertEqual(rs.infer_vendor_from_model("glm-5.2-high"), "zhipu")
        self.assertEqual(rs.infer_vendor_from_model("kimi-k3-high"), "moonshot")
        self.assertEqual(rs.infer_vendor_from_model("gemini-3.7-flash-high"), "google")
        self.assertEqual(rs.infer_vendor_from_model("composer-2.5"), "cursor")

    def test_unknown_prefix_returns_none(self):
        self.assertIsNone(rs.infer_vendor_from_model("auto"))
        self.assertIsNone(rs.infer_vendor_from_model("ollama-cloud/llama-70b"))


class TestGroupModelsByFamily(unittest.TestCase):
    def test_strips_trailing_tier_tokens(self):
        models = ["claude-opus-5-thinking-high-fast", "claude-opus-5-high",
                  "claude-opus-5-low-fast"]
        groups = rs.group_models_by_family(models)
        self.assertEqual(groups, {"claude-opus-5": models})

    def test_keeps_different_versions_as_separate_families(self):
        # confirmed live: cursor-grok-4.5-* and cursor-grok-4.6-* are
        # genuinely different model generations, must never merge
        groups = rs.group_models_by_family(["cursor-grok-4.5-high", "cursor-grok-4.6-high"])
        self.assertEqual(set(groups), {"cursor-grok-4.5", "cursor-grok-4.6"})

    def test_id_with_no_recognized_suffix_is_its_own_family(self):
        groups = rs.group_models_by_family(["auto", "composer-2.5", "kimi-k2.7-code"])
        self.assertEqual(groups, {
            "auto": ["auto"], "composer-2.5": ["composer-2.5"],
            "kimi-k2.7-code": ["kimi-k2.7-code"],
        })

    def test_empty_list_returns_empty_dict(self):
        self.assertEqual(rs.group_models_by_family([]), {})

    def test_preserves_first_seen_order_of_families(self):
        groups = rs.group_models_by_family(["b-high", "a-high", "b-low"])
        self.assertEqual(list(groups), ["b", "a"])


class TestDetectToolAvailability(unittest.TestCase):
    def test_reports_installed_and_missing_tools(self):
        def fake_which(name):
            return f"/usr/bin/{name}" if name in ("rg", "fd") else None
        result = detection.detect_tool_availability(which_fn=fake_which)
        self.assertEqual(result, {"rg": True, "sd": False, "bat": False,
                                   "eza": False, "fd": True, "codegraph": False})


class TestResolveAgentsToolingPath(unittest.TestCase):
    def test_env_override_wins_when_it_exists(self):
        env = {"AGENTS_TOOLING_PATH": "/custom/AGENTS-TOOLING.md", "HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=True):
            self.assertEqual(detection.resolve_agents_tooling_path(env=env),
                              "/custom/AGENTS-TOOLING.md")

    def test_env_override_ignored_when_it_does_not_exist(self):
        # never pass an unverified path into a dispatch prompt, even one the user configured
        env = {"AGENTS_TOOLING_PATH": "/custom/AGENTS-TOOLING.md", "HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=False):
            self.assertIsNone(detection.resolve_agents_tooling_path(env=env))

    def test_falls_back_to_conventional_home_path_if_it_exists(self):
        env = {"HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=True):
            self.assertEqual(detection.resolve_agents_tooling_path(env=env),
                              "/home/u/.agents/AGENTS-TOOLING.md")

    def test_returns_none_when_nothing_found(self):
        env = {"HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=False):
            self.assertIsNone(detection.resolve_agents_tooling_path(env=env))


class TestFindCodegraphAlternative(unittest.TestCase):
    def test_finds_grok_model_reachable_via_cursor_agent(self):
        snapshot = {"clis": {
            "cursor-agent": {"installed": True,
                              "models": ["cursor-grok-4.6-high", "claude-opus-5-high"]},
            "opencode": {"installed": True, "models": ["opencode-go/qwen3.8-max"]},
        }}
        result = detection.find_codegraph_alternative("grok", "grok-4.6", snapshot)
        self.assertEqual(result, "cursor-agent")

    def test_returns_none_when_cli_already_supports_codegraph(self):
        snapshot = {"clis": {"cursor-agent": {"installed": True, "models": ["cursor-grok-4.6"]}}}
        result = detection.find_codegraph_alternative("cursor-agent", "cursor-grok-4.6", snapshot)
        self.assertIsNone(result)

    def test_returns_none_when_no_matching_model_found_anywhere(self):
        snapshot = {"clis": {
            "cursor-agent": {"installed": True, "models": ["claude-opus-5-high"]},
            "opencode": {"installed": True, "models": ["opencode-go/qwen3.8-max"]},
        }}
        result = detection.find_codegraph_alternative("grok", "grok-4.6", snapshot)
        self.assertIsNone(result)

    def test_skips_a_codegraph_capable_cli_that_is_not_installed(self):
        snapshot = {"clis": {"cursor-agent": {"installed": False}}}
        result = detection.find_codegraph_alternative("grok", "grok-4.6", snapshot)
        self.assertIsNone(result)


class TestCheckCodegraphMcpHealthy(unittest.TestCase):
    def test_grok_is_always_false_no_command_attempted(self):
        # grok is confirmed unsupported by codegraph -- never even run a command for it
        result = detection.check_codegraph_mcp_healthy(
            "grok", run_fn=lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("must not run any command for grok")))
        self.assertFalse(result)

    def test_unknown_cli_is_false(self):
        self.assertFalse(detection.check_codegraph_mcp_healthy("some-future-cli"))

    def test_claude_true_when_mcp_get_exits_zero_and_status_is_connected(self):
        # confirmed live (2026-08-30): `claude mcp get <name>` exits 0 and prints a
        # "Status: ✔ Connected" line when the server is registered AND healthy
        result = detection.check_codegraph_mcp_healthy(
            "claude", run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0, stdout="codegraph:\n  Scope: user config\n  Status: ✔ Connected\n"))
        self.assertTrue(result)

    def test_claude_false_when_get_exits_zero_but_status_shows_failed_to_connect(self):
        # confirmed live: a REGISTERED server can still be currently disconnected -- `claude
        # mcp get` returned exit 0 with "Status: ✘ Failed to connect" observed live for a real
        # server in this session. Registered-but-unhealthy must be treated as unusable, same as
        # not-registered -- exit code 0 alone is NOT sufficient to declare it usable.
        result = detection.check_codegraph_mcp_healthy(
            "claude", run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0,
                stdout="codegraph:\n  Scope: user config\n  Status: ✘ Failed to connect — "
                        "CONNECTION_CLOSED\n"))
        self.assertFalse(result)

    def test_claude_false_when_get_and_list_fallback_both_say_not_registered(self):
        # confirmed live: `claude mcp get nonexistent` exits 1 with "No MCP server named...";
        # this must also cross-check `mcp list` (fallback) before concluding "not registered"
        def fake_run(cmd, **k):
            if "get" in cmd:
                return unittest.mock.MagicMock(returncode=1)
            return unittest.mock.MagicMock(returncode=0, stdout="other-tool: x - Connected\n")
        result = detection.check_codegraph_mcp_healthy("claude", run_fn=fake_run)
        self.assertFalse(result)

    def test_claude_get_succeeds_never_calls_list_fallback(self):
        # the fallback must be nonzero-exit-triggered only -- a successful get is the cheapest
        # path and must not incur a second subprocess call
        seen = []
        detection.check_codegraph_mcp_healthy(
            "claude",
            run_fn=lambda cmd, **k: seen.append(cmd) or unittest.mock.MagicMock(
                returncode=0, stdout="Status: ✔ Connected\n"))
        self.assertEqual(seen, ["claude mcp get codegraph"])

    def test_claude_get_fails_but_list_fallback_finds_it_registered_and_healthy(self):
        # the exact resilience case this fallback exists for: `get` returns nonzero for some
        # unrelated reason (CLI bug, auth hiccup) even though the server genuinely IS registered
        def fake_run(cmd, **k):
            if "get" in cmd:
                return unittest.mock.MagicMock(returncode=1)
            return unittest.mock.MagicMock(returncode=0, stdout="codegraph: x - ✔ Connected\n")
        result = detection.check_codegraph_mcp_healthy("claude", run_fn=fake_run)
        self.assertTrue(result)

    def test_codex_true_when_mcp_get_exits_zero_and_healthy(self):
        # confirmed live: codex mcp get <name> mirrors claude's exit-code contract exactly
        result = detection.check_codegraph_mcp_healthy(
            "codex", run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0, stdout="Status: ✔ Connected\n"))
        self.assertTrue(result)

    def test_cursor_agent_parses_mcp_list_for_an_actual_server_name_token(self):
        # confirmed live: cursor-agent has no `mcp get`, only `mcp list` -- must parse output.
        # "codegraph" must be the actual name token (text before the first ':'), never a
        # substring match anywhere in the line
        fake_list = "codegraph: some-command - ✔ Connected\nother-tool: x - ✔ Connected\n"
        result = detection.check_codegraph_mcp_healthy(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fake_list))
        self.assertTrue(result)

    def test_cursor_agent_false_when_codegraph_only_appears_outside_the_name_token(self):
        fake_list = "other-tool: some codegraph-related command - ✔ Connected\n"
        result = detection.check_codegraph_mcp_healthy(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fake_list))
        self.assertFalse(result)

    def test_cursor_agent_false_when_codegraph_present_but_disconnected(self):
        # present (name token matches) but its own line shows a failure signal -- must be
        # treated the same as absent, not as usable
        fake_list = "codegraph: some-command - ✘ Failed to connect\n"
        result = detection.check_codegraph_mcp_healthy(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fake_list))
        self.assertFalse(result)

    def test_opencode_parses_mcp_list_the_same_way_as_cursor_agent(self):
        fake_list = "codegraph: ✔ connected\n"
        result = detection.check_codegraph_mcp_healthy(
            "opencode",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fake_list))
        self.assertTrue(result)

    def test_list_based_client_false_when_no_servers_configured(self):
        result = detection.check_codegraph_mcp_healthy(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0,
                stdout="No MCP servers configured (expected in .cursor/mcp.json or "
                       "~/.cursor/mcp.json)\n"))
        self.assertFalse(result)


class TestBuildRuntimesSnapshot(unittest.TestCase):
    def test_marks_missing_clis_not_installed(self):
        snapshot = rs.build_runtimes_snapshot(which_fn=lambda n: None,
                                               run_fn=lambda *a, **k: None)
        self.assertFalse(snapshot["clis"]["grok"]["installed"])

    def test_lists_opencode_models_when_installed(self):
        class FakeResult:
            stdout = "opencode-go/kimi-k3\n"

        def fake_which(name):
            return "/usr/bin/opencode" if name == "opencode" else None

        snapshot = rs.build_runtimes_snapshot(which_fn=fake_which,
                                               run_fn=lambda *a, **k: FakeResult())
        self.assertTrue(snapshot["clis"]["opencode"]["installed"])
        self.assertEqual(snapshot["clis"]["opencode"]["models"], ["opencode-go/kimi-k3"])

    def test_lists_cursor_agent_models_when_installed(self):
        class FakeResult:
            stdout = "Available models\n\nauto - Auto (current, default)\n"

        def fake_which(name):
            return "/usr/bin/cursor-agent" if name == "cursor-agent" else None

        snapshot = rs.build_runtimes_snapshot(which_fn=fake_which,
                                               run_fn=lambda *a, **k: FakeResult())
        self.assertTrue(snapshot["clis"]["cursor-agent"]["installed"])
        self.assertEqual(snapshot["clis"]["cursor-agent"]["models"], ["auto"])

    def test_non_multi_provider_clis_have_no_models_key(self):
        def fake_which(name):
            return "/usr/bin/codex" if name == "codex" else None
        snapshot = rs.build_runtimes_snapshot(which_fn=fake_which,
                                               run_fn=lambda *a, **k: None)
        self.assertNotIn("models", snapshot["clis"]["codex"])


class TestResolveLadderPick(unittest.TestCase):
    def setUp(self):
        self.reviewers = [
            {"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai"},
            {"key": "grok-flagship", "model": "grok-4.6", "vendor": "xai"},
        ]

    def test_picks_first_available_non_same_vendor(self):
        pick = rs.resolve_ladder_pick(self.reviewers, ["codex-gpt", "grok-flagship"],
                                       skip_vendor="anthropic", quota={})
        self.assertEqual(pick.key, "codex-gpt")

    def test_skips_same_vendor_as_source(self):
        pick = rs.resolve_ladder_pick(self.reviewers, ["codex-gpt", "grok-flagship"],
                                       skip_vendor="openai", quota={})
        self.assertEqual(pick.key, "grok-flagship")

    def test_skips_candidate_without_quota(self):
        quota = {"codex-gpt": {"available": False}}
        pick = rs.resolve_ladder_pick(self.reviewers, ["codex-gpt", "grok-flagship"],
                                       skip_vendor="anthropic", quota=quota)
        self.assertEqual(pick.key, "grok-flagship")

    def test_no_quota_entry_means_available(self):
        pick = rs.resolve_ladder_pick(self.reviewers, ["codex-gpt"],
                                       skip_vendor="anthropic", quota={})
        self.assertEqual(pick.key, "codex-gpt")

    def test_falls_back_to_same_vendor_before_giving_up(self):
        # only same-vendor-as-source candidate exists and has quota -> still picked,
        # rather than returning None
        pick = rs.resolve_ladder_pick(self.reviewers, ["codex-gpt"],
                                       skip_vendor="openai", quota={})
        self.assertEqual(pick.key, "codex-gpt")

    def test_returns_none_when_nothing_survives(self):
        quota = {"codex-gpt": {"available": False}}
        pick = rs.resolve_ladder_pick([self.reviewers[0]], ["codex-gpt"],
                                       skip_vendor="anthropic", quota=quota)
        self.assertIsNone(pick)

    def test_unknown_ladder_key_is_skipped(self):
        pick = rs.resolve_ladder_pick(self.reviewers, ["nonexistent", "grok-flagship"],
                                       skip_vendor="anthropic", quota={})
        self.assertEqual(pick.key, "grok-flagship")

    def test_entry_missing_model_resolves_to_empty_string_not_a_crash(self):
        reviewers = [{"key": "no-model", "vendor": "openai"}]
        pick = rs.resolve_ladder_pick(reviewers, ["no-model"], skip_vendor="anthropic", quota={})
        self.assertEqual(pick.model, "")


class TestResolveReviewers(unittest.TestCase):
    def setUp(self):
        self.config = {
            "policy": {"mode": "single", "ladder": ["claude-opus", "claude-sonnet", "codex-gpt"]},
            "reviewers": [
                {"key": "claude-opus", "model": "opus", "vendor": "anthropic"},
                {"key": "claude-sonnet", "model": "sonnet", "vendor": "anthropic"},
                {"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai",
                 "cli": "codex", "command": "codex exec -m {model} {prompt}"},
            ],
        }

    def test_no_cross_ai_returns_only_the_no_config_fallback(self):
        result = rs.resolve_reviewers(self.config, quota={}, source_vendor="anthropic",
                                       cross_ai=False)
        self.assertEqual(result, [rs.NO_CONFIG_FALLBACK])

    def test_no_config_at_all_falls_back_to_session_default(self):
        config = {"policy": {"mode": "single", "ladder": []}, "reviewers": []}
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic",
                                       cross_ai=True)
        self.assertEqual(result, [rs.NO_CONFIG_FALLBACK])

    def test_single_mode_skips_same_vendor_as_source(self):
        # single mode's whole point is an independent perspective, so the two
        # same-vendor-as-source (anthropic) ladder entries are skipped even
        # though they're earlier in the ladder
        result = rs.resolve_reviewers(self.config, quota={}, source_vendor="anthropic",
                                       cross_ai=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].key, "codex-gpt")

    def test_single_mode_falls_through_tiers_when_flagship_lacks_quota(self):
        quota = {"codex-gpt": {"available": False}}
        result = rs.resolve_reviewers(self.config, quota=quota, source_vendor="anthropic",
                                       cross_ai=True)
        # only same-vendor entries left with quota -> the vendor-skip fallback picks
        # the ladder's best surviving entry, which is claude-opus (tier-aware: tried
        # before claude-sonnet because it is earlier in the ladder)
        self.assertEqual(result[0].key, "claude-opus")

    def test_double_mode_primary_is_first_ladder_entry_tier_aware(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 2)
        # first ladder entry, regardless of native/external (here it happens
        # to also be native, since claude-opus leads the ladder)
        self.assertEqual(result[0].key, "claude-opus")
        self.assertEqual(result[1].key, "codex-gpt")      # first DIFFERENT-vendor entry

    def test_double_mode_primary_falls_through_tiers_when_flagship_lacks_quota(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        quota = {"claude-opus": {"available": False}}
        result = rs.resolve_reviewers(config, quota=quota, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result[0].key, "claude-sonnet")  # falls through the tier ladder
        self.assertEqual(result[1].key, "codex-gpt")

    def test_double_mode_drops_to_single_when_no_other_vendor_has_quota(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        quota = {"codex-gpt": {"available": False}}
        result = rs.resolve_reviewers(config, quota=quota, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 1)  # no cross-vendor survivor -> just the primary
        self.assertEqual(result[0].key, "claude-opus")

    def test_double_mode_with_empty_ladder_falls_back_to_session_default(self):
        config = {"policy": {"mode": "double", "ladder": []}, "reviewers": []}
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result, [rs.NO_CONFIG_FALLBACK])

    def test_double_mode_primary_is_external_when_it_leads_the_ladder(self):
        # CHANGED 2026-08-29: native entries are no longer given automatic
        # precedence over ladder position (superseding the old "double mode
        # always runs a native baseline, guaranteed" rule from
        # docs/superpowers/specs/2026-08-27-review-spec-cross-ai-design.md
        # §3). An external entry ranked ABOVE every native entry in the
        # ladder now DOES become primary — ladder position is the only
        # priority signal.
        config = {
            "policy": {"mode": "double", "ladder": ["codex-gpt", "claude-opus", "claude-sonnet"]},
            "reviewers": self.config["reviewers"],
        }
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result[0].key, "codex-gpt")      # first ladder entry, external
        self.assertEqual(result[0].cli, "codex")
        self.assertEqual(result[1].key, "claude-opus")    # first different-vendor entry

    def test_double_mode_with_only_external_entry_picks_it_as_primary_and_drops_secondary(self):
        # ladder is entirely external -> primary is that external entry
        # itself (no more forced NO_CONFIG_FALLBACK just because nothing
        # native is configured), and secondary is dropped since nothing
        # else in the ladder has a different vendor.
        config = {
            "policy": {"mode": "double", "ladder": ["codex-gpt"]},
            "reviewers": [self.config["reviewers"][2]],  # codex-gpt only, no native entries at all
        }
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].key, "codex-gpt")

    def test_double_mode_secondary_is_dropped_not_substituted_with_same_vendor(self):
        # regression: the design's guarantee for the secondary slot is
        # "cross-vendor alternate, DROPPED if none survives" — an earlier
        # draft's resolve_ladder_pick fell back to a same-vendor pick
        # instead (its generic same-vendor-fallback pass), so a ladder
        # with a same-vendor EXTERNAL entry (e.g. an "anthropic"-vendor
        # CLI profile) would incorrectly seat it as the secondary,
        # running two same-vendor reviewers under "double review".
        config = {
            "policy": {"mode": "double", "ladder": ["claude-opus", "claude-cli-opus"]},
            "reviewers": [
                {"key": "claude-opus", "model": "opus", "vendor": "anthropic"},
                {"key": "claude-cli-opus", "model": "opus", "vendor": "anthropic",
                 "cli": "claude", "command": "claude -p --model {model} {prompt}"},
            ],
        }
        result = rs.resolve_reviewers(config, quota={}, source_vendor="openai", cross_ai=True)
        self.assertEqual(len(result), 1)  # secondary dropped, not substituted
        self.assertEqual(result[0].key, "claude-opus")

    def test_double_mode_single_external_entry_becomes_primary_secondary_dropped(self):
        # CHANGED 2026-08-29: a ladder holding a single external (cli-set)
        # entry and no native entry now seats that entry as primary itself
        # (ladder position is the only priority signal — see
        # resolve_reviewers' docstring) rather than forcing NO_CONFIG_FALLBACK.
        # secondary still has nothing cross-vendor to pick from, so it's
        # dropped, not substituted with a same-vendor entry.
        config = {
            "policy": {"mode": "double", "ladder": ["claude-cli-opus"]},
            "reviewers": [
                {"key": "claude-cli-opus", "model": "opus", "vendor": "anthropic",
                 "cli": "claude", "command": "claude -p --model {model} {prompt}"},
            ],
        }
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 1)  # secondary dropped, not substituted
        self.assertEqual(result[0].key, "claude-cli-opus")

    def test_resolve_reviewers_filters_ladder_to_review_purpose(self):
        config = {
            "policy": {"mode": "single", "ladder": ["execute-only", "both-ok"]},
            "reviewers": [
                {"key": "execute-only", "model": "m1", "vendor": "openai", "purpose": "execute"},
                {"key": "both-ok", "model": "m2", "vendor": "xai", "purpose": "both"},
            ],
        }
        result = quota.resolve_reviewers(config, quota={}, source_vendor="", cross_ai=True)
        self.assertEqual([r.key for r in result], ["both-ok"])

    def test_resolve_reviewers_falls_back_to_full_ladder_when_purpose_filter_empties_it(self):
        config = {
            "policy": {"mode": "single", "ladder": ["execute-only"]},
            "reviewers": [
                {"key": "execute-only", "model": "m1", "vendor": "openai", "purpose": "execute"},
            ],
        }
        result = quota.resolve_reviewers(config, quota={}, source_vendor="", cross_ai=True)
        self.assertEqual([r.key for r in result], ["execute-only"])

    def test_resolve_reviewers_missing_purpose_field_always_included(self):
        config = {
            "policy": {"mode": "single", "ladder": ["legacy-entry"]},
            "reviewers": [{"key": "legacy-entry", "model": "m1", "vendor": "openai"}],
        }
        result = quota.resolve_reviewers(config, quota={}, source_vendor="", cross_ai=True)
        self.assertEqual([r.key for r in result], ["legacy-entry"])

    def test_resolve_reviewers_warns_on_fallback_but_not_otherwise(self):
        warnings = []
        config_fallback = {
            "policy": {"mode": "single", "ladder": ["execute-only"]},
            "reviewers": [
                {"key": "execute-only", "model": "m1", "vendor": "openai", "purpose": "execute"},
            ],
        }
        quota.resolve_reviewers(config_fallback, quota={}, source_vendor="", cross_ai=True,
                                 warn_fn=warnings.append)
        self.assertEqual(len(warnings), 1)
        self.assertIn("purpose", warnings[0].lower())

        warnings.clear()
        config_no_fallback = {
            "policy": {"mode": "single", "ladder": ["both-ok"]},
            "reviewers": [{"key": "both-ok", "model": "m2", "vendor": "xai", "purpose": "both"}],
        }
        quota.resolve_reviewers(config_no_fallback, quota={}, source_vendor="", cross_ai=True,
                                 warn_fn=warnings.append)
        self.assertEqual(warnings, [])


class TestFilterLadderByPurpose(unittest.TestCase):
    def test_uses_the_shared_purpose_matches_predicate(self):
        # A direct check that this ladder-shaped filter is NOT a reimplementation of the
        # matching logic -- it must agree with execute_selection.purpose_matches exactly,
        # including for a value purpose_matches alone decides (e.g. "both").
        reviewers = [{"key": "a", "purpose": "both"}]
        result, fell_back = quota._filter_ladder_by_purpose(reviewers, ["a"], "review")
        self.assertEqual(result, ["a"])
        self.assertFalse(fell_back)
        self.assertTrue(execute_selection.purpose_matches("both", "review"))

    def test_reports_fell_back_true_only_when_narrowing_emptied_the_ladder(self):
        reviewers = [{"key": "a", "purpose": "execute"}]
        result, fell_back = quota._filter_ladder_by_purpose(reviewers, ["a"], "review")
        self.assertEqual(result, ["a"])  # unfiltered fallback
        self.assertTrue(fell_back)

    def test_reports_fell_back_false_when_nothing_needed_excluding(self):
        reviewers = [{"key": "a"}]  # no purpose set -- always passes, nothing excluded
        result, fell_back = quota._filter_ladder_by_purpose(reviewers, ["a"], "review")
        self.assertEqual(result, ["a"])
        self.assertFalse(fell_back)


class TestBuildReviewerCommand(unittest.TestCase):
    def test_codex_bakes_effort_and_service_tier_as_separate_dash_c_flags(self):
        cmd = rs.build_reviewer_command("codex", effort="low", service_tier="fast")
        self.assertIn("-m {model}", cmd)
        self.assertIn("model_reasoning_effort='\"low\"'", cmd)
        self.assertIn("service_tier='\"fast\"'", cmd)
        self.assertNotIn("{prompt}", cmd)  # stdin-only — confirmed live
        self.assertIn("--sandbox read-only", cmd)

    def test_codex_omits_unset_knobs(self):
        cmd = rs.build_reviewer_command("codex")
        self.assertNotIn("model_reasoning_effort", cmd)
        self.assertNotIn("service_tier", cmd)

    def test_claude_command_shape(self):
        # no {prompt} — confirmed live: `claude -p` with no positional
        # prompt reads it from stdin
        self.assertEqual(rs.build_reviewer_command("claude"),
                          "claude -p --model {model} --output-format text")

    def test_grok_command_shape(self):
        # corrected 2026-08-29: `-p -` does NOT read from stdin -- it sends the literal
        # string "-" as the prompt (confirmed live). {prompt} is the correct placeholder,
        # shlex-quoted by render_reviewer_command like every other builder.
        self.assertEqual(rs.build_reviewer_command("grok"),
                          "grok -p {prompt} -m {model} --output-format plain")

    def test_gemini_no_longer_registered(self):
        # removed 2026-08-29 -- Gemini CLI is deprecated; never fall back to
        # a guessed shape for a CLI outside the registry
        with self.assertRaises(ValueError):
            rs.build_reviewer_command("gemini")

    def test_opencode_command_shape(self):
        # no {prompt} — confirmed live: `opencode run -m {model}` with no
        # positional message reads it from stdin
        self.assertEqual(rs.build_reviewer_command("opencode"),
                          "opencode run -m {model}")

    def test_cursor_agent_defaults_to_plan_mode(self):
        cmd = rs.build_reviewer_command("cursor-agent")
        self.assertIn("--mode plan", cmd)
        self.assertIn("--trust", cmd)
        self.assertIn("--model {model}", cmd)
        # no {prompt} — confirmed live: cursor-agent's -p/--print is a
        # boolean flag; with it set the process reads stdin instead
        self.assertNotIn("{prompt}", cmd)
        self.assertIn("cursor-agent -p ", cmd)

    def test_cursor_agent_accepts_ask_mode(self):
        cmd = rs.build_reviewer_command("cursor-agent", mode="ask")
        self.assertIn("--mode ask", cmd)

    def test_cursor_agent_rejects_a_write_capable_mode(self):
        with self.assertRaises(ValueError):
            rs.build_reviewer_command("cursor-agent", mode="default")

    def test_unknown_cli_raises_value_error(self):
        with self.assertRaises(ValueError):
            rs.build_reviewer_command("nonexistent-cli")

    def test_built_command_renders_through_render_reviewer_command(self):
        # the factory's output must still be a valid command template —
        # {model} fillable exactly like a hand-written one. codex's
        # template has no {prompt} (stdin-only, confirmed live), so
        # render_reviewer_command just leaves the prompt text unused here
        # — delivery happens via probe_reviewer_quota's/the orchestrator's
        # stdin redirect instead, not by string substitution.
        cmd = rs.build_reviewer_command("codex", effort="high")
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command=cmd, extra={})
        filled = rs.render_reviewer_command(resolved, "hello")
        self.assertIn("-m gpt-5.2", filled)
        self.assertIn("model_reasoning_effort='\"high\"'", filled)
        self.assertNotIn("hello", filled)


class TestBuildReviewerModelId(unittest.TestCase):
    def test_cursor_agent_adds_bracket_overrides(self):
        model_id = rs.build_cursor_agent_model_id("claude-opus-4-8", effort="high", fast=False,
                                                    context="1m")
        self.assertEqual(model_id, "claude-opus-4-8[effort=high,fast=false,context=1m]")

    def test_cursor_agent_no_overrides_returns_base_model_unchanged(self):
        self.assertEqual(rs.build_cursor_agent_model_id("claude-opus-4-8"), "claude-opus-4-8")

    def test_dispatches_via_cli_name(self):
        self.assertEqual(
            rs.build_reviewer_model_id("cursor-agent", "gpt-5.3-codex", effort="low"),
            "gpt-5.3-codex[effort=low]",
        )

    def test_non_cursor_cli_returns_base_model_unchanged(self):
        self.assertEqual(rs.build_reviewer_model_id("codex", "gpt-5.2", effort="high"), "gpt-5.2")


class TestRenderReviewerCommand(unittest.TestCase):
    def test_fills_model_and_prompt(self):
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command='codex exec -m {model} {prompt}',
                                        extra={})
        self.assertEqual(rs.render_reviewer_command(resolved, "hello"),
                          'codex exec -m gpt-5.2 hello')

    def test_fills_extra_fields(self):
        cmd = "codex exec -m {model} -c service_tier='\"{service_tier}\"' {prompt}"
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command=cmd,
                                        extra={"service_tier": "fast"})
        out = rs.render_reviewer_command(resolved, "hi")
        self.assertIn("service_tier='\"fast\"'", out)

    def test_prompt_is_shell_escaped_but_extra_fields_are_not(self):
        # {prompt} is free text built from document paths/content signals —
        # the one field that MUST survive as a single shell argument no
        # matter what it contains. {model}/extra fields are short,
        # human-typed config values whose own quoting idiom (e.g. codex's
        # -c key='"value"') the template author controls directly — auto-
        # quoting those would break that idiom, so only {prompt} is quoted.
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="codex exec -m {model} {prompt}",
                                        extra={})
        dangerous_prompt = 'Read this; rm -rf / #'
        out = rs.render_reviewer_command(resolved, dangerous_prompt)
        import shlex as _shlex
        tokens = _shlex.split(out)
        self.assertEqual(tokens[-1], dangerous_prompt)  # survives as ONE argument

    def test_missing_command_raises_value_error_not_attribute_error(self):
        # a cli-set entry with no command is a malformed config (schema:
        # command is "required iff cli present") — must be a reportable
        # ValueError, never a raw AttributeError from `None.format(...)`
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command=None, extra={})
        with self.assertRaises(ValueError):
            rs.render_reviewer_command(resolved, "hello")

    def test_malformed_template_raises_value_error_not_key_error(self):
        # {unknown_field} isn't {model}/{prompt}/in extra -> str.format
        # raises KeyError; must surface as a reportable ValueError instead
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex",
                                        command="codex -m {model} {unknown_field} {prompt}",
                                        extra={})
        with self.assertRaises(ValueError):
            rs.render_reviewer_command(resolved, "hello")

    def test_extra_field_colliding_with_reserved_placeholder_raises_value_error(self):
        # a hand-written config entry that defines extra={"prompt": ...} or
        # extra={"model": ...} collides with the reserved keyword args
        # passed to str.format, raising a TypeError that must not escape
        # as a raw crash either
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="codex -m {model} {prompt}",
                                        extra={"prompt": "oops"})
        with self.assertRaises(ValueError):
            rs.render_reviewer_command(resolved, "hello")


class TestProbeReviewerQuota(unittest.TestCase):
    def test_native_entry_is_always_available(self):
        resolved = rs.ResolvedReviewer(key="claude-opus", model="opus", vendor="anthropic",
                                        cli=None, command=None, extra={})
        result = rs.probe_reviewer_quota(resolved, run_fn=lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("should never shell out for a native entry")))
        self.assertTrue(result["available"])

    def test_successful_call_is_available(self):
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="echo ok", extra={})
        class FakeResult:
            returncode = 0
            stdout = "ok\n"
            stderr = ""
        result = rs.probe_reviewer_quota(resolved, run_fn=lambda *a, **k: FakeResult())
        self.assertTrue(result["available"])

    def test_nonzero_exit_is_unavailable(self):
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="false", extra={})
        class FakeResult:
            returncode = 1
            stdout = ""
            stderr = "some error"
        result = rs.probe_reviewer_quota(resolved, run_fn=lambda *a, **k: FakeResult())
        self.assertFalse(result["available"])

    def test_usage_limit_text_is_unavailable_even_on_exit_zero(self):
        # confirmed live: codex can print a usage-limit message and still
        # be worth treating as unavailable regardless of exit code
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.6-luna", vendor="openai",
                                        cli="codex", command="echo 'usage limit reached'", extra={})
        class FakeResult:
            returncode = 0
            stdout = "You have hit your usage limit.\n"
            stderr = ""
        result = rs.probe_reviewer_quota(resolved, run_fn=lambda *a, **k: FakeResult())
        self.assertFalse(result["available"])

    def test_timeout_is_unavailable(self):
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="sleep 999", extra={})
        def fake_run(*a, **k):
            raise subprocess.TimeoutExpired(cmd="sleep 999", timeout=30)
        result = rs.probe_reviewer_quota(resolved, run_fn=fake_run)
        self.assertFalse(result["available"])

    def test_probe_pipes_prompt_via_stdin(self):
        # the probe prompt must reach the child process via stdin
        # (input=), never inlined as a shell argument — this is what
        # makes codex/claude/grok/opencode/cursor-agent's stdin-only
        # command templates (no {prompt} placeholder) actually work
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command="cat", extra={})
        captured = {}
        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""
        def fake_run(*a, **k):
            captured.update(k)
            return FakeResult()
        rs.probe_reviewer_quota(resolved, run_fn=fake_run)
        self.assertEqual(captured.get("input"), "Only say: Hello world!")

    def test_cli_entry_with_missing_command_is_unavailable_not_true(self):
        # regression: a cli-set entry with no command template can never
        # actually be dispatched — must classify as unavailable, not
        # silently `available: True` (which would let it win a ladder
        # walk and only fail later, in real dispatch)
        resolved = rs.ResolvedReviewer(key="codex-gpt", model="gpt-5.2", vendor="openai",
                                        cli="codex", command=None, extra={})
        result = rs.probe_reviewer_quota(resolved, run_fn=lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("should never shell out for a malformed command")))
        self.assertFalse(result["available"])


class TestRefreshQuotaCache(unittest.TestCase):
    def setUp(self):
        self.config = {
            "policy": {"mode": "single", "ladder": ["codex-gpt"]},
            "reviewers": [{"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai",
                           "cli": "codex", "command": "echo ok"}],
        }

    def test_probes_missing_entries(self):
        class FakeResult:
            returncode = 0
            stdout = "ok"
            stderr = ""
        updated = rs.refresh_quota_cache(self.config, ["codex-gpt"], existing={},
                                          ttl_seconds=3600, run_fn=lambda *a, **k: FakeResult())
        self.assertTrue(updated["codex-gpt"]["available"])

    def test_skips_fresh_entries(self):
        existing = {"codex-gpt": {"available": False, "checked_at": time.time()}}
        def fail_if_called(*a, **k):
            raise AssertionError("should not re-probe a fresh entry")
        updated = rs.refresh_quota_cache(self.config, ["codex-gpt"], existing,
                                          ttl_seconds=3600, run_fn=fail_if_called)
        self.assertFalse(updated["codex-gpt"]["available"])  # untouched

    def test_reprobes_stale_entries(self):
        existing = {"codex-gpt": {"available": False, "checked_at": time.time() - 7200}}
        class FakeResult:
            returncode = 0
            stdout = "ok"
            stderr = ""
        updated = rs.refresh_quota_cache(self.config, ["codex-gpt"], existing,
                                          ttl_seconds=3600, run_fn=lambda *a, **k: FakeResult())
        self.assertTrue(updated["codex-gpt"]["available"])  # re-probed, flipped to available


_REPORT_A = """## Review: spec.md
### Document Type
superpowers · design
### CRITICAL
- **Missing field** — Location: §2.1. Required: add the field. Why: breaks downstream.
### HIGH
- **Vague wording** — Location: §3. Required: clarify. Why: ambiguous.
### Status: Issues Found — fix and re-invoke
"""

_REPORT_B = """## Review: spec.md
### Document Type
superpowers · design
### CRITICAL
- **Missing field entirely** — Location: §2.1. Required: define it. Why: undefined behavior.
### MEDIUM
- **Typo** — Location: §1. Required: fix spelling. Why: readability.
### Status: Issues Found — fix and re-invoke
"""


class TestParseFindings(unittest.TestCase):
    def test_extracts_title_location_required_why_and_severity(self):
        findings = rs.parse_findings(_REPORT_A)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["severity"], "CRITICAL")
        self.assertEqual(findings[0]["title"], "Missing field")
        self.assertEqual(findings[0]["location"], "§2.1")
        self.assertEqual(findings[1]["severity"], "HIGH")

    def test_report_with_no_findings_returns_empty_list(self):
        approved = "## Review: spec.md\n### Status: Approved\n"
        self.assertEqual(rs.parse_findings(approved), [])

    def test_cross_document_consistency_bullets_are_not_misattributed(self):
        report = """## Review: a.md, b.md
### HIGH
- **Real high finding** — Location: §1. Required: fix it. Why: reasons.
### Cross-Document Consistency
- **Docs disagree** — Location: §2 vs §3. Required: reconcile. Why: contradiction.
### Status: Issues Found — fix and re-invoke
"""
        findings = rs.parse_findings(report)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["severity"], "HIGH")
        self.assertEqual(findings[1]["severity"], "CROSS-DOC")
        self.assertEqual(findings[1]["title"], "Docs disagree")

    def test_low_severity_bullets_keep_their_own_tag_not_medium(self):
        # regression: a plan-archetype review may legitimately emit a
        # ### LOW heading (review-spec-checklist's LOW/Tooling-Catchable tier);
        # before this fix its bullets fell through to severity None and
        # render_merged_report silently re-labeled them MEDIUM.
        report = """## Review: plan.md
### LOW
- **Trailing whitespace** — Location: §4. Required: trim it. Why: lint noise.
### Status: Issues Found — fix and re-invoke
"""
        findings = rs.parse_findings(report)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "LOW")


class TestReportHasStatus(unittest.TestCase):
    def test_true_when_status_line_present(self):
        self.assertTrue(rs.report_has_status(_REPORT_A))

    def test_false_for_garbage_text(self):
        self.assertFalse(rs.report_has_status("some random CLI error output, no status here"))

    def test_false_for_empty_text(self):
        self.assertFalse(rs.report_has_status(""))


class TestReportDeclaresIssues(unittest.TestCase):
    def test_true_for_issues_found_status(self):
        self.assertTrue(rs.report_declares_issues(_REPORT_A))

    def test_false_for_approved_status(self):
        approved = "## Review: spec.md\n### Status: Approved\n"
        self.assertFalse(rs.report_declares_issues(approved))

    def test_false_for_garbage_text(self):
        self.assertFalse(rs.report_declares_issues("no status line at all"))


class TestMergeFindings(unittest.TestCase):
    def test_same_severity_and_location_merges_into_one_tagged_entry(self):
        merged = rs.merge_findings([("claude-opus", _REPORT_A), ("codex-gpt", _REPORT_B)])
        crit = [f for f in merged if f["severity"] == "CRITICAL"]
        self.assertEqual(len(crit), 1)  # both CRITICAL findings share (CRITICAL, "§2.1")
        self.assertEqual(crit[0]["reviewers"], ["claude-opus", "codex-gpt"])

    def test_distinct_locations_stay_separate_each_tagged_with_its_own_source(self):
        merged = rs.merge_findings([("claude-opus", _REPORT_A), ("codex-gpt", _REPORT_B)])
        high = [f for f in merged if f["severity"] == "HIGH"]
        medium = [f for f in merged if f["severity"] == "MEDIUM"]
        self.assertEqual(high[0]["reviewers"], ["claude-opus"])
        self.assertEqual(medium[0]["reviewers"], ["codex-gpt"])

    def test_single_report_passthrough(self):
        merged = rs.merge_findings([("claude-opus", _REPORT_A)])
        self.assertEqual(len(merged), 2)
        self.assertTrue(all(f["reviewers"] == ["claude-opus"] for f in merged))

    def test_two_distinct_findings_from_the_same_reviewer_at_the_same_location_both_survive(self):
        # regression: a single report can legitimately raise two different
        # findings at the same Location (e.g. two separate HIGH issues both
        # in "§3") — these must never collapse into one just because their
        # (severity, location) pair matches; only cross-reviewer matches at
        # the same (severity, location) should merge.
        report = """## Review: spec.md
### HIGH
- **First issue** — Location: §3. Required: fix A. Why: reason A.
- **Second issue** — Location: §3. Required: fix B. Why: reason B.
### Status: Issues Found — fix and re-invoke
"""
        merged = rs.merge_findings([("claude-opus", report)])
        self.assertEqual(len(merged), 2)
        titles = {f["title"] for f in merged}
        self.assertEqual(titles, {"First issue", "Second issue"})
        self.assertTrue(all(f["reviewers"] == ["claude-opus"] for f in merged))


class TestRenderMergedReport(unittest.TestCase):
    def test_groups_by_severity_and_tags_reviewers(self):
        merged = rs.merge_findings([("claude-opus", _REPORT_A), ("codex-gpt", _REPORT_B)])
        rendered = rs.render_merged_report(merged, "spec.md")
        self.assertIn("### CRITICAL", rendered)
        self.assertIn("### HIGH", rendered)
        self.assertIn("### MEDIUM", rendered)
        self.assertIn("(Reviewers: claude-opus, codex-gpt)", rendered)
        self.assertIn("### Status: Issues Found — fix and re-invoke", rendered)

    def test_no_findings_renders_approved_status(self):
        rendered = rs.render_merged_report([], "spec.md")
        self.assertIn("### Status: Approved", rendered)
        self.assertNotIn("Issues Found", rendered)

    def test_cross_doc_findings_render_under_their_own_heading(self):
        findings = [{"severity": "CROSS-DOC", "title": "Docs disagree", "location": "§2 vs §3",
                     "required": "reconcile", "why": "contradiction", "reviewers": ["claude-opus"]}]
        rendered = rs.render_merged_report(findings, "a.md, b.md")
        self.assertIn("### Cross-Document Consistency", rendered)
        self.assertNotIn("### CROSS-DOC", rendered)

    def test_low_findings_render_under_their_own_heading_not_medium(self):
        findings = [{"severity": "LOW", "title": "Trailing whitespace", "location": "§4",
                     "required": "trim it", "why": "lint noise", "reviewers": ["claude-opus"]}]
        rendered = rs.render_merged_report(findings, "plan.md")
        self.assertIn("### LOW", rendered)
        self.assertNotIn("### MEDIUM", rendered)

    def test_any_source_issues_prevents_false_approved_when_no_findings_parsed(self):
        # regression: a source report can say "Issues Found" while its
        # bullet(s) fail _BULLET_RE's strict single-line shape (e.g. a
        # wrapped Required: clause) — parse_findings then returns nothing
        # for it, but the merge must never report Approved in that case.
        rendered = rs.render_merged_report([], "spec.md", any_source_issues=True)
        self.assertIn("### Status: Issues Found — fix and re-invoke", rendered)
        self.assertNotIn("### Status: Approved", rendered)

    def test_any_source_issues_false_still_renders_approved_when_no_findings(self):
        rendered = rs.render_merged_report([], "spec.md", any_source_issues=False)
        self.assertIn("### Status: Approved", rendered)


class TestMainCli(unittest.TestCase):
    def test_detect_runtimes_prints_json_snapshot(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rs.main(
                ["detect-runtimes"], which_fn=lambda n: None, run_fn=lambda *a, **k: None
            )
        self.assertEqual(code, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIn("clis", parsed)

    def test_detect_runtimes_save_writes_cache_file(self):
        with tempfile.TemporaryDirectory() as d:
            save_path = os.path.join(d, "runtimes.json")
            code = rs.main(["detect-runtimes", "--save", save_path],
                            which_fn=lambda n: None, run_fn=lambda *a, **k: None)
            self.assertEqual(code, 0)
            self.assertIn("clis", rs.cache_read_json(save_path))

    def test_dispatch_execute_reads_prompt_file_and_prints_json_result(self):
        import io
        from contextlib import redirect_stdout
        captured = {}
        def fake_dispatch(candidate, prompt, target_dir, heartbeat_interval, timeout, **kw):
            captured["candidate"] = candidate
            captured["prompt"] = prompt
            captured["target_dir"] = target_dir
            captured["heartbeat_interval"] = heartbeat_interval
            captured["timeout"] = timeout
            captured["kw"] = kw
            return {"cli": candidate["cli"], "model": candidate["model"], "command": "x",
                    "returncode": 0, "stdout": "done", "stderr": "", "timed_out": False}
        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("do the phase task")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(
                    ["dispatch-execute", "--cli", "codex", "--model", "gpt-5.6-sol",
                     "--target-dir", "/scratch/run1", "--prompt-file", prompt_path,
                     "--timeout", "600"],
                    dispatch_execute_fn=fake_dispatch)
        self.assertEqual(code, 0)
        result = json.loads(buf.getvalue())
        self.assertEqual(result["stdout"], "done")
        self.assertEqual(captured["candidate"],
                          {"cli": "codex", "model": "gpt-5.6-sol", "effort": None,
                           "service_tier": None})
        self.assertEqual(captured["prompt"], "do the phase task")
        self.assertEqual(captured["target_dir"], "/scratch/run1")
        self.assertEqual(captured["heartbeat_interval"], 30)  # default
        self.assertEqual(captured["timeout"], 600)
        self.assertIsNone(captured["kw"]["format_block"])

    def test_dispatch_execute_reads_optional_format_block_file(self):
        import io
        from contextlib import redirect_stdout
        captured = {}
        def fake_dispatch(candidate, prompt, target_dir, heartbeat_interval, timeout, **kw):
            captured["kw"] = kw
            return {"cli": candidate["cli"], "model": candidate["model"], "command": "x",
                    "returncode": 0, "stdout": "", "stderr": "", "timed_out": False}
        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            format_path = os.path.join(d, "format.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            with open(format_path, "w", encoding="utf-8") as f:
                f.write("FORMAT-BLOCK-MARKER")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(
                    ["dispatch-execute", "--cli", "grok", "--model", "grok-4.6",
                     "--target-dir", "/scratch/run1", "--prompt-file", prompt_path,
                     "--timeout", "600", "--format-block-file", format_path],
                    dispatch_execute_fn=fake_dispatch)
        self.assertEqual(code, 0)
        self.assertEqual(captured["kw"]["format_block"], "FORMAT-BLOCK-MARKER")

    def test_dispatch_execute_passes_effort_and_service_tier_into_the_candidate(self):
        import io
        from contextlib import redirect_stdout
        captured = {}
        def fake_dispatch(candidate, prompt, target_dir, heartbeat_interval, timeout, **kw):
            captured["candidate"] = candidate
            return {"cli": candidate["cli"], "model": candidate["model"], "command": "x",
                    "returncode": 0, "stdout": "", "stderr": "", "timed_out": False}
        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            with redirect_stdout(io.StringIO()):
                code = rs.main(
                    ["dispatch-execute", "--cli", "codex", "--model", "gpt-5.6-sol",
                     "--target-dir", "/scratch/run1", "--prompt-file", prompt_path,
                     "--timeout", "600", "--effort", "high", "--service-tier", "priority"],
                    dispatch_execute_fn=fake_dispatch)
        self.assertEqual(code, 0)
        self.assertEqual(captured["candidate"]["effort"], "high")
        self.assertEqual(captured["candidate"]["service_tier"], "priority")

    def test_dispatch_execute_surfaces_value_error_on_stderr(self):
        import io
        from contextlib import redirect_stderr
        def raising_dispatch(*a, **kw):
            raise ValueError("no execute-mode command builder for 'gemini' yet")
        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            buf = io.StringIO()
            with redirect_stderr(buf):
                code = rs.main(
                    ["dispatch-execute", "--cli", "gemini", "--model", "gemini-3.1-pro",
                     "--target-dir", "/scratch/run1", "--prompt-file", prompt_path,
                     "--timeout", "600"],
                    dispatch_execute_fn=raising_dispatch)
        self.assertEqual(code, 1)
        self.assertIn("no execute-mode command builder", buf.getvalue())

    def test_dispatch_execute_prompt_file_dash_reads_stdin(self):
        # The exact shape needed to drop this subcommand into GSD's own workflow.cross_ai_command,
        # which always pipes its task prompt into that hook's stdin.
        import io
        from contextlib import redirect_stdout
        captured = {}
        def fake_dispatch(candidate, prompt, target_dir, heartbeat_interval, timeout, **kw):
            captured["prompt"] = prompt
            return {"cli": candidate["cli"], "model": candidate["model"], "command": "x",
                    "returncode": 0, "stdout": "", "stderr": "", "timed_out": False}
        buf = io.StringIO()
        with mock.patch.object(cli.sys, "stdin", io.StringIO("piped prompt text")), \
             redirect_stdout(buf):
            code = rs.main(
                ["dispatch-execute", "--cli", "grok", "--model", "grok-4.6",
                 "--target-dir", "/scratch/run1", "--prompt-file", "-", "--timeout", "600"],
                dispatch_execute_fn=fake_dispatch)
        self.assertEqual(code, 0)
        self.assertEqual(captured["prompt"], "piped prompt text")

    def test_dispatch_execute_stdout_only_prints_raw_stdout_and_real_returncode(self):
        import io
        from contextlib import redirect_stdout
        def fake_dispatch(candidate, prompt, target_dir, heartbeat_interval, timeout, **kw):
            return {"cli": candidate["cli"], "model": candidate["model"], "command": "x",
                    "returncode": 0, "stdout": "# Phase Summary\n...", "stderr": "diagnostics",
                    "timed_out": False}
        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(
                    ["dispatch-execute", "--cli", "codex", "--model", "gpt-5.6-sol",
                     "--target-dir", "/scratch/run1", "--prompt-file", prompt_path,
                     "--timeout", "600", "--stdout-only"],
                    dispatch_execute_fn=fake_dispatch)
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue(), "# Phase Summary\n...")
        self.assertNotIn("diagnostics", buf.getvalue())  # stderr never leaks into this stream

    def test_dispatch_execute_stdout_only_propagates_nonzero_returncode(self):
        import io
        from contextlib import redirect_stdout
        def fake_dispatch(candidate, prompt, target_dir, heartbeat_interval, timeout, **kw):
            return {"cli": candidate["cli"], "model": candidate["model"], "command": "x",
                    "returncode": 3, "stdout": "partial", "stderr": "", "timed_out": False}
        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            with redirect_stdout(io.StringIO()):
                code = rs.main(
                    ["dispatch-execute", "--cli", "codex", "--model", "gpt-5.6-sol",
                     "--target-dir", "/scratch/run1", "--prompt-file", prompt_path,
                     "--timeout", "600", "--stdout-only"],
                    dispatch_execute_fn=fake_dispatch)
        self.assertEqual(code, 3)

    def test_cache_path_honors_xdg_cache_home(self):
        import io
        from contextlib import redirect_stdout
        env = {"XDG_CACHE_HOME": "/x/cache"}
        buf = io.StringIO()
        with mock.patch.object(rs.os, "environ", env), redirect_stdout(buf):
            code = rs.main(["cache-path", "--kind", "runtimes"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "/x/cache/ai-kit/spec/runtimes.json")

    def test_cache_path_quota_kind(self):
        import io
        from contextlib import redirect_stdout
        env = {"HOME": "/home/u"}
        buf = io.StringIO()
        with mock.patch.object(rs.os, "environ", env), redirect_stdout(buf):
            code = rs.main(["cache-path", "--kind", "quota"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "/home/u/.cache/ai-kit/spec/quota.json")

    def test_detect_runtimes_if_stale_skips_detection_when_fresh(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "runtimes.json")
            rs.cache_write_json(path, {"clis": {}})  # just written -> fresh
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            probe_calls = []
            with redirect_stdout(buf):
                code = rs.main(["detect-runtimes", "--if-stale", path],
                                which_fn=lambda n: probe_calls.append(n) or None,
                                run_fn=lambda *a, **k: None)
            self.assertEqual(code, 0)
            self.assertEqual(probe_calls, [])  # detection never ran
            self.assertEqual(json.loads(buf.getvalue()), {})

    def test_detect_runtimes_if_stale_redetects_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "runtimes.json")  # never written -> stale
            code = rs.main(["detect-runtimes", "--if-stale", path],
                            which_fn=lambda n: None, run_fn=lambda *a, **k: None)
            self.assertEqual(code, 0)
            self.assertIn("clis", rs.cache_read_json(path))

    def test_resolve_reviewers_uses_cfg_resolve_local_global_merge(self):
        # regression test for the CRITICAL bug: resolve-reviewers must go
        # through cfg_resolve (local/global + strategy), not a single
        # --config path — write ONLY a local file that overrides one field
        # of a global-declared reviewer, and confirm the override lands.
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            os.makedirs(os.path.join(home, ".config", "ai-kit"))
            rs.cfg_write_toml(os.path.join(home, ".config", "ai-kit", "review-spec.toml"), {
                "policy": {"mode": "single", "ladder": ["codex-gpt"]},
                "reviewers": [{"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai"}],
            })
            os.makedirs(os.path.join(cwd, ".aikit"))
            with open(os.path.join(cwd, ".aikit", "review-spec.toml"), "w", encoding="utf-8") as f:
                f.write('[[reviewers]]\nkey = "codex-gpt"\nmodel = "gpt-5.2-mini"\n')
            quota_path = os.path.join(cwd, "quota.json")
            rs.cache_write_json(quota_path, {})
            buf = io.StringIO()
            env = {"HOME": home}
            with mock.patch.object(rs.os, "environ", env), redirect_stdout(buf):
                code = rs.main(["resolve-reviewers", "--cwd", cwd, "--quota-path", quota_path,
                                 "--source-vendor", "anthropic", "--cross-ai"])
            self.assertEqual(code, 0)
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed[0]["model"], "gpt-5.2-mini")  # local override applied

    def test_probe_quota_refreshes_stale_entries_and_writes_cache(self):
        with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            os.makedirs(os.path.join(home, ".config", "ai-kit"))
            rs.cfg_write_toml(os.path.join(home, ".config", "ai-kit", "review-spec.toml"), {
                "policy": {"mode": "single", "ladder": ["codex-gpt"]},
                "reviewers": [{"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai",
                               "cli": "codex", "command": "echo ok"}],
            })
            quota_path = os.path.join(cwd, "quota.json")
            env = {"HOME": home}
            fake_run = mock.Mock(
                return_value=subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="ok", stderr=""
                )
            )
            with mock.patch.object(rs.os, "environ", env):
                code = rs.main(
                    ["probe-quota", "--cwd", cwd, "--quota-path", quota_path], run_fn=fake_run
                )
            self.assertEqual(code, 0)
            written = rs.cache_read_json(quota_path)
            self.assertTrue(written["codex-gpt"]["available"])
            fake_run.assert_called()  # never shells out to a real "echo ok"

    def test_merge_reports_reads_files_and_prints_markdown(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            path_a = os.path.join(d, "a.md")
            path_b = os.path.join(d, "b.md")
            with open(path_a, "w", encoding="utf-8") as f:
                f.write(_REPORT_A)
            with open(path_b, "w", encoding="utf-8") as f:
                f.write(_REPORT_B)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["merge-reports", "--doc-paths", "spec.md",
                                 "claude-opus=" + path_a, "codex-gpt=" + path_b])
            self.assertEqual(code, 0)
            self.assertIn("### CRITICAL", buf.getvalue())

    def test_merge_reports_fails_closed_on_a_non_conforming_report(self):
        # regression: a garbage/failed external CLI report (no Status
        # line) must never silently merge into a false Approved
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            path_a = os.path.join(d, "a.md")
            path_b = os.path.join(d, "b.md")
            with open(path_a, "w", encoding="utf-8") as f:
                f.write(_REPORT_A)
            with open(path_b, "w", encoding="utf-8") as f:
                f.write("codex: error: usage limit exceeded\n")  # no ### Status: line
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["merge-reports", "--doc-paths", "spec.md",
                                 "claude-opus=" + path_a, "codex-gpt=" + path_b])
            self.assertEqual(code, 0)
            self.assertNotIn("### Status:", buf.getvalue())
            self.assertIn("codex-gpt", buf.getvalue())

    def test_render_command_fills_the_indexed_reviewer(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump([{"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai",
                            "cli": "codex", "command": "codex exec -m {model} {prompt}",
                            "extra": {}}], f)
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("hello")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["render-command", "--reviewers-json", reviewers_path,
                                 "--index", "0", "--prompt-file", prompt_path])
            self.assertEqual(code, 0)
            self.assertEqual(buf.getvalue().strip(), "codex exec -m gpt-5.2 hello")

    def test_render_command_returns_nonzero_on_malformed_template(self):
        with tempfile.TemporaryDirectory() as d:
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump([{"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai",
                            "cli": "codex", "command": None, "extra": {}}], f)
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("hello")
            code = rs.main(["render-command", "--reviewers-json", reviewers_path,
                             "--index", "0", "--prompt-file", prompt_path])
            self.assertEqual(code, 1)

    def test_render_toml_prints_only_without_out(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            json_path = os.path.join(d, "config.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"policy": {"mode": "single"}, "reviewers": []}, f)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["render-toml", "--json-config", json_path])
            self.assertEqual(code, 0)
            self.assertIn("mode", buf.getvalue())
            self.assertFalse(os.path.exists(os.path.join(d, "review-spec.toml")))

    def test_render_toml_with_out_writes_via_cfg_write_toml(self):
        with tempfile.TemporaryDirectory() as d:
            json_path = os.path.join(d, "config.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"policy": {"mode": "double", "ladder": ["a"]}, "reviewers": []}, f)
            out_path = os.path.join(d, "nested", "review-spec.toml")
            code = rs.main(["render-toml", "--json-config", json_path, "--out", out_path])
            self.assertEqual(code, 0)
            written = rs.cfg_load_toml(out_path)
            self.assertEqual(written["policy"]["mode"], "double")

    def test_infer_vendor_prints_matched_vendor(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rs.main(["infer-vendor", "--model", "kimi-k3-high"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue()), {"vendor": "moonshot"})

    def test_infer_vendor_prints_null_when_unmatched(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rs.main(["infer-vendor", "--model", "auto"])
        self.assertEqual(code, 0)
        self.assertIsNone(json.loads(buf.getvalue())["vendor"])

    def test_build_command_prints_the_built_template(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rs.main(["build-command", "--cli", "codex", "--effort", "high"])
        self.assertEqual(code, 0)
        self.assertIn("model_reasoning_effort='\"high\"'", buf.getvalue())

    def test_build_command_unknown_cli_exits_nonzero(self):
        import io
        from contextlib import redirect_stderr
        buf = io.StringIO()
        with redirect_stderr(buf):
            code = rs.main(["build-command", "--cli", "nonexistent-cli"])
        self.assertEqual(code, 1)
        self.assertIn("no command builder", buf.getvalue())

    def test_build_command_cursor_agent_passes_mode_flag(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rs.main(["build-command", "--cli", "cursor-agent", "--mode", "ask"])
        self.assertEqual(code, 0)
        self.assertIn("--mode ask", buf.getvalue())

    def test_build_model_id_applies_cursor_agent_overrides(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rs.main(["build-model-id", "--cli", "cursor-agent",
                             "--base-model", "glm-5.2-high", "--fast", "true"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "glm-5.2-high[fast=true]")

    def test_build_model_id_non_cursor_cli_returns_base_model(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rs.main(["build-model-id", "--cli", "codex", "--base-model", "gpt-5.2",
                             "--effort", "high"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "gpt-5.2")

    def test_group_models_reads_the_named_clis_models_from_a_runtimes_snapshot(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            runtimes_path = os.path.join(d, "runtimes.json")
            rs.cache_write_json(runtimes_path, {
                "clis": {"cursor-agent": {"installed": True,
                                           "models": ["glm-5.2-high", "glm-5.2-max"]}},
            })
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["group-models", "--runtimes-json", runtimes_path,
                                 "--cli", "cursor-agent"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(buf.getvalue()),
                              {"glm-5.2": ["glm-5.2-high", "glm-5.2-max"]})

    def test_group_models_unknown_cli_or_missing_file_yields_empty_groups(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            runtimes_path = os.path.join(d, "does-not-exist.json")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["group-models", "--runtimes-json", runtimes_path,
                                 "--cli", "cursor-agent"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(buf.getvalue()), {})

    def test_check_reviewer_native_entry_is_always_available(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rs.main(["check-reviewer", "--key", "session-default"],
                            run_fn=lambda *a, **k: (_ for _ in ()).throw(
                                AssertionError("should never shell out for a native entry")))
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(buf.getvalue())["available"])

    def test_check_reviewer_runs_the_real_command_and_reports_detail(self):
        import io
        from contextlib import redirect_stdout
        class FakeResult:
            returncode = 1
            stdout = ""
            stderr = "ActionRequiredError: Named models unavailable"
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rs.main(
                ["check-reviewer", "--key", "cursor-glm", "--model", "glm-5.2-high",
                 "--vendor", "zhipu", "--cli", "cursor-agent",
                 "--command", "cursor-agent -p {prompt} --output-format text --model {model}"],
                run_fn=lambda *a, **k: FakeResult(),
            )
        self.assertEqual(code, 0)
        parsed = json.loads(buf.getvalue())
        self.assertFalse(parsed["available"])
        self.assertIn("ActionRequiredError", parsed["detail"])

    def test_check_reviewer_passes_extra_json_to_command_template(self):
        import io
        from contextlib import redirect_stdout
        class FakeResult:
            returncode = 0
            stdout = "ok"
            stderr = ""
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rs.main(
                ["check-reviewer", "--key", "codex-gpt", "--model", "gpt-5.2",
                 "--cli", "codex", "--command", "codex -m {model} -c effort={effort} {prompt}",
                 "--extra-json", '{"effort": "high"}'],
                run_fn=lambda *a, **k: FakeResult(),
            )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(buf.getvalue())["available"])


class TestMainCliDetectTools(unittest.TestCase):
    def test_detect_tools_subcommand_prints_json(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(["detect-tools"], which_fn=lambda name: "/usr/bin/x" if name == "rg" else None)
        result = json.loads(buf.getvalue())
        self.assertEqual(
            result,
            {"rg": True, "sd": False, "bat": False, "eza": False, "fd": False, "codegraph": False},
        )


class TestBuildToolingGuidance(unittest.TestCase):
    def test_empty_when_nothing_confirmed(self):
        result = tooling_guidance.build_tooling_guidance(
            "grok", tool_availability={}, agents_tooling_path=None, codegraph_registered=False)
        self.assertEqual(result, "")

    def test_points_to_agents_tooling_file_when_present(self):
        result = tooling_guidance.build_tooling_guidance(
            "claude", tool_availability={}, agents_tooling_path="/home/u/.agents/AGENTS-TOOLING.md",
            codegraph_registered=False)
        self.assertIn("/home/u/.agents/AGENTS-TOOLING.md", result)

    def test_mentions_codegraph_explore_only_when_registered(self):
        result = tooling_guidance.build_tooling_guidance(
            "claude", tool_availability={"codegraph": True}, agents_tooling_path=None,
            codegraph_registered=True)
        self.assertIn("codegraph_explore", result)

    def test_omits_codegraph_explore_when_not_registered_even_if_binary_present(self):
        result = tooling_guidance.build_tooling_guidance(
            "grok", tool_availability={"codegraph": True}, agents_tooling_path=None,
            codegraph_registered=False)
        self.assertNotIn("codegraph_explore", result)

    def test_omits_codegraph_explore_when_registered_but_binary_not_detected(self):
        result = tooling_guidance.build_tooling_guidance(
            "claude", tool_availability={"codegraph": False}, agents_tooling_path=None,
            codegraph_registered=True)
        self.assertNotIn("codegraph_explore", result)

    def test_grok_never_gets_codegraph_explore_even_with_inconsistent_true_inputs(self):
        result = tooling_guidance.build_tooling_guidance(
            "grok", tool_availability={"codegraph": True}, agents_tooling_path=None,
            codegraph_registered=True)
        self.assertNotIn("codegraph_explore", result)

    def test_resolve_shared_tooling_reference_path_points_to_a_real_file(self):
        path = tooling_guidance.resolve_shared_tooling_reference_path()
        self.assertTrue(path.endswith(
            os.path.join("references", "tooling-guidance.md")))
        self.assertTrue(os.path.isfile(path))

    def test_build_tooling_guidance_always_includes_shared_reference_when_given(self):
        guidance = tooling_guidance.build_tooling_guidance(
            "grok", {}, None, False, shared_reference_path="/fake/tooling-guidance.md")
        self.assertIn("Read /fake/tooling-guidance.md", guidance)

    def test_build_tooling_guidance_omits_shared_reference_line_when_not_given(self):
        guidance = tooling_guidance.build_tooling_guidance("grok", {}, None, False)
        self.assertNotIn("tooling-guidance.md", guidance)

    def test_surfaces_tool_availability_as_a_named_variable_the_reviewer_can_check(self):
        # ai-kit-spec-review-checklist's legacy-tool-usage rule is gated on the modern
        # equivalent being "confirmed in tool_availability" -- the map has to actually reach
        # the dispatched reviewer under that name or the rule can never fire.
        guidance = tooling_guidance.build_tooling_guidance(
            "grok", {"rg": True, "fd": False}, None, False)
        self.assertIn('TOOL_AVAILABILITY = {"fd":false,"rg":true}', guidance)

    def test_omits_the_tool_availability_line_when_nothing_was_detected(self):
        guidance = tooling_guidance.build_tooling_guidance("grok", {}, None, False)
        self.assertNotIn("TOOL_AVAILABILITY", guidance)

    def test_paths_are_emitted_as_named_variables_not_only_bare_paths(self):
        guidance = tooling_guidance.build_tooling_guidance(
            "claude", {}, "/home/u/.agents/AGENTS-TOOLING.md", False,
            shared_reference_path="/fake/tooling-guidance.md")
        self.assertIn("SHARED_TOOLING_PATH = /fake/tooling-guidance.md", guidance)
        self.assertIn("AGENTS_TOOLING_PATH = /home/u/.agents/AGENTS-TOOLING.md", guidance)


class TestDispatchGuidance(unittest.TestCase):
    def test_model_selection_override_names_the_resolved_dispatch(self):
        result = dispatch_guidance.build_model_selection_override_guidance(
            "codex, model gpt-5.6-sol")
        self.assertIn("codex, model gpt-5.6-sol", result)
        self.assertIn("do not re-select", result)

    def test_incremental_progress_guidance_is_nonempty_and_stable(self):
        result = dispatch_guidance.build_incremental_progress_guidance()
        self.assertIn("incrementally", result)

    def test_failure_reporting_guidance_forbids_false_success(self):
        result = dispatch_guidance.build_failure_reporting_guidance()
        self.assertIn("never report success", result)

    def test_output_format_guidance_wraps_the_given_block_verbatim(self):
        result = dispatch_guidance.build_output_format_guidance("---\nphase: x\n---")
        self.assertIn("---\nphase: x\n---", result)
        self.assertIn("MUST match this exact", result)

    def test_composed_guidance_includes_all_four_sections_when_format_block_given(self):
        result = dispatch_guidance.build_dispatch_reinforcement_guidance(
            "codex, model gpt-5.6-sol", "FORMAT-BLOCK-MARKER")
        self.assertIn("codex, model gpt-5.6-sol", result)
        self.assertIn("incrementally", result)
        self.assertIn("never report success", result)
        self.assertIn("FORMAT-BLOCK-MARKER", result)

    def test_composed_guidance_omits_output_format_section_when_block_is_none(self):
        result = dispatch_guidance.build_dispatch_reinforcement_guidance(
            "claude, tier opus", None)
        self.assertIn("claude, tier opus", result)
        self.assertNotIn("MUST match this exact", result)


class TestBuildSoftConfinementGuidance(unittest.TestCase):
    def test_names_target_dir_as_the_only_writable_location(self):
        result = execute_dispatch.build_soft_confinement_guidance("/scratch/run1")
        self.assertIn("/scratch/run1", result)
        self.assertIn("NO operating-system-level write confinement", result)


class TestDispatchExecute(unittest.TestCase):
    def test_native_candidate_raises_rather_than_dispatch(self):
        candidate = {"cli": None, "model": "opus", "key": "opus-native"}
        with self.assertRaises(ValueError) as ctx:
            execute_dispatch.dispatch_execute(candidate, "do the task", "/scratch/run1", 30, 600)
        self.assertIn("native", str(ctx.exception).lower())

    def test_builds_real_command_and_dispatches_with_composed_prompt(self):
        candidate = {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol"}
        captured = {}
        def fake_dispatch(command, prompt, heartbeat_interval, timeout):
            captured["command"] = command
            captured["prompt"] = prompt
            captured["heartbeat_interval"] = heartbeat_interval
            captured["timeout"] = timeout
            return {"returncode": 0, "stdout": "done", "stderr": "", "timed_out": False}
        result = execute_dispatch.dispatch_execute(
            candidate, "do the task", "/scratch/run1", 30, 600, dispatch_fn=fake_dispatch)
        self.assertEqual(
            captured["command"],
            "codex exec --sandbox workspace-write --skip-git-repo-check -C /scratch/run1 "
            "-m gpt-5.6-sol")
        self.assertIn("codex, model gpt-5.6-sol", captured["prompt"])
        self.assertIn("do not re-select", captured["prompt"])
        self.assertIn("incrementally", captured["prompt"])
        self.assertTrue(captured["prompt"].endswith("do the task"))
        self.assertEqual(captured["heartbeat_interval"], 30)
        self.assertEqual(captured["timeout"], 600)
        self.assertEqual(result["cli"], "codex")
        self.assertEqual(result["model"], "gpt-5.6-sol")
        self.assertEqual(result["stdout"], "done")

    def test_no_hard_sandbox_cli_gets_soft_confinement_guidance_appended(self):
        candidate = {"cli": "cursor-agent", "model": "auto", "key": "cursor-agent/auto"}
        captured = {}
        def fake_dispatch(command, prompt, heartbeat_interval, timeout):
            captured["prompt"] = prompt
            return {"returncode": 0, "stdout": "", "stderr": "", "timed_out": False}
        execute_dispatch.dispatch_execute(
            candidate, "do the task", "/scratch/run1", 30, 600, dispatch_fn=fake_dispatch)
        self.assertIn("NO operating-system-level write confinement", captured["prompt"])
        self.assertIn("/scratch/run1", captured["prompt"])

    def test_hard_sandbox_cli_gets_no_soft_confinement_guidance(self):
        candidate = {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol"}
        captured = {}
        def fake_dispatch(command, prompt, heartbeat_interval, timeout):
            captured["prompt"] = prompt
            return {"returncode": 0, "stdout": "", "stderr": "", "timed_out": False}
        execute_dispatch.dispatch_execute(
            candidate, "do the task", "/scratch/run1", 30, 600, dispatch_fn=fake_dispatch)
        self.assertNotIn("NO operating-system-level write confinement", captured["prompt"])

    def test_includes_tool_guidance_when_provided(self):
        candidate = {"cli": "claude", "model": "sonnet", "key": "claude/sonnet"}
        captured = {}
        def fake_dispatch(command, prompt, heartbeat_interval, timeout):
            captured["prompt"] = prompt
            return {"returncode": 0, "stdout": "", "stderr": "", "timed_out": False}
        execute_dispatch.dispatch_execute(
            candidate, "do the task", "/scratch/run1", 30, 600,
            tool_availability={"codegraph": True}, agents_tooling_path="/repo/AGENTS-TOOLING.md",
            codegraph_registered=True, dispatch_fn=fake_dispatch)
        self.assertIn("/repo/AGENTS-TOOLING.md", captured["prompt"])
        self.assertIn("codegraph_explore", captured["prompt"])

    def test_includes_output_format_block_when_given(self):
        candidate = {"cli": "grok", "model": "grok-4.6", "key": "grok/grok-4.6"}
        captured = {}
        def fake_dispatch(command, prompt, heartbeat_interval, timeout):
            captured["prompt"] = prompt
            return {"returncode": 0, "stdout": "", "stderr": "", "timed_out": False}
        execute_dispatch.dispatch_execute(
            candidate, "do the task", "/scratch/run1", 30, 600,
            format_block="FORMAT-BLOCK-MARKER", dispatch_fn=fake_dispatch)
        self.assertIn("FORMAT-BLOCK-MARKER", captured["prompt"])

    def test_threads_effort_and_service_tier_from_the_candidate_into_the_real_builder(self):
        candidate = {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                     "effort": "high", "service_tier": "priority"}
        captured = {}
        def fake_dispatch(command, prompt, heartbeat_interval, timeout):
            captured["command"] = command
            return {"returncode": 0, "stdout": "", "stderr": "", "timed_out": False}
        execute_dispatch.dispatch_execute(
            candidate, "do the task", "/scratch/run1", 30, 600, dispatch_fn=fake_dispatch)
        self.assertIn("-c model_reasoning_effort='\"high\"'", captured["command"])
        self.assertIn("-c service_tier='\"priority\"'", captured["command"])


class TestEnsureCodegraphRegistered(unittest.TestCase):
    def test_skips_install_when_already_registered(self):
        calls = []
        detection.ensure_codegraph_registered(
            "claude",
            run_fn=lambda *a, **k: calls.append(a) or unittest.mock.MagicMock(returncode=0),
            check_fn=lambda cli: True)
        self.assertEqual(calls, [])

    def test_installs_when_not_registered(self):
        calls = []
        def fake_run(cmd, **k):
            calls.append(cmd)
            return unittest.mock.MagicMock(returncode=0)
        detection.ensure_codegraph_registered("claude", run_fn=fake_run, check_fn=lambda cli: False)
        self.assertEqual(len(calls), 1)
        self.assertIn("--location=global", calls[0])
        self.assertIn("--target=claude", calls[0])
        self.assertIn("--yes", calls[0])

    def test_grok_never_attempts_install(self):
        calls = []
        result = detection.ensure_codegraph_registered(
            "grok", run_fn=lambda *a, **k: calls.append(a),
            check_fn=lambda cli: False)
        self.assertEqual(calls, [])
        self.assertFalse(result)


class TestBuildCodegraphIndexCommand(unittest.TestCase):
    def test_tries_sync_then_init(self):
        cmd = detection.build_codegraph_index_command("/repo/root")
        self.assertIn("cd /repo/root", cmd)
        self.assertIn("codegraph sync || codegraph init", cmd)

    def test_target_dir_with_shell_metacharacters_is_quoted(self):
        cmd = detection.build_codegraph_index_command("/tmp/a b$(x)")
        self.assertIn(shlex.quote("/tmp/a b$(x)"), cmd)

    def test_minimum_timeout_constant(self):
        self.assertEqual(detection.CODEGRAPH_INDEX_TIMEOUT_SECONDS, 15)


class TestDispatchWithHeartbeat(unittest.TestCase):
    def test_default_print_fn_writes_heartbeat_to_stderr_not_stdout(self):
        # A caller capturing stdout as a real artifact (e.g. dispatch-execute's --stdout-only
        # mode, used as a drop-in GSD workflow.cross_ai_command) must never see heartbeat text
        # mixed into it -- the default print_fn must write to stderr, never stdout.
        import io
        from contextlib import redirect_stderr, redirect_stdout

        class FakeProcess:
            def __init__(self):
                self.stdin = unittest.mock.MagicMock()
                self.returncode = 0
                self._attempts = 0

            def communicate(self, input=None, timeout=None):
                self._attempts += 1
                if self._attempts < 2:
                    raise subprocess.TimeoutExpired(cmd="x", timeout=timeout)
                return ("done", "")

        fake_time = iter([0, 1, 2]).__next__
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            dispatch.dispatch_with_heartbeat(
                "echo hi", "prompt text", heartbeat_interval=1, timeout=30,
                popen_fn=lambda *a, **k: FakeProcess(), time_fn=fake_time)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("still running", err.getvalue())

    def test_prints_timestamped_heartbeat_while_process_runs(self):
        class FakeProcess:
            def __init__(self):
                self.stdin = unittest.mock.MagicMock()
                self.returncode = 0
                self._attempts = 0

            def communicate(self, input=None, timeout=None):
                self._attempts += 1
                if self._attempts < 3:
                    raise subprocess.TimeoutExpired(cmd="x", timeout=timeout)
                return ("done", "")

        printed = []
        fake_time = iter([0, 1, 2, 3]).__next__
        dispatch.dispatch_with_heartbeat(
            "echo hi", "prompt text", heartbeat_interval=1, timeout=30,
            popen_fn=lambda *a, **k: FakeProcess(), time_fn=fake_time,
            print_fn=printed.append)
        self.assertTrue(any("still running" in line for line in printed))

    def test_delivers_prompt_via_communicate_never_via_manual_stdin_write(self):
        class FakeProcess:
            returncode = 0
            def __init__(self):
                self.stdin = unittest.mock.MagicMock()
            def communicate(self, input=None, timeout=None):
                assert input == "the prompt", "prompt must be delivered via communicate(input=...)"
                return ("done", "")
        proc = FakeProcess()
        dispatch.dispatch_with_heartbeat(
            "cat", "the prompt", heartbeat_interval=60, timeout=30,
            popen_fn=lambda *a, **k: proc, print_fn=lambda *a: None)
        proc.stdin.write.assert_not_called()

    def test_returns_stdout_stderr_and_returncode_on_clean_completion(self):
        class FakeProcess:
            returncode = 0
            stdin = unittest.mock.MagicMock()

            def communicate(self, input=None, timeout=None):
                return ("all good", "")

        result = dispatch.dispatch_with_heartbeat(
            "echo hi", "prompt", heartbeat_interval=60, timeout=30,
            popen_fn=lambda *a, **k: FakeProcess(), print_fn=lambda *a: None)
        self.assertEqual(result, {"returncode": 0, "stdout": "all good",
                                   "stderr": "", "timed_out": False})

    def test_kills_process_group_and_still_returns_output_collected_before_the_kill(self):
        class FakeProcess:
            returncode = None
            stdin = unittest.mock.MagicMock()
            pid = 1234

            def __init__(self):
                self.killed = False

            def communicate(self, input=None, timeout=None):
                if self.killed:
                    self.returncode = -9
                    return ("partial output before kill", "")
                raise subprocess.TimeoutExpired(cmd="x", timeout=timeout)

        proc = FakeProcess()
        killed_targets = []

        def fake_kill_fn(p):
            killed_targets.append(p)
            p.killed = True

        result = dispatch.dispatch_with_heartbeat(
            "sleep 999", "prompt", heartbeat_interval=1000, timeout=1,
            popen_fn=lambda *a, **k: proc, time_fn=iter([0, 2]).__next__,
            kill_fn=fake_kill_fn, print_fn=lambda *a: None)
        self.assertTrue(result["timed_out"])
        self.assertEqual(killed_targets, [proc])
        self.assertEqual(result["stdout"], "partial output before kill")


class TestDispatchWithPolling(unittest.TestCase):
    class _FakeProc:
        def __init__(self, returncode_after_polls):
            self._polls_left = returncode_after_polls
            self.returncode = None
            self.pid = 4242
            self.killed = False

        def poll(self):
            if self._polls_left <= 0:
                self.returncode = 0
            else:
                self._polls_left -= 1
            return self.returncode

        def wait(self, timeout=None):
            return self.returncode

    def _fake_kill(self, proc):
        proc.killed = True
        proc.returncode = -9

    def test_single_tier_success_writes_prompt_and_returns_captured_output(self):
        written = {}

        def fake_popen(command, shell, stdin, stdout, stderr, start_new_session):
            written["command"] = command
            written["prompt"] = stdin.read()
            # flush(): a REAL child writes straight to the dup'd fd, so its output is on
            # disk the moment it is produced; a fake that writes through this Python file
            # object has to flush to emulate that (dispatch_with_polling deliberately does
            # not flush a handle it never writes to itself).
            stdout.write(b"real report text")
            stdout.flush()
            stderr.write(b"")
            return self._FakeProc(returncode_after_polls=1)

        times = iter([0.0, 10.0, 20.0])
        result = dispatch.dispatch_with_polling(
            "echo hi", "the prompt", timeout_tiers=[600], poll_interval=50,
            popen_fn=fake_popen, time_fn=lambda: next(times), sleep_fn=lambda s: None,
            kill_fn=self._fake_kill, print_fn=lambda *a: None)

        self.assertEqual(written["command"], "echo hi")
        self.assertEqual(written["prompt"], b"the prompt")
        self.assertEqual(result["stdout"], "real report text")
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(result["timed_out"])
        self.assertEqual(result["tiers_tried"], 1)
        self.assertEqual(result["final_timeout"], 600)

    def test_first_tier_times_out_and_escalates_to_second_tier_which_succeeds(self):
        attempts = []
        killed = []

        def recording_kill(proc):
            killed.append(proc)
            self._fake_kill(proc)

        def fake_popen(command, shell, stdin, stdout, stderr, start_new_session):
            attempt_index = len(attempts)
            attempts.append(attempt_index)
            if attempt_index == 0:
                # Never finishes within tier 1's budget -- polls_left huge.
                return self._FakeProc(returncode_after_polls=10_000)
            stdout.write(b"finished on tier 2")
            stdout.flush()
            return self._FakeProc(returncode_after_polls=0)

        # Tier 1 (timeout=10): start=0.0, first poll check at elapsed=15 (>10 -> timeout).
        # Tier 2 (timeout=600): start=15.0, next call elapsed=16 (<600 -> proceed), proc
        # finishes on first poll() call (returncode_after_polls=0).
        times = iter([0.0, 15.0, 15.0, 16.0])
        result = dispatch.dispatch_with_polling(
            "slow-cmd", "p", timeout_tiers=[10, 600], poll_interval=50,
            popen_fn=fake_popen, time_fn=lambda: next(times), sleep_fn=lambda s: None,
            kill_fn=recording_kill, print_fn=lambda *a: None)

        self.assertEqual(len(attempts), 2)
        # The tier-1 process must actually have been KILLED, not merely abandoned -- a killed
        # process group is the whole point of the escalation (a survivor would keep burning
        # quota against the same prompt while tier 2 runs).
        self.assertEqual([p.killed for p in killed], [True])
        self.assertFalse(result["timed_out"])
        self.assertEqual(result["tiers_tried"], 2)
        self.assertEqual(result["final_timeout"], 600)
        self.assertEqual(result["stdout"], "finished on tier 2")

    def test_all_tiers_exhausted_returns_timed_out_with_last_tier_partial_output(self):
        def fake_popen(command, shell, stdin, stdout, stderr, start_new_session):
            stdout.write(b"partial from last tier")
            stdout.flush()
            return self._FakeProc(returncode_after_polls=10_000)

        times = iter([0.0, 15.0, 15.0, 25.0])
        result = dispatch.dispatch_with_polling(
            "never-finishes", "p", timeout_tiers=[10, 10], poll_interval=50,
            popen_fn=fake_popen, time_fn=lambda: next(times), sleep_fn=lambda s: None,
            kill_fn=self._fake_kill, print_fn=lambda *a: None)

        self.assertTrue(result["timed_out"])
        self.assertEqual(result["tiers_tried"], 2)
        self.assertEqual(result["stdout"], "partial from last tier")

    def test_progress_lines_report_byte_growth_between_polls(self):
        printed = []

        def fake_popen(command, shell, stdin, stdout, stderr, start_new_session):
            stdout.write(b"x" * 100)
            stdout.flush()
            return self._FakeProc(returncode_after_polls=10_000)

        # Two poll checks before the tier's own timeout hits.
        times = iter([0.0, 5.0, 8.0, 12.0])
        dispatch.dispatch_with_polling(
            "cmd", "p", timeout_tiers=[10], poll_interval=3,
            popen_fn=fake_popen, time_fn=lambda: next(times), sleep_fn=lambda s: None,
            kill_fn=self._fake_kill, print_fn=lambda *a: printed.append(" ".join(map(str, a))))

        self.assertTrue(any("100 bytes" in line or "total 100" in line for line in printed))

    def test_finished_process_is_noticed_without_waiting_a_full_poll_interval(self):
        # Regression: the loop used to sleep min(poll_interval, remaining) between poll()
        # checks, so a child that exited in one second still went unnoticed for up to 150s.
        # poll_interval must govern the PROGRESS LINE only, never completion detection.
        sleeps = []
        printed = []
        ticks = {"t": 0.0}

        def fake_time():
            now = ticks["t"]
            ticks["t"] += 1.0
            return now

        def fake_popen(command, shell, stdin, stdout, stderr, start_new_session):
            stdout.write(b"done fast")
            stdout.flush()
            return self._FakeProc(returncode_after_polls=2)

        result = dispatch.dispatch_with_polling(
            "fast-cmd", "p", timeout_tiers=[600], poll_interval=150,
            popen_fn=fake_popen, time_fn=fake_time, sleep_fn=sleeps.append,
            kill_fn=self._fake_kill, print_fn=lambda *a: printed.append(" ".join(map(str, a))))

        self.assertFalse(result["timed_out"])
        self.assertEqual(result["stdout"], "done fast")
        self.assertTrue(sleeps, "expected the loop to have slept at least once")
        self.assertLessEqual(max(sleeps), 5, "each wait must be a short slice, not poll_interval")
        self.assertLessEqual(sum(sleeps), 10,
                             "a process finishing in seconds must not cost a whole poll_interval")
        self.assertEqual(printed, [],
                         "no progress line is due before poll_interval seconds have elapsed")

    def test_empty_timeout_tiers_raises_value_error_instead_of_returning_none(self):
        # Reachable from a config with `timeout_tiers = []`; returning None used to surface
        # downstream as an opaque TypeError where the CLI subscripts result["stdout"].
        with self.assertRaises(ValueError):
            dispatch.dispatch_with_polling(
                "cmd", "p", timeout_tiers=[], popen_fn=lambda *a, **k: None)


class TestBuildExecuteCommand(unittest.TestCase):
    def test_codex_uses_workspace_write_sandbox_with_target_dir(self):
        cmd = commands.build_execute_command("codex", target_dir="/scratch/run1")
        self.assertIn("--sandbox workspace-write", cmd)
        self.assertIn("--skip-git-repo-check", cmd)
        self.assertIn("-C /scratch/run1", cmd)
        self.assertIn("-m {model}", cmd)

    def test_codex_execute_honors_effort_and_service_tier(self):
        # Fixed 2026-08-31: the execute builder used to silently drop these via its own bare
        # **_params while the review builder honored them -- a real asymmetry the unified
        # (kind, cli) registry exists specifically to prevent.
        cmd = commands.build_execute_command("codex", target_dir="/scratch/run1", effort="high",
                                              service_tier="priority")
        self.assertIn("-c model_reasoning_effort='\"high\"'", cmd)
        self.assertIn("-c service_tier='\"priority\"'", cmd)

    def test_cursor_agent_execute_has_no_hard_sandbox_but_is_dispatchable(self):
        # Accepted-risk decision (2026-08-30): no CLI flag genuinely confines cursor-agent's
        # writes (re-confirmed live even with --sandbox enabled) -- it's registered anyway,
        # marked in NO_HARD_SANDBOX_CLIS so callers know to add soft-confinement prompt guidance.
        cmd = commands.build_execute_command("cursor-agent", target_dir="/scratch/run1")
        self.assertIn("--sandbox enabled", cmd)
        self.assertIn("--workspace /scratch/run1", cmd)
        self.assertIn("--force", cmd)
        self.assertIn("--trust", cmd)
        self.assertIn("--model {model}", cmd)
        self.assertIn("cursor-agent", commands.NO_HARD_SANDBOX_CLIS)

    def test_opencode_execute_has_no_hard_sandbox_but_is_dispatchable(self):
        # Accepted-risk decision (2026-08-30): no CLI flag confines opencode's writes at all
        # (re-confirmed live with --dir + --auto) -- registered anyway, same as cursor-agent.
        cmd = commands.build_execute_command("opencode", target_dir="/scratch/run1")
        self.assertIn("--dir /scratch/run1", cmd)
        self.assertIn("--auto", cmd)
        self.assertIn("-m {model}", cmd)
        self.assertIn("opencode", commands.NO_HARD_SANDBOX_CLIS)

    def test_codex_requires_target_dir(self):
        with self.assertRaises(ValueError):
            commands.build_execute_command("codex")

    def test_target_dir_with_shell_metacharacters_is_quoted(self):
        cmd = commands.build_execute_command("codex", target_dir="/tmp/a b$(x)")
        self.assertIn(shlex.quote("/tmp/a b$(x)"), cmd)

    def test_grok_uses_workspace_sandbox_with_stdin_bridge(self):
        # Live-verified 2026-08-30: --sandbox workspace confines writes to --cwd; --always-approve
        # is required for a headless run (no interactive terminal to approve tool-use); the
        # sh -c '... "$(cat)"' wrapper bridges GSD's stdin-only prompt delivery into grok's
        # positional -p/--single value requirement -- confirmed live end-to-end with a piped prompt.
        cmd = commands.build_execute_command("grok", target_dir="/scratch/run1")
        self.assertIn("--sandbox workspace", cmd)
        self.assertIn("--cwd /scratch/run1", cmd)
        self.assertIn("--always-approve", cmd)
        self.assertIn("-m {model}", cmd)
        self.assertIn('"$(cat)"', cmd)
        self.assertTrue(cmd.startswith("sh -c '") and cmd.endswith("'"))

    def test_grok_execute_requires_target_dir(self):
        with self.assertRaises(ValueError):
            commands.build_execute_command("grok")

    def test_claude_uses_restricted_mode_with_cd_wrapper(self):
        # Live-verified 2026-08-30: --restricted + --permission-mode acceptEdits genuinely
        # confines file-tool writes to the working directory (a write outside it was refused
        # with the CLI's own real error). claude has no -C/--cwd flag, so this wraps the whole
        # invocation in sh -c 'cd <dir> && exec claude ...' -- confirmed live end-to-end with a
        # piped prompt, matching how GSD actually invokes this command.
        cmd = commands.build_execute_command("claude", target_dir="/scratch/run1")
        self.assertIn("--restricted", cmd)
        self.assertIn("--permission-mode acceptEdits", cmd)
        self.assertIn("cd /scratch/run1", cmd)
        self.assertIn("exec claude", cmd)
        self.assertIn("--model {model}", cmd)
        self.assertTrue(cmd.startswith("sh -c '") and cmd.endswith("'"))

    def test_claude_execute_requires_target_dir(self):
        with self.assertRaises(ValueError):
            commands.build_execute_command("claude")

    def test_unknown_cli_raises_value_error(self):
        with self.assertRaises(ValueError):
            commands.build_execute_command("nonexistent-cli")


class TestFilterByAffinity(unittest.TestCase):
    def test_keeps_only_matching_affinity_when_any_match_exists(self):
        candidates = [{"key": "a", "task_affinity": "frontend"},
                      {"key": "b", "task_affinity": "backend"}]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_no_matching_affinity_returns_all_unfiltered(self):
        candidates = [{"key": "a", "task_affinity": "backend"}]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_candidates_with_no_declared_affinity_always_pass_through(self):
        candidates = [{"key": "a", "task_affinity": None},
                      {"key": "b", "task_affinity": "frontend"}]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual({c["key"] for c in result}, {"a", "b"})

    def test_mixed_untagged_and_wrong_tag_excludes_only_the_wrong_tag(self):
        candidates = [{"key": "untagged", "task_affinity": None},
                      {"key": "backend-tagged", "task_affinity": "backend"}]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual([c["key"] for c in result], ["untagged"])


class TestFilterByPurpose(unittest.TestCase):
    def test_keeps_only_matching_purpose_when_any_match_exists(self):
        candidates = [{"key": "a", "purpose": "execute"},
                      {"key": "b", "purpose": "review"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_both_purpose_always_matches(self):
        candidates = [{"key": "a", "purpose": "both"},
                      {"key": "b", "purpose": "review"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_candidates_with_no_declared_purpose_always_pass_through(self):
        candidates = [{"key": "a", "purpose": None},
                      {"key": "b", "purpose": "execute"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual({c["key"] for c in result}, {"a", "b"})

    def test_no_matching_purpose_returns_all_unfiltered(self):
        candidates = [{"key": "a", "purpose": "review"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_missing_purpose_key_entirely_treated_as_no_preference(self):
        # pre-migration review-spec.toml: the field is absent, not None
        candidates = [{"key": "a"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual([c["key"] for c in result], ["a"])


class TestFilterByContext(unittest.TestCase):
    def test_drops_candidates_below_required_context(self):
        candidates = [{"key": "small", "context_limit": 100_000},
                      {"key": "big", "context_limit": 1_000_000}]
        result = execute_selection.filter_by_context(candidates, required_context=500_000)
        self.assertEqual([c["key"] for c in result], ["big"])

    def test_unknown_context_limit_passes_through_not_dropped(self):
        candidates = [{"key": "unknown", "context_limit": None}]
        result = execute_selection.filter_by_context(candidates, required_context=500_000)
        self.assertEqual([c["key"] for c in result], ["unknown"])


class TestResolveExecuteCandidates(unittest.TestCase):
    def test_full_pipeline_ranks_top_n_first(self):
        candidates = [
            {"key": "c", "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "a", "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "b", "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=["b", "a"])
        self.assertEqual([c["key"] for c in result], ["b", "a", "c"])

    def test_unknown_context_ranks_after_confirmed_sufficient(self):
        candidates = [
            {"key": "unknown", "task_affinity": "backend", "context_limit": None},
            {"key": "confirmed", "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=["unknown", "confirmed"])
        self.assertEqual([c["key"] for c in result], ["confirmed", "unknown"])

    def test_purpose_filter_excludes_review_only_candidates(self):
        candidates = [
            {"key": "reviewer-only", "purpose": "review",
             "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "both-ok", "purpose": "both",
             "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=[])
        self.assertEqual([c["key"] for c in result], ["both-ok"])


class TestTaskAffinityMatchBonus(unittest.TestCase):
    # Cross-Document Consistency CRITICAL finding (round 3): the design's task_affinity_match=2
    # bonus (spec §6) is additive on a 0-100 score, capped at +15 COMBINED with every other
    # bonus -- it can never be large enough to flip an arbitrarily-large explicit rank
    # distance. Placed BEFORE top_n_keys rank in the sort key (an earlier draft's ordering),
    # the bonus was effectively unbounded: it could outrank a top_n_keys #1 candidate with a
    # last-place, merely-tagged one, which is not what "capped at +15" means. The bonus is
    # therefore ranked AFTER top_n_keys rank in the sort key below -- a genuine tie-break that
    # only ever matters among candidates the ladder itself treats as equally ranked (both
    # explicitly tied, or both absent from top_n_keys and sharing the same fallback rank),
    # never an override of a real, distinguishing rank.
    def test_exact_affinity_match_ranks_above_an_untagged_candidate_at_equal_top_n_rank(self):
        candidates = [
            {"key": "untagged", "context_limit": 1_000_000},
            {"key": "exact-match", "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=[])  # neither is in top_n_keys -- both share the
            # same fallback rank (len(top_n_keys)), so this IS a genuine rank tie.
        self.assertEqual([c["key"] for c in result], ["exact-match", "untagged"])

    def test_top_n_rank_still_wins_when_no_affinity_tag_is_involved(self):
        # The bonus never overrides an EXPLICIT top_n_keys preference between two candidates
        # that are equally untagged -- it only ever breaks a tie in favor of an exact match.
        candidates = [{"key": "a", "context_limit": 1_000_000},
                      {"key": "b", "context_limit": 1_000_000}]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=["b", "a"])
        self.assertEqual([c["key"] for c in result], ["b", "a"])

    def test_explicit_top_n_rank_always_wins_over_the_affinity_tie_break(self):
        # CRITICAL finding: the bonus is a BOUNDED tie-break only -- it must never override a
        # real, explicit ladder-rank distance (the spec's bonus is capped at +15 on a 0-100
        # score, never large enough to flip a top_n_keys preference between two DIFFERENTLY
        # ranked candidates just because one happens to carry a matching task_affinity tag).
        candidates = [
            {"key": "top-ranked-untagged", "context_limit": 1_000_000},
            {"key": "low-ranked-match", "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type="backend", required_context=1000,
            affinity_table={}, top_n_keys=["top-ranked-untagged", "low-ranked-match"])
        self.assertEqual([c["key"] for c in result], ["top-ranked-untagged", "low-ranked-match"])


class TestCandidatesToLadder(unittest.TestCase):
    def test_extracts_ordered_keys(self):
        candidates = [{"key": "b/model"}, {"key": "a/model"}]
        self.assertEqual(execute_selection.candidates_to_ladder(candidates), ["b/model", "a/model"])


class TestDispatchReviewer(unittest.TestCase):
    def test_composes_tooling_guidance_and_dispatches_via_the_polling_engine(self):
        captured = {}

        def fake_dispatch(command, prompt, timeout_tiers, poll_interval=150, **kw):
            captured["command"] = command
            captured["prompt"] = prompt
            captured["timeout_tiers"] = timeout_tiers
            return {"returncode": 0, "stdout": "## Review\n### Status: Approved\n",
                    "stderr": "", "timed_out": False, "tiers_tried": 1, "final_timeout": 600}

        result = reviewer_dispatch.dispatch_reviewer(
            {"key": "codex-sol", "model": "gpt-5.6-sol", "vendor": "openai", "cli": "codex",
             "command": "codex exec --sandbox read-only -m {model}", "extra": {}},
            "Read the checklist and review...",
            timeout_tiers=[600, 1200], tool_availability={"rg": True},
            agents_tooling_path=None,
            dispatch_fn=fake_dispatch,
            build_tooling_guidance_fn=lambda *a, **kw: "TOOLING GUIDANCE HERE",
            resolve_shared_reference_fn=lambda: "/fake/tooling-guidance.md",
            codegraph_health_fn=lambda cli: True)

        self.assertEqual(captured["timeout_tiers"], [600, 1200])
        self.assertIn("TOOLING GUIDANCE HERE", captured["prompt"])
        self.assertIn("Read the checklist and review...", captured["prompt"])
        self.assertEqual(captured["command"], "codex exec --sandbox read-only -m gpt-5.6-sol")
        self.assertEqual(result["stdout"], "## Review\n### Status: Approved\n")

    def test_command_line_prompt_cli_receives_the_tooling_guidance_prefix_too(self):
        # The whole point of rendering INSIDE dispatch_reviewer: grok inlines {prompt} into its
        # own command line and never reads stdin, so a guidance prefix applied only to stdin
        # would be silently discarded for exactly the CLI that has no AGENTS.md ingestion.
        captured = {}

        def fake_dispatch(command, prompt, timeout_tiers, **kw):
            captured["command"] = command
            captured["prompt"] = prompt
            return {"returncode": 0, "stdout": "", "stderr": "", "timed_out": False,
                    "tiers_tried": 1, "final_timeout": 600}

        reviewer_dispatch.dispatch_reviewer(
            {"key": "grok-flagship", "model": "grok-4.6", "vendor": "xai", "cli": "grok",
             "command": "grok -p {prompt} -m {model}", "extra": {}},
            "Read the checklist and review...",
            timeout_tiers=[600], tool_availability={"rg": True}, agents_tooling_path=None,
            dispatch_fn=fake_dispatch,
            resolve_shared_reference_fn=lambda: "/fake/tooling-guidance.md",
            codegraph_health_fn=lambda cli: False)

        self.assertIn("SHARED_TOOLING_PATH = /fake/tooling-guidance.md", captured["command"])
        self.assertIn("TOOL_AVAILABILITY = ", captured["command"])
        self.assertIn("Read the checklist and review...", captured["command"])

    def test_codegraph_health_is_resolved_internally_not_asked_of_the_caller(self):
        asked = []

        def fake_dispatch(command, prompt, timeout_tiers, **kw):
            return {"returncode": 0, "stdout": "", "stderr": "", "timed_out": False,
                    "tiers_tried": 1, "final_timeout": 600}

        def fake_health(cli):
            asked.append(cli)
            return True

        captured_guidance_args = {}

        def fake_guidance(cli, availability, agents_path, codegraph_registered, **kw):
            captured_guidance_args["codegraph_registered"] = codegraph_registered
            return ""

        reviewer_dispatch.dispatch_reviewer(
            {"key": "k", "model": "m", "vendor": "v", "cli": "codex",
             "command": "codex exec -m {model}", "extra": {}},
            "p", timeout_tiers=[600], tool_availability={"codegraph": True},
            dispatch_fn=fake_dispatch, build_tooling_guidance_fn=fake_guidance,
            resolve_shared_reference_fn=lambda: None, codegraph_health_fn=fake_health)

        self.assertEqual(asked, ["codex"])
        self.assertTrue(captured_guidance_args["codegraph_registered"])

    def test_native_entry_with_no_cli_never_runs_the_codegraph_health_check(self):
        asked = []

        def fake_dispatch(command, prompt, timeout_tiers, **kw):
            return {"returncode": 0, "stdout": "", "stderr": "", "timed_out": False,
                    "tiers_tried": 1, "final_timeout": 600}

        reviewer_dispatch.dispatch_reviewer(
            {"key": "custom", "model": "m", "vendor": "v", "cli": None,
             "command": "my-script --model {model} --prompt {prompt}", "extra": {}},
            "p", timeout_tiers=[600], tool_availability={},
            dispatch_fn=fake_dispatch, resolve_shared_reference_fn=lambda: None,
            codegraph_health_fn=lambda cli: asked.append(cli) or True)

        self.assertEqual(asked, [])

    def test_malformed_entry_without_a_command_template_raises_value_error(self):
        with self.assertRaises(ValueError):
            reviewer_dispatch.dispatch_reviewer(
                {"key": "broken", "model": "m", "vendor": "v", "cli": "codex",
                 "command": None, "extra": {}},
                "p", timeout_tiers=[600], tool_availability={},
                resolve_shared_reference_fn=lambda: None,
                codegraph_health_fn=lambda cli: False)

    def test_dispatch_reviewer_cli_subcommand_stdout_only_prints_raw_report(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("review this plan")
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump([{"key": "grok-flagship", "model": "grok-4.6", "vendor": "xai",
                            "cli": "grok", "command": "grok -p {prompt} -m {model}",
                            "extra": {}}], f)
            seen = {}

            def fake_dispatch_reviewer(reviewer_entry, prompt, timeout_tiers, *a, **kw):
                seen["entry"] = reviewer_entry
                return {"returncode": 0, "stdout": "### Status: Approved\n", "stderr": "",
                        "timed_out": False, "tiers_tried": 1, "final_timeout": 600}

            with redirect_stdout(io.StringIO()) as out:
                code = rs.main(
                    ["dispatch-reviewer", "--reviewers-json", reviewers_path, "--index", "0",
                     "--prompt-file", prompt_path, "--timeout-tiers", "600,1200",
                     "--stdout-only"],
                    dispatch_reviewer_fn=fake_dispatch_reviewer)
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "### Status: Approved\n")
        self.assertEqual(seen["entry"]["cli"], "grok")

    def test_dispatch_reviewer_cli_subcommand_reports_a_malformed_entry_cleanly(self):
        import io
        from contextlib import redirect_stderr
        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("review this plan")
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump([{"key": "broken", "model": "m", "vendor": "v", "cli": "codex",
                            "command": None, "extra": {}}], f)
            with redirect_stderr(io.StringIO()) as err:
                code = rs.main(
                    ["dispatch-reviewer", "--reviewers-json", reviewers_path, "--index", "0",
                     "--prompt-file", prompt_path, "--timeout-tiers", "600"])
        self.assertEqual(code, 1)
        self.assertIn("dispatch-reviewer:", err.getvalue())
        self.assertNotIn("### Status:", err.getvalue())

    def test_dispatch_reviewer_cli_subcommand_reports_an_out_of_range_index(self):
        import io
        from contextlib import redirect_stderr
        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("p")
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump([], f)
            with redirect_stderr(io.StringIO()) as err:
                code = rs.main(
                    ["dispatch-reviewer", "--reviewers-json", reviewers_path, "--index", "0",
                     "--prompt-file", prompt_path, "--timeout-tiers", "600"])
        self.assertEqual(code, 1)
        self.assertIn("no reviewer at index 0", err.getvalue())


class TestTimeoutTiers(unittest.TestCase):
    def test_default_policy_includes_the_10_20_30_minute_default(self):
        self.assertEqual(config_io.DEFAULT_POLICY["timeout_tiers"], [600, 1200, 1800])

    def test_cfg_resolve_surfaces_the_default_when_config_omits_it(self):
        def fake_load(path):
            return {}
        with unittest.mock.patch.object(config_io, "cfg_load_toml", fake_load):
            resolved = config_io.cfg_resolve("/nonexistent", {})
        self.assertEqual(resolved["policy"]["timeout_tiers"], [600, 1200, 1800])

    def test_resolve_timeout_tiers_uses_reviewer_override_when_present(self):
        reviewer = {"key": "codex-sol", "extra": {"timeout_tiers": [900, 1800]}}
        policy = {"timeout_tiers": [600, 1200, 1800]}
        self.assertEqual(config_io.resolve_timeout_tiers(reviewer, policy), [900, 1800])

    def test_resolve_timeout_tiers_falls_back_to_policy_default(self):
        reviewer = {"key": "grok-flagship", "extra": {}}
        policy = {"timeout_tiers": [600, 1200, 1800]}
        self.assertEqual(config_io.resolve_timeout_tiers(reviewer, policy), [600, 1200, 1800])

    def test_resolve_timeout_tiers_cli_subcommand_uses_reviewer_override(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".aikit"))
            with open(os.path.join(d, ".aikit", "review-spec.toml"), "w", encoding="utf-8") as f:
                f.write('[policy]\nmode = "single"\nladder = []\n')
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump([{"key": "codex-sol", "model": "gpt-5.6-sol", "vendor": "openai",
                            "cli": "codex", "command": "codex exec -m {model}",
                            "extra": {"timeout_tiers": [900, 1800]}}], f)
            with redirect_stdout(io.StringIO()) as out:
                code = rs.main(
                    ["resolve-timeout-tiers", "--cwd", d, "--reviewers-json", reviewers_path,
                     "--index", "0"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().strip(), "900,1800")

    def test_resolve_timeout_tiers_cli_subcommand_falls_back_to_policy_default(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            # No .aikit/review-spec.toml at all -- cfg_resolve degrades to DEFAULT_POLICY.
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump([{"key": "grok-flagship", "model": "grok-4.6", "vendor": "xai",
                            "cli": "grok", "command": "grok -p {prompt} -m {model}",
                            "extra": {}}], f)
            with redirect_stdout(io.StringIO()) as out:
                code = rs.main(
                    ["resolve-timeout-tiers", "--cwd", d, "--reviewers-json", reviewers_path,
                     "--index", "0"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().strip(), "600,1200,1800")


class TestLoadRankingWeights(unittest.TestCase):
    def test_loads_the_real_bundled_weights_file(self):
        weights = model_ranker.load_ranking_weights()
        self.assertAlmostEqual(weights["review"]["intelligence_index"], 0.30)
        self.assertAlmostEqual(weights["execute"]["coding_index"], 0.30)
        self.assertEqual(weights["bonuses"]["batch_mode"], 8)
        self.assertEqual(weights["bonuses"]["bonus_cap"], 15)

    def test_missing_file_falls_back_to_default_weights(self):
        weights = model_ranker.load_ranking_weights("/nonexistent/path.toml")
        self.assertIn("review", weights)
        self.assertIn("execute", weights)
        self.assertIn("bonuses", weights)

    def test_fallback_returns_an_independent_copy_each_call(self):
        # HIGH finding: a caller mutating one fallback result must never corrupt the next.
        w1 = model_ranker.load_ranking_weights("/nonexistent/path.toml")
        w1["review"]["intelligence_index"] = 999.0
        w2 = model_ranker.load_ranking_weights("/nonexistent/path.toml")
        self.assertEqual(w2["review"]["intelligence_index"], 0.30)

    def test_syntactically_valid_toml_missing_a_purpose_section_falls_back(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n")
            path = f.name
        try:
            weights = model_ranker.load_ranking_weights(path)
            self.assertIn("review", weights)
            self.assertIn("execute", weights)
        finally:
            os.remove(path)

    def test_syntactically_valid_toml_missing_an_axis_falls_back(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[review]\nintelligence_index = 0.99\n"  # missing every other axis --
                    # MEDIUM finding (round-4): deliberately 0.99, NOT 0.30 (the real default's
                    # own value) -- an earlier draft used 0.30 here too, so this assertion could
                    # pass whether load_ranking_weights actually fell back OR just happened to
                    # read this partial file's own intelligence_index value back verbatim,
                    # proving nothing about the fallback path actually running.
                    "[execute]\nintelligence_index = 0.15\ncoding_index = 0.30\n"
                    "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                    "price = 0.15\nspeed = 0.10\n"
                    "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n")
            path = f.name
        try:
            weights = model_ranker.load_ranking_weights(path)
            # Asserting the REAL default's value (0.30), distinguishable from the fixture's
            # own 0.99, is what actually proves the fallback path discarded the incomplete
            # file rather than silently using its partial values as-is.
            self.assertAlmostEqual(weights["review"]["intelligence_index"], 0.30)
        finally:
            os.remove(path)

    def test_syntactically_valid_toml_with_a_non_numeric_axis_falls_back(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write('[review]\nintelligence_index = "high"\ncoding_index = 0.10\n'
                    "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                    "price = 0.15\nspeed = 0.05\n"
                    "[execute]\nintelligence_index = 0.15\ncoding_index = 0.30\n"
                    "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                    "price = 0.15\nspeed = 0.10\n"
                    "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n")
            path = f.name
        try:
            weights = model_ranker.load_ranking_weights(path)
            self.assertIsInstance(weights["review"]["intelligence_index"], (int, float))
        finally:
            os.remove(path)

    def test_syntactically_valid_toml_missing_a_bonus_field_falls_back(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[review]\nintelligence_index = 0.30\ncoding_index = 0.10\n"
                    "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                    "price = 0.15\nspeed = 0.05\n"
                    "[execute]\nintelligence_index = 0.15\ncoding_index = 0.30\n"
                    "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                    "price = 0.15\nspeed = 0.10\n"
                    "[bonuses]\nbatch_mode = 8\n")  # missing fallback_quota/bonus_cap
            path = f.name
        try:
            weights = model_ranker.load_ranking_weights(path)
            self.assertIn("bonus_cap", weights["bonuses"])
        finally:
            os.remove(path)


class TestScoreCandidates(unittest.TestCase):
    def setUp(self):
        self.weights = model_ranker.load_ranking_weights()

    def test_higher_intelligence_index_ranks_first_for_review(self):
        entries = [
            {"key": "low", "scores": {"intelligence_index": 40, "coding_index": 40,
                                       "agentic_index": 40}},
            {"key": "high", "scores": {"intelligence_index": 90, "coding_index": 40,
                                        "agentic_index": 40}},
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        self.assertEqual([e["key"] for e in ranked], ["high", "low"])

    def test_missing_axis_defaults_to_49_not_excluded_or_zeroed(self):
        # A candidate with NO scores dict at all (every AA-index axis genuinely missing)
        # must score meaningfully above 0 (its missing axes default to 49.0, not 0) --
        # but a real, low intelligence_index of 1 (present, genuinely bad) should score
        # LOWER than the missing-axis default of 49.0 once normalized, since normalizing a
        # lone real value of 1 against nothing else still yields 100 for that single
        # present point... use a THIRD anchor candidate with a much higher real score so
        # the low real score normalizes down near 0, clearly below the 49.0 default.
        entries = [
            {"key": "anchor", "scores": {"intelligence_index": 100, "coding_index": 100,
                                          "agentic_index": 100}},
            {"key": "no_scores", "tool_calling": True},
            {"key": "low_real_scores", "scores": {"intelligence_index": 1, "coding_index": 1,
                                                    "agentic_index": 1}, "tool_calling": False},
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        by_key = {e["key"]: e["score"] for e in ranked}
        self.assertGreater(by_key["no_scores"], 0)
        order = [e["key"] for e in ranked]
        self.assertLess(order.index("no_scores"), order.index("low_real_scores"))

    def test_a_real_flagship_now_outranks_a_data_free_candidate_with_favorable_price(self):
        # This is the exact live-production bug this fix round exists to close: a data-
        # free candidate whose ONLY signal is a favorable ($0) price must no longer beat a
        # real flagship with genuine (if comparatively unremarkable, ~60-range) AA scores
        # and a real, non-zero price. Before this fix, the free candidate's single present
        # axis (price) normalized to 100 and its weighted average was 100 outright (nothing
        # else to drag it down); the flagship's weighted average, diluted across several
        # real-but-imperfect axes, lost. Verified against a real production catalog
        # (2026-09-04) that this exact shape of comparison was failing before this fix.
        entries = [
            {"key": "flagship", "scores": {"intelligence_index": 62, "coding_index": 58,
                                            "agentic_index": 55},
             "pricing": {"input_per_1m": 15.0}},
            {"key": "mid_tier", "scores": {"intelligence_index": 45, "coding_index": 42,
                                            "agentic_index": 40},
             "pricing": {"input_per_1m": 20.0}},
            {"key": "free_no_data", "pricing": {"input_per_1m": 0.0}},
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        self.assertEqual(ranked[0]["key"], "flagship")

    def test_batch_mode_bonus_can_flip_the_ranking(self):
        # A 3rd "anchor" candidate establishes a real spread for the now-normalized
        # intelligence/coding/agentic axes -- with only 2 candidates, a small raw gap
        # (50 vs 48) would min-max-normalize to the FULL 0-100 range and swamp the
        # capped +8 bonus. The anchor compresses no_batch/batch's normalized gap down
        # to something the bonus can still flip, same intent as the original test.
        entries = [
            {"key": "anchor", "scores": {"intelligence_index": 100, "coding_index": 100,
                                          "agentic_index": 100}},
            {"key": "no_batch", "scores": {"intelligence_index": 52, "coding_index": 52,
                                            "agentic_index": 52}, "batch_mode": False},
            {"key": "batch", "scores": {"intelligence_index": 50, "coding_index": 50,
                                         "agentic_index": 50}, "batch_mode": True},
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        order = [e["key"] for e in ranked]
        self.assertLess(order.index("batch"), order.index("no_batch"))

    def test_bonus_is_capped(self):
        entries = [{"key": "everything", "scores": {"intelligence_index": 100,
                                                      "coding_index": 100, "agentic_index": 100},
                    "batch_mode": True, "fallback_quota": True}]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        self.assertLessEqual(ranked[0]["score"], 100.0)

    def test_price_is_normalized_within_the_candidate_set_and_inverted(self):
        entries = [
            {"key": "cheap", "pricing": {"input_per_1m": 1.0}},
            {"key": "expensive", "pricing": {"input_per_1m": 100.0}},
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        self.assertEqual(ranked[0]["key"], "cheap")

    def test_score_never_exceeds_100_even_with_full_axes_and_bonuses(self):
        entries = [{"key": "maxed", "scores": {"intelligence_index": 100, "coding_index": 100,
                                                 "agentic_index": 100}, "tool_calling": True,
                    "batch_mode": True, "fallback_quota": True}]
        ranked = model_ranker.score_candidates(entries, "execute", self.weights)
        self.assertLessEqual(ranked[0]["score"], 100.0)

    def test_intelligence_index_is_normalized_within_the_candidate_set(self):
        # Mirrors the existing test_price_is_normalized_within_the_candidate_set_and_inverted
        # -- same contract, applied to intelligence_index instead of price: raw AA indices
        # (which top out ~55-65 in live production data) now get min-max normalized onto the
        # same 0-100 scale price/context/speed already use, instead of feeding a raw ~60 into
        # a scale where the other axes routinely hit 100. NOTE: this alone does not fully
        # guarantee a real flagship outranks a data-free candidate with a favorable price --
        # a candidate present on FEWER axes can still win if every axis it does have
        # normalizes favorably (weight_sum only sums over present axes, per the existing
        # "missing axis excluded, never zeroed" contract) -- that is a separate, deeper
        # design question (how missing-axis weight-renormalization interacts with a
        # data-completeness signal) flagged for the human, not fixed by this normalization.
        entries = [
            {"key": "low", "scores": {"intelligence_index": 30, "coding_index": 30,
                                       "agentic_index": 30}},
            {"key": "high", "scores": {"intelligence_index": 65, "coding_index": 65,
                                        "agentic_index": 65}},
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        self.assertEqual(ranked[0]["key"], "high")


class TestLoadSecret(unittest.TestCase):
    def test_env_var_takes_precedence(self):
        env = {"ARTIFICIAL_ANALYSIS_API_KEY": "from-env"}
        self.assertEqual(
            local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY"), "from-env")

    def test_reads_from_secrets_file_when_env_absent(self):
        with tempfile.TemporaryDirectory() as d:
            cfg_dir = os.path.join(d, ".config", "ai-kit")
            os.makedirs(cfg_dir)
            with open(os.path.join(cfg_dir, "secrets.env"), "w", encoding="utf-8") as f:
                f.write("# comment\nARTIFICIAL_ANALYSIS_API_KEY=from-file\nOTHER=ignored\n")
            env = {"HOME": d}
            self.assertEqual(
                local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY"), "from-file")

    def test_missing_file_returns_none(self):
        env = {"HOME": "/nonexistent-home-dir-xyz"}
        self.assertIsNone(local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY"))

    def test_missing_key_in_existing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            cfg_dir = os.path.join(d, ".config", "ai-kit")
            os.makedirs(cfg_dir)
            with open(os.path.join(cfg_dir, "secrets.env"), "w", encoding="utf-8") as f:
                f.write("OTHER=ignored\n")
            env = {"HOME": d}
            self.assertIsNone(local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY"))


class TestHttpGetJson(unittest.TestCase):
    # CRITICAL finding: models.dev returns HTTP 403 to urllib's default "Python-urllib/3.x"
    # User-Agent (confirmed live), so _http_get_json must send a real one -- assert against a
    # fake urlopen/Request capture, never a real network call.
    def test_sends_non_default_user_agent(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"{}"

        def fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.headers)
            return FakeResponse()

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            model_sources._http_get_json("https://example.test/x", {})
        ua = captured["headers"].get("User-agent") or captured["headers"].get("User-Agent")
        self.assertIsNotNone(ua)
        self.assertNotIn("python-urllib", ua.lower())

    def test_merges_caller_headers_rather_than_replacing_them(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"{}"

        def fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.headers)
            return FakeResponse()

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            model_sources._http_get_json("https://example.test/x", {"X-Api-Key": "secret"})
        self.assertEqual(captured["headers"].get("X-api-key"), "secret")
        ua = captured["headers"].get("User-agent") or captured["headers"].get("User-Agent")
        self.assertIsNotNone(ua)
        self.assertNotIn("python-urllib", ua.lower())


class TestFetchModelsDev(unittest.TestCase):
    def test_returns_parsed_json_and_ok_true_on_success(self):
        def fake_fetch(url, headers):
            self.assertEqual(url, model_sources.MODELS_DEV_URL)
            return {"openai": {"models": {"gpt-4o": {"id": "gpt-4o"}}}}
        data, ok = model_sources.fetch_models_dev(fetch_fn=fake_fetch)
        self.assertTrue(ok)
        self.assertEqual(data["openai"]["models"]["gpt-4o"]["id"], "gpt-4o")

    def test_fetch_failure_returns_empty_dict_and_ok_false(self):
        def failing_fetch(url, headers):
            raise urllib.error.URLError("no network")
        data, ok = model_sources.fetch_models_dev(fetch_fn=failing_fetch)
        self.assertEqual(data, {})
        self.assertFalse(ok)


class TestFetchArtificialAnalysis(unittest.TestCase):
    def test_no_api_key_returns_empty_list_and_ok_true_without_fetching(self):
        def should_not_be_called(url, headers):
            self.fail("must not fetch with no api key")
        data, ok = model_sources.fetch_artificial_analysis(None, fetch_fn=should_not_be_called)
        self.assertEqual(data, [])
        self.assertTrue(ok)  # deliberately skipped is NOT a failure -- nothing to preserve/lose

    def test_single_page_response(self):
        def fake_fetch(url, headers):
            self.assertEqual(headers, {"x-api-key": "aa_test"})
            return {"data": [{"id": "1", "name": "Model A"}],
                    "pagination": {"has_more": False}}
        data, ok = model_sources.fetch_artificial_analysis("aa_test", fetch_fn=fake_fetch)
        self.assertTrue(ok)
        self.assertEqual([m["id"] for m in data], ["1"])

    def test_paginates_until_has_more_is_false(self):
        pages = {
            1: {"data": [{"id": "1"}], "pagination": {"has_more": True}},
            2: {"data": [{"id": "2"}], "pagination": {"has_more": False}},
        }
        def fake_fetch(url, headers):
            page = 1 if "page=1" in url else 2
            return pages[page]
        data, ok = model_sources.fetch_artificial_analysis("aa_test", fetch_fn=fake_fetch)
        self.assertTrue(ok)
        self.assertEqual(sorted(m["id"] for m in data), ["1", "2"])

    def test_fetch_failure_returns_ok_false_and_whatever_was_collected_so_far(self):
        def failing_fetch(url, headers):
            raise urllib.error.URLError("no network")
        data, ok = model_sources.fetch_artificial_analysis("aa_test", fetch_fn=failing_fetch)
        self.assertEqual(data, [])
        self.assertFalse(ok)

    def test_mid_pagination_failure_returns_ok_false_even_with_partial_data(self):
        def flaky_fetch(url, headers):
            if "page=1" in url:
                return {"data": [{"id": "1"}], "pagination": {"has_more": True}}
            raise urllib.error.URLError("dropped mid-pagination")
        data, ok = model_sources.fetch_artificial_analysis("aa_test", fetch_fn=flaky_fetch)
        self.assertFalse(ok)  # partial data exists but is NOT trustworthy -- caller must not use it


class TestInferIsRouter(unittest.TestCase):
    def test_router_env_provider_name_matches(self):
        self.assertTrue(model_heuristics.infer_is_router("router-env"))

    def test_plain_vendor_name_does_not_match(self):
        self.assertFalse(model_heuristics.infer_is_router("openai"))

    def test_case_insensitive(self):
        self.assertTrue(model_heuristics.infer_is_router("Router-Env"))


class TestInferBatchMode(unittest.TestCase):
    def test_flash_suffix_matches(self):
        self.assertTrue(model_heuristics.infer_batch_mode("gemini-3.5-flash"))

    def test_batch_suffix_matches(self):
        self.assertTrue(model_heuristics.infer_batch_mode("gpt-5.6-batch"))

    def test_mini_suffix_matches(self):
        self.assertTrue(model_heuristics.infer_batch_mode("gpt-5-mini"))

    def test_flagship_model_does_not_match(self):
        self.assertFalse(model_heuristics.infer_batch_mode("gpt-5.6-sol"))


class TestInferFallbackQuota(unittest.TestCase):
    def test_matches_wherever_is_router_matches(self):
        self.assertTrue(model_heuristics.infer_fallback_quota("router-env"))

    def test_plain_vendor_name_does_not_match(self):
        self.assertFalse(model_heuristics.infer_fallback_quota("openai"))


class TestInferPurposeFromName(unittest.TestCase):
    def test_review_hint_matches(self):
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("router-env-review"), "review")

    def test_plan_review_hint_matches(self):
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("router-env-plan-review"), "review")

    def test_coding_hint_matches(self):
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("router-env-coding"), "execute")

    def test_execute_hint_matches(self):
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("router-env-execute"), "execute")

    def test_no_hint_returns_none(self):
        self.assertIsNone(model_heuristics.infer_purpose_from_name("router-env-fast"))

    def test_both_groups_matching_is_a_contradiction_returns_none(self):
        # A naming contradiction (both a review word and an execute word) must never be
        # silently resolved by picking one.
        self.assertIsNone(
            model_heuristics.infer_purpose_from_name("router-env-coding-review"))

    def test_case_insensitive(self):
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("Router-Env-Coding"), "execute")

    def test_hint_word_need_not_be_trailing(self):
        # A router operator's naming convention isn't guaranteed to put the purpose word
        # last -- token match anywhere in the id, not suffix-only.
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("review-router-env"), "review")

    def test_review_does_not_match_inside_preview(self):
        # Delimiter-boundary pin: "review" is a substring of "preview", but the "r" in
        # "review" is preceded by "p" (a word character), so no \b boundary exists there --
        # this must NOT match. Without the \b-bounded fix, this would wrongly return
        # "review", silently discarding a legitimate router-exposed model's real enrichment.
        self.assertIsNone(
            model_heuristics.infer_purpose_from_name("router-env/gemini-3-pro-preview"))

    def test_coding_does_not_match_inside_encoding(self):
        # Same class of false positive for the execute group: "coding" is a substring of
        # "encoding" but not a delimiter-bounded token there.
        self.assertIsNone(
            model_heuristics.infer_purpose_from_name("router-env/some-encoding-model"))


class TestStripKnownEffortSuffix(unittest.TestCase):
    def test_strips_a_single_trailing_effort_token(self):
        self.assertEqual(
            model_matcher._strip_known_effort_suffix("claude-opus-5-high"),
            "claude-opus-5")

    def test_strips_a_two_token_effort_compound(self):
        self.assertEqual(
            model_matcher._strip_known_effort_suffix("claude-opus-5-thinking-xhigh"),
            "claude-opus-5")

    def test_strips_the_thinking_max_compound(self):
        self.assertEqual(
            model_matcher._strip_known_effort_suffix("claude-opus-5-thinking-max"),
            "claude-opus-5")

    def test_no_strippable_trailing_token_returns_none(self):
        self.assertIsNone(model_matcher._strip_known_effort_suffix("claude-opus-5"))

    def test_a_service_tier_suffix_as_trailing_token_is_never_touched(self):
        # "fast" is not a recognized effort word -- the loop never even starts, so this is
        # untouched for a structural reason, not a separate tier denylist.
        self.assertIsNone(
            model_matcher._strip_known_effort_suffix("claude-opus-5-thinking-low-fast"))

    def test_bare_max_without_a_preceding_thinking_token_is_not_stripped(self):
        # Real base model qwen3-max must never be misattributed to "qwen3".
        self.assertIsNone(model_matcher._strip_known_effort_suffix("qwen3-max"))

    def test_a_real_base_model_ending_in_an_effort_word_is_preserved_after_stripping(self):
        # o3-mini-high is a genuine, different-from-o3 model -- "mini" must survive the strip.
        self.assertEqual(model_matcher._strip_known_effort_suffix("o3-mini-high"), "o3-mini")


class TestMatchModelsDev(unittest.TestCase):
    def setUp(self):
        self.data = {
            "openai": {"models": {"gpt-5.6-sol": {"id": "gpt-5.6-sol", "reasoning": True,
                                                    "tool_call": True,
                                                    "limit": {"context": 400000, "output": 128000},
                                                    "cost": {"input": 3.5, "output": 14.0}}}},
            "xai": {"models": {"grok-4.6": {"id": "grok-4.6", "tool_call": True,
                                             "limit": {"context": 256000}}}},
        }

    def test_matches_provider_prefixed_id_exactly(self):
        result = model_matcher.match_models_dev("openai/gpt-5.6-sol", self.data)
        self.assertIsNotNone(result)
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["cost"]["input"], 3.5)

    def test_matches_bare_id_by_searching_all_providers(self):
        result = model_matcher.match_models_dev("gpt-5.6-sol", self.data)
        self.assertIsNotNone(result)
        self.assertEqual(result["provider"], "openai")

    def test_no_match_returns_none(self):
        self.assertIsNone(model_matcher.match_models_dev("nonexistent-model", self.data))

    def test_provider_hint_wrong_still_falls_back_to_bare_search(self):
        # opencode namespaces as "<provider>/<model>" but the provider label opencode uses
        # isn't guaranteed to equal models.dev's own provider key -- must not give up early.
        result = model_matcher.match_models_dev("some-other-vendor/grok-4.6", self.data)
        self.assertIsNotNone(result)
        self.assertEqual(result["provider"], "xai")

    def test_bare_id_collision_across_two_providers_returns_none_rather_than_guess(self):
        # HIGH finding: "first provider in dict-iteration order wins" would silently attach
        # one vendor's fields (pricing/context/tool_calling) to a DIFFERENT vendor's model.
        collision_data = {
            "openai": {"models": {"sol": {"id": "sol", "cost": {"input": 3.5}}}},
            "xai": {"models": {"sol": {"id": "sol", "cost": {"input": 1.0}}}},
        }
        self.assertIsNone(model_matcher.match_models_dev("sol", collision_data))

    def test_fuzzy_match_finds_a_near_spelling_when_exact_lookup_finds_nothing(self):
        # CRITICAL finding: the design mandates a normalization + FUZZY-MATCH step, not just
        # direct/near-exact string equality -- a CLI's own id can differ from models.dev's id
        # by a short version token (here: a trailing "-2" models.dev carries that the CLI's own
        # id doesn't) that pure normalization (case/separator folding) alone never closes.
        fuzzy_data = {"openai": {"models": {"gpt-5.6-sol-2": {
            "id": "gpt-5.6-sol-2", "cost": {"input": 3.5}}}}}
        result = model_matcher.match_models_dev("openai/gpt-5.6-sol", fuzzy_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["cost"]["input"], 3.5)

    def test_fuzzy_match_returns_none_when_no_candidate_is_close_enough(self):
        fuzzy_data = {"openai": {"models": {"gpt-5.6-sol-2": {"id": "gpt-5.6-sol-2"}}}}
        self.assertIsNone(model_matcher.match_models_dev("totally-different-vendor-model", fuzzy_data))

    def test_fuzzy_match_with_two_equally_close_candidates_returns_none_rather_than_guess(self):
        # Collision-safety extends to the fuzzy path too -- two near-ties (both an equally
        # plausible "-a"/"-b" variant of the target) must not silently pick either one.
        fuzzy_collision = {
            "openai": {"models": {"gpt-5.6-sola": {"id": "gpt-5.6-sola"}}},
            "xai": {"models": {"gpt-5.6-solb": {"id": "gpt-5.6-solb"}}},
        }
        self.assertIsNone(model_matcher.match_models_dev("gpt-5.6-sol", fuzzy_collision))

    def test_hinted_provider_prefix_disambiguates_a_bare_id_collision(self):
        # The SAME collision as above, but the caller gave a "<hint>/<model>" shaped id --
        # step-1 lookup already resolves this unambiguously, no fallback search needed.
        collision_data = {
            "openai": {"models": {"sol": {"id": "sol", "cost": {"input": 3.5}}}},
            "xai": {"models": {"sol": {"id": "sol", "cost": {"input": 1.0}}}},
        }
        result = model_matcher.match_models_dev("openai/sol", collision_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["cost"]["input"], 3.5)

    def test_provider_hint_disambiguates_a_multi_provider_bare_id_collision(self):
        models_dev_data = {
            "openai": {"models": {"gpt-5.2": {"id": "gpt-5.2", "reasoning": True}}},
            "some-reseller": {"models": {"gpt-5.2": {"id": "gpt-5.2", "reasoning": False}}},
        }
        result = model_matcher.match_models_dev("gpt-5.2", models_dev_data,
                                                   provider_hint="openai")
        self.assertIsNotNone(result)
        self.assertEqual(result["provider"], "openai")

    def test_provider_hint_that_matches_nothing_still_returns_none_on_collision(self):
        models_dev_data = {
            "openai": {"models": {"gpt-5.2": {"id": "gpt-5.2"}}},
            "some-reseller": {"models": {"gpt-5.2": {"id": "gpt-5.2"}}},
        }
        result = model_matcher.match_models_dev("gpt-5.2", models_dev_data,
                                                   provider_hint="nonexistent-vendor")
        self.assertIsNone(result)

    def test_no_provider_hint_still_returns_none_on_collision_unchanged_behavior(self):
        models_dev_data = {
            "openai": {"models": {"gpt-5.2": {"id": "gpt-5.2"}}},
            "some-reseller": {"models": {"gpt-5.2": {"id": "gpt-5.2"}}},
        }
        result = model_matcher.match_models_dev("gpt-5.2", models_dev_data)
        self.assertIsNone(result)


class TestMatchModelsDevAllowFuzzy(unittest.TestCase):
    def test_default_preserves_existing_fuzzy_behavior_unchanged(self):
        # The primary call site in build_model_catalog never passes allow_fuzzy -- the
        # default must keep resolving a fuzzy-only match exactly as it did before this spec.
        fuzzy_data = {"openai": {"models": {"gpt-5.6-sol-2": {
            "id": "gpt-5.6-sol-2", "cost": {"input": 3.5}}}}}
        result = model_matcher.match_models_dev("openai/gpt-5.6-sol", fuzzy_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["cost"]["input"], 3.5)

    def test_allow_fuzzy_false_skips_the_pool_fuzzy_step(self):
        fuzzy_data = {"openai": {"models": {"gpt-5.6-sol-2": {
            "id": "gpt-5.6-sol-2", "cost": {"input": 3.5}}}}}
        result = model_matcher.match_models_dev(
            "openai/gpt-5.6-sol", fuzzy_data, allow_fuzzy=False)
        self.assertIsNone(result)


class TestMatchArtificialAnalysis(unittest.TestCase):
    def setUp(self):
        self.models = [
            {"id": "abc", "name": "GPT-5.6 Sol", "slug": "gpt-5-6-sol",
             "model_creator": {"name": "OpenAI"},
             "evaluations": {"artificial_analysis_intelligence_index": 68.4,
                              "artificial_analysis_coding_index": 74.1,
                              "artificial_analysis_agentic_index": 61.2},
             "performance": {"median_output_tokens_per_second": 142.3}},
        ]

    def test_matches_by_normalized_slug(self):
        result = model_matcher.match_artificial_analysis("openai/gpt-5.6-sol", self.models)
        self.assertIsNotNone(result)
        self.assertEqual(result["evaluations"]["artificial_analysis_coding_index"], 74.1)

    def test_no_match_returns_none(self):
        self.assertIsNone(
            model_matcher.match_artificial_analysis("totally-unknown-model", self.models))

    def test_fuzzy_match_finds_a_near_spelling_when_exact_lookup_finds_nothing(self):
        # CRITICAL finding: same fuzzy fallback as match_models_dev, applied to AA's own
        # slug/name fields -- a short version token difference must not fall through to
        # "unmatched" when normalization + fuzzy similarity would confidently resolve it.
        near_models = [{"id": "1", "name": "GPT-5.6 Sol V2", "slug": "gpt-5-6-sol-v2",
                        "model_creator": {"name": "OpenAI"},
                        "evaluations": {"artificial_analysis_coding_index": 74.1}}]
        result = model_matcher.match_artificial_analysis("openai/gpt-5.6-sol", near_models)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "1")

    def test_collision_disambiguated_by_provider_hint_via_model_creator(self):
        # Two different vendors' models normalize to the SAME slug ("sol") -- a naive
        # "first normalized match wins" would silently pick whichever is listed first.
        collision_models = [
            {"id": "1", "name": "Sol", "slug": "sol", "model_creator": {"name": "Xai"},
             "evaluations": {"artificial_analysis_coding_index": 10.0}},
            {"id": "2", "name": "Sol", "slug": "sol", "model_creator": {"name": "OpenAI"},
             "evaluations": {"artificial_analysis_coding_index": 90.0}},
        ]
        result = model_matcher.match_artificial_analysis(
            "openai/sol", collision_models, provider_hint="openai")
        self.assertEqual(result["id"], "2")

    def test_collision_with_no_provider_hint_returns_none_rather_than_guess(self):
        collision_models = [
            {"id": "1", "name": "Sol", "slug": "sol", "model_creator": {"name": "Xai"}},
            {"id": "2", "name": "Sol", "slug": "sol", "model_creator": {"name": "OpenAI"}},
        ]
        self.assertIsNone(model_matcher.match_artificial_analysis("sol", collision_models))

    def test_provider_hint_with_no_creator_match_falls_back_to_the_sole_name_match(self):
        # Only one normalized match exists at all -- provider_hint has nothing to disambiguate,
        # so the single match still wins (matches today's real-data behavior: most models have
        # no collision).
        result = model_matcher.match_artificial_analysis(
            "openai/gpt-5.6-sol", self.models, provider_hint="some-unrelated-vendor")
        self.assertIsNotNone(result)

    def test_none_slug_and_name_do_not_crash_and_fall_through_to_no_match(self):
        # Important finding: a key present with an explicit `null` value (not merely absent)
        # must not reach _normalize's .lower() call unguarded -- one malformed AA record must
        # not abort the whole match_artificial_analysis batch.
        malformed_models = [{"id": "bad", "slug": None, "name": None,
                              "model_creator": {"name": "OpenAI"}}]
        result = model_matcher.match_artificial_analysis(
            "openai/gpt-5.6-sol", malformed_models + self.models)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "abc")

    def test_none_model_creator_does_not_crash_the_vendor_derivation_path(self):
        # Important finding: `m.get("model_creator", {})` returns None (not {}) when the key is
        # present with an explicit `null` value -- `.get("name", "")` on None then raises.
        collision_models = [
            {"id": "1", "name": "Sol", "slug": "sol", "model_creator": None},
            {"id": "2", "name": "Sol", "slug": "sol", "model_creator": {"name": "OpenAI"}},
        ]
        result = model_matcher.match_artificial_analysis(
            "openai/sol", collision_models, provider_hint="openai")
        self.assertEqual(result["id"], "2")


class TestBuildModelCatalog(unittest.TestCase):
    def test_matched_candidate_is_enriched_and_added(self):
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        models_dev_data = {"openai": {"models": {"gpt-5.6-sol": {
            "id": "gpt-5.6-sol", "tool_call": True, "structured_output": True,
            "limit": {"context": 400000, "output": 128000},
            "cost": {"input": 3.5, "output": 14.0}}}}}
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, [], True, {})
        self.assertEqual(rejections, [])
        self.assertEqual(unmatched, [])
        self.assertIn("openai/gpt-5.6-sol", catalog)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertEqual(entry["provider"], "openai")
        self.assertTrue(entry["source"]["models_dev"])
        self.assertFalse(entry["source"]["artificial_analysis"])
        self.assertIn("opencode", entry["runtimes"])

    def test_router_candidate_with_coding_hint_never_calls_external_matching(self):
        # models_dev_data/aa_models both contain an EXACT match for this candidate's bare id --
        # if match_models_dev/match_artificial_analysis were called, source.models_dev and
        # source.artificial_analysis would come back True and tool_calling/scores would be
        # populated. Proving they stay False/absent proves the lookup never ran.
        models_dev_data = {"opencode-go": {"models": {"router-env-coding": {
            "id": "router-env-coding", "tool_call": True, "structured_output": True,
            "limit": {"context": 128000, "output": 8000}}}}}
        aa_models = [{"id": "1", "slug": "router-env-coding", "name": "Router Env Coding",
                      "model_creator": {"name": "SomeVendor"},
                      "evaluations": {"artificial_analysis_coding_index": 89.0}}]
        discovered = [{"cli": "opencode", "model_id": "opencode-go/router-env-coding"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(rejections, [])
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-coding"]
        self.assertEqual(entry["name_declared_purpose"], "execute")
        self.assertFalse(entry["source"]["models_dev"])
        self.assertFalse(entry["source"]["artificial_analysis"])
        self.assertNotIn("tool_calling", entry)
        self.assertNotIn("scores", entry)

    def test_router_candidate_with_review_hint_gets_review_purpose(self):
        discovered = [{"cli": "opencode", "model_id": "opencode-go/router-env-plan-review"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, {}, True, [], True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-plan-review"]
        self.assertEqual(entry["name_declared_purpose"], "review")

    def test_router_candidate_with_no_purpose_word_takes_the_unchanged_normal_path(self):
        # "router-env-fast" is a router (infer_is_router matches "-env") but has no purpose
        # word -- infer_purpose_from_name returns None, so this must fall through to ordinary
        # md_match/aa_match matching, unaffected by this feature.
        models_dev_data = {"opencode-go": {"models": {"router-env-fast": {
            "id": "router-env-fast", "tool_call": True, "structured_output": True,
            "limit": {"context": 128000, "output": 8000}}}}}
        discovered = [{"cli": "opencode", "model_id": "opencode-go/router-env-fast"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, [], True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-fast"]
        self.assertNotIn("name_declared_purpose", entry)
        self.assertTrue(entry["source"]["models_dev"])   # normal matching DID run
        self.assertTrue(entry["tool_calling"])

    def test_non_router_candidate_with_a_purpose_word_in_its_name_is_unaffected(self):
        # A real vendor model whose name happens to contain "coding" must never trigger this
        # heuristic -- infer_is_router gates it, and this id matches none of
        # _ROUTER_NAME_HINTS ("router", "-env", "local-llm").
        models_dev_data = {"openai": {"models": {"gpt-5-coding-assistant": {
            "id": "gpt-5-coding-assistant", "tool_call": True, "structured_output": True,
            "limit": {"context": 128000, "output": 8000}}}}}
        discovered = [{"cli": "codex", "model_id": "openai/gpt-5-coding-assistant"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, [], True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["openai/gpt-5-coding-assistant"]
        self.assertNotIn("name_declared_purpose", entry)
        self.assertTrue(entry["source"]["models_dev"])
        self.assertTrue(entry["tool_calling"])

    def test_lifecycle_preserves_prior_cached_fields_across_a_later_name_declared_run(self):
        # A candidate already in the catalog (e.g. from before this feature existed, or from a
        # manual correction) keeps its cached ctx_window/pricing/tool_calling when a LATER run
        # recognizes it as name-declared-purpose -- the new code path must never clear fields
        # it didn't itself populate, exactly like every other preserve-on-not-queried path in
        # this function.
        existing_catalog = {"opencode-go/router-env-coding": {
            "provider": "opencode-go",
            "runtimes": {"opencode": {"model_id": "opencode-go/router-env-coding",
                                       "ctx_window": 128000}},
            "is_router": True, "batch_mode": False, "fallback_quota": True,
            "tool_calling": True, "structured_output": True, "max_output_tokens": 8000,
            "pricing": {"input_per_1m": 1.0, "output_per_1m": 2.0},
            "source": {"models_dev": True, "artificial_analysis": False, "manual": False},
            "confidence": "high", "last_verified": "2026-08-01"}}
        # models_dev_data/aa_models both WOULD match if queried -- proving they weren't.
        models_dev_data = {"opencode-go": {"models": {"router-env-coding": {
            "id": "router-env-coding", "tool_call": False, "structured_output": False,
            "limit": {"context": 9999, "output": 9999}}}}}
        discovered = [{"cli": "opencode", "model_id": "opencode-go/router-env-coding"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, [], True, existing_catalog)
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-coding"]
        self.assertEqual(entry["name_declared_purpose"], "execute")
        self.assertEqual(entry["runtimes"]["opencode"]["ctx_window"], 128000)
        self.assertTrue(entry["tool_calling"])
        self.assertTrue(entry["structured_output"])
        self.assertEqual(entry["max_output_tokens"], 8000)
        self.assertEqual(entry["pricing"]["input_per_1m"], 1.0)
        self.assertTrue(entry["source"]["models_dev"])   # preserved from cache, not re-derived

    def test_router_candidate_with_contradictory_purpose_words_falls_through(self):
        # design spec Section 5(c): a naming CONTRADICTION (both a review word and an execute
        # word present) must fall through to the unchanged md_match/aa_match path, exactly like
        # the no-purpose-word case above -- verified here at the WIRING level (build_model_catalog
        # itself), not just at infer_purpose_from_name's own unit level (Task 1), since it's the
        # wiring's job to actually route on the heuristic's None result.
        models_dev_data = {"opencode-go": {"models": {"router-env-coding-review": {
            "id": "router-env-coding-review", "tool_call": True, "structured_output": True,
            "limit": {"context": 128000, "output": 8000}}}}}
        discovered = [{"cli": "opencode", "model_id": "opencode-go/router-env-coding-review"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, [], True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-coding-review"]
        self.assertNotIn("name_declared_purpose", entry)
        self.assertTrue(entry["source"]["models_dev"])   # normal matching DID run
        self.assertTrue(entry["tool_calling"])

    def test_name_declared_bare_id_with_no_provider_lands_in_unmatched_with_purpose_carried(self):
        # The short-circuit's only failure path: a name-declared router candidate reported as a
        # BARE id (no "<vendor>/" prefix -- e.g. a CLI that reports its own raw model name) with
        # no existing catalog entry to recover a provider from. It must land in `unmatched` with
        # `vendor_unknown: True` (same convention as the ordinary unmatched path), AND it must
        # still carry `name_declared_purpose` on that payload -- otherwise the wizard's Task 4
        # partition, which only inspects catalog entries, would silently lose the declaration
        # for any candidate that never makes it into the catalog.
        discovered = [{"cli": "customcli", "model_id": "router-env-coding"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, {}, True, [], True, {})
        self.assertEqual(catalog, {})
        self.assertEqual(len(unmatched), 1)
        candidate = unmatched[0]
        self.assertTrue(candidate["vendor_unknown"])
        self.assertIsNone(candidate["provider"])
        self.assertEqual(candidate["name_declared_purpose"], "execute")

    def test_attempt_1_exact_id_with_hint_resolves_a_cross_provider_collision(self):
        # No effort suffix at all here -- Attempt 1 (exact id + hint) must resolve this on
        # its own, without ever reaching Attempt 2's effort-stripping.
        models_dev_data = {
            "openai": {"models": {"sol": {
                "id": "sol", "tool_call": True, "structured_output": True,
                "limit": {"context": 400000, "output": 128000}}}},
            "some-reseller": {"models": {"sol": {
                "id": "sol", "tool_call": False, "structured_output": None,
                "limit": {"context": 400000, "output": 128000}}}},
        }
        aa_models = [{"id": "1", "slug": "sol", "name": "Sol",
                      "model_creator": {"name": "OpenAI"},
                      "evaluations": {"artificial_analysis_intelligence_index": 70.0}}]
        discovered = [{"cli": "codex", "model_id": "sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        entry = next(iter(catalog.values()))
        self.assertTrue(entry["tool_calling"])          # openai's row, not some-reseller's
        self.assertTrue(entry["structured_output"])

    def test_attempt_2_strips_the_effort_suffix_and_picks_the_hinted_provider_row(self):
        # Mirrors this spec's own motivating case: the raw id ("claude-opus-5-high") has no
        # exact match anywhere (Attempt 1 -> None, both providers tie on the UNSTRIPPED id
        # only via fuzzy which the primary call also can't use unambiguously), but its
        # effort-stripped base id ("claude-opus-5") collides across two providers whose
        # payloads genuinely disagree on structured_output -- proving the hint picks a
        # SPECIFIC row, not just "a" row from the collision (spec's round-6 safety property).
        models_dev_data = {
            "anthropic": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": True,
                "limit": {"context": 1000000, "output": 128000}}}},
            "some-reseller": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": None,
                "limit": {"context": 1000000, "output": 128000}}}},
        }
        aa_models = [{"id": "1", "slug": "claude-opus-5-high", "name": "Claude Opus 5 High",
                      "model_creator": {"name": "Anthropic"},
                      "evaluations": {"artificial_analysis_intelligence_index": 61.5}}]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-high"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["anthropic/claude-opus-5-high"]
        self.assertTrue(entry["structured_output"])         # anthropic's row, not the reseller's
        self.assertTrue(entry["tool_calling"])
        self.assertEqual(entry["max_output_tokens"], 128000)
        self.assertEqual(entry["runtimes"]["cursor-agent"]["ctx_window"], 1000000)
        self.assertFalse(entry["source"]["models_dev"])     # enrichment, not an exact match

    def test_attempt_2_never_falls_back_to_fuzzy_matching(self):
        # The stripped id here only fuzzy-matches (a trailing version-token difference) --
        # allow_fuzzy=False on both retry attempts means this must stay unresolved, never a
        # guessed match.
        models_dev_data = {"anthropic": {"models": {"claude-opus-5-2": {
            "id": "claude-opus-5-2", "tool_call": True, "structured_output": True,
            "limit": {"context": 1000000, "output": 128000}}}}}
        aa_models = [{"id": "1", "slug": "claude-opus-5-high", "name": "Claude Opus 5 High",
                      "model_creator": {"name": "Anthropic"},
                      "evaluations": {"artificial_analysis_intelligence_index": 61.5}}]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-high"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["anthropic/claude-opus-5-high"]
        self.assertNotIn("tool_calling", entry)
        self.assertNotIn("structured_output", entry)
        self.assertNotIn("max_output_tokens", entry)
        self.assertIsNone(entry["runtimes"]["cursor-agent"]["ctx_window"])

    def test_lifecycle_across_runs_clears_previously_recovered_fields_on_a_later_no_signal_run(
            self):
        # Round-3's accepted, documented tradeoff (spec Section 3.2): an Artificial Analysis
        # outage on a LATER run clears fields this spec's own enrichment retry recovered on
        # an earlier run -- exactly like today's existing contract for any candidate whose
        # primary match disappears. A second, unrelated candidate whose fields came from a
        # genuine PRIMARY match (never touched md_enrich_match at all) must clear identically,
        # proving the enrichment mechanism doesn't special-case fields it never touched.
        models_dev_data_run1 = {
            "anthropic": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": True,
                "limit": {"context": 1000000, "output": 128000}}}},
            "some-reseller": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": None,
                "limit": {"context": 1000000, "output": 128000}}}},
            "openai": {"models": {"gpt-5.6-sol": {
                "id": "gpt-5.6-sol", "tool_call": True, "structured_output": True,
                "limit": {"context": 400000, "output": 128000}}}},
        }
        aa_models = [{"id": "1", "slug": "claude-opus-5-high", "name": "Claude Opus 5 High",
                      "model_creator": {"name": "Anthropic"},
                      "evaluations": {"artificial_analysis_intelligence_index": 61.5}}]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-high"},
                      {"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog_run1, _, unmatched_run1 = cli.build_model_catalog(
            discovered, models_dev_data_run1, True, aa_models, True, {})
        self.assertEqual(unmatched_run1, [])
        enriched_key = "anthropic/claude-opus-5-high"      # recovered via this spec's retry
        primary_key = "openai/gpt-5.6-sol"           # recovered via the ordinary primary match
        self.assertTrue(catalog_run1[enriched_key]["structured_output"])
        self.assertTrue(catalog_run1[primary_key]["structured_output"])

        # Run 2: Artificial Analysis is down (aa_ok=False) and models.dev genuinely no longer
        # lists either model (models_dev_ok=True -- a real, empty re-query, not a skip).
        catalog_run2, _, unmatched_run2 = cli.build_model_catalog(
            discovered, {}, True, [], False, catalog_run1)
        self.assertEqual(unmatched_run2, [])
        for key, cli_name in ((enriched_key, "cursor-agent"), (primary_key, "opencode")):
            entry = catalog_run2[key]
            self.assertNotIn("tool_calling", entry)
            self.assertNotIn("structured_output", entry)
            self.assertNotIn("max_output_tokens", entry)
            self.assertIsNone(entry["runtimes"][cli_name]["ctx_window"])

    def test_unmatched_new_candidate_is_reported_but_never_persisted(self):
        # CRITICAL: an unmatched, never-before-seen candidate must NOT land in the catalog
        # automatically -- it needs research + user confirmation first (Task 8's wizard).
        discovered = [{"cli": "opencode", "model_id": "vendor/totally-unknown"}]
        catalog, rejections, unmatched = cli.build_model_catalog(discovered, {}, True, [], True, {})
        self.assertEqual(rejections, [])
        self.assertNotIn("vendor/totally-unknown", catalog)
        self.assertEqual(len(unmatched), 1)
        self.assertEqual(unmatched[0]["model_id"], "vendor/totally-unknown")
        self.assertEqual(unmatched[0]["cli"], "opencode")

    def test_unmatched_candidate_carries_heuristic_fields_for_wizard_confirmation(self):
        # CRITICAL finding: an earlier draft returned unmatched candidates with NO heuristic
        # fields at all, and its own confirmation-payload test looked them up in `catalog`
        # (a KeyError, since unmatched entries are never added to catalog) -- both bugs fixed
        # here: heuristics are computed for unmatched candidates too, and returned inline on
        # the unmatched dict itself, never via a catalog lookup that can't succeed.
        discovered = [{"cli": "opencode", "model_id": "router-env/totally-unknown"}]
        _, _, unmatched = cli.build_model_catalog(discovered, {}, True, [], True, {})
        self.assertEqual(len(unmatched), 1)
        self.assertTrue(unmatched[0]["is_router"])
        self.assertTrue(unmatched[0]["fallback_quota"])
        self.assertIn("batch_mode", unmatched[0])

    def test_already_confirmed_manual_entry_is_not_re_reported_as_unmatched(self):
        # A candidate already persisted (via confirm-catalog-entry, a previous run) is known --
        # re-running discovery on it must refresh its runtimes, not flag it as needing
        # confirmation again every single run.
        existing = {"vendor/totally-unknown": {"provider": "vendor", "runtimes": {},
                                                 "source": {"manual": True}, "confidence": "low",
                                                 "last_verified": "2026-08-01"}}
        discovered = [{"cli": "opencode", "model_id": "vendor/totally-unknown"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, {}, True, [], True, existing)
        self.assertEqual(unmatched, [])
        self.assertIn("opencode", catalog["vendor/totally-unknown"]["runtimes"])
        self.assertEqual(catalog["vendor/totally-unknown"]["confidence"], "low")

    def test_router_batch_and_fallback_quota_heuristics_are_applied(self):
        # HIGH finding: a candidate that matches NEITHER external source is, by this function's
        # own contract, never added to `catalog` -- it goes to `unmatched` instead (see the
        # dedicated unmatched-candidate tests above). Asserting on catalog[key] for such a
        # candidate is a KeyError by construction. Give this candidate a real models.dev match
        # so it actually lands in `catalog`, exercising the heuristics on the MATCHED path
        # (the unmatched path's own heuristic fields are already covered separately, above).
        discovered = [{"cli": "opencode", "model_id": "router-env/my-plan-review"}]
        models_dev_data = {"router-env": {"models": {"my-plan-review": {"id": "my-plan-review"}}}}
        catalog, _, unmatched = cli.build_model_catalog(discovered, models_dev_data, True, [], True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["router-env/my-plan-review"]
        self.assertTrue(entry["is_router"])
        self.assertTrue(entry["fallback_quota"])

    def test_existing_catalog_entries_are_preserved_when_not_rediscovered(self):
        existing = {"stale/model": {"provider": "p", "runtimes": {"c": {}}, "source": {},
                                     "confidence": "high", "last_verified": "2026-01-01"}}
        catalog, _, _ = cli.build_model_catalog([], {}, True, [], True, existing)
        self.assertIn("stale/model", catalog)

    def test_two_clis_reporting_the_same_model_merge_into_one_canonical_entry(self):
        # HIGH finding: catalog identity must not lose runtime mappings across CLIs.
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"},
                      {"cli": "codex", "model_id": "gpt-5.6-sol"}]
        models_dev_data = {"openai": {"models": {"gpt-5.6-sol": {"id": "gpt-5.6-sol"}}}}
        catalog, _, _ = cli.build_model_catalog(discovered, models_dev_data, True, [], True, {})
        self.assertEqual(len(catalog), 1)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertIn("opencode", entry["runtimes"])
        self.assertIn("codex", entry["runtimes"])

    def test_models_dev_fetch_failure_preserves_cached_models_dev_fields(self):
        # CRITICAL finding: a network failure must never overwrite already-cached enrichment.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {"models_dev": True, "artificial_analysis": False}, "confidence": "high",
            "last_verified": "2026-08-01", "tool_calling": True,
            "pricing": {"input_per_1m": 3.5, "output_per_1m": 14.0}}}
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, {}, False, [], True, existing)  # models_dev_ok=False: source is DOWN
        self.assertEqual(unmatched, [])
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertTrue(entry["tool_calling"])
        self.assertEqual(entry["pricing"]["input_per_1m"], 3.5)
        self.assertTrue(entry["source"]["models_dev"])  # still true -- not silently downgraded

    def test_total_source_failure_leaves_a_cached_entry_completely_unchanged_except_runtimes(self):
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {"models_dev": True, "artificial_analysis": True}, "confidence": "high",
            "last_verified": "2026-08-01", "scores": {"intelligence_index": 91.0}}}
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, False, [], False, existing)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertEqual(entry["scores"]["intelligence_index"], 91.0)
        self.assertEqual(entry["confidence"], "high")
        self.assertEqual(entry["last_verified"], "2026-08-01")  # unchanged -- nothing re-verified

    def test_artificial_analysis_pricing_fills_in_when_models_dev_has_no_match(self):
        # HIGH finding: AA pricing must not be discarded when models.dev has no match.
        aa_models = [{"id": "1", "slug": "totally-unknown", "name": "Totally Unknown",
                      "model_creator": {"name": "Vendor"},
                      "pricing": {"price_1m_input_tokens": 2.0, "price_1m_output_tokens": 8.0}}]
        discovered = [{"cli": "opencode", "model_id": "vendor/totally-unknown"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, True, aa_models, True, {})
        entry = catalog["vendor/totally-unknown"]
        self.assertEqual(entry["pricing"]["input_per_1m"], 2.0)
        self.assertEqual(entry["pricing"]["output_per_1m"], 8.0)

    def test_models_dev_fetch_failure_preserves_cached_runtime_ctx_window(self):
        # CRITICAL finding: a models.dev outage must not blank out an already-cached
        # runtime's ctx_window by unconditionally recomputing it from a (necessarily absent)
        # md_match -- that silently corrupts ranking's context_window axis.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai",
            "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol", "ctx_window": 400000}},
            "source": {"models_dev": True, "artificial_analysis": False}, "confidence": "high",
            "last_verified": "2026-08-01"}}
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, False, [], True, existing)
        self.assertEqual(
            catalog["openai/gpt-5.6-sol"]["runtimes"]["opencode"]["ctx_window"], 400000)

    def test_missing_api_key_preserves_cached_aa_fields_rather_than_wiping_them(self):
        # CRITICAL finding: no API key configured (aa_ok=True, aa_models=[] per Task 4's own
        # "deliberately skipped is not a failure" contract) must NOT be treated identically to
        # "AA was queried and genuinely found no match" -- the CLI wiring in Step 5 passes
        # aa_ok=False to THIS function whenever no key was available, specifically so this
        # preserve-not-wipe path runs; this test exercises that resulting contract directly.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {"models_dev": True, "artificial_analysis": True}, "confidence": "high",
            "last_verified": "2026-08-01",
            "scores": {"intelligence_index": 91.0, "coding_index": 88.0, "agentic_index": 84.0},
            "tokens_per_sec": 142.3}}
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, True, [], False, existing)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertEqual(entry["scores"]["intelligence_index"], 91.0)
        self.assertEqual(entry["tokens_per_sec"], 142.3)
        self.assertTrue(entry["source"]["artificial_analysis"])

    def test_genuine_no_match_with_a_working_key_clears_aa_fields_and_flips_source_false(self):
        # The OTHER transition (contrast with the no-key test above): AA genuinely queried,
        # genuinely found no match for THIS candidate -- fields and provenance are cleared
        # together, consistently, not left stale.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {"models_dev": True, "artificial_analysis": True}, "confidence": "high",
            "last_verified": "2026-08-01",
            "scores": {"intelligence_index": 91.0, "coding_index": 88.0, "agentic_index": 84.0}}}
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, True, [], True, existing)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertNotIn("scores", entry)
        self.assertFalse(entry["source"]["artificial_analysis"])

    def test_partial_aa_match_with_no_performance_data_clears_stale_tokens_per_sec(self):
        # MEDIUM finding (round-4): a PARTIAL match -- AA matched this candidate this run
        # (source.artificial_analysis is about to read True again) but this match's own
        # payload has no performance/median_output_tokens_per_second -- must clear a stale
        # cached tokens_per_sec, exactly like the full no-match case above. An earlier draft
        # only ever set "tokens_per_sec" in the returned fields dict when perf data existed,
        # silently retaining the old value via merge_catalog_entry's omission-preserves rule
        # even though this run's genuine query found nothing for it.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {"models_dev": True, "artificial_analysis": True}, "confidence": "high",
            "last_verified": "2026-08-01",
            "scores": {"intelligence_index": 91.0, "coding_index": 88.0, "agentic_index": 84.0},
            "tokens_per_sec": 142.3}}
        aa_models = [{"id": "1", "slug": "gpt-5-6-sol", "name": "GPT-5.6 Sol",
                      "model_creator": {"name": "OpenAI"},
                      "evaluations": {"artificial_analysis_intelligence_index": 91.0}}]
        # no "performance" key at all -- a genuine partial match
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, True, aa_models, True, existing)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertNotIn("tokens_per_sec", entry)
        self.assertTrue(entry["source"]["artificial_analysis"])

    def test_heuristic_correction_survives_a_later_catalog_rebuild(self):
        # HIGH finding: every refresh recomputed is_router/batch_mode/fallback_quota fresh
        # from the naming heuristic, silently overwriting a user's prior correction
        # (apply_heuristic_corrections, Task 2) on the very next run.
        existing = {"router-env/my-plan-review": {
            "provider": "router-env", "runtimes": {"opencode": {"model_id": "router-env/my-plan-review"}},
            "source": {}, "confidence": "low", "last_verified": "2026-08-01",
            "is_router": False}}  # user corrected this away from the heuristic default (True)
        discovered = [{"cli": "opencode", "model_id": "router-env/my-plan-review"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, True, [], True, existing)
        self.assertFalse(catalog["router-env/my-plan-review"]["is_router"])

    def test_bare_model_matched_only_via_artificial_analysis_derives_vendor_from_model_creator(self):
        # HIGH finding: a bare model id (codex-style, no "<vendor>/" prefix) with NO
        # models.dev match must not become its own vendor ("gpt-5.6-sol/gpt-5.6-sol") just
        # because model_id.split("/", 1)[0] has nothing to split -- when Artificial Analysis
        # matched, its model_creator is the real vendor signal.
        aa_models = [{"id": "1", "slug": "gpt-5-6-sol", "name": "GPT-5.6 Sol",
                      "model_creator": {"name": "OpenAI"},
                      "evaluations": {"artificial_analysis_intelligence_index": 91.0}}]
        discovered = [{"cli": "codex", "model_id": "gpt-5.6-sol"}]
        catalog, _, unmatched = cli.build_model_catalog(discovered, {}, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        self.assertIn("openai/gpt-5.6-sol", catalog)
        self.assertEqual(catalog["openai/gpt-5.6-sol"]["provider"], "openai")

    def test_discovered_candidates_include_single_provider_and_extra_candidates(self):
        # CRITICAL cross-doc finding: Task 8's ranking step must be able to reconstruct the
        # FULL candidate set (not just runtimes-with-a-"models"-array) without recomputing
        # cfg_resolve/--extra-candidate parsing itself -- build_model_catalog is given the
        # already-fully-reconciled `discovered_models` list by its caller (the CLI command,
        # Step 5) and this test only confirms it treats every one of them uniformly,
        # regardless of whether the candidate came from a runtimes snapshot, review-spec.toml,
        # or --extra-candidate -- there's no special-casing by origin inside this function.
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"},
                      {"cli": "codex", "model_id": "gpt-5.6-alt"}]  # e.g. from --extra-candidate
        catalog, _, unmatched = cli.build_model_catalog(discovered, {}, True, [], True, {})
        self.assertEqual({u["cli"] for u in unmatched}, {"opencode", "codex"})

    def test_bare_id_with_both_sources_unavailable_recovers_key_from_existing_catalog(self):
        # CRITICAL/HIGH fix (round-2 native-opus review): this is the `--if-stale` DEFAULT
        # path -- both sources skipped (models_dev_ok=False, aa_ok=False), a bare CLI-native
        # id (codex-style, no "<vendor>/" prefix) that was already matched and persisted on a
        # PRIOR run. Before the fix, this fell through to `provider = model_id`, minting an
        # unstable "gpt-5.6-sol/gpt-5.6-sol" key every such run -- never matching the real
        # cached entry, permanently orphaning it, and reclassifying an already-known model as
        # `unmatched` (needing manual research) on every single --if-stale run.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai",
            "runtimes": {"codex": {"model_id": "gpt-5.6-sol", "ctx_window": 400000}},
            "source": {"models_dev": True, "artificial_analysis": False}, "confidence": "high",
            "last_verified": "2026-08-01",
            "scores": {"intelligence_index": 91.0}}}
        discovered = [{"cli": "codex", "model_id": "gpt-5.6-sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, {}, False, [], False, existing)
        self.assertEqual(unmatched, [])
        self.assertEqual(len(catalog), 1)
        self.assertIn("openai/gpt-5.6-sol", catalog)
        self.assertNotIn("gpt-5.6-sol/gpt-5.6-sol", catalog)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertEqual(entry["provider"], "openai")
        self.assertEqual(entry["scores"]["intelligence_index"], 91.0)  # preserved, not wiped

    def test_a_mis_keyed_entry_self_heals_once_a_real_match_comes_back(self):
        # Important finding (#2, coordinator review): `existing_key` recovery must ONLY apply
        # when this run genuinely has no signal of its own (md_match AND aa_match both None) --
        # the function's own docstring already said "neither source matched THIS run", but the
        # original code consulted `existing_key` for the final `key` UNCONDITIONALLY, so a
        # catalog entry that got mis-keyed while a source was down (e.g. self-referential
        # "gpt-5.6-sol/gpt-5.6-sol", minted during an earlier outage) could never self-heal --
        # even once the source came back with a real, authoritative match, the stale key kept
        # winning forever. Here "gpt-5.6-sol/gpt-5.6-sol" is the pre-existing (wrong) entry;
        # models.dev is back up this run and genuinely matches "gpt-5.6-sol" to "openai" --
        # the fresh match must win, landing under "openai/gpt-5.6-sol", not the stale key.
        existing = {"gpt-5.6-sol/gpt-5.6-sol": {
            "provider": "gpt-5.6-sol",
            "runtimes": {"codex": {"model_id": "gpt-5.6-sol"}},
            "source": {"models_dev": False, "artificial_analysis": False}, "confidence": "low",
            "last_verified": "2026-08-01"}}
        models_dev_data = {"openai": {"models": {"gpt-5.6-sol": {"id": "gpt-5.6-sol"}}}}
        discovered = [{"cli": "codex", "model_id": "gpt-5.6-sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, [], True, existing)
        self.assertEqual(unmatched, [])
        self.assertIn("openai/gpt-5.6-sol", catalog)
        self.assertEqual(catalog["openai/gpt-5.6-sol"]["provider"], "openai")

    def test_brand_new_unmatched_bare_id_with_no_vendor_signal_gets_provider_none(self):
        # Important finding (#4, coordinator review): a brand-new (never-cached) bare id (no
        # "<vendor>/" prefix) with BOTH sources down and NO existing catalog entry to recover
        # from has genuinely zero vendor signal -- falling back to `provider = model_id` used to
        # mint a plausible-looking but entirely fabricated self-referential "model_id/model_id"
        # key on the UNMATCHED candidate payload surfaced to the wizard (Task 8), which could
        # be accidentally trusted and persisted as-is later. `provider=None` +
        # `vendor_unknown=True` forces whatever confirms this candidate later to supply a real
        # vendor. Distinct from the recoverable case above (test_bare_id_with_both_sources_
        # unavailable_recovers_key_from_existing_catalog), which still gets its real recovered
        # provider, not None.
        discovered = [{"cli": "codex", "model_id": "totally-unknown-bare-id"}]
        _, _, unmatched = cli.build_model_catalog(discovered, {}, False, [], False, {})
        self.assertEqual(len(unmatched), 1)
        self.assertIsNone(unmatched[0]["provider"])
        self.assertTrue(unmatched[0]["vendor_unknown"])
        self.assertIsNone(unmatched[0]["key"])

    def test_recoverable_unmatched_candidate_is_not_flagged_vendor_unknown(self):
        # Contrast case for the above: when `existing_key` recovery succeeds, `vendor_unknown`
        # must read False and `provider` must be the real recovered vendor, not None.
        existing = {"vendor/totally-unknown": {"provider": "vendor",
                                                 "runtimes": {"codex": {"model_id": "bare-id"}},
                                                 "source": {}, "confidence": "low",
                                                 "last_verified": "2026-08-01"}}
        discovered = [{"cli": "codex", "model_id": "bare-id"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, {}, False, [], False, existing)
        self.assertEqual(unmatched, [])
        self.assertIn("vendor/totally-unknown", catalog)
        self.assertEqual(catalog["vendor/totally-unknown"]["provider"], "vendor")

    def test_aa_match_with_no_usable_model_creator_name_routes_to_unmatched_without_crashing(self):
        # Important finding (round-2 re-review): a bare id (no "<vendor>/" prefix) that matches
        # Artificial Analysis (aa_match IS truthy) but whose own `model_creator` is missing/empty
        # used to fall through to the matched/enrichment branch with `provider=None` -- because
        # the old unmatched-routing check was `md_match is None and aa_match is None and
        # existing_entry is None`, which is False here (aa_match is not None) even though
        # `provider` itself ended up None. That reached an unguarded
        # `_infer_heuristics(provider, model_id)` call in the matched path and raised
        # `AttributeError: 'NoneType' object has no attribute 'lower'`, aborting the ENTIRE
        # build_model_catalog run (losing every other candidate in the same batch, not just this
        # one). Must instead land safely in `unmatched` with provider=None/vendor_unknown=True,
        # exactly like the zero-signal case, and must NOT raise.
        aa_models = [{"id": "1", "slug": "gpt-5-6-sol", "name": "GPT-5.6 Sol",
                      "model_creator": {},  # no "name" at all
                      "evaluations": {"artificial_analysis_intelligence_index": 91.0}}]
        discovered = [{"cli": "codex", "model_id": "gpt-5.6-sol"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, {}, False, aa_models, True, {})  # models_dev_ok=False -> md_match None
        self.assertEqual(rejections, [])
        self.assertEqual(len(unmatched), 1)
        self.assertIsNone(unmatched[0]["provider"])
        self.assertTrue(unmatched[0]["vendor_unknown"])
        self.assertEqual(catalog, {})  # never silently added to the catalog either

    def test_md_enrich_match_provider_field_never_influences_provider_or_key_derivation(self):
        # md_enrich_match's OWN "provider" field can legitimately differ from
        # aa_provider_hint (a single, non-colliding models.dev row always wins regardless of
        # hint) -- this must never leak into provider/key derivation, which read only
        # md_match/provider_hint/AA's model_creator.name. Uses a raw id
        # ("claude-opus-5-thinking-xhigh") whose fuzzy ratio against the single stripped-form
        # candidate ("claude-opus-5") is ~0.63 -- well under the PRIMARY call's own 0.82
        # threshold -- so the primary call cannot resolve this on its own; only the retry's
        # exact match on the STRIPPED id (Attempt 2) can. (A real 16-provider
        # single-row-per-provider case would behave the same way; a single provider here is
        # enough to isolate this specific invariant.)
        models_dev_data = {"some-other-provider": {"models": {"claude-opus-5": {
            "id": "claude-opus-5", "tool_call": True, "structured_output": True,
            "limit": {"context": 1000000, "output": 128000}}}}}
        aa_models = [{"id": "1", "slug": "claude-opus-5-thinking-xhigh",
                      "name": "Claude Opus 5 Thinking XHigh",
                      "model_creator": {"name": "Anthropic"},
                      "evaluations": {"artificial_analysis_intelligence_index": 61.5}}]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-thinking-xhigh"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        self.assertIn("anthropic/claude-opus-5-thinking-xhigh", catalog)
        entry = catalog["anthropic/claude-opus-5-thinking-xhigh"]
        self.assertEqual(entry["provider"], "anthropic")   # from AA's model_creator, not
        self.assertTrue(entry["structured_output"])        # "some-other-provider"

    def test_pricing_after_a_successful_retry_still_comes_from_aa_never_the_base_models_cost(self):
        # A real multi-provider collision on the STRIPPED id ("claude-opus-5") is required
        # so the PRIMARY call (no hint, fuzzy-enabled) can't resolve the raw suffixed id on
        # its own -- with only one provider, a single fuzzy match would win regardless of
        # hint AT THE PRIMARY STAGE, meaning pricing would legitimately come from that
        # primary match's own models.dev cost instead of exercising this spec's
        # enrichment-only retry at all.
        models_dev_data = {
            "anthropic": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": True,
                "limit": {"context": 1000000, "output": 128000},
                "cost": {"input": 6.0, "output": 30.0}}}},
            "some-reseller": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": None,
                "limit": {"context": 1000000, "output": 128000},
                "cost": {"input": 0.0, "output": 0.0}}}},
        }
        aa_models = [{"id": "1", "slug": "claude-opus-5-high", "name": "Claude Opus 5 High",
                      "model_creator": {"name": "Anthropic"},
                      "evaluations": {"artificial_analysis_intelligence_index": 61.5},
                      "pricing": {"price_1m_input_tokens": 15.0,
                                  "price_1m_output_tokens": 75.0}}]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-high"}]
        catalog, _, _ = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        entry = catalog["anthropic/claude-opus-5-high"]
        self.assertEqual(entry["pricing"]["input_per_1m"], 15.0)   # AA's effort-specific price
        self.assertEqual(entry["pricing"]["output_per_1m"], 75.0)  # never the base model's 6.0/30.0

    def test_vendor_prefixed_id_with_an_effort_suffix_also_reaches_the_retry(self):
        # A prefixed id doesn't skip the need for this fallback either -- step 1's exact
        # lookup misses the suffix exactly as the bare case does, and the pool-fuzzy step
        # also finds nothing for this example (ratio("gpt5high","gpt5") ~= 0.667, well under
        # the 0.82 threshold).
        models_dev_data = {"openai": {"models": {"gpt-5": {
            "id": "gpt-5", "tool_call": True, "structured_output": True,
            "limit": {"context": 400000, "output": 128000}}}}}
        aa_models = [{"id": "1", "slug": "gpt-5-high", "name": "GPT-5 High",
                      "model_creator": {"name": "OpenAI"},
                      "evaluations": {"artificial_analysis_intelligence_index": 70.0}}]
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5-high"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["openai/gpt-5-high"]
        self.assertTrue(entry["structured_output"])
        self.assertEqual(entry["runtimes"]["opencode"]["ctx_window"], 400000)
        # Discriminates the retry path from an (incorrect) primary fuzzy match: if the
        # primary call ever started resolving "openai/gpt-5-high" directly, source.models_dev
        # would read True and this assertion would catch it -- the two asserts above alone
        # would still pass either way, so they can't guard this invariant on their own.
        self.assertFalse(entry["source"]["models_dev"])

    def test_end_to_end_regression_claude_opus_5_high_shape_and_its_fast_sibling(self):
        # Regression fixture mirroring the real motivating case: claude-opus-5-high
        # backfills via this spec's retry; its -fast-suffixed sibling
        # (claude-opus-5-high-fast) resolves via the PRIMARY call's own fuzzy step directly
        # (never reaching this spec's retry at all) and must never have its price/context
        # conflated with the non-fast base model's.
        models_dev_data = {
            "anthropic": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": True,
                "limit": {"context": 1000000, "output": 128000},
                "cost": {"input": 6.0, "output": 30.0}}}},
            "some-reseller": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": None,
                "limit": {"context": 1000000, "output": 128000},
                "cost": {"input": 0.0, "output": 0.0}}}},
            "venice": {"models": {"claude-opus-5-fast": {
                "id": "claude-opus-5-fast", "tool_call": True, "structured_output": True,
                "limit": {"context": 1000000, "output": 128000},
                "cost": {"input": 12.0, "output": 60.0}}}},
        }
        aa_models = [
            {"id": "1", "slug": "claude-opus-5-high", "name": "Claude Opus 5 High",
             "model_creator": {"name": "Anthropic"},
             "evaluations": {"artificial_analysis_intelligence_index": 61.5},
             "pricing": {"price_1m_input_tokens": 15.0, "price_1m_output_tokens": 75.0}},
            {"id": "2", "slug": "claude-opus-5-high-fast", "name": "Claude Opus 5 High Fast",
             "model_creator": {"name": "Anthropic"},
             "evaluations": {"artificial_analysis_intelligence_index": 61.5},
             "pricing": {"price_1m_input_tokens": 30.0, "price_1m_output_tokens": 150.0}},
        ]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-high"},
                      {"cli": "cursor-agent", "model_id": "claude-opus-5-high-fast"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(rejections, [])
        self.assertEqual(unmatched, [])

        base = catalog["anthropic/claude-opus-5-high"]
        self.assertTrue(base["structured_output"])          # anthropic's row, not the reseller's
        self.assertTrue(base["tool_calling"])
        self.assertEqual(base["max_output_tokens"], 128000)
        self.assertEqual(base["runtimes"]["cursor-agent"]["ctx_window"], 1000000)
        self.assertFalse(base["source"]["models_dev"])          # enrichment, not an exact match
        self.assertEqual(base["scores"]["intelligence_index"], 61.5)
        self.assertEqual(base["pricing"]["input_per_1m"], 15.0)  # AA's, never models.dev's 6.0

        fast = catalog["venice/claude-opus-5-high-fast"]
        self.assertTrue(fast["source"]["models_dev"])           # resolved by the PRIMARY fuzzy step
        self.assertEqual(fast["runtimes"]["cursor-agent"]["ctx_window"], 1000000)
        self.assertEqual(fast["pricing"]["input_per_1m"], 12.0)  # its own tier's price, not the
                                                                  # base model's 6.0


class TestFetchModelCatalogCli(unittest.TestCase):
    def _write_runtimes(self, d, clis):
        path = os.path.join(d, "runtimes.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"clis": clis}, f)
        return path

    def _write_fresh_fetch_meta(self, catalog_path):
        # Important finding (coordinator review): freshness for `--if-stale` is now tracked via
        # a dedicated `<catalog_path>.fetch-meta.json` sidecar (mtime-based, same cache_is_stale
        # mechanism, but written ONLY on a real fetch -- never on every catalog write) rather
        # than the catalog file's own mtime. Every test below that wants to stay network-free
        # under `--if-stale` must seed THIS file fresh, not just the catalog file.
        with open(catalog_path + ".fetch-meta.json", "w", encoding="utf-8") as f:
            json.dump({"last_fetched": time.time()}, f)

    def _never_fetch_models_dev(self):
        self.fail("fetch_models_dev_fn should not be called on a skip_fetch run")

    def _never_fetch_aa(self, api_key):
        self.fail("fetch_artificial_analysis_fn should not be called on a skip_fetch run")

    def test_if_stale_with_a_fresh_catalog_skips_fetch_but_still_reports_new_candidates(self):
        # CRITICAL finding: freshness must gate the network fetch only, never candidate
        # discovery -- a brand-new model must still surface as `unmatched`, not be silently
        # missed until the cache goes stale.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            self._write_fresh_fetch_meta(catalog_path)
            runtimes_path = self._write_runtimes(
                d, {"opencode": {"installed": True, "models": ["vendor/brand-new"]}})
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(
                    ["fetch-model-catalog", "--runtimes-json", runtimes_path,
                     "--catalog-path", catalog_path, "--if-stale"],
                    fetch_models_dev_fn=self._never_fetch_models_dev,
                    fetch_artificial_analysis_fn=self._never_fetch_aa)
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertTrue(result["fetch_skipped"])
            self.assertEqual(len(result["unmatched"]), 1)
            self.assertEqual(result["unmatched"][0]["model_id"], "vendor/brand-new")

    def test_if_stale_skip_never_touches_the_fetch_freshness_marker(self):
        # Important finding (coordinator review): a skip_fetch run must leave the fetch-meta
        # sidecar file completely untouched (content AND mtime) -- otherwise a subsequent
        # --if-stale run would (wrongly) see it as freshly re-verified and keep extending the
        # TTL window forever without ever actually re-fetching. Seed a meta file with an old
        # `last_fetched` epoch (already outside CATALOG_TTL_SECONDS, so a real fetch WOULD be
        # warranted by that timestamp) but a very recent mtime (so cache_is_stale's mtime check
        # alone would call it fresh) -- proving staleness is judged by the file's mtime here
        # (same cache_is_stale mechanism as everywhere else in this codebase), and that a
        # skipped run leaves that mtime/content alone rather than refreshing it.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            meta_path = catalog_path + ".fetch-meta.json"
            original_marker = {"last_fetched": 12345.0}
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(original_marker, f)
            before_mtime = os.stat(meta_path).st_mtime
            runtimes_path = self._write_runtimes(d, {})
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(
                    ["fetch-model-catalog", "--runtimes-json", runtimes_path,
                     "--catalog-path", catalog_path, "--if-stale"],
                    fetch_models_dev_fn=self._never_fetch_models_dev,
                    fetch_artificial_analysis_fn=self._never_fetch_aa)
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertTrue(result["fetch_skipped"])  # mtime is fresh -> still skipped
            self.assertEqual(os.stat(meta_path).st_mtime, before_mtime)  # untouched
            self.assertEqual(cache_read_json(meta_path), original_marker)  # content untouched

    def test_a_real_fetch_updates_the_freshness_marker_only_when_a_source_answered(self):
        # Important finding (coordinator review): the freshness marker must be written when a
        # real fetch runs and at least one source came back ok=True -- exercising the injectable
        # fetch_models_dev_fn/fetch_artificial_analysis_fn hooks (Important finding #3: the real
        # fetch branch previously had no injection point at all and was never covered by tests).
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            runtimes_path = self._write_runtimes(d, {})
            meta_path = catalog_path + ".fetch-meta.json"
            self.assertFalse(os.path.exists(meta_path))
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(
                    ["fetch-model-catalog", "--runtimes-json", runtimes_path,
                     "--catalog-path", catalog_path],  # no --if-stale -- always fetches
                    fetch_models_dev_fn=lambda: ({}, True),
                    fetch_artificial_analysis_fn=lambda api_key: ([], True),
                    load_secret_fn=lambda env, key: None)
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertTrue(result["models_dev_ok"])
            self.assertTrue(os.path.exists(meta_path))
            self.assertIsInstance(cache_read_json(meta_path)["last_fetched"], float)

    def test_no_api_key_is_treated_as_source_skipped_not_a_genuine_no_match(self):
        # CRITICAL finding (#3, coordinator review): this is the line that was never actually
        # exercised by any test before -- `aa_ok = aa_fetch_ok and bool(api_key)`. Inject a
        # fetch_artificial_analysis_fn that WOULD succeed (ok=True, real data) to prove the
        # missing API key -- not a fetch failure -- is what collapses aa_ok to False here.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            runtimes_path = self._write_runtimes(d, {})
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(
                    ["fetch-model-catalog", "--runtimes-json", runtimes_path,
                     "--catalog-path", catalog_path],
                    fetch_models_dev_fn=lambda: ({}, True),
                    fetch_artificial_analysis_fn=lambda api_key: (
                        [{"id": "1", "slug": "x"}], True),  # source itself would have succeeded
                    load_secret_fn=lambda env, key: None)  # ...but no key is configured
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertFalse(result["artificial_analysis_ok"])

    def test_extra_candidate_flag_is_included_in_discovery(self):
        # --if-stale + a fresh fetch-meta sidecar keeps this test network-free (see the
        # skip-fetch test above) while still proving --extra-candidate reaches `discovered` --
        # discovery/reconciliation runs unconditionally, network fetching is what's gated.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            self._write_fresh_fetch_meta(catalog_path)
            runtimes_path = self._write_runtimes(d, {})
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(
                    ["fetch-model-catalog", "--runtimes-json", runtimes_path,
                     "--catalog-path", catalog_path, "--if-stale",
                     "--extra-candidate", "codex:vendor/typed-in-model"],
                    fetch_models_dev_fn=self._never_fetch_models_dev,
                    fetch_artificial_analysis_fn=self._never_fetch_aa)
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertIn({"cli": "codex", "model_id": "vendor/typed-in-model"},
                           result["discovered"])

    def test_single_provider_cli_candidate_pulled_from_review_spec_toml(self):
        # Same network-free technique as above (--if-stale + a fresh fetch-meta sidecar).
        # HIGH finding: this resolves review-spec.toml's global-merge path too (cfg_resolve),
        # so `env_fn` MUST point HOME at this tempdir -- never the real dict(os.environ) --
        # or this test would silently read whatever global config exists on the machine
        # actually running the suite.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            self._write_fresh_fetch_meta(catalog_path)
            runtimes_path = self._write_runtimes(
                d, {"codex": {"installed": True}})  # no "models" key -- single-provider
            local_cfg = os.path.join(d, ".aikit", "review-spec.toml")
            os.makedirs(os.path.dirname(local_cfg))
            with open(local_cfg, "w", encoding="utf-8") as f:
                f.write('[[reviewers]]\nkey = "codex-primary"\nmodel = "vendor/already-registered"\n'
                        'vendor = "vendor"\ncli = "codex"\n')
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(
                    ["fetch-model-catalog", "--runtimes-json", runtimes_path,
                     "--catalog-path", catalog_path, "--cwd", d, "--if-stale"],
                    env_fn=lambda: {"HOME": d},
                    fetch_models_dev_fn=self._never_fetch_models_dev,
                    fetch_artificial_analysis_fn=self._never_fetch_aa)
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertIn({"cli": "codex", "model_id": "vendor/already-registered"},
                           result["discovered"])

    def test_confirm_catalog_entry_rejects_invalid_entry_with_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            entry_path = os.path.join(d, "entry.json")
            with open(entry_path, "w", encoding="utf-8") as f:
                json.dump({"model_id": "vendor/x", "entry": {"provider": "vendor"}}, f)  # missing fields
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["confirm-catalog-entry", "--catalog-path", catalog_path,
                                 "--entry-json", entry_path])
            self.assertEqual(code, 1)
            result = json.loads(buf.getvalue())
            self.assertFalse(result["confirmed"])
            self.assertEqual(cache_read_json(catalog_path), {})  # unchanged, no partial write

    def test_confirm_catalog_entry_rejects_malformed_payload_without_raising(self):
        # Important finding (#5, coordinator review): a missing/malformed --entry-json used to
        # raise a bare KeyError traceback (payload["model_id"]/payload["entry"] unguarded) --
        # unlike every other failure path across these three subcommands, which return
        # structured JSON + exit 1. Covers both "model_id" and "entry" missing entirely.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            entry_path = os.path.join(d, "entry.json")
            with open(entry_path, "w", encoding="utf-8") as f:
                json.dump({"model_id": "vendor/x"}, f)  # "entry" entirely missing
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["confirm-catalog-entry", "--catalog-path", catalog_path,
                                 "--entry-json", entry_path])
            self.assertEqual(code, 1)
            result = json.loads(buf.getvalue())
            self.assertFalse(result["confirmed"])
            self.assertIn("reason", result)
            self.assertEqual(cache_read_json(catalog_path), {})  # unchanged, no partial write

    def test_apply_heuristic_correction_writes_through_the_atomic_cache_api(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            existing = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                          "source": {}, "confidence": "low",
                                          "last_verified": "2026-09-02", "is_router": True}}
            cache_write_json(catalog_path, existing)
            corrections_path = os.path.join(d, "corrections.json")
            with open(corrections_path, "w", encoding="utf-8") as f:
                json.dump({"is_router": False}, f)
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["apply-heuristic-correction", "--catalog-path", catalog_path,
                                 "--model-id", "router-env/x",
                                 "--corrections-json", corrections_path])
            self.assertEqual(code, 0)
            self.assertFalse(cache_read_json(catalog_path)["router-env/x"]["is_router"])

    def test_apply_heuristic_correction_rejects_invalid_correction_with_nonzero_exit(self):
        # CRITICAL finding: a correction that would make the merged entry schema-invalid must
        # be rejected (nonzero exit, no write) -- cache_write_json alone never validates.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            existing = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                          "source": {}, "confidence": "low",
                                          "last_verified": "2026-09-02", "is_router": True}}
            cache_write_json(catalog_path, existing)
            corrections_path = os.path.join(d, "corrections.json")
            with open(corrections_path, "w", encoding="utf-8") as f:
                json.dump({"is_router": "not-a-bool"}, f)
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["apply-heuristic-correction", "--catalog-path", catalog_path,
                                 "--model-id", "router-env/x",
                                 "--corrections-json", corrections_path])
            self.assertEqual(code, 1)
            result = json.loads(buf.getvalue())
            self.assertFalse(result["applied"])
            self.assertTrue(cache_read_json(catalog_path)["router-env/x"]["is_router"])  # unchanged


if __name__ == "__main__":
    unittest.main()
