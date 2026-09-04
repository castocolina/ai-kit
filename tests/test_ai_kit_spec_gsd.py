import os
import sys
import unittest
from unittest import mock

# Bootstraps ALL package roots this plan's tests need -- ai_kit_spec_gsd (this plan) and
# ai_kit_spec (Plan 1, Foundation) both live outside this file's own directory, on no search
# path by default. skills/ai-kit-spec-execute is ALSO added here (not just
# skills/ai-kit-spec-execute-gsd) because Task 6's detect_framework module lives there and this is
# the ONE bootstrap block for the whole file -- it goes ONCE at the top; every later Task in this
# plan appends test classes below it, never repeats it.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute-gsd"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute"))

import detect_framework
from ai_kit_spec import execute_selection
from ai_kit_spec_gsd import adapter, cli, cross_ai_guidance, gsd_config, gsd_cross_ai


class TestReadGsdConfig(unittest.TestCase):
    def test_returns_empty_dict_and_missing_status_when_file_missing(self):
        def raise_not_found(*a, **k):
            raise FileNotFoundError()
        warnings = []
        config, status = gsd_config.read_gsd_config("/nonexistent", read_fn=raise_not_found,
                                                      warn_fn=warnings.append)
        self.assertEqual(config, {})
        self.assertEqual(status, "missing")
        self.assertEqual(warnings, [])  # missing file is a valid state -- no warning

    def test_parses_real_config_shape_with_ok_status(self):
        import io
        fake = io.StringIO('{"runtime": "codex", "model_profile_overrides": '
                            '{"codex": {"sonnet": "gpt-5.6-sol"}}}')
        config, status = gsd_config.read_gsd_config("/x", read_fn=lambda *a, **k: fake)
        self.assertEqual(config["runtime"], "codex")
        self.assertEqual(status, "ok")

    def test_malformed_json_warns_and_returns_empty_dict_with_malformed_status(self):
        import io
        fake = io.StringIO("not valid json {{{")
        warnings = []
        config, status = gsd_config.read_gsd_config("/x", read_fn=lambda *a, **k: fake,
                                                      warn_fn=warnings.append)
        self.assertEqual(config, {})
        self.assertEqual(status, "malformed")
        self.assertEqual(len(warnings), 1)
        self.assertIn("/x", warnings[0])


class TestResolveActiveRuntime(unittest.TestCase):
    def test_defaults_to_claude_when_unset(self):
        # Task 1 finding 2: runtime's real default is null, which reads as "claude" -- never a
        # None/"unknown" sentinel.
        self.assertEqual(gsd_config.resolve_active_runtime({}), "claude")

    def test_reads_the_configured_value(self):
        self.assertEqual(gsd_config.resolve_active_runtime({"runtime": "codex"}), "codex")


