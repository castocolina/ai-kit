"""Unit tests for cross_ai_script render, state classification, and write planning."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-gsd-curated-config"))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import cli, cross_ai, cross_ai_script
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS

TEMPLATE_PATH = os.path.join(
    REPO_ROOT, "skills", "ai-kit-spec-review", "references", "cross-ai.mjs"
)


def _load_template() -> bytes:
    with open(TEMPLATE_PATH, "rb") as f:
        return f.read()


def _artifact(**overrides) -> dict:
    base = cross_ai.script_artifact([], cross_ai.MIN_TIMEOUT_S)
    base["config"] = {
        "prefer": ["pi", "cursor"],
        "models": {"pi": "router-env/my-coding"},
        "outer_timeout_s": 1800,
        "router_backed": {"pi": True},
    }
    base.update(overrides)
    return base


class TestRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = _load_template()

    def test_template_version_constants_match_the_shipped_template(self):
        # C-WR-04/PT-07: plans stamp TEMPLATE_VERSION; readiness is a floor at or below it.
        shipped = cross_ai_script.template_version(self.template)
        self.assertEqual(cross_ai.TEMPLATE_VERSION, shipped)
        self.assertLessEqual(cross_ai_script._READY_TEMPLATE, shipped)

    def test_project_paths_match_the_runner_dispatch_paths(self):
        # PT-07: the GSD hook names files this module renders.
        from ai_kit_spec import runner_dispatch
        self.assertEqual(cross_ai.SCRIPT_PATH, runner_dispatch.PROJECT_RUNNER_PATH)
        self.assertEqual(cross_ai_script.GUIDANCE_PATH, runner_dispatch.PROJECT_GUIDANCE_PATH)

    def test_runner_config_maps_artifact_fields(self):
        art = _artifact()
        art["choices"] = {"codex": {"candidates": []}}
        cfg = cross_ai_script.runner_config(self.template, art, HOST_SIGNAL_ENV_VARS)
        self.assertEqual(cfg["prefer"], ["pi", "cursor"])
        self.assertEqual(cfg["models"], {"pi": "router-env/my-coding"})
        self.assertEqual(cfg["outerTimeoutS"], 1800)
        self.assertEqual(cfg["routerBacked"], {"pi": True})
        self.assertEqual(cfg["scrubEnv"], sorted(HOST_SIGNAL_ENV_VARS))
        self.assertIn("backoffS", cfg)
        self.assertEqual(cfg["effort"], {})
        art["config"]["effort"] = {"pi": "medium"}
        cfg = cross_ai_script.runner_config(self.template, art, HOST_SIGNAL_ENV_VARS)
        self.assertEqual(cfg["effort"], {"pi": "medium"})

    def test_render_idempotent(self):
        art = _artifact()
        cfg = cross_ai_script.runner_config(self.template, art, HOST_SIGNAL_ENV_VARS)
        first = cross_ai_script.render(self.template, cfg)
        second = cross_ai_script.render(self.template, cfg)
        self.assertEqual(first, second)

    def test_header_is_line_two(self):
        art = _artifact()
        rendered = cross_ai_script.render(
            self.template,
            cross_ai_script.runner_config(self.template, art, HOST_SIGNAL_ENV_VARS),
        )
        lines = rendered.split(b"\n", 2)
        self.assertTrue(lines[0].startswith(b"#!"))
        self.assertTrue(cross_ai_script.HEADER_RE.match(lines[1]))

    def test_crlf_body_hashed_raw(self):
        art = _artifact()
        cfg = cross_ai_script.runner_config(self.template, art, HOST_SIGNAL_ENV_VARS)
        rendered = cross_ai_script.render(self.template, cfg)
        parts = cross_ai_script.split_header(rendered)
        assert parts is not None
        shebang, _header, body = parts
        body_crlf = body.replace(b"\n", b"\r\n", 1)
        digest = hashlib.sha256(body_crlf).hexdigest()
        header = (
            b"// ai-kit-cross-ai generator=ai-kit-gsd-curated-config "
            b"template=3 sha256=" + digest.encode()
        )
        crlf_file = shebang + b"\n" + header + b"\n" + body_crlf
        self.assertEqual(cross_ai_script.script_state(crlf_file), "pristine")

    def test_command_splits_without_shell(self):
        # GSD expands ${CROSS_AI_CMD} unquoted: plain word splitting, no shell parsing.
        self.assertEqual(cross_ai.CROSS_AI_COMMAND.split(), ["node", cross_ai.SCRIPT_PATH])


class TestScriptState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = _load_template()

    def test_mismatched_header_reads_edited(self):
        art = _artifact()
        rendered = cross_ai_script.render(
            self.template,
            cross_ai_script.runner_config(self.template, art, HOST_SIGNAL_ENV_VARS),
        )
        parts = cross_ai_script.split_header(rendered)
        assert parts is not None
        shebang, _header, body = parts
        fake = b"// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=3 sha256="
        fake += b"0" * 64
        tampered = shebang + b"\n" + fake + b"\n" + body
        self.assertEqual(cross_ai_script.script_state(tampered), "edited")

    def test_trailing_newline_is_edited(self):
        art = _artifact()
        rendered = cross_ai_script.render(
            self.template,
            cross_ai_script.runner_config(self.template, art, HOST_SIGNAL_ENV_VARS),
        )
        self.assertEqual(cross_ai_script.script_state(rendered + b"\n"), "edited")


class TestPlanScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = _load_template()

    def _render(self, art=None) -> bytes:
        artifact = art or _artifact()
        return cross_ai_script.render(
            self.template,
            cross_ai_script.runner_config(self.template, artifact, HOST_SIGNAL_ENV_VARS),
        )

    def test_add_creates_scripts_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = _artifact()
            plan = cross_ai_script.plan_script(tmp, art, self.template, HOST_SIGNAL_ENV_VARS)
            self.assertEqual(plan.kind, "add")
            cross_ai_script.write_script(plan)
            target = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            self.assertTrue(os.path.isfile(target))

    def test_keep_pristine_skips_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = _artifact()
            data = self._render(art)
            target = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(data)
            mtime = os.path.getmtime(target)
            time.sleep(0.02)
            plan = cross_ai_script.plan_script(tmp, art, self.template, HOST_SIGNAL_ENV_VARS)
            self.assertEqual(plan.kind, "keep-pristine")
            cross_ai_script.write_script(plan)
            with open(target, "rb") as f:
                self.assertEqual(f.read(), data)
            self.assertEqual(os.path.getmtime(target), mtime)

    def test_pristine_different_models_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = _artifact()
            data = self._render(art)
            target = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(data)
            art2 = _artifact()
            art2["config"] = dict(art2["config"])
            art2["config"]["models"] = {"cursor": "auto"}
            plan = cross_ai_script.plan_script(tmp, art2, self.template, HOST_SIGNAL_ENV_VARS)
            self.assertEqual(plan.kind, "change")
            cross_ai_script.write_script(plan)
            with open(target, "rb") as f:
                updated = f.read()
            self.assertNotEqual(updated, data)
            self.assertEqual(cross_ai_script.script_state(updated), "pristine")

    def test_edited_goes_to_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = _artifact()
            data = self._render(art)
            target = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            new_path = target + ".new"
            os.makedirs(os.path.dirname(target), exist_ok=True)
            edited = data + b"\n"
            with open(target, "wb") as f:
                f.write(edited)
            with open(new_path, "wb") as f:
                f.write(b"stale")
            mtime = os.path.getmtime(target)
            plan = cross_ai_script.plan_script(tmp, art, self.template, HOST_SIGNAL_ENV_VARS)
            self.assertEqual(plan.kind, "new-as-.new")
            cross_ai_script.write_script(plan)
            with open(target, "rb") as f:
                self.assertEqual(f.read(), edited)
            self.assertEqual(os.path.getmtime(target), mtime)
            with open(new_path, "rb") as f:
                self.assertEqual(f.read(), plan.data)

    def test_unstamped_and_foreign_go_to_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = _artifact()
            target = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            unstamped = (
                b"#!/usr/bin/env node\n"
                b"// ai-kit-cross-ai generator=ai-kit-gsd-curated-config "
                b"template=3 sha256=UNSTAMPED\n"
                b"// body\n"
            )
            with open(target, "wb") as f:
                f.write(unstamped)
            plan = cross_ai_script.plan_script(tmp, art, self.template, HOST_SIGNAL_ENV_VARS)
            self.assertEqual(plan.state, "unstamped")
            self.assertEqual(plan.kind, "new-as-.new")
            foreign = b"#!/usr/bin/env node\n// not a header\nbody\n"
            with open(target, "wb") as f:
                f.write(foreign)
            plan2 = cross_ai_script.plan_script(tmp, art, self.template, HOST_SIGNAL_ENV_VARS)
            self.assertEqual(plan2.state, "foreign")
            self.assertEqual(plan2.kind, "new-as-.new")

    def test_edit_between_plan_and_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = _artifact()
            data = self._render(art)
            target = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(data)
            art2 = _artifact()
            art2["config"] = dict(art2["config"])
            art2["config"]["models"] = {"cursor": "auto"}
            plan = cross_ai_script.plan_script(tmp, art2, self.template, HOST_SIGNAL_ENV_VARS)
            self.assertEqual(plan.kind, "change")
            with open(target, "ab") as f:
                f.write(b"// user\n")
            performed = cross_ai_script.write_script(plan)
            self.assertEqual(performed.kind, "new-as-.new")
            self.assertIn("changed after planning", performed.note)
            with open(target, "rb") as f:
                self.assertTrue(f.read().endswith(b"// user\n"))

    def test_keep_pristine_edit_between_plan_and_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = _artifact()
            data = self._render(art)
            target = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(data)
            plan = cross_ai_script.plan_script(tmp, art, self.template, HOST_SIGNAL_ENV_VARS)
            self.assertEqual(plan.kind, "keep-pristine")
            with open(target, "ab") as f:
                f.write(b"// touch\n")
            performed = cross_ai_script.write_script(plan)
            self.assertEqual(performed.kind, "new-as-.new")

    def test_create_between_plan_and_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = _artifact()
            plan = cross_ai_script.plan_script(tmp, art, self.template, HOST_SIGNAL_ENV_VARS)
            self.assertEqual(plan.kind, "add")
            target = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(b"other")
            performed = cross_ai_script.write_script(plan)
            self.assertEqual(performed.kind, "new-as-.new")
            with open(target, "rb") as f:
                self.assertEqual(f.read(), b"other")

    def test_template_version_bump(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = _artifact()
            data = self._render(art)
            target = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(data)
            template_v4 = re.sub(rb"template=3", b"template=4", self.template, count=1)
            plan = cross_ai_script.plan_script(tmp, art, template_v4, HOST_SIGNAL_ENV_VARS)
            self.assertEqual(plan.kind, "change")
            cross_ai_script.write_script(plan)
            with open(target, "rb") as f:
                out = f.read()
            parts = cross_ai_script.split_header(out)
            assert parts is not None
            match = cross_ai_script.HEADER_RE.match(parts[1])
            assert match is not None
            self.assertEqual(int(match.group(1)), 4)


def _v2_pristine(template: bytes, prefer: list) -> bytes:
    """A pristine script stamped template=2, body otherwise identical to a current render."""
    cfg = cross_ai_script.template_config(template)
    cfg["prefer"] = prefer
    cfg["scrubEnv"] = sorted(HOST_SIGNAL_ENV_VARS)
    rendered = cross_ai_script.render(template, cfg)
    return re.sub(rb"template=3", b"template=2", rendered, count=1)


class TestEnsureRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = _load_template()

    def test_upgrade_tracer(self):
        from ai_kit_spec.runner_dispatch import RunnerSpec, project_runner_command

        with tempfile.TemporaryDirectory() as tmp:
            old = _v2_pristine(self.template, ["codex"])
            target = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as handle:
                handle.write(old)
            code, result = _run_ensure(
                ["--cwd", tmp, "--guidance-file", "-"], stdin_text="GUIDE"
            )
            self.assertEqual(code, 0)
            self.assertTrue(result["ready"])
            self.assertEqual(result["runner"], "change")
            self.assertEqual(result["guidance"], "add")
            with open(target, "rb") as handle:
                upgraded = handle.read()
            self.assertIn(b"template=3", upgraded.split(b"\n", 2)[1])
            self.assertEqual(
                cross_ai_script.template_config(upgraded)["prefer"], ["codex"]
            )
            guidance = os.path.join(tmp, ".planning", "scripts", "cross-ai-guidance.md")
            with open(guidance, "rb") as handle:
                text = handle.read()
            lines = text.split(b"\n")
            self.assertTrue(lines[0].startswith(b"<!-- "))
            self.assertTrue(lines[1].startswith(b"<!-- ai-kit-cross-ai-guidance "))
            self.assertTrue(text.endswith(b"GUIDE"))

            command = project_runner_command(
                RunnerSpec("codex", "gpt-5.6-sol", "exec", 0,
                           codex_sandbox="workspace-write"),
                guidance=True,
            )
            assert command is not None
            tokens = command.split()
            self.assertEqual(tokens[0], "node")
            self.assertEqual(tokens[1], ".planning/scripts/cross-ai.mjs")
            if shutil.which("node") is None:
                self.skipTest("node not on PATH")
            proc = subprocess.run(
                ["node", target, "--print-argv", *tokens[2:]],
                cwd=tmp, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("workspace-write", proc.stdout)


def _run_ensure(argv, stdin_text=None):
    out = io.StringIO()
    stdin = io.StringIO("" if stdin_text is None else stdin_text)
    with contextlib.redirect_stdout(out), unittest.mock.patch("sys.stdin", stdin):
        code = cli.main(["ensure-runner", *argv])
    return code, json.loads(out.getvalue())


def _current_pristine(template: bytes) -> bytes:
    cfg = cross_ai_script.template_config(template)
    cfg["scrubEnv"] = sorted(HOST_SIGNAL_ENV_VARS)
    return cross_ai_script.render(template, cfg)


class TestEnsureRunnerStates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = _load_template()

    def _runner(self, tmp):
        return os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")

    def test_absent_adds_and_is_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, result = _run_ensure(["--cwd", tmp])
            self.assertEqual(code, 0)
            self.assertEqual(result["runner"], "add")
            self.assertTrue(result["ready"])
            self.assertTrue(os.path.isfile(self._runner(tmp)))

    def test_pristine_current_kept_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _current_pristine(self.template)
            target = self._runner(tmp)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as handle:
                handle.write(data)
            code, result = _run_ensure(["--cwd", tmp])
            self.assertEqual((code, result["runner"]), (0, "keep-pristine"))
            with open(target, "rb") as handle:
                self.assertEqual(handle.read(), data)

    def test_edited_template_2_writes_new_and_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _v2_pristine(self.template, ["codex"]) + b"\n"
            target = self._runner(tmp)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as handle:
                handle.write(data)
            code, result = _run_ensure(["--cwd", tmp])
            self.assertEqual(code, 1)
            self.assertFalse(result["ready"])
            self.assertEqual(result["runner"], "new-as-.new")
            self.assertTrue(any(target + ".new" in note for note in result["notes"]))
            with open(target, "rb") as handle:
                self.assertEqual(handle.read(), data)
            self.assertTrue(os.path.isfile(target + ".new"))

    def test_edited_template_3_kept_and_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = _current_pristine(self.template) + b"\n"
            target = self._runner(tmp)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as handle:
                handle.write(data)
            code, result = _run_ensure(["--cwd", tmp])
            self.assertEqual((code, result["runner"]), (0, "keep-edited"))
            self.assertTrue(result["ready"])
            with open(target, "rb") as handle:
                self.assertEqual(handle.read(), data)
            self.assertFalse(os.path.exists(target + ".new"))

    def test_unstamped_current_runner_note_says_unstamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = self._runner(tmp)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as handle:
                handle.write(self.template)
            code, result = _run_ensure(["--cwd", tmp])
            self.assertEqual((code, result["runner"]), (0, "keep-edited"))
            self.assertEqual(
                result["notes"], [f"existing {target} is unstamped (sha256=UNSTAMPED) and "
                                  "current; kept"],
            )

    def test_foreign_writes_new_and_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = self._runner(tmp)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as handle:
                handle.write(b"#!/usr/bin/env node\n// mine\n")
            code, result = _run_ensure(["--cwd", tmp])
            self.assertEqual(code, 1)
            self.assertFalse(result["ready"])
            self.assertTrue(os.path.isfile(target + ".new"))

    def test_guidance_pristine_new_text_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _run_ensure(["--cwd", tmp, "--guidance-file", "-"], stdin_text="one")
            code, result = _run_ensure(
                ["--cwd", tmp, "--guidance-file", "-"], stdin_text="two"
            )
            self.assertEqual((code, result["guidance"]), (0, "change"))
            path = os.path.join(tmp, ".planning", "scripts", "cross-ai-guidance.md")
            with open(path, "rb") as handle:
                self.assertTrue(handle.read().endswith(b"two"))

    def test_guidance_user_edited_writes_new_and_stays_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            _run_ensure(["--cwd", tmp, "--guidance-file", "-"], stdin_text="one")
            path = os.path.join(tmp, ".planning", "scripts", "cross-ai-guidance.md")
            with open(path, "ab") as handle:
                handle.write(b"\nuser")
            with open(path, "rb") as handle:
                edited = handle.read()
            code, result = _run_ensure(
                ["--cwd", tmp, "--guidance-file", "-"], stdin_text="two"
            )
            self.assertEqual(code, 0)
            self.assertTrue(result["ready"])
            self.assertEqual(result["guidance"], "new-as-.new")
            self.assertTrue(result["notes"])
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), edited)
            self.assertTrue(os.path.isfile(path + ".new"))


class TestEnsureRunnerErrors(unittest.TestCase):
    def test_directory_at_runner_path_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            os.makedirs(target)
            code, result = _run_ensure(["--cwd", tmp])
            self.assertEqual(code, 2)
            self.assertFalse(result["ready"])
            self.assertIn("cannot read", result["error"])
            self.assertFalse(os.path.exists(target + ".new"))

    def test_missing_template_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch.object(
            cross_ai_script, "load_template", return_value=(None, "sibling missing")
        ):
            code, result = _run_ensure(["--cwd", tmp])
            self.assertEqual(code, 2)
            self.assertIn("sibling missing", result["error"])
            self.assertFalse(os.path.exists(os.path.join(tmp, ".planning")))

    def test_template_open_oserror_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch.object(
            cross_ai_script, "load_template", side_effect=OSError("disk")
        ):
            code, result = _run_ensure(["--cwd", tmp])
            self.assertEqual(code, 2)
            self.assertIn("disk", result["error"])
            self.assertFalse(os.path.exists(os.path.join(tmp, ".planning")))

    def test_unparsable_template_header_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch.object(
            cross_ai_script, "load_template", return_value=(b"no header\n", None)
        ):
            code, result = _run_ensure(["--cwd", tmp])
            self.assertEqual(code, 2)
            self.assertTrue(result["error"])
            self.assertFalse(os.path.exists(os.path.join(tmp, ".planning")))

    def test_publish_oserror_for_runner_leaves_runner_null(self):
        with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch.object(
            cross_ai_script, "_publish", side_effect=OSError("full")
        ):
            code, result = _run_ensure(["--cwd", tmp])
            self.assertEqual(code, 2)
            self.assertIsNone(result["runner"])
            self.assertIn("full", result["error"])

    def test_publish_oserror_for_guidance_names_the_written_runner(self):
        real = cross_ai_script._publish

        def fail_guidance(path, data):
            if path.endswith("cross-ai-guidance.md"):
                raise OSError(f"cannot write {path}")
            real(path, data)

        with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch.object(
            cross_ai_script, "_publish", side_effect=fail_guidance
        ):
            code, result = _run_ensure(
                ["--cwd", tmp, "--guidance-file", "-"], stdin_text="GUIDE"
            )
            self.assertEqual(code, 2)
            self.assertEqual(result["runner"], "add")
            self.assertIsNone(result["guidance"])
            self.assertIn("cross-ai-guidance.md", result["error"])
            self.assertFalse(result["ready"])

    def test_directory_at_guidance_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            guide = os.path.join(tmp, ".planning", "scripts", "cross-ai-guidance.md")
            os.makedirs(guide)
            code, result = _run_ensure(
                ["--cwd", tmp, "--guidance-file", "-"], stdin_text="GUIDE"
            )
            self.assertEqual(code, 2)
            self.assertIn("cannot read", result["error"])
            self.assertIn("cross-ai-guidance.md", result["error"])

    def test_non_utf8_guidance_file_exits_2_with_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            guide = os.path.join(tmp, "guide.md")
            with open(guide, "wb") as handle:
                handle.write(b"\xff\xfe not utf-8")
            code, result = _run_ensure(["--cwd", tmp, "--guidance-file", guide])
            self.assertEqual(code, 2)
            self.assertFalse(result["ready"])
            self.assertIn(f"cannot read {guide}", result["error"])

    def test_empty_guidance_rejected_before_any_write(self):
        for text in ("", "   \n\t"):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                code, result = _run_ensure(
                    ["--cwd", tmp, "--guidance-file", "-"], stdin_text=text
                )
                self.assertEqual(code, 2)
                self.assertEqual(result["error"], "guidance text is empty")
                self.assertFalse(
                    os.path.exists(os.path.join(tmp, ".planning", "scripts"))
                )


class TestApplyExecutionHookToken(unittest.TestCase):
    """C-WR-02/C-IN-05: a model the unquoted hook cannot carry degrades by name before the
    runner render, and a run that wrote no hook prints no pi exec note."""

    def test_unsafe_model_degrades_before_any_render(self):
        from ai_kit_spec.runner_dispatch import PI_EXEC_NOTE

        from tests.test_ai_kit_gsd_curated_config import (
            _make_fake_install,
            _which_stub,
            make_fake_run,
        )

        with tempfile.TemporaryDirectory() as install, tempfile.TemporaryDirectory() as project:
            _make_fake_install(install)
            run = make_fake_run([(0, "ok", "")])
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = cli.main(
                    ["apply-execution", "--project-dir", project, "--cli", "pi",
                     "--model", "my model"],
                    which_fn=_which_stub(), run_fn=run,
                    env_fn=lambda: {"CLAUDE_CONFIG_DIR": install},
                )
            summary = json.loads(out.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(summary["degraded_reason"], "unsafe_hook_token")
            self.assertFalse(summary["cross_ai_command_written"])
            self.assertIsNone(summary["runner"])
            self.assertIn("'my model'", err.getvalue())
            self.assertFalse(os.path.exists(os.path.join(project, ".planning")))
            self.assertEqual(
                [call[3] for call in run.calls if "config-set" in call],
                ["workflow.cross_ai_execution"],
            )
            self.assertEqual(summary["notes"], [])
            self.assertNotIn(PI_EXEC_NOTE, err.getvalue())


class TestReadTarget(unittest.TestCase):
    def test_missing_file_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(
                cross_ai_script._read_target(os.path.join(tmp, "absent"))
            )

    def test_directory_raises_script_read_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "adir")
            os.makedirs(target)
            with self.assertRaises(cross_ai_script.ScriptReadError) as ctx:
                cross_ai_script._read_target(target)
            self.assertIn(f"cannot read {target}", str(ctx.exception))
            self.assertIsInstance(ctx.exception, ValueError)


if __name__ == "__main__":
    unittest.main()
