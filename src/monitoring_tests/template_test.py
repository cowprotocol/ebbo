"""
In this file, we introduce a TemplateClass, whose purpose is to be used as the base class
for all tests developed.
"""
import json
from typing import List, Dict, Tuple, Any
from fractions import Fraction
import os
from dotenv import load_dotenv
import requests
from web3 import Web3
from web3.types import TxData, TxReceipt
from eth_typing import Address, HexStr
from hexbytes import HexBytes
from src.helper_functions import percent_eth_conversions_order
from src.constants import (
    ADDRESS,
    header,
    SUCCESS_CODE,
    FAIL_CODE,
)
from src.helper_functions import get_logger, DecodedSettlement
from contracts.gpv2_settlement import gpv2_settlement as gpv2Abi


class TemplateTest:
    # pylint: disable=too-many-public-methods
    """
    This is a TemplateTest class that contains a few auxiliary functions that
    multiple tests might find useful. The intended usage is that every new test
    is a subclass of this class.
    """

    load_dotenv()

    ###### class variables
    DUNE_KEY = os.getenv("DUNE_KEY")
    INFURA_KEY = os.getenv("INFURA_KEY")
    ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")
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
            "topics": [
                "0xa07a543ab8a018198e99ca0184c93fe9050a79400a0a723441f84de1d972cc17"
            ],
        }
        # transactions may have repeating hashes, since even event logs are filtered
        # therefore, check if hash has already been added to the list

        # only successful transactions are filtered
        try:
            transactions = cls.web_3.eth.filter(filter_criteria).get_all_entries()  # type: ignore
        except ValueError as except_err:
            cls.logger.error(
                "ValueError while fetching hashes: %s.",
                str(except_err),
            )
            transactions = []
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
            except requests.exceptions.ConnectionError as except_err:
                cls.logger.error(
                    "Connection error while fetching competition data: %s.",
                    str(except_err),
                )

        return solver_competition_data

    @classmethod
    def get_encoded_transaction(cls, tx_hash: str) -> TxData:
        """
        Takes settlement hash as input, returns encoded transaction data.
        """
        return cls.web_3.eth.get_transaction(HexStr(tx_hash))

    @classmethod
    def get_encoded_receipt(cls, tx_hash: str) -> TxReceipt:
        """
        Get the receipt of a transaction from the transaction hash.
        This is used to obtain the gas used for the transaction.
        """
        return cls.web_3.eth.wait_for_transaction_receipt(HexStr(tx_hash))

    @classmethod
    def get_decoded_settlement_raw(
        cls, encoded_transaction: TxData
    ) -> DecodedSettlement:
        """
        Decode settlement from transaction using the settlement contract.
        """
        return DecodedSettlement.new(
            cls.contract_instance, encoded_transaction["input"]
        )

    @classmethod
    def get_decoded_settlement(cls, tx_hash: str):
        """
        Takes settlement hash as input, returns decoded settlement data.
        """
        encoded_transaction = cls.get_encoded_transaction(tx_hash)
        decoded_settlement = DecodedSettlement.new(
            cls.contract_instance, encoded_transaction["input"]
        )
        return (
            decoded_settlement.trades,
            decoded_settlement.clearing_prices,
            decoded_settlement.tokens,
        )

    @classmethod
    def get_endpoint_order_data(cls, tx_hash: str) -> List[Any]:
        """
        Get all orders in a transaction from the transaction hash.
        """
        prod_endpoint_url = (
            "https://api.cow.fi/mainnet/api/v1/transactions/" + tx_hash + "/orders"
        )
        barn_endpoint_url = (
            "https://barn.api.cow.fi/mainnet/api/v1/transactions/" + tx_hash + "/orders"
        )
        orders_response = requests.get(
            prod_endpoint_url,
            headers=header,
            timeout=30,
        )
        if orders_response.status_code != SUCCESS_CODE:
            orders_response = requests.get(
                barn_endpoint_url,
                headers=header,
                timeout=30,
            )
            if orders_response.status_code != SUCCESS_CODE:
                cls.logger.error(
                    "Error loading orders from mainnet: %s", orders_response.status_code
                )
                return []

        orders = json.loads(orders_response.text)

        return orders

    @classmethod
    def get_order_execution(
        cls, decoded_settlement: DecodedSettlement, i: int
    ) -> Tuple[int, int, int]:
        # pylint: disable=too-many-locals
        """
        Given a settlement and the index of an trade, compute buy_amount, sell_amount, and
        fee_amount of the trade.
        """
        trade = decoded_settlement.trades[i]
        tokens = decoded_settlement.tokens
        clearing_prices = decoded_settlement.clearing_prices

        buy_token = tokens[trade["buyTokenIndex"]]
        buy_token_price = clearing_prices[trade["buyTokenIndex"]]
        buy_token_index_ucp = tokens.index(buy_token)
        buy_token_price_ucp = clearing_prices[buy_token_index_ucp]

        sell_token = tokens[trade["sellTokenIndex"]]
        sell_token_price = clearing_prices[trade["sellTokenIndex"]]
        sell_token_index_ucp = tokens.index(sell_token)
        sell_token_price_ucp = clearing_prices[sell_token_index_ucp]

        executed_amount = trade["executedAmount"]
        precomputed_fee_amount = trade["feeAmount"]

        if str(f"{trade['flags']:08b}")[-1] == "0":  # sell order
            buy_amount = int(
                executed_amount * Fraction(sell_token_price, buy_token_price)
            )
            sell_amount = int(
                buy_amount * Fraction(buy_token_price_ucp, sell_token_price_ucp)
            )
            fee_amount = precomputed_fee_amount + executed_amount - sell_amount
        else:  # buy orders
            buy_amount = executed_amount
            sell_amount = int(
                buy_amount * Fraction(buy_token_price_ucp, sell_token_price_ucp)
            )
            fee_amount = (
                precomputed_fee_amount
                + int(buy_amount * Fraction(buy_token_price, sell_token_price))
                - sell_amount
            )

        return buy_amount, sell_amount, fee_amount

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
    def get_quote(cls, decoded_settlement, i) -> Tuple[int, int, int]:
        """
        Given a trade, compute buy_amount, sell_amount, and fee_amount of the trade
        as proposed by our quoting infrastructure.
        """
        trade = decoded_settlement.trades[i]

        if str(f"{trade['flags']:08b}")[-1] == "0":
            kind = "sell"
            limit_amount_name = "sellAmountBeforeFee"
        else:
            kind = "buy"
            limit_amount_name = "buyAmountAfterFee"

        request_dict = {
            "sellToken": decoded_settlement.tokens[trade["sellTokenIndex"]],
            "buyToken": decoded_settlement.tokens[trade["buyTokenIndex"]],
            "receiver": trade["receiver"],
            "appData": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "partiallyFillable": False,
            "sellTokenBalance": "erc20",
            "buyTokenBalance": "erc20",
            "from": trade["receiver"],
            "priceQuality": "optimal",
            "signingScheme": "eip712",
            "onchainOrder": False,
            "kind": kind,
            limit_amount_name: str(trade["executedAmount"]),
        }

        try:
            prod_endpoint_url = "https://api.cow.fi/mainnet/api/v1/quote"
            quote_response = requests.post(
                prod_endpoint_url,
                headers=header,
                json=request_dict,
                timeout=30,
            )
        except ValueError as err:
            cls.logger.error("Fee quote failed with error %s.", err)

        if quote_response.status_code != SUCCESS_CODE:
            error_type = json.loads(quote_response.content)["errorType"]
            error_description = json.loads(quote_response.content)["description"]
            if error_type in ("SellAmountDoesNotCoverFee", "NoLiquidity"):
                cls.logger.error(
                    "Error %s, %s while getting quote for trade %s",
                    quote_response.status_code,
                    error_description,
                    trade,
                )
                raise ValueError(error_description)

            cls.logger.error(
                "Error %s, %s while getting quote for trade %s",
                quote_response.status_code,
                error_description,
                trade,
            )
            raise ConnectionError(
                f"Fee quote failed with error {quote_response.status_code}, {error_description}"
            )

        quote_json = json.loads(quote_response.text)
        TemplateTest.logger.debug("Quote received: %s", quote_json)

        quote_buy_amount = int(quote_json["quote"]["buyAmount"])
        quote_sell_amount = int(quote_json["quote"]["sellAmount"])
        quote_fee_amount = int(quote_json["quote"]["feeAmount"])

        return quote_buy_amount, quote_sell_amount, quote_fee_amount

    @classmethod
    def get_gas_costs(
        cls, encoded_transaction: TxData, receipt: TxReceipt
    ) -> Tuple[int, int]:
        """
        Combine the transaction and receipt to return gas used and gas price.
        """
        return int(receipt["gasUsed"]), int(encoded_transaction["gasPrice"])

    @classmethod
    def get_fee(
        cls, order: dict, tx_hash: str  # pylint: disable=unused-argument
    ) -> int:
        """
        Get the fee amount in the sell token for the execution of an order in the transaction given
        hash.
        TODO: use database for this. atm only the fee of the last execution can be recovered.
        """
        return int(order["executedSurplusFee"])

    @classmethod
    def adapt_execution_to_gas_price(
        cls,
        buy_amount: int,
        sell_amount: int,
        fee_amount: int,
        gas_price: int,
        gas_price_adapted: int,
    ) -> Tuple[int, int, int]:
        """
        Given an execution in term of buy, sell, and fee amount created at a time with gas price
        `gas_price`, computes what the execution would have been with gas price `gas_price_adapted`.
        """
        buy_amount_adapted = buy_amount
        fee_amount_adapted = int(fee_amount * gas_price_adapted / gas_price)
        sell_amount_adapted = sell_amount + fee_amount - fee_amount_adapted
        cls.logger.debug(
            "original fee: %s, adapted fee: %s, original gas price: %s, "
            "adapted gas price: %s, correction of fee: %s",
            fee_amount,
            fee_amount_adapted,
            gas_price,
            gas_price_adapted,
            gas_price_adapted / gas_price,
        )
        return buy_amount_adapted, sell_amount_adapted, fee_amount_adapted

    @classmethod
    def get_current_gas_price(cls) -> int:
        """
        Get the current gas price.
        """
        return int(cls.web_3.eth.gas_price)

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
        compete_data = {}
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
            return []
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
            return int(data[0]["auctionId"])
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
            return None
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
