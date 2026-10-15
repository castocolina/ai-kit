import json
import os
import shutil
import subprocess
import sys
import tempfile
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
from ai_kit_spec import detection, execute_selection, gsd_tools
from ai_kit_spec_gsd import adapter, cli, cross_ai_guidance, gsd_config, gsd_cross_ai


def _stub_run_fn(*args, **kwargs):
    return subprocess.CompletedProcess(args=args[0] if args else [], returncode=0)


def _stub_tools():
    return gsd_tools.GsdTools("node", "/nonexistent/test-gsd-tools.cjs")


def _resolve_gsd_dispatch(candidates, top_n_keys, gsd_config, ctx, target_dir="/repo", **kwargs):
    seam_keys = ("apply_changes_fn", "is_adapter_owned_fn", "resolve_ladder_pick_fn")
    seams_kw = {k: kwargs.pop(k) for k in list(kwargs) if k in seam_keys}
    dispatch_kw = {k: kwargs.pop(k) for k in list(kwargs)
                   if k in ("current_runtime", "required_context", "quota")}
    if kwargs:
        raise TypeError(f"unexpected kwargs: {kwargs}")
    dispatch = adapter.DispatchContext(target_dir=target_dir, **dispatch_kw)
    seams = adapter.DispatchSeams(**seams_kw) if seams_kw else None
    inputs = adapter.DispatchInputs(candidates, top_n_keys, gsd_config, ctx)
    return adapter.resolve_gsd_dispatch(inputs, dispatch, seams)


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


def _ctx(config_path="/repo/.planning/config.json", run_fn=None, project_dir="/repo",
         tools=None):
    """A GsdWriteContext for tests: inert stubs when tools/run_fn are omitted."""
    if tools is None:
        tools = _stub_tools()
    if run_fn is None:
        run_fn = _stub_run_fn
    return gsd_config.GsdWriteContext(tools=tools, project_dir=project_dir,
                                       config_path=config_path, run_id="r1", run_fn=run_fn)


def _ok_apply(ctx, changes):
    return gsd_config.ApplyResult([key for key, _ in changes], None, None, [], [])


