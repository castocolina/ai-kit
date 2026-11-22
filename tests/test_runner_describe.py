"""37-17 / SPEC R9: the runner's --describe output (offline, no stdin read, sorted, locked to the source, golden)."""  # noqa: E501

import copy
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "skills" / "ai-kit-spec-review" / "references" / "cross-ai.mjs"
GOLDEN = REPO / "tests" / "fixtures" / "runner_describe_golden.json"
sys.path.insert(0, str(REPO))
from tests.cross_ai_selftest import _real_node_executable

NODE = _real_node_executable()
HELP_DIR = REPO / "tests" / "fixtures" / "cli_help"
FLAG_RX = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*(?![\w-])")
MODEL_FOR = {"pi": "fake/placeholder-model-1", "opencode": "fake/placeholder-model-1"}


def describe(extra_env=None, path=None) -> tuple[int, str, str]:
    assert NODE is not None
    with tempfile.TemporaryDirectory(prefix="xai-describe-") as home:
        env = {"PATH": path if path is not None else os.environ.get("PATH", ""),
               "HOME": home, "LANG": "C", "AI_KIT_REFUSE_REAL_HOME": "1", **(extra_env or {})}
        out_path, err_path = Path(home) / "out.txt", Path(home) / "err.txt"
        with out_path.open("wb") as out, err_path.open("wb") as err:
            proc = subprocess.Popen([NODE, str(TEMPLATE), "--describe"], cwd=home, env=env,
                                    stdin=subprocess.PIPE, stdout=out, stderr=err)
            # stdin stays open and unwritten: a runner that read stdin would block until the timeout
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired as exc:
                proc.kill()
                proc.wait()
                assert proc.stdin is not None
                proc.stdin.close()
                raise AssertionError("--describe read stdin or hung") from exc
            assert proc.stdin is not None
            proc.stdin.close()
        return (proc.returncode, out_path.read_text(encoding="utf-8"),
                err_path.read_text(encoding="utf-8"))


def source_list(name) -> list[str]:
    text = TEMPLATE.read_text(encoding="utf-8")
    match = re.search(rf"^const {name} = (?:Object\.freeze\()?\[(.*?)\]", text, re.M | re.S)
    assert match is not None
    return re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))


BLOCKING = {"no_commit": "partial", "task_uncovered": "partial", "admits_skipped": "partial",
            "forbidden_path": "contract_violation"}


def status_table() -> dict[str, int]:
    text = TEMPLATE.read_text(encoding="utf-8")
    match = re.search(r"^const STATUS_TABLE = \{(.*?)^\};", text, re.M | re.S)
    assert match is not None
    return {name: int(code) for name, code in
            re.findall(r"^\s+([a-z_]+): \{ exit: (\d+) \}", match.group(1), re.M)}


def key_problems(obj, statuses, codes, flags) -> list[str]:
    problems = []
    if obj["statuses"] != statuses:
        problems.append("statuses differ")
    if [item["code"] for item in obj["findings"]] != codes:
        problems.append("finding codes differ")
    if any(item["result"] != BLOCKING.get(item["code"], "info") for item in obj["findings"]):
        problems.append("finding results differ")
    if obj["supervision_flags"] != flags or flags != sorted(flags):
        problems.append("flags differ")
    return problems


def unsorted_objects(text) -> list[list[str]]:
    result = []

    def hook(pairs):
        keys = [key for key, _ in pairs]
        if keys != sorted(keys) or any(not key.isascii() for key in keys):
            result.append(keys)
        return dict(pairs)

    json.loads(text, object_pairs_hook=hook)
    return result


def label_found(value) -> bool:
    if isinstance(value, dict):
        label = value.get("label")
        if isinstance(label, str) and label:
            return True
        if isinstance(label, dict) and isinstance(label.get("source"), str) and label["source"]:
            return True
        return any(label_found(item) for item in value.values())
    return isinstance(value, list) and any(label_found(item) for item in value)


