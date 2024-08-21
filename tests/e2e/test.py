"""
File to run historical block/hash testing for EBBO
"""
import unittest
from src.monitoring_tests.competition_endpoint_test.endpoint_test import EndpointTest
from src.monitoring_tests.fee_monitoring.fee_monitoring import FeeMonitoring


# class TestSurplusCalculation(unittest.TestCase):
#     """
#     Each function of this class runs a test
#     """

#     def test_hash_input(self) -> None:
#         """
#         Test that function works with a hash
#         """
#         tx_hash = "0x8b40027e1484c64ae4154d65a5d727ae7f912efd5df43f2c70ae92393ee93b7c"
#         instance = EndpointTest()
#         self.assertTrue(instance.cow_endpoint_test(tx_hash))


class TestFeeMonitoring(unittest.TestCase):
    """
    Each function of this class runs a test
    """

    def test_hash_input(self) -> None:
        """
        Test that function works with a hash
        """
        instance = FeeMonitoring()
        # tx_hash = "0xb1add23c49fc99f1471b61e48a1f0e6eb18f88d190144cea80dfc290ad0bcc98"
        tx_hash = "0xf467a6a01f61fa608c1bc116e2f4f4df1b95461827b1e7700c1d36628875feab"
        self.assertTrue(instance.fee_test(tx_hash))
        # buy order:
        tx_hash = "0x8e9f98cabf9b6ff4e001eda5efacfd70590a60bd03a499d8b02130b67b208eb1"
        self.assertTrue(instance.fee_test(tx_hash))
        # small executed amount:
        tx_hash = "0xda857a0db563dae564b09febb683fff6150628c1706afc9ebd961c194ca29c5e"
        self.assertTrue(instance.fee_test(tx_hash))


if __name__ == "__main__":
    unittest.main()
