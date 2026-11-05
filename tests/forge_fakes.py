"""Stateful fakes for the forge CLIs (gh and gh stack) used by the unit-flow tests.

Helper only, not a test module. The fake `gh` appends each call to a log in the
`tests.host_fakes.fake_calls` format (`{"name": "gh", "argv": [...]}`), keeps PR state in a
JSON file, and runs git for real against the bare remote, so pushes and merges land in the
fixture. Every `gh pr` verb must name `--repo ai-kit-fixture/demo`; the fake never reads
GH_TOKEN.

gh-stack 0.3.0 flags (from --help, read-only; captured in tmp/p29.1/01/gh-stack-help.txt):
  gh stack init [branches...] [-b|--base string]
  gh stack add [branch]
  gh stack submit [--auto] [--open] [--no-atomic] [--remote string]
  gh stack push [--no-atomic] [--remote string]
  gh stack link <stack-number | branch-or-pr> <branch-or-pr> [...] [--base string] [--open]
                [--no-atomic] [--remote string]
  gh stack rebase [--abort] [--continue] [--downstack] [--upstack] [--no-trunk] [--remote string]
  gh stack merge [--merge] [--merge-method string] [--squash] [--rebase] [-y|--yes]
  gh stack view [--json] [-s|--short]
Misuse as gh-stack 0.3.0 answers it (probed live, read-only): `link` with fewer than two
branch-or-PR arguments exits 1 with "requires at least 2 arg(s), only received N" on stderr;
`merge` with two positionals exits 1 with "accepts at most 1 arg(s), received 2"; a second
`init` on a branch already in a stack exits 5 with "current branch ... is already part of a
stack".
gh pr flags (from --help, read-only; captured in tmp/p29.1/01/gh-help.txt):
  pr create -B/--base, -H/--head, -d/--draft, -t/--title, -F/--body-file, -R/--repo
  pr edit -B/--base, -F/--body-file, -t/--title, -R/--repo
  pr view --json fields, -R/--repo; pr ready, -R/--repo; pr close, -R/--repo
Opt-in PR fields (set with set_pr): `rollup` replaces statusCheckRollup (CheckRun and
StatusContext shapes), `mergeable` replaces MERGEABLE, `headRefOid` replaces the head sha,
`hold_merge` makes `pr merge` exit 0 and leave the PR OPEN (a merge queue).
Stacked-PR merges as GitHub enforces them: `pr merge` on an open PR in the linked stack fails
with GitHub's GraphQL "part of a stack" message; `api --method PUT
repos/OWNER/NAME/pulls/N/merge-async --raw-field merge_method=merge --raw-field sha=<head>`
merges N and its open downstack PRs (sha pins N's head) and answers `pending` with a uuid, and
`api .../merge-async/<uuid>` answers the result: `merged` with the merge sha, or `failed` with a
message. Docs: https://docs.github.com/rest/pulls/pulls#merge-a-pull-request-asynchronously
"""

import json
import sys
from pathlib import Path

REPO = "ai-kit-fixture/demo"

