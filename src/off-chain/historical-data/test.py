import unittest
import cowEndpointSurplus


class TestSurplusCalculation(unittest.TestCase):
    def test_block_range_input(self):
        # Test that function works with a start and end block input
        start_block = 16887000
        end_block = 16890002
        file_name = str(start_block) + "_surplusTo_" + str(end_block) + ".txt"
        # clears the previous file if checking same block range
        with open(f"{file_name}", mode="w") as file:
            file.write("\n")
        file.close()
        instance = cowEndpointSurplus.EBBOHistoricalDataTesting()
        self.assertIsNone(
            instance.total_surplus(
                start_block=start_block, end_block=end_block, file_name=file_name
            )
        )

    def test_hash_input(self):
        # Test that function works with a hash
        hash = "0xcda565e60a3aea1b9171ffd271ca01dd4b2fc9feaa9b008aaf5c8c88f4272333"
        file_name = str(hash) + ".txt"
        # clears the previous file if checking same hash
        with open(f"{file_name}", mode="w") as file:
            file.write("\n")
        file.close()
        instance = cowEndpointSurplus.EBBOHistoricalDataTesting()
        self.assertIsNone(
            instance.total_surplus(settlement_hash=hash, file_name=file_name)
        )


if __name__ == "__main__":
    unittest.main()
