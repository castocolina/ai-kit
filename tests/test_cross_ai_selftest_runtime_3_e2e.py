"""E2E tier: runtime shard 3 of 4 of the runner self-test (tests/cross_ai_selftest.py)."""

import unittest

from tests.cross_ai_selftest import shard_case

RuntimeShard3Test = shard_case("runtime", 3)

if __name__ == "__main__":
    unittest.main()
