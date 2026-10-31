import contextlib
import hashlib
import io
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

# Bootstraps every package root this plan's tests need. ai_kit_spec_superpowers (this plan) and
# ai_kit_spec (Plan 1, Foundation) both live outside this file's own directory, on no search path
# by default. skills/ai-kit-spec-execute is ALSO added here (not just
# skills/ai-kit-spec-execute-superpowers) because Task 5's detect_framework module lives there --
# this is the ONE bootstrap block for the whole file, at the top; it is never repeated.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute-superpowers")
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute"))

import detect_framework as router_detect_framework
from ai_kit_spec import detection, routing, runner_dispatch
from ai_kit_spec_superpowers import cli as superpowers_cli
from ai_kit_spec_superpowers import dispatch_injection, task_classification

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-session-wake"))
from tests import session_wake_fakes


class TestClassifyTask(unittest.TestCase):
    def test_classifies_frontend_from_file_extensions(self):
        task = "### Task 3: Button\n**Files:**\n- Create: `src/components/Button.tsx`\n"
        self.assertEqual(task_classification.classify_task(task), "frontend")

    def test_classifies_backend_from_file_paths(self):
        task = "### Task 4: API\n**Files:**\n- Create: `server/api/handlers.py`\n"
        self.assertEqual(task_classification.classify_task(task), "backend")

    def test_classifies_mixed_when_both_signal_types_present(self):
        task = (
            "### Task 5: Full-stack widget\n**Files:**\n"
            "- Create: `src/components/Widget.tsx`\n- Create: `server/api/widget.py`\n"
        )
        self.assertEqual(task_classification.classify_task(task), "mixed")

    def test_returns_none_with_no_confident_signal(self):
        task = "### Task 6: Docs\n**Files:**\n- Modify: `README.md`\n"
        self.assertIsNone(task_classification.classify_task(task))


class TestExtractTouchedPaths(unittest.TestCase):
    def test_extracts_every_backtick_path_in_order(self):
        task = "### Task 1\n**Files:**\n- Create: `a.py`\n- Modify: `b.py`\n"
        self.assertEqual(task_classification.extract_touched_paths(task), ["a.py", "b.py"])

    def test_preserves_writing_plans_line_qualified_paths_verbatim(self):
        # CRITICAL finding: writing-plans' own task template routinely emits a `Modify:` target
        # as a line-range-qualified path (`existing.py:123-145`, per the skill's own Task
        # Structure example), not a bare filesystem path. extract_touched_paths must return this
        # EXACT string, unmodified -- it is the SAME string estimate_required_context uses as a
        # files_touched_sizes dict key, and Task 2's derive_files_touched_sizes (the one place
        # that ever touches the filesystem) is where the line-range suffix gets stripped for
        # stat'ing, not here. Normalizing it in two places would let the two drift.
        task = "### Task 1\n**Files:**\n- Modify: `existing.py:123-145`\n"
        self.assertEqual(task_classification.extract_touched_paths(task), ["existing.py:123-145"])


class TestEstimateRequiredContext(unittest.TestCase):
    def test_sums_file_sizes_plus_overhead(self):
        task = "### Task 1\n**Files:**\n- Modify: `a.py`\n- Modify: `b.py`\n"
        sizes = {"a.py": 4000, "b.py": 8000}
        result = task_classification.estimate_required_context(task, sizes)
        self.assertEqual(result, (4000 + 8000) // 4 + task_classification.OVERHEAD_TOKENS)

    def test_missing_size_data_counts_as_zero_not_an_error(self):
        task = "### Task 1\n**Files:**\n- Create: `new.py`\n"
        result = task_classification.estimate_required_context(task, {})
        self.assertEqual(result, task_classification.OVERHEAD_TOKENS)


class TestAssembleCandidates(unittest.TestCase):
    def test_reads_reviewers_and_ladder_from_shared_config(self):
        fake_resolved = {
            "policy": {"ladder": ["claude/opus-5", "codex/terra"]},
            "reviewers": [
                {"key": "claude/opus-5", "model": "opus", "runtime": None, "vendor": "anthropic"},
                {
                    "key": "codex/terra",
                    "model": "gpt-5.6-terra",
                    "runtime": "codex",
                    "vendor": "openai",
                    "task_affinity": "backend",
                    "context_limit": 1_000_000,
                },
            ],
        }
        candidates, top_n_keys = dispatch_injection.assemble_candidates(
            "/repo", {}, cfg_resolve_fn=lambda cwd, env: fake_resolved
        )
        self.assertEqual(top_n_keys, ["claude/opus-5", "codex/terra"])
        self.assertEqual(candidates[1]["task_affinity"], "backend")
        self.assertEqual(candidates[1]["runtime"], "codex")

    def test_resolves_end_to_end_against_todays_real_config_shape(self):
        # CRITICAL finding: ai-kit-spec-config's real generated review-spec.toml carries the
        # schema-known key/model/vendor/cli/command PLUS several optional flat fields it already
        # prompts for and writes today -- strength (Step 2.6), effort/service_tier (Step 2.4, for
        # a CLI whose builder uses them), and a per-entry timeout_tiers override (Step 2.8) --
        # confirmed by reading ai-kit-spec-config/SKILL.md and ai_kit_spec.config_io.
        # _KNOWN_REVIEWER_FIELDS directly, not assumed. Only task_affinity/context_limit are
        # genuinely never written yet (Global Constraints). Proves assemble_candidates ->
        # build_dispatch_injection still resolves correctly (ladder-position-only ranking)
        # against that REAL shape -- including the optional fields it DOES carry -- not only
        # against a fixture that mischaracterizes today's real output as narrower than it is.
        fake_resolved = {
            "policy": {"ladder": ["claude/opus-5", "codex/terra"]},
            "reviewers": [
                {
                    "key": "claude/opus-5",
                    "model": "opus",
                    "runtime": None,
                    "vendor": "anthropic",
                    "strength": "planning",
                },
                {
                    "key": "codex/terra",
                    "model": "gpt-5.6-terra",
                    "runtime": "codex",
                    "vendor": "openai",
                    "strength": "coding",
                    "effort": "high",
                    "service_tier": "priority",
                    "timeout_tiers": [900, 1800],
                },
            ],
        }
        candidates, top_n_keys = dispatch_injection.assemble_candidates(
            "/repo", {}, cfg_resolve_fn=lambda cwd, env: fake_resolved
        )
        self.assertIsNone(candidates[0]["task_affinity"])
        self.assertIsNone(candidates[0]["context_limit"])
        self.assertEqual(candidates[1]["effort"], "high")
        self.assertEqual(candidates[1]["service_tier"], "priority")
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        result = dispatch_injection.build_dispatch_injection(
            dispatch_injection.BuildInjectionRequest(task, candidates, {}, {}, top_n_keys),
            options=dispatch_injection.BuildInjectionOptions(quota={}),
        )
        self.assertEqual(result, {"mode": "native", "key": "claude/opus-5",
                                  "runtime": None, "model": "opus"})

    def test_purpose_field_is_threaded_through_from_config(self):
        def fake_cfg_resolve(cwd, env):
            return {
                "policy": {"ladder": ["a"]},
                "reviewers": [
                    {
                        "key": "a",
                        "model": "m",
                        "runtime": "codex",
                        "vendor": "openai",
                        "command": "codex exec -m {model}",
                        "purpose": "execute",
                    },
                ],
            }

        candidates, _top_n_keys = dispatch_injection.assemble_candidates(
            "/fake/cwd", {}, cfg_resolve_fn=fake_cfg_resolve
        )
        self.assertEqual(candidates[0]["purpose"], "execute")

    def test_missing_purpose_field_comes_back_none(self):
        def fake_cfg_resolve(cwd, env):
            return {
                "policy": {"ladder": ["a"]},
                "reviewers": [{"key": "a", "model": "m", "runtime": "codex", "vendor": "openai"}],
            }

        candidates, _ = dispatch_injection.assemble_candidates(
            "/fake/cwd", {}, cfg_resolve_fn=fake_cfg_resolve
        )
        self.assertIsNone(candidates[0]["purpose"])


class TestDeriveFilesTouchedSizes(unittest.TestCase):
    def test_stats_real_existing_files_and_zeros_missing_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_path = os.path.join(tmp, "a.py")
            with open(real_path, "w") as f:
                f.write("x" * 4000)
            task = "### Task 1\n**Files:**\n- Modify: `a.py`\n- Create: `new.py`\n"
            sizes = dispatch_injection.derive_files_touched_sizes(task, tmp)
        self.assertEqual(sizes, {"a.py": 4000, "new.py": 0})

    def test_resolves_writing_plans_line_qualified_paths_to_the_real_file(self):
        # CRITICAL finding: writing-plans' own standard task shape (this plan's own Task
        # Structure, and every task in this very document) writes a Modify: target as
        # `existing.py:123-145` -- a line-range-qualified path, never a bare filesystem path.
        # Joining that literal string against cwd always misses (isfile() is False for a path
        # containing a trailing `:123-145`), so every real Modify: target silently contributed 0
        # bytes and context-size filtering was inert for the framework's own standard shape. The
        # dict KEY stays the raw, unqualified string (estimate_required_context looks sizes up by
        # extract_touched_paths' own raw output) -- only the on-disk lookup is normalized.
        with tempfile.TemporaryDirectory() as tmp:
            real_path = os.path.join(tmp, "existing.py")
            with open(real_path, "w") as f:
                f.write("x" * 4000)
            task = "### Task 1\n**Files:**\n- Modify: `existing.py:123-145`\n"
            sizes = dispatch_injection.derive_files_touched_sizes(task, tmp)
        self.assertEqual(sizes, {"existing.py:123-145": 4000})


class TestComputeLadderKeys(unittest.TestCase):
    def test_includes_a_candidate_ranked_outside_policy_ladder(self):
        # CRITICAL finding (Rounds 4-5 capability escalation): top_n_keys (policy.ladder's own
        # configured keys) is an INCOMPLETE proxy for the real, full ordered candidate set --
        # codex/terra below is narrowed/ranked by resolve_execute_candidates (no affinity/context
        # rejection) but is absent from top_n_keys entirely; it must still appear here, ranked
        # last, or a stuck top_n_keys candidate could never be proven "escalated past" it.
        candidates = [
            {
                "key": "claude/opus-5",
                "model": "opus",
                "runtime": None,
                "vendor": "anthropic",
                "task_affinity": None,
                "context_limit": None,
            },
            {
                "key": "codex/terra",
                "model": "gpt-5.6-terra",
                "runtime": "codex",
                "vendor": "openai",
                "task_affinity": None,
                "context_limit": None,
            },
        ]
        task = "### Task 1\n**Files:**\n- Create: `a.py`\n"
        result = dispatch_injection.compute_ladder_keys(
            dispatch_injection.BuildInjectionRequest(
                task, candidates, {}, {}, ["claude/opus-5"]))
        self.assertEqual(result, ["claude/opus-5", "codex/terra"])


class TestBuildDispatchInjection(unittest.TestCase):
    def test_stored_runtime_is_kept_for_routing(self):
        # Routing, not assembly, decides native vs subprocess. A host-selectable alias keeps
        # its stored runtime so a later route walk can still see it.
        resolved = {"policy": {"ladder": ["claude/opus"]},
                    "reviewers": [{"key": "claude/opus", "runtime": "claude",
                                   "model": "opus"}]}
        candidates, _ = dispatch_injection.assemble_candidates(
            "/repo", {"CLAUDECODE": "1"}, cfg_resolve_fn=lambda cwd, env: resolved)
        self.assertEqual(candidates[0]["runtime"], "claude")

    def test_native_mode_when_top_candidate_has_quota(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "claude/opus-5",
                "runtime": None,
                "model": "opus",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            }
        ]
        result = dispatch_injection.build_dispatch_injection(
            dispatch_injection.BuildInjectionRequest(
                task, candidates, {"server/api.py": 1000}, {}, ["claude/opus-5"]
            ),
            options=dispatch_injection.BuildInjectionOptions(quota={}),
        )
        self.assertEqual(
            result,
            {"mode": "native", "key": "claude/opus-5", "runtime": None, "model": "opus"},
        )

    def test_external_cli_mode_when_top_candidate_is_another_cli(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "codex/terra",
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            }
        ]
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(
                    task, candidates, {"server/api.py": 1000}, {}, ["codex/terra"]
                ),
                options=dispatch_injection.BuildInjectionOptions(quota={}),
            )
        # No routes mapping fails closed: an unknown host and empty inventory skip a
        # subprocess candidate as not installed, and that skip is permanent.
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "not_installed"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_escalates_past_a_quota_exhausted_top_candidate(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "claude/opus-5",
                "runtime": None,
                "model": "opus",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            },
            {
                "key": "codex/terra",
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            },
        ]
        quota = {"claude/opus-5": {"available": False}, "codex/terra": {"available": True}}
        result = dispatch_injection.build_dispatch_injection(
            dispatch_injection.BuildInjectionRequest(
                task, candidates, {}, {}, ["claude/opus-5", "codex/terra"]
            ),
            options=dispatch_injection.BuildInjectionOptions(
                quota=quota,
                routes={"claude/opus-5": "native", "codex/terra": "subprocess"},
            ),
        )
        self.assertEqual(result["mode"], "external_cli")
        self.assertEqual(result["key"], "codex/terra")

    def test_unknown_runtime_is_skipped_and_the_next_candidate_runs(self):
        # Replaces the deleted builder probe: an out-of-table runtime is a permanent skip
        # route, recorded even when a cached quota row says it is unavailable for quota.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "gemini/main",
                "runtime": "gemini",
                "model": "gemini-3-pro",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            },
            {
                "key": "codex/terra",
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            },
        ]
        quota = {
            "gemini/main": {"available": False, "reason": "quota"},
            "codex/terra": {"available": True},
        }
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(
                    task, candidates, {}, {}, ["gemini/main", "codex/terra"]
                ),
                dispatch_injection.BuildInjectionOptions(
                    quota=quota,
                    routes={"gemini/main": "unknown_runtime", "codex/terra": "subprocess"},
                ),
            )
        self.assertEqual(result["key"], "codex/terra")
        self.assertIn("skipping gemini/main for execution: route unknown_runtime",
                      stderr.getvalue())

    def test_claude_off_its_native_route_is_recorded_as_review_only(self):
        # D-15 screen order: a purpose-unset claude candidate is exempt from the execute screen.
        # Off its native route the walk records review_only, a permanent skip, and continues.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "claude-cli/opus-5",
                "runtime": "claude",
                "model": "opus",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            },
            {
                "key": "codex/terra",
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            },
        ]
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(
                    task, candidates, {}, {}, ["claude-cli/opus-5", "codex/terra"]
                ),
                options=dispatch_injection.BuildInjectionOptions(
                    quota={},
                    routes={"claude-cli/opus-5": "review_only", "codex/terra": "subprocess"},
                ),
            )
        self.assertEqual(result["mode"], "external_cli")
        self.assertEqual(result["runtime"], "codex")
        self.assertIn("skipping claude-cli/opus-5 for execution: route review_only",
                      stderr.getvalue())
        self.assertNotIn("cannot be an execution CLI", stderr.getvalue())

    def test_cli_claude_purpose_execute_raises_value_error_naming_the_supported_clis(self):
        # D-15: an explicit purpose = "execute" claude entry is a hard error, never a fallback.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "claude-cli/opus-5",
                "runtime": "claude",
                "model": "opus",
                "purpose": "execute",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            }
        ]
        with self.assertRaises(ValueError) as ctx:
            dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(
                    task, candidates, {}, {}, ["claude-cli/opus-5"]
                ),
                options=dispatch_injection.BuildInjectionOptions(quota={}),
            )
        self.assertIn("codex, copilot, cursor, opencode, pi", str(ctx.exception))

    def test_cli_purpose_execute_exits_2_with_the_supported_list_on_stderr(self):
        candidates = [
            {
                "key": "claude-cli/opus-5",
                "runtime": "claude",
                "model": "opus",
                "vendor": "anthropic",
                "purpose": "execute",
                "task_affinity": None,
                "context_limit": None,
            }
        ]

        def fake_assemble(cwd, env):
            return candidates, ["claude-cli/opus-5"]

        out, stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            # The route is pinned (a non-Claude host's exec route for claude/opus), so no real
            # host, runtimes cache or CLI listing is ever consulted.
            with contextlib.redirect_stderr(stderr):
                rc = superpowers_cli.main(
                    [
                        "resolve-injection",
                        "--cwd",
                        tmp,
                        "--task-file",
                        task_file,
                        "--quota-path",
                        quota_path,
                    ],
                    assemble_candidates_fn=fake_assemble,
                    cache_read_json_fn=lambda path: {},
                    cache_write_json_fn=lambda path, data: None,
                    refresh_quota_cache_fn=lambda config, keys, existing, _ttl: {},
                    route_all_fn=lambda entries, _ctx: {"claude-cli/opus-5": "review_only"},
                    env_fn=lambda: {"HOME": tmp, "XDG_CACHE_HOME": tmp},
                    stdout=out,
                )
        self.assertEqual(rc, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("codex, copilot, cursor, opencode, pi", stderr.getvalue())
        self.assertIn("ai-kit-spec-execute-superpowers:", stderr.getvalue())

    def test_cli_custom_entry_with_purpose_execute_exits_2_not_a_traceback(self):
        # B-CR-01: a D-21 custom entry declared an executor is a config error (exit 2).
        candidates = [{
            "key": "g", "runtime": None, "model": "grok-4", "vendor": "xai",
            "command": "grok -p {prompt} -m {model}", "purpose": "execute",
            "task_affinity": None, "context_limit": None,
        }]
        out, stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            with contextlib.redirect_stderr(stderr):
                rc = superpowers_cli.main(
                    ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                     "--quota-path", os.path.join(tmp, "quota.json")],
                    assemble_candidates_fn=lambda cwd, env: (candidates, ["g"]),
                    cache_read_json_fn=lambda path: {},
                    cache_write_json_fn=lambda path, data: None,
                    refresh_quota_cache_fn=lambda config, keys, existing, _ttl: {},
                    route_all_fn=lambda entries, _ctx: {"g": "custom"},
                    env_fn=lambda: {"HOME": tmp, "XDG_CACHE_HOME": tmp},
                    stdout=out,
                )
        self.assertEqual(rc, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("custom entries run only as reviewers", stderr.getvalue())

    def test_resolve_injection_prints_the_d15_skip_warning_once(self):
        # A-IN-06: the ladder pass and the build pass both screen; warn only once.
        candidates = [
            {"key": "g", "runtime": "grok", "model": "m", "vendor": "x", "purpose": None,
             "task_affinity": None, "context_limit": None},
            {"key": "c", "runtime": "codex", "model": "m", "vendor": "o", "purpose": None,
             "task_affinity": None, "context_limit": None},
        ]
        out, stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            with contextlib.redirect_stderr(stderr):
                rc = superpowers_cli.main(
                    ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                     "--quota-path", os.path.join(tmp, "quota.json")],
                    assemble_candidates_fn=lambda cwd, env: (candidates, ["g", "c"]),
                    cache_read_json_fn=lambda path: {},
                    cache_write_json_fn=lambda path, data: None,
                    refresh_quota_cache_fn=lambda config, keys, existing, _ttl: {},
                    route_all_fn=lambda entries, _ctx: {
                        "g": "review_only", "c": "subprocess"},
                    stdout=out,
                )
        self.assertEqual(rc, 0)
        self.assertEqual(stderr.getvalue().count("skipping g for execution: route review_only"), 1)

    def test_no_surviving_candidates_raises_value_error(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        with self.assertRaises(ValueError):
            dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(task, [], {}, {}, []),
                options=dispatch_injection.BuildInjectionOptions(quota={}),
            )

    def test_every_candidate_quota_exhausted_raises_quota_exhausted_error_with_reasons(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "claude/opus-5",
                "runtime": None,
                "model": "opus",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            }
        ]
        quota = {
            "claude/opus-5": {
                "available": False,
                "reason": "quota",
                "detail": "usage limit reached",
            }
        }
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(
                    task, candidates, {}, {}, ["claude/opus-5"]
                ),
                options=dispatch_injection.BuildInjectionOptions(quota=quota),
            )
        self.assertEqual(ctx.exception.tried, ["claude/opus-5"])
        self.assertEqual(ctx.exception.reasons, {"claude/opus-5": "quota"})
        self.assertFalse(ctx.exception.all_auth_failures)
        self.assertEqual(ctx.exception.task_type, "backend")

    def test_auth_failure_is_classified_distinctly_and_flagged_all_auth_failures(self):
        # HIGH finding: an unauthenticated/unentitled candidate must never look like a real,
        # time-bound quota exhaustion -- .all_auth_failures is what tells a caller to skip the
        # futile later re-run and surface an actionable setup error instead.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "codex/terra",
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            }
        ]
        quota = {
            "codex/terra": {
                "available": False,
                "reason": "auth",
                "detail": "Error: not authenticated",
            }
        }
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(task, candidates, {}, {}, ["codex/terra"]),
                options=dispatch_injection.BuildInjectionOptions(
                    quota=quota, routes={"codex/terra": "subprocess"}),
            )
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "auth"})
        self.assertTrue(ctx.exception.all_auth_failures)
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_timeout_failure_classified_distinctly_not_quota(self):
        # HIGH finding: a probe timeout is a real, non-time-bound problem (a hung/broken CLI
        # invocation) -- it must never be classified "quota" and invite a futile later re-run.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "codex/terra",
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            }
        ]
        quota = {
            "codex/terra": {
                "available": False,
                "reason": "timeout",
                "detail": "timed out after 30s",
            }
        }
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(task, candidates, {}, {}, ["codex/terra"]),
                options=dispatch_injection.BuildInjectionOptions(
                    quota=quota, routes={"codex/terra": "subprocess"}),
            )
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "timeout"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_malformed_command_template_classified_as_configuration_not_quota(self):
        # HIGH finding: a bad/missing command template is a config problem -- never fixed by
        # waiting for quota to refill.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "codex/terra",
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            }
        ]
        quota = {
            "codex/terra": {
                "available": False,
                "reason": "configuration",
                "detail": "reviewer 'codex/terra' has a malformed command template: KeyError",
            }
        }
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(task, candidates, {}, {}, ["codex/terra"]),
                options=dispatch_injection.BuildInjectionOptions(
                    quota=quota, routes={"codex/terra": "subprocess"}),
            )
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "configuration"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_os_error_style_failure_classified_as_dispatch_unavailable(self):
        # HIGH finding: the CLI binary itself failing to launch is not a quota problem either.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "codex/terra",
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            }
        ]
        quota = {
            "codex/terra": {
                "available": False,
                "reason": "dispatch_unavailable",
                "detail": "[Errno 2] No such file or directory: 'codex'",
            }
        }
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(task, candidates, {}, {}, ["codex/terra"]),
                options=dispatch_injection.BuildInjectionOptions(
                    quota=quota, routes={"codex/terra": "subprocess"}),
            )
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "dispatch_unavailable"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_arbitrary_nonzero_exit_classified_as_real_error_not_quota(self):
        # HIGH finding (the core bug): prior to this revision, EVERY non-auth detail defaulted to
        # "quota" -- a bad model id or any other unrelated failure text is a real error, not a
        # time-bound rate limit, and must never invite a futile later re-run.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "codex/terra",
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            }
        ]
        quota = {
            "codex/terra": {
                "available": False,
                "reason": "real_error",
                "detail": "Error: unrecognized model id",
            }
        }
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(task, candidates, {}, {}, ["codex/terra"]),
                options=dispatch_injection.BuildInjectionOptions(
                    quota=quota, routes={"codex/terra": "subprocess"}),
            )
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "real_error"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_any_quota_recoverable_true_when_at_least_one_reason_is_quota(self):
        # HIGH finding: any_quota_recoverable is the general gate a caller uses to decide whether
        # a later re-run accomplishes anything -- True as soon as ANY tried
        # candidate's reason is "quota", even when others in the same batch are permanent.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {
                "key": "claude/opus-5",
                "runtime": None,
                "model": "opus",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            },
            {
                "key": "codex/terra",
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            },
        ]
        quota = {
            "claude/opus-5": {
                "available": False,
                "reason": "quota",
                "detail": "usage limit reached",
            },
            "codex/terra": {"available": False, "reason": "auth", "detail": "not authenticated"},
        }
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(
                    task, candidates, {}, {}, ["claude/opus-5", "codex/terra"]
                ),
                options=dispatch_injection.BuildInjectionOptions(
                    quota=quota,
                    routes={"claude/opus-5": "native", "codex/terra": "subprocess"},
                ),
            )
        self.assertTrue(ctx.exception.any_quota_recoverable)
        self.assertFalse(ctx.exception.all_auth_failures)


