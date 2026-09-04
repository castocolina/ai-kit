import io
import json
import os
import sys
import tempfile
import unittest

# Bootstraps every package root this plan's tests need. ai_kit_spec_superpowers (this plan) and
# ai_kit_spec (Plan 1, Foundation) both live outside this file's own directory, on no search path
# by default. skills/ai-kit-spec-execute is ALSO added here (not just
# skills/ai-kit-spec-execute-superpowers) because Task 5's detect_framework module lives there --
# this is the ONE bootstrap block for the whole file, at the top; it is never repeated.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute-superpowers"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute"))

from ai_kit_spec_superpowers import dispatch_injection, task_classification
from ai_kit_spec_superpowers import cli as superpowers_cli
import detect_framework as router_detect_framework


class TestClassifyTask(unittest.TestCase):
    def test_classifies_frontend_from_file_extensions(self):
        task = "### Task 3: Button\n**Files:**\n- Create: `src/components/Button.tsx`\n"
        self.assertEqual(task_classification.classify_task(task), "frontend")

    def test_classifies_backend_from_file_paths(self):
        task = "### Task 4: API\n**Files:**\n- Create: `server/api/handlers.py`\n"
        self.assertEqual(task_classification.classify_task(task), "backend")

    def test_classifies_mixed_when_both_signal_types_present(self):
        task = ("### Task 5: Full-stack widget\n**Files:**\n"
                "- Create: `src/components/Widget.tsx`\n- Create: `server/api/widget.py`\n")
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
        self.assertEqual(task_classification.extract_touched_paths(task),
                          ["existing.py:123-145"])


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
                {"key": "claude/opus-5", "model": "opus", "cli": None, "vendor": "anthropic"},
                {"key": "codex/terra", "model": "gpt-5.6-terra", "cli": "codex", "vendor": "openai",
                 "task_affinity": "backend", "context_limit": 1_000_000},
            ],
        }
        candidates, top_n_keys = dispatch_injection.assemble_candidates(
            "/repo", {}, cfg_resolve_fn=lambda cwd, env: fake_resolved)
        self.assertEqual(top_n_keys, ["claude/opus-5", "codex/terra"])
        self.assertEqual(candidates[1]["task_affinity"], "backend")
        self.assertEqual(candidates[1]["cli"], "codex")

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
                {"key": "claude/opus-5", "model": "opus", "cli": None, "vendor": "anthropic",
                 "strength": "planning"},
                {"key": "codex/terra", "model": "gpt-5.6-terra", "cli": "codex", "vendor": "openai",
                 "strength": "coding", "effort": "high", "service_tier": "priority",
                 "timeout_tiers": [900, 1800]},
            ],
        }
        candidates, top_n_keys = dispatch_injection.assemble_candidates(
            "/repo", {}, cfg_resolve_fn=lambda cwd, env: fake_resolved)
        self.assertIsNone(candidates[0]["task_affinity"])
        self.assertIsNone(candidates[0]["context_limit"])
        self.assertEqual(candidates[1]["effort"], "high")
        self.assertEqual(candidates[1]["service_tier"], "priority")
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {}, {}, top_n_keys, quota={})
        self.assertEqual(result, {"mode": "native_claude", "model": "opus", "key": "claude/opus-5"})

    def test_purpose_field_is_threaded_through_from_config(self):
        def fake_cfg_resolve(cwd, env):
            return {
                "policy": {"ladder": ["a"]},
                "reviewers": [
                    {"key": "a", "model": "m", "cli": "codex", "vendor": "openai",
                     "command": "codex exec -m {model}", "purpose": "execute"},
                ],
            }
        candidates, top_n_keys = dispatch_injection.assemble_candidates(
            "/fake/cwd", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertEqual(candidates[0]["purpose"], "execute")

    def test_missing_purpose_field_comes_back_none(self):
        def fake_cfg_resolve(cwd, env):
            return {
                "policy": {"ladder": ["a"]},
                "reviewers": [{"key": "a", "model": "m", "cli": "codex", "vendor": "openai"}],
            }
        candidates, _ = dispatch_injection.assemble_candidates(
            "/fake/cwd", {}, cfg_resolve_fn=fake_cfg_resolve)
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
            {"key": "claude/opus-5", "model": "opus", "cli": None, "vendor": "anthropic",
             "task_affinity": None, "context_limit": None},
            {"key": "codex/terra", "model": "gpt-5.6-terra", "cli": "codex", "vendor": "openai",
             "task_affinity": None, "context_limit": None},
        ]
        task = "### Task 1\n**Files:**\n- Create: `a.py`\n"
        result = dispatch_injection.compute_ladder_keys(task, candidates, {}, {},
                                                          ["claude/opus-5"])
        self.assertEqual(result, ["claude/opus-5", "codex/terra"])


