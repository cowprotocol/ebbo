"""
Comparing order surplus accross different solutions.
"""

# pylint: disable=logging-fstring-interpolation

from typing import Any
from fractions import Fraction
from src.monitoring_tests.base_test import BaseTest
from src.apis.orderbookapi import OrderbookAPI
from src.models import Trade, OrderExecution
from src.constants import SURPLUS_ABSOLUTE_DEVIATION_ETH, SURPLUS_REL_DEVIATION


class SolverCompetitionSurplusTest(BaseTest):
    """
    This test compares the surplus all orders from the winning settlement to
    the different executions of these orders by other solvers in the competition.
    """

    def __init__(self) -> None:
        super().__init__()
        self.orderbook_api = OrderbookAPI()

    def compare_orders_surplus(self, competition_data: dict[str, Any]) -> bool:
        """
        This function goes through each order that the winning solution executed
        and finds non-winning solutions that executed the same order and
        calculates surplus difference between that pair (winning and non-winning solution).
        """

        solution = competition_data["solutions"][-1]

        trades_dict = self.orderbook_api.get_uid_trades(solution)
        if trades_dict is None:
            return False

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
                trade, uid, competition_data["solutions"][0:-1]
            )

            for solver_alt, trade_alt in trade_alt_dict:
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
                    a_abs_eth > SURPLUS_ABSOLUTE_DEVIATION_ETH / 100
                    and a_rel > SURPLUS_REL_DEVIATION / 10
                ):
                    self.logger.info(log_output)
                else:
                    self.logger.debug(log_output)

        return True

    def get_trade_alternatives(
        self, trade: Trade, uid: str, solution_alternatives: list[dict[str, Any]]
    ) -> list[tuple[str, Trade]]:
        """Compute surplus and exchange rate for an order with uid as settled in alternative
        solutions."""
        trade_alt_list: list[tuple[str, Trade]] = []
        order_data = trade.data
        for solution_alt in solution_alternatives:
            executions_dict_alt = self.get_uid_order_execution(solution_alt)
            try:
                trade_alt = Trade(order_data, executions_dict_alt[uid])
            except KeyError:
                continue
            trade_alt_list.append((solution_alt["solver"], trade_alt))

        return trade_alt_list

    def get_uid_order_execution(
        self, solution: dict[str, Any]
    ) -> dict[str, OrderExecution]:
        """Given a solution from the competition endpoint, compute the executin for all included
        orders.
        """
        result: dict[str, OrderExecution] = {}
        for order in solution["orders"]:
            buy_amount = int(order["buyAmount"])
            sell_amount = int(order["sellAmount"])
            # fee amount is set to zero for the moment, could be computed from clearing prices
            # and buy and sell token of the order
            fee_amount = 0
            order_execution = OrderExecution(buy_amount, sell_amount, fee_amount)
            result[order["id"]] = order_execution
        return result

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
