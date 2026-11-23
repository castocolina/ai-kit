"""37-19 / SPEC R12, D-24 to D-27: hosted-lane protocol builders and run directory,
run for real under /bin/sh (no herdr).
"""

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from tests.cross_ai_selftest import _real_node_executable

TEMPLATE = REPO / "skills" / "ai-kit-spec-review" / "references" / "cross-ai.mjs"
FIXTURE = REPO / "tests" / "fixtures" / "runner_host_protocol.json"
NODE = _real_node_executable()
PRELUDE = ("const fs = require('node:fs'); const path = require('node:path'); "
           "const os = require('node:os'); const crypto = require('node:crypto'); "
           "const { spawnSync } = require('node:child_process');\n")
BUILD = ("hostToken", "hostLabel", "hostRunDir", "shQuote", "writePrivate", "procStartTime",
         "hostEnvText", "buildLauncher", "writeRunDir", "writeCycleState")
CONSTS = ("HOST_LABEL_PREFIX", "HOST_FILES", "RUN_RECORD_VERSION")


def runner_source(functions, constants=()) -> str:
    lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    parts = [next(line for line in lines if line.startswith(f"const {name} = "))
             for name in constants]
    for name in functions:
        start = next(i for i, line in enumerate(lines)
                     if re.match(rf"^(?:async )?function {name}\(", line))
        line = lines[start]
        end = start if line.endswith("}") and line.count("{") == line.count("}") else next(
            i for i in range(start + 1, len(lines)) if lines[i] == "}")
        parts.extend(lines[start:end + 1])
    return "\n".join(parts)


def run_node(script, *args) -> str:
    assert NODE is not None
    return subprocess.run([NODE, "-e", PRELUDE + script, *args], capture_output=True,
                          text=True, timeout=30, check=True,
                          env={"PATH": os.environ.get("PATH", ""),
                               "AI_KIT_REFUSE_REAL_HOME": "1"}).stdout


def make_run_dir(home, lane) -> dict:
    script = (runner_source(BUILD, CONSTS)
              + "\nconst home = process.argv[1]; const lane = JSON.parse(process.argv[2]);\n"
              + "process.stdout.write(JSON.stringify(writeRunDir(home, hostToken(), lane)));\n")
    return json.loads(run_node(script, str(home), json.dumps(lane)))


