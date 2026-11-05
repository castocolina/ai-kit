#!/usr/bin/env python3
"""Scripted live check of the unit flow (plan 29.1-06, FLOW-11).

Each run works under a unique run id: it pushes a per-run trunk `<run-id>/main` from the
repository's default branch and names every unit branch, hotfix branch and PR with the run id, so
it never touches another run's work. Two rounds run the same steps. Round 1 uses the gh-stack
backend and fails if any step falls back to plain gh; round 2 forces AI_KIT_FLOW_PR_BACKEND=gh.
Each round builds three stacked units on the per-run trunk through a synthetic adapter (unit and
checkpoint JSON only), starts a hotfix to that trunk, merges it with `merge-chain --unit-id` while
the three PRs stay open, restacks, and runs `merge-chain`. After each round every PR must be
MERGED, every recorded pushed tip must be an ancestor of the remote per-run trunk, the trunk must
have gained a merge commit, and no round branch is left. The merge count is not asserted: GitHub's
merge-async lands a whole stack in one merge, so the stack is one commit and the hotfix another.
At the end, and on failure, the run closes its own open PRs and deletes its own branches and
trunk; a failed cleanup fails it.

  --fixture BARE --workdir DIR
      Local bare remote, used by the tests. The fake gh must be on PATH.
  --live --yes-owner-attended --workdir DIR [--owner LOGIN | --repo OWNER/NAME]
      Owner-attended run on GitHub in one persistent private repo, by default
      <owner>/ai-kit-flow-live. A missing repo is created once and kept; no repo is ever deleted.
      Needs gh signed in with the repo scope. Without --yes-owner-attended it prints the plan and
      exits 2.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import typing
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
FOLD = ROOT / "skills" / "ai-kit-commit-fold" / "scripts" / "fold.py"
FIXTURE_URL = "https://github.com/ai-kit-fixture/demo.git"
FIXTURE_SLUG = "ai-kit-fixture/demo"
LIVE_REPO = "ai-kit-flow-live"
SLUG = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+")
BACKEND_ENV = "AI_KIT_FLOW_PR_BACKEND"
FALLBACK = re.compile(r"pr backend: gh(?!-stack)")
ROUNDS = (None, "gh")  # round 1 unforced (gh-stack), round 2 forced plain gh
UNIT_LETTERS = ("x", "y", "z")
USAGE = (
    "usage: flow_live_check.py (--fixture BARE | --live --yes-owner-attended) --workdir DIR "
    "[--owner LOGIN | --repo OWNER/NAME]"
)


class RunInfo(typing.NamedTuple):
    run_id: str
    slug: str


class LiveFailure(Exception):
    """A step that did not pass. `reason` joins the failure line; `detail` follows it."""

    def __init__(self, step, reason="", detail=""):
        super().__init__(step)
        self.step = step
        self.reason = reason
        self.detail = detail


def _last_line(text):
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _gh(argv):
    return subprocess.run(argv, capture_output=True, text=True, check=False)


class Round:
    """One round of the flow in `repo`. Unforced backend (round 1) is strict: a plain-gh fallback
    fails the step, since that round is the gh-stack proof."""

    def __init__(self, number, repo, workdir, env, info):
        self.number = number
        self.tag = env.get(BACKEND_ENV, "gh-stack")
        self.repo = repo
        self.workdir = workdir
        self.env = env
        self.info = info
        self.strict = BACKEND_ENV not in env

    @property
    def run_id(self):
        return self.info.run_id

    @property
    def slug(self):
        return self.info.slug

    @property
    def trunk(self):
        return trunk_of(self.run_id)

    @property
    def prefix(self):
        return f"live-{self.number}"

    @property
    def hotfix_name(self):
        return f"{self.run_id}-r{self.number}-hotfix"

    def branch(self, letter):
        return f"{self.run_id}/r{self.number}/{letter}"

    @property
    def branches(self):
        return [self.branch(letter) for letter in UNIT_LETTERS] + [f"hotfix/{self.hotfix_name}"]

    def ok(self, what):
        print(f"ok {self.tag} {what}", flush=True)

    def git(self, what, *args):
        proc = subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True,
                              text=True, check=False, env=self.env)
        if proc.returncode != 0:
            raise LiveFailure(f"{self.tag} {what}", detail=_last_line(proc.stderr))
        return proc.stdout

    def fold(self, what, *args):
        proc = subprocess.run([sys.executable, str(FOLD), *args, "--repo", str(self.repo)],
                              capture_output=True, text=True, check=False, env=self.env)
        report = proc.stdout + proc.stderr
        step = f"{self.tag} {what}"
        if proc.returncode != 0:
            # a refusal's reason line (gh's redacted first stderr line) precedes the outcome line
            refusal = [ln.strip() for ln in report.splitlines() if ln.strip().startswith("refused")]
            raise LiveFailure(step, detail=refusal[0] if refusal else _last_line(report))
        fallback = [line.strip() for line in report.splitlines() if FALLBACK.search(line)]
        if self.strict and fallback:
            raise LiveFailure(step, "gh-stack fallback", fallback[0])  # carries gh's stderr
        self.ok(what)

    def commit(self, what, files, message):
        for name, text in files.items():
            (self.repo / name).write_text(text, encoding="utf-8")
        self.git(f"add {what}", "add", "--", *files)
        self.git(f"commit {what}", "commit", "-q", "-m", message)

    def entry(self, unit_id):
        record = json.loads((self.repo / ".git" / "ai-kit-stack.json").read_text(encoding="utf-8"))
        for entry in record["units"]:
            if entry["id"] == unit_id:
                return entry
        raise LiveFailure(f"{self.tag} record", detail=f"no recorded unit {unit_id}")

    def checkpoint(self, what, selector, unit_id, branch, files):
        entry = self.entry(unit_id)
        tip = self.git(f"tip {unit_id}", "rev-parse", f"refs/heads/{branch}").strip()
        checkpoint = _write_json(self.workdir / "cp" / f"{unit_id}.json", {
            "schema": 1, "unit": unit_id, "ref": f"refs/heads/{branch}",
            "base": entry["parent_tip"], "end": tip, "tip": tip, "base_branch": entry["parent"],
            "merged_refs": [], "own_merge_subjects": [], "docs_paths": [],
            "candidates": [{"id": "t1", "title": unit_id, "files": files}],
        })
        self.fold(what, "checkpoint", *selector, "--checkpoint", checkpoint, "--final")

    def build_unit(self, letter):
        unit_id = f"{self.prefix}-{letter}"
        branch = self.branch(letter)
        stem = f"r{self.number}_{letter}"
        contract = _write_json(self.workdir / "units" / f"{unit_id}.json", {
            "schema": 1, "id": unit_id, "kind": "stacked", "branch": branch,
            "target": self.trunk, "title": f"{self.run_id} live unit {letter} round {self.number}",
        })
        self.fold(f"start {unit_id}", "start", "--unit", contract)
        self.commit(f"feat {unit_id}", {f"{stem}.py": f"{stem}\n"}, f"feat: add {stem}")
        self.commit(f"test {unit_id}", {f"test_{stem}.py": f"t {stem}\n"},
                    f"test: cover {stem}")
        self.checkpoint(f"checkpoint {unit_id}", ["--unit", contract], unit_id, branch,
                        [f"{stem}.py", f"test_{stem}.py"])
        self.fold(f"ready {unit_id}", "ready", "--unit", contract)

    def hotfix(self):
        label, name = f"{self.prefix}-hotfix", self.hotfix_name
        stem = f"hotfix_r{self.number}"
        self.fold(f"hotfix {label}", "hotfix", "--target", self.trunk, "--name", name)
        self.commit(f"hotfix {label}", {f"{stem}.txt": "fix\n"}, f"fix: live hotfix {stem}")
        self.checkpoint(f"checkpoint {label}", ["--unit-id", name], name, f"hotfix/{name}",
                        [f"{stem}.txt"])
        self.fold(f"ready {label}", "ready", "--unit-id", name)
        merged = self.snapshot(name)
        self.fold(f"merge-chain {label}", "merge-chain", "--unit-id", name)
        return merged

    def merges(self):
        self.git("fetch", "fetch", "-q", "origin")
        out = self.git("merge count", "rev-list", "--merges", "--first-parent", "--count",
                       f"refs/remotes/origin/{self.trunk}")
        return int(out.strip())

    def snapshot(self, unit_id):
        """The PR number and pushed tip the flow recorded for a unit, read before it merges."""
        entry = self.entry(unit_id)
        if entry.get("pr") is None or not entry.get("pushed"):
            raise LiveFailure(f"{self.tag} record", detail=f"{unit_id} has no PR or pushed tip")
        return unit_id, entry["pr"], entry["pushed"]

    def check_unit(self, unit):
        unit_id, number, tip = unit
        view = _gh(["gh", "pr", "view", str(number), "--repo", self.slug, "--json",
                    "state,mergeCommit"])
        try:
            data = json.loads(view.stdout) if view.returncode == 0 else {}
        except ValueError:
            data = {}
        if data.get("state") != "MERGED" or not (data.get("mergeCommit") or {}).get("oid"):
            raise LiveFailure(f"{self.tag} remote check", f"PR #{number} ({unit_id}) is not "
                              f"MERGED with a merge commit", _last_line(view.stderr))
        trunk = f"refs/remotes/origin/{self.trunk}"
        ancestor = subprocess.run(["git", "-C", str(self.repo), "merge-base", "--is-ancestor", tip,
                                   trunk], capture_output=True, text=True, check=False)
        if ancestor.returncode != 0:
            raise LiveFailure(f"{self.tag} remote check",
                              f"{unit_id} tip {tip[:12]} is not on {self.trunk}")

    def check_remote(self, before, units):
        after = self.merges()  # fetches first, so the ancestor checks see the merged trunk
        if after <= before:
            raise LiveFailure(f"{self.tag} remote check",
                              f"{self.trunk} gained no merge commit (squash or fast-forward)")
        for unit in units:
            self.check_unit(unit)
        for branch in self.branches:
            if self.git("remote branches", "ls-remote", "--heads", "origin", branch).strip():
                raise LiveFailure(f"{self.tag} remote check", f"{branch} is left on the remote")
        self.ok("remote check")

    def run(self):
        before = self.merges()
        for letter in UNIT_LETTERS:
            self.build_unit(letter)
        hotfix = self.hotfix()
        # The merged hotfix left HEAD detached; restack needs a unit branch checked out.
        self.git("switch top unit", "switch", "-q", self.branch(UNIT_LETTERS[-1]))
        self.fold("restack", "restack")
        units = [self.snapshot(f"{self.prefix}-{letter}") for letter in UNIT_LETTERS]
        self.fold("merge-chain", "merge-chain")
        self.check_remote(before, [hotfix, *units])


def trunk_of(run_id):
    return f"{run_id}/main"


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=False)


def prepare_trunk(repo, run_id):
    """Push the per-run trunk from the default branch and make it the flow's only target."""
    head = _git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").stdout.strip()
    default = head.removeprefix("origin/") or "main"
    trunk = trunk_of(run_id)
    pushed = _git(repo, "push", "-q", "origin", f"refs/remotes/origin/{default}:refs/heads/{trunk}")
    if pushed.returncode != 0:
        raise LiveFailure(f"setup trunk {trunk}", detail=_last_line(pushed.stderr))
    _git(repo, "fetch", "-q", "origin")
    path = repo / ".aikit" / "flow.json"
    settings = json.loads(path.read_text(encoding="utf-8"))
    settings["targets"] = [trunk]
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(settings), encoding="utf-8")
    temp.replace(path)
    print(f"ok setup trunk {trunk} from {default}", flush=True)


