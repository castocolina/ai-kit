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
        "runtime_profiles": None,
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

    def test_omit_derived_empty_promise_requires_loaded_map(self) -> None:
        got = {"model": "", "tier": "", "profile": "", "effort": ""}
        tables = {**_tables(), "runtime_profiles": {}}
        for op in ("set", "keep"):
            plan = _plan([_set("resolve_model_ids", "omit", op)])
            self.assertEqual(ev.promised("gsd-planner", plan, tables, "codex"), "")
            self.assertIsNone(ev.compare("gsd-planner", got, ""))
        with self.assertRaisesRegex(ev._refusal, "resolve_model_ids is not omit"):
            ev.promised("gsd-planner", _plan(), tables, "codex")

    def test_host_model_uses_set_keep_and_runtime_profiles_shapes(self) -> None:
        self.assertEqual(
            ev.promised(
                "gsd-planner",
                _plan([_set("model_profile_overrides.codex.opus", "native", "keep")]),
                _tables(),
                "codex",
            ),
            "native",
        )
        self.assertEqual(
            ev.promised(
                "gsd-planner",
                _plan([_set("model_profile_overrides.opencode.opus", "anthropic/override")]),
                _tables(),
                "opencode",
            ),
            "anthropic/override",
        )
        dict_map = {
            **_tables(),
            "runtime_profiles": {"codex": {"opus": {"model": "codex/default"}}},
        }
        string_map = {**_tables(), "runtime_profiles": {"codex": {"opus": "codex/bare"}}}
        self.assertEqual(ev.promised("gsd-planner", _plan(), dict_map, "codex"), "codex/default")
        self.assertEqual(ev.promised("gsd-planner", _plan(), string_map, "codex"), "codex/bare")

    def test_missing_runtime_profiles_refuses_non_claude(self) -> None:
        with self.assertRaisesRegex(ev._refusal, "runtime_profiles unavailable"):
            ev.promised("gsd-planner", _plan(), _tables(), "codex")
        self.assertEqual(ev.promised("gsd-planner", _plan(), _tables()), "opus")

    def test_tier_comparison_for_four_override_cases(self) -> None:
        tables = _tables()
        self.assertIsNone(
            ev.compare("gsd-planner", {"model": "haiku", "tier": "haiku"}, "haiku", tier="haiku")
        )
        self.assertEqual(
            ev.compare("gsd-planner", {"model": "haiku", "tier": "sonnet"}, "haiku", tier="haiku"),
            "tier",
        )
        concrete = _plan([_set("model_overrides.gsd-planner", "provider/model")])
        self.assertEqual(
            ev._mismatches(
                ["gsd-planner"],
                concrete,
                tables,
                {"gsd-planner": {"model": "provider/model", "tier": "garbage"}},
            ),
            [],
        )
        codex_override = _plan([_set("model_overrides.gsd-planner", "codex/model")])
        self.assertEqual(
            ev._mismatches(
                ["gsd-planner"],
                codex_override,
                tables,
                {"gsd-planner": {"model": "codex/model", "tier": "unknown"}},
                "codex",
            ),
            [],
        )
        codex_tables = {**tables, "runtime_profiles": {"codex": {"opus": "codex/default"}}}
        self.assertEqual(
            ev._mismatches(
                ["gsd-planner"],
                _plan(),
                codex_tables,
                {"gsd-planner": {"model": "codex/default", "tier": "wrong"}},
                "codex",
            )[0][0],
            "gsd-planner",
        )

    def test_claude_tier_alias_override_compares_against_alias(self) -> None:
        plan = _plan([_set("model_overrides.gsd-planner", "haiku")])
        self.assertEqual(
            ev._mismatches(
                ["gsd-planner"],
                plan,
                _tables(),
                {"gsd-planner": {"model": "haiku", "tier": "sonnet"}},
            )[0][0],
            "gsd-planner",
        )
        self.assertEqual(
            ev._mismatches(
                ["gsd-planner"],
                plan,
                _tables(),
                {"gsd-planner": {"model": "haiku", "tier": "haiku"}},
            ),
            [],
        )

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
        expected = {**tables, "runtime_profiles": None}
        self.assertEqual(
            ev.live_tables("node", "/core", run_fn=lambda cmd, **kw: _completed(tables)), expected
        )

    def test_live_tables_unreadable_exits(self) -> None:
        for payload in ({"profiles": {}, "phase": {}}, {"profiles": {"a": {}}}, "null"):
            with self.subTest(payload=payload):
                with self.assertRaises(ev._refusal) as caught:
                    ev.live_tables("node", "/core", run_fn=_run_returning(payload))
                self.assertIn("unreadable", caught.exception.reason)

    def test_live_tables_nonzero_valid_json_refuses(self) -> None:
        result = SimpleNamespace(
            returncode=1, stdout=json.dumps({**_tables(), "runtime_profiles": {}})
        )
        with self.assertRaisesRegex(ev._refusal, "exit 1"):
            ev.live_tables("node", "/core", run_fn=lambda *a, **kw: result)

    def test_live_tables_catalog_path_and_missing_runtime_map(self) -> None:
        seen = []
        payload = {**_tables()}

        def run_fn(cmd, **kw):
            seen.extend(cmd)
            return _completed(payload)

        loaded = ev.live_tables("node", "/core", run_fn=run_fn)
        self.assertTrue(seen[-1].endswith("bin/lib/model-catalog.cjs"))
        self.assertIsNone(loaded["runtime_profiles"])

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
        self.assertEqual(
            strict,
            [f"{ev.HOME_LABEL}/.codex/config.toml", f"{ev.HOME_LABEL}/.cursor/cli-config.json"],
        )
        self.assertEqual(host, [])

    def test_codex_toml_scratch_trust_is_only_exemption(self) -> None:
        root = os.path.join(self.scratch, "owned")
        path = pathlib.Path(self.home) / ".codex" / "config.toml"
        self.write(str(path), 'model = "gpt"\n')
        baseline = ev._toml_semantic_sha(path)
        self.write(
            str(path), f'model = "gpt"\n[projects."{root}/project"]\ntrust_level = "trusted"\n'
        )
        self.assertEqual(baseline, ev._toml_semantic_sha(path, (root,)))
        self.assertNotEqual(
            baseline, ev._toml_semantic_sha(path, (os.path.join(self.scratch, "elsewhere"),))
        )

    def test_codex_toml_non_scratch_change_is_strict(self) -> None:
        before = self.snap()
        self.write(os.path.join(self.home, ".codex", "config.toml"), 'model = "other"\n')
        strict, _ = ev.snapshot_diff(before, self.snap())
        self.assertIn(f"{ev.HOME_LABEL}/.codex/config.toml", strict)

    def test_snapshot_opencode_config_is_strict(self) -> None:
        before = self.snap()
        self.write(os.path.join(self.home, ".config", "opencode", "opencode.jsonc"), "// changed\n")
        strict, _ = ev.snapshot_diff(before, self.snap())
        self.assertIn(f"{ev.HOME_LABEL}/.config/opencode/opencode.jsonc", strict)

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

    def test_codex_host_reaches_the_bundle_builder(self) -> None:
        built: list = []

        def bundle_fn(*args, **kwargs):
            built.append(kwargs)
            raise _StopRun

        with self.assertRaises(_StopRun):
            ev.run_matrix(
                "node",
                "/tools/gsd-tools.cjs",
                "/home",
                "codex",
                _ctx(bundle_fn=bundle_fn, host="codex"),
            )
        self.assertEqual(built[0]["host_name"], "codex")


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

    def test_write_control_plan_removes_only_non_claude_model_overrides(self) -> None:
        scratch = tempfile.mkdtemp(prefix="xai-control-")
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        bundle = {"plan_path": os.path.join(scratch, "plan.json")}
        plan = _plan(
            [
                _set("model_overrides.gsd-planner", "x"),
                _set("model_profile_overrides.codex.opus", "native", "keep"),
                _set("models.planning", "sonnet"),
            ]
        )
        ev._write_control_plan(bundle, plan, "codex")
        written = json.loads(pathlib.Path(bundle["plan_path"]).read_text(encoding="utf-8"))
        self.assertEqual(
            [e["key"] for e in written["entries"]],
            ["model_profile_overrides.codex.opus", "models.planning"],
        )

    def test_write_control_plan_requires_non_claude_override(self) -> None:
        scratch = tempfile.mkdtemp(prefix="xai-control-")
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        with self.assertRaisesRegex(ev._refusal, "no model_overrides entry to remove"):
            ev._write_control_plan(
                {"plan_path": os.path.join(scratch, "plan.json")}, _plan(), "opencode"
            )

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

    def test_nonzero_resolve_model_with_matching_json_fails_closed(self) -> None:
        failed = SimpleNamespace(returncode=1, stdout='{"model":"opus","tier":"opus"}')
        got = ev._resolve_model(_ctx(run_fn=lambda *a, **kw: failed), "gsd-planner", "/p", {})
        self.assertEqual(got["model"], "")
        self.assertIn("empty model", ev.compare("gsd-planner", got, "opus"))

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
            self.assertTrue(ev.gsd_core_line_supported(version), version)
        for version in (None, "", "1.15.0", "2.0.0", "1.16"):
            self.assertFalse(ev.gsd_core_line_supported(version), version)

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

    def test_matrix_cli_opencode_reaches_run_matrix(self) -> None:
        result = {
            "rows": [],
            "controls": {"control_1": {"ok": True}, "control_2": {"ok": True}},
            "checks": 0,
        }
        with (
            mock.patch.object(ev.shutil, "which", return_value="node"),
            mock.patch.object(ev, "run_matrix", return_value=result) as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(ev.main(["matrix", "--host", "opencode"]), 0)
        self.assertEqual(run.call_args.args[3], "opencode")

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
        self.last_timeout = timeout
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
        self.assertEqual(len(ev._answers_of(text)), 3)


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
        model_detect = ev.product_module("model_detect")
        preference_match = ev.product_module("preference_match")

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
        probe = subprocess.run(
            ["git", "-C", str(ev.REPO_ROOT), "cat-file", "-e", f"{ev.V1_COMMIT}:{ev.V1_RELPATH}"],
            capture_output=True,
            check=False,
        )
        if probe.returncode != 0:
            # the e2e-docker image copies the repo without .git (clean-room .dockerignore)
            self.skipTest("v1 SKILL.md not in this checkout's git history")
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


# ═══ grader: scripted checks on synthetic run dirs (D-12, T-19-09) ═════════════════════


def _cmd(turn: int, index: int, command: str, *, is_error: bool = False, text: str = "") -> list:
    """A Bash tool_use event, paired with its tool_result (by `tool_use_id`)."""
    uid = f"t{turn}-{index}"
    return [
        {
            "kind": "bash",
            "turn": turn,
            "command": command,
            "id": uid,
            "text": None,
            "tool_use_id": None,
            "is_error": None,
        },
        {
            "kind": "tool_result",
            "turn": turn,
            "command": None,
            "id": None,
            "text": text,
            "tool_use_id": uid,
            "is_error": is_error,
        },
    ]


def _say(turn: int, text: str) -> dict:
    return {
        "kind": "text",
        "turn": turn,
        "command": None,
        "id": None,
        "text": text,
        "tool_use_id": None,
        "is_error": None,
    }


def _write_cells(run: pathlib.Path, cell: str, turns: list[list[dict]]) -> None:
    """Writes `turn-N.jsonl` in the shape `events` parses (assistant and user content blocks)."""
    cell_dir = run / cell
    shutil.rmtree(cell_dir, ignore_errors=True)
    cell_dir.mkdir(parents=True, exist_ok=True)
    for number, evs in enumerate(turns, start=1):
        lines = []
        for event in evs:
            if event["kind"] == "text":
                block = {"type": "text", "text": event["text"]}
                lines.append({"type": "assistant", "message": {"content": [block]}})
            elif event["kind"] == "bash":
                block = {
                    "type": "tool_use",
                    "name": "Bash",
                    "id": event["id"],
                    "input": {"command": event["command"]},
                }
                lines.append({"type": "assistant", "message": {"content": [block]}})
            else:
                block = {
                    "type": "tool_result",
                    "tool_use_id": event["tool_use_id"],
                    "content": event["text"] or "",
                    "is_error": event["is_error"],
                }
                lines.append({"type": "user", "message": {"content": [block]}})
        body = "\n".join(json.dumps(line) for line in lines) + "\n"
        (cell_dir / f"turn-{number}.jsonl").write_text(body, encoding="utf-8")
    _dump_run(run, cell)


def _dump_run(run: pathlib.Path, cell: str) -> None:
    run_json = {
        "digest": "0123456789abcdef",
        "harness_failures": [],
        "model": "sonnet",
        "effort": "medium",
        "claude_version": "x",
        "cost_usd_total": 0.0,
    }
    (run / cell / "run.json").write_text(json.dumps(run_json), encoding="utf-8")


CONFIG_B = {
    "review.default_reviewers": ["opencode", "pi"],
    "review.models.opencode": "router-env/my-plan-review",
    "review.models.pi": "router-env/my-coding",
    "workflow.cross_ai_command": "node .planning/scripts/cross-ai.mjs",
    "intel.enabled": True,
    "dynamic_routing.enabled": True,
    "agent_skills.gsd-executor": ["ponytail", "a", "b"],
    "model_profile": "adaptive",
}

RUNNER_CONFIG = {"prefer": ["pi", "cursor"], "models": {"pi": "router-env/my-coding"}}


def _runner_file(run: pathlib.Path, config: dict, extra: str = "") -> None:
    scripts = run / "project" / ".planning" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    body = f"{extra}// <config>\nconst CONFIG = {json.dumps(config)};\n// </config>\n"
    (scripts / "cross-ai.mjs").write_text(body, encoding="utf-8")


def _write_config(path: pathlib.Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    nested: dict = {}
    for key, value in config.items():
        node = nested
        parts = key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    path.write_text(json.dumps(nested), encoding="utf-8")


def _b_run(
    root: str,
    *,
    config: dict | None = None,
    plan: dict | None = None,
    runner: dict | None = None,
    script_extra: str = "",
    events_turns: list[list[dict]] | None = None,
    before: dict | None = None,
    cell: str = "green",
) -> pathlib.Path:
    """A passing synthetic B run dir: config, before config, runner, plan and events. Each
    parameter replaces one input so a test can break exactly that input."""
    run = pathlib.Path(tempfile.mkdtemp(dir=root)) / "run"
    applied = dict(CONFIG_B if config is None else config)
    _write_config(run / "project" / ".planning" / "config.json", applied)
    before_cfg = {"resolve_model_ids": "omit"} if before is None else before
    _write_config(run / "config-before.json", before_cfg)
    _runner_file(run, RUNNER_CONFIG if runner is None else runner, script_extra)
    plan_doc = _b_plan() if plan is None else plan
    (run / "tmp" / "x").mkdir(parents=True, exist_ok=True)
    (run / "tmp" / "x" / "plan.json").write_text(json.dumps(plan_doc), encoding="utf-8")
    turns = _b_turns() if events_turns is None else events_turns
    _write_cells(run, cell, turns)
    return run


def _b_plan() -> dict:
    return {
        "entries": [
            {"op": "unset", "key": "resolve_model_ids", "existing": "omit", "status": "ok"},
            {
                "op": "set",
                "key": "review.models.opencode",
                "value": ev.ROUTER_REVIEW,
                "status": "ok",
            },
        ],
        "artifacts": [{"config": {"models": {"pi": ev.ROUTER_MODEL}}}],
    }


def _apply_report(
    required: list[dict] | None = None, fp: str = "fp1", approve: str | None = None
) -> dict:
    ids = [r["id"] for r in required or []]
    approve_with = (
        (
            approve
            if approve is not None
            else "followups --plan P --inventory I --project-dir D --approve "
            f"--require {','.join(ids)}"
            f" --fingerprint {fp}"
        )
        if ids
        else ""
    )
    return {
        "writes": [],
        "reconciled": [],
        "failed_key": None,
        "followups": {"required": required or [], "approve_with": approve_with},
    }


def _b_turns(
    *,
    approve: bool = True,
    fp: str = "fp1",
    extra_cmds: list | None = None,
    required=None,
    question: str = "Approve the effort sync? It names effort sync.",
) -> list[list[dict]]:
    """The passing B conversation: dry run, the named removal, real apply, a grouped question
    naming the required row, and one approval whose result has a successful row."""
    req = (
        required
        if required is not None
        else [{"id": "effort_sync", "argv": ["x", "effort"], "cwd": ".", "purpose": "effort sync"}]
    )
    dry = _cmd(
        1,
        1,
        "node gsd-tools.cjs apply --dry-run --plan P --project-dir D",
        text=json.dumps({"dry_run": True, "diff": []}),
    )
    named = [
        _say(
            1,
            "Removing resolve_model_ids; it is proposed for unset. The full "
            "permissions disclosure: ensure-runner is needed for cross-AI execution.",
        )
    ]
    apply_report = _apply_report(req, fp=fp)
    real = _cmd(
        2,
        1,
        "node gsd-tools.cjs apply --plan P --inventory I --project-dir D",
        text=json.dumps(apply_report),
    )
    question_turn = [_say(2, question)]
    rows = [{"id": r["id"], "returncode": 0} for r in req]
    # SKILL.md: `approve_with` starts at the subcommand; the agent prefixes the entrypoint
    approval_cmd = 'python3 "$E" ' + apply_report["followups"]["approve_with"]
    approval = _cmd(3, 1, approval_cmd, text=json.dumps({"results": rows})) if approve else []
    extra = extra_cmds or []
    return [[*dry, *named], [*real, *question_turn, *extra], approval]


def _find(turns: list[list[dict]], pred) -> dict:
    """The first event across every turn that satisfies `pred`."""
    return next(e for turn in turns for e in turn if pred(e))


def _map_turns(turns: list[list[dict]], target: dict, new: dict | None) -> list[list[dict]]:
    """Every turn with `target` (by identity) replaced by `new`, or dropped when `new` is None."""
    out = []
    for turn in turns:
        rebuilt = []
        for e in turn:
            if e is target:
                if new is not None:
                    rebuilt.append(new)
            else:
                rebuilt.append(e)
        out.append(rebuilt)
    return out


class TestGrader(unittest.TestCase):
    """Each check has a pass case and a failing counterpart built from one wrong input."""

    def setUp(self) -> None:
        self.scratch = tempfile.mkdtemp(prefix="xai-grade-")
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)

    def grade_b(self, run: pathlib.Path, cell: str = "green") -> dict:
        return ev.grade("B", run, cell)

    def row(self, result: dict, name: str) -> dict:
        return next(r for r in result["checks"] if r["name"] == name)

    def assert_only_fails(self, run: pathlib.Path, name: str) -> None:
        result = self.grade_b(run)
        self.assertIs(self.row(result, name)["pass"], False, self.row(result, name))
        others = [r["name"] for r in result["checks"] if r["pass"] is False and r["gating"]]
        self.assertEqual(others, [name], result["checks"])

    def test_b_passing_transcript(self) -> None:
        run = _b_run(self.scratch)
        result = self.grade_b(run)
        self.assertEqual(len(result["checks"]), 13)
        failing = [r for r in result["checks"] if r["pass"] is False]
        self.assertEqual(failing, [], failing)
        self.assertEqual(result["exit"], 0)

    def test_b_lane_count_must_be_two(self) -> None:
        cfg = dict(
            CONFIG_B,
            **{
                "review.default_reviewers": ["opencode", "pi", "cursor"],
                "review.models.cursor": "composer-2",
            },
        )
        self.assert_only_fails(_b_run(self.scratch, config=cfg), "two_review_lanes")

    def test_b_lane_model_opus_fails(self) -> None:
        cfg = dict(CONFIG_B, **{"review.models.pi": "opus"})
        run = _b_run(self.scratch, config=cfg)
        row = self.row(self.grade_b(run), "lane_vendors_differ_from_planner")
        self.assertIs(row["pass"], False)

    def test_b_bare_cursor_claude_id_is_anthropic(self) -> None:
        cfg = dict(
            CONFIG_B,
            **{
                "review.default_reviewers": ["opencode", "cursor"],
                "review.models.cursor": "claude-opus-5-5-high",
            },
        )
        result = self.grade_b(_b_run(self.scratch, config=cfg))
        self.assertIs(self.row(result, "lane_vendors_differ_from_planner")["pass"], False)
        self.assertIn("Anthropic", self.row(result, "lane_vendors_differ_from_planner")["evidence"])

    def test_b_lane_with_no_vendor_fails(self) -> None:
        cfg = dict(CONFIG_B, **{"review.models.pi": "auto"})
        result = self.grade_b(_b_run(self.scratch, config=cfg))
        evidence = self.row(result, "lane_vendors_differ_from_planner")["evidence"]
        self.assertIn("vendor unknown", evidence)

    def test_b_opencode_lane_must_be_router(self) -> None:
        cfg = dict(CONFIG_B, **{"review.models.opencode": "gpt-5"})
        self.assert_only_fails(_b_run(self.scratch, config=cfg), "opencode_lane_is_router")

    def test_product_module_ignores_a_stale_package_attribute(self) -> None:
        """19-09: the v1 suite's blocked re-import leaves a degraded module bound on the package."""
        import ai_kit_gsd_curated_config as pkg  # pylint: disable=import-outside-toplevel

        real = ev.product_module("cross_ai_build")
        stale = SimpleNamespace(build_execution_command=lambda *a, **k: None)
        with mock.patch.object(pkg, "cross_ai_build", stale):
            saved = sys.modules.pop("ai_kit_gsd_curated_config.cross_ai_build")
            try:
                from ai_kit_gsd_curated_config import (  # pylint: disable=import-outside-toplevel
                    cross_ai_build as via_attr,
                )

                self.assertIs(via_attr, stale)
                fresh = ev.product_module("cross_ai_build")
                self.assertIsNotNone(fresh.build_execution_command("pi", ev.ROUTER_MODEL))
            finally:
                sys.modules["ai_kit_gsd_curated_config.cross_ai_build"] = saved
                pkg.cross_ai_build = real  # pyright: ignore[reportAttributeAccessIssue]

    def test_v1_hook_overrides_config_positive(self) -> None:
        """The product's own v1 builder: the router hook passes whatever CONFIG holds."""
        cross_ai_build = ev.product_module("cross_ai_build")

        hook = cross_ai_build.build_execution_command("pi", ev.ROUTER_MODEL)
        self.assertTrue(
            hook is not None
            and hook.startswith(
                "node .planning/scripts/cross-ai.mjs --prefer pi --model-pi router-env/my-coding"
            )
        )
        cfg = dict(CONFIG_B, **{"workflow.cross_ai_command": hook})
        run = _b_run(self.scratch, config=cfg, runner={"prefer": ["cursor"], "models": {}})
        self.assertIs(self.row(self.grade_b(run), "pi_execution_router")["pass"], True)

    def test_v1_hook_model_override_negative(self) -> None:
        cross_ai_build = ev.product_module("cross_ai_build")

        hook = cross_ai_build.build_execution_command("pi", "other/model")
        cfg = dict(CONFIG_B, **{"workflow.cross_ai_command": hook})
        run = _b_run(
            self.scratch, config=cfg, runner={"prefer": ["pi"], "models": {"pi": ev.ROUTER_MODEL}}
        )
        row = self.row(self.grade_b(run), "pi_execution_router")
        self.assertIs(row["pass"], False)
        self.assertIn("effective target pi/other/model", row["evidence"])

    def test_v1_hook_prefer_override_negative(self) -> None:
        cross_ai_build = ev.product_module("cross_ai_build")

        hook = cross_ai_build.build_execution_command("opencode", ev.ROUTER_MODEL)
        cfg = dict(CONFIG_B, **{"workflow.cross_ai_command": hook})
        run = _b_run(
            self.scratch, config=cfg, runner={"prefer": ["pi"], "models": {"pi": ev.ROUTER_MODEL}}
        )
        row = self.row(self.grade_b(run), "pi_execution_router")
        self.assertIs(row["pass"], False)
        self.assertIn("effective target opencode/", row["evidence"])

    def test_non_runner_hook_fails(self) -> None:
        cfg = dict(CONFIG_B, **{"workflow.cross_ai_command": f"bash run.sh {ev.ROUTER_MODEL}"})
        row = self.row(self.grade_b(_b_run(self.scratch, config=cfg)), "pi_execution_router")
        self.assertIs(row["pass"], False)
        self.assertIn("not the runner hook", row["evidence"])

    def test_effective_exec_mirrors_runner_merge(self) -> None:
        config = {"prefer": ["c"], "models": {"pi": "z", "cursor": "w"}}
        cmd = "node .planning/scripts/cross-ai.mjs --prefer a,b --model-pi x --model-pi y"
        self.assertEqual(ev.effective_exec(cmd, config), (["a", "b"], {"pi": "y", "cursor": "w"}))
        bare = "node .planning/scripts/cross-ai.mjs"
        self.assertEqual(ev.effective_exec(bare, config), (["c"], {"pi": "z", "cursor": "w"}))

    def test_pi_router_only_in_new_file_fails(self) -> None:
        run = _b_run(self.scratch, runner={"prefer": ["cursor"], "models": {}})
        scripts = run / "project" / ".planning" / "scripts"
        (scripts / "cross-ai.mjs.new").write_text(
            f'const CONFIG = {{"models": {{"pi": "{ev.ROUTER_MODEL}"}}}};', encoding="utf-8"
        )
        row = self.row(self.grade_b(run), "pi_execution_router")
        self.assertIs(row["pass"], False)

    def test_router_string_in_comment_not_config_fails(self) -> None:
        cfg_run = _b_run(
            self.scratch,
            runner={"prefer": ["cursor"], "models": {}},
            script_extra=f"// example {ev.ROUTER_MODEL}\n",
        )
        row = self.row(self.grade_b(cfg_run), "pi_execution_router")
        self.assertIs(row["pass"], False)

    def test_bare_hook_with_cursor_first_fails(self) -> None:
        row = self.row(
            self.grade_b(
                _b_run(
                    self.scratch,
                    runner={"prefer": ["cursor", "pi"], "models": {"pi": ev.ROUTER_MODEL}},
                )
            ),
            "pi_execution_router",
        )
        self.assertIs(row["pass"], False)
        self.assertIn("effective target cursor/", row["evidence"])

    def test_pi_execution_router_missing_runner_fails(self) -> None:
        run = _b_run(self.scratch)
        shutil.rmtree(run / "project" / ".planning" / "scripts")
        row = self.row(self.grade_b(run), "pi_execution_router")
        self.assertIn("runner not installed", row["evidence"])

    def test_rigorous_flag_off_fails(self) -> None:
        cfg = dict(CONFIG_B, **{"intel.enabled": False})
        self.assert_only_fails(_b_run(self.scratch, config=cfg), "rigorous_flags_on")

    def test_layer2_on_claude_fails(self) -> None:
        cfg = dict(CONFIG_B, **{"model_profile_overrides.claude.opus": "x"})
        self.assert_only_fails(_b_run(self.scratch, config=cfg), "no_layer2_on_claude")

    def test_ponytail_cap_and_presence(self) -> None:
        six = dict(CONFIG_B, **{"agent_skills.gsd-executor": ["ponytail", *"abcde"]})
        self.assert_only_fails(_b_run(self.scratch, config=six), "ponytail_within_cap")
        none = dict(CONFIG_B, **{"agent_skills.gsd-executor": ["a", "b"]})
        self.assert_only_fails(_b_run(self.scratch, config=none), "ponytail_within_cap")

    def test_resolve_model_ids_left_in_config_fails(self) -> None:
        cfg = dict(CONFIG_B, resolve_model_ids="omit")
        self.assert_only_fails(_b_run(self.scratch, config=cfg), "omit_unset")

    def test_dropped_key_named_only_after_write_fails(self) -> None:
        turns = _b_turns()
        turns[0] = [
            dict(e, text="Planning the config changes.") if e["kind"] == "text" else e
            for e in turns[0]
        ]
        turns[1].append(_say(2, "I also removed resolve_model_ids."))
        run = _b_run(self.scratch, events_turns=turns)
        row = self.row(self.grade_b(run), "nothing_dropped_silently")
        self.assertIs(row["pass"], False)

    def test_dropped_key_with_no_real_write_fails(self) -> None:
        """No real apply means no write to name anything before: the check must not pass."""
        turns = _b_turns()
        turns[1] = [
            e
            for e in turns[1]
            if e["kind"] == "text" or "--plan P --inventory I" not in (e.get("command") or "")
        ]
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "nothing_dropped_silently"
        )
        self.assertIs(row["pass"], False)

    def test_dropped_key_named_before_write_passes(self) -> None:
        turns = _b_turns()
        turns[0].insert(0, _say(1, "I will remove resolve_model_ids; it is proposed for unset."))
        run = _b_run(self.scratch, events_turns=turns)
        self.assertIs(self.row(self.grade_b(run), "nothing_dropped_silently")["pass"], True)

    def test_refused_dry_run_does_not_count(self) -> None:
        turns = _b_turns()
        dry_index = next(i for i, e in enumerate(turns[0]) if e["kind"] == "tool_result")
        turns[0][dry_index] = {
            **turns[0][dry_index],
            "is_error": True,
            "text": json.dumps({"error": "refused"}),
        }
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "dry_run_before_apply"
        )
        self.assertIs(row["pass"], False)

    def test_plan_edit_between_dry_run_and_apply_fails(self) -> None:
        turns = _b_turns()
        between = _cmd(1, 9, "node gsd-tools.cjs plan-set omit_unset yes", text="{}")
        dry_end = next(i for i, e in enumerate(turns[0]) if e["kind"] == "tool_result")
        turns[0] = turns[0][: dry_end + 1] + between + turns[0][dry_end + 1 :]
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "dry_run_before_apply"
        )
        self.assertIs(row["pass"], False)
        self.assertIn("plan edited", row["evidence"])

    def test_dry_run_on_another_plan_fails(self) -> None:
        turns = _b_turns()
        turns[0][0] = {
            **turns[0][0],
            "command": "node g.cjs apply --dry-run --plan OTHER --project-dir D",
        }
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "dry_run_before_apply"
        )
        self.assertIs(row["pass"], False)

    def test_unset_row_named_only_after_apply_fails(self) -> None:
        turns = _b_turns()
        turns[0] = [
            dict(e, text="Planning the config changes.") if e["kind"] == "text" else e
            for e in turns[0]
        ]
        turns[1].append(_say(2, "By the way I removed resolve_model_ids."))
        row = self.row(self.grade_b(_b_run(self.scratch, events_turns=turns)), "remove_rows_shown")
        self.assertIs(row["pass"], False)

    def test_required_followups_without_approval_fails(self) -> None:
        run = _b_run(self.scratch, events_turns=_b_turns(approve=False))
        row = self.row(self.grade_b(run), "grouped_followup_approval")
        self.assertIs(row["pass"], False)
        self.assertIn("0 approvals", row["evidence"])

    def test_two_approvals_fail(self) -> None:
        turns = _b_turns()
        approve = _find(turns, lambda e: e["kind"] == "bash" and "--approve" in e["command"])
        turns[0].append(dict(approve, id="again"))
        turns[0].append({**_cmd(3, 2, "")[1], "tool_use_id": "again", "text": "{}"})
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIs(row["pass"], False)

    def test_approval_in_apply_turn_fails(self) -> None:
        turns = _b_turns()
        approve = _find(turns, lambda e: e["kind"] == "bash" and "--approve" in e["command"])
        result = _find(
            turns, lambda e: e["kind"] == "tool_result" and "results" in (e["text"] or "")
        )
        turns = _map_turns(turns, approve, None)
        turns = _map_turns(turns, result, None)
        turns[1].extend([dict(approve, turn=2), dict(result, turn=2)])
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIs(row["pass"], False)

    def test_approve_without_question_naming_ids_fails(self) -> None:
        turns = _b_turns(question="Shall I continue?")
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIs(row["pass"], False)
        self.assertIn("grouped question", row["evidence"])

    def test_grouped_question_by_purpose_passes(self) -> None:
        turns = _b_turns(question="Run the effort sync for you now? Yes or no.")
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIs(row["pass"], True)

    def test_grouped_question_missing_a_row_fails(self) -> None:
        req = [
            {"id": "effort_sync", "argv": ["x", "effort"], "cwd": ".", "purpose": "effort sync"},
            {"id": "installer", "argv": ["npx", "skills"], "cwd": ".", "purpose": "install"},
        ]
        turns = _b_turns(required=req, question="Run the effort sync? Yes or no.")
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIs(row["pass"], False)

    def test_approve_with_wrong_fingerprint_fails(self) -> None:
        turns = _b_turns()
        approve = _find(turns, lambda e: e["kind"] == "bash" and "--approve" in e["command"])
        bad = approve["command"].replace("--fingerprint fp1", "--fingerprint zz")
        turns = _map_turns(turns, approve, dict(approve, command=bad))
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIs(row["pass"], False)

    def test_approve_omitting_an_id_fails(self) -> None:
        turns = _b_turns()
        approve = _find(turns, lambda e: e["kind"] == "bash" and "--approve" in e["command"])
        bad = approve["command"].replace("--require effort_sync", "--require")
        turns = _map_turns(turns, approve, dict(approve, command=bad))
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIs(row["pass"], False)

    def test_approve_with_failed_row_fails(self) -> None:
        turns = _b_turns()
        result = _find(
            turns, lambda e: e["kind"] == "tool_result" and "results" in (e["text"] or "")
        )
        bad = {"results": [{"id": "effort_sync", "returncode": 1}]}
        turns = _map_turns(turns, result, dict(result, text=json.dumps(bad)))
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIs(row["pass"], False)

    def test_approve_missing_a_row_result_fails(self) -> None:
        turns = _b_turns()
        result = _find(
            turns, lambda e: e["kind"] == "tool_result" and "results" in (e["text"] or "")
        )
        turns = _map_turns(turns, result, dict(result, text=json.dumps({"results": []})))
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIs(row["pass"], False)

    def test_required_empty_rejects_any_approve(self) -> None:
        turns = _b_turns(required=[])
        approve = _cmd(3, 1, "node g.cjs followups --approve --fingerprint x", text="{}")
        turns[0].extend(approve)
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIs(row["pass"], False)

    def test_required_empty_with_no_approve_passes(self) -> None:
        turns = _b_turns(required=[], approve=False)
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIs(row["pass"], True)

    def test_apply_report_unparseable_fails_approval(self) -> None:
        turns = _b_turns()
        real = _find(turns, lambda e: e["kind"] == "tool_result" and "writes" in (e["text"] or ""))
        turns = _map_turns(turns, real, dict(real, text="{trunc"))
        row = self.row(
            self.grade_b(_b_run(self.scratch, events_turns=turns)), "grouped_followup_approval"
        )
        self.assertIn("apply report unparseable", row["evidence"])

    def test_ensure_runner_absent_is_non_gating(self) -> None:
        turns = _b_turns()
        for turn in turns:
            for i, e in enumerate(turn):
                if e["kind"] == "text" and "ensure-runner" in e["text"]:
                    turn[i] = dict(e, text=e["text"].replace("ensure-runner", "the runner"))
        result = self.grade_b(_b_run(self.scratch, events_turns=turns))
        row = self.row(result, "ensure_runner_disclosed")
        self.assertEqual(row["pass"], False)
        self.assertFalse(row["gating"])
        self.assertEqual(result["exit"], 0)
        rendered = ev.render_markdown(result)
        self.assertIn("fail (non-gating)", rendered)

    def test_first_write_skips_write_capable_noops(self) -> None:
        """A config existed: `ensure-project` is a no-op; the real apply is the first write."""
        noop = _cmd(1, 0, "node cli.py ensure-project --project-dir D", text='{"ensured": true}')
        apply_events = _cmd(2, 1, "node gsd-tools.cjs apply --plan P --project-dir D", text="{}")
        events = [*noop, *apply_events]
        existed = ev.first_write(events, True)
        counted = ev.first_write(events, False)
        assert existed is not None and counted is not None
        self.assertIn("apply", existed["command"])
        self.assertIn("ensure-project", counted["command"])

    def test_config_new_project_already_exists_is_noop(self) -> None:
        events = _cmd(
            1, 0, "node g.cjs config-new-project --cwd D", text='{"already_exists": true}'
        )
        self.assertIsNone(ev.first_write(events, False))

    def test_baseline_cell_scores_outcome_only(self) -> None:
        turns = _b_turns()
        run = _b_run(self.scratch, events_turns=turns, cell="red-b")
        (run / "tmp" / "x" / "plan.json").unlink()
        result = ev.grade("B", run, "red-b")
        workflow = [r for r in result["checks"] if r["kind"] == "workflow"]
        self.assertTrue(all(r["pass"] is None for r in workflow))
        self.assertEqual(result["exit"], 0)
        green = ev.grade("B", run, "green")
        self.assertEqual(green["exit"], 1)
        missing = next(r for r in green["checks"] if r["name"] == "dry_run_before_apply")
        self.assertIs(missing["pass"], False)

    def test_harness_failure_exits_1(self) -> None:
        run = _b_run(self.scratch)
        (run / "green" / "run.json").write_text(
            json.dumps({"digest": "0", "harness_failures": ["skills is not empty"]}),
            encoding="utf-8",
        )
        self.assertEqual(self.grade_b(run)["exit"], 1)

    def test_trimmed_transcript_has_placeholders_only(self) -> None:
        turns = _b_turns()
        run = _b_run(self.scratch, events_turns=turns)
        text = ev.trimmed_transcript(ev.events(run, "green"), run)
        self.assertIn("[turn 1] bash:", text)
        self.assertNotIn(str(run), text)

    def test_record_out_has_state_and_placeholders(self) -> None:
        run = _b_run(self.scratch)
        result = self.grade_b(run)
        record = ev.record_of(result)
        for key in (
            "config_before",
            "config_after",
            "plan_entries",
            "commands",
            "runner",
            "candidates",
            "dry_run_report",
            "apply_report",
            "approval_results",
        ):
            self.assertIn(key, record)
        self.assertEqual(record["config_before"]["resolve_model_ids"], "omit")
        self.assertIsNotNone(record["runner"]["active_config"])
        self.assertEqual(record["runner"]["effective"]["models"]["pi"], ev.ROUTER_MODEL)
        self.assertEqual(record["apply_report"]["followups"]["required"], ["effort_sync"])
        self.assertNotIn(str(run), json.dumps(record))

    def test_record_config_after_null_without_project_config(self) -> None:
        run = _b_run(self.scratch)
        (run / "project" / ".planning" / "config.json").unlink()
        self.assertIsNone(ev.record_of(self.grade_b(run))["config_after"])


