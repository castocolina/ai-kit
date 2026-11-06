"""Real GSD run for the ai-kit-commit-fold capability (the e2e tier). It runs real `node` against
the checkout's project-local gsd-core, copied into a temp fixture project. HOME and GSD_HOME are
temp dirs; nothing is installed into this repository. Skips with a named reason when `node` or the
project-local gsd-core is missing."""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests import forge_fakes, host_fakes
from tests.fold_fixtures import (
    PHASE_DIR,
    ROOT,
    SKILL,
    commit,
    git_env,
    gsd_plan_commits,
    gsd_plan_text,
    gsd_project,
    make_remote,
    run_git,
)

COMMAND_GRAMMAR = r"^[a-z][a-z0-9-]*( [a-z][a-z0-9-]*)*$"

GSD_TOOLS = ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs"
BUNDLE = SKILL / "gsd" / "ai-kit-commit-fold"
MODULE = BUNDLE / "ai-kit-fold.cjs"


def _gsd_env(home, gsd_home):
    env = git_env(home)
    env.update(GSD_HOME=str(gsd_home), AI_KIT_REFUSE_REAL_HOME="1")
    return env


def _gsd(repo, env, *args):
    return subprocess.run(["node", str(GSD_TOOLS), *args], cwd=repo, env=env,
                          capture_output=True, text=True, check=False)


def _fixture(root, env, summary=True):
    """A phase-07 fixture project with the checkout's project-local gsd-core copied in.
    `summary=False` leaves plan 01 without its SUMMARY.md, so wave 1 is not finished."""
    repo = gsd_project(root, env, "sequential",
                       [{"plan": "01", "stems": ("a", "b"), "summary": summary}])
    for part in (".claude/gsd-core", ".claude/scripts"):
        shutil.copytree(ROOT / part, repo / part, symlinks=True)
    return repo


def _json(text):
    """The first JSON object in `text` (gsd-tools may print a line before it)."""
    return json.JSONDecoder().raw_decode(text[text.index("{"):])[0]


