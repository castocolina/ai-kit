"""R4 (D-07) sibling-first resolution tests: both resolvers must try the from-checkout
sibling skill before any installed copy (`$CLAUDE_PLUGIN_ROOT`, `$HOME/.claude/skills`,
XDG opencode skills, `$HOME/.agents/skills`), because an installed copy may point at
another branch. Also pins the no-write property and the branch-checkout import case.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CHECKOUT_ROOT = Path(__file__).resolve().parents[1]

# Make the two packages importable from the checkout regardless of how the
# test runner was invoked.
for _p in (
    CHECKOUT_ROOT / "skills" / "ai-kit-project-rules-all",
    CHECKOUT_ROOT / "skills" / "_shared",
    CHECKOUT_ROOT / "skills" / "ai-kit-gsd-curated-config",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from ai_kit_gsd_curated_config import model_detect
from ai_kit_project_rules_all import dispatch


class TestModelDetectSiblingFirst(unittest.TestCase):
    """model_detect.resolve_ai_kit_spec_path tries the sibling first (R4)."""

    def test_sibling_wins_over_home_copy(self):
        def isdir_fn(path):
            return path in (
                os.path.join("/somewhere", "skills", "ai-kit-spec-review"),
                os.path.join("/home/user", ".claude", "skills", "ai-kit-spec-review"),
            )

        result = model_detect.resolve_ai_kit_spec_path(
            os.path.join("/somewhere", "skills", "ai-kit-gsd-curated-config"),
            env={"HOME": "/home/user"},
            isdir_fn=isdir_fn,
        )
        self.assertEqual(
            result, os.path.join("/somewhere", "skills", "ai-kit-spec-review", "ai-kit-spec.py")
        )

    def test_sibling_wins_over_plugin_root(self):
        def isdir_fn(path):
            return path in (
                os.path.join("/somewhere", "skills", "ai-kit-spec-review"),
                os.path.join("/plugin/root", "skills", "ai-kit-spec-review"),
            )

        result = model_detect.resolve_ai_kit_spec_path(
            os.path.join("/somewhere", "skills", "ai-kit-gsd-curated-config"),
            env={"CLAUDE_PLUGIN_ROOT": "/plugin/root", "HOME": "/nonexistent"},
            isdir_fn=isdir_fn,
        )
        self.assertEqual(
            result, os.path.join("/somewhere", "skills", "ai-kit-spec-review", "ai-kit-spec.py")
        )

    def test_plugin_root_only(self):
        result = model_detect.resolve_ai_kit_spec_path(
            os.path.join("/somewhere", "skills", "ai-kit-gsd-curated-config"),
            env={"CLAUDE_PLUGIN_ROOT": "/plugin/root", "HOME": "/nonexistent"},
            isdir_fn=lambda path: path
            == os.path.join("/plugin/root", "skills", "ai-kit-spec-review"),
        )
        self.assertEqual(
            result, os.path.join("/plugin/root", "skills", "ai-kit-spec-review", "ai-kit-spec.py")
        )

    def test_none_when_nothing_found(self):
        result = model_detect.resolve_ai_kit_spec_path(
            os.path.join("/nonexistent", "skills", "ai-kit-gsd-curated-config"),
            env={"HOME": "/nonexistent"},
            isdir_fn=lambda path: False,
        )
        self.assertIsNone(result)


class TestBranchCheckoutImport(unittest.TestCase):
    """End to end: a subprocess run from the checkout's curated-config skill dir must
    import the checkout's own `ai_kit_spec`, even with a decoy installed copy under an
    alternate HOME's `.claude/skills` (R4, D-07). Realpath-compared so symlinks cannot
    fake or break the match."""

    def test_import_resolves_to_checkout_sibling(self):
        with tempfile.TemporaryDirectory() as home:
            decoy = Path(home) / ".claude" / "skills" / "ai-kit-spec-review" / "ai_kit_spec"
            decoy.mkdir(parents=True)
            (decoy / "__init__.py").write_text("DECOY = True\n")
            shim = Path(home) / ".claude" / "skills" / "ai-kit-spec-review" / "ai-kit-spec.py"
            shim.write_text("# decoy shim\n")
            skip = ("CLAUDE_PLUGIN_ROOT", "HOME", "PYTHONPATH")
            env = {k: v for k, v in os.environ.items() if k not in skip}
            env["HOME"] = home
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import ai_kit_gsd_curated_config.cross_ai_build, sys;"
                    ' print(sys.modules["ai_kit_spec"].__file__)',
                ],
                cwd=str(CHECKOUT_ROOT / "skills" / "ai-kit-gsd-curated-config"),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            printed = proc.stdout.strip()
            self.assertTrue(
                os.path.realpath(printed).startswith(
                    os.path.realpath(str(CHECKOUT_ROOT)) + os.sep
                ),
                f"expected the checkout's ai_kit_spec, got {printed}",
            )
            # Decoy home untouched: the resolver only probes paths.
            self.assertTrue((decoy / "__init__.py").read_text() == "DECOY = True\n")


class TestRulesAllSiblingFirst(unittest.TestCase):
    """dispatch.resolve_entrypoint tries the checkout sibling first (R4)."""

    def test_sibling_entrypoint_wins_over_installed_copies(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as plugin, \
                tempfile.TemporaryDirectory() as xdg:
            name = "ai-kit-project-rules-agents"
            for root, parts in (
                (home, (".claude", "skills")),
                (plugin, ("skills",)),
                (xdg, ("opencode", "skills")),
            ):
                d = Path(root).joinpath(*parts) / name
                d.mkdir(parents=True)
                (d / f"{name}.py").write_text("# decoy\n")
            with mock.patch.dict(
                os.environ,
                {
                    "HOME": home,
                    "CLAUDE_PLUGIN_ROOT": plugin,
                    "XDG_CONFIG_HOME": xdg,
                },
            ):
                result = dispatch.resolve_entrypoint(name)
            expected = (
                CHECKOUT_ROOT / "skills" / name / f"{name}.py"
            )
            self.assertEqual(
                os.path.realpath(str(result)), os.path.realpath(str(expected))
            )

    def test_none_when_nothing_found(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as plugin, \
                tempfile.TemporaryDirectory() as xdg:
            before = {p: sorted(os.listdir(p)) for p in (home, plugin, xdg)}
            with mock.patch.dict(
                os.environ,
                {
                    "HOME": home,
                    "CLAUDE_PLUGIN_ROOT": plugin,
                    "XDG_CONFIG_HOME": xdg,
                },
            ):
                result = dispatch.resolve_entrypoint("ai-kit-no-such-skill")
            self.assertIsNone(result)
            after = {p: sorted(os.listdir(p)) for p in (home, plugin, xdg)}
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
