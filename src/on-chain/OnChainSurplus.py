# from config import INFURA_KEY
from web3 import Web3
from typing import List, Tuple
from fractions import Fraction
import json
import requests
import os
import getDirectory

#GPv2 contract address
address = '0x9008D19f58AAbD9eD0D60971565AA8510560ab41'

class DecodedSettlement:
    def __init__(self, tokens: List[str], clearing_prices: List[int], trades: List[Tuple[int, int, str, int, int, int, bytes, int, int, int, bytes]], interactions: List[List[Tuple[str, int, bytes]]]):
        self.tokens = tokens
        self.clearing_prices = clearing_prices
        self.trades = trades
        self.interactions = interactions

    @classmethod
    def new(cls, contractInstance, transaction):
        # Decode the function input
        decoded_input = contractInstance.decode_function_input(transaction)[1:]
        # Convert the decoded input to the expected types
        tokens = decoded_input[0]['tokens']
        clearing_prices = decoded_input[0]['clearingPrices']
        trades = decoded_input[0]['trades']
        interactions = decoded_input[0]['interactions']

        # Create and return a new instance of DecodedSettlement
        return cls(tokens, clearing_prices, trades, interactions)


def fetchSettlements(startBlock = None, endBlock = None, settlementHash = None, w3 = None, contractInstance = None):
    transactionHashes = []
    if settlementHash is not None:
        transactionHashes.append(settlementHash)

    elif startBlock is not None and endBlock is not None:
    # define the filter criteria
        filter_criteria = {
            'fromBlock': int(startBlock),
            'toBlock': int(endBlock),
            'address': address,
        }
        transactions = w3.eth.filter(filter_criteria).get_all_entries()
        for tx in transactions:
            txHash = (tx['transactionHash']).hex()
            if txHash not in transactionHashes:
                transactionHashes.append(txHash)
        transactionHashes.reverse()

        # At this point we have all the needed hashes
    decodeHashes(transactionHashes, w3, contractInstance)


def decodeHashes(transactionHashes, w3, contractInstance):
    for hashCounter in range(len(transactionHashes)):
        singleHash = transactionHashes[hashCounter]
        decoder(singleHash, w3, contractInstance)


def decoder(settlementHash, w3, contractInstance):
    encodedTransaction = w3.eth.get_transaction(settlementHash)
    encodedTransaction = encodedTransaction.input
    decoded_settlement = DecodedSettlement.new(contractInstance, encodedTransaction)

    endpointDataJson = requests.get(f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{settlementHash}")
    endpointDataPy = json.loads(endpointDataJson.text)
    auctionId = endpointDataPy["auctionId"]
    bucketResponseJson = requests.get(f"https://solver-instances.s3.eu-central-1.amazonaws.com/prod-mainnet/{auctionId}.json")
    bucketResponsePy = json.loads(bucketResponseJson.text)

    # there can be multiple orders/trades in a single settlement
    for ordersCount in range(len(decoded_settlement.trades)):
        trade = decoded_settlement.trades[ordersCount]
        sellTokenIndex = trade['sellTokenIndex']
        buyTokenIndex = trade['buyTokenIndex']
        sellTokenClearingPrice = decoded_settlement.clearing_prices[sellTokenIndex]
        buyTokenClearingPrice = decoded_settlement.clearing_prices[buyTokenIndex]

        surplus = getSurplus(trade, sellTokenClearingPrice, buyTokenClearingPrice)
        print(surplus)
        orderId = endpointDataPy["solutions"][-1]["orders"][ordersCount]["id"]
        for order in bucketResponsePy["orders"].items():
            if order[1]["id"] == orderId:
                bucketResponsePy["orders"] = order
                break
        #convert back to JSON for sending to Quasimodo
        bucketResponseJson = json.dumps(bucketResponsePy)
        # space here to post and receive instance.json to-fro Quasimodo
        # assuming jsonObject is called instanceJson
        InstanceJson = {}
        InstancePy = json.loads(InstanceJson.text)
        if len(InstancePy["prices"]) > 0:
            sellTokenIndex = trade['sellTokenIndex']
            buyTokenIndex = trade['buyTokenIndex']
            sellTokenClearingPrice = InstancePy["prices"][sellTokenIndex]
            buyTokenClearingPrice = InstancePy["prices"][buyTokenIndex]
            quasimodoSurplus = getSurplus(trade, sellTokenClearingPrice, buyTokenClearingPrice)


def getSurplus(trade, sellTokenClearingPrice, buyTokenClearingPrice):
    flagBin = str('{0:08b}'.format(trade['flags'])) # convert flags value to binary to extract L.S.B (Least Sigificant Byte)
    if flagBin[-1] == '0': # implies a sell order
        execVolume = int(Fraction(trade['executedAmount']) * Fraction(sellTokenClearingPrice) // Fraction(buyTokenClearingPrice))
        Surplus = execVolume - int(trade['buyAmount']) 
    elif flagBin[-1] == '1': # implies a buy order
        execVolume = int(Fraction(trade['executedAmount']) * Fraction(buyTokenClearingPrice) // Fraction(sellTokenClearingPrice))
        Surplus = int(trade['sellAmount']) - execVolume

    return Surplus 


# ---------------------------- TESTING --------------------------------
def main():
    #connecting to ethereum node
    w3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{getDirectory.INFURA_KEY}"))
    #creating an instance of GPv2 contract 
    contractInstance = w3.eth.contract(address=address, abi=getDirectory.gpv2Abi)

    optionInput = input("b for block input, h for hash input: ")

    match optionInput:
        case "b":
            startBlock = input("Start Block: ")
            endBlock = input("End Block: ")
            fetchSettlements(startBlock, endBlock, None, w3, contractInstance)
        case "h":
            settlementHash = input("Settlement Hash: ")
            fetchSettlements(None, None, settlementHash, w3, contractInstance)


if __name__ == "__main__":
    main() 