def _skills_roots(env):
    """The fold's skills-root list from the command module, computed by a node child."""
    script = ("const m = require(process.argv[1]);"
              " process.stdout.write(JSON.stringify(m.skillsRoots(JSON.parse(process.argv[2]))));")
    proc = subprocess.run(["node", "-e", script, str(MODULE), json.dumps(env)],
                          capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


@unittest.skipUnless(shutil.which("node") and GSD_TOOLS.is_file()
                     and (ROOT / ".claude" / "scripts").is_dir(),
                     "node or the checkout's project-local gsd-core is missing")
class TestCapabilityE2E(unittest.TestCase):
    # Slow on purpose: setUpClass runs real gsd-tools several times, about a second each.
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p29-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        cls.home = cls.tmp / "home"
        cls.gsd_home = cls.tmp / "gsd-home"
        cls.home.mkdir()
        cls.gsd_home.mkdir()
        cls.env = _gsd_env(cls.home, cls.gsd_home)
        repo = _fixture(cls.tmp / "fixture", cls.env)
        shutil.copytree(SKILL, cls.home / ".claude" / "skills" / "ai-kit-commit-fold",
                        ignore=shutil.ignore_patterns("__pycache__"))
        cls.install_no_yes = _gsd(repo, cls.env, "capability", "install", str(BUNDLE),
                                  "--scope", "project")
        cls.install_yes = _gsd(repo, cls.env, "capability", "install", str(BUNDLE),
                               "--scope", "project", "--yes")
        cls.hooks = _gsd(repo, cls.env, "loop", "render-hooks", "execute:wave:post", "--raw")
        cls.fold = _gsd(repo, cls.env, "ai-kit-fold", "run", "--phase", "7", "--raw")
        cls.repo = repo
        # The same installed capability, but HOME holds no fold skill: the command must refuse.
        missing_home = cls.tmp / "home-empty"
        missing_home.mkdir()
        cls.missing_env = _gsd_env(missing_home, cls.gsd_home)
        cls.missing = _fixture(cls.tmp / "missing", cls.missing_env)
        _gsd(cls.missing, cls.missing_env, "capability", "install", str(BUNDLE),
             "--scope", "project", "--yes")
        cls.missing_head = run_git(cls.missing, cls.missing_env, "rev-parse", "HEAD").strip()
        cls.missing_run = _gsd(cls.missing, cls.missing_env, "ai-kit-fold", "run", "--phase", "7",
                               "--raw")
        # ai-kit's own checkout: no host dir holds the skill, the project's skills/ tree does. The
        # wave:post step is rendered and run the way GSD dispatches it: gsd-tools <ref.command>.
        cls.local = _fixture(cls.tmp / "local", cls.missing_env)
        shutil.copytree(SKILL, cls.local / "skills" / "ai-kit-commit-fold",
                        ignore=shutil.ignore_patterns("__pycache__"))
        with (cls.local / ".git" / "info" / "exclude").open("a", encoding="utf-8") as exclude:
            exclude.write("skills/\n")
        _gsd(cls.local, cls.missing_env, "capability", "install", str(BUNDLE),
             "--scope", "project", "--yes")
        local_hooks = _json(_gsd(cls.local, cls.missing_env, "loop", "render-hooks",
                                 "execute:wave:post", "--raw").stdout)["activeHooks"]
        cls.local_command = next(hook["ref"]["command"] for hook in local_hooks
                                 if hook.get("capId") == "ai-kit-commit-fold")
        cls.local_run = _gsd(cls.local, cls.missing_env, *cls.local_command.split(),
                             "--phase", "7", "--raw")

    def test_install_without_yes_is_refused_and_names_the_command_module(self):
        self.assertEqual(self.install_no_yes.returncode, 1)
        self.assertIn("command module", (self.install_no_yes.stdout + self.install_no_yes.stderr)
                      .lower())

    def test_install_with_yes_installs(self):
        self.assertEqual(self.install_yes.returncode, 0, self.install_yes.stderr)
        self.assertEqual(_json(self.install_yes.stdout)["status"], "installed")

    def test_render_hooks_lists_the_fold_step(self):
        self.assertEqual(self.hooks.returncode, 0, self.hooks.stderr)
        hooks = [hook for hook in _json(self.hooks.stdout)["activeHooks"]
                 if hook.get("capId") == "ai-kit-commit-fold"]
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0]["kind"], "step")
        self.assertEqual(hooks[0]["ref"], {"command": "ai-kit-fold checkpoint"})

    def test_fold_run_folds_the_fixture_plan_into_two_commits(self):
        self.assertEqual(self.fold.returncode, 0, self.fold.stderr)
        lines = self.fold.stdout.splitlines()
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[-1], "outcome: 07-01 folded (inline)")
        subjects = run_git(self.repo, self.env, "log", "--format=%s", "HEAD").splitlines()
        self.assertEqual(subjects.index("docs(07): create phase plan"), 2)

    def test_fold_run_rejects_a_phase_id_with_three_parts(self):
        proc = _gsd(self.repo, self.env, "ai-kit-fold", "run", "--phase", "1.2.3", "--raw")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("usage", proc.stderr)

    def test_fold_run_without_the_skill_refuses_and_moves_nothing(self):
        self.assertNotEqual(self.missing_run.returncode, 0)
        self.assertIn("fold script not found", self.missing_run.stdout)
        head = run_git(self.missing, self.env, "rev-parse", "HEAD").strip()
        self.assertEqual(head, self.missing_head)

    def test_wave_post_step_finds_the_fold_in_the_project_skills_tree(self):
        self.assertRegex(self.local_command, COMMAND_GRAMMAR)
        output = self.local_run.stdout + self.local_run.stderr
        self.assertNotIn("fold script not found", output)
        # fold.py itself answered: no unit was started in this fixture, so it refuses by name.
        self.assertIn("outcome: phase-07 refused not_started", self.local_run.stdout, output)

    def test_skills_roots_with_a_full_env_list_the_five_host_dirs(self):
        env = {"HOME": "/h", "CLAUDE_CONFIG_DIR": "/cc", "XDG_CONFIG_HOME": "/xdg",
               "CURSOR_CONFIG_DIR": "/cur", "PI_CODING_AGENT_DIR": "/pi"}
        self.assertEqual(_skills_roots(env), [
            os.path.join("/cc", "skills"),
            os.path.join("/h", ".agents", "skills"),
            os.path.join("/xdg", "opencode", "skills"),
            os.path.join("/cur", "skills"),
            os.path.join("/pi", "skills"),
        ])

    def test_skills_roots_with_only_home_list_the_fallback_dirs(self):
        self.assertEqual(_skills_roots({"HOME": "/h"}), [
            os.path.join("/h", ".claude", "skills"),
            os.path.join("/h", ".agents", "skills"),
            os.path.join("/h", ".config", "opencode", "skills"),
            os.path.join("/h", ".cursor", "skills"),
            os.path.join("/h", ".pi", "agent", "skills"),
        ])


def _predicate_eval(repo, env, predicate):
    """Evaluate a gate's check.predicate the way ship.md step 1 does (gsd_run check predicate)."""
    return _gsd(repo, env, "check", "predicate", "--predicate", json.dumps(predicate),
                "--phase-dir", ".planning/phases/07-demo", "--phase-number", "07", "--raw")


@unittest.skipUnless(shutil.which("node") and GSD_TOOLS.is_file()
                     and (ROOT / ".claude" / "scripts").is_dir(),
                     "node or the checkout's project-local gsd-core is missing")