class TestIsAdapterOwned(unittest.TestCase):
    def test_true_when_current_value_equals_the_sidecar_record(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            config_path = os.path.join(t, "config.json")
            gsd_config.write_ownership(config_path,
                                       {"model_profile_overrides.codex.sonnet": "gpt-5.6-sol"})
            cfg = {"model_profile_overrides": {"codex": {"sonnet": "gpt-5.6-sol"}}}
            self.assertTrue(gsd_config.is_adapter_owned(cfg, config_path,
                                                         "model_profile_overrides.codex.sonnet"))

    def test_false_when_sidecar_missing_value_reads_user_owned(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            config_path = os.path.join(t, "config.json")
            cfg = {"model_profile_overrides": {"codex": {"sonnet": "hand-set"}}}
            self.assertFalse(gsd_config.is_adapter_owned(cfg, config_path,
                                                          "model_profile_overrides.codex.sonnet"))

    def test_false_when_value_no_longer_matches_the_sidecar(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            config_path = os.path.join(t, "config.json")
            gsd_config.write_ownership(config_path, {"workflow.x": "old"})
            self.assertFalse(gsd_config.is_adapter_owned({"workflow": {"x": "hand-edited"}},
                                                          config_path, "workflow.x"))

    def test_false_when_current_value_is_none_or_absent(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            config_path = os.path.join(t, "config.json")
            gsd_config.write_ownership(config_path, {"workflow.x": None})
            self.assertFalse(gsd_config.is_adapter_owned({}, config_path, "workflow.x"))


class TestApplyChangesBackup(unittest.TestCase):
    def test_backs_up_an_existing_config_once_per_run_before_the_first_write(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            config_path = os.path.join(t, "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("{}")
            fake = FakeGsdTools(t)
            ctx = _ctx(config_path=config_path, run_fn=fake.run_fn, project_dir=t,
                       tools=gsd_tools.GsdTools("node", fake.gsd_tools_path))
            gsd_config.apply_changes(ctx, [("workflow.a", True)])
            backup = config_path + ".ai-kit-spec-execute-gsd.r1.bak"
            self.assertTrue(os.path.exists(backup))
            # A second run with a different run id gets its own backup; the same run id does
            # not duplicate (already covered by the once-per-run isfile check).

    def test_no_backup_when_the_config_does_not_exist_yet(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            config_path = os.path.join(t, "config.json")
            fake = FakeGsdTools(t)
            ctx = _ctx(config_path=config_path, run_fn=fake.run_fn, project_dir=t,
                       tools=gsd_tools.GsdTools("node", fake.gsd_tools_path))
            gsd_config.apply_changes(ctx, [("workflow.a", True)])
            self.assertEqual([p for p in os.listdir(t) if p.endswith(".bak")], [])


class TestUndoLog(unittest.TestCase):
    """D-17/RUN-11: each undo entry is the key's own config-set previousValue; a later failure
    reverts earlier keys in reverse order; config-get is never called."""

    def _ctx(self, fake, t):
        return _ctx(config_path=os.path.join(t, ".planning", "config.json"),
                    run_fn=fake.run_fn, project_dir=t,
                    tools=gsd_tools.GsdTools("node", fake.gsd_tools_path))

    def test_failure_on_later_key_reverts_earlier_keys_in_reverse_order(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t, fail_keys={"c"})
            fake.config["a"] = 1
            result = gsd_config.apply_changes(self._ctx(fake, t),
                                               [("a", 1), ("b", 2), ("c", 3)])
            self.assertEqual(result.applied, ["a", "b"])
            self.assertEqual(result.failed, "c")
            self.assertEqual(result.reverted, ["b", "a"])
            keys_and_values = [(c[3], c[4]) for c in fake.config_set_calls()]
            self.assertEqual(keys_and_values,
                             [("a", "1"), ("b", "2"), ("c", "3"),
                              ("b", "null"), ("a", "1")])  # reverse order; b was absent

    def test_a_failed_revert_is_reported_as_revert_failed_not_reverted(self):
        # A-WR-03/M2: a revert that itself fails (or cannot spawn node) must never be
        # reported as reverted -- that key still holds the new value.
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t, fail_keys={"c"})
            seen = []

            def run(argv, **kwargs):
                key = argv[3] if len(argv) > 3 and argv[2] == "config-set" else None
                seen.append(key)
                if key == "a" and seen.count("a") == 2:
                    return subprocess.CompletedProcess(argv, 1, "", "lock busy")
                if key == "b" and seen.count("b") == 2:
                    raise FileNotFoundError("node")
                return fake.run_fn(argv, **kwargs)

            ctx = _ctx(config_path=os.path.join(t, ".planning", "config.json"), run_fn=run,
                       project_dir=t, tools=gsd_tools.GsdTools("node", fake.gsd_tools_path))
            result = gsd_config.apply_changes(ctx, [("a", 1), ("b", 2), ("c", 3)])
            self.assertEqual(result.failed, "c")
            self.assertEqual(result.reverted, [])
            self.assertEqual(result.revert_failed, ["b", "a"])
            assert result.error is not None
            self.assertIn("revert also failed for b, a", result.error)

    def test_failure_on_the_first_key_makes_no_revert_call(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t, fail_keys={"a"})
            result = gsd_config.apply_changes(self._ctx(fake, t), [("a", 1), ("b", 2)])
            self.assertEqual(result.applied, [])
            self.assertEqual(result.failed, "a")
            self.assertEqual(result.reverted, [])
            self.assertEqual(len(fake.config_set_calls()), 1)

    def test_exit_zero_without_parseable_json_means_unknown_prior_value_key_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t, raw_keys={"b"})
            fake.config["a"] = 1
            result = gsd_config.apply_changes(self._ctx(fake, t), [("a", 1), ("b", 2)])
            self.assertEqual(result.applied, ["a"])
            self.assertEqual(result.failed, "b")
            assert result.error is not None
            self.assertIn("prior value is unknown", result.error)
            self.assertIn("keeps the new value", result.error)
            self.assertEqual(result.reverted, ["a"])
            self.assertNotIn("b", fake.config_set_calls()[-1])

    def test_no_config_get_call_in_any_undo_scenario(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t, fail_keys={"c"})
            gsd_config.apply_changes(self._ctx(fake, t), [("a", 1), ("b", 2), ("c", 3)])
            self.assertNotIn("config-get", fake.subcommands())

    def test_success_records_ownership_and_a_null_unset_drops_the_sidecar_key(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            config_path = os.path.join(t, ".planning", "config.json")
            os.makedirs(os.path.dirname(config_path))
            gsd_config.write_ownership(config_path, {"workflow.old": "x"})
            fake = FakeGsdTools(t)
            fake.config["workflow.old"] = "x"
            result = gsd_config.apply_changes(
                self._ctx(fake, t), [("workflow.old", None), ("workflow.new", True)])
            self.assertIsNone(result.failed)
            self.assertEqual(gsd_config.read_ownership(config_path), {"workflow.new": True})
            self.assertEqual(fake.config_set_calls()[0][3:5], ["workflow.old", "null"])


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
        assert result is not None
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
                                        "tier": None, "purpose": None, "effort": None,
                                        "service_tier": None}])
        self.assertEqual(top_n_keys, ["codex/gpt-5.6-sol"])

    def test_carries_purpose_effort_and_service_tier(self):
        # A-WR-07: without purpose the D-15 hard error and filter_by_purpose are unreachable on
        # the GSD path; without effort the codex reasoning flag is dropped from the hook.
        def fake_cfg_resolve(cwd, env):
            return {"policy": {"ladder": []},
                    "reviewers": [{"key": "c", "model": "m", "cli": "codex",
                                   "purpose": "review", "effort": "high",
                                   "service_tier": "flex"}]}
        candidates, _ = adapter.assemble_candidates("/repo", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertEqual((candidates[0]["purpose"], candidates[0]["effort"],
                          candidates[0]["service_tier"]), ("review", "high", "flex"))

    def test_purpose_execute_on_an_unsupported_cli_is_a_hard_error_end_to_end(self):
        def fake_cfg_resolve(cwd, env):
            return {"policy": {"ladder": ["g", "r"]},
                    "reviewers": [{"key": "g", "model": "m", "cli": "grok", "purpose": "execute"},
                                  {"key": "r", "model": "m", "cli": "codex",
                                   "purpose": "review"}]}
        candidates, top = adapter.assemble_candidates("/repo", {}, cfg_resolve_fn=fake_cfg_resolve)
        with self.assertRaisesRegex(ValueError, "codex, cursor-agent, opencode"):
            _resolve_gsd_dispatch(candidates, top, {}, _ctx(), "/repo")

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
        result = _resolve_gsd_dispatch(
            candidates, ["fable-native", "codex/gpt-5.6-sol"], {}, _ctx(), "/repo",
            apply_changes_fn=_ok_apply)
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["key"], "codex/gpt-5.6-sol")
        self.assertEqual(result["tier"], "sonnet")

    def test_native_candidate_with_curated_tier_writes_override_and_runtime_in_one_call(self):
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        seen = []
        def fake_apply(ctx, changes):
            seen.append((ctx, changes))
            return gsd_config.ApplyResult([key for key, _ in changes], None, None, [], [])
        result = _resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], {}, _ctx(), "/repo", apply_changes_fn=fake_apply)
        self.assertEqual(result, {"mode": "native_tier", "runtime": "codex", "tier": "sonnet",
                                    "model": "gpt-5.6-sol", "written": True, "cli": "codex",
                                    "key": "codex/gpt-5.6-sol", "provenance": "resolved_candidate"})
        # D-17: ONE apply_changes call; runtime first, then the tier override, in that order.
        self.assertEqual(len(seen), 1)
        ctx, changes = seen[0]
        self.assertEqual(ctx.config_path, "/repo/.planning/config.json")
        self.assertEqual(changes, [("runtime", "codex"),
                                   ("model_profile_overrides.codex.sonnet", "gpt-5.6-sol")])

    def test_does_not_rewrite_active_runtime_when_it_already_matches_current_runtime(self):
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        seen = []
        _resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], {}, _ctx(), "/repo", current_runtime="codex",
            apply_changes_fn=lambda ctx, changes: seen.append(changes)
            or gsd_config.ApplyResult([key for key, _ in changes], None, None, [], []))
        # Only the tier override is written -- runtime already matches.
        self.assertEqual(seen, [[("model_profile_overrides.codex.sonnet", "gpt-5.6-sol")]])

    def test_native_candidate_cli_none_resolves_with_claude_as_runtime(self):
        # Task 7 smoke-test finding: model_profile_overrides.claude.<tier> is dead for GSD's real
        # resolution -- native claude dispatch writes the model_profile scalar instead (mapped via
        # TIER_TO_MODEL_PROFILE), never model_profile_overrides.
        candidates = [{"cli": None, "model": "opus", "key": "opus-native", "vendor": "",
                       "task_affinity": None, "context_limit": None, "tier": "opus"}]
        seen = []
        result = _resolve_gsd_dispatch(
            candidates, ["opus-native"], {}, _ctx(), "/repo",
            apply_changes_fn=lambda ctx, changes: seen.append(changes)
            or gsd_config.ApplyResult([key for key, _ in changes], None, None, [], []))
        self.assertEqual(result["runtime"], "claude")
        self.assertEqual(result["tier"], "opus")
        self.assertIsNone(result["cli"])
        self.assertEqual(result["model"], "quality")
        self.assertTrue(result["written"])
        self.assertEqual(seen, [[("model_profile", "quality")]])

    def test_native_candidate_honors_an_existing_non_adapter_owned_model_profile(self):
        cfg = {"model_profile": "budget"}  # a genuine, hand-set user value
        candidates = [{"cli": None, "model": "opus", "key": "opus-native", "vendor": "",
                       "task_affinity": None, "context_limit": None, "tier": "opus"}]
        seen = []
        result = _resolve_gsd_dispatch(
            candidates, ["opus-native"], cfg, _ctx(), "/repo",
            apply_changes_fn=lambda ctx, changes: seen.append(changes)
            or gsd_config.ApplyResult([], None, None, [], []))
        self.assertEqual(result["model"], "budget")
        self.assertFalse(result["written"])
        self.assertEqual(result["provenance"], "existing_gsd_config")
        self.assertEqual(seen, [])

    def test_existing_non_adapter_owned_slot_is_honored_and_not_overwritten(self):
        cfg = {"model_profile_overrides": {"codex": {"sonnet": "hand-picked-model"}}}
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        seen = []
        result = _resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], cfg, _ctx(), "/repo", current_runtime="codex",
            apply_changes_fn=lambda ctx, changes: seen.append(changes)
            or gsd_config.ApplyResult([], None, None, [], []))
        self.assertEqual(result["model"], "hand-picked-model")
        self.assertFalse(result["written"])
        self.assertEqual(result["provenance"], "existing_gsd_config")
        self.assertEqual(seen, [])

    def test_adapter_owned_existing_slot_is_re_resolved_not_treated_as_fixed(self):
        cfg = {"model_profile_overrides": {"codex": {"sonnet": "stale-model"}}}
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        result = _resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], cfg, _ctx(), "/repo", current_runtime="codex",
            is_adapter_owned_fn=lambda _gsd_cfg, path, key: True,
            apply_changes_fn=_ok_apply)
        self.assertEqual(result["model"], "gpt-5.6-sol")
        self.assertTrue(result["written"])

    def test_a_failed_apply_surfaces_as_a_write_failed_result_carrying_the_undo_log(self):
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        failing = gsd_config.ApplyResult(["runtime"], "model_profile_overrides.codex.sonnet",
                                          "config-set failed", ["runtime"], [])
        result = _resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], {}, _ctx(), "/repo", current_runtime="claude",
            apply_changes_fn=lambda ctx, changes: failing)
        self.assertEqual(result["mode"], "write_failed")
        self.assertEqual(result["applied"], ["runtime"])
        self.assertEqual(result["failed"], "model_profile_overrides.codex.sonnet")
        self.assertEqual(result["reverted"], ["runtime"])
        self.assertEqual(result["error"], "config-set failed")

    @mock.patch("ai_kit_spec_gsd.adapter.build_cross_ai_command")
    def test_falls_through_to_cross_ai_when_no_tier_and_no_native_runtime(self, mock_build):
        # D-15 (Phase 16.1): only SUPPORTED_EXECUTE_CLIS entries survive the ladder screen, so
        # this uses opencode (supported, no curated tier) instead of the removed grok path.
        mock_build.return_value = "opencode run -m router-env/my-coding -C /repo"
        candidates = [{"cli": "opencode", "model": "router-env/my-coding",
                       "key": "opencode/router-env-my-coding", "vendor": "opencode",
                       "task_affinity": None, "context_limit": None, "tier": None}]
        result = _resolve_gsd_dispatch(
            candidates, ["opencode/router-env-my-coding"], {}, _ctx(), "/repo")
        self.assertEqual(result["mode"], "cross_ai_hook")
        self.assertEqual(result["cli"], "opencode")
        self.assertEqual(result["cross_ai_command"],
                         "opencode run -m router-env/my-coding -C /repo")
        self.assertEqual(result["provenance"], "resolved_candidate")

    @mock.patch("ai_kit_spec_gsd.adapter.build_cross_ai_command")
    def test_escalates_past_an_unusable_candidate_to_a_later_native_one(self, mock_build):
        mock_build.return_value = None
        candidates = [
            {"cli": "opencode", "model": "router-env/my-coding",
             "key": "opencode/router-env-my-coding", "vendor": "opencode",
             "task_affinity": None, "context_limit": None, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None, "tier": "sonnet"},
        ]
        result = _resolve_gsd_dispatch(
            candidates, ["opencode/router-env-my-coding", "codex/gpt-5.6-sol"], {}, _ctx(),
            "/repo", apply_changes_fn=_ok_apply)
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_skips_a_candidate_with_no_quota_and_uses_the_next_one(self):
        candidates = [
            {"cli": "opencode", "model": "router-env/my-coding",
             "key": "opencode/router-env-my-coding", "vendor": "opencode",
             "task_affinity": None, "context_limit": None, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None, "tier": "sonnet"},
        ]
        quota = {"opencode/router-env-my-coding": {"available": False}}
        result = _resolve_gsd_dispatch(
            candidates, ["opencode/router-env-my-coding", "codex/gpt-5.6-sol"], {}, _ctx(),
            "/repo", quota=quota, apply_changes_fn=_ok_apply)
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_unsupported_cli_roster_falls_back_with_a_visible_warning(self):
        # D-15 (Phase 16.1): a roster naming a CLI with no execute builder (gemini) is screened
        # out of the ladder with a stderr warning -- never silently -- and the empty remainder
        # produces an honest fallback notice, never a silent fallback dispatch to another CLI.
        import contextlib
        import io
        stderr = io.StringIO()
        candidates = [{"cli": "gemini", "model": "gemini-3.1-pro",
                       "key": "gemini/gemini-3.1-pro", "vendor": "google",
                       "task_affinity": None, "context_limit": None, "tier": None}]
        with contextlib.redirect_stderr(stderr):
            result = _resolve_gsd_dispatch(
                candidates, ["gemini/gemini-3.1-pro"], {}, _ctx(), "/repo")
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["provenance"], "fallback")
        self.assertIn("gemini/gemini-3.1-pro", stderr.getvalue())
        self.assertIn("codex, cursor-agent, opencode", stderr.getvalue())
        # C-WR-02: the reason is the screen, never a context-size rejection.
        self.assertEqual(result["reason"], "no_usable_dispatch")
        self.assertIn("gemini/gemini-3.1-pro", result["message"])
        self.assertNotIn("context", result["message"])

    def test_tiered_gemini_keeps_its_native_tier_route_without_a_screen_warning(self):
        # A-WR-08: the native-tier route writes GSD config and needs no execute builder, so the
        # D-15 screen must not drop it (it returned native_tier before Phase 16.1).
        import contextlib
        import io
        stderr = io.StringIO()
        seen = []
        candidates = [{"cli": "gemini", "model": "gemini-3.1-pro", "key": "g",
                       "vendor": "google", "task_affinity": None, "context_limit": None,
                       "tier": "opus"}]
        with contextlib.redirect_stderr(stderr):
            result = _resolve_gsd_dispatch(
                candidates, ["g"], {}, _ctx(), "/repo",
                apply_changes_fn=lambda ctx, changes: seen.append(changes) or
                gsd_config.ApplyResult([k for k, _ in changes], None, None, [], []))
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(seen, [[("runtime", "gemini"),
                                 ("model_profile_overrides.gemini.opus", "gemini-3.1-pro")]])
        self.assertNotIn("skipping", stderr.getvalue())

    def test_tiered_claude_and_grok_stay_screened_fail_closed(self):
        # D-15 names claude and grok; whether it covers GSD's native-tier route for them is
        # unsettled, so they stay screened (warning, no config write).
        import contextlib
        import io
        for cli_name in ("claude", "grok"):
            with self.subTest(cli=cli_name):
                stderr = io.StringIO()
                candidates = [{"cli": cli_name, "model": "m", "key": "k", "vendor": "v",
                               "task_affinity": None, "context_limit": None, "tier": "opus"}]
                with contextlib.redirect_stderr(stderr):
                    result = _resolve_gsd_dispatch(
                        candidates, ["k"], {}, _ctx(), "/repo",
                        apply_changes_fn=lambda ctx, changes: self.fail("no write expected"))
                self.assertEqual(result["mode"], "fallback_notice")
                self.assertEqual(result["reason"], "no_usable_dispatch")
                self.assertIn("skipping 'k'", stderr.getvalue())

    def test_every_candidate_lacks_quota_falls_back_quota_exhausted(self):
        candidates = [
            {"cli": "opencode", "model": "router-env/my-coding",
             "key": "opencode/router-env-my-coding", "vendor": "opencode",
             "task_affinity": None, "context_limit": None, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None, "tier": "sonnet"},
        ]
        quota = {"opencode/router-env-my-coding": {"available": False},
                 "codex/gpt-5.6-sol": {"available": False}}
        result = _resolve_gsd_dispatch(
            candidates, ["opencode/router-env-my-coding", "codex/gpt-5.6-sol"], {}, _ctx(),
            "/repo", quota=quota)
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "quota_exhausted")

    def test_no_configured_candidate_at_all_has_its_own_distinct_reason_code(self):
        result = _resolve_gsd_dispatch([], [], {}, _ctx(), "/repo")
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "no_configured_candidate")

    def test_all_candidates_present_but_context_rejected_gets_a_distinct_reason_code(self):
        candidates = [
            {"cli": "opencode", "model": "router-env/my-coding",
             "key": "opencode/router-env-my-coding", "vendor": "opencode",
             "task_affinity": None, "context_limit": 1000, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": 2000, "tier": "sonnet"},
        ]
        result = _resolve_gsd_dispatch(
            candidates, ["opencode/router-env-my-coding", "codex/gpt-5.6-sol"], {}, _ctx(),
            "/repo", required_context=1_000_000)
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "all_candidates_context_rejected")

    def test_real_nonempty_phase_prompt_with_uncurated_candidates_still_resolves(self):
        real_phase_prompt = "Implement the login form validation for the signup flow." * 20
        required_context = adapter.estimate_required_context(real_phase_prompt)
        self.assertGreater(required_context, 0)
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        result = _resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], {}, _ctx(), "/repo",
            quota={}, required_context=required_context, apply_changes_fn=_ok_apply)
        self.assertNotEqual(result["mode"], "fallback_notice")

