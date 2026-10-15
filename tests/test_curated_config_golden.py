"""Golden plans for curated config v2 (D-20): shared fixtures, hermetic inventory -> recommend.

Fixtures under ``tests/fixtures/curated_config_v2/`` include trimmed live runtimes, a catalog
trimmed from models.dev whose scores/tokens_per_sec are synthetic rank-preserving values (not
Artificial Analysis data; labelled in ``_meta.fixture_note``), gsd-core 1.16 tables as the node
query emits them, and synthetic pi models (labelled in runtimes).
Regenerate goldens: ``UPDATE_GOLDEN=1 python3 -m unittest tests.test_curated_config_golden``.
"""
from __future__ import annotations

import json
import os
import re
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
# Any absolute POSIX path (a "/" + letter right after a quote, space or bracket) or a
# Windows drive path: replaces a fixed /home//tmp/... fragment list (C-IN-08).
ABSOLUTE_PATH = re.compile(r"""(?:^|[\s"'(=,\[])/[A-Za-z]|\b[A-Za-z]:(?:\\\\|/)""", re.M)
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
ALL_GOLDEN_CASES = [*GOLDEN_GRID, *GOLDEN_SPOTS]


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


def tables_answer(keys: list[str]) -> dict:
    body = _tables_body()
    rejected_set = _fixture_rejected_keys()
    accepted = sorted(k for k in keys if k not in rejected_set)
    rejected = sorted(k for k in keys if k in rejected_set)
    out = dict(body)
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
    """Goldens pin plan content only: an unmasked digest would churn all 17 goldens on any
    inventory field change. The inventory -> digest link is pinned instead by
    test_curated_config_recommend (plan digest == plan_schema.inventory_digest(inv), and
    its candidate-order independence)."""
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
        # Loud, not silent: an UPDATE_GOLDEN left exported must never pass as green.
        test.skipTest(f"UPDATE_GOLDEN set: rewrote {path.name}; assertion skipped")
    test.assertEqual(data, path.read_bytes(), f"Golden drift: regenerate with {regen}")


def real_gsd_paths() -> tuple[gsd_catalog.GsdCorePaths, str] | str:
    """The checkout-local gsd-core 1.16.0 paths, or the reason they are unusable."""
    node_bin = _real_node_executable()
    if node_bin is None:
        return "no node executable"
    tools = REPO_ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs"
    if not tools.is_file():
        return "no checkout-local .claude/gsd-core"
    version = gsd_tools.gsd_core_version(str(tools))
    if version != "1.16.0":
        return f"checkout-local gsd-core is {version}; gsd_tables_1_16.json pins 1.16.0"
    model_catalog = gsd_catalog.resolve_model_catalog_cjs_path(str(tools))
    config_schema = gsd_catalog.resolve_config_schema_cjs_path(str(tools))
    if not model_catalog or not config_schema:
        return "gsd-core lib/model-catalog.cjs or lib/config-schema.cjs missing"
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
        if isinstance(cls._paths, str):
            raise unittest.SkipTest(f"fixture not re-validated: {cls._paths}")
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
        raw_stdout: list[str] = []

        def capture(cmd, **kw):
            res = self._gsd_runner[0](cmd, **kw)
            raw_stdout.append(res.stdout)
            return res

        result = gsd_catalog.query_gsd_tables(self.paths, self.project, keys, run_fn=capture)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["valid_keys"]["rejected"], [])
        raw_profiles = json.loads(raw_stdout[-1])["model_profiles"]
        if os.environ.get("UPDATE_GOLDEN"):
            meta = {
                "gsd_core_version": self.gsd_version,
                "keys": "union of presets.closed_key_set over host.HOSTS",
            }
            # The fixture stores gsd-core's raw agent-first MODEL_PROFILES (the node output).
            payload = {**result, "model_profiles": raw_profiles, "_meta": meta}
            (FIXTURES / "gsd_tables_1_16.json").write_text(
                plan_io.canonical_json(payload) + "\n", encoding="utf-8"
            )
            self.skipTest("UPDATE_GOLDEN set: rewrote gsd_tables_1_16.json; assertion skipped")
        body = _tables_body()
        self.assertEqual(raw_profiles, body["model_profiles"])
        expected = {**body, "model_profiles": gsd_catalog.profile_first(body["model_profiles"])}
        self.assertEqual(result, expected)

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