class TestWriteActiveRuntime(unittest.TestCase):
    def test_writes_runtime_key_records_ownership_marker_and_preserves_other_keys(self):
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        result = gsd_config.write_active_runtime(
            "/repo/.planning/config.json", {"model_profile": "balanced"}, "codex",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(result["runtime"], "codex")
        self.assertEqual(result["model_profile"], "balanced")  # untouched
        self.assertEqual(writes["/repo/.planning/config.json"]["runtime"], "codex")
        self.assertEqual(result["_ai_kit_spec_execute_gsd"]["runtime"], "codex")


class TestResolveNativeTier(unittest.TestCase):
    def test_reads_the_nested_runtime_and_tier_slot(self):
        config = {"model_profile_overrides": {"codex": {"sonnet": "gpt-5.6-sol"}}}
        self.assertEqual(gsd_config.resolve_native_tier(config, "codex", "sonnet"),
                          "gpt-5.6-sol")

    def test_returns_none_without_crashing_when_any_level_is_missing(self):
        self.assertIsNone(gsd_config.resolve_native_tier({}, "codex", "sonnet"))
        self.assertIsNone(gsd_config.resolve_native_tier(
            {"model_profile_overrides": {"claude": {"opus": "claude-opus-5"}}},
            "codex", "sonnet"))


class TestWriteNativeTierOverride(unittest.TestCase):
    def test_writes_nested_override_records_ownership_marker_and_preserves_other_runtimes(self):
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        existing = {"model_profile_overrides": {"claude": {"opus": "claude-opus-5"}}}
        result = gsd_config.write_native_tier_override(
            "/repo/.planning/config.json", existing, "codex", "sonnet", "gpt-5.6-sol",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(result["model_profile_overrides"]["codex"]["sonnet"], "gpt-5.6-sol")
        self.assertEqual(result["model_profile_overrides"]["claude"]["opus"], "claude-opus-5")
        self.assertEqual(result["_ai_kit_spec_execute_gsd"]["overrides"]["codex"]["sonnet"],
                          "gpt-5.6-sol")
        self.assertEqual(writes["/repo/.planning/config.json"]
                          ["model_profile_overrides"]["codex"]["sonnet"], "gpt-5.6-sol")

    def test_backs_up_existing_config_once_before_first_write_of_this_run(self):
        copies = []
        def fake_copy(src, dst):
            copies.append((src, dst))
        gsd_config.write_native_tier_override(
            "/repo/.planning/config.json", {}, "codex", "sonnet", "gpt-5.6-sol",
            write_fn=lambda *a: None, backup_copy_fn=fake_copy,
            isfile_fn=lambda p: p == "/repo/.planning/config.json", run_id="run-1")
        self.assertEqual(copies, [("/repo/.planning/config.json",
                                    "/repo/.planning/config.json.ai-kit-spec-execute-gsd.run-1.bak")])

    def test_a_later_run_gets_its_own_distinct_backup_path(self):
        copies = []
        def fake_copy(src, dst):
            copies.append(dst)
        gsd_config.write_native_tier_override(
            "/repo/.planning/config.json", {}, "codex", "sonnet", "gpt-5.6-sol",
            write_fn=lambda *a: None, backup_copy_fn=fake_copy,
            isfile_fn=lambda p: p == "/repo/.planning/config.json", run_id="run-2")
        self.assertEqual(copies, ["/repo/.planning/config.json.ai-kit-spec-execute-gsd.run-2.bak"])


class TestOverrideIsAdapterOwned(unittest.TestCase):
    def test_true_when_marker_matches_current_override_exactly(self):
        config = {"model_profile_overrides": {"codex": {"sonnet": "gpt-5.6-sol"}},
                  "_ai_kit_spec_execute_gsd": {"overrides": {"codex": {"sonnet": "gpt-5.6-sol"}}}}
        self.assertTrue(gsd_config.override_is_adapter_owned(config, "codex", "sonnet"))

    def test_false_when_no_marker_present_at_all(self):
        # A genuine, hand-written user override -- never touched.
        config = {"model_profile_overrides": {"codex": {"sonnet": "gpt-5.6-sol"}}}
        self.assertFalse(gsd_config.override_is_adapter_owned(config, "codex", "sonnet"))

    def test_false_when_marker_present_but_value_no_longer_matches(self):
        config = {"model_profile_overrides": {"codex": {"sonnet": "hand-edited"}},
                  "_ai_kit_spec_execute_gsd": {"overrides": {"codex": {"sonnet": "gpt-5.6-sol"}}}}
        self.assertFalse(gsd_config.override_is_adapter_owned(config, "codex", "sonnet"))


class TestResolveGsdConfigPath(unittest.TestCase):
    def test_defaults_to_project_root_planning_config(self):
        self.assertEqual(gsd_config.resolve_gsd_config_path("/repo"),
                          "/repo/.planning/config.json")


class TestWriteWorkflowKey(unittest.TestCase):
    def test_writes_key_under_workflow_and_preserves_other_keys(self):
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        result = gsd_config.write_workflow_key(
            "/repo/.planning/config.json",
            {"model_profile": "balanced", "workflow": {"other_key": "keep-me"}},
            "cross_ai_command", "codex exec ...",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(result["workflow"]["cross_ai_command"], "codex exec ...")
        self.assertEqual(result["workflow"]["other_key"], "keep-me")  # untouched
        self.assertEqual(result["model_profile"], "balanced")  # untouched
        self.assertEqual(writes["/repo/.planning/config.json"]["workflow"]["cross_ai_command"],
                          "codex exec ...")

    def test_a_second_write_against_the_first_writes_own_returned_dict_keeps_both_keys(self):
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        first_result = gsd_config.write_workflow_key(
            "/repo/.planning/config.json", {}, "cross_ai_command", "codex exec ...",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        second_result = gsd_config.write_workflow_key(
            "/repo/.planning/config.json", first_result, "cross_ai_execution", True,
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(second_result["workflow"]["cross_ai_command"], "codex exec ...")
        self.assertEqual(second_result["workflow"]["cross_ai_execution"], True)


class TestWorkflowKeyOwnershipAndClearing(unittest.TestCase):
    def test_clear_workflow_key_if_adapter_owned_removes_an_adapter_owned_key(self):
        config = {"workflow": {"cross_ai_command": "codex exec ...", "other_key": "keep-me"},
                  "_ai_kit_spec_execute_gsd": {"workflow": {"cross_ai_command": "codex exec ..."}}}
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        result = gsd_config.clear_workflow_key_if_adapter_owned(
            "/repo/.planning/config.json", config, "cross_ai_command", write_fn=fake_write,
            backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False, run_id="run-1")
        self.assertNotIn("cross_ai_command", result["workflow"])
        self.assertEqual(result["workflow"]["other_key"], "keep-me")
        self.assertNotIn("cross_ai_command", result["_ai_kit_spec_execute_gsd"]["workflow"])

    def test_clear_workflow_key_if_adapter_owned_never_touches_a_genuine_user_value(self):
        config = {"workflow": {"cross_ai_command": "user-set-command"}}
        write_calls = []
        result = gsd_config.clear_workflow_key_if_adapter_owned(
            "/repo/.planning/config.json", config, "cross_ai_command",
            write_fn=lambda *a: write_calls.append(a), backup_copy_fn=lambda *a: None,
            isfile_fn=lambda p: False, run_id="run-1")
        self.assertEqual(result, config)
        self.assertEqual(write_calls, [])


class TestKnownGsdRuntimes(unittest.TestCase):
    def test_contains_every_task_1_confirmed_runtime(self):
        for runtime in ("claude", "codex", "gemini", "opencode", "qwen", "kilo", "copilot",
                         "grok", "cursor", "windsurf", "augment", "trae", "codebuddy", "cline",
                         "antigravity"):
            self.assertIn(runtime, gsd_config.KNOWN_GSD_RUNTIMES)


class TestBuildCrossAiCommand(unittest.TestCase):
    def test_native_cli_none_returns_none(self):
        # cli=None is native/current-session dispatch -- never needs the cross-AI hook.
        candidate = {"cli": None, "model": "opus", "key": "opus-native"}
        self.assertIsNone(gsd_cross_ai.build_cross_ai_command(candidate, "/repo"))

    def test_cli_in_known_gsd_runtimes_still_builds_when_it_has_a_real_execute_builder(self):
        # Bug fix (2026-08-30): a cli name being in KNOWN_GSD_RUNTIMES must NOT by itself block
        # the cross-AI hook -- adapter.py already tried (and failed) the curated-tier native route
        # before ever calling this function, so a live-verified execute builder must still be used.
        candidate = {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol"}
        result = gsd_cross_ai.build_cross_ai_command(candidate, "/repo")
        self.assertEqual(
            result,
            "codex exec --sandbox workspace-write --skip-git-repo-check -C /repo -m gpt-5.6-sol")

    def test_no_live_verified_builder_returns_none_not_raise(self):
        # A CLI with no registered execute-mode builder at all (Foundation's real
        # build_execute_command raises ValueError for it) must degrade to None, never raise.
        candidate = {"cli": "gemini", "model": "gemini-3.1-pro", "key": "gemini/gemini-3.1-pro"}
        self.assertIsNone(gsd_cross_ai.build_cross_ai_command(candidate, "/repo"))

    def test_builds_the_real_command_string_with_model_filled_in(self):
        # Injected fake builder -- exercises this module's plumbing without depending on which
        # CLIs Foundation has actually implemented today.
        def fake_execute_command(cli, target_dir, effort=None, service_tier=None):
            return f"future-cli exec --write -C {target_dir} -m {{model}}"
        candidate = {"cli": "future-cli", "model": "gpt-5.6-terra",
                     "key": "future-cli/gpt-5.6-terra"}
        result = gsd_cross_ai.build_cross_ai_command(
            candidate, "/repo/worktree", execute_command_fn=fake_execute_command)
        self.assertEqual(result, "future-cli exec --write -C /repo/worktree -m gpt-5.6-terra")
        # This IS the literal string, no wrapper/shim indirection whatsoever (Task 1 finding 1 --
        # GSD itself pipes the phase prompt into this command's own stdin and captures its own
        # stdout; a wrapper would only get in the way of that).
        self.assertNotIn("ai-kit-spec-gsd.py", result)

    def test_threads_effort_and_service_tier_into_the_execute_builder(self):
        captured = {}

        def fake_execute_command(cli, target_dir, effort=None, service_tier=None):
            captured["effort"] = effort
            captured["service_tier"] = service_tier
            return f"codex exec -C {target_dir} -m {{model}}"

        candidate = {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                     "effort": "high", "service_tier": "priority"}
        gsd_cross_ai.build_cross_ai_command(
            candidate, "/repo/worktree", execute_command_fn=fake_execute_command)
        self.assertEqual(captured["effort"], "high")
        self.assertEqual(captured["service_tier"], "priority")


class TestAssembleCandidates(unittest.TestCase):
    def test_reshapes_cfg_reviewers_with_open_risk_fields_none_and_no_curated_tier(self):
        def fake_cfg_resolve(cwd, env):
            return {"policy": {"ladder": ["codex/gpt-5.6-sol"]},
                    "reviewers": [{"key": "codex/gpt-5.6-sol", "model": "gpt-5.6-sol",
                                    "vendor": "openai", "cli": "codex"}]}
        candidates, top_n_keys = adapter.assemble_candidates(
            "/repo", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertEqual(candidates, [{"key": "codex/gpt-5.6-sol", "model": "gpt-5.6-sol",
                                        "cli": "codex", "vendor": "openai", "command": None,
                                        "task_affinity": None, "context_limit": None,
                                        "tier": None}])
        self.assertEqual(top_n_keys, ["codex/gpt-5.6-sol"])

    def test_native_cli_none_entry_derives_tier_from_its_own_model_field(self):
        # This repo's own "opus-native"-shaped entries: model IS already a tier alias.
        def fake_cfg_resolve(cwd, env):
            return {"policy": {"ladder": ["opus-native"]},
                    "reviewers": [{"key": "opus-native", "model": "opus", "vendor": "",
                                    "cli": None}]}
        candidates, _ = adapter.assemble_candidates("/repo", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertEqual(candidates[0]["tier"], "opus")

    def test_curated_tier_field_takes_priority_over_the_derived_default(self):
        def fake_cfg_resolve(cwd, env):
            return {"policy": {"ladder": ["codex/gpt-5.6-sol"]},
                    "reviewers": [{"key": "codex/gpt-5.6-sol", "model": "gpt-5.6-sol",
                                    "vendor": "openai", "cli": "codex", "tier": "sonnet",
                                    "command": "codex exec -m {model} -- {prompt}",
                                    "task_affinity": "backend", "context_limit": 128000}]}
        candidates, _ = adapter.assemble_candidates("/repo", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertEqual(candidates[0]["tier"], "sonnet")
        self.assertEqual(candidates[0]["command"], "codex exec -m {model} -- {prompt}")
        self.assertEqual(candidates[0]["task_affinity"], "backend")
        self.assertEqual(candidates[0]["context_limit"], 128000)


class TestEstimateRequiredContext(unittest.TestCase):
    def test_estimates_a_real_nonzero_value_from_the_actual_phase_prompt(self):
        prompt = "x" * 4000
        self.assertEqual(adapter.estimate_required_context(prompt), 1000)

    def test_empty_prompt_estimates_zero(self):
        self.assertEqual(adapter.estimate_required_context(""), 0)


class TestResolveGsdDispatch(unittest.TestCase):
    def test_fable_tier_is_not_gsd_honored_so_falls_through_to_next_candidate(self):
        # Task 7 smoke-test finding: GSD's own model resolution only ever consults
        # opus/sonnet/haiku for model_profile_overrides.<runtime>.<tier> -- "fable" (this plan's
        # own Global Constraints listed it as a 4th Agent-tool alias) is never read back, so a
        # candidate whose tier is "fable" must never resolve as native_tier; it must be dropped
        # and the next ladder entry tried instead.
        candidates = [
            {"cli": None, "model": "fable", "key": "fable-native", "vendor": "",
             "task_affinity": None, "context_limit": None, "tier": "fable"},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None, "tier": "sonnet"},
        ]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["fable-native", "codex/gpt-5.6-sol"], {}, "/repo/.planning/config.json",
            "/repo",
            write_tier_fn=lambda *a, **k: {"model_profile_overrides": {a[2]: {a[3]: a[4]}}},
            write_runtime_fn=lambda *a, **k: {})
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["key"], "codex/gpt-5.6-sol")
        self.assertEqual(result["tier"], "sonnet")

    def test_native_candidate_with_curated_tier_writes_override_and_runtime(self):
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        written, runtime_written = {}, {}
        def fake_write_tier(path, gsd_config, runtime, tier, model, **kw):
            written["args"] = (path, gsd_config, runtime, tier, model)
            return {**gsd_config, "model_profile_overrides": {runtime: {tier: model}}}
        def fake_write_runtime(path, gsd_config, runtime, **kw):
            runtime_written["args"] = (path, gsd_config, runtime)
            return {**gsd_config, "runtime": runtime}
        result = adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], {}, "/repo/.planning/config.json", "/repo",
            write_tier_fn=fake_write_tier, write_runtime_fn=fake_write_runtime)
        self.assertEqual(result, {"mode": "native_tier", "runtime": "codex", "tier": "sonnet",
                                    "model": "gpt-5.6-sol", "written": True, "cli": "codex",
                                    "key": "codex/gpt-5.6-sol", "provenance": "resolved_candidate"})
        # Write-ordering: runtime write happens FIRST, its own returned dict feeds the tier write.
        self.assertEqual(runtime_written["args"], ("/repo/.planning/config.json", {}, "codex"))
        self.assertEqual(written["args"],
                          ("/repo/.planning/config.json", {"runtime": "codex"}, "codex",
                           "sonnet", "gpt-5.6-sol"))

    def test_does_not_rewrite_active_runtime_when_it_already_matches_current_runtime(self):
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        runtime_written = {"called": False}
        def fake_write_runtime(*a, **kw):
            runtime_written["called"] = True
            return {}
        adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], {}, "/repo/.planning/config.json", "/repo",
            current_runtime="codex", write_tier_fn=lambda *a, **k: {},
            write_runtime_fn=fake_write_runtime)
        self.assertFalse(runtime_written["called"])

    def test_native_candidate_cli_none_resolves_with_claude_as_runtime(self):
        # Task 7 smoke-test finding: model_profile_overrides.claude.<tier> is dead for GSD's real
        # resolution -- native claude dispatch writes the model_profile scalar instead (mapped via
        # TIER_TO_MODEL_PROFILE), never model_profile_overrides.
        candidates = [{"cli": None, "model": "opus", "key": "opus-native", "vendor": "",
                       "task_affinity": None, "context_limit": None, "tier": "opus"}]
        profile_writes = []
        result = adapter.resolve_gsd_dispatch(
            candidates, ["opus-native"], {}, "/repo/.planning/config.json", "/repo",
            write_tier_fn=lambda *a, **k: {}, write_runtime_fn=lambda *a, **k: {},
            write_model_profile_fn=lambda path, cfg, profile, **k: profile_writes.append(profile)
            or {**cfg, "model_profile": profile})
        self.assertEqual(result["runtime"], "claude")
        self.assertEqual(result["tier"], "opus")
        self.assertIsNone(result["cli"])
        self.assertEqual(result["model"], "quality")
        self.assertTrue(result["written"])
        self.assertEqual(profile_writes, ["quality"])

    def test_native_candidate_honors_an_existing_non_adapter_owned_model_profile(self):
        gsd_config = {"model_profile": "budget"}  # a genuine, hand-set user value
        candidates = [{"cli": None, "model": "opus", "key": "opus-native", "vendor": "",
                       "task_affinity": None, "context_limit": None, "tier": "opus"}]
        profile_writes = []
        result = adapter.resolve_gsd_dispatch(
            candidates, ["opus-native"], gsd_config, "/repo/.planning/config.json", "/repo",
            write_tier_fn=lambda *a, **k: {}, write_runtime_fn=lambda *a, **k: {},
            write_model_profile_fn=lambda path, cfg, profile, **k: profile_writes.append(profile))
        self.assertEqual(result["model"], "budget")
        self.assertFalse(result["written"])
        self.assertEqual(result["provenance"], "existing_gsd_config")
        self.assertEqual(profile_writes, [])

    def test_existing_non_adapter_owned_slot_is_honored_and_not_overwritten(self):
        gsd_config = {"model_profile_overrides": {"codex": {"sonnet": "hand-picked-model"}}}
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        write_calls = []
        result = adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], gsd_config, "/repo/.planning/config.json", "/repo",
            current_runtime="codex",
            write_tier_fn=lambda *a, **k: write_calls.append(a),
            write_runtime_fn=lambda *a, **k: write_calls.append(a))
        self.assertEqual(result["model"], "hand-picked-model")
        self.assertFalse(result["written"])
        self.assertEqual(result["provenance"], "existing_gsd_config")
        self.assertEqual(write_calls, [])

    def test_adapter_owned_existing_slot_is_re_resolved_not_treated_as_fixed(self):
        gsd_config = {
            "model_profile_overrides": {"codex": {"sonnet": "stale-model"}},
            "_ai_kit_spec_execute_gsd": {"overrides": {"codex": {"sonnet": "stale-model"}}},
        }
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], gsd_config, "/repo/.planning/config.json", "/repo",
            current_runtime="codex", write_tier_fn=lambda *a, **k: {**gsd_config},
            write_runtime_fn=lambda *a, **k: {**gsd_config})
        self.assertEqual(result["model"], "gpt-5.6-sol")
        self.assertTrue(result["written"])

    @mock.patch("ai_kit_spec_gsd.adapter.build_cross_ai_command")
    def test_falls_through_to_cross_ai_when_no_tier_and_no_native_runtime(self, mock_build):
        mock_build.return_value = "future-cli exec -C /repo -m grok-4-fast"
        candidates = [{"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast",
                       "vendor": "xai", "task_affinity": None, "context_limit": None,
                       "tier": None}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast"], {}, "/repo/.planning/config.json", "/repo")
        self.assertEqual(result["mode"], "cross_ai_hook")
        self.assertEqual(result["cli"], "grok")
        self.assertEqual(result["cross_ai_command"], "future-cli exec -C /repo -m grok-4-fast")
        self.assertEqual(result["provenance"], "resolved_candidate")

    @mock.patch("ai_kit_spec_gsd.adapter.build_cross_ai_command")
    def test_escalates_past_an_unusable_candidate_to_a_later_native_one(self, mock_build):
        mock_build.return_value = None
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": None, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None, "tier": "sonnet"},
        ]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], {},
            "/repo/.planning/config.json", "/repo", write_tier_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {})
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_skips_a_candidate_with_no_quota_and_uses_the_next_one(self):
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": None, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None, "tier": "sonnet"},
        ]
        quota = {"grok/grok-4-fast": {"available": False}}
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], {},
            "/repo/.planning/config.json", "/repo", quota=quota, write_tier_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {})
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_falls_back_with_no_usable_dispatch_when_nothing_can_carry_it(self):
        # real (unmocked) build_cross_ai_command: gemini has no live-verified execute
        # builder -- returns None for real, and no curated tier exists.
        candidates = [{"cli": "gemini", "model": "gemini-3.1-pro",
                       "key": "gemini/gemini-3.1-pro", "vendor": "google",
                       "task_affinity": None, "context_limit": None, "tier": None}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["gemini/gemini-3.1-pro"], {}, "/repo/.planning/config.json",
            "/repo")
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertIn("gemini/gemini-3.1-pro", result["message"])
        self.assertEqual(result["reason"], "no_usable_dispatch")
        self.assertEqual(result["provenance"], "fallback")

    def test_every_candidate_lacks_quota_falls_back_quota_exhausted(self):
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": None, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None, "tier": "sonnet"},
        ]
        quota = {"grok/grok-4-fast": {"available": False},
                 "codex/gpt-5.6-sol": {"available": False}}
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], {},
            "/repo/.planning/config.json", "/repo", quota=quota)
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "quota_exhausted")

    def test_no_configured_candidate_at_all_has_its_own_distinct_reason_code(self):
        result = adapter.resolve_gsd_dispatch([], [], {}, "/repo/.planning/config.json", "/repo")
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "no_configured_candidate")

    def test_all_candidates_present_but_context_rejected_gets_a_distinct_reason_code(self):
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": 1000, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": 2000, "tier": "sonnet"},
        ]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], {},
            "/repo/.planning/config.json", "/repo", required_context=1_000_000)
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "all_candidates_context_rejected")

    def test_real_nonempty_phase_prompt_with_uncurated_candidates_still_resolves(self):
        real_phase_prompt = "Implement the login form validation for the signup flow." * 20
        required_context = adapter.estimate_required_context(real_phase_prompt)
        self.assertGreater(required_context, 0)
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], {}, "/repo/.planning/config.json", "/repo",
            quota={}, required_context=required_context, write_tier_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {})
        self.assertNotEqual(result["mode"], "fallback_notice")


