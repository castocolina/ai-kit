"""36-21: effort probing and render-toml effort refusal (SPEC R4)."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, effort_probe, lane_effort, quota
from ai_kit_spec.cache import cache_write_json
from ai_kit_spec.commands import ResolvedReviewer
from ai_kit_spec.model_catalog import CATALOG_SCHEMA_VERSION, cache_catalog_path
from ai_kit_spec.runner_dispatch import RunnerResult


def runner(reason=None, stdout="Hello world!", lines=()):
    calls = []
    def fake(spec, prompt, seams):
        calls.append(spec)
        for line in lines:
            seams.print_fn(line)
        return RunnerResult(0 if reason is None else 1, stdout, None, reason, False, ["node"], "")
    return fake, calls


def probe(fake, runtime="opencode", model="fake/placeholder-model-1", effort="high"):
    return effort_probe.probe_effort(ResolvedReviewer("k", model, "", runtime, None, {}),
                                     effort, "2026-11-20", quota.ProbeSeams(runner_fn=fake))


class TestProbeEffort(unittest.TestCase):
    def test_accepted_labels_the_date(self):
        fake, calls = runner()
        result = probe(fake)
        self.assertEqual(result["state"], "accepted")
        self.assertEqual(result["label"], "accepted by a call on 2026-11-20")
        self.assertTrue(result["probe"]["available"])
        expected = lane_effort.effort_form("opencode", "fake/placeholder-model-1", "high")
        self.assertEqual(calls[0].model, expected.model)
        self.assertEqual(calls[0].mode, "review")
        self.assertEqual(len(calls), 1)

    def test_same_level_carried_is_not_certified(self):
        fake, calls = runner()
        result = probe(fake, "pi", "fake/placeholder-model-1:high")
        self.assertEqual(result["state"], "inconclusive")
        self.assertFalse(calls)

    def test_ignored_makes_no_call(self):
        fake, calls = runner()
        cases = [("claude", "placeholder-model-1", "high"),
                 ("copilot", "placeholder-model-1", "high"),
                 ("codex", "placeholder-model-1", "max"), (None, "", "high")]
        for runtime, model, level in cases:
            expected = lane_effort.effort_form(runtime, model, level).ignored
            self.assertEqual(probe(fake, runtime, model, level)["reason"], expected)
        self.assertFalse(calls)

    def test_rejected_keeps_a_clean_first_line(self):
        key = "sk-" + "A" * 24
        fake, _ = runner("real_error", lines=("unsupported effort level\x07 token " + key,
                                             "second line"))
        self.assertEqual(probe(fake)["error"], "unsupported effort level token [redacted]")

    def test_runner_lines_are_skipped(self):
        fake, _ = runner("real_error", lines=("cross-ai: start", "AIKIT-XAI status=error",
                                             "ai-kit-spec: status", "Error: unsupported"))
        self.assertEqual(probe(fake)["error"], "Error: unsupported")

    def test_wrapper_only_failure_is_inconclusive(self):
        for reason in ("real_error", "configuration"):
            fake, _ = runner(reason, lines=("cross-ai: preflight",))
            result = probe(fake)
            self.assertEqual(result["state"], "inconclusive")
            self.assertEqual(result["reason"], "runner: cross-ai: preflight")

    def test_truncated_wrapper_detail_is_inconclusive(self):
        fake, _ = runner("real_error", lines=("cross-ai: " + "x" * 90,) * 4 + ("host error",))
        self.assertEqual(probe(fake)["state"], "inconclusive")

    def test_configuration_is_rejected(self):
        fake, _ = runner("configuration", lines=("host error",))
        self.assertEqual(probe(fake)["reason"], "configuration")
        self.assertEqual(probe(fake)["state"], "rejected")

    def test_no_answer_and_stops_are_inconclusive(self):
        fake, _ = runner(stdout="")
        self.assertEqual(probe(fake)["reason"], effort_probe.NO_ANSWER_REASON)
        for reason in ("quota", "auth", "timeout"):
            fake, _ = runner(reason)
            expected = (f"the call stopped on '{reason}', which does not show whether "
                        "the effort is accepted")
            self.assertEqual(probe(fake)["reason"], expected)

    def test_no_model_makes_no_call(self):
        fake, calls = runner()
        self.assertEqual(probe(fake, "pi", "")["reason"], effort_probe.NO_MODEL_REASON)
        self.assertFalse(calls)

    def test_probe_writes_nothing(self):
        fake, _ = runner()
        with tempfile.TemporaryDirectory() as root:
            seams = quota.ProbeSeams(
                runner_fn=fake, env_fn=lambda: {"HOME": root, "XDG_CACHE_HOME": root + "/cache"})
            resolved = ResolvedReviewer("k", "fake/placeholder-model-1", "", "pi", None, {})
            effort_probe.probe_effort(resolved, "high", "2026-11-20", seams)
            self.assertEqual(os.listdir(root), [])


def invoke(args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(args, **kwargs)
    return code, out.getvalue(), err.getvalue()


class TestCheckReviewerEffort(unittest.TestCase):
    def test_effort_with_catalog_path_exits_2(self):
        self.check_guard(["--effort", "high"])

    def test_extra_json_effort_with_catalog_path_exits_2(self):
        self.check_guard(["--extra-json", '{"effort":"high"}'])

    def check_guard(self, flags):
        fake, calls = runner()
        with tempfile.TemporaryDirectory() as root:
            path = root + "/catalog.json"
            args = ["check-reviewer", "--runtime", "pi", "--catalog-path", path, *flags]
            code, _, err = invoke(args, runner_fn=fake)
            self.assertEqual(code, 2)
            self.assertIn("an effort probe cannot be combined", err)
            self.assertFalse(os.path.exists(path))
            self.assertFalse(calls)

    def test_effort_probe_in_output(self):
        fake, calls = runner()
        args = ["check-reviewer", "--runtime", "pi", "--model", "fake/placeholder-model-1",
                "--effort", "high"]
        code, out, _ = invoke(args, runner_fn=fake)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["effort_probe"]["state"], "accepted")
        self.assertEqual(calls[0].model, "fake/placeholder-model-1:high")

    def test_rejected_output_is_redacted(self):
        key = "sk-" + "A" * 24
        fake, _ = runner("real_error", lines=("unsupported " + key,))
        args = ["check-reviewer", "--runtime", "pi", "--model", "fake/placeholder-model-1",
                "--effort", "high"]
        _, out, _ = invoke(args, runner_fn=fake)
        self.assertNotIn(key, out)
        self.assertIn("[redacted]", json.loads(out)["effort_probe"]["error"])

    def test_without_effort_output_unchanged(self):
        fake, _ = runner()
        args = ["check-reviewer", "--runtime", "pi", "--model", "fake/placeholder-model-1"]
        _, out, _ = invoke(args, runner_fn=fake)
        self.assertNotIn("effort_probe", json.loads(out))


class TestRenderTomlEffort(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {"HOME": str(self.root / "home"), "XDG_CACHE_HOME": str(self.root / "cache")}
        self.lane = {"key": "k", "purpose": "review", "runtime": "codex",
                     "model": "placeholder-model-1", "effort": "low"}
        row = {"model_id": "placeholder-model-1", "efforts": ["high", "xhigh"]}
        self.catalog = {"_meta": {"schema_version": CATALOG_SCHEMA_VERSION},
                        "fake/placeholder-model-1": {"runtimes": {"codex": row}}}

    def run_render(self, lane, flags=()):
        path = self.root / "input.json"
        path.write_text(json.dumps({"lanes": [lane]}))
        return invoke(["render-toml", "--json-config", str(path), *flags], env_fn=lambda: self.env)

    def test_level_outside_listed_set_refused_nothing_written(self):
        cache_write_json(cache_catalog_path(self.env), self.catalog)
        target = self.root / "proj" / "config.toml"
        code, out, err = self.run_render(self.lane, ["--out", str(target)])
        self.assertEqual((code, out), (1, ""))
        self.assertIn(lane_effort.write_problems([self.lane], self.catalog, None)[0], err)
        self.assertFalse(target.exists())

    def test_runner_refused_level_refused(self):
        self.catalog["fake/placeholder-model-1"]["runtimes"]["codex"]["efforts"].append("max")
        cache_write_json(cache_catalog_path(self.env), self.catalog)
        lane = {**self.lane, "effort": "max"}
        code, _, err = self.run_render(lane)
        self.assertEqual(code, 1)
        self.assertIn(lane_effort.write_problems([lane], self.catalog, None)[0], err)

    def test_unknown_support_and_listed_level_write(self):
        lane = {**self.lane, "runtime": "opencode", "model": "fake/placeholder-model-1",
                "effort": "high"}
        self.assertEqual(self.run_render(lane)[0], 0)
        cache_write_json(cache_catalog_path(self.env), self.catalog)
        self.assertEqual(self.run_render({**self.lane, "effort": "xhigh"})[0], 0)

    def test_explicit_catalog_and_runtimes_files(self):
        catalog = self.root / "catalog.json"
        catalog.write_text(json.dumps(self.catalog))
        self.assertEqual(self.run_render(self.lane, ["--catalog-path", str(catalog)])[0], 1)
        snapshot = {"clis": {"pi": {"reasoning_modes": {
            "fake/placeholder-model-2": ["off", "low"]}}}}
        path = self.root / "runtimes.json"
        path.write_text(json.dumps(snapshot))
        lane = {**self.lane, "runtime": "pi", "model": "fake/placeholder-model-2", "effort": "high"}
        self.assertEqual(self.run_render(lane, ["--runtimes-json", str(path)])[0], 1)
        self.assertEqual(self.run_render(lane)[0], 0)

    def test_unreadable_evidence_file_exits_2(self):
        path = self.root / "bad.json"
        for flag in ("--catalog-path", "--runtimes-json"):
            flags = [flag, str(path), "--out", str(self.root / "out")]
            code, _, err = self.run_render(self.lane, flags)
            self.assertEqual(code, 2)
            self.assertIn(f"cannot read {path}", err)
            self.assertFalse((self.root / "out").exists())
            path.write_text("not json")
