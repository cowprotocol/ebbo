"""
TokenListAPI for fetching a curated token list.
"""

# pylint: disable=logging-fstring-interpolation
from typing import Optional
import requests
from src.helper_functions import Logger
from src.constants import (
    header,
    REQUEST_TIMEOUT,
)


class TokenListAPI:
    """
    Class for fetching a curated token list.
    """

    def __init__(self) -> None:
        self.logger = Logger()
        self.token_lists = [
            "http://t2crtokens.eth.link",
            "https://tokens.1inch.eth.link",
            "https://tokenlist.aave.eth.link",
        ]

    def get_token_list(self) -> Optional[list[str]]:
        """
        Returns a token list.
        """
        token_list: list[str] = []
        for url in self.token_lists:
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
                self.logger.warning(f"Exception while fetching a token list: {err}")
            if len(token_list) > 0:
                return token_list
        return None
