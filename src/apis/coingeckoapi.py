"""
CoingeckoAPI for fetching the price in usd of a given token.
"""

# pylint: disable=logging-fstring-interpolation

from typing import Optional
import requests
from src.helper_functions import get_logger
from src.constants import (
    header,
    REQUEST_TIMEOUT,
)


class CoingeckoAPI:
    """
    Class for fetching token prices from Coingecko.
    """

    def __init__(self) -> None:
        self.logger = get_logger()

    def get_token_price_in_usd(self, address: str) -> Optional[float]:
        """
        Returns the Coingecko price in usd of the given token.
        """
        coingecko_url = (
            "https://api.coingecko.com/api/v3/simple/token_price/ethereum?contract_addresses="
            + address
            + "&vs_currencies=usd"
        )
        try:
            coingecko_data = requests.get(
                coingecko_url,
                headers=header,
                timeout=REQUEST_TIMEOUT,
            )
            coingecko_rsp = coingecko_data.json()
            coingecko_price_in_usd = float(coingecko_rsp[address]["usd"])
        except requests.RequestException as err:
            self.logger.warning(
                f"Connection error while fetching Coingecko price for token {address}, error: {err}"
            )
            return None
        return coingecko_price_in_usd
