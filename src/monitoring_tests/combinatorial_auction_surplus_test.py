"""
Comparing order surplus per token pair to a reference solver in the competition.
"""
# pylint: disable=logging-fstring-interpolation
# pylint: disable=duplicate-code

from typing import Any
from fractions import Fraction
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.orderbookapi import OrderbookAPI
from src.models import Trade
from src.constants import SURPLUS_ABSOLUTE_DEVIATION_ETH, SURPLUS_REL_DEVIATION


class CombinatorialAuctionSurplusTest(BaseTest):
    """
    This test compares the surplus all orders from the winning settlement to
    the different executions of these orders by other solvers in the competition.
    """

    def __init__(self) -> None:
        super().__init__()
        self.web3_api = Web3API()
        self.orderbook_api = OrderbookAPI()

    def compare_token_pairs_surplus(self, competition_data: dict[str, Any]) -> bool:
        """
        This function goes through each token pair that the winning solution executed
        and finds non-winning solutions that executed the only orders on the same token pair.
        It then calculates surplus difference between the winning and non-winning solution.
        """

        aggregate_solutions = [
            self.get_token_pairs_surplus(
                solution, competition_data["auction"]["prices"]
            )
            for solution in competition_data["solutions"]
        ]
        aggregate_solution = aggregate_solutions[-1]

        for token_pair, token_pair_surplus in aggregate_solution.items():
            for i, aggregate_solution_alt in enumerate(aggregate_solutions[0:-1]):
                if len(aggregate_solution_alt) == 1:
                    if token_pair in aggregate_solution_alt:
                        solution = competition_data["solutions"][-1]
                        solution_alt = competition_data["solutions"][i]

                        token_pair_surplus_alt = aggregate_solution_alt[token_pair]
                        token_pair_objective_alt = Fraction(
                            Fraction(solution_alt["objective"]["total"]), 10**18
                        )

                        a_abs_eth = (
                            min(token_pair_surplus_alt, token_pair_objective_alt)
                            - token_pair_surplus
                        )
                        a_rel = a_abs_eth / token_pair_surplus

                        log_output = "\t".join(
                            [
                                "Combinatorial auction surplus test:",
                                f"Tx Hash: {competition_data['transactionHash']}",
                                f"Token pair: {token_pair}",
                                f"Winning Solver: {solution['solver']}",
                                f"Solver providing more surplus: {solution_alt['solver']}",
                                f"Relative deviation: {float(a_rel * 100):.4f}%",
                                f"Absolute difference: {float(a_abs_eth):.5f}ETH",
                            ]
                        )

                        if (
                            a_abs_eth > SURPLUS_ABSOLUTE_DEVIATION_ETH
                            and a_rel > SURPLUS_REL_DEVIATION
                        ):
                            self.alert(log_output)
                        elif (
                            a_abs_eth > SURPLUS_ABSOLUTE_DEVIATION_ETH / 10
                            and a_rel > SURPLUS_REL_DEVIATION / 10
                        ):
                            self.logger.info(log_output)
                        else:
                            self.logger.debug(log_output)

        return True

    def get_uid_trades(self, solution: dict[str, Any]) -> dict[str, Trade]:
        """Get a dictionary mapping UIDs to trades in a solution."""
        calldata = solution["callData"]
        settlement = self.web3_api.get_settlement_from_calldata(calldata)
        trades = self.web3_api.get_trades(settlement)
        trades_dict = {
            solution["orders"][i]["id"]: trade for (i, trade) in enumerate(trades)
        }
        return trades_dict

    def get_token_pairs_surplus(
        self, solution: dict[str, Any], prices: dict[str, float]
    ) -> dict[tuple[str, str], Fraction]:
        """Aggregate surplus of a solution on the different token pairs.
        The result is a dict containing token pairs and the aggregated surplus on them.
        """
        trades_dict = self.get_uid_trades(solution)
        surplus_dict: dict[tuple[str, str], Fraction] = {}
        for uid in trades_dict:
            trade = trades_dict[uid]
            token_pair = (trade.data.sell_token.lower(), trade.data.buy_token.lower())

            if trade.get_surplus_token() == trade.data.sell_token:
                token_to_eth = Fraction(
                    int(prices[token_pair[0]]),
                    10**36,
                )
            elif trade.get_surplus_token() == trade.data.buy_token:
                token_to_eth = Fraction(
                    int(prices[token_pair[1]]),
                    10**36,
                )
            surplus_dict[token_pair] = (
                surplus_dict.get(token_pair, 0) + token_to_eth * trade.get_surplus()
            )

        return surplus_dict

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

        success = self.compare_token_pairs_surplus(solver_competition_data)

        return success