class TestCliResolveDispatch(unittest.TestCase):
    """resolve-dispatch resolves node + gsd-tools itself (project-local first), asks gsd-tools
    for the config path, and exits 1 on a write_failed result."""

    def _main(self, assemble_fn, fake, read_gsd_config_fn=None, run_id=None):
        import contextlib
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as t, contextlib.redirect_stderr(io.StringIO()):
            argv = ["resolve-dispatch", "--cwd", t, "--target-dir", t,
                    "--quota-path", os.path.join(t, "quota.json")]
            if run_id:
                argv += ["--run-id", run_id]
            stdout = io.StringIO()
            if read_gsd_config_fn is not None:
                code = cli.main(
                    argv,
                    assemble_candidates_fn=assemble_fn,
                    refresh_quota_cache_fn=lambda *a, **k: {},
                    cache_read_json_fn=lambda p: {},
                    cache_write_json_fn=lambda p, d: None,
                    run_fn=fake.run_fn,
                    which_fn=_node_which,
                    resolve_gsd_tools_fn=lambda start: fake.gsd_tools_path,
                    read_gsd_config_fn=read_gsd_config_fn,
                    stdout=stdout,
                )
            else:
                code = cli.main(
                    argv,
                    assemble_candidates_fn=assemble_fn,
                    refresh_quota_cache_fn=lambda *a, **k: {},
                    cache_read_json_fn=lambda p: {},
                    cache_write_json_fn=lambda p, d: None,
                    run_fn=fake.run_fn,
                    which_fn=_node_which,
                    resolve_gsd_tools_fn=lambda start: fake.gsd_tools_path,
                    stdout=stdout,
                )
        return code, stdout.getvalue()

    @staticmethod
    def _codex_assemble():
        def fake_assemble(cwd, env):
            return ([{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                      "vendor": "openai", "task_affinity": None, "context_limit": None,
                      "tier": "sonnet"}],
                    ["codex/gpt-5.6-sol"])
        return fake_assemble

    def test_resolve_dispatch_prints_json_dispatch_decision_and_writes_via_config_set(self):
        import json
        fake = FakeGsdTools(tempfile.gettempdir())  # config-path is answered in memory
        code, out = self._main(self._codex_assemble(), fake)
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")
        keys = [c[3] for c in fake.config_set_calls()]
        self.assertEqual(keys, ["runtime", "model_profile_overrides.codex.sonnet"])

    def test_resolve_dispatch_aborts_and_reports_malformed_config_without_mutating(self):
        import json
        fake = FakeGsdTools("/tmp")
        code, out = self._main(lambda cwd, env: ([], []), fake,
                               read_gsd_config_fn=lambda p, warn_fn=None: ({}, "malformed"))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "malformed_config")
        self.assertEqual(fake.config_set_calls(), [])

    def test_resolve_dispatch_threads_one_explicit_run_id_into_the_config_write(self):
        import contextlib
        import io
        import json
        import tempfile
        fake = FakeGsdTools("/tmp")
        stderr, stdout = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as t, contextlib.redirect_stderr(stderr):
            planning = os.path.join(t, ".planning")
            os.makedirs(planning)
            # An existing config makes apply_changes' once-per-run backup carry the run id.
            with open(os.path.join(planning, "config.json"), "w", encoding="utf-8") as f:
                f.write("{}")
            code = cli.main(["resolve-dispatch", "--cwd", t, "--target-dir", t,
                             "--quota-path", os.path.join(t, "quota.json"),
                             "--run-id", "explicit-run-42"],
                            assemble_candidates_fn=self._codex_assemble(),
                            refresh_quota_cache_fn=lambda *a, **k: {},
                            cache_read_json_fn=lambda p: {},
                            cache_write_json_fn=lambda p, d: None,
                            run_fn=fake.run_fn, which_fn=_node_which,
                            resolve_gsd_tools_fn=lambda start: fake.gsd_tools_path,
                            stdout=stdout)
            backups = [p for p in os.listdir(planning) if p.endswith(".bak")]
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["run_id"], "explicit-run-42")
        self.assertEqual(backups,
                         ["config.json.ai-kit-spec-execute-gsd.explicit-run-42.bak"])

    def test_resolve_dispatch_falls_back_to_zero_context_when_phase_prompt_file_is_unreadable(self):
        import contextlib
        import io
        import tempfile
        fake = FakeGsdTools("/tmp")
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as t, contextlib.redirect_stderr(stderr):
            argv = ["resolve-dispatch", "--cwd", t, "--target-dir", t,
                    "--quota-path", os.path.join(t, "quota.json"),
                    "--phase-prompt-file", "/nonexistent/phase-prompt.md"]
            code = cli.main(argv, assemble_candidates_fn=self._codex_assemble(),
                            refresh_quota_cache_fn=lambda *a, **k: {},
                            cache_read_json_fn=lambda p: {},
                            cache_write_json_fn=lambda p, d: None,
                            run_fn=fake.run_fn, which_fn=_node_which,
                            resolve_gsd_tools_fn=lambda start: fake.gsd_tools_path,
                            stdout=io.StringIO())
        self.assertEqual(code, 0)
        self.assertIn("phase-prompt.md", stderr.getvalue())

    def test_resolve_dispatch_purpose_execute_claude_entry_exits_2_before_any_write(self):
        # D-15 (Phase 16.1): an explicit purpose = "execute" entry naming claude is a hard
        # config error -- exit 2 naming the supported CLIs, zero config writes, never a
        # silent fallback to another CLI.
        import contextlib
        import io
        import tempfile
        def fake_assemble(cwd, env):
            return ([{"cli": "claude", "model": "opus", "key": "claude/opus",
                      "vendor": "anthropic", "purpose": "execute", "task_affinity": None,
                      "context_limit": None, "tier": None}],
                    ["claude/opus"])
        fake = FakeGsdTools("/tmp")
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as t, contextlib.redirect_stderr(stderr):
            code = cli.main(["resolve-dispatch", "--cwd", t, "--target-dir", t,
                             "--quota-path", os.path.join(t, "quota.json")],
                            assemble_candidates_fn=fake_assemble,
                            refresh_quota_cache_fn=lambda *a, **k: {},
                            cache_read_json_fn=lambda p: {},
                            cache_write_json_fn=lambda p, d: None,
                            run_fn=fake.run_fn, which_fn=_node_which,
                            resolve_gsd_tools_fn=lambda start: fake.gsd_tools_path,
                            stdout=io.StringIO())
        self.assertEqual(code, 2)
        self.assertEqual(fake.config_set_calls(), [])
        self.assertIn("codex, cursor-agent, opencode", stderr.getvalue())
        self.assertIn("ai-kit-spec-execute-gsd:", stderr.getvalue())

    def test_resolve_dispatch_purpose_none_grok_entry_is_skipped_with_a_warning(self):
        # D-15: a purpose-unset grok ladder entry is dropped with one visible stderr warning
        # naming the key; the remaining codex entry still resolves normally.
        import contextlib
        import io
        import json
        import tempfile
        def fake_assemble(cwd, env):
            return ([{"cli": "grok", "model": "grok-4.6", "key": "grok/grok-4.6",
                      "vendor": "xai", "task_affinity": None, "context_limit": None,
                      "tier": None},
                     {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                      "vendor": "openai", "task_affinity": None, "context_limit": None,
                      "tier": "sonnet"}],
                    ["grok/grok-4.6", "codex/gpt-5.6-sol"])
        fake = FakeGsdTools("/tmp")
        stderr = io.StringIO()
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as t, contextlib.redirect_stderr(stderr):
            code = cli.main(["resolve-dispatch", "--cwd", t, "--target-dir", t,
                             "--quota-path", os.path.join(t, "quota.json")],
                            assemble_candidates_fn=fake_assemble,
                            refresh_quota_cache_fn=lambda *a, **k: {},
                            cache_read_json_fn=lambda p: {},
                            cache_write_json_fn=lambda p, d: None,
                            run_fn=fake.run_fn, which_fn=_node_which,
                            resolve_gsd_tools_fn=lambda start: fake.gsd_tools_path,
                            stdout=stdout)
        self.assertEqual(code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["cli"], "codex")
        warnings = [line for line in stderr.getvalue().splitlines() if "grok/grok-4.6" in line]
        self.assertEqual(len(warnings), 1)
        self.assertIn("codex, cursor-agent, opencode", warnings[0])

    def test_resolve_dispatch_write_failed_result_exits_1_carrying_the_undo_log(self):
        import json
        fake = FakeGsdTools("/tmp", fail_keys={"model_profile_overrides.codex.sonnet"})
        code, out = self._main(self._codex_assemble(), fake)
        self.assertEqual(code, 1)
        result = json.loads(out)
        self.assertEqual(result["mode"], "write_failed")
        self.assertEqual(result["applied"], ["runtime"])
        self.assertEqual(result["failed"], "model_profile_overrides.codex.sonnet")
        self.assertEqual(result["reverted"], ["runtime"])

    def test_resolve_dispatch_exits_2_when_gsd_tools_cannot_be_resolved(self):
        import contextlib
        import io
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = cli.main(["resolve-dispatch", "--cwd", "/repo", "--target-dir", "/repo",
                             "--quota-path", "/cache/quota.json"],
                            assemble_candidates_fn=lambda cwd, env: ([], []),
                            which_fn=_node_which, resolve_gsd_tools_fn=lambda start: None)
        self.assertEqual(code, 2)
        self.assertIn("gsd-tools", stderr.getvalue())

