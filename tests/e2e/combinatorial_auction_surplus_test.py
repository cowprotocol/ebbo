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
        # CoW with liquidity order by Naive solver
        tx_hash = "0x6b728195926e033ab92bbe7db51170c582ff57ba841aaaca3a9319cfe34491ff"
        self.assertTrue(surplus_test.run(tx_hash))


if __name__ == "__main__":
    unittest.main()
