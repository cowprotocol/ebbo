"""
Fee Test
"""

from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.orderbookapi import OrderbookAPI
from src.helper_functions import get_logger
from src.constants import (
    FEE_ABSOLUTE_DEVIATION_ETH_FLAG,
    FEE_RELATIVE_DEVIATION_FLAG,
)


class FeeTest(BaseTest):
    """
    Class for testing fees.
    """

    def __init__(self):
        self.web3_api = Web3API()
        self.orderbook_api = OrderbookAPI()
        self.logger = get_logger()

    def run(self, tx_hash) -> bool:  # pylint: disable=too-many-locals
        """
        Given a transaction hash, check if there is a partially-fillable order in the settlement.
        If this is the case, perform multiple tests on the execution of those orders to check if
        the fee was set correctly.
        TODO: add more explanations
        """
        # get settlement and trades via api
        transaction = self.web3_api.get_transaction(tx_hash)
        if transaction is None:
            return False
        settlement = self.web3_api.get_settlement(transaction)
        trades = self.web3_api.get_trades(settlement)

        partially_fillable_indices = []
        for i, trade in enumerate(trades):
            if trade.data.is_partially_fillable:
                partially_fillable_indices.append(i)
                log_output = (
                    "Partially fillable order found.\t"
                    + "Tx hash:"
                    + tx_hash
                    + "\t\t"
                    + "Order uid: "
                    + "NOT IMPLEMENTED YET"
                )
                self.logger.debug(log_output)

        if len(partially_fillable_indices) > 0:
            # get additional data for the batch
            receipt = self.web3_api.get_receipt(tx_hash)
            if receipt is None:
                return False

            # get batch costs
            gas_amount, gas_price = self.web3_api.get_batch_gas_costs(
                transaction, receipt
            )

            for i in partially_fillable_indices:
                trade = trades[i]
                quote = self.orderbook_api.get_quote(trade)
                if quote is None:
                    self.logger.error("Error fetching quote. Skipping hash %s", tx_hash)
                    return False

                gas_price_quote = self.web3_api.get_current_gas_price()
                if gas_price_quote is None:
                    self.logger.error(
                        "Error fetching current gas price. Skipping hash %s", tx_hash
                    )
                    return False

                quote.adapt_execution_to_gas_price(gas_price_quote, gas_price)

                fee_amount = trade.execution.fee_amount
                quote_fee_amount = quote.execution.fee_amount

                diff_fee_abs = fee_amount - quote_fee_amount
                diff_fee_rel = (fee_amount - quote_fee_amount) / quote_fee_amount

                log_output = (
                    "Quote test:"
                    "Tx hash: "
                    + tx_hash
                    + "\t\t"
                    + "Order indices: "
                    + str(i)
                    + "\t\t"
                    + "Winning Solver: "
                    + transaction["from"]
                    + "\t\t"
                    + "Fee: "
                    + str(fee_amount)
                    + "\t\t"
                    + "Fee quote: "
                    + str(quote_fee_amount)
                    + "\t\t"
                    + "Absolute difference: "
                    + str(diff_fee_abs)
                    + "\t\t"
                    + "Relative difference: "
                    + (str(format(100 * diff_fee_rel, ".2f")) + "%")
                )
                if abs(diff_fee_rel) > FEE_RELATIVE_DEVIATION_FLAG:
                    self.alert(log_output)

            batch_cost = gas_amount * gas_price

            # get batch fees (not correct if some orders are market orders)
            competition_data_list = self.orderbook_api.get_solver_competition_data(
                [tx_hash]
            )
            if len(competition_data_list) == 0:
                self.logger.debug("No competition data found. Skipping hash.")
                return False
            competition_data = competition_data_list[0]

            batch_fee = int(competition_data["solutions"][-1]["objective"]["fees"])

            a_abs = batch_fee - batch_cost
            a_rel = (batch_fee - batch_cost) / batch_cost

            log_output = (
                "Cost coverage test:"
                "Tx hash: "
                + tx_hash
                + "\t\t"
                + "Order indices: "
                + str(partially_fillable_indices)
                + "\t\t"
                + "Winning Solver: "
                + transaction["from"]
                + "\t\t"
                + "Fee: "
                + (str(format(batch_fee * 1e-18, ".5f")) + " ETH")
                + "\t\t"
                + "Cost: "
                + (str(format(batch_cost * 1e-18, ".5f")) + " ETH")
                + "\t\t"
                + "Absolute difference: "
                + (str(format(a_abs * 1e-18, ".5f")) + " ETH")
                + "\t\t"
                + "Relative difference: "
                + (str(format(100 * a_rel, ".2f")) + "%")
            )

            if (
                abs(a_abs) > 1e18 * FEE_ABSOLUTE_DEVIATION_ETH_FLAG
                or abs(a_rel) > FEE_RELATIVE_DEVIATION_FLAG
            ) and len(trades) == len(partially_fillable_indices):
                self.alert(log_output)
        return True

    def alert(self, msg: str):
        self.logger.error(msg)