class TestCliConfigPath(unittest.TestCase):
    def test_config_path_prints_the_gsd_tools_resolved_path(self):
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t)
            stdout = io.StringIO()
            exit_code = cli.main(["config-path", "--cwd", t], run_fn=fake.run_fn,
                                 which_fn=_node_which,
                                 resolve_gsd_tools_fn=lambda start: fake.gsd_tools_path,
                                 stdout=stdout)
            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout.getvalue().strip(),
                             os.path.join(t, ".planning", "config.json"))

    def test_config_path_exits_2_when_gsd_tools_cannot_be_resolved(self):
        import contextlib
        import io
        with contextlib.redirect_stderr(io.StringIO()):
            exit_code = cli.main(["config-path", "--cwd", "/repo"], which_fn=_node_which,
                                 resolve_gsd_tools_fn=lambda start: None)
        self.assertEqual(exit_code, 2)


class TestCliClearWorkflowKeys(unittest.TestCase):
    def test_clear_workflow_keys_unset_only_adapter_owned_keys_through_config_set(self):
        import io
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t)
            fake.config["workflow.cross_ai_command"] = "codex exec ..."
            fake.config["workflow.user_key"] = "user-set"
            planning = os.path.join(t, ".planning")
            os.makedirs(planning)
            # The on-disk config.json is gsd-tools' own artifact; ai-kit only ever reads it.
            with open(os.path.join(planning, "config.json"), "w", encoding="utf-8") as f:
                json.dump({"workflow": {"cross_ai_command": "codex exec ...",
                                        "user_key": "user-set"}}, f)
            gsd_config.write_ownership(os.path.join(planning, "config.json"),
                                       {"workflow.cross_ai_command": "codex exec ..."})
            stdout = io.StringIO()
            exit_code = cli.main(
                ["clear-workflow-keys", "--cwd", t, "--run-id", "r1",
                 "--key", "cross_ai_command", "--key", "user_key"],
                run_fn=fake.run_fn, which_fn=_node_which,
                resolve_gsd_tools_fn=lambda start: fake.gsd_tools_path, stdout=stdout)
            self.assertEqual(exit_code, 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["applied"], ["workflow.cross_ai_command"])
            calls = fake.config_set_calls()
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][3:5], ["workflow.cross_ai_command", "null"])
            self.assertNotIn("workflow.cross_ai_command", fake.config)
            self.assertEqual(fake.config["workflow.user_key"], "user-set")  # user value kept
            with open(os.path.join(planning, "ai-kit-gsd-owned.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f), {})  # cleared key dropped from the sidecar


class FakeGsdTools:
    """In-memory gsd-tools double (plan 16.1-10): answers `config-set` against an in-memory
    dict and `config-path`, records every argv, and raises AssertionError on any other
    subcommand -- config-get included -- proving ai-kit never calls it (RUN-11)."""

    def __init__(self, root, fail_keys=(), raw_keys=()):
        self.gsd_tools_path = os.path.join(root, "gsd-core", "bin", "gsd-tools.cjs")
        self.config = {}  # dotted key -> value (stands in for config.json)
        self.calls = []
        self.fail_keys = set(fail_keys)
        self.raw_keys = set(raw_keys)

    def _completed(self, returncode, stdout="", stderr=""):
        return subprocess.CompletedProcess(
            args=["node", self.gsd_tools_path], returncode=returncode,
            stdout=stdout, stderr=stderr)

    def run_fn(self, argv, **kw):
        self.calls.append(list(argv))
        assert argv[0] == "node" and argv[1] == self.gsd_tools_path, argv
        sub, rest = argv[2], argv[3:]
        if sub == "config-set":
            return self._config_set(rest[0], rest[1])
        if sub == "config-path":
            cwd = rest[rest.index("--cwd") + 1]
            return self._completed(0, stdout=os.path.join(cwd, ".planning", "config.json") + "\n")
        raise AssertionError(f"FakeGsdTools saw an unexpected subcommand: {sub}")

    def _config_set(self, key, value):
        if key in self.fail_keys:
            return self._completed(1, stderr=f"Error: config-set failed for {key}")
        if key in self.raw_keys:
            return self._completed(0, stdout=f"{key}={value}\n")
        if value == "null":
            was_present = key in self.config
            old = self.config.pop(key, None)
            out = {"updated": True, "unset": True, "key": key, "value": None}
            if was_present:
                out["previousValue"] = old
            return self._completed(0, stdout=json.dumps(out) + "\n")
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = value
        out = {"updated": True, "key": key, "value": decoded}
        if key in self.config:
            out["previousValue"] = self.config[key]
        self.config[key] = decoded
        return self._completed(0, stdout=json.dumps(out) + "\n")

    def config_set_calls(self):
        return [argv for argv in self.calls if argv[2] == "config-set"]

    def subcommands(self):
        return [argv[2] for argv in self.calls]


def _node_which(name):
    return "node"


class TestWorkflowKeysViaConfigSet(unittest.TestCase):
    """R11: workflow keys reach GSD only through gsd-tools config-set, one call per key, with
    ownership in the sidecar and no direct config.json write."""

    def _run_write(self, fake, t, sets, stdout):
        return cli.main(
            ["write-workflow-keys", "--cwd", t, "--run-id", "r1"]
            + [flag for spec in sets for flag in ("--set", spec)],
            run_fn=fake.run_fn, which_fn=_node_which,
            resolve_gsd_tools_fn=lambda start: fake.gsd_tools_path, stdout=stdout)

    def test_non_json_set_value_is_a_usage_error_with_no_gsd_call(self):
        # ponytail L5: `--set k=notjson` exits 2 with a one-line message, never a traceback.
        import contextlib
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = self._run_write(fake, t, ["cross_ai_timeout=notjson"], io.StringIO())
            self.assertEqual(code, 2)
            self.assertIn("--set needs KEY=JSON", err.getvalue())
            self.assertEqual(fake.calls, [])

    def test_unresolvable_config_path_exits_2_and_writes_nothing(self):
        # A-WR-04: never guess <cwd>/.planning/config.json when gsd-tools' config-path fails
        # (in a workstream project that is the wrong file).
        import contextlib
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t)
            calls = []

            def run(argv, **kw):
                calls.append(argv[2])
                if argv[2] == "config-path":
                    return subprocess.CompletedProcess(argv, 1, "", "unknown command")
                return fake.run_fn(argv, **kw)

            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = cli.main(["write-workflow-keys", "--cwd", t, "--run-id", "r1",
                                 "--set", "cross_ai_execution=true"],
                                run_fn=run, which_fn=_node_which,
                                resolve_gsd_tools_fn=lambda start: fake.gsd_tools_path,
                                stdout=io.StringIO())
            self.assertEqual(code, 2)
            self.assertIn("could not resolve a config path", err.getvalue())
            self.assertEqual(calls, ["config-path"])

    def test_three_keys_go_through_config_set_one_call_each_in_plan_order(self):
        import io
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t)
            stdout = io.StringIO()
            code = self._run_write(fake, t,
                                   ['cross_ai_command="python3 x"', "cross_ai_execution=true",
                                    "cross_ai_timeout=900"], stdout)
            self.assertEqual(code, 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["applied"], ["workflow.cross_ai_command",
                                                  "workflow.cross_ai_execution",
                                                  "workflow.cross_ai_timeout"])
            self.assertIsNone(result["failed"])
            self.assertEqual(result["reverted"], [])
            calls = fake.config_set_calls()
            self.assertEqual(len(calls), 3)
            self.assertEqual([c[3] for c in calls],
                             ["workflow.cross_ai_command", "workflow.cross_ai_execution",
                              "workflow.cross_ai_timeout"])
            self.assertEqual(fake.config["workflow.cross_ai_execution"], True)
            self.assertEqual(fake.config["workflow.cross_ai_timeout"], 900)
            self.assertEqual(fake.config["workflow.cross_ai_command"], "python3 x")

    def test_ownership_sidecar_maps_each_dotted_key_to_its_written_value(self):
        import io
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t)
            stdout = io.StringIO()
            self._run_write(fake, t, ["cross_ai_execution=true"], stdout)
            with open(os.path.join(t, ".planning", "ai-kit-gsd-owned.json"),
                      encoding="utf-8") as f:
                owned = json.load(f)
            self.assertEqual(owned, {"workflow.cross_ai_execution": True})

    def test_no_direct_config_json_write_and_no_config_get_calls(self):
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t)
            config_json = os.path.join(t, ".planning", "config.json")
            spied = []
            real_write = gsd_config.cache_write_json
            with mock.patch.object(gsd_config, "cache_write_json",
                                   side_effect=lambda p, d: (spied.append(p),
                                                             real_write(p, d))):
                stdout = io.StringIO()
                self._run_write(fake, t, ["cross_ai_execution=true"], stdout)
            self.assertFalse(os.path.exists(config_json))  # never created by ai-kit
            for path in spied:
                self.assertFalse(path.endswith("config.json"), path)  # sidecar only
            self.assertNotIn("config-get", fake.subcommands())  # RUN-11

    def test_bytes_of_an_existing_config_json_are_untouched(self):
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            planning = os.path.join(t, ".planning")
            os.makedirs(planning)
            config_json = os.path.join(planning, "config.json")
            with open(config_json, "w", encoding="utf-8") as f:
                f.write('{"workflow": {"cross_ai_execution": false}}')
            with open(config_json, "rb") as f:
                before = f.read()
            fake = FakeGsdTools(t)
            fake.config["workflow.cross_ai_execution"] = False
            stdout = io.StringIO()
            self._run_write(fake, t, ["cross_ai_execution=true"], stdout)
            with open(config_json, "rb") as f:
                self.assertEqual(f.read(), before)  # gsd-tools owns the real write

    def test_write_workflows_keys_without_any_set_is_an_argparse_error(self):
        import contextlib
        import io
        import tempfile
        with (tempfile.TemporaryDirectory() as t,
              contextlib.redirect_stderr(io.StringIO()),
              self.assertRaises(SystemExit)):
            cli.main(["write-workflow-keys", "--cwd", t, "--run-id", "r1"],
                     run_fn=lambda *a, **k: None, which_fn=_node_which,
                     resolve_gsd_tools_fn=lambda start: "/x/gsd-tools.cjs")

    def test_empty_change_list_makes_zero_run_fn_calls(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t)
            ctx = gsd_config.GsdWriteContext(
                tools=gsd_tools.GsdTools("node", fake.gsd_tools_path), project_dir=t,
                config_path=os.path.join(t, ".planning", "config.json"),
                run_id="r1", run_fn=fake.run_fn)
            result = gsd_config.apply_changes(ctx, [])
            self.assertEqual(result, gsd_config.ApplyResult([], None, None, [], []))
            self.assertEqual(fake.calls, [])

    def test_gsd_core_version_banner_printed_once_with_version_file(self):
        import contextlib
        import io
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            os.makedirs(os.path.join(t, "gsd-core", "bin"))
            with open(os.path.join(t, "gsd-core", "VERSION"), "w", encoding="utf-8") as f:
                f.write("9.9.9\n")
            fake = FakeGsdTools(t)
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self._run_write(fake, t, ["cross_ai_execution=true"], stdout)
            expected = f"ai-kit: gsd-core 9.9.9 at {fake.gsd_tools_path}"
            self.assertEqual([l for l in stderr.getvalue().splitlines() if l.startswith("ai-kit:")],
                             [expected])
            self.assertEqual(json.loads(stdout.getvalue())["applied"],
                             ["workflow.cross_ai_execution"])

    def test_gsd_core_version_banner_says_unknown_without_a_version_file(self):
        import contextlib
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake = FakeGsdTools(t)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self._run_write(fake, t, ["cross_ai_execution=true"], io.StringIO())
            self.assertIn(f"ai-kit: gsd-core unknown at {fake.gsd_tools_path}",
                          stderr.getvalue())


