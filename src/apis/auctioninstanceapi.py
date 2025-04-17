"""
API for fetching auction instances from AWS.
"""

# pylint: disable=logging-fstring-interpolation

from typing import Any, Optional
from copy import deepcopy
import json
import requests
from src.models import OrderData
from src.helper_functions import Logger
from src.constants import (
    header,
    REQUEST_TIMEOUT,
    SUCCESS_CODE,
    FAIL_CODE,
)

PROD_BASE_URL = (
    "https://solver-instances.s3.eu-central-1.amazonaws.com/prod/mainnet/legacy/"
)
BARN_BASE_URL = (
    "https://solver-instances.s3.eu-central-1.amazonaws.com/barn/mainnet/legacy/"
)


class AuctionInstanceAPI:
    """
    Class for fetching auction instance files from AWS.
    """

    def __init__(self) -> None:
        self.logger = Logger()

    def get_auction_instance(self, auction_id: int) -> Optional[dict[str, Any]]:
        """
        Get auction instance files for an auction id.
        """
        prod_endpoint_url = f"{PROD_BASE_URL}{auction_id}.json"
        barn_endpoint_url = f"{BARN_BASE_URL}{auction_id}.json"
        auction_instance: Optional[dict[str, Any]] = None
        try:
            json_auction_instance = requests.get(
                prod_endpoint_url,
                headers=header,
                timeout=REQUEST_TIMEOUT,
            )
            if json_auction_instance.status_code == SUCCESS_CODE:
                auction_instance = json.loads(json_auction_instance.text)
            elif json_auction_instance.status_code == FAIL_CODE:
                json_auction_instance = requests.get(
                    barn_endpoint_url, headers=header, timeout=REQUEST_TIMEOUT
                )
                if json_auction_instance.status_code == SUCCESS_CODE:
                    auction_instance = json.loads(json_auction_instance.text)
                else:
                    return None
        except requests.RequestException as err:
            self.logger.warning(
                "Connection error while fetching auction instance. "
                f"Auction ID: {auction_id}, error: {err}"
            )
            return None
        return auction_instance

    def get_order_data(self, uid: str, auction_instance: dict[str, Any]) -> OrderData:
        """Get order data from uid and auction instance"""
        for order in auction_instance["orders"].values():
            if order["id"] == uid:
                return OrderData(
                    int(order["buy_amount"]),
                    int(order["sell_amount"]),
                    int(order["fee"]["amount"]),
                    order["buy_token"],
                    order["sell_token"],
                    order["is_sell_order"],
                    order["allow_partial_fill"],
                )
        raise ValueError(
            f"uid {uid} not in auction instance "
            f"for auction id {auction_instance['metadata']['auction_id']}"
        )

    def generate_reduced_single_order_auction_instance(
        self, uid: str, auction_instance: dict[str, Any]
    ) -> dict[str, Any]:
        """Get auction instance only containing the order with a given uid."""
        order_auction_instance = deepcopy(auction_instance)
        for key, order_ in auction_instance["orders"].items():
            if order_["id"] == uid:
                order_auction_instance["orders"] = {key: order_}
                return order_auction_instance
        raise ValueError(
            f"uid {uid} not in auction instance "
            f"for auction id {auction_instance['metadata']['auction_id']}"
        )
