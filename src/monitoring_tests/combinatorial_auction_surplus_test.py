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
from src.constants import SURPLUS_ABSOLUTE_DEVIATION_ETH


class CombinatorialAuctionSurplusTest(BaseTest):
    """Test how a combinatorial auctions would have settled the auction.
    This test implements a logic for a combinatorial auction and compares the result to what
    actually happened.

    The combinatorial auction goes as follows:
    - Aggregate surplus on the different directed sell token-buy token pairs for all solutions in
      the competition.
    - Compute a baseline for surplus on all token pairs from those solutions.
    - Filter solutions which to not provide at least as much surplus as the baseline on all token
      pairs.
    - Choose one batch winner and multiple single order winners.

    The test logs an output whenever
    - the winner of the solver competition would have been filtered out in a combinatorial auction
      or
    - the total surplus in a combinatorial auction would have been significantly larger than it was
      with our current mechanism.
    """

    def __init__(self) -> None:
        super().__init__()
        self.web3_api = Web3API()
        self.orderbook_api = OrderbookAPI()

    def run_combinatorial_auction(self, competition_data: dict[str, Any]) -> bool:
        """Run combinatorial auction on competition data.

        The combinatorial auction consists of 4 steps:
        1. Aggregate surplus on the different directed sell token-buy token pairs for all solutions
           in the competition.
        2. Compute a baseline for surplus on all token pairs from those solutions.
        3. Filter solutions which to not provide at least as much surplus as the baseline on all
           token pairs.
        4. Choose one batch winner and multiple single order winners.
        """

        solutions = competition_data["solutions"]
        solution = competition_data["solutions"][-1]

        aggregate_solutions = [
            self.get_token_pairs_surplus(
                solution, competition_data["auction"]["prices"]
            )
            for solution in solutions
        ]
        aggregate_solution = aggregate_solutions[-1]

        baseline_surplus = self.compute_baseline_surplus(aggregate_solutions)
        filter_mask = self.filter_solutions(aggregate_solutions, baseline_surplus)
        winning_solutions = self.determine_winning_solutions(
            aggregate_solutions, baseline_surplus, filter_mask
        )
        winning_solvers = self.determine_winning_solvers(
            solutions, aggregate_solutions, winning_solutions
        )

        solutions_filtering_winner = [
            solution["solver"]
            for i, solution in enumerate(solutions)
            if i in filter_mask[-1]
        ]

        total_combinatorial_surplus = sum(
            sum(surplus for _, surplus in token_pair_surplus.items())
            for _, token_pair_surplus in winning_solvers.items()
        )
        total_surplus = sum(surplus for _, surplus in aggregate_solution.items())

        a_abs_eth = total_combinatorial_surplus - total_surplus

        log_output = "\t".join(
            [
                "Combinatorial auction surplus test:",
                f"Tx Hash: {competition_data['transactionHash']}",
                f"Winning Solver: {solution['solver']}",
                f"Winning surplus: {aggregate_solution}",
                f"Baseline surplus: {baseline_surplus}",
                f"Solutions filtering winner: {filter_mask[-1]}",
                f"Solvers filtering winner: {solutions_filtering_winner}",
                f"Combinatorial winners: {winning_solvers}",
                f"Total surplus: {float(total_surplus):.5f} ETH",
                f"Combinatorial surplus: {float(total_combinatorial_surplus):.5f} ETH",
                f"Absolute difference: {float(a_abs_eth):.5f}ETH",
            ]
        )
        if a_abs_eth > SURPLUS_ABSOLUTE_DEVIATION_ETH:
            self.alert(log_output)
        elif (
            a_abs_eth > SURPLUS_ABSOLUTE_DEVIATION_ETH / 10
            or not len(filter_mask[-1]) == 0
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
        The result is a dict containing directed token pairs and the aggregated surplus on them.

        Instead of surplus we use the minimum of surplus and the objective. This is more
        conservative than just using objective. If fees are larger than costs, the objective is
        larger than surplus and surplus is used for the comparison. If fees are larger than costs,
        the objective is smaller than surplus and the objective is used instead of surplus for
        filtering. This takes care of the case of solvers providing a lot of surplus but at really
        large costs.
        """
        trades_dict = self.get_uid_trades(solution)
        surplus_dict: dict[tuple[str, str], Fraction] = {}
        for uid in trades_dict:
            trade = trades_dict[uid]
            token_pair = (trade.data.sell_token.lower(), trade.data.buy_token.lower())

            # compute the conversion rate of the surplus token to ETH
            if trade.get_surplus_token() == trade.data.sell_token:
                surplus_token_to_eth = Fraction(
                    int(prices[token_pair[0]]),
                    10**36,
                )
            elif trade.get_surplus_token() == trade.data.buy_token:
                surplus_token_to_eth = Fraction(
                    int(prices[token_pair[1]]),
                    10**36,
                )

            surplus_dict[token_pair] = (
                surplus_dict.get(token_pair, 0)
                + surplus_token_to_eth * trade.get_surplus()
            )

        # use the minimum of surplus and objective in case there is only one token pair
        if len(surplus_dict) == 1:
            for token_pair in surplus_dict:
                surplus_dict[token_pair] = min(
                    surplus_dict[token_pair], solution["objective"]["total"]
                )
                # surplus_dict[token_pair] = solution["objective"]["total"]

        return surplus_dict

    def compute_baseline_surplus(
        self, aggregate_solutions: list[dict[tuple[str, str], Fraction]]
    ) -> dict[tuple[str, str], tuple[Fraction, int]]:
        """Computes baseline surplus for all token pairs.
        The baseline is computed from those solutions which only contain orders for a single token
        pair.
        The result is a dict containing directed token pairs and the aggregated surplus on them as
        well as the index of the corresponding solution in the solutions list.
        """
        result: dict[tuple[str, str], tuple[Fraction, int]] = {}
        for i, aggregate_solution in enumerate(aggregate_solutions):
            if len(aggregate_solution) == 1:
                token_pair, surplus = list(aggregate_solution.items())[0]
                surplus_old = result.get(token_pair, (0, -1))[0]
                if surplus > surplus_old:
                    result[token_pair] = (surplus, i)
        return result

    def filter_solutions(
        self,
        aggregate_solutions: list[dict[tuple[str, str], Fraction]],
        baseline_surplus: dict[tuple[str, str], tuple[Fraction, int]],
    ) -> list[list[int]]:
        """Filter out solutions which do not provide enough surplus.
        Only solutions are considered for ranking that supply more surplus than any of the single
        aggregate order solutions. The function returns a list of bools where False means the
        solution is filtered out.
        """
        result: list[list[int]] = []
        for aggregate_solution in aggregate_solutions:
            flag = []
            for token_pair, surplus in aggregate_solution.items():
                surplus_ref, solution_index = baseline_surplus.get(token_pair, (0, -1))
                if surplus < surplus_ref:
                    flag.append(solution_index)
            result.append(flag)

        return result

    def determine_winning_solutions(
        self,
        aggregate_solutions: list[dict[tuple[str, str], Fraction]],
        baseline_surplus: dict[tuple[str, str], tuple[Fraction, int]],
        filter_mask: list[list[int]],
    ) -> dict[tuple[str, str], int]:
        """Determine the winning solutions for the different token pairs.
        There is one batch winner, and the remaining token pairs are won by single aggregate order
        solutions.
        """
        result: dict[tuple[str, str], int] = {}
        # one batch winner
        for i, _ in reversed(list(enumerate(aggregate_solutions))):
            if len(filter_mask[i]) == 0:
                batch_winner_index = i
                break
        for token_pair, _ in aggregate_solutions[batch_winner_index].items():
            result[token_pair] = batch_winner_index
        # the remaining token pairs are won by baseline solutions
        for token_pair, surplus_and_index in baseline_surplus.items():
            if not token_pair in result:
                result[token_pair] = surplus_and_index[1]
        return result

    def determine_winning_solvers(
        self,
        solutions: list[dict[str, Any]],
        aggregate_solutions: list[dict[tuple[str, str], Fraction]],
        winning_solutions: dict[tuple[str, str], int],
    ) -> dict[str, dict[tuple[str, str], Fraction]]:
        """Determine the winning solvers and the surplus for each token pair.
        There is one batch winner, and the remaining token pairs are won by single aggregate order
        solutions.
        """
        result: dict[str, dict[tuple[str, str], Fraction]] = {}
        for token_pair, solution_index in winning_solutions.items():
            solution = solutions[solution_index]
            solver = solution["solver"]
            if not solver in result:
                result[solver] = {}
            result[solver][token_pair] = aggregate_solutions[solution_index][token_pair]
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

        success = self.run_combinatorial_auction(solver_competition_data)

        return success
