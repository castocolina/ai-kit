"""Unit tier: the Phase 19 eval helper's oracle, snapshot, digest and matrix env, hermetically.

No node, no CLI, no real home: every subprocess seam is an injected `run_fn`, every path is a
`tempfile` directory, and each negative case is paired with the positive case proving the check
is not vacuous.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import pathlib
import shutil
import tempfile
import unittest
from argparse import Namespace
from types import SimpleNamespace

from tests import gsd_curated_eval as ev


def _tables() -> dict:
    """A small stand-in for the live tables: two agents, one shared key set."""
    return {
        "profiles": {
            "gsd-planner": {"adaptive": "opus", "budget": "haiku", "quality": "opus"},
            "gsd-executor": {"adaptive": "sonnet", "budget": "haiku", "quality": "opus"},
        },
        "phase": {"gsd-planner": "planning", "gsd-executor": "execution"},
    }


def _plan(entries: list[dict] | None = None, profile: str = "adaptive") -> dict:
    return {"profile": profile, "entries": entries or []}


def _set(key: str, value: object, op: str = "set") -> dict:
    return {"op": op, "key": key, "value": value}


def _unset(key: str) -> dict:
    return _set(key, None, "unset")


def _completed(payload: object):
    stdout = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="", args=[])


class _StopRun(Exception):
    """Raised by an injected seam to stop a matrix run at a chosen step."""


def _ctx(**kwargs) -> ev._MatrixCtx:
    """A matrix context whose every seam is inert unless the test overrides it."""
    fields: dict = {
        "node_bin": "node",
        "tools_path": "/tools/gsd-tools.cjs",
        "home": "/home",
        "host": "claude",
        "core_root": "/core",
        "bundle_fn": lambda *a, **_kw: (_ for _ in ()).throw(_StopRun("bundle")),
        "apply_fn": lambda *a, **_kw: (0, {"applied": True}, "", ""),
        "run_fn": lambda *a, **_kw: _completed({}),
        "tables_fn": lambda *a, **_kw: _tables(),
    }
    fields.update(kwargs)
    return ev._MatrixCtx(**fields)


def _run_returning(payload):
    """A `run_fn` seam whose stdout is exactly `payload`."""

    def run_fn(cmd, **kw):
        return _completed(payload)

    return run_fn


class TestOracle(unittest.TestCase):
    def test_override_wins(self) -> None:
        plan = _plan([_set("model_overrides.gsd-planner", "moon"), _set("models.planning", "mars")])
        self.assertEqual(ev.promised("gsd-planner", plan, _tables()), "moon")

    def test_phase_shift_wins_over_profile(self) -> None:
        plan = _plan([_set("models.planning", "mars")])
        self.assertEqual(ev.promised("gsd-planner", plan, _tables()), "mars")
        both = _plan([_set("models.planning", "mars"), _set("model_overrides.gsd-planner", "moon")])
        self.assertEqual(ev.promised("gsd-planner", both, _tables()), "moon")

    def test_profile_default(self) -> None:
        tables = _tables()
        self.assertEqual(ev.promised("gsd-planner", _plan(), tables), "opus")
        self.assertEqual(ev.promised("gsd-executor", _plan(), tables), "sonnet")
        self.assertEqual(ev.promised("gsd-executor", _plan(profile="budget"), tables), "haiku")

    def test_promised_requires_a_live_entry(self) -> None:
        """Non-vacuity for `test_profile_default`: a profile the live table does not carry is a
        hard failure, not a silently-empty promise."""
        with self.assertRaises(ev._refusal) as caught:
            ev.promised("gsd-planner", _plan(profile="unknown"), _tables())
        self.assertIn("no live MODEL_PROFILES entry", str(caught.exception))

    def test_empty_model_fails(self) -> None:
        got = {"model": "", "tier": "", "profile": "", "effort": ""}
        self.assertEqual(ev.compare("gsd-planner", got, "opus"), "empty model for gsd-planner")
        # the same call with a real model passes: the failure is the emptiness, not the shape
        self.assertIsNone(ev.compare("gsd-planner", {"model": "opus", "tier": "opus"}, "opus"))

    def test_inheritance_promised_accepts_empty(self) -> None:
        got = {"model": "", "tier": "", "profile": "", "effort": ""}
        self.assertIsNone(ev.compare("gsd-planner", got, "", inheritance_promised=True))
        promised = ev.promised("gsd-planner", _plan(), _tables(), inheritance_promised=True)
        self.assertEqual(promised, "")

    def test_tier_mismatch_detected(self) -> None:
        wrong = {"model": "opus", "tier": "sonnet", "profile": "", "effort": ""}
        self.assertEqual(ev.compare("gsd-planner", wrong, "opus"), "tier")
        self.assertIsNone(ev.compare("gsd-planner", {"model": "opus", "tier": "opus"}, "opus"))
        # a concrete model id is not a tier alias, so its tier field is not graded
        concrete = {"model": "gpt-5.6", "tier": "haiku", "profile": "", "effort": ""}
        self.assertIsNone(ev.compare("gsd-planner", concrete, "gpt-5.6"))

    def test_wrong_model_detected(self) -> None:
        got = {"model": "sonnet", "tier": "sonnet", "profile": "", "effort": ""}
        self.assertEqual(ev.compare("gsd-planner", got, "opus"), "model")

    def test_key_parity_mismatch_exits(self) -> None:
        """`live_tables` asserts both tables cover the same agents before any comparison."""
        def run_fn(cmd, **kw):
            return _completed({
                "profiles": {"gsd-planner": {"adaptive": "opus"},
                             "gsd-extra": {"adaptive": "opus"}},
                "phase": {"gsd-planner": "planning"},
            })
        with self.assertRaises(ev._refusal) as caught:
            ev.live_tables("node", "/core", run_fn=run_fn)
        self.assertEqual(caught.exception.exit_code, 1)
        self.assertIn("agent key sets differ: gsd-extra", caught.exception.reason)

    def test_key_parity_match_returns_tables(self) -> None:
        """Non-vacuity: the same injection with matching key sets returns the tables."""
        tables = _tables()
        self.assertEqual(
            ev.live_tables("node", "/core", run_fn=lambda cmd, **kw: _completed(tables)), tables
        )

    def test_live_tables_unreadable_exits(self) -> None:
        for payload in ({"profiles": {}, "phase": {}}, {"profiles": {"a": {}}}, "null"):
            with self.subTest(payload=payload):
                with self.assertRaises(ev._refusal) as caught:
                    ev.live_tables("node", "/core", run_fn=_run_returning(payload))
                self.assertIn("unreadable", caught.exception.reason)

    def test_live_tables_spawn_failure_exits(self) -> None:
        def run_fn(cmd, **kw):
            raise OSError("no node")

        with self.assertRaises(ev._refusal) as caught:
            ev.live_tables("node", "/core", run_fn=run_fn)
        self.assertIn("unavailable", str(caught.exception))

    def test_mismatch_rows_are_sorted_and_shaped(self) -> None:
        tables, plan = _tables(), _plan()
        agents = sorted(tables["profiles"])
        rows = ev._mismatches(agents, plan, tables, {
            "gsd-executor": {"model": "haiku", "tier": "haiku"},
            "gsd-planner": {"model": "sonnet", "tier": "sonnet"},
        })
        self.assertEqual(rows, [
            ["gsd-executor", "sonnet", "haiku", "haiku"],
            ["gsd-planner", "opus", "sonnet", "sonnet"],
        ])
        clean = ev._mismatches(agents, plan, tables, {
            "gsd-executor": {"model": "sonnet", "tier": "sonnet"},
            "gsd-planner": {"model": "opus", "tier": "opus"},
        })
        self.assertEqual(clean, [])


class _ScratchPaths(unittest.TestCase):
    """A scratch repo root and a scratch home, both seeded with the protected files."""

    def setUp(self) -> None:
        self.scratch = tempfile.mkdtemp(prefix="xai-snap-")
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)
        self.repo = os.path.join(self.scratch, "repo")
        self.home = os.path.join(self.scratch, "home")
        self.seed()

    def seed(self) -> None:
        self.write(os.path.join(self.repo, ".planning", "config.json"), '{"x": 1}\n')
        self.write(os.path.join(self.repo, ".planning", "config.json.bak-1"), '{"x": 0}\n')
        self.write(os.path.join(self.repo, ".planning", "scripts", "cross-ai.mjs"), "// runner\n")
        self.write(os.path.join(self.home, ".gsd", "defaults.json"), "{}\n")
        self.write(os.path.join(self.home, ".gsd", "state.md"), "state\n")
        self.write(os.path.join(self.home, ".claude", "settings.json"), "{}\n")
        self.write(os.path.join(self.home, ".claude", "CLAUDE.md"), "claude-rules\n")
        self.write(os.path.join(self.home, ".claude", "plugins", "marketplaces.json"), "[]\n")
        self.write(os.path.join(self.home, ".claude", "plugins", "credentials.json"), "SECRET\n")
        self.write(os.path.join(self.home, ".claude", "skills", "a", "SKILL.md"), "s\n")
        self.write(os.path.join(self.home, ".cursor", "cli-config.json"), '{"model":"x"}\n')
        self.write(os.path.join(self.home, ".config", "opencode", "opencode.jsonc"), "// oc\n")
        self.write(os.path.join(self.home, ".codex", "config.toml"), 'model = "gpt"\n')

    @staticmethod
    def write(path: str, text: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def snap(self) -> dict:
        return ev.snapshot(self.repo, self.home)


class TestSnapshot(_ScratchPaths):
    def test_identical_passes(self) -> None:
        self.assertEqual(ev.snapshot_diff(self.snap(), self.snap()), ([], []))

    def test_strict_change_fails(self) -> None:
        before = self.snap()
        self.write(os.path.join(self.home, ".claude", "settings.json"), '{"x": 2}\n')
        strict, host = ev.snapshot_diff(before, self.snap())
        self.assertEqual(strict, [f"{ev.HOME_LABEL}/.claude/settings.json"])
        self.assertEqual(host, [])

    def test_host_managed_change_reported_not_failed(self) -> None:
        before = self.snap()
        self.write(os.path.join(self.home, ".claude", "plugins", "marketplaces.json"), "[1]\n")
        strict, host = ev.snapshot_diff(before, self.snap())
        self.assertEqual(strict, [])
        self.assertEqual(host, [f"{ev.HOME_LABEL}/.claude/plugins/marketplaces.json"])
        lines, failed = ev._snapshot_report(before, self.snap())
        self.assertEqual((failed, lines), (False, [f"changed (host-managed) {host[0]}"]))

    def test_report_lines_name_labels_only(self) -> None:
        before = self.snap()
        self.write(os.path.join(self.home, ".gsd", "defaults.json"), '{"y": 2}\n')
        lines, failed = ev._snapshot_report(before, self.snap())
        self.assertTrue(failed)
        self.assertEqual(lines, [f"changed {ev.HOME_LABEL}/.gsd/defaults.json"])

    def test_listing_change_detected(self) -> None:
        before = self.snap()
        self.write(os.path.join(self.home, ".gsd", "new-file.md"), "n\n")
        strict, _host = ev.snapshot_diff(before, self.snap())
        self.assertEqual(strict, [f"{ev.HOME_LABEL}/.gsd"])

    def test_absence_is_a_change(self) -> None:
        """Deleting a protected file is a strict change: a `null` value is still a value."""
        before = self.snap()
        os.remove(os.path.join(self.home, ".gsd", "defaults.json"))
        strict, _host = ev.snapshot_diff(before, self.snap())
        self.assertIn(f"{ev.HOME_LABEL}/.gsd/defaults.json", strict)

    def test_cursor_config_change_is_strict(self) -> None:
        """`cursor-agent models` rewrites `~/.cursor/cli-config.json`, so it must fail a batch;
        the codex config, which no probe is documented to rewrite, is a host-managed tripwire."""
        before = self.snap()
        self.write(os.path.join(self.home, ".cursor", "cli-config.json"), '{"model":"y"}\n')
        self.write(os.path.join(self.home, ".codex", "config.toml"), 'model = "other"\n')
        strict, host = ev.snapshot_diff(before, self.snap())
        self.assertEqual(strict, [f"{ev.HOME_LABEL}/.cursor/cli-config.json"])
        self.assertEqual(host, [f"{ev.HOME_LABEL}/.codex/config.toml"])

    def test_credentials_file_is_never_snapshot(self) -> None:
        """The Claude credentials file is read by nothing here, not even to hash it."""
        snap = self.snap()
        keys = " ".join(list(snap["strict"]) + list(snap["host_managed"]))
        self.assertNotIn("credentials.json", keys)

    def test_no_absolute_paths_or_values_in_output(self) -> None:
        text = json.dumps(self.snap(), sort_keys=True)
        for secret in (self.repo, self.home, self.scratch, "SECRET", "claude-rules", "// runner"):
            self.assertNotIn(secret, text)
        self.assertIn(f"{ev.WORKTREE_LABEL}/.planning/config.json", text)
        self.assertIn(f"{ev.HOME_LABEL}/.cursor/cli-config.json", text)

    def test_gsd_core_tree_hash_moves_with_the_bytes(self) -> None:
        """The tree entry is one hash under its label; a byte change moves it."""
        label = ev.GSD_CORE_LABEL
        bin_dir = os.path.join(self.repo, ".claude", "gsd-core", "bin")
        self.assertIsNone(self.snap()["strict"][label])
        self.write(os.path.join(bin_dir, "gsd-tools.cjs"), "// v1\n")
        before = self.snap()["strict"][label]
        self.write(os.path.join(bin_dir, "gsd-tools.cjs"), "// v2\n")
        self.assertNotEqual(before, self.snap()["strict"][label])

    def test_snapshot_writes_and_checks_a_file(self) -> None:
        """The CLI shape the batch rails use: `--out` then `--check` prints `snapshot ok`."""
        out = os.path.join(self.scratch, "snap.json")
        with contextlib.redirect_stdout(io.StringIO()) as sink:
            code = ev._cmd_snapshot(Namespace(out=out, check=None,
                                                    home=pathlib.Path(self.home)))
            self.assertEqual(code, 0)
            self.assertNotIn(self.home, sink.getvalue())
            text = pathlib.Path(out).read_text(encoding="utf-8")
            self.assertNotIn(self.scratch, text)
            code = ev._cmd_snapshot(Namespace(out=None, check=out,
                                                    home=pathlib.Path(self.home)))
        self.assertEqual(code, 0)
        self.assertIn("snapshot ok", sink.getvalue())

    def test_snapshot_check_reports_a_strict_change_and_exits_1(self) -> None:
        out = os.path.join(self.scratch, "snap.json")
        with contextlib.redirect_stdout(io.StringIO()):
            ev._cmd_snapshot(Namespace(out=out, check=None, home=pathlib.Path(self.home)))
        self.write(os.path.join(self.home, ".gsd", "defaults.json"), '{"z": 9}\n')
        with contextlib.redirect_stdout(io.StringIO()) as sink:
            code = ev._cmd_snapshot(Namespace(out=None, check=out,
                                                    home=pathlib.Path(self.home)))
        self.assertEqual(code, 1)
        self.assertEqual(sink.getvalue().strip(), f"changed {ev.HOME_LABEL}/.gsd/defaults.json")


class TestDigest(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.mkdtemp(prefix="xai-digest-")
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)
        self.skill = os.path.join(self.scratch, "skills", "demo-skill")
        self.write(os.path.join(self.skill, "SKILL.md"), "# skill\n")
        self.write(os.path.join(self.skill, "references", "one.md"), "one\n")
        self.write(os.path.join(self.skill, "references", "sub", "two.md"), "two\n")
        self.write(os.path.join(self.skill, "scripts", "not-read.py"), "x = 1\n")

    @staticmethod
    def write(path: str, text: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def evidence(self, text: str) -> str:
        path = os.path.join(self.scratch, "evidence.md")
        self.write(path, text)
        return path

    def test_matches_digest_cmd_formula(self) -> None:
        """The helper's digest equals 18.1-21's DIGEST_CMD formula, computed inline."""
        digest = hashlib.sha256()
        for rel in ("SKILL.md", "references/one.md", "references/sub/two.md"):
            with open(os.path.join(self.skill, rel), "rb") as handle:
                digest.update(rel.encode() + b"\0" + hashlib.sha256(handle.read()).digest())
        self.assertEqual(ev.skill_digest(self.skill), digest.hexdigest()[:16])
        self.assertRegex(ev.skill_digest(self.skill), r"^[0-9a-f]{16}$")

    def test_digest_moves_with_the_bytes(self) -> None:
        """Non-vacuity: the digest is over the bytes, not over the file names."""
        before = ev.skill_digest(self.skill)
        self.write(os.path.join(self.skill, "references", "one.md"), "one changed\n")
        self.assertNotEqual(ev.skill_digest(self.skill), before)

    def test_check_rejects_zero_row(self) -> None:
        digest = ev.skill_digest(self.skill)
        path = self.evidence(f"| scenario | {'0' * 16} | note |\n")
        self.assertEqual(ev.check_digests([path], digest),
                         [f"{path}: {'0' * 16} != {digest}"])

    def test_check_accepts_matching_live_row(self) -> None:
        digest = ev.skill_digest(self.skill)
        self.assertEqual(ev.check_digests([self.evidence(f"| s | {digest} | ok |\n")], digest), [])

    def test_check_skips_superseded_and_context(self) -> None:
        digest = ev.skill_digest(self.skill)
        stale = "0" * 16
        path = self.evidence(
            f"| a | {stale} | superseded ({digest}) |\n| context | {stale} | history |\n"
            f"| b | {digest} | live |\n"
        )
        self.assertEqual(ev.check_digests([path], digest), [])

    def test_check_requires_live_row(self) -> None:
        path = self.evidence("# notes\n\nno table here\n")
        self.assertEqual(ev.check_digests([path], "0" * 16), [f"{path}: no live row"])

    def test_check_names_an_unreadable_file(self) -> None:
        problems = ev.check_digests([os.path.join(self.scratch, "gone.md")], "0" * 16)
        self.assertEqual(len(problems), 1)
        self.assertIn("unreadable", problems[0])


class TestMatrixEnv(unittest.TestCase):
    def bundle(self) -> dict:
        return {
            "resolve_env": {"GSD_HOME": "/scratch/gsd_home", "XDG_CACHE_HOME": "/scratch/xdg",
                            "RUNTIME_DIR": "/repo", "PATH": "/usr/bin"},
            "child_env": {"GSD_HOME": "/scratch/gsd_home", "PATH": "/usr/bin"},
            "project": "/scratch/project",
            "plan_path": "/scratch/plan.json",
            "inv_path": "/scratch/inv.json",
        }

    def test_matrix_env_real_home_scratch_gsd_home(self) -> None:
        env = ev.matrix_env(self.bundle(), "/real/home")
        self.assertEqual(env["HOME"], "/real/home")
        self.assertEqual(env["GSD_HOME"], "/scratch/gsd_home")
        self.assertEqual(env["XDG_CACHE_HOME"], "/scratch/xdg")
        self.assertEqual(env["RUNTIME_DIR"], "/repo")
        self.assertEqual(env["GSD_RUNTIME"], "claude")

    def test_matrix_env_host_parameter(self) -> None:
        env = ev.matrix_env(self.bundle(), "/real/home", "codex")
        self.assertEqual(env["GSD_RUNTIME"], "codex")
        self.assertEqual(env["HOME"], "/real/home")

    def test_apply_bundle_passes_one_env_to_both_seams(self) -> None:
        seen: list[tuple] = []

        def apply_fn(*args):
            seen.append(args)
            return (0, {"applied": True}, "", "")

        bundle = self.bundle()
        env = ev._apply_bundle(bundle, "/real/home", "node", apply_fn)
        self.assertEqual(len(seen), 1)
        self.assertIs(seen[0][3], seen[0][4], "resolve_env and child_env must be one dict")
        self.assertEqual(seen[0][3], env)
        self.assertEqual(seen[0][3]["HOME"], "/real/home")
        self.assertEqual(seen[0][5], "node")

    def test_matrix_refuses_non_claude_host(self) -> None:
        built: list = []

        def bundle_fn(*args, **kwargs):
            built.append(args)
            raise _StopRun

        ctx = _ctx(bundle_fn=bundle_fn)
        with self.assertRaises(ev._refusal) as caught:
            ev.run_matrix("node", "/tools/gsd-tools.cjs", "/home", "codex", ctx)
        self.assertEqual(caught.exception.exit_code, 2)
        self.assertEqual(built, [], "the refusal must precede any bundle build")
        self.assertIn("matrix oracle supports claude only", caught.exception.reason)
        self.assertIn("Phase 20", caught.exception.reason)


class TestMatrixShape(unittest.TestCase):
    """The matrix's own bookkeeping, with every external seam injected."""

    def bundle(self, scratch: str) -> dict:
        return {
            "resolve_env": {"GSD_HOME": os.path.join(scratch, "gsd_home"), "PATH": "/usr/bin"},
            "child_env": {"PATH": "/usr/bin"},
            "project": os.path.join(scratch, "project"),
            "plan_path": os.path.join(scratch, "plan.json"),
            "inv_path": os.path.join(scratch, "inv.json"),
            "start": "P1",
        }

    def collect_scratches(self) -> list:
        created: list = []
        self.addCleanup(lambda: [shutil.rmtree(p, ignore_errors=True) for p in created])
        return created

    def test_claude_host_reaches_the_bundle_builder(self) -> None:
        """Non-vacuity: the refusal above is the host check, not an early return."""
        built: list = []

        def bundle_fn(*args, **kwargs):
            built.append(kwargs)
            raise _StopRun

        with self.assertRaises(_StopRun):
            ev.run_matrix("node", "/tools/gsd-tools.cjs", "/home", "claude",
                          _ctx(bundle_fn=bundle_fn))
        self.assertEqual(len(built), 1)
        self.assertEqual(built[0]["host_name"], "claude")

    def test_apply_bundle_reports_a_failed_apply(self) -> None:
        def apply_fn(*args):
            return (4, None, "", "boom in stderr")

        with self.assertRaises(ev._refusal) as caught:
            ev._apply_bundle(self.bundle("/scratch"), "/real/home", "node", apply_fn)
        self.assertEqual(caught.exception.exit_code, 1)
        self.assertIn("matrix apply failed (exit 4)", caught.exception.reason)
        self.assertIn("boom in stderr", caught.exception.reason)

    def test_bundle_for_poisons_p2_and_marks_the_combo(self) -> None:
        created = self.collect_scratches()
        seen: dict = {}

        def bundle_fn(path, **kwargs):
            created.append(path)
            seen.update(kwargs)
            return self.bundle(path)

        bundle = ev._bundle_for(_ctx(bundle_fn=bundle_fn), ("rigorous", "quality"), "P2",
                                ev.POISON_DEFAULTS)
        self.assertEqual(seen["rigor"], "rigorous")
        self.assertEqual(seen["profile"], "quality")
        self.assertEqual(seen["host_name"], "claude")
        self.assertFalse(seen["with_planning"])
        self.assertIsNotNone(seen["pre_inventory"], "P2 must seed the config pre-inventory")
        self.assertEqual(bundle["combo"], "rigorous/quality")
        self.assertEqual(bundle["start"], "P2")
        # the poison is deep-copied: a mutation inside one bundle cannot leak to the next
        seen["defaults"]["resolve_model_ids"] = "tampered"
        self.assertEqual(ev.POISON_DEFAULTS["resolve_model_ids"], "omit")

    def test_bundle_for_removes_scratch_when_the_builder_fails(self) -> None:
        """Non-vacuity for the cleanup above: a builder that raises leaves no scratch dir."""
        seen: list[str] = []

        def bundle_fn(path, **kwargs):
            seen.append(path)
            raise _StopRun

        with self.assertRaises(_StopRun):
            ev._bundle_for(_ctx(bundle_fn=bundle_fn), ("standard", "adaptive"), "P1", None)
        self.assertEqual(len(seen), 1)
        self.assertFalse(os.path.exists(seen[0]))

    def test_p1_bundle_has_no_seeder_and_no_defaults(self) -> None:
        created = self.collect_scratches()
        seen: dict = {}

        def bundle_fn(path, **kwargs):
            created.append(path)
            seen.update(kwargs)
            return self.bundle(path)

        ev._bundle_for(_ctx(bundle_fn=bundle_fn), ("standard", "adaptive"), "P1", None)
        self.assertIsNone(seen["pre_inventory"])
        self.assertIsNone(seen["defaults"])

    def test_unoverridden_lists_only_agents_without_an_override(self) -> None:
        plan = _plan([_set("model_overrides.gsd-planner", "moon"), _unset("resolve_model_ids")])
        self.assertEqual(ev._unoverridden(["gsd-planner", "gsd-executor"], plan), ["gsd-executor"])

    def test_write_control_plan_drops_only_the_unset_entry(self) -> None:
        scratch = tempfile.mkdtemp(prefix="xai-control-")
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        plan_path = os.path.join(scratch, "plan.json")
        bundle = {"plan_path": plan_path}
        ev._write_control_plan(bundle, _plan([
            _unset("resolve_model_ids"), _set("models.planning", "mars"),
        ]))
        self.assertTrue(bundle["plan_path"].endswith("plan-control1.json"))
        written = json.loads(pathlib.Path(bundle["plan_path"]).read_text(encoding="utf-8"))
        self.assertEqual([e["key"] for e in written["entries"]], ["models.planning"])
        self.assertEqual(written["profile"], "adaptive")

    def test_write_control_plan_requires_the_entry(self) -> None:
        """Non-vacuity: a plan without the unset cannot drive Control 1."""
        scratch = tempfile.mkdtemp(prefix="xai-control-")
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        with self.assertRaises(ev._refusal) as caught:
            ev._write_control_plan({"plan_path": os.path.join(scratch, "plan.json")},
                                   _plan([_set("models.planning", "mars")]))
        self.assertIn("no resolve_model_ids entry", str(caught.exception))

    def test_resolve_model_parses_stdout_only(self) -> None:
        calls: list[list[str]] = []

        def run_fn(cmd, **kwargs):
            calls.append(cmd)
            return _completed({"model": "opus", "tier": "opus"})

        got = ev._resolve_model(_ctx(run_fn=run_fn), "gsd-planner", "/scratch/project",
                                {"HOME": "/real"})
        self.assertEqual(got["model"], "opus")
        self.assertEqual(got["effort"], "")
        self.assertEqual(calls[0], ["node", "/tools/gsd-tools.cjs", "resolve-model",
                                    "gsd-planner", "--cwd", "/scratch/project"])

    def test_resolve_model_failure_reads_as_empty(self) -> None:
        broken = _ctx(run_fn=lambda cmd, **kw: (_ for _ in ()).throw(OSError("no node")))
        self.assertEqual(ev._resolve_model(broken, "gsd-planner", "/p", {})["model"], "")
        garbage = _ctx(run_fn=lambda cmd, **kw: _completed("not json"))
        self.assertEqual(ev._resolve_model(garbage, "gsd-planner", "/p", {})["model"], "")

    def test_seed_runtime_key_requires_the_readback(self) -> None:
        """`runtime not seeded` is the message when gsd-tools refuses or reads back a miss."""
        calls: list[list[str]] = []

        def run_fn(cmd, **kwargs):
            calls.append(cmd)
            return _completed({"success": True, "value": None if "config-set" in cmd else "wrong"})

        ctx = _ctx(run_fn=run_fn)
        bundle = self.bundle("/scratch")
        with self.assertRaises(ev._refusal) as caught:
            ev._seed_runtime_key(ctx, bundle, {"PATH": "/usr/bin"})
        self.assertIn("runtime not seeded", str(caught.exception))


