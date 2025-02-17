"""
Checking winner's score and generating an alert if score is very large
"""

# pylint: disable=logging-fstring-interpolation

from typing import Any
from src.monitoring_tests.base_test import BaseTest
from src.apis.orderbookapi import OrderbookAPI
from src.constants import HIGH_SCORE_THRESHOLD_ETH


class HighScoreTest(BaseTest):
    """
    This test checks how large is the winning score and raises an alert if score
    is above certain threshold
    """

    def __init__(self, orderbook_api: OrderbookAPI) -> None:
        super().__init__()
        self.orderbook_api = orderbook_api

    def compute_winning_score(self, competition_data: dict[str, Any]) -> bool:
        """
        This function simply returns the winning score.
        """
        solution = competition_data["solutions"][-1]
        score = int(solution["score"]) / 10**18
        log_output = "\t".join(
            [
                "Large score test:",
                f"Tx Hash: {competition_data['transactionHashes'][0]}",
                f"Winning Solver: {solution['solver']}",
                f"Score in ETH: {score}",
            ]
        )
        if score > HIGH_SCORE_THRESHOLD_ETH:
            self.alert(log_output)
        return True

    def run(self, tx_hash: str) -> bool:
        """
        Wrapper function for the whole test. Checks if solver competition data is retrievable
        and then checks how large the winning score is.
        """

        solver_competition_data = self.orderbook_api.get_solver_competition_data(
            tx_hash
        )
        if solver_competition_data is None:
            return False

        success = self.compute_winning_score(solver_competition_data)

        return success
