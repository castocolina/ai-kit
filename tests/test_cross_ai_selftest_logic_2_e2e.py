"""E2E tier: logic shard 2 of 4 of the runner self-test (tests/cross_ai_selftest.py)."""

import unittest

from tests.cross_ai_selftest import shard_case

LogicShard2Test = shard_case("logic", 2)

if __name__ == "__main__":
    unittest.main()
