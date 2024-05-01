"""
Comparing order surplus per token pair to a reference solver in the competition.
"""

# pylint: disable=logging-fstring-interpolation
# pylint: disable=duplicate-code

from typing import Any
from fractions import Fraction
from src.monitoring_tests.base_test import BaseTest
from src.apis.orderbookapi import OrderbookAPI
from src.constants import (
    SURPLUS_ABSOLUTE_DEVIATION_ETH,
    COMBINATORIAL_AUCTION_ABSOLUTE_DEVIATION_ETH,
)


class CombinatorialAuctionSurplusTest(BaseTest):
    """Test how a combinatorial auction would have settled the auction.
    This test implements a logic for a combinatorial auction and compares the result to what
    actually happened.

    The combinatorial auction goes as follows:
    - Aggregate surplus on the different directed sell token-buy token pairs for all solutions in
      the competition.
    - Compute a baseline for surplus on all token pairs from those solutions.
    - Filter solutions which do not provide at least as much surplus as the baseline on all token
      pairs that the solution contains.
    - Choose one batch winner and multiple single order winners.

    The test logs an output whenever
    - the winner of the solver competition would have been filtered out in a combinatorial auction
      or
    - the total surplus in a combinatorial auction would have been significantly larger than it was
      with our current mechanism.
    """

    def __init__(self) -> None:
        super().__init__()
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

        aggregate_solutions: list[dict[tuple[str, str], Fraction]] = []
        for solution in solutions:
            aggregate_solution = self.get_token_pairs_surplus(
                solution, competition_data["auction"]["prices"]
            )
            if aggregate_solution is None:
                return False
            aggregate_solutions.append(aggregate_solution)

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
            if i in [ind for ind, _ in filter_mask[-1]]
        ]

        total_combinatorial_surplus = sum(
            sum(surplus for _, surplus in token_pair_surplus.items())
            for _, token_pair_surplus in winning_solvers.items()
        )
        total_surplus = sum(surplus for _, surplus in aggregate_solutions[-1].items())

        a_abs_eth = total_combinatorial_surplus - total_surplus

        log_output = "\t".join(
            [
                "Combinatorial auction surplus test:",
                f"Tx Hash: {competition_data['transactionHash']}",
                f"Winning Solver: {competition_data['solutions'][-1]['solver']}",
                f"Winning surplus: {self.convert_fractions_to_floats(aggregate_solutions[-1])}",
                f"Baseline surplus: {self.convert_fractions_to_floats(baseline_surplus)}",
                f"Solutions filtering winner: {self.convert_fractions_to_floats(filter_mask[-1])}",
                f"Solvers filtering winner: {solutions_filtering_winner}",
                f"Combinatorial winners: {self.convert_fractions_to_floats(winning_solvers)}",
                f"Total surplus: {float(total_surplus):.5f} ETH",
                f"Combinatorial surplus: {float(total_combinatorial_surplus):.5f} ETH",
                f"Absolute difference: {float(a_abs_eth):.5f}ETH",
            ]
        )

        if any(
            solutions[ind]["solver"] == "baseline"
            and surplus_difference > COMBINATORIAL_AUCTION_ABSOLUTE_DEVIATION_ETH
            for ind, surplus_difference in filter_mask[-1]
        ):
            self.alert(log_output)
        elif (
            a_abs_eth > SURPLUS_ABSOLUTE_DEVIATION_ETH / 10
            or not len(filter_mask[-1]) == 0
        ):
            self.logger.info(log_output)
        else:
            self.logger.debug(log_output)

        return True

    def get_token_pairs_surplus(
        self, solution: dict[str, Any], prices: dict[str, float]
    ) -> dict[tuple[str, str], Fraction] | None:
        """Aggregate surplus of a solution on the different token pairs.
        The result is a dict containing directed token pairs and the aggregated surplus on them.
        """
        trades_dict = self.orderbook_api.get_uid_trades(solution)
        if trades_dict is None:
            return None

        surplus_dict: dict[tuple[str, str], Fraction] = {}
        for uid in trades_dict:
            trade = trades_dict[uid]
            token_pair = (trade.data.sell_token.lower(), trade.data.buy_token.lower())

            # compute the conversion rate of the surplus token to ETH
            if trade.get_surplus_token() == trade.data.buy_token:  # sell order
                surplus_token_to_eth = Fraction(
                    int(prices[token_pair[1]]),
                    10**36,
                )
            else:  # buy order
                surplus_token_to_eth = Fraction(
                    int(prices[token_pair[0]]),
                    10**36,
                )

            surplus_dict[token_pair] = (
                surplus_dict.get(token_pair, 0)
                + surplus_token_to_eth * trade.get_surplus()
            )

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
                # extract the single key-value pair from the aggregate_solution dict
                ((token_pair, surplus),) = aggregate_solution.items()
                # get the previous best surplus or zero (with dummy index -1 which is not accessed)
                surplus_old = result.get(token_pair, (0, -1))[0]
                # if surplus is larger than previously best surplus, overwrite entry in result
                if surplus > surplus_old:
                    result[token_pair] = (surplus, i)
        return result

    def filter_solutions(
        self,
        aggregate_solutions: list[dict[tuple[str, str], Fraction]],
        baseline_surplus: dict[tuple[str, str], tuple[Fraction, int]],
    ) -> list[list[tuple[int, Fraction]]]:
        """Check which baseline solutions filter out solutions.
        Only solutions are considered for ranking that supply more surplus than any of the single
        aggregate order solutions on all directed token pairs they touch.
        For each solution a list of tuples is returned. The first entry of each tuple is an integer
         corresponding to the index of a baseline solution would have resulted in filtering of the
        given solution. The second entry is the difference in surplus of the filtered and filtering
        solution.
        This information is used e.g. to trigger alerts depending on which solver resulted in
        filtering.
        """
        result: list[list[tuple[int, Fraction]]] = []
        for aggregate_solution in aggregate_solutions:
            flag = []
            for token_pair, surplus in aggregate_solution.items():
                if token_pair in baseline_surplus:
                    surplus_ref, solution_index = baseline_surplus[token_pair]
                    if surplus < surplus_ref:
                        flag.append((solution_index, surplus_ref - surplus))
            result.append(flag)

        return result

    def determine_winning_solutions(
        self,
        aggregate_solutions: list[dict[tuple[str, str], Fraction]],
        baseline_surplus: dict[tuple[str, str], tuple[Fraction, int]],
        filter_mask: list[list[tuple[int, Fraction]]],
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

    def convert_fractions_to_floats(self, obj: Any, precision: int = 4) -> Any:
        """Convert fractions in nested object to rounded floats.
        This function is only used for logging.
        """
        if isinstance(obj, dict):
            return {
                k: self.convert_fractions_to_floats(v, precision)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [self.convert_fractions_to_floats(v, precision) for v in obj]
        if isinstance(obj, tuple):
            return tuple(self.convert_fractions_to_floats(x, precision) for x in obj)
        if isinstance(obj, Fraction):
            return round(float(obj), precision)
        return obj

    def run(self, tx_hash: str) -> bool:
        """Runs the combinatoral auction surplus test
        Wrapper function for the whole test. Checks if solver competition data is retrievable
        and runs the test, else returns False to add to list of unchecked hashes.
        """

        solver_competition_data = self.orderbook_api.get_solver_competition_data(
            tx_hash
        )
        if solver_competition_data is None:
            return False

        success = self.run_combinatorial_auction(solver_competition_data)

        return success
