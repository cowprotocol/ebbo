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
import os
from typing import List, Optional
from dotenv import load_dotenv
from web3 import Web3
from src.off_chain.cow_endpoint_surplus import EBBOAnalysis
from src.off_chain.configuration import get_logger

load_dotenv()
INFURA_KEY = os.getenv("INFURA_KEY")


class DaemonEBBO:
    """
    Initialization of EBBOAnalysis class object and logger object.
    """

    def __init__(self, file_name: Optional[str] = None):
        self.instance = EBBOAnalysis()
        self.logger = get_logger(f"{file_name}")

    def main(self, sleep_time: int) -> None:
        """
        daemon function that runs as highlighted in docstring.
        """
        infura_connection = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
        web_3 = Web3(Web3.HTTPProvider(infura_connection))
        start_block = int(web_3.eth.block_number)
        # self.logger.info("starting...")
        unchecked_hashes: List[str] = []
        while True:
            time.sleep(sleep_time)
            end_block = web_3.eth.block_number
            fetched_hashes = self.instance.get_settlement_hashes(start_block, end_block)
            all_hashes = fetched_hashes + unchecked_hashes
            unchecked_hashes = []
            while len(all_hashes) > 0:
                single_hash = all_hashes.pop(0)
                response_data = self.instance.get_solver_competition_data([single_hash])
                if len(response_data) != 0:
                    self.instance.get_order_surplus(response_data[0])
                else:
                    unchecked_hashes.append(single_hash)

            # self.logger.info("going to sleep...")
            start_block = end_block + 1


if __name__ == "__main__":
    checker = DaemonEBBO()
    # sleep time can be set here in seconds
    checker.main(300)
