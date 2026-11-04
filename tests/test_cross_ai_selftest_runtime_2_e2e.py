"""E2E tier: runtime shard 2 of 4 of the runner self-test (tests/cross_ai_selftest.py)."""

import unittest

from tests.cross_ai_selftest import shard_case

RuntimeShard2Test = shard_case("runtime", 2)

if __name__ == "__main__":
    unittest.main()