class TestShipGate(unittest.TestCase):
    # One install and one started phase; each state the gate sees is set on the record.
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p29.1-gate-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        cls.home = cls.tmp / "home"
        cls.home.mkdir()
        cls.env = _gsd_env(cls.home, cls.tmp / "gsd-home")
        cls.repo = _fixture(cls.tmp / "fixture", cls.env)
        make_remote(cls.tmp / "fixture", cls.env, cls.repo)
        shutil.copytree(SKILL, cls.home / ".claude" / "skills" / "ai-kit-commit-fold",
                        ignore=shutil.ignore_patterns("__pycache__"))
        cls.install = _gsd(cls.repo, cls.env, "capability", "install", str(BUNDLE),
                           "--scope", "project", "--yes")
        cls.hooks = _gsd(cls.repo, cls.env, "loop", "render-hooks", "ship:pre", "--raw")
        cls.start = _gsd(cls.repo, cls.env, "ai-kit-fold", "start", "--phase", "07", "--raw")

    def _record_state(self, state):
        sys.path.insert(0, str(SKILL / "scripts"))
        import flow_record  # pylint: disable=import-outside-toplevel
        record = flow_record.read_record(self.repo)
        for unit in record["units"]:
            unit["state"] = state
        flow_record.write_record(self.repo, record)

    def _gate(self):
        hooks = [hook for hook in _json(self.hooks.stdout)["activeHooks"]
                 if hook.get("capId") == "ai-kit-commit-fold"]
        self.assertEqual(len(hooks), 1)
        return hooks[0]

    def test_ship_gate_is_listed_blocking_with_a_command_predicate(self):
        self.assertEqual(self.install.returncode, 0, self.install.stderr)
        self.assertEqual(self.hooks.returncode, 0, self.hooks.stderr)
        gate = self._gate()
        self.assertEqual(gate["kind"], "gate")
        self.assertTrue(gate["blocking"])
        self.assertEqual(gate["onError"], "halt")
        self.assertEqual(gate["check"]["predicate"]["kind"], "command-exit-zero")

    def test_open_unit_blocks_the_gate_with_not_ready(self):
        self.assertEqual(self.start.returncode, 0, self.start.stderr)
        verdict = _json(_predicate_eval(self.repo, self.env,
                                        self._gate()["check"]["predicate"]).stdout)
        self.assertTrue(verdict["block"])
        self.assertIn("not_ready", verdict["message"])
        self.assertNotIn("ship_redirect", verdict["message"])

    def test_ready_unit_still_blocks_the_gate_with_ship_redirect(self):
        self._record_state("ready")
        verdict = _json(_predicate_eval(self.repo, self.env,
                                        self._gate()["check"]["predicate"]).stdout)
        self.assertTrue(verdict["block"])
        self.assertIn("ship_redirect", verdict["message"])
        self.assertIn("fold.py merge-chain", verdict["message"])

    def test_ship_verb_exits_1_with_the_reason_for_each_state(self):
        self._record_state("open")
        open_run = _gsd(self.repo, self.env, "ai-kit-fold", "ship", "--phase", "07", "--raw")
        self.assertEqual(open_run.returncode, 1)
        self.assertIn("refused not_ready", open_run.stdout)
        self._record_state("ready")
        ready_run = _gsd(self.repo, self.env, "ai-kit-fold", "ship", "--phase", "07")
        self.assertEqual(ready_run.returncode, 1)
        self.assertIn("refused ship_redirect", ready_run.stdout)
        self.assertIn("fold.py merge-chain", ready_run.stdout)

    def test_verbs_outside_the_allow_list_and_extra_arguments_are_refused(self):
        bogus = _gsd(self.repo, self.env, "ai-kit-fold", "merge", "--phase", "07")
        self.assertEqual(bogus.returncode, 2)
        self.assertIn("usage", bogus.stderr)
        extra = _gsd(self.repo, self.env, "ai-kit-fold", "ship", "--phase", "07", "--force")
        self.assertEqual(extra.returncode, 2)
        self.assertIn("usage", extra.stderr)


def _installed_fixture(root, env, summary=True):
    """A phase-07 fixture with a bare origin and the capability installed (tests read the hooks)."""
    repo = _fixture(root, env, summary)
    make_remote(root, env, repo)
    shutil.copytree(SKILL, pathlib.Path(env["HOME"]) / ".claude" / "skills" / "ai-kit-commit-fold",
                    ignore=shutil.ignore_patterns("__pycache__"), dirs_exist_ok=True)
    _gsd(repo, env, "capability", "install", str(BUNDLE), "--scope", "project", "--yes")
    return repo


def _fold_hooks(proc):
    return [hook for hook in _json(proc.stdout)["activeHooks"]
            if hook.get("capId") == "ai-kit-commit-fold"]


@unittest.skipUnless(shutil.which("node") and GSD_TOOLS.is_file()
                     and (ROOT / ".claude" / "scripts").is_dir(),
                     "node or the checkout's project-local gsd-core is missing")
