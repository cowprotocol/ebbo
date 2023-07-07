"""
OrderbookAPI for fetching relevant data using the CoW Swap Orderbook API.
"""
# pylint: disable=logging-fstring-interpolation

from typing import Any, Optional
import json
import requests
from src.helper_functions import get_logger
from src.models import Trade, OrderExecution
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
        self.logger = get_logger()

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

    def get_quote(self, trade: Trade) -> Optional[Trade]:
        """
        Given a trade, compute buy_amount, sell_amount, and fee_amount of the trade
        as proposed by our quoting infrastructure.
        """

        if trade.data.is_sell_order:
            kind = "sell"
            limit_amount_name = "sellAmountBeforeFee"
            executed_amount = trade.execution.sell_amount
        else:
            kind = "buy"
            limit_amount_name = "buyAmountAfterFee"
            executed_amount = trade.execution.buy_amount

        request_dict = {
            "sellToken": trade.data.sell_token,
            "buyToken": trade.data.buy_token,
            "receiver": "0x0000000000000000000000000000000000000000",
            "appData": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "partiallyFillable": False,
            "sellTokenBalance": "erc20",
            "buyTokenBalance": "erc20",
            "from": "0x0000000000000000000000000000000000000000",
            "priceQuality": "optimal",
            "signingScheme": "eip712",
            "onchainOrder": False,
            "kind": kind,
            limit_amount_name: str(executed_amount),
        }
        prod_endpoint_url = f"{PROD_BASE_URL}quote"

        try:
            quote_response = requests.post(
                prod_endpoint_url,
                headers=header,
                json=request_dict,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as err:
            self.logger.warning(
                f"Fee quote failed. Request: {request_dict}, error: {err}"
            )
            return None

        if quote_response.status_code != SUCCESS_CODE:
            error_response_json = json.loads(quote_response.content)
            self.logger.warning(
                f"Error {error_response_json['errorType']},"
                + f"{error_response_json['description']} while getting quote for trade {trade}"
            )
            return None

        quote_json = json.loads(quote_response.text)
        self.logger.debug("Quote received: %s", quote_json)

        quote_buy_amount = int(quote_json["quote"]["buyAmount"])
        quote_sell_amount = int(quote_json["quote"]["sellAmount"])
        quote_fee_amount = int(quote_json["quote"]["feeAmount"])

        quote_execution = OrderExecution(
            quote_buy_amount, quote_sell_amount, quote_fee_amount
        )

        return Trade(trade.data, quote_execution)

    def get_settlement_fee(self, solution: dict[str, Any]) -> int:
        """Return the fee from the objective of a solution."""
        return int(solution["objective"]["fees"])
