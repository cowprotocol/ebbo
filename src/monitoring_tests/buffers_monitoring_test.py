"""
Checks the value of buffers every 150 settlements by invoking
the ehtplorer api, and in some cases, coingecko.
"""
# pylint: disable=logging-fstring-interpolation
import requests
from src.monitoring_tests.base_test import BaseTest
from src.constants import (
    BUFFER_INTERVAL,
    header,
    REQUEST_TIMEOUT,
    BUFFER_VALUE_THRESHOLD,
)


class BuffersMonitoringTest(BaseTest):
    """
    This test compares the surplus all orders from the winning settlement to
    the different executions of these orders by other solvers in the competition.
    """

    def __init__(self) -> None:
        super().__init__()
        self.counter: int = 0
        self.buffers_value = 0

    def compute_buffers_value(self) -> bool:
        """
        Evaluates current state of buffers.
        """
        # get all token balances of the smart contract
        try:
            resp = requests.get(
                "https://api.ethplorer.io/\
                    getAddressInfo/\
                    0x9008D19f58AAbD9eD0D60971565AA8510560ab41?\
                    apiKey=freekey",
                headers=header,
                timeout=REQUEST_TIMEOUT,
            )
            rsp = resp.json()

            value_in_usd = 0.0
            for token in rsp["tokens"]:
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
                        coingecko_resp = requests.get(
                            "https://api.coingecko.com/\
                                api/v3/simple/token_price/\
                                ethereum?contract_addresses="
                            + token["tokenInfo"]["address"]
                            + "&vs_currencies=usd",
                            headers=header,
                            timeout=REQUEST_TIMEOUT,
                        )
                        coingecko_rsp = coingecko_resp.json()
                        coingecko_price_in_usd = coingecko_rsp[
                            token["tokenInfo"]["address"]
                        ]["usd"]
                        coingecko_value_in_usd = (
                            balance / 10**decimals
                        ) * coingecko_price_in_usd
                        if coingecko_value_in_usd < token_buffer_value_in_usd:
                            token_buffer_value_in_usd = coingecko_value_in_usd
                    value_in_usd += token_buffer_value_in_usd
            self.buffers_value = value_in_usd
            log_output = f"Buffer value is {self.buffers_value} USD"
            if self.buffers_value > BUFFER_VALUE_THRESHOLD:
                self.alert(log_output)
            else:
                self.logger.info(log_output)

        except requests.RequestException as err:
            self.logger.warning(
                f"Connection error while fetching buffer tokens and prices, error: {err}"
            )
            return False
        return True

    def run(self, tx_hash: str) -> bool:
        """
        Wrapper function for the whole test. Checks if solver competition data is retrievable
        and runs EBBO test, else returns True to add to list of unchecked hashes.
        """
        self.counter += 1
        if self.counter > BUFFER_INTERVAL:
            success = self.compute_buffers_value()
            if success:
                self.counter = 0
        return True