class TestLabels(unittest.TestCase):
    def test_label_path_placeholders(self) -> None:
        scratch = tempfile.mkdtemp(prefix="xai-label-")
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        self.assertEqual(ev.label_path(ev.REPO_ROOT / "tools" / "setup.py"),
                         "<worktree>/tools/setup.py")
        self.assertEqual(ev.label_path(ev.REPO_ROOT), "<worktree>")
        self.assertEqual(ev.label_path(str(pathlib.Path.home())), "<home>")
        # an explicit scratch root reads as `<scratch>` itself; a bare mkdtemp path under the
        # system temp dir reads as a `<scratch>` child - never a machine path
        self.assertEqual(ev.label_path(scratch, scratch), "<scratch>")
        self.assertEqual(ev.label_path(os.path.join(scratch, "project"), scratch),
                         "<scratch>/project")
        self.assertEqual(ev.label_path(scratch), f"<scratch>/{os.path.basename(scratch)}")
        self.assertNotIn(scratch, ev.label_path(scratch))

    def test_scratch_under_the_repo_still_labels_as_scratch(self) -> None:
        inside = ev.REPO_ROOT / "tmp" / "xai-nested"
        self.assertEqual(ev.label_path(inside, inside), "<scratch>")


class TestVersionGuard(unittest.TestCase):
    def test_supported_lines(self) -> None:
        for version in ("1.16.0", "1.17.0"):
            self.assertTrue(ev.gsd_version_supported(version), version)
        for version in (None, "", "1.15.0", "2.0.0", "1.16"):
            self.assertFalse(ev.gsd_version_supported(version), version)

    def test_run_reason_names_the_blocker(self) -> None:
        self.assertEqual(ev.gsd_run_reason(None, "/tools"), "no node executable")
        missing = os.path.join(tempfile.gettempdir(), "xai-absent-gsd-tools.cjs")
        self.assertIn("no checkout-local gsd-tools", ev.gsd_run_reason("node", missing))

    def test_guard_prefixes_are_the_verified_lines(self) -> None:
        """The helper and the apply e2e tier share one prefix tuple, and it names the two
        lines this phase verified (1.16.0 and the 1.17.0 now in this checkout)."""
        self.assertEqual(ev.GSD_CORE_PREFIXES, ("1.16.", "1.17."))
        self.assertTrue(callable(ev.gsd_tools.gsd_core_version))