class TestHookPoints(unittest.TestCase):
    # Hooks at the three points GSD dispatches, and no entry at the three it never runs them at.
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p29.1-points-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        home = cls.tmp / "home"
        home.mkdir()
        cls.env = _gsd_env(home, cls.tmp / "gsd-home")
        cls.repo = _installed_fixture(cls.tmp / "fixture", cls.env)
        cls.points = {point: _gsd(cls.repo, cls.env, "loop", "render-hooks", point, "--raw")
                      for point in ("discuss:pre", "plan:pre", "execute:wave:pre",
                                    "execute:wave:post", "verify:post")}

    def test_discuss_pre_and_wave_post_list_their_steps(self):
        discuss = _fold_hooks(self.points["discuss:pre"])
        self.assertEqual(len(discuss), 1)
        self.assertEqual(discuss[0]["kind"], "step")
        self.assertEqual(discuss[0]["ref"], {"command": "ai-kit-fold start"})
        wave = _fold_hooks(self.points["execute:wave:post"])
        self.assertEqual(len(wave), 1)
        self.assertEqual(wave[0]["kind"], "step")
        self.assertEqual(wave[0]["ref"], {"command": "ai-kit-fold checkpoint"})

    def test_plan_pre_lists_the_boundary_contribution_for_the_planner(self):
        self.assertEqual(self.points["plan:pre"].returncode, 0, self.points["plan:pre"].stderr)
        hooks = _fold_hooks(self.points["plan:pre"])
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0]["kind"], "contribution")
        self.assertEqual(hooks[0]["into"], "planner")
        text = hooks[0]["fragment"]["inline"]
        self.assertIn("gsd-tools.cjs ai-kit-fold boundary-plan --phase", text)
        self.assertIn("<objective>", text)
        self.assertIn("Unit brief: read .aikit/brief/SKILL.md", text)

    def test_execute_wave_pre_lists_the_boundary_step(self):
        self.assertEqual(self.points["execute:wave:pre"].returncode, 0,
                         self.points["execute:wave:pre"].stderr)
        hooks = _fold_hooks(self.points["execute:wave:pre"])
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0]["kind"], "step")
        self.assertEqual(hooks[0]["ref"], {"command": "ai-kit-fold boundary-wave"})

    def test_verify_post_lists_no_fold_entry(self):
        self.assertEqual(self.points["verify:post"].returncode, 0,
                         self.points["verify:post"].stderr)
        self.assertEqual(_fold_hooks(self.points["verify:post"]), [])

    def test_step_commands_match_the_dispatch_grammar(self):
        for point in ("discuss:pre", "execute:wave:pre", "execute:wave:post"):
            with self.subTest(point=point):
                command = _fold_hooks(self.points[point])[0]["ref"]["command"]
                self.assertRegex(command, COMMAND_GRAMMAR)


@unittest.skipUnless(shutil.which("node") and GSD_TOOLS.is_file()
                     and (ROOT / ".claude" / "scripts").is_dir(),
                     "node or the checkout's project-local gsd-core is missing")
class TestBoundaryDispatch(unittest.TestCase):
    # The router's boundary verbs as GSD runs them: unfinished wave 1 writes the brief, a
    # finished wave 1 skips, and an unknown verb is a usage error naming both boundary verbs.
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-boundary-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        home = cls.tmp / "home"
        home.mkdir()
        cls.env = _gsd_env(home, cls.tmp / "gsd-home")
        cls.open = _installed_fixture(cls.tmp / "open", cls.env, summary=False)
        cls.plan = _gsd(cls.open, cls.env, "ai-kit-fold", "boundary-plan", "--phase", "7", "--raw")
        cls.plan_brief = _brief_text(cls.open)
        cls.wave = _gsd(cls.open, cls.env, "ai-kit-fold", "boundary-wave", "--phase", "7", "--raw")
        cls.wave_brief = _brief_text(cls.open)
        cls.unknown = _gsd(cls.open, cls.env, "ai-kit-fold", "boundary-nope", "--phase", "7")
        cls.done = _installed_fixture(cls.tmp / "done", cls.env)
        cls.done_wave = _gsd(cls.done, cls.env, "ai-kit-fold", "boundary-wave", "--phase", "7",
                             "--raw")
        cls.done_brief = _brief_text(cls.done)

    def test_plan_verb_writes_the_plan_point(self):
        self.assertEqual(self.plan.returncode, 0, self.plan.stderr)
        self.assertIn("point: plan", self.plan_brief)

    def test_wave_verb_on_unfinished_wave_one_writes_the_wave_point(self):
        self.assertEqual(self.wave.returncode, 0, self.wave.stderr)
        self.assertIn("flow boundary", self.wave.stdout)
        self.assertIn("point: wave", self.wave_brief)

    def test_wave_verb_on_finished_wave_one_skips_and_writes_no_wave_brief(self):
        self.assertEqual(self.done_wave.returncode, 0, self.done_wave.stderr)
        self.assertIn("wave 1 finished: boundary skipped", self.done_wave.stdout)
        self.assertNotIn("point: wave", self.done_brief)

    def test_unknown_verb_is_a_usage_error_naming_both_boundary_verbs(self):
        self.assertEqual(self.unknown.returncode, 2)
        self.assertIn("boundary-plan", self.unknown.stderr)
        self.assertIn("boundary-wave", self.unknown.stderr)


