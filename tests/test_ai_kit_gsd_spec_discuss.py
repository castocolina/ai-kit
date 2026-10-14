# tests/test_ai_kit_gsd_spec_discuss.py
"""Tests for skills/ai-kit-gsd-spec-discuss/scripts (decide.py, phase_range.py, edge_floor.py).

Two layers: injected-seam unit tests, and subprocess tests that run the real CLI against a fake
jev client in a tmpdir plus a real loopback listener. Never reads the user's real config.
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import unittest
import unittest.mock
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "ai-kit-gsd-spec-discuss" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import decide
import edge_floor
import phase_range

SENTINEL = "SENTINEL-KEY-0123456789abcdef"

# Fake jev client: logs what it received (env names, never a real key), answers by backend.
FAKE_CLIENT = textwrap.dedent('''
    import json, os, sys
    payload = json.load(sys.stdin)
    url = os.environ.get("JEV_API_URL", "")
    log = os.environ.get("FAKE_JEV_LOG")
    if log:
        with open(log, "a") as fh:
            fh.write(json.dumps({"url": url, "model": os.environ.get("JEV_MODEL"),
                                 "key": os.environ.get("JEV_API_KEY"),
                                 "opencode": "OPENCODE_API_KEY" in os.environ,
                                 "min": os.environ.get("JEV_MIN_CONFIDENCE"),
                                 "ids": [i["id"] for i in payload["items"]]}) + "\\n")
    remote = "typesafe" in url
    answers = {}
    for item in payload["items"]:
        names = list(item.get("criteria") or {"yes": 1, "no": 1})
        top = 0.9 if remote or "sure" in item["id"] else 0.5
        if item["type"] == "noul":
            answers[item["id"]] = {"type": "noul", "noul": top, "needs_fallback": top < 0.7}
            continue
        rest = (1 - top) / (len(names) - 1)
        answers[item["id"]] = {"type": "choice", "choice": names[0], "confidence": top,
                               "probabilities": {n: (top if i == 0 else rest)
                                                 for i, n in enumerate(names)},
                               "needs_fallback": top < 0.7}
    out = {"advisory": True, "status": "ok", "answers": answers}
    if os.environ.get("FAKE_JEV_LEAK"):
        out["debug_env"] = dict(os.environ)
        sys.stderr.write(json.dumps(dict(os.environ)))
    print(json.dumps(out))
''')


def choice_item(identifier, context="Option A is smaller; option B is safer."):
    return {"id": identifier, "type": "choice", "instructions": "Which option is best?",
            "context": context, "criteria": {"a": "the smaller option", "b": "the safer option"}}


class _Listener:
    """A real loopback TCP listener standing in for a reachable Laya."""

    def __enter__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(8)
        self.url = f"http://127.0.0.1:{self.sock.getsockname()[1]}/v1/systemone"
        return self

    def __exit__(self, *exc):
        self.sock.close()


def closed_port_url():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}/v1/systemone"


class _TmpHome(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.env = {"HOME": str(self.tmp), "XDG_CONFIG_HOME": str(self.tmp / "cfg"),
                    "PATH": os.environ.get("PATH", "")}

    def seams(self, **extra):
        env = {**self.env, **extra}
        return decide.Seams(env=env, run=subprocess.run,
                            connect=socket.create_connection)


# ─── decide.py: unit layer ────────────────────────────────────────────────────

class TestLayaUrl(unittest.TestCase):
    def test_dedicated_variable_wins(self):
        env = {"AI_KIT_LAYA_URL": "http://10.0.0.5:8010/x", "JEV_API_URL": "http://127.0.0.1:1/x"}
        self.assertEqual(decide.laya_url(env), ("http://10.0.0.5:8010/x", "AI_KIT_LAYA_URL"))

    def test_shared_variable_only_when_loopback(self):
        self.assertEqual(decide.laya_url({"JEV_API_URL": "http://localhost:8010/v1"})[1],
                         "JEV_API_URL")
        self.assertEqual(decide.laya_url({"JEV_API_URL": "https://opencode.ai/zen/v1"}),
                         (None, None))

    def test_nothing_configured_probes_nothing(self):
        self.assertEqual(decide.laya_url({}), (None, None))


class TestTypesafeKey(_TmpHome):
    def test_env_first(self):
        self.assertEqual(decide.typesafe_key({**self.env, "JEV_API_KEY": SENTINEL}),
                         (SENTINEL, "env"))

    def test_key_file_named_by_env(self):
        key_file = self.tmp / "k.txt"
        key_file.write_text(SENTINEL + "\n")
        env = {**self.env, "JEV_API_KEY_FILE": str(key_file)}
        self.assertEqual(decide.typesafe_key(env), (SENTINEL, "key_file"))

    def test_secrets_env_line(self):
        secrets = self.tmp / "cfg" / "ai-kit" / "secrets.env"
        secrets.parent.mkdir(parents=True)
        secrets.write_text(f"# comment\nOTHER=1\nJEV_API_KEY='{SENTINEL}'\n")
        self.assertEqual(decide.typesafe_key(self.env), (SENTINEL, "secrets_env"))

    def test_none(self):
        self.assertEqual(decide.typesafe_key(self.env), (None, None))


class TestItemError(unittest.TestCase):
    def test_valid_items(self):
        self.assertIsNone(decide.item_error(choice_item("x")))
        self.assertIsNone(decide.item_error({"id": "n", "type": "noul",
                                             "instructions": "Ship it?", "context": "All green."}))

    def test_commit_sha_in_summary_passes(self):
        sha = "a5b3fab" + "0" * 33
        self.assertIsNone(decide.item_error(choice_item("x", f"Amended in commit {sha}.")))

    def test_rejections(self):
        cases = {
            "empty_context": choice_item("x", context=" "),
            "unknown_key": {**choice_item("x"), "evidence": "raw"},
            "choice_needs_two_criteria": {**choice_item("x"), "criteria": {"a": "only"}},
            "code_fence_context": choice_item("x", "```python\nprint(1)\n```"),
            "secret_pattern_context": choice_item("x", "token sk-" + "a" * 30),
            "too_long_context": choice_item("x", "y" * (decide.MAX_FIELD_CHARS + 1)),
            "bad_type": {**choice_item("x"), "type": "score"},
            "missing_id": {**choice_item(""), "id": ""},
        }
        for reason, item in cases.items():
            with self.subTest(reason):
                self.assertEqual(decide.item_error(item), reason)


class TestTypedAnswer(unittest.TestCase):
    def test_choice_top_is_winning_probability(self):
        got = decide.typed_answer({"type": "choice", "choice": "a", "confidence": 0.03,
                                   "probabilities": {"a": 0.46, "b": 0.54 - 0.1, "c": 0.1},
                                   "needs_fallback": True})
        self.assertEqual(got, {"choice": "a", "top": 0.46, "fallback": True})

    def test_noul_maps_to_yes_no(self):
        self.assertEqual(decide.typed_answer({"type": "noul", "noul": 0.2})["choice"], "no")
        self.assertEqual(decide.typed_answer({"type": "noul", "noul": 0.2})["top"], 0.8)

    def test_garbage(self):
        self.assertEqual(decide.typed_answer("nope"), {"error": "invalid_response"})


class TestConsent(_TmpHome):
    def test_round_trip_and_host_binding(self):
        with _Listener() as laya:
            seams = self.seams(AI_KIT_LAYA_URL=laya.url.replace("127.0.0.1", "10.9.9.9"))
            self.assertIsNone(decide.consent_date(seams.env, "laya"))
            decide.consent(seams, "grant", "laya")
            self.assertIsNotNone(decide.consent_date(seams.env, "laya"))
            moved = self.seams(AI_KIT_LAYA_URL="http://10.1.1.1:8010/v1")
            self.assertIsNone(decide.consent_date(moved.env, "laya"))
            decide.consent(seams, "revoke", "laya")
            self.assertIsNone(decide.consent_date(seams.env, "laya"))

    def test_grant_without_endpoint_refuses(self):
        self.assertFalse(decide.consent(self.seams(), "grant", "laya")["ok"])


class TestBackendStatus(_TmpHome):
    def test_detection_combinations(self):
        with _Listener() as laya:
            rows = [
                ({}, "not_configured", "no_key"),
                ({"AI_KIT_LAYA_URL": closed_port_url()}, "unreachable", "no_key"),
                ({"AI_KIT_LAYA_URL": laya.url, "JEV_API_KEY": SENTINEL}, None, "no_consent"),
            ]
            for extra, laya_skip, ts_skip in rows:
                with self.subTest(extra=sorted(extra)):
                    status = decide.backend_status(self.seams(**extra))
                    self.assertEqual(status["laya"].get("skip"), laya_skip)
                    self.assertEqual(status["typesafe"].get("skip"), ts_skip)

    def test_remote_laya_needs_its_own_consent(self):
        seams = self.seams(AI_KIT_LAYA_URL="http://10.9.9.9:8010/v1", JEV_API_KEY=SENTINEL)
        decide.consent(seams, "grant", "typesafe")
        fake = decide.Seams(env=seams.env, run=seams.run, connect=lambda *a, **k: socket.socket())
        self.assertEqual(decide.backend_status(fake)["laya"]["skip"], "no_consent")


class TestFindClient(_TmpHome):
    def test_override_then_roots(self):
        client = self.tmp / "jev_review.py"
        client.write_text("")
        self.assertEqual(decide.find_client(self.env, str(client))[0], str(client))
        rooted = self.tmp / ".claude" / "skills" / decide.CLIENT_REL
        rooted.parent.mkdir(parents=True)
        rooted.write_text("")
        self.assertEqual(decide.find_client(self.env, None)[0], str(rooted))


# ─── decide.py: subprocess layer ──────────────────────────────────────────────

class TestLadderCli(_TmpHome):
    def setUp(self):
        super().setUp()
        self.client = self.tmp / "fake_jev.py"
        self.client.write_text(FAKE_CLIENT)
        self.log = self.tmp / "calls.jsonl"
        self.env["FAKE_JEV_LOG"] = str(self.log)

    def run_cli(self, args, stdin="", **extra):
        return subprocess.run([sys.executable, str(SCRIPTS / "decide.py"),
                               "--client", str(self.client), *args],
                              input=stdin, capture_output=True, text=True, check=False,
                              env={**self.env, **extra}, cwd=self.tmp, timeout=60)

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def ladder(self, items, *flags, **extra):
        out = self.run_cli(["ladder", *flags], json.dumps({"items": items}), **extra)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout), out

    def grant_typesafe(self):
        self.assertEqual(self.run_cli(["consent", "grant", "typesafe"]).returncode, 0)

    def test_no_backend_completes_with_own_reasoning_and_no_calls(self):
        result, _ = self.ladder([choice_item("a1"), choice_item("a2")])
        self.assertEqual({v["decided_by"] for v in result["items"].values()}, {"own_reasoning"})
        self.assertEqual(self.calls(), [])

    def test_laya_one_call_per_item_then_typesafe_batch(self):
        self.grant_typesafe()
        with _Listener() as laya:
            result, _ = self.ladder([choice_item("sure1"), choice_item("low1"),
                                     choice_item("low2")],
                                    AI_KIT_LAYA_URL=laya.url, JEV_API_KEY=SENTINEL,
                                    OPENCODE_API_KEY="inherited", JEV_MIN_CONFIDENCE="0.1")
        calls = self.calls()
        laya_calls = [c for c in calls if "typesafe" not in c["url"]]
        ts_calls = [c for c in calls if "typesafe" in c["url"]]
        self.assertEqual([c["ids"] for c in laya_calls], [["sure1"], ["low1"], ["low2"]])
        self.assertEqual([c["ids"] for c in ts_calls], [["low1", "low2"]])
        self.assertTrue(all(c["key"] is None for c in laya_calls), "key reached Laya")
        self.assertEqual(ts_calls[0]["key"], SENTINEL)
        self.assertFalse(any(c["opencode"] for c in calls))
        self.assertEqual({c["min"] for c in calls}, {decide.MIN_CONFIDENCE})
        self.assertEqual(result["items"]["sure1"]["decided_by"], "laya")
        self.assertEqual(result["items"]["low1"]["decided_by"], "typesafe")

    def test_no_consent_means_zero_remote_calls(self):
        result, _ = self.ladder([choice_item("x")], JEV_API_KEY=SENTINEL)
        self.assertEqual(self.calls(), [])
        self.assertEqual(result["backends"]["typesafe"]["skip"], "no_consent")

    def test_second_opinion_skips_laya(self):
        self.grant_typesafe()
        with _Listener() as laya:
            result, _ = self.ladder([choice_item("sure1")], "--second-opinion",
                                    AI_KIT_LAYA_URL=laya.url, JEV_API_KEY=SENTINEL)
        self.assertEqual([c["url"] for c in self.calls()], [decide.TYPESAFE_URL])
        self.assertIsNone(result["items"]["sure1"]["laya"])
        self.assertEqual(result["items"]["sure1"]["decided_by"], "typesafe")

    def test_no_key_value_in_any_output_even_from_a_leaky_client(self):
        self.grant_typesafe()
        result, out = self.ladder([choice_item("x")], JEV_API_KEY=SENTINEL, FAKE_JEV_LEAK="1")
        self.assertEqual(result["items"]["x"]["decided_by"], "typesafe")
        self.assertNotIn(SENTINEL, out.stdout + out.stderr)
        detect = self.run_cli(["detect"], JEV_API_KEY=SENTINEL)
        self.assertNotIn(SENTINEL, detect.stdout + detect.stderr)
        self.assertEqual(json.loads(detect.stdout)["typesafe"]["key_source"], "env")

    def test_invalid_item_rejected_alone(self):
        self.grant_typesafe()
        result, _ = self.ladder([choice_item("bad", context=""), choice_item("good")],
                                JEV_API_KEY=SENTINEL)
        self.assertEqual(result["items"]["bad"]["reason"], "empty_context")
        self.assertEqual([c["ids"] for c in self.calls()], [["good"]])

    def test_unusable_stdin_exits_2(self):
        self.assertEqual(self.run_cli(["ladder"], "not json").returncode, 2)
        self.assertEqual(self.run_cli(["ladder"], '{"items": []}').returncode, 2)


@unittest.skipUnless((Path.home() / ".claude" / "skills" / decide.CLIENT_REL).is_file(),
                     "jev-fast-decision not installed")
class TestRealClientSmoke(_TmpHome):
    def test_real_client_answers_disabled_shape_without_backends(self):
        real = Path.home() / ".claude" / "skills" / decide.CLIENT_REL
        out = subprocess.run([sys.executable, "-B", str(real)], input="{}", capture_output=True,
                             text=True, env={"PATH": self.env["PATH"]}, check=False, timeout=30)
        self.assertEqual(json.loads(out.stdout)["status"], "disabled")


# ─── phase_range.py ───────────────────────────────────────────────────────────

def _args(start=None, end=None, phases=None):
    return argparse.Namespace(start=start, end=end, list=phases)


class TestPhaseRange(_TmpHome):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "phases"
        self.times = {}
        layout = {"16-a": [], "16.1-b": ["SPEC", "CONTEXT"], "17-c": ["SPEC", "CONTEXT"],
                  "18-d": ["SPEC"], "19-e": ["SPEC", "CONTEXT"]}
        for name, files in layout.items():
            (self.root / name).mkdir(parents=True)
            for kind in files:
                path = self.root / name / f"{name.split('-')[0]}-{kind}.md"
                path.write_text(kind)
                self.times[str(path)] = 100.0
        self.times[str(self.root / "17-c" / "17-SPEC.md")] = 200.0  # SPEC newer
        self.roadmap = {"phases": [
            {"number": "19", "disk_status": "discussed"},
            {"number": "16", "disk_status": "executed"},
            {"number": "17", "disk_status": "discussed"},
            {"number": "16.1", "disk_status": "discussed"},
            {"number": "18", "disk_status": "specified", "mode": "mvp"}]}

    def propose(self, args):
        return phase_range.propose(self.roadmap, str(self.root), args, timer=self.times.get)

    def test_no_range_proposes_undiscussed_with_reasons(self):
        got = self.propose(_args())
        self.assertEqual([(p["phase"], p["reason"]) for p in got["proposed"]],
                         [("17", "SPEC newer than CONTEXT"), ("18", "no CONTEXT")])
        self.assertEqual(got["proposed"][1]["mode"], "mvp")
        self.assertEqual(got["skipped"], [{"phase": "16", "reason": "executed"}])

    def test_explicit_range_and_list(self):
        self.assertEqual([p["phase"] for p in self.propose(_args("16.1", "18"))["proposed"]],
                         ["16.1", "17", "18"])
        self.assertEqual([p["phase"] for p in self.propose(_args(phases="19,16.1"))["proposed"]],
                         ["16.1", "19"])

    def test_decimal_order(self):
        self.assertLess(phase_range.phase_key("16.1"), phase_range.phase_key("16.10"))
        self.assertLess(phase_range.phase_key("9"), phase_range.phase_key("16"))


# ─── edge_floor.py ────────────────────────────────────────────────────────────

SPEC = textwrap.dedent("""\
    # Phase 9: X — Specification

    ## Requirements

    1. **Parse rows**.
       - Target: an empty list yields no rows; a row at the max width parses.
       - Acceptance: tests.

    2. **Write cache** (REQ-2).
       - Target: two concurrent writers leave one intact file.

    ## Boundaries

    nothing

    ## Edge Coverage

    | Category | Requirement | Status | Resolution / Reason |
    |----------|-------------|--------|---------------------|
    | empty | R1 | ✅ covered | Empty input yields [] |
    | boundary | R1 | ✅ covered | Max width parses (added by the author) |
    | unclassified | R2 | ✅ covered | wrong |
    | ordering | R2 | 🧪 backstop | unmarked extra |

    ## Prohibitions (must-NOT)
    """)


class TestEdgeFloor(unittest.TestCase):
    def test_requirements_extraction_rule(self):
        reqs = edge_floor.requirements(SPEC)
        self.assertEqual([r["id"] for r in reqs], ["R1", "R2"])
        self.assertTrue(reqs[0]["text"].startswith("Parse rows. "))
        self.assertIn("Target: an empty list yields no rows", reqs[0]["text"])
        self.assertIn("Acceptance: tests.", reqs[0]["text"])

    def test_compare_flags_missing_unmarked_and_unclassified(self):
        floor = {"items": [{"category": "empty", "requirement_id": "R1"},
                           {"category": "concurrency", "requirement_id": "R2"},
                           {"category": "unclassified", "requirement_id": "R2"}]}
        got = edge_floor.compare(floor, edge_floor.table_rows(SPEC))
        self.assertFalse(got["ok"])
        self.assertEqual(got["missing"], [("concurrency", "R2")])
        self.assertEqual(got["unmarked_extra"], [("ordering", "R2")])
        self.assertEqual(got["unclassified_not_unresolved"], [("unclassified", "R2")])

    def test_missing_engine_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "09-SPEC.md"
            spec.write_text(SPEC)
            env = {"HOME": tmp, "RUNTIME_DIR": tmp}
            with unittest.mock.patch("sys.stderr"):
                self.assertEqual(edge_floor.main(["check", str(spec)], env=env), 2)

    @unittest.skipUnless(shutil.which("node") and edge_floor.find_engine(os.environ, os.getcwd(),
                                                                          None),
                         "node or gsd-core edge-probe.cjs not installed")
    def test_real_engine_floor(self):
        engine = edge_floor.find_engine(os.environ, os.getcwd(), None)
        floor = edge_floor.run_engine(engine, edge_floor.requirements(SPEC))
        self.assertTrue({i["requirement_id"] for i in floor["items"]} <= {"R1", "R2"})


if __name__ == "__main__":
    unittest.main()
