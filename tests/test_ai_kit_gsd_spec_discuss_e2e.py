"""Real gsd-core run for ai-kit-gsd-spec-discuss: the e2e tier (C-IN-06). It spawns real
`node` against the gsd-core edge-probe.cjs that `edge_floor.find_engine` resolves, and skips
when either is missing."""
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.cross_ai_selftest import require_real_node
from tests.fold_fixtures import git_env
from tests.test_ai_kit_gsd_spec_discuss import SPEC, edge_floor

_SPEC_SCRIPTS = (Path(__file__).resolve().parent.parent
                 / "skills" / "ai-kit-gsd-spec-discuss" / "scripts")
sys.path.insert(0, str(_SPEC_SCRIPTS))
import branch_preflight

_FOLD_SCRIPTS = (Path(__file__).resolve().parent.parent
                 / "skills" / "ai-kit-commit-fold" / "scripts")
sys.path.insert(0, str(_FOLD_SCRIPTS))
import fold_adapters

GSD_TOOLS = (Path(__file__).resolve().parent.parent
             / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs")
FOLD_PY = (Path(__file__).resolve().parent.parent
           / "skills" / "ai-kit-commit-fold" / "scripts" / "fold.py")

# The floor this fixture's two requirements produce on the checkout-local engine (WR-07).
# An empty `items` list used to satisfy a subset check and hide a silent engine.
_EXPECTED = {
    ("adjacency", "R1"),
    ("boundary", "R1"),
    ("concurrency", "R2"),
    ("empty", "R1"),
    ("ordering", "R1"),
    ("precision", "R1"),
}


def _spec_with(pairs: set[tuple[str, str]]) -> str:
    """The fixture requirements plus an Edge Coverage table of exactly `pairs`."""
    head, rest = SPEC.split("## Edge Coverage", 1)
    _body, tail = rest.split("## Prohibitions", 1)
    rows = ["| Category | Requirement | Status | Resolution / Reason |",
            "|----------|-------------|--------|---------------------|"]
    rows += [f"| {category} | {requirement} | covered | fixture |"
             for category, requirement in sorted(pairs)]
    return f"{head}## Edge Coverage\n\n" + "\n".join(rows) + f"\n\n## Prohibitions{tail}"


class TestRealEdgeFloor(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node") and edge_floor.find_engine(os.environ, os.getcwd(),
                                                                          None),
                         "node or gsd-core edge-probe.cjs not installed")
    def test_real_engine_floor_and_a_removed_row_drifts(self):
        engine = edge_floor.find_engine(os.environ, os.getcwd(), None)
        assert engine is not None
        floor = edge_floor.run_engine(engine, edge_floor.requirements(SPEC))
        pairs = {(item["category"], item["requirement_id"]) for item in floor["items"]}
        self.assertEqual(pairs, _EXPECTED)
        with tempfile.TemporaryDirectory() as tmp:
            full = Path(tmp) / "09-SPEC.md"
            full.write_text(_spec_with(_EXPECTED))
            self.assertEqual(edge_floor.main(["check", str(full), "--engine", engine],
                                              env=os.environ), 0)
            short = Path(tmp) / "10-SPEC.md"
            short.write_text(_spec_with(_EXPECTED - {("empty", "R1")}))
            self.assertEqual(edge_floor.main(["check", str(short), "--engine", engine],
                                              env=os.environ), 1)


