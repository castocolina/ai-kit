"""Every test module is gated exactly once, through the parallel runner."""
import fnmatch
import importlib.util
import os
import pathlib
import re
import tempfile
import tomllib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
HOOKS = REPO_ROOT / ".pre-commit-config.yaml"
PYPROJECT = REPO_ROOT / "pyproject.toml"
RUNNER = REPO_ROOT / "tools" / "run_unittest_parallel.py"
GENERATOR = REPO_ROOT / "tools" / "gen_test_groups.py"
PYLINT_DISABLE_NAMES = frozenset({
    "too-many-lines",
    "unused-argument",
    "duplicate-code",
    "fixme",
    "too-few-public-methods",
    "missing-module-docstring",
    "missing-class-docstring",
    "missing-function-docstring",
})
PYLINT_DISABLE_CODES = frozenset({"C0114", "C0115", "C0116"})
PYLINT_DESIGN = {
    "max-args": 5,
    "max-positional-arguments": 5,
    "max-locals": 15,
    "max-branches": 12,
    "max-returns": 6,
    "max-statements": 50,
}
SHIPPED_SUBDIRS = ("tools", "skills", "tests")
PRE_WIDEN_RUFF_FILES = (
    r"^((tools|tests)/.*|skills/ai-kit-spec-review/ai-kit-spec-review|"
    r"skills/ai-kit-spec-execute/.*|"
    r"skills/ai-kit-usage-metrics/.*|"
    r"skills/ai-kit-project-rules-agents/.*|skills/ai-kit-project-rules-makefile/.*|"
    r"skills/ai-kit-project-rules-precommit/.*|skills/ai-kit-project-rules-arch/.*|"
    r"skills/ai-kit-project-rules-docker/.*|skills/ai-kit-project-rules-cicd/.*|"
    r"skills/ai-kit-project-rules-all/.*|skills/ai-kit-gsd-curated-config/.*|"
    r"skills/ai-kit-gsd-spec-discuss/.*|skills/_shared/.*)\.py$"
)

TIER_TARGETS = ("test-unit", "test-integration", "e2e-test", "arch-test")
UV_TARGETS = ("test-integration", "e2e-test")
WORKER_RE = re.compile(r"-j\s*\d|--jobs\b|--workers \d|max_workers\s*=\s*\d")