class _FakeCompletedProcess:
    def __init__(self, returncode):
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


class TestCliPrepareTooling(unittest.TestCase):
    def test_prepare_tooling_runs_index_after_healthy_probe(self):
        import io
        index_dirs = []
        stdout = io.StringIO()
        exit_code = cli.main(
            ["prepare-tooling", "--cli", "codex", "--target-dir", "/repo"],
            detect_tool_availability_fn=lambda **k: {"codegraph": True, "rg": True},
            resolve_agents_tooling_path_fn=lambda **k: "/home/u/.agents/AGENTS-TOOLING.md",
            probe_codegraph_fn=lambda cli: detection.CodegraphProbe(True, True, None, "ok"),
            run_codegraph_index_fn=lambda target_dir: index_dirs.append(target_dir) or True,
            stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(index_dirs, ["/repo"])
        self.assertIn("AGENTS-TOOLING.md", stdout.getvalue())
        self.assertIn("codegraph_explore", stdout.getvalue())

    def test_prepare_tooling_prints_install_hint_on_stderr_when_probe_reports_missing(self):
        import contextlib
        import io
        hint = detection.codegraph_install_command("claude")
        index_dirs = []
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            cli.main(
                ["prepare-tooling", "--cli", "claude", "--target-dir", "/repo"],
                detect_tool_availability_fn=lambda **k: {"codegraph": True, "rg": True},
                resolve_agents_tooling_path_fn=lambda **k: None,
                probe_codegraph_fn=lambda cli: detection.CodegraphProbe(
                    False, False, hint, "codegraph not listed"),
                run_codegraph_index_fn=lambda target_dir: index_dirs.append(target_dir) or True,
                stdout=stdout)
        self.assertEqual(index_dirs, [])
        self.assertIn(hint, stderr.getvalue())
        self.assertNotIn(hint, stdout.getvalue())

    def test_prepare_tooling_indexes_when_health_is_unknown_but_registered(self):
        import contextlib
        import io
        index_dirs = []
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            cli.main(
                ["prepare-tooling", "--cli", "codex", "--target-dir", "/repo"],
                detect_tool_availability_fn=lambda **k: {"codegraph": True, "rg": True},
                resolve_agents_tooling_path_fn=lambda **k: None,
                probe_codegraph_fn=lambda cli: detection.CodegraphProbe(
                    True, None, None, "health not observable"),
                run_codegraph_index_fn=lambda target_dir: index_dirs.append(target_dir) or True,
                stdout=io.StringIO())
        self.assertEqual(index_dirs, ["/repo"])
        self.assertIn("is unknown", stderr.getvalue())

    def test_prepare_tooling_skips_index_when_registration_is_unknown(self):
        import io
        index_dirs = []
        cli.main(
            ["prepare-tooling", "--cli", "codex", "--target-dir", "/repo"],
            detect_tool_availability_fn=lambda **k: {"codegraph": True, "rg": True},
            resolve_agents_tooling_path_fn=lambda **k: None,
            probe_codegraph_fn=lambda cli: detection.CodegraphProbe(None, None, None, "timeout"),
            run_codegraph_index_fn=lambda target_dir: index_dirs.append(target_dir) or True,
            stdout=io.StringIO())
        self.assertEqual(index_dirs, [])

    def test_prepare_tooling_degrades_when_index_build_fails(self):
        import io
        stdout = io.StringIO()
        exit_code = cli.main(
            ["prepare-tooling", "--cli", "codex", "--target-dir", "/repo"],
            detect_tool_availability_fn=lambda **k: {"codegraph": True, "rg": True},
            resolve_agents_tooling_path_fn=lambda **k: "/home/u/.agents/AGENTS-TOOLING.md",
            probe_codegraph_fn=lambda cli: detection.CodegraphProbe(True, True, None, "ok"),
            run_codegraph_index_fn=lambda target_dir: False,
            stdout=stdout)
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



class TestMainCli(unittest.TestCase):
    def test_every_subcommand_has_a_handler(self):
        parser = cli._build_parser()
        subparsers = next(a for a in parser._actions if a.dest == "command")
        assert subparsers.choices is not None
        self.assertEqual(set(cli._COMMANDS), set(subparsers.choices))


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
            candidates,
            execute_selection.ExecuteResolveOptions(None, 1000, {}, []),
        )
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



