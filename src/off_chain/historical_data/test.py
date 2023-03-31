import unittest
from cow_endpoint_surplus import EBBOHistoricalDataTesting, get_surplus_difference


class TestSurplusCalculation(unittest.TestCase):
    def test_hash_input(self) -> None:
        # Test that function works with a hash
        self.hash = "0x703f603e67ac532646ce2d4a5cd85703bcfbad0dd64364fc2d1bd8e38d7871c6"
        self.file_name = str(self.hash) + ".txt"
        # clears the previous file if checking same hash
        with open(f"{self.file_name}", mode="w") as file:
            file.write("\n")
        file.close()
        instance = EBBOHistoricalDataTesting(self.file_name)
        self.assertIsNone(instance.get_surplus_by_input(settlement_hash=self.hash))

    def test_block_range_input(self) -> None:
        # Test that function works with a start and end block input
        self.start_block = 16936719
        self.end_block = 16939800
        self.file_name = (
            str(self.start_block) + "_surplusTo_" + str(self.end_block) + ".txt"
        )
        # clears the previous file if checking same block range
        with open(f"{self.file_name}", mode="w") as file:
            file.write("\n")
        file.close()
        instance = EBBOHistoricalDataTesting(self.file_name)
        self.assertIsNone(
            instance.get_surplus_by_input(
                start_block=self.start_block, end_block=self.end_block
            )
        )
        instance.statistics_output(self.start_block, self.end_block)

    def test_surplus_difference(self) -> None:
        # Test that function works with a hash
        self.order_data = {}
        self.order_data["buyAmount"] = "2390570453901"
        self.order_data["sellAmount"] = "2411147339029"
        self.order_data["executedBuyAmount"] = "2402443463900"
        self.order_data["buyToken"] = "0xdac17f958d2ee523a2206206994597c13d831ec7"
        self.order_data["sellToken"] = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
        self.order_data["kind"] = "sell"
        self.order_data["class"] = "market"

        self.order = {
            "id": "0x9bd10334850d29301bff94dd9cf9080963009f7befec3c9e6fe1b6cd885b7abb40093c0156cd8d1daefb5a5465d17fcc6467aa31641c414d",
            "executedAmount": "2411147339029",
        }
        self.clearingPrices = {
            "0x6710c63432a2de02954fc0f851db07146a6c0312": "2847836368384604390076",
            "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "2402567036407",
            "0xc91a71a1ffa3d8b22ba615ba1b9c01b2bbbf55ad": "496353767667424323174400",
            "0xdac17f958d2ee523a2206206994597c13d831ec7": "2411147339029",
        }

        (
            self.diff_surplus,
            self.percent_deviation,
            self.surplus_token,
        ) = get_surplus_difference(self.order_data, self.clearingPrices, self.order)
        self.assertEqual(self.diff_surplus, -123572507, "Not equivalent!")


if __name__ == "__main__":
    unittest.main()
