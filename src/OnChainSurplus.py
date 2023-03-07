from config import INFURA_KEY
from web3 import Web3
from typing import List, Tuple
from fractions import Fraction
import json
import requests


#GPv2 contract address
address = '0x9008D19f58AAbD9eD0D60971565AA8510560ab41'
#abi in json to py object
abiJson = '[{"inputs":[{"internalType":"contract GPv2Authentication","name":"authenticator_","type":"address"},{"internalType":"contract IVault","name":"vault_","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"target","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"},{"indexed":false,"internalType":"bytes4","name":"selector","type":"bytes4"}],"name":"Interaction","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":false,"internalType":"bytes","name":"orderUid","type":"bytes"}],"name":"OrderInvalidated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":false,"internalType":"bytes","name":"orderUid","type":"bytes"},{"indexed":false,"internalType":"bool","name":"signed","type":"bool"}],"name":"PreSignature","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"solver","type":"address"}],"name":"Settlement","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":false,"internalType":"contract IERC20","name":"sellToken","type":"address"},{"indexed":false,"internalType":"contract IERC20","name":"buyToken","type":"address"},{"indexed":false,"internalType":"uint256","name":"sellAmount","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"buyAmount","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"feeAmount","type":"uint256"},{"indexed":false,"internalType":"bytes","name":"orderUid","type":"bytes"}],"name":"Trade","type":"event"},{"inputs":[],"name":"authenticator","outputs":[{"internalType":"contract GPv2Authentication","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"domainSeparator","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes","name":"","type":"bytes"}],"name":"filledAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes[]","name":"orderUids","type":"bytes[]"}],"name":"freeFilledAmountStorage","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes[]","name":"orderUids","type":"bytes[]"}],"name":"freePreSignatureStorage","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"offset","type":"uint256"},{"internalType":"uint256","name":"length","type":"uint256"}],"name":"getStorageAt","outputs":[{"internalType":"bytes","name":"","type":"bytes"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes","name":"orderUid","type":"bytes"}],"name":"invalidateOrder","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes","name":"","type":"bytes"}],"name":"preSignature","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes","name":"orderUid","type":"bytes"},{"internalType":"bool","name":"signed","type":"bool"}],"name":"setPreSignature","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"contract IERC20[]","name":"tokens","type":"address[]"},{"internalType":"uint256[]","name":"clearingPrices","type":"uint256[]"},{"components":[{"internalType":"uint256","name":"sellTokenIndex","type":"uint256"},{"internalType":"uint256","name":"buyTokenIndex","type":"uint256"},{"internalType":"address","name":"receiver","type":"address"},{"internalType":"uint256","name":"sellAmount","type":"uint256"},{"internalType":"uint256","name":"buyAmount","type":"uint256"},{"internalType":"uint32","name":"validTo","type":"uint32"},{"internalType":"bytes32","name":"appData","type":"bytes32"},{"internalType":"uint256","name":"feeAmount","type":"uint256"},{"internalType":"uint256","name":"flags","type":"uint256"},{"internalType":"uint256","name":"executedAmount","type":"uint256"},{"internalType":"bytes","name":"signature","type":"bytes"}],"internalType":"struct GPv2Trade.Data[]","name":"trades","type":"tuple[]"},{"components":[{"internalType":"address","name":"target","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"bytes","name":"callData","type":"bytes"}],"internalType":"struct GPv2Interaction.Data[][3]","name":"interactions","type":"tuple[][3]"}],"name":"settle","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"targetContract","type":"address"},{"internalType":"bytes","name":"calldataPayload","type":"bytes"}],"name":"simulateDelegatecall","outputs":[{"internalType":"bytes","name":"response","type":"bytes"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"targetContract","type":"address"},{"internalType":"bytes","name":"calldataPayload","type":"bytes"}],"name":"simulateDelegatecallInternal","outputs":[{"internalType":"bytes","name":"response","type":"bytes"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"components":[{"internalType":"bytes32","name":"poolId","type":"bytes32"},{"internalType":"uint256","name":"assetInIndex","type":"uint256"},{"internalType":"uint256","name":"assetOutIndex","type":"uint256"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"bytes","name":"userData","type":"bytes"}],"internalType":"struct IVault.BatchSwapStep[]","name":"swaps","type":"tuple[]"},{"internalType":"contract IERC20[]","name":"tokens","type":"address[]"},{"components":[{"internalType":"uint256","name":"sellTokenIndex","type":"uint256"},{"internalType":"uint256","name":"buyTokenIndex","type":"uint256"},{"internalType":"address","name":"receiver","type":"address"},{"internalType":"uint256","name":"sellAmount","type":"uint256"},{"internalType":"uint256","name":"buyAmount","type":"uint256"},{"internalType":"uint32","name":"validTo","type":"uint32"},{"internalType":"bytes32","name":"appData","type":"bytes32"},{"internalType":"uint256","name":"feeAmount","type":"uint256"},{"internalType":"uint256","name":"flags","type":"uint256"},{"internalType":"uint256","name":"executedAmount","type":"uint256"},{"internalType":"bytes","name":"signature","type":"bytes"}],"internalType":"struct GPv2Trade.Data","name":"trade","type":"tuple"}],"name":"swap","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"vault","outputs":[{"internalType":"contract IVault","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"vaultRelayer","outputs":[{"internalType":"contract GPv2VaultRelayer","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"stateMutability":"payable","type":"receive"}]'
gpv2Abi = json.loads(abiJson)
#connecting to ethereum node
w3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}"))
#creating an instance of GPv2 contract 
contractInstance = w3.eth.contract(address=address, abi=gpv2Abi)