class TestRealBranchPreflight(unittest.TestCase):
    """The preflight against the checkout-local gsd-tools and the real fold.py."""

    @unittest.skipUnless(shutil.which("node") and GSD_TOOLS.is_file(),
                         "node or the checkout-local gsd-tools is missing")
    def setUp(self):
        self.node = require_real_node(self)

    def _child_env(self, tmp):
        home = Path(tmp) / "home"
        home.mkdir(exist_ok=True)
        env = git_env(home)
        env["HOME"] = str(home)
        env["AI_KIT_REFUSE_REAL_HOME"] = "1"
        return env

    def _git(self, env, *args):
        proc = subprocess.run(["git", *args], capture_output=True, text=True,
                              check=False, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout

    def _project(self, tmp, config, dirname="05-demo-slice"):
        root = Path(tmp)
        proj = root / "proj"
        proj.mkdir()
        env = self._child_env(tmp)
        self._git(env, "init", "-q", "-b", "main", str(proj))
        self._git(env, "-C", str(proj), "config", "user.email", "t@example.invalid")
        self._git(env, "-C", str(proj), "config", "user.name", "t")
        planning = proj / ".planning"
        planning.mkdir()
        (planning / "ROADMAP.md").write_text(
            "### Phase 5: Other Heading Name\n", encoding="utf-8")
        phase = planning / "phases" / dirname
        phase.mkdir(parents=True)
        (phase / "05-CONTEXT.md").write_text("context\n", encoding="utf-8")
        config_path = planning / "config.json"
        if config is not None:
            config_path.write_text(json.dumps(config), encoding="utf-8")
        self._git(env, "-C", str(proj), "add", "-A")
        self._git(env, "-C", str(proj), "commit", "-q", "-m", "init")
        bare = root / "remote.git"
        self._git(env, "init", "-q", "--bare", "-b", "main", str(bare))
        self._git(env, "-C", str(proj), "remote", "add", "origin", str(bare))
        self._git(env, "-C", str(proj), "push", "-q", "origin", "main")
        return proj, env, config_path

    def _preflight(self, proj, env, units_text):
        units = proj.parent / "units.txt"
        units.write_text(units_text, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(_SPEC_SCRIPTS / "branch_preflight.py"),
             "--repo", str(proj),
             "--gsd", shlex.join([self.node, str(GSD_TOOLS)]),
             "--fold-py", str(FOLD_PY),
             "--phases", "5", "--units", str(units)],
            capture_output=True, text=True, check=False, timeout=60, env=env)

    def _init_branch_name(self, proj, env):
        proc = subprocess.run(
            [self.node, str(GSD_TOOLS), "init", "execute-phase", "5", "--pick",
             "branch_name"],
            cwd=proj, capture_output=True, text=True, check=False, timeout=60, env=env)
        return proc

    def _snapshot(self, proj, env, config_path):
        digest = (hashlib.sha256(config_path.read_bytes()).hexdigest()
                  if config_path.is_file() else None)
        stack = proj / ".git" / "ai-kit-stack.json"
        stack_bytes = stack.read_bytes() if stack.is_file() else None
        refs = self._git(env, "-C", str(proj), "for-each-ref",
                         "--format=%(refname) %(objectname)")
        head = self._git(env, "-C", str(proj), "branch", "--show-current")
        return digest, stack_bytes, refs, head

    def _side(self, proj, env):
        self._git(env, "-C", str(proj), "switch", "-q", "-c", "side")
        (proj / "side.txt").write_text("side\n", encoding="utf-8")
        self._git(env, "-C", str(proj), "add", "side.txt")
        self._git(env, "-C", str(proj), "commit", "-q", "-m", "feat: side work")

    def test_gsd_rule_matches_real_init_and_real_tools_agree(self):
        config = {"git": {"branching_strategy": "phase",
                          "phase_branch_template": "gsd/phase-{phase}-{slug}"}}
        with tempfile.TemporaryDirectory() as tmp:
            proj, env, _config_path = self._project(tmp, config)
            init = self._init_branch_name(proj, env)
            printed = init.stdout.strip()
            expected = branch_preflight.gsd_name(
                "gsd/phase-{phase}-{slug}", "5", "demo-slice")
            if printed != "gsd/phase-05-demo-slice":
                self.fail(f"init execute-phase printed {printed!r}: {init.stderr}")
            self.assertEqual(printed, expected)
            out = self._preflight(proj, env, "units: none\n")
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("preflight: ok", out.stdout)
            self.assertNotIn("deferred", out.stdout)
            self._side(proj, env)
            out = self._preflight(proj, env, "units: none\n")
            self.assertEqual(out.returncode, 1, out.stderr)
            self.assertIn(
                "refused unrecorded_head: HEAD branch side is not a recorded unit "
                "and holds 1 commit(s) the trunk lacks:",
                out.stdout)

    def test_missing_config_or_git_section_proceeds_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj, env, config_path = self._project(tmp, None)
            out = self._preflight(proj, env, "units: none\n")
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("preflight: ok", out.stdout)
            self.assertFalse(config_path.exists())
        with tempfile.TemporaryDirectory() as tmp:
            proj, env, config_path = self._project(tmp, {"mode": "yolo"})
            before = config_path.read_bytes()
            out = self._preflight(proj, env, "units: none\n")
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("preflight: ok", out.stdout)
            self.assertEqual(config_path.read_bytes(), before)

    def test_legacy_key_config_keeps_its_bytes(self):
        config = {"git": {"branching_strategy": "phase",
                          "phase_branch_template": "gsd/phase-{phase}-{slug}"},
                  "depth": "standard"}
        with tempfile.TemporaryDirectory() as tmp:
            proj, env, config_path = self._project(tmp, config)
            before = self._snapshot(proj, env, config_path)
            out = self._preflight(proj, env, "units: none\n")
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(self._snapshot(proj, env, config_path), before)
            self._side(proj, env)
            after_side = self._snapshot(proj, env, config_path)
            self.assertNotEqual(after_side[2:], before[2:])
            out = self._preflight(proj, env, "units: none\n")
            self.assertEqual(out.returncode, 1, out.stderr)
            self.assertEqual(self._snapshot(proj, env, config_path), after_side)

    def test_unnormalized_suffix_real_tools_disagree_and_preflight_refuses(self):
        config = {"git": {"branching_strategy": "phase",
                          "phase_branch_template": "gsd/phase-{phase}-{slug}"}}
        with tempfile.TemporaryDirectory() as tmp:
            proj, env, config_path = self._project(tmp, config, dirname="05-Demo_Slice")
            before = config_path.read_bytes()
            out = self._preflight(proj, env, "units: none\n")
            self.assertEqual(out.returncode, 1, out.stderr)
            self.assertIn(
                "refused gsd_branch_mismatch: phase 5: GSD branch "
                "gsd/phase-05-demo-slice differs from unit branch "
                "gsd/phase-05-Demo_Slice (strategy phase)",
                out.stdout)
            self.assertEqual(config_path.read_bytes(), before)
            init = self._init_branch_name(proj, env)
            printed = init.stdout.strip()
            if printed != "gsd/phase-05-demo-slice":
                self.fail(f"init execute-phase printed {printed!r}: {init.stderr}")
            self.assertEqual(
                fold_adapters.gsd_unit(str(proj), "5")["branch"],
                "gsd/phase-05-Demo_Slice")

    def test_flat_template_real_init_matches_preflight(self):
        config = {"git": {"branching_strategy": "phase"},
                  "phase_branch_template": "gsd/{phase}-{slug}"}
        with tempfile.TemporaryDirectory() as tmp:
            proj, env, config_path = self._project(tmp, config)
            before = config_path.read_bytes()
            out = self._preflight(proj, env, "units: none\n")
            self.assertEqual(out.returncode, 1, out.stderr)
            self.assertIn(
                "GSD branch gsd/05-demo-slice differs from unit branch "
                "gsd/phase-05-demo-slice",
                out.stdout)
            self.assertEqual(config_path.read_bytes(), before)
            init = self._init_branch_name(proj, env)
            printed = init.stdout.strip()
            if printed != "gsd/05-demo-slice":
                self.fail(f"init execute-phase printed {printed!r}: {init.stderr}")


if __name__ == "__main__":
    unittest.main()
