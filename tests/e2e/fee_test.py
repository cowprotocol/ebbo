"""
Tests for fee test.
"""

import unittest
from src.monitoring_tests.partially_fillable_fee_quote_test import (
    PartialFillFeeQuoteTest,
)
from src.monitoring_tests.partially_fillable_cost_coverage_test import (
    PartialFillCostCoverageTest,
)


class TestFees(unittest.TestCase):
    def test_fee_quote(self):
        fee_test = PartialFillFeeQuoteTest()
        tx_hash = "0xf467a6a01f61fa608c1bc116e2f4f4df1b95461827b1e7700c1d36628875feab"
        self.assertTrue(fee_test.run(tx_hash))
        # buy order:
        tx_hash = "0x8e9f98cabf9b6ff4e001eda5efacfd70590a60bd03a499d8b02130b67b208eb1"
        self.assertTrue(fee_test.run(tx_hash))
        # small executed amount:
        tx_hash = "0xda857a0db563dae564b09febb683fff6150628c1706afc9ebd961c194ca29c5e"
        self.assertTrue(fee_test.run(tx_hash))

    def test_cost_coverage(self):
        fee_test = PartialFillCostCoverageTest()
        tx_hash = "0xf467a6a01f61fa608c1bc116e2f4f4df1b95461827b1e7700c1d36628875feab"
        self.assertTrue(fee_test.run(tx_hash))
        # buy order:
        tx_hash = "0x8e9f98cabf9b6ff4e001eda5efacfd70590a60bd03a499d8b02130b67b208eb1"
        self.assertTrue(fee_test.run(tx_hash))
        # small executed amount:
        tx_hash = "0xda857a0db563dae564b09febb683fff6150628c1706afc9ebd961c194ca29c5e"
        self.assertTrue(fee_test.run(tx_hash))


if __name__ == "__main__":
    unittest.main()