def formula_argvs(obj) -> dict:
    assert NODE is not None
    result = {}
    with tempfile.TemporaryDirectory(prefix="xai-formulas-") as home:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": home, "LANG": "C",
               "AI_KIT_REFUSE_REAL_HOME": "1"}
        for rid, row in obj["runtimes"].items():
            facts = {"exec": None, "review": None, "resume": None, "listing": row["listing"]}
            for mode in ("exec", "review"):
                if not row["formulas"][mode]:
                    continue
                proc = subprocess.run([NODE, str(TEMPLATE), "--runtime", rid, "--mode", mode,
                                       "--model", MODEL_FOR.get(rid, "placeholder-model-1"),
                                       "--print-argv"], cwd=home, env=env, capture_output=True,
                                      text=True, check=True)
                line = next(line for line in proc.stdout.splitlines()
                            if line.startswith(rid + "\t"))
                facts[mode] = json.loads(line.split("\t", 2)[2])
                prefix = f"cross-ai: rung1 {rid} argv="
                resume = next((line for line in proc.stderr.splitlines()
                               if line.startswith(prefix)), None)
                if resume and facts["resume"] is None:
                    facts["resume"] = json.loads(resume[len(prefix):])
            result[rid] = facts
    return result


def expected_label(rid, fact, argv) -> dict:
    if argv is None:
        return {"state": "unknown", "source": "no listing in the runner" if fact == "listing"
                else "no formula in the runner"}
    folder = HELP_DIR / rid
    meta = folder / "meta.json"
    if not meta.exists():
        return {"state": "unverified", "source": "unverified: no recorded help"}
    flags = {arg.split("=")[0] for arg in argv if re.match(r"^--[a-z][a-z0-9-]*", arg)}
    recorded = set()
    for path in folder.glob("*.txt"):
        recorded.update(FLAG_RX.findall(path.read_text(encoding="utf-8")))
    missing = sorted(flags - recorded)
    if missing:
        return {"state": "unverified",
                "source": f"unverified: {', '.join(missing)} not in the recorded help"}
    metadata = json.loads(meta.read_text(encoding="utf-8"))
    source = (f"verified: {rid} {metadata['version']} help recorded {metadata['recorded']} "
              f"(tests/fixtures/cli_help/{rid}/)")
    return {"state": "verified", "source": source}


def label_problems(obj, argvs) -> list[str]:
    problems = []
    for rid, row in obj["runtimes"].items():
        for fact in ("exec", "review", "resume", "listing"):
            got = row["listing_label"] if fact == "listing" else row["formula_labels"].get(fact)
            expected = expected_label(rid, fact, argvs[rid][fact])
            if got != expected:
                problems.append(f"{rid} {fact}: expected {expected!r}, got {got!r}")
    return problems


