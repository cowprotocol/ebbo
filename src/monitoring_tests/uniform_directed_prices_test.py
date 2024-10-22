"""
Checks the uniform directed prices constraint that was introduced with CIP-38
"""

# pylint: disable=duplicate-code
from typing import Any
from fractions import Fraction
from src.monitoring_tests.base_test import BaseTest
from src.apis.orderbookapi import OrderbookAPI
from src.constants import (
    UDP_SENSITIVITY_THRESHOLD,
)


class UniformDirectedPricesTest(BaseTest):
    """
    This test checks whether the Uniform Directed Prices constraint,
    as introduced in CIP-38, is satisfied.
    """

    def __init__(self) -> None:
        super().__init__()
        self.orderbook_api = OrderbookAPI()

    def check_udp(self, competition_data: dict[str, Any]) -> bool:
        """
        This function checks whether there are multiple orders in the same directed token pair,
        and if so, checks whether UDP is satisfied.
        """
        solution = competition_data["solutions"][-1]
        trades_dict = self.orderbook_api.get_uid_trades(solution)

        if trades_dict is None:
            return False

        directional_prices: dict[tuple[str, str], list[Fraction]] = {}
        for _, trade in trades_dict.items():
            token_pair = (
                trade.data.sell_token.lower(),
                trade.data.buy_token.lower(),
            )
            directional_price = Fraction(
                trade.execution.sell_amount, trade.execution.buy_amount
            )
            if token_pair not in directional_prices:
                directional_prices[token_pair] = []
            directional_prices[token_pair].append(directional_price)

        for pair, prices_list in directional_prices.items():
            if len(prices_list) == 1:
                continue
            min_rate = min(prices_list)
            max_rate = max(prices_list)

            log_output = "\t".join(
                [
                    "Uniform Directed Prices test:",
                    f"Tx Hash: {competition_data['transactionHashes'][0]}",
                    f"Winning Solver: {solution['solver']}",
                    f"Token pair: {pair}",
                    f"Directional prices: {[float(p) for p in prices_list]}",
                ]
            )
            if max_rate > min_rate * (1 + UDP_SENSITIVITY_THRESHOLD):
                self.alert(log_output)
            elif max_rate > min_rate * (1 + UDP_SENSITIVITY_THRESHOLD / 10):
                self.logger.info(log_output)

        return True

    def run(self, tx_hash: str) -> bool:
        """
        Wrapper function for the whole test. Checks if violation is more than
        UDP_SENSITIVITY_THRESHOLD, in which case it generates an alert.
        """
        solver_competition_data = self.orderbook_api.get_solver_competition_data(
            tx_hash
        )
        if solver_competition_data is None:
            return False

        success = self.check_udp(solver_competition_data)

        return success
