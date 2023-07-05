"""
OrderbookAPI for fetching relevant data using the CoW Swap Orderbook API.
"""
# pylint: disable=logging-fstring-interpolation

from os import getenv
from typing import Any, Optional
import json
import requests
from dotenv import load_dotenv
from src.models import OrderExecution
from src.helper_functions import get_logger
from src.constants import (
    header,
    REQUEST_TIMEOUT,
)


class SolverAPI:
    """
    Class for querying a solver to provide alternative solutions.
    """

    def __init__(self, url: Optional[str] = None):
        self.logger = get_logger()
        if url is None:
            load_dotenv()
            self.solver_url = getenv("SOLVER_URL")

    def get_solution(
        self, auction_instance: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """
        Get solution from auction instance.
        """
        try:
            json_solution = requests.post(
                f"{self.solver_url}solve?time_limit=20&use_internal_buffers=false&objective=surplusfeescosts",
                headers=header,
                json=auction_instance,
                timeout=REQUEST_TIMEOUT,
            )
            if json_solution.ok:
                solution = json.loads(json_solution.text)
            else:
                return None
        except requests.RequestException as err:
            self.logger.warning(
                "Connection error while computing solution. "
                f"Auction ID: {auction_instance['metadata']['auction_id']}, error: {err}"
            )
            return None
        return solution

    def get_execution_from_solution(self, solution: dict[str, Any]) -> OrderExecution:
        """Get the execution of an order from solution.
        This is only implemented for the case where exactly one order is supposed to be executed.
        """
        orders = solution["orders"]
        if len(orders) == 1:
            _, order_dict = solution["orders"].popitem()
            execution = self.get_execution_from_order(order_dict)
        elif len(orders) == 0:
            self.logger.debug("Trivial solution found.")
            execution = OrderExecution(0, 0, 0)
        else:
            raise ValueError(f"Unexpected number of orders in solution: {len(orders)}.")

        return execution

    def get_execution_from_order(self, order_dict: dict[str, Any]) -> OrderExecution:
        """Get execution of an order given the order dict from a solution."""
        if order_dict["exec_fee_amount"] is None:
            fee_amount = int(order_dict["fee"]["amount"])
        else:
            fee_amount = int(order_dict["exec_fee_amount"])
        execution = OrderExecution(
            int(order_dict["exec_buy_amount"]),
            int(order_dict["exec_sell_amount"]),
            fee_amount,
        )
        return execution
