"""
Comparing order surplus accross different solutions.
"""
# pylint: disable=logging-fstring-interpolation

from typing import Any
from fractions import Fraction
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.orderbookapi import OrderbookAPI
from src.helper_functions import get_logger
from src.constants import ABSOLUTE_ETH_FLAG_AMOUNT, REL_DEVIATION_FLAG_PERCENT


class SolverCompetitionSurplusTest(BaseTest):
    """
    This test compares the surplus all orders from the winning settlement to
    the different executions of these orders by other solvers in the competition.
    """

    def __init__(self):
        super().__init__()
        self.web3_api = Web3API()
        self.orderbook_api = OrderbookAPI()
        self.logger = get_logger()

    def compare_orders_surplus(self, competition_data: dict[str, Any]) -> bool:
        """
        This function goes through each order that the winning solution executed
        and finds non-winning solutions that executed the same order and
        calculates surplus difference between that pair (winning and non-winning solution).
        """

        tx_hash = competition_data["transactionHash"]
        solution = competition_data["solutions"][-1]
        solver = solution["solver"]
        calldata = solution["callData"]
        settlement = self.web3_api.get_settlement_from_calldata(calldata)
        trades = self.web3_api.get_trades(settlement)
        external_prices = competition_data["auction"]["prices"]

        trades_dict = {
            solution["orders"][i]["id"]: trade for (i, trade) in enumerate(trades)
        }

        for uid in trades_dict:
            trade = trades_dict[uid]
            surplus = trade.get_surplus()
            price = trade.get_price()
            token_to_eth = Fraction(
                int(external_prices[trade.get_surplus_token().lower()]), 10**36
            )
            surplus_alt_dict: dict[str, tuple[int, Fraction]] = {}
            for solution_alt in competition_data["solutions"][0:-1]:
                if (
                    solution_alt["objective"]["fees"]
                    < 0.9 * solution_alt["objective"]["cost"]
                ):
                    continue
                uid_list = [o["id"] for o in solution_alt["orders"]]
                try:
                    i = uid_list.index(uid)
                except ValueError:
                    continue
                calldata_alt = solution_alt["callData"]
                settlement_alt = self.web3_api.get_settlement_from_calldata(
                    calldata_alt
                )
                trade_alt = self.web3_api.get_trades(settlement_alt)[i]
                surplus_alt = trade_alt.get_surplus()
                price_alt = trade_alt.get_price()
                surplus_alt_dict[solution_alt["solver"]] = surplus_alt
            if len(surplus_alt_dict) == 0:
                continue
            solver_alt = max(surplus_alt_dict, key=lambda key: surplus_alt_dict[key])
            surplus_alt = surplus_alt_dict[solver_alt]
            a_abs = surplus_alt - surplus
            a_abs_eth = a_abs * token_to_eth
            a_rel = price / price_alt - 1
            log_output = [
                "Solver competition surplus test:",
                f"Tx Hash: {tx_hash}",
                f"Order UID: {uid}",
                f"Winning Solver: {solver}",
                f"Solver providing more surplus: {solver_alt}",
                f"Relative deviation: {float(a_rel * 100):.4f}%",
                f"Absolute difference: {float(a_abs_eth):.5f}ETH ({a_abs} atoms)",
            ]
            self.logger.info("\t".join(log_output))
            if (
                a_abs_eth > ABSOLUTE_ETH_FLAG_AMOUNT
                and a_rel * 100 > REL_DEVIATION_FLAG_PERCENT
            ):
                self.alert("\t".join(log_output))

        return True

    def run(self, tx_hash) -> bool:
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

    def alert(self, msg: str) -> None:
        self.logger.error(msg)