class TestCli(unittest.TestCase):
    def test_digest_cli_prints_only_the_digest(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as sink:
            code = ev.main(["digest", "--skill-dir", str(ev.SKILL_DIR)])
        self.assertEqual(code, 0)
        self.assertRegex(sink.getvalue().strip(), r"^[0-9a-f]{16}$")

    def test_snapshot_cli_requires_a_mode(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ev.main(["snapshot"]), 2)

    def test_matrix_cli_host_refusal_is_exit_2(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()) as sink:
            code = ev.main(["matrix", "--host", "codex"])
        self.assertEqual(code, 2)
        self.assertIn("matrix oracle supports claude only", sink.getvalue())

    def test_render_matrix_is_mismatches_plus_control_verdict(self) -> None:
        result = {
            "rows": [{"combo": "mvp/adaptive", "path": "P1",
                      "mismatches": [["gsd-planner", "opus", "", ""]]}],
            "controls": {
                "control_1": {"ok": False, "expected_failures": 3, "observed": 0},
                "control_2": {"ok": True},
            },
        }
        lines = ev._render_matrix(result).splitlines()
        self.assertEqual(lines[0], "mvp/adaptive P1 gsd-planner expected=opus got= tier=")
        self.assertIn("control 1 vacuous: expected 3 observed 0", lines[-1])
        self.assertTrue(ev._matrix_failed(result))

    def test_clean_result_is_not_failed(self) -> None:
        """Non-vacuity for the verdict above."""
        result = {
            "rows": [{"combo": "mvp/adaptive", "path": "P1", "mismatches": []}],
            "controls": {"control_1": {"ok": True}, "control_2": {"ok": True}},
        }
        self.assertFalse(ev._matrix_failed(result))


if __name__ == "__main__":
    unittest.main()