class TestFixtureShape(unittest.TestCase):
    def test_catalog_scores_are_marked_synthetic(self):
        """C-IN-08: no Artificial Analysis data is redistributed in the fixture."""
        note = load_fixture("model-catalog.json")["_meta"]["fixture_note"]
        self.assertTrue(note.startswith("synthetic:"))

    def test_fixture_model_profiles_are_agent_first(self):
        """The fake node answers with gsd-core's raw shape, so goldens run the real parse."""
        profiles = _tables_body()["model_profiles"]
        self.assertIn("gsd-planner", profiles)
        self.assertIn("adaptive", profiles["gsd-planner"])


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
        self.assertIsNone(ABSOLUTE_PATH.search(text))
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

class TestGoldenProperties(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not GOLDEN_DIR.is_dir():
            raise unittest.SkipTest("no golden dir")
        cls._inventory_by_host = {
            h: _strip_fake(build_golden_inventory(h)) for h in host.HOSTS
        }

    def _load_golden(self, basename: str) -> dict:
        with open(GOLDEN_DIR / f"{basename}.json", encoding="utf-8") as handle:
            return json.load(handle)

    def test_golden_files_count(self):
        self.assertEqual(len(list(GOLDEN_DIR.glob("*.json"))), 17)

    def test_properties_per_golden(self):
        for host_name, rigor, profile in ALL_GOLDEN_CASES:
            with self.subTest(host=host_name, rigor=rigor, profile=profile):
                basename = golden_basename(host_name, rigor, profile)
                plan = self._load_golden(basename)
                inv = self._inventory_by_host[host_name]
                entries = plan["entries"]
                model_keys = {e["key"] for e in entries if e["key"].startswith("models.")}
                self.assertEqual(model_keys, MODELS_KEYS_BY_RIGOR[rigor])
                set_overrides = [
                    e
                    for e in entries
                    if e["key"].startswith("model_overrides.") and e.get("op") == "set"
                ]
                self.assertLessEqual(len(set_overrides), 7)
                self.assertFalse(any(e.get("op") == "unset" for e in entries))
                for entry in entries:
                    if entry.get("source") != "catalog-score":
                        continue
                    matches = resolve_host_candidates(inv, entry.get("value"))
                    self.assertTrue(matches)
                    self.assertTrue(any(m.get("score_axes", 0) > 0 for m in matches))
                for entry in entries:
                    if entry.get("op") != "set":
                        continue
                    if not (
                        entry["key"].startswith("model_overrides.")
                        or entry["key"].startswith("model_profile_overrides.")
                    ):
                        continue
                    matches = resolve_host_candidates(inv, entry.get("value"))
                    if not matches:
                        continue
                    self.assertFalse(any(m.get("fast_twin_of") for m in matches))
                if host_name == "codex" and rigor == "standard" and profile == "adaptive":
                    keeps = [
                        e
                        for e in entries
                        if e["key"].startswith("model_profile_overrides.codex.")
                    ]
                    self.assertTrue(keeps)
                    self.assertTrue(all(e.get("op") == "keep" for e in keeps))
                if host_name == "opencode":
                    for entry in entries:
                        if entry.get("op") != "set":
                            continue
                        val = entry.get("value")
                        if isinstance(val, str) and val.startswith("anthropic/"):
                            self.fail(f"anthropic set on opencode: {entry['key']}")
                    routers = [
                        e
                        for e in entries
                        if e.get("source") == "router-declared"
                        and e.get("value") == "router-env/my-coding"
                    ]
                    self.assertTrue(routers)
                    self.assertFalse(
                        any(e.get("value") == "router-env/my-plan-review" for e in entries)
                    )
                if host_name == "cursor":
                    self.assertFalse(any(e.get("op") == "keep" for e in entries))
                    haiku = next(
                        (
                            e
                            for e in entries
                            if e["key"] == "model_profile_overrides.cursor.haiku"
                            and e.get("op") == "set"
                        ),
                        None,
                    )
                    if haiku is not None:
                        val = haiku.get("value")
                        model = val if isinstance(val, str) else val.get("model", "")
                        self.assertFalse(str(model).endswith("-max"))
                        self.assertFalse(str(model).endswith("-xhigh"))
                if host_name in ("claude", "codex"):
                    self.assertTrue(
                        any(n.get("kind") == "counterpart" for n in plan.get("notes", []))
                    )
                if host_name == "claude":
                    self.assertFalse(
                        any(
                            e["key"].startswith("model_profile_overrides.")
                            and e.get("op") == "set"
                            for e in entries
                        )
                    )
                if host_name == "pi":
                    self.assertFalse(
                        any(e["key"].startswith("model_overrides.") for e in entries)
                    )
                    sonnet = next(
                        e for e in entries if e["key"] == "model_profile_overrides.pi.sonnet"
                    )
                    self.assertEqual(sonnet.get("status"), "needs_choice")
                    self.assertEqual(sonnet.get("candidates"), [])


class TestConflictsEndToEnd(unittest.TestCase):
    def _entry(self, plan: dict, key: str) -> dict:
        for entry in plan["entries"]:
            if entry["key"] == key:
                return entry
        raise AssertionError(key)

    def test_project_config_unsets(self):
        inv = _strip_fake(
            build_golden_inventory(
                "claude",
                project_config={
                    "model_policy": {"provider": "generic", "high": "x"},
                    "resolve_model_ids": "omit",
                },
            )
        )
        kinds = {(c["kind"], c["scope"]) for c in inv["conflicts"]}
        self.assertIn(("model_policy", "project"), kinds)
        self.assertIn(("resolve_model_ids", "project"), kinds)
        code, plan, _bytes, _err = run_recommend(
            inv, "--profile", "adaptive", "--rigor", "standard"
        )
        self.assertEqual(code, 0)
        assert plan is not None
        high = self._entry(plan, "model_policy.high")
        self.assertEqual(high["op"], "unset")
        self.assertIn("unset per leaf", high.get("why", ""))
        provider = self._entry(plan, "model_policy.provider")
        self.assertEqual(provider["op"], "unset")
        resolve = self._entry(plan, "resolve_model_ids")
        self.assertEqual(resolve["op"], "unset")
        self.assertEqual(resolve.get("existing"), "omit")

    def test_global_defaults_latent_unsets(self):
        inv = _strip_fake(
            build_golden_inventory(
                "claude",
                global_defaults={
                    "resolve_model_ids": "omit",
                    "model_policy": {"provider": "generic"},
                },
            )
        )
        code, plan, _bytes, _err = run_recommend(
            inv, "--profile", "adaptive", "--rigor", "standard"
        )
        self.assertEqual(code, 0)
        assert plan is not None
        latent = "latent (copied into the project config by config-new-project)"
        resolve = self._entry(plan, "resolve_model_ids")
        self.assertEqual(resolve["op"], "unset")
        self.assertEqual(resolve.get("effect"), latent)
        provider = self._entry(plan, "model_policy.provider")
        self.assertEqual(provider["op"], "unset")
        self.assertEqual(provider.get("effect"), latent)
        dropped = [n for n in plan.get("notes", []) if n.get("kind") == "dropped_key"]
        dropped_keys = {n.get("key") for n in dropped}
        for key in ("resolve_model_ids", "model_policy.provider", "model_policy.high"):
            self.assertNotIn(key, dropped_keys)


class TestFixtureHygiene(unittest.TestCase):
    def test_no_absolute_paths_in_fixtures(self):
        tmpdir = tempfile.gettempdir()
        for path in FIXTURES.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(ABSOLUTE_PATH.search(text), f"{path} has an absolute path")
            self.assertNotIn(tmpdir, text, f"{path} contains tempfile.gettempdir()")

    def test_absolute_path_pattern_catches_posix_and_windows(self):
        for bad in ('"/opt/x"', '"at /usr/lib"', '"C:\\\\Users"', '"[/mnt/d]"', '"D:/x"'):
            self.assertIsNotNone(ABSOLUTE_PATH.search(bad), bad)
        for ok in ('"openai/gpt-5.6-sol"', '"<scratch>/.planning"', '"<= 4/1M"'):
            self.assertIsNone(ABSOLUTE_PATH.search(ok), ok)


if __name__ == "__main__":
    unittest.main()
