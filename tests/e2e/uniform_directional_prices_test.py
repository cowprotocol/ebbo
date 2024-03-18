"""
Tests for combinatorial auction surplus test.
"""

import unittest
from src.monitoring_tests.uniform_directed_prices_test import (
    UniformDirectedPricesTest,
)


class TestCombinatorialAuctionSurplus(unittest.TestCase):
    def test_surplus(self) -> None:
        surplus_test = UniformDirectedPricesTest()
        # Fair prices
        # tx_hash = "0x4c702f9a3e4593a16fed03229cb4d449a48eab5fb92030fc8ba596e78fef8d1c"
        # self.assertTrue(surplus_test.run(tx_hash))
        # Unfair prices
        tx_hash = "0x469ac0d0e430c67c94d26ae202e9e6710396a1968b1a6656be002eb4f2b7af65"
        self.assertTrue(surplus_test.run(tx_hash))


if __name__ == "__main__":
    unittest.main()