class TestBuildDispatchInjection(unittest.TestCase):
    def test_native_claude_mode_when_top_candidate_has_quota(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "claude/opus-5", "cli": None, "model": "opus",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {"server/api.py": 1000}, {}, ["claude/opus-5"], quota={})
        self.assertEqual(result, {"mode": "native_claude", "model": "opus",
                                   "key": "claude/opus-5"})

    def test_external_cli_mode_when_top_candidate_is_another_cli(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {"server/api.py": 1000}, {}, ["codex/terra"], quota={})
        self.assertEqual(result, {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                                   "model": "gpt-5.6-terra", "effort": None, "service_tier": None})

    def test_escalates_past_a_quota_exhausted_top_candidate(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {"key": "claude/opus-5", "cli": None, "model": "opus",
             "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
             "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        quota = {"claude/opus-5": {"available": False}, "codex/terra": {"available": True}}
        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {}, {}, ["claude/opus-5", "codex/terra"], quota=quota)
        self.assertEqual(result["mode"], "external_cli")
        self.assertEqual(result["key"], "codex/terra")

    def test_drops_a_quota_available_candidate_with_no_usable_dispatch_mechanism(self):
        # CRITICAL finding: a candidate can have quota AND still be undispatchable (its cli has no
        # registered execute-mode builder -- build_execute_command raises ValueError for it). This
        # must be dropped, not returned as a broken external_cli injection that blows up later.
        # MEDIUM finding: "gemini" is used here, not "grok" -- ai_kit_spec.commands._COMMAND_
        # BUILDERS (confirmed by reading commands.py) registers a real (_EXECUTE, "grok") builder
        # today, so "grok" would misstate an existing capability as absent; "gemini" has NO entry
        # in _COMMAND_BUILDERS at all -- review builders are exactly codex/claude/grok/opencode/
        # cursor-agent, and gemini is not among them either -- so this fixture matches a real gap
        # in today's code (build_execute_command("gemini") raises ValueError) rather than
        # simulating one that doesn't exist.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {"key": "gemini/main", "cli": "gemini", "model": "gemini-3-pro",
             "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
             "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        quota = {"gemini/main": {"available": True}, "codex/terra": {"available": True}}

        def fake_build_execute_command(cli, **params):
            if cli == "gemini":
                raise ValueError("no execute-mode builder registered for cli='gemini'")
            return "codex exec --sandbox workspace-write -m {model}"

        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {}, {}, ["gemini/main", "codex/terra"], quota=quota,
            build_execute_command_fn=fake_build_execute_command)
        self.assertEqual(result["key"], "codex/terra")

    def test_cli_claude_is_routed_external_not_treated_as_native(self):
        # CRITICAL finding: only cli is None guarantees a native Agent-tool alias. cli == "claude"
        # is a real, subprocess-invoked entry -- ai_kit_spec.commands._COMMAND_BUILDERS registers
        # a real (_EXECUTE, "claude") builder for it -- and must be routed through external_cli
        # mode like any other CLI-set entry, never silently folded into native_claude.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "claude-cli/opus-5", "cli": "claude", "model": "opus",
                        "task_affinity": "backend", "context_limit": 1_000_000}]

        def fake_build_execute_command(cli, **params):
            return "claude -p --model {model}"

        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {}, {}, ["claude-cli/opus-5"], quota={},
            build_execute_command_fn=fake_build_execute_command)
        self.assertEqual(result, {"mode": "external_cli", "key": "claude-cli/opus-5",
                                   "cli": "claude", "model": "opus", "effort": None,
                                   "service_tier": None})

    def test_no_surviving_candidates_raises_value_error(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        with self.assertRaises(ValueError):
            dispatch_injection.build_dispatch_injection(task, [], {}, {}, [], quota={})

    def test_every_candidate_quota_exhausted_raises_quota_exhausted_error_with_reasons(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "claude/opus-5", "cli": None, "model": "opus",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"claude/opus-5": {"available": False, "detail": "usage limit reached"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["claude/opus-5"], quota=quota)
        self.assertEqual(ctx.exception.tried, ["claude/opus-5"])
        self.assertEqual(ctx.exception.reasons, {"claude/opus-5": "quota"})
        self.assertFalse(ctx.exception.all_auth_failures)
        self.assertEqual(ctx.exception.task_type, "backend")

    def test_auth_failure_is_classified_distinctly_and_flagged_all_auth_failures(self):
        # HIGH finding: an unauthenticated/unentitled candidate must never look like a real,
        # time-bound quota exhaustion -- .all_auth_failures is what tells a caller to skip the
        # futile hourly CronCreate wake and surface an actionable setup error instead.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"codex/terra": {"available": False, "detail": "Error: not authenticated"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["codex/terra"], quota=quota)
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "auth"})
        self.assertTrue(ctx.exception.all_auth_failures)
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_timeout_failure_classified_distinctly_not_quota(self):
        # HIGH finding: a probe timeout is a real, non-time-bound problem (a hung/broken CLI
        # invocation) -- it must never be classified "quota" and trigger a futile hourly wake.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"codex/terra": {"available": False, "detail": "timed out after 30s"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["codex/terra"], quota=quota)
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "timeout"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_malformed_command_template_classified_as_configuration_not_quota(self):
        # HIGH finding: a bad/missing command template is a config problem -- never fixed by
        # waiting for quota to refill.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"codex/terra": {"available": False,
                                   "detail": "reviewer 'codex/terra' has a malformed command "
                                             "template: KeyError"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["codex/terra"], quota=quota)
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "configuration"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_os_error_style_failure_classified_as_dispatch_unavailable(self):
        # HIGH finding: the CLI binary itself failing to launch is not a quota problem either.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"codex/terra": {"available": False,
                                   "detail": "[Errno 2] No such file or directory: 'codex'"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["codex/terra"], quota=quota)
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "dispatch_unavailable"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_arbitrary_nonzero_exit_classified_as_real_error_not_quota(self):
        # HIGH finding (the core bug): prior to this revision, EVERY non-auth detail defaulted to
        # "quota" -- a bad model id or any other unrelated failure text is a real error, not a
        # time-bound rate limit, and must never trigger a futile hourly CronCreate wake.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"codex/terra": {"available": False, "detail": "Error: unrecognized model id"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["codex/terra"], quota=quota)
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "real_error"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_any_quota_recoverable_true_when_at_least_one_reason_is_quota(self):
        # HIGH finding: any_quota_recoverable is the general gate a caller uses to decide whether
        # scheduling an hourly CronCreate wake accomplishes anything -- True as soon as ANY tried
        # candidate's reason is "quota", even when others in the same batch are permanent.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {"key": "claude/opus-5", "cli": None, "model": "opus",
             "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
             "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        quota = {"claude/opus-5": {"available": False, "detail": "usage limit reached"},
                  "codex/terra": {"available": False, "detail": "not authenticated"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["claude/opus-5", "codex/terra"], quota=quota)
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
        # recovers, or the hourly CronCreate wake can never actually resume anything.
        result = dispatch_injection.compute_resume_exclusions(
            tried=["claude/opus-5", "codex/terra"],
            reasons={"claude/opus-5": "quota", "codex/terra": "auth"},
            prior_excluded_keys=[])
        self.assertEqual(result, ["codex/terra"])

    def test_prior_permanent_exclusions_are_preserved(self):
        result = dispatch_injection.compute_resume_exclusions(
            tried=["grok/main"], reasons={"grok/main": "no_usable_dispatch"},
            prior_excluded_keys=["codex/terra"])
        self.assertEqual(result, ["codex/terra", "grok/main"])

    def test_round_trip_quota_recovery_makes_candidate_eligible_again(self):
        # The round-trip this CRITICAL finding requires: an all-quota-exhausted ladder computes a
        # resume-state exclusion set, THEN (once quota recovers) a fresh build_dispatch_injection
        # call using THAT exclusion set must be able to pick the previously-exhausted candidate
        # again -- never permanently locked out by its own earlier exhaustion event.
        candidates = [{"key": "claude/opus-5", "cli": None, "model": "opus",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota_when_exhausted = {"claude/opus-5": {"available": False, "detail": "usage limit"}}
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["claude/opus-5"], quota=quota_when_exhausted)
        excluded_keys = dispatch_injection.compute_resume_exclusions(
            ctx.exception.tried, ctx.exception.reasons, [])
        self.assertEqual(excluded_keys, [])  # a quota-only reason -- nothing permanently excluded

        # Resume: candidates filtered by excluded_keys (none removed here), quota now recovered.
        surviving = [c for c in candidates if c["key"] not in excluded_keys]
        quota_recovered = {"claude/opus-5": {"available": True}}
        result = dispatch_injection.build_dispatch_injection(
            task, surviving, {}, {}, ["claude/opus-5"], quota=quota_recovered)
        self.assertEqual(result["key"], "claude/opus-5")


class TestDispatchSuperpowersTask(unittest.TestCase):
    def test_delegates_to_dispatch_execute_with_a_real_candidate_dict(self):
        injection = {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                      "model": "gpt-5.6-terra", "effort": "high", "service_tier": None}
        captured = {}

        def fake_dispatch_execute(candidate, prompt, target_dir, heartbeat_interval, timeout,
                                   format_block=None, tool_availability=None,
                                   agents_tooling_path=None, codegraph_registered=False):
            captured.update(candidate=candidate, prompt=prompt, target_dir=target_dir)
            return {"cli": "codex", "model": "gpt-5.6-terra", "command": "codex exec ...",
                    "returncode": 0, "stdout": "ok", "stderr": "", "timed_out": False}

        result = dispatch_injection.dispatch_superpowers_task(
            injection, "do the task", "/real/scratch/dir", 60, 900,
            dispatch_execute_fn=fake_dispatch_execute)
        self.assertEqual(captured["target_dir"], "/real/scratch/dir")
        self.assertEqual(captured["candidate"]["cli"], "codex")
        self.assertEqual(captured["candidate"]["effort"], "high")
        self.assertEqual(result["returncode"], 0)

    def test_native_claude_injection_raises_value_error(self):
        injection = {"mode": "native_claude", "model": "opus", "key": "claude/opus-5"}
        with self.assertRaises(ValueError):
            dispatch_injection.dispatch_superpowers_task(injection, "prompt", "/dir", 60, 900)

    def test_real_dispatch_execute_path_produces_a_real_workspace_write_command(self):
        # Confirms this wrapper genuinely reaches ai_kit_spec.execute_dispatch.dispatch_execute's
        # OWN real command-building (HIGH finding: never a raw dispatch_with_heartbeat call, never
        # a "{target_dir}" placeholder) by calling the real, un-mocked dispatch_execute and only
        # substituting ITS OWN dispatch_fn (the actual subprocess launch) -- the same pattern
        # tests.test_ai_kit_spec's own execute_dispatch.dispatch_execute tests already use.
        from ai_kit_spec.execute_dispatch import dispatch_execute as real_dispatch_execute

        injection = {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                      "model": "gpt-5.6-terra", "effort": None, "service_tier": None}
        captured_command = {}

        def fake_dispatch_fn(command, prompt, heartbeat_interval, timeout):
            captured_command["value"] = command
            return {"returncode": 0, "stdout": "DONE", "stderr": "", "timed_out": False}

        def dispatch_execute_with_fake_subprocess(candidate, prompt, target_dir,
                                                    heartbeat_interval, timeout, **kwargs):
            return real_dispatch_execute(candidate, prompt, target_dir, heartbeat_interval,
                                          timeout, dispatch_fn=fake_dispatch_fn, **kwargs)

        result = dispatch_injection.dispatch_superpowers_task(
            injection, "do the task", "/real/scratch/dir", 60, 900,
            dispatch_execute_fn=dispatch_execute_with_fake_subprocess)
        self.assertIn("workspace-write", captured_command["value"])
        self.assertIn("/real/scratch/dir", captured_command["value"])
        self.assertEqual(result["command"], captured_command["value"])


class TestClassifyDispatchFailure(unittest.TestCase):
    def test_ok_on_zero_returncode(self):
        self.assertEqual(dispatch_injection.classify_dispatch_failure(
            {"returncode": 0, "stdout": "", "stderr": "", "timed_out": False}), "ok")

    def test_quota_on_quota_signal_and_nonzero_returncode(self):
        self.assertEqual(dispatch_injection.classify_dispatch_failure(
            {"returncode": 1, "stdout": "Error: usage limit reached", "stderr": "",
             "timed_out": False}), "quota")

    def test_real_error_on_auth_signal_even_with_nonzero_returncode(self):
        # HIGH finding: an auth/entitlement/setup failure must classify as real_error, never
        # quota -- it will never be fixed by an hourly quota-wake retry.
        self.assertEqual(dispatch_injection.classify_dispatch_failure(
            {"returncode": 1, "stdout": "Error: not authenticated", "stderr": "",
             "timed_out": False}), "real_error")

    def test_real_error_on_unrelated_nonzero_returncode(self):
        self.assertEqual(dispatch_injection.classify_dispatch_failure(
            {"returncode": 1, "stdout": "SyntaxError", "stderr": "", "timed_out": False}),
            "real_error")

    def test_real_error_on_timeout_even_with_quota_looking_text(self):
        self.assertEqual(dispatch_injection.classify_dispatch_failure(
            {"returncode": -9, "stdout": "rate limit", "stderr": "", "timed_out": True}),
            "real_error")


class TestCliResolveInjection(unittest.TestCase):
    def test_resolve_injection_prints_native_claude_json(self):
        candidates = [{"key": "claude/opus-5", "model": "opus", "cli": None,
                        "vendor": "anthropic", "task_affinity": None, "context_limit": None}]

        def fake_assemble(cwd, env):
            return candidates, ["claude/opus-5"]

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path],
                assemble_candidates_fn=fake_assemble,
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: {},
                stdout=out)
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result, {"mode": "native_claude", "model": "opus",
                                   "key": "claude/opus-5",
                                   "ladder_keys": ["claude/opus-5"]})

    def test_resolve_injection_prints_quota_exhausted_json_with_reasons(self):
        candidates = [{"key": "claude/opus-5", "model": "opus", "cli": None,
                        "vendor": "anthropic", "task_affinity": None, "context_limit": None}]

        def fake_assemble(cwd, env):
            return candidates, ["claude/opus-5"]

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path],
                assemble_candidates_fn=fake_assemble,
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: (
                    {"claude/opus-5": {"available": False, "detail": "usage limit reached"}}),
                stdout=out)
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "quota_exhausted")
        self.assertEqual(result["tried"], ["claude/opus-5"])
        self.assertEqual(result["reasons"], {"claude/opus-5": "quota"})
        self.assertFalse(result["all_auth_failures"])
        # HIGH finding: any_quota_recoverable, not all_auth_failures, is the real gate Task 4's
        # SKILL.md now uses to decide whether an hourly CronCreate wake accomplishes anything.
        self.assertTrue(result["any_quota_recoverable"])
        # CRITICAL finding (Rounds 4-5 capability escalation): ladder_keys must be present even on
        # the quota_exhausted branch -- Step 2's own resumable-state persistence path is exactly
        # where a struggling candidate is first discovered, and Step 3's mid-dispatch "quota"
        # branch reads this same field shape.
        self.assertEqual(result["ladder_keys"], ["claude/opus-5"])

    def test_resolve_injection_derives_real_file_sizes_from_cwd(self):
        # CRITICAL finding: resolve-injection must derive files_touched_sizes itself (never rely
        # on a caller-supplied, always-empty default) so context-size filtering is actually live.
        candidates = [{"key": "claude/opus-5", "model": "opus", "cli": None,
                        "vendor": "anthropic", "task_affinity": None, "context_limit": None}]
        captured = {}

        def fake_build_dispatch_injection(task_markdown, cands, sizes, affinity, top_n, **kwargs):
            captured["sizes"] = sizes
            return {"mode": "native_claude", "model": "opus", "key": "claude/opus-5"}

        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "big.py"), "w") as f:
                f.write("x" * 4000)
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Modify: `big.py`\n")
            quota_path = os.path.join(tmp, "quota.json")
            superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path],
                assemble_candidates_fn=lambda cwd, env: (candidates, ["claude/opus-5"]),
                build_dispatch_injection_fn=fake_build_dispatch_injection,
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: {},
                stdout=io.StringIO())
        self.assertEqual(captured["sizes"], {"big.py": 4000})

    def test_resolve_injection_emits_controlled_quota_exhausted_when_every_candidate_already_excluded(self):
        # CRITICAL finding: a single-candidate ladder, already excluded by --exclude-keys-json
        # (e.g. a mid-dispatch "quota" failure caught in Step 3, re-running resolve-injection with
        # that SAME candidate excluded) previously reached build_dispatch_injection_fn with an
        # EMPTY candidates list, which raised its own "no candidate survived narrowing" ValueError
        # -- the WRONG exception (a real curation-gap signal, never "we already tried everything")
        # -- UNCAUGHT here, crashing the whole resolve-injection call instead of reporting a
        # controlled quota_exhausted result the SKILL.md's own branch-on-mode logic already
        # handles. --excluded-reasons-json carries this wave's own already-known reason forward.
        candidates = [{"key": "claude/opus-5", "model": "opus", "cli": None,
                        "vendor": "anthropic", "task_affinity": None, "context_limit": None}]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path, "--exclude-keys-json",
                 json.dumps(["claude/opus-5"]), "--excluded-reasons-json",
                 json.dumps({"claude/opus-5": "quota"})],
                assemble_candidates_fn=lambda cwd, env: (candidates, ["claude/opus-5"]),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: {},
                stdout=out)
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
        # folded into "quota_exhausted", which would wrongly imply a CronCreate wake could help.
        candidates = [{"key": "small-context/model", "model": "opus", "cli": None,
                        "vendor": "anthropic", "task_affinity": None, "context_limit": 10}]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "big.py"), "w") as f:
                f.write("x" * 4000)
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Modify: `big.py`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path],
                assemble_candidates_fn=lambda cwd, env: (candidates, ["small-context/model"]),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: {},
                stdout=out)
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

    def test_resolve_injection_merges_wave_excluded_reasons_with_this_calls_own_quota_exhaustion(self):
        # CRITICAL finding: mixed quota/auth case -- a caller re-resolving mid-wave (one candidate
        # already excluded for a KNOWN reason from an earlier call, another going quota-exhausted
        # fresh THIS call) must see BOTH reasons in the final output, never just this call's own
        # narrower remaining-ladder walk (which never even visits an already-excluded candidate).
        candidates = [
            {"key": "claude/opus-5", "model": "opus", "cli": None, "vendor": "anthropic",
             "task_affinity": None, "context_limit": None},
            {"key": "codex/terra", "model": "gpt-5.6-terra", "cli": "codex", "vendor": "openai",
             "task_affinity": None, "context_limit": None},
        ]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path, "--exclude-keys-json",
                 json.dumps(["codex/terra"]), "--excluded-reasons-json",
                 json.dumps({"codex/terra": "auth"})],
                assemble_candidates_fn=lambda cwd, env: (
                    candidates, ["claude/opus-5", "codex/terra"]),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: (
                    {"claude/opus-5": {"available": False, "detail": "usage limit reached"}}),
                stdout=out)
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
            {"key": "claude/opus-5", "model": "opus", "cli": None, "vendor": "anthropic",
             "task_affinity": None, "context_limit": None},
            {"key": "codex/terra", "model": "gpt-5.6-terra", "cli": "codex", "vendor": "openai",
             "task_affinity": None, "context_limit": None},
        ]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path, "--exclude-keys-json", json.dumps(["codex/terra"]),
                 "--excluded-reasons-json", json.dumps({"codex/terra": "quota"}),
                 "--escalation-excluded-keys-json", json.dumps(["claude/opus-5"])],
                assemble_candidates_fn=lambda cwd, env: (
                    candidates, ["claude/opus-5", "codex/terra"]),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: {},
                stdout=out)
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "quota_exhausted")
        # claude/opus-5 was excluded ONLY for capability-escalation reasons -- it must be absent
        # from both `tried` and `reasons` entirely, never defaulted to "no_usable_dispatch".
        self.assertEqual(result["tried"], ["codex/terra"])
        self.assertEqual(result["reasons"], {"codex/terra": "quota"})
        self.assertTrue(result["any_quota_recoverable"])


