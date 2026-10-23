"""Tests for skills/ai-kit-gsd-spec-discuss/scripts (decide.py, phase_range.py, edge_floor.py).

Two layers: injected-seam unit tests, and subprocess tests that run the real CLI against the
real repo client (`skills/jev-fast-decision/scripts/jev_review.py`) with in-process HTTP stubs
(`JevStub`, shared with tests.test_jev_fast_decision) standing in for the backends. Every env
pins `JEV_LAYA_URL` to a stub or a closed loopback port (the client's default is the real local
Laya) and uses a temp HOME/XDG tree. Never reads the user's real config.
"""

import argparse
import importlib.util
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

from tests.test_jev_fast_decision import JevStub

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "ai-kit-gsd-spec-discuss" / "scripts"
REPO_CLIENT = SCRIPTS.parent.parent / "jev-fast-decision" / "scripts" / "jev_review.py"
sys.path.insert(0, str(SCRIPTS))
import decide
import edge_floor
import phase_range

SENTINEL = "SENTINEL-KEY-0123456789abcdef"
HEAD = "0" * 40
_PUBLIC_BACKEND_KEYS = {"name", "remote", "batch", "host", "usable", "reason", "key_source",
                        "consent", "status"}
_PUBLIC_CONSENT_KEYS = {"ok", "backend", "host", "consent", "file", "note", "reason"}

# Fake jev client carrying the protocol line decide.py requires: logs its calls, answers every
# item from one rung named "fake", and leaks its whole env when FAKE_JEV_LEAK is set (24 D-13).
FAKE_CLIENT = textwrap.dedent('''
    import json, os, sys

    CLIENT_PROTOCOL = 2

    argv = sys.argv[1:]
    if os.environ.get("FAKE_JEV_LOG"):
        with open(os.environ["FAKE_JEV_LOG"], "a") as fh:
            fh.write(json.dumps({"argv": argv}) + "\\n")

    def emit(out):
        if os.environ.get("FAKE_JEV_LEAK"):
            out["debug_env"] = dict(os.environ)
            sys.stderr.write(json.dumps(dict(os.environ)))
        print(json.dumps(out))

    if argv == ["--probe"]:
        backends = [
            {"name": "fake", "remote": False, "batch": False, "host": "127.0.0.1",
             "usable": True, "key_source": None, "reason": None, "consent": None},
            {"name": "remote-one", "remote": True, "batch": True, "host": "example.test",
             "usable": False, "key_source": None, "reason": "no_key", "consent": None,
             "debug_env": dict(os.environ)},
        ]
        emit({"status": "ok", "backends": backends})
        sys.exit(0)
    if len(argv) == 3 and argv[0] == "consent":
        out = {"ok": True, "backend": argv[2], "host": "example.test",
               "consent": "2026-10-18", "file": "/tmp/fake-consent.json",
               "note": "fake note"}
        if os.environ.get("FAKE_JEV_LEAK"):
            out["debug_env"] = dict(os.environ)
        print(json.dumps(out))
        sys.exit(0)

    payload = json.load(sys.stdin)
    answers, trail = {}, {}
    for item in payload["items"]:
        names = list(item.get("criteria") or {"yes": "y", "no": "n"})
        top = 0.9 if "sure" in item["id"] else 0.5
        rest = round((1 - top) / (len(names) - 1), 4)
        entry = {"backend": "fake", "model": "fake-1", "choice": names[0],
                 "probabilities": {name: (top if i == 0 else rest)
                                   for i, name in enumerate(names)},
                 "top": top, "needs_fallback": top < 0.7}
        answers[item["id"]] = entry
        trail[item["id"]] = [entry]
    emit({"status": "ok", "answers": answers, "trail": trail,
          "backends": [{"name": "fake", "remote": False, "batch": False, "host": "127.0.0.1",
                        "usable": True, "key_source": None, "reason": None, "consent": None}],
          "consent_used": [{"backend": "remote-one", "granted": "2026-10-18",
                            "debug_env": "leaked"}],
          "remote_available": ["remote-one", 42]})
''')


