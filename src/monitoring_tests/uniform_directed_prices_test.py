"""
Checks the uniform directed prices constraint that was introduced with CIP-38
"""
# pylint: disable=logging-fstring-interpolation
from typing import Any
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
        token_pairs = {}
        for uid in trades_dict:
            trade = trades_dict[uid]
            sell_token = trade.data.sell_token
            buy_token = trade.data.buy_token
            sell_amount = trade.execution.sell_amount
            buy_amount = trade.execution.buy_amount
            if (sell_token, buy_token) not in token_pairs:
                token_pairs[(sell_token, buy_token)] = [sell_amount / buy_amount]
            else:
                token_pairs[(sell_token, buy_token)].append(sell_amount / buy_amount)
        for token_pair in token_pairs:
            if len(token_pairs[token_pair]) == 1:
                continue
            min_rate = token_pairs[token_pair][0]
            for rate in token_pairs[token_pair]:
                if rate < min_rate:
                    min_rate = rate
            lower_r = rate * (1 - UDP_SENSITIVITY_THRESHOLD)
            upper_r = rate * (1 + UDP_SENSITIVITY_THRESHOLD)
            for rate in token_pairs[token_pair]:
                if rate < lower_r or rate > upper_r:
                    log_output = "\t".join(
                        [
                            "Uniform Directed Prices test:",
                            f"Tx Hash: {competition_data['transactionHash']}",
                            f"Token pair: {token_pair}",
                        ]
                    )
                    self.alert(log_output)
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
