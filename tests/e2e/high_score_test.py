"""
Tests for large score test.
"""

import unittest
from src.apis.orderbookapi import OrderbookAPI
from src.monitoring_tests.high_score_test import (
    HighScoreTest,
)


class TestHighScore(unittest.TestCase):
    def test_high_score(self) -> None:
        orderbook_api = OrderbookAPI("mainnet")
        high_score_test = HighScoreTest(orderbook_api)
        # large score tx
        tx_hash = "0x5eef22d04a2f30e62df76614decf43e1cc92ab957285a687f182a0191d85d15a"
        self.assertTrue(high_score_test.run(tx_hash))

        # small score tx
        tx_hash = "0x37e7dbc2f3df5f31f017634d07855933c6d82f4fda033daebd4377987d2b5ae9"
        self.assertTrue(high_score_test.run(tx_hash))


if __name__ == "__main__":
    unittest.main()