class TestCliDispatchTask(unittest.TestCase):
    def test_dispatch_task_refuses_a_native_claude_injection_with_a_clear_error(self):
        # HIGH finding: dispatch-task is the only real entry point that ever reaches
        # dispatch_superpowers_task -- a native_claude injection must fail here with a clear,
        # actionable error BEFORE any tooling-detection code runs (which indexes
        # injection["cli"], absent on a native_claude injection, and would otherwise die with a
        # bare, unexplained KeyError instead of a diagnosable message).
        injection = {"mode": "native_claude", "model": "opus", "key": "claude/opus-5"}
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
                    ["dispatch-task", "--injection-json", json.dumps(injection),
                     "--prompt-file", prompt_file, "--target-dir", tmp,
                     "--heartbeat-interval", "60", "--timeout", "900",
                     "--format-block-file", format_block_file, "--report-file", report_file],
                    detect_tool_availability_fn=lambda: {},
                    resolve_agents_tooling_path_fn=lambda: None,
                    ensure_codegraph_registered_fn=lambda cli: False,
                    stdout=io.StringIO())
        self.assertIn("external_cli", str(ctx.exception))
        self.assertIn("native_claude", str(ctx.exception))
        self.assertIn("Agent tool", str(ctx.exception))

    def test_preserves_implementer_authored_report_when_the_cli_writes_it_directly(self):
        # CRITICAL finding (recurrence -- a prior revision's fix attempt did not close every
        # path): the real superpowers implementer contract has the dispatched CLI write its OWN
        # detailed report directly to --report-file (it has write access to target_dir, being an
        # execute-mode dispatch) and return only a SHORT status separately (design spec's own
        # "writes detailed evidence to the report file and returns a short status separately").
        # dispatch-task must never overwrite that real, on-disk report with captured subprocess
        # stdout -- this is the normal case, and it must be left completely untouched.
        injection = {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                      "model": "gpt-5.6-terra", "effort": None, "service_tier": None}

        def fake_dispatch(injection_arg, prompt, target_dir, heartbeat_interval, timeout,
                           format_block=None, tool_availability=None, agents_tooling_path=None,
                           codegraph_registered=False):
            # Simulates the real dispatched CLI: per the prompt's report-file-path instruction, it
            # writes its OWN detailed report directly to disk and returns only a short status in
            # stdout -- exactly the contract this test guards.
            report_path = os.path.join(target_dir, "task-1-report.md")
            with open(report_path, "w") as f:
                f.write("## TDD Evidence\n\nfull detailed report with real test output...\n")
            return {"cli": "codex", "model": "gpt-5.6-terra", "command": "codex exec ...",
                     "returncode": 0, "stdout": "DONE", "stderr": "", "timed_out": False}

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
                ["dispatch-task", "--injection-json", json.dumps(injection),
                 "--prompt-file", prompt_file, "--target-dir", tmp,
                 "--heartbeat-interval", "60", "--timeout", "900",
                 "--format-block-file", format_block_file, "--report-file", report_file],
                dispatch_superpowers_task_fn=fake_dispatch,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                ensure_codegraph_registered_fn=lambda cli: False,
                stdout=out)
            self.assertEqual(rc, 0)
            with open(report_file) as f:
                content = f.read()
        # The implementer's own detailed, on-disk report survives verbatim -- the short "DONE"
        # status returned separately in stdout must NEVER have replaced it.
        self.assertEqual(content, "## TDD Evidence\n\nfull detailed report with real test "
                                   "output...\n")
        self.assertNotIn("DONE", content)
        result = json.loads(out.getvalue())
        self.assertEqual(result["returncode"], 0)

    def test_falls_back_to_labeled_stdout_only_when_the_cli_never_wrote_its_own_report(self):
        # Degraded case: the dispatched CLI did not follow the report-file-path instruction and
        # wrote nothing to disk -- something evidentiary must still survive, but clearly labeled
        # as a fallback, never silently indistinguishable from a genuine implementer report.
        injection = {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                      "model": "gpt-5.6-terra", "effort": None, "service_tier": None}

        def fake_dispatch(injection_arg, prompt, target_dir, heartbeat_interval, timeout,
                           format_block=None, tool_availability=None, agents_tooling_path=None,
                           codegraph_registered=False):
            return {"cli": "codex", "model": "gpt-5.6-terra", "command": "codex exec ...",
                     "returncode": 0, "stdout": "DONE\nonly stdout, no report file written",
                     "stderr": "", "timed_out": False}

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
                ["dispatch-task", "--injection-json", json.dumps(injection),
                 "--prompt-file", prompt_file, "--target-dir", tmp,
                 "--heartbeat-interval", "60", "--timeout", "900",
                 "--format-block-file", format_block_file, "--report-file", report_file],
                dispatch_superpowers_task_fn=fake_dispatch,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                ensure_codegraph_registered_fn=lambda cli: False,
                stdout=out)
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
        injection = {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                      "model": "gpt-5.6-terra", "effort": None, "service_tier": None}

        def fake_dispatch(injection_arg, prompt, target_dir, heartbeat_interval, timeout,
                           format_block=None, tool_availability=None, agents_tooling_path=None,
                           codegraph_registered=False):
            return {"cli": "codex", "model": "gpt-5.6-terra", "command": "codex exec ...",
                     "returncode": 0, "stdout": "fix round 1 report", "stderr": "",
                     "timed_out": False}

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
                ["dispatch-task", "--injection-json", json.dumps(injection),
                 "--prompt-file", prompt_file, "--target-dir", tmp,
                 "--heartbeat-interval", "60", "--timeout", "900",
                 "--format-block-file", format_block_file, "--report-file", report_file,
                 "--report-mode", "append"],
                dispatch_superpowers_task_fn=fake_dispatch,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                ensure_codegraph_registered_fn=lambda cli: False,
                stdout=io.StringIO())
            self.assertEqual(rc, 0)
            with open(report_file) as f:
                content = f.read()
        self.assertIn("original implementer report", content)
        self.assertIn("fix round 1 report", content)


