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
        # # Baseline EBBO error
        # tx_hash = "0x4115f6f4abaea17f2ebef3a1e75c589c38cac048ff5116d406038e48ff7aeacd"
        # # large settlement with bad execution for one of the orders
        # tx_hash = "0xc22b1e4984b212e679d4af49c1622e7018c83d5e32ece590cf84a3e1950f9f18"
        # # EBBO violations
        # #
        # tx_hash = "0x2ff69424f7bf8951ed5e7dd04b648380b0e73dbf7f0191c800651bc4b16a30c5"
        # # combinatorial auction worse than current auction
        # tx_hash = "0xb743b023ad838f04680fd321bf579c35931c4f886f664bd2b6e675c310a9c287"
        # # combinatorial auction better than current auction
        # tx_hash = "0x46639ae0e516bcad7b052fb6bfb6227d0aa2707e9882dd8d86bab2ab6aeee155"
        # tx_hash = "0xe28b92ba73632d6b167fdb9bbfec10744ce208536901dd43379a6778c4408536"
        # tx_hash = "0xad0ede9fd68481b8ef4722d069598898e01d61427ccb378ca4c82c772c6644e0"
        # tx_hash = "0xead8f01e8e24fdc306fca8fcac5146edc22c27e49a7aad6134adc2ad50ba8581"
        tx_hash = "0x6200e744e5d6f9990271be53840c01044cc19f3a8526190e1eaac0bc5fefed85"
        self.assertTrue(surplus_test.run(tx_hash))


if __name__ == "__main__":
    unittest.main()
