"""
TenderlyAPI for simulating transactions on tenderly.
"""
# pylint: disable=logging-fstring-interpolation

from os import getenv
from typing import Any, Optional
import requests
from dotenv import load_dotenv
from src.helper_functions import get_logger
from src.constants import (
    SETTLEMENT_CONTRACT_ADDRESS,
    REQUEST_TIMEOUT,
)


class TenderlyAPI:
    """
    Class for simulating transactions on tenderly.
    """

    def __init__(self) -> None:
        self.logger = get_logger()
        load_dotenv()
        self.node_url = "https://mainnet.gateway.tenderly.co/" + str(
            getenv("TENDERLY_NODE_ACCESS_KEY")
        )
        self.simulation_url = (
            "https://api.tenderly.co/api/v1/account/"
            + str(getenv("TENDERLY_USER"))
            + "/project/"
            + str(getenv("TENDERLY_PROJECT"))
            + "/simulate"
        )

    def trace_transaction(self, tx_hash: str) -> dict[str, Any] | None:
        """Get trace for given hash"""
        trace_input = {
            "id": 0,
            "jsonrpc": "2.0",
            "method": "tenderly_traceTransaction",
            "params": [tx_hash],
        }

        trace_output: dict[str, Any] | None = None
        try:
            json_trace_output = requests.post(
                self.node_url,
                headers={
                    "Content-Type": "application/json",
                },
                timeout=REQUEST_TIMEOUT,
                json=trace_input,
            )
            if json_trace_output.ok:
                trace_output = json_trace_output.json()
            else:
                return None
        except requests.RequestException as err:
            self.logger.warning(
                f"Error while simulating transaction.\
                    Simulation input: {trace_input}, error: {err}"
            )
            return None
        return trace_output

    def simulate_solution(
        self, solution: dict[str, Any], block_number: int, internalize: bool = True
    ) -> Optional[dict[str, Any]]:
        """Simulate a solution from the solver competition at a specified block number.
        The solution dictionary follows the convention from the competition endpoint.
        If internalize == False, uninternalized calldata is used for the simulation if it exists.
        """
        if not internalize and "uninternalizedCallData" in solution:
            calldata = solution["uninternalizedCallData"]
        else:
            calldata = solution["callData"]

        return self.simulate_calldata(calldata, solution["solverAddress"], block_number)

    def simulate_calldata(
        self, calldata: str, solver: str, block_number: int
    ) -> Optional[dict[str, Any]]:
        """Simulate a transaction from solver with given calldata at a specified block number."""

        simulation_output: Optional[dict[str, Any]] = None
        try:
            simulation_input = {
                "save": True,  # if true simulation is saved and shows up in the dashboard
                "save_if_fails": True,  # if true, reverting simulations show up in the dashboard
                "simulation_type": "quick",  # full or quick (full is default)
                # network to simulate on
                "network_id": "1",
                # simulate transaction at this (historical) block number
                "block_number": block_number,
                # simulate transaction at this index within the (historical) block
                # "transaction_index": 0,
                # Standard EVM Transaction object
                "from": solver,
                "input": calldata,
                "to": SETTLEMENT_CONTRACT_ADDRESS,
                # "gas": 138864,
                # "gas_price": "32909736476",
                "value": "0",
                # "access_list": [],
                # "generate_access_list": True,
            }

            json_simulation_output = requests.post(
                self.simulation_url,
                headers={
                    "X-Access-Key": str(getenv("TENDERLY_ACCESS_KEY")),
                },
                timeout=REQUEST_TIMEOUT,
                json=simulation_input,
            )
            if json_simulation_output.ok:
                simulation_output = json_simulation_output.json()
            else:
                return None
        except requests.RequestException as err:
            self.logger.warning(
                f"Error while simulating transaction.\
                    Simulation input: {simulation_input}, error: {err}"
            )
            return None
        return simulation_output