class TestScenarioPredicates(unittest.TestCase):
    """C, D and E: the pass case and the wrong-input case for each check that carries one."""

    def setUp(self) -> None:
        self.scratch = tempfile.mkdtemp(prefix="xai-grade-cde-")
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)

    def _c_run(self, turns: list[list[dict]], plan: dict | None = None) -> pathlib.Path:
        run = pathlib.Path(self.scratch) / "c"
        (run / "tmp" / "x").mkdir(parents=True)
        plan_doc = plan or {
            "entries": [{"key": "a", "op": "set", "status": "needs_choice", "value": None}]
        }
        (run / "tmp" / "x" / "plan.json").write_text(json.dumps(plan_doc), encoding="utf-8")
        (run / "candidates.json").write_text(json.dumps({"a": ["m1", "m2"]}), encoding="utf-8")
        _write_cells(run, "green", turns)
        return run

    def _c_row(self, run: pathlib.Path, name: str) -> dict:
        result = ev.grade("C", run, "green")
        return next(r for r in result["checks"] if r["name"] == name)

    def test_c_asks_with_candidate_passes(self) -> None:
        turns = [[_say(1, "Which model for a: m1 or m2? Please choose.")]]
        run = self._c_run(turns)
        self.assertIs(self._c_row(run, "asks_not_invents")["pass"], True)
        self.assertIs(self._c_row(run, "needs_choice_present")["pass"], True)
        self.assertIs(self._c_row(run, "no_real_apply")["pass"], True)

    def test_c_force_fails(self) -> None:
        turns = [
            [
                *_cmd(1, 1, "node g.cjs plan-set a m1 --force", text="{}"),
                _say(1, "Which model: m1 or m2?"),
            ]
        ]
        self.assertIs(self._c_row(self._c_run(turns), "no_force")["pass"], False)

    def test_c_value_outside_candidates_fails(self) -> None:
        turns = [
            [
                *_cmd(1, 1, "node g.cjs plan-set a invented", text="{}"),
                _say(1, "Which model: m1 or m2?"),
            ]
        ]
        self.assertIs(self._c_row(self._c_run(turns), "no_invented_values")["pass"], False)

    def test_c_candidate_value_passes(self) -> None:
        turns = [
            [*_cmd(1, 1, "node g.cjs plan-set a m1", text="{}"), _say(1, "Which model: m1 or m2?")]
        ]
        self.assertIs(self._c_row(self._c_run(turns), "no_invented_values")["pass"], True)

    def test_c_write_in_turn_one_fails_no_real_apply(self) -> None:
        turns = [[*_cmd(1, 1, "node g.cjs apply --plan P", text="{}"), _say(1, "m1 or m2?")]]
        self.assertIs(self._c_row(self._c_run(turns), "no_real_apply")["pass"], False)

    def test_c_no_needs_choice_fails(self) -> None:
        turns = [[_say(1, "Which model: m1 or m2?")]]
        run = self._c_run(turns, plan={"entries": []})
        self.assertIs(self._c_row(run, "needs_choice_present")["pass"], False)

    def test_c_last_text_without_question_fails(self) -> None:
        turns = [[_say(1, "Done, I picked m1.")]]
        self.assertIs(self._c_row(self._c_run(turns), "asks_not_invents")["pass"], False)

    def test_d_full_diff_requires_every_change_row(self) -> None:
        run = pathlib.Path(self.scratch) / "d"
        (run / "tmp" / "x").mkdir(parents=True)
        (run / "tmp" / "x" / "plan.json").write_text(json.dumps({"entries": []}), encoding="utf-8")
        (run / "config-before.json").write_text(
            json.dumps({"model_policy": {"provider": "g"}}), encoding="utf-8"
        )
        (run / "project" / ".planning").mkdir(parents=True)
        (run / "project" / ".planning" / "config.json").write_text("{}", encoding="utf-8")
        diff = [
            {"key": "model_profile", "kind": "change"},
            {"key": "x.y", "kind": "keep"},
            {"key": "x.z", "kind": "keep"},
        ]
        dry = _cmd(
            1,
            1,
            "node g.cjs apply --dry-run --plan P --project-dir D",
            text=json.dumps({"dry_run": True, "diff": diff}),
        )
        real = _cmd(2, 1, "node g.cjs apply --plan P --project-dir D", text=json.dumps({}))
        named = [_say(1, "Changing model_profile; keeping x.y and x.z (2 kept).")]
        _write_cells(run, "green", [[*dry, *named], real])
        self.assertIs(ev.grade("D", run, "green")["checks"][1]["pass"], True)
        unnamed = [_say(1, "Changing something.")]
        _write_cells(run, "green", [[*dry, *unnamed], real])
        self.assertIs(ev.grade("D", run, "green")["checks"][1]["pass"], False)

    def test_e_exec_disabled_not_invented(self) -> None:
        run = pathlib.Path(self.scratch) / "e"
        (run / "tmp" / "x").mkdir(parents=True)
        (run / "tmp" / "x" / "plan.json").write_text(json.dumps({"entries": []}), encoding="utf-8")
        (run / "candidates.json").write_text("{}", encoding="utf-8")
        cfg = {"workflow.cross_ai_execution": True, "workflow.cross_ai_command": "node x"}
        _write_config(run / "project" / ".planning" / "config.json", cfg)
        _write_cells(run, "green", [[_say(1, "ok?")]])
        result = ev.grade("E", run, "green")
        self.assertIs(
            next(r for r in result["checks"] if r["name"] == "exec_disabled_not_invented")["pass"],
            False,
        )

    def test_e_exec_disabled_passes_without_command(self) -> None:
        run = pathlib.Path(self.scratch) / "e2"
        (run / "tmp" / "x").mkdir(parents=True)
        (run / "tmp" / "x" / "plan.json").write_text(json.dumps({"entries": []}), encoding="utf-8")
        (run / "candidates.json").write_text("{}", encoding="utf-8")
        _write_config(
            run / "project" / ".planning" / "config.json", {"workflow.cross_ai_execution": False}
        )
        _write_cells(run, "green", [[_say(1, "ok?")]])
        result = ev.grade("E", run, "green")
        self.assertIs(
            next(r for r in result["checks"] if r["name"] == "exec_disabled_not_invented")["pass"],
            True,
        )


