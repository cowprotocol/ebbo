"""
A daemon to run tests on settlements. An infinite loop is started which listens to settlement events. If such an event happens, tests are added to an execution pool.
"""
# pylint: disable=logging-fstring-interpolation

import time
from src.apis.web3api import Web3API
from src.monitoring_tests.partially_fillable_fee_quote_test import (
    PartialFillFeeQuoteTest,
)
from src.monitoring_tests.partially_fillable_cost_coverage_test import (
    PartialFillCostCoverageTest,
)
from src.constants import SLEEP_TIME_IN_SEC


def main() -> None:
    """
    daemon function that runs as highlighted in docstring.
    """
    web3_api = Web3API()

    # initialize tests
    tests = [
        PartialFillFeeQuoteTest(),
        PartialFillCostCoverageTest(),
    ]

    start_block = web3_api.get_current_block_number()
    if start_block is None:
        return

    web3_api.logger.debug("Start infinite loop")
    while True:
        time.sleep(SLEEP_TIME_IN_SEC)
        end_block = web3_api.get_current_block_number()
        if end_block is None:
            continue
        tx_hashes = web3_api.get_tx_hashes_by_block(start_block, end_block)

        web3_api.logger.debug(f"{len(tx_hashes)} hashes found: {tx_hashes}")
        for test in tests:
            test.add_hashes_to_queue(tx_hashes)
            web3_api.logger.debug(f"Running test ({test}) for hashes {test.tx_hashes}.")
            test.run_queue()
            web3_api.logger.debug("Test completed.")

        start_block = end_block + 1


if __name__ == "__main__":
    # sleep time can be set here in seconds
    main()
