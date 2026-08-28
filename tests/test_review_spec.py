import importlib.util
import json
import os
import subprocess
import tempfile
import time
import unittest
from unittest import mock

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "skills",
                             "review-spec", "review-spec.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("review_spec", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rs = _load_module()


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
        import tomllib
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
        import tomllib
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["reviewers"][0]["command"], 'echo "hi" \\ done')

    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_renders_top_level_strategy_when_present(self):
        rendered = rs.cfg_render_toml({"strategy": "local-only", "policy": {"mode": "single"},
                                        "reviewers": []})
        import tomllib
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["strategy"], "local-only")

    @unittest.skipIf(rs.tomllib is None, "tomllib not available on this interpreter")
    def test_omits_strategy_line_when_absent(self):
        rendered = rs.cfg_render_toml({"policy": {"mode": "single"}, "reviewers": []})
        import tomllib
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
        import tomllib
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


class TestCachePaths(unittest.TestCase):
    def test_base_uses_xdg_cache_home(self):
        env = {"XDG_CACHE_HOME": "/x/cache"}
        self.assertEqual(rs.cache_base(env), "/x/cache/ai-kit/review-spec")

    def test_base_falls_back_to_home_dot_cache(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(rs.cache_base(env), "/home/u/.cache/ai-kit/review-spec")

    def test_runtimes_and_quota_paths(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(rs.cache_runtimes_path(env),
                          "/home/u/.cache/ai-kit/review-spec/runtimes.json")
        self.assertEqual(rs.cache_quota_path(env), "/home/u/.cache/ai-kit/review-spec/quota.json")


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

    def test_double_mode_primary_is_best_native_entry_tier_aware(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 2)
        # best NATIVE entry (guaranteed baseline), tier-aware
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

    def test_double_mode_baseline_is_always_native_even_when_external_ranks_first(self):
        # regression for the design spec's "double mode always runs a
        # native baseline, guaranteed" guarantee
        # (docs/superpowers/specs/2026-08-27-review-spec-cross-ai-design.md
        # §3): an external entry ranked ABOVE every native entry in the
        # ladder must never become
        # the baseline — it can only ever take the second (cross-vendor)
        # slot.
        config = {
            "policy": {"mode": "double", "ladder": ["codex-gpt", "claude-opus", "claude-sonnet"]},
            "reviewers": self.config["reviewers"],
        }
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result[0].key, "claude-opus")   # native baseline, not codex-gpt
        self.assertIsNone(result[0].cli)
        self.assertEqual(result[1].key, "codex-gpt")     # external takes the secondary slot only

    def test_double_mode_baseline_falls_back_to_default_when_no_native_entry(self):
        # ladder is entirely external -> the native-baseline guarantee still
        # holds via NO_CONFIG_FALLBACK, never by promoting an external entry
        config = {
            "policy": {"mode": "double", "ladder": ["codex-gpt"]},
            "reviewers": [self.config["reviewers"][2]],  # codex-gpt only, no native entries at all
        }
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result[0], rs.NO_CONFIG_FALLBACK)
        self.assertEqual(result[1].key, "codex-gpt")

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

    def test_double_mode_secondary_dropped_when_no_native_and_only_source_vendor(self):
        # regression: when NO native entry is configured at all, primary
        # is NO_CONFIG_FALLBACK (vendor == "") -- an empty skip_vendor
        # disables resolve_ladder_pick's vendor filter entirely, so the
        # secondary walk must fall back to filtering against source_vendor
        # instead, or a same-source-vendor external entry (e.g. another
        # "anthropic"-vendor CLI) would wrongly fill the "cross-vendor"
        # slot opposite a native anthropic baseline.
        config = {
            "policy": {"mode": "double", "ladder": ["claude-cli-opus"]},
            "reviewers": [
                {"key": "claude-cli-opus", "model": "opus", "vendor": "anthropic",
                 "cli": "claude", "command": "claude -p --model {model} {prompt}"},
            ],
        }
        result = rs.resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 1)  # secondary dropped, not substituted
        self.assertEqual(result[0], rs.NO_CONFIG_FALLBACK)


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
        # `-p -` (dash-as-value) forces stdin; grok's -p requires *some*
        # value and won't accept a bare {prompt}-less flag
        self.assertEqual(rs.build_reviewer_command("grok"),
                          "grok -p - -m {model} --output-format plain")

    def test_gemini_command_shape(self):
        # unverified live (no installed CLI) — kept on the legacy
        # inline-{prompt} path deliberately, unlike the other 5 builders
        self.assertEqual(rs.build_reviewer_command("gemini"),
                          "gemini -m {model} --sandbox --approval-mode yolo {prompt}")

    def test_opencode_command_shape(self):
        # no {prompt} — confirmed live: `opencode run -m {model}` with no
        # positional message reads it from stdin
        self.assertEqual(rs.build_reviewer_command("opencode"),
                          "opencode run -m {model}")

    def test_cursor_agent_defaults_to_plan_mode(self):
        cmd = rs.build_reviewer_command("cursor-agent")
        self.assertIn("--mode plan", cmd)
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

    def test_cache_path_honors_xdg_cache_home(self):
        import io
        from contextlib import redirect_stdout
        env = {"XDG_CACHE_HOME": "/x/cache"}
        buf = io.StringIO()
        with mock.patch.object(rs.os, "environ", env), redirect_stdout(buf):
            code = rs.main(["cache-path", "--kind", "runtimes"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "/x/cache/ai-kit/review-spec/runtimes.json")

    def test_cache_path_quota_kind(self):
        import io
        from contextlib import redirect_stdout
        env = {"HOME": "/home/u"}
        buf = io.StringIO()
        with mock.patch.object(rs.os, "environ", env), redirect_stdout(buf):
            code = rs.main(["cache-path", "--kind", "quota"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "/home/u/.cache/ai-kit/review-spec/quota.json")

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


if __name__ == "__main__":
    unittest.main()
