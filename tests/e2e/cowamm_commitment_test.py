"""
Tests for CoW AMM commitment test.
"""

import unittest
from src.monitoring_tests.cowamm_commitment_test import (
    CoWAMMCommitmentTest,
    COWAMM_CONSTANT_PRODUCT_ADDRESS,
)


class TestCoWAMMCommitment(unittest.TestCase):
    def test_cowamm_commitment(self) -> None:
        surplus_test = CoWAMMCommitmentTest()
        # using dummy call data which encodes one active CoW AMM
        settlement = {
            "interactions": [
                [
                    {
                        "target": COWAMM_CONSTANT_PRODUCT_ADDRESS,
                        "callData": "0x30f73c99000000000000000000000000beef5afe88ef73337e5070ab2855d37dbf5493a40000000000000000000000000000000000000000000000000000000000000001",
                    }
                ]
            ]
        }
        self.assertTrue(surplus_test.check_commitments(settlement))


if __name__ == "__main__":
    unittest.main()
