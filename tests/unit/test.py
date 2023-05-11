"""
File to run historical block/hash testing for EBBO
"""
import unittest
from src.off_chain.cow_endpoint_surplus import EndpointSolutionsEBBO
from src.fee_monitoring.fee_monitoring import FeeMonitoring


class TestSurplusCalculation(unittest.TestCase):
    """
    Each function of this class runs a test
    """

    def test_hash_input(self) -> None:
        """
        Test that function works with a hash
        """
        self.hash = "0x8b40027e1484c64ae4154d65a5d727ae7f912efd5df43f2c70ae92393ee93b7c"
        self.file_name = str(self.hash)
        instance = EndpointSolutionsEBBO(self.file_name)
        self.assertIsNone(instance.get_surplus_by_input(settlement_hash=self.hash))

    def test_block_range_input(self) -> None:
        """
        Test that function works with a start and end block input
        """
        self.start_block = 16996550
        self.end_block = 16997050
        self.file_name = str(self.start_block) + "_surplusTo_" + str(self.end_block)
        instance = EndpointSolutionsEBBO(self.file_name)
        self.assertIsNone(
            instance.get_surplus_by_input(
                start_block=self.start_block, end_block=self.end_block
            )
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
