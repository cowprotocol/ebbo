"""
Quote test for partially fillable orders.
"""
# pylint: disable=logging-fstring-interpolation
# pylint: disable=duplicate-code

from web3.types import TxData
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.orderbookapi import OrderbookAPI
from src.models import Trade, find_partially_fillable
from src.constants import FEE_RELATIVE_DEVIATION


class PartialFillFeeQuoteTest(BaseTest):
    """
    Class for testing fees.
    """

    def __init__(self) -> None:
        super().__init__()
        self.web3_api = Web3API()
        self.orderbook_api = OrderbookAPI()

    def run(self, tx_hash: str) -> bool:
        """
        Given a transaction hash, check if there is a partially-fillable order in the settlement.
        If this is the case, perform multiple tests on the execution of those orders to check if
        the fee was set correctly.
        """
        # get settlement and trades via web3 api
        transaction = self.web3_api.get_transaction(tx_hash)
        if transaction is None:
            return False
        settlement = self.web3_api.get_settlement(transaction)
        trades = self.web3_api.get_trades(settlement)

        partially_fillable_indices = find_partially_fillable(trades)
        self.logger.debug(
            f"Number of partially fillable orders: {len(partially_fillable_indices)}."
        )

        # Only run test if at least one partially fillable order is in the batch.
        if len(partially_fillable_indices) > 0:
            for i in partially_fillable_indices:
                trade = trades[i]
                success = self.run_quote_test(trade, transaction)
                if not success:
                    return False

        return True

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
            self.logger.warning("Error fetching quote. Skipping trade %s.", trade)
            return True

        gas_price = int(transaction["gasPrice"])
        gas_price_quote = self.web3_api.get_current_gas_price()
        if gas_price_quote is None:
            self.logger.warning(
                "Error fetching current gas price. Skipping hash %s.", tx_hash
            )
            return False

        quote.adapt_execution_to_gas_price(gas_price_quote, gas_price)

        self.check_and_log(trade, quote, transaction)

        return True

    def check_and_log(
        self, trade: Trade, trade_quote: Trade, transaction: TxData
    ) -> None:
        """Compare fees of a trade to fees from a quote for that trade."""

        fee_amount = trade.execution.fee_amount
        quote_fee_amount = trade_quote.execution.fee_amount

        diff_fee_abs = fee_amount - quote_fee_amount
        diff_fee_rel = (fee_amount - quote_fee_amount) / quote_fee_amount

        log_output = "\t".join(
            [
                f"Quote test\nTx hash: {transaction['hash'].hex()}",
                f"Trade: {trade}",
                f"Winning Solver: {transaction['from']}",
                f"Fee: {fee_amount}",
                f"Fee quote: {quote_fee_amount}",
                f"Absolute difference: {diff_fee_abs}",
                f"Relative difference: {100 * diff_fee_rel:.2f}%",
            ]
        )

        if abs(diff_fee_rel) > FEE_RELATIVE_DEVIATION:
            self.alert(log_output)
        elif abs(diff_fee_rel) > FEE_RELATIVE_DEVIATION / 2:
            self.logger.warning(log_output)
        elif abs(diff_fee_rel) > FEE_RELATIVE_DEVIATION / 4:
            self.logger.info(log_output)
        else:
            self.logger.debug(log_output)
