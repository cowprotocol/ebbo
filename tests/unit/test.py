"""
File to run historical block/hash testing for EBBO
"""
import unittest
from src.monitoring_tests.competition_endpoint_test.endpoint_test import EndpointTest
from src.monitoring_tests.fee_monitoring.fee_monitoring import FeeMonitoring


class TestSurplusCalculation(unittest.TestCase):
    """
    Each function of this class runs a test
    """

    def test_hash_input(self) -> None:
        """
        Test that function works with a hash
        """
        hash = "0x8b40027e1484c64ae4154d65a5d727ae7f912efd5df43f2c70ae92393ee93b7c"
        instance = EndpointTest()
        self.assertIsNone(instance.get_surplus_by_input(settlement_hash=hash))

    def test_block_range_input(self) -> None:
        """
        Test that function works with a start and end block input
        """
        start_block = 16996550
        end_block = 16997050
        instance = EndpointTest()
        self.assertIsNone(
            instance.get_surplus_by_input(start_block=start_block, end_block=end_block)
        )


class TestFeeMonitoring(unittest.TestCase):
    """
    Each function of this class runs a test
    """

    def test_hash_input(self) -> None:
        """
        Test that function works with a hash
        """
        # tx_hash = "0xb1add23c49fc99f1471b61e48a1f0e6eb18f88d190144cea80dfc290ad0bcc98"
        tx_hash = "0x26bd983c653319851224d70d5cee2ac56605f1004fbf695b34358be482647466"
        instance = FeeMonitoring()
        self.assertTrue(instance.fee_test(tx_hash))


if __name__ == "__main__":
    unittest.main()
