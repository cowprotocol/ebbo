"""
OrderbookAPI for fetching relevant data using the CoW Swap Orderbook API.
"""

# pylint: disable=logging-fstring-interpolation

from typing import Any, Optional
import json
import requests
from src.helper_functions import Logger
from src.models import Trade, OrderData, OrderExecution
from src.constants import (
    header,
    REQUEST_TIMEOUT,
    SUCCESS_CODE,
    FAIL_CODE,
)

PROD_BASE_URL = "https://api.cow.fi/mainnet/api/v1/"
BARN_BASE_URL = "https://barn.api.cow.fi/mainnet/api/v1/"


class OrderbookAPI:
    """
    Class for fetching data from a Web3 API.
    """

    def __init__(self) -> None:
        self.logger = Logger()

    def get_solver_competition_data(self, tx_hash: str) -> Optional[dict[str, Any]]:
        """
        Get solver competition data from a transaction hash.
        The returned dict follows the schema outlined here:
        https://api.cow.fi/docs/#/default/get_api_v1_solver_competition_by_tx_hash__tx_hash_
        """
        prod_endpoint_url = f"{PROD_BASE_URL}solver_competition/by_tx_hash/{tx_hash}"
        barn_endpoint_url = f"{BARN_BASE_URL}solver_competition/by_tx_hash/{tx_hash}"
        solver_competition_data: Optional[dict[str, Any]] = None
        try:
            json_competition_data = requests.get(
                prod_endpoint_url,
                headers=header,
                timeout=REQUEST_TIMEOUT,
            )
            if json_competition_data.status_code == SUCCESS_CODE:
                solver_competition_data = json.loads(json_competition_data.text)
            elif json_competition_data.status_code == FAIL_CODE:
                barn_competition_data = requests.get(
                    barn_endpoint_url, headers=header, timeout=REQUEST_TIMEOUT
                )
                if barn_competition_data.status_code == SUCCESS_CODE:
                    solver_competition_data = json.loads(barn_competition_data.text)
                else:
                    return None
        except requests.RequestException as err:
            self.logger.warning(
                f"Connection error while fetching competition data. Hash: {tx_hash}, error: {err}"
            )
            return None
        return solver_competition_data

    def get_order_data(self, uid: str) -> dict[str, Any] | None:
        """Get order data from uid.
        The returned dict follows the schema outlined here:
        https://api.cow.fi/docs/#/default/get_api_v1_orders__UID_
        """
        prod_endpoint_url = f"{PROD_BASE_URL}orders/{uid}"
        barn_endpoint_url = f"{BARN_BASE_URL}orders/{uid}"
        order_data: Optional[dict[str, Any]] = None
        try:
            json_order_data = requests.get(
                prod_endpoint_url,
                headers=header,
                timeout=REQUEST_TIMEOUT,
            )
            if json_order_data.status_code == SUCCESS_CODE:
                order_data = json_order_data.json()
            elif json_order_data.status_code == FAIL_CODE:
                barn_order_data = requests.get(
                    barn_endpoint_url, headers=header, timeout=REQUEST_TIMEOUT
                )
                if barn_order_data.status_code == SUCCESS_CODE:
                    order_data = barn_order_data.json()
                else:
                    return None
        except requests.RequestException as err:
            self.logger.warning(
                f"Connection error while fetching order data. UID: {uid}, error: {err}"
            )
            return None
        return order_data

    def get_trade(
        self, order_response: dict[str, Any], execution_response: dict[str, Any]
    ) -> Trade:
        """Create Trade from order and execution data."""
        data = OrderData(
            int(order_response["buyAmount"]),
            int(order_response["sellAmount"]),
            int(order_response["feeAmount"]),
            order_response["buyToken"],
            order_response["sellToken"],
            order_response["kind"] == "sell",
            order_response["partiallyFillable"],
        )
        execution = OrderExecution(
            int(execution_response["buyAmount"]),
            int(execution_response["sellAmount"]),
            0,
        )
        return Trade(data, execution)

    def get_uid_trades(self, solution: dict[str, Any]) -> dict[str, Trade] | None:
        """Get a dictionary mapping UIDs to trades in a solution."""
        trades_dict: dict[str, Trade] = {}
        for execution in solution["orders"]:
            uid = execution["id"]
            order_data = self.get_order_data(uid)
            if order_data is None:
                return None
            trades_dict[uid] = self.get_trade(order_data, execution)

        return trades_dict
