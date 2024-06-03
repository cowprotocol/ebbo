"""
Tests for reference solver surplus test.
"""

import unittest
from src.monitoring_tests.token_imbalances_test import (
    TokenImbalancesTest,
)


class TestTokenImbalances(unittest.TestCase):
    def test_token_imbalances(self) -> None:
        surplus_test = TokenImbalancesTest()
        # # NaiveSolver CoW
        # tx_hash = "0x7800e49eb8e7319894fd2d784a11783d5c01cd64ad9bd4fe107fe69872c0f98e"
        # # Quasimodo slippage
        # tx_hash = "0x43b216f62de0f2807c596fa33b6e94748aecbb6df2cd477c5efdad9d1354fce7"
        # # Barter slippage
        # tx_hash = "0x66d9f24e158a0e23de4cbe6426cc86985a896de19be7a1feae0d93bd0d7008c7"
        # Otex slippage
        tx_hash = "0x4c23102d780d87d523e4ba105dc5a9382ccd80a4b2404228860ae24bdca573c8"
        self.assertTrue(surplus_test.run(tx_hash))


if __name__ == "__main__":
    unittest.main()