def choice_item(identifier, context="Option A is smaller; option B is safer."):
    return {"id": identifier, "type": "choice", "instructions": "Which option is best?",
            "context": context, "criteria": {"a": "the smaller option", "b": "the safer option"}}


def noul_item(identifier, context="All green on the live check."):
    return {"id": identifier, "type": "noul", "instructions": "Ship it?", "context": context}


def score_item(identifier, levels=None, context="The refund is duplicated."):
    return {"id": identifier, "type": "score", "instructions": "How severe is it?",
            "context": context, "criteria": levels or ["low", "mid", "high"]}


def closed_port_url():
    """A loopback URL on a port nothing listens on (bound, then released right away)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}/v1/systemone"


def _isolated_decide(tmp):
    """A copy of decide.py whose own skills root holds no client (the repo copy's always does)."""
    scripts = Path(tmp) / "skills" / "ai-kit-gsd-spec-discuss" / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(SCRIPTS / "decide.py", scripts / "decide.py")
    return scripts


def _load_client():
    """The real client module, loaded by path: parity checks against its request builder."""
    spec = importlib.util.spec_from_file_location("jev_review_parity", str(REPO_CLIENT))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _TmpHome(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        home = self.tmp / "home"
        home.mkdir()
        self.env = {"HOME": str(home),
                    "XDG_CONFIG_HOME": str(home / ".config"),
                    "XDG_STATE_HOME": str(home / ".local" / "state"),
                    "XDG_DATA_HOME": str(home / ".local" / "share"),
                    "PATH": os.environ.get("PATH", ""),
                    "JEV_LAYA_URL": closed_port_url()}

    def seams(self, **extra):
        env = {**self.env, **extra}
        return decide.Seams(env=env, run=subprocess.run)


# ─── decide.py: unit layer ────────────────────────────────────────────────────

class TestItemError(unittest.TestCase):
    def test_valid_items(self):
        self.assertIsNone(decide.item_error(choice_item("x")))
        self.assertIsNone(decide.item_error(noul_item("n")))
        self.assertIsNone(decide.item_error({**noul_item("n"),
                                             "criteria": {"true": "holds",
                                                          "false": "fails"}}))
        self.assertIsNone(decide.item_error(score_item("s")))

    def test_commit_sha_in_summary_passes(self):
        sha = "a5b3fab" + "0" * 33
        self.assertIsNone(decide.item_error(choice_item("x", f"Amended in commit {sha}.")))

    def test_rejections(self):
        cases = [
            ("empty_context", choice_item("x", context=" ")),
            ("unknown_key", {**choice_item("x"), "evidence": "raw"}),
            ("choice_needs_two_criteria", {**choice_item("x"), "criteria": {"a": "only"}}),
            ("missing_criteria", {k: v for k, v in choice_item("x").items() if k != "criteria"}),
            ("missing_criteria", {k: v for k, v in score_item("s").items() if k != "criteria"}),
            ("bad_criteria", {**noul_item("n"), "criteria": {"yes": "y", "no": "n"}}),
            ("bad_criteria", {**noul_item("n"), "criteria": None}),
            ("bad_criteria", {**noul_item("n"), "criteria": {"true": "holds"}}),
            ("reserved_id", choice_item("#2")),
            ("code_fence_context", choice_item("x", "```python\nprint(1)\n```")),
            ("secret_pattern_context", choice_item("x", "token sk-" + "a" * 30)),
            ("too_long_context", choice_item("x", "y" * (decide.MAX_FIELD_CHARS + 1))),
            ("bad_type", {**choice_item("x"), "type": "box"}),
            ("bad_criteria", score_item("s", ["only"])),
            ("bad_criteria", score_item("s", [f"l{i}" for i in range(11)])),
            ("bad_criteria", score_item("s", {"low": "high"})),
            ("bad_criteria", score_item("s", ["low", " "])),
            ("missing_id", {**choice_item(""), "id": ""}),
            ("missing_id", {**choice_item(""), "id": " "}),
        ]
        for reason, item in cases:
            with self.subTest(reason=reason, id=item["id"]):
                self.assertEqual(decide.item_error(item), reason)


class TestTypedAnswer(unittest.TestCase):
    def test_choice_rung(self):
        got = decide.typed_answer({"backend": "one", "model": "m-1", "type": "choice",
                                   "choice": "a", "probabilities": {"a": 0.46, "b": 0.54},
                                   "top": 0.54, "needs_fallback": True})
        self.assertEqual(got, {"choice": "a", "top": 0.54, "fallback": True, "model": "m-1"})

    def test_noul_rung_maps_to_yes_no(self):
        low = decide.typed_answer({"backend": "one", "noul": 0.2, "top": 0.8,
                                   "needs_fallback": False})
        self.assertEqual(low["choice"], "no")
        self.assertEqual(low["top"], 0.8)
        self.assertEqual(decide.typed_answer({"backend": "one", "noul": 0.8, "top": 0.8,
                                              "needs_fallback": False})["choice"], "yes")

    def test_error_rung(self):
        self.assertEqual(decide.typed_answer({"backend": "one", "error": "http_503"}),
                         {"error": "http_503"})

    def test_score_rung_names_the_winning_level(self):
        got = decide.typed_answer({"backend": "one", "model": "m-1", "type": "score",
                                   "level": "2", "legend": {"0": "low", "1": "mid",
                                                            "2": "high"},
                                   "top": 0.91, "needs_fallback": False})
        self.assertEqual(got, {"choice": "high", "top": 0.91, "fallback": False,
                               "model": "m-1"})

    def test_garbage(self):
        self.assertEqual(decide.typed_answer("nope"), {"error": "invalid_response"})
        self.assertEqual(decide.typed_answer({"backend": "one", "model": "m-1"}),
                         {"error": "invalid_response"})


class TestFindClient(_TmpHome):
    def test_override_then_roots(self):
        client = self.tmp / "jev_review.py"
        client.write_text("")
        self.assertEqual(decide.find_client(self.env, str(client))[0], str(client))
        rooted = self.tmp / "home" / ".claude" / "skills" / decide.CLIENT_REL
        rooted.parent.mkdir(parents=True)
        rooted.write_text("")
        # 21.1-01 put the client in this repo, so the repo's own skills/ root wins (D-02);
        # the home-rooted path stays in `tried` because it is still a real lookup candidate.
        sibling = str(SCRIPTS.parent.parent / decide.CLIENT_REL)
        self.assertEqual(decide.find_client(self.env, None)[0], sibling)
        self.assertIn(str(rooted), decide.find_client(self.env, None)[1])


# ─── decide.py: subprocess layer ──────────────────────────────────────────────

class TestLadderCli(_TmpHome):
    def setUp(self):
        super().setUp()
        self.fake = self.tmp / "fake_jev.py"
        self.fake.write_text(FAKE_CLIENT)
        self.log = self.tmp / "calls.jsonl"
        self.env["FAKE_JEV_LOG"] = str(self.log)

    def run_cli(self, args, stdin="", client=None, **extra):
        target = str(client or REPO_CLIENT)
        return subprocess.run([sys.executable, str(SCRIPTS / "decide.py"),
                               "--client", target, *args],
                              input=stdin, capture_output=True, text=True, check=False,
                              env={**self.env, **extra}, cwd=self.tmp, timeout=120)

    def cli_json(self, args, **extra):
        out = self.run_cli(args, **extra)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def ladder(self, items, *flags, client=None, **extra):
        out = self.run_cli(["ladder", *flags], json.dumps({"items": items}),
                           client=client, **extra)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout), out

    def grant_typesafe(self, **extra):
        return self.cli_json(["consent", "grant", "typesafe"], **extra)

    @staticmethod
    def _client_calls(calls):
        return [call for call in calls if call[0][0][:2] == [sys.executable, "-B"]]

    def test_ladder_laya_then_remote_batch(self):
        with (JevStub(tops={"low1": 0.5, "low2": 0.5}) as laya,
              JevStub(model="typesafe-1") as remote):
            extra = {"JEV_LAYA_URL": laya.url,
                     "JEV_TYPESAFE_URL": f"http://127.0.0.1:{remote.port}",
                     "TYPESAFE_API_KEY": SENTINEL}
            granted = self.grant_typesafe(**extra)
            self.assertTrue(granted["ok"])
            result, _ = self.ladder([choice_item("sure1"), choice_item("low1"),
                                     choice_item("low2")], **extra)
            laya_bodies, remote_bodies = laya.bodies, remote.bodies
            laya_headers = [record["headers"] for record in laya.posts]
            remote_headers = [record["headers"] for record in remote.posts]
        self.assertEqual([sorted(body["questions"]) for body in laya_bodies],
                         [["sure1"], ["low1"], ["low2"]])
        self.assertEqual([sorted(body["questions"]) for body in remote_bodies],
                         [["low1", "low2"]])
        self.assertNotIn("Authorization", laya_headers[0], "the key reached the local rung")
        self.assertEqual(remote_headers[0].get("Authorization"), f"Bearer {SENTINEL}")
        self.assertEqual(result["items"]["sure1"]["decided_by"], "laya")
        self.assertEqual(result["items"]["low1"]["decided_by"], "typesafe")
        self.assertTrue(result["items"]["low1"]["laya"]["fallback"])
        for identifier in ("sure1", "low1", "low2"):
            columns = set(result["items"][identifier]) - {"decided_by"}
            self.assertEqual(columns, {"laya", "typesafe", "opencode"})
        self.assertIsNone(result["items"]["sure1"]["opencode"])

    def test_ladder_no_consent_zero_remote(self):
        environ_before = dict(os.environ)
        with JevStub(tops={"low1": 0.5}) as laya, JevStub(model="typesafe-1") as remote:
            result, _ = self.ladder([choice_item("low1")], JEV_LAYA_URL=laya.url,
                                    JEV_TYPESAFE_URL=f"http://127.0.0.1:{remote.port}",
                                    TYPESAFE_API_KEY=SENTINEL, JEV_ALLOW_REMOTE="1")
            remote_posts = remote.posts
        self.assertEqual(remote_posts, [], "the record check, not the parent env, gates remotes")
        self.assertEqual(result["items"]["low1"]["decided_by"], "own_reasoning")
        self.assertEqual(result["remote_available"], ["typesafe"])
        self.assertEqual(result["consent_used"], [])
        self.assertEqual(dict(os.environ), environ_before)
        self.assertNotIn("GSD_PATH_JEV", os.environ, "the kill switch leaked into the parent env")

    def test_ladder_child_env_scrubbed(self):
        items = [choice_item("a1"), choice_item("a2"), choice_item("a3")]
        parent_env = {**self.env, "JEV_BACKEND": "laya", "JEV_ALLOW_REMOTE": "1",
                      "JEV_MIN_CONFIDENCE": "0.1", "GSD_PATH_JEV_DEADLINE_SECONDS": "999",
                      "TYPESAFE_API_KEY": SENTINEL, "JEV_TYPESAFE_URL": "http://127.0.0.1:9"}
        env_before = dict(parent_env)
        environ_before = dict(os.environ)
        calls = []

        def record(*args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.run(*args, **kwargs)

        result = decide.run_ladder(decide.Seams(env=parent_env, run=record),
                                   str(REPO_CLIENT), items)
        client_calls = self._client_calls(calls)
        self.assertEqual(len(client_calls), 1)
        child = client_calls[0][1]["env"]
        for name in ("JEV_BACKEND", "JEV_ALLOW_REMOTE", "JEV_MIN_CONFIDENCE"):
            self.assertNotIn(name, child, f"control variable {name} reached the client")
        self.assertNotEqual(child["GSD_PATH_JEV_DEADLINE_SECONDS"], "999",
                            "the parent's GSD_PATH_JEV* value reached the client")
        self.assertEqual(child["GSD_PATH_JEV"], "1")
        self.assertEqual(child["GSD_PATH_JEV_TIMEOUT_SECONDS"], "30")
        self.assertEqual(child["GSD_PATH_JEV_DEADLINE_SECONDS"], str(30 * (len(items) + 3)))
        self.assertEqual(child["JEV_CALLER"], "ai-kit-gsd-spec-discuss")
        self.assertEqual(child["TYPESAFE_API_KEY"], SENTINEL, "keys pass through to the client")
        self.assertEqual(child["JEV_TYPESAFE_URL"], "http://127.0.0.1:9")
        self.assertEqual(parent_env, env_before)
        self.assertEqual(dict(os.environ), environ_before)
        self.assertEqual(result["client"], {"found": True})

    def test_ladder_one_subprocess(self):
        with JevStub() as laya:
            calls = []

            def record(*args, **kwargs):
                calls.append((args, kwargs))
                return subprocess.run(*args, **kwargs)

            result = decide.run_ladder(decide.Seams(env={**self.env, "JEV_LAYA_URL": laya.url},
                                                    run=record),
                                       str(REPO_CLIENT), [choice_item("a1"), choice_item("a2")])
        self.assertEqual(len(self._client_calls(calls)), 1)
        self.assertEqual(result["items"]["a1"]["decided_by"], "laya")
        self.assertEqual(result["items"]["a2"]["decided_by"], "laya")

    def test_ladder_no_client(self):
        scripts = _isolated_decide(self.tmp)
        out = subprocess.run([sys.executable, str(scripts / "decide.py"), "ladder"],
                             input=json.dumps({"items": [choice_item("a1"), choice_item("a2")]}),
                             capture_output=True, text=True, check=False,
                             env={"HOME": str(self.tmp / "home"), "PATH": self.env["PATH"]},
                             cwd=self.tmp, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        result = json.loads(out.stdout)
        self.assertFalse(result["client"]["found"])
        self.assertNotIn("client_status", result)
        self.assertEqual({row["decided_by"] for row in result["items"].values()},
                         {"own_reasoning"})

    def test_ladder_incompatible_client(self):
        stale = self.tmp / "stale_jev.py"
        stale.write_text(FAKE_CLIENT.replace("CLIENT_PROTOCOL = 2", "CLIENT_PROTOCOL = 1"))
        result, _ = self.ladder([choice_item("a1")], client=stale)
        self.assertEqual(self.calls(), [], "a client without the protocol line must never run")
        self.assertEqual(result["client_status"], "incompatible_client")
        self.assertEqual(result["items"]["a1"]["decided_by"], "own_reasoning")
        self.assertEqual(result["client"], {"found": True})

    def test_ladder_order_and_encoding(self):
        items = [choice_item("b"), choice_item("a"), choice_item("naïve")]
        result, out = self.ladder(items)
        self.assertEqual(result["order"], ["b", "a", "naïve"])
        self.assertEqual(json.loads(out.stdout)["items"]["naïve"]["decided_by"], "own_reasoning")
        self.assertEqual(out.stdout, json.dumps(result, indent=1, sort_keys=True) + "\n")

    def test_ladder_mixed_batch_keeps_valid_siblings(self):
        items = [choice_item("good1"),
                 {**noul_item("bad_noul"), "criteria": {"yes": "y", "no": "n"}},
                 choice_item("good1"),
                 " ",
                 noul_item("good2")]
        with JevStub() as laya:
            result, _ = self.ladder(items, JEV_LAYA_URL=laya.url)
            again, _ = self.ladder([noul_item("#2"), noul_item("good"), noul_item("good")],
                                   JEV_LAYA_URL=laya.url)
            bodies = laya.bodies
        self.assertEqual([sorted(body["questions"]) for body in bodies],
                         [["good1"], ["good2"], ["good"]])
        self.assertEqual(result["items"]["bad_noul"]["reason"], "bad_criteria")
        self.assertEqual(result["items"]["#2"]["reason"], "duplicate_id")
        self.assertEqual(result["items"]["#3"]["reason"], "missing_id")
        self.assertEqual(result["order"], ["good1", "bad_noul", "#2", "#3", "good2"])
        self.assertEqual(result["items"]["good1"]["decided_by"], "laya")
        self.assertEqual(result["items"]["good2"]["decided_by"], "laya")
        self.assertEqual(again["items"]["#0"]["reason"], "reserved_id")
        self.assertEqual(again["items"]["#2"]["reason"], "duplicate_id")
        self.assertEqual(again["items"]["good"]["decided_by"], "laya")
        self.assertEqual(again["order"], ["#0", "good", "#2"])
        self.assertEqual(set(again["items"]), {"#0", "good", "#2"})

    def test_no_key_value_in_any_output_even_from_a_leaky_client(self):
        result, out = self.ladder([choice_item("sure1")], client=self.fake,
                                  JEV_API_KEY=SENTINEL, FAKE_JEV_LEAK="1")
        self.assertEqual(result["items"]["sure1"]["decided_by"], "fake")
        self.assertNotIn(SENTINEL, out.stdout + out.stderr)
        self.assertEqual(result["consent_used"],
                         [{"backend": "remote-one", "granted": "2026-10-18"}])
        self.assertEqual(result["remote_available"], ["remote-one"])
        for entry in result["backends"].values():
            self.assertLessEqual(set(entry), _PUBLIC_BACKEND_KEYS)

    def test_item_validation_matches_client(self):
        client = _load_client()
        edges = [
            {**noul_item("n_true_false"), "criteria": {"true": "holds", "false": "fails"}},
            {**noul_item("n_null"), "criteria": None},
            {**noul_item("n_yes_no"), "criteria": {"yes": "y", "no": "n"}},
            {**noul_item("n_one_key"), "criteria": {"true": "holds"}},
            {**choice_item("c_one_key"), "criteria": {"a": "only"}},
            {**choice_item("c_empty_key"), "criteria": {"": "empty", "b": "fine"}},
            {**choice_item("c_space_key"), "criteria": {" ": "space", "b": "fine"}},
            score_item("s_1", ["only"]),
            score_item("s_11", [f"l{i}" for i in range(11)]),
            score_item("s_dict", {"a": "b"}),
            score_item("s_empty_level", ["low", " "]),
            score_item("s_2", ["low", "high"]),
            score_item("s_10", [f"l{i}" for i in range(10)]),
            {**noul_item(" "), },
            {**noul_item("empty_ctx"), "context": " "},
            {**noul_item("extra_key"), "evidence": "raw"},
        ]
        for item in edges:
            with self.subTest(id=item["id"]):
                if decide.item_error(item) is None:
                    client.request_body({"reviewed_head": HEAD, "items": [item]}, "jev-1")

    def test_ladder_reports_consent_metadata(self):
        with (JevStub(tops={"low1": 0.5, "low2": 0.5}) as laya,
              JevStub(model="typesafe-1") as remote):
            extra = {"JEV_LAYA_URL": laya.url,
                     "JEV_TYPESAFE_URL": f"http://127.0.0.1:{remote.port}",
                     "TYPESAFE_API_KEY": SENTINEL}
            granted = self.grant_typesafe(**extra)
            with_record, _ = self.ladder([choice_item("low1"), choice_item("low2")], **extra)
            no_record, _ = self.ladder([choice_item("low1")],
                                       XDG_CONFIG_HOME=str(self.tmp / "other"), **extra)
        self.assertEqual(with_record["consent_used"],
                         [{"backend": "typesafe", "granted": granted["consent"]}])
        self.assertEqual(with_record["items"]["low1"]["decided_by"], "typesafe")
        self.assertEqual(no_record["consent_used"], [])
        self.assertEqual(no_record["remote_available"], ["typesafe"])
        self.assertEqual(no_record["items"]["low1"]["decided_by"], "own_reasoning")

    def test_detect_reports_probe(self):
        with JevStub() as laya, JevStub(model="typesafe-1") as remote:
            out = self.run_cli(["detect"], JEV_LAYA_URL=laya.url,
                               JEV_TYPESAFE_URL=f"http://127.0.0.1:{remote.port}",
                               TYPESAFE_API_KEY=SENTINEL)
            self.assertEqual(out.returncode, 0, out.stderr)
            report = json.loads(out.stdout)
        self.assertNotIn(SENTINEL, out.stdout + out.stderr)
        self.assertEqual(report["client"]["path"], str(REPO_CLIENT))
        self.assertIn(str(REPO_CLIENT), report["client"]["tried"])
        self.assertEqual(set(report["backends"]), {"laya", "typesafe", "opencode"})
        for entry in report["backends"].values():
            self.assertLessEqual(set(entry), _PUBLIC_BACKEND_KEYS)
        self.assertTrue(report["backends"]["laya"]["usable"])
        self.assertIsInstance(report["status"], str)
        scripts = _isolated_decide(self.tmp)
        out = subprocess.run([sys.executable, str(scripts / "decide.py"), "detect"],
                             capture_output=True, text=True, check=False,
                             env={"HOME": str(self.tmp / "home"),
                                  "PATH": self.env["PATH"]},
                             cwd=self.tmp, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        report = json.loads(out.stdout)
        self.assertEqual(report["status"], "no_client")
        self.assertEqual(report["backends"], {})
        self.assertIsNone(report["client"]["path"])

    def test_no_key_value_in_detect_or_consent_from_a_leaky_client(self):
        for args in (["detect"], ["consent", "show", "typesafe"],
                     ["consent", "grant", "remote-one"]):
            with self.subTest(args=args):
                out = self.run_cli(args, client=self.fake, JEV_API_KEY=SENTINEL,
                                   FAKE_JEV_LEAK="1")
                self.assertEqual(out.returncode, 0, out.stderr)
                self.assertNotIn(SENTINEL, out.stdout + out.stderr)
                result = json.loads(out.stdout)
                if args == ["detect"]:
                    for entry in result["backends"].values():
                        self.assertLessEqual(set(entry), _PUBLIC_BACKEND_KEYS)
                else:
                    self.assertTrue(result["ok"])
                    self.assertLessEqual(set(result), _PUBLIC_CONSENT_KEYS)

    def test_detect_and_consent_refuse_incompatible_client(self):
        stale = self.tmp / "stale_jev.py"
        stale.write_text(FAKE_CLIENT.replace("CLIENT_PROTOCOL = 2", "CLIENT_PROTOCOL = 1"))
        report = self.cli_json(["detect"], client=stale)
        self.assertEqual(report["status"], "incompatible_client")
        self.assertEqual(report["backends"], {})
        self.assertEqual(report["client"]["path"], str(stale))
        refused = self.cli_json(["consent", "grant", "typesafe"], client=stale)
        self.assertEqual(refused, {"ok": False, "reason": "incompatible_client"})
        self.assertEqual(self.calls(), [], "a client without the protocol line must never run")

    def test_consent_delegated(self):
        with JevStub(model="typesafe-1") as remote:
            url = f"http://127.0.0.1:{remote.port}"
            granted = self.grant_typesafe(JEV_TYPESAFE_URL=url, TYPESAFE_API_KEY=SENTINEL)
            self.assertTrue(granted["ok"])
            record = self.tmp / "home" / ".config" / "ai-kit" / "jev-consent.json"
            self.assertTrue(record.is_file())
            shown = self.cli_json(["consent", "show", "typesafe"], JEV_TYPESAFE_URL=url)
            self.assertEqual(shown["consent"], granted["consent"])
            self.assertTrue(shown["file"].startswith(str(self.tmp)))
            moved = f"http://127.0.0.2:{remote.port}"
            shown_moved = self.cli_json(["consent", "show", "typesafe"],
                                        JEV_TYPESAFE_URL=moved)
            self.assertIsNone(shown_moved["consent"])
            revoked = self.cli_json(["consent", "revoke", "typesafe"], JEV_TYPESAFE_URL=url)
            self.assertTrue(revoked["ok"])
            shown_after = self.cli_json(["consent", "show", "typesafe"],
                                        JEV_TYPESAFE_URL=url)
            self.assertIsNone(shown_after["consent"])
        laya_grant = self.cli_json(["consent", "grant", "laya"])
        self.assertEqual(laya_grant, {"ok": False, "reason": "not_remote"})

    def test_second_opinion_skips_laya(self):
        with JevStub() as laya, JevStub(model="typesafe-1") as remote:
            extra = {"JEV_LAYA_URL": laya.url,
                     "JEV_TYPESAFE_URL": f"http://127.0.0.1:{remote.port}",
                     "TYPESAFE_API_KEY": SENTINEL}
            self.grant_typesafe(**extra)
            result, _ = self.ladder([choice_item("sure1")], "--second-opinion", **extra)
            laya_requests = list(laya.requests)
        self.assertEqual(laya_requests, [], "--skip-local must make zero local requests")
        self.assertIsNone(result["items"]["sure1"].get("laya"),
                          "the local rung was skipped: no column answer at all")
        self.assertEqual(result["items"]["sure1"]["decided_by"], "typesafe")

    def test_score_item_through_ladder(self):
        with JevStub() as laya:
            result, _ = self.ladder([score_item("sev")], JEV_LAYA_URL=laya.url)
            bodies = laya.bodies
        answer = result["items"]["sev"]["laya"]
        self.assertEqual(answer["choice"], "high", "the winning level, not the index")
        self.assertEqual(answer["model"], "laya-rl-agent")
        self.assertFalse(answer["fallback"])
        self.assertEqual(result["items"]["sev"]["decided_by"], "laya")
        self.assertEqual(list(bodies[0]["questions"]), ["sev"])
        for bad in (["only"], [f"l{i}" for i in range(11)]):
            with JevStub() as laya:
                result, _ = self.ladder([score_item("sev", bad)], JEV_LAYA_URL=laya.url)
                posts = laya.posts
            self.assertEqual(result["items"]["sev"]["reason"], "bad_criteria")
            self.assertEqual(posts, [], "a rejected score item must never reach the client")

    def test_invalid_item_rejected_alone(self):
        with JevStub() as laya:
            result, _ = self.ladder([choice_item("bad", context=""), choice_item("good")],
                                    JEV_LAYA_URL=laya.url)
            bodies = laya.bodies
        self.assertEqual(result["items"]["bad"]["reason"], "empty_context")
        self.assertEqual([sorted(body["questions"]) for body in bodies], [["good"]])

    def test_unusable_stdin_exits_2(self):
        self.assertEqual(self.run_cli(["ladder"], "not json").returncode, 2)
        self.assertEqual(self.run_cli(["ladder"], '{"items": []}').returncode, 2)


class TestRealClientSmoke(_TmpHome):
    def test_real_client_answers_disabled_shape_without_backends(self):
        out = subprocess.run([sys.executable, "-B", str(REPO_CLIENT)], input="{}",
                             capture_output=True, text=True,
                             env={"PATH": self.env["PATH"]}, check=False, timeout=30)
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

    @staticmethod
    def _engine_at(root: Path) -> str:
        path = root / "gsd-core" / "bin" / "lib" / "edge-probe.cjs"
        path.parent.mkdir(parents=True)
        path.write_text("")
        return str(path)

    def test_project_local_engine_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._engine_at(Path(tmp) / "proj" / ".claude")
            env = {"HOME": str(Path(tmp) / "home"), "RUNTIME_DIR": str(Path(tmp) / "proj")}
            self.assertEqual(edge_floor.find_engine(env, tmp, None), engine)

    def test_project_local_beats_host_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._engine_at(Path(tmp) / "home" / ".claude")
            local = self._engine_at(Path(tmp) / "proj")
            env = {"HOME": str(Path(tmp) / "home"), "RUNTIME_DIR": str(Path(tmp) / "proj")}
            self.assertEqual(edge_floor.find_engine(env, tmp, None), local)

    def test_gsd_run_on_path_is_last_resort(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = self._engine_at(Path(tmp) / "elsewhere")
            launcher = Path(engine).parent.parent / "gsd_run"
            launcher.write_text("#!/bin/sh\n")
            launcher.chmod(0o755)
            env = {"HOME": str(Path(tmp) / "home"), "RUNTIME_DIR": str(Path(tmp) / "proj"),
                   "PATH": str(launcher.parent)}
            self.assertEqual(edge_floor.find_engine(env, tmp, None), engine)


if __name__ == "__main__":
    unittest.main()