LENS = ".planning/lens-brief"
JEV = "skills/jev-fast-decision"
UNIT_BRIEF = ".aikit/brief"
BRIEF_AGENTS = ("gsd-phase-researcher", "gsd-planner", "gsd-executor")
LENS_SETS = {
    "gsd-ui-researcher": ["global:impeccable", LENS, JEV],
    "gsd-ui-checker": ["global:impeccable", LENS, JEV],
    "gsd-ui-auditor": ["global:impeccable", LENS, JEV],
    "gsd-planner": ["global:ponytail:ponytail", LENS, JEV, UNIT_BRIEF],
    "gsd-plan-checker": ["global:ponytail:ponytail", LENS, JEV],
    "gsd-code-reviewer": ["global:ponytail:ponytail-review", LENS, JEV],
    "gsd-phase-researcher": [JEV, LENS, UNIT_BRIEF],
    "gsd-executor": [JEV, LENS, UNIT_BRIEF],
}
SYNTHETIC_LENS_BRIEF = (
    "# lens brief (synthetic)\n\n## Expected lenses\n\n- gsd-planner: global:ponytail:ponytail\n\n"
    "## If a lens did not load\n\nContinue without it.\n\n## Design rule\n\nSimple is not easy.\n\n"
    "## Unit brief\n\nFor gsd-phase-researcher, gsd-planner and gsd-executor only: say no unit "
    "brief was found.\n")


def _wire_lenses(repo, env):
    """The eight arrays, the trusted roots and ui_review, set through config-set as wire.sh does,
    plus a synthetic lens brief in the fixture (never the repository's .planning/)."""
    for agent, entries in LENS_SETS.items():
        _gsd(repo, env, "config-set", f"agent_skills.{agent}", json.dumps(entries))
    _gsd(repo, env, "config-set", "agent_skills_security.trusted_global_roots",
         '["~/.agents/skills"]')
    _gsd(repo, env, "config-set", "workflow.ui_review", "true")
    brief = repo / ".planning" / "lens-brief" / "SKILL.md"
    brief.parent.mkdir(parents=True, exist_ok=True)
    brief.write_text(SYNTHETIC_LENS_BRIEF, encoding="utf-8")


def _render(repo, env, agent):
    return _gsd(repo, env, "query", "agent-skills", agent)


def _entries(proc):
    """A config-get list (the JSON form); a failed read or empty output counts as []."""
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    return json.loads(proc.stdout)


def _brief_install_step(repo, env):
    """The commit-fold SKILL.md step, as written: read each list, append the brief entry when it is
    absent, write the whole list back."""
    for agent in BRIEF_AGENTS:
        entries = _entries(_gsd(repo, env, "config-get", f"agent_skills.{agent}"))
        if UNIT_BRIEF not in entries:
            entries.append(UNIT_BRIEF)
        _gsd(repo, env, "config-set", f"agent_skills.{agent}", json.dumps(entries))


def _brief_lists(repo, env):
    return {agent: _entries(_gsd(repo, env, "config-get", f"agent_skills.{agent}"))
            for agent in BRIEF_AGENTS}


def _skill_section(heading, next_heading):
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    start = text.index(heading)
    return text[start:text.index(next_heading, start)]


@unittest.skipUnless(shutil.which("node") and GSD_TOOLS.is_file()
                     and (ROOT / ".claude" / "scripts").is_dir(),
                     "node or the checkout's project-local gsd-core is missing")
