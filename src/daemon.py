"""
At runtime, "main" function records the most recent block and initializes it as the start block.
After the daemon is asleep for SLEEP_TIME_IN_SEC seconds, it gets the newest block as the end block.
Since the competition endpoint has a lag of SLEEP_TIME_IN_SEC seconds (worst case), we wait
SLEEP_TIME_IN_SEC seconds before we fetch comp. data and start running our tests.

If all tests fail, then the candidate tx hash is added to the list of unchecked hashes
to be checked in the next cycle. Once all hashes in the current cycle have been iterated through,
the previous end block + 1 becomes the start block for the next cycle, and the latest block is
the new end block. Daemon sleeps for SLEEP_TIME_IN_SEC seconds and continues checking.
"""
import time
from typing import List
from src.constants import SLEEP_TIME_IN_SEC
from src.monitoring_tests.template_test import TemplateTest
from src.monitoring_tests.competition_endpoint_test.endpoint_test import EndpointTest


def main(sleep_time: int) -> None:
    """
    daemon function that runs as highlighted in docstring.
    """
    # here, we have one object per test that we will run
    endpoind_test = EndpointTest()  # the CoW Competition Endpoint Test
    ####

    start_block = TemplateTest.get_current_block_number()
    unchecked_hashes: List[str] = []

    # main (infinite) loop
    while True:
        time.sleep(sleep_time)
        end_block = TemplateTest.get_current_block_number()
        fetched_hashes = TemplateTest.get_tx_hashes_by_block(start_block, end_block)
        all_hashes = fetched_hashes + unchecked_hashes
        unchecked_hashes = []

        while len(all_hashes) > 0:
            single_hash = all_hashes.pop(0)
            endpoint_test_success = endpoind_test.cow_endpoint_test(single_hash)
            print(endpoint_test_success)
            print(single_hash)
            if not endpoint_test_success:
                unchecked_hashes.append(single_hash)

        start_block = end_block + 1


if __name__ == "__main__":
    # sleep time can be set here in seconds
    main(SLEEP_TIME_IN_SEC)
