import time
import requests
import json
from cowEndpointFunctions import getSurplus, fetchCompetitionData
from web3 import Web3
import directory

def getHashes(startBlock, endBlock):
    etherscanUrl = f"https://api.etherscan.io/api?module=account&action=txlist&address=0x9008D19f58AAbD9eD0D60971565AA8510560ab41&startblock={startBlock}&endblock={endBlock}&sort=desc&apikey={directory.ETHERSCAN_KEY}"
    try:
            settlements = json.loads((requests.get(etherscanUrl)).text)["result"]
            hashesList = []
            for settlement in settlements:
                settlementHash = settlement["hash"]
                hashesList.append(settlementHash)
            return hashesList
    except ValueError:
        print("could not fetch etherscan data.")
        
def main():
    w3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{directory.INFURA_KEY}"))
    startBlock = w3.eth.block_number
    time.sleep(18)
    print("1")
    endBlock = w3.eth.block_number
    uncheckedHashes = []
    while True:
        time.sleep(18)
        fetchedHashes = getHashes(startBlock, endBlock)
        allHashes = fetchedHashes + uncheckedHashes
        uncheckedHashes = []
        while len(allHashes) > 0:
            hash = allHashes[0]
            jsonData = fetchCompetitionData(hash)
            allHashes.pop(0)
            if jsonData.status_code == 200:
                getSurplus(hash)
            else:
                uncheckedHashes.append(hash)

        print("going to sleep")
        startBlock = endBlock
        endBlock = w3.eth.block_number

if __name__ == "__main__":
    main()