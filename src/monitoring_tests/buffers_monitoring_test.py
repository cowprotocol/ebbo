"""
Checks the value of buffers every 150 settlements by invoking
the ehtplorer api, and in some cases, coingecko.
"""
# pylint: disable=logging-fstring-interpolation
import requests
from src.monitoring_tests.base_test import BaseTest
from src.apis.coingeckoapi import CoingeckoAPI
from src.apis.klerosapi import KlerosAPI
from src.constants import (
    BUFFER_INTERVAL,
    header,
    REQUEST_TIMEOUT,
    BUFFERS_VALUE_USD_THRESHOLD,
)


class BuffersMonitoringTest(BaseTest):
    """
    This test checks the value of the settlement contract buffers
    every 150 settlements and generates an alert if it is higher than 200_000 USD.
    Price feeds from ethplorer and coingecko (as backup) are used.
    """

    def __init__(self) -> None:
        super().__init__()
        self.coingecko_api = CoingeckoAPI()
        self.kleros_api = KlerosAPI()
        self.counter: int = 0

    def compute_buffers_value(self) -> bool:
        """
        Evaluates current state of buffers.
        """
        # get all token balances of the smart contract
        try:
            ethplorer_data = requests.get(
                "https://api.ethplorer.io/getAddressInfo/0x9008D19f58AAbD9eD0D60971565AA8510560ab41?apiKey=freekey",
                headers=header,
                timeout=REQUEST_TIMEOUT,
            )
            ethplorer_rsp = ethplorer_data.json()
            kleros_list = self.kleros_api.get_token_list()

            value_in_usd = 0.0
            if "tokens" not in ethplorer_rsp:
                return False
            for token in ethplorer_rsp["tokens"]:
                if token["tokenInfo"]["address"] not in kleros_list:
                    continue
                balance = token["balance"]
                decimals = int(token["tokenInfo"]["decimals"])
                if token["tokenInfo"]["price"] is not False:
                    price_in_usd = token["tokenInfo"]["price"]["rate"]
                    token_buffer_value_in_usd = (
                        balance / 10**decimals
                    ) * price_in_usd
                    # in case some price is way off and it blows a lot the total value held in the
                    # smart contract we use a second price feed, from coingecko, to correct in case
                    # the initial price is indeed off
                    if token_buffer_value_in_usd > 10000:
                        coingecko_price_in_usd = (
                            self.coingecko_api.get_token_price_in_usd(
                                token["tokenInfo"]["address"]
                            )
                        )
                        coingecko_value_in_usd = (
                            balance / 10**decimals
                        ) * coingecko_price_in_usd
                        if coingecko_value_in_usd < token_buffer_value_in_usd:
                            token_buffer_value_in_usd = coingecko_value_in_usd
                    value_in_usd += token_buffer_value_in_usd
            log_output = f"Buffer value is {value_in_usd} USD"
            if value_in_usd > BUFFERS_VALUE_USD_THRESHOLD:
                self.alert(log_output)
            else:
                self.logger.info(log_output)

        except requests.RequestException as err:
            self.logger.warning(
                f"Connection Error while fetching buffer tokens and prices, error: {err}"
            )
            return False
        return True

    def run(self, tx_hash: str) -> bool:
        """
        Wrapper function for the whole test. Checks if 150 settlements have been observed,
        in which case it invokes the main function that checks the current value of buffers.
        """
        self.counter += 1
        if self.counter > BUFFER_INTERVAL:
            print("HERE")
            success = self.compute_buffers_value()
            if success:
                self.counter = 0
        return True