class TestCliResolveDispatch(unittest.TestCase):
    def test_resolve_dispatch_subcommand_prints_json_dispatch_decision(self):
        import io
        import json
        def fake_assemble(cwd, env):
            return ([{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}],
                    ["codex/gpt-5.6-sol"])
        stdout = io.StringIO()
        exit_code = cli.main(
            ["resolve-dispatch", "--cwd", "/repo",
             "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
             "--quota-path", "/cache/quota.json"],
            assemble_candidates_fn=fake_assemble,
            read_gsd_config_fn=lambda p, warn_fn=None: ({}, "missing"),
            refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
            cache_write_json_fn=lambda p, d: None, write_tier_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {}, stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_resolve_dispatch_aborts_and_reports_malformed_config_without_mutating(self):
        import io
        import json
        write_calls = []
        stdout = io.StringIO()
        exit_code = cli.main(
            ["resolve-dispatch", "--cwd", "/repo",
             "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
             "--quota-path", "/cache/quota.json"],
            assemble_candidates_fn=lambda cwd, env: ([], []),
            read_gsd_config_fn=lambda p, warn_fn=None: ({}, "malformed"),
            refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
            cache_write_json_fn=lambda p, d: None,
            write_tier_fn=lambda *a, **k: write_calls.append(a),
            write_runtime_fn=lambda *a, **k: write_calls.append(a), stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "malformed_config")
        self.assertEqual(write_calls, [])

    def test_resolve_dispatch_generates_one_run_id_and_threads_it_through_every_write(self):
        import io
        import json
        def fake_assemble(cwd, env):
            return ([{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}],
                    ["codex/gpt-5.6-sol"])
        run_ids_seen = []
        def fake_write_tier(path, gsd_config, runtime, tier, model, run_id=None, **kw):
            run_ids_seen.append(run_id)
            return {**gsd_config, "model_profile_overrides": {runtime: {tier: model}}}
        def fake_write_runtime(path, gsd_config, runtime, run_id=None, **kw):
            run_ids_seen.append(run_id)
            return {**gsd_config, "runtime": runtime}
        stdout = io.StringIO()
        cli.main(
            ["resolve-dispatch", "--cwd", "/repo",
             "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
             "--quota-path", "/cache/quota.json", "--run-id", "explicit-run-42"],
            assemble_candidates_fn=fake_assemble,
            read_gsd_config_fn=lambda p, warn_fn=None: ({}, "missing"),
            refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
            cache_write_json_fn=lambda p, d: None, write_tier_fn=fake_write_tier,
            write_runtime_fn=fake_write_runtime, stdout=stdout)
        self.assertTrue(run_ids_seen)
        self.assertEqual(set(run_ids_seen), {"explicit-run-42"})
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["run_id"], "explicit-run-42")

    def test_resolve_dispatch_falls_back_to_zero_context_when_phase_prompt_file_is_unreadable(self):
        import contextlib
        import io
        import json
        def fake_assemble(cwd, env):
            return ([{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}],
                    ["codex/gpt-5.6-sol"])
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = cli.main(
                ["resolve-dispatch", "--cwd", "/repo",
                 "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
                 "--quota-path", "/cache/quota.json",
                 "--phase-prompt-file", "/nonexistent/phase-prompt.md"],
                assemble_candidates_fn=fake_assemble,
                read_gsd_config_fn=lambda p, warn_fn=None: ({}, "missing"),
                refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
                cache_write_json_fn=lambda p, d: None, write_tier_fn=lambda *a, **k: {},
                write_runtime_fn=lambda *a, **k: {}, stdout=stdout)
        self.assertEqual(exit_code, 0)
        json.loads(stdout.getvalue())
        self.assertIn("phase-prompt.md", stderr.getvalue())


