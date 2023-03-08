import time
import requests
import json
from cowEndpointFunctions import getSurplus, fetchCompetitionData
from web3 import Web3
from config import INFURA_KEY, ETHERSCAN_KEY

def getHashes(startBlock, endBlock):
    etherscanUrl = f"https://api.etherscan.io/api?module=account&action=txlist&address=0x9008D19f58AAbD9eD0D60971565AA8510560ab41&startblock={startBlock}&endblock={endBlock}&sort=desc&apikey={ETHERSCAN_KEY}"
    jsonRecentSettlements = requests.get(etherscanUrl)
    pyRecentSettlements = json.loads(jsonRecentSettlements.text)
    results = pyRecentSettlements["result"]
    hashesList = []
    for counterResults in range(len(results)):
        settlementHash = results[counterResults]["hash"]
        hashesList.append(settlementHash)
    return hashesList
        
def main():
    w3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}"))
    startBlock = w3.eth.block_number
    time.sleep(1800)
    endBlock = w3.eth.block_number
    uncheckedHashes = []
    while True:
        time.sleep(1800)
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