class TestReasonsSummary(unittest.TestCase):
    def test_summarizes_a_reasons_dict_merged_across_more_than_one_call(self):
        # CRITICAL finding (recurrence guard): this is the exact shape cli.py's resolve-injection
        # must recompute over -- a reasons dict merging an earlier wave's own already-known
        # reasons (passed in via --excluded-reasons-json) with a fresh QuotaExhaustedError's own
        # `.reasons` from THIS call, since a single call's own exception never sees a key that was
        # excluded before its ladder walk even started.
        merged = {"claude/opus-5": "auth", "codex/terra": "quota"}
        summary = dispatch_injection.reasons_summary(merged)
        self.assertFalse(summary["all_auth_failures"])
        self.assertTrue(summary["any_quota_recoverable"])

    def test_empty_reasons_is_neither_all_auth_nor_quota_recoverable(self):
        summary = dispatch_injection.reasons_summary({})
        self.assertFalse(summary["all_auth_failures"])
        self.assertFalse(summary["any_quota_recoverable"])


class TestComputeResumeExclusions(unittest.TestCase):
    def test_quota_reason_keys_are_not_permanently_excluded(self):
        # CRITICAL finding (recurrence): a persisted resume state must NOT permanently exclude a
        # candidate whose only failure reason was quota -- it must be eligible again once quota
        # recovers, or a later re-run can never actually resume anything.
        result = dispatch_injection.compute_resume_exclusions(
            tried=["claude/opus-5", "codex/terra"],
            reasons={"claude/opus-5": "quota", "codex/terra": "auth"},
            prior_excluded_keys=[],
        )
        self.assertEqual(result, ["codex/terra"])

    def test_prior_permanent_exclusions_are_preserved(self):
        result = dispatch_injection.compute_resume_exclusions(
            tried=["grok/main"],
            reasons={"grok/main": "no_usable_dispatch"},
            prior_excluded_keys=["codex/terra"],
        )
        self.assertEqual(result, ["codex/terra", "grok/main"])

    def test_round_trip_quota_recovery_makes_candidate_eligible_again(self):
        # The round-trip this CRITICAL finding requires: an all-quota-exhausted ladder computes a
        # resume-state exclusion set, THEN (once quota recovers) a fresh build_dispatch_injection
        # call using THAT exclusion set must be able to pick the previously-exhausted candidate
        # again -- never permanently locked out by its own earlier exhaustion event.
        candidates = [
            {
                "key": "claude/opus-5",
                "runtime": None,
                "model": "opus",
                "task_affinity": "backend",
                "context_limit": 1_000_000,
            }
        ]
        quota_when_exhausted = {
            "claude/opus-5": {"available": False, "reason": "quota", "detail": "usage limit"}
        }
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                dispatch_injection.BuildInjectionRequest(
                    task, candidates, {}, {}, ["claude/opus-5"]
                ),
                options=dispatch_injection.BuildInjectionOptions(quota=quota_when_exhausted),
            )
        excluded_keys = dispatch_injection.compute_resume_exclusions(
            ctx.exception.tried, ctx.exception.reasons, []
        )
        self.assertEqual(excluded_keys, [])  # a quota-only reason -- nothing permanently excluded

        # Resume: candidates filtered by excluded_keys (none removed here), quota now recovered.
        surviving = [c for c in candidates if c["key"] not in excluded_keys]
        quota_recovered = {"claude/opus-5": {"available": True}}
        result = dispatch_injection.build_dispatch_injection(
            dispatch_injection.BuildInjectionRequest(task, surviving, {}, {}, ["claude/opus-5"]),
            options=dispatch_injection.BuildInjectionOptions(quota=quota_recovered),
        )
        self.assertEqual(result["key"], "claude/opus-5")


class TestDispatchSuperpowersTask(unittest.TestCase):
    def test_delegates_to_dispatch_execute_with_a_real_candidate_dict(self):
        injection = {
            "mode": "external_cli",
            "key": "codex/terra",
            "runtime": "codex",
            "model": "gpt-5.6-terra",
            "effort": "high",
            "service_tier": None,
        }
        captured = {}

        def fake_dispatch_execute(spec):
            captured.update(
                candidate=spec.candidate, prompt=spec.prompt, target_dir=spec.target_dir
            )
            return {
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "command": "codex exec ...",
                "returncode": 0,
                "stdout": "ok",
                "stderr": "",
                "timed_out": False,
            }

        result = dispatch_injection.dispatch_superpowers_task(
            dispatch_injection.DispatchTaskRequest(
                injection, "do the task", "/real/scratch/dir", 900
            ),
            seams=dispatch_injection.SuperpowersDispatchSeams(
                dispatch_execute_fn=fake_dispatch_execute,
            ),
        )
        self.assertEqual(captured["target_dir"], "/real/scratch/dir")
        self.assertEqual(captured["candidate"]["runtime"], "codex")
        self.assertEqual(captured["candidate"]["effort"], "high")
        self.assertEqual(result["returncode"], 0)

    def test_native_injection_raises_value_error(self):
        injection = {"mode": "native", "runtime": "claude", "model": "opus",
                     "key": "claude/opus-5"}
        with self.assertRaises(ValueError):
            dispatch_injection.dispatch_superpowers_task(
                dispatch_injection.DispatchTaskRequest(injection, "prompt", "/dir", 900)
            )

    def test_real_dispatch_execute_path_produces_a_real_workspace_write_command(self):
        # Confirms this wrapper genuinely reaches ai_kit_spec.execute_dispatch.dispatch_execute's
        # OWN real runner spec (HIGH finding: never a second supervisor, never a
        # "{target_dir}" placeholder) by calling the real, un-mocked dispatch_execute and only
        # substituting ITS OWN runner_fn (the actual subprocess launch).
        import tempfile

        from ai_kit_spec.execute_dispatch import dispatch_execute as real_dispatch_execute
        from ai_kit_spec.runner_dispatch import RunnerResult

        injection = {
            "mode": "external_cli",
            "key": "codex/terra",
            "runtime": "codex",
            "model": "gpt-5.6-terra",
            "effort": None,
            "service_tier": None,
        }
        captured = {}

        def fake_runner(spec, prompt, seams):
            del prompt, seams
            captured["spec"] = spec
            argv = ["node", "runner", *runner_dispatch.runner_flags(spec)[-2:]]
            return RunnerResult(0, "DONE", {"status": "ok"}, None, False, argv, "")

        def dispatch_execute_with_fake_subprocess(spec):
            from ai_kit_spec.execute_dispatch import ExecuteSeams

            return real_dispatch_execute(spec, seams=ExecuteSeams(runner_fn=fake_runner))

        with tempfile.TemporaryDirectory() as target:
            result = dispatch_injection.dispatch_superpowers_task(
                dispatch_injection.DispatchTaskRequest(
                    injection, "do the task", target, 900
                ),
                seams=dispatch_injection.SuperpowersDispatchSeams(
                    dispatch_execute_fn=dispatch_execute_with_fake_subprocess,
                ),
            )
        self.assertEqual(captured["spec"].cwd, target)
        self.assertEqual(result["command"], shlex.join(
            ["node", "runner", "--codex-sandbox", "workspace-write"]
        ))


class TestUnavailabilityReason(unittest.TestCase):
    """D-13: _unavailability_reason reads the stored typed reason, never the detail text."""

    def test_stored_reason_wins_over_detail_text(self):
        quota = {"k": {"available": False, "reason": "auth", "detail": "quota"}}
        self.assertEqual(dispatch_injection._unavailability_reason(quota, "k"), "auth")

    def test_legacy_entry_without_reason_reads_real_error(self):
        quota = {"k": {"available": False, "detail": "usage limit reached"}}
        self.assertEqual(dispatch_injection._unavailability_reason(quota, "k"), "real_error")


