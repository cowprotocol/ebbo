"""
Tests for surplus test.
"""

import unittest
from src.apis.orderbookapi import OrderbookAPI
from src.monitoring_tests.solver_competition_surplus_test import (
    SolverCompetitionSurplusTest,
)


class TestSurplus(unittest.TestCase):
    def test_surplus(self) -> None:
        orderbook_api = OrderbookAPI("mainnet")
        surplus_test = SolverCompetitionSurplusTest(orderbook_api)
        # new competition format: no alert or info
        tx_hash = "0xc140a3adc9debfc00a45cc713afbac1bbe197ad2dd1d7fa5b4a36de1080a3d66"
        self.assertTrue(surplus_test.run(tx_hash))


if __name__ == "__main__":
    unittest.main()
