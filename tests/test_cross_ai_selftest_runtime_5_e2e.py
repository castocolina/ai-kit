"""E2E tier: runtime shard 5 of 7 of the runner self-test (tests/cross_ai_selftest.py)."""

import unittest

from tests.cross_ai_selftest import shard_case

RuntimeShard5Test = shard_case("runtime", 5)

if __name__ == "__main__":
    unittest.main()