class TestClassifyDispatchFailure(unittest.TestCase):
    def test_ok_on_zero_returncode(self):
        self.assertEqual(
            dispatch_injection.classify_dispatch_failure({"returncode": 0}), "ok",
        )

    def test_quota_on_runner_reason(self):
        self.assertEqual(
            dispatch_injection.classify_dispatch_failure(
                {"returncode": 75, "reason": "quota"}
            ),
            "quota",
        )

    def test_answer_text_on_success_is_never_classified(self):
        # R8/D-13: the model's answer (stdout) is never classified -- an answer saying
        # "quota exceeded" with exit 0 is a success, whatever reason text rides along.
        self.assertEqual(
            dispatch_injection.classify_dispatch_failure(
                {"returncode": 0, "stdout": "quota exceeded", "reason": "quota"}
            ),
            "ok",
        )

    def test_quota_on_hinted_transient_capacity_exit(self):
        payload = {
            "returncode": 75, "reason": "capacity",
            "status": {
                "status": "transient", "exit": "75",
                "retry_after_s": "600", "cycle": "0",
            },
        }
        self.assertEqual(dispatch_injection.classify_dispatch_failure(payload), "quota")

    def test_quota_on_bare_transient_exit(self):
        # 25.1 WR-01: a bare 75 is a spent ladder whose hint was dropped (state unwritable);
        # it is the same lane's wait, never Step 2's capacity fix. No re-invoke: no tokens.
        self.assertEqual(
            dispatch_injection.classify_dispatch_failure({
                "returncode": 75, "reason": "capacity",
                "status": {"status": "transient", "exit": "75"},
            }),
            "quota",
        )

    def test_real_error_on_non_numeric_hint(self):
        self.assertEqual(
            dispatch_injection.classify_dispatch_failure({
                "returncode": 75, "reason": "capacity",
                "status": {
                    "status": "transient", "retry_after_s": "600s", "cycle": "0",
                },
            }),
            "real_error",
        )

    def test_quota_on_transient_hard_tier_stop(self):
        # 25.1 WR-01: a spent transient hard tier is an owner stop, not a capacity error.
        for stopped in ("hard-waits", "cap"):
            with self.subTest(stopped=stopped):
                self.assertEqual(
                    dispatch_injection.classify_dispatch_failure({
                        "returncode": 69, "reason": "capacity",
                        "status": {"status": "transient", "exit": "69", "stopped": stopped},
                    }),
                    "quota",
                )

    def test_real_error_on_transient_exit_1(self):
        self.assertEqual(
            dispatch_injection.classify_dispatch_failure({
                "returncode": 1, "reason": "capacity",
                "status": {"status": "transient", "exit": "1"},
            }),
            "real_error",
        )

    def test_quota_on_terminal_quota_exit_69(self):
        self.assertEqual(
            dispatch_injection.classify_dispatch_failure({
                "returncode": 69, "reason": "quota",
                "status": {"status": "quota", "exit": "69", "stopped": "hard-waits"},
            }),
            "quota",
        )

    def test_real_error_on_auth_reason(self):
        # HIGH finding: an auth/entitlement/setup failure must classify as real_error, never
        # quota -- it will never be fixed by a later re-run.
        self.assertEqual(
            dispatch_injection.classify_dispatch_failure(
                {"returncode": 69, "reason": "auth"}
            ),
            "real_error",
        )

    def test_real_error_on_unrelated_nonzero_returncode(self):
        self.assertEqual(
            dispatch_injection.classify_dispatch_failure(
                {"returncode": 1, "reason": "real_error"}
            ),
            "real_error",
        )

    def test_real_error_on_timeout_result(self):
        self.assertEqual(
            dispatch_injection.classify_dispatch_failure(
                {"returncode": -9, "reason": "timeout", "timed_out": True}
            ),
            "real_error",
        )

    def test_wake_tokens_come_from_the_nested_status_dict(self):
        # The SKILL's quota branch reads retry_after_s and cycle from the nested status dict,
        # the parsed AIKIT-XAI line. Both tokens live nowhere else in the dispatch result, so
        # this runs the exact extraction the SKILL shows and asserts both values.
        payload = json.dumps({
            "runtime": "pi", "model": "router-env/x", "returncode": 75, "reason": "quota",
            "status": {"status": "quota", "exit": "75", "retry_after_s": "600", "cycle": "2"},
        })
        # Run the exact one-liners the SKILL shows, so this fails if they drift.
        skill = pathlib.Path(__file__).resolve().parents[1].joinpath(
            "skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md"
        ).read_text(encoding="utf-8")
        out = {}
        for token in ("retry_after_s", "cycle"):
            shown = (
                'd=json.loads(sys.argv[1]); s=d.get("status") or {}; '
                f'print("" if s.get("{token}") is None else s.get("{token}"))'
            )
            self.assertIn(shown, skill)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), unittest.mock.patch.object(
                sys, "argv", ["skill", payload]
            ):
                exec(compile("import json,sys; " + shown, "<skill>", "exec"))
            out[token] = buf.getvalue().strip()
        self.assertEqual(out, {"retry_after_s": "600", "cycle": "2"})
        self.assertEqual(
            dispatch_injection.classify_dispatch_failure(json.loads(payload)), "quota",
        )


class TestCliSubcommandHandlers(unittest.TestCase):
    def test_every_subcommand_has_a_handler(self):
        parser = superpowers_cli._build_parser()
        subparsers = next(a for a in parser._actions if a.dest == "command")
        assert subparsers.choices is not None
        self.assertEqual(set(superpowers_cli._COMMANDS), set(subparsers.choices))


def _session_routes(entries, _ctx):
    """A runtime-less candidate is the session default; a named runtime dispatches."""
    return {entry["key"]: "native" if entry.get("runtime") is None else "subprocess"
            for entry in entries}


class TestCliResolveInjection(unittest.TestCase):
    def test_resolve_injection_prints_native_json(self):
        candidates = [
            {
                "key": "claude/opus-5",
                "model": "opus",
                "runtime": None,
                "vendor": "anthropic",
                "task_affinity": None,
                "context_limit": None,
            }
        ]

        def fake_assemble(cwd, env):
            return candidates, ["claude/opus-5"]

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                [
                    "resolve-injection",
                    "--cwd",
                    tmp,
                    "--task-file",
                    task_file,
                    "--quota-path",
                    quota_path,
                ],
                assemble_candidates_fn=fake_assemble,
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, _ttl: {},
                route_all_fn=_session_routes,
                stdout=out,
            )
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(
            result,
            {
                "mode": "native",
                "runtime": None,
                "model": "opus",
                "key": "claude/opus-5",
                "ladder_keys": ["claude/opus-5"],
            },
        )

    def test_resolve_injection_prints_quota_exhausted_json_with_reasons(self):
        candidates = [
            {
                "key": "claude/opus-5",
                "model": "opus",
                "runtime": None,
                "vendor": "anthropic",
                "task_affinity": None,
                "context_limit": None,
            }
        ]

        def fake_assemble(cwd, env):
            return candidates, ["claude/opus-5"]

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                [
                    "resolve-injection",
                    "--cwd",
                    tmp,
                    "--task-file",
                    task_file,
                    "--quota-path",
                    quota_path,
                ],
                assemble_candidates_fn=fake_assemble,
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, _ttl: (
                    {
                        "claude/opus-5": {
                            "available": False,
                            "reason": "quota",
                            "detail": "usage limit reached",
                        }
                    }
                ),
                route_all_fn=_session_routes,
                stdout=out,
            )
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "quota_exhausted")
        self.assertEqual(result["tried"], ["claude/opus-5"])
        self.assertEqual(result["reasons"], {"claude/opus-5": "quota"})
        self.assertFalse(result["all_auth_failures"])
        # HIGH finding: any_quota_recoverable, not all_auth_failures, is the real gate Task 4's
        # SKILL.md now uses to decide whether a later re-run accomplishes anything.
        self.assertTrue(result["any_quota_recoverable"])
        # CRITICAL finding (Rounds 4-5 capability escalation): ladder_keys must be present even on
        # the quota_exhausted branch -- Step 2's own resumable-state persistence path is exactly
        # where a struggling candidate is first discovered, and Step 3's mid-dispatch "quota"
        # branch reads this same field shape.
        self.assertEqual(result["ladder_keys"], ["claude/opus-5"])

    def test_resolve_injection_derives_real_file_sizes_from_cwd(self):
        # CRITICAL finding: resolve-injection must derive files_touched_sizes itself (never rely
        # on a caller-supplied, always-empty default) so context-size filtering is actually live.
        candidates = [
            {
                "key": "claude/opus-5",
                "model": "opus",
                "runtime": None,
                "vendor": "anthropic",
                "task_affinity": None,
                "context_limit": None,
            }
        ]
        captured = {}

        def fake_build_dispatch_injection(request, _options=None):
            captured["sizes"] = request.files_touched_sizes
            return {"mode": "native", "runtime": None, "model": "opus",
                    "key": "claude/opus-5"}

        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "big.py"), "w") as f:
                f.write("x" * 4000)
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Modify: `big.py`\n")
            quota_path = os.path.join(tmp, "quota.json")
            superpowers_cli.main(
                [
                    "resolve-injection",
                    "--cwd",
                    tmp,
                    "--task-file",
                    task_file,
                    "--quota-path",
                    quota_path,
                ],
                assemble_candidates_fn=lambda cwd, env: (candidates, ["claude/opus-5"]),
                build_dispatch_injection_fn=fake_build_dispatch_injection,
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, _ttl: {},
                route_all_fn=_session_routes,
                stdout=io.StringIO(),
            )
        self.assertEqual(captured["sizes"], {"big.py": 4000})

    def test_resolve_injection_quota_exhausted_when_all_candidates_excluded(self):
        # CRITICAL finding: a single-candidate ladder, already excluded by --exclude-keys-json
        # (e.g. a mid-dispatch "quota" failure caught in Step 3, re-running resolve-injection with
        # that SAME candidate excluded) previously reached build_dispatch_injection_fn with an
        # EMPTY candidates list, which raised its own "no candidate survived narrowing" ValueError
        # -- the WRONG exception (a real curation-gap signal, never "we already tried everything")
        # -- UNCAUGHT here, crashing the whole resolve-injection call instead of reporting a
        # controlled quota_exhausted result the SKILL.md's own branch-on-mode logic already
        # handles. --excluded-reasons-json carries this wave's own already-known reason forward.
        candidates = [
            {
                "key": "claude/opus-5",
                "model": "opus",
                "runtime": None,
                "vendor": "anthropic",
                "task_affinity": None,
                "context_limit": None,
            }
        ]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                [
                    "resolve-injection",
                    "--cwd",
                    tmp,
                    "--task-file",
                    task_file,
                    "--quota-path",
                    quota_path,
                    "--exclude-keys-json",
                    json.dumps(["claude/opus-5"]),
                    "--excluded-reasons-json",
                    json.dumps({"claude/opus-5": "quota"}),
                ],
                assemble_candidates_fn=lambda cwd, env: (candidates, ["claude/opus-5"]),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, _ttl: {},
                route_all_fn=_session_routes,
                stdout=out,
            )
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "quota_exhausted")
        self.assertEqual(result["tried"], ["claude/opus-5"])
        self.assertEqual(result["reasons"], {"claude/opus-5": "quota"})
        self.assertTrue(result["any_quota_recoverable"])
        self.assertEqual(result["ladder_keys"], ["claude/opus-5"])

    def test_resolve_injection_reports_no_candidate_when_narrowing_drops_every_candidate(self):
        # HIGH finding: `candidates` is non-empty here (never excluded down to empty -- that's the
        # separate "every configured candidate already excluded" case above) but every one gets
        # dropped by affinity/context narrowing itself (a context_limit below this task's
        # required_context) -- build_dispatch_injection_fn's own "no candidate survived narrowing"
        # ValueError, previously uncaught, must never crash this command. It is a genuine curation
        # gap, never a quota-availability problem, so it gets its own "no_candidate" mode -- never
        # folded into "quota_exhausted", which would wrongly imply a later re-run could help.
        candidates = [
            {
                "key": "small-context/model",
                "model": "opus",
                "runtime": None,
                "vendor": "anthropic",
                "task_affinity": None,
                "context_limit": 10,
            }
        ]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "big.py"), "w") as f:
                f.write("x" * 4000)
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Modify: `big.py`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                [
                    "resolve-injection",
                    "--cwd",
                    tmp,
                    "--task-file",
                    task_file,
                    "--quota-path",
                    quota_path,
                ],
                assemble_candidates_fn=lambda cwd, env: (candidates, ["small-context/model"]),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, _ttl: {},
                route_all_fn=_session_routes,
                stdout=out,
            )
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "no_candidate")
        self.assertIn("no execute candidate survived", result["detail"])
        # ladder_keys is computed via the SAME affinity/context narrowing (compute_ladder_keys
        # shares _narrow_and_rank with build_dispatch_injection) -- the one candidate that failed
        # context narrowing for the dispatch call fails it here too, so the full ranked ladder is
        # also empty. This is consistent, not a second bug: ladder_keys never claims a candidate
        # narrowing already rejected is somehow still ranked.
        self.assertEqual(result["ladder_keys"], [])

    def test_resolve_injection_merges_wave_excluded_reasons_with_this_calls_own_quota_exhaustion(
        self,
    ):
        # CRITICAL finding: mixed quota/auth case -- a caller re-resolving mid-wave (one candidate
        # already excluded for a KNOWN reason from an earlier call, another going quota-exhausted
        # fresh THIS call) must see BOTH reasons in the final output, never just this call's own
        # narrower remaining-ladder walk (which never even visits an already-excluded candidate).
        candidates = [
            {
                "key": "claude/opus-5",
                "model": "opus",
                "runtime": None,
                "vendor": "anthropic",
                "task_affinity": None,
                "context_limit": None,
            },
            {
                "key": "codex/terra",
                "model": "gpt-5.6-terra",
                "runtime": "codex",
                "vendor": "openai",
                "task_affinity": None,
                "context_limit": None,
            },
        ]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                [
                    "resolve-injection",
                    "--cwd",
                    tmp,
                    "--task-file",
                    task_file,
                    "--quota-path",
                    quota_path,
                    "--exclude-keys-json",
                    json.dumps(["codex/terra"]),
                    "--excluded-reasons-json",
                    json.dumps({"codex/terra": "auth"}),
                ],
                assemble_candidates_fn=lambda cwd, env: (
                    candidates,
                    ["claude/opus-5", "codex/terra"],
                ),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, _ttl: (
                    {
                        "claude/opus-5": {
                            "available": False,
                            "reason": "quota",
                            "detail": "usage limit reached",
                        }
                    }
                ),
                route_all_fn=_session_routes,
                stdout=out,
            )
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "quota_exhausted")
        self.assertEqual(result["reasons"], {"claude/opus-5": "quota", "codex/terra": "auth"})
        self.assertEqual(sorted(result["tried"]), ["claude/opus-5", "codex/terra"])
        self.assertTrue(result["any_quota_recoverable"])
        self.assertFalse(result["all_auth_failures"])
        self.assertEqual(result["ladder_keys"], ["claude/opus-5", "codex/terra"])

    def test_escalation_excluded_keys_never_get_a_reason_or_enter_tried(self):
        # HIGH finding: a Rounds 4-5 capability-escalation exclusion is a healthy, NEVER-tried
        # candidate dropped purely for ranking reasons -- it must never receive the
        # "no_usable_dispatch" permanent-shaped fallback reason, must never appear in `tried`, and
        # must never be counted toward any_quota_recoverable/all_auth_failures -- distinct from a
        # genuine --exclude-keys-json member, which DOES get all of that. Here every real
        # candidate is quota-exhausted (a real, recoverable reason) while one candidate is excluded
        # ONLY via --escalation-excluded-keys-json.
        candidates = [
            {
                "key": "claude/opus-5",
                "model": "opus",
                "runtime": None,
                "vendor": "anthropic",
                "task_affinity": None,
                "context_limit": None,
            },
            {
                "key": "codex/terra",
                "model": "gpt-5.6-terra",
                "runtime": "codex",
                "vendor": "openai",
                "task_affinity": None,
                "context_limit": None,
            },
        ]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                [
                    "resolve-injection",
                    "--cwd",
                    tmp,
                    "--task-file",
                    task_file,
                    "--quota-path",
                    quota_path,
                    "--exclude-keys-json",
                    json.dumps(["codex/terra"]),
                    "--excluded-reasons-json",
                    json.dumps({"codex/terra": "quota"}),
                    "--escalation-excluded-keys-json",
                    json.dumps(["claude/opus-5"]),
                ],
                assemble_candidates_fn=lambda cwd, env: (
                    candidates,
                    ["claude/opus-5", "codex/terra"],
                ),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, _ttl: {},
                route_all_fn=_session_routes,
                stdout=out,
            )
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "quota_exhausted")
        # claude/opus-5 was excluded ONLY for capability-escalation reasons -- it must be absent
        # from both `tried` and `reasons` entirely, never defaulted to "no_usable_dispatch".
        self.assertEqual(result["tried"], ["codex/terra"])
        self.assertEqual(result["reasons"], {"codex/terra": "quota"})
        self.assertTrue(result["any_quota_recoverable"])

    def test_quota_reason_below_the_floor_or_outside_the_walk_never_gets_a_later_rerun(self):
        # A wave-tried quota key below the Rounds 4-5 floor, or a stale reason for a key that is
        # neither excluded nor tried, cannot be picked by this call: it must not make the result
        # look quota-recoverable.
        candidates = [
            {"key": "claude/opus-5", "model": "opus", "runtime": None, "vendor": "anthropic",
             "task_affinity": None, "context_limit": None},
            {"key": "codex/terra", "model": "gpt-5.6-terra", "runtime": "codex",
             "vendor": "openai", "task_affinity": None, "context_limit": None},
        ]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", os.path.join(tmp, "quota.json"),
                 "--exclude-keys-json", json.dumps(["claude/opus-5", "codex/terra"]),
                 "--excluded-reasons-json", json.dumps(
                     {"claude/opus-5": "auth", "codex/terra": "quota", "gone/key": "quota"}),
                 "--escalation-excluded-keys-json", json.dumps(["codex/terra"])],
                assemble_candidates_fn=lambda cwd, env: (
                    candidates, ["claude/opus-5", "codex/terra"]),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, _ttl: {},
                route_all_fn=_session_routes,
                stdout=out,
            )
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "quota_exhausted")
        self.assertFalse(result["any_quota_recoverable"])
        self.assertTrue(result["all_auth_failures"])