class TestCliClassifyDispatchFailure(unittest.TestCase):
    def test_prints_the_classification_string(self):
        out = io.StringIO()
        result = {"returncode": 1, "stdout": "usage limit reached", "stderr": "",
                  "timed_out": False}
        rc = superpowers_cli.main(
            ["classify-dispatch-failure", "--dispatch-result-json", json.dumps(result)],
            stdout=out)
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "quota")


class TestCliResumeExclusions(unittest.TestCase):
    def test_prints_only_permanent_exclusions(self):
        # CRITICAL finding: the executable subcommand SKILL.md's resume/wake path calls -- proves
        # the reason-based split (quota dropped, everything else kept) is real and testable, not
        # just inline, untested bash arithmetic.
        out = io.StringIO()
        rc = superpowers_cli.main(
            ["resume-exclusions",
             "--tried-json", json.dumps(["claude/opus-5", "codex/terra"]),
             "--reasons-json", json.dumps({"claude/opus-5": "quota", "codex/terra": "auth"}),
             "--prior-excluded-keys-json", json.dumps([])],
            stdout=out)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.getvalue()), ["codex/terra"])


class TestCliWriteResumableState(unittest.TestCase):
    def test_writes_state_and_confirms(self):
        out = io.StringIO()
        captured = {}
        rc = superpowers_cli.main(
            ["write-resumable-state", "--path", "/x/state.json",
             "--state-json", json.dumps({"framework": "superpowers", "tried": []})],
            write_resumable_state_fn=lambda path, state: captured.update(path=path, state=state),
            stdout=out)
        self.assertEqual(rc, 0)
        self.assertEqual(captured["path"], "/x/state.json")
        self.assertEqual(json.loads(out.getvalue())["written"], True)


