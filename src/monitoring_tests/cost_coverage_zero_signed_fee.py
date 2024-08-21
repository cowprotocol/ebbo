"""
Computing cost coverage per solver.
"""

# pylint: disable=logging-fstring-interpolation

from typing import Any, Dict
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.orderbookapi import OrderbookAPI


class CostCoverageForZeroSignedFee(BaseTest):
    """
    This test checks the cost coverage of in-market orders that are
    sent as zero-signed fee orders from CoW Swap.
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
        """

        solution = competition_data["solutions"][-1]
        ucp = solution["clearingPrices"]
        orders = solution["orders"]
        native_prices = competition_data["auction"]["prices"]
        total_fee = 0.0
        for order in orders:
            order_data = self.orderbook_api.get_order_data(order["id"])
            if order_data is None:
                return False
            sell_token = order_data["sellToken"]
            buy_token = order_data["buyToken"]

            fee = (
                (
                    int(order["sellAmount"])
                    - int(order["buyAmount"])
                    * int(ucp[buy_token])
                    / int(ucp[sell_token])
                )
                * int(native_prices[sell_token])
                / 10**36
            )
            total_fee += fee
        if total_fee - gas_cost > 0.02:
            self.alert(
                f'"Fees - gasCost" is {total_fee - gas_cost} \
                    for {competition_data["transactionHash"]}.'
            )
        elif total_fee - gas_cost < -0.04:
            self.logger.info(
                f'"Fees - gasCost" is {total_fee - gas_cost} \
                for {competition_data["transactionHash"]}.'
            )
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

        return success
