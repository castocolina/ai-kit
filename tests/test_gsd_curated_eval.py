"""Unit tier: the Phase 19 eval helper's oracle, snapshot, digest and matrix env, hermetically.

No node, no CLI, no real home: every subprocess seam is an injected `run_fn`, every path is a
`tempfile` directory, and each negative case is paired with the positive case proving the check
is not vacuous.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from types import SimpleNamespace
from unittest import mock

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
            return _completed(
                {
                    "profiles": {
                        "gsd-planner": {"adaptive": "opus"},
                        "gsd-extra": {"adaptive": "opus"},
                    },
                    "phase": {"gsd-planner": "planning"},
                }
            )

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
        rows = ev._mismatches(
            agents,
            plan,
            tables,
            {
                "gsd-executor": {"model": "haiku", "tier": "haiku"},
                "gsd-planner": {"model": "sonnet", "tier": "sonnet"},
            },
        )
        self.assertEqual(
            rows,
            [
                ["gsd-executor", "sonnet", "haiku", "haiku"],
                ["gsd-planner", "opus", "sonnet", "sonnet"],
            ],
        )
        clean = ev._mismatches(
            agents,
            plan,
            tables,
            {
                "gsd-executor": {"model": "sonnet", "tier": "sonnet"},
                "gsd-planner": {"model": "opus", "tier": "opus"},
            },
        )
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
            code = ev._cmd_snapshot(Namespace(out=out, check=None, home=pathlib.Path(self.home)))
            self.assertEqual(code, 0)
            self.assertNotIn(self.home, sink.getvalue())
            text = pathlib.Path(out).read_text(encoding="utf-8")
            self.assertNotIn(self.scratch, text)
            code = ev._cmd_snapshot(Namespace(out=None, check=out, home=pathlib.Path(self.home)))
        self.assertEqual(code, 0)
        self.assertIn("snapshot ok", sink.getvalue())

    def test_snapshot_check_reports_a_strict_change_and_exits_1(self) -> None:
        out = os.path.join(self.scratch, "snap.json")
        with contextlib.redirect_stdout(io.StringIO()):
            ev._cmd_snapshot(Namespace(out=out, check=None, home=pathlib.Path(self.home)))
        self.write(os.path.join(self.home, ".gsd", "defaults.json"), '{"z": 9}\n')
        with contextlib.redirect_stdout(io.StringIO()) as sink:
            code = ev._cmd_snapshot(Namespace(out=None, check=out, home=pathlib.Path(self.home)))
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
        self.assertEqual(ev.check_digests([path], digest), [f"{path}: {'0' * 16} != {digest}"])

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
            "resolve_env": {
                "GSD_HOME": "/scratch/gsd_home",
                "XDG_CACHE_HOME": "/scratch/xdg",
                "RUNTIME_DIR": "/repo",
                "PATH": "/usr/bin",
            },
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
            ev.run_matrix(
                "node", "/tools/gsd-tools.cjs", "/home", "claude", _ctx(bundle_fn=bundle_fn)
            )
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

        bundle = ev._bundle_for(
            _ctx(bundle_fn=bundle_fn), ("rigorous", "quality"), "P2", ev.POISON_DEFAULTS
        )
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
        ev._write_control_plan(
            bundle,
            _plan(
                [
                    _unset("resolve_model_ids"),
                    _set("models.planning", "mars"),
                ]
            ),
        )
        self.assertTrue(bundle["plan_path"].endswith("plan-control1.json"))
        written = json.loads(pathlib.Path(bundle["plan_path"]).read_text(encoding="utf-8"))
        self.assertEqual([e["key"] for e in written["entries"]], ["models.planning"])
        self.assertEqual(written["profile"], "adaptive")

    def test_write_control_plan_requires_the_entry(self) -> None:
        """Non-vacuity: a plan without the unset cannot drive Control 1."""
        scratch = tempfile.mkdtemp(prefix="xai-control-")
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        with self.assertRaises(ev._refusal) as caught:
            ev._write_control_plan(
                {"plan_path": os.path.join(scratch, "plan.json")},
                _plan([_set("models.planning", "mars")]),
            )
        self.assertIn("no resolve_model_ids entry", str(caught.exception))

    def test_resolve_model_parses_stdout_only(self) -> None:
        calls: list[list[str]] = []

        def run_fn(cmd, **kwargs):
            calls.append(cmd)
            return _completed({"model": "opus", "tier": "opus"})

        got = ev._resolve_model(
            _ctx(run_fn=run_fn), "gsd-planner", "/scratch/project", {"HOME": "/real"}
        )
        self.assertEqual(got["model"], "opus")
        self.assertEqual(got["effort"], "")
        self.assertEqual(
            calls[0],
            [
                "node",
                "/tools/gsd-tools.cjs",
                "resolve-model",
                "gsd-planner",
                "--cwd",
                "/scratch/project",
            ],
        )

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
        self.assertEqual(
            ev.label_path(ev.REPO_ROOT / "tools" / "setup.py"), "<worktree>/tools/setup.py"
        )
        self.assertEqual(ev.label_path(ev.REPO_ROOT), "<worktree>")
        self.assertEqual(ev.label_path(str(pathlib.Path.home())), "<home>")
        # an explicit scratch root reads as `<scratch>` itself; a bare mkdtemp path under the
        # system temp dir reads as a `<scratch>` child - never a machine path
        self.assertEqual(ev.label_path(scratch, scratch), "<scratch>")
        self.assertEqual(
            ev.label_path(os.path.join(scratch, "project"), scratch), "<scratch>/project"
        )
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
            "rows": [
                {
                    "combo": "mvp/adaptive",
                    "path": "P1",
                    "mismatches": [["gsd-planner", "opus", "", ""]],
                }
            ],
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


def _fake_stream(
    *,
    skills=None,
    tools=None,
    skill_tool=False,
    result_error=False,
    no_result=False,
    extra_bash=None,
):
    """Canned stream-json for one turn: init, one text, one Bash tool_use with its id and
    result, optionally a Skill tool_use, then the result event."""
    lines = [
        {
            "type": "system",
            "subtype": "init",
            "model": "sonnet",
            "tools": tools if tools is not None else ["Read", "Bash", "Glob", "Grep"],
            "skills": skills or [],
            "slash_commands": [],
            "mcp_servers": [],
            "plugins": [],
            "memory_paths": [],
            "claude_code_version": "9.9.9",
            "permissionMode": "default",
        },
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tu-1",
                        "name": "Bash",
                        "input": {"command": extra_bash or "echo ok"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tu-1",
                        "is_error": False,
                        "content": [
                            {"type": "text", "text": "line one"},
                            {"type": "text", "text": "line two"},
                        ],
                    }
                ]
            },
        },
    ]
    if skill_tool:
        lines.append(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "id": "tu-2", "name": "Skill", "input": {"skill": "x"}}
                    ]
                },
            }
        )
    if not no_result:
        lines.append({"type": "result", "total_cost_usd": 0.25, "is_error": result_error})
    return lines


class _FakeProc:
    def __init__(self, returncode=0, wait_exc=None):
        self.pid = 4242
        self.returncode = returncode
        self._wait_exc = wait_exc
        self.waits = 0

    def wait(self, timeout=None):
        self.waits += 1
        if self._wait_exc is not None and self.waits == 1:
            raise self._wait_exc
        return self.returncode


class _Spawner:
    """Writes a canned stream to the stdout handle and returns a fake process."""

    def __init__(self, streams, returncodes=None, wait_exc=None):
        self.streams = list(streams)
        self.returncodes = list(returncodes or [])
        self.wait_exc = wait_exc
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), dict(kwargs)))
        stream = self.streams.pop(0) if self.streams else []
        handle = kwargs["stdout"]
        for line in stream:
            handle.write(json.dumps(line) + "\n")
        rc = self.returncodes.pop(0) if self.returncodes else 0
        return _FakeProc(rc, self.wait_exc)


class _Kills:
    def __init__(self):
        self.log = []
        self.raise_for = set()

    def __call__(self, pgid, sig):
        self.log.append((pgid, sig))
        if pgid in self.raise_for:
            raise ProcessLookupError


def _fixture_for(tmp: str, scenario: str = "C") -> dict:
    run = os.path.join(tmp, "run")
    os.makedirs(os.path.join(run, "project"))
    return {
        "scenario": scenario,
        "run_dir": run,
        "project": os.path.join(run, "project"),
        "env": {"XDG_CACHE_HOME": os.path.join(run, "xdg")},
        "digest": "d" * 16,
        "skill_md": "/x/SKILL.md",
        "v1_commit": "7009d22^",
    }


def _scripted(tmp: str) -> str:
    text = os.path.join(tmp, "scenario.md")
    with open(text, "w", encoding="utf-8") as fh:
        fh.write(
            "## Prompt\n\n```\nDo the thing.\n```\n\n## Scripted answers\n\n```\n"
            "answer one\n```\n\n```\nanswer two\n```\n\n## Expected behavior\n"
        )
    return open(text, encoding="utf-8").read()


def _seams(spawner, kills, tmp, ps_text="", **extra):
    return ev.RunSeams(
        claude_bin="/bin/claude",
        popen_fn=spawner,
        kill_fn=kills,
        home=os.path.join(tmp, "home"),
        ps_fn=lambda: ps_text,
        **extra,
    )


class TestRun(unittest.TestCase):
    """The headless runner with injected seams: argv, env, supervision, gating, checks."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmp, True)
        os.makedirs(os.path.join(self._tmp, "home"))
        self.fixture = _fixture_for(self._tmp)
        self.text = _scripted(self._tmp)
        self.kills = _Kills()

    def _run(self, spawner, cell="red-a", ps_text="", scenario_text=None):
        return ev.run_cell(
            self.fixture,
            cell,
            scenario_text or self.text,
            _seams(spawner, self.kills, self._tmp, ps_text),
            model="sonnet",
            effort="medium",
        )

    def test_turn_one_argv_exact(self):
        spawner = _Spawner([_fake_stream(), _fake_stream()])
        self._run(spawner)
        argv = spawner.calls[0][0]
        self.assertEqual(argv[:2], ["/bin/claude", "-p"])
        self.assertEqual(argv[2 : 2 + len(ev.RUN_FLAGS)], list(ev.RUN_FLAGS))
        self.assertIn("--session-id", argv)
        self.assertNotIn("--resume", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "sonnet")
        self.assertEqual(argv[argv.index("--effort") + 1], "medium")
        self.assertTrue(argv[-1].endswith("Do the thing."))

    def test_resume_turns_keep_session_id(self):
        spawner = _Spawner([_fake_stream(), _fake_stream(), _fake_stream()])
        rec = self._run(spawner)
        sessions = [
            c[0][c[0].index("--session-id") + 1]
            if "--session-id" in c[0]
            else c[0][c[0].index("--resume") + 1]
            for c in spawner.calls
        ]
        self.assertEqual(len(set(sessions)), 1)
        self.assertEqual(sessions[0], rec["session_id"])
        self.assertIn("--resume", spawner.calls[1][0])
        self.assertEqual(spawner.calls[2][0][-1], "answer two")
        self.assertEqual(rec["harness_failures"], [])

    def test_init_fields_and_cost_recorded(self):
        stub = os.path.join(self._tmp, "claude-stub")
        with open(stub, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\necho '9.9.9 (fake)'\n")
        os.chmod(stub, 0o755)
        spawner = _Spawner([_fake_stream(), _fake_stream(), _fake_stream()])
        rec = ev.run_cell(
            self.fixture,
            "red-a",
            self.text,
            ev.RunSeams(
                claude_bin=stub,
                popen_fn=spawner,
                kill_fn=self.kills,
                home=os.path.join(self._tmp, "home"),
                ps_fn=lambda: "",
            ),
            model="sonnet",
            effort="medium",
        )
        self.assertEqual(rec["init"]["model"], "sonnet")
        self.assertEqual(rec["init"]["tools"], ["Read", "Bash", "Glob", "Grep"])
        self.assertEqual(rec["turns"][0]["total_cost_usd"], 0.25)
        self.assertEqual(rec["cost_usd_total"], 0.75)
        self.assertEqual(rec["claude_version"], "9.9.9 (fake)")

    def test_skill_tool_use_is_harness_failure(self):
        spawner = _Spawner([_fake_stream(skill_tool=True), _fake_stream()])
        rec = self._run(spawner)
        self.assertIn("Skill tool_use", rec["harness_failures"])

    def test_nonempty_skills_is_harness_failure(self):
        rec = self._run(_Spawner([_fake_stream(skills=["x"]), _fake_stream()]))
        self.assertIn("skills is not empty", rec["harness_failures"])

    def test_projects_key_for_scratch_dir_is_harness_failure(self):
        with open(os.path.join(self._tmp, "home", ".claude.json"), "w", encoding="utf-8") as fh:
            json.dump({"projects": {self.fixture["project"]: {}}}, fh)
        rec = self._run(_Spawner([_fake_stream(), _fake_stream(), _fake_stream()]))
        self.assertTrue(any("projects key" in f for f in rec["harness_failures"]))

    def test_projects_key_for_other_dir_is_not_a_failure(self):
        with open(os.path.join(self._tmp, "home", ".claude.json"), "w", encoding="utf-8") as fh:
            json.dump({"projects": {"/elsewhere": {}}}, fh)
        rec = self._run(_Spawner([_fake_stream(), _fake_stream(), _fake_stream()]))
        self.assertEqual(rec["harness_failures"], [])

    def test_transcript_dir_recorded_and_deleted(self):
        transcript = ev._transcript_dir(self.fixture["project"])
        target = os.path.join(self._tmp, "home", ".claude", "projects", transcript)
        os.makedirs(target)
        rec = self._run(_Spawner([_fake_stream(), _fake_stream(), _fake_stream()]))
        self.assertEqual(rec["transcript_dir"], transcript)
        self.assertFalse(os.path.exists(target))

    def test_transcript_dir_name_sanitized(self):
        self.assertEqual(ev._transcript_dir("/a/b.c/d"), "-a-b-c-d")

    def test_env_has_no_host_signals(self):
        spawner = _Spawner([_fake_stream(), _fake_stream(), _fake_stream()])
        with mock.patch.dict(os.environ, {"CLAUDECODE": "1"}):
            self._run(spawner)
        self.assertNotIn("CLAUDECODE", spawner.calls[0][1]["env"])

    def test_env_drops_plugin_root(self):
        spawner = _Spawner([_fake_stream(), _fake_stream(), _fake_stream()])
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": "/some/plugin"}):
            self._run(spawner)
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", spawner.calls[0][1]["env"])

    def test_popen_starts_new_session(self):
        spawner = _Spawner([_fake_stream(), _fake_stream(), _fake_stream()])
        self._run(spawner)
        self.assertTrue(spawner.calls[0][1]["start_new_session"])
        self.assertEqual(spawner.calls[0][1]["stdin"], ev.subprocess.DEVNULL)

    def test_timeout_signals_group_term_then_kill(self):
        spawner = _Spawner([_fake_stream()], wait_exc=ev.subprocess.TimeoutExpired("c", 1))
        rec = self._run(spawner)
        self.assertEqual(self.kills.log[:2], [(4242, ev.signal.SIGTERM), (4242, ev.signal.SIGKILL)])
        self.assertTrue(rec["turns"][0]["timed_out"])
        self.assertIn("turn 1: timed out", rec["harness_failures"])

    def test_group_killed_after_normal_exit(self):
        self.kills.raise_for.add(4242)
        rec = self._run(_Spawner([_fake_stream(), _fake_stream(), _fake_stream()]))
        self.assertEqual(self.kills.log[0], (4242, ev.signal.SIGKILL))
        self.assertEqual(rec["harness_failures"], [])

    def test_events_pair_results_with_commands(self):
        self._run(_Spawner([_fake_stream(), _fake_stream(), _fake_stream()]))
        evs = ev.events(self.fixture["run_dir"], "red-a")
        bash = next(e for e in evs if e["kind"] == "bash")
        result = next(e for e in evs if e["kind"] == "tool_result")
        self.assertEqual(bash["id"], result["tool_use_id"])
        self.assertFalse(result["is_error"])
        self.assertEqual(result["text"], "line one\nline two")
        self.assertEqual(bash["command"], "echo ok")

    def test_nonzero_exit_stops_turns(self):
        spawner = _Spawner([_fake_stream(), _fake_stream()], returncodes=[1, 0])
        rec = self._run(spawner)
        self.assertEqual(len(spawner.calls), 1)
        self.assertIn("turn 1: exit 1", rec["harness_failures"])

    def test_missing_result_event_is_harness_failure(self):
        rec = self._run(_Spawner([_fake_stream(no_result=True), _fake_stream()]))
        self.assertIn("turn 1: no result event", rec["harness_failures"])

    def test_result_is_error_is_harness_failure(self):
        rec = self._run(_Spawner([_fake_stream(result_error=True), _fake_stream()]))
        self.assertIn("turn 1: result is_error", rec["harness_failures"])

    def test_clean_turns_have_no_gating_entry(self):
        rec = self._run(_Spawner([_fake_stream(), _fake_stream(), _fake_stream()]))
        self.assertEqual(rec["harness_failures"], [])

    def test_detached_descendant_reaped(self):
        run = self.fixture["run_dir"]
        ps = "\n".join(
            [
                f"111 1 111 node {run}/project/x.cjs",
                "222 1 222 unrelated process",
            ]
        )
        rec = self._run(_Spawner([_fake_stream(), _fake_stream(), _fake_stream()]), ps_text=ps)
        self.assertIn((111, ev.signal.SIGKILL), self.kills.log)
        self.assertNotIn((222, ev.signal.SIGKILL), self.kills.log)
        self.assertEqual(rec["reaped"][0][0], 111)
        self.assertIn("<run>", rec["reaped"][0][1])

    def test_reaper_spares_own_pid_parent_and_group(self):
        run = self.fixture["run_dir"]
        parent = os.getppid()
        ps = "\n".join(
            [
                f"{os.getpid()} {parent} {os.getpgrp()} python {run}/self",
                f"{parent} 1 {parent} parent {run}/parent",
                f"555 {os.getpid()} {os.getpgrp()} child in our group {run}/x",
            ]
        )
        rec = self._run(_Spawner([_fake_stream(), _fake_stream(), _fake_stream()]), ps_text=ps)
        signalled = {pgid for pgid, _s in self.kills.log}
        self.assertNotIn(os.getpgrp(), signalled)
        self.assertNotIn(parent, signalled)
        self.assertEqual(rec["reaped"], [])

    def test_reaper_spares_higher_ancestor_in_other_group(self):
        run = self.fixture["run_dir"]
        parent, grand = os.getppid(), 999_001
        ps = "\n".join(
            [
                f"{os.getpid()} {parent} {os.getpgrp()} python {run}/self",
                f"{parent} {grand} {parent} parent",
                f"{grand} 1 {grand} shell with {run}",
                f"777 1 777 detached {run}/d",
            ]
        )
        self._run(_Spawner([_fake_stream(), _fake_stream(), _fake_stream()]), ps_text=ps)
        signalled = {pgid for pgid, _s in self.kills.log}
        self.assertNotIn(grand, signalled)
        self.assertNotIn(grand, {pid for pid, _s in self.kills.log})
        self.assertIn(777, signalled)

    def test_shadowed_entrypoint_is_harness_failure(self):
        home = os.path.join(self._tmp, "home")
        shadow = os.path.join(
            home, ".claude", "skills", "ai-kit-gsd-curated-config", "ai-kit-gsd-curated-config.py"
        )
        fixture = dict(self.fixture, v1_entrypoint="x")
        rec = self._run_red_b(fixture, shadow)
        self.assertTrue(any(f.startswith("entrypoint_shadowed:") for f in rec))

    def test_entrypoint_inside_run_dir_passes(self):
        fixture = dict(self.fixture)
        inside = os.path.join(
            fixture["run_dir"],
            "v1-skill",
            "ai-kit-gsd-curated-config",
            "ai-kit-gsd-curated-config.py",
        )
        rec = self._run_red_b(fixture, inside)
        self.assertFalse(any(f.startswith("entrypoint_shadowed:") for f in rec))

    def _run_red_b(self, fixture, command_path):
        spawner = _Spawner(
            [
                _fake_stream(extra_bash=f"python3 {command_path} --help"),
                _fake_stream(),
                _fake_stream(),
            ]
        )
        self.fixture = fixture
        rec = ev.run_cell(
            self.fixture,
            "red-b",
            self.text,
            _seams(spawner, self.kills, self._tmp),
            model="sonnet",
            effort="medium",
        )
        return rec["harness_failures"]

    def test_preamble_per_cell(self):
        prompts = {}
        for cell in ("red-a", "red-b", "green"):
            spawner = _Spawner([_fake_stream(), _fake_stream(), _fake_stream()])
            self.fixture["v1_skill_md"] = "/run/v1/SKILL.md"
            self.fixture["v1_entrypoint"] = "/run/v1/entry.py"
            self._run(spawner, cell=cell)
            prompts[cell] = spawner.calls[0][0][-1]
        self.assertIn("/run/v1/entry.py", prompts["red-b"])
        self.assertIn("The gsd-core install is at", prompts["red-a"])
        self.assertNotIn("/run/v1/entry.py", prompts["green"])

    def test_scripted_answers_parsed(self):
        self.assertEqual(ev._answers_of(self.text), ["answer one", "answer two"])

    def test_runner_helper_parses_real_eval_b(self):
        text = (ev.SKILL_DIR / "evals" / ev.EVAL_FILES["B"]).read_text(encoding="utf-8")
        self.assertEqual(len(ev._answers_of(text)), 2)


class TestFixture(unittest.TestCase):
    """The pure parts of the fixture builders (no node, no CLI, no real home)."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmp, True)

    def test_router_confirmation_added_to_both_routers(self):
        cat = ev._router_confirmed({k: {} for k in ev.ROUTERS})
        for key in ev.ROUTERS:
            self.assertIn("is_router", cat[key]["heuristic_confirmed"])
        bare = ev._router_confirmed({})
        self.assertIn("router-env/my-coding", bare)

    def test_model_less_installed_rows_dropped(self):
        rts = {
            "clis": {
                "grok": {"installed": True},
                "opencode": {"installed": True, "models": ["a/b"]},
                "pi": {"installed": False},
            }
        }
        out = ev._drop_model_less_rows(rts)["clis"]
        self.assertEqual(out["grok"], {"installed": False})
        self.assertEqual(out["opencode"], {"installed": True, "models": ["a/b"]})
        self.assertEqual(out["pi"], {"installed": False})

    def test_ambient_review_config_cannot_affect_fetch(self):
        from ai_kit_spec import cli as spec_cli  # pylint: disable=import-outside-toplevel
        from ai_kit_spec.cli import CliDeps  # pylint: disable=import-outside-toplevel
        from ai_kit_spec.config_io import ConfigError  # pylint: disable=import-outside-toplevel

        xdg = os.path.join(self._tmp, "xdg-config")
        os.makedirs(os.path.join(xdg, "ai-kit"))
        with open(os.path.join(xdg, "ai-kit", "review-spec.toml"), "w", encoding="utf-8") as fh:
            fh.write("[[[")
        env = {"XDG_CONFIG_HOME": xdg, "HOME": self._tmp, "PATH": os.environ.get("PATH", "")}
        args = argparse.Namespace(cwd=self._tmp, extra_candidate=[])
        deps = CliDeps(env_fn=lambda: env)
        raw = _load_raw_fixture_rows()
        spec_cli._discovered_catalog_candidates(  # pylint: disable=protected-access
            ev._drop_model_less_rows(raw), args, deps
        )
        with self.assertRaises(ConfigError):
            spec_cli._discovered_catalog_candidates(  # pylint: disable=protected-access
                raw, args, deps
            )

    def test_fakebin_covers_every_non_claude_binary(self):
        from ai_kit_spec import detection  # pylint: disable=import-outside-toplevel

        run = os.path.join(self._tmp, "run")
        os.makedirs(run)
        ev._write_fakebin(ev._layout(run), _load_raw_fixture_rows())
        names = set(os.listdir(os.path.join(run, "fakebin")))
        want = {
            b for rid, row in detection.RUNTIMES.items() if rid != "claude" for b in row.binaries
        }
        self.assertEqual(names, want)
        for name in names:
            self.assertTrue(os.access(os.path.join(run, "fakebin", name), os.X_OK))

    def test_fakebin_listings_parse_with_product_parsers(self):
        from ai_kit_spec import detection  # pylint: disable=import-outside-toplevel

        run = os.path.join(self._tmp, "run")
        os.makedirs(run)
        ev._write_fakebin(ev._layout(run), _load_raw_fixture_rows())
        fb = os.path.join(run, "fakebin")
        seeded = _load_raw_fixture_rows()["clis"]
        cursor = detection.detect_cursor_agent_models(os.path.join(fb, "cursor-agent"))
        self.assertEqual(cursor, seeded["cursor"]["models"])
        opencode = detection.detect_opencode_models(os.path.join(fb, "opencode"))
        self.assertEqual(opencode, seeded["opencode"]["models"])
        pi = subprocess.run([os.path.join(fb, "pi"), "--mode"], capture_output=True, check=False)
        self.assertEqual(pi.returncode, 1)
        with open(os.path.join(run, "fakebin.log"), encoding="utf-8") as fh:
            self.assertEqual(len(fh.read().splitlines()), 3)

    def test_v1_detect_through_launcher_never_runs_path_binary(self):
        from ai_kit_gsd_curated_config import (  # pylint: disable=import-outside-toplevel
            model_detect,
            preference_match,
        )

        run = os.path.join(self._tmp, "run")
        os.makedirs(run)
        paths = ev._layout(run)
        ev._write_seed_files(
            paths, confirm_routers=True, catalog=None, runtimes=_load_raw_fixture_rows()
        )
        ev._write_fakebin(paths, _load_raw_fixture_rows())
        launcher = ev._write_launcher(paths)
        # Decoys on PATH: each logs its own call, then emits the seeded listing, so a probe
        # that reaches them is visible as both a call marker and a candidate.
        decoy = os.path.join(self._tmp, "decoy")
        os.makedirs(decoy)
        hits = os.path.join(decoy, "hits")
        seeded = _load_raw_fixture_rows()["clis"]
        listings = {
            "cursor-agent": seeded["cursor"]["models"],
            "opencode": seeded["opencode"]["models"],
        }
        for name, models in listings.items():
            target = os.path.join(decoy, name)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(
                    '#!/bin/sh\necho "$0" >> '
                    + hits
                    + "\n"
                    + "".join(f"echo {m!r}\n" for m in models)
                )
            os.chmod(target, 0o755)
        base = {
            "PATH": decoy + os.pathsep + os.path.dirname(sys.executable),
            "HOME": os.path.join(self._tmp, "home"),
            "TMPDIR": self._tmp,
            "RUNTIME_DIR": str(ev.REPO_ROOT),
        }
        proc = subprocess.run(
            [sys.executable, str(launcher), "detect-execution-candidate"],
            env={**base, "XDG_CACHE_HOME": paths.xdg},
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(os.path.exists(hits), "the launcher ran a PATH decoy")
        pool = model_detect.build_candidate_pool(_load_raw_fixture_rows())
        want = preference_match.best_execution_candidate(pool)
        self.assertEqual(json.loads(proc.stdout)["cli"], want[0] if want else None)
        # Non-vacuity: the bare worktree script, on the same PATH with no seeded cache, does
        # reach the decoys, so the assertion above is not satisfied by an unreached probe.
        bare = subprocess.run(
            [
                sys.executable,
                str(ev.SKILL_DIR / "ai-kit-gsd-curated-config.py"),
                "detect-execution-candidate",
            ],
            env={**base, "XDG_CACHE_HOME": os.path.join(self._tmp, "bare-xdg")},
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(bare.returncode, 0, bare.stderr)
        self.assertTrue(os.path.exists(hits), "the bare run should reach a PATH decoy")

    def test_assert_no_probe(self):
        run = os.path.join(self._tmp, "run")
        paths = ev._layout(run)
        ev._write_seed_files(paths, confirm_routers=True, catalog=None, runtimes=None)
        ev._make_claude_row_current(paths)
        env = {"XDG_CACHE_HOME": paths.xdg, "HOME": self._tmp}
        ev.assert_no_probe(env)
        os.remove(str(paths.catalog) + ev.SIDECAR_SUFFIX)
        with self.assertRaises(SystemExit) as caught:
            ev.assert_no_probe(env)
        self.assertIn("inventory would probe", str(caught.exception))

    def test_pin_entrypoint_changes_only_resolver_block(self):
        text = (
            "intro\n\n## Resolve the entrypoint\n\nold block\n```\nold\n```\n\n"
            "## Run the curated flow\n\nkeep me\n"
        )
        out = ev._pin_entrypoint(text, "/run/entry.py")
        self.assertTrue(out.startswith("intro\n\n## Resolve the entrypoint\n"))
        self.assertIn("The entrypoint is /run/entry.py", out)
        self.assertNotIn("old block", out)
        self.assertTrue(out.endswith("## Run the curated flow\n\nkeep me\n"))
        with self.assertRaises(ValueError):
            ev._pin_entrypoint("no such section\n", "/run/entry.py")

    def test_pin_entrypoint_on_real_v1_text(self):
        v1 = subprocess.run(
            [
                "git",
                "-C",
                str(ev.REPO_ROOT),
                "show",
                "7009d22^:skills/ai-kit-gsd-curated-config/SKILL.md",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        out = ev._pin_entrypoint(v1, "/run/entry.py")
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", out)
        self.assertIn("## Run the curated flow", out)

    def test_e_answer_pairs_turn_feature_off_then_first_candidate(self):
        plan = {
            "entries": [
                {"key": "workflow.cross_ai_command", "status": "needs_choice", "candidates": []},
                {
                    "key": "agent_skills_security.trusted_global_roots",
                    "status": "needs_choice",
                    "candidates": [{"value": ["~/a"]}],
                },
            ]
        }
        pairs = ev._e_answer_pairs(plan)
        self.assertEqual(pairs[0], ("workflow.cross_ai_execution", "false"))
        self.assertEqual(pairs[1], ("agent_skills_security.trusted_global_roots", '["~/a"]'))
        self.assertEqual(len(pairs), 2)

    def test_e_answer_without_turn_off_keeps_needs_choice(self):
        from ai_kit_gsd_curated_config import (
            apply as apply_mod,  # pylint: disable=import-outside-toplevel
        )

        plan = {
            "entries": [
                {"key": "workflow.cross_ai_command", "status": "needs_choice", "candidates": []}
            ]
        }
        self.assertEqual(apply_mod.needs_choice_keys(plan), ["workflow.cross_ai_command"])
        plan["entries"][0]["status"] = "set"
        self.assertEqual(apply_mod.needs_choice_keys(plan), [])

    def test_fixture_env_is_scratch_only(self):
        paths = ev._layout(os.path.join(self._tmp, "run"))
        env = ev._fixture_env(paths)
        self.assertEqual(env["GSD_HOME"], str(paths.gsd_home))
        self.assertEqual(env["GSD_RUNTIME"], "claude")
        self.assertNotIn("HOME", env)

    def test_cache_sha_covers_three_files(self):
        run = os.path.join(self._tmp, "run")
        paths = ev._layout(run)
        ev._write_seed_files(paths, confirm_routers=True, catalog=None, runtimes=None)
        self.assertEqual(
            set(ev._cache_sha(paths)),
            {"runtimes.json", "model-catalog.json", "model-catalog.json" + ev.SIDECAR_SUFFIX},
        )


def _load_raw_fixture_rows() -> dict:
    with open(ev.CACHE_SEED / "runtimes.json", encoding="utf-8") as fh:
        return json.load(fh)


if __name__ == "__main__":
    unittest.main()
