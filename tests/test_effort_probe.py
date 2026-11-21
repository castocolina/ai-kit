"""36-21: effort probing and render-toml effort refusal (SPEC R4)."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


def preview(state, reason=None):
    def show(spec):
        return [f"cross-ai: setting effort={spec.effort} {state}"
                + (f" reason={reason}" if reason else ""), f"cross-ai: model-id {spec.model}"]
    return show


APPLIED_PREVIEW = preview("applied")


def probe(fake, runtime: str | None = "opencode", model="fake/placeholder-model-1", effort="high",
          preview_fn=APPLIED_PREVIEW):
    return effort_probe.probe_effort(ResolvedReviewer("k", model, "", runtime, None, {}),
                                     effort, "2026-11-20", quota.ProbeSeams(runner_fn=fake),
                                     preview_fn=preview_fn)


class TestProbeEffort(unittest.TestCase):
    def test_accepted_labels_the_date(self):
        fake, calls = runner()
        def show(spec):
            self.assertTrue(os.path.isdir(spec.cwd))
            self.assertIsNone(spec.context)
            self.assertIsNone(spec.session_id)
            self.assertEqual(spec.model, "fake/placeholder-model-1")
            self.assertEqual(spec.effort, "high")
            return preview("applied")(spec)
        result = probe(fake, preview_fn=show)
        self.assertEqual(result["state"], "accepted")
        self.assertEqual(result["label"], "accepted by a call on 2026-11-20")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].model, "fake/placeholder-model-1")
        self.assertEqual(calls[0].effort, "high")

    def test_same_level_carried_is_not_certified(self):
        fake, calls = runner()
        result = probe(fake, "pi", "fake/placeholder-model-1:high",
                       preview_fn=preview("ignored", "id_carries"))
        self.assertEqual((result["state"], result["reason"]),
                         ("inconclusive", effort_probe.CARRIED_REASON))
        self.assertFalse(calls)

    def test_ignored_makes_no_call(self):
        fake, calls = runner()
        for runtime in ("claude", "copilot"):
            result = probe(fake, runtime, "placeholder-model-1",
                           preview_fn=preview("ignored", "no_form"))
            self.assertEqual(result["state"], "ignored")
            self.assertEqual(result["reason"],
                "ignored: the runner reports effort 'high' ignored (reason=no_form)")
        result = probe(fake, None, "", preview_fn=self.fail)
        self.assertEqual(result["reason"], lane_effort.NO_RUNTIME_IGNORED)
        self.assertFalse(calls)

    def test_no_preview_is_inconclusive(self):
        fake, calls = runner()
        result = probe(fake, preview_fn=lambda _: None)
        self.assertEqual((result["state"], result["reason"]),
                         ("inconclusive", effort_probe.NO_PREVIEW_REASON))
        self.assertFalse(calls)

    def test_no_setting_line_is_inconclusive(self):
        fake, calls = runner()
        result = probe(fake, preview_fn=lambda _: [])
        self.assertEqual((result["state"], result["reason"]),
                         ("inconclusive", effort_probe.NO_SETTING_REASON))
        self.assertFalse(calls)

    def test_rejected_keeps_a_clean_first_line(self):
        key = "sk-" + "A" * 24
        fake, _ = runner("real_error", lines=("unsupported effort level\x07 token " + key,
                                             "second line"))
        result = probe(fake)
        self.assertEqual(result["error"], "unsupported effort level token [redacted]")
        self.assertEqual((result["state"], result["reason"]), ("rejected", "real_error"))
        # A control character glued to the key: redacted before the control is stripped.
        fake, _ = runner("real_error", lines=("bad\x07" + key,))
        self.assertEqual(probe(fake)["error"], "bad[redacted]")

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
            self.assertIsNone(result["error"])

    def test_truncated_wrapper_detail_is_inconclusive(self):
        fake, _ = runner("real_error", lines=("cross-ai: " + "x" * 90,) * 4 + ("host error",))
        self.assertEqual(probe(fake)["state"], "inconclusive")

    def test_configuration_is_rejected(self):
        fake, _ = runner("configuration", lines=("host error",))
        self.assertEqual(probe(fake)["reason"], "configuration")
        self.assertEqual(probe(fake)["state"], "rejected")

    def test_no_answer_and_stops_are_inconclusive(self):
        fake, _ = runner(stdout="")
        result = probe(fake)
        self.assertEqual(result["reason"], effort_probe.NO_ANSWER_REASON)
        self.assertEqual((result["state"], result["label"]), ("inconclusive", None))
        for reason in ("quota", "auth", "timeout"):
            fake, _ = runner(reason)
            expected = (f"the call stopped on '{reason}', which does not show whether "
                        "the effort is accepted")
            result = probe(fake)
            self.assertEqual(result["reason"], expected)
            self.assertEqual((result["state"], result["error"], result["label"]),
                             ("inconclusive", None, None))

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
            effort_probe.probe_effort(resolved, "high", "2026-11-20", seams, preview("applied"))
            self.assertEqual(os.listdir(root), [])


def invoke(args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(args, **kwargs)
    return code, out.getvalue(), err.getvalue()


class TestCheckReviewerEffort(unittest.TestCase):
    def setUp(self):
        active = patch.object(effort_probe, "print_argv_lines", side_effect=preview("applied"))
        active.start()
        self.addCleanup(active.stop)

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
        payload = json.loads(out)
        self.assertEqual((payload["available"], payload["answered"]), (True, True))
        outcome = payload["effort_probe"]
        self.assertEqual(set(outcome), {"state", "level", "label", "error", "reason"})
        self.assertEqual((outcome["state"], outcome["level"]), ("accepted", "high"))
        self.assertRegex(outcome["label"], r"^accepted by a call on \d{4}-\d{2}-\d{2}$")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].model, "fake/placeholder-model-1")
        self.assertEqual(calls[0].effort, "high")

    def test_rejected_output_is_redacted(self):
        key = "sk-" + "A" * 24
        fake, _ = runner("real_error", lines=("unsupported " + key,))
        args = ["check-reviewer", "--runtime", "pi", "--model", "fake/placeholder-model-1",
                "--effort", "high"]
        _, out, _ = invoke(args, runner_fn=fake)
        self.assertNotIn(key, out)
        self.assertEqual(json.loads(out)["effort_probe"]["state"], "rejected")
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

    def test_listed_max_level_writes(self):
        self.catalog["fake/placeholder-model-1"]["runtimes"]["codex"]["efforts"].append("max")
        cache_write_json(cache_catalog_path(self.env), self.catalog)
        lane = {**self.lane, "effort": "max"}
        code, _, _ = self.run_render(lane)
        self.assertEqual(code, 0)

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
