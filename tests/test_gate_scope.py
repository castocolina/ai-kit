"""Every test module is gated exactly once, through the parallel runner."""
import importlib.util
import pathlib
import re
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
HOOKS = REPO_ROOT / ".pre-commit-config.yaml"
RUNNER = REPO_ROOT / "tools" / "run_unittest_parallel.py"

TIER_TARGETS = ("test-unit", "test-integration", "e2e-test", "arch-test")
UV_TARGETS = ("test-integration", "e2e-test")
WORKER_RE = re.compile(r"-j \d|--jobs\b|--workers \d|max_workers=\d")


def load_runner():
    spec = importlib.util.spec_from_file_location("run_unittest_parallel", RUNNER)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    def test_tiers_run_through_the_runner(self) -> None:
        for target in TIER_TARGETS:
            recipe = "\n".join(recipe_lines(self.makefile, target))
            self.assertIn("tools/run_unittest_parallel.py --group", recipe, target)
        self.assertEqual(direct_unittest_lines(self.makefile), [])

    def test_uv_tiers_run_under_uv(self) -> None:
        for target in (*UV_TARGETS, "test-unit"):
            recipe = "\n".join(recipe_lines(self.makefile, target))
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

    def test_hooks_cover_every_group_except_e2e(self) -> None:
        named = " ".join(hook_entries(self.hooks).values())
        self.assertEqual(
            {name for name in self.groups if f"--group {name}" in named},
            set(self.groups) - {"e2e"},
        )
        e2e = "\n".join(recipe_lines(self.makefile, "e2e-test"))
        self.assertIn("--group e2e", e2e)

    def test_core_hook_precedes_wizard_hook(self) -> None:
        self.assertEqual(hook_order_errors(hook_ids(self.hooks)), [])

    def test_no_hardcoded_worker_counts(self) -> None:
        entries = "\n".join(hook_entries(self.hooks).values())
        self.assertEqual(hardcoded_worker_counts(self.makefile), [])
        self.assertEqual(hardcoded_worker_counts(entries), [])
        self.assertEqual(hardcoded_worker_counts(RUNNER.read_text()), [])

    def test_generated_listings_name_every_discovered_module(self) -> None:
        # The listings are a projection of discovery, so gate-registration tests
        # that search the Makefile and the hook config for a module name stay true.
        for text in (self.makefile, self.hooks):
            block = text.split("# BEGIN GENERATED test groups\n", 1)[1]
            block = block.split("# END GENERATED test groups", 1)[0]
            for module in self.runner.discover_modules():
                self.assertIn(module, block, module)
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "gen_test_groups.py")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(MAKEFILE.read_text(), self.makefile)
        self.assertEqual(HOOKS.read_text(), self.hooks)


class TestGateScopeNonVacuity(unittest.TestCase):
    def test_flags_a_module_in_two_groups(self) -> None:
        groups = {"unit": ["tests.test_a"], "arch": ["tests.test_a"]}
        self.assertEqual(modules_in_multiple_groups(groups), ["tests.test_a"])

    def test_flags_a_direct_unittest_recipe(self) -> None:
        text = "test-unit:\n\tpython3 -m unittest tests.test_x\n"
        self.assertEqual(direct_unittest_lines(text), ["\tpython3 -m unittest tests.test_x"])

    def test_flags_a_hardcoded_worker_count(self) -> None:
        self.assertEqual(hardcoded_worker_counts("entry: uv run python t.py --workers 8"),
                         ["entry: uv run python t.py --workers 8"])

    def test_flags_wizard_hook_first(self) -> None:
        self.assertEqual(hook_order_errors(["unittest-wizard", "unittest"]),
                         ["unittest-wizard precedes unittest"])


if __name__ == "__main__":
    unittest.main()