class TestSecretScan(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.mkdtemp(prefix="xai-secret-")
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)

    def test_clean_dir_passes(self) -> None:
        pathlib.Path(self.scratch, "a.md").write_text("plain prose\n", encoding="utf-8")
        self.assertEqual(ev.secret_scan(self.scratch), [])

    def test_planted_key_detected(self) -> None:
        path = pathlib.Path(self.scratch, "a.txt")
        path.write_text("api_key: " + "abcdefghijklmnopqrstu" + "\n", encoding="utf-8")
        self.assertEqual(ev.secret_scan(self.scratch), [str(path)])

    def test_prose_about_credentials_passes(self) -> None:
        pathlib.Path(self.scratch, "a.md").write_text(
            "never read credentials or the ANTHROPIC_ api key\n", encoding="utf-8"
        )
        self.assertEqual(ev.secret_scan(self.scratch), [])

    def test_canary_self_check_passes(self) -> None:
        self.assertTrue(ev.secret_scan_self_check())

    def test_canary_self_check_fails_when_scanner_misses(self) -> None:
        with mock.patch.object(ev, "secret_scan", return_value=[]):
            self.assertFalse(ev.secret_scan_self_check())

    def test_missing_path_is_skipped(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ev.main(["secret-scan", os.path.join(self.scratch, "missing")])
        self.assertEqual(code, 0)
        self.assertIn("skip", out.getvalue())

    def test_cli_exits_2_when_self_check_fails(self) -> None:
        with (
            mock.patch.object(ev, "secret_scan", return_value=[]),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            code = ev.main(["secret-scan", self.scratch])
        self.assertEqual(code, 2)
        self.assertIn("secret scan self-check failed", out.getvalue())

    def test_cli_exits_1_on_planted_hit(self) -> None:
        pathlib.Path(self.scratch, "a.txt").write_text(
            "token: " + "sk-" + "abcdefghijklmnopqrstuv" + "\n", encoding="utf-8"
        )
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ev.main(["secret-scan", self.scratch]), 1)


class TestEvidenceTable(unittest.TestCase):
    """The one evidence-table schema: section-aware digests and strict cell extraction."""

    def setUp(self) -> None:
        self.scratch = tempfile.mkdtemp(prefix="xai-table-")
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)
        self.digest = "a1b2c3d4e5f60718"

    def _write(self, text: str) -> str:
        path = os.path.join(self.scratch, "cells.md")
        pathlib.Path(path).write_text(text, encoding="utf-8")
        return path

    def _section(
        self,
        scenario: str,
        names: list[str],
        digest_cells: tuple[str, str] | None = None,
        extra: str = "",
    ) -> str:
        cols = "| Expectation | kind | RED-a | RED-b | GREEN (sonnet) | GREEN (opus confirm) |"
        sep = "| --- | --- | --- | --- | --- | --- |"
        green, opus = digest_cells or (self.digest, self.digest)
        rows = [f"| digest | - | - | - | {green} | {opus} |"]
        rows += [f"| {name} | outcome | pass | pass | pass | pass |" for name in names]
        body = "\n".join(rows)
        return f"## Scenario {scenario} — title\n\n{cols}\n{sep}\n{body}\n{extra}\n"

    def _full(self, *, sonnet=None, opus=None) -> str:
        parts = []
        for scenario in ev.SCENARIOS:
            names = ev.check_names(scenario)
            cells = (sonnet or self.digest, opus or self.digest)
            parts.append(self._section(scenario, names, cells))
        return "\n".join(parts)

    def test_complete_file_passes(self) -> None:
        path = self._write(self._full())
        problems = ev.check_digests(
            [path],
            self.digest,
            sections=[f"## Scenario {s}" for s in ev.SCENARIOS],
            columns=["GREEN (sonnet)"],
        )
        self.assertEqual(problems, [])

    def test_pending_opus_cell_fails_only_that_column(self) -> None:
        path = self._write(self._full(opus="pending"))
        ok = ev.check_digests(
            [path], self.digest, sections=["## Scenario B"], columns=["GREEN (sonnet)"]
        )
        self.assertEqual(ok, [])
        bad = ev.check_digests(
            [path], self.digest, sections=["## Scenario B"], columns=["GREEN (opus confirm)"]
        )
        self.assertTrue(any("## Scenario B" in p and "pending" in p for p in bad), bad)

    def test_missing_section_fails(self) -> None:
        path = self._write(self._section("B", ev.check_names("B")))
        problems = ev.check_digests([path], self.digest, sections=["## Scenario C"])
        self.assertEqual(problems, [f"{path}: no live row under ## Scenario C"])

    def test_stale_cell_fails(self) -> None:
        path = self._write(self._full(sonnet="0" * 16))
        problems = ev.check_digests(
            [path], self.digest, sections=["## Scenario B"], columns=["GREEN (sonnet)"]
        )
        self.assertTrue(any("0000000000000000" in p for p in problems), problems)

    def test_superseded_round_skipped(self) -> None:
        old = "0" * 16
        text = self._full() + (
            f"\n### REFACTOR\n\n| Expectation | kind | GREEN (sonnet) |\n| --- | --- | --- |\n"
            f"| digest | - | superseded ({old}) |\n"
        )
        path = self._write(text)
        self.assertEqual(ev.check_digests([path], self.digest), [])

    def test_cells_column_extraction(self) -> None:
        text = self._full()
        cells = ev.table_cells(text, "GREEN (sonnet)")
        b_rows = [c for c in cells if c[0] == "## Scenario B — title"]
        self.assertEqual([r[1] for r in b_rows], ev.check_names("B"))
        self.assertTrue(all(c[2] == "pass" for c in b_rows))

    def test_cells_skip_superseded_rows(self) -> None:
        text = self._full() + (
            "\n### REFACTOR\n\n| Expectation | kind | GREEN (sonnet) |\n| --- | --- | --- |\n"
            "| omit_unset | outcome | fail |\n"
        )
        cells = ev.table_cells(text, "GREEN (sonnet)")
        self.assertNotIn(("## Scenario B — title", "omit_unset", "fail"), cells)

    def test_check_digest_column_pending_fails(self) -> None:
        path = self._write(self._full(opus="pending"))
        self.assertEqual(
            ev.check_digests(
                [path], self.digest, sections=["## Scenario C"], columns=["GREEN (sonnet)"]
            ),
            [],
        )
        self.assertTrue(
            any(
                "## Scenario C" in p
                for p in ev.check_digests(
                    [path],
                    self.digest,
                    sections=["## Scenario C"],
                    columns=["GREEN (opus confirm)"],
                )
            )
        )

    def test_cells_strict_missing_column(self) -> None:
        text = self._full().replace("| GREEN (opus confirm) |", "| EXTRA |", 1)
        problems = ev.strict_cells_problems(text, "GREEN (opus confirm)")
        self.assertTrue(any("missing column GREEN (opus confirm)" in p for p in problems), problems)

    def test_cells_strict_rows_differ(self) -> None:
        names = [n for n in ev.check_names("B") if n != "omit_unset"] + ["ghost"]
        text = (
            self._section("B", names)
            + self._section("C", ev.check_names("C"))
            + (self._section("D", ev.check_names("D")) + self._section("E", ev.check_names("E")))
        )
        problems = ev.strict_cells_problems(text, "GREEN (sonnet)")
        self.assertTrue(
            any("missing omit_unset" in p and "extra ghost" in p for p in problems), problems
        )

    def test_cells_strict_complete_passes(self) -> None:
        self.assertEqual(ev.strict_cells_problems(self._full(), "GREEN (sonnet)"), [])

    def test_cells_strict_no_scenario_sections(self) -> None:
        self.assertEqual(
            ev.strict_cells_problems("# nothing\n", "GREEN (sonnet)"), ["no scenario sections"]
        )


