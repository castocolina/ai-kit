"""check-providers: stale opencode provider report (SPEC R5, D-02, D-03).

Every opencode listing is a fake through CliDeps.run_fn; no host CLI runs. Files are synthetic
and live in a scratch dir (never the real config or cache).
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, config_io, trust

SKILL_MD = os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-config", "SKILL.md")
CHECK_ONLY_MD = os.path.join(
    _REPO_ROOT, "skills", "ai-kit-spec-config", "references", "check-only.md"
)
EVALS_JSON = os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-config", "evals", "evals.json")
UNCONFIRMED = (
    " (unconfirmed: config file only; built-in, login and environment providers not checked)"
)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


class _Scratch(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-p31-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.proj = os.path.join(self.root, "proj")
        os.makedirs(self.proj)
        self.env = {
            "HOME": os.path.join(self.root, "home"),
            "XDG_CONFIG_HOME": os.path.join(self.root, "config"),
            "XDG_CACHE_HOME": os.path.join(self.root, "cache"),
            "XDG_DATA_HOME": os.path.join(self.root, "data"),
        }
        self.local = os.path.join(self.proj, ".aikit", "review-spec.toml")
        self.global_path = os.path.join(self.env["XDG_CONFIG_HOME"], "ai-kit", "review-spec.toml")
        self.catalog = os.path.join(
            self.env["XDG_CACHE_HOME"], "ai-kit", "spec", "model-catalog.json"
        )
        self.listing = "anthropic/claude-x\nopencode/free-y\n"
        self.listed_rc = 0
        self.binary = True

    def _trust(self, path):
        with open(path, "rb") as handle:
            raw = handle.read()
        trust.record_trust(config_io.cfg_trust_store_dir(self.env), os.path.realpath(path), raw)

    def _deps(self):
        def which_fn(name, *_args, **_kwargs):
            return "/fake/bin/opencode" if self.binary and name == "opencode" else None

        def run_fn(argv, **_kwargs):
            return subprocess.CompletedProcess(argv, self.listed_rc, self.listing, "")

        return cli.CliDeps(which_fn=which_fn, run_fn=run_fn, env_fn=lambda: self.env)

    def _report(self, deps=None):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = cli.main(["check-providers", "--cwd", self.proj], deps or self._deps())
        self.assertEqual(rc, 0)
        return out.getvalue().splitlines()

    @staticmethod
    def _opencode_reviewer(key, model):
        return f'[[reviewers]]\nkey = "{key}"\nruntime = "opencode"\nmodel = "{model}"\n'

    def _local_reviewers(self, *reviewers):
        text = "".join(
            f'[[reviewers]]\nkey = "{key}"\nruntime = "{runtime}"\nmodel = "{model}"\n'
            for key, runtime, model in reviewers
        )
        _write(self.local, text)
        self._trust(self.local)


class TestCheckProvidersTracer(_Scratch):
    def test_stale_reviewer_warned_in_order(self):
        self._local_reviewers(("oc-gone", "opencode", "gone/model-x"))
        lines = self._report()
        self.assertEqual(
            lines,
            [
                f"cross-reference: {self.local} scanned",
                f"cross-reference: {self.global_path} absent",
                f"cross-reference: {self.catalog} absent",
                "served providers: listed by opencode (anthropic, opencode)",
                f'warning: "gone" is referenced in {self.local}: oc-gone model=gone/model-x',
            ],
        )

    def test_served_model_gives_no_warning(self):
        self._local_reviewers(("oc-ok", "opencode", "anthropic/claude-x"))
        self.assertFalse([line for line in self._report() if line.startswith("warning:")])

    def test_runtime_name_is_not_matched_as_a_provider(self):
        self._local_reviewers(
            ("free", "opencode", "opencode/free-y"),
            ("claude-review", "claude", "opus"),
        )
        self.assertFalse([line for line in self._report() if line.startswith("warning:")])

    def test_cwd_defaults_to_process_cwd(self):
        self._local_reviewers(("oc-gone", "opencode", "gone/model-x"))
        out = io.StringIO()
        with mock.patch("os.getcwd", return_value=self.proj), redirect_stdout(out):
            rc = cli.main(["check-providers"], self._deps())
        self.assertEqual(rc, 0)
        self.assertIn(f"cross-reference: {self.local} scanned", out.getvalue())


class TestCheckProvidersSources(_Scratch):
    def test_trusted_local_only_marks_global_inactive(self):
        _write(self.local, 'strategy = "local-only"\n')
        self._trust(self.local)
        _write(self.global_path, self._opencode_reviewer("g", "gone/m"))
        lines = self._report()
        self.assertIn(f"cross-reference: {self.global_path} scanned-inactive", lines)
        self.assertIn(
            f'warning: "gone" is referenced in {self.global_path}: g model=gone/m'
            ' (not active: local review-spec sets strategy = "local-only")',
            lines,
        )

    def test_untrusted_local_does_not_deactivate_global(self):
        _write(
            self.local,
            'strategy = "local-only"\n[[reviewers]]\nkey = "l"\nruntime = "opencode"\n'
            'model = "gone2/m"\n',
        )
        _write(self.global_path, self._opencode_reviewer("g", "gone/m"))
        lines = self._report()
        self.assertIn(f"cross-reference: {self.local} scanned-inactive (untrusted)", lines)
        self.assertIn(f"cross-reference: {self.global_path} scanned", lines)
        self.assertIn(
            f'warning: "gone2" is referenced in {self.local}: l model=gone2/m'
            " (not active: local review-spec is not trusted)",
            lines,
        )
        self.assertIn(f'warning: "gone" is referenced in {self.global_path}: g model=gone/m', lines)

    def test_invalid_local_toml_is_unreadable_not_fatal(self):
        _write(self.local, "not = [valid\n")
        lines = self._report()
        self.assertTrue(
            any(line.startswith(f"cross-reference: {self.local} scanned (unreadable: ")
                for line in lines)
        )

    def test_invalid_catalog_json_is_unreadable(self):
        _write(self.catalog, "{not json")
        self.assertIn(
            f"cross-reference: {self.catalog} scanned (unreadable: not valid JSON)",
            self._report(),
        )

    def test_catalog_reference_and_meta_skipped(self):
        _write(
            self.catalog,
            '{"_meta": {"schema_version": 2},'
            ' "x/y": {"provider": "x", "runtimes": {"opencode": {"model_id": "gone/y"}}},'
            ' "a/b": {"provider": "anthropic", "runtimes": {"claude": {"model_id": "opus"}}}}',
        )
        warnings = [line for line in self._report() if line.startswith("warning:")]
        self.assertEqual(
            warnings,
            [
                f'warning: "gone" is referenced in {self.catalog}: x/y'
                " runtimes.opencode.model_id=gone/y"
            ],
        )

    def test_project_config_providers_are_added_to_the_listing(self):
        self._local_reviewers(("p", "opencode", "proj/m"))
        _write(os.path.join(self.proj, "opencode.json"), '{"provider": {"proj": {}}}')
        lines = self._report()
        self.assertIn(
            "served providers: listed by opencode plus project config files"
            " (anthropic, opencode, proj)",
            lines,
        )
        self.assertFalse([line for line in lines if line.startswith("warning:")])

    def test_empty_listing_is_not_checked_without_warning(self):
        self._local_reviewers(("g", "opencode", "gone/m"))
        self.listing = ""
        lines = self._report()
        self.assertIn("served providers: not checked: opencode listed no models", lines)
        self.assertFalse([line for line in lines if line.startswith("warning:")])

    def test_fallback_is_unconfirmed_and_reads_jsonc_names(self):
        self._local_reviewers(
            ("builtin", "opencode", "opencode/free-y"),
            ("mine", "opencode", "mine/m"),
        )
        self.listed_rc = 1
        _write(
            os.path.join(self.env["XDG_CONFIG_HOME"], "opencode", "opencode.jsonc"),
            '{\n  // user providers\n  "provider": {\n'
            '    "mine": {"name": "a \\"//\\" b", /* block */ },\n  },\n}\n',
        )
        _write(
            os.path.join(self.proj, ".opencode", "opencode.json"),
            '{"providers": {"mine2": {}}}',
        )
        lines = self._report()
        self.assertIn(
            "served providers: config file only; login and environment providers not checked"
            " (mine, mine2)",
            lines,
        )
        self.assertIn(
            f'warning: "opencode" is referenced in {self.local}: builtin model=opencode/free-y'
            + UNCONFIRMED,
            lines,
        )
        self.assertFalse([line for line in lines if '"mine"' in line])

    def test_opencode_config_dir_env_is_read(self):
        self.listed_rc = 1
        self.env["OPENCODE_CONFIG_DIR"] = os.path.join(self.root, "oc")
        _write(os.path.join(self.root, "oc", "opencode.json"), '{"provider": {"x1": {}}}')
        self.assertIn(
            "served providers: config file only; login and environment providers not checked (x1)",
            self._report(),
        )

    def test_neither_listing_nor_config_is_not_checked(self):
        self.binary = False
        self.assertIn(
            "served providers: not checked: opencode not installed and no opencode config file",
            self._report(),
        )
        self.binary = True
        self.listed_rc = 1
        self.assertIn(
            "served providers: not checked: opencode models failed and no opencode config file",
            self._report(),
        )

    def test_secret_values_and_auth_file_are_never_read_or_printed(self):
        self._local_reviewers(("g", "opencode", "gone/m"))
        self.listed_rc = 1
        _write(
            os.path.join(self.env["XDG_CONFIG_HOME"], "opencode", "opencode.json"),
            '{"apiKey": "SECRET-MARKER-1", "provider": {"mine": {"apiKey": "SECRET-MARKER-1"}}}',
        )
        _write(os.path.join(self.env["XDG_DATA_HOME"], "opencode", "auth.json"),
               '{"x": "SECRET-MARKER-2"}')
        out = io.StringIO()
        with mock.patch("builtins.open", wraps=open) as opened, redirect_stdout(out):
            rc = cli.main(["check-providers", "--cwd", self.proj], self._deps())
        self.assertEqual(rc, 0)
        self.assertNotIn("SECRET-MARKER", out.getvalue())
        opened_names = [os.path.basename(str(call.args[0])) for call in opened.call_args_list
                        if call.args]
        self.assertNotIn("auth.json", opened_names)

    def test_empty_state_prints_status_lines_and_no_warning(self):
        _write(self.catalog, "{}")
        lines = self._report()
        self.assertEqual(
            lines,
            [
                f"cross-reference: {self.local} absent",
                f"cross-reference: {self.global_path} absent",
                f"cross-reference: {self.catalog} scanned",
                "served providers: listed by opencode (anthropic, opencode)",
            ],
        )

    def test_non_ascii_provider_id_is_reported_unchanged(self):
        self._local_reviewers(("n", "opencode", "prové/m"))
        self.assertIn(
            f'warning: "prové" is referenced in {self.local}: n model=prové/m', self._report()
        )


class TestSpecConfigStep(unittest.TestCase):
    def test_skill_runs_check_providers_in_both_branches(self):
        with open(SKILL_MD, encoding="utf-8") as handle:
            text = handle.read()
        with open(CHECK_ONLY_MD, encoding="utf-8") as handle:
            check_only = handle.read()
        # setup runs it from SKILL.md; --check-only runs it from the reference SKILL.md links
        self.assertIn("check-providers --cwd", text)
        self.assertIn("check-providers --cwd", check_only)
        self.assertIn("(references/check-only.md)", text)
        self.assertLessEqual(len(text.splitlines()), 500)
        lines = text.splitlines()
        never = lines.index("## NEVER")
        section_end = next(i for i in range(never + 1, len(lines)) if lines[i].startswith("#"))
        auth_lines = [i for i, line in enumerate(lines) if "auth.json" in line]
        self.assertTrue(auth_lines)
        for index in auth_lines:
            self.assertTrue(never < index < section_end, lines[index])

    def test_skill_evals_have_six_cases(self):
        with open(EVALS_JSON, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(len(data["evals"]), 6)


if __name__ == "__main__":
    unittest.main()