class TestRunnerDescribe(unittest.TestCase):
    def setUp(self):
        if NODE is None:
            self.skipTest("node not on PATH")

    def test_one_json_object_and_one_status_line(self):
        code, stdout, stderr = describe()
        self.assertEqual(code, 0)
        obj = json.loads(stdout)
        self.assertIsInstance(obj, dict)
        self.assertEqual(list(obj), sorted(obj))
        lines = [line for line in stderr.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("AIKIT-XAI status=ok "))
        self.assertIn(" exit=0 ", lines[0])

    def test_reads_no_stdin(self):
        """The helper keeps stdin open and unwritten until the runner exits."""
        self.assertEqual(describe()[0], 0)

    def test_lists_equal_the_runner_source(self):
        obj = json.loads(describe()[1])
        for key, name in (("settings", "SETTING_NAMES"), ("reasons", "SETTING_REASONS"),
                          ("states", "SETTING_STATES")):
            with self.subTest(key=key):
                self.assertEqual(obj[key], source_list(name))

    def test_closed_lists_hold_the_host_names(self):
        obj = json.loads(describe()[1])
        self.assertIn("host", obj["settings"])
        for reason in ("no_herdr", "host_failed", "bad_value"):
            self.assertIn(reason, obj["reasons"])
        self.assertEqual(obj["states"], ["applied", "ignored", "unknown"])
        self.assertEqual(obj["schema"], 1)
        match = re.search(r"template=(\d+)", TEMPLATE.read_text(encoding="utf-8").splitlines()[1])
        assert match is not None
        self.assertEqual(obj["template_version"], int(match.group(1)))

    def test_no_classes_key(self):
        # 0b-10: 38.1 adds classes; an empty list here would claim there are none
        self.assertNotIn("classes", json.loads(describe()[1]))

    def test_new_keys_beside_the_existing_ones(self):
        obj = json.loads(describe()[1])
        self.assertEqual(set(obj), {"findings", "host", "reasons", "runtimes", "schema", "settings",
                                    "states", "statuses", "supervision_flags", "template_version"})
        self.assertEqual(obj["schema"], 1)
        self.assertEqual(obj["supervision_flags"],
                         ["--baseline", "--forbid", "--idle-timeout", "--plan-id", "--sweep"])
        self.assertIn("--sweep", obj["supervision_flags"])
        self.assertEqual(obj["statuses"]["locked"], 75)
        self.assertEqual(obj["statuses"]["partial"], 1)
        self.assertEqual([item["code"] for item in obj["findings"]][:3],
                         ["no_commit", "task_uncovered", "admits_skipped"])

    def test_statuses_equal_the_status_table(self):
        self.assertEqual(json.loads(describe()[1])["statuses"], status_table())

    def test_findings_follow_the_closed_list(self):
        findings = json.loads(describe()[1])["findings"]
        self.assertEqual([item["code"] for item in findings], source_list("FINDING_CODES"))
        for item in findings:
            self.assertIn(item["result"], {"partial", "contract_violation", "info"})
            self.assertEqual(item["result"], BLOCKING.get(item["code"], "info"))

    def test_supervision_flags_are_parsed_flags(self):
        flags = json.loads(describe()[1])["supervision_flags"]
        self.assertEqual(flags, source_list("SUPERVISION_FLAGS"))
        self.assertEqual(flags, sorted(flags))
        values = {"--baseline": ["0000000"], "--forbid": ["docs/"],
                  "--idle-timeout": ["0"], "--plan-id": ["12-03"], "--sweep": []}
        assert NODE is not None
        with tempfile.TemporaryDirectory(prefix="xai-flags-") as home:
            env = {"PATH": os.environ.get("PATH", ""), "HOME": home, "LANG": "C",
                   "AI_KIT_REFUSE_REAL_HOME": "1"}
            for flag in [*flags, "--made-up-flag"]:
                with self.subTest(flag=flag):
                    proc = subprocess.run([NODE, str(TEMPLATE), "--print-argv", "--runtime", "pi",
                                           "--model", "fake/placeholder-model-1", flag,
                                           *values.get(flag, [])], cwd=home, env=env,
                                          capture_output=True, text=True, timeout=30, check=False)
                    message = f"unknown argument: {flag}"
                    if flag == "--made-up-flag":
                        self.assertIn(message, proc.stderr)
                    else:
                        self.assertNotIn(message, proc.stderr)

    def test_source_lock_catches_a_drift(self):
        obj = json.loads(describe()[1])
        sources = (status_table(), source_list("FINDING_CODES"), source_list("SUPERVISION_FLAGS"))
        self.assertEqual(key_problems(obj, *sources), [])
        variants = [copy.deepcopy(obj) for _ in range(3)]
        variants[0]["statuses"]["made_up"] = 1
        variants[1]["findings"][0], variants[1]["findings"][1] = (variants[1]["findings"][1],
                                                                    variants[1]["findings"][0])
        variants[2]["supervision_flags"].pop()
        for variant in variants:
            self.assertTrue(key_problems(variant, *sources))

    def test_python_reader_accepts_the_new_keys(self):
        from ai_kit_spec.runner_facts import read_runner_describe

        obj = read_runner_describe(NODE, str(TEMPLATE))["describe"]
        self.assertIsInstance(obj, dict)
        assert isinstance(obj, dict)
        self.assertTrue({"runtimes", "statuses", "findings", "supervision_flags"} <= obj.keys())
        self.assertIsInstance(obj["runtimes"]["pi"]["formulas"]["exec"], bool)

    def test_runtimes_and_keys_sorted(self):
        out = describe()[1]
        obj = json.loads(out, object_pairs_hook=dict)
        self.assertEqual(list(obj["runtimes"]), sorted(obj["runtimes"]))
        self.assertEqual(unsorted_objects(out), [])

    def test_rows_carry_formulas_and_labels(self):
        for rid, row in json.loads(describe()[1])["runtimes"].items():
            with self.subTest(runtime=rid):
                self.assertEqual(set(row["formulas"]), {"exec", "review", "resume"})
                self.assertTrue(all(isinstance(v, bool) for v in row["formulas"].values()))
                self.assertTrue(row["formulas"]["review"])
                self.assertTrue(row["listing"] is None or
                                all(isinstance(x, str) for x in row["listing"]))
                self.assertTrue(isinstance(row["source"], str) and row["source"])
                for key, value in row.items():
                    if key not in {"formulas", "formula_labels", "listing", "listing_label",
                                   "source"}:
                        self.assertTrue(value is None or
                                        (isinstance(value, dict) and label_found(value)), key)

    def test_host_available_reads_env_and_path_only(self):
        with tempfile.TemporaryDirectory(prefix="xai-herdr-") as tmp:
            fake, empty = Path(tmp) / "fake", Path(tmp) / "empty"
            fake.mkdir()
            empty.mkdir()
            marker = str(Path(tmp) / "herdr-called")
            script = fake / "herdr"
            script.write_text(f"#!/bin/sh\n: > {shlex.quote(marker)}\n", encoding="utf-8")
            script.chmod(0o755)
            for extra, path, expected in (({}, fake, False), ({"HERDR_ENV": "1"}, empty, False),
                                          ({"HERDR_ENV": "1"}, fake, True),
                                          ({"HERDR_ENV": "0"}, fake, False)):
                available = json.loads(describe(extra, str(path))[1])["host"]["available"]
                self.assertEqual(available, expected)
            self.assertFalse(os.path.exists(marker))

    def test_formula_and_listing_labels_follow_recorded_help(self):
        obj = json.loads(describe()[1])
        self.assertEqual([], label_problems(obj, formula_argvs(obj)))

    def test_label_check_is_not_vacuous(self):
        obj = json.loads(describe()[1])
        argvs = formula_argvs(obj)
        broken = copy.deepcopy(obj)
        rid = next(iter(broken["runtimes"]))
        del broken["runtimes"][rid]["formula_labels"]["review"]
        self.assertTrue(label_problems(broken, argvs))
        broken = copy.deepcopy(obj)
        label = broken["runtimes"][rid]["formula_labels"]["review"]
        label.update(state="unverified", source="unverified: synthetic missing flag")
        self.assertTrue(label_problems(broken, argvs))
        label.update(state="verified", source="wrong version")
        self.assertTrue(label_problems(broken, argvs))

    def test_matches_golden(self):
        out = describe()[1]
        self.assertEqual(GOLDEN.read_text(encoding="utf-8"), out,
                         "regenerate with: python3 tests/test_runner_describe.py --write-golden")


# Regenerate after a row, form or list change: python3 tests/test_runner_describe.py --write-golden
if __name__ == "__main__":
    if sys.argv[1:] == ["--write-golden"]:
        code, out, err = describe()
        if code:
            sys.exit(err)
        GOLDEN.write_text(out, encoding="utf-8")
        sys.exit(0)
    unittest.main()