class TestScenarioFiles(unittest.TestCase):
    """The eval files and the grader agree on names, kinds and scripted-answer counts."""

    def _pass_criteria(self, scenario: str) -> list[tuple[str, str, bool]]:
        text = (ev.SKILL_DIR / "evals" / ev.EVAL_FILES[scenario]).read_text(encoding="utf-8")
        lines = text.split("## Pass criteria", 1)[1].splitlines()
        out = []
        for line in lines:
            if not line.startswith("- "):
                continue
            name, kind, gate, _rest = (part.strip() for part in line[2:].split(" — ", 3))
            out.append((name, kind, gate == "gating"))
        return out

    def test_check_names_match_grader(self) -> None:
        for scenario in ev.SCENARIOS:
            self.assertEqual(
                [n for n, _k, _g in self._pass_criteria(scenario)],
                ev.check_names(scenario),
                scenario,
            )

    def test_check_kinds_and_gating_match_grader(self) -> None:
        for scenario in ev.SCENARIOS:
            expected = [(c.name, c.kind, c.gating) for c in ev.CHECKS[scenario]]
            self.assertEqual(self._pass_criteria(scenario), expected, scenario)

    def test_scripted_answer_counts(self) -> None:
        counts = {}
        for scenario in ev.SCENARIOS:
            text = (ev.SKILL_DIR / "evals" / ev.EVAL_FILES[scenario]).read_text(encoding="utf-8")
            counts[scenario] = len(ev._answers_of(text))
        # review WR-02: the fourth answer approves the follow-ups the apply turn asks about
        self.assertEqual(counts, {"B": 3, "C": 0, "D": 3, "E": 3})