class TestUntrustedLocalExecuteEntry(unittest.TestCase):
    """Plan 16.1-08 (R5): the DEFAULT cfg_resolve binding must be trust-gated, so a later
    seam refactor cannot silently bind a non-gated loader into execute dispatch."""

    def test_untrusted_local_execute_entry_absent_until_trusted(self):
        import io
        import tempfile
        from contextlib import redirect_stderr

        from ai_kit_spec import config_io, trust
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as xdg:
            env = {"HOME": home, "XDG_CONFIG_HOME": xdg}
            cwd = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, cwd, True)
            local_dir = os.path.join(cwd, ".aikit")
            os.makedirs(local_dir)
            local_path = os.path.join(local_dir, "review-spec.toml")
            raw = (b'strategy = "local-only"\n[[reviewers]]\nkey = "x1"\nmodel = "m"\n'
                   b'vendor = "v"\ncli = "codex"\ncommand = "codex exec -m {model}"\n'
                   b'purpose = "execute"\n')
            with open(local_path, "wb") as f:
                f.write(raw)
            with redirect_stderr(io.StringIO()):
                candidates, _ = adapter.assemble_candidates(cwd, env)
            self.assertNotIn("x1", [c["key"] for c in candidates])
            trust.record_trust(config_io.cfg_trust_store_dir(env),
                               os.path.realpath(local_path), raw)
            with redirect_stderr(io.StringIO()):
                candidates, _ = adapter.assemble_candidates(cwd, env)
            self.assertIn("x1", [c["key"] for c in candidates])