def _fresh_snapshot(clis):
    """A schema-current runtimes cache row. Claude rows carry the dated fallback ids."""
    from ai_kit_spec.detection import (
        CLAUDE_FALLBACK_MODEL_IDS,
        CLAUDE_MODEL_ALIASES,
        RUNTIMES_SCHEMA_VERSION,
    )

    rows = {}
    for rid, models in clis.items():
        row = {"installed": True, "path": f"/fake/{rid}"}
        if rid == "claude":
            row["aliases"] = list(CLAUDE_MODEL_ALIASES)
            row["models"] = list(models if models is not None else CLAUDE_FALLBACK_MODEL_IDS)
        elif models is not None:
            row["models"] = list(models)
        rows[rid] = row
    return {"schema_version": RUNTIMES_SCHEMA_VERSION, "clis": rows}


def _routed_native(entry, host):
    """A session default, or what the production host_can_select calls host-selectable."""
    runtime = entry.get("runtime")
    session_default = runtime is None and not entry.get("command")
    return session_default or routing.host_can_select(runtime, entry.get("model", ""), host)


def _route_all_recording(calls):
    """route_all that records its context and returns native for a claude alias, else subprocess."""

    def route_all_fn(entries, ctx):
        calls.append(ctx)
        routes = {}
        for entry in entries:
            runtime = entry.get("runtime")
            model = entry.get("model", "")
            if _routed_native(entry, ctx.host):
                routes[entry["key"]] = "native"
            elif runtime == "claude" or entry.get("command"):
                routes[entry["key"]] = "review_only"
            elif model == "missing":
                routes[entry["key"]] = "bad_model"
            elif model == "unchecked":
                routes[entry["key"]] = "unverified"
            else:
                routes[entry["key"]] = "subprocess"
        return routes

    return route_all_fn


class TestResolveInjectionRouting(unittest.TestCase):
    """resolve-injection routes per call and speaks host-agnostic payload names."""

    def _run(self, candidates, env, quota=None, refresh=None, top_n=None):
        from ai_kit_spec.cache import cache_write_json
        from ai_kit_spec.detection import cache_runtimes_path

        calls = []
        refreshed = []

        def recording_refresh(config, keys, existing, _ttl):
            refreshed.append(list(keys))
            if refresh is not None:
                return refresh(config, keys, existing, _ttl)
            return dict(quota or {})

        out, stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w", encoding="utf-8") as handle:
                handle.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            home = os.path.join(tmp, "home")
            cache = os.path.join(tmp, "cache")
            os.makedirs(home)
            os.makedirs(cache)
            scratch_env = {"HOME": home, "XDG_CACHE_HOME": cache, **env}
            cache_write_json(cache_runtimes_path(scratch_env), _fresh_snapshot({
                "claude": None, "codex": ["gpt-5.6-sol"],
            }))
            with contextlib.redirect_stderr(stderr):
                rc = superpowers_cli.main(
                    ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                     "--quota-path", os.path.join(tmp, "quota.json")],
                    assemble_candidates_fn=lambda cwd, _env: (
                        candidates, top_n or [c["key"] for c in candidates]),
                    cache_read_json_fn=lambda _path: dict(quota or {}),
                    cache_write_json_fn=lambda _path, _data: None,
                    refresh_quota_cache_fn=recording_refresh,
                    route_all_fn=_route_all_recording(calls),
                    env_fn=lambda: scratch_env,
                    stdout=out,
                )
        return rc, out.getvalue(), stderr.getvalue(), refreshed, calls

    def test_claude_host_returns_native_and_opencode_host_returns_external_cli(self):
        candidates = [
            {"key": "c-opus", "runtime": "claude", "model": "opus", "vendor": "anthropic",
             "purpose": "both", "task_affinity": None, "context_limit": None},
            {"key": "cx", "runtime": "codex", "model": "gpt-5.6-sol", "vendor": "openai",
             "task_affinity": None, "context_limit": None},
        ]
        rc, stdout, stderr, _refreshed, calls = self._run(candidates, {"CLAUDECODE": "1"})
        self.assertEqual(rc, 0, stderr)
        result = json.loads(stdout)
        self.assertEqual(result["mode"], "native")
        self.assertEqual(result["key"], "c-opus")
        self.assertEqual(result["runtime"], "claude")
        self.assertEqual(result["model"], "opus")
        self.assertEqual(calls[0].mode, "exec")
        self.assertEqual(calls[0].host, "claude")

        rc, stdout, stderr, _refreshed, _calls = self._run(candidates, {"OPENCODE": "1"})
        self.assertEqual(rc, 0, stderr)
        result = json.loads(stdout)
        self.assertEqual(result["mode"], "external_cli")
        self.assertEqual(result["key"], "cx")
        self.assertEqual(result["runtime"], "codex")
        self.assertIn("skipping c-opus for execution: route review_only", stderr)

    def test_bad_model_after_refresh_is_permanent(self):
        candidates = [
            {"key": "cx", "runtime": "codex", "model": "missing", "vendor": "openai",
             "task_affinity": None, "context_limit": None},
        ]
        rc, stdout, stderr, _refreshed, _calls = self._run(
            candidates, {"OPENCODE": "1"},
            quota={"cx": {"available": False, "reason": "quota"}})
        self.assertEqual(rc, 0, stderr)
        result = json.loads(stdout)
        self.assertEqual(result["reasons"], {"cx": "bad_model"})
        self.assertFalse(result["any_quota_recoverable"])
        self.assertIn("skipping cx for execution: route bad_model", stderr)

    def test_unverified_model_list_dispatches_and_names_the_key(self):
        candidates = [
            {"key": "cx", "runtime": "codex", "model": "unchecked", "vendor": "openai",
             "task_affinity": None, "context_limit": None},
        ]
        rc, stdout, stderr, _refreshed, _calls = self._run(candidates, {"OPENCODE": "1"})
        self.assertEqual(rc, 0, stderr)
        result = json.loads(stdout)
        self.assertEqual(result["mode"], "external_cli")
        self.assertEqual(result["key"], "cx")
        self.assertIn("dispatching cx unverified", stderr)
        self.assertIn("codex", stderr)

    def test_native_quota_exemption_never_probes_or_blocks_a_native_route(self):
        candidates = [
            {"key": "c-opus", "runtime": "claude", "model": "opus", "vendor": "anthropic",
             "purpose": "both", "task_affinity": None, "context_limit": None},
            {"key": "cx", "runtime": "codex", "model": "gpt-5.6-sol", "vendor": "openai",
             "task_affinity": None, "context_limit": None},
        ]
        stale = {"c-opus": {"available": False, "reason": "auth"}}
        rc, stdout, _stderr, refreshed, _calls = self._run(
            candidates, {"CLAUDECODE": "1"}, quota=stale)
        self.assertEqual(rc, 0)
        result = json.loads(stdout)
        self.assertEqual(result["mode"], "native")
        self.assertEqual(result["key"], "c-opus")
        self.assertEqual(refreshed, [["cx"]])

    def test_screen_order_records_review_only_unless_purpose_is_execute(self):
        full = {"key": "c-full", "runtime": "claude", "model": "claude-opus-5-5",
                "vendor": "anthropic", "task_affinity": None, "context_limit": None}
        rc, stdout, stderr, _refreshed, _calls = self._run([full], {"CLAUDECODE": "1"})
        self.assertEqual(rc, 0, stderr)
        result = json.loads(stdout)
        self.assertEqual(result["reasons"], {"c-full": "review_only"})
        self.assertNotIn("cannot be an execution CLI", stderr)
        self.assertIn("skipping c-full for execution: route review_only", stderr)

        explicit = dict(full, purpose="execute")
        rc, stdout, stderr, _refreshed, _calls = self._run([explicit], {"CLAUDECODE": "1"})
        self.assertEqual(rc, 2)
        self.assertEqual(stdout, "")
        self.assertIn("cannot be an execution CLI", stderr)


class TestCliDispatchTask(unittest.TestCase):
    def test_dispatch_task_refuses_a_native_injection_with_a_clear_error(self):
        # HIGH finding: dispatch-task is the only real entry point that ever reaches
        # dispatch_superpowers_task -- a native injection must fail here with a clear,
        # actionable error BEFORE any tooling-detection code runs (which indexes
        # injection["runtime"], and would otherwise die with a bare, unexplained KeyError
        # instead of a diagnosable message).
        injection = {"mode": "native", "runtime": None, "model": "opus", "key": "claude/opus-5"}
        with tempfile.TemporaryDirectory() as tmp:
            prompt_file = os.path.join(tmp, "prompt.txt")
            with open(prompt_file, "w") as f:
                f.write("do the task")
            format_block_file = os.path.join(tmp, "format.md")
            with open(format_block_file, "w") as f:
                f.write("status: DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED")
            report_file = os.path.join(tmp, "task-1-report.md")
            with self.assertRaises(ValueError) as ctx:
                superpowers_cli.main(
                    [
                        "dispatch-task",
                        "--injection-json",
                        json.dumps(injection),
                        "--prompt-file",
                        prompt_file,
                        "--target-dir",
                        tmp,
                        "--heartbeat-interval",
                        "60",
                        "--timeout",
                        "900",
                        "--format-block-file",
                        format_block_file,
                        "--report-file",
                        report_file,
                    ],
                    detect_tool_availability_fn=lambda: {},
                    resolve_agents_tooling_path_fn=lambda: None,
                    probe_codegraph_fn=lambda cli: detection.CodegraphProbe(
                        False, False, None, "skip"
                    ),
                    stdout=io.StringIO(),
                )
        self.assertIn("external_cli", str(ctx.exception))
        self.assertIn("mode='native'", str(ctx.exception))
        self.assertIn("Agent tool", str(ctx.exception))

    def test_preserves_implementer_authored_report_when_the_cli_writes_it_directly(self):
        # CRITICAL finding (recurrence -- a prior revision's fix attempt did not close every
        # path): the real superpowers implementer contract has the dispatched CLI write its OWN
        # detailed report directly to --report-file (it has write access to target_dir, being an
        # execute-mode dispatch) and return only a SHORT status separately (design spec's own
        # "writes detailed evidence to the report file and returns a short status separately").
        # dispatch-task must never overwrite that real, on-disk report with captured subprocess
        # stdout -- this is the normal case, and it must be left completely untouched.
        injection = {
            "mode": "external_cli",
            "key": "codex/terra",
            "runtime": "codex",
            "model": "gpt-5.6-terra",
            "effort": None,
            "service_tier": None,
        }

        def fake_dispatch(request, guidance=None, seams=None):
            # Simulates the real dispatched CLI: per the prompt's report-file-path instruction, it
            # writes its OWN detailed report directly to disk and returns only a short status in
            # stdout -- exactly the contract this test guards.
            report_path = os.path.join(request.target_dir, "task-1-report.md")
            with open(report_path, "w") as f:
                f.write("## TDD Evidence\n\nfull detailed report with real test output...\n")
            return {
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "command": "codex exec ...",
                "returncode": 0,
                "stdout": "DONE",
                "stderr": "",
                "timed_out": False,
            }

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            prompt_file = os.path.join(tmp, "prompt.txt")
            with open(prompt_file, "w") as f:
                f.write("do the task")
            format_block_file = os.path.join(tmp, "format.md")
            with open(format_block_file, "w") as f:
                f.write("status: DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED")
            report_file = os.path.join(tmp, "task-1-report.md")
            rc = superpowers_cli.main(
                [
                    "dispatch-task",
                    "--injection-json",
                    json.dumps(injection),
                    "--prompt-file",
                    prompt_file,
                    "--target-dir",
                    tmp,
                    "--heartbeat-interval",
                    "60",
                    "--timeout",
                    "900",
                    "--format-block-file",
                    format_block_file,
                    "--report-file",
                    report_file,
                ],
                dispatch_superpowers_task_fn=fake_dispatch,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                probe_codegraph_fn=lambda cli: detection.CodegraphProbe(False, False, None, "skip"),
                stdout=out,
            )
            self.assertEqual(rc, 0)
            with open(report_file) as f:
                content = f.read()
        # The implementer's own detailed, on-disk report survives verbatim -- the short "DONE"
        # status returned separately in stdout must NEVER have replaced it.
        self.assertEqual(
            content, "## TDD Evidence\n\nfull detailed report with real test output...\n"
        )
        self.assertNotIn("DONE", content)
        result = json.loads(out.getvalue())
        self.assertEqual(result["returncode"], 0)

    def test_a_pre_18_1_injection_with_a_cli_key_still_dispatches(self):
        # B-IN-05: an injection written before the cli -> runtime rename is read, not a KeyError.
        injection = {"mode": "external_cli", "key": "c", "cli": "cursor-agent",
                     "model": "gpt-5", "effort": None, "service_tier": None}
        seen = []

        def fake_dispatch(request, guidance=None, seams=None):
            seen.append(request.injection["runtime"])
            return {"runtime": "cursor", "model": "gpt-5", "command": "x", "returncode": 0,
                    "stdout": "DONE", "stderr": "", "timed_out": False}

        with tempfile.TemporaryDirectory() as tmp:
            for name in ("prompt.txt", "format.md"):
                with open(os.path.join(tmp, name), "w") as f:
                    f.write("x")
            rc = superpowers_cli.main(
                ["dispatch-task", "--injection-json", json.dumps(injection),
                 "--prompt-file", os.path.join(tmp, "prompt.txt"), "--target-dir", tmp,
                 "--heartbeat-interval", "60", "--timeout", "900",
                 "--format-block-file", os.path.join(tmp, "format.md"),
                 "--report-file", os.path.join(tmp, "report.md")],
                dispatch_superpowers_task_fn=fake_dispatch,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                probe_codegraph_fn=lambda cli: detection.CodegraphProbe(False, False, None, "skip"),
                stdout=io.StringIO(),
            )
        self.assertEqual(rc, 0)
        self.assertEqual(seen, ["cursor"])

    def test_falls_back_to_labeled_stdout_only_when_the_cli_never_wrote_its_own_report(self):
        # Degraded case: the dispatched CLI did not follow the report-file-path instruction and
        # wrote nothing to disk -- something evidentiary must still survive, but clearly labeled
        # as a fallback, never silently indistinguishable from a genuine implementer report.
        injection = {
            "mode": "external_cli",
            "key": "codex/terra",
            "runtime": "codex",
            "model": "gpt-5.6-terra",
            "effort": None,
            "service_tier": None,
        }

        def fake_dispatch(request, guidance=None, seams=None):
            return {
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "command": "codex exec ...",
                "returncode": 0,
                "stdout": "DONE\nonly stdout, no report file written",
                "stderr": "",
                "timed_out": False,
            }

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            prompt_file = os.path.join(tmp, "prompt.txt")
            with open(prompt_file, "w") as f:
                f.write("do the task")
            format_block_file = os.path.join(tmp, "format.md")
            with open(format_block_file, "w") as f:
                f.write("status: DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED")
            report_file = os.path.join(tmp, "task-1-report.md")
            rc = superpowers_cli.main(
                [
                    "dispatch-task",
                    "--injection-json",
                    json.dumps(injection),
                    "--prompt-file",
                    prompt_file,
                    "--target-dir",
                    tmp,
                    "--heartbeat-interval",
                    "60",
                    "--timeout",
                    "900",
                    "--format-block-file",
                    format_block_file,
                    "--report-file",
                    report_file,
                ],
                dispatch_superpowers_task_fn=fake_dispatch,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                probe_codegraph_fn=lambda cli: detection.CodegraphProbe(False, False, None, "skip"),
                stdout=out,
            )
            self.assertEqual(rc, 0)
            with open(report_file) as f:
                content = f.read()
        self.assertIn("no report file was written", content)
        self.assertIn("only stdout, no report file written", content)

    def test_report_mode_append_preserves_the_prior_rounds_report_in_the_fallback_case(self):
        # CRITICAL finding: a fix-loop round must APPEND to the existing report file, never
        # overwrite it -- subagent-driven-development's own "every round... appends its fix
        # report to the same report file" contract is the harness's persistent memory for an
        # external_cli task (there's no live subagent to hold context between rounds). Exercises
        # the STDOUT-fallback branch specifically (the dispatched CLI here does not write its own
        # report directly) -- even the degraded fallback must never destroy earlier rounds.
        injection = {
            "mode": "external_cli",
            "key": "codex/terra",
            "runtime": "codex",
            "model": "gpt-5.6-terra",
            "effort": None,
            "service_tier": None,
        }

        def fake_dispatch(request, guidance=None, seams=None):
            return {
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "command": "codex exec ...",
                "returncode": 0,
                "stdout": "fix round 1 report",
                "stderr": "",
                "timed_out": False,
            }

        with tempfile.TemporaryDirectory() as tmp:
            prompt_file = os.path.join(tmp, "prompt.txt")
            with open(prompt_file, "w") as f:
                f.write("fix it")
            format_block_file = os.path.join(tmp, "format.md")
            with open(format_block_file, "w") as f:
                f.write("status: DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED")
            report_file = os.path.join(tmp, "task-1-report.md")
            with open(report_file, "w") as f:
                f.write("original implementer report")
            rc = superpowers_cli.main(
                [
                    "dispatch-task",
                    "--injection-json",
                    json.dumps(injection),
                    "--prompt-file",
                    prompt_file,
                    "--target-dir",
                    tmp,
                    "--heartbeat-interval",
                    "60",
                    "--timeout",
                    "900",
                    "--format-block-file",
                    format_block_file,
                    "--report-file",
                    report_file,
                    "--report-mode",
                    "append",
                ],
                dispatch_superpowers_task_fn=fake_dispatch,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                probe_codegraph_fn=lambda cli: detection.CodegraphProbe(False, False, None, "skip"),
                stdout=io.StringIO(),
            )
            self.assertEqual(rc, 0)
            with open(report_file) as f:
                content = f.read()
        self.assertIn("original implementer report", content)
        self.assertIn("fix round 1 report", content)

    def test_dispatch_task_prints_install_hint_on_stderr_when_probe_unhealthy(self):
        hint = detection.codegraph_install_command("codex")
        index_dirs = []
        injection = {
            "mode": "external_cli",
            "key": "codex/terra",
            "runtime": "codex",
            "model": "gpt-5.6-terra",
            "effort": None,
            "service_tier": None,
        }
        captured = {}

        def fake_dispatch(request, guidance=None, seams=None):
            captured["codegraph_registered"] = (
                guidance.codegraph_registered if guidance is not None else False
            )
            return {
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "command": "codex exec ...",
                "returncode": 0,
                "stdout": "DONE",
                "stderr": "",
                "timed_out": False,
            }

        out = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            prompt_file = os.path.join(tmp, "prompt.txt")
            with open(prompt_file, "w") as f:
                f.write("do the task")
            format_block_file = os.path.join(tmp, "format.md")
            with open(format_block_file, "w") as f:
                f.write("status: DONE")
            report_file = os.path.join(tmp, "task-1-report.md")
            with contextlib.redirect_stderr(stderr):
                rc = superpowers_cli.main(
                    [
                        "dispatch-task",
                        "--injection-json",
                        json.dumps(injection),
                        "--prompt-file",
                        prompt_file,
                        "--target-dir",
                        tmp,
                        "--heartbeat-interval",
                        "60",
                        "--timeout",
                        "900",
                        "--format-block-file",
                        format_block_file,
                        "--report-file",
                        report_file,
                    ],
                    dispatch_superpowers_task_fn=fake_dispatch,
                    detect_tool_availability_fn=lambda: {},
                    resolve_agents_tooling_path_fn=lambda: None,
                    probe_codegraph_fn=lambda cli: detection.CodegraphProbe(
                        True, False, hint, "unhealthy"
                    ),
                    run_codegraph_index_fn=lambda d: index_dirs.append(d) or True,
                    stdout=out,
                )
            self.assertEqual(rc, 0)
            self.assertIn(hint, stderr.getvalue())
            self.assertNotIn(hint, out.getvalue())
            self.assertEqual(index_dirs, [])
            self.assertFalse(captured["codegraph_registered"])

    def test_dispatch_task_runs_index_after_healthy_probe(self):
        index_dirs = []
        injection = {
            "mode": "external_cli",
            "key": "codex/terra",
            "runtime": "codex",
            "model": "gpt-5.6-terra",
            "effort": None,
            "service_tier": None,
        }
        captured = {}

        def fake_dispatch(request, guidance=None, seams=None):
            captured["codegraph_registered"] = (
                guidance.codegraph_registered if guidance is not None else False
            )
            return {
                "runtime": "codex",
                "model": "gpt-5.6-terra",
                "command": "codex exec ...",
                "returncode": 0,
                "stdout": "DONE",
                "stderr": "",
                "timed_out": False,
            }

        with tempfile.TemporaryDirectory() as tmp:
            prompt_file = os.path.join(tmp, "prompt.txt")
            with open(prompt_file, "w") as f:
                f.write("do the task")
            format_block_file = os.path.join(tmp, "format.md")
            with open(format_block_file, "w") as f:
                f.write("status: DONE")
            report_file = os.path.join(tmp, "task-1-report.md")
            superpowers_cli.main(
                [
                    "dispatch-task",
                    "--injection-json",
                    json.dumps(injection),
                    "--prompt-file",
                    prompt_file,
                    "--target-dir",
                    tmp,
                    "--heartbeat-interval",
                    "60",
                    "--timeout",
                    "900",
                    "--format-block-file",
                    format_block_file,
                    "--report-file",
                    report_file,
                ],
                dispatch_superpowers_task_fn=fake_dispatch,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                probe_codegraph_fn=lambda cli: detection.CodegraphProbe(True, True, None, "ok"),
                run_codegraph_index_fn=lambda d: index_dirs.append(d) or True,
                stdout=io.StringIO(),
            )
            self.assertEqual(index_dirs, [tmp])
            self.assertTrue(captured["codegraph_registered"])