class TestAgentSkills(unittest.TestCase):
    # The rendered agent-skills blocks of an unfinished fixture after one boundary-wave run.
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-skills-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        home = cls.tmp / "home"
        home.mkdir()
        cls.env = _gsd_env(home, cls.tmp / "gsd-home")
        cls.repo = _installed_fixture(cls.tmp / "fixture", cls.env, summary=False)
        _wire_lenses(cls.repo, cls.env)
        cls.wave = _gsd(cls.repo, cls.env, "ai-kit-fold", "boundary-wave", "--phase", "7", "--raw")
        cls.blocks = {agent: _render(cls.repo, cls.env, agent) for agent in BRIEF_AGENTS}
        cls.checker = _render(cls.repo, cls.env, "gsd-ui-checker")
        cls.trusted = _gsd(cls.repo, cls.env, "config-get",
                           "agent_skills_security.trusted_global_roots")

    def test_each_brief_agent_renders_the_unit_brief_and_the_lens_brief(self):
        self.assertEqual(self.wave.returncode, 0, self.wave.stderr)
        for agent, proc in self.blocks.items():
            with self.subTest(agent=agent):
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("@.aikit/brief/SKILL.md", proc.stdout)
                self.assertIn("@.planning/lens-brief/SKILL.md", proc.stdout)

    def test_planner_reads_the_lens_brief_right_after_its_lens(self):
        lines = self.blocks["gsd-planner"].stdout.splitlines()
        lens_at = next(i for i, line in enumerate(lines) if "ponytail:ponytail" in line)
        self.assertEqual(lines[lens_at + 1], "- @.planning/lens-brief/SKILL.md")

    def test_a_missing_lens_still_renders_and_keeps_the_lens_brief_line(self):
        self.assertEqual(self.checker.returncode, 0, self.checker.stderr)
        self.assertIn("@.planning/lens-brief/SKILL.md", self.checker.stdout)

    def test_trusted_roots_are_the_literal_tilde_path(self):
        self.assertEqual(self.trusted.returncode, 0, self.trusted.stderr)
        self.assertEqual(json.loads(self.trusted.stdout), ["~/.agents/skills"])


@unittest.skipUnless(shutil.which("node") and GSD_TOOLS.is_file()
                     and (ROOT / ".claude" / "scripts").is_dir(),
                     "node or the checkout's project-local gsd-core is missing")
class TestMissingBrief(unittest.TestCase):
    # With the unit brief removed the renders still succeed, and the no-brief file is written again.
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-nobrief-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        home = cls.tmp / "home"
        home.mkdir()
        cls.env = _gsd_env(home, cls.tmp / "gsd-home")
        cls.repo = _installed_fixture(cls.tmp / "fixture", cls.env, summary=False)
        _wire_lenses(cls.repo, cls.env)
        _gsd(cls.repo, cls.env, "ai-kit-fold", "boundary-wave", "--phase", "7", "--raw")
        brief = cls.repo / ".aikit" / "brief" / "SKILL.md"
        brief.unlink()
        cls.blocks = {agent: _render(cls.repo, cls.env, agent) for agent in BRIEF_AGENTS}
        cls.rewritten = _gsd(cls.repo, cls.env, "ai-kit-fold", "boundary-wave", "--phase", "7",
                             "--raw")
        cls.brief_text = _brief_text(cls.repo)

    def test_each_brief_agent_still_renders_with_the_lens_brief_line(self):
        for agent, proc in self.blocks.items():
            with self.subTest(agent=agent):
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("@.planning/lens-brief/SKILL.md", proc.stdout)

    def test_every_boundary_run_writes_the_brief_again(self):
        self.assertEqual(self.rewritten.returncode, 0, self.rewritten.stderr)
        self.assertIn("point: wave", self.brief_text)


@unittest.skipUnless(shutil.which("node") and GSD_TOOLS.is_file()
                     and (ROOT / ".claude" / "scripts").is_dir(),
                     "node or the checkout's project-local gsd-core is missing")
class TestBriefInstallStep(unittest.TestCase):
    # The commit-fold SKILL.md step run as written, on a project whose lists were not pre-supplied.
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-install-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        home = cls.tmp / "home"
        home.mkdir()
        cls.env = _gsd_env(home, cls.tmp / "gsd-home")
        cls.repo = _installed_fixture(cls.tmp / "fixture", cls.env, summary=False)
        _gsd(cls.repo, cls.env, "config-set", "agent_skills.gsd-planner", '["skills/x"]')
        _brief_install_step(cls.repo, cls.env)
        cls.first = _brief_lists(cls.repo, cls.env)
        _brief_install_step(cls.repo, cls.env)
        cls.second = _brief_lists(cls.repo, cls.env)
        cls.wave = _gsd(cls.repo, cls.env, "ai-kit-fold", "boundary-wave", "--phase", "7", "--raw")
        cls.blocks = {agent: _render(cls.repo, cls.env, agent) for agent in BRIEF_AGENTS}
        cls.section = _skill_section("## GSD install", "## GSD hooks")

    def test_the_step_appends_the_brief_and_keeps_existing_entries(self):
        self.assertEqual(self.first, {"gsd-phase-researcher": [UNIT_BRIEF],
                                      "gsd-planner": ["skills/x", UNIT_BRIEF],
                                      "gsd-executor": [UNIT_BRIEF]})

    def test_running_the_step_twice_changes_nothing(self):
        self.assertEqual(self.first, self.second)

    def test_each_brief_agent_renders_the_unit_brief_after_one_boundary_wave(self):
        self.assertEqual(self.wave.returncode, 0, self.wave.stderr)
        for agent, proc in self.blocks.items():
            with self.subTest(agent=agent):
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("@.aikit/brief/SKILL.md", proc.stdout)

    def test_the_skill_section_names_the_step_it_runs(self):
        self.assertIn("config-get agent_skills.<agent>", self.section)
        self.assertIn('".aikit/brief"', self.section)