def load_tool(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_runner():
    return load_tool(RUNNER)


def hook_group_names(text: str) -> set[str]:
    """Runner group names passed as `--group NAME`, matched as whole tokens."""
    return set(re.findall(r"--group (\S+)", text))


def modules_in_multiple_groups(groups: dict[str, list[str]]) -> list[str]:
    """Module names assigned to more than one group."""
    seen: dict[str, int] = {}
    for names in groups.values():
        for name in names:
            seen[name] = seen.get(name, 0) + 1
    return sorted(name for name, count in seen.items() if count > 1)


def direct_unittest_lines(text: str) -> list[str]:
    """Lines that invoke unittest directly instead of through the runner."""
    return [line for line in text.splitlines() if "-m unittest" in line]


def hardcoded_worker_counts(text: str) -> list[str]:
    """Lines pinning a worker or core count."""
    return [line for line in text.splitlines() if WORKER_RE.search(line)]


def hook_order_errors(hook_ids: list[str]) -> list[str]:
    """The core unittest hook must precede the wizard hook."""
    if "unittest" not in hook_ids or "unittest-wizard" not in hook_ids:
        return ["missing unittest hook"]
    if hook_ids.index("unittest") > hook_ids.index("unittest-wizard"):
        return ["unittest-wizard precedes unittest"]
    return []


def recipe_lines(makefile: str, target: str) -> list[str]:
    """Recipe lines of one Makefile target, stopping at the next target."""
    lines = makefile.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{target}:"))
    body: list[str] = []
    for line in lines[start + 1:]:
        if line and not line[0].isspace():
            break
        body.append(line)
    return body


def prerequisites(makefile: str, target: str) -> list[str]:
    """Names after the colon on a target's rule line; none for a missing target."""
    return (make_target_line(makefile, target) or "").split(":", 1)[-1].split()


def tier_recipe(makefile: str, target: str) -> str:
    """A tier's recipe lines plus those of its prerequisite targets, joined by newlines."""
    names = [target, *prerequisites(makefile, target)]
    return "\n".join(line for name in names for line in recipe_lines(makefile, name))


def multi_line_recipes(makefile: str, targets: tuple[str, ...]) -> list[str]:
    """Targets (and their prerequisites) whose recipe holds more than one command: under `make -k`
    a failing command skips the rest of its recipe."""
    found = []
    for target in targets:
        for name in (target, *prerequisites(makefile, target)):
            if len([line for line in recipe_lines(makefile, name) if line.strip()]) > 1:
                found.append(name)
    return sorted(set(found))


def hook_entries(text: str) -> dict[str, str]:
    """Map each hook id to its `entry:` line."""
    entries: dict[str, str] = {}
    current: str | None = None
    for line in text.splitlines():
        id_match = re.match(r"\s*- id: (\S+)", line)
        if id_match:
            current = id_match.group(1)
        elif current and (entry := re.match(r"\s*entry: (.*)", line)):
            entries[current] = entry.group(1)
            current = None
    return entries


def hook_ids(text: str) -> list[str]:
    return re.findall(r"^\s*- id: (\S+)", text, re.MULTILINE)


def iter_py_files(root: pathlib.Path, subdirs: tuple[str, ...]) -> list[str]:
    """Repo-relative paths to every ``.py`` under ``subdirs``."""
    paths: list[str] = []
    for sub in subdirs:
        base = root / sub
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [
                name for name in dirnames
                if name != "__pycache__" and not name.startswith(".")
            ]
            for name in filenames:
                if name.endswith(".py"):
                    rel = pathlib.Path(dirpath, name).relative_to(root)
                    paths.append(rel.as_posix())
    return sorted(paths)


WALK_SKIP_DIRS = frozenset({"__pycache__", "node_modules", "tmp"})


def _has_python_shebang(path: pathlib.Path) -> bool:
    with path.open("rb") as handle:
        first = handle.readline(128)
    return first.startswith(b"#!") and b"python" in first


def ungated_python_assets(root: pathlib.Path) -> list[pathlib.Path]:
    """Python the `.py` hook regexes cannot select: `*.py.txt` copy-me templates and
    extensionless files with a python shebang (B-WR-12)."""
    found: list[pathlib.Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name for name in dirnames
            if name not in WALK_SKIP_DIRS and not name.startswith(".")
        ]
        for name in filenames:
            path = pathlib.Path(dirpath, name)
            if name.endswith(".py.txt") or (
                "." not in name and path.is_file() and _has_python_shebang(path)
            ):
                found.append(path)
    return sorted(found)


def uncompilable(paths: list[pathlib.Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
            errors.append(f"{path}: {exc}")
    return errors


def unselected_files(paths: list[str], regex: str) -> list[str]:
    """Paths the hook ``files:`` regex does not match."""
    pattern = re.compile(regex)
    return sorted(path for path in paths if not pattern.match(path))


def hook_files_regex(text: str, hook_id: str) -> str | None:
    """Return a hook's ``files:`` regex, if present."""
    current: str | None = None
    for line in text.splitlines():
        id_match = re.match(r"\s*- id: (\S+)", line)
        if id_match:
            current = id_match.group(1)
            continue
        if current == hook_id and (files_match := re.match(r"\s*files: (.*)", line)):
            return files_match.group(1).strip()
    return None


def make_target_line(makefile: str, name: str) -> str | None:
    for line in makefile.splitlines():
        if line.startswith(f"{name}:"):
            return line
    return None


def hook_require_serial(text: str, hook_id: str) -> bool | None:
    """Return whether a hook sets ``require_serial: true``."""
    current: str | None = None
    for line in text.splitlines():
        id_match = re.match(r"\s*- id: (\S+)", line)
        if id_match:
            current = id_match.group(1)
            continue
        if current == hook_id and (serial_match := re.match(
            r"\s*require_serial:\s*(true|false)", line
        )):
            return serial_match.group(1) == "true"
    return None


def hook_block(text: str, hook_id: str) -> str | None:
    """The lines of one hook, from its `- id:` line to the next hook; None when absent."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(rf"\s*- id: {hook_id}$", line)),
                 None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"\s*- id: ", lines[i])), len(lines))
    return "\n".join(lines[start:end])


def hook_stage(text: str, hook_id: str) -> str | None:
    """The inside of a hook's `stages: [...]` value, or None when absent."""
    match = re.search(r"^\s*stages: \[(.*)\]\s*$", hook_block(text, hook_id) or "", re.MULTILINE)
    return match.group(1).strip() if match else None


def dogfood_hook_errors(text: str) -> list[str]:
    """What the check-dogfood hook must be: a verbose, always-run, pre-push hook running
    tools/check_dogfood.py, listed after unittest-wizard."""
    block = hook_block(text, "check-dogfood")
    if block is None:
        return ["check-dogfood hook missing"]
    errors = []
    if hook_stage(text, "check-dogfood") != "pre-push":
        errors.append("check-dogfood lacks the pre-push stage")
    for setting in ("pass_filenames: false", "always_run: true", "verbose: true"):
        if not re.search(rf"^\s*{setting}\s*$", block, re.MULTILINE):
            errors.append(f"check-dogfood lacks {setting}")
    if not hook_entries(text).get("check-dogfood", "").startswith("python3 tools/check_dogfood.py"):
        errors.append("check-dogfood entry is not python3 tools/check_dogfood.py")
    ids = hook_ids(text)
    if "unittest-wizard" not in ids or ids.index("check-dogfood") < ids.index("unittest-wizard"):
        errors.append("check-dogfood does not follow unittest-wizard")
    return errors


MAPPER = REPO_ROOT / "tools" / "staged_mapper.py"
# D-03: the files whose change runs the full unit and arch groups. The runner's SHARED_MACHINERY
# must be exactly this set, so removing one entry fails the gate as surely as a stale one does.
REQUIRED_SHARED_MACHINERY = frozenset({
    "tools/run_unittest_parallel.py", "tools/staged_mapper.py", "tools/gen_test_groups.py",
    ".pre-commit-config.yaml", "Makefile", "pyproject.toml", "uv.lock",
})
# SPEC R3's push target for the two test hooks: the commit budget may never exceed it.
PUSH_TARGET_SECS = 60


def _flag_errors(block: str, hook_id: str, settings: tuple[str, ...]) -> list[str]:
    return [
        f"{hook_id} lacks {setting}" for setting in settings
        if not re.search(rf"^\s*{setting}\s*$", block, re.MULTILINE)
    ]


def staged_hook_errors(text: str) -> list[str]:
    """What the staged-tests hook must be: the commit stage's covering-module runner, its stage
    stated (an omitted stages: line runs at every installed hook type), verbose, always-run, with
    no fixed group, between pylint and unittest."""
    block = hook_block(text, "staged-tests")
    if block is None:
        return ["missing staged-tests hook"]
    errors = []
    stage = hook_stage(text, "staged-tests")
    if stage is None:
        errors.append("staged-tests has no stages: line, so an omitted stage runs at every "
                      "installed hook type")
    elif stage != "pre-commit":
        errors.append(f"staged-tests stages are [{stage}], not [pre-commit]")
    entry = hook_entries(text).get("staged-tests", "")
    if not entry.startswith("python3 tools/run_unittest_parallel.py --staged"):
        errors.append("staged-tests entry is not python3 tools/run_unittest_parallel.py --staged")
    if "--group" in entry:
        errors.append("staged-tests entry names a --group")
    errors += _flag_errors(block, "staged-tests",
                           ("pass_filenames: false", "always_run: true", "verbose: true"))
    ids = hook_ids(text)
    if not all(name in ids for name in ("pylint", "staged-tests", "unittest")) or not (
            ids.index("pylint") < ids.index("staged-tests") < ids.index("unittest")):
        errors.append("staged-tests does not sit between pylint and unittest")
    return errors


def deferred_hook_errors(text: str) -> list[str]:
    """What the deferred-e2e hook must be: the pre-push runner of the over-budget e2e modules,
    its stage stated, verbose, always-run, no fixed group, after unittest-wizard and
    check-dogfood."""
    block = hook_block(text, "deferred-e2e")
    if block is None:
        return ["missing deferred-e2e hook"]
    errors = []
    stage = hook_stage(text, "deferred-e2e")
    if stage is None:
        errors.append("deferred-e2e has no stages: line, so an omitted stage runs at every "
                      "installed hook type")
    elif stage != "pre-push":
        errors.append(f"deferred-e2e stages are [{stage}], not [pre-push]")
    entry = hook_entries(text).get("deferred-e2e", "")
    if not entry.startswith("python3 tools/run_unittest_parallel.py --pushed"):
        errors.append("deferred-e2e entry is not python3 tools/run_unittest_parallel.py --pushed")
    if "--group" in entry:
        errors.append("deferred-e2e entry names a --group")
    errors += _flag_errors(block, "deferred-e2e",
                           ("pass_filenames: false", "always_run: true", "verbose: true"))
    ids = hook_ids(text)
    earlier = ("unittest-wizard", "check-dogfood")
    if not all(name in ids for name in (*earlier, "deferred-e2e")) or not all(
            ids.index(name) < ids.index("deferred-e2e") for name in earlier):
        errors.append("deferred-e2e does not follow unittest-wizard and check-dogfood")
    return errors


def shared_machinery_errors(names) -> list[str]:
    """SHARED_MACHINERY must be exactly the seven required files: a missing one and an extra one are
    each named. (Staleness, an entry whose file is gone, is the runner's own check.)"""
    listed = set(names)
    missing = sorted(REQUIRED_SHARED_MACHINERY - listed)
    extra = sorted(listed - REQUIRED_SHARED_MACHINERY)
    return ([f"shared machinery lacks {name}" for name in missing]
            + [f"shared machinery has an unexpected entry {name}" for name in extra])


def recorded_secs_errors(table, e2e_modules, budget) -> list[str]:
    """The duration table names only e2e modules, with positive whole seconds, and the commit
    budget is a whole number from 1 to the push target (it may never exceed SPEC R3's target)."""
    errors = []
    for module in sorted(table):
        value = table[module]
        if module not in e2e_modules:
            errors.append(f"E2E_RECORDED_SECS names {module}, which is not an e2e module")
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append(f"E2E_RECORDED_SECS[{module}] is {value!r}, not a positive whole "
                          "number of seconds")
    is_whole = isinstance(budget, int) and not isinstance(budget, bool)
    if not is_whole or not 1 <= budget <= PUSH_TARGET_SECS:
        errors.append(f"COMMIT_E2E_BUDGET_SECS is {budget!r}; it must be a whole number from 1 "
                      f"to {PUSH_TARGET_SECS} (SPEC R3's push target)")
    return errors


def env_matrix_gate_errors(makefile: str, hooks: str) -> list[str]:
    """The six-environment target runs its tool and no gate or hook depends on it (SPEC R7)."""
    if make_target_line(makefile, "test-env-matrix") is None:
        return ["test-env-matrix target is missing"]
    errors = []
    if "tools/env_matrix.py" not in "\n".join(recipe_lines(makefile, "test-env-matrix")):
        errors.append("test-env-matrix does not run tools/env_matrix.py")
    for gate in ("test", "validate"):
        line = make_target_line(makefile, gate) or ""
        if "test-env-matrix" in line.split(":", 1)[-1].split():
            errors.append(f"{gate} depends on test-env-matrix")
    if "tools/env_matrix.py" in hooks or "test-env-matrix" in hooks:
        errors.append("a pre-commit hook runs the six-environment matrix")
    return errors


def pylint_disable_drift(disable_list: list[str]) -> list[str]:
    """Report pylint disables outside the pinned set."""
    errors: list[str] = []
    for entry in disable_list:
        token = entry.strip().strip("'\"")
        if token in PYLINT_DISABLE_NAMES or token in PYLINT_DISABLE_CODES:
            continue
        errors.append(f"unexpected pylint disable: {token}")
    expected = len(PYLINT_DISABLE_NAMES)
    if len(disable_list) != expected:
        errors.append(f"disable count {len(disable_list)} != {expected}")
    return errors


def pylint_design_drift(design: dict[str, int]) -> list[str]:
    errors: list[str] = []
    for key, value in PYLINT_DESIGN.items():
        if design.get(key) != value:
            errors.append(f"{key}: got {design.get(key)!r}, want {value}")
    for key in design:
        if key not in PYLINT_DESIGN:
            errors.append(f"unexpected design key: {key}")
    return errors


def path_under_roots(rel_path: str, roots: list[str]) -> bool:
    return any(
        rel_path == root or rel_path.startswith(f"{root}/")
        for root in roots
    )


def stray_test_modules(tests_dir: pathlib.Path) -> list[str]:
    """Every test_*.py below a subfolder of tests/, which the runner's flat glob never discovers
    (32 SPEC R1). One walk; __pycache__ is skipped; paths are repo-relative and sorted."""
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(tests_dir):
        dirnames[:] = [name for name in dirnames if name != "__pycache__"]
        if pathlib.Path(dirpath) == tests_dir:
            continue
        for name in filenames:
            if fnmatch.fnmatchcase(name, "test_*.py"):
                path = pathlib.Path(dirpath) / name
                found.append(path.relative_to(tests_dir.parent).as_posix())
    return sorted(found)


def lint_config_drift(tool: dict) -> list[str]:
    """Drift in pinned ruff, vulture, pylint basic and pyright settings."""
    errors: list[str] = []
    ruff = tool.get("ruff", {}).get("lint", {})
    select = set(ruff.get("select", []))
    if select != {"E", "F", "W", "I", "UP", "B", "SIM", "RUF"}:
        errors.append(f"ruff select drift: {sorted(select)}")
    ignore = set(ruff.get("ignore", []))
    if ignore != {"RUF001", "RUF002", "RUF003"}:
        errors.append(f"ruff ignore drift: {sorted(ignore)}")
    per_file = ruff.get("per-file-ignores", {})
    tests_ignores = set(per_file.get("tests/*", []))
    if tests_ignores != {"E741", "E731", "E402", "E702", "E401", "RUF012"}:
        errors.append(f"ruff per-file-ignores drift: {sorted(tests_ignores)}")
    vulture = tool.get("vulture", {})
    if vulture.get("min_confidence") != 80:
        errors.append("vulture min_confidence drift")
    names = set(vulture.get("ignore_names", []))
    if names != {"signum", "frame", "offset", "whence"}:
        errors.append(f"vulture ignore_names drift: {sorted(names)}")
    basic = tool.get("pylint", {}).get("basic", {})
    if set(basic.keys()) != {"bad-names", "good-names", "module-rgx"}:
        errors.append(f"pylint basic keys drift: {sorted(basic.keys())}")
    if basic.get("good-names") != ["tomllib"]:
        errors.append("pylint good-names drift")
    pyright = tool.get("pyright", {})
    if pyright.get("pythonVersion") != "3.12":
        errors.append("pyright pythonVersion drift")
    if pyright.get("typeCheckingMode") != "basic":
        errors.append("pyright typeCheckingMode drift")
    return errors


def load_pyproject_tool() -> dict:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)["tool"]


class TestGateScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_runner()
        cls.makefile = MAKEFILE.read_text()
        cls.hooks = HOOKS.read_text()
        cls.groups = cls.runner.group_modules(cls.runner.discover_modules())

    def test_every_module_in_exactly_one_group(self) -> None:
        self.assertEqual(modules_in_multiple_groups(self.groups), [])
        assigned = [name for names in self.groups.values() for name in names]
        self.assertCountEqual(assigned, self.runner.discover_modules())

    def test_no_test_module_in_a_tests_subfolder(self) -> None:
        self.assertEqual(stray_test_modules(REPO_ROOT / "tests"), [])

    def test_tiers_run_through_the_runner(self) -> None:
        for target in TIER_TARGETS:
            recipe = tier_recipe(self.makefile, target)
            self.assertIn("tools/run_unittest_parallel.py --group", recipe, target)
        self.assertEqual(direct_unittest_lines(self.makefile), [])

    def test_uv_tiers_run_under_uv(self) -> None:
        for target in (*UV_TARGETS, "test-unit"):
            recipe = tier_recipe(self.makefile, target)
            self.assertIn("uv run", recipe, target)

    def test_hooks_name_runner_groups(self) -> None:
        entries = hook_entries(self.hooks)
        self.assertTrue(entries["unittest"].startswith(
            "python3 tools/run_unittest_parallel.py --group unit --group arch -- "))
        self.assertTrue(entries["unittest-wizard"].startswith(
            "uv run python tools/run_unittest_parallel.py"
            " --group unit-uv --group integration -- "))
        hooks = self.runner.hook_groups()
        for module in hooks["unittest"]:
            self.assertIn(module, entries["unittest"], module)
        for module in hooks["unittest-wizard"]:
            self.assertIn(module, entries["unittest-wizard"], module)
        # Their Textual tests skip under system python3 (B-WR-03).
        for module in ("tests.test_config_doctor", "tests.test_config_doctor_pty"):
            self.assertIn(module, hooks["unittest-wizard"], module)
            self.assertNotIn(module, hooks["unittest"], module)

    def test_hooks_cover_every_group_except_e2e(self) -> None:
        named = " ".join(hook_entries(self.hooks).values())
        self.assertEqual(hook_group_names(named), set(self.groups) - {"e2e"})
        e2e = tier_recipe(self.makefile, "e2e-test")
        self.assertIn("--group e2e", e2e)

    def test_tier_recipes_run_one_command_each(self) -> None:
        self.assertEqual(multi_line_recipes(self.makefile, TIER_TARGETS), [])
        self.assertIn("bash tests/test_install.sh", tier_recipe(self.makefile, "e2e-test"))

    def test_core_hook_precedes_wizard_hook(self) -> None:
        self.assertEqual(hook_order_errors(hook_ids(self.hooks)), [])

    def test_check_dogfood_hook_gates_push(self) -> None:
        self.assertEqual(dogfood_hook_errors(self.hooks), [])
        self.assertEqual(hook_stage(self.hooks, "check-dogfood"), "pre-push")

    def test_validate_runs_check_dogfood(self) -> None:
        line = make_target_line(self.makefile, "validate")
        self.assertIsNotNone(line)
        self.assertEqual((line or "").split()[-1], "check-dogfood")
        self.assertEqual(
            [part.strip() for part in recipe_lines(self.makefile, "check-dogfood") if part.strip()],
            ["uv run pre-commit run check-dogfood --all-files --hook-stage pre-push"],
        )

    def test_env_matrix_stays_out_of_gates(self) -> None:
        self.assertEqual(env_matrix_gate_errors(self.makefile, self.hooks), [])

    def test_no_hardcoded_worker_counts(self) -> None:
        entries = "\n".join(hook_entries(self.hooks).values())
        self.assertEqual(hardcoded_worker_counts(self.makefile), [])
        self.assertEqual(hardcoded_worker_counts(entries), [])
        self.assertEqual(hardcoded_worker_counts(RUNNER.read_text()), [])
        self.assertEqual(hardcoded_worker_counts(MAPPER.read_text()), [])

    def test_generated_listings_name_every_discovered_module(self) -> None:
        # The listings are a projection of discovery, so gate-registration tests
        # that search the Makefile and the hook config for a module name stay true.
        for text in (self.makefile, self.hooks):
            block = text.split("# BEGIN GENERATED test groups\n", 1)[1]
            block = block.split("# END GENERATED test groups", 1)[0]
            for module in self.runner.discover_modules():
                self.assertIn(module, block, module)
        # Compared in memory: a check must never rewrite the tree it checks.
        generator = load_tool(GENERATOR)
        makefile, hooks = generator.render(self.makefile, self.hooks, generator.groups())
        hint = "stale listing; run: python3 tools/gen_test_groups.py"
        self.assertEqual(makefile, self.makefile, hint)
        self.assertEqual(hooks, self.hooks, hint)

    def test_ruff_selects_every_shipped_py(self) -> None:
        regex = hook_files_regex(self.hooks, "ruff")
        self.assertIsNotNone(regex)
        paths = iter_py_files(REPO_ROOT, SHIPPED_SUBDIRS)
        self.assertGreater(len(paths), 0)
        self.assertEqual(unselected_files(paths, regex or ""), [])

    def test_py_compile_selects_every_shipped_py(self) -> None:
        regex = hook_files_regex(self.hooks, "py-compile")
        self.assertIsNotNone(regex)
        paths = iter_py_files(REPO_ROOT, SHIPPED_SUBDIRS)
        self.assertEqual(unselected_files(paths, regex or ""), [])

    def test_ungated_python_assets_compile(self) -> None:
        # No hook selects these, so this is their only compile gate.
        assets = ungated_python_assets(REPO_ROOT)
        rel = {path.relative_to(REPO_ROOT).as_posix() for path in assets}
        self.assertIn("examples/segments/system_memory", rel)
        self.assertIn("skills/cst-refactor/codemod_template.py.txt", rel)
        self.assertEqual(uncompilable(assets), [])

    def test_make_lint_is_hook_aggregate(self) -> None:
        self.assertEqual(make_target_line(self.makefile, "lint"), "lint: shellcheck py-compile")
        self.assertEqual(recipe_lines(self.makefile, "lint"), [])

    def test_pylint_selects_tools_and_skills_py(self) -> None:
        regex = hook_files_regex(self.hooks, "pylint")
        self.assertIsNotNone(regex)
        paths = iter_py_files(REPO_ROOT, ("tools", "skills"))
        self.assertEqual(unselected_files(paths, regex or ""), [])

    def test_pyright_and_vulture_paths_cover_tree(self) -> None:
        tool = load_pyproject_tool()
        pyright_roots = tool["pyright"]["include"]
        vulture_roots = tool["vulture"]["paths"]
        for sub in SHIPPED_SUBDIRS:
            self.assertTrue(
                any(r == sub or r.startswith(f"{sub}/") for r in pyright_roots),
                f"pyright missing {sub}",
            )
            self.assertTrue(
                any(r == sub or r.startswith(f"{sub}/") for r in vulture_roots),
                f"vulture missing {sub}",
            )
        paths = iter_py_files(REPO_ROOT, SHIPPED_SUBDIRS)
        for path in paths:
            self.assertTrue(path_under_roots(path, pyright_roots), path)
            self.assertTrue(path_under_roots(path, vulture_roots), path)

    def test_pinned_pylint_disable_and_design(self) -> None:
        tool = load_pyproject_tool()
        disable = tool["pylint"]["messages control"]["disable"]
        self.assertEqual(pylint_disable_drift(disable), [])
        design = tool["pylint"]["design"]
        self.assertEqual(pylint_design_drift(design), [])

    def test_staged_hook_is_commit_stage(self) -> None:
        self.assertEqual(staged_hook_errors(self.hooks), [])

    def test_shared_machinery_is_pinned(self) -> None:
        self.assertEqual(shared_machinery_errors(self.runner.SHARED_MACHINERY), [])

    def test_deferred_hook_is_push_stage(self) -> None:
        self.assertEqual(deferred_hook_errors(self.hooks), [])

    def test_commit_budget_is_pinned(self) -> None:
        self.assertEqual(recorded_secs_errors(self.runner.E2E_RECORDED_SECS,
                                              self.runner.E2E_MODULES,
                                              self.runner.COMMIT_E2E_BUDGET_SECS), [])

    def test_hook_order_and_serial_runs(self) -> None:
        ids = hook_ids(self.hooks)
        self.assertLess(ids.index("ruff"), ids.index("pylint"))
        self.assertLess(ids.index("pylint"), ids.index("staged-tests"))
        self.assertLess(ids.index("staged-tests"), ids.index("unittest"))
        self.assertLess(ids.index("pylint"), ids.index("unittest"))
        self.assertLess(ids.index("unittest"), ids.index("unittest-wizard"))
        self.assertTrue(hook_require_serial(self.hooks, "ruff"))
        self.assertTrue(hook_require_serial(self.hooks, "pylint"))

    def test_pylint_files_are_subset_of_ruff(self) -> None:
        ruff_re = hook_files_regex(self.hooks, "ruff")
        pylint_re = hook_files_regex(self.hooks, "pylint")
        self.assertIsNotNone(ruff_re)
        self.assertIsNotNone(pylint_re)
        pylint_paths = iter_py_files(REPO_ROOT, ("tools", "skills"))
        extra = unselected_files(pylint_paths, ruff_re or "")
        self.assertEqual(extra, [])

    def test_lint_config_pinned(self) -> None:
        self.assertEqual(lint_config_drift(load_pyproject_tool()), [])


class TestGateScopeNonVacuity(unittest.TestCase):
    def test_flags_a_module_in_two_groups(self) -> None:
        groups = {"unit": ["tests.test_a"], "arch": ["tests.test_a"]}
        self.assertEqual(modules_in_multiple_groups(groups), ["tests.test_a"])

    def test_flags_a_direct_unittest_recipe(self) -> None:
        text = "test-unit:\n\tpython3 -m unittest tests.test_x\n"
        self.assertEqual(direct_unittest_lines(text), ["\tpython3 -m unittest tests.test_x"])

    def test_flags_a_two_command_tier_recipe(self) -> None:
        self.assertEqual(
            multi_line_recipes("test-unit:\n\tpython3 a\n\tuv run b\n", ("test-unit",)),
            ["test-unit"],
        )
        split = ("test-unit: test-unit-core test-unit-uv\n\ntest-unit-core:\n\tpython3 a\n\n"
                 "test-unit-uv:\n\tuv run b\n")
        self.assertEqual(multi_line_recipes(split, ("test-unit",)), [])

    def test_flags_a_hardcoded_worker_count(self) -> None:
        self.assertEqual(hardcoded_worker_counts("entry: uv run python t.py --workers 8"),
                         ["entry: uv run python t.py --workers 8"])

    def test_flags_spaced_and_short_worker_counts(self) -> None:
        for line in ("max_workers = 12", "make -j8"):
            self.assertEqual(hardcoded_worker_counts(line), [line])

    def test_group_names_are_whole_tokens(self) -> None:
        self.assertEqual(hook_group_names("run.py --group unit-uv"), {"unit-uv"})

    def test_path_under_roots_rejects_a_sibling_prefix(self) -> None:
        self.assertFalse(path_under_roots("toolsx/a.py", ["tools"]))
        self.assertTrue(path_under_roots("tools/a.py", ["tools"]))

    def test_a_nested_test_module_is_named(self) -> None:
        files = {
            "tests/test_top.py": "",
            "tests/skills/demo/test_x.py": "",
            "tests/a/test_b.py": "",
            "tests/fixtures/archived/26/skill-judge/check_verdicts.py.txt": "",
            "tests/fixtures/y/helper.py": "",
            "tests/c/Test_upper.py": "",
            "tests/d/__pycache__/test_cached.py": "",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for rel, text in files.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text, encoding="utf-8")
            self.assertEqual(stray_test_modules(root / "tests"),
                             ["tests/a/test_b.py", "tests/skills/demo/test_x.py"])

    def test_an_empty_tests_tree_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = pathlib.Path(tmp) / "tests"
            tests_dir.mkdir()
            self.assertEqual(stray_test_modules(tests_dir), [])
            (tests_dir / "sub").mkdir()
            (tests_dir / "sub" / "helper.py").write_text("", encoding="utf-8")
            self.assertEqual(stray_test_modules(tests_dir), [])

    def test_stale_generated_listing_is_detected(self) -> None:
        generator = load_tool(GENERATOR)
        makefile = MAKEFILE.read_text()
        stale = makefile.replace("# arch: tests.test_arch", "# arch:", 1)
        self.assertNotEqual(stale, makefile)
        rendered, _ = generator.render(stale, HOOKS.read_text(), generator.groups())
        self.assertNotEqual(rendered, stale)

    def test_flags_a_dogfood_hook_without_the_push_stage(self) -> None:
        good = HOOKS.read_text()
        self.assertEqual(dogfood_hook_errors(good), [])
        at = good.index("- id: check-dogfood")
        broken = good[:at] + good[at:].replace("stages: [pre-push]", "stages: [pre-commit]")
        self.assertNotEqual(broken, good)
        self.assertIn("check-dogfood lacks the pre-push stage", dogfood_hook_errors(broken))

    def test_flags_a_dogfood_hook_without_verbose(self) -> None:
        good = HOOKS.read_text()
        at = good.index("- id: check-dogfood")
        broken = good[:at] + good[at:].replace("verbose: true", "verbose: false")
        self.assertNotEqual(broken, good)
        self.assertIn("check-dogfood lacks verbose: true", dogfood_hook_errors(broken))

    def test_flags_wizard_hook_first(self) -> None:
        self.assertEqual(hook_order_errors(["unittest-wizard", "unittest"]),
                         ["unittest-wizard precedes unittest"])

    def test_narrow_regex_misses_unlisted_skill_py(self) -> None:
        path = "skills/ai-kit-spec-review/ai_kit_spec/cli.py"
        self.assertEqual(unselected_files([path], PRE_WIDEN_RUFF_FILES), [path])

    def test_skill_dir_without_py_is_fine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "skills" / "empty-skill").mkdir(parents=True)
            paths = iter_py_files(root, SHIPPED_SUBDIRS)
            self.assertEqual(paths, [])
            wide = r"^(tools|skills|tests)/.*\.py$"
            self.assertEqual(unselected_files(paths, wide), [])

    def test_broken_ungated_python_asset_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "examples").mkdir()
            (root / "examples" / "seg").write_text("#!/usr/bin/env python3\ndef (:\n")
            (root / "examples" / "notes").write_text("#!/bin/sh\necho hi\n")
            (root / "tpl.py.txt").write_text("x = (\n")
            assets = ungated_python_assets(root)
            self.assertEqual([path.name for path in assets], ["seg", "tpl.py.txt"])
            self.assertEqual(len(uncompilable(assets)), 2)

    def test_extra_pylint_disable_reported(self) -> None:
        drift = pylint_disable_drift([*PYLINT_DISABLE_NAMES, "broad-except"])
        self.assertTrue(any("broad-except" in err for err in drift))

    def test_raised_design_threshold_reported(self) -> None:
        design = dict(PYLINT_DESIGN)
        design["max-args"] = 99
        self.assertTrue(pylint_design_drift(design))

    def test_lint_config_drift_on_extra_ruff_ignore(self) -> None:
        tool = load_pyproject_tool()
        bad = {**tool, "ruff": {**tool["ruff"], "lint": {
            **tool["ruff"]["lint"],
            "ignore": [*tool["ruff"]["lint"]["ignore"], "E999"],
        }}}
        self.assertTrue(lint_config_drift(bad))

    def test_lint_config_drift_on_extra_vulture_name(self) -> None:
        tool = load_pyproject_tool()
        bad = {**tool, "vulture": {
            **tool["vulture"],
            "ignore_names": [*tool["vulture"]["ignore_names"], "unused"],
        }}
        self.assertTrue(lint_config_drift(bad))

    def test_lint_config_drift_on_extra_pylint_basic_key(self) -> None:
        tool = load_pyproject_tool()
        bad = {**tool, "pylint": {**tool["pylint"], "basic": {
            **tool["pylint"]["basic"],
            "extra-key": "x",
        }}}
        self.assertTrue(lint_config_drift(bad))

    @staticmethod
    def _without(text: str, hook_id: str, old: str, new: str = "") -> str:
        """`text` with the first `old` in the hook's own block replaced, from its id on"""
        at = text.index(f"- id: {hook_id}\n")
        return text[:at] + text[at:].replace(old, new, 1)

    def test_flags_a_staged_hook_without_a_stage(self) -> None:
        good = HOOKS.read_text()
        self.assertEqual(staged_hook_errors(good), [])
        broken = self._without(good, "staged-tests", "        stages: [pre-commit]\n")
        self.assertNotEqual(broken, good)
        errors = staged_hook_errors(broken)
        self.assertTrue(any("omitted stage runs at every installed hook type" in e for e in errors),
                        errors)

    def test_flags_a_staged_hook_with_a_push_stage(self) -> None:
        good = HOOKS.read_text()
        for stages in ("[pre-push]", "[pre-commit, pre-push]"):
            broken = self._without(good, "staged-tests", "stages: [pre-commit]",
                                   f"stages: {stages}")
            self.assertIn(f"staged-tests stages are [{stages[1:-1]}], not [pre-commit]",
                          staged_hook_errors(broken), stages)

    def test_flags_a_staged_hook_without_verbose(self) -> None:
        good = HOOKS.read_text()
        broken = self._without(good, "staged-tests", "verbose: true", "verbose: false")
        self.assertIn("staged-tests lacks verbose: true", staged_hook_errors(broken))

    def test_flags_a_staged_hook_with_a_group(self) -> None:
        good = HOOKS.read_text()
        broken = self._without(good, "staged-tests", "--staged", "--staged --group unit")
        self.assertIn("staged-tests entry names a --group", staged_hook_errors(broken))

    def test_flags_a_missing_staged_hook(self) -> None:
        good = HOOKS.read_text()
        without = good.replace("- id: staged-tests", "- id: staged-tests-gone")
        self.assertEqual(staged_hook_errors(without), ["missing staged-tests hook"])

    def test_flags_a_staged_hook_out_of_order(self) -> None:
        good = HOOKS.read_text()
        block = hook_block(good, "staged-tests")
        assert block is not None  # the good hooks file always carries staged-tests
        without = good.replace(block + "\n", "", 1)
        moved = without.replace("      - id: pylint\n", block + "\n      - id: pylint\n", 1)
        self.assertNotEqual(moved, good)
        self.assertIn("staged-tests does not sit between pylint and unittest",
                      staged_hook_errors(moved))

    def test_flags_a_shared_machinery_entry_removed_or_added(self) -> None:
        self.assertEqual(shared_machinery_errors(REQUIRED_SHARED_MACHINERY), [])
        for entry in sorted(REQUIRED_SHARED_MACHINERY):
            short = REQUIRED_SHARED_MACHINERY - {entry}
            self.assertEqual(shared_machinery_errors(short),
                             [f"shared machinery lacks {entry}"], entry)
        extra = REQUIRED_SHARED_MACHINERY | {"tools/other.py"}
        self.assertEqual(shared_machinery_errors(extra),
                         ["shared machinery has an unexpected entry tools/other.py"])

    def test_flags_a_deferred_hook_without_a_stage_or_at_pre_commit(self) -> None:
        good = HOOKS.read_text()
        self.assertEqual(deferred_hook_errors(good), [])
        bare = self._without(good, "deferred-e2e", "        stages: [pre-push]\n")
        self.assertTrue(any("omitted stage runs at every installed hook type" in e
                            for e in deferred_hook_errors(bare)))
        commit = self._without(good, "deferred-e2e", "stages: [pre-push]",
                               "stages: [pre-commit]")
        self.assertIn("deferred-e2e stages are [pre-commit], not [pre-push]",
                      deferred_hook_errors(commit))

    def test_flags_a_deferred_hook_without_verbose_or_with_a_group(self) -> None:
        good = HOOKS.read_text()
        quiet = self._without(good, "deferred-e2e", "verbose: true", "verbose: false")
        self.assertIn("deferred-e2e lacks verbose: true", deferred_hook_errors(quiet))
        grouped = self._without(good, "deferred-e2e", "--pushed", "--pushed --group e2e")
        self.assertIn("deferred-e2e entry names a --group", deferred_hook_errors(grouped))

    def test_flags_a_deferred_hook_placed_before_the_wizard_hook(self) -> None:
        good = HOOKS.read_text()
        at = good.index("- id: deferred-e2e")
        head, tail = good[:at], good[at:]
        wizard = head.index("      - id: unittest-wizard\n")
        early = head[:wizard] + "      " + tail + head[wizard:]
        self.assertNotEqual(early, good)
        self.assertIn("deferred-e2e does not follow unittest-wizard and check-dogfood",
                      deferred_hook_errors(early))

    def test_flags_a_missing_deferred_hook(self) -> None:
        good = HOOKS.read_text()
        without = good.replace("- id: deferred-e2e", "- id: deferred-e2e-gone")
        self.assertEqual(deferred_hook_errors(without), ["missing deferred-e2e hook"])

    def test_flags_a_recorded_table_entry_outside_the_e2e_set_or_not_positive(self) -> None:
        modules = frozenset({"tests.test_a_e2e"})
        self.assertEqual(recorded_secs_errors({"tests.test_a_e2e": 3}, modules, 60), [])
        self.assertIn("E2E_RECORDED_SECS names tests.test_stray, which is not an e2e module",
                      recorded_secs_errors({"tests.test_stray": 3}, modules, 60))
        for bad in (0, 1.5, "3", True):
            with self.subTest(value=bad):
                self.assertTrue(recorded_secs_errors({"tests.test_a_e2e": bad}, modules, 60))

    def test_flags_a_commit_budget_above_the_push_target(self) -> None:
        modules = frozenset()
        self.assertEqual(recorded_secs_errors({}, modules, 60), [])
        for bad in (61, 0, 60.0):
            with self.subTest(budget=bad):
                self.assertTrue(recorded_secs_errors({}, modules, bad))

    def test_flags_env_matrix_under_validate_or_in_a_hook(self) -> None:
        makefile = ("test-env-matrix:\n\tpython3 tools/env_matrix.py\n"
                    "validate: ruff test-env-matrix\n")
        self.assertIn("validate depends on test-env-matrix",
                      env_matrix_gate_errors(makefile, ""))
        self.assertIn("a pre-commit hook runs the six-environment matrix",
                      env_matrix_gate_errors(makefile.replace("validate: ruff test-env-matrix",
                                                              "validate: ruff"),
                                             "entry: python3 tools/env_matrix.py"))
        self.assertEqual(env_matrix_gate_errors(
            makefile.replace("validate: ruff test-env-matrix", "validate: ruff"), ""), [])


if __name__ == "__main__":
    unittest.main()