def run_rounds(repo, workdir, env, run_id, slug):
    """The per-run trunk, then both rounds in `repo`; prints one ok line per step. 0 or 1."""
    try:
        prepare_trunk(repo, run_id)
        for number, backend in enumerate(ROUNDS, start=1):
            round_env = {key: value for key, value in env.items() if key != BACKEND_ENV}
            if backend is not None:
                round_env[BACKEND_ENV] = backend
            Round(number, repo, workdir, round_env, RunInfo(run_id, slug)).run()
    except LiveFailure as exc:
        print(f"live-check: failed at {exc.step}" + (f": {exc.reason}" if exc.reason else ""))
        if exc.detail:
            print(f"  {exc.detail}")
        return 1
    return 0


def cleanup(repo, slug, run_id):
    """Close this run's open PRs, then delete its branches and its trunk. Returns failure lines.

    Only what this run recorded is touched: the PRs and branches in the clone's flow record whose
    branch carries the run id, and the per-run trunk. No repository is deleted.
    """
    if not (repo / ".git").is_dir():
        return []  # no clone, so nothing was pushed
    path = repo / ".git" / "ai-kit-stack.json"
    units = json.loads(path.read_text(encoding="utf-8"))["units"] if path.exists() else []
    own = [entry for entry in units if run_id in entry["branch"]]
    failures = []
    for entry in own:
        if entry.get("pr") is None:
            continue
        number = str(entry["pr"])
        view = _gh(["gh", "pr", "view", number, "--repo", slug, "--json", "state"])
        try:
            state = json.loads(view.stdout).get("state") if view.returncode == 0 else None
        except ValueError:
            state = None
        if state is None:
            failures.append(f"PR {number}: {_last_line(view.stderr) or 'state unknown'}")
        elif state == "OPEN":
            closed = _gh(["gh", "pr", "close", number, "--repo", slug])
            if closed.returncode != 0:
                failures.append(f"close PR {number}: {_last_line(closed.stderr)}")
    for branch in [entry["branch"] for entry in own] + [trunk_of(run_id)]:
        listed = _git(repo, "ls-remote", "--heads", "origin", f"refs/heads/{branch}")
        if listed.returncode != 0:
            failures.append(f"list {branch}: {_last_line(listed.stderr)}")
        elif listed.stdout.strip():
            deleted = _git(repo, "push", "-q", "origin", "--delete", branch)
            if deleted.returncode != 0:
                failures.append(f"delete {branch}: {_last_line(deleted.stderr)}")
    return failures