class TestCliConfigPath(unittest.TestCase):
    def test_config_path_subcommand_prints_the_resolved_path(self):
        import io
        stdout = io.StringIO()
        exit_code = cli.main(["config-path", "--cwd", "/repo"], stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().strip(), "/repo/.planning/config.json")


class TestCliWriteWorkflowKey(unittest.TestCase):
    def test_write_workflow_key_subcommand_writes_a_real_json_value(self):
        import io
        import json
        writes = {}
        def fake_write(path, gsd_config, key, value, **kw):
            writes["args"] = (path, gsd_config, key, value)
            return {**gsd_config, "workflow": {key: value}}
        stdout = io.StringIO()
        exit_code = cli.main(
            ["write-workflow-key", "--config-path", "/repo/.planning/config.json",
             "--config-json", "{}", "--key", "cross_ai_execution", "--run-id", "run-1",
             "--value-json", "true"],
            write_workflow_key_fn=fake_write, stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertIs(result["workflow"]["cross_ai_execution"], True)
        self.assertIs(writes["args"][3], True)  # a real bool, never the string "true"


class TestCliClearWorkflowKey(unittest.TestCase):
    def test_clear_workflow_key_subcommand_clears_an_adapter_owned_key(self):
        import io
        import json
        config_json = json.dumps({
            "workflow": {"cross_ai_command": "codex exec ..."},
            "_ai_kit_spec_execute_gsd": {"workflow": {"cross_ai_command": "codex exec ..."}},
        })
        def fake_clear(path, gsd_config, key, **kw):
            return {**gsd_config, "workflow": {}}
        stdout = io.StringIO()
        exit_code = cli.main(
            ["clear-workflow-key", "--config-path", "/repo/.planning/config.json",
             "--config-json", config_json, "--key", "cross_ai_command", "--run-id", "run-1"],
            clear_workflow_key_if_adapter_owned_fn=fake_clear, stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertNotIn("cross_ai_command", result["workflow"])


class _FakeCompletedProcess:
    def __init__(self, returncode):
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


class TestCliPrepareTooling(unittest.TestCase):
    def test_prepare_tooling_subcommand_builds_the_index_for_real_and_prints_guidance_text(self):
        import io
        run_calls = []
        def fake_run(cmd, **kw):
            run_calls.append((cmd, kw))
            return _FakeCompletedProcess(returncode=0)
        stdout = io.StringIO()
        exit_code = cli.main(
            ["prepare-tooling", "--cli", "codex", "--target-dir", "/repo"],
            detect_tool_availability_fn=lambda **k: {"codegraph": True, "rg": True},
            resolve_agents_tooling_path_fn=lambda **k: "/home/u/.agents/AGENTS-TOOLING.md",
            ensure_codegraph_registered_fn=lambda cli, **k: True,
            build_codegraph_index_command_fn=lambda target_dir: "cd /repo && codegraph sync",
            run_fn=fake_run, stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(run_calls), 1)
        self.assertIn("AGENTS-TOOLING.md", stdout.getvalue())
        self.assertIn("codegraph_explore", stdout.getvalue())

    def test_prepare_tooling_degrades_to_generic_guidance_when_index_build_times_out(self):
        import io
        import subprocess
        def timing_out_run(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=kw.get("timeout", 15))
        stdout = io.StringIO()
        exit_code = cli.main(
            ["prepare-tooling", "--cli", "codex", "--target-dir", "/repo"],
            detect_tool_availability_fn=lambda **k: {"codegraph": True, "rg": True},
            resolve_agents_tooling_path_fn=lambda **k: "/home/u/.agents/AGENTS-TOOLING.md",
            ensure_codegraph_registered_fn=lambda cli, **k: True,
            build_codegraph_index_command_fn=lambda target_dir: "cd /repo && codegraph sync",
            run_fn=timing_out_run, stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertNotIn("codegraph_explore", stdout.getvalue())
        self.assertIn("AGENTS-TOOLING.md", stdout.getvalue())


class TestCliWriteResumableState(unittest.TestCase):
    def test_write_resumable_state_subcommand_writes_the_given_state_json(self):
        import io
        writes = {}
        def fake_write(path, state):
            writes[path] = state
        stdout = io.StringIO()
        exit_code = cli.main(
            ["write-resumable-state", "--path", "/cache/gsd-resume-abc123-phase1.json",
             "--state-json", '{"framework": "gsd", "phase_id": "phase1"}'],
            write_resumable_state_fn=fake_write, stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(writes["/cache/gsd-resume-abc123-phase1.json"]["phase_id"], "phase1")


class TestDetectFramework(unittest.TestCase):
    def test_detects_gsd_via_planning_project_md(self):
        result = detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: p == "/repo/.planning/PROJECT.md",
            isdir_fn=lambda p: False)
        self.assertEqual(result, "gsd")

    def test_unknown_when_no_markers_present(self):
        result = detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=lambda p: False)
        self.assertEqual(result, "unknown")


class TestBuildGsdCrossAiGuidance(unittest.TestCase):
    def test_includes_the_resolved_label(self):
        result = cross_ai_guidance.build_gsd_cross_ai_guidance("codex, model gpt-5.6-sol")
        self.assertIn("codex, model gpt-5.6-sol", result)

    def test_includes_gsd_real_summary_frontmatter_fields(self):
        # Task 7 second-round smoke-test finding: this exact set of fields, live-verified against
        # gsd-core/templates/summary.md and confirmed to make codex's own stdout GSD-summary-
        # shaped in a real dispatch.
        result = cross_ai_guidance.build_gsd_cross_ai_guidance("codex, model gpt-5.6-sol")
        for field in ("phase:", "plan:", "requirements-completed:", "duration:", "completed:"):
            self.assertIn(field, result)
        self.assertIn("## Accomplishments", result)
        self.assertIn("## Files Created/Modified", result)

    def test_includes_incremental_progress_and_failure_reporting_guidance(self):
        result = cross_ai_guidance.build_gsd_cross_ai_guidance("codex, model gpt-5.6-sol")
        self.assertIn("incrementally", result)
        self.assertIn("never report success", result)


class TestCliPrepareCrossAiGuidance(unittest.TestCase):
    def test_prepare_cross_ai_guidance_subcommand_prints_guidance(self):
        import io
        stdout = io.StringIO()
        exit_code = cli.main(
            ["prepare-cross-ai-guidance", "--resolved-label", "codex, model gpt-5.6-sol"],
            build_gsd_cross_ai_guidance_fn=lambda label: f"GUIDANCE FOR {label}", stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "GUIDANCE FOR codex, model gpt-5.6-sol")


class TestCliPrintSummaryFormatBlock(unittest.TestCase):
    def test_prints_the_raw_format_block_with_no_resolved_label_wrapper(self):
        import io
        stdout = io.StringIO()
        exit_code = cli.main(["print-summary-format-block"], stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), cross_ai_guidance.GSD_SUMMARY_FORMAT_BLOCK)


class TestGsdPurposeFilterInertness(unittest.TestCase):
    def test_purpose_filter_is_inert_for_gsd_while_purpose_stays_unset(self):
        # GSD's candidates never carry a "purpose" key (adapter.py's assemble_candidates
        # does not set one) -- purpose_matches treats an absent field as "no preference",
        # so resolve_execute_candidates' new purpose-narrowing step (Task 1) must never
        # exclude a GSD candidate on that basis alone. This pins down the load-bearing
        # coincidence noted in this plan's Global Constraints: if GSD's adapter ever starts
        # writing "purpose" onto its candidate dicts, this test's assumption (both
        # candidates pass through unfiltered) breaks and must be revisited deliberately,
        # not silently.
        candidates = [
            {"key": "review-only-tagged", "purpose": "review", "context_limit": 1_000_000},
            {"key": "gsd-style-untagged", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, task_type=None, required_context=1000,
            affinity_table={}, top_n_keys=[])
        # Only the untagged candidate survives -- resolve_execute_candidates wants
        # purpose="execute", and an entry explicitly tagged purpose="review" correctly
        # does NOT match that (this is filter_by_purpose working as intended, not a bug).
        # The untagged candidate matches "no preference" and survives -- this is the
        # exact shape GSD's real candidates take (assemble_candidates never sets
        # "purpose"), so GSD's execute-candidate resolution stays unaffected today. The
        # non-empty result also means filter_by_purpose's never-empty fallback never
        # engages here -- if a future change starts writing "purpose" onto GSD's
        # candidate dicts, this test's assumption should be revisited deliberately.
        self.assertEqual({c["key"] for c in result}, {"gsd-style-untagged"})

