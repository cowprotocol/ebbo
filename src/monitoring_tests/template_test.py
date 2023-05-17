"""
In this file, we introduce a TemplateClass, whose purpose is to be used as the base class
for all tests developed.
"""
import json
from typing import List, Dict, Any
from fractions import Fraction
import os
from dotenv import load_dotenv
import requests
from web3 import Web3
from eth_typing import Address, HexStr
from hexbytes import HexBytes
from helper_functions import percent_eth_conversions_order
from src.constants import (
    ADDRESS,
    header,
    SUCCESS_CODE,
    FAIL_CODE,
)
from src.helper_functions import get_logger, DecodedSettlement
from contracts.gpv2_settlement import gpv2_settlement as gpv2Abi


class TemplateTest:
    """
    This is a TemplateTest class that contains a few auxiliary functions that
    multiple tests might find useful. The intended usage is that every new test
    is a subclass of this class.
    """

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
    def get_order_data_by_hash(cls, settlement_hash: str) -> Any:
        """
        Returns competition endpoint data since we need order_id and auction_id
        """
        comp_data = None
        compete_data = []
        try:
            # first fetch from production environment
            comp_data = requests.get(
                f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{settlement_hash}"
            )
            status_code = comp_data.status_code
            if status_code == SUCCESS_CODE:
                compete_data = comp_data.json()
                return compete_data["solutions"][-1]["orders"]

            # attempt fetch from staging environment, if prod failed.
            comp_data = requests.get(
                (
                    "https://barn.api.cow.fi/mainnet/api/v1/solver_competition/"
                    f"by_tx_hash/{settlement_hash}"
                )
            )
            status_code = comp_data.status_code
            if comp_data.status_code == SUCCESS_CODE:
                compete_data = comp_data.json()
                return compete_data["solutions"][-1]["orders"]
        except ValueError as except_err:
            TemplateTest.logger.error("Unhandled exception: %s", str(except_err))
            return []

    @classmethod
    def get_auction_id_by_hash(cls, settlement_hash: str) -> int:
        """
        To be completed
        """
        data = cls.get_solver_competition_data([settlement_hash])
        if data:
            return int(data["auctionId"])
        return -1

    @classmethod
    def get_instance_json_by_auction_id(cls, auction_id: int) -> Any:
        """
        To be completed
        """
        bucket_response = None
        try:
            # first fetch from production environment
            bucket_response = requests.get(
                "https://solver-instances.s3.eu-central-1.amazonaws.com/"
                f"prod-mainnet/{auction_id}.json"
            )
            if bucket_response.status_code == SUCCESS_CODE:
                return dict(bucket_response.json())

            # attempt fetch from staging environment, if prod failed.
            bucket_response = requests.get(
                "https://solver-instances.s3.eu-central-1.amazonaws.com/"
                f"staging-mainnet/{auction_id}.json"
            )
            if bucket_response.status_code == SUCCESS_CODE:
                return dict(bucket_response.json())
        except ValueError as except_err:
            TemplateTest.logger.error("Unhandled exception: %s", str(except_err))
            return None

    @classmethod
    def get_eth_value(cls):
        """
        Returns live ETH price using etherscan API
        """
        eth_price_url = (
            "https://api.etherscan.io/api?module=stats&"
            f"action=ethprice&apikey={cls.ETHERSCAN_KEY}"
        )
        ## a try-catch is missing here!!!!!
        eth_price = requests.get(eth_price_url).json()["result"]["ethusd"]
        return eth_price

    @classmethod
    def get_flagging_values(
        cls, onchain_order_data, executed_amount, clearing_prices, external_prices
    ):
        """
        This function calculates surplus for solution, compares to winning
        solution to get surplus difference, and finally returns percent_deviations
        and surplus difference in eth based on external prices.
        """
        if onchain_order_data["order_type"] == "1":  # buy order
            # in this case, it is sell amount
            buy_or_sell_amount = int(onchain_order_data["sell_amount"])
            conversion_external_price = int(
                external_prices[onchain_order_data["sell_token"]]
            )
        elif onchain_order_data["order_type"] == "0":  # sell order
            # in this case, it is buy amount
            buy_or_sell_amount = int(onchain_order_data["buy_amount"])
            conversion_external_price = int(
                external_prices[onchain_order_data["buy_token"]]
            )

        win_surplus = TemplateTest.get_order_surplus(
            executed_amount,
            buy_or_sell_amount,
            onchain_order_data["sell_token_clearing_price"],
            onchain_order_data["buy_token_clearing_price"],
            onchain_order_data["order_type"],
        )

        soln_surplus = TemplateTest.get_order_surplus(
            executed_amount,
            buy_or_sell_amount,
            clearing_prices[onchain_order_data["sell_token"]],
            clearing_prices[onchain_order_data["buy_token"]],
            onchain_order_data["order_type"],
        )
        # difference in surplus
        diff_surplus = win_surplus - soln_surplus

        percent_deviation, surplus_eth = percent_eth_conversions_order(
            diff_surplus,
            buy_or_sell_amount,
            conversion_external_price,
        )
        # divide by 10**18 to convert to ETH, consistent with quasimodo test
        surplus_eth = surplus_eth / pow(10, 18)
        return surplus_eth, percent_deviation