class DecodedSettlement:
    def __init__(self, tokens: List[str], clearing_prices: List[int], trades: List[Tuple[int, int, str, int, int, int, bytes, int, int, int, bytes]], interactions: List[List[Tuple[str, int, bytes]]]):
        self.tokens = tokens
        self.clearing_prices = clearing_prices
        self.trades = trades
        self.interactions = interactions

    @classmethod
    def new(cls, contractInstance, transaction):
        # Decode the function input
        decoded_input = contractInstance.decode_function_input(transaction.input)[1:]
        # Convert the decoded input to the expected types
        tokens = decoded_input[0]['tokens']
        clearing_prices = decoded_input[0]['clearingPrices']
        trades = decoded_input[0]['trades']
        interactions = decoded_input[0]['interactions']

        # Create and return a new instance of DecodedSettlement
        return cls(tokens, clearing_prices, trades, interactions)


def calculateSurplus(startBlock = None, endBlock = None, settlementHash = None):
    if settlementHash is not None:
        decoder(settlementHash)
    elif startBlock is not None and endBlock is not None:
    # define the filter criteria
        filter_criteria = {
            'fromBlock': int(startBlock),
            'toBlock': int(endBlock),
            'address': address,
        }
        transactions = w3.eth.filter(filter_criteria).get_all_entries()
        transactionHashes = []
        for tx in transactions:
            txHash = (tx['transactionHash']).hex()
            if txHash not in transactionHashes:
                transactionHashes.append(txHash)
        transactionHashes.reverse()
        # At this point we have all the needed hashes

        for hashCounter in range(len(transactionHashes)):
            singleHash = transactionHashes[hashCounter]
            decoder(singleHash)


def decoder(settlementHash):
    encodedTransaction = w3.eth.get_transaction(settlementHash)
    decoded_settlement = DecodedSettlement.new(contractInstance, encodedTransaction)
    # there can be multiple orders/trades in a single settlement
    for ordersCount in range(len(decoded_settlement.trades)):
        individualOrder = decoded_settlement.trades[ordersCount]
        surplus = calculationFunction(decoded_settlement, individualOrder)
        print(surplus)

        endpointDataJson = requests.get(f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{settlementHash}")
        endpointDataPy = json.loads(endpointDataJson.text)
        auctionId = endpointDataPy["auctionId"]
        orderId = endpointDataPy["solutions"][-1]["orders"][ordersCount]["id"]
        bucketResponseJson = requests.get(f"https://solver-instances.s3.eu-central-1.amazonaws.com/prod-mainnet/{auctionId}.json")
        bucketResponsePy = json.loads(bucketResponseJson.text)
        for order in bucketResponsePy["orders"].items():
            if order[1]["id"] == orderId:
                bucketResponsePy["orders"] = order
                break


def calculationFunction(decoded_settlement, individualOrder):
    sellTokenIndex = individualOrder['sellTokenIndex']
    buyTokenIndex = individualOrder['buyTokenIndex']
    sellTokenClearingPrice = decoded_settlement.clearing_prices[sellTokenIndex]
    buyTokenClearingPrice = decoded_settlement.clearing_prices[buyTokenIndex]
    flagBin = str('{0:08b}'.format(individualOrder['flags'])) # convert flags value to binary to extract L.S.B (Least Sigificant Byte)
    if flagBin[-1] == '0': # implies a sell order
        execVolume = int(Fraction(individualOrder['executedAmount']) * Fraction(sellTokenClearingPrice) // Fraction(buyTokenClearingPrice))
        Surplus = execVolume - int(individualOrder['buyAmount']) 
    elif flagBin[-1] == '1': # implies a buy order
        execVolume = int(Fraction(individualOrder['executedAmount']) * Fraction(buyTokenClearingPrice) // Fraction(sellTokenClearingPrice))
        Surplus = int(individualOrder['sellAmount']) - execVolume
    return Surplus

# Below line fetches latest block
# endBlock = w3.eth.block_number

# ---------------------------- TESTING --------------------------------

optionInput = input("b for block input, h for hash input: ")

match optionInput:
    case "b":
        startBlock = input("Start Block: ")
        endBlock = input("End Block: ")
        calculateSurplus(startBlock, endBlock, None)
    case "h":
        settlementHash = input("Settlement Hash: ")
        calculateSurplus(None, None, settlementHash)