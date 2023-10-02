"""
Computing cost coverage per solver.
"""
# pylint: disable=logging-fstring-interpolation

from typing import Any, Dict
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.orderbookapi import OrderbookAPI
from src.constants import DAY_BLOCK_INTERVAL, CAP_PARAMETER


class CostCoveragePerSolverTest(BaseTest):
    """
    This test checks the following on a per solver basis:
        1. fees_collected (as perceived by solver) minus actual execution cost.
        2. total payout to solver minus fees collected.
    The intent is to gain a better understanding of which solvers are more costly,
    how much we are paying them etc.

    The results are reported once a day as a log.
    """

    def __init__(self) -> None:
        super().__init__()
        self.web3_api = Web3API()
        self.orderbook_api = OrderbookAPI()
        self.cost_coverage_per_solver: Dict[str, float] = {}
        self.total_coverage_per_solver: Dict[str, float] = {}
        self.original_block = self.web3_api.get_current_block_number()

    def cost_coverage(self, competition_data: dict[str, Any], gas_cost: float) -> bool:
        """
        This function compares the fees, as perceived by the winning solver, and the actual
        execution cost of the corresponding settlement. This is refered to as cost_coverage,
        and is supposed to monitor how well the fees end up approximating the execution cost
        of a solution.
        We also look at the coverage, from the protocol perspective, of each settlement, i.e.,
        we compare the payout made to the solver with the fees collected.
        """

        solution = competition_data["solutions"][-1]
        fees = float(int(solution["objective"]["fees"]) / 10**18)
        surplus = float(int(solution["objective"]["surplus"]) / 10**18)
        solver = solution["solver"]
        ref_score = 0.0
        if len(competition_data["solutions"]) > 1:
            second_best_sol = competition_data["solutions"][-2]
            if "score" in second_best_sol:
                ref_score_str = second_best_sol["score"]
            elif "scoreDiscounted" in second_best_sol:
                ref_score_str = second_best_sol["scoreDiscounted"]
            elif "scoreProtocolWithSolverRisk" in second_best_sol:
                ref_score_str = second_best_sol["scoreProtocolWithSolverRisk"]
            else:
                ref_score_str = second_best_sol["scoreProtocol"]
            ref_score = float(int(ref_score_str) / 10**18)
        payout = surplus + fees - ref_score
        capped_payout = min(payout, gas_cost + CAP_PARAMETER)
        if solver in self.cost_coverage_per_solver:
            self.cost_coverage_per_solver[solver] += fees - gas_cost
            self.total_coverage_per_solver[solver] += fees - capped_payout
        else:
            self.cost_coverage_per_solver[solver] = fees - gas_cost
            self.total_coverage_per_solver[solver] = fees - capped_payout

        return True

    def run(self, tx_hash: str) -> bool:
        """
        Wrapper function for the whole test. Checks if solver competition data is retrievable
        and runs test, else returns False to add to list of unchecked hashes.
        """
        solver_competition_data = self.orderbook_api.get_solver_competition_data(
            tx_hash
        )
        transaction = self.web3_api.get_transaction(tx_hash)
        receipt = self.web3_api.get_receipt(tx_hash)
        gas_cost = 0.0
        if transaction is not None and receipt is not None:
            gas_used, gas_price = self.web3_api.get_batch_gas_costs(
                transaction, receipt
            )
            gas_cost = float(gas_used) * float(gas_price) / 10**18
        if gas_cost == 0 or solver_competition_data is None:
            return False

        success = self.cost_coverage(solver_competition_data, gas_cost)

        ### This part takes care of the reporting once a day.
        current_block = self.web3_api.get_current_block_number()
        if self.original_block is None:
            self.original_block = current_block
        if current_block is None or self.original_block is None:
            return success
        if current_block - self.original_block > DAY_BLOCK_INTERVAL:
            log_msg = (
                f'"Fees - gasCost" per solver from block {self.original_block} to {current_block}: '
                + str(self.cost_coverage_per_solver)
            )
            self.logger.info(log_msg)
            log_msg = (
                f'"Fees - payment" per solver from block {self.original_block} to {current_block}: '
                + str(self.total_coverage_per_solver)
            )
            self.logger.info(log_msg)
            self.original_block = current_block
            for solver in self.cost_coverage_per_solver:
                self.cost_coverage_per_solver[solver] = 0
                self.total_coverage_per_solver[solver] = 0
        return success