_GH = r'''#!@PY@
import json
import os
import shutil
import subprocess
import sys
import tempfile

LOG = @LOG@
STATE = @STATE@
SIGNED_IN = @SIGNED_IN@
GH_STACK = @GH_STACK@
REPO = "ai-kit-fixture/demo"
REFUSED_WITH_MERGE = ("--squash", "--rebase", "--auto")
VALUED_STACK_FLAGS = ("--base", "-b", "--remote", "--merge-method")
STACKED_SYNC_MERGE = ("GraphQL: This pull request is part of a stack and must be merged using the "
                      "asynchronous merge REST API. For more information, see "
                      "https://docs.github.com/rest/pulls/pulls"
                      "#merge-a-pull-request-asynchronously (mergePullRequest)")


def load():
    with open(STATE, encoding="utf-8") as handle:
        return json.load(handle)


def save(state):
    temp = STATE + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(state, handle)
    os.replace(temp, STATE)


def done(argv, code, extra=None):
    record = {"name": "gh", "argv": argv}
    if extra:
        record.update(extra)
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    sys.exit(code)


def fail(argv, message, code=1):
    sys.stderr.write(message + "\n")
    done(argv, code)


def value(flag, args):
    if flag in args:
        index = args.index(flag)
        if index + 1 < len(args):
            return args[index + 1]
    return None


def positionals(args):
    out, skip = [], False
    for item in args:
        if skip:
            skip = False
            continue
        if item in VALUED_STACK_FLAGS:
            skip = True
            continue
        if not item.startswith("-"):
            out.append(item)
    return out


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def bare_path():
    return git("ls-remote", "--get-url", "origin").stdout.strip()


def find_pr(state, number):
    for pr in state["prs"]:
        if pr["number"] == number:
            return pr
    return None


def new_pr(state, head, base, title, body, draft):
    number = state["next"]
    state["next"] = number + 1
    pr = {"number": number, "state": "OPEN", "isDraft": draft, "baseRefName": base,
          "headRefName": head, "title": title or head, "body": body, "checks": "SUCCESS"}
    state["prs"].append(pr)
    return pr


def merge_pr(state, pr, expect=None):
    """Merge the PR's head into its base on the bare remote; return the merge sha or None."""
    if pr["state"] != "OPEN" or pr["isDraft"] or pr["checks"] != "SUCCESS":
        return None
    bare = bare_path()
    head_tip = git("--git-dir", bare, "rev-parse", "--verify", "-q",
                   f"refs/heads/{pr['headRefName']}").stdout.strip()
    if not head_tip or (expect is not None and head_tip != expect):
        return None
    temp = tempfile.mkdtemp(prefix="forge-merge-")
    try:
        clone = os.path.join(temp, "clone")
        subprocess.run(["git", "clone", "-q", bare, clone], check=True, capture_output=True)
        base = pr["baseRefName"]
        subprocess.run(["git", "-C", clone, "checkout", "-q", base], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", clone, "merge", "--no-ff", "-q", "-m",
                        f"Merge pull request #{pr['number']}",
                        f"origin/{pr['headRefName']}"], check=True, capture_output=True)
        subprocess.run(["git", "-C", clone, "push", "-q", "origin", base], check=True,
                       capture_output=True)
        sha = subprocess.run(["git", "-C", clone, "rev-parse", "HEAD"], capture_output=True,
                             text=True, check=True).stdout.strip()
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    pr["state"], pr["mergeCommit"] = "MERGED", {"oid": sha}
    return sha


def stack_order(state):
    return [item["pr"] for item in (state.get("stack") or {}).get("branches", [])]


def pr_verb(argv, verb, args):
    if value("--repo", args) != REPO:
        fail(argv, f"fake gh: --repo must be {REPO}, got {value('--repo', args)!r}")
    state = load()
    if verb == "create":
        base, head = value("--base", args), value("--head", args)
        if not base or not head:
            fail(argv, "fake gh: create needs --base and --head")
        body_file = value("--body-file", args)
        body = open(body_file, encoding="utf-8").read() if body_file else ""
        pr = new_pr(state, head, base, value("--title", args), body, "--draft" in args)
        save(state)
        sys.stderr.write("Warning: 1 uncommitted change\n")  # real gh warns on stderr
        print(f"https://github.com/{REPO}/pull/{pr['number']}")
        done(argv, 0)
    if verb == "list":
        head = value("--head", args)
        found = [{"number": pr["number"]} for pr in state["prs"]
                 if pr["headRefName"] == head and pr["state"] == "OPEN"]
        print(json.dumps(found))
        done(argv, 0)
    positional = [item for item in args if not item.startswith("-")]
    number = int(positional[0]) if positional and positional[0].isdigit() else None
    pr = find_pr(state, number) if number is not None else None
    if pr is None:
        fail(argv, f"fake gh: no pull request {positional[:1]}")
    if verb == "edit":
        if state.get("fail_edit_once"):
            state["fail_edit_once"] = False
            save(state)
            fail(argv, "fake gh: transient edit failure")
        if value("--base", args):
            pr["baseRefName"] = value("--base", args)
        if value("--title", args):
            pr["title"] = value("--title", args)
        if value("--body-file", args):
            pr["body"] = open(value("--body-file", args), encoding="utf-8").read()
        save(state)
        done(argv, 0)
    if verb == "ready":
        pr["isDraft"] = False
        save(state)
        done(argv, 0)
    if verb == "close":
        if pr["state"] != "OPEN":
            fail(argv, f"fake gh: pull request #{number} is not open")
        pr["state"] = "CLOSED"
        save(state)
        done(argv, 0)
    if verb == "view":
        fields = (value("--json", args) or "").split(",")
        data = {}
        for field in fields:
            if field == "statusCheckRollup":
                data[field] = pr.get("rollup") or [{"conclusion": pr["checks"]}]
            elif field == "mergeable":
                data[field] = pr.get("mergeable", "MERGEABLE")
            elif field == "headRefOid":
                data[field] = pr.get("headRefOid") or git(
                    "--git-dir", bare_path(), "rev-parse", "--verify", "-q",
                    f"refs/heads/{pr['headRefName']}").stdout.strip()
            elif field == "url":
                data[field] = f"https://github.com/{REPO}/pull/{pr['number']}"
            else:
                data[field] = pr.get(field)
        print(json.dumps(data))
        done(argv, 0)
    if verb == "merge":
        if "--merge" not in args or value("--match-head-commit", args) is None:
            fail(argv, "fake gh: merge needs --merge and --match-head-commit")
        if pr["number"] in stack_order(state) and pr["state"] == "OPEN":
            fail(argv, STACKED_SYNC_MERGE)
        if pr.get("hold_merge"):
            save(state)
            done(argv, 0)
        sha = merge_pr(state, pr, value("--match-head-commit", args))
        if sha is None:
            fail(argv, "fake gh: merge refused (not open, draft, checks, or head moved)")
        save(state)
        print(sha)
        done(argv, 0)
    fail(argv, f"fake gh: unknown pr verb {verb}")


def stack_verb(argv, args):
    state = load()
    verb, rest = (args[0] if args else ""), args[1:]
    if verb == "init":
        current = git("branch", "--show-current").stdout.strip()
        if current in [item["branch"] for item in (state.get("stack") or {}).get("branches", [])]:
            fail(argv, f'\u2717 current branch "{current}" is already part of a stack', 5)
        base = value("--base", rest) or value("-b", rest) or "main"
        state["stack"] = {"base": base, "branches": [
            {"branch": item, "pr": None} for item in positionals(rest)]}
        save(state)
        done(argv, 0)
    if verb == "add":
        stack = state["stack"] or {"base": "main", "branches": []}
        stack["branches"].append({"branch": positionals(rest)[0], "pr": None})
        state["stack"] = stack
        save(state)
        done(argv, 0)
    stack = state.get("stack") or {"base": "main", "branches": []}
    state["stack"] = stack
    names = [item["branch"] for item in stack["branches"]]
    if verb == "submit":
        remote = value("--remote", rest) or "origin"
        pushed = git("push", "--atomic", "--force", remote, *names)
        if pushed.returncode != 0:
            fail(argv, pushed.stderr.strip())
        for index, item in enumerate(stack["branches"]):
            base = stack["base"] if index == 0 else names[index - 1]
            existing = [pr for pr in state["prs"]
                        if pr["headRefName"] == item["branch"] and pr["state"] == "OPEN"]
            if existing:
                existing[0]["baseRefName"] = base
                existing[0]["isDraft"] = existing[0]["isDraft"] and "--open" not in rest
                item["pr"] = existing[0]["number"]
            else:
                pr = new_pr(state, item["branch"], base, item["branch"], "",
                            "--open" not in rest)
                item["pr"] = pr["number"]
        save(state)
        done(argv, 0, {"pushed": names})
    if verb == "link":
        items = positionals(rest)
        if len(items) < 2:  # cobra MinimumNArgs(2), checked before anything runs
            fail(argv, f"requires at least 2 arg(s), only received {len(items)}")
        base = value("--base", rest) or stack["base"]
        pushed, chain = [], []
        for item in items:
            number = None
            if "/pull/" in item:
                number = int(item.rsplit("/", 1)[1])
            elif item.isdigit() and find_pr(state, int(item)):
                number = int(item)
            if number is None:
                pushed.append(item)
                if git("push", "--atomic", "origin", item).returncode != 0:
                    fail(argv, f"fake gh: push of {item} failed")
                pr = new_pr(state, item, base, item, "", "--open" not in rest)
                number = pr["number"]
            chain.append(number)
        previous = base
        for number in chain:
            pr = find_pr(state, number)
            pr["baseRefName"] = previous
            if "--open" in rest:
                pr["isDraft"] = False
            previous = pr["headRefName"]
        stack["base"] = base
        stack["branches"] = [{"branch": find_pr(state, n)["headRefName"], "pr": n}
                             for n in chain]
        save(state)
        done(argv, 0, {"pushed": pushed} if pushed else None)
    if verb == "push":
        remote = value("--remote", rest) or "origin"
        pushes = []
        for name in names:
            tip = git("ls-remote", remote, f"refs/heads/{name}").stdout.split()
            pushes.append(f"--force-with-lease=refs/heads/{name}:{tip[0]}" if tip else None)
        leases = [lease for lease in pushes if lease]
        result = git("push", "--atomic", *leases, remote, *names)
        if result.returncode != 0:
            fail(argv, result.stderr.strip())
        done(argv, 0, {"pushed": names})
    if verb == "rebase":
        if "--continue" in rest:
            code = git("rebase", "--continue").returncode
        elif "--abort" in rest:
            code = git("rebase", "--abort").returncode
        else:
            git("checkout", "-q", names[-1])
            code = git("rebase", "--update-refs", stack["base"]).returncode
        done(argv, 1 if code else 0)
    if verb == "merge":
        if any(flag in rest for flag in REFUSED_WITH_MERGE):
            fail(argv, "fake gh: stack merge only merges")
        targets = positionals(rest)
        if len(targets) > 1:  # cobra MaximumNArgs(1)
            fail(argv, f"accepts at most 1 arg(s), received {len(targets)}")
        order = [item["pr"] for item in stack["branches"]]
        if targets and not targets[0].isdigit():
            fail(argv, f"invalid stack or pull request number: {targets[0]}")
        target = int(targets[0]) if targets else (order[-1] if order else None)
        if target not in order:
            fail(argv, "fake gh: target is not in the stack")
        for number in order[:order.index(target) + 1]:
            pr = find_pr(state, number)
            if pr["isDraft"]:
                fail(argv, f"fake gh: pull request #{number} is still a draft")
        for number in order[:order.index(target) + 1]:
            pr = find_pr(state, number)
            pr["baseRefName"] = stack["base"]
            if merge_pr(state, pr) is None:
                fail(argv, f"fake gh: merge of #{number} refused")
        save(state)
        done(argv, 0)
    if verb == "view":
        for item in stack["branches"]:
            print(f"{item['branch']} {item['pr']}")
        done(argv, 0)
    fail(argv, f"fake gh: unknown stack verb {verb}")


def api_verb(argv, args):
    """PUT .../pulls/N/merge-async merges N and its open downstack PRs, returns pending and a
    uuid; GET .../merge-async/<uuid> returns the stored result (merged, or failed + message)."""
    method, fields, path, items = "GET", {}, None, iter(args)
    for item in items:
        if item in ("--method", "-X"):
            method = next(items, "")
        elif item in ("-f", "--raw-field", "-F", "--field"):
            key, _, val = next(items, "").partition("=")
            fields[key] = val
        elif not item.startswith("-"):
            path = item
    prefix = f"repos/{REPO}/pulls/"
    parts = path[len(prefix):].split("/") if path and path.startswith(prefix) else []
    state = load()
    pr = find_pr(state, int(parts[0])) if parts and parts[0].isdigit() else None
    if pr is None or parts[1:2] != ["merge-async"]:
        fail(argv, "gh: Not Found (HTTP 404)")
    results = state.setdefault("async", {})
    if method == "GET" and len(parts) == 3:
        if parts[2] not in results:
            fail(argv, "gh: Not Found (HTTP 404)")
        print(json.dumps(results[parts[2]]))
        done(argv, 0)
    if method != "PUT" or len(parts) != 2:
        fail(argv, "gh: Not Found (HTTP 404)")
    if fields.get("merge_method", "merge") != "merge":
        fail(argv, "fake gh: merge-async only merges")
    order = stack_order(state)
    chain = order[:order.index(pr["number"]) + 1] if pr["number"] in order else [pr["number"]]
    chain = [n for n in chain if find_pr(state, n)["state"] == "OPEN"]
    if any(find_pr(state, n)["isDraft"] for n in chain):
        fail(argv, "gh: Pull request is in draft state (HTTP 400)")
    uuid = f"merge-{pr['number']}"
    refused = [n for n in chain if find_pr(state, n)["checks"] != "SUCCESS"]
    if refused:  # a stack merge is all-or-nothing
        result = {"status": "failed", "details": {"message": f"merge of #{refused[0]} refused"}}
    else:
        # GitHub merges the PR's head once; its open downstack PRs land inside that one merge.
        if pr["number"] in order:
            pr["baseRefName"] = state["stack"]["base"]
        sha = merge_pr(state, pr, fields.get("sha"))
        if sha is None:
            message = f"merge of #{pr['number']} refused"
            result = {"status": "failed", "details": {"message": message}}
        else:
            result = {"status": "merged", "details": {"sha": sha}}
            for number in chain:
                member = find_pr(state, number)
                member["state"], member["mergeCommit"] = "MERGED", {"oid": sha}
    results[uuid] = result
    save(state)
    print(json.dumps({"status": "pending", "details": {"uuid": uuid, "merge_method": "merge"}}))
    done(argv, 0)


argv = sys.argv[1:]
if argv[:2] == ["auth", "status"]:
    done(argv, 0 if SIGNED_IN else 1)
if argv and argv[0] == "stack":
    if not GH_STACK:
        fail(argv, 'unknown command "stack" for "gh"')
    stack_verb(argv, argv[1:])
if argv and argv[0] == "api":
    api_verb(argv, argv[1:])
if len(argv) < 2 or argv[0] != "pr":
    fail(argv, "fake gh: unknown command")
if argv[1] == "merge" and any(flag in argv for flag in REFUSED_WITH_MERGE):
    fail(argv, "fake gh: merge with a squash, rebase or auto flag is refused")
pr_verb(argv, argv[1], argv[2:])
'''


