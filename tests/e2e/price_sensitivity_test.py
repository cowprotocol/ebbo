"""
Tests for surplus test.
"""

import unittest
from src.apis.orderbookapi import OrderbookAPI
from src.monitoring_tests.price_sensitivity_test import (
    PriceSensitivityTest,
)


class TestPrices(unittest.TestCase):
    def test_prices(self) -> None:
        orderbook_api = OrderbookAPI("mainnet")
        price_sensitivity_test = PriceSensitivityTest(orderbook_api)
        # new competition format: no alert or info
        tx_hash = "0x524b92cfc81e9b590a701bf157ca1b0f21b05d7c37ebb39f332cd215c8db1046"
        self.assertTrue(price_sensitivity_test.run(tx_hash))


if __name__ == "__main__":
    unittest.main()
