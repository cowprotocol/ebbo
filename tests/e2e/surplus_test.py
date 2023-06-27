"""
Tests for surplus test.
"""

import unittest
from src.monitoring_tests.solver_competition_surplus_test import (
    SolverCompetitionSurplusTest,
)


class TestSurplus(unittest.TestCase):
    def test_surplus(self):
        surplus_test = SolverCompetitionSurplusTest()
        # minor EBBO violation
        tx_hash = "0xb2189d1a9fe31d15522f0110c0a2907354fbb1edccd1a6186ef0608fe5ad5722"
        self.assertTrue(surplus_test.run(tx_hash))
        # hash not in the data base
        tx_hash = "0x999999999fe31d15522f0110c0a2907354fbb1edccd1a6186ef0608fe5ad5722"
        self.assertFalse(surplus_test.run(tx_hash))
        # surplus shift to partial fill
        tx_hash = "0xf467a6a01f61fa608c1bc116e2f4f4df1b95461827b1e7700c1d36628875feab"
        self.assertTrue(surplus_test.run(tx_hash))
        # order combined with partial fill
        tx_hash = "0x8e9f98cabf9b6ff4e001eda5efacfd70590a60bd03a499d8b02130b67b208eb1"
        self.assertTrue(surplus_test.run(tx_hash))
        # partial fill with competition
        # look for this


if __name__ == "__main__":
    unittest.main()