def _new_run_id():
    return f"flowlive-{uuid.uuid4().hex[:8]}"


def _finish(code, repo, slug, run_id):
    failures = cleanup(repo, slug, run_id)
    if failures:
        print(f"live-check: cleanup failed for run {run_id}")
        for line in failures:
            print(f"  {line}")
        code = 1
    if code == 0:
        print("live-check: ok")
    return code


def fixture_run(bare, workdir):
    run_id = _new_run_id()
    workdir = workdir / run_id
    repo = workdir / "repo"
    cloned = subprocess.run(["git", "clone", "--local", "--no-hardlinks", "-q", bare, str(repo)],
                            capture_output=True, text=True, check=False)
    if cloned.returncode != 0:
        print(f"live-check: failed at clone: {_last_line(cloned.stderr)}")
        return 1
    # The clone's origin is the GitHub URL the flow reads the owner and repo from; insteadOf
    # routes it to the bare fixture, as the flow's own tests do.
    subprocess.run(["git", "-C", str(repo), "remote", "set-url", "origin", FIXTURE_URL],
                   check=True)
    subprocess.run(["git", "-C", str(repo), "config", "--local",
                    f"url.{bare}.insteadOf", FIXTURE_URL], check=True)
    code = 1
    if _consent(repo, dict(os.environ)):
        code = run_rounds(repo, workdir, dict(os.environ), run_id, FIXTURE_SLUG)
    return _finish(code, repo, FIXTURE_SLUG, run_id)


