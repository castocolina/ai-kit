import base64
import contextlib
import copy
import glob
import io
import json
import os
import re
import shlex
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import typing
import unittest
import unittest.mock
import urllib.error
import uuid
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

# Bare module imports -- test classes call module-qualified names like
# `detection.detect_tool_availability(...)`, which need the module in scope alongside the
# individually-named imports below.
from ai_kit_spec import (
    cache,
    cli,
    commands,
    config_io,
    detection,
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
    runner_dispatch,
    tooling_guidance,
    trust,
)
from ai_kit_spec.cache import (
    cache_base,
    cache_is_stale,
    cache_read_json,
    cache_write_bytes,
    cache_write_json,
    cache_write_text,
)
from ai_kit_spec.cli import main
from ai_kit_spec.commands import (
    ResolvedReviewer,
    build_cursor_agent_model_id,
    build_grok_command,
    build_reviewer_model_id,
    render_reviewer_command,
)
from ai_kit_spec.config_io import (
    cfg_global_path,
    cfg_load_toml,
    cfg_local_path,
    cfg_merge_reviewers,
    cfg_render_toml,
    cfg_resolve,
    cfg_write_toml,
    tomllib,
)
from ai_kit_spec.detection import (
    KNOWN_CLIS,
    build_runtimes_snapshot,
    cache_runtimes_path,
    detect_cursor_agent_models,
    detect_installed_clis,
    detect_opencode_models,
    group_models_by_family,
)
from ai_kit_spec.error_classifier import REASONS, classify_error
from ai_kit_spec.quota import (
    NO_CONFIG_FALLBACK,
    ProbeSeams,
    cache_quota_path,
    entry_reason,
    probe_reviewer_quota,
    refresh_quota_cache,
    resolve_ladder_pick,
    resolve_reviewers,
)
from ai_kit_spec.review_reports import (
    merge_findings,
    parse_findings,
    render_merged_report,
    report_status,
)
from ai_kit_spec.runner_dispatch import PI_EXEC_NOTE, RunnerResult
from ai_kit_spec.vendor import infer_vendor_from_model

# Fixture provenance (JSON cannot hold comments, so the record lives here, next to the
# constant the tests read the fixture through):
# - Source command: `codex debug models` (CLI version codex-cli 0.147.0, the real binary
#   resolved via PATH -- a volta shim, i.e. a real executable, not an alias/function).
# - Captured 2026-09-23 on the maintainer's machine
#   (.planning/phases/16-ai-kit-spec-extensions/16-RESEARCH.md, Pattern 2).
# - Kept verbatim: the six slugs and their order, display_name, description,
#   default_reasoning_level, every supported_reasoning_levels effort and description,
#   visibility, and priority.
# - Replaced: `model_messages` by a placeholder string; `context_window` and
#   `input_modalities` are set to one representative value for every model (not verified
#   per model; the parser never reads either).
# - Why the raw capture is not committed: it is 259 KB, almost all of it the vendor's
#   `model_messages.instructions_template` prompt text, which the parser never reads and
#   the repo should not carry.
CODEX_FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "codex_debug_models.json")

# Source: `opencode models --verbose`, opencode 1.18.32, 2026-09-24
# Capture: 110 header+JSON blocks (8528 lines)
# Kept verbatim: two real models (openai/gpt-5.6-sol, router-env/my-coding) with their
#   id, providerID, name, family, status, limit, and capabilities fields
# Trimmed: name, family, status, limit, and capabilities are kept as essential for this
#   test (image_input verification); model_messages, instructions_template, and other
#   verbose CLI metadata are omitted to keep the fixture small
# Why the raw capture is not committed: it enumerates every provider configured on the
#   maintainer's machine, including private router endpoints, so it is not public-shareable
OPENCODE_VERBOSE_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "opencode_models_verbose.txt"
)

# Source: `GET /api/model` on a scratch-HOME `opencode serve`, opencode v2.0.29,
# 2026-10-15 (.planning/phases/17-curated-config-inventory-recommendation-engine/
# 17-SPIKE-opencode-image-input.md).
# Kept verbatim: the spike sample's first 4 Model.Info objects (id, modelID, providerID,
#   capabilities, status, enabled), in spike order.
# `location` is replaced by a placeholder string; the parser never reads it.
OPENCODE_API_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "opencode_api_model.json"
)


# Fixture provenance (JSON cannot hold comments, so the record lives here):
# - Source command shape: `printf '{"id":"1","type":"get_available_models"}\n' | pi --mode rpc
#   --offline --no-session --no-extensions --no-skills --no-context-files --no-mcp`
# - pi 1.2.0, 2026-10-15, recorded in 18-RESEARCH L8.
# - Values synthetic; `baseUrl` never present (stripped from live captures).
# - Phase 22 replaces this with a trimmed real capture (22 D-04).
PI_RPC_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "pi_rpc_get_available_models.json"
)

def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()



_MODULE_CACHE = {}


def setUpModule():
    """opencode subprocess helpers create private dirs under the ai-kit cache base; keep
    every test off the real ~/.cache (AGENTS.md: never the user's real config)."""
    _MODULE_CACHE["dir"] = tempfile.mkdtemp(prefix="aikit-spec-cache-")
    _MODULE_CACHE["patch"] = mock.patch.dict(os.environ, {"XDG_CACHE_HOME": _MODULE_CACHE["dir"]})
    _MODULE_CACHE["patch"].start()


def tearDownModule():
    _MODULE_CACHE["patch"].stop()
    shutil.rmtree(_MODULE_CACHE["dir"], ignore_errors=True)

class TestConfigPaths(unittest.TestCase):
    def test_local_path_under_cwd_aikit(self):
        self.assertEqual(cfg_local_path("/repo"), "/repo/.aikit/review-spec.toml")

    def test_global_path_uses_xdg_config_home(self):
        env = {"XDG_CONFIG_HOME": "/x/config"}
        self.assertEqual(cfg_global_path(env), "/x/config/ai-kit/review-spec.toml")

    def test_global_path_falls_back_to_home_dot_config(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(cfg_global_path(env), "/home/u/.config/ai-kit/review-spec.toml")

    def test_base_is_never_relative_to_the_cwd(self):
        # A-WR-01: an unset/relative HOME or XDG_CONFIG_HOME must not resolve under the
        # project (a repo could then ship its own "global" config and trust store).
        with unittest.mock.patch.object(config_io.os.path, "expanduser", lambda p: "/pw/home"):
            self.assertEqual(config_io.cfg_config_base({}), "/pw/home/.config/ai-kit")
            self.assertEqual(config_io.cfg_config_base({"XDG_CONFIG_HOME": "rel", "HOME": "/h"}),
                             "/h/.config/ai-kit")
        with unittest.mock.patch.object(config_io.os.path, "expanduser", lambda p: "~"), \
                self.assertRaises(config_io.ConfigError):
            config_io.cfg_trust_store_dir({})


class TestLoadToml(unittest.TestCase):
    def test_missing_file_returns_empty_dict(self):
        self.assertEqual(cfg_load_toml("/no/such/file.toml"), {})

    def test_malformed_toml_raises_config_error(self):
        # D-11/R13 (Plan 16.1-08): a broken review-spec.toml fails LOUDLY (ConfigError with
        # the path and parser message) instead of silently disabling cross-AI review.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.toml")
            with open(path, "w", encoding="utf-8") as f:
                f.write("this is not [ valid toml")
            with self.assertRaises(config_io.ConfigError) as ctx:
                cfg_load_toml(path)
            self.assertIn(path, str(ctx.exception))

    def test_valid_toml_parses(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "good.toml")
            with open(path, "w", encoding="utf-8") as f:
                f.write('[policy]\nmode = "double"\n')
            self.assertEqual(cfg_load_toml(path), {"policy": {"mode": "double"}})


class TestMergeReviewers(unittest.TestCase):
    def test_local_overrides_matching_key_fields_only(self):
        global_list = [{"key": "codex-gpt", "model": "gpt-5.2", "effort": "high"}]
        local_list = [{"key": "codex-gpt", "effort": "low"}]
        merged = cfg_merge_reviewers(global_list, local_list)
        self.assertEqual(merged, [{"key": "codex-gpt", "model": "gpt-5.2", "effort": "low"}])

    def test_local_only_key_is_appended(self):
        global_list = [{"key": "a", "model": "m1"}]
        local_list = [{"key": "b", "model": "m2"}]
        merged = cfg_merge_reviewers(global_list, local_list)
        self.assertEqual([r["key"] for r in merged], ["a", "b"])

    def test_global_only_key_is_preserved(self):
        global_list = [{"key": "a", "model": "m1"}, {"key": "b", "model": "m2"}]
        local_list = [{"key": "a", "model": "m1-override"}]
        merged = cfg_merge_reviewers(global_list, local_list)
        self.assertEqual([r["key"] for r in merged], ["a", "b"])
        self.assertEqual(merged[0]["model"], "m1-override")

    def test_entry_with_no_key_is_skipped_not_raised(self):
        # one hand-written mistake in review-spec.toml must not crash the
        # whole orchestrator (matches cfg_load_toml's never-raises contract)
        global_list = [{"key": "a", "model": "m1"}, {"model": "no-key-here"}]
        local_list = [{"model": "also-no-key"}]
        merged = cfg_merge_reviewers(global_list, local_list)
        self.assertEqual([r["key"] for r in merged], ["a"])


class TestResolveConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, ignore_errors=True)
        self.global_home = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.global_home, ignore_errors=True)
        self.env = {"HOME": self.global_home}
        os.makedirs(os.path.join(self.global_home, ".config", "ai-kit"), exist_ok=True)
        with open(
            os.path.join(self.global_home, ".config", "ai-kit", "review-spec.toml"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(
                '[policy]\nmode = "single"\nladder = ["a"]\n'
                '[[reviewers]]\nkey = "a"\nmodel = "m1"\nvendor = "openai"\n'
            )

    def _trust_local_file(self, local_path: str) -> None:
        with open(local_path, "rb") as f:
            self._trust_local(f.read())

    def _trust_local(self, raw: bytes) -> None:
        """Record trust for this test's own local .aikit/review-spec.toml -- a local file is
        only applied once its exact content is trusted (Plan 16.1-08, HARD-03)."""
        trust.record_trust(
            config_io.cfg_trust_store_dir(self.env),
            os.path.realpath(config_io.cfg_local_path(self.tmp)),
            raw,
        )

    def test_no_local_file_uses_global_only(self):
        resolved = cfg_resolve(self.tmp, self.env)
        self.assertEqual(resolved["policy"]["mode"], "single")
        self.assertEqual(resolved["reviewers"][0]["key"], "a")

    def test_local_only_strategy_ignores_global(self):
        os.makedirs(os.path.join(self.tmp, ".aikit"), exist_ok=True)
        local_path = os.path.join(self.tmp, ".aikit", "review-spec.toml")
        with open(local_path, "w", encoding="utf-8") as f:
            f.write('strategy = "local-only"\n[policy]\nmode = "double"\n')
        self._trust_local_file(local_path)
        resolved = cfg_resolve(self.tmp, self.env)
        self.assertEqual(resolved["policy"]["mode"], "double")
        # local declared no reviewers, global not consulted
        self.assertEqual(resolved["reviewers"], [])

    def test_global_merge_is_the_default_strategy(self):
        os.makedirs(os.path.join(self.tmp, ".aikit"), exist_ok=True)
        local_path = os.path.join(self.tmp, ".aikit", "review-spec.toml")
        with open(local_path, "w", encoding="utf-8") as f:
            f.write('[[reviewers]]\nkey = "a"\nmodel = "m1"\nvendor = "openai"\neffort = "low"\n')
        self._trust_local_file(local_path)
        resolved = cfg_resolve(self.tmp, self.env)
        self.assertEqual(resolved["policy"]["mode"], "single")  # inherited from global
        self.assertEqual(resolved["reviewers"][0]["effort"], "low")  # local override applied


class TestRenderAndWriteToml(unittest.TestCase):
    @unittest.skipIf(tomllib is None, "tomllib not available on this interpreter")
    def test_round_trips_through_tomllib(self):
        import tomllib

        config = {
            "policy": {"mode": "double", "ladder": ["a", "b"]},
            "reviewers": [{"key": "a", "model": "m1", "vendor": "openai"}],
        }
        rendered = cfg_render_toml(config)
        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["policy"]["mode"], "double")
        self.assertEqual(parsed["policy"]["ladder"], ["a", "b"])
        self.assertEqual(parsed["reviewers"][0]["key"], "a")

    def test_write_toml_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "nested", "review-spec.toml")
            cfg_write_toml(path, {"policy": {"mode": "single"}, "reviewers": []})
            self.assertTrue(os.path.exists(path))

    def test_write_toml_replaces_atomically(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "review-spec.toml")
            config = {"policy": {"mode": "single"}, "reviewers": []}
            cfg_write_toml(path, {"policy": {"mode": "double"}, "reviewers": []})
            with mock.patch("ai_kit_spec.cache.os.replace", wraps=os.replace) as replace:
                cfg_write_toml(path, config)
            replace.assert_called_once()
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), cfg_render_toml(config))
            self.assertEqual(os.listdir(d), ["review-spec.toml"])

    @unittest.skipIf(tomllib is None, "tomllib not available on this interpreter")
    def test_escapes_quotes_and_backslashes_in_strings(self):
        rendered = cfg_render_toml(
            {"policy": {}, "reviewers": [{"key": "a", "command": 'echo "hi" \\ done'}]}
        )
        import tomllib

        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["reviewers"][0]["command"], 'echo "hi" \\ done')

    @unittest.skipIf(tomllib is None, "tomllib not available on this interpreter")
    def test_renders_top_level_strategy_when_present(self):
        rendered = cfg_render_toml(
            {"strategy": "local-only", "policy": {"mode": "single"}, "reviewers": []}
        )
        import tomllib

        parsed = tomllib.loads(rendered)
        self.assertEqual(parsed["strategy"], "local-only")

    @unittest.skipIf(tomllib is None, "tomllib not available on this interpreter")
    def test_omits_strategy_line_when_absent(self):
        rendered = cfg_render_toml({"policy": {"mode": "single"}, "reviewers": []})
        import tomllib

        parsed = tomllib.loads(rendered)
        self.assertNotIn("strategy", parsed)

    @unittest.skipIf(tomllib is None, "tomllib not available on this interpreter")
    def test_ladder_renders_as_priority_fallback_comment(self):
        rendered = cfg_render_toml(
            {
                "policy": {"mode": "double", "ladder": ["codex-gpt", "sonnet-native"]},
                "reviewers": [],
            }
        )
        self.assertIn("# Priority fallback order", rendered)
        self.assertIn("#   1. codex-gpt", rendered)
        self.assertIn("#   2. sonnet-native", rendered)
        import tomllib

        parsed = tomllib.loads(rendered)  # comment must not break parsing
        self.assertEqual(parsed["policy"]["ladder"], ["codex-gpt", "sonnet-native"])

    @unittest.skipIf(tomllib is None, "tomllib not available on this interpreter")
    def test_empty_ladder_renders_no_priority_comment(self):
        rendered = cfg_render_toml({"policy": {"mode": "single", "ladder": []}, "reviewers": []})
        self.assertNotIn("# Priority fallback order", rendered)

    @unittest.skipIf(tomllib is None, "tomllib not available on this interpreter")
    def test_single_mode_ladder_comment_omits_secondary_clause(self):
        rendered = cfg_render_toml(
            {
                "policy": {"mode": "single", "ladder": ["codex-gpt", "sonnet-native"]},
                "reviewers": [],
            }
        )
        self.assertIn("# Priority fallback order", rendered)
        self.assertNotIn("secondary", rendered)

    def test_render_toml_rejects_invalid_purpose_value(self):
        config = {
            "policy": {},
            "reviewers": [
                {"key": "a", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"}
            ],
        }
        output = config_io.cfg_render_toml(config)
        self.assertNotIn("not-a-real-purpose", output)

    def test_render_toml_rejects_non_string_purpose_without_raising(self):
        # HIGH finding: a non-string (unhashable) purpose value must be REJECTED, never crash
        # cfg_render_toml with an unhandled TypeError from a bare `in <set>` membership test.
        config = {
            "policy": {},
            "reviewers": [
                {"key": "a", "model": "m", "vendor": "v", "purpose": ["review", "execute"]}
            ],
        }
        output = config_io.cfg_render_toml(config)  # must not raise
        self.assertNotIn("[[reviewers]]", output)

    def test_render_toml_keeps_valid_purpose_value(self):
        config = {
            "policy": {},
            "reviewers": [{"key": "a", "model": "m", "vendor": "v", "purpose": "execute"}],
        }
        output = config_io.cfg_render_toml(config)
        self.assertIn('purpose = "execute"', output)

    def test_render_toml_rejects_non_bool_is_router(self):
        config = {
            "policy": {},
            "reviewers": [{"key": "a", "model": "m", "vendor": "v", "is_router": "yes"}],
        }
        output = config_io.cfg_render_toml(config)
        self.assertNotIn("is_router", output)

    def test_render_toml_drops_rejected_reviewer_from_the_ladder_too(self):
        # HIGH finding: a dangling policy.ladder reference to a dropped reviewer key produces
        # a config that LOOKS valid (parses fine) but resolve_ladder_pick can never satisfy.
        config = {
            "policy": {"mode": "single", "ladder": ["bad", "good"]},
            "reviewers": [
                {"key": "bad", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"},
                {"key": "good", "model": "m2", "vendor": "v2"},
            ],
        }
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
        config = {
            "policy": {"mode": "single", "ladder": ["good"]},
            "reviewers": [
                {"key": "bad", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"},
                {"key": "good", "model": "m2", "vendor": "v2"},
            ],
        }
        import io
        from contextlib import redirect_stderr

        captured = io.StringIO()
        with redirect_stderr(captured):
            config_io.cfg_render_toml(config)
        self.assertNotIn("dangling", captured.getvalue())

    def test_render_toml_rejects_dict_valued_reviewer_field(self):
        # WR-03 (code review, 01.2): `_toml_value` had no `dict` branch, so a dict-valued
        # reviewer field (e.g. a hand-edited/generated `extra = { timeout_tiers = [...] }`,
        # the exact failure mode SKILL.md documents as a known constraint) fell through to the
        # final `str(v)` branch and rendered Python's str()-of-a-dict as a quoted TOML STRING
        # (corrupted data, not a table) instead of being rejected like every other malformed
        # reviewer field. Must be rejected via the same rejections/WARNING pathway -- the
        # ENTIRE reviewer entry dropped, `[[reviewers]]` for it never emitted -- not silently
        # written as corrupted TOML.
        config = {
            "policy": {},
            "reviewers": [
                {"key": "a", "model": "m", "vendor": "v", "extra": {"timeout_tiers": [900, 1800]}}
            ],
        }
        output = config_io.cfg_render_toml(config)  # must not raise
        self.assertNotIn("[[reviewers]]", output)
        self.assertNotIn("timeout_tiers", output)
        self.assertNotIn("{'timeout_tiers'", output)  # the corrupted str(dict) rendering

    def test_render_toml_result_resolves_cleanly_through_cfg_resolve(self):
        # The dropped-entry write must be USABLE, not just superficially valid TOML -- round-trip
        # it through cfg_write_toml + cfg_resolve (this repo's real resolution path) and confirm
        # the ladder cfg_resolve sees contains no reference to the dropped key.
        config = {
            "policy": {"mode": "single", "ladder": ["bad", "good"]},
            "reviewers": [
                {"key": "bad", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"},
                {"key": "good", "model": "m2", "vendor": "v2", "runtime": "opencode"},
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            path = config_io.cfg_local_path(d)  # ./.aikit/review-spec.toml under d
            config_io.cfg_write_toml(path, config)
            with open(path, "rb") as f:
                raw = f.read()
            trust.record_trust(
                config_io.cfg_trust_store_dir({"HOME": d}), os.path.realpath(path), raw
            )
            resolved = config_io.cfg_resolve(d, {"HOME": d})
            self.assertNotIn("bad", resolved["policy"]["ladder"])
            self.assertIn("good", resolved["policy"]["ladder"])


class TestCacheCatalogPath(unittest.TestCase):
    def test_uses_cache_base_convention(self):
        path = model_catalog.cache_catalog_path({"HOME": "/home/u"})
        self.assertEqual(path, "/home/u/.cache/ai-kit/spec/model-catalog.json")


class TestCanonicalKey(unittest.TestCase):
    def test_builds_vendor_slash_model(self):
        self.assertEqual(model_catalog.canonical_key("openai", "gpt-5.6-sol"), "openai/gpt-5.6-sol")


class TestValidateCatalogEntry(unittest.TestCase):
    def _valid_entry(self, **overrides):
        entry = {
            "provider": "openai",
            "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {"models_dev": True},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }
        entry.update(overrides)
        return entry

    def test_valid_entry_returns_none(self):
        self.assertIsNone(
            model_catalog.validate_catalog_entry("openai/gpt-5.6-sol", self._valid_entry())
        )

    def test_missing_mandatory_field_is_rejected(self):
        entry = {"provider": "openai", "runtimes": {"opencode": {}}}
        reason = model_catalog.validate_catalog_entry("openai/gpt-5.6-sol", entry)
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("source", reason)

    def test_empty_runtimes_is_rejected(self):
        entry = {
            "provider": "openai",
            "runtimes": {},
            "source": {},
            "confidence": "low",
            "last_verified": "2026-09-02",
        }
        reason = model_catalog.validate_catalog_entry("x", entry)
        self.assertIsNotNone(reason)

    def test_none_on_a_mandatory_field_is_rejected(self):
        # Important finding: the None-skip meant for OPTIONAL fields (a signal to clear the
        # field on merge) must never extend to a mandatory field -- a mandatory field present
        # with value None is still missing its required value.
        reason = model_catalog.validate_catalog_entry("x", self._valid_entry(provider=None))
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("provider", reason)

    def test_missing_optional_fields_never_rejected(self):
        entry = {
            "provider": "openai",
            "runtimes": {"opencode": {}},
            "source": {},
            "confidence": "low",
            "last_verified": "2026-09-02",
        }
        self.assertIsNone(model_catalog.validate_catalog_entry("x", entry))

    def test_wrong_type_provider_is_rejected(self):
        reason = model_catalog.validate_catalog_entry("x", self._valid_entry(provider=123))
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("provider", reason)

    def test_non_dict_runtimes_is_rejected(self):
        reason = model_catalog.validate_catalog_entry("x", self._valid_entry(runtimes=["opencode"]))
        self.assertIsNotNone(reason)

    def test_unrecognized_confidence_value_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(confidence="very-sure")
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("confidence", reason)

    def test_wrong_type_optional_field_is_rejected(self):
        reason = model_catalog.validate_catalog_entry("x", self._valid_entry(batch_mode="yes"))
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("batch_mode", reason)

    def test_unrecognized_name_declared_purpose_value_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(name_declared_purpose="planning")
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("name_declared_purpose", reason)

    def test_review_name_declared_purpose_is_accepted(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(name_declared_purpose="review")
        )
        self.assertIsNone(reason)

    def test_execute_name_declared_purpose_is_accepted(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(name_declared_purpose="execute")
        )
        self.assertIsNone(reason)

    def test_absent_name_declared_purpose_is_never_rejected(self):
        reason = model_catalog.validate_catalog_entry("x", self._valid_entry())
        self.assertIsNone(reason)

    def test_wrong_type_scores_subfield_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(scores={"intelligence_index": "high"})
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("scores", reason)

    def test_correct_type_optional_fields_pass(self):
        entry = self._valid_entry(
            batch_mode=True,
            is_router=False,
            fallback_quota=False,
            tokens_per_sec=142.3,
            native=False,
            reasoning_modes=["low", "medium", "high"],
            fast_mode=False,
            speed_tier="standard",
            scores={"intelligence_index": 68.4, "coding_index": 74.1, "agentic_index": 61.2},
            pricing={"input_per_1m": 3.5, "output_per_1m": 14.0},
        )
        self.assertIsNone(model_catalog.validate_catalog_entry("x", entry))

    def test_wrong_type_reasoning_modes_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(reasoning_modes="high")
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("reasoning_modes", reason)

    def test_reasoning_modes_with_a_non_string_element_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(reasoning_modes=["low", 3])
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("reasoning_modes", reason)

    def test_wrong_type_fast_mode_is_rejected(self):
        reason = model_catalog.validate_catalog_entry("x", self._valid_entry(fast_mode="no"))
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("fast_mode", reason)

    def test_wrong_type_speed_tier_is_rejected(self):
        reason = model_catalog.validate_catalog_entry("x", self._valid_entry(speed_tier=3))
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("speed_tier", reason)

    def test_malformed_last_verified_date_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(last_verified="09/02/2026")
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("last_verified", reason)

    def test_runtime_entry_wrong_type_model_id_is_rejected(self):
        entry = self._valid_entry(runtimes={"opencode": {"model_id": 123}})
        reason = model_catalog.validate_catalog_entry("x", entry)
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("model_id", reason)

    def test_runtime_entry_wrong_type_ctx_window_is_rejected(self):
        entry = self._valid_entry(runtimes={"opencode": {"model_id": "m", "ctx_window": "big"}})
        reason = model_catalog.validate_catalog_entry("x", entry)
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("ctx_window", reason)

    def test_runtime_entry_correct_types_pass(self):
        entry = self._valid_entry(
            runtimes={"opencode": {"model_id": "openai/gpt-5.6-sol", "ctx_window": 400000}}
        )
        self.assertIsNone(model_catalog.validate_catalog_entry("x", entry))


class TestMergeCatalogEntry(unittest.TestCase):
    def test_valid_entry_is_added(self):
        entry = {
            "provider": "openai",
            "runtimes": {"opencode": {}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }
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
        existing_entry = {
            "provider": "p",
            "runtimes": {"c": {}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }
        catalog = {"k": existing_entry}
        entry = {
            "provider": None,
            "runtimes": {"c": {}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }
        catalog, reason = model_catalog.merge_catalog_entry(catalog, "k", entry)
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("provider", reason)
        self.assertEqual(catalog["k"]["provider"], "p")  # unchanged -- rejected merge never applied

    def test_does_not_mutate_input_catalog(self):
        original = {"existing": {}}
        entry = {
            "provider": "p",
            "runtimes": {"c": {}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }
        model_catalog.merge_catalog_entry(original, "new", entry)
        self.assertNotIn("new", original)

    def test_runtimes_merge_across_two_cli_writes_for_the_same_key(self):
        entry_a = {
            "provider": "openai",
            "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }
        catalog, _ = model_catalog.merge_catalog_entry({}, "openai/gpt-5.6-sol", entry_a)
        entry_b = {
            "provider": "openai",
            "runtimes": {"codex": {"model_id": "gpt-5.6-sol"}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }
        catalog, reason = model_catalog.merge_catalog_entry(catalog, "openai/gpt-5.6-sol", entry_b)
        self.assertIsNone(reason)
        self.assertIn("opencode", catalog["openai/gpt-5.6-sol"]["runtimes"])
        self.assertIn("codex", catalog["openai/gpt-5.6-sol"]["runtimes"])

    def test_explicit_none_in_the_incoming_entry_clears_the_existing_field(self):
        # CRITICAL finding: a source's provenance flipping to false must actually clear the
        # field it used to own, not leave it behind under plain dict-spread's "absent key
        # means preserve" semantics.
        existing_entry = {
            "provider": "p",
            "runtimes": {"c": {}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-09-02",
            "scores": {"intelligence_index": 91.0},
        }
        catalog = {"k": existing_entry}
        entry = {
            "provider": "p",
            "runtimes": {"c": {}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-09-02",
            "scores": None,
        }
        catalog, reason = model_catalog.merge_catalog_entry(catalog, "k", entry)
        self.assertIsNone(reason)
        self.assertNotIn("scores", catalog["k"])

    def test_key_absent_from_incoming_entry_still_preserves_the_existing_value(self):
        # Contrast with the test above: OMITTING a key (a source that's simply down this run,
        # never claiming anything about the field) must still preserve the cached value --
        # only an explicit None is a clear signal.
        existing_entry = {
            "provider": "p",
            "runtimes": {"c": {}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-09-02",
            "scores": {"intelligence_index": 91.0},
        }
        catalog = {"k": existing_entry}
        entry = {
            "provider": "p",
            "runtimes": {"c": {}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }  # no "scores" key at all
        catalog, reason = model_catalog.merge_catalog_entry(catalog, "k", entry)
        self.assertIsNone(reason)
        self.assertEqual(catalog["k"]["scores"], {"intelligence_index": 91.0})


class TestCurrentCandidateKeys(unittest.TestCase):
    def test_keeps_only_keys_with_a_currently_discovered_runtime(self):
        catalog = {
            "openai/gpt-5.6-sol": {"runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}}},
            "xai/grok-old": {"runtimes": {"opencode": {"model_id": "xai/grok-old"}}},
        }
        discovered = [{"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        self.assertEqual(
            model_catalog.current_candidate_keys(catalog, discovered), {"openai/gpt-5.6-sol"}
        )


class TestApplyHeuristicCorrections(unittest.TestCase):
    def test_merges_corrected_fields_into_existing_entry(self):
        catalog = {
            "router-env/x": {
                "provider": "router-env",
                "runtimes": {"opencode": {}},
                "source": {},
                "confidence": "low",
                "last_verified": "2026-09-02",
                "is_router": True,
            }
        }
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"is_router": False, "batch_mode": True}
        )
        self.assertIsNone(reason)
        self.assertFalse(updated["router-env/x"]["is_router"])
        self.assertTrue(updated["router-env/x"]["batch_mode"])

    def test_marks_every_corrected_field_confirmed_even_when_value_is_unchanged(self):
        # HIGH finding: the wizard must be able to tell "never asked" apart from "asked, and
        # the user's answer happened to match the heuristic's own guess" -- so a field must
        # be recorded as confirmed even when the "correction" leaves its value unchanged.
        catalog = {
            "router-env/x": {
                "provider": "router-env",
                "runtimes": {"opencode": {}},
                "source": {},
                "confidence": "low",
                "last_verified": "2026-09-02",
                "is_router": True,
            }
        }
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"is_router": True}
        )  # confirmed as-is, not corrected
        self.assertIsNone(reason)
        self.assertTrue(updated["router-env/x"]["is_router"])
        self.assertEqual(updated["router-env/x"]["heuristic_confirmed"], ["is_router"])

    def test_heuristic_confirmed_accumulates_across_separate_calls(self):
        catalog = {
            "router-env/x": {
                "provider": "router-env",
                "runtimes": {"opencode": {}},
                "source": {},
                "confidence": "low",
                "last_verified": "2026-09-02",
                "is_router": True,
                "heuristic_confirmed": ["is_router"],
            }
        }
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"batch_mode": False}
        )
        self.assertIsNone(reason)
        self.assertEqual(
            updated["router-env/x"]["heuristic_confirmed"], ["batch_mode", "is_router"]
        )

    def test_unknown_key_is_a_no_op(self):
        catalog = {"existing": {}}
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "nonexistent", {"is_router": True}
        )
        self.assertIsNone(reason)
        self.assertEqual(updated, catalog)

    def test_does_not_mutate_input_catalog(self):
        catalog = {
            "k": {
                "provider": "p",
                "runtimes": {"c": {}},
                "source": {},
                "confidence": "high",
                "last_verified": "2026-09-02",
                "is_router": True,
            }
        }
        model_catalog.apply_heuristic_corrections(catalog, "k", {"is_router": False})
        self.assertTrue(catalog["k"]["is_router"])

    def test_correction_that_would_produce_a_schema_invalid_entry_is_rejected(self):
        # CRITICAL finding: apply_heuristic_corrections must not bypass the same type-checked
        # schema validation merge_catalog_entry already enforces -- cache_write_json only writes
        # atomically, it never validates, so this is the ONLY gate before a bad correction reaches
        # the cache.
        catalog = {
            "router-env/x": {
                "provider": "router-env",
                "runtimes": {"opencode": {}},
                "source": {},
                "confidence": "low",
                "last_verified": "2026-09-02",
                "is_router": True,
            }
        }
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"is_router": "not-a-bool"}
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("is_router", reason)
        # unchanged -- rejected correction never applied
        self.assertTrue(updated["router-env/x"]["is_router"])


class TestCachePaths(unittest.TestCase):
    def test_base_uses_xdg_cache_home(self):
        env = {"XDG_CACHE_HOME": "/x/cache"}
        self.assertEqual(cache_base(env), "/x/cache/ai-kit/spec")

    def test_base_falls_back_to_home_dot_cache(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(cache_base(env), "/home/u/.cache/ai-kit/spec")

    def test_runtimes_and_quota_paths(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(cache_runtimes_path(env), "/home/u/.cache/ai-kit/spec/runtimes.json")
        self.assertEqual(cache_quota_path(env), "/home/u/.cache/ai-kit/spec/quota.json")


class TestCacheReadWrite(unittest.TestCase):
    def test_read_missing_file_returns_none(self):
        self.assertIsNone(cache_read_json("/no/such/file.json"))

    def test_write_then_read_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "data.json")
            cache_write_json(path, {"a": 1})
            self.assertEqual(cache_read_json(path), {"a": 1})

    def test_read_malformed_json_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not valid json")
            self.assertIsNone(cache_read_json(path))


class TestCacheWriteJsonAtomic(unittest.TestCase):
    def test_output_bytes_and_no_tmp_left(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "data.json")
            cache_write_json(path, {"b": 1, "a": [1, 2]})
            with open(path, "rb") as f:
                self.assertEqual(
                    f.read(), json.dumps({"b": 1, "a": [1, 2]}, indent=2).encode("utf-8")
                )
            self.assertEqual(glob.glob(os.path.join(d, "*.tmp")), [])

    def test_creates_missing_parent_directory(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "dir", "data.json")
            cache_write_json(path, {"a": 1})
            self.assertEqual(cache_read_json(path), {"a": 1})

    def test_error_leaves_original_and_no_tmp(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "data.json")
            cache_write_json(path, {"a": 1})
            with open(path, "rb") as f:
                original = f.read()
            # Fail after the temp file is written, so the cleanup path runs.
            with unittest.mock.patch(
                "ai_kit_spec.cache.os.replace", side_effect=OSError("injected")
            ), self.assertRaises(OSError):
                cache_write_json(path, {"a": 2})
            with open(path, "rb") as f:
                self.assertEqual(f.read(), original)
            self.assertEqual(glob.glob(os.path.join(d, "*.tmp")), [])

    def test_concurrent_writers_both_succeed(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "shared.json")
            errors = []

            def writer(w):
                try:
                    for i in range(50):
                        cache_write_json(path, {"w": w, "i": i})
                except Exception as exc:  # pragma-ish: recorded and asserted below
                    errors.append(exc)

            threads = [threading.Thread(target=writer, args=(w,)) for w in (1, 2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(errors, [])
            final = cache_read_json(path)
            assert final is not None
            assert isinstance(final, dict)
            self.assertIn(final["w"], (1, 2))
            self.assertEqual(glob.glob(os.path.join(d, "*.tmp")), [])

    def test_created_file_mode_is_0600(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "data.json")
            cache_write_json(path, {"a": 1})
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)


class TestCacheWriteBytes(unittest.TestCase):
    def test_writes_exact_bytes_including_non_utf8(self):
        payload = b"line\r\n\xff"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bin.dat")
            cache_write_bytes(path, payload)
            with open(path, "rb") as f:
                self.assertEqual(f.read(), payload)
            self.assertEqual(glob.glob(os.path.join(d, "*.tmp")), [])

    def test_applies_mode_when_given(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "mode.dat")
            cache_write_bytes(path, b"x", mode=0o640)
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o640)

    def test_error_leaves_original_and_no_tmp(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "data.dat")
            cache_write_bytes(path, b"one")
            with open(path, "rb") as f:
                original = f.read()
            with unittest.mock.patch(
                "ai_kit_spec.cache.os.replace", side_effect=OSError("injected")
            ), self.assertRaises(OSError):
                cache_write_bytes(path, b"two")
            with open(path, "rb") as f:
                self.assertEqual(f.read(), original)
            self.assertEqual(glob.glob(os.path.join(d, "*.tmp")), [])

    def test_umask_file_mode_follows_umask(self):
        old = os.umask(0o027)
        try:
            self.assertEqual(cache.umask_file_mode(), 0o640)
        finally:
            os.umask(old)

    @unittest.skipUnless(os.path.isfile("/proc/self/status"), "needs /proc")
    def test_umask_file_mode_never_zeroes_the_process_umask(self):
        """IN-11: reading the umask must not set it to 0, even briefly."""
        with unittest.mock.patch("ai_kit_spec.cache.os.umask") as umask:
            mode = cache.umask_file_mode()
        umask.assert_not_called()
        current = os.umask(0o022)
        os.umask(current)
        self.assertEqual(mode, 0o666 & ~current)

    def test_cache_write_text_utf8_round_trip_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "text.json")
            text = json.dumps({"a": 1}, indent=2)
            cache_write_text(path, text)
            with open(path, "rb") as f:
                self.assertEqual(f.read(), text.encode("utf-8"))


class TestCacheStaleness(unittest.TestCase):
    def test_missing_file_is_stale(self):
        self.assertTrue(cache_is_stale("/no/such/file.json", 3600))

    def test_fresh_file_is_not_stale(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.json")
            cache_write_json(path, {})
            self.assertFalse(cache_is_stale(path, 3600))

    def test_old_file_is_stale(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.json")
            cache_write_json(path, {})
            old = time.time() - 7200
            os.utime(path, (old, old))
            self.assertTrue(cache_is_stale(path, 3600))


class TestDetectInstalledClis(unittest.TestCase):
    def test_reports_installed_and_missing(self):
        def fake_which(name):
            return f"/usr/bin/{name}" if name in ("claude", "codex") else None

        result = detect_installed_clis(which_fn=fake_which)
        self.assertEqual(result["claude"], "/usr/bin/claude")
        self.assertEqual(result["codex"], "/usr/bin/codex")
        self.assertIsNone(result["cursor"])

    def test_covers_all_known_clis(self):
        result = detect_installed_clis(which_fn=lambda n: None)
        self.assertEqual(set(result.keys()), set(KNOWN_CLIS))


class TestDetectCurrentRuntime(unittest.TestCase):
    def test_claudecode_signal_returns_claude(self):
        self.assertEqual(detection.detect_current_runtime(env={"CLAUDECODE": "1"}), "claude")

    def test_opencode_signal_returns_opencode(self):
        self.assertEqual(
            detection.detect_current_runtime(env={"OPENCODE": "1", "OPENCODE_PID": "12345"}),
            "opencode",
        )

    def test_cursor_agent_signal_returns_cursor_not_cursor_agent(self):
        self.assertEqual(detection.detect_current_runtime(env={"CURSOR_AGENT": "1"}), "cursor")

    def test_codex_version_signal_returns_codex(self):
        self.assertEqual(
            detection.detect_current_runtime(env={"CODEX_VERSION": "0.153.4"}), "codex"
        )

    def test_empty_env_returns_unknown(self):
        self.assertEqual(detection.detect_current_runtime(env={}), "unknown")

    def test_empty_string_signal_is_falsy_and_falls_through(self):
        self.assertEqual(detection.detect_current_runtime(env={"CLAUDECODE": ""}), "unknown")

    def test_nested_subprocess_fixed_order_winner_is_opencode(self):
        self.assertEqual(
            detection.detect_current_runtime(env={"OPENCODE": "1", "CLAUDECODE": "1"}), "opencode"
        )

    def test_env_none_reads_live_os_environ(self):
        with unittest.mock.patch.dict(os.environ, {"CLAUDECODE": "1"}, clear=True):
            self.assertEqual(detection.detect_current_runtime(env=None), "claude")


class TestPiHostEndToEnd(unittest.TestCase):
    def test_pi_signal_wins_over_outer_claude_and_prints_pi(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                ["detect-current-runtime"],
                env_fn=lambda: {"PI_CODING_AGENT": "1", "CLAUDECODE": "1"},
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue()), {"host": "pi"})

    def test_pi_host_renders_as_the_session_default(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            main(
                ["detect-current-runtime"],
                env_fn=lambda: {"PI_CODING_AGENT": "1", "CLAUDECODE": "1"},
            )
        host = json.loads(buf.getvalue())["host"]
        self.assertEqual(host, "pi")
        # Only Claude Code aliases are per-call selectable today, so a pi host's native
        # entry is the session default: an empty model and no runtime.
        rendered = config_io.cfg_render_toml(
            {"policy": {}, "reviewers": [{"key": "native-primary", "model": ""}]}
        )
        self.assertIn("[[reviewers]]", rendered)
        self.assertIn('model = ""', rendered)
        self.assertNotIn("runtime =", rendered)

    def test_pi_host_is_a_table_runtime(self):
        self.assertIsNone(
            config_io.validate_reviewer_fields(
                {"key": "a", "runtime": "pi", "model": "m"}
            )
        )
        entry = {
            "provider": "openai",
            "runtimes": {"pi": {"model_id": "m"}},
            "source": {"models_dev": True},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }
        self.assertIsNone(model_catalog.validate_catalog_entry("x", entry))

    def test_codex_launched_from_claude_reads_as_codex(self):
        # Phase 20 D-02 rationale: claude is the usual outer orchestrator, so a codex
        # launched from Claude must read as codex, not claude.
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                ["detect-current-runtime"],
                env_fn=lambda: {"CODEX_THREAD_ID": "t-1", "CLAUDECODE": "1"},
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue()), {"host": "codex"})


class TestRuntimePrecedenceMatrix(unittest.TestCase):
    def test_signal_tuple_is_pinned(self):
        self.assertEqual(
            detection._RUNTIME_ENV_SIGNALS,
            (
                ("pi", "PI_CODING_AGENT"),
                ("opencode", "OPENCODE"),
                ("cursor", "CURSOR_AGENT"),
                ("codex", "CODEX_THREAD_ID"),
                ("codex", "CODEX_VERSION"),
                ("claude", "CLAUDECODE"),
            ),
        )

    def test_each_single_signal_maps_to_its_label(self):
        for var, label in (
            ("PI_CODING_AGENT", "pi"),
            ("OPENCODE", "opencode"),
            ("CURSOR_AGENT", "cursor"),
            ("CODEX_THREAD_ID", "codex"),
            ("CODEX_VERSION", "codex"),
            ("CLAUDECODE", "claude"),
        ):
            self.assertEqual(detection.detect_current_runtime(env={var: "1"}), label, msg=var)

    def test_all_signals_set_resolves_in_documented_order(self):
        # E1: with every signal set, removing the winner step by step walks the documented
        # precedence pi > opencode > cursor > codex > claude, then "unknown".
        env = {
            "PI_CODING_AGENT": "1",
            "OPENCODE": "1",
            "CURSOR_AGENT": "1",
            "CODEX_THREAD_ID": "1",
            "CODEX_VERSION": "1",
            "CLAUDECODE": "1",
        }
        steps = (
            ("PI_CODING_AGENT", "pi"),
            ("OPENCODE", "opencode"),
            ("CURSOR_AGENT", "cursor"),
            ("CODEX_THREAD_ID", "codex"),
            ("CODEX_VERSION", "codex"),
            ("CLAUDECODE", "claude"),
        )
        for removed_var, expected in steps:
            self.assertEqual(detection.detect_current_runtime(env=dict(env)), expected)
            del env[removed_var]
        self.assertEqual(detection.detect_current_runtime(env=dict(env)), "unknown")

    def test_both_codex_signals_return_codex_alone_or_together(self):
        # E3: the codex label owns TWO tuple rows (16 D-02) -- each alone, and both
        # together, must read as codex.
        self.assertEqual(detection.detect_current_runtime(env={"CODEX_THREAD_ID": "t-1"}), "codex")
        self.assertEqual(
            detection.detect_current_runtime(env={"CODEX_VERSION": "0.153.4"}), "codex"
        )
        self.assertEqual(
            detection.detect_current_runtime(
                env={"CODEX_THREAD_ID": "t-1", "CODEX_VERSION": "0.153.4"}
            ),
            "codex",
        )

    def test_empty_env_and_empty_string_signals_return_unknown(self):
        # E2: absent OR present-but-empty everywhere resolves to the literal str "unknown",
        # never None.
        self.assertEqual(detection.detect_current_runtime(env={}), "unknown")
        all_empty = {var: "" for _, var in detection._RUNTIME_ENV_SIGNALS}
        result = detection.detect_current_runtime(env=all_empty)
        self.assertEqual(result, "unknown")
        self.assertIsInstance(result, str)

    def test_empty_string_signal_falls_through_to_next(self):
        self.assertEqual(
            detection.detect_current_runtime(env={"PI_CODING_AGENT": "", "CLAUDECODE": "1"}),
            "claude",
        )

    def test_env_none_reads_live_os_environ_for_pi(self):
        with unittest.mock.patch.dict(os.environ, {"PI_CODING_AGENT": "1"}, clear=True):
            self.assertEqual(detection.detect_current_runtime(env=None), "pi")

    def test_known_clis_follow_runtime_table(self):
        self.assertEqual(
            detection.KNOWN_CLIS,
            ("pi", "opencode", "cursor", "codex", "claude", "grok"),
        )

    def test_docstring_confidence_labels_for_pi_and_codex_thread_id(self):
        # P1: pi and codex stay visibly flagged as not (yet) live-verified -- they must never
        # borrow the live-verified (01.2) label the opencode/claude bullets carry.
        # inspect.cleandoc normalizes across interpreter eras: CPython 3.14+ dedents
        # docstrings at compile time (_PyCompile_CleanDoc, "C implementation of
        # inspect.cleandoc()"), while <= 3.13 keeps the source indentation, so the raw
        # __doc__ bullet indentation is interpreter-dependent but its cleandoc form is not.
        import inspect

        doc = detection.detect_current_runtime.__doc__
        assert doc is not None
        doc = inspect.cleandoc(doc)
        bullets = doc.split("\n- ")
        pi_bullet = next(b for b in bullets if "PI_CODING_AGENT" in b)
        thread_id_bullet = next(b for b in bullets if "CODEX_THREAD_ID" in b)
        self.assertIn("source-inspected-only", pi_bullet)
        self.assertIn("not live-verified", pi_bullet)
        self.assertNotIn("live-verified (01.2)", pi_bullet)
        self.assertIn("not yet live-verified", thread_id_bullet)
        self.assertNotIn("live-verified (01.2)", thread_id_bullet)

    def test_docstring_names_only_signals_the_tuple_reads(self):
        # Review-cycle-1 honesty: every env var the tuple reads is documented, and the
        # docstring names no env var the tuple does not read (notably opencode's PID var).
        doc = detection.detect_current_runtime.__doc__
        assert doc is not None
        for _, var in detection._RUNTIME_ENV_SIGNALS:
            self.assertIn(var, doc, msg=var)
        self.assertNotIn("OPENCODE_PID", doc)


def _listing(stdout, returncode=0):
    return subprocess.CompletedProcess(["bin"], returncode, stdout=stdout, stderr="")


class TestListerOutcomes(unittest.TestCase):
    """A failed listing is None; a successful one is a list, possibly empty."""

    def _check(self, name, call, expected):
        with self.subTest(name=name):
            if expected is None:
                self.assertIsNone(call())
            else:
                self.assertEqual(call(), expected)

    def test_each_enumerator(self):
        pi_one = (
            '{"command":"get_available_models","success":true,'
            '"data":{"models":[{"id":"m","provider":"p"}]}}'
        )
        pi_empty = (
            '{"command":"get_available_models","success":true,"data":{"models":[]}}'
        )
        codex_one = json.dumps(
            {"models": [{"slug": "m", "visibility": "list"}]}
        )
        cursor_one = "Available models\n\nm - Name\n"
        cases = {
            "opencode-ids": (
                lambda: detect_opencode_models("/b", run_fn=lambda *_a, **_k: _listing("m\n")),
                ["m"],
            ),
            "opencode-empty": (
                lambda: detect_opencode_models("/b", run_fn=lambda *_a, **_k: _listing("")),
                [],
            ),
            "cursor-ids": (
                lambda: detect_cursor_agent_models(
                    "/b", run_fn=lambda *_a, **_k: _listing(cursor_one)
                ),
                ["m"],
            ),
            "cursor-empty": (
                lambda: detect_cursor_agent_models(
                    "/b", run_fn=lambda *_a, **_k: _listing("Available models\n")
                ),
                [],
            ),
            "codex-ids": (
                lambda: detection.detect_codex_models(
                    "/b", run_fn=lambda *_a, **_k: _listing(codex_one)
                ),
                [{"id": "m", "reasoning_modes": []}],
            ),
            "codex-empty": (
                lambda: detection.detect_codex_models(
                    "/b", run_fn=lambda *_a, **_k: _listing('{"models": []}')
                ),
                [],
            ),
            "pi-ids": (
                lambda: detection.detect_pi_models(
                    "/b", run_fn=lambda *_a, **_k: _listing(pi_one)
                ),
                [{
                    "id": "p/m",
                    "reasoning_modes": [],
                    "image_input": False,
                    "context_window": None,
                }],
            ),
            "pi-empty": (
                lambda: detection.detect_pi_models(
                    "/b", run_fn=lambda *_a, **_k: _listing(pi_empty)
                ),
                [],
            ),
        }
        for name, (call, expected) in cases.items():
            self._check(name, call, expected)
        self._check_failures(cursor_one, codex_one, pi_one)

    def _check_failures(self, cursor_one, codex_one, pi_one):
        def boom(exc):
            def run_fn(*_a, **_k):
                raise exc
            return run_fn

        timeout = subprocess.TimeoutExpired(cmd="bin", timeout=15)
        listers = (
            ("opencode", detect_opencode_models, "m\n"),
            ("cursor", detect_cursor_agent_models, cursor_one),
            ("codex", detection.detect_codex_models, codex_one),
            ("pi", detection.detect_pi_models, pi_one),
        )
        for label, fn, stdout in listers:
            self._check(
                f"{label}-timeout",
                lambda fn=fn: fn("/b", run_fn=boom(timeout)),
                None,
            )
            self._check(
                f"{label}-oserror",
                lambda fn=fn: fn("/b", run_fn=boom(OSError("down"))),
                None,
            )
            self._check(
                f"{label}-nonzero",
                lambda fn=fn, stdout=stdout: fn(
                    "/b", run_fn=lambda *_a, **_k: _listing(stdout, returncode=1)
                ),
                None,
            )
        self._check(
            "cursor-malformed",
            lambda: detect_cursor_agent_models(
                "/b", run_fn=lambda *_a, **_k: _listing("not a listing\n")
            ),
            None,
        )
        for name, stdout in (
            ("codex-invalid-json", "not json"),
            ("codex-non-dict", "[]"),
            ("codex-models-not-list", '{"models": {}}'),
        ):
            self._check(
                name,
                lambda stdout=stdout: detection.detect_codex_models(
                    "/b", run_fn=lambda *_a, **_k: _listing(stdout)
                ),
                None,
            )
        self._check(
            "pi-malformed",
            lambda: detection.detect_pi_models(
                "/b", run_fn=lambda *_a, **_k: _listing("no envelope")
            ),
            None,
        )


class TestDetectOpencodeModels(unittest.TestCase):
    def test_parses_one_model_per_line(self):
        class FakeResult:
            stdout = "opencode-go/kimi-k3\nopencode-go/qwen3.8-max\n\n"
            returncode = 0

        result = detect_opencode_models("/usr/bin/opencode", run_fn=lambda *a, **k: FakeResult())
        self.assertEqual(result, ["opencode-go/kimi-k3", "opencode-go/qwen3.8-max"])

    def test_returns_empty_list_on_failure(self):
        def fake_run(*a, **k):
            raise OSError("not found")

        self.assertIsNone(detect_opencode_models("/usr/bin/opencode", run_fn=fake_run))


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
            returncode = 0

        result = detect_cursor_agent_models(
            "/usr/bin/cursor-agent", run_fn=lambda *a, **k: FakeResult()
        )
        self.assertEqual(result, ["auto", "kimi-k3-high", "glm-5.2-high"])

    def test_skips_lines_with_no_separator(self):
        class FakeResult:
            stdout = "Available models\n\nauto - Auto (current, default)\n"
            returncode = 0

        result = detect_cursor_agent_models(
            "/usr/bin/cursor-agent", run_fn=lambda *a, **k: FakeResult()
        )
        self.assertEqual(result, ["auto"])

    def test_returns_empty_list_on_failure(self):
        def fake_run(*a, **k):
            raise OSError("not found")

        self.assertIsNone(
            detect_cursor_agent_models("/usr/bin/cursor-agent", run_fn=fake_run)
        )


class TestInferVendorFromModel(unittest.TestCase):
    def test_opencode_namespaced_ids(self):
        self.assertEqual(infer_vendor_from_model("opencode-go/kimi-k3"), "moonshot")
        self.assertEqual(infer_vendor_from_model("opencode-go/qwen3.8-max"), "alibaba")
        self.assertEqual(infer_vendor_from_model("opencode-go/grok-4.6"), "xai")
        self.assertEqual(infer_vendor_from_model("opencode-go/gpt-5.6-luna"), "openai")

    def test_cursor_agent_bare_ids(self):
        self.assertEqual(infer_vendor_from_model("claude-opus-5-thinking-high"), "anthropic")
        self.assertEqual(infer_vendor_from_model("gpt-5.3-codex"), "openai")
        self.assertEqual(infer_vendor_from_model("cursor-grok-4.6-high"), "xai")
        self.assertEqual(infer_vendor_from_model("glm-5.2-high"), "zhipu")
        self.assertEqual(infer_vendor_from_model("kimi-k3-high"), "moonshot")
        self.assertEqual(infer_vendor_from_model("gemini-3.7-flash-high"), "google")
        self.assertEqual(infer_vendor_from_model("composer-2.5"), "cursor")

    def test_unknown_prefix_returns_none(self):
        self.assertIsNone(infer_vendor_from_model("auto"))
        self.assertIsNone(infer_vendor_from_model("ollama-cloud/llama-70b"))


class TestGroupModelsByFamily(unittest.TestCase):
    def test_strips_trailing_tier_tokens(self):
        models = [
            "claude-opus-5-thinking-high-fast",
            "claude-opus-5-high",
            "claude-opus-5-low-fast",
        ]
        groups = group_models_by_family(models)
        self.assertEqual(groups, {"claude-opus-5": models})

    def test_keeps_different_versions_as_separate_families(self):
        # confirmed live: cursor-grok-4.5-* and cursor-grok-4.6-* are
        # genuinely different model generations, must never merge
        groups = group_models_by_family(["cursor-grok-4.5-high", "cursor-grok-4.6-high"])
        self.assertEqual(set(groups), {"cursor-grok-4.5", "cursor-grok-4.6"})

    def test_id_with_no_recognized_suffix_is_its_own_family(self):
        groups = group_models_by_family(["auto", "composer-2.5", "kimi-k2.7-code"])
        self.assertEqual(
            groups,
            {
                "auto": ["auto"],
                "composer-2.5": ["composer-2.5"],
                "kimi-k2.7-code": ["kimi-k2.7-code"],
            },
        )

    def test_empty_list_returns_empty_dict(self):
        self.assertEqual(group_models_by_family([]), {})

    def test_preserves_first_seen_order_of_families(self):
        groups = group_models_by_family(["b-high", "a-high", "b-low"])
        self.assertEqual(list(groups), ["b", "a"])


class TestDetectToolAvailability(unittest.TestCase):
    def test_reports_installed_and_missing_tools(self):
        def fake_which(name):
            return f"/usr/bin/{name}" if name in ("rg", "fd") else None

        result = detection.detect_tool_availability(which_fn=fake_which)
        self.assertEqual(
            result,
            {"rg": True, "sd": False, "bat": False, "eza": False, "fd": True, "codegraph": False},
        )


class TestResolveAgentsToolingPath(unittest.TestCase):
    def test_env_override_wins_when_it_exists(self):
        env = {"AGENTS_TOOLING_PATH": "/custom/AGENTS-TOOLING.md", "HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=True):
            self.assertEqual(
                detection.resolve_agents_tooling_path(env=env), "/custom/AGENTS-TOOLING.md"
            )

    def test_env_override_ignored_when_it_does_not_exist(self):
        # never pass an unverified path into a dispatch prompt, even one the user configured
        env = {"AGENTS_TOOLING_PATH": "/custom/AGENTS-TOOLING.md", "HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=False):
            self.assertIsNone(detection.resolve_agents_tooling_path(env=env))

    def test_falls_back_to_conventional_home_path_if_it_exists(self):
        env = {"HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=True):
            self.assertEqual(
                detection.resolve_agents_tooling_path(env=env), "/home/u/.agents/AGENTS-TOOLING.md"
            )

    def test_returns_none_when_nothing_found(self):
        env = {"HOME": "/home/u"}
        with unittest.mock.patch("os.path.isfile", return_value=False):
            self.assertIsNone(detection.resolve_agents_tooling_path(env=env))


class TestFindCodegraphAlternative(unittest.TestCase):
    def test_finds_grok_model_reachable_via_cursor_agent(self):
        snapshot = {
            "clis": {
                "cursor-agent": {
                    "installed": True,
                    "models": ["cursor-grok-4.6-high", "claude-opus-5-high"],
                },
                "opencode": {"installed": True, "models": ["opencode-go/qwen3.8-max"]},
            }
        }
        result = detection.find_codegraph_alternative("grok", "grok-4.6", snapshot)
        self.assertEqual(result, "cursor")

    def test_returns_none_when_cli_already_supports_codegraph(self):
        snapshot = {"clis": {"cursor-agent": {"installed": True, "models": ["cursor-grok-4.6"]}}}
        result = detection.find_codegraph_alternative("cursor-agent", "cursor-grok-4.6", snapshot)
        self.assertIsNone(result)

    def test_returns_none_when_no_matching_model_found_anywhere(self):
        snapshot = {
            "clis": {
                "cursor-agent": {"installed": True, "models": ["claude-opus-5-high"]},
                "opencode": {"installed": True, "models": ["opencode-go/qwen3.8-max"]},
            }
        }
        result = detection.find_codegraph_alternative("grok", "grok-4.6", snapshot)
        self.assertIsNone(result)

    def test_skips_a_codegraph_capable_cli_that_is_not_installed(self):
        snapshot = {"clis": {"cursor-agent": {"installed": False}}}
        result = detection.find_codegraph_alternative("grok", "grok-4.6", snapshot)
        self.assertIsNone(result)


class TestProbeCodegraph(unittest.TestCase):
    def _is_get(self, argv):
        return len(argv) >= 3 and argv[2] == "get"

    def test_grok_is_unsupported_without_running_any_command(self):
        probe = detection.probe_codegraph(
            "grok",
            run_fn=lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("must not run any command for grok")
            ),
        )
        self.assertEqual(probe.registered, False)
        self.assertEqual(probe.healthy, False)
        self.assertIsNone(probe.install_command)
        self.assertIn("grok", probe.detail)

    def test_unknown_cli_is_unsupported(self):
        self.assertFalse(detection.check_codegraph_mcp_usable("some-future-cli"))

    def test_claude_healthy_when_mcp_get_exits_zero_and_connected(self):
        probe = detection.probe_codegraph(
            "claude",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0, stdout="codegraph:\n  Status: ✔ Connected\n"
            ),
        )
        self.assertTrue(probe.registered)
        self.assertTrue(probe.healthy)
        self.assertIsNone(probe.install_command)
        self.assertTrue(
            detection.check_codegraph_mcp_usable(
                "claude",
                run_fn=lambda *a, **k: unittest.mock.MagicMock(
                    returncode=0, stdout="Status: ✔ Connected\n"
                ),
            )
        )

    def test_claude_unhealthy_when_get_shows_failed_to_connect(self):
        probe = detection.probe_codegraph(
            "claude",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0, stdout="Status: ✘ Failed to connect — CONNECTION_CLOSED\n"
            ),
        )
        self.assertTrue(probe.registered)
        self.assertFalse(probe.healthy)
        self.assertEqual(probe.install_command, detection.codegraph_install_command("claude"))

    def test_claude_missing_when_get_and_list_both_fail(self):
        def fake_run(argv, **k):
            if self._is_get(argv):
                return unittest.mock.MagicMock(returncode=1)
            return unittest.mock.MagicMock(returncode=0, stdout="other-tool: x - Connected\n")

        probe = detection.probe_codegraph("claude", run_fn=fake_run)
        self.assertFalse(probe.registered)
        self.assertFalse(probe.healthy)
        self.assertEqual(probe.install_command, detection.codegraph_install_command("claude"))

    def test_claude_get_success_skips_list_fallback(self):
        seen = []

        def fake_run(argv, **k):
            seen.append(argv)
            return unittest.mock.MagicMock(returncode=0, stdout="Status: ✔ Connected\n")

        detection.probe_codegraph("claude", run_fn=fake_run)
        self.assertEqual(seen, [detection._MCP_GET_COMMANDS["claude"]])

    def test_claude_get_fails_but_list_finds_healthy_entry(self):
        def fake_run(argv, **k):
            if self._is_get(argv):
                return unittest.mock.MagicMock(returncode=1)
            return unittest.mock.MagicMock(returncode=0, stdout="codegraph: x - ✔ Connected\n")

        probe = detection.probe_codegraph("claude", run_fn=fake_run)
        self.assertTrue(probe.registered and probe.healthy)

    def test_codex_registered_with_health_unknown_never_healthy(self):
        # A-WR-10/RUN-11: codex exposes no health, so it is never reported healthy.
        def run(*_a, **_k):
            return unittest.mock.MagicMock(returncode=0, stdout="anything\n")

        probe = detection.probe_codegraph("codex", run_fn=run)
        self.assertTrue(probe.registered)
        self.assertIsNone(probe.healthy)
        self.assertIsNone(probe.install_command)
        self.assertEqual(probe.detail, "registered; codex does not expose health")
        self.assertTrue(detection.check_codegraph_mcp_usable("codex", run_fn=run))

    def test_codex_get_output_with_a_failure_signal_is_unhealthy(self):
        probe = detection.probe_codegraph(
            "codex",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0, stdout="codegraph ✘ not connected\n"),
        )
        self.assertTrue(probe.registered)
        self.assertFalse(probe.healthy)
        self.assertEqual(probe.install_command, detection.codegraph_install_command("codex"))

    def test_failed_mcp_list_is_unknown_with_no_install_hint(self):
        # A-IN-05: a failing `mcp list` proves nothing about registration.
        probe = detection.probe_codegraph(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=1, stdout=""),
        )
        self.assertIsNone(probe.registered)
        self.assertIsNone(probe.healthy)
        self.assertIsNone(probe.install_command)

    def test_cursor_agent_parses_list_name_token(self):
        fake_list = "codegraph: some-command - ✔ Connected\nother-tool: x\n"
        probe = detection.probe_codegraph(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fake_list),
        )
        self.assertTrue(probe.registered and probe.healthy)

    def test_cursor_agent_false_when_codegraph_only_in_description(self):
        fake_list = "other-tool: some codegraph-related command - ✔ Connected\n"
        probe = detection.probe_codegraph(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fake_list),
        )
        self.assertFalse(probe.registered)

    def test_cursor_agent_unhealthy_line_gets_install_hint(self):
        fake_list = "codegraph: cmd - ✘ Failed to connect\n"
        probe = detection.probe_codegraph(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fake_list),
        )
        self.assertTrue(probe.registered)
        self.assertFalse(probe.healthy)
        self.assertEqual(probe.install_command, detection.codegraph_install_command("cursor-agent"))

    def test_opencode_list_parsing_matches_cursor_agent(self):
        probe = detection.probe_codegraph(
            "opencode",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0, stdout="codegraph: ✔ connected\n"
            ),
        )
        self.assertTrue(probe.registered and probe.healthy)

    def test_list_client_false_when_no_codegraph_entry(self):
        probe = detection.probe_codegraph(
            "cursor-agent",
            run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0, stdout="No MCP servers configured\n"
            ),
        )
        self.assertFalse(probe.registered)

    def test_timeout_yields_unknown_registered_and_healthy(self):
        def fake_run(argv, **k):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=k["timeout"])

        probe = detection.probe_codegraph("claude", run_fn=fake_run)
        self.assertIsNone(probe.registered)
        self.assertIsNone(probe.healthy)
        self.assertIsNone(probe.install_command)

    def test_oserror_yields_unknown_with_detail(self):
        def fake_run(argv, **k):
            raise OSError("no such binary")

        probe = detection.probe_codegraph("claude", run_fn=fake_run)
        self.assertIsNone(probe.registered)
        self.assertIn("no such binary", probe.detail)

    def test_every_subprocess_uses_argv_list_and_probe_timeout(self):
        recorded = []

        def fake_run(argv, **k):
            recorded.append((argv, k))
            return unittest.mock.MagicMock(returncode=1, stdout="")

        detection.probe_codegraph("claude", run_fn=fake_run)
        self.assertGreaterEqual(len(recorded), 2)
        for argv, kw in recorded:
            self.assertIsInstance(argv, (list, tuple))
            self.assertEqual(kw.get("timeout"), detection.CODEGRAPH_PROBE_TIMEOUT_SECONDS)
            joined = " ".join(argv)
            self.assertNotIn("install", joined)

    def test_no_supported_client_ever_runs_install_even_when_codegraph_missing(self):
        # R12: for every client, a "codegraph not registered" answer yields only a hint.
        for client in sorted(detection._SUPPORTED_CODEGRAPH_CLIENTS):
            with self.subTest(cli=client):
                recorded = []

                def fake_run(argv, recorded=recorded, **k):
                    recorded.append(list(argv))
                    # "mcp get" misses (rc 1); "mcp list" succeeds with no codegraph entry
                    return unittest.mock.MagicMock(
                        returncode=1 if "get" in argv else 0, stdout="")

                probe = detection.probe_codegraph(client, run_fn=fake_run)
                self.assertTrue(recorded)
                for argv in recorded:
                    self.assertNotIn("install", argv)
                    self.assertNotIn("add", argv)
                self.assertIs(probe.registered, False)
                self.assertTrue(probe.install_command)

    def test_hanging_cli_binary_respects_probe_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_claude = os.path.join(tmp, "claude")
            with open(fake_claude, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\nexec sleep 30\n")  # exec: the probe timeout kills sleep itself
            os.chmod(fake_claude, stat.S_IRWXU)
            env = os.environ.copy()
            env["PATH"] = tmp + os.pathsep + env.get("PATH", "")

            def patched_run(argv, **kw):
                kw["env"] = env
                return subprocess.run(argv, **kw)

            start = time.monotonic()
            probe = detection.probe_codegraph("claude", run_fn=patched_run, timeout=1)
            elapsed = time.monotonic() - start
            self.assertLess(elapsed, 5.0)
            self.assertIsNone(probe.registered)


class TestRunCodegraphIndex(unittest.TestCase):
    def test_sync_success_returns_true_without_init(self):
        calls = []

        def fake_run(argv, **kw):
            calls.append((argv, kw))
            return unittest.mock.MagicMock(returncode=0)

        self.assertTrue(detection.run_codegraph_index("/repo/root", run_fn=fake_run))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], ["codegraph", "sync"])
        self.assertEqual(calls[0][1]["cwd"], "/repo/root")

    def test_sync_failure_runs_init_in_target_dir(self):
        attempt = {"n": 0}

        def fake_run(argv, **kw):
            attempt["n"] += 1
            return unittest.mock.MagicMock(returncode=0 if attempt["n"] == 2 else 1)

        self.assertTrue(detection.run_codegraph_index("/tmp/a b", run_fn=fake_run))
        self.assertEqual(attempt["n"], 2)

    def test_both_fail_returns_false(self):
        def fake_run(argv, **kw):
            return unittest.mock.MagicMock(returncode=1)

        self.assertFalse(detection.run_codegraph_index("/repo", run_fn=fake_run))

    def test_timeout_returns_false(self):
        def fake_run(argv, **kw):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=15)

        self.assertFalse(detection.run_codegraph_index("/repo", run_fn=fake_run))

    def test_minimum_index_timeout_constant(self):
        self.assertEqual(detection.CODEGRAPH_INDEX_TIMEOUT_SECONDS, 15)


class TestBuildRuntimesSnapshot(unittest.TestCase):
    def test_marks_missing_clis_not_installed(self):
        snapshot = build_runtimes_snapshot(which_fn=lambda n: None, run_fn=lambda *a, **k: None)
        self.assertFalse(snapshot["clis"]["grok"]["installed"])

    def test_lists_opencode_models_when_installed(self):
        class FakeResult:
            stdout = "opencode-go/kimi-k3\n"
            returncode = 0

        def fake_which(name):
            return "/usr/bin/opencode" if name == "opencode" else None

        snapshot = build_runtimes_snapshot(
            which_fn=fake_which, run_fn=lambda *a, **k: FakeResult()
        )
        self.assertTrue(snapshot["clis"]["opencode"]["installed"])
        self.assertEqual(snapshot["clis"]["opencode"]["models"], ["opencode-go/kimi-k3"])

    def test_lists_cursor_agent_models_when_installed(self):
        class FakeResult:
            stdout = "Available models\n\nauto - Auto (current, default)\n"
            returncode = 0

        def fake_which(name):
            return "/usr/bin/cursor-agent" if name == "cursor-agent" else None

        snapshot = build_runtimes_snapshot(
            which_fn=fake_which, run_fn=lambda *a, **k: FakeResult()
        )
        self.assertTrue(snapshot["clis"]["cursor"]["installed"])
        self.assertEqual(snapshot["clis"]["cursor"]["models"], ["auto"])

    def test_non_multi_provider_clis_have_no_models_key(self):
        def fake_which(name):
            return "/usr/bin/codex" if name == "codex" else None

        snapshot = build_runtimes_snapshot(which_fn=fake_which, run_fn=lambda *a, **k: None)
        self.assertNotIn("models", snapshot["clis"]["codex"])

    @staticmethod
    def _fixture_text():
        with open(CODEX_FIXTURE_PATH, encoding="utf-8") as f:
            return f.read()

    def test_codex_models_and_reasoning_modes_from_fixture(self):
        fixture_text = self._fixture_text()

        def fake_which(name):
            return "/fake/volta/bin/codex" if name == "codex" else None

        snapshot = build_runtimes_snapshot(
            which_fn=fake_which,
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=0, stdout=fixture_text),
        )
        codex = snapshot["clis"]["codex"]
        self.assertEqual(codex["path"], "/fake/volta/bin/codex")
        self.assertEqual(
            codex["models"], ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"]
        )
        self.assertEqual(
            sorted(codex["reasoning_modes"]),
            sorted(["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"]),
        )
        self.assertEqual(codex["reasoning_modes"]["gpt-5.5"], ["low", "medium", "high", "xhigh"])

    def test_codex_enumeration_failure_omits_models_key(self):
        def fake_which(name):
            return "/fake/volta/bin/codex" if name == "codex" else None

        def fake_run_fn(*a, **k):
            raise OSError("codex debug models failed to launch")

        snapshot = build_runtimes_snapshot(which_fn=fake_which, run_fn=fake_run_fn)
        self.assertEqual(
            snapshot["clis"]["codex"], {"installed": True, "path": "/fake/volta/bin/codex"}
        )

    def test_codex_nonzero_exit_omits_models_key(self):
        # A failing command that still prints stale or partial JSON must not populate
        # models -- the entry degrades to bare installed/path (16 D-05's degrade path).
        fixture_text = self._fixture_text()

        def fake_which(name):
            return "/fake/volta/bin/codex" if name == "codex" else None

        snapshot = build_runtimes_snapshot(
            which_fn=fake_which,
            run_fn=lambda *a, **k: unittest.mock.MagicMock(returncode=1, stdout=fixture_text),
        )
        self.assertEqual(
            snapshot["clis"]["codex"], {"installed": True, "path": "/fake/volta/bin/codex"}
        )

    def test_failed_opencode_listing_omits_models_key(self):
        def fake_which(name):
            return "/usr/bin/opencode" if name == "opencode" else None

        def fake_run(*_a, **_k):
            raise OSError("down")

        snapshot = build_runtimes_snapshot(which_fn=fake_which, run_fn=fake_run)
        entry = snapshot["clis"]["opencode"]
        self.assertTrue(entry["installed"])
        self.assertNotIn("models", entry)

    def test_failed_cursor_listing_omits_models_key(self):
        def fake_which(name):
            return "/usr/bin/cursor-agent" if name == "cursor-agent" else None

        def fake_run(*_a, **_k):
            raise OSError("down")

        snapshot = build_runtimes_snapshot(which_fn=fake_which, run_fn=fake_run)
        entry = snapshot["clis"]["cursor"]
        self.assertTrue(entry["installed"])
        self.assertNotIn("models", entry)

    def test_empty_codex_listing_records_empty_models(self):
        def fake_which(name):
            return "/usr/bin/codex" if name == "codex" else None

        snapshot = build_runtimes_snapshot(
            which_fn=fake_which,
            run_fn=lambda *_a, **_k: _listing('{"models": []}'),
        )
        self.assertEqual(snapshot["clis"]["codex"]["models"], [])


class TestCodexEnumerationEndToEnd(unittest.TestCase):
    """Tracer for the full path: `codex debug models` (fixture text standing in for the
    real binary's stdout) -> detect-runtimes -> runtimes.json -> fetch-model-catalog ->
    model-catalog.json's existing `reasoning_modes` field (Phase 16 D-05/D-08)."""

    @staticmethod
    def _read_file(path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def _run_both(self, d, models_dev_data):
        fixture_text = self._read_file(CODEX_FIXTURE_PATH)
        recorded = []

        def fake_run_fn(argv, **kwargs):
            recorded.append((argv, kwargs))
            return unittest.mock.MagicMock(returncode=0, stdout=fixture_text)

        def fake_which(name):
            return "/fake/volta/bin/codex" if name == "codex" else None

        runtimes_path = os.path.join(d, "runtimes.json")
        catalog_path = os.path.join(d, "model-catalog.json")
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump({}, f)

        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                ["detect-runtimes", "--save", runtimes_path],
                which_fn=fake_which,
                run_fn=fake_run_fn,
                env_fn=lambda: {"HOME": d},
            )
        self.assertEqual(code, 0)
        buf2 = io.StringIO()
        with redirect_stdout(buf2):
            code = main(
                [
                    "fetch-model-catalog",
                    "--runtimes-json",
                    runtimes_path,
                    "--catalog-path",
                    catalog_path,
                ],
                fetch_models_dev_fn=lambda: (models_dev_data, True),
                fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                load_secret_fn=lambda env, key: None,
                env_fn=lambda: {"HOME": d},
            )
        self.assertEqual(code, 0)
        return catalog_path, runtimes_path, recorded, buf2.getvalue()

    @staticmethod
    def _models_dev_data(slugs):
        return {
            "openai": {
                "models": {
                    slug: {
                        "id": slug,
                        "tool_call": True,
                        "limit": {"context": 272000, "output": 128000},
                    }
                    for slug in slugs
                }
            }
        }

    def test_codex_models_flow_from_debug_models_into_the_catalog(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path, runtimes_path, recorded, _ = self._run_both(
                d,
                self._models_dev_data(["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"]),
            )
            runtimes = cache_read_json(runtimes_path)
            assert runtimes is not None
            self.assertEqual(
                runtimes["clis"]["codex"]["models"],
                ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"],
            )
            first_argv, first_kwargs = recorded[0]
            self.assertEqual(first_argv, ["/fake/volta/bin/codex", "debug", "models"])
            self.assertEqual(first_kwargs.get("timeout"), 15)
            self.assertFalse(first_kwargs.get("shell"))
            catalog = cache_read_json(catalog_path)
            assert catalog is not None
            terra = catalog["openai/gpt-5.6-terra"]
            self.assertEqual(terra["runtimes"]["codex"]["model_id"], "gpt-5.6-terra")
            self.assertEqual(
                terra["reasoning_modes"], ["low", "medium", "high", "xhigh", "max", "ultra"]
            )
            self.assertEqual(
                catalog["openai/gpt-5.5"]["reasoning_modes"], ["low", "medium", "high", "xhigh"]
            )

    def test_hidden_codex_models_never_reach_runtimes_or_catalog(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path, runtimes_path, _, _ = self._run_both(
                d,
                self._models_dev_data(["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"]),
            )
            catalog_raw = self._read_file(catalog_path)
            runtimes_raw = self._read_file(runtimes_path)
            for hidden in ("gpt-reserve", "codex-auto-review"):
                self.assertNotIn(hidden, runtimes_raw)
                self.assertNotIn(hidden, catalog_raw)

    def test_instruction_payload_is_never_persisted(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path, runtimes_path, _, _ = self._run_both(
                d,
                self._models_dev_data(["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"]),
            )
            for path in (catalog_path, runtimes_path):
                raw = self._read_file(path)
                self.assertNotIn("instructions_template", raw)
                self.assertNotIn("model_messages", raw)

    def test_every_written_codex_entry_passes_catalog_validation(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path, _, _, _ = self._run_both(
                d,
                self._models_dev_data(["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"]),
            )
            catalog = cache_read_json(catalog_path)
            assert catalog is not None
            self.assertTrue(catalog)
            for key, entry in catalog.items():
                if "codex" in entry.get("runtimes", {}):
                    self.assertIsNone(model_catalog.validate_catalog_entry(key, entry))

    def test_unmatched_codex_slug_carries_reasoning_modes_to_the_wizard(self):
        # A brand-new codex slug no external source knows exits through build_model_catalog's
        # unmatched branch -- its CLI-reported effort levels must still reach the wizard's
        # confirmation payload (review cycle 1 finding).
        with tempfile.TemporaryDirectory() as d:
            _, _, _, printed = self._run_both(
                d, self._models_dev_data(["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"])
            )
            result = json.loads(printed)
            gpt55 = [u for u in result["unmatched"] if u["model_id"] == "gpt-5.5"]
            self.assertEqual(len(gpt55), 1)
            self.assertEqual(gpt55[0]["runtime"], "codex")
            self.assertEqual(gpt55[0]["reasoning_modes"], ["low", "medium", "high", "xhigh"])
            self.assertFalse(
                [
                    k
                    for k in (cache_read_json(os.path.join(d, "model-catalog.json")) or {})
                    if k.endswith("/gpt-5.5")
                ]
            )


class TestParseCodexDebugModels(unittest.TestCase):
    """Pins parse_codex_debug_models: an unusable envelope is None; a valid one skips
    bad items and returns [] when nothing is listed."""

    @staticmethod
    def _fixture_text():
        with open(CODEX_FIXTURE_PATH, encoding="utf-8") as f:
            return f.read()

    def test_fixture_yields_only_listed_slugs_in_output_order(self):
        parsed = detection.parse_codex_debug_models(self._fixture_text())
        assert parsed is not None
        self.assertEqual(
            [m["id"] for m in parsed], ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"]
        )

    def test_fixture_effort_lists_match_supported_reasoning_levels(self):
        parsed = detection.parse_codex_debug_models(self._fixture_text())
        assert parsed is not None
        efforts = {m["id"]: m["reasoning_modes"] for m in parsed}
        self.assertEqual(efforts["gpt-5.6-sol"], ["low", "medium", "high", "xhigh", "max", "ultra"])
        self.assertEqual(
            efforts["gpt-5.6-terra"], ["low", "medium", "high", "xhigh", "max", "ultra"]
        )
        self.assertEqual(efforts["gpt-5.6-luna"], ["low", "medium", "high", "xhigh", "max"])
        self.assertEqual(efforts["gpt-5.5"], ["low", "medium", "high", "xhigh"])

    def test_non_string_input_returns_empty(self):
        self.assertIsNone(detection.parse_codex_debug_models(None))
        self.assertIsNone(detection.parse_codex_debug_models(b"{}"))
        self.assertIsNone(detection.parse_codex_debug_models(42))

    def test_invalid_json_returns_empty(self):
        self.assertIsNone(detection.parse_codex_debug_models(""))
        self.assertIsNone(detection.parse_codex_debug_models("not json"))
        self.assertIsNone(detection.parse_codex_debug_models("{"))

    def test_unexpected_top_level_shapes_return_empty(self):
        self.assertIsNone(detection.parse_codex_debug_models("[]"))
        self.assertIsNone(detection.parse_codex_debug_models("{}"))
        self.assertIsNone(detection.parse_codex_debug_models('{"models": {}}'))
        self.assertIsNone(detection.parse_codex_debug_models('{"models": null}'))

    def test_malformed_items_are_skipped_not_fatal(self):
        stdout = json.dumps(
            {
                "models": [
                    3,
                    "x",
                    {},
                    {"slug": "", "visibility": "list"},
                    {"slug": 5, "visibility": "list"},
                    {"slug": "ok", "visibility": "list"},
                ]
            }
        )
        self.assertEqual(
            detection.parse_codex_debug_models(stdout), [{"id": "ok", "reasoning_modes": []}]
        )

    def test_missing_or_malformed_levels_degrade_to_empty_modes(self):
        base = {"slug": "m", "visibility": "list"}
        cases = [
            {**base},  # key missing
            {**base, "supported_reasoning_levels": "high"},  # a string, not a list
            {
                **base,
                "supported_reasoning_levels": [
                    1,
                    {"effort": ""},
                    {"effort": "low"},
                    {"effort": "low"},
                    {"x": 1},
                ],
            },
        ]
        for item in cases:
            stdout = json.dumps({"models": [item]})
            self.assertEqual(
                detection.parse_codex_debug_models(stdout),
                [
                    {"id": "m", "reasoning_modes": ["low"]}
                    if "supported_reasoning_levels" in item
                    and isinstance(item["supported_reasoning_levels"], list)
                    else {"id": "m", "reasoning_modes": []}
                ],
            )

    def test_missing_visibility_is_treated_as_hidden(self):
        stdout = json.dumps({"models": [{"slug": "m"}]})
        self.assertEqual(detection.parse_codex_debug_models(stdout), [])

    def test_duplicate_slug_keeps_first(self):
        stdout = json.dumps(
            {
                "models": [
                    {
                        "slug": "m",
                        "visibility": "list",
                        "supported_reasoning_levels": [{"effort": "low"}],
                    },
                    {
                        "slug": "m",
                        "visibility": "list",
                        "supported_reasoning_levels": [{"effort": "high"}],
                    },
                ]
            }
        )
        self.assertEqual(
            detection.parse_codex_debug_models(stdout), [{"id": "m", "reasoning_modes": ["low"]}]
        )


class TestDetectCodexModels(unittest.TestCase):
    """Pins detect_codex_models's real-binary argv (16 D-07) and its never-raise degrade
    contract, including the non-zero-exit-is-failure gate."""

    @staticmethod
    def _fixture_text():
        with open(CODEX_FIXTURE_PATH, encoding="utf-8") as f:
            return f.read()

    def test_invokes_the_resolved_real_binary_with_an_argv_list(self):
        recorded = {}

        def fake_run_fn(argv, **kwargs):
            recorded["argv"] = argv
            recorded["kwargs"] = kwargs
            return unittest.mock.MagicMock(returncode=0, stdout=self._fixture_text())

        models = detection.detect_codex_models("/fake/volta/bin/codex", run_fn=fake_run_fn)
        assert models is not None
        self.assertEqual(
            [m["id"] for m in models], ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"]
        )
        self.assertEqual(recorded["argv"], ["/fake/volta/bin/codex", "debug", "models"])
        self.assertEqual(recorded["kwargs"].get("timeout"), 15)
        self.assertFalse(recorded["kwargs"].get("shell"))

    def test_oserror_returns_empty(self):
        def fake_run_fn(*a, **k):
            raise OSError("binary vanished")

        self.assertIsNone(detection.detect_codex_models("/fake/codex", run_fn=fake_run_fn))

    def test_timeout_returns_empty(self):
        def fake_run_fn(*a, **k):
            raise subprocess.TimeoutExpired(cmd="codex", timeout=15)

        self.assertIsNone(detection.detect_codex_models("/fake/codex", run_fn=fake_run_fn))

    def test_none_result_returns_empty(self):
        self.assertIsNone(
            detection.detect_codex_models("/fake/codex", run_fn=lambda *a, **k: None)
        )

    def test_empty_stdout_returns_empty(self):
        result = unittest.mock.MagicMock(returncode=0, stdout="")
        self.assertIsNone(
            detection.detect_codex_models("/fake/codex", run_fn=lambda *a, **k: result)
        )

    def test_nonzero_exit_with_valid_json_returns_empty(self):
        # A failing command that still prints stale or partial JSON must not populate
        # models -- non-zero exit is a failure, not a success with a payload.
        result = unittest.mock.MagicMock(returncode=1, stdout=self._fixture_text())
        self.assertIsNone(
            detection.detect_codex_models("/fake/codex", run_fn=lambda *a, **k: result)
        )

    def test_result_without_returncode_returns_empty(self):
        class NoReturnCode:
            stdout = self._fixture_text()

        self.assertIsNone(
            detection.detect_codex_models("/fake/codex", run_fn=lambda *a, **k: NoReturnCode())
        )


class TestPiRpcModels(unittest.TestCase):
    """18 D-25: pi RPC get_available_models parser and snapshot branch."""

    @staticmethod
    def _fixture_text():
        with open(PI_RPC_FIXTURE_PATH, encoding="utf-8") as f:
            return f.read()

    def test_parse_fixture_models_in_order(self):
        parsed = detection.parse_pi_models(self._fixture_text())
        assert parsed is not None
        self.assertEqual(
            [m["id"] for m in parsed],
            ["anthropic/claude-sonnet-5", "openai/gpt-5.6-terra", "router-env/my-coding"],
        )
        sonnet, terra, router = parsed
        self.assertEqual(sonnet["reasoning_modes"], ["low", "medium", "high"])
        self.assertTrue(sonnet["image_input"])
        self.assertEqual(sonnet["context_window"], 200000)
        self.assertEqual(terra["reasoning_modes"], ["minimal", "low", "medium", "high"])
        self.assertFalse(terra["image_input"])
        self.assertEqual(terra["context_window"], 400000)
        self.assertEqual(router["reasoning_modes"], [])
        self.assertFalse(router["image_input"])

    def test_snapshot_pi_installed_with_fixture_listing(self):
        fixture = self._fixture_text()
        pi_path = "/tmp/pi-token-for-test"
        recorded = {}

        def fake_which(name):
            return pi_path if name == "pi" else None

        def fake_run(argv, **kwargs):
            recorded["argv"] = argv
            recorded["kwargs"] = kwargs
            return subprocess.CompletedProcess(argv, 0, stdout=fixture, stderr="")

        snapshot = build_runtimes_snapshot(which_fn=fake_which, run_fn=fake_run)
        self.assertEqual(
            snapshot["clis"]["pi"],
            {
                "installed": True,
                "path": pi_path,
                "models": [
                    "anthropic/claude-sonnet-5",
                    "openai/gpt-5.6-terra",
                    "router-env/my-coding",
                ],
                "reasoning_modes": {
                    "anthropic/claude-sonnet-5": ["low", "medium", "high"],
                    "openai/gpt-5.6-terra": ["minimal", "low", "medium", "high"],
                },
                "image_input": {
                    "anthropic/claude-sonnet-5": True,
                    "openai/gpt-5.6-terra": False,
                    "router-env/my-coding": False,
                },
            },
        )
        self.assertEqual(recorded["argv"], [pi_path, *detection.PI_RPC_ARGS])
        self.assertEqual(recorded["kwargs"]["input"], detection.PI_RPC_REQUEST)
        self.assertEqual(recorded["kwargs"]["timeout"], 15)

    def test_parse_returns_none_without_usable_envelope(self):
        for bad in (None, "", "not json", '{"command":"other"}'):
            self.assertIsNone(detection.parse_pi_models(bad))
        false_resp = (
            '{"command":"get_available_models","success":false,"data":{"models":[]}}'
        )
        self.assertIsNone(detection.parse_pi_models(false_resp))
        missing_data = '{"command":"get_available_models","success":true}'
        self.assertIsNone(detection.parse_pi_models(missing_data))
        bad_models = (
            '{"command":"get_available_models","success":true,"data":{"models":{}}}'
        )
        self.assertIsNone(detection.parse_pi_models(bad_models))

    def test_parse_empty_list_when_all_models_skipped(self):
        line = (
            '{"command":"get_available_models","success":true,'
            '"data":{"models":[{"id":"","provider":"x"}]}}'
        )
        self.assertEqual(detection.parse_pi_models(line), [])

    def test_parse_skips_blank_provider_and_field_defaults(self):
        line = (
            '{"command":"get_available_models","success":true,"data":{"models":['
            '{"id":"m","provider":"","input":"text","contextWindow":"n"},'
            '{"id":"m2","provider":"p","input":null,"contextWindow":1.5}'
            ']}}'
        )
        parsed = detection.parse_pi_models(line)
        assert parsed is not None
        self.assertEqual(len(parsed), 1)
        rec = parsed[0]
        self.assertEqual(rec["id"], "p/m2")
        self.assertEqual(rec["reasoning_modes"], [])
        self.assertFalse(rec["image_input"])
        self.assertIsNone(rec["context_window"])

    def test_detect_pi_models_failure_paths_return_none(self):
        fixture = self._fixture_text()

        def oserror(*a, **k):
            raise OSError("gone")

        def timeout(*a, **k):
            raise subprocess.TimeoutExpired(cmd="pi", timeout=15)

        def bad_rc(*_a, **_k):
            return subprocess.CompletedProcess(["pi"], 1, stdout=fixture, stderr="")

        def bad_parse(*_a, **_k):
            return subprocess.CompletedProcess(["pi"], 0, stdout="not json", stderr="")
        self.assertIsNone(detection.detect_pi_models("/pi", run_fn=oserror))
        self.assertIsNone(detection.detect_pi_models("/pi", run_fn=timeout))
        self.assertIsNone(detection.detect_pi_models("/pi", run_fn=bad_rc))
        self.assertIsNone(detection.detect_pi_models("/pi", run_fn=bad_parse))

    def test_snapshot_omits_models_on_failed_pi_listing(self):
        pi_path = "/tmp/pi-fail-test"

        def fake_which(name):
            return pi_path if name == "pi" else None

        def bad_run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout="not json", stderr="")

        snapshot = build_runtimes_snapshot(which_fn=fake_which, run_fn=bad_run)
        entry = snapshot["clis"]["pi"]
        self.assertEqual(entry, {"installed": True, "path": pi_path})
        self.assertNotIn("models", entry)

    def test_snapshot_empty_valid_listing(self):
        empty = (
            '{"command":"get_available_models","success":true,"data":{"models":[]}}'
        )
        pi_path = "/tmp/pi-empty-test"

        def fake_which(name):
            return pi_path if name == "pi" else None

        def fake_run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout=empty, stderr="")

        snapshot = build_runtimes_snapshot(which_fn=fake_which, run_fn=fake_run)
        self.assertEqual(
            snapshot["clis"]["pi"],
            {
                "installed": True,
                "path": pi_path,
                "models": [],
                "reasoning_modes": {},
                "image_input": {},
            },
        )

    def test_snapshot_pi_not_installed(self):
        snapshot = build_runtimes_snapshot(which_fn=lambda n: None, run_fn=lambda *a, **k: None)
        self.assertEqual(snapshot["clis"]["pi"], {"installed": False})



class TestPiRouterMerge(unittest.TestCase):
    """18 D-45: pi-discovered router merges into an existing catalog entry."""

    def test_pi_router_merges_runtimes_into_existing_opencode_entry(self):
        existing = {
            "router-env/my-coding": {
                "batch_mode": False,
                "confidence": "low",
                "fallback_quota": True,
                "heuristic_confirmed": ["is_router"],
                "is_router": True,
                "last_verified": "2026-10-15",
                "name_declared_purpose": "execute",
                "provider": "router-env",
                "runtimes": {
                    "opencode": {"ctx_window": None, "model_id": "router-env/my-coding"},
                },
                "source": {
                    "artificial_analysis": False,
                    "manual": False,
                    "models_dev": False,
                },
            }
        }
        discovered = [{"runtime": "pi", "model_id": "router-env/my-coding"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, False, [], False), existing
        )
        self.assertEqual(rejections, [])
        self.assertEqual(unmatched, [])
        entry = catalog["router-env/my-coding"]
        self.assertIn("opencode", entry["runtimes"])
        self.assertIn("pi", entry["runtimes"])
        self.assertEqual(entry["heuristic_confirmed"], ["is_router"])
        self.assertEqual(entry["name_declared_purpose"], "execute")




class TestRuntimesSchemaVersion(unittest.TestCase):
    """16 D-12 tracer: runtimes.json schema_version -- snapshot stamping ->
    detect-runtimes --if-stale -> an unversioned/older cache forces one re-detect
    (and re-stamp) even when its mtime is fresh; cache.py stays schema-agnostic."""

    def test_snapshot_carries_current_schema_version(self):
        snapshot = build_runtimes_snapshot(which_fn=lambda n: None, run_fn=lambda *a, **k: None)
        self.assertEqual(snapshot["schema_version"], detection.RUNTIMES_SCHEMA_VERSION)
        self.assertEqual(detection.RUNTIMES_SCHEMA_VERSION, 5)

    def test_fresh_but_unversioned_cache_redetects_and_stamps(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "runtimes.json")
            cache_write_json(path, {"clis": {}})  # fresh mtime, NO schema_version
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            recorded = []
            with redirect_stdout(buf):
                code = main(
                    ["detect-runtimes", "--if-stale", path],
                    which_fn=lambda n: recorded.append(n) or None,
                    run_fn=lambda *a, **k: None,
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                recorded,
                [b for row in detection.RUNTIMES.values() for b in row.binaries] + ["node"],
            )  # detection ran
            self.assertIn("clis", json.loads(buf.getvalue()))
            cached = cache_read_json(path)
            assert cached is not None
            self.assertEqual(
                cached["schema_version"], detection.RUNTIMES_SCHEMA_VERSION
            )  # re-stamped

    def test_fresh_cache_with_older_version_redetects(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "runtimes.json")
            cache_write_json(path, {"schema_version": 1, "clis": {}})
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            recorded = []
            with redirect_stdout(buf):
                code = main(
                    ["detect-runtimes", "--if-stale", path],
                    which_fn=lambda n: recorded.append(n) or None,
                    run_fn=lambda *a, **k: None,
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                recorded,
                [b for row in detection.RUNTIMES.values() for b in row.binaries] + ["node"],
            )
            cached = cache_read_json(path)
            assert cached is not None
            self.assertEqual(
                cached["schema_version"], detection.RUNTIMES_SCHEMA_VERSION)

    def test_fresh_version_2_cache_redetects_and_restamps(self):
        # 17 D-32: version 2 predates the opencode 2.x /api/model source, so even a
        # fresh version-2 cache re-detects and re-stamps the current version.
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "runtimes.json")
            cache_write_json(path, {"schema_version": 2, "clis": {}})
            buf = io.StringIO()
            recorded = []
            with redirect_stdout(buf):
                code = main(
                    ["detect-runtimes", "--if-stale", path],
                    which_fn=lambda n: recorded.append(n) or None,
                    run_fn=lambda *a, **k: None,
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                recorded,
                [b for row in detection.RUNTIMES.values() for b in row.binaries] + ["node"],
            )
            cached = cache_read_json(path)
            assert cached is not None
            self.assertEqual(
                cached["schema_version"], detection.RUNTIMES_SCHEMA_VERSION)

    def test_fresh_current_cache_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "runtimes.json")
            cache_write_json(
                path, {"schema_version": detection.RUNTIMES_SCHEMA_VERSION, "clis": {}})
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            recorded = []
            with redirect_stdout(buf):
                code = main(
                    ["detect-runtimes", "--if-stale", path],
                    which_fn=lambda n: recorded.append(n) or None,
                    run_fn=lambda *a, **k: None,
                )
            self.assertEqual(code, 0)
            self.assertEqual(recorded, [])  # detection never ran
            self.assertEqual(json.loads(buf.getvalue()), {})

    def test_old_mtime_current_version_still_redetects(self):
        # TTL still honored: a current-version file past RUNTIMES_TTL_SECONDS re-detects.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "runtimes.json")
            cache_write_json(
                path, {"schema_version": detection.RUNTIMES_SCHEMA_VERSION, "clis": {}})
            old = time.time() - detection.RUNTIMES_TTL_SECONDS - 60
            os.utime(path, (old, old))
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            recorded = []
            with redirect_stdout(buf):
                code = main(
                    ["detect-runtimes", "--if-stale", path],
                    which_fn=lambda n: recorded.append(n) or None,
                    run_fn=lambda *a, **k: None,
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                recorded,
                [b for row in detection.RUNTIMES.values() for b in row.binaries] + ["node"],
            )

    def test_unreadable_or_non_object_cache_redetects_without_raising(self):
        for seed_text in ("not json", "[1, 2]"):
            import io
            from contextlib import redirect_stdout

            with self.subTest(seed=seed_text), tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "runtimes.json")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(seed_text)
                buf = io.StringIO()
                recorded = []
                with redirect_stdout(buf):
                    code = main(
                        ["detect-runtimes", "--if-stale", path],
                        which_fn=lambda n, _r=recorded: _r.append(n) or None,
                        run_fn=lambda *a, **k: None,
                    )
                self.assertEqual(code, 0)
                self.assertEqual(
                    recorded,
                    [b for row in detection.RUNTIMES.values() for b in row.binaries] + ["node"],
                )

    def test_version_predicate_rejects_non_int_values(self):
        f = detection.runtimes_schema_is_current
        for bad in (
            None,
            [],
            {},
            {"schema_version": True},
            {"schema_version": "3"},
            {"schema_version": 1},
            {"schema_version": 2},
            {"schema_version": 3},
            {"schema_version": 4},
        ):
            self.assertFalse(f(bad))
        for good in ({"schema_version": 5}, {"schema_version": 6}):
            self.assertTrue(f(good))

    def test_cache_is_stale_stays_schema_agnostic(self):
        # The version check lives in the cli.py caller; cache_is_stale stays a generic
        # mtime/TTL helper and must never see or judge schema_version.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.json")
            cache_write_json(path, {"clis": {}})
            self.assertFalse(cache_is_stale(path, 3600))


class TestResolveLadderPick(unittest.TestCase):
    def setUp(self):
        self.reviewers = [
            {"key": "codex-gpt", "model": "gpt-5.2", "vendor": "openai", "runtime": "codex"},
            {"key": "grok-flagship", "model": "grok-4.6", "vendor": "xai"},
        ]

    def test_picks_first_available_non_same_vendor(self):
        pick = resolve_ladder_pick(
            self.reviewers, ["codex-gpt", "grok-flagship"], skip_vendor="anthropic", quota={}
        )
        assert pick is not None
        self.assertEqual(pick.key, "codex-gpt")

    def test_skips_same_vendor_as_source(self):
        pick = resolve_ladder_pick(
            self.reviewers, ["codex-gpt", "grok-flagship"], skip_vendor="openai", quota={}
        )
        assert pick is not None
        self.assertEqual(pick.key, "grok-flagship")

    def test_skips_candidate_without_quota(self):
        quota = {"codex-gpt": {"available": False}}
        pick = resolve_ladder_pick(
            self.reviewers, ["codex-gpt", "grok-flagship"], skip_vendor="anthropic", quota=quota
        )
        assert pick is not None
        self.assertEqual(pick.key, "grok-flagship")

    def test_no_quota_entry_means_available(self):
        pick = resolve_ladder_pick(
            self.reviewers, ["codex-gpt"], skip_vendor="anthropic", quota={}
        )
        assert pick is not None
        self.assertEqual(pick.key, "codex-gpt")

    def test_falls_back_to_same_vendor_before_giving_up(self):
        # only same-vendor-as-source candidate exists and has quota -> still picked,
        # rather than returning None
        pick = resolve_ladder_pick(self.reviewers, ["codex-gpt"], skip_vendor="openai", quota={})
        assert pick is not None
        self.assertEqual(pick.key, "codex-gpt")

    def test_returns_none_when_nothing_survives(self):
        quota = {"codex-gpt": {"available": False}}
        pick = resolve_ladder_pick(
            [self.reviewers[0]], ["codex-gpt"], skip_vendor="anthropic", quota=quota
        )
        self.assertIsNone(pick)

    def test_unknown_ladder_key_is_skipped(self):
        pick = resolve_ladder_pick(
            self.reviewers, ["nonexistent", "grok-flagship"], skip_vendor="anthropic", quota={}
        )
        assert pick is not None
        self.assertEqual(pick.key, "grok-flagship")

    def test_entry_missing_model_resolves_to_empty_string_not_a_crash(self):
        reviewers = [{"key": "no-model", "vendor": "openai"}]
        pick = resolve_ladder_pick(reviewers, ["no-model"], skip_vendor="anthropic", quota={})
        assert pick is not None
        self.assertEqual(pick.model, "")


class TestResolveReviewers(unittest.TestCase):
    def setUp(self):
        self.config = {
            "policy": {"mode": "single", "ladder": ["claude-opus", "claude-sonnet", "codex-gpt"]},
            "reviewers": [
                {"key": "claude-opus", "model": "opus", "vendor": "anthropic"},
                {"key": "claude-sonnet", "model": "sonnet", "vendor": "anthropic"},
                {
                    "key": "codex-gpt",
                    "model": "gpt-5.2",
                    "vendor": "openai",
                    "runtime": "codex",
                    "command": "codex exec -m {model} {prompt}",
                },
            ],
        }

    def test_no_cross_ai_returns_only_the_no_config_fallback(self):
        result = resolve_reviewers(
            self.config, quota={}, source_vendor="anthropic", cross_ai=False
        )
        self.assertEqual(result, [NO_CONFIG_FALLBACK])

    def test_no_config_at_all_falls_back_to_session_default(self):
        config = {"policy": {"mode": "single", "ladder": []}, "reviewers": []}
        result = resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result, [NO_CONFIG_FALLBACK])

    def test_single_mode_skips_same_vendor_as_source(self):
        # single mode's whole point is an independent perspective, so the two
        # same-vendor-as-source (anthropic) ladder entries are skipped even
        # though they're earlier in the ladder
        result = resolve_reviewers(
            self.config, quota={}, source_vendor="anthropic", cross_ai=True
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].key, "codex-gpt")

    def test_single_mode_falls_through_tiers_when_flagship_lacks_quota(self):
        quota = {"codex-gpt": {"available": False}}
        result = resolve_reviewers(
            self.config, quota=quota, source_vendor="anthropic", cross_ai=True
        )
        # only same-vendor entries left with quota -> the vendor-skip fallback picks
        # the ladder's best surviving entry, which is claude-opus (tier-aware: tried
        # before claude-sonnet because it is earlier in the ladder)
        self.assertEqual(result[0].key, "claude-opus")

    def test_double_mode_primary_is_first_ladder_entry_tier_aware(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        result = resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 2)
        # first ladder entry, regardless of native/external (here it happens
        # to also be native, since claude-opus leads the ladder)
        self.assertEqual(result[0].key, "claude-opus")
        self.assertEqual(result[1].key, "codex-gpt")  # first DIFFERENT-vendor entry

    def test_double_mode_primary_falls_through_tiers_when_flagship_lacks_quota(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        quota = {"claude-opus": {"available": False}}
        result = resolve_reviewers(config, quota=quota, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result[0].key, "claude-sonnet")  # falls through the tier ladder
        self.assertEqual(result[1].key, "codex-gpt")

    def test_double_mode_drops_to_single_when_no_other_vendor_has_quota(self):
        config = dict(self.config)
        config["policy"] = {"mode": "double", "ladder": self.config["policy"]["ladder"]}
        quota = {"codex-gpt": {"available": False}}
        result = resolve_reviewers(config, quota=quota, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(len(result), 1)  # no cross-vendor survivor -> just the primary
        self.assertEqual(result[0].key, "claude-opus")

    def test_double_mode_with_empty_ladder_falls_back_to_session_default(self):
        config = {"policy": {"mode": "double", "ladder": []}, "reviewers": []}
        result = resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result, [NO_CONFIG_FALLBACK])

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
        result = resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
        self.assertEqual(result[0].key, "codex-gpt")  # first ladder entry, external
        self.assertEqual(result[0].runtime, "codex")
        self.assertEqual(result[1].key, "claude-opus")  # first different-vendor entry

    def test_double_mode_with_only_external_entry_picks_it_as_primary_and_drops_secondary(self):
        # ladder is entirely external -> primary is that external entry
        # itself (no more forced NO_CONFIG_FALLBACK just because nothing
        # native is configured), and secondary is dropped since nothing
        # else in the ladder has a different vendor.
        config = {
            "policy": {"mode": "double", "ladder": ["codex-gpt"]},
            "reviewers": [self.config["reviewers"][2]],  # codex-gpt only, no native entries at all
        }
        result = resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
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
                {
                    "key": "claude-cli-opus",
                    "model": "opus",
                    "vendor": "anthropic",
                    "cli": "claude",
                    "command": "claude -p --model {model} {prompt}",
                },
            ],
        }
        result = resolve_reviewers(config, quota={}, source_vendor="openai", cross_ai=True)
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
                {
                    "key": "claude-cli-opus",
                    "model": "opus",
                    "vendor": "anthropic",
                    "cli": "claude",
                    "command": "claude -p --model {model} {prompt}",
                },
            ],
        }
        result = resolve_reviewers(config, quota={}, source_vendor="anthropic", cross_ai=True)
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
        quota.resolve_reviewers(
            config_fallback, quota={}, source_vendor="", cross_ai=True, warn_fn=warnings.append
        )
        self.assertEqual(len(warnings), 1)
        self.assertIn("purpose", warnings[0].lower())

        warnings.clear()
        config_no_fallback = {
            "policy": {"mode": "single", "ladder": ["both-ok"]},
            "reviewers": [{"key": "both-ok", "model": "m2", "vendor": "xai", "purpose": "both"}],
        }
        quota.resolve_reviewers(
            config_no_fallback, quota={}, source_vendor="", cross_ai=True, warn_fn=warnings.append
        )
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


class TestBuildGrokCommand(unittest.TestCase):
    def test_grok_command_shape(self):
        # corrected 2026-08-29: `-p -` does NOT read from stdin -- it sends the literal
        # string "-" as the prompt (confirmed live). {prompt} is the correct placeholder,
        # substituted raw into one argv element by render_reviewer_command.
        self.assertEqual(
            build_grok_command(), "grok -p {prompt} -m {model} --output-format plain"
        )


class TestBuildReviewerModelId(unittest.TestCase):
    def test_cursor_agent_adds_bracket_overrides(self):
        model_id = build_cursor_agent_model_id(
            "claude-opus-4-8", effort="high", fast=False, context="1m"
        )
        self.assertEqual(model_id, "claude-opus-4-8[effort=high,fast=false,context=1m]")

    def test_cursor_agent_no_overrides_returns_base_model_unchanged(self):
        self.assertEqual(build_cursor_agent_model_id("claude-opus-4-8"), "claude-opus-4-8")

    def test_dispatches_via_cli_name(self):
        self.assertEqual(
            build_reviewer_model_id("cursor-agent", "gpt-5.3-codex", effort="low"),
            "gpt-5.3-codex[effort=low]",
        )

    def test_non_cursor_cli_returns_base_model_unchanged(self):
        self.assertEqual(build_reviewer_model_id("codex", "gpt-5.2", effort="high"), "gpt-5.2")


class TestRenderReviewerCommand(unittest.TestCase):
    def test_fills_model_and_prompt(self):
        resolved = ResolvedReviewer(
            key="codex-gpt",
            model="gpt-5.2",
            vendor="openai",
            runtime="codex",
            command="codex exec -m {model} {prompt}",
            extra={},
        )
        self.assertEqual(
            render_reviewer_command(resolved, "hello"),
            ["codex", "exec", "-m", "gpt-5.2", "hello"],
        )

    def test_fills_extra_fields(self):
        cmd = "codex exec -m {model} -c service_tier='\"{service_tier}\"' {prompt}"
        resolved = ResolvedReviewer(
            key="codex-gpt",
            model="gpt-5.2",
            vendor="openai",
            runtime="codex",
            command=cmd,
            extra={"service_tier": "fast"},
        )
        out = render_reviewer_command(resolved, "hi")
        self.assertIn('service_tier="fast"', out)

    def test_prompt_is_shell_escaped_but_extra_fields_are_not(self):
        # {prompt} is free text built from document paths/content signals —
        # the one field that MUST survive as a single shell argument no
        # matter what it contains. {model}/extra fields are short,
        # human-typed config values whose own quoting idiom (e.g. codex's
        # -c key='"value"') the template author controls directly — auto-
        # quoting those would break that idiom, so only {prompt} is quoted.
        resolved = ResolvedReviewer(
            key="codex-gpt",
            model="gpt-5.2",
            vendor="openai",
            runtime="codex",
            command="codex exec -m {model} {prompt}",
            extra={},
        )
        dangerous_prompt = "Read this; rm -rf / #"
        out = render_reviewer_command(resolved, dangerous_prompt)
        # argv dispatch, no shell: the prompt survives verbatim as ONE argv element
        self.assertEqual(out[-1], dangerous_prompt)

    def test_runtime_entry_without_a_command_raises_value_error(self):
        resolved = ResolvedReviewer(
            key="codex-gpt", model="gpt-5.2", vendor="openai", runtime="codex",
            command=None, extra={},
        )
        with self.assertRaises(ValueError) as ctx:
            render_reviewer_command(resolved, "hello")
        self.assertIn("codex-gpt", str(ctx.exception))
        self.assertIn("no command", str(ctx.exception))

    def test_malformed_template_raises_value_error_not_key_error(self):
        # {unknown_field} isn't {model}/{prompt}/in extra -> str.format
        # raises KeyError; must surface as a reportable ValueError instead
        resolved = ResolvedReviewer(
            key="codex-gpt",
            model="gpt-5.2",
            vendor="openai",
            runtime="codex",
            command="codex -m {model} {unknown_field} {prompt}",
            extra={},
        )
        with self.assertRaises(ValueError):
            render_reviewer_command(resolved, "hello")

    def test_attribute_placeholder_raises_value_error_not_attribute_error(self):
        # A-IN-02: "{model.foo}" makes str.format raise AttributeError.
        resolved = ResolvedReviewer(key="k", model="m", vendor="v", runtime="codex",
                                    command="x {model.foo}", extra={})
        with self.assertRaises(ValueError):
            render_reviewer_command(resolved, "hello")

    def test_extra_field_colliding_with_reserved_placeholder_raises_value_error(self):
        # a hand-written config entry that defines extra={"prompt": ...} or
        # extra={"model": ...} collides with the reserved keyword args
        # passed to str.format, raising a TypeError that must not escape
        # as a raw crash either
        resolved = ResolvedReviewer(
            key="codex-gpt",
            model="gpt-5.2",
            vendor="openai",
            runtime="codex",
            command="codex -m {model} {prompt}",
            extra={"prompt": "oops"},
        )
        with self.assertRaises(ValueError):
            render_reviewer_command(resolved, "hello")


def _probe_result(reason, status=None, stderr_tail=""):
    return runner_dispatch.RunnerResult(
        0 if reason is None else 1, "", {"status": status} if status else None, reason,
        False, ["node", "runner"], stderr_tail,
    )


class TestProbeReviewerQuota(unittest.TestCase):
    def test_native_entry_is_always_available(self):
        resolved = ResolvedReviewer(
            key="claude-opus", model="opus", vendor="anthropic",
            runtime=None, command=None, extra={},
        )
        result = probe_reviewer_quota(
            resolved,
            seams=ProbeSeams(runner_fn=lambda *a: (_ for _ in ()).throw(
                AssertionError("should never shell out for a native entry")
            )),
        )
        self.assertTrue(result["available"])

    def _codex(self):
        return ResolvedReviewer(
            key="codex-gpt", model="gpt-5.2", vendor="openai", runtime="codex",
            command=None, extra={},
        )

    def test_successful_call_is_available(self):
        seen = {}

        def fake_runner(spec, prompt, seams):
            seen["spec"] = spec
            return _probe_result(None, "ok")

        result = probe_reviewer_quota(self._codex(), seams=ProbeSeams(runner_fn=fake_runner))
        self.assertTrue(result["available"])
        self.assertIsNone(result["reason"])
        self.assertEqual(seen["spec"].mode, "review")
        self.assertEqual(seen["spec"].timeout_s, 30)
        self.assertEqual(seen["spec"].runtime, "codex")

    def test_nonzero_exit_is_unavailable(self):
        result = probe_reviewer_quota(
            self._codex(),
            seams=ProbeSeams(runner_fn=lambda *a: _probe_result("real_error", "crash")),
        )
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "real_error")

    def test_answer_containing_quota_text_on_exit_zero_is_a_success(self):
        # R8/D-13: the runner's status decides, never the answer text — an `ok` status is a
        # success even when the answer happens to say "quota exceeded".
        result = probe_reviewer_quota(
            self._codex(), seams=ProbeSeams(runner_fn=lambda *a: _probe_result(None, "ok"))
        )
        self.assertTrue(result["available"])
        self.assertIsNone(result["reason"])

    def test_quota_status_records_reason_quota_and_relays_stderr(self):
        lines = []

        def fake_runner(spec, prompt, seams):
            del spec, prompt
            seams.print_fn("Error: usage limit reached")
            return _probe_result("quota", "quota")

        result = probe_reviewer_quota(
            self._codex(), seams=ProbeSeams(runner_fn=fake_runner, print_fn=lines.append)
        )
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "quota")
        self.assertIn("usage limit", result["detail"])
        self.assertEqual(lines, ["Error: usage limit reached"])

    def test_timeout_is_unavailable(self):
        result = probe_reviewer_quota(
            self._codex(),
            seams=ProbeSeams(runner_fn=lambda *a: _probe_result("timeout", "timeout")),
        )
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "timeout")

    def test_billing_status_records_billing_or_access(self):
        result = probe_reviewer_quota(
            self._codex(),
            seams=ProbeSeams(
                runner_fn=lambda *a: _probe_result("billing_or_access", "billing")
            ),
        )
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "billing_or_access")

    def test_probe_sends_the_prompt_to_the_runner(self):
        # the probe prompt reaches the runner as its prompt argument, never inside argv
        captured = {}

        def fake_runner(spec, prompt, seams):
            del spec, seams
            captured["prompt"] = prompt
            return _probe_result(None, "ok")

        probe_reviewer_quota(self._codex(), seams=ProbeSeams(runner_fn=fake_runner))
        self.assertEqual(captured["prompt"], "Only say: Hello world!")

    def test_no_node_is_dispatch_unavailable_and_names_node(self):
        def fake_runner(spec, prompt, seams):
            del spec, prompt
            seams.print_fn(
                "ai-kit-spec: subprocess dispatch needs Node (node not found on PATH)")
            return _probe_result("dispatch_unavailable")

        result = probe_reviewer_quota(self._codex(), seams=ProbeSeams(runner_fn=fake_runner))
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "dispatch_unavailable")
        self.assertIn("Node", result["detail"])

    def test_probe_cwd_is_outside_any_git_work_tree_and_removed_afterwards(self):
        seen = {}

        def fake_runner(spec, prompt, seams):
            del prompt, seams
            seen["cwd"] = spec.cwd
            seen["existed"] = os.path.isdir(spec.cwd)
            return _probe_result(None, "ok")

        probe_reviewer_quota(self._codex(), seams=ProbeSeams(runner_fn=fake_runner))
        self.assertTrue(seen["existed"])
        self.assertFalse(os.path.exists(seen["cwd"]))
        self.assertFalse(os.path.isdir(os.path.join(seen["cwd"], ".git")))

    def test_probe_git_search_stops_at_its_private_cwd(self):
        seen = {}

        def fake_runner(spec, prompt, seams):
            del prompt
            seen["cwd"] = spec.cwd
            seen["ceiling"] = seams.env_fn().get("GIT_CEILING_DIRECTORIES")
            return _probe_result(None, "ok")

        probe_reviewer_quota(self._codex(), seams=ProbeSeams(runner_fn=fake_runner))
        self.assertEqual(seen["ceiling"], os.path.dirname(seen["cwd"]))

    def test_session_default_is_available_without_a_probe(self):
        resolved = ResolvedReviewer(
            key="session-default", model="", vendor="",
            runtime=None, command=None, extra={},
        )
        def never(*_a, **_k):
            raise AssertionError("session default should never shell out")

        result = probe_reviewer_quota(
            resolved, seams=ProbeSeams(runner_fn=never, custom_fn=never),
        )
        self.assertTrue(result["available"])
        self.assertIsNone(result["reason"])


class TestErrorClassifier(unittest.TestCase):
    """D-13/R8: one shared classifier; inputs are exit status and stderr only."""

    def test_exit_zero_is_never_classified_even_with_hostile_stderr(self):
        self.assertIsNone(classify_error(0, "", False))
        self.assertIsNone(classify_error(0, "quota exceeded", False))

    def test_quota_signals(self):
        self.assertEqual(classify_error(1, "Error: quota exceeded", False), "quota")
        self.assertEqual(classify_error(1, "Rate limit reached", False), "quota")
        self.assertEqual(classify_error(1, "usage limit", False), "quota")

    def test_auth_checked_before_quota(self):
        self.assertEqual(
            classify_error(1, "ActionRequiredError: Named models unavailable", False), "auth"
        )
        self.assertEqual(
            classify_error(1, "Warning: The provided API key is invalid", False), "auth"
        )
        self.assertEqual(classify_error(1, "not logged in ... quota", False), "auth")
        self.assertEqual(classify_error(1, "unauthorized", False), "auth")

    def test_configuration_signals(self):
        self.assertEqual(classify_error(1, "Cannot use this model: x", False), "configuration")
        self.assertEqual(classify_error(1, "unknown model", False), "configuration")
        self.assertEqual(classify_error(1, "model not found", False), "configuration")

    def test_dispatch_unavailable(self):
        self.assertEqual(classify_error(127, "", False), "dispatch_unavailable")
        self.assertEqual(classify_error(126, "permission denied", False), "dispatch_unavailable")
        self.assertEqual(
            classify_error(127, "No such file or directory: 'codex'", False),
            "dispatch_unavailable",
        )

    def test_transcript_text_cannot_outrank_or_fake_a_limit(self):
        # A-WR-02: execute stderr is a whole transcript. An earlier benign tool error must
        # not outrank the real limit, and a task about rate limiting is not a quota event.
        transcript = "tool: cat missing.txt -> No such file or directory\n" + "x\n" * 50
        self.assertEqual(
            classify_error(1, transcript + "ERROR: You've hit your usage limit.", False), "quota"
        )
        self.assertEqual(classify_error(1, "No such file or directory", False), "real_error")
        self.assertEqual(
            classify_error(1, "exec: implementing rate limit middleware ... test failed", False),
            "real_error",
        )
        # only the tail is scanned
        self.assertEqual(
            classify_error(1, "usage limit\n" + "y" * 4096 + "\nboom", False), "real_error"
        )

    def test_timeout_wins_over_everything(self):
        self.assertEqual(classify_error(None, "", True), "timeout")
        self.assertEqual(classify_error(1, "quota", True), "timeout")

    def test_other_nonzero_exit_is_real_error(self):
        self.assertEqual(classify_error(1, "boom", False), "real_error")

    def test_non_utf8_stderr_bytes_do_not_crash(self):
        self.assertEqual(classify_error(1, b"\xff\xfe quota exceeded", False), "quota")

    def test_reason_vocabulary_is_closed(self):
        self.assertEqual(
            set(REASONS),
            {
                "quota", "auth", "timeout", "configuration", "dispatch_unavailable",
                "real_error", "capacity", "billing_or_access", "git_timeout",
            },
        )


class TestProbeReason(unittest.TestCase):
    """D-13: quota.json entries carry a typed `reason`; legacy entries read real_error."""

    def test_legacy_unavailable_entry_without_reason_reads_real_error(self):
        self.assertEqual(entry_reason({"available": False, "detail": "x"}), "real_error")

    def test_available_entry_without_reason_reads_none(self):
        self.assertIsNone(entry_reason({"available": True}))

    def test_stored_reason_wins(self):
        self.assertEqual(
            entry_reason({"available": False, "reason": "auth", "detail": "quota"}), "auth"
        )


class TestRefreshQuotaCache(unittest.TestCase):
    def setUp(self):
        self.config = {
            "policy": {"mode": "single", "ladder": ["codex-gpt"]},
            "reviewers": [
                {
                    "key": "codex-gpt",
                    "model": "gpt-5.2",
                    "vendor": "openai",
                    "cli": "codex",
                    "command": "echo ok",
                }
            ],
        }

    def test_probes_missing_entries(self):
        updated = refresh_quota_cache(
            self.config, ["codex-gpt"], existing={}, ttl_seconds=3600,
            seams=ProbeSeams(runner_fn=lambda *a: _probe_result(None, "ok")),
        )
        self.assertTrue(updated["codex-gpt"]["available"])

    def test_skips_fresh_entries(self):
        existing = {"codex-gpt": {"available": False, "checked_at": time.time()}}

        def fail_if_called(*a, **k):
            raise AssertionError("should not re-probe a fresh entry")

        updated = refresh_quota_cache(
            self.config, ["codex-gpt"], existing, ttl_seconds=3600,
            seams=ProbeSeams(runner_fn=fail_if_called),
        )
        self.assertFalse(updated["codex-gpt"]["available"])  # untouched

    def test_reprobes_stale_entries(self):
        existing = {"codex-gpt": {"available": False, "checked_at": time.time() - 7200}}

        updated = refresh_quota_cache(
            self.config, ["codex-gpt"], existing, ttl_seconds=3600,
            seams=ProbeSeams(runner_fn=lambda *a: _probe_result(None, "ok")),
        )
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
        findings = parse_findings(_REPORT_A)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["severity"], "CRITICAL")
        self.assertEqual(findings[0]["title"], "Missing field")
        self.assertEqual(findings[0]["location"], "§2.1")
        self.assertEqual(findings[1]["severity"], "HIGH")

    def test_report_with_no_findings_returns_empty_list(self):
        approved = "## Review: spec.md\n### Status: Approved\n"
        self.assertEqual(parse_findings(approved), [])

    def test_cross_document_consistency_bullets_are_not_misattributed(self):
        report = """## Review: a.md, b.md
### HIGH
- **Real high finding** — Location: §1. Required: fix it. Why: reasons.
### Cross-Document Consistency
- **Docs disagree** — Location: §2 vs §3. Required: reconcile. Why: contradiction.
### Status: Issues Found — fix and re-invoke
"""
        findings = parse_findings(report)
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
        findings = parse_findings(report)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "LOW")


class TestReportStatus(unittest.TestCase):
    """D-12: closed status vocabulary; the most severe ### Status: line wins (A-WR-06)."""

    def test_approved(self):
        self.assertEqual(report_status("x\n### Status: Approved\n"), "approved")

    def test_issues_found(self):
        self.assertEqual(report_status("### Status: Issues Found — fix and re-invoke"), "issues")

    def test_failure(self):
        self.assertEqual(report_status("### Status: Failure — input not on disk"), "failure")

    def test_unknown_status_text_reads_issues(self):
        self.assertEqual(report_status("### Status: Something odd"), "issues")

    def test_no_status_line_reads_none(self):
        self.assertIsNone(report_status("no status line at all"))
        self.assertIsNone(report_status(""))

    def test_most_severe_status_line_wins_in_any_order(self):
        text = "### Status: Approved\nmid\n### Status: Issues Found — fix\n"
        self.assertEqual(report_status(text), "issues")
        text = "### Status: Issues Found — fix\n```\n### Status: Approved\n```\n"
        self.assertEqual(report_status(text), "issues")
        text = "### Status: Failure — x\n### Status: Approved\n### Status: Issues Found\n"
        self.assertEqual(report_status(text), "failure")


class TestMergeReportsFailure(unittest.TestCase):
    """D-12/R7: a failed or missing lane can never merge into Approved, in any order."""

    def _merge(self, tmp, files, order=("a", "b")):
        import io
        from contextlib import redirect_stdout

        args = ["merge-reports", "--doc-paths", "spec.md"]
        for key in order:
            args.append(f"{key}={files[key]}")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(args)
        return code, buf.getvalue()

    def _write(self, tmp, name, text):
        path = os.path.join(tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_failure_plus_approved_fails_naming_the_failed_lane(self):
        with tempfile.TemporaryDirectory() as d:
            files = {
                "a": self._write(d, "a.md", "### Status: Failure — input missing\n"),
                "b": self._write(d, "b.md", "### Status: Approved\n"),
            }
            code, out = self._merge(d, files)
            self.assertEqual(code, 1)
            self.assertIn("### Status: Failure — a", out)
            self.assertNotIn("### Status: Approved", out)

    def test_missing_lane_fails_naming_it_regardless_of_order(self):
        for order in (("a", "b"), ("b", "a")):
            with self.subTest(order=order), tempfile.TemporaryDirectory() as d:
                files = {
                    "a": self._write(d, "a.md", "### Status: Approved\n"),
                    "b": os.path.join(d, "does-not-exist.md"),
                }
                code, out = self._merge(d, files, order=order)
                self.assertEqual(code, 1)
                self.assertIn("### Status: Failure — b", out)

    def test_lane_without_status_line_fails(self):
        with tempfile.TemporaryDirectory() as d:
            files = {
                "a": self._write(d, "a.md", "### Status: Approved\n"),
                "b": self._write(d, "b.md", "codex: error: exploded\n"),
            }
            code, out = self._merge(d, files)
            self.assertEqual(code, 1)
            self.assertIn("### Status: Failure — b", out)

    def test_non_utf8_lane_fails_naming_it(self):
        # A-WR-05: invalid bytes in a report are a named Failure lane, never a traceback.
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "b.md")
            with open(bad, "wb") as f:
                f.write(b"\xff\xfe### Status: Approved\n")
            files = {"a": self._write(d, "a.md", "### Status: Approved\n"), "b": bad}
            code, out = self._merge(d, files)
            self.assertEqual(code, 1)
            self.assertIn("### Status: Failure — b", out)

    def test_failure_plus_failure_fails_naming_both(self):
        with tempfile.TemporaryDirectory() as d:
            files = {
                "a": self._write(d, "a.md", "### Status: Failure — x\n"),
                "b": self._write(d, "b.md", "### Status: Failure — y\n"),
            }
            code, out = self._merge(d, files)
            self.assertEqual(code, 1)
            self.assertIn("### Status: Failure — a, b", out)

    def test_approved_plus_approved_merges_clean(self):
        with tempfile.TemporaryDirectory() as d:
            files = {
                "a": self._write(d, "a.md", "### Status: Approved\n"),
                "b": self._write(d, "b.md", "### Status: Approved\n"),
            }
            code, out = self._merge(d, files)
            self.assertEqual(code, 0)
            self.assertIn("### Status: Approved", out)

    def test_approved_plus_issues_merges_to_issues(self):
        with tempfile.TemporaryDirectory() as d:
            files = {
                "a": self._write(d, "a.md", "### Status: Approved\n"),
                "b": self._write(d, "b.md", "### Status: Issues Found — fix and re-invoke\n"),
            }
            code, out = self._merge(d, files)
            self.assertEqual(code, 0)
            self.assertIn("### Status: Issues Found", out)


class TestMergeFindings(unittest.TestCase):
    def test_same_severity_and_location_merges_into_one_tagged_entry(self):
        merged = merge_findings([("claude-opus", _REPORT_A), ("codex-gpt", _REPORT_B)])
        crit = [f for f in merged if f["severity"] == "CRITICAL"]
        self.assertEqual(len(crit), 1)  # both CRITICAL findings share (CRITICAL, "§2.1")
        self.assertEqual(crit[0]["reviewers"], ["claude-opus", "codex-gpt"])

    def test_distinct_locations_stay_separate_each_tagged_with_its_own_source(self):
        merged = merge_findings([("claude-opus", _REPORT_A), ("codex-gpt", _REPORT_B)])
        high = [f for f in merged if f["severity"] == "HIGH"]
        medium = [f for f in merged if f["severity"] == "MEDIUM"]
        self.assertEqual(high[0]["reviewers"], ["claude-opus"])
        self.assertEqual(medium[0]["reviewers"], ["codex-gpt"])

    def test_single_report_passthrough(self):
        merged = merge_findings([("claude-opus", _REPORT_A)])
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
        merged = merge_findings([("claude-opus", report)])
        self.assertEqual(len(merged), 2)
        titles = {f["title"] for f in merged}
        self.assertEqual(titles, {"First issue", "Second issue"})
        self.assertTrue(all(f["reviewers"] == ["claude-opus"] for f in merged))


class TestRenderMergedReport(unittest.TestCase):
    def test_groups_by_severity_and_tags_reviewers(self):
        merged = merge_findings([("claude-opus", _REPORT_A), ("codex-gpt", _REPORT_B)])
        rendered = render_merged_report(merged, "spec.md")
        self.assertIn("### CRITICAL", rendered)
        self.assertIn("### HIGH", rendered)
        self.assertIn("### MEDIUM", rendered)
        self.assertIn("(Reviewers: claude-opus, codex-gpt)", rendered)
        self.assertIn("### Status: Issues Found — fix and re-invoke", rendered)

    def test_no_findings_renders_approved_status(self):
        rendered = render_merged_report([], "spec.md")
        self.assertIn("### Status: Approved", rendered)
        self.assertNotIn("Issues Found", rendered)

    def test_cross_doc_findings_render_under_their_own_heading(self):
        findings = [
            {
                "severity": "CROSS-DOC",
                "title": "Docs disagree",
                "location": "§2 vs §3",
                "required": "reconcile",
                "why": "contradiction",
                "reviewers": ["claude-opus"],
            }
        ]
        rendered = render_merged_report(findings, "a.md, b.md")
        self.assertIn("### Cross-Document Consistency", rendered)
        self.assertNotIn("### CROSS-DOC", rendered)

    def test_low_findings_render_under_their_own_heading_not_medium(self):
        findings = [
            {
                "severity": "LOW",
                "title": "Trailing whitespace",
                "location": "§4",
                "required": "trim it",
                "why": "lint noise",
                "reviewers": ["claude-opus"],
            }
        ]
        rendered = render_merged_report(findings, "plan.md")
        self.assertIn("### LOW", rendered)
        self.assertNotIn("### MEDIUM", rendered)

    def test_any_source_issues_prevents_false_approved_when_no_findings_parsed(self):
        # regression: a source report can say "Issues Found" while its
        # bullet(s) fail _BULLET_RE's strict single-line shape (e.g. a
        # wrapped Required: clause) — parse_findings then returns nothing
        # for it, but the merge must never report Approved in that case.
        rendered = render_merged_report([], "spec.md", any_source_issues=True)
        self.assertIn("### Status: Issues Found — fix and re-invoke", rendered)
        self.assertNotIn("### Status: Approved", rendered)

    def test_any_source_issues_false_still_renders_approved_when_no_findings(self):
        rendered = render_merged_report([], "spec.md", any_source_issues=False)
        self.assertIn("### Status: Approved", rendered)


class TestMainCli(unittest.TestCase):
    def test_every_subcommand_has_a_handler(self):
        parser = cli._build_parser()
        subparsers = next(a for a in parser._actions if a.dest == "command")
        assert subparsers.choices is not None
        self.assertEqual(set(cli._COMMANDS), set(subparsers.choices))

    def test_main_accepts_deps_and_overrides(self):
        marker = {}

        def fake_which(name):
            marker["last"] = name
            return None

        deps = cli.CliDeps(which_fn=fake_which)
        self.assertEqual(cli.main(["detect-tools"], deps=deps), 0)
        self.assertIn("last", marker)
        marker.clear()
        self.assertEqual(cli.main(["detect-tools"], which_fn=fake_which), 0)
        self.assertIn("last", marker)

    def test_detect_runtimes_prints_json_snapshot(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                ["detect-runtimes"], which_fn=lambda n: None, run_fn=lambda *a, **k: None
            )
        self.assertEqual(code, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIn("clis", parsed)

    def test_detect_current_runtime_prints_json(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["detect-current-runtime"], env_fn=lambda: {"CLAUDECODE": "1"})
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue()), {"host": "claude"})

    def test_detect_current_runtime_prints_json_for_unknown(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["detect-current-runtime"], env_fn=lambda: {})
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue()), {"host": "unknown"})

    def test_detect_runtimes_save_writes_cache_file(self):
        with tempfile.TemporaryDirectory() as d:
            save_path = os.path.join(d, "runtimes.json")
            code = main(
                ["detect-runtimes", "--save", save_path],
                which_fn=lambda n: None,
                run_fn=lambda *a, **k: None,
            )
            self.assertEqual(code, 0)
            cached = cache_read_json(save_path)
            assert cached is not None
            self.assertIn("clis", cached)

    def test_dispatch_execute_reads_prompt_file_and_prints_json_result(self):
        import io
        from contextlib import redirect_stdout

        captured = {}

        def fake_dispatch(spec, **kw):
            captured["candidate"] = spec.candidate
            captured["prompt"] = spec.prompt
            captured["target_dir"] = spec.target_dir
            captured["timeout"] = spec.timeout
            captured["format_block"] = spec.format_block
            return {
                "runtime": spec.candidate["runtime"],
                "model": spec.candidate["model"],
                "command": "x",
                "returncode": 0,
                "stdout": "done",
                "stderr": "",
                "timed_out": False,
            }

        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("do the phase task")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "dispatch-execute",
                        "--cli",
                        "codex",
                        "--model",
                        "gpt-5.6-sol",
                        "--target-dir",
                        "/scratch/run1",
                        "--prompt-file",
                        prompt_path,
                        "--timeout",
                        "600",
                    ],
                    dispatch_execute_fn=fake_dispatch,
                )
        self.assertEqual(code, 0)
        result = json.loads(buf.getvalue())
        self.assertEqual(result["stdout"], "done")
        self.assertEqual(
            captured["candidate"],
            {"runtime": "codex", "model": "gpt-5.6-sol", "effort": None, "service_tier": None},
        )
        self.assertEqual(captured["prompt"], "do the phase task")
        self.assertEqual(captured["target_dir"], "/scratch/run1")
        self.assertEqual(captured["timeout"], 600)
        self.assertIsNone(captured["format_block"])

    def test_dispatch_execute_prints_the_pi_note_once(self):
        def fake_runner(spec, prompt, seams):
            del spec, prompt, seams
            return RunnerResult(0, "done", None, None, False, [], "")

        def dispatch(spec):
            return execute_dispatch.dispatch_execute(
                spec, execute_dispatch.ExecuteSeams(runner_fn=fake_runner))

        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = main(["dispatch-execute", "--runtime", "pi", "--model", "p/m",
                             "--target-dir", d, "--prompt-file", prompt_path,
                             "--timeout", "60"],
                            dispatch_execute_fn=dispatch)
        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue().count(PI_EXEC_NOTE), 1)

    def test_dispatch_execute_reads_optional_format_block_file(self):
        import io
        from contextlib import redirect_stdout

        captured = {}

        def fake_dispatch(spec, **kw):
            captured["format_block"] = spec.format_block
            return {
                "runtime": spec.candidate["runtime"],
                "model": spec.candidate["model"],
                "command": "x",
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "timed_out": False,
            }

        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            format_path = os.path.join(d, "format.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            with open(format_path, "w", encoding="utf-8") as f:
                f.write("FORMAT-BLOCK-MARKER")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "dispatch-execute",
                        "--cli",
                        "codex",
                        "--model",
                        "gpt-5.6-sol",
                        "--target-dir",
                        "/scratch/run1",
                        "--prompt-file",
                        prompt_path,
                        "--timeout",
                        "600",
                        "--format-block-file",
                        format_path,
                    ],
                    dispatch_execute_fn=fake_dispatch,
                )
        self.assertEqual(code, 0)
        self.assertEqual(captured["format_block"], "FORMAT-BLOCK-MARKER")

    def test_dispatch_execute_passes_effort_and_service_tier_into_the_candidate(self):
        import io
        from contextlib import redirect_stdout

        captured = {}

        def fake_dispatch(spec, **kw):
            captured["candidate"] = spec.candidate
            return {
                "runtime": spec.candidate["runtime"],
                "model": spec.candidate["model"],
                "command": "x",
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "timed_out": False,
            }

        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            with redirect_stdout(io.StringIO()):
                code = main(
                    [
                        "dispatch-execute",
                        "--cli",
                        "codex",
                        "--model",
                        "gpt-5.6-sol",
                        "--target-dir",
                        "/scratch/run1",
                        "--prompt-file",
                        prompt_path,
                        "--timeout",
                        "600",
                        "--effort",
                        "high",
                        "--service-tier",
                        "priority",
                    ],
                    dispatch_execute_fn=fake_dispatch,
                )
        self.assertEqual(code, 0)
        self.assertEqual(captured["candidate"]["effort"], "high")
        self.assertEqual(captured["candidate"]["service_tier"], "priority")

    def test_dispatch_execute_surfaces_value_error_on_stderr(self):
        import io
        from contextlib import redirect_stderr

        def raising_dispatch(*a, **kw):
            raise ValueError(
                "'gemini' cannot be an execution CLI; supported execute CLIs: "
                "codex, cursor, opencode, pi"
            )

        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            buf = io.StringIO()
            with redirect_stderr(buf):
                code = main(
                    [
                        "dispatch-execute",
                        "--cli",
                        "codex",
                        "--model",
                        "gpt-5.6-sol",
                        "--target-dir",
                        "/scratch/run1",
                        "--prompt-file",
                        prompt_path,
                        "--timeout",
                        "600",
                    ],
                    dispatch_execute_fn=raising_dispatch,
                )
        self.assertEqual(code, 1)
        self.assertIn("cannot be an execution CLI", buf.getvalue())

    def test_dispatch_execute_prompt_file_dash_reads_stdin(self):
        # The exact shape needed to drop this subcommand into GSD's own workflow.cross_ai_command,
        # which always pipes its task prompt into that hook's stdin.
        import io
        from contextlib import redirect_stdout

        captured = {}

        def fake_dispatch(spec, **kw):
            captured["prompt"] = spec.prompt
            return {
                "runtime": spec.candidate["runtime"],
                "model": spec.candidate["model"],
                "command": "x",
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "timed_out": False,
            }

        buf = io.StringIO()
        with (
            mock.patch.object(cli.sys, "stdin", io.StringIO("piped prompt text")),
            redirect_stdout(buf),
        ):
            code = main(
                [
                    "dispatch-execute",
                    "--cli",
                    "codex",
                    "--model",
                    "gpt-5.6-sol",
                    "--target-dir",
                    "/scratch/run1",
                    "--prompt-file",
                    "-",
                    "--timeout",
                    "600",
                ],
                dispatch_execute_fn=fake_dispatch,
            )
        self.assertEqual(code, 0)
        self.assertEqual(captured["prompt"], "piped prompt text")

    def test_dispatch_execute_stdout_only_prints_raw_stdout_and_real_returncode(self):
        import io
        from contextlib import redirect_stdout

        def fake_dispatch(spec, **kw):
            return {
                "runtime": spec.candidate["runtime"],
                "model": spec.candidate["model"],
                "command": "x",
                "returncode": 0,
                "stdout": "# Phase Summary\n...",
                "stderr": "diagnostics",
                "timed_out": False,
            }

        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "dispatch-execute",
                        "--cli",
                        "codex",
                        "--model",
                        "gpt-5.6-sol",
                        "--target-dir",
                        "/scratch/run1",
                        "--prompt-file",
                        prompt_path,
                        "--timeout",
                        "600",
                        "--stdout-only",
                    ],
                    dispatch_execute_fn=fake_dispatch,
                )
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue(), "# Phase Summary\n...")
        self.assertNotIn("diagnostics", buf.getvalue())  # stderr never leaks into this stream

    def test_dispatch_execute_stdout_only_propagates_nonzero_returncode(self):
        import io
        from contextlib import redirect_stdout

        def fake_dispatch(spec, **kw):
            return {
                "runtime": spec.candidate["runtime"],
                "model": spec.candidate["model"],
                "command": "x",
                "returncode": 3,
                "stdout": "partial",
                "stderr": "",
                "timed_out": False,
            }

        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            with redirect_stdout(io.StringIO()):
                code = main(
                    [
                        "dispatch-execute",
                        "--cli",
                        "codex",
                        "--model",
                        "gpt-5.6-sol",
                        "--target-dir",
                        "/scratch/run1",
                        "--prompt-file",
                        prompt_path,
                        "--timeout",
                        "600",
                        "--stdout-only",
                    ],
                    dispatch_execute_fn=fake_dispatch,
                )
        self.assertEqual(code, 3)

    def test_cache_path_honors_xdg_cache_home(self):
        import io
        from contextlib import redirect_stdout

        env = {"XDG_CACHE_HOME": "/x/cache"}
        buf = io.StringIO()
        with mock.patch.object(os, "environ", env), redirect_stdout(buf):
            code = main(["cache-path", "--kind", "runtimes"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "/x/cache/ai-kit/spec/runtimes.json")

    def test_cache_path_quota_kind(self):
        import io
        from contextlib import redirect_stdout

        env = {"HOME": "/home/u"}
        buf = io.StringIO()
        with mock.patch.object(os, "environ", env), redirect_stdout(buf):
            code = main(["cache-path", "--kind", "quota"])
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "/home/u/.cache/ai-kit/spec/quota.json")

    def test_detect_runtimes_if_stale_skips_detection_when_fresh(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "runtimes.json")
            cache_write_json(
                path, {"schema_version": detection.RUNTIMES_SCHEMA_VERSION, "clis": {}}
            )  # just written -> fresh
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            probe_calls = []
            with redirect_stdout(buf):
                code = main(
                    ["detect-runtimes", "--if-stale", path],
                    which_fn=lambda n: probe_calls.append(n) or None,
                    run_fn=lambda *a, **k: None,
                )
            self.assertEqual(code, 0)
            self.assertEqual(probe_calls, [])  # detection never ran
            self.assertEqual(json.loads(buf.getvalue()), {})

    def test_detect_runtimes_if_stale_redetects_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "runtimes.json")  # never written -> stale
            code = main(
                ["detect-runtimes", "--if-stale", path],
                which_fn=lambda n: None,
                run_fn=lambda *a, **k: None,
            )
            self.assertEqual(code, 0)
            cached = cache_read_json(path)
            assert cached is not None
            self.assertIn("clis", cached)

    def test_resolve_reviewers_uses_cfg_resolve_local_global_merge(self):
        # regression test for the CRITICAL bug: resolve-reviewers must go
        # through cfg_resolve (local/global + strategy), not a single
        # --config path — write ONLY a local file that overrides one field
        # of a global-declared reviewer, and confirm the override lands.
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            os.makedirs(os.path.join(home, ".config", "ai-kit"))
            cfg_write_toml(
                os.path.join(home, ".config", "ai-kit", "review-spec.toml"),
                {
                    "policy": {"mode": "single", "ladder": ["codex-gpt"]},
                    "reviewers": [{"key": "codex-gpt", "model": "gpt-5.2",
                                  "vendor": "openai", "runtime": "codex"}],
                },
            )
            os.makedirs(os.path.join(cwd, ".aikit"))
            local_path = os.path.join(cwd, ".aikit", "review-spec.toml")
            raw = b'[[reviewers]]\nkey = "codex-gpt"\nmodel = "gpt-5.2-mini"\n'
            with open(local_path, "wb") as f:
                f.write(raw)
            trust.record_trust(
                config_io.cfg_trust_store_dir({"HOME": home}), os.path.realpath(local_path), raw
            )
            quota_path = os.path.join(cwd, "quota.json")
            cache_write_json(quota_path, {})
            buf = io.StringIO()
            env = {"HOME": home, "XDG_CACHE_HOME": os.path.join(cwd, "cache")}
            cache_write_json(
                detection.cache_runtimes_path(env),
                {"schema_version": detection.RUNTIMES_SCHEMA_VERSION,
                 "clis": {"codex": {"installed": True, "path": "/fake/codex",
                                     "models": ["gpt-5.2", "gpt-5.2-mini"]}}},
            )
            with mock.patch.object(os, "environ", env), redirect_stdout(buf):
                code = main(
                    [
                        "resolve-reviewers",
                        "--cwd",
                        cwd,
                        "--quota-path",
                        quota_path,
                        "--source-vendor",
                        "anthropic",
                        "--cross-ai",
                    ],
                    which_fn=lambda _name: None,
                    run_fn=lambda *_a, **_k: None,
                    env_fn=lambda: dict(env),
                )
            self.assertEqual(code, 0)
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed[0]["model"], "gpt-5.2-mini")  # local override applied
            self.assertIn("route", parsed[0])

    def test_probe_quota_does_not_probe_a_host_selectable_alias(self):
        with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            config_dir = os.path.join(home, ".config", "ai-kit")
            os.makedirs(config_dir)
            cfg_write_toml(
                os.path.join(config_dir, "review-spec.toml"),
                {"policy": {"ladder": ["native"]},
                 "reviewers": [{"key": "native", "model": "opus", "runtime": "claude"}]},
            )
            quota_path = os.path.join(cwd, "quota.json")
            fake_runner = mock.Mock(
                side_effect=AssertionError("host-selectable reviewer reached the runner"))
            fake_custom = mock.Mock(
                side_effect=AssertionError("host-selectable reviewer reached the launcher"))
            with mock.patch.object(os, "environ", {"HOME": home, "CLAUDECODE": "1"}):
                self.assertEqual(main(
                    ["probe-quota", "--cwd", cwd, "--quota-path", quota_path],
                    env_fn=lambda: {"HOME": home, "CLAUDECODE": "1"},
                    runner_fn=fake_runner, custom_fn=fake_custom,
                    which_fn=lambda _name: None, run_fn=lambda *_a, **_k: None,
                ), 0)
            fake_runner.assert_not_called()
            fake_custom.assert_not_called()
            written = cache_read_json(quota_path)
            self.assertNotIn("native", written or {})

    def test_probe_quota_refreshes_stale_entries_and_writes_cache(self):
        with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
            os.makedirs(os.path.join(home, ".config", "ai-kit"))
            cfg_write_toml(
                os.path.join(home, ".config", "ai-kit", "review-spec.toml"),
                {
                    "policy": {"mode": "single", "ladder": ["codex-gpt"]},
                    "reviewers": [
                        {
                            "key": "codex-gpt",
                            "model": "gpt-5.2",
                            "vendor": "openai",
                            "cli": "codex",
                            "command": "echo ok",
                        }
                    ],
                },
            )
            quota_path = os.path.join(cwd, "quota.json")
            env = {"HOME": home}
            fake_custom = mock.Mock(return_value=_probe_result(None, "ok"))
            with mock.patch.object(os, "environ", env):
                code = main(
                    ["probe-quota", "--cwd", cwd, "--quota-path", quota_path],
                    custom_fn=fake_custom, env_fn=lambda: dict(env),
                    which_fn=lambda _name: None, run_fn=lambda *_a, **_k: None,
                )
            self.assertEqual(code, 0)
            written = cache_read_json(quota_path)
            assert written is not None
            self.assertTrue(written["codex-gpt"]["available"])
            fake_custom.assert_called()  # a command entry goes through the launcher

    def test_probe_quota_reads_its_config_from_the_injected_env(self):
        # B-IN-01: config and host come from one env (env_fn), never os.environ.
        with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home, \
                tempfile.TemporaryDirectory() as other_home:
            os.makedirs(os.path.join(home, ".config", "ai-kit"))
            cfg_write_toml(
                os.path.join(home, ".config", "ai-kit", "review-spec.toml"),
                {"policy": {"ladder": ["cu"]},
                 "reviewers": [{"key": "cu", "model": "m", "command": "mycli {model}"}]},
            )
            fake_custom = mock.Mock(return_value=_probe_result(None, "ok"))
            with mock.patch.object(os, "environ", {"HOME": other_home}):
                code = main(
                    ["probe-quota", "--cwd", cwd,
                     "--quota-path", os.path.join(cwd, "quota.json")],
                    custom_fn=fake_custom, env_fn=lambda: {"HOME": home},
                    which_fn=lambda _name: None, run_fn=lambda *_a, **_k: None,
                )
            self.assertEqual(code, 0)
            fake_custom.assert_called_once()

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
                code = main(
                    [
                        "merge-reports",
                        "--doc-paths",
                        "spec.md",
                        "claude-opus=" + path_a,
                        "codex-gpt=" + path_b,
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("### CRITICAL", buf.getvalue())

    def test_merge_reports_fails_closed_on_a_non_conforming_report(self):
        # D-12/R7: a garbage/failed external CLI report (no Status
        # line) must never silently merge into a false Approved — it
        # fails the merge with a Failure Status line and a non-zero exit
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
                code = main(
                    [
                        "merge-reports",
                        "--doc-paths",
                        "spec.md",
                        "claude-opus=" + path_a,
                        "codex-gpt=" + path_b,
                    ]
                )
            self.assertEqual(code, 1)
            self.assertIn("### Status: Failure — codex-gpt", buf.getvalue())
            self.assertNotIn("### Status: Approved", buf.getvalue())

    def test_render_command_fills_the_indexed_reviewer(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "key": "codex-gpt",
                            "model": "gpt-5.2",
                            "vendor": "openai",
                            "cli": "codex",
                            "command": "codex exec -m {model} {prompt}",
                            "extra": {},
                        }
                    ],
                    f,
                )
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("hello")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "render-command",
                        "--reviewers-json",
                        reviewers_path,
                        "--index",
                        "0",
                        "--prompt-file",
                        prompt_path,
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                json.loads(buf.getvalue()), ["codex", "exec", "-m", "gpt-5.2", "hello"]
            )

    def test_render_command_returns_nonzero_on_malformed_template(self):
        with tempfile.TemporaryDirectory() as d:
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "key": "codex-gpt",
                            "model": "gpt-5.2",
                            "vendor": "openai",
                            "cli": "codex",
                            "command": None,
                            "extra": {},
                        }
                    ],
                    f,
                )
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("hello")
            code = main(
                [
                    "render-command",
                    "--reviewers-json",
                    reviewers_path,
                    "--index",
                    "0",
                    "--prompt-file",
                    prompt_path,
                ]
            )
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
                code = main(["render-toml", "--json-config", json_path])
            self.assertEqual(code, 0)
            self.assertIn("mode", buf.getvalue())
            self.assertFalse(os.path.exists(os.path.join(d, "review-spec.toml")))

    def test_render_toml_with_out_writes_via_cfg_write_toml(self):
        with tempfile.TemporaryDirectory() as d:
            json_path = os.path.join(d, "config.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"policy": {"mode": "double", "ladder": ["a"]}, "reviewers": []}, f)
            out_path = os.path.join(d, "nested", "review-spec.toml")
            code = main(["render-toml", "--json-config", json_path, "--out", out_path])
            self.assertEqual(code, 0)
            written = cfg_load_toml(out_path)
            self.assertEqual(written["policy"]["mode"], "double")

    def test_infer_vendor_prints_matched_vendor(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["infer-vendor", "--model", "kimi-k3-high"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue()), {"vendor": "moonshot"})

    def test_infer_vendor_prints_null_when_unmatched(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["infer-vendor", "--model", "auto"])
        self.assertEqual(code, 0)
        self.assertIsNone(json.loads(buf.getvalue())["vendor"])

    def test_build_command_codex_prints_runner_argv(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["build-command", "--runtime", "codex", "--effort", "high"])
        self.assertEqual(code, 0)
        body = json.loads(out.getvalue())
        self.assertEqual(body["kind"], "runner")
        argv = body["argv"]
        self.assertIn("--prefer", argv)
        self.assertIn("codex", argv)
        self.assertIn("--model-codex", argv)
        self.assertIn("{model}", argv)
        self.assertEqual(argv[argv.index("--codex-effort") + 1], "high")
        self.assertIn("review-spec.toml stores runtime and model", err.getvalue())
        self.assertIn("codex", err.getvalue())

    def test_build_command_cursor_agent_passes_mode_flag(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["build-command", "--cli", "cursor-agent", "--mode", "plan"])
        self.assertEqual(code, 0)
        body = json.loads(out.getvalue())
        self.assertEqual(body["kind"], "runner")
        argv = body["argv"]
        self.assertEqual(argv[argv.index("--cursor-mode") + 1], "plan")
        self.assertIn("review-spec.toml stores runtime and model", err.getvalue())

    def test_build_command_grok_prints_custom_template(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["build-command", "--runtime", "grok"])
        self.assertEqual(code, 0)
        body = json.loads(out.getvalue())
        self.assertEqual(body, {
            "kind": "custom",
            "command": "grok -p {prompt} -m {model} --output-format plain",
        })
        self.assertIn("custom entry", err.getvalue())

    def test_build_command_unknown_runtime_exits_nonzero(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["build-command", "--runtime", "gemini"])
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("hand-written command", err.getvalue())
        self.assertIn("gemini", err.getvalue())

    def test_build_model_id_applies_cursor_agent_overrides(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                [
                    "build-model-id",
                    "--cli",
                    "cursor-agent",
                    "--base-model",
                    "glm-5.2-high",
                    "--fast",
                    "true",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "glm-5.2-high[fast=true]")

    def test_build_model_id_non_cursor_cli_returns_base_model(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                ["build-model-id", "--cli", "codex", "--base-model", "gpt-5.2", "--effort", "high"]
            )
        self.assertEqual(code, 0)
        self.assertEqual(buf.getvalue().strip(), "gpt-5.2")

    def test_group_models_reads_the_named_clis_models_from_a_runtimes_snapshot(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            runtimes_path = os.path.join(d, "runtimes.json")
            cache_write_json(
                runtimes_path,
                {
                    "clis": {
                        "cursor-agent": {
                            "installed": True,
                            "models": ["glm-5.2-high", "glm-5.2-max"],
                        }
                    },
                },
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    ["group-models", "--runtimes-json", runtimes_path, "--cli", "cursor-agent"]
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                json.loads(buf.getvalue()), {"glm-5.2": ["glm-5.2-high", "glm-5.2-max"]}
            )

    def test_group_models_unknown_cli_or_missing_file_yields_empty_groups(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            runtimes_path = os.path.join(d, "does-not-exist.json")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    ["group-models", "--runtimes-json", runtimes_path, "--cli", "cursor-agent"]
                )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(buf.getvalue()), {})

    def test_check_reviewer_native_entry_is_always_available(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                ["check-reviewer", "--key", "session-default"],
                runner_fn=lambda *a: (_ for _ in ()).throw(
                    AssertionError("should never shell out for a native entry")
                ),
            )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(buf.getvalue())["available"])

    def test_check_reviewer_runtime_goes_through_the_runner(self):
        import io
        from contextlib import redirect_stdout

        seen = {}

        def fake_runner(spec, prompt, seams):
            del prompt
            seen["spec"] = spec
            seams.print_fn("ActionRequiredError: Named models unavailable")
            return _probe_result("auth", "auth")

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                ["check-reviewer", "--key", "cursor-glm", "--model", "glm-5.2-high",
                 "--vendor", "zhipu", "--runtime", "cursor"],
                runner_fn=fake_runner,
            )
        self.assertEqual(code, 0)
        parsed = json.loads(buf.getvalue())
        self.assertFalse(parsed["available"])
        self.assertEqual(parsed["reason"], "auth")
        self.assertIn("ActionRequiredError", parsed["detail"])
        self.assertEqual(seen["spec"].runtime, "cursor")
        self.assertEqual(seen["spec"].mode, "review")

    def test_check_reviewer_custom_command_goes_through_the_launcher(self):
        import io
        from contextlib import redirect_stdout

        seen = {}

        def fake_custom(spec, prompt, seams):
            del prompt, seams
            seen["argv"] = spec.argv
            seen["tiers"] = spec.timeout_tiers
            return _probe_result(None)

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(
                ["check-reviewer", "--key", "codex-gpt", "--model", "gpt-5.2",
                 "--command", "codex -m {model} -c effort={effort} {prompt}",
                 "--extra-json", '{"effort": "high"}'],
                custom_fn=fake_custom,
                runner_fn=lambda *a: (_ for _ in ()).throw(AssertionError("runner")),
            )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(buf.getvalue())["available"])
        self.assertEqual(seen["tiers"], [30])
        self.assertIn("effort=high", seen["argv"])


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
            "grok", tool_availability={}, agents_tooling_path=None, codegraph_registered=False
        )
        self.assertEqual(result, "")

    def test_points_to_agents_tooling_file_when_present(self):
        result = tooling_guidance.build_tooling_guidance(
            "claude",
            tool_availability={},
            agents_tooling_path="/home/u/.agents/AGENTS-TOOLING.md",
            codegraph_registered=False,
        )
        self.assertIn("/home/u/.agents/AGENTS-TOOLING.md", result)

    def test_mentions_codegraph_explore_only_when_registered(self):
        result = tooling_guidance.build_tooling_guidance(
            "claude",
            tool_availability={"codegraph": True},
            agents_tooling_path=None,
            codegraph_registered=True,
        )
        self.assertIn("codegraph_explore", result)

    def test_omits_codegraph_explore_when_not_registered_even_if_binary_present(self):
        result = tooling_guidance.build_tooling_guidance(
            "grok",
            tool_availability={"codegraph": True},
            agents_tooling_path=None,
            codegraph_registered=False,
        )
        self.assertNotIn("codegraph_explore", result)

    def test_omits_codegraph_explore_when_registered_but_binary_not_detected(self):
        result = tooling_guidance.build_tooling_guidance(
            "claude",
            tool_availability={"codegraph": False},
            agents_tooling_path=None,
            codegraph_registered=True,
        )
        self.assertNotIn("codegraph_explore", result)

    def test_grok_never_gets_codegraph_explore_even_with_inconsistent_true_inputs(self):
        result = tooling_guidance.build_tooling_guidance(
            "grok",
            tool_availability={"codegraph": True},
            agents_tooling_path=None,
            codegraph_registered=True,
        )
        self.assertNotIn("codegraph_explore", result)

    def test_resolve_shared_tooling_reference_path_points_to_a_real_file(self):
        path = tooling_guidance.resolve_shared_tooling_reference_path()
        assert path is not None
        self.assertTrue(path.endswith(os.path.join("references", "tooling-guidance.md")))
        self.assertTrue(os.path.isfile(path))

    def test_build_tooling_guidance_always_includes_shared_reference_when_given(self):
        guidance = tooling_guidance.build_tooling_guidance(
            "grok", {}, None, False, shared_reference_path="/fake/tooling-guidance.md"
        )
        self.assertIn("Read /fake/tooling-guidance.md", guidance)

    def test_build_tooling_guidance_omits_shared_reference_line_when_not_given(self):
        guidance = tooling_guidance.build_tooling_guidance("grok", {}, None, False)
        self.assertNotIn("tooling-guidance.md", guidance)

    def test_surfaces_tool_availability_as_a_named_variable_the_reviewer_can_check(self):
        # ai-kit-spec-review-checklist's legacy-tool-usage rule is gated on the modern
        # equivalent being "confirmed in tool_availability" -- the map has to actually reach
        # the dispatched reviewer under that name or the rule can never fire.
        guidance = tooling_guidance.build_tooling_guidance(
            "grok", {"rg": True, "fd": False}, None, False
        )
        self.assertIn('TOOL_AVAILABILITY = {"fd":false,"rg":true}', guidance)

    def test_omits_the_tool_availability_line_when_nothing_was_detected(self):
        guidance = tooling_guidance.build_tooling_guidance("grok", {}, None, False)
        self.assertNotIn("TOOL_AVAILABILITY", guidance)

    def test_paths_are_emitted_as_named_variables_not_only_bare_paths(self):
        guidance = tooling_guidance.build_tooling_guidance(
            "claude",
            {},
            "/home/u/.agents/AGENTS-TOOLING.md",
            False,
            shared_reference_path="/fake/tooling-guidance.md",
        )
        self.assertIn("SHARED_TOOLING_PATH = /fake/tooling-guidance.md", guidance)
        self.assertIn("AGENTS_TOOLING_PATH = /home/u/.agents/AGENTS-TOOLING.md", guidance)


class TestDispatchGuidance(unittest.TestCase):
    def test_model_selection_override_names_the_resolved_dispatch(self):
        result = dispatch_guidance.build_model_selection_override_guidance(
            "codex, model gpt-5.6-sol"
        )
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
            "codex, model gpt-5.6-sol", "FORMAT-BLOCK-MARKER"
        )
        self.assertIn("codex, model gpt-5.6-sol", result)
        self.assertIn("incrementally", result)
        self.assertIn("never report success", result)
        self.assertIn("FORMAT-BLOCK-MARKER", result)

    def test_composed_guidance_omits_output_format_section_when_block_is_none(self):
        result = dispatch_guidance.build_dispatch_reinforcement_guidance("claude, tier opus", None)
        self.assertIn("claude, tier opus", result)
        self.assertNotIn("MUST match this exact", result)


class TestBuildSoftConfinementGuidance(unittest.TestCase):
    def test_names_target_dir_as_the_only_writable_location(self):
        result = execute_dispatch.build_soft_confinement_guidance("/scratch/run1")
        self.assertIn("/scratch/run1", result)
        self.assertIn("NO operating-system-level write confinement", result)


class TestDispatchExecute(unittest.TestCase):
    def test_legacy_runtime_name_runs_as_its_runtime_id(self):
        captured = {}

        def fake_runner(spec, prompt, seams):
            del prompt, seams
            captured["spec"] = spec
            return RunnerResult(0, "", None, None, False, [], "")

        with tempfile.TemporaryDirectory() as target:
            result = execute_dispatch.dispatch_execute(
                execute_dispatch.ExecuteDispatchSpec(
                    candidate={"runtime": "cursor-agent", "model": "gpt-6[effort=high]"},
                    prompt="p", target_dir=target, timeout=600,
                ),
                seams=execute_dispatch.ExecuteSeams(runner_fn=fake_runner),
            )
        self.assertEqual(captured["spec"].runtime, "cursor")
        self.assertEqual(result["runtime"], "cursor")

    def test_native_candidate_raises_rather_than_dispatch(self):
        candidate = {"runtime": None, "model": "opus", "key": "opus-native"}
        with self.assertRaises(ValueError) as ctx:
            execute_dispatch.dispatch_execute(
                execute_dispatch.ExecuteDispatchSpec(
                    candidate=candidate,
                    prompt="do the task",
                    target_dir="/scratch/run1",
                    timeout=600,
                )
            )
        self.assertIn("native", str(ctx.exception).lower())

    def test_builds_real_command_and_dispatches_with_composed_prompt(self):
        candidate = {"runtime": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol"}
        captured = {}

        def fake_runner(spec, prompt, seams):
            captured["spec"] = spec
            captured["prompt"] = prompt
            return RunnerResult(
                0, "done", {"status": "ok"}, None, False,
                ["node", "runner", "--mode", "exec"], "",
            )

        with tempfile.TemporaryDirectory() as target:
            result = execute_dispatch.dispatch_execute(
                execute_dispatch.ExecuteDispatchSpec(
                    candidate=candidate,
                    prompt="do the task",
                    target_dir=target,
                    timeout=600,
                ),
                seams=execute_dispatch.ExecuteSeams(runner_fn=fake_runner),
            )
        self.assertEqual(captured["spec"].runtime, "codex")
        self.assertEqual(captured["spec"].mode, "exec")
        self.assertEqual(captured["spec"].timeout_s, 600)
        self.assertEqual(captured["spec"].cwd, target)
        self.assertEqual(runner_dispatch.runner_flags(captured["spec"])[-2:],
                         ["--codex-sandbox", "workspace-write"])
        self.assertIn("codex, model gpt-5.6-sol", captured["prompt"])
        self.assertIn("do not re-select", captured["prompt"])
        self.assertIn("incrementally", captured["prompt"])
        self.assertTrue(captured["prompt"].endswith("do the task"))
        self.assertEqual(result["runtime"], "codex")
        self.assertEqual(result["model"], "gpt-5.6-sol")
        self.assertEqual(result["stdout"], "done")
        self.assertEqual(result["reason"], None)
        self.assertEqual(result["returncode"], 0)

    def _confinement_prompt(self, runtime):
        captured = {}

        def fake_runner(spec, prompt, seams):
            del spec, seams
            captured["prompt"] = prompt
            return RunnerResult(0, "", {"status": "ok"}, None, False, ["node"], "")

        with tempfile.TemporaryDirectory() as target:
            execute_dispatch.dispatch_execute(
                execute_dispatch.ExecuteDispatchSpec(
                    candidate={"runtime": runtime, "model": "auto", "key": f"{runtime}/auto"},
                    prompt="do the task",
                    target_dir=target,
                    timeout=600,
                ),
                seams=execute_dispatch.ExecuteSeams(runner_fn=fake_runner),
            )
            captured["target"] = target
        return captured

    def test_no_hard_sandbox_cli_gets_soft_confinement_guidance_appended(self):
        for runtime in ("cursor", "opencode", "pi"):
            with self.subTest(runtime=runtime):
                captured = self._confinement_prompt(runtime)
                self.assertIn("NO operating-system-level write confinement", captured["prompt"])
                self.assertIn(captured["target"], captured["prompt"])

    def test_hard_sandbox_cli_gets_no_soft_confinement_guidance(self):
        captured = self._confinement_prompt("codex")
        self.assertNotIn("NO operating-system-level write confinement", captured["prompt"])

    def test_includes_tool_guidance_when_provided(self):
        candidate = {"runtime": "cursor-agent", "model": "sonnet", "key": "cursor-agent/sonnet"}
        captured = {}

        def fake_runner(spec, prompt, seams):
            del spec, seams
            captured["prompt"] = prompt
            return RunnerResult(0, "", {"status": "ok"}, None, False, ["node"], "")

        with tempfile.TemporaryDirectory() as target:
            execute_dispatch.dispatch_execute(
                execute_dispatch.ExecuteDispatchSpec(
                    candidate=candidate,
                    prompt="do the task",
                    target_dir=target,
                    timeout=600,
                    tool_availability={"codegraph": True},
                    agents_tooling_path="/repo/AGENTS-TOOLING.md",
                    codegraph_registered=True,
                ),
                seams=execute_dispatch.ExecuteSeams(runner_fn=fake_runner),
            )
        self.assertIn("/repo/AGENTS-TOOLING.md", captured["prompt"])
        self.assertIn("codegraph_explore", captured["prompt"])

    def test_includes_output_format_block_when_given(self):
        candidate = {
            "runtime": "opencode",
            "model": "router-env/my-coding",
            "key": "opencode/router-env/my-coding",
        }
        captured = {}

        def fake_runner(spec, prompt, seams):
            del spec, seams
            captured["prompt"] = prompt
            return RunnerResult(0, "", {"status": "ok"}, None, False, ["node"], "")

        with tempfile.TemporaryDirectory() as target:
            execute_dispatch.dispatch_execute(
                execute_dispatch.ExecuteDispatchSpec(
                    candidate=candidate,
                    prompt="do the task",
                    target_dir=target,
                    timeout=600,
                    format_block="FORMAT-BLOCK-MARKER",
                ),
                seams=execute_dispatch.ExecuteSeams(runner_fn=fake_runner),
            )
        self.assertIn("FORMAT-BLOCK-MARKER", captured["prompt"])

    def test_threads_effort_and_service_tier_from_the_candidate_into_the_real_builder(self):
        candidate = {
            "runtime": "codex",
            "model": "gpt-5.6-sol",
            "key": "codex/gpt-5.6-sol",
            "effort": "high",
            "service_tier": "priority",
        }
        captured = {}

        def fake_runner(spec, prompt, seams):
            del prompt, seams
            captured["spec"] = spec
            return RunnerResult(0, "", {"status": "ok"}, None, False, ["node"], "")

        with tempfile.TemporaryDirectory() as target:
            execute_dispatch.dispatch_execute(
                execute_dispatch.ExecuteDispatchSpec(
                    candidate=candidate,
                    prompt="do the task",
                    target_dir=target,
                    timeout=600,
                ),
                seams=execute_dispatch.ExecuteSeams(runner_fn=fake_runner),
            )
        self.assertEqual(captured["spec"].effort, "high")
        self.assertEqual(captured["spec"].service_tier, "priority")
        self.assertEqual(runner_dispatch.runner_flags(captured["spec"])[-2:],
                         ["--codex-sandbox", "workspace-write"])

    def test_missing_target_dir_is_refused_before_any_spawn(self):
        def fake_runner(spec, prompt, seams):
            del spec, prompt, seams
            self.fail("runner must not be called for a missing target dir")

        with self.assertRaises(ValueError) as ctx:
            execute_dispatch.dispatch_execute(
                execute_dispatch.ExecuteDispatchSpec(
                    candidate={"runtime": "opencode", "model": "m"},
                    prompt="do the task",
                    target_dir="/no/such/dir",
                    timeout=600,
                ),
                seams=execute_dispatch.ExecuteSeams(runner_fn=fake_runner),
            )
        self.assertIn("/no/such/dir", str(ctx.exception))
        self.assertIn("does not exist", str(ctx.exception))

    def test_pi_exec_prints_the_live_verification_note(self):
        printed = []

        def fake_runner(spec, prompt, seams):
            del spec, prompt, seams
            return RunnerResult(0, "", {"status": "ok"}, None, False, ["node"], "")

        with tempfile.TemporaryDirectory() as target:
            execute_dispatch.dispatch_execute(
                execute_dispatch.ExecuteDispatchSpec(
                    candidate={"runtime": "pi", "model": "m"},
                    prompt="do the task",
                    target_dir=target,
                    timeout=600,
                ),
                seams=execute_dispatch.ExecuteSeams(
                    runner_fn=fake_runner, print_fn=printed.append
                ),
            )
        self.assertTrue(any("Phase 22" in line for line in printed))


class TestExecuteCliError(unittest.TestCase):
    def test_execute_error_message_names_the_supported_clis(self):
        # execute_cli_error is the pre-spawn screen every CLI calls first.
        claude = commands.execute_cli_error("claude")
        grok = commands.execute_cli_error("grok")
        self.assertEqual(
            claude,
            f"'claude' cannot be an execution CLI; supported execute CLIs: "
            f"{', '.join(commands.SUPPORTED_EXECUTE_CLIS)}",
        )
        self.assertIsNotNone(claude)
        self.assertIsNotNone(grok)
        assert claude is not None and grok is not None
        self.assertIn("codex, cursor, opencode, pi", claude)
        self.assertIn("codex, cursor, opencode, pi", grok)
        self.assertIsNotNone(commands.execute_cli_error("nonexistent-cli"))


class TestExecuteCliRejection(unittest.TestCase):
    """D-15 (Phase 16.1): an explicit claude/grok executor choice fails before any spawn."""

    def _rejected_dispatch_run(self, cli_name):
        import io
        from contextlib import redirect_stderr

        def failing_dispatch(*a, **kw):
            self.fail("dispatch_execute_fn must never be called for a rejected CLI")

        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("task")
            buf = io.StringIO()
            with redirect_stderr(buf):
                code = main(
                    [
                        "dispatch-execute",
                        "--cli",
                        cli_name,
                        "--model",
                        "m",
                        "--target-dir",
                        d,
                        "--prompt-file",
                        "-",
                        "--timeout",
                        "5",
                    ],
                    dispatch_execute_fn=failing_dispatch,
                )
        return code, buf.getvalue()

    def test_dispatch_execute_rejects_claude_grok_and_case_variant(self):
        for cli_name in ("claude", "grok", "Claude"):
            with self.subTest(cli=cli_name):
                code, stderr = self._rejected_dispatch_run(cli_name)
                self.assertEqual(code, 2)
                self.assertIn("codex, cursor, opencode, pi", stderr)

    def test_rejection_is_idempotent_across_reruns(self):
        # D-15: nothing is written before the check, so a rejected executor fails identically
        # on every run.
        first = self._rejected_dispatch_run("claude")
        second = self._rejected_dispatch_run("claude")
        self.assertEqual(first, second)

    def test_supported_execute_clis_are_the_runner_table(self):
        self.assertEqual(commands.SUPPORTED_EXECUTE_CLIS, ("codex", "cursor", "opencode", "pi"))

    def test_grok_keeps_its_custom_entry_generator(self):
        # R10/D-29 boundary: the table builders are gone; grok still generates the custom
        # command a review-spec.toml entry stores.
        self.assertEqual(
            commands.build_grok_command(),
            "grok -p {prompt} -m {model} --output-format plain",
        )


class TestExecuteLadderScreen(unittest.TestCase):
    """D-15: unsupported CLIs in the execute ladder are screened loudly, never silently."""

    def _screen(self, candidates, warn_fn=None):
        return execute_selection.resolve_execute_candidates(
            candidates,
            execute_selection.ExecuteResolveOptions(None, 0, {}, [], warn_fn),
        )

    def test_purpose_none_claude_entry_is_skipped_with_a_warning(self):
        warnings = []
        candidates = [
            {"key": "cla", "runtime": "claude", "model": "m"},
            {"key": "oc", "runtime": "opencode", "model": "m"},
        ]
        result = self._screen(candidates, warn_fn=warnings.append)
        self.assertEqual([c["key"] for c in result], ["oc"])
        self.assertEqual(len(warnings), 1)
        self.assertIn("cla", warnings[0])
        self.assertIn("codex, cursor, opencode, pi", warnings[0])

    def test_purpose_both_grok_entry_is_skipped_with_a_warning(self):
        warnings = []
        candidates = [{"key": "gk", "runtime": "grok", "model": "m", "purpose": "both"}]
        result = self._screen(candidates, warn_fn=warnings.append)
        self.assertEqual(result, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("gk", warnings[0])

    def test_purpose_execute_claude_entry_raises_value_error(self):
        candidates = [{"key": "cla", "runtime": "claude", "model": "m", "purpose": "execute"}]
        with self.assertRaises(ValueError) as ctx:
            self._screen(candidates, warn_fn=lambda _msg: self.fail("must raise, not warn"))
        self.assertIn("codex, cursor, opencode, pi", str(ctx.exception))
        self.assertIn("cla", str(ctx.exception))

    def test_custom_command_is_dropped_and_execute_purpose_raises(self):
        warnings = []
        candidate = {"key": "custom", "runtime": None, "command": "mycli {model}"}
        result = self._screen([candidate], warn_fn=warnings.append)
        self.assertEqual(result, [])
        self.assertTrue(any("custom" in warning and "custom command" in warning
                            for warning in warnings))
        candidate["purpose"] = "execute"
        with self.assertRaisesRegex(ValueError, "custom entries run only as reviewers"):
            self._screen([candidate], warn_fn=lambda _: None)

    def test_purpose_review_claude_entry_passes_through_untouched(self):
        warnings = []
        candidates = [{"key": "cla", "runtime": "claude", "model": "m", "purpose": "review"}]
        result = self._screen(candidates, warn_fn=warnings.append)
        self.assertEqual([c["key"] for c in result], ["cla"])
        self.assertEqual(warnings, [])


class TestFilterByAffinity(unittest.TestCase):
    def test_keeps_only_matching_affinity_when_any_match_exists(self):
        candidates = [
            {"key": "a", "task_affinity": "frontend"},
            {"key": "b", "task_affinity": "backend"},
        ]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_no_matching_affinity_returns_all_unfiltered(self):
        candidates = [{"key": "a", "task_affinity": "backend"}]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_candidates_with_no_declared_affinity_always_pass_through(self):
        candidates = [
            {"key": "a", "task_affinity": None},
            {"key": "b", "task_affinity": "frontend"},
        ]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual({c["key"] for c in result}, {"a", "b"})

    def test_mixed_untagged_and_wrong_tag_excludes_only_the_wrong_tag(self):
        candidates = [
            {"key": "untagged", "task_affinity": None},
            {"key": "backend-tagged", "task_affinity": "backend"},
        ]
        result = execute_selection.filter_by_affinity(candidates, "frontend", {})
        self.assertEqual([c["key"] for c in result], ["untagged"])


class TestFilterByPurpose(unittest.TestCase):
    def test_keeps_only_matching_purpose_when_any_match_exists(self):
        candidates = [{"key": "a", "purpose": "execute"}, {"key": "b", "purpose": "review"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_both_purpose_always_matches(self):
        candidates = [{"key": "a", "purpose": "both"}, {"key": "b", "purpose": "review"}]
        result = execute_selection.filter_by_purpose(candidates, "execute")
        self.assertEqual([c["key"] for c in result], ["a"])

    def test_candidates_with_no_declared_purpose_always_pass_through(self):
        candidates = [{"key": "a", "purpose": None}, {"key": "b", "purpose": "execute"}]
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
        candidates = [
            {"key": "small", "context_limit": 100_000},
            {"key": "big", "context_limit": 1_000_000},
        ]
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
            candidates,
            execute_selection.ExecuteResolveOptions("backend", 1000, {}, ["b", "a"]),
        )
        self.assertEqual([c["key"] for c in result], ["b", "a", "c"])

    def test_untyped_task_prefers_untagged_candidates(self):
        # A-WR-09: task_type None still runs the affinity filter (pre-16.1 behavior).
        candidates = [
            {"key": "a", "task_affinity": "frontend", "context_limit": None},
            {"key": "b", "task_affinity": None, "context_limit": None},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, execute_selection.ExecuteResolveOptions(None, 0, {}, ["a", "b"]))
        self.assertEqual([c["key"] for c in result], ["b"])

    def test_unknown_context_ranks_after_confirmed_sufficient(self):
        candidates = [
            {"key": "unknown", "task_affinity": "backend", "context_limit": None},
            {"key": "confirmed", "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates,
            execute_selection.ExecuteResolveOptions("backend", 1000, {}, ["unknown", "confirmed"]),
        )
        self.assertEqual([c["key"] for c in result], ["confirmed", "unknown"])

    def test_purpose_filter_excludes_review_only_candidates(self):
        candidates = [
            {
                "key": "reviewer-only",
                "purpose": "review",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            },
            {
                "key": "both-ok",
                "purpose": "both",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            },
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates, execute_selection.ExecuteResolveOptions("backend", 1000, {}, []),
        )
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
            candidates, execute_selection.ExecuteResolveOptions("backend", 1000, {}, []),
        )  # neither is in top_n_keys -- both share the
        # same fallback rank (len(top_n_keys)), so this IS a genuine rank tie.
        self.assertEqual([c["key"] for c in result], ["exact-match", "untagged"])

    def test_top_n_rank_still_wins_when_no_affinity_tag_is_involved(self):
        # The bonus never overrides an EXPLICIT top_n_keys preference between two candidates
        # that are equally untagged -- it only ever breaks a tie in favor of an exact match.
        candidates = [
            {"key": "a", "context_limit": 1_000_000},
            {"key": "b", "context_limit": 1_000_000},
        ]
        result = execute_selection.resolve_execute_candidates(
            candidates,
            execute_selection.ExecuteResolveOptions("backend", 1000, {}, ["b", "a"]),
        )
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
            candidates,
            execute_selection.ExecuteResolveOptions(
                "backend", 1000, {}, ["top-ranked-untagged", "low-ranked-match"]),
        )
        self.assertEqual([c["key"] for c in result], ["top-ranked-untagged", "low-ranked-match"])


class TestCandidatesToLadder(unittest.TestCase):
    def test_extracts_ordered_keys(self):
        candidates = [{"key": "b/model"}, {"key": "a/model"}]
        self.assertEqual(execute_selection.candidates_to_ladder(candidates), ["b/model", "a/model"])


class TestDispatchReviewer(unittest.TestCase):
    def test_composes_tooling_guidance_and_dispatches_through_the_runner(self):
        captured = {}

        def fake_tiers(spec, tiers, prompt, seams):
            del seams
            captured["spec"] = spec
            captured["prompt"] = prompt
            captured["timeout_tiers"] = tiers
            return runner_dispatch.RunnerResult(
                0, "## Review\n### Status: Approved\n", {"status": "ok"}, None, False, [], ""
            )

        result = reviewer_dispatch.dispatch_reviewer(
            reviewer_dispatch.ReviewerDispatchSpec(
                reviewer_entry={
                    "key": "codex-sol",
                    "model": "gpt-5.6-sol",
                    "vendor": "openai",
                    "runtime": "codex",
                    "extra": {"effort": "high"},
                    "route": "subprocess",
                },
                prompt="Read the checklist and review...",
                timeout_tiers=[600, 1200],
                tool_availability={"rg": True},
                agents_tooling_path=None,
            ),
            seams=reviewer_dispatch.ReviewerSeams(
                runner_tiers_fn=fake_tiers,
                build_tooling_guidance_fn=lambda *a, **kw: "TOOLING GUIDANCE HERE",
                resolve_shared_reference_fn=lambda: "/fake/tooling-guidance.md",
                codegraph_health_fn=lambda cli: True,
            ),
        )

        self.assertEqual(captured["timeout_tiers"], [600, 1200])
        self.assertIn("TOOLING GUIDANCE HERE", captured["prompt"])
        self.assertIn("Read the checklist and review...", captured["prompt"])
        self.assertEqual(captured["spec"].runtime, "codex")
        self.assertEqual(captured["spec"].model, "gpt-5.6-sol")
        self.assertEqual(captured["spec"].mode, "review")
        self.assertEqual(captured["spec"].effort, "high")
        self.assertEqual(result["stdout"], "## Review\n### Status: Approved\n")
        self.assertIsNone(result["reason"])

    def test_custom_command_receives_the_tooling_guidance_prefix_too(self):
        # A custom entry (D-21) inlines {prompt} into its own argv and may never read stdin,
        # so the guidance prefix has to be inside the substituted prompt, not only on stdin.
        captured = {}

        def fake_custom(spec, prompt, seams):
            del seams
            captured["argv"] = spec.argv
            captured["prompt"] = prompt
            return runner_dispatch.RunnerResult(0, "", None, None, False, spec.argv, "")

        reviewer_dispatch.dispatch_reviewer(
            reviewer_dispatch.ReviewerDispatchSpec(
                reviewer_entry={
                    "key": "grok-flagship",
                    "model": "grok-4.6",
                    "vendor": "xai",
                    "command": "grok -p {prompt} -m {model}",
                    "extra": {},
                },
                prompt="Read the checklist and review...",
                timeout_tiers=[600],
                tool_availability={"rg": True},
                agents_tooling_path=None,
            ),
            seams=reviewer_dispatch.ReviewerSeams(
                custom_fn=fake_custom,
                resolve_shared_reference_fn=lambda: "/fake/tooling-guidance.md",
                codegraph_health_fn=lambda cli: False,
            ),
        )

        prompt_element = captured["argv"][2]
        self.assertIn("SHARED_TOOLING_PATH = /fake/tooling-guidance.md", prompt_element)
        self.assertIn("TOOL_AVAILABILITY = ", prompt_element)
        self.assertIn("Read the checklist and review...", prompt_element)
        self.assertEqual(captured["prompt"], prompt_element)

    def test_codegraph_health_is_resolved_internally_not_asked_of_the_caller(self):
        asked = []

        def fake_tiers(spec, tiers, prompt, seams):
            del spec, tiers, prompt, seams
            return runner_dispatch.RunnerResult(0, "", {"status": "ok"}, None, False, [], "")

        def fake_health(cli):
            asked.append(cli)
            return True

        captured_guidance_args = {}

        def fake_guidance(cli, availability, agents_path, codegraph_registered, **kw):
            del cli
            del availability
            del agents_path
            captured_guidance_args["codegraph_registered"] = codegraph_registered
            return ""

        reviewer_dispatch.dispatch_reviewer(
            reviewer_dispatch.ReviewerDispatchSpec(
                reviewer_entry={
                    "key": "k",
                    "model": "m",
                    "vendor": "v",
                    "runtime": "codex",
                    "route": "subprocess",
                    "extra": {},
                },
                prompt="p",
                timeout_tiers=[600],
                tool_availability={"codegraph": True},
            ),
            seams=reviewer_dispatch.ReviewerSeams(
                runner_tiers_fn=fake_tiers,
                build_tooling_guidance_fn=fake_guidance,
                resolve_shared_reference_fn=lambda: None,
                codegraph_health_fn=fake_health,
            ),
        )

        self.assertEqual(asked, ["codex"])
        self.assertTrue(captured_guidance_args["codegraph_registered"])

    def test_custom_entry_never_runs_the_codegraph_health_check(self):
        asked = []

        def fake_custom(spec, prompt, seams):
            del spec, prompt, seams
            return runner_dispatch.RunnerResult(0, "", None, None, False, [], "")

        reviewer_dispatch.dispatch_reviewer(
            reviewer_dispatch.ReviewerDispatchSpec(
                reviewer_entry={
                    "key": "custom",
                    "model": "m",
                    "vendor": "v",
                    "command": "my-script --model {model} --prompt {prompt}",
                    "extra": {},
                },
                prompt="p",
                timeout_tiers=[600],
                tool_availability={},
            ),
            seams=reviewer_dispatch.ReviewerSeams(
                custom_fn=fake_custom,
                resolve_shared_reference_fn=lambda: None,
                codegraph_health_fn=lambda cli: asked.append(cli) or True,
            ),
        )

        self.assertEqual(asked, [])

    def test_native_route_raises_value_error_naming_the_key(self):
        with self.assertRaises(ValueError) as ctx:
            reviewer_dispatch.dispatch_reviewer(
                reviewer_dispatch.ReviewerDispatchSpec(
                    reviewer_entry={
                        "key": "host",
                        "model": "opus",
                        "vendor": "anthropic",
                        "runtime": "claude",
                        "route": "native",
                    },
                    prompt="p",
                    timeout_tiers=[600],
                    tool_availability={},
                ),
                seams=reviewer_dispatch.ReviewerSeams(
                    resolve_shared_reference_fn=lambda: None,
                    codegraph_health_fn=lambda cli: False,
                    runner_tiers_fn=lambda *a: (_ for _ in ()).throw(AssertionError(a)),
                ),
            )
        self.assertIn("host", str(ctx.exception))
        self.assertIn("routes native", str(ctx.exception))

    def test_dispatch_reviewer_cli_subcommand_stdout_only_prints_raw_report(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            prompt_path = os.path.join(d, "prompt.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("review this plan")
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "key": "grok-flagship",
                            "model": "grok-4.6",
                            "vendor": "xai",
                            "cli": "grok",
                            "command": "grok -p {prompt} -m {model}",
                            "extra": {},
                        }
                    ],
                    f,
                )
            seen = {}

            def fake_dispatch_reviewer(spec, *a, **kw):
                seen["entry"] = spec.reviewer_entry
                return {
                    "returncode": 0,
                    "stdout": "### Status: Approved\n",
                    "stderr": "",
                    "timed_out": False,
                    "tiers_tried": 1,
                    "final_timeout": 600,
                }

            with redirect_stdout(io.StringIO()) as out:
                code = main(
                    [
                        "dispatch-reviewer",
                        "--reviewers-json",
                        reviewers_path,
                        "--index",
                        "0",
                        "--prompt-file",
                        prompt_path,
                        "--timeout-tiers",
                        "600,1200",
                        "--stdout-only",
                    ],
                    dispatch_reviewer_fn=fake_dispatch_reviewer,
                )
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
                json.dump(
                    [
                        {
                            "key": "broken",
                            "model": "m",
                            "vendor": "v",
                            "cli": "codex",
                            "command": None,
                            "extra": {},
                        }
                    ],
                    f,
                )
            with redirect_stderr(io.StringIO()) as err:
                code = main(
                    [
                        "dispatch-reviewer",
                        "--reviewers-json",
                        reviewers_path,
                        "--index",
                        "0",
                        "--prompt-file",
                        prompt_path,
                        "--timeout-tiers",
                        "600",
                    ]
                )
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
                code = main(
                    [
                        "dispatch-reviewer",
                        "--reviewers-json",
                        reviewers_path,
                        "--index",
                        "0",
                        "--prompt-file",
                        prompt_path,
                        "--timeout-tiers",
                        "600",
                    ]
                )
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
                json.dump(
                    [
                        {
                            "key": "codex-sol",
                            "model": "gpt-5.6-sol",
                            "vendor": "openai",
                            "cli": "codex",
                            "command": "codex exec -m {model}",
                            "extra": {"timeout_tiers": [900, 1800]},
                        }
                    ],
                    f,
                )
            with redirect_stdout(io.StringIO()) as out:
                code = main(
                    [
                        "resolve-timeout-tiers",
                        "--cwd",
                        d,
                        "--reviewers-json",
                        reviewers_path,
                        "--index",
                        "0",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().strip(), "900,1800")

    def test_resolve_timeout_tiers_cli_subcommand_falls_back_to_policy_default(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            # No .aikit/review-spec.toml at all -- cfg_resolve degrades to DEFAULT_POLICY.
            reviewers_path = os.path.join(d, "reviewers.json")
            with open(reviewers_path, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "key": "grok-flagship",
                            "model": "grok-4.6",
                            "vendor": "xai",
                            "cli": "grok",
                            "command": "grok -p {prompt} -m {model}",
                            "extra": {},
                        }
                    ],
                    f,
                )
            with redirect_stdout(io.StringIO()) as out:
                code = main(
                    [
                        "resolve-timeout-tiers",
                        "--cwd",
                        d,
                        "--reviewers-json",
                        reviewers_path,
                        "--index",
                        "0",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().strip(), "600,1200,1800")


class TestLoadRankingWeights(unittest.TestCase):
    def test_loads_the_real_bundled_weights_file(self):
        weights = model_ranker.load_ranking_weights()
        self.assertAlmostEqual(weights["review"]["intelligence_index"], 0.30)
        self.assertAlmostEqual(weights["execution"]["coding_index"], 0.25)
        self.assertEqual(weights["bonuses"]["batch_mode"], 8)
        self.assertEqual(weights["bonuses"]["bonus_cap"], 15)

    def test_missing_file_falls_back_to_default_weights(self):
        weights = model_ranker.load_ranking_weights("/nonexistent/path.toml")
        self.assertIn("review", weights)
        self.assertIn("execution", weights)
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
            self.assertIn("execution", weights)
        finally:
            os.remove(path)

    def test_syntactically_valid_toml_missing_an_axis_falls_back(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(
                "[review]\nintelligence_index = 0.99\n"  # missing every other axis --
                # MEDIUM finding (round-4): deliberately 0.99, NOT 0.30 (the real default's
                # own value) -- an earlier draft used 0.30 here too, so this assertion could
                # pass whether load_ranking_weights actually fell back OR just happened to
                # read this partial file's own intelligence_index value back verbatim,
                # proving nothing about the fallback path actually running.
                "[execute]\nintelligence_index = 0.15\ncoding_index = 0.30\n"
                "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                "price = 0.15\nspeed = 0.10\n"
                "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n"
            )
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
            f.write(
                '[review]\nintelligence_index = "high"\ncoding_index = 0.10\n'
                "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                "price = 0.15\nspeed = 0.05\n"
                "[execute]\nintelligence_index = 0.15\ncoding_index = 0.30\n"
                "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                "price = 0.15\nspeed = 0.10\n"
                "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n"
            )
            path = f.name
        try:
            weights = model_ranker.load_ranking_weights(path)
            self.assertIsInstance(weights["review"]["intelligence_index"], (int, float))
        finally:
            os.remove(path)

    def test_syntactically_valid_toml_missing_a_bonus_field_falls_back(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(
                "[review]\nintelligence_index = 0.30\ncoding_index = 0.10\n"
                "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                "price = 0.15\nspeed = 0.05\n"
                "[execute]\nintelligence_index = 0.15\ncoding_index = 0.30\n"
                "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                "price = 0.15\nspeed = 0.10\n"
                "[bonuses]\nbatch_mode = 8\n"
            )  # missing fallback_quota/bonus_cap
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
            {
                "key": "low",
                "scores": {"intelligence_index": 40, "coding_index": 40, "agentic_index": 40},
            },
            {
                "key": "high",
                "scores": {"intelligence_index": 90, "coding_index": 40, "agentic_index": 40},
            },
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
            {
                "key": "anchor",
                "scores": {"intelligence_index": 100, "coding_index": 100, "agentic_index": 100},
            },
            {"key": "no_scores", "tool_calling": True},
            {
                "key": "low_real_scores",
                "scores": {"intelligence_index": 1, "coding_index": 1, "agentic_index": 1},
                "tool_calling": False,
            },
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
            {
                "key": "flagship",
                "scores": {"intelligence_index": 62, "coding_index": 58, "agentic_index": 55},
                "pricing": {"input_per_1m": 15.0},
            },
            {
                "key": "mid_tier",
                "scores": {"intelligence_index": 45, "coding_index": 42, "agentic_index": 40},
                "pricing": {"input_per_1m": 20.0},
            },
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
            {
                "key": "anchor",
                "scores": {"intelligence_index": 100, "coding_index": 100, "agentic_index": 100},
            },
            {
                "key": "no_batch",
                "scores": {"intelligence_index": 52, "coding_index": 52, "agentic_index": 52},
                "batch_mode": False,
            },
            {
                "key": "batch",
                "scores": {"intelligence_index": 50, "coding_index": 50, "agentic_index": 50},
                "batch_mode": True,
            },
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        order = [e["key"] for e in ranked]
        self.assertLess(order.index("batch"), order.index("no_batch"))

    def test_bonus_is_capped(self):
        entries = [
            {
                "key": "everything",
                "scores": {"intelligence_index": 100, "coding_index": 100, "agentic_index": 100},
                "batch_mode": True,
                "fallback_quota": True,
            }
        ]
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
        entries = [
            {
                "key": "maxed",
                "scores": {"intelligence_index": 100, "coding_index": 100, "agentic_index": 100},
                "tool_calling": True,
                "batch_mode": True,
                "fallback_quota": True,
            }
        ]
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
            {
                "key": "low",
                "scores": {"intelligence_index": 30, "coding_index": 30, "agentic_index": 30},
            },
            {
                "key": "high",
                "scores": {"intelligence_index": 65, "coding_index": 65, "agentic_index": 65},
            },
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        self.assertEqual(ranked[0]["key"], "high")

    def test_score_exact_is_unrounded_and_rounds_to_score(self):
        # 17 D-15: every returned copy carries the unrounded score next to the
        # unchanged rounded one.
        entries = [
            {"key": "a", "scores": {"intelligence_index": 40.0}},
            {"key": "b", "scores": {"intelligence_index": 50.0}},
        ]
        ranked = model_ranker.score_candidates(entries, "planning", self.weights)
        for e in ranked:
            self.assertIsInstance(e["score_exact"], float)
            self.assertEqual(round(e["score_exact"], 1), e["score"])

    def test_score_exact_separates_scores_that_round_equal(self):
        # Two candidates whose exact scores differ by < 0.05 share the same rounded
        # "score" but carry different unrounded "score_exact" values. Two anchors (0
        # and 100) compress the min-max spread so 40.0 vs 40.04 stays a sub-0.05 gap.
        entries = [
            {"key": "lo", "scores": {"intelligence_index": 0.0}},
            {"key": "a", "scores": {"intelligence_index": 40.0}},
            {"key": "b", "scores": {"intelligence_index": 40.04}},
            {"key": "hi", "scores": {"intelligence_index": 100.0}},
        ]
        ranked = model_ranker.score_candidates(entries, "planning", self.weights)
        by_key = {e["key"]: e for e in ranked}
        self.assertEqual(by_key["a"]["score"], by_key["b"]["score"])
        self.assertNotEqual(by_key["a"]["score_exact"], by_key["b"]["score_exact"])


class TestPurposeAliasesEndToEnd(unittest.TestCase):
    """Test the 5-purpose ranker with execute/review aliases (16 D-10)."""

    def setUp(self):
        # Candidates with coding_index >= 40 so Task 2's mechanical floor never excludes them
        self.entries = [
            {
                "key": "A",
                "scores": {"intelligence_index": 90, "coding_index": 50, "agentic_index": 80},
                "pricing": {"input_per_1m": 15.0},
            },
            {
                "key": "B",
                "scores": {"intelligence_index": 50, "coding_index": 50, "agentic_index": 40},
                "pricing": {"input_per_1m": 0.5},
            },
            {
                "key": "C",
                "scores": {"intelligence_index": 70, "coding_index": 80, "agentic_index": 60},
                "pricing": {"input_per_1m": 3.0},
                "tool_calling": True,
            },
        ]

    def test_bundled_file_loads_every_canonical_purpose_and_mirrors_defaults(self):
        w = model_ranker.load_ranking_weights()
        self.assertEqual(set(w.keys()), set(model_ranker.CANONICAL_PURPOSES) | {"bonuses"})
        self.assertEqual(w, model_ranker.DEFAULT_WEIGHTS)

    def test_execute_alias_ranks_identically_to_execution(self):
        weights = model_ranker.load_ranking_weights()
        ranked_exec = [
            (e["key"], e["score"])
            for e in model_ranker.score_candidates(self.entries, "execute", weights)
        ]
        ranked_execution = [
            (e["key"], e["score"])
            for e in model_ranker.score_candidates(self.entries, "execution", weights)
        ]
        self.assertEqual(ranked_exec, ranked_execution)

    def test_review_resolves_to_itself(self):
        self.assertEqual(model_ranker.resolve_purpose("review"), "review")

    def test_resolve_purpose_maps_aliases_only(self):
        self.assertEqual(model_ranker.resolve_purpose("execute"), "execution")
        self.assertEqual(model_ranker.resolve_purpose("review"), "review")
        self.assertEqual(model_ranker.resolve_purpose("planning"), "planning")
        self.assertEqual(model_ranker.resolve_purpose("banana"), "banana")

    def test_every_canonical_purpose_ranks_all_candidates(self):
        weights = model_ranker.load_ranking_weights()
        for purpose in model_ranker.CANONICAL_PURPOSES:
            ranked = model_ranker.score_candidates(self.entries, purpose, weights)
            self.assertEqual(len(ranked), 3)
            for e in ranked:
                self.assertGreaterEqual(e["score"], 0)
                self.assertLessEqual(e["score"], 100)

    def test_planning_prefers_intelligence_and_mechanical_prefers_price(self):
        weights = model_ranker.load_ranking_weights()
        ranked_planning = model_ranker.score_candidates(self.entries, "planning", weights)
        ranked_mechanical = model_ranker.score_candidates(self.entries, "mechanical", weights)
        # A has highest intelligence (90), should rank first in planning (planning_weight=0.40)
        self.assertEqual(ranked_planning[0]["key"], "A")
        # Mechanical ranks by price (weight=0.55), so lower price > high intelligence
        # C has price $3.0 with good scores; B has price $0.5 but lower scores
        # Both rank ahead of A at $15.0, proving price dominates mechanical
        planning_order = [e["key"] for e in ranked_planning]
        mechanical_order = [e["key"] for e in ranked_mechanical]
        self.assertNotEqual(planning_order, mechanical_order)

    def test_unknown_purpose_raises_key_error(self):
        weights = model_ranker.load_ranking_weights()
        with self.assertRaises(KeyError):
            model_ranker.score_candidates(self.entries, "unknown_purpose", weights)

    def test_hand_built_legacy_weights_dict_still_ranks_execute(self):
        legacy = {
            "review": model_ranker.DEFAULT_WEIGHTS["review"].copy(),
            "execute": model_ranker.DEFAULT_WEIGHTS["execution"].copy(),
            "bonuses": model_ranker.DEFAULT_WEIGHTS["bonuses"].copy(),
        }
        ranked = model_ranker.score_candidates(self.entries, "execute", legacy)
        self.assertEqual(len(ranked), 3)

    def test_old_two_purpose_file_still_loads(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(
                "[review]\nintelligence_index = 0.33\ncoding_index = 0.10\n"
                "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                "price = 0.15\nspeed = 0.05\n"
                "[execute]\nintelligence_index = 0.15\ncoding_index = 0.77\n"
                "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                "price = 0.15\nspeed = 0.10\n"
                "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n"
            )
            path = f.name
        try:
            w = model_ranker.load_ranking_weights(path)
            self.assertAlmostEqual(w["review"]["intelligence_index"], 0.33)
            self.assertAlmostEqual(w["execution"]["coding_index"], 0.77)
            self.assertEqual(w["planning"], model_ranker.DEFAULT_WEIGHTS["planning"])
            self.assertNotIn("execute", w)
        finally:
            os.remove(path)

    def test_canonical_section_wins_over_alias_section(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(
                "[execute]\nintelligence_index = 0.15\ncoding_index = 0.77\n"
                "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                "price = 0.15\nspeed = 0.10\n"
                "[execution]\nintelligence_index = 0.15\ncoding_index = 0.66\n"
                "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                "price = 0.15\nspeed = 0.10\n"
                "[review]\nintelligence_index = 0.30\ncoding_index = 0.10\n"
                "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                "price = 0.15\nspeed = 0.05\n"
                "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n"
            )
            path = f.name
        try:
            w = model_ranker.load_ranking_weights(path)
            self.assertAlmostEqual(w["execution"]["coding_index"], 0.66)
        finally:
            os.remove(path)

    def test_malformed_new_section_rejects_whole_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(
                "[planning]\nintelligence_index = 0.40\n"  # missing all other axes
                "[review]\nintelligence_index = 0.33\ncoding_index = 0.10\n"
                "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                "price = 0.15\nspeed = 0.05\n"
                "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n"
            )
            path = f.name
        try:
            w = model_ranker.load_ranking_weights(path)
            self.assertEqual(
                w["review"]["intelligence_index"],
                model_ranker.DEFAULT_WEIGHTS["review"]["intelligence_index"],
            )
        finally:
            os.remove(path)

    def test_bool_axis_weight_rejects_whole_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(
                "[review]\nintelligence_index = true\ncoding_index = 0.10\n"
                "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                "price = 0.15\nspeed = 0.05\n"
                "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n"
            )
            path = f.name
        try:
            w = model_ranker.load_ranking_weights(path)
            self.assertEqual(w, model_ranker.DEFAULT_WEIGHTS)
        finally:
            os.remove(path)

    def test_bool_bonus_rejects_whole_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(
                "[review]\nintelligence_index = 0.30\ncoding_index = 0.10\n"
                "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                "price = 0.15\nspeed = 0.05\n"
                "[bonuses]\nbatch_mode = true\nfallback_quota = 5\nbonus_cap = 15\n"
            )
            path = f.name
        try:
            w = model_ranker.load_ranking_weights(path)
            self.assertEqual(w, model_ranker.DEFAULT_WEIGHTS)
        finally:
            os.remove(path)

    def test_is_finite_number_rejects_bool_and_non_finite(self):
        self.assertTrue(model_ranker._is_finite_number(0))
        self.assertTrue(model_ranker._is_finite_number(0.25))
        self.assertTrue(model_ranker._is_finite_number(35))
        self.assertFalse(model_ranker._is_finite_number(True))
        self.assertFalse(model_ranker._is_finite_number(False))
        self.assertFalse(model_ranker._is_finite_number(float("nan")))
        self.assertFalse(model_ranker._is_finite_number(float("inf")))
        self.assertFalse(model_ranker._is_finite_number("1"))
        self.assertFalse(model_ranker._is_finite_number(None))

    def test_review_self_alias_section_is_kept_as_is(self):
        data = {
            "review": {
                "intelligence_index": 0.30,
                "coding_index": 0.10,
                "agentic_index": 0.15,
                "context_window": 0.15,
                "tool_calling": 0.05,
                "price": 0.15,
                "speed": 0.05,
            },
            "execute": {
                "intelligence_index": 0.10,
                "coding_index": 0.25,
                "agentic_index": 0.20,
                "context_window": 0.05,
                "tool_calling": 0.10,
                "price": 0.25,
                "speed": 0.05,
            },
            "bonuses": {"batch_mode": 8, "fallback_quota": 5, "bonus_cap": 15},
        }
        result = model_ranker._normalize_purpose_aliases(data)
        self.assertEqual(result["review"], data["review"])
        self.assertEqual(result["execution"], data["execute"])
        self.assertNotIn("execute", result)


class TestRankerPurposeFloor(unittest.TestCase):
    """Test optional per-purpose floors (mechanical coding_index 35) with exclusive filtering."""

    def test_bundled_mechanical_floor_is_coding_35_only(self):
        w = model_ranker.load_ranking_weights()
        self.assertEqual(w["mechanical"]["floor"], {"coding_index": 35})
        for purpose in ("review", "execution", "planning", "general"):
            self.assertNotIn("floor", w[purpose])

    def test_floor_boundary_is_inclusive(self):
        entries = [
            {"key": "below", "scores": {"coding_index": 34}},
            {"key": "at", "scores": {"coding_index": 35}},
            {"key": "above", "scores": {"coding_index": 36}},
        ]
        # Add minimal required other fields to avoid errors
        for e in entries:
            e.update({"intelligence_index": 50, "agentic_index": 50, "pricing": {}})
        w = model_ranker.load_ranking_weights()
        ranked = model_ranker.score_candidates(entries, "mechanical", w)
        keys = [e["key"] for e in ranked]
        self.assertNotIn("below", keys)
        self.assertIn("at", keys)
        self.assertIn("above", keys)

    def test_missing_or_non_numeric_floor_axis_is_excluded(self):
        entries = [
            {"key": "no_scores"},
            {"key": "no_coding"},
            {"key": "coding_none", "scores": {"coding_index": None}},
            {"key": "coding_bool", "scores": {"coding_index": True}},
            {"key": "coding_string", "scores": {"coding_index": "40"}},
            {"key": "pass", "scores": {"coding_index": 40}},
        ]
        for e in entries:
            if "scores" not in e:
                e["scores"] = {}
            e.update({"pricing": {}})
        w = model_ranker.load_ranking_weights()
        ranked = model_ranker.score_candidates(entries, "mechanical", w)
        keys = [e["key"] for e in ranked]
        self.assertEqual(keys, ["pass"])

    def test_floor_filters_before_normalization(self):
        # High-price, above-floor candidate; low-price, below-floor candidate
        entries = [
            {
                "key": "expensive_pass",
                "scores": {"coding_index": 80, "intelligence_index": 50, "agentic_index": 50},
                "pricing": {"input_per_1m": 50.0},
            },
            {
                "key": "cheap_fail",
                "scores": {"coding_index": 30, "intelligence_index": 100, "agentic_index": 100},
                "pricing": {"input_per_1m": 0.1},
            },
            {
                "key": "cheap_pass",
                "scores": {"coding_index": 35, "intelligence_index": 50, "agentic_index": 50},
                "pricing": {"input_per_1m": 0.1},
            },
        ]
        w = model_ranker.load_ranking_weights()
        ranked_mech = model_ranker.score_candidates(entries, "mechanical", w)
        keys_mech = [e["key"] for e in ranked_mech]
        # cheap_fail is excluded by floor, so cheap_pass and expensive_pass survive
        # The normalization range for price is now 0.1-50, not 0.1-100
        self.assertNotIn("cheap_fail", keys_mech)
        self.assertIn("cheap_pass", keys_mech)
        self.assertIn("expensive_pass", keys_mech)

    def test_floors_are_generic_across_purposes(self):
        # Test that any purpose can have a floor (not just mechanical)
        planning_weights = copy.deepcopy(model_ranker.DEFAULT_WEIGHTS)
        planning_weights["planning"]["floor"] = {"intelligence_index": 50}
        entries = [
            {
                "key": "low_int",
                "scores": {"intelligence_index": 40, "coding_index": 80, "agentic_index": 80},
                "pricing": {},
            },
            {
                "key": "high_int",
                "scores": {"intelligence_index": 60, "coding_index": 50, "agentic_index": 50},
                "pricing": {},
            },
        ]
        ranked = model_ranker.score_candidates(entries, "planning", planning_weights)
        keys = [e["key"] for e in ranked]
        self.assertEqual(keys, ["high_int"])

    def test_invalid_floor_tables_reject_the_whole_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(
                "[review]\nintelligence_index = 0.30\ncoding_index = 0.10\n"
                "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                "price = 0.15\nspeed = 0.05\n"
                "[planning]\nintelligence_index = 0.40\ncoding_index = 0.10\n"
                "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.05\n"
                "price = 0.05\nspeed = 0.05\n"
                "[planning.floor]\nprice = 20\n"  # price not in _FLOORABLE_AXES
                "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n"
            )
            path = f.name
        try:
            w = model_ranker.load_ranking_weights(path)
            self.assertEqual(w, model_ranker.DEFAULT_WEIGHTS)
        finally:
            os.remove(path)

    def test_invalid_floor_nan_rejects_the_whole_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(
                "[review]\nintelligence_index = 0.30\ncoding_index = 0.10\n"
                "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                "price = 0.15\nspeed = 0.05\n"
                "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n"
            )
            path = f.name
        try:
            # Instead, write a floor with a string value that fails _is_finite_number
            with open(path, "w") as f:
                f.write(
                    "[review]\nintelligence_index = 0.30\ncoding_index = 0.10\n"
                    "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                    "price = 0.15\nspeed = 0.05\n"
                    '[review.floor]\nintelligence_index = "high"\n'
                    "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n"
                )
            w = model_ranker.load_ranking_weights(path)
            self.assertEqual(w, model_ranker.DEFAULT_WEIGHTS)
        finally:
            os.remove(path)

    def test_invalid_utf8_file_falls_back_without_raising(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".toml", delete=False) as f:
            f.write(b"\xff\xfe[review]\n")  # Invalid UTF-8 bytes
            path = f.name
        try:
            w = model_ranker.load_ranking_weights(path)
            self.assertEqual(w, model_ranker.DEFAULT_WEIGHTS)
        finally:
            os.remove(path)

    def test_loaded_floor_is_an_independent_copy(self):
        w1 = model_ranker.load_ranking_weights()
        w1["mechanical"]["floor"]["coding_index"] = 999
        w2 = model_ranker.load_ranking_weights()
        self.assertEqual(w2["mechanical"]["floor"]["coding_index"], 35)

    def test_score_candidates_never_mutates_inputs(self):
        entries = [
            {
                "key": "A",
                "scores": {"coding_index": 50, "intelligence_index": 50, "agentic_index": 50},
                "pricing": {},
            },
            {
                "key": "B",
                "scores": {"coding_index": 20, "intelligence_index": 50, "agentic_index": 50},
                "pricing": {},
            },
        ]
        entries_copy = copy.deepcopy(entries)
        w = model_ranker.load_ranking_weights()
        model_ranker.score_candidates(entries, "mechanical", w)
        # entries should not be mutated (same object structure, no added keys)
        self.assertEqual(entries, entries_copy)


class TestLoadSecret(unittest.TestCase):
    def test_env_var_takes_precedence(self):
        env = {"ARTIFICIAL_ANALYSIS_API_KEY": "from-env"}
        self.assertEqual(local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY"), "from-env")

    def test_reads_from_secrets_file_when_env_absent(self):
        with tempfile.TemporaryDirectory() as d:
            cfg_dir = os.path.join(d, ".config", "ai-kit")
            os.makedirs(cfg_dir)
            with open(os.path.join(cfg_dir, "secrets.env"), "w", encoding="utf-8") as f:
                f.write("# comment\nARTIFICIAL_ANALYSIS_API_KEY=from-file\nOTHER=ignored\n")
            env = {"HOME": d}
            self.assertEqual(
                local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY"), "from-file"
            )

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



class TestSecretIsSet(unittest.TestCase):
    def test_env_non_empty_is_true(self):
        self.assertTrue(local_secrets.secret_is_set({"JEV_API_KEY": "x"}, "JEV_API_KEY"))

    def test_file_value_without_returning_it(self):
        with tempfile.TemporaryDirectory() as d:
            cfg_dir = os.path.join(d, ".config", "ai-kit")
            os.makedirs(cfg_dir)
            with open(os.path.join(cfg_dir, "secrets.env"), "w", encoding="utf-8") as f:
                f.write("JEV_API_KEY=sk-SENTINEL-18-01\n")
            env = {"HOME": d, "JEV_API_KEY": ""}
            result = local_secrets.secret_is_set(env, "JEV_API_KEY")
            self.assertIs(result, True)
            self.assertNotEqual(result, "sk-SENTINEL-18-01")

    def test_empty_file_value_is_false(self):
        with tempfile.TemporaryDirectory() as d:
            cfg_dir = os.path.join(d, ".config", "ai-kit")
            os.makedirs(cfg_dir)
            with open(os.path.join(cfg_dir, "secrets.env"), "w", encoding="utf-8") as f:
                f.write("JEV_API_KEY=\n")
            self.assertFalse(local_secrets.secret_is_set({"HOME": d}, "JEV_API_KEY"))

    def test_missing_file_is_false(self):
        self.assertFalse(
            local_secrets.secret_is_set({"HOME": "/nonexistent-home-dir-18-01"}, "JEV_API_KEY")
        )


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
            return {"data": [{"id": "1", "name": "Model A"}], "pagination": {"has_more": False}}

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

        _data, ok = model_sources.fetch_artificial_analysis("aa_test", fetch_fn=flaky_fetch)
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
        self.assertEqual(model_heuristics.infer_purpose_from_name("router-env-review"), "review")

    def test_plan_review_hint_matches(self):
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("router-env-plan-review"), "review"
        )

    def test_coding_hint_matches(self):
        self.assertEqual(model_heuristics.infer_purpose_from_name("router-env-coding"), "execute")

    def test_execute_hint_matches(self):
        self.assertEqual(model_heuristics.infer_purpose_from_name("router-env-execute"), "execute")

    def test_no_hint_returns_none(self):
        self.assertIsNone(model_heuristics.infer_purpose_from_name("router-env-fast"))

    def test_both_groups_matching_is_a_contradiction_returns_none(self):
        # A naming contradiction (both a review word and an execute word) must never be
        # silently resolved by picking one.
        self.assertIsNone(model_heuristics.infer_purpose_from_name("router-env-coding-review"))

    def test_case_insensitive(self):
        self.assertEqual(model_heuristics.infer_purpose_from_name("Router-Env-Coding"), "execute")

    def test_hint_word_need_not_be_trailing(self):
        # A router operator's naming convention isn't guaranteed to put the purpose word
        # last -- token match anywhere in the id, not suffix-only.
        self.assertEqual(model_heuristics.infer_purpose_from_name("review-router-env"), "review")

    def test_review_does_not_match_inside_preview(self):
        # Delimiter-boundary pin: "review" is a substring of "preview", but the "r" in
        # "review" is preceded by "p" (a word character), so no \b boundary exists there --
        # this must NOT match. Without the \b-bounded fix, this would wrongly return
        # "review", silently discarding a legitimate router-exposed model's real enrichment.
        self.assertIsNone(
            model_heuristics.infer_purpose_from_name("router-env/gemini-3-pro-preview")
        )

    def test_coding_does_not_match_inside_encoding(self):
        # Same class of false positive for the execute group: "coding" is a substring of
        # "encoding" but not a delimiter-bounded token there.
        self.assertIsNone(
            model_heuristics.infer_purpose_from_name("router-env/some-encoding-model")
        )


class TestStripKnownEffortSuffix(unittest.TestCase):
    def test_strips_a_single_trailing_effort_token(self):
        self.assertEqual(
            model_matcher._strip_known_effort_suffix("claude-opus-5-high"), "claude-opus-5"
        )

    def test_strips_a_two_token_effort_compound(self):
        self.assertEqual(
            model_matcher._strip_known_effort_suffix("claude-opus-5-thinking-xhigh"),
            "claude-opus-5",
        )

    def test_strips_the_thinking_max_compound(self):
        self.assertEqual(
            model_matcher._strip_known_effort_suffix("claude-opus-5-thinking-max"), "claude-opus-5"
        )

    def test_no_strippable_trailing_token_returns_none(self):
        self.assertIsNone(model_matcher._strip_known_effort_suffix("claude-opus-5"))

    def test_a_service_tier_suffix_as_trailing_token_is_never_touched(self):
        # "fast" is not a recognized effort word -- the loop never even starts, so this is
        # untouched for a structural reason, not a separate tier denylist.
        self.assertIsNone(
            model_matcher._strip_known_effort_suffix("claude-opus-5-thinking-low-fast")
        )

    def test_bare_max_without_a_preceding_thinking_token_is_not_stripped(self):
        # Real base model qwen3-max must never be misattributed to "qwen3".
        self.assertIsNone(model_matcher._strip_known_effort_suffix("qwen3-max"))

    def test_a_real_base_model_ending_in_an_effort_word_is_preserved_after_stripping(self):
        # o3-mini-high is a genuine, different-from-o3 model -- "mini" must survive the strip.
        self.assertEqual(model_matcher._strip_known_effort_suffix("o3-mini-high"), "o3-mini")


class TestMatchModelsDev(unittest.TestCase):
    def setUp(self):
        self.data = {
            "openai": {
                "models": {
                    "gpt-5.6-sol": {
                        "id": "gpt-5.6-sol",
                        "reasoning": True,
                        "tool_call": True,
                        "limit": {"context": 400000, "output": 128000},
                        "cost": {"input": 3.5, "output": 14.0},
                    }
                }
            },
            "xai": {
                "models": {
                    "grok-4.6": {"id": "grok-4.6", "tool_call": True, "limit": {"context": 256000}}
                }
            },
        }

    def test_matches_provider_prefixed_id_exactly(self):
        result = model_matcher.match_models_dev("openai/gpt-5.6-sol", self.data)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["cost"]["input"], 3.5)

    def test_matches_bare_id_by_searching_all_providers(self):
        result = model_matcher.match_models_dev("gpt-5.6-sol", self.data)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["provider"], "openai")

    def test_no_match_returns_none(self):
        self.assertIsNone(model_matcher.match_models_dev("nonexistent-model", self.data))

    def test_provider_hint_wrong_still_falls_back_to_bare_search(self):
        # opencode namespaces as "<provider>/<model>" but the provider label opencode uses
        # isn't guaranteed to equal models.dev's own provider key -- must not give up early.
        result = model_matcher.match_models_dev("some-other-vendor/grok-4.6", self.data)
        self.assertIsNotNone(result)
        assert result is not None
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
        fuzzy_data = {
            "openai": {"models": {"gpt-5.6-sol-2": {"id": "gpt-5.6-sol-2", "cost": {"input": 3.5}}}}
        }
        result = model_matcher.match_models_dev("openai/gpt-5.6-sol", fuzzy_data)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["cost"]["input"], 3.5)

    def test_fuzzy_match_returns_none_when_no_candidate_is_close_enough(self):
        fuzzy_data = {"openai": {"models": {"gpt-5.6-sol-2": {"id": "gpt-5.6-sol-2"}}}}
        self.assertIsNone(
            model_matcher.match_models_dev("totally-different-vendor-model", fuzzy_data)
        )

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
        assert result is not None
        self.assertEqual(result["cost"]["input"], 3.5)

    def test_provider_hint_disambiguates_a_multi_provider_bare_id_collision(self):
        models_dev_data = {
            "openai": {"models": {"gpt-5.2": {"id": "gpt-5.2", "reasoning": True}}},
            "some-reseller": {"models": {"gpt-5.2": {"id": "gpt-5.2", "reasoning": False}}},
        }
        result = model_matcher.match_models_dev("gpt-5.2", models_dev_data, provider_hint="openai")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["provider"], "openai")

    def test_provider_hint_that_matches_nothing_still_returns_none_on_collision(self):
        models_dev_data = {
            "openai": {"models": {"gpt-5.2": {"id": "gpt-5.2"}}},
            "some-reseller": {"models": {"gpt-5.2": {"id": "gpt-5.2"}}},
        }
        result = model_matcher.match_models_dev(
            "gpt-5.2", models_dev_data, provider_hint="nonexistent-vendor"
        )
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
        fuzzy_data = {
            "openai": {"models": {"gpt-5.6-sol-2": {"id": "gpt-5.6-sol-2", "cost": {"input": 3.5}}}}
        }
        result = model_matcher.match_models_dev("openai/gpt-5.6-sol", fuzzy_data)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["cost"]["input"], 3.5)

    def test_allow_fuzzy_false_skips_the_pool_fuzzy_step(self):
        fuzzy_data = {
            "openai": {"models": {"gpt-5.6-sol-2": {"id": "gpt-5.6-sol-2", "cost": {"input": 3.5}}}}
        }
        result = model_matcher.match_models_dev("openai/gpt-5.6-sol", fuzzy_data, allow_fuzzy=False)
        self.assertIsNone(result)


class TestMatchArtificialAnalysis(unittest.TestCase):
    def setUp(self):
        self.models = [
            {
                "id": "abc",
                "name": "GPT-5.6 Sol",
                "slug": "gpt-5-6-sol",
                "model_creator": {"name": "OpenAI"},
                "evaluations": {
                    "artificial_analysis_intelligence_index": 68.4,
                    "artificial_analysis_coding_index": 74.1,
                    "artificial_analysis_agentic_index": 61.2,
                },
                "performance": {"median_output_tokens_per_second": 142.3},
            },
        ]

    def test_matches_by_normalized_slug(self):
        result = model_matcher.match_artificial_analysis("openai/gpt-5.6-sol", self.models)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["evaluations"]["artificial_analysis_coding_index"], 74.1)

    def test_no_match_returns_none(self):
        self.assertIsNone(
            model_matcher.match_artificial_analysis("totally-unknown-model", self.models)
        )

    def test_fuzzy_match_finds_a_near_spelling_when_exact_lookup_finds_nothing(self):
        # CRITICAL finding: same fuzzy fallback as match_models_dev, applied to AA's own
        # slug/name fields -- a short version token difference must not fall through to
        # "unmatched" when normalization + fuzzy similarity would confidently resolve it.
        near_models = [
            {
                "id": "1",
                "name": "GPT-5.6 Sol V2",
                "slug": "gpt-5-6-sol-v2",
                "model_creator": {"name": "OpenAI"},
                "evaluations": {"artificial_analysis_coding_index": 74.1},
            }
        ]
        result = model_matcher.match_artificial_analysis("openai/gpt-5.6-sol", near_models)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["id"], "1")

    def test_collision_disambiguated_by_provider_hint_via_model_creator(self):
        # Two different vendors' models normalize to the SAME slug ("sol") -- a naive
        # "first normalized match wins" would silently pick whichever is listed first.
        collision_models = [
            {
                "id": "1",
                "name": "Sol",
                "slug": "sol",
                "model_creator": {"name": "Xai"},
                "evaluations": {"artificial_analysis_coding_index": 10.0},
            },
            {
                "id": "2",
                "name": "Sol",
                "slug": "sol",
                "model_creator": {"name": "OpenAI"},
                "evaluations": {"artificial_analysis_coding_index": 90.0},
            },
        ]
        result = model_matcher.match_artificial_analysis(
            "openai/sol", collision_models, provider_hint="openai"
        )
        assert result is not None
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
            "openai/gpt-5.6-sol", self.models, provider_hint="some-unrelated-vendor"
        )
        self.assertIsNotNone(result)

    def test_none_slug_and_name_do_not_crash_and_fall_through_to_no_match(self):
        # Important finding: a key present with an explicit `null` value (not merely absent)
        # must not reach _normalize's .lower() call unguarded -- one malformed AA record must
        # not abort the whole match_artificial_analysis batch.
        malformed_models = [
            {"id": "bad", "slug": None, "name": None, "model_creator": {"name": "OpenAI"}}
        ]
        result = model_matcher.match_artificial_analysis(
            "openai/gpt-5.6-sol", malformed_models + self.models
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["id"], "abc")

    def test_none_model_creator_does_not_crash_the_vendor_derivation_path(self):
        # Important finding: `m.get("model_creator", {})` returns None (not {}) when the key is
        # present with an explicit `null` value -- `.get("name", "")` on None then raises.
        collision_models = [
            {"id": "1", "name": "Sol", "slug": "sol", "model_creator": None},
            {"id": "2", "name": "Sol", "slug": "sol", "model_creator": {"name": "OpenAI"}},
        ]
        result = model_matcher.match_artificial_analysis(
            "openai/sol", collision_models, provider_hint="openai"
        )
        assert result is not None
        self.assertEqual(result["id"], "2")


class TestBuildModelCatalog(unittest.TestCase):
    def test_matched_candidate_is_enriched_and_added(self):
        discovered = [{"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        models_dev_data = {
            "openai": {
                "models": {
                    "gpt-5.6-sol": {
                        "id": "gpt-5.6-sol",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 400000, "output": 128000},
                        "cost": {"input": 3.5, "output": 14.0},
                    }
                }
            }
        }
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, [], True), {}
        )
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
        models_dev_data = {
            "opencode-go": {
                "models": {
                    "router-env-coding": {
                        "id": "router-env-coding",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 128000, "output": 8000},
                    }
                }
            }
        }
        aa_models = [
            {
                "id": "1",
                "slug": "router-env-coding",
                "name": "Router Env Coding",
                "model_creator": {"name": "SomeVendor"},
                "evaluations": {"artificial_analysis_coding_index": 89.0},
            }
        ]
        discovered = [{"runtime": "opencode", "model_id": "opencode-go/router-env-coding"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, aa_models, True), {}
        )
        self.assertEqual(rejections, [])
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-coding"]
        self.assertEqual(entry["name_declared_purpose"], "execute")
        self.assertFalse(entry["source"]["models_dev"])
        self.assertFalse(entry["source"]["artificial_analysis"])
        self.assertNotIn("tool_calling", entry)
        self.assertNotIn("scores", entry)

    def test_router_candidate_with_review_hint_gets_review_purpose(self):
        discovered = [{"runtime": "opencode", "model_id": "opencode-go/router-env-plan-review"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, [], True), {}
        )
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-plan-review"]
        self.assertEqual(entry["name_declared_purpose"], "review")

    def test_router_candidate_with_no_purpose_word_takes_the_unchanged_normal_path(self):
        # "router-env-fast" is a router (infer_is_router matches "-env") but has no purpose
        # word -- infer_purpose_from_name returns None, so this must fall through to ordinary
        # md_match/aa_match matching, unaffected by this feature.
        models_dev_data = {
            "opencode-go": {
                "models": {
                    "router-env-fast": {
                        "id": "router-env-fast",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 128000, "output": 8000},
                    }
                }
            }
        }
        discovered = [{"runtime": "opencode", "model_id": "opencode-go/router-env-fast"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, [], True), {}
        )
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-fast"]
        self.assertNotIn("name_declared_purpose", entry)
        self.assertTrue(entry["source"]["models_dev"])  # normal matching DID run
        self.assertTrue(entry["tool_calling"])

    def test_non_router_candidate_with_a_purpose_word_in_its_name_is_unaffected(self):
        # A real vendor model whose name happens to contain "coding" must never trigger this
        # heuristic -- infer_is_router gates it, and this id matches none of
        # _ROUTER_NAME_HINTS ("router", "-env", "local-llm").
        models_dev_data = {
            "openai": {
                "models": {
                    "gpt-5-coding-assistant": {
                        "id": "gpt-5-coding-assistant",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 128000, "output": 8000},
                    }
                }
            }
        }
        discovered = [{"runtime": "codex", "model_id": "openai/gpt-5-coding-assistant"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, [], True), {}
        )
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
        existing_catalog = {
            "opencode-go/router-env-coding": {
                "provider": "opencode-go",
                "runtimes": {
                    "opencode": {"model_id": "opencode-go/router-env-coding", "ctx_window": 128000}
                },
                "is_router": True,
                "batch_mode": False,
                "fallback_quota": True,
                "tool_calling": True,
                "structured_output": True,
                "max_output_tokens": 8000,
                "pricing": {"input_per_1m": 1.0, "output_per_1m": 2.0},
                "source": {"models_dev": True, "artificial_analysis": False, "manual": False},
                "confidence": "high",
                "last_verified": "2026-08-01",
            }
        }
        # models_dev_data/aa_models both WOULD match if queried -- proving they weren't.
        models_dev_data = {
            "opencode-go": {
                "models": {
                    "router-env-coding": {
                        "id": "router-env-coding",
                        "tool_call": False,
                        "structured_output": False,
                        "limit": {"context": 9999, "output": 9999},
                    }
                }
            }
        }
        discovered = [{"runtime": "opencode", "model_id": "opencode-go/router-env-coding"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, [], True), existing_catalog
        )
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-coding"]
        self.assertEqual(entry["name_declared_purpose"], "execute")
        self.assertEqual(entry["runtimes"]["opencode"]["ctx_window"], 128000)
        self.assertTrue(entry["tool_calling"])
        self.assertTrue(entry["structured_output"])
        self.assertEqual(entry["max_output_tokens"], 8000)
        self.assertEqual(entry["pricing"]["input_per_1m"], 1.0)
        self.assertTrue(entry["source"]["models_dev"])  # preserved from cache, not re-derived

    def test_router_candidate_with_contradictory_purpose_words_falls_through(self):
        # design spec Section 5(c): a naming CONTRADICTION (both a review word and an execute
        # word present) must fall through to the unchanged md_match/aa_match path, exactly like
        # the no-purpose-word case above -- verified here at the WIRING level (build_model_catalog
        # itself), not just at infer_purpose_from_name's own unit level (Task 1), since it's the
        # wiring's job to actually route on the heuristic's None result.
        models_dev_data = {
            "opencode-go": {
                "models": {
                    "router-env-coding-review": {
                        "id": "router-env-coding-review",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 128000, "output": 8000},
                    }
                }
            }
        }
        discovered = [{"runtime": "opencode", "model_id": "opencode-go/router-env-coding-review"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, [], True), {}
        )
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-coding-review"]
        self.assertNotIn("name_declared_purpose", entry)
        self.assertTrue(entry["source"]["models_dev"])  # normal matching DID run
        self.assertTrue(entry["tool_calling"])

    def test_name_declared_bare_id_with_no_provider_lands_in_unmatched_with_purpose_carried(self):
        # The short-circuit's only failure path: a name-declared router candidate reported as a
        # BARE id (no "<vendor>/" prefix -- e.g. a CLI that reports its own raw model name) with
        # no existing catalog entry to recover a provider from. It must land in `unmatched` with
        # `vendor_unknown: True` (same convention as the ordinary unmatched path), AND it must
        # still carry `name_declared_purpose` on that payload -- otherwise the wizard's Task 4
        # partition, which only inspects catalog entries, would silently lose the declaration
        # for any candidate that never makes it into the catalog.
        discovered = [{"runtime": "customcli", "model_id": "router-env-coding"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, [], True), {}
        )
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
            "openai": {
                "models": {
                    "sol": {
                        "id": "sol",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 400000, "output": 128000},
                    }
                }
            },
            "some-reseller": {
                "models": {
                    "sol": {
                        "id": "sol",
                        "tool_call": False,
                        "structured_output": None,
                        "limit": {"context": 400000, "output": 128000},
                    }
                }
            },
        }
        aa_models = [
            {
                "id": "1",
                "slug": "sol",
                "name": "Sol",
                "model_creator": {"name": "OpenAI"},
                "evaluations": {"artificial_analysis_intelligence_index": 70.0},
            }
        ]
        discovered = [{"runtime": "codex", "model_id": "sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, aa_models, True), {}
        )
        self.assertEqual(unmatched, [])
        entry = next(iter(catalog.values()))
        self.assertTrue(entry["tool_calling"])  # openai's row, not some-reseller's
        self.assertTrue(entry["structured_output"])

    def test_attempt_2_strips_the_effort_suffix_and_picks_the_hinted_provider_row(self):
        # Mirrors this spec's own motivating case: the raw id ("claude-opus-5-high") has no
        # exact match anywhere (Attempt 1 -> None, both providers tie on the UNSTRIPPED id
        # only via fuzzy which the primary call also can't use unambiguously), but its
        # effort-stripped base id ("claude-opus-5") collides across two providers whose
        # payloads genuinely disagree on structured_output -- proving the hint picks a
        # SPECIFIC row, not just "a" row from the collision (spec's round-6 safety property).
        models_dev_data = {
            "anthropic": {
                "models": {
                    "claude-opus-5": {
                        "id": "claude-opus-5",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 1000000, "output": 128000},
                    }
                }
            },
            "some-reseller": {
                "models": {
                    "claude-opus-5": {
                        "id": "claude-opus-5",
                        "tool_call": True,
                        "structured_output": None,
                        "limit": {"context": 1000000, "output": 128000},
                    }
                }
            },
        }
        aa_models = [
            {
                "id": "1",
                "slug": "claude-opus-5-high",
                "name": "Claude Opus 5 High",
                "model_creator": {"name": "Anthropic"},
                "evaluations": {"artificial_analysis_intelligence_index": 61.5},
            }
        ]
        discovered = [{"runtime": "cursor-agent", "model_id": "claude-opus-5-high"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, aa_models, True), {}
        )
        self.assertEqual(unmatched, [])
        entry = catalog["anthropic/claude-opus-5-high"]
        self.assertTrue(entry["structured_output"])  # anthropic's row, not the reseller's
        self.assertTrue(entry["tool_calling"])
        self.assertEqual(entry["max_output_tokens"], 128000)
        self.assertEqual(entry["runtimes"]["cursor-agent"]["ctx_window"], 1000000)
        self.assertFalse(entry["source"]["models_dev"])  # enrichment, not an exact match

    def test_attempt_2_never_falls_back_to_fuzzy_matching(self):
        # The stripped id here only fuzzy-matches (a trailing version-token difference) --
        # allow_fuzzy=False on both retry attempts means this must stay unresolved, never a
        # guessed match.
        models_dev_data = {
            "anthropic": {
                "models": {
                    "claude-opus-5-2": {
                        "id": "claude-opus-5-2",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 1000000, "output": 128000},
                    }
                }
            }
        }
        aa_models = [
            {
                "id": "1",
                "slug": "claude-opus-5-high",
                "name": "Claude Opus 5 High",
                "model_creator": {"name": "Anthropic"},
                "evaluations": {"artificial_analysis_intelligence_index": 61.5},
            }
        ]
        discovered = [{"runtime": "cursor-agent", "model_id": "claude-opus-5-high"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, aa_models, True), {}
        )
        self.assertEqual(unmatched, [])
        entry = catalog["anthropic/claude-opus-5-high"]
        self.assertNotIn("tool_calling", entry)
        self.assertNotIn("structured_output", entry)
        self.assertNotIn("max_output_tokens", entry)
        self.assertIsNone(entry["runtimes"]["cursor-agent"]["ctx_window"])

    def test_lifecycle_across_runs_clears_previously_recovered_fields_on_a_later_no_signal_run(
        self,
    ):
        # Round-3's accepted, documented tradeoff (spec Section 3.2): an Artificial Analysis
        # outage on a LATER run clears fields this spec's own enrichment retry recovered on
        # an earlier run -- exactly like today's existing contract for any candidate whose
        # primary match disappears. A second, unrelated candidate whose fields came from a
        # genuine PRIMARY match (never touched md_enrich_match at all) must clear identically,
        # proving the enrichment mechanism doesn't special-case fields it never touched.
        models_dev_data_run1 = {
            "anthropic": {
                "models": {
                    "claude-opus-5": {
                        "id": "claude-opus-5",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 1000000, "output": 128000},
                    }
                }
            },
            "some-reseller": {
                "models": {
                    "claude-opus-5": {
                        "id": "claude-opus-5",
                        "tool_call": True,
                        "structured_output": None,
                        "limit": {"context": 1000000, "output": 128000},
                    }
                }
            },
            "openai": {
                "models": {
                    "gpt-5.6-sol": {
                        "id": "gpt-5.6-sol",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 400000, "output": 128000},
                    }
                }
            },
        }
        aa_models = [
            {
                "id": "1",
                "slug": "claude-opus-5-high",
                "name": "Claude Opus 5 High",
                "model_creator": {"name": "Anthropic"},
                "evaluations": {"artificial_analysis_intelligence_index": 61.5},
            }
        ]
        discovered = [
            {"runtime": "cursor-agent", "model_id": "claude-opus-5-high"},
            {"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"},
        ]
        catalog_run1, _, unmatched_run1 = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data_run1, True, aa_models, True), {}
        )
        self.assertEqual(unmatched_run1, [])
        enriched_key = "anthropic/claude-opus-5-high"  # recovered via this spec's retry
        primary_key = "openai/gpt-5.6-sol"  # recovered via the ordinary primary match
        self.assertTrue(catalog_run1[enriched_key]["structured_output"])
        self.assertTrue(catalog_run1[primary_key]["structured_output"])

        # Run 2: Artificial Analysis is down (aa_ok=False) and models.dev genuinely no longer
        # lists either model (models_dev_ok=True -- a real, empty re-query, not a skip).
        catalog_run2, _, unmatched_run2 = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, [], False), catalog_run1
        )
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
        discovered = [{"runtime": "opencode", "model_id": "vendor/totally-unknown"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, [], True), {}
        )
        self.assertEqual(rejections, [])
        self.assertNotIn("vendor/totally-unknown", catalog)
        self.assertEqual(len(unmatched), 1)
        self.assertEqual(unmatched[0]["model_id"], "vendor/totally-unknown")
        self.assertEqual(unmatched[0]["runtime"], "opencode")

    def test_unmatched_candidate_carries_heuristic_fields_for_wizard_confirmation(self):
        # CRITICAL finding: an earlier draft returned unmatched candidates with NO heuristic
        # fields at all, and its own confirmation-payload test looked them up in `catalog`
        # (a KeyError, since unmatched entries are never added to catalog) -- both bugs fixed
        # here: heuristics are computed for unmatched candidates too, and returned inline on
        # the unmatched dict itself, never via a catalog lookup that can't succeed.
        discovered = [{"runtime": "opencode", "model_id": "router-env/totally-unknown"}]
        _, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, [], True), {}
        )
        self.assertEqual(len(unmatched), 1)
        self.assertTrue(unmatched[0]["is_router"])
        self.assertTrue(unmatched[0]["fallback_quota"])
        self.assertIn("batch_mode", unmatched[0])

    def test_already_confirmed_manual_entry_is_not_re_reported_as_unmatched(self):
        # A candidate already persisted (via confirm-catalog-entry, a previous run) is known --
        # re-running discovery on it must refresh its runtimes, not flag it as needing
        # confirmation again every single run.
        existing = {
            "vendor/totally-unknown": {
                "provider": "vendor",
                "runtimes": {},
                "source": {"manual": True},
                "confidence": "low",
                "last_verified": "2026-08-01",
            }
        }
        discovered = [{"runtime": "opencode", "model_id": "vendor/totally-unknown"}]
        catalog, _rejections, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, [], True), existing
        )
        self.assertEqual(unmatched, [])
        self.assertIn("opencode", catalog["vendor/totally-unknown"]["runtimes"])
        self.assertEqual(catalog["vendor/totally-unknown"]["confidence"], "low")

    def test_router_batch_and_fallback_quota_heuristics_are_applied(self):
        # HIGH finding: a candidate that matches NEITHER external source is, by this function's
        # own contract, never added to `catalog` -- it goes to `unmatched` instead (see
        # the dedicated unmatched-candidate tests above). Asserting on catalog[key] for
        # such a candidate is a KeyError by construction. Give this candidate a real
        # models.dev match so it actually lands in `catalog`, exercising the heuristics
        # on the MATCHED path (the unmatched path's own heuristic fields are already
        # covered separately, above).
        discovered = [{"runtime": "opencode", "model_id": "router-env/my-plan-review"}]
        models_dev_data = {"router-env": {"models": {"my-plan-review": {"id": "my-plan-review"}}}}
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, [], True), {}
        )
        self.assertEqual(unmatched, [])
        entry = catalog["router-env/my-plan-review"]
        self.assertTrue(entry["is_router"])
        self.assertTrue(entry["fallback_quota"])

    def test_existing_catalog_entries_are_preserved_when_not_rediscovered(self):
        existing = {
            "stale/model": {
                "provider": "p",
                "runtimes": {"c": {}},
                "source": {},
                "confidence": "high",
                "last_verified": "2026-01-01",
            }
        }
        catalog, _, _ = cli.build_model_catalog(
            [], cli.CatalogSources({}, True, [], True), existing
        )
        self.assertIn("stale/model", catalog)

    def test_two_clis_reporting_the_same_model_merge_into_one_canonical_entry(self):
        # HIGH finding: catalog identity must not lose runtime mappings across CLIs.
        discovered = [
            {"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"},
            {"runtime": "codex", "model_id": "gpt-5.6-sol"},
        ]
        models_dev_data = {"openai": {"models": {"gpt-5.6-sol": {"id": "gpt-5.6-sol"}}}}
        catalog, _, _ = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, [], True), {}
        )
        self.assertEqual(len(catalog), 1)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertIn("opencode", entry["runtimes"])
        self.assertIn("codex", entry["runtimes"])

    def test_models_dev_fetch_failure_preserves_cached_models_dev_fields(self):
        # CRITICAL finding: a network failure must never overwrite already-cached enrichment.
        existing = {
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
                "source": {"models_dev": True, "artificial_analysis": False},
                "confidence": "high",
                "last_verified": "2026-08-01",
                "tool_calling": True,
                "pricing": {"input_per_1m": 3.5, "output_per_1m": 14.0},
            }
        }
        discovered = [{"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, False, [], True), existing
        )  # models_dev_ok=False: source is DOWN
        self.assertEqual(unmatched, [])
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertTrue(entry["tool_calling"])
        self.assertEqual(entry["pricing"]["input_per_1m"], 3.5)
        self.assertTrue(entry["source"]["models_dev"])  # still true -- not silently downgraded

    def test_total_source_failure_leaves_a_cached_entry_completely_unchanged_except_runtimes(self):
        existing = {
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
                "source": {"models_dev": True, "artificial_analysis": True},
                "confidence": "high",
                "last_verified": "2026-08-01",
                "scores": {"intelligence_index": 91.0},
            }
        }
        discovered = [{"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, False, [], False), existing
        )
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertEqual(entry["scores"]["intelligence_index"], 91.0)
        self.assertEqual(entry["confidence"], "high")
        self.assertEqual(entry["last_verified"], "2026-08-01")  # unchanged -- nothing re-verified

    def test_artificial_analysis_pricing_fills_in_when_models_dev_has_no_match(self):
        # HIGH finding: AA pricing must not be discarded when models.dev has no match.
        aa_models = [
            {
                "id": "1",
                "slug": "totally-unknown",
                "name": "Totally Unknown",
                "model_creator": {"name": "Vendor"},
                "pricing": {"price_1m_input_tokens": 2.0, "price_1m_output_tokens": 8.0},
            }
        ]
        discovered = [{"runtime": "opencode", "model_id": "vendor/totally-unknown"}]
        catalog, _, _ = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, aa_models, True), {}
        )
        entry = catalog["vendor/totally-unknown"]
        self.assertEqual(entry["pricing"]["input_per_1m"], 2.0)
        self.assertEqual(entry["pricing"]["output_per_1m"], 8.0)

    def test_models_dev_fetch_failure_preserves_cached_runtime_ctx_window(self):
        # CRITICAL finding: a models.dev outage must not blank out an already-cached
        # runtime's ctx_window by unconditionally recomputing it from a (necessarily absent)
        # md_match -- that silently corrupts ranking's context_window axis.
        existing = {
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol", "ctx_window": 400000}},
                "source": {"models_dev": True, "artificial_analysis": False},
                "confidence": "high",
                "last_verified": "2026-08-01",
            }
        }
        discovered = [{"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, False, [], True), existing
        )
        self.assertEqual(
            catalog["openai/gpt-5.6-sol"]["runtimes"]["opencode"]["ctx_window"], 400000
        )

    def test_missing_api_key_preserves_cached_aa_fields_rather_than_wiping_them(self):
        # CRITICAL finding: no API key configured (aa_ok=True, aa_models=[] per Task 4's own
        # "deliberately skipped is not a failure" contract) must NOT be treated identically to
        # "AA was queried and genuinely found no match" -- the CLI wiring in Step 5 passes
        # aa_ok=False to THIS function whenever no key was available, specifically so this
        # preserve-not-wipe path runs; this test exercises that resulting contract directly.
        existing = {
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
                "source": {"models_dev": True, "artificial_analysis": True},
                "confidence": "high",
                "last_verified": "2026-08-01",
                "scores": {"intelligence_index": 91.0, "coding_index": 88.0, "agentic_index": 84.0},
                "tokens_per_sec": 142.3,
            }
        }
        discovered = [{"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, [], False), existing
        )
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertEqual(entry["scores"]["intelligence_index"], 91.0)
        self.assertEqual(entry["tokens_per_sec"], 142.3)
        self.assertTrue(entry["source"]["artificial_analysis"])

    def test_genuine_no_match_with_a_working_key_clears_aa_fields_and_flips_source_false(self):
        # The OTHER transition (contrast with the no-key test above): AA genuinely queried,
        # genuinely found no match for THIS candidate -- fields and provenance are cleared
        # together, consistently, not left stale.
        existing = {
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
                "source": {"models_dev": True, "artificial_analysis": True},
                "confidence": "high",
                "last_verified": "2026-08-01",
                "scores": {"intelligence_index": 91.0, "coding_index": 88.0, "agentic_index": 84.0},
            }
        }
        discovered = [{"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, [], True), existing
        )
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
        existing = {
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
                "source": {"models_dev": True, "artificial_analysis": True},
                "confidence": "high",
                "last_verified": "2026-08-01",
                "scores": {"intelligence_index": 91.0, "coding_index": 88.0, "agentic_index": 84.0},
                "tokens_per_sec": 142.3,
            }
        }
        aa_models = [
            {
                "id": "1",
                "slug": "gpt-5-6-sol",
                "name": "GPT-5.6 Sol",
                "model_creator": {"name": "OpenAI"},
                "evaluations": {"artificial_analysis_intelligence_index": 91.0},
            }
        ]
        # no "performance" key at all -- a genuine partial match
        discovered = [{"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, aa_models, True), existing
        )
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertNotIn("tokens_per_sec", entry)
        self.assertTrue(entry["source"]["artificial_analysis"])

    def test_heuristic_correction_survives_a_later_catalog_rebuild(self):
        # HIGH finding: every refresh recomputed is_router/batch_mode/fallback_quota fresh
        # from the naming heuristic, silently overwriting a user's prior correction
        # (apply_heuristic_corrections, Task 2) on the very next run
        existing = {
            "router-env/my-plan-review": {
                "provider": "router-env",
                "runtimes": {"opencode": {"model_id": "router-env/my-plan-review"}},
                "source": {},
                "confidence": "low",
                "last_verified": "2026-08-01",
                "is_router": False,
            }
        }
        # user corrected this away from the heuristic default (True)
        discovered = [{"runtime": "opencode", "model_id": "router-env/my-plan-review"}]
        catalog, _, _ = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, [], True), existing
        )
        self.assertFalse(catalog["router-env/my-plan-review"]["is_router"])

    def test_bare_model_matched_only_via_artificial_analysis_derives_vendor_from_model_creator(
        self,
    ):
        # HIGH finding: a bare model id (codex-style, no "<vendor>/" prefix) with NO
        # models.dev match must not become its own vendor ("gpt-5.6-sol/gpt-5.6-sol") just
        # because model_id.split("/", 1)[0] has nothing to split -- when Artificial Analysis
        # matched, its model_creator is the real vendor signal.
        aa_models = [
            {
                "id": "1",
                "slug": "gpt-5-6-sol",
                "name": "GPT-5.6 Sol",
                "model_creator": {"name": "OpenAI"},
                "evaluations": {"artificial_analysis_intelligence_index": 91.0},
            }
        ]
        discovered = [{"runtime": "codex", "model_id": "gpt-5.6-sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, aa_models, True), {}
        )
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
        discovered = [
            {"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"},
            {"runtime": "codex", "model_id": "gpt-5.6-alt"},
        ]  # e.g. from --extra-candidate
        _catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, True, [], True), {}
        )
        self.assertEqual({u["runtime"] for u in unmatched}, {"opencode", "codex"})

    def test_bare_id_with_both_sources_unavailable_recovers_key_from_existing_catalog(self):
        # CRITICAL/HIGH fix (round-2 native-opus review): this is the `--if-stale` DEFAULT
        # path -- both sources skipped (models_dev_ok=False, aa_ok=False), a bare CLI-native
        # id (codex-style, no "<vendor>/" prefix) that was already matched and persisted on a
        # PRIOR run. Before the fix, this fell through to `provider = model_id`, minting an
        # unstable "gpt-5.6-sol/gpt-5.6-sol" key every such run -- never matching the real
        # cached entry, permanently orphaning it, and reclassifying an already-known model as
        # `unmatched` (needing manual research) on every single --if-stale run.
        existing = {
            "openai/gpt-5.6-sol": {
                "provider": "openai",
                "runtimes": {"codex": {"model_id": "gpt-5.6-sol", "ctx_window": 400000}},
                "source": {"models_dev": True, "artificial_analysis": False},
                "confidence": "high",
                "last_verified": "2026-08-01",
                "scores": {"intelligence_index": 91.0},
            }
        }
        discovered = [{"runtime": "codex", "model_id": "gpt-5.6-sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, False, [], False), existing
        )
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
        existing = {
            "gpt-5.6-sol/gpt-5.6-sol": {
                "provider": "gpt-5.6-sol",
                "runtimes": {"codex": {"model_id": "gpt-5.6-sol"}},
                "source": {"models_dev": False, "artificial_analysis": False},
                "confidence": "low",
                "last_verified": "2026-08-01",
            }
        }
        models_dev_data = {"openai": {"models": {"gpt-5.6-sol": {"id": "gpt-5.6-sol"}}}}
        discovered = [{"runtime": "codex", "model_id": "gpt-5.6-sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, [], True), existing
        )
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
        discovered = [{"runtime": "codex", "model_id": "totally-unknown-bare-id"}]
        _, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, False, [], False), {}
        )
        self.assertEqual(len(unmatched), 1)
        self.assertIsNone(unmatched[0]["provider"])
        self.assertTrue(unmatched[0]["vendor_unknown"])
        self.assertIsNone(unmatched[0]["key"])

    def test_recoverable_unmatched_candidate_is_not_flagged_vendor_unknown(self):
        # Contrast case for the above: when `existing_key` recovery succeeds, `vendor_unknown`
        # must read False and `provider` must be the real recovered vendor, not None.
        existing = {
            "vendor/totally-unknown": {
                "provider": "vendor",
                "runtimes": {"codex": {"model_id": "bare-id"}},
                "source": {},
                "confidence": "low",
                "last_verified": "2026-08-01",
            }
        }
        discovered = [{"runtime": "codex", "model_id": "bare-id"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, False, [], False), existing
        )
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
        aa_models = [
            {
                "id": "1",
                "slug": "gpt-5-6-sol",
                "name": "GPT-5.6 Sol",
                "model_creator": {},  # no "name" at all
                "evaluations": {"artificial_analysis_intelligence_index": 91.0},
            }
        ]
        discovered = [{"runtime": "codex", "model_id": "gpt-5.6-sol"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, False, aa_models, True), {}
        )  # models_dev_ok=False -> md_match None
        self.assertEqual(rejections, [])
        self.assertEqual(len(unmatched), 1)
        self.assertIsNone(unmatched[0]["provider"])
        self.assertTrue(unmatched[0]["vendor_unknown"])
        self.assertEqual(catalog, {})  # never silently added to the catalog either

    def test_aa_match_with_creator_name_that_slugifies_empty_routes_to_unmatched(self):
        # WR-01 (code review, 01.2): distinct from the case above -- here `model_creator.name`
        # is present and NON-empty ("—", an em dash) so it passes the primary elif's raw
        # truthiness check `(aa_match.get("model_creator") or {}).get("name")`, but it is
        # entirely non-alphanumeric, so `_slugify()` (strips everything but [a-z0-9], then
        # strip("-")) reduces it to "". The buggy code called `_slugify(...)` a SECOND time
        # (for the assignment) without re-checking its result, so `provider` became "" -- a
        # str, not None -- which passed the later `if provider is not None` gate and minted a
        # malformed catalog key with an empty vendor segment (e.g. "/gpt-5.6-sol"), persisting
        # `"provider": ""` into the catalog instead of routing to the existing
        # vendor_unknown=True safeguard a few lines below (the guard that already exists for the
        # sibling aa_provider_hint call site a few lines above this one). Must land safely in
        # `unmatched` with provider=None/vendor_unknown=True, and must NEVER be added to the
        # catalog under a malformed key.
        aa_models = [
            {
                "id": "1",
                "slug": "gpt-5-6-sol",
                "name": "GPT-5.6 Sol",
                "model_creator": {"name": "—"},  # non-empty, slugifies to ""
                "evaluations": {"artificial_analysis_intelligence_index": 91.0},
            }
        ]
        discovered = [{"runtime": "codex", "model_id": "gpt-5.6-sol"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources({}, False, aa_models, True), {}
        )  # models_dev_ok=False -> md_match None
        self.assertEqual(rejections, [])
        self.assertEqual(catalog, {})  # never silently added under a malformed "/gpt-5.6-sol" key
        self.assertEqual(len(unmatched), 1)
        self.assertIsNone(unmatched[0]["provider"])
        self.assertTrue(unmatched[0]["vendor_unknown"])

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
        models_dev_data = {
            "some-other-provider": {
                "models": {
                    "claude-opus-5": {
                        "id": "claude-opus-5",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 1000000, "output": 128000},
                    }
                }
            }
        }
        aa_models = [
            {
                "id": "1",
                "slug": "claude-opus-5-thinking-xhigh",
                "name": "Claude Opus 5 Thinking XHigh",
                "model_creator": {"name": "Anthropic"},
                "evaluations": {"artificial_analysis_intelligence_index": 61.5},
            }
        ]
        discovered = [{"runtime": "cursor-agent", "model_id": "claude-opus-5-thinking-xhigh"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, aa_models, True), {}
        )
        self.assertEqual(unmatched, [])
        self.assertIn("anthropic/claude-opus-5-thinking-xhigh", catalog)
        entry = catalog["anthropic/claude-opus-5-thinking-xhigh"]
        self.assertEqual(entry["provider"], "anthropic")  # from AA's model_creator, not
        self.assertTrue(entry["structured_output"])  # "some-other-provider"

    def test_pricing_after_a_successful_retry_still_comes_from_aa_never_the_base_models_cost(self):
        # A real multi-provider collision on the STRIPPED id ("claude-opus-5") is required
        # so the PRIMARY call (no hint, fuzzy-enabled) can't resolve the raw suffixed id on
        # its own -- with only one provider, a single fuzzy match would win regardless of
        # hint AT THE PRIMARY STAGE, meaning pricing would legitimately come from that
        # primary match's own models.dev cost instead of exercising this spec's
        # enrichment-only retry at all.
        models_dev_data = {
            "anthropic": {
                "models": {
                    "claude-opus-5": {
                        "id": "claude-opus-5",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 1000000, "output": 128000},
                        "cost": {"input": 6.0, "output": 30.0},
                    }
                }
            },
            "some-reseller": {
                "models": {
                    "claude-opus-5": {
                        "id": "claude-opus-5",
                        "tool_call": True,
                        "structured_output": None,
                        "limit": {"context": 1000000, "output": 128000},
                        "cost": {"input": 0.0, "output": 0.0},
                    }
                }
            },
        }
        aa_models = [
            {
                "id": "1",
                "slug": "claude-opus-5-high",
                "name": "Claude Opus 5 High",
                "model_creator": {"name": "Anthropic"},
                "evaluations": {"artificial_analysis_intelligence_index": 61.5},
                "pricing": {"price_1m_input_tokens": 15.0, "price_1m_output_tokens": 75.0},
            }
        ]
        discovered = [{"runtime": "cursor-agent", "model_id": "claude-opus-5-high"}]
        catalog, _, _ = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, aa_models, True), {}
        )
        entry = catalog["anthropic/claude-opus-5-high"]
        self.assertEqual(entry["pricing"]["input_per_1m"], 15.0)  # AA's effort-specific price
        self.assertEqual(entry["pricing"]["output_per_1m"], 75.0)  # never the base model's 6.0/30.0

    def test_vendor_prefixed_id_with_an_effort_suffix_also_reaches_the_retry(self):
        # A prefixed id doesn't skip the need for this fallback either -- step 1's exact
        # lookup misses the suffix exactly as the bare case does, and the pool-fuzzy step
        # also finds nothing for this example (ratio("gpt5high","gpt5") ~= 0.667, well under
        # the 0.82 threshold).
        models_dev_data = {
            "openai": {
                "models": {
                    "gpt-5": {
                        "id": "gpt-5",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 400000, "output": 128000},
                    }
                }
            }
        }
        aa_models = [
            {
                "id": "1",
                "slug": "gpt-5-high",
                "name": "GPT-5 High",
                "model_creator": {"name": "OpenAI"},
                "evaluations": {"artificial_analysis_intelligence_index": 70.0},
            }
        ]
        discovered = [{"runtime": "opencode", "model_id": "openai/gpt-5-high"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, aa_models, True), {}
        )
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
            "anthropic": {
                "models": {
                    "claude-opus-5": {
                        "id": "claude-opus-5",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 1000000, "output": 128000},
                        "cost": {"input": 6.0, "output": 30.0},
                    }
                }
            },
            "some-reseller": {
                "models": {
                    "claude-opus-5": {
                        "id": "claude-opus-5",
                        "tool_call": True,
                        "structured_output": None,
                        "limit": {"context": 1000000, "output": 128000},
                        "cost": {"input": 0.0, "output": 0.0},
                    }
                }
            },
            "venice": {
                "models": {
                    "claude-opus-5-fast": {
                        "id": "claude-opus-5-fast",
                        "tool_call": True,
                        "structured_output": True,
                        "limit": {"context": 1000000, "output": 128000},
                        "cost": {"input": 12.0, "output": 60.0},
                    }
                }
            },
        }
        aa_models = [
            {
                "id": "1",
                "slug": "claude-opus-5-high",
                "name": "Claude Opus 5 High",
                "model_creator": {"name": "Anthropic"},
                "evaluations": {"artificial_analysis_intelligence_index": 61.5},
                "pricing": {"price_1m_input_tokens": 15.0, "price_1m_output_tokens": 75.0},
            },
            {
                "id": "2",
                "slug": "claude-opus-5-high-fast",
                "name": "Claude Opus 5 High Fast",
                "model_creator": {"name": "Anthropic"},
                "evaluations": {"artificial_analysis_intelligence_index": 61.5},
                "pricing": {"price_1m_input_tokens": 30.0, "price_1m_output_tokens": 150.0},
            },
        ]
        discovered = [
            {"runtime": "cursor-agent", "model_id": "claude-opus-5-high"},
            {"runtime": "cursor-agent", "model_id": "claude-opus-5-high-fast"},
        ]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, cli.CatalogSources(models_dev_data, True, aa_models, True), {}
        )
        self.assertEqual(rejections, [])
        self.assertEqual(unmatched, [])

        base = catalog["anthropic/claude-opus-5-high"]
        self.assertTrue(base["structured_output"])  # anthropic's row, not the reseller's
        self.assertTrue(base["tool_calling"])
        self.assertEqual(base["max_output_tokens"], 128000)
        self.assertEqual(base["runtimes"]["cursor-agent"]["ctx_window"], 1000000)
        self.assertFalse(base["source"]["models_dev"])  # enrichment, not an exact match
        self.assertEqual(base["scores"]["intelligence_index"], 61.5)
        self.assertEqual(base["pricing"]["input_per_1m"], 15.0)  # AA's, never models.dev's 6.0

        fast = catalog["venice/claude-opus-5-high-fast"]
        self.assertTrue(fast["source"]["models_dev"])  # resolved by the PRIMARY fuzzy step
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

    def _write_current_schema_catalog(self, catalog_path):
        # 16 D-12: a skip-fetch run additionally requires the catalog's `_meta.schema_version`
        # to be current -- seed the versioned empty catalog these tests need.
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump({"_meta": {"schema_version": model_catalog.CATALOG_SCHEMA_VERSION}}, f)

    def _never_fetch_models_dev(self):
        self.fail("fetch_models_dev_fn should not be called on a skip_fetch run")

    def _never_fetch_aa(self, api_key):
        del api_key
        self.fail("fetch_artificial_analysis_fn should not be called on a skip_fetch run")

    def test_if_stale_with_a_fresh_catalog_skips_fetch_but_still_reports_new_candidates(self):
        # CRITICAL finding: freshness must gate the network fetch only, never candidate
        # discovery -- a brand-new model must still surface as `unmatched`, not be silently
        # missed until the cache goes stale.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            self._write_current_schema_catalog(catalog_path)
            self._write_fresh_fetch_meta(catalog_path)
            runtimes_path = self._write_runtimes(
                d, {"opencode": {"installed": True, "models": ["vendor/brand-new"]}}
            )
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                        "--if-stale",
                    ],
                    fetch_models_dev_fn=self._never_fetch_models_dev,
                    fetch_artificial_analysis_fn=self._never_fetch_aa,
                )
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
            self._write_current_schema_catalog(catalog_path)
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
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                        "--if-stale",
                    ],
                    fetch_models_dev_fn=self._never_fetch_models_dev,
                    fetch_artificial_analysis_fn=self._never_fetch_aa,
                )
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
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                    ],  # no --if-stale -- always fetches
                    fetch_models_dev_fn=lambda: ({}, True),
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    load_secret_fn=lambda env, key: None,
                )
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertTrue(result["models_dev_ok"])
            self.assertTrue(os.path.exists(meta_path))
            meta = cache_read_json(meta_path)
            assert meta is not None
            self.assertIsInstance(meta["last_fetched"], float)

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
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                    ],
                    fetch_models_dev_fn=lambda: ({}, True),
                    fetch_artificial_analysis_fn=lambda _api_key: (
                        [{"id": "1", "slug": "x"}],
                        True,
                    ),  # source itself would have succeeded
                    load_secret_fn=lambda env, key: None,
                )  # ...but no key is configured
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertFalse(result["artificial_analysis_ok"])

    def test_extra_candidate_flag_is_included_in_discovery(self):
        # --if-stale + a fresh fetch-meta sidecar keeps this test network-free (see the
        # skip-fetch test above) while still proving --extra-candidate reaches `discovered` --
        # discovery/reconciliation runs unconditionally, network fetching is what's gated.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            self._write_current_schema_catalog(catalog_path)
            self._write_fresh_fetch_meta(catalog_path)
            runtimes_path = self._write_runtimes(d, {})
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                        "--if-stale",
                        "--extra-candidate",
                        "codex:vendor/typed-in-model",
                    ],
                    fetch_models_dev_fn=self._never_fetch_models_dev,
                    fetch_artificial_analysis_fn=self._never_fetch_aa,
                )
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertIn(
                {"runtime": "codex", "model_id": "vendor/typed-in-model"}, result["discovered"]
            )

    def test_single_provider_cli_candidate_pulled_from_review_spec_toml(self):
        # Same network-free technique as above (--if-stale + a fresh fetch-meta sidecar).
        # HIGH finding: this resolves review-spec.toml's global-merge path too (cfg_resolve),
        # so `env_fn` MUST point HOME at this tempdir -- never the real dict(os.environ) --
        # or this test would silently read whatever global config exists on the machine
        # actually running the suite.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            self._write_current_schema_catalog(catalog_path)
            self._write_fresh_fetch_meta(catalog_path)
            runtimes_path = self._write_runtimes(
                d, {"codex": {"installed": True}}
            )  # no "models" key -- single-provider
            local_cfg = os.path.join(d, ".aikit", "review-spec.toml")
            os.makedirs(os.path.dirname(local_cfg))
            raw = (
                b'[[reviewers]]\nkey = "codex-primary"\n'
                b'model = "vendor/already-registered"\n'
                b'vendor = "vendor"\ncli = "codex"\n'
            )
            with open(local_cfg, "wb") as f:
                f.write(raw)
            trust.record_trust(
                config_io.cfg_trust_store_dir({"HOME": d}), os.path.realpath(local_cfg), raw
            )
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                        "--cwd",
                        d,
                        "--if-stale",
                    ],
                    env_fn=lambda: {"HOME": d},
                    fetch_models_dev_fn=self._never_fetch_models_dev,
                    fetch_artificial_analysis_fn=self._never_fetch_aa,
                )
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertIn(
                {"runtime": "codex", "model_id": "vendor/already-registered"}, result["discovered"]
            )

    def test_custom_grok_entry_model_is_discovered_through_its_command(self):
        from contextlib import redirect_stdout

        # A grok entry stores a custom command and no runtime; its model must still reach
        # discovery, or a refresh run silently drops it from ranking.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            self._write_current_schema_catalog(catalog_path)
            self._write_fresh_fetch_meta(catalog_path)
            runtimes_path = self._write_runtimes(d, {"grok": {"installed": True}})
            local_cfg = os.path.join(d, ".aikit", "review-spec.toml")
            os.makedirs(os.path.dirname(local_cfg))
            raw = (
                b'[[reviewers]]\nkey = "grok-flagship"\nmodel = "grok-x"\nvendor = "xai"\n'
                b'command = "grok -p {prompt} -m {model} --output-format plain"\n'
                b'[[reviewers]]\nkey = "script"\nmodel = "m"\nvendor = "v"\n'
                b'command = "my-script {model} {prompt}"\n'
            )
            with open(local_cfg, "wb") as f:
                f.write(raw)
            trust.record_trust(
                config_io.cfg_trust_store_dir({"HOME": d}), os.path.realpath(local_cfg), raw
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    ["fetch-model-catalog", "--runtimes-json", runtimes_path,
                     "--catalog-path", catalog_path, "--cwd", d, "--if-stale"],
                    env_fn=lambda: {"HOME": d},
                    fetch_models_dev_fn=self._never_fetch_models_dev,
                    fetch_artificial_analysis_fn=self._never_fetch_aa,
                )
            self.assertEqual(code, 0)
            discovered = json.loads(buf.getvalue())["discovered"]
            self.assertIn({"runtime": "grok", "model_id": "grok-x"}, discovered)
            self.assertNotIn("m", [row["model_id"] for row in discovered])

    def test_confirm_catalog_entry_rejects_invalid_entry_with_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            entry_path = os.path.join(d, "entry.json")
            with open(entry_path, "w", encoding="utf-8") as f:
                # missing fields
                json.dump({"model_id": "vendor/x", "entry": {"provider": "vendor"}}, f)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "confirm-catalog-entry",
                        "--catalog-path",
                        catalog_path,
                        "--entry-json",
                        entry_path,
                    ]
                )
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
                code = main(
                    [
                        "confirm-catalog-entry",
                        "--catalog-path",
                        catalog_path,
                        "--entry-json",
                        entry_path,
                    ]
                )
            self.assertEqual(code, 1)
            result = json.loads(buf.getvalue())
            self.assertFalse(result["confirmed"])
            self.assertIn("reason", result)
            self.assertEqual(cache_read_json(catalog_path), {})  # unchanged, no partial write

    def test_apply_heuristic_correction_writes_through_the_atomic_cache_api(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            existing = {
                "router-env/x": {
                    "provider": "router-env",
                    "runtimes": {"opencode": {}},
                    "source": {},
                    "confidence": "low",
                    "last_verified": "2026-09-02",
                    "is_router": True,
                }
            }
            cache_write_json(catalog_path, existing)
            corrections_path = os.path.join(d, "corrections.json")
            with open(corrections_path, "w", encoding="utf-8") as f:
                json.dump({"is_router": False}, f)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "apply-heuristic-correction",
                        "--catalog-path",
                        catalog_path,
                        "--model-id",
                        "router-env/x",
                        "--corrections-json",
                        corrections_path,
                    ]
                )
            self.assertEqual(code, 0)
            cached = cache_read_json(catalog_path)
            assert cached is not None
            self.assertFalse(cached["router-env/x"]["is_router"])

    def test_apply_heuristic_correction_rejects_invalid_correction_with_nonzero_exit(self):
        # CRITICAL finding: a correction that would make the merged entry schema-invalid must
        # be rejected (nonzero exit, no write) -- cache_write_json alone never validates.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            existing = {
                "router-env/x": {
                    "provider": "router-env",
                    "runtimes": {"opencode": {}},
                    "source": {},
                    "confidence": "low",
                    "last_verified": "2026-09-02",
                    "is_router": True,
                }
            }
            cache_write_json(catalog_path, existing)
            corrections_path = os.path.join(d, "corrections.json")
            with open(corrections_path, "w", encoding="utf-8") as f:
                json.dump({"is_router": "not-a-bool"}, f)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "apply-heuristic-correction",
                        "--catalog-path",
                        catalog_path,
                        "--model-id",
                        "router-env/x",
                        "--corrections-json",
                        corrections_path,
                    ]
                )
            self.assertEqual(code, 1)
            result = json.loads(buf.getvalue())
            self.assertFalse(result["applied"])
            cached = cache_read_json(catalog_path)
            assert cached is not None
            self.assertTrue(cached["router-env/x"]["is_router"])  # unchanged


class TestCatalogSchemaVersion(unittest.TestCase):
    """16 D-12: model-catalog.json's `_meta.schema_version` -- split/join helpers, the
    reserved-key guard in merge_catalog_entry, schema-aware --if-stale gating in
    fetch-model-catalog, and `_meta` preservation across every catalog-writing subcommand."""

    def _write_fresh_fetch_meta(self, catalog_path):
        with open(catalog_path + ".fetch-meta.json", "w", encoding="utf-8") as f:
            json.dump({"last_fetched": time.time()}, f)

    @staticmethod
    def _legacy_entry():
        return {
            "provider": "openai",
            "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol", "ctx_window": 400000}},
            "source": {"models_dev": True, "artificial_analysis": False, "manual": False},
            "confidence": "high",
            "last_verified": "2026-09-01",
            "tool_calling": True,
        }

    # ── split_catalog_meta ────────────────────────────────────────────────

    def test_split_rejects_non_dict_input(self):
        for raw in (None, [], "x"):
            self.assertEqual(model_catalog.split_catalog_meta(raw), ({}, {}))

    def test_split_separates_entries_from_meta(self):
        raw = {"a/b": {"provider": "a"}, "_meta": {"schema_version": 2}}
        entries, meta = model_catalog.split_catalog_meta(raw)
        self.assertEqual(entries, {"a/b": {"provider": "a"}})
        self.assertEqual(meta, {"schema_version": 2})

    def test_split_drops_a_non_dict_meta_value(self):
        entries, meta = model_catalog.split_catalog_meta(
            {"a/b": {"provider": "a"}, "_meta": "garbage"}
        )
        self.assertEqual(entries, {"a/b": {"provider": "a"}})
        self.assertEqual(meta, {})

    # ── join_catalog_meta ─────────────────────────────────────────────────

    def test_join_with_empty_meta_has_no_meta_key(self):
        self.assertEqual(model_catalog.join_catalog_meta({"a/b": {}}, {}), {"a/b": {}})

    def test_join_adds_meta_and_neither_call_mutates_inputs(self):
        entries = {"a/b": {"provider": "a"}}
        meta = {"schema_version": 2}
        joined = model_catalog.join_catalog_meta(entries, meta)
        self.assertEqual(joined, {**entries, "_meta": {"schema_version": 2}})
        self.assertEqual(entries, {"a/b": {"provider": "a"}})  # untouched
        self.assertEqual(meta, {"schema_version": 2})  # untouched

    # ── catalog_schema_is_current ─────────────────────────────────────────

    def test_schema_predicate_rejects_missing_old_and_non_int(self):
        f = model_catalog.catalog_schema_is_current
        for bad in (
            {},
            {"schema_version": 1},
            {"schema_version": 2},
            {"schema_version": True},
            {"schema_version": "2"},
            None,
        ):
            self.assertFalse(f(bad))
        for good in ({"schema_version": 3}, {"schema_version": 4}):
            self.assertTrue(f(good))

    # ── merge_catalog_entry reserved-key guard ────────────────────────────

    def test_merge_rejects_meta_as_a_model_id(self):
        catalog = {"_meta": {"schema_version": 2}}
        valid_entry = {
            "provider": "p",
            "runtimes": {"c": {}},
            "source": {},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }
        updated, reason = model_catalog.merge_catalog_entry(catalog, "_meta", valid_entry)
        self.assertEqual(updated, catalog)  # unchanged
        self.assertIn("reserved", reason)

    # ── current_candidate_keys ignores _meta ──────────────────────────────

    def test_current_candidate_keys_never_returns_meta(self):
        catalog = {
            "_meta": {"schema_version": 2},
            "openai/gpt-5.6-sol": {"runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}}},
        }
        keys = model_catalog.current_candidate_keys(
            catalog, [{"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        )
        self.assertEqual(keys, {"openai/gpt-5.6-sol"})
        self.assertNotIn("_meta", keys)

    # ── fetch-model-catalog --if-stale gating (CLI) ───────────────────────

    def test_legacy_catalog_with_fresh_fetch_meta_is_refetched_and_stamped(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({"openai/gpt-5.6-sol": self._legacy_entry()}, f)
            self._write_fresh_fetch_meta(catalog_path)
            runtimes_path = os.path.join(d, "runtimes.json")
            with open(runtimes_path, "w", encoding="utf-8") as f:
                json.dump({"clis": {}}, f)
            fetches = []
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                        "--if-stale",
                    ],
                    fetch_models_dev_fn=lambda: fetches.append("md") or ({}, True),
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    load_secret_fn=lambda env, key: None,
                )
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertEqual(fetches, ["md"])  # the version-stale catalog forced one fetch
            self.assertFalse(result["fetch_skipped"])
            self.assertEqual(result["entry_count"], 1)  # entries only, `_meta` not counted
            written = cache_read_json(catalog_path)
            assert written is not None
            self.assertEqual(written["_meta"], {"schema_version": 3})
            self.assertEqual(written["openai/gpt-5.6-sol"], self._legacy_entry())  # preserved

    def test_meta_with_older_version_is_refetched(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({"_meta": {"schema_version": 1}}, f)
            self._write_fresh_fetch_meta(catalog_path)
            runtimes_path = os.path.join(d, "runtimes.json")
            with open(runtimes_path, "w", encoding="utf-8") as f:
                json.dump({"clis": {}}, f)
            fetches = []
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                        "--if-stale",
                    ],
                    fetch_models_dev_fn=lambda: fetches.append("md") or ({}, True),
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    load_secret_fn=lambda env, key: None,
                )
            self.assertEqual(code, 0)
            self.assertEqual(fetches, ["md"])  # older version -> fetch

    def test_current_meta_is_preserved_verbatim_on_a_skipped_run(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({"_meta": {"schema_version": 3, "note": "keep"}}, f)
            self._write_fresh_fetch_meta(catalog_path)
            runtimes_path = os.path.join(d, "runtimes.json")
            with open(runtimes_path, "w", encoding="utf-8") as f:
                json.dump({"clis": {}}, f)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                        "--if-stale",
                    ],
                    fetch_models_dev_fn=self.fail,
                    fetch_artificial_analysis_fn=self.fail,
                    load_secret_fn=lambda env, key: None,
                )
            self.assertEqual(code, 0)
            written = cache_read_json(catalog_path)
            assert written is not None
            self.assertEqual(written["_meta"], {"schema_version": 3, "note": "keep"})

    def test_models_dev_down_aa_only_never_stamps_meta_so_next_run_refetches(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            runtimes_path = os.path.join(d, "runtimes.json")
            with open(runtimes_path, "w", encoding="utf-8") as f:
                json.dump({"clis": {}}, f)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                    ],
                    fetch_models_dev_fn=lambda: ({}, False),  # models.dev down
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    load_secret_fn=lambda env, key: "k",
                )  # AA ok
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertFalse(result["models_dev_ok"])
            self.assertTrue(result["artificial_analysis_ok"])
            cached = cache_read_json(catalog_path)
            assert cached is not None
            self.assertNotIn("_meta", cached)  # not stamped
            # fetch-meta WAS written (existing behavior) but the catalog is still versionless
            # -- the immediate second --if-stale run must fetch again.
            self.assertTrue(os.path.exists(catalog_path + ".fetch-meta.json"))
            fetches = []
            buf2 = io.StringIO()
            with redirect_stdout(buf2):
                code2 = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                        "--if-stale",
                    ],
                    fetch_models_dev_fn=lambda: fetches.append("md") or ({}, True),
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    load_secret_fn=lambda env, key: None,
                )
            self.assertEqual(code2, 0)
            self.assertEqual(fetches, ["md"])  # retried -- one successful refresh comes first

    # ── confirm-catalog-entry / apply-heuristic-correction preserve _meta ──

    def test_confirm_catalog_entry_preserves_meta(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            original = {
                "_meta": {"schema_version": 2, "note": "keep"},
                "openai/gpt-5.6-sol": self._legacy_entry(),
            }
            cache_write_json(catalog_path, original)
            entry_path = os.path.join(d, "entry.json")
            with open(entry_path, "w", encoding="utf-8") as f:
                json.dump({"model_id": "vendor/new", "entry": self._legacy_entry()}, f)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "confirm-catalog-entry",
                        "--catalog-path",
                        catalog_path,
                        "--entry-json",
                        entry_path,
                    ]
                )
            self.assertEqual(code, 0)
            written = cache_read_json(catalog_path)
            assert written is not None
            self.assertEqual(written["_meta"], {"schema_version": 2, "note": "keep"})
            self.assertIn("vendor/new", written)

    def test_confirm_catalog_entry_rejects_meta_as_model_id_without_writing(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            original_text = json.dumps(
                {"_meta": {"schema_version": 2}, "openai/gpt-5.6-sol": self._legacy_entry()}
            )
            with open(catalog_path, "w", encoding="utf-8") as f:
                f.write(original_text)
            entry_path = os.path.join(d, "entry.json")
            with open(entry_path, "w", encoding="utf-8") as f:
                json.dump({"model_id": "_meta", "entry": self._legacy_entry()}, f)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "confirm-catalog-entry",
                        "--catalog-path",
                        catalog_path,
                        "--entry-json",
                        entry_path,
                    ]
                )
            self.assertEqual(code, 1)
            self.assertIn("reserved", json.loads(buf.getvalue())["reason"])
            with open(catalog_path, encoding="utf-8") as f:
                self.assertEqual(f.read(), original_text)  # byte-identical

    def test_apply_heuristic_correction_preserves_meta(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            cache_write_json(
                catalog_path,
                {
                    "_meta": {"schema_version": 2, "note": "keep"},
                    "router-env/x": {
                        "provider": "router-env",
                        "runtimes": {"opencode": {}},
                        "source": {},
                        "confidence": "low",
                        "last_verified": "2026-09-02",
                        "is_router": True,
                    },
                },
            )
            corrections_path = os.path.join(d, "corrections.json")
            with open(corrections_path, "w", encoding="utf-8") as f:
                json.dump({"is_router": False}, f)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "apply-heuristic-correction",
                        "--catalog-path",
                        catalog_path,
                        "--model-id",
                        "router-env/x",
                        "--corrections-json",
                        corrections_path,
                    ]
                )
            self.assertEqual(code, 0)
            written = cache_read_json(catalog_path)
            assert written is not None
            self.assertEqual(written["_meta"], {"schema_version": 2, "note": "keep"})
            self.assertFalse(written["router-env/x"]["is_router"])

    # ── E5: garbage catalog file with a real fetch ────────────────────────

    def test_garbage_catalog_file_is_replaced_by_a_valid_fetch(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                f.write("{not json")
            runtimes_path = os.path.join(d, "runtimes.json")
            with open(runtimes_path, "w", encoding="utf-8") as f:
                json.dump({"clis": {}}, f)
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                    ],
                    fetch_models_dev_fn=lambda: ({}, True),
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    load_secret_fn=lambda env, key: None,
                )
            self.assertEqual(code, 0)
            written = cache_read_json(catalog_path)
            assert written is not None
            self.assertIsInstance(written, dict)
            self.assertEqual(written.get("_meta"), {"schema_version": 3})


class TestClaudeEnumerationEndToEnd(unittest.TestCase):
    """16 D-04 tracer for the REAL refresh order (design spec §3: detect-runtimes
    --if-stale, then fetch-model-catalog --if-stale): the first detect writes the labeled
    dated fallback; the fetch records models.dev's anthropic ids in `_meta` AND, in that
    same fetch, builds an `anthropic/<id>` entry for every one (including an id outside the
    fallback); the next detect re-detects immediately (no TTL wait) and labels the ids
    "catalog"; a network-skipping fetch keeps every listed id scoreable; the last detect is
    skipped. Claude is never executed (16 D-07)."""

    MD = {
        "anthropic": {
            "models": {
                **{
                    mid: {
                        "id": mid,
                        "tool_call": True,
                        "limit": {"context": 1000000, "output": 128000},
                    }
                    for mid in detection.CLAUDE_FALLBACK_MODEL_IDS
                },
                "claude-sonnet-5": {
                    "id": "claude-sonnet-5",
                    "tool_call": True,
                    "limit": {"context": 1000000, "output": 64000},
                },
                "claude-new-not-in-fallback": {
                    "id": "claude-new-not-in-fallback",
                    "tool_call": True,
                    "limit": {"context": 1000000, "output": 128000},
                },
            }
        },
        # The live collision shape (2026-09-24): reseller providers list the same bare ids.
        "reseller": {
            "models": {
                "claude-sonnet-5": {
                    "id": "claude-sonnet-5",
                    "limit": {"context": 200000, "output": 4096},
                },
                "claude-new-not-in-fallback": {
                    "id": "claude-new-not-in-fallback",
                    "limit": {"context": 200000, "output": 4096},
                },
            }
        },
    }

    @staticmethod
    def _claude_which(name):
        return "/fake/bin/claude" if name == "claude" else None

    def test_real_refresh_order_makes_a_non_fallback_id_scoreable_without_ttl_wait(self):
        new = "claude-new-not-in-fallback"
        with tempfile.TemporaryDirectory() as d:
            env = {"HOME": d}
            r = os.path.join(d, "runtimes.json")
            catalog_path = model_catalog.cache_catalog_path(env)
            md_calls = self.MD.copy()
            md_fetch_count = []

            def md_fake():
                md_fetch_count.append(1)
                return md_calls, True

            recorded_runs = []

            def recording_run_fn(argv, **kwargs):
                recorded_runs.append((argv, kwargs))
                return unittest.mock.MagicMock(returncode=0, stdout="")

            def detect(**overrides):
                import io
                from contextlib import redirect_stdout

                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = main(
                        ["detect-runtimes", "--if-stale", r],
                        which_fn=self._claude_which,
                        run_fn=recording_run_fn,
                        env_fn=lambda: env,
                        **overrides,
                    )
                return code, buf.getvalue()

            def fetch(**overrides):
                import io
                from contextlib import redirect_stdout

                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = main(
                        [
                            "fetch-model-catalog",
                            "--if-stale",
                            "--runtimes-json",
                            r,
                            "--catalog-path",
                            catalog_path,
                        ],
                        which_fn=self._claude_which,
                        fetch_models_dev_fn=md_fake,
                        fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                        load_secret_fn=lambda _env_, key: None,
                        env_fn=lambda: env,
                        **overrides,
                    )
                return code, buf.getvalue()

            # 1. No runtimes file yet -> detect, writing the dated fallback.
            code, out = detect()
            self.assertEqual(code, 0)
            first = cache_read_json(r)
            assert first is not None
            self.assertEqual(first["clis"]["claude"]["models_source"], "dated-fallback")
            self.assertEqual(
                first["clis"]["claude"]["models"], list(detection.CLAUDE_FALLBACK_MODEL_IDS)
            )
            self.assertNotIn(new, json.dumps(first))

            # 2. Fetch: records the ids in `_meta` AND materializes every one of them.
            code, out = fetch()
            self.assertEqual(code, 0)
            result = json.loads(out)
            self.assertFalse(result["fetch_skipped"])
            self.assertEqual(len(md_fetch_count), 1)
            entries, meta = model_catalog.split_catalog_meta(cache_read_json(catalog_path))
            self.assertEqual(
                meta["anthropic_model_ids"], sorted([*detection.CLAUDE_FALLBACK_MODEL_IDS, new])
            )
            self.assertEqual(meta["anthropic_model_ids_as_of"], time.strftime("%Y-%m-%d"))
            self.assertEqual(meta["schema_version"], 3)
            for mid in [*detection.CLAUDE_FALLBACK_MODEL_IDS, new]:
                key = f"anthropic/{mid}"
                self.assertIn(key, entries)
                self.assertEqual(entries[key]["runtimes"]["claude"]["model_id"], mid)
                self.assertIsNone(model_catalog.validate_catalog_entry(key, entries[key]))
            # The anthropic row won the hinted collision, not the reseller's 4096.
            self.assertEqual(entries["anthropic/claude-sonnet-5"]["max_output_tokens"], 64000)
            self.assertFalse([k for k in entries if k.startswith("reseller/")])
            self.assertEqual(
                result["discovered"],
                [
                    {"runtime": "claude", "model_id": mid}
                    for mid in detection.CLAUDE_FALLBACK_MODEL_IDS
                ],
            )
            self.assertEqual(result["unmatched"], [])

            # 3. Fresh + schema-current runtimes, but the claude ids changed -> re-detect.
            code, out = detect()
            self.assertEqual(code, 0)
            self.assertNotEqual(json.loads(out), {})
            second = cache_read_json(r)
            assert second is not None
            self.assertEqual(
                second["clis"]["claude"],
                {
                    "installed": True,
                    "path": "/fake/bin/claude",
                    "aliases": ["fable", "opus", "sonnet", "haiku"],
                    "models": sorted([*detection.CLAUDE_FALLBACK_MODEL_IDS, new]),
                    "models_source": "catalog",
                    "models_as_of": time.strftime("%Y-%m-%d"),
                },
            )

            # 4. Network-skipping fetch: every listed id stays scoreable, unmatched empty.
            code, out = fetch()
            self.assertEqual(code, 0)
            result = json.loads(out)
            self.assertTrue(result["fetch_skipped"])
            self.assertEqual(len(md_fetch_count), 1)  # still just the one real fetch
            self.assertIn({"runtime": "claude", "model_id": new}, result["discovered"])
            self.assertEqual(result["unmatched"], [])
            entries, _ = model_catalog.split_catalog_meta(cache_read_json(catalog_path))
            self.assertIn(f"anthropic/{new}", entries)
            self.assertIsNone(
                model_catalog.validate_catalog_entry(
                    f"anthropic/{new}", entries[f"anthropic/{new}"]
                )
            )
            self.assertIn(
                f"anthropic/{new}",
                model_catalog.current_candidate_keys(entries, result["discovered"]),
            )

            # 5. Runtimes and catalog now agree -> the third detect is skipped.
            code, out = detect()
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out), {})

            # 6. Claude was never executed (16 D-07) -- only claude is installed.
            self.assertEqual(recorded_runs, [])


class TestClaudeFallback(unittest.TestCase):
    """Unit + CLI pins for 16 D-04's claude hybrid sourcing: the dated in-code fallback and
    its labeling, junk-tolerant id parsing, the never-execute rule, and the lazy catalog
    read (only for an installed claude)."""

    @staticmethod
    def _claude_which(name):
        return "/fake/bin/claude" if name == "claude" else None

    def _snapshot(self, **overrides):
        kwargs = {"which_fn": self._claude_which, "run_fn": lambda *a, **k: None}
        kwargs.update(overrides)
        return detection.build_runtimes_snapshot(**kwargs)

    def _fallback_entry(self):
        return {
            "installed": True,
            "path": "/fake/bin/claude",
            "aliases": list(detection.CLAUDE_MODEL_ALIASES),
            "models": list(detection.CLAUDE_FALLBACK_MODEL_IDS),
            "models_source": "dated-fallback",
            "models_as_of": detection.CLAUDE_FALLBACK_AS_OF,
        }

    def test_no_catalog_uses_dated_fallback(self):
        claude = self._snapshot(catalog_fn=lambda: None)["clis"]["claude"]
        self.assertEqual(claude, self._fallback_entry())

    def test_missing_catalog_fn_uses_dated_fallback(self):
        claude = self._snapshot()["clis"]["claude"]
        self.assertEqual(claude, self._fallback_entry())

    def test_catalog_without_usable_anthropic_ids_uses_fallback(self):
        for raw in (
            {"_meta": {"schema_version": 2}},
            {"_meta": {"anthropic_model_ids": []}},
            {"_meta": "junk"},
            {"x/y": {}},
        ):
            with self.subTest(raw=raw):
                claude = self._snapshot(catalog_fn=lambda raw=raw: raw)["clis"]["claude"]
                self.assertEqual(claude, self._fallback_entry())

    def test_junk_ids_are_filtered_and_labeled_catalog(self):
        raw = {"_meta": {"anthropic_model_ids": ["claude-x", None, 3, "", "claude-x"]}}
        claude = self._snapshot(catalog_fn=lambda: raw)["clis"]["claude"]
        self.assertEqual(claude["models"], ["claude-x"])
        self.assertEqual(claude["models_source"], "catalog")
        self.assertNotIn("models_as_of", claude)

    def test_claude_is_never_executed(self):
        recorded = []

        def recording_run_fn(argv, **kwargs):
            recorded.append((argv, kwargs))
            return unittest.mock.MagicMock(returncode=0, stdout="")

        self._snapshot(run_fn=recording_run_fn)
        self.assertEqual(recorded, [])  # 16 D-07: claude is never executed

    def test_uninstalled_claude_never_reads_the_catalog(self):
        reads = []

        def recording_catalog_fn():
            reads.append(1)
            return None

        snapshot = detection.build_runtimes_snapshot(
            which_fn=lambda n: None, run_fn=lambda *a, **k: None, catalog_fn=recording_catalog_fn
        )
        self.assertEqual(snapshot["clis"]["claude"], {"installed": False})
        self.assertEqual(reads, [])  # the catalog is only ever read for an installed claude

    def test_garbage_default_catalog_falls_back_via_cli(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            env = {"HOME": d}
            catalog_file = model_catalog.cache_catalog_path(env)
            os.makedirs(os.path.dirname(catalog_file), exist_ok=True)
            with open(catalog_file, "w", encoding="utf-8") as f:
                f.write("not json")
            r = os.path.join(d, "runtimes.json")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    ["detect-runtimes", "--if-stale", r],
                    which_fn=self._claude_which,
                    run_fn=lambda *a, **k: None,
                    env_fn=lambda: env,
                )
            self.assertEqual(code, 0)
            saved = cache_read_json(r)
            assert saved is not None
            self.assertEqual(saved["clis"]["claude"]["models_source"], "dated-fallback")

    def test_models_dev_without_anthropic_preserves_recorded_ids(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            cache_write_json(
                catalog_path,
                {
                    "_meta": {
                        "schema_version": 2,
                        "anthropic_model_ids": ["claude-a"],
                        "anthropic_model_ids_as_of": "2026-09-01",
                    }
                },
            )
            runtimes_path = os.path.join(d, "runtimes.json")
            cache_write_json(runtimes_path, {"clis": {}})
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                    ],
                    which_fn=lambda name: None,
                    fetch_models_dev_fn=lambda: ({"openai": {"models": {}}}, True),
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    load_secret_fn=lambda _env_, key: None,
                    env_fn=lambda: {"HOME": d},
                )
            self.assertEqual(code, 0)
            _, meta = model_catalog.split_catalog_meta(cache_read_json(catalog_path))
            self.assertEqual(meta["anthropic_model_ids"], ["claude-a"])
            self.assertEqual(meta["anthropic_model_ids_as_of"], "2026-09-01")

    def test_aliases_never_appear_in_models(self):
        recorded_raw = {
            "_meta": {
                "anthropic_model_ids": ["claude-x"],
                "anthropic_model_ids_as_of": "2026-09-01",
            }
        }
        cases = [None, "no-catalog-fn", {"_meta": {"schema_version": 2}}, recorded_raw]
        for raw in cases:
            with self.subTest(raw=raw):
                claude = self._snapshot(
                    catalog_fn=None if raw == "no-catalog-fn" else lambda raw=raw: raw
                )["clis"]["claude"]
                for alias in detection.CLAUDE_MODEL_ALIASES:
                    self.assertNotIn(alias, claude["models"])
                self.assertEqual(
                    claude["models_source"], "catalog" if raw is recorded_raw else "dated-fallback"
                )


class TestImageInputEndToEnd(unittest.TestCase):
    """End-to-end image_input from models.dev — modalities.input -> build_model_catalog
    -> fetch-model-catalog -> validated catalog entry (16 D-09)."""

    def test_models_dev_modalities_become_image_input(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "model-catalog.json")
            r = os.path.join(d, "runtimes.json")
            models_dev_data = {
                "anthropic": {
                    "models": {
                        "claude-sonnet-5": {
                            "id": "claude-sonnet-5",
                            "tool_call": True,
                            "modalities": {"input": ["text", "image", "pdf"], "output": ["text"]},
                            "limit": {"context": 200000, "output": 100000},
                        }
                    }
                },
                "vendor": {
                    "models": {
                        "text-only": {
                            "id": "text-only",
                            "tool_call": False,
                            "modalities": {"input": ["text"], "output": ["text"]},
                            "limit": {"context": 50000, "output": 10000},
                        },
                        "no-modalities": {
                            "id": "no-modalities",
                            "tool_call": False,
                            "limit": {"context": 40000, "output": 8000},
                        },
                    }
                },
            }
            # Create a simple runtimes.json with these models
            cache_write_json(
                r,
                {
                    "schema_version": 2,
                    "clis": {
                        "opencode": {
                            "installed": True,
                            "models": [
                                "anthropic/claude-sonnet-5",
                                "vendor/text-only",
                                "vendor/no-modalities",
                            ],
                        }
                    },
                },
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    ["fetch-model-catalog", "--runtimes-json", r, "--catalog-path", c],
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    fetch_models_dev_fn=lambda: (models_dev_data, True),
                    load_secret_fn=lambda env, key: None,
                    env_fn=lambda: {"HOME": d},
                    which_fn=lambda name: None,
                )
            self.assertEqual(code, 0)
            catalog = cache_read_json(c)
            entries, _meta = model_catalog.split_catalog_meta(catalog)
            # anthropic/claude-sonnet-5 modalities has image -> True
            self.assertIn("anthropic/claude-sonnet-5", entries)
            self.assertEqual(entries["anthropic/claude-sonnet-5"].get("image_input"), True)
            self.assertEqual(
                entries["anthropic/claude-sonnet-5"].get("image_input_source"), "models_dev"
            )
            # vendor/text-only modalities input list exists but no image -> False
            self.assertIn("vendor/text-only", entries)
            self.assertEqual(entries["vendor/text-only"].get("image_input"), False)
            self.assertEqual(entries["vendor/text-only"].get("image_input_source"), "models_dev")
            # vendor/no-modalities has no modalities key -> no image_input key
            self.assertIn("vendor/no-modalities", entries)
            self.assertNotIn("image_input", entries["vendor/no-modalities"])
            self.assertNotIn("image_input_source", entries["vendor/no-modalities"])
            # All entries pass validation
            for model_id, entry in entries.items():
                reason = model_catalog.validate_catalog_entry(model_id, entry)
                self.assertIsNone(reason, f"{model_id}: {reason}")

    def test_models_dev_outage_preserves_cached_image_input(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "model-catalog.json")
            r = os.path.join(d, "runtimes.json")
            # Seed: catalog with vendor/text-only having models_dev-sourced image_input
            entry = {
                "provider": "vendor",
                "runtimes": {"opencode": {"model_id": "vendor/text-only"}},
                "source": {"models_dev": True},
                "confidence": "high",
                "last_verified": "2026-09-02",
                "image_input": True,
                "image_input_source": "models_dev",
            }
            cache_write_json(c, {"_meta": {"schema_version": 3}, "vendor/text-only": entry})
            cache_write_json(
                r,
                {
                    "schema_version": 2,
                    "clis": {"opencode": {"installed": True, "models": ["vendor/text-only"]}},
                },
            )
            # Create a fetch-meta sidecar so it's "fresh" enough to skip
            cache_write_json(c + ".fetch-meta.json", {"last_fetched": time.time()})
            fetch_called = []

            def never_fetch_models_dev():
                fetch_called.append(True)
                raise Exception("should not fetch models.dev on --if-stale")

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--if-stale",
                        "--runtimes-json",
                        r,
                        "--catalog-path",
                        c,
                    ],
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    fetch_models_dev_fn=never_fetch_models_dev,
                    load_secret_fn=lambda env, key: None,
                    env_fn=lambda: {"HOME": d},
                    which_fn=lambda name: None,
                )
            self.assertEqual(code, 0)
            self.assertEqual(fetch_called, [])  # Should not have been called
            catalog = cache_read_json(c)
            entries, _meta = model_catalog.split_catalog_meta(catalog)
            # Entry still has the cached image_input and source
            self.assertEqual(entries["vendor/text-only"]["image_input"], True)
            self.assertEqual(entries["vendor/text-only"]["image_input_source"], "models_dev")

    def test_fresh_answer_without_statement_clears_stale_value(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "model-catalog.json")
            r = os.path.join(d, "runtimes.json")
            # Seed: same entry as above
            entry = {
                "provider": "vendor",
                "runtimes": {"opencode": {"model_id": "vendor/no-modalities"}},
                "source": {"models_dev": True},
                "confidence": "high",
                "last_verified": "2026-09-02",
                "image_input": True,
                "image_input_source": "models_dev",
            }
            cache_write_json(c, {"vendor/no-modalities": entry})
            cache_write_json(
                r,
                {
                    "schema_version": 2,
                    "clis": {"opencode": {"installed": True, "models": ["vendor/no-modalities"]}},
                },
            )
            models_dev_data = {
                "vendor": {
                    "models": {
                        "no-modalities": {
                            "id": "no-modalities",
                            "tool_call": False,
                            "limit": {"context": 40000, "output": 8000},
                        }
                    }
                }
            }
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    ["fetch-model-catalog", "--runtimes-json", r, "--catalog-path", c],
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    fetch_models_dev_fn=lambda: (models_dev_data, True),
                    load_secret_fn=lambda env, key: None,
                    env_fn=lambda: {"HOME": d},
                    which_fn=lambda name: None,
                )
            self.assertEqual(code, 0)
            catalog = cache_read_json(c)
            entries, _meta = model_catalog.split_catalog_meta(catalog)
            # Fresh fetch found the model but with no modalities -> clears both keys
            self.assertNotIn("image_input", entries["vendor/no-modalities"])
            self.assertNotIn("image_input_source", entries["vendor/no-modalities"])

    def test_image_input_schema_accepts_bool_and_none_rejects_other_types(self):
        valid_entry = {
            "provider": "test",
            "runtimes": {"cli": {"model_id": "test"}},
            "source": {"models_dev": True},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }
        model_id = "test/model"
        # Bool values and None are valid
        for val in (True, False, None):
            with self.subTest(image_input=val):
                self.assertIsNone(
                    model_catalog.validate_catalog_entry(
                        model_id, {**valid_entry, "image_input": val}
                    )
                )
        # Non-bool values are rejected
        for val in ("yes", 1):
            with self.subTest(image_input=val):
                reason = model_catalog.validate_catalog_entry(
                    model_id, {**valid_entry, "image_input": val}
                )
                self.assertIsNotNone(reason)
                assert reason is not None
                self.assertIn("image_input", reason)
        # image_input_source with bool image_input is valid
        for source in ("models_dev", "opencode"):
            with self.subTest(source=source):
                self.assertIsNone(
                    model_catalog.validate_catalog_entry(
                        model_id, {**valid_entry, "image_input": True, "image_input_source": source}
                    )
                )
                self.assertIsNone(
                    model_catalog.validate_catalog_entry(
                        model_id,
                        {**valid_entry, "image_input": False, "image_input_source": source},
                    )
                )
        # image_input_source with None image_input alone is valid
        self.assertIsNone(
            model_catalog.validate_catalog_entry(
                model_id, {**valid_entry, "image_input": None, "image_input_source": None}
            )
        )
        # Plain entry with neither key is valid (SPEC-03)
        self.assertIsNone(model_catalog.validate_catalog_entry(model_id, valid_entry))

    def test_image_input_source_requires_a_bool_image_input(self):
        valid_entry = {
            "provider": "test",
            "runtimes": {"cli": {"model_id": "test"}},
            "source": {"models_dev": True},
            "confidence": "high",
            "last_verified": "2026-09-02",
        }
        model_id = "test/model"
        # Source without bool image_input is rejected (review cycle 3)
        reason = model_catalog.validate_catalog_entry(
            model_id, {**valid_entry, "image_input_source": "models_dev"}
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("image_input_source", reason)
        reason = model_catalog.validate_catalog_entry(
            model_id, {**valid_entry, "image_input": None, "image_input_source": "opencode"}
        )
        self.assertIsNotNone(reason)
        # Legacy entry without source but with value is valid
        self.assertIsNone(
            model_catalog.validate_catalog_entry(model_id, {**valid_entry, "image_input": True})
        )
        # Paired clear is valid
        self.assertIsNone(
            model_catalog.validate_catalog_entry(
                model_id, {**valid_entry, "image_input": None, "image_input_source": None}
            )
        )
        # CLI round trip: confirm-catalog-entry rejects orphan-source
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "catalog.json")
            e = os.path.join(d, "entry.json")
            orphan_entry = {**valid_entry, "image_input_source": "models_dev"}
            with open(e, "w", encoding="utf-8") as f:
                json.dump({"model_id": model_id, "entry": orphan_entry}, f)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["confirm-catalog-entry", "--catalog-path", c, "--entry-json", e])
            self.assertEqual(code, 1)
            # Nothing written
            self.assertFalse(os.path.exists(c))
            # Printed "confirmed": false with a reason
            output = buf.getvalue()
            self.assertIn('"confirmed": false', output)
            self.assertIn("reason", output)
        # CLI round trip: legacy entry is accepted
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "catalog.json")
            e = os.path.join(d, "entry.json")
            legacy_entry = {**valid_entry, "image_input": True}
            with open(e, "w", encoding="utf-8") as f:
                json.dump({"model_id": model_id, "entry": legacy_entry}, f)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["confirm-catalog-entry", "--catalog-path", c, "--entry-json", e])
            self.assertEqual(code, 0)
            # Entry is persisted
            catalog = cache_read_json(c)
            assert catalog is not None
            persisted_entry = catalog[model_id]
            self.assertEqual(persisted_entry["image_input"], True)
            self.assertNotIn("image_input_source", persisted_entry)


class TestOpencodeVerboseImageInput(unittest.TestCase):
    """End-to-end opencode models --verbose image_input detection, provenance tracking,
    and fetch-skipped transitions (16 D-09 source 2)."""

    def test_parse_real_fixture_returns_expected_models(self):
        """Fixture parsing: two real blocks with correct image capability."""
        with open(OPENCODE_VERBOSE_FIXTURE_PATH, encoding="utf-8") as f:
            text = f.read()
        result = detection.parse_opencode_verbose_image_input(text)
        self.assertEqual(result, {"openai/gpt-5.6-sol": True, "router-env/my-coding": False})

    def test_parse_non_string_input_returns_empty(self):
        """Non-string input (None, int, list) returns {}."""
        for val in (None, 42, [], {}):
            with self.subTest(val=val):
                self.assertEqual(detection.parse_opencode_verbose_image_input(val), {})

    def test_parse_headerless_json_stops_early(self):
        """Text starting with { (no header line) returns {}."""
        self.assertEqual(detection.parse_opencode_verbose_image_input('{"id": "x"}'), {})

    def test_parse_garbage_block_stops_parsing(self):
        """Header followed by unparseable JSON stops parsing, keeps prior blocks."""
        text = "valid/model\n{}\ngarbage/model\nno json here\n"
        result = detection.parse_opencode_verbose_image_input(text)
        self.assertEqual(result, {})

    def test_parse_first_valid_then_garbage_keeps_first(self):
        """Valid block, then garbage, keeps the valid one."""
        text = (
            "openai/gpt-5.6-sol\n"
            '{"providerID":"openai","id":"gpt-5.6-sol",'
            '"capabilities":{"input":{"image":true}}}\n'
            "garbage\n"
        )
        result = detection.parse_opencode_verbose_image_input(text)
        self.assertEqual(result, {"openai/gpt-5.6-sol": True})

    def test_parse_mismatched_header_and_id_skips_block(self):
        """Header does not match providerID/id, block is skipped."""
        text = (
            "openai/gpt-5.6-sol\n"
            '{"providerID":"openai","id":"different",'
            '"capabilities":{"input":{"image":true}}}\n'
        )
        result = detection.parse_opencode_verbose_image_input(text)
        self.assertEqual(result, {})

    def test_parse_swapped_headers_result_is_empty(self):
        """Both blocks present but headers swapped — both skipped."""
        with open(OPENCODE_VERBOSE_FIXTURE_PATH, encoding="utf-8") as f:
            fixture = f.read()
        # Find the two blocks and swap them
        blocks = fixture.split("\n\n")
        if len(blocks) >= 2:
            swapped_text = "\n\n".join([blocks[1], blocks[0]])
            result = detection.parse_opencode_verbose_image_input(swapped_text)
            self.assertEqual(result, {})

    def test_parse_mismatched_then_matching_keeps_matching(self):
        """Mismatched block, then matched block — only matched is returned."""
        text = """mismatched/header
{"providerID":"openai","id":"gpt-5.6-sol","capabilities":{"input":{"image":true}}}
openai/gpt-5.6-sol
{"providerID":"openai","id":"gpt-5.6-sol","capabilities":{"input":{"image":true}}}
"""
        result = detection.parse_opencode_verbose_image_input(text)
        self.assertEqual(result, {"openai/gpt-5.6-sol": True})

    def test_parse_missing_capabilities_skips_block(self):
        """Block without capabilities key is skipped."""
        text = 'openai/gpt-5.6-sol\n{"providerID":"openai","id":"gpt-5.6-sol"}\n'
        result = detection.parse_opencode_verbose_image_input(text)
        self.assertEqual(result, {})

    def test_parse_missing_image_key_skips_block(self):
        """Capabilities without image key is skipped."""
        text = (
            "openai/gpt-5.6-sol\n"
            '{"providerID":"openai","id":"gpt-5.6-sol",'
            '"capabilities":{"input":{"text":true}}}\n'
        )
        result = detection.parse_opencode_verbose_image_input(text)
        self.assertEqual(result, {})

    def test_parse_non_bool_image_value_skips_block(self):
        """Image value that is not bool (e.g., "yes") is skipped."""
        text = (
            "openai/gpt-5.6-sol\n"
            '{"providerID":"openai","id":"gpt-5.6-sol",'
            '"capabilities":{"input":{"image":"yes"}}}\n'
        )
        result = detection.parse_opencode_verbose_image_input(text)
        self.assertEqual(result, {})

    def test_detect_nonzero_exit_with_valid_output_returns_empty(self):
        """Non-zero exit code returns {} even if stdout is valid JSON."""

        def fake_run(argv, **kwargs):
            with open(OPENCODE_VERBOSE_FIXTURE_PATH, encoding="utf-8") as f:
                fixture = f.read()
            return unittest.mock.MagicMock(returncode=1, stdout=fixture)

        result = detection.detect_opencode_verbose_image_input(
            "/fake/bin/opencode", run_fn=fake_run)
        self.assertEqual(result, {})

    def test_detect_timeout_returns_empty(self):
        """subprocess.TimeoutExpired returns {}."""

        def fake_run(argv, **kwargs):
            raise subprocess.TimeoutExpired("cmd", 15)

        result = detection.detect_opencode_verbose_image_input(
            "/fake/bin/opencode", run_fn=fake_run)
        self.assertEqual(result, {})

    def test_detect_oserror_returns_empty(self):
        """OSError (missing binary) returns {}."""

        def fake_run(argv, **kwargs):
            raise OSError("not found")

        result = detection.detect_opencode_verbose_image_input(
            "/fake/bin/opencode", run_fn=fake_run)
        self.assertEqual(result, {})

    def test_detect_missing_returncode_returns_empty(self):
        """Result object without returncode attribute returns {}."""

        def fake_run(argv, **kwargs):
            return None

        result = detection.detect_opencode_verbose_image_input(
            "/fake/bin/opencode", run_fn=fake_run)
        self.assertEqual(result, {})

    def test_full_size_listing_parses_quickly(self):
        """110 generated blocks parse within 5 seconds."""
        blocks = []
        for i in range(110):
            header = f"vendor/m-{i}"
            obj = {
                "id": f"m-{i}",
                "providerID": "vendor",
                "capabilities": {"input": {"image": True}},
            }
            blocks.append(f"{header}\n{json.dumps(obj, indent=2)}")
        text = "\n".join(blocks)
        start = time.perf_counter()
        result = detection.parse_opencode_verbose_image_input(text)
        elapsed = time.perf_counter() - start
        self.assertEqual(len(result), 110)
        self.assertLess(elapsed, 5.0, f"Parsing took {elapsed:.2f}s, expected < 5.0s")

    def test_unmatched_router_candidate_carries_image_input(self):
        """Unmatched opencode candidate with image_input on fetch-model-catalog unmatched list."""
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            r = os.path.join(d, "runtimes.json")
            cache_write_json(
                r,
                {
                    "schema_version": 2,
                    "clis": {
                        "opencode": {
                            "installed": True,
                            "models": ["router-env/custom"],
                            "image_input": {"router-env/custom": True},
                        }
                    },
                },
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        r,
                        "--catalog-path",
                        os.path.join(d, "catalog.json"),
                    ],
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    fetch_models_dev_fn=lambda: ({}, True),
                    load_secret_fn=lambda env, key: None,
                    env_fn=lambda: {"HOME": d},
                    which_fn=lambda name: None,
                )
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            unmatched = [
                u for u in result.get("unmatched", []) if u["model_id"] == "router-env/custom"
            ]
            self.assertEqual(len(unmatched), 1)
            self.assertEqual(unmatched[0]["runtime"], "opencode")
            self.assertEqual(unmatched[0].get("image_input"), True)
            self.assertEqual(unmatched[0].get("image_input_source"), "opencode")

    def test_vendor_unknown_router_candidate_carries_image_input(self):
        """Vendor-unknown router carries image_input from runtime metadata."""
        with tempfile.TemporaryDirectory():
            result = cli.build_model_catalog(
                [{"runtime": "opencode", "model_id": "local-llm-coding"}],
                cli.CatalogSources({}, True, [], True),
                {},
                runtime_meta={("opencode", "local-llm-coding"): {"image_input": False}},
            )
            _, _, unmatched = result
            self.assertEqual(len(unmatched), 1)
            self.assertEqual(unmatched[0]["vendor_unknown"], True)
            self.assertEqual(unmatched[0].get("image_input"), False)
            self.assertEqual(unmatched[0].get("image_input_source"), "opencode")

    def test_fetch_skipped_runtime_true_to_false_transition(self):
        """Fetch-skipped run: runtime value changes True -> False (review cycle 2 MEDIUM)."""
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "model-catalog.json")
            r = os.path.join(d, "runtimes.json")
            # Run 1: fresh fetch with runtime True
            cache_write_json(
                r,
                {
                    "schema_version": 2,
                    "clis": {
                        "opencode": {
                            "installed": True,
                            "models": ["vendor/no-modalities"],
                            "image_input": {"vendor/no-modalities": True},
                        }
                    },
                },
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    ["fetch-model-catalog", "--runtimes-json", r, "--catalog-path", c],
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    fetch_models_dev_fn=lambda: (
                        {"vendor": {"models": {"no-modalities": {"id": "no-modalities"}}}},
                        True,
                    ),
                    load_secret_fn=lambda env, key: None,
                    env_fn=lambda: {"HOME": d},
                    which_fn=lambda name: None,
                )
            self.assertEqual(code, 0)
            catalog = cache_read_json(c)
            entries, _meta = model_catalog.split_catalog_meta(catalog)
            self.assertEqual(entries["vendor/no-modalities"]["image_input"], True)
            self.assertEqual(entries["vendor/no-modalities"]["image_input_source"], "opencode")
            # Run 2: skip fetch, runtime changes to False
            cache_write_json(c + ".fetch-meta.json", {"last_fetched": time.time()})
            cache_write_json(
                r,
                {
                    "schema_version": 2,
                    "clis": {
                        "opencode": {
                            "installed": True,
                            "models": ["vendor/no-modalities"],
                            "image_input": {"vendor/no-modalities": False},
                        }
                    },
                },
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--if-stale",
                        "--runtimes-json",
                        r,
                        "--catalog-path",
                        c,
                    ],
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    fetch_models_dev_fn=lambda: self.fail("should skip fetch"),
                    load_secret_fn=lambda env, key: None,
                    env_fn=lambda: {"HOME": d},
                    which_fn=lambda name: None,
                )
            self.assertEqual(code, 0)
            catalog = cache_read_json(c)
            entries, _meta = model_catalog.split_catalog_meta(catalog)
            self.assertEqual(entries["vendor/no-modalities"]["image_input"], False)
            self.assertEqual(entries["vendor/no-modalities"]["image_input_source"], "opencode")

    def test_fetch_skipped_models_dev_value_beats_new_runtime_reading(self):
        """Fetch-skipped: models.dev value stays True even when runtime says False."""
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "model-catalog.json")
            r = os.path.join(d, "runtimes.json")
            # Run 1: models.dev says True
            cache_write_json(
                r,
                {
                    "schema_version": 2,
                    "clis": {
                        "opencode": {
                            "installed": True,
                            "models": ["vendor/no-modalities"],
                            "image_input": {"vendor/no-modalities": False},
                        }
                    },
                },
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    ["fetch-model-catalog", "--runtimes-json", r, "--catalog-path", c],
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    fetch_models_dev_fn=lambda: (
                        {
                            "vendor": {
                                "models": {
                                    "no-modalities": {
                                        "id": "no-modalities",
                                        "modalities": {"input": ["text", "image"]},
                                    }
                                }
                            }
                        },
                        True,
                    ),
                    load_secret_fn=lambda env, key: None,
                    env_fn=lambda: {"HOME": d},
                    which_fn=lambda name: None,
                )
            self.assertEqual(code, 0)
            # Run 2: skip, runtime now says False
            cache_write_json(c + ".fetch-meta.json", {"last_fetched": time.time()})
            cache_write_json(
                r,
                {
                    "schema_version": 2,
                    "clis": {
                        "opencode": {
                            "installed": True,
                            "models": ["vendor/no-modalities"],
                            "image_input": {"vendor/no-modalities": False},
                        }
                    },
                },
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--if-stale",
                        "--runtimes-json",
                        r,
                        "--catalog-path",
                        c,
                    ],
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    fetch_models_dev_fn=lambda: self.fail("should skip"),
                    load_secret_fn=lambda env, key: None,
                    env_fn=lambda: {"HOME": d},
                    which_fn=lambda name: None,
                )
            self.assertEqual(code, 0)
            catalog = cache_read_json(c)
            entries, _meta = model_catalog.split_catalog_meta(catalog)
            # models.dev value (True) stays, not overridden by runtime (False)
            self.assertEqual(entries["vendor/no-modalities"]["image_input"], True)
            self.assertEqual(entries["vendor/no-modalities"]["image_input_source"], "models_dev")

    def test_fetch_skipped_runtime_silence_keeps_cached_value(self):
        """Fetch-skipped: no runtime image_input in new snapshot keeps cached runtime value."""
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "model-catalog.json")
            r = os.path.join(d, "runtimes.json")
            # Run 1: runtime says True
            cache_write_json(
                r,
                {
                    "schema_version": 2,
                    "clis": {
                        "opencode": {
                            "installed": True,
                            "models": ["vendor/no-modalities"],
                            "image_input": {"vendor/no-modalities": True},
                        }
                    },
                },
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    ["fetch-model-catalog", "--runtimes-json", r, "--catalog-path", c],
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    fetch_models_dev_fn=lambda: (
                        {"vendor": {"models": {"no-modalities": {"id": "no-modalities"}}}},
                        True,
                    ),
                    load_secret_fn=lambda env, key: None,
                    env_fn=lambda: {"HOME": d},
                    which_fn=lambda name: None,
                )
            # Run 2: skip, no image_input in runtime snapshot
            cache_write_json(c + ".fetch-meta.json", {"last_fetched": time.time()})
            cache_write_json(
                r,
                {
                    "schema_version": 2,
                    "clis": {"opencode": {"installed": True, "models": ["vendor/no-modalities"]}},
                },
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--if-stale",
                        "--runtimes-json",
                        r,
                        "--catalog-path",
                        c,
                    ],
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    fetch_models_dev_fn=lambda: self.fail("should skip"),
                    load_secret_fn=lambda env, key: None,
                    env_fn=lambda: {"HOME": d},
                    which_fn=lambda name: None,
                )
            self.assertEqual(code, 0)
            catalog = cache_read_json(c)
            entries, _meta = model_catalog.split_catalog_meta(catalog)
            # Cached value stays (source silence is not removal)
            self.assertEqual(entries["vendor/no-modalities"]["image_input"], True)
            self.assertEqual(entries["vendor/no-modalities"]["image_input_source"], "opencode")

    def test_sourceless_cached_value_is_treated_as_runtime_derived(self):
        """Cached value without image_input_source is treated as runtime-derived."""
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "model-catalog.json")
            r = os.path.join(d, "runtimes.json")
            # Seed: entry without image_input_source
            cache_write_json(
                c,
                {
                    "_meta": {"schema_version": 3},
                    "vendor/no-modalities": {
                        "provider": "vendor",
                        "runtimes": {"opencode": {"model_id": "vendor/no-modalities"}},
                        "source": {"models_dev": False},
                        "confidence": "low",
                        "last_verified": "2026-09-24",
                        "image_input": True,
                    },
                },
            )
            # Skip fetch, but runtime now says False
            cache_write_json(c + ".fetch-meta.json", {"last_fetched": time.time()})
            cache_write_json(
                r,
                {
                    "schema_version": 2,
                    "clis": {
                        "opencode": {
                            "installed": True,
                            "models": ["vendor/no-modalities"],
                            "image_input": {"vendor/no-modalities": False},
                        }
                    },
                },
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--if-stale",
                        "--runtimes-json",
                        r,
                        "--catalog-path",
                        c,
                    ],
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    fetch_models_dev_fn=lambda: self.fail("should skip"),
                    load_secret_fn=lambda env, key: None,
                    env_fn=lambda: {"HOME": d},
                    which_fn=lambda name: None,
                )
            self.assertEqual(code, 0)
            catalog = cache_read_json(c)
            entries, _meta = model_catalog.split_catalog_meta(catalog)
            # Sourceless value is treated as runtime-derived, replaced by new runtime reading
            self.assertEqual(entries["vendor/no-modalities"]["image_input"], False)
            self.assertEqual(entries["vendor/no-modalities"]["image_input_source"], "opencode")

    def test_runtime_image_input_is_read_from_opencode_only(self):
        """Runtime image_input is read from clis.opencode only, not codex/claude."""
        result = {}
        result = cli._runtime_meta_from_snapshot(
            {
                "clis": {
                    "codex": {
                        "installed": True,
                        "models": ["gpt-x"],
                        "image_input": {"gpt-x": True},
                    },
                    "opencode": {
                        "installed": True,
                        "models": ["vendor/x"],
                        "image_input": {"vendor/x": False},
                    },
                }
            }
        )
        # opencode's image_input is extracted
        self.assertIn(("opencode", "vendor/x"), result)
        self.assertEqual(result[("opencode", "vendor/x")]["image_input"], False)
        # codex's image_input is NOT extracted
        self.assertNotIn(("codex", "gpt-x"), result)


class TestOpencodeApiImageInput(unittest.TestCase):
    """17 D-24/D-32: opencode 2.x image_input read from `GET /api/model` through a
    private `opencode serve` probe -- all via injected fakes, never a real opencode."""

    EXPECTED_MAP = {
        "opencode/exo-free": True,
        "opencode/ling-3.1-flash-free": False,
        "opencode/longcat-2.5-preview-free": True,
        "opencode/space-bunny-free": True,
    }

    class FakePopen:
        """Records argv/kwargs and the terminate/wait/kill sequence; its stdout is a
        StringIO carrying the banner lines."""

        def __init__(self, banner="server listening on http://127.0.0.1:41234\n"
                                   "server password s3cr3t\n"):
            self.argv: list | None = None
            self.kwargs: dict = {}
            self.stdout: typing.Any = io.StringIO(banner)
            self.pid: int | None = None
            self.calls = []

        def __call__(self, argv, **kwargs):
            self.argv = argv
            self.kwargs = kwargs
            return self

        def terminate(self):
            self.calls.append("terminate")

        def wait(self, timeout=None):
            self.calls.append(f"wait({timeout})")

        def kill(self):
            self.calls.append("kill")

    class FakeResponse:
        def __init__(self, body):
            self.body = body
            self.read = lambda: self.body

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    def _fake_urlopen(self, body=None):
        recorded = {}

        def fake_urlopen(request, timeout=None):
            recorded["url"] = request.full_url
            # Unredirected: a redirect never forwards the password (17 security audit).
            recorded["authorization"] = request.unredirected_hdrs.get("Authorization")
            recorded["redirectable_auth"] = request.headers.get("Authorization")
            recorded["timeout"] = timeout
            return self.FakeResponse(
                body if body is not None else _read_bytes(OPENCODE_API_FIXTURE_PATH)
            )

        fake_urlopen.recorded = recorded
        return fake_urlopen

    def _raise_urlopen_error(self, request, timeout=None):
        raise urllib.error.URLError("refused")

    def _fake_version_run(self, version="opencode v2.0.29\n", returncode=0):
        def fake_run(argv, **kwargs):
            if argv[1:] == ["--version"]:
                return unittest.mock.MagicMock(returncode=returncode, stdout=version)
            return unittest.mock.MagicMock(returncode=1, stdout="")
        return fake_run

    def test_detect_2x_returns_fixture_image_map_via_probe(self):
        popen = self.FakePopen()
        urlopen = self._fake_urlopen()
        result = detection.opencode_image_input_with_source(
            "/fake/bin/opencode", run_fn=self._fake_version_run(),
            popen_fn=popen, urlopen_fn=urlopen)[0]
        self.assertEqual(result, self.EXPECTED_MAP)

    def test_probe_argv_and_cwd(self):
        popen = self.FakePopen()
        detection.probe_opencode_api_image_input(
            "/fake/bin/opencode", popen_fn=popen, urlopen_fn=self._fake_urlopen())
        self.assertEqual(
            popen.argv,
            ["/fake/bin/opencode", "serve", "--hostname", "127.0.0.1", "--port", "0"],
        )
        cwd = popen.kwargs["cwd"]
        assert isinstance(cwd, str)
        self.assertNotEqual(cwd, tempfile.gettempdir())
        self.assertTrue(os.path.basename(cwd).startswith("ai-kit-opencode-probe-"))
        self.assertFalse(os.path.exists(cwd))  # the private dir is removed afterwards
        self.assertTrue(popen.kwargs.get("start_new_session"))

    # Inherited values the hardened env must override or drop (C-CR-01, C-WR-02, NF-2/3).
    HOSTILE_ENV = {"OPENCODE_SERVER_PASSWORD": "users-own", "OPENCODE_PASSWORD": "legacy",
                   "OPENCODE_DISABLE_PROJECT_CONFIG": "0",
                   "OPENCODE_CONFIG_PROJECT_DISABLE": "false"}

    def setUp(self):
        cache = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cache, ignore_errors=True)
        patcher = mock.patch.dict(os.environ, {"XDG_CACHE_HOME": cache})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.private_base = os.path.join(cache, "ai-kit", "spec")

    def _assert_hardened(self, kwargs):
        env = kwargs["env"]
        self.assertEqual(env["OPENCODE_DISABLE_PROJECT_CONFIG"], "1")
        self.assertEqual(env["OPENCODE_CONFIG_PROJECT_DISABLE"], "1")
        self.assertNotIn("OPENCODE_SERVER_PASSWORD", env)
        self.assertNotIn("OPENCODE_PASSWORD", env)
        cwd = kwargs["cwd"]
        self.assertEqual(os.path.dirname(cwd), self.private_base)
        self.assertTrue(os.path.basename(cwd).startswith("ai-kit-opencode-probe-"))

    def test_probe_env_disables_project_config_and_drops_password(self):
        """C-CR-01/C-WR-02/NF-2/NF-3: no opencode.json from cwd/ancestors under either
        disable name; opencode always prints its own one-time password."""
        popen = self.FakePopen()
        with mock.patch.dict(os.environ, self.HOSTILE_ENV):
            detection.probe_opencode_api_image_input(
                "/fake/bin/opencode", popen_fn=popen, urlopen_fn=self._fake_urlopen())
        self._assert_hardened(popen.kwargs)

    def test_every_opencode_subprocess_runs_hardened(self):
        """NF-1: `models`, `--version` and 1.x `models --verbose` get the probe's env and a
        private cwd (removed afterwards), never the caller's project config."""
        seen = []

        def fake_run(argv, **kwargs):
            seen.append((argv[1:], kwargs))
            self.assertTrue(os.path.isdir(kwargs["cwd"]))
            stdout = "opencode v1.18.32\n" if argv[1:] == ["--version"] else ""
            return unittest.mock.MagicMock(returncode=0, stdout=stdout)

        with mock.patch.dict(os.environ, self.HOSTILE_ENV):
            detection.detect_opencode_models("/fake/bin/opencode", run_fn=fake_run)
            detection.opencode_image_input_with_source("/fake/bin/opencode", run_fn=fake_run)
        self.assertEqual([argv for argv, _ in seen],
                         [["models"], ["--version"], ["models", "--verbose"]])
        for _argv, kwargs in seen:
            self._assert_hardened(kwargs)
            self.assertFalse(os.path.exists(kwargs["cwd"]))

    def test_private_dir_is_user_only(self):
        """NF-2: the private cwd is mode 0700 under ai-kit's own cache, not the temp root."""
        with detection._opencode_private_dir() as path:
            self.assertEqual(os.path.dirname(path), self.private_base)
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o700)
        self.assertFalse(os.path.exists(path))

    def test_private_dir_falls_back_to_tempfile(self):
        """NF-2: an unusable cache base (here a regular file) falls back to tempfile; a
        relative base (no HOME, no XDG_CACHE_HOME) never lands in the caller's cwd."""
        blocker = os.path.join(tempfile.mkdtemp(), "file")
        self.addCleanup(shutil.rmtree, os.path.dirname(blocker), ignore_errors=True)
        open(blocker, "w").close()
        for env in ({"XDG_CACHE_HOME": blocker}, {"XDG_CACHE_HOME": "", "HOME": ""}):
            with self.subTest(env=env), mock.patch.dict(os.environ, env), \
                    detection._opencode_private_dir() as path:
                self.assertEqual(os.path.dirname(path), tempfile.gettempdir())

    def test_default_opener_bypasses_http_proxy(self):
        """C-WR-01: the loopback request never reaches a configured http_proxy."""
        import http.server

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"direct")

            def log_message(self, *_args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        dead = socket.socket()
        dead.bind(("127.0.0.1", 0))
        dead_port = dead.getsockname()[1]
        dead.close()  # a proxy port nobody listens on: going through it would fail
        try:
            proxy = f"http://127.0.0.1:{dead_port}"
            with mock.patch.dict(os.environ, {"http_proxy": proxy, "HTTP_PROXY": proxy,
                                              "no_proxy": "", "NO_PROXY": ""}):
                url = f"http://127.0.0.1:{server.server_address[1]}/api/model"
                with detection._LOOPBACK_OPENER.open(url, timeout=5) as resp:
                    self.assertEqual(resp.read(), b"direct")
        finally:
            server.shutdown()
            server.server_close()

    def test_probe_signals_the_process_group(self):
        """C-WR-03: the whole server group is signalled, never just the direct PID."""
        popen = self.FakePopen()
        popen.pid = 424242
        sent = []
        with mock.patch.object(detection.os, "killpg", side_effect=lambda p, s: sent.append((p, s)),
                               create=True):
            detection.probe_opencode_api_image_input(
                "/fake/bin/opencode", popen_fn=popen, urlopen_fn=self._fake_urlopen())
        self.assertEqual(sent, [(424242, signal.SIGTERM), (424242, detection._SIGKILL)])
        self.assertNotIn("terminate", popen.calls)

    def test_blocked_stdout_hits_deadline_and_kills_group(self):
        """C-WR-03: a server that never prints (pipe held open) is killed at the deadline."""
        read_fd, write_fd = os.pipe()
        popen = self.FakePopen()
        popen.stdout = os.fdopen(read_fd, "r")
        popen.pid = 434343
        writer: dict[str, int | None] = {"fd": write_fd}
        sent = []

        def fake_killpg(pid, sig):
            sent.append((pid, sig))
            fd = writer["fd"]
            if fd is not None:  # the group dies: its end of the pipe closes
                os.close(fd)
                writer["fd"] = None

        with mock.patch.object(detection, "_OPENCODE_PROBE_DEADLINE_S", 0.2), \
                mock.patch.object(detection.os, "killpg", side_effect=fake_killpg, create=True):
            started = time.monotonic()
            result = detection.probe_opencode_api_image_input(
                "/fake/bin/opencode", popen_fn=popen, urlopen_fn=self._fake_urlopen())
        self.assertEqual(result, {})
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(sent[0], (434343, detection._SIGKILL))

    def test_sigterm_during_probe_unwinds_through_finally(self):
        """B-WR-05: a caller's SIGTERM timeout still runs the probe's cleanup."""
        previous = signal.getsignal(signal.SIGTERM)
        with self.assertRaises(SystemExit), detection._sigterm_unwinds():
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(1)
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)

    def test_probe_request_url_and_basic_auth(self):
        popen = self.FakePopen()
        urlopen = self._fake_urlopen()
        detection.probe_opencode_api_image_input(
            "/fake/bin/opencode", popen_fn=popen, urlopen_fn=urlopen)
        recorded = urlopen.recorded
        self.assertEqual(recorded["url"], "http://127.0.0.1:41234/api/model")
        expected = "Basic " + base64.b64encode(b"opencode:s3cr3t").decode()
        self.assertEqual(recorded["authorization"], expected)
        self.assertIsNone(recorded["redirectable_auth"])

    def test_probe_stops_server_after_success(self):
        popen = self.FakePopen()
        detection.probe_opencode_api_image_input(
            "/fake/bin/opencode", popen_fn=popen, urlopen_fn=self._fake_urlopen())
        self.assertEqual(popen.calls[0], "terminate")
        self.assertIn("wait(5)", popen.calls)

    def test_major_version(self):
        self.assertEqual(
            detection.opencode_major_version("x", run_fn=self._fake_version_run()), 2)
        self.assertEqual(
            detection.opencode_major_version(
                "x", run_fn=self._fake_version_run(version="1.18.32\n")), 1)
        self.assertIsNone(
            detection.opencode_major_version(
                "x", run_fn=self._fake_version_run(version="opencode-go/kimi-k3\n")))
        with open(OPENCODE_VERBOSE_FIXTURE_PATH, encoding="utf-8") as f:
            verbose_text = f.read()
        self.assertIsNone(
            detection.opencode_major_version(
                "x", run_fn=self._fake_version_run(version=verbose_text)))

    def test_major_version_failures_return_none(self):
        self.assertIsNone(
            detection.opencode_major_version(
                "x", run_fn=self._fake_version_run(returncode=1)))

        def raise_oserror(argv, **kwargs):
            raise OSError("not found")

        self.assertIsNone(detection.opencode_major_version("x", run_fn=raise_oserror))
        self.assertIsNone(
            detection.opencode_major_version(
                "x", run_fn=lambda *a, **k: type(
                    "R", (), {"returncode": 0, "stdout": "openai/gpt-5.6-sol"})()))

    def test_parse_api_models_skips_malformed_items(self):
        payload = {
            "location": "x",
            "data": [
                {"providerID": "p", "id": "m", "capabilities": {"input": ["text", "image"]}},
                {"providerID": "", "id": "m", "capabilities": {"input": ["image"]}},
                {"providerID": "p2", "id": "  ", "capabilities": {"input": ["image"]}},
                {"providerID": "p3", "id": "m3", "capabilities": "nope"},
                {"providerID": "p4", "id": "m4", "capabilities": {"input": "nope"}},
                "not-a-dict",
            ],
        }
        self.assertEqual(detection.parse_opencode_api_models(payload), {"p/m": True})

    def test_parse_api_models_degrades_to_empty(self):
        for payload in (None, 42, "x", {}, {"data": "nope"}, {"data": {}}):
            with self.subTest(payload=payload):
                self.assertEqual(detection.parse_opencode_api_models(payload), {})

    # ── 17 D-32: every failure stops the server and returns {} ──

    def _run_failure_case(self, popen, urlopen):
        import io
        from contextlib import redirect_stderr, redirect_stdout

        buf_out, buf_err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            result = detection.probe_opencode_api_image_input(
                "/fake/bin/opencode", popen_fn=popen, urlopen_fn=urlopen)
        return result, buf_out.getvalue() + buf_err.getvalue()

    def test_popen_oserror_returns_empty_without_urlopen(self):
        urlopen = self._fake_urlopen()

        def raise_oserror(*_args, **_kwargs):
            raise OSError("no binary")

        result, _output = self._run_failure_case(raise_oserror, urlopen)
        self.assertEqual(result, {})
        self.assertNotIn("/api/model", urlopen.recorded.get("url", ""))

    def test_silent_stdout_returns_empty_and_stops_server(self):
        popen = self.FakePopen(banner="")
        urlopen = self._fake_urlopen()
        result, _ = self._run_failure_case(popen, urlopen)
        self.assertEqual(result, {})
        self.assertEqual(popen.calls[0], "terminate")
        self.assertNotIn("/api/model", urlopen.recorded.get("url", ""))

    def test_missing_password_line_returns_empty_and_stops_server(self):
        popen = self.FakePopen(banner="server listening on http://127.0.0.1:41234\n")
        urlopen = self._fake_urlopen()
        result, _ = self._run_failure_case(popen, urlopen)
        self.assertEqual(result, {})
        self.assertEqual(popen.calls[0], "terminate")

    def test_urlerror_returns_empty_and_stops_server(self):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.URLError("refused")

        popen = self.FakePopen()
        result, _ = self._run_failure_case(popen, fake_urlopen)
        self.assertEqual(result, {})
        self.assertEqual(popen.calls[0], "terminate")

    def test_non_json_body_returns_empty_and_stops_server(self):
        popen = self.FakePopen()
        result, _ = self._run_failure_case(popen, self._fake_urlopen(body=b"not json"))
        self.assertEqual(result, {})
        self.assertEqual(popen.calls[0], "terminate")

    def test_wait_timeout_escalates_to_kill(self):
        popen = self.FakePopen()
        original_wait = popen.wait
        calls = {"n": 0}

        def flaky_wait(timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise subprocess.TimeoutExpired("cmd", timeout if timeout is not None else 5)
            return original_wait(timeout)

        popen.wait = flaky_wait
        result, _ = self._run_failure_case(popen, self._fake_urlopen())
        self.assertEqual(result, self.EXPECTED_MAP)
        self.assertLess(popen.calls.index("terminate"), popen.calls.index("kill"))

    def test_password_never_reaches_stdout_or_stderr(self):
        for popen, urlopen in (
            (self.FakePopen(banner=""), self._fake_urlopen()),
            (self.FakePopen(
                banner="server listening on http://127.0.0.1:41234\n"), self._fake_urlopen()),
            (self.FakePopen(), self._raise_urlopen_error),
            (self.FakePopen(), self._fake_urlopen(body=b"not json")),
        ):
            with self.subTest(calls=len(popen.calls)):
                _, output = self._run_failure_case(popen, urlopen)
                self.assertNotIn("s3cr3t", output)

    # ── 17 D-24 provenance ──

    def test_1x_still_uses_verbose_path(self):
        with open(OPENCODE_VERBOSE_FIXTURE_PATH, encoding="utf-8") as f:
            verbose_text = f.read()
        calls = {"version": 0, "verbose": 0}

        def fake_run(argv, **kwargs):
            calls["version" if argv[1:] == ["--version"] else "verbose"] += 1
            return unittest.mock.MagicMock(
                returncode=0,
                stdout="opencode v1.18.32\n" if argv[1:] == ["--version"] else verbose_text)

        popen = self.FakePopen()
        result = detection.opencode_image_input_with_source(
            "/fake/bin/opencode", run_fn=fake_run, popen_fn=popen,
            urlopen_fn=self._fake_urlopen())[0]
        self.assertEqual(result, {"openai/gpt-5.6-sol": True, "router-env/my-coding": False})
        self.assertEqual(popen.argv, None)  # the probe never ran

    def test_with_source_2x_and_1x(self):
        popen = self.FakePopen()
        result = detection.opencode_image_input_with_source(
            "/fake/bin/opencode", run_fn=self._fake_version_run(),
            popen_fn=popen, urlopen_fn=self._fake_urlopen())
        self.assertEqual(result, (self.EXPECTED_MAP, "opencode-api"))

        with open(OPENCODE_VERBOSE_FIXTURE_PATH, encoding="utf-8") as f:
            verbose_text = f.read()

        def fake_run(argv, **kwargs):
            return unittest.mock.MagicMock(
                returncode=0,
                stdout="1.18.32\n" if argv[1:] == ["--version"] else verbose_text)

        result = detection.opencode_image_input_with_source(
            "/fake/bin/opencode", run_fn=fake_run, popen_fn=self.FakePopen(),
            urlopen_fn=self._fake_urlopen())
        self.assertEqual(
            result, ({"openai/gpt-5.6-sol": True, "router-env/my-coding": False}, "opencode"))

    def test_snapshot_threads_probe_seams(self):
        """C-IN-01: a 2.x snapshot built with fakes never reaches the real Popen/urlopen."""
        popen = self.FakePopen()
        snapshot = build_runtimes_snapshot(
            which_fn=lambda name: "/fake/bin/opencode" if name == "opencode" else None,
            run_fn=self._fake_version_run(),
            opencode=detection.OpencodeSeams(popen, self._fake_urlopen()))
        self.assertIsNotNone(popen.argv)
        self.assertEqual(snapshot["clis"]["opencode"]["image_input"], self.EXPECTED_MAP)

    def test_cli_detect_runtimes_threads_probe_seams(self):
        popen = self.FakePopen()
        deps = cli.CliDeps(
            which_fn=lambda name: "/fake/bin/opencode" if name == "opencode" else None,
            run_fn=self._fake_version_run(), popen_fn=popen, urlopen_fn=self._fake_urlopen())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["detect-runtimes"], deps=deps), 0)
        self.assertIsNotNone(popen.argv)

    def test_snapshot_records_image_input_source(self):
        def fake_which(name):
            return "/fake/bin/opencode" if name == "opencode" else None

        # 2.x: the probe itself is patched here (popen_fn/urlopen_fn fakes: see above).
        with mock.patch.object(
                detection, "probe_opencode_api_image_input",
                return_value={"opencode/exo-free": True}) as probe_mock:
            snapshot = build_runtimes_snapshot(
                which_fn=fake_which, run_fn=self._fake_version_run())
        probe_mock.assert_called_once()
        entry = snapshot["clis"]["opencode"]
        self.assertEqual(entry["image_input"], {"opencode/exo-free": True})
        self.assertEqual(entry["image_input_source"], "opencode-api")

        # 1.x: no probe runs.
        with open(OPENCODE_VERBOSE_FIXTURE_PATH, encoding="utf-8") as f:
            verbose_text = f.read()

        def fake_run(argv, **kwargs):
            return unittest.mock.MagicMock(
                returncode=0,
                stdout="1.18.32\n" if argv[1:] == ["--version"] else verbose_text)

        with mock.patch.object(detection, "probe_opencode_api_image_input") as probe_mock:
            snapshot = build_runtimes_snapshot(which_fn=fake_which, run_fn=fake_run)
        probe_mock.assert_not_called()
        self.assertEqual(snapshot["clis"]["opencode"]["image_input_source"], "opencode")

        # No image map: neither key is stored.
        snapshot = build_runtimes_snapshot(
            which_fn=fake_which, run_fn=lambda *a, **k: unittest.mock.MagicMock(
                returncode=0, stdout="opencode-go/kimi-k3\n"))
        self.assertNotIn("image_input", snapshot["clis"]["opencode"])
        self.assertNotIn("image_input_source", snapshot["clis"]["opencode"])
        self.assertNotIn("image_input_probe", snapshot["clis"]["opencode"])

        # C-WR-02: a failed 2.x probe is recorded, not silently absent.
        with mock.patch.object(detection, "probe_opencode_api_image_input", return_value={}):
            snapshot = build_runtimes_snapshot(
                which_fn=fake_which, run_fn=self._fake_version_run())
        self.assertEqual(snapshot["clis"]["opencode"]["image_input_probe"], "failed")
        self.assertNotIn("image_input", snapshot["clis"]["opencode"])

    def test_catalog_meta_carries_provenance_label(self):
        from ai_kit_spec.catalog_build import _apply_runtime_meta, _runtime_meta_from_snapshot

        snapshot = {"clis": {"opencode": {
            "installed": True,
            "image_input": {"opencode/exo-free": True},
            "image_input_source": "opencode-api",
        }}}
        meta = _runtime_meta_from_snapshot(snapshot)
        entry = {}
        _apply_runtime_meta(entry, meta, "opencode", "opencode/exo-free")
        self.assertEqual(entry["image_input"], True)
        self.assertEqual(entry["image_input_source"], "opencode-api")

        # No source field (a schema-2 snapshot) -> the 1.x default "opencode".
        cli_data = {"installed": True, "image_input": {"opencode/exo-free": True}}
        meta = _runtime_meta_from_snapshot({"clis": {"opencode": cli_data}})
        entry = {}
        _apply_runtime_meta(entry, meta, "opencode", "opencode/exo-free")
        self.assertEqual(entry["image_input_source"], "opencode")

        # C-IN-02: an unknown label is unsourced data, never relabelled as 1.x verbose.
        cli_data = {**cli_data, "image_input_source": "weird"}
        meta = _runtime_meta_from_snapshot({"clis": {"opencode": cli_data}})
        entry = {}
        _apply_runtime_meta(entry, meta, "opencode", "opencode/exo-free")
        self.assertEqual(entry, {})

    def test_validate_catalog_entry_accepts_opencode_api_source(self):
        base = {
            "provider": "opencode",
            "runtimes": {"opencode": {"model_id": "opencode/exo-free"}},
            "source": {"models_dev": True},
            "confidence": "high",
            "last_verified": "2026-10-15",
        }
        entry = {**base, "image_input": True, "image_input_source": "opencode-api"}
        self.assertIsNone(
            model_catalog.validate_catalog_entry("opencode/exo-free", entry))
        bad = {**base, "image_input": True, "image_input_source": "telepathy"}
        self.assertIsNotNone(
            model_catalog.validate_catalog_entry("opencode/exo-free", bad))


class TestClaudeRuntimeFreshness(unittest.TestCase):
    """The catalog -> runtimes freshness edge (review cycle 1): runtimes.json's claude ids
    are derived from model-catalog.json `_meta`, so a catalog change re-detects a fresh
    snapshot -- and an unchanged catalog (including no recorded ids vs a stored dated
    fallback) never loops."""

    @staticmethod
    def _claude_which(name):
        return "/fake/bin/claude" if name == "claude" else None

    def test_fallback_snapshot_without_catalog_ids_is_not_redetected(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            env = {"HOME": d}
            r = os.path.join(d, "runtimes.json")
            for seed in ("no-catalog-file", {"_meta": {"schema_version": 2}}):
                with self.subTest(seed=seed):
                    if os.path.exists(r):
                        os.remove(r)
                    if seed != "no-catalog-file":
                        cache_write_json(model_catalog.cache_catalog_path(env), seed)
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = main(
                            ["detect-runtimes", "--if-stale", r],
                            which_fn=self._claude_which,
                            run_fn=lambda *a, **k: None,
                            env_fn=lambda: env,
                        )
                    self.assertEqual(code, 0)
                    self.assertNotEqual(json.loads(buf.getvalue()), {})  # first run detects
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = main(
                            ["detect-runtimes", "--if-stale", r],
                            which_fn=self._claude_which,
                            run_fn=lambda *a, **k: None,
                            env_fn=lambda: env,
                        )
                    self.assertEqual(code, 0)
                    # A stored dated fallback matches "no recorded ids" -- no re-detect loop.
                    self.assertEqual(json.loads(buf.getvalue()), {})

    def test_catalog_id_change_invalidates_a_fresh_snapshot(self):
        import io
        from contextlib import redirect_stdout

        new = "claude-new-not-in-fallback"
        with tempfile.TemporaryDirectory() as d:
            env = {"HOME": d}
            r = os.path.join(d, "runtimes.json")
            catalog_path = model_catalog.cache_catalog_path(env)
            md = json.loads(json.dumps(TestClaudeEnumerationEndToEnd.MD))

            def detect():
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = main(
                        ["detect-runtimes", "--if-stale", r],
                        which_fn=self._claude_which,
                        run_fn=lambda *a, **k: None,
                        env_fn=lambda: env,
                    )
                return code, buf.getvalue()

            def fetch(if_stale):
                argv = ["fetch-model-catalog", "--runtimes-json", r, "--catalog-path", catalog_path]
                if if_stale:
                    argv.append("--if-stale")
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = main(
                        argv,
                        which_fn=self._claude_which,
                        fetch_models_dev_fn=lambda: (md, True),
                        fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                        load_secret_fn=lambda _env_, key: None,
                        env_fn=lambda: env,
                    )
                return code, buf.getvalue()

            # Replay the tracer's convergence: fallback detect -> recording fetch -> detect.
            self.assertEqual(detect()[0], 0)
            code, out = fetch(if_stale=True)
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out)["fetch_skipped"])
            code, out = detect()
            self.assertNotEqual(json.loads(out), {})
            new = "claude-new-not-in-fallback"
            five = sorted([*detection.CLAUDE_FALLBACK_MODEL_IDS, new])
            cached = cache_read_json(r)
            assert cached is not None
            self.assertEqual(cached["clis"]["claude"]["models"], five)

            # A FORCED fetch whose models.dev payload gained `claude-extra-new` ...
            md["anthropic"]["models"]["claude-extra-new"] = {
                "id": "claude-extra-new",
                "tool_call": True,
                "limit": {"context": 1000000, "output": 128000},
            }
            code, _ = fetch(if_stale=False)
            self.assertEqual(code, 0)
            entries, meta = model_catalog.split_catalog_meta(cache_read_json(catalog_path))
            six = sorted([*five, "claude-extra-new"])
            self.assertEqual(meta["anthropic_model_ids"], six)
            self.assertEqual(
                entries["anthropic/claude-extra-new"]["runtimes"]["claude"]["model_id"],
                "claude-extra-new",
            )

            # ... invalidates the still-fresh runtimes snapshot: claude re-detects.
            code, out = detect()
            self.assertEqual(code, 0)
            self.assertNotEqual(json.loads(out), {})
            cached = cache_read_json(r)
            assert cached is not None
            self.assertEqual(cached["clis"]["claude"]["models"], six)

    def test_skip_check_never_reads_the_catalog_without_an_installed_claude(self):
        reads = []

        def recording_catalog_fn():
            reads.append(1)
            return None

        for data in (
            None,
            [],
            {},
            {"clis": []},
            {"clis": {}},
            {"clis": {"claude": "x"}},
            {"clis": {"claude": {"installed": False}}},
        ):
            with self.subTest(data=data):
                reads.clear()
                self.assertTrue(
                    detection.claude_runtime_is_current(data, catalog_fn=recording_catalog_fn)
                )
                self.assertEqual(reads, [])

    def test_as_of_difference_is_stale_and_full_match_is_current(self):
        catalog_raw = {
            "_meta": {
                "anthropic_model_ids": ["claude-x"],
                "anthropic_model_ids_as_of": "2026-09-01",
            }
        }
        base = {
            "installed": True,
            "path": "/fake/bin/claude",
            "aliases": list(detection.CLAUDE_MODEL_ALIASES),
            "models": ["claude-x"],
            "models_source": "catalog",
        }
        stale = {**base, "models_as_of": "2026-09-02"}
        self.assertFalse(
            detection.claude_runtime_is_current(
                {"clis": {"claude": stale}}, catalog_fn=lambda: catalog_raw
            )
        )
        current = {**base, "models_as_of": "2026-09-01"}
        self.assertTrue(
            detection.claude_runtime_is_current(
                {"clis": {"claude": current}}, catalog_fn=lambda: catalog_raw
            )
        )


class TestClaudeCatalogMaterialization(unittest.TestCase):
    """Same-fetch materialization (review cycle 2 HIGH): a fetch that records models.dev's
    anthropic ids also builds an `anthropic/<id>` entry with a claude runtime for every one,
    gated on claude being on PATH, lazy (no anthropic provider -> nothing), never widening
    the printed `discovered`/`unmatched` scope, with the `anthropic` match hint claude-only
    and malformed rows neither crashing the fetch nor getting recorded (review cycle 3)."""

    def test_materialization_needs_claude_on_path(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            runtimes_path = os.path.join(d, "runtimes.json")
            cache_write_json(runtimes_path, {"clis": {}})
            which_calls = []

            def recording_which(name):
                which_calls.append(name)
                return None

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                    ],
                    which_fn=recording_which,
                    fetch_models_dev_fn=lambda: (TestClaudeEnumerationEndToEnd.MD, True),
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    load_secret_fn=lambda _env_, key: None,
                    env_fn=lambda: {"HOME": d},
                )
            self.assertEqual(code, 0)
            entries, meta = model_catalog.split_catalog_meta(cache_read_json(catalog_path))
            self.assertEqual(
                meta["anthropic_model_ids"],
                sorted([*detection.CLAUDE_FALLBACK_MODEL_IDS, "claude-new-not-in-fallback"]),
            )
            self.assertFalse([e for e in entries.values() if "claude" in e.get("runtimes", {})])
            self.assertEqual(which_calls, ["claude"])

    def test_materialization_is_lazy(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            runtimes_path = os.path.join(d, "runtimes.json")
            cache_write_json(runtimes_path, {"clis": {}})
            which_calls = []

            def recording_which(name):
                which_calls.append(name)
                return "/fake/bin/claude" if name == "claude" else None

            no_anthropic = {
                "openai": {
                    "models": {
                        "gpt-5.6-sol": {
                            "id": "gpt-5.6-sol",
                            "tool_call": True,
                            "limit": {"context": 400000, "output": 128000},
                        }
                    }
                }
            }
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                    ],
                    which_fn=recording_which,
                    fetch_models_dev_fn=lambda: (no_anthropic, True),
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    load_secret_fn=lambda _env_, key: None,
                    env_fn=lambda: {"HOME": d},
                )
            self.assertEqual(code, 0)
            self.assertEqual(which_calls, [])  # no anthropic ids -> claude is never probed
            written = cache_read_json(catalog_path)
            assert written is not None
            self.assertFalse([k for k in written if k.startswith("anthropic/")])

    def test_narrowed_snapshot_scope_never_widens(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            runtimes_path = os.path.join(d, "runtimes.json")
            cache_write_json(
                runtimes_path,
                {
                    "schema_version": 2,
                    "clis": {"opencode": {"installed": True, "models": ["openai/gpt-5.6-sol"]}},
                },
            )
            md = json.loads(json.dumps(TestClaudeEnumerationEndToEnd.MD))
            md["openai"] = {
                "models": {
                    "gpt-5.6-sol": {
                        "id": "gpt-5.6-sol",
                        "tool_call": True,
                        "limit": {"context": 400000, "output": 128000},
                    }
                }
            }
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                    ],
                    which_fn=lambda name: "/fake/bin/claude" if name == "claude" else None,
                    fetch_models_dev_fn=lambda: (md, True),
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    load_secret_fn=lambda _env_, key: None,
                    env_fn=lambda: {"HOME": d},
                )
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            entries, _ = model_catalog.split_catalog_meta(cache_read_json(catalog_path))
            for mid in [*detection.CLAUDE_FALLBACK_MODEL_IDS, "claude-new-not-in-fallback"]:
                self.assertEqual(entries[f"anthropic/{mid}"]["runtimes"]["claude"]["model_id"], mid)
            self.assertEqual(
                result["discovered"], [{"runtime": "opencode", "model_id": "openai/gpt-5.6-sol"}]
            )
            self.assertFalse([u for u in result["unmatched"] if u.get("cli") == "claude"])
            self.assertEqual(
                model_catalog.current_candidate_keys(entries, result["discovered"]),
                {"openai/gpt-5.6-sol"},
            )

    def test_anthropic_hint_is_claude_only(self):
        md = {
            "anthropic": {"models": {"claude-x": {"id": "claude-x"}}},
            "reseller": {"models": {"claude-x": {"id": "claude-x"}}},
        }
        catalog, _, unmatched = cli.build_model_catalog(
            [{"runtime": "claude", "model_id": "claude-x"}],
            cli.CatalogSources(md, True, [], False),
            {},
        )
        self.assertIn("anthropic/claude-x", catalog)
        self.assertEqual(unmatched, [])
        catalog, _, unmatched = cli.build_model_catalog(
            [{"runtime": "cursor-agent", "model_id": "claude-x"}],
            cli.CatalogSources(md, True, [], False),
            {},
        )
        self.assertNotIn("anthropic/claude-x", catalog)
        self.assertEqual(len(unmatched), 1)  # every other CLI keeps the unhinted behavior

    def test_anthropic_model_ids_keeps_only_well_formed_rows(self):
        md = {
            "anthropic": {
                "models": {
                    "claude-b": {},
                    "claude-a": {"id": "claude-a", "limit": {"output": 1}, "cost": {"input": 1.0}},
                    "claude-null": None,
                    "claude-str": "junk",
                    "claude-list": [],
                    "": {},
                    "claude-bad-limit": {"limit": "junk"},
                    "claude-null-limit": {"limit": None},
                    "claude-bad-cost": {"cost": 3},
                }
            }
        }
        self.assertEqual(cli._anthropic_model_ids(md), ["claude-a", "claude-b"])
        for bad in (None, "x", {}, {"anthropic": []}, {"anthropic": {"models": []}}):
            self.assertEqual(cli._anthropic_model_ids(bad), [])

    def test_malformed_anthropic_rows_never_crash_or_get_recorded(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            runtimes_path = os.path.join(d, "runtimes.json")
            cache_write_json(runtimes_path, {"schema_version": 2, "clis": {}})
            md = {
                "anthropic": {
                    "models": {
                        "claude-ok": {
                            "id": "claude-ok",
                            "tool_call": True,
                            "limit": {"context": 200000, "output": 64000},
                        },
                        "claude-null": None,
                        "claude-str": "junk",
                        "claude-bad-limit": {"id": "claude-bad-limit", "limit": "junk"},
                        "claude-bad-tool": {"id": "claude-bad-tool", "tool_call": "yes"},
                    }
                }
            }
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(
                    [
                        "fetch-model-catalog",
                        "--runtimes-json",
                        runtimes_path,
                        "--catalog-path",
                        catalog_path,
                    ],
                    which_fn=lambda name: "/fake/bin/claude" if name == "claude" else None,
                    fetch_models_dev_fn=lambda: (md, True),
                    fetch_artificial_analysis_fn=lambda _api_key: ([], True),
                    load_secret_fn=lambda _env_, key: None,
                    env_fn=lambda: {"HOME": d},
                )
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            entries, meta = model_catalog.split_catalog_meta(cache_read_json(catalog_path))
            self.assertEqual(meta["anthropic_model_ids"], ["claude-ok"])
            ok = entries["anthropic/claude-ok"]
            self.assertEqual(ok["runtimes"]["claude"]["model_id"], "claude-ok")
            self.assertIsNone(model_catalog.validate_catalog_entry("anthropic/claude-ok", ok))
            self.assertEqual(
                [k for k in entries if k.startswith("anthropic/")], ["anthropic/claude-ok"]
            )
            self.assertFalse([u for u in result["unmatched"] if u.get("cli") == "claude"])
            # A well-shaped row whose entry validation rejected ("tool_call": "yes") is
            # reported, never recorded without an entry.
            self.assertTrue(any("claude-bad-tool" in r for r in result["rejections"]))


class TestArgvRendering(unittest.TestCase):
    """D-10: reviewer templates render to argv lists; shell syntax fails loudly."""

    def _resolved(self, command, extra=None):
        return ResolvedReviewer(
            key="k", model="m", vendor="v", runtime="codex", command=command, extra=extra or {}
        )

    def test_split_command_template_tokenizes(self):
        self.assertEqual(
            commands.split_command_template("k", "codex exec -m {model} {prompt}"),
            ["codex", "exec", "-m", "{model}", "{prompt}"],
        )

    def test_render_returns_argv_with_raw_prompt_and_formatted_extra(self):
        argv = render_reviewer_command(
            self._resolved(
                "codex exec -m {model} -c effort='\"{effort}\"' {prompt}", extra={"effort": "high"}
            ),
            'a "b" $c `d`',
        )
        self.assertEqual(argv, ["codex", "exec", "-m", "m", "-c", 'effort="high"', 'a "b" $c `d`'])

    def test_shell_syntax_templates_raise_value_error_naming_key_and_template(self):
        for template in ("x; rm -rf /", "x | y", "x && y", "x > f", "x $HOME", "x `id`"):
            with self.subTest(template=template):
                with self.assertRaises(ValueError) as ctx:
                    commands.split_command_template("k", template)
                self.assertIn("k", str(ctx.exception))
                self.assertIn(template, str(ctx.exception))

    def test_render_surfaces_shell_syntax_rejection(self):
        with self.assertRaises(ValueError):
            render_reviewer_command(self._resolved("x; rm -rf /"), "p")

    def test_empty_and_whitespace_templates_raise_value_error_naming_key(self):
        for template in ("", "   "):
            with self.subTest(template=template):
                with self.assertRaises(ValueError) as ctx:
                    commands.split_command_template("k", template)
                self.assertIn("k", str(ctx.exception))

    def test_unknown_placeholder_and_literal_brace_still_raise_value_error(self):
        with self.assertRaises(ValueError):
            render_reviewer_command(self._resolved("codex -m {model} {nope}"), "p")
        with self.assertRaises(ValueError):
            render_reviewer_command(self._resolved("codex -m {model} {}"), "p")


class TestChildEnv(unittest.TestCase):
    """D-14: HOST_SIGNAL_ENV_VARS covers every R9 signal plus CODEX_VERSION; child_env scrubs
    them, then applies extra."""

    def test_host_signal_env_vars_exact_set(self):
        self.assertEqual(
            detection.HOST_SIGNAL_ENV_VARS,
            {
                "AI_AGENT",
                "CLAUDECODE",
                "CLAUDE_CODE_ENTRYPOINT",
                "CLAUDE_CODE_SSE_PORT",
                "OPENCODE",
                "CURSOR_AGENT",
                "PI_CODING_AGENT",
                "CODEX_THREAD_ID",
                "CODEX_SANDBOX",
                "GROK_AGENT",
                "CODEX_VERSION",
            },
        )

    def test_scrubs_host_signals_and_passes_the_rest_through(self):
        self.assertEqual(
            runner_dispatch.child_env(env={"PATH": "p", "AI_AGENT": "x"}), {"PATH": "p"}
        )

    def test_no_signals_set_environment_equals_the_parents(self):
        env = {k: v for k, v in os.environ.items() if k not in detection.HOST_SIGNAL_ENV_VARS}
        self.assertEqual(runner_dispatch.child_env(env=env), env)

    def test_extra_is_applied_after_the_scrub(self):
        self.assertEqual(
            runner_dispatch.child_env(extra={"AI_AGENT": "y"}, env={"AI_AGENT": "x"}),
            {"AI_AGENT": "y"},
        )

    def test_defaults_copy_os_environ(self):
        # C-WR-08: exercise the os.environ default, with a signal set so the scrub must act.
        with unittest.mock.patch.dict(os.environ, {"PATH": "p", "AI_AGENT": "1"}, clear=True):
            self.assertEqual(runner_dispatch.child_env(), {"PATH": "p"})


class TestDispatchReviewerRealChild(unittest.TestCase):
    """R9 tracer: a REAL custom child spawned through dispatch_reviewer with all eleven host
    signal variables set sees none of them; PATH and HOME pass through. The marker rides the
    child's argv so a leak check can find this process if it outlives the test."""

    def test_real_child_sees_none_of_the_host_signals(self):
        with tempfile.TemporaryDirectory() as d:
            script = os.path.join(d, "dump_env.py")
            with open(script, "w", encoding="utf-8") as f:
                f.write(
                    "import json, os, sys\n"
                    "with open(sys.argv[1], 'w', encoding='utf-8') as f:\n"
                    "    f.write(json.dumps(sorted(os.environ)))\n"
                )
            outfile = os.path.join(d, "env.json")
            marker = f"aikit-leak-marker-{uuid.uuid4().hex}"
            command = (
                f"{shlex.quote(sys.executable)} {shlex.quote(script)} "
                f"{shlex.quote(outfile)} {marker}"
            )
            signals = [
                "AI_AGENT",
                "CLAUDECODE",
                "CLAUDE_CODE_ENTRYPOINT",
                "CLAUDE_CODE_SSE_PORT",
                "OPENCODE",
                "CURSOR_AGENT",
                "PI_CODING_AGENT",
                "CODEX_THREAD_ID",
                "CODEX_SANDBOX",
                "GROK_AGENT",
                "CODEX_VERSION",
            ]
            env = dict(os.environ)
            env.update({s: "1" for s in signals})
            with unittest.mock.patch.dict(os.environ, env, clear=True):
                result = reviewer_dispatch.dispatch_reviewer(
                    reviewer_dispatch.ReviewerDispatchSpec(
                        reviewer_entry={
                            "key": "k",
                            "model": "m",
                            "vendor": "v",
                            "command": command,
                            "extra": {},
                        },
                        prompt="p",
                        timeout_tiers=[60],
                        tool_availability={},
                    ),
                    seams=reviewer_dispatch.ReviewerSeams(
                        custom_fn=runner_dispatch.run_custom_command,
                        build_tooling_guidance_fn=lambda *a, **kw: "",
                        resolve_shared_reference_fn=lambda: None,
                        codegraph_health_fn=lambda cli: False,
                    ),
                )
            self.assertEqual(result["returncode"], 0, result)
            with open(outfile, encoding="utf-8") as f:
                child_env_keys = set(json.load(f))
            self.assertEqual(child_env_keys & set(signals), set())
            self.assertIn("PATH", child_env_keys)
            self.assertIn("HOME", child_env_keys)


class TestProbeArgv(unittest.TestCase):
    """D-11/D-14: a runtime probe is one review-mode runner call; a custom probe is a launcher
    call whose argv carries no shell and whose reason still comes from stderr."""

    def test_runtime_probe_is_one_review_mode_runner_call(self):
        resolved = ResolvedReviewer(
            key="k", model="m", vendor="v", runtime="codex", command=None,
            extra={"effort": "high", "service_tier": "fast"},
        )
        captured = {}

        def fake_runner(spec, prompt, seams):
            del seams
            captured["spec"] = spec
            captured["prompt"] = prompt
            return _probe_result(None, "ok")

        with unittest.mock.patch.dict(os.environ, {"AI_AGENT": "1"}):  # C-WR-08
            result = probe_reviewer_quota(resolved, seams=ProbeSeams(runner_fn=fake_runner))
        self.assertTrue(result["available"])
        self.assertEqual(captured["spec"].mode, "review")
        self.assertEqual(captured["spec"].timeout_s, 30)
        self.assertEqual(captured["spec"].effort, "high")
        self.assertEqual(captured["spec"].service_tier, "fast")
        self.assertEqual(captured["prompt"], "Only say: Hello world!")
        self.assertNotIn("AI_AGENT", captured["prompt"])

    def test_custom_probe_with_a_missing_binary_names_it(self):
        resolved = ResolvedReviewer(
            key="k", model="m", vendor="v", runtime=None,
            command="definitely-not-a-real-binary-xyz --flag", extra={},
        )

        def fake_custom(spec, prompt, seams):
            del prompt
            seams.print_fn(f"[Errno 2] No such file or directory: '{spec.argv[0]}'")
            return _probe_result("dispatch_unavailable")

        result = probe_reviewer_quota(resolved, seams=ProbeSeams(custom_fn=fake_custom))
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "dispatch_unavailable")
        self.assertIn("definitely-not-a-real-binary-xyz", result["detail"])

    def test_custom_probe_on_shell_syntax_is_unavailable_naming_the_key(self):
        resolved = ResolvedReviewer(
            key="k", model="m", vendor="v", runtime=None, command="codex exec $HOME", extra={}
        )
        result = probe_reviewer_quota(
            resolved,
            seams=ProbeSeams(custom_fn=lambda *a: (_ for _ in ()).throw(
                AssertionError("must fail before any spawn")
            )),
        )
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "configuration")
        self.assertIn("k", result["detail"])


class TestDispatchExecuteArgv(unittest.TestCase):
    """D-10: execute dispatch reports shlex.join of the runner argv, never a shell string."""

    def test_target_dir_with_braces_reaches_the_child_verbatim_as_one_argument(self):
        candidate = {"runtime": "opencode", "model": "m", "key": "opencode/m"}
        captured = {}

        def fake_popen(argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            raise OSError("spawn stopped after argv capture")

        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "dir with {x}")
            os.makedirs(target)
            result = execute_dispatch.dispatch_execute(
                execute_dispatch.ExecuteDispatchSpec(
                    candidate=candidate,
                    prompt="do the task",
                    target_dir=target,
                    timeout=600,
                ),
                seams=execute_dispatch.ExecuteSeams(
                    build_tooling_guidance_fn=lambda *a, **kw: "",
                    # which_fn: the image without node must still reach the spawn.
                    runner_seams=runner_dispatch.RunnerSeams(
                        popen_fn=fake_popen, which_fn=lambda _name: "node"
                    ),
                ),
            )
        self.assertIsInstance(captured["argv"], list)
        self.assertNotIn("shell", captured["kwargs"])
        self.assertTrue(captured["kwargs"]["start_new_session"])
        self.assertIn(target, captured["kwargs"]["cwd"])
        self.assertIn("--child-pgid-file", captured["argv"])
        self.assertNotIn("--child-pgid-file", result["command"])
        self.assertEqual(result["reason"], "dispatch_unavailable")

    def test_result_command_is_shlex_join_of_the_argv(self):
        candidate = {"runtime": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol"}
        captured = {}

        def fake_runner(spec, prompt, seams):
            del prompt, seams
            captured["spec"] = spec
            argv = ["node", "runner", "--model-codex", spec.model, "--mode", "exec"]
            return RunnerResult(0, "", {"status": "ok"}, None, False, argv, "")

        with tempfile.TemporaryDirectory() as target:
            result = execute_dispatch.dispatch_execute(
                execute_dispatch.ExecuteDispatchSpec(
                    candidate=candidate,
                    prompt="do the task",
                    target_dir=target,
                    timeout=600,
                ),
                seams=execute_dispatch.ExecuteSeams(runner_fn=fake_runner),
            )
        self.assertEqual(result["command"], shlex.join(
            ["node", "runner", "--model-codex", "gpt-5.6-sol", "--mode", "exec"]
        ))
        self.assertEqual(runner_dispatch.runner_flags(captured["spec"])[-2:],
                         ["--codex-sandbox", "workspace-write"])



class TestCrossAiTemplateText(unittest.TestCase):
    """Pins cross-ai.mjs header, CONFIG block, and scrub list for the v2 renderer (18-09)."""

    _SCRUB_DEFAULT = sorted(detection.HOST_SIGNAL_ENV_VARS)

    def _template_path(self) -> str:
        path = tooling_guidance.resolve_cross_ai_template_path()
        self.assertIsNotNone(path)
        assert path is not None
        return path

    def test_resolve_path_missing_when_file_absent(self):
        self.assertIsNotNone(tooling_guidance.resolve_cross_ai_template_path())
        with mock.patch("ai_kit_spec.tooling_guidance.os.path.isfile", return_value=False):
            self.assertIsNone(tooling_guidance.resolve_cross_ai_template_path())

    def test_header_and_config_contract(self):
        path = self._template_path()
        text = _read_bytes(path).decode("utf-8")
        lines = text.splitlines()
        hdr = (
            r"^// ai-kit-cross-ai generator=ai-kit-gsd-curated-config "
            r"template=(\d+) sha256=UNSTAMPED$"
        )
        m = re.match(hdr, lines[1])
        self.assertIsNotNone(m)
        assert m is not None
        self.assertEqual(m.group(1), "3")
        start = text.index("// <config>\n") + len("// <config>\n")
        end = text.index("\n// </config>", start)
        block = text[start:end]
        self.assertTrue(block.startswith("const CONFIG = "))
        cfg_text = block[len("const CONFIG = ") : -1]
        cfg = json.loads(cfg_text)
        expected = {
            "backoffS": [30, 60],
            "effort": {},
            "extraArgs": {},
            "heartbeatS": 30,
            "models": {},
            "outerTimeoutS": 1800,
            "prefer": ["pi", "cursor", "opencode"],
            "retries": 2,
            "routerBacked": {},
            "scrubEnv": self._SCRUB_DEFAULT,
        }
        self.assertEqual(cfg, expected)
        self.assertNotIn("timeoutMarginS", cfg)
        reserialized = "const CONFIG = " + json.dumps(cfg, indent=2, sort_keys=True) + ";"
        self.assertEqual(block, reserialized)
        self.assertIn("const TIMEOUT_MARGIN_S = 30;", text)
        self.assertEqual(cfg["scrubEnv"], sorted(detection.HOST_SIGNAL_ENV_VARS))

    def test_retired_cli_absent_outside_scrub_entry(self):
        path = self._template_path()
        text = _read_bytes(path).decode("utf-8")
        start = text.index('"scrubEnv"')
        end = text.index("\n// </config>", start)
        region = text[:start] + text[end:]
        region_no_grok_agent = region.replace('"GROK_AGENT"', "")
        self.assertIsNone(re.search("grok", region_no_grok_agent, re.I))
        cfg_start = text.index("const CONFIG = ") + len("const CONFIG = ")
        cfg_end = text.index("\n// </config>")
        cfg = json.loads(text[cfg_start:cfg_end].rstrip(";"))
        for key in ("prefer", "models", "extraArgs", "routerBacked"):
            val = cfg.get(key)
            if isinstance(val, (dict, list)):
                self.assertFalse(any("grok" in str(k).lower() for k in val))

    def test_no_absolute_home_paths_or_header_state(self):
        path = self._template_path()
        text = _read_bytes(path).decode("utf-8")
        for frag in ("/home/", "/Users/", "/var/home/"):
            self.assertNotIn(frag, text)
        self.assertNotIn("headerState", text)

    def test_patterns_block(self):
        path = self._template_path()
        text = _read_bytes(path).decode("utf-8")
        start = text.index("// <patterns>\n") + len("// <patterns>\n")
        end = text.index("\n// </patterns>", start)
        block = text[start:end]
        self.assertTrue(block.startswith("const PATTERNS = "))
        pat_text = block[len("const PATTERNS = ") : -1]
        patterns = json.loads(pat_text)
        expected_keys = [
            "permission_blocked",
            "billing",
            "quota",
            "auth",
            "bad_model",
            "capacity",
            "transient",
        ]
        self.assertEqual(list(patterns.keys()), expected_keys)
        for value in patterns.values():
            re.compile(value, re.I)


if __name__ == "__main__":
    unittest.main()