class TestNativeTierViaConfigSet(unittest.TestCase):
    """Native-tier writes go through one apply_changes call (config-set per key), ownership in
    the sidecar, and user-set values are never overwritten."""

    def _fake(self, t, fail_keys=()):
        fake = FakeGsdTools(t, fail_keys=fail_keys)
        ctx = _ctx(config_path=os.path.join(t, ".planning", "config.json"), run_fn=fake.run_fn,
                   project_dir=t, tools=gsd_tools.GsdTools("node", fake.gsd_tools_path))
        return fake, ctx

    def _codex_opus(self):
        return [{"cli": "codex", "model": "m-x", "key": "codex/m-x", "vendor": "openai",
                 "task_affinity": None, "context_limit": None, "tier": "opus"}]

    def test_codex_opus_on_a_claude_runtime_project_writes_runtime_then_tier(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake, ctx = self._fake(t)
            result = _resolve_gsd_dispatch(self._codex_opus(), ["codex/m-x"], {}, ctx,
                                                   t, current_runtime="claude")
            self.assertTrue(result["written"])
            keys = [c[3] for c in fake.config_set_calls()]
            self.assertEqual(keys, ["runtime", "model_profile_overrides.codex.opus"])
            owned = gsd_config.read_ownership(ctx.config_path)
            self.assertEqual(owned, {"runtime": "codex",
                                     "model_profile_overrides.codex.opus": "m-x"})

    def test_a_user_set_override_is_never_overwritten(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake, ctx = self._fake(t)
            cfg = {"model_profile_overrides": {"codex": {"opus": "user-model"}}}
            result = _resolve_gsd_dispatch(self._codex_opus(), ["codex/m-x"], cfg, ctx,
                                                   t, current_runtime="codex")
            self.assertFalse(result["written"])
            self.assertEqual(result["model"], "user-model")
            self.assertEqual(result["provenance"], "existing_gsd_config")
            self.assertEqual(fake.config_set_calls(), [])

    def test_claude_runtime_writes_model_profile_only_when_not_user_owned(self):
        import tempfile
        candidates = [{"cli": None, "model": "opus", "key": "opus-native", "vendor": "",
                       "task_affinity": None, "context_limit": None, "tier": "opus"}]
        with tempfile.TemporaryDirectory() as t:
            fake, ctx = self._fake(t)
            result = _resolve_gsd_dispatch(candidates, ["opus-native"], {}, ctx, t)
            self.assertEqual([c[3] for c in fake.config_set_calls()], ["model_profile"])
            self.assertEqual(result["model"], "quality")
        with tempfile.TemporaryDirectory() as t:
            fake, ctx = self._fake(t)
            cfg = {"model_profile": "budget"}  # hand-set user value, no sidecar record
            result = _resolve_gsd_dispatch(candidates, ["opus-native"], cfg, ctx, t)
            self.assertEqual(fake.config_set_calls(), [])
            self.assertEqual(result["provenance"], "existing_gsd_config")

    def test_a_failed_tier_write_reverts_the_runtime_and_reports_write_failed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            fake, ctx = self._fake(t, fail_keys={"model_profile_overrides.codex.opus"})
            result = _resolve_gsd_dispatch(self._codex_opus(), ["codex/m-x"], {}, ctx,
                                                   t, current_runtime="claude")
            self.assertEqual(result["mode"], "write_failed")
            self.assertEqual(result["applied"], ["runtime"])
            self.assertEqual(result["reverted"], ["runtime"])
            self.assertEqual(result["failed"], "model_profile_overrides.codex.opus")
            calls = fake.config_set_calls()
            self.assertEqual(calls[-1][3:5], ["runtime", "null"])

