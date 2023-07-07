"""
Cost coverage test for partially fillable orders.
"""
# pylint: disable=logging-fstring-interpolation

from web3.types import TxData, TxReceipt
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.orderbookapi import OrderbookAPI
from src.models import find_partially_fillable
from src.constants import (
    COST_COVERAGE_ABSOLUTE_DEVIATION_ETH,
    COST_COVERAGE_RELATIVE_DEVIATION,
)


class PartialFillCostCoverageTest(BaseTest):
    """
    Class for testing fees.
    """

    def __init__(self) -> None:
        super().__init__()
        self.web3_api = Web3API()
        self.orderbook_api = OrderbookAPI()

    def run(self, tx_hash: str) -> bool:
        """
        Given a transaction hash, check if the fee as computed for the objective covers costs for
        the batch.
        """
        # get settlement and trades via web3 api
        transaction = self.web3_api.get_transaction(tx_hash)
        if transaction is None:
            return False
        settlement = self.web3_api.get_settlement(transaction)
        trades = self.web3_api.get_trades(settlement)

        partially_fillable_indices = find_partially_fillable(trades)
        self.logger.debug(
            f"Number of partially fillable orders: {len(partially_fillable_indices)}."
        )

        # Only run test if at least one partially fillable order is in the batch.
        if len(partially_fillable_indices) > 0:
            # get additional data for the batch
            receipt = self.web3_api.get_receipt(tx_hash)
            if receipt is None:
                return False

            success = self.run_cost_coverage_test(transaction, receipt)
            if not success:
                return False

        return True

    def run_cost_coverage_test(self, transaction: TxData, receipt: TxReceipt) -> bool:
        """
        Test if the cost of a batch are close to the fees collected in that batch.
        """
        solver_competition_data = self.orderbook_api.get_solver_competition_data(
            transaction["hash"].hex()
        )
        if solver_competition_data is None:
            self.logger.debug("No competition data found. Skipping hash.")
            return False

        batch_fee = self.orderbook_api.get_settlement_fee(
            solver_competition_data["solutions"][-1]
        )
        batch_cost = self.web3_api.get_settlement_cost(transaction, receipt)

        self.check_and_log(batch_fee, batch_cost, transaction)

        return True

    def check_and_log(self, fee: int, cost: int, transaction: TxData) -> None:
        """Check tolerances and log the result."""

        a_abs = fee - cost
        a_rel = (fee - cost) / cost

        log_output = "\t".join(
            [
                "Cost coverage test",
                f"Tx hash: {transaction['hash'].hex()}",
                f"Winning Solver: {transaction['from']}",
                f"Fee: {fee * 1e-18:.5f}ETH",
                f"Cost: {cost * 1e-18:.5f}ETH",
                f"Absolute difference: {a_abs * 1e-18:.5f}ETH",
                f"Relative difference: {100 * a_rel:.2f}%",
            ]
        )

        if (
            abs(a_abs) > 1e18 * COST_COVERAGE_ABSOLUTE_DEVIATION_ETH
            or abs(a_rel) > COST_COVERAGE_RELATIVE_DEVIATION
        ):
            self.alert(log_output)
        elif (
            abs(a_abs) > 1e18 * COST_COVERAGE_ABSOLUTE_DEVIATION_ETH / 2
            or abs(a_rel) > COST_COVERAGE_RELATIVE_DEVIATION / 2
        ):
            self.logger.warning(log_output)
        elif (
            abs(a_abs) > 1e18 * COST_COVERAGE_ABSOLUTE_DEVIATION_ETH / 4
            or abs(a_rel) > COST_COVERAGE_RELATIVE_DEVIATION / 4
        ):
            self.logger.info(log_output)
        else:
            self.logger.debug(log_output)
