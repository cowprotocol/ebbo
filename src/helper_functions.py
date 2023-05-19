"""
This file contains some auxiliary functions
"""
from __future__ import annotations
import logging
from typing import List, Optional, Tuple, Any
from eth_typing import HexStr


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


class DecodedSettlement:
    """
    Decodes transaction fetched from blockchain using web3.py for GPv2 settlement
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

    @classmethod
    def get_decoded_settlement(cls, contract_instance, web_3, tx_hash: str):
        """
        Takes settlement hash as input, returns decoded settlement data.
        """
        encoded_transaction = web_3.eth.get_transaction(HexStr(tx_hash))
        decoded_settlement = DecodedSettlement.new(
            contract_instance, encoded_transaction["input"]
        )
        return (
            decoded_settlement.trades,
            decoded_settlement.clearing_prices,
            decoded_settlement.tokens,
        )
