"""
on_chain file
"""
from config import INFURA_KEY
from contracts.gpv2_settlement import gpv2_settlement as gpv2Abi
from typing import List, Tuple
from fractions import Fraction
import requests
from web3 import Web3
# from instance_file import instance

#GPv2 contract address
address = '0x9008D19f58AAbD9eD0D60971565AA8510560ab41'

class DecodedSettlement:
    def __init__(self, tokens: List[str], clearing_prices: List[int], trades: List[Tuple[int, int, str, int, int, int, bytes, int, int, int, bytes]], interactions: List[List[Tuple[str, int, bytes]]]):
        self.tokens = tokens
        self.clearing_prices = clearing_prices
        self.trades = trades
        self.interactions = interactions

    @classmethod
    def new(cls, contract_instance, transaction):
        # Decode the function input
        decoded_input = contract_instance.decode_function_input(transaction)[1:]
        # Convert the decoded input to the expected types
        tokens = decoded_input[0]['tokens']
        clearing_prices = decoded_input[0]['clearingPrices']
        trades = decoded_input[0]['trades']
        interactions = decoded_input[0]['interactions']

        # Create and return a new instance of DecodedSettlement
        return cls(tokens, clearing_prices, trades, interactions)

class OnChainEBBO:

    def __init__(self):
        """
        Makes ethereum node connection to Infura, and creates contract instance
        """
        self.web_3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}"))
        self.contract_instance = self.web_3.eth.contract(address=address, abi=gpv2Abi)


    def get_hashes_by_block(self, start_block, end_block):
        """
        Function filters hashes by contract address
        """
        filter_criteria = {
            'fromBlock': int(start_block),
            'toBlock': int(end_block),
            'address': address,
        }
        transactions = self.web_3.eth.filter(filter_criteria).get_all_entries()
        settlement_hashes_list = []
        for tx in transactions:
            tx_hash = (tx['transactionHash']).hex()
            if tx_hash not in settlement_hashes_list:
                settlement_hashes_list.append(tx_hash)
        settlement_hashes_list.reverse()
        return settlement_hashes_list


    def get_tx_hashes(self, start_block = None, end_block = None, settlement_hash = None):
        """
        Puts transactions in list, calls required function in case of range of blocks.
        """
        settlement_hashes_list = []
        if settlement_hash is not None:
            settlement_hashes_list = [settlement_hash]
        elif start_block is not None and end_block is not None:
            settlement_hashes_list = self.get_hashes_by_block(start_block, end_block)
            # At this point we have all the needed hashes
        self.decoder(settlement_hashes_list)


    def get_order_data_by_hash(self, settlement_hash):
        """
        Returns competition endpoint data since we need order_id and auction_id, and also AWS
        Bucket response.
        """
        try:
            comp_data = requests.get(f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{settlement_hash}")
            status_code = comp_data.status_code
            if status_code == 200:
                comp_data = comp_data.json()
                auction_id = comp_data["auctionId"] 
                bucket_response = dict(requests.get(f"https://solver-instances.s3.eu-central-1.amazonaws.com/prod-mainnet/{auction_id}.json").json())
            elif status_code == 404:
                comp_data = requests.get(f"https://barn.api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{settlement_hash}")
                status_code = comp_data.status_code
                if comp_data.status_code == 200:
                    comp_data = comp_data.json()
                    auction_id = comp_data["auctionId"] 
                    bucket_response = dict(requests.get(f"https://solver-instances.s3.eu-central-1.amazonaws.com/staging-mainnet/{auction_id}.json").json())
        except ValueError as except_err:
            print("Order not found... " + str(except_err))

        return comp_data, bucket_response


    def decoder(self, settlement_hashes_list):
        """
        Need a better name for this function. Goes through all settlements fetched, decodes orders,
        gets AWS Bucket response and makes call to quasimodo for required orders.
        """
        for settlement_hash in settlement_hashes_list:
            print(settlement_hash)
            try:
                encoded_transaction = self.web_3.eth.get_transaction(settlement_hash)
                decoded_settlement = DecodedSettlement.new(self.contract_instance, encoded_transaction.input)
                (comp_data, bucket_response) = self.get_order_data_by_hash(settlement_hash)
            except ValueError as except_err:
                print("Transaction doesn't exist." + str(except_err))
 
            if bucket_response is None:
                continue
            # there can be multiple orders/trades in a single settlement
            for trade in decoded_settlement.trades:
                sell_token_index = trade['sellTokenIndex']
                buy_token_index = trade['buyTokenIndex']
                sell_token_clearing_price = decoded_settlement.clearing_prices[sell_token_index]
                buy_token_clearing_price = decoded_settlement.clearing_prices[buy_token_index]

                order_type = str('{0:08b}'.format(trade['flags'])) # convert flags value to binary to extract L.S.B (Least Sigificant Byte)
                win_surplus = self.get_surplus(trade, sell_token_clearing_price, buy_token_clearing_price, order_type[-1])
                order_id = comp_data["solutions"][-1]["orders"][decoded_settlement.trades.index(trade)]["id"]
                for key, order in bucket_response["orders"].items():
                    if order["id"] == order_id:
                        bucket_response["orders"] = {key:order}
                        break

                # convert back to JSON for sending to Quasimodo
                # bucketResponseJson = json.dumps(bucket_response)
                # # space here to post and receive instance JSON from Quasimodo
                # instanceJson = requests.post(bucketResponseJson)
                # assuming jsonObject is called instanceJson
                # instance = instanceJson.json() to convert to dict
                # 'instance' is what we use here as a python object in instance_file.py
                
                # This part needs to be commented out in case you try to run
                # since there is no instance json available from quasimodo,
                # but is certainly part of the code.

                sell_token = order['sell_token']
                buy_token = order['buy_token']
                if len(instance["prices"]) > 0:
                    sell_token_clearing_price = instance["prices"][sell_token]
                    buy_token_clearing_price = instance["prices"][buy_token]
                    qmdo_surplus = self.get_surplus(trade, sell_token_clearing_price, buy_token_clearing_price, order_type[-1])
                    diff_surplus = win_surplus - qmdo_surplus
                    (percent_deviation, diff_in_eth) = self.get_conversions(diff_surplus, trade, order_type[-1], bucket_response["tokens"], order)
                    print(percent_deviation, diff_in_eth)
                    if percent_deviation < 0.1 and diff_in_eth < 0.002:
                        print("flag")


    def get_conversions(self, diff_surplus, trade, order_type, tokens, order):
        """
        calcuate order flag condition values,
        (relative % deviation, absolute ETH difference) based on order type
        """
        if order_type == '0': # implies a sell order
            percent_deviation = (diff_surplus * 100) / int(trade['buyAmount'])
            buy_token = order["buy_token"]
            diff_in_eth = tokens[buy_token]["external_price"]/ (pow(10, 18)) * (diff_surplus)
        elif order_type == '1': #implies a buy order
            percent_deviation = (diff_surplus * 100) / int(trade['sellAmount'])
            sell_token = order["buy_token"]
            diff_in_eth = tokens[sell_token]["external_price"]/ (pow(10, 18)) * (diff_surplus)

        return percent_deviation, diff_in_eth


    def get_surplus(self, trade, sell_token_clearing_price, buy_token_clearing_price, order_type):
        """
        Function calculates surplus using clearing prices,
        for winning order and from quasimodo
        """
        # print(trade['executedAmount'])
        # print(sell_token_clearing_price)
        # print(buy_token_clearing_price)
        if order_type == '0': # implies sell order
            executed_volume = int(Fraction(trade['executedAmount']) * Fraction(sell_token_clearing_price) // Fraction(buy_token_clearing_price))
            Surplus = executed_volume - int(trade['buyAmount']) 
        elif order_type == '1': # implies buy order
            executed_volume = int(Fraction(trade['executedAmount']) * Fraction(buy_token_clearing_price) // Fraction(sell_token_clearing_price))
            Surplus = int(trade['sellAmount']) - executed_volume
        return Surplus 


# ---------------------------- TESTING --------------------------------
def main():
    instance = OnChainEBBO()
    optionInput = input("b for block input, h for hash input: ")
    match optionInput:
        case "b":
            start_block = input("Start Block: ")
            end_block = input("End Block: ")
            instance.get_tx_hashes(start_block, end_block, None)
        case "h":
            settlement_hash = input("Settlement Hash: ")
            instance.get_tx_hashes(None, None, settlement_hash)


if __name__ == "__main__":
    main() 