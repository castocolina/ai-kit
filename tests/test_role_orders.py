"""Per-role orders (36 SPEC R3, D-04): role_orders, cfg_combine's orders and readers."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-execute-superpowers"))

from ai_kit_spec import cli, config_io, quota, role_orders
from ai_kit_spec.runner_dispatch import RunnerResult
from ai_kit_spec_superpowers import dispatch_injection


class _FileCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cwd = os.path.join(tmp.name, "project")
        os.makedirs(self.cwd)
        self.env = {"HOME": os.path.join(tmp.name, "home"),
                    "XDG_CONFIG_HOME": os.path.join(tmp.name, "xdg"),
                    "XDG_CACHE_HOME": os.path.join(tmp.name, "cache")}
        self.warnings = []

    def write_user(self, text):
        self.write(config_io.cfg_global_path(self.env), text)

    def write_project(self, text):
        self.write(config_io.cfg_local_path(self.cwd), text)

    @staticmethod
    def write(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def resolve(self):
        return config_io.cfg_resolve(self.cwd, self.env, warn_fn=self.warnings.append)


USER = '''[[lanes.review]]
key = "r1"
runtime = "codex"
model = "placeholder-model-1"
vendor = "v1"
[[lanes.execute]]
key = "e1"
runtime = "codex"
model = "placeholder-model-2"
vendor = "v2"
'''
TABLES = '''[lanes.policy.review]
ladder = ["r1"]
[lanes.policy.execute]
ladder = ["e1"]
'''


class TestRoleOrdersTracer(_FileCase):
    def test_role_tables_give_each_role_its_order(self):
        policy = {"review": {"ladder": ["r2", "r1"]}, "execute": {"ladder": ["e1"]}}
        lanes = {"review": [{"key": "r1"}, {"key": "r2"}], "execute": [{"key": "e1"}]}
        self.assertEqual(role_orders.role_orders(policy, lanes, self.warnings.append),
                         {"review": ["r2", "r1"], "execute": ["e1"]})
        self.assertEqual(self.warnings, [])

    def test_cfg_resolve_adds_orders_and_keeps_the_raw_policy(self):
        self.write_user(USER + TABLES)
        resolved = self.resolve()
        self.assertEqual(resolved["orders"], {"review": ["r1"], "execute": ["e1"]})
        self.assertEqual(resolved["policy"]["review"], {"ladder": ["r1"]})
        self.assertEqual(resolved["policy"]["mode"], "single")
        self.assertEqual(self.warnings, [])

    def test_review_resolution_walks_the_review_order(self):
        config = {"policy": {"mode": "single", "ladder": ["e1", "r1"]},
                  "orders": {"review": ["r1"], "execute": ["e1"]},
                  "reviewers": [{"key": "e1", "model": "placeholder-model-1", "vendor": "v1"},
                                {"key": "r1", "model": "placeholder-model-2", "vendor": "v2"}]}
        self.assertEqual([r.key for r in quota.resolve_reviewers(config, {}, "", True)], ["r1"])


class TestRoleOrdersRules(_FileCase):
    def check_orders(self, policy, lanes, expected, warnings):
        self.assertEqual(role_orders.role_orders(policy, lanes, self.warnings.append), expected)
        self.assertEqual(self.warnings, warnings)

    def test_legacy_ladder_splits_by_role_with_one_note(self):
        lanes = {"review": [{"key": "r1"}, {"key": "r2"}], "execute": [{"key": "e1"}]}
        self.check_orders({"ladder": ["r1", "e1", "r2"]}, lanes,
                          {"review": ["r1", "r2"], "execute": ["e1"]}, [note(2, 1)])

    def test_table_key_naming_no_role_lane_is_dropped_with_a_warning(self):
        policy = {"review": {"ladder": ["r1", "gone", "e1"]}, "execute": {"ladder": ["e1"]}}
        lanes = {"review": [{"key": "r1"}], "execute": [{"key": "e1"}]}
        self.check_orders(policy, lanes, {"review": ["r1"], "execute": ["e1"]},
                          ["ai-kit-spec: [lanes.policy.review] ladder names no review lane: "
                           "['gone', 'e1']; dropped"])

    def test_legacy_key_naming_no_lane_is_dropped_with_a_warning(self):
        self.check_orders({"ladder": ["r1", "gone"]}, {"review": [{"key": "r1"}]},
                          {"review": ["r1"], "execute": []},
                          [note(1, 0), "ai-kit-spec: [lanes.policy] ladder names no lane: "
                           "['gone']; dropped"])

    def test_duplicate_key_keeps_its_first_place(self):
        policy = {"review": {"ladder": ["r2", "r1", "r2"]}, "execute": {"ladder": []}}
        self.check_orders(policy, {"review": [{"key": "r1"}, {"key": "r2"}]},
                          {"review": ["r2", "r1"], "execute": []}, [])

    def test_malformed_role_table_is_ignored_with_one_warning(self):
        policy = {"review": "r1", "execute": {"ladder": "e1"}, "ladder": ["r1", "e1"]}
        lanes = {"review": [{"key": "r1"}], "execute": [{"key": "e1"}]}
        self.check_orders(policy, lanes, {"review": ["r1"], "execute": ["e1"]},
                          [f"ai-kit-spec: [lanes.policy.{r}] must be a table holding a ladder "
                           "list; ignored" for r in ("review", "execute")] + [note(1, 1)])

    def test_flat_ladder_beside_both_role_tables_is_ignored_with_a_warning(self):
        policy = {"ladder": ["x"], "review": {"ladder": ["r1"]},
                  "execute": {"ladder": ["e1"]}}
        lanes = {"review": [{"key": "r1"}], "execute": [{"key": "e1"}]}
        self.check_orders(policy, lanes, {"review": ["r1"], "execute": ["e1"]},
                          ["ai-kit-spec: the shared [lanes.policy] ladder is ignored: "
                           "[lanes.policy.review] and [lanes.policy.execute] set each role's "
                           "order"])

    def test_key_in_both_roles_has_an_entry_in_each_order(self):
        lanes = {"review": [{"key": "k", "model": "placeholder-model-1"}],
                 "execute": [{"key": "k", "model": "placeholder-model-2"}]}
        policy = {role: {"ladder": ["k"]} for role in lanes}
        orders = role_orders.role_orders(policy, lanes, self.warnings.append)
        self.assertEqual(orders, {"review": ["k"], "execute": ["k"]})
        config = {**lanes, "orders": orders}
        self.assertEqual(role_orders.ordered_lanes(config, "review")[0]["model"],
                         "placeholder-model-1")
        self.assertEqual(role_orders.ordered_lanes(config, "execute")[0]["model"],
                         "placeholder-model-2")
        self.assertEqual(self.warnings, [])

    def test_role_order_falls_back_to_the_policy_ladder(self):
        self.assertEqual(role_orders.role_order({"policy": {"ladder": ["a"]}}, "review"), ["a"])
        self.assertEqual(role_orders.role_order({"orders": {"review": ["b"], "execute": []},
                                                 "policy": {"ladder": ["a"]}}, "review"), ["b"])
        self.assertEqual(role_orders.role_order({}, "execute"), [])

    def test_split_policy_separates_flat_keys_from_role_tables(self):
        policy = {"mode": "double", "timeout_tiers": [600], "ladder": ["x"],
                  "review": {"ladder": ["r1"]}, "execute": "bad"}
        self.assertEqual(role_orders.split_policy(policy),
                         ({"mode": "double", "timeout_tiers": [600], "ladder": ["x"]},
                          {"review": {"ladder": ["r1"]}}))

    def test_inline_table_and_array_entries_are_dropped_without_hashing(self):
        policy = {"review": {"ladder": ["r1", {"x": 1}, ["y"], {"x": 1}]},
                  "execute": {"ladder": []}, "ladder": ["r1", ["z"]]}
        lanes = {"review": [{"key": "r1"}]}
        orders = role_orders.role_orders(policy, lanes, self.warnings.append)
        self.assertEqual(orders["review"], ["r1"])
        self.assertEqual(self.warnings[0], "ai-kit-spec: [lanes.policy.review] ladder names no "
                         "review lane: [{'x': 1}, ['y']]; dropped")
        self.warnings.clear()
        orders = role_orders.role_orders({"ladder": ["r1", {"x": 1}]}, lanes,
                                          self.warnings.append)
        self.assertEqual(orders["review"], ["r1"])
        self.assertIn("ai-kit-spec: [lanes.policy] ladder names no lane: [{'x': 1}]; dropped",
                      self.warnings)


def note(review, execute):
    return ("ai-kit-spec: the shared [lanes.policy] ladder loads as one order per role "
            f"(review: {review} keys, execute: {execute} keys); the next write replaces it with "
            "[lanes.policy.review] and [lanes.policy.execute]")


class TestRoleOrdersLayers(_FileCase):
    def test_project_role_table_replaces_the_user_table_per_role(self):
        self.write_user(USER + TABLES)
        self.write_project('''[[lanes.review]]
key = "p1"
runtime = "codex"
model = "placeholder-model-3"
[lanes.policy.review]
ladder = ["p1"]
''')
        resolved = self.resolve()
        self.assertEqual(resolved["orders"], {"review": ["p1"], "execute": ["e1"]})
        self.assertEqual([r["key"] for r in resolved["review"]], ["r1", "p1"])
        self.assertEqual(self.warnings, [])

    def test_legacy_ladder_review_run_skips_execute_lanes(self):
        self.write_user(USER + '[lanes.policy]\nladder = ["e1", "r1"]\n')
        resolved = self.resolve()
        picked = quota.resolve_reviewers(resolved, {}, "", True, warn_fn=lambda _m: None)
        self.assertEqual([r.key for r in picked], ["r1"])
        self.assertEqual(self.warnings, [note(1, 1)])

    def test_shared_key_across_roles_and_layers_reaches_each_role_lane(self):
        self.write_user('''[[lanes.review]]
key = "k"
runtime = "codex"
model = "placeholder-model-1"
vendor = "v1"
[lanes.policy.review]
ladder = ["k"]
''')
        self.write_project('''[[lanes.execute]]
key = "k"
runtime = "codex"
model = "placeholder-model-2"
[lanes.policy.execute]
ladder = ["k"]
''')
        picked = quota.resolve_reviewers(self.resolve(), {}, "", True, warn_fn=lambda _m: None)
        self.assertEqual([(r.key, r.model) for r in picked], [("k", "placeholder-model-1")])
        candidates, top = dispatch_injection.assemble_candidates(self.cwd, self.env)
        self.assertEqual([(r["key"], r["model"]) for r in candidates],
                         [("k", "placeholder-model-2")])
        self.assertEqual(top, ["k"])


class TestRoleOrdersExecuteAdapter(unittest.TestCase):
    def test_execute_candidates_and_order_come_from_the_execute_role(self):
        review = {"key": "r1", "model": "placeholder-model-1"}
        execute = {"key": "e1", "model": "placeholder-model-2"}
        resolved = {"policy": {"ladder": ["r1", "e1"]},
                    "orders": {"review": ["r1"], "execute": ["e1"]},
                    "reviewers": [review, execute], "execute": [execute]}
        candidates, top = dispatch_injection.assemble_candidates(
            "/repo", {}, cfg_resolve_fn=lambda cwd, env: resolved)
        self.assertEqual([r["key"] for r in candidates], ["e1"])
        self.assertEqual(top, ["e1"])


PROBE_ROSTER = '''[[lanes.review]]
key = "r1"
model = "placeholder-model-1"
command = "placeholder-cli-1 {model}"
[[lanes.review]]
key = "both1"
model = "placeholder-model-2"
command = "placeholder-cli-1 {model}"
[[lanes.review]]
key = "same1"
model = "placeholder-model-5"
command = "placeholder-cli-1 {model}"
[[lanes.execute]]
key = "e1"
model = "placeholder-model-3"
command = "placeholder-cli-1 --exec {model}"
[[lanes.execute]]
key = "both1"
model = "placeholder-model-4"
command = "placeholder-cli-1 --exec {model}"
[[lanes.execute]]
key = "same1"
model = "placeholder-model-5"
command = "placeholder-cli-1 {model}"
[lanes.policy.review]
ladder = ["r1", "both1", "same1"]
[lanes.policy.execute]
ladder = ["both1", "e1", "same1"]
'''


class TestProbeQuotaRole(_FileCase):
    def probe(self, *extra) -> tuple[list, str]:
        recorded = []

        def rec(spec, prompt, seams):
            recorded.append((spec.key, list(spec.argv)))
            return RunnerResult(0, "", {"status": "ok"}, None, False, ["node", "runner"], "")

        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = cli.main(["probe-quota", "--cwd", self.cwd, "--quota-path",
                             os.path.join(self.cwd, "quota.json"), "--no-save-runtimes", *extra],
                            runner_fn=rec, custom_fn=rec, env_fn=lambda: dict(self.env),
                            which_fn=lambda _name, **_kwargs: None, run_fn=lambda *_a, **_k: None)
        self.assertEqual(code, 0)
        return recorded, err.getvalue()

    def test_default_role_probes_the_review_lanes(self):
        self.write_user(PROBE_ROSTER)
        calls, err = self.probe()
        self.assertEqual(calls, [("r1", ["placeholder-cli-1", "placeholder-model-1"]),
                                 ("both1", ["placeholder-cli-1", "placeholder-model-2"]),
                                 ("same1", ["placeholder-cli-1", "placeholder-model-5"])])
        self.assertNotIn("probe-quota: 'both1'", err)

    def test_execute_role_probes_the_execute_lanes(self):
        self.write_user(PROBE_ROSTER)
        calls, err = self.probe("--role", "execute")
        self.assertEqual(calls, [("both1", ["placeholder-cli-1", "--exec", "placeholder-model-4"]),
                                 ("e1", ["placeholder-cli-1", "--exec", "placeholder-model-3"]),
                                 ("same1", ["placeholder-cli-1", "placeholder-model-5"])])
        self.assertNotIn("names different lanes", err)

    def test_execute_role_also_probes_unlisted_execute_lanes(self):
        self.write_user('''[[lanes.review]]
key = "r"
model = "placeholder-model-1"
command = "placeholder-cli-1 {model}"
[[lanes.execute]]
key = "unlisted"
model = "placeholder-model-2"
command = "placeholder-cli-1 {model}"
[[lanes.execute]]
key = "listed"
model = "placeholder-model-3"
command = "placeholder-cli-1 {model}"
[lanes.policy.review]
ladder = ["r"]
[lanes.policy.execute]
ladder = ["listed"]
''')
        calls, _ = self.probe("--role", "execute")
        self.assertEqual([key for key, _ in calls], ["listed", "unlisted"])
        calls, _ = self.probe("--role", "review")
        self.assertEqual([key for key, _ in calls], ["r"])

    def test_both_probes_review_then_execute_once_per_key_and_warns(self):
        self.write_user(PROBE_ROSTER)
        calls, err = self.probe("--role", "both")
        self.assertEqual(calls, [("r1", ["placeholder-cli-1", "placeholder-model-1"]),
                                 ("both1", ["placeholder-cli-1", "placeholder-model-2"]),
                                 ("same1", ["placeholder-cli-1", "placeholder-model-5"]),
                                 ("e1", ["placeholder-cli-1", "--exec", "placeholder-model-3"])])
        self.assertEqual([line for line in err.splitlines() if "names different lanes" in line],
                         ["ai-kit-spec: key 'both1' names different lanes in the review and "
                          "execute roles; the execute lane is not probed (rename one of them)"])

    def test_usage_limited_lane_is_probed_like_any_other(self):
        self.write_user(PROBE_ROSTER.replace('key = "e1"',
                                             'key = "e1"\nusage_limited = true'))
        calls, _ = self.probe("--role", "execute")
        self.assertIn(("e1", ["placeholder-cli-1", "--exec", "placeholder-model-3"]), calls)

    def snippet(self):
        path = os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-config", "references",
                            "check-only.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        opener = 'python3 -c "\n'
        start = text.rindex(opener, 0, text.index("probe_keys")) + len(opener)
        body = text[start:text.index('\n"\n', start)]
        review_dir = os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review")
        return body.replace('$(dirname "$TOOLS_PY")', review_dir).replace("$(pwd)", self.cwd)

    def test_check_only_snippet_lists_model_and_command_for_both_roles(self):
        self.write_user(PROBE_ROSTER)
        deps = cli.CliDeps(which_fn=lambda *_a, **_k: None,
                           run_fn=lambda *_a, **_k: subprocess.CompletedProcess([], 0, "", ""),
                           env_fn=lambda: dict(self.env))
        out, err = io.StringIO(), io.StringIO()
        with (mock.patch.object(cli, "CliDeps", lambda: deps), redirect_stdout(out),
              redirect_stderr(err)):
            exec(compile(self.snippet(), "check-only-snippet", "exec"), {})
        rows = json.loads(out.getvalue())
        self.assertEqual(rows, [{"key": key, "runtime": None, "model": model,
                                 "command": command, "custom": True}
                                for key, model, command in [
                                    ("r1", "placeholder-model-1", "placeholder-cli-1 {model}"),
                                    ("both1", "placeholder-model-2", "placeholder-cli-1 {model}"),
                                    ("same1", "placeholder-model-5", "placeholder-cli-1 {model}"),
                                    ("e1", "placeholder-model-3",
                                     "placeholder-cli-1 --exec {model}"),
                                ]])
        self.assertIn("key 'both1' names different lanes", err.getvalue())

    def test_check_only_text_names_both_roles_and_the_probe_spend(self):
        path = os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-config", "references",
                            "check-only.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn('probe-quota --cwd "$(pwd)" --role both', text)
        self.assertIn("List every such entry with the model and command", text)
        self.assertIn("A key that names different lanes", text)
        self.assertIn("every `--check-only` run spends one probe per probed lane", text)
        self.assertNotIn("reachable from `policy.ladder`", text)


if __name__ == "__main__":
    unittest.main()