def _consent(repo, env):
    proc = subprocess.run([sys.executable, str(FOLD), "consent", "grant", "--add-exclude",
                           "--repo", str(repo)], capture_output=True, text=True, check=False,
                          env=env)
    if proc.returncode != 0:
        print(f"live-check: failed at consent: {_last_line(proc.stderr or proc.stdout)}")
        return False
    return True


def _live_rounds(slug, workdir, run_id):
    repo = workdir / "repo"
    cloned = _gh(["gh", "repo", "clone", slug, str(repo)])
    if cloned.returncode != 0:
        print(f"live-check: failed at clone {slug}: {_last_line(cloned.stderr)}")
        return 1
    if not _consent(repo, dict(os.environ)):
        return 1
    return run_rounds(repo, workdir, dict(os.environ), run_id, slug)


def ensure_repo(slug):
    """True when `slug` is a private repo; a missing one is created once and kept."""
    view = _gh(["gh", "repo", "view", slug, "--json", "isPrivate"])
    if view.returncode != 0:
        created = _gh(["gh", "repo", "create", slug, "--private", "--add-readme"])
        if created.returncode != 0:
            print(f"live-check: failed at create {slug}: {_last_line(created.stderr)}")
            return False
        print(f"live-check: created private repo {slug}; it is kept for later runs")
        return True
    try:
        private = json.loads(view.stdout).get("isPrivate")
    except ValueError:
        private = None
    if private is not True:
        print(f"live-check: refused: {slug} is not a private repo")
        return False
    return True