class TestCodegraphUnknownHealth(unittest.TestCase):
    def test_registered_with_unknown_health_is_indexed(self):
        index_dirs = []
        deps = superpowers_cli.CliDeps()._replace(
            probe_codegraph_fn=lambda cli: detection.CodegraphProbe(
                True, None, None, "health not observable"),
            run_codegraph_index_fn=lambda d: index_dirs.append(d) or True,
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertTrue(superpowers_cli._codegraph_registered_for_cli("codex", "/repo", deps))
        self.assertEqual(index_dirs, ["/repo"])
        self.assertIn("is unknown", err.getvalue())

    def test_known_unhealthy_is_not_indexed(self):
        index_dirs = []
        deps = superpowers_cli.CliDeps()._replace(
            probe_codegraph_fn=lambda cli: detection.CodegraphProbe(True, False, None, "down"),
            run_codegraph_index_fn=lambda d: index_dirs.append(d) or True,
        )
        self.assertFalse(superpowers_cli._codegraph_registered_for_cli("codex", "/repo", deps))
        self.assertEqual(index_dirs, [])


class TestCliClassifyDispatchFailure(unittest.TestCase):
    def test_prints_the_classification_string(self):
        out = io.StringIO()
        result = {"returncode": 75, "reason": "quota"}
        rc = superpowers_cli.main(
            ["classify-dispatch-failure", "--dispatch-result-json", json.dumps(result)], stdout=out
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "quota")


class TestImplementerStatus(unittest.TestCase):
    """The status comes from a line that declares it, never from a word inside prose."""

    def test_a_declared_status_wins_over_status_words_in_prose(self):
        cases = {
            "BLOCKED: checks failed; task is not DONE": "BLOCKED",
            "Ran the suite; every test passes, nothing BLOCKED.\nSTATUS: DONE": "DONE",
            "**Status:** DONE_WITH_CONCERNS": "DONE_WITH_CONCERNS",
            "- NEEDS_CONTEXT - which schema?": "NEEDS_CONTEXT",
            "DONE.": "DONE",
            "status: DONE\nDONE": "DONE",
        }
        for stdout, want in cases.items():
            with self.subTest(stdout=stdout):
                self.assertEqual(dispatch_injection.implementer_status(stdout), want)

    def test_missing_conflicting_or_echoed_declarations_read_as_blocked(self):
        for stdout in ("", "all good, task is DONE", "STATUS: DONE\nSTATUS: BLOCKED",
                       "Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED",
                       "DONE is not reachable without the schema"):
            with self.subTest(stdout=stdout):
                self.assertEqual(dispatch_injection.implementer_status(stdout), "BLOCKED")

    def test_cli_reads_only_the_stdout_field(self):
        out = io.StringIO()
        result = {"returncode": 0, "stdout": "work summary\nSTATUS: DONE", "reason": "BLOCKED"}
        rc = superpowers_cli.main(
            ["implementer-status", "--dispatch-result-json", json.dumps(result)], stdout=out
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "DONE")
        out = io.StringIO()
        superpowers_cli.main(
            ["implementer-status", "--dispatch-result-json", json.dumps({"returncode": 0})],
            stdout=out,
        )
        self.assertEqual(out.getvalue(), "BLOCKED")


class TestCliResumeExclusions(unittest.TestCase):
    def test_prints_only_permanent_exclusions(self):
        # CRITICAL finding: the executable subcommand SKILL.md's resume path calls -- proves
        # the reason-based split (quota dropped, everything else kept) is real and testable, not
        # just inline, untested bash arithmetic.
        out = io.StringIO()
        rc = superpowers_cli.main(
            [
                "resume-exclusions",
                "--tried-json",
                json.dumps(["claude/opus-5", "codex/terra"]),
                "--reasons-json",
                json.dumps({"claude/opus-5": "quota", "codex/terra": "auth"}),
                "--prior-excluded-keys-json",
                json.dumps([]),
            ],
            stdout=out,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.getvalue()), ["codex/terra"])


class TestCliWriteResumableState(unittest.TestCase):
    def test_writes_state_and_confirms(self):
        out = io.StringIO()
        captured = {}
        rc = superpowers_cli.main(
            [
                "write-resumable-state",
                "--path",
                "/x/state.json",
                "--state-json",
                json.dumps({"framework": "superpowers", "tried": []}),
            ],
            write_resumable_state_fn=lambda path, state: captured.update(path=path, state=state),
            stdout=out,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(captured["path"], "/x/state.json")
        self.assertEqual(json.loads(out.getvalue())["written"], True)


class TestDetectFrameworkSuperpowers(unittest.TestCase):
    def test_detects_superpowers_from_plans_directory(self):
        def isdir_fn(path):
            return path == os.path.join("/repo", "docs", "superpowers", "plans")

        result = router_detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=isdir_fn
        )
        self.assertEqual(result, "superpowers")

    def test_gsd_marker_wins_over_superpowers_marker_when_both_present_and_no_stronger_signal(self):
        result = router_detect_framework.detect_framework(
            "/repo",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: p == os.path.join("/repo", "docs", "superpowers", "plans"),
        )
        self.assertEqual(result, "gsd")

    def test_returns_unknown_when_neither_marker_present(self):
        result = router_detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=lambda p: False
        )
        self.assertEqual(result, "unknown")

    def test_document_path_overrides_gsd_marker_when_both_markers_present(self):
        # CRITICAL finding (recurrence guard): a repo with BOTH markers present must still route a
        # user-supplied superpowers plan path to superpowers -- markers are supporting evidence
        # only, never the primary signal once an explicit document path is available.
        result = router_detect_framework.detect_framework(
            "/repo",
            document_path="/repo/docs/superpowers/plans/2026-08-29-widget.md",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: p == os.path.join("/repo", "docs", "superpowers", "plans"),
        )
        self.assertEqual(result, "superpowers")

    def test_document_path_under_planning_resolves_gsd_even_without_markers(self):
        result = router_detect_framework.detect_framework(
            "/repo",
            document_path="/repo/.planning/phases/02-widget/02-01-PLAN.md",
            isfile_fn=lambda p: False,
            isdir_fn=lambda p: False,
        )
        self.assertEqual(result, "gsd")

    def test_conversation_signal_wins_over_a_contradicting_document_path_and_markers(self):
        # CRITICAL finding: conversation signal is the strongest evidence -- the user just invoked
        # writing-plans in this very conversation, which outranks even an explicit document path
        # that happens to look GSD-shaped (e.g. copied under a .planning/ scratch directory).
        result = router_detect_framework.detect_framework(
            "/repo",
            document_path="/repo/.planning/scratch/notes.md",
            conversation_signal="superpowers",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: False,
        )
        self.assertEqual(result, "superpowers")


class TestUntrustedLocalExecuteEntry(unittest.TestCase):
    """Plan 16.1-08 (R5): the DEFAULT cfg_resolve binding must be trust-gated, so a later
    seam refactor cannot silently bind a non-gated loader into execute dispatch."""

    def test_untrusted_local_execute_entry_absent_until_trusted(self):
        import tempfile

        from ai_kit_spec import config_io, trust

        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as xdg:
            env = {"HOME": home, "XDG_CONFIG_HOME": xdg}
            cwd = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, cwd, True)
            local_dir = os.path.join(cwd, ".aikit")
            os.makedirs(local_dir)
            local_path = os.path.join(local_dir, "review-spec.toml")
            raw = (
                b'strategy = "local-only"\n[[reviewers]]\nkey = "x1"\nmodel = "m"\n'
                b'vendor = "v"\ncli = "codex"\ncommand = "codex exec -m {model}"\n'
                b'purpose = "execute"\n'
            )
            with open(local_path, "wb") as f:
                f.write(raw)
            with contextlib.redirect_stderr(io.StringIO()):
                candidates, _ = dispatch_injection.assemble_candidates(cwd, env)
            self.assertNotIn("x1", [c["key"] for c in candidates])
            trust.record_trust(
                config_io.cfg_trust_store_dir(env), os.path.realpath(local_path), raw
            )
            with contextlib.redirect_stderr(io.StringIO()):
                candidates, _ = dispatch_injection.assemble_candidates(cwd, env)
            self.assertIn("x1", [c["key"] for c in candidates])


# ── 26-10: the session wake step (D-23, D-35, D-36) ─────────────────────────
# The blocks run under session_wake_fakes.doc_block_env; the stub shim stands in for
# ai-kit-session-wake and logs every call. Each test writes its own plan with N `### Task` headings.

_SUPER_SKILL = pathlib.Path(__file__).resolve().parent.parent / "skills" / (
    "ai-kit-spec-execute-superpowers") / "SKILL.md"
_SUPER_COMMANDS = ["dirname", "mkdir", "grep", "wc", "printf", "cat", "sed", "tr", "echo", "head",
                   "rm", "tee"]


def _super_text() -> str:
    return _SUPER_SKILL.read_text(encoding="utf-8")


def _super_dispatch_ref() -> str:
    return (_SUPER_SKILL.parent / "references" / "dispatch-external-cli.md").read_text(
        encoding="utf-8")


def _super_wake_ref() -> str:
    return (_SUPER_SKILL.parent / "references" / "session-wake.md").read_text(encoding="utf-8")


def _super_block(needle: str) -> str:
    """The first fenced bash block of SKILL.md or its dispatch/wake references with `needle`."""
    for block in re.findall(r"```bash\n(.*?)```",
                            _super_text() + "\n" + _super_dispatch_ref() + "\n" + _super_wake_ref(),
                            re.DOTALL):
        if needle in block:
            return block
    raise AssertionError(f"no SKILL.md or dispatch-external-cli.md bash block has {needle!r}")


