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

from ai_kit_spec import cli, config_io, config_migrate

SKILL_MD = os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-config", "SKILL.md")
CLI_MODEL_SELECTION_MD = os.path.join(
    _REPO_ROOT, "skills", "ai-kit-spec-config", "references", "cli-model-selection.md"
)
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
        self.local = os.path.join(self.proj, ".aikit", "config.toml")
        self.global_path = os.path.join(self.env["XDG_CONFIG_HOME"], "ai-kit", "config.toml")
        self.catalog = os.path.join(
            self.env["XDG_CACHE_HOME"], "ai-kit", "spec", "model-catalog.json"
        )
        self.listing = "anthropic/claude-x\nopencode/free-y\n"
        self.listed_rc = 0
        self.binary = True

    def _trust(self, path):
        self.assertEqual(path, self.local)
        config_io.cfg_trust_project(self.proj, self.env)

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
        return f'[[lanes.review]]\nkey = "{key}"\nruntime = "opencode"\nmodel = "{model}"\n'

    def _local_reviewers(self, *reviewers):
        text = "".join(
            f'[[lanes.review]]\nkey = "{key}"\nruntime = "{runtime}"\nmodel = "{model}"\n'
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
        _write(self.local, '[lanes]\nstrategy = "local-only"\n')
        self._trust(self.local)
        _write(self.global_path, self._opencode_reviewer("g", "gone/m"))
        lines = self._report()
        self.assertIn(f"cross-reference: {self.global_path} scanned-inactive", lines)
        self.assertIn(
            f'warning: "gone" is referenced in {self.global_path}: g model=gone/m'
            ' (not active: project config.toml sets strategy = "local-only")',
            lines,
        )

    def test_untrusted_local_does_not_deactivate_global(self):
        # The lane carries a command, so it is command-bearing and needs trust (D-11); the
        # command-free case is test_command_free_local_only_deactivates_global below.
        _write(
            self.local,
            '[lanes]\nstrategy = "local-only"\n[[lanes.review]]\nkey = "l"\nruntime = "opencode"\n'
            'model = "gone2/m"\ncommand = "codex exec -m {model}"\n',
        )
        _write(self.global_path, self._opencode_reviewer("g", "gone/m"))
        lines = self._report()
        self.assertIn(f"cross-reference: {self.local} scanned-inactive (untrusted)", lines)
        self.assertIn(f"cross-reference: {self.global_path} scanned", lines)
        self.assertIn(
            f'warning: "gone2" is referenced in {self.local}: l model=gone2/m'
            " (not active: project config.toml is not trusted)",
            lines,
        )
        self.assertIn(f'warning: "gone" is referenced in {self.global_path}: g model=gone/m', lines)

    def test_command_free_local_only_deactivates_global_without_trust(self):
        # D-11: a project [lanes] with no command-bearing entry needs no trust, so its
        # local-only strategy applies at once and the user layer is inactive.
        _write(
            self.local,
            '[lanes]\nstrategy = "local-only"\n[[lanes.review]]\nkey = "l"\nruntime = "opencode"\n'
            'model = "gone2/m"\n',
        )
        _write(self.global_path, self._opencode_reviewer("g", "gone/m"))
        lines = self._report()
        self.assertIn(f"cross-reference: {self.local} scanned", lines)
        self.assertIn(f"cross-reference: {self.global_path} scanned-inactive", lines)
        self.assertIn(f'warning: "gone2" is referenced in {self.local}: l model=gone2/m', lines)
        self.assertIn(
            f'warning: "gone" is referenced in {self.global_path}: g model=gone/m'
            ' (not active: project config.toml sets strategy = "local-only")',
            lines,
        )

    def test_pending_legacy_roster_is_reported_and_nothing_is_written(self):
        # check-providers reads a pending old roster read-only: it is reported, never migrated.
        legacy = os.path.join(self.proj, ".aikit", "review-spec.toml")
        _write(legacy, '[[reviewers]]\nkey = "p"\nruntime = "opencode"\nmodel = "gone/m"\n')
        lines = self._report()
        self.assertIn(f"cross-reference: {self.local} scanned (migration pending: {legacy})",
                      lines)
        self.assertIn(f'warning: "gone" is referenced in {legacy}: p model=gone/m', lines)
        self.assertFalse(os.path.exists(self.local))
        self.assertTrue(os.path.exists(legacy))

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

    def test_listing_without_model_lines_is_not_checked(self):
        self._local_reviewers(("g", "opencode", "gone/m"))
        self.listing = "Loading...\n"
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

    def test_skill_evals_have_the_ten_cases(self):
        with open(EVALS_JSON, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(
            [item["id"] for item in data["evals"]],
            [
                "casual-set-up-reviewers",
                "casual-check-only",
                "precise-global-write",
                "precise-stale-opencode-provider-warning",
                "edge-opencode-not-installed-config-fallback",
                "edge-existing-local-config-replace",
                "edge-old-roster-migration-pending",
                "edge-unconfirmed-read-only-asks-before-test",
                "edge-catalog-stale-report-and-usability",
                "edge-router-alias-assumed",
            ],
        )

    def test_write_risk_ask_comes_before_the_live_test(self):
        # Judge loop 33 finding D6: the read_only: unconfirmed ask must precede check-reviewer.
        with open(SKILL_MD, encoding="utf-8") as handle:
            text = handle.read()
        step = text[text.index("#### Step 2.5"):text.index("#### Step 2.6")]
        self.assertLess(step.index("read_only: unconfirmed"), step.index("check-reviewer --key"))

    def test_check_only_asks_write_risk_before_the_probe(self):
        # Judge loop 33 finding D8-1: --check-only asks the same question before probe-quota.
        with open(CHECK_ONLY_MD, encoding="utf-8") as handle:
            text = handle.read()
        probe = text.index("probe-quota --cwd")
        self.assertLess(text.index("read_only: unconfirmed"), probe)
        self.assertLess(text.index("AskUserQuestion"), probe)
        self.assertIn("write-risk probe was declined", text)

    def test_cli_model_selection_keeps_no_shell_state_across_blocks(self):
        # Judge loop 33 r3 finding D8-2: every Bash call is a fresh shell, so no block assigns a
        # variable a later block reads; the two paths are literal values.
        with open(CLI_MODEL_SELECTION_MD, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("## Build and classify", text)
        self.assertIn("caches each source by its own age", text)
        self.assertNotIn("narrowed to the ids chosen", text)

    def test_global_write_eval_and_near_miss_negatives(self):
        # Judge loop 33 r3 findings D7-1 and D7-2.
        with open(EVALS_JSON, encoding="utf-8") as handle:
            case = {c["id"]: c for c in json.load(handle)["evals"]}["precise-global-write"]
        self.assertIn("already has a [lanes] table", case["prompt"])
        self.assertIn("replacement consent", case["assertions"][0])
        queries = os.path.join(os.path.dirname(EVALS_JSON), "trigger-queries.json")
        with open(queries, encoding="utf-8") as handle:
            negatives = [q["query"] for q in json.load(handle) if not q["should_trigger"]]
        for word in ("cross-AI review", "[runner]", "secrets.env", "opencode.jsonc"):
            self.assertTrue(any(word in q for q in negatives), word)

    def test_session_default_purpose_matches_the_writer(self):
        # Judge loop 33 r3 finding D8-3: an absent purpose is filed under review only.
        with open(SKILL_MD, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn("matches both review and execute", text)
        self.assertIn("under `[[lanes.review]]` only (`split_by_purpose`)", text)
        review, execute = config_migrate.split_by_purpose([{"key": "s"}])
        self.assertEqual((len(review), len(execute)), (1, 0))


class TestCheckOnlyProbeSet(_Scratch):
    """Judge loop 33 r3 finding D8-1: the write-risk ask covers exactly the probed keys."""

    def _snippet(self):
        with open(CHECK_ONLY_MD, encoding="utf-8") as handle:
            text = handle.read()
        opener = 'python3 -c "\n'
        start = text.rindex(opener, 0, text.index("probe_keys")) + len(opener)
        body = text[start : text.index('\n"\n', start)]
        review_dir = os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review")
        return body.replace('$(dirname "$TOOLS_PY")', review_dir).replace("$(pwd)", self.proj)

    def test_snippet_lists_the_merged_probe_set(self):
        # a user-layer key reached only through the merge is listed; an uninstalled one is not
        _write(self.global_path, self._opencode_reviewer("g-one", "anthropic/claude-x"))
        _write(
            self.local,
            self._opencode_reviewer("l-one", "opencode/free-y")
            + '[[lanes.review]]\nkey = "cx"\nruntime = "codex"\nmodel = "gpt-x"\n'
            + '[lanes.policy]\nladder = ["g-one", "l-one", "cx"]\n',
        )
        deps = self._deps()
        out = io.StringIO()
        with mock.patch.object(cli, "CliDeps", lambda: deps), redirect_stdout(out):
            exec(compile(self._snippet(), "check-only-snippet", "exec"), {})
        listed = json.loads(out.getvalue())
        self.assertEqual([row["key"] for row in listed], ["g-one", "l-one"])
        self.assertEqual({row["runtime"] for row in listed}, {"opencode"})
        self.assertFalse(any(row["custom"] for row in listed))

    def test_ask_reads_the_probe_set_not_the_raw_read(self):
        with open(CHECK_ONLY_MD, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn("For each listed entry with a `runtime`", text)
        self.assertLess(text.index("probe_keys"), text.index("read_only: unconfirmed"))
        self.assertIn("(from the merged view)", text)


if __name__ == "__main__":
    unittest.main()