def live_run(slug, workdir):
    """Run both rounds under a new run id in the persistent repo, then clean up this run only."""
    if not ensure_repo(slug):
        return 1
    run_id = _new_run_id()
    print(f"live-check: run {run_id} in {slug} on trunk {trunk_of(run_id)}", flush=True)
    rundir, code = workdir / run_id, 1
    try:
        code = _live_rounds(slug, rundir, run_id)
    finally:
        code = _finish(code, rundir / "repo", slug, run_id)
    return code


def _live_plan(slug):
    return "\n".join([
        f"live-check: would use the private repo {slug}, creating it once if missing "
        "(gh repo create --private --add-readme); it is kept, and no repo is ever deleted",
        "live-check: would run both rounds in a clone of it under a new run id: a per-run trunk "
        "<run-id>/main from the default branch, and branches and PRs named with the run id",
        "live-check: would then close this run's open PRs and delete this run's branches and "
        "trunk only, also on failure; a failed cleanup fails the check",
        "live-check: precondition: gh signed in with the repo scope, and the owner present",
        "live-check: rerun with --live --yes-owner-attended to run it",
    ])


def _login():
    proc = _gh(["gh", "api", "user", "--jq", ".login"])
    if proc.returncode != 0:
        print(f"live-check: failed at owner lookup: {_last_line(proc.stderr)}")
        return None
    return proc.stdout.strip()


def build_parser():
    parser = argparse.ArgumentParser(description="Scripted live check of the unit flow (FLOW-11).")
    parser.add_argument("--fixture", metavar="BARE", help="local bare remote (tests)")
    parser.add_argument("--live", action="store_true", help="real GitHub, owner-attended")
    parser.add_argument("--yes-owner-attended", action="store_true")
    parser.add_argument("--owner", help=f"GitHub login that owns <owner>/{LIVE_REPO}")
    parser.add_argument("--repo", metavar="OWNER/NAME",
                        help=f"persistent private repo to reuse (default <owner>/{LIVE_REPO})")
    parser.add_argument("--workdir", help="scratch directory; each run uses <workdir>/<run-id>")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if bool(args.fixture) == args.live or (args.repo and not SLUG.fullmatch(args.repo)):
        print(USAGE, file=sys.stderr)
        return 2
    if args.live and not args.yes_owner_attended:
        print(_live_plan(args.repo or f"{args.owner or '<owner>'}/{LIVE_REPO}"))
        return 2
    if args.workdir is None:
        print(USAGE, file=sys.stderr)
        return 2
    workdir = pathlib.Path(args.workdir).resolve()  # each run works in <workdir>/<run-id>
    workdir.mkdir(parents=True, exist_ok=True)
    if args.fixture:
        return fixture_run(args.fixture, workdir)
    slug = args.repo
    if slug is None:
        owner = args.owner or _login()
        if owner is None:
            return 1
        slug = f"{owner}/{LIVE_REPO}"
    return live_run(slug, workdir)


if __name__ == "__main__":
    sys.exit(main())
