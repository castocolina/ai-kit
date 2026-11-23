"""E2E tier: logic shard 5 of 5 of the runner self-test (tests/cross_ai_selftest.py)."""

import unittest

from tests.cross_ai_selftest import shard_case

LogicShard5Test = shard_case("logic", 5)

if __name__ == "__main__":
    unittest.main()
