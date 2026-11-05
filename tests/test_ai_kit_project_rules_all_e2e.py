"""Real dispatch of the six sibling checkers against this repo (e2e tier).

Moved out of `tests/test_ai_kit_project_rules_all.py` by 26-08: the agents domain now runs the
checkout-local gsd-core's `runtime-identity` through `node` (SPEC R7), so these cases are real
`node` runs and belong to `make e2e-test`, not the unit tier (AGENTS.md test tiers).

The environment is cleared to a scratch HOME/XDG and a PATH of `node` and `git` symlinks: the
gsd-tools resolver reads `RUNTIME_DIR` and every host-home override, and `.claude/` is
gitignored, so an inherited env could reach a gsd-tools under the real home. The `node` link is
the real binary behind a version-manager shim: the identity probe passes node only PATH and the
scratch HOME, where a Volta shim cannot find its toolchain. Each class skips with a reason when
the checkout-local gsd-tools or `node` is absent.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-all"),
)

from ai_kit_project_rules_all import aggregate, dispatch

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENTRYPOINT = [
    sys.executable,
    os.path.join(_REPO, "skills", "ai-kit-project-rules-all", "ai-kit-project-rules-all.py"),
]
_AGENTS_ENTRY = os.path.join(
    _REPO, "skills", "ai-kit-project-rules-agents", "ai-kit-project-rules-agents.py"
)
_CHECKOUT_GSD_TOOLS = os.path.join(_REPO, ".claude", "gsd-core", "bin", "gsd-tools.cjs")
_NODE = shutil.which("node")
_SKIP_REASON = (
    "needs the checkout-local gsd-core (.claude/gsd-core/bin/gsd-tools.cjs) and node on PATH"
)


def _real_node(node):
    """The node binary a version-manager shim (Volta, asdf) runs, resolved under the caller's
    env; `node` itself when it is not a shim or the lookup fails."""
    if node is None:
        return None
    real = subprocess.run([node, "-e", "process.stdout.write(process.execPath)"],
                          capture_output=True, text=True, check=False, timeout=30)
    return real.stdout.strip() if real.returncode == 0 and real.stdout.strip() else node


_REAL_NODE = _real_node(_NODE)


def _scoped_env_setup(case: unittest.TestCase) -> str:
    """Patch `os.environ` to a scratch HOME/XDG and a PATH of node and git symlinks.

    Returns the scratch PATH directory. `clear=True` drops `RUNTIME_DIR` and every host-home
    override; the patch is undone by `addCleanup`.
    """
    root = tempfile.mkdtemp(prefix="p26-08-e2e-")
    case.addCleanup(shutil.rmtree, root, True)
    bin_dir = os.path.join(root, "bin")
    os.makedirs(bin_dir)
    for name, found in (("node", _REAL_NODE), ("git", shutil.which("git"))):
        if found:
            os.symlink(found, os.path.join(bin_dir, name))
    home = os.path.join(root, "home")
    env = {
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "XDG_DATA_HOME": os.path.join(home, ".local", "share"),
        "XDG_STATE_HOME": os.path.join(home, ".local", "state"),
        "XDG_CACHE_HOME": os.path.join(home, ".cache"),
        "PATH": bin_dir,
    }
    patcher = mock.patch.dict(os.environ, env, clear=True)
    patcher.start()
    case.addCleanup(patcher.stop)
    return bin_dir


@unittest.skipUnless(_NODE and os.path.isfile(_CHECKOUT_GSD_TOOLS), _SKIP_REASON)
class TestTracer(unittest.TestCase):
    def setUp(self):
        _scoped_env_setup(self)

    """The real six checkers against this repo (the e2e tier)."""

    def test_dispatch_all_returns_all_six_real_domains(self):
        results = dispatch.dispatch_all(repo_root=_REPO)
        self.assertEqual(set(results.keys()), set(dispatch.DOMAIN_ORDER))
        for domain, result in results.items():
            self.assertIn("remediate", result, msg=f"{domain}: {result}")
            self.assertNotEqual(
                result.get("status"), "failed", msg=f"{domain}: {result}"
            )

    def test_aggregate_of_real_dispatch_is_globally_sorted_with_no_failures(self):
        report = aggregate.aggregate(dispatch.dispatch_all(repo_root=_REPO))
        self.assertEqual(set(report.keys()), {"remediate", "blocked", "failed", "notices"})
        self.assertEqual(report["failed"], [])
        crits = [entry["criticality"] for entry in report["remediate"]]
        self.assertEqual(crits, sorted(crits))

    def test_entry_script_subprocess_check_against_this_repo(self):
        result = subprocess.run(
            [*_ENTRYPOINT, "check", _REPO],
            capture_output=True,
            text=True,
            timeout=240,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(set(report.keys()), {"remediate", "blocked", "failed", "notices"})


@unittest.skipUnless(_NODE and os.path.isfile(_CHECKOUT_GSD_TOOLS), _SKIP_REASON)
class TestRealDomainIsolation(unittest.TestCase):
    def setUp(self):
        _scoped_env_setup(self)

    def test_unresolvable_entrypoint_isolated_from_other_five_real_domains(self):
        real_resolve = dispatch.resolve_entrypoint

        def _break_cicd_only(skill_name):
            if skill_name == dispatch.SKILL_NAMES["cicd"]:
                return None
            return real_resolve(skill_name)

        with mock.patch.object(dispatch, "resolve_entrypoint", side_effect=_break_cicd_only):
            results = dispatch.dispatch_all(repo_root=_REPO)

        cicd_result = results["cicd"]
        self.assertEqual(cicd_result["status"], "failed")
        self.assertIsNone(cicd_result["returncode"])
        self.assertIn("entrypoint not found", cicd_result["error"].lower())

        other_domains = [d for d in dispatch.DOMAIN_ORDER if d != "cicd"]
        for domain in other_domains:
            self.assertIn("remediate", results[domain], msg=f"{domain}: {results[domain]}")
            self.assertNotEqual(
                results[domain].get("status"), "failed", msg=f"{domain}: {results[domain]}"
            )


@unittest.skipUnless(_NODE and os.path.isfile(_CHECKOUT_GSD_TOOLS), _SKIP_REASON)
class TestAgentsProbe(unittest.TestCase):
    def setUp(self):
        _scoped_env_setup(self)

    def test_agents_probe_runs_the_checkout_gsd_tools(self):
        # The probe runs only where `<repo>/.planning/` exists, and the long-path clone has none
        # (SPEC R9). So probe a scratch repo with a `.planning/` marker whose gsd-core is a link to
        # the checkout's: the probe resolves to the same tools, and no live `.planning/` is read.
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "probe-repo")
            os.makedirs(os.path.join(repo, ".planning"))
            os.makedirs(os.path.join(repo, ".claude"))
            os.symlink(os.path.dirname(os.path.dirname(_CHECKOUT_GSD_TOOLS)),
                       os.path.join(repo, ".claude", "gsd-core"))
            subprocess.run(["git", "init", "-q", repo], check=True, capture_output=True)
            result = subprocess.run(
                [sys.executable, _AGENTS_ENTRY, "check", repo],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            probe_lines = [
                line for line in result.stderr.splitlines()
                if line.startswith("ai-kit: gsd identity probe ran ")
            ]
            self.assertEqual(len(probe_lines), 1, msg=result.stderr)
            probed = probe_lines[0][len("ai-kit: gsd identity probe ran "):]
            # realpath must run while the scratch link exists: it resolves through it.
            self.assertEqual(
                os.path.realpath(probed), os.path.realpath(_CHECKOUT_GSD_TOOLS)
            )
            # The probe answered `ok`, so the opengsd rules apply; the scratch repo has no
            # AGENTS.md, so both are missing. A probe that timed out marks them unverified.
            rows = {row["id"]: row for row in json.loads(result.stdout)["workflow"]}
            for rule in ("R18", "R19"):
                self.assertEqual(rows[rule]["status"], "missing", msg=rows[rule])
                self.assertNotIn("unverified", rows[rule], msg=rows[rule])

if __name__ == "__main__":
    unittest.main()
