"""
Tests cost coverage.
"""

import unittest
from src.monitoring_tests.cost_coverage_zero_signed_fee import (
    CostCoverageForZeroSignedFee,
)


class TestCostCoverage(unittest.TestCase):
    def test_costcoverage(self) -> None:
        costcoverage_test = CostCoverageForZeroSignedFee()
        # overcharging
        tx_hash = "0xb96ef0556e7dd5543b9a832ef458c914878112eda9a02f26ba7577a7da1d95bc"
        self.assertTrue(costcoverage_test.run(tx_hash))


if __name__ == "__main__":
    unittest.main()
