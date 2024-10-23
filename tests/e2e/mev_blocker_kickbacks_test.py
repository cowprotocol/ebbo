"""
Tests for large score test.
"""

import unittest
from src.monitoring_tests.mev_blocker_kickbacks_test import (
    MEVBlockerRefundsMonitoringTest,
)


class TestHighScore(unittest.TestCase):
    def test_high_score(self) -> None:
        high_score_test = MEVBlockerRefundsMonitoringTest()
        # large kickback tx
        tx_hash = "0xcbf4677177fb320b7e000ca95b31b5259648c75ebcfa9544014298ddfea94282"
        self.assertTrue(high_score_test.run(tx_hash))

        # no kickback tx
        tx_hash = "0x3198bc18bc41ec3eb35cc382697d18917ebdaf03528e7dcc5270488d156037c8"
        self.assertTrue(high_score_test.run(tx_hash))


if __name__ == "__main__":
    unittest.main()