def _script(path_values):
    text = _GH
    for token, value in path_values.items():
        text = text.replace(token, value)
    return text


def write_forge_fakes(bin_dir, state_path, log_path, gh_stack=False, signed_in=True):
    """Write the fake `gh` into `bin_dir` and reset its state file; returns the bin dir.

    Each call overwrites the state file, so a copied fixture starts from an empty forge.
    """
    bin_path = Path(bin_dir)
    bin_path.mkdir(parents=True, exist_ok=True)
    Path(state_path).write_text(
        json.dumps({"prs": [], "bare": None, "next": 1, "stack": None}), encoding="utf-8")
    script = _script({
        "@PY@": sys.executable,
        "@LOG@": repr(str(log_path)),
        "@STATE@": repr(str(state_path)),
        "@SIGNED_IN@": repr(bool(signed_in)),
        "@GH_STACK@": repr(bool(gh_stack)),
    })
    gh = bin_path / "gh"
    gh.write_text(script, encoding="utf-8")
    gh.chmod(0o755)
    return str(bin_path)


def forge_state(state_path):
    """The PR state the fake keeps (a read of the JSON file)."""
    return json.loads(Path(state_path).read_text(encoding="utf-8"))


def fail_next_edit(state_path):
    """Make the next `gh pr edit` fail once (test setup)."""
    state = forge_state(state_path)
    state["fail_edit_once"] = True
    Path(state_path).write_text(json.dumps(state), encoding="utf-8")


def set_pr(state_path, number, **fields):
    """Overwrite fields of one PR in the state file (test setup, not a gh verb)."""
    state = forge_state(state_path)
    for pr in state["prs"]:
        if pr["number"] == number:
            pr.update(fields)
            break
    else:
        raise KeyError(f"no pull request {number}")
    temp = Path(state_path).with_suffix(".tmp")
    temp.write_text(json.dumps(state), encoding="utf-8")
    temp.replace(state_path)
    return state
