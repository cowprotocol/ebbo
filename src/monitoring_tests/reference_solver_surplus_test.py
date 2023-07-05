"""
Comparing order surplus to a reference solution.
"""
# pylint: disable=logging-fstring-interpolation

from typing import Any, Optional
from fractions import Fraction
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.orderbookapi import OrderbookAPI
from src.apis.auctioninstanceapi import AuctionInstanceAPI
from src.apis.solverapi import SolverAPI
from src.models import Trade
from src.constants import ABSOLUTE_ETH_FLAG_AMOUNT, REL_DEVIATION_FLAG_PERCENT


class ReferenceSolverSurplusTest(BaseTest):
    """
    This test compares the surplus all orders from the winning settlement to
    the executions of these orders by a reference solver.
    """

    def __init__(self):
        super().__init__()
        self.web3_api = Web3API()
        self.orderbook_api = OrderbookAPI()
        self.auction_instance_api = AuctionInstanceAPI()
        self.solver_api = SolverAPI()

    def compare_orders_surplus(
        self, competition_data: dict[str, Any], auction_instance: dict[str, Any]
    ) -> bool:
        """
        This function goes through each order that the winning solution executed
        and finds non-winning solutions that executed the same order and
        calculates surplus difference between that pair (winning and non-winning solution).
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

            trade_alt = self.get_trade_alternative(uid, auction_instance)
            if trade_alt is None:
                self.logger.debug(
                    f"No alternative trade for uid {uid} and "
                    f"auction id {auction_instance['metadata']['auction_id']}"
                )
                return False

            a_abs = trade_alt.compare_surplus(trade)
            a_abs_eth = a_abs * token_to_eth
            a_rel = trade_alt.compare_price(trade)

            log_output = "\t".join(
                [
                    "Reference solver surplus test:",
                    f"Tx Hash: {competition_data['transactionHash']}",
                    f"Order UID: {uid}",
                    f"Winning Solver: {solution['solver']}",
                    "Solver providing more surplus: Reference solver",
                    f"Relative deviation: {float(a_rel * 100):.4f}%",
                    f"Absolute difference: {float(a_abs_eth):.5f}ETH ({a_abs} atoms)",
                ]
            )

            if (
                a_abs_eth > ABSOLUTE_ETH_FLAG_AMOUNT
                and a_rel * 100 > REL_DEVIATION_FLAG_PERCENT
            ):
                self.alert(log_output)
            elif (
                a_abs_eth > ABSOLUTE_ETH_FLAG_AMOUNT / 2
                and a_rel * 100 > REL_DEVIATION_FLAG_PERCENT / 2
            ):
                self.logger.info(log_output)
            else:
                self.logger.debug(log_output)

        return True

    def get_trade_alternative(
        self, uid: str, auction_instance: dict[str, Any]
    ) -> Optional[Trade]:
        """Compute alternative execution for an order with uid as settled by a referefernce solver
        given the liquidity in auction_instance.
        """
        data = self.auction_instance_api.get_order_data(uid, auction_instance)
        order_auction_instance = self.auction_instance_api.get_order_auction_instance(
            uid, auction_instance
        )

        solution = self.solver_api.get_solution(order_auction_instance)
        if solution is None:
            self.logger.debug(
                f"No reference solution for uid {uid} and "
                f"auction id {auction_instance['metadata']['auction_id']}"
            )
            return None
        execution = self.solver_api.get_execution(solution)

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

        auction_id = solver_competition_data["auctionId"]

        auction_instance = self.auction_instance_api.get_auction_instance(auction_id)
        if auction_instance is None:
            return False

        success = self.compare_orders_surplus(solver_competition_data, auction_instance)

        return success