class TestDetectFrameworkSuperpowers(unittest.TestCase):
    def test_detects_superpowers_from_plans_directory(self):
        def isdir_fn(path):
            return path == os.path.join("/repo", "docs", "superpowers", "plans")

        result = router_detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=isdir_fn)
        self.assertEqual(result, "superpowers")

    def test_gsd_marker_wins_over_superpowers_marker_when_both_present_and_no_stronger_signal(self):
        result = router_detect_framework.detect_framework(
            "/repo",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: p == os.path.join("/repo", "docs", "superpowers", "plans"))
        self.assertEqual(result, "gsd")

    def test_returns_unknown_when_neither_marker_present(self):
        result = router_detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=lambda p: False)
        self.assertEqual(result, "unknown")

    def test_document_path_overrides_gsd_marker_when_both_markers_present(self):
        # CRITICAL finding (recurrence guard): a repo with BOTH markers present must still route a
        # user-supplied superpowers plan path to superpowers -- markers are supporting evidence
        # only, never the primary signal once an explicit document path is available.
        result = router_detect_framework.detect_framework(
            "/repo", document_path="/repo/docs/superpowers/plans/2026-08-29-widget.md",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: p == os.path.join("/repo", "docs", "superpowers", "plans"))
        self.assertEqual(result, "superpowers")

    def test_document_path_under_planning_resolves_gsd_even_without_markers(self):
        result = router_detect_framework.detect_framework(
            "/repo", document_path="/repo/.planning/phases/02-widget/02-01-PLAN.md",
            isfile_fn=lambda p: False, isdir_fn=lambda p: False)
        self.assertEqual(result, "gsd")

    def test_conversation_signal_wins_over_a_contradicting_document_path_and_markers(self):
        # CRITICAL finding: conversation signal is the strongest evidence -- the user just invoked
        # writing-plans in this very conversation, which outranks even an explicit document path
        # that happens to look GSD-shaped (e.g. copied under a .planning/ scratch directory).
        result = router_detect_framework.detect_framework(
            "/repo", document_path="/repo/.planning/scratch/notes.md",
            conversation_signal="superpowers",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: False)
        self.assertEqual(result, "superpowers")
