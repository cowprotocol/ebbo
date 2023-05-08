"""
This file contains functions used by cow_endpoint_surplus and quasimodo_test_surplus.
"""
from __future__ import annotations
import logging
from fractions import Fraction
from typing import List, Optional, Tuple, Any
from web3 import Web3

# from dune_client.client import DuneClient
# from dune_client.query import Query
from src.constants import ADDRESS


def get_logger(filename: Optional[str] = None) -> logging.Logger:
    """
    get_logger() returns a logger object that can write to a file, terminal or only file if needed.
    """
    logging.basicConfig(format="%(levelname)s - %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if filename:
        file_handler = logging.FileHandler(filename + ".log", mode="w")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_tx_hashes_by_block(web_3: Web3, start_block: int, end_block: int) -> List[str]:
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
    transactions = web_3.eth.filter(filter_criteria).get_all_entries()
    settlement_hashes_list = []
    for transaction in transactions:
        tx_hash = (transaction["transactionHash"]).hex()
        if tx_hash not in settlement_hashes_list:
            settlement_hashes_list.append(tx_hash)
    return settlement_hashes_list


# def get_eth_value():
#    """
#    Returns live eth price using etherscan API
#    """
#    eth_price_url = (
#        "https://api.etherscan.io/api?module=stats&"
#        f"action=ethprice&apikey={ETHERSCAN_KEY}"
#    )
#    eth_price = requests.get(eth_price_url).json()["result"]["ethusd"]
#    # min_flag_usd = 4.00
#    # eth_absolute_check = str(format(min_flag_usd / float(eth_price), ".6f"))
#    return eth_price


def percent_eth_conversions_order(
    diff_surplus: int, buy_or_sell_amount: int, external_price: float
) -> Tuple[float, float]:
    """
    Returns conversions required for flagging orders.
    """
    percent_deviation = (diff_surplus * 100) / buy_or_sell_amount
    diff_in_eth = (external_price / (pow(10, 18))) * (diff_surplus)
    # diff_in_eth = (external_price/(pow(10, 18))) * (diff_surplus/(pow(10, 18)))
    return percent_deviation, diff_in_eth


def get_surplus_order(
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


class DecodedSettlement:
    """
    Decodes transaction fetched from blockchain using web3.py for GPV2 settlement
    """

    def __init__(
        self,
        tokens: List[str],
        clearing_prices: List[int],
        trades: Any,  # List[Tuple[int, int, str, int, int, int, bytes, int, int, int, bytes]],
    ):
        self.tokens = tokens
        self.clearing_prices = clearing_prices
        self.trades = trades

    @classmethod
    def new(cls, contract_instance: Any, transaction: Any) -> DecodedSettlement:
        """
        Returns decoded settlement
        """
        # Decode the function input
        decoded_input = contract_instance.decode_function_input(transaction)[1:]
        # Convert the decoded input to the expected types
        tokens = decoded_input[0]["tokens"]
        clearing_prices = decoded_input[0]["clearingPrices"]
        trades = decoded_input[0]["trades"]

        # Create and return a new instance of DecodedSettlement
        return cls(tokens, clearing_prices, trades)
