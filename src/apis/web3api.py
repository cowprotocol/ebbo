"""
Web3API for fetching relevant data using the web3 library.
"""

# pylint: disable=logging-fstring-interpolation

from os import getenv
from typing import Any, Optional
from fractions import Fraction
from dotenv import load_dotenv
from web3 import Web3
from web3.types import TxData, TxReceipt, FilterParams
from eth_typing import Address, HexStr
from hexbytes import HexBytes
from contracts.gpv2_settlement import gpv2_settlement
from src.models import Trade, OrderData, OrderExecution
from src.helper_functions import get_logger
from src.constants import SETTLEMENT_CONTRACT_ADDRESS


class Web3API:
    """
    Class for fetching data from a Web3 API.
    """

    def __init__(self) -> None:
        load_dotenv()
        if getenv("NODE_URL"):
            self.url = getenv("NODE_URL")
        else:
            infura_key = getenv("INFURA_KEY")
            self.url = f"https://mainnet.infura.io/v3/{infura_key}"
        self.web_3 = Web3(Web3.HTTPProvider(self.url))
        self.contract = self.web_3.eth.contract(
            address=Address(HexBytes(SETTLEMENT_CONTRACT_ADDRESS)), abi=gpv2_settlement
        )
        self.logger = get_logger()

    def get_chain_id(self) -> int:
        return self.web_3.eth.chain_id

    def get_current_block_number(self) -> Optional[int]:
        """
        Function that returns the current block number
        """
        try:
            return int(self.web_3.eth.block_number)
        except ValueError as err:
            self.logger.warning(f"Error while fetching block number: {err}")
            return None
        except Exception as err:  # pylint: disable=W0718
            self.logger.warning(f"Exception of type {type(err)} not handled: {err}")
            return None

    def get_filtered_receipts(
        self, start_block: int, end_block: int, target: str, topics: list[Any]
    ) -> Optional[list[Any]]:
        """
        Function filters receipts by contract address, and block ranges
        """
        if start_block > end_block:
            return []
        filter_criteria: FilterParams = {
            "fromBlock": int(start_block),
            "toBlock": int(end_block),
            "address": self.web_3.to_checksum_address(target),
            "topics": topics,
        }
        try:
            log_receipts = self.web_3.eth.filter(filter_criteria).get_all_entries()
        except ValueError as err:
            self.logger.warning(f"ValueError while fetching hashes: {err}")
            return None
        except Exception as err:  # pylint: disable=W0718
            self.logger.warning(f"Exception of type {type(err)} not handled: {err}")
            return None
        return log_receipts

    def get_tx_hashes_by_block(self, start_block: int, end_block: int) -> list[str]:
        """
        Function filters hashes by contract address, and block ranges
        """
        topics = [
            HexStr("0xa07a543ab8a018198e99ca0184c93fe9050a79400a0a723441f84de1d972cc17")
        ]
        log_receipts = self.get_filtered_receipts(
            start_block, end_block, SETTLEMENT_CONTRACT_ADDRESS, topics
        )

        if log_receipts is None:
            return []
        settlement_hashes_list = list(
            {log_receipt["transactionHash"].hex() for log_receipt in log_receipts}
        )
        return settlement_hashes_list

    def get_eth_transfers_by_block_range(
        self, start_block: int, end_block: int, target: str
    ) -> Optional[float]:
        """
        Function that computes total eth transfers to a target Safe address
        within a certain block range
        """
        log_receipts = self.get_filtered_receipts(start_block, end_block, target, [])
        if log_receipts is None:
            return None
        total_transfers_in_eth = 0.0
        for txs in log_receipts:
            if txs["topics"][0] == HexBytes(
                "0x3d0ce9bfc3ed7d6862dbb28b2dea94561fe714a1b4d019aa8af39730d1ad7c3d"
            ):
                total_transfers_in_eth += int(txs["data"].hex(), 16) / 10**18
        return total_transfers_in_eth

    def get_transaction(self, tx_hash: str) -> Optional[TxData]:
        """
        Takes settlement hash as input, returns transaction data.
        """
        try:
            transaction = self.web_3.eth.get_transaction(HexStr(tx_hash))
        except Exception as err:  # pylint: disable=W0718
            self.logger.warning(
                f"Error of type {type(err)} while fetching transaction: {err}"
            )
            transaction = None
        return transaction

    def get_tx_block_number(self, tx_hash: str) -> Optional[int]:
        """
        Takes tx hash as input, returns block number where tx took place.
        """
        transaction = self.get_transaction(tx_hash)
        if transaction is None:
            return None
        return transaction["blockNumber"]

    def get_receipt(self, tx_hash: str) -> Optional[TxReceipt]:
        """
        Get the receipt of a transaction from the transaction hash.
        This is used to obtain the gas used for the transaction.
        """
        try:
            receipt = self.web_3.eth.wait_for_transaction_receipt(HexStr(tx_hash))
        except ValueError as err:
            self.logger.warning(f"Error fetching log receipt: {err}")
            receipt = None
        return receipt

    def get_settlement(self, transaction: TxData) -> dict[str, Any]:
        """
        Decode settlement from transaction using the settlement contract.
        """
        return self.get_settlement_from_calldata(transaction["input"].hex())

    def get_settlement_from_calldata(self, calldata: str) -> dict[str, Any]:
        """
        Decode settlement from transaction using the settlement contract.
        """
        args: dict[str, Any] = self.contract.decode_function_input(calldata)[1]
        return args

    def get_trades(self, settlement: dict[str, Any]) -> list[Trade]:
        """
        Get all trades from a settlement.
        """
        trades = []
        for i in range(len(settlement["trades"])):
            data = self.get_order_data_from_settlement(settlement, i)
            execution = self.get_order_execution_from_settlement(settlement, i)
            trades.append(Trade(data, execution))

        return trades

    def get_order_data_from_settlement(
        self, settlement: dict[str, Any], i: int
    ) -> OrderData:
        """
        Given a settlement and the index of a trade, return order information.
        """
        decoded_trade = settlement["trades"][i]
        tokens = settlement["tokens"]

        order_data = OrderData(
            decoded_trade["buyAmount"],
            decoded_trade["sellAmount"],
            decoded_trade["feeAmount"],
            tokens[decoded_trade["buyTokenIndex"]],
            tokens[decoded_trade["sellTokenIndex"]],
            self.is_sell_order(decoded_trade),
            self.is_partially_fillable(decoded_trade),
        )
        return order_data

    def get_order_execution_from_settlement(
        self, settlement: dict[str, Any], i: int
    ) -> OrderExecution:
        # pylint: disable=too-many-locals
        """
        Given a settlement and the index of a trade, compute the execution of the order.
        """
        decoded_trade = settlement["trades"][i]
        tokens = settlement["tokens"]
        clearing_prices = settlement["clearingPrices"]

        buy_token = tokens[decoded_trade["buyTokenIndex"]]
        buy_token_price = clearing_prices[decoded_trade["buyTokenIndex"]]
        buy_token_index_ucp = tokens.index(buy_token)
        buy_token_price_ucp = clearing_prices[buy_token_index_ucp]

        sell_token = tokens[decoded_trade["sellTokenIndex"]]
        sell_token_price = clearing_prices[decoded_trade["sellTokenIndex"]]
        sell_token_index_ucp = tokens.index(sell_token)
        sell_token_price_ucp = clearing_prices[sell_token_index_ucp]

        executed_amount = decoded_trade["executedAmount"]
        precomputed_fee_amount = decoded_trade["feeAmount"]

        if self.is_sell_order(decoded_trade):  # sell order
            buy_amount = int(
                executed_amount * Fraction(sell_token_price, buy_token_price)
            )
            sell_amount = int(
                buy_amount * Fraction(buy_token_price_ucp, sell_token_price_ucp)
            )
            fee_amount = precomputed_fee_amount + executed_amount - sell_amount
        else:  # buy order
            buy_amount = executed_amount
            sell_amount = int(
                buy_amount * Fraction(buy_token_price_ucp, sell_token_price_ucp)
            )
            fee_amount = (
                precomputed_fee_amount
                + int(buy_amount * Fraction(buy_token_price, sell_token_price))
                - sell_amount
            )

        return OrderExecution(buy_amount, sell_amount, fee_amount)

    @staticmethod
    def is_sell_order(decoded_trade: dict[str, Any]) -> bool:
        """
        Check if the order corresponding to a trade is a sell order.
        """
        return str(f"{decoded_trade['flags']:08b}")[-1] == "0"

    @staticmethod
    def is_partially_fillable(decoded_trade: dict[str, Any]) -> bool:
        """
        Check if the order corresponding to a trade is partially-fillable.
        """
        return str(f"{decoded_trade['flags']:08b}")[-2] == "1"

    @staticmethod
    def get_batch_gas_costs(transaction: TxData, receipt: TxReceipt) -> tuple[int, int]:
        """
        Combine the transaction and receipt to return gas used and gas price.
        """
        return int(receipt["gasUsed"]), int(transaction["gasPrice"])

    def get_current_gas_price(self) -> Optional[int]:
        """
        Get the current gas price.
        """
        try:
            gas_price = int(self.web_3.eth.gas_price)
        except ValueError as err:
            self.logger.warning(f"Error fetching gas price: {err}")
            gas_price = None
        return gas_price
