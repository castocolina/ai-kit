"""Real gsd-core run for ai-kit-gsd-spec-discuss: the e2e tier (C-IN-06). It spawns real
`node` against the gsd-core edge-probe.cjs that `edge_floor.find_engine` resolves, and skips
when either is missing."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.test_ai_kit_gsd_spec_discuss import SPEC, edge_floor

# The floor this fixture's two requirements produce on the checkout-local engine (WR-07).
# An empty `items` list used to satisfy a subset check and hide a silent engine.
_EXPECTED = {
    ("adjacency", "R1"),
    ("boundary", "R1"),
    ("concurrency", "R2"),
    ("empty", "R1"),
    ("ordering", "R1"),
    ("precision", "R1"),
}


def _spec_with(pairs: set[tuple[str, str]]) -> str:
    """The fixture requirements plus an Edge Coverage table of exactly `pairs`."""
    head, rest = SPEC.split("## Edge Coverage", 1)
    _body, tail = rest.split("## Prohibitions", 1)
    rows = ["| Category | Requirement | Status | Resolution / Reason |",
            "|----------|-------------|--------|---------------------|"]
    rows += [f"| {category} | {requirement} | covered | fixture |"
             for category, requirement in sorted(pairs)]
    return f"{head}## Edge Coverage\n\n" + "\n".join(rows) + f"\n\n## Prohibitions{tail}"


class TestRealEdgeFloor(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node") and edge_floor.find_engine(os.environ, os.getcwd(),
                                                                          None),
                         "node or gsd-core edge-probe.cjs not installed")
    def test_real_engine_floor_and_a_removed_row_drifts(self):
        engine = edge_floor.find_engine(os.environ, os.getcwd(), None)
        assert engine is not None
        floor = edge_floor.run_engine(engine, edge_floor.requirements(SPEC))
        pairs = {(item["category"], item["requirement_id"]) for item in floor["items"]}
        self.assertEqual(pairs, _EXPECTED)
        with tempfile.TemporaryDirectory() as tmp:
            full = Path(tmp) / "09-SPEC.md"
            full.write_text(_spec_with(_EXPECTED))
            self.assertEqual(edge_floor.main(["check", str(full), "--engine", engine],
                                              env=os.environ), 0)
            short = Path(tmp) / "10-SPEC.md"
            short.write_text(_spec_with(_EXPECTED - {("empty", "R1")}))
            self.assertEqual(edge_floor.main(["check", str(short), "--engine", engine],
                                              env=os.environ), 1)


if __name__ == "__main__":
    unittest.main()
