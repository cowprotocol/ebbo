"""
Comparing order surplus to a reference solution.
"""

# pylint: disable=logging-fstring-interpolation
# pylint: disable=duplicate-code

from typing import Any, Optional
from fractions import Fraction
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.orderbookapi import OrderbookAPI
from src.apis.auctioninstanceapi import AuctionInstanceAPI
from src.apis.solverapi import SolverAPI
from src.models import Trade
from src.constants import SURPLUS_ABSOLUTE_DEVIATION_ETH, SURPLUS_REL_DEVIATION


class ReferenceSolverSurplusTest(BaseTest):
    """
    This test compares the surplus of all orders from the winning settlement to
    the executions of these orders by a reference solver.
    """

    def __init__(self, web3_api: Web3API, orderbook_api: OrderbookAPI) -> None:
        super().__init__()
        self.web3_api = web3_api
        self.orderbook_api = orderbook_api
        self.auction_instance_api = AuctionInstanceAPI()
        self.solver_api = SolverAPI()

    def compare_orders_surplus(
        self, competition_data: dict[str, Any], auction_instance: dict[str, Any]
    ) -> bool:
        """
        This function goes through each order that the winning solution executed
        and compares its execution with the execution of that order by
        a reference solver.
        """

        solution = competition_data["solutions"][-1]

        trades_dict = self.get_uid_trades(solution)

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

            ref_solver_response = self.solve_order_with_reference_solver(
                uid, auction_instance
            )
            if ref_solver_response is None:
                self.logger.debug(
                    f"No reference solution for uid {uid} and "
                    f"auction id {auction_instance['metadata']['auction_id']}"
                )
                return True
            trade_alt = self.get_trade_information(
                uid, auction_instance, ref_solver_response
            )
            if trade_alt.execution.buy_amount == 0:
                continue

            a_abs = trade_alt.compare_surplus(trade)
            a_abs_eth = a_abs * token_to_eth
            a_rel = trade_alt.compare_price(trade)

            log_output = "\t".join(
                [
                    "Reference solver surplus test:",
                    f"Tx Hash: {competition_data['transactionHashes'][0]}",
                    f"Order UID: {uid}",
                    f"Winning Solver: {solution['solver']}",
                    "Solver providing more surplus: Reference solver",
                    f"Relative deviation: {float(a_rel * 100):.4f}%",
                    f"Absolute difference: {float(a_abs_eth):.5f}ETH ({a_abs} atoms)",
                ]
            )
            ref_solver_log = "\t".join(
                [
                    f"Tx Hash: {competition_data['transactionHashes'][0]}",
                    f"Order UID: {uid}",
                    f"Solution providing more surplus: {ref_solver_response}",
                ]
            )

            if (
                a_abs_eth > SURPLUS_ABSOLUTE_DEVIATION_ETH
                and a_rel > SURPLUS_REL_DEVIATION
            ):
                self.logger.info(log_output)
                self.logger.info(ref_solver_log)
            elif (
                a_abs_eth > SURPLUS_ABSOLUTE_DEVIATION_ETH / 10
                and a_rel > SURPLUS_REL_DEVIATION / 10
            ):
                self.logger.info(log_output)
            else:
                self.logger.debug(log_output)

        return True

    def solve_order_with_reference_solver(
        self, uid: str, auction_instance: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Compute solution json for an order with uid as settled by a reference solver
        given the liquidity in auction_instance.
        """
        order_auction_instance = (
            self.auction_instance_api.generate_reduced_single_order_auction_instance(
                uid, auction_instance
            )
        )
        return self.solver_api.solve_instance(order_auction_instance)

    def get_trade_information(
        self, uid: str, auction_instance: dict[str, Any], solution: dict[str, Any]
    ) -> Trade:
        """Parse execution for an order with uid as settled by a reference solver
        given the liquidity in auction_instance.
        """
        data = self.auction_instance_api.get_order_data(uid, auction_instance)
        execution = self.solver_api.get_execution_from_solution(solution)

        return Trade(data, execution)

    def get_uid_trades(self, solution: dict[str, Any]) -> dict[str, Trade]:
        """Get a dictionary mapping UIDs to trades in a solution."""
        calldata = solution["callData"]
        settlement = self.web3_api.get_settlement_from_calldata(calldata)
        trades = self.web3_api.get_trades(settlement)
        trades_dict = {
            solution["orders"][i]["id"]: trade for (i, trade) in enumerate(trades)
        }
        return trades_dict

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

        auction_id = solver_competition_data["auctionId"]

        auction_instance = self.auction_instance_api.get_auction_instance(auction_id)
        if auction_instance is None:
            return False

        success = self.compare_orders_surplus(solver_competition_data, auction_instance)

        return success
