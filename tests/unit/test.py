"""
File to run historical block/hash testing for EBBO
"""
import unittest
from src.off_chain.cow_endpoint_surplus import EndpointSolutionsEBBO


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

if __name__ == "__main__":
    unittest.main()
