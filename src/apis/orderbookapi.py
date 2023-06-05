"""
OrderbookAPI for fetching relevant data using the CoW Swap Orderbook API.
"""
from typing import Any, Optional
from json import loads
import requests
from src.helper_functions import get_logger
from src.trades import Trade, OrderExecution
from src.constants import (
    header,
    SUCCESS_CODE,
    FAIL_CODE,
)


class OrderbookAPI:
    """
    Class for fetching data from a Web3 API.
    """

    def __init__(self):
        self.logger = get_logger()

    def get_solver_competition_data(
        self,
        settlement_hashes_list: list[str],
    ) -> list[dict[str, Any]]:
        """
        This function uses a list of tx hashes to fetch and assemble competition data
        for each of the tx hashes and returns it.
        """
        solver_competition_data = []
        for tx_hash in settlement_hashes_list:
            try:
                prod_endpoint_url = (
                    "https://api.cow.fi/mainnet/api/v1/solver_competition"
                    f"/by_tx_hash/{tx_hash}"
                )
                json_competition_data = requests.get(
                    prod_endpoint_url,
                    headers=header,
                    timeout=30,
                )
                if json_competition_data.status_code == SUCCESS_CODE:
                    solver_competition_data.append(loads(json_competition_data.text))
                elif json_competition_data.status_code == FAIL_CODE:
                    barn_endpoint_url = (
                        "https://barn.api.cow.fi/mainnet/api/v1"
                        f"/solver_competition/by_tx_hash/{tx_hash}"
                    )
                    barn_competition_data = requests.get(
                        barn_endpoint_url, headers=header, timeout=30
                    )
                    if barn_competition_data.status_code == SUCCESS_CODE:
                        solver_competition_data.append(
                            loads(barn_competition_data.text)
                        )
            except requests.exceptions.ConnectionError as except_err:
                self.logger.error(
                    "Connection error while fetching competition data: %s.",
                    str(except_err),
                )

        return solver_competition_data

    def get_endpoint_order_data(self, tx_hash: str) -> list[Any]:
        """
        Get all orders in a transaction from the transaction hash.
        """
        prod_endpoint_url = (
            "https://api.cow.fi/mainnet/api/v1/transactions/" + tx_hash + "/orders"
        )
        barn_endpoint_url = (
            "https://barn.api.cow.fi/mainnet/api/v1/transactions/" + tx_hash + "/orders"
        )
        orders_response = requests.get(
            prod_endpoint_url,
            headers=header,
            timeout=30,
        )
        if orders_response.status_code != SUCCESS_CODE:
            orders_response = requests.get(
                barn_endpoint_url,
                headers=header,
                timeout=30,
            )
            if orders_response.status_code != SUCCESS_CODE:
                self.logger.error(
                    "Error loading orders from mainnet: %s", orders_response.status_code
                )
                return []

        orders = loads(orders_response.text)

        return orders

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
        prod_endpoint_url = "https://api.cow.fi/mainnet/api/v1/quote"

        try:
            quote_response = requests.post(
                prod_endpoint_url,
                headers=header,
                json=request_dict,
                timeout=30,
            )
            if quote_response.status_code != SUCCESS_CODE:
                self.logger.error(
                    "Error %s getting quote for trade %s: %s",
                    quote_response.status_code,
                    trade,
                    quote_response.content,
                )
                return None
        except ValueError as except_err:
            self.logger.error(
                "Unhandled exception when fetching quotes: %s.", str(except_err)
            )
            return None

        quote_json = loads(quote_response.text)
        self.logger.debug("Quote received: %s", quote_json)

        quote_buy_amount = int(quote_json["quote"]["buyAmount"])
        quote_sell_amount = int(quote_json["quote"]["sellAmount"])
        quote_fee_amount = int(quote_json["quote"]["feeAmount"])

        quote_execution = OrderExecution(
            quote_buy_amount, quote_sell_amount, quote_fee_amount
        )

        return Trade(trade.data, quote_execution)
