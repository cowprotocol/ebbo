"""
TokenListAPI for fetching a curated token list.
"""
# pylint: disable=logging-fstring-interpolation
from typing import Optional
import requests
from src.helper_functions import get_logger
from src.constants import (
    header,
    REQUEST_TIMEOUT,
)


class TokenListAPI:
    """
    Class for fetching a curated token list.
    """

    def __init__(self) -> None:
        self.logger = get_logger()

    def get_token_list(self) -> Optional[list[str]]:
        """
        Returns a token list.
        """
        kleros_url = "http://t2crtokens.eth.link"
        one_inch_url = "https://tokens.1inch.eth.link"
        aave_url = "https://tokenlist.aave.eth.link"

        url_list = [kleros_url, one_inch_url, aave_url]

        token_list: list[str] = []
        for url in url_list:
            try:
                data = requests.get(
                    url,
                    headers=header,
                    timeout=REQUEST_TIMEOUT,
                )
                rsp = data.json()
                if "tokens" in rsp:
                    for token in rsp["tokens"]:
                        token_list.append(token["address"].lower())
            except requests.RequestException as err:
                self.logger.warning(
                    f"Connection error while fetching a token list, error: {err}"
                )
            if len(token_list) > 0:
                return token_list
        return None