def _brief_text(repo):
    brief = repo / ".aikit" / "brief" / "SKILL.md"
    return brief.read_text(encoding="utf-8") if brief.is_file() else ""


@unittest.skipUnless(shutil.which("node") and GSD_TOOLS.is_file()
                     and (ROOT / ".claude" / "scripts").is_dir(),
                     "node or the checkout's project-local gsd-core is missing")
class TestStartLifecycle(unittest.TestCase):
    # The discuss:pre command, run as loop-hook-dispatch.md runs it: create, reuse, worktrees.
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p29.1-life-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        home = cls.tmp / "home"
        home.mkdir()
        cls.env = _gsd_env(home, cls.tmp / "gsd-home")
        cls.repo = _installed_fixture(cls.tmp / "fixture", cls.env)
        # The phase directory must exist where start runs: seed it on the pushed trunk, then drop
        # the local phase branch so the first start creates it from the trunk tip.
        run_git(cls.repo, cls.env, "checkout", "-q", "main")
        commit(cls.repo, cls.env, {".planning/phases/07-demo/07-SEED.md": b"seed\n"},
               "docs(07): seed phase dir on trunk")
        run_git(cls.repo, cls.env, "push", "-q", "origin", "main")
        run_git(cls.repo, cls.env, "branch", "-D", "gsd/phase-07-demo")
        cls.trunk = run_git(cls.repo, cls.env, "rev-parse", "origin/main").strip()

    def _start_command(self):
        proc = _gsd(self.repo, self.env, "loop", "render-hooks", "discuss:pre", "--raw")
        command = _fold_hooks(proc)[0]["ref"]["command"]
        self.assertRegex(command, COMMAND_GRAMMAR)
        return command.split()

    def _branch(self):
        return run_git(self.repo, self.env, "rev-parse", "--abbrev-ref", "HEAD").strip()

    def test_start_creates_the_unit_branch_at_the_trunk_tip_and_planning_commits_land_on_it(self):
        argv = self._start_command()
        first = _gsd(self.repo, self.env, *argv, "--phase", "07", "--raw")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(self._branch(), "gsd/phase-07-demo")
        self.assertEqual(run_git(self.repo, self.env, "rev-parse", "HEAD").strip(), self.trunk)
        commit(self.repo, self.env, {".planning/phases/07-demo/07-CONTEXT.md": b"context\n"},
               "docs(07): capture phase context")
        self.assertEqual(run_git(self.repo, self.env, "rev-parse", "HEAD^").strip(), self.trunk)
        again = _gsd(self.repo, self.env, *argv, "--phase", "07", "--raw")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertEqual(self._branch(), "gsd/phase-07-demo")
        self.assertEqual(run_git(self.repo, self.env, "rev-parse", "HEAD^").strip(), self.trunk)
        sys.path.insert(0, str(SKILL / "scripts"))
        import flow_record  # pylint: disable=import-outside-toplevel
        self.assertEqual(len(flow_record.read_record(self.repo)["units"]), 1)

    def test_use_worktrees_true_sets_the_base_ref_to_head(self):
        _gsd(self.repo, self.env, "config-set", "workflow.use_worktrees", "true")
        proc = _gsd(self.repo, self.env, *self._start_command(), "--phase", "07", "--raw")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        settings = json.loads((self.repo / ".claude" / "settings.local.json").read_text())
        self.assertEqual(settings["worktree"]["baseRef"], "head")

    def test_use_worktrees_false_writes_no_settings_file(self):
        plain = _installed_fixture(self.tmp / "plain", self.env)
        _gsd(plain, self.env, "config-set", "workflow.use_worktrees", "false")
        proc = _gsd(plain, self.env, *self._start_command(), "--phase", "07", "--raw")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse((plain / ".claude" / "settings.local.json").exists())


@unittest.skipUnless(shutil.which("node") and GSD_TOOLS.is_file()
                     and (ROOT / ".claude" / "scripts").is_dir(),
                     "node or the checkout's project-local gsd-core is missing")
