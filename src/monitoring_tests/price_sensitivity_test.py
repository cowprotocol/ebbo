"""
Checks whether native prices are far from UCP for a trade
"""

# pylint: disable=duplicate-code
# pylint: disable=too-many-locals
from typing import Any
from fractions import Fraction
from src.monitoring_tests.base_test import BaseTest
from src.apis.orderbookapi import OrderbookAPI
from src.constants import (
    UCP_VS_NATIVE_SENSITIVITY_THRESHOLD,
)


class PriceSensitivityTest(BaseTest):
    """
    This test checks whether the exchange rate implied by native prices
    is far from exchange rate implied by UCP
    """

    def __init__(self, orderbook_api: OrderbookAPI) -> None:
        super().__init__()
        self.orderbook_api = orderbook_api

    def check_prices(self, competition_data: dict[str, Any]) -> bool:
        """
        This function checks whether native prices are far from ucp
        """
        winning_solution = competition_data["solutions"][-1]
        trades_dict = self.orderbook_api.get_uid_trades(winning_solution)
        if trades_dict is None:
            return False

        ucp = {token.lower(): int(price) for token, price in winning_solution["clearingPrices"].items()}

        native_prices: dict[str, int] = {}
        for token, price in competition_data["auction"]["prices"].items():
            native_prices[token.lower()] = int(price)

        for uid, trade in trades_dict.items():
            sell_token = trade.data.sell_token.lower()
            buy_token = trade.data.buy_token.lower()
            ucp_rate = Fraction(ucp[sell_token], ucp[buy_token])
            native_price_rate = Fraction(
                native_prices[sell_token], native_prices[buy_token]
            )

            max_rate = max(ucp_rate, native_price_rate)
            min_rate = min(ucp_rate, native_price_rate)

            if max_rate > (1 + UCP_VS_NATIVE_SENSITIVITY_THRESHOLD) * min_rate:
                log_output = "\t".join(
                    [
                        "Price sensitivity test:",
                        f"Tx Hash: {competition_data['transactionHashes'][0]}",
                        f"Winning Solver: {winning_solution['solver']}",
                        f"Trade: {uid}",
                        f"Gap: {float(max_rate / min_rate)}",
                    ]
                )
                self.alert(log_output)

        return True

    def run(self, tx_hash: str) -> bool:
        """
        Wrapper function for the whole test. Checks if violation is more than
        UCP_VS_NATIVE_SENSITIVITY_THRESHOLD, in which case it generates an alert.
        """
        solver_competition_data = self.orderbook_api.get_solver_competition_data(
            tx_hash
        )
        if solver_competition_data is None:
            return False

        success = self.check_prices(solver_competition_data)

        return success