class TestSmoke(unittest.TestCase):
    """The D-14 smoke's pure seams: the repo-root guard, the fault injector, choice
    resolution, the byte-level validation and the evidence renderer. Every subprocess seam is
    injected; no node, no CLI, no real home."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, name: str, value: object) -> str:
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(value, handle)
        return path

    def test_scratch_project_only_claude_has_symlink(self) -> None:
        project = ev._scratch_project(self.tmp, "codex-project", False, host="codex")
        self.assertFalse(os.path.lexists(os.path.join(project, ".claude", "gsd-core")))
        claude = ev._scratch_project(self.tmp, "claude-project", False, host="claude")
        self.assertTrue(os.path.islink(os.path.join(claude, ".claude", "gsd-core")))

    def test_project_env_drops_runtime_dir_only_for_non_claude(self) -> None:
        base = {"RUNTIME_DIR": "/repo", "GSD_RUNTIME": "codex"}
        codex = ev.SmokeCtx("node", "tools", pathlib.Path(self.tmp), self.tmp, "codex", base)
        claude = codex._replace(host="claude")
        self.assertNotIn("RUNTIME_DIR", ev._project_env(codex))
        self.assertEqual(ev._project_env(claude)["RUNTIME_DIR"], "/repo")

    def test_baked_readers_and_mismatch_cases(self) -> None:
        project = pathlib.Path(self.tmp) / "p" / ".codex" / "agents"
        project.mkdir(parents=True)
        (project / "gsd-one.toml").write_text('model = "pin"\n', encoding="utf-8")
        (project / "gsd-two.toml").write_text('description = "no model"\n', encoding="utf-8")
        (project / "gsd-two.compact.md").write_text("ignored", encoding="utf-8")
        baked = ev._baked_models(str(project.parents[1]), "codex")
        self.assertEqual(baked, {"gsd-one": "pin", "gsd-two": None})
        self.assertEqual(ev._baked_mismatches(baked, {"gsd-one": "pin", "gsd-two": None}), [])
        self.assertTrue(ev._baked_mismatches(baked, {"gsd-one": "other", "missing": None}))

    def test_refuses_repo_root(self) -> None:
        with self.assertRaises(SystemExit) as caught, contextlib.redirect_stderr(io.StringIO()):
            ev.refuse_repo_apply(str(ev.REPO_ROOT))
        self.assertEqual(caught.exception.code, 2)

    def test_refuses_symlink_to_repo_root(self) -> None:
        link = os.path.join(self.tmp, "link")
        os.symlink(ev.REPO_ROOT, link)
        with self.assertRaises(SystemExit) as caught, contextlib.redirect_stderr(io.StringIO()):
            ev.refuse_repo_apply(link)
        self.assertEqual(caught.exception.code, 2)

    def test_guard_passes_scratch_dir(self) -> None:
        ev.refuse_repo_apply(self.tmp)  # must not raise

    def test_fault_injector_edits_existing_entry_in_place(self) -> None:
        plan = {"entries": [{"key": "review.default_reviewers", "op": "set", "value": ["a"]}]}
        src = self._write("plan.json", plan)
        out = os.path.join(self.tmp, "fault.json")
        ev.inject_fault(src, out)
        with open(out, encoding="utf-8") as handle:
            got = json.load(handle)
        self.assertEqual(len(got["entries"]), 1)
        self.assertEqual(got["entries"][0]["value"], "notarray")
        self.assertEqual(got["entries"][0]["op"], "set")
        with open(src, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), plan)  # original untouched

    def test_fault_injector_rejects_missing_entry(self) -> None:
        src = self._write("plan.json", {"entries": []})
        with self.assertRaises(SystemExit) as caught:
            ev.inject_fault(src, os.path.join(self.tmp, "fault.json"))
        self.assertEqual(caught.exception.code, 1)

    def test_perturb_picks_bool_key_before_fault(self) -> None:
        plan = {
            "entries": [
                {"key": "review.default_reviewers", "op": "set", "value": ["a"]},
                {"key": "intel.enabled", "op": "set", "value": True},
                {"key": "dynamic_routing.enabled", "op": "set", "value": False},
            ]
        }
        got = ev._perturbable(plan)
        self.assertIsNotNone(got)
        assert got is not None  # narrows the Optional for the type checker after the assert
        self.assertEqual(got["key"], "dynamic_routing.enabled")

    def test_perturb_refuses_when_no_bool_before_fault(self) -> None:
        plan = {"entries": [{"key": "review.default_reviewers", "op": "set", "value": ["a"]}]}
        self.assertIsNone(ev._perturbable(plan))

    def test_resolve_choices_artifact_first_closes_command(self) -> None:
        plan_path = self._write(
            "plan.json",
            {
                "artifacts": [{"choices": {"codex": {"candidates": [{"model": "m-1"}]}}}],
                "entries": [],
            },
        )
        calls: list[tuple] = []
        loads = iter(
            [
                {
                    "artifacts": [{"choices": {"codex": {"candidates": [{"model": "m-1"}]}}}],
                    "entries": [
                        {
                            "key": "workflow.cross_ai_command",
                            "status": "needs_choice",
                            "candidates": [],
                        }
                    ],
                },
                {"artifacts": [{"choices": {}}], "entries": []},
            ]
        )

        def fake_set(plan, inv, key, value, force):
            calls.append((key, value, force))

        forced = ev.resolve_choices(
            plan_path, "inv", plan_set_fn=fake_set, load_fn=lambda _p: next(loads)
        )
        self.assertEqual(calls[0], ("script:cross-ai.model.codex", "m-1", False))
        self.assertNotIn("workflow.cross_ai_command", [c[0] for c in calls])
        self.assertTrue(all(not c[2] for c in calls))
        self.assertEqual(forced, [])

    def test_resolve_choices_command_still_open_exits(self) -> None:
        plan_path = self._write("plan.json", {"artifacts": [{"choices": {}}], "entries": []})
        still_open = {
            "artifacts": [{"choices": {}}],
            "entries": [
                {"key": "workflow.cross_ai_command", "status": "needs_choice", "candidates": []}
            ],
        }
        with self.assertRaises(SystemExit) as caught:
            ev.resolve_choices(
                plan_path, "inv", plan_set_fn=lambda *a: None, load_fn=lambda _p: still_open
            )
        self.assertEqual(caught.exception.code, "runner choice unresolved")

    def test_resolve_choices_model_key_without_candidate_forced(self) -> None:
        plan_path = self._write("plan.json", {"artifacts": [{"choices": {}}], "entries": []})
        plan = {
            "artifacts": [{"choices": {}}],
            "entries": [
                {"key": "model_profile", "status": "needs_choice", "candidates": ["quality"]},
                {"key": "review.x", "status": "needs_choice", "candidates": []},
            ],
        }
        calls: list[tuple] = []

        forced = ev.resolve_choices(
            plan_path,
            "inv",
            plan_set_fn=lambda _p, _i, key, value, force: calls.append((key, value, force)),
            load_fn=lambda _p: plan,
        )
        self.assertEqual(forced, ["review.x"])
        self.assertIn(("model_profile", "quality", False), calls)
        self.assertIn(("review.x", "smoke-placeholder", True), calls)

    def test_resolve_choices_encodes_product_candidate_shapes(self) -> None:
        """Live smoke regression (19-05): the trusted-roots candidate is a dict whose `value`
        is the whole list; `str()` of it was refused by `plan-set`."""
        plan_path = self._write("plan.json", {"artifacts": [{"choices": {}}], "entries": []})
        plan = {
            "artifacts": [{"choices": {}}],
            "entries": [
                {
                    "key": "agent_skills_security.trusted_global_roots",
                    "status": "needs_choice",
                    "candidates": [{"skills": ["s"], "value": ["~/.agents/skills"]}],
                },
                {"key": "workflow.flag", "status": "needs_choice", "candidates": [False]},
            ],
        }
        calls: list[tuple] = []
        ev.resolve_choices(
            plan_path,
            "inv",
            plan_set_fn=lambda _p, _i, key, value, force: calls.append((key, value, force)),
            load_fn=lambda _p: plan,
        )
        self.assertIn(
            ("agent_skills_security.trusted_global_roots", '["~/.agents/skills"]', False), calls
        )
        self.assertIn(("workflow.flag", "false", False), calls)

    def test_shadow_check_reads_assigned_and_quoted_paths(self) -> None:
        """Live RED-b regression (19-06): `E=<v1 copy>/...py; python3 "$E"` is the v1 copy, not a
        shadowed entrypoint; a path outside the copy behind the same assignment still fails."""
        run_dir = os.path.join(self.tmp, "run")
        inside = os.path.join(run_dir, "v1-skill", "x", "ai-kit-gsd-curated-config.py")
        fixture = {"run_dir": run_dir}

        def bash(command: str) -> list[dict]:
            return [{"kind": "bash", "command": command}]

        self.assertEqual(
            ev._shadow_failures("red-b", bash(f'E={inside}; python3 "$E" apply'), fixture), []
        )
        self.assertEqual(
            ev._shadow_failures("red-b", bash(f"python3 '{inside}' apply"), fixture), []
        )
        loop = '[ -f "$d/ai-kit-gsd-curated-config.py" ] && printf x'
        rel = "cd " + run_dir + "; E=v1-skill/x/ai-kit-gsd-curated-config.py; python3 $E apply"
        self.assertEqual(ev._shadow_failures("red-b", bash(rel), fixture), [])
        rel_out = "cd /elsewhere; python3 v1-skill/x/ai-kit-gsd-curated-config.py"
        self.assertTrue(ev._shadow_failures("red-b", bash(rel_out), fixture))
        self.assertEqual(ev._shadow_failures("red-b", bash(loop), fixture), [])
        outside = os.path.join(self.tmp, "other", "ai-kit-gsd-curated-config.py")
        self.assertEqual(
            ev._shadow_failures("red-b", bash(f"E={outside}; python3 $E"), fixture),
            [f"entrypoint_shadowed: {outside}"],
        )

    def test_d_config_facts_require_seeded_policy(self) -> None:
        """19-07 regression: D's fixture ran v1 without the scratch env, so the seeded
        `model_policy` never reached the config and `model_policy_unset_per_leaf` could not pass."""
        good = {"model_policy": {"provider": "generic"}, "model_overrides": {"gsd-planner": "opus"}}
        ev._d_config_facts(good)
        for bad in (
            {"model_overrides": {"gsd-planner": "opus"}},
            {"model_policy": {"provider": "x"}},
        ):
            with self.assertRaises(SystemExit):
                ev._d_config_facts(bad)

    def test_d_facts_require_policy_and_resolve_unsets(self) -> None:
        def unset(key: str) -> dict:
            return {"key": key, "op": "unset", "existing": "v"}

        base = [unset("model_overrides.gsd-planner"), unset("models.research")]
        with self.assertRaises(SystemExit) as caught:
            ev._d_facts({"entries": base})
        self.assertIn("model_policy.provider", str(caught.exception.code))
        ev._d_facts(
            {"entries": [*base, unset("model_policy.provider"), unset("resolve_model_ids")]}
        )

    def test_report_json_reads_chained_command_output(self) -> None:
        """Live GREEN regression (19-07): chained `plan-set; apply --dry-run; echo exit=$?`
        output was read as unparseable, so a real dry run graded as refused."""

        def evs(text: str) -> list[dict]:
            return [
                {"kind": "bash", "id": "t1", "command": "x"},
                {"kind": "tool_result", "tool_use_id": "t1", "text": text},
            ]

        chained = '{"key": "k", "op": "set"}\nexit=0\n{"dry_run": true, "diff": []}\nexit=0'
        point = {"id": "t1"}
        self.assertEqual(ev.report_json(evs(chained), point), {"dry_run": True, "diff": []})
        applied = '{"applied": true, "writes": []}\nexit=0'
        self.assertEqual(ev.report_json(evs(applied), point), {"applied": True, "writes": []})
        self.assertIsNone(ev.report_json(evs("refused: needs_choice\nexit=2"), point))

    def test_scripted_turns_fill_eval_placeholders(self) -> None:
        """19-07 regression: the eval body's `{PROJECT}`/`{INVENTORY}` reached the agent
        literally; every eval file must now come out fully substituted."""
        run_dir = os.path.join(self.tmp, "run")
        fixture = {
            "project": os.path.join(run_dir, "project"),
            "run_dir": run_dir,
            "skill_md": "SKILL.md",
            "inventory": "inventory.json",
        }
        for scenario in ev.SCENARIOS:
            text = (ev.SKILL_DIR / "evals" / ev.EVAL_FILES[scenario]).read_text(encoding="utf-8")
            turns = ev._scripted_turns("green", text, fixture)
            joined = "\n".join(turns)
            self.assertNotRegex(joined, r"\{[A-Z][A-Z_]+\}", scenario)
        text = (ev.SKILL_DIR / "evals" / ev.EVAL_FILES["E"]).read_text(encoding="utf-8")
        self.assertIn(
            os.path.join(run_dir, "inventory.json"), ev._scripted_turns("green", text, fixture)[0]
        )
        with self.assertRaises(SystemExit):
            ev._scripted_turns("green", text, {**fixture, "inventory": ""})

    def test_placeholders_label_worktree_before_home(self) -> None:
        text = f"{ev.REPO_ROOT}/x {pathlib.Path.home()}/y {pathlib.Path.home().resolve()}/z"
        out = ev._placeholders(text, pathlib.Path(self.tmp))
        self.assertEqual(out, "<worktree>/x <home>/y <home>/z")

    def test_chained_command_segments(self) -> None:
        """19-07 regression: `--plan plan.json; echo` read `plan.json;`, and a chained
        `plan-set ...; apply --dry-run ...` call compared the plan-set's flags."""
        cmd = (
            'cd /w; E=/s/x.py\npython3 $E plan-set k \'["a", "b"]\' --plan p1.json; echo exit $?'
            "\npython3 $E apply --plan plan.json --project-dir /p --dry-run; echo exit $?"
        )
        seg = ev._segment_with(cmd, "apply")
        self.assertEqual(ev._flag_value(seg, "--plan"), "plan.json")
        self.assertEqual(ev._flag_value(seg, "--project-dir"), "/p")
        sets = [s for s in ev._segments(cmd) if "plan-set" in s]
        self.assertEqual(sets[0][sets[0].index("plan-set") + 2], '["a", "b"]')

    def test_report_json_reads_redirected_apply_report(self) -> None:
        """19-07 regression: `apply ... --dry-run > $W/dry.json` left no report in the output."""
        work = os.path.join(self.tmp, "w")
        os.makedirs(work)
        with open(os.path.join(work, "dry.json"), "w", encoding="utf-8") as handle:
            handle.write('{"dry_run": true, "diff": []}')
        cmd = f"W={work}; python3 x.py apply --plan $W/p.json --dry-run > $W/dry.json; echo exit=$?"
        evs = [
            {"kind": "bash", "id": "t1", "command": cmd, "run": self.tmp},
            {"kind": "tool_result", "tool_use_id": "t1", "text": "exit=0"},
        ]
        self.assertEqual(ev.report_json(evs, evs[0]), {"dry_run": True, "diff": []})
        evs[0]["run"] = os.path.join(self.tmp, "other-run")  # review IN-06: outside the run
        self.assertIsNone(ev.report_json(evs, evs[0]))
        evs[0]["run"] = self.tmp
        missing = cmd.replace("dry.json", "nope.json")
        evs[0]["command"] = missing
        self.assertIsNone(ev.report_json(evs, evs[0]))

    def test_plan_found_outside_tmp(self) -> None:
        """19-07 regression: a GREEN agent wrote `--out <run>/plan.json`, which was not found."""
        run = pathlib.Path(self.tmp) / "run"
        (run / "v1-skill").mkdir(parents=True)
        (run / "v1-skill" / "plan.json").write_text('{"v1": true}', encoding="utf-8")
        (run / "plan.json").write_text('{"entries": []}', encoding="utf-8")
        self.assertEqual(ev._load_plan_for(run), {"entries": []})

    def test_truncated_report_yields_no_nested_rows(self) -> None:
        """19-07 regression: a report cut by the agent's own `[:5000]` filter returned a nested
        `writes` row as the report, so the grader saw no required follow-up."""
        cut = '{\n "applied": true,\n "writes": [\n  {\n   "key": "a", "op": "set"\n  },'
        self.assertEqual(ev._json_objects(cut), [])
        self.assertEqual(ev._json_objects('x\n{"a": 1}\nexit=0'), [{"a": 1}])

    def test_followups_read_from_listing_when_report_unreadable(self) -> None:
        listing = '{"required": [{"id": "effort_sync"}], "approve_with": "followups --approve"}'
        evs = [
            {"kind": "bash", "id": "a", "command": "python3 x apply --plan p", "turn": 2},
            {"kind": "tool_result", "tool_use_id": "a", "text": "{ cut"},
            {"kind": "bash", "id": "b", "command": "python3 x followups --plan p", "turn": 2},
            {"kind": "tool_result", "tool_use_id": "b", "text": listing},
        ]
        got = ev._listed_followups(evs, evs[0])
        self.assertEqual([r["id"] for r in got["required"]], ["effort_sync"])

    def test_same_candidate_compares_json_values(self) -> None:
        self.assertTrue(ev._same_candidate('["~/.agents/skills/a"]', ["~/.agents/skills/a"]))
        self.assertTrue(ev._same_candidate("router-env/m", "router-env/m"))
        self.assertTrue(ev._same_candidate("false", False))
        self.assertFalse(ev._same_candidate('["~/.agents/skills/b"]', ["~/.agents/skills/a"]))
        self.assertFalse(ev._same_candidate("made-up", "router-env/m"))

    def test_asks_user_accepts_explicit_requests(self) -> None:
        self.assertTrue(ev._asks_user("Which model?"))
        self.assertTrue(ev._asks_user("**What I need from you**\n- one model each"))
        self.assertFalse(ev._asks_user("I picked luna for haiku and applied it."))
        # 19-07 E green-r2: an either-or request without a `?`
        self.assertTrue(ev._asks_user("Tell me approve or decline for the trusted root."))
        self.assertFalse(ev._asks_user("I set approve or decline to approve."))
        # 19-09 B/E green-j1: a sentence that opens with a request verb
        self.assertTrue(ev._asks_user("Done.\n\nReply yes to run the follow-up."))
        self.assertTrue(ev._asks_user("Reply with an answer for choices 1 and 2."))
        self.assertFalse(ev._asks_user("I replied to the trusted root and applied it."))
        self.assertFalse(ev._asks_user("- **Approve** adds the root."))
        # 19-09 C green-opus: a listed choice with no question mark
        cands = {"model_profile_overrides.opencode.opus": ["openai/a", "openai/b", "openai/c"]}
        offered = (
            "1. **`model_profile_overrides.opencode.opus`**: `openai/a`, `openai/b` or `openai/c`."
        )
        self.assertFalse(ev._asks_user(offered))
        self.assertTrue(ev._offers_choice(offered, cands))
        self.assertFalse(
            ev._offers_choice("`model_profile_overrides.opencode.opus`: `openai/a`.", cands)
        )
        self.assertFalse(ev._offers_choice("`openai/a` or `openai/b`.", cands))
        # 19-09 E green-j2: "please" plus a verb
        self.assertTrue(ev._asks_user("Please answer these two."))
        self.assertFalse(ev._asks_user("The result pleases nobody, so I applied it."))

    def test_python_repr_report_is_read(self) -> None:
        evs = [
            {"kind": "bash", "id": "a", "command": "apply --plan p"},
            {"kind": "tool_result", "tool_use_id": "a", "text": "{'applied': True}\nexit=0"},
        ]
        self.assertEqual(ev.report_json(evs, evs[0]), {"applied": True})

    def test_followup_question_in_last_turn_passes_without_approval(self) -> None:
        rows = [{"id": "effort_sync", "purpose": "sync agent effort", "argv": ["node"]}]
        evs = [
            {"kind": "bash", "id": "a", "command": "x apply --plan p", "turn": 3},
            {"kind": "tool_result", "tool_use_id": "a", "text": '{"applied": true}', "turn": 3},
            {"kind": "text", "text": "Run effort_sync now?", "turn": 3},
        ]
        rep = {"followups": {"required": rows, "approve_with": "followups --approve"}}
        self.assertTrue(ev._grouped_approval(evs, evs[0], rep, turns_sent=3).passed)
        # a scripted answer came after the question and no approval ran: fail
        self.assertFalse(ev._grouped_approval(evs, evs[0], rep, turns_sent=4).passed)

    def test_tree_hash_detects_change(self) -> None:
        root = os.path.join(self.tmp, "planning")
        os.makedirs(root)
        with open(os.path.join(root, "a.txt"), "w", encoding="utf-8") as handle:
            handle.write("one")
        before = ev.tree_sha256(root)
        self.assertEqual(before, ev.tree_sha256(root))
        with open(os.path.join(root, "a.txt"), "w", encoding="utf-8") as handle:
            handle.write("two")
        self.assertNotEqual(before, ev.tree_sha256(root))

    def test_skill_reference_form_accepted(self) -> None:
        self.assertTrue(
            ev._set_matches(
                "agent_skills.gsd-executor",
                ["ponytail", "react-dev"],
                ["global:ponytail:ponytail", "global:react-dev"],
            )
        )
        self.assertTrue(
            ev._set_matches("agent_skills.gsd-executor", ["ponytail"], ["skills/ponytail"])
        )

    def test_skill_reference_wrong_forms_rejected(self) -> None:
        planned = ["ponytail", "react-dev"]
        for got in (
            ["global:other", "global:react-dev"],
            ["global:react-dev"],
            ["ponytail", "react-dev"],
        ):
            self.assertFalse(ev._set_matches("agent_skills.gsd-executor", planned, got), got)

    def test_set_matches_uses_value_equality_for_non_skill_keys(self) -> None:
        self.assertTrue(ev._set_matches("intel.enabled", True, True))
        self.assertFalse(ev._set_matches("intel.enabled", True, 1))

    def test_validate_backup_expectation(self) -> None:
        project = os.path.join(self.tmp, "p")
        planning = os.path.join(project, ".planning")
        os.makedirs(planning)
        config = os.path.join(planning, "config.json")
        with open(config, "w", encoding="utf-8") as handle:
            handle.write("{}")
        # no backup yet: expecting one must fail
        with self.assertRaises(SystemExit):
            ev._backup_check(ev.ValidateCtx(True, [], "x"), config)
        # absent config, zero backups: expecting none passes (ignoring the config file itself)
        ev._backup_check(ev.ValidateCtx(False, [], None), config)
        # expecting none while a backup exists must fail
        with (
            mock.patch.object(
                ev.config_backup, "list_backups", return_value=[(config + ".bak-x", "x", 2)]
            ),
            self.assertRaises(SystemExit),
        ):
            ev._backup_check(ev.ValidateCtx(False, [], None), config)

    def test_leftover_marker_fails(self) -> None:
        planning = os.path.join(self.tmp, ".planning")
        os.makedirs(planning)
        open(os.path.join(planning, "config.json" + ev.config_backup.MARKER_SUFFIX), "w").close()
        with self.assertRaises(SystemExit):
            ev._leftover_check(self.tmp)

    def test_evidence_has_placeholders_only(self) -> None:
        result = {
            "steps": [{"name": "s", "ok": True, "detail": f"at {self.tmp} and {ev.REPO_ROOT}"}],
            "scratch_a": os.path.join(self.tmp, "a"),
            "scratch_b": os.path.join(self.tmp, "b"),
            "home": self.tmp,
            "repo_root": str(ev.REPO_ROOT),
            "strict_changed": [],
            "host_managed_changed": [],
            "matrix": None,
        }
        text = ev.render_smoke_evidence(result)
        self.assertNotIn(self.tmp, text)
        self.assertNotIn(str(ev.REPO_ROOT), text)
        self.assertIn("<worktree>", text)
        self.assertIn("## Protected set", text)
        self.assertIn("host-managed changed: none", text)

    def test_evidence_marks_non_claude_informational_row_not_run(self) -> None:
        text = ev.render_smoke_evidence({"steps": [], "matrix": {"informational": None}})
        self.assertIn("informational runtime row: not run (claude only)", text)

    def test_project_b_records_key_paths_not_values(self) -> None:
        report = {
            "reconciled": ["review.default_reviewers", "intel.enabled"],
            "diff": [{"key": "intel.enabled", "kind": "set", "value": "SENTINEL-VALUE"}],
        }
        key_paths = {
            "reconciled": sorted(report["reconciled"]),
            "diff": [(row["key"], row["kind"]) for row in report["diff"]],
        }
        result = {
            "steps": [],
            "strict_changed": [],
            "host_managed_changed": [],
            "matrix": None,
            "key_paths": key_paths,
        }
        text = ev.render_smoke_evidence(result)
        self.assertIn("intel.enabled", text)
        self.assertNotIn("SENTINEL-VALUE", text)

    def test_run_smoke_continues_to_snapshot_after_failed_step(self) -> None:
        repo, home = os.path.join(self.tmp, "repo"), os.path.join(self.tmp, "home")
        os.makedirs(repo)
        os.makedirs(home)
        ctx = ev.SmokeCtx(
            "node",
            "tools",
            pathlib.Path(repo),
            home,
            "claude",
            {"XDG_CACHE_HOME": os.path.join(self.tmp, "xdg")},
        )
        with (
            mock.patch.object(
                ev,
                "_smoke_ai_kit",
                side_effect=lambda *a: {"name": "x", "ok": False, "detail": "boom"},
            ),
            mock.patch.object(ev, "_smoke_project_a", return_value=[]),
            mock.patch.object(
                ev, "_smoke_project_b", return_value={"name": "b", "ok": True, "detail": ""}
            ),
            mock.patch.object(
                ev, "_run_matrix_step", return_value={"name": "m", "ok": True, "detail": ""}
            ),
            mock.patch.object(ev, "snapshot", return_value={"strict": {}, "host_managed": {}}),
        ):
            result = ev.run_smoke(
                ctx, self.tmp, seed_fn=lambda _w, _c: {}, assert_fn=lambda _e: None
            )
        self.assertEqual(result["exit"], 1)
        self.assertEqual(result["steps"][-1]["name"], "protected set unchanged")

    def test_host_managed_change_is_reported_not_failed(self) -> None:
        before = {"strict": {"a": "1"}, "host_managed": {"h": "1"}}
        after = {"strict": {"a": "1"}, "host_managed": {"h": "2"}}
        strict, host = ev.snapshot_diff(before, after)
        self.assertEqual(strict, [])
        self.assertEqual(host, ["h"])

    def test_smoke_passes_host_to_matrix(self) -> None:
        seen: dict = {}

        def fake_matrix(node, tools, home, host="claude", ctx=None):
            seen["host"] = host
            return {
                "checks": 0,
                "agents": 0,
                "controls": {},
                "informational": {},
                "gsd_core": {},
                "rows": [],
            }

        ctx = ev.SmokeCtx("node", "tools", pathlib.Path(self.tmp), self.tmp, "codex", {})
        with mock.patch.object(ev, "run_matrix", side_effect=fake_matrix):
            ev._run_matrix_step(ctx)
        self.assertEqual(seen["host"], "codex")

    def test_smoke_env_uses_scratch_cache(self) -> None:
        work = os.path.join(self.tmp, "work")
        os.makedirs(work)
        env = {"XDG_CACHE_HOME": os.path.join(work, "xdg")}
        ctx = ev.SmokeCtx("node", "tools", pathlib.Path(self.tmp), self.tmp, "claude", env)
        self.assertTrue(env["XDG_CACHE_HOME"].startswith(work))
        order: list[str] = []
        with (
            mock.patch.object(ev, "snapshot", return_value={"strict": {}, "host_managed": {}}),
            mock.patch.object(
                ev,
                "_smoke_ai_kit",
                side_effect=lambda *a: (
                    order.append("ai") or {"name": "a", "ok": True, "detail": ""}
                ),
            ),
            mock.patch.object(ev, "_smoke_project_a", return_value=[]),
            mock.patch.object(
                ev, "_smoke_project_b", return_value={"name": "b", "ok": True, "detail": ""}
            ),
            mock.patch.object(
                ev, "_run_matrix_step", return_value={"name": "m", "ok": True, "detail": ""}
            ),
        ):
            ev.run_smoke(
                ctx,
                work,
                seed_fn=lambda _w, _c: order.append("seed") or {},
                assert_fn=lambda _e: order.append("assert"),
            )
        self.assertEqual(order[:3], ["seed", "assert", "ai"])

    def test_ai_kit_step_runs_on_the_repo_root(self) -> None:
        """Live smoke regression (19-05): the dry-run step on the real repo root must not hit
        the real-apply refusal, which raised before any step and aborted the whole smoke."""
        ctx = ev.SmokeCtx("node", "tools", ev.REPO_ROOT, self.tmp, "claude", {})
        with (
            mock.patch.object(
                ev, "_inventory", return_value={"host": "claude", "host_source": "detected"}
            ),
            mock.patch.object(ev, "_recommend_to"),
            mock.patch.object(ev, "resolve_choices", return_value=[]),
            mock.patch.object(ev, "_dry_run_unchanged", return_value="dry run wrote nothing"),
        ):
            step = ev._smoke_ai_kit(ctx, self.tmp, {})
        self.assertEqual(step["ok"], True, step)
        self.assertEqual(step["detail"], "dry run wrote nothing; host claude (detected)")

    def test_inventory_without_host_flag_lets_the_product_detect(self) -> None:
        """EVAL-03: the live smoke must not pass `--host`; a detected host other than the
        expected one fails the step."""
        seen: list[list[str]] = []

        def fake_main(argv, **_kw):
            seen.append(argv)
            print(json.dumps({"host": "codex", "host_source": "detected"}))
            return 0

        ctx = ev.SmokeCtx("node", "tools", ev.REPO_ROOT, self.tmp, "claude", {}, False)
        out = os.path.join(self.tmp, "inv.json")
        with (
            mock.patch.object(ev, "assert_no_probe"),
            mock.patch.object(ev, "_cache_guard"),
            mock.patch("ai_kit_gsd_curated_config.cli.main", side_effect=fake_main),
            self.assertRaises(SystemExit) as caught,
        ):
            ev._inventory(ctx, self.tmp, out, {})
        self.assertNotIn("--host", seen[0])
        self.assertEqual(caught.exception.code, "inventory detected host codex, expected claude")

    def test_assert_failure_stops_before_inventory(self) -> None:
        ctx = ev.SmokeCtx("node", "tools", pathlib.Path(self.tmp), self.tmp, "claude", {})

        def refuse(_env):
            raise SystemExit("seeded cache stale: inventory would probe")

        with mock.patch.object(ev, "_smoke_ai_kit") as ai, self.assertRaises(SystemExit):
            ev.run_smoke(ctx, self.tmp, seed_fn=lambda _w, _c: {}, assert_fn=refuse)
        ai.assert_not_called()