class TestHookCheckpointReady(unittest.TestCase):
    # The execute:wave:post step and the ready verb, run as hook dispatch runs them, against a
    # fake gh. Ready is refused before VERIFICATION.md passes, then marks the PR ready.
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p29.1-ready-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        home = cls.tmp / "home"
        home.mkdir()
        cls.env = _gsd_env(home, cls.tmp / "gsd-home")
        cls.repo = _installed_fixture(cls.tmp / "fixture", cls.env)
        # The discuss:pre start creates the phase branch from the trunk tip, so the trunk must hold
        # the phase directory and the phase's commits go on the new branch (as TestStartLifecycle).
        run_git(cls.repo, cls.env, "checkout", "-q", "main")
        commit(cls.repo, cls.env, {f"{PHASE_DIR}/07-SEED.md": b"seed\n"},
               "docs(07): seed phase dir on trunk")
        run_git(cls.repo, cls.env, "push", "-q", "origin", "main")
        run_git(cls.repo, cls.env, "branch", "-D", "gsd/phase-07-demo")
        cls.start = _gsd(cls.repo, cls.env, "ai-kit-fold", "start", "--phase", "07", "--raw")
        commit(cls.repo, cls.env, {f"{PHASE_DIR}/07-01-PLAN.md":
                                   gsd_plan_text("01", ("a", "b")).encode()},
               "docs(07): create phase plan")
        for files, message, author in gsd_plan_commits("01", ("a", "b")):
            commit(cls.repo, cls.env, files, message, author)
        consent = subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "fold.py"), "consent", "grant",
             "--add-exclude", "--repo", str(cls.repo)],
            capture_output=True, text=True, env=cls.env, check=False)
        if consent.returncode != 0:
            raise RuntimeError(consent.stderr)
        cls.state = cls.tmp / "forge.json"
        cls.log = cls.tmp / "gh.log"
        bin_dir = cls.tmp / "bin"
        forge_fakes.write_forge_fakes(bin_dir, cls.state, cls.log, gh_stack=False)
        cls.env["PATH"] = host_fakes.host_path(bin_dir, cls.env["PATH"])
        wave_post = _fold_hooks(_gsd(cls.repo, cls.env, "loop", "render-hooks",
                                     "execute:wave:post", "--raw"))
        cls.wave_post = wave_post
        cls.checkpoint_command = wave_post[0]["ref"]["command"] if wave_post else ""
        cls.checkpoint_run = _gsd(cls.repo, cls.env, *cls.checkpoint_command.split(),
                                  "--phase", "07", "--raw")
        cls.unverified = _gsd(cls.repo, cls.env, "ai-kit-fold", "ready", "--phase", "07", "--raw")
        cls.unverified_ready = [c["argv"] for c in host_fakes.fake_calls(cls.log)
                                if c["argv"][:2] == ["pr", "ready"]]
        verification = cls.repo / PHASE_DIR / "07-VERIFICATION.md"
        verification.write_text("---\nstatus: passed\n---\n", encoding="utf-8")
        cls.ready = _gsd(cls.repo, cls.env, "ai-kit-fold", "ready", "--phase", "07", "--raw")
        ship = _fold_hooks(_gsd(cls.repo, cls.env, "loop", "render-hooks", "ship:pre", "--raw"))
        cls.ship_predicate = ship[0]["check"]["predicate"] if ship else None
        cls.ship_verdict = _json(_predicate_eval(cls.repo, cls.env, cls.ship_predicate).stdout) \
            if ship else {}

    def test_wave_post_step_folds_and_pushes_the_plan_with_a_draft_pr(self):
        self.assertEqual(len(self.wave_post), 1)
        self.assertRegex(self.checkpoint_command, COMMAND_GRAMMAR)
        self.assertEqual(self.checkpoint_run.returncode, 0,
                         self.checkpoint_run.stdout + self.checkpoint_run.stderr)
        self.assertIn("folded", self.checkpoint_run.stdout)
        local = run_git(self.repo, self.env, "rev-parse", "gsd/phase-07-demo").strip()
        remote = run_git(self.repo, self.env, "ls-remote", "origin",
                         "refs/heads/gsd/phase-07-demo").split()[0]
        self.assertEqual(remote, local)
        creates = [c["argv"] for c in host_fakes.fake_calls(self.log)
                   if c["argv"][:2] == ["pr", "create"]]
        self.assertEqual(len(creates), 1)
        self.assertIn("--draft", creates[0])

    def test_ready_is_refused_until_verification_passes_then_marks_the_pr_ready(self):
        self.assertEqual(self.unverified.returncode, 1, self.unverified.stdout)
        self.assertIn("not_verified", self.unverified.stdout)
        self.assertEqual(self.unverified_ready, [])
        self.assertEqual(self.ready.returncode, 0, self.ready.stdout + self.ready.stderr)
        self.assertFalse(forge_fakes.forge_state(self.state)["prs"][0]["isDraft"])
        self.assertIn(["pr", "ready", "1", "--repo", "ai-kit-fixture/demo"],
                      [c["argv"] for c in host_fakes.fake_calls(self.log)])

    def test_ship_gate_still_blocks_after_ready_with_ship_redirect(self):
        self.assertTrue(self.ship_verdict.get("block"), self.ship_verdict)
        self.assertIn("ship_redirect", self.ship_verdict["message"])
        self.assertIn("fold.py merge-chain", self.ship_verdict["message"])


if __name__ == "__main__":
    unittest.main()