class TestSessionWakeStep(unittest.TestCase):
    """The superpowers arm, re-arm and close steps, run against a stub shim in a scratch root."""

    def setUp(self):
        bash_bin = shutil.which("bash")
        if bash_bin is None:
            self.skipTest("bash not found")
        self.bash_bin: str = bash_bin
        self.root = tempfile.mkdtemp(prefix="super-wake-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.skills = os.path.join(self.root, "skills")
        self.super_skill = os.path.join(self.skills, "ai-kit-spec-execute-superpowers")
        self.shim = os.path.join(self.skills, "ai-kit-session-wake", "ai-kit-session-wake.py")
        session_wake_fakes.stub_shim(self.shim)
        self.cwd = os.path.join(self.root, "project")
        os.makedirs(os.path.join(self.cwd, "docs"))
        self.plan = os.path.join(self.cwd, "docs", "plan.md")
        self.log = os.path.join(self.root, "fake.log")
        self.scalars = os.path.join(self.root, "scalars.env")
        self.env = session_wake_fakes.doc_block_env(self.root, _SUPER_COMMANDS)

    def _plan(self, tasks: int):
        body = "# Plan\n\n" + "".join(
            f"### Task {n}: thing\n\nbody\n\n" for n in range(1, tasks + 1)
        )
        with open(self.plan, "w", encoding="utf-8") as handle:
            handle.write(body)

    def _run(self, block: str, extra: dict | None = None):
        env = {
            **self.env,
            "AI_KIT_FAKE_LOG": self.log,
            "SKILL_DIR": self.super_skill,
            "SCALARS": self.scalars,
            "CWD": self.cwd,
            "PLAN_FILE": self.plan,
            **(extra or {}),
        }
        return subprocess.run(
            [self.bash_bin, "-c", block], cwd=self.cwd, env=env,
            capture_output=True, text=True, timeout=60, check=False,
        )

    def _shim_calls(self):
        if not os.path.exists(self.log):
            return []
        return [e["argv"] for e in session_wake_fakes.read_log(self.log) if e["name"] == "shim"]

    @staticmethod
    def _value(out: str, key: str) -> str:
        for line in out.splitlines():
            if line.startswith(key + "="):
                return line[len(key) + 1:]
        raise AssertionError(f"{key}= not printed in: {out!r}")

    def _arm_block(self) -> str:
        block = _super_block("single-task plan: no session wake")
        # The id line is a literal the agent fills; the tests pass it through the env.
        return re.sub(r'^WAKE_SESSION_ID="<[^"\n]*>"$', 'WAKE_SESSION_ID="${WAKE_SESSION_ID:-}"',
                      block, count=1, flags=re.MULTILINE)

    def test_arm_block_sets_the_session_id_on_its_own_first_line(self):
        """A variable set in an earlier Bash call is gone, so the id literal opens the block."""
        first = _super_block("single-task plan: no session wake").splitlines()[0]
        self.assertTrue(first.startswith("WAKE_SESSION_ID="), first)

    def _fill_task_paths(self, block: str, skill_dir: str, shim: str, tools: str, task_n: str):
        """Substitute the six literals the agent fills in the task-paths block's first lines."""
        values = {"SKILL_DIR": skill_dir, "SHIM": shim, "TOOLS_PY": tools, "CWD": self.cwd,
                  "PLAN_FILE": self.plan, "TASK_N": task_n}
        for name, value in values.items():
            block = re.sub(rf'{name}="<[^"\n]*>"', lambda _m, n=name, v=value: f'{n}={v!r}', block,
                           count=1)
        return block

    def test_task_paths_guard_rejects_empty_and_placeholder_values(self):
        """An unbound CWD/PLAN_FILE/TASK_N would collide task state, so the block stops first."""
        block = _super_block("RESUME_FOUND=")
        tools = os.path.join(self.root, "tools.py")
        with open(tools, "w", encoding="utf-8") as handle:
            handle.write("print('q')\n")
        for name in ("CWD", "PLAN_FILE", "TASK_N", "TOOLS_PY"):
            for bad in ("", "<Step 1 value>"):
                with self.subTest(name=name, bad=bad):
                    filled = self._fill_task_paths(block, self.super_skill, "shim", tools, "3")
                    filled = re.sub(rf"\b{name}='[^']*'", lambda _m, n=name, v=bad: f"{n}={v!r}",
                                    filled, count=1)
                    result = self._run(filled, {"SCALARS": "unset"})
                    self.assertNotEqual(0, result.returncode, result.stdout)
                    self.assertIn(f"ERROR: {name} is empty", result.stdout)
                    self.assertFalse(os.path.exists("unset"))

    def test_resume_check_finds_the_task_state_file(self):
        """Step 2's resume check computes the state path exactly as the state-write blocks do."""
        tools = os.path.join(self.root, "tools.py")
        cache = os.path.join(self.root, "cache")
        os.makedirs(cache)
        with open(tools, "w", encoding="utf-8") as handle:
            handle.write(f"print({os.path.join(cache, 'quota.json')!r})\n")
        block = _super_block("RESUME_FOUND=")
        block = self._fill_task_paths(block, self.super_skill, "shim", tools, "3")
        extra = {"SCALARS": "unset"}
        first = self._run(block, extra)
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual("0", self._value(first.stdout, "RESUME_FOUND"))
        key = hashlib.sha256(f"{self.cwd}\n{self.plan}".encode()).hexdigest()[:12]
        path = os.path.join(cache, f"superpowers-resume-{key}-task-3.json")
        self.assertEqual(path, self._value(first.stdout, "RESUME_STATE_PATH"))
        self.assertEqual(os.path.join(cache, "quota.json"), self._value(first.stdout, "QUOTA_PATH"))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{}")
        second = self._run(block, extra)
        self.assertEqual("1", self._value(second.stdout, "RESUME_FOUND"))

    def _state_write_blocks(self) -> list[str]:
        ref = (_SUPER_SKILL.parent / "references" / "state-management.md").read_text(
            encoding="utf-8")
        blocks = [b for b in re.findall(r"```bash\n(.*?)```", ref, re.DOTALL)
                  if "write-resumable-state" in b]
        self.assertEqual(2, len(blocks))
        return blocks

    def test_state_write_blocks_use_the_loaded_resume_path_and_never_recompute_it(self):
        """A fresh shell has no QUOTA_PATH: recomputing wrote ./superpowers-resume-...; an empty
        loaded path must stop the block before any write."""
        for block in self._state_write_blocks():
            self.assertNotRegex(block, r"(?m)^\s*(PROJECT_KEY|RESUME_STATE_PATH)=")
            self.assertNotIn("dirname", block)
            proc = self._run(block, {"RESUME_STATE_PATH": "", "SHIM": "false", "RUN_DIR": self.root,
                                     "FIX_ROUND": "0"})
            self.assertNotEqual(0, proc.returncode, proc.stdout)
            self.assertIn("RESUME_STATE_PATH is empty", proc.stdout)
            self.assertEqual([], [n for n in os.listdir(self.cwd) if n.startswith("superpowers-")])

    def test_second_task_shell_loads_the_second_tasks_resume_path(self):
        """The scalar file is per plan (last line wins): task 2's task-paths block must make a
        later shell load task 2's RESUME_STATE_PATH, not task 1's."""
        tools = os.path.join(self.root, "tools.py")
        cache = os.path.join(self.root, "cache")
        os.makedirs(cache)
        with open(tools, "w", encoding="utf-8") as handle:
            handle.write(f"print({os.path.join(cache, 'quota.json')!r})\n")
        block = _super_block("RESUME_FOUND=")
        for task_n in ("1", "2"):
            filled = self._fill_task_paths(block, self.super_skill, "shim", tools, task_n)
            proc = self._run(filled)
            self.assertEqual(0, proc.returncode, proc.stderr)
        loader = _super_block("while IFS== read").replace(
            "<the path the task-paths block printed>", self._value(proc.stdout, "SCALARS"))
        later = self._run(loader + '\nprintf "%s\\n" "$RESUME_STATE_PATH" "$RUN_DIR"')
        key = hashlib.sha256(f"{self.cwd}\n{self.plan}".encode()).hexdigest()[:12]
        self.assertEqual(
            [os.path.join(cache, f"superpowers-resume-{key}-task-2.json"),
             os.path.join(cache, f"superpowers-run-{key}-task-2")],
            later.stdout.splitlines())

    def test_wake_id_wording_names_no_verified_pi_or_opencode_session_variable(self):
        flat = " ".join(_super_wake_ref().split())
        self.assertNotIn("this session's exact id", flat)
        self.assertIn("pi and opencode have no verified session variable", flat)
        self.assertIn("never a guess or the newest session file", flat)
        self.assertIn("Otherwise leave it empty", flat)

    def test_clear_resume_state_removes_only_the_task_state_file(self):
        """A succeeded dispatch deletes the task's own state file, never a sibling."""
        mine = os.path.join(self.root, "superpowers-resume-k-task-3.json")
        other = os.path.join(self.root, "superpowers-resume-k-task-4.json")
        for path in (mine, other):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{}")
        block = _super_block('rm -f -- "$RESUME_STATE_PATH"')
        for _ in range(2):  # the second run proves a missing file is not an error
            proc = self._run(block, {"RESUME_STATE_PATH": mine})
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertFalse(os.path.exists(mine))
            self.assertTrue(os.path.exists(other))
        self.assertEqual(0, self._run(block, {"RESUME_STATE_PATH": ""}).returncode)

    def test_fix_round_start_precedes_both_dispatch_modes(self):
        """The round increment and anchor are shared, so native dispatch also moves the floor."""
        text = _super_text()
        start = text.index("**At the start of every fix round, in either mode")
        self.assertLess(start, text.index('**`mode == "native"`:**'))
        self.assertLess(start, text.index('**`mode == "external_cli"`:**'))
        self.assertIn('ESCALATION_ANCHOR_KEY="$LAST_DISPATCHED_KEY"', text[start:start + 300])
        self.assertNotIn("never dispatches a task itself", text)

    def test_fix_round_start_is_new_round_only_and_reads_escalation_before_dispatch(self):
        text = " ".join(_super_text().split())
        self.assertIn("new rounds only, never on a resume, a re-invoke that kept its "
                      "scalars or a Step-2 re-entry", text)
        self.assertLess(
            text.index("**MANDATORY: read `references/escalation.md` in full before composing"),
            text.index("**Clear the resume state when a dispatch succeeds**"))

    def test_single_task_plan_arms_nothing(self):
        self._plan(1)
        proc = self._run(self._arm_block())
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("single-task plan: no session wake", proc.stdout)
        self.assertEqual("0", self._value(proc.stdout, "WAKE_OWNED"))
        self.assertEqual([], self._shim_calls())

    def test_two_tasks_on_claude_arm_once_and_record_the_identity(self):
        self._plan(2)
        proc = self._run(self._arm_block(), {"STUB_HOST": "claude", "STUB_SID": "sid-s1"})
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual(self.shim, self._value(proc.stdout, "WAKE_SHIM"))
        self.assertEqual("1", self._value(proc.stdout, "WAKE_OWNED"))
        self.assertEqual("claude", self._value(proc.stdout, "WAKE_HOST"))
        self.assertEqual("sid-s1", self._value(proc.stdout, "WAKE_ID"))
        self.assertEqual([["arm", "--ref", self.plan]], self._shim_calls())

    def test_pi_without_an_id_relays_the_refusal_and_goes_on(self):
        self._plan(2)
        proc = self._run(self._arm_block(), {"STUB_HOST": "pi"})
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("no session id: pass --session-id", proc.stdout)
        self.assertIn("session wake arm exit 2", proc.stdout)
        self.assertEqual("0", self._value(proc.stdout, "WAKE_OWNED"))

    def test_unfilled_session_id_placeholder_is_a_hard_failure(self):
        self._plan(2)
        block = _super_block("single-task plan: no session wake")
        proc = self._run(block, {"STUB_HOST": "pi"})
        self.assertNotEqual(0, proc.returncode, proc.stdout)
        self.assertIn("WAKE_SESSION_ID is a placeholder", proc.stdout)
        self.assertEqual([], self._shim_calls())

    def test_pi_with_the_recorded_id_passes_session_id(self):
        self._plan(2)
        proc = self._run(self._arm_block(), {"STUB_HOST": "pi", "WAKE_SESSION_ID": "pi-s-id"})
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual("1", self._value(proc.stdout, "WAKE_OWNED"))
        self.assertEqual("pi-s-id", self._value(proc.stdout, "WAKE_ID"))
        self.assertIn(["arm", "--session-id", "pi-s-id", "--ref", self.plan],
                      self._shim_calls())

    def test_refreshed_and_exit_three_are_not_owned(self):
        self._plan(2)
        refreshed = self._run(self._arm_block(),
                              {"STUB_HOST": "claude", "STUB_ARM_OUTPUT": "refreshed claude-old"})
        self.assertEqual("0", self._value(refreshed.stdout, "WAKE_OWNED"))
        exit3 = self._run(self._arm_block(),
                          {"STUB_HOST": "claude", "STUB_ARM_RC": "3",
                           "STUB_ARM_OUTPUT": "armed claude-x"})
        self.assertEqual(0, exit3.returncode, exit3.stderr)
        self.assertEqual("0", self._value(exit3.stdout, "WAKE_OWNED"))

    def test_missing_sibling_shim_prints_not_installed(self):
        self._plan(2)
        os.remove(self.shim)
        proc = self._run(self._arm_block())
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("ai-kit-session-wake not installed", proc.stdout)

    def test_owned_rearm_and_close_use_the_recorded_identity(self):
        self._plan(2)
        owned = {"WAKE_SHIM": self.shim, "WAKE_OWNED": "1", "WAKE_HOST": "claude",
                 "WAKE_ID": "sid-s1", "RESUME_STATE_PATH": os.path.join(self.root, "r.json"),
                 "SCALARS": self.scalars}
        rearm = _super_block('--ref "$RESUME_STATE_PATH"')
        close = _super_block('done --host "$WAKE_HOST"')
        for block in (rearm, close):
            env = {**self.env, "AI_KIT_FAKE_LOG": self.log, **owned}
            proc = subprocess.run([self.bash_bin, "-c", block], cwd=self.cwd, env=env,
                                  capture_output=True, text=True, timeout=60, check=False)
            self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual(
            [["arm", "--host", "claude", "--session-id", "sid-s1",
              "--ref", os.path.join(self.root, "r.json")],
             ["done", "--host", "claude", "--session-id", "sid-s1"]],
            self._shim_calls(),
        )
        with open(self.scalars, encoding="utf-8") as handle:  # a later run arms its own wake
            self.assertEqual("WAKE_OWNED=0", handle.read().splitlines()[-1])

    def _loader(self) -> str:
        return _super_block("while IFS== read").replace(
            "<the path the task-paths block printed>", self.scalars)

    def test_arm_block_runs_once_per_plan_when_run_twice(self):
        """A re-invoked or wake-resumed run follows the skill from the top and runs the block
        again; the owned wake must stay owned and `arm` must not be called a second time."""
        self._plan(2)
        block = self._arm_block()
        first = self._run(block, {"STUB_HOST": "claude", "STUB_SID": "sid-s1"})
        self.assertEqual("1", self._value(first.stdout, "WAKE_OWNED"))
        second = self._run(self._loader() + "\n" + block,
                           {"STUB_HOST": "claude", "STUB_ARM_OUTPUT": "refreshed claude-sid-s1"})
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertIn("arm skipped", second.stdout)
        self.assertEqual([["arm", "--ref", self.plan]], self._shim_calls())
        with open(self.scalars, encoding="utf-8") as handle:
            owned = [ln for ln in handle.read().splitlines() if ln.startswith("WAKE_OWNED=")]
        self.assertEqual(["WAKE_OWNED=1"], owned)
        # an unowned plan (a refusal or `refreshed` earlier) still tries again
        with open(self.scalars, "w", encoding="utf-8") as handle:
            handle.write("WAKE_OWNED=0\n")
        third = self._run(self._loader() + "\n" + block,
                          {"STUB_HOST": "claude", "STUB_SID": "sid-s2"})
        self.assertEqual("1", self._value(third.stdout, "WAKE_OWNED"))
        self.assertEqual(2, len(self._shim_calls()))

    def test_single_task_run_through_a_stop_and_completion_touches_no_wake(self):
        self._plan(1)
        arm = self._run(self._arm_block())
        self.assertEqual("0", self._value(arm.stdout, "WAKE_OWNED"))
        rearm = _super_block('--ref "$RESUME_STATE_PATH"')
        close = _super_block('done --host "$WAKE_HOST"')
        env = {**self.env, "AI_KIT_FAKE_LOG": self.log, "WAKE_SHIM": self.shim,
               "WAKE_OWNED": "0", "WAKE_HOST": "", "WAKE_ID": "",
               "RESUME_STATE_PATH": os.path.join(self.root, "r.json")}
        for block in (rearm, close):
            proc = subprocess.run([self.bash_bin, "-c", block], cwd=self.cwd, env=env,
                                  capture_output=True, text=True, timeout=60, check=False)
            self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual([], self._shim_calls())

    def test_arm_sits_before_step_two_and_close_after_step_four(self):
        text = _super_text()
        wake = _super_wake_ref()
        arm = text.index("## Arm the session wake (plans with two or more tasks)\n")
        step2 = text.index("## Step 2: Before each task's implementer dispatch")
        step4 = text.index("## Step 4: Task review, fix loop, final review")
        close = text.index("## Close the session wake\n")
        self.assertLess(arm, step2)
        self.assertLess(step4, close)
        self.assertEqual(0, text.count("ai-kit-session-wake/ai-kit-session-wake.py"))
        self.assertEqual(1, wake.count("ai-kit-session-wake/ai-kit-session-wake.py"))
        self.assertIn("MANDATORY: read [`references/session-wake.md`]", text[arm:step2])
        # done runs when the job ends: the plan finished, or a stop ended the run
        close_text = text[close:] + wake
        self.assertIn("STOP this wave, or an owner stop", close_text)
        self.assertIn("the final whole-branch review finished", close_text)
        self.assertNotIn("D-23", text)

    def test_arm_is_once_per_plan_and_pinned_resume_reuses_the_prompt_file(self):
        flat = " ".join(_super_text().split())
        wake = " ".join(_super_wake_ref().split())
        self.assertIn("Run this block once per plan, not once per task", wake)
        self.assertIn("It skips itself on the loaded `WAKE_OWNED=1`", wake)
        self.assertIn("reusing the existing `$PROMPT_FILE` (switch only its WRITE sentence to "
                      "APPEND; never recompose the objective)", flat)

    def test_rearm_runs_only_on_the_one_shot_wait_path(self):
        # An owner stop must not re-arm: the close step runs `done` right after it.
        text = " ".join(_super_dispatch_ref().split())
        rearm = text.index('--ref "$RESUME_STATE_PATH"')
        self.assertLess(text.index("**Schedule-or-stop.**"), rearm)
        self.assertLess(text.index("On the one-shot wait path only, first re-arm"), rearm)
        self.assertLess(rearm, text.index("Where `CronCreate` is callable"))
        self.assertNotRegex(text + _super_text(), r"\bpoint [0-9]\b")

    def test_companion_line_defers_to_the_session_wake_skill(self):
        flat = " ".join(_super_wake_ref().split())
        self.assertIn("When `arm` prints a `companion:` line", flat)
        self.assertIn('says under "When `arm` prints a companion time"', flat)


class TestSkillStepZero(unittest.TestCase):
    """Step 0 prints SKILL_DIR (the wake block needs it) and accepts only the sibling review
    skill, the one directory the shim puts on sys.path."""

    def setUp(self):
        bash_bin = shutil.which("bash")
        if bash_bin is None:
            self.skipTest("bash not found")
        self.bash_bin: str = bash_bin
        self.root = tempfile.mkdtemp(prefix="super-step0-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.skill = os.path.join(self.root, "skills", "ai-kit-spec-execute-superpowers")
        os.makedirs(self.skill)
        with open(os.path.join(self.skill, "ai-kit-spec-superpowers.py"), "w") as shim:
            shim.write("")
        block = _super_block('TOOLS_PY="$REVIEW_SKILL_DIR/ai-kit-spec.py"')
        self.raw_block = block
        self.block = block.replace("<absolute path to THIS SKILL.md>",
                                   os.path.join(self.skill, "SKILL.md"))
        self.env = session_wake_fakes.doc_block_env(self.root, ["dirname", "printf"])

    def _run(self):
        return subprocess.run([self.bash_bin, "-c", self.block], cwd=self.root, env=self.env,
                              capture_output=True, text=True, timeout=60, check=False)

    def test_prints_skill_dir_shim_and_the_sibling_tools_py(self):
        os.makedirs(os.path.join(self.root, "skills", "ai-kit-spec-review"))
        proc = self._run()
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        lines = dict(line.split("=", 1) for line in proc.stdout.splitlines() if "=" in line)
        self.assertEqual(self.skill, lines["SKILL_DIR"])
        self.assertEqual(os.path.join(self.skill, "ai-kit-spec-superpowers.py"), lines["SHIM"])
        self.assertEqual(os.path.join(self.root, "skills", "ai-kit-spec-review", "ai-kit-spec.py"),
                         lines["TOOLS_PY"])

    def test_unfilled_skill_md_placeholder_stops_instead_of_resolving_to_cwd(self):
        # dirname of the literal placeholder is ".", which exists in any cwd
        os.makedirs(os.path.join(self.root, "skills", "ai-kit-spec-review"))
        empty = os.path.join(self.root, "empty")
        os.makedirs(empty)
        proc = subprocess.run([self.bash_bin, "-c", self.raw_block], cwd=empty, env=self.env,
                              capture_output=True, text=True, timeout=60, check=False)
        self.assertEqual(1, proc.returncode, proc.stdout)
        self.assertIn("could not resolve", proc.stdout)
        self.assertNotIn("SKILL_DIR=", proc.stdout)

    def test_review_skill_elsewhere_is_refused(self):
        os.makedirs(os.path.join(self.root, "home", ".claude", "skills", "ai-kit-spec-review"))
        proc = self._run()
        self.assertEqual(1, proc.returncode, proc.stdout)
        self.assertIn("ai-kit-spec-review is not installed beside", proc.stdout)
        self.assertNotIn("TOOLS_PY=", proc.stdout)


_SUPER_REFS = _SUPER_SKILL.parent / "references"


class TestFixRoundAndWakeScope(unittest.TestCase):
    """Fix rounds 1-3 never re-resolve; the quota wake's Step 2 ban covers its re-dispatch only."""

    @staticmethod
    def _flat(path: pathlib.Path) -> str:
        return " ".join(path.read_text(encoding="utf-8").split())

    def test_rounds_one_to_three_reuse_the_injection(self):
        skill = self._flat(_SUPER_SKILL)
        self.assertIn("Fix rounds 1–3 reuse the task's `$INJECTION_JSON` unchanged", skill)
        self.assertIn("Rounds 1–3 keep `$INJECTION_JSON` and skip Step 2", skill)
        self.assertNotIn("repeats on every task and fix round", skill)
        escalation = self._flat(_SUPER_REFS / "escalation.md")
        self.assertIn("rounds 1–3 run no resolution and reuse `$INJECTION_JSON`", escalation)
        self.assertNotIn("this round's same `--exclude-keys-json`", escalation)

    def test_schedule_or_stop_requires_classified_quota_and_numeric_tokens(self):
        flat = self._flat(_SUPER_REFS / "dispatch-external-cli.md")
        self.assertIn('Only a classified `"quota"` with `RETURNCODE` 75', flat)
        self.assertIn("both matching `[0-9]+`", flat)
        skill = " ".join((_SUPER_REFS.parent / "SKILL.md").read_text(encoding="utf-8").split())
        stops = " ".join((_SUPER_REFS / "resolution-stops.md").read_text(encoding="utf-8").split())
        self.assertIn("`ai-kit-spec: ignoring untrusted project-local config <path>;", skill)
        self.assertIn("ai-kit-spec: ignoring untrusted project-local config", stops)

    def test_unknown_anchor_stop_comes_before_the_floor_script(self):
        text = (_SUPER_REFS / "escalation.md").read_text(encoding="utf-8")
        self.assertLess(text.index("**An empty or unknown anchor never dispatches.**"),
                        text.index("ladder.index(stuck)"))

    def test_wake_prompt_binds_fourteen_placeholders_with_skill_dir_and_tools_py(self):
        text = (_SUPER_REFS / "quota-wake.md").read_text(encoding="utf-8")
        match = re.search(r"```text\n(.*?)```", text, re.DOTALL)
        assert match is not None
        prompt = match.group(1)
        placeholders = set(re.findall(r"=<([A-Z_]+)>", prompt))
        self.assertIn("TOOLS_PY", placeholders)
        # the task-paths guard exits on an empty SKILL_DIR, so the woken run must be given it
        self.assertIn("SKILL_DIR", placeholders)
        self.assertEqual(14, len(placeholders))
        self.assertIn("Substitute all fourteen placeholders", text)
        self.assertIn("filling its six placeholder lines from the step 1 and step 2 values",
                      " ".join(prompt.split()))
        self.assertIn("its fourteen placeholders",
                      self._flat(_SUPER_REFS / "dispatch-external-cli.md"))
        flat_prompt = " ".join(prompt.split())
        self.assertIn("For this re-dispatch only: do not resolve a candidate", flat_prompt)
        self.assertIn("redo the ai-kit-spec-execute-superpowers Step 0 and take BRIEF_FILE "
                      "from the restored ledger", flat_prompt)
        self.assertNotIn("point 3", flat_prompt)

    def test_no_json_stop_writes_pinned_state_and_design_notes_name_the_rule(self):
        skill = self._flat(_SUPER_REFS / "dispatch-external-cli.md")
        self.assertIn("stop exactly as the `real_error` branch does (pinned state write", skill)
        self.assertNotIn("no result\"; exit 1", _SUPER_SKILL.read_text(encoding="utf-8"))
        notes = self._flat(_SUPER_REFS / "design-notes.md")
        self.assertNotIn("predate the owner rule", notes)
        self.assertIn("never-switch rule (ai-kit-cross-ai section 8)", notes)


class TestPinnedResumeAndReturnCode69OneRule(unittest.TestCase):
    """r18: one rule for a pinned resume at any round, and 69 is always an owner stop."""

    @staticmethod
    def _flat(path) -> str:
        return " ".join(path.read_text(encoding="utf-8").split())

    def test_pinned_injection_never_re_enters_step_two_at_any_round(self):
        skill = " ".join(_super_text().split())
        esc = self._flat(_SUPER_REFS / "escalation.md")
        state = self._flat(_SUPER_REFS / "state-management.md")
        self.assertIn("`injection_json` is pinned: it re-dispatches unchanged at any "
                      "`$FIX_ROUND`", skill)
        self.assertIn("a resume with no pinned `injection_json`", skill)
        self.assertNotIn("a resume that re-enters Step 2", skill)
        self.assertIn(
            "a restored `injection_json` always re-dispatches unchanged at any round", esc
        )
        self.assertIn("with a restored `$FIX_ROUND >= 4` and no `injection_json`", state)
        self.assertIn("that always goes to Step 3, at any `$FIX_ROUND`", state)

    def test_return_code_69_is_an_owner_stop_never_a_wait(self):
        dispatch = self._flat(_SUPER_REFS / "dispatch-external-cli.md")
        self.assertNotIn("reaches it as an owner stop", dispatch)
        self.assertIn("is classified `quota` but is an owner stop: relay, write pinned state, "
                      "schedule nothing", dispatch)
        self.assertIn("every `RETURNCODE` 69", " ".join(_super_text().split()))

    def test_cross_ai_contract_has_a_do_not_load_clause_and_pair_rule_is_a_pointer(self):
        skill = " ".join(_super_text().split())
        self.assertIn("Do NOT load it at any other point", skill)
        self.assertNotIn("A reviewer or executor is a (runtime, model) pair", skill)
        self.assertIn("`ai-kit-spec-config` and `ai-kit-spec-review`", skill)


class TestRound21OneRule(unittest.TestCase):
    """r20: one rule for the rounds 4-5 re-entry, quoting, the quota wake order."""

    @staticmethod
    def _flat(path) -> str:
        return " ".join(path.read_text(encoding="utf-8").split())

    def test_rounds_four_five_re_entry_has_one_rule_in_all_three_files(self):
        pick = "is only the source of `ladder_keys`: never act on its mode or dispatch it"
        floor = "before any dispatch, compute the floor from the restored `$ESCALATION_ANCHOR_KEY`"
        for path in (_SUPER_SKILL, _SUPER_REFS / "state-management.md",
                     _SUPER_REFS / "escalation.md"):
            flat = self._flat(path)
            self.assertIn(pick, flat, path.name)
            self.assertIn(floor, flat, path.name)
        self.assertIn("yet at 4 or more still take the floor below", self._flat(_SUPER_SKILL))

    def test_quoted_expansion_keeps_hostile_json_whole(self):
        hostile = json.dumps({"k/m": 'a"b`c$d\ne;\' rm'})
        with tempfile.TemporaryDirectory(prefix="super-quote-") as root:
            path = os.path.join(root, "P.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(hostile)
            block = _super_block("a.update(json.loads(sys.argv[2]))")
            merge = re.search(r"^EXCLUDED_REASONS_JSON=.*?\)\"$", block, re.DOTALL | re.MULTILINE)
            assert merge is not None
            script = (f'PRIOR_REASONS_JSON="$(cat {shlex.quote(path)})"\n'
                      f'WAVE_REASONS_JSON="{{}}"\n{merge.group(0)}\n'
                      'printf "%s" "$EXCLUDED_REASONS_JSON"\n')
            proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                                  timeout=60, check=False)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual(json.loads(hostile), json.loads(proc.stdout))
        self.assertIn("a double-quoted expansion is never re-parsed", self._flat(_SUPER_SKILL))

    def test_quota_wake_prompt_order_is_bind_paths_resume_found_scalars_restore(self):
        text = (_SUPER_REFS / "quota-wake.md").read_text(encoding="utf-8")
        block = re.search(r"```text\n(.*?)```", text, re.DOTALL)
        assert block is not None, "quota-wake.md has no ```text block"
        prompt = " ".join(block.group(1).split())
        order = ["read that state file", "task-paths block", "never executes Step 2 or the Seed",
                 "if RESUME_FOUND is not 1", "Record the printed SCALARS path",
                 'the "Restore" script']
        positions = [prompt.index(item) for item in order]
        self.assertEqual(sorted(positions), positions)
        self.assertNotIn("Step 2 included", prompt)
        self.assertIn("a later fix round of this task starts at Step 3 with the restored pin, "
                      "and Step 2 runs only for a later task or an owner-named pair", prompt)

    def test_node_crash_and_companion_skill_clauses(self):
        self.assertIn("that crash is a `real_error` of the pair, never a reason to switch pairs",
                      self._flat(_SUPER_SKILL))
        self.assertIn("Do NOT load the rest of ai-kit-session-wake",
                      self._flat(_SUPER_REFS / "session-wake.md"))


# ── 26-11: JSON values live in files; the owner-named replacement pair recipe ──────────────


def _ref_blocks(name: str) -> list:
    text = (_SUPER_REFS / name).read_text(encoding="utf-8")
    return re.findall(r"```bash\n(.*?)```", text, re.DOTALL)


def _ref_block(name: str, needle: str) -> str:
    for block in _ref_blocks(name):
        if needle in block:
            return block
    raise AssertionError(f"no bash block in {name} has {needle!r}")


class TestJsonFilesAndOwnerNamedPair(unittest.TestCase):
    """The docs' own scripts, run for real against a scratch RUN_DIR."""

    def setUp(self):
        bash_bin = shutil.which("bash")
        if bash_bin is None:
            self.skipTest("bash not found")
        self.bash_bin: str = bash_bin
        self.root = tempfile.mkdtemp(prefix="super-json-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.run_dir = os.path.join(self.root, "run")
        os.makedirs(self.run_dir)

    def _put(self, name, value):
        with open(os.path.join(self.run_dir, name + ".json"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps(value))

    def _get(self, name):
        with open(os.path.join(self.run_dir, name + ".json"), encoding="utf-8") as handle:
            return json.load(handle)

    def _bash(self, block, **env):
        return subprocess.run(
            [self.bash_bin, "-c", block], cwd=self.root, capture_output=True, text=True,
            env={**os.environ, "RUN_DIR": self.run_dir, **env}, timeout=60, check=False)

    def test_no_block_pastes_json_into_a_command(self):
        for name in ("SKILL.md", "dispatch-external-cli.md", "state-management.md",
                     "escalation.md"):
            path = _SUPER_SKILL if name == "SKILL.md" else _SUPER_REFS / name
            text = path.read_text(encoding="utf-8")
            for blocks in re.findall(r"```bash\n(.*?)```", text, re.DOTALL):
                self.assertNotRegex(blocks, r"printf '[^']*_JSON=%s", name)
            self.assertNotIn('--injection-json "$INJECTION_JSON"', text)

    def test_restore_writes_hostile_json_to_files_and_rejects_a_mismatch(self):
        hostile = {"mode": "external_cli", "key": "codex/terra", "runtime": "codex",
                   "detail": 'quote " dollar $HOME tick ` $(touch pwned)', "ladder_keys": ["a"]}
        state = {"framework": "superpowers", "plan_path": "p.md", "task_index": "2",
                 "fix_round": 4, "excluded_keys": ["x"], "reasons": {"x": "auth", "y": "auth"},
                 "last_dispatched_key": "a", "escalation_anchor_key": "b",
                 "injection_json": hostile}
        path = os.path.join(self.root, "state.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        block = _ref_block("state-management.md", "state file does not match")
        scalars = os.path.join(self.root, "scalars.env")
        env = {"RESUME_STATE_PATH": path, "PLAN_FILE": "p.md", "TASK_N": "2", "SCALARS": scalars}
        proc = self._bash(block, **env)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("FIX_ROUND=4", proc.stdout)
        with open(scalars, encoding="utf-8") as handle:
            self.assertEqual(proc.stdout, handle.read())
        self.assertIn("INJECTION_KEY=codex/terra", proc.stdout)
        self.assertEqual(hostile, self._get("INJECTION_JSON"))
        self.assertEqual({"x": "auth"}, self._get("PRIOR_REASONS_JSON"))
        self.assertEqual(["x"], self._get("EXCLUDED_KEYS_JSON"))
        self.assertEqual([], self._get("WAVE_TRIED_JSON"))
        self.assertFalse(os.path.exists(os.path.join(self.root, "pwned")))
        self.assertNotEqual(0, self._bash(block, **{**env, "TASK_N": "3"}).returncode)

    def _seed_pair(self):
        self._put("INJECTION_JSON", {"mode": "external_cli", "key": "a/one",
                                     "ladder_keys": ["a/one", "b/two", "c/three"]})
        self._put("PRIOR_EXCLUDED_KEYS_JSON", ["z/old"])
        self._put("PRIOR_REASONS_JSON", {"z/old": "auth"})
        self._put("WAVE_TRIED_JSON", [])
        self._put("WAVE_REASONS_JSON", {})

    def _pair_block(self, owner):
        block = _ref_block("state-management.md", "OWNER_KEY=")
        return block.replace("<the ladder key the owner named, exactly as in ladder_keys>", owner
                             ).replace("<the failed key's real reason from the stop report: auth, "
                                       "timeout, real_error, ...>", "auth")

    def test_owner_named_pair_excludes_every_other_key_and_folds_the_failed_one(self):
        self._seed_pair()
        proc = self._bash(self._pair_block("c/three"))
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual(["a/one", "b/two"], self._get("ESCALATION_EXCLUDE_JSON"))
        self.assertEqual(["a/one"], self._get("WAVE_TRIED_JSON"))
        self.assertEqual({"a/one": "auth"}, self._get("WAVE_REASONS_JSON"))
        self.assertEqual(["a/one", "z/old"], self._get("EXCLUDED_KEYS_JSON"))

    def test_owner_named_key_in_the_prior_permanent_set_is_resolved(self):
        self._seed_pair()
        self._put("PRIOR_EXCLUDED_KEYS_JSON", ["z/old", "c/three"])
        self._put("PRIOR_REASONS_JSON", {"z/old": "auth", "c/three": "capacity"})
        proc = self._bash(self._pair_block("c/three"))
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual(["a/one", "z/old"], self._get("EXCLUDED_KEYS_JSON"))
        self.assertEqual(["z/old"], self._get("PRIOR_EXCLUDED_KEYS_JSON"))
        self.assertEqual({"z/old": "auth"}, self._get("PRIOR_REASONS_JSON"))

    def test_owner_named_second_key_is_the_one_resolve_injection_picks(self):
        # The recipe's files, fed to the real resolve-injection with a 3-key ladder: the owner's
        # second key must survive (an excluded owner key would yield quota_exhausted).
        keys = ["a/one", "b/two", "c/three"]
        self._seed_pair()
        self.assertEqual(0, self._bash(self._pair_block("b/two")).returncode)
        candidates = [{"key": k, "model": k.split("/")[1], "runtime": "codex", "vendor": "v",
                       "task_affinity": None, "context_limit": None} for k in keys]
        task_file = os.path.join(self.root, "task-1-brief.md")
        with open(task_file, "w", encoding="utf-8") as handle:
            handle.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
        reasons = {**self._get("PRIOR_REASONS_JSON"), **self._get("WAVE_REASONS_JSON")}
        out = io.StringIO()
        rc = superpowers_cli.main(
            ["resolve-injection", "--cwd", self.root, "--task-file", task_file,
             "--quota-path", os.path.join(self.root, "quota.json"),
             "--exclude-keys-json", json.dumps(self._get("EXCLUDED_KEYS_JSON")),
             "--excluded-reasons-json", json.dumps(reasons),
             "--escalation-excluded-keys-json", json.dumps(self._get("ESCALATION_EXCLUDE_JSON"))],
            assemble_candidates_fn=lambda cwd, env: (candidates, keys),
            cache_read_json_fn=lambda path: {}, cache_write_json_fn=lambda path, data: None,
            refresh_quota_cache_fn=lambda config, ks, existing, _ttl: {},
            route_all_fn=_session_routes, stdout=out)
        self.assertEqual(0, rc)
        result = json.loads(out.getvalue())
        self.assertEqual(("external_cli", "b/two"), (result["mode"], result["key"]))

    def test_owner_named_pair_refuses_the_failed_key_and_unknown_keys(self):
        self._seed_pair()
        for owner in ("a/one", "nope/x"):
            self.assertNotEqual(0, self._bash(self._pair_block(owner)).returncode, owner)

    def test_real_error_fold_records_the_dispatch_reason(self):
        block = _ref_block("dispatch-external-cli.md", "FOLD_REASON=\"$(python3")
        self.assertNotIn("FOLD_REASON=quota", block)
        quota_fold = _ref_block("dispatch-external-cli.md", "FOLD_REASON=quota")
        self.assertTrue(quota_fold.startswith("FOLD_REASON=quota\n"))
        self.assertNotIn("first line replaced", " ".join(
            (_SUPER_REFS / "dispatch-external-cli.md").read_text(encoding="utf-8").split()))
        self._put("PRIOR_EXCLUDED_KEYS_JSON", [])
        self._put("WAVE_TRIED_JSON", [])
        self._put("WAVE_REASONS_JSON", {})
        result = os.path.join(self.root, "dispatch.json")
        with open(result, "w", encoding="utf-8") as handle:
            json.dump({"returncode": 1, "reason": "auth", "stdout": 'say "hi" $x `y`'}, handle)
        proc = self._bash(block, DISPATCH_BASE=result[:-len(".json")], INJECTION_KEY="a/one")
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual({"a/one": "auth"}, self._get("WAVE_REASONS_JSON"))
        self.assertEqual(["a/one"], self._get("EXCLUDED_KEYS_JSON"))


class TestScalarFile(unittest.TestCase):
    """Scalars live in a file the loader restores; hostile values stay inert."""

    HOSTILE = 'q" s\' d$HOME t` $(touch pwned) a=b= \\n'

    def setUp(self):
        bash_bin = shutil.which("bash")
        if bash_bin is None:
            self.skipTest("bash not found")
        self.bash_bin: str = bash_bin
        self.root = tempfile.mkdtemp(prefix="super-scalars-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.scalars = os.path.join(self.root, "scalars.env")

    def _bash(self, block, **env):
        return subprocess.run(
            [self.bash_bin, "-c", block], cwd=self.root, capture_output=True, text=True,
            env={**os.environ, "SCALARS": self.scalars, **env}, timeout=60, check=False)

    def _loader(self):
        block = _super_block("IFS== read")
        return block.replace("<the path the task-paths block printed>", self.scalars)

    def test_a_persisted_hostile_value_round_trips_and_stays_inert(self):
        write = self._bash(
            'for n in LAST_DISPATCHED_KEY FIX_ROUND; do printf "%s=%s\\n" "$n" '
            '"${!n}"; done | tee -a "$SCALARS" >/dev/null', LAST_DISPATCHED_KEY=self.HOSTILE,
            FIX_ROUND="4")
        self.assertEqual(0, write.returncode, write.stderr)
        read = self._bash(self._loader() + '\nprintf "%s" "$LAST_DISPATCHED_KEY"; '
                          'printf "|%s" "$FIX_ROUND"')
        self.assertEqual(0, read.returncode, read.stderr)
        self.assertEqual(self.HOSTILE + "|4", read.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.root, "pwned")))

    def test_the_last_line_wins_and_odd_names_are_skipped(self):
        with open(self.scalars, "w", encoding="utf-8") as handle:
            handle.write("FIX_ROUND=1\nbad-name=x\nlower=y\nFIX_ROUND=2\nEMPTY=\n")
        read = self._bash(self._loader() + '\nprintf "%s|%s|%s" "$FIX_ROUND" "${EMPTY-unset}" '
                          '"${lower-unset}"')
        self.assertEqual(0, read.returncode, read.stderr)
        self.assertEqual("2||unset", read.stdout)

    def test_seed_twice_keeps_a_nonzero_fix_round_but_resets_for_another_task(self):
        seed = _ref_block("state-management.md", "SEEDED_TASK")
        run_dir = os.path.join(self.root, "run")
        os.makedirs(run_dir)
        env = {"RUN_DIR": run_dir, "TASK_N": "2"}
        script = self._loader() + "\n" + seed + "\n" + self._loader() + \
            '\nprintf "R=%s|%s|%s" "$FIX_ROUND" "$LAST_DISPATCHED_KEY" "$ESCALATION_ANCHOR_KEY"'
        first = self._bash(script, **env)
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertTrue(first.stdout.endswith("R=0||"), first.stdout)
        with open(self.scalars, "a", encoding="utf-8") as handle:  # a stop with no state file
            handle.write("FIX_ROUND=4\nLAST_DISPATCHED_KEY=a/one\nESCALATION_ANCHOR_KEY=a/one\n")
        again = self._bash(script, **env)  # last line wins in the loader
        self.assertEqual(0, again.returncode, again.stderr)
        self.assertTrue(again.stdout.endswith("R=4|a/one|a/one"), again.stdout)
        with open(self.scalars, encoding="utf-8") as handle:
            self.assertEqual(1, handle.read().count("SEEDED_TASK="))
        other = self._bash(script, **{**env, "TASK_N": "3"})
        self.assertTrue(other.stdout.endswith("R=0||"), other.stdout)
        # the close block's WAKE_OWNED=0 line is a different name: the seed leaves it alone
        with open(self.scalars, "a", encoding="utf-8") as handle:
            handle.write("WAKE_OWNED=0\n")
        wake = self._bash(script + '\nprintf "|%s" "$WAKE_OWNED"', **{**env, "TASK_N": "3"})
        self.assertTrue(wake.stdout.endswith("|0"), wake.stdout)

    def test_every_listing_that_prints_scalars_appends_them(self):
        for name, needle in (("SKILL.md", "RESUME_FOUND"), ("session-wake.md", "WAKE_OWNED"),
                             ("dispatch-external-cli.md", "REPORT_MODE=%s"),
                             ("dispatch-external-cli.md", "RETRY_AFTER_S=%s")):
            path = _SUPER_SKILL if name == "SKILL.md" else _SUPER_REFS / name
            blocks = re.findall(r"```bash\n(.*?)```", path.read_text(encoding="utf-8"), re.DOTALL)
            hits = [b for b in blocks if needle in b and "printf" in b]
            self.assertTrue(hits, needle)
            for block in hits:
                self.assertIn('tee -a "$SCALARS"', block, needle)
        text = " ".join(_SUPER_SKILL.read_text(encoding="utf-8").split())
        self.assertNotIn("re-substituted verbatim", text)

    def test_capacity_is_persisted_as_permanent_and_the_docs_say_so(self):
        from ai_kit_spec_superpowers.dispatch_injection import compute_resume_exclusions
        self.assertEqual(["cap"], compute_resume_exclusions(["cap", "q"], {"cap": "capacity",
                                                                          "q": "quota"}, []))
        skill = " ".join((_SUPER_REFS / "resolution-stops.md").read_text(encoding="utf-8").split())
        self.assertIn('`"capacity"` included, is saved as a permanent exclusion', skill)
        self.assertNotIn("later retry on the same lane", skill)
        for name in ("escalation.md", "state-management.md"):
            text = " ".join((_SUPER_REFS / name).read_text(encoding="utf-8").split())
            self.assertIn("permanent exclusion", text, name)


class TestProgressiveDisclosure(unittest.TestCase):
    """SKILL.md stays a decision flow; every reference has an explicit load trigger."""

    def test_skill_is_short_and_every_reference_has_a_trigger(self):
        text = _super_text()
        self.assertLessEqual(len(text.splitlines()), 300)
        refs = sorted(p.name for p in (_SUPER_SKILL.parent / "references").glob("*.md"))
        for name in refs:
            body = (_SUPER_SKILL.parent / "references" / name).read_text(encoding="utf-8")
            if name != "design-notes.md":  # optional background, no mandatory read
                self.assertIn("MANDATORY", body.split("\n## ")[0], name)
            if name != "state-management.md":
                self.assertIn("Do NOT load", body + text, name)
            self.assertIn(f"references/{name}", text + _super_dispatch_ref(), name)

    def test_empty_anchor_stop_is_named_in_step_three(self):
        flat = " ".join(_super_text().split())
        self.assertIn("An empty anchor, or one missing from `ladder_keys`, dispatches nothing",
                      flat)



class TestRound22Wording(unittest.TestCase):
    """r21: restore never dispatches the plain pick, wake binds, Step 0 placeholder, design note."""

    @staticmethod
    def _flat(path) -> str:
        return " ".join(path.read_text(encoding="utf-8").split())

    def test_step2_end_and_restore_never_dispatch_the_plain_pick_at_round_four(self):
        skill = self._flat(_SUPER_SKILL)
        restore = self._flat(_SUPER_REFS / "state-management.md")
        self.assertIn("dispatch only the result of `references/escalation.md`'s resolve block, "
                      "never this pick", skill)
        self.assertIn("Step 3 dispatches that result, never the plain pick", restore)

    def test_step0_placeholder_dirname_dot_is_skipped(self):
        block = _super_block('case "$d" in')
        self.assertIn('""|.|*"<"*', block)
        self.assertIn("Replace `<absolute path to THIS SKILL.md>` with the absolute path",
                      self._flat(_SUPER_SKILL))

    def test_quota_wake_names_the_state_file_and_the_scalar_file_holds_the_paths(self):
        wake = self._flat(_SUPER_REFS / "quota-wake.md")
        self.assertIn("at RESUME_STATE_PATH from step 1", wake)
        self.assertIn("PLAN_FILE and TASK_N are then in the file too", wake)
        block = " ".join(_super_block("PROJECT_KEY RESUME_STATE_PATH").split())
        self.assertIn("PLAN_FILE TASK_N QUOTA_PATH", block)

    def test_injection_json_quotes_are_mandatory_and_design_note_is_exact(self):
        self.assertIn("The quotes around", self._flat(_SUPER_REFS / "dispatch-external-cli.md"))
        notes = self._flat(_SUPER_REFS / "design-notes.md")
        self.assertIn("`dispatch-task` reads no tiers", notes)
        self.assertNotIn("nothing like `ai_kit_spec.config_io.resolve_timeout_tiers`", notes)


class TestRound23OnePath(unittest.TestCase):
    """Round 23: the Seed, anchor, fold and floor rules each have one path."""

    def setUp(self):
        bash_bin = shutil.which("bash")
        if bash_bin is None:
            self.skipTest("bash not found")
        self.bash_bin: str = bash_bin
        self.root = tempfile.mkdtemp(prefix="super-r23-")
        self.addCleanup(shutil.rmtree, self.root, True)

    def _bash(self, block, **env):
        return subprocess.run(
            [self.bash_bin, "-c", block], cwd=self.root, capture_output=True, text=True,
            env={**os.environ, **env}, timeout=60, check=False)

    @staticmethod
    def _flat(path) -> str:
        return " ".join(path.read_text(encoding="utf-8").split())

    def test_seed_is_never_run_from_the_quota_wake(self):
        self.assertIn("never from the quota-wake prompt", self._flat(_SUPER_SKILL))
        self.assertIn("This run never executes Step 2 or the Seed block",
                      self._flat(_SUPER_REFS / "quota-wake.md"))

    def test_only_an_ok_dispatch_records_the_last_dispatched_key(self):
        text = (_SUPER_REFS / "dispatch-external-cli.md").read_text(encoding="utf-8")
        after = _ref_block("dispatch-external-cli.md", "REPORT_MODE=%s")
        self.assertNotIn("LAST_DISPATCHED_KEY", after)
        ok = " ".join(text[text.index('- **`"ok"`**'):].split()[:40])
        found = re.search(r"`(printf 'LAST_DISPATCHED_KEY=.*?)`", ok)
        assert found is not None, "dispatch-external-cli.md has no ok printf line"
        line = found.group(1)
        scalars = os.path.join(self.root, "s.env")
        proc = self._bash(line, INJECTION_KEY="a/one", SCALARS=scalars)
        self.assertEqual(0, proc.returncode, proc.stderr)
        with open(scalars, encoding="utf-8") as handle:
            self.assertEqual("LAST_DISPATCHED_KEY=a/one\n", handle.read())

    def test_real_error_fold_loads_the_result_file_first_and_survives_a_missing_one(self):
        block = _ref_block("dispatch-external-cli.md", 'FOLD_REASON="$(python3')
        self.assertNotIn("$(cat \"$DISPATCH_BASE.json\")\")", block)
        head = "\n".join(block.splitlines()[:2])
        proc = self._bash(head + '\nprintf "%s" "$FOLD_REASON"',
                          DISPATCH_BASE=os.path.join(self.root, "none"))
        self.assertEqual("real_error", proc.stdout)

    def test_the_floor_script_stops_on_an_empty_or_unknown_anchor(self):
        block = _ref_block("escalation.md", "ESCALATION_EXCLUDE_JSON saved")
        run_dir = os.path.join(self.root, "run")
        os.makedirs(run_dir)
        with open(os.path.join(run_dir, "INJECTION_JSON.json"), "w", encoding="utf-8") as handle:
            json.dump({"ladder_keys": ["a/one", "b/two", "c/three"]}, handle)
        target = os.path.join(run_dir, "ESCALATION_EXCLUDE_JSON.json")
        for anchor in ("", "z/gone"):
            proc = self._bash(block, RUN_DIR=run_dir, ESCALATION_ANCHOR_KEY=anchor)
            self.assertEqual(1, proc.returncode, anchor)
            self.assertIn("STOP", proc.stderr)
            self.assertFalse(os.path.exists(target))
        proc = self._bash(block, RUN_DIR=run_dir, ESCALATION_ANCHOR_KEY="b/two")
        self.assertEqual(0, proc.returncode, proc.stderr)
        with open(target, encoding="utf-8") as handle:
            self.assertEqual(["b/two", "c/three"], json.load(handle))
