"""
At runtime, "main" function records the most recent block and initializes it as the start block.
After the daemon is asleep for 30 mins, it gets the newest block as the end block.
Since the competition endpoint has a lag of 30 mins (worst case), we wait 30 mins before we
fetch comp. data and start checking for potential surplus.
If the data was not retrievable for any reason, it adds it to the list of unchecked hashes
to be checked in the next cycle. Once all hashes in the current cycle have been iterated through,
the previous end block + 1 becomes the start block for the next cycle, and the latest block is
the new end block. Daemon sleeps for 30 mins and continue checking.
"""
import time
from typing import List
from web3 import Web3
import os
from dotenv import load_dotenv
from onchain import OnChainEBBO
from src.off_chain.cow_endpoint_surplus import EBBOAnalysis
from src.configuration import get_logger, get_tx_hashes_by_block

load_dotenv()
INFURA_KEY = os.getenv("INFURA_KEY")


class DaemonEBBO:
    """
    Initialization of EBBOAnalysis class object and logger object.
    """

    def __init__(self):
        self.quasimodo_test_instance = OnChainEBBO()
        self.cow_endpoint_test_instance = EBBOAnalysis()
        self.logger = get_logger()

    def main(self, sleep_time: int) -> None:
        """
        daemon function that runs as highlighted in docstring.
        """
        infura_connection = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
        web_3 = Web3(Web3.HTTPProvider(infura_connection))
        start_block = web_3.eth.block_number
        print("starting...")
        unchecked_hashes: List[str] = []
        while True:
            time.sleep(sleep_time)
            end_block = web_3.eth.block_number
            fetched_hashes = get_tx_hashes_by_block(start_block, end_block)
            all_hashes = fetched_hashes + unchecked_hashes
            unchecked_hashes = []
            while len(all_hashes) > 0:
                single_hash = all_hashes.pop(0)
                if self.onchain_quasimodo_test(single_hash) or self.cow_endpoint_test(
                    single_hash
                ):
                    unchecked_hashes.append(single_hash)
            self.logger.info("going to sleep...")
            start_block = end_block + 1

    def onchain_quasimodo_test(self, single_hash):
        return self.quasimodo_test_instance.decode_single_hash(single_hash) is None

    def cow_endpoint_test(self, single_hash):
        response_data = self.cow_endpoint_test_instance.get_solver_competition_data(
            [single_hash]
        )
        if len(response_data) != 0:
            self.cow_endpoint_test_instance.get_order_surplus(response_data[0])
            return False
        else:
            return True


if __name__ == "__main__":
    checker = DaemonEBBO()
    # sleep time can be set here in seconds
    checker.main(600)