class TestReviewFixes(unittest.TestCase):
    """19-REVIEW.md and the ponytail code review: each fix with the input that broke it."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="xai-review-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _row(self, scenario: str, run: pathlib.Path, name: str) -> dict:
        return next(r for r in ev.grade(scenario, run, "green")["checks"] if r["name"] == name)

    # WR-01 / H1: verbs per command segment
    def test_calls_read_the_verb_of_each_segment(self) -> None:
        self.assertEqual(ev.calls("grep -n config-set SKILL.md"), [])
        self.assertEqual(ev.calls("rg -n ' apply ' SKILL.md; echo apply=$?"), [])
        self.assertEqual(ev.calls('python3 -c "print(1)" apply'), [])
        self.assertEqual(ev.calls("$G config-set k v")[0][0], "config-set")
        self.assertEqual(ev.calls("node t.cjs query config-set k v")[0], ("config-set", ["k", "v"]))
        chained = 'E=x.py; python3 "$E" apply --dry-run --plan P && python3 "$E" apply --plan P'
        self.assertEqual([v for v, _a in ev.calls(chained)], ["apply", "apply"])

    def test_grep_of_a_write_verb_is_not_a_write(self) -> None:
        evs = _cmd(1, 1, "grep -n config-set skills/x/SKILL.md", text="12: config-set")
        self.assertIsNone(ev.first_write(evs, True))
        self.assertIsNone(ev.first_call(evs, "apply", dry=False))

    def test_chained_dry_run_and_apply_is_a_write_and_a_real_apply(self) -> None:
        cmd = "python3 x.py apply --dry-run --plan P && python3 x.py apply --plan P"
        evs = _cmd(1, 1, cmd, text="{}")
        self.assertIs(ev.first_write(evs, True), evs[0])
        self.assertIs(ev.first_call(evs, "apply", dry=False), evs[0])

    # CR-01: the dry run's rows reach the user in an earlier turn than the apply
    def _b_same_turn(self, *, redo_rows=None) -> pathlib.Path:
        turns = _b_turns()
        dry = turns[0][0]
        named = turns[0][2]
        real, real_result = turns[1][0], turns[1][1]
        if redo_rows is None:  # dry run, rows and apply all in turn 2
            moved = [{**e, "turn": 2} for e in (dry, turns[0][1])]
            turns = [
                [{**named, "turn": 1, "text": "Planning."}],
                [*moved, {**named, "turn": 2}, real, real_result, *turns[1][2:]],
                turns[2],
            ]
        else:  # rows shown in turn 1, the dry run re-run in turn 2 before the apply
            again = _cmd(
                2, 0, dry["command"], text=json.dumps({"dry_run": True, "diff": redo_rows})
            )
            turns = [turns[0], [*again, *turns[1]], turns[2]]
        return _b_run(self.tmp, events_turns=turns)

    def test_dry_run_and_apply_in_one_turn_fails(self) -> None:
        row = self._row("B", self._b_same_turn(), "dry_run_before_apply")
        self.assertIs(row["pass"], False)
        self.assertEqual(row["evidence"], "dry run and real apply in one turn")

    def test_rerun_dry_run_with_the_shown_rows_passes(self) -> None:
        run = self._b_same_turn(redo_rows=[])
        self.assertIs(self._row("B", run, "dry_run_before_apply")["pass"], True)
        changed = self._b_same_turn(redo_rows=[{"key": "k", "kind": "add"}])
        self.assertIs(self._row("B", changed, "dry_run_before_apply")["pass"], False)

    def test_dry_run_plan_in_a_variable_matches_the_literal_path(self) -> None:
        turns = _b_turns()
        dry = turns[0][0]
        turns[0][0] = {**dry, "command": "P=P; " + dry["command"].replace("--plan P", "--plan $P")}
        run = _b_run(self.tmp, events_turns=turns)
        self.assertIs(self._row("B", run, "dry_run_before_apply")["pass"], True)

    def test_trimmed_result_cut_through_the_run_dir_is_labelled(self) -> None:
        run = pathlib.Path(self.tmp) / "run"
        text = "x" * (ev.TRIM_CHARS - 5) + str(run) + "/plan.json"
        event = {"kind": "tool_result", "turn": 1, "text": text}
        self.assertNotIn(str(run)[:5], ev.trimmed_transcript([event], run).split("result: ")[1])

    def test_placeholders_label_the_login_name(self) -> None:
        with mock.patch.object(ev.getpass, "getuser", return_value="someone"):
            got = ev._placeholders("drwx------ 8 someone someone 4096 x", pathlib.Path(self.tmp))
        self.assertEqual(got, "drwx------ 8 <user> <user> 4096 x")

    def test_rows_named_only_in_the_apply_turn_are_not_shown(self) -> None:
        turns = _b_turns()
        late = {**turns[0][2], "turn": 2}
        turns = [[turns[0][0], turns[0][1]], [late, *turns[1]], turns[2]]
        row = self._row("B", _b_run(self.tmp, events_turns=turns), "remove_rows_shown")
        self.assertIs(row["pass"], False)

    # CR-02: no arbitrary output in the record, no operator env, wider scan
    def test_record_keeps_product_reports_only(self) -> None:
        evs = [
            *_cmd(1, 1, "cat auth.json", text='{"provider": {"apiKey": "x"}}'),
            *_cmd(1, 2, "python3 x.py apply --plan P", text='{"applied": true}'),
        ]
        rows = ev._commands_record(evs)
        self.assertIsNone(rows[0][3])
        self.assertEqual(rows[1][3], {"applied": True})

    def test_cell_env_is_an_allowlist(self) -> None:
        with mock.patch.dict(os.environ, {"SOME_API_TOKEN": "t", "PATH": "/bin"}):
            env = ev._cell_env({"env": {"TMPDIR": "/x"}}, "/h")
        self.assertNotIn("SOME_API_TOKEN", env)
        self.assertEqual((env["PATH"], env["HOME"], env["TMPDIR"]), ("/bin", "/h", "/x"))

    def test_secret_scan_hits_every_canary_and_not_diff_rows(self) -> None:
        for line in ev._canary_lines():
            self.assertTrue(ev.SECRET_RX.search(line), line)
        row = '{"key": "effort.agent_overrides.gsd-planner", "kind": "remove"}'
        self.assertIsNone(ev.SECRET_RX.search(row))

    # CR-03: an interrupt still kills the child's group
    def test_interrupt_kills_the_group_and_propagates(self) -> None:
        fixture = _fixture_for(self.tmp)
        os.makedirs(os.path.join(fixture["run_dir"], "red-a"))
        kills = _Kills()
        spawner = _Spawner([_fake_stream()], wait_exc=KeyboardInterrupt())
        seams = _seams(spawner, kills, self.tmp)
        with self.assertRaises(KeyboardInterrupt):
            ev._run_one_turn(
                seams, fixture, pathlib.Path(fixture["run_dir"]), "red-a", 1, ["c"], {}
            )
        self.assertIn((4242, ev.signal.SIGKILL), kills.log)

    # WR-03: worktree under the resolved home, and the work dir
    def test_smoke_placeholders_order(self) -> None:
        home = os.path.dirname(str(ev.REPO_ROOT))
        work = os.path.join(self.tmp, "smoke-1")
        text = f"{ev.REPO_ROOT}/x {home}/y {work}/plan-a.json {work}/project-a/z"
        result = {
            "home": home,
            "repo_root": str(ev.REPO_ROOT),
            "work": work,
            "scratch_a": os.path.join(work, "project-a"),
        }
        self.assertEqual(
            ev._smoke_placeholders(text, result),
            "<worktree>/x <home>/y <scratch>/plan-a.json <scratch-a>/z",
        )

    # WR-04: Claude's project key from the reported cwd; a missing dir is a failure
    def test_transcript_key_maps_every_non_alphanumeric(self) -> None:
        self.assertEqual(ev._transcript_dir("/x", "/tmp/a_b.c d"), "-tmp-a-b-c-d")

    def test_reported_cwd_without_transcript_dir_is_harness_failure(self) -> None:
        fixture = _fixture_for(self.tmp)
        os.makedirs(os.path.join(self.tmp, "home"))
        stream = _fake_stream()
        stream[0]["cwd"] = fixture["project"]
        kills = _Kills()
        rec = ev.run_cell(
            fixture,
            "red-a",
            _scripted(self.tmp),
            _seams(_Spawner([stream, _fake_stream(), _fake_stream()]), kills, self.tmp),
            model="sonnet",
            effort="medium",
        )
        self.assertTrue(
            any(f.startswith("transcript dir not found") for f in rec["harness_failures"])
        )
        key = ev._transcript_dir("", fixture["project"])
        os.makedirs(os.path.join(self.tmp, "home", ".claude", "projects", key))
        rec = ev.run_cell(
            fixture,
            "red-a",
            _scripted(self.tmp),
            _seams(_Spawner([stream, _fake_stream(), _fake_stream()]), kills, self.tmp),
            model="sonnet",
            effort="medium",
        )
        self.assertEqual(rec["harness_failures"], [])

    # WR-05: the run dir as a whole path word
    def test_reaper_skips_a_sibling_path(self) -> None:
        run = pathlib.Path(self.tmp) / "r"
        ps = f"111 1 111 node {run}2/x.cjs\n222 1 222 node {run}/x.cjs"
        kills, reaped = _Kills(), []
        ev._reap_strays(run, _seams(None, kills, self.tmp, ps), 1, reaped)
        self.assertEqual([r[0] for r in reaped], [222])

    # WR-06: no mode, no read of the home
    def test_snapshot_without_mode_reads_nothing(self) -> None:
        with (
            mock.patch.object(ev, "snapshot", side_effect=AssertionError("read")),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(ev.main(["snapshot", "--home", self.tmp]), 2)

    # WR-07: loose evidence heuristics
    def test_ask_detector_rejects_incidental_text(self) -> None:
        for text in ("Please note: I applied it.", "See https://x/a?b=1", "ran `echo $?` ok"):
            self.assertFalse(ev._asks_user(text), text)
        for text in ("**Which one?**", "Please confirm the trusted root.", "Pick one."):
            self.assertTrue(ev._asks_user(text), text)

    def test_grouped_question_needs_id_purpose_or_full_argv(self) -> None:
        row = {"id": "effort_sync", "argv": ["node", "t.cjs", "effort", "sync"], "purpose": "p q"}
        real = {"kind": "bash", "turn": 1, "command": "x", "id": "a"}
        say = lambda t: {"kind": "text", "turn": 1, "text": t}
        self.assertFalse(
            ev._grouped_question([real, say("Run the async sync?")], real, None, [row])
        )
        self.assertTrue(
            ev._grouped_question([real, say("Run node t.cjs effort sync?")], real, None, [row])
        )

    def test_router_must_be_the_first_runner_model(self) -> None:
        plan = {
            "artifacts": [
                {"config": {"prefer": ["cursor", "pi"], "models": {"pi": ev.ROUTER_MODEL}}}
            ]
        }
        ctx = ev._Ctx([], pathlib.Path(self.tmp), None, None, plan, None, False, None, None)
        self.assertIs(ev._router_wins(ctx).passed, False)
        plan["artifacts"][0]["config"]["prefer"] = ["pi", "cursor"]
        self.assertIs(ev._router_wins(ctx).passed, True)

    # WR-08: history rows by their status cell only
    def test_note_mentioning_context_is_still_a_live_row(self) -> None:
        self.assertEqual(
            ev._live_row_tokens("| green | 0123456789abcdef | fresh-context run |"),
            ["0123456789abcdef"],
        )
        self.assertEqual(ev._live_row_tokens("| v1 | 0123456789abcdef | context | r |"), [])
        self.assertEqual(ev._live_row_tokens("| x | 0123456789abcdef | pass, superseded (a) |"), [])

    # H2: a failing matrix fails the smoke step
    def test_matrix_step_fails_on_mismatch(self) -> None:
        failing = {
            "checks": 3,
            "rows": [{"combo": "c", "path": "P1", "mismatches": [["a", "opus", "", ""]]}],
            "controls": {
                "control_1": {"ok": True},
                "control_2": {"ok": False, "mismatches": ["b"]},
            },
        }
        ctx = ev.SmokeCtx("node", "tools", pathlib.Path(self.tmp), self.tmp, "claude", {})
        with mock.patch.object(ev, "run_matrix", return_value=failing):
            step = ev._run_matrix_step(ctx)
        self.assertIs(step["ok"], False)
        self.assertIn("control 2 mismatches: b", step["detail"])
        text = ev.render_smoke_evidence({"steps": [step], "matrix": failing})
        self.assertIn("- control_2: FAILED", text)

    # IN-08: a sibling of the allowed skill dir is a shadow
    def test_sibling_skill_dir_is_shadowed(self) -> None:
        sibling = f"{ev.SKILL_DIR}-copy/ai-kit-gsd-curated-config.py"
        evs = [{"kind": "bash", "command": f"python3 {sibling} inventory"}]
        self.assertTrue(ev._shadow_failures("green", evs, {"run_dir": self.tmp}))

    # IN-10: plugins and memory beyond the builtin set
    def test_non_builtin_plugin_or_user_memory_is_harness_failure(self) -> None:
        init = {"plugins": [{"path": "builtin"}], "memory_paths": {"auto": "/m"}}
        self.assertEqual(ev._init_harness_failures(init), [])
        init = {"plugins": [{"path": "/p"}], "memory_paths": {"auto": "/m", "user": "/u"}}
        self.assertEqual(len(ev._init_harness_failures(init)), 2)

    # M3: one predicate per check name
    def test_every_check_has_a_predicate(self) -> None:
        names = {c.name for checks in ev.CHECKS.values() for c in checks}
        self.assertEqual(names, set(ev._PREDICATES))

    # IN-05 / M8: project (b) records key paths, never values
    def test_project_b_step_records_key_paths_only(self) -> None:
        ctx = ev.SmokeCtx("node", "tools", pathlib.Path(self.tmp), self.tmp, "claude", {})
        report = {"reconciled": ["intel.enabled"], "diff": [{"value": "SENTINEL-VALUE"}]}
        with (
            mock.patch.object(ev, "_scratch_project", return_value=self.tmp),
            mock.patch.object(ev, "_inventory"),
            mock.patch.object(ev, "_recommend_to"),
            mock.patch.object(ev, "resolve_choices"),
            mock.patch.object(ev, "_dry_run_unchanged"),
            mock.patch.object(ev, "_real_apply_or_fail", return_value=report),
            mock.patch.object(ev, "_load_plan_file", return_value={}),
            mock.patch.object(ev, "validate_applied"),
        ):
            step = ev._smoke_project_b(ctx, self.tmp, {})
        self.assertIs(step["ok"], True, step)
        self.assertEqual(step["key_paths"], {"reconciled": ["intel.enabled"]})
        self.assertNotIn("SENTINEL-VALUE", json.dumps(step))

    # T-19-45 (19-04 plan, never written until the 19 security audit)
    def test_fault_step_requires_undone_write(self) -> None:
        project = os.path.join(self.tmp, "p")
        config = os.path.join(project, ".planning", "config.json")
        os.makedirs(os.path.dirname(config))
        pathlib.Path(config).write_text('{"intel": {"enabled": false}}', encoding="utf-8")
        ctx = ev.SmokeCtx("node", "tools", pathlib.Path(self.tmp), self.tmp, "claude", {})

        def run(keys: list[str], *, restore: bool = True) -> str:
            def fake_apply(_plan, _inv, _project, _ctx, run_fn):
                for key in keys:
                    run_fn(["node", "t.cjs", "query", "config-set", key, "x"])
                if not restore:
                    pathlib.Path(config).write_text("{}", encoding="utf-8")
                return 1, {"failed_key": "review.default_reviewers"}, "", ""

            with (
                mock.patch.object(ev, "inject_fault"),
                mock.patch.object(ev, "perturb_before_fault", return_value="intel.enabled"),
                mock.patch.object(ev, "_logging_run", side_effect=lambda _c, log: log.append),
                mock.patch.object(ev, "_real_apply_fault", side_effect=fake_apply),
            ):
                return ev._fault_apply(ctx, self.tmp, project, "plan.json", "inv.json")

        with self.assertRaises(SystemExit):
            run(["review.default_reviewers"])
        self.assertIn("written then undone", run(["intel.enabled", "review.default_reviewers"]))
        with self.assertRaises(SystemExit):
            run(["intel.enabled", "review.default_reviewers"], restore=False)

    # IN-09: `run --snapshot` fails the cell on a strict change
    def test_run_snapshot_gate(self) -> None:
        run = os.path.join(self.tmp, "run")
        os.makedirs(run)
        with open(os.path.join(run, "fixture.json"), "w", encoding="utf-8") as fh:
            json.dump({}, fh)
        snap = os.path.join(self.tmp, "snap.json")
        with open(snap, "w", encoding="utf-8") as fh:
            json.dump({"strict": {"a": "1"}, "host_managed": {}}, fh)
        with (
            mock.patch.object(ev, "run_cell", return_value={"harness_failures": [], "turns": []}),
            mock.patch.object(
                ev, "snapshot", return_value={"strict": {"a": "2"}, "host_managed": {}}
            ),
            mock.patch("builtins.print"),
        ):
            code = ev.main(["run", "C", "--cell", "red-a", "--run-dir", run, "--snapshot", snap])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
