#!/usr/bin/env python3
"""Scripted live check of the unit flow (plan 29.1-06, FLOW-11).

Two rounds run the same steps. Round 1 uses the gh-stack backend and fails if any step falls back
to plain gh; round 2 forces AI_KIT_FLOW_PR_BACKEND=gh. Each round builds three stacked units
through a synthetic adapter (unit and checkpoint JSON only), starts a hotfix to main, merges it
with `merge-chain --unit-id` while the three PRs stay open, restacks, and runs `merge-chain`.
After each round the remote must show four new merge commits on main and no round branch left.

  --fixture BARE --workdir DIR
      Local bare remote, used by the tests. The fake gh must be on PATH.
  --live --yes-owner-attended --workdir DIR [--owner LOGIN]
      Owner-attended run on GitHub. Creates one private repo named
      <owner>/ai-kit-flow-live-<8 hex>, runs the rounds in a clone of it, and deletes exactly
      that repo afterwards. Without --yes-owner-attended it prints the plan and exits 2.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
FOLD = ROOT / "skills" / "ai-kit-commit-fold" / "scripts" / "fold.py"
FIXTURE_URL = "https://github.com/ai-kit-fixture/demo.git"
BACKEND_ENV = "AI_KIT_FLOW_PR_BACKEND"
FALLBACK = re.compile(r"pr backend: gh(?!-stack)")
ROUNDS = (("gh-stack", None), ("gh", "gh"))
UNIT_LETTERS = ("x", "y", "z")
USAGE = (
    "usage: flow_live_check.py (--fixture BARE | --live --yes-owner-attended) --workdir DIR "
    "[--owner LOGIN]"
)


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

    def __init__(self, number, tag, repo, workdir, env):
        self.number = number
        self.tag = tag
        self.repo = repo
        self.workdir = workdir
        self.env = env
        self.strict = BACKEND_ENV not in env

    @property
    def prefix(self):
        return f"live-{self.number}"

    @property
    def branches(self):
        return [f"live/r{self.number}/{letter}" for letter in UNIT_LETTERS] + [
            f"hotfix/{self.prefix}-hotfix"]

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
            raise LiveFailure(step, detail=_last_line(report))
        if self.strict and FALLBACK.search(report):
            raise LiveFailure(step, "gh-stack fallback", _last_line(report))
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
        branch = f"live/r{self.number}/{letter}"
        stem = f"r{self.number}_{letter}"
        contract = _write_json(self.workdir / "units" / f"{unit_id}.json", {
            "schema": 1, "id": unit_id, "kind": "stacked", "branch": branch,
            "title": f"Live unit {letter} round {self.number}",
        })
        self.fold(f"start {unit_id}", "start", "--unit", contract)
        self.commit(f"feat {unit_id}", {f"{stem}.py": f"{stem}\n"}, f"feat: add {stem}")
        self.commit(f"test {unit_id}", {f"test_{stem}.py": f"t {stem}\n"},
                    f"test: cover {stem}")
        self.checkpoint(f"checkpoint {unit_id}", ["--unit", contract], unit_id, branch,
                        [f"{stem}.py", f"test_{stem}.py"])
        self.fold(f"ready {unit_id}", "ready", "--unit", contract)

    def hotfix(self):
        name = f"{self.prefix}-hotfix"
        stem = f"hotfix_r{self.number}"
        self.fold(f"hotfix {name}", "hotfix", "--target", "main", "--name", name)
        self.commit(f"hotfix {name}", {f"{stem}.txt": "fix\n"}, f"fix: live hotfix {stem}")
        self.checkpoint(f"checkpoint {name}", ["--unit-id", name], name, f"hotfix/{name}",
                        [f"{stem}.txt"])
        self.fold(f"ready {name}", "ready", "--unit-id", name)
        self.fold(f"merge-chain {name}", "merge-chain", "--unit-id", name)

    def merges(self):
        self.git("fetch", "fetch", "-q", "origin")
        out = self.git("merge count", "rev-list", "--merges", "--first-parent", "--count",
                       "refs/remotes/origin/main")
        return int(out.strip())

    def check_remote(self, before):
        after = self.merges()
        if after != before + 4:
            raise LiveFailure(f"{self.tag} remote check",
                              f"main gained {after - before} merges, expected 4")
        for branch in self.branches:
            if self.git("remote branches", "ls-remote", "--heads", "origin", branch).strip():
                raise LiveFailure(f"{self.tag} remote check", f"{branch} is left on the remote")
        self.ok("remote check")

    def run(self):
        before = self.merges()
        for letter in UNIT_LETTERS:
            self.build_unit(letter)
        self.hotfix()
        # The merged hotfix left HEAD detached; restack needs a unit branch checked out.
        self.git("switch top unit", "switch", "-q", f"live/r{self.number}/{UNIT_LETTERS[-1]}")
        self.fold("restack", "restack")
        self.fold("merge-chain", "merge-chain")
        self.check_remote(before)


def run_rounds(repo, workdir, env):
    """Both rounds in `repo`; prints one ok line per step. Returns 0 or 1."""
    for number, (tag, backend) in enumerate(ROUNDS, start=1):
        round_env = {key: value for key, value in env.items() if key != BACKEND_ENV}
        if backend is not None:
            round_env[BACKEND_ENV] = backend
        try:
            Round(number, tag, repo, workdir, round_env).run()
        except LiveFailure as exc:
            print(f"live-check: failed at {exc.step}" + (f": {exc.reason}" if exc.reason else ""))
            if exc.detail:
                print(f"  {exc.detail}")
            return 1
    return 0


def fixture_run(bare, workdir):
    repo = workdir / "repo"
    if repo.exists():
        print("live-check: workdir must not hold a repo yet")
        return 2
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
    if not _consent(repo, dict(os.environ)):
        return 1
    code = run_rounds(repo, workdir, dict(os.environ))
    if code == 0:
        print("live-check: ok")
    return code


def _consent(repo, env):
    proc = subprocess.run([sys.executable, str(FOLD), "consent", "grant", "--add-exclude",
                           "--repo", str(repo)], capture_output=True, text=True, check=False,
                          env=env)
    if proc.returncode != 0:
        print(f"live-check: failed at consent: {_last_line(proc.stderr or proc.stdout)}")
        return False
    return True


def _live_rounds(slug, workdir):
    repo = workdir / "repo"
    cloned = _gh(["gh", "repo", "clone", slug, str(repo)])
    if cloned.returncode != 0:
        print(f"live-check: failed at clone {slug}: {_last_line(cloned.stderr)}")
        return 1
    if not _consent(repo, dict(os.environ)):
        return 1
    return run_rounds(repo, workdir, dict(os.environ))


def live_run(owner, workdir):
    """Create, run and delete one private repo. Only the repo this run created is deleted."""
    slug = f"{owner}/ai-kit-flow-live-{uuid.uuid4().hex[:8]}"
    created = _gh(["gh", "repo", "create", slug, "--private", "--add-readme"])
    if created.returncode != 0:
        print(f"live-check: failed at create {slug}: {_last_line(created.stderr)}")
        return 1
    code = 1
    try:
        code = _live_rounds(slug, workdir)
    finally:
        deleted = _gh(["gh", "repo", "delete", slug, "--yes"])
        if deleted.returncode != 0:
            print(f"live-check: cleanup failed {slug}")
            print(f"  {_last_line(deleted.stderr)}; delete it by hand: gh repo delete {slug} --yes")
            code = 1
    if code == 0:
        print("live-check: ok")
    return code


def _live_plan(owner):
    name = f"{owner or '<owner>'}/ai-kit-flow-live-<8 hex>"
    return "\n".join([
        f"live-check: would create private repo {name} (gh repo create --private --add-readme)",
        "live-check: would run both rounds in a clone of it, then delete exactly that repo "
        "(gh repo delete --yes)",
        "live-check: precondition: gh auth refresh -s delete_repo, and the owner present",
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
    parser.add_argument("--owner", help="GitHub login that owns the throwaway repo")
    parser.add_argument("--workdir", help="scratch directory for the clone and JSON files")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if bool(args.fixture) == args.live:
        print(USAGE, file=sys.stderr)
        return 2
    if args.live and not args.yes_owner_attended:
        print(_live_plan(args.owner))
        return 2
    if args.workdir is None:
        print(USAGE, file=sys.stderr)
        return 2
    workdir = pathlib.Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    if args.fixture:
        return fixture_run(args.fixture, workdir)
    owner = args.owner or _login()
    if owner is None:
        return 1
    return live_run(owner, workdir)


if __name__ == "__main__":
    sys.exit(main())
