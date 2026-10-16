"""Unit tests for cross_ai_script render, state classification, and write planning."""

from __future__ import annotations

import hashlib
import os
import re
import sys
import tempfile
import time
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-gsd-curated-config"))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import cross_ai, cross_ai_script
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
            b"template=2 sha256=" + digest.encode()
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
        fake = b"// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=2 sha256="
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
                b"template=2 sha256=UNSTAMPED\n"
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
            template_v3 = re.sub(rb"template=2", b"template=3", self.template, count=1)
            plan = cross_ai_script.plan_script(tmp, art, template_v3, HOST_SIGNAL_ENV_VARS)
            self.assertEqual(plan.kind, "change")
            cross_ai_script.write_script(plan)
            with open(target, "rb") as f:
                out = f.read()
            parts = cross_ai_script.split_header(out)
            assert parts is not None
            match = cross_ai_script.HEADER_RE.match(parts[1])
            assert match is not None
            self.assertEqual(int(match.group(1)), 3)


if __name__ == "__main__":
    unittest.main()
