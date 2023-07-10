"""
Comparing order surplus accross different solutions.
"""
# pylint: disable=logging-fstring-interpolation

from typing import Any
from fractions import Fraction
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.orderbookapi import OrderbookAPI
from src.models import Trade
from src.constants import SURPLUS_ABSOLUTE_DEVIATION_ETH, SURPLUS_REL_DEVIATION


class SolverCompetitionSurplusTest(BaseTest):
    """
    This test compares the surplus all orders from the winning settlement to
    the different executions of these orders by other solvers in the competition.
    """

    def __init__(self) -> None:
        super().__init__()
        self.web3_api = Web3API()
        self.orderbook_api = OrderbookAPI()

    def compare_orders_surplus(self, competition_data: dict[str, Any]) -> bool:
        """
        This function goes through each order that the winning solution executed
        and finds non-winning solutions that executed the same order and
        calculates surplus difference between that pair (winning and non-winning solution).
        """

        solution = competition_data["solutions"][-1]

        trades_dict = self.get_uid_trades(solution)

        for uid in trades_dict:
            trade = trades_dict[uid]
            token_to_eth = Fraction(
                int(
                    competition_data["auction"]["prices"][
                        trade.get_surplus_token().lower()
                    ]
                ),
                10**36,
            )

            trade_alt_dict = self.get_trade_alternatives(
                uid, competition_data["solutions"][0:-1]
            )

            for solver_alt, trade_alt in trade_alt_dict.items():
                a_abs = trade_alt.compare_surplus(trade)
                a_abs_eth = a_abs * token_to_eth
                a_rel = trade_alt.compare_price(trade)

                log_output = "\t".join(
                    [
                        "Solver competition surplus test:",
                        f"Tx Hash: {competition_data['transactionHash']}",
                        f"Order UID: {uid}",
                        f"Winning Solver: {solution['solver']}",
                        f"Solver providing more surplus: {solver_alt}",
                        f"Relative deviation: {float(a_rel * 100):.4f}%",
                        f"Absolute difference: {float(a_abs_eth):.5f}ETH ({a_abs} atoms)",
                    ]
                )

                if (
                    a_abs_eth > SURPLUS_ABSOLUTE_DEVIATION_ETH
                    and a_rel > SURPLUS_REL_DEVIATION
                ):
                    self.alert(log_output)
                elif (
                    a_abs_eth > SURPLUS_ABSOLUTE_DEVIATION_ETH / 2
                    and a_rel > SURPLUS_REL_DEVIATION / 2
                ):
                    self.logger.info(log_output)
                else:
                    self.logger.debug(log_output)

        return True

    def get_trade_alternatives(
        self, uid: str, solution_alternatives: list[dict[str, Any]]
    ) -> dict[str, Trade]:
        """Compute surplus and exchange rate for an order with uid as settled in alternative
        solutions."""
        trade_alt_dict: dict[str, Trade] = {}
        for solution_alt in solution_alternatives:
            if (
                solution_alt["objective"]["fees"]
                < 0.9 * solution_alt["objective"]["cost"]
            ):
                continue
            trades_dict_alt = self.get_uid_trades(solution_alt)
            try:
                trade_alt = trades_dict_alt[uid]
            except KeyError:
                continue
            trade_alt_dict[solution_alt["solver"]] = trade_alt

        return trade_alt_dict

    def get_uid_trades(self, solution: dict[str, Any]) -> dict[str, Trade]:
        """Get a dictionary mapping UIDs to trades in a solution."""
        calldata = solution["callData"]
        settlement = self.web3_api.get_settlement_from_calldata(calldata)
        trades = self.web3_api.get_trades(settlement)
        trades_dict = {
            solution["orders"][i]["id"]: trade for (i, trade) in enumerate(trades)
        }
        return trades_dict

    def run(self, tx_hash: str) -> bool:
        """
        Wrapper function for the whole test. Checks if solver competition data is retrievable
        and runs EBBO test, else returns True to add to list of unchecked hashes.
        """

        solver_competition_data = self.orderbook_api.get_solver_competition_data(
            tx_hash
        )
        if solver_competition_data is None:
            return False

        success = self.compare_orders_surplus(solver_competition_data)

        return success
