""" A daemon to run tests on settlements.
An infinite loop is started which listens to CoW Protocol trade events. If such an event happens,
the correstonding transaction hash is added to the queue of the individual tests.

If a settlement failes a test, an error level message is logged.
"""
# pylint: disable=logging-fstring-interpolation

import time
from typing import Optional
from src.apis.web3api import Web3API
from src.monitoring_tests.solver_competition_surplus_test import (
    SolverCompetitionSurplusTest,
)
from src.monitoring_tests.reference_solver_surplus_test import (
    ReferenceSolverSurplusTest,
)
from src.monitoring_tests.mev_blocker_kickbacks_test import (
    MEVBlockerRefundsMonitoringTest,
)
from src.monitoring_tests.buffers_monitoring_test import (
    BuffersMonitoringTest,
)
from src.monitoring_tests.combinatorial_auction_surplus_test import (
    CombinatorialAuctionSurplusTest,
)
from src.monitoring_tests.uniform_directed_prices_test import (
    UniformDirectedPricesTest,
)
from src.constants import SLEEP_TIME_IN_SEC


def main() -> None:
    """
    daemon function that runs as highlighted in docstring.
    """
    web3_api = Web3API()

    # initialize tests
    tests = [
        SolverCompetitionSurplusTest(),
        ReferenceSolverSurplusTest(),
        MEVBlockerRefundsMonitoringTest(),
        BuffersMonitoringTest(),
        CombinatorialAuctionSurplusTest(),
        UniformDirectedPricesTest(),
    ]

    start_block: Optional[int] = None

    web3_api.logger.debug("Start infinite loop")
    while True:
        time.sleep(SLEEP_TIME_IN_SEC)
        if start_block is None:
            start_block = web3_api.get_current_block_number()
            continue
        end_block = web3_api.get_current_block_number()
        if end_block is None:
            continue

        tx_hashes = web3_api.get_tx_hashes_by_block(start_block, end_block)
        if not tx_hashes:
            continue

        web3_api.logger.debug(f"{len(tx_hashes)} hashes found: {tx_hashes}")
        for test in tests:
            test.add_hashes_to_queue(tx_hashes)
            web3_api.logger.debug(f"Running test ({test}) for hashes {test.tx_hashes}.")
            test.run_queue()
            web3_api.logger.debug(f"Test ({test}) completed.")

        start_block = end_block + 1


if __name__ == "__main__":
    # sleep time can be set here in seconds
    main()
