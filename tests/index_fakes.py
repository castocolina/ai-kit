"""Recording fakes for the codegraph and graphify CLIs used by the index step (30-01).

Helper only, not a test module. Both fakes append each call to a log in the
`tests.host_fakes.fake_calls` format plus `cwd` and an `event` key: a `start` line before
acting and an `end` line with `rc` after. State is a JSON file (absent or `{}` means
defaults). Keys: `codegraph_status` (object keyed by absolute cwd; a status object, or the
string `unreadable`), `codegraph_fail` (verb -> [rc, stderr line]), `delay_s` (sleep before
acting), `graphify_fail` ([rc, stderr line] or null), `graphify_no_graph` (exit 0, write
nothing), `explore_raw` (string printed verbatim by `codegraph explore`, or null).

`graphify update .` writes `graphify-out/graph.json` with `built_at_commit` (full HEAD sha),
one node per tracked path not excluded by the root `.graphifyignore`, plus small
`graph.html` and `GRAPH_REPORT.md`.
"""

import json
import os
import shutil
import stat
import sys
from pathlib import Path

_FAKE = r'''#!@PY@
import json
import os
import re
import subprocess
import sys
import time

NAME = os.path.basename(sys.argv[0])
LOG = @LOG@
STATE = @STATE@
ARGV = sys.argv[1:]
CWD = os.getcwd()


def load_state():
    try:
        with open(STATE, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def record(event, rc=None):
    entry = {"name": NAME, "argv": ARGV, "cwd": CWD, "event": event}
    if rc is not None:
        entry["rc"] = rc
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def git(*args):
    return subprocess.run(["git", "-C", CWD, *args], capture_output=True, text=True,
                          check=False).stdout


def codegraph(state):
    verb = ARGV[0] if ARGV else ""
    if ARGV[:2] == ["init", "-y"]:
        os.makedirs(os.path.join(CWD, ".codegraph"), exist_ok=True)
        with open(os.path.join(CWD, ".codegraph", ".gitignore"), "w", encoding="utf-8") as h:
            h.write("*\n!.gitignore\n")
        return 0, "", ""
    if verb in ("sync", "index"):
        fail = (state.get("codegraph_fail") or {}).get(verb)
        if fail:
            return fail[0], "", fail[1] + "\n"
        return 0, "", ""
    if verb == "status":
        status = (state.get("codegraph_status") or {}).get(CWD)
        if status == "unreadable":
            return 1, "not json\n", ""
        if status is None:
            if os.path.isdir(os.path.join(CWD, ".codegraph")):
                status = {"initialized": True,
                          "pendingChanges": {"added": 0, "modified": 0, "removed": 0},
                          "worktreeMismatch": None, "index": {"reindexRecommended": False}}
            else:
                status = {"initialized": False}
        return 0, json.dumps(status) + "\n", ""
    if verb == "explore":
        if state.get("explore_raw") is not None:
            return 0, state["explore_raw"], ""
        query = " ".join(ARGV[1:])
        out = [f"**Exploration: {query}**"]
        for token in query.split():
            path = os.path.join(CWD, token)
            if not os.path.isfile(path):
                continue
            items = []
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    match = re.match(r"^(\s*)(def|class)\s+([A-Za-z_]\w*)", line)
                    if match:
                        kind = "class" if match.group(2) == "class" else (
                            "method" if match.group(1) else "function")
                        items.append(f"{match.group(3)}({kind})")
            shown = items[:6]
            if len(items) > 6:
                shown.append(f"+{len(items) - 6} more")
            out.append(f"**`{token}`** — " + ", ".join(shown))
        return 0, "\n".join(out) + "\n", ""
    return 2, "", f"codegraph fake: unknown argv {ARGV}\n"


def graphify(state):
    if ARGV == ["--version"]:
        return 0, "graphify 0.0.0-fake\n", ""
    if ARGV != ["update", "."]:
        return 2, "", f"graphify fake: unknown argv {ARGV}\n"
    if state.get("graphify_fail"):
        return state["graphify_fail"][0], "", state["graphify_fail"][1] + "\n"
    if state.get("graphify_no_graph"):
        return 0, "", ""
    ignore = []
    try:
        with open(os.path.join(CWD, ".graphifyignore"), encoding="utf-8") as handle:
            ignore = [line.strip() for line in handle if line.strip()]
    except OSError:
        pass
    paths = [p for p in git("ls-files").splitlines()
             if not any(p.startswith(prefix) for prefix in ignore)]
    graph = {"built_at_commit": git("rev-parse", "HEAD").strip(),
             "nodes": [{"id": p, "source_file": p} for p in paths], "edges": []}
    out_dir = os.path.join(CWD, "graphify-out")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "graph.json"), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(graph, indent=1, sort_keys=True))
    with open(os.path.join(out_dir, "graph.html"), "w", encoding="utf-8") as handle:
        handle.write("<html><body>fake graph</body></html>\n")
    with open(os.path.join(out_dir, "GRAPH_REPORT.md"), "w", encoding="utf-8") as handle:
        handle.write("# Fake graph report\n")
    return 0, "", ""


def main():
    state = load_state()
    record("start")
    if state.get("delay_s"):
        time.sleep(float(state["delay_s"]))
    if NAME == "codegraph":
        rc, out, err = codegraph(state)
    else:
        rc, out, err = graphify(state)
    record("end", rc)
    sys.stdout.write(out)
    sys.stderr.write(err)
    return rc


sys.exit(main())
'''


def fakes_dir(home) -> Path:
    """The fake-bin directory for a scratch HOME, outside that HOME."""
    home = Path(home)
    return home.parent / (home.name + "-index-fakes")


def write_index_fakes(bin_dir, state_path, log_path) -> str:
    """Write the `codegraph` and `graphify` fakes into `bin_dir`; return the bin dir."""
    bin_dir = Path(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    for name in ("codegraph", "graphify"):
        body = (_FAKE.replace("@PY@", sys.executable)
                .replace("@LOG@", repr(str(log_path)))
                .replace("@STATE@", repr(str(state_path))))
        target = bin_dir / name
        target.write_text(body, encoding="utf-8")
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(bin_dir)


def tool_path(bin_dir, base=None) -> str:
    """`bin_dir` first, then `base` (default: the current PATH); the fakes must win."""
    result = str(bin_dir) + os.pathsep + (base if base is not None else os.environ.get("PATH", ""))
    found = shutil.which("codegraph", path=result)
    if found is None or Path(found).parent != Path(bin_dir):
        raise AssertionError(f"codegraph fake not first on PATH: {found}")
    return result


def no_tool_path(directory) -> str:
    """A PATH holding only git, so `codegraph` and `graphify` are not found."""
    bin_dir = Path(directory) / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    git_bin = shutil.which("git")
    if git_bin is None:
        raise AssertionError("git is required on PATH for the no-tool fixture")
    link = bin_dir / "git"
    if not link.exists():
        link.symlink_to(git_bin)
    return str(bin_dir)


def set_state(state_path, **fields) -> None:
    """Merge `fields` into the JSON state file (created when absent)."""
    path = Path(state_path)
    state = {}
    if path.is_file():
        state = json.loads(path.read_text(encoding="utf-8"))
    state.update(fields)
    path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")


def index_calls(log_path) -> list[dict]:
    """The `start` events the index fakes logged, oldest first."""
    path = Path(log_path)
    if not path.is_file():
        return []
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return [entry for entry in entries if entry.get("event") == "start"]
