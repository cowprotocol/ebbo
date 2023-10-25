"""
Tests for combinatorial auction surplus test.
"""

import unittest
from src.monitoring_tests.combinatorial_auction_surplus_test import (
    CombinatorialAuctionSurplusTest,
)


class TestCombinatorialAuctionSurplus(unittest.TestCase):
    def test_surplus(self) -> None:
        surplus_test = CombinatorialAuctionSurplusTest()
        # Baseline EBBO error
        # tx_hash = "0x4115f6f4abaea17f2ebef3a1e75c589c38cac048ff5116d406038e48ff7aeacd"
        # large settlement with bad execution for one of the orders
        tx_hash = "0xc22b1e4984b212e679d4af49c1622e7018c83d5e32ece590cf84a3e1950f9f18"
        self.assertTrue(surplus_test.run(tx_hash))


if __name__ == "__main__":
    unittest.main()
