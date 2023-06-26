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
                f"Tx Hash: {tx_hash}",
                f"Order UID: {uid[:10]}",
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

    #     for trade, individual_win_order in zip(
    #         trades, competition_data["solutions"][-1]["orders"]
    #     ):
    #         onchain_order_data = TemplateTest.get_onchain_order_data(
    #             trade, onchain_clearing_prices, tokens
    #         )
    #         try:
    #             # ignore limit orders, represented by zero fee amount
    #             if onchain_order_data["fee_amount"] == 0:
    #                 continue

    #             surplus_deviation_dict = {}
    #             soln_count = 0
    #             for soln in competition_data["solutions"]:
    #                 if soln["objective"]["fees"] < 0.9 * soln["objective"]["cost"]:
    #                     surplus_deviation_dict[soln_count] = 0.0, 0.0
    #                     soln_count += 1
    #                     continue
    #                 for order in soln["orders"]:
    #                     if individual_win_order["id"] == order["id"]:
    #                         # order data, executed amount, clearing price vector, and
    #                         # external prices are passed
    #                         surplus_eth, percent_deviation = cls.get_flagging_values(
    #                             onchain_order_data,
    #                             int(order["executedAmount"]),
    #                             soln["clearingPrices"],
    #                             competition_data["auction"]["prices"],
    #                         )
    #                         surplus_deviation_dict[soln_count] = (
    #                             surplus_eth,
    #                             percent_deviation,
    #                         )
    #                 soln_count += 1
    #             cls.flagging_order_check(
    #                 surplus_deviation_dict,
    #                 individual_win_order["id"],
    #                 competition_data,
    #             )
    #         except TypeError as except_err:
    #             TemplateTest.logger.error("Unhandled exception: %s.", str(except_err))
    #             # templateTest.logger.error(traceback.format_exc())

    # @classmethod
    # def flagging_order_check(
    #     cls,
    #     surplus_deviation_dict: Dict[int, Tuple[float, float]],
    #     individual_order_id: str,
    #     competition_data: Dict[str, Any],
    # ) -> None:
    #     """
    #     Below function finds the solution that could have been given a better surplus (if any) and
    #     checks whether if meets the flagging conditions. If yes, logging function is called.
    #     """

    #     sorted_dict = dict(
    #         sorted(surplus_deviation_dict.items(), key=lambda x: x[1][0])
    #     )
    #     sorted_values = sorted(sorted_dict.values(), key=lambda x: x[0])
    #     if (
    #         sorted_values[0][0] < -ABSOLUTE_ETH_FLAG_AMOUNT
    #         and sorted_values[0][1] < -REL_DEVIATION_FLAG_PERCENT
    #     ):
    #         for key, value in sorted_dict.items():
    #             if value == sorted_values[0]:
    #                 first_key = key
    #                 break
    #         winning_solver = competition_data["solutions"][-1]["solver"]

    #         cls.logging_function(
    #             individual_order_id,
    #             first_key,
    #             winning_solver,
    #             competition_data,
    #             sorted_values,
    #         )

    # def logging_function(
    #     self,
    #     individual_order_id: str,
    #     first_key: int,
    #     winning_solver: str,
    #     competition_data: Dict[str, Any],
    #     sorted_values: List[Tuple[float, float]],
    # ) -> None:
    #     """
    #     Logs to terminal (and file iff file_name is passed).
    #     """

    #     log_output = (
    #         "Tx hash: "
    #         + competition_data["transactionHash"]
    #         + "\t\t"
    #         + "Order: "
    #         + individual_order_id
    #         + "\t\t"
    #         + "Winning Solver: "
    #         + winning_solver
    #         + "\t\t"
    #         + "Solver providing more surplus: "
    #         + competition_data["solutions"][first_key]["solver"]
    #         + "\t\t"
    #         + "Relative deviation: "
    #         + (str(format(sorted_values[0][1], ".4f")) + "%")
    #         + "\t\t"
    #         + "Absolute difference: "
    #         + (str(format(sorted_values[0][0], ".5f")) + " ETH")
    #     )
    #     TemplateTest.logger.error(log_output)

    def run(self, tx_hash) -> bool:
        """
        Wrapper function for the whole test. Checks if solver competition data is retrievable
        and runs EBBO test, else returns True to add to list of unchecked hashes
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
