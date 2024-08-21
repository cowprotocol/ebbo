"""
API for calling an http solver with auction instances.
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
    SOLVER_TIME_LIMIT,
)


class SolverAPI:
    """
    Class for querying a solver to provide alternative solutions.
    """

    def __init__(self, url: Optional[str] = None) -> None:
        self.logger = get_logger()
        if url is None:
            load_dotenv()
            self.solver_url = getenv("QUASIMODO_SOLVER_URL")
            if self.solver_url is not None:
                self.solver_url = self.solver_url.replace("prod", "staging")

    def solve_instance(
        self, auction_instance: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """
        Get solution from auction instance.
        """
        solution: Optional[dict[str, Any]] = None
        try:
            json_solution = requests.post(
                f"{self.solver_url}/solve?time_limit={SOLVER_TIME_LIMIT}&use_internal_buffers=false"
                "&objective=surplusfeescosts",
                headers=header,
                json=auction_instance,
                timeout=SOLVER_TIME_LIMIT + REQUEST_TIMEOUT,
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

        This method cannot handle the case of additional liquidity orders in the auction. If this
        is desired, the logic for extracting the surplus capturing order needs to be modified.
        """
        orders = solution["orders"]
        if len(orders) == 1:
            (order_dict,) = solution["orders"].values()
            execution = self.get_execution_from_order(order_dict)
        elif len(orders) == 0:
            self.logger.debug("Trivial solution found.")
            execution = OrderExecution(0, 0, 0)
        else:
            raise ValueError(f"Unexpected number of orders in solution: {len(orders)}.")

        return execution

    def get_execution_from_order(self, order_dict: dict[str, Any]) -> OrderExecution:
        """Get execution of an order given the order dict from a solution."""
        fee_amount = fee_amount = order_dict.get(
            "exec_fee_amount", int(order_dict["fee"]["amount"])
        )

        execution = OrderExecution(
            int(order_dict["exec_buy_amount"]),
            int(order_dict["exec_sell_amount"]),
            fee_amount,
        )
        return execution