def mode(path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


class TestHostProtocol(unittest.TestCase):
    def setUp(self):
        if NODE is None:
            self.skipTest("node not on PATH")
        if not all(os.access(p, os.X_OK) for p in
                   ("/bin/sh", "/usr/bin/env", "/bin/rm", "/bin/mv", "/bin/cat")):
            self.skipTest("needs /bin/sh, /usr/bin/env, /bin/rm, /bin/mv and /bin/cat")

    def lane(self, tmp, argv, input_value=None, **extra):
        return {"role": "execute", "runtime": "pi", "cwd": str(tmp), "bin": "/bin/sh",
                "argv": argv, "env": {"PATH": "/bin"}, "input": input_value, **extra}

    def launch(self, result):
        return subprocess.run(["/bin/sh", result["files"]["launcher"]], capture_output=True,
                              timeout=30, check=True)

    def test_hostile_argv_reaches_the_lane_intact(self):
        values = ["q'uote", 'd"q', "new\nline", "$HOME", "`id`", "back\\slash", "", "sp ace",
                  "-dash", "*", "tab\there", "café"]
        with tempfile.TemporaryDirectory() as tmp:
            lane = self.lane(tmp, ["-c", 'for a; do printf "%s\\036" "$a"; done', "argv0", *values])
            result = make_run_dir(Path(tmp) / "state", lane)
            files = result["files"]
            self.assertFalse(Path(files["prompt"]).exists())
            self.assertIn(" < /dev/null", Path(files["launcher"]).read_text())
            self.launch(result)
            self.assertEqual(Path(files["out"]).read_bytes().split(b"\x1e")[:-1],
                             [v.encode() for v in values])

    def test_nul_element_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = (runner_source(BUILD, CONSTS) + "\n"
                      "const lane = JSON.parse(process.argv[2]);\n"
                      "try { writeRunDir(process.argv[1], hostToken(), lane); } "
                      "catch(e) { console.log(e.message); }\n")
            self.assertEqual(run_node(script, tmp, json.dumps(self.lane(tmp, ["a\0b"])) ).strip(),
                             "argv element holds a NUL byte")
            self.assertFalse((Path(tmp) / "ai-kit").exists())

    def test_label_and_token_grammar(self):
        fixture = json.loads(FIXTURE.read_text())
        script = runner_source(("hostToken", "hostLabel"), ("HOST_LABEL_PREFIX",)) + "\n" + (
            "const a=hostToken(), b=hostToken(); console.log(JSON.stringify([a,b,"
            "...['review','execute'].flatMap(r=>['pi','A'+'b'.repeat(31),'placeholder-cli-1']"
            ".map(x=>hostLabel(r,x,a)))]));")
        a, b, *labels = json.loads(run_node(script))
        self.assertNotEqual(a, b)
        for token in (a, b):
            self.assertRegex(token, fixture["token_pattern"])
        for label in labels:
            self.assertRegex(label, fixture["label"]["pattern"])
            self.assertLessEqual(len(label), 63)

    def test_rc_file_reading(self):
        values = ["0\n", "255", "SIGTERM\n", "", "256", "007", "-1", "sigterm",
                  "ab\x07cd", "x" * 200]
        script = runner_source(("parseRc",))
        script += "\nconsole.log(JSON.stringify(JSON.parse(process.argv[1]).map(parseRc)));"
        actual = json.loads(run_node(script, json.dumps(values)))
        expected = [{"code": 0, "signal": None}, {"code": 255, "signal": None},
                    {"code": None, "signal": "SIGTERM"}, None]
        expected += [{"code": None, "signal": None, "bad": x} for x in
                     ["256", "007", "-1", "sigterm", "abcd", "x" * 80]]
        self.assertEqual(actual, expected)

    def test_start_problem_refuses_unsafe_paths(self):
        script = runner_source(("isExec", "hostStartProblem"), ("HOST_PATH_SAFE", "HOST_TOOLS"))
        script += ("\nconsole.log(JSON.stringify(JSON.parse(process.argv[1])"
                   ".map(hostStartProblem)));")
        result = json.loads(run_node(script, json.dumps(["/srv/a b", "/srv/a'b", "/srv/ok-1/x.y"])))
        self.assertEqual(result,
                         ["state home path holds a character outside [A-Za-z0-9._/-]"] * 2 + [None])

    def test_record_first_then_secret_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = runner_source(BUILD, CONSTS) + "\n" + (
                "const home=process.argv[1], lane=JSON.parse(process.argv[2]);"
                "const token=hostToken(), dir=hostRunDir(home,token), seen=[];"
                "const orig=fs.openSync; fs.openSync=(p,...a)=>{"
                "if(String(p).startsWith(dir+path.sep)) "
                "seen.push(path.basename(String(p))); return orig(p,...a);};"
                "writeRunDir(home,token,lane); console.log(JSON.stringify(seen));")
            seen = json.loads(run_node(script, tmp, json.dumps(self.lane(tmp, [], "prompt"))))
            self.assertTrue(seen[0].startswith(".run.json."))
            self.assertEqual(seen[1:], ["env", "prompt", "launch.sh", "out", "err"])

    def test_proc_start_time(self):
        if not Path("/proc/self/stat").exists():
            self.skipTest("no /proc")
        script = runner_source(("procStartTime",))
        script += ("\nconsole.log(JSON.stringify([procStartTime(process.pid),"
                   "procStartTime(999999999)]));")
        own, absent = json.loads(run_node(script))
        self.assertRegex(own, r"^\d+$")
        self.assertEqual(absent, "-")

    def test_env_file_quotes_values_and_skips_non_shell_names(self):
        script = runner_source(("shQuote", "hostEnvText"))
        script += "\nconsole.log(JSON.stringify(hostEnvText({A:\"x'y\",'B-C':'1',PATH:'/bin'})));"
        result = json.loads(run_node(script))
        self.assertIn("export A='x'\\''y'", result["text"])
        self.assertNotIn("B-C", result["text"])
        self.assertEqual(result["skipped"], 1)
        with tempfile.TemporaryDirectory() as tmp:
            secret = "sk-" + "A" * 24
            lane = self.lane(tmp, [], env={"AIKIT_KEY": secret})
            files = make_run_dir(Path(tmp) / "state", lane)["files"]
            self.assertIn(secret, Path(files["env"]).read_text())
            for name in ("launcher", "run"):
                self.assertNotIn(secret, Path(files[name]).read_text())

    def test_herdr_call_runs_only_listed_verbs(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "herdr"
            binary.write_text('#!/bin/sh\nprintf "%s\\n" "$*"\nexit "${FAKE_EXIT:-0}"\n')
            binary.chmod(0o755)
            script = runner_source(("herdrCall",), ("HERDR_BIN", "HERDR_VERBS", "HERDR_TIMEOUT_MS"))
            script += ("\nprocess.env.PATH=process.argv[1]+':'+process.env.PATH;"
                       "process.env.FAKE_EXIT=process.argv[2];"
                       "let bad; try { herdrCall('pane read',[]); } catch(e) { bad=e.message; }"
                       "console.log(JSON.stringify([herdrCall('tab create',"
                       "['--label','x']),bad]));")
            for code in ("0", "3"):
                result, bad = json.loads(run_node(script, tmp, code))
                self.assertEqual(result["ok"], code == "0")
                self.assertEqual(result["stdout"], "tab create --label x\n")
                self.assertEqual(result["detail"], None if code == "0" else "exit 3")
                self.assertEqual(bad, "herdr verb pane read is not one of "
                                 "tab create, pane run, tab close")

    def test_protocol_fixture_matches_runner(self):
        fixture = json.loads(FIXTURE.read_text())
        script = runner_source(("hostRunDir", "hostTypedLine", "parseRc"),
                               ("HOST_FILES", "HERDR_VERBS", "HOST_LABEL_PREFIX"))
        script += ("\nconsole.log(JSON.stringify({files:HOST_FILES,verbs:HERDR_VERBS,"
                   "prefix:HOST_LABEL_PREFIX,"
                   "runDir:hostRunDir('/H','<token>'),typed:hostTypedLine({launcher:'/X/launch.sh'}),"
                   "rc:JSON.parse(process.argv[1]).map(parseRc)}));")
        values = ["0\n", "255", "SIGTERM\n", "", "256", "007", "-1", "sigterm",
                  "ab\x07cd", "x" * 200]
        result = json.loads(run_node(script, json.dumps(values)))
        self.assertEqual(result["files"], fixture["files"])
        self.assertEqual(result["verbs"], fixture["herdr_verbs"])
        self.assertEqual(result["prefix"], fixture["label"]["prefix"])
        self.assertEqual(result["runDir"], fixture["run_dir"].replace("<state home>", "/H"))
        self.assertEqual(result["typed"],
                         fixture["typed_line"].replace("<launcher path>", "/X/launch.sh"))
        self.assertIn(fixture["verdict"], result["files"])
        for value, parsed in zip(values, result["rc"], strict=True):
            if parsed is not None:
                matches = bool(re.fullmatch(fixture["rc_pattern"], value.removesuffix("\n")))
                self.assertEqual(matches, "bad" not in parsed)

    def test_argv_prompt_never_enters_the_launcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            prompt = "placeholder-prompt-sentinel-1 q'uote\nline two\n"
            lane = self.lane(tmp, ["-c", 'printf "%s" "$1"', "argv0", prompt], promptArg=prompt)
            files = make_run_dir(Path(tmp) / "state", lane)["files"]
            self.assertTrue(Path(files["prompt"]).exists())
            text = Path(files["launcher"]).read_text()
            self.assertNotIn("placeholder-prompt-sentinel-1", text)
            self.assertIn(" < /dev/null", text)
            self.launch({"files": files})
            self.assertEqual(Path(files["out"]).read_bytes(), prompt.encode())
            self.assertFalse(Path(files["prompt"]).exists())

    def test_launcher_leads_its_own_group(self):
        if not Path("/usr/bin/setsid").exists() or not Path("/proc/self/stat").exists():
            self.skipTest("needs setsid and /proc")
        script = runner_source(("procGroup",))
        script += "\nconsole.log(JSON.stringify([procGroup(999999999),procGroup(process.pid)]));"
        absent, own = json.loads(run_node(script))
        self.assertIsNone(absent)
        self.assertGreater(own, 0)
        with tempfile.TemporaryDirectory() as tmp:
            lane = self.lane(tmp, ["-c", 'read -r s < /proc/$$/stat; printf "%s" "$s"'])
            files = make_run_dir(Path(tmp) / "state", lane)["files"]
            self.launch({"files": files})
            fields = Path(files["out"]).read_text().rsplit(")", 1)[1].split()
            self.assertEqual(fields[2], Path(files["pid"]).read_text().strip())

    def test_launcher_runs_the_lane_and_writes_rc(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="xai-host-") as tmp:
            work = Path(tmp) / "work"
            work.mkdir()
            lane = {"role": "execute", "runtime": "placeholder-cli-1", "cwd": str(work),
                    "bin": "/bin/sh", "argv": ["-c", 'IFS= read -r line; '
                        'printf "%s|%s|%s" "$line" "$AIKIT_T1" "${AIKIT_HOST_LEAK:-unset}"'],
                    "env": {"PATH": os.environ.get("PATH", ""), "AIKIT_T1": "from-env"},
                    "input": "prompt-line\n"}
            result = make_run_dir(Path(tmp) / "state", lane)
            files, record = result["files"], result["record"]
            self.assertEqual(format(mode(result["dir"]), "o"), fixture["dir_mode"])
            for name in ("run", "env", "prompt", "launcher", "out", "err"):
                self.assertEqual(format(mode(files[name]), "o"), fixture["file_mode"])
            self.assertEqual(sorted(record), fixture["run_record_fields"])
            self.assertRegex(record["label"], fixture["label"]["pattern"])
            self.assertRegex(record["token"], fixture["token_pattern"])
            for key in ("tab_id", "pane_id", "launcher_pid", "launcher_pgid", "launcher_start"):
                self.assertIsNone(record[key])
            self.assertEqual(record["role"], "execute")
            self.assertEqual(record["runtime"], "placeholder-cli-1")
            self.assertRegex(record["runner_start"], r"^(?:\d+|-)$")
            self.assertEqual(record["version"], 1)
            self.assertEqual(json.loads(Path(files["run"]).read_text()), record)
            proc = subprocess.run(["/bin/sh", files["launcher"]],
                                  env={**os.environ, "AIKIT_HOST_LEAK": "1",
                                       "AIKIT_HOST_CLEAN": "1"},
                                  cwd=tmp, timeout=30, check=False, capture_output=True)
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(Path(files["out"]).read_bytes().decode("utf-8"),
                             "prompt-line|from-env|unset")
            self.assertEqual(Path(files["rc"]).read_text(), "0\n")
            self.assertRegex(Path(files["pid"]).read_text(), r"^\d+\n$")
            self.assertFalse(Path(files["env"]).exists())
            self.assertFalse(Path(files["prompt"]).exists())
            expected = fixture["done_line"].replace("<token>", record["token"]).replace("<rc>", "0")
            self.assertEqual(proc.stdout.decode().splitlines()[-1], expected)
