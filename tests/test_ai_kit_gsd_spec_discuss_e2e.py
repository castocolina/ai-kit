"""Real gsd-core run for ai-kit-gsd-spec-discuss: the e2e tier (C-IN-06). It spawns real
`node` against the gsd-core edge-probe.cjs that `edge_floor.find_engine` resolves, and skips
when either is missing."""
import os
import shutil
import unittest

from tests.test_ai_kit_gsd_spec_discuss import SPEC, edge_floor


class TestRealEdgeFloor(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node") and edge_floor.find_engine(os.environ, os.getcwd(),
                                                                          None),
                         "node or gsd-core edge-probe.cjs not installed")
    def test_real_engine_floor(self):
        engine = edge_floor.find_engine(os.environ, os.getcwd(), None)
        assert engine is not None
        floor = edge_floor.run_engine(engine, edge_floor.requirements(SPEC))
        self.assertTrue({i["requirement_id"] for i in floor["items"]} <= {"R1", "R2"})


if __name__ == "__main__":
    unittest.main()
