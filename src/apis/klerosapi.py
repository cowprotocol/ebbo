"""
KlerosAPI for fetching the Kleros token list.
"""
# pylint: disable=logging-fstring-interpolation

import requests
from src.helper_functions import get_logger
from src.constants import (
    header,
    REQUEST_TIMEOUT,
)


class KlerosAPI:
    """
    Class for fetching the Kleros token list.
    """

    def __init__(self) -> None:
        self.logger = get_logger()

    def get_token_list(self) -> list[str]:
        """
        Returns the Kleros token list.
        """
        kleros_url = "http://t2crtokens.eth.link"

        try:
            kleros_data = requests.get(
                kleros_url,
                headers=header,
                timeout=REQUEST_TIMEOUT,
            )
            kleros_rsp = kleros_data.json()
            kleros_list = []
            if "tokens" not in kleros_rsp:
                return kleros_list
            for token in kleros_rsp["tokens"]:
                kleros_list.append(token["address"].lower())
        except requests.RequestException as err:
            self.logger.warning(
                f"Connection error while fetching the Kleros token list, error: {err}"
            )
        return kleros_list
