"""Recording fakes for the codebase-memory-mcp and graphify CLIs used by the index step (30-01).

Helper only, not a test module. Each fake appends each call to a log in the
`tests.host_fakes.fake_calls` format plus `cwd` and an `event` key: a `start` line before
acting and an `end` line with `rc` after. State is a JSON file (absent or `{}` means
defaults). Keys: `cbm_fail` ([rc, stderr line]: fails `index_repository`), `cbm_raw` (string
printed verbatim by `index_repository`), `cbm_projects` (list of project roots that
`list_projects` pages through, 500 a page; absent means the checkout alone), `cbm_query_fail`
([rc, stderr line]: fails `query_graph`), `cbm_query_raw` (string printed verbatim by
`query_graph`), `cbm_query_budget` (max rows per `query_graph` page, like the real output
budget; pages carry `next_offset`), `cbm_delete_fail` ([rc, stderr line]: fails `delete_project`;
a successful one drops the project from `cbm_projects`), `graphify_fail` ([rc, stderr line] or
null), `graphify_no_graph` (exit 0, write nothing), `delay_s` (sleep before acting).

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


def name_of(root):
    return root.lstrip("/").replace("/", "-")


def in_list_items(query):
    """Quoted items of the first IN [...] list; a backslash escapes the next character."""
    start = query.find("IN [")
    if start < 0:
        return []
    items, cur, inside, i = [], [], False, start + 4
    while i < len(query):
        char = query[i]
        if not inside:
            if char == "]":
                break
            if char == "'":
                inside, cur = True, []
        elif char == "\\":
            i += 1
            cur.append(query[i])
        elif char == "'":
            inside = False
            items.append("".join(cur))
        else:
            cur.append(char)
        i += 1
    return items


def cbm(state):
    opts = dict(zip(ARGV[2::2], ARGV[3::2]))
    if ARGV[:2] == ["cli", "index_repository"]:
        if state.get("cbm_fail"):
            return state["cbm_fail"][0], "", state["cbm_fail"][1] + "\n"
        if state.get("cbm_raw") is not None:
            return 0, state["cbm_raw"], ""
        root = os.path.realpath(os.path.join(CWD, opts.get("--repo-path", ".")))
        data = {"project": name_of(root), "excluded": {"dirs": [".git"], "count": 1,
                                                      "truncated": False},
                "not_indexed_files_count": 0, "skipped_count": 0, "parse_partial_count": 0,
                "parse_unusable_count": 0, "nodes": 32, "edges": 47, "status": "indexed"}
        return 0, json.dumps(data) + "\n", ""
    if ARGV[:2] == ["cli", "list_projects"]:
        roots = state.get("cbm_projects")
        if not isinstance(roots, list):
            roots = [os.path.realpath(CWD)]
        limit = min(int(opts.get("--limit", "50")), 500)
        offset = int(opts.get("--offset", "0"))
        page = roots[offset:offset + limit]
        rows = [{"name": name_of(root), "root_path": root, "branch": "main"} for root in page]
        data = {"projects": rows, "total": len(roots), "offset": offset, "limit": limit,
                "returned": len(page), "has_more": offset + len(page) < len(roots)}
        return 0, json.dumps(data) + "\n", ""
    if ARGV[:2] == ["cli", "query_graph"]:
        if state.get("cbm_query_fail"):
            return state["cbm_query_fail"][0], "", state["cbm_query_fail"][1] + "\n"
        if state.get("cbm_query_raw") is not None:
            return 0, state["cbm_query_raw"], ""
        cap = int(opts.get("--max-rows", "200"))
        rows = []
        for item in in_list_items(opts.get("--query", "")):
            path = os.path.join(CWD, item)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    match = re.match(r"^(\s*)(def|class)\s+([A-Za-z_]\w*)", line)
                    if match:
                        rows.append([item, match.group(3)])
        offset = int(opts.get("--offset", "0"))
        budget = state.get("cbm_query_budget")  # rows per page before the output budget cuts
        take = min(cap, budget) if budget else cap
        page = rows[offset:offset + take]
        more = offset + len(page) < len(rows)
        data = {"columns": ["f.file_path", "f.name"], "rows": page,
                "returned": len(page), "total": len(rows),
                "total_relation": "eq", "has_more": more, "truncated": more}
        if more:
            data["truncation_reason"] = "output_budget" if take < cap else "max_rows"
            data["next_offset"] = offset + len(page)
        return 0, json.dumps(data) + "\n", ""
    if ARGV[:2] == ["cli", "delete_project"]:
        if state.get("cbm_delete_fail"):
            return state["cbm_delete_fail"][0], "", state["cbm_delete_fail"][1] + "\n"
        roots = state.get("cbm_projects")
        if not isinstance(roots, list):
            roots = [os.path.realpath(CWD)]
        keep = [root for root in roots if name_of(root) != opts.get("--project")]
        state["cbm_projects"] = keep
        with open(STATE, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        return 0, json.dumps({"status": "deleted", "deleted": len(roots) - len(keep)}) + "\n", ""
    return 2, "", f"codebase-memory-mcp fake: unknown argv {ARGV}\n"


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
    if NAME == "codebase-memory-mcp":
        rc, out, err = cbm(state)
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
    """Write the codebase-memory-mcp and graphify fakes into `bin_dir`."""
    bin_dir = Path(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    for name in ("codebase-memory-mcp", "graphify"):
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
    found = shutil.which("codebase-memory-mcp", path=result)
    if found is None or Path(found).parent != Path(bin_dir):
        raise AssertionError(f"codebase-memory-mcp fake not first on PATH: {found}")
    return result


def no_tool_path(directory) -> str:
    """A PATH holding only git, so `codebase-memory-mcp` and `graphify` are not found."""
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
