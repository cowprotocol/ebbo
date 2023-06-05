"""
Fee Test
"""

from web3.types import TxData, TxReceipt
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.orderbookapi import OrderbookAPI
from src.helper_functions import get_logger
from src.trades import Trade
from src.constants import (
    FEE_ABSOLUTE_DEVIATION_ETH_FLAG,
    FEE_RELATIVE_DEVIATION_FLAG,
)


class FeeTest(BaseTest):
    """
    Class for testing fees.
    """

    def __init__(self):
        super().__init__()
        self.web3_api = Web3API()
        self.orderbook_api = OrderbookAPI()
        self.logger = get_logger()

    def run(self, tx_hash) -> bool:
        """
        Given a transaction hash, check if there is a partially-fillable order in the settlement.
        If this is the case, perform multiple tests on the execution of those orders to check if
        the fee was set correctly.
        TODO: add more explanations
        """
        # get settlement and trades via web3 api
        transaction = self.web3_api.get_transaction(tx_hash)
        if transaction is None:
            return False
        settlement = self.web3_api.get_settlement(transaction)
        trades = self.web3_api.get_trades(settlement)

        partially_fillable_indices = self.find_partially_fillable(trades)

        # Only run test if at least one partially fillable order is in the batch.
        if len(partially_fillable_indices) > 0:
            log_output = [
                f"Partially fillable order found for hash: {tx_hash}",
                f"Indices of partially fillable orders: {partially_fillable_indices}",
            ]
            self.logger.debug("\t".join(log_output))

            # get additional data for the batch
            receipt = self.web3_api.get_receipt(tx_hash)
            if receipt is None:
                return False

            for i in partially_fillable_indices:
                trade = trades[i]
                success = self.run_quote_test(trade, transaction)
                if not success:
                    return False

            success = self.run_cost_coverage_test(transaction, receipt)
            if not success:
                return False
            # TODO: should this be written as
            #
            # if not self.run_cost_coverage_test(transaction, receipt):
            #     return False
            #
            # to be shorter?

        return True

    def alert(self, msg: str):
        self.logger.error(msg)

    def find_partially_fillable(self, trades: list[Trade]) -> list[int]:
        """
        Go through a list of trades and output a list of indices corresponding to all partially
        fillable orders.
        """
        partially_fillable_indices = []
        for i, trade in enumerate(trades):
            if trade.data.is_partially_fillable:
                partially_fillable_indices.append(i)

        return partially_fillable_indices

    def run_quote_test(self, trade: Trade, transaction: TxData) -> bool:
        """
        Check if the fee proposed by a solver is close to the fee proposed by our quoting system.
        The order is treated as a fill-or-kill order with the same amount as executed in this batch.
        The fee is rescaled by the relative difference in gas prices between the time of settlement
        and the time of quoting.
        The transaction data is only used for the gas price and for logging the transaction hash
        at the moment.
        """
        tx_hash = transaction["hash"].hex()
        quote = self.orderbook_api.get_quote(trade)
        if quote is None:
            self.logger.error("Error fetching quote. Skipping hash %s.", tx_hash)
            return False

        gas_price = int(transaction["gasPrice"])
        gas_price_quote = self.web3_api.get_current_gas_price()
        if gas_price_quote is None:
            self.logger.error(
                "Error fetching current gas price. Skipping hash %s.", tx_hash
            )
            return False

        quote.adapt_execution_to_gas_price(gas_price_quote, gas_price)

        fee_amount = trade.execution.fee_amount
        quote_fee_amount = quote.execution.fee_amount

        diff_fee_abs = fee_amount - quote_fee_amount
        diff_fee_rel = (fee_amount - quote_fee_amount) / quote_fee_amount

        log_output = [
            f"Quote test\nTx hash: {tx_hash}",
            f"Trade: {trade}",
            f"Winning Solver: {transaction['from']}",
            f"Fee: {fee_amount}",
            f"Fee quote: {quote_fee_amount}",
            f"Absolute difference: {diff_fee_abs}",
            f"Relative difference: {100 * diff_fee_rel:.2f}%",
        ]
        if abs(diff_fee_rel) > FEE_RELATIVE_DEVIATION_FLAG:
            self.alert("\t".join(log_output))
        return True

    def run_cost_coverage_test(self, transaction: TxData, receipt: TxReceipt) -> bool:
        """
        Test if the cost of a batch are close to the fees collected in that batch.
        """
        tx_hash = transaction["hash"].hex()
        competition_data_list = self.orderbook_api.get_solver_competition_data(
            [tx_hash]
        )
        if len(competition_data_list) == 0:
            self.logger.debug("No competition data found. Skipping hash.")
            return False
        competition_data = competition_data_list[0]

        gas_amount = int(receipt["gasUsed"])
        gas_price = int(transaction["gasPrice"])

        batch_fee = int(competition_data["solutions"][-1]["objective"]["fees"])
        batch_cost = gas_amount * gas_price

        a_abs = batch_fee - batch_cost
        a_rel = (batch_fee - batch_cost) / batch_cost

        log_output = [
            "Cost coverage test\n",
            f"Tx hash: {tx_hash}",
            f"Winning Solver: {transaction['from']}",
            f"Fee: {batch_fee * 1e-18:.5f}ETH",
            f"Cost: {batch_cost * 1e-18:.5f}ETH",
            f"Absolute difference: {a_abs * 1e-18:.5f}ETH",
            f"Relative difference: {100 * a_rel:.2f}%",
        ]

        if (
            abs(a_abs) > 1e18 * FEE_ABSOLUTE_DEVIATION_ETH_FLAG
            or abs(a_rel) > FEE_RELATIVE_DEVIATION_FLAG
        ):
            self.alert("\t".join(log_output))

        return True
