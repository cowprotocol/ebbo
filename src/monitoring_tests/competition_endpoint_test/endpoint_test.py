"""
To be completed
"""
from typing import List, Tuple, Dict, Any
from src.monitoring_tests.template_test import TemplateTest
from src.helper_functions import (
    DecodedSettlement,
    percent_eth_conversions_order,
)
from src.constants import ABSOLUTE_ETH_FLAG_AMOUNT, REL_DEVIATION_FLAG_PERCENT

# this class implements the EBBO test based solely on the competition endpoint.
# the way to run the test is by calling the cow_endpoint_test() method
class EndpointTest(TemplateTest):
    """
    To be completed
    """
    @classmethod
    def compare_orders_surplus(cls, competition_data: Dict[str, Any]) -> None:
        """
        This function goes through each order that the winning solution executed
        and finds non-winning solutions that executed the same order and
        calculates surplus difference between that pair (winning and non-winning solution).
        """
        (
            trades,
            onchain_clearing_prices,
            tokens,
        ) = DecodedSettlement.get_decoded_settlement(
            TemplateTest.contract_instance,
            TemplateTest.web_3,
            competition_data["transactionHash"],
        )
        # this loop iterates over a single trade from on-chain trades (decoded data)
        # and order from the list of settled orders in the winning solution. We
        # do this since the corresponding order ID for the trade needs to be chosen.

        # zip is used for simultaneous iteration.
        for trade, individual_win_order in zip(
            trades, competition_data["solutions"][-1]["orders"]
        ):
            onchain_order_data = TemplateTest.get_onchain_order_data(
                trade, onchain_clearing_prices, tokens
            )
            try:
                # ignore limit orders, represented by zero fee amount
                if onchain_order_data["fee_amount"] == 0:
                    continue

                surplus_deviation_dict = {}
                soln_count = 0
                for soln in competition_data["solutions"]:
                    if soln["objective"]["fees"] < 0.9 * soln["objective"]["cost"]:
                        surplus_deviation_dict[soln_count] = 0.0, 0.0
                        soln_count += 1
                        continue
                    for order in soln["orders"]:
                        if individual_win_order["id"] == order["id"]:
                            # order data, executed amount, clearing price vector, and
                            # external prices are passed
                            surplus_eth, percent_deviation = cls.get_flagging_values(
                                onchain_order_data,
                                int(order["executedAmount"]),
                                soln["clearingPrices"],
                                competition_data["auction"]["prices"],
                            )
                            surplus_deviation_dict[soln_count] = (
                                surplus_eth,
                                percent_deviation,
                            )
                    soln_count += 1
                cls.flagging_order_check(
                    surplus_deviation_dict,
                    individual_win_order["id"],
                    competition_data,
                )
            except TypeError as except_err:
                TemplateTest.logger.error("Unhandled exception: %s.", str(except_err))
                # templateTest.logger.error(traceback.format_exc())

    @classmethod
    def flagging_order_check(
        cls,
        surplus_deviation_dict: Dict[int, Tuple[float, float]],
        individual_order_id: str,
        competition_data: Dict[str, Any],
    ) -> None:
        """
        Below function finds the solution that could have been given a better surplus (if any) and
        checks whether if meets the flagging conditions. If yes, logging function is called.
        """

        sorted_dict = dict(
            sorted(surplus_deviation_dict.items(), key=lambda x: x[1][0])
        )
        sorted_values = sorted(sorted_dict.values(), key=lambda x: x[0])
        if (
            sorted_values[0][0] < -ABSOLUTE_ETH_FLAG_AMOUNT
            and sorted_values[0][1] < -REL_DEVIATION_FLAG_PERCENT
        ):
            for key, value in sorted_dict.items():
                if value == sorted_values[0]:
                    first_key = key
                    break
            winning_solver = competition_data["solutions"][-1]["solver"]

            cls.logging_function(
                individual_order_id,
                first_key,
                winning_solver,
                competition_data,
                sorted_values,
            )

    @classmethod
    def logging_function(
        cls,
        individual_order_id: str,
        first_key: int,
        winning_solver: str,
        competition_data: Dict[str, Any],
        sorted_values: List[Tuple[float, float]],
    ) -> None:
        """
        Logs to terminal (and file iff file_name is passed).
        """

        log_output = (
            "Tx hash: "
            + competition_data["transactionHash"]
            + "\t\t"
            + "Order: "
            + individual_order_id
            + "\t\t"
            + "Winning Solver: "
            + winning_solver
            + "\t\t"
            + "Solver providing more surplus: "
            + competition_data["solutions"][first_key]["solver"]
            + "\t\t"
            + "Relative deviation: "
            + (str(format(sorted_values[0][1], ".4f")) + "%")
            + "\t\t"
            + "Absolute difference: "
            + (str(format(sorted_values[0][0], ".5f")) + " ETH")
        )
        TemplateTest.logger.error(log_output)

    @classmethod
    def get_flagging_values(
        cls, onchain_order_data, executed_amount, clearing_prices, external_prices
    ):
        """
        This function calculates surplus for solution, compares to winning
        solution to get surplus difference, and finally returns percent_deviations
        and surplus difference in eth based on external prices.
        """
        if onchain_order_data["order_type"] == "1":  # buy order
            # in this case, it is sell amount
            buy_or_sell_amount = int(onchain_order_data["sell_amount"])
            conversion_external_price = int(
                external_prices[onchain_order_data["sell_token"]]
            )
        elif onchain_order_data["order_type"] == "0":  # sell order
            # in this case, it is buy amount
            buy_or_sell_amount = int(onchain_order_data["buy_amount"])
            conversion_external_price = int(
                external_prices[onchain_order_data["buy_token"]]
            )

        win_surplus = TemplateTest.get_order_surplus(
            executed_amount,
            buy_or_sell_amount,
            onchain_order_data["sell_token_clearing_price"],
            onchain_order_data["buy_token_clearing_price"],
            onchain_order_data["order_type"],
        )

        soln_surplus = TemplateTest.get_order_surplus(
            executed_amount,
            buy_or_sell_amount,
            clearing_prices[onchain_order_data["sell_token"]],
            clearing_prices[onchain_order_data["buy_token"]],
            onchain_order_data["order_type"],
        )
        # difference in surplus
        diff_surplus = win_surplus - soln_surplus

        percent_deviation, surplus_eth = percent_eth_conversions_order(
            diff_surplus,
            buy_or_sell_amount,
            conversion_external_price,
        )
        # divide by 10**18 to convert to ETH, consistent with quasimodo test
        surplus_eth = surplus_eth / pow(10, 18)
        return surplus_eth, percent_deviation

    def cow_endpoint_test(self, single_hash: str):
        """
        Wrapper function for the whole test. Checks if solver competition data is retrievable
        and runs EBBO test, else returns True to add to list of unchecked hashes
        """
        response_data = TemplateTest.get_solver_competition_data([single_hash])
        if len(response_data) != 0:
            self.compare_orders_surplus(response_data[0])
            return True
        return False
