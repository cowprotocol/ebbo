import json
from typing import List, Dict, Any
from fractions import Fraction
import os
from dotenv import load_dotenv
import requests
from web3 import Web3
from eth_typing import Address, HexStr
from hexbytes import HexBytes
from src.constants import (
    ADDRESS,
    header,
    SUCCESS_CODE,
    FAIL_CODE,
)
from src.helper_functions import get_logger, DecodedSettlement
from contracts.gpv2_settlement import gpv2_settlement as gpv2Abi


# This is a templateTest class that contains a few auxiliary functions that
# multiple tests might find useful. The intended usage is that every new test
# is a subclass of this class.
class TemplateTest:

    load_dotenv()

    ###### class variables
    DUNE_KEY = os.getenv("DUNE_KEY")
    INFURA_KEY = "ec46e54a3d5a41e4930952e54bd0cd51"  # os.getenv("INFURA_KEY")
    ETHERSCAN_KEY = os.getenv("INFURA_KEY")
    infura_connection = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
    web_3 = Web3(Web3.HTTPProvider(infura_connection))
    QUASIMODO_SOLVER_URL = os.getenv("QUASIMODO_SOLVER_URL")
    contract_instance = web_3.eth.contract(
        address=Address(HexBytes(ADDRESS)), abi=gpv2Abi
    )
    logger = get_logger()
    #################

    @classmethod
    def get_current_block_number(cls) -> int:
        """
        Function that returns the current block number
        """
        return int(cls.web_3.eth.block_number)

    @classmethod
    def get_tx_hashes_by_block(cls, start_block: int, end_block: int) -> List[str]:
        """
        Function filters hashes by contract address, and block ranges
        """
        filter_criteria = {
            "fromBlock": int(start_block),
            "toBlock": int(end_block),
            "address": ADDRESS,
        }
        # transactions may have repeating hashes, since even event logs are filtered
        # therefore, check if hash has already been added to the list

        # only successful transactions are filtered
        transactions = cls.web_3.eth.filter(filter_criteria).get_all_entries()  # type: ignore
        settlement_hashes_list = []
        for transaction in transactions:
            tx_hash = (transaction["transactionHash"]).hex()
            if tx_hash not in settlement_hashes_list:
                settlement_hashes_list.append(tx_hash)
        return settlement_hashes_list

    @classmethod
    def get_solver_competition_data(
        cls,
        settlement_hashes_list: List[str],
    ) -> List[Dict[str, Any]]:
        """
        This function uses a list of tx hashes to fetch and assemble competition data
        for each of the tx hashes and returns it.
        """
        solver_competition_data = []
        for tx_hash in settlement_hashes_list:
            try:
                prod_endpoint_url = (
                    "https://api.cow.fi/mainnet/api/v1/solver_competition"
                    f"/by_tx_hash/{tx_hash}"
                )
                json_competition_data = requests.get(
                    prod_endpoint_url,
                    headers=header,
                    timeout=30,
                )
                if json_competition_data.status_code == SUCCESS_CODE:
                    solver_competition_data.append(
                        json.loads(json_competition_data.text)
                    )
                elif json_competition_data.status_code == FAIL_CODE:
                    barn_endpoint_url = (
                        "https://barn.api.cow.fi/mainnet/api/v1"
                        f"/solver_competition/by_tx_hash/{tx_hash}"
                    )
                    barn_competition_data = requests.get(
                        barn_endpoint_url, headers=header, timeout=30
                    )
                    if barn_competition_data.status_code == SUCCESS_CODE:
                        solver_competition_data.append(
                            json.loads(barn_competition_data.text)
                        )
            except ValueError as except_err:
                cls.logger.error("Unhandled exception: %s.", str(except_err))

        return solver_competition_data

    @classmethod
    def get_decoded_settlement(cls, tx_hash: str):
        """
        Takes settlement hash as input, returns decoded settlement data.
        """
        encoded_transaction = cls.web_3.eth.get_transaction(HexStr(tx_hash))
        decoded_settlement = DecodedSettlement.new(
            cls.contract_instance, encoded_transaction["input"]
        )
        return (
            decoded_settlement.trades,
            decoded_settlement.clearing_prices,
            decoded_settlement.tokens,
        )

    @classmethod
    def get_onchain_order_data(cls, trade, onchain_clearing_prices, tokens):
        """
        Returns required data to calculate surplus for winning order
        using onchain data from decoded settlement.
        """
        return {
            "sell_token_clearing_price": onchain_clearing_prices[
                trade["sellTokenIndex"]
            ],
            "buy_token_clearing_price": onchain_clearing_prices[trade["buyTokenIndex"]],
            "sell_token": tokens[trade["sellTokenIndex"]].lower(),
            "buy_token": tokens[trade["buyTokenIndex"]].lower(),
            "order_type": str(f"{trade['flags']:08b}")[-1],
            "executed_amount": trade["executedAmount"],
            "sell_amount": trade["sellAmount"],
            "buy_amount": trade["buyAmount"],
            "fee_amount": trade["feeAmount"],
        }

    @classmethod
    def get_order_surplus(
        cls,
        executed_amount: int,
        buy_or_sell_amount: int,
        sell_token_clearing_price: int,
        buy_token_clearing_price: int,
        order_type: str,
    ) -> int:
        """
        Returns surplus using:
        executed amount,
        buy amount if sell order OR sell amount if buy order,
        token clearing prices, and the type of order.
        """
        surplus = 0
        if order_type == "1":  # buy order
            exec_amt = int(
                Fraction(executed_amount)
                * Fraction(buy_token_clearing_price)
                // Fraction(sell_token_clearing_price)
            )
            # sell amount here
            surplus = buy_or_sell_amount - exec_amt
        elif order_type == "0":  # sell order
            exec_amt = int(
                Fraction(executed_amount)
                * Fraction(sell_token_clearing_price)
                // Fraction(buy_token_clearing_price)
            )
            # buy amount here
            surplus = exec_amt - buy_or_sell_amount
        return surplus

    @classmethod
    def get_eth_value(cls):
        """
        Returns live ETH price using etherscan API
        """
        eth_price_url = (
            "https://api.etherscan.io/api?module=stats&"
            f"action=ethprice&apikey={cls.ETHERSCAN_KEY}"
        )
        eth_price = requests.get(eth_price_url).json()["result"]["ethusd"]
        return eth_price
