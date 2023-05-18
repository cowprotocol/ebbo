"""
To be completed
"""
from typing import List, Tuple, Any
import json
from copy import deepcopy
import requests
from eth_typing import HexStr
from src.monitoring_tests.template_test import TemplateTest
from src.helper_functions import (
    DecodedSettlement,
)

# this class implements the EBBO test that is using quasimodo
# the way to run the test is by calling the cow_endpoint_test() method
class QuasimodoEbboTest(TemplateTest):
    """
    To be completed
    """

    @classmethod
    def get_solver_response(
        cls, order_id: str, bucket_response: Any
    ) -> Tuple[Any, Any]:
        """
        Updates AWS bucket response to a single order for posting
        to quasimodo, in order to get the solutions JSON.
        Note that bucket_response is a dict, but wanted to bypass type checks.
        """
        solver_instance = deepcopy(bucket_response)
        order: Any = {}
        for key, order_ in solver_instance["orders"].items():
            if order_["id"] == order_id:
                solver_instance["orders"] = {key: order_}
                order = order_
                break
        # convert back to JSON as post data
        bucket_response_json = json.dumps(solver_instance)
        solver_url = "http://testnets-quasimodo-solver-staging.services.svc.cluster.local:80/solve?time_limit=20&use_internal_buffers=false&objective=surplusfeescosts"
        # solver_url = (
        #    str(TemplateTest.QUASIMODO_SOLVER_URL)
        #    + "/solve?time_limit=20&use_internal_buffers=false&objective=surplusfeescosts"
        # )
        # make solution request to quasimodo
        solution = requests.post(
            solver_url, data=bucket_response_json, timeout=30
        ).json()
        # return quasimodo solved solution
        return solution, order

    def solve_orders_in_settlement(
        self,
        bucket_response: Any,  # this is a dict, but wanted to bypass type annotation
        winning_orders: List[str],
        decoded_settlement: DecodedSettlement,
    ) -> None:
        """
        This function goes over orders in settlement,
        calculates surplus difference by making calls to
        surplus calculating functions for on-chain solution, and
        quasimodo solution.
        """
        # there can be multiple orders/trades in a single settlement
        for trade in decoded_settlement.trades:
            sell_token_clearing_price = decoded_settlement.clearing_prices[
                trade["sellTokenIndex"]
            ]
            buy_token_clearing_price = decoded_settlement.clearing_prices[
                trade["buyTokenIndex"]
            ]
            # convert flags value to binary to extract L.S.B (Least Sigificant Byte)
            # 1 implies buy order, 0 implies sell order
            order_type = str(f"{trade['flags']:08b}")[-1]
            winning_surplus = TemplateTest.get_order_surplus(
                trade["executedAmount"],
                trade["sellAmount"],
                sell_token_clearing_price,
                buy_token_clearing_price,
                order_type,
            )
            order_id = winning_orders[decoded_settlement.trades.index(trade)]["id"]
            solver_solution, order = self.get_solver_response(order_id, bucket_response)

            sell_token = order["sell_token"]
            buy_token = order["buy_token"]
            # if a valid solution is returned by solver
            if not len(solver_solution["prices"]) > 0:
                continue
            sell_token_clearing_price = solver_solution["prices"][sell_token]
            buy_token_clearing_price = solver_solution["prices"][buy_token]
            quasimodo_surplus = TemplateTest.get_order_surplus(
                trade["executedAmount"],
                trade["sellAmount"],
                sell_token_clearing_price,
                buy_token_clearing_price,
                order_type,
            )
            print("Done")
            print(winning_surplus, quasimodo_surplus)
            # TemplateTest.check_flag_condition(
            #    winning_surplus - quasimodo_surplus,
            #    trade,
            #    order_type,
            #    bucket_response["tokens"],
            #    order,
            # )

    def process_single_hash(self, settlement_hash: str) -> bool:
        """
        Goes over all orders in the winning settlement, decodes orders,
        gets response from AWS bucket, and runs the main Quasimodo test for each order.
        Returns FALSE in case data cannot be fetched, and TRUE, otherwise.
        """
        try:
            encoded_transaction = TemplateTest.web_3.eth.get_transaction(
                HexStr(settlement_hash)
            )
            decoded_settlement = DecodedSettlement.new(
                TemplateTest.contract_instance, encoded_transaction["input"]
            )
        except ValueError as except_err:
            TemplateTest.logger.error(
                "Unhandled exception, possibly can't decode: %s", str(except_err)
            )
            return False
        winning_orders = TemplateTest.get_order_data_by_hash(settlement_hash)
        auction_id = TemplateTest.get_auction_id_by_hash(settlement_hash)
        bucket_response = TemplateTest.get_instance_json_by_auction_id(auction_id)
        if bucket_response is None:
            return False
        self.solve_orders_in_settlement(
            bucket_response, winning_orders, decoded_settlement
        )
        return True

    def quasimodo_ebbo_test(self, single_hash: str) -> bool:
        """
        Wrapper function for the whole test. Returns True if the test successfully completes
        and otherwise it returns False.
        """
        return self.process_single_hash(single_hash)
