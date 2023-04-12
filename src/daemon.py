"""
At runtime, "main" function records the most recent block and initializes it as the start block.
After the daemon is asleep for 30 mins, it gets the newest block as the end block.
Since the competition endpoint has a lag of 30 mins (worst case), we wait 30 mins before we
fetch comp. data and start checking for potential surplus.
If the data was not retrievable for any reason, it adds it to the list of unchecked hashes
to be checked in the next cycle. Once all hashes in the current cycle have been iterated through,
the previous end block + 1 becomes the start block for the next cycle, and the latest block is
the new end block. Daemon sleeps for 30 mins and continues checking.
"""
import time
from typing import List, Optional
from web3 import Web3
from config import INFURA_KEY
from src.off_chain.cow_endpoint_surplus import EBBOAnalysis
from src.off_chain.configuration import get_logger


class DaemonEBBO:
    """
    Initialization of EBBOAnalysis class object and logger object.
    """

    def __init__(self, file_name: Optional[str] = None):
        self.Instance = EBBOAnalysis()
        self.logger = get_logger(f"{file_name}")

    def main(self, sleep_time: int) -> None:
        """
        daemon function that runs as highlighted in docstring.
        """
        infura_connection = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
        w3 = Web3(Web3.HTTPProvider(infura_connection))
        start_block = w3.eth.block_number
        time.sleep(sleep_time)
        self.logger.info("starting...")
        end_block = w3.eth.block_number
        unchecked_hashes: List[str] = []
        while True:
            time.sleep(sleep_time)
            fetched_hashes = self.Instance.get_settlement_hashes(start_block, end_block)
            all_hashes = fetched_hashes + unchecked_hashes
            unchecked_hashes = []
            while len(all_hashes) > 0:
                single_hash = all_hashes[0]
                single_hash_list: List[str] = []
                single_hash_list.append(single_hash)
                response_data = self.Instance.get_solver_competition_data(
                    single_hash_list
                )
                all_hashes.pop(0)
                if len(response_data) != 0:
                    self.Instance.get_order_surplus(response_data[0])
                else:
                    unchecked_hashes.append(single_hash)

            self.logger.info("going to sleep...")
            start_block = end_block + 1
            end_block = w3.eth.block_number


if __name__ == "__main__":
    checker = DaemonEBBO()
    checker.main(30)
