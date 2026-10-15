"""Golden plans for curated config v2 (D-20): shared fixtures, hermetic inventory -> recommend.

Fixtures under ``tests/fixtures/curated_config_v2/`` include trimmed live runtimes/catalog,
gsd-core 1.16 tables from ``query_gsd_tables``, and synthetic pi models (labelled in runtimes).
Regenerate goldens: ``UPDATE_GOLDEN=1 python3 -m unittest tests.test_curated_config_golden``.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import gsd_catalog, host, plan_io, presets, roles
from ai_kit_spec import gsd_tools

from tests.test_ai_kit_gsd_curated_config import _real_node_executable
from tests.test_curated_config_inventory import (
    FakeRun,
    make_gsd_install,
    real_gsd_run,
    run_inventory,
    seed_cache,
)
from tests.test_curated_config_recommend import run_recommend

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "curated_config_v2"
GOLDEN_DIR = FIXTURES / "golden"

MODELS_KEYS_BY_RIGOR = {
    "mvp": {"models.research", "models.verification"},
    "standard": set(),
    "rigorous": {"models.planning", "models.verification"},
}

POLICY = {
    "provider": "generic",
    "budget": "b",
    "high": "h",
    "medium": "m",
    "low": "l",
    "runtime_tiers": {
        "codex": {"opus": {"model": "gpt-5.6-sol", "reasoning_effort": "high"}},
    },
}

GOLDEN_GRID = [(h, r, "adaptive") for h in host.HOSTS for r in presets.RIGORS]
GOLDEN_SPOTS = (("opencode", "standard", "quality"), ("codex", "mvp", "budget"))
ALL_GOLDEN_CASES = [("codex", "standard", "adaptive")]  # task 1; expanded in 17-09 task 2


def golden_basename(host_name: str, rigor: str, profile: str) -> str:
    if (host_name, rigor, profile) == ("opencode", "standard", "quality"):
        return "opencode-standard-quality"
    if (host_name, rigor, profile) == ("codex", "mvp", "budget"):
        return "codex-mvp-budget"
    return f"{host_name}-{rigor}-{profile}"


def load_fixture(name: str) -> dict:
    with open(FIXTURES / name, encoding="utf-8") as handle:
        return json.load(handle)


def _tables_body() -> dict:
    raw = load_fixture("gsd_tables_1_16.json")
    return {k: v for k, v in raw.items() if k != "_meta"}


def _fixture_rejected_keys() -> set[str]:
    body = _tables_body()
    vk = body.get("valid_keys", {})
    return set(vk.get("rejected", []))


def _profile_first_model_profiles(agent_first: dict) -> dict:
    """gsd-core exports agent -> {profile: tier}; recommend expects profile -> {agent: tier}."""
    out: dict[str, dict[str, str]] = {}
    for agent, profs in agent_first.items():
        if not isinstance(profs, dict):
            continue
        for profile, tier in profs.items():
            if isinstance(tier, str):
                out.setdefault(profile, {})[agent] = tier
    return out


def tables_answer(keys: list[str]) -> dict:
    body = _tables_body()
    rejected_set = _fixture_rejected_keys()
    accepted = sorted(k for k in keys if k not in rejected_set)
    rejected = sorted(k for k in keys if k in rejected_set)
    out = dict(body)
    out["model_profiles"] = _profile_first_model_profiles(body["model_profiles"])
    out["valid_keys"] = {"accepted": accepted, "rejected": rejected}
    return out


def build_golden_inventory(
    host_name: str,
    project_config: dict | None = None,
    global_defaults: dict | None = None,
) -> dict:
    with tempfile.TemporaryDirectory() as root:
        project = os.path.join(root, "project")
        home = os.path.join(root, "home")
        gsd_home = os.path.join(root, "gsd_home")
        xdg = os.path.join(root, "xdg")
        os.makedirs(project)
        os.makedirs(os.path.join(project, ".planning"), exist_ok=True)
        with open(os.path.join(project, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write("# agents\n")
        with open(os.path.join(project, "package.json"), "w", encoding="utf-8") as handle:
            json.dump({"dependencies": {"react": "19.0.0"}}, handle)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        config_path = os.path.join(project, ".planning", "config.json")
        if project_config is not None:
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump(project_config, handle)
        if global_defaults is not None:
            os.makedirs(os.path.join(gsd_home, ".gsd"), exist_ok=True)
            with open(os.path.join(gsd_home, ".gsd", "defaults.json"), "w", encoding="utf-8") as fh:
                json.dump(global_defaults, fh)
        seed_cache(xdg, load_fixture("runtimes.json"), load_fixture("model-catalog.json"))
        env = {
            "HOME": home,
            "GSD_HOME": gsd_home,
            "XDG_CACHE_HOME": xdg,
            "PATH": "",
        }
        fake = FakeRun(
            node_stdout=lambda argv: json.dumps(tables_answer(json.loads(argv[6]))),
            config_path_stdout=config_path,
        )
        code, parsed, _err = run_inventory(project, env, fake, "--host", host_name)
        if code != 0 or parsed is None:
            raise AssertionError(f"inventory failed for {host_name}: code={code}")
        text = plan_io.canonical_json(parsed).replace(root, "<scratch>")
        inv = json.loads(text)
        inv["_fake_argv_log"] = fake.argv_log
        return inv


def mask_digest(plan_bytes: bytes) -> bytes:
    plan = json.loads(plan_bytes.decode("utf-8"))
    plan["inventory_digest"] = "<digest>"
    return plan_io.canonical_json(plan).encode("utf-8")


def check_golden(test: unittest.TestCase, name: str, data: bytes) -> None:
    path = GOLDEN_DIR / f"{name}.json"
    regen = (
        "UPDATE_GOLDEN=1 python3 -m unittest tests.test_curated_config_golden -k TestGoldenPlans"
    )
    if os.environ.get("UPDATE_GOLDEN"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return
    test.assertEqual(data, path.read_bytes(), f"Golden drift: regenerate with {regen}")


def real_gsd_paths() -> tuple[gsd_catalog.GsdCorePaths, str] | None:
    node_bin = _real_node_executable()
    if node_bin is None:
        return None
    tools = REPO_ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs"
    if not tools.is_file():
        return None
    version = gsd_tools.gsd_core_version(str(tools))
    if version != "1.16.0":
        return None
    model_catalog = gsd_catalog.resolve_model_catalog_cjs_path(str(tools))
    config_schema = gsd_catalog.resolve_config_schema_cjs_path(str(tools))
    if not model_catalog or not config_schema:
        return None
    paths = gsd_catalog.GsdCorePaths(node_bin, model_catalog, config_schema)
    return paths, version


def resolve_host_candidates(inventory: dict, value) -> list[dict]:
    if value is None:
        return []
    model = value if isinstance(value, str) else value.get("model")
    if not isinstance(model, str):
        return []
    host_name = inventory["host"]
    out: list[dict] = []
    for cand in inventory.get("candidates", []):
        if not cand.get("is_host"):
            continue
        if host_name == "claude":
            alias = roles.claude_alias_for(cand["model"])
            if alias == model or cand["model"] == model:
                out.append(cand)
        elif cand["model"] == model:
            out.append(cand)
    return out


def _strip_fake(inv: dict) -> dict:
    return {k: v for k, v in inv.items() if k != "_fake_argv_log"}


class TestGoldenTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._paths = real_gsd_paths()
        if cls._paths is None:
            raise unittest.SkipTest("no node or gsd-core 1.16.0 in checkout")
        cls.paths, cls.gsd_version = cls._paths
        cls.scratch = tempfile.mkdtemp()
        cls.child_env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": cls.scratch,
            "GSD_HOME": cls.scratch,
        }
        # Store on instance dict via list so unittest does not bind the nested _run fn.
        cls._gsd_runner = [real_gsd_run(cls.child_env, cls.paths.node_bin)]
        cls.project = os.path.join(cls.scratch, "project")
        os.makedirs(cls.project)

    @classmethod
    def tearDownClass(cls):
        import shutil

        shutil.rmtree(cls.scratch, ignore_errors=True)

    def _union_keys(self) -> list[str]:
        keys: set[str] = set()
        for host_name in host.HOSTS:
            keys.update(presets.closed_key_set(host_name))
        return sorted(keys)

    def test_union_keys_match_fixture(self):
        keys = self._union_keys()
        result = gsd_catalog.query_gsd_tables(
            self.paths, self.project, keys, run_fn=self._gsd_runner[0]
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["valid_keys"]["rejected"], [])
        if os.environ.get("UPDATE_GOLDEN"):
            meta = {
                "gsd_core_version": self.gsd_version,
                "keys": "union of presets.closed_key_set over host.HOSTS",
            }
            payload = {**result, "_meta": meta}
            (FIXTURES / "gsd_tables_1_16.json").write_text(
                plan_io.canonical_json(payload) + "\n", encoding="utf-8"
            )
            return
        self.assertEqual(result, _tables_body())

    def test_model_policy_unset_keys_accepted(self):
        flat = presets.flatten_config({"model_policy": POLICY})
        keys = sorted(flat)
        result = gsd_catalog.query_gsd_tables(
            self.paths, self.project, keys, run_fn=self._gsd_runner[0]
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["valid_keys"]["rejected"], [])
        self.assertIn(
            "model_policy.runtime_tiers.codex.opus",
            result["valid_keys"]["accepted"],
        )


class TestGoldenPlans(unittest.TestCase):
    _inventory_by_host: dict[str, dict] = {}

    @classmethod
    def setUpClass(cls):
        if not (FIXTURES / "gsd_tables_1_16.json").is_file():
            raise unittest.SkipTest("gsd_tables_1_16.json fixture missing")
        for host_name in host.HOSTS:
            cls._inventory_by_host[host_name] = build_golden_inventory(host_name)

    def test_build_golden_inventory_codex(self):
        inv = build_golden_inventory("codex")
        text = plan_io.canonical_json(_strip_fake(inv))
        self.assertEqual(inv["host"], "codex")
        self.assertEqual(inv["gsd_core"]["version"], "1.16.0")
        self.assertIn("<scratch>", text)
        for frag in ("/home/", "/Users/", "/tmp/", "/var/"):
            self.assertNotIn(frag, text)
        node_calls = [
            a for a in inv["_fake_argv_log"] if a and a[0] == "node" and len(a) > 6 and a[1] == "-e"
        ]
        self.assertTrue(node_calls)
        keys = json.loads(node_calls[0][6])
        self.assertEqual(keys, sorted(presets.closed_key_set("codex")))

    def test_build_golden_inventory_codex_deterministic(self):
        a = plan_io.canonical_json(_strip_fake(build_golden_inventory("codex")))
        b = plan_io.canonical_json(_strip_fake(build_golden_inventory("codex")))
        self.assertEqual(a, b)

    def test_golden_plans(self):
        for host_name, rigor, profile in ALL_GOLDEN_CASES:
            with self.subTest(host=host_name, rigor=rigor, profile=profile):
                inv = _strip_fake(self._inventory_by_host[host_name])
                code, _plan, plan_bytes, _err = run_recommend(
                    inv,
                    "--profile",
                    profile,
                    "--rigor",
                    rigor,
                )
                self.assertEqual(code, 0, f"{host_name}-{rigor}-{profile}")
                assert plan_bytes is not None
                name = golden_basename(host_name, rigor, profile)
                check_golden(self, name, mask_digest(plan_bytes))


