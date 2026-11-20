"""Phase 35 stub; plan 35-02 replaces this body."""

import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))


class TestHardcodedModels(unittest.TestCase):
    def test_stub(self):
        self.skipTest("filled by plan 35-02")


if __name__ == "__main__":
    unittest.main()
