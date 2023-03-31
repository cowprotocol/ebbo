import time
from typing import List, Union
from cow_endpoint_surplus import EBBOHistoricalDataTesting
from web3 import Web3
import directory


def main() -> None:
    Instance = EBBOHistoricalDataTesting()
    infura_connection = f"https://mainnet.infura.io/v3/{directory.INFURA_KEY}"
    w3 = Web3(Web3.HTTPProvider(infura_connection))
    start_block = w3.eth.block_number
    time.sleep(1800)
    print("starting...")
    end_block = w3.eth.block_number
    unchecked_hashes: List[str] = []
    while True:
        time.sleep(1800)
        fetched_hashes = Instance.get_settlement_hashes(start_block, end_block)
        all_hashes = fetched_hashes + unchecked_hashes
        unchecked_hashes = []
        while len(all_hashes) > 0:
            hash = all_hashes[0]
            single_hash_list: List[str] = []
            single_hash_list.append(hash)
            response_data = Instance.get_solver_competition_data(single_hash_list)
            all_hashes.pop(0)
            if len(response_data) != 0:
                Instance.get_order_surplus(response_data[0])
            else:
                unchecked_hashes.append(hash)

        print("going to sleep")
        start_block = end_block
        end_block = w3.eth.block_number


if __name__ == "__main__":
    main